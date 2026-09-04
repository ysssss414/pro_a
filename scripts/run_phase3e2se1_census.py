from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pro_a.operational_ingestion import _semantic_admission_artifact
from pro_a.table_claim_safety import _normalize_pdf_locator_text


RUN_ID = "INGEST_4CE8B7B36EE3FAC6"
SOURCE_SHA256 = "4ce8b7b36ee3fac6cca73573d50f04e79d68fff3ecda4e4047d7fce5cc7ca40e"
BASELINE_HASHES = {
    "semantic_decomposition.json": "315d3703195caf00ace53d15ee567009fc542064a8f08a7c2592b4ffd6e2ad2b",
    "phase3e2se_sc_development_regression_report.json": "bf96f00d53533a7a8143ddc2c936305c567b8e708bf4a94843e19149b51a455d",
    "phase3e2se_final_qualification_report.json": "eb195cacedb50dd2054e0eb0c6f2b377ae50a6251613b789392f1fd2ce8c5486",
}


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
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frozen_inputs(authority: Path) -> dict[str, dict[str, Any]]:
    run = authority / "workspace" / "ingestion" / RUN_ID
    return {
        "bundle": _read(run / "evidence" / "evidence_bound_extraction_bundle.json"),
        "evidence": _read(run / "evidence" / "evidence_binding.json"),
        "quote": _read(run / "evidence" / "quote_fidelity.json"),
        "table": _read(run / "evidence" / "table_claim_safety.json")["result"],
        "human": _read(
            authority
            / "workspace"
            / "phase3e2sc"
            / "receipts"
            / "phase3e2sc_human_semantic_review.json"
        ),
        "atomicity": _read(
            authority
            / "workspace"
            / "phase3e2sd"
            / "phase3e2sd_atomicity_failure_census.json"
        ),
    }


def _semantic_artifact(
    frozen: Mapping[str, Mapping[str, Any]],
    decomposition: Mapping[str, Any],
) -> dict[str, Any]:
    proposition_results = {
        str(item["parent_claim_id"]): item
        for item in decomposition.get("results") or []
    }
    return _semantic_admission_artifact(
        manifest={"run_id": RUN_ID, "source": {"sha256": SOURCE_SHA256}},
        bundle=frozen["bundle"],
        evidence_draft=frozen["evidence"],
        gate=frozen["quote"],
        table_boundary=frozen["table"],
        proposition_results=proposition_results,
    )


def _evidence_failure_class(claim_text: str, evidence_text: str) -> str:
    claim_normalized = _normalize_pdf_locator_text(claim_text)
    evidence_normalized = _normalize_pdf_locator_text(evidence_text)
    if claim_normalized == evidence_normalized or claim_normalized in evidence_normalized:
        return "PUNCTUATION_OR_WHITESPACE_NORMALIZATION"
    return "CLAIM_VS_EVIDENCE_COORDINATE_MISMATCH"


