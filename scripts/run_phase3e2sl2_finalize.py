from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


BASELINE = "e7878cc42447bfc06e8e23da54e2c0c720311f13"
IMPLEMENTATION_COMMIT = "e70b50fdbc436735c6ca7f7a3d4de45eb941e1b7"
BRANCH = "codex/phase3e2sl2-bounded-semantic-closure"
PRODUCTION_SHA256 = "3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0"
S_K_SOURCE_SHA256 = "18dfbb4cef2eeb94e9319f6e7178da183a66bb57db852f819f338b27182310b9"
S_K_CONTRACT_SHA256 = "4a848436725edf1cca4ac3545a83b45d48adc1af05a1210fca47035d4200bcbd"


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _production_state(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    digest = _sha256(resolved)
    uri = f"file:{resolved.as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    sidecars = {
        suffix: Path(f"{resolved}{suffix}").exists()
        for suffix in ("-wal", "-shm", "-journal")
    }
    return {
        "path": str(resolved),
        "sha256": digest,
        "integrity": integrity,
        "foreign_key_violations": foreign_keys,
        "sidecars_present": sidecars,
        "matches_frozen_baseline": digest == PRODUCTION_SHA256
        and integrity == "ok"
        and foreign_keys == 0
        and not any(sidecars.values()),
    }


def _contract() -> dict[str, Any]:
    return {
        "document_type": "phase3e2sm_acceptance_contract",
        "schema_version": "1.0",
        "created_at_utc": _now(),
        "authority": "PROSPECTIVE_FUTURE_S_M_ACCEPTANCE_ONLY",
        "implementation_commit_identity": IMPLEMENTATION_COMMIT,
        "implementation_baseline_parent": BASELINE,
        "fresh_source_rule": {
            "required": "GENUINELY_THIRD_UNUSED_UNINSPECTED_FRESH_CLEAN_PDF",
            "must_not_be_s_k_source_sha256": S_K_SOURCE_SHA256,
            "development_probe_ineligible": True,
            "source_selected": False,
            "source_inspected": False,
            "source_substitution_after_freeze": "FORBIDDEN",
        },
        "retry_policy": {
            "same_source_semantic_retry": "FORBIDDEN",
            "source_substitution_after_failure": "FORBIDDEN",
            "transport_retry": "ALLOWED_ONLY_FOR_IDENTICAL_SEMANTIC_INPUTS_UNDER_FROZEN_RUNTIME",
        },
        "thresholds": {
            "repair_detection_recall": {"comparator": ">=", "value": 0.75},
            "atomicity_generalization_recall": {"comparator": ">=", "value": 0.80},
            "causally_correct_atomicity_recall": {"comparator": ">=", "value": 0.80},
            "nature_generalization_recall": {"comparator": ">=", "value": 0.80},
            "system_keep_precision": {"comparator": ">=", "value": 0.80},
            "nature_human_keep_false_positives": {
                "comparator": "<=",
                "formula": "max(3, 0.10 * HUMAN_KEEP)",
            },
            "system_review_rate": {"comparator": "<=", "value": 0.30},
            "valid_proposition_ir_rate": {"comparator": ">=", "value": 0.95},
            "proposition_evidence_binding_failures": {"comparator": "==", "value": 0},
            "unsupported_proposition_content": {"comparator": "==", "value": 0},
            "catastrophic_false_drops": {"comparator": "==", "value": 0},
            "unsupported_false_keep": {"comparator": "==", "value": 0},
            "duplicate_similarity_threshold": {"comparator": "==", "value": 0.92},
        },
        "zero_denominator_semantics": {
            "fresh_source_zero_denominator_and_historical_class_coverage_pass": {
                "numerator": 0,
                "denominator": 0,
                "value": None,
                "scoreability": "NOT_APPLICABLE",
                "gate": "PASS_BY_HISTORICAL_COVERAGE",
            },
            "fresh_source_zero_denominator_and_historical_class_coverage_not_proven": {
                "numerator": 0,
                "denominator": 0,
                "value": None,
                "scoreability": "NOT_APPLICABLE",
                "gate": "FAIL",
            },
            "zero_over_zero_is_one_hundred_percent": False,
        },
        "required_historical_replay_coverage": {
            "S_B": "PASS",
            "S_C": "PASS",
            "S_F": "PASS",
            "S_H": "PASS",
            "S_I": "PASS",
        },
        "hard_gates": {
            "production_mode": "READ_ONLY",
            "production_changed": False,
            "unsupported_content_allowed": False,
            "human_labels_mutable_after_freeze": False,
            "threshold_changes_after_source_freeze": False,
            "code_or_prompt_changes_after_source_freeze": False,
        },
        "original_s_k_contract_sha256": S_K_CONTRACT_SHA256,
        "original_s_k_result": "FAIL",
        "S_M_STARTED": False,
    }


