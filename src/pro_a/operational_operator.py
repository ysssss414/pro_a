"""Privileged external operator entry. Never imported by the Workbench HTTP app."""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tomllib

from .operational_contract import (ENTRY_VERSION, KEYS, VERSION, WEB_REQUEST, identity, predicted_diff, readonly,
                                   require, sealed, snapshot, verify, verify_envelope)
from .operational_qualification import materialized_source, validate_package
from .production_promotion import canonical_sha256
from .workbench.attribution import Attribution
from .workbench.config import BoundaryError, WorkbenchConfig, checked_path
from .workbench.review_workbench import encode
from .workbench.store import Store


@dataclass(frozen=True)
class OperatorConfig:
    workbench: WorkbenchConfig
    ledger: Path

    @classmethod
    def load(cls, path):
        path = checked_path(Path(path))
        raw = tomllib.loads(path.read_text(encoding='utf-8'))['operator']
        require(set(raw) == {'workbench_config', 'ledger'}, 'OPERATOR_CONFIG_INVALID')
        return cls(WorkbenchConfig.load(checked_path(path.parent / raw['workbench_config'])), checked_path(path.parent / raw['ledger'], missing=True))

    def paths(self):
        target = checked_path(self.workbench.knowledge_db)
        ledger = checked_path(self.ledger, missing=True)
        artifacts, state = checked_path(self.workbench.artifact_root), checked_path(self.workbench.state_db)
        require(ledger != target and ledger != state and not ledger.is_relative_to(artifacts) and
                not ledger.is_relative_to(state.parent) and not target.is_relative_to(ledger.parent), 'OPERATOR_NOT_ISOLATED')
        for path in (target, ledger):
            for suffix in ('-journal', '-wal', '-shm'):
                require(not checked_path(Path(str(path) + suffix), missing=True).exists(), 'RECOVERY_REQUIRED')
        self.workbench.validate()
        return target, ledger


