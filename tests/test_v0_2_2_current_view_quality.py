from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pro_a.db import now_iso
from pro_a.propagation import PropagationManager

from stability_helpers import make_config


class ResultAnalyzer:
    available = True

    def __init__(self, result):
        self.result = result
        self.context = None

    def review_impact(self, node, current_view_md, evidence, context):
        self.context = copy.deepcopy(context)
        return copy.deepcopy(self.result)


def add_source_claims(db, node_id: str, source_id: str, claims: list[dict], *,
                      source_rank: str = "B", origin_type: str = "secondary",
                      underlying_source_id: str = "") -> list[str]:
    ts = now_iso()
    db.execute(
        """INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,
           source_rank,origin_type,underlying_source_id,ingested_at,status,metadata_json)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (source_id, source_id, f"{source_id}.md", f"/{source_id}.md", source_id, "standard",
         source_rank, origin_type, underlying_source_id, ts, "analyzed", "{}"),
    )
    claim_ids = []
    for item in claims:
        claim_id = item["claim_id"]
        db.execute(
            """INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,evidence_excerpt,
               attributed_to,scope,status,confidence,structured_json,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (claim_id, item["statement"], item["nature"], ts, source_id,
             item.get("evidence_excerpt", item["statement"]), item.get("attributed_to", ""),
             item.get("scope", ""), "current", item.get("confidence", 0.85),
             json.dumps(item.get("structured") or {}, ensure_ascii=False), ts),
        )
        db.execute(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            (claim_id, node_id, "related"),
        )
        claim_ids.append(claim_id)
    return claim_ids


def mlcc_evidence(db, node_id: str) -> list[str]:
    return add_source_claims(
        db,
        node_id,
        "SRC_MLCC",
        [
            {
                "claim_id": "CLM_PRICE",
                "statement": "昀冢科技披露其7月、8月MLCC价格环比上涨30%以上",
                "nature": "company_guidance",
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
            },
        ],
    )


def valid_initial_result(claim_ids: list[str]) -> dict:
    return {
        "requires_change": True,
        "change_level": "initial",
        "reason": "首次建立 MLCC Current View",
        "scope_normalization_notes": ["当前仅有昀冢科技单一公司、单一底层来源样本"],
        "evidence_sufficiency": {
            "sufficient": True,
            "reason": "三条 Claim 相互独立并共同确认行业长周期",
        },
        "proposed_current_view": {
            "one_line_conclusion": (
                "MLCC公司侧样本显示价格与高容产品需求改善，但单一公司Evidence尚不足以确认全行业长期上行。"
            ),
            "core_logic": [
                "昀冢科技认为AI与存储需求可能带来高容MLCC产能挤兑，但这属于公司判断（CLM_GUIDANCE）。",
                "财通电子团队判断MLCC国内外原厂趋势一致，仍需行业数据验证（CLM_BROKER）。",
            ],
            "key_facts": [
                "昀冢科技披露其7月、8月MLCC价格环比上涨30%以上（CLM_PRICE）。",
            ],
            "core_disagreements": ["MLCC公司样本能否代表行业整体供需仍存在分歧。"],
            "assumptions_to_verify": ["MLCC行业是否存在可持续的高容产品供需缺口。"],
            "investment_implication": (
                "对MLCC产业而言，昀冢科技公司侧Evidence可作为景气验证样本，但不能单独确认行业长周期。"
            ),
            "major_risks": ["MLCC行业供给扩张或下游需求走弱可能使公司样本失去代表性。"],
            "knowledge_gaps": ["缺少MLCC行业供需、竞争对手和下游需求量化数据。"],
            "key_watch_items": [
                "跟踪MLCC行业供需与库存数据。",
                "跟踪MLCC主要竞争对手的价格和扩产计划。",
                "跟踪MLCC下游AI、存储及其他应用需求。",
            ],
            "recent_change": "首次基于昀冢科技样本建立MLCC初始认知。",
            "evidence_claim_ids": claim_ids,
            "type_specific": {
                "applications": ["昀冢科技认为AI与存储可能拉动高容MLCC需求（CLM_GUIDANCE）。"],
                "demand_drivers": ["昀冢科技认为AI与存储需求是潜在驱动（CLM_GUIDANCE）。"],
                "supply_capacity": ["昀冢科技认为高容MLCC可能存在产能挤兑（CLM_GUIDANCE）。"],
                "pricing": ["昀冢科技披露其7月、8月MLCC价格环比上涨30%以上（CLM_PRICE）。"],
                "major_suppliers": ["昀冢科技是当前Evidence覆盖的MLCC供应商样本（CLM_PRICE）。"],
                "product_evolution": ["昀冢科技认为高容MLCC是产品升级方向（CLM_GUIDANCE）。"],
            },
        },
        "knowledge_gaps": [],
        "research_question_candidates": [],
    }


