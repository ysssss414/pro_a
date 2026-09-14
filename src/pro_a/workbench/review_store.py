"""Explicit Workbench-only schema preparation and transactional recovery."""
import hashlib
from pathlib import Path

from .config import BoundaryError, checked_path
from .store import Store


TABLES = (
    '''CREATE TABLE review_drafts(
        artifact_id TEXT PRIMARY KEY REFERENCES registered_packets(artifact_id),
        review_id TEXT UNIQUE NOT NULL, basis_id TEXT NOT NULL, reviewer TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision >= 0),
        status TEXT NOT NULL CHECK(status IN ('DRAFT','SEALED')),
        updated_at TEXT NOT NULL)''',
    '''CREATE TABLE review_decisions(
        artifact_id TEXT NOT NULL REFERENCES review_drafts(artifact_id),
        candidate_id TEXT NOT NULL, state_json TEXT NOT NULL,
        PRIMARY KEY(artifact_id,candidate_id))''',
    '''CREATE TABLE review_audit(
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id TEXT NOT NULL REFERENCES review_drafts(artifact_id),
        revision INTEGER NOT NULL, operation_id TEXT NOT NULL, candidate_id TEXT,
        event_type TEXT NOT NULL, old_json TEXT NOT NULL, new_json TEXT NOT NULL,
        actor TEXT NOT NULL, session_id TEXT NOT NULL, reviewer TEXT NOT NULL,
        reason TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE review_operations(
        artifact_id TEXT NOT NULL REFERENCES review_drafts(artifact_id),
        operation_id TEXT NOT NULL, request_sha256 TEXT NOT NULL, response_json TEXT NOT NULL,
        PRIMARY KEY(artifact_id,operation_id))''',
    '''CREATE TABLE sealed_review_artifacts(
        artifact_id TEXT NOT NULL REFERENCES review_drafts(artifact_id),
        kind TEXT NOT NULL CHECK(kind IN ('completed_packet','completion_receipt')),
        object_id TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL, body BLOB NOT NULL,
        PRIMARY KEY(artifact_id,kind))''',
)


def schema_version(connection):
    return connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0]


def prepare_reviews(config):
    """Operator-only v1 -> v2. Backup first; never migrate the knowledge DB."""
    config.validate()
    with Store(config).connect() as source:
        if schema_version(source) in ('2', '3', '4'):
            return {'status': 'ALREADY_PREPARED', 'schema_version': schema_version(source)}
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + '.stage0-backup'), missing=True)
    content = path.read_bytes()
    if backup.exists():
        if backup.read_bytes() != content:
            raise BoundaryError('WORKBENCH_BACKUP_CONFLICT')
    else:
        with backup.open('xb') as output:
            output.write(content)
            output.flush()
            import os
            os.fsync(output.fileno())
    with Store(config).connect(operator_write=True) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        if schema_version(connection) != '1':
            raise BoundaryError('WORKBENCH_SCHEMA_CHANGED')
        for statement in TABLES:
            connection.execute(statement)
        for table in ('review_audit', 'review_operations', 'sealed_review_artifacts'):
            for action in ('UPDATE', 'DELETE'):
                connection.execute(f"CREATE TRIGGER {table}_{action.lower()}_forbidden BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute("CREATE TRIGGER sealed_draft_immutable BEFORE UPDATE ON review_drafts WHEN OLD.status='SEALED' BEGIN SELECT RAISE(ABORT,'ALREADY_SEALED'); END")
        connection.execute("CREATE TRIGGER sealed_draft_delete_forbidden BEFORE DELETE ON review_drafts WHEN OLD.status='SEALED' BEGIN SELECT RAISE(ABORT,'ALREADY_SEALED'); END")
        connection.execute("CREATE TRIGGER sealed_audit_insert_forbidden BEFORE INSERT ON review_audit WHEN (SELECT status FROM review_drafts WHERE artifact_id=NEW.artifact_id)='SEALED' BEGIN SELECT RAISE(ABORT,'ALREADY_SEALED'); END")
        for action in ('INSERT', 'UPDATE', 'DELETE'):
            record = 'NEW' if action == 'INSERT' else 'OLD'
            connection.execute(f"CREATE TRIGGER sealed_decisions_{action.lower()}_forbidden BEFORE {action} ON review_decisions WHEN (SELECT status FROM review_drafts WHERE artifact_id={record}.artifact_id)='SEALED' BEGIN SELECT RAISE(ABORT,'ALREADY_SEALED'); END")
        connection.execute("UPDATE workbench_meta SET value='2' WHERE key='schema_version'")
    return {'status': 'REVIEW_SCHEMA_PREPARED', 'schema_version': '2', 'backup_sha256': hashlib.sha256(content).hexdigest()}


def recover_workbench(config):
    """SQLite rolls back an interrupted Workbench transaction as a single unit."""
    path = checked_path(config.state_db)
    journal = checked_path(Path(str(path) + '-journal'), missing=True)
    if journal.exists():
        config.validate()
        # A read-write WORKBENCH handle is necessary for SQLite hot-journal recovery.
        # No knowledge handle is opened here; isolation was validated above.
        with Store(config).connect(operator_write=True) as connection:
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise BoundaryError('RECOVERY_REQUIRED')
