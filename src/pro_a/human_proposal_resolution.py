"""Human artifact resolution: direct SQLite View activation, without runtime managers."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .current_view import create_official_view_record
from .db import Database, now_iso
from .human_review_intake import (
    HumanReviewIntakeError, _canonical_state, _object, _require, _string, _validate_content,
)
from .production_proposal_gateway import _backup, _integrity
from .query import ReadOnlyQuery
from .storage import sha256_file, write_json
from .view_proposal_review import _human_payload, proposal_snapshot


RESOLUTION_FIELDS = {"document_type", "schema_version", "status", "proposal_id", "action", "reason", "proposal_snapshot"}
TERMINAL_STATUS = {"ACCEPT": "accepted", "REJECT": "rejected"}


def _exact(left: Any, right: Any) -> bool:
    # Object key order is immaterial; strings, arrays and JSON value types stay exact.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def validate_resolution(artifact: dict) -> None:
    _object(artifact, RESOLUTION_FIELDS, "human_view_proposal_resolution")
    for key, value in (("document_type", "human_view_proposal_resolution"), ("schema_version", "1"), ("status", "READY")):
        _require(artifact[key] == value, "INVALID_ARTIFACT", f"{key} must be {value}")
    for key in ("proposal_id", "action", "reason"):
        _string(artifact[key], key)
    _require(artifact["action"] in TERMINAL_STATUS, "INVALID_ARTIFACT", "action must be ACCEPT or REJECT")
    snapshot = artifact["proposal_snapshot"]
    _object(snapshot, {"proposal_type", "target_node_id", "created_at", "payload"}, "proposal_snapshot")
    for key in ("proposal_type", "target_node_id", "created_at"):
        _string(snapshot[key], key)
    _require(snapshot["proposal_type"] == "current_view_change" and isinstance(snapshot["payload"], dict),
             "INVALID_ARTIFACT", "expected a current_view_change payload")
    try:
        json.dumps(artifact, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HumanReviewIntakeError("INVALID_ARTIFACT", "resolution must be finite JSON") from exc


def resolution_result(conn: sqlite3.Connection, row: sqlite3.Row, payload: dict) -> dict | None:
    """Verify stored terminal provenance; never expose arbitrary legacy result fields."""
    try:
        result = json.loads(row["result_json"])
        human = result["human_resolution"]
        artifact = {k: v for k, v in human.items() if k != "resolved_at"}
        validate_resolution(artifact)
        if (artifact["proposal_id"] != row["proposal_id"] or not row["resolved_at"]
                or human.get("resolved_at") != row["resolved_at"]
                or row["status"] != TERMINAL_STATUS[artifact["action"]]
                or not _exact(artifact["proposal_snapshot"], proposal_snapshot(row, payload))):
            return None
        expected = {"activation_scope": "NO_VIEW_CREATED", "human_resolution": human}
        if artifact["action"] == "ACCEPT":
            view = conn.execute("SELECT * FROM current_views WHERE view_id=?", (result.get("view_id"),)).fetchone()
            if (view is None or view["status"] != "official" or view["node_id"] != row["target_node_id"]
                    or view["accepted_proposal_id"] != row["proposal_id"] or view["version"] != result.get("version")
                    or view["previous_view_id"] != payload["previous_view_id"]
                    or view["trigger_source_id"] != payload["trigger_source_id"]
                    or view["change_level"] != payload["change_level"]
                    or not _exact(json.loads(view["content_json"]), payload["proposed_current_view"])
                    or not _exact(json.loads(view["trigger_claim_ids_json"]), payload["evidence_claim_ids"])):
                return None
            expected.update(view_id=view["view_id"], version=view["version"], propagation_batch_id="",
                            activation_scope="DIRECT_VIEW_ONLY")
        return result if _exact(result, expected) else None
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


def resolution_write_authorizer(accept: bool):
    def authorize(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_INSERT:
            return sqlite3.SQLITE_OK if accept and first == "current_views" and database == "main" and trigger is None else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_UPDATE:
            allowed = first == "proposals" and second in {"status", "result_json", "resolved_at"}
            return sqlite3.SQLITE_OK if allowed and database == "main" and trigger is None else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA:
            return sqlite3.SQLITE_OK if first in {"integrity_check", "foreign_key_check"} and second is None else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION and second == "load_extension":
            return sqlite3.SQLITE_DENY
        if action in {sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                      sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_RECURSIVE}:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return authorize


def _checked(conn: sqlite3.Connection, artifact: dict) -> tuple[sqlite3.Row, dict, dict | None]:
    validate_resolution(artifact)
    row = conn.execute("SELECT * FROM proposals WHERE proposal_id=?", (artifact["proposal_id"],)).fetchone()
    _require(row is not None, "PROPOSAL_NOT_FOUND", artifact["proposal_id"])
    payload = _human_payload(row)
    _require(payload is not None, "NOT_HUMAN_VIEW_PROPOSAL", artifact["proposal_id"])
    _require(_exact(artifact["proposal_snapshot"], proposal_snapshot(row, payload)),
             "RESOLUTION_ARTIFACT_STALE", "exact Proposal snapshot changed")
    if row["status"] != "pending":
        result = resolution_result(conn, row, payload)
        _require(result is not None and _exact(result["human_resolution"], {**artifact, "resolved_at": row["resolved_at"]}),
                 "PROPOSAL_RESOLUTION_CONFLICT", "terminal Proposal has a different or invalid resolution")
        return row, payload, result
    _require(row["resolved_at"] in (None, "") and row["result_json"] == "{}",
             "PROPOSAL_RESOLUTION_CONFLICT", "pending Proposal already has resolution metadata")
    if artifact["action"] == "ACCEPT":
        try:
            node, view, claims = _canonical_state(conn, payload["human_review_handoff"])
            _validate_content(node, view, claims, payload)
        except HumanReviewIntakeError as exc:
            if exc.code == "INELIGIBLE_EVIDENCE":
                raise HumanReviewIntakeError("EVIDENCE_INELIGIBLE", str(exc)) from exc
            raise
    return row, payload, None


def _persist(conn, cfg, artifact: dict, payload: dict, existing: dict | None) -> dict:
    if existing is not None:
        return {"proposal_id": artifact["proposal_id"], "status": TERMINAL_STATUS[artifact["action"]],
                "resolved": False, "idempotent": True, "result": existing}
    ts = now_iso()
    result = {"activation_scope": "NO_VIEW_CREATED", "human_resolution": {**deepcopy(artifact), "resolved_at": ts}}
    if artifact["action"] == "ACCEPT":
        view = create_official_view_record(
            conn, cfg, payload["node_id"], payload["proposed_current_view"], payload["change_level"],
            payload["trigger_source_id"], payload["evidence_claim_ids"], accepted_proposal_id=artifact["proposal_id"],
        )
        result.update(view_id=view["view_id"], version=view["version"], propagation_batch_id="",
                      activation_scope="DIRECT_VIEW_ONLY")
    updated = conn.execute(
        "UPDATE proposals SET status=?,result_json=?,resolved_at=? WHERE proposal_id=? AND status='pending'",
        (TERMINAL_STATUS[artifact["action"]], json.dumps(result, ensure_ascii=False, allow_nan=False), ts, artifact["proposal_id"]),
    )
    _require(updated.rowcount == 1, "PROPOSAL_RESOLUTION_CONFLICT", "pending Proposal changed")
    return {"proposal_id": artifact["proposal_id"], "status": TERMINAL_STATUS[artifact["action"]],
            "resolved": True, "idempotent": False, "result": result}


def preview_resolution(artifact: dict) -> dict:
    with ReadOnlyQuery(load_config().db_path).connect() as conn:
        conn.execute("BEGIN")
        row, _, existing = _checked(conn, artifact)
        return {"status": "PREVIEW_VALID", "proposal_id": row["proposal_id"], "action": artifact["action"],
                "would_resolve": existing is None, "idempotent": existing is not None, "result": existing}


def resolve_isolated(db_path: str | Path, artifact: dict) -> dict:
    path = Path(db_path).resolve(strict=True)
    cfg = load_config()
    production = cfg.db_path.resolve()
    _require(path != production and not (production.exists() and path.samefile(production)),
             "PRODUCTION_WRITE_NOT_AUTHORIZED", "isolated resolution cannot target configured Production")
    cfg = replace(cfg, workspace=replace(cfg.workspace, root=path.parent))
    with Database(path).transaction(immediate=True) as conn:
        validate_resolution(artifact)
        conn.set_authorizer(resolution_write_authorizer(artifact["action"] == "ACCEPT"))
        _, payload, existing = _checked(conn, artifact)
        return _persist(conn, cfg, artifact, payload, existing)


def resolve_production(artifact: dict) -> dict:
    cfg = load_config()
    path = cfg.db_path.resolve(strict=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = cfg.root / "backups" / f"pro_a_pre_phase2_7c_{stamp}.db"
    receipt_path = cfg.root / "generated" / "receipts" / f"phase2_7c_{stamp}.json"
    with Database(path).transaction(immediate=True) as conn:
        validate_resolution(artifact)
        conn.set_authorizer(resolution_write_authorizer(artifact["action"] == "ACCEPT"))
        _, payload, existing = _checked(conn, artifact)
        _integrity(conn)
        pre_sha = sha256_file(path)
        if existing is None:
            _backup(path, backup_path)
        outcome = _persist(conn, cfg, artifact, payload, existing)
        checks = _integrity(conn)
    receipt = {
        "timestamp": now_iso(), "database_identity": "configured_production", "production_db_path": str(path),
        "pre_write_sha256": pre_sha, "backup_location": str(backup_path) if existing is None else "",
        **outcome, "action": artifact["action"], "resolution_reason": artifact["reason"],
        "node_id": payload["node_id"], "previous_view_id": payload["previous_view_id"],
        "previous_version": payload["previous_version"], "new_view_id": outcome["result"].get("view_id", ""),
        "new_version": outcome["result"].get("version", ""), **checks, "receipt_path": str(receipt_path),
    }
    try:
        receipt["post_write_sha256"] = sha256_file(path)
        write_json(receipt_path, receipt)
    except OSError as exc:
        raise HumanReviewIntakeError("RESOLUTION_COMMITTED_RECEIPT_FAILED",
            f"proposal_id={artifact['proposal_id']}; action={artifact['action']}; backup={receipt['backup_location']}; {exc}") from exc
    return receipt