def evaluate(tmp_path: Path, result_mutator=None):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("MLCC", "Product", ["多层陶瓷电容器"])
    claim_ids = mlcc_evidence(db, node_id)
    result = valid_initial_result(claim_ids)
    if result_mutator:
        result_mutator(result)
    manager = PropagationManager(cfg, db, ResultAnalyzer(result))
    reviewed = manager.evaluate_node(
        batch_id="BATCH_MLCC", trigger_type="new_node_accept", trigger_id="PROP_MLCC",
        node_id=node_id, path_type="direct", claim_ids=claim_ids,
        trigger_source_id="SRC_MLCC",
    )
    return db, reviewed


def test_initial_proposal_records_source_level_evidence_profile(tmp_path: Path):
    db, reviewed = evaluate(tmp_path)

    assert reviewed["status"] == "proposed"
    proposal = db.proposal(reviewed["proposal_id"])
    payload = proposal["payload"]
    assert payload["evidence_source_count"] == 1
    assert payload["independent_evidence_source_count"] == 1
    assert payload["source_rank_distribution"] == {"B": 1}
    assert payload["source_origin_distribution"] == {"secondary": 1}
    assert "相互独立" not in payload["evidence_sufficiency"]["reason"]
    assert payload["proposed_current_view"]["evidence_profile"]["independent_evidence_source_count"] == 1


