"""Privileged Stage 3 View operator. The HTTP application never imports this module."""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tomllib

from .current_view_workbench import (ENTRY_VERSION, VERSION, CurrentViewWorkbench,
                                     verify_package)
from .operational_contract import WEB_REQUEST, identity, require, sealed, snapshot, verify
from .production_promotion import canonical_sha256
from .workbench.config import BoundaryError, WorkbenchConfig, checked_path
from .workbench.store import Store


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True)
class ViewOperatorConfig:
    workbench: WorkbenchConfig
    ledger: Path

    @classmethod
    def load(cls, path):
        path = checked_path(Path(path))
        raw = tomllib.loads(path.read_text(encoding='utf-8'))['view_operator']
        require(set(raw) == {'workbench_config', 'ledger'}, 'OPERATOR_CONFIG_INVALID')
        return cls(WorkbenchConfig.load(checked_path(path.parent / raw['workbench_config'])),
                   checked_path(path.parent / raw['ledger'], missing=True))

    def paths(self):
        target = checked_path(self.workbench.knowledge_db)
        ledger = checked_path(self.ledger, missing=True)
        state = checked_path(self.workbench.state_db)
        artifacts = checked_path(self.workbench.artifact_root)
        require(ledger != target and ledger != state and not ledger.is_relative_to(artifacts)
                and not ledger.is_relative_to(state.parent) and not target.is_relative_to(ledger.parent),
                'OPERATOR_NOT_ISOLATED')
        for path in (target, ledger):
            for suffix in ('-journal', '-wal', '-shm'):
                require(not checked_path(Path(str(path) + suffix), missing=True).exists(), 'RECOVERY_REQUIRED')
        self.workbench.validate()
        return target, ledger


