from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PILOT_RUN_ID = "PILOT_20260901_4C6535B7"
SOURCE_SHA256 = "4c6535b75fa97968f8f1651987ff52c64c0ffded41d3dba39ca72a5bbac3a178"
CLAIM_PROJECTION_SHA256 = (
    "b105a9bcaa433eac6dcaaa96fd85fd774e5a0757ac0da1671f1a7d3e18e4b100"
)
PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"


BLOCKS = {
    "PAGE:6/TABLE:figure_5_incentive_targets": {
        "page": 6,
        "label": "图表5：2026年股权激励业绩考核标准",
        "category": "operational_product",
        "broad_claim_type": "corporate_incentive_target",
        "claim_ids": {
            "CLM_20260901_B87644F5",
            "CLM_20260901_7E18EAA9",
            "CLM_20260901_13316DDB",
        },
    },
    "PAGE:20/TABLE:figure_38_business_forecast": {
        "page": 20,
        "label": "图表38：公司各业务营收及毛利率预测",
        "category": "financial_statement_or_forecast",
        "broad_claim_type": "financial_performance_or_forecast",
        "claim_ids": {
            "CLM_20260901_ED4E6835",
            "CLM_20260901_CEB566A2",
            "CLM_20260901_B0960FC7",
            "CLM_20260901_83F81AEF",
            "CLM_20260901_562CA823",
            "CLM_20260901_118E41A2",
        },
    },
    "PAGE:20/TABLE:figure_39_expense_forecast": {
        "page": 20,
        "label": "图表39：2024-2028E公司三费情况",
        "category": "financial_statement_or_forecast",
        "broad_claim_type": "financial_performance_or_forecast",
        "claim_ids": {"CLM_20260901_38564DE2"},
    },
    "PAGE:21/TABLE:figure_40_peer_valuation": {
        "page": 21,
        "label": "图表40：可比公司估值比较（市盈率法）",
        "category": "peer_valuation_or_comparable",
        "broad_claim_type": "valuation_or_comparable_company",
        "claim_ids": set(),
    },
    "PAGE:23/TABLE:appendix_three_statement_forecast": {
        "page": 23,
        "label": "附录：三张报表预测摘要",
        "category": "financial_statement_or_forecast",
        "broad_claim_type": "financial_statement_cashflow_ratio_or_forecast",
        "claim_ids": set(),
    },
    "PAGE:24/TABLE:market_rating_distribution": {
        "page": 24,
        "label": "市场中相关报告评级比率分析",
        "category": "other",
        "broad_claim_type": "market_rating_meta",
        "claim_ids": {
            "CLM_20260901_F7E50542",
            "CLM_20260901_FD2B7E03",
            "CLM_20260901_F55063F0",
            "CLM_20260901_F7FE26C3",
            "CLM_20260901_4887693A",
            "CLM_20260901_A4D820D7",
            "CLM_20260901_CE8342CF",
            "CLM_20260901_9B14E25F",
            "CLM_20260901_68F230D3",
            "CLM_20260901_A13224CF",
        },
    },
}

FIGURE_CAPTION_ONLY_CLAIMS = {"CLM_20260901_B6DE169A"}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def table_block_map(claims: list[dict[str, Any]]) -> dict[str, str]:
    block_by_claim: dict[str, str] = {}
    for block_id, block in BLOCKS.items():
        for claim_id in block["claim_ids"]:
            block_by_claim[claim_id] = block_id
    for claim in claims:
        locator = ((claim.get("validation") or {}).get("source_locator") or {})
        if locator.get("status") != "resolved":
            continue
        if locator.get("locator") == "PAGE:21":
            block_by_claim[claim["claim_id"]] = "PAGE:21/TABLE:figure_40_peer_valuation"
        elif locator.get("locator") == "PAGE:23":
            block_by_claim[claim["claim_id"]] = (
                "PAGE:23/TABLE:appendix_three_statement_forecast"
            )
    return block_by_claim


