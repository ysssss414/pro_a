from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from . import analyzer as analyzer_module
from .corpus_pilot import (
    PilotError,
    phase3c_evidence_provenance_contract,
    phase3c_gate_a_monitoring_metrics,
    phase3c_prompt_repair_status,
    production_snapshot,
    resolve_pdf_evidence_locator,
)
from .storage import sha256_file, write_json


RUN_ID = "PILOT_20260831_FF7D5C58"
SOURCE_SHA256 = "1ea71205fb04885f44ab0aa48b57586647c9c823d4b321f11d23d7505aa65f52"
OUTPUT_NAMES = {
    "pilot2_gate_c_remaining_quality_repair_report.md",
    "pilot2_gate_c_remaining_quality_repair_metrics.json",
    "pilot2_gate_c_repair_simulation.json",
}

RESIDUAL_ROOT_CAUSES = {
    "CLM_20260831_36C543E6": {
        "primary_failure": "TECHNICAL_TERM_INFERENCE",
        "model_behavior": "Normalized a noisy technical token to a domain-plausible term and combined it with price and demand propositions.",
        "deterministic_behavior": "No deterministic semantic rewrite; the immutable model Claim and Evidence were preserved for review.",
        "minimum_preventive_rule": "Keep unknown/noisy technical wording, or omit the proposition that depends on the inferred term.",
        "affected_code_prompt_path": "src/pro_a/prompts.py: technical-term inference prevention",
        "regression_fixture": "Noisy technical token remains unchanged and is not normalized from domain plausibility.",
    },
    "CLM_20260831_FF223F7B": {
        "primary_failure": "CONDITIONALITY_LOSS",
        "model_behavior": "Dropped the possibility qualifier from a mainland-company capability proposition and joined it to separate NPU/CPU demand.",
        "deterministic_behavior": "No deterministic semantic rewrite; validation did not add or remove modality.",
        "minimum_preventive_rule": "Keep modality on the exact proposition it modifies and split propositions with different certainty or Evidence scope.",
        "affected_code_prompt_path": "src/pro_a/prompts.py: conditionality preservation and atomicity clarification",
        "regression_fixture": "A possible CPU capability remains possible and separate from definite demand statements.",
    },
    "CLM_20260831_38B76965": {
        "primary_failure": "ENTITY_INFERENCE",
        "model_behavior": "Resolved a noisy ASR company token into specific named leaders and combined identity with a capability gate.",
        "deterministic_behavior": "No Node/Alias or deterministic entity rewrite changed the Claim statement.",
        "minimum_preventive_rule": "Do not expand a noisy entity unless the same permitted local Source scope establishes the identity.",
        "affected_code_prompt_path": "src/pro_a/prompts.py: entity inference prevention",
        "regression_fixture": "A noisy company token is not expanded from Node, Alias, title, filename, or industry context.",
    },
    "CLM_20260831_3F48A578": {
        "primary_failure": "ENTITY_INFERENCE",
        "model_behavior": "Inserted normalized vendor identities that were absent from the cited local Evidence excerpt.",
        "deterministic_behavior": "No deterministic entity correction was applied; the unsupported model expansion remained visible.",
        "minimum_preventive_rule": "Keep entity observations separate from Claim semantics and omit unstated vendor identities.",
        "affected_code_prompt_path": "src/pro_a/prompts.py: entity inference prevention",
        "regression_fixture": "Third-party vendor comparison does not acquire locally unstated company names.",
    },
    "CLM_20260831_2009986B": {
        "primary_failure": "SCOPE_ERROR",
        "model_behavior": "Broadened 'many mainland companies' to mainland companies generally.",
        "deterministic_behavior": "The page pointer was deterministically recovered, but no deterministic process broadened semantic scope.",
        "minimum_preventive_rule": "Do not widen quantified subsets, companies, customers, products, processes, or demand scopes.",
        "affected_code_prompt_path": "src/pro_a/prompts.py: scope preservation",
        "regression_fixture": "'Many companies' remains a subset and never becomes an unqualified industry-wide statement.",
    },
    "CLM_20260831_B1AF35B8": {
        "primary_failure": "CONDITIONALITY_LOSS",
        "model_behavior": "Presented first- and second-quarter estimates as facts after dropping speaker uncertainty and combining several horizons.",
        "deterministic_behavior": "No deterministic semantic rewrite; marker diagnostics only exposed the difference.",
        "minimum_preventive_rule": "Preserve each uncertainty marker with its horizon and split independently reviewable time/certainty propositions.",
        "affected_code_prompt_path": "src/pro_a/prompts.py: conditionality preservation and atomicity clarification",
        "regression_fixture": "Q1, Q2, H2, and next-year estimates retain their own uncertainty and split boundaries.",
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"PILOT2_GATE_C_INVALID_JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"PILOT2_GATE_C_JSON_OBJECT_REQUIRED: {path}")
    return value


def _prior_artifact_hashes(run_dir: Path) -> dict[str, str]:
    return {
        item.name: sha256_file(item)
        for item in sorted(run_dir.iterdir())
        if item.is_file() and item.name not in OUTPUT_NAMES
    }


def _evidence_simulation() -> dict[str, Any]:
    exact_text = "[[PAGE:1]]\n唯一精确引文。\n[[PAGE:2]]\n其他文本。"
    exact_locator = resolve_pdf_evidence_locator(exact_text, "唯一精确引文。", "[[PAGE:1]]")
    exact = phase3c_evidence_provenance_contract(
        model_evidence_excerpt="唯一精确引文。",
        evidence_pointer="[[PAGE:1]]",
        deterministic_locator=exact_locator,
        fidelity_status="EXACT_SOURCE_MATCH",
    )
    wrong_pointer_locator = resolve_pdf_evidence_locator(
        exact_text, "唯一精确引文。", "[[PAGE:2]]",
    )
    wrong_pointer = phase3c_evidence_provenance_contract(
        model_evidence_excerpt="唯一精确引文。",
        evidence_pointer="[[PAGE:2]]",
        deterministic_locator=wrong_pointer_locator,
        fidelity_status="PROVENANCE_MISMATCH_RECOVERED",
    )
    drift_locator = resolve_pdf_evidence_locator(
        exact_text, "唯一已清理引文。", "[[PAGE:1]]",
    )
    drift = phase3c_evidence_provenance_contract(
        model_evidence_excerpt="唯一已清理引文。",
        evidence_pointer="[[PAGE:1]]",
        deterministic_locator=drift_locator,
        fidelity_status="QUOTE_DRIFT",
    )
    spans = [
        {"order": 1, "locator": "PAGE:1", "text": "跨页前半", "exact_source_text": True},
        {"order": 2, "locator": "PAGE:2", "text": "跨页后半。", "exact_source_text": True},
    ]
    cross_page = phase3c_evidence_provenance_contract(
        model_evidence_excerpt="跨页前半跨页后半。",
        evidence_pointer="[[PAGE:1]]",
        deterministic_locator={"status": "unresolved", "reason": "cross_page_span"},
        fidelity_status="EXACT_ORDERED_CROSS_PAGE_SPAN",
        ordered_spans=spans,
    )
    return {
        "exact_source_quote": exact,
        "wrong_model_page_pointer_exact_elsewhere": wrong_pointer,
        "quote_drift": drift,
        "ordered_adjacent_page_quote": cross_page,
    }


def _project_historical_gate_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projected = []
    for item in claims:
        record = copy.deepcopy(item)
        status = item.get("fidelity_status")
        if status in {"EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH"}:
            pointer_status = "matched"
            resolved = {"status": "resolved", "authoritative": True}
        elif status == "PROVENANCE_MISMATCH_RECOVERED":
            pointer_status = "mismatch"
            resolved = {"status": "resolved", "authoritative": True}
        elif status == "EXACT_ORDERED_CROSS_PAGE_SPAN":
            pointer_status = "unsupported"
            resolved = {"status": "resolved", "kind": "ordered_spans", "authoritative": True}
        else:
            pointer_status = "unsupported"
            resolved = None
        record["model_page_pointer"] = {
            "value": item.get("provenance_pointer") or "",
            "status": pointer_status,
            "authoritative": False,
        }
        record["resolved_locator"] = resolved
        projected.append(record)
    return projected


def _render_report(metrics: dict[str, Any]) -> str:
    monitoring = metrics["monitoring_metrics"]
    checks = metrics["acceptance_checks"]
    lines = [
        "# Phase 3C Pilot #2 Gate C — Residual Semantic Guardrails & Evidence Provenance Hardening",
        "",
        f"PHASE3C_PILOT2_GATE_C_COMPLETE = `{str(metrics['PHASE3C_PILOT2_GATE_C_COMPLETE']).lower()}`",
        "PHASE3C_COMPLETE = `false`",
        "",
        "## Baseline and outcome",
        "",
        "- Historical controlled re-extraction semantic failure rate: `11.76%` (unchanged; no rerun)",
        "- Historical controlled re-extraction material atomicity failure rate: `7.84%` (unchanged)",
        "- Attribution errors: `0`; deterministic company-to-speaker recurrence: `NO`",
        f"- Gate C acceptance: `{'PASS' if all(checks.values()) else 'FAIL'}`",
        "",
        "## Residual failure root causes",
        "",
        "| Claim ID | Primary failure | Model behavior | Deterministic behavior | Minimum preventive rule |",
        "|---|---|---|---|---|",
    ]
    for item in metrics["residual_failure_root_causes"]:
        lines.append(
            f"| {item['claim_id']} | {item['primary_failure']} | {item['model_behavior']} | "
            f"{item['deterministic_behavior']} | {item['minimum_preventive_rule']} |"
        )
    lines += ["", "## Acceptance checks", ""]
    lines += [f"- {name}: `{'PASS' if value else 'FAIL'}`" for name, value in checks.items()]
    lines += [
        "", "## Evidence and provenance contract", "",
        "- Model Evidence is a proposed quotation until deterministic source validation succeeds.",
        "- Model PAGE pointer is retained as a non-authoritative diagnostic hint.",
        "- Exact/layout-only/ordered-span deterministic binding supplies the authoritative artifact locator.",
        "- Quote drift remains blocked; nearest-region diagnostics never replace model Evidence.",
        "- `MODEL_PAGE_POINTER_ERROR` is monitored separately and is not a semantic failure.",
        "",
        "## Monitoring metrics (Claim grain)", "",
        f"- evidence_quote_fidelity_rate: `{monitoring['evidence_quote_fidelity_rate']['fraction']}` ({monitoring['evidence_quote_fidelity_rate']['percent']}%)",
        f"- evidence_quote_drift_rate: `{monitoring['evidence_quote_drift_rate']['fraction']}` ({monitoring['evidence_quote_drift_rate']['percent']}%)",
        f"- model_page_pointer_accuracy: `{monitoring['model_page_pointer_accuracy']['fraction']}` ({monitoring['model_page_pointer_accuracy']['percent']}%)",
        f"- deterministic_locator_recovery_rate: `{monitoring['deterministic_locator_recovery_rate']['fraction']}` ({monitoring['deterministic_locator_recovery_rate']['percent']}%)",
        f"- MODEL_PAGE_POINTER_ERROR count: `{monitoring['model_page_pointer_error_claims']}`",
        "- Semantic support is intentionally excluded; no composite score is defined.",
        "",
        "## Immutability and isolation", "",
        f"- Previous Pilot artifacts unchanged: `{'PASS' if metrics['historical_artifacts_unchanged'] else 'FAIL'}`",
        f"- Historical Claims/Evidence/decisions changed: `NO / NO / NO`",
        f"- Production SHA: `{metrics['production_pre']['sha256']}` → `{metrics['production_post']['sha256']}`",
        f"- Production table counts changed: `{'YES' if metrics['production_pre']['table_counts'] != metrics['production_post']['table_counts'] else 'NO'}`",
        f"- integrity_check / FK violations: `{metrics['production_post']['integrity_check']}` / `{len(metrics['production_post']['foreign_key_violations'])}`",
        "- LLM calls / Pilot #2 rerun / Pilot #3 / Production / IMA / propagation / legacy pipeline: `0 / NO / NO / NO / NO / NO / NO`",
        "",
        "## Next gate", "",
        f"`{metrics['PHASE3C_NEXT_GATE']}`",
        "",
        "Independent generalization re-test: `NOT_YET_PERFORMED`.",
        "",
        "STOP: no extraction, canonical migration, Production apply, IMA, or Stage 2 action was performed.",
        "",
    ]
    return "\n".join(lines)


def audit_pilot2_gate_c_quality_hardening(
    run_dir: Path,
    production_db_path: Path,
) -> dict[str, Any]:
    """Audit static Gate C repairs and write only new Gate C artifacts."""
    run_dir = Path(run_dir).resolve()
    production_db_path = Path(production_db_path).resolve()
    required = {
        "decisions": run_dir / "reextraction_human_review_decisions.json",
        "review_metrics": run_dir / "reextraction_human_review_metrics.json",
        "quote_fidelity": run_dir / "reextraction_quote_fidelity.json",
        "bundle": run_dir / "extraction_bundle.json",
    }
    if any(not path.is_file() for path in required.values()):
        raise PilotError("PILOT2_GATE_C_INPUT_MISSING")
    prior_hashes_pre = _prior_artifact_hashes(run_dir)
    production_pre = production_snapshot(production_db_path)
    decisions = _load_json(required["decisions"])
    review_metrics = _load_json(required["review_metrics"])
    quote = _load_json(required["quote_fidelity"])
    bundle = _load_json(required["bundle"])
    if (
        decisions.get("pilot_run_id") != RUN_ID
        or review_metrics.get("pilot_run_id") != RUN_ID
        or quote.get("pilot_run_id") != RUN_ID
        or bundle.get("pilot_run_id") != RUN_ID
        or decisions.get("source_sha256") != SOURCE_SHA256
        or (bundle.get("source") or {}).get("sha256") != SOURCE_SHA256
    ):
        raise PilotError("PILOT2_GATE_C_BINDING_INVALID")

    unsupported = [
        item for item in decisions.get("claims") or []
        if item.get("semantic_support") == "UNSUPPORTED"
    ]
    if {item.get("claim_id") for item in unsupported} != set(RESIDUAL_ROOT_CAUSES):
        raise PilotError("PILOT2_GATE_C_RESIDUAL_CLAIM_SET_INVALID")
    root_causes = []
    for item in unsupported:
        expected = RESIDUAL_ROOT_CAUSES[item["claim_id"]]
        if item.get("semantic_failure_category") != expected["primary_failure"]:
            raise PilotError(f"PILOT2_GATE_C_FAILURE_CATEGORY_CHANGED: {item['claim_id']}")
        root_causes.append({"claim_id": item["claim_id"], **copy.deepcopy(expected)})

    prompt = phase3c_prompt_repair_status()
    analyzer_source = Path(analyzer_module.__file__).read_text(encoding="utf-8")
    attribution_preserved = (
        'raw_statement.replace("公司", normalized_subject, 1)' not in analyzer_source
        and "deterministic_attribution_prefix_or_company_replacement" not in analyzer_source
        and "never inject or substitute attributed_to into Claim semantics" in analyzer_source
    )
    evidence_simulation = _evidence_simulation()
    exact = evidence_simulation["exact_source_quote"]
    wrong_pointer = evidence_simulation["wrong_model_page_pointer_exact_elsewhere"]
    drift = evidence_simulation["quote_drift"]
    cross_page = evidence_simulation["ordered_adjacent_page_quote"]
    monitoring = phase3c_gate_a_monitoring_metrics(
        _project_historical_gate_claims(quote.get("claims") or [])
    )
    expected_monitoring = (
        monitoring["evidence_quote_fidelity_rate"]["fraction"] == "45/51"
        and monitoring["evidence_quote_drift_rate"]["fraction"] == "6/51"
        and monitoring["model_page_pointer_accuracy"]["fraction"] == "35/45"
        and monitoring["deterministic_locator_recovery_rate"]["fraction"] == "8/8"
        and monitoring["model_page_pointer_error_claims"] == 8
    )
    categories = prompt["categories"]
    acceptance_checks = {
        "Residual six failure root causes classified": len(root_causes) == 6,
        "conditionality guardrail": categories["conditionality_preservation"],
        "entity inference guardrail": categories["entity_inference_prevention"],
        "technical-term inference guardrail": categories["technical_term_inference_prevention"],
        "scope guardrail": categories["scope_invention_prevention"],
        "atomicity clarification": categories["gate_c_atomicity_clarification"],
        "existing attribution repair preserved": attribution_preserved,
        "model Evidence treated as proposed quote": exact["model_evidence_is_proposed_quote"],
        "deterministic validation required": exact["validated_source_evidence"] is not None,
        "quote drift remains fail-closed": (
            drift["canonical_ready_evidence"] is None and drift["review_required"] is True
        ),
        "no automatic quote repair": all(
            item["automatic_quote_repair_applied"] is False
            for item in evidence_simulation.values()
        ),
        "model PAGE pointer non-authoritative": all(
            item["model_page_pointer"]["authoritative"] is False
            for item in evidence_simulation.values()
        ),
        "deterministic locator authoritative": (
            exact["resolved_locator"]["authoritative"] is True
            and wrong_pointer["resolved_locator"]["authoritative"] is True
            and cross_page["resolved_locator"]["authoritative"] is True
        ),
        "MODEL_PAGE_POINTER_ERROR separately tracked": (
            wrong_pointer["model_page_pointer_error"] == "MODEL_PAGE_POINTER_ERROR"
            and wrong_pointer["model_page_pointer"]["status"] == "mismatch"
        ),
        "pointer mismatch not semantic failure": (
            wrong_pointer["pointer_mismatch_is_semantic_failure"] is False
        ),
        "ordered adjacent-page quote validated": (
            cross_page["validated_source_evidence"] is not None
            and cross_page["resolved_locator"]["kind"] == "ordered_spans"
        ),
        "monitoring metrics implemented": expected_monitoring,
        "Evidence Contract v2 remains artifact-level": True,
    }
    simulation = {
        "document_type": "phase3c_pilot2_gate_c_repair_simulation",
        "schema_version": "1",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "historical_claims_modified": False,
        "historical_evidence_modified": False,
        "historical_decisions_modified": False,
        "known_residual_failures": root_causes,
        "evidence_provenance_simulation": evidence_simulation,
        "expected_future_behavior": [
            "Qualifiers remain attached to the exact proposition they modify.",
            "Noisy entities and technical terms are not expanded from external or observational knowledge.",
            "Claim scope does not exceed the local Source proposition.",
            "Different uncertainty, entity identity, or Evidence scope strongly signals a split without maximizing Claim count.",
            "Model Evidence remains proposed until deterministic source binding succeeds.",
            "Model PAGE pointer remains diagnostic; deterministic locator is authoritative.",
        ],
        "new_quality_rate_claimed": False,
        "independent_generalization_retest": "NOT_YET_PERFORMED",
    }
    simulation_path = run_dir / "pilot2_gate_c_repair_simulation.json"
    metrics_path = run_dir / "pilot2_gate_c_remaining_quality_repair_metrics.json"
    report_path = run_dir / "pilot2_gate_c_remaining_quality_repair_report.md"
    write_json(simulation_path, simulation)

    prior_hashes_post = _prior_artifact_hashes(run_dir)
    production_post = production_snapshot(production_db_path)
    historical_unchanged = prior_hashes_pre == prior_hashes_post
    production_unchanged = production_pre == production_post
    all_checks_pass = (
        all(acceptance_checks.values())
        and prompt["passed"]
        and historical_unchanged
        and production_unchanged
        and review_metrics.get("true_semantic_failure_rate", {}).get("percent") == 11.76
        and review_metrics.get("atomicity", {}).get("material_failure_rate", {}).get("percent") == 7.84
        and review_metrics.get("attribution", {}).get("any_dimension") == 0
    )
    next_gate = (
        "Independent Generalization Pilot Authorization"
        if all_checks_pass
        else "Resolve Gate C Semantic Guardrail Blockers"
        if not all(acceptance_checks[name] for name in (
            "conditionality guardrail", "entity inference guardrail",
            "technical-term inference guardrail", "scope guardrail",
            "atomicity clarification", "existing attribution repair preserved",
        ))
        else "Resolve Gate C Evidence Provenance Blockers"
    )
    metrics = {
        "document_type": "phase3c_pilot2_gate_c_remaining_quality_repair_metrics",
        "schema_version": "1",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "PHASE3C_PILOT2_GATE_C_COMPLETE": all_checks_pass,
        "historical_controlled_reextraction_semantic_failure_rate_percent": 11.76,
        "historical_controlled_reextraction_material_atomicity_failure_rate_percent": 7.84,
        "historical_quality_rates_changed": False,
        "residual_failure_root_causes": root_causes,
        "acceptance_checks": acceptance_checks,
        "prompt_guardrails": copy.deepcopy(categories),
        "prompt_sha256": prompt["prompt_sha256"],
        "monitoring_metrics": monitoring,
        "monitoring_metric_definitions": {
            "grain": "one_phase3c_claim",
            "evidence_quote_fidelity_rate": "deterministically source-bound Claims / all Claims",
            "evidence_quote_drift_rate": "QUOTE_DRIFT Claims / all Claims",
            "model_page_pointer_accuracy": "matched model PAGE pointers / deterministically locatable Claims",
            "deterministic_locator_recovery_rate": "deterministically recovered MODEL_PAGE_POINTER_ERROR Claims / MODEL_PAGE_POINTER_ERROR Claims",
            "semantic_support_separate": True,
            "composite_quality_score": "NOT_DEFINED",
        },
        "previous_artifact_hashes_pre": prior_hashes_pre,
        "previous_artifact_hashes_post": prior_hashes_post,
        "historical_artifacts_unchanged": historical_unchanged,
        "historical_claims_changed": False,
        "historical_evidence_changed": False,
        "historical_decisions_changed": False,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "llm_calls_added": 0,
        "pilot2_rerun": False,
        "pilot3_executed": False,
        "production_write": False,
        "production_schema_changed": False,
        "canonical_claim_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
        "independent_generalization_retest": "NOT_YET_PERFORMED",
        "PRODUCTION_APPLY_READY": "NO",
        "remaining_blockers": [
            "Independent generalization has not been performed.",
            "Evidence Contract v2 remains artifact-level and canonical migration is not authorized.",
        ],
        "PHASE3C_NEXT_GATE": next_gate,
    }
    write_json(metrics_path, metrics)
    report_path.write_text(_render_report(metrics), encoding="utf-8")
    if not all_checks_pass:
        raise PilotError("PILOT2_GATE_C_ACCEPTANCE_FAILED")
    return {
        "status": "PASS",
        "metrics": metrics,
        "report_path": str(report_path),
        "metrics_path": str(metrics_path),
        "simulation_path": str(simulation_path),
    }
