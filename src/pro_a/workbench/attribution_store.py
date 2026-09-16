"""Explicit Workbench schema 3 preparation; no canonical schema change."""
import os
from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


def prepare_attribution(config):
    config.validate()
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version in ('3', '4', '5', '6', '7', '8'):
            return {'status': 'ALREADY_PREPARED', 'schema_version': version}
        if version != '2': raise BoundaryError('REVIEW_SCHEMA_REQUIRED')
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + '.stage1-backup'), missing=True)
    content = path.read_bytes()
    if backup.exists():
        if backup.read_bytes() != content: raise BoundaryError('WORKBENCH_BACKUP_CONFLICT')
    else:
        with backup.open('xb') as output:
            output.write(content); output.flush(); os.fsync(output.fileno())
    with Store(config).connect(operator_write=True) as connection:
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        if schema_version(connection) != '2': raise BoundaryError('WORKBENCH_SCHEMA_CHANGED')
        connection.execute('CREATE TABLE attribution_events(artifact_id TEXT NOT NULL,revision INTEGER NOT NULL,operation_id TEXT NOT NULL,request_sha256 TEXT NOT NULL,event_json TEXT NOT NULL,response_json TEXT NOT NULL,PRIMARY KEY(artifact_id,revision),UNIQUE(artifact_id,operation_id))')
        connection.execute('CREATE TABLE attribution_objects(artifact_id TEXT PRIMARY KEY,object_id TEXT UNIQUE NOT NULL,body TEXT NOT NULL)')
        connection.execute('CREATE TABLE operational_packages(artifact_id TEXT PRIMARY KEY,object_id TEXT UNIQUE NOT NULL,body TEXT NOT NULL)')
        connection.execute('CREATE TABLE operational_receipts(artifact_id TEXT PRIMARY KEY,object_id TEXT UNIQUE NOT NULL,body TEXT NOT NULL)')
        for table in ('attribution_events', 'attribution_objects', 'operational_packages', 'operational_receipts'):
            for action in ('UPDATE', 'DELETE'):
                connection.execute(f"CREATE TRIGGER {table}_{action.lower()}_forbidden BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute("UPDATE workbench_meta SET value='3' WHERE key='schema_version'")
    return {'status': 'ATTRIBUTION_SCHEMA_PREPARED', 'schema_version': '3'}
