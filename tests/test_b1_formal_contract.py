"""Synthetic B1 fixtures, no external calls, real Source Operations/ledger persistence."""
import copy
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import requests

from pro_a import b1_extraction as b1, output_decomposition as output
from pro_a import output_provider_record_v7 as v7
from pro_a.bounded_extraction import initial_extraction_plan
from pro_a.config import LLMConfig
from pro_a.evidence_binding import identity
from pro_a.source_analysis_wire import build_source_evidence_catalog
from pro_a.workbench import b1_extraction as entry, output_qualification
from test_source_analysis_wire import context, canonical_claim, empty_canonical
from test_whole_piece_compact import payload_for
from test_evidence_intent_prototype import v6_record
from test_evidence_intent_v7 import new_record
from series_binding_helpers import case, ToolResponse, rows
from test_workbench_stage7 import clean_pdf, upload


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', lambda *a, **k: pytest.fail('REAL_PROVIDER_FORBIDDEN'))
    monkeypatch.setenv('PROA_LLM_API_KEY', 'TEST_FIXTURE_NOT_HUMAN_AUTHORIZATION')


def frozen_context(ctx, catalog):
    assigned = [u.evidence_ref for u in catalog.units[:2]]
    return {'version': b1.CONTEXT, 'source_sha256': ctx.source_sha256,
        'piece_sha256': ctx.piece.source_sha256, 'assigned_evidence_refs': assigned,
        'closure': {ref: [catalog.units[2].evidence_ref] for ref in assigned},
        'source_metadata_reference': {'source_sha256': ctx.source_sha256,
            'title': 'Synthetic expert interview', 'author': '', 'publication_time': ''}}


def fixture():
    ctx = context('Synthetic Company forecasts 42 units next year if qualified.\n'
                  'Its second route may begin later.\nThe expert is referring to the same Company.\n'
                  'Unrelated Context fact is not assigned.', ('NODE_A',))
    catalog = build_source_evidence_catalog(ctx)
    native = payload_for(ctx)
    native['scoped_node_catalog'][0].update(aliases=['Synthetic Alias'], description='Full native record preserved.')
    native.update(user_prompt=ctx.piece.source_text,
        user_prompt_sha256=hashlib.sha256(ctx.piece.source_text.encode()).hexdigest(), initial_plan_sha256='a' * 64)
    selected = frozen_context(ctx, catalog)
    value = output.piece_input(native, ctx.source_sha256, 'TEST_FIXTURE_B1_RUN', 1,
        binding_version=b1.BINDING, b1_request_context=selected)
    _, _, series = output.restore_input(value, ctx.source_sha256, 'TEST_FIXTURE_B1_RUN', 1)
    segment = initial_extraction_plan(series).leaves[0]
    return value, ctx, catalog, series, segment


class SyntheticCounter:
    """TEST FIXTURE only; not a qualified live counter."""
    identity = {'version': b1.COUNTER, 'fixture': True, 'server_exact_usage': False}
    tokens = 100

    def __init__(self, config_path=None):
        self.identity = copy.deepcopy(type(self).identity)
        if config_path is not None:
            self.identity['manifest_sha256'] = b1.load_settings(config_path)['counter_identity_sha256']

    def preflight(self, request):
        b1.require(self.tokens <= 13000, 'B1_INPUT_PREFLIGHT_EXCEEDED')
        return {'version': b1.COUNTER, 'counter_identity': self.identity,
            'request_sha256': identity(request), 'input_tokens': self.tokens,
            'reserved_input_tokens': 14000, 'reserved_output_tokens': 12000,
            'reserved_total_tokens': 26000, 'server_exact_usage': False, 'budget_reservation_authority': False}


