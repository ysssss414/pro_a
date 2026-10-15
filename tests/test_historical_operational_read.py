"""Opt-in private historical snapshot regression; no private fixture bytes enter Git.

PRO_A_HISTORICAL_SNAPSHOT points at config.json inside an isolated snapshot root.
All mutable tests make another disposable copy. No successful Apply is performed.
"""
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from pro_a.mcp.write_service import WritePolicy, WriteService
from pro_a.operational_contract import sealed, verify_envelope
from pro_a.operational_operator import Operator, OperatorConfig
from pro_a.operational_qualification import (package_projection, qualify, reconcile_registered,
                                            registered_historical_read, validate_package)
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.config import BoundaryError, WorkbenchConfig
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.store import Store


@pytest.fixture
def history(tmp_path):
    path = os.environ.get('PRO_A_HISTORICAL_SNAPSHOT')
    if not path:
        pytest.skip('Private isolated historical snapshot not supplied')
    manifest = Path(path).resolve()
    raw = json.loads(manifest.read_text(encoding='utf-8'))
    for key in ('knowledge_db', 'state_db', 'artifact_root'):
        raw[key] = Path(raw[key]).resolve()
        assert raw[key].is_relative_to(manifest.parent), 'ISOLATED_SNAPSHOT_REQUIRED'
    original = WorkbenchConfig(**raw)
    for name in ('canonical', 'state'):
        (tmp_path / name).mkdir()
    config = replace(original, knowledge_db=tmp_path / 'canonical/data.db', state_db=tmp_path / 'state/state.db')
    shutil.copyfile(original.knowledge_db, config.knowledge_db)
    shutil.copyfile(original.state_db, config.state_db)
    shutil.copytree(original.knowledge_db.parent / 'operational_sources', config.knowledge_db.parent / 'operational_sources')
    with sqlite3.connect(config.state_db) as db:
        for key, value in config.bindings().items():
            if key != 'schema_version':
                db.execute('UPDATE workbench_meta SET value=? WHERE key=?', (value, key))
        row = db.execute('SELECT artifact_id,body FROM operational_receipts').fetchone()
        handle, receipt = row[0], json.loads(row[1])
        envelope = json.loads(db.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()[0])
    return config, handle, envelope, receipt


def fingerprints(config):
    return [hashlib.sha256(p.read_bytes()).hexdigest() for p in (config.knowledge_db, config.state_db)]


def replace_stored(config, table, handle, value, *, update_id=True):
    # Deliberate corruption only in the per-test disposable database.
    with sqlite3.connect(config.state_db) as db:
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall():
            db.execute('DROP TRIGGER "' + row[0] + '"')
        if value is None:
            db.execute('DELETE FROM ' + table + ' WHERE artifact_id=?', (handle,))
        else:
            column = 'object_id=?,body=?' if update_id else 'body=?'
            args = (value['object_id'], json.dumps(value), handle) if update_id else (json.dumps(value), handle)
            db.execute('UPDATE ' + table + ' SET ' + column + ' WHERE artifact_id=?', args)


def reseal(value, prefix):
    return sealed({k: v for k, v in value.items() if k not in ('object_id', 'sha256')}, prefix)


def test_registered_history_and_mcp_preserve_objects_without_writes(history, monkeypatch):
    config, handle, envelope, receipt = history
    before = fingerprints(config)
    connect = Store.connect
    def readonly(self, *, operator_write=False):
        assert not operator_write, 'HISTORICAL_READ_MUST_NOT_WRITE'
        return connect(self)
    monkeypatch.setattr(Store, 'connect', readonly)
    for name in ('register', 'execute', 'reconcile'):
        monkeypatch.setattr(Operator, name, lambda *a, **k: pytest.fail('NO_OPERATOR_IN_READ_PATH'))
    native = ReviewWorkbench(config).sealed_result(handle)
    result = Attribution(config).read(handle)
    assert result['receipt'] == receipt and result['sidecar'] == envelope['attribution']
    assert result['qualification']['object_id'] == envelope['object_id']
    assert result['qualification']['historical_read_verified'] is True
    assert result['qualification']['executable_under_current_runtime'] is False
    assert result['qualification']['original_runtime_identity'] == envelope['runtime_identity']
    assert reconcile_registered(config, handle, receipt['object_id'])['receipt'] == receipt
    policy = WritePolicy(enabled=True, artifact_ids=(handle,), slot='A', reviewer_id='snapshot-reader',
                         execution_id='isolated-read-test', model='no-model-called', review_mode='SINGLE_MODEL_HUMAN')
    projected = WriteService(config, policy).get_shadow_qualification(handle)
    assert projected['operator_status'] == 'EXECUTED_RECEIPT_VERIFIED'
    assert projected['historical_read_verified'] and not projected['executable_under_current_runtime']
    with pytest.raises(BoundaryError, match='ARTIFACT_IDENTITY_MISMATCH'):
        verify_envelope(projected)
    assert ReviewWorkbench(config).sealed_result(handle) == native
    assert fingerprints(config) == before


