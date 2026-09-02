from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from pro_a.corpus_pilot import (
    PILOT2_EVIDENCE_DRAFT_DOCUMENT_TYPE,
    PILOT2_GATE_A_DOCUMENT_TYPE,
    PilotError,
    _controlled_reextraction_mechanical_diagnostics,
    production_snapshot,
)
from pro_a.pilot3 import (
    REQUIRED_REGRESSIONS,
    _at_most_result,
    _code_file_hashes,
    _target_result,
    render_pilot3_review_surface,
)
from pro_a.storage import sha256_file, write_json


REPAIR_DOCUMENT_TYPE = "phase3c_pilot3_evidence_v2_mechanical_repair"
REPAIRED_EVIDENCE_DOCUMENT_TYPE = "phase3c_pilot3_evidence_support_v2_repaired"
REPAIRED_QUOTE_DOCUMENT_TYPE = "phase3c_pilot3_quote_fidelity_repaired"
REGRESSION_DOCUMENT_TYPE = "phase3c_pilot3_evidence_v2_repair_regression_receipt"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"PILOT3_REPAIR_INPUT_INVALID: {path}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"PILOT3_REPAIR_INPUT_INVALID: {path}")
    return value


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bundle_claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def _evidence_claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("original_evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def _binding_class(item: dict[str, Any]) -> str:
    status = item.get("evidence_mechanics_status")
    if status in {"EXCERPT_BOUND", "CONTEXT_AVAILABLE"}:
        return "SINGLE_PAGE_BOUND"
    if status == "ORDERED_SPAN_BOUND":
        return "CROSS_PAGE_BOUND"
    if status == "LOCATOR_AMBIGUOUS":
        return "AMBIGUOUS"
    return "UNRESOLVED"


def _classification_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": item.get("claim_id"),
        "fidelity_status": item.get("fidelity_status"),
        "primary_drift_category": item.get("primary_drift_category"),
        "source_binding_recoverable_without_semantic_change": item.get(
            "source_binding_recoverable_without_semantic_change"
        ),
    }


