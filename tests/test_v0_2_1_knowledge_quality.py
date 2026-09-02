from __future__ import annotations

import json
from pathlib import Path

import pytest

from pro_a.analyzer import Analyzer, SourceAnalysis
from pro_a.llm import LLMError
from pro_a.pipeline import IngestionPipeline
from pro_a.proposals import ProposalManager

from stability_helpers import make_config


class StaticLLM:
    available = True

    def __init__(self, payload):
        self.payload = payload

    def json(self, system, user):
        return self.payload


class SequenceLLM:
    available = True

    def __init__(self, *payloads):
        self.payloads = list(payloads)

    def json(self, system, user):
        return self.payloads.pop(0)


class TruncationThenLLM:
    available = True

    def __init__(self, payload):
        self.payload = payload
        self.users = []

    def json(self, system, user):
        self.users.append(user)
        if len(self.users) == 1:
            raise LLMError(
                "LLM output truncated: finish_reason=length; "
                "failure_category=output_truncation"
            )
        return self.payload


def source_payload(*, matches=None, candidates=None, claims=None):
    return {
        "source_metadata": {
            "title": "昀冢科技MLCC更新",
            "author": "财通电子",
            "organization": "财通证券",
            "publication_time": "2026-08-13",
            "source_rank": "B",
            "source_origin_type": "secondary",
            "summary": "MLCC业务更新",
        },
        "node_matches": matches or [],
        "node_candidates": candidates or [],
        "claims": claims or [],
        "source_references": [],
    }


RUN_003_INFRA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "run_003_infrastructure_failures.json").read_text(
        encoding="utf-8"
    )
)


def claim(statement: str, excerpt: str, *, attributed_to: str = "昀冢科技", scope: str = "公司"):
    return {
        "statement": statement,
        "nature": "data",
        "related_node_ids": [],
        "related_candidate_names": [],
        "fact_time": "2026-08",
        "evidence_pointer": "[[PARA:1]]",
        "evidence_excerpt": excerpt,
        "attributed_to": attributed_to,
        "scope": scope,
        "assumption": "",
        "status": "current",
        "confidence": 0.9,
        "novelty_level": "N2",
        "structured": {},
    }


def test_markdown_escape_is_canonicalized_before_exact_evidence_match(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    text = "其中高容\\&超高容占新扩产产能比例70%以上。"
    payload = source_payload(claims=[claim(
        "昀冢科技高容和超高容产品占新扩产产能比例70%以上。",
        "高容&超高容占新扩产产能比例70%以上",
    )])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source("sample.md", text, "standard")

    validation = result.claims[0]["validation"]
    assert validation["evidence_validated"] is True
    assert validation["match_method"] == "normalized_exact_substring"
    assert validation["normalized_excerpt"] == "高容&超高容占新扩产产能比例70%以上"
    assert validation["normalized_start"] >= 0


def test_company_price_claim_preserves_statement_and_separate_attribution(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    payload = source_payload(claims=[claim(
        "2026年7月MLCC价格环比上涨30%以上。",
        "公司2026年7月MLCC价格环比上涨30%以上",
        attributed_to="昀冢科技",
        scope="公司价格",
    )])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "公司2026年7月MLCC价格环比上涨30%以上。", "standard"
    )

    normalized = result.claims[0]
    assert normalized["statement"] == "2026年7月MLCC价格环比上涨30%以上。"
    assert normalized["attributed_to"] == "昀冢科技"
    assert "statement_normalization" not in normalized


def test_structured_company_does_not_overwrite_claim_subject(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    item = claim(
        "2026年7月MLCC价格环比上涨30%以上。",
        "公司2026年7月MLCC价格环比上涨30%以上",
        attributed_to="昀冢科技业绩说明会",
        scope="MLCC行业",
    )
    item["structured"] = {"company": "昀冢科技", "metric": "MLCC价格"}
    payload = source_payload(claims=[item])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "公司2026年7月MLCC价格环比上涨30%以上。", "standard"
    )

    assert result.claims[0]["statement"] == "2026年7月MLCC价格环比上涨30%以上。"
    assert result.claims[0]["attributed_to"] == "昀冢科技业绩说明会"
    assert "statement_normalization" not in result.claims[0]


@pytest.mark.parametrize(("statement", "scope", "forbidden"), [
    ("龙头公司在备料方面更有优势。", "龙头光模块公司", "龙头发言人"),
    ("大陆公司主要做无源器件和外置光源模组。", "大陆光模块公司", "大陆发言人"),
    ("两家龙头公司订单完成率不足50%。", "龙头光模块公司", "两家龙头发言人"),
])
def test_speaker_metadata_never_replaces_company_business_subject(
    tmp_path: Path, statement: str, scope: str, forbidden: str,
):
    cfg, db = make_config(tmp_path)
    item = claim(
        statement, statement, attributed_to="发言人（研究员）", scope=scope,
    )
    item["nature"] = "expert_judgment"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(claims=[item]))

    result = analyzer.analyze_source("sample.md", statement, "standard")

    normalized = result.claims[0]
    assert normalized["statement"] == statement
    assert forbidden not in normalized["statement"]
    assert normalized["attributed_to"] == "发言人（研究员）"
    assert "statement_normalization" not in normalized


