"""Deterministic, artifact-only Phase 2.4A Current View pilot.

The pilot is intentionally limited to MLCC and Yunzhong Technology.  It reads
Production through SQLite's read-only URI, mirrors the frozen
``current_view_change`` Proposal payload, and never inserts a Proposal or a
Current View.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .propagation import CurrentViewValidationError, PropagationManager
from .query import ReadOnlyQuery


MLCC_NODE_ID = "NODE_20260817_DABE52FE"
YUNZHONG_NODE_ID = "NODE_20260826_BC260F3E"
MLCC_NAME = "MLCC"
YUNZHONG_NAME = "昀冢科技"

MLCC_SUBJECT_CLAIM_IDS = (
    "CLM_20260814_980FA010",
    "CLM_20260814_BAED6789",
    "CLM_20260814_D2C7FCD1",
)
YUNZHONG_SUBJECT_CLAIM_IDS = (
    "CLM_20260814_0B6E52F8",
    "CLM_20260814_541F5C31",
    "CLM_20260814_8E4B9E25",
    "CLM_20260814_939CAEDD",
    "CLM_20260814_9A069D06",
    "CLM_20260814_BA7AC415",
    "CLM_20260814_E1A48290",
    "CLM_20260814_E53B8E9C",
)
MLCC_CONTEXT_CLAIM_IDS = YUNZHONG_SUBJECT_CLAIM_IDS
PILOT_NODE_IDS = (MLCC_NODE_ID, YUNZHONG_NODE_ID)

MLCC_FORBIDDEN_PRIMARY_TEXT = (
    "80亿颗/月",
    "120亿颗/月",
    "220亿颗/月",
    "400亿颗/月",
    "7.5亿元",
    "车规认证",
    "车规级",
    "70%以上",
)

CURRENT_VIEW_EVIDENCE_POLICY = {
    "subject": "required for every direct factual assertion and every primary supporting Claim",
    "context": "review-package background only; label CONTEXT_ONLY and never use as direct support",
    "related": "prohibited as direct Current View support until human subject/context adjudication",
    "needs_review": "exclude from primary evidence and list explicitly as unresolved",
    "expert_judgment": "retain as attributed judgment; never present as data or confirmed fact",
    "company_guidance": "retain company attribution, future time anchor, and guidance status",
}

_NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?(?:\s*(?:Q[1-4]|H[12]|年(?:底|末)?|月|日|亿颗(?:/月)?|亿元|%|倍))?",
    re.IGNORECASE,
)


class CurrentViewPilotError(RuntimeError):
    """The frozen pilot scope, evidence, or governance contract was violated."""


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _claim_summary(claim: dict[str, Any], *, evidence_use: str) -> dict[str, Any]:
    return {
        "claim_id": claim["claim_id"],
        "statement": claim["statement"],
        "nature": claim["nature"],
        "fact_time": claim["fact_time"],
        "publication_time": claim["publication_time"],
        "status": claim["status"],
        "confidence": claim["confidence"],
        "source_id": claim["source_id"],
        "source_title": claim["source_title"],
        "role": claim["role"],
        "evidence_use": evidence_use,
    }


def _record(
    section: str,
    text: str,
    supporting_claim_ids: Iterable[str],
    evidence_kind: str,
) -> dict[str, Any]:
    return {
        "section": section,
        "text": text,
        "supporting_claim_ids": list(supporting_claim_ids),
        "evidence_kind": evidence_kind,
    }


def _mlcc_draft() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    price, cycle, ai_effect = MLCC_SUBJECT_CLAIM_IDS
    assertions = [
        _record(
            "summary",
            "截至2026年8月，MLCC已存数据支持7月和8月单月价格环比上涨30%以上；"
            f"周期长度及AI挤出效应仅保留为分析师判断。[{price}] [{cycle}] [{ai_effect}]",
            (price, cycle, ai_effect),
            "mixed_data_and_attributed_judgment",
        ),
        _record(
            "key_facts",
            f"MLCC在2026年7月和8月的单月价格环比上涨30%以上。[{price}]",
            (price,),
            "data",
        ),
        _record(
            "core_logic",
            f"分析师判断认为，本轮MLCC周期持续期将长于上一轮；这不是已确认数据。[{cycle}]",
            (cycle,),
            "expert_judgment",
        ),
        _record(
            "core_logic",
            "分析师判断认为，国内与海外MLCC原厂趋势相符且AI挤出效应明显；"
            f"这不是已确认事实。[{ai_effect}]",
            (ai_effect,),
            "expert_judgment",
        ),
    ]
    content = {
        "one_line_conclusion": assertions[0]["text"],
        "core_logic": [assertions[2]["text"], assertions[3]["text"]],
        "key_facts": [assertions[1]["text"]],
        "core_disagreements": ["MLCC周期长度与AI挤出判断尚待独立证据验证。"],
        "assumptions_to_verify": ["需验证MLCC价格变化能否由更多原厂或市场数据交叉确认。"],
        "investment_implication": (
            "当前MLCC产品证据只支持价格观察，单一二手来源尚不足以形成行业投资结论。"
            f"[{price}]"
        ),
        "major_risks": [
            f"MLCC价格数据来自单一B级二手Source，尚需独立来源复核。[{price}]",
            "分析师判断认为MLCC周期可能更长且存在AI挤出效应；"
            f"这些判断不能按已确认事实使用。[{cycle}] [{ai_effect}]",
        ],
        "knowledge_gaps": [
            "缺少MLCC行业供需、库存与多家原厂价格的独立交叉验证。",
        ],
        "key_watch_items": [
            "跟踪MLCC行业供需与库存。",
            "跟踪国内外MLCC厂商竞争与定价。",
            "跟踪AI及其他下游应用需求。",
        ],
        "recent_change": "首次建立人工评审候选；尚未形成官方 Current View。",
        "evidence_claim_ids": list(MLCC_SUBJECT_CLAIM_IDS),
        "type_specific": {
            "applications": [],
            "demand_drivers": [
                "分析师判断认为AI需求可能对MLCC形成挤出效应，仍需复核。"
                f"[{ai_effect}]"
            ],
            "supply_capacity": [],
            "pricing": [assertions[1]["text"]],
            "major_suppliers": [
                "分析师判断比较国内MLCC原厂与海外MLCC原厂趋势，但未识别具体供应商。"
                f"[{ai_effect}]"
            ],
            "product_evolution": [],
        },
    }
    return content, assertions


def _yunzhong_draft() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    capacity, phase_two, high_capacity, phase_three, certification, revenue = (
        "CLM_20260814_541F5C31",
        "CLM_20260814_8E4B9E25",
        "CLM_20260814_939CAEDD",
        "CLM_20260814_9A069D06",
        "CLM_20260814_BA7AC415",
        "CLM_20260814_E1A48290",
    )
    primary_ids = (capacity, phase_two, high_capacity, phase_three, certification, revenue)
    assertions = [
        _record(
            "summary",
            "昀冢科技现有证据支持其MLCC一期产线出货、扩产计划、车规级高容产品认证"
            "和单月营收变化的公司级候选判断；未来产能均保留为公司指引。"
            + " ".join(f"[{claim_id}]" for claim_id in primary_ids),
            primary_ids,
            "mixed_company_evidence",
        ),
        _record(
            "key_facts",
            f"公司表示，昀冢科技一期产线当前出货量80亿颗/月，预计2026Q4达120亿颗/月并于2026年底满产。[{capacity}]",
            (capacity,),
            "company_guidance",
        ),
        _record(
            "key_facts",
            f"公司表示，昀冢科技二期投资7.5亿元，预计2026年底开始导入量产、2027Q3完成爬坡，2027年底月产能达220亿颗。[{phase_two}]",
            (phase_two,),
            "company_guidance",
        ),
        _record(
            "key_facts",
            f"公司表示，昀冢科技计划在2026H2围绕高容和超高容产品扩产，较原2027年导入计划提前。[{high_capacity}]",
            (high_capacity,),
            "company_guidance",
        ),
        _record(
            "key_facts",
            f"公司表示，昀冢科技三期投资7.5亿元，预计2028年开始量产爬坡、2028H2陆续达产，2028年底月产能超400亿颗。[{phase_three}]",
            (phase_three,),
            "company_guidance",
        ),
        _record(
            "key_facts",
            f"昀冢科技车规级高容产品已完成认证，106、107进入实验室阶段。[{certification}]",
            (certification,),
            "fact",
        ),
        _record(
            "key_facts",
            f"昀冢科技2026年6月MLCC单月营收相较于4月将近翻倍。[{revenue}]",
            (revenue,),
            "data",
        ),
    ]
    content = {
        "one_line_conclusion": assertions[0]["text"],
        "core_logic": [record["text"] for record in assertions[1:]],
        "key_facts": [record["text"] for record in assertions[1:]],
        "core_disagreements": [
            "昀冢科技的扩产路径为公司指引，兑现节奏仍需后续事实验证。",
        ],
        "assumptions_to_verify": [
            "昀冢科技高容和超高容产品占新扩产产能比例70%以上仍为needs_review，"
            "不纳入主证据。[CLM_20260814_0B6E52F8]",
            "昀冢科技关于MLCC上行周期提前的判断仍为needs_review，"
            "不扩展为行业结论。[CLM_20260814_E53B8E9C]",
        ],
        "investment_implication": (
            "昀冢科技候选证据显示公司处于MLCC产能扩张与产品验证阶段；"
            "未来产能是公司指引，不能视为已实现结果。"
            f"[{capacity}] [{phase_two}] [{high_capacity}] [{phase_three}] [{certification}] [{revenue}]"
        ),
        "major_risks": [
            "昀冢科技扩产时间表均为公司指引，后续需验证兑现。"
            f"[{capacity}] [{phase_two}] [{high_capacity}] [{phase_three}]",
            f"昀冢科技MLCC单月营收数据仍需更多期间与独立来源验证。[{revenue}]",
        ],
        "knowledge_gaps": [
            "缺少昀冢科技扩产兑现、良率、客户结构与持续营收的独立跟踪证据。",
        ],
        "key_watch_items": [
            "跟踪昀冢科技一期产线2026Q4及2026年底指引兑现。",
            "跟踪昀冢科技二期、三期量产爬坡与月产能。",
            "跟踪昀冢科技车规产品实验室进展及后续认证。",
        ],
        "recent_change": "首次建立人工评审候选；尚未形成官方 Current View。",
        "evidence_claim_ids": list(primary_ids),
        "type_specific": {},
    }
    return content, assertions


def _load_state(db_path: str | Path) -> dict[str, Any]:
    query = ReadOnlyQuery(db_path)
    with query.connect() as conn:
        placeholders = ",".join("?" for _ in PILOT_NODE_IDS)
        nodes = {
            row["node_id"]: dict(row)
            for row in conn.execute(
                f"""SELECT node_id,canonical_name,primary_type,description,status
                    FROM nodes WHERE node_id IN ({placeholders}) ORDER BY node_id""",
                PILOT_NODE_IDS,
            ).fetchall()
        }
        for node_id, node in nodes.items():
            node["aliases"] = [
                row[0]
                for row in conn.execute(
                    "SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias",
                    (node_id,),
                ).fetchall()
            ]
        claims = [
            dict(row)
            for row in conn.execute(
                f"""SELECT cnl.node_id,cnl.role,c.claim_id,c.statement,c.nature,
                           c.fact_time,c.publication_time,c.ingestion_time,c.status,
                           c.confidence,c.attributed_to,c.scope,c.structured_json,
                           c.source_id,s.title AS source_title,s.source_rank,s.origin_type,
                           s.underlying_source_id,s.source_id AS evidence_source_id
                    FROM claim_node_links cnl
                    JOIN claims c ON c.claim_id=cnl.claim_id
                    JOIN sources s ON s.source_id=c.source_id
                    WHERE cnl.node_id IN ({placeholders})
                    ORDER BY cnl.node_id,
                             CASE WHEN c.status='needs_review' THEN 1 ELSE 0 END,
                             c.confidence DESC,
                             COALESCE(NULLIF(c.fact_time,''),c.publication_time) DESC,
                             c.nature,c.claim_id""",
                PILOT_NODE_IDS,
            ).fetchall()
        ]
        current_view_counts = {
            row["node_id"]: int(row["count"])
            for row in conn.execute(
                f"""SELECT node_id,COUNT(*) AS count FROM current_views
                    WHERE node_id IN ({placeholders}) GROUP BY node_id""",
                PILOT_NODE_IDS,
            ).fetchall()
        }
        counts = dict(
            conn.execute(
                """SELECT
                     (SELECT COUNT(*) FROM current_views) AS current_views,
                     (SELECT COUNT(*) FROM current_views WHERE status='official') AS official_views,
                     (SELECT COUNT(*) FROM proposals) AS proposals,
                     (SELECT COUNT(*) FROM proposals
                        WHERE proposal_type='current_view_change') AS current_view_proposals"""
            ).fetchone()
        )
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = [list(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
    return {
        "nodes": nodes,
        "claims": claims,
        "current_view_counts": current_view_counts,
        "counts": counts,
        "integrity_check": integrity,
        "foreign_key_violations": foreign_keys,
    }


def _primary_text(content: dict[str, Any]) -> str:
    values: list[str] = [
        str(content.get("one_line_conclusion") or ""),
        str(content.get("investment_implication") or ""),
    ]
    for field in ("core_logic", "key_facts", "major_risks"):
        values.extend(str(item) for item in content.get(field) or [])
    for items in (content.get("type_specific") or {}).values():
        if isinstance(items, list):
            values.extend(str(item) for item in items)
    return "\n".join(values)


def _number_tokens(text: str, claim_ids: Iterable[str]) -> set[str]:
    for claim_id in claim_ids:
        text = text.replace(claim_id, "")
    return {re.sub(r"\s+", "", match.group(0)).lower() for match in _NUMBER_RE.finditer(text)}


def _validate_frozen_content_contract(
    node: dict[str, Any],
    content: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> None:
    result = {
        "change_level": "initial",
        "proposed_current_view": content,
        "evidence_sufficiency": {"sufficient": True},
        "knowledge_gaps": [],
        "research_question_candidates": [],
    }
    frozen_evidence = [dict(item) for item in evidence]
    if node.get("primary_type") == "Company":
        for item in frozen_evidence:
            item["attributed_to"] = item.get("attributed_to") or node["canonical_name"]
    manager = object.__new__(PropagationManager)
    try:
        manager._validate_current_view_quality(node, result, frozen_evidence)
    except (ValueError, CurrentViewValidationError) as exc:
        raise CurrentViewPilotError(f"frozen Current View contract failed: {exc}") from exc


def _validate_node_proposal(
    proposal: dict[str, Any],
    node: dict[str, Any],
    claims: list[dict[str, Any]],
) -> dict[str, bool]:
    by_id = {claim["claim_id"]: claim for claim in claims}
    payload = proposal["payload"]
    content = payload["proposed_current_view"]
    primary_ids = proposal["primary_evidence_claim_ids"]
    if payload["evidence_claim_ids"] != primary_ids:
        raise CurrentViewPilotError("Proposal evidence IDs differ from primary evidence IDs")
    if payload["previous_view_id"] or payload["previous_version"]:
        raise CurrentViewPilotError("Pilot attempted to replace an existing Current View")
    if proposal["human_confirmation_state"] != "pending":
        raise CurrentViewPilotError("Pilot Proposal must remain pending human confirmation")
    if proposal["production_write_authorized"] is not False:
        raise CurrentViewPilotError("Pilot authorized a final Current View write")

    for claim_id in primary_ids:
        claim = by_id.get(claim_id)
        if not claim:
            raise CurrentViewPilotError(f"unknown primary Evidence Claim: {claim_id}")
        if claim["role"] != "subject":
            raise CurrentViewPilotError(
                f"direct Current View support must be role=subject: {claim_id} ({claim['role']})"
            )
        if claim["status"] == "needs_review":
            raise CurrentViewPilotError(f"needs_review Claim used as primary Evidence: {claim_id}")
        if not claim["source_id"] or not claim["source_title"]:
            raise CurrentViewPilotError(f"Claim Source traceability missing: {claim_id}")

    assertion_support: set[str] = set()
    for record in proposal["review_sections"]["primary_assertions"]:
        support = record["supporting_claim_ids"]
        if not support:
            raise CurrentViewPilotError("factual assertion has no supporting Claim")
        if any(claim_id not in record["text"] for claim_id in support):
            raise CurrentViewPilotError("factual assertion text does not retain Claim IDs")
        for claim_id in support:
            if claim_id not in primary_ids:
                raise CurrentViewPilotError(
                    f"assertion uses non-primary or context Evidence: {claim_id}"
                )
            assertion_support.add(claim_id)
        kind = record["evidence_kind"]
        if kind == "expert_judgment" and not (
            "分析师" in record["text"] and "判断" in record["text"]
        ):
            raise CurrentViewPilotError("expert_judgment attribution was not preserved")
        if kind == "company_guidance" and not (
            "公司" in record["text"]
            and any(marker in record["text"] for marker in ("预计", "计划", "指引"))
        ):
            raise CurrentViewPilotError("company_guidance attribution was not preserved")
        supported_numbers: set[str] = set()
        for claim_id in support:
            claim = by_id[claim_id]
            supported_numbers.update(
                _number_tokens(
                    " ".join(
                        str(claim.get(field) or "")
                        for field in ("statement", "fact_time", "publication_time")
                    ),
                    (),
                )
            )
        unsupported_numbers = _number_tokens(record["text"], support) - supported_numbers
        if unsupported_numbers:
            raise CurrentViewPilotError(
                "assertion exceeds numeric Evidence scope: "
                + ", ".join(sorted(unsupported_numbers))
            )
    if assertion_support != set(primary_ids):
        raise CurrentViewPilotError("primary Evidence is not fully represented in assertions")

    unresolved_ids = {
        claim_id
        for item in proposal["review_sections"]["uncertainty"]
        for claim_id in item.get("claim_ids", [])
        if item.get("handling") == "UNRESOLVED_ONLY"
    }
    expected_unresolved = {
        claim["claim_id"]
        for claim in claims
        if claim["role"] == "subject" and claim["status"] == "needs_review"
    }
    if unresolved_ids != expected_unresolved:
        raise CurrentViewPilotError("needs_review Claims are not fully isolated as unresolved")

    context_ids = {
        item["claim_id"] for item in proposal["review_sections"]["context"]
    }
    if context_ids & set(primary_ids):
        raise CurrentViewPilotError("context Claim leaked into primary Evidence")
    if any(item["label"] != "CONTEXT_ONLY" for item in proposal["review_sections"]["context"]):
        raise CurrentViewPilotError("context Evidence lacks CONTEXT_ONLY label")

    if node["node_id"] == MLCC_NODE_ID:
        primary_text = _primary_text(content)
        leaked = [token for token in MLCC_FORBIDDEN_PRIMARY_TEXT if token in primary_text]
        if leaked:
            raise CurrentViewPilotError(
                "MLCC primary text contains Company-only context: " + ", ".join(leaked)
            )
    elif node["node_id"] == YUNZHONG_NODE_ID:
        for record in proposal["review_sections"]["primary_assertions"]:
            industry_scoped = any(by_id[claim_id]["scope"] == "行业" for claim_id in record["supporting_claim_ids"])
            if industry_scoped and not (
                YUNZHONG_NAME in record["text"]
                and any(marker in record["text"] for marker in ("表示", "判断", "观察", "预计"))
            ):
                raise CurrentViewPilotError("Company Claim was expanded into an industry-wide assertion")

    evidence = [by_id[claim_id] for claim_id in primary_ids]
    _validate_frozen_content_contract(node, content, evidence)
    return {
        "subject_only_primary_evidence": True,
        "context_excluded_from_primary_support": True,
        "related_excluded_from_primary_support": True,
        "source_traceability": True,
        "needs_review_isolated": True,
        "frozen_content_contract": True,
        "scope_overreach": False,
    }


def _proposal_for(
    name: str,
    node: dict[str, Any],
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {claim["claim_id"]: claim for claim in claims}
    if name == MLCC_NAME:
        expected_subject = MLCC_SUBJECT_CLAIM_IDS
        expected_context = MLCC_CONTEXT_CLAIM_IDS
        content, assertions = _mlcc_draft()
        primary_ids = list(MLCC_SUBJECT_CLAIM_IDS)
        verdict = "PARTIAL"
        verdict_reason = "Only three subject Claims from one secondary Source; two are expert judgment."
    else:
        expected_subject = YUNZHONG_SUBJECT_CLAIM_IDS
        expected_context = ()
        content, assertions = _yunzhong_draft()
        primary_ids = [
            claim_id
            for claim_id in YUNZHONG_SUBJECT_CLAIM_IDS
            if by_id[claim_id]["status"] != "needs_review"
        ]
        verdict = "PARTIAL"
        verdict_reason = "Eight subject Claims exist, but two are needs_review and all come from one secondary Source."

    actual_subject = {claim["claim_id"] for claim in claims if claim["role"] == "subject"}
    actual_context = {claim["claim_id"] for claim in claims if claim["role"] == "context"}
    actual_related = {claim["claim_id"] for claim in claims if claim["role"] == "related"}
    if actual_subject != set(expected_subject):
        raise CurrentViewPilotError(f"{name} subject Claim drift")
    if actual_context != set(expected_context):
        raise CurrentViewPilotError(f"{name} context Claim drift")
    if actual_related:
        raise CurrentViewPilotError(f"{name} has unadjudicated related Claims")

    unresolved = [
        claim for claim in claims if claim["role"] == "subject" and claim["status"] == "needs_review"
    ]
    review_context = []
    for claim in claims:
        if claim["role"] == "context":
            item = _claim_summary(claim, evidence_use="CONTEXT_ONLY")
            item["label"] = "CONTEXT_ONLY"
            review_context.append(item)
    proposal = {
        "proposal_type": "current_view_change",
        "target_node_id": node["node_id"],
        "target_node_name": node["canonical_name"],
        "change_level": "initial",
        "reason": "Phase 2.4A subject-aware artifact-only Current View pilot",
        "previous_view": None,
        "human_confirmation_state": "pending",
        "production_write_authorized": False,
        "primary_evidence_claim_ids": primary_ids,
        "payload": {
            "node_id": node["node_id"],
            "change_level": "initial",
            "reason": "Phase 2.4A subject-aware artifact-only Current View pilot",
            "scope_normalization_notes": [
                "Direct assertions use role=subject only.",
                "context is review-only; related is prohibited as direct support.",
            ],
            "evidence_sufficiency": {
                "sufficient": False,
                "reason": verdict_reason,
            },
            "proposed_current_view": content,
            "evidence_claim_ids": primary_ids,
            "trigger_source_id": by_id[primary_ids[0]]["source_id"],
            "previous_view_id": "",
            "previous_version": "",
            "context": {
                "phase": "2.4A",
                "proposal_storage": "artifact_only",
                "human_confirmation_state": "pending",
            },
        },
        "review_sections": {
            "primary_assertions": assertions,
            "summary": next(item for item in assertions if item["section"] == "summary"),
            "key_facts": [
                item for item in assertions if item["section"] == "key_facts"
            ],
            "evidence": [
                _claim_summary(
                    claim,
                    evidence_use=(
                        "PRIMARY"
                        if claim["claim_id"] in primary_ids
                        else "UNRESOLVED_ONLY"
                    ),
                )
                for claim in claims
                if claim["role"] == "subject"
            ],
            "context": review_context,
            "uncertainty": [
                {
                    "claim_ids": [claim["claim_id"]],
                    "status": claim["status"],
                    "confidence": claim["confidence"],
                    "handling": "UNRESOLVED_ONLY",
                    "reason": "needs_review Claim excluded from primary Evidence",
                }
                for claim in unresolved
            ],
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }
    proposal["validation"] = _validate_node_proposal(proposal, node, claims)
    return proposal


def build_review_package(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path)
    pre_sha = file_sha256(db)
    state = _load_state(db)
    if set(state["nodes"]) != set(PILOT_NODE_IDS):
        raise CurrentViewPilotError("exactly two frozen pilot Nodes must exist")
    if state["nodes"][MLCC_NODE_ID]["canonical_name"] != MLCC_NAME:
        raise CurrentViewPilotError("MLCC Node identity drift")
    if state["nodes"][YUNZHONG_NODE_ID]["canonical_name"] != YUNZHONG_NAME:
        raise CurrentViewPilotError("Yunzhong Node identity drift")
    if any(state["current_view_counts"].get(node_id, 0) for node_id in PILOT_NODE_IDS):
        raise CurrentViewPilotError("official Current View already exists for a pilot Node")
    if state["integrity_check"] != "ok" or state["foreign_key_violations"]:
        raise CurrentViewPilotError("Production integrity check failed")

    claims_by_node = {
        node_id: [claim for claim in state["claims"] if claim["node_id"] == node_id]
        for node_id in PILOT_NODE_IDS
    }
    nodes = {
        MLCC_NAME: _proposal_for(
            MLCC_NAME, state["nodes"][MLCC_NODE_ID], claims_by_node[MLCC_NODE_ID]
        ),
        YUNZHONG_NAME: _proposal_for(
            YUNZHONG_NAME,
            state["nodes"][YUNZHONG_NODE_ID],
            claims_by_node[YUNZHONG_NODE_ID],
        ),
    }
    post_sha = file_sha256(db)
    if post_sha != pre_sha:
        raise CurrentViewPilotError("Production changed during the read-only pilot")
    return {
        "phase": "2.4A",
        "proposal_storage": "artifact_only",
        "production_write_authorized_for_current_view": False,
        "human_review_required": True,
        "policy": CURRENT_VIEW_EVIDENCE_POLICY,
        "production": {
            "pre_sha256": pre_sha,
            "post_sha256": post_sha,
            "database_changed": False,
            "current_views_before": state["counts"]["current_views"],
            "current_views_after": state["counts"]["current_views"],
            "current_views_created": 0,
            "current_view_proposals_before": state["counts"]["current_view_proposals"],
            "current_view_proposals_after": state["counts"]["current_view_proposals"],
            "proposals_created_in_db": 0,
            "integrity_check": state["integrity_check"],
            "foreign_key_violations": state["foreign_key_violations"],
        },
        "nodes": nodes,
        "artifact_only_proposals": 2,
        "subject_aware_view_model_valid": "PARTIAL",
        "model_verdict_reason": (
            "The two-node pilot enforces attribution and blocks context leakage, but all Evidence "
            "comes from one secondary Source and no proposal has received human confirmation."
        ),
        "primary_next_step": "Human review of the two Current View proposals",
    }


def _claim_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "_None._"
    lines = [
        "| Claim | Role/use | Nature | Status | Confidence | Time | Source |",
        "|---|---|---|---|---:|---|---|",
    ]
    for item in items:
        lines.append(
            "| {claim_id} | {use} | {nature} | {status} | {confidence} | {time} | "
            "{source_id} — {source_title} |".format(
                claim_id=item["claim_id"],
                use=item.get("label") or item["evidence_use"],
                nature=item["nature"],
                status=item["status"],
                confidence=item["confidence"],
                time=item["fact_time"] or item["publication_time"] or "—",
                source_id=item["source_id"],
                source_title=item["source_title"].replace("|", "\\|"),
            )
        )
    return "\n".join(lines)


def build_report(package: dict[str, Any]) -> str:
    mlcc = package["nodes"][MLCC_NAME]
    company = package["nodes"][YUNZHONG_NAME]
    forbidden = ", ".join(f"`{item}`" for item in MLCC_FORBIDDEN_PRIMARY_TEXT)
    policy = package["policy"]
    return f"""# Phase 2.4A — Subject-Aware Current View Pilot

