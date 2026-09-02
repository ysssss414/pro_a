from __future__ import annotations

import json
from pathlib import Path

import pytest

from pro_a.semantic_admission import (
    ADMISSIBLE,
    BLOCKED,
    REVIEW_REQUIRED,
    evaluate_semantic_admission,
    guard_configuration_sha256,
    is_explicit_bound_affirmation,
    is_question_premise,
    number_and_time_provenance_guard,
    precision_token_provenance_guard,
    question_premise_admission_guard,
    subject_scope_anchor_guard,
)
from pro_a.pilot3_semantic_admission_replay import (
    derive_turn_provenance,
    split_transcript_turns,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "semantic_admission_guard_cases.json"
FIXTURES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_guard_configuration_is_stable_and_generic():
    assert len(guard_configuration_sha256()) == 64
    serialized = json.dumps(FIXTURES, ensure_ascii=False)
    for forbidden in ("PTFE", "Rubin", "CLM_", "PILOT_"):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURES["cases"] if "expected_question_status" in case],
    ids=lambda case: case["id"],
)
def test_generic_question_premise_fixtures(case):
    result = question_premise_admission_guard(
        supporting_turn_roles=case["supporting_turn_roles"],
        attributed_role="ANSWERER",
        adoption_status=case["adoption_status"],
    )
    assert result["status"] == case["expected_question_status"]


def test_unrelated_affirmative_word_does_not_adopt_a_premise():
    assert is_explicit_bound_affirmation("对。") is True
    assert is_explicit_bound_affirmation("是的！") is True
    assert is_explicit_bound_affirmation("对，这个材料以后再讨论。") is False
    result = question_premise_admission_guard(
        supporting_turn_roles=["QUESTIONER"],
        attributed_role="ANSWERER",
        adoption_status="NOT_FOUND",
    )
    assert result["status"] == BLOCKED


def test_question_morphology_detection_is_repeatable():
    for _ in range(3):
        assert is_question_premise("您觉得该方案可行吗？") is True
        assert is_question_premise("该方案仍在验证阶段。") is False


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURES["cases"] if "expected_precision_status" in case],
    ids=lambda case: case["id"],
)
def test_generic_precision_token_fixtures(case):
    result = precision_token_provenance_guard(
        statement=case["statement"],
        permitted_support_text=case["support"],
        support_region_authoritative=True,
        classified_named_entities=case.get("classified_named_entities", []),
    )
    assert result["status"] == case["expected_precision_status"]


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURES["cases"] if "expected_number_status" in case],
    ids=lambda case: case["id"],
)
def test_generic_number_and_year_fixtures(case):
    result = number_and_time_provenance_guard(
        statement=case["statement"],
        permitted_support_text=case["support"],
        support_region_authoritative=True,
    )
    assert result["status"] == case["expected_number_status"]


def test_relative_date_invention_is_blocked_without_new_resolution_rules():
    result = number_and_time_provenance_guard(
        statement="该产品将在明年4月交付。",
        permitted_support_text="该产品将在4月交付。",
        support_region_authoritative=True,
    )
    assert result["status"] == BLOCKED
    assert result["details"]["new_date_resolution_rule_used"] is False


def test_grouped_numeric_scope_routes_to_review_not_automatic_block():
    result = evaluate_semantic_admission(
        statement="甲、乙等业务合计增长70%。",
        attributed_to="回答者",
        permitted_support_text="甲、乙等业务合计增长70%。",
        support_region_authoritative=True,
        supporting_turn_roles=["ANSWERER"],
    )
    assert result["number_time_guard"]["status"] == REVIEW_REQUIRED
    assert result["subject_scope_guard"]["status"] == REVIEW_REQUIRED
    assert result["overall_guard_disposition"] == REVIEW_REQUIRED


def test_subject_scope_blocks_only_explicit_exhaustive_disjoint_anchors():
    mismatch = subject_scope_anchor_guard(
        claim_subject_anchors=["material"],
        source_subject_anchors=["cabinet"],
        source_subjects_exhaustive=True,
    )
    unresolved = subject_scope_anchor_guard()
    assert mismatch["status"] == BLOCKED
    assert unresolved["status"] == ADMISSIBLE
    assert "NO_HIGH_CONFIDENCE" in unresolved["reason_codes"][0]


def test_non_authoritative_support_degrades_missing_provenance_to_review():
    precision = precision_token_provenance_guard(
        statement="ZX-42等级已经送样。",
        permitted_support_text="",
        support_region_authoritative=False,
    )
    number = number_and_time_provenance_guard(
        statement="该项目将在2031年量产。",
        permitted_support_text="",
        support_region_authoritative=False,
    )
    assert precision["status"] == REVIEW_REQUIRED
    assert number["status"] == REVIEW_REQUIRED


def test_generic_transcript_turn_derivation_is_conservative():
    transcript = """发言人   01:00
您认为该方案已经量产了吗？谢谢。

发言人   01:20
目前仍在验证，还没有量产。

发言人   02:00
后续再讨论供应安排。
"""
    turns = split_transcript_turns(transcript)
    assert [turn.role for turn in turns] == ["QUESTIONER", "ANSWERER", "UNKNOWN"]

    decision = {
        "immutable_evidence_excerpt": "您认为该方案已经量产了吗？",
        "nearest_deterministic_source_region_reference": None,
    }
    result = derive_turn_provenance(
        decision=decision,
        quote_item={"resolved_locator": None},
        turns=turns,
        preferred_locator=None,
    )
    assert result["supporting_turn_roles"] == ["QUESTIONER"]
    assert result["answer_adoption_status"] == "NOT_FOUND"
    assert result["speaker_identity_available"] is False
