"""Read-only Phase 2.3E entity-granularity and Claim-attribution review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .claim_node_activation import EXPECTED_SOURCE_ID, LINK_CLAIM_IDS, TARGET_NODE_ID
from .constants import NODE_TYPES


COMPANY_NAME = "昀冢科技"
MLCC_NAME = "MLCC"
ALLOWED_CLASSES = {
    "MLCC_PRIMARY",
    "COMPANY_PRIMARY_MLCC_CONTEXT",
    "COMPANY_PRIMARY",
    "AMBIGUOUS",
}

# This is a frozen human review input, not an NLP classifier.  The reasons are
# deliberately tied to the stored Claim statement/evidence and Source title.
REVIEW_DECISIONS: dict[str, dict[str, Any]] = {
    "CLM_20260814_0B6E52F8": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "昀冢科技是显式主体；新扩产中的产品结构是公司经营事实，"
            "MLCC 只表示产品/业务上下文。"
        ),
    },
    "CLM_20260814_541F5C31": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "昀冢科技一期产线的出货量、爬坡和满产时间是公司产能事实，"
            "MLCC 是该产线的产品上下文。"
        ),
    },
    "CLM_20260814_8E4B9E25": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "二期投资和量产计划直接陈述昀冢科技的资本开支与产能，"
            "不能升格为 MLCC 行业总产能。"
        ),
    },
    "CLM_20260814_939CAEDD": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "statement 与 evidence 都将量产提前及扩产计划归于公司；"
            "高容/超高容 MLCC 是上下文。"
        ),
    },
    "CLM_20260814_980FA010": {
        "attribution_class": "MLCC_PRIMARY",
        "reason": (
            "statement 与 evidence 直接陈述 MLCC 价格环比变化，"
            "未将公司营收、产能或投资写成产品整体事实。"
        ),
    },
    "CLM_20260814_9A069D06": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "三期投资、量产爬坡和公司月产能直接以昀冢科技为主体；"
            "MLCC 是产品上下文。"
        ),
    },
    "CLM_20260814_BA7AC415": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "认证和实验室进度属于昀冢科技的车规级高容产品，"
            "不能解释为整个 MLCC 产品类别已完成认证。"
        ),
    },
    "CLM_20260814_BAED6789": {
        "attribution_class": "MLCC_PRIMARY",
        "reason": "Claim 直接比较本轮与上一轮 MLCC 行业周期持续期。",
    },
    "CLM_20260814_D2C7FCD1": {
        "attribution_class": "MLCC_PRIMARY",
        "reason": (
            "Claim 比较国内外 MLCC 原厂并陈述 AI 挤出效应，"
            "事实层级是行业/产品趋势。"
        ),
    },
    "CLM_20260814_E1A48290": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "营收必须归属于报告主体；Source 标题限定昀冢科技，"
            "且 evidence 没有行业汇总口径，因此 MLCC 只是业务上下文。"
        ),
    },
    "CLM_20260814_E53B8E9C": {
        "attribution_class": "COMPANY_PRIMARY_MLCC_CONTEXT",
        "reason": (
            "昀冢科技/公司是原预判的显式主体；MLCC 上行周期是该公司判断的上下文，"
            "不应丢失公司 attribution。"
        ),
    },
}

REVIEW_FIELDS = (
    "claim_id",
    "statement",
    "evidence_excerpt",
    "source_id",
    "source_title",
    "current_linked_nodes",
    "primary_subject_candidate",
    "context_node_candidates",
    "mention_only_candidates",
    "attribution_class",
    "mlcc_semantic_role",
    "reason",
    "mlcc_link_should_remain",
    "company_link_should_exist",
    "current_view_eligible",
)

PROPOSAL_FIELDS = (
    "claim_id",
    "current_mlcc_link",
    "proposed_primary_subject",
    "proposed_context",
    "recommended_action",
)


class EntityGranularityError(RuntimeError):
    """The frozen review target or read-only invariant was not satisfied."""


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _connect_read_only(db_path: str | Path) -> sqlite3.Connection:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def lookup_company_node(
    db_path: str | Path,
    name: str = COMPANY_NAME,
) -> dict[str, Any]:
    """Resolve only exact canonical/alias matches; substring rows are diagnostics."""
    with _connect_read_only(db_path) as conn:
        canonical = [
            dict(row)
            for row in conn.execute(
                """SELECT node_id,canonical_name,primary_type,status
                   FROM nodes WHERE canonical_name=? COLLATE NOCASE
                   ORDER BY node_id""",
                (name,),
            ).fetchall()
        ]
        aliases = [
            dict(row)
            for row in conn.execute(
                """SELECT a.alias,a.node_id,n.canonical_name,n.primary_type,n.status
                   FROM node_aliases a JOIN nodes n ON n.node_id=a.node_id
                   WHERE a.alias=? COLLATE NOCASE
                   ORDER BY a.node_id""",
                (name,),
            ).fetchall()
        ]
        matched_ids = sorted(
            {row["node_id"] for row in canonical}
            | {row["node_id"] for row in aliases}
        )
        matched_nodes: list[dict[str, Any]] = []
        if matched_ids:
            placeholders = ",".join("?" for _ in matched_ids)
            rows = conn.execute(
                f"""SELECT node_id,canonical_name,primary_type,status
                    FROM nodes WHERE node_id IN ({placeholders}) ORDER BY node_id""",
                matched_ids,
            ).fetchall()
            for row in rows:
                item = dict(row)
                item["aliases"] = [
                    alias_row[0]
                    for alias_row in conn.execute(
                        "SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias",
                        (item["node_id"],),
                    ).fetchall()
                ]
                matched_nodes.append(item)
        substring_nodes = [
            dict(row)
            for row in conn.execute(
                """SELECT node_id,canonical_name,primary_type,status
                   FROM nodes WHERE instr(canonical_name, ?) > 0
                   ORDER BY node_id""",
                (name[:2],),
            ).fetchall()
        ]
        substring_aliases = [
            dict(row)
            for row in conn.execute(
                """SELECT a.alias,a.node_id,n.canonical_name,n.primary_type,n.status
                   FROM node_aliases a JOIN nodes n ON n.node_id=a.node_id
                   WHERE instr(a.alias, ?) > 0 ORDER BY a.alias,a.node_id""",
                (name[:2],),
            ).fetchall()
        ]
    return {
        "query": name,
        "match_method": "exact canonical_name or exact alias, NOCASE; no fuzzy match",
        "exists": bool(matched_ids),
        "canonical_exact_matches": canonical,
        "alias_exact_matches": aliases,
        "matched_nodes": matched_nodes,
        "duplicate_exact_match": len(matched_ids) > 1,
        "deterministic_substring_diagnostics": {
            "canonical_name": substring_nodes,
            "aliases": substring_aliases,
        },
    }


def _validate_review_decisions() -> None:
    if set(REVIEW_DECISIONS) != set(LINK_CLAIM_IDS):
        raise EntityGranularityError("Phase 2.3E review allowlist mismatch")
    invalid = sorted(
        claim_id
        for claim_id, decision in REVIEW_DECISIONS.items()
        if decision["attribution_class"] not in ALLOWED_CLASSES
    )
    if invalid:
        raise EntityGranularityError(
            f"invalid attribution class for Claims: {','.join(invalid)}"
        )


def review_claims(db_path: str | Path) -> dict[str, Any]:
    """Apply the frozen human decisions to the exact Phase 2.3D Production rows."""
    _validate_review_decisions()
    placeholders = ",".join("?" for _ in LINK_CLAIM_IDS)
    with _connect_read_only(db_path) as conn:
        claim_rows = conn.execute(
            f"""SELECT c.claim_id,c.statement,c.evidence_excerpt,c.source_id,
                       s.title AS source_title
                FROM claims c JOIN sources s ON s.source_id=c.source_id
                WHERE c.claim_id IN ({placeholders}) ORDER BY c.claim_id""",
            LINK_CLAIM_IDS,
        ).fetchall()
        if len(claim_rows) != len(LINK_CLAIM_IDS):
            found = {row["claim_id"] for row in claim_rows}
            missing = sorted(set(LINK_CLAIM_IDS) - found)
            raise EntityGranularityError(
                f"Phase 2.3E target Claims missing: {','.join(missing)}"
            )
        if any(row["source_id"] != EXPECTED_SOURCE_ID for row in claim_rows):
            raise EntityGranularityError("Phase 2.3E Claim Source identity drift")

        links = conn.execute(
            f"""SELECT cnl.claim_id,cnl.node_id,n.canonical_name,cnl.role
                FROM claim_node_links cnl JOIN nodes n ON n.node_id=cnl.node_id
                WHERE cnl.claim_id IN ({placeholders})
                ORDER BY cnl.claim_id,cnl.node_id""",
            LINK_CLAIM_IDS,
        ).fetchall()
        links_by_claim: dict[str, list[dict[str, Any]]] = {
            claim_id: [] for claim_id in LINK_CLAIM_IDS
        }
        for link in links:
            links_by_claim[link["claim_id"]].append(dict(link))
        for claim_id in LINK_CLAIM_IDS:
            if links_by_claim[claim_id] != [
                {
                    "claim_id": claim_id,
                    "node_id": TARGET_NODE_ID,
                    "canonical_name": MLCC_NAME,
                    "role": "related",
                }
            ]:
                raise EntityGranularityError(
                    f"Phase 2.3D link drift for Claim: {claim_id}"
                )
        role_values = [
            {"role": row["role"], "count": row["count"]}
            for row in conn.execute(
                """SELECT role,COUNT(*) AS count FROM claim_node_links
                   GROUP BY role ORDER BY role"""
            ).fetchall()
        ]

    rows: list[dict[str, str]] = []
    for claim in claim_rows:
        claim_id = claim["claim_id"]
        decision = REVIEW_DECISIONS[claim_id]
        classification = decision["attribution_class"]
        company_primary = classification in {
            "COMPANY_PRIMARY_MLCC_CONTEXT",
            "COMPANY_PRIMARY",
        }
        mlcc_primary = classification == "MLCC_PRIMARY"
        link_text = ";".join(
            f'{link["node_id"]}|{link["canonical_name"]}|{link["role"]}'
            for link in links_by_claim[claim_id]
        )
        rows.append(
            {
                "claim_id": claim_id,
                "statement": claim["statement"],
                "evidence_excerpt": claim["evidence_excerpt"],
                "source_id": claim["source_id"],
                "source_title": claim["source_title"],
                "current_linked_nodes": link_text,
                "primary_subject_candidate": MLCC_NAME if mlcc_primary else COMPANY_NAME,
                "context_node_candidates": (
                    f"{TARGET_NODE_ID}|{MLCC_NAME}"
                    if classification == "COMPANY_PRIMARY_MLCC_CONTEXT"
                    else ""
                ),
                "mention_only_candidates": "",
                "attribution_class": classification,
                "mlcc_semantic_role": "PRIMARY_SUBJECT" if mlcc_primary else "CONTEXT",
                "reason": decision["reason"],
                "mlcc_link_should_remain": "true",
                "company_link_should_exist": "true" if company_primary else "false",
                "current_view_eligible": "true" if mlcc_primary else "false",
            }
        )
    counts = {
        classification: sum(
            row["attribution_class"] == classification for row in rows
        )
        for classification in sorted(ALLOWED_CLASSES)
    }
    return {"rows": rows, "counts": counts, "role_values": role_values}


def build_company_node_proposal(
    review_rows: list[dict[str, str]],
    company_lookup: dict[str, Any],
) -> dict[str, Any] | None:
    if company_lookup["exists"]:
        return None
    supporting = [
        row["claim_id"]
        for row in review_rows
        if row["company_link_should_exist"] == "true"
    ]
    if not supporting:
        return None
    if "Entity" not in NODE_TYPES or "Company" in NODE_TYPES:
        raise EntityGranularityError("frozen Node Type convention drift")
    return {
        "canonical_name": COMPANY_NAME,
        "proposed_type": "Company",
        "primary_type": "Entity",
        "entity_kind": "Company",
        "type_rationale": (
            "Company is not a frozen primary_type; the existing frozen company-compatible "
            "primary_type is Entity."
        ),
        "explicit_aliases": [],
        "supporting_claim_ids": supporting,
        "source_ids": sorted({row["source_id"] for row in review_rows}),
        "reason": (
            "Production has no exact canonical/alias match for 昀冢科技, while eight reviewed "
            "Claims have the company as PRIMARY_SUBJECT and MLCC as CONTEXT."
        ),
        "production_write_authorized": False,
    }


def build_claim_attribution_proposals(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    proposals: list[dict[str, str]] = []
    for row in review_rows:
        classification = row["attribution_class"]
        if classification == "MLCC_PRIMARY":
            action = "KEEP_MLCC_ONLY"
            primary_subject = MLCC_NAME
            context = ""
        elif classification == "COMPANY_PRIMARY_MLCC_CONTEXT":
            action = "ADD_COMPANY_REVIEW_MLCC_ROLE"
            primary_subject = COMPANY_NAME
            context = MLCC_NAME
        else:
            action = "DEFER"
            primary_subject = row["primary_subject_candidate"]
            context = row["context_node_candidates"]
        proposals.append(
            {
                "claim_id": row["claim_id"],
                "current_mlcc_link": row["current_linked_nodes"],
                "proposed_primary_subject": primary_subject,
                "proposed_context": context,
                "recommended_action": action,
            }
        )
    return proposals


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _format_ids(rows: list[dict[str, str]], eligible: bool) -> str:
    wanted = "true" if eligible else "false"
    return ", ".join(
        f'`{row["claim_id"]}`'
        for row in rows
        if row["current_view_eligible"] == wanted
    )


def _build_report(
    db_sha: str,
    lookup: dict[str, Any],
    review: dict[str, Any],
    node_proposal: dict[str, Any] | None,
) -> str:
    rows = review["rows"]
    counts = review["counts"]
    node_exists = "YES" if lookup["exists"] else "NO"
    company_needed = "YES" if node_proposal is not None else "NO"
    role_values = ", ".join(
        f'{row["role"]} ({row["count"]})' for row in review["role_values"]
    ) or "none"
    table_rows = "\n".join(
        "| {claim_id} | {attribution_class} | {primary_subject_candidate} | "
        "{mlcc_semantic_role} | {current_view_eligible} | {reason} |".format(**row)
        for row in rows
    )
    return f"""# Phase 2.3E — Entity Granularity & Claim Attribution Review

