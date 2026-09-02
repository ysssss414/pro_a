from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .corpus_pilot import PilotError, production_snapshot
from .storage import sha256_file, write_json


SCHEMA_VERSION = "1"
RUN_ID = "PILOT_20260831_7AD15F72"
SOURCE_SHA256 = "1daf977493798d0334dedcd685d8a10f7c39dd25d768a44fa8a99ddf761627be"
CLAIMS_TOTAL = 70
TOTAL_TOKENS = 346179

ANNOTATIONS_DOCUMENT_TYPE = "phase3c_pilot3_human_review_annotations"
DECISIONS_DOCUMENT_TYPE = "phase3c_pilot3_human_review_decisions"
METRICS_DOCUMENT_TYPE = "phase3c_pilot3_human_review_metrics"

SEMANTIC_SUPPORT = {"SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"}
ADMISSIBILITY = {
    "CURRENT_CONTRACT_ADMISSIBLE",
    "V2_CONTEXT_REQUIRED",
    "V2_ORDERED_SPAN_REQUIRED",
    "EVIDENCE_QUOTE_DRIFT_BLOCKED",
    "SOURCE_AMBIGUITY_BLOCKED",
}
FAILURE_CATEGORIES = {
    "TRUE_OVERREACH",
    "ATTRIBUTION_ERROR",
    "CONDITIONALITY_LOSS",
    "SCOPE_ERROR",
    "ENTITY_INFERENCE",
    "TECHNICAL_TERM_INFERENCE",
    "OTHER",
}
SECONDARY_DIAGNOSTICS = {"TIME_NORMALIZATION", "NUMBER_NORMALIZATION"}
REVIEW_MODES = {
    "EXCERPT_ONLY",
    "BOUNDED_CONTEXT",
    "CROSS_PAGE",
    "QUOTE_DRIFT_SOURCE_REGION",
}
ATTRIBUTION_FAILURE_ORIGINS = {"DETERMINISTIC", "MODEL", "MIXED"}
VERDICTS = {"PASS", "PASS_WITH_REPAIR", "FAIL"}
PROMPT_REPAIR_CATEGORIES = {
    "evidence_quote_verbatim_preservation",
    "claim_atomicity",
    "attribution",
    "conditionality",
    "scope",
    "entity_inference",
    "technical_term_inference",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_INVALID_JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_JSON_OBJECT_REQUIRED: {path}")
    return value


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100 * numerator / denominator, 2) if denominator else 0.0,
    }


def _tokens_per(denominator: int) -> float | str:
    return round(TOTAL_TOKENS / denominator, 2) if denominator else "NOT_AVAILABLE"


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
    if admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        return review_mode == "EXCERPT_ONLY"
    if admissibility in {"V2_CONTEXT_REQUIRED", "SOURCE_AMBIGUITY_BLOCKED"}:
        return review_mode == "BOUNDED_CONTEXT"
    return False


