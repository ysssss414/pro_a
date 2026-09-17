"""Explicit Workbench schema 4 preparation for server-persisted View drafts."""
import hashlib
import os

from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


def prepare_current_views(config):
    config.validate()
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version in ('4', '5', '6', '7', '8', '9'):
            return {'status': 'ALREADY_PREPARED', 'schema_version': version}
        if version != '3':
            raise BoundaryError('ATTRIBUTION_SCHEMA_REQUIRED')
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + '.stage2-backup'), missing=True)
    content = path.read_bytes()
    if backup.exists():
        if backup.read_bytes() != content:
            raise BoundaryError('WORKBENCH_BACKUP_CONFLICT')
    else:
        with backup.open('xb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
    with Store(config).connect(operator_write=True) as connection:
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        if schema_version(connection) != '3':
            raise BoundaryError('WORKBENCH_SCHEMA_CHANGED')
        connection.execute('''CREATE TABLE view_drafts(
            node_id TEXT PRIMARY KEY,draft_id TEXT UNIQUE NOT NULL,revision INTEGER NOT NULL,
            basis_sha256 TEXT NOT NULL,reviewer TEXT NOT NULL,status TEXT NOT NULL,
            body TEXT NOT NULL,updated_at TEXT NOT NULL)''')
        connection.execute('''CREATE TABLE view_draft_events(
            node_id TEXT NOT NULL,revision INTEGER NOT NULL,operation_id TEXT NOT NULL,
            request_sha256 TEXT NOT NULL,event_json TEXT NOT NULL,response_json TEXT NOT NULL,
            PRIMARY KEY(node_id,revision),UNIQUE(node_id,operation_id))''')
        connection.execute('''CREATE TABLE view_activation_packages(
            object_id TEXT PRIMARY KEY,node_id TEXT NOT NULL,draft_revision INTEGER NOT NULL,body TEXT NOT NULL)''')
        connection.execute('''CREATE TABLE view_activation_receipts(
            object_id TEXT PRIMARY KEY,package_id TEXT UNIQUE NOT NULL,node_id TEXT NOT NULL,body TEXT NOT NULL)''')
        for table in ('view_draft_events', 'view_activation_packages', 'view_activation_receipts'):
            for action in ('UPDATE', 'DELETE'):
                connection.execute(f"CREATE TRIGGER {table}_{action.lower()}_forbidden BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute('CREATE TRIGGER view_drafts_delete_forbidden BEFORE DELETE ON view_drafts BEGIN SELECT RAISE(ABORT,\'APPEND_ONLY\'); END')
        connection.execute("UPDATE workbench_meta SET value='4' WHERE key='schema_version'")
    return {'status': 'CURRENT_VIEW_SCHEMA_PREPARED', 'schema_version': '4',
            'backup_sha256': hashlib.sha256(content).hexdigest()}
