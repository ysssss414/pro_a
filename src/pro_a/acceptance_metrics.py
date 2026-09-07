"""Prospective acceptance metrics with explicit scoreability semantics."""

from __future__ import annotations

from typing import Any


def evaluate_recall_metric(
    *,
    numerator: int,
    denominator: int,
    threshold: float,
    historical_class_coverage_pass: bool,
) -> dict[str, Any]:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("recall numerator and denominator are inconsistent")
    if not 0 <= threshold <= 1:
        raise ValueError("recall threshold must be between zero and one")
    if denominator == 0:
        return {
            "numerator": 0,
            "denominator": 0,
            "value": None,
            "threshold": threshold,
            "comparator": ">=",
            "scoreability": "NOT_APPLICABLE",
            "historical_class_coverage": (
                "PASS" if historical_class_coverage_pass else "NOT_PROVEN"
            ),
            "gate": (
                "PASS_BY_HISTORICAL_COVERAGE"
                if historical_class_coverage_pass
                else "FAIL"
            ),
        }
    value = numerator / denominator
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "threshold": threshold,
        "comparator": ">=",
        "scoreability": "SCOREABLE",
        "historical_class_coverage": (
            "PASS" if historical_class_coverage_pass else "NOT_REQUIRED_FOR_SCOREABLE_METRIC"
        ),
        "gate": "PASS" if value >= threshold else "FAIL",
    }
