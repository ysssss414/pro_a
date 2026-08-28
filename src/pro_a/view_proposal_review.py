"""Read-only projections of human-review-backed View Proposals, never a legacy queue."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .current_view_compare import compare_view_content
from .human_review_intake import HumanReviewIntakeError, _canonical_state, _prepared, validate_review
from .query import ReadOnlyQuery


def _human_payload(row: sqlite3.Row) -> dict | None:
    if row["proposal_type"] != "current_view_change" or row["source_impact_id"] or row["propagation_batch_id"]:
        return None
    try:
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            return None
        review = payload.get("human_review_handoff")
        validate_review(review)
        content = payload.get("proposed_current_view")
        if review["decision"] == "no_change" or not isinstance(content, dict):
            return None
        json.dumps(content, allow_nan=False)
        expected = _prepared(review, {"content_json": content})["payload"]
        if payload != expected or row["target_node_id"] != review["node_id"]:
            return None
        return payload
    except (TypeError, ValueError):
        return None


def _source(conn: sqlite3.Connection, review: dict) -> dict:
    row = conn.execute(
        "SELECT source_id,title,publication_time,source_rank,source_type,origin_type FROM sources WHERE source_id=?",
        (review["source_id"],),
    ).fetchone()
    return {**(dict(row) if row else review["source"]), "resolved": row is not None}


def _summary(conn: sqlite3.Connection, row: sqlite3.Row, payload: dict) -> dict:
    review = payload["human_review_handoff"]
    node = conn.execute("SELECT canonical_name,primary_type,status FROM nodes WHERE node_id=?",
                        (review["node_id"],)).fetchone()
    return {
        "proposal_id": row["proposal_id"], "status": row["status"],
        "node_id": review["node_id"], "node_name": node["canonical_name"] if node else review["node_name"],
        "node_type": node["primary_type"] if node else review["node_type"],
        "node_status": node["status"] if node else None, "node_resolved": node is not None,
        "decision": review["decision"], "reason": review["reason"],
        "trigger_source_id": review["source_id"], "trigger_source": _source(conn, review),
        "previous_view_id": payload["previous_view_id"], "previous_version": payload["previous_version"],
        "created_at": row["created_at"], "resolved_at": row["resolved_at"], "human_review_origin": True,
    }


def proposal_snapshot(row: sqlite3.Row, payload: dict) -> dict:
    return {"proposal_type": row["proposal_type"], "target_node_id": row["target_node_id"],
            "created_at": row["created_at"], "payload": payload}


def list_view_proposals(conn: sqlite3.Connection, limit: int, offset: int, status: str = "pending") -> list[dict]:
    # Filter provenance before pagination: malformed/legacy rows never occupy queue slots.
    from .human_proposal_resolution import resolution_result

    terminal_result = resolution_result if status in {"accepted", "rejected"} else None
    rows = conn.execute(
        """SELECT * FROM proposals WHERE proposal_type='current_view_change' AND status=?
           ORDER BY created_at DESC,proposal_id DESC""", (status,),
    )
    valid = []
    for row in rows:
        payload = _human_payload(row)
        if payload is not None and (terminal_result is None or terminal_result(conn, row, payload) is not None):
            valid.append((row, payload))
    return [_summary(conn, row, payload) for row, payload in valid[offset:offset + limit]]


def _evidence(conn: sqlite3.Connection, ids: list[str], node_id: str) -> list[dict]:
    result = ReadOnlyQuery._evidence_claim_refs(conn, ids)
    for item in result:
        row = conn.execute(
            """SELECT c.nature,c.attributed_to,c.scope,l.role FROM claims c
               LEFT JOIN claim_node_links l ON l.claim_id=c.claim_id AND l.node_id=? WHERE c.claim_id=?""",
            (node_id, item["claim_id"]),
        ).fetchone()
        item.update(dict(row) if row else {"nature": None, "attributed_to": None, "scope": None, "role": None})
    return result


def view_proposal_detail(conn: sqlite3.Connection, proposal_id: str) -> dict[str, Any] | None:
    from .human_proposal_resolution import resolution_result

    row = conn.execute("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    if row is None or (payload := _human_payload(row)) is None:
        return None
    review = payload["human_review_handoff"]
    alignment = "CURRENT"
    try:
        _canonical_state(conn, review)
    except HumanReviewIntakeError as exc:
        alignment = "EVIDENCE_INELIGIBLE" if exc.code == "INELIGIBLE_EVIDENCE" else exc.code
    base = conn.execute(
        """SELECT * FROM current_views WHERE view_id=? AND node_id=? AND version=? AND status='official'""",
        (payload["previous_view_id"], payload["node_id"], payload["previous_version"]),
    ).fetchone()
    base_view = ReadOnlyQuery._current_view_result(base) if base else None
    result = resolution_result(conn, row, payload) if row["status"] in {"accepted", "rejected"} else None
    if row["status"] in {"accepted", "rejected"} and result is None:
        return None
    resolution = None
    if result:
        resolution = {key: result["human_resolution"][key] for key in ("action", "reason", "resolved_at")}
        resolution.update(activation_scope=result["activation_scope"], view_id=result.get("view_id", ""),
                          version=result.get("version", ""))
    return {
        **_summary(conn, row, payload), "canonical_alignment": alignment,
        "proposal_snapshot": proposal_snapshot(row, payload), "resolution": resolution,
        "target_official_view": ({key: base_view[key] for key in
                                  ("view_id", "node_id", "version", "revision_date", "change_level")} if base_view else None),
        "before_current_view": base_view["content_json"] if base_view else None,
        "proposed_current_view": payload["proposed_current_view"],
        "diff": compare_view_content(base_view["content_json"], payload["proposed_current_view"]) if base_view else None,
        "human_review_handoff": review, "thesis_break": review["thesis_break"],
        "primary_evidence": _evidence(conn, review["selected_primary_claim_ids"], review["node_id"]),
        "context_evidence": _evidence(conn, review["selected_context_claim_ids"], review["node_id"]),
        "candidate_claims": review["candidate_claims"],
    }
