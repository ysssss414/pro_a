"""Controlled Phase 2.3F Claim attribution semantics and Company activation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .claim_node_activation import EXPECTED_SOURCE_ID, NO_LINK_CLAIM_ID, TARGET_NODE_ID
from .constants import CLAIM_NODE_ROLES, NODE_TYPES
from .coverage import run_audit
from .db import now_iso
from .entity_granularity import COMPANY_NAME, REVIEW_DECISIONS
from .ids import make_id


MLCC_NAME = "MLCC"
MLCC_TYPE = "Product"
COMPANY_TYPE = "Company"
MLCC_PRIMARY_CLAIM_IDS = (
    "CLM_20260814_980FA010",
    "CLM_20260814_BAED6789",
    "CLM_20260814_D2C7FCD1",
)
COMPANY_PRIMARY_CLAIM_IDS = (
    "CLM_20260814_0B6E52F8",
    "CLM_20260814_541F5C31",
    "CLM_20260814_8E4B9E25",
    "CLM_20260814_939CAEDD",
    "CLM_20260814_9A069D06",
    "CLM_20260814_BA7AC415",
    "CLM_20260814_E1A48290",
    "CLM_20260814_E53B8E9C",
)
REVIEWED_CLAIM_IDS = tuple(sorted((*MLCC_PRIMARY_CLAIM_IDS, *COMPANY_PRIMARY_CLAIM_IDS)))
ROLE_SEMANTICS = {
    "subject": "Claim directly makes an assertion about this Node; the Node is the factual subject.",
    "context": "Claim is materially relevant to this Node, but the Node is not the primary factual subject.",
    "related": "Legacy or generic association whose subject/context attribution is not adjudicated.",
}
PRESERVED_TABLES = (
    "claims",
    "sources",
    "source_node_links",
    "node_relations",
    "relation_evidence_links",
    "current_views",
    "research_questions",
    "knowledge_gaps",
)
COUNTED_TABLES = (
    "nodes",
    "node_aliases",
    "claims",
    "sources",
    "claim_node_links",
    "source_node_links",
    "node_relations",
    "relation_evidence_links",
    "current_views",
    "research_questions",
    "knowledge_gaps",
)


class AttributionActivationError(RuntimeError):
    """A frozen Phase 2.3F precondition or postcondition was not satisfied."""


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_claim_node_role(role: str) -> str:
    if role not in CLAIM_NODE_ROLES:
        raise AttributionActivationError(f"invalid Claim-Node role: {role!r}")
    return role


def insert_claim_node_link(
    conn: sqlite3.Connection,
    claim_id: str,
    node_id: str,
    role: str,
) -> None:
    validated = validate_claim_node_role(role)
    conn.execute(
        "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
        (claim_id, node_id, validated),
    )


def update_claim_node_link_role(
    conn: sqlite3.Connection,
    claim_id: str,
    node_id: str,
    *,
    expected_role: str,
    new_role: str,
) -> None:
    expected = validate_claim_node_role(expected_role)
    new = validate_claim_node_role(new_role)
    cursor = conn.execute(
        """UPDATE claim_node_links SET role=?
           WHERE claim_id=? AND node_id=? AND role=?""",
        (new, claim_id, node_id, expected),
    )
    if cursor.rowcount != 1:
        raise AttributionActivationError(
            f"Claim-Node role update precondition failed: {claim_id}"
        )


def approved_claim_matrix() -> list[dict[str, Any]]:
    rows = [
        {
            "claim_id": claim_id,
            "primary_subject": MLCC_NAME,
            "context": [],
            "mlcc_role": "subject",
            "company_role": None,
        }
        for claim_id in MLCC_PRIMARY_CLAIM_IDS
    ]
    rows.extend(
        {
            "claim_id": claim_id,
            "primary_subject": COMPANY_NAME,
            "context": [MLCC_NAME],
            "mlcc_role": "context",
            "company_role": "subject",
        }
        for claim_id in COMPANY_PRIMARY_CLAIM_IDS
    )
    return sorted(rows, key=lambda row: row["claim_id"])


def _validate_frozen_contract() -> None:
    if CLAIM_NODE_ROLES != {"subject", "context", "related"}:
        raise AttributionActivationError("Claim-Node role vocabulary drift")
    if COMPANY_TYPE not in NODE_TYPES:
        raise AttributionActivationError("Company is not an allowed Node Type")
    if len(REVIEWED_CLAIM_IDS) != 11 or len(set(REVIEWED_CLAIM_IDS)) != 11:
        raise AttributionActivationError("approved Claim allowlist must contain 11 unique IDs")
    expected_classes = {
        **{claim_id: "MLCC_PRIMARY" for claim_id in MLCC_PRIMARY_CLAIM_IDS},
        **{
            claim_id: "COMPANY_PRIMARY_MLCC_CONTEXT"
            for claim_id in COMPANY_PRIMARY_CLAIM_IDS
        },
    }
    actual_classes = {
        claim_id: decision["attribution_class"]
        for claim_id, decision in REVIEW_DECISIONS.items()
    }
    if actual_classes != expected_classes:
        raise AttributionActivationError("Phase 2.3E frozen review matrix drift")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _table_snapshot(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
    if not _table_exists(conn, table):
        return {"exists": False, "count": 0, "sha256": ""}
    rows = [
        json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str)
        for row in conn.execute(f'SELECT * FROM "{table}"').fetchall()
    ]
    payload = "\n".join(sorted(rows)).encode("utf-8")
    return {
        "exists": True,
        "count": len(rows),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
    }


def _preserved_state(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    return {table: _table_snapshot(conn, table) for table in PRESERVED_TABLES}


def _database_counts(conn: sqlite3.Connection) -> dict[str, int | None]:
    return {
        table: (
            conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            if _table_exists(conn, table)
            else None
        )
        for table in COUNTED_TABLES
    }


def _links(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _clean_mlcc_links() -> list[dict[str, str]]:
    return [
        {"claim_id": claim_id, "node_id": TARGET_NODE_ID, "role": "related"}
        for claim_id in REVIEWED_CLAIM_IDS
    ]


def _post_mlcc_links() -> list[dict[str, str]]:
    roles = {
        **{claim_id: "subject" for claim_id in MLCC_PRIMARY_CLAIM_IDS},
        **{claim_id: "context" for claim_id in COMPANY_PRIMARY_CLAIM_IDS},
    }
    return [
        {"claim_id": claim_id, "node_id": TARGET_NODE_ID, "role": roles[claim_id]}
        for claim_id in REVIEWED_CLAIM_IDS
    ]


def _post_target_links(company_node_id: str) -> list[dict[str, str]]:
    rows = _post_mlcc_links()
    rows.extend(
        {"claim_id": claim_id, "node_id": company_node_id, "role": "subject"}
        for claim_id in COMPANY_PRIMARY_CLAIM_IDS
    )
    return sorted(rows, key=lambda row: (row["claim_id"], row["node_id"]))


def _expected_all_links_after(
    pre_links: list[dict[str, Any]],
    company_node_id: str,
) -> list[dict[str, Any]]:
    reviewed = set(REVIEWED_CLAIM_IDS)
    rows = [
        row
        for row in pre_links
        if not (row["claim_id"] in reviewed and row["node_id"] == TARGET_NODE_ID)
    ]
    rows.extend(_post_target_links(company_node_id))
    return sorted(rows, key=lambda row: (row["claim_id"], row["node_id"]))


def _inspect_connection(conn: sqlite3.Connection) -> dict[str, Any]:
    _validate_frozen_contract()
    mlcc_row = conn.execute(
        """SELECT node_id,canonical_name,primary_type,status
           FROM nodes WHERE node_id=?""",
        (TARGET_NODE_ID,),
    ).fetchone()
    if mlcc_row is None or dict(mlcc_row) != {
        "node_id": TARGET_NODE_ID,
        "canonical_name": MLCC_NAME,
        "primary_type": MLCC_TYPE,
        "status": "active",
    }:
        raise AttributionActivationError("MLCC identity/status drift")

    placeholders = ",".join("?" for _ in REVIEWED_CLAIM_IDS)
    claims = [
        dict(row)
        for row in conn.execute(
            f"""SELECT claim_id,source_id,statement,nature,status,confidence,
                       evidence_pointer,evidence_excerpt
                FROM claims WHERE claim_id IN ({placeholders}) ORDER BY claim_id""",
            REVIEWED_CLAIM_IDS,
        ).fetchall()
    ]
    if len(claims) != len(REVIEWED_CLAIM_IDS):
        found = {row["claim_id"] for row in claims}
        missing = sorted(set(REVIEWED_CLAIM_IDS) - found)
        raise AttributionActivationError(f"approved Claim missing: {','.join(missing)}")
    if any(row["source_id"] != EXPECTED_SOURCE_ID for row in claims):
        raise AttributionActivationError("approved Claim Source identity drift")

    canonical_matches = [
        dict(row)
        for row in conn.execute(
            """SELECT node_id,canonical_name,primary_type,status
               FROM nodes WHERE canonical_name=? COLLATE NOCASE ORDER BY node_id""",
            (COMPANY_NAME,),
        ).fetchall()
    ]
    alias_matches = [
        dict(row)
        for row in conn.execute(
            """SELECT a.alias,a.node_id,n.canonical_name,n.primary_type,n.status
               FROM node_aliases a JOIN nodes n ON n.node_id=a.node_id
               WHERE a.alias=? COLLATE NOCASE ORDER BY a.node_id""",
            (COMPANY_NAME,),
        ).fetchall()
    ]
    target_links = _links(
        conn,
        f"""SELECT claim_id,node_id,role FROM claim_node_links
            WHERE claim_id IN ({placeholders}) ORDER BY claim_id,node_id""",
        REVIEWED_CLAIM_IDS,
    )
    mlcc_links = _links(
        conn,
        """SELECT claim_id,node_id,role FROM claim_node_links
           WHERE node_id=? ORDER BY claim_id,node_id""",
        (TARGET_NODE_ID,),
    )
    no_link_count = conn.execute(
        "SELECT COUNT(*) FROM claim_node_links WHERE claim_id=?",
        (NO_LINK_CLAIM_ID,),
    ).fetchone()[0]
    all_links = _links(
        conn,
        "SELECT claim_id,node_id,role FROM claim_node_links ORDER BY claim_id,node_id",
        (),
    )

    company_node: dict[str, Any] | None = None
    company_aliases: list[str] = []
    company_links: list[dict[str, Any]] = []
    if len(canonical_matches) == 1:
        company_node = canonical_matches[0]
        company_aliases = [
            row[0]
            for row in conn.execute(
                "SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias",
                (company_node["node_id"],),
            ).fetchall()
        ]
        company_links = _links(
            conn,
            """SELECT claim_id,node_id,role FROM claim_node_links
               WHERE node_id=? ORDER BY claim_id,node_id""",
            (company_node["node_id"],),
        )

    clean = (
        not canonical_matches
        and not alias_matches
        and target_links == _clean_mlcc_links()
        and mlcc_links == _clean_mlcc_links()
        and no_link_count == 0
    )
    already_applied = bool(
        company_node
        and company_node == {
            "node_id": company_node["node_id"],
            "canonical_name": COMPANY_NAME,
            "primary_type": COMPANY_TYPE,
            "status": "active",
        }
        and not alias_matches
        and not company_aliases
        and target_links == _post_target_links(company_node["node_id"])
        and mlcc_links == _post_mlcc_links()
        and company_links
        == [
            {
                "claim_id": claim_id,
                "node_id": company_node["node_id"],
                "role": "subject",
            }
            for claim_id in COMPANY_PRIMARY_CLAIM_IDS
        ]
        and no_link_count == 0
    )
    if clean:
        classification = "CLEAN_NOT_APPLIED"
    elif already_applied:
        classification = "ALREADY_APPLIED"
    else:
        raise AttributionActivationError(
            "PARTIAL_OR_CONFLICTING_DRIFT: "
            f"company_canonical={len(canonical_matches)}, "
            f"company_alias={len(alias_matches)}, target_links={len(target_links)}, "
            f"mlcc_links={len(mlcc_links)}, no_link_count={no_link_count}"
        )

    return {
        "classification": classification,
        "mlcc_node": dict(mlcc_row),
        "company_node": company_node,
        "company_canonical_matches": canonical_matches,
        "company_alias_matches": alias_matches,
        "company_aliases": company_aliases,
        "claims": claims,
        "target_links": target_links,
        "mlcc_links": mlcc_links,
        "company_links": company_links,
        "no_link_claim_link_count": no_link_count,
        "all_claim_node_links": all_links,
        "counts": _database_counts(conn),
        "preserved_state": _preserved_state(conn),
        "node_aliases": _table_snapshot(conn, "node_aliases"),
        "nodes": _table_snapshot(conn, "nodes"),
        "claim_node_links": _table_snapshot(conn, "claim_node_links"),
    }


def preflight(db_path: str | Path) -> dict[str, Any]:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        if integrity != "ok":
            raise AttributionActivationError(f"Production integrity_check failed: {integrity}")
        if foreign_key_violations:
            raise AttributionActivationError("Production foreign_key_check failed")
        state = _inspect_connection(conn)
    state["integrity_check"] = integrity
    state["foreign_key_violations"] = foreign_key_violations
    return state


def _create_backup(db_path: Path, backup_dir: Path, pre_sha: str) -> tuple[Path, str]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"pro_a_pre_phase2_3f_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    backup_sha = file_sha256(backup_path)
    if backup_sha != pre_sha:
        raise AttributionActivationError("backup SHA does not match Production pre-SHA")
    return backup_path, backup_sha


def activate_database(
    db_path: str | Path,
    backup_dir: str | Path,
) -> dict[str, Any]:
    db = Path(db_path)
    pre_sha = file_sha256(db)
    pre = preflight(db)
    if pre["classification"] == "ALREADY_APPLIED":
        return {
            "write_authorized": True,
            "write_needed": False,
            "idempotent_already_applied": True,
            "company_node_created": False,
            "company_node_id": pre["company_node"]["node_id"],
            "aliases_added": 0,
            "company_links_inserted": 0,
            "mlcc_role_updates": 0,
            "pre_sha": pre_sha,
            "post_sha": pre_sha,
            "backup_path": "",
            "backup_sha": "",
            "pre": pre,
            "post": pre,
            "preserved_table_changes": {table: False for table in PRESERVED_TABLES},
        }

    backup_path, backup_sha = _create_backup(db, Path(backup_dir), pre_sha)
    if file_sha256(db) != pre_sha:
        raise AttributionActivationError("Production changed after backup and before transaction")

    company_node_id = make_id("NODE")
    conn = sqlite3.connect(db, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        locked = _inspect_connection(conn)
        if locked["classification"] != "CLEAN_NOT_APPLIED":
            raise AttributionActivationError("Production drifted before transaction apply")
        if locked["preserved_state"] != pre["preserved_state"]:
            raise AttributionActivationError("preserved Production state drifted before apply")
        if locked["all_claim_node_links"] != pre["all_claim_node_links"]:
            raise AttributionActivationError("Claim-Node links drifted before apply")

        timestamp = now_iso()
        conn.execute(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                company_node_id,
                COMPANY_NAME,
                COMPANY_TYPE,
                "",
                "active",
                timestamp,
                timestamp,
            ),
        )
        for claim_id in MLCC_PRIMARY_CLAIM_IDS:
            update_claim_node_link_role(
                conn,
                claim_id,
                TARGET_NODE_ID,
                expected_role="related",
                new_role="subject",
            )
        for claim_id in COMPANY_PRIMARY_CLAIM_IDS:
            update_claim_node_link_role(
                conn,
                claim_id,
                TARGET_NODE_ID,
                expected_role="related",
                new_role="context",
            )
            insert_claim_node_link(conn, claim_id, company_node_id, "subject")

        applied = _inspect_connection(conn)
        if applied["classification"] != "ALREADY_APPLIED":
            raise AttributionActivationError("exact postcondition failed inside transaction")
        if applied["company_node"]["node_id"] != company_node_id:
            raise AttributionActivationError("created Company Node identity mismatch")
        if applied["preserved_state"] != locked["preserved_state"]:
            raise AttributionActivationError("transaction changed a preserved Production object")
        if applied["node_aliases"] != locked["node_aliases"]:
            raise AttributionActivationError("transaction changed Node aliases")
        if applied["nodes"]["count"] - locked["nodes"]["count"] != 1:
            raise AttributionActivationError("transaction Node delta is not exactly +1")
        if (
            applied["claim_node_links"]["count"]
            - locked["claim_node_links"]["count"]
            != 8
        ):
            raise AttributionActivationError("Claim-Node link delta is not exactly +8")
        if applied["all_claim_node_links"] != _expected_all_links_after(
            locked["all_claim_node_links"], company_node_id
        ):
            raise AttributionActivationError("unexpected Claim-Node link delta")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    post = preflight(db)
    post_sha = file_sha256(db)
    preserved_changes = {
        table: pre["preserved_state"][table] != post["preserved_state"][table]
        for table in PRESERVED_TABLES
    }
    if any(preserved_changes.values()):
        raise AttributionActivationError("post-write preserved Production state mismatch")
    if post["classification"] != "ALREADY_APPLIED":
        raise AttributionActivationError("post-write exact attribution validation failed")
    if post["company_node"]["node_id"] != company_node_id:
        raise AttributionActivationError("post-write Company Node identity mismatch")
    if post_sha == pre_sha:
        raise AttributionActivationError("Production SHA did not change after authorized write")
    return {
        "write_authorized": True,
        "write_needed": True,
        "idempotent_already_applied": False,
        "company_node_created": True,
        "company_node_id": company_node_id,
        "aliases_added": 0,
        "company_links_inserted": 8,
        "mlcc_role_updates": 11,
        "pre_sha": pre_sha,
        "post_sha": post_sha,
        "backup_path": str(backup_path),
        "backup_sha": backup_sha,
        "pre": pre,
        "post": post,
        "preserved_table_changes": preserved_changes,
    }


def _node_role_summary(conn: sqlite3.Connection, node_id: str) -> dict[str, int]:
    counts = {
        row["role"]: row["count"]
        for row in conn.execute(
            """SELECT role,COUNT(*) AS count FROM claim_node_links
               WHERE node_id=? GROUP BY role ORDER BY role""",
            (node_id,),
        ).fetchall()
    }
    return {
        "total_claims": sum(counts.values()),
        "subject_claims": counts.get("subject", 0),
        "context_claims": counts.get("context", 0),
        "related_claims": counts.get("related", 0),
    }


def post_attribution_summary(db_path: str | Path) -> dict[str, Any]:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        company = conn.execute(
            """SELECT node_id,canonical_name,primary_type,status
               FROM nodes WHERE canonical_name=? COLLATE NOCASE""",
            (COMPANY_NAME,),
        ).fetchone()
        if company is None:
            raise AttributionActivationError("Company Node missing from post state")
        result = {
            "nodes_total": conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
            "aliases_total": conn.execute("SELECT COUNT(*) FROM node_aliases").fetchone()[0],
            "claims_total": conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
            "sources_total": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "claim_node_links_total": conn.execute(
                "SELECT COUNT(*) FROM claim_node_links"
            ).fetchone()[0],
            "node_relations_total": conn.execute(
                "SELECT COUNT(*) FROM node_relations"
            ).fetchone()[0],
            "current_views_total": conn.execute(
                "SELECT COUNT(*) FROM current_views"
            ).fetchone()[0],
            "research_questions_total": conn.execute(
                "SELECT COUNT(*) FROM research_questions"
            ).fetchone()[0],
            "knowledge_gaps_total": conn.execute(
                "SELECT COUNT(*) FROM knowledge_gaps"
            ).fetchone()[0],
            "mlcc": {"node_id": TARGET_NODE_ID, **_node_role_summary(conn, TARGET_NODE_ID)},
            "yunzhong": {
                "node_id": company["node_id"],
                **_node_role_summary(conn, company["node_id"]),
            },
            "nodes_with_subject_claims": conn.execute(
                "SELECT COUNT(DISTINCT node_id) FROM claim_node_links WHERE role='subject'"
            ).fetchone()[0],
            "nodes_with_context_claims": conn.execute(
                "SELECT COUNT(DISTINCT node_id) FROM claim_node_links WHERE role='context'"
            ).fetchone()[0],
            "unlinked_claims": conn.execute(
                """SELECT COUNT(*) FROM claims c
                   WHERE NOT EXISTS (
                       SELECT 1 FROM claim_node_links cnl WHERE cnl.claim_id=c.claim_id
                   )"""
            ).fetchone()[0],
        }
    result["knowledge_level_distribution"] = run_audit(db_path)["summary"][
        "knowledge_level_distribution"
    ]
    return result


def _write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def write_activation_receipt(result: dict[str, Any], path: str | Path) -> Path:
    payload = {
        "phase": "2.3F",
        "human_review_source": "Phase 2.3E",
        "production_write_authorized": result["write_authorized"],
        "company_node": {
            "node_id": result["company_node_id"],
            "canonical_name": COMPANY_NAME,
            "primary_type": COMPANY_TYPE,
            "status": "active",
            "description": "",
            "aliases_added": result["aliases_added"],
        },
        "role_semantics": ROLE_SEMANTICS,
        "approved_claim_matrix": approved_claim_matrix(),
        "pre_write_state": {
            "classification": result["pre"]["classification"],
            "counts": result["pre"]["counts"],
            "target_links": result["pre"]["target_links"],
            "no_link_claim_link_count": result["pre"]["no_link_claim_link_count"],
        },
        "write": {
            "needed": result["write_needed"],
            "idempotent_already_applied": result["idempotent_already_applied"],
            "company_node_created": result["company_node_created"],
            "company_links_inserted": result["company_links_inserted"],
            "mlcc_role_updates": result["mlcc_role_updates"],
        },
        "post_write_state": {
            "classification": result["post"]["classification"],
            "counts": result["post"]["counts"],
            "target_links": result["post"]["target_links"],
            "no_link_claim_link_count": result["post"]["no_link_claim_link_count"],
            "integrity_check": result["post"]["integrity_check"],
            "foreign_key_violations": result["post"]["foreign_key_violations"],
        },
        "backup": {"path": result["backup_path"], "sha256": result["backup_sha"]},
        "production_sha256": {"pre": result["pre_sha"], "post": result["post_sha"]},
        "preserved_table_changes": result["preserved_table_changes"],
    }
    return _write_json(path, payload)


def write_post_summary(summary: dict[str, Any], path: str | Path) -> Path:
    return _write_json(path, summary)


def write_activation_report(
    result: dict[str, Any],
    summary: dict[str, Any],
    path: str | Path,
) -> Path:
    preserved = result["preserved_table_changes"]
    report = f"""# Phase 2.3F — Claim Attribution Semantics & Company Entity Activation

