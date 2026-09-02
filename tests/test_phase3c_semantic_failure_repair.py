from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pro_a.corpus_pilot import phase3c_prompt_repair_status
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "phase3c_semantic_repair_cases.json"
FIXTURES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
EXPECTED_PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"


def test_semantic_repair_fixtures_cover_a_through_j_without_pilot_memorization():
    cases = FIXTURES["cases"]

    assert [case["id"] for case in cases] == list("ABCDEFGHIJ")
    assert len({case["failure_class"] for case in cases}) == 10
    serialized = json.dumps(FIXTURES, ensure_ascii=False)
    for source_specific_token in ("PTFE", "Rubin", "CLM_20260831_", "PILOT_20260831_"):
        assert source_specific_token not in serialized


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda case: case["id"])
def test_each_generic_semantic_fixture_is_covered_by_the_prompt_contract(case):
    assert case["source"]
    assert case["candidate_claim"]
    assert case["expected"]
    for fragment in case["required_prompt_fragments"]:
        assert fragment in SOURCE_ANALYSIS_SYSTEM


def test_semantic_repair_prompt_snapshot_and_existing_gate_c_contract_pass():
    status = phase3c_prompt_repair_status()

    assert status["passed"] is True
    assert all(status["categories"].values())
    assert hashlib.sha256(SOURCE_ANALYSIS_SYSTEM.encode("utf-8")).hexdigest() == (
        EXPECTED_PROMPT_SHA256
    )
    assert status["prompt_sha256"] == EXPECTED_PROMPT_SHA256


def test_attribution_and_question_answer_boundaries_are_both_explicit():
    assert "不得用说话者替换 statement 中的公司" in SOURCE_ANALYSIS_SYSTEM
    assert "问句中的前提不等于回答者的陈述或判断" in SOURCE_ANALYSIS_SYSTEM
    assert "不得仅因话题连续就视为回答者采纳" in SOURCE_ANALYSIS_SYSTEM
    assert "明确肯定并清楚绑定到该前提" in SOURCE_ANALYSIS_SYSTEM


def test_evidence_fidelity_clause_is_preserved_but_not_expanded_by_semantic_fixtures():
    assert "evidence_excerpt 必须逐字复制输入原文中的一个连续片段" in SOURCE_ANALYSIS_SYSTEM
    serialized = json.dumps(FIXTURES, ensure_ascii=False)
    for evidence_repair_term in ("quote matcher", "bounded context", "Evidence Contract v2"):
        assert evidence_repair_term not in serialized