def table_dimensions(claim: dict[str, Any], block_id: str) -> dict[str, Any]:
    nature = str(claim.get("nature") or "")
    if nature == "company_guidance":
        actual_vs_forecast = "forecast_or_target"
    elif nature == "broker_forecast":
        actual_vs_forecast = "forecast"
    else:
        actual_vs_forecast = "actual_or_current"

    if block_id == "PAGE:21/TABLE:figure_40_peer_valuation":
        subject_scope = (
            "company_specific"
            if "仕佳光子" in str(claim.get("statement") or "")
            else "peer_or_comparable_company"
        )
    elif block_id == "PAGE:24/TABLE:market_rating_distribution":
        subject_scope = "market_meta_not_company_or_peer"
    else:
        subject_scope = "company_specific"
    return {
        "actual_vs_forecast": actual_vs_forecast,
        "subject_scope": subject_scope,
        "attribution_bearing": bool(str(claim.get("attributed_to") or "").strip()),
    }


def build_counterfactual(bundle: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    claims = bundle.get("claims") or []
    if bundle.get("pilot_run_id") != PILOT_RUN_ID or len(claims) != 320:
        raise RuntimeError("Pilot #4 frozen identity/count mismatch")
    projection_sha = canonical_sha256([claim_projection(claim) for claim in claims])
    prompt_sha = (((bundle.get("model") or {}).get("prompt") or {}).get("prompt_sha256"))
    if projection_sha != CLAIM_PROJECTION_SHA256 or prompt_sha != PROMPT_SHA256:
        raise RuntimeError("Pilot #4 claim/prompt freeze mismatch")
    if evidence.get("pilot_run_id") != PILOT_RUN_ID:
        raise RuntimeError("Pilot #4 Evidence identity mismatch")

    block_by_claim = table_block_map(claims)
    claim_rows = []
    by_origin: dict[str, list[str]] = {
        "narrative_derived": [],
        "table_derived": [],
        "mixed_or_uncertain": [],
        "unresolved_origin": [],
    }
    by_id = {claim["claim_id"]: claim for claim in claims}
    for claim in claims:
        claim_id = claim["claim_id"]
        locator = ((claim.get("validation") or {}).get("source_locator") or {})
        binding_status = str(locator.get("status") or "unresolved")
        block_id = block_by_claim.get(claim_id)
        if binding_status == "unresolved":
            origin = "unresolved_origin"
            rationale = "frozen authoritative Evidence occurrence unresolved"
        elif block_id:
            origin = "table_derived"
            rationale = "resolved Evidence span lies in visually verified Source table block"
        elif binding_status == "ambiguous":
            origin = "mixed_or_uncertain"
            rationale = "multiple frozen candidate Source occurrences; no authoritative occurrence"
        elif claim_id in FIGURE_CAPTION_ONLY_CLAIMS:
            origin = "mixed_or_uncertain"
            rationale = "resolved figure caption is neither narrative prose nor a table block"
        else:
            origin = "narrative_derived"
            rationale = "resolved Evidence lies outside the verified table-block manifest"
        by_origin[origin].append(claim_id)
        row = {
            "claim_id": claim_id,
            "origin_class": origin,
            "classification_rationale": rationale,
            "binding_status": binding_status,
            "locator": locator.get("locator"),
            "candidate_locators": locator.get("locators") or [],
            "nature": claim.get("nature"),
            "table_block": block_id,
        }
        if block_id:
            row.update(table_dimensions(claim, block_id))
        claim_rows.append(row)

    counts = {key: len(value) for key, value in by_origin.items()}
    expected = {
        "narrative_derived": 100,
        "table_derived": 198,
        "mixed_or_uncertain": 3,
        "unresolved_origin": 19,
    }
    if counts != expected or sum(counts.values()) != 320:
        raise RuntimeError(f"unexpected classification census: {counts}")

    block_rows = []
    for block_id, block in BLOCKS.items():
        selected = [claim for claim in claims if block_by_claim.get(claim["claim_id"]) == block_id]
        dimensions = [table_dimensions(claim, block_id) for claim in selected]
        block_rows.append({
            "block_id": block_id,
            "page": block["page"],
            "label": block["label"],
            "category": block["category"],
            "broad_claim_type": block["broad_claim_type"],
            "claim_count": len(selected),
            "actual_vs_forecast": dict(Counter(d["actual_vs_forecast"] for d in dimensions)),
            "subject_scope": dict(Counter(d["subject_scope"] for d in dimensions)),
            "attribution": {
                "bearing": sum(d["attribution_bearing"] for d in dimensions),
                "non_bearing": sum(not d["attribution_bearing"] for d in dimensions),
            },
            "nature": dict(Counter(str(claim.get("nature") or "") for claim in selected)),
            "claim_ids": [claim["claim_id"] for claim in selected],
        })

    table_rows = [row for row in claim_rows if row["origin_class"] == "table_derived"]
    category_totals = Counter(BLOCKS[row["table_block"]]["category"] for row in table_rows)
    actual_totals = Counter(row["actual_vs_forecast"] for row in table_rows)
    scope_totals = Counter(row["subject_scope"] for row in table_rows)
    attribution_totals = Counter(
        "bearing" if row["attribution_bearing"] else "non_bearing" for row in table_rows
    )

    evidence_claims = evidence.get("claims") or []
    human_decisions = Counter(str(claim.get("human_decision") or "") for claim in evidence_claims)
    if len(evidence_claims) != 320 or human_decisions != Counter({"PENDING": 320}):
        raise RuntimeError("Pilot #4 Evidence Human Review surface is not frozen PENDING=320")

    example_ids = {
        "low_value_raw_table_cell_loss": [
            "CLM_20260901_963C4D22",
            "CLM_20260901_69EFDA7D",
            "CLM_20260901_A4D820D7",
        ],
        "potentially_meaningful_knowledge_loss": [
            "CLM_20260901_E399A714",
            "CLM_20260901_3C6B0E81",
            "CLM_20260901_C56F02AC",
            "CLM_20260901_CBE06D3B",
        ],
    }
    information_loss = {
        key: [
            {
                "claim_id": claim_id,
                "statement": by_id[claim_id]["statement"],
                "table_block": block_by_claim[claim_id],
                "restatement_check": (
                    "no statement-identical or evidence-identical provenance-resolved narrative Claim; "
                    "semantic equivalence was not inferred"
                ),
            }
            for claim_id in claim_ids
        ]
        for key, claim_ids in example_ids.items()
    }

    return {
        "document_type": "phase3c_pilot4_table_suppression_counterfactual",
        "schema_version": "1.0",
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "scope": "DESIGN_AND_CENSUS_ONLY",
        "pilot_run_id": PILOT_RUN_ID,
        "freeze": {
            "source_sha256": SOURCE_SHA256,
            "claim_projection_sha256": projection_sha,
            "prompt_sha256": prompt_sha,
            "claims": len(claims),
            "semantic_extraction_calls_this_task": 0,
            "llm_calls_this_task": 0,
            "human_review_labels_modified": False,
            "pilot4_rebuilt": False,
        },
        "methodology": {
            "classification_basis": [
                "frozen deterministic Evidence locator status and locator",
                "visually rendered authoritative Source pages",
                "explicit retrospective table-block manifest",
                "frozen Claim nature and attributed_to fields for cross-tabs",
            ],
            "not_used": [
                "numeric density",
                "punctuation density",
                "token count",
                "new table detector",
                "LLM or semantic re-grading",
            ],
            "conservative_rule": (
                "Only a resolved Evidence span mapped to a verified table block is counted as "
                "table-derived. Ambiguous, figure-caption-only, and unresolved bindings are not "
                "counterfactually suppressed."
            ),
            "important_limitation": (
                "This is a retrospective Pilot #4 census, not a reusable PDF table detector."
            ),
        },
        "classification_summary": {
            "total_claims": 320,
            **counts,
            "table_suppression_rate": counts["table_derived"] / 320,
            "counterfactual_review_set_size": 320 - counts["table_derived"],
            "estimated_claim_review_burden_reduction": counts["table_derived"] / 320,
        },
        "claims_by_origin": by_origin,
        "claim_classifications": claim_rows,
        "table_derived_census": {
            "by_source_page_or_block": block_rows,
            "category_totals": dict(category_totals),
            "actual_vs_forecast_totals": dict(actual_totals),
            "subject_scope_totals": dict(scope_totals),
            "attribution_totals": {
                "bearing": attribution_totals["bearing"],
                "non_bearing": attribution_totals["non_bearing"],
            },
        },
        "counterfactual_quality": {
            "scenario": (
                "If NARRATIVE_FIRST_TABLE_SUPPRESSION had already been active before "
                "Pilot #4 extraction"
            ),
            "claims_removed": counts["table_derived"],
            "claims_remaining_for_review": 320 - counts["table_derived"],
            "known_semantic_failures_suppressed": None,
            "known_semantic_failures_remaining": None,
            "known_attribution_failures_suppressed": None,
            "known_attribution_failures_remaining": None,
            "failure_partition_status": "NOT_COMPUTABLE_NO_CLAIM_LEVEL_PILOT4_HUMAN_REVIEW_ARTIFACT",
            "failure_partition_reason": (
                "The frozen Pilot #4 Evidence surface contains PENDING=320 and no Pilot #4 "
                "claim-level semantic/attribution decision artifact exists in the run directory. "
                "The user-supplied aggregate semantic gate FAIL cannot be partitioned by origin."
            ),
            "human_review_surface_decisions": dict(human_decisions),
            "information_loss_examples": information_loss,
            "demonstrably_repeated_in_narrative_examples": [
                {
                    "table_claim_id": "CLM_20260901_C80DBAB2",
                    "narrative_claim_id": "CLM_20260901_DD9446AD",
                    "fact": "2026-2028 revenue forecast",
                },
                {
                    "table_claim_id": "CLM_20260901_59534905",
                    "narrative_claim_id": "CLM_20260901_48F4F8CF",
                    "fact": "2026-2028 EPS forecast",
                },
                {
                    "table_claim_id": "CLM_20260901_3DC1A2AF",
                    "narrative_claim_id": "CLM_20260901_345CF102",
                    "fact": "2025 net profit",
                },
            ],
        },
        "design_state": {
            "phase3c_table_suppression_scope_design_complete": True,
            "table_structure_signal": "PARTIAL_EXISTING_METADATA",
            "pilot4_pdf_table_structure_signal": "NO_RELIABLE_EXISTING_METADATA",
            "table_suppression_implementation_ready": "NO",
            "recommended_default_policy": "BLOCKED_PENDING_STRUCTURE_SIGNAL",
            "phase3c_complete": False,
            "production_apply_ready": "NO",
            "phase3c_next_gate": "Table Structure Design Blocker",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    source = args.source.resolve()
    bundle_path = run_dir / "extraction_bundle_stage1_1_rebound.json"
    evidence_path = run_dir / "evidence_v2_repair" / "evidence_contract_v2_repaired.json"
    if file_sha256(source) != SOURCE_SHA256:
        raise RuntimeError("Pilot #4 Source SHA mismatch")
    bundle = load_json(bundle_path)
    evidence = load_json(evidence_path)
    result = build_counterfactual(bundle, evidence)
    result["frozen_artifacts"] = {
        "source": str(source),
        "source_sha256": file_sha256(source),
        "bundle": str(bundle_path),
        "bundle_sha256": file_sha256(bundle_path),
        "evidence": str(evidence_path),
        "evidence_sha256": file_sha256(evidence_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["classification_summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
