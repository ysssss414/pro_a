"""Release-only installed-package checks on disposable synthetic state."""
import asyncio
import importlib
import json
import sqlite3

import pytest

from pro_a.db import Database
from pro_a.admission_schema import migrate, require_schema
from pro_a.foundation_schema_preparation import apply_synthetic_migration
from pro_a.production_promotion import sha256_file, PromotionError
from pro_a.query import ReadOnlyQuery


@pytest.mark.parametrize('name', ['pro_a.cli', 'pro_a.current_view_workbench', 'pro_a.view_operator', 'pro_a.workbench.api',
                                  'pro_a.candidate_origin', 'pro_a.workbench.candidate_inputs'])
def test_installed_entrypoint_loads(name):
    importlib.import_module(name)


def test_mcp_inventory_and_readonly_annotations(tmp_path):
    from mcp import Client
    from pro_a.mcp.server import create_server
    from pro_a.mcp.service import ReadService, TOOLS
    from pro_a.workbench.config import WorkbenchConfig
    config = WorkbenchConfig('PRIVATE', tmp_path/'absent.db', tmp_path/'state/wb.db',
                             tmp_path/'artifacts', 'http://127.0.0.1:8000')
    server = create_server(ReadService(config))
    async def inspect():
        async with Client(server) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 14 and {t.name for t in tools} == set(TOOLS)
            for tool in tools:
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
    asyncio.run(inspect())


def test_legacy_read_and_new_schema_admission(tmp_path):
    path = tmp_path/'synthetic.db'
    db = Database(path)
    db.init_schema()
    with db.connect() as c:
        c.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,created_at,updated_at) VALUES('N','Synthetic','Company','t','t')")
        c.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at) VALUES('S','Synthetic','synthetic','synthetic','abc','local','t')")
        c.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) VALUES('C','Synthetic','fact','t','S','t')")
        c.execute("INSERT INTO current_views(view_id,node_id,version,change_level,content_md,content_json,created_at) VALUES('V','N','1','initial','Historical','{}','t')")
    apply_synthetic_migration(path, configured_production_path=tmp_path/'unused-production', expected_sha256=sha256_file(path))
    before = path.read_bytes()
    query = ReadOnlyQuery(path)
    historical = query.node_current_view('N')
    assert historical and query.node_current_view_history('N')
    with db.connect() as c:
        with pytest.raises(PromotionError, match='B_LITE_SCHEMA_REQUIRED'):
            require_schema(c)
    assert path.read_bytes() == before
    receipt = migrate(path, expected_sha256=sha256_file(path), backup_path=tmp_path/'backup.db', configured_production_path=path)
    assert receipt['schema_version']=='0.2.4'
    assert query.node_current_view('N') == historical
    with db.connect() as c:
        require_schema(c)
        c.execute("UPDATE claims SET admission_semantics='SOURCE_ASSERTION', reality_support='UNVERIFIED', current_view_use='CLUE_ONLY', admission_basis_sha256=? WHERE claim_id='C'", ('a'*64,))
        with pytest.raises(sqlite3.IntegrityError, match='CURRENT_VIEW_REVIEWED_BASIS_REQUIRED'):
            c.execute("INSERT INTO current_views(view_id,node_id,version,change_level,content_md,content_json,created_at) VALUES('V2','N','2','initial','New',?,'t')",(json.dumps({'evidence_claim_ids':['C']}),))
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()


def test_operational_contract_identity():
    from pro_a.operational_contract import VERSION, CONTRACT_SHA, runtime_identity
    assert VERSION == 'phase42-operational-v2'
    assert len(CONTRACT_SHA)==64 and len(runtime_identity())==64


def test_workbench_schema12_and_run_limit(tmp_path):
    from workbench_stage7_fixture import stage7_fixture
    from pro_a.workbench.domains import prepare_domains
    from pro_a.workbench.stage1_scale import prepare_stage1_scale, Stage1Limits
    from pro_a.workbench.lifecycle_closure import prepare_stage6_lifecycle
    from pro_a.workbench.bounded_extraction_persistence import prepare_bounded_extraction_persistence
    from pro_a.workbench.store import Store
    value = stage7_fixture(tmp_path)
    config = value['config']
    prepare_domains(config)
    prepare_stage1_scale(config)
    prepare_stage6_lifecycle(config)
    prepare_bounded_extraction_persistence(config)
    with Store(config).connect() as c:
        assert c.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0]=='12'
        assert c.execute('SELECT count(*) FROM source_processing_runs').fetchone()[0]==0
    assert Stage1Limits().runs_per_24h==3