def _evidence_census(
    frozen: Mapping[str, Mapping[str, Any]],
    decomposition: Mapping[str, Any],
    baseline_report: Mapping[str, Any],
) -> dict[str, Any]:
    claims = {str(item["claim_id"]): item for item in frozen["bundle"].get("claims") or []}
    quotes = {str(item["claim_id"]): item for item in frozen["quote"].get("claims") or []}
    rows = []
    for result in decomposition.get("results") or []:
        claim_id = str(result["parent_claim_id"])
        evidence_text = str(
            (quotes[claim_id].get("evidence_contract") or {}).get("canonical_ready_evidence")
            or ""
        )
        claim_text = str(claims[claim_id].get("statement") or "")
        classification = _evidence_failure_class(claim_text, evidence_text)
        for issue in result.get("validation", {}).get("issues") or []:
            if issue.get("code") != "EVIDENCE_QUOTE_NOT_RECOVERABLE":
                continue
            rows.append({
                "claim_id": claim_id,
                "failed_model_unit_index": issue.get("unit_index"),
                "classification": classification,
                "claim_text": claim_text,
                "bounded_evidence": evidence_text,
                "classification_basis": (
                    "repository PDF-locator normalization makes the Claim surface an exact "
                    "or contained match"
                    if classification == "PUNCTUATION_OR_WHITESPACE_NORMALIZATION"
                    else "Claim and bounded Evidence use different subject/prefix surfaces"
                ),
                "raw_failed_model_quote_retained": False,
            })
    counts = Counter(row["classification"] for row in rows)
    all_classes = (
        "MODEL_OFFSET_ERROR",
        "MODEL_QUOTE_NORMALIZATION_DRIFT",
        "CLAIM_VS_EVIDENCE_COORDINATE_MISMATCH",
        "MULTI_SPAN_SUPPORT",
        "PUNCTUATION_OR_WHITESPACE_NORMALIZATION",
        "ACTUAL_UNSUPPORTED_UNIT",
        "OTHER",
    )
    unsupported = int(
        (baseline_report.get("proposition_ir") or {}).get(
            "unsupported_proposition_content", 0
        )
    )
    return {
        "document_type": "phase3e2se1_evidence_binding_failure_census",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "authority": "FROZEN_PHASE3E2SE_SEMANTIC_OUTPUT",
        "llm_calls": 0,
        "failure_count": len(rows),
        "affected_claims": len({row["claim_id"] for row in rows}),
        "classification_counts": {name: counts.get(name, 0) for name in all_classes},
        "unsupported_proposition_content": unsupported,
        "unsupported_exception_identified": unsupported != 0,
        "audit_limitation": (
            "The v2 artifact intentionally did not retain failed raw model quotes. "
            "Classification therefore uses the exact frozen Claim/Evidence surfaces and "
            "repository normalization, not retrospective quote reconstruction."
        ),
        "cases": rows,
        "gate": (
            "PASS"
            if len(rows) == 14 and unsupported == 0
            else "FAIL"
        ),
    }