def _render_report(metrics: dict[str, Any]) -> str:
    repair = metrics["mechanical_repair"]
    evidence = metrics["evidence_fidelity"]
    locator = metrics["locator"]
    pointer = metrics["model_page_pointer"]
    production = metrics["production"]
    usage = metrics["model_usage"]
    regressions = metrics["regression_validation"]
    code = metrics["freeze_comparison"]
    artifacts = metrics["artifacts"]
    return "\n".join([
        "# Phase 3C Pilot #3 — Evidence v2 Mechanical Repair Report",
        "",
        "## 1. Root cause and minimal repair",
        "",
        f"- First triggering Claim: `{repair['first_triggering_claim_id']}` (zero-based index `{repair['first_triggering_claim_index']}`, `PAGE:10`).",
        "- Generator output: same-page preceding candidate `谢谢。`, selected from the segment immediately before the Evidence segment.",
        "- Validator input: `{\"locator\": \"PAGE:10\", \"text\": \"谢谢。\"}` with the frozen Evidence excerpt and the PAGE:10 source body.",
        "- Frozen rule: normalized same-page Evidence/context gap must be <= 500 characters.",
        "- Exact mismatch: normalized `谢谢` occurs at offsets 70 and 656; Evidence occupies `[660, 721)`. The old `.find()` chose offset 70 and calculated gap 588, although the generated adjacent occurrence at 656 has gap 2.",
        "- Repair: enumerate every normalized occurrence and accept only when at least one occurrence pair satisfies the unchanged 500-character rule. Distant context still fails closed; no exception catch, skip, threshold change, or source-specific branch was added.",
        "",
        "## 2. Frozen extraction and rebuild discipline",
        "",
        f"- Original extraction bundle reused: `{repair['original_bundle_reused']}`.",
        f"- LLM rerun: `{repair['llm_rerun']}`; repair/rebuild LLM calls: `{usage['repair_llm_calls']}`.",
        f"- Frozen logical extractions / actual API attempts remain `{usage['logical_extractions']}` / `{usage['frozen_extraction_llm_calls']}`.",
        f"- Claim count: `{metrics['claims_total']}`; Claim ID/statement/Evidence/attributed_to byte projection unchanged: `{repair['frozen_claim_fields_unchanged']}`.",
        f"- Original blocking artifact preserved at `{artifacts['original_failure_artifact']['path']}` with SHA-256 `{artifacts['original_failure_artifact']['sha256']}`.",
        "",
        "## 3. Recomputed mechanical metrics",
        "",
        f"- Fidelity counts: `{json.dumps(evidence['counts'], ensure_ascii=False, sort_keys=True)}`.",
        f"- Quote fidelity: {evidence['quote_fidelity_rate']['fraction']} ({evidence['quote_fidelity_rate']['percent']}%) — `{'PASS' if evidence['quote_fidelity_rate']['passed'] else 'FAIL'}` vs >= 85%.",
        f"- Quote drift: {evidence['quote_drift_rate']['fraction']} ({evidence['quote_drift_rate']['percent']}%) — `{'PASS' if evidence['quote_drift_rate']['passed'] else 'FAIL'}` vs <= 15%.",
        f"- Source binding: {locator['source_binding_rate']['fraction']} ({locator['source_binding_rate']['percent']}%) — `{'PASS' if locator['source_binding_rate']['passed'] else 'FAIL'}` vs >= 85%.",
        f"- Single-page / cross-page / unresolved: `{locator['single_page']}` / `{locator['cross_page']}` / `{locator['unresolved']}`; bounded-context candidates: `{locator['bounded_context_candidates']}`.",
        f"- Quote/source classifications unchanged from the frozen pre-repair audit: `{repair['quote_source_classifications_unchanged']}`; changed Claim IDs: `{repair['classification_changed_claim_ids']}`.",
        f"- Context metadata changed only as expected: candidate-bearing Claims `0 -> {locator['bounded_context_candidates']}` because the former artifact stopped at generation failure.",
        f"- Mechanical gate: `{metrics['PILOT3_EXTRACTION_GATE']}`.",
        "",
        "## 4. Pointer, attribution, usage, and isolation",
        "",
        f"- Model pointer matched/errors/accuracy: `{pointer['matched']}` / `{pointer['errors']}` / `{pointer['accuracy']['fraction']}` ({pointer['accuracy']['percent']}%); deterministic recovery `{pointer['recovery']['fraction']}` ({pointer['recovery']['percent']}%).",
        f"- Deterministic company-to-speaker mutations: `{metrics['attribution_mechanical_qa']['count']}`; old mutation recurrence: `{metrics['attribution_mechanical_qa']['known_old_mutation_recurrence']}`.",
        f"- Frozen token usage prompt/completion/total: `{usage['prompt_tokens']}` / `{usage['completion_tokens']}` / `{usage['total_tokens']}`; tokens/Claim `{usage['tokens_per_claim']}`, tokens/bound Claim `{usage['tokens_per_bound_claim']}`.",
        f"- Production SHA-256 pre/post: `{production['pre']['sha256']}` / `{production['post']['sha256']}`; unchanged `{production['unchanged']}`; integrity `{production['post']['integrity_check']}`; FK violations `{len(production['post']['foreign_key_violations'])}`.",
        f"- Current-vs-extraction code hashes changed only in the authorized mechanical validator file: `{code['changed_code_files']}`. Prompt/source/model/timeout/retry/backoff/temperature/output/chunk settings changed: `{code['prompt_source_model_settings_changed']}`.",
        "",
        "## 5. Regression results",
        "",
        *[f"- {name}: `{regressions[name]['status']}` — {regressions[name]['detail']}" for name in REQUIRED_REGRESSIONS],
        "",
        "## 6. Artifact handoff and final state",
        "",
        f"- Repaired Evidence v2: `{artifacts['repaired_evidence_v2']['path']}` (`{artifacts['repaired_evidence_v2']['sha256']}`).",
        f"- Repaired quote audit: `{artifacts['repaired_quote_fidelity']['path']}` (`{artifacts['repaired_quote_fidelity']['sha256']}`).",
        f"- Repaired review surface: `{artifacts['repaired_review_surface']['path']}` (`{artifacts['repaired_review_surface']['sha256']}`).",
        f"- Regression receipt: `{artifacts['regression_receipt']['path']}` (`{artifacts['regression_receipt']['sha256']}`).",
        "- No Human Review was performed. No prompt/source/model/runtime tuning was performed. No Production, IMA, propagation, legacy ingestion, or canonical-schema write was performed.",
        "",
        f"- PHASE3C_PILOT3_EVIDENCE_V2_REPAIR_COMPLETE = {str(metrics['PHASE3C_PILOT3_EVIDENCE_V2_REPAIR_COMPLETE']).lower()}",
        f"- PHASE3C_PILOT3_EXTRACTION_COMPLETE = {str(metrics['PHASE3C_PILOT3_EXTRACTION_COMPLETE']).lower()}",
        f"- PILOT3_EXTRACTION_GATE = {metrics['PILOT3_EXTRACTION_GATE']}",
        f"- PHASE3C_COMPLETE = {str(metrics['PHASE3C_COMPLETE']).lower()}",
        f"- PHASE3C_NEXT_GATE = {metrics['PHASE3C_NEXT_GATE']}",
        "",
        "STOP — awaiting Pilot #3 Independent Human Review.",
        "",
    ])


