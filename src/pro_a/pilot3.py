from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from . import analyzer as analyzer_module
from . import corpus_pilot as corpus_pilot_module
from . import pipeline as pipeline_module
from . import prompts as prompts_module
from .config import AppConfig
from .corpus_pilot import (
    PILOT2_GATE_A_FIDELITY_STATUSES,
    PilotError,
    _controlled_reextraction_freeze,
    _controlled_reextraction_mechanical_diagnostics,
    _load_json,
    build_pilot2_evidence_support_draft,
    extract_pilot_source,
    production_snapshot,
    rebind_stage1_evidence_locators,
    run_pilot2_gate_a_quote_fidelity,
)
from .parsers import parse_source_with_diagnostics
from .storage import sha256_file, write_json


PILOT1_SOURCE_SHA256 = "387d641f2e00c969b3f5d037f0f53b06bf537ac394271bb8d33ced6275b21376"
PILOT2_SOURCE_SHA256 = "1ea71205fb04885f44ab0aa48b57586647c9c823d4b321f11d23d7505aa65f52"
PRODUCTION_BASELINE_SHA256 = "581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250"
SOURCE_SELECTION_DOCUMENT_TYPE = "phase3c_pilot3_source_selection_manifest"
PREFLIGHT_DOCUMENT_TYPE = "phase3c_pilot3_preflight_receipt"
REGRESSION_DOCUMENT_TYPE = "phase3c_pilot3_regression_receipt"
METRICS_DOCUMENT_TYPE = "phase3c_pilot3_pre_review_metrics"
REQUIRED_PROMPT_CATEGORIES = (
    "evidence_quote_verbatim_preservation",
    "claim_atomicity",
    "attribution_preservation",
    "conditionality_preservation",
    "entity_inference_prevention",
    "technical_term_inference_prevention",
    "scope_invention_prevention",
)
REQUIRED_REGRESSIONS = (
    "preflight_tests",
    "phase3a_regressions",
    "phase3b_regressions",
    "phase3c_regressions",
    "full_pytest",
    "frontend_tests",
    "frontend_build",
    "compileall",
)


