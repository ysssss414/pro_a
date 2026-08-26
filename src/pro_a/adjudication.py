"""Read-only Claim-to-Node human adjudication package generation.

This module prepares reviewer inputs for unlinked Claims.  It never applies a
decision, creates a link or proposal, or opens a writable database connection.
Candidate Nodes are limited to direct Source links and exact canonical/alias
signals, using the same matcher as the Phase 2.3B coverage audit.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import load_config
from .coverage import exact_node_matches
from .query import ReadOnlyQuery


DECISIONS = ("PENDING", "LINK", "MULTI_LINK", "NO_LINK", "DEFER")
CSV_FIELDS = [
    "claim_id",
    "source_id",
    "source_title",
    "statement",
    "evidence_excerpt",
    "source_linked_nodes",
    "exact_canonical_matches",
    "exact_alias_matches",
    "candidate_node_ids",
    "candidate_node_names",
    "candidate_signals",
    "decision",
    "selected_node_ids",
    "reviewer_note",
]


@dataclass(frozen=True)
class Candidate:
    node_id: str
    canonical_name: str
    primary_type: str
    signals: tuple[str, ...]
    matched_aliases: tuple[str, ...]


@dataclass(frozen=True)
class ReviewItem:
    claim_id: str
    source_id: str
    source_title: str
    organization: str
    publication_time: str
    statement: str
    evidence_excerpt: str
    nature: str
    status: str
    confidence: Any
    evidence_pointer: str
    source_linked_node_ids: tuple[str, ...]
    exact_canonical_node_ids: tuple[str, ...]
    exact_alias_node_ids: tuple[str, ...]
    candidates: tuple[Candidate, ...]
    decision: str = "PENDING"
    selected_node_ids: str = ""
    reviewer_note: str = ""


def _sorted_ids(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _candidate_signals(candidate: Candidate) -> str:
    return " / ".join(candidate.signals)


def _candidate_signal_json(candidates: Iterable[Candidate]) -> str:
    return json.dumps(
        [
            {
                "node_id": candidate.node_id,
                "signals": list(candidate.signals),
                "matched_aliases": list(candidate.matched_aliases),
            }
            for candidate in candidates
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _load_review_items(db_path: str | Path) -> list[ReviewItem]:
    query = ReadOnlyQuery(db_path)
    with query.connect() as conn:
        node_rows = [
            dict(row)
            for row in conn.execute(
                """SELECT node_id,canonical_name,primary_type
                   FROM nodes WHERE status='active'
                   ORDER BY node_id"""
            ).fetchall()
        ]
        nodes = {row["node_id"]: row for row in node_rows}
        alias_rows = [
            dict(row)
            for row in conn.execute(
                """SELECT a.alias,a.node_id
                   FROM node_aliases a JOIN nodes n ON n.node_id=a.node_id
                   WHERE n.status='active'
                   ORDER BY a.alias,a.node_id"""
            ).fetchall()
        ]
        aliases = {row["alias"]: row["node_id"] for row in alias_rows}

        source_rows = {
            row["source_id"]: dict(row)
            for row in conn.execute(
                """SELECT source_id,title,organization,publication_time
                   FROM sources ORDER BY source_id"""
            ).fetchall()
        }
        source_links: dict[str, set[str]] = defaultdict(set)
        for row in conn.execute(
            """SELECT snl.source_id,snl.node_id
               FROM source_node_links snl JOIN nodes n ON n.node_id=snl.node_id
               WHERE n.status='active'
               ORDER BY snl.source_id,snl.node_id"""
        ).fetchall():
            source_links[row["source_id"]].add(row["node_id"])

        linked_claim_ids = {
            row["claim_id"]
            for row in conn.execute("SELECT DISTINCT claim_id FROM claim_node_links").fetchall()
        }
        claim_rows = [
            dict(row)
            for row in conn.execute(
                """SELECT claim_id,source_id,statement,evidence_excerpt,nature,status,
                          confidence,evidence_pointer
                   FROM claims ORDER BY claim_id"""
            ).fetchall()
            if row["claim_id"] not in linked_claim_ids
        ]

    items: list[ReviewItem] = []
    for claim in claim_rows:
        source_node_ids = source_links.get(claim["source_id"], set())
        text = f"{claim.get('statement') or ''}\n{claim.get('evidence_excerpt') or ''}"
        canonical_ids, alias_ids = exact_node_matches(text, nodes, aliases)
        candidate_ids = source_node_ids | canonical_ids | alias_ids
        candidates: list[Candidate] = []
        for node_id in sorted(
            candidate_ids,
            key=lambda value: (
                str(nodes[value]["canonical_name"]).casefold(),
                str(nodes[value]["canonical_name"]),
                value,
            ),
        ):
            signals = tuple(
                signal
                for signal, present in (
                    ("SOURCE_LINK", node_id in source_node_ids),
                    ("EXACT_CANONICAL", node_id in canonical_ids),
                    ("EXACT_ALIAS", node_id in alias_ids),
                )
                if present
            )
            matched_aliases = tuple(
                sorted(
                    (
                        alias
                        for alias, alias_node_id in aliases.items()
                        if alias_node_id == node_id
                        and alias_node_id in alias_ids
                        and exact_node_matches(text, {}, {alias: alias_node_id})[1]
                    ),
                    key=lambda value: (value.casefold(), value),
                )
            )
            candidates.append(
                Candidate(
                    node_id=node_id,
                    canonical_name=nodes[node_id]["canonical_name"],
                    primary_type=nodes[node_id]["primary_type"],
                    signals=signals,
                    matched_aliases=matched_aliases,
                )
            )
        source = source_rows.get(claim["source_id"], {})
        items.append(
            ReviewItem(
                claim_id=claim["claim_id"],
                source_id=claim["source_id"],
                source_title=source.get("title", ""),
                organization=source.get("organization", ""),
                publication_time=source.get("publication_time", ""),
                statement=claim.get("statement", ""),
                evidence_excerpt=claim.get("evidence_excerpt", ""),
                nature=claim.get("nature", ""),
                status=claim.get("status", ""),
                confidence=claim.get("confidence", ""),
                evidence_pointer=claim.get("evidence_pointer", ""),
                source_linked_node_ids=_sorted_ids(source_node_ids),
                exact_canonical_node_ids=_sorted_ids(canonical_ids),
                exact_alias_node_ids=_sorted_ids(alias_ids),
                candidates=tuple(candidates),
            )
        )
    return items


def build_package(db_path: str | Path) -> dict[str, Any]:
    """Read the current database and build a reviewer-only package."""

    items = _load_review_items(db_path)
    package = {"items": items, "claim_count": len(items)}
    validate_package(package, db_path)
    return package


def _csv_row(item: ReviewItem) -> dict[str, str]:
    return {
        "claim_id": item.claim_id,
        "source_id": item.source_id,
        "source_title": item.source_title,
        "statement": item.statement,
        "evidence_excerpt": item.evidence_excerpt,
        "source_linked_nodes": ";".join(item.source_linked_node_ids),
        "exact_canonical_matches": ";".join(item.exact_canonical_node_ids),
        "exact_alias_matches": ";".join(item.exact_alias_node_ids),
        "candidate_node_ids": ";".join(candidate.node_id for candidate in item.candidates),
        "candidate_node_names": ";".join(candidate.canonical_name for candidate in item.candidates),
        "candidate_signals": _candidate_signal_json(item.candidates),
        "decision": item.decision,
        "selected_node_ids": item.selected_node_ids,
        "reviewer_note": item.reviewer_note,
    }


def write_csv(package: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(_csv_row(item) for item in package["items"])
    return output


def _quote(text: str) -> str:
    if not text:
        return ">"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def render_markdown(package: dict[str, Any]) -> str:
    items: list[ReviewItem] = package["items"]
    lines = [
        f"# Phase 2.3C Claim–Node Human Adjudication Package",
        "",
        f"This package contains {len(items)} unlinked Claims requiring human adjudication.",
        "No Claim→Node decisions in this document are machine-approved.",
        "Production has not been modified.",
        "",
        "Every review item defaults to `decision = PENDING`. Allowed human decisions are `LINK`, `MULTI_LINK`, `NO_LINK`, and `DEFER`.",
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"## {item.claim_id}",
                "",
                "Source",
                f"- source_id: {item.source_id}",
                f"- title: {item.source_title}",
                f"- organization: {item.organization}",
                f"- publication_time: {item.publication_time}",
                "",
                "Claim",
                f"- statement: {item.statement}",
                f"- nature: {item.nature}",
                f"- status: {item.status}",
                f"- confidence: {item.confidence}",
                "",
                "Evidence",
                _quote(item.evidence_excerpt),
                "",
                "Candidate Nodes",
                "",
            ]
        )
        if item.candidates:
            for index, candidate in enumerate(item.candidates, start=1):
                lines.extend(
                    [
                        f"{index}. {candidate.canonical_name}",
                        f"   - node_id: {candidate.node_id}",
                        f"   - type: {candidate.primary_type}",
                        f"   - signals: {_candidate_signals(candidate)}",
                    ]
                )
                if candidate.matched_aliases:
                    lines.append(f"   - matched_alias: {', '.join(candidate.matched_aliases)}")
        else:
            lines.append("No deterministic candidate Node was found.")
        lines.extend(
            [
                "",
                "Human Decision",
                f"- Decision: {item.decision}",
                f"- Selected Node IDs: {item.selected_node_ids}",
                f"- Reviewer Note: {item.reviewer_note}",
                "",
            ]
        )
    return "\n".join(lines)


def write_markdown(package: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(package), encoding="utf-8")
    return output


def validate_package(package: dict[str, Any], db_path: str | Path) -> None:
    """Validate completeness and reproducibility without writing to SQLite."""

    items: list[ReviewItem] = package["items"]
    if len({item.claim_id for item in items}) != len(items):
        raise ValueError("duplicate claim_id in adjudication package")
    if any(item.decision not in DECISIONS for item in items):
        raise ValueError("invalid human decision value")
    if any(item.decision != "PENDING" for item in items):
        raise ValueError("all generated decisions must remain PENDING")
    if any(item.selected_node_ids or item.reviewer_note for item in items):
        raise ValueError("generated package must not prefill reviewer fields")
    expected = _load_review_items(db_path)
    if [item.claim_id for item in items] != [item.claim_id for item in expected]:
        raise ValueError("package Claim set does not match current unlinked Claims")
    for actual, expected_item in zip(items, expected):
        if actual != expected_item:
            raise ValueError(f"package is not reproducible for {actual.claim_id}")
        with ReadOnlyQuery(db_path).connect() as conn:
            rows = conn.execute(
                """SELECT n.node_id,n.status FROM nodes n
                   WHERE n.node_id IN ({})""".format(
                    ",".join("?" for _ in actual.candidates) or "NULL"
                ),
                tuple(candidate.node_id for candidate in actual.candidates),
            ).fetchall()
        if len(rows) != len(actual.candidates) or any(row["status"] != "active" for row in rows):
            raise ValueError(f"candidate Node set is not active for {actual.claim_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a read-only Claim-to-Node human adjudication package")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--markdown", type=Path, default=Path("docs/PHASE2_3C_CLAIM_NODE_ADJUDICATION.md"))
    parser.add_argument("--csv", dest="csv_path", type=Path, default=Path("artifacts/phase2_3c/claim_node_adjudication.csv"))
    args = parser.parse_args(argv)
    db_path = args.db or load_config(args.config).db_path
    package = build_package(db_path)
    write_markdown(package, args.markdown)
    write_csv(package, args.csv_path)
    print(json.dumps({"unlinked_claims": package["claim_count"], "decision": "PENDING"}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
