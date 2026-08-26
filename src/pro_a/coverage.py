"""Read-only Knowledge coverage audit for the Phase 2 research surface.

The audit deliberately reads the canonical SQLite database through
``ReadOnlyQuery``.  It never creates a schema, opens a writable connection,
or infers a new Node link; exact canonical/alias mentions are review signals
only.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .config import load_config
from .query import ReadOnlyQuery


NODE_FIELDS = [
    "node_id", "canonical_name", "primary_type", "alias_count", "parent_count",
    "child_count", "source_count", "claim_count", "current_view_count",
    "research_question_count", "knowledge_gap_count", "part_of_in_count",
    "part_of_out_count", "functional_relation_count",
]
SOURCE_FIELDS = [
    "source_id", "title", "source_type", "source_rank", "source_node_link_count",
    "claim_count", "node_linked_claim_count", "unlinked_claim_count",
]
CLAIM_FIELDS = [
    "claim_id", "source_id", "source_title", "source_type", "source_rank",
    "statement", "evidence_excerpt", "nature", "status", "confidence",
    "evidence_pointer",
    "evidence_pointer_present", "evidence_excerpt_present", "claim_node_link_count",
    "relation_evidence_link_count", "current_view_trigger_ref_count",
    "research_question_ref_count", "knowledge_gap_ref_count", "direct_source_node_count",
    "direct_source_node_ids", "direct_source_node_names", "exact_canonical_node_ids", "exact_alias_node_ids",
    "matched_node_ids", "coverage_labels", "audit_bucket",
]

def _json_string_list(raw: Any) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _joined(values: Iterable[str]) -> str:
    return ";".join(sorted(set(values)))


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    # ASCII tokens need boundaries so an alias such as AI does not match RAIL.
    if term and all(ord(char) < 128 for char in term):
        return re.compile(r"(?<![A-Za-z0-9])" + escaped + r"(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def exact_node_matches(
    text: str,
    nodes: dict[str, dict[str, str]],
    aliases: dict[str, str],
) -> tuple[set[str], set[str]]:
    """Return exact canonical and alias Node IDs mentioned in *text*.

    Matching is deliberately literal and case-insensitive.  ASCII tokens use
    alphanumeric boundaries; non-ASCII names are matched as exact substrings,
    which is the useful boundary convention for scripts without whitespace.
    """

    canonical: set[str] = set()
    alias_matches: set[str] = set()
    for node_id, node in nodes.items():
        term = str(node.get("canonical_name", "")).strip()
        if term and _term_pattern(term).search(text):
            canonical.add(node_id)
    for alias, node_id in aliases.items():
        if alias and _term_pattern(alias).search(text):
            alias_matches.add(node_id)
    return canonical, alias_matches


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _count_by(conn: sqlite3.Connection, sql: str) -> dict[str, int]:
    return {row[0]: int(row[1]) for row in conn.execute(sql).fetchall()}


def _current_view_counts(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "current_views"):
        return {}
    return _count_by(conn, "SELECT node_id,COUNT(*) FROM current_views WHERE status='official' GROUP BY node_id")


def _hierarchy_depth(rows: list[dict[str, Any]], active_ids: set[str]) -> tuple[int, bool]:
    parents: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row["relation_type"] == "part_of" and row["from_node_id"] in active_ids and row["to_node_id"] in active_ids:
            parents[row["from_node_id"]].append(row["to_node_id"])
    memo: dict[str, int] = {}
    cycle = False

    def depth(node_id: str, trail: set[str]) -> int:
        nonlocal cycle
        if node_id in trail:
            cycle = True
            return 0
        if node_id in memo:
            return memo[node_id]
        next_trail = trail | {node_id}
        value = 0 if not parents.get(node_id) else 1 + max(depth(parent, next_trail) for parent in parents[node_id])
        memo[node_id] = value
        return value

    maximum = max((depth(node_id, set()) for node_id in active_ids), default=0)
    return maximum, cycle


def run_audit(db_path: str | Path) -> dict[str, Any]:
    """Run the deterministic audit and return summary plus CSV-ready rows."""

    query = ReadOnlyQuery(db_path)
    with query.connect() as conn:
        all_nodes = [dict(row) for row in conn.execute(
            "SELECT node_id,canonical_name,primary_type,status FROM nodes ORDER BY node_id"
        ).fetchall()]
        active_nodes = [row for row in all_nodes if row["status"] == "active"]
        active_ids = {row["node_id"] for row in active_nodes}
        node_by_id = {row["node_id"]: row for row in active_nodes}
        alias_rows = [dict(row) for row in conn.execute(
            "SELECT alias,node_id FROM node_aliases ORDER BY alias,node_id"
        ).fetchall()]
        aliases = {row["alias"]: row["node_id"] for row in alias_rows if row["node_id"] in active_ids}
        alias_count_by_node = Counter(row["node_id"] for row in alias_rows if row["node_id"] in active_ids)

        relation_rows = [dict(row) for row in conn.execute(
            "SELECT relation_id,from_node_id,relation_type,to_node_id,status FROM node_relations ORDER BY relation_id"
        ).fetchall()]
        current_relations = [row for row in relation_rows if row["status"] == "current"]
        source_rows = [dict(row) for row in conn.execute(
            "SELECT source_id,title,source_type,source_rank FROM sources ORDER BY source_id"
        ).fetchall()]
        source_by_id = {row["source_id"]: row for row in source_rows}
        source_links = [dict(row) for row in conn.execute(
            "SELECT source_id,node_id,evidence_excerpt,evidence_validation_json FROM source_node_links ORDER BY source_id,node_id"
        ).fetchall()]
        source_nodes: dict[str, set[str]] = defaultdict(set)
        for row in source_links:
            source_nodes[row["source_id"]].add(row["node_id"])
        claim_rows = [dict(row) for row in conn.execute(
            "SELECT claim_id,source_id,statement,evidence_pointer,evidence_excerpt,nature,status,confidence "
            "FROM claims ORDER BY claim_id"
        ).fetchall()]
        claim_links = [dict(row) for row in conn.execute(
            "SELECT claim_id,node_id FROM claim_node_links ORDER BY claim_id,node_id"
        ).fetchall()]
        claim_nodes: dict[str, set[str]] = defaultdict(set)
        for row in claim_links:
            claim_nodes[row["claim_id"]].add(row["node_id"])

        views = _current_view_counts(conn)
        rq_counts = _count_by(conn, "SELECT node_id,COUNT(*) FROM research_questions GROUP BY node_id") if _table_exists(conn, "research_questions") else {}
        gap_counts = _count_by(conn, "SELECT node_id,COUNT(*) FROM knowledge_gaps GROUP BY node_id") if _table_exists(conn, "knowledge_gaps") else {}
        open_gap_count = int(conn.execute("SELECT COUNT(*) FROM knowledge_gaps WHERE status='open'").fetchone()[0]) if _table_exists(conn, "knowledge_gaps") else 0

        claim_relation_evidence: dict[str, int] = defaultdict(int)
        relation_evidence_total = 0
        relation_evidence_current = 0
        relation_evidence_current_supports = 0
        relation_evidence_current_contradicts = 0
        if _table_exists(conn, "relation_evidence_links"):
            relation_status = {row["relation_id"]: row["status"] for row in relation_rows}
            for row in conn.execute("SELECT relation_id,claim_id,evidence_role FROM relation_evidence_links").fetchall():
                relation_id = row["relation_id"]
                claim_id = row["claim_id"]
                claim_relation_evidence[claim_id] += 1
                relation_evidence_total += 1
                if relation_status.get(relation_id) == "current":
                    relation_evidence_current += 1
                    relation_evidence_current_supports += row["evidence_role"] == "supports"
                    relation_evidence_current_contradicts += row["evidence_role"] == "contradicts"

        view_ref_counts: Counter[str] = Counter()
        rq_ref_counts: Counter[str] = Counter()
        gap_ref_counts: Counter[str] = Counter()
        if _table_exists(conn, "current_views"):
            for row in conn.execute("SELECT trigger_claim_ids_json FROM current_views").fetchall():
                view_ref_counts.update(_json_string_list(row[0]))
        if _table_exists(conn, "research_questions"):
            for row in conn.execute("SELECT supporting_claim_ids_json,opposing_claim_ids_json FROM research_questions").fetchall():
                rq_ref_counts.update(_json_string_list(row[0]))
                rq_ref_counts.update(_json_string_list(row[1]))
        if _table_exists(conn, "knowledge_gaps"):
            for row in conn.execute("SELECT source_claim_ids_json FROM knowledge_gaps").fetchall():
                gap_ref_counts.update(_json_string_list(row[0]))

        node_rows: list[dict[str, Any]] = []
        source_link_counts = Counter(row["node_id"] for row in source_links)
        claim_link_counts = Counter(node_id for values in claim_nodes.values() for node_id in values)
        parents = Counter(row["from_node_id"] for row in current_relations if row["relation_type"] == "part_of")
        children = Counter(row["to_node_id"] for row in current_relations if row["relation_type"] == "part_of")
        part_of_in = Counter(row["to_node_id"] for row in current_relations if row["relation_type"] == "part_of")
        part_of_out = Counter(row["from_node_id"] for row in current_relations if row["relation_type"] == "part_of")
        functional = Counter(
            node_id for row in current_relations if row["relation_type"] != "part_of"
            for node_id in (row["from_node_id"], row["to_node_id"])
        )
        for node in sorted(active_nodes, key=lambda row: (row["primary_type"].casefold(), row["canonical_name"].casefold(), row["node_id"])):
            node_rows.append({
                "node_id": node["node_id"], "canonical_name": node["canonical_name"], "primary_type": node["primary_type"],
                "alias_count": alias_count_by_node[node["node_id"]], "parent_count": parents[node["node_id"]],
                "child_count": children[node["node_id"]], "source_count": source_link_counts[node["node_id"]],
                "claim_count": claim_link_counts[node["node_id"]], "current_view_count": views.get(node["node_id"], 0),
                "research_question_count": rq_counts.get(node["node_id"], 0), "knowledge_gap_count": gap_counts.get(node["node_id"], 0),
                "part_of_in_count": part_of_in[node["node_id"]], "part_of_out_count": part_of_out[node["node_id"]],
                "functional_relation_count": functional[node["node_id"]],
            })

        claim_coverage: list[dict[str, Any]] = []
        unlinked_claims: list[dict[str, Any]] = []
        label_counts: Counter[str] = Counter()
        bucket_counts: Counter[str] = Counter()
        high_signal = 0
        for claim in claim_rows:
            source_node_ids = source_nodes.get(claim["source_id"], set())
            text = f"{claim.get('statement') or ''}\n{claim.get('evidence_excerpt') or ''}"
            canonical_ids, alias_ids = exact_node_matches(text, node_by_id, aliases)
            matched_ids = canonical_ids | alias_ids
            labels: list[str] = []
            if len(source_node_ids) == 1:
                labels.append("SOURCE_HAS_SINGLE_NODE")
            elif len(source_node_ids) > 1:
                labels.append("SOURCE_HAS_MULTIPLE_NODES")
            else:
                labels.append("SOURCE_HAS_NO_NODE")
            if canonical_ids:
                labels.append("EXACT_CANONICAL_MENTION")
            if alias_ids:
                labels.append("EXACT_ALIAS_MENTION")
            if len(matched_ids) > 1:
                labels.append("MULTIPLE_EXACT_NODE_MENTIONS")
            if not source_node_ids and not matched_ids:
                labels.append("NO_DETERMINISTIC_NODE_SIGNAL")
            if len(source_node_ids) == 1 and matched_ids == source_node_ids:
                bucket = "HIGH_SIGNAL_REVIEW_CANDIDATE"
                high_signal += 1
            elif source_node_ids or matched_ids:
                bucket = "AMBIGUOUS_REVIEW_CANDIDATE"
            else:
                bucket = "NO_SAFE_SIGNAL"
            for label in labels:
                label_counts[label] += 1
            bucket_counts[bucket] += 1
            source = source_by_id.get(claim["source_id"], {})
            ref_view = view_ref_counts[claim["claim_id"]]
            ref_rq = rq_ref_counts[claim["claim_id"]]
            ref_gap = gap_ref_counts[claim["claim_id"]]
            direct_source_node_names = [
                node_by_id.get(node_id, {}).get("canonical_name", node_id)
                for node_id in sorted(source_node_ids)
            ]
            row = {
                "claim_id": claim["claim_id"], "source_id": claim["source_id"], "source_title": source.get("title", ""),
                "source_type": source.get("source_type", ""), "source_rank": source.get("source_rank", ""),
                "statement": claim.get("statement", ""), "evidence_excerpt": claim.get("evidence_excerpt", ""),
                "nature": claim.get("nature", ""), "status": claim.get("status", ""), "confidence": claim.get("confidence", ""),
                "evidence_pointer": claim.get("evidence_pointer", ""),
                "evidence_pointer_present": int(bool(claim.get("evidence_pointer"))),
                "evidence_excerpt_present": int(bool(claim.get("evidence_excerpt"))),
                "claim_node_link_count": len(claim_nodes.get(claim["claim_id"], set())),
                "relation_evidence_link_count": claim_relation_evidence.get(claim["claim_id"], 0),
                "current_view_trigger_ref_count": ref_view, "research_question_ref_count": ref_rq,
                "knowledge_gap_ref_count": ref_gap, "direct_source_node_count": len(source_node_ids),
                "direct_source_node_ids": _joined(source_node_ids), "direct_source_node_names": _joined(direct_source_node_names),
                "exact_canonical_node_ids": _joined(canonical_ids),
                "exact_alias_node_ids": _joined(alias_ids), "matched_node_ids": _joined(matched_ids),
                "coverage_labels": _joined(labels), "audit_bucket": bucket,
            }
            claim_coverage.append(row)
            if row["claim_node_link_count"] == 0:
                unlinked_claims.append(row)

        source_coverage: list[dict[str, Any]] = []
        for source in source_rows:
            source_claims = [row for row in claim_coverage if row["source_id"] == source["source_id"]]
            source_coverage.append({
                "source_id": source["source_id"], "title": source["title"], "source_type": source["source_type"],
                "source_rank": source["source_rank"], "source_node_link_count": len(source_nodes.get(source["source_id"], set())),
                "claim_count": len(source_claims),
                "node_linked_claim_count": sum(row["claim_node_link_count"] > 0 for row in source_claims),
                "unlinked_claim_count": sum(row["claim_node_link_count"] == 0 for row in source_claims),
            })

        level_counts: Counter[str] = Counter({
            "LEVEL_0_STRUCTURE_ONLY": 0,
            "LEVEL_1_SOURCE_CONNECTED": 0,
            "LEVEL_2_EVIDENCE_CONNECTED": 0,
            "LEVEL_3_CANONICAL_VIEW": 0,
            "LEVEL_4_RESEARCH_ACTIVE": 0,
        })
        for row in node_rows:
            if row["research_question_count"] or row["knowledge_gap_count"]:
                level = "LEVEL_4_RESEARCH_ACTIVE"
            elif row["current_view_count"]:
                level = "LEVEL_3_CANONICAL_VIEW"
            elif row["claim_count"]:
                level = "LEVEL_2_EVIDENCE_CONNECTED"
            elif row["source_count"]:
                level = "LEVEL_1_SOURCE_CONNECTED"
            else:
                level = "LEVEL_0_STRUCTURE_ONLY"
            row["knowledge_level"] = level
            level_counts[level] += 1

        type_coverage: dict[str, dict[str, int]] = {}
        for row in node_rows:
            bucket = type_coverage.setdefault(row["primary_type"], {"active_nodes": 0, "with_sources": 0, "with_claims": 0, "with_current_view": 0, "with_rq": 0, "with_gaps": 0})
            bucket["active_nodes"] += 1
            bucket["with_sources"] += row["source_count"] > 0
            bucket["with_claims"] += row["claim_count"] > 0
            bucket["with_current_view"] += row["current_view_count"] > 0
            bucket["with_rq"] += row["research_question_count"] > 0
            bucket["with_gaps"] += row["knowledge_gap_count"] > 0

        orphan_counts = {}
        for table in ("current_views", "research_questions", "knowledge_gaps"):
            orphan_counts[table] = int(conn.execute(
                f"SELECT COUNT(*) FROM {table} x LEFT JOIN nodes n ON n.node_id=x.node_id WHERE n.node_id IS NULL"
            ).fetchone()[0]) if _table_exists(conn, table) else 0
        hierarchy_max_depth, hierarchy_cycle = _hierarchy_depth(current_relations, active_ids)
        active_relation_node_ids = {
            node_id for row in current_relations for node_id in (row["from_node_id"], row["to_node_id"]) if node_id in active_ids
        }
        summary = {
            "total_nodes": len(all_nodes), "active_nodes": len(active_nodes), "inactive_nodes": len(all_nodes) - len(active_nodes),
            "alias_count": len(alias_rows), "active_alias_count": sum(alias_count_by_node.values()),
            "nodes_with_aliases": sum(row["alias_count"] > 0 for row in node_rows), "nodes_without_aliases": sum(row["alias_count"] == 0 for row in node_rows),
            "current_relations": len(current_relations), "current_part_of": sum(row["relation_type"] == "part_of" for row in current_relations),
            "current_functional_relations": sum(row["relation_type"] != "part_of" for row in current_relations),
            "relation_type_breakdown": dict(sorted(Counter(row["relation_type"] for row in current_relations).items())),
            "node_relations_total": len(relation_rows), "retired_relations": len(relation_rows) - len(current_relations),
            "relation_evidence_links": relation_evidence_total, "current_relation_evidence_links": relation_evidence_current,
            "current_relation_support_links": relation_evidence_current_supports,
            "current_relation_contradict_links": relation_evidence_current_contradicts,
            "non_current_relation_evidence_links": relation_evidence_total - relation_evidence_current,
            "source_node_links_with_evidence_excerpt": sum(bool(row.get("evidence_excerpt")) for row in source_links),
            "source_node_links_with_validation_json": sum(row.get("evidence_validation_json") not in (None, "", "{}") for row in source_links),
            "sources": len(source_rows), "claims": len(claim_rows), "claim_node_links": len(claim_links),
            "claims_with_evidence_pointer": sum(bool(row.get("evidence_pointer")) for row in claim_rows),
            "claims_with_evidence_excerpt": sum(bool(row.get("evidence_excerpt")) for row in claim_rows),
            "claims_with_existing_source": sum(row["source_id"] in source_by_id for row in claim_rows),
            "claims_with_direct_source_node_context": sum(bool(source_nodes.get(row["source_id"])) for row in claim_rows),
            "claims_with_node_link": sum(bool(claim_nodes.get(row["claim_id"])) for row in claim_rows),
            "current_views": sum(views.values()), "research_questions": sum(rq_counts.values()), "knowledge_gaps": sum(gap_counts.values()),
            "open_knowledge_gaps": open_gap_count, "node_coverage": {
                "with_sources": sum(row["source_count"] > 0 for row in node_rows), "with_claims": sum(row["claim_count"] > 0 for row in node_rows),
                "with_current_view": sum(row["current_view_count"] > 0 for row in node_rows), "with_rq": sum(row["research_question_count"] > 0 for row in node_rows),
                "with_gaps": sum(row["knowledge_gap_count"] > 0 for row in node_rows),
            },
            "knowledge_level_distribution": dict(sorted(level_counts.items())),
            "coverage_label_distribution": dict(sorted(label_counts.items())), "audit_bucket_distribution": dict(sorted(bucket_counts.items())),
            "unlinked_claims": len(unlinked_claims), "high_signal_review_candidates": high_signal,
            "ambiguous_review_candidates": bucket_counts["AMBIGUOUS_REVIEW_CANDIDATE"], "no_safe_signal": bucket_counts["NO_SAFE_SIGNAL"],
            "exact_canonical_matches": sum(bool(row["exact_canonical_node_ids"]) for row in claim_coverage),
            "exact_alias_matches": sum(bool(row["exact_alias_node_ids"]) for row in claim_coverage),
            "multi_node_matches": sum(len(row["matched_node_ids"].split(";")) > 1 for row in claim_coverage if row["matched_node_ids"]),
            "orphan_view_count": orphan_counts["current_views"], "orphan_research_question_count": orphan_counts["research_questions"],
            "orphan_knowledge_gap_count": orphan_counts["knowledge_gaps"], "nodes_with_current_relation": len(active_relation_node_ids),
            "roots_no_parent": sum(row["parent_count"] == 0 for row in node_rows), "leaves_no_child": sum(row["child_count"] == 0 for row in node_rows),
            "completely_isolated_nodes": sum(sum(row[field] for field in ("parent_count", "child_count", "source_count", "claim_count", "current_view_count", "research_question_count", "knowledge_gap_count", "functional_relation_count")) == 0 for row in node_rows),
            "hierarchy_max_depth": hierarchy_max_depth, "hierarchy_cycle_detected": hierarchy_cycle,
            "type_coverage": type_coverage,
        }
        linked_claims = sum(row["claim_node_link_count"] > 0 for row in claim_coverage)
        if not claim_rows or not summary["claims_with_evidence_excerpt"]:
            readiness = "NO"
        elif linked_claims == len(claim_rows):
            readiness = "YES"
        elif high_signal:
            readiness = "PARTIAL"
        else:
            readiness = "NO"
        summary["claim_node_activation_ready"] = readiness
        return {"summary": summary, "node_coverage": node_rows, "source_coverage": source_coverage, "claim_coverage": claim_coverage, "unlinked_claims": unlinked_claims}


def write_csv_outputs(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    specs = (
        ("node_coverage.csv", NODE_FIELDS, result["node_coverage"]),
        ("source_coverage.csv", SOURCE_FIELDS, result["source_coverage"]),
        ("claim_coverage.csv", CLAIM_FIELDS, result["claim_coverage"]),
        ("unlinked_claims.csv", CLAIM_FIELDS, result["unlinked_claims"]),
    )
    paths: list[Path] = []
    for filename, fields, rows in specs:
        path = output / filename
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the read-only Phase 2 knowledge coverage audit")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--db", type=Path, default=None, help="Optional database path override")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/phase2_3b"))
    args = parser.parse_args(argv)
    db_path = args.db or load_config(args.config).db_path
    result = run_audit(db_path)
    write_csv_outputs(result, args.output_dir)
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
