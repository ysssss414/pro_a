from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .corpus_pilot import PilotError, production_snapshot
from .storage import sha256_file, write_json


SCHEMA_VERSION = "1"
RUN_ID = "PILOT_20260831_FF7D5C58"
HISTORICAL_RUN_ID = "PILOT_20260831_DEA82C1F"
SOURCE_SHA256 = "1ea71205fb04885f44ab0aa48b57586647c9c823d4b321f11d23d7505aa65f52"
DECISIONS_DOCUMENT_TYPE = "phase3c_pilot2_reextraction_human_review_decisions"
ANNOTATIONS_DOCUMENT_TYPE = "phase3c_pilot2_reextraction_human_review_annotations"
READY_DOCUMENT_TYPE = "phase3c_pilot2_reextraction_human_review_ready"
METRICS_DOCUMENT_TYPE = "phase3c_pilot2_reextraction_human_review_metrics"

SEMANTIC_SUPPORT = {"SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"}
ADMISSIBILITY = {
    "CURRENT_CONTRACT_ADMISSIBLE",
    "V2_CONTEXT_REQUIRED",
    "V2_ORDERED_SPAN_REQUIRED",
    "EVIDENCE_QUOTE_DRIFT_BLOCKED",
    "SOURCE_AMBIGUITY_BLOCKED",
}
FAILURE_CATEGORIES = {
    "TRUE_OVERREACH", "ATTRIBUTION_ERROR", "CONDITIONALITY_LOSS", "SCOPE_ERROR",
    "ENTITY_INFERENCE", "TECHNICAL_TERM_INFERENCE", "OTHER",
}
REVIEW_MODES = {
    "EXCERPT_ONLY", "BOUNDED_CONTEXT", "CROSS_PAGE", "QUOTE_DRIFT_SOURCE_REGION",
    "PROVENANCE_RECOVERY_REVIEW",
}
ATTRIBUTION_FAILURE_ORIGINS = {
    "MODEL_OUTPUT", "DETERMINISTIC_POSTPROCESSING", "MIXED_OR_UNCERTAIN",
}
CLAIM_COUNT_CATEGORIES = {
    "ATOMIC_SPLIT_OF_HISTORICAL_CONTENT",
    "NEW_VALID_PROPOSITION_PREVIOUSLY_MISSED",
    "DUPLICATE_OR_REDUNDANT",
    "FRAGMENTED_LOW_VALUE",
    "OTHER",
}
VERDICTS = {"PASS", "PASS_WITH_REMAINING_REPAIR", "FAIL"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_INVALID_JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_JSON_OBJECT_REQUIRED: {path}")
    return value


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100 * numerator / denominator, 2) if denominator else 0.0,
    }


def _tokens_per(total: Any, denominator: int) -> float | str:
    return round(total / denominator, 2) if isinstance(total, int) and denominator else "NOT_AVAILABLE"


