"""Real isolated P1 -> P2 -> attached SQLite transaction; no real Provider."""
from contextlib import closing
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from pro_a.operational_contract import readonly, sealed, snapshot
from pro_a.operational_operator import OperatorConfig
from pro_a.operator_handoff import OperatorHandoff
from pro_a.production_promotion import canonical_sha256
from pro_a.workbench.canonical_admission import CanonicalAdmission, APPROVAL
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.unified_review import records
from test_candidate_advice_submission import advice_case, HUMAN
from test_unified_review import plan as p1_plan


def prepared(value, monkeypatch, mode='single', **options):
    engine, body = p1_plan(value, mode=mode, **options)
    pid = engine.prepare(value['handle'], **body)['proposal_id']
    engine.approve(value['handle'], pid, HUMAN, confirm=True)
    admission = CanonicalAdmission(value['config'])
    monkeypatch.setattr('pro_a.workbench.canonical_admission.require_readonly_boundary',
                        lambda _: {'scheme': 'WINDOWS_MANDATORY_INTEGRITY', 'web_integrity': 4096})
    monkeypatch.setattr('pro_a.operator_handoff.integrity_level', lambda: 8192)
    return admission


def approved(value, monkeypatch, mode='single'):
    admission = prepared(value, monkeypatch, mode)
    frozen = admission.prepare(value['handle'])
    admission.approve(value['handle'], frozen['plan']['object_id'], HUMAN, confirm=True)
    worker = OperatorHandoff(OperatorConfig(value['config'], value['config'].state_db.parent.parent / 'operator/ledger.db'))
    worker.operator.initialize()
    return admission, worker, frozen['plan']


@pytest.mark.parametrize('mode', ['single', 'dual'])
def test_two_approvals_real_transaction_and_replay(advice_case, monkeypatch, mode):
    v = advice_case; admission, worker, plan = approved(v, monkeypatch, mode)
    result = worker.run(v['handle'])
    assert result['status'] == 'RECONCILED'
    assert result['receipt']['actual_mutation_counts'] == plan['insert_counts']
    assert result['receipt']['post_state_sha256'] == plan['post_state_sha256']
    with closing(readonly(v['config'].knowledge_db)) as db:
        assert canonical_sha256(snapshot(db)) == plan['post_state_sha256']
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    before = v['config'].knowledge_db.read_bytes()
    assert worker.run(v['handle'])['receipt'] == result['receipt']
    assert admission.approve(v['handle'], plan['object_id'], HUMAN, confirm=True)['status'] == 'RECONCILED'
    assert v['config'].knowledge_db.read_bytes() == before
    with admission.store.connect() as db:
        assert len(records(db, v['handle'], APPROVAL)) == 1
        assert len(records(db, v['handle'], 'UNIFIED_REVIEW_APPROVED')) == 1
    with pytest.raises(BoundaryError, match='ALREADY_CONSUMED'):
        worker.operator.execute(plan['envelope_id'], confirm=plan['envelope_id'])


@pytest.mark.parametrize('point', ['registered', 'insert', 'before_commit', 'after_commit', 'receipt_export', 'before_reconcile'])
def test_interruption_reopens_same_authorization(advice_case, monkeypatch, point):
    v = advice_case; admission, worker, plan = approved(v, monkeypatch)
    def fault(where, _):
        if where == point: raise RuntimeError('isolated interruption')
    with pytest.raises((RuntimeError, BoundaryError)):
        worker.run(v['handle'], fault=fault)
    restarted = OperatorHandoff(worker.operator.config)
    assert restarted.run(v['handle'])['status'] == 'RECONCILED'
    with closing(worker.operator.connect()) as db:
        grants = db.execute('SELECT status FROM grants').fetchall()
        assert [r[0] for r in grants] == ['CONSUMED']
    assert admission.read(v['handle'])['receipt']['actual_mutation_counts'] == plan['insert_counts']