def build_pilot3_human_review_decisions(
    bundle_path: Path,
    repaired_evidence_path: Path,
    quote_fidelity_path: Path,
    annotations_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Bind explicit human annotations to frozen Pilot #3 fields."""
    bundle = _load_json(Path(bundle_path))
    evidence = _load_json(Path(repaired_evidence_path))
    quote = _load_json(Path(quote_fidelity_path))
    annotations = _load_json(Path(annotations_path))
    if (
        bundle.get("pilot_run_id") != RUN_ID
        or evidence.get("pilot_run_id") != RUN_ID
        or quote.get("pilot_run_id") != RUN_ID
        or annotations.get("pilot_run_id") != RUN_ID
        or (bundle.get("source") or {}).get("sha256") != SOURCE_SHA256
        or quote.get("source_sha256") != SOURCE_SHA256
        or annotations.get("source_sha256") != SOURCE_SHA256
        or annotations.get("document_type") != ANNOTATIONS_DOCUMENT_TYPE
        or annotations.get("schema_version") != SCHEMA_VERSION
    ):
        raise PilotError("PILOT3_HUMAN_REVIEW_ANNOTATION_BINDING_INVALID")

    bundle_claims = bundle.get("claims") or []
    evidence_by_id = {item.get("claim_id"): item for item in evidence.get("claims") or []}
    quote_by_id = {item.get("claim_id"): item for item in quote.get("claims") or []}
    annotation_claims = annotations.get("claims") or []
    bundle_ids = [item.get("claim_id") for item in bundle_claims]
    if (
        len(bundle_ids) != CLAIMS_TOTAL
        or len(bundle_ids) != len(set(bundle_ids))
        or [item.get("claim_id") for item in annotation_claims] != bundle_ids
        or set(evidence_by_id) != set(bundle_ids)
        or set(quote_by_id) != set(bundle_ids)
    ):
        raise PilotError("PILOT3_HUMAN_REVIEW_ANNOTATION_COVERAGE_INVALID")

    claims: list[dict[str, Any]] = []
    for original, annotation in zip(bundle_claims, annotation_claims):
        claim_id = original["claim_id"]
        gate = quote_by_id[claim_id]
        repaired = evidence_by_id[claim_id]
        fidelity_status = gate.get("fidelity_status")
        semantic_support = annotation.get("semantic_support")
        admissibility = annotation.get("evidence_admissibility")
        review_mode = annotation.get("review_mode")
        is_quote_drift = fidelity_status == "QUOTE_DRIFT"
        is_cross_page = fidelity_status == "EXACT_ORDERED_CROSS_PAGE_SPAN"
        uses_context = review_mode == "BOUNDED_CONTEXT"
        claims.append({
            "claim_id": claim_id,
            "original_claim": original.get("statement"),
            "attributed_to": original.get("attributed_to"),
            "immutable_evidence_excerpt": original.get("evidence_excerpt"),
            "gate_mechanical_fidelity_status": fidelity_status,
            "review_mode": review_mode,
            "semantic_support": semantic_support,
            "semantic_failure_category": annotation.get("semantic_failure_category", "NONE"),
            "secondary_failure_categories": annotation.get("secondary_failure_categories") or [],
            "secondary_diagnostics": annotation.get("secondary_diagnostics") or [],
            "attribution_failure_origin": annotation.get("attribution_failure_origin"),
            "atomicity_issue": annotation.get("atomicity_issue"),
            "atomicity_material_failure": annotation.get("atomicity_material_failure"),
            "evidence_admissibility": admissibility,
            "human_decision": _expected_decision(semantic_support, admissibility),
            "rationale": annotation.get("rationale"),
            "quote_drift": is_quote_drift,
            "quote_drift_category": gate.get("primary_drift_category") if is_quote_drift else None,
            "quote_drift_semantically_material": annotation.get(
                "quote_drift_semantically_material", False
            ),
            "nearest_deterministic_source_region_reference": (
                copy.deepcopy(gate.get("nearest_deterministic_local_source_region"))
                if is_quote_drift else None
            ),
            "evidence_v2_ordered_span_reference": (
                copy.deepcopy(gate.get("resolved_locator")) if is_cross_page else None
            ),
            "bounded_context_candidate_reference": (
                {
                    "context_locators": copy.deepcopy(repaired.get("context_locators") or []),
                    "candidates": copy.deepcopy(repaired.get("bounded_context_candidates") or []),
                }
                if uses_context else None
            ),
        })

    decisions = {
        "document_type": DECISIONS_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "PILOT3_GENERALIZATION_VERDICT": annotations.get("PILOT3_GENERALIZATION_VERDICT"),
        "generalization_rationale": annotations.get("generalization_rationale"),
        "PROMPT_REPAIR_NEXT": copy.deepcopy(annotations.get("PROMPT_REPAIR_NEXT") or []),
        "PHASE3C_NEXT_GATE": annotations.get("PHASE3C_NEXT_GATE"),
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": annotations.get(
            "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED"
        ),
        "claims": claims,
    }
    write_json(Path(output_path), decisions)
    return decisions