PHASE2_3F_COMPLETE = true
PRODUCTION_WRITE_AUTHORIZED = true
ROLE_SEMANTICS_FROZEN = true
CURRENT_VIEW_CREATED = false

## Outcome

Phase 2.3E showed that eight adjudicated Claims directly assert facts about
`{COMPANY_NAME}`, while MLCC is their product context. A canonical active Company Node was
therefore required. Phase 2.3F created `{result['company_node_id']}` with
`primary_type=Company`, no aliases and no inferred company metadata.

The minimal Claim-to-Node vocabulary is now frozen as:

- `subject`: the Node is the Claim's factual subject.
- `context`: the Claim is materially relevant to the Node, but the Node is not its factual subject.
- `related`: legacy/generic association not yet adjudicated as subject or context.

Link existence no longer implies primary subject. Read API Node Claims expose `link_role`, and
the Explorer Claims tab renders Subject, Context or Related from the stored database role.

## Exact authorized Production delta

- Nodes: {result['pre']['counts']['nodes']} → {result['post']['counts']['nodes']} (+1 `{COMPANY_NAME}` Company).
- Aliases: {result['pre']['counts']['node_aliases']} → {result['post']['counts']['node_aliases']} (+0).
- Claim-to-Node links: {result['pre']['counts']['claim_node_links']} → {result['post']['counts']['claim_node_links']} (+8 Company subject links).
- Existing MLCC roles updated: 3 `related → subject`, 8 `related → context`.
- MLCC: {summary['mlcc']['total_claims']} total = {summary['mlcc']['subject_claims']} subject + {summary['mlcc']['context_claims']} context.
- `{COMPANY_NAME}`: {summary['yunzhong']['total_claims']} total = {summary['yunzhong']['subject_claims']} subject.
- The explicit NO_LINK Claim remains unlinked.