PHASE2_4A_COMPLETE = true
MLCC_VIEW_PILOT_READY = {mlcc['verdict']}
YUNZHONG_VIEW_PILOT_READY = {company['verdict']}
SUBJECT_AWARE_VIEW_MODEL_VALID = {package['subject_aware_view_model_valid']}
PRODUCTION_WRITE_AUTHORIZED_FOR_CURRENT_VIEW = false
HUMAN_REVIEW_REQUIRED = true

## Outcome

Exactly two artifact-only `current_view_change` Proposal payloads were generated for human
review: `{MLCC_NODE_ID}` / MLCC and `{YUNZHONG_NODE_ID}` / 昀冢科技. They reuse the frozen
Proposal fields and Current View `content_json` shape, but no row was inserted into
`proposals` or `current_views`. No LLM was called.

The deterministic gate passes subject/context separation, source traceability, frozen content
validation, uncertainty handling and scope-overreach checks. The model verdict remains
`PARTIAL`, because both pilots rely on one B-rank secondary Source and neither draft has been
human-confirmed.

## CURRENT_VIEW_EVIDENCE_POLICY

- `subject`: {policy['subject']}.
- `context`: {policy['context']}.
- `related`: {policy['related']}.
- `needs_review`: {policy['needs_review']}.
- `expert_judgment`: {policy['expert_judgment']}.
- `company_guidance`: {policy['company_guidance']}.

