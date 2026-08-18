from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pro_a.acceptance_preflight import run_deterministic_pytest_probe, windows_user_temp_root


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_TARGETS = (
    "tests/test_v0_2_1_knowledge_quality.py::test_source_analysis_truncation_recovers_by_splitting_only_that_chunk",
    "tests/test_relation_candidate_extraction.py::test_same_identity_candidates_merge_persistent_claims",
    "tests/test_impact_recovery.py::test_propagation_validation_failure_enters_repair_path_with_full_context",
    "tests/test_impact_recovery.py::test_retry_repairs_invalid_candidate_and_keeps_proposal_pending",
    "tests/test_impact_recovery.py::test_failed_repairs_end_in_explicit_terminal_failure_and_never_bypass_validator",
    "tests/test_llm.py::test_run_003_length_completion_records_parseability_tail_and_limits",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic R1 acceptance launch-gate probe.")
    parser.add_argument(
        "--preferred-temp-root",
        type=Path,
        default=PROJECT_ROOT / "workspace" / "r1_acceptance" / "preflight_temp",
    )
    parser.add_argument(
        "--fallback-temp-root",
        type=Path,
        default=windows_user_temp_root(),
    )
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("tests", nargs="*", default=DEFAULT_TEST_TARGETS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_deterministic_pytest_probe(
        PROJECT_ROOT,
        args.tests,
        args.preferred_temp_root,
        fallback_temp_root=args.fallback_temp_root,
        python_executable=sys.executable,
        audit_path=args.audit_output,
    )
    print(json.dumps({
        "decision": result.decision,
        "resolved_temp_path": result.temp_resolution.resolved_path,
        "selected_root_kind": result.temp_resolution.selected_root_kind,
        "fallback_used": result.temp_resolution.fallback_used,
        "canary_passed": bool(
            result.temp_resolution.canary_attempts
            and result.temp_resolution.canary_attempts[-1].success
        ),
        "pytest_exit_code": result.pytest_exit_code,
        "permission_error_detected": result.permission_error_detected,
        "audit_output": str(args.audit_output.resolve()),
    }, ensure_ascii=False))
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
