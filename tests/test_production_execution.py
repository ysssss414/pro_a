from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.config import AppConfig, IMAConfig, LLMConfig, PipelineConfig, WorkspaceConfig
from pro_a.db import Database
from pro_a import production_execution as pe
from pro_a.production_promotion import production_identity, sha256_file


FEATURE_SHA = "abc123feature"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def app_config(root: Path) -> AppConfig:
    return AppConfig(
        workspace=WorkspaceConfig(root=root),
        llm=LLMConfig(),
        ima=IMAConfig(),
        pipeline=PipelineConfig(),
        config_path=root / "config.toml",
    )


def source_row(source_sha: str) -> dict:
    return {
        "source_id": "SRC_FIXTURE",
        "title": "Fixture source",
        "original_name": "fixture.bin",
        "archived_path": "archive/fixture.bin",
        "sha256": source_sha,
        "ingestion_mode": "deep",
        "analysis_mode": "deep",
        "source_type": "binary",
        "source_rank": "B",
        "origin_type": "secondary",
        "author": "",
        "organization": "Fixture",
        "publication_time": "2026-01-01",
        "ingested_at": "2026-01-02T00:00:00+00:00",
        "status": "analyzed",
        "ima_media_id": "",
        "ima_kb_id": "",
        "underlying_source_id": "",
        "metadata_json": "{}",
    }


