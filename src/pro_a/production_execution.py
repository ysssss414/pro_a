from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from pro_a.config import AppConfig
from pro_a.production_final_qualification import (
    filesystem_inventory,
    validate_final_payload,
)
from pro_a.production_promotion import (
    PromotionError,
    _diff_rows,
    _insert_mutation,
    _row_equal,
    _row_for_key,
    _write_authorizer,
    connect_read_only,
    database_identity,
    database_rows,
    production_identity,
    schema_sha256,
    sha256_file,
    table_counts,
    validate_executable_operations,
)


AUTHORIZATION_DOCUMENT_TYPE = "phase3d_production_execution_authorization"
AUTHORIZATION_VERSION = "1"
AUTHORIZATION_AUTHORITY = "USER"
AUTHORIZATION_SCOPE = "EXACT_PAYLOAD_ONE_TIME"
AUTHORIZATION_STATUS = "AUTHORIZED"
AUTHORIZATION_ENVIRONMENTS = {"PRODUCTION", "QUALIFICATION"}
MANIFEST_DOCUMENT_TYPE = "phase3d_production_apply_candidate_manifest"
PLAN_DOCUMENT_TYPE = "phase3d_production_apply_plan"
JOURNAL_DOCUMENT_TYPE = "phase3d_production_execution_journal"
RECEIPT_DOCUMENT_TYPE = "phase3d_production_apply_receipt"
EXECUTION_STATE_RELATIVE_ROOT = Path("phase3d") / "production-executions"
ALLOWED_MUTATION_TABLES = {"sources", "claims", "nodes", "node_aliases"}
INCOMPLETE_STATES = {"PREPARED", "SOURCE_MATERIALIZED", "DB_COMMITTED"}
TERMINAL_STATES = {"COMPLETE", "FAILED_RESTORED", "UNCERTAIN"}


