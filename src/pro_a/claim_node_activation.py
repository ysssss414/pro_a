"""Controlled Phase 2.3D activation of human-approved Claim-to-Node links."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .coverage import exact_node_matches, run_audit


TARGET_NODE_ID = "NODE_20260817_DABE52FE"
TARGET_NODE_NAME = "MLCC"
TARGET_NODE_TYPE = "Product"
EXPECTED_SOURCE_ID = "SRC_20260814_F6E1EFAD"
LINK_CLAIM_IDS = (
    "CLM_20260814_0B6E52F8",
    "CLM_20260814_541F5C31",
    "CLM_20260814_8E4B9E25",
    "CLM_20260814_939CAEDD",
    "CLM_20260814_980FA010",
    "CLM_20260814_9A069D06",
    "CLM_20260814_BA7AC415",
    "CLM_20260814_BAED6789",
    "CLM_20260814_D2C7FCD1",
    "CLM_20260814_E1A48290",
    "CLM_20260814_E53B8E9C",
)
NO_LINK_CLAIM_ID = "CLM_20260814_84099D0C"
REVIEWED_CLAIM_IDS = tuple(sorted((*LINK_CLAIM_IDS, NO_LINK_CLAIM_ID)))
LINK_REVIEWER_NOTE = (
    "Human adjudication confirms that the Claim is attributable to MLCC. "
    "Broad Source-level links are not inherited as Claim-level attribution."
)
NO_LINK_REVIEWER_NOTE = (
    "Electronic ceramics revenue is broader than MLCC. "
    "Current evidence does not support attributing the full revenue figure to MLCC."
)
PRESERVED_TABLES = (
    "nodes",
    "node_aliases",
    "node_relations",
    "sources",
    "claims",
    "current_views",
    "research_questions",
    "knowledge_gaps",
    "source_node_links",
    "relation_evidence_links",
)


class ActivationError(RuntimeError):
    """A frozen precondition or exact postcondition was not satisfied."""


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def _object_state(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    return {table: _table_snapshot(conn, table) for table in PRESERVED_TABLES}


def _read_package(path: str | Path) -> dict[str, dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    package = {row["claim_id"]: row for row in rows}
    if len(package) != len(rows):
        raise ActivationError("duplicate claim_id in Phase 2.3C package")
    if set(package) != set(REVIEWED_CLAIM_IDS):
        raise ActivationError("Phase 2.3C package Claim allowlist mismatch")
    return package


def _validate_allowlist() -> None:
    if len(LINK_CLAIM_IDS) != 11 or len(set(LINK_CLAIM_IDS)) != 11:
        raise ActivationError("human LINK allowlist must contain exactly 11 unique Claims")
    if NO_LINK_CLAIM_ID in LINK_CLAIM_IDS:
        raise ActivationError("NO_LINK Claim cannot appear in LINK allowlist")
    if (TARGET_NODE_ID, TARGET_NODE_NAME, TARGET_NODE_TYPE) != (
        "NODE_20260817_DABE52FE",
        "MLCC",
        "Product",
    ):
        raise ActivationError("target Node allowlist changed")


def _source_validation(
    conn: sqlite3.Connection,
    source_id: str,
    target: dict[str, Any],
) -> dict[str, Any]:
    source = conn.execute(
        """SELECT source_id,title,original_name,metadata_json,status
           FROM sources WHERE source_id=?""",
        (source_id,),
    ).fetchone()
    if source is None:
        raise ActivationError(f"Source does not exist: {source_id}")
    aliases = {
        row["alias"]: row["node_id"]
        for row in conn.execute(
            "SELECT alias,node_id FROM node_aliases WHERE node_id=? ORDER BY alias",
            (TARGET_NODE_ID,),
        ).fetchall()
    }
    target_map = {TARGET_NODE_ID: target}
    canonical_fields: list[str] = []
    alias_fields: list[str] = []
    for field in ("title", "original_name", "metadata_json"):
        canonical_ids, alias_ids = exact_node_matches(
            str(source[field] or ""), target_map, aliases
        )
        if TARGET_NODE_ID in canonical_ids:
            canonical_fields.append(field)
        if TARGET_NODE_ID in alias_ids:
            alias_fields.append(field)
    if not canonical_fields and not alias_fields:
        raise ActivationError("Source has no exact MLCC canonical/alias signal")
    return {
        "source_id": source["source_id"],
        "title": source["title"],
        "status": source["status"],
        "exact_canonical_fields": canonical_fields,
        "exact_alias_fields": alias_fields,
        "validated": True,
    }


def _inspect_connection(
    conn: sqlite3.Connection,
    package: dict[str, dict[str, str]],
) -> dict[str, Any]:
    _validate_allowlist()
    target_row = conn.execute(
        """SELECT node_id,canonical_name,primary_type,status
           FROM nodes WHERE node_id=?""",
        (TARGET_NODE_ID,),
    ).fetchone()
    if target_row is None:
        raise ActivationError(f"target Node does not exist: {TARGET_NODE_ID}")
    target = dict(target_row)
    if target != {
        "node_id": TARGET_NODE_ID,
        "canonical_name": TARGET_NODE_NAME,
        "primary_type": TARGET_NODE_TYPE,
        "status": "active",
    }:
        raise ActivationError("target Node identity/status mismatch")

    placeholders = ",".join("?" for _ in REVIEWED_CLAIM_IDS)
    claims = [
        dict(row)
        for row in conn.execute(
            f"""SELECT claim_id,source_id,statement,nature,status,confidence,evidence_excerpt
                FROM claims WHERE claim_id IN ({placeholders}) ORDER BY claim_id""",
            REVIEWED_CLAIM_IDS,
        ).fetchall()
    ]
    if len(claims) != len(REVIEWED_CLAIM_IDS):
        found = {claim["claim_id"] for claim in claims}
        missing = sorted(set(REVIEWED_CLAIM_IDS) - found)
        raise ActivationError(f"reviewed Claim missing: {','.join(missing)}")
    for claim in claims:
        package_row = package[claim["claim_id"]]
        if claim["statement"] != package_row["statement"]:
            raise ActivationError(f"Claim statement drift: {claim['claim_id']}")
        if claim["source_id"] != EXPECTED_SOURCE_ID:
            raise ActivationError(f"Claim Source identity drift: {claim['claim_id']}")
        if package_row["source_id"] != EXPECTED_SOURCE_ID:
            raise ActivationError(f"package Source identity drift: {claim['claim_id']}")

    source_validation = _source_validation(conn, EXPECTED_SOURCE_ID, target)
    package_titles = {package[claim_id]["source_title"] for claim_id in REVIEWED_CLAIM_IDS}
    if package_titles != {source_validation["title"]}:
        raise ActivationError("Source title drift from Phase 2.3C package")

    links = [
        dict(row)
        for row in conn.execute(
            f"""SELECT claim_id,node_id,role FROM claim_node_links
                WHERE claim_id IN ({placeholders}) ORDER BY claim_id,node_id""",
            REVIEWED_CLAIM_IDS,
        ).fetchall()
    ]
    links_by_claim: dict[str, list[dict[str, Any]]] = {
        claim_id: [] for claim_id in REVIEWED_CLAIM_IDS
    }
    for link in links:
        links_by_claim[link["claim_id"]].append(link)
    exact_desired = {
        claim_id: links_by_claim[claim_id]
        == [{"claim_id": claim_id, "node_id": TARGET_NODE_ID, "role": "related"}]
        for claim_id in LINK_CLAIM_IDS
    }
    no_link_count = len(links_by_claim[NO_LINK_CLAIM_ID])
    unexpected = [
        link
        for link in links
        if not (
            link["claim_id"] in LINK_CLAIM_IDS
            and link["node_id"] == TARGET_NODE_ID
            and link["role"] == "related"
        )
    ]
    desired_count = sum(exact_desired.values())
    all_empty = not links
    if all_empty:
        classification = "CLEAN_NOT_APPLIED"
    elif desired_count == len(LINK_CLAIM_IDS) and not unexpected and no_link_count == 0:
        classification = "ALREADY_APPLIED"
    else:
        raise ActivationError("PARTIAL_OR_CONFLICTING_DRIFT")

    return {
        "classification": classification,
        "target_node": target,
        "claims": claims,
        "source_validation": source_validation,
        "reviewed_links": links,
        "pre_existing_desired_links": desired_count,
        "unexpected_claim_node_links": unexpected,
        "no_link_claim_link_count": no_link_count,
        "object_state": _object_state(conn),
        "claim_node_links": _table_snapshot(conn, "claim_node_links"),
    }


def preflight(db_path: str | Path, package_path: str | Path) -> dict[str, Any]:
    package = _read_package(package_path)
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        if integrity != "ok":
            raise ActivationError(f"Production integrity_check failed: {integrity}")
        if foreign_key_violations:
            raise ActivationError("Production foreign_key_check failed")
        state = _inspect_connection(conn, package)
    coverage = run_audit(db_path)["summary"]
    state.update(
        {
            "integrity_check": integrity,
            "foreign_key_violations": foreign_key_violations,
            "coverage": {
                "nodes_with_sources": coverage["node_coverage"]["with_sources"],
                "nodes_with_claims": coverage["node_coverage"]["with_claims"],
                "unlinked_claims": coverage["unlinked_claims"],
                "knowledge_level_distribution": coverage["knowledge_level_distribution"],
            },
        }
    )
    return state


def _create_backup(db_path: Path, backup_dir: Path, pre_sha: str) -> tuple[Path, str]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"pro_a_pre_phase2_3d_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    backup_sha = file_sha256(backup_path)
    if backup_sha != pre_sha:
        raise ActivationError("backup SHA does not match Production pre-SHA")
    return backup_path, backup_sha


def activate_database(
    db_path: str | Path,
    package_path: str | Path,
    backup_dir: str | Path,
) -> dict[str, Any]:
    db = Path(db_path)
    package = _read_package(package_path)
    pre_sha = file_sha256(db)
    pre = preflight(db, package_path)
    if pre["classification"] == "ALREADY_APPLIED":
        return {
            "write_authorized": True,
            "write_needed": False,
            "idempotent_already_applied": True,
            "links_inserted": 0,
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
        raise ActivationError("Production changed after backup and before transaction")

    conn = sqlite3.connect(db, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        locked = _inspect_connection(conn, package)
        if locked["classification"] != "CLEAN_NOT_APPLIED":
            raise ActivationError("Production drifted before transaction apply")
        if locked["object_state"] != pre["object_state"]:
            raise ActivationError("preserved Production state drifted before transaction apply")
        conn.executemany(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            [(claim_id, TARGET_NODE_ID, "related") for claim_id in LINK_CLAIM_IDS],
        )
        applied = _inspect_connection(conn, package)
        if applied["classification"] != "ALREADY_APPLIED":
            raise ActivationError("exact postcondition failed inside transaction")
        if applied["claim_node_links"]["count"] - locked["claim_node_links"]["count"] != 11:
            raise ActivationError("transaction did not insert exactly 11 links")
        if applied["object_state"] != locked["object_state"]:
            raise ActivationError("transaction changed a preserved Production object")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    post = preflight(db, package_path)
    post_sha = file_sha256(db)
    changes = {
        table: pre["object_state"][table] != post["object_state"][table]
        for table in PRESERVED_TABLES
    }
    if any(changes.values()):
        raise ActivationError("post-write preserved Production state mismatch")
    if post["classification"] != "ALREADY_APPLIED":
        raise ActivationError("post-write exact link validation failed")
    if post["claim_node_links"]["count"] - pre["claim_node_links"]["count"] != 11:
        raise ActivationError("post-write Claim-Node link delta is not exactly 11")
    if post_sha == pre_sha:
        raise ActivationError("Production SHA did not change after authorized write")
    return {
        "write_authorized": True,
        "write_needed": True,
        "idempotent_already_applied": False,
        "links_inserted": 11,
        "pre_sha": pre_sha,
        "post_sha": post_sha,
        "backup_path": str(backup_path),
        "backup_sha": backup_sha,
        "pre": pre,
        "post": post,
        "preserved_table_changes": changes,
    }


def decisions() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": claim_id,
            "decision": "LINK",
            "selected_node_ids": [TARGET_NODE_ID],
            "reviewer_note": LINK_REVIEWER_NOTE,
        }
        for claim_id in LINK_CLAIM_IDS
    ] + [
        {
            "claim_id": NO_LINK_CLAIM_ID,
            "decision": "NO_LINK",
            "selected_node_ids": [],
            "reviewer_note": NO_LINK_REVIEWER_NOTE,
        }
    ]


def post_activation_coverage(db_path: str | Path) -> dict[str, Any]:
    summary = run_audit(db_path)["summary"]
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        mlcc_claim_count = conn.execute(
            "SELECT COUNT(*) FROM claim_node_links WHERE node_id=?", (TARGET_NODE_ID,)
        ).fetchone()[0]
    return {
        "nodes_with_sources": summary["node_coverage"]["with_sources"],
        "nodes_with_claims": summary["node_coverage"]["with_claims"],
        "unlinked_claims": summary["unlinked_claims"],
        "knowledge_level_distribution": summary["knowledge_level_distribution"],
        "mlcc_claim_count": mlcc_claim_count,
    }


def _write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def write_receipt(result: dict[str, Any], path: str | Path) -> Path:
    payload = {
        "phase": "2.3D",
        "decision_source": "human_adjudication",
        "reviewer": "human",
        "target_node_id": TARGET_NODE_ID,
        "target_node_name": TARGET_NODE_NAME,
        "decisions": decisions(),
        "source_validation": result["pre"]["source_validation"],
        "pre_write_state": {
            "classification": result["pre"]["classification"],
            "pre_existing_desired_links": result["pre"]["pre_existing_desired_links"],
            "unexpected_claim_node_links": result["pre"]["unexpected_claim_node_links"],
            "no_link_claim_link_count": result["pre"]["no_link_claim_link_count"],
            "claims": result["pre"]["claims"],
        },
        "write": {
            "authorized": result["write_authorized"],
            "needed": result["write_needed"],
            "idempotent_already_applied": result["idempotent_already_applied"],
            "links_inserted": result["links_inserted"],
            "role": "related",
        },
        "backup": {"path": result["backup_path"], "sha256": result["backup_sha"]},
        "production_sha256": {"pre": result["pre_sha"], "post": result["post_sha"]},
    }
    return _write_json(path, payload)


def write_activation_report(
    result: dict[str, Any],
    coverage: dict[str, Any],
    path: str | Path,
) -> Path:
    pre_coverage = result["pre"]["coverage"]
    lines = [
        "# Phase 2.3D Controlled Claim–Node Activation",
        "",
        "- Decision source: human adjudication",
        f"- Target: `{TARGET_NODE_ID}` (`{TARGET_NODE_NAME}`, `{TARGET_NODE_TYPE}`)",
        f"- Human LINK decisions: {len(LINK_CLAIM_IDS)}",
        "- Human NO_LINK decisions: 1",
        "- Write payload role: `related`",
        f"- Links inserted: {result['links_inserted']}",
        f"- Production pre-SHA-256: `{result['pre_sha']}`",
        f"- Production post-SHA-256: `{result['post_sha']}`",
        f"- Backup: `{result['backup_path']}`",
        f"- Backup SHA-256: `{result['backup_sha']}`",
        "",
        "## Post-write validation",
        "",
        f"- Desired MLCC links: {result['post']['pre_existing_desired_links']}",
        f"- Unexpected reviewed Claim links: {len(result['post']['unexpected_claim_node_links'])}",
        f"- NO_LINK Claim links: {result['post']['no_link_claim_link_count']}",
        f"- Nodes with Claims: {pre_coverage['nodes_with_claims']} → {coverage['nodes_with_claims']}",
        f"- Unlinked Claims: {pre_coverage['unlinked_claims']} → {coverage['unlinked_claims']}",
        f"- MLCC linked Claims: {coverage['mlcc_claim_count']}",
        f"- Knowledge levels before: `{json.dumps(pre_coverage['knowledge_level_distribution'], sort_keys=True)}`",
        f"- Knowledge levels after: `{json.dumps(coverage['knowledge_level_distribution'], sort_keys=True)}`",
        "- Production integrity: `ok`; foreign-key violations: `0`",
        "- Claims, Source links, Current Views, Research Questions, Knowledge Gaps and Relations: unchanged",
        "",
        "`PHASE2_3D_CLAIM_NODE_ACTIVATION_COMPLETE = true`",
        "",
    ]
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate/apply the fixed Phase 2.3D human adjudication allowlist")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--package", type=Path, default=Path("artifacts/phase2_3c/claim_node_adjudication.csv"))
    parser.add_argument("--backup-dir", type=Path, default=Path("workspace/backups"))
    parser.add_argument("--receipt", type=Path, default=Path("artifacts/phase2_3d/claim_node_human_adjudication_receipt.json"))
    parser.add_argument("--coverage", type=Path, default=Path("artifacts/phase2_3d/post_activation_coverage.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/PHASE2_3D_CLAIM_NODE_ACTIVATION.md"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    db_path = args.db or load_config(args.config).db_path
    if not args.apply:
        state = preflight(db_path, args.package)
        print(json.dumps({"classification": state["classification"], "write_authorized": True}, sort_keys=True))
        return 0
    result = activate_database(db_path, args.package, args.backup_dir)
    coverage = post_activation_coverage(db_path)
    write_receipt(result, args.receipt)
    _write_json(args.coverage, coverage)
    write_activation_report(result, coverage, args.report)
    print(
        json.dumps(
            {
                "classification": result["post"]["classification"],
                "links_inserted": result["links_inserted"],
                "write_needed": result["write_needed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
