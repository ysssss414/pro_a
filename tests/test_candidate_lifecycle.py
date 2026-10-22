"""Explicit TEST FIXTURE identities; real acceptance, review and SQLite paths."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from pro_a import candidate_origin_v2 as bridge
from pro_a.workbench.candidate_lifecycle import (
    RevisionLifecycle, reference, _required, freeze, require_documents, require_handle)
from pro_a.workbench.config import BoundaryError
from series_binding_helpers import rows, synthetic_providers
from test_candidate_origin_v2 import (
    accepted_case, children, metadata_resolution, select_document, isolated_review_chain)

HUMAN = {'actor': 'TEST_FIXTURE_HUMAN', 'session_id': 'TEST_FIXTURE_SESSION', 'principal_type': 'HUMAN_USER'}


def prepared(tmp_path, monkeypatch):
    value = accepted_case(tmp_path, monkeypatch)
    revisions = children(value['document'])
    ref = value['archive'].publish(value['original_id'], value['attempt'], revisions,
                                  metadata_resolution=metadata_resolution(value['document']))
    doc = value['archive'].read(ref)
    select_document(value, doc)
    value.update(selected=doc, selected_ref=ref, revisions=revisions)
    return value


def proposal(value):
    revisions = copy.deepcopy(value['revisions'])
    next(iter(revisions.values()))['reason'] = 'TEST FIXTURE explicit second semantic proposal'
    ref = value['archive'].publish(value['original_id'], value['attempt'], revisions,
                                  metadata_resolution=metadata_resolution(value['document']))
    return ref, value['archive'].read(ref)


def decide(lifecycle, action, ref, key, **kwargs):
    return lifecycle.decide(action, ref, expected_head=lifecycle.read(ref)['head_sha256'],
        identity=HUMAN, reason='TEST FIXTURE explicit lifecycle decision', idempotency_key=key,
        confirm=True, **kwargs)


def packet(value, ref, key):
    service = value['service']
    run = service.start_v7_review([ref], idempotency_key=key, entry_contract=bridge.ENTRY_CONTRACT)['run']
    rid = run['processing_run_id']
    for _ in range(2):
        run = service.advance_once(worker_id='TEST_FIXTURE', processing_run_id=rid)
    with synthetic_providers(value) as providers:
        providers['SEMANTIC_DECOMPOSITION'].provider_identity = service.jobs.profile.provider
        providers['SEMANTIC_DECOMPOSITION'].adapter_version = service.jobs.profile.adapter_for_operation('SEMANTIC_DECOMPOSITION')
        run = service.advance_once(worker_id='TEST_FIXTURE', processing_run_id=rid, provider=providers)
    assert run['state'] == 'HUMAN_REVIEW_REQUIRED', run.get('error')
    require_handle(value['config'], run['packet_artifact_id'])
    return run


def test_lifecycle_identity_terminal_and_exact_replay(tmp_path, monkeypatch):
    value = prepared(tmp_path, monkeypatch)
    doc, cfg = value['selected'], value['config']
    lifecycle = RevisionLifecycle(cfg)
    binding = freeze(cfg, [doc])
    _, new = proposal(value)
    # A parallel immutable proposal neither changes current selection nor support.
    assert freeze(cfg, [doc]) == binding
    old_refs = {r['logical_id']: r for r in _required([doc])}
    changed = [r for r in _required([new]) if r != old_refs[r['logical_id']]]
    assert len(changed) == 2
    new_ref = changed[0]; old = old_refs[new_ref['logical_id']]
    assert lifecycle.read(new_ref)['versions'][new_ref['revision_sha256']] == 'AVAILABLE'
    head = lifecycle.read(old)['head_sha256']
    for identity in ({**HUMAN, 'principal_type': 'MODEL'}, {**HUMAN, 'actor': ''}):
        with pytest.raises(BoundaryError, match='HUMAN_USER_REQUIRED'):
            lifecycle.decide('REPLACE', old, expected_head=head, identity=identity, reason='test',
                idempotency_key='unauthorized-replace-0001', replacement=new_ref, confirm=True)
    with pytest.raises(BoundaryError, match='STALE_HEAD'):
        lifecycle.decide('REPLACE', old, expected_head=None, identity=HUMAN, reason='test',
            idempotency_key='stale-replace-00001', replacement=new_ref, confirm=True)
    foreign = next(r for r in old_refs.values() if r['logical_id'] != old['logical_id'])
    with pytest.raises(BoundaryError, match='CROSS_OBJECT'):
        decide(lifecycle, 'REPLACE', old, 'cross-object-000001', replacement=foreign)
    forged = {**old, 'attempt_id': 'FORGED'}
    with pytest.raises(BoundaryError, match='UNREGISTERED'):
        decide(lifecycle, 'REVOKE', forged, 'forged-attempt-0001')
    result = decide(lifecycle, 'REPLACE', old, 'explicit-replace-0001', replacement=new_ref)
    assert lifecycle.decide('REPLACE', old, expected_head=head, identity=HUMAN,
        reason='TEST FIXTURE explicit lifecycle decision', idempotency_key='explicit-replace-0001',
        replacement=new_ref, confirm=True) == result
    with pytest.raises(BoundaryError, match='IDEMPOTENCY_CONFLICT'):
        lifecycle.decide('REPLACE', old, expected_head=head, identity=HUMAN, reason='changed reason',
            idempotency_key='explicit-replace-0001', replacement=new_ref, confirm=True)
    assert lifecycle.read(old)['versions'][old['revision_sha256']] == 'SUPERSEDED'
    with pytest.raises(BoundaryError, match='TERMINAL'):
        decide(lifecycle, 'SELECT', old, 'restore-old-0000001')
    with pytest.raises(BoundaryError, match='NOT_CURRENT'):
        require_documents(cfg, [doc], binding)
    # Unrelated logical objects retain their selections. Revoke needs no successor.
    other = next(r for r in old_refs.values() if r['child_id'] and r['logical_id'] not in {x['logical_id'] for x in changed})
    before = lifecycle.read(other)
    revoked_head = lifecycle.read(new_ref)['head_sha256']
    revoked = decide(lifecycle, 'REVOKE', new_ref, 'explicit-revoke-0001')
    assert lifecycle.read(other) == before
    assert lifecycle.decide('REVOKE', new_ref, expected_head=revoked_head, identity=HUMAN,
        reason='TEST FIXTURE explicit lifecycle decision', idempotency_key='explicit-revoke-0001', confirm=True) == revoked
    with pytest.raises(BoundaryError, match='TERMINAL'):
        decide(lifecycle, 'SELECT', new_ref, 'restore-revoked-0001')
    # Re-publishing identical immutable content does not resurrect its authority.
    _, replayed = proposal(value)
    assert replayed == new
    assert lifecycle.read(new_ref)['versions'][new_ref['revision_sha256']] == 'REVOKED'
    assert lifecycle.decide('REPLACE', old, expected_head=head, identity=HUMAN,
        reason='TEST FIXTURE explicit lifecycle decision', idempotency_key='explicit-replace-0001',
        replacement=new_ref, confirm=True) == result
    assert lifecycle.read(new_ref)['current_revision'] is None
    # Restart uses persisted events, not an in-process selected-version cache.
    from dataclasses import asdict
    payload = tmp_path/'restart-lifecycle.json'
    payload.write_text(json.dumps({'config': asdict(cfg), 'ref': old}, default=str))
    child = subprocess.run([sys.executable, '-B', '-c', '''import json,sys
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.candidate_lifecycle import RevisionLifecycle
p=json.loads(Path(sys.argv[1]).read_text())
for k in ('knowledge_db','state_db','artifact_root'): p['config'][k]=Path(p['config'][k])
s=RevisionLifecycle(WorkbenchConfig(**p['config'])).read(p['ref'])
assert s['versions'][p['ref']['revision_sha256']]=='SUPERSEDED'
print('PERSISTED_SUPERSESSION_VERIFIED')
''', str(payload)], capture_output=True, timeout=30,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)})
    assert child.returncode == 0, child.stderr.decode(errors='replace')
    assert b'PERSISTED_SUPERSESSION_VERIFIED' in child.stdout
    # Missing lifecycle authority is blocked explicitly; immutable origin is readable.
    assert value['archive'].read(value['selected_ref']) == doc
    with pytest.raises(BoundaryError, match='LIFECYCLE_BINDING_REQUIRED'):
        require_documents(cfg, [doc], None)


def test_replacement_blocks_old_authority_then_fresh_review_executes(tmp_path, monkeypatch):
    value = prepared(tmp_path, monkeypatch)
    run = packet(value, value['selected_ref'], 'lifecycle-old-review-0001')
    lifecycle = RevisionLifecycle(value['config'])
    def blocked(admission, worker, handle, plan, human):
        original = value['config'].knowledge_db.read_bytes()
        new_ref, doc = proposal(value)
        admission.approved(handle, before_execution=True)  # publish alone is safe
        old = {r['logical_id']: r for r in _required([value['selected']])}
        for ref in _required([doc]):
            if ref != old[ref['logical_id']]:
                decide(lifecycle, 'REPLACE', old[ref['logical_id']],
                       'p2-replace-'+ref['logical_id'][:20], replacement=ref)
        for operation in (lambda: admission.check(handle, plan, before_execution=True),
                          lambda: admission.approved(handle, before_execution=True),
                          lambda: worker.operator.register(plan['envelope_id'], confirm=plan['envelope_id']),
                          lambda: require_handle(value['config'], handle)):
            with pytest.raises(BoundaryError, match='CANDIDATE_REVISION_NOT_CURRENT'):
                operation()
        with pytest.raises(BoundaryError, match='CANDIDATE_REVISION_NOT_CURRENT'):
            worker.run(handle)
        result = admission.read(handle)
        assert result['status'] == 'BLOCKED', result
        assert value['config'].knowledge_db.read_bytes() == original
        # P2 and P0/P1 files remain immutable readable history, not executable authority.
        assert admission.read(handle)['plan']['object_id'] == plan['object_id']
        value['next_ref'] = new_ref
        assert doc['raw_sha256'] == value['selected']['raw_sha256']
        return result
    (tmp_path/'old').mkdir()
    isolated_review_chain(value, run, tmp_path/'old', monkeypatch, before_execute=blocked)
    # The same content under a new explicit revision obtains its own complete
    # policy/P0/P1/P2 path. No old seal, advice or plan is copied.
    fresh = packet(value, value['next_ref'], 'lifecycle-fresh-review-0001')
    assert fresh['packet_artifact_id'] != run['packet_artifact_id']
    from pro_a.workbench.canonical_admission import CanonicalAdmission
    from pro_a.workbench.unified_review import UnifiedReview
    old_plan = json.loads((tmp_path/'old/p2-plan.json').read_text())
    with pytest.raises(BoundaryError, match='ADMISSION_RUNTIME_MISMATCH'):
        CanonicalAdmission(value['config']).check(fresh['packet_artifact_id'], old_plan, before_execution=True)
    # A P1 proposal/Seal is packet-scoped, including the revision lineage.
    old_p1 = json.loads((tmp_path/'old/p1-receipt.json').read_text())
    with pytest.raises(BoundaryError):
        UnifiedReview(value['config']).approve(fresh['packet_artifact_id'], old_p1['proposal_id'], HUMAN, confirm=True)
    (tmp_path/'fresh').mkdir()
    isolated_review_chain(value, fresh, tmp_path/'fresh', monkeypatch)


def test_revoke_parent_dependency_blocks_whole_selection(tmp_path, monkeypatch):
    value = prepared(tmp_path, monkeypatch)
    doc, cfg = value['selected'], value['config']
    lifecycle = RevisionLifecycle(cfg)
    binding = freeze(cfg, [doc])
    parent = next(r for r in _required([doc]) if r['child_id'] is None)
    decide(lifecycle, 'REVOKE', parent, 'parent-revoke-00001')
    with pytest.raises(BoundaryError, match='NOT_CURRENT'):
        require_documents(cfg, [doc], binding)
    child = next(r for r in _required([doc]) if r['child_id'] and r['parent_observation_id'] == parent['parent_observation_id'])
    assert lifecycle.read(child)['versions'][child['revision_sha256']] == 'ACTIVE'
    # An independently selected parent is unaffected, but an old aggregate plan
    # cannot silently omit this dependency and continue on its old authority.
    other = next(r for r in _required([doc]) if r['parent_observation_id'] != parent['parent_observation_id'])
    assert lifecycle.read(other)['versions'][other['revision_sha256']] == 'ACTIVE'


def test_reconciliation_reserves_state_before_ledger(tmp_path, monkeypatch):
    """A competing SQLite writer cannot enter before reconciliation takes ledger."""
    import sqlite3
    from pro_a.operational_operator import Operator, OperatorConfig
    from pro_a.workbench.store import Store
    value = accepted_case(tmp_path, monkeypatch)
    worker = Operator(OperatorConfig(value['config'], tmp_path/'operator/ledger.db'))
    worker.initialize()
    original = worker.connect
    before = value['config'].knowledge_db.read_bytes()
    def contested_connection():
        with Store(value['config']).connect(operator_write=True) as competitor:
            competitor.execute('PRAGMA busy_timeout=0')
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                competitor.execute('BEGIN IMMEDIATE')
        return original()
    monkeypatch.setattr(worker, 'connect', contested_connection)
    with pytest.raises(BoundaryError, match='RECOVERY_REQUIRED'):
        worker.reconcile('TEST_FIXTURE_MISSING_CONSUMED_RECEIPT')
    assert value['config'].knowledge_db.read_bytes() == before


@pytest.mark.parametrize('winner', ['execution', 'replacement'])
def test_cross_process_execution_and_replacement_serial_order(tmp_path, monkeypatch, winner):
    """Pause real transactions, not a stand-in writer or an early UI check."""
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import asdict
    import sqlite3
    import time
    value = prepared(tmp_path, monkeypatch)
    run = packet(value, value['selected_ref'], 'race-review-'+winner+'-0001')
    def race(admission, worker, handle, plan, human):
        archive_ref, new = proposal(value)
        old_by_id = {r['logical_id']: r for r in _required([value['selected']])}
        replacement = next(r for r in _required([new]) if r != old_by_id[r['logical_id']])
        old = old_by_id[replacement['logical_id']]
        lifecycle = RevisionLifecycle(value['config'])
        job = {'config': asdict(value['config']), 'old': old, 'new': replacement,
               'head': lifecycle.read(old)['head_sha256'], 'winner': winner,
               'ledger': str(worker.operator.config.ledger), 'envelope': plan['envelope_id']}
        job_path = tmp_path/'race.json'; job_path.write_text(json.dumps(job, default=str))
        ready, release = tmp_path/'ready', tmp_path/'release'
        done, committed = tmp_path/'done.json', tmp_path/'canonical-committed'
        script = '''import json,sys,time,sqlite3
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig,BoundaryError
from pro_a.workbench.candidate_lifecycle import RevisionLifecycle,DECISION
from pro_a.workbench.source_operations import SourceOperations
p=Path(sys.argv[1]); j=json.loads(p.read_text()); root=p.parent
for k in ('knowledge_db','state_db','artifact_root'): j['config'][k]=Path(j['config'][k])
original=SourceOperations._event
if j['winner']=='replacement':
 def pause(db,rid,kind,body):
  original(db,rid,kind,body)
  if kind==DECISION:
   (root/'ready').write_text('STATE_TRANSACTION_RESERVED')
   limit=time.monotonic()+15
   while not (root/'release').exists():
    assert time.monotonic()<limit
    time.sleep(.01)
 SourceOperations._event=staticmethod(pause)
else: (root/'ready').write_text('ATTEMPTING_STATE_TRANSACTION')
if j['winner']=='execution':
 from pro_a.workbench import store as store_module
 real_connect=sqlite3.connect
 def no_wait(*args,**kwargs):
  kwargs['timeout']=0
  return real_connect(*args,**kwargs)
 store_module.sqlite3.connect=no_wait
try:
 r=RevisionLifecycle(WorkbenchConfig(**j['config'])).decide('REPLACE',j['old'],replacement=j['new'],
  expected_head=j['head'],identity={'actor':'TEST_FIXTURE_HUMAN','session_id':'TEST_FIXTURE_SESSION','principal_type':'HUMAN_USER'},
  reason='TEST FIXTURE concurrent explicit replacement', idempotency_key='concurrent-replace-0001',confirm=True)
except BoundaryError as exc:
 assert j['winner']=='execution' and str(exc)=='CANDIDATE_REVISION_CONCURRENT_WRITE'
 (root/'busy.json').write_text(json.dumps({'error':str(exc)}))
else:
 (root/'done.json').write_text(json.dumps(r))
'''
        def spawn():
            return subprocess.Popen([sys.executable, '-B', '-c', script, str(job_path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)})
        def until_ready(child):
            limit = time.monotonic()+60
            while not ready.exists():
                assert time.monotonic() < limit and child.poll() is None
                time.sleep(.01)
        worker.operator.register(plan['envelope_id'], confirm=plan['envelope_id'])
        before = value['config'].knowledge_db.read_bytes()
        if winner == 'execution':
            child = None
            def fault(stage, index):
                nonlocal child
                if stage == 'before_commit':
                    child = spawn(); until_ready(child)
                    time.sleep(.1)
                    # A zero-timeout SQLITE_BUSY rejection may complete before
                    # this process is scheduled again.  Its persisted result,
                    # rather than child liveness at an arbitrary instant, is
                    # the concurrency contract.
                    assert not done.exists()
                elif stage == 'after_commit':
                    committed.write_text('CANONICAL_AND_GRANT_COMMITTED_BEFORE_STATE_RELEASE')
            receipt = worker.operator.execute(plan['envelope_id'], confirm=plan['envelope_id'], fault=fault)
            stdout, stderr = child.communicate(timeout=15)
            assert child.returncode == 0, stderr.decode(errors='replace')
            assert (tmp_path/'busy.json').read_text() == '{"error": "CANDIDATE_REVISION_CONCURRENT_WRITE"}'
            assert committed.exists() and not done.exists()
            result = lifecycle.decide('REPLACE', old, replacement=replacement,
                expected_head=job['head'], identity={'actor':'TEST_FIXTURE_HUMAN',
                'session_id':'TEST_FIXTURE_SESSION','principal_type':'HUMAN_USER'},
                reason='TEST FIXTURE concurrent explicit replacement',
                idempotency_key='concurrent-replace-0001', confirm=True)
            done.write_text(json.dumps(result))
            assert done.exists()
            worker.operator.reconcile(plan['envelope_id'])
            # Replacement after execution cannot rewrite or block read-only history.
            assert admission.read(handle)['receipt']['object_id'] == receipt['object_id']
            after = value['config'].knowledge_db.read_bytes()
            assert worker.run(handle)['receipt']['object_id'] == receipt['object_id']
            assert value['config'].knowledge_db.read_bytes() == after
            from pro_a.workbench.source_operations import SourceOperationError
            from pro_a.recovered_candidate_origin import VERSION as RECOVERED, ENTRY_CONTRACT as RECOVERED_ENTRY
            recovered = value['selected']['version'] == RECOVERED
            start_review = (value['service'].start_recovered_review if recovered
                            else value['service'].start_v7_review)
            with pytest.raises(SourceOperationError, match='CANDIDATE_ADDITIONAL_SUPPORT_REVIEW_REQUIRED'):
                start_review([archive_ref], entry_contract=(RECOVERED_ENTRY if recovered else bridge.ENTRY_CONTRACT),
                             idempotency_key='no-duplicate-claim-0001')
        else:
            child = spawn(); until_ready(child)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(worker.operator.execute, plan['envelope_id'], confirm=plan['envelope_id'])
                time.sleep(.1)
                assert not future.done()  # final writer is waiting for the same durable reservation
                release.write_text('ALLOW_REPLACEMENT_COMMIT')
                with pytest.raises(BoundaryError, match='CANDIDATE_REVISION_NOT_CURRENT'):
                    future.result(timeout=15)
            stdout, stderr = child.communicate(timeout=15)
            assert child.returncode == 0, stderr.decode(errors='replace')
            assert value['config'].knowledge_db.read_bytes() == before
            with worker.operator.connect() as db:
                grant = db.execute('SELECT status,receipt FROM grants WHERE envelope_id=?', (plan['envelope_id'],)).fetchone()
                assert tuple(grant) == ('READY', None)
        return {'status': 'TEST_FIXTURE_SERIAL_ORDER_VERIFIED', 'winner': winner}
    isolated_review_chain(value, run, tmp_path, monkeypatch, before_execute=race)
