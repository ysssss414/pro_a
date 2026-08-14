from __future__ import annotations

import json
from pathlib import Path

from pro_a.analyzer import SourceAnalysis
from pro_a.cli import main
from pro_a.pipeline import IngestionPipeline

from stability_helpers import add_source_and_claim, make_config


class AuditAnalyzer:
    available = True

    def __init__(self, node_id: str):
        self.node_id = node_id

    def analyze_source(self, filename, text, mode):
        return SourceAnalysis(
            source_metadata={
                "title": "中际旭创产能更新",
                "author": "测试研究员",
                "organization": "测试机构",
                "publication_time": "2026-08-14",
                "source_rank": "A",
                "source_origin_type": "secondary",
                "summary": "产能与需求更新",
            },
            node_matches=[{
                "node_id": self.node_id, "role": "primary", "confidence": 0.96,
                "reason": "公司主体明确", "evidence_excerpt": "中际旭创",
                "evidence_validated": True,
                "validation": {
                    "evidence_validated": True,
                    "match_method": "normalized_exact_substring",
                    "normalized_excerpt": "中际旭创",
                    "normalized_start": 0,
                    "normalized_end": 4,
                },
            }],
            node_candidates=[{
                "canonical_name": "800G光模块", "primary_type": "Product", "aliases": [],
                "description": "高速光模块产品", "suggested_parent_node_ids": [],
                "reason": "资料反复讨论的独立产品", "confidence": 0.82,
                "candidate_kind": "normal", "quality_eligible": True,
            }],
            claims=[{
                "statement": "中际旭创预计2026年产能增长20%。",
                "nature": "company_guidance",
                "related_node_ids": [self.node_id],
                "related_candidate_names": ["800G光模块"],
                "fact_time": "2026",
                "evidence_pointer": "[[PARA:1]]",
                "evidence_excerpt": "预计2026年产能增长20%",
                "attributed_to": "中际旭创",
                "evidence_validated": True,
                "scope": "公司产能",
                "assumption": "需求按期释放",
                "status": "current",
                "confidence": 0.9,
                "novelty_level": "N2",
                "structured": {},
                "validation": {"evidence_validated": True, "model_confidence": 0.9},
            }],
            source_references=[],
        )

    def backfill_candidate_claims(self, candidates, claims):
        return {"800g光模块": [0]}

    def compare_claims(self, node, new_claims, history):
        return {
            "comparisons": [{
                "new_claim_id": new_claims[0]["claim_id"],
                "classification": "updates",
                "related_claim_id": history[0]["claim_id"],
                "reason": "同口径的后续更新",
                "scope_normalization": "均为公司产能",
                "independent_evidence": True,
            }]
        }

    def review_impact(self, node, current_view_md, evidence, context):
        claim_ids = [item["claim_id"] for item in evidence if item.get("claim_id")]
        return {
            "requires_change": True,
            "change_level": "initial",
            "reason": "首次建立产能判断",
            "scope_normalization_notes": ["公司口径"],
            "evidence_sufficiency": {"sufficient": True, "reason": "首次建立"},
            "proposed_current_view": {
                "one_line_conclusion": "中际旭创公司指引显示其产能处于扩张期",
                "core_logic": [f"中际旭创预计需求增长带动扩产（{claim_ids[0]}）。"],
                "key_facts": [f"中际旭创预计2026年产能增长20%（{claim_ids[0]}）。"],
                "core_disagreements": [],
                "assumptions_to_verify": [],
                "investment_implication": "中际旭创的投资含义取决于扩产兑现与需求持续性。",
                "major_risks": ["中际旭创扩产进度或需求可能低于公司指引。"],
                "knowledge_gaps": [],
                "key_watch_items": ["跟踪中际旭创季度产能与出货兑现情况。"],
                "recent_change": "首次建立中际旭创产能判断。",
                "evidence_claim_ids": claim_ids,
                "type_specific": {},
            },
            "knowledge_gaps": [{
                "title": "产能兑现节奏", "description": "需要跟踪季度出货",
                "source_claim_ids": claim_ids, "freshness_due": "2026-12-31",
            }],
            "research_question_candidates": [{
                "canonical_name": "2026年产能能否按期兑现？",
                "question": "2026年产能能否按期兑现？",
                "importance": "可能改变产能判断",
                "related_node_ids": [self.node_id],
                "what_would_change_my_mind": "季度出货持续低于计划",
                "reason": "核心假设仍待验证",
            }],
        }


def test_standard_ingestion_receipt_and_source_show_are_auditable(tmp_path: Path, capsys):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("中际旭创", "Entity")
    add_source_and_claim(
        db,
        source_id="SRC_HISTORY",
        claim_id="CLM_HISTORY",
        node_id=node_id,
        source_rank="B",
        origin_type="secondary",
        confidence=0.75,
    )
    pipeline = IngestionPipeline(cfg, db)
    analyzer = AuditAnalyzer(node_id)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "capacity_update.txt"
    request.write_text(
        "中际旭创管理层预计2026年产能增长20%，需求增长带动扩产。",
        encoding="utf-8",
    )

    result = pipeline.process_all()[0]

    assert result["status"] == "analyzed"
    assert result["job_id"]
    audit = result["audit"]
    assert audit["source"]["source_rank"] == "A"
    assert audit["source"]["origin_type"] == "secondary"
    assert audit["nodes"][0]["canonical_name"] == "中际旭创"
    assert len(audit["node_proposals"]) == 1
    assert len(audit["claims"]) == 1
    assert audit["claims"][0]["nature"] == "company_guidance"
    assert audit["claims"][0]["evidence_validated"] is True
    assert len(audit["claim_relations"]) == 1
    assert audit["claim_relations"][0]["relation_type"] == "updates"
    assert len(audit["impact_reviews"]) == 1
    assert audit["impact_reviews"][0]["status"] == "proposed"
    assert len(audit["current_view_proposals"]) == 1
    assert len(audit["knowledge_gaps"]) == 1
    assert len(audit["research_question_candidates"]) == 1

    receipt = Path(result["receipt_path"])
    receipt_text = receipt.read_text(encoding="utf-8")
    for heading in [
        "## Source Metadata",
        "## Existing Nodes",
        "## Candidate Node Proposals",
        "## Claims",
        "## Historical Compare",
        "## Impact Reviews",
        "## Current View Proposals",
        "## Knowledge Gaps",
        "## Research Question Candidates",
    ]:
        assert heading in receipt_text
    assert "中际旭创预计2026年产能增长20%" in receipt_text

    main(["--config", str(cfg.config_path), "source", "show", result["source_id"]])
    shown = json.loads(capsys.readouterr().out)
    assert shown["source"]["source_id"] == result["source_id"]
    assert shown["claims"][0]["evidence_validated"] is True
    assert shown["impact_reviews"][0]["result"]["change_level"] == "initial"