def test_pending_approval_cannot_be_bypassed_by_cli_confirm(advice_case, monkeypatch):
    v = advice_case; admission = prepared(v, monkeypatch)
    frozen = admission.prepare(v['handle']); eid = frozen['plan']['envelope_id']
    worker = OperatorHandoff(OperatorConfig(v['config'], v['config'].state_db.parent.parent / 'operator/ledger.db'))
    worker.operator.initialize()
    with pytest.raises(BoundaryError, match='P2_HUMAN_APPROVAL_REQUIRED'):
        worker.operator.register(eid, confirm=eid)
    assert admission.read(v['handle'])['status'] == 'AWAITING_SECOND_APPROVAL'
    with closing(worker.operator.connect()) as db: assert db.execute('SELECT count(*) FROM grants').fetchone()[0] == 0
    for key, changed in (('insert_counts', {}), ('unchanged_count', 999), ('excluded', []),
                         ('pre_state_sha256', '0' * 64), ('runtime_identity', '0' * 64),
                         ('envelope_id', 'OPERATIONAL_' + '0' * 64)):
        body = {k: x for k, x in frozen['plan'].items() if k not in ('object_id', 'sha256')}
        if body[key] == changed: continue
        body[key] = changed
        with pytest.raises(BoundaryError): admission.check(v['handle'], sealed(body, 'ADMISSION'), before_execution=True)


@pytest.mark.parametrize('fault', ['model', 'session', 'plan', 'confirm', 'os_boundary'])
def test_invalid_human_authority(advice_case, monkeypatch, fault):
    v = advice_case; admission = prepared(v, monkeypatch)
    pid = admission.prepare(v['handle'])['plan']['object_id']; actor = copy.deepcopy(HUMAN)
    if fault == 'model': actor['principal_type'] = 'MODEL'
    if fault == 'session': actor['session_id'] = ''
    if fault == 'plan': pid = 'ADMISSION_' + '0' * 64
    if fault == 'os_boundary':
        monkeypatch.setattr('pro_a.workbench.canonical_admission.require_readonly_boundary',
                            lambda _: (_ for _ in ()).throw(BoundaryError('UNPRIVILEGED_PROCESS_REQUIRED')))
    with pytest.raises(BoundaryError): admission.approve(v['handle'], pid, actor, confirm=fault != 'confirm')
    with admission.store.connect() as db: assert not records(db, v['handle'], APPROVAL)


def test_baseline_drift_never_registers_grant(advice_case, monkeypatch):
    v = advice_case; admission, worker, plan = approved(v, monkeypatch)
    with sqlite3.connect(v['config'].knowledge_db) as db:
        db.execute("INSERT INTO nodes VALUES('NODE_DRIFT','Isolated drift','Entity','','active','2026-01-01','2026-01-01')")
    from pro_a.operational_contract import identity
    assert identity(v['config'].knowledge_db) != plan['baseline']
    with pytest.raises(BoundaryError): worker.run(v['handle'])
    with closing(worker.operator.connect()) as db: assert db.execute('SELECT count(*) FROM grants').fetchone()[0] == 0


def test_defer_is_not_rewritten(advice_case, monkeypatch):
    v = advice_case; engine, body = p1_plan(v, mode='single', deferred=True)
    for item in body['attribution_items']: item['outcome'] = 'DEFER'
    pid = engine.prepare(v['handle'], **body)['proposal_id']
    engine.approve(v['handle'], pid, HUMAN, confirm=True)
    with pytest.raises(BoundaryError, match='ATTRIBUTION_DEFERRED'):
        CanonicalAdmission(v['config']).prepare(v['handle'])


def test_two_workers_only_one_commit(advice_case, monkeypatch):
    v = advice_case; admission, worker, _ = approved(v, monkeypatch)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: OperatorHandoff(worker.operator.config).run(v['handle']), range(2)))
    assert results[0]['receipt'] == results[1]['receipt']
    assert admission.read(v['handle'])['status'] == 'RECONCILED'
