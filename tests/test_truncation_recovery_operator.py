"""Zero-network operator qualification against the real five-Series shape."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from pro_a.workbench.bounded_extraction_store import _event
from pro_a.workbench.source_operations import SourceOperationError
from pro_a.workbench.truncation_recovery import assess_truncation_recovery, contract
from test_bounded_only_resume import topology, resume, events, tripwires
from series_binding_helpers import Transport, rows, synthetic_providers, request_parts


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))


def stopped(tmp_path, monkeypatch, counts=(65, 81, 81, 81, 49), *, mode='truncated', failure_call=2):
    value = topology(tmp_path, monkeypatch, counts=counts, accepted_retry=False)
    class FailureTransport(Transport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            if mode == 'semantic' and len(self.calls) == failure_call:
                record = json.loads(response.value['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
                record['evidence_acknowledgements'][0]['evidence_ref'] = 'EV_FOREIGN'
                response.value['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = json.dumps(record)
            return response
    transport = FailureTransport(mode=lambda _target, n: mode if n == failure_call else None)
    with synthetic_providers(value, transport) as providers:
        result = resume(value, providers, key='synthetic-truncation-stop', ceiling=100)
        assert not result.get('bounded_complete')
        assert len(transport.calls) == failure_call
        assert providers['SEMANTIC_DECOMPOSITION'].call_count == 0
    value['attempt_id'] = rows(value, 'bounded_extraction_attempts')[-1]['attempt_id']
    return value


def recover(value, *, key='explicit-capacity-recovery-0001', worker='recovery_worker', reason='Confirmed durable output truncation.'):
    return value['service'].recover_truncated_bounded_extraction(value['run_id'], value['attempt_id'],
        worker_id=worker, idempotency_key=key, reason=reason)


def snapshot(value):
    tables = ('source_processing_runs', 'source_processing_events', 'bounded_extraction_series',
              'bounded_extraction_segments', 'bounded_extraction_attempts', 'bounded_extraction_dispatches',
              'bounded_extraction_outcomes', 'bounded_extraction_segment_results', 'bounded_extraction_events')
    return {t: rows(value, t) for t in tables}


def test_real_topology_atomic_recovery_and_later_fake_execution(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    before = snapshot(value)
    raw = {p: p.read_bytes() for p in value['config'].artifact_root.rglob('*.raw.json')}
    database_before = value['config'].state_db.read_bytes()
    assessment = assess_truncation_recovery(value['service'], value['run_id'], value['attempt_id'])
    assert len(assessment['reopen']) == 25
    assert assessment['child_assigned_ref_counts'] == [8, 8]
    assert value['config'].state_db.read_bytes() == database_before
    result = recover(value)
    assert result['provider_calls'] == 0 and not result['duplicate']
    assert (result['active_leaves_before'], result['active_leaves_after'], result['pending_after_recovery']) == (27, 28, 27)
    assert result['child_segment_ids'] == assessment['child_segment_ids']
    after = snapshot(value)
    for table in ('bounded_extraction_attempts', 'bounded_extraction_dispatches', 'bounded_extraction_outcomes', 'bounded_extraction_segment_results'):
        assert after[table] == before[table]
    succeeded = next(r for r in before['bounded_extraction_segments'] if r['state'] == 'SUCCEEDED_COMPLETE')
    assert next(r for r in after['bounded_extraction_segments'] if r['segment_id'] == succeeded['segment_id']) == succeeded
    assert sum(r['state'] == 'SUPERSEDED_BY_CHILDREN' for r in after['bounded_extraction_segments']) == 1
    assert sum(r['state'] == 'PLANNED' for r in after['bounded_extraction_segments']) == 27
    assert all(r in after['bounded_extraction_events'] for r in before['bounded_extraction_events'])
    assert all(p.read_bytes() == content for p, content in raw.items())
    assert len(events(value, 'TRUNCATION_RECOVERY_AUTHORIZED')) == 1
    assert len(events(value, 'TRUNCATED_PARENT_SUBDIVIDED')) == 1
    assert len(events(value, 'UPSTREAM_FAIL_CLOSED_REOPENED')) == 1
    bindings = value['service'].output_batches.inputs(value['service'].get_run(value['run_id']))
    series = next(b[3] for b in bindings if b[3].series_id == result['series_id'])
    _, _, state, usage = value['service'].output_batches.ledger.read(series.series_id)
    assert state['provider_call_reservations'] == usage.provider_call_count == 2
    assert state['output_liability'] == usage.output_token_liability == 12050
    with monkeypatch.context() as execution:
        tripwires(execution)
        transport = Transport(mode='empty')
        with synthetic_providers(value, transport) as providers:
            finished = resume(value, providers, key='synthetic-after-explicit-recovery', ceiling=27)
            assert finished['bounded_complete'] and len(transport.calls) == 27
            assert providers['SEMANTIC_DECOMPOSITION'].call_count == 0
        dispatched = [request_parts(request)[0] for request in transport.calls]
        assert [t['segment_id'] for t in dispatched[:2]] == result['child_segment_ids']
        assert all(t['segment_id'] not in (succeeded['segment_id'], result['parent_segment_id']) for t in dispatched)
        contexts = [re.sub(r'\[/?EV_[A-Z0-9]+\]', '', request_parts(call)[1]) for call in transport.calls[:2]]
        assert contexts[0] == contexts[1]
    assert len(rows(value, 'bounded_extraction_series_results')) == 5
    assert not rows(value, 'source_processing_jobs')
    assert value['config'].knowledge_db.read_bytes() == value['production_before']


def test_idempotency_and_concurrent_workers(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    barrier = threading.Barrier(2)
    def action(index):
        barrier.wait(timeout=15)
        return recover(value, worker='recovery_worker_' + str(index))
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(action, range(2)))
    assert sorted(r['duplicate'] for r in results) == [False, True]
    assert results[0]['child_segment_ids'] == results[1]['child_segment_ids']
    assert len(rows(value, 'bounded_extraction_segments')) == 5
    count = len(rows(value, 'bounded_extraction_events'))
    assert recover(value)['duplicate']
    assert len(rows(value, 'bounded_extraction_events')) == count
    with pytest.raises(SourceOperationError, match='ALREADY_RECOVERED'):
        recover(value, key='different-action-same-parent')
    with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'):
        recover(value, reason='Changed reason.')


def test_child_retruncation_stops_then_explicit_eight_to_four(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    first = recover(value)
    with monkeypatch.context() as execution:
        tripwires(execution)
        transport = Transport(mode='truncated')
        with synthetic_providers(value, transport) as providers:
            result = resume(value, providers, key='child-truncation-new-action', ceiling=10)
        assert result['status'] == 'STOP_ON_FIRST_NEW_FAILURE' and len(transport.calls) == 1
    assert len(rows(value, 'bounded_extraction_segments')) == 5
    value['attempt_id'] = rows(value, 'bounded_extraction_attempts')[-1]['attempt_id']
    second = recover(value, key='second-explicit-capacity-recovery')
    assert second['child_assigned_ref_counts'] == [4, 4]
    assert second['parent_segment_id'] == first['child_segment_ids'][0]
    assert len(rows(value, 'bounded_extraction_dispatches')) == 3


@pytest.mark.parametrize('mode', ['malformed', 'unknown', 'semantic'])
def test_nontruncation_rejected_without_state_changes(tmp_path, monkeypatch, mode):
    value = stopped(tmp_path, monkeypatch, counts=(33,), mode=mode)
    before = snapshot(value)
    with pytest.raises(SourceOperationError, match='NOT_TRUNCATION_RECOVERY_ELIGIBLE'):
        recover(value)
    assert snapshot(value) == before


@pytest.mark.parametrize('reason', ['', ' ', ' leading', 'line\nbreak', 'x' * 1001])
def test_invalid_reason_rejected(tmp_path, monkeypatch, reason):
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    before = snapshot(value)
    with pytest.raises(SourceOperationError, match='INVALID_RECOVERY_REASON'):
        recover(value, reason=reason)
    assert snapshot(value) == before


def test_one_ref_truncation_fails_closed(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch, counts=(1,), failure_call=1)
    before = snapshot(value)
    with pytest.raises(ValueError, match='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'):
        recover(value)
    assert snapshot(value) == before


@pytest.mark.parametrize('restriction', ['depth', 'leaf', 'calls', 'liability'])
def test_frozen_policy_limits_fail_closed(tmp_path, monkeypatch, restriction):
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    import pro_a.workbench.truncation_recovery as module
    original = module._worker
    def constrained(*args):
        worker = original(*args)
        load = worker.output_batches.ledger._load
        def limited(connection, sid):
            series, plan, state, usage = load(connection, sid)
            if restriction == 'calls':
                state = {**state, 'provider_call_reservations': series.budget.max_provider_calls}
            if restriction == 'liability':
                state = {**state, 'output_liability': series.budget.max_cumulative_output_tokens}
            return series, plan, state, usage
        worker.output_batches.ledger._load = limited
        return worker
    # Budget limits are tested directly at the authority seam below; the full
    # operator also requires the exact frozen Series identity.
    if restriction in ('calls', 'liability'):
        monkeypatch.setattr(module, '_worker', constrained)
        with pytest.raises(SourceOperationError, match='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'):
            recover(value)
    else:
        from pro_a.bounded_extraction import subdivide_extraction_plan, SeriesBudget
        from test_bounded_extraction import fixture
        _, _, series, plan = fixture(16 if restriction == 'depth' else 33,
            SeriesBudget(max_subdivision_depth=1) if restriction == 'depth' else SeriesBudget(max_leaf_segments=3))
        if restriction == 'depth':
            plan = subdivide_extraction_plan(series, plan, plan.leaves[0].segment_id)
        with pytest.raises(ValueError, match='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'):
            subdivide_extraction_plan(series, plan, plan.leaves[0].segment_id)


def test_unrelated_or_manual_upstream_state_is_not_reopened(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch, counts=(49,))
    unattempted = rows(value, 'bounded_extraction_segments')[-1]
    with value['service'].store.connect(operator_write=True) as c:
        c.execute('BEGIN IMMEDIATE')
        _event(c, unattempted['series_id'], 'SEGMENT_MANUALLY_BLOCKED', segment_id=unattempted['segment_id'])
    before = snapshot(value)
    with pytest.raises(SourceOperationError, match='NOT_TRUNCATION_RECOVERY_ELIGIBLE'):
        recover(value)
    assert snapshot(value) == before


CRASH_WINDOWS = ['truncation_recovery_authorized', 'subdivision_parent_superseded',
                 'subdivision_child_inserted', 'truncation_recovery_frontier_incremented',
                 'truncation_recovery_upstream_reopened', 'truncation_recovery_before_run_restored',
                 'truncation_recovery_committed']


@pytest.mark.parametrize('window', CRASH_WINDOWS)
def test_hard_crash_is_atomic_in_fresh_process(tmp_path, monkeypatch, window):
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    before = snapshot(value)
    document = {'config': asdict(value['config']), 'phase4_config': str(value['phase4_config']),
                'run_id': value['run_id'], 'attempt_id': value['attempt_id']}
    path = tmp_path / 'synthetic-recovery-input.json'
    path.write_text(json.dumps(document, default=str), encoding='utf-8')
    bootstrap = '''
import json,os,socket,sys
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench import bounded_extraction_persistence as p
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN'))
v=json.loads(Path(sys.argv[1]).read_text())
for k in ('knowledge_db','state_db','artifact_root'):v['config'][k]=Path(v['config'][k])
s=SourceOperations(WorkbenchConfig(**v['config']),SourceProfile(Path(v['phase4_config'])),CloudProfile('deepseek','deepseek-flash'))
def recover():return s.recover_truncated_bounded_extraction(v['run_id'],v['attempt_id'],worker_id='hard_crash_worker',idempotency_key='hard-crash-recovery-action',reason='Confirmed durable output truncation.')
'''
    crash = bootstrap + "\ndef fault(name):\n if name==sys.argv[2]:os._exit(73)\np.checkpoint=fault\nrecover()\n"
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).parent))), 'PYTHONDONTWRITEBYTECODE': '1'}
    child = subprocess.run([sys.executable, '-c', crash, str(path), window], env=env, capture_output=True, timeout=60)
    assert child.returncode == 73, child.stderr.decode(errors='replace')
    if window != 'truncation_recovery_committed':
        assert snapshot(value) == before
    recovery = subprocess.run([sys.executable, '-c', bootstrap + "\nr=recover();assert r['status']=='RECOVERED' and r['provider_calls']==0\n", str(path)], env=env, capture_output=True, timeout=60)
    assert recovery.returncode == 0, recovery.stderr.decode(errors='replace')
    assert len(rows(value, 'bounded_extraction_segments')) == 5
    assert len(rows(value, 'bounded_extraction_dispatches')) == 2
    assert len(events(value, 'TRUNCATED_PARENT_SUBDIVIDED')) == 1


def test_contract_and_public_surface_remain_bounded(tmp_path, monkeypatch):
    from pro_a.workbench.bounded_resume import contract as bounded_contract
    assert contract()['provider_calls'] == 0 and contract()['subdivision_count_per_action'] == 1
    assert not bounded_contract()['new_subdivision_allowed'] and not bounded_contract()['automatic_retry']
    package = Path(__import__('pro_a').__file__).resolve().parent
    for name in ('workbench/api.py', 'mcp/server.py', 'mcp/service.py'):
        assert 'recover_truncated_bounded_extraction' not in (package / name).read_text(encoding='utf-8')


def test_cross_release_truncation_requires_exact_scope_token_then_recovers(tmp_path, monkeypatch):
    import pro_a.phase4_orchestration as native
    from pro_a.cloud_contract import digest
    from pro_a.workbench import cloud_jobs, retry_compatibility as compatibility
    from pro_a.workbench.truncation_recovery import assess_truncation_recovery_compatibility
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    target = {**value['service'].jobs.current_runtime(), 'git_sha': 'f' * 40}
    target['runtime_sha256'] = digest({k: v for k, v in target.items() if k != 'runtime_sha256'})
    target_native = {**native._runtime(), 'repository_commit': 'f' * 40}
    monkeypatch.setattr(cloud_jobs, 'runtime_identity', lambda *_a, **_k: target)
    monkeypatch.setattr(native, '_runtime', lambda: target_native)
    monkeypatch.setattr(compatibility, 'native_runtime', lambda: target_native)
    before = snapshot(value)
    with pytest.raises(SourceOperationError, match='RETRY_RUNTIME_INCOMPATIBLE'):
        recover(value)
    assert snapshot(value) == before
    ordinary = compatibility.assess_bounded_retry_compatibility(value['config'], value['run_id'], value['attempt_id'], persist=False)
    assert ordinary['status'] == 'BLOCKED'
    assessment = assess_truncation_recovery_compatibility(value['config'], value['run_id'], value['attempt_id'], persist=False)
    assert assessment['status'] == 'QUALIFIED', assessment
    assert snapshot(value) == before
    assert 'durable_truncation' in assessment['dimensions']
    assert 'malformed_json_syntax_only' not in assessment['dimensions']
    persisted = assess_truncation_recovery_compatibility(value['config'], value['run_id'], value['attempt_id'], persist=True)
    assert persisted['status'] == 'QUALIFIED'
    result = recover(value)
    assert result['child_assigned_ref_counts'] == [8, 8]
    with monkeypatch.context() as execution:
        tripwires(execution)
        transport = Transport(mode='empty')
        with synthetic_providers(value, transport) as providers:
            assert resume(value, providers, key='cross-release-after-explicit-recovery', ceiling=3)['bounded_complete']
    assert len(transport.calls) == 3 and not rows(value, 'source_processing_jobs')


def test_recovery_does_not_normalize_changed_research_or_provider_semantics():
    from pro_a.workbench import retry_compatibility as compatibility
    package = Path(compatibility.__file__).resolve().parent.parent
    for name, old, new in (
        ('workbench/bounded_extraction_store.py', b'"DURABLE_TRUNCATION_REQUIRED"', b'"CHANGED_TRUNCATION"'),
        ('bounded_extraction.py', b'(parent.range_start + parent.range_end) // 2', b'parent.range_start + 1'),
        ('output_decomposition.py', b"'max_tokens':12000", b"'max_tokens':24000"),
    ):
        source = (package / name).read_bytes()
        assert old in source
        assert compatibility._ast_sha256(source, None, name=name) != compatibility._ast_sha256(source.replace(old, new), None, name=name)
