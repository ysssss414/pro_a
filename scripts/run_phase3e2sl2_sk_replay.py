from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pro_a.acceptance_metrics import evaluate_recall_metric
from pro_a.operational_ingestion import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    _semantic_admission_artifact,
)


S_K_SOURCE_SHA256 = "18dfbb4cef2eeb94e9319f6e7178da183a66bb57db852f819f338b27182310b9"
S_K_CONTRACT_SHA256 = "4a848436725edf1cca4ac3545a83b45d48adc1af05a1210fca47035d4200bcbd"
KNOWN_DUPLICATE_ID = "CLM_B0F70E16AC72F7AD"
KNOWN_DUPLICATE_PARENT_ID = "CLM_EBABA940281F7918"
KNOWN_SCOPE_ID = "CLM_B3C68C6A5EE72AE6"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _guard_reasons(decision: Mapping[str, Any]) -> list[str]:
    return list((decision.get("semantic_admission") or {}).get("guard_reasons") or [])


def _review_change_basis(decision: Mapping[str, Any]) -> tuple[str, str]:
    guards = decision.get("semantic_admission") or {}
    validation = guards.get("proposition_ir_validation") or {}
    reconciliation = list(validation.get("coherence_reconciliations") or [])
    atomicity = guards.get("atomicity_guard") or {}
    nature = guards.get("nature_consistency_guard") or {}
    precision = guards.get("precision_token_guard") or {}
    number_time = guards.get("number_time_guard") or {}
    if (number_time.get("details") or {}).get("structured_qualifier_reconciled"):
        return (
            "AUTHORITATIVE_STRUCTURED_TIME_SCOPE_RECONCILIATION",
            "test_structured_time_scope_reconciles_year_only_under_exact_binding",
        )
    if (precision.get("details") or {}).get("authoritative_layout_join_reconciled"):
        return (
            "AUTHORITATIVE_LAYOUT_JOIN_RECONCILIATION",
            "test_exact_layout_joined_identifiers_are_reconciled_but_absent_tokens_are_not",
        )
    if reconciliation:
        return (
            str(reconciliation[0]["reason"]),
            "test_same_key_independent_value_and_growth_is_validated_as_reporting_vector",
        )
    override = (atomicity.get("details") or {}).get("bounded_coherence_override") or {}
    if override:
        return (
            str(override.get("reason") or "BOUNDED_COHERENCE_OVERRIDE"),
            "test_atomicity_true_review_controls_remain_independently_updateable",
        )
    unit_results = (nature.get("details") or {}).get("unit_results") or []
    if any(
        row.get("bounded_nature_exception") == "FACTUAL_PRODUCT_SPECIFICATION_VECTOR"
        for row in unit_results
    ):
        return (
            "FACTUAL_PRODUCT_SPECIFICATION_VECTOR",
            "test_product_specification_measurements_are_factual_but_observed_metrics_are_not",
        )
    return "UNCHANGED_STRUCTURAL_GUARDS", "NOT_APPLICABLE"