@pytest.fixture
def execution_fixture(tmp_path: Path, monkeypatch) -> dict:
    target_root = tmp_path / "emulated"
    target = target_root / "pro_a.db"
    Database(target).init_schema()
    baseline = production_identity(target)
    source = tmp_path / "candidate" / "source" / "fixture.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"phase3d qualification source")
    source_sha = sha256_file(source)
    row = source_row(source_sha)
    payload = {
        "document_type": "phase3d_authorization_bound_promotion_payload",
        "payload_version": "1",
        "payload_id": "PROMO_FIXTURE",
        "payload_hash": "fixture-payload-sha",
        "metadata": {
            "repository_commit": FEATURE_SHA,
            "production_sha256": baseline["sha256"],
            "production_schema_version": baseline["schema_version"],
            "production_schema_sha256": baseline["schema_sha256"],
            "production_counts": baseline["counts"],
            "source_id": "SRC_FIXTURE",
            "source_sha256": source_sha,
        },
        "source_materialization": {
            "source_id": "SRC_FIXTURE",
            "size": source.stat().st_size,
            "package_sha256": source_sha,
            "archive_logical_destination": "archive/fixture.bin",
            "production_archive_copy_authorized": False,
        },
        "human_authorization": {
            "human_review_id": "HUMAN_FIXTURE",
            "human_review_sha256": "human-fixture-sha",
        },
        "node_operations": [],
        "relation_operations": [],
        "intended_mutations": [{
            "mutation_id": "MUT_SOURCE_FIXTURE",
            "table": "sources",
            "operation": "INSERT",
            "key": {"source_id": "SRC_FIXTURE"},
            "row": row,
        }],
        "qualified_execution_target": "SHADOW_ONLY",
        "production_apply_authorized": False,
    }
    candidate = tmp_path / "candidate"
    payload_path = candidate / "phase3d_production_apply_payload.json"
    plan_path = candidate / "production_apply_plan.json"
    receipt_path = candidate / "phase3d_release_shadow_receipt.json"
    materialization_path = candidate / "source_materialization_release.json"
    write_json(payload_path, payload)
    write_json(plan_path, {
        "document_type": pe.PLAN_DOCUMENT_TYPE,
        "status": "AWAITING_EXPLICIT_USER_AUTHORIZATION",
        "release_commit": FEATURE_SHA,
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "production_pre_sha256": baseline["sha256"],
        "source_sha256": source_sha,
        "steps": [{"step": index} for index in range(1, 15)],
        "constraints": {"production_apply_authorized": False},
    })
    write_json(receipt_path, {
        "status": "PASS",
        "release": {"commit": FEATURE_SHA},
        "payload": {"payload_id": payload["payload_id"], "payload_sha256": payload["payload_hash"]},
        "flags": {
            "release_shadow_preflight_pass": True,
            "release_shadow_apply_pass": True,
            "release_shadow_postflight_pass": True,
        },
    })
    write_json(materialization_path, {
        "status": "SOURCE_PACKAGE_FROZEN",
        "source": {"source_id": "SRC_FIXTURE", "original_sha256": source_sha},
        "package": {"sha256": source_sha},
        "flags": {"production_apply_authorized": False},
    })
    artifact_paths = {
        "source_package": source,
        "production_apply_payload": payload_path,
        "release_shadow_receipt": receipt_path,
        "production_apply_plan": plan_path,
        "source_materialization": materialization_path,
    }
    manifest = {
        "document_type": pe.MANIFEST_DOCUMENT_TYPE,
        "status": "PASS_QUALIFICATION_ONLY",
        "release_commit": FEATURE_SHA,
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "flags": {"production_apply_authorized": False},
        "artifacts": [
            {
                "role": role,
                "path": path.relative_to(candidate).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for role, path in artifact_paths.items()
        ],
    }
    manifest_path = candidate / "production_apply_candidate_manifest.json"
    write_json(manifest_path, manifest)
    config = app_config(target_root)
    authorization = {
        "document_type": pe.AUTHORIZATION_DOCUMENT_TYPE,
        "authorization_version": pe.AUTHORIZATION_VERSION,
        "authorization_id": "QUAL_AUTH_0001",
        "authority": "USER",
        "scope": "EXACT_PAYLOAD_ONE_TIME",
        "status": "AUTHORIZED",
        "authorization_environment": "QUALIFICATION",
        "real_production_authorization": False,
        "release_commit_sha": FEATURE_SHA,
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "payload_file_sha256": sha256_file(payload_path),
        "candidate_manifest_sha256": sha256_file(manifest_path),
        "expected_production_sha256": baseline["sha256"],
        "source_id": payload["metadata"]["source_id"],
        "source_sha256": source_sha,
        "human_review_id": payload["human_authorization"]["human_review_id"],
        "human_review_sha256": payload["human_authorization"]["human_review_sha256"],
        "expected_operation_counts": pe.payload_operation_counts(payload),
        "target_database_identity": {"resolved_path": str(target.resolve())},
        "target_archive_identity": {"resolved_root": str(target_root.resolve())},
        "authorization_consumed": False,
    }
    authorization_path = tmp_path / "authorization.json"
    write_json(authorization_path, authorization)
    protected = tmp_path / "protected-real" / "pro_a.db"
    execution_root = target_root / pe.EXECUTION_STATE_RELATIVE_ROOT
    monkeypatch.setattr(pe, "validate_final_payload", lambda _payload: None)
    monkeypatch.setattr(pe, "validate_executable_operations", lambda _connection, _payload: None)
    return {
        "target_root": target_root,
        "target": target,
        "baseline": baseline,
        "source": source,
        "source_sha": source_sha,
        "payload": payload,
        "payload_path": payload_path,
        "candidate": candidate,
        "manifest_path": manifest_path,
        "authorization": authorization,
        "authorization_path": authorization_path,
        "config": config,
        "protected": protected,
        "execution_root": execution_root,
    }


def execute(fixture: dict, **overrides):
    arguments = {
        "candidate_dir": fixture["candidate"],
        "authorization_path": fixture["authorization_path"],
        "config": fixture["config"],
        "execution_commit": FEATURE_SHA,
        "protected_real_production_path": fixture["protected"],
    }
    arguments.update(overrides)
    return pe.execute_authorized_production(**arguments)


def rewrite_authorization(fixture: dict, **changes) -> None:
    fixture["authorization"].update(changes)
    write_json(fixture["authorization_path"], fixture["authorization"])


def test_authorized_top_level_emulation_and_one_time_consumption(execution_fixture: dict):
    original_authorization_sha = sha256_file(execution_fixture["authorization_path"])
    result = execute(execution_fixture)
    assert result["status"] == "COMPLETE"
    assert result["production_pre_sha256"] == execution_fixture["baseline"]["sha256"]
    assert result["changed_tables"] == {"sources": {"added": 1, "removed": 0}}
    assert result["locked_revalidation_pass"] is True
    assert result["backup_sha256"] == execution_fixture["baseline"]["sha256"]
    assert Path(result["backup_path"]).is_file()
    assert Path(result["journal_path"]).parent.parent == execution_fixture["execution_root"]
    assert Path(result["archive_destination"]).read_bytes() == execution_fixture["source"].read_bytes()
    assert sha256_file(execution_fixture["authorization_path"]) == original_authorization_sha
    receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["status"] == "COMPLETE"
    assert receipt["authorization_consumed"] is True
    second = execute(execution_fixture)
    assert second["status"] == "AUTHORIZATION_ALREADY_CONSUMED"
    assert second["production_apply_attempted"] is False


def test_source_staging_name_stays_short_for_long_archive_destination(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    archive = tmp_path / "archive"
    filename_length = 235 - len(str(archive)) - 1
    destination = archive / ("x" * (filename_length - 4) + ".bin")

    materialized, _ = pe._materialize_source(
        source,
        destination,
        sha256_file(source),
        "A" * 128,
    )

    assert materialized == destination
    assert materialized.read_bytes() == b"source"
    assert not list(archive.glob(".phase3d-source-*.tmp"))


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("authority", "LLM", "AUTHORIZATION_AUTHORITY_INVALID"),
        ("scope", "ANY_PAYLOAD", "AUTHORIZATION_SCOPE_INVALID"),
        ("status", "PENDING", "AUTHORIZATION_STATUS_INVALID"),
        ("release_commit_sha", "wrong", "AUTHORIZATION_RELEASE_MISMATCH"),
        ("payload_id", "wrong", "AUTHORIZATION_PAYLOAD_ID_MISMATCH"),
        ("payload_sha256", "wrong", "AUTHORIZATION_PAYLOAD_SHA_MISMATCH"),
        ("payload_file_sha256", "wrong", "AUTHORIZATION_PAYLOAD_FILE_SHA_MISMATCH"),
        ("candidate_manifest_sha256", "wrong", "AUTHORIZATION_MANIFEST_SHA_MISMATCH"),
        ("expected_production_sha256", "wrong", "AUTHORIZATION_BASELINE_MISMATCH"),
        ("authorization_consumed", True, "AUTHORIZATION_ARTIFACT_ALREADY_CONSUMED"),
    ],
)
def test_authorization_contract_rejects_mismatches(execution_fixture: dict, field: str, value, error: str):
    rewrite_authorization(execution_fixture, **{field: value})
    with pytest.raises(pe.ProductionExecutionError, match=error):
        execute(execution_fixture)
    assert production_identity(execution_fixture["target"])["sha256"] == execution_fixture["baseline"]["sha256"]


