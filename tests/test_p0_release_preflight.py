"""Focused offline release checks; all fixtures and identities are synthetic."""
from contextlib import closing
import json
import os
import shutil
import sqlite3

import pytest

from pro_a import admission_schema as admission
from pro_a.db import Database
from pro_a.foundation_schema_preparation import apply_synthetic_migration
from pro_a.production_promotion import PromotionError, sha256_file


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'synthetic.db'
    Database(path).init_schema()
    apply_synthetic_migration(path, configured_production_path=tmp_path / 'unused',
                              expected_sha256=sha256_file(path))
    return path


def migrate(path, backup):
    return admission.migrate(path, expected_sha256=sha256_file(path), backup_path=backup,
                             configured_production_path=path)


@pytest.mark.parametrize('fault', ['short_copy', 'space', 'fsync', 'publish', 'ddl'])
def test_backup_failures_precede_mutation_and_ddl_failure_restores_bytes(database, tmp_path, monkeypatch, fault):
    before = database.read_bytes()
    backup = tmp_path / 'backup.db'
    def fail(*args, **kwargs):
        raise OSError('synthetic interrupted operation')
    if fault == 'short_copy':
        monkeypatch.setattr(admission.shutil, 'copyfileobj', lambda source, dest: dest.write(source.read(64)))
    elif fault == 'space':
        def partial(source, dest):
            dest.write(source.read(64))
            raise OSError(28, 'synthetic disk full')
        monkeypatch.setattr(admission.shutil, 'copyfileobj', partial)
    elif fault == 'fsync':
        monkeypatch.setattr(admission.os, 'fsync', fail)
    elif fault == 'publish':
        monkeypatch.setattr(admission, '_publish_backup', fail)
    else:
        monkeypatch.setattr(admission, 'require_schema', fail)
    with pytest.raises((OSError, PromotionError)):
        migrate(database, backup)
    assert database.read_bytes() == before
    assert not backup.with_name(backup.name + '.pending').exists()
    if fault == 'ddl':
        assert backup.read_bytes() == before
    else:
        assert not backup.exists()
    assert not any(database.with_name(database.name + suffix).exists() for suffix in ('-wal', '-shm', '-journal'))


def test_backup_is_durable_verified_and_exclusive_before_ddl(database, tmp_path, monkeypatch):
    before = database.read_bytes()
    backup = tmp_path / 'backup.db'
    real_sync, real_publish, real_require = admission.os.fsync, admission._publish_backup, admission.require_schema
    events = []
    def sync(fd):
        events.append('fsync')
        return real_sync(fd)
    def publish(pending, target):
        assert events and pending.read_bytes() == before and database.read_bytes() == before
        # A competing SQLite writer cannot acquire a reservation during backup.
        with closing(sqlite3.connect(database, timeout=0, isolation_level=None)) as other:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                other.execute('BEGIN IMMEDIATE')
        real_publish(pending, target)
        events.append('published')
    def require(connection):
        assert events[-1] == 'published' and backup.read_bytes() == before
        return real_require(connection)
    monkeypatch.setattr(admission.os, 'fsync', sync)
    monkeypatch.setattr(admission, '_publish_backup', publish)
    monkeypatch.setattr(admission, 'require_schema', require)
    migrate(database, backup)
    frozen = database.read_bytes()
    with pytest.raises(PromotionError, match='SOURCE_VERSION'):
        migrate(database, tmp_path / 'repeat.db')
    assert database.read_bytes() == frozen and not (tmp_path / 'repeat.db').exists()
    restored = tmp_path / 'restored.db'
    shutil.copyfile(backup, restored)
    assert restored.read_bytes() == before
    with closing(sqlite3.connect(restored)) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '0.2.3'


@pytest.mark.parametrize('obstacle', ['backup', 'pending', '-wal', '-shm', '-journal', 'wrong_target', 'hardlink'])
def test_migration_refuses_unsafe_target_and_recovery_artifacts(database, tmp_path, obstacle):
    backup = tmp_path / 'backup.db'
    before = database.read_bytes()
    configured = database
    if obstacle == 'wrong_target':
        configured = tmp_path / 'another.db'
        shutil.copyfile(database, configured)  # Same bytes are not the same authorized target.
    elif obstacle == 'hardlink':
        os.link(database, tmp_path / 'alias.db')
    else:
        target = backup if obstacle == 'backup' else backup.with_name(backup.name + '.pending') if obstacle == 'pending' else database.with_name(database.name + obstacle)
        target.write_bytes(b'incomplete recovery artifact')
    with pytest.raises((ValueError, PromotionError)):
        admission.migrate(database, expected_sha256=sha256_file(database), backup_path=backup,
                          configured_production_path=configured)
    assert database.read_bytes() == before
    if obstacle not in ('wrong_target', 'hardlink'):
        assert target.read_bytes() == b'incomplete recovery artifact'