class ProductionExecutionError(PromotionError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ProductionExecutionError(code)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    _require(path.is_file(), f"JSON_ARTIFACT_MISSING:{path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionExecutionError(f"JSON_ARTIFACT_INVALID:{path.name}") from exc
    _require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def _write_json_atomic(path: Path, value: Mapping[str, Any], *, immutable: bool = False) -> None:
    path = Path(path)
    if immutable:
        _require(not path.exists(), f"IMMUTABLE_ARTIFACT_EXISTS:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    _require(not temporary.exists(), f"ARTIFACT_STAGING_CONFLICT:{temporary.name}")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _paths_equivalent(first: Path, second: Path) -> bool:
    first = Path(first).resolve()
    second = Path(second).resolve()
    if first == second:
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError:
        return False


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    _require(bool(value) and not path.is_absolute(), "ARCHIVE_DESTINATION_NOT_RELATIVE")
    _require(all(part not in {"", ".", ".."} for part in path.parts), "ARCHIVE_DESTINATION_UNSAFE")
    _require(path.parts[0] == "archive", "ARCHIVE_DESTINATION_OUTSIDE_ARCHIVE")
    return path


def _path_within(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def payload_operation_counts(payload: Mapping[str, Any]) -> dict[str, int]:
    mutations = payload.get("intended_mutations") or []
    node_operations = payload.get("node_operations") or []
    relation_operations = payload.get("relation_operations") or []
    return {
        "source_create": sum(item.get("table") == "sources" for item in mutations),
        "claim_create": sum(item.get("table") == "claims" for item in mutations),
        "node_create": sum(item.get("operation") == "CREATE" for item in node_operations),
        "node_reuse": sum(item.get("operation") == "REUSE" for item in node_operations),
        "alias_create": sum(item.get("table") == "node_aliases" for item in mutations),
        "node_defer": sum(item.get("operation") == "DEFER" for item in node_operations),
        "node_reject": sum(item.get("operation") == "REJECT" for item in node_operations),
        "relation_create": sum(
            bool(item.get("executable")) and item.get("operation") == "CREATE"
            for item in relation_operations
        ),
        "relation_reuse": sum(
            bool(item.get("executable")) and item.get("operation") == "REUSE"
            for item in relation_operations
        ),
        "relation_executable": sum(bool(item.get("executable")) for item in relation_operations),
        "relation_reject": sum(item.get("operation") == "REJECT" for item in relation_operations),
        "claim_node_link_create": sum(item.get("table") == "claim_node_links" for item in mutations),
        "source_node_link_create": sum(item.get("table") == "source_node_links" for item in mutations),
    }


def validate_supported_mutations(payload: Mapping[str, Any]) -> set[str]:
    mutations = payload.get("intended_mutations") or []
    _require(bool(mutations), "EMPTY_PRODUCTION_MUTATION_SET")
    tables = {str(item.get("table")) for item in mutations}
    _require(tables <= ALLOWED_MUTATION_TABLES, f"UNSUPPORTED_PRODUCTION_MUTATION_TABLES:{sorted(tables)}")
    _require(all(item.get("operation") == "INSERT" for item in mutations), "UNSUPPORTED_PRODUCTION_MUTATION_OPERATION")
    _require(
        not any(item.get("executable") for item in payload.get("relation_operations") or []),
        "EXECUTABLE_RELATION_FORBIDDEN",
    )
    _require(
        all(not (item.get("approved_aliases") or []) for item in payload.get("node_operations") or [] if item.get("operation") == "REUSE"),
        "REUSE_ALIAS_MUTATION_FORBIDDEN",
    )
    return tables


def validate_candidate_package(candidate_dir: Path) -> dict[str, Any]:
    candidate_dir = Path(candidate_dir).resolve()
    manifest_path = candidate_dir / "production_apply_candidate_manifest.json"
    manifest = _load_json(manifest_path)
    _require(manifest.get("document_type") == MANIFEST_DOCUMENT_TYPE, "CANDIDATE_MANIFEST_DOCUMENT_TYPE_MISMATCH")
    _require(str(manifest.get("status", "")).startswith("PASS"), "CANDIDATE_MANIFEST_NOT_QUALIFIED")

    artifacts: dict[str, Path] = {}
    for artifact in manifest.get("artifacts") or []:
        role = artifact.get("role")
        _require(isinstance(role, str) and role not in artifacts, "CANDIDATE_MANIFEST_ROLE_INVALID")
        relative = Path(str(artifact.get("path", "")))
        _require(not relative.is_absolute() and ".." not in relative.parts, f"CANDIDATE_ARTIFACT_PATH_UNSAFE:{role}")
        path = (candidate_dir / relative).resolve()
        _require(_path_within(path, candidate_dir), f"CANDIDATE_ARTIFACT_PATH_ESCAPE:{role}")
        _require(path.is_file(), f"CANDIDATE_ARTIFACT_MISSING:{role}")
        _require(path.stat().st_size == artifact.get("size"), f"CANDIDATE_ARTIFACT_SIZE_MISMATCH:{role}")
        _require(sha256_file(path) == artifact.get("sha256"), f"CANDIDATE_ARTIFACT_SHA_MISMATCH:{role}")
        artifacts[role] = path

    required_roles = {
        "source_package",
        "production_apply_payload",
        "release_shadow_receipt",
        "production_apply_plan",
        "source_materialization",
    }
    _require(required_roles <= set(artifacts), "CANDIDATE_MANIFEST_REQUIRED_ROLE_MISSING")
    payload_path = artifacts["production_apply_payload"]
    payload = _load_json(payload_path)
    validate_final_payload(payload)
    validate_supported_mutations(payload)
    _require(manifest.get("release_commit") == payload["metadata"]["repository_commit"], "MANIFEST_RELEASE_BINDING_MISMATCH")
    _require(manifest.get("payload_id") == payload.get("payload_id"), "MANIFEST_PAYLOAD_ID_MISMATCH")
    _require(manifest.get("payload_sha256") == payload.get("payload_hash"), "MANIFEST_PAYLOAD_SHA_MISMATCH")
    _require((manifest.get("flags") or {}).get("production_apply_authorized") is False, "CANDIDATE_MANIFEST_EMBEDS_AUTHORIZATION")

    plan = _load_json(artifacts["production_apply_plan"])
    _require(plan.get("document_type") == PLAN_DOCUMENT_TYPE, "PRODUCTION_APPLY_PLAN_DOCUMENT_TYPE_MISMATCH")
    _require(plan.get("release_commit") == manifest.get("release_commit"), "PRODUCTION_APPLY_PLAN_RELEASE_MISMATCH")
    _require(plan.get("payload_id") == payload.get("payload_id"), "PRODUCTION_APPLY_PLAN_PAYLOAD_ID_MISMATCH")
    _require(plan.get("payload_sha256") == payload.get("payload_hash"), "PRODUCTION_APPLY_PLAN_PAYLOAD_SHA_MISMATCH")
    _require(plan.get("production_pre_sha256") == payload["metadata"]["production_sha256"], "PRODUCTION_APPLY_PLAN_BASELINE_MISMATCH")
    _require(plan.get("source_sha256") == payload["metadata"]["source_sha256"], "PRODUCTION_APPLY_PLAN_SOURCE_MISMATCH")
    _require(len(plan.get("steps") or []) == 14, "PRODUCTION_APPLY_PLAN_STEP_COUNT_MISMATCH")
    _require((plan.get("constraints") or {}).get("production_apply_authorized") is False, "PRODUCTION_APPLY_PLAN_EMBEDS_AUTHORIZATION")

    shadow_receipt = _load_json(artifacts["release_shadow_receipt"])
    receipt_release = shadow_receipt.get("release") or {}
    receipt_payload = shadow_receipt.get("payload") or {}
    _require(shadow_receipt.get("status") == "PASS", "RELEASE_SHADOW_RECEIPT_NOT_QUALIFIED")
    _require(receipt_release.get("commit") == manifest.get("release_commit"), "RELEASE_SHADOW_RECEIPT_RELEASE_MISMATCH")
    _require(receipt_payload.get("payload_id") == payload.get("payload_id"), "RELEASE_SHADOW_RECEIPT_PAYLOAD_ID_MISMATCH")
    _require(receipt_payload.get("payload_sha256") == payload.get("payload_hash"), "RELEASE_SHADOW_RECEIPT_PAYLOAD_SHA_MISMATCH")
    receipt_flags = shadow_receipt.get("flags") or {}
    _require(
        receipt_flags.get("release_shadow_preflight_pass") is True
        and receipt_flags.get("release_shadow_apply_pass") is True
        and receipt_flags.get("release_shadow_postflight_pass") is True,
        "RELEASE_SHADOW_RECEIPT_GATE_MISMATCH",
    )

    source_materialization = _load_json(artifacts["source_materialization"])
    materialization_source = source_materialization.get("source") or {}
    materialization_package = source_materialization.get("package") or {}
    _require(source_materialization.get("status") == "SOURCE_PACKAGE_FROZEN", "SOURCE_MATERIALIZATION_STATUS_MISMATCH")
    _require(materialization_source.get("source_id") == payload["metadata"]["source_id"], "SOURCE_MATERIALIZATION_ID_MISMATCH")
    _require(
        materialization_source.get("original_sha256")
        == materialization_package.get("sha256")
        == payload["metadata"]["source_sha256"],
        "SOURCE_MATERIALIZATION_SHA_MISMATCH",
    )
    _require((source_materialization.get("flags") or {}).get("production_apply_authorized") is False, "SOURCE_MATERIALIZATION_EMBEDS_AUTHORIZATION")

    source_path = artifacts["source_package"]
    _require(sha256_file(source_path) == payload["source_materialization"]["package_sha256"], "CANDIDATE_SOURCE_SHA_MISMATCH")
    return {
        "candidate_dir": candidate_dir,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "payload": payload,
        "payload_path": payload_path,
        "payload_file_sha256": sha256_file(payload_path),
        "plan": plan,
        "source_path": source_path,
        "artifacts": artifacts,
    }


def validate_execution_authorization(
    authorization: Mapping[str, Any],
    *,
    authorization_file_sha256: str,
    candidate: Mapping[str, Any],
    execution_commit: str,
    config: AppConfig,
    protected_real_production_path: Path,
) -> dict[str, Any]:
    payload = candidate["payload"]
    target_path = config.db_path.resolve()
    archive_root = config.root.resolve()
    protected_path = Path(protected_real_production_path).resolve()
    authorization_id = authorization.get("authorization_id")
    _require(authorization.get("document_type") == AUTHORIZATION_DOCUMENT_TYPE, "AUTHORIZATION_DOCUMENT_TYPE_MISMATCH")
    _require(authorization.get("authorization_version") == AUTHORIZATION_VERSION, "AUTHORIZATION_VERSION_MISMATCH")
    _require(isinstance(authorization_id, str) and re.fullmatch(r"[A-Za-z0-9_.-]{8,128}", authorization_id) is not None, "AUTHORIZATION_ID_INVALID")
    _require(authorization.get("authority") == AUTHORIZATION_AUTHORITY, "AUTHORIZATION_AUTHORITY_INVALID")
    _require(authorization.get("scope") == AUTHORIZATION_SCOPE, "AUTHORIZATION_SCOPE_INVALID")
    _require(authorization.get("status") == AUTHORIZATION_STATUS, "AUTHORIZATION_STATUS_INVALID")
    _require(authorization.get("authorization_consumed") is False, "AUTHORIZATION_ARTIFACT_ALREADY_CONSUMED")
    environment = authorization.get("authorization_environment")
    _require(environment in AUTHORIZATION_ENVIRONMENTS, "AUTHORIZATION_ENVIRONMENT_INVALID")

    _require(authorization.get("release_commit_sha") == execution_commit, "AUTHORIZATION_RELEASE_MISMATCH")
    _require(payload["metadata"]["repository_commit"] == execution_commit, "PAYLOAD_RELEASE_MISMATCH")
    _require(authorization.get("payload_id") == payload.get("payload_id"), "AUTHORIZATION_PAYLOAD_ID_MISMATCH")
    _require(authorization.get("payload_sha256") == payload.get("payload_hash"), "AUTHORIZATION_PAYLOAD_SHA_MISMATCH")
    _require(authorization.get("payload_file_sha256") == candidate["payload_file_sha256"], "AUTHORIZATION_PAYLOAD_FILE_SHA_MISMATCH")
    _require(authorization.get("candidate_manifest_sha256") == candidate["manifest_sha256"], "AUTHORIZATION_MANIFEST_SHA_MISMATCH")
    _require(authorization.get("expected_production_sha256") == payload["metadata"]["production_sha256"], "AUTHORIZATION_BASELINE_MISMATCH")
    _require(authorization.get("source_id") == payload["metadata"]["source_id"], "AUTHORIZATION_SOURCE_ID_MISMATCH")
    _require(authorization.get("source_sha256") == payload["metadata"]["source_sha256"], "AUTHORIZATION_SOURCE_SHA_MISMATCH")
    human = payload["human_authorization"]
    _require(authorization.get("human_review_id") == human["human_review_id"], "AUTHORIZATION_HUMAN_REVIEW_ID_MISMATCH")
    _require(authorization.get("human_review_sha256") == human["human_review_sha256"], "AUTHORIZATION_HUMAN_REVIEW_SHA_MISMATCH")
    _require(authorization.get("expected_operation_counts") == payload_operation_counts(payload), "AUTHORIZATION_OPERATION_COUNTS_MISMATCH")

    database_identity_binding = authorization.get("target_database_identity") or {}
    archive_identity_binding = authorization.get("target_archive_identity") or {}
    authorized_db = Path(str(database_identity_binding.get("resolved_path", ""))).resolve()
    authorized_archive = Path(str(archive_identity_binding.get("resolved_root", ""))).resolve()
    _require(_paths_equivalent(authorized_db, target_path), "AUTHORIZATION_TARGET_DATABASE_MISMATCH")
    _require(_paths_equivalent(authorized_archive, archive_root), "AUTHORIZATION_TARGET_ARCHIVE_MISMATCH")

    real_authorization = authorization.get("real_production_authorization")
    if environment == "QUALIFICATION":
        _require(real_authorization is False, "QUALIFICATION_AUTHORIZATION_MARKED_REAL")
        _require(not _paths_equivalent(target_path, protected_path), "QUALIFICATION_AUTHORIZATION_TARGETS_REAL_PRODUCTION")
    else:
        _require(real_authorization is True, "PRODUCTION_AUTHORIZATION_NOT_MARKED_REAL")
        _require(_paths_equivalent(target_path, protected_path), "PRODUCTION_AUTHORIZATION_TARGET_MISMATCH")

    return {
        "authorization_id": authorization_id,
        "authorization_file_sha256": authorization_file_sha256,
        "environment": environment,
        "real_production_authorization": real_authorization,
        "target_path": target_path,
        "archive_root": archive_root,
        "protected_real_production_path": protected_path,
    }


def _expected_post_counts(payload: Mapping[str, Any]) -> dict[str, int]:
    counts = copy.deepcopy(payload["metadata"]["production_counts"])
    for mutation in payload["intended_mutations"]:
        counts[mutation["table"]] += 1
    return counts


def _preflight(
    payload: Mapping[str, Any],
    *,
    target_path: Path,
    archive_root: Path,
    source_path: Path,
) -> dict[str, Any]:
    identity = production_identity(target_path)
    metadata = payload["metadata"]
    _require(identity["sha256"] == metadata["production_sha256"], "PRODUCTION_BASELINE_SHA_MISMATCH")
    _require(identity["schema_version"] == metadata["production_schema_version"], "PRODUCTION_SCHEMA_VERSION_MISMATCH")
    _require(identity["schema_sha256"] == metadata["production_schema_sha256"], "PRODUCTION_SCHEMA_SHA_MISMATCH")
    _require(identity["counts"] == metadata["production_counts"], "PRODUCTION_TABLE_COUNTS_MISMATCH")
    _require(identity["integrity"] == "ok" and not identity["foreign_key_violations"], "PRODUCTION_DATABASE_INVALID")
    _require(not any(identity["sidecars"].values()), "PRODUCTION_SQLITE_SIDECAR_PRESENT")
    _require(source_path.is_file(), "SOURCE_PACKAGE_MISSING")
    _require(source_path.stat().st_size == payload["source_materialization"]["size"], "SOURCE_PACKAGE_SIZE_MISMATCH")
    _require(sha256_file(source_path) == payload["source_materialization"]["package_sha256"], "SOURCE_PACKAGE_SHA_MISMATCH")
    relative = _safe_relative_path(payload["source_materialization"]["archive_logical_destination"])
    destination = (archive_root / relative).resolve()
    _require(_path_within(destination, archive_root / "archive"), "PRODUCTION_ARCHIVE_DESTINATION_ESCAPE")
    _require(not destination.exists(), "PRODUCTION_ARCHIVE_DESTINATION_EXISTS")
    collisions = list(destination.parent.glob(f"{metadata['source_id']}__*")) if destination.parent.exists() else []
    _require(not collisions, "PRODUCTION_ARCHIVE_SOURCE_ID_COLLISION")

    connection = connect_read_only(target_path)
    try:
        validate_executable_operations(connection, payload)
        source_count = connection.execute("SELECT COUNT(*) FROM sources WHERE source_id=?", (metadata["source_id"],)).fetchone()[0]
        source_sha_count = connection.execute("SELECT COUNT(*) FROM sources WHERE sha256=?", (metadata["source_sha256"],)).fetchone()[0]
        _require(source_count == source_sha_count == 0, "PRODUCTION_SOURCE_ALREADY_EXISTS")
        claim_ids = [item["row"]["claim_id"] for item in payload["intended_mutations"] if item["table"] == "claims"]
        if claim_ids:
            placeholders = ",".join("?" for _ in claim_ids)
            count = connection.execute(f"SELECT COUNT(*) FROM claims WHERE claim_id IN ({placeholders})", claim_ids).fetchone()[0]
            _require(count == 0, "PRODUCTION_CLAIM_ALREADY_EXISTS")
    finally:
        connection.close()
    return {"identity": identity, "archive_destination": destination, "archive_inventory": filesystem_inventory(archive_root / "archive")}


def _locked_revalidation(
    connection: sqlite3.Connection,
    payload: Mapping[str, Any],
    target_path: Path,
) -> None:
    metadata = payload["metadata"]
    _require(sha256_file(target_path) == metadata["production_sha256"], "LOCKED_BASELINE_SHA_MISMATCH")
    schema_version = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    _require(schema_version is not None and schema_version[0] == metadata["production_schema_version"], "LOCKED_SCHEMA_VERSION_MISMATCH")
    _require(schema_sha256(connection) == metadata["production_schema_sha256"], "LOCKED_SCHEMA_SHA_MISMATCH")
    _require(table_counts(connection) == metadata["production_counts"], "LOCKED_TABLE_COUNTS_MISMATCH")
    validate_executable_operations(connection, payload)
    source_count = connection.execute(
        "SELECT COUNT(*) FROM sources WHERE source_id=? OR sha256=?",
        (metadata["source_id"], metadata["source_sha256"]),
    ).fetchone()[0]
    _require(source_count == 0, "LOCKED_SOURCE_COLLISION")
    claim_ids = [item["row"]["claim_id"] for item in payload["intended_mutations"] if item["table"] == "claims"]
    if claim_ids:
        placeholders = ",".join("?" for _ in claim_ids)
        count = connection.execute(f"SELECT COUNT(*) FROM claims WHERE claim_id IN ({placeholders})", claim_ids).fetchone()[0]
        _require(count == 0, "LOCKED_CLAIM_COLLISION")


def _apply_database_transaction(
    payload: Mapping[str, Any],
    target_path: Path,
    *,
    inject_transaction_failure: bool = False,
) -> dict[str, Any]:
    allowed_tables = validate_supported_mutations(payload)
    connection = sqlite3.connect(target_path)
    connection.row_factory = sqlite3.Row
    committed = False
    changed: dict[str, dict[str, list[str]]] = {}
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        _locked_revalidation(connection, payload, target_path)
        before_rows = database_rows(connection)
        connection.set_authorizer(_write_authorizer(allowed_tables))
        try:
            for index, mutation in enumerate(payload["intended_mutations"], start=1):
                _insert_mutation(connection, mutation)
                if inject_transaction_failure and index == min(2, len(payload["intended_mutations"])):
                    raise ProductionExecutionError("INJECTED_PRODUCTION_TRANSACTION_FAILURE")
            foreign_keys = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            _require(not foreign_keys, "PRODUCTION_TRANSACTION_FOREIGN_KEY_FAILURE")
            _require(integrity == "ok", "PRODUCTION_TRANSACTION_INTEGRITY_FAILURE")
            after_rows = database_rows(connection)
            changed = _diff_rows(before_rows, after_rows)
            _require(set(changed) == allowed_tables, f"UNEXPECTED_PRODUCTION_TABLE_DELTA:{sorted(changed)}")
            expected_added: dict[str, set[str]] = {table: set() for table in allowed_tables}
            for mutation in payload["intended_mutations"]:
                expected_added[mutation["table"]].add(
                    json.dumps(mutation["row"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                )
            for table, delta in changed.items():
                _require(not delta["removed"], f"UNEXPECTED_PRODUCTION_ROW_REMOVAL:{table}")
                _require(set(delta["added"]) == expected_added[table], f"UNEXPECTED_PRODUCTION_ROW_DELTA:{table}")
            connection.set_authorizer(None)
            connection.commit()
            committed = True
        except Exception:
            connection.set_authorizer(None)
            connection.rollback()
            raise
    finally:
        if not committed:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
        connection.close()

    return {
        "status": "COMMITTED",
        "locked_revalidation_pass": True,
        "database_post_sha256": sha256_file(target_path),
        "changed_tables": {
            table: {"added": len(delta["added"]), "removed": len(delta["removed"])}
            for table, delta in changed.items()
        },
    }


def _materialize_source(
    source_path: Path,
    destination: Path,
    expected_sha256: str,
    authorization_id: str,
    *,
    inject_before_finalization: bool = False,
) -> tuple[Path, list[Path]]:
    _require(not destination.exists(), "PRODUCTION_ARCHIVE_DESTINATION_EXISTS")
    created_directories: list[Path] = []
    current = destination.parent
    while not current.exists():
        created_directories.append(current)
        current = current.parent
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging_token = hashlib.sha256(authorization_id.encode("utf-8")).hexdigest()[:16]
    staged = destination.parent / f".phase3d-source-{staging_token}.tmp"
    _require(not staged.exists(), "PRODUCTION_SOURCE_STAGING_CONFLICT")
    try:
        shutil.copy2(source_path, staged)
        _require(sha256_file(staged) == expected_sha256, "STAGED_SOURCE_SHA_MISMATCH")
        if inject_before_finalization:
            raise ProductionExecutionError("INJECTED_BEFORE_SOURCE_FINALIZATION")
        os.replace(staged, destination)
    except Exception:
        for directory in created_directories:
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    finally:
        if staged.exists():
            staged.unlink()
    _require(sha256_file(destination) == expected_sha256, "MATERIALIZED_SOURCE_SHA_MISMATCH")
    return destination, created_directories


def _remove_materialized_source(destination: Path, expected_sha256: str, created_directories: list[Path]) -> None:
    if destination.exists():
        _require(destination.is_file() and sha256_file(destination) == expected_sha256, "MATERIALIZED_SOURCE_CLEANUP_CONFLICT")
        destination.unlink()
    for directory in created_directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def _verify_postflight(
    payload: Mapping[str, Any],
    *,
    target_path: Path,
    archive_root: Path,
    archive_destination: Path,
    archive_inventory_pre: list[dict[str, Any]],
    changed_tables: Mapping[str, Any],
) -> dict[str, Any]:
    identity = production_identity(target_path)
    _require(identity["schema_version"] == payload["metadata"]["production_schema_version"], "POSTFLIGHT_SCHEMA_VERSION_MISMATCH")
    _require(identity["schema_sha256"] == payload["metadata"]["production_schema_sha256"], "POSTFLIGHT_SCHEMA_SHA_MISMATCH")
    _require(identity["counts"] == _expected_post_counts(payload), "POSTFLIGHT_TABLE_COUNTS_MISMATCH")
    _require(identity["integrity"] == "ok" and not identity["foreign_key_violations"], "POSTFLIGHT_DATABASE_INVALID")
    _require(not any(identity["sidecars"].values()), "POSTFLIGHT_SQLITE_SIDECAR_PRESENT")
    _require(archive_destination.is_file(), "POSTFLIGHT_SOURCE_ARCHIVE_MISSING")
    source_sha = payload["metadata"]["source_sha256"]
    _require(sha256_file(archive_destination) == source_sha, "POSTFLIGHT_SOURCE_ARCHIVE_SHA_MISMATCH")

    connection = connect_read_only(target_path)
    try:
        for mutation in payload["intended_mutations"]:
            actual = _row_for_key(connection, mutation["table"], mutation["key"])
            _require(actual is not None and _row_equal(actual, mutation["row"]), f"POSTFLIGHT_MUTATION_ROW_MISMATCH:{mutation['mutation_id']}")
        for operation in payload.get("node_operations") or []:
            if operation.get("operation") != "REUSE":
                continue
            expected = operation["expected_target"]
            actual = connection.execute(
                "SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE node_id=?",
                (operation["resolved_target_id"],),
            ).fetchall()
            _require(len(actual) == 1 and dict(actual[0]) == expected, f"POSTFLIGHT_REUSE_TARGET_DRIFT:{operation['resolved_target_id']}")
    finally:
        connection.close()

    archive_inventory_post = filesystem_inventory(archive_root / "archive")
    relative_archive_path = archive_destination.relative_to(archive_root / "archive").as_posix()
    expected_inventory = sorted(
        archive_inventory_pre + [{
            "path": relative_archive_path,
            "size": archive_destination.stat().st_size,
            "sha256": source_sha,
        }],
        key=lambda item: item["path"],
    )
    _require(archive_inventory_post == expected_inventory, "POSTFLIGHT_ARCHIVE_INVENTORY_MISMATCH")
    _require(set(changed_tables) == {item["table"] for item in payload["intended_mutations"]}, "POSTFLIGHT_CHANGED_TABLES_MISMATCH")
    return {"identity": identity, "archive_inventory": archive_inventory_post, "archive_sha256": source_sha}


def _restore_after_failure(
    *,
    target_path: Path,
    backup_path: Path,
    expected_pre_sha256: str,
    archive_destination: Path,
    source_sha256: str,
    created_directories: list[Path],
    archive_root: Path,
    archive_inventory_pre: list[dict[str, Any]],
    database_committed: bool,
    expected_database_post_sha256: str | None,
) -> dict[str, Any]:
    try:
        current_sha256 = sha256_file(target_path)
        if database_committed and current_sha256 != expected_pre_sha256:
            _require(
                expected_database_post_sha256 is not None
                and current_sha256 == expected_database_post_sha256,
                "PRODUCTION_CHANGED_AFTER_EXECUTOR_COMMIT",
            )
            _require(backup_path.is_file(), "PRODUCTION_BACKUP_MISSING_DURING_RESTORE")
            shutil.copyfile(backup_path, target_path)
        elif not database_committed:
            _require(current_sha256 == expected_pre_sha256, "PRODUCTION_CHANGED_OUTSIDE_EXECUTOR")
        _remove_materialized_source(archive_destination, source_sha256, created_directories)
        restored = production_identity(target_path)
        _require(restored["sha256"] == expected_pre_sha256, "RESTORED_PRODUCTION_SHA_MISMATCH")
        _require(restored["integrity"] == "ok" and not restored["foreign_key_violations"], "RESTORED_PRODUCTION_DATABASE_INVALID")
        _require(not any(restored["sidecars"].values()), "RESTORED_PRODUCTION_SQLITE_SIDECAR_PRESENT")
        _require(filesystem_inventory(archive_root / "archive") == archive_inventory_pre, "RESTORED_ARCHIVE_INVENTORY_MISMATCH")
        return {"status": "FAILED_RESTORED", "identity": restored}
    except Exception as exc:
        return {"status": "UNCERTAIN", "error": f"{type(exc).__name__}:{exc}"}


def execute_authorized_production(
    *,
    candidate_dir: Path,
    authorization_path: Path,
    config: AppConfig,
    execution_commit: str,
    protected_real_production_path: Path,
    failure_point: str | None = None,
) -> dict[str, Any]:
    """Execute one externally authorized payload against the configured target exactly once.

    ``failure_point`` exists only for direct test/qualification injection and is not
    exposed by the Production CLI.
    """
    _require(failure_point in {None, "before_source_finalization", "after_source_materialization", "during_db_transaction", "after_db_commit"}, "FAILURE_POINT_INVALID")
    candidate = validate_candidate_package(candidate_dir)
    authorization_path = Path(authorization_path).resolve()
    authorization = _load_json(authorization_path)
    authorization_file_sha256 = sha256_file(authorization_path)
    binding = validate_execution_authorization(
        authorization,
        authorization_file_sha256=authorization_file_sha256,
        candidate=candidate,
        execution_commit=execution_commit,
        config=config,
        protected_real_production_path=protected_real_production_path,
    )
    authorization_id = binding["authorization_id"]
    archive_root = binding["archive_root"]
    execution_root = (archive_root / EXECUTION_STATE_RELATIVE_ROOT).resolve()
    execution_dir = execution_root / authorization_id
    journal_path = execution_dir / "execution_journal.json"
    receipt_path = execution_dir / "phase3d_production_apply_receipt.json"
    backup_path = execution_dir / "backup" / "production_pre.db"
    payload = candidate["payload"]
    target_path = binding["target_path"]
    _require(not _path_within(execution_dir, archive_root / "archive"), "EXECUTION_ROOT_INSIDE_PRODUCTION_ARCHIVE")
    _require(not _paths_equivalent(backup_path, target_path), "PRODUCTION_BACKUP_TARGET_COLLISION")

    if journal_path.exists():
        journal = _load_json(journal_path)
        _require(journal.get("document_type") == JOURNAL_DOCUMENT_TYPE, "EXECUTION_JOURNAL_DOCUMENT_TYPE_MISMATCH")
        _require(journal.get("authorization_id") == authorization_id, "EXECUTION_JOURNAL_AUTHORIZATION_MISMATCH")
        _require(journal.get("authorization_file_sha256") == authorization_file_sha256, "EXECUTION_JOURNAL_AUTHORIZATION_FILE_MISMATCH")
        _require(journal.get("release_commit_sha") == execution_commit, "EXECUTION_JOURNAL_RELEASE_MISMATCH")
        _require(journal.get("payload_sha256") == payload["payload_hash"], "EXECUTION_JOURNAL_PAYLOAD_MISMATCH")
        _require(
            journal.get("production_pre_sha256") == payload["metadata"]["production_sha256"],
            "EXECUTION_JOURNAL_BASELINE_MISMATCH",
        )
        state = journal.get("state")
        if state == "COMPLETE":
            journal_receipt_path = Path(str(journal.get("receipt_path", ""))).resolve()
            _require(_paths_equivalent(journal_receipt_path, receipt_path), "EXECUTION_JOURNAL_RECEIPT_PATH_MISMATCH")
            _require(receipt_path.is_file(), "EXECUTION_RECEIPT_MISSING")
            _require(sha256_file(receipt_path) == journal.get("receipt_sha256"), "EXECUTION_RECEIPT_SHA_MISMATCH")
            completed_receipt = _load_json(receipt_path)
            _require(
                completed_receipt.get("document_type") == RECEIPT_DOCUMENT_TYPE
                and completed_receipt.get("status") == "COMPLETE"
                and (completed_receipt.get("authorization") or {}).get("authorization_id") == authorization_id,
                "EXECUTION_RECEIPT_BINDING_MISMATCH",
            )
            return {
                "status": "AUTHORIZATION_ALREADY_CONSUMED",
                "authorization_id": authorization_id,
                "journal_path": str(journal_path),
                "receipt_path": journal.get("receipt_path"),
                "production_apply_attempted": False,
            }
        if state in INCOMPLETE_STATES:
            raise ProductionExecutionError(f"INCOMPLETE_EXECUTION_REQUIRES_RECOVERY:{state}")
        if state == "FAILED_RESTORED":
            raise ProductionExecutionError("AUTHORIZATION_PREVIOUS_ATTEMPT_FAILED_RESTORED")
        if state == "UNCERTAIN":
            raise ProductionExecutionError("EXECUTION_STATE_UNCERTAIN")
        raise ProductionExecutionError(f"EXECUTION_JOURNAL_STATE_INVALID:{state}")
    _require(not execution_dir.exists(), "EXECUTION_DIRECTORY_CONFLICT")

    preflight = _preflight(
        payload,
        target_path=target_path,
        archive_root=archive_root,
        source_path=candidate["source_path"],
    )
    production_pre = preflight["identity"]
    archive_destination = preflight["archive_destination"]
    archive_inventory_pre = preflight["archive_inventory"]
    started_at = _now()

    backup_path.parent.mkdir(parents=True, exist_ok=False)
    _require(not backup_path.exists(), "PRODUCTION_BACKUP_ALREADY_EXISTS")
    shutil.copy2(target_path, backup_path)
    _require(sha256_file(backup_path) == production_pre["sha256"], "PRODUCTION_BACKUP_SHA_MISMATCH")
    backup_identity = production_identity(backup_path)
    _require(backup_identity["sha256"] == production_pre["sha256"], "PRODUCTION_BACKUP_IDENTITY_MISMATCH")

    journal: dict[str, Any] = {
        "document_type": JOURNAL_DOCUMENT_TYPE,
        "journal_version": "1",
        "authorization_id": authorization_id,
        "authorization_file_sha256": authorization_file_sha256,
        "authorization_environment": binding["environment"],
        "release_commit_sha": execution_commit,
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "production_pre_sha256": production_pre["sha256"],
        "target_database_path": str(target_path),
        "target_archive_root": str(archive_root),
        "backup_path": str(backup_path),
        "backup_sha256": backup_identity["sha256"],
        "archive_destination": str(archive_destination),
        "started_at": started_at,
        "updated_at": started_at,
        "state": "PREPARED",
        "transitions": [{"state": "PREPARED", "at": started_at}],
    }
    _write_json_atomic(journal_path, journal)

    created_directories: list[Path] = []
    database_committed = False
    expected_database_post_sha256: str | None = None
    try:
        _, created_directories = _materialize_source(
            candidate["source_path"],
            archive_destination,
            payload["metadata"]["source_sha256"],
            authorization_id,
            inject_before_finalization=failure_point == "before_source_finalization",
        )
        journal["state"] = "SOURCE_MATERIALIZED"
        journal["updated_at"] = _now()
        journal["created_archive_directories"] = [str(path) for path in created_directories]
        journal["transitions"].append({"state": "SOURCE_MATERIALIZED", "at": journal["updated_at"]})
        _write_json_atomic(journal_path, journal)
        if failure_point == "after_source_materialization":
            raise ProductionExecutionError("INJECTED_AFTER_SOURCE_MATERIALIZATION")

        database_result = _apply_database_transaction(
            payload,
            target_path,
            inject_transaction_failure=failure_point == "during_db_transaction",
        )
        database_committed = True
        expected_database_post_sha256 = database_result["database_post_sha256"]
        journal["state"] = "DB_COMMITTED"
        journal["updated_at"] = _now()
        journal["changed_tables"] = database_result["changed_tables"]
        journal["transitions"].append({"state": "DB_COMMITTED", "at": journal["updated_at"]})
        _write_json_atomic(journal_path, journal)
        if failure_point == "after_db_commit":
            raise ProductionExecutionError("INJECTED_AFTER_DB_COMMIT")

        postflight = _verify_postflight(
            payload,
            target_path=target_path,
            archive_root=archive_root,
            archive_destination=archive_destination,
            archive_inventory_pre=archive_inventory_pre,
            changed_tables=database_result["changed_tables"],
        )
        production_post = postflight["identity"]
        completed_at = _now()
        create_identities = [
            {
                "node_id": item["final_node"]["node_id"],
                "canonical_name": item["final_node"]["canonical_name"],
                "primary_type": item["final_node"]["primary_type"],
                "aliases": item.get("aliases") or [],
            }
            for item in payload.get("node_operations") or []
            if item.get("operation") == "CREATE"
        ]
        reuse_targets = [
            {
                "node_id": item["resolved_target_id"],
                "canonical_name": item["expected_target"]["canonical_name"],
                "primary_type": item["expected_target"]["primary_type"],
            }
            for item in payload.get("node_operations") or []
            if item.get("operation") == "REUSE"
        ]
        receipt = {
            "document_type": RECEIPT_DOCUMENT_TYPE,
            "receipt_version": "1",
            "status": "COMPLETE",
            "authorization": {
                "authorization_id": authorization_id,
                "authority": authorization["authority"],
                "scope": authorization["scope"],
                "environment": binding["environment"],
                "real_production_authorization": binding["real_production_authorization"],
                "artifact_sha256": authorization_file_sha256,
            },
            "release_commit_sha": execution_commit,
            "payload": {
                "payload_id": payload["payload_id"],
                "payload_sha256": payload["payload_hash"],
                "payload_file_sha256": candidate["payload_file_sha256"],
                "candidate_manifest_sha256": candidate["manifest_sha256"],
            },
            "source": {
                "source_id": payload["metadata"]["source_id"],
                "source_sha256": payload["metadata"]["source_sha256"],
                "archive_destination": str(archive_destination),
                "archive_sha256": postflight["archive_sha256"],
            },
            "human_review": {
                "human_review_id": payload["human_authorization"]["human_review_id"],
                "human_review_sha256": payload["human_authorization"]["human_review_sha256"],
            },
            "production": {
                "pre_sha256": production_pre["sha256"],
                "post_sha256": production_post["sha256"],
                "schema_version": production_post["schema_version"],
                "schema_sha256": production_post["schema_sha256"],
                "counts_pre": production_pre["counts"],
                "counts_post": production_post["counts"],
                "changed_tables": database_result["changed_tables"],
                "integrity": production_post["integrity"],
                "foreign_key_violations": production_post["foreign_key_violations"],
                "sidecars": production_post["sidecars"],
            },
            "backup": {"path": str(backup_path), "sha256": backup_identity["sha256"], "retained": True},
            "operation_counts": payload_operation_counts(payload),
            "create_identities": create_identities,
            "reuse_targets": reuse_targets,
            "apply_started_at": started_at,
            "apply_completed_at": completed_at,
            "locked_revalidation_pass": database_result["locked_revalidation_pass"],
            "authorization_consumed": True,
        }
        _write_json_atomic(receipt_path, receipt, immutable=True)
        receipt_sha256 = sha256_file(receipt_path)
        journal["state"] = "COMPLETE"
        journal["updated_at"] = completed_at
        journal["receipt_path"] = str(receipt_path)
        journal["receipt_sha256"] = receipt_sha256
        journal["production_post_sha256"] = production_post["sha256"]
        journal["transitions"].append({"state": "COMPLETE", "at": completed_at})
        _write_json_atomic(journal_path, journal)
        return {
            "status": "COMPLETE",
            "authorization_id": authorization_id,
            "journal_path": str(journal_path),
            "receipt_path": str(receipt_path),
            "receipt_sha256": receipt_sha256,
            "backup_path": str(backup_path),
            "backup_sha256": backup_identity["sha256"],
            "production_pre_sha256": production_pre["sha256"],
            "production_post_sha256": production_post["sha256"],
            "changed_tables": database_result["changed_tables"],
            "archive_destination": str(archive_destination),
            "archive_sha256": postflight["archive_sha256"],
            "locked_revalidation_pass": True,
            "production_apply_attempted": True,
        }
    except Exception as exc:
        restoration = _restore_after_failure(
            target_path=target_path,
            backup_path=backup_path,
            expected_pre_sha256=production_pre["sha256"],
            archive_destination=archive_destination,
            source_sha256=payload["metadata"]["source_sha256"],
            created_directories=created_directories,
            archive_root=archive_root,
            archive_inventory_pre=archive_inventory_pre,
            database_committed=database_committed,
            expected_database_post_sha256=expected_database_post_sha256,
        )
        journal["state"] = restoration["status"]
        journal["updated_at"] = _now()
        journal["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        journal["restoration"] = {key: value for key, value in restoration.items() if key != "identity"}
        journal["transitions"].append({"state": restoration["status"], "at": journal["updated_at"]})
        _write_json_atomic(journal_path, journal)
        if restoration["status"] == "UNCERTAIN":
            raise ProductionExecutionError(f"PRODUCTION_STATE_UNCERTAIN:{restoration.get('error')}") from exc
        raise