def _code_file_hashes() -> dict[str, str]:
    paths = {
        "src/pro_a/analyzer.py": Path(analyzer_module.__file__).resolve(),
        "src/pro_a/prompts.py": Path(prompts_module.__file__).resolve(),
        "src/pro_a/pipeline.py": Path(pipeline_module.__file__).resolve(),
        "src/pro_a/corpus_pilot.py": Path(corpus_pilot_module.__file__).resolve(),
        "src/pro_a/pilot3.py": Path(__file__).resolve(),
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def pilot3_freeze(cfg: AppConfig) -> dict[str, Any]:
    """Return the exact Gate C execution freeze used by Pilot #3."""
    gate_b = _controlled_reextraction_freeze(cfg)
    categories = gate_b["prompt_categories"]
    missing = [name for name in REQUIRED_PROMPT_CATEGORIES if not categories.get(name)]
    if missing:
        raise PilotError(f"PILOT3_PROMPT_PROTECTION_MISSING: {','.join(missing)}")
    if cfg.llm.model != "deepseek-chat":
        raise PilotError("PILOT3_MODEL_INVALID")
    return {
        "gate_c_repaired_code_active": True,
        "prompt_sha256": gate_b["prompt_sha256"],
        "prompt_categories": copy.deepcopy(categories),
        "code_file_sha256": _code_file_hashes(),
        "evidence_contract": {
            "version": "2",
            "artifact_level_only": True,
            "model_evidence_is_proposed_quote": True,
            "deterministic_validation_required": True,
            "quote_drift_fail_closed": True,
            "automatic_quote_correction": False,
            "canonical_schema_changed": False,
        },
        "runtime_protections": {
            "grammatical_subject_separate_from_attributed_to": gate_b[
                "gate_b_attribution_repair_active"
            ],
            "company_to_speaker_mutation_removed": gate_b[
                "gate_b_attribution_repair_active"
            ],
            "model_page_pointer_authoritative": False,
            "deterministic_locator_authoritative": True,
            "claim_semantic_postprocessing_rewrite": False,
        },
        "extraction_configuration": copy.deepcopy(gate_b["extraction_configuration"]),
    }


def validate_source_selection_manifest(
    manifest_path: Path,
    source_path: Path,
    run_id: str,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    source_path = Path(source_path).resolve()
    if not manifest_path.is_file() or not source_path.is_file():
        raise PilotError("PILOT3_SOURCE_SELECTION_INPUT_MISSING")
    manifest = _load_json(manifest_path)
    selected = manifest.get("selected_source") or {}
    source_sha256 = sha256_file(source_path)
    if (
        manifest.get("document_type") != SOURCE_SELECTION_DOCUMENT_TYPE
        or manifest.get("pilot_run_id") != run_id
        or manifest.get("selection_frozen_before_semantic_extraction") is not True
        or manifest.get("source_replacement_after_freeze_allowed") is not False
        or manifest.get("eligible_candidate_count") != 1
        or selected.get("sha256") != source_sha256
        or Path(str(selected.get("path") or "")).resolve() != source_path
    ):
        raise PilotError("PILOT3_SOURCE_SELECTION_MANIFEST_INVALID")
    if source_sha256 in {PILOT1_SOURCE_SHA256, PILOT2_SOURCE_SHA256}:
        raise PilotError("PILOT3_SOURCE_NOT_INDEPENDENT")
    parsed = parse_source_with_diagnostics(source_path)
    diagnostics = parsed.diagnostics
    if (
        parsed.source_type != "pdf"
        or diagnostics.get("error_units") != 0
        or not diagnostics.get("text_units")
        or diagnostics.get("empty_extraction") is not False
    ):
        raise PilotError("PILOT3_SOURCE_PARSE_INADEQUATE")
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_file(manifest_path),
        "source_sha256": source_sha256,
        "parse_diagnostics": copy.deepcopy(diagnostics),
    }


def validate_preflight_receipt(
    receipt_path: Path,
    source_sha256: str,
    freeze: dict[str, Any],
) -> dict[str, Any]:
    receipt_path = Path(receipt_path).resolve()
    if not receipt_path.is_file():
        raise PilotError("PILOT3_PREFLIGHT_RECEIPT_MISSING")
    receipt = _load_json(receipt_path)
    if (
        receipt.get("document_type") != PREFLIGHT_DOCUMENT_TYPE
        or receipt.get("passed") is not True
        or receipt.get("source_sha256") != source_sha256
        or receipt.get("prompt_sha256") != freeze["prompt_sha256"]
        or receipt.get("code_file_sha256") != freeze["code_file_sha256"]
    ):
        raise PilotError("PILOT3_PREFLIGHT_RECEIPT_INVALID")
    checks = receipt.get("checks") or {}
    if not checks or any(value != "PASS" for value in checks.values()):
        raise PilotError("PILOT3_PREFLIGHT_FAILED")
    return receipt


def _target_result(numerator: int, denominator: int, *, at_least: float) -> dict[str, Any]:
    percent = 100 * numerator / denominator if denominator else 0.0
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(percent, 2),
        "threshold_percent": at_least,
        "passed": percent >= at_least,
    }


def _at_most_result(numerator: int, denominator: int, *, at_most: float) -> dict[str, Any]:
    percent = 100 * numerator / denominator if denominator else 0.0
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(percent, 2),
        "threshold_percent": at_most,
        "passed": percent <= at_most,
    }


