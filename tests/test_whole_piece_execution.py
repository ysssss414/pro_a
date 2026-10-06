"""Real compact adapter over synthetic HTTP, disposable schema12 databases."""
import json
import re
from copy import deepcopy

import pytest
import requests

from pro_a.cloud_contract import DeterministicFakeProvider, ADAPTER_VERSION
from pro_a.config import load_config
from pro_a.workbench.cloud_jobs import CloudProfile, InjectedCrash
from pro_a.workbench.source_operations import SourceOperations, build_source_providers
from series_binding_helpers import case, start, ToolResponse as Response, response_content
from lexical_record_helpers import from_wire


class Transport:
    def __init__(self, mode='success'):
        self.mode, self.calls = mode, []

    def __call__(self, endpoint, *, json: dict, headers, timeout, allow_redirects=False):
        assert endpoint == 'https://api.deepseek.com/beta/chat/completions' and allow_redirects is False
        self.calls.append(deepcopy(json))
        if self.mode == 'unknown':
            raise requests.ReadTimeout('PRIVATE_ERROR')
        if self.mode == 'known_failure':
            response = Response('')
            response.status_code = 503
            return response
        if self.mode == 'invalid':
            return Response('PRIVATE_INVALID_JSON')
        if self.mode == 'truncated':
            return Response('{"wire":', 'length', 12000)
        source = json['messages'][1]['content'].split('\nComplete annotated SourcePiece:\n')[1]
        refs = re.findall(r'\[(EV_[^\]]+)\]', source)
        target = {'assigned_evidence_refs': refs}
        body = __import__('json').loads(response_content(target, source))
        from series_binding_helpers import request_parts,batch_record
        actual,_=request_parts(json)
        record=batch_record(body,target) if 'assigned_evidence_refs' in actual else from_wire(body['wire'])
        return Response(__import__('json').dumps(record, ensure_ascii=False))


def setup(tmp_path, monkeypatch, mode='success', count=40, *, decomposed=False):
    value = case(tmp_path)
    path = value['phase4_config']
    path.write_text(path.read_text(encoding='utf-8').replace('enabled = false\nmodel = "fake-semantic-v1"',
                    'enabled = true\nmodel = "deepseek-flash"'), encoding='utf-8')
    value['cloud_profile'] = CloudProfile('deepseek', 'deepseek-flash')
    value['service'] = SourceOperations(value['config'], value['source_profile'], value['cloud_profile'])
    monkeypatch.setenv('PROA_LLM_API_KEY', 'synthetic-only')
    # External networking is forbidden; the transport is an in-memory HTTP fixture.
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))
    provider = build_source_providers(load_config(path).llm, value['cloud_profile'])
    transport = Transport(mode)
    if decomposed:
        provider['WHOLE_PIECE_OUTPUT_BATCH'].transport = transport
    else:
        from pro_a.whole_piece_compact import WholePieceCompactProvider
        from dataclasses import replace
        provider['SOURCE_ANALYSIS_PIECE'] = WholePieceCompactProvider(replace(load_config(path).llm, max_output_tokens=12000, max_retries=0), transport=transport)
    semantic = DeterministicFakeProvider()
    semantic.provider_identity = 'deepseek'
    semantic.adapter_version = ADAPTER_VERSION
    provider['SEMANTIC_DECOMPOSITION'] = semantic
    def laid_out_pdf(root, *, text):
        from reportlab.pdfgen.canvas import Canvas
        path = root / 'synthetic-whole-piece.pdf'
        canvas = Canvas(str(path), pagesize=(612, 792))
        for index, line in enumerate(text.splitlines()):
            if index and index % 40 == 0:
                canvas.showPage()
            canvas.setFont('Helvetica', 8)
            canvas.drawString(30, 750 - (index % 40) * 17, line)
        canvas.save()
        return path
    monkeypatch.setattr('series_binding_helpers.clean_pdf', laid_out_pdf)
    _, run_id = start(value, tmp_path, count=count)
    if decomposed:
        run = value['service'].advance_once(worker_id='whole-piece-test', processing_run_id=run_id)
    else:
        # Historical single-call acceptance is exercised as a standalone CloudJob.
        # New SourceOperations runs never select this scheduling path.
        from pathlib import Path
        from pro_a.phase4_orchestration import start_execution
        from pro_a.phase4_retry import RetryPolicy
        from pro_a.operational_ingestion import plan_external_source_analysis
        service = value['service']
        with service.store.connect() as c:
            source = c.execute('SELECT * FROM private_sources').fetchone()
        native = start_execution(service.artifacts.resolve(source['storage_relative']),
            config_path=path, retry_policy=RetryPolicy.FORBID_ALL, stop_after='SOURCE_READY', external_semantic=True)
        native_root = Path(native['execution_root'])
        service._transition(run_id,'EXTRACTION_PROCESSING','STANDALONE_WHOLE_PIECE_TEST',values={
            'native_execution_id':native['execution_id'],
            'native_root_relative':native_root.relative_to(load_config(path).root.resolve()).as_posix()})
        plan = plan_external_source_analysis(native_root/'engine',config_path=path)
        run=service.get_run(run_id)
        checkpoint={'native_state':'SOURCE_READY','execution_id':native['execution_id'],
            'run_id':plan['run_id'],'plan_sha256':plan['plan']['initial_extraction_plan_sha256'],
            'resume_semantics':'REFERENCE_EXISTING_NATIVE_CHECKPOINT_ONLY'}
        for ordinal,piece in enumerate(plan['pieces'],1):
            artifact=service._register_input(run,'SOURCE_ANALYSIS_PIECE',ordinal,
                {**piece,'source_sha256':plan['source_sha256']},checkpoint)
            service._bind_job(run_id,'SOURCE_ANALYSIS_PIECE',ordinal,artifact)
    assert run['state'] == 'EXTRACTION_PROCESSING', run.get('error')
    return value, provider, transport, run_id