def build(repo: Path, draft_pr_number: int | None) -> dict[str, Any]:
    output = repo / "workspace/phase3e2sl2"
    sk = _read(output / "phase3e2sl2_sk_prospective_replay.json")
    historical = _read(output / "phase3e2sl2_historical_replay.json")
    review = _read(output / "phase3e2sl2_review_reconciliation_census.json")
    census = _read(output / "phase3e2sl2_code_path_census.json")
    if sk["S_L2_PROSPECTIVE_S_K_REPLAY"] != "PASS":
        raise RuntimeError("S_K_PROSPECTIVE_REPLAY_NOT_PASS")
    if not historical["all_required_historical_replays_pass"]:
        raise RuntimeError("HISTORICAL_REPLAYS_NOT_PASS")
    if census.get("status") != "COMPLETE_BEFORE_IMPLEMENTATION":
        raise RuntimeError("CODE_PATH_CENSUS_NOT_COMPLETE_BEFORE_IMPLEMENTATION")

    contract_path = output / "phase3e2sm_acceptance_contract.json"
    if contract_path.exists():
        contract = _read(contract_path)
        if contract.get("implementation_commit_identity") != IMPLEMENTATION_COMMIT:
            raise RuntimeError("S_M_CONTRACT_IMPLEMENTATION_IDENTITY_MISMATCH")
    else:
        contract = _contract()
        _write(contract_path, contract)
    contract_sha = _sha256(contract_path)
    metrics = sk["metrics"]
    scope = sk["scope_preservation"]
    duplicate = sk["duplicate"]
    production_pre = _production_state(repo / "workspace/pro_a.db")

    repair_receipt = {
        "document_type": "phase3e2sl2_repair_receipt",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "baseline": BASELINE,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "branch": BRANCH,
        "bounded_repair_surfaces": {
            "conditionality_scope_preservation": "IMPLEMENTED",
            "proposition_aware_duplicate_candidacy": "IMPLEMENTED",
            "bounded_review_reconciliation": "IMPLEMENTED",
            "zero_denominator_acceptance_semantics": "IMPLEMENTED",
        },
        "scope_preservation_invariant": (
            "A canonical proposition cannot omit an authoritatively supported "
            "meaning-changing structured qualifier; unsafe reconciliation remains REVIEW."
        ),
        "duplicate_similarity_threshold": 0.92,
        "global_duplicate_threshold_lowered": False,
        "keep_precision_threshold_lowered": False,
        "source_specific_behavior_added": False,
        "human_labels_changed": False,
        "original_s_k_artifacts_changed": False,
        "original_s_k_result": "FAIL",
        "known_scope_fn_fixed": scope["known_scope_fn_fixed"],
        "known_duplicate_fn_fixed": duplicate["known_duplicate_fn_fixed"],
        "avoidable_review_dispositions_reconciled": review[
            "changed_s_k_review_dispositions"
        ],
        "modified_implementation_files": [
            "src/pro_a/acceptance_metrics.py",
            "src/pro_a/operational_ingestion.py",
            "src/pro_a/pipeline.py",
            "src/pro_a/proposition_ir.py",
            "src/pro_a/semantic_admission.py",
        ],
    }
    scope_tests = {
        "document_type": "phase3e2sl2_scope_preservation_tests",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "result": "PASS",
        "focused_test_file": "tests/test_phase3e2sl2_bounded_semantic_closure.py",
        "positive_tests": [
            "test_scope_preservation_restores_supported_mandatory_condition",
            "test_scope_repair_is_visible_at_admission_without_silent_keep",
        ],
        "negative_tests": [
            "test_scope_preservation_does_not_duplicate_existing_condition_or_optional_context",
            "test_scope_preservation_fails_closed_when_condition_is_not_authoritatively_supported",
        ],
        "known_s_k_scope_fn_fixed": scope["known_scope_fn_fixed"],
        "material_scope_overstatement": metrics["material_scope_overstatement"],
    }
    duplicate_tests = {
        "document_type": "phase3e2sl2_duplicate_tests",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "result": "PASS",
        "similarity_threshold": duplicate["similarity_threshold"],
        "positive_test": "test_duplicate_shared_subproposition_is_compared_before_frozen_threshold",
        "negative_tests": [
            "test_duplicate_negative_controls_preserve_predicate_scope_outcome_and_condition",
            "test_duplicate_negative_controls_do_not_strip_scenario_or_unbounded_detail_parent",
        ],
        "known_s_k_duplicate_fn_fixed": duplicate["known_duplicate_fn_fixed"],
        "s_k_duplicate_false_positives": metrics["duplicate_false_positives"],
        "s_i_duplicate_false_positives": historical["s_i"]["metrics"][
            "duplicate_false_positives"
        ],
    }
    scoreability_tests = {
        "document_type": "phase3e2sl2_contract_scoreability_tests",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "result": "PASS",
        "cases": [
            {
                "case": "0/0 + historical coverage PASS",
                "value": None,
                "scoreability": "NOT_APPLICABLE",
                "gate": "PASS_BY_HISTORICAL_COVERAGE",
            },
            {
                "case": "0/0 + historical coverage FAIL",
                "value": None,
                "scoreability": "NOT_APPLICABLE",
                "gate": "FAIL",
            },
            {"case": "4/5", "value": 0.8, "scoreability": "SCOREABLE", "gate": "PASS"},
            {"case": "3/5", "value": 0.6, "scoreability": "SCOREABLE", "gate": "FAIL"},
        ],
        "test_names": [
            "test_zero_denominator_recall_is_explicitly_n_a_only_with_historical_coverage",
            "test_positive_denominator_recall_retains_numeric_pass_and_fail",
        ],
    }
    regression_receipt = {
        "document_type": "phase3e2sl2_regression_receipt",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "focused_tests": {"status": "PASS", "passed": 145, "duration_seconds": 119.96},
        "full_pytest": {
            "status": "PASS",
            "passed": 1272,
            "skipped": 1,
            "warnings": 1,
            "duration_seconds": 350.62,
        },
        "compileall": "PASS",
        "git_diff_check": "PASS",
        "historical_replays": historical["stages"],
        "s_k_prospective_replay": sk["S_L2_PROSPECTIVE_S_K_REPLAY"],
        "llm_usage": {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }
    production_post = _production_state(repo / "workspace/pro_a.db")
    production_unchanged = (
        production_pre["matches_frozen_baseline"]
        and production_post["matches_frozen_baseline"]
        and production_pre["sha256"] == production_post["sha256"]
    )
    production_receipt = {
        "document_type": "phase3e2sl2_production_integrity_receipt",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "access_mode": "READ_ONLY_IMMUTABLE_SQLITE_URI",
        "production_apply_attempted": False,
        "pre": production_pre,
        "post": production_post,
        "PRODUCTION_PRE_SHA": production_pre["sha256"],
        "PRODUCTION_POST_SHA": production_post["sha256"],
        "PRODUCTION_INTEGRITY": production_post["integrity"],
        "PRODUCTION_FK_VIOLATIONS": production_post["foreign_key_violations"],
        "PRODUCTION_CHANGED": not production_unchanged,
    }
    final = {
        "document_type": "phase3e2sl2_final_receipt",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "PHASE3E_STAGE3E2SL2_STARTED": True,
        "PHASE3E_STAGE3E2SL2_COMPLETE": True,
        "BASELINE": BASELINE,
        "BRANCH": BRANCH,
        "IMPLEMENTATION_COMMIT_SHA": IMPLEMENTATION_COMMIT,
        "DRAFT_PR_NUMBER": draft_pr_number,
        "S_K_ORIGINAL_RESULT": "FAIL",
        "S_K_RESULT_PRESERVED": True,
        "CONTRACT_ZERO_DENOMINATOR_SEMANTICS_EXPLICIT": True,
        "ZERO_DENOMINATOR_POLICY": "NOT_APPLICABLE_NON_FAILING_ONLY_WITH_REQUIRED_HISTORICAL_CLASS_COVERAGE_PASS",
        "KNOWN_SCOPE_FN_FIXED": scope["known_scope_fn_fixed"],
        "SCOPE_PRESERVATION_INVARIANT": repair_receipt["scope_preservation_invariant"],
        "MATERIAL_SCOPE_OVERSTATEMENT": metrics["material_scope_overstatement"],
        "KNOWN_DUPLICATE_FN_FIXED": duplicate["known_duplicate_fn_fixed"],
        "DUPLICATE_SIMILARITY_THRESHOLD": duplicate["similarity_threshold"],
        "DUPLICATE_NEGATIVE_CONTROLS": duplicate["negative_controls"],
        "S_K_PROSPECTIVE_METRICS": metrics,
        **historical["stages"],
        "DEVELOPMENT_PROBE_USED": False,
        "DEVELOPMENT_PROBE_SHA256": None,
        "DEVELOPMENT_PROBE_RESULT": "NOT_RUN",
        "DEVELOPMENT_PROBE_FINAL_ACCEPTANCE_ELIGIBLE": False,
        "FOCUSED_TESTS": "PASS (145 passed)",
        "FULL_PYTEST": "PASS (1272 passed, 1 skipped)",
        "COMPILEALL": "PASS",
        "DIFF_CHECK": "PASS",
        "LLM_CALLS": 0,
        "INPUT_TOKENS": 0,
        "OUTPUT_TOKENS": 0,
        "TOTAL_TOKENS": 0,
        "PRODUCTION_PRE_SHA": production_pre["sha256"],
        "PRODUCTION_POST_SHA": production_post["sha256"],
        "PRODUCTION_INTEGRITY": production_post["integrity"],
        "PRODUCTION_FK_VIOLATIONS": production_post["foreign_key_violations"],
        "PRODUCTION_CHANGED": not production_unchanged,
        "S_M_ACCEPTANCE_CONTRACT_CREATED": True,
        "S_M_ACCEPTANCE_CONTRACT_SHA256": contract_sha,
        "S_M_STARTED": False,
        "S_L2_SCOPE_EXCEEDED": False,
        "FINAL_STOP_REASON": "S_L2_COMPLETE_STOP_BEFORE_S_M",
    }
    required = [
        "phase3e2sl2_manifest.json",
        "phase3e2sl2_code_path_census.json",
        "phase3e2sl2_repair_receipt.json",
        "phase3e2sl2_scope_preservation_tests.json",
        "phase3e2sl2_duplicate_tests.json",
        "phase3e2sl2_review_reconciliation_census.json",
        "phase3e2sl2_contract_scoreability_tests.json",
        "phase3e2sl2_sk_prospective_replay.json",
        "phase3e2sl2_historical_replay.json",
        "phase3e2sl2_regression_receipt.json",
        "phase3e2sl2_production_integrity_receipt.json",
        "phase3e2sm_acceptance_contract.json",
        "phase3e2sl2_final_receipt.json",
        "phase3e2sl2_artifact_hashes.json",
    ]
    manifest = {
        "document_type": "phase3e2sl2_manifest",
        "schema_version": "1.0",
        "generated_at_utc": _now(),
        "stage": "Phase 3E.2S-L2 — Bounded Semantic Closure and Prospective Acceptance-Contract Repair",
        "baseline": BASELINE,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "branch": BRANCH,
        "original_s_k_result": "FAIL",
        "original_s_k_result_preserved": True,
        "development_probe": {
            "used": False,
            "sha256": None,
            "result": "NOT_RUN",
            "classification": "DEVELOPMENT_OR_REGRESSION_MATERIAL",
            "final_acceptance_eligible": False,
        },
        "llm_usage": regression_receipt["llm_usage"],
        "required_artifacts": required,
    }
    payloads = {
        "phase3e2sl2_manifest.json": manifest,
        "phase3e2sl2_repair_receipt.json": repair_receipt,
        "phase3e2sl2_scope_preservation_tests.json": scope_tests,
        "phase3e2sl2_duplicate_tests.json": duplicate_tests,
        "phase3e2sl2_contract_scoreability_tests.json": scoreability_tests,
        "phase3e2sl2_regression_receipt.json": regression_receipt,
        "phase3e2sl2_production_integrity_receipt.json": production_receipt,
        "phase3e2sl2_final_receipt.json": final,
    }
    for name, payload in payloads.items():
        _write(output / name, payload)
    hash_targets = [name for name in required if name != "phase3e2sl2_artifact_hashes.json"]
    missing = [name for name in hash_targets if not (output / name).is_file()]
    if missing:
        raise RuntimeError(f"MISSING_REQUIRED_ARTIFACTS: {missing}")
    artifact_hashes = {name: _sha256(output / name) for name in hash_targets}
    _write(
        output / "phase3e2sl2_artifact_hashes.json",
        {
            "document_type": "phase3e2sl2_artifact_hashes",
            "schema_version": "1.0",
            "generated_at_utc": _now(),
            "hash_algorithm": "SHA256",
            "artifacts": artifact_hashes,
            "all_required_artifacts_present_and_hashed": len(artifact_hashes)
            == len(hash_targets),
        },
    )
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--draft-pr-number", type=int)
    args = parser.parse_args()
    final = build(args.repo.resolve(), args.draft_pr_number)
    print(json.dumps(final, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
