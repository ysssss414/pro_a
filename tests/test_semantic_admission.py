from __future__ import annotations

import json
from pathlib import Path

import pytest

from pro_a.semantic_admission import (
    ADMISSIBLE,
    BLOCKED,
    REVIEW_REQUIRED,
    claim_atomicity_admission_guard,
    claim_nature_consistency_guard,
    evaluate_semantic_admission,
    guard_configuration_sha256,
    is_explicit_bound_affirmation,
    is_question_premise,
    join_permitted_support_regions,
    number_and_time_provenance_guard,
    number_time_tokens,
    precision_sensitive_tokens,
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


@pytest.mark.parametrize(
    ("text", "value", "unit"),
    [
        ("营收为54.56亿元。", "54.56", "亿元"),
        ("费用为320万元。", "320", "万元"),
        ("规模达到1.2万亿元。", "1.2", "万亿元"),
        ("速率为7200 MT/s。", "7200", "MT/s"),
        ("链路达到64GT/s。", "64", "GT/s"),
        ("容量为1.6TB。", "1.6", "TB"),
        ("缓存为3GB。", "3", "GB"),
    ],
)
def test_quantity_and_unit_are_one_semantic_token(text, value, unit):
    tokens = number_time_tokens(text)
    assert tokens == [{"token": f"{value}{unit}", "value": value, "unit": unit, "kind": "QUANTITY"}]


def test_chinese_unit_only_phrases_are_not_numeric_facts():
    assert number_time_tokens("亿元和万元均为计量单位。") == []
    assert number_time_tokens("投资额超过十亿元。") == [
        {"token": "十亿元", "value": "十亿元", "unit": "", "kind": "CHINESE_NUMBER"}
    ]


def test_value_only_quantity_anchor_requires_review_but_absent_value_blocks():
    uncertain_unit = number_and_time_provenance_guard(
        statement="接口速率为7200 MT/s。",
        permitted_support_text="接口速率达到7200 GT/s。",
        support_region_authoritative=True,
    )
    absent_value = number_and_time_provenance_guard(
        statement="接口速率为7200 MT/s。",
        permitted_support_text="接口速率达到6400 MT/s。",
        support_region_authoritative=True,
    )
    bounded_excerpt = number_and_time_provenance_guard(
        statement="接口速率为7200 MT/s。",
        permitted_support_text="该接口正在验证。",
        support_region_authoritative=True,
        support_region_exhaustive=False,
    )
    assert uncertain_unit["status"] == REVIEW_REQUIRED
    assert uncertain_unit["reason_codes"] == ["NUMERIC_UNIT_REVIEW_REQUIRED"]
    assert absent_value["status"] == BLOCKED
    assert bounded_excerpt["status"] == REVIEW_REQUIRED


def test_compound_technical_identifiers_are_precision_tokens_not_numbers():
    statement = "DDR5、RCD 04、CXL 3.1、CXL3.1 Type 3、CXL 4.0、PCIe 5.0和PCIe 6.x。"
    precision = precision_sensitive_tokens(statement)
    assert [item["token"] for item in precision] == [
        "DDR5",
        "RCD 04",
        "CXL 3.1",
        "CXL3.1 Type 3",
        "CXL 4.0",
        "PCIe 5.0",
        "PCIe 6.x",
    ]
    assert number_time_tokens(statement) == []


def test_compound_identifier_requires_the_full_anchored_span():
    anchored = precision_token_provenance_guard(
        statement="该芯片采用CXL3.1 Type 3标准。",
        permitted_support_text="该产品基于 CXL3.1 Type 3 标准设计。",
        support_region_authoritative=True,
    )
    unsafe_prefix = precision_token_provenance_guard(
        statement="该芯片采用CXL3.1 Type 3标准。",
        permitted_support_text="该产品基于CXL3.1 Type 4标准。",
        support_region_authoritative=True,
    )
    assert anchored["status"] == ADMISSIBLE
    assert unsafe_prefix["status"] == BLOCKED


def test_distinct_support_regions_do_not_create_or_break_token_boundaries():
    support = join_permitted_support_regions(["DDR5", "AI产业需求增加"])
    result = precision_token_provenance_guard(
        statement="DDR5需求增加。",
        permitted_support_text=support,
        support_region_authoritative=True,
    )
    assert result["status"] == ADMISSIBLE
    split_token = join_permitted_support_regions(["DDR", "5需求增加"])
    result = precision_token_provenance_guard(
        statement="DDR5需求增加。",
        permitted_support_text=split_token,
        support_region_authoritative=True,
    )
    assert result["status"] == BLOCKED


@pytest.mark.parametrize(
    "statement",
    [
        "预计公司实现营收80亿元，实现归母净利润40亿元。",
        "产品已量产，最高支持7200 MT/s。",
        "第二代开始出货，第三代实现量产，第四代正在送样。",
        "当前可用于高速外设互连，未来还可切换至另一协议模式。",
        "前三家合计占据90%市场，公司以35%排名第一。",
    ],
)
def test_atomicity_guard_surfaces_independently_reviewable_predicates(statement):
    result = claim_atomicity_admission_guard(statement=statement)
    assert result["status"] == REVIEW_REQUIRED
    assert result["details"]["claim_text_rewritten"] is False
    assert result["details"]["automatic_split_authorized"] is False


@pytest.mark.parametrize(
    "statement",
    [
        "2026至2028年收入分别为10、12、15亿元。",
        "市场规模将由10亿元增长至20亿元，复合增长率为20%。",
        "产品速率由6400 MT/s提升至7200 MT/s。",
        "预计价格区间为10至15元。",
    ],
)
def test_atomicity_guard_keeps_single_series_ranges_and_comparisons(statement):
    assert claim_atomicity_admission_guard(statement=statement)["status"] == ADMISSIBLE


@pytest.mark.parametrize(
    ("statement", "nature"),
    [
        ("产品已储备至第五代，第六代正在研发中。", "company_guidance"),
        ("预计第三代产品将实现14000 MT/s。", "fact"),
        ("未来性能提升可能超过30%。", "data"),
        ("若产能持续紧张，公司可能无法响应订单。", "fact"),
        ("该技术国际领先。", "fact"),
        ("2024年市场尚处于早期，预计2030年规模达到20亿元。", "broker_forecast"),
    ],
)
def test_nature_guard_surfaces_temporal_or_judgment_inconsistency(statement, nature):
    result = claim_nature_consistency_guard(statement=statement, nature=nature)
    assert result["status"] == REVIEW_REQUIRED
    assert result["details"]["nature_mutated"] is False


def test_nature_guard_does_not_flag_a_coherent_broker_forecast():
    result = claim_nature_consistency_guard(
        statement="预计2026至2028年营收分别达到10、12、15亿元。",
        nature="broker_forecast",
    )
    assert result["status"] == ADMISSIBLE


def test_combined_admission_exposes_all_six_pure_guards():
    result = evaluate_semantic_admission(
        statement="产品已量产，最高支持7200 MT/s。",
        attributed_to="开源证券",
        permitted_support_text="产品已量产，最高支持7200 MT/s。",
        support_region_authoritative=True,
        nature="data",
    )
    assert {
        "question_premise_guard",
        "precision_token_guard",
        "number_time_guard",
        "subject_scope_guard",
        "atomicity_guard",
        "nature_consistency_guard",
    } <= result.keys()
    assert result["atomicity_guard"]["status"] == REVIEW_REQUIRED
    assert result["overall_guard_disposition"] == REVIEW_REQUIRED


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
