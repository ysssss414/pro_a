"""Versioned regeneration qualification, using synthetic transport exclusively."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import stat
import sys
import threading

import pytest

from pro_a import output_decomposition as output
from pro_a.workbench import bounded_extraction_persistence as persistence
from pro_a.workbench import strict_recovery as strict
from pro_a.workbench.source_operations import SourceOperationError
from test_bounded_only_resume import topology, resume, events, tripwires
from test_truncation_recovery_operator import snapshot
from series_binding_helpers import Transport, rows, synthetic_providers, request_parts

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))

class InvalidOutput(Transport):
    def __init__(self, mode='strict', *, call=2):
        super().__init__(mode=lambda _target, n: mode if n == call and mode in ('truncated', 'unknown', 'malformed') else None)
        self.failure_mode, self.failure_call = mode, call

    def __call__(self, *args, **kwargs):
        response = super().__call__(*args, **kwargs)
        if len(self.calls) != self.failure_call or self.failure_mode in ('truncated', 'unknown', 'malformed'):
            return response
        if self.failure_mode == 'http':
            response.status_code = 503
            return response
        args = response.value['choices'][0]['message']['tool_calls'][0]['function']
        record = json.loads(args['arguments'])
        if self.failure_mode != 'references_only':
            record['node_candidates'][0]['cross_source_or_node_value'] = 'TRUE'
        if self.failure_mode != 'variant_only':
            record['claims'][0]['related_candidate_names'] = ['Synthetic absent candidate']
        if self.failure_mode == 'evidence_ack':
            record['evidence_acknowledgements'][0]['evidence_ref'] = 'EV_FOREIGN'
        elif self.failure_mode == 'binding':
            record['claims'][0]['evidence'].update(selection_mode='RAW_SUBSPAN', selector='Synthetic absent selector')
        elif self.failure_mode == 'ownership':
            record['node_candidates'][0]['ownership_evidence_ref'] = 'EV_FOREIGN'
        elif self.failure_mode == 'event_binding':
            event = json.loads(json.dumps(record['node_candidates'][0]))
            event.update(canonical_name='Synthetic Event', primary_type='Event', cross_source_or_node_value='FALSE')
            record['node_candidates'].append(event)
        args['arguments'] = json.dumps(record)
        return response

def stopped(tmp_path, monkeypatch, *, counts=(33,), mode='strict'):
    value = topology(tmp_path, monkeypatch, counts=counts, accepted_retry=False)
    with synthetic_providers(value, InvalidOutput(mode)) as providers:
        result = resume(value, providers, key='strict-synthetic-initial-stop', ceiling=100)
        assert not result.get('bounded_complete')
        assert len(providers[output.OPERATION].transport.calls) == 2
        assert providers['SEMANTIC_DECOMPOSITION'].call_count == 0
    value['attempt_id'] = rows(value, 'bounded_extraction_attempts')[-1]['attempt_id']
    return value

def authorize(value, *, key='strict-explicit-recovery-0001', worker='strict_worker', reason='Versioned strict output regeneration.'):
    return value['service'].authorize_strict_same_run_recovery(value['run_id'], value['attempt_id'],
        worker_id=worker, idempotency_key=key, reason=reason)

def test_complete_topology_preserves_history_and_accepts_only_fresh_output(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch, counts=(65,81,81,81,49))
    before = snapshot(value)
    original_files = {p: p.read_bytes() for p in value['config'].artifact_root.rglob('*') if p.is_file()}
    uncalled = [s for s in before['bounded_extraction_segments'] if not any(a['segment_id'] == s['segment_id'] for a in before['bounded_extraction_attempts'])]
    result = authorize(value)
    assert result['provider_calls'] == 0 and result['new_attempt_number'] == 2
    assert result['upstream_unattempted_count'] == len(uncalled)
    after = snapshot(value)
    for table in ('bounded_extraction_attempts', 'bounded_extraction_dispatches', 'bounded_extraction_outcomes', 'bounded_extraction_segment_results'):
        assert all(r in after[table] for r in before[table])
    succeeded = next(s for s in before['bounded_extraction_segments'] if s['state'] == 'SUCCEEDED_COMPLETE')
    assert succeeded in after['bounded_extraction_segments']
    assert all(p.read_bytes() == content for p, content in original_files.items())
    assert len(after['bounded_extraction_attempts']) == 3 and len(after['bounded_extraction_dispatches']) == 2
    old = before['bounded_extraction_attempts'][-1]
    new = after['bounded_extraction_attempts'][-1]
    request = json.loads(new['request_json'])
    assert request['original_request_sha256'] == old['request_sha256']
    assert request['regeneration_contract_version'] == strict.REQUEST_VERSION
    assert request['payload_sha256'] != json.loads(old['request_json'])['payload_sha256']
    grants = [json.loads(e['event_json']) for e in events(value, strict.AUTHORIZED_RECOVERY)]
    assert len(grants) == 1
    sid = grants[0]['series_id']
    ledger = value['service'].output_batches.ledger
    _, _, state, usage = ledger.read(sid)
    assert state['provider_call_reservations'] == usage.provider_call_count == 3
    assert state['output_liability'] == usage.output_token_liability == 100 + 24000
    original_raw = rows(value, 'bounded_extraction_outcomes')[-1]
    old_body = ledger._decode_envelope(old, ledger._read_artifact(sid, old['attempt_id'] + '.raw.json', original_raw))[1]
    binding = next(b for b in value['service'].output_batches.inputs(value['service'].get_run(value['run_id'])) if b[3].series_id == sid)
    segment = next(s for s in ledger.read(sid)[1].segments if s.segment_id == old['segment_id'])
    with pytest.raises(ValueError, match='NONDEFAULT_INACTIVE_VARIANT'):
        output.record_to_result(old_body.decode('utf-8'), binding[3], segment, binding[2], binding[1])
    with monkeypatch.context() as execution:
        tripwires(execution)
        transport = Transport(mode='empty')
        with synthetic_providers(value, transport) as providers:
            finished = resume(value, providers, key='strict-synthetic-continuation', ceiling=len(uncalled) + 1)
            assert finished['bounded_complete']
            assert len(transport.calls) == len(uncalled) + 1
            assert providers['SEMANTIC_DECOMPOSITION'].call_count == 0
        first = transport.calls[0]
        assert first['messages'][-1] == {'role':'user', 'content':strict.GUIDANCE}
        assert all(succeeded['segment_id'] != request_parts(call)[0]['segment_id'] for call in transport.calls)
        assert len(events(value, strict.COMMITTED)) == 1
    assert len(rows(value, 'bounded_extraction_series_results')) == len(rows(value, 'bounded_extraction_series'))
    assert not rows(value, 'source_processing_jobs')
    assert value['config'].knowledge_db.read_bytes() == value['production_before']

@pytest.mark.parametrize('mode', ['strict', 'variant_only', 'references_only'])
def test_new_invalid_response_still_fails_and_never_grants_third_attempt(tmp_path, monkeypatch, mode):
    value = stopped(tmp_path, monkeypatch)
    authorize(value)
    transport = InvalidOutput(mode, call=1)
    with synthetic_providers(value, transport) as providers:
        result = resume(value, providers, key='strict-synthetic-repeat-failure', ceiling=10)
        assert result['status'] == 'STOP_ON_FIRST_NEW_FAILURE' and len(transport.calls) == 1
        resume(value, providers, key='strict-synthetic-after-repeat-failure', ceiling=10)
        assert len(transport.calls) == 1
    assert len(rows(value, 'bounded_extraction_attempts')) == 3
    assert len(rows(value, 'bounded_extraction_segment_results')) == 1
    with pytest.raises(SourceOperationError, match='STRICT_RECOVERY_ALREADY_AUTHORIZED'):
        authorize(value, key='strict-unauthorized-third-attempt')

@pytest.mark.parametrize('mode', ['truncated', 'unknown', 'http', 'malformed', 'evidence_ack', 'binding', 'event_binding', 'ownership', 'variant_only', 'references_only'])
def test_other_failure_families_are_rejected_without_writes(tmp_path, monkeypatch, mode):
    value = stopped(tmp_path, monkeypatch, mode=mode)
    before = snapshot(value)
    with pytest.raises((ValueError, RuntimeError)):
        authorize(value)
    assert snapshot(value) == before

def test_successful_segment_and_unproven_frontier_cannot_be_reopened(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    failed_id = value['attempt_id']
    value['attempt_id'] = rows(value, 'bounded_extraction_attempts')[0]['attempt_id']
    before = snapshot(value)
    with pytest.raises(SourceOperationError):
        authorize(value)
    assert snapshot(value) == before
    value['attempt_id'] = failed_id
    from pro_a.workbench.bounded_extraction_store import _event
    uncalled = rows(value, 'bounded_extraction_segments')[-1]
    with value['service'].store.connect(operator_write=True) as c:
        _event(c, uncalled['series_id'], 'SEGMENT_MANUALLY_BLOCKED', segment_id=uncalled['segment_id'])
    before = snapshot(value)
    with pytest.raises(SourceOperationError):
        authorize(value)
    assert snapshot(value) == before

def test_idempotency_and_concurrent_workers(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    barrier = threading.Barrier(2)
    def action(i):
        barrier.wait(timeout=15)
        return authorize(value, worker='strict_worker_' + str(i))
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(action, range(2)))
    assert sorted(r['duplicate'] for r in results) == [False, True]
    assert results[0]['new_attempt_id'] == results[1]['new_attempt_id']
    before = snapshot(value)
    assert authorize(value)['duplicate']
    assert snapshot(value) == before
    with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'):
        authorize(value, reason='Changed reason.')
    with pytest.raises(SourceOperationError, match='STRICT_RECOVERY_ALREADY_AUTHORIZED'):
        authorize(value, key='different-strict-recovery-action')
    assert snapshot(value) == before

@pytest.mark.parametrize('limit', ['calls', 'liability'])
def test_budget_is_not_refunded_or_increased(tmp_path, monkeypatch, limit):
    value = stopped(tmp_path, monkeypatch)
    original = strict.frozen_bounded_service
    def constrained(*args):
        worker = original(*args)
        load = worker.output_batches.ledger._load
        def limited(c, sid):
            series, plan, state, usage = load(c, sid)
            key = 'provider_call_reservations' if limit == 'calls' else 'output_liability'
            ceiling = series.budget.max_provider_calls if limit == 'calls' else series.budget.max_cumulative_output_tokens
            return series, plan, {**state, key:ceiling}, usage
        worker.output_batches.ledger._load = limited
        return worker
    monkeypatch.setattr(strict, 'frozen_bounded_service', constrained)
    before = snapshot(value)
    with pytest.raises(SourceOperationError, match='STOP_STRICT_RECOVERY_BUDGET_INSUFFICIENT'):
        authorize(value)
    assert snapshot(value) == before

@pytest.mark.parametrize('kind', ['source', 'context'])
def test_source_or_context_drift_rejected_without_authorization(tmp_path, monkeypatch, kind):
    value = stopped(tmp_path, monkeypatch)
    if kind == 'source':
        source_id = value['service'].get_run(value['run_id'])['source_id']
        source = next(r for r in rows(value, 'private_sources') if r['source_id'] == source_id)
        path = value['config'].artifact_root / source['storage_relative']
        path.chmod(stat.S_IREAD | stat.S_IWRITE)
        path.write_bytes(b'Synthetic changed source')
    else:
        original = value['phase4_config'].read_text()
        changed = original.replace('model = "deepseek-flash"', 'model = "synthetic-changed-model"')
        assert changed != original
        value['phase4_config'].write_text(changed, encoding='utf-8')
    before = snapshot(value)
    with pytest.raises((ValueError, RuntimeError)):
        authorize(value)
    assert snapshot(value) == before

CRASH_WINDOWS = ['strict_recovery_authorized', 'strict_recovery_attempt_reserved', 'strict_recovery_frontier_reopened', 'strict_recovery_committed']

@pytest.mark.parametrize('window', CRASH_WINDOWS)
def test_hard_crash_transaction_and_request_file_are_recoverable(tmp_path, monkeypatch, window):
    value = stopped(tmp_path, monkeypatch)
    before = snapshot(value)
    document = {'config':asdict(value['config']), 'phase4_config':str(value['phase4_config']), 'run_id':value['run_id'], 'attempt_id':value['attempt_id']}
    path = tmp_path / 'synthetic-strict-input.json'
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
def authorize():return s.authorize_strict_same_run_recovery(v['run_id'],v['attempt_id'],worker_id='strict_crash_worker',idempotency_key='strict-hard-crash-action',reason='Versioned strict output regeneration.')
'''
    crash = bootstrap + "\ndef fault(name):\n if name==sys.argv[2]:os._exit(73)\np.checkpoint=fault\nauthorize()\n"
    env = {**os.environ, 'PYTHONPATH':os.pathsep.join((str(Path(__file__).resolve().parents[1] / 'src'),str(Path(__file__).parent))), 'PYTHONDONTWRITEBYTECODE':'1'}
    child = subprocess.run([sys.executable,'-B','-c',crash,str(path),window],env=env,capture_output=True,timeout=60)
    assert child.returncode == 73, child.stderr.decode(errors='replace')
    if window != 'strict_recovery_committed':
        assert snapshot(value) == before
    recovered = subprocess.run([sys.executable,'-B','-c',bootstrap + "\nr=authorize();assert r['status']=='AUTHORIZED' and r['provider_calls']==0\n",str(path)],env=env,capture_output=True,timeout=60)
    assert recovered.returncode == 0, recovered.stderr.decode(errors='replace')
    assert len(rows(value,'bounded_extraction_attempts')) == 3
    assert len(rows(value,'bounded_extraction_dispatches')) == 2
    assert len(events(value,strict.COMMITTED)) == 1

def test_cross_release_requires_exact_strict_scope_then_continues(tmp_path, monkeypatch):
    import pro_a.phase4_orchestration as native
    from pro_a.cloud_contract import digest
    from pro_a.workbench import cloud_jobs, retry_compatibility as compatibility
    value = stopped(tmp_path, monkeypatch)
    target = {**value['service'].jobs.current_runtime(),'git_sha':'f'*40}
    target['runtime_sha256'] = digest({k:v for k,v in target.items() if k != 'runtime_sha256'})
    target_native = {**native._runtime(),'repository_commit':'f'*40}
    monkeypatch.setattr(cloud_jobs,'runtime_identity',lambda *_a,**_k:target)
    monkeypatch.setattr(native,'_runtime',lambda:target_native)
    monkeypatch.setattr(compatibility,'native_runtime',lambda:target_native)
    before = snapshot(value)
    with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
        authorize(value)
    assert compatibility.assess_bounded_retry_compatibility(value['config'],value['run_id'],value['attempt_id'])['status'] == 'BLOCKED'
    result = strict.assess_strict_recovery_compatibility(value['config'],value['run_id'],value['attempt_id'])
    assert result['status'] == 'QUALIFIED', result
    assert 'strict_output_failure_family' in result['dimensions'] and 'malformed_json_syntax_only' not in result['dimensions']
    assert snapshot(value) == before
    assert strict.assess_strict_recovery_compatibility(value['config'],value['run_id'],value['attempt_id'],persist=True)['status'] == 'QUALIFIED'
    authorize(value)
    with synthetic_providers(value, Transport(mode='empty')) as providers:
        assert resume(value, providers, key='strict-cross-release-continuation', ceiling=2)['bounded_complete']

def test_operator_has_no_public_write_exposure_and_default_attempt_prohibition(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    ledger = value['service'].output_batches.ledger
    failed = rows(value,'bounded_extraction_attempts')[-1]
    with pytest.raises(ValueError):
        ledger.reserve_attempt(failed['segment_id'],'unowned',0,attempt_number=2,payload_sha256='a'*64,configuration_sha256='b'*64)
    package = Path(__import__('pro_a').__file__).resolve().parent
    for name in ('workbench/api.py','mcp/server.py','mcp/service.py'):
        assert 'authorize_strict_same_run_recovery' not in (package / name).read_text(encoding='utf-8')
    from pro_a.workbench.bounded_resume import contract
    assert not contract()['automatic_retry'] and not contract()['new_subdivision_allowed']

def test_versioned_prompt_tampering_cannot_dispatch(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    result = authorize(value)
    ledger = value['service'].output_batches.ledger
    old = rows(value, 'bounded_extraction_attempts')[1]
    with value['service'].store.connect() as c:
        sid = c.execute('SELECT series_id FROM bounded_extraction_segments WHERE segment_id=?', (old['segment_id'],)).fetchone()[0]
    prompt = ledger._path(sid, result['new_attempt_id'] + '.prompt.json')
    content = prompt.read_bytes()
    payload = json.loads(content)
    payload['request']['messages'][-1]['content'] += ' Synthetic unauthorized change.'
    prompt.write_text(json.dumps(payload), encoding='utf-8')
    transport = Transport(mode='empty')
    with synthetic_providers(value, transport) as providers:
        with pytest.raises((ValueError, RuntimeError)):
            resume(value, providers, key='strict-tampered-versioned-request')
    assert not transport.calls and len(rows(value, 'bounded_extraction_dispatches')) == 2
    prompt.write_bytes(content)
    ledger.read(sid)

def test_unknown_attempt_two_is_never_dispatched_again(tmp_path, monkeypatch):
    value = stopped(tmp_path, monkeypatch)
    authorize(value)
    transport = Transport(mode='unknown')
    with synthetic_providers(value, transport) as providers:
        result = resume(value, providers, key='strict-unknown-attempt-two')
        assert result['status'] == 'STOP_RECOVERY_REQUIRED'
        resume(value, providers, key='strict-unknown-attempt-two-again')
        assert len(transport.calls) == 1
    assert len(rows(value, 'bounded_extraction_attempts')) == 3
    assert len(rows(value, 'bounded_extraction_dispatches')) == 3
    with pytest.raises((ValueError, RuntimeError)):
        authorize(value, key='strict-unknown-no-third-attempt')
