from __future__ import annotations

from copy import deepcopy

import pro_a.operational_ingestion as operational_ingestion
from pro_a.operational_ingestion import _semantic_admission_artifact
from pro_a.proposition_ir import (
    PROPOSITION_IR_VERSION,
    derived_evidence_unit_id,
    derived_proposition_id,
    structural_atomicity_result,
    structural_nature_result,
    validate_proposition_ir,
)


def _validation(parent: str, segments: list[str], specs: list[dict]) -> dict:
    evidence = []
    for order, text in enumerate(segments):
        evidence.append(
            {
                "evidence_unit_id": derived_evidence_unit_id(
                    parent, text, "PAGE:1", order
                ),
                "normalized_text": text,
                "source_locator": "PAGE:1",
                "order": order,
            }
        )
    units = []
    for ordinal, spec in enumerate(specs, 1):
        support = [evidence[index]["evidence_unit_id"] for index in spec["support"]]
        units.append(
            {
                "unit_id": derived_proposition_id(parent, support, ordinal),
                "predicate_family": spec.get("family", "status"),
                "modality": spec.get("modality", "actual"),
                "nature": spec.get("nature", "fact"),
                "support_evidence_unit_ids": support,
                "coherence_key": spec.get("key", f"k{ordinal}"),
                "coherence_type": spec.get("coherence_type", "INDEPENDENT"),
                "time_scope": spec.get("time_scope", "current"),
            }
        )
    ir = {
        "schema_version": PROPOSITION_IR_VERSION,
        "parent_claim_id": parent,
        "ir_status": "VALID",
        "units": units,
    }
    return validate_proposition_ir(
        ir,
        expected_parent_claim_id=parent,
        evidence_units=evidence,
    )


def _nature(
    parent: str,
    segments: list[str],
    specs: list[dict],
    *,
    claim_nature: str,
    attributed_to: str,
) -> dict:
    return structural_nature_result(
        _validation(parent, segments, specs),
        claim_nature=claim_nature,
        attributed_to=attributed_to,
    )