YUNZHONG_TECH_NODE_EXISTS = {node_exists}
COMPANY_NODE_NEEDED = {company_needed}
ROLE_MODEL_SUFFICIENT = NO
MLCC_CURRENT_VIEW_READY = PARTIAL

## Executive conclusion

The deterministic lookup found no exact `canonical_name` or `node_aliases.alias` match for
`{COMPANY_NAME}`. The 11 Phase 2.3D Claims divide into {counts['MLCC_PRIMARY']}
`MLCC_PRIMARY` and {counts['COMPANY_PRIMARY_MLCC_CONTEXT']}
`COMPANY_PRIMARY_MLCC_CONTEXT`; no Claim was forced into `COMPANY_PRIMARY` or `AMBIGUOUS`.
The existing MLCC links should remain, but their semantic meaning is primary subject for
three Claims and context for eight Claims.

The Company Node proposal uses frozen `primary_type=Entity`; `Company` is recorded as the
entity kind/proposed business category because `Company` is not an allowed frozen Node Type.
No alias is proposed: the only explicit company string is identical to the proposed canonical
name.

## Deterministic Company Node lookup

- Exact canonical matches: {len(lookup['canonical_exact_matches'])}
- Exact alias matches: {len(lookup['alias_exact_matches'])}
- Duplicate exact match: `{str(lookup['duplicate_exact_match']).lower()}`
- Deterministic `昀冢` substring diagnostics: canonical
  {len(lookup['deterministic_substring_diagnostics']['canonical_name'])}, aliases
  {len(lookup['deterministic_substring_diagnostics']['aliases'])}
