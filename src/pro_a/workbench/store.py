from __future__ import annotations

from contextlib import closing, contextmanager
import json
import sqlite3

from .config import BoundaryError, WorkbenchConfig, checked_path


class Store:
    def __init__(self, config: WorkbenchConfig):
        self.config = config

    def initialize(self) -> None:
        """Operator only. Never create/migrate the knowledge database."""
        self.config.validate()
        path = checked_path(self.config.state_db, missing=True)
        if path.exists():
            with self.connect():
                return
        root = checked_path(self.config.artifact_root, missing=True)
        root.mkdir(parents=True, exist_ok=True)
        marker = root / '.workbench-mode.json'
        expected = {'mode': self.config.mode}
        if marker.exists():
            if json.loads(checked_path(marker).read_text()) != expected:
                raise BoundaryError('ARTIFACT_MODE_MISMATCH')
        else:
            marker.write_text(json.dumps(expected), encoding='utf-8')
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive file creation avoids accidentally bootstrapping an existing DB.
        with path.open('xb'):
            pass
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.executescript('''
                CREATE TABLE workbench_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE registered_packets(
                    artifact_id TEXT PRIMARY KEY, packet_id TEXT UNIQUE NOT NULL,
                    packet_relative TEXT NOT NULL, run_relative TEXT NOT NULL,
                    packet_sha256 TEXT NOT NULL, file_inventory TEXT NOT NULL,
                    registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            connection.executemany('INSERT INTO workbench_meta VALUES(?,?)', self.config.bindings().items())

    @contextmanager
    def connect(self, *, operator_write: bool = False):
        path = checked_path(self.config.state_db)
        for suffix in ('-journal', '-wal', '-shm'):
            checked_path(path.with_name(path.name + suffix), missing=True)
        marker = checked_path(self.config.artifact_root / '.workbench-mode.json')
        if json.loads(marker.read_text()) != {'mode': self.config.mode}:
            raise BoundaryError('ARTIFACT_MODE_MISMATCH')
        connection = sqlite3.connect(f'{path.as_uri()}?mode={"rw" if operator_write else "ro"}', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            if not operator_write:
                connection.execute('PRAGMA query_only=ON')
            metadata = dict(connection.execute('SELECT key,value FROM workbench_meta'))
            if metadata.get('schema_version') not in ('1', '2', '3', '4', '5', '6', '7'):
                raise BoundaryError('WORKBENCH_SCHEMA_UNSUPPORTED')
            if metadata != {**self.config.bindings(), 'schema_version': metadata['schema_version']}:
                raise BoundaryError('WORKBENCH_BINDING_MISMATCH')
            yield connection
            if operator_write:
                connection.commit()
        finally:
            connection.close()