def test_historical_whole_piece_canonical_response(tmp_path, monkeypatch):
    value, providers, transport, run_id = setup(tmp_path, monkeypatch)
    service=value['service']
    job=service._jobs_for(run_id,'SOURCE_ANALYSIS_PIECE')[0]
    result=service.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'],worker_id='whole-test',job_id=job['job_id'])
    assert result['status']=='SUCCEEDED'
    canonical=service.jobs.private_result(job['job_id'])['normalized_output']['response']
    assert len(canonical['claims'])==40 and len(transport.calls)==1
    with service.store.connect() as c:
        assert c.execute('SELECT count(*) FROM bounded_extraction_series').fetchone()[0]==0
        assert c.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0]=='12'


@pytest.mark.parametrize('mode,error', [('invalid', 'OUTPUT_VALIDATION_FAILED'),
    ('truncated', 'WHOLE_PIECE_COMPACT_OUTPUT_LIMIT'), ('known_failure', 'PROVIDER_ERROR'),
    ('unknown', 'UNKNOWN_EXTERNAL_OUTCOME')])
def test_failures_do_not_retry(tmp_path, monkeypatch, mode, error):
    value, providers, transport, run_id = setup(tmp_path, monkeypatch, mode)
    service = value['service']
    job = service._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    result = service.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='whole-piece-test', job_id=job['job_id'])
    assert result['last_error'] == error
    assert service.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='whole-piece-test', job_id=job['job_id']) is None
    assert len(transport.calls) == 1
    if mode in ('invalid', 'truncated'):
        with service.store.connect() as c:
            events = c.execute("SELECT event_json FROM cloud_job_events WHERE event_type='WHOLE_PIECE_RAW_DURABLE'").fetchall()
        assert len(events) == 1 and 'PRIVATE_INVALID_JSON' not in str(events[0][0])
        raw = service.artifacts.resolve(json.loads(events[0][0])['artifact_relative']).read_text(encoding='utf-8')
        assert 'PRIVATE_INVALID_JSON' in raw if mode == 'invalid' else '{\\"wire\\":' in raw


@pytest.mark.parametrize('fault,expected,calls', [
    ('after_claim', 'QUEUED', 0), ('after_dispatch_intent', 'QUEUED', 0),
    ('before_network_call', 'RECOVERY_REQUIRED', 0),
    ('after_provider_response', 'RECOVERY_REQUIRED', 1),
    ('before_raw_artifact_durable', 'RECOVERY_REQUIRED', 1),
    ('after_raw_artifact_before_event_commit', 'SUCCEEDED', 1),
    ('after_raw_artifact_durable', 'SUCCEEDED', 1),
    ('before_result_artifact_durable', 'SUCCEEDED', 1),
    ('after_result_artifact_durable', 'SUCCEEDED', 1),
    ('before_terminal_update', 'SUCCEEDED', 1),
])
def test_crash_recovery_no_provider_recall(tmp_path, monkeypatch, fault, expected, calls):
    value, providers, transport, run_id = setup(tmp_path, monkeypatch)
    service = value['service']
    job = service._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    with pytest.raises(InjectedCrash):
        service.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='whole-piece-test',
                             job_id=job['job_id'], lease_seconds=0, fault_at=fault)
    fresh = SourceOperations(value['config'], value['source_profile'], value['cloud_profile'])
    fresh.jobs.reconcile()
    assert fresh.jobs.get(job['job_id'])['status'] == expected
    assert len(transport.calls) == calls
    if expected == 'RECOVERY_REQUIRED':
        assert fresh.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='whole-piece-test', job_id=job['job_id']) is None
        assert len(transport.calls) == calls


