from __future__ import annotations

import copy
import json
from pathlib import Path

from pro_a.analyzer import Analyzer
from pro_a.cli import build_parser
from pro_a.db import now_iso
from pro_a.impact_recovery import ImpactRecoveryService
from pro_a.propagation import PropagationManager

from stability_helpers import make_config


class SequencedLLM:
    available = True

    def __init__(self, outputs):
        self.outputs = [copy.deepcopy(item) for item in outputs]
        self.calls = 0

    def json(self, system, user):
        self.calls += 1
        if not self.outputs:
            raise AssertionError("Unexpected extra LLM call")
        return copy.deepcopy(self.outputs.pop(0))


def add_mlcc_evidence(db, node_id: str) -> list[str]:
    ts = now_iso()
    db.execute(
        """INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,
           source_rank,origin_type,underlying_source_id,ingested_at,status,metadata_json)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "SRC_MLCC",
            "SRC_MLCC",
            "mlcc.md",
            "/mlcc.md",
            "sha-mlcc",
            "standard",
            "B",
            "secondary",
            "",
            ts,
            "analyzed",
            "{}",
        ),
    )
    claims = [
        {
            "claim_id": "CLM_PRICE",
            "statement": "昀冢科技披露其7月、8月MLCC价格环比上涨30%以上",
            "nature": "data",
            "attributed_to": "昀冢科技业绩说明会",
            "scope": "昀冢科技",
            "structured": {"company": "昀冢科技", "metric": "MLCC价格"},
        },
        {
            "claim_id": "CLM_GUIDANCE",
            "statement": "昀冢科技认为AI和存储需求叠加高容产品产能挤兑，本轮周期可能更长",
            "nature": "company_guidance",
            "attributed_to": "昀冢科技业绩说明会",
            "scope": "昀冢科技",
            "structured": {"company": "昀冢科技"},
        },
        {
            "claim_id": "CLM_BROKER",
            "statement": "财通电子团队判断国内外MLCC原厂趋势一致，AI挤出效应明显",
            "nature": "expert_judgment",
            "attributed_to": "财通电子团队",
            "scope": "MLCC行业",
            "structured": {},
        },
    ]
    for item in claims:
        db.execute(
            """INSERT INTO claims(
               claim_id,statement,nature,ingestion_time,source_id,evidence_excerpt,attributed_to,
               scope,status,confidence,structured_json,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["claim_id"],
                item["statement"],
                item["nature"],
                ts,
                "SRC_MLCC",
                item["statement"],
                item["attributed_to"],
                item["scope"],
                "current",
                0.85,
                json.dumps(item["structured"], ensure_ascii=False),
                ts,
            ),
        )
        db.execute(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            (item["claim_id"], node_id, "related"),
        )
    return [item["claim_id"] for item in claims]


def valid_initial_result(claim_ids: list[str]) -> dict:
    return {
        "requires_change": True,
        "change_level": "initial",
        "reason": "首次建立 MLCC Current View",
        "scope_normalization_notes": ["当前仅有昀冢科技单一公司样本"],
        "evidence_sufficiency": {
            "sufficient": True,
            "reason": "单一公司样本足以建立受限范围的 Initial View",
            "direct_primary_claim_ids": [],
            "decisive_primary_claim_ids": [],
            "invalidated_core_assumption": "",
            "logic_chain_failure": "",
            "conclusion_change": "",
        },
        "proposed_current_view": {
            "one_line_conclusion": (
                "MLCC单一公司样本显示价格与高容产品需求改善，但尚不足以确认全行业长期上行。"
            ),
            "core_logic": [
                "MLCC方面，昀冢科技认为AI与存储需求可能带来高容产品产能挤兑（CLM_GUIDANCE）。",
                "MLCC方面，财通电子团队判断国内外原厂趋势一致，仍需行业数据验证（CLM_BROKER）。",
            ],
            "key_facts": [
                "昀冢科技披露其7月、8月MLCC价格环比上涨30%以上（CLM_PRICE）。"
            ],
            "core_disagreements": ["MLCC公司样本能否代表行业整体供需仍待验证。"],
            "assumptions_to_verify": ["MLCC行业是否存在可持续的高容产品供需缺口。"],
            "investment_implication": (
                "对MLCC产业而言，昀冢科技公司侧Evidence可作为景气验证样本，但不能单独确认行业长周期。"
            ),
            "major_risks": ["MLCC行业结论当前依赖单一公司样本，缺少行业级交叉验证。"],
            "knowledge_gaps": ["缺少MLCC行业供需、竞争对手和下游需求量化数据。"],
            "key_watch_items": [
                "跟踪MLCC行业供需与库存数据。",
                "跟踪MLCC主要竞争对手的价格和扩产计划。",
                "跟踪MLCC下游需求变化。",
            ],
            "recent_change": "首次基于昀冢科技样本建立MLCC初始认知。",
            "evidence_claim_ids": claim_ids,
            "type_specific": {
                "applications": [],
                "demand_drivers": [
                    "昀冢科技认为AI与存储需求是MLCC潜在驱动（CLM_GUIDANCE）。"
                ],
                "supply_capacity": [
                    "昀冢科技认为高容MLCC可能存在产能挤兑（CLM_GUIDANCE）。"
                ],
                "pricing": [
                    "昀冢科技披露其7月、8月MLCC价格环比上涨30%以上（CLM_PRICE）。"
                ],
                "major_suppliers": [],
                "product_evolution": [
                    "昀冢科技认为高容MLCC是当前关注的产品方向（CLM_GUIDANCE）。"
                ],
            },
        },
        "knowledge_gaps": [],
        "research_question_candidates": [],
    }