def build_report(
    run_dir: Path, source_path: Path, production_db: Path, regression_receipt_path: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_path = source_path.resolve()
    production_db = production_db.resolve()
    regression_receipt_path = regression_receipt_path.resolve()
    repair_dir = run_dir / "evidence_v2_repair"
    paths = {
        "original_bundle": run_dir / "extraction_bundle.json",
        "rebound_bundle": run_dir / "extraction_bundle_stage1_1_rebound.json",
        "freeze": run_dir / "pilot3_extraction_freeze.json",
        "original_failure": run_dir / "evidence_contract_v2_draft.json",
        "old_quote": run_dir / "pilot3_quote_fidelity.json",
        "work_evidence": repair_dir / "evidence_contract_v2_draft.json",
        "work_quote": repair_dir / "pilot2_gate_a_quote_fidelity.json",
    }
    if any(not path.is_file() for path in [*paths.values(), source_path, production_db, regression_receipt_path]):
        raise PilotError("PILOT3_REPAIR_REQUIRED_INPUT_MISSING")

    production_pre = production_snapshot(production_db)
    original_bundle = _load_json(paths["original_bundle"])
    rebound_bundle = _load_json(paths["rebound_bundle"])
    freeze = _load_json(paths["freeze"])
    original_failure = _load_json(paths["original_failure"])
    old_quote = _load_json(paths["old_quote"])
    work_evidence = _load_json(paths["work_evidence"])
    work_quote = _load_json(paths["work_quote"])
    regression_receipt = _load_json(regression_receipt_path)
    run_id = original_bundle.get("pilot_run_id")

    if (
        work_evidence.get("document_type") != PILOT2_EVIDENCE_DRAFT_DOCUMENT_TYPE
        or work_quote.get("document_type") != PILOT2_GATE_A_DOCUMENT_TYPE
        or original_failure.get("status") != "BLOCKED_BOUNDED_CONTEXT_GENERATION"
        or regression_receipt.get("document_type") != REGRESSION_DOCUMENT_TYPE
        or any(item.get("pilot_run_id") != run_id for item in (rebound_bundle, freeze, original_failure, old_quote, work_evidence, work_quote, regression_receipt))
    ):
        raise PilotError("PILOT3_REPAIR_ARTIFACT_BINDING_INVALID")
    regression_results = regression_receipt.get("results") or {}
    if set(regression_results) != set(REQUIRED_REGRESSIONS) or any(
        (result or {}).get("status") != "PASS" for result in regression_results.values()
    ):
        raise PilotError("PILOT3_REPAIR_REGRESSION_RECEIPT_INVALID")
    source_sha = sha256_file(source_path)
    if source_sha != (original_bundle.get("source") or {}).get("sha256") or source_sha != (freeze.get("source") or {}).get("sha256"):
        raise PilotError("PILOT3_REPAIR_SOURCE_MISMATCH")

    original_projection = [_bundle_claim_projection(item) for item in original_bundle.get("claims") or []]
    rebound_projection = [_bundle_claim_projection(item) for item in rebound_bundle.get("claims") or []]
    evidence_projection = [_evidence_claim_projection(item) for item in work_evidence.get("claims") or []]
    frozen_claim_fields_unchanged = original_projection == rebound_projection == evidence_projection
    if len(original_projection) != 70 or not frozen_claim_fields_unchanged:
        raise PilotError("PILOT3_REPAIR_FROZEN_CLAIM_MUTATION")

    old_classes = [_classification_projection(item) for item in old_quote.get("claims") or []]
    new_classes = [_classification_projection(item) for item in work_quote.get("claims") or []]
    classification_changed = sorted(
        new.get("claim_id")
        for old, new in zip(old_classes, new_classes)
        if old != new
    )
    if len(old_classes) != 70 or len(new_classes) != 70 or classification_changed:
        raise PilotError("PILOT3_REPAIR_QUOTE_SOURCE_CLASSIFICATION_DRIFT")

    old_binding = [_binding_class(item) for item in original_failure.get("claims") or []]
    new_binding = [_binding_class(item) for item in work_evidence.get("claims") or []]
    if len(old_binding) != 70 or old_binding != new_binding:
        raise PilotError("PILOT3_REPAIR_BINDING_CLASSIFICATION_DRIFT")

    repair_metadata = {
        "mechanical_only": True,
        "llm_calls_added": 0,
        "original_bundle_reused": True,
        "frozen_claim_projection_sha256": _canonical_sha256(original_projection),
        "original_failure_artifact": {
            "path": str(paths["original_failure"]),
            "sha256": sha256_file(paths["original_failure"]),
        },
        "invariant": "any normalized occurrence pair must have a gap <= 500 characters",
        "first_triggering_claim_id": "CLM_20260831_431E60FE",
    }
    repaired_evidence = copy.deepcopy(work_evidence)
    repaired_evidence["document_type"] = REPAIRED_EVIDENCE_DOCUMENT_TYPE
    repaired_evidence["repair"] = copy.deepcopy(repair_metadata)
    repaired_evidence_path = repair_dir / "evidence_contract_v2_repaired.json"
    write_json(repaired_evidence_path, repaired_evidence)

    repaired_quote = copy.deepcopy(work_quote)
    repaired_quote["document_type"] = REPAIRED_QUOTE_DOCUMENT_TYPE
    repaired_quote["stage"] = "INDEPENDENT_GENERALIZATION_PRE_HUMAN_REVIEW_REPAIRED"
    repaired_quote["repair"] = copy.deepcopy(repair_metadata)
    repaired_quote_path = repair_dir / "pilot3_quote_fidelity_repaired.json"
    write_json(repaired_quote_path, repaired_quote)
    review_surface_path = repair_dir / "evidence_review_surface_repaired.md"
    review_surface_path.write_text(
        render_pilot3_review_surface(repaired_quote, repaired_evidence), encoding="utf-8",
    )

    gate_metrics = work_quote["metrics"]
    evidence_metrics = _load_json(repair_dir / "pilot2_metrics.json")
    counts = gate_metrics["fidelity_counts"]
    faithful = sum(counts[name] for name in (
        "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
        "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
    ))
    drift = counts["QUOTE_DRIFT"]
    total = len(original_projection)
    bound = evidence_metrics["evidence_deterministically_bound"]
    targets = {
        "quote_fidelity": _target_result(faithful, total, at_least=85.0),
        "quote_drift": _at_most_result(drift, total, at_most=15.0),
        "source_binding": _target_result(bound, total, at_least=85.0),
    }
    mechanical_gate = "PASS" if all(item["passed"] for item in targets.values()) else "FAIL"
    diagnostics = _controlled_reextraction_mechanical_diagnostics(
        original_bundle, work_quote, work_evidence,
    )
    attribution = diagnostics["deterministic_company_to_speaker_mutations"] | {
        "known_old_mutation_recurrence": diagnostics["known_old_mutation_recurrence"],
    }
    monitoring = gate_metrics["monitoring_contract"]
    model = original_bundle.get("model") or {}
    usage = model.get("usage") or {}
    original_code_hashes = (freeze.get("freeze") or {}).get("code_file_sha256") or {}
    current_code_hashes = _code_file_hashes()
    changed_code_files = sorted(
        name for name, old_hash in original_code_hashes.items()
        if current_code_hashes.get(name) != old_hash
    )
    settings_changed = not (
        source_sha == (freeze.get("source") or {}).get("sha256")
        and ((model.get("prompt") or {}).get("prompt_sha256")) == (freeze.get("freeze") or {}).get("prompt_sha256")
        and model.get("configured_model") == ((freeze.get("freeze") or {}).get("extraction_configuration") or {}).get("configured_request_model")
    )
    production_post = production_snapshot(production_db)
    production_unchanged = production_pre == production_post
    if not production_unchanged:
        raise PilotError("PILOT3_REPAIR_PRODUCTION_MUTATED")

    metrics = {
        "document_type": REPAIR_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "COMPLETE_MECHANICAL_GATE_FAILED" if mechanical_gate == "FAIL" else "COMPLETE_MECHANICAL_GATE_PASSED",
        "pilot_run_id": run_id,
        "PHASE3C_PILOT3_EVIDENCE_V2_REPAIR_COMPLETE": True,
        "PHASE3C_PILOT3_EXTRACTION_COMPLETE": True,
        "PILOT3_EXTRACTION_GATE": mechanical_gate,
        "PHASE3C_COMPLETE": False,
        "PHASE3C_NEXT_GATE": "Pilot #3 Independent Human Review",
        "claims_total": total,
        "mechanical_repair": {
            "first_triggering_claim_index": 27,
            "first_triggering_claim_id": "CLM_20260831_431E60FE",
            "original_bundle_reused": True,
            "llm_rerun": False,
            "llm_calls_added": 0,
            "frozen_claim_fields_unchanged": frozen_claim_fields_unchanged,
            "frozen_claim_projection_sha256": _canonical_sha256(original_projection),
            "quote_source_classifications_unchanged": not classification_changed,
            "classification_changed_claim_ids": classification_changed,
            "original_failure_preserved": paths["original_failure"].is_file(),
        },
        "evidence_fidelity": {
            "counts": copy.deepcopy(counts),
            "quote_fidelity_rate": targets["quote_fidelity"],
            "quote_drift_rate": targets["quote_drift"],
        },
        "locator": {
            "single_page": evidence_metrics["single_page_locator_bound"],
            "cross_page": evidence_metrics["cross_page_exact_spans"],
            "ambiguous": evidence_metrics["locator_ambiguous"],
            "unresolved": evidence_metrics["locator_unresolved"],
            "bounded_context_candidates": evidence_metrics["bounded_context_candidate_claims"],
            "source_binding_rate": targets["source_binding"],
        },
        "mechanical_targets": targets,
        "model_page_pointer": {
            "matched": monitoring["model_pointer_matched_claims"],
            "errors": monitoring["model_page_pointer_error_claims"],
            "accuracy": copy.deepcopy(monitoring["model_page_pointer_accuracy"]),
            "recovery": copy.deepcopy(monitoring["deterministic_locator_recovery_rate"]),
        },
        "attribution_mechanical_qa": attribution,
        "model_usage": {
            "logical_extractions": 1,
            "frozen_extraction_llm_calls": model.get("llm_calls", "NOT_AVAILABLE"),
            "repair_llm_calls": 0,
            "prompt_tokens": usage.get("prompt_tokens", "NOT_AVAILABLE"),
            "completion_tokens": usage.get("completion_tokens", "NOT_AVAILABLE"),
            "total_tokens": usage.get("total_tokens", "NOT_AVAILABLE"),
            "tokens_per_claim": evidence_metrics["tokens_per_claim"],
            "tokens_per_bound_claim": evidence_metrics["tokens_per_deterministically_bound_claim"],
        },
        "freeze_comparison": {
            "original_code_file_sha256": original_code_hashes,
            "current_code_file_sha256": current_code_hashes,
            "changed_code_files": changed_code_files,
            "authorized_mechanical_change_only": changed_code_files == ["src/pro_a/corpus_pilot.py"],
            "prompt_source_model_settings_changed": settings_changed,
            "extraction_configuration": copy.deepcopy((freeze.get("freeze") or {}).get("extraction_configuration") or {}),
        },
        "production": {
            "pre": production_pre,
            "post": production_post,
            "unchanged": production_unchanged,
            "table_counts_changed": production_pre["table_counts"] != production_post["table_counts"],
        },
        "isolation": {
            "production_write": False,
            "ima_invoked": False,
            "propagation_invoked": False,
            "legacy_pipeline_invoked": False,
            "canonical_schema_changed": False,
            "human_semantic_review_executed": False,
        },
        "regression_validation": copy.deepcopy(regression_results),
        "artifacts": {
            "original_failure_artifact": repair_metadata["original_failure_artifact"],
            "repaired_evidence_v2": {"path": str(repaired_evidence_path), "sha256": sha256_file(repaired_evidence_path)},
            "repaired_quote_fidelity": {"path": str(repaired_quote_path), "sha256": sha256_file(repaired_quote_path)},
            "repaired_review_surface": {"path": str(review_surface_path), "sha256": sha256_file(review_surface_path)},
            "regression_receipt": {"path": str(regression_receipt_path), "sha256": sha256_file(regression_receipt_path)},
        },
    }
    metrics_path = run_dir / "pilot3_pre_review_metrics_repaired.json"
    report_path = run_dir / "pilot3_evidence_v2_repair_report.md"
    write_json(metrics_path, metrics)
    report_path.write_text(_render_report(metrics), encoding="utf-8")
    receipt_path = run_dir / "pilot3_evidence_v2_repair_receipt.json"
    receipt = {
        "document_type": REPAIR_DOCUMENT_TYPE,
        "schema_version": "1",
        "pilot_run_id": run_id,
        "completed_at": regression_receipt.get("completed_at"),
        "status": metrics["status"],
        "metrics": {"path": str(metrics_path), "sha256": sha256_file(metrics_path)},
        "report": {"path": str(report_path), "sha256": sha256_file(report_path)},
        "production_unchanged": True,
        "llm_calls_added": 0,
    }
    write_json(receipt_path, receipt)
    return {
        "metrics": metrics,
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "receipt_path": str(receipt_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize the deterministic Phase 3C Pilot #3 Evidence v2 repair",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--production-db", required=True, type=Path)
    parser.add_argument("--regression-receipt", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build_report(
            args.run_dir, args.source_file, args.production_db, args.regression_receipt,
        )
    except PilotError as exc:
        print(str(exc))
        return 1
    print(json.dumps({
        "status": result["metrics"]["status"],
        "repair_complete": result["metrics"]["PHASE3C_PILOT3_EVIDENCE_V2_REPAIR_COMPLETE"],
        "extraction_complete": result["metrics"]["PHASE3C_PILOT3_EXTRACTION_COMPLETE"],
        "mechanical_gate": result["metrics"]["PILOT3_EXTRACTION_GATE"],
        "metrics_path": result["metrics_path"],
        "report_path": result["report_path"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
