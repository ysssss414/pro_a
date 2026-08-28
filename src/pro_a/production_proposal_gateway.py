"""Explicit configured-Production gateway. The only business write is INSERT proposals."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .db import Database, now_iso
from .human_review_intake import (
    HumanReviewIntakeError, _canonical_state, _find_pending_submission,
    _persist_submission, _prepared, _require, _validate_submission,
)
from .query import ReadOnlyQuery
from .storage import sha256_file, write_json


def proposal_write_authorizer(action, first, second, database, trigger):
    if action == sqlite3.SQLITE_INSERT:
        return sqlite3.SQLITE_OK if first == "proposals" and database == "main" and trigger is None else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA:
        return sqlite3.SQLITE_OK if first in {"integrity_check", "foreign_key_check"} and second is None else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION and second == "load_extension":
        return sqlite3.SQLITE_DENY
    if action in {sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                  sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_RECURSIVE}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _no_change(conn: sqlite3.Connection, artifact: dict) -> dict | None:
    if not isinstance(artifact, dict) or artifact.get("document_type") != "human_review_intake_receipt":
        return None
    review = artifact.get("human_review_handoff")
    _, view, _ = _canonical_state(conn, review)
    _require(review["decision"] == "no_change" and artifact == _prepared(review, view),
             "INVALID_ARTIFACT", "expected exact NO_CHANGE receipt")
    return {"status": "INTAKE_VALID", "action": "NO_PROPOSAL", "created": False}


def preview_production(draft: dict[str, Any]) -> dict[str, Any]:
    """Read-only preview of the current config.toml DB; never create backups/receipts."""
    with ReadOnlyQuery(load_config().db_path).connect() as conn:
        conn.execute("BEGIN")
        noop = _no_change(conn, draft)
        if noop:
            return noop
        payload = _validate_submission(conn, draft)
        existing_id = _find_pending_submission(conn, payload)
        return {"status": "PREVIEW_VALID", "action": "PENDING_PROPOSAL",
                "would_create": existing_id is None, "proposal_id": existing_id,
                "node_id": payload["node_id"], "previous_view_id": payload["previous_view_id"],
                "previous_version": payload["previous_version"], "decision": payload["change_level"]}


def _integrity(conn: sqlite3.Connection) -> dict[str, Any]:
    integrity = [r[0] for r in conn.execute("PRAGMA integrity_check")]
    foreign_keys = [list(r) for r in conn.execute("PRAGMA foreign_key_check")]
    _require(integrity == ["ok"] and not foreign_keys,
             "DATABASE_INTEGRITY_FAILED", "integrity or foreign-key check failed")
    return {"integrity_check": "ok", "foreign_key_check": foreign_keys}


def _backup(db_path: Path, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb"):
        pass
    # Use a separate reader: backing up the caller's active write transaction can deadlock.
    # BEGIN IMMEDIATE on the caller prevents another writer before this snapshot/INSERT.
    with ReadOnlyQuery(db_path).connect() as source:
        with sqlite3.connect(path) as destination:
            source.backup(destination)
            _integrity(destination)


def apply_production(draft: dict[str, Any]) -> dict[str, Any]:
    """Explicit authority, no caller-supplied DB path or isolated/Production boolean."""
    cfg = load_config()
    path = cfg.db_path.resolve(strict=True)
    db = Database(path)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = cfg.root / "backups" / f"pro_a_pre_phase2_7b_{stamp}.db"
    receipt_path = cfg.root / "generated" / "receipts" / f"phase2_7b_{stamp}.json"
    with db.transaction(immediate=True) as conn:
        conn.set_authorizer(proposal_write_authorizer)
        noop = _no_change(conn, draft)
        if noop:
            return noop
        payload = _validate_submission(conn, draft)
        existing_id = _find_pending_submission(conn, payload)
        _integrity(conn)
        pre_sha = sha256_file(path)
        if not existing_id:
            _backup(path, backup_path)
        result = _persist_submission(db, conn, payload)
        checks = _integrity(conn)
    receipt = {
        "timestamp": now_iso(), "database_identity": "configured_production",
        "production_db_path": str(path), "pre_write_sha256": pre_sha,
        "backup_location": str(backup_path) if not existing_id else "",
        **result, "target_node_id": payload["node_id"],
        "target_view_id": payload["previous_view_id"], "target_view_version": payload["previous_version"],
        "decision": payload["change_level"], "trigger_source_id": payload["trigger_source_id"],
        "evidence_claim_ids": payload["evidence_claim_ids"],
        **checks, "receipt_path": str(receipt_path),
    }
    try:
        receipt["post_write_sha256"] = sha256_file(path)
        write_json(receipt_path, receipt)
    except OSError as exc:
        raise HumanReviewIntakeError(
            "PROPOSAL_COMMITTED_RECEIPT_FAILED",
            f"Proposal {result['proposal_id']} is pending; backup={receipt['backup_location']}; {exc}",
        ) from exc
    return receipt