def setup_impact(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("MLCC", "Product", ["多层陶瓷电容器"])
    claim_ids = add_mlcc_evidence(db, node_id)
    analyzer = Analyzer(cfg, db)
    manager = PropagationManager(cfg, db, analyzer)
    impact_id = manager._insert_impact(
        "BATCH_MLCC",
        "new_node_accept",
        "PROP_MLCC",
        node_id,
        "direct",
        "retry",
        {"claim_ids": claim_ids, "trigger_source_id": "SRC_MLCC"},
    )
    assert impact_id
    return cfg, db, analyzer, impact_id, claim_ids


def persist_pending_candidate(cfg, db, impact_id: str, claim_ids: list[str], candidate: dict) -> str:
    manager = PropagationManager(cfg, db, Analyzer(cfg, db))
    impact = db.one("SELECT * FROM impact_reviews WHERE impact_id=?", (impact_id,))
    context = json.loads(impact["payload_json"])
    manager._apply_initial_evidence_profile(candidate, manager._claims(claim_ids))
    proposal_id = manager._create_current_view_proposal(
        impact["node_id"],
        candidate,
        claim_ids,
        context["trigger_source_id"],
        impact["batch_id"],
        context,
        impact_id,
    )
    db.execute(
        """UPDATE impact_reviews
           SET status='proposed',proposal_id=?,attempts=1,reason=?
           WHERE impact_id=?""",
        (
            proposal_id,
            json.dumps({"context": context, "result": candidate}, ensure_ascii=False),
            impact_id,
        ),
    )
    return proposal_id


def test_retry_repairs_invalid_candidate_and_keeps_proposal_pending(tmp_path: Path):
    cfg, db, analyzer, impact_id, claim_ids = setup_impact(tmp_path)
    invalid = valid_initial_result(claim_ids)
    invalid["proposed_current_view"]["one_line_conclusion"] = (
        "MLCC行业已经确认进入长期上行周期。"
    )
    repaired = valid_initial_result(claim_ids)
    analyzer.llm = SequencedLLM([invalid, repaired])
    recovery = ImpactRecoveryService(cfg, db, analyzer)

    result = recovery.retry(impact_id, max_repairs=2)

    assert result["status"] == "proposed"
    proposal = db.proposal(result["proposal_id"])
    assert proposal["status"] == "pending"
    assert proposal["source_impact_id"] == impact_id
    assert db.one("SELECT COUNT(*) AS n FROM current_views WHERE status='official'")["n"] == 0

    impact = db.one("SELECT * FROM impact_reviews WHERE impact_id=?", (impact_id,))
    assert impact["attempts"] == 1
    assert impact["status"] == "proposed"

    audit = db.all(
        """SELECT * FROM impact_attempt_audit
           WHERE impact_id=? ORDER BY execution_attempt,repair_round""",
        (impact_id,),
    )
    assert len(audit) == 2
    assert audit[0]["phase"] == "initial"
    assert "single-company Evidence scope" in json.loads(audit[0]["validation_errors_json"])[0]
    assert audit[1]["phase"] == "repair"
    assert json.loads(audit[1]["validation_errors_json"]) == []

    shown = recovery.show(impact_id)
    assert shown["target_node"]["canonical_name"] == "MLCC"
    assert shown["evidence_profile"]["evidence_scope"] == "single_company_sample"
    assert len(shown["claims"]) == 3
    assert shown["validation_errors"] == []
    assert shown["last_llm_output"]["proposed_current_view"]["one_line_conclusion"] == (
        repaired["proposed_current_view"]["one_line_conclusion"]
    )


def test_retry_is_idempotent_after_proposal_creation(tmp_path: Path):
    cfg, db, analyzer, impact_id, claim_ids = setup_impact(tmp_path)
    analyzer.llm = SequencedLLM([valid_initial_result(claim_ids)])
    recovery = ImpactRecoveryService(cfg, db, analyzer)

    first = recovery.retry(impact_id)
    attempts_before = db.one(
        "SELECT attempts FROM impact_reviews WHERE impact_id=?", (impact_id,)
    )["attempts"]
    second = recovery.retry(impact_id)

    assert first["status"] == "proposed"
    assert second == {
        "status": "proposed",
        "proposal_id": first["proposal_id"],
        "proposal_status": "pending",
        "idempotent": True,
    }
    assert db.one("SELECT COUNT(*) AS n FROM proposals WHERE source_impact_id=?", (impact_id,))["n"] == 1
    assert db.one("SELECT attempts FROM impact_reviews WHERE impact_id=?", (impact_id,))["attempts"] == attempts_before
    assert analyzer.llm.calls == 1


def test_failed_repairs_remain_retry_and_never_bypass_validator(tmp_path: Path):
    cfg, db, analyzer, impact_id, claim_ids = setup_impact(tmp_path)
    invalid = valid_initial_result(claim_ids)
    invalid["proposed_current_view"]["one_line_conclusion"] = (
        "MLCC行业已经确认进入长期上行周期。"
    )
    analyzer.llm = SequencedLLM([invalid, invalid, invalid])
    recovery = ImpactRecoveryService(cfg, db, analyzer)

    result = recovery.retry(impact_id, max_repairs=2)

    assert result["status"] == "retry"
    assert db.one("SELECT COUNT(*) AS n FROM proposals WHERE source_impact_id=?", (impact_id,))["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM current_views WHERE status='official'")["n"] == 0
    impact = db.one("SELECT * FROM impact_reviews WHERE impact_id=?", (impact_id,))
    assert impact["status"] == "retry"
    assert "single-company Evidence scope" in impact["last_error"]
    assert db.one(
        "SELECT COUNT(*) AS n FROM impact_attempt_audit WHERE impact_id=?", (impact_id,)
    )["n"] == 3


def test_impacts_cli_exposes_show_and_retry():
    parser = build_parser()
    show = parser.parse_args(["impacts", "show", "IMP_X"])
    retry = parser.parse_args(
        ["impacts", "retry", "IMP_X", "--replace-pending", "--max-repairs", "1"]
    )

    assert show.command == "impacts" and show.impact_command == "show"
    assert retry.command == "impacts" and retry.impact_command == "retry"
    assert retry.replace_pending is True
    assert retry.max_repairs == 1


def test_replace_pending_stales_original_repairs_and_is_idempotent(tmp_path: Path):
    cfg, db, analyzer, impact_id, claim_ids = setup_impact(tmp_path)
    invalid = valid_initial_result(claim_ids)
    invalid["proposed_current_view"]["major_risks"].append(
        "MLCC行业竞争格局可能因扩产加剧，导致价格战风险。"
    )
    old_proposal_id = persist_pending_candidate(
        cfg, db, impact_id, claim_ids, invalid
    )
    repaired = valid_initial_result(claim_ids)
    analyzer.llm = SequencedLLM([repaired])
    recovery = ImpactRecoveryService(cfg, db, analyzer)

    first = recovery.retry(impact_id, replace_pending=True, max_repairs=2)

    assert first["status"] == "proposed"
    assert first["replaced_proposal_id"] == old_proposal_id
    assert first["proposal_id"] != old_proposal_id
    assert db.proposal(old_proposal_id)["status"] == "stale"
    new_proposal = db.proposal(first["proposal_id"])
    assert new_proposal["status"] == "pending"
    assert new_proposal["source_impact_id"] == impact_id
    assert db.one("SELECT COUNT(*) AS n FROM current_views WHERE status='official'")["n"] == 0
    assert db.one(
        "SELECT attempts FROM impact_reviews WHERE impact_id=?", (impact_id,)
    )["attempts"] == 2

    audit = db.all(
        """SELECT * FROM impact_attempt_audit
           WHERE impact_id=? ORDER BY execution_attempt,repair_round""",
        (impact_id,),
    )
    assert [row["phase"] for row in audit] == ["correction_original", "correction_repair"]
    original_errors = json.loads(audit[0]["validation_errors_json"])
    assert any("unsupported causal inference" in error for error in original_errors)
    assert json.loads(audit[0]["candidate_json"])["proposed_current_view"]["major_risks"][-1] == (
        "MLCC行业竞争格局可能因扩产加剧，导致价格战风险。"
    )
    assert json.loads(audit[1]["candidate_json"])["proposed_current_view"] == (
        repaired["proposed_current_view"]
    )
    assert json.loads(audit[1]["validation_errors_json"]) == []

    second = recovery.retry(impact_id, replace_pending=True, max_repairs=2)

    assert second["proposal_id"] == first["proposal_id"]
    assert second["proposal_status"] == "pending"
    assert second["idempotent"] is True
    assert db.one(
        "SELECT COUNT(*) AS n FROM proposals WHERE source_impact_id=?", (impact_id,)
    )["n"] == 2
    assert db.one(
        "SELECT attempts FROM impact_reviews WHERE impact_id=?", (impact_id,)
    )["attempts"] == 2
    assert analyzer.llm.calls == 1
