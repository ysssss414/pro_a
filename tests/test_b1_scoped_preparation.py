"""Synthetic preparation fixtures, no inference or human authorization."""
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import requests

from pro_a import source_scope as scope, b1_extraction as b1, output_decomposition as output
from pro_a.analyzer import Analyzer
from pro_a.db import Database
from pro_a.parsers import ParsedSource, parse_source_with_diagnostics
from pro_a.config import load_config
from pro_a.evidence_binding import identity
from pro_a.workbench import b1_extraction as entry, b1_preparation as prep
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.source_operations import SourceOperations
from series_binding_helpers import case, rows
from test_b1_formal_contract import SyntheticCounter, frozen_context, AssignedTransport
from test_workbench_stage7 import upload
from multiformat_helpers import write_pdf


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))
    monkeypatch.setenv('PROA_LLM_API_KEY', 'TEST_FIXTURE_ONLY')


def test_range_deterministic_mapping_drift_and_legacy_identity(tmp_path):
    from stability_helpers import make_config
    cfg, db = make_config(tmp_path)
    planner = Analyzer(cfg, db)
    text = ''.join(f'[[PAGE:{n}]]\n' + (f'Synthetic page {n}. ' * 70) + '\n' for n in range(1, 5))
    parsed = ParsedSource(text, 'pdf', {})
    selection = scope.select(parsed, 'a' * 64, 2, 3)
    assert {'pdf_layout.py','analyzer.py'} <= set(selection['parser_identity']['components'])
    assert selection == scope.select(parsed, 'a' * 64, 2, 3)
    scope.validate_parsed(parsed, 'a' * 64, selection)
    full = planner.plan_initial_extraction('fixture.pdf', text, 'deep', adaptive_retry_policy='forbid')
    scoped = planner.plan_initial_extraction('fixture.pdf', text, 'deep', adaptive_retry_policy='forbid', source_scope=selection)
    assert len(full.pieces) > 1 and len(scoped.pieces) == 1
    piece = scoped.pieces[0]
    assert (piece.source_start, piece.source_end) == (selection['global_start'], selection['global_end'])
    assert text[piece.source_start:piece.source_end] == piece.source_piece.source_text
    assert piece.locators == ('PAGE:2', 'PAGE:3')
    assert piece.source_piece.scope_identity == identity(selection)
    assert scoped.artifact['coverage']['source_complete'] is False
    assert scope.original_range(selection, 1, 10) == (piece.source_start + 1, piece.source_start + 10)
    assert 'scope_identity' not in full.pieces[0].source_piece.document()
    assert full.artifact == planner.plan_initial_extraction('fixture.pdf', text, 'deep', adaptive_retry_policy='forbid').artifact
    changed = copy.deepcopy(selection); changed['parser_identity']['parsed_text_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='PARSE_OR_SOURCE_DRIFT'):
        scope.validate_parsed(parsed, 'a' * 64, changed)
    with pytest.raises(ValueError, match='TEXT_DRIFT'):
        scope.slice_text(text + 'drift', selection)
    with pytest.raises(ValueError, match='EVIDENCE_OUT_OF_RANGE'):
        scope.original_range(selection, 0, len(text))
    with pytest.raises(ValueError, match='EXCEEDS_PIECE_HARD_CAP'):
        planner.plan_initial_extraction('fixture.pdf', text, 'deep', adaptive_retry_policy='forbid', source_scope=scope.select(parsed, 'a'*64, 1, 4))
    for first, last, code in [(0, 1, 'PAGES_INVALID'), (1, 5, 'OUT_OF_RANGE')]:
        with pytest.raises(ValueError, match=code):
            scope.select(parsed, 'a' * 64, first, last)
    with pytest.raises(ValueError, match='AMBIGUOUS'):
        scope.select(ParsedSource(text.replace('[[PAGE:3]]', '[[PAGE:2]]'), 'pdf', {}), 'a'*64, 2, 3)


class ScopedSyntheticCounter(SyntheticCounter):
    identity = {'version': b1.COUNTER_V2, 'fixture': True, 'server_exact_usage': False}

    def preflight(self, request):
        return {**super().preflight(request), 'version': b1.COUNTER_V2,
            'request_wire_sha256':hashlib.sha256(json.dumps(request,allow_nan=False).encode('utf8')).hexdigest()}


def scoped_fixture(tmp_path, monkeypatch):
    from pro_a.phase4_orchestration import start_execution
    from pro_a.phase4_retry import RetryPolicy
    from pro_a.operational_ingestion import plan_external_source_analysis
    from pro_a.whole_piece_compact import piece_context
    monkeypatch.setattr(b1, 'LocalCounter', ScopedSyntheticCounter)
    value = case(tmp_path)
    config = value['phase4_config']
    content = config.read_text(encoding='utf8').replace('enabled = false\nmodel = "fake-semantic-v1"',
        'enabled = true\napi_key_env = "PROA_LLM_API_KEY"\nmodel = "deepseek-flash"')
    config.write_text(content, encoding='utf8')
    pdf = tmp_path/'synthetic-scoped.pdf'
    write_pdf(pdf, ['Outside page 1; must never appear in a request.',
        '\n'.join(f'Expert: Company forecasts {i+42} units in 2027 if qualified.' for i in range(4)),
        'Same Company has a second route.\nIts qualification is uncertain.'])
    parsed = parse_source_with_diagnostics(pdf, include_semantic_segments=True)
    selection = scope.select(parsed, b1.sha(pdf), 2, 3)
    preview = start_execution(pdf, config_path=config, retry_policy=RetryPolicy.FORBID_ALL,
        stop_after='SOURCE_READY', external_semantic=True)
    plan = plan_external_source_analysis(Path(preview['execution_root'])/'engine', config_path=config, source_scope=selection)
    ctx, catalog = piece_context({**plan['pieces'][0], 'source_sha256': plan['source_sha256']})
    context_path, scope_path, counter_path = (tmp_path/n for n in ('b1-context.json', 'scope.json', 'counter.json'))
    context_path.write_text(json.dumps(frozen_context(ctx, catalog)), encoding='utf8')
    scope_path.write_text(json.dumps(selection), encoding='utf8')
    counter_path.write_text(json.dumps({'version': b1.COUNTER_V2, 'TEST_FIXTURE': True}), encoding='utf8')
    settings = {'context_file': context_path.as_posix(), 'context_sha256': b1.sha(context_path),
        'scope_file': scope_path.as_posix(), 'scope_sha256': b1.sha(scope_path),
        'counter_identity_file': counter_path.as_posix(), 'counter_identity_sha256': b1.sha(counter_path)}
    config.write_text(content + '\n[b1]\n' + '\n'.join(f'{k} = {json.dumps(v)}' for k,v in settings.items()), encoding='utf8')
    value['service'] = SourceOperations(value['config'], value['source_profile'], CloudProfile('deepseek','deepseek-flash'))
    source = upload(value, pdf)
    run = entry.start(value['service'], source['source_id'], request_contract=b1.VERSION,
        reason='TEST FIXTURE scoped preparation only', idempotency_key='scoped-b1-test-fixture-0001')['run']
    rid = run['processing_run_id']
    assert value['service'].advance_once(worker_id='ordinary-worker', processing_run_id=rid) is None
    run = entry.advance(value['service'], rid, worker_id='explicit-b1-fixture')
    assert run['state'] == 'EXTRACTION_PROCESSING', run.get('error')
    return value, run


def test_prepare_only_replay_restart_and_frozen_transport(tmp_path, monkeypatch):
    value, run = scoped_fixture(tmp_path, monkeypatch)
    service, rid = value['service'], run['processing_run_id']
    before = value['config'].knowledge_db.read_bytes()
    first = entry.prepare(service, rid)
    assert first == entry.prepare(service, rid)
    # Fresh service/worker reconstruction, not an in-memory preparation cache.
    restarted = SourceOperations(service.config, service.profile, service.jobs.profile)
    assert entry.prepare(restarted, rid) == first
    restart = tmp_path/'preparation-restart.json'
    from dataclasses import asdict
    restart.write_text(json.dumps({'config':asdict(service.config), 'profile':asdict(service.profile),
        'cloud':asdict(service.jobs.profile), 'run_id':rid, 'expected':first}, default=str))
    child = subprocess.run([sys.executable, '-B', '-c', '''
import json,socket,sys
from pathlib import Path
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO_NETWORK'))
from pro_a import b1_extraction as b1
from pro_a.workbench import b1_extraction as entry
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from test_b1_scoped_preparation import ScopedSyntheticCounter
b1.LocalCounter=ScopedSyntheticCounter
d=json.loads(Path(sys.argv[1]).read_text())
for k in ('knowledge_db','state_db','artifact_root'):d['config'][k]=Path(d['config'][k])
d['profile']['phase4_config_path']=Path(d['profile']['phase4_config_path'])
d['cloud']['accepted_model_aliases']=tuple(d['cloud']['accepted_model_aliases'])
s=SourceOperations(WorkbenchConfig(**d['config']),SourceProfile(**d['profile']),CloudProfile(**d['cloud']))
assert entry.prepare(s,d['run_id'])==d['expected']
print('PREPARATION_RESTART_ZERO_DISPATCH')
''', str(restart)], capture_output=True, timeout=60,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path), 'PYTHONUTF8':'1'})
    assert child.returncode == 0, child.stderr.decode(errors='replace')
    assert service.advance_once(worker_id='ordinary-worker', processing_run_id=rid) is None
    worker = entry.frozen_worker(restarted, rid)
    binding, ctx, catalog, series = worker.output_batches.inputs(worker.get_run(rid))[0]
    segment = worker.output_batches.ledger.read(series.series_id)[1].leaves[0]
    assert binding['b1_counter_version'] == b1.COUNTER_V2
    assert len([r for r in rows(value, 'bounded_extraction_events') if r['event_type'] == prep.EVENT]) == 1
    for table in ('bounded_extraction_attempts','bounded_extraction_dispatches','bounded_extraction_outcomes','bounded_extraction_segment_results'):
        assert rows(value, table) == []
    assert worker.output_batches.ledger.read(series.series_id)[3].provider_call_count == 0
    providers = entry.providers(service, rid)
    selected = providers[output.OPERATION]
    payload = prep.frozen_payload(worker, run, binding, ctx, catalog, series, segment, selected)
    actual_body = requests.Request('POST', 'https://example.invalid', json=payload['request']).prepare().body
    assert actual_body == payload['request_wire_json'].encode('utf8')
    assert hashlib.sha256(actual_body).hexdigest() == first['wire_body_sha256']
    assert 'Outside page 1' not in actual_body.decode()
    changed = copy.deepcopy(binding); changed['native']['source_scope']['global_start'] += 1
    with pytest.raises(ValueError, match='IDENTITY_DRIFT'):
        prep.frozen_payload(worker, run, changed, ctx, catalog, series, segment, selected)
    transport = AssignedTransport(); transport.catalog, transport.segment = catalog, segment
    selected.transport = transport
    complete = entry.advance(service, rid, worker_id='explicit-b1-fixture', provider=providers)
    assert complete['stage'] == 'BOUNDED_EXTRACTION_COMPLETE', complete.get('error')
    assert complete['coverage_status'] == 'PARTIAL' and complete['source_coverage_status'] == 'NOT_ESTABLISHED'
    assert len(transport.calls) == 1 and transport.calls[0] == payload['request']
    with pytest.raises(ValueError, match='SERIES_NOT_OPEN|AFTER_ATTEMPT'):
        entry.prepare(service, rid)
    assert value['config'].knowledge_db.read_bytes() == before


