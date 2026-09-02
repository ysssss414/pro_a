from __future__ import annotations

import copy
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean, median
from typing import Any

from . import (
    analyzer as analyzer_module,
    corpus_pilot as corpus_pilot_module,
    llm as llm_module,
    parsers as parsers_module,
    pipeline as pipeline_module,
    prompts as prompts_module,
)
from .config import AppConfig
from .corpus_pilot import (
    PILOT2_GATE_A_FIDELITY_STATUSES,
    PilotError,
    build_pilot2_evidence_support_draft,
    extract_pilot_source,
    phase3c_prompt_repair_status,
    production_snapshot,
    rebind_stage1_evidence_locators,
    run_pilot2_gate_a_quote_fidelity,
)
from .ids import make_id
from .parsers import parse_source_with_diagnostics
from .pilot3 import render_pilot3_review_surface
from .storage import sha256_file, write_json


ORIGINAL_RUN_ID = "PILOT_20260831_7AD15F72"
ORIGINAL_SOURCE_SHA256 = "1daf977493798d0334dedcd685d8a10f7c39dd25d768a44fa8a99ddf761627be"
ORIGINAL_PROMPT_SHA256 = "fa075613b3616b36218c552cd0c29c18db255320cfda2be3835d8769ef5d16fe"
REPAIRED_PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"
REPAIRED_PROMPT_FILE_SHA256 = "4ac7a3ed099797920e57702fd3860f0ed98153fa272f112f2618e5e3fb6edce5"
PRODUCTION_BASELINE_SHA256 = "581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250"
REGRESSION_DOCUMENT_TYPE = "phase3c_pilot3_controlled_reextraction_regression_receipt"
METRICS_DOCUMENT_TYPE = "phase3c_pilot3_controlled_reextraction_metrics"
COMPARISON_DOCUMENT_TYPE = "phase3c_pilot3_controlled_reextraction_comparison"

REQUIRED_REGRESSIONS = (
    "preflight_freeze_validation",
    "targeted_stage_s2_tests",
    "semantic_repair_tests",
    "gate_c_attribution_tests",
    "phase3c_regressions",
    "full_pytest",
    "compileall",
)

SEMANTIC_CONTRACT_FRAGMENTS = {
    "source_local_resolution_only": "SOURCE-LOCAL RESOLUTION ONLY",
    "no_silent_technical_normalization": "不得依据领域知识静默纠正为已知术语",
    "core_unresolved_preserve_broader_or_omit": "则不输出该 Claim",
    "pronoun_unique_local_antecedent": "存在唯一明确先行词",
    "product_category_boundary": "产品类别边界",
    "relative_time_preservation": "相对时间必须忠于 Source",
    "conditionality_preservation": "条件能力写成当前已实现能力",
    "local_scope_preservation": "整个主题的普遍结论",
    "material_atomicity": "有支持的 A 与无支持的 B",
    "question_answer_boundary": "问句中的前提不等于回答者的陈述或判断",
    "gate_c_attribution": "归因只写入 attributed_to",
}