@pytest.mark.parametrize("statement", [
    "袁杰可能28年的产能已被客户预订。",
    "清香甘的这种技术仍需验证。",
])
def test_attribution_processing_does_not_infer_entity_or_technical_term(
    tmp_path: Path, statement: str,
):
    cfg, db = make_config(tmp_path)
    item = claim(
        statement, statement, attributed_to="发言人（研究员）", scope="专家交流",
    )
    item["nature"] = "expert_judgment"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(claims=[item]))

    result = analyzer.analyze_source("sample.md", statement, "standard")

    normalized = result.claims[0]
    assert normalized["statement"] == statement
    assert "可能指新易盛" not in normalized["statement"]
    assert "硅光" not in normalized["statement"]
    if "袁杰" in statement:
        assert "袁杰可能28年的产能" in normalized["statement"]


def test_pilot1_host_and_expert_attribution_remain_distinguishable(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    claims = []
    for statement, attributed_to in (
        ("主持人提出供需问题。", "主持人"),
        ("专家判断供给仍然紧张。", "专家"),
    ):
        item = claim(statement, statement, attributed_to=attributed_to, scope="专家交流")
        item["nature"] = "expert_judgment"
        claims.append(item)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(claims=claims))

    result = analyzer.analyze_source(
        "sample.md", "主持人提出供需问题。专家判断供给仍然紧张。", "standard",
    )

    assert [item["attributed_to"] for item in result.claims] == ["主持人", "专家"]
    assert [item["statement"] for item in result.claims] == [
        "主持人提出供需问题。", "专家判断供给仍然紧张。",
    ]


def test_mixed_current_actual_and_future_guidance_is_atomicized(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    item = claim(
        "昀冢科技一期当前出货量为80亿颗/月，预计2026Q4达到120亿颗/月。",
        "昀冢科技一期当前出货量为80亿颗/月，预计2026Q4达到120亿颗/月。",
        attributed_to="昀冢科技业绩说明会",
        scope="昀冢科技一期MLCC产能",
    )
    item["nature"] = "company_guidance"
    item["structured"] = {
        "company": "昀冢科技",
        "metric": "一期MLCC出货量",
        "current_output": "80亿颗/月",
        "target_output": "120亿颗/月",
        "target_time": "2026Q4",
    }
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(claims=[item]))

    result = analyzer.analyze_source(
        "sample.md",
        "昀冢科技一期当前出货量为80亿颗/月，预计2026Q4达到120亿颗/月。",
        "standard",
    )

    assert len(result.claims) == 2
    assert [item["nature"] for item in result.claims] == ["data", "company_guidance"]
    assert "当前出货量为80亿颗/月" in result.claims[0]["statement"]
    assert "预计2026Q4达到120亿颗/月" in result.claims[1]["statement"]
    assert all(item["validation"]["evidence_validated"] for item in result.claims)