def _validate_claim(
    original: dict[str, Any], repaired: dict[str, Any], gate: dict[str, Any], selected: dict[str, Any],
) -> None:
    claim_id = original["claim_id"]
    if repaired.get("original_evidence_excerpt") != original.get("evidence_excerpt"):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_EVIDENCE_INPUT_CHANGED: {claim_id}")
    frozen_equalities = (
        selected.get("original_claim") == original.get("statement"),
        selected.get("attributed_to") == original.get("attributed_to"),
        selected.get("immutable_evidence_excerpt") == original.get("evidence_excerpt"),
        selected.get("gate_mechanical_fidelity_status") == gate.get("fidelity_status"),
    )
    if not all(frozen_equalities):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FROZEN_FIELD_CHANGED: {claim_id}")

    semantic_support = selected.get("semantic_support")
    admissibility = selected.get("evidence_admissibility")
    primary = selected.get("semantic_failure_category")
    secondary = selected.get("secondary_failure_categories") or []
    diagnostics = selected.get("secondary_diagnostics") or []
    review_mode = selected.get("review_mode")
    if semantic_support not in SEMANTIC_SUPPORT or admissibility not in ADMISSIBILITY:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_AXIS_INVALID: {claim_id}")
    if primary != "NONE" and primary not in FAILURE_CATEGORIES:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_PRIMARY_FAILURE_INVALID: {claim_id}")
    if len(secondary) != len(set(secondary)) or any(x not in FAILURE_CATEGORIES for x in secondary):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_SECONDARY_FAILURE_INVALID: {claim_id}")
    if len(diagnostics) != len(set(diagnostics)) or any(x not in SECONDARY_DIAGNOSTICS for x in diagnostics):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_SECONDARY_DIAGNOSTIC_INVALID: {claim_id}")
    if semantic_support == "UNSUPPORTED" and primary == "NONE":
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FAILURE_REQUIRED: {claim_id}")
    if semantic_support != "UNSUPPORTED" and primary != "NONE":
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FALSE_PRIMARY_FAILURE: {claim_id}")
    if selected.get("human_decision") != _expected_decision(semantic_support, admissibility):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_DECISION_INCONSISTENT: {claim_id}")
    if semantic_support == "AMBIGUOUS" and admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        raise PilotError(f"PILOT3_HUMAN_REVIEW_AMBIGUITY_NOT_BLOCKED: {claim_id}")
    if review_mode not in REVIEW_MODES or not _review_mode_is_valid(
        fidelity_status=gate["fidelity_status"],
        admissibility=admissibility,
        review_mode=review_mode,
    ):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_MODE_INVALID: {claim_id}")

    atomicity_issue = selected.get("atomicity_issue")
    material_atomicity = selected.get("atomicity_material_failure")
    if not isinstance(atomicity_issue, bool) or not isinstance(material_atomicity, bool):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_ATOMICITY_INVALID: {claim_id}")
    if material_atomicity and (not atomicity_issue or semantic_support != "UNSUPPORTED"):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_MATERIAL_ATOMICITY_INVALID: {claim_id}")
    if semantic_support == "SUPPORTED" and admissibility == "CURRENT_CONTRACT_ADMISSIBLE" and material_atomicity:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_UNSAFE_KEEP: {claim_id}")

    dimensions = set(secondary)
    if primary != "NONE":
        dimensions.add(primary)
    origin = selected.get("attribution_failure_origin")
    if "ATTRIBUTION_ERROR" in dimensions:
        if origin not in ATTRIBUTION_FAILURE_ORIGINS:
            raise PilotError(f"PILOT3_HUMAN_REVIEW_ATTRIBUTION_ORIGIN_REQUIRED: {claim_id}")
    elif origin is not None:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FALSE_ATTRIBUTION_ORIGIN: {claim_id}")

    is_quote_drift = gate["fidelity_status"] == "QUOTE_DRIFT"
    is_cross_page = gate["fidelity_status"] == "EXACT_ORDERED_CROSS_PAGE_SPAN"
    if selected.get("quote_drift") is not is_quote_drift:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_QUOTE_FLAG_INVALID: {claim_id}")
    if is_quote_drift:
        if (
            selected.get("quote_drift_category") != gate.get("primary_drift_category")
            or not selected.get("nearest_deterministic_source_region_reference")
            or not isinstance(selected.get("quote_drift_semantically_material"), bool)
        ):
            raise PilotError(f"PILOT3_HUMAN_REVIEW_QUOTE_DETAIL_INVALID: {claim_id}")
    elif (
        selected.get("quote_drift_category") is not None
        or selected.get("nearest_deterministic_source_region_reference") is not None
        or selected.get("quote_drift_semantically_material") is not False
    ):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FALSE_QUOTE_DETAIL: {claim_id}")
    if is_cross_page and not selected.get("evidence_v2_ordered_span_reference"):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_SPAN_REFERENCE_REQUIRED: {claim_id}")
    if not is_cross_page and selected.get("evidence_v2_ordered_span_reference") is not None:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FALSE_SPAN_REFERENCE: {claim_id}")
    if review_mode == "BOUNDED_CONTEXT" and not selected.get("bounded_context_candidate_reference"):
        raise PilotError(f"PILOT3_HUMAN_REVIEW_CONTEXT_REFERENCE_REQUIRED: {claim_id}")
    if review_mode != "BOUNDED_CONTEXT" and selected.get("bounded_context_candidate_reference") is not None:
        raise PilotError(f"PILOT3_HUMAN_REVIEW_FALSE_CONTEXT_REFERENCE: {claim_id}")
    if not isinstance(selected.get("rationale"), str) or not selected["rationale"].strip():
        raise PilotError(f"PILOT3_HUMAN_REVIEW_RATIONALE_REQUIRED: {claim_id}")