- Fuzzy matching, entity resolution, web research and inferred aliases were not used.

## Claim attribution review

`current_view_eligible` below is the entity-granularity gate only. Any later Current View
proposal must still pass the frozen Evidence, attribution and governance validators.

| Claim | Class | Primary subject | MLCC semantic role | Current View eligible | Reason |
|---|---|---|---|---|---|
{table_rows}

Eligible Claim IDs: {_format_ids(rows, True)}

Ineligible Claim IDs: {_format_ids(rows, False)}

## `claim_node_links.role` audit

- Production distinct values: `{role_values}`.
- Schema: `claim_node_links.role` is unconstrained text with default `related`; there is no
  subject/context enum or CHECK constraint.
- Read API: Node Claims select membership without returning role. Source Detail exposes the
  stored role as an opaque string; provenance also carries it without interpreting semantics.
- Frontend: role is typed and rendered as a plain string; no subject/context filtering exists.
- Coverage: Claim coverage and knowledge levels count link existence and ignore role semantics.
- Validators/write paths: Phase 1 ingestion/proposal paths and Phase 2.3D write `related` for
  Claim links. Existing `primary`/`related` validation in Analyzer applies to Source-to-Node
  matches, not a governed Claim subject/context model.

`ROLE_MODEL_SUFFICIENT = NO`: the current value cannot distinguish three MLCC-primary links
from eight MLCC-context links. A minimal future contract is `subject`, `context`, `related`,
but it must be frozen and implemented consistently before any role mutation.

