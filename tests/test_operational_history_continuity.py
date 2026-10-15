"""Real Operator commits on disposable, public-safe synthetic databases only."""
import copy
from dataclasses import replace
import hashlib
import shutil
import sqlite3

import pytest

from pro_a.operational_contract import verify_envelope
from pro_a.operational_qualification import registered_historical_read, reconcile_registered
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from operational_history_fixture import setup, prepare, apply
from test_historical_operational_read import replace_stored, reseal

VERIFIED = 'HISTORICAL_EXECUTION_CHAIN_VERIFIED'
INCOMPLETE = 'HISTORICAL_STATE_PROOF_INCOMPLETE'


def verification(config, handle):
    return registered_historical_read(config, handle)['qualification']['history_verification']


@pytest.mark.parametrize('schema_version', ['0.2.3', '0.2.4'])
def test_two_actual_applies_preserve_first_history(tmp_path, schema_version):
    seed, operator = setup(tmp_path, schema_version=schema_version)
    h1, e1 = prepare(seed, 1)
    r1 = apply(operator, e1)
    assert registered_historical_read(seed['config'], h1)['receipt'] == r1
    h2, e2 = prepare(seed, 2)
    r2 = apply(operator, e2)
    assert registered_historical_read(seed['config'], h2)['receipt'] == r2
    assert registered_historical_read(seed['config'], h1)['receipt'] == r1
    proof = verification(seed['config'], h1)
    assert proof['status'] == VERIFIED
    assert proof['registered_receipt_chain'] == [r1['object_id'], r2['object_id']]


@pytest.fixture(scope='module')
def three_commits(tmp_path_factory):
    seed, operator = setup(tmp_path_factory.mktemp('actual-three-applies'))
    records = []
    for index in (1, 2, 3):
        handle, envelope = prepare(seed, index)
        assert envelope['baseline']['schema_version'] == '0.2.4'
        records.append((handle, envelope, apply(operator, envelope)))
    return seed['config'], records


@pytest.fixture
def history_copy(three_commits, tmp_path):
    config, records = three_commits
    (tmp_path / 'canonical').mkdir()
    (tmp_path / 'state').mkdir()
    cloned = replace(config, knowledge_db=tmp_path / 'canonical/data.db', state_db=tmp_path / 'state/state.db')
    shutil.copyfile(config.knowledge_db, cloned.knowledge_db)
    shutil.copyfile(config.state_db, cloned.state_db)
    shutil.copytree(config.knowledge_db.parent / 'operational_sources', cloned.knowledge_db.parent / 'operational_sources')
    with sqlite3.connect(cloned.state_db) as db:
        for key, value in cloned.bindings().items():
            if key != 'schema_version':
                db.execute('UPDATE workbench_meta SET value=? WHERE key=?', (value, key))
    return cloned, copy.deepcopy(records)


def test_three_applies_all_receipts_verified_without_writes(history_copy, monkeypatch):
    config, records = history_copy
    fingerprint = lambda: [hashlib.sha256(p.read_bytes()).hexdigest() for p in (config.knowledge_db, config.state_db)]
    before = fingerprint()
    connect = Store.connect
    def read_only(self, *, operator_write=False):
        assert not operator_write
        return connect(self)
    monkeypatch.setattr(Store, 'connect', read_only)
    for i, (handle, envelope, receipt) in enumerate(records):
        proof = verification(config, handle)
        assert proof['status'] == VERIFIED
        assert proof['registered_receipt_chain'] == [r[2]['object_id'] for r in records[i:]]
        assert proof['original_post_state_sha256'] == receipt['post_state_sha256']
        assert not proof['execution_authorized']
        assert reconcile_registered(config, handle, receipt['object_id'])['status'] == VERIFIED
        assert verification(config, handle) == proof
    assert fingerprint() == before


def test_runtime_upgrade_reads_history_but_execution_guard_rejects(history_copy, monkeypatch):
    import pro_a.operational_contract as contract
    config, records = history_copy
    monkeypatch.setattr(contract, 'runtime_identity', lambda: '0' * 64)
    for handle, envelope, _ in records:
        assert verification(config, handle)['status'] == VERIFIED
        with pytest.raises(BoundaryError, match='RUNTIME_IDENTITY_MISMATCH'):
            verify_envelope(envelope)


def test_missing_intermediate_is_explicit_incomplete(history_copy):
    config, records = history_copy
    replace_stored(config, 'operational_receipts', records[1][0], None)
    first = registered_historical_read(config, records[0][0])['qualification']
    assert first['history_verification']['status'] == INCOMPLETE
    assert first['history_verification']['receipt_integrity'] == 'HISTORICAL_RECEIPT_INTEGRITY_VERIFIED'
    assert not first['historical_read_verified'] and not first['executable_under_current_runtime']
    assert reconcile_registered(config, records[0][0], records[0][2]['object_id'])['status'] == INCOMPLETE
    assert verification(config, records[2][0])['status'] == VERIFIED