def test_actual_company_price_is_not_rewritten_as_guidance_or_forecast(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    item = claim(
        "昀冢科技26M7、26M8单月MLCC价格环比上涨30%以上。",
        "昀冢科技26M7、26M8单月MLCC价格环比上涨30%以上。",
        attributed_to="昀冢科技业绩说明会",
        scope="昀冢科技MLCC价格",
    )
    item["nature"] = "company_guidance"
    item["structured"] = {"company": "昀冢科技", "metric": "MLCC价格"}
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(claims=[item]))

    result = analyzer.analyze_source(
        "sample.md", "昀冢科技26M7、26M8单月MLCC价格环比上涨30%以上。", "standard"
    )

    normalized = result.claims[0]
    assert normalized["nature"] == "data"
    assert "预计" not in normalized["statement"]
    assert "forecast" not in normalized["statement"].lower()


def test_node_match_without_locatable_evidence_is_not_directly_linked(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("国产替代", "Theme")
    payload = source_payload(matches=[{
        "node_id": node_id,
        "role": "related",
        "confidence": 0.8,
        "reason": "语义联想",
        "evidence_excerpt": "国内MLCC原厂与海外MLCC原厂产业趋势相符合",
    }])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "国内MLCC原厂与海外MLCC原厂产业趋势相符合。", "standard"
    )

    assert result.node_matches == []
    assert result.rejected_node_matches[0]["node_id"] == node_id
    assert result.rejected_node_matches[0]["validation"]["evidence_validated"] is False
    assert result.rejected_node_matches[0]["validation"]["excerpt_located"] is True
    assert result.rejected_node_matches[0]["validation"]["node_name_or_alias_found"] is False


@pytest.mark.parametrize(
    "case",
    RUN_003_INFRA_FIXTURE["analyzer_cases"],
    ids=lambda case: case["call_id"],
)
def test_run_003_node_match_without_evidence_is_safely_rejected(
    tmp_path: Path, case: dict
):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node(f"fixture-{case['call_id']}", "Theme")
    payload = source_payload(matches=[{
        "node_id": node_id,
        "role": "related",
        "confidence": 0.8,
        "reason": case["validation_error"],
    }])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(case["source"], "unrelated fixture text", "standard")

    assert result.node_matches == []
    assert len(result.rejected_node_matches) == 1
    rejected = result.rejected_node_matches[0]
    assert rejected["node_id"] == node_id
    assert rejected["evidence_validated"] is False
    assert rejected["validation"]["errors"] == ["evidence_excerpt_missing"]


def test_source_analysis_truncation_recovers_by_splitting_only_that_chunk(
    tmp_path: Path,
):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = TruncationThenLLM(source_payload())
    text = "x" * (cfg.llm.max_chunk_chars - 1)

    result = analyzer.analyze_source("run_003_length_fixture.docx", text, "standard")

    assert result.claims == []
    assert len(analyzer.llm.users) == 3
    assert "[[TRUNCATION_SPLIT:" not in analyzer.llm.users[0]
    assert "[[TRUNCATION_SPLIT:1]]" in analyzer.llm.users[1]
    assert "[[TRUNCATION_SPLIT:2]]" in analyzer.llm.users[2]
    assert cfg.llm.max_output_tokens == 32768


def test_claim_cannot_bypass_node_match_evidence_with_semantic_related_node(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("国产替代", "Theme")
    item = claim(
        "财通电子团队判断国内MLCC原厂与海外原厂趋势一致。",
        "国内MLCC原厂与海外MLCC原厂产业趋势相符合",
        attributed_to="财通电子团队",
        scope="MLCC行业",
    )
    item["nature"] = "broker_forecast"
    item["related_node_ids"] = [node_id]
    payload = source_payload(claims=[item])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "国内MLCC原厂与海外MLCC原厂产业趋势相符合。", "standard"
    )

    assert result.claims[0]["related_node_ids"] == []
    assert result.rejected_claim_node_links == [{
        "claim_statement": "财通电子团队判断国内MLCC原厂与海外原厂趋势一致。",
        "node_id": node_id,
        "evidence_excerpt": "国内MLCC原厂与海外MLCC原厂产业趋势相符合",
        "reason": "node_name_or_alias_not_in_evidence",
    }]


