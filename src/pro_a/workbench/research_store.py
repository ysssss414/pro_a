"""Workbench-only Stage 5 schema and noncanonical follow-up notes."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store

OBJECT_TYPES = ('NODE', 'CLAIM', 'SOURCE', 'RELATION', 'GAP', 'RESEARCH_QUESTION')
NOTE_STATUSES = ('OPEN', 'DONE', 'DEFERRED')


class NoteError(RuntimeError):
    def __init__(self, code: str, status: int, current_revision: int | None = None):
        super().__init__(code)
        self.status = status
        self.current_revision = current_revision


def _sha(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def prepare_research(config):
    """Operator-only v5 -> v6 migration. The canonical knowledge DB is never opened for write."""
    config.validate()
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version in ('6', '7', '8', '9', '10'):
            return {'status': 'ALREADY_PREPARED', 'schema_version': version}
        if version != '5':
            raise BoundaryError('IMPACT_SCHEMA_REQUIRED')
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + '.stage4-backup'), missing=True)
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
        if schema_version(connection) != '5':
            raise BoundaryError('WORKBENCH_SCHEMA_CHANGED')
        connection.execute('''CREATE TABLE followup_notes(
            note_id TEXT PRIMARY KEY,
            object_type TEXT NOT NULL CHECK(object_type IN ('NODE','CLAIM','SOURCE','RELATION','GAP','RESEARCH_QUESTION')),
            object_id TEXT NOT NULL,text TEXT NOT NULL CHECK(length(trim(text))>0),
            status TEXT NOT NULL CHECK(status IN ('OPEN','DONE','DEFERRED')),
            revision INTEGER NOT NULL CHECK(revision>0),operator TEXT NOT NULL,
            created_at TEXT NOT NULL,updated_at TEXT NOT NULL)''')
        connection.execute('''CREATE INDEX followup_notes_object
            ON followup_notes(object_type,object_id,status,updated_at DESC,note_id)''')
        connection.execute('''CREATE TABLE followup_note_events(
            note_id TEXT NOT NULL,revision INTEGER NOT NULL,operation_id TEXT NOT NULL UNIQUE,
            request_sha256 TEXT NOT NULL,event_json TEXT NOT NULL,response_json TEXT NOT NULL,
            PRIMARY KEY(note_id,revision))''')
        for action in ('UPDATE', 'DELETE'):
            connection.execute(f"CREATE TRIGGER followup_note_events_{action.lower()}_forbidden BEFORE {action} ON followup_note_events BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute("CREATE TRIGGER followup_notes_delete_forbidden BEFORE DELETE ON followup_notes BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
        connection.execute("UPDATE workbench_meta SET value='6' WHERE key='schema_version'")
    return {'status': 'RESEARCH_SCHEMA_PREPARED', 'schema_version': '6',
            'backup_sha256': hashlib.sha256(content).hexdigest()}


class FollowupNotes:
    def __init__(self, config):
        self.config = config
        self.store = Store(config)

    def list(self, *, object_type: str = '', object_id: str = '', status: str = '', limit: int = 50):
        if object_type and object_type not in OBJECT_TYPES:
            raise NoteError('UNSUPPORTED_RESEARCH_OBJECT', 422)
        if status and status not in NOTE_STATUSES:
            raise NoteError('INVALID_FILTER', 422)
        if not 1 <= limit <= 100:
            raise NoteError('INVALID_CURSOR', 422)
        clauses, args = [], []
        if object_type:
            clauses.append('object_type=?'); args.append(object_type)
        if object_id:
            clauses.append('object_id=?'); args.append(object_id)
        if status:
            clauses.append('status=?'); args.append(status)
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        with self.store.connect() as connection:
            if schema_version(connection) not in ('6', '7', '8', '9', '10'):
                raise BoundaryError('RESEARCH_SCHEMA_REQUIRED')
            rows = [dict(row) for row in connection.execute(
                f'''SELECT note_id,object_type,object_id,text,status,revision,operator,created_at,updated_at
                    FROM followup_notes{where}
                    ORDER BY CASE status WHEN 'OPEN' THEN 0 WHEN 'DEFERRED' THEN 1 ELSE 2 END,
                             updated_at DESC,note_id LIMIT ?''', (*args, limit))]
        return {'notes': rows, 'canonical_write': False, 'private_operator_state': True}

    def create(self, body: dict, identity: dict[str, str]):
        request = {key: body[key] for key in ('operation_id', 'object_type', 'object_id', 'text', 'status')}
        digest = _sha(request)
        now = _now()
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            if schema_version(connection) not in ('6', '7', '8', '9', '10'):
                raise BoundaryError('RESEARCH_SCHEMA_REQUIRED')
            prior = connection.execute(
                'SELECT request_sha256,response_json FROM followup_note_events WHERE operation_id=?',
                (body['operation_id'],)).fetchone()
            if prior:
                if prior['request_sha256'] != digest:
                    raise NoteError('IDEMPOTENCY_CONFLICT', 409)
                return json.loads(prior['response_json'])
            note_id = 'NOTE_' + uuid4().hex.upper()
            row = {'note_id': note_id, 'object_type': body['object_type'],
                   'object_id': body['object_id'], 'text': body['text'].strip(),
                   'status': body['status'], 'revision': 1,
                   'operator': identity['actor'], 'created_at': now, 'updated_at': now}
            connection.execute('''INSERT INTO followup_notes
                (note_id,object_type,object_id,text,status,revision,operator,created_at,updated_at)
                VALUES(:note_id,:object_type,:object_id,:text,:status,:revision,:operator,:created_at,:updated_at)''', row)
            response = {'note': row, 'canonical_write': False, 'production_authorized': False}
            event = {'event_type': 'CREATE', **row}
            connection.execute('INSERT INTO followup_note_events VALUES(?,?,?,?,?,?)',
                (note_id, 1, body['operation_id'], digest,
                 json.dumps(event, sort_keys=True), json.dumps(response, sort_keys=True)))
            return response

    def update(self, note_id: str, body: dict, identity: dict[str, str]):
        request = {key: body[key] for key in ('operation_id', 'expected_revision', 'text', 'status')}
        request['note_id'] = note_id
        digest = _sha(request)
        now = _now()
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            if schema_version(connection) not in ('6', '7', '8', '9', '10'):
                raise BoundaryError('RESEARCH_SCHEMA_REQUIRED')
            prior = connection.execute(
                'SELECT request_sha256,response_json FROM followup_note_events WHERE operation_id=?',
                (body['operation_id'],)).fetchone()
            if prior:
                if prior['request_sha256'] != digest:
                    raise NoteError('IDEMPOTENCY_CONFLICT', 409)
                return json.loads(prior['response_json'])
            current = connection.execute('SELECT * FROM followup_notes WHERE note_id=?', (note_id,)).fetchone()
            if current is None:
                raise NoteError('NOTE_NOT_FOUND', 404)
            if current['revision'] != body['expected_revision']:
                raise NoteError('NOTE_REVISION_CONFLICT', 409, current['revision'])
            revision = current['revision'] + 1
            connection.execute('''UPDATE followup_notes SET text=?,status=?,revision=?,operator=?,updated_at=?
                                  WHERE note_id=? AND revision=?''',
                (body['text'].strip(), body['status'], revision, identity['actor'], now,
                 note_id, current['revision']))
            row = dict(connection.execute('SELECT * FROM followup_notes WHERE note_id=?', (note_id,)).fetchone())
            response = {'note': row, 'canonical_write': False, 'production_authorized': False}
            event = {'event_type': 'UPDATE', **row}
            connection.execute('INSERT INTO followup_note_events VALUES(?,?,?,?,?,?)',
                (note_id, revision, body['operation_id'], digest,
                 json.dumps(event, sort_keys=True), json.dumps(response, sort_keys=True)))
            return response

    def write_count(self) -> int:
        with self.store.connect() as connection:
            return int(connection.execute('SELECT COUNT(*) FROM followup_note_events').fetchone()[0])