@pytest.mark.parametrize('field,value', [('post_state_sha256', '0'*64), ('actual_mutation_counts', {}),
    ('keys_touched', []), ('tables_touched', []), ('status', 'READY'), ('transaction_result', 'FAILED'),
    ('operator_entry_version', 'wrong'), ('source_sha256', '0'*64), ('binding', {})])
def test_rehashed_successor_receipt_tamper_rejected(history_copy, field, value):
    config, records = history_copy
    handle, _, receipt = records[1]
    replace_stored(config, 'operational_receipts', handle, reseal({**receipt, field: value}, 'EXECUTION'))
    with pytest.raises(BoundaryError):
        verification(config, records[0][0])


@pytest.mark.parametrize('fault', ['hash', 'registry_id', 'source', 'binding', 'runtime', 'mutations'])
def test_successor_envelope_tamper_rejected(history_copy, fault):
    config, records = history_copy
    handle, envelope, _ = records[1]
    if fault == 'hash': envelope['sha256'] = '0'*64
    elif fault == 'registry_id': envelope['object_id'] = 'OPERATIONAL_'+'0'*64
    else:
        field, value = {'source': ('source_sha256', '0'*64), 'binding': ('binding', {}),
                        'runtime': ('runtime_identity', 'invalid'), 'mutations': ('mutations', [])}[fault]
        envelope = reseal({**envelope, field: value}, 'OPERATIONAL')
    replace_stored(config, 'operational_packages', handle, envelope)
    with pytest.raises((BoundaryError, KeyError)):
        verification(config, records[0][0])


def test_forged_bridge_cannot_skip_second_transition(history_copy):
    config, records = history_copy
    replace_stored(config, 'operational_receipts', records[1][0], None)
    handle, envelope, receipt = records[2]
    diff = reseal({**envelope['predicted_diff'], 'pre_state_sha256': records[0][2]['post_state_sha256']}, 'DIFF')
    envelope = reseal({**envelope, 'predicted_diff': diff}, 'OPERATIONAL')
    receipt = reseal({**receipt, 'envelope_id': envelope['object_id'], 'predicted_diff_id': diff['object_id']}, 'EXECUTION')
    replace_stored(config, 'operational_packages', handle, envelope)
    replace_stored(config, 'operational_receipts', handle, receipt)
    with pytest.raises(BoundaryError, match='HISTORICAL_INTEGRITY_INVALID'):
        verification(config, records[0][0])


@pytest.mark.parametrize('fault', ['source_bytes', 'canonical_row', 'unknown_transition', 'journal'])
def test_source_object_and_state_drift_have_distinct_scopes(history_copy, fault):
    config, records = history_copy
    handle, envelope, _ = records[0]
    if fault == 'source_bytes':
        (config.knowledge_db.parent / 'operational_sources' / envelope['source_sha256']).write_bytes(b'tampered')
    elif fault == 'journal':
        config.knowledge_db.with_name(config.knowledge_db.name+'-journal').write_bytes(b'pending recovery')
    else:
        with sqlite3.connect(config.knowledge_db) as db:
            if fault == 'canonical_row':
                claim = next(x['key']['claim_id'] for x in envelope['mutations'] if x['table']=='claims')
                db.execute("UPDATE claims SET statement='tampered' WHERE claim_id=?", (claim,))
            else:
                db.execute("UPDATE nodes SET description='unproven external update' WHERE node_id='NODE_SYNTHETIC_PARENT'")
    if fault == 'unknown_transition':
        assert verification(config, handle)['status'] == INCOMPLETE
    else:
        with pytest.raises(BoundaryError):
            verification(config, handle)


def test_post_commit_crash_recovery_then_second_apply(tmp_path):
    seed, operator = setup(tmp_path)
    handle, envelope = prepare(seed, 1)
    eid = envelope['object_id']
    operator.register(eid, confirm=eid)
    def crash(point, _):
        if point == 'after_commit': raise RuntimeError('synthetic crash after durable commit')
    with pytest.raises(BoundaryError, match='RECOVERY_REQUIRED'):
        operator.execute(eid, confirm=eid, fault=crash)
    with pytest.raises(BoundaryError, match='ALREADY_CONSUMED'):
        operator.execute(eid, confirm=eid)
    receipt = operator.reconcile(eid)
    assert operator.reconcile(eid) == receipt
    _, next_envelope = prepare(seed, 2)
    apply(operator, next_envelope)
    assert verification(seed['config'], handle)['status'] == VERIFIED
    with pytest.raises(BoundaryError, match='RECOVERY_REQUIRED'):
        operator.reconcile(eid)
