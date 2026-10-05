"""Exact business-DB copy; durable metadata and every historical row stay intact."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--package-path', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--workbench-config', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.package_path.resolve()))
from pro_a.mcp.server import load_config
from pro_a.workbench.bounded_extraction_persistence import TABLES, migration_drain_report, prepare_bounded_extraction_persistence
from pro_a.workbench.lifecycle_closure import _require_drain
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.source_operations import SourceOperations, SourceProfile
from pro_a.workbench.store import Store


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}


def snapshot(path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as c:
        c.execute('PRAGMA query_only=ON')
        names = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {n: c.execute('SELECT * FROM "' + n + '" ORDER BY rowid').fetchall() for n in names}
        schema = {r[0]: r[1] for r in c.execute('SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL')}
        return rows, schema


def forbidden(*args, **kwargs):
    raise AssertionError('NETWORK_OR_PROVIDER_FORBIDDEN')


original = load_config(args.workbench_config)
assert original.mode == 'PRIVATE'
before = {'workbench': sha(original.state_db), 'production': sha(original.knowledge_db),
          'artifacts': inventory(original.artifact_root)}
assert not any(original.state_db.with_name(original.state_db.name + s).exists() for s in ('-wal', '-shm', '-journal'))
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
copy = output / 'workbench.sqlite3'
shutil.copyfile(original.state_db, copy)
assert sha(copy) == before['workbench']
config = replace(original, state_db=copy)
old, old_schema = snapshot(copy)
assert dict(old['workbench_meta'])['schema_version'] == '11'
socket.socket.connect = forbidden
import requests
requests.sessions.Session.request = forbidden
# Keep exact metadata bindings: production/artifacts are referenced read-only by
# existing validation. SQLite write connections are allowed only to the copy.
connect = sqlite3.connect
def guarded_connect(database, *positional, **kwargs):
    raw = str(database)
    if 'mode=ro' not in raw:
        assert copy.as_uri() in raw, 'NON_COPY_SQLITE_WRITE_FORBIDDEN'
    return connect(database, *positional, **kwargs)
sqlite3.connect = guarded_connect
with Store(config).connect() as c:
    report = migration_drain_report(c)
    assert report['active_run_count'] == report['active_job_count'] == 0, report
    assert not report['broken_foreign_keys']
    assert report['terminal_unreachable_queued_count'] == 14, report
    queued_ids = tuple(r[0] for r in c.execute("SELECT job_id FROM cloud_jobs WHERE state='QUEUED' ORDER BY job_id"))
    assert queued_ids == report['terminal_unreachable_queued_job_ids']
    try:
        _require_drain(c)
    except BoundaryError as error:
        assert str(error) == 'STAGE6_LIFECYCLE_REQUIRES_DRAIN'
    else:
        raise AssertionError('STRICT_OPERATIONAL_GUARD_WEAKENED')
    runs = [r[0] for r in c.execute('SELECT processing_run_id FROM source_processing_runs')]
profile_path = output / 'unused-source-profile.toml'
profile_path.write_text('# No work is eligible; configuration must never be loaded.\n')
service = SourceOperations(config, SourceProfile(profile_path))
service.jobs.run_once = forbidden
assert service.advance_once(worker_id='copy-migration-audit', provider=object()) is None
for run in runs:
    assert service.advance_once(worker_id='copy-migration-audit', processing_run_id=run, provider=object()) is None
assert snapshot(copy) == (old, old_schema)
assert sha(copy) == before['workbench']
receipt = prepare_bounded_extraction_persistence(config)
assert receipt['schema_version'] == '12'
backup = copy.with_name(copy.name + '.stage-bounded-extraction-v12-backup')
assert sha(backup) == before['workbench']
new, new_schema = snapshot(copy)
old['workbench_meta'] = [(k, '12' if k == 'schema_version' else v) for k, v in old['workbench_meta']]
assert all(new[n] == rows for n, rows in old.items())
assert all(new_schema[n] == sql for n, sql in old_schema.items())
assert set(new) - set(old) == set(TABLES)
assert all(not new[n] for n in TABLES)
prepared_sha = sha(copy)
assert prepare_bounded_extraction_persistence(config)['status'] == 'ALREADY_PREPARED'
assert sha(copy) == prepared_sha
assert sha(original.state_db) == before['workbench']
assert sha(original.knowledge_db) == before['production']
assert inventory(original.artifact_root) == before['artifacts']
record = {'status': 'PASS', 'classification': report, 'copy_schema_before': 11, 'copy_schema_after': 12,
          'original_workbench_sha256': before['workbench'], 'exact_backup_sha256': sha(backup),
          'copy_after_sha256': prepared_sha, 'old_table_count': len(old), 'added_empty_tables': list(TABLES),
          'all_old_rows_preserved_except_schema_version': True, 'all_old_schema_objects_preserved': True,
          'normal_scheduler_global_and_all_terminal_run_probes': len(runs) + 1,
          'strict_operational_guard': 'STILL_BLOCKS', 'idempotence': 'PASS',
          'historical_job_rows_mutated': 0, 'historical_runs_mutated': 0,
          'real_workbench_unchanged': True, 'production_unchanged': True, 'artifact_corpus_unchanged': True,
          'provider_calls': 0, 'provider_liability_created': 0,
          'sqlite_noncopy_write_connections': 0,
          'binding_note': 'Exact copy retains original metadata; existing production/artifact validation is read-only.'}
(output / 'qualification.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
