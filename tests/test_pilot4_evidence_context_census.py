from __future__ import annotations

import pytest

from pro_a.corpus_pilot import PilotError, _bounded_context_candidates
from scripts.phase3c_pilot4_evidence_context_census import (
    _evidence_window,
    _local_subspan_probe,
    census_claims,
)


def _claim(evidence: str = "证据", *, status: str = "resolved") -> dict:
    locator = {"status": status}
    if status == "resolved":
        locator["locator"] = "PAGE:1"
    return {
        "claim_id": "CLM_GENERIC",
        "statement": "通用测试 Claim",
        "evidence_excerpt": evidence,
        "attributed_to": "",
        "validation": {"source_locator": locator},
    }


def _single(page: str, evidence: str = "证据") -> dict:
    return census_claims([_claim(evidence)], [("PAGE:1", page)])


def test_census_valid_context_inside_500_passes():
    result = _single("前文。证据。后文。")

    assert result["metrics"]["validator_pass"] == 2
    assert result["metrics"]["validator_fail"] == 0
    assert result["metrics"]["claims_with_any_context_candidate"] == 1


def test_census_candidate_at_exactly_500_passes():
    result = _single("证据" + "隔" * 500 + "\n\n后文。")
    attempts = result["claims"][0]["candidate_attempts"]

    assert len(attempts) == 1
    assert attempts[0]["minimum_gap"] == 500
    assert attempts[0]["within_500"] is True
    assert attempts[0]["validator_outcome"] == "PASS"


def test_census_candidate_at_501_fails_closed():
    page = "证据" + "隔" * 501 + "\n\n后文。"
    result = _single(page)
    attempt = result["claims"][0]["candidate_attempts"][0]

    assert attempt["minimum_gap"] == 501
    assert attempt["within_500"] is False
    assert attempt["validator_outcome"] == "FAIL"
    assert attempt["root_category"] == "OUTSIDE_BOUNDED_WINDOW"
    with pytest.raises(PilotError, match="outside the bounded window"):
        _bounded_context_candidates([("PAGE:1", page)], "PAGE:1", "证据")


def test_census_records_normalized_empty_without_emitting_it():
    result = _single("前文。证据。 。后文。")
    attempts = result["claims"][0]["candidate_attempts"]
    empty = next(item for item in attempts if item["root_category"] == "EMPTY_NORMALIZATION")

    assert empty["candidate_raw_text"] == "。"
    assert empty["candidate_normalized_text"] == ""
    assert empty["generator_outcome"] == "FILTERED_NORMALIZED_EMPTY"
    assert empty["validator_outcome"] == "NOT_RUN_FILTERED"
    assert result["metrics"]["filtered_by_root_category"] == {"EMPTY_NORMALIZATION": 1}


def test_census_duplicate_normalized_occurrence_uses_nearest_pair():
    page = "谢谢。" + "远" * 600 + "。谢谢。证据。后文。"
    result = _single(page)
    before = next(
        item for item in result["claims"][0]["candidate_attempts"]
        if item["candidate_direction"] == "before"
    )

    assert before["duplicate_occurrence_present"] is True
    assert before["validator_outcome"] == "PASS"
    assert before["minimum_gap"] <= 500


def test_census_records_no_context_candidate():
    result = _single("证据。")
    claim = result["claims"][0]

    assert claim["candidate_attempts"] == []
    assert claim["no_context_candidate"] == {
        "status": "NO_CONTEXT_CANDIDATE",
        "code": "no_adjacent_segment",
        "detail": "no prior or following parsed segment/page-boundary candidate exists",
    }


def test_census_large_segment_with_evidence_near_beginning_finds_local_subspan():
    result = _single("证据" + "中" * 600 + "\n\n后文。")
    attempt = result["claims"][0]["candidate_attempts"][0]

    assert attempt["root_category"] == "OUTSIDE_BOUNDED_WINDOW"
    assert attempt["minimum_gap"] == 600
    assert attempt["representation_granularity_probe"][
        "valid_source_local_subspan_within_500_exists"
    ] is True
    assert len(attempt["representation_granularity_probe"]["selected"]["normalized_text"]) >= 16


def test_census_large_segment_with_evidence_near_end_finds_local_subspan():
    result = _single("前文。\n\n" + "中" * 600 + "证据。")
    attempt = result["claims"][0]["candidate_attempts"][0]

    assert attempt["candidate_direction"] == "before"
    assert attempt["root_category"] == "OUTSIDE_BOUNDED_WINDOW"
    assert attempt["representation_granularity_probe"][
        "valid_source_local_subspan_within_500_exists"
    ] is True


def test_census_detects_valid_local_subspan_when_neighbor_segment_is_too_far():
    result = _single("证据" + "正文" * 350 + "\n\n邻段。")
    outside = result["metrics"]["outside_bounded_window"]

    assert outside["count"] == 1
    assert outside["valid_local_subspan_within_500"] == 1
    assert outside["without_found_local_subspan_within_500"] == 0


def test_census_probe_reports_truly_no_other_local_context():
    page = "证据。"
    window = _evidence_window(page, "证据。")

    assert window is not None
    assert _local_subspan_probe(page, "证据。", window) == {
        "valid_source_local_subspan_within_500_exists": False,
        "probe_scope": "raw line/chunk substrings inside the Evidence-containing segment window",
        "minimum_normalized_chars": 16,
        "selected": None,
    }


def test_census_unresolved_locator_is_not_sent_to_context_generator():
    result = census_claims([_claim(status="unresolved")], [("PAGE:1", "证据。")])
    claim = result["claims"][0]

    assert claim["candidate_attempts"] == []
    assert claim["no_context_candidate"]["code"] == "no_bindable_local_segment"