def test_company_attribution_suffix_does_not_duplicate_explicit_subject(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    payload = source_payload(claims=[claim(
        "昀冢科技二期投资7.5亿元。",
        "二期：投资7.5亿元",
        attributed_to="昀冢科技（业绩说明会披露）",
        scope="公司产能",
    )])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "二期：投资7.5亿元。", "standard"
    )

    assert result.claims[0]["statement"] == "昀冢科技二期投资7.5亿元。"
    assert "statement_normalization" not in result.claims[0]


def test_explicit_broker_attribution_is_not_prefixed_with_duplicate_author(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    item = claim(
        "财通证券认为国内MLCC原厂与海外原厂趋势一致。",
        "国内MLCC原厂与海外原厂趋势一致",
        attributed_to="财通电子&新科技（唐佳/周勃宇）",
        scope="MLCC行业",
    )
    item["nature"] = "expert_judgment"
    payload = source_payload(claims=[item])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "国内MLCC原厂与海外原厂趋势一致。", "standard"
    )

    assert result.claims[0]["statement"] == "财通证券认为国内MLCC原厂与海外原厂趋势一致。"
    assert "statement_normalization" not in result.claims[0]


@pytest.mark.parametrize("name", ["MLCC产能挤兑", "MLCC月度调价模式"])
def test_non_discrete_mechanism_or_strategy_is_not_an_event_candidate(tmp_path: Path, name: str):
    cfg, db = make_config(tmp_path)
    payload = source_payload(candidates=[{
        "canonical_name": name,
        "primary_type": "Event",
        "aliases": [],
        "description": "公司经营机制或持续状态",
        "suggested_parent_node_ids": [],
        "reason": "材料重点讨论",
        "confidence": 0.8,
        "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "可能影响判断",
        "is_discrete_event": False,
        "event_time": "",
        "evidence_excerpt": name,
    }])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source("sample.md", f"材料讨论{name}。", "standard")

    assert result.node_candidates == []
    assert result.rejected_node_candidates[0]["canonical_name"] == name


def test_single_source_logic_is_not_a_theme_candidate(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    payload = source_payload(candidates=[{
        "canonical_name": "AI对MLCC需求的挤出效应",
        "primary_type": "Theme",
        "aliases": [],
        "description": "本材料中的单一逻辑",
        "suggested_parent_node_ids": [],
        "reason": "本材料提及",
        "confidence": 0.8,
        "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "单份材料逻辑",
        "long_term_research_value": False,
        "cross_source_or_node_value": False,
    }])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", "本材料认为AI需求挤占MLCC产能。", "standard"
    )

    assert result.node_candidates == []


@pytest.mark.parametrize("candidate_name", ["MLCC上行周期", "MLCC周期"])
def test_cycle_state_is_not_a_theme_even_when_model_marks_long_term_value(
    tmp_path: Path, candidate_name: str,
):
    cfg, db = make_config(tmp_path)
    payload = source_payload(candidates=[{
        "canonical_name": candidate_name,
        "primary_type": "Theme",
        "aliases": ["MLCC周期"],
        "description": "当前供需和价格周期状态",
        "suggested_parent_node_ids": [],
        "reason": "模型认为可长期跟踪",
        "confidence": 0.85,
        "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "模型认为跨资料",
        "long_term_research_value": True,
        "cross_source_or_node_value": True,
    }])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source(
        "sample.md", f"材料判断{candidate_name}已经提前到来。", "standard"
    )

    assert result.node_candidates == []
    assert "candidate_is_plan_strategy_mechanism_or_state" in (
        result.rejected_node_candidates[0]["quality_validation"]["errors"]
    )