_EXPECTED_ORIGINAL_HASHES = {
    "original_extraction_bundle": "50ec4e09d68e3ea938307de215859fccac12e524c8687c9245052c2e266f2196",
    "original_repaired_evidence_v2": "a62d6298d9a798ee37e4f5e05114f26d1b10f5b90e2f54734b59553034b7d708",
    "original_human_review_decisions": "c60cbe85edf08310046f08db111d354585322b68ab8b348a0735fc53089d7f26",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"PILOT3_REEXTRACTION_JSON_INVALID: {path}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"PILOT3_REEXTRACTION_JSON_INVALID: {path}")
    return value


def _runtime_settings(cfg: AppConfig) -> dict[str, Any]:
    return {
        "analysis_mode": "deep",
        "configured_request_model": cfg.llm.model,
        "base_url": cfg.llm.base_url,
        "temperature": cfg.llm.temperature,
        "max_output_tokens": cfg.llm.max_output_tokens,
        "max_chunk_chars": cfg.llm.max_chunk_chars,
        "timeout_seconds": cfg.llm.timeout_seconds,
        "max_retries": cfg.llm.max_retries,
        "retry_backoff_seconds": cfg.llm.retry_backoff_seconds,
    }


def _runtime_file_snapshot() -> dict[str, str]:
    paths = {
        "src/pro_a/analyzer.py": Path(analyzer_module.__file__).resolve(),
        "src/pro_a/corpus_pilot.py": Path(corpus_pilot_module.__file__).resolve(),
        "src/pro_a/llm.py": Path(llm_module.__file__).resolve(),
        "src/pro_a/parsers.py": Path(parsers_module.__file__).resolve(),
        "src/pro_a/pipeline.py": Path(pipeline_module.__file__).resolve(),
        "src/pro_a/prompts.py": Path(prompts_module.__file__).resolve(),
        "src/pro_a/pilot3_controlled_reextraction.py": Path(__file__).resolve(),
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def _original_artifact_paths(root: Path) -> dict[str, Path]:
    original = root / "phase3c" / ORIGINAL_RUN_ID
    repair = root / "phase3c" / "pilot3_semantic_failure_repair"
    return {
        "original_extraction_bundle": original / "extraction_bundle.json",
        "original_repaired_evidence_v2": (
            original / "evidence_v2_repair" / "evidence_contract_v2_repaired.json"
        ),
        "original_human_review_decisions": original / "pilot3_human_review_decisions.json",
        "original_human_review_report": original / "pilot3_human_review_report.md",
        "stage_s1_repair_report": repair / "pilot3_semantic_failure_repair_report.md",
        "stage_s1_prompt_diff": repair / "pilot3_semantic_prompt_diff.md",
    }


def _snapshot_files(paths: dict[str, Path]) -> dict[str, dict[str, str]]:
    if any(not path.is_file() for path in paths.values()):
        missing = [name for name, path in paths.items() if not path.is_file()]
        raise PilotError(f"PILOT3_REEXTRACTION_FROZEN_ARTIFACT_MISSING: {','.join(missing)}")
    return {
        name: {"path": str(path.resolve()), "sha256": sha256_file(path)}
        for name, path in paths.items()
    }


def _assert_original_hashes(snapshot: dict[str, dict[str, str]]) -> None:
    mismatches = [
        name for name, expected in _EXPECTED_ORIGINAL_HASHES.items()
        if (snapshot.get(name) or {}).get("sha256") != expected
    ]
    if mismatches:
        raise PilotError(f"PILOT3_REEXTRACTION_ORIGINAL_ARTIFACT_MISMATCH: {','.join(mismatches)}")


def _ratio(numerator: int, denominator: int, threshold: float, *, at_least: bool) -> dict[str, Any]:
    percent = 100 * numerator / denominator if denominator else 0.0
    passed = percent >= threshold if at_least else percent <= threshold
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(percent, 2),
        "threshold_percent": threshold,
        "passed": passed,
    }


def controlled_reextraction_preflight(
    source_path: Path,
    cfg: AppConfig,
    run_id: str,
    *,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    production_db = Path(production_db_path or cfg.db_path).resolve()
    run_dir = (cfg.root / "phase3c" / run_id).resolve()
    if run_id == ORIGINAL_RUN_ID or not re.fullmatch(r"PILOT_\d{8}_[A-F0-9]{8}", run_id):
        raise PilotError("PILOT3_REEXTRACTION_RUN_ID_INVALID")
    if run_dir.exists():
        raise PilotError("PILOT3_REEXTRACTION_RUN_ALREADY_EXISTS")
    if not source_path.is_file() or sha256_file(source_path) != ORIGINAL_SOURCE_SHA256:
        raise PilotError("PILOT3_REEXTRACTION_SOURCE_FREEZE_MISMATCH")
    if not cfg.llm.enabled or not cfg.llm.api_key:
        raise PilotError("PILOT3_REEXTRACTION_LLM_NOT_AVAILABLE")

    prompt_status = phase3c_prompt_repair_status(prompts_module.SOURCE_ANALYSIS_SYSTEM)
    prompt_file_sha = sha256_file(Path(prompts_module.__file__).resolve())
    contract_checks = {
        name: fragment in prompts_module.SOURCE_ANALYSIS_SYSTEM
        for name, fragment in SEMANTIC_CONTRACT_FRAGMENTS.items()
    }
    if (
        not prompt_status["passed"]
        or prompt_status["prompt_sha256"] != REPAIRED_PROMPT_SHA256
        or prompt_file_sha != REPAIRED_PROMPT_FILE_SHA256
        or not all(contract_checks.values())
    ):
        raise PilotError("PILOT3_REEXTRACTION_PROMPT_FREEZE_MISMATCH")

    original_freeze_path = cfg.root / "phase3c" / ORIGINAL_RUN_ID / "pilot3_extraction_freeze.json"
    original_freeze = _load_json(original_freeze_path)
    frozen_settings = ((original_freeze.get("freeze") or {}).get("extraction_configuration") or {})
    runtime_settings = _runtime_settings(cfg)
    if runtime_settings != frozen_settings:
        raise PilotError("PILOT3_REEXTRACTION_RUNTIME_SETTINGS_MISMATCH")

    parsed = parse_source_with_diagnostics(source_path)
    original_source = original_freeze.get("source") or {}
    if (
        parsed.source_type != "pdf"
        or parsed.diagnostics != original_source.get("parse_diagnostics")
        or original_source.get("sha256") != ORIGINAL_SOURCE_SHA256
    ):
        raise PilotError("PILOT3_REEXTRACTION_SOURCE_PARSE_FREEZE_MISMATCH")

    original_paths = _original_artifact_paths(cfg.root)
    original_snapshot = _snapshot_files(original_paths)
    _assert_original_hashes(original_snapshot)
    decisions = _load_json(original_paths["original_human_review_decisions"])
    if decisions.get("PILOT3_GENERALIZATION_VERDICT") != "FAIL":
        raise PilotError("PILOT3_REEXTRACTION_ORIGINAL_VERDICT_MUTATED")
    production = production_snapshot(production_db)
    if production.get("sha256") != PRODUCTION_BASELINE_SHA256:
        raise PilotError("PILOT3_REEXTRACTION_PRODUCTION_BASELINE_MISMATCH")

    return {
        "document_type": "phase3c_pilot3_controlled_reextraction_preflight",
        "schema_version": "1",
        "status": "PASS",
        "pilot_run_id": run_id,
        "original_run_id": ORIGINAL_RUN_ID,
        "source": {
            "path": str(source_path),
            "sha256": ORIGINAL_SOURCE_SHA256,
            "parse_diagnostics": copy.deepcopy(parsed.diagnostics),
        },
        "prompt": {
            "old_prompt_sha256_not_used": ORIGINAL_PROMPT_SHA256,
            "prompt_sha256": prompt_status["prompt_sha256"],
            "prompt_file_sha256": prompt_file_sha,
            "contract_checks": contract_checks,
            "gate_c_contract_active": prompt_status["passed"],
        },
        "runtime_settings": runtime_settings,
        "runtime_semantic_settings_changed": False,
        "runtime_files": _runtime_file_snapshot(),
        "original_artifacts": original_snapshot,
        "original_generalization_verdict": "FAIL",
        "production_pre": production,
        "one_logical_extraction_authorized": True,
        "quality_rerun_allowed": False,
        "human_review_authorized": False,
    }


def _text_stats(values: list[str]) -> dict[str, float | int]:
    lengths = [len(value or "") for value in values]
    return {
        "count": len(lengths),
        "median_chars": round(float(median(lengths)), 2) if lengths else 0.0,
        "mean_chars": round(float(mean(lengths)), 2) if lengths else 0.0,
    }


def _atomicity_diagnostics(claims: list[dict[str, Any]]) -> dict[str, Any]:
    conjunction_re = re.compile(r"以及|并且|同时|而且|但是|但|且|一是|二是|或者|或")
    punctuation_re = re.compile(r"[，,；;]")
    rows = []
    for claim in claims:
        statement = str(claim.get("statement") or "")
        punctuation = len(punctuation_re.findall(statement))
        conjunctions = len(conjunction_re.findall(statement))
        rows.append({
            "claim_id": claim.get("claim_id"),
            "statement_chars": len(statement),
            "separator_count": punctuation,
            "conjunction_count": conjunctions,
            "multi_clause_heuristic": punctuation + conjunctions >= 2,
        })
    return {
        "diagnostic_only": True,
        "human_atomicity_metric": False,
        "multi_clause_heuristic_count": sum(item["multi_clause_heuristic"] for item in rows),
        "separator_count": sum(item["separator_count"] for item in rows),
        "conjunction_count": sum(item["conjunction_count"] for item in rows),
        "claims": rows,
    }


def _normalized_chars(value: str) -> str:
    return "".join(re.findall(r"[0-9A-Za-z\u4e00-\u9fff]", value or "")).lower()


def _bigrams(value: str) -> set[str]:
    normalized = _normalized_chars(value)
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[index:index + 2] for index in range(len(normalized) - 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def _pointer_locators(value: str) -> set[str]:
    return set(re.findall(r"(?:PAGE|PARA|SHEET):[^\]\s]+", value or ""))


def map_old_failures_to_new_candidates(
    original_bundle: dict[str, Any],
    original_decisions: dict[str, Any],
    new_bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    original_by_id = {item.get("claim_id"): item for item in original_bundle.get("claims") or []}
    unsupported = [
        item for item in original_decisions.get("claims") or []
        if item.get("semantic_support") == "UNSUPPORTED"
    ]
    mappings = []
    for decision in unsupported:
        original = original_by_id.get(decision.get("claim_id")) or {}
        old_statement = str(original.get("statement") or decision.get("original_claim") or "")
        old_evidence = str(original.get("evidence_excerpt") or decision.get("immutable_evidence_excerpt") or "")
        old_locators = _pointer_locators(str(original.get("evidence_pointer") or ""))
        candidates = []
        for new_claim in new_bundle.get("claims") or []:
            statement_score = _jaccard(_bigrams(old_statement), _bigrams(str(new_claim.get("statement") or "")))
            evidence_score = SequenceMatcher(
                None, _normalized_chars(old_evidence),
                _normalized_chars(str(new_claim.get("evidence_excerpt") or "")),
                autojunk=False,
            ).ratio()
            locator_overlap = bool(
                old_locators & _pointer_locators(str(new_claim.get("evidence_pointer") or ""))
            )
            score = 0.45 * statement_score + 0.35 * evidence_score + 0.20 * int(locator_overlap)
            if locator_overlap or score >= 0.18:
                candidates.append({
                    "claim_id": new_claim.get("claim_id"),
                    "score": round(score, 4),
                    "statement_bigram_jaccard": round(statement_score, 4),
                    "evidence_sequence_ratio": round(evidence_score, 4),
                    "locator_overlap": locator_overlap,
                })
        candidates.sort(key=lambda item: (-item["score"], str(item["claim_id"])))
        selected = candidates[:3]
        mappings.append({
            "old_claim_id": decision.get("claim_id"),
            "old_failure_category": decision.get("semantic_failure_category"),
            "candidate_new_claim_ids": [item["claim_id"] for item in selected],
            "match_basis": selected,
            "no_new_candidate": not selected,
            "diagnostic_only": True,
            "semantic_verdict": "PENDING_HUMAN_REVIEW",
        })
    return mappings


def build_structural_comparison(
    original_bundle: dict[str, Any],
    new_bundle: dict[str, Any],
    original_decisions: dict[str, Any],
    new_mechanical: dict[str, Any],
) -> dict[str, Any]:
    old_claims = original_bundle.get("claims") or []
    new_claims = new_bundle.get("claims") or []
    old_count = len(old_claims)
    new_count = len(new_claims)
    old_attribution = [str(item.get("attributed_to") or "") for item in old_claims]
    new_attribution = [str(item.get("attributed_to") or "") for item in new_claims]
    old_usage = (original_bundle.get("model") or {}).get("usage") or {}
    new_model = new_bundle.get("model") or {}
    new_usage = new_model.get("usage") or {}
    new_total = new_usage.get("total_tokens")
    return {
        "document_type": COMPARISON_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "COMPLETE_MECHANICS_ONLY",
        "original_run_id": ORIGINAL_RUN_ID,
        "controlled_run_id": new_bundle.get("pilot_run_id"),
        "semantic_verdict": "PENDING_HUMAN_REVIEW",
        "extraction_volume": {
            "old_claim_count": old_count,
            "new_claim_count": new_count,
            "delta": new_count - old_count,
            "delta_percent": round(100 * (new_count - old_count) / old_count, 2) if old_count else 0.0,
        },
        "statement_length": {
            "old": _text_stats([str(item.get("statement") or "") for item in old_claims]),
            "new": _text_stats([str(item.get("statement") or "") for item in new_claims]),
        },
        "evidence_length": {
            "old": _text_stats([str(item.get("evidence_excerpt") or "") for item in old_claims]),
            "new": _text_stats([str(item.get("evidence_excerpt") or "") for item in new_claims]),
        },
        "attributed_to": {
            "old_non_empty_count": sum(bool(value.strip()) for value in old_attribution),
            "new_non_empty_count": sum(bool(value.strip()) for value in new_attribution),
            "old_distinct_labels": sorted({value for value in old_attribution if value.strip()}),
            "new_distinct_labels": sorted({value for value in new_attribution if value.strip()}),
        },
        "mechanical_evidence": {
            "old_quote_fidelity_percent": 78.57,
            "new_quote_fidelity_percent": new_mechanical["quote_fidelity"]["percent"],
            "old_quote_drift_percent": 21.43,
            "new_quote_drift_percent": new_mechanical["quote_drift"]["percent"],
            "old_source_binding_percent": 78.57,
            "new_source_binding_percent": new_mechanical["source_binding"]["percent"],
        },
        "atomicity_structural_diagnostics": {
            "old": _atomicity_diagnostics(old_claims),
            "new": _atomicity_diagnostics(new_claims),
            "interpretation": "heuristic compound rate != Human atomicity issue rate",
        },
        "old_failure_to_new_candidate_mapping": map_old_failures_to_new_candidates(
            original_bundle, original_decisions, new_bundle,
        ),
        "token_usage": {
            "old": {
                "prompt_tokens": old_usage.get("prompt_tokens", 224062),
                "completion_tokens": old_usage.get("completion_tokens", 122117),
                "total_tokens": old_usage.get("total_tokens", 346179),
                "claims": old_count,
                "tokens_per_claim": round((old_usage.get("total_tokens", 346179)) / old_count, 2),
            },
            "new": {
                "logical_extractions": 1,
                "actual_api_attempts": new_model.get("llm_calls", "NOT_AVAILABLE"),
                "prompt_tokens": new_usage.get("prompt_tokens", "NOT_AVAILABLE"),
                "completion_tokens": new_usage.get("completion_tokens", "NOT_AVAILABLE"),
                "total_tokens": new_total if new_total is not None else "NOT_AVAILABLE",
                "claims": new_count,
                "tokens_per_claim": (
                    round(new_total / new_count, 2)
                    if isinstance(new_total, int) and new_count else "NOT_AVAILABLE"
                ),
            },
        },
        "interpretation_limits": {
            "claim_count_decrease_is_not_automatically_recall_regression": True,
            "missing_old_failure_is_not_automatically_fixed": True,
            "literal_noisy_token_is_not_automatically_quality_regression": True,
            "no_automated_semantic_pass": True,
        },
    }


def _render_comparison(comparison: dict[str, Any]) -> str:
    volume = comparison["extraction_volume"]
    statement = comparison["statement_length"]
    evidence = comparison["evidence_length"]
    attribution = comparison["attributed_to"]
    mechanics = comparison["mechanical_evidence"]
    tokens = comparison["token_usage"]
    mapping = comparison["old_failure_to_new_candidate_mapping"]
    lines = [
        "# Pilot #3 controlled re-extraction — deterministic structural comparison",
        "",
        "This is mechanics-only review assistance. It does not assign semantic support, atomicity, KEEP/DROP, or repair success.",
        "",
        f"- Original run: `{comparison['original_run_id']}`",
        f"- Controlled run: `{comparison['controlled_run_id']}`",
        f"- Claims: `{volume['old_claim_count']} -> {volume['new_claim_count']}` (`{volume['delta']}`, `{volume['delta_percent']}%`)",
        f"- Statement median / mean chars: `{statement['old']['median_chars']} / {statement['old']['mean_chars']}` -> `{statement['new']['median_chars']} / {statement['new']['mean_chars']}`",
        f"- Evidence median chars: `{evidence['old']['median_chars']}` -> `{evidence['new']['median_chars']}`",
        f"- Non-empty attribution: `{attribution['old_non_empty_count']} -> {attribution['new_non_empty_count']}`",
        f"- Distinct attribution labels: `{len(attribution['old_distinct_labels'])} -> {len(attribution['new_distinct_labels'])}`",
        f"- Quote fidelity: `{mechanics['old_quote_fidelity_percent']}% -> {mechanics['new_quote_fidelity_percent']}%`",
        f"- Quote drift: `{mechanics['old_quote_drift_percent']}% -> {mechanics['new_quote_drift_percent']}%`",
        f"- Source binding: `{mechanics['old_source_binding_percent']}% -> {mechanics['new_source_binding_percent']}%`",
        f"- Total tokens: `{tokens['old']['total_tokens']} -> {tokens['new']['total_tokens']}`",
        f"- Tokens / Claim: `{tokens['old']['tokens_per_claim']} -> {tokens['new']['tokens_per_claim']}`",
        "",
        "## Old unsupported Claim → likely new candidates",
        "",
        "| Old Claim | Failure category | Candidate new Claims | Basis |",
        "|---|---|---|---|",
    ]
    for item in mapping:
        basis = "; ".join(
            f"{candidate['claim_id']} score={candidate['score']} locator={candidate['locator_overlap']}"
            for candidate in item["match_basis"]
        ) or "no obvious deterministic candidate"
        lines.append(
            f"| `{item['old_claim_id']}` | `{item['old_failure_category']}` | "
            f"`{', '.join(item['candidate_new_claim_ids']) or 'NONE'}` | {basis} |"
        )
    lines += [
        "",
        "A missing candidate may be correct fail-closed behavior or recall loss. Preserved noisy wording may be contract-compliant. Stage S3 must decide.",
        "",
    ]
    return "\n".join(lines)


def _render_report(metrics: dict[str, Any], comparison: dict[str, Any]) -> str:
    mechanical = metrics.get("mechanical_evidence") or {}
    production = metrics.get("production") or {}
    usage = metrics.get("model_usage") or {}
    regressions = metrics.get("regression_validation") or {}
    artifacts = metrics.get("artifacts") or {}
    lines = [
        "# Phase 3C Pilot #3 — Controlled Semantic Re-extraction Report",
        "",
        f"PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE = `{str(metrics.get('PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE', False)).lower()}`",
        f"PILOT3_REEXTRACTION_RUN_ID = `{metrics.get('pilot_run_id')}`",
        f"PILOT3_REEXTRACTION_ARTIFACT_GATE = `{metrics.get('PILOT3_REEXTRACTION_ARTIFACT_GATE')}`",
        f"PILOT3_REEXTRACTION_MECHANICAL_GATE = `{metrics.get('PILOT3_REEXTRACTION_MECHANICAL_GATE')}`",
        "PILOT3_GENERALIZATION_VERDICT = `FAIL`",
        "PHASE3C_COMPLETE = `false`",
        "PRODUCTION_APPLY_READY = `NO`",
        "",
        "## Freeze",
        "",
        f"- Source SHA: `{metrics.get('source_sha256')}` (`PASS`)",
        f"- Prompt SHA: `{metrics.get('prompt_sha256')}` (`PASS`)",
        f"- Prompt file SHA: `{metrics.get('prompt_file_sha256')}` (`PASS`)",
        f"- Runtime semantic settings changed: `{str(metrics.get('runtime_semantic_settings_changed')).lower()}`",
        f"- Runtime files unchanged during S2: `{str(metrics.get('runtime_files_unchanged')).lower()}`",
        "",
        "## Extraction and Evidence",
        "",
        f"- Logical extractions / actual API attempts: `{usage.get('logical_extractions')} / {usage.get('actual_api_attempts')}`",
        f"- Configured / response model: `{usage.get('configured_model')} / {usage.get('response_model')}`",
        f"- Claims: `{metrics.get('claims_total')}`",
        f"- Human decisions PENDING: `{metrics.get('human_decisions_pending')}`",
        f"- Fidelity counts: `{json.dumps(mechanical.get('counts') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- Quote fidelity / drift / source binding: `{(mechanical.get('quote_fidelity') or {}).get('percent')}% / {(mechanical.get('quote_drift') or {}).get('percent')}% / {(mechanical.get('source_binding') or {}).get('percent')}%`",
        f"- Single-page / cross-page / ambiguous / unresolved / bounded candidates: `{mechanical.get('single_page')} / {mechanical.get('cross_page')} / {mechanical.get('ambiguous')} / {mechanical.get('unresolved')} / {mechanical.get('bounded_context_candidates')}`",
        "- Semantic support, true semantic failure, and Human atomicity: `PENDING_HUMAN_REVIEW`",
        "",
        "## Structural comparison",
        "",
        f"- Claim count old/new: `{comparison['extraction_volume']['old_claim_count']} / {comparison['extraction_volume']['new_claim_count']}`",
        f"- Old failure mappings with no candidate: `{sum(item['no_new_candidate'] for item in comparison['old_failure_to_new_candidate_mapping'])} / 14`",
        f"- Prompt / completion / total tokens: `{usage.get('prompt_tokens')} / {usage.get('completion_tokens')} / {usage.get('total_tokens')}`",
        f"- Tokens / Claim: `{usage.get('tokens_per_claim')}`",
        "",
        "## Isolation and regressions",
        "",
        f"- Original artifacts unchanged: `{str(metrics.get('original_artifacts_unchanged')).lower()}`",
        f"- Production SHA: `{(production.get('pre') or {}).get('sha256')} -> {(production.get('post') or {}).get('sha256')}`",
        f"- Production changed / table counts changed: `{'YES' if not production.get('unchanged') else 'NO'} / {'YES' if production.get('table_counts_changed') else 'NO'}`",
        f"- Integrity / FK violations: `{(production.get('post') or {}).get('integrity_check')} / {len((production.get('post') or {}).get('foreign_key_violations') or [])}`",
        "- IMA / propagation / legacy ingestion: `NO / NO / NO`",
    ]
    for name in REQUIRED_REGRESSIONS:
        result = regressions.get(name, "PENDING")
        status = result.get("status") if isinstance(result, dict) else result
        lines.append(f"- {name}: `{status}`")
    lines += [
        "",
        "## Artifacts",
        "",
        *[f"- {name}: `{path}`" for name, path in artifacts.items()],
        "",
        f"PHASE3C_NEXT_GATE = `{metrics.get('PHASE3C_NEXT_GATE')}`",
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED = `true`",
        "",
        "STOP: Stage S3 Human Review, Prompt iteration, Evidence repair, Pilot #4, Production, IMA, propagation, and legacy ingestion were not executed.",
        "",
    ]
    return "\n".join(lines)


def _write_failure(
    run_dir: Path,
    repair_dir: Path,
    run_id: str,
    stage: str,
    exc: BaseException,
    preflight: dict[str, Any],
    production_db: Path,
) -> dict[str, Any]:
    production_post = production_snapshot(production_db)
    original_post = _snapshot_files(_original_artifact_paths(run_dir.parent.parent))
    failure = {
        "document_type": "phase3c_pilot3_controlled_reextraction_failure",
        "schema_version": "1",
        "status": "FAILED_PRESERVED",
        "pilot_run_id": run_id,
        "failed_stage": stage,
        "error_class": type(exc).__name__,
        "error": str(exc),
        "PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE": False,
        "PILOT3_REEXTRACTION_ARTIFACT_GATE": "FAIL",
        "PILOT3_GENERALIZATION_VERDICT": "FAIL",
        "PHASE3C_COMPLETE": False,
        "PRODUCTION_APPLY_READY": "NO",
        "PHASE3C_NEXT_GATE": "Resolve Pilot #3 Controlled Re-extraction Failure",
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": True,
        "one_logical_extraction_started": stage != "PREFLIGHT",
        "quality_rerun": False,
        "original_artifacts_unchanged": original_post == preflight["original_artifacts"],
        "production_pre": preflight["production_pre"],
        "production_post": production_post,
        "production_unchanged": production_post == preflight["production_pre"],
    }
    path = run_dir / "controlled_reextraction_failure.json"
    write_json(path, failure)
    repair_path = repair_dir / "pilot3_controlled_reextraction_failure.json"
    write_json(repair_path, failure)
    return {"status": "FAIL", "failure": failure, "failure_path": str(path)}


def run_controlled_reextraction(
    source_path: Path,
    cfg: AppConfig,
    *,
    run_id: str | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    run_id = run_id or make_id("PILOT")
    production_db = Path(production_db_path or cfg.db_path).resolve()
    run_dir = (cfg.root / "phase3c" / run_id).resolve()
    repair_dir = (cfg.root / "phase3c" / "pilot3_semantic_failure_repair").resolve()
    protected_outputs = (
        repair_dir / "pilot3_controlled_reextraction_report.md",
        repair_dir / "pilot3_controlled_reextraction_comparison.json",
        repair_dir / "pilot3_controlled_reextraction_comparison.md",
        repair_dir / "pilot3_controlled_reextraction_regression_receipt.json",
    )
    if any(path.exists() for path in protected_outputs):
        raise PilotError("PILOT3_REEXTRACTION_OUTPUT_ALREADY_EXISTS")
    preflight = controlled_reextraction_preflight(
        source_path, cfg, run_id, production_db_path=production_db,
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    repair_dir.mkdir(parents=True, exist_ok=True)
    preflight_path = run_dir / "controlled_reextraction_preflight.json"
    write_json(preflight_path, preflight)
    marker_path = run_dir / "one_logical_extraction_marker.json"
    write_json(marker_path, {
        "document_type": "phase3c_pilot3_controlled_reextraction_marker",
        "pilot_run_id": run_id,
        "source_sha256": ORIGINAL_SOURCE_SHA256,
        "prompt_sha256": REPAIRED_PROMPT_SHA256,
        "one_logical_extraction_started": True,
        "quality_rerun_allowed": False,
        "status": "STARTED",
    })

    try:
        extraction = extract_pilot_source(
            Path(source_path), cfg,
            output_dir=run_dir,
            production_db_path=production_db,
            required_prompt_sha256=REPAIRED_PROMPT_SHA256,
            run_id=run_id,
        )
    except Exception as exc:
        return _write_failure(run_dir, repair_dir, run_id, "SEMANTIC_EXTRACTION", exc, preflight, production_db)

    bundle = extraction["bundle"]
    if (
        bundle.get("pilot_run_id") != run_id
        or (bundle.get("source") or {}).get("sha256") != ORIGINAL_SOURCE_SHA256
        or ((bundle.get("model") or {}).get("prompt") or {}).get("prompt_sha256") != REPAIRED_PROMPT_SHA256
    ):
        return _write_failure(
            run_dir, repair_dir, run_id, "EXTRACTION_FREEZE_VALIDATION",
            PilotError("PILOT3_REEXTRACTION_BUNDLE_FREEZE_MISMATCH"), preflight, production_db,
        )

    try:
        rebound = rebind_stage1_evidence_locators(
            Path(extraction["extraction_bundle_path"]), Path(source_path),
            output_dir=run_dir, production_db_path=production_db,
        )
        evidence = build_pilot2_evidence_support_draft(
            Path(rebound["rebound_bundle_path"]), Path(rebound["review_draft_path"]),
            Path(source_path), output_dir=run_dir, production_db_path=production_db,
        )
        gate = run_pilot2_gate_a_quote_fidelity(
            Path(extraction["extraction_bundle_path"]), Path(rebound["rebound_bundle_path"]),
            Path(evidence["draft_path"]), Path(source_path), output_dir=run_dir,
            production_db_path=production_db,
            original_review_path=Path(extraction["review_draft_path"]),
        )
    except Exception as exc:
        return _write_failure(run_dir, repair_dir, run_id, "EVIDENCE_V2", exc, preflight, production_db)

    evidence_artifact = copy.deepcopy(evidence["draft"])
    evidence_artifact["document_type"] = "phase3c_pilot3_controlled_reextraction_evidence_v2"
    evidence_artifact["stage"] = "CONTROLLED_SEMANTIC_REEXTRACTION_PRE_HUMAN_REVIEW"
    evidence_path = run_dir / "evidence_contract_v2.json"
    write_json(evidence_path, evidence_artifact)

    quote_artifact = copy.deepcopy(gate)
    quote_artifact["document_type"] = "phase3c_pilot3_controlled_reextraction_quote_fidelity"
    quote_artifact["stage"] = "CONTROLLED_SEMANTIC_REEXTRACTION_PRE_HUMAN_REVIEW"
    quote_path = run_dir / "quote_fidelity.json"
    write_json(quote_path, quote_artifact)
    review_surface_path = run_dir / "evidence_review_surface.md"
    surface = render_pilot3_review_surface(quote_artifact, evidence_artifact).replace(
        "# Phase 3C Pilot #3 Independent Human Review Surface",
        "# Phase 3C Pilot #3 Controlled Re-extraction — Independent Human Review Surface",
        1,
    )
    review_surface_path.write_text(surface, encoding="utf-8")

    claims_total = len(bundle.get("claims") or [])
    counts = gate["metrics"]["fidelity_counts"]
    faithful = sum(counts.get(name, 0) for name in (
        "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
        "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
    ))
    drift = counts.get("QUOTE_DRIFT", 0)
    evidence_metrics = evidence["metrics"]
    bound = evidence_metrics["evidence_deterministically_bound"]
    mechanical = {
        "counts": {name: counts.get(name, 0) for name in sorted(PILOT2_GATE_A_FIDELITY_STATUSES)},
        "quote_fidelity": _ratio(faithful, claims_total, 85.0, at_least=True),
        "quote_drift": _ratio(drift, claims_total, 15.0, at_least=False),
        "source_binding": _ratio(bound, claims_total, 85.0, at_least=True),
        "single_page": evidence_metrics["single_page_locator_bound"],
        "cross_page": evidence_metrics["cross_page_exact_spans"],
        "ambiguous": evidence_metrics["locator_ambiguous"],
        "unresolved": evidence_metrics["locator_unresolved"],
        "bounded_context_candidates": evidence_metrics["bounded_context_candidate_claims"],
    }
    mechanical_gate = "PASS" if all(
        mechanical[name]["passed"] for name in ("quote_fidelity", "quote_drift", "source_binding")
    ) else "FAIL"
    original_paths = _original_artifact_paths(cfg.root)
    original_bundle = _load_json(original_paths["original_extraction_bundle"])
    original_decisions = _load_json(original_paths["original_human_review_decisions"])
    comparison = build_structural_comparison(
        original_bundle, bundle, original_decisions, mechanical,
    )
    comparison_path = repair_dir / "pilot3_controlled_reextraction_comparison.json"
    comparison_md_path = repair_dir / "pilot3_controlled_reextraction_comparison.md"
    write_json(comparison_path, comparison)
    comparison_md_path.write_text(_render_comparison(comparison), encoding="utf-8")

    runtime_files_post = _runtime_file_snapshot()
    runtime_settings_post = _runtime_settings(cfg)
    original_post = _snapshot_files(original_paths)
    production_post = production_snapshot(production_db)
    production_pre = preflight["production_pre"]
    original_unchanged = original_post == preflight["original_artifacts"]
    production_unchanged = production_post == production_pre
    runtime_files_unchanged = runtime_files_post == preflight["runtime_files"]
    runtime_settings_unchanged = runtime_settings_post == preflight["runtime_settings"]
    pending_count = sum(
        item.get("human_decision") == "PENDING" for item in evidence_artifact.get("claims") or []
    )
    review_pending = all(
        item.get("decision") == "PENDING" for item in extraction["review"].get("claims") or []
    )
    model = bundle.get("model") or {}
    usage = model.get("usage") or {}
    total_tokens = usage.get("total_tokens")
    hard_artifact_complete = bool(
        claims_total
        and pending_count == claims_total
        and review_pending
        and original_unchanged
        and production_unchanged
        and runtime_files_unchanged
        and runtime_settings_unchanged
        and all(path.is_file() for path in (
            Path(extraction["extraction_bundle_path"]), evidence_path, quote_path,
            review_surface_path, comparison_path, comparison_md_path,
        ))
    )
    metrics = {
        "document_type": METRICS_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "AWAITING_REGRESSION_VALIDATION" if hard_artifact_complete else "FAIL",
        "pilot_run_id": run_id,
        "original_run_id": ORIGINAL_RUN_ID,
        "PHASE3C_PILOT3_SEMANTIC_REPAIR_IMPLEMENTED": True,
        "PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE": False,
        "PILOT3_REEXTRACTION_ARTIFACT_GATE": "PASS" if hard_artifact_complete else "FAIL",
        "PILOT3_REEXTRACTION_MECHANICAL_GATE": mechanical_gate,
        "PILOT3_GENERALIZATION_VERDICT": "FAIL",
        "PHASE3C_COMPLETE": False,
        "PRODUCTION_APPLY_READY": "NO",
        "PHASE3C_NEXT_GATE": (
            "Stage S2 Regression Validation"
            if hard_artifact_complete else "Resolve Pilot #3 Controlled Re-extraction Failure"
        ),
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": True,
        "source_sha256": ORIGINAL_SOURCE_SHA256,
        "prompt_sha256": REPAIRED_PROMPT_SHA256,
        "prompt_file_sha256": REPAIRED_PROMPT_FILE_SHA256,
        "runtime_settings": copy.deepcopy(preflight["runtime_settings"]),
        "runtime_semantic_settings_changed": not runtime_settings_unchanged,
        "runtime_files_pre": copy.deepcopy(preflight["runtime_files"]),
        "runtime_files_post": runtime_files_post,
        "runtime_files_unchanged": runtime_files_unchanged,
        "one_logical_extraction": True,
        "quality_rerun": False,
        "claims_total": claims_total,
        "human_decisions_pending": pending_count,
        "human_semantic_review_executed": False,
        "semantic_metrics": {
            "semantic_support_rate": "PENDING_HUMAN_REVIEW",
            "true_semantic_failure_rate": "PENDING_HUMAN_REVIEW",
            "material_atomicity_failure_rate": "PENDING_HUMAN_REVIEW",
        },
        "mechanical_evidence": mechanical,
        "model_usage": {
            "logical_extractions": 1,
            "actual_api_attempts": model.get("llm_calls", "NOT_AVAILABLE"),
            "configured_model": model.get("configured_model", "NOT_AVAILABLE"),
            "response_model": model.get("response_model", "NOT_AVAILABLE"),
            "prompt_tokens": usage.get("prompt_tokens", "NOT_AVAILABLE"),
            "completion_tokens": usage.get("completion_tokens", "NOT_AVAILABLE"),
            "total_tokens": total_tokens if total_tokens is not None else "NOT_AVAILABLE",
            "tokens_per_claim": (
                round(total_tokens / claims_total, 2)
                if isinstance(total_tokens, int) and claims_total else "NOT_AVAILABLE"
            ),
        },
        "original_artifacts_pre": preflight["original_artifacts"],
        "original_artifacts_post": original_post,
        "original_artifacts_unchanged": original_unchanged,
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
            "prompt_modified_after_result": False,
        },
        "regression_validation": {name: "PENDING" for name in REQUIRED_REGRESSIONS},
        "artifacts": {
            "run_directory": str(run_dir),
            "preflight": str(preflight_path),
            "logical_extraction_marker": str(marker_path),
            "extraction_bundle": extraction["extraction_bundle_path"],
            "evidence_contract_v2": str(evidence_path),
            "quote_fidelity": str(quote_path),
            "evidence_review_surface": str(review_surface_path),
            "pre_review_metrics": str(run_dir / "pre_review_metrics.json"),
            "comparison_json": str(comparison_path),
            "comparison_markdown": str(comparison_md_path),
            "controlled_report": str(repair_dir / "pilot3_controlled_reextraction_report.md"),
        },
    }
    metrics_path = run_dir / "pre_review_metrics.json"
    report_path = repair_dir / "pilot3_controlled_reextraction_report.md"
    write_json(metrics_path, metrics)
    report_path.write_text(_render_report(metrics, comparison), encoding="utf-8")
    marker = _load_json(marker_path)
    marker["status"] = "LOGICAL_EXTRACTION_COMPLETE"
    marker["actual_api_attempts"] = model.get("llm_calls", "NOT_AVAILABLE")
    marker["quality_rerun"] = False
    write_json(marker_path, marker)
    if not hard_artifact_complete:
        return {"status": "FAIL", "metrics": metrics, "metrics_path": str(metrics_path)}
    return {
        "status": "AWAITING_REGRESSION_VALIDATION",
        "pilot_run_id": run_id,
        "metrics": metrics,
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "comparison_path": str(comparison_path),
        "run_dir": str(run_dir),
    }


def finalize_controlled_reextraction(
    run_dir: Path,
    regression_receipt_path: Path,
    cfg: AppConfig,
    *,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    receipt_path = Path(regression_receipt_path).resolve()
    production_db = Path(production_db_path or cfg.db_path).resolve()
    metrics_path = run_dir / "pre_review_metrics.json"
    metrics = _load_json(metrics_path)
    receipt = _load_json(receipt_path)
    if (
        receipt.get("document_type") != REGRESSION_DOCUMENT_TYPE
        or receipt.get("pilot_run_id") != metrics.get("pilot_run_id")
    ):
        raise PilotError("PILOT3_REEXTRACTION_REGRESSION_RECEIPT_INVALID")
    results = receipt.get("results") or {}
    if set(results) != set(REQUIRED_REGRESSIONS) or any(
        not isinstance(result, dict) or result.get("status") != "PASS"
        for result in results.values()
    ):
        raise PilotError("PILOT3_REEXTRACTION_REGRESSION_COVERAGE_INVALID")

    prompt_status = phase3c_prompt_repair_status(prompts_module.SOURCE_ANALYSIS_SYSTEM)
    prompt_frozen = bool(
        prompt_status["prompt_sha256"] == metrics["prompt_sha256"] == REPAIRED_PROMPT_SHA256
        and sha256_file(Path(prompts_module.__file__).resolve())
        == metrics["prompt_file_sha256"] == REPAIRED_PROMPT_FILE_SHA256
    )
    runtime_frozen = _runtime_settings(cfg) == metrics["runtime_settings"]
    runtime_files_post = _runtime_file_snapshot()
    runtime_files_unchanged = runtime_files_post == metrics["runtime_files_pre"]
    original_post = _snapshot_files(_original_artifact_paths(cfg.root))
    original_unchanged = original_post == metrics["original_artifacts_pre"]
    production_post = production_snapshot(production_db)
    production_pre = metrics["production"]["pre"]
    production_unchanged = production_post == production_pre
    artifacts_complete = all(
        Path(path).exists() for name, path in metrics["artifacts"].items()
        if name not in {"controlled_report"}
    )
    complete = bool(
        metrics.get("PILOT3_REEXTRACTION_ARTIFACT_GATE") == "PASS"
        and prompt_frozen and runtime_frozen and runtime_files_unchanged and original_unchanged
        and production_unchanged and artifacts_complete
    )
    metrics["regression_validation"] = copy.deepcopy(results)
    metrics["regression_receipt"] = {"path": str(receipt_path), "sha256": sha256_file(receipt_path)}
    metrics["prompt_frozen_post"] = prompt_frozen
    metrics["runtime_semantic_settings_changed"] = not runtime_frozen
    metrics["runtime_files_post"] = runtime_files_post
    metrics["runtime_files_unchanged"] = runtime_files_unchanged
    metrics["original_artifacts_post"] = original_post
    metrics["original_artifacts_unchanged"] = original_unchanged
    metrics["production"]["post"] = production_post
    metrics["production"]["unchanged"] = production_unchanged
    metrics["production"]["table_counts_changed"] = (
        production_pre["table_counts"] != production_post["table_counts"]
    )
    metrics["status"] = "COMPLETE" if complete else "FAIL"
    metrics["PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE"] = complete
    metrics["PHASE3C_NEXT_GATE"] = (
        "Pilot #3 Controlled Re-extraction Independent Human Review"
        if complete else "Resolve Pilot #3 Controlled Re-extraction Failure"
    )
    write_json(metrics_path, metrics)
    repair_dir = cfg.root / "phase3c" / "pilot3_semantic_failure_repair"
    comparison_path = repair_dir / "pilot3_controlled_reextraction_comparison.json"
    comparison = _load_json(comparison_path)
    report_path = repair_dir / "pilot3_controlled_reextraction_report.md"
    report_path.write_text(_render_report(metrics, comparison), encoding="utf-8")
    if not complete:
        raise PilotError("PILOT3_REEXTRACTION_FINALIZATION_FAILED")
    return {
        "status": "PASS",
        "metrics": metrics,
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "comparison_path": str(comparison_path),
    }
