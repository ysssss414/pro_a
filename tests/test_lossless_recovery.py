"""Disposable five-Series recovery; synthetic HTTP and authority exclusively."""
import json
import sqlite3
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pro_a.workbench.lossless_recovery import assessment
from pro_a.workbench.lossless_compatibility import qualify_recovery
from pro_a.workbench.source_operations import SourceOperationError
from test_lossless_aggregate import synthetic_authority
from test_bounded_only_resume import topology, resume
from series_binding_helpers import Transport, rows, synthetic_providers


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))


class ConflictingMetadata(Transport):
    def __init__(self):
        super().__init__(mode='sparse')

    def __call__(self, *args, **kwargs):
        response = super().__call__(*args, **kwargs)
        function = response.value['choices'][0]['message']['tool_calls'][0]['function']
        record = json.loads(function['arguments'])
        record['source_metadata']['author'] = 'SYNTHETIC_AUTHOR_' + str(len(self.calls))
        record['source_metadata']['summary'] = 'SYNTHETIC_SUMMARY_' + str(len(self.calls))
        function['arguments'] = json.dumps(record)
        return response


def stopped(tmp_path, monkeypatch):
    value = topology(tmp_path, monkeypatch, accepted_retry=False)
    transport = ConflictingMetadata()
    with synthetic_providers(value, transport) as providers:
        resume(value, providers, key='lossless-synthetic-stop', ceiling=5)
    run = value['service'].get_run(value['run_id'])
    assert run['state'] == 'BLOCKED' and run['error']['code'] == 'SOURCE_METADATA_CONFLICT'
    assert len(transport.calls) == 5
    bindings = value['service'].output_batches.inputs(run)
    with value['service'].store.connect() as conn:
        proof = assessment(value['service'], conn, value['run_id'], bindings)
    value['resolution'] = synthetic_authority(proof['authority_scope'])
    return value


def qualified(value):
    return qualify_recovery(value['service'], value['run_id'], value['resolution'],
        historical_repository_root=Path(os.environ.get('PRO_A_HISTORY_TEST_REPOSITORY', Path(__file__).resolve().parents[1])))


def authorize(value, token, key='lossless-offline-recovery'):
    return value['service'].authorize_lossless_aggregate_recovery(value['run_id'], value['resolution'],
        token, idempotency_key=key, worker_id='synthetic_worker', reason='Synthetic offline recovery only')