@pytest.mark.parametrize('tokens,allowed', [(13000, True), (13001, False)])
def test_complete_counter_template_schema_budget_and_component_drift(tmp_path, monkeypatch, tokens, allowed):
    from types import SimpleNamespace
    value, ctx, catalog, series, segment = fixture()
    request = output.segment_payload(value, ctx, catalog, series, segment)['request']
    context_path = tmp_path/'context.json'
    context_path.write_text(json.dumps(value['b1_request_context']))
    manifest = {'recipe_commit': 'TEST_FIXTURE_OFFICIAL_FORMAT_NOT_LIVE_QUALIFICATION'}
    for key in b1.COMPONENTS:
        component = tmp_path/'runtime/counter/target/debug'/key
        component.parent.mkdir(parents=True, exist_ok=True)
        component.write_text('SYNTHETIC_ONLY_' + key)
        manifest[key] = {'path': str(component), 'sha256': b1.sha(component)}
    manifest_path = tmp_path/'counter.json'
    manifest_path.write_text(json.dumps(manifest))
    config_path = tmp_path/'config.toml'
    config_path.write_text('[b1]\n' + '\n'.join(f'{k} = {json.dumps(str(v))}' for k, v in {
        'context_file': context_path.as_posix(), 'context_sha256': b1.sha(context_path),
        'counter_identity_file': manifest_path.as_posix(), 'counter_identity_sha256': b1.sha(manifest_path)}.items()))
    observed = []
    def counter_process(args, **kwargs):
        counted = json.loads(Path(args[1]).read_text(encoding='utf8'))
        observed.append(counted)
        directory = Path(args[3]); directory.mkdir()
        (directory/'local-token-count.json').write_text(json.dumps({'encoder': 'DeepseekV41Encoding', 'input_tokens': tokens}))
        rendered = '\n'.join(m['content'] for m in counted['messages']) + '\n### Available Tool Schemas\n\n'
        rendered += json.dumps(counted['tools'][0]['function'], ensure_ascii=False) + '\n\nYou MUST strictly follow'
        (directory/'rendered-prompt.txt').write_text(rendered, encoding='utf8')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(b1.subprocess, 'run', counter_process)
    with pytest.raises(ValueError, match='NOT_QUALIFIED'):
        b1.LocalCounter(config_path)
    monkeypatch.setattr(b1, 'QUALIFIED_COMPONENTS', {k: manifest[k]['sha256'] for k in b1.COMPONENTS})
    monkeypatch.setattr(b1, 'RECIPE_COMMIT', manifest['recipe_commit'])
    counter = b1.LocalCounter(config_path)
    if allowed:
        proof = counter.preflight(request)
        assert proof['input_tokens'] == 13000 and proof['request_sha256'] == identity(request)
        assert proof['reserved_total_tokens'] == 26000 and proof['server_exact_usage'] is False
    else:
        with pytest.raises(ValueError, match='PREFLIGHT_EXCEEDED'):
            counter.preflight(request)
    assert observed == [request]
    Path(manifest['tokenizer']['path']).write_text('DRIFTED')
    with pytest.raises(ValueError, match='COMPONENT_DRIFT'):
        counter.preflight(request)
    assert observed == [request]


def provider(transport, counter=None):
    cfg = LLMConfig(enabled=True, model='deepseek-flash', max_retries=0,
                    max_output_tokens=12000, api_key_env='PROA_LLM_API_KEY')
    return output.OutputBatchProvider(cfg, binding_version=b1.BINDING,
        b1_counter=counter or SyntheticCounter(), transport=transport)


