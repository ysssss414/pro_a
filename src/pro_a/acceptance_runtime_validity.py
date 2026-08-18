from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SEMANTIC_FAILURE_CATEGORIES = {
    "relation_candidate_validation_rejection",
    "node_match_validation_rejection",
    "impact_validation_exhausted",
    "attribution_validation",
    "evidence_validation",
    "direction_validation",
    "unsupported_entity_validation",
    "required_field_validation",
    "unknown_node_reference",
    "zero_valid_relations",
}

NONTERMINAL_STATES = {"", "queued", "running", "pending", "retry"}
REQUIRED_GLOBAL_CHECKS = (
    "launch_gate_passed",
    "code_unchanged",
    "gold_unread",
    "production_db_immutable",
    "raw_sources_immutable",
    "ima_off",
)


@dataclass
class RuntimeValidityDecision:
    passed: bool
    decision: str
    semantic_failures: list[dict[str, Any]]
    infrastructure_blockers: list[dict[str, Any]]


def _blocker(item: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {**dict(item), "runtime_validity_reason": reason}


def evaluate_runtime_validity(
    source_results: Sequence[Mapping[str, Any]],
    global_checks: Mapping[str, bool],
) -> RuntimeValidityDecision:
    """Classify execution trustworthiness without grading model semantics."""
    semantic_failures: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    check_names = [
        *REQUIRED_GLOBAL_CHECKS,
        *(name for name in global_checks if name not in REQUIRED_GLOBAL_CHECKS),
    ]
    for name in check_names:
        if global_checks.get(name) is not True:
            blockers.append({
                "category": name,
                "runtime_validity_reason": "global runtime safety check failed",
            })

    for source in source_results:
        source_name = str(source.get("source") or "")
        state = str(source.get("terminal_runtime_state") or "")
        if source.get("terminal") is not True or state in NONTERMINAL_STATES:
            blockers.append({
                "source": source_name,
                "category": "nonterminal_state",
                "runtime_validity_reason": "source is not in a terminal runtime state",
            })
        if source.get("unresolved_retry_ids"):
            blockers.append({
                "source": source_name,
                "category": "unresolved_retry",
                "retry_ids": list(source["unresolved_retry_ids"]),
                "runtime_validity_reason": "source has unresolved retry state",
            })
        if source.get("audit_complete") is not True:
            blockers.append({
                "source": source_name,
                "category": "missing_audit",
                "runtime_validity_reason": "source audit is incomplete",
            })
        if source.get("observability_complete") is not True:
            blockers.append({
                "source": source_name,
                "category": "missing_observability",
                "runtime_validity_reason": "source observability is incomplete",
            })
        if source.get("result_determinable") is not True:
            blockers.append({
                "source": source_name,
                "category": "indeterminate_result",
                "runtime_validity_reason": "source result cannot be determined reliably",
            })

        for raw_failure in source.get("failures") or []:
            failure = dict(raw_failure)
            failure.setdefault("source", source_name)
            category = failure.get("category")
            if category not in SEMANTIC_FAILURE_CATEGORIES:
                reason = (
                    "infrastructure execution failure"
                    if category in {
                        "transport_failure", "parser_runtime_crash", "unresolved_retry",
                        "missing_audit", "missing_observability", "code_drift", "gold_leak",
                        "production_db_mutation", "raw_source_mutation", "persistence_failure",
                        "state_machine_failure", "indeterminate_result",
                    }
                    else "unclassified failure category"
                )
                blockers.append(_blocker(failure, reason))
                continue
            if failure.get("terminal") is not True:
                blockers.append(_blocker(failure, "semantic failure is not terminal"))
                continue
            if failure.get("audit_complete", True) is not True:
                blockers.append(_blocker(failure, "semantic failure audit is incomplete"))
                continue
            if failure.get("observability_complete", True) is not True:
                blockers.append(_blocker(failure, "semantic failure observability is incomplete"))
                continue
            if category == "impact_validation_exhausted" and (
                int(failure.get("recovery_attempts_executed", -1))
                < int(failure.get("configured_recovery_attempts", 0))
            ):
                blockers.append(_blocker(failure, "configured recovery did not execute"))
                continue
            semantic_failures.append(failure)

    passed = not blockers
    return RuntimeValidityDecision(
        passed=passed,
        decision="PASS" if passed else "TEST_INFRASTRUCTURE_BLOCKER",
        semantic_failures=semantic_failures,
        infrastructure_blockers=blockers,
    )
