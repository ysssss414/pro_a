"""Explicit Canonical B-lite migration. Importing or querying never migrates."""
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3

from .production_promotion import PromotionError, sha256_file

VERSION = '0.2.4'
FIELDS = {
    'admission_semantics': "TEXT NOT NULL DEFAULT 'LEGACY_UNKNOWN' CHECK(admission_semantics IN ('LEGACY_UNKNOWN','SOURCE_ASSERTION','FACTUAL_KNOWLEDGE'))",
    'reality_support': "TEXT NOT NULL DEFAULT 'LEGACY_UNKNOWN' CHECK(reality_support IN ('LEGACY_UNKNOWN','UNVERIFIED','OFFICIAL_SUPPORTED','INDEPENDENTLY_SUPPORTED','DISPUTED'))",
    'current_view_use': "TEXT NOT NULL DEFAULT 'LEGACY_UNKNOWN' CHECK(current_view_use IN ('LEGACY_UNKNOWN','CLUE_ONLY','BASIS_ELIGIBLE'))",
    'admission_basis_sha256': "TEXT NOT NULL DEFAULT '' CHECK(length(admission_basis_sha256) IN (0,64))",
}


def view_guard(action):
    return f"""CREATE TRIGGER admission_view_{action.lower()} BEFORE {action} ON current_views
WHEN NEW.status='official'
BEGIN
 SELECT CASE WHEN json_valid(NEW.content_json)=0
 OR coalesce(json_type(NEW.content_json,'$.evidence_claim_ids'),'')<>'array'
 OR json_array_length(NEW.content_json,'$.evidence_claim_ids')=0
 OR EXISTS(SELECT 1 FROM json_each(NEW.content_json,'$.evidence_claim_ids') e
 LEFT JOIN claims c ON c.claim_id=e.value
 WHERE c.claim_id IS NULL OR c.current_view_use<>'BASIS_ELIGIBLE'
 OR c.reality_support NOT IN ('OFFICIAL_SUPPORTED','INDEPENDENTLY_SUPPORTED')
 OR length(c.admission_basis_sha256)<>64)
 THEN RAISE(ABORT,'CURRENT_VIEW_REVIEWED_BASIS_REQUIRED') END;
END"""


def guards():
    return {f'admission_view_{action.lower()}': view_guard(action) for action in ('INSERT', 'UPDATE')}


def require_schema(connection):
    version = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    columns = {r[1] for r in connection.execute('PRAGMA table_info(claims)')}
    if not version or version[0] != VERSION or not set(FIELDS) <= columns:
        raise PromotionError('B_LITE_SCHEMA_REQUIRED')
    table = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='claims'").fetchone()[0]
    if any(name + ' ' + definition not in table for name, definition in FIELDS.items()):
        raise PromotionError('B_LITE_COLUMN_CONTRACT_DRIFT')
    for name, expected in guards().items():
        row = connection.execute("SELECT sql FROM sqlite_master WHERE name=? AND type='trigger'", (name,)).fetchone()
        if row is None or row[0] != expected:
            raise PromotionError('B_LITE_GUARD_DRIFT')