def test_deterministic_prompt_schema_scope_and_separate_12k_identity():
    value, ctx, catalog, series, segment = fixture()
    first = output.segment_payload(value, ctx, catalog, series, segment)
    assert first == output.segment_payload(value, ctx, catalog, series, segment)
    assert hashlib.sha256(first['request']['messages'][0]['content'].encode()).hexdigest() == b1.SYSTEM_SHA256
    assert first['request']['tools'][0]['function']['parameters'] == v7.record_schema()
    user = json.loads(first['request']['messages'][1]['content'])
    assert [r['evidence_ref'] for r in user['source_regions']] == [u.evidence_ref for u in catalog.units[:3]]
    assert all(r['text'] == next(u.exact_text for u in catalog.units if u.evidence_ref == r['evidence_ref']) for r in user['source_regions'])
    assert user['source_regions'][-1]['role'] == 'CONTEXT'
    assert user['source_metadata_reference']['author'] == ''
    assert user['scoped_node_catalog'] == value['native']['scoped_node_catalog']
    assert user['scoped_node_catalog'][0]['aliases'] == ['Synthetic Alias']
    assert user['formal_execution']['request_contract_sha256'] == identity(first['target'])
    assert user['evaluation_only'] is False and user['formal_execution']['processing_run_id'] == series.processing_run_id
    assert segment.max_output_tokens == first['request']['max_tokens'] == 12000
    assert series.budget.max_provider_calls == 1 and series.budget.max_cumulative_output_tokens == 12000
    assert output.contract()['max_output_tokens'] == output.contract(binding_version=output.EVIDENCE_INTENT_BINDING_VERSION)['max_output_tokens'] == 24000
    assert output_qualification.qualification_contract(output.EVIDENCE_INTENT_BINDING_VERSION)['version'] == 'evidence-intent-operator-qualification-v2'
    assert output_qualification.qualification_contract(b1.BINDING)['version'] == 'b1-source-operations-extraction-entry-v1'
    from pro_a.workbench.source_operations import SourceOperationError
    with pytest.raises(SourceOperationError, match='CONTRACT_SELECTION_REQUIRED'):
        entry.start(object(), 'SOURCE_NOT_CREATED', request_contract='unqualified',
            reason='TEST FIXTURE', idempotency_key='wrong-selection-test')
    from pro_a.bounded_extraction import create_extraction_series, SeriesBudget
    with pytest.raises(ValueError, match='INVALID_B1_BUDGET'):
        create_extraction_series(ctx, catalog, series.processing_run_id, SeriesBudget(),
            series_version=b1.SERIES, eligible_evidence_refs=series.eligible_evidence_refs)


@pytest.mark.parametrize('field', ['source_sha256', 'piece_sha256', 'assigned_evidence_refs', 'closure', 'source_metadata_reference'])
def test_context_identity_drift_is_rejected(field):
    value, ctx, catalog, _, _ = fixture()
    changed = copy.deepcopy(value)
    changed['b1_request_context'][field] = '0' * 64 if field.endswith('sha256') else [] if field == 'assigned_evidence_refs' else {}
    with pytest.raises(ValueError):
        output.restore_input(changed, ctx.source_sha256, 'TEST_FIXTURE_B1_RUN', 1)


def test_no_context_primary_or_invisible_dependency_and_no_semantic_truth_claim():
    value, ctx, catalog, series, segment = fixture()
    canonical = empty_canonical()
    canonical['claims'] = [canonical_claim(catalog.units[0].exact_text, catalog.units[0])]
    record = new_record(v6_record(catalog, segment, canonical), catalog)
    record['claims'][0]['evidence_pointer'] = ''
    b1.validate_record(json.dumps(record), value['b1_request_context'], catalog, ctx, segment)
    _, review = v7.compile_result(json.dumps(record), series, segment, catalog, ctx)
    assert review['semantic_authorization'] == 'NOT_ESTABLISHED'
    record['claims'][0]['evidence'] = v7.unit_selection(catalog.units[2])
    with pytest.raises(ValueError, match='OUTSIDE_ASSIGNED'):
        v7.compile_result(json.dumps(record), series, segment, catalog, ctx)
    record['claims'][0]['evidence'] = v7.unit_selection(catalog.units[0])
    record['claims'][0]['research_review']['context_dependencies'] = [{
        'evidence': v7.unit_selection(catalog.units[3]), 'relationship': 'BACKGROUND', 'reason': 'Invisible fixture'}]
    with pytest.raises(ValueError, match='NOT_VISIBLE'):
        b1.validate_record(json.dumps(record), value['b1_request_context'], catalog, ctx, segment)
    record['claims'][0]['research_review']['context_dependencies'][0]['evidence'] = v7.unit_selection(catalog.units[2])
    b1.validate_record(json.dumps(record), value['b1_request_context'], catalog, ctx, segment)