def _tree_hashes(path: Path) -> dict[str, str]:
    path = Path(path).resolve()
    return {
        item.relative_to(path).as_posix(): sha256_file(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def _expected_decision(semantic_support: str, admissibility: str) -> str:
    if semantic_support == "UNSUPPORTED":
        return "DROP"
    if semantic_support == "SUPPORTED" and admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        return "KEEP"
    return "KEEP_NEEDS_REVIEW"


def _review_mode_is_valid(
    *, fidelity_status: str, admissibility: str, review_mode: str,
) -> bool:
    if fidelity_status == "QUOTE_DRIFT":
        return (
            admissibility == "EVIDENCE_QUOTE_DRIFT_BLOCKED"
            and review_mode == "QUOTE_DRIFT_SOURCE_REGION"
        )
    if fidelity_status == "EXACT_ORDERED_CROSS_PAGE_SPAN":
        return (
            admissibility == "V2_ORDERED_SPAN_REQUIRED"
            and review_mode == "CROSS_PAGE"
        )
    if fidelity_status == "PROVENANCE_MISMATCH_RECOVERED":
        return review_mode == "PROVENANCE_RECOVERY_REVIEW"
    if admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        return review_mode == "EXCERPT_ONLY"
    if admissibility in {"V2_CONTEXT_REQUIRED", "SOURCE_AMBIGUITY_BLOCKED"}:
        return review_mode == "BOUNDED_CONTEXT"
    return False


def build_reextraction_human_review_decisions(
    bundle_path: Path,
    quote_fidelity_path: Path,
    annotations_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Bind human annotations to immutable Claim, Evidence, and Gate A fields."""
    bundle = _load_json(Path(bundle_path))
    quote = _load_json(Path(quote_fidelity_path))
    annotations = _load_json(Path(annotations_path))
    if (
        bundle.get("pilot_run_id") != RUN_ID
        or quote.get("pilot_run_id") != RUN_ID
        or annotations.get("pilot_run_id") != RUN_ID
        or (bundle.get("source") or {}).get("sha256") != SOURCE_SHA256
        or quote.get("source_sha256") != SOURCE_SHA256
        or annotations.get("source_sha256") != SOURCE_SHA256
        or annotations.get("document_type") != ANNOTATIONS_DOCUMENT_TYPE
        or annotations.get("schema_version") != SCHEMA_VERSION
    ):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_ANNOTATION_BINDING_INVALID")

    bundle_claims = bundle.get("claims") or []
    gate_by_id = {item.get("claim_id"): item for item in quote.get("claims") or []}
    annotations_claims = annotations.get("claims") or []
    bundle_ids = [item.get("claim_id") for item in bundle_claims]
    if (
        len(bundle_ids) != 51
        or len(bundle_ids) != len(set(bundle_ids))
        or [item.get("claim_id") for item in annotations_claims] != bundle_ids
        or set(gate_by_id) != set(bundle_ids)
    ):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_ANNOTATION_COVERAGE_INVALID")

    claims = []
    for original, annotation in zip(bundle_claims, annotations_claims):
        claim_id = original["claim_id"]
        gate = gate_by_id[claim_id]
        primary = annotation.get("semantic_failure_category", "NONE")
        secondary = annotation.get("secondary_failure_categories") or []
        dimensions = set(secondary)
        if primary != "NONE":
            dimensions.add(primary)
        fidelity_status = gate.get("fidelity_status")
        is_quote_drift = fidelity_status == "QUOTE_DRIFT"
        nearest_region = None
        if is_quote_drift:
            nearest_region = (
                gate.get("nearest_deterministic_local_source_region")
                or gate.get("gate_a_source_locator")
                or gate.get("bound_page")
            )
        semantic_support = annotation.get("semantic_support")
        admissibility = annotation.get("evidence_admissibility")
        claims.append({
            "claim_id": claim_id,
            "original_claim": original.get("statement"),
            "immutable_evidence_excerpt": original.get("evidence_excerpt"),
            "gate_a_fidelity_status": fidelity_status,
            "semantic_support": semantic_support,
            "evidence_admissibility": admissibility,
            "human_decision": _expected_decision(semantic_support, admissibility),
            "semantic_failure_category": primary,
            "secondary_failure_categories": secondary,
            "attribution_error": "ATTRIBUTION_ERROR" in dimensions,
            "entity_inference": "ENTITY_INFERENCE" in dimensions,
            "technical_term_inference": "TECHNICAL_TERM_INFERENCE" in dimensions,
            "conditionality_loss": "CONDITIONALITY_LOSS" in dimensions,
            "attribution_failure_origin": annotation.get("attribution_failure_origin"),
            "atomicity_issue": annotation.get("atomicity_issue"),
            "atomicity_material_failure": annotation.get("atomicity_material_failure"),
            "quote_drift": is_quote_drift,
            "quote_drift_category": gate.get("primary_drift_category") if is_quote_drift else None,
            "nearest_deterministic_source_region_reference": nearest_region,
            "quote_drift_semantically_material": annotation.get(
                "quote_drift_semantically_material", False
            ),
            "provenance_diagnostic": (
                "MODEL_PAGE_POINTER_ERROR_ONLY"
                if fidelity_status == "PROVENANCE_MISMATCH_RECOVERED" else None
            ),
            "review_mode": annotation.get("review_mode"),
            "claim_count_diagnostic": annotation.get("claim_count_diagnostic"),
            "substantive_duplicate": annotation.get("substantive_duplicate", False),
            "redundant_low_value": annotation.get("redundant_low_value", False),
            "rationale": annotation.get("rationale"),
        })

    decisions = {
        "document_type": DECISIONS_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": RUN_ID,
        "historical_pilot_run_id": HISTORICAL_RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "repair_efficacy_verdict": annotations.get("repair_efficacy_verdict"),
        "repair_efficacy_rationale": annotations.get("repair_efficacy_rationale"),
        "independent_generalization_retest": annotations.get(
            "independent_generalization_retest"
        ),
        "claim_count_diagnostic_rationale": annotations.get(
            "claim_count_diagnostic_rationale"
        ),
        "coverage_diagnostic": copy.deepcopy(annotations.get("coverage_diagnostic")),
        "claims": claims,
    }
    write_json(Path(output_path), decisions)
    return decisions


def _metrics(
    bundle: dict[str, Any], reviewed_claims: list[dict[str, Any]],
    decisions: dict[str, Any], quote_artifact: dict[str, Any],
    reextraction_metrics: dict[str, Any], historical_metrics: dict[str, Any],
) -> dict[str, Any]:
    total = len(reviewed_claims)
    decisions_count = Counter(item["human_decision"] for item in reviewed_claims)
    semantic_count = Counter(item["semantic_support"] for item in reviewed_claims)
    admissibility_count = Counter(item["evidence_admissibility"] for item in reviewed_claims)
    primary_failures = Counter(
        item["semantic_failure_category"]
        for item in reviewed_claims
        if item["semantic_failure_category"] != "NONE"
    )
    any_failures = Counter()
    attribution_origins = Counter()
    for item in reviewed_claims:
        dimensions = set(item.get("secondary_failure_categories") or [])
        if item["semantic_failure_category"] != "NONE":
            dimensions.add(item["semantic_failure_category"])
        any_failures.update(dimensions)
        if item.get("attribution_failure_origin"):
            attribution_origins[item["attribution_failure_origin"]] += 1

    quote_claims = [item for item in reviewed_claims if item["quote_drift"]]
    provenance_claims = [
        item for item in reviewed_claims
        if item["gate_a_fidelity_status"] == "PROVENANCE_MISMATCH_RECOVERED"
    ]
    atomicity_issues = sum(item["atomicity_issue"] for item in reviewed_claims)
    material_atomicity = sum(item["atomicity_material_failure"] for item in reviewed_claims)
    count_diagnostic = Counter(item["claim_count_diagnostic"] for item in reviewed_claims)
    review_modes = Counter(item["review_mode"] for item in reviewed_claims)
    expanded_manual = total - review_modes["EXCERPT_ONLY"]
    supported = semantic_count["SUPPORTED"]
    keep = decisions_count["KEEP"]
    total_tokens = ((bundle.get("model") or {}).get("usage") or {}).get("total_tokens")
    coverage = decisions["coverage_diagnostic"]
    mutation_count = (
        (((reextraction_metrics.get("mechanical_diagnostics") or {}).get(
            "deterministic_company_to_speaker_mutations"
        ) or {}).get("count"))
    )
    return {
        "document_type": METRICS_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": RUN_ID,
        "historical_pilot_run_id": HISTORICAL_RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims_total": total,
        "claims_reviewed": total,
        "decision_counts": {
            name: decisions_count[name]
            for name in ("KEEP", "DROP", "KEEP_NEEDS_REVIEW", "PENDING")
        },
        "semantic_counts": {
            name: semantic_count[name] for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
        },
        "semantic_support_rate": _ratio(supported, total),
        "true_semantic_failure_rate": _ratio(semantic_count["UNSUPPORTED"], total),
        "historical_true_semantic_failure_rate": copy.deepcopy(
            historical_metrics["true_semantic_failure_rate"]
        ),
        "primary_semantic_failure_category_counts": {
            name: primary_failures[name] for name in sorted(FAILURE_CATEGORIES)
        },
        "semantic_failure_dimension_counts": {
            name: any_failures[name] for name in sorted(FAILURE_CATEGORIES)
        },
        "attribution": {
            "primary_errors": primary_failures["ATTRIBUTION_ERROR"],
            "any_dimension": any_failures["ATTRIBUTION_ERROR"],
            "error_rate": _ratio(any_failures["ATTRIBUTION_ERROR"], total),
            "deterministic_postprocessing": attribution_origins["DETERMINISTIC_POSTPROCESSING"],
            "model_output": attribution_origins["MODEL_OUTPUT"],
            "mixed_or_uncertain": attribution_origins["MIXED_OR_UNCERTAIN"],
            "known_company_to_speaker_mutation_recurrence": "YES" if mutation_count else "NO",
        },
        "atomicity": {
            "issues": atomicity_issues,
            "issue_rate": _ratio(atomicity_issues, total),
            "material_failures": material_atomicity,
            "material_failure_rate": _ratio(material_atomicity, total),
            "historical_issue_rate": copy.deepcopy(historical_metrics["atomicity"]["issue_rate"]),
            "historical_material_failure_rate": copy.deepcopy(
                historical_metrics["atomicity"]["material_failure_rate"]
            ),
        },
        "quote_fidelity": {
            "mechanical_counts": copy.deepcopy(quote_artifact["metrics"]["fidelity_counts"]),
            "quote_drift_total": len(quote_claims),
            "quote_drift_semantic_outcomes": {
                name: sum(item["semantic_support"] == name for item in quote_claims)
                for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
            },
            "quote_drift_semantically_material": sum(
                item["quote_drift_semantically_material"] for item in quote_claims
            ),
        },
        "provenance_recovery": {
            "total": len(provenance_claims),
            "semantic_outcomes": {
                name: sum(item["semantic_support"] == name for item in provenance_claims)
                for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
            },
            "model_page_pointer_error_only": sum(
                item.get("provenance_diagnostic") == "MODEL_PAGE_POINTER_ERROR_ONLY"
                for item in provenance_claims
            ),
            "semantic_issue_cooccurs": sum(
                item["semantic_support"] != "SUPPORTED" for item in provenance_claims
            ),
        },
        "evidence_admissibility_counts": {
            name: admissibility_count[name] for name in sorted(ADMISSIBILITY)
        },
        "strict_current_contract_keep_rate": _ratio(keep, total),
        "claim_count_diagnostic": {
            "historical_claims": 29,
            "reextraction_claims": total,
            "counts": {name: count_diagnostic[name] for name in sorted(CLAIM_COUNT_CATEGORIES)},
            "substantive_duplicate_claims": sum(
                item["substantive_duplicate"] for item in reviewed_claims
            ),
            "redundant_low_value_claims": sum(
                item["redundant_low_value"] for item in reviewed_claims
            ),
            "rationale": decisions["claim_count_diagnostic_rationale"],
        },
        "coverage_diagnostic": copy.deepcopy(coverage),
        "token_economics": {
            "historical_total_tokens": historical_metrics["token_economics"][
                "pilot2_extraction_total_tokens"
            ],
            "reextraction_total_tokens": total_tokens,
            "historical_tokens_per_claim": historical_metrics["token_economics"][
                "tokens_per_claim"
            ],
            "reextraction_tokens_per_claim": _tokens_per(total_tokens, total),
            "tokens_per_semantically_supported_claim": _tokens_per(total_tokens, supported),
            "tokens_per_current_contract_keep_claim": _tokens_per(total_tokens, keep),
        },
        "human_review_burden": {
            "EXCERPT_ONLY": review_modes["EXCERPT_ONLY"],
            "BOUNDED_CONTEXT": review_modes["BOUNDED_CONTEXT"],
            "CROSS_PAGE": review_modes["CROSS_PAGE"],
            "QUOTE_DRIFT_SOURCE_REGION": review_modes["QUOTE_DRIFT_SOURCE_REGION"],
            "PROVENANCE_RECOVERY_REVIEW": review_modes["PROVENANCE_RECOVERY_REVIEW"],
            "expanded_manual_evidence_review": expanded_manual,
            "expanded_manual_rate": _ratio(expanded_manual, total),
            "historical_expanded_manual_evidence_review": historical_metrics[
                "human_review_burden"
            ]["expanded_manual_evidence_review"],
            "categories_are_mutually_exclusive": sum(review_modes.values()) == total,
        },
        "REPAIR_EFFICACY_VERDICT": decisions["repair_efficacy_verdict"],
        "repair_efficacy_rationale": decisions["repair_efficacy_rationale"],
        "independent_generalization_retest": "NOT_YET_PERFORMED",
        "llm_calls_added": 0,
        "reextraction_rerun": False,
        "pilot3_executed": False,
        "production_write": False,
        "production_schema_changed": False,
        "canonical_claim_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
        "PRODUCTION_APPLY_READY": "NO",
    }


def _render_report(ready: dict[str, Any]) -> str:
    metrics = ready["metrics"]
    semantic = metrics["semantic_counts"]
    decisions = metrics["decision_counts"]
    failure = metrics["primary_semantic_failure_category_counts"]
    attribution = metrics["attribution"]
    atomicity = metrics["atomicity"]
    quote = metrics["quote_fidelity"]
    provenance = metrics["provenance_recovery"]
    admissibility = metrics["evidence_admissibility_counts"]
    count_diagnostic = metrics["claim_count_diagnostic"]
    coverage = metrics["coverage_diagnostic"]
    tokens = metrics["token_economics"]
    burden = metrics["human_review_burden"]
    invariants = metrics["invariants"]
    lines = [
        "# Phase 3C Pilot #2 Controlled Re-extraction Human Review", "",
        "## Outcome", "",
        f"- Claims reviewed: {metrics['claims_reviewed']}",
        f"- Pending: {decisions['PENDING']}",
        f"- Decisions KEEP / DROP / KEEP_NEEDS_REVIEW: {decisions['KEEP']} / {decisions['DROP']} / {decisions['KEEP_NEEDS_REVIEW']}",
        f"- Semantic SUPPORTED / UNSUPPORTED / AMBIGUOUS: {semantic['SUPPORTED']} / {semantic['UNSUPPORTED']} / {semantic['AMBIGUOUS']}",
        f"- Semantic support rate: {metrics['semantic_support_rate']['fraction']} ({metrics['semantic_support_rate']['percent']}%)",
        f"- Semantic failure rate: {metrics['true_semantic_failure_rate']['fraction']} ({metrics['true_semantic_failure_rate']['percent']}%)",
        f"- Historical semantic failure rate: {metrics['historical_true_semantic_failure_rate']['fraction']} ({metrics['historical_true_semantic_failure_rate']['percent']}%)",
        f"- Strict current-contract KEEP rate: {metrics['strict_current_contract_keep_rate']['fraction']} ({metrics['strict_current_contract_keep_rate']['percent']}%)",
        f"- Repair efficacy verdict: `{metrics['REPAIR_EFFICACY_VERDICT']}`", "",
        "## Repair efficacy", "",
        f"- Known company-to-speaker deterministic recurrence: `{attribution['known_company_to_speaker_mutation_recurrence']}`",
        f"- Attribution errors, primary / any dimension: {attribution['primary_errors']} / {attribution['any_dimension']}",
        f"- Attribution origin, deterministic / model / mixed: {attribution['deterministic_postprocessing']} / {attribution['model_output']} / {attribution['mixed_or_uncertain']}",
        f"- Atomicity issues: {atomicity['issue_rate']['fraction']} ({atomicity['issue_rate']['percent']}%); historical {atomicity['historical_issue_rate']['percent']}%",
        f"- Material atomicity failures: {atomicity['material_failure_rate']['fraction']} ({atomicity['material_failure_rate']['percent']}%); historical {atomicity['historical_material_failure_rate']['percent']}%",
        f"- Rationale: {metrics['repair_efficacy_rationale']}", "",
        "## Primary semantic failures", "",
    ]
    lines += [f"- {name}: {failure[name]}" for name in sorted(failure)]
    lines += [
        "", "## Evidence", "",
        f"- Mechanical fidelity counts: `{json.dumps(quote['mechanical_counts'], ensure_ascii=False)}`",
        f"- Quote drift total: {quote['quote_drift_total']}; semantic outcomes: `{json.dumps(quote['quote_drift_semantic_outcomes'], ensure_ascii=False)}`",
        f"- Semantically material quote drift: {quote['quote_drift_semantically_material']}",
        f"- Provenance recovery total: {provenance['total']}; semantic outcomes: `{json.dumps(provenance['semantic_outcomes'], ensure_ascii=False)}`",
        f"- Model page-pointer-only diagnostics: {provenance['model_page_pointer_error_only']}; semantic issue co-occurs: {provenance['semantic_issue_cooccurs']}",
        f"- Evidence admissibility: `{json.dumps(admissibility, ensure_ascii=False)}`", "",
        "## Claim-count and coverage diagnostic", "",
        f"- Historical / re-extraction Claims: {count_diagnostic['historical_claims']} / {count_diagnostic['reextraction_claims']}",
        f"- Structural counts: `{json.dumps(count_diagnostic['counts'], ensure_ascii=False)}`",
        f"- Substantive duplicates / redundant low-value: {count_diagnostic['substantive_duplicate_claims']} / {count_diagnostic['redundant_low_value_claims']}",
        f"- Diagnostic: {count_diagnostic['rationale']}",
        f"- Historical supported concepts retained / lost: {coverage['historical_supported_concepts_retained']} / {coverage['historical_supported_concepts_lost']}",
        f"- Useful new propositions: {coverage['useful_new_propositions']}",
        f"- Precision/recall claim: `{coverage['precision_or_recall_claim']}`", "",
        "## Token economics and human-review burden", "",
        f"- Total tokens, historical / re-extraction: {tokens['historical_total_tokens']} / {tokens['reextraction_total_tokens']}",
        f"- Tokens per Claim, historical / re-extraction: {tokens['historical_tokens_per_claim']} / {tokens['reextraction_tokens_per_claim']}",
        f"- Re-extraction tokens per supported Claim: {tokens['tokens_per_semantically_supported_claim']}",
        f"- Re-extraction tokens per current-contract KEEP: {tokens['tokens_per_current_contract_keep_claim']}",
        f"- Review modes: `{json.dumps({name: burden[name] for name in REVIEW_MODES}, ensure_ascii=False)}`",
        f"- Expanded/manual review: {burden['expanded_manual_rate']['fraction']} ({burden['expanded_manual_rate']['percent']}%); historical {burden['historical_expanded_manual_evidence_review']}/29", "",
        "## Immutability and isolation", "",
        f"- Invariants: `{json.dumps(invariants, ensure_ascii=False)}`",
        f"- Production pre/post SHA256: `{metrics['production_pre']['sha256']}` / `{metrics['production_post']['sha256']}`",
        f"- Production integrity / foreign-key violations: `{metrics['production_post']['integrity_check']}` / {len(metrics['production_post']['foreign_key_violations'])}", "",
        "## Safety", "",
        "- LLM calls added: `0`; re-extraction rerun: `NO`; Pilot #3: `NO`",
        "- Production / IMA / propagation / legacy pipeline: `NO / NO / NO / NO`",
        "- Independent generalization re-test: `NOT_YET_PERFORMED`",
        "- PRODUCTION_APPLY_READY: `NO`", "",
        f"PHASE3C_NEXT_GATE = `{ready['PHASE3C_NEXT_GATE']}`", "",
        "## Decision register", "",
        "| Claim ID | Semantic | Evidence admissibility | Decision | Primary failure | Atomic / material | Review mode |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        "| {claim_id} | {semantic_support} | {evidence_admissibility} | {human_decision} | "
        "{semantic_failure_category} | {atomicity_issue} / {atomicity_material_failure} | "
        "{review_mode} |".format(**item)
        for item in ready["claims"]
    ]
    lines.append("")
    return "\n".join(lines)


def _render_comparison(metrics: dict[str, Any]) -> str:
    historical_failure = metrics["historical_true_semantic_failure_rate"]
    current_failure = metrics["true_semantic_failure_rate"]
    atomicity = metrics["atomicity"]
    token = metrics["token_economics"]
    decisions = metrics["decision_counts"]
    semantic = metrics["semantic_counts"]
    burden = metrics["human_review_burden"]
    return "\n".join([
        "# Historical Pilot #2 vs Controlled Re-extraction — Semantic Comparison", "",
        "This same-Source comparison measures repair efficacy, not independent generalization.", "",
        "| Metric | Historical | Controlled re-extraction |",
        "|---|---:|---:|",
        f"| Claims | 29 | {metrics['claims_total']} |",
        f"| SUPPORTED / UNSUPPORTED / AMBIGUOUS | 19 / 10 / 0 | {semantic['SUPPORTED']} / {semantic['UNSUPPORTED']} / {semantic['AMBIGUOUS']} |",
        f"| KEEP / DROP / KEEP_NEEDS_REVIEW | 5 / 10 / 14 | {decisions['KEEP']} / {decisions['DROP']} / {decisions['KEEP_NEEDS_REVIEW']} |",
        f"| True semantic failure rate | {historical_failure['percent']}% | {current_failure['percent']}% |",
        f"| Attribution errors (primary) | 8 | {metrics['attribution']['primary_errors']} |",
        f"| Attribution errors (any dimension) | 9 | {metrics['attribution']['any_dimension']} |",
        f"| Atomicity issue rate | {atomicity['historical_issue_rate']['percent']}% | {atomicity['issue_rate']['percent']}% |",
        f"| Material atomicity failure rate | {atomicity['historical_material_failure_rate']['percent']}% | {atomicity['material_failure_rate']['percent']}% |",
        f"| Quote drift | 7/29 | {metrics['quote_fidelity']['quote_drift_total']}/{metrics['claims_total']} |",
        f"| Expanded/manual evidence review | 19/29 | {burden['expanded_manual_evidence_review']}/{metrics['claims_total']} |",
        f"| Total tokens | {token['historical_total_tokens']} | {token['reextraction_total_tokens']} |",
        f"| Tokens per Claim | {token['historical_tokens_per_claim']} | {token['reextraction_tokens_per_claim']} |", "",
        f"Re-extraction tokens per supported Claim: {token['tokens_per_semantically_supported_claim']}; historical: 2093.79.", "",
        f"Re-extraction tokens per current-contract KEEP: {token['tokens_per_current_contract_keep_claim']}; historical: 7956.40.", "",
        f"Claim-count diagnostic: `{json.dumps(metrics['claim_count_diagnostic']['counts'], ensure_ascii=False)}`.", "",
        f"Coverage: retained {metrics['coverage_diagnostic']['historical_supported_concepts_retained']} major historical supported concepts, lost {metrics['coverage_diagnostic']['historical_supported_concepts_lost']}, and added {metrics['coverage_diagnostic']['useful_new_propositions']} useful propositions. No precision/recall statistic is claimed.", "",
        f"Repair efficacy verdict: `{metrics['REPAIR_EFFICACY_VERDICT']}`.", "",
        "Independent generalization re-test: `NOT_YET_PERFORMED`.", "",
    ])


def close_reextraction_human_review(
    bundle_path: Path,
    evidence_draft_path: Path,
    quote_fidelity_path: Path,
    reextraction_metrics_path: Path,
    decisions_path: Path,
    historical_run_dir: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Close the 51-Claim review without LLM, extraction, or canonical side effects."""
    paths = {
        "bundle": Path(bundle_path).resolve(),
        "evidence_draft": Path(evidence_draft_path).resolve(),
        "quote_fidelity": Path(quote_fidelity_path).resolve(),
        "reextraction_metrics": Path(reextraction_metrics_path).resolve(),
        "decisions": Path(decisions_path).resolve(),
    }
    if any(not path.is_file() for path in paths.values()):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_INPUT_MISSING")
    input_hashes = {name: sha256_file(path) for name, path in paths.items()}
    historical_run_dir = Path(historical_run_dir).resolve()
    historical_metrics_path = historical_run_dir / "pilot2_human_review_metrics.json"
    if not historical_metrics_path.is_file():
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_HISTORICAL_METRICS_MISSING")
    historical_hashes_pre = _tree_hashes(historical_run_dir)
    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None

    bundle = _load_json(paths["bundle"])
    evidence_draft = _load_json(paths["evidence_draft"])
    quote = _load_json(paths["quote_fidelity"])
    reextraction_metrics = _load_json(paths["reextraction_metrics"])
    decisions = _load_json(paths["decisions"])
    historical_metrics = _load_json(historical_metrics_path)
    if (
        bundle.get("pilot_run_id") != RUN_ID
        or evidence_draft.get("pilot_run_id") != RUN_ID
        or quote.get("pilot_run_id") != RUN_ID
        or reextraction_metrics.get("pilot_run_id") != RUN_ID
        or decisions.get("pilot_run_id") != RUN_ID
        or (bundle.get("source") or {}).get("sha256") != SOURCE_SHA256
        or decisions.get("source_sha256") != SOURCE_SHA256
    ):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_BINDING_INVALID")
    if (
        decisions.get("document_type") != DECISIONS_DOCUMENT_TYPE
        or decisions.get("schema_version") != SCHEMA_VERSION
        or decisions.get("repair_efficacy_verdict") not in VERDICTS
        or decisions.get("independent_generalization_retest") != "NOT_YET_PERFORMED"
    ):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_DECISIONS_INVALID")

    bundle_claims = bundle.get("claims") or []
    evidence_by_id = {item.get("claim_id"): item for item in evidence_draft.get("claims") or []}
    quote_by_id = {item.get("claim_id"): item for item in quote.get("claims") or []}
    decision_claims = decisions.get("claims") or []
    bundle_ids = [item.get("claim_id") for item in bundle_claims]
    if (
        len(bundle_ids) != 51
        or len(bundle_ids) != len(set(bundle_ids))
        or [item.get("claim_id") for item in decision_claims] != bundle_ids
        or set(evidence_by_id) != set(bundle_ids)
        or set(quote_by_id) != set(bundle_ids)
    ):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_CLAIM_COVERAGE_INVALID")

    reviewed_claims = []
    for original, selected in zip(bundle_claims, decision_claims):
        claim_id = original["claim_id"]
        evidence = evidence_by_id[claim_id]
        gate = quote_by_id[claim_id]
        if evidence.get("original_evidence_excerpt") != original.get("evidence_excerpt"):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_EVIDENCE_INPUT_CHANGED: {claim_id}")
        if selected.get("original_claim") != original.get("statement"):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_CLAIM_CHANGED: {claim_id}")
        if selected.get("immutable_evidence_excerpt") != original.get("evidence_excerpt"):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_EVIDENCE_CHANGED: {claim_id}")
        if selected.get("gate_a_fidelity_status") != gate.get("fidelity_status"):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_FIDELITY_CHANGED: {claim_id}")

        semantic_support = selected.get("semantic_support")
        admissibility = selected.get("evidence_admissibility")
        primary = selected.get("semantic_failure_category")
        secondary = selected.get("secondary_failure_categories") or []
        review_mode = selected.get("review_mode")
        if semantic_support not in SEMANTIC_SUPPORT or admissibility not in ADMISSIBILITY:
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_AXIS_INVALID: {claim_id}")
        if primary != "NONE" and primary not in FAILURE_CATEGORIES:
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_PRIMARY_FAILURE_INVALID: {claim_id}")
        if len(secondary) != len(set(secondary)) or any(item not in FAILURE_CATEGORIES for item in secondary):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_SECONDARY_FAILURE_INVALID: {claim_id}")
        if semantic_support == "UNSUPPORTED" and primary == "NONE":
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_FAILURE_REQUIRED: {claim_id}")
        if semantic_support != "UNSUPPORTED" and primary != "NONE":
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_FALSE_FAILURE: {claim_id}")
        if selected.get("human_decision") != _expected_decision(semantic_support, admissibility):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_DECISION_INCONSISTENT: {claim_id}")
        if semantic_support == "AMBIGUOUS" and admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_AMBIGUITY_NOT_BLOCKED: {claim_id}")
        if review_mode not in REVIEW_MODES or not _review_mode_is_valid(
            fidelity_status=gate["fidelity_status"],
            admissibility=admissibility,
            review_mode=review_mode,
        ):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_MODE_INVALID: {claim_id}")

        is_quote_drift = gate["fidelity_status"] == "QUOTE_DRIFT"
        if selected.get("quote_drift") is not is_quote_drift:
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_QUOTE_FLAG_INVALID: {claim_id}")
        if is_quote_drift:
            if (
                selected.get("quote_drift_category") != gate.get("primary_drift_category")
                or not selected.get("nearest_deterministic_source_region_reference")
                or not isinstance(selected.get("quote_drift_semantically_material"), bool)
            ):
                raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_QUOTE_DETAIL_INVALID: {claim_id}")
        elif (
            selected.get("quote_drift_category") is not None
            or selected.get("nearest_deterministic_source_region_reference") is not None
            or selected.get("quote_drift_semantically_material") is not False
        ):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_FALSE_QUOTE_DETAIL: {claim_id}")

        dimensions = set(secondary)
        if primary != "NONE":
            dimensions.add(primary)
        dimension_flags = {
            "ATTRIBUTION_ERROR": "attribution_error",
            "ENTITY_INFERENCE": "entity_inference",
            "TECHNICAL_TERM_INFERENCE": "technical_term_inference",
            "CONDITIONALITY_LOSS": "conditionality_loss",
        }
        if any(selected.get(field) is not (category in dimensions) for category, field in dimension_flags.items()):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_FAILURE_FLAG_INVALID: {claim_id}")
        origin = selected.get("attribution_failure_origin")
        if selected["attribution_error"]:
            if origin not in ATTRIBUTION_FAILURE_ORIGINS:
                raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_ATTRIBUTION_ORIGIN_REQUIRED: {claim_id}")
        elif origin is not None:
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_FALSE_ATTRIBUTION_ORIGIN: {claim_id}")

        atomicity_issue = selected.get("atomicity_issue")
        material_atomicity = selected.get("atomicity_material_failure")
        if not isinstance(atomicity_issue, bool) or not isinstance(material_atomicity, bool):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_ATOMICITY_INVALID: {claim_id}")
        if material_atomicity and (not atomicity_issue or semantic_support != "UNSUPPORTED"):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_MATERIAL_ATOMICITY_INVALID: {claim_id}")
        if selected.get("claim_count_diagnostic") not in CLAIM_COUNT_CATEGORIES:
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_COUNT_DIAGNOSTIC_INVALID: {claim_id}")
        if not isinstance(selected.get("substantive_duplicate"), bool) or not isinstance(
            selected.get("redundant_low_value"), bool
        ):
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_REDUNDANCY_INVALID: {claim_id}")
        if not isinstance(selected.get("rationale"), str) or not selected["rationale"].strip():
            raise PilotError(f"REEXTRACTION_HUMAN_REVIEW_RATIONALE_REQUIRED: {claim_id}")
        reviewed_claims.append(copy.deepcopy(selected))

    metrics = _metrics(
        bundle, reviewed_claims, decisions, quote, reextraction_metrics, historical_metrics,
    )
    recurrence = metrics["attribution"]["known_company_to_speaker_mutation_recurrence"]
    if recurrence == "YES" and metrics["REPAIR_EFFICACY_VERDICT"] != "FAIL":
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_ATTRIBUTION_RECURRENCE_REQUIRES_FAIL")
    if metrics["REPAIR_EFFICACY_VERDICT"] == "PASS" and (
        metrics["true_semantic_failure_rate"]["numerator"]
        or metrics["quote_fidelity"]["quote_drift_total"]
        or metrics["provenance_recovery"]["total"]
    ):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_PASS_HAS_REMAINING_REPAIRS")

    next_gate = {
        "PASS": "Independent Generalization Pilot Authorization",
        "PASS_WITH_REMAINING_REPAIR": "Resolve Remaining Re-extraction Quality Defects",
        "FAIL": "Reopen Gate B Semantic Failure Repair",
    }[metrics["REPAIR_EFFICACY_VERDICT"]]
    ready = {
        "document_type": READY_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "READY",
        "pilot_run_id": RUN_ID,
        "historical_pilot_run_id": HISTORICAL_RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims": reviewed_claims,
        "metrics": metrics,
        "bindings": {
            **{f"{name}_file_sha256": digest for name, digest in input_hashes.items()},
            "source_sha256": SOURCE_SHA256,
        },
        "policy": {
            "two_axis_review": True,
            "semantic_support_independent_of_quote_fidelity": True,
            "quote_drift_not_automatic_semantic_failure": True,
            "provenance_recovery_not_automatic_semantic_failure": True,
            "ambiguous_claims_not_silently_accepted": True,
            "original_claim_and_evidence_immutable": True,
            "production_apply_ready": False,
        },
        "PHASE3C_NEXT_GATE": next_gate,
    }

    output_dir = Path(output_dir or paths["decisions"].parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ready_path = output_dir / "reextraction_human_review_ready.json"
    metrics_path = output_dir / "reextraction_human_review_metrics.json"
    report_path = output_dir / "reextraction_human_review_report.md"
    comparison_path = output_dir / "historical_vs_reextraction_semantic_comparison.md"
    input_unchanged = input_hashes == {name: sha256_file(path) for name, path in paths.items()}
    historical_hashes_post = _tree_hashes(historical_run_dir)
    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    invariants = {
        "all_decisions_explicit": len(reviewed_claims) == 51,
        "pending_zero": metrics["decision_counts"]["PENDING"] == 0,
        "claim_ids_unchanged": [item["claim_id"] for item in reviewed_claims] == bundle_ids,
        "raw_claims_unchanged": all(
            selected["original_claim"] == original["statement"]
            for selected, original in zip(reviewed_claims, bundle_claims)
        ),
        "raw_evidence_unchanged": all(
            selected["immutable_evidence_excerpt"] == original["evidence_excerpt"]
            for selected, original in zip(reviewed_claims, bundle_claims)
        ),
        "input_artifacts_unchanged": input_unchanged,
        "historical_artifacts_unchanged": historical_hashes_pre == historical_hashes_post,
        "production_unchanged": production_pre == production_post if production_pre else None,
    }
    metrics["invariants"] = invariants
    metrics["production_pre"] = production_pre
    metrics["production_post"] = production_post
    metrics["historical_hashes_pre"] = historical_hashes_pre
    metrics["historical_hashes_post"] = historical_hashes_post
    ready["metrics"] = metrics
    write_json(ready_path, ready)
    write_json(metrics_path, metrics)
    if not all(value is True for value in invariants.values()):
        raise PilotError("REEXTRACTION_HUMAN_REVIEW_INVARIANT_FAILED")
    report_path.write_text(_render_report(ready), encoding="utf-8")
    comparison_path.write_text(_render_comparison(metrics), encoding="utf-8")
    return {
        "status": "READY",
        "ready": ready,
        "metrics": metrics,
        "ready_path": str(ready_path),
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "comparison_path": str(comparison_path),
        "production_unchanged": invariants["production_unchanged"],
        "historical_artifacts_unchanged": invariants["historical_artifacts_unchanged"],
    }
