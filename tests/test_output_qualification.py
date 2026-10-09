"""Actual Run start/dispatch/restart path, exclusively synthetic and offline."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from pro_a import output_decomposition as output
from pro_a import output_provider_record_v5 as v5, output_provider_record_v6 as v6
from pro_a.workbench import output_qualification as operator
from pro_a.workbench.source_operations import SourceOperations, SourceOperationError
from pro_a.workbench.cloud_jobs import CloudProfile
from series_binding_helpers import case, text, request_parts, response_content, batch_record, ToolResponse, rows
from node_intent_helpers import from_valid_v4
from test_workbench_stage7 import clean_pdf, upload


class FakeTransport:
    def __init__(self, mutation=None):
        self.calls = []
        self.mutation = mutation

    def __call__(self, endpoint, **kwargs):
        request = kwargs['json']
        self.calls.append(copy.deepcopy(request))
        target, source = request_parts(request)
        version = target['provider_record_version']
        record = batch_record(json.loads(response_content(target, source)),
                              {**target, 'provider_record_version': output.RECORD_VERSION})
        if version in (v5.VERSION, v6.VERSION):
            record = from_valid_v4(record)
        if version == v6.VERSION:
            for candidate in record['node_candidates']:
                del candidate['ownership_evidence_ref']
        if self.mutation == 'unsupported':
            for claim in record['claims']:
                claim['related_candidate_names'] = []
        elif self.mutation == 'forged':
            record['claims'][0]['evidence']['evidence_ref'] = 'EV_FORGED'
        elif self.mutation == 'foreign':
            record['claims'][0]['evidence']['evidence_ref'] = self.foreign
        elif self.mutation == 'wrong_owner':
            record['node_candidates'][0]['ownership_evidence_ref'] = 'EV_FORGED'
        elif self.mutation == 'own_selection':
            selection = record['claims'][0]['evidence']
            record['claims'] = []
            record['node_candidates'][0]['evidence_properties'] = [{'field': 'evidence_ref', 'value': selection}]
        assert request['tools'][0]['function']['parameters'] == output.record_schema(record_version=version)
        return ToolResponse(json.dumps(record))


def fixture(tmp_path, monkeypatch, version=v6.VERSION):
    original = socket.socket.connect
    def local_only(sock, address):
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', 'localhost', '::1'):
            return original(sock, address)
        raise AssertionError('NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket, 'connect', local_only)
    monkeypatch.setenv('PROA_LLM_API_KEY', 'synthetic-only')
    value = case(tmp_path)
    path = value['phase4_config']
    content = path.read_text(encoding='utf-8').replace('enabled = false\nmodel = "fake-semantic-v1"',
        'enabled = true\nprovider = "deepseek"\napi_key_env = "PROA_LLM_API_KEY"\nmodel = "deepseek-flash"')
    path.write_text(content, encoding='utf-8')
    cloud = CloudProfile('deepseek', 'deepseek-flash')
    value['service'] = SourceOperations(value['config'], value['source_profile'], cloud)
    source = upload(value, clean_pdf(tmp_path, text=text(18)))
    service = value['service']
    if version == output.RECORD_VERSION:
        run = service.start(source['source_id'], idempotency_key='synthetic-default-run-0001')['run']
    else:
        run = operator.start(service, source['source_id'], record_version=version,
                             reason='Synthetic operator qualification', idempotency_key='synthetic-operator-run-0001')['run']
    return value, run


def advance(value, rid, transport=None):
    providers = operator.providers(value['service'], rid) if transport else None
    if providers:
        providers[output.OPERATION].transport = transport
    return operator.advance(value['service'], rid, worker_id='synthetic-operator', provider=providers)


@pytest.mark.parametrize('version', [v5.VERSION, v6.VERSION])
def test_operator_run_binding_durable_restart_and_stop(tmp_path, monkeypatch, version):
    value, run = fixture(tmp_path, monkeypatch, version)
    rid = run['processing_run_id']; frozen = run['runtime_identity']
    production = value['config'].knowledge_db.read_bytes()
    assert value['service'].advance_once(worker_id='ordinary-worker', processing_run_id=rid) is None
    run = advance(value, rid)
    assert run['state'] == 'EXTRACTION_PROCESSING', run.get('error')
    worker = operator.frozen_worker(value['service'], rid)
    inputs = worker.output_batches.inputs(run)
    selected = frozen['whole_piece_output_decomposition']
    assert selected['provider_record_version'] == version
    assert all(b[0]['binding_version'] == selected['binding_version'] and b[3].series_version == selected['series'] for b in inputs)
    provider = operator.providers(value['service'], rid)[output.OPERATION]
    assert provider.configuration()['contract'] == selected
    transport = FakeTransport()
    run = advance(value, rid, transport)
    assert run['accepted_leaf_calls'] == 1, run.get('error')
    assert run['stage'] != 'BOUNDED_EXTRACTION_COMPLETE'
    immutable = {p: p.read_bytes() for p in value['config'].artifact_root.rglob('*') if p.is_file()}
    before_rows = {t: rows(value, t) for t in ('bounded_extraction_outcomes', 'bounded_extraction_segment_results', 'bounded_extraction_events')}
    payload = {'config': asdict(value['config']), 'profile': asdict(value['source_profile']),
               'cloud': asdict(worker.jobs.profile), 'run_id': rid, 'runtime': frozen}
    restart = tmp_path/'restart.json'; restart.write_text(json.dumps(payload, default=str), encoding='utf-8')
    child = subprocess.run([sys.executable, '-B', '-c', '''
import json,sys,socket
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench import output_qualification as operator
from test_output_qualification import FakeTransport,advance
socket.socket.connect=lambda *a: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN'))
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for key in ('knowledge_db','state_db','artifact_root'):data['config'][key]=Path(data['config'][key])
data['profile']['phase4_config_path']=Path(data['profile']['phase4_config_path'])
data['cloud']['accepted_model_aliases']=tuple(data['cloud']['accepted_model_aliases'])
service=SourceOperations(WorkbenchConfig(**data['config']),SourceProfile(**data['profile']),CloudProfile(**data['cloud']))
assert operator.frozen_worker(service,data['run_id']).jobs.current_runtime()==data['runtime']
fake=FakeTransport()
for _ in range(8):
 if data['runtime']['whole_piece_output_decomposition']['provider_record_version'].endswith('-v6'):
  providers=operator.providers(service,data['run_id'])
  providers['WHOLE_PIECE_OUTPUT_BATCH'].transport=fake
  receipt=operator.resume(service,data['run_id'],worker_id='restart-worker',idempotency_key='synthetic-restart-0001',max_new_calls=1,provider=providers)
  run=receipt['run']
 else:
  run=advance({'service':service},data['run_id'],fake)
 assert run['state']=='EXTRACTION_PROCESSING',run.get('error')
 if run['stage']=='BOUNDED_EXTRACTION_COMPLETE':break
assert run['stage']=='BOUNDED_EXTRACTION_COMPLETE'
assert run['runtime_identity']==data['runtime']
print('RESTART_COMPLETE',len(fake.calls))
''', str(restart)], capture_output=True, timeout=90,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join([str(Path(__file__).parent), *sys.path])})
    assert child.returncode == 0, child.stderr.decode(errors='replace')
    assert b'RESTART_COMPLETE 1' in child.stdout
    run = value['service'].get_run(rid)
    assert run['runtime_identity'] == frozen and run['coverage_status'] == 'COMPLETE'
    assert run['provider_call_count'] == 2 and not rows(value, 'source_processing_jobs')
    assert all(p.read_bytes() == content for p, content in immutable.items())
    for table, old in before_rows.items():
        assert all(row in rows(value, table) for row in old)
    assert value['config'].knowledge_db.read_bytes() == production
    ledger = worker.output_batches.ledger
    for binding in inputs:
        series, plan, _, _ = ledger.read(binding[3].series_id)
        for segment in plan.leaves:
            accepted = next(r for r in rows(value, 'bounded_extraction_segment_results') if r['segment_id'] == segment.segment_id)
            outcome = next(r for r in rows(value, 'bounded_extraction_outcomes') if r['attempt_id'] == accepted['attempt_id'])
            attempt = next(r for r in rows(value, 'bounded_extraction_attempts') if r['attempt_id'] == accepted['attempt_id'])
            _, body = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, attempt['attempt_id']+'.raw.json', outcome))
            replay = output.record_to_result(body.decode(), series, segment, binding[2], binding[1])
            assert replay.result_sha256 == accepted['result_sha256']
            document = json.loads(ledger._read_artifact(series.series_id, segment.segment_id+'.result.json', accepted))
            if version == v6.VERSION:
                proof = v6.compile_result(body.decode(), series, segment, binding[2], binding[1])[1]
                assert document['ownership_provenance'] == proof
                assert len(proof['candidates'][0]['evidence_refs']) > 1
                assert len(proof['candidates'][0]['supports']) == len(json.loads(body)['claims'])
            else:
                assert 'ownership_provenance' not in document


@pytest.mark.parametrize('mutation,version', [('unsupported', v6.VERSION), ('forged', v6.VERSION),
    ('foreign', v6.VERSION), ('wrong_owner', v5.VERSION)])
def test_operator_rejects_invalid_ownership_without_acceptance(tmp_path, monkeypatch, mutation, version):
    value, run = fixture(tmp_path, monkeypatch, version); rid = run['processing_run_id']
    advance(value, rid)
    worker = operator.frozen_worker(value['service'], rid)
    binding = worker.output_batches.inputs(worker.get_run(rid))[0]
    fake = FakeTransport(mutation)
    fake.foreign = worker.output_batches.ledger.read(binding[3].series_id)[1].leaves[-1].assigned_evidence_refs[0]
    run = advance(value, rid, fake)
    assert run['state'] == 'BLOCKED', run.get('error')
    assert len(fake.calls) == 1 and not rows(value, 'bounded_extraction_segment_results')
    assert len(rows(value, 'bounded_extraction_outcomes')) == 1
    assert not rows(value, 'source_processing_jobs')


def test_own_selection_and_frozen_config_drift(tmp_path, monkeypatch):
    value, run = fixture(tmp_path, monkeypatch); rid = run['processing_run_id']
    advance(value, rid)
    run = advance(value, rid, FakeTransport('own_selection'))
    assert run['accepted_leaf_calls'] == 1, run.get('error')
    value['phase4_config'].write_text(value['phase4_config'].read_text().replace(
        'max_chunk_chars = 22000', 'max_chunk_chars = 21000'))
    with pytest.raises(SourceOperationError, match='RETRY_FROZEN_CONFIG_INCOMPLETE'):
        advance(value, rid, FakeTransport())


def test_default_v4_run_remains_v4_after_restart(tmp_path, monkeypatch):
    value, run = fixture(tmp_path, monkeypatch, output.RECORD_VERSION); rid = run['processing_run_id']
    assert 'output_operator_qualification' not in run['runtime_identity']
    service = value['service']; frozen = run['runtime_identity']
    service.advance_once(worker_id='default-v4-worker', processing_run_id=rid)
    fresh = SourceOperations(service.config, service.profile, service.jobs.profile)
    from pro_a.workbench.source_operations import build_source_providers
    from pro_a.config import load_config
    providers = build_source_providers(load_config(service.profile.phase4_config_path).llm, service.jobs.profile)
    fake = FakeTransport(); providers[output.OPERATION].transport = fake
    run = fresh.advance_once(worker_id='default-v4-worker', processing_run_id=rid, provider=providers)
    assert run['accepted_leaf_calls'] == 1 and run['runtime_identity'] == frozen
    assert request_parts(fake.calls[0])[0]['provider_record_version'] == output.RECORD_VERSION
    assert not rows(value, 'source_processing_jobs')


@pytest.mark.parametrize('module', ['node_candidate_intent.py', 'output_provider_record_v5.py',
    'output_provider_record_v6.py', 'workbench/output_qualification.py'])
def test_compiler_and_operator_bytes_are_in_runtime_identity(monkeypatch, module):
    from pro_a.workbench import cloud_jobs, retry_compatibility
    assert module in retry_compatibility._CLOUD_EXECUTION_DEPENDENCIES
    args = {'workbench_schema_version': '12', 'output_binding_version': output.OWNERSHIP_BINDING_VERSION}
    original = cloud_jobs.sha256_file
    cloud_jobs.runtime_identity.cache_clear()
    before = cloud_jobs.runtime_identity('synthetic-adapter', **args)
    monkeypatch.setattr(cloud_jobs, 'sha256_file', lambda path:
        '0'*64 if Path(path).as_posix().endswith('/'+module) else original(path))
    cloud_jobs.runtime_identity.cache_clear()
    try:
        after = cloud_jobs.runtime_identity('synthetic-adapter', **args)
        assert before['runtime_sha256'] != after['runtime_sha256']
        assert before['domain_code_sha256'] != after['domain_code_sha256']
    finally:
        cloud_jobs.runtime_identity.cache_clear()