def render_pilot3_review_surface(
    quote_artifact: dict[str, Any], evidence_draft: dict[str, Any],
) -> str:
    quote_by_id = {item["claim_id"]: item for item in quote_artifact.get("claims") or []}
    lines = [
        "# Phase 3C Pilot #3 Independent Human Review Surface",
        "",
        "This is a complete mechanics-only handoff. Semantic acceptance, KEEP/DROP, and atomicity decisions remain PENDING.",
        "",
        f"- pilot_run_id: `{quote_artifact['pilot_run_id']}`",
        f"- Source SHA-256: `{quote_artifact['source_sha256']}`",
        f"- Claims: {len(evidence_draft.get('claims') or [])}",
        "- Human semantic review executed: `NO`",
        "",
    ]
    for item in evidence_draft.get("claims") or []:
        quote = quote_by_id[item["claim_id"]]
        contract = quote.get("evidence_contract") or {}
        model_pointer = contract.get("model_page_pointer") or {}
        lines += [
            f"## {item['claim_id']}",
            "",
            f"- statement: {item.get('statement') or ''}",
            f"- attributed_to: {item.get('attributed_to') or ''}",
            f"- immutable model Evidence: {item.get('original_evidence_excerpt') or ''}",
            f"- quote fidelity status: `{quote.get('fidelity_status')}`",
            f"- authoritative deterministic locator: `{json.dumps(contract.get('resolved_locator'), ensure_ascii=False)}`",
            f"- model pointer / status: `{model_pointer.get('value') or ''}` / `{model_pointer.get('status') or ''}`",
            f"- bounded context candidates: `{json.dumps(item.get('bounded_context_candidates') or [], ensure_ascii=False)}`",
            f"- ordered spans: `{json.dumps(item.get('evidence_spans') or [], ensure_ascii=False)}`",
            f"- formal / model confidence: `{item.get('formal_confidence')}` / `{item.get('model_confidence')}`",
            "- Human decision: `PENDING`",
            "",
        ]
    lines += [
        "No automated semantic support, failure-rate, attribution-semantic, or atomicity verdict is included.",
        "",
    ]
    return "\n".join(lines)