class Operator:
    def __init__(self, config): self.config = config

    def initialize(self):
        require(not WEB_REQUEST.get(), 'WEB_APPLY_FORBIDDEN')
        target, ledger = self.config.paths()
        require(not ledger.exists(), 'OPERATOR_ALREADY_INITIALIZED')
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open('xb'): pass
        with closing(sqlite3.connect(ledger)) as connection, connection:
            connection.execute('CREATE TABLE operator_meta(target TEXT PRIMARY KEY,entry_version TEXT NOT NULL)')
            connection.execute('INSERT INTO operator_meta VALUES(?,?)', (str(target), ENTRY_VERSION))
            connection.execute("CREATE TABLE grants(envelope_id TEXT PRIMARY KEY,artifact_id TEXT NOT NULL,target_file_id TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('READY','CONSUMED')),receipt TEXT)")
            connection.execute('CREATE TABLE execution_failures(attempt_id INTEGER PRIMARY KEY,event TEXT NOT NULL)')
            connection.execute("CREATE TRIGGER consumed_immutable BEFORE UPDATE ON grants WHEN OLD.status='CONSUMED' BEGIN SELECT RAISE(ABORT,'ALREADY_CONSUMED'); END")
            connection.execute("CREATE TRIGGER grant_delete_forbidden BEFORE DELETE ON grants BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")

    def connect(self):
        require(not WEB_REQUEST.get(), 'WEB_APPLY_FORBIDDEN')
        target, ledger = self.config.paths()
        require(ledger.is_file(), 'OPERATOR_NOT_INITIALIZED')
        # Both file-backed DBs participate in one rollback-journal transaction.
        # Leftover journals are blocked by paths(); ambiguous recovery is operator-owned.
        connection = sqlite3.connect(ledger.as_uri() + '?mode=rw', uri=True, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('ATTACH DATABASE ? AS canonical', (target.as_uri() + '?mode=rw',))
            for schema in ('main', 'canonical'):
                require(connection.execute(f'PRAGMA {schema}.journal_mode').fetchone()[0] == 'delete', 'JOURNAL_MODE_UNSUPPORTED')
                connection.execute(f'PRAGMA {schema}.synchronous=FULL')
                require(connection.execute(f'PRAGMA {schema}.integrity_check').fetchone()[0] == 'ok', 'RECOVERY_REQUIRED')
            connection.execute('PRAGMA foreign_keys=ON')
            row = connection.execute('SELECT * FROM operator_meta').fetchall()
            require(len(row) == 1 and dict(row[0]) == {'target': str(target), 'entry_version': ENTRY_VERSION}, 'OPERATOR_BINDING_MISMATCH')
            return connection
        except BaseException:
            connection.close(); raise

    def register(self, envelope_id, *, confirm):
        require(confirm == envelope_id, 'OPERATOR_CONFIRMATION_REQUIRED')
        target, _ = self.config.paths()
        with Store(self.config.workbench).connect() as connection:
            row = connection.execute('SELECT artifact_id,body FROM operational_packages WHERE object_id=?', (envelope_id,)).fetchone()
        require(row is not None, 'PACKAGE_NOT_REGISTERED')
        artifact_id, envelope = row[0], json.loads(row[1])
        context, sidecar = Attribution(self.config.workbench).sealed_context(artifact_id)
        validate_package(envelope, context, sidecar)
        require(envelope['object_id'] == envelope_id, 'ARTIFACT_IDENTITY_MISMATCH')
        require(identity(target) == envelope['baseline'], 'STALE_BASELINE')
        with closing(readonly(target)) as connection:
            require(predicted_diff(connection, envelope['mutations']) == envelope['predicted_diff'], 'PREDICTED_DIFF_MISMATCH')
        info = target.stat()
        file_id = encode([info.st_dev, info.st_ino])
        with closing(self.connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            existing = connection.execute('SELECT * FROM grants WHERE envelope_id=?', (envelope_id,)).fetchone()
            if existing:
                require(existing['body'] == encode(envelope) and existing['target_file_id'] == file_id, 'GRANT_IDENTITY_MISMATCH')
                require(existing['status'] == 'READY', 'ALREADY_CONSUMED')
            else: connection.execute("INSERT INTO grants VALUES(?,?,?,?,'READY',NULL)", (envelope_id, artifact_id, file_id, encode(envelope)))
        return {'status': 'REGISTERED_OPERATOR_GRANT', 'envelope_id': envelope_id}

    def source(self, envelope, artifact_id):
        context, sidecar = Attribution(self.config.workbench).sealed_context(artifact_id)
        validate_package(envelope, context, sidecar)
        body = materialized_source(context)
        target, _ = self.config.paths()
        directory = checked_path(target.parent / 'operational_sources', missing=True)
        require(not directory.is_relative_to(self.config.workbench.artifact_root), 'SOURCE_DESTINATION_INVALID')
        directory.mkdir(exist_ok=True)
        path = checked_path(directory / envelope['source_sha256'], missing=True)
        if not path.exists():
            with path.open('xb') as output:
                output.write(body); output.flush(); os.fsync(output.fileno())
        require(path.read_bytes() == body, 'SOURCE_MATERIALIZATION_MISMATCH')
        return path

    def execute(self, envelope_id, *, confirm, fault=None):
        """Consume a registered operator grant. There is no raw-mutations writer API."""
        require(confirm == envelope_id, 'OPERATOR_CONFIRMATION_REQUIRED')
        target, _ = self.config.paths()
        with closing(self.connect()) as connection:
            committed = attempted_commit = False
            try:
                connection.execute('BEGIN IMMEDIATE')
                grant = connection.execute('SELECT * FROM grants WHERE envelope_id=?', (envelope_id,)).fetchone()
                require(grant is not None, 'GRANT_NOT_REGISTERED')
                require(grant['status'] == 'READY', 'ALREADY_CONSUMED')
                envelope = json.loads(grant['body']); verify_envelope(envelope)
                info = target.stat()
                require(grant['target_file_id'] == encode([info.st_dev, info.st_ino]), 'TARGET_IDENTITY_MISMATCH')
                # The reservation lock holds the baseline stable while reads use a separate RO handle.
                require(identity(target) == envelope['baseline'], 'STALE_BASELINE')
                source = self.source(envelope, grant['artifact_id'])
                require(canonical_sha256(snapshot(connection, 'canonical')) == envelope['predicted_diff']['pre_state_sha256'], 'PREDICTED_DIFF_MISMATCH')
                connection.set_authorizer(_authorizer)
                for index, item in enumerate(envelope['predicted_diff']['inserts']):
                    require(item['table'] in KEYS, 'UNSUPPORTED_MUTATION')
                    columns = list(item['row'])
                    sql = f'INSERT INTO canonical."{item["table"]}"(' + ','.join('"' + c + '"' for c in columns) + ') VALUES(' + ','.join('?' for c in columns) + ')'
                    connection.execute(sql, tuple(item['row'][c] for c in columns))
                    if fault: fault('insert', index)
                require(not connection.execute('PRAGMA canonical.foreign_key_check').fetchall(), 'POST_FOREIGN_KEY_FAILURE')
                post = canonical_sha256(snapshot(connection, 'canonical'))
                require(post == envelope['predicted_diff']['post_state_sha256'], 'POST_STATE_MISMATCH')
                require(hashlib.sha256(checked_path(source).read_bytes()).hexdigest() == envelope['source_sha256'], 'SOURCE_MATERIALIZATION_MISMATCH')
                counts = {}
                for row in envelope['predicted_diff']['inserts']: counts[row['table']] = counts.get(row['table'], 0) + 1
                receipt = sealed({'document_type': 'phase42_operational_execution_receipt', 'adapter_version': VERSION, 'operator_entry_version': ENTRY_VERSION,
                    'envelope_id': envelope_id, 'binding': envelope['binding'], 'attribution_id': envelope['attribution']['object_id'],
                    'baseline_sha256': envelope['baseline']['sha256'], 'predicted_diff_id': envelope['predicted_diff']['object_id'],
                    'actual_mutation_counts': counts, 'tables_touched': sorted(counts),
                    'keys_touched': [{'table': r['table'], 'key': r['key']} for r in envelope['predicted_diff']['inserts']],
                    'post_state_sha256': post, 'source_sha256': envelope['source_sha256'], 'transaction_result': 'COMMITTED',
                    'status': 'EXECUTED', 'timestamp': datetime.now(timezone.utc).isoformat()}, 'EXECUTION')
                connection.execute("UPDATE grants SET status='CONSUMED',receipt=? WHERE envelope_id=?", (encode(receipt), envelope_id))
                if fault: fault('before_commit', None)
                attempted_commit = True
                connection.commit(); committed = True
                if fault: fault('after_commit', None)
                return self.export_receipt(receipt, fault=fault)
            except BaseException as error:
                connection.set_authorizer(None)
                if not committed: connection.rollback()
                # A durable ledger receipt takes precedence after commit; never reset consumption.
                if committed or attempted_commit: raise BoundaryError('RECOVERY_REQUIRED') from None
                failure = sealed({'envelope_id': envelope_id, 'status': 'ROLLED_BACK', 'transaction_result': 'NOT_COMMITTED',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error_code': str(error) if isinstance(error, BoundaryError) else 'EXECUTION_FAILED'}, 'FAILED_EXECUTION')
                connection.execute('INSERT INTO execution_failures(event) VALUES(?)', (encode(failure),)); connection.commit()
                raise

    def export_receipt(self, receipt, *, fault=None):
        _, ledger = self.config.paths()
        directory = checked_path(ledger.parent / 'receipts', missing=True); directory.mkdir(exist_ok=True)
        path = checked_path(directory / (receipt['object_id'] + '.json'), missing=True)
        if fault: fault('receipt_export', None)
        body = encode(receipt).encode('utf-8')
        if path.exists(): require(path.read_bytes() == body, 'RECOVERY_REQUIRED')
        else:
            with path.open('xb') as output:
                output.write(body); output.flush(); os.fsync(output.fileno())
        return receipt

    def reconcile(self, envelope_id):
        """Operator verifies durable ledger/post-state and registers an opaque receipt."""
        target, _ = self.config.paths()
        with closing(self.connect()) as connection:
            connection.execute('BEGIN IMMEDIATE')
            grant = connection.execute('SELECT * FROM grants WHERE envelope_id=?', (envelope_id,)).fetchone()
            require(grant is not None and grant['status'] == 'CONSUMED' and grant['receipt'], 'RECOVERY_REQUIRED')
            envelope, receipt = json.loads(grant['body']), json.loads(grant['receipt'])
            verify_envelope(envelope); verify(receipt, 'EXECUTION')
            require(receipt['envelope_id'] == envelope_id and receipt['binding'] == envelope['binding'] and
                    receipt['attribution_id'] == envelope['attribution']['object_id'] and receipt['baseline_sha256'] == envelope['baseline']['sha256'] and
                    receipt['predicted_diff_id'] == envelope['predicted_diff']['object_id'] and receipt['adapter_version'] == VERSION and
                    receipt['post_state_sha256'] == canonical_sha256(snapshot(connection, 'canonical')) == envelope['predicted_diff']['post_state_sha256'], 'RECOVERY_REQUIRED')
            self.source(envelope, grant['artifact_id'])
            self.export_receipt(receipt)
            with Store(self.config.workbench).connect(operator_write=True) as workbench:
                prior = workbench.execute('SELECT body FROM operational_receipts WHERE artifact_id=?', (grant['artifact_id'],)).fetchone()
                if prior: require(json.loads(prior[0]) == receipt, 'RECEIPT_CONFLICT')
                else: workbench.execute('INSERT INTO operational_receipts VALUES(?,?,?)', (grant['artifact_id'], receipt['object_id'], encode(receipt)))
            return receipt


def _authorizer(action, table, column, database, trigger):
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
        if database == 'canonical':
            return sqlite3.SQLITE_OK if action == sqlite3.SQLITE_INSERT and table in KEYS and not trigger else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if database == 'main' and table == 'grants' and action == sqlite3.SQLITE_UPDATE else sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    for name in ('register', 'execute', 'reconcile', 'inspect'):
        sub = commands.add_parser(name); sub.add_argument('--envelope', required=True)
        if name in ('register', 'execute'): sub.add_argument('--confirm', required=True)
    args = parser.parse_args()
    try:
        operator = Operator(OperatorConfig.load(args.config))
        if args.command == 'init': result = operator.initialize() or {'status': 'OPERATOR_READY'}
        elif args.command == 'register': result = operator.register(args.envelope, confirm=args.confirm)
        elif args.command == 'execute': result = operator.execute(args.envelope, confirm=args.confirm)
        elif args.command == 'reconcile': result = operator.reconcile(args.envelope)
        else:
            with Store(operator.config.workbench).connect() as connection:
                row = connection.execute('SELECT body FROM operational_packages WHERE object_id=?', (args.envelope,)).fetchone()
            require(row is not None, 'PACKAGE_NOT_REGISTERED'); result = json.loads(row[0]); verify_envelope(result)
        print(encode(result))
    except Exception as error:
        parser.exit(1, str(error) + '\n' if isinstance(error, BoundaryError) else 'OPERATOR_UNAVAILABLE\n')


if __name__ == '__main__': main()
