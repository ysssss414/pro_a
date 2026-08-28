import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pro_a import ima_sync
from pro_a.api import create_app
from pro_a.db import now_iso
from pro_a.ima import IMAClient
from pro_a.pipeline import IngestionPipeline
from pro_a.storage import sha256_file
from ima_helpers import IMASimulator, enable_ima, no_live_services
from multiformat_helpers import write_source
from stability_helpers import make_config
from test_multiformat_ingestion import FixtureLLM


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    no_live_services(monkeypatch)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    cfg, db = make_config(tmp_path)
    enable_ima(cfg)
    path = cfg.root / "archive" / "fixture.txt"
    write_source(path)
    db.execute("""INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at)
                  VALUES(?,?,?,?,?,'archive',?)""", ("SRC_FIXTURE", "Mutable analyzed title", path.name, str(path), sha256_file(path), now_iso()))
    return cfg, db, path, IMASimulator(monkeypatch)


def canonical_snapshot(db):
    tables = [r["name"] for r in db.all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    result = {}
    for table in tables:
        if table == "ima_objects":
            continue
        rows = db.all(f'SELECT * FROM "{table}" ORDER BY rowid')
        if table == "sources":
            rows = [{k: v for k, v in row.items() if k not in {"ima_media_id", "ima_kb_id"}} for row in rows]
        result[table] = rows
    return result


def insert_mapping(db, *, status="synced", media="simulated-media", kb="simulated-source-kb", mapping_id="IMA_EXISTING"):
    db.execute("""INSERT INTO ima_objects(mapping_id,local_object_type,local_object_id,ima_kb_id,ima_folder_id,
                  ima_media_id,title,synced_at,status) VALUES(?,'source','SRC_FIXTURE',?,'simulated-source-folder',?,'title','',?)""",
               (mapping_id, kb, media, status))


@pytest.mark.parametrize("case,expected", [
    ("disabled", "DISABLED"), ("credentials", "CREDENTIALS_MISSING"), ("kb", "SOURCE_KB_NOT_CONFIGURED"),
    ("upload", "UPLOAD_ORIGINALS_DISABLED"), ("source", "SOURCE_NOT_FOUND"),
    ("archive", "ARCHIVE_FILE_MISSING"), ("extension", "UNSUPPORTED_MEDIA_TYPE"),
    ("size", "FILE_TOO_LARGE"), ("ready", "READY"),
])
def test_preflight_is_local_and_read_only(fixture, monkeypatch, case, expected):
    cfg, db, path, sim = fixture
    source_id = "SRC_FIXTURE"
    if case == "disabled":
        cfg.ima.enabled = False
    elif case == "credentials":
        monkeypatch.delenv("IMA_OPENAPI_APIKEY")
    elif case == "kb":
        cfg.ima.source_kb_id = ""
    elif case == "upload":
        cfg.ima.upload_originals = False
    elif case == "source":
        source_id = "SRC_MISSING"
    elif case == "archive":
        path.unlink()
    elif case == "extension":
        path = path.rename(path.with_suffix(".unsupported"))
        db.execute("UPDATE sources SET archived_path=?", (str(path),))
    elif case == "size":
        with path.open("wb") as file:
            file.truncate(10 * 1024 * 1024 + 1)
    before = sha256_file(cfg.db_path)
    result = ima_sync.preview_source_sync(cfg, source_id)
    assert result["preflight_status"] == expected
    assert result["would_upload"] is (case == "ready")
    assert sim.calls == [] and sha256_file(cfg.db_path) == before
    assert "archived_path" not in json.dumps(result) and "simulated-api-key" not in json.dumps(result)


@pytest.mark.parametrize("fmt", ["pdf", "docx", "xlsx", "pptx", "txt", "md"])
def test_multiformat_preflight_reuses_client_rules(fixture, fmt):
    cfg, db, _, sim = fixture
    path = cfg.root / "archive" / f"source.{fmt}"
    write_source(path)
    db.execute("UPDATE sources SET archived_path=?,original_name=?", (str(path), path.name))
    result = ima_sync.preview_source_sync(cfg, "SRC_FIXTURE")
    media_type, _, size = IMAClient(cfg.ima)._preflight(path)
    assert result["would_upload"] and (result["media_type"], result["file_size"]) == (media_type, size)
    assert sim.calls == []


def test_complete_sync_idempotency_and_canonical_boundary(fixture, monkeypatch):
    cfg, db, path, sim = fixture
    before = canonical_snapshot(db)
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["status"] == "synced" and result["result_classification"] == "SYNCED"
    assert sim.calls == result["remote_stages_attempted"] == ["duplicate_check", "create_media", "cos_upload", "add_knowledge"]
    assert sim.add_payload["title"] == "[SRC_FIXTURE] fixture.txt"
    assert sim.add_payload["knowledge_base_id"] == cfg.ima.source_kb_id
    assert canonical_snapshot(db) == before
    mapping = db.one("SELECT * FROM ima_objects")
    assert mapping["status"] == "synced" and mapping["ima_media_id"] == "simulated-media" and mapping["synced_at"]
    source = db.one("SELECT * FROM sources")
    assert source["ima_media_id"] == mapping["ima_media_id"] and source["ima_kb_id"] == mapping["ima_kb_id"]
    assert not list((cfg.root / "generated" / "current_views").iterdir())
    assert db.all("PRAGMA foreign_key_check") == []
    sim.calls.clear()
    path.unlink()
    monkeypatch.delenv("IMA_OPENAPI_APIKEY")
    sha = sha256_file(cfg.db_path)
    again = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert again["result_classification"] == "IDEMPOTENT" and again["status"] == "synced"
    assert again["mapping_before"] == again["mapping_after"] and sim.calls == []
    assert sha256_file(cfg.db_path) == sha


@pytest.mark.parametrize("case", ["source_only", "mapping_only", "media_mismatch", "kb_mismatch", "empty_synced",
                                  "multiple", "unknown_status", "failed_with_media", "partial_source"])
def test_local_mapping_conflicts_fail_closed(fixture, case):
    cfg, db, _, sim = fixture
    if case != "source_only":
        insert_mapping(db, media="" if case == "empty_synced" else "simulated-media",
                       status={"unknown_status": "unexpected", "failed_with_media": "sync_failed"}.get(case, "synced"))
    if case not in {"mapping_only", "empty_synced", "unknown_status", "failed_with_media"}:
        db.execute("UPDATE sources SET ima_media_id=?,ima_kb_id=?", (
            "different-media" if case == "media_mismatch" else "simulated-media",
            "different-kb" if case == "kb_mismatch" else "simulated-source-kb"))
    if case == "multiple":
        insert_mapping(db, kb="other-kb", mapping_id="IMA_OTHER")
    if case == "partial_source":
        db.execute("UPDATE sources SET ima_media_id=''")
    before = sha256_file(cfg.db_path)
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["result_classification"] == "LOCAL_MAPPING_CONFLICT" and result["status"] == "failed"
    assert sim.calls == [] and sha256_file(cfg.db_path) == before


def test_same_name_is_unresolved_and_never_blindly_retried(fixture):
    cfg, db, _, sim = fixture
    cfg.ima.skip_same_name = False  # Source safety cannot be disabled by the legacy client switch.
    sim.repeated = True
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["result_classification"] == "REMOTE_NAME_EXISTS_UNRESOLVED"
    assert result["status"] == "name_conflict_unresolved" and sim.calls == ["duplicate_check"]
    assert result["mapping_after"]["source"] == {"ima_media_id": "", "ima_kb_id": ""}
    mapping = db.one("SELECT * FROM ima_objects")
    assert mapping["status"] == "name_conflict_unresolved" and mapping["ima_media_id"] == ""
    sim.calls.clear()
    sha = sha256_file(cfg.db_path)
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["result_classification"] == result["result_classification"]
    assert sim.calls == [] and sha256_file(cfg.db_path) == sha


@pytest.mark.parametrize("stage", ["duplicate_check", "create_media", "cos_upload", "add_knowledge"])
def test_failure_stage_uncertainty_and_retry_boundary(fixture, stage):
    cfg, db, _, sim = fixture
    sim.fail_stage = stage
    before = canonical_snapshot(db)
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["stage"] == stage and result["remote_stages_attempted"] == sim.calls
    assert result["remote_state_uncertain"] is (stage != "duplicate_check")
    mapping = db.one("SELECT * FROM ima_objects")
    assert mapping["status"] == ("sync_failed" if stage == "duplicate_check" else "remote_state_uncertain")
    assert mapping["ima_media_id"] == ("simulated-media" if stage in {"cos_upload", "add_knowledge"} else "")
    assert result["mapping_after"]["source"] == {"ima_media_id": "", "ima_kb_id": ""}
    assert canonical_snapshot(db) == before
    sim.calls.clear()
    sim.fail_stage = ""
    retry = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert retry["status"] == ("synced" if stage == "duplicate_check" else "remote_state_uncertain")
    assert bool(sim.calls) is (stage == "duplicate_check")
    assert db.one("SELECT mapping_id FROM ima_objects")["mapping_id"] == mapping["mapping_id"]


def test_successful_remote_upload_then_local_commit_failure_is_durable(fixture, monkeypatch):
    cfg, db, _, sim = fixture
    original = ima_sync._write_mapping
    def fail_commit(conn, cfg, source, existing, status, media_id):
        result = original(conn, cfg, source, existing, status, media_id)
        if status == "synced":
            raise sqlite3.OperationalError("simulated-token final transaction failed")
        return result
    monkeypatch.setattr(ima_sync, "_write_mapping", fail_commit)
    before = canonical_snapshot(db)
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["status"] == "remote_state_uncertain" and result["stage"] == "local_mapping_commit"
    assert result["result_classification"] == "LOCAL_MAPPING_COMMIT_FAILED"
    assert result["media_id"] == "simulated-media" and sim.calls[-1] == "add_knowledge"
    assert db.one("SELECT status,ima_media_id FROM ima_objects") == {"status": "remote_state_uncertain", "ima_media_id": "simulated-media"}
    assert result["mapping_after"]["source"] == {"ima_media_id": "", "ima_kb_id": ""}
    assert canonical_snapshot(db) == before
    monkeypatch.setattr(ima_sync, "_write_mapping", original)
    sim.calls.clear()
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["status"] == "remote_state_uncertain"
    assert sim.calls == []


def test_reservation_failure_prevents_remote_calls_and_can_retry(fixture, monkeypatch):
    cfg, db, _, sim = fixture
    original = ima_sync._write_mapping
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("reservation failed")
    monkeypatch.setattr(ima_sync, "_write_mapping", fail)
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["result_classification"] == "LOCAL_MAPPING_COMMIT_FAILED"
    assert sim.calls == [] and db.all("SELECT * FROM ima_objects") == []
    monkeypatch.setattr(ima_sync, "_write_mapping", original)
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["status"] == "synced"


def test_known_identity_commit_failure_stops_before_cos(fixture, monkeypatch):
    cfg, db, _, sim = fixture
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated-token")
    monkeypatch.setattr(ima_sync, "_persist_outcome", fail)
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert sim.calls == ["duplicate_check", "create_media"]
    assert result["stage"] == "local_mapping_commit" and result["status"] == "remote_state_uncertain"
    assert result["media_id"] == "simulated-media" and result["remote_state_uncertain"]
    assert db.one("SELECT status FROM ima_objects")["status"] == "remote_state_uncertain"


def test_mapping_changed_during_upload_is_not_overwritten(fixture):
    cfg, db, _, sim = fixture
    sim.on_duplicate = lambda: db.execute("UPDATE ima_objects SET title='external change'")
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["result_classification"] == "LOCAL_MAPPING_CONFLICT"
    assert result["status"] == "remote_state_uncertain"
    assert db.one("SELECT title,status FROM ima_objects") == {"title": "external change", "status": "remote_state_uncertain"}


def test_invalid_remote_completion_cannot_persist_synced_empty_media(fixture):
    cfg, db, _, sim = fixture
    sim.created["media_id"] = ""
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["result_classification"] == "CREATE_MEDIA_INVALID_RESPONSE"
    assert result["status"] == "remote_state_uncertain"
    assert db.one("SELECT status,ima_media_id FROM ima_objects") == {"status": "remote_state_uncertain", "ima_media_id": ""}
    assert sim.calls == ["duplicate_check", "create_media"]


def test_concurrent_or_crashed_attempt_cannot_create_another_remote_object(fixture):
    cfg, db, _, sim = fixture
    nested = []
    sim.on_duplicate = lambda: nested.append(ima_sync.sync_source(cfg, "SRC_FIXTURE"))
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["status"] == "synced"
    assert nested[0]["status"] == "remote_state_uncertain"
    assert sim.calls.count("create_media") == 1


def test_interruption_keeps_conservative_reservation(fixture):
    cfg, db, _, sim = fixture
    def interrupt():
        raise KeyboardInterrupt()
    sim.on_duplicate = interrupt
    with pytest.raises(KeyboardInterrupt):
        ima_sync.sync_source(cfg, "SRC_FIXTURE")
    sim.on_duplicate = None
    sim.calls.clear()
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["status"] == "remote_state_uncertain"
    assert sim.calls == []


@pytest.mark.parametrize("sql", [
    "UPDATE sources SET title='changed'", "UPDATE sources SET source_rank='A'",
    "UPDATE sources SET metadata_json='{}'", "UPDATE sources SET status='analyzed'",
    "UPDATE sources SET ingestion_mode='deep'", "UPDATE sources SET analysis_mode='deep'",
    "DELETE FROM sources", "DELETE FROM ima_objects", "UPDATE ima_objects SET mapping_id='changed'",
    "UPDATE ima_objects SET local_object_id='changed'", "UPDATE ima_objects SET ima_kb_id='changed'",
    "INSERT INTO processing_jobs(job_id,input_path,ingestion_mode,status,started_at) VALUES('x','x','x','x','x')",
    "UPDATE claims SET statement='changed'", "UPDATE nodes SET description='changed'",
    "UPDATE node_relations SET scope='changed'", "UPDATE current_views SET content_md='changed'",
    "UPDATE proposals SET status='accepted'", "UPDATE impact_reviews SET status='done'",
    "UPDATE side_effect_jobs SET status='done'", "UPDATE research_questions SET question='changed'",
    "UPDATE knowledge_gaps SET title='changed'", "CREATE TABLE unsafe(x)", "PRAGMA user_version=9",
    "ATTACH DATABASE ':memory:' AS other",
])
def test_column_level_write_guard_denies_every_non_ima_write(fixture, sql):
    cfg, db, _, _ = fixture
    before = sha256_file(cfg.db_path)
    with ima_sync._connect(cfg.db_path, write=True) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(sql)
    assert sha256_file(cfg.db_path) == before


def test_write_guard_blocks_trigger_side_effects(fixture):
    cfg, db, _, sim = fixture
    db.execute("CREATE TRIGGER unsafe AFTER INSERT ON ima_objects BEGIN UPDATE sources SET title='changed'; END")
    before = canonical_snapshot(db)
    result = ima_sync.sync_source(cfg, "SRC_FIXTURE")
    assert result["result_classification"] == "LOCAL_MAPPING_COMMIT_FAILED"
    assert sim.calls == [] and canonical_snapshot(db) == before and not db.all("SELECT * FROM ima_objects")


@pytest.mark.parametrize("fmt", ["pdf", "docx"])
def test_isolated_ingestion_preview_sync_receipt_and_source_detail(tmp_path, monkeypatch, fmt):
    cfg, db = make_config(tmp_path)
    sim = IMASimulator(monkeypatch)
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = FixtureLLM()
    incoming = cfg.root / "inbox" / "standard" / f"source.{fmt}"
    write_source(incoming)
    ingestion = pipeline.process_file(incoming, "standard")
    assert ingestion["status"] == "analyzed" and ingestion["ima_status"] == "disabled"
    source_id = ingestion["source_id"]
    enable_ima(cfg)
    before = canonical_snapshot(db)
    sha = sha256_file(cfg.db_path)
    preview = ima_sync._run_operation(cfg, source_id, "preview-source")
    assert preview["would_upload"] and Path(preview["receipt_path"]).is_file()
    assert sim.calls == [] and sha256_file(cfg.db_path) == sha
    receipt = ima_sync._run_operation(cfg, source_id, "sync-production-source")
    assert receipt["status"] == "synced" and canonical_snapshot(db) == before
    written = Path(receipt["receipt_path"]).read_text(encoding="utf-8")
    assert json.loads(written) == receipt
    assert not any(value in written for value in ["simulated-api-key", "simulated-client-id", "simulated-secret", "simulated-token", "simulated-cos-key", "archived_path"])
    with TestClient(create_app(cfg.db_path, ima_source_kb_id=cfg.ima.source_kb_id)) as client:
        result = client.get(f"/api/sources/{source_id}")
    assert result.status_code == 200
    assert result.json()["ima_sync"] == {"status": "synced", "target_configured": True, "mapped": True, "message": "Synced to IMA"}
    assert result.json()["parse_diagnostics"]["format"] == fmt
    assert "ima_media_id" not in result.text and "archived_path" not in result.text


@pytest.mark.parametrize("stage", ["duplicate_check", "cos_upload", "same_name"])
def test_pipeline_ima_outage_or_same_name_preserves_ingestion(tmp_path, monkeypatch, stage):
    cfg, db = make_config(tmp_path)
    enable_ima(cfg)
    sim = IMASimulator(monkeypatch)
    sim.fail_stage = stage
    sim.repeated = stage == "same_name"
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = FixtureLLM()
    incoming = cfg.root / "inbox" / "standard" / "source.pdf"
    write_source(incoming)
    result = pipeline.process_file(incoming, "standard")
    assert result["status"] == "analyzed" and len(result["claims"]) == 2
    assert db.one("SELECT status,analysis_mode,ima_media_id,ima_kb_id FROM sources") == {
        "status": "analyzed", "analysis_mode": "standard", "ima_media_id": "", "ima_kb_id": ""}
    assert result["ima_status"] == {"duplicate_check": "failed", "cos_upload": "remote_state_uncertain", "same_name": "name_conflict_unresolved"}[stage]
    written = Path(result["receipt_path"]).read_text(encoding="utf-8")
    assert result["warnings"] and "simulated-token" not in written and "simulated-api-key" not in written
    if stage == "same_name":
        assert "IMA remote name exists but local media identity is unresolved." in result["warnings"]


def load_cli():
    spec = importlib.util.spec_from_file_location("phase3b_cli", Path(__file__).parents[1] / "scripts" / "phase3b_ima_sync.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("args", [[], ["sync"], ["sync-production-source", "--source-id", "SRC_FIXTURE", "--db", "arbitrary.db"],
                                ["sync-production-source", "--source-id", "SRC_FIXTURE", "--config", "other.toml"]])