def test_preflight_equals_transport_and_mutation_cannot_reuse_proof():
    value, ctx, catalog, series, segment = fixture()
    calls = []
    def transport(endpoint, **kwargs):
        calls.append(copy.deepcopy(kwargs['json']))
        return ToolResponse('{}')
    selected = provider(transport)
    raw = output.segment_payload(value, ctx, catalog, series, segment)
    frozen = selected.prepare_payload(raw)
    original = copy.deepcopy(raw)
    raw['request']['messages'][1]['content'] += ' caller mutation'
    assert frozen['request'] == original['request']
    raw = original
    changed = copy.deepcopy(frozen)
    changed['request']['messages'][1]['content'] += ' changed after preflight'
    with pytest.raises(ValueError, match='PREFLIGHT_DRIFT'):
        selected.invoke(changed)
    assert calls == []
    selected.invoke(frozen)
    assert calls == [raw['request']]
    assert frozen['request_token_preflight']['request_sha256'] == identity(calls[0])
    with pytest.raises(ValueError, match='CONFIGURATION_MISMATCH'):
        output.OutputBatchProvider(replace(selected.cfg, max_output_tokens=24000), binding_version=b1.BINDING)
    with pytest.raises(ValueError, match='PARAMETER_DRIFT'):
        output.OutputBatchProvider(replace(selected.cfg, temperature=0.7), binding_version=b1.BINDING)


@pytest.mark.parametrize('input_tokens,total,model', [(14001, 14051, 'deepseek-flash'),
    (100, 26100, 'deepseek-flash'), (100, 150, 'drifted-model')])
def test_server_budget_or_model_drift_retains_response_but_cannot_accept(input_tokens, total, model):
    value, ctx, catalog, series, segment = fixture()
    response = ToolResponse('{"synthetic":"retained"}')
    response.value['model'] = model
    response.value['usage'].update(prompt_tokens=input_tokens, total_tokens=total)
    selected = provider(lambda *a, **k: response)
    result = selected.invoke(selected.prepare_payload(output.segment_payload(value, ctx, catalog, series, segment)))
    assert result.finish_reason == 'tool_calls' and result.input_tokens == input_tokens
    assert b1.response_violation(result.__dict__) in ('B1_MODEL_IDENTITY_DRIFT', 'B1_BUDGET_VIOLATION')
    assert result.content == b'{"synthetic":"retained"}'