def test_external_forecast_role_is_not_hidden_by_exact_nature_match():
    result = _nature(
        "CLM_SI_EXTERNAL",
        ["根据行业协会预测", "全球市场预计2027年增长20%"],
        [
            {
                "family": "measurement",
                "modality": "future",
                "nature": "broker_forecast",
                "support": [0, 1],
                "time_scope": "future",
            }
        ],
        claim_nature="broker_forecast",
        attributed_to="行业协会（转引自研究机构）",
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert "TRANSITIVELY_CITED_FORECAST_REQUIRES_EXPERT_JUDGMENT" in result[
        "reason_codes"
    ]
    assert result["details"]["unit_results"][0][
        "attributed_nature_exact_match"
    ] is True


def test_external_forecast_role_structural_analogue_and_direct_author_control():
    specs = [
        {
            "family": "measurement",
            "modality": "future",
            "nature": "broker_forecast",
            "support": [0, 1],
            "time_scope": "future",
        }
    ]
    relayed = _nature(
        "CLM_RELAYED",
        ["据独立数据商预计", "装机量明年将增加12%"],
        specs,
        claim_nature="broker_forecast",
        attributed_to="独立数据商（引自行业周报）",
    )
    direct = _nature(
        "CLM_DIRECT",
        ["本机构预计", "装机量明年将增加12%"],
        specs,
        claim_nature="broker_forecast",
        attributed_to="本机构",
    )

    assert relayed["status"] == "REVIEW_REQUIRED"
    assert direct["status"] == "ADMISSIBLE"


def test_company_guidance_is_evaluated_per_proposition_after_exact_match():
    result = _nature(
        "CLM_SI_MIXED",
        [
            "项目预计总投资5亿元",
            "2025年已投入2亿元",
            "累计投入3亿元",
            "目前已进入客户验证阶段",
        ],
        [
            {
                "family": "measurement",
                "modality": "future",
                "nature": "company_guidance",
                "support": [0],
                "time_scope": "future",
            },
            {
                "family": "measurement",
                "nature": "company_guidance",
                "support": [1],
                "time_scope": "historical",
            },
            {
                "family": "measurement",
                "nature": "company_guidance",
                "support": [2],
            },
            {
                "family": "lifecycle",
                "nature": "company_guidance",
                "support": [3],
            },
        ],
        claim_nature="company_guidance",
        attributed_to="发行人（转引自研究机构）",
    )

    assert result["status"] == "REVIEW_REQUIRED"
    per_unit = result["details"]["unit_results"]
    assert per_unit[0]["reason_codes"] == []
    assert all(
        "REALIZED_PROPOSITION_INHERITS_COMPANY_GUIDANCE" in row["reason_codes"]
        for row in per_unit[1:]
    )


def test_company_guidance_future_plan_precision_control_remains_admissible():
    result = _nature(
        "CLM_GUIDANCE_CONTROL",
        ["公司计划明年投资5亿元", "并预计新增产能20万件"],
        [
            {
                "family": "lifecycle",
                "modality": "proposal",
                "nature": "company_guidance",
                "support": [0],
                "key": "k1",
                "coherence_type": "REPORTING_VECTOR",
                "time_scope": "future",
            },
            {
                "family": "measurement",
                "modality": "future",
                "nature": "company_guidance",
                "support": [1],
                "key": "k1",
                "coherence_type": "REPORTING_VECTOR",
                "time_scope": "future",
            },
        ],
        claim_nature="company_guidance",
        attributed_to="公司",
    )

    assert result["status"] == "ADMISSIBLE"


def test_proposal_alias_and_reporting_comparison_group_are_boundedly_canonicalized():
    proposal = _validation(
        "CLM_PROPOSAL_ALIAS",
        ["公司公告拟以1000万元收购目标公司全部股权"],
        [
            {
                "family": "proposal",
                "modality": "proposal",
                "support": [0],
                "coherence_type": "SINGLE_EVENT_ATTRIBUTES",
                "time_scope": "future",
            }
        ],
    )
    vector = _validation(
        "CLM_VECTOR_COMPAT",
        ["甲基地单价100元", "乙基地单价120元", "乙比甲高20%"],
        [
            {
                "family": "measurement",
                "nature": "data",
                "support": [0],
                "key": "k1",
                "coherence_type": "REPORTING_VECTOR",
            },
            {
                "family": "measurement",
                "nature": "data",
                "support": [1],
                "key": "k1",
                "coherence_type": "REPORTING_VECTOR",
            },
            {
                "family": "comparison",
                "nature": "data",
                "support": [2],
                "key": "k1",
                "coherence_type": "COMPARISON_VECTOR",
            },
        ],
    )
    invalid = _validation(
        "CLM_UNKNOWN_FAMILY",
        ["目标公司完成交割"],
        [{"family": "totally_unknown", "support": [0]}],
    )

    assert proposal["status"] == "VALID"
    assert proposal["normalized_units"][0]["predicate_family"] == "lifecycle"
    assert vector["status"] == "VALID"
    assert invalid["status"] == "AMBIGUOUS"
    assert "PREDICATE_FAMILY_INVALID" in invalid["issue_codes"]


def test_missing_acquisition_to_market_entry_boundary_is_generated():
    validation = _validation(
        "CLM_SI_ACQUISITION",
        [
            "此后",
            "公司围绕关键环节持续开展并购",
            "相继收购甲公司的接口业务与乙公司的温控业务",
            "并通过丙公司切入功率器件检测市场",
        ],
        [
            {
                "family": "lifecycle",
                "support": [0, 1, 2, 3],
                "coherence_type": "SEQUENTIAL_ROUTE",
                "time_scope": "historical",
            }
        ],
    )
    result = structural_atomicity_result(validation)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["details"]["generated_boundary_candidates"][0]["pattern"] == (
        "ACQUISITION_TO_DISTINCT_MARKET_ENTRY"
    )


def test_missing_current_next_generation_boundary_and_controls():
    roadmap = _validation(
        "CLM_SI_ROADMAP",
        [
            "我们认为",
            "平台正向高速控制能力纵向延伸",
            "标准控制器承担当前客户导入",
            "自研芯片则面向下一代平台进行底层能力储备",
        ],
        [
            {
                "family": "architecture_route",
                "nature": "expert_judgment",
                "support": [0, 1, 2, 3],
                "coherence_type": "SEQUENTIAL_ROUTE",
            }
        ],
    )
    acquisition_history = _validation(
        "CLM_HISTORY_CONTROL",
        ["公司先后收购甲业务", "并收购乙业务"],
        [
            {
                "family": "lifecycle",
                "support": [0, 1],
                "coherence_type": "SEQUENTIAL_ROUTE",
                "time_scope": "historical",
            }
        ],
    )
    one_roadmap = _validation(
        "CLM_ROADMAP_CONTROL",
        ["当前平台用于客户导入", "并持续面向当前平台完善能力"],
        [
            {
                "family": "architecture_route",
                "support": [0, 1],
                "coherence_type": "SEQUENTIAL_ROUTE",
            }
        ],
    )

    result = structural_atomicity_result(roadmap)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["details"]["generated_boundary_candidates"][0]["pattern"] == (
        "CURRENT_TO_NEXT_GENERATION_RESPONSIBILITY_SHIFT"
    )
    assert structural_atomicity_result(acquisition_history)["status"] == "ADMISSIBLE"
    assert structural_atomicity_result(one_roadmap)["status"] == "ADMISSIBLE"


def test_same_key_project_investment_and_period_budget_are_not_collapsed():
    result = structural_atomicity_result(
        _validation(
            "CLM_SI_BUDGET",
            ["公司拟投资78亿元建设新工厂", "并将2026年固定资产投资预算提升至100亿元"],
            [
                {
                    "family": "lifecycle",
                    "modality": "proposal",
                    "nature": "company_guidance",
                    "support": [0],
                    "key": "k1",
                    "coherence_type": "SINGLE_EVENT_ATTRIBUTES",
                    "time_scope": "future",
                },
                {
                    "family": "measurement",
                    "modality": "future",
                    "nature": "company_guidance",
                    "support": [1],
                    "key": "k1",
                    "coherence_type": "SINGLE_EVENT_ATTRIBUTES",
                    "time_scope": "future",
                },
            ],
        )
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert "PROJECT_EVENT_AND_PERIOD_CAPITAL_BUDGET" in result["reason_codes"]


def test_same_event_project_budget_precision_control_remains_coherent():
    result = structural_atomicity_result(
        _validation(
            "CLM_BUDGET_CONTROL",
            ["公司拟投资78亿元建设新工厂", "该项目总投资预算约100亿元"],
            [
                {
                    "family": "lifecycle",
                    "modality": "proposal",
                    "nature": "company_guidance",
                    "support": [0],
                    "key": "k1",
                    "coherence_type": "SINGLE_EVENT_ATTRIBUTES",
                    "time_scope": "future",
                },
                {
                    "family": "measurement",
                    "modality": "future",
                    "nature": "company_guidance",
                    "support": [1],
                    "key": "k1",
                    "coherence_type": "SINGLE_EVENT_ATTRIBUTES",
                    "time_scope": "future",
                },
            ],
        )
    )

    assert result["status"] == "ADMISSIBLE"


def test_unlinked_attributed_forecast_and_causal_driver_are_not_reconciled():
    result = structural_atomicity_result(
        _validation(
            "CLM_SI_CAUSAL",
            ["市场预计2026年增长250%", "市场规模突破8000亿元", "需求成为主要增长动力"],
            [
                {
                    "family": "measurement",
                    "modality": "future",
                    "nature": "broker_forecast",
                    "support": [0],
                    "key": "k1",
                    "coherence_type": "REPORTING_VECTOR",
                    "time_scope": "future",
                },
                {
                    "family": "measurement",
                    "modality": "future",
                    "nature": "broker_forecast",
                    "support": [1],
                    "key": "k1",
                    "coherence_type": "REPORTING_VECTOR",
                    "time_scope": "future",
                },
                {
                    "family": "causal_judgment",
                    "modality": "future",
                    "nature": "broker_forecast",
                    "support": [2],
                    "key": "k2",
                    "coherence_type": "CAUSAL_JUDGMENT",
                    "time_scope": "future",
                },
            ],
        )
    )
    linked = structural_atomicity_result(
        _validation(
            "CLM_CAUSAL_CONTROL",
            ["负载预计增长20%", "因此散热需求将成为主要约束"],
            [
                {
                    "family": "measurement",
                    "modality": "future",
                    "nature": "expert_judgment",
                    "support": [0],
                    "key": "k1",
                    "coherence_type": "REPORTING_VECTOR",
                    "time_scope": "future",
                },
                {
                    "family": "causal_judgment",
                    "modality": "future",
                    "nature": "expert_judgment",
                    "support": [1],
                    "key": "k2",
                    "coherence_type": "CAUSAL_JUDGMENT",
                    "time_scope": "future",
                },
            ],
        )
    )
    driven = structural_atomicity_result(
        _validation(
            "CLM_CAUSAL_DRIVEN_CONTROL",
            ["设备增速高于同期市场水平", "主要受复杂度提升以及验证趋严等因素推动"],
            [
                {
                    "family": "comparison",
                    "nature": "expert_judgment",
                    "support": [0],
                    "key": "k1",
                },
                {
                    "family": "causal_judgment",
                    "nature": "expert_judgment",
                    "support": [1],
                    "key": "k2",
                    "coherence_type": "CAUSAL_JUDGMENT",
                },
            ],
        )
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert linked["status"] == "ADMISSIBLE"
    assert driven["status"] == "ADMISSIBLE"


def test_four_bounded_coherence_precision_patterns_and_negative_controls():
    positives = [
        (
            "CLM_MARKET_STRUCTURE",
            ["行业集中度长期维持较高水平", "全球市场已形成少数厂商主导的竞争格局"],
            [
                {"family": "status", "support": [0]},
                {"family": "status", "support": [1]},
            ],
        ),
        (
            "CLM_COMPETITIVE_SCOPE",
            ["高端市场高度集中", "竞争优势已由单机参数延伸至平台生态与交付能力"],
            [
                {"family": "status", "nature": "expert_judgment", "support": [0]},
                {"family": "capability", "nature": "expert_judgment", "support": [1]},
            ],
        ),
        (
            "CLM_ELIDED_TIME_SERIES",
            ["2025年销售净利率提升至25.39%", "2026Q1进一步达到26.05%"],
            [
                {"family": "measurement", "nature": "data", "support": [0], "time_scope": "historical"},
                {"family": "measurement", "nature": "data", "support": [1], "time_scope": "historical"},
            ],
        ),
        (
            "CLM_PERIOD_SNAPSHOT",
            ["2024年公司营业收入同比增长31.60%", "但归母净利润仍同比下降17.41%"],
            [
                {"family": "measurement", "nature": "data", "support": [0], "time_scope": "historical"},
                {"family": "measurement", "nature": "data", "support": [1], "time_scope": "historical"},
            ],
        ),
    ]
    negatives = [
        (
            "CLM_STATUS_NEGATIVE",
            ["甲项目已量产", "乙项目仍在验证"],
            [{"family": "status", "support": [0]}, {"family": "status", "support": [1]}],
        ),
        (
            "CLM_CAPABILITY_NEGATIVE",
            ["市场高度集中", "该设备支持高压测试"],
            [
                {"family": "status", "nature": "expert_judgment", "support": [0]},
                {"family": "capability", "nature": "expert_judgment", "support": [1]},
            ],
        ),
        (
            "CLM_TIME_SERIES_NEGATIVE",
            ["2025年收入增长20%", "2026Q1利润进一步下降10%"],
            [
                {"family": "measurement", "nature": "data", "support": [0], "time_scope": "historical"},
                {"family": "measurement", "nature": "data", "support": [1], "time_scope": "historical"},
            ],
        ),
        (
            "CLM_PERIOD_NEGATIVE",
            ["2024年收入同比增长20%", "但2025年利润同比下降10%"],
            [
                {"family": "measurement", "nature": "data", "support": [0], "time_scope": "historical"},
                {"family": "measurement", "nature": "data", "support": [1], "time_scope": "historical"},
            ],
        ),
    ]

    assert all(
        structural_atomicity_result(_validation(parent, segments, specs))["status"]
        == "ADMISSIBLE"
        for parent, segments, specs in positives
    )
    assert all(
        structural_atomicity_result(_validation(parent, segments, specs))["status"]
        == "REVIEW_REQUIRED"
        for parent, segments, specs in negatives
    )


def _semantic_inputs(claims: list[dict], proposition_results: dict | None = None) -> dict:
    return _semantic_admission_artifact(
        manifest={"run_id": "INGEST_DUP", "source": {"sha256": "a" * 64}},
        bundle={"claims": claims},
        evidence_draft={
            "claims": [
                {
                    "claim_id": claim["claim_id"],
                    "bounded_context_candidates": [],
                    "evidence_spans": [],
                }
                for claim in claims
            ]
        },
        gate={
            "claims": [
                {
                    "claim_id": claim["claim_id"],
                    "fidelity_status": "EXACT_SOURCE_MATCH",
                    "resolved_locator": {"authoritative": True, "locator": "PAGE:1"},
                    "evidence_contract": {
                        "canonical_ready_evidence": claim["statement"]
                    },
                }
                for claim in claims
            ]
        },
        table_boundary={
            "decisions": [
                {
                    "claim_id": claim["claim_id"],
                    "review_eligible": True,
                    "eligibility_decision": "TABLE_CLAIM_ELIGIBLE_FAIL_OPEN",
                    "decision_reason": "KEEP_FAIL_OPEN",
                }
                for claim in claims
            ]
        },
        proposition_results=proposition_results,
    )


def test_same_source_semantic_duplicate_is_reviewed_without_suppressing_claim():
    claims = [
        {
            "claim_id": "CLM_SUMMARY",
            "statement": "报告指出，供应网络升级通过“交付更快、覆盖更广、响应更稳”三个方面提升韧性。",
            "attributed_to": "研究机构",
            "nature": "expert_judgment",
        },
        {
            "claim_id": "CLM_DETAIL",
            "statement": "研究机构判断，供应网络升级通过“交付更快、覆盖更广、响应更稳”三个方面持续提升韧性。",
            "attributed_to": "研究机构",
            "nature": "expert_judgment",
        },
    ]
    result = _semantic_inputs(claims)
    decisions = {row["claim_id"]: row for row in result["decisions"]}

    assert decisions["CLM_SUMMARY"]["recommended_decision"] == "KEEP"
    assert decisions["CLM_DETAIL"]["recommended_decision"] == "REVIEW"
    assert decisions["CLM_DETAIL"]["recommendation_reason"] == (
        "SAME_SOURCE_SEMANTIC_DUPLICATE_CANDIDATE"
    )
    assert decisions["CLM_DETAIL"]["duplicate_of_claim_id"] == "CLM_SUMMARY"
    assert len(result["decisions"]) == 2


def test_duplicate_precision_controls_preserve_distinct_time_quantity_nature_and_semantics():
    helper = getattr(operational_ingestion, "_same_source_duplicate_pairs")
    base = {
        "claim_id": "CLM_BASE",
        "statement": "机构预测，市场2027年增长20%至120亿元。",
        "nature": "broker_forecast",
    }
    changed_year = deepcopy(base)
    changed_year.update(
        claim_id="CLM_YEAR", statement="机构预测，市场2028年增长20%至120亿元。"
    )
    changed_value = deepcopy(base)
    changed_value.update(
        claim_id="CLM_VALUE", statement="机构预测，市场2027年增长30%至130亿元。"
    )
    changed_nature = deepcopy(base)
    changed_nature.update(claim_id="CLM_NATURE", nature="company_guidance")
    changed_semantics = deepcopy(base)
    changed_semantics.update(
        claim_id="CLM_SEMANTICS",
        statement="机构预测，项目2027年削减20%后预算为120亿元。",
    )

    assert helper(
        [base, changed_year, changed_value, changed_nature, changed_semantics]
    ) == {}