def test_independence_uses_underlying_source_not_claim_or_wrapper_source_count(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("MLCC", "Product")
    claim_a = add_source_claims(
        db, node_id, "SRC_WRAPPER_A",
        [{"claim_id": "CLM_A", "statement": "A", "nature": "fact"}],
        source_rank="A", origin_type="secondary", underlying_source_id="SRC_UNDERLYING",
    )[0]
    claim_b = add_source_claims(
        db, node_id, "SRC_WRAPPER_B",
        [{"claim_id": "CLM_B", "statement": "B", "nature": "fact"}],
        source_rank="B", origin_type="secondary", underlying_source_id="SRC_UNDERLYING",
    )[0]
    manager = PropagationManager(cfg, db, ResultAnalyzer({}))

    profile = manager._evidence_profile(manager._claims([claim_a, claim_b]))

    assert profile == {
        "evidence_source_count": 2,
        "independent_evidence_source_count": 1,
        "source_rank_distribution": {"A": 1, "B": 1},
        "source_origin_distribution": {"secondary": 2},
    }


@pytest.mark.parametrize(
    "mutator",
    [
        lambda result: result["proposed_current_view"].update({
            "core_logic": ["AI与存储需求将造成MLCC产能挤兑并带来长周期（CLM_GUIDANCE）。"]
        }),
        lambda result: result["proposed_current_view"].update({
            "key_facts": ["MLCC将进入长期上行周期（CLM_BROKER）。"]
        }),
        lambda result: result["proposed_current_view"].update({
            "one_line_conclusion": "MLCC行业已经确认进入长期上行周期。"
        }),
        lambda result: result["proposed_current_view"].update({
            "one_line_conclusion": "昀冢科技价格和产能改善，未来成长确定。"
        }),
        lambda result: result["proposed_current_view"].update({"type_specific": {}}),
        lambda result: result["proposed_current_view"]["type_specific"].update({
            "pricing": ["公司披露7月、8月价格环比上涨30%以上（CLM_PRICE）。"]
        }),
        lambda result: result["proposed_current_view"].update({
            "major_risks": ["后续情况仍存在不确定性。"]
        }),
        lambda result: result["proposed_current_view"].update({
            "one_line_conclusion": ["MLCC", "单一公司样本"]
        }),
    ],
    ids=[
        "unattributed-guidance",
        "judgment-in-key-facts",
        "company-to-industry-overreach",
        "source-centric-view",
        "missing-product-schema",
        "generic-company-attribution",
        "ungrounded-major-risk",
        "non-string-one-line",
    ],
)
def test_invalid_initial_view_quality_cannot_create_proposal(tmp_path: Path, mutator):
    db, reviewed = evaluate(tmp_path, mutator)

    assert reviewed["status"] == "retry"
    assert reviewed["proposal_id"] == ""
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0


def test_valid_mlcc_view_is_target_centric_attributed_and_typed(tmp_path: Path):
    db, reviewed = evaluate(tmp_path)

    proposal = db.proposal(reviewed["proposal_id"])["payload"]
    view = proposal["proposed_current_view"]
    assert "尚不足以确认全行业长期上行" in view["one_line_conclusion"]
    assert "昀冢科技认为" in view["core_logic"][0]
    assert "财通电子团队判断" in view["core_logic"][1]
    assert "昀冢科技" in view["key_facts"][0] and "CLM_PRICE" in view["key_facts"][0]
    assert all("MLCC" in item for item in view["key_watch_items"])
    assert "MLCC产业" in view["investment_implication"]
    assert any(view["type_specific"][key] for key in view["type_specific"])


def test_product_type_specific_accepts_structured_auditable_evidence_items(tmp_path: Path):
    def structured_pricing(result):
        result["proposed_current_view"]["type_specific"]["pricing"] = [{
            "company": "昀冢科技",
            "price_change": "7月、8月MLCC价格环比上涨30%以上",
            "evidence_claim_ids": ["CLM_PRICE"],
            "attribution": "昀冢科技业绩说明会",
        }]

    db, reviewed = evaluate(tmp_path, structured_pricing)

    assert reviewed["status"] == "proposed"
    pricing = db.proposal(reviewed["proposal_id"])["payload"]["proposed_current_view"]["type_specific"]["pricing"]
    assert pricing[0]["evidence_claim_ids"] == ["CLM_PRICE"]


def test_impact_context_exposes_required_claim_attributions(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("MLCC", "Product", ["多层陶瓷电容器"])
    claim_ids = mlcc_evidence(db, node_id)
    analyzer = ResultAnalyzer(valid_initial_result(claim_ids))
    manager = PropagationManager(cfg, db, analyzer)

    reviewed = manager.evaluate_node(
        batch_id="BATCH_CONTEXT", trigger_type="new_node_accept", trigger_id="PROP_CONTEXT",
        node_id=node_id, path_type="direct", claim_ids=claim_ids, trigger_source_id="SRC_MLCC",
    )

    assert reviewed["status"] == "proposed"
    assert analyzer.context["required_claim_attributions"] == {
        "CLM_PRICE": {"nature": "company_guidance", "attributed_to": "昀冢科技业绩说明会"},
        "CLM_GUIDANCE": {"nature": "company_guidance", "attributed_to": "昀冢科技业绩说明会"},
        "CLM_BROKER": {"nature": "expert_judgment", "attributed_to": "财通电子团队"},
    }


def test_company_guidance_look_positive_word_preserves_attributed_judgment(tmp_path: Path):
    def use_look_positive_attribution(result):
        result["proposed_current_view"]["core_logic"][0] = (
            "昀冢科技看好AI与存储需求带来高容MLCC产能挤兑（CLM_GUIDANCE）。"
        )

    _, reviewed = evaluate(tmp_path, use_look_positive_attribution)

    assert reviewed["status"] == "proposed"


def test_initial_single_source_does_not_override_semantic_scope_insufficiency(tmp_path: Path):
    def scope_insufficient(result):
        result["evidence_sufficiency"] = {
            "sufficient": False,
            "reason": "Evidence scope cannot support even a qualified Initial View",
        }

    db, reviewed = evaluate(tmp_path, scope_insufficient)

    assert reviewed["status"] == "no_change"
    assert reviewed["proposal_id"] == ""
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0