def test_missing_authorization_is_rejected(execution_fixture: dict):
    execution_fixture["authorization_path"].unlink()
    with pytest.raises(pe.ProductionExecutionError, match="JSON_ARTIFACT_MISSING"):
        execute(execution_fixture)


def test_wrong_database_and_archive_targets_are_rejected(execution_fixture: dict):
    rewrite_authorization(
        execution_fixture,
        target_database_identity={"resolved_path": str(execution_fixture["target"].with_name("other.db"))},
    )
    with pytest.raises(pe.ProductionExecutionError, match="AUTHORIZATION_TARGET_DATABASE_MISMATCH"):
        execute(execution_fixture)

    rewrite_authorization(
        execution_fixture,
        target_database_identity={"resolved_path": str(execution_fixture["target"])},
        target_archive_identity={"resolved_root": str(execution_fixture["target_root"].with_name("other-root"))},
    )
    with pytest.raises(pe.ProductionExecutionError, match="AUTHORIZATION_TARGET_ARCHIVE_MISMATCH"):
        execute(execution_fixture)


def test_qualification_authorization_cannot_target_real_production(execution_fixture: dict, monkeypatch):
    monkeypatch.setattr(pe, "production_identity", lambda _path: pytest.fail("Production preflight must not run"))
    with pytest.raises(pe.ProductionExecutionError, match="QUALIFICATION_AUTHORIZATION_TARGETS_REAL_PRODUCTION"):
        execute(execution_fixture, protected_real_production_path=execution_fixture["target"])


def test_real_authorization_cannot_target_another_database(execution_fixture: dict):
    rewrite_authorization(
        execution_fixture,
        authorization_environment="PRODUCTION",
        real_production_authorization=True,
    )
    with pytest.raises(pe.ProductionExecutionError, match="PRODUCTION_AUTHORIZATION_TARGET_MISMATCH"):
        execute(execution_fixture)