def test_active_writer_and_wal_header_refuse_without_migration(database, tmp_path):
    before = database.read_bytes()
    with closing(sqlite3.connect(database, isolation_level=None)) as writer:
        writer.execute('BEGIN IMMEDIATE')
        with pytest.raises(sqlite3.OperationalError, match='locked'):
            migrate(database, tmp_path / 'locked.db')
        writer.rollback()
        assert database.read_bytes() == before
        writer.execute('PRAGMA journal_mode=WAL')
    wal_before = database.read_bytes()
    assert not any(database.with_name(database.name + s).exists() for s in ('-wal', '-shm'))
    with pytest.raises(PromotionError, match='DELETE_JOURNAL'):
        migrate(database, tmp_path / 'wal.db')
    assert database.read_bytes() == wal_before
    assert not any(database.with_name(database.name + s).exists() for s in ('-wal', '-shm'))


def test_existing_foreign_key_damage_stops_before_backup(database, tmp_path):
    with sqlite3.connect(database) as c:
        c.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) VALUES('C','Synthetic','fact','t','MISSING','t')")
    before = database.read_bytes()
    with pytest.raises(PromotionError, match='SOURCE_INTEGRITY'):
        migrate(database, tmp_path / 'invalid.db')
    assert database.read_bytes() == before and not (tmp_path / 'invalid.db').exists()


def test_explicit_cli_binds_configured_target(database, tmp_path, monkeypatch, capsys):
    config = tmp_path / 'workbench.toml'
    config.write_text('[workbench]\nknowledge_db="synthetic.db"\n', encoding='utf-8')
    backup = tmp_path / 'cli-backup.db'
    before = sha256_file(database)
    monkeypatch.setattr('sys.argv', ['migration', '--workbench-config', str(config),
        '--database', str(database), '--expected-sha256', before, '--backup', str(backup)])
    admission.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['schema_version'] == '0.2.4' and receipt['backup_sha256'] == before


def test_schema12_history_comparison_drafts_and_all_official_update_levels(tmp_path):
    from workbench_stage3_fixture import stage3_fixture, COMPANY, PRODUCT, COMPANY_CLAIM, PRODUCT_CLAIM, company_content, product_content
    from test_workbench_stage3 import save, validate
    from pro_a.current_view_workbench import CurrentViewWorkbench, _basis
    from pro_a.current_view import create_official_view_record
    from pro_a.config import load_config
    from pro_a.workbench.config import BoundaryError
    from pro_a.workbench.impact_store import prepare_impact
    from pro_a.workbench.research_store import prepare_research
    from pro_a.workbench.cloud_jobs import prepare_cloud_jobs
    from pro_a.workbench.source_operations import prepare_source_operations
    from series_binding_helpers import prepare_bounded
    from pro_a.mcp.service import ReadService
    value = stage3_fixture(tmp_path)
    for prepare in (prepare_impact, prepare_research, prepare_cloud_jobs, prepare_source_operations):
        prepare(value['config'])
    prepare_bounded(value)
    service = CurrentViewWorkbench(value['config'])
    old = service.read(COMPANY)
    path = value['knowledge']
    migrate(path, tmp_path / 'before-b-lite.db')
    new = service.read(COMPANY)
    for key in ('official', 'history', 'previous_official', 'official_comparison', 'baseline_views'):
        assert new[key] == old[key]
    assert [{k: v for k, v in row.items() if k != 'primary_eligible'} for row in new['official_evidence']] == [
        {k: v for k, v in row.items() if k != 'primary_eligible'} for row in old['official_evidence']]
    assert new['basis_sha256'] == _basis(new['node'], new['official'], new['available_evidence'], '0.2.4')
    assert new['basis_sha256'] != _basis(new['node'], new['official'], new['available_evidence'], '0.2.3')
    assert not any(e['primary_eligible'] for e in new['available_evidence'])
    assert ReadService(value['config']).get_current_view(COMPANY)
    assert ReadService(value['config']).get_current_view_history(COMPANY)
    config_path = tmp_path / 'app.toml'
    config_path.write_text('[workspace]\nroot="."\n', encoding='utf-8')
    for level in ('initial', 'minor', 'material', 'thesis'):
        node, claim, content = (PRODUCT, PRODUCT_CLAIM, product_content()) if level == 'initial' else (COMPANY, COMPANY_CLAIM, company_content('Synthetic changed conclusion'))
        case = {'service': service}
        assert save(case, node, content, [claim], change_level=level)['status'] == 'DRAFT'
        with pytest.raises(BoundaryError, match='PRIMARY_EVIDENCE_INVALID'):
            validate(case, node)
        with closing(sqlite3.connect(path)) as c:
            c.row_factory = sqlite3.Row
            with pytest.raises(sqlite3.IntegrityError, match='CURRENT_VIEW_REVIEWED_BASIS_REQUIRED'):
                create_official_view_record(c, load_config(config_path), node, content, level)
    assert service.read(COMPANY)['history'] == old['history']