def test_zero_call_recovery_preserves_accepted_and_reopens_only_22(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    token = qualified(value)
    originals = {table: rows(value, table) for table in ('bounded_extraction_attempts',
        'bounded_extraction_outcomes', 'bounded_extraction_segment_results', 'bounded_extraction_dispatches')}
    recovered = authorize(value, token)
    assert recovered['provider_calls'] == 0 and recovered['accepted_preserved'] == 5
    assert recovered['unopened_reopened'] == 22
    assert authorize(value, token)['duplicate']
    for table, original in originals.items():
        assert rows(value, table) == original
    segments = rows(value, 'bounded_extraction_segments')
    assert sum(s['state'] == 'PLANNED' for s in segments) == 22
    assert sum(s['state'] == 'SUCCEEDED_COMPLETE' for s in segments) == 5
    assert not rows(value, 'source_processing_jobs')
    assert value['config'].knowledge_db.read_bytes() == value['production_before']


def test_process_death_after_aggregate_publication_is_recoverable(tmp_path, monkeypatch):
    import subprocess
    import sys
    from dataclasses import asdict
    value = stopped(tmp_path, monkeypatch)
    token = qualified(value)
    document = {'config': asdict(value['config']), 'run_id': value['run_id'],
        'phase4_config': str(value['phase4_config']), 'resolution': value['resolution'],
        'qualification': token.evidence, 'qualification_identity': token.identity}
    path = tmp_path/'synthetic-lossless-worker.json'
    path.write_text(json.dumps(document, default=str), encoding='utf-8')
    script = '''
import json, os, socket, sys
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations, SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.lossless_compatibility import restore_token
from pro_a.workbench import lossless_runtime
socket.socket.connect=lambda *a, **k: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN'))
v=json.loads(Path(sys.argv[1]).read_text())
for k in ('knowledge_db','state_db','artifact_root'): v['config'][k]=Path(v['config'][k])
s=SourceOperations(WorkbenchConfig(**v['config']), SourceProfile(Path(v['phase4_config'])), CloudProfile('deepseek','deepseek-flash'))
q=restore_token(v['qualification'], v['qualification_identity'])
def fault(name):
    if name=='lossless_aggregate_artifact_durable': os._exit(73)
lossless_runtime.checkpoint=fault
s.authorize_lossless_aggregate_recovery(v['run_id'], v['resolution'], q,
    idempotency_key='lossless-offline-recovery', worker_id='synthetic_worker', reason='Synthetic offline recovery only')
'''
    child = subprocess.run([sys.executable, '-B', '-c', script, str(path)],
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, timeout=300)
    assert child.returncode == 73, child.stderr.decode(errors='replace')
    assert value['service'].get_run(value['run_id'])['state'] == 'BLOCKED'
    assert not rows(value, 'bounded_extraction_series_results')
    assert authorize(value, token)['accepted_preserved'] == 5
    assert len(rows(value, 'bounded_extraction_attempts')) == 5
    with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'):
        authorize(value, token, 'lossless-different-key')


def test_transaction_crash_windows_and_concurrent_idempotency(tmp_path, monkeypatch):
    from pro_a.workbench import lossless_recovery, lossless_runtime
    value = stopped(tmp_path, monkeypatch)
    token = qualified(value)
    originals = rows(value, 'bounded_extraction_segment_results')
    for window in ('lossless_recovery_authorized', 'lossless_aggregate_artifact_durable',
                   'lossless_recovery_first_aggregate', 'lossless_recovery_frontier_reopened'):
        def crash(name):
            if name == window:
                raise RuntimeError('SYNTHETIC_CRASH')
        monkeypatch.setattr(lossless_recovery, 'checkpoint', crash)
        monkeypatch.setattr(lossless_runtime, 'checkpoint', crash)
        with pytest.raises(RuntimeError, match='SYNTHETIC_CRASH'):
            authorize(value, token)
        assert value['service'].get_run(value['run_id'])['state'] == 'BLOCKED'
        assert rows(value, 'bounded_extraction_segment_results') == originals
        assert len(rows(value, 'bounded_extraction_attempts')) == 5
    monkeypatch.setattr(lossless_recovery, 'checkpoint', lambda _name: None)
    monkeypatch.setattr(lossless_runtime, 'checkpoint', lambda _name: None)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(authorize, value, token) for _ in range(2)]
        results = []
        busy = 0
        for future in futures:
            try:
                results.append(future.result())
            except sqlite3.OperationalError as error:
                # Existing SQLite writer timeout is fail-closed; the explicit
                # same-key retry observes the single committed recovery.
                assert error.sqlite_errorcode in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                busy += 1
    results.extend(authorize(value, token) for _ in range(busy))
    assert sorted(r['duplicate'] for r in results) == [False, True]
    assert len(rows(value, 'bounded_extraction_attempts')) == 5
    assert sum(r['state'] == 'PLANNED' for r in rows(value, 'bounded_extraction_segments')) == 22


def test_unresolved_metadata_and_stale_run_fence_rejected(tmp_path, monkeypatch):
    from pro_a.source_metadata_authority import candidate_resolution, MetadataAuthorityError
    value = stopped(tmp_path, monkeypatch)
    unresolved = candidate_resolution(value['resolution']['scope'], [])
    with pytest.raises(MetadataAuthorityError, match='NEEDS_HUMAN_RESOLUTION'):
        qualify_recovery(value['service'], value['run_id'], unresolved,
            historical_repository_root=Path(__file__).resolve().parents[1])
    token = qualified(value)
    with pytest.raises(SourceOperationError, match='LOSSLESS_QUALIFICATION_REQUIRED'):
        authorize(value, True)
    from pro_a.workbench import lossless_compatibility
    original = lossless_compatibility.package_manifest()
    with monkeypatch.context() as patch:
        patch.setattr(lossless_compatibility, 'package_manifest', lambda: {**original, 'analyzer.py': '0'*64})
        with pytest.raises(SourceOperationError, match='LOSSLESS_QUALIFICATION_TARGET_DRIFT'):
            authorize(value, token)
    with value['service'].store.connect(operator_write=True) as conn:
        conn.execute('UPDATE source_processing_runs SET fence=fence+1 WHERE processing_run_id=?', (value['run_id'],))
    with pytest.raises(SourceOperationError, match='LOSSLESS_RECOVERY_SCOPE_DRIFT'):
        authorize(value, token)
    assert len(rows(value, 'bounded_extraction_attempts')) == 5
    assert not rows(value, 'bounded_extraction_series_results')