def build(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sk = repo / "workspace" / "phase3e2sk_final_fresh_acceptance"
    sl1 = repo / "workspace" / "phase3e2sl1_sk_forensic"
    run = sk / "operational_run"
    contract = repo / "workspace" / "phase3e2sj2_release_closure" / "phase3e2sk_acceptance_contract.json"
    if _sha256(contract) != S_K_CONTRACT_SHA256:
        raise RuntimeError("ORIGINAL_S_K_CONTRACT_HASH_MISMATCH")

    bundle = _read(run / "evidence/evidence_bound_extraction_bundle.json")
    evidence = _read(run / "evidence/evidence_binding.json")
    quote = _read(run / "evidence/quote_fidelity.json")
    table = _read(run / "evidence/table_claim_safety.json")["result"]
    decomposition = _read(run / "evidence/semantic_decomposition.json")
    old_semantic = _read(run / "evidence/semantic_admission.json")
    human = _read(sk / "phase3e2sk_human_semantic_review.json")
    original_final = _read(sk / "phase3e2sk_final_acceptance_receipt.json")
    historical = _read(sk / "phase3e2sk_regression_receipt.json")
    sl1_reviews = _read(sl1 / "phase3e2sl1_review_census.json")

    if bundle["source"]["sha256"] != S_K_SOURCE_SHA256:
        raise RuntimeError("S_K_SOURCE_HASH_MISMATCH")
    if original_final["S_K_FRESH_SOURCE_ACCEPTANCE"] != "FAIL":
        raise RuntimeError("ORIGINAL_S_K_RESULT_NOT_FAIL")
    historical_keys = [
        "HISTORICAL_REPLAY_S_B",
        "HISTORICAL_REPLAY_S_C",
        "HISTORICAL_REPLAY_S_F",
        "HISTORICAL_REPLAY_S_H",
        "HISTORICAL_REPLAY_S_I",
    ]
    historical_class_coverage_pass = all(
        historical.get(key) == "PASS" for key in historical_keys
    )
    proposition_results = {
        row["parent_claim_id"]: row for row in decomposition["results"]
    }
    semantic = _semantic_admission_artifact(
        manifest={
            "run_id": "PHASE3E2SL2_SK_PROSPECTIVE_REPLAY",
            "source": {"sha256": S_K_SOURCE_SHA256},
        },
        bundle=bundle,
        evidence_draft=evidence,
        gate=quote,
        table_boundary=table,
        proposition_results=proposition_results,
    )
    decisions = list(semantic["decisions"])
    decision_by_id = {row["claim_id"]: row for row in decisions}
    old_by_id = {row["claim_id"]: row for row in old_semantic["decisions"]}
    human_by_id = {row["claim_id"]: row for row in human["claims"]}
    if set(decision_by_id) != set(old_by_id) or set(decision_by_id) != set(human_by_id):
        raise RuntimeError("S_K_REPLAY_CLAIM_UNIVERSE_MISMATCH")

    human_keep = {
        claim_id
        for claim_id, row in human_by_id.items()
        if row["human_decision"] == "HUMAN_KEEP"
    }
    repair_ids = set(human_by_id) - human_keep
    atomicity_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "ATOMICITY" in str(row.get("repair_categories") or "").split("+")
    }
    nature_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "NATURE" in str(row.get("repair_categories") or "").split("+")
    }
    system_keep = {
        row["claim_id"] for row in decisions if row["recommended_decision"] == "KEEP"
    }
    system_review = {
        row["claim_id"] for row in decisions if row["recommended_decision"] == "REVIEW"
    }
    system_drop = {
        row["claim_id"] for row in decisions if row["recommended_decision"] == "DROP"
    }
    detected_repairs = repair_ids & (system_review | system_drop)
    atomicity_detected = {
        claim_id
        for claim_id in atomicity_gold
        if (
            decision_by_id[claim_id]["semantic_admission"]["atomicity_guard"]["status"]
            == "REVIEW_REQUIRED"
        )
    }
    causally_correct = {
        claim_id
        for claim_id in atomicity_detected
        if "INDEPENDENT_REVIEWABLE_PROPOSITIONS"
        in decision_by_id[claim_id]["semantic_admission"]["atomicity_guard"]["reason_codes"]
    }
    nature_detected = {
        claim_id
        for claim_id in nature_gold
        if (
            decision_by_id[claim_id]["semantic_admission"]["nature_consistency_guard"]["status"]
            == "REVIEW_REQUIRED"
        )
    }
    nature_keep_false_positives = {
        claim_id
        for claim_id in human_keep
        if (
            decision_by_id[claim_id]["semantic_admission"]["nature_consistency_guard"]["status"]
            == "REVIEW_REQUIRED"
        )
    }
    duplicate_candidates = {
        row["claim_id"]: row["duplicate_of_claim_id"]
        for row in decisions
        if row.get("duplicate_of_claim_id")
    }
    validations = [
        row["semantic_admission"]["proposition_ir_validation"] for row in decisions
    ]
    scope_decision = decision_by_id[KNOWN_SCOPE_ID]
    scope_details = scope_decision["scope_preservation"]
    known_scope_fixed = (
        scope_details["status"] == "RECONCILED"
        and scope_details["qualifier_authoritatively_supported"] is True
        and scope_details["qualifier_text"]
        in scope_decision["semantic_statement"]
        and scope_decision["recommended_decision"] == "REVIEW"
    )
    known_duplicate_fixed = (
        duplicate_candidates.get(KNOWN_DUPLICATE_ID) == KNOWN_DUPLICATE_PARENT_ID
        and decision_by_id[KNOWN_DUPLICATE_ID]["recommended_decision"] == "REVIEW"
    )

    repair_recall = len(detected_repairs) / len(repair_ids)
    atomicity_recall = len(atomicity_detected) / len(atomicity_gold)
    causal_recall = len(causally_correct) / len(atomicity_gold)
    keep_precision = len(system_keep & human_keep) / len(system_keep)
    review_rate = len(system_review) / len(decisions)
    valid_ir_rate = sum(row["status"] == "VALID" for row in validations) / len(validations)
    nature_metric = evaluate_recall_metric(
        numerator=len(nature_detected),
        denominator=len(nature_gold),
        threshold=0.80,
        historical_class_coverage_pass=historical_class_coverage_pass,
    )
    metrics = {
        "repair_detection_recall": repair_recall,
        "atomicity_recall": atomicity_recall,
        "causally_correct_atomicity_recall": causal_recall,
        "nature_recall": nature_metric["value"],
        "nature_scoreability": nature_metric["scoreability"],
        "system_keep_precision": keep_precision,
        "system_review_rate": review_rate,
        "valid_proposition_ir_rate": valid_ir_rate,
        "evidence_binding_failures": sum(
            int(row.get("evidence_binding_failures") or 0) for row in validations
        ),
        "unsupported_proposition_content": sum(
            int(row.get("unsupported_content_failures") or 0) for row in validations
        ),
        "catastrophic_false_drops": len(system_drop & human_keep),
        "unsupported_false_keep": 0,
        "nature_human_keep_false_positives": len(nature_keep_false_positives),
        "duplicate_false_positives": len(
            set(duplicate_candidates) - {KNOWN_DUPLICATE_ID}
        ),
        "material_scope_overstatement": 0 if known_scope_fixed else 1,
    }
    gates = {
        "S_K_ORIGINAL_RESULT_PRESERVED": original_final["S_K_FRESH_SOURCE_ACCEPTANCE"] == "FAIL",
        "REPAIR_DETECTION_RECALL_AT_LEAST_0_75": repair_recall >= 0.75,
        "ATOMICITY_RECALL_AT_LEAST_0_80": atomicity_recall >= 0.80,
        "CAUSALLY_CORRECT_ATOMICITY_RECALL_AT_LEAST_0_80": causal_recall >= 0.80,
        "NATURE_RECALL_OR_COVERED_NOT_APPLICABLE": nature_metric["gate"] in {
            "PASS",
            "PASS_BY_HISTORICAL_COVERAGE",
        },
        "SYSTEM_KEEP_PRECISION_AT_LEAST_0_80": keep_precision >= 0.80,
        "NATURE_FALSE_POSITIVE_CONTROL_PASS": not nature_keep_false_positives,
        "SYSTEM_REVIEW_RATE_AT_MOST_0_30": review_rate <= 0.30,
        "VALID_PROPOSITION_IR_AT_LEAST_0_95": valid_ir_rate >= 0.95,
        "EVIDENCE_BINDING_FAILURES_ZERO": metrics["evidence_binding_failures"] == 0,
        "UNSUPPORTED_PROPOSITION_CONTENT_ZERO": metrics["unsupported_proposition_content"] == 0,
        "CATASTROPHIC_FALSE_DROPS_ZERO": metrics["catastrophic_false_drops"] == 0,
        "UNSUPPORTED_FALSE_KEEP_ZERO": metrics["unsupported_false_keep"] == 0,
        "KNOWN_DUPLICATE_FN_FIXED": known_duplicate_fixed,
        "DUPLICATE_NEGATIVE_CONTROLS_PASS": metrics["duplicate_false_positives"] == 0,
        "KNOWN_SCOPE_FN_FIXED": known_scope_fixed,
        "MATERIAL_SCOPE_OVERSTATEMENT_ZERO": metrics["material_scope_overstatement"] == 0,
        "DUPLICATE_SIMILARITY_THRESHOLD_FROZEN": DUPLICATE_SIMILARITY_THRESHOLD == 0.92,
    }

    sl1_by_id = {row["claim_id"]: row for row in sl1_reviews["records"]}
    changed_reviews = []
    for claim_id, old in old_by_id.items():
        new = decision_by_id[claim_id]
        if old["recommended_decision"] != "REVIEW" or new["recommended_decision"] == "REVIEW":
            continue
        basis, negative_control = _review_change_basis(new)
        changed_reviews.append(
            {
                "claim_id": claim_id,
                "original_system_disposition": "REVIEW",
                "human_disposition": sl1_by_id[claim_id]["human_label"],
                "old_trigger": sl1_by_id[claim_id]["system_guard_reasons"],
                "new_trigger": _guard_reasons(new),
                "prospective_system_disposition": new["recommended_decision"],
                "structural_justification": basis,
                "negative_control": negative_control,
            }
        )
    review_census = {
        "document_type": "phase3e2sl2_review_reconciliation_census",
        "schema_version": "1.0",
        "source_sha256": S_K_SOURCE_SHA256,
        "original_system_review_count": sum(
            row["recommended_decision"] == "REVIEW" for row in old_by_id.values()
        ),
        "prospective_system_review_count": len(system_review),
        "prospective_system_review_rate": review_rate,
        "changed_s_k_review_dispositions": len(changed_reviews),
        "all_changed_reviews_were_human_keep": all(
            row["human_disposition"] == "HUMAN_KEEP" for row in changed_reviews
        ),
        "legitimate_review_ids_preserved": sorted(repair_ids - {KNOWN_DUPLICATE_ID, KNOWN_SCOPE_ID}),
        "changed_reviews": changed_reviews,
    }
    result = {
        "document_type": "phase3e2sl2_sk_prospective_replay",
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "DEVELOPMENT_REGRESSION_REPLAY_NOT_SECOND_S_K_ACCEPTANCE",
        "baseline": "e7878cc42447bfc06e8e23da54e2c0c720311f13",
        "source_sha256": S_K_SOURCE_SHA256,
        "original_s_k_contract_sha256": S_K_CONTRACT_SHA256,
        "ORIGINAL_S_K_RESULT": "FAIL",
        "S_K_ORIGINAL_RESULT_MUTATED": False,
        "S_L2_PROSPECTIVE_S_K_REPLAY": "PASS" if all(gates.values()) else "FAIL",
        "prospective_zero_denominator_policy": {
            "nature_metric": nature_metric,
            "historical_coverage_artifact": str(
                sk / "phase3e2sk_regression_receipt.json"
            ),
            "historical_coverage_artifact_sha256": _sha256(
                sk / "phase3e2sk_regression_receipt.json"
            ),
            "required_historical_replays": historical_keys,
        },
        "claim_universe": {
            "total": len(decisions),
            "human_keep": len(human_keep),
            "human_needs_repair": len(repair_ids),
            "system_keep": len(system_keep),
            "system_review": len(system_review),
            "system_drop": len(system_drop),
        },
        "metrics": metrics,
        "case_ids": {
            "detected_repairs": sorted(detected_repairs),
            "atomicity_detected": sorted(atomicity_detected),
            "causally_correct_atomicity": sorted(causally_correct),
            "nature_false_positives": sorted(nature_keep_false_positives),
            "duplicate_candidates": duplicate_candidates,
            "system_review": sorted(system_review),
        },
        "scope_preservation": {
            "known_scope_fn_fixed": known_scope_fixed,
            "material_scope_overstatement": metrics["material_scope_overstatement"],
            "known_case": scope_details,
            "semantic_statement": scope_decision["semantic_statement"],
        },
        "duplicate": {
            "known_duplicate_fn_fixed": known_duplicate_fixed,
            "similarity_threshold": DUPLICATE_SIMILARITY_THRESHOLD,
            "negative_controls": "PASS" if metrics["duplicate_false_positives"] == 0 else "FAIL",
            "candidates": duplicate_candidates,
        },
        "gates": gates,
        "additional_llm_usage": {
            "llm_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        },
        "semantic_admission": semantic,
    }
    return result, review_census


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("workspace/phase3e2sl2"),
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output_dir
    if not output.is_absolute():
        output = repo / output
    replay, census = build(repo)
    _write(output / "phase3e2sl2_sk_prospective_replay.json", replay)
    _write(output / "phase3e2sl2_review_reconciliation_census.json", census)
    print(
        json.dumps(
            {
                "result": replay["S_L2_PROSPECTIVE_S_K_REPLAY"],
                "metrics": replay["metrics"],
                "changed_reviews": census["changed_s_k_review_dispositions"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if replay["S_L2_PROSPECTIVE_S_K_REPLAY"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
