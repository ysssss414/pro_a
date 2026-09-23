"""Schema 11 lifecycle closure registry and explicit offline apply path."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pro_a.production_promotion import sha256_file
from pro_a.stage6_lifecycle import (
    CAPACITY_POLICY_VERSION, CONTRACT_VERSION, POPULATION_SHA256, PRODUCTION_SHA256,
    SOURCE_PACKET_SHA256, validate_closure,
)
from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


def _canonical(value: Any) -> bytes:
    return (json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) + "\n").encode("utf-8")


def _write_once(path: Path, content: bytes, code: str) -> None:
    path = checked_path(path, missing=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise BoundaryError(code)
        return
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _require_offline(path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        if path.with_name(path.name + suffix).exists():
            raise BoundaryError("STAGE6_LIFECYCLE_REQUIRES_OFFLINE")


def _require_drain(connection) -> None:
    active_job = connection.execute(
        "SELECT 1 FROM cloud_jobs WHERE state IN ('QUEUED','RUNNING') LIMIT 1"
    ).fetchone()
    active_run = connection.execute(
        """SELECT 1 FROM source_processing_runs
           WHERE state NOT IN ('HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED','RECOVERY_REQUIRED')
           LIMIT 1"""
    ).fetchone()
    if active_job or active_run:
        raise BoundaryError("STAGE6_LIFECYCLE_REQUIRES_DRAIN")


def prepare_stage6_lifecycle(config) -> dict[str, Any]:
    """Explicit offline Workbench v10 -> v11 migration."""
    config.validate()
    path = checked_path(config.state_db)
    _require_offline(path)
    backup = path.with_name(path.name + ".stage43-stage6-backup")
    receipt_path = path.with_name(path.name + ".stage43-stage6-migration.json")
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version == "11":
            return {"status": "ALREADY_PREPARED", "schema_version": "11"}
        if version != "10":
            raise BoundaryError("STAGE1_SCHEMA_REQUIRED")
        _require_drain(connection)
    before = path.read_bytes()
    _write_once(backup, before, "STAGE6_MIGRATION_BACKUP_CONFLICT")
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN EXCLUSIVE")
        if schema_version(connection) != "10":
            raise BoundaryError("WORKBENCH_SCHEMA_CHANGED")
        _require_drain(connection)
        connection.execute("""CREATE TABLE lifecycle_closure_meta(
            closure_id TEXT PRIMARY KEY,
            contract_version TEXT NOT NULL,
            capacity_policy_version TEXT NOT NULL,
            population_sha256 TEXT NOT NULL,
            source_packet_immutable_sha256 TEXT NOT NULL,
            closure_sha256 TEXT NOT NULL UNIQUE,
            closure_file_sha256 TEXT NOT NULL,
            artifact_id TEXT REFERENCES registered_packets(artifact_id),
            summary_json TEXT NOT NULL,
            authority_json TEXT NOT NULL,
            human_resolved_rows INTEGER NOT NULL CHECK(human_resolved_rows>=0),
            ai_policy_resolved_rows INTEGER NOT NULL CHECK(ai_policy_resolved_rows>=0),
            total_rows INTEGER NOT NULL CHECK(total_rows>=0),
            created_at TEXT NOT NULL
        )""")
        connection.execute("""CREATE TABLE lifecycle_resolutions(
            closure_id TEXT NOT NULL REFERENCES lifecycle_closure_meta(closure_id),
            candidate_id TEXT NOT NULL,
            candidate_type TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            resolution_source TEXT NOT NULL CHECK(resolution_source IN (
                'HUMAN_USER_QUALIFICATION','AI_POLICY_QUALIFICATION')),
            native_decision TEXT NOT NULL,
            native_target_id TEXT,
            authorized_decision TEXT,
            followup_required INTEGER NOT NULL CHECK(followup_required IN (0,1)),
            closure_reason TEXT NOT NULL,
            resolution_sha256 TEXT NOT NULL UNIQUE,
            authority_json TEXT NOT NULL,
            artifact_id TEXT REFERENCES registered_packets(artifact_id),
            PRIMARY KEY(closure_id,candidate_id)
        )""")
        connection.execute("""CREATE INDEX lifecycle_resolution_artifact
            ON lifecycle_resolutions(artifact_id,candidate_id,resolution_source)""")
        connection.execute("""CREATE INDEX lifecycle_resolution_queue
            ON lifecycle_resolutions(resolution_source,followup_required,candidate_id)""")
        for table in ("lifecycle_closure_meta", "lifecycle_resolutions"):
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"CREATE TRIGGER {table}_{action.lower()}_forbidden "
                    f"BEFORE {action} ON {table} BEGIN "
                    "SELECT RAISE(ABORT,'IMMUTABLE_LIFECYCLE_CLOSURE'); END"
                )
        connection.execute("UPDATE workbench_meta SET value='11' WHERE key='schema_version'")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise BoundaryError("STAGE6_MIGRATION_FOREIGN_KEYS")
    receipt = {
        "document_type": "phase43_stage6_workbench_migration_receipt",
        "status": "STAGE6_LIFECYCLE_SCHEMA_PREPARED",
        "schema_version": "11",
        "contract_version": CONTRACT_VERSION,
        "capacity_policy_version": CAPACITY_POLICY_VERSION,
        "backup_sha256": hashlib.sha256(before).hexdigest(),
        "migrated_sha256": sha256_file(path),
        "canonical_db_write": False,
    }
    _write_once(receipt_path, _canonical(receipt), "STAGE6_MIGRATION_RECEIPT_CONFLICT")
    return receipt


def _packet_candidate_ids(packet: dict[str, Any]) -> set[str]:
    if isinstance(packet.get("objects"), dict):
        return {
            str(row["candidate_id"])
            for rows in packet["objects"].values()
            for row in rows
        }
    return {
        str(row["candidate_id"])
        for group in ("claims", "nodes", "relations")
        for row in packet.get(group, [])
    }


def _matching_artifact(config, candidate_ids: set[str]) -> str | None:
    from .artifacts import Artifacts

    artifacts = Artifacts(config)
    with Store(config).connect() as connection:
        ids = [row[0] for row in connection.execute(
            """SELECT artifact_id FROM registered_packets
               WHERE COALESCE(artifact_kind,'REVIEW_PACKET')='REVIEW_PACKET'
               ORDER BY registered_at,artifact_id"""
        )]
    matches: list[str] = []
    for artifact_id in ids:
        packet, _run, dto = artifacts.native(artifact_id)
        immutable = str(dto.get("immutable_packet_sha256") or
                        packet.get("immutable_packet_sha256") or "")
        if immutable == SOURCE_PACKET_SHA256:
            if _packet_candidate_ids(packet) != candidate_ids:
                raise BoundaryError("LIFECYCLE_PACKET_CANDIDATE_MISMATCH")
            matches.append(artifact_id)
    if len(matches) > 1:
        raise BoundaryError("LIFECYCLE_PACKET_BINDING_AMBIGUOUS")
    return matches[0] if matches else None


def apply_lifecycle_closure(config, closure_path: Path, *,
                            expected_production_sha256: str = PRODUCTION_SHA256) -> dict[str, Any]:
    """Register one validated closure. Reapplication is idempotent; conflict is fatal."""
    config.validate()
    closure_path = checked_path(closure_path)
    _require_offline(checked_path(config.state_db))
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    validated = validate_closure(closure)
    if expected_production_sha256 != PRODUCTION_SHA256:
        raise BoundaryError("LIFECYCLE_PRODUCTION_AUTHORITY_MISMATCH")
    if sha256_file(config.knowledge_db) != expected_production_sha256:
        raise BoundaryError("PRODUCTION_SHA_MISMATCH")
    rows = closure["resolutions"]
    candidate_ids = {str(row["candidate_id"]) for row in rows}
    artifact_id = _matching_artifact(config, candidate_ids)
    closure_file_sha256 = sha256_file(closure_path)
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        if schema_version(connection) != "11":
            raise BoundaryError("STAGE6_LIFECYCLE_SCHEMA_REQUIRED")
        _require_drain(connection)
        prior = connection.execute(
            "SELECT * FROM lifecycle_closure_meta WHERE closure_id=?", (closure["closure_id"],)
        ).fetchone()
        if prior:
            count = connection.execute(
                "SELECT COUNT(*) FROM lifecycle_resolutions WHERE closure_id=?",
                (closure["closure_id"],),
            ).fetchone()[0]
            if (prior["closure_sha256"] != closure["closure_sha256"] or
                    prior["closure_file_sha256"] != closure_file_sha256 or count != 274):
                raise BoundaryError("LIFECYCLE_CLOSURE_CONFLICT")
            return {
                "status": "ALREADY_APPLIED", **validated,
                "artifact_id": prior["artifact_id"], "production_authorized": False,
            }
        connection.execute(
            """INSERT INTO lifecycle_closure_meta(
               closure_id,contract_version,capacity_policy_version,population_sha256,
               source_packet_immutable_sha256,closure_sha256,closure_file_sha256,artifact_id,
               summary_json,authority_json,human_resolved_rows,ai_policy_resolved_rows,
               total_rows,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                closure["closure_id"], closure["contract_version"],
                closure["capacity_policy_version"], POPULATION_SHA256,
                SOURCE_PACKET_SHA256, closure["closure_sha256"], closure_file_sha256,
                artifact_id, json.dumps(closure["summary"], sort_keys=True),
                json.dumps(closure["authority"], sort_keys=True),
                closure["summary"]["human_user_qualified"],
                closure["summary"]["ai_policy_closed"],
                closure["summary"]["historical_lifecycle_closed"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        for row in rows:
            authority = {
                "human_authorization_id": row["human_authorization_id"],
                "human_item_attribution": row["human_item_attribution"],
                "ai_policy_attribution": row["ai_policy_attribution"],
                "mandatory_human": row["mandatory_human"],
                "residual_sample": row["residual_sample"],
            }
            connection.execute(
                """INSERT INTO lifecycle_resolutions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["closure_id"], row["candidate_id"], row["candidate_type"],
                    row["content_sha256"], row["resolution_source"], row["native_decision"],
                    row["native_target_id"], row["authorized_decision"],
                    int(row["followup_required"]), row["closure_reason"],
                    row["resolution_sha256"], json.dumps(authority, sort_keys=True), artifact_id,
                ),
            )
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise BoundaryError("LIFECYCLE_APPLY_FOREIGN_KEYS")
    return {
        "status": "LIFECYCLE_CLOSURE_APPLIED", **validated,
        "artifact_id": artifact_id, "closure_file_sha256": closure_file_sha256,
        "production_authorized": False,
    }


def lifecycle_status(config) -> dict[str, Any]:
    """Read lifecycle closure registration and capacity without changing state."""
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version != "11":
            return {"enabled": False, "schema_version": version, "closures": []}
        closures = []
        for row in connection.execute(
            "SELECT * FROM lifecycle_closure_meta ORDER BY closure_id"
        ):
            counts = dict(connection.execute(
                """SELECT resolution_source,COUNT(*) FROM lifecycle_resolutions
                   WHERE closure_id=? GROUP BY resolution_source""", (row["closure_id"],)
            ))
            followup = connection.execute(
                """SELECT COUNT(*) FROM lifecycle_resolutions
                   WHERE closure_id=? AND followup_required=1""", (row["closure_id"],)
            ).fetchone()[0]
            closures.append({
                "closure_id": row["closure_id"], "closure_sha256": row["closure_sha256"],
                "population_sha256": row["population_sha256"], "artifact_id": row["artifact_id"],
                "historical_lifecycle_closed": sum(counts.values()),
                "human_user_qualified": counts.get("HUMAN_USER_QUALIFICATION", 0),
                "ai_policy_closed": counts.get("AI_POLICY_QUALIFICATION", 0),
                "followup_governance": followup, "production_authorized": False,
            })
        from .stage1_scale import stage1_capacity
        return {"enabled": True, "schema_version": "11", "closures": closures,
                "capacity": stage1_capacity(connection)}


def closure_for_artifact(connection, artifact_id: str) -> dict[str, Any] | None:
    """Return only a closure bound to this validated registered artifact."""
    if schema_version(connection) != "11":
        return None
    meta = connection.execute(
        "SELECT * FROM lifecycle_closure_meta WHERE artifact_id=?", (artifact_id,)
    ).fetchone()
    if meta is None:
        return None
    counts = dict(connection.execute(
        """SELECT resolution_source,COUNT(*) FROM lifecycle_resolutions
           WHERE closure_id=? GROUP BY resolution_source""", (meta["closure_id"],)
    ))
    followup = int(connection.execute(
        """SELECT COUNT(*) FROM lifecycle_resolutions
           WHERE closure_id=? AND followup_required=1""", (meta["closure_id"],)
    ).fetchone()[0])
    return {
        "closure_id": meta["closure_id"], "closure_sha256": meta["closure_sha256"],
        "lifecycle_closed": sum(counts.values()),
        "human_user_qualified": counts.get("HUMAN_USER_QUALIFICATION", 0),
        "ai_policy_closed": counts.get("AI_POLICY_QUALIFICATION", 0),
        "followup_governance": followup,
        "message": "Historical lifecycle closure is registered; Workbench review completion is not inferred from this total.",
        "production_authorized": False,
    }


def apply_stage6_plan(config, closure_path: Path, *, expected_workbench_sha256: str,
                      expected_production_sha256: str, receipt_path: Path) -> dict[str, Any]:
    """Back up exact v8 input, run the 8->9->10->11 chain, and register closure."""
    config.validate()
    path = checked_path(config.state_db)
    _require_offline(path)
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version == "11":
            applied = apply_lifecycle_closure(
                config, closure_path,
                expected_production_sha256=expected_production_sha256,
            )
            return {"status": applied["status"], "schema_version": "11", "apply": applied}
        _require_drain(connection)
    before = path.read_bytes()
    before_sha = hashlib.sha256(before).hexdigest()
    if before_sha != expected_workbench_sha256:
        raise BoundaryError("WORKBENCH_SHA_MISMATCH")
    if sha256_file(config.knowledge_db) != expected_production_sha256:
        raise BoundaryError("PRODUCTION_SHA_MISMATCH")
    backup = path.with_name(path.name + ".stage43-stage6-apply-backup")
    _write_once(backup, before, "STAGE6_APPLY_BACKUP_CONFLICT")
    from .domains import prepare_domains
    from .stage1_scale import prepare_stage1_scale
    migrations = [prepare_domains(config), prepare_stage1_scale(config), prepare_stage6_lifecycle(config)]
    applied = apply_lifecycle_closure(
        config, closure_path, expected_production_sha256=expected_production_sha256,
    )
    post_sha = sha256_file(path)
    from .stage1_scale import stage1_capacity
    with Store(config).connect() as connection:
        capacity = stage1_capacity(connection)
    receipt = {
        "document_type": "phase43_stage6_lifecycle_apply_receipt",
        "status": "STAGE6_LIFECYCLE_APPLIED",
        "schema_before": version,
        "schema_after": "11",
        "workbench_sha256_before": before_sha,
        "exact_backup_sha256": sha256_file(backup),
        "workbench_sha256_after": post_sha,
        "production_sha256_before": expected_production_sha256,
        "production_sha256_after": sha256_file(config.knowledge_db),
        "migration_statuses": [item["status"] for item in migrations],
        "closure_id": applied["closure_id"],
        "closure_sha256": applied["closure_sha256"],
        "artifact_id": applied["artifact_id"],
        "native_pending_review_rows": capacity["native_pending_review_rows"],
        "lifecycle_resolved_rows": capacity["lifecycle_resolved_rows"],
        "operational_pending_review_rows": capacity["operational_pending_review_rows"],
        "wip_state": capacity["wip_state"],
        "new_intake_allowed": capacity["new_intake_allowed"],
        "production_write_count": 0,
        "production_authorized": False,
    }
    _write_once(receipt_path, _canonical(receipt), "STAGE6_APPLY_RECEIPT_CONFLICT")
    return receipt
