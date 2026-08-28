"""Controlled file handoff: read-only PREPARE, isolated-DB pending-only SUBMIT."""

from __future__ import annotations

import json
import re
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import load_config
from .constants import CLAIM_NODE_ROLES
from .current_view_compare import (
    LIST_FIELDS,
    SCALAR_FIELDS,
    compare_view_content,
)
from .current_view_pilot import CurrentViewPilotError, _validate_frozen_content_contract
from .db import CURRENT_VIEW_ORDER, Database
from .query import ReadOnlyQuery


DECISIONS = {"no_change", "minor", "material", "thesis"}
# Fail closed for terminal/unknown statuses. No Evidence scoring or status mutation.
PRIMARY_STATUSES = {"current", "pending_verification", "disputed"}
THESIS_FIELDS = {"invalidated_core_assumption", "logic_chain_failure", "conclusion_change"}
SOURCE_FIELDS = {"source_id", "title", "publication_time", "source_rank", "source_type", "origin_type"}
REVIEW_FIELDS = {
    "document_type", "schema_version", "status", "source", "source_id", "node_id",
    "node_name", "node_type", "target_view_id", "target_view_version", "decision", "reason",
    "selected_primary_claim_ids", "selected_context_claim_ids", "candidate_claims",
    "thesis_break", "evidence_sufficiency",
}
LABELS = ["HUMAN EDIT REQUIRED", "NOT CANONICAL", "NOT A PRODUCTION PROPOSAL"]
CLAIM_REF = re.compile(r"\bCLM_[A-Za-z0-9_]+\b")


class HumanReviewIntakeError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise HumanReviewIntakeError(code, detail)


def _object(value: Any, fields: set[str], name: str) -> None:
    _require(isinstance(value, dict) and set(value) == fields,
             "INVALID_ARTIFACT", f"{name} must contain exactly {sorted(fields)}")


def _string(value: Any, name: str, *, nonempty: bool = True) -> None:
    _require(isinstance(value, str) and (not nonempty or bool(value.strip())),
             "INVALID_ARTIFACT", f"{name} must be a {'nonempty ' if nonempty else ''}string")


def _ids(value: Any, name: str) -> None:
    _require(isinstance(value, list), "INVALID_ARTIFACT", f"{name} must be an array")
    for item in value:
        _string(item, name)
        _require(item == item.strip(), "INVALID_ARTIFACT", f"{name} contains padded identity")
    _require(len(set(value)) == len(value), "INVALID_ARTIFACT", f"{name} contains duplicates")