def test_cli_has_no_default_upload_or_caller_supplied_production_db(args):
    with pytest.raises(SystemExit) as caught:
        load_cli().main(args)
    assert caught.value.code == 2


def test_cli_uses_load_config_and_writes_a_receipt_per_operation(fixture, monkeypatch, capsys):
    cfg, db, _, sim = fixture
    monkeypatch.setattr(ima_sync, "load_config", lambda: cfg)
    cli = load_cli()
    before = sha256_file(cfg.db_path)
    assert cli.main(["preview-source", "--source-id", "SRC_FIXTURE"]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert sha256_file(cfg.db_path) == before and sim.calls == []
    assert cli.main(["sync-production-source", "--source-id", "SRC_FIXTURE"]) == 0
    synced = json.loads(capsys.readouterr().out)
    assert synced["status"] == "synced" and synced["receipt_path"] != preview["receipt_path"]
    assert Path(preview["receipt_path"]).exists() and Path(synced["receipt_path"]).exists()


def test_missing_database_is_not_initialized_and_still_has_failure_receipt(fixture):
    cfg, db, _, sim = fixture
    cfg.db_path.unlink()
    result = ima_sync._run_operation(cfg, "SRC_FIXTURE", "sync-production-source")
    assert result["preflight_status"] == "LOCAL_DATABASE_UNAVAILABLE" and result["status"] == "failed"
    assert not cfg.db_path.exists() and sim.calls == []
    assert json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))["status"] == "failed"