## Current View gate

`MLCC_CURRENT_VIEW_READY = PARTIAL`. The explicit three-Claim allowlist can safely pass the
entity-granularity gate, but selecting all 11 Claims by `node_id=MLCC` is unsafe because the
persisted role does not encode subject versus context. This phase does not generate a Current
View.

## Proposed next write package (not authorized here)

1. Human-review and create one canonical `{COMPANY_NAME}` Node using
   frozen `primary_type=Entity`; do not add unobserved aliases.
2. Freeze minimal Claim-link role semantics and update schema/read/coverage/write validation
   together.
3. Add Company subject links for the eight company-primary Claims; retain all MLCC links and
   review those eight MLCC roles as context. Keep the three MLCC-primary Claims as MLCC subject.
4. Re-run integrity, foreign-key, coverage and Current View eligibility checks before any
   governed Current View proposal.

`PRODUCTION_WRITE_AUTHORIZED = false`.

## Read-only invariance

- Production pre-SHA: `{db_sha}`
- Production post-SHA at artifact generation: `{db_sha}`
- Company Node proposal generated: `{str(node_proposal is not None).lower()}`
- Production rows changed: `false`

## Scope exclusions

No Node/Alias/Claim/link/role/View/RQ/Gap/Relation/schema/API/frontend mutation was performed.
No LLM, embedding, RAG or web call was used.
"""


def generate_review_package(
    db_path: str | Path,
    artifact_dir: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    db = Path(db_path)
    pre_sha = file_sha256(db)
    lookup = lookup_company_node(db)
    review = review_claims(db)
    node_proposal = build_company_node_proposal(review["rows"], lookup)
    attribution_proposals = build_claim_attribution_proposals(review["rows"])

    output_dir = Path(artifact_dir)
    review_csv = output_dir / "claim_attribution_review.csv"
    node_json = output_dir / "company_node_proposal.json"
    proposal_csv = output_dir / "claim_attribution_proposal.csv"
    _write_csv(review_csv, REVIEW_FIELDS, review["rows"])
    if node_proposal is not None:
        node_json.parent.mkdir(parents=True, exist_ok=True)
        node_json.write_text(
            json.dumps(node_proposal, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _write_csv(proposal_csv, PROPOSAL_FIELDS, attribution_proposals)
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        _build_report(pre_sha, lookup, review, node_proposal), encoding="utf-8"
    )
    post_sha = file_sha256(db)
    if post_sha != pre_sha:
        raise EntityGranularityError("Production database changed during read-only review")
    return {
        "pre_sha": pre_sha,
        "post_sha": post_sha,
        "production_db_changed": False,
        "lookup": lookup,
        "review": review,
        "company_node_proposal": node_proposal,
        "claim_attribution_proposals": attribution_proposals,
        "paths": {
            "review_csv": str(review_csv),
            "company_node_proposal": str(node_json) if node_proposal else "",
            "claim_attribution_proposal": str(proposal_csv),
            "report": str(report),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="workspace/pro_a.db")
    parser.add_argument("--artifact-dir", default="artifacts/phase2_3e")
    parser.add_argument(
        "--report", default="docs/PHASE2_3E_ENTITY_GRANULARITY_REVIEW.md"
    )
    args = parser.parse_args(argv)
    result = generate_review_package(args.db, args.artifact_dir, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