def read_artifact(path: str | Path) -> dict[str, Any]:
    """Reject duplicate keys and non-JSON numbers instead of repairing input."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "INVALID_JSON", f"duplicate key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise HumanReviewIntakeError("INVALID_JSON", f"non-JSON constant: {value}")

    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"),
                           object_pairs_hook=unique_object, parse_constant=invalid_constant)
        json.dumps(value, allow_nan=False)
    except HumanReviewIntakeError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise HumanReviewIntakeError("INVALID_JSON", str(exc)) from exc
    _require(isinstance(value, dict), "INVALID_ARTIFACT", "root must be an object")
    return value


def validate_review(review: dict[str, Any]) -> None:
    _object(review, REVIEW_FIELDS, "human_impact_review")
    for key, expected in (
        ("document_type", "human_impact_review"), ("schema_version", "1"),
        ("status", "READY"), ("evidence_sufficiency", "NOT_EVALUATED"),
    ):
        _require(review[key] == expected, "INVALID_ARTIFACT", f"{key} must be {expected}")
    for key in ("source_id", "node_id", "node_name", "node_type", "target_view_id",
                "target_view_version", "decision", "reason"):
        _string(review[key], key)
    _require(review["decision"] in DECISIONS, "INVALID_ARTIFACT", "unknown exported decision")
    _object(review["source"], SOURCE_FIELDS, "source")
    for key in SOURCE_FIELDS:
        _string(review["source"][key], f"source.{key}", nonempty=key == "source_id")
    _require(review["source"]["source_id"] == review["source_id"],
             "INVALID_ARTIFACT", "source identities disagree")
    for key in ("selected_primary_claim_ids", "selected_context_claim_ids"):
        _ids(review[key], key)
    _require(isinstance(review["candidate_claims"], list) and bool(review["candidate_claims"]),
             "INVALID_ARTIFACT", "candidate_claims must be a nonempty array")
    candidate_ids = []
    for item in review["candidate_claims"]:
        _object(item, {"claim_id", "role"}, "candidate Claim")
        _string(item["claim_id"], "candidate Claim ID")
        _string(item["role"], "candidate role")
        _require(item["role"] in CLAIM_NODE_ROLES, "INVALID_ARTIFACT", "unknown Claim role")
        candidate_ids.append(item["claim_id"])
    _ids(candidate_ids, "candidate Claim IDs")
    _object(review["thesis_break"], THESIS_FIELDS, "thesis_break")
    for key in THESIS_FIELDS:
        _string(review["thesis_break"][key], key, nonempty=review["decision"] == "thesis")
    if review["decision"] != "no_change":
        _require(bool(review["selected_primary_claim_ids"]), "INVALID_ARTIFACT",
                 "change decisions require selected Primary Evidence")


def _canonical_state(conn: sqlite3.Connection, review: dict[str, Any]) -> tuple[dict, dict, list]:
    validate_review(review)
    source = conn.execute("SELECT source_id FROM sources WHERE source_id=?",
                          (review["source_id"],)).fetchone()
    _require(source is not None, "SOURCE_NOT_FOUND", review["source_id"])
    row = conn.execute("SELECT * FROM nodes WHERE node_id=?", (review["node_id"],)).fetchone()
    _require(row is not None, "NODE_NOT_FOUND", review["node_id"])
    node = dict(row)
    _require(node["status"] == "active", "NODE_NOT_ACTIVE", review["node_id"])
    _require((node["canonical_name"], node["primary_type"]) ==
             (review["node_name"], review["node_type"]), "NODE_IDENTITY_CHANGED", review["node_id"])
    node["aliases"] = [r[0] for r in conn.execute(
        "SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias", (review["node_id"],))]
    row = conn.execute(
        f"SELECT * FROM current_views WHERE node_id=? AND status='official' ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1",
        (review["node_id"],),
    ).fetchone()
    _require(row is not None and (row["view_id"], row["version"]) ==
             (review["target_view_id"], review["target_view_version"]),
             "STALE_TARGET_VIEW", "latest official target ID/version changed")
    view = dict(row)
    claim_ids = [r[0] for r in conn.execute(
        "SELECT claim_id FROM claims WHERE source_id=? ORDER BY claim_id", (review["source_id"],))]
    candidates = ReadOnlyQuery._impact_candidates_for_claims(conn, claim_ids)["candidates"]
    candidate = next((c for c in candidates if c["node"]["node_id"] == review["node_id"]), None)
    actual = sorted((c["claim_id"], c["role"]) for c in candidate["claims"]) if candidate else []
    expected = sorted((c["claim_id"], c["role"]) for c in review["candidate_claims"])
    _require(actual == expected, "CANDIDATE_EVIDENCE_CHANGED", "exact Claim ID/role snapshot changed")
    claims = [dict(r) for r in conn.execute(
        """SELECT c.*,cnl.role,s.title AS source_title,s.source_rank,s.origin_type,
                  s.underlying_source_id,s.source_id AS evidence_source_id
           FROM claims c JOIN claim_node_links cnl ON cnl.claim_id=c.claim_id
           JOIN sources s ON s.source_id=c.source_id WHERE cnl.node_id=? ORDER BY c.claim_id""",
        (review["node_id"],),
    )]
    by_id = {c["claim_id"]: c for c in claims}
    snapshot = dict(actual)
    for key, role in (("selected_primary_claim_ids", "subject"), ("selected_context_claim_ids", "context")):
        for claim_id in review[key]:
            claim = by_id.get(claim_id)
            _require(claim is not None and snapshot.get(claim_id) == role and claim["role"] == role,
                     "INELIGIBLE_EVIDENCE", f"{claim_id} must be a current candidate with role={role}")
            if role == "subject":
                _require(claim["status"].strip().lower() in PRIMARY_STATUSES,
                         "INELIGIBLE_EVIDENCE", f"{claim_id}: status={claim['status']}")
    try:
        view["content_json"] = json.loads(view["content_json"])
    except (TypeError, ValueError) as exc:
        raise HumanReviewIntakeError("INVALID_TARGET_CONTENT", "target content is not JSON") from exc
    _require(isinstance(view["content_json"], dict), "INVALID_TARGET_CONTENT", "target must be an object")
    return node, view, claims


def _prepared(review: dict, view: dict) -> dict[str, Any]:
    if review["decision"] == "no_change":
        return {"document_type": "human_review_intake_receipt", "schema_version": "1",
                "status": "INTAKE_VALID", "action": "NO_PROPOSAL", "canonical": False,
                "human_review_handoff": deepcopy(review)}
    return {
        "document_type": "human_review_view_proposal_draft", "schema_version": "1",
        "status": "HUMAN_EDIT_REQUIRED", "labels": list(LABELS),
        "proposal_type": "current_view_change", "propagation_batch_id": "", "source_impact_id": "",
        "payload": {
            "node_id": review["node_id"], "previous_view_id": review["target_view_id"],
            "previous_version": review["target_view_version"], "change_level": review["decision"],
            "trigger_source_id": review["source_id"],
            "evidence_claim_ids": list(review["selected_primary_claim_ids"]),
            "proposed_current_view": deepcopy(view["content_json"]),
            "human_review_handoff": deepcopy(review),
        },
    }


def prepare_review(db_path: str | Path, review: dict[str, Any]) -> dict[str, Any]:
    with ReadOnlyQuery(db_path).connect() as conn:
        conn.execute("BEGIN")  # One read-only snapshot, including candidate discovery.
        _, view, _ = _canonical_state(conn, review)
        return _prepared(review, view)


def _has_content_change(before: dict, after: dict) -> bool:
    # Reuse the Phase 2.5B value comparators without pretending a draft is an official View.
    # Governance / evidence metadata alone is deliberately not a human content edit.
    return compare_view_content(before, after)["has_changes"]


def _validate_content(node: dict, view: dict, claims: list[dict], payload: dict) -> None:
    content = payload["proposed_current_view"]
    _require(isinstance(content, dict), "INVALID_VIEW_CONTENT", "proposed_current_view must be an object")
    try:
        json.dumps(content, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HumanReviewIntakeError("INVALID_VIEW_CONTENT", "content must be finite JSON") from exc
    _require(_has_content_change(view["content_json"], content),
             "CHANGE_DECISION_WITHOUT_VIEW_CHANGE", "human edit must change deterministic View content")
    for key in SCALAR_FIELDS + ("recent_change",):
        if key in content:
            _string(content[key], key, nonempty=False)
    for key in LIST_FIELDS:
        _require(isinstance(content.get(key, []), list) and
                 all(isinstance(v, str) for v in content.get(key, [])),
                 "INVALID_VIEW_CONTENT", f"{key} must be an array of strings")
    _ids(content.get("evidence_claim_ids"), "proposed_current_view.evidence_claim_ids")
    primary = set(payload["evidence_claim_ids"])
    _require(set(content["evidence_claim_ids"]) == primary, "INELIGIBLE_EVIDENCE",
             "content evidence must equal selected Primary Evidence")
    by_id = {c["claim_id"]: c for c in claims}
    editable = set(SCALAR_FIELDS + LIST_FIELDS) | {"type_specific", "recent_change", "evidence_claim_ids"}
    for key in (set(content) | set(view["content_json"])) - editable:
        _require(key in content and key in view["content_json"] and content[key] == view["content_json"][key],
                 "INVALID_VIEW_CONTENT", f"out-of-scope content metadata edit: {key}")
    for key in editable - {"evidence_claim_ids"}:
        items = content.get(key, []) if key in LIST_FIELDS else [content.get(key)]
        for item in items:
            text = json.dumps(item, ensure_ascii=False, allow_nan=False)
            refs = set(CLAIM_REF.findall(text)) | {cid for cid in by_id if cid in text}
            for cid in refs - primary:
                claim = by_id.get(cid)
                unresolved = (claim is not None and claim["role"] == "subject" and
                              claim["status"].strip().lower() == "needs_review" and
                              key in {"assumptions_to_verify", "knowledge_gaps"} and "needs_review" in text)
                _require(unresolved, "NON_PRIMARY_DIRECT_SUPPORT", f"{key} cites non-primary {cid}")
    try:
        _validate_frozen_content_contract(node, content, [by_id[cid] for cid in payload["evidence_claim_ids"]])
    except CurrentViewPilotError as exc:
        raise HumanReviewIntakeError("FROZEN_CURRENT_VIEW_VALIDATION_FAILED", str(exc)) from exc


def submit_review(db_path: str | Path, draft: dict[str, Any], *, isolated: bool = False) -> dict[str, Any]:
    """Only an explicit isolated DB may receive a pending Proposal; never accept it."""
    _require(isolated is True, "ISOLATED_DB_REQUIRED", "Production Proposal writes are not authorized")
    path = Path(db_path).resolve(strict=True)
    production = load_config().db_path.resolve()
    _require(path != production and not (production.exists() and path.samefile(production)),
             "PRODUCTION_WRITE_NOT_AUTHORIZED", "use an isolated fixture or copy")
    db = Database(path)
    with db.transaction(immediate=True) as conn:
        payload = _validate_submission(conn, draft)
        return _persist_submission(db, conn, payload)


def _validate_submission(conn: sqlite3.Connection, draft: dict[str, Any]) -> dict[str, Any]:
    """Shared deterministic gates, using the caller's current transaction snapshot."""
    _require(isinstance(draft, dict) and isinstance(draft.get("payload"), dict),
             "INVALID_ARTIFACT", "SUBMIT requires a change Proposal draft, not a NO_CHANGE receipt")
    payload = draft["payload"]
    review = payload.get("human_review_handoff")
    node, view, claims = _canonical_state(conn, review)
    _require(review["decision"] != "no_change", "NO_PROPOSAL", "NO_CHANGE cannot create a Proposal")
    expected = _prepared(review, view)
    _require("proposed_current_view" in payload, "INVALID_ARTIFACT", "missing proposed_current_view")
    expected["payload"]["proposed_current_view"] = payload["proposed_current_view"]
    _require(draft == expected, "DRAFT_ENVELOPE_CHANGED", "only proposed_current_view is editable")
    _validate_content(node, view, claims, payload)
    return payload