def test_whole_piece_mcp_is_readonly_and_private(tmp_path, monkeypatch):
    from pro_a.mcp.service import ReadService
    from pro_a.workbench.store import Store
    from test_mcp_bounded_reads import snapshot
    value, providers, _, run_id = setup(tmp_path, monkeypatch, 'invalid')
    job=value['service']._jobs_for(run_id,'SOURCE_ANALYSIS_PIECE')[0]
    value['service'].jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'],worker_id='whole-test',job_id=job['job_id'])
    run=value['service'].get_run(run_id)
    before = snapshot(value['config'])
    original = Store.connect
    def readonly(store, *, operator_write=False):
        assert not operator_write
        return original(store)
    monkeypatch.setattr(Store, 'connect', readonly)
    service = ReadService(value['config'])
    result = service.get_processing_run(run_id)
    assert 'PRIVATE_INVALID_JSON' not in result.model_dump_json()
    assert service.operations.get_run(run_id) == run
    assert before == snapshot(value['config'])


@pytest.mark.parametrize('tamper', ['bytes', 'missing'])
def test_pending_raw_corruption_fails_closed(tmp_path, monkeypatch, tamper):
    value, providers, transport, run_id = setup(tmp_path, monkeypatch)
    jobs = value['service'].jobs
    job = value['service']._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    with pytest.raises(InjectedCrash):
        jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='whole-piece-test', job_id=job['job_id'],
                      lease_seconds=0, fault_at='after_raw_artifact_durable')
    path = next(value['config'].artifact_root.glob('cloud-results/*/*.raw.json'))
    if tamper == 'bytes':
        path.write_bytes(b'{}')
    else:
        path.unlink()
    jobs.reconcile()
    assert jobs.get(job['job_id'])['status'] == 'RECOVERY_REQUIRED'
    assert len(transport.calls) == 1


def test_fresh_process_raw_recovery_without_provider(tmp_path, monkeypatch):
    import os
    import subprocess
    import sys
    from pathlib import Path
    from dataclasses import asdict
    value, providers, _, run_id = setup(tmp_path, monkeypatch)
    job = value['service']._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    info = {'config': asdict(value['config']), 'profile': str(value['phase4_config']), 'job_id': job['job_id']}
    path = tmp_path / 'synthetic-recovery.json'
    path.write_text(json.dumps(info, default=str))
    bootstrap = '''
import json,sys,os,socket
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile,build_source_providers
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.config import load_config
from test_whole_piece_execution import Transport
info=json.loads(Path(sys.argv[1]).read_text())
for k in ('knowledge_db','state_db','artifact_root'):info['config'][k]=Path(info['config'][k])
service=SourceOperations(WorkbenchConfig(**info['config']),SourceProfile(Path(info['profile'])),CloudProfile('deepseek','deepseek-flash'))
def forbidden(*a,**k):raise AssertionError('NETWORK_FORBIDDEN')
socket.socket.connect=forbidden
'''
    crash = bootstrap + '''
from pro_a.whole_piece_compact import WholePieceCompactProvider
from dataclasses import replace
provider=WholePieceCompactProvider(replace(load_config(Path(info['profile'])).llm,max_output_tokens=12000,max_retries=0))
provider.transport=Transport()
def fault(point,expected):
 if expected=='after_raw_artifact_before_event_commit':os._exit(73)
service.jobs._fault=fault
service.jobs.run_once(provider,worker_id='child-crash',job_id=info['job_id'],lease_seconds=0)
'''
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join((
        str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parent))))
    exited = subprocess.run([sys.executable, '-B', '-c', crash, str(path)], capture_output=True, env=environment)
    assert exited.returncode == 73, exited.stderr.decode(errors='replace')
    recover = bootstrap + "\nservice.jobs.reconcile()\nprint(service.jobs.get(info['job_id'])['status'])\n"
    result = subprocess.run([sys.executable, '-B', '-c', recover, str(path)], capture_output=True, env=environment)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    assert result.stdout.strip() == b'SUCCEEDED'
    with value['service'].store.connect() as c:
        assert c.execute('SELECT count(*) FROM cloud_attempt_dispatches').fetchone()[0] == 1


@pytest.mark.parametrize('mode,error', [('invalid', 'OUTPUT_VALIDATION_FAILED'), ('truncated', 'WHOLE_PIECE_COMPACT_OUTPUT_LIMIT')])
def test_raw_recovery_rejects_invalid_output_without_recall(tmp_path, monkeypatch, mode, error):
    value, providers, transport, run_id = setup(tmp_path, monkeypatch, mode)
    service = value['service']
    job = service._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    with pytest.raises(InjectedCrash):
        service.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='whole-piece-test',
            job_id=job['job_id'], lease_seconds=0, fault_at='after_raw_artifact_durable')
    service.jobs.reconcile()
    assert service.jobs.get(job['job_id'])['last_error'] == error
    assert service.jobs.get(job['job_id'])['status'] == 'FAILED'
    assert len(transport.calls) == 1