Claims, Sources, Source links, Relations, Current Views, Research Questions and Knowledge Gaps
were not changed. No Company-to-MLCC Relation or Source-to-Node link was created.

## Current View implication

No Current View was created. A future MLCC Current View candidate set should begin with the
three MLCC `role=subject` Claims, not all 11 MLCC-linked Claims. The eight `role=context`
Claims must not be presented as MLCC aggregate facts. The Company has eight subject Claims,
but its Current View also remains a separate future pilot decision.

## Validation and recovery

- Production pre-SHA: `{result['pre_sha']}`
- Backup: `{result['backup_path']}`
- Backup SHA: `{result['backup_sha']}`
- Production post-SHA: `{result['post_sha']}`
- Integrity check: `{result['post']['integrity_check']}`
- Foreign-key violations: `{result['post']['foreign_key_violations']}`
- Preserved tables changed: `{str(any(preserved.values())).lower()}`
- Knowledge levels: `{json.dumps(summary['knowledge_level_distribution'], ensure_ascii=False, sort_keys=True)}`

The write ran in one `BEGIN IMMEDIATE` transaction after an exact locked preflight. A fully
applied state is classified `ALREADY_APPLIED` and performs zero writes; any partial or
conflicting state is rejected rather than completed.

## Scope exclusions

