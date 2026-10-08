"""Disposable five-Series recovery; synthetic HTTP and authority exclusively."""
import json
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
        historical_repository_root=Path(__file__).resolve().parents[1])


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
        results = [f.result() for f in futures]
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
    with value['service'].store.connect(operator_write=True) as conn:
        conn.execute('UPDATE source_processing_runs SET fence=fence+1 WHERE processing_run_id=?', (value['run_id'],))
    with pytest.raises(SourceOperationError, match='LOSSLESS_RECOVERY_SCOPE_DRIFT'):
        authorize(value, token)
    assert len(rows(value, 'bounded_extraction_attempts')) == 5
    assert not rows(value, 'bounded_extraction_series_results')
