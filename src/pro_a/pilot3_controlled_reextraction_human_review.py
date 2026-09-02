from __future__ import annotations

import copy
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .corpus_pilot import PilotError, production_snapshot
from .storage import sha256_file, write_json


SCHEMA_VERSION = "1"
RUN_ID = "PILOT_20260901_4ED57ED2"
SOURCE_SHA256 = "1daf977493798d0334dedcd685d8a10f7c39dd25d768a44fa8a99ddf761627be"
CLAIMS_TOTAL = 56

ANNOTATIONS_DOCUMENT_TYPE = (
    "phase3c_pilot3_controlled_reextraction_blind_human_annotations"
)
DECISIONS_DOCUMENT_TYPE = (
    "phase3c_pilot3_controlled_reextraction_human_decisions"
)
FREEZE_RECEIPT_DOCUMENT_TYPE = (
    "phase3c_pilot3_controlled_reextraction_s3a_freeze_receipt"
)

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
SECONDARY_DIAGNOSTICS = {
    "TIME_NORMALIZATION",
    "NUMBER_NORMALIZATION",
    "SUBJECT_BINDING",
    "PRODUCT_CATEGORY_SUBSTITUTION",
    "QUESTION_PREMISE_ADOPTION",
}
REVIEW_MODES = {
    "EXCERPT_ONLY",
    "BOUNDED_CONTEXT",
    "CROSS_PAGE",
    "QUOTE_DRIFT_SOURCE_REGION",
}
ATTRIBUTION_FAILURE_ORIGINS = {"DETERMINISTIC", "MODEL", "MIXED"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"PILOT3_S3_INVALID_JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"PILOT3_S3_JSON_OBJECT_REQUIRED: {path}")
    return value


def _expected_decision(semantic_support: str, admissibility: str) -> str:
    if semantic_support == "UNSUPPORTED":
        return "DROP"
    if (
        semantic_support == "SUPPORTED"
        and admissibility == "CURRENT_CONTRACT_ADMISSIBLE"
    ):
        return "KEEP"
    return "KEEP_NEEDS_REVIEW"


def _validate_mode(
    *, fidelity_status: str, admissibility: str, review_mode: str,
) -> None:
    if fidelity_status == "QUOTE_DRIFT":
        valid = (
            admissibility == "EVIDENCE_QUOTE_DRIFT_BLOCKED"
            and review_mode == "QUOTE_DRIFT_SOURCE_REGION"
        )
    elif fidelity_status == "EXACT_ORDERED_CROSS_PAGE_SPAN":
        valid = (
            admissibility == "V2_ORDERED_SPAN_REQUIRED"
            and review_mode == "CROSS_PAGE"
        )
    elif admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        valid = review_mode == "EXCERPT_ONLY"
    elif admissibility in {"V2_CONTEXT_REQUIRED", "SOURCE_AMBIGUITY_BLOCKED"}:
        valid = review_mode == "BOUNDED_CONTEXT"
    else:
        valid = False
    if not valid:
        raise PilotError("PILOT3_S3_REVIEW_MODE_INVALID")


def _validate_annotation(
    annotation: dict[str, Any], *, fidelity_status: str,
) -> None:
    claim_id = annotation.get("claim_id")
    semantic = annotation.get("semantic_support")
    admissibility = annotation.get("evidence_admissibility")
    primary = annotation.get("semantic_failure_category")
    secondary = annotation.get("secondary_failure_categories") or []
    diagnostics = annotation.get("secondary_diagnostics") or []
    review_mode = annotation.get("review_mode")

    if semantic not in SEMANTIC_SUPPORT or admissibility not in ADMISSIBILITY:
        raise PilotError(f"PILOT3_S3_AXIS_INVALID: {claim_id}")
    if primary != "NONE" and primary not in FAILURE_CATEGORIES:
        raise PilotError(f"PILOT3_S3_PRIMARY_FAILURE_INVALID: {claim_id}")
    if len(secondary) != len(set(secondary)) or any(
        value not in FAILURE_CATEGORIES for value in secondary
    ):
        raise PilotError(f"PILOT3_S3_SECONDARY_FAILURE_INVALID: {claim_id}")
    if len(diagnostics) != len(set(diagnostics)) or any(
        value not in SECONDARY_DIAGNOSTICS for value in diagnostics
    ):
        raise PilotError(f"PILOT3_S3_SECONDARY_DIAGNOSTIC_INVALID: {claim_id}")
    if semantic == "UNSUPPORTED" and primary == "NONE":
        raise PilotError(f"PILOT3_S3_FAILURE_REQUIRED: {claim_id}")
    if semantic != "UNSUPPORTED" and primary != "NONE":
        raise PilotError(f"PILOT3_S3_FALSE_FAILURE: {claim_id}")
    if semantic == "AMBIGUOUS" and admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        raise PilotError(f"PILOT3_S3_AMBIGUITY_NOT_BLOCKED: {claim_id}")

    atomicity_issue = annotation.get("atomicity_issue")
    material_atomicity = annotation.get("atomicity_material_failure")
    if not isinstance(atomicity_issue, bool) or not isinstance(
        material_atomicity, bool
    ):
        raise PilotError(f"PILOT3_S3_ATOMICITY_INVALID: {claim_id}")
    if material_atomicity and (not atomicity_issue or semantic != "UNSUPPORTED"):
        raise PilotError(f"PILOT3_S3_MATERIAL_ATOMICITY_INVALID: {claim_id}")

    dimensions = set(secondary)
    if primary != "NONE":
        dimensions.add(primary)
    origin = annotation.get("attribution_failure_origin")
    if "ATTRIBUTION_ERROR" in dimensions:
        if origin not in ATTRIBUTION_FAILURE_ORIGINS:
            raise PilotError(f"PILOT3_S3_ATTRIBUTION_ORIGIN_REQUIRED: {claim_id}")
    elif origin is not None:
        raise PilotError(f"PILOT3_S3_FALSE_ATTRIBUTION_ORIGIN: {claim_id}")

    if not isinstance(annotation.get("quote_drift_semantically_material"), bool):
        raise PilotError(f"PILOT3_S3_QUOTE_MATERIALITY_INVALID: {claim_id}")
    if (
        fidelity_status != "QUOTE_DRIFT"
        and annotation["quote_drift_semantically_material"]
    ):
        raise PilotError(f"PILOT3_S3_FALSE_QUOTE_MATERIALITY: {claim_id}")
    if not isinstance(annotation.get("rationale"), str) or not annotation[
        "rationale"
    ].strip():
        raise PilotError(f"PILOT3_S3_RATIONALE_REQUIRED: {claim_id}")
    _validate_mode(
        fidelity_status=fidelity_status,
        admissibility=admissibility,
        review_mode=review_mode,
    )


def build_blind_human_decisions(
    bundle_path: Path,
    evidence_v2_path: Path,
    quote_fidelity_path: Path,
    annotations_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Build S3-A decisions without accepting any historical comparison input."""
    bundle = _load_json(Path(bundle_path))
    evidence = _load_json(Path(evidence_v2_path))
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
        or annotations.get("review_phase") != "S3-A_BLIND_REVIEW"
        or annotations.get("historical_comparison_inputs_accessed") is not False
    ):
        raise PilotError("PILOT3_S3_BLIND_BINDING_INVALID")

    bundle_claims = bundle.get("claims") or []
    evidence_by_id = {
        item.get("claim_id"): item for item in evidence.get("claims") or []
    }
    quote_by_id = {
        item.get("claim_id"): item for item in quote.get("claims") or []
    }
    annotation_claims = annotations.get("claims") or []
    bundle_ids = [item.get("claim_id") for item in bundle_claims]
    if (
        len(bundle_ids) != CLAIMS_TOTAL
        or len(bundle_ids) != len(set(bundle_ids))
        or [item.get("claim_id") for item in annotation_claims] != bundle_ids
        or set(evidence_by_id) != set(bundle_ids)
        or set(quote_by_id) != set(bundle_ids)
    ):
        raise PilotError("PILOT3_S3_BLIND_COVERAGE_INVALID")

    reviewed: list[dict[str, Any]] = []
    for original, annotation in zip(bundle_claims, annotation_claims):
        claim_id = original["claim_id"]
        evidence_item = evidence_by_id[claim_id]
        gate = quote_by_id[claim_id]
        fidelity_status = gate.get("fidelity_status")
        if evidence_item.get("original_evidence_excerpt") != original.get(
            "evidence_excerpt"
        ):
            raise PilotError(f"PILOT3_S3_EVIDENCE_CHANGED: {claim_id}")
        _validate_annotation(annotation, fidelity_status=fidelity_status)

        review_mode = annotation["review_mode"]
        semantic = annotation["semantic_support"]
        admissibility = annotation["evidence_admissibility"]
        is_quote_drift = fidelity_status == "QUOTE_DRIFT"
        is_cross_page = fidelity_status == "EXACT_ORDERED_CROSS_PAGE_SPAN"
        reviewed.append(
            {
                "claim_id": claim_id,
                "original_claim": original.get("statement"),
                "attributed_to": original.get("attributed_to"),
                "immutable_evidence_excerpt": original.get("evidence_excerpt"),
                "gate_mechanical_fidelity_status": fidelity_status,
                "review_mode": review_mode,
                "semantic_support": semantic,
                "semantic_failure_category": annotation[
                    "semantic_failure_category"
                ],
                "secondary_failure_categories": copy.deepcopy(
                    annotation.get("secondary_failure_categories") or []
                ),
                "secondary_diagnostics": copy.deepcopy(
                    annotation.get("secondary_diagnostics") or []
                ),
                "attribution_failure_origin": annotation.get(
                    "attribution_failure_origin"
                ),
                "atomicity_issue": annotation["atomicity_issue"],
                "atomicity_material_failure": annotation[
                    "atomicity_material_failure"
                ],
                "evidence_admissibility": admissibility,
                "human_decision": _expected_decision(semantic, admissibility),
                "rationale": annotation["rationale"],
                "quote_drift": is_quote_drift,
                "quote_drift_category": (
                    gate.get("primary_drift_category") if is_quote_drift else None
                ),
                "quote_drift_semantically_material": annotation[
                    "quote_drift_semantically_material"
                ],
                "nearest_deterministic_source_region_reference": (
                    copy.deepcopy(
                        gate.get("nearest_deterministic_local_source_region")
                    )
                    if is_quote_drift
                    else None
                ),
                "evidence_v2_ordered_span_reference": (
                    copy.deepcopy(gate.get("resolved_locator"))
                    if is_cross_page
                    else None
                ),
                "bounded_context_candidate_reference": (
                    {
                        "context_locators": copy.deepcopy(
                            evidence_item.get("context_locators") or []
                        ),
                        "candidates": copy.deepcopy(
                            evidence_item.get("bounded_context_candidates") or []
                        ),
                    }
                    if review_mode == "BOUNDED_CONTEXT"
                    else None
                ),
            }
        )

    decisions = {
        "document_type": DECISIONS_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "FROZEN",
        "review_phase": "S3-A_BLIND_REVIEW",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims_total": CLAIMS_TOTAL,
        "claims_reviewed": len(reviewed),
        "pending": 0,
        "blind_review_protocol": {
            "permitted_inputs": copy.deepcopy(
                annotations.get("permitted_inputs") or []
            ),
            "prohibited_historical_inputs_accessed_before_freeze": False,
            "comparison_performed": False,
        },
        "claims": reviewed,
    }
    write_json(Path(output_path), decisions)
    return decisions


def freeze_blind_human_decisions(
    decisions_path: Path,
    receipt_path: Path,
    *,
    frozen_inputs: dict[str, Path],
) -> dict[str, Any]:
    """Hash the completed S3-A register before S3-B is allowed to start."""
    decisions_path = Path(decisions_path).resolve()
    decisions = _load_json(decisions_path)
    if (
        decisions.get("document_type") != DECISIONS_DOCUMENT_TYPE
        or decisions.get("status") != "FROZEN"
        or decisions.get("review_phase") != "S3-A_BLIND_REVIEW"
        or decisions.get("pilot_run_id") != RUN_ID
        or decisions.get("claims_reviewed") != CLAIMS_TOTAL
        or decisions.get("pending") != 0
        or len(decisions.get("claims") or []) != CLAIMS_TOTAL
        or (decisions.get("blind_review_protocol") or {}).get(
            "comparison_performed"
        )
        is not False
    ):
        raise PilotError("PILOT3_S3_FREEZE_PRECONDITION_INVALID")

    resolved_inputs = {
        name: Path(path).resolve() for name, path in frozen_inputs.items()
    }
    if any(not path.is_file() for path in resolved_inputs.values()):
        raise PilotError("PILOT3_S3_FROZEN_INPUT_MISSING")
    receipt = {
        "document_type": FREEZE_RECEIPT_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "FROZEN",
        "pilot_run_id": RUN_ID,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "claims_reviewed": CLAIMS_TOTAL,
        "pending": 0,
        "BLIND_REVIEW_COMPLETED_BEFORE_COMPARISON": True,
        "historical_comparison_inputs_accessed_before_freeze": False,
        "decisions": {
            "path": str(decisions_path),
            "sha256": sha256_file(decisions_path),
        },
        "frozen_inputs": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in resolved_inputs.items()
        },
    }
    write_json(Path(receipt_path), receipt)
    return receipt


EVALUATION_ANNOTATIONS_DOCUMENT_TYPE = (
    "phase3c_pilot3_semantic_repair_evaluation_annotations"
)
EVALUATION_DOCUMENT_TYPE = "phase3c_pilot3_semantic_repair_evaluation"
METRICS_DOCUMENT_TYPE = (
    "phase3c_pilot3_controlled_reextraction_human_review_metrics"
)
REPAIR_OUTCOMES = {
    "RESOLVED_BY_OMISSION",
    "RESOLVED_BY_CONSERVATIVE_REWRITE",
    "RESOLVED_BY_ATOMIC_SPLIT",
    "PERSISTED_EQUIVALENT_FAILURE",
    "MORPHED_TO_DIFFERENT_FAILURE",
    "NO_COMPARABLE_NEW_CLAIM",
}
RETENTION_CATEGORIES = {
    "CLEARLY_RETAINED",
    "RETAINED_IN_SPLIT_OR_REPHRASED_FORM",
    "NOT_OBVIOUSLY_RETAINED",
    "NOT_COMPARABLE",
}
SEMANTIC_REPAIR_VERDICTS = {"PASS", "PASS_WITH_RESIDUALS", "FAIL"}
NEXT_GATES = {
    "Cross-Pilot Evidence Fidelity Repair",
    "Pilot #3 Semantic Failure Repair Iteration 2",
    "Define Noisy-Source Boundary for Phase 3C",
}
NEW_FAILURE_ORIGINS = {"REPAIR_INDUCED", "PREVIOUSLY_LATENT", "UNRELATED"}
TOTAL_TOKENS = 50172


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100 * numerator / denominator, 2) if denominator else 0.0,
    }


def _decision_metrics(
    decisions: dict[str, Any], old_decisions: dict[str, Any], quote: dict[str, Any],
) -> dict[str, Any]:
    claims = decisions.get("claims") or []
    old_claims = old_decisions.get("claims") or []
    decision_counts = Counter(item["human_decision"] for item in claims)
    semantic_counts = Counter(item["semantic_support"] for item in claims)
    admissibility_counts = Counter(item["evidence_admissibility"] for item in claims)
    review_modes = Counter(item["review_mode"] for item in claims)
    primary_failures = Counter(
        item["semantic_failure_category"]
        for item in claims
        if item["semantic_failure_category"] != "NONE"
    )
    secondary_diagnostics: Counter[str] = Counter()
    for item in claims:
        secondary_diagnostics.update(item.get("secondary_diagnostics") or [])

    quote_claims = [item for item in claims if item["quote_drift"]]
    supported = semantic_counts["SUPPORTED"]
    keep = decision_counts["KEEP"]
    atomicity_issues = sum(item["atomicity_issue"] for item in claims)
    material_atomicity = sum(item["atomicity_material_failure"] for item in claims)
    old_semantic = Counter(item["semantic_support"] for item in old_claims)
    old_primary = Counter(
        item["semantic_failure_category"]
        for item in old_claims
        if item["semantic_failure_category"] != "NONE"
    )
    old_diagnostics: Counter[str] = Counter()
    for item in old_claims:
        old_diagnostics.update(item.get("secondary_diagnostics") or [])

    quote_counts = Counter(
        item.get("fidelity_status") for item in quote.get("claims") or []
    )
    return {
        "claims_total": len(claims),
        "claims_reviewed": len(claims),
        "pending": 0,
        "decision_counts": {
            name: decision_counts[name]
            for name in ("KEEP", "DROP", "KEEP_NEEDS_REVIEW", "PENDING")
        },
        "semantic_counts": {
            name: semantic_counts[name]
            for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
        },
        "semantic_support_rate": _ratio(supported, len(claims)),
        "true_semantic_failure_rate": _ratio(
            semantic_counts["UNSUPPORTED"], len(claims)
        ),
        "evidence_admissibility_counts": {
            name: admissibility_counts[name] for name in sorted(ADMISSIBILITY)
        },
        "strict_current_contract_keep_rate": _ratio(keep, len(claims)),
        "mechanical_fidelity_counts": {
            name: quote_counts[name]
            for name in (
                "EXACT_SOURCE_MATCH",
                "LAYOUT_NORMALIZED_EXACT_MATCH",
                "EXACT_ORDERED_CROSS_PAGE_SPAN",
                "PROVENANCE_MISMATCH_RECOVERED",
                "QUOTE_DRIFT",
                "UNRESOLVED_SOURCE_BINDING",
            )
        },
        "quote_drift": {
            "total": len(quote_claims),
            "semantic_outcomes": {
                name: sum(item["semantic_support"] == name for item in quote_claims)
                for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
            },
            "semantically_material": sum(
                item["quote_drift_semantically_material"] for item in quote_claims
            ),
        },
        "atomicity": {
            "issues": atomicity_issues,
            "issue_rate": _ratio(atomicity_issues, len(claims)),
            "material_failures": material_atomicity,
            "material_failure_rate": _ratio(material_atomicity, len(claims)),
        },
        "primary_semantic_failure_category_counts": {
            name: primary_failures[name] for name in sorted(FAILURE_CATEGORIES)
        },
        "secondary_diagnostics": {
            name: secondary_diagnostics[name]
            for name in sorted(SECONDARY_DIAGNOSTICS)
        },
        "attribution": {
            "errors": primary_failures["ATTRIBUTION_ERROR"],
            "question_premise_adoptions": secondary_diagnostics[
                "QUESTION_PREMISE_ADOPTION"
            ],
        },
        "review_burden": {
            **{
                name: review_modes[name]
                for name in (
                    "EXCERPT_ONLY",
                    "BOUNDED_CONTEXT",
                    "CROSS_PAGE",
                    "QUOTE_DRIFT_SOURCE_REGION",
                )
            },
            "expanded_manual_reviews": len(claims) - review_modes["EXCERPT_ONLY"],
            "expanded_manual_rate": _ratio(
                len(claims) - review_modes["EXCERPT_ONLY"], len(claims)
            ),
            "categories_are_mutually_exclusive": sum(review_modes.values())
            == len(claims),
        },
        "old_baseline": {
            "claims": len(old_claims),
            "semantic_counts": {
                name: old_semantic[name]
                for name in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
            },
            "true_semantic_failure_rate": _ratio(
                old_semantic["UNSUPPORTED"], len(old_claims)
            ),
            "atomicity_issue_rate": _ratio(
                sum(item["atomicity_issue"] for item in old_claims), len(old_claims)
            ),
            "material_atomicity_failure_rate": _ratio(
                sum(item["atomicity_material_failure"] for item in old_claims),
                len(old_claims),
            ),
            "primary_semantic_failure_category_counts": {
                name: old_primary[name] for name in sorted(FAILURE_CATEGORIES)
            },
            "secondary_diagnostics": {
                name: old_diagnostics[name]
                for name in sorted(SECONDARY_DIAGNOSTICS)
            },
        },
        "pilot2_post_repair_semantic_failure_rate_percent": 11.76,
        "no_statistical_significance_claim": True,
        "token_economics": {
            "total_tokens": TOTAL_TOKENS,
            "tokens_per_claim": round(TOTAL_TOKENS / len(claims), 2),
            "tokens_per_supported_claim": round(TOTAL_TOKENS / supported, 2),
            "tokens_per_keep_claim": round(TOTAL_TOKENS / keep, 2),
            "logical_extractions": 1,
            "actual_api_attempts": 1,
            "original_total_tokens": 346179,
            "original_tokens_per_claim": 4945.41,
            "original_truncation_recovery_attempts": 10,
        },
    }


def _validate_evaluation_annotations(
    annotations: dict[str, Any],
    old_decisions: dict[str, Any],
    new_decisions: dict[str, Any],
    comparison: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if (
        annotations.get("document_type") != EVALUATION_ANNOTATIONS_DOCUMENT_TYPE
        or annotations.get("schema_version") != SCHEMA_VERSION
        or annotations.get("pilot_run_id") != RUN_ID
        or annotations.get("review_phase") != "S3-B_POST_DECISION_COMPARISON"
    ):
        raise PilotError("PILOT3_S3_EVALUATION_BINDING_INVALID")

    old_unsupported = [
        item
        for item in old_decisions.get("claims") or []
        if item.get("semantic_support") == "UNSUPPORTED"
    ]
    old_supported = [
        item
        for item in old_decisions.get("claims") or []
        if item.get("semantic_support") == "SUPPORTED"
    ]
    new_by_id = {
        item["claim_id"]: item for item in new_decisions.get("claims") or []
    }
    mapping_by_id = {
        item["old_claim_id"]: item
        for item in comparison.get("old_failure_to_new_candidate_mapping") or []
    }

    outcomes = annotations.get("old_failure_repair_outcomes") or []
    if [item.get("old_claim_id") for item in outcomes] != [
        item.get("claim_id") for item in old_unsupported
    ]:
        raise PilotError("PILOT3_S3_OLD_FAILURE_RECONCILIATION_INVALID")
    rendered_outcomes: list[dict[str, Any]] = []
    linked_new_failures: set[str] = set()
    for old, item in zip(old_unsupported, outcomes):
        outcome = item.get("repair_outcome")
        related = item.get("related_new_claim_ids") or []
        if (
            outcome not in REPAIR_OUTCOMES
            or any(claim_id not in new_by_id for claim_id in related)
            or not isinstance(item.get("rationale"), str)
            or not item["rationale"].strip()
        ):
            raise PilotError("PILOT3_S3_REPAIR_OUTCOME_INVALID")
        for claim_id in related:
            if new_by_id[claim_id]["semantic_support"] == "UNSUPPORTED":
                linked_new_failures.add(claim_id)
        candidate_ids = (mapping_by_id.get(old["claim_id"]) or {}).get(
            "candidate_new_claim_ids"
        ) or []
        rendered_outcomes.append(
            {
                "old_claim_id": old["claim_id"],
                "old_failure_category": old["semantic_failure_category"],
                "candidate_new_claim_ids": candidate_ids,
                "new_human_outcomes": [
                    {
                        "claim_id": claim_id,
                        "semantic_support": new_by_id[claim_id]["semantic_support"],
                        "human_decision": new_by_id[claim_id]["human_decision"],
                        "failure_category": new_by_id[claim_id][
                            "semantic_failure_category"
                        ],
                    }
                    for claim_id in candidate_ids
                ],
                "related_new_claim_ids": related,
                "repair_outcome": outcome,
                "rationale": item["rationale"],
            }
        )

    expected_new_failures = {
        claim_id
        for claim_id, item in new_by_id.items()
        if item["semantic_support"] == "UNSUPPORTED"
        and claim_id not in linked_new_failures
    }
    new_failure_annotations = annotations.get("new_post_repair_failures") or []
    if {item.get("claim_id") for item in new_failure_annotations} != expected_new_failures:
        raise PilotError("PILOT3_S3_NEW_FAILURE_RECONCILIATION_INVALID")
    rendered_new_failures: list[dict[str, Any]] = []
    for item in new_failure_annotations:
        claim_id = item["claim_id"]
        origin = item.get("origin")
        if origin not in NEW_FAILURE_ORIGINS or not str(item.get("rationale") or "").strip():
            raise PilotError("PILOT3_S3_NEW_FAILURE_INVALID")
        rendered_new_failures.append(
            {
                "claim_id": claim_id,
                "failure_category": new_by_id[claim_id][
                    "semantic_failure_category"
                ],
                "origin": origin,
                "rationale": item["rationale"],
            }
        )

    retention = annotations.get("supported_information_retention") or []
    if [item.get("old_claim_id") for item in retention] != [
        item.get("claim_id") for item in old_supported
    ]:
        raise PilotError("PILOT3_S3_RETENTION_RECONCILIATION_INVALID")
    rendered_retention: list[dict[str, Any]] = []
    for item in retention:
        category = item.get("retention_category")
        candidates = item.get("candidate_new_claim_ids") or []
        if (
            category not in RETENTION_CATEGORIES
            or any(claim_id not in new_by_id for claim_id in candidates)
            or not str(item.get("rationale") or "").strip()
        ):
            raise PilotError("PILOT3_S3_RETENTION_ITEM_INVALID")
        if category in {
            "CLEARLY_RETAINED",
            "RETAINED_IN_SPLIT_OR_REPHRASED_FORM",
        } and not any(
            new_by_id[claim_id]["semantic_support"] == "SUPPORTED"
            for claim_id in candidates
        ):
            raise PilotError("PILOT3_S3_RETENTION_SUPPORT_REQUIRED")
        rendered_retention.append(copy.deepcopy(item))
    return rendered_outcomes, rendered_new_failures, rendered_retention


def _render_evaluation_report(evaluation: dict[str, Any]) -> str:
    comparison = evaluation["semantic_comparison"]
    atomicity = evaluation["atomicity_comparison"]
    lines = [
        "# Phase 3C Pilot #3 Semantic Repair Evaluation",
        "",
        f"- S3-A decisions SHA-256: `{evaluation['S3_A_DECISIONS_SHA256']}`",
        "- Blind review completed before comparison: `true`",
        f"- Semantic repair verdict: `{evaluation['PILOT3_SEMANTIC_REPAIR_VERDICT']}`",
        f"- Next gate: `{evaluation['PHASE3C_NEXT_GATE']}`",
        "",
        "## Old vs new semantic quality",
        "",
        f"- Claims: `{comparison['old_claims']} -> {comparison['new_claims']}`",
        f"- SUPPORTED: `{comparison['old_supported']} -> {comparison['new_supported']}`",
        f"- UNSUPPORTED: `{comparison['old_unsupported']} -> {comparison['new_unsupported']}`",
        f"- AMBIGUOUS: `{comparison['old_ambiguous']} -> {comparison['new_ambiguous']}`",
        f"- True semantic failure: `{comparison['old_failure_rate_percent']}% -> {comparison['new_failure_rate_percent']}%`",
        "- Pilot #2 post-repair semantic failure: `11.76%`",
        "- No statistical-significance claim is made.",
        "",
        "## Atomicity",
        "",
        f"- Issue rate: `{atomicity['old_issue_rate_percent']}% -> {atomicity['new_issue_rate_percent']}%`",
        f"- Material failure rate: `{atomicity['old_material_failure_rate_percent']}% -> {atomicity['new_material_failure_rate_percent']}%`",
        "",
        "## Failure categories",
        "",
        "| Category | Old | New | Delta |",
        "|---|---:|---:|---:|",
    ]
    for name, item in evaluation["failure_category_comparison"].items():
        lines.append(f"| {name} | {item['old']} | {item['new']} | {item['delta']} |")
    lines.extend([
        "",
        "## Old 14 failure outcomes",
        "",
        "| Old Claim | Category | Outcome | Related new Claims | Rationale |",
        "|---|---|---|---|---|",
    ])
    for item in evaluation["old_failure_repair_outcomes"]:
        related = ", ".join(item["related_new_claim_ids"]) or "-"
        rationale = item["rationale"].replace("|", "\\|")
        lines.append(
            f"| {item['old_claim_id']} | {item['old_failure_category']} | "
            f"{item['repair_outcome']} | {related} | {rationale} |"
        )
    lines.extend([
        "",
        "## New post-repair failures",
        "",
        "| New Claim | Category | Origin | Rationale |",
        "|---|---|---|---|",
    ])
    for item in evaluation["NEW_POST_REPAIR_FAILURES"]:
        rationale = item["rationale"].replace("|", "\\|")
        lines.append(
            f"| {item['claim_id']} | {item['failure_category']} | "
            f"{item['origin']} | {rationale} |"
        )
    retention = evaluation["supported_information_retention"]
    lines.extend([
        "",
        "## Supported-information retention diagnostic",
        "",
        f"- Old SUPPORTED Claims: `{retention['old_supported_claims']}`",
        f"- Clearly retained: `{retention['counts']['CLEARLY_RETAINED']}`",
        f"- Split/rephrased retained: `{retention['counts']['RETAINED_IN_SPLIT_OR_REPHRASED_FORM']}`",
        f"- Not obviously retained: `{retention['counts']['NOT_OBVIOUSLY_RETAINED']}`",
        f"- Not comparable: `{retention['counts']['NOT_COMPARABLE']}`",
        "- This is descriptive and is not a formal recall metric.",
        "",
        "## Diagnosis",
        "",
        f"- Extraction-contract failures: `{evaluation['failure_origin_diagnosis']['extraction_contract_failures']}`",
        f"- Upstream Source-quality limits: `{evaluation['failure_origin_diagnosis']['upstream_source_quality_limits']}`",
        f"- Noisy-source preprocessing backlog: `{str(evaluation['NOISY_SOURCE_PREPROCESSING_BACKLOG']).lower()}`",
        "",
        "## STOP",
        "",
        "No Prompt iteration, LLM rerun, Evidence repair, audio preprocessing, Pilot #4, Production apply, IMA, propagation, or legacy ingestion was executed.",
        "",
    ])
    return "\n".join(lines)


def _render_human_review_report(metrics: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 3C Pilot #3 Controlled Re-extraction Human Review Report",
        "",
        "PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_HUMAN_REVIEW_COMPLETE = `true`",
        f"S3_A_DECISIONS_SHA256 = `{metrics['S3_A_DECISIONS_SHA256']}`",
        "BLIND_REVIEW_COMPLETED_BEFORE_COMPARISON = `true`",
        "PILOT3_REEXTRACTION_MECHANICAL_GATE = `FAIL`",
        "PILOT3_GENERALIZATION_VERDICT = `FAIL`",
        f"PILOT3_SEMANTIC_REPAIR_VERDICT = `{metrics['PILOT3_SEMANTIC_REPAIR_VERDICT']}`",
        "PHASE3C_COMPLETE = `false`",
        "PRODUCTION_APPLY_READY = `NO`",
        f"PHASE3C_NEXT_GATE = `{metrics['PHASE3C_NEXT_GATE']}`",
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED = `true`",
        f"NOISY_SOURCE_PREPROCESSING_BACKLOG = `{str(metrics['NOISY_SOURCE_PREPROCESSING_BACKLOG']).lower()}`",
        "",
        "## Blind-review procedure",
        "",
        "- S3-A accepted only the controlled Run, immutable Source, frozen Evidence v2, review surface, mechanics, and review contract.",
        "- Historical decisions, failure labels, candidate mapping, and old-vs-new interpretation were not inputs to the S3-A builder.",
        "- The 56 decisions were hashed before S3-B loaded historical comparison inputs.",
        "",
        "## Human results",
        "",
        f"- Decisions KEEP / DROP / KEEP_NEEDS_REVIEW: `{metrics['decision_counts']['KEEP']} / {metrics['decision_counts']['DROP']} / {metrics['decision_counts']['KEEP_NEEDS_REVIEW']}`",
        f"- Semantic SUPPORTED / UNSUPPORTED / AMBIGUOUS: `{metrics['semantic_counts']['SUPPORTED']} / {metrics['semantic_counts']['UNSUPPORTED']} / {metrics['semantic_counts']['AMBIGUOUS']}`",
        f"- True semantic failure rate: `{metrics['true_semantic_failure_rate']['fraction']} = {metrics['true_semantic_failure_rate']['percent']}%`",
        f"- Atomicity issues / material failures: `{metrics['atomicity']['issues']} / {metrics['atomicity']['material_failures']}`",
        f"- Atomicity issue / material failure rate: `{metrics['atomicity']['issue_rate']['percent']}% / {metrics['atomicity']['material_failure_rate']['percent']}%`",
        f"- Quote-drift semantic outcomes S/U/A: `{metrics['quote_drift']['semantic_outcomes']['SUPPORTED']} / {metrics['quote_drift']['semantic_outcomes']['UNSUPPORTED']} / {metrics['quote_drift']['semantic_outcomes']['AMBIGUOUS']}`",
        f"- Semantically material quote drift: `{metrics['quote_drift']['semantically_material']}`",
        "",
        "## Evidence admissibility",
        "",
    ]
    for name, count in metrics["evidence_admissibility_counts"].items():
        lines.append(f"- {name}: `{count}`")
    lines.extend([
        "",
        "## Review burden",
        "",
    ])
    for name in (
        "EXCERPT_ONLY",
        "BOUNDED_CONTEXT",
        "CROSS_PAGE",
        "QUOTE_DRIFT_SOURCE_REGION",
    ):
        lines.append(f"- {name}: `{metrics['review_burden'][name]}`")
    lines.extend([
        f"- Expanded/manual reviews: `{metrics['review_burden']['expanded_manual_reviews']}`",
        "",
        "## Token economics",
        "",
        f"- Tokens / supported Claim: `{metrics['token_economics']['tokens_per_supported_claim']}`",
        f"- Tokens / KEEP Claim: `{metrics['token_economics']['tokens_per_keep_claim']}`",
        "",
        "## Isolation and validation",
        "",
        f"- Prompt / Evidence v2 / extraction / original artifacts unchanged: `{str(metrics['invariants']['all_frozen_inputs_unchanged']).lower()}`",
        f"- Production changed / table counts changed: `NO / NO`",
        f"- Production integrity / FK violations: `{metrics['production_post']['integrity_check']} / {len(metrics['production_post']['foreign_key_violations'])}`",
        "- LLM / extraction rerun / Evidence write / Production write / IMA / propagation / legacy ingestion: `NO / NO / NO / NO / NO / NO / NO`",
        "",
        "## Regression validation",
        "",
    ])
    for name, result in metrics["regression_validation"].items():
        lines.append(f"- {name}: `{result['status']}` - {result['detail']}")
    lines.extend([
        "",
        "## Frozen decision register",
        "",
        "| Claim ID | Semantic | Admissibility | Decision | Primary failure | Atomic/material | Review mode |",
        "|---|---|---|---|---|---|---|",
    ])
    for item in claims:
        lines.append(
            f"| {item['claim_id']} | {item['semantic_support']} | "
            f"{item['evidence_admissibility']} | {item['human_decision']} | "
            f"{item['semantic_failure_category']} | {item['atomicity_issue']} / "
            f"{item['atomicity_material_failure']} | {item['review_mode']} |"
        )
    lines.extend([
        "",
        "## STOP",
        "",
        "Stage S3 is complete. The selected next gate was not implemented.",
        "",
    ])
    return "\n".join(lines)


def close_controlled_reextraction_human_review(
    *,
    decisions_path: Path,
    freeze_receipt_path: Path,
    new_bundle_path: Path,
    evidence_v2_path: Path,
    quote_fidelity_path: Path,
    pre_review_metrics_path: Path,
    old_bundle_path: Path,
    old_decisions_path: Path,
    structural_comparison_path: Path,
    evaluation_annotations_path: Path,
    prompt_path: Path,
    source_path: Path,
    production_db_path: Path,
    run_output_dir: Path,
    evaluation_output_dir: Path,
    regression_receipt_path: Path | None = None,
) -> dict[str, Any]:
    input_paths = {
        "decisions": Path(decisions_path).resolve(),
        "freeze_receipt": Path(freeze_receipt_path).resolve(),
        "new_bundle": Path(new_bundle_path).resolve(),
        "evidence_v2": Path(evidence_v2_path).resolve(),
        "quote_fidelity": Path(quote_fidelity_path).resolve(),
        "pre_review_metrics": Path(pre_review_metrics_path).resolve(),
        "old_bundle": Path(old_bundle_path).resolve(),
        "old_decisions": Path(old_decisions_path).resolve(),
        "structural_comparison": Path(structural_comparison_path).resolve(),
        "evaluation_annotations": Path(evaluation_annotations_path).resolve(),
        "prompt": Path(prompt_path).resolve(),
        "source": Path(source_path).resolve(),
    }
    if any(not path.is_file() for path in input_paths.values()):
        raise PilotError("PILOT3_S3_INPUT_MISSING")
    input_hashes_pre = {
        name: sha256_file(path) for name, path in input_paths.items()
    }
    production_pre = production_snapshot(Path(production_db_path).resolve())

    decisions = _load_json(input_paths["decisions"])
    freeze_receipt = _load_json(input_paths["freeze_receipt"])
    new_bundle = _load_json(input_paths["new_bundle"])
    evidence_v2 = _load_json(input_paths["evidence_v2"])
    quote = _load_json(input_paths["quote_fidelity"])
    pre_review = _load_json(input_paths["pre_review_metrics"])
    old_bundle = _load_json(input_paths["old_bundle"])
    old_decisions = _load_json(input_paths["old_decisions"])
    comparison = _load_json(input_paths["structural_comparison"])
    annotations = _load_json(input_paths["evaluation_annotations"])

    decisions_hash = sha256_file(input_paths["decisions"])
    if (
        decisions.get("pilot_run_id") != RUN_ID
        or decisions.get("claims_reviewed") != CLAIMS_TOTAL
        or decisions.get("pending") != 0
        or freeze_receipt.get("BLIND_REVIEW_COMPLETED_BEFORE_COMPARISON")
        is not True
        or (freeze_receipt.get("decisions") or {}).get("sha256")
        != decisions_hash
        or comparison.get("controlled_run_id") != RUN_ID
        or len(old_decisions.get("claims") or []) != 70
    ):
        raise PilotError("PILOT3_S3_FREEZE_OR_COMPARISON_INVALID")

    frozen_inputs = freeze_receipt.get("frozen_inputs") or {}
    freeze_names = {
        "source_pdf": "source",
        "prompt_file": "prompt",
        "extraction_bundle": "new_bundle",
        "evidence_v2": "evidence_v2",
        "quote_fidelity": "quote_fidelity",
    }
    if any(
        (frozen_inputs.get(receipt_name) or {}).get("sha256")
        != input_hashes_pre[path_name]
        for receipt_name, path_name in freeze_names.items()
    ):
        raise PilotError("PILOT3_S3_S3A_FROZEN_INPUT_CHANGED")
    if production_pre["sha256"] != (
        frozen_inputs.get("production_db") or {}
    ).get("sha256"):
        raise PilotError("PILOT3_S3_PRODUCTION_BASELINE_CHANGED")
    original_post = pre_review.get("original_artifacts_post") or {}
    if (
        input_hashes_pre["old_bundle"]
        != (original_post.get("original_extraction_bundle") or {}).get("sha256")
        or input_hashes_pre["old_decisions"]
        != (original_post.get("original_human_review_decisions") or {}).get(
            "sha256"
        )
    ):
        raise PilotError("PILOT3_S3_ORIGINAL_ARTIFACT_CHANGED")

    outcomes, new_failures, retention_rows = _validate_evaluation_annotations(
        annotations, old_decisions, decisions, comparison
    )
    metrics = _decision_metrics(decisions, old_decisions, quote)
    old_baseline = metrics["old_baseline"]
    retention_counts = Counter(
        item["retention_category"] for item in retention_rows
    )
    outcome_counts = Counter(item["repair_outcome"] for item in outcomes)
    failure_comparison = {
        name: {
            "old": old_baseline["primary_semantic_failure_category_counts"][name],
            "new": metrics["primary_semantic_failure_category_counts"][name],
            "delta": metrics["primary_semantic_failure_category_counts"][name]
            - old_baseline["primary_semantic_failure_category_counts"][name],
        }
        for name in sorted(FAILURE_CATEGORIES)
    }
    for name in ("TIME_NORMALIZATION", "NUMBER_NORMALIZATION"):
        failure_comparison[name] = {
            "old": old_baseline["secondary_diagnostics"][name],
            "new": metrics["secondary_diagnostics"][name],
            "delta": metrics["secondary_diagnostics"][name]
            - old_baseline["secondary_diagnostics"][name],
        }

    verdict = annotations.get("PILOT3_SEMANTIC_REPAIR_VERDICT")
    next_gate = annotations.get("PHASE3C_NEXT_GATE")
    if (
        verdict not in SEMANTIC_REPAIR_VERDICTS
        or next_gate not in NEXT_GATES
        or (verdict in {"PASS", "PASS_WITH_RESIDUALS"}
            and next_gate != "Cross-Pilot Evidence Fidelity Repair")
        or (verdict == "FAIL" and next_gate == "Cross-Pilot Evidence Fidelity Repair")
        or annotations.get("POST_REPAIR_INDEPENDENT_PILOT_REQUIRED") is not True
        or not isinstance(annotations.get("NOISY_SOURCE_PREPROCESSING_BACKLOG"), bool)
    ):
        raise PilotError("PILOT3_S3_VERDICT_GATE_INVALID")

    evaluation = {
        "document_type": EVALUATION_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE",
        "pilot_run_id": RUN_ID,
        "BLIND_REVIEW_COMPLETED_BEFORE_COMPARISON": True,
        "S3_A_DECISIONS_SHA256": decisions_hash,
        "semantic_comparison": {
            "old_claims": old_baseline["claims"],
            "new_claims": metrics["claims_total"],
            "old_supported": old_baseline["semantic_counts"]["SUPPORTED"],
            "new_supported": metrics["semantic_counts"]["SUPPORTED"],
            "old_unsupported": old_baseline["semantic_counts"]["UNSUPPORTED"],
            "new_unsupported": metrics["semantic_counts"]["UNSUPPORTED"],
            "old_ambiguous": old_baseline["semantic_counts"]["AMBIGUOUS"],
            "new_ambiguous": metrics["semantic_counts"]["AMBIGUOUS"],
            "old_failure_rate_percent": old_baseline[
                "true_semantic_failure_rate"
            ]["percent"],
            "new_failure_rate_percent": metrics["true_semantic_failure_rate"][
                "percent"
            ],
            "pilot2_post_repair_failure_rate_percent": 11.76,
            "no_statistical_significance_claim": True,
        },
        "atomicity_comparison": {
            "old_issue_rate_percent": old_baseline["atomicity_issue_rate"][
                "percent"
            ],
            "new_issue_rate_percent": metrics["atomicity"]["issue_rate"][
                "percent"
            ],
            "old_material_failure_rate_percent": old_baseline[
                "material_atomicity_failure_rate"
            ]["percent"],
            "new_material_failure_rate_percent": metrics["atomicity"][
                "material_failure_rate"
            ]["percent"],
        },
        "failure_category_comparison": failure_comparison,
        "old_failure_repair_outcomes": outcomes,
        "old_failure_repair_outcome_counts": {
            name: outcome_counts[name] for name in sorted(REPAIR_OUTCOMES)
        },
        "NEW_POST_REPAIR_FAILURES": new_failures,
        "supported_information_retention": {
            "old_supported_claims": len(retention_rows),
            "counts": {
                name: retention_counts[name]
                for name in sorted(RETENTION_CATEGORIES)
            },
            "rows": retention_rows,
            "diagnostic_only": True,
            "formal_recall_metric": False,
        },
        "PILOT3_SEMANTIC_REPAIR_VERDICT": verdict,
        "verdict_rationale": annotations.get("verdict_rationale"),
        "failure_origin_diagnosis": copy.deepcopy(
            annotations.get("failure_origin_diagnosis") or {}
        ),
        "NOISY_SOURCE_PREPROCESSING_BACKLOG": annotations[
            "NOISY_SOURCE_PREPROCESSING_BACKLOG"
        ],
        "PHASE3C_NEXT_GATE": next_gate,
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": True,
    }

    regression_names = {
        "targeted_s3_tests",
        "semantic_repair_tests",
        "gate_c_attribution_tests",
        "phase3c_regressions",
        "full_pytest",
        "compileall",
    }
    regression = {
        name: {"status": "NOT_RUN", "detail": "Regression receipt not supplied."}
        for name in sorted(regression_names)
    }
    if regression_receipt_path is not None:
        receipt = _load_json(Path(regression_receipt_path))
        if (
            receipt.get("pilot_run_id") != RUN_ID
            or set(receipt.get("validation") or {}) != regression_names
            or any(
                item.get("status") != "PASS"
                for item in (receipt.get("validation") or {}).values()
            )
        ):
            raise PilotError("PILOT3_S3_REGRESSION_RECEIPT_INVALID")
        regression = copy.deepcopy(receipt["validation"])

    input_hashes_post = {
        name: sha256_file(path) for name, path in input_paths.items()
    }
    production_post = production_snapshot(Path(production_db_path).resolve())
    invariants = {
        "blind_review_completed_before_comparison": True,
        "s3_a_decisions_hash_stable": decisions_hash
        == (freeze_receipt.get("decisions") or {}).get("sha256"),
        "all_decisions_explicit": len(decisions.get("claims") or []) == CLAIMS_TOTAL,
        "pending_zero": decisions.get("pending") == 0,
        "semantic_and_evidence_axes_separate": True,
        "quote_drift_not_automatic_semantic_failure": metrics["quote_drift"][
            "semantic_outcomes"
        ]["SUPPORTED"]
        > 0,
        "old_14_failure_outcomes_reconcile": len(outcomes) == 14,
        "retention_categories_reconcile": len(retention_rows) == 53,
        "new_failures_separately_identified": len(new_failures)
        + len(
            {
                claim_id
                for item in outcomes
                for claim_id in item["related_new_claim_ids"]
                if any(
                    claim["claim_id"] == claim_id
                    and claim["semantic_support"] == "UNSUPPORTED"
                    for claim in decisions["claims"]
                )
            }
        )
        == metrics["semantic_counts"]["UNSUPPORTED"],
        "all_frozen_inputs_unchanged": input_hashes_pre == input_hashes_post,
        "production_unchanged": production_pre == production_post,
        "production_table_counts_unchanged": production_pre["table_counts"]
        == production_post["table_counts"],
        "prompt_unchanged": input_hashes_post["prompt"]
        == (frozen_inputs.get("prompt_file") or {}).get("sha256"),
        "evidence_v2_unchanged": input_hashes_post["evidence_v2"]
        == (frozen_inputs.get("evidence_v2") or {}).get("sha256"),
        "extraction_unchanged": input_hashes_post["new_bundle"]
        == (frozen_inputs.get("extraction_bundle") or {}).get("sha256"),
    }
    if not all(invariants.values()):
        raise PilotError("PILOT3_S3_INVARIANT_FAILED")

    run_output_dir = Path(run_output_dir).resolve()
    evaluation_output_dir = Path(evaluation_output_dir).resolve()
    metrics_path = run_output_dir / (
        "pilot3_controlled_reextraction_human_review_metrics.json"
    )
    report_path = run_output_dir / (
        "pilot3_controlled_reextraction_human_review_report.md"
    )
    evaluation_json_path = evaluation_output_dir / (
        "pilot3_semantic_repair_evaluation.json"
    )
    evaluation_report_path = evaluation_output_dir / (
        "pilot3_semantic_repair_evaluation.md"
    )
    metrics.update(
        {
            "document_type": METRICS_DOCUMENT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "status": "COMPLETE",
            "pilot_run_id": RUN_ID,
            "PHASE3C_PILOT3_SEMANTIC_REPAIR_IMPLEMENTED": True,
            "PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE": True,
            "PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_HUMAN_REVIEW_COMPLETE": True,
            "PILOT3_REEXTRACTION_MECHANICAL_GATE": "FAIL",
            "PILOT3_GENERALIZATION_VERDICT": "FAIL",
            "PILOT3_SEMANTIC_REPAIR_VERDICT": verdict,
            "PHASE3C_COMPLETE": False,
            "PRODUCTION_APPLY_READY": "NO",
            "PHASE3C_NEXT_GATE": next_gate,
            "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": True,
            "BLIND_REVIEW_COMPLETED_BEFORE_COMPARISON": True,
            "NOISY_SOURCE_PREPROCESSING_BACKLOG": annotations[
                "NOISY_SOURCE_PREPROCESSING_BACKLOG"
            ],
            "S3_A_DECISIONS_SHA256": decisions_hash,
            "semantic_repair_evaluation": evaluation,
            "input_hashes_pre": input_hashes_pre,
            "input_hashes_post": input_hashes_post,
            "invariants": invariants,
            "production_pre": production_pre,
            "production_post": production_post,
            "production_changed": False,
            "production_table_counts_changed": False,
            "llm_call": False,
            "extraction_rerun": False,
            "evidence_write": False,
            "production_write": False,
            "ima_invoked": False,
            "propagation_invoked": False,
            "legacy_ingestion_invoked": False,
            "frontend_required": False,
            "regression_validation": regression,
            "artifacts": {
                "decisions": str(input_paths["decisions"]),
                "s3a_freeze_receipt": str(input_paths["freeze_receipt"]),
                "human_review_metrics": str(metrics_path),
                "human_review_report": str(report_path),
                "semantic_repair_evaluation_json": str(evaluation_json_path),
                "semantic_repair_evaluation_report": str(
                    evaluation_report_path
                ),
            },
        }
    )
    write_json(metrics_path, metrics)
    report_path.write_text(
        _render_human_review_report(metrics, decisions["claims"]), encoding="utf-8"
    )
    write_json(evaluation_json_path, evaluation)
    evaluation_report_path.write_text(
        _render_evaluation_report(evaluation), encoding="utf-8"
    )
    return {
        "status": "COMPLETE",
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "evaluation_json_path": str(evaluation_json_path),
        "evaluation_report_path": str(evaluation_report_path),
        "S3_A_DECISIONS_SHA256": decisions_hash,
    }