def _render_pre_review_report(metrics: dict[str, Any]) -> str:
    parse = metrics["source"]["parse_diagnostics"]
    evidence = metrics["evidence_fidelity"]
    pointer = metrics["model_page_pointer"]
    locator = metrics["locator"]
    usage = metrics["model_usage"]
    production = metrics["production"]
    regressions = metrics["regression_validation"]
    lines = [
        "# Phase 3C Pilot #3 - Independent Generalization Pilot Pre-review Report",
        "",
        f"PHASE3C_PILOT3_EXTRACTION_COMPLETE = `{str(metrics['PHASE3C_PILOT3_EXTRACTION_COMPLETE']).lower()}`",
        "PHASE3C_COMPLETE = `false`",
        "",
        f"- Pilot #3 Source: `{metrics['source']['path']}`",
        f"- Pilot #3 Source SHA256: `{metrics['source']['sha256']}`",
        f"- Pilot #3 run ID: `{metrics['pilot_run_id']}`",
        f"- Independent from Pilot #1/#2 repair design: `{'PASS' if metrics['source']['independent'] else 'FAIL'}`",
        f"- Source selection frozen before semantic extraction: `{'PASS' if metrics['source_selection']['frozen_before_semantic_extraction'] else 'FAIL'}`",
        "",
        "## Frozen path",
        "",
        f"- Gate C repaired code active: `{'PASS' if metrics['freeze']['gate_c_repaired_code_active'] else 'FAIL'}`",
        f"- Prompt frozen: `{'PASS' if metrics['prompt_and_code_frozen'] else 'FAIL'}`",
        f"- Prompt SHA-256: `{metrics['freeze']['prompt_sha256']}`",
        f"- Configured / response model: `{metrics['configured_request_model']}` / `{metrics['response_model']}`",
        "",
        "## Source and extraction",
        "",
        f"- PDF pages / parsed units: {parse['total_units']} / {parse['text_units']}",
        f"- Parse errors / empty units / extracted chars: {parse['error_units']} / {parse['empty_units']} / {parse['extracted_chars']}",
        f"- Claims total: {metrics['claims_total']}",
        "",
        "## Evidence fidelity",
        "",
    ]
    lines += [
        f"- {name}: {evidence['counts'][name]}"
        for name in sorted(PILOT2_GATE_A_FIDELITY_STATUSES)
    ]
    lines += [
        f"- Evidence quote fidelity rate: {evidence['quote_fidelity_rate']['fraction']} ({evidence['quote_fidelity_rate']['percent']}%)",
        f"- Evidence quote drift rate: {evidence['quote_drift_rate']['fraction']} ({evidence['quote_drift_rate']['percent']}%)",
        f"- Model page pointer matched / errors / accuracy: {pointer['matched']} / {pointer['errors']} / {pointer['accuracy']['fraction']} ({pointer['accuracy']['percent']}%)",
        f"- Deterministic locator recovery: {pointer['recovery']['fraction']} ({pointer['recovery']['percent']}%)",
        f"- Deterministic source binding rate: {locator['source_binding_rate']['fraction']} ({locator['source_binding_rate']['percent']}%)",
        f"- Single-page / cross-page / ambiguous / unresolved: {locator['single_page']} / {locator['cross_page']} / {locator['ambiguous']} / {locator['unresolved']}",
        f"- Bounded-context candidates: {locator['bounded_context_candidates']}",
        "",
        "## Hard and mechanical gates",
        "",
        f"- Known deterministic company-to-speaker recurrence: `{metrics['attribution_mechanical_qa']['known_old_mutation_recurrence']}` (0 expected)",
        f"- Quote fidelity >= 85%: `{'PASS' if metrics['mechanical_targets']['quote_fidelity']['passed'] else 'FAIL'}`",
        f"- Quote drift <= 15%: `{'PASS' if metrics['mechanical_targets']['quote_drift']['passed'] else 'FAIL'}`",
        f"- Source binding >= 85%: `{'PASS' if metrics['mechanical_targets']['source_binding']['passed'] else 'FAIL'}`",
        "",
        "## Human decisions and usage",
        "",
        f"- Human decisions PENDING: {metrics['human_decisions']['PENDING']}",
        "- Human semantic review executed: `NO`",
        "- Semantic support / true failure / atomicity: `PENDING_HUMAN_REVIEW`",
        f"- Logical extractions / LLM calls: {usage['logical_extractions']} / {usage['llm_calls']}",
        f"- Prompt / completion / total tokens: {usage['prompt_tokens']} / {usage['completion_tokens']} / {usage['total_tokens']}",
        f"- Tokens per Claim / bound Claim: {usage['tokens_per_claim']} / {usage['tokens_per_bound_claim']}",
        "",
        "## Production isolation and regressions",
        "",
        f"- Production SHA: `{production['pre']['sha256']}` -> `{production['post']['sha256']}`",
        f"- Production changed / table counts changed: `{'YES' if not production['unchanged'] else 'NO'}` / `{'YES' if production['table_counts_changed'] else 'NO'}`",
        f"- Integrity / FK violations: `{production['post']['integrity_check']}` / `{len(production['post']['foreign_key_violations'])}`",
        "- IMA / propagation / legacy pipeline invoked: `NO / NO / NO`",
    ]
    lines += [f"- {name}: `{regressions.get(name, 'PENDING')}`" for name in REQUIRED_REGRESSIONS]
    lines += [
        "",
        f"PHASE3C_NEXT_GATE = `{metrics['PHASE3C_NEXT_GATE']}`",
        "",
        "STOP: no Human KEEP/DROP review, prompt change, quality rerun, canonical migration, or Production write was performed.",
        "",
    ]
    return "\n".join(lines)