No Claim content/status/confidence, Source link, Relation, Current View, Research Question,
Knowledge Gap or schema migration was created or changed. No LLM, RAG, embedding or generic
ontology framework was used.
"""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="workspace/pro_a.db")
    parser.add_argument("--backup-dir", default="workspace/backups")
    parser.add_argument("--artifact-dir", default="artifacts/phase2_3f")
    parser.add_argument(
        "--report", default="docs/PHASE2_3F_CLAIM_ATTRIBUTION_ACTIVATION.md"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if not args.apply:
        print(json.dumps(preflight(args.db), ensure_ascii=False, indent=2, default=str))
        return 0

    result = activate_database(args.db, args.backup_dir)
    summary = post_attribution_summary(args.db)
    artifact_dir = Path(args.artifact_dir)
    receipt = write_activation_receipt(
        result, artifact_dir / "claim_attribution_activation_receipt.json"
    )
    summary_path = write_post_summary(
        summary, artifact_dir / "post_attribution_summary.json"
    )
    report = write_activation_report(result, summary, args.report)
    print(
        json.dumps(
            {
                "result": {
                    key: value
                    for key, value in result.items()
                    if key not in {"pre", "post"}
                },
                "summary": summary,
                "paths": {
                    "receipt": str(receipt),
                    "post_summary": str(summary_path),
                    "report": str(report),
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
