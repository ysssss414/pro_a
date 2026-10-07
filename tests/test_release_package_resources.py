"""Run from copied tests in a fresh installed environment, not the checkout."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
import pro_a
from pro_a.db import Database
from pro_a import foundation_schema_migration as migration
from pro_a.repository_identity import repository_commit
from installed_wheel_smoke import RESOURCES, verify_origins


@pytest.fixture
def package():
    root = Path(pro_a.__file__).resolve().parent
    assert root.is_relative_to(Path(sys.prefix).resolve()), 'INSTALLED_ONLY_TEST'
    return root


@pytest.mark.parametrize('name', list(RESOURCES))
def test_runtime_resource_exists(package, name):
    assert (package / name).is_file()


@pytest.mark.parametrize('name,expected', list(RESOURCES.items()))
def test_resource_bytes_match_frozen_git_authority(package, name, expected):
    assert hashlib.sha256((package / name).read_bytes()).hexdigest() == expected


def test_runtime_resource_inventory_closed(package):
    resources = {p.relative_to(package).as_posix() for p in package.rglob('*')
                 if p.is_file() and p.suffix not in ('.py', '.pyc') and p.name != '_build_identity.json'}
    assert resources == set(RESOURCES)


def test_fresh_native_database_bootstrap(tmp_path, package):
    db = Database(tmp_path / 'fresh-native.db')
    db.init_schema()
    with db.connect() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'meta', 'nodes', 'claims', 'sources', 'node_relations', 'current_views', 'relation_evidence_links'} <= tables
        assert connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '0.2.2'
        assert connection.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
        assert connection.execute('SELECT count(*) FROM claims').fetchone()[0] == 0
    db.init_schema()


def test_foundation_authorized_resource_preflight(package):
    assert migration.SQL_PATH == package / 'migrations/foundation_0_2_3_relation_native.sql'
    data = migration.SQL_PATH.read_bytes()
    assert hashlib.sha256(data).hexdigest() == migration.AUTHORIZED_SQL_SHA256
    statements = migration.frozen_statements(data)
    assert statements[1].strip() == 'BEGIN IMMEDIATE;' and statements[-1].strip() == 'COMMIT;'


def test_source_and_metadata_contamination_tripwire(package):
    root = Path(os.environ['PRO_A_SMOKE_SOURCE_ROOT'])
    result = verify_origins(root)
    assert not result['source_tree_on_sys_path'] and not result['source_egg_info_shadowing']
    assert Path(result['metadata_origin']).name.endswith('.dist-info')
    with pytest.raises(PermissionError, match='SOURCE_CHECKOUT_ACCESS_FORBIDDEN'):
        (root / 'pyproject.toml').read_bytes()


def test_installed_identity_with_git_unavailable(package):
    expected = os.environ['PRO_A_SMOKE_EXPECTED_COMMIT']
    env = {**os.environ, 'PATH': '', 'PYTHONPATH': ''}
    value = subprocess.check_output([sys.executable, '-I', '-c',
                                    'from pro_a.repository_identity import repository_commit; print(repository_commit())'],
                                   cwd=Path.cwd(), env=env, text=True).strip()
    assert value == repository_commit() == expected


def test_source_operations_bounded_construction(tmp_path, package):
    from test_phase43_stage71_shared_core_pending import case
    from pro_a.workbench.source_operations import SourceOperations
    from pro_a.workbench.store import Store
    value = case(tmp_path)
    assert isinstance(value['service'], SourceOperations)
    with Store(value['config']).connect() as connection:
        assert connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == '12'
        assert connection.execute('SELECT count(*) FROM source_processing_runs').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM bounded_extraction_attempts').fetchone()[0] == 0