@pytest.mark.parametrize('binding', [b1.BINDING, output.BINDING_VERSION])
def test_counter_selection_cannot_be_attached_to_unscoped_or_generic_input(binding):
    from test_b1_formal_contract import fixture
    value, ctx, _, _, _ = fixture()
    with pytest.raises(ValueError, match='SCOPE_COUNTER_SELECTION_MISMATCH|CONTEXT_WITHOUT_SELECTION'):
        output.piece_input(value['native'],ctx.source_sha256,'TEST_FIXTURE',1,binding_version=binding,
            b1_request_context=value['b1_request_context'] if binding==b1.BINDING else None,
            b1_counter_version=b1.COUNTER_V2)


def test_scoped_piece_and_context_cannot_escape_original_range(tmp_path, monkeypatch):
    value, run = scoped_fixture(tmp_path, monkeypatch)
    worker = entry.frozen_worker(value['service'], run['processing_run_id'])
    binding, ctx, catalog, series = worker.output_batches.inputs(run)[0]
    bad = copy.deepcopy(binding); bad['native']['source_piece']['source_text'] += 'Outside range'
    with pytest.raises(ValueError, match='SCOPE_PIECE_DRIFT'):
        output.restore_input(bad, ctx.source_sha256, run['processing_run_id'], 1)
    bad = copy.deepcopy(binding); bad['b1_request_context']['closure'][catalog.units[0].evidence_ref].append('EV_OUTSIDE_RANGE')
    with pytest.raises(ValueError, match='CONTEXT_CLOSURE_INCOMPLETE'):
        output.restore_input(bad, ctx.source_sha256, run['processing_run_id'], 1)
    assert rows(value,'bounded_extraction_attempts') == [] and rows(value,'bounded_extraction_dispatches') == []