## MLCC pilot

- Subject Claims available / primary: 3 / 3.
- Context Claims: 8, all `CONTEXT_ONLY`.
- Verdict: `{mlcc['verdict']}` — {mlcc['verdict_reason']}
- Summary: {mlcc['payload']['proposed_current_view']['one_line_conclusion']}

### Primary Evidence

{_claim_table(mlcc['review_sections']['evidence'])}

### Context-only Evidence

{_claim_table(mlcc['review_sections']['context'])}

### Rejected context leakage

The validator rejects the following company-only facts from MLCC Summary, Key Facts and other
primary content: {forbidden}. None appears in the MLCC primary proposal. These Claims remain
visible only in the `CONTEXT_ONLY` review section.

## 昀冢科技 pilot

- Subject Claims available / primary: 8 / 6.
- Context Claims: 0.
- Two `needs_review` Claims are isolated as unresolved and excluded from primary Evidence.
- Verdict: `{company['verdict']}` — {company['verdict_reason']}
- Summary: {company['payload']['proposed_current_view']['one_line_conclusion']}

### Subject Evidence

{_claim_table(company['review_sections']['evidence'])}

### Uncertainty handling

`CLM_20260814_0B6E52F8` and `CLM_20260814_E53B8E9C` retain `needs_review` and confidence
`0.0`. The first is not used to assert a 70% product mix; the second is not turned into an
industry-wide cycle fact. Company guidance is phrased as “据公司材料/预计/计划”, while
`fact` and `data` remain separately typed. Time anchors stay in the Claim evidence and draft
statements.