def test_candidate_payload_and_source_tampering_fail_before_target_access(execution_fixture: dict, monkeypatch):
    monkeypatch.setattr(pe, "production_identity", lambda _path: pytest.fail("Target must not be opened"))
    execution_fixture["source"].write_bytes(b"tampered")
    with pytest.raises(pe.ProductionExecutionError, match="CANDIDATE_ARTIFACT_(SIZE|SHA)_MISMATCH"):
        execute(execution_fixture)


def test_unsupported_mutation_table_is_rejected(execution_fixture: dict):
    payload = copy.deepcopy(execution_fixture["payload"])
    payload["intended_mutations"].append({
        "mutation_id": "MUT_FORBIDDEN",
        "table": "proposals",
        "operation": "INSERT",
        "key": {"proposal_id": "P"},
        "row": {"proposal_id": "P"},
    })
    with pytest.raises(pe.ProductionExecutionError, match="UNSUPPORTED_PRODUCTION_MUTATION_TABLES"):
        pe.validate_supported_mutations(payload)


@pytest.mark.parametrize(
    ("failure_point", "error"),
    [
        ("before_source_finalization", "INJECTED_BEFORE_SOURCE_FINALIZATION"),
        ("after_source_materialization", "INJECTED_AFTER_SOURCE_MATERIALIZATION"),
        ("during_db_transaction", "INJECTED_PRODUCTION_TRANSACTION_FAILURE"),
        ("after_db_commit", "INJECTED_AFTER_DB_COMMIT"),
    ],
)
def test_failure_paths_restore_database_archive_and_record_journal(
    execution_fixture: dict,
    failure_point: str,
    error: str,
):
    with pytest.raises(pe.ProductionExecutionError, match=error):
        execute(execution_fixture, failure_point=failure_point)
    restored = production_identity(execution_fixture["target"])
    assert restored["sha256"] == execution_fixture["baseline"]["sha256"]
    assert restored["integrity"] == "ok"
    assert restored["foreign_key_violations"] == []
    assert not (execution_fixture["target_root"] / "archive" / "fixture.bin").exists()
    journal = json.loads(
        (
            execution_fixture["execution_root"]
            / execution_fixture["authorization"]["authorization_id"]
            / "execution_journal.json"
        ).read_text(encoding="utf-8")
    )
    assert journal["state"] == "FAILED_RESTORED"
    assert journal["transitions"][-1]["state"] == "FAILED_RESTORED"
    assert Path(journal["backup_path"]).is_file()
    with pytest.raises(pe.ProductionExecutionError, match="AUTHORIZATION_PREVIOUS_ATTEMPT_FAILED_RESTORED"):
        execute(execution_fixture)


def test_backup_sha_failure_prevents_source_or_database_mutation(execution_fixture: dict, monkeypatch):
    real_sha256_file = pe.sha256_file

    def mismatched_backup(path: Path, *args, **kwargs) -> str:
        if Path(path).name == "production_pre.db":
            return "0" * 64
        return real_sha256_file(path, *args, **kwargs)

    monkeypatch.setattr(pe, "sha256_file", mismatched_backup)
    with pytest.raises(pe.ProductionExecutionError, match="PRODUCTION_BACKUP_SHA_MISMATCH"):
        execute(execution_fixture)
    assert production_identity(execution_fixture["target"])["sha256"] == execution_fixture["baseline"]["sha256"]
    assert not (execution_fixture["target_root"] / "archive" / "fixture.bin").exists()


def test_locked_source_collision_fails_closed(execution_fixture: dict):
    payload = execution_fixture["payload"]
    connection = sqlite3.connect(execution_fixture["target"])
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            "INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at) VALUES(?,?,?,?,?,?,?)",
            ("SRC_FIXTURE", "Existing", "x", "archive/x", execution_fixture["source_sha"], "deep", "2026-01-01"),
        )
        connection.commit()
        changed = production_identity(execution_fixture["target"])
        payload["metadata"]["production_sha256"] = changed["sha256"]
        payload["metadata"]["production_counts"] = changed["counts"]
        payload["metadata"]["production_schema_sha256"] = changed["schema_sha256"]
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(pe.ProductionExecutionError, match="LOCKED_SOURCE_COLLISION"):
            pe._locked_revalidation(connection, payload, execution_fixture["target"])
        connection.rollback()
    finally:
        connection.close()