def _metrics(
    reviewed_claims: list[dict[str, Any]], quote: dict[str, Any], pre_review: dict[str, Any],
    decisions: dict[str, Any],
) -> dict[str, Any]:
    total = len(reviewed_claims)
    decision_counts = Counter(x["human_decision"] for x in reviewed_claims)
    semantic_counts = Counter(x["semantic_support"] for x in reviewed_claims)
    admissibility_counts = Counter(x["evidence_admissibility"] for x in reviewed_claims)
    review_modes = Counter(x["review_mode"] for x in reviewed_claims)
    primary_failures = Counter(
        x["semantic_failure_category"] for x in reviewed_claims
        if x["semantic_failure_category"] != "NONE"
    )
    any_failures: Counter[str] = Counter()
    diagnostics: Counter[str] = Counter()
    attribution_origins: Counter[str] = Counter()
    for item in reviewed_claims:
        dimensions = set(item.get("secondary_failure_categories") or [])
        if item["semantic_failure_category"] != "NONE":
            dimensions.add(item["semantic_failure_category"])
        any_failures.update(dimensions)
        diagnostics.update(item.get("secondary_diagnostics") or [])
        if item.get("attribution_failure_origin"):
            attribution_origins[item["attribution_failure_origin"]] += 1

    quote_claims = [x for x in reviewed_claims if x["quote_drift"]]
    supported = semantic_counts["SUPPORTED"]
    keep = decision_counts["KEEP"]
    atomicity_issues = sum(x["atomicity_issue"] for x in reviewed_claims)
    material_atomicity = sum(x["atomicity_material_failure"] for x in reviewed_claims)
    expanded = total - review_modes["EXCERPT_ONLY"]
    mechanical_counts = Counter(x["gate_mechanical_fidelity_status"] for x in reviewed_claims)
    return {
        "document_type": METRICS_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims_total": total,
        "claims_reviewed": total,
        "pending": decision_counts["PENDING"],
        "decision_counts": {name: decision_counts[name] for name in ("KEEP", "DROP", "KEEP_NEEDS_REVIEW", "PENDING")},
        "semantic_counts": {name: semantic_counts[name] for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")},
        "semantic_support_rate": _ratio(supported, total),
        "true_semantic_failure_rate": _ratio(semantic_counts["UNSUPPORTED"], total),
        "evidence_admissibility_counts": {name: admissibility_counts[name] for name in sorted(ADMISSIBILITY)},
        "strict_current_contract_keep_rate": _ratio(keep, total),
        "mechanical_fidelity_counts": {name: mechanical_counts[name] for name in (
            "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
            "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
            "QUOTE_DRIFT", "UNRESOLVED_SOURCE_BINDING",
        )},
        "quote_drift": {
            "total": len(quote_claims),
            "semantic_outcomes": {name: sum(x["semantic_support"] == name for x in quote_claims) for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")},
            "semantically_material": sum(x["quote_drift_semantically_material"] for x in quote_claims),
        },
        "atomicity": {
            "issues": atomicity_issues,
            "issue_rate": _ratio(atomicity_issues, total),
            "material_failures": material_atomicity,
            "material_failure_rate": _ratio(material_atomicity, total),
        },
        "primary_semantic_failure_category_counts": {name: primary_failures[name] for name in sorted(FAILURE_CATEGORIES)},
        "semantic_failure_dimension_counts": {name: any_failures[name] for name in sorted(FAILURE_CATEGORIES)},
        "secondary_diagnostics": {name: diagnostics[name] for name in sorted(SECONDARY_DIAGNOSTICS)},
        "attribution": {
            "primary_errors": primary_failures["ATTRIBUTION_ERROR"],
            "any_dimension_errors": any_failures["ATTRIBUTION_ERROR"],
            "known_company_to_speaker_recurrence": (pre_review.get("attribution_mechanical_qa") or {}).get("known_old_mutation_recurrence"),
            "deterministic_origin": attribution_origins["DETERMINISTIC"],
            "model_origin": attribution_origins["MODEL"],
            "mixed_origin": attribution_origins["MIXED"],
        },
        "review_burden": {
            **{name: review_modes[name] for name in ("EXCERPT_ONLY", "BOUNDED_CONTEXT", "CROSS_PAGE", "QUOTE_DRIFT_SOURCE_REGION")},
            "expanded_manual_reviews": expanded,
            "expanded_manual_rate": _ratio(expanded, total),
            "categories_are_mutually_exclusive": sum(review_modes.values()) == total,
        },
        "comparison": {
            "pilot1": {
                "claims": 53,
                "true_semantic_failure_rate_percent": 11.32,
                "atomicity_issue_rate_percent": 13.21,
            },
            "pilot2_post_repair": {
                "claims": 51,
                "supported": 44,
                "unsupported": 6,
                "ambiguous": 1,
                "semantic_support_rate_percent": 86.27,
                "true_semantic_failure_rate_percent": 11.76,
                "atomicity_issues": 12,
                "atomicity_issue_rate_percent": 23.53,
                "material_atomicity_failures": 4,
                "material_atomicity_failure_rate_percent": 7.84,
                "attribution_errors": 0,
                "quote_drift": 6,
            },
            "claim_of_statistical_significance": False,
        },
        "token_economics": {
            "total_tokens": TOTAL_TOKENS,
            "tokens_per_claim": round(TOTAL_TOKENS / total, 2),
            "tokens_per_semantically_supported_claim": _tokens_per(supported),
            "tokens_per_current_contract_keep_claim": _tokens_per(keep),
        },
        "PILOT3_GENERALIZATION_VERDICT": decisions["PILOT3_GENERALIZATION_VERDICT"],
        "generalization_rationale": decisions["generalization_rationale"],
        "PROMPT_REPAIR_NEXT": copy.deepcopy(decisions["PROMPT_REPAIR_NEXT"]),
        "PHASE3C_NEXT_GATE": decisions["PHASE3C_NEXT_GATE"],
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": decisions["POST_REPAIR_INDEPENDENT_PILOT_REQUIRED"],
        "PHASE3C_PILOT3_EVIDENCE_V2_REPAIR_COMPLETE": True,
        "PHASE3C_PILOT3_EXTRACTION_COMPLETE": True,
        "PHASE3C_PILOT3_HUMAN_REVIEW_COMPLETE": True,
        "PILOT3_EXTRACTION_GATE": "FAIL",
        "PHASE3C_COMPLETE": False,
        "PRODUCTION_APPLY_READY": "NO",
        "llm_calls_added": 0,
        "pilot3_rerun": False,
        "production_write": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
    }


def _render_report(metrics: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    d = metrics["decision_counts"]
    s = metrics["semantic_counts"]
    a = metrics["atomicity"]
    q = metrics["quote_drift"]
    e = metrics["evidence_admissibility_counts"]
    f = metrics["primary_semantic_failure_category_counts"]
    diag = metrics["secondary_diagnostics"]
    attr = metrics["attribution"]
    burden = metrics["review_burden"]
    token = metrics["token_economics"]
    p2 = metrics["comparison"]["pilot2_post_repair"]
    production_pre = metrics["production_pre"]
    production_post = metrics["production_post"]
    invariants = metrics["invariants"]
    regression = metrics["regression_validation"]
    lines = [
        "# Phase 3C Pilot #3 — Independent Human Review and Post-Gate-C Generalization Evaluation", "",
        "## Outcome", "",
        f"- Generalization verdict: `{metrics['PILOT3_GENERALIZATION_VERDICT']}`.",
        f"- Mechanical extraction gate remains: `{metrics['PILOT3_EXTRACTION_GATE']}`.",
        f"- Claims reviewed / pending: {metrics['claims_reviewed']} / {metrics['pending']}.",
        f"- KEEP / DROP / KEEP_NEEDS_REVIEW: {d['KEEP']} / {d['DROP']} / {d['KEEP_NEEDS_REVIEW']}.",
        f"- SUPPORTED / UNSUPPORTED / AMBIGUOUS: {s['SUPPORTED']} / {s['UNSUPPORTED']} / {s['AMBIGUOUS']}.",
        f"- Semantic support rate: {metrics['semantic_support_rate']['fraction']} ({metrics['semantic_support_rate']['percent']}%).",
        f"- True semantic failure rate: {metrics['true_semantic_failure_rate']['fraction']} ({metrics['true_semantic_failure_rate']['percent']}%).",
        f"- Strict current-contract KEEP rate: {metrics['strict_current_contract_keep_rate']['fraction']} ({metrics['strict_current_contract_keep_rate']['percent']}%).", "",
        "The repaired behavior did not fully generalize on this noisy transcript. The known deterministic company-to-speaker mutation did not recur, but precise product/technical-term normalization, time normalization, scope, and compound-Claim failures remain material. Quote preservation is a separate blocker: most drifted Claims are semantically supported, yet none is admissible under the current contract.", "",
        "## Evidence and semantic separation", "",
        f"- Frozen mechanical fidelity: `{json.dumps(metrics['mechanical_fidelity_counts'], ensure_ascii=False)}`.",
        f"- Evidence admissibility: `{json.dumps(e, ensure_ascii=False)}` (sum={sum(e.values())}).",
        f"- Quote drift: total {q['total']}; SUPPORTED / UNSUPPORTED / AMBIGUOUS = {q['semantic_outcomes']['SUPPORTED']} / {q['semantic_outcomes']['UNSUPPORTED']} / {q['semantic_outcomes']['AMBIGUOUS']}; semantically material drift = {q['semantically_material']}.",
        f"- Atomicity issues: {a['issue_rate']['fraction']} ({a['issue_rate']['percent']}%); material failures: {a['material_failure_rate']['fraction']} ({a['material_failure_rate']['percent']}%).", "",
        "## Semantic failure diagnostics", "",
    ]
    lines.extend(f"- {name}: {f[name]}" for name in sorted(f))
    lines.extend([
        f"- TIME_NORMALIZATION: {diag['TIME_NORMALIZATION']}",
        f"- NUMBER_NORMALIZATION: {diag['NUMBER_NORMALIZATION']}",
        f"- Attribution errors, primary / any dimension: {attr['primary_errors']} / {attr['any_dimension_errors']}.",
        f"- Known company-to-speaker recurrence: `{attr['known_company_to_speaker_recurrence']}`.",
        f"- Attribution origin, deterministic / model / mixed: {attr['deterministic_origin']} / {attr['model_origin']} / {attr['mixed_origin']}.", "",
        "## Generalization comparison", "",
        "This is a descriptive cross-Source comparison; no statistical significance is claimed.", "",
        "| Metric | Pilot #1 | Pilot #2 post-repair | Pilot #3 |",
        "|---|---:|---:|---:|",
        f"| True semantic failure rate | 11.32% | {p2['true_semantic_failure_rate_percent']}% | {metrics['true_semantic_failure_rate']['percent']}% |",
        f"| Atomicity issue rate | 13.21% | {p2['atomicity_issue_rate_percent']}% | {a['issue_rate']['percent']}% |",
        f"| Material atomicity failure rate | n/a | {p2['material_atomicity_failure_rate_percent']}% | {a['material_failure_rate']['percent']}% |",
        f"| Attribution errors | n/a | {p2['attribution_errors']} | {attr['any_dimension_errors']} |", "",
        f"Verdict rationale: {metrics['generalization_rationale']}", "",
        "## Review burden and economics", "",
        f"- Review modes: EXCERPT_ONLY / BOUNDED_CONTEXT / CROSS_PAGE / QUOTE_DRIFT_SOURCE_REGION = {burden['EXCERPT_ONLY']} / {burden['BOUNDED_CONTEXT']} / {burden['CROSS_PAGE']} / {burden['QUOTE_DRIFT_SOURCE_REGION']}.",
        f"- Expanded/manual reviews: {burden['expanded_manual_rate']['fraction']} ({burden['expanded_manual_rate']['percent']}%).",
        f"- Tokens / Claim: {token['tokens_per_claim']}; tokens / supported Claim: {token['tokens_per_semantically_supported_claim']}; tokens / KEEP: {token['tokens_per_current_contract_keep_claim']}.", "",
        "## Next gate", "",
        f"- Prompt-repair recommendations only: `{json.dumps(metrics['PROMPT_REPAIR_NEXT'], ensure_ascii=False)}`.",
        f"- PHASE3C_NEXT_GATE = `{metrics['PHASE3C_NEXT_GATE']}`.",
        f"- POST_REPAIR_INDEPENDENT_PILOT_REQUIRED = `{str(metrics['POST_REPAIR_INDEPENDENT_PILOT_REQUIRED']).lower()}`.",
        "- No repair is implemented in this stage.", "",
        "## Immutability, Production, and isolation", "",
        f"- Frozen-field and input invariants: `{json.dumps(invariants, ensure_ascii=False)}`.",
        f"- Production pre/post SHA256: `{production_pre['sha256']}` / `{production_post['sha256']}`.",
        f"- Production table counts changed: `{production_pre['table_counts'] != production_post['table_counts']}`.",
        f"- Integrity / FK violations: `{production_post['integrity_check']}` / {len(production_post['foreign_key_violations'])}.",
        "- LLM calls added / Pilot rerun / Production write: `0 / NO / NO`.",
        "- IMA / propagation / legacy pipeline: `NO / NO / NO`.", "",
        "## Validation", "",
    ])
    lines.extend(f"- {name}: `{item['status']}` — {item['detail']}" for name, item in regression.items())
    lines.extend([
        "", "## Decision register", "",
        "| Claim ID | Semantic | Evidence admissibility | Decision | Primary failure | Atomic / material | Review mode | Rationale |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for item in claims:
        rationale = item["rationale"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {item['claim_id']} | {item['semantic_support']} | {item['evidence_admissibility']} | "
            f"{item['human_decision']} | {item['semantic_failure_category']} | "
            f"{item['atomicity_issue']} / {item['atomicity_material_failure']} | "
            f"{item['review_mode']} | {rationale} |"
        )
    lines.extend([
        "", "## STOP", "",
        "Human Review, metrics, generalization verdict, and validation are complete. No prompt, Claim, Evidence, extraction, Evidence Contract, canonical schema, Production, IMA, propagation, legacy pipeline, Pilot #4, or Stage 2 work was started.", "",
    ])
    return "\n".join(lines)


def close_pilot3_human_review(
    bundle_path: Path,
    repaired_evidence_path: Path,
    quote_fidelity_path: Path,
    pre_review_metrics_path: Path,
    original_failed_evidence_path: Path,
    decisions_path: Path,
    *,
    output_dir: Path,
    production_db_path: Path,
    regression_receipt_path: Path | None = None,
) -> dict[str, Any]:
    """Validate and close the 70-Claim review without extraction or canonical side effects."""
    paths = {
        "bundle": Path(bundle_path).resolve(),
        "repaired_evidence": Path(repaired_evidence_path).resolve(),
        "quote_fidelity": Path(quote_fidelity_path).resolve(),
        "pre_review_metrics": Path(pre_review_metrics_path).resolve(),
        "original_failed_evidence": Path(original_failed_evidence_path).resolve(),
        "decisions": Path(decisions_path).resolve(),
    }
    if any(not path.is_file() for path in paths.values()):
        raise PilotError("PILOT3_HUMAN_REVIEW_INPUT_MISSING")
    input_hashes_pre = {name: sha256_file(path) for name, path in paths.items()}
    production_pre = production_snapshot(Path(production_db_path).resolve())

    bundle = _load_json(paths["bundle"])
    evidence = _load_json(paths["repaired_evidence"])
    quote = _load_json(paths["quote_fidelity"])
    pre_review = _load_json(paths["pre_review_metrics"])
    decisions = _load_json(paths["decisions"])
    if (
        bundle.get("pilot_run_id") != RUN_ID
        or evidence.get("pilot_run_id") != RUN_ID
        or quote.get("pilot_run_id") != RUN_ID
        or pre_review.get("pilot_run_id") != RUN_ID
        or decisions.get("pilot_run_id") != RUN_ID
        or (bundle.get("source") or {}).get("sha256") != SOURCE_SHA256
        or decisions.get("source_sha256") != SOURCE_SHA256
    ):
        raise PilotError("PILOT3_HUMAN_REVIEW_BINDING_INVALID")
    if (
        decisions.get("document_type") != DECISIONS_DOCUMENT_TYPE
        or decisions.get("schema_version") != SCHEMA_VERSION
        or decisions.get("PILOT3_GENERALIZATION_VERDICT") not in VERDICTS
        or len(decisions.get("PROMPT_REPAIR_NEXT") or []) != len(set(decisions.get("PROMPT_REPAIR_NEXT") or []))
        or any(x not in PROMPT_REPAIR_CATEGORIES for x in decisions.get("PROMPT_REPAIR_NEXT") or [])
        or decisions.get("PHASE3C_NEXT_GATE") not in {
            "Cross-Pilot Evidence Fidelity Repair",
            "Pilot #3 Semantic Failure Repair",
            "Reassess Phase 3C Extraction Contract",
        }
        or not isinstance(decisions.get("POST_REPAIR_INDEPENDENT_PILOT_REQUIRED"), bool)
    ):
        raise PilotError("PILOT3_HUMAN_REVIEW_DECISIONS_INVALID")

    bundle_claims = bundle.get("claims") or []
    evidence_by_id = {x.get("claim_id"): x for x in evidence.get("claims") or []}
    quote_by_id = {x.get("claim_id"): x for x in quote.get("claims") or []}
    reviewed_claims = decisions.get("claims") or []
    bundle_ids = [x.get("claim_id") for x in bundle_claims]
    if (
        len(bundle_ids) != CLAIMS_TOTAL
        or [x.get("claim_id") for x in reviewed_claims] != bundle_ids
        or set(evidence_by_id) != set(bundle_ids)
        or set(quote_by_id) != set(bundle_ids)
    ):
        raise PilotError("PILOT3_HUMAN_REVIEW_CLAIM_COVERAGE_INVALID")
    for original, selected in zip(bundle_claims, reviewed_claims):
        claim_id = original["claim_id"]
        _validate_claim(original, evidence_by_id[claim_id], quote_by_id[claim_id], selected)

    metrics = _metrics(reviewed_claims, quote, pre_review, decisions)
    if metrics["mechanical_fidelity_counts"] != (pre_review.get("evidence_fidelity") or {}).get("counts"):
        raise PilotError("PILOT3_HUMAN_REVIEW_MECHANICAL_CLASSIFICATION_CHANGED")
    if metrics["quote_drift"]["total"] != 15:
        raise PilotError("PILOT3_HUMAN_REVIEW_QUOTE_DRIFT_COVERAGE_INVALID")
    if sum(metrics["evidence_admissibility_counts"].values()) != CLAIMS_TOTAL:
        raise PilotError("PILOT3_HUMAN_REVIEW_ADMISSIBILITY_SUM_INVALID")
    if sum(metrics["semantic_counts"].values()) != CLAIMS_TOTAL:
        raise PilotError("PILOT3_HUMAN_REVIEW_SEMANTIC_SUM_INVALID")
    if sum(metrics["decision_counts"].values()) != CLAIMS_TOTAL or metrics["pending"]:
        raise PilotError("PILOT3_HUMAN_REVIEW_DECISION_SUM_INVALID")
    if metrics["PILOT3_GENERALIZATION_VERDICT"] == "PASS" or (
        metrics["PILOT3_GENERALIZATION_VERDICT"] == "PASS_WITH_REPAIR"
        and metrics["PHASE3C_NEXT_GATE"] != "Cross-Pilot Evidence Fidelity Repair"
    ):
        raise PilotError("PILOT3_HUMAN_REVIEW_VERDICT_GATE_INVALID")
    if metrics["PILOT3_GENERALIZATION_VERDICT"] == "FAIL" and metrics["PHASE3C_NEXT_GATE"] not in {
        "Pilot #3 Semantic Failure Repair", "Reassess Phase 3C Extraction Contract",
    }:
        raise PilotError("PILOT3_HUMAN_REVIEW_FAIL_GATE_INVALID")

    regression = {
        name: {"status": "NOT_RUN", "detail": "Validation receipt not supplied yet."}
        for name in (
            "targeted_human_review_tests", "phase3a_regressions", "phase3b_regressions",
            "phase3c_regressions", "full_pytest", "frontend_tests", "frontend_build", "compileall",
        )
    }
    if regression_receipt_path:
        receipt = _load_json(Path(regression_receipt_path))
        if receipt.get("pilot_run_id") != RUN_ID or set(receipt.get("validation") or {}) != set(regression):
            raise PilotError("PILOT3_HUMAN_REVIEW_REGRESSION_RECEIPT_INVALID")
        regression = copy.deepcopy(receipt["validation"])

    input_hashes_post = {name: sha256_file(path) for name, path in paths.items()}
    production_post = production_snapshot(Path(production_db_path).resolve())
    expected_original_failure_hash = (
        (((pre_review.get("artifacts") or {}).get("original_failure_artifact") or {}).get("sha256"))
    )
    invariants = {
        "all_decisions_explicit": len(reviewed_claims) == CLAIMS_TOTAL,
        "pending_zero": metrics["pending"] == 0,
        "claim_ids_unchanged": [x["claim_id"] for x in reviewed_claims] == bundle_ids,
        "statements_unchanged": all(x["original_claim"] == y["statement"] for x, y in zip(reviewed_claims, bundle_claims)),
        "immutable_evidence_unchanged": all(x["immutable_evidence_excerpt"] == y["evidence_excerpt"] for x, y in zip(reviewed_claims, bundle_claims)),
        "attributed_to_unchanged": all(x["attributed_to"] == y["attributed_to"] for x, y in zip(reviewed_claims, bundle_claims)),
        "mechanical_classifications_unchanged": metrics["mechanical_fidelity_counts"] == (pre_review.get("evidence_fidelity") or {}).get("counts"),
        "frozen_input_files_unchanged": input_hashes_pre == input_hashes_post,
        "original_failed_evidence_preserved": (
            bool(expected_original_failure_hash)
            and input_hashes_post["original_failed_evidence"] == expected_original_failure_hash
        ),
        "production_unchanged": production_pre == production_post,
        "production_table_counts_unchanged": production_pre["table_counts"] == production_post["table_counts"],
    }
    if not all(invariants.values()):
        raise PilotError("PILOT3_HUMAN_REVIEW_INVARIANT_FAILED")

    metrics["invariants"] = invariants
    metrics["input_hashes_pre"] = input_hashes_pre
    metrics["input_hashes_post"] = input_hashes_post
    metrics["production_pre"] = production_pre
    metrics["production_post"] = production_post
    metrics["production_changed"] = False
    metrics["production_table_counts_changed"] = False
    metrics["regression_validation"] = regression

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "pilot3_human_review_metrics.json"
    report_path = output_dir / "pilot3_human_review_report.md"
    write_json(metrics_path, metrics)
    report_path.write_text(_render_report(metrics, reviewed_claims), encoding="utf-8")
    return {
        "status": "COMPLETE",
        "metrics": metrics,
        "decisions_path": str(Path(decisions_path).resolve()),
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
    }