def test_two_workers_dispatch_only_once(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    value, providers, transport, run_id = setup(tmp_path, monkeypatch)
    service = value['service']
    job = service._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    def worker(index):
        fresh = SourceOperations(value['config'], value['source_profile'], value['cloud_profile'])
        return fresh.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='worker-' + str(index), job_id=job['job_id'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert sum(r is not None for r in results) == 1
    assert len(transport.calls) == 1
    with service.store.connect() as c:
        assert c.execute('SELECT count(*) FROM cloud_attempt_dispatches').fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM cloud_job_events WHERE event_type='WHOLE_PIECE_RAW_DURABLE'").fetchone()[0] == 1


def test_frozen_request_and_exact_raw_are_durable_before_parse(tmp_path, monkeypatch):
    from pro_a.whole_piece_compact import render
    from pro_a.workbench import whole_piece_raw
    value, providers, transport, run_id = setup(tmp_path, monkeypatch, count=1)
    service = value['service']
    job = service._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE')[0]
    content = []
    class ForbiddenReasoning:
        def __str__(self):
            raise AssertionError('REASONING_INSPECTED')
        def __len__(self):
            raise AssertionError('REASONING_MEASURED')
    def request_transport(*args, **kwargs):
        with service.store.connect() as c:
            assert c.execute('SELECT count(*) FROM cloud_attempt_dispatches').fetchone()[0] == 1
            artifact = c.execute('SELECT artifact_relative FROM source_cloud_inputs').fetchone()[0]
        payload = json.loads(service.artifacts.resolve(artifact).read_bytes())['payload']
        assert render(payload) == kwargs['json']
        response = transport(*args, **kwargs)
        data = response.json()
        content.append(data['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        data['choices'][0]['message']['reasoning_content'] = ForbiddenReasoning()
        response.json = lambda: data
        return response
    original_parse = whole_piece_raw.parse
    def checked_parse(raw, payload):
        with service.store.connect() as c:
            event = json.loads(c.execute("SELECT event_json FROM cloud_job_events WHERE event_type='WHOLE_PIECE_RAW_DURABLE'").fetchone()[0])
        envelope = json.loads(service.artifacts.resolve(event['artifact_relative']).read_bytes())
        assert envelope['result']['output'] == raw == content[0]
        assert 'reasoning_content' not in json.dumps(envelope)
        return original_parse(raw, payload)
    providers['SOURCE_ANALYSIS_PIECE'].transport = request_transport
    monkeypatch.setattr(whole_piece_raw, 'parse', checked_parse)
    result = service.jobs.run_once(providers['SOURCE_ANALYSIS_PIECE'], worker_id='durable-order', job_id=job['job_id'])
    assert result['status'] == 'SUCCEEDED' and len(content) == 1


def test_dense_semantic_job_overflow_fails_before_semantic_submission(tmp_path, monkeypatch):
    from test_phase43_stage1_operator_scale import semantic_inputs
    value, providers, transport, run_id = setup(tmp_path, monkeypatch, decomposed=True)
    # Native replay is qualified above; exercise the submission boundary with
    # a dense synthetic canonical checkpoint, without repeating PDF analysis.
    def dense_checkpoint(native_root, **kwargs):
        assert kwargs['stop_after'] == 'SEMANTIC_INPUT_READY'
        path = native_root / 'engine/evidence/stage6_semantic_input.json'
        path.write_text(json.dumps({'run_id': 'SYNTHETIC_DENSE', 'payload_sha256': 'a' * 64,
                                   'payload': {'claims': semantic_inputs(249)}}), encoding='utf-8')
        return {'state': 'SEMANTIC_INPUT_READY'}
    monkeypatch.setattr('pro_a.workbench.source_operations.resume_execution', dense_checkpoint)
    for _ in range(10):
        run = value['service'].advance_once(worker_id='whole-piece-test', provider=providers, processing_run_id=run_id)
        if run['state']!='EXTRACTION_PROCESSING':break
    assert run['state'] == 'BLOCKED' and run['error']['code'] == 'SOURCE_JOB_BUDGET_EXCEEDED', run.get('error')
    assert not value['service']._jobs_for(run_id, 'SEMANTIC_DECOMPOSITION')
    assert all(j['attempt_count'] == 1 for j in value['service']._jobs_for(run_id, 'SOURCE_ANALYSIS_PIECE'))
    assert len(transport.calls) == 3 and run['logical_extraction_series_count'] == 1