def test_locked_revalidation_rejects_same_count_baseline_drift(execution_fixture: dict):
    payload = execution_fixture["payload"]
    connection = sqlite3.connect(execution_fixture["target"])
    try:
        connection.execute(
            "INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at) VALUES(?,?,?,?,?,?,?)",
            ("SRC_OTHER", "Before", "x", "archive/x", "1" * 64, "deep", "2026-01-01"),
        )
        connection.commit()
        frozen = production_identity(execution_fixture["target"])
        payload["metadata"]["production_sha256"] = frozen["sha256"]
        payload["metadata"]["production_counts"] = frozen["counts"]
        payload["metadata"]["production_schema_sha256"] = frozen["schema_sha256"]
        connection.execute("UPDATE sources SET title='Concurrent drift' WHERE source_id='SRC_OTHER'")
        connection.commit()
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(pe.ProductionExecutionError, match="LOCKED_BASELINE_SHA_MISMATCH"):
            pe._locked_revalidation(connection, payload, execution_fixture["target"])
        connection.rollback()
    finally:
        connection.close()


def test_precommit_external_drift_is_not_overwritten_by_backup(execution_fixture: dict, monkeypatch):
    def drift_then_fail(*_args, **_kwargs):
        connection = sqlite3.connect(execution_fixture["target"])
        try:
            connection.execute("INSERT INTO meta(key,value) VALUES('external-drift','preserve-me')")
            connection.commit()
        finally:
            connection.close()
        raise pe.ProductionExecutionError("SIMULATED_PRECOMMIT_FAILURE")

    monkeypatch.setattr(pe, "_materialize_source", drift_then_fail)
    with pytest.raises(pe.ProductionExecutionError, match="PRODUCTION_STATE_UNCERTAIN"):
        execute(execution_fixture)

    connection = sqlite3.connect(execution_fixture["target"])
    try:
        value = connection.execute("SELECT value FROM meta WHERE key='external-drift'").fetchone()
    finally:
        connection.close()
    assert value == ("preserve-me",)
    journal = json.loads(
        (
            execution_fixture["execution_root"]
            / execution_fixture["authorization"]["authorization_id"]
            / "execution_journal.json"
        ).read_text(encoding="utf-8")
    )
    assert journal["state"] == "UNCERTAIN"


@pytest.mark.parametrize("state", sorted(pe.INCOMPLETE_STATES))
def test_incomplete_journal_states_require_recovery(execution_fixture: dict, state: str):
    authorization_sha = sha256_file(execution_fixture["authorization_path"])
    journal_path = (
        execution_fixture["execution_root"]
        / execution_fixture["authorization"]["authorization_id"]
        / "execution_journal.json"
    )
    write_json(journal_path, {
        "document_type": pe.JOURNAL_DOCUMENT_TYPE,
        "authorization_id": execution_fixture["authorization"]["authorization_id"],
        "authorization_file_sha256": authorization_sha,
        "release_commit_sha": FEATURE_SHA,
        "payload_sha256": execution_fixture["payload"]["payload_hash"],
        "production_pre_sha256": execution_fixture["payload"]["metadata"]["production_sha256"],
        "state": state,
    })
    with pytest.raises(pe.ProductionExecutionError, match=f"INCOMPLETE_EXECUTION_REQUIRES_RECOVERY:{state}"):
        execute(execution_fixture)


def test_uncertain_journal_refuses_further_execution(execution_fixture: dict):
    authorization_sha = sha256_file(execution_fixture["authorization_path"])
    journal_path = (
        execution_fixture["execution_root"]
        / execution_fixture["authorization"]["authorization_id"]
        / "execution_journal.json"
    )
    write_json(journal_path, {
        "document_type": pe.JOURNAL_DOCUMENT_TYPE,
        "authorization_id": execution_fixture["authorization"]["authorization_id"],
        "authorization_file_sha256": authorization_sha,
        "release_commit_sha": FEATURE_SHA,
        "payload_sha256": execution_fixture["payload"]["payload_hash"],
        "production_pre_sha256": execution_fixture["payload"]["metadata"]["production_sha256"],
        "state": "UNCERTAIN",
    })
    with pytest.raises(pe.ProductionExecutionError, match="EXECUTION_STATE_UNCERTAIN"):
        execute(execution_fixture)