class ViewOperator:
    def __init__(self, config):
        self.config = config

    def initialize(self):
        require(not WEB_REQUEST.get(), 'WEB_VIEW_ACTIVATION_FORBIDDEN')
        target, ledger = self.config.paths()
        require(not ledger.exists(), 'OPERATOR_ALREADY_INITIALIZED')
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open('xb'):
            pass
        with closing(sqlite3.connect(ledger)) as connection, connection:
            connection.execute('CREATE TABLE operator_meta(target TEXT PRIMARY KEY,entry_version TEXT NOT NULL)')
            connection.execute('INSERT INTO operator_meta VALUES(?,?)', (str(target), ENTRY_VERSION))
            connection.execute("""CREATE TABLE grants(package_id TEXT PRIMARY KEY,node_id TEXT NOT NULL,
                target_file_id TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL
                CHECK(status IN ('READY','CONSUMED')),receipt TEXT)""")
            connection.execute('CREATE TABLE execution_failures(attempt_id INTEGER PRIMARY KEY,event TEXT NOT NULL)')
            connection.execute("CREATE TRIGGER consumed_immutable BEFORE UPDATE ON grants WHEN OLD.status='CONSUMED' BEGIN SELECT RAISE(ABORT,'ALREADY_CONSUMED'); END")
            connection.execute("CREATE TRIGGER grants_delete_forbidden BEFORE DELETE ON grants BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        return {'status': 'VIEW_OPERATOR_READY', 'entry_version': ENTRY_VERSION}

    def connect(self):
        require(not WEB_REQUEST.get(), 'WEB_VIEW_ACTIVATION_FORBIDDEN')
        target, ledger = self.config.paths()
        require(ledger.is_file(), 'OPERATOR_NOT_INITIALIZED')
        connection = sqlite3.connect(ledger.as_uri() + '?mode=rw', uri=True, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('ATTACH DATABASE ? AS canonical', (target.as_uri() + '?mode=rw',))
            for schema in ('main', 'canonical'):
                require(connection.execute(f'PRAGMA {schema}.journal_mode').fetchone()[0] == 'delete', 'JOURNAL_MODE_UNSUPPORTED')
                connection.execute(f'PRAGMA {schema}.synchronous=FULL')
                require(connection.execute(f'PRAGMA {schema}.integrity_check').fetchone()[0] == 'ok', 'RECOVERY_REQUIRED')
            connection.execute('PRAGMA foreign_keys=ON')
            rows = connection.execute('SELECT * FROM operator_meta').fetchall()
            require(len(rows) == 1 and dict(rows[0]) == {'target': str(target), 'entry_version': ENTRY_VERSION},
                    'OPERATOR_BINDING_MISMATCH')
            return connection
        except BaseException:
            connection.close()
            raise

    def package(self, package_id):
        with Store(self.config.workbench).connect() as connection:
            row = connection.execute('SELECT body FROM view_activation_packages WHERE object_id=?', (package_id,)).fetchone()
        require(row is not None, 'PACKAGE_NOT_REGISTERED')
        package = json.loads(row[0])
        verify_package(package)
        require(package['object_id'] == package_id, 'PACKAGE_IDENTITY_MISMATCH')
        return package

    def register(self, package_id, *, confirm):
        require(confirm == package_id, 'OPERATOR_CONFIRMATION_REQUIRED')
        target, _ledger = self.config.paths()
        package = self.package(package_id)
        state = CurrentViewWorkbench(self.config.workbench).read(package['node_id'])
        draft = state['draft']
        require(draft and draft['draft_id'] == package['draft_id'] and
                draft['revision'] == package['draft_revision'] and draft['status'] == 'VALIDATED',
                'DRAFT_IDENTITY_MISMATCH')
        require(draft['basis_sha256'] == package['draft_basis_sha256'], 'BASELINE_STALE')
        primary = [item['claim_id'] for item in package['evidence_basis']['primary']]
        context = [item['claim_id'] for item in package['evidence_basis']['context']]
        row = package['predicted_diff']['row']
        require(primary == draft['primary_claim_ids'] and context == draft['context_claim_ids'] and
                json.loads(row['content_json']) == draft['content'] and
                json.loads(row['trigger_claim_ids_json']) == draft['primary_claim_ids'] and
                row['change_level'] == draft['change_level'], 'DRAFT_IDENTITY_MISMATCH')
        require(identity(target) == package['baseline'], 'BASELINE_STALE')
        with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            require(canonical_sha256(snapshot(connection)) == package['predicted_diff']['pre_state_sha256'],
                    'PREDICTED_DIFF_MISMATCH')
        info = target.stat()
        file_id = encode([info.st_dev, info.st_ino])
        with closing(self.connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            existing = connection.execute('SELECT * FROM grants WHERE package_id=?', (package_id,)).fetchone()
            if existing:
                require(existing['body'] == encode(package) and existing['target_file_id'] == file_id,
                        'GRANT_IDENTITY_MISMATCH')
                require(existing['status'] == 'READY', 'ALREADY_CONSUMED')
            else:
                connection.execute("INSERT INTO grants VALUES(?,?,?,?, 'READY',NULL)",
                                   (package_id, package['node_id'], file_id, encode(package)))
        return {'status': 'REGISTERED_VIEW_GRANT', 'package_id': package_id}

    def execute(self, package_id, *, confirm, fault=None):
        require(confirm == package_id, 'OPERATOR_CONFIRMATION_REQUIRED')
        target, _ledger = self.config.paths()
        with closing(self.connect()) as connection:
            committed = attempted_commit = False
            try:
                connection.execute('BEGIN IMMEDIATE')
                grant = connection.execute('SELECT * FROM grants WHERE package_id=?', (package_id,)).fetchone()
                require(grant is not None, 'GRANT_NOT_REGISTERED')
                require(grant['status'] == 'READY', 'ALREADY_CONSUMED')
                package = json.loads(grant['body'])
                verify_package(package)
                info = target.stat()
                require(grant['target_file_id'] == encode([info.st_dev, info.st_ino]), 'TARGET_IDENTITY_MISMATCH')
                require(identity(target) == package['baseline'], 'BASELINE_STALE')
                before = snapshot(connection, 'canonical')
                require(canonical_sha256(before) == package['predicted_diff']['pre_state_sha256'], 'PREDICTED_DIFF_MISMATCH')
                row = package['predicted_diff']['row']
                connection.set_authorizer(_authorizer)
                columns = list(row)
                sql = 'INSERT INTO canonical.current_views(' + ','.join('"' + name + '"' for name in columns) + ') VALUES(' + ','.join('?' for _ in columns) + ')'
                connection.execute(sql, tuple(row[name] for name in columns))
                if fault:
                    fault('insert', None)
                require(not connection.execute('PRAGMA canonical.foreign_key_check').fetchall(), 'POST_FOREIGN_KEY_FAILURE')
                post = snapshot(connection, 'canonical')
                require(canonical_sha256(post) == package['predicted_diff']['post_state_sha256'], 'POST_STATE_MISMATCH')
                require(canonical_sha256({k:v for k,v in post.items() if k != 'current_views'}) ==
                        package['predicted_diff']['unrelated_tables_sha256'], 'UNRELATED_TABLE_CHANGED')
                receipt = sealed({'document_type': 'phase42_view_execution_receipt',
                    'adapter_version': VERSION, 'operator_entry_version': ENTRY_VERSION,
                    'package_id': package_id, 'node_id': package['node_id'],
                    'draft_id': package['draft_id'], 'draft_revision': package['draft_revision'],
                    'baseline_sha256': package['baseline']['sha256'],
                    'predicted_diff_id': package['predicted_diff']['object_id'],
                    'evidence_basis_id': package['evidence_basis']['object_id'],
                    'actual_mutation_counts': {'current_views': 1},
                    'keys_touched': [{'table': 'current_views', 'key': package['predicted_diff']['key']}],
                    'post_state_sha256': package['predicted_diff']['post_state_sha256'],
                    'transaction_result': 'COMMITTED', 'status': 'EXECUTED',
                    'timestamp': datetime.now(timezone.utc).isoformat()}, 'VIEWEXECUTION')
                connection.execute("UPDATE grants SET status='CONSUMED',receipt=? WHERE package_id=?",
                                   (encode(receipt), package_id))
                if fault:
                    fault('before_commit', None)
                attempted_commit = True
                connection.commit()
                committed = True
                if fault:
                    fault('after_commit', None)
                return self.export(receipt, fault=fault)
            except BaseException as error:
                connection.set_authorizer(None)
                if not committed:
                    connection.rollback()
                if committed or attempted_commit:
                    raise BoundaryError('RECOVERY_REQUIRED') from None
                failure = sealed({'package_id': package_id, 'status': 'ROLLED_BACK',
                    'transaction_result': 'NOT_COMMITTED', 'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error_code': str(error) if isinstance(error, BoundaryError) else 'EXECUTION_FAILED'},
                    'FAILED_VIEW_EXECUTION')
                connection.execute('INSERT INTO execution_failures(event) VALUES(?)', (encode(failure),))
                connection.commit()
                raise

    def export(self, receipt, *, fault=None):
        _target, ledger = self.config.paths()
        directory = checked_path(ledger.parent / 'receipts', missing=True)
        directory.mkdir(exist_ok=True)
        path = checked_path(directory / (receipt['object_id'] + '.json'), missing=True)
        if fault:
            fault('receipt_export', None)
        body = encode(receipt).encode('utf-8')
        if path.exists():
            require(path.read_bytes() == body, 'RECOVERY_REQUIRED')
        else:
            with path.open('xb') as output:
                output.write(body)
                output.flush()
                os.fsync(output.fileno())
        return receipt

    def reconcile(self, package_id):
        with closing(self.connect()) as connection:
            connection.execute('BEGIN IMMEDIATE')
            grant = connection.execute('SELECT * FROM grants WHERE package_id=?', (package_id,)).fetchone()
            require(grant and grant['status'] == 'CONSUMED' and grant['receipt'], 'RECOVERY_REQUIRED')
            package, receipt = json.loads(grant['body']), json.loads(grant['receipt'])
            verify_package(package)
            verify(receipt, 'VIEWEXECUTION')
            require(receipt['package_id'] == package_id and receipt['adapter_version'] == VERSION and
                    receipt['predicted_diff_id'] == package['predicted_diff']['object_id'] and
                    receipt['evidence_basis_id'] == package['evidence_basis']['object_id'] and
                    receipt['post_state_sha256'] == canonical_sha256(snapshot(connection, 'canonical')) ==
                    package['predicted_diff']['post_state_sha256'], 'RECOVERY_REQUIRED')
            self.export(receipt)
            with Store(self.config.workbench).connect(operator_write=True) as workbench:
                prior = workbench.execute('SELECT body FROM view_activation_receipts WHERE package_id=?', (package_id,)).fetchone()
                if prior:
                    require(json.loads(prior[0]) == receipt, 'RECEIPT_CONFLICT')
                else:
                    workbench.execute('INSERT INTO view_activation_receipts VALUES(?,?,?,?)',
                                      (receipt['object_id'], package_id, package['node_id'], encode(receipt)))
            return receipt


def _authorizer(action, table, column, database, trigger):
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
        if database == 'canonical':
            return sqlite3.SQLITE_OK if action == sqlite3.SQLITE_INSERT and table == 'current_views' and not trigger else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if database == 'main' and table == 'grants' and action == sqlite3.SQLITE_UPDATE else sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
                  sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    for name in ('inspect', 'register', 'execute', 'reconcile'):
        sub = commands.add_parser(name)
        sub.add_argument('--package', required=True)
        if name in ('register', 'execute'):
            sub.add_argument('--confirm', required=True)
    args = parser.parse_args()
    try:
        operator = ViewOperator(ViewOperatorConfig.load(args.config))
        if args.command == 'init':
            result = operator.initialize()
        elif args.command == 'inspect':
            result = operator.package(args.package)
        elif args.command == 'register':
            result = operator.register(args.package, confirm=args.confirm)
        elif args.command == 'execute':
            result = operator.execute(args.package, confirm=args.confirm)
        else:
            result = operator.reconcile(args.package)
        print(encode(result))
    except Exception as error:
        parser.exit(1, str(error) + '\n' if isinstance(error, BoundaryError) else 'VIEW_OPERATOR_UNAVAILABLE\n')


if __name__ == '__main__':
    main()
