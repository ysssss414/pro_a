"""Explicit Workbench schema 5 preparation for Impact attention state."""
from __future__ import annotations

import hashlib
import os

from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


def prepare_impact(config):
    config.validate()
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version == '5':
            return {'status': 'ALREADY_PREPARED', 'schema_version': '5'}
        if version != '4':
            raise BoundaryError('CURRENT_VIEW_SCHEMA_REQUIRED')
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + '.stage3-backup'), missing=True)
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
        if schema_version(connection) != '4':
            raise BoundaryError('WORKBENCH_SCHEMA_CHANGED')
        connection.execute('''CREATE TABLE impact_attention_states(
            impact_id TEXT PRIMARY KEY,snapshot_id TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK(outcome IN ('NO_CHANGE','MINOR','MATERIAL','THESIS')),
            revision INTEGER NOT NULL CHECK(revision>0),reviewer TEXT NOT NULL,
            actor TEXT NOT NULL,reason TEXT NOT NULL,updated_at TEXT NOT NULL)''')
        connection.execute('''CREATE TABLE impact_attention_events(
            impact_id TEXT NOT NULL,revision INTEGER NOT NULL,operation_id TEXT NOT NULL,
            request_sha256 TEXT NOT NULL,event_json TEXT NOT NULL,response_json TEXT NOT NULL,
            PRIMARY KEY(impact_id,revision),UNIQUE(impact_id,operation_id))''')
        for action in ('UPDATE', 'DELETE'):
            connection.execute(f"CREATE TRIGGER impact_attention_events_{action.lower()}_forbidden BEFORE {action} ON impact_attention_events BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute("CREATE TRIGGER impact_attention_states_delete_forbidden BEFORE DELETE ON impact_attention_states BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute("UPDATE workbench_meta SET value='5' WHERE key='schema_version'")
    return {'status': 'IMPACT_SCHEMA_PREPARED', 'schema_version': '5',
            'backup_sha256': hashlib.sha256(content).hexdigest()}