def test_historical_git_and_installed_byte_evidence_are_required(monkeypatch):
    from pro_a.workbench import lossless_compatibility
    root = Path(os.environ.get('PRO_A_HISTORY_TEST_REPOSITORY', Path(__file__).resolve().parents[1]))
    evidence = lossless_compatibility.git_evidence(root)
    assert evidence['native_and_research_bytes_unchanged']
    assert set(evidence['changed_existing_modules']) <= lossless_compatibility.CHANGED
    original = lossless_compatibility.package_manifest()
    monkeypatch.setattr(lossless_compatibility, 'package_manifest', lambda: {**original, 'analyzer.py': '0'*64})
    with pytest.raises(SourceOperationError, match='TARGET_GIT_TREE_BYTE_MISMATCH'):
        lossless_compatibility.git_evidence(root)


def test_remaining_22_synthetic_results_replay_all_series_and_block_registration(tmp_path, monkeypatch):
    from pro_a.analyzer import Analyzer, InitialExtractionPlan, PlannedExtractionPiece
    from pro_a.evidence_binding import identity
    from pro_a.workbench.lossless_runtime import REVIEW_DURABLE
    value = stopped(tmp_path, monkeypatch)
    token = qualified(value)
    authorize(value, token)
    class DuplicateAcrossPieces(Transport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            function = response.value['choices'][0]['message']['tool_calls'][0]['function']
            record = json.loads(function['arguments'])
            record['claims'][0]['statement'] = 'Synthetic Company product 1-0 has 1 units.'
            function['arguments'] = json.dumps(record)
            return response
    transport = DuplicateAcrossPieces(mode='sparse')
    with synthetic_providers(value, transport) as providers:
        complete = resume(value, providers, key='SYNTHETIC_REMAINING_22', ceiling=22)
    assert len(transport.calls) == 22 and complete['pending_segments'] == 0
    service = value['service']
    bindings = service.output_batches.inputs(service.get_run(value['run_id']))
    documents = [service.output_batches.ledger.aggregate(b[3].series_id) for b in bindings]
    assert len(documents) == 5 and sum(len(d['observation_ledger']['observations']) for d in documents) == 27
    planned = tuple(PlannedExtractionPiece(c.piece, 0, len(c.piece.source_text), (), (), v['native']['user_prompt'])
        for v, c, _, _ in bindings)
    frozen = InitialExtractionPlan(4000, 0, identity([]), planned, {}, identity({'synthetic': True}))
    monkeypatch.setattr(Analyzer, 'plan_initial_extraction', lambda *a, **k: frozen)
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', lambda *a, **k: pytest.fail('PROVIDER_FORBIDDEN'))
    result = service.advance_once(worker_id='synthetic_native', processing_run_id=value['run_id'], lease_seconds=3660)
    assert result['state'] == 'BLOCKED' and result['error']['code'] == 'BLOCKED_PENDING_REVIEW'
    assert not rows(value, 'source_processing_jobs')
    events = [json.loads(r['event_json']) for r in rows(value, 'source_processing_events') if r['event_type'] == REVIEW_DURABLE]
    assert len(events) == 1
    review = json.loads(service.artifacts.resolve(events[0]['artifact_relative']).read_text())
    assert len(review['ledger']['series_ledgers']) == 5
    assert sum(len(g['observation_ids']) for g in review['projection']['groups']) == 27
    assert review['production_admission'] == 'NOT_AUTHORIZED'
    assert value['config'].knowledge_db.read_bytes() == value['production_before']