def run_pilot3_independent_extraction(
    source_path: Path,
    manifest_path: Path,
    preflight_receipt_path: Path,
    run_id: str,
    cfg: AppConfig,
    *,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Run the single authorized Pilot #3 extraction and deterministic mechanical QA."""
    source_path = Path(source_path).resolve()
    manifest_path = Path(manifest_path).resolve()
    preflight_receipt_path = Path(preflight_receipt_path).resolve()
    production_db = Path(production_db_path or cfg.db_path).resolve()
    run_dir = (cfg.root / "phase3c" / run_id).resolve()
    if not cfg.llm.enabled or not cfg.llm.api_key:
        raise PilotError("PILOT3_LLM_NOT_AVAILABLE")
    selection = validate_source_selection_manifest(manifest_path, source_path, run_id)
    freeze_pre = pilot3_freeze(cfg)
    preflight = validate_preflight_receipt(
        preflight_receipt_path, selection["source_sha256"], freeze_pre,
    )
    production_pre = production_snapshot(production_db)
    if production_pre["sha256"] != PRODUCTION_BASELINE_SHA256:
        raise PilotError("PILOT3_PRODUCTION_BASELINE_MISMATCH")
    forbidden_outputs = (
        "extraction_bundle.json", "production_copy.db", "pilot3_pre_review_metrics.json",
    )
    if any((run_dir / name).exists() for name in forbidden_outputs):
        raise PilotError("PILOT3_LOGICAL_EXTRACTION_ALREADY_STARTED")
    freeze_artifact = {
        "document_type": "phase3c_pilot3_extraction_freeze",
        "schema_version": "1",
        "pilot_run_id": run_id,
        "source": {
            "path": str(source_path),
            "sha256": selection["source_sha256"],
            "parse_diagnostics": selection["parse_diagnostics"],
        },
        "source_selection_manifest_sha256": selection["manifest_sha256"],
        "preflight_receipt_sha256": sha256_file(preflight_receipt_path),
        "freeze": freeze_pre,
        "production_pre": production_pre,
        "one_logical_real_extraction_authorized": True,
        "quality_based_rerun_forbidden": True,
    }
    freeze_path = run_dir / "pilot3_extraction_freeze.json"
    write_json(freeze_path, freeze_artifact)

    extraction = extract_pilot_source(
        source_path,
        cfg,
        output_dir=run_dir,
        production_db_path=production_db,
        required_prompt_sha256=freeze_pre["prompt_sha256"],
        run_id=run_id,
    )
    rebound = rebind_stage1_evidence_locators(
        Path(extraction["extraction_bundle_path"]),
        source_path,
        output_dir=run_dir,
        production_db_path=production_db,
    )
    evidence = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]),
        Path(rebound["review_draft_path"]),
        source_path,
        output_dir=run_dir,
        production_db_path=production_db,
    )
    gate_a = run_pilot2_gate_a_quote_fidelity(
        Path(extraction["extraction_bundle_path"]),
        Path(rebound["rebound_bundle_path"]),
        Path(evidence["draft_path"]),
        source_path,
        output_dir=run_dir,
        production_db_path=production_db,
        original_review_path=Path(extraction["review_draft_path"]),
    )
    diagnostics = _controlled_reextraction_mechanical_diagnostics(
        extraction["bundle"], gate_a, evidence["draft"],
    )
    quote_artifact = copy.deepcopy(gate_a)
    quote_artifact["document_type"] = "phase3c_pilot3_quote_fidelity"
    quote_artifact["stage"] = "INDEPENDENT_GENERALIZATION_PRE_HUMAN_REVIEW"
    quote_path = run_dir / "pilot3_quote_fidelity.json"
    write_json(quote_path, quote_artifact)

    review_surface_path = run_dir / "evidence_review_surface.md"
    review_surface_path.write_text(
        render_pilot3_review_surface(quote_artifact, evidence["draft"]), encoding="utf-8",
    )
    freeze_post = pilot3_freeze(cfg)
    production_post = production_snapshot(production_db)
    prompt_and_code_frozen = freeze_pre == freeze_post
    production_unchanged = production_pre == production_post
    claims_total = len(extraction["bundle"].get("claims") or [])
    fidelity_counts = gate_a["metrics"]["fidelity_counts"]
    faithful = sum(
        fidelity_counts[name]
        for name in (
            "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
            "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
        )
    )
    drift = fidelity_counts["QUOTE_DRIFT"]
    evidence_metrics = evidence["metrics"]
    monitoring = gate_a["metrics"]["monitoring_contract"]
    bound = evidence_metrics["evidence_deterministically_bound"]
    mutation_count = diagnostics["deterministic_company_to_speaker_mutations"]["count"]
    hard_complete = bool(
        prompt_and_code_frozen
        and production_unchanged
        and mutation_count == 0
        and gate_a["metrics"]["invariants"]["all_claims_classified"]
        and all(item.get("human_decision") == "PENDING" for item in evidence["draft"]["claims"])
        and all(item.get("decision") == "PENDING" for item in extraction["review"]["claims"])
    )
    model = extraction["bundle"]["model"]
    usage = model.get("usage") or {}
    metrics = {
        "document_type": METRICS_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "PASS" if hard_complete else "FAIL",
        "PHASE3C_PILOT3_EXTRACTION_COMPLETE": hard_complete,
        "PHASE3C_COMPLETE": False,
        "pilot_run_id": run_id,
        "source": {
            "path": str(source_path),
            "name": source_path.name,
            "sha256": selection["source_sha256"],
            "independent": selection["source_sha256"] not in {
                PILOT1_SOURCE_SHA256, PILOT2_SOURCE_SHA256,
            },
            "parse_diagnostics": selection["parse_diagnostics"],
        },
        "source_selection": {
            "pre_designated_candidate": selection["manifest"].get("pre_designated_candidate"),
            "eligible_candidate_count": selection["manifest"].get("eligible_candidate_count"),
            "selection_rule": selection["manifest"].get("selection_rule"),
            "frozen_before_semantic_extraction": True,
            "manifest_path": str(manifest_path),
            "manifest_sha256": selection["manifest_sha256"],
        },
        "freeze": freeze_pre,
        "prompt_and_code_frozen": prompt_and_code_frozen,
        "configured_request_model": model.get("configured_model"),
        "response_model": model.get("response_model"),
        "claims_total": claims_total,
        "evidence_fidelity": {
            "counts": copy.deepcopy(fidelity_counts),
            "quote_fidelity_rate": _target_result(faithful, claims_total, at_least=85.0),
            "quote_drift_rate": _at_most_result(drift, claims_total, at_most=15.0),
        },
        "model_page_pointer": {
            "matched": monitoring["model_pointer_matched_claims"],
            "errors": monitoring["model_page_pointer_error_claims"],
            "accuracy": copy.deepcopy(monitoring["model_page_pointer_accuracy"]),
            "recovery": copy.deepcopy(monitoring["deterministic_locator_recovery_rate"]),
        },
        "locator": {
            "single_page": evidence_metrics["single_page_locator_bound"],
            "cross_page": evidence_metrics["cross_page_exact_spans"],
            "ambiguous": evidence_metrics["locator_ambiguous"],
            "unresolved": evidence_metrics["locator_unresolved"],
            "bounded_context_candidates": evidence_metrics["bounded_context_candidate_claims"],
            "source_binding_rate": _target_result(bound, claims_total, at_least=85.0),
        },
        "mechanical_targets": {
            "quote_fidelity": _target_result(faithful, claims_total, at_least=85.0),
            "quote_drift": _at_most_result(drift, claims_total, at_most=15.0),
            "source_binding": _target_result(bound, claims_total, at_least=85.0),
        },
        "attribution_mechanical_qa": diagnostics[
            "deterministic_company_to_speaker_mutations"
        ] | {"known_old_mutation_recurrence": diagnostics["known_old_mutation_recurrence"]},
        "diagnostic_only_flags": {
            key: copy.deepcopy(value)
            for key, value in diagnostics.items()
            if key not in {
                "deterministic_company_to_speaker_mutations", "known_old_mutation_recurrence",
            }
        },
        "human_decisions": {"KEEP": 0, "DROP": 0, "KEEP_NEEDS_REVIEW": 0, "PENDING": claims_total},
        "human_semantic_review_executed": False,
        "semantic_metrics": {
            "semantic_support_rate": "PENDING_HUMAN_REVIEW",
            "true_semantic_failure_rate": "PENDING_HUMAN_REVIEW",
            "atomicity_issue_rate": "PENDING_HUMAN_REVIEW",
        },
        "model_usage": {
            "logical_extractions": 1,
            "llm_calls": model.get("llm_calls", "NOT_AVAILABLE"),
            "prompt_tokens": usage.get("prompt_tokens", "NOT_AVAILABLE"),
            "completion_tokens": usage.get("completion_tokens", "NOT_AVAILABLE"),
            "total_tokens": usage.get("total_tokens", "NOT_AVAILABLE"),
            "tokens_per_claim": evidence_metrics["tokens_per_claim"],
            "tokens_per_bound_claim": evidence_metrics[
                "tokens_per_deterministically_bound_claim"
            ],
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
        },
        "preflight_receipt": preflight,
        "regression_validation": {name: "PENDING" for name in REQUIRED_REGRESSIONS},
        "one_logical_real_extraction": True,
        "quality_based_rerun": False,
        "artifacts": {
            "source_selection_manifest": str(manifest_path),
            "extraction_freeze": str(freeze_path),
            "extraction_bundle": extraction["extraction_bundle_path"],
            "extraction_review_draft": extraction["review_draft_path"],
            "evidence_contract_v2_draft": evidence["draft_path"],
            "evidence_review_surface": str(review_surface_path),
            "quote_fidelity": str(quote_path),
            "pre_review_metrics": str(run_dir / "pilot3_pre_review_metrics.json"),
            "pre_review_report": str(run_dir / "pilot3_pre_review_report.md"),
        },
        "PHASE3C_NEXT_GATE": (
            "Pilot #3 Independent Human Review"
            if hard_complete
            else "Resolve Pilot #3 Hard Extraction Gate Failure"
        ),
    }
    metrics_path = run_dir / "pilot3_pre_review_metrics.json"
    report_path = run_dir / "pilot3_pre_review_report.md"
    write_json(metrics_path, metrics)
    report_path.write_text(_render_pre_review_report(metrics), encoding="utf-8")
    if not hard_complete:
        raise PilotError("PILOT3_EXTRACTION_GATE_FAILED")
    return {
        "status": "PASS",
        "pilot_run_id": run_id,
        "metrics": metrics,
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "quote_path": str(quote_path),
        "review_surface_path": str(review_surface_path),
    }