@pytest.mark.parametrize('entry', ['verify', 'validate', 'projection', 'qualify', 'register', 'source', 'execute', 'reconcile'])
def test_old_envelope_never_gains_current_execution_authority(history, tmp_path, entry):
    config, handle, envelope, receipt = history
    context, sidecar = Attribution(config).sealed_context(handle)
    assert registered_historical_read(config, handle)['qualification']['historical_read_verified']
    op = Operator(OperatorConfig(config, tmp_path / 'operator/ledger.db'))
    eid = envelope['object_id']
    if entry in ('execute', 'reconcile'):
        op.initialize()
        info = config.knowledge_db.stat()
        with sqlite3.connect(op.config.ledger) as db:
            db.execute('INSERT INTO grants VALUES(?,?,?,?,?,?)', (eid, handle, json.dumps([info.st_dev, info.st_ino]),
                       json.dumps(envelope), 'READY' if entry == 'execute' else 'CONSUMED', json.dumps(receipt)))
    before = fingerprints(config)
    calls = {'verify': lambda: verify_envelope(envelope),
             'validate': lambda: validate_package(envelope, context, sidecar),
             'projection': lambda: package_projection(envelope),
             'qualify': lambda: qualify(config, handle, sidecar['object_id']),
             'register': lambda: op.register(eid, confirm=eid),
             'source': lambda: op.source(envelope, handle),
             'execute': lambda: op.execute(eid, confirm=eid),
             'reconcile': lambda: op.reconcile(eid)}
    with pytest.raises(BoundaryError, match='RUNTIME_IDENTITY_MISMATCH'):
        calls[entry]()
    assert fingerprints(config) == before


@pytest.mark.parametrize('field', ['runtime_identity', 'contract_sha256', 'source_sha256', 'binding'])
def test_envelope_tampering_is_not_historical_verification(history, field):
    config, handle, envelope, _ = history
    bad = copy.deepcopy(envelope)
    bad[field] = {**bad[field], 'review_id': 'tampered'} if field == 'binding' else '0' * 64
    # Recomputing a content hash cannot replace the immutable registered object identity.
    replace_stored(config, 'operational_packages', handle, reseal(bad, 'OPERATIONAL'),
                   update_id=field != 'runtime_identity')
    errors = {'runtime_identity': 'ARTIFACT_IDENTITY_MISMATCH', 'contract_sha256': 'ADAPTER_VERSION_MISMATCH',
              'source_sha256': 'SOURCE_MATERIALIZATION_MISMATCH', 'binding': 'ATTRIBUTION_BASIS_MISMATCH'}
    with pytest.raises(BoundaryError, match=errors[field]):
        registered_historical_read(config, handle)


@pytest.mark.parametrize('field,value', [
    ('envelope_id', 'OPERATIONAL_' + '0' * 64), ('post_state_sha256', '0' * 64),
    ('actual_mutation_counts', {}), ('keys_touched', []), ('source_sha256', '0' * 64),
    ('status', 'PENDING'), ('transaction_result', 'ROLLED_BACK'), ('binding', {}),
])
def test_even_rehashed_registered_receipt_must_match_all_evidence(history, field, value):
    config, handle, _, receipt = history
    bad = reseal({**receipt, field: value}, 'EXECUTION')
    replace_stored(config, 'operational_receipts', handle, bad)
    with pytest.raises(BoundaryError):
        registered_historical_read(config, handle)


def test_unregistered_receipt_and_pending_old_package(history):
    config, handle, envelope, receipt = history
    with pytest.raises(BoundaryError, match='RECEIPT_NOT_REGISTERED'):
        reconcile_registered(config, handle, 'EXECUTION_' + '0' * 64)
    replace_stored(config, 'operational_receipts', handle, None)
    result = registered_historical_read(config, handle)
    assert result['receipt'] is None
    assert result['qualification']['operator_status'] == 'AWAITING_OPERATOR_ACTION'
    assert result['qualification']['historical_read_verified']
    assert not result['qualification']['executable_under_current_runtime']
    with pytest.raises(BoundaryError, match='RECEIPT_NOT_REGISTERED'):
        reconcile_registered(config, handle, receipt['object_id'])
    with pytest.raises(BoundaryError, match='RUNTIME_IDENTITY_MISMATCH'):
        verify_envelope(envelope)


@pytest.mark.parametrize('fault', ['post_state', 'materialized_source', 'receipt_hash', 'receipt_registration', 'native_seal', 'attribution'])
def test_corrupt_history_fails_closed(history, fault):
    config, handle, envelope, receipt = history
    if fault == 'post_state':
        # Corrupt an object covered by this receipt. An unrelated catalog change
        # now has the distinct STATE_PROOF_INCOMPLETE result (continuity tests).
        claim_id = next(r['key']['claim_id'] for r in envelope['predicted_diff']['inserts'] if r['table'] == 'claims')
        with sqlite3.connect(config.knowledge_db) as db:
            db.execute("UPDATE claims SET statement='isolated corruption' WHERE claim_id=?", (claim_id,))
    elif fault == 'materialized_source':
        (config.knowledge_db.parent / 'operational_sources' / envelope['source_sha256']).write_bytes(b'corrupt')
    elif fault == 'receipt_hash':
        replace_stored(config, 'operational_receipts', handle, {**receipt, 'sha256': '0' * 64})
    elif fault == 'receipt_registration':
        replace_stored(config, 'operational_receipts', handle, {**receipt, 'object_id': 'EXECUTION_' + '0' * 64})
    elif fault == 'attribution':
        replace_stored(config, 'attribution_objects', handle, {**envelope['attribution'], 'sha256': '0' * 64})
    else:
        with sqlite3.connect(config.state_db) as db:
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='sealed_review_artifacts'").fetchall():
                db.execute('DROP TRIGGER "' + row[0] + '"')
            db.execute("UPDATE sealed_review_artifacts SET body=? WHERE artifact_id=?", (b'{}', handle))
    with pytest.raises((BoundaryError, ValueError, KeyError)):
        registered_historical_read(config, handle)
