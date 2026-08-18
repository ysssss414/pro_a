from __future__ import annotations

import json
from pathlib import Path

from pro_a.acceptance_runtime_validity import evaluate_runtime_validity


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "run_005_runtime_failures.json").read_text(
        encoding="utf-8"
    )
)


def source_result(*failures: dict) -> dict:
    return {
        "source": "offline replay",
        "terminal": True,
        "terminal_runtime_state": "terminal",
        "unresolved_retry_ids": [],
        "audit_complete": True,
        "observability_complete": True,
        "result_determinable": True,
        "failures": list(failures),
    }


def safe_global_checks() -> dict[str, bool]:
    return {
        "launch_gate_passed": True,
        "code_unchanged": True,
        "gold_unread": True,
        "production_db_immutable": True,
        "raw_sources_immutable": True,
        "ima_off": True,
    }


def test_run_005_terminal_impact_semantic_exhaustion_is_scoreable_offline_replay():
    semantic_failures = [
        item for item in FIXTURE["impact_failures"]
        if item["category"] == "impact_validation_exhausted"
    ]

    decision = evaluate_runtime_validity(
        [source_result(*semantic_failures)], safe_global_checks()
    )

    assert decision.passed is True
    assert decision.decision == "PASS"
    assert {item["object_id"] for item in decision.semantic_failures} == {
        item["object_id"] for item in semantic_failures
    }
    assert decision.infrastructure_blockers == []


def test_run_005_transport_reset_remains_an_infrastructure_blocker_offline_replay():
    decision = evaluate_runtime_validity(
        [source_result(*FIXTURE["impact_failures"])], safe_global_checks()
    )

    assert decision.passed is False
    assert decision.decision == "TEST_INFRASTRUCTURE_BLOCKER"
    assert len(decision.semantic_failures) == 10
    assert [item["object_id"] for item in decision.infrastructure_blockers] == [
        "IMP_20260818_37BB666B"
    ]


def test_relation_node_and_zero_relation_semantic_results_do_not_fail_validity():
    failures = [
        {"category": "relation_candidate_validation_rejection", "terminal": True},
        {"category": "node_match_validation_rejection", "terminal": True},
        {"category": "direction_validation", "terminal": True},
        {"category": "evidence_validation", "terminal": True},
        {"category": "zero_valid_relations", "terminal": True},
    ]

    decision = evaluate_runtime_validity([source_result(*failures)], safe_global_checks())

    assert decision.passed is True
    assert len(decision.semantic_failures) == len(failures)


def test_incomplete_semantic_recovery_is_an_infrastructure_blocker():
    failure = {
        "category": "impact_validation_exhausted",
        "terminal": True,
        "configured_recovery_attempts": 2,
        "recovery_attempts_executed": 1,
        "audit_complete": True,
        "observability_complete": True,
    }

    decision = evaluate_runtime_validity([source_result(failure)], safe_global_checks())

    assert decision.passed is False
    assert decision.infrastructure_blockers[0]["runtime_validity_reason"] == (
        "configured recovery did not execute"
    )


def test_nonterminal_missing_audit_and_unknown_failure_are_blockers():
    result = source_result({"category": "new_unclassified_failure", "terminal": True})
    result["terminal_runtime_state"] = "retry"
    result["audit_complete"] = False

    decision = evaluate_runtime_validity([result], safe_global_checks())

    reasons = {item["runtime_validity_reason"] for item in decision.infrastructure_blockers}
    assert "source is not in a terminal runtime state" in reasons
    assert "source audit is incomplete" in reasons
    assert "unclassified failure category" in reasons


def test_global_execution_safety_failure_is_a_blocker():
    checks = safe_global_checks()
    checks["gold_unread"] = False

    decision = evaluate_runtime_validity([source_result()], checks)

    assert decision.passed is False
    assert decision.infrastructure_blockers == [
        {
            "category": "gold_unread",
            "runtime_validity_reason": "global runtime safety check failed",
        }
    ]