def _publish_backup(pending, backup):
    """Publish verified bytes without replacing any existing recovery artifact."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        move = kernel.MoveFileExW
        move.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
        move.restype = wintypes.BOOL
        if not move(str(pending), str(backup), 8):  # MOVEFILE_WRITE_THROUGH, no replace
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        os.link(pending, backup)  # Exclusive destination creation on the same filesystem.
        pending.unlink()
        descriptor = os.open(backup.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def migrate(path, *, expected_sha256, backup_path, configured_production_path):
    """Offline, exact-baseline schema action; callers authorize this separately."""
    from .foundation_schema_preparation import require_execution_schema
    from .workbench.config import checked_path
    path = checked_path(Path(path))
    if path != checked_path(Path(configured_production_path)):
        raise PromotionError('CONFIGURED_PRODUCTION_PATH_MISMATCH')
    backup = checked_path(Path(backup_path), missing=True)
    pending = checked_path(backup.with_name(backup.name + '.pending'), missing=True)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise PromotionError('B_LITE_MIGRATION_BASELINE_MISMATCH')
    reserved = {Path(str(path) + s) for s in ('', '-wal', '-shm', '-journal')}
    if backup.exists() or pending.exists() or backup in reserved or pending in reserved:
        raise PromotionError('B_LITE_MIGRATION_PATH_INVALID')
    if any(Path(str(path) + s).exists() for s in ('-wal', '-shm', '-journal')):
        raise PromotionError('B_LITE_MIGRATION_REQUIRES_OFFLINE')
    # Reject WAL-format databases before SQLite can create a shared-memory sidecar.
    with path.open('rb') as stream:
        header = stream.read(20)
    if header[:16] != b'SQLite format 3\0' or header[18:20] != b'\1\1':
        raise PromotionError('B_LITE_MIGRATION_REQUIRES_DELETE_JOURNAL')
    with closing(sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=0,
                                 isolation_level=None)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=EXTRA')
        if connection.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise PromotionError('B_LITE_MIGRATION_REQUIRES_DELETE_JOURNAL')
        connection.execute('BEGIN EXCLUSIVE')
        try:
            if any(Path(str(path) + s).exists() for s in ('-wal', '-shm', '-journal')):
                raise PromotionError('B_LITE_MIGRATION_REQUIRES_OFFLINE')
            require_execution_schema(connection)
            if sha256_file(path) != expected_sha256:
                raise PromotionError('B_LITE_MIGRATION_BASELINE_MISMATCH')
            if connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] != '0.2.3':
                raise PromotionError('B_LITE_MIGRATION_SOURCE_VERSION')
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchall():
                raise PromotionError('B_LITE_MIGRATION_SOURCE_INTEGRITY')
            # Reuse the foundation migration's byte-copy/flush/fsync pattern, but
            # publish only after complete-byte verification. A crash leaves .pending.
            pending_created = False
            try:
                with path.open('rb') as source, pending.open('xb') as stream:
                    pending_created = True
                    shutil.copyfileobj(source, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                if sha256_file(pending) != expected_sha256:
                    raise PromotionError('B_LITE_BACKUP_SHA_MISMATCH')
                _publish_backup(pending, backup)
                if sha256_file(backup) != expected_sha256:
                    raise PromotionError('B_LITE_BACKUP_SHA_MISMATCH')
            finally:
                if pending_created and pending.exists():
                    pending.unlink()
            for field, definition in FIELDS.items():
                connection.execute(f'ALTER TABLE claims ADD COLUMN {field} {definition}')
            for sql in guards().values():
                connection.execute(sql)
            connection.execute("UPDATE meta SET value=? WHERE key='schema_version'", (VERSION,))
            require_schema(connection)
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchall():
                raise PromotionError('B_LITE_MIGRATION_INTEGRITY')
            connection.commit()
        except BaseException:
            connection.rollback()
            if sha256_file(path) != expected_sha256:
                raise PromotionError('B_LITE_MIGRATION_RECOVERY_REQUIRED') from None
            raise
    return {'schema_before': '0.2.3', 'schema_version': VERSION, 'backup_sha256': sha256_file(backup),
            'sha256': sha256_file(path), 'historical_semantics': 'LEGACY_UNKNOWN'}


def projection(row):
    values = dict(row)
    return {key: values.get(key, '' if key == 'admission_basis_sha256' else 'LEGACY_UNKNOWN') for key in FIELDS}


def select_fields(connection):
    columns = {r[1] for r in connection.execute('PRAGMA table_info(claims)')}
    return ','.join('c.' + key if key in columns else
        ("''" if key == 'admission_basis_sha256' else "'LEGACY_UNKNOWN'") + ' AS ' + key for key in FIELDS)


def date_basis(row):
    return ('FACT_TIME' if row['fact_time'] else 'PUBLICATION_TIME' if row['publication_time']
            else 'INGESTION_TIME' if row['ingestion_time'] else 'UNKNOWN')


def basis_eligible(row):
    value = projection(row)
    return (value['current_view_use'] == 'BASIS_ELIGIBLE'
            and value['reality_support'] in ('OFFICIAL_SUPPORTED', 'INDEPENDENTLY_SUPPORTED')
            and len(value['admission_basis_sha256']) == 64)


def main():
    import argparse
    import json
    import tomllib
    parser = argparse.ArgumentParser(description='Explicit offline Canonical B-lite schema preparation')
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--workbench-config', type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.workbench_config.read_text(encoding='utf-8'))['workbench']
    configured = args.workbench_config.absolute().parent / config['knowledge_db']
    print(json.dumps(migrate(args.database, expected_sha256=args.expected_sha256,
                             backup_path=args.backup, configured_production_path=configured), sort_keys=True))


if __name__ == '__main__':
    main()