def _atomicity_census(
    frozen: Mapping[str, Mapping[str, Any]],
    decomposition: Mapping[str, Any],
    decisions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    result_by_id = {
        str(item["parent_claim_id"]): item for item in decomposition.get("results") or []
    }
    decision_by_id = {str(item["claim_id"]): item for item in decisions}
    human_by_id = {
        str(item["claim_id"]): item for item in frozen["human"].get("claim_decisions") or []
    }
    gold_ids = {
        claim_id for claim_id, row in human_by_id.items()
        if "ATOMICITY" in (row.get("repair_categories") or [])
    }
    expected = {
        str(item["claim_id"]): str(item["mechanism_class"])
        for item in frozen["atomicity"].get("cases") or []
    }
    review_rows = []
    valid_review_ids: set[str] = set()
    invalid_ids: set[str] = set()
    for claim_id, decision in decision_by_id.items():
        semantic = decision.get("semantic_admission") or {}
        validation = semantic.get("proposition_ir_validation") or {}
        atomicity = semantic.get("atomicity_guard") or {}
        if validation.get("status") != "VALID":
            invalid_ids.add(claim_id)
            review_class = "ATOMICITY_IR_INVALID"
        elif atomicity.get("status") == "REVIEW_REQUIRED":
            valid_review_ids.add(claim_id)
            review_class = (
                "ATOMICITY_TRUE_POSITIVE"
                if claim_id in gold_ids
                else "ATOMICITY_FALSE_POSITIVE"
            )
        else:
            continue
        review_rows.append({
            "claim_id": claim_id,
            "review_class": review_class,
            "human_atomicity_repair": claim_id in gold_ids,
            "validation_status": validation.get("status"),
            "atomicity_reason_codes": atomicity.get("reason_codes") or [],
            "mechanism_classes": (atomicity.get("details") or {}).get(
                "mechanism_classes"
            ) or [],
        })

    gold_rows = []
    failure_modes = Counter()
    for claim_id in sorted(gold_ids):
        result = result_by_id[claim_id]
        validation = result.get("validation") or {}
        decision = decision_by_id[claim_id]
        atomicity = (decision.get("semantic_admission") or {}).get("atomicity_guard") or {}
        details = atomicity.get("details") or {}
        mechanisms = list(details.get("mechanism_classes") or [])
        units = list(validation.get("normalized_units") or [])
        keys = {unit.get("coherence_key") for unit in units}
        if validation.get("status") != "VALID":
            mode = "INVALID_IR_PREVENTED_DECISION"
        elif atomicity.get("status") != "REVIEW_REQUIRED":
            mode = (
                "OVER_GROUPED_BY_COHERENCE"
                if len(units) > 1 and len(keys) <= 1
                else "UNDER_DECOMPOSED_BY_MODEL"
            )
        elif expected.get(claim_id) in mechanisms:
            mode = "CORRECT_DECOMPOSITION_CORRECT_POLICY"
        else:
            mode = "CORRECT_IR_BUT_POLICY_MISS"
        failure_modes[mode] += 1
        gold_rows.append({
            "claim_id": claim_id,
            "expected_mechanism_class": expected.get(claim_id),
            "validation_status": validation.get("status"),
            "unit_count": len(units),
            "coherence_keys": sorted(str(key) for key in keys if key),
            "atomicity_status": atomicity.get("status"),
            "observed_mechanism_classes": mechanisms,
            "failure_mode": mode,
        })
    true_positives = len(valid_review_ids & gold_ids)
    false_positives = len(valid_review_ids - gold_ids)
    return {
        "document_type": "phase3e2se1_atomicity_review_census",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "authority": "FROZEN_PHASE3E2SE_SEMANTIC_OUTPUT_AND_S_C_HUMAN_GOLD",
        "llm_calls": 0,
        "ATOMICITY_REVIEW_TOTAL": len(valid_review_ids),
        "ATOMICITY_TRUE_POSITIVE": true_positives,
        "ATOMICITY_FALSE_POSITIVE": false_positives,
        "ATOMICITY_IR_INVALID": len(invalid_ids),
        "ATOMICITY_REVIEW_INCLUDING_IR_INVALID": len(valid_review_ids | invalid_ids),
        "atomicity_gold_cases": len(gold_ids),
        "atomicity_gold_invalid_ir": len(gold_ids & invalid_ids),
        "gold_failure_mode_counts": dict(sorted(failure_modes.items())),
        "review_cases": review_rows,
        "gold_cases": gold_rows,
        "gate": (
            "PASS"
            if (len(valid_review_ids), true_positives, false_positives, len(invalid_ids))
            == (24, 10, 14, 13)
            else "FAIL"
        ),
    }


def _nature_census(
    frozen: Mapping[str, Mapping[str, Any]],
    decomposition: Mapping[str, Any],
    decisions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    result_by_id = {
        str(item["parent_claim_id"]): item for item in decomposition.get("results") or []
    }
    human_by_id = {
        str(item["claim_id"]): item for item in frozen["human"].get("claim_decisions") or []
    }
    claim_by_id = {
        str(item["claim_id"]): item for item in frozen["bundle"].get("claims") or []
    }
    rows = []
    class_counts = Counter()
    original_jiang = 0
    for decision in decisions:
        claim_id = str(decision["claim_id"])
        if human_by_id[claim_id].get("human_semantic_decision") != "KEEP":
            continue
        semantic = decision.get("semantic_admission") or {}
        validation = semantic.get("proposition_ir_validation") or {}
        nature = semantic.get("nature_consistency_guard") or {}
        if validation.get("status") != "VALID" or nature.get("status") != "REVIEW_REQUIRED":
            continue
        reasons = list(nature.get("reason_codes") or [])
        if "JIANG_OBJECT_FRONTING_MISCLASSIFIED_AS_FUTURE" in reasons:
            original_jiang += 1
        for reason in reasons:
            class_counts[reason] += 1
        rows.append({
            "claim_id": claim_id,
            "claim_nature": claim_by_id[claim_id].get("nature"),
            "claim_text": claim_by_id[claim_id].get("statement"),
            "proposition_ir": result_by_id[claim_id].get("proposition_ir"),
            "nature_rule_reason_codes": reasons,
            "unit_rule_results": (nature.get("details") or {}).get("unit_results") or [],
            "original_disposal_jiang_case": (
                "JIANG_OBJECT_FRONTING_MISCLASSIFIED_AS_FUTURE" in reasons
            ),
        })
    return {
        "document_type": "phase3e2se1_nature_false_positive_census",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "authority": "FROZEN_PHASE3E2SE_SEMANTIC_OUTPUT_AND_S_C_HUMAN_GOLD",
        "llm_calls": 0,
        "ORIGINAL_JIANG_FP_REMAINING": original_jiang,
        "NEW_NATURE_FP_COUNT": len(rows) - original_jiang,
        "NEW_NATURE_FP_CLASSES": dict(sorted(class_counts.items())),
        "nature_human_keep_false_positives": len(rows),
        "cases": rows,
        "gate": (
            "PASS"
            if len(rows) == 6 and original_jiang + (len(rows) - original_jiang) == 6
            else "FAIL"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    authority = args.authority_root.resolve()
    baseline = args.baseline_dir.resolve()
    output = args.output_dir.resolve()
    actual_hashes = {name: _sha256(baseline / name) for name in BASELINE_HASHES}
    if actual_hashes != BASELINE_HASHES:
        raise ValueError("frozen Phase 3E.2S-E baseline hash mismatch")
    decomposition = _read(baseline / "semantic_decomposition.json")
    baseline_report = _read(baseline / "phase3e2se_sc_development_regression_report.json")
    frozen = _frozen_inputs(authority)
    baseline_admission_path = baseline / "phase3e2se1_baseline_semantic_admission.json"
    if baseline_admission_path.exists():
        baseline_admission = _read(baseline_admission_path)
    else:
        baseline_admission = _semantic_artifact(frozen, decomposition)
        _write(baseline_admission_path, baseline_admission)
    decisions = list(baseline_admission["decisions"])
    freeze = {
        "document_type": "phase3e2se1_baseline_freeze_receipt",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "baseline_dir": str(baseline),
        "expected_sha256": BASELINE_HASHES,
        "actual_sha256": actual_hashes,
        "hashes_match": actual_hashes == BASELINE_HASHES,
        "derived_baseline_semantic_admission": {
            "path": str(baseline_admission_path),
            "sha256": _sha256(baseline_admission_path),
        },
        "stage1_llm_calls": 0,
    }
    evidence = _evidence_census(frozen, decomposition, baseline_report)
    atomicity = _atomicity_census(frozen, decomposition, decisions)
    nature = _nature_census(frozen, decomposition, decisions)
    _write(output / "phase3e2se1_baseline_freeze_receipt.json", freeze)
    _write(output / "phase3e2se1_evidence_binding_failure_census.json", evidence)
    _write(output / "phase3e2se1_atomicity_review_census.json", atomicity)
    _write(output / "phase3e2se1_nature_false_positive_census.json", nature)
    passed = all(item["gate"] == "PASS" for item in (evidence, atomicity, nature))
    print(json.dumps({
        "baseline_hashes_match": freeze["hashes_match"],
        "evidence_failure_count": evidence["failure_count"],
        "atomicity_review_total": atomicity["ATOMICITY_REVIEW_TOTAL"],
        "atomicity_true_positive": atomicity["ATOMICITY_TRUE_POSITIVE"],
        "atomicity_false_positive": atomicity["ATOMICITY_FALSE_POSITIVE"],
        "atomicity_ir_invalid": atomicity["ATOMICITY_IR_INVALID"],
        "original_jiang_fp_remaining": nature["ORIGINAL_JIANG_FP_REMAINING"],
        "new_nature_fp_count": nature["NEW_NATURE_FP_COUNT"],
        "census_complete": passed,
    }, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