def integration_fixture(tmp_path, monkeypatch):
    from pro_a.workbench.cloud_jobs import CloudProfile
    from pro_a.workbench.source_operations import SourceOperations
    from pro_a.phase4_orchestration import start_execution
    from pro_a.operational_ingestion import plan_external_source_analysis
    from pro_a.phase4_retry import RetryPolicy
    monkeypatch.setattr(b1, 'LocalCounter', SyntheticCounter)
    value = case(tmp_path)
    config_path = value['phase4_config']
    content = config_path.read_text(encoding='utf8').replace('enabled = false\nmodel = "fake-semantic-v1"',
        'enabled = true\napi_key_env = "PROA_LLM_API_KEY"\nmodel = "deepseek-flash"')
    config_path.write_text(content, encoding='utf8')
    pdf = clean_pdf(tmp_path, text='\n'.join(f'Expert: Synthetic Company product {i} forecasts {i+10} units next year if qualified.' for i in range(4)))
    # Separate local planning fixture, never a fabricated accepted Processing Run.
    preview = start_execution(pdf, config_path=config_path, retry_policy=RetryPolicy.FORBID_ALL,
                              stop_after='SOURCE_READY', external_semantic=True)
    assert preview['state'] == 'SOURCE_READY', preview
    plan = plan_external_source_analysis(Path(preview['execution_root'])/'engine', config_path=config_path)
    native = plan['pieces'][0]
    from pro_a.whole_piece_compact import piece_context
    ctx, catalog = piece_context({**native, 'source_sha256': plan['source_sha256']})
    frozen = frozen_context(ctx, catalog)
    context_path = tmp_path/'b1-context.json'
    context_path.write_text(json.dumps(frozen), encoding='utf8')
    counter_path = tmp_path/'counter.json'
    counter_path.write_text('{"TEST_FIXTURE":true}', encoding='utf8')
    config_path.write_text(content + '\n[b1]\n' + '\n'.join(f'{k} = {json.dumps(str(v))}' for k, v in {
        'context_file': context_path.as_posix(), 'context_sha256': b1.sha(context_path),
        'counter_identity_file': counter_path.as_posix(), 'counter_identity_sha256': b1.sha(counter_path)}.items()), encoding='utf8')
    value['service'] = SourceOperations(value['config'], value['source_profile'], CloudProfile('deepseek', 'deepseek-flash'))
    source = upload(value, pdf)
    run = entry.start(value['service'], source['source_id'], request_contract=b1.VERSION,
        reason='TEST FIXTURE opt-in B1', idempotency_key='synthetic-b1-selection-0001')['run']
    return value, run, context_path


class AssignedTransport:
    def __init__(self, timeout=False, truncated=False):
        self.calls = []
        self.timeout = timeout
        self.truncated = truncated

    def __call__(self, endpoint, **kwargs):
        self.calls.append(copy.deepcopy(kwargs['json']))
        if self.timeout:
            raise requests.Timeout('TEST FIXTURE UNKNOWN')
        user = json.loads(kwargs['json']['messages'][1]['content'])
        record = empty_canonical()
        record['claims'] = [canonical_claim(self.catalog.units[0].exact_text, self.catalog.units[0],
            nature='expert_judgment', attributed_to='Expert')]
        # Use the actual frozen catalog supplied by the real runner in this fixture.
        wire = v6_record(self.catalog, self.segment, record)
        result = new_record(wire, self.catalog)
        result['claims'][0]['evidence_pointer'] = ''
        assert user['assigned_evidence_refs'] == list(self.segment.assigned_evidence_refs)
        return ToolResponse(json.dumps(result), finish='length' if self.truncated else 'tool_calls')


