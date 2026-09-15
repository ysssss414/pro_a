import json
import os
import sqlite3

import pytest

from pro_a.workbench.config import BoundaryError, WorkbenchConfig
from pro_a.workbench.operations import (
    _require_copy_headroom,
    create_backup,
    path_preflight,
    restore_backup,
)
from pro_a.workbench.research_store import FollowupNotes
from pro_a.workbench.store import Store
from workbench_stage5_fixture import GAP, stage5_fixture
from pro_a.workbench.cloud_jobs import prepare_cloud_jobs
from pro_a.workbench.source_operations import prepare_source_operations


def _schema8(root):
    value = stage5_fixture(root)
    prepare_cloud_jobs(value["config"])
    prepare_source_operations(value["config"])
    return value


def _rows(path):
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        return {table: [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
                for table in tables if table != "workbench_meta"}


def test_coordinated_backup_restore_rebinds_and_preserves_state(tmp_path):
    source = _schema8(tmp_path / "source")
    FollowupNotes(source["config"]).create({
        "operation_id": "stage8-backup-note", "object_type": "GAP", "object_id": GAP,
        "text": "Synthetic restore qualification note", "status": "OPEN",
    }, {"actor": "operator"})
    extra = source["config"].artifact_root / "qualification" / "sealed.json"
    extra.parent.mkdir()
    extra.write_text(json.dumps({"synthetic": True}), encoding="utf-8")
    expected_rows = _rows(source["config"].state_db)
    backup = tmp_path / "backup"
    result = create_backup(source["config"], backup)
    assert result["status"] == "BACKUP_COMPLETE"
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["configuration_contract"] == {
        "absolute_paths_stored": False, "restore_config_required": True,
        "secrets_stored": False, "session_token_stored": False,
    }
    assert str(tmp_path) not in (backup / "manifest.json").read_text(encoding="utf-8")

    target_root = tmp_path / "restored"
    target_root.mkdir()
    knowledge = target_root / "knowledge.db"
    knowledge.write_bytes(source["config"].knowledge_db.read_bytes())
    target = WorkbenchConfig(
        source["config"].mode, knowledge, target_root / "state" / "workbench.sqlite3",
        target_root / "artifacts", source["config"].origin,
    )
    restored = restore_backup(target, backup)
    assert restored == {"status": "RESTORE_COMPLETE", "backup_format": "phase42-workbench-backup-v1",
                        "workbench_schema_version": "8", "artifact_files": 2,
                        "paths_rebound": True}
    assert _rows(target.state_db) == expected_rows
    assert (target.artifact_root / "qualification" / "sealed.json").read_bytes() == extra.read_bytes()
    assert FollowupNotes(target).list(object_type="GAP", object_id=GAP)["notes"][0]["text"].startswith("Synthetic")
    with Store(target).connect() as connection:
        metadata = dict(connection.execute("SELECT key,value FROM workbench_meta"))
    assert metadata["knowledge_db"] == str(target.knowledge_db.resolve())
    assert metadata["artifact_root"] == str(target.artifact_root.resolve())


def test_backup_rejects_undrained_jobs_and_existing_destination(tmp_path):
    value = _schema8(tmp_path / "source")
    with Store(value["config"]).connect(operator_write=True) as connection:
        connection.execute("INSERT INTO cloud_jobs(job_id,input_artifact_id,input_sha256,source_id,operation_kind,"
                           "intent_sha256,runtime_json,runtime_sha256,prompt_json,prompt_sha256,configuration_json,"
                           "configuration_sha256,native_checkpoint_json,provider,requested_model,"
                           "accepted_model_aliases_json,provider_adapter_version,timeout_seconds,max_output_tokens,"
                           "max_calls,max_attempts,max_total_tokens,retry_owner,retry_policy_id,state,phase,"
                           "created_at,updated_at) VALUES('JOB_STAGE8','missing','x','source','SEMANTIC_DECOMPOSITION',"
                           "'x','{}','x','{}','x','{}','x','{}','fake','fake','[]','fake',1,1,1,1,1,'job','retry',"
                           "'QUEUED','QUEUED','now','now')")
    with pytest.raises(BoundaryError, match="WORKBENCH_DRAIN_REQUIRED"):
        create_backup(value["config"], tmp_path / "backup")


def test_path_preflight_has_deterministic_headroom_contract(tmp_path):
    value = _schema8(tmp_path / "short")
    passed = path_preflight(value["config"], limit=240)
    assert passed["status"] == "PASS"
    deep = tmp_path / ("x" * 120)
    config = WorkbenchConfig("PRIVATE", value["config"].knowledge_db,
                             deep / "state.sqlite3", deep / "artifacts",
                             value["config"].origin)
    assert path_preflight(config, limit=240)["status"] == "FAIL"


def test_backup_copy_headroom_fails_before_windows_copy(tmp_path):
    relative = "nested/" + "x" * 241
    if os.name == "nt":
        with pytest.raises(BoundaryError, match="PATH_LENGTH_UNSAFE"):
            _require_copy_headroom(tmp_path, [relative])
    else:
        _require_copy_headroom(tmp_path, [relative])
