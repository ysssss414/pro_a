"""Offline continuation from the real previous release; synthetic research only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from pro_a import output_decomposition as output
from pro_a.evidence_binding import identity
from pro_a.workbench import lossless_compatibility as compatibility, lossless_recovery as recovery
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.extraction_retry import bounded_frozen_components
from pro_a.workbench.source_operations import SourceOperations, SourceOperationError
from series_binding_helpers import Transport, rows, synthetic_providers
from test_bounded_only_resume import resume
from test_provider_record_v4 import records, result


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))


@pytest.fixture
def historical(tmp_path):
    """Never fake the old commit/runtime/token. Run the old installed interpreter."""
    interpreter = os.environ.get('PRO_A_RELEASED_PYTHON')
    assert interpreter, 'Set PRO_A_RELEASED_PYTHON to the verified 3cb installed interpreter'
    cached = os.environ.get('PRO_A_EVIDENCE_FIXTURE')
    if cached and not hasattr(historical, '_used'):
        root = Path(cached)
        historical._used = True
    else:
        root = tmp_path/'h'
        child = subprocess.run([interpreter, '-B', str(Path(__file__).with_name('evidence_regeneration_fixture.py')), str(root)],
            capture_output=True, timeout=900, env={k:v for k,v in os.environ.items() if k != 'PYTHONPATH'})
        assert child.returncode == 0, child.stderr.decode(errors='replace')
    saved = json.loads((root/'fixture.json').read_text())
    for key in ('state_db', 'artifact_root', 'knowledge_db'):
        saved['config'][key] = Path(saved['config'][key])
    config = WorkbenchConfig(**saved['config'])
    with sqlite3.connect(config.state_db.as_uri()+'?mode=ro', uri=True) as c:
        c.row_factory = sqlite3.Row
        row = c.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (saved['run_id'],)).fetchone()
        profile, cloud, _, _ = bounded_frozen_components(config, c, row)
    service = SourceOperations(config, profile, cloud)
    package = Path(interpreter).resolve().parents[1]/'Lib/site-packages/pro_a'
    repository = Path(os.environ.get('PRO_A_HISTORY_TEST_REPOSITORY', Path(__file__).resolve().parents[1]))
    token = compatibility.qualify_evidence_regeneration(service, saved['run_id'], saved['failed_attempt_id'],
        historical_repository_root=repository, released_installed_package=package)
    return {**saved, 'config': config, 'service': service, 'token': token,
        'production_before': config.knowledge_db.read_bytes(), 'cloud_profile': cloud,
        'phase4_config': Path(saved['phase4_config'])}


def authorize(value, key='synthetic-selector-regeneration', reason='Offline synthetic exact-scope regeneration'):
    return value['service'].authorize_evidence_selector_regeneration(value['run_id'], value['failed_attempt_id'], value['token'],
        idempotency_key=key, worker_id='offline_worker', reason=reason)


def test_original_diagnostic_and_independent_request():
    ctx, catalog, _, record = records()
    _, series, segment = result(record, ctx, catalog)
    failed = deepcopy(record)
    failed['claims'] = [deepcopy(record['claims'][0]) for _ in range(26)]
    failed['node_matches'] = [deepcopy(record['node_matches'][0]) for _ in range(5)]
    for family in ('claims', 'node_matches'):
        for item in failed[family]:
            item['evidence'].update(selection_mode='RAW_SUBSPAN', selector='ABSENT_SYNTHETIC_SELECTOR')
    body = json.dumps(failed).encode()
    before = body[:]
    diagnostic = recovery.evidence_diagnostic(body, series, segment, catalog, ctx)
    assert len(diagnostic['violations']) == 31 and diagnostic['violations'][0]['path'] == '$.claims[0].evidence.selector'
    with pytest.raises(ValueError, match='EVIDENCE_SELECTOR_NOT_FOUND'):
        output.record_to_result(body.decode(), series, segment, catalog, ctx)
    assert body == before
    original = {'target': {'source': 'FROZEN'}, 'request': {'messages': [{'role': 'user', 'content': 'FROZEN'}], 'tools': ['SCHEMA']}}
    proof = {'frozen_context_sha256': 'c'*64, 'failed': {'attempt_id': 'ORIGINAL', 'request_sha256': 'a'*64, 'assigned_evidence_identity': 'b'*64}}
    saved = deepcopy(original)
    regenerated = recovery.evidence_payload(original, proof)
    assert original == saved and regenerated['request']['messages'][:-1] == original['request']['messages']
    assert regenerated['request']['tools'] == original['request']['tools']
    assert regenerated['request']['messages'][-1]['content'] == recovery.EVIDENCE_GUIDANCE
    assert regenerated['target']['regeneration_contract_version'] == recovery.EVIDENCE_REQUEST


@pytest.mark.parametrize('family', ['claims', 'node_matches'])
@pytest.mark.parametrize('mode', ['whole', 'literal', 'unassigned_text', 'cross_boundary', 'paraphrase'])
def test_original_strict_evidence_validator(family, mode):
    ctx, catalog, _, record = records()
    item = record[family][0]
    ref = item['evidence']['evidence_ref']
    unit = next(u for u in catalog.units if u.evidence_ref == ref)
    other = next(u for u in catalog.units if u.evidence_ref != ref)
    if mode == 'whole':
        item['evidence'].update(selection_mode='WHOLE_UNIT', selector='', occurrence='1')
    else:
        selector = {'literal': unit.exact_text[:5], 'unassigned_text': other.exact_text,
            'cross_boundary': unit.exact_text + other.exact_text, 'paraphrase': 'Synthetic unsupported paraphrase'}[mode]
        item['evidence'].update(selection_mode='RAW_SUBSPAN', selector=selector, occurrence='1')
    if mode in ('whole', 'literal'):
        result(record, ctx, catalog)
    else:
        with pytest.raises(ValueError, match='EVIDENCE_SELECTOR_NOT_FOUND'):
            result(record, ctx, catalog)


def test_zero_claim_and_ownership_linkage_guards_unchanged():
    ctx, catalog, _, record = records()
    empty = deepcopy(record)
    empty['claims'] = empty['relation_candidates'] = []
    result(empty, ctx, catalog)
    foreign = deepcopy(record)
    foreign['node_candidates'][0]['ownership_evidence_ref'] = 'FOREIGN'
    with pytest.raises(ValueError, match='OUTPUT_OWNERSHIP_VIOLATION'):
        result(foreign, ctx, catalog)
    foreign = deepcopy(record)
    foreign['claims'][0]['related_candidate_names'] = ['NONEXISTENT_CANDIDATE']
    with pytest.raises(ValueError):
        result(foreign, ctx, catalog)


@pytest.mark.parametrize('mode', ['foreign_ref', 'foreign_selector', 'cross_boundary'])
def test_unassigned_unit_and_true_cross_boundary_fail_closed(mode):
    from pro_a.bounded_extraction import create_extraction_series, initial_extraction_plan
    from pro_a.source_analysis_wire import build_source_evidence_catalog
    from test_source_analysis_wire import context
    ctx = context('\n'.join(f'Synthetic unique unit {i} has {i+1} products.' for i in range(17)))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_UNASSIGNED_RUN', series_version=output.OUTPUT_SERIES_VERSION)
    segment = initial_extraction_plan(series).leaves[0]
    owned = next(u for u in catalog.units if u.evidence_ref in segment.assigned_evidence_refs)
    other = next(u for u in catalog.units if u.evidence_ref not in segment.assigned_evidence_refs)
    _, _, _, record = records()
    record['claims'] = record['claims'][:1]
    record['node_matches'] = record['node_candidates'] = record['relation_candidates'] = record['source_references'] = []
    claim = record['claims'][0]
    claim.update(related_node_ids=[], related_candidate_names=[], evidence_pointer='TEXT')
    claim['evidence'] = {'evidence_ref': owned.evidence_ref, 'selection_mode': 'RAW_SUBSPAN', 'selector': other.exact_text, 'occurrence': '1'}
    record['evidence_acknowledgements'] = [{'evidence_ref': ref} for ref in segment.assigned_evidence_refs]
    if mode == 'foreign_ref':
        claim['evidence'].update(evidence_ref=other.evidence_ref, selection_mode='WHOLE_UNIT', selector='')
    elif mode == 'cross_boundary':
        following = next(u for u in catalog.units if u.source_start >= owned.source_end)
        claim['evidence']['selector'] = ctx.piece.source_text[owned.source_end-3:following.source_start+3]
        assert claim['evidence']['selector'] in ctx.piece.source_text
    with pytest.raises(ValueError, match='OUTPUT_OWNERSHIP_VIOLATION' if mode == 'foreign_ref' else 'EVIDENCE_SELECTOR_NOT_FOUND'):
        output.record_to_result(json.dumps(record), series, segment, catalog, ctx)


def test_crash_fence_concurrency_idempotency_and_full_lossless_path(historical, monkeypatch):
    value = historical
    service, token = value['service'], value['token']
    protected = {t: rows(value, t) for t in ('bounded_extraction_attempts', 'bounded_extraction_outcomes',
        'bounded_extraction_dispatches', 'bounded_extraction_segment_results', 'bounded_extraction_series_results')}
    files = {p:p.read_bytes() for p in value['config'].artifact_root.rglob('*') if p.is_file()}
    with service.store.connect(operator_write=True) as c:
        last = dict(c.execute('SELECT * FROM source_processing_events WHERE processing_run_id=? ORDER BY sequence DESC LIMIT 1', (value['run_id'],)).fetchone())
        c.execute("UPDATE source_processing_events SET event_json='{}' WHERE processing_run_id=? AND sequence=?", (value['run_id'], last['sequence']))
    with pytest.raises(ValueError, match='SOURCE_EVENT_CHAIN_MISMATCH'):
        service.output_batches.inputs(service.get_run(value['run_id']))
    with service.store.connect(operator_write=True) as c:
        c.execute('UPDATE source_processing_events SET event_json=? WHERE processing_run_id=? AND sequence=?', (last['event_json'], value['run_id'], last['sequence']))
    first_sid = token.evidence['scope']['first_aggregate']['series_id']
    old_token_path = service.output_batches.ledger._path(first_sid, 'lossless-qualification.json')
    old_bytes = old_token_path.read_bytes()
    old_token_path.write_bytes(old_bytes + b' ')
    with service.store.connect() as c, pytest.raises(ValueError, match='ARTIFACT_HASH_MISMATCH'):
        recovery.original_lossless_grant(service, c, value['run_id'])
    old_token_path.write_bytes(old_bytes)
    original_manifest = compatibility.package_manifest()
    with monkeypatch.context() as patch:
        patch.setattr(compatibility, 'package_manifest', lambda: {**original_manifest, 'analyzer.py': '0'*64})
        with pytest.raises(SourceOperationError, match='EVIDENCE_CONTINUATION_TARGET_DRIFT'):
            authorize(value)
    token.evidence['original_qualification']['resolution_identity'] = '0'*64
    with pytest.raises(SourceOperationError, match='EVIDENCE_CONTINUATION_TOKEN_DRIFT'):
        authorize(value)
    token.evidence['original_qualification']['resolution_identity'] = token.evidence['scope']['resolution_identity']
    assert token.identity == token.sealed_identity
    with service.store.connect(operator_write=True) as c:
        c.execute("UPDATE source_processing_runs SET lease_owner='other',lease_expires_at='9999' WHERE processing_run_id=?", (value['run_id'],))
    with pytest.raises(SourceOperationError, match='LEASE_BUSY'):
        authorize(value)
    with service.store.connect(operator_write=True) as c:
        c.execute('UPDATE source_processing_runs SET lease_owner=NULL,lease_expires_at=NULL,fence=fence+1 WHERE processing_run_id=?', (value['run_id'],))
    with pytest.raises(SourceOperationError, match='EVIDENCE_REGENERATION_SCOPE_DRIFT'):
        authorize(value)
    with service.store.connect(operator_write=True) as c:
        c.execute('UPDATE source_processing_runs SET fence=fence-1 WHERE processing_run_id=?', (value['run_id'],))
    for window in ('evidence_regeneration_authorized', 'evidence_regeneration_attempt_reserved', 'evidence_regeneration_frontier_reopened'):
        def fault(name):
            if name == window:
                raise RuntimeError('SYNTHETIC_CRASH')
        with monkeypatch.context() as patch:
            patch.setattr(recovery, 'checkpoint', fault)
            with pytest.raises(RuntimeError, match='SYNTHETIC_CRASH'):
                authorize(value)
        assert service.get_run(value['run_id'])['state'] == 'BLOCKED'
        for table, original in protected.items():
            assert rows(value, table) == original
    # Serialize competing writers; a busy SQLite writer is fail-closed and can
    # repeat only the identical key after the winning transaction commits.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(authorize, value) for _ in range(2)]
        answers = []
        for future in futures:
            try:
                answers.append(future.result())
            except sqlite3.OperationalError as error:
                assert error.sqlite_errorcode in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                answers.append(authorize(value))
    assert sorted(a['duplicate'] for a in answers) == [False, True]
    assert authorize(value)['duplicate']
    for key, reason in [('conflicting-key-0001', 'Offline synthetic exact-scope regeneration'), ('synthetic-selector-regeneration', 'Conflicting reason')]:
        with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'):
            authorize(value, key, reason)
    assert len(rows(value, 'bounded_extraction_attempts')) == 8
    assert len(rows(value, 'bounded_extraction_dispatches')) == 7
    assert all(p.read_bytes() == raw for p,raw in files.items())
    for table, original in protected.items():
        assert all(r in rows(value, table) for r in original)
    assert sum(r['state'] == 'PLANNED' for r in rows(value, 'bounded_extraction_segments')) == 21
    # Restoring a committed token is the normal load_worker path, with no Git.
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, 'check_output', lambda *a, **k: pytest.fail('GIT_FORBIDDEN'))
        # In a source checkout repository_commit requires Git; installed-only
        # qualification executes this assertion without that source dependency.
        if (Path(compatibility.__file__).parents[1]/'_build_identity.json').exists():
            assert recovery.load_worker(service, value['run_id']).runtime_compatibility.identity == token.identity
    first = service.output_batches.ledger.aggregate(token.evidence['scope']['first_aggregate']['series_id'])
    repeated_statement = json.loads(first['observation_ledger']['original_segment_results'][0]['wire_json'])['claims'][0]['statement']
    class DuplicateAcrossPieces(Transport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            function = response.value['choices'][0]['message']['tool_calls'][0]['function']
            record = json.loads(function['arguments'])
            record['claims'][0]['statement'] = repeated_statement
            function['arguments'] = json.dumps(record)
            return response
    transport = DuplicateAcrossPieces(mode='sparse')
    with synthetic_providers(value, transport) as providers:
        completed = resume(value, providers, key='synthetic-selector-complete', ceiling=21)
    assert completed['bounded_complete'] and len(transport.calls) == 21
    assert transport.calls[0]['messages'][-1]['content'] == recovery.EVIDENCE_GUIDANCE
    assert all(call['messages'][-1]['content'] != recovery.EVIDENCE_GUIDANCE for call in transport.calls[1:])
    assert all(p.read_bytes() == raw for p,raw in files.items())
    assert not rows(value, 'source_processing_jobs')
    bindings = service.output_batches.inputs(service.get_run(value['run_id']))
    aggregates = [service.output_batches.ledger.aggregate(b[3].series_id) for b in bindings]
    assert len(aggregates[0]['observation_ledger']['observations']) == 146
    assert all(a['source_metadata_resolution_identity'] == value['resolution']['identity'] for a in aggregates)
    # Native planning uses the same synthetic frozen pieces as the old fixture;
    # the production lossless replay and observation admission guards run intact.
    from pro_a.analyzer import Analyzer, InitialExtractionPlan, PlannedExtractionPiece
    planned = tuple(PlannedExtractionPiece(c.piece, 0, len(c.piece.source_text), (), tuple(v['native']['scoped_node_catalog']), v['native']['user_prompt']) for v,c,_,_ in bindings)
    frozen = InitialExtractionPlan(4000, 0, identity([]), planned, {}, identity({'synthetic': True}))
    monkeypatch.setattr(Analyzer, 'plan_initial_extraction', lambda *a, **k: frozen)
    with service.store.connect() as c:
        original_checkpoint = json.loads(c.execute("SELECT checkpoint_json FROM source_cloud_inputs WHERE processing_run_id=? AND operation_kind='SOURCE_ANALYSIS_PIECE' ORDER BY ordinal LIMIT 1", (value['run_id'],)).fetchone()[0])
    synthetic_plan = {'run_id': original_checkpoint['run_id'], 'source_id': token.evidence['scope']['source_id'],
        'source_sha256': bindings[0][1].source_sha256, 'plan': {'initial_extraction_plan_sha256': original_checkpoint['plan_sha256']},
        'pieces': [v['native'] for v,_,_,_ in bindings]}
    monkeypatch.setattr('pro_a.workbench.source_operations.plan_external_source_analysis', lambda *a, **k: synthetic_plan)
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', lambda *a, **k: pytest.fail('PROVIDER_FORBIDDEN'))
    final = service.advance_once(worker_id='synthetic_native', processing_run_id=value['run_id'], lease_seconds=3660)
    assert final['state'] == 'BLOCKED' and final['error']['code'] == 'BLOCKED_PENDING_REVIEW'
    assert not rows(value, 'source_processing_jobs')
    assert value['config'].knowledge_db.read_bytes() == value['production_before']


@pytest.mark.parametrize('mode', ['malformed', 'unknown', 'raw_crash'])
def test_new_failure_stops_and_never_grants_attempt_three(historical, monkeypatch, mode):
    value = historical
    def after_commit(name):
        if name == 'evidence_regeneration_committed':
            raise RuntimeError('SYNTHETIC_AFTER_COMMIT')
    with monkeypatch.context() as patch:
        patch.setattr(recovery, 'checkpoint', after_commit)
        with pytest.raises(RuntimeError, match='SYNTHETIC_AFTER_COMMIT'):
            authorize(value)
    assert authorize(value)['duplicate']
    transport = Transport(mode='sparse' if mode == 'raw_crash' else mode)
    with synthetic_providers(value, transport) as providers:
        if mode == 'raw_crash':
            from pro_a.workbench import bounded_extraction_persistence as persistence
            def raw_crash(name):
                if name == 'raw_artifact_durable':
                    raise RuntimeError('SYNTHETIC_RAW_DURABLE_CRASH')
            with monkeypatch.context() as patch:
                patch.setattr(persistence, 'checkpoint', raw_crash)
                with pytest.raises(RuntimeError, match='SYNTHETIC_RAW_DURABLE_CRASH'):
                    resume(value, providers, key='synthetic-raw-crash', ceiling=1)
            assert len(transport.calls) == 1 and len(rows(value, 'bounded_extraction_segment_results')) == 6
            attempt_id = value['token'].evidence['new_request']['attempt_id']
            sid = value['token'].evidence['scope']['failed']['series_id']
            assert value['service'].output_batches.ledger._path(sid, attempt_id + '.raw.json').is_file()
            assert not any(r['attempt_id'] == attempt_id for r in rows(value, 'bounded_extraction_outcomes'))
            recovered = resume(value, providers, key='synthetic-raw-reconcile', ceiling=0)
            assert recovered['new_provider_calls'] == 0 and len(transport.calls) == 1
            assert len(rows(value, 'bounded_extraction_segment_results')) == 7
            assert not rows(value, 'source_processing_jobs')
            return
        result = resume(value, providers, key='synthetic-selector-failure', ceiling=21)
        assert not result.get('bounded_complete') and len(transport.calls) == 1
        again = resume(value, providers, key='synthetic-selector-no-auto-retry', ceiling=21)
        assert again['new_provider_calls'] == 0 and len(transport.calls) == 1
    assert len(rows(value, 'bounded_extraction_attempts')) == 8
    assert len(rows(value, 'bounded_extraction_segment_results')) == 6
    assert not rows(value, 'source_processing_jobs')
    assert max(a['attempt_number'] for a in rows(value, 'bounded_extraction_attempts')) == 2