@pytest.mark.parametrize('mode', ['success', 'over_budget', 'unknown', 'truncated', 'counter_drift'])
def test_real_shape_ledger_freeze_stop_origin_and_unknown_reservation(tmp_path, monkeypatch, mode):
    value, run, context_path = integration_fixture(tmp_path, monkeypatch)
    service, rid = value['service'], run['processing_run_id']
    production_before = value['config'].knowledge_db.read_bytes()
    assert service.advance_once(worker_id='ordinary-worker', processing_run_id=rid) is None
    run = entry.advance(service, rid, worker_id='b1-test-worker')
    assert run['state'] == 'EXTRACTION_PROCESSING', run.get('error')
    worker = entry.frozen_worker(service, rid)
    binding, ctx, catalog, series = worker.output_batches.inputs(run)[0]
    _, plan, _, _ = worker.output_batches.ledger.read(series.series_id)
    transport = AssignedTransport(timeout=mode == 'unknown', truncated=mode == 'truncated')
    transport.catalog, transport.segment = catalog, plan.leaves[0]
    providers = entry.providers(service, rid)
    providers[output.OPERATION].transport = transport
    if mode == 'over_budget':
        monkeypatch.setattr(SyntheticCounter, 'tokens', 13001)
    if mode == 'counter_drift':
        providers[output.OPERATION].b1_counter.identity['manifest_sha256'] = '0' * 64
    run = entry.advance(service, rid, worker_id='b1-test-worker', provider=providers)
    if mode in ('over_budget', 'counter_drift'):
        assert run['state'] == 'BLOCKED' and transport.calls == []
        assert run['error']['code'] == ('B1_INPUT_PREFLIGHT_EXCEEDED' if mode == 'over_budget' else 'B1_COUNTER_CONFIGURATION_MISMATCH')
        assert rows(value, 'bounded_extraction_attempts') == []
        assert rows(value, 'bounded_extraction_dispatches') == []
    elif mode == 'truncated':
        assert run['state'] == 'BLOCKED' and len(transport.calls) == 1
        assert len(worker.output_batches.ledger.read(series.series_id)[1].leaves) == 1
        assert rows(value, 'bounded_extraction_outcomes')[0]['external_outcome'] == 'TRUNCATED'
        assert rows(value, 'bounded_extraction_segment_results') == []
    elif mode == 'unknown':
        assert run['state'] == 'RECOVERY_REQUIRED' and len(transport.calls) == 1
        usage = worker.output_batches.ledger.read(series.series_id)[3]
        assert usage.output_token_liability == 12000 and usage.provider_call_count == 1
        again = entry.advance(service, rid, worker_id='b1-test-worker', provider=providers)
        assert again is None and len(transport.calls) == 1
        assert rows(value, 'bounded_extraction_segment_results') == []
    else:
        assert run['stage'] == 'BOUNDED_EXTRACTION_COMPLETE', run.get('error')
        assert run['assigned_coverage_status'] == 'COMPLETE' and run['coverage_status'] == 'PARTIAL'
        assert run['source_coverage_status'] == 'NOT_ESTABLISHED'
        assert service.get_run(rid)['coverage_status'] == 'PARTIAL'
        from pro_a.read_model.service import ReadService
        public = ReadService(value['config']).get_processing_run(rid).output_decomposition
        assert public.coverage_status == 'PARTIAL' and public.assigned_coverage_status == 'COMPLETE'
        assert public.coverage_scope == 'B1_FROZEN_ASSIGNED_ONLY' and public.source_coverage_status == 'NOT_ESTABLISHED'
        assert 'EV_' not in public.model_dump_json() and 'Synthetic Company' not in public.model_dump_json()
        attempts = rows(value, 'bounded_extraction_attempts')
        assert len(attempts) == len(rows(value, 'bounded_extraction_dispatches')) == 1
        assert len(rows(value, 'bounded_extraction_segment_results')) == 1
        prompt = json.loads(worker.output_batches.ledger._path(series.series_id, plan.leaves[0].segment_id + '.prompt.json').read_bytes())
        assert prompt['request'] == transport.calls[0]
        assert prompt['request_token_preflight']['request_sha256'] == identity(transport.calls[0])
        from pro_a.workbench.candidate_inputs import CandidateInputs
        reference = CandidateInputs(worker).publish(rid, attempts[0]['attempt_id'])
        document = CandidateInputs(worker).read(reference)
        assert document['scope']['run_id'] == rid and document['metadata_resolution'] is None
        assert len([o for o in document['objects'] if o['family'] == 'claims']) == 1
        assert document['scope']['runtime_identity']['b1_request_settings']['context'] == binding['b1_request_context']
        assert document['canonical_permission'] is False
        from pro_a.candidate_origin_v2 import ENTRY_CONTRACT
        from pro_a.workbench.source_operations import SourceOperationError
        with pytest.raises(SourceOperationError, match='SOURCE_METADATA_AUTHORITY_REQUIRED'):
            worker.start_v7_review([reference], idempotency_key='b1-unresolved-metadata-test', entry_contract=ENTRY_CONTRACT)
        restart = tmp_path/'restart.json'
        restart.write_text(json.dumps({'config': asdict(value['config']), 'profile': asdict(value['source_profile']),
            'cloud': asdict(worker.jobs.profile), 'run_id': rid, 'runtime': run['runtime_identity']}, default=str))
        child = subprocess.run([sys.executable, '-B', '-c', '''
import json,socket,sys
from pathlib import Path
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO_NETWORK'))
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench import b1_extraction as entry
data=json.loads(Path(sys.argv[1]).read_text())
for key in ('knowledge_db','state_db','artifact_root'):data['config'][key]=Path(data['config'][key])
data['profile']['phase4_config_path']=Path(data['profile']['phase4_config_path'])
data['cloud']['accepted_model_aliases']=tuple(data['cloud']['accepted_model_aliases'])
service=SourceOperations(WorkbenchConfig(**data['config']),SourceProfile(**data['profile']),CloudProfile(**data['cloud']))
worker=entry.frozen_worker(service,data['run_id'])
assert worker.jobs.current_runtime()==data['runtime']
binding,ctx,catalog,series=worker.output_batches.inputs(worker.get_run(data['run_id']))[0]
assert binding['b1_request_context']==data['runtime']['b1_request_settings']['context']
assert worker.output_batches.ledger.read(series.series_id)[3].provider_call_count==1
assert all(Path(m.__file__).resolve().is_relative_to(Path(sys.argv[2]).resolve()) for n,m in sys.modules.items()
 if (n=='pro_a' or n.startswith('pro_a.')) and getattr(m,'__file__',None))
print('B1_FROZEN_RECONSTRUCTED')
''', str(restart), str(Path(b1.__file__).resolve().parent)], capture_output=True, timeout=60,
            env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path), 'PYTHONUTF8': '1'})
        assert child.returncode == 0 and child.stdout.strip() == b'B1_FROZEN_RECONSTRUCTED', child.stderr.decode(errors='replace')
        changed = json.loads(context_path.read_text())
        changed['source_metadata_reference']['author'] = 'Unapproved new attribution'
        context_path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match='CONTEXT_FILE_DRIFT'):
            entry.frozen_worker(service, rid)
    assert not [r for r in rows(value, 'source_processing_jobs') if r['operation_kind'] == 'SEMANTIC_DECOMPOSITION']
    assert value['config'].knowledge_db.read_bytes() == production_before