def _find_pending_submission(conn: sqlite3.Connection, payload: dict[str, Any]) -> str | None:
    review = payload["human_review_handoff"]
    existing_id = None
    for row in conn.execute(
        """SELECT * FROM proposals WHERE proposal_type='current_view_change'
           AND target_node_id=? AND status='pending' ORDER BY proposal_id""", (review["node_id"],),
    ):
        try:
            stored = json.loads(row["payload_json"])
        except ValueError as exc:
            raise HumanReviewIntakeError("INVALID_PENDING_PROPOSAL", row["proposal_id"]) from exc
        if not isinstance(stored, dict) or stored.get("human_review_handoff") != review:
            continue
        _require(stored == payload and row["propagation_batch_id"] == "" and row["source_impact_id"] == "",
                 "PENDING_PROPOSAL_CONFLICT", f"pending Proposal {row['proposal_id']} differs; human resolution required")
        existing_id = existing_id or row["proposal_id"]
    return existing_id


def _persist_submission(db: Database, conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    existing_id = _find_pending_submission(conn, payload)
    if existing_id:
        return {"status": "pending", "proposal_id": existing_id, "created": False}
    proposal_id = db.add_proposal(
        "current_view_change", deepcopy(payload), target_node_id=payload["node_id"],
        reason=payload["human_review_handoff"]["reason"], propagation_batch_id="", source_impact_id="", _conn=conn,
    )
    return {"status": "pending", "proposal_id": proposal_id, "created": True}