def finalize_pilot3_artifacts(
    run_dir: Path,
    regression_receipt_path: Path,
    cfg: AppConfig,
    *,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Attach post-run regressions and the final Production/freeze verification."""
    run_dir = Path(run_dir).resolve()
    receipt = _load_json(Path(regression_receipt_path).resolve())
    metrics_path = run_dir / "pilot3_pre_review_metrics.json"
    report_path = run_dir / "pilot3_pre_review_report.md"
    metrics = _load_json(metrics_path)
    if (
        receipt.get("document_type") != REGRESSION_DOCUMENT_TYPE
        or receipt.get("pilot_run_id") != metrics.get("pilot_run_id")
    ):
        raise PilotError("PILOT3_REGRESSION_RECEIPT_INVALID")
    results = receipt.get("results") or {}
    if set(results) != set(REQUIRED_REGRESSIONS):
        raise PilotError("PILOT3_REGRESSION_COVERAGE_INVALID")
    metrics["regression_validation"] = copy.deepcopy(results)
    freeze_post = pilot3_freeze(cfg)
    metrics["prompt_and_code_frozen"] = freeze_post == metrics["freeze"]
    production_post = production_snapshot(Path(production_db_path or cfg.db_path).resolve())
    production_pre = metrics["production"]["pre"]
    production_unchanged = production_pre == production_post
    metrics["production"]["post"] = production_post
    metrics["production"]["unchanged"] = production_unchanged
    metrics["production"]["table_counts_changed"] = (
        production_pre["table_counts"] != production_post["table_counts"]
    )
    all_regressions_pass = all(value == "PASS" for value in results.values())
    complete = bool(
        metrics.get("PHASE3C_PILOT3_EXTRACTION_COMPLETE")
        and all_regressions_pass
        and metrics["prompt_and_code_frozen"]
        and production_unchanged
    )
    metrics["status"] = "PASS" if complete else "FAIL"
    metrics["PHASE3C_PILOT3_EXTRACTION_COMPLETE"] = complete
    metrics["PHASE3C_NEXT_GATE"] = (
        "Pilot #3 Independent Human Review"
        if complete
        else "Resolve Pilot #3 Post-extraction Validation Failure"
    )
    metrics["regression_receipt"] = {
        "path": str(Path(regression_receipt_path).resolve()),
        "sha256": sha256_file(Path(regression_receipt_path).resolve()),
    }
    write_json(metrics_path, metrics)
    report_path.write_text(_render_pre_review_report(metrics), encoding="utf-8")
    if not complete:
        raise PilotError("PILOT3_POST_EXTRACTION_VALIDATION_FAILED")
    return {
        "status": "PASS",
        "metrics": metrics,
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
    }