@pytest.mark.parametrize('name', ['b1_extraction.py', 'resources/B1_EVIDENCE_FIRST_SYSTEM_V1.txt', 'workbench/b1_extraction.py'])
def test_b1_code_and_prompt_are_in_both_runtime_fingerprints(monkeypatch, name):
    from pro_a import operational_contract
    from pro_a.workbench import cloud_jobs
    root = Path(b1.__file__).parent
    target = (root/name).resolve()
    cloud_jobs.runtime_identity.cache_clear()
    before = cloud_jobs.runtime_identity('semantic-backend-adapter-v2', workbench_schema_version='12')
    operator_before = operational_contract.runtime_identity()
    original_read = Path.read_bytes
    original_sha = cloud_jobs.sha256_file
    monkeypatch.setattr(Path, 'read_bytes', lambda p: original_read(p) + b'TEST_FIXTURE_DRIFT' if p.resolve() == target else original_read(p))
    monkeypatch.setattr(cloud_jobs, 'sha256_file', lambda p: hashlib.sha256(original_read(Path(p)) + b'TEST_FIXTURE_DRIFT').hexdigest() if Path(p).resolve() == target else original_sha(p))
    cloud_jobs.runtime_identity.cache_clear()
    after = cloud_jobs.runtime_identity('semantic-backend-adapter-v2', workbench_schema_version='12')
    assert after['domain_code_sha256'] != before['domain_code_sha256']
    assert operational_contract.runtime_identity() != operator_before
    cloud_jobs.runtime_identity.cache_clear()