## Traceability and validation

Every primary assertion carries at least one Claim ID. Each ID resolves to an existing Claim,
a `role=subject` link to the target Node, an existing Source ID and Source title. `context` and
`related` links are rejected as direct support. The existing frozen Current View content
validator also passes both drafts.

- Production SHA: `{package['production']['pre_sha256']}` before and after.
- Current Views: {package['production']['current_views_before']} → {package['production']['current_views_after']}.
- Current View Proposals in DB: {package['production']['current_view_proposals_before']} → {package['production']['current_view_proposals_after']}.
- Integrity: `{package['production']['integrity_check']}`.
- Foreign-key violations: {len(package['production']['foreign_key_violations'])}.

## Next recommendation

Human reviewers should `APPROVE`, `REVISE`, or `REJECT` each artifact proposal independently.
Only an explicit later approval may create a pending Production Proposal or an official Current
View through the frozen acceptance path. Do not broaden this pilot to other Nodes yet.
"""


def generate_review_package(
    db_path: str | Path,
    artifact_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    package = build_review_package(db_path)
    artifact = Path(artifact_path)
    report = Path(report_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report.write_text(build_report(package), encoding="utf-8")
    final_sha = file_sha256(db_path)
    if final_sha != package["production"]["pre_sha256"]:
        raise CurrentViewPilotError("Production changed while writing pilot artifacts")
    return package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="workspace/pro_a.db")
    parser.add_argument(
        "--artifact", default="artifacts/phase2_4a/current_view_pilot_review.json"
    )
    parser.add_argument(
        "--report", default="docs/PHASE2_4A_CURRENT_VIEW_PILOT.md"
    )
    args = parser.parse_args(argv)
    package = generate_review_package(args.db, args.artifact, args.report)
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
