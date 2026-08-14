from __future__ import annotations

from pathlib import Path

import pytest

from pro_a.analyzer import Analyzer
from pro_a.llm import LLMError
from pro_a.pipeline import IngestionPipeline

from stability_helpers import make_config


class StaticLLM:
    available = True

    def __init__(self, payload):
        self.payload = payload

    def json(self, system, user):
        return self.payload


def valid_source_payload(node_id: str) -> dict:
    return {
        "source_metadata": {
            "title": "测试资料",
            "author": "研究员",
            "organization": "测试机构",
            "publication_time": "2026-08-14",
            "source_rank": "A",
            "source_origin_type": "primary",
            "summary": "测试摘要",
        },
        "node_matches": [
            {"node_id": node_id, "role": "primary", "confidence": 0.95, "reason": "明确提及"}
        ],
        "node_candidates": [],
        "claims": [
            {
                "statement": "中际旭创预计2026年产能增长20%。",
                "nature": "company_guidance",
                "related_node_ids": [node_id],
                "related_candidate_names": [],
                "fact_time": "2026",
                "evidence_pointer": "[[PARA:1]]",
                "evidence_excerpt": "预计2026年产能增长20%",
                "scope": "公司产能",
                "assumption": "",
                "status": "current",
                "confidence": 0.9,
                "novelty_level": "N2",
                "structured": {},
            }
        ],
        "source_references": [],
    }


@pytest.mark.parametrize(
    "case",
    ["node_type", "claim_nature", "claim_status", "claim_novelty", "unknown_node", "confidence"],
)
def test_source_analysis_rejects_illegal_llm_output(tmp_path: Path, case: str):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("中际旭创", "Entity")
    payload = valid_source_payload(node_id)
    if case == "node_type":
        payload["node_candidates"] = [{
            "canonical_name": "非法节点", "primary_type": "Company", "aliases": [],
            "suggested_parent_node_ids": [], "confidence": 0.8, "candidate_kind": "normal",
        }]
    elif case == "claim_nature":
        payload["claims"][0]["nature"] = "opinion"
    elif case == "claim_status":
        payload["claims"][0]["status"] = "trusted"
    elif case == "claim_novelty":
        payload["claims"][0]["novelty_level"] = "N9"
    elif case == "unknown_node":
        payload["claims"][0]["related_node_ids"] = ["NODE_NOT_REAL"]
    elif case == "confidence":
        payload["claims"][0]["confidence"] = 1.2
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    with pytest.raises(LLMError, match="Invalid LLM output"):
        analyzer.analyze_source(
            "sample.txt", "中际旭创预计2026年产能增长20%。", "standard"
        )


def test_unlocated_evidence_is_downgraded_not_high_confidence(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("中际旭创", "Entity")
    payload = valid_source_payload(node_id)
    payload["claims"][0]["evidence_excerpt"] = "原文中不存在的句子"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    analysis = analyzer.analyze_source(
        "sample.txt", "中际旭创预计2026年产能增长20%。", "standard"
    )

    claim = analysis.claims[0]
    assert claim["evidence_validated"] is False
    assert claim["status"] == "needs_review"
    assert claim["confidence"] == 0.0
    assert claim["validation"]["model_confidence"] == 0.9


def test_invalid_source_analysis_does_not_insert_claims_or_proposals(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("中际旭创", "Entity")
    payload = valid_source_payload(node_id)
    payload["claims"][0]["nature"] = "opinion"
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = StaticLLM(payload)
    request = cfg.root / "inbox" / "standard" / "invalid.txt"
    request.write_text("中际旭创预计2026年产能增长20%。", encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "failed"
    assert "Invalid LLM output" in result["error"]
    assert result["source_id"]
    assert Path(result["receipt_path"]).exists()
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 1
    assert db.one("SELECT COUNT(*) AS n FROM claims")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0
    job = db.one("SELECT source_id,status,error_text FROM processing_jobs")
    assert job["source_id"] == result["source_id"]
    assert job["status"] == "failed"
    assert "Invalid LLM output" in job["error_text"]


def test_impact_review_rejects_illegal_change_level(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("中际旭创", "Entity")
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM({
        "requires_change": True,
        "change_level": "major",
        "reason": "非法枚举",
        "evidence_sufficiency": {"sufficient": True},
        "proposed_current_view": {},
        "knowledge_gaps": [],
        "research_question_candidates": [],
    })

    with pytest.raises(LLMError, match="change_level"):
        analyzer.review_impact(db.get_node(node_id), "", [], {})