def test_high_quality_source_can_propose_product_without_existing_node_match(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    payload = source_payload(candidates=[{
        "canonical_name": "MLCC",
        "primary_type": "Product",
        "aliases": ["多层陶瓷电容器"],
        "description": "明确且可长期维护的产品对象",
        "suggested_parent_node_ids": [],
        "reason": "材料核心研究对象",
        "confidence": 0.95,
        "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "会被后续资料反复引用并维护 Current View",
    }])
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source("sample.md", "材料只讨论MLCC。", "standard")

    assert result.node_matches == []
    assert [item["canonical_name"] for item in result.node_candidates] == ["MLCC"]


def test_invalid_candidate_backfill_does_not_insert_claims_or_proposals(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    payload = source_payload(
        candidates=[{
            "canonical_name": "MLCC",
            "primary_type": "Product",
            "aliases": ["多层陶瓷电容器"],
            "description": "明确且可长期维护的产品对象",
            "suggested_parent_node_ids": [],
            "reason": "材料核心研究对象",
            "confidence": 0.95,
            "candidate_kind": "normal",
            "independent_research_value": True,
            "maintenance_rationale": "会被后续资料反复引用并维护 Current View",
        }],
        claims=[claim(
            "昀冢科技MLCC一期月出货量为80亿颗。", "MLCC一期月出货量为80亿颗"
        )],
    )
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = SequenceLLM(payload, {
        "candidate_claim_links": [{
            "candidate_name": "MLCC", "related_claim_refs": ["C99"], "reason": "非法引用",
        }],
    })
    request = cfg.root / "inbox" / "standard" / "sample.md"
    request.write_text("昀冢科技MLCC一期月出货量为80亿颗。", encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "failed"
    assert "unknown validated Claim ref" in result["error"]
    assert db.one("SELECT COUNT(*) AS n FROM claims")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0


def test_backfill_unions_initial_links_and_lexically_more_specific_candidate(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM({
        "candidate_claim_links": [
            {"candidate_name": "MLCC", "related_claim_refs": [], "reason": "模型漏判"},
            {"candidate_name": "高容值MLCC", "related_claim_refs": ["C2"], "reason": "直接相关"},
        ],
    })
    candidates = [
        {"canonical_name": "MLCC", "aliases": ["多层陶瓷电容器"], "quality_eligible": True},
        {"canonical_name": "高容值MLCC", "aliases": ["高容MLCC"], "quality_eligible": True},
    ]
    claims = [
        {
            "statement": "昀冢科技MLCC价格上涨。", "attributed_to": "昀冢科技",
            "evidence_excerpt": "MLCC价格上涨", "scope": "公司价格", "structured": {},
            "related_candidate_names": ["MLCC"], "evidence_validated": True, "status": "current",
        },
        {
            "statement": "昀冢科技高容产品完成认证。", "attributed_to": "昀冢科技",
            "evidence_excerpt": "高容产品完成认证", "scope": "公司产品", "structured": {},
            "related_candidate_names": ["高容值MLCC"], "evidence_validated": True, "status": "current",
        },
    ]

    mapping = analyzer.backfill_candidate_claims(candidates, claims)

    assert mapping["mlcc"] == [0, 1]
    assert mapping["高容值mlcc"] == [1]


class MatchAnalyzer:
    available = True

    def __init__(self, child_id: str, parent_id: str):
        self.child_id = child_id
        self.parent_id = parent_id

    def analyze_source(self, filename, text, mode):
        validation = {
            "evidence_validated": True,
            "match_method": "normalized_exact_substring",
            "normalized_excerpt": "MLCC",
            "normalized_start": 4,
            "normalized_end": 8,
        }
        return SourceAnalysis(
            source_metadata=source_payload()["source_metadata"],
            node_matches=[
                {"node_id": self.child_id, "role": "primary", "confidence": 0.95,
                 "evidence_excerpt": "MLCC", "evidence_validated": True, "validation": validation},
                {"node_id": self.parent_id, "role": "related", "confidence": 0.7,
                 "evidence_excerpt": "电子元件", "evidence_validated": True,
                 "validation": {**validation, "normalized_excerpt": "电子元件"}},
            ],
            node_candidates=[],
            claims=[],
            source_references=[],
        )

    def backfill_candidate_claims(self, candidates, claims):
        return {}


def test_parent_match_is_derived_from_confirmed_part_of_relation(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("电子元件", "Segment")
    child_id = db.add_node("MLCC", "Product")
    db.add_relation(child_id, "part_of", parent_id)
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer = MatchAnalyzer(child_id, parent_id)
    request = cfg.root / "inbox" / "standard" / "sample.md"
    request.write_text("昀冢科技MLCC业务更新，属于电子元件。", encoding="utf-8")

    result = pipeline.process_all()[0]

    nodes = {item["node_id"]: item for item in result["audit"]["nodes"]}
    assert nodes[child_id]["link_origin"] == "direct"
    assert nodes[child_id]["evidence_excerpt"] == "MLCC"
    assert nodes[child_id]["evidence_validation"]["evidence_validated"] is True
    assert nodes[parent_id]["link_origin"] == "part_of"
    assert nodes[parent_id]["derived_from_node_id"] == child_id


class BackfillAnalyzer:
    available = True

    def analyze_source(self, filename, text, mode):
        claims = [
            {
                **claim("昀冢科技2026年7月MLCC价格环比上涨30%以上。", "价格上涨30%以上"),
                "related_candidate_names": ["MLCC"],
                "evidence_validated": True,
                "validation": {"evidence_validated": True, "model_confidence": 0.9},
            },
            {
                **claim("昀冢科技MLCC一期月出货量为80亿颗。", "一期月出货量80亿颗"),
                "related_candidate_names": [],
                "evidence_validated": True,
                "validation": {"evidence_validated": True, "model_confidence": 0.9},
            },
            {
                **claim("昀冢科技精密冲压业务收入保持稳定。", "精密冲压业务收入稳定"),
                "related_candidate_names": [],
                "evidence_validated": True,
                "validation": {"evidence_validated": True, "model_confidence": 0.9},
            },
        ]
        return SourceAnalysis(
            source_metadata=source_payload()["source_metadata"],
            node_matches=[],
            node_candidates=[{
                "canonical_name": "MLCC",
                "primary_type": "Product",
                "aliases": ["多层陶瓷电容器"],
                "description": "独立电子元件产品",
                "suggested_parent_node_ids": [],
                "reason": "值得长期维护",
                "confidence": 0.95,
                "candidate_kind": "normal",
                "quality_eligible": True,
            }],
            claims=claims,
            source_references=[],
        )

    def backfill_candidate_claims(self, candidates, claims):
        return {"mlcc": [0, 1]}

    def review_impact(self, node, current_view_md, evidence, context):
        return {
            "requires_change": False,
            "change_level": "none",
            "reason": "测试仅验证关联",
            "evidence_sufficiency": {"sufficient": True},
            "proposed_current_view": {"evidence_claim_ids": []},
            "knowledge_gaps": [],
            "research_question_candidates": [],
        }


def test_accept_candidate_links_all_backfilled_validated_claims(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    analyzer = BackfillAnalyzer()
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "sample.md"
    request.write_text(
        "价格上涨30%以上；一期月出货量80亿颗；精密冲压业务收入稳定。",
        encoding="utf-8",
    )

    result = pipeline.process_all()[0]
    proposal_id = result["node_proposals"][0]
    proposal = db.proposal(proposal_id)

    assert len(proposal["payload"]["related_claim_ids"]) == 2
    assert set(proposal["payload"]["related_claim_ids"]) != {
        row["claim_id"] for row in db.all("SELECT claim_id FROM claims WHERE source_id=?", (result["source_id"],))
    }

    manager = ProposalManager(cfg, db, analyzer)
    accepted = manager.accept(proposal_id)
    linked = db.all(
        "SELECT claim_id FROM claim_node_links WHERE node_id=? ORDER BY claim_id",
        (accepted["node_id"],),
    )
    assert {row["claim_id"] for row in linked} == set(proposal["payload"]["related_claim_ids"])
    assert len(linked) == 2


def test_schema_records_claim_attribution_and_match_audit(tmp_path: Path):
    _, db = make_config(tmp_path)

    assert db.one("SELECT value FROM meta WHERE key='schema_version'")["value"] == "0.2.2"
    claim_columns = {row["name"] for row in db.all("PRAGMA table_info(claims)")}
    link_columns = {row["name"] for row in db.all("PRAGMA table_info(source_node_links)")}
    assert "attributed_to" in claim_columns
    assert {"link_origin", "derived_from_node_id", "evidence_excerpt", "evidence_validation_json"} <= link_columns