def test_receipt_setup_failure_never_starts_remote_upload(fixture, monkeypatch):
    cfg, _, _, sim = fixture
    def fail(*args, **kwargs):
        raise OSError("receipt unavailable")
    monkeypatch.setattr(ima_sync, "write_json", fail)
    with pytest.raises(OSError):
        ima_sync._run_operation(cfg, "SRC_FIXTURE", "sync-production-source")
    assert sim.calls == []


def test_final_receipt_failure_does_not_claim_upload_rollback(fixture, monkeypatch):
    cfg, db, _, sim = fixture
    original = ima_sync.write_json
    def fail_final(path, receipt):
        if receipt["status"] == "synced":
            raise OSError("simulated-token")
        original(path, receipt)
    monkeypatch.setattr(ima_sync, "write_json", fail_final)
    result = ima_sync._run_operation(cfg, "SRC_FIXTURE", "sync-production-source")
    assert result["status"] == "synced" and result["receipt_error"] == "SYNC_RECEIPT_WRITE_FAILED"
    assert db.one("SELECT status FROM ima_objects")["status"] == "synced"
    sim.calls.clear()
    assert ima_sync.sync_source(cfg, "SRC_FIXTURE")["result_classification"] == "IDEMPOTENT"
    assert sim.calls == []


@pytest.mark.parametrize("status,media", [("sync_failed", ""), ("name_conflict_unresolved", ""), ("remote_state_uncertain", "simulated-media"), ("synced", "")])
def test_source_detail_exposes_safe_read_only_status(fixture, status, media):
    cfg, db, _, sim = fixture
    insert_mapping(db, status=status, media=media)
    sha = sha256_file(cfg.db_path)
    app = create_app(cfg.db_path, ima_source_kb_id=cfg.ima.source_kb_id)
    with TestClient(app) as client:
        response = client.get("/api/sources/SRC_FIXTURE")
        assert response.json()["ima_sync"]["status"] == ("local_mapping_conflict" if status == "synced" else status)
        assert response.json()["ima_sync"]["mapped"] is False
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)("/api/sources/SRC_FIXTURE/ima-sync").status_code in {404, 405}
    assert sim.calls == [] and sha256_file(cfg.db_path) == sha
