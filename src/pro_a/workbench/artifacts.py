from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import uuid

from pro_a.phase3f_review_completion import read_review_packet, validate_blank_review_packet
from .config import BoundaryError, WorkbenchConfig, checked_path
from .review import project
from .store import Store


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Artifacts:
    def __init__(self, config: WorkbenchConfig):
        self.config = config
        self.store = Store(config)

    def resolve(self, relative: str) -> Path:
        if not relative or relative.startswith('/') or '\\' in relative or ':' in relative or Path(relative).is_absolute() or PureWindowsPath(relative).is_absolute() or '..' in Path(relative).parts:
            raise BoundaryError('UNSAFE_PATH')
        root = checked_path(self.config.artifact_root)
        path = checked_path(root / relative)
        if not path.is_relative_to(root) or path == root:
            raise BoundaryError('UNSAFE_PATH')
        return path

    def inventory(self, packet_relative: str, run_relative: str) -> dict:
        packet = self.resolve(packet_relative)
        run = self.resolve(run_relative)
        if not packet.is_file() or not run.is_dir():
            raise BoundaryError('ARTIFACT_TYPE_INVALID')
        files = {packet_relative: digest(packet)}
        # Inspect every directory before walking into it; os.walk never follows links.
        for directory, dirs, names in os.walk(run, followlinks=False):
            for name in [*dirs, *names]:
                path = checked_path(Path(directory) / name)
                if path.is_file():
                    files[path.relative_to(self.config.artifact_root.resolve()).as_posix()] = digest(path)
        # Check paths the native validator is about to resolve BEFORE invoking it.
        manifest = read_review_packet(run / 'run_manifest.json')
        referenced = [manifest['source']['frozen_relative_path']]
        referenced += [item['path'] for item in manifest['artifact_inventory']]
        for relative in referenced:
            if not isinstance(relative, str) or relative.startswith('/') or '..' in Path(relative).parts or '\\' in relative or ':' in relative or Path(relative).is_absolute():
                raise BoundaryError('UNSAFE_PATH')
            path = checked_path(run / relative)
            if not path.is_relative_to(run):
                raise BoundaryError('UNSAFE_PATH')
        return files

    def validate(self, packet_relative: str, run_relative: str, artifact_id: str, expected: dict | None = None) -> tuple[dict, dict, dict]:
        try:
            inventory = self.inventory(packet_relative, run_relative)
            if expected is not None and inventory != expected:
                raise BoundaryError('ARTIFACT_HASH_MISMATCH')
            packet = read_review_packet(self.resolve(packet_relative))
            validation = validate_blank_review_packet(packet, run_root=self.resolve(run_relative))
            if self.config.mode == 'DEMO' and packet['source']['source_type'] != 'SYNTHETIC_TEXT':
                raise BoundaryError('ARTIFACT_MODE_MISMATCH')
            dto = project(packet, validation, artifact_id, inventory[packet_relative], self.config.mode)
            if self.inventory(packet_relative, run_relative) != inventory:
                raise BoundaryError('ARTIFACT_CHANGED_DURING_READ')
            return dto, inventory, packet
        except BoundaryError:
            raise
        except Exception:
            raise BoundaryError('NATIVE_PACKET_UNAVAILABLE') from None

    def register(self, packet_relative: str, run_relative: str) -> dict:
        """Operator-only registration references frozen bytes; no packet/execution writes."""
        self.config.validate()
        artifact_id = 'ART_' + uuid.uuid4().hex
        dto, inventory, _ = self.validate(packet_relative, run_relative, artifact_id)
        with self.store.connect(operator_write=True) as connection:
            existing = connection.execute(
                "SELECT * FROM registered_packets WHERE packet_id=? AND "
                "(artifact_kind='REVIEW_PACKET' OR artifact_kind IS NULL)"
                if 'artifact_kind' in {row[1] for row in connection.execute('PRAGMA table_info(registered_packets)')}
                else 'SELECT * FROM registered_packets WHERE packet_id=?',
                (dto['packet_id'],),
            ).fetchone()
            if existing:
                if existing['file_inventory'] != json.dumps(inventory, sort_keys=True) or existing['packet_relative'] != packet_relative or existing['run_relative'] != run_relative:
                    raise BoundaryError('PACKET_ALREADY_REGISTERED_DIFFERENTLY')
                return {'artifact_id': existing['artifact_id'], 'packet_id': dto['packet_id']}
            connection.execute('INSERT INTO registered_packets(artifact_id,packet_id,packet_relative,run_relative,packet_sha256,file_inventory) VALUES(?,?,?,?,?,?)',
                               (artifact_id, dto['packet_id'], packet_relative, run_relative, dto['packet_file_sha256'], json.dumps(inventory, sort_keys=True)))
        return {'artifact_id': artifact_id, 'packet_id': dto['packet_id']}

    def native(self, artifact_id: str) -> tuple[dict, Path, dict]:
        """Validated native bytes/context for the internal completion service only."""
        if not re.fullmatch(r'ART_[0-9a-f]{32}', artifact_id):
            raise BoundaryError('ARTIFACT_NOT_REGISTERED')
        with self.store.connect() as connection:
            row = connection.execute('SELECT * FROM registered_packets WHERE artifact_id=?', (artifact_id,)).fetchone()
        if row is None:
            raise BoundaryError('ARTIFACT_NOT_REGISTERED')
        if 'artifact_kind' in row.keys() and row['artifact_kind'] != 'REVIEW_PACKET':
            raise BoundaryError('ARTIFACT_NOT_REGISTERED')
        from .domains import Domains
        Domains(self.config).validate_packet(artifact_id)
        dto, _, packet = self.validate(row['packet_relative'], row['run_relative'], artifact_id, json.loads(row['file_inventory']))
        if dto['packet_id'] != row['packet_id'] or dto['packet_file_sha256'] != row['packet_sha256']:
            raise BoundaryError('REGISTRY_IDENTITY_MISMATCH')
        return packet, self.resolve(row['run_relative']), dto

    def read(self, artifact_id: str) -> dict:
        return self.native(artifact_id)[2]

    def listing(self) -> list[dict]:
        with self.store.connect() as connection:
            columns = {row[1] for row in connection.execute('PRAGMA table_info(registered_packets)')}
            where = " WHERE artifact_kind='REVIEW_PACKET'" if 'artifact_kind' in columns else ''
            handles = [row[0] for row in connection.execute(
                'SELECT artifact_id FROM registered_packets' + where + ' ORDER BY registered_at,artifact_id')]
        return [{key: dto[key] for key in ('artifact_id', 'packet_id', 'run_id', 'source', 'summary', 'validation_state', 'mode')}
                for dto in (self.read(handle) for handle in handles)]