def test_scoped_dispatch_without_preparation_never_reserves(tmp_path, monkeypatch):
    value, run = scoped_fixture(tmp_path, monkeypatch)
    providers = entry.providers(value['service'], run['processing_run_id'])
    providers[output.OPERATION].transport = lambda *a, **k: pytest.fail('MISSING_PREPARATION_MUST_NOT_SEND')
    rejected = entry.advance(value['service'], run['processing_run_id'], worker_id='explicit-fixture', provider=providers)
    assert rejected['state'] == 'BLOCKED' and rejected['error']['code'] == 'BOUNDED_EXTRACTION_FAILED'
    assert rows(value, 'bounded_extraction_attempts') == [] and rows(value, 'bounded_extraction_dispatches') == []


@pytest.mark.parametrize('field,value', [('stream',True),('thinking',{'type':'enabled'}),
    ('temperature',0.7),('messages',[{'role':'assistant','content':'unsupported'}]),('extra_field','ignored?')])
def test_counter_v2_rejects_unsupported_domain_before_executable(field, value):
    from test_b1_formal_contract import fixture
    binding, ctx, catalog, series, segment = fixture()
    request = output.segment_payload(binding, ctx, catalog, series, segment)['request']
    request[field] = value
    counter = object.__new__(b1.LocalCounter)
    counter.version = b1.COUNTER_V2
    counter.verify = lambda: None
    with pytest.raises(ValueError, match='REQUEST_DOMAIN_UNSUPPORTED'):
        counter.preflight(request)
