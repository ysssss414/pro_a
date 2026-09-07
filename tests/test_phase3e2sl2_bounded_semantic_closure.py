from __future__ import annotations

from copy import deepcopy

from pro_a.acceptance_metrics import evaluate_recall_metric
from pro_a.operational_ingestion import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    _same_source_duplicate_pairs,
    _semantic_admission_artifact,
)
from pro_a.proposition_ir import (
    PROPOSITION_IR_VERSION,
    derived_evidence_unit_id,
    derived_proposition_id,
    structural_atomicity_result,
    structural_nature_result,
    validate_proposition_ir,
)
from pro_a.semantic_admission import (
    ADMISSIBLE,
    REVIEW_REQUIRED,
    evaluate_semantic_admission,
    reconcile_mandatory_qualifier,
)


def _validation(parent: str, segments: list[str], specs: list[dict]) -> dict:
    evidence = [
        {
            "evidence_unit_id": derived_evidence_unit_id(parent, text, "PAGE:1", order),
            "normalized_text": text,
            "source_locator": "PAGE:1",
            "order": order,
        }
        for order, text in enumerate(segments)
    ]
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
    return validate_proposition_ir(
        {
            "schema_version": PROPOSITION_IR_VERSION,
            "parent_claim_id": parent,
            "ir_status": "VALID",
            "units": units,
        },
        expected_parent_claim_id=parent,
        evidence_units=evidence,
    )


def _semantic_inputs(
    claims: list[dict], *, evidence_by_id: dict[str, str] | None = None
) -> dict:
    evidence_by_id = evidence_by_id or {
        claim["claim_id"]: claim["statement"] for claim in claims
    }
    return _semantic_admission_artifact(
        manifest={"run_id": "INGEST_SL2", "source": {"sha256": "a" * 64}},
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
                    "resolved_locator": {
                        "authoritative": True,
                        "locator": "PAGE:1",
                    },
                    "evidence_contract": {
                        "canonical_ready_evidence": evidence_by_id[claim["claim_id"]]
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
    )


def test_scope_preservation_restores_supported_mandatory_condition():
    statement = "设备交付可能延后，替代方案的使用周期可能延长。"
    condition = "若认证进度慢于计划，或部署成本持续高于预算"
    result = reconcile_mandatory_qualifier(
        statement=statement,
        assumption_text=condition,
        authoritative_evidence=f"{condition}，设备交付可能延后，替代方案的使用周期可能延长",
        evidence_authoritative=True,
    )

    assert result["status"] == "RECONCILED"
    assert result["qualifier_class"] == "MEANING_CHANGING_SCOPE"
    assert result["semantic_statement"] == f"{condition}，{statement}"
    assert result["invented_qualifier"] is False


def test_scope_preservation_does_not_duplicate_existing_condition_or_optional_context():
    condition = "如果维护窗口不足"
    already = reconcile_mandatory_qualifier(
        statement=f"{condition}，切换计划可能延期。",
        assumption_text=condition,
        authoritative_evidence=f"{condition}，切换计划可能延期",
        evidence_authoritative=True,
    )
    optional = reconcile_mandatory_qualifier(
        statement="系统支持远程巡检。",
        assumption_text="背景说明：该方案最初用于试点园区",
        authoritative_evidence="该方案最初用于试点园区，系统支持远程巡检",
        evidence_authoritative=True,
    )

    assert already["status"] == "ALREADY_PRESERVED"
    assert already["semantic_statement"] == f"{condition}，切换计划可能延期。"
    assert optional["status"] == "OPTIONAL_CONTEXT"
    assert optional["semantic_statement"] == "系统支持远程巡检。"


def test_scope_preservation_fails_closed_when_condition_is_not_authoritatively_supported():
    result = reconcile_mandatory_qualifier(
        statement="批量交付可能延迟。",
        assumption_text="除非完成全部环境测试",
        authoritative_evidence="批量交付可能延迟",
        evidence_authoritative=True,
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["semantic_statement"] == "批量交付可能延迟。"


def test_scope_repair_is_visible_at_admission_without_silent_keep():
    claim = {
        "claim_id": "CLM_SCOPE_GENERIC",
        "statement": "设备交付可能延后。",
        "assumption_text": "若认证进度慢于计划",
        "scope": "设备交付",
        "fact_time": "",
        "status": "current",
        "attributed_to": "研究机构",
        "nature": "expert_judgment",
    }
    result = _semantic_inputs(
        [claim],
        evidence_by_id={
            claim["claim_id"]: "若认证进度慢于计划，设备交付可能延后"
        },
    )
    decision = result["decisions"][0]

    assert decision["recommended_decision"] == "REVIEW"
    assert decision["scope_preservation"]["status"] == "RECONCILED"
    assert decision["semantic_statement"].startswith("若认证进度慢于计划，")
    assert "MEANING_CHANGING_SCOPE_RECONCILED" in decision[
        "semantic_admission"
    ]["guard_reasons"]


def test_duplicate_shared_subproposition_is_compared_before_frozen_threshold():
    claims = [
        {
            "claim_id": "CLM_PARENT",
            "statement": "专用适配器依赖部署路线，标准接口的扩容收益相对更具普适性。",
            "nature": "expert_judgment",
            "scope": "部署方案",
            "source_id": "SRC_SHARED",
            "origin_piece_sha256": "a" * 64,
            "attributed_to": "研究机构",
            "evidence_validated": True,
        },
        {
            "claim_id": "CLM_SHARED",
            "statement": "标准接口的扩容收益逻辑更具普适性。",
            "nature": "expert_judgment",
            "scope": "标准接口",
            "source_id": "SRC_SHARED",
            "origin_piece_sha256": "a" * 64,
            "attributed_to": "研究机构",
            "evidence_validated": True,
        },
    ]

    assert DUPLICATE_SIMILARITY_THRESHOLD == 0.92
    assert _same_source_duplicate_pairs(claims) == {"CLM_SHARED": "CLM_PARENT"}


def test_duplicate_negative_controls_preserve_predicate_scope_outcome_and_condition():
    base = {
        "claim_id": "CLM_BASE",
        "statement": "若负载高于设计值，互连模块的传输效率将提高。",
        "nature": "expert_judgment",
    }
    controls = [
        {**deepcopy(base), "claim_id": "CLM_PREDICATE", "statement": "若负载高于设计值，互连模块的故障率将提高。"},
        {**deepcopy(base), "claim_id": "CLM_SCOPE", "statement": "若负载高于设计值，冷却模块的传输效率将提高。"},
        {**deepcopy(base), "claim_id": "CLM_OUTCOME", "statement": "若负载高于设计值，互连模块的传输效率将下降。"},
        {**deepcopy(base), "claim_id": "CLM_CONDITION", "statement": "若温度低于设计值，互连模块的传输效率将提高。"},
        {**deepcopy(base), "claim_id": "CLM_RELATED", "statement": "互连模块和冷却模块都使用相同的封装材料。"},
    ]

    assert _same_source_duplicate_pairs([base, *controls]) == {}


def test_duplicate_negative_controls_do_not_strip_scenario_or_unbounded_detail_parent():
    claims = [
        {
            "claim_id": "CLM_SCENARIO_A",
            "statement": "在成熟工艺场景下，覆盖率提升至90%时总成本降至500元。",
            "nature": "data",
        },
        {
            "claim_id": "CLM_SCENARIO_B",
            "statement": "在试产工艺场景下，覆盖率提升至90%时总成本降至500元。",
            "nature": "data",
        },
        {
            "claim_id": "CLM_DETAIL_PARENT",
            "statement": "甲基地单价为600元，乙基地单价为620元，加权后高端平台约610元，中端平台约110元，高端单位价值约为中端的5倍。",
            "nature": "data",
        },
        {
            "claim_id": "CLM_DERIVED_SUMMARY",
            "statement": "报告指出，高端单位价值约为中端的5倍。",
            "nature": "data",
        },
    ]

    assert _same_source_duplicate_pairs(claims) == {}


def test_exact_layout_joined_identifiers_are_reconciled_but_absent_tokens_are_not():
    reconciled = evaluate_semantic_admission(
        statement="测试在100Gbps/lane DAC配置下运行。",
        attributed_to="实验室",
        permitted_support_text="测试在100Gbps/laneDAC配置下运行",
        support_region_authoritative=True,
        support_region_exhaustive=False,
        claim_evidence_fidelity_status="LAYOUT_NORMALIZED_EXACT_MATCH",
    )
    absent = evaluate_semantic_admission(
        statement="测试在100Gbps/lane DAC配置下运行。",
        attributed_to="实验室",
        permitted_support_text="测试在100Gbps/lane配置下运行",
        support_region_authoritative=True,
        support_region_exhaustive=False,
        claim_evidence_fidelity_status="LAYOUT_NORMALIZED_EXACT_MATCH",
    )

    assert reconciled["precision_token_guard"]["status"] == ADMISSIBLE
    assert reconciled["precision_token_guard"]["details"][
        "authoritative_layout_join_reconciled"
    ] is True
    assert absent["precision_token_guard"]["status"] == REVIEW_REQUIRED


def test_structured_time_scope_reconciles_year_only_under_exact_binding():
    reconciled = evaluate_semantic_admission(
        statement="运营方预计2027年资本开支约80亿元。",
        attributed_to="运营方",
        permitted_support_text="运营方预计资本开支约80亿元",
        support_region_authoritative=True,
        support_region_exhaustive=False,
        nature="company_guidance",
        fact_time="2027-06",
        scope="运营方2027年资本开支",
        claim_evidence_fidelity_status="EXACT_SOURCE_MATCH",
    )
    mismatch = evaluate_semantic_admission(
        statement="运营方预计2028年资本开支约80亿元。",
        attributed_to="运营方",
        permitted_support_text="运营方预计资本开支约80亿元",
        support_region_authoritative=True,
        support_region_exhaustive=False,
        nature="company_guidance",
        fact_time="2027-06",
        scope="运营方2027年资本开支",
        claim_evidence_fidelity_status="EXACT_SOURCE_MATCH",
    )

    assert reconciled["number_time_guard"]["status"] == ADMISSIBLE
    assert reconciled["number_time_guard"]["details"][
        "structured_qualifier_reconciled"
    ] is True
    assert mismatch["number_time_guard"]["status"] == REVIEW_REQUIRED


def test_same_key_independent_value_and_growth_is_validated_as_reporting_vector():
    validation = _validation(
        "CLM_REPORTING_VECTOR",
        ["2027年第二季度收入约90亿元", "同比增长25%"],
        [
            {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
            {"family": "measurement", "nature": "data", "support": [1], "key": "k1"},
        ],
    )

    assert validation["status"] == "VALID"
    assert validation["coherence_reconciliations"][0]["reason"] == (
        "SAME_PERIOD_VALUE_AND_GROWTH"
    )


def test_bounded_atomicity_reconciliation_accepts_four_general_vector_forms():
    cases = [
        _validation(
            "CLM_BOUND_METRIC",
            ["信号通过四条路径进入处理单元", "该配置的链路损耗约为8dB"],
            [
                {"family": "configuration", "nature": "expert_judgment", "support": [0], "coherence_type": "SPEC_VECTOR"},
                {"family": "measurement", "nature": "expert_judgment", "support": [1]},
            ],
        ),
        _validation(
            "CLM_PRODUCT_SPEC",
            ["八通道样机在50°C下实现每通道18dBm输出", "并配套隔离器、监控器和温控电路"],
            [
                {"family": "measurement", "support": [0]},
                {"family": "configuration", "support": [1]},
            ],
        ),
        _validation(
            "CLM_PLATFORM_VECTOR",
            ["平台同时布局两种接口路线", "并把光源、连接和监测放入同一系统框架"],
            [
                {"family": "architecture_route", "support": [0]},
                {"family": "configuration", "support": [1]},
            ],
        ),
        _validation(
            "CLM_GENERATION_VECTOR",
            ["当前平台采用32条低速通道", "下一阶段平台采用16条高速通道"],
            [
                {"family": "configuration", "nature": "expert_judgment", "support": [0]},
                {"family": "configuration", "modality": "future", "nature": "expert_judgment", "support": [1], "time_scope": "future"},
            ],
        ),
    ]

    assert all(structural_atomicity_result(case)["status"] == ADMISSIBLE for case in cases)


def test_atomicity_true_review_controls_remain_independently_updateable():
    current_and_roadmap = _validation(
        "CLM_TRUE_REVIEW",
        ["当前试点已开始运行", "下一代标准仍处于讨论阶段"],
        [
            {"family": "lifecycle", "support": [0]},
            {"family": "architecture_route", "modality": "future", "support": [1], "time_scope": "future"},
        ],
    )
    configuration_and_budget = _validation(
        "CLM_TRUE_REVIEW_METRIC",
        ["系统采用四条互连路径", "公司2027年研发预算为20亿元"],
        [
            {"family": "configuration", "support": [0]},
            {"family": "measurement", "nature": "data", "support": [1], "time_scope": "future"},
        ],
    )

    assert structural_atomicity_result(current_and_roadmap)["status"] == REVIEW_REQUIRED
    assert structural_atomicity_result(configuration_and_budget)["status"] == REVIEW_REQUIRED


def test_product_specification_measurements_are_factual_but_observed_metrics_are_not():
    specification = _validation(
        "CLM_SPEC_NATURE",
        ["设备搭载4颗处理芯片", "单颗带宽为20Gbps", "整机总带宽为80Gbps"],
        [
            {
                "family": "measurement",
                "support": [0, 1, 2],
                "coherence_type": "REPORTING_VECTOR",
            }
        ],
    )
    observed = _validation(
        "CLM_OBSERVED_NATURE",
        ["2027年第二季度收入约90亿元", "同比增长25%"],
        [
            {"family": "measurement", "support": [0], "coherence_type": "REPORTING_VECTOR"},
            {"family": "measurement", "support": [1], "coherence_type": "REPORTING_VECTOR", "key": "k1"},
        ],
    )

    spec_result = structural_nature_result(specification, claim_nature="fact")
    observed_result = structural_nature_result(observed, claim_nature="fact")

    assert spec_result["status"] == ADMISSIBLE
    assert spec_result["details"]["unit_results"][0]["bounded_nature_exception"] == (
        "FACTUAL_PRODUCT_SPECIFICATION_VECTOR"
    )
    assert observed_result["status"] == REVIEW_REQUIRED
    assert "MEASUREMENT_PROPOSITION_NOT_CLASSIFIED_AS_DATA" in observed_result[
        "reason_codes"
    ]


def test_zero_denominator_recall_is_explicitly_n_a_only_with_historical_coverage():
    covered = evaluate_recall_metric(
        numerator=0,
        denominator=0,
        threshold=0.80,
        historical_class_coverage_pass=True,
    )
    uncovered = evaluate_recall_metric(
        numerator=0,
        denominator=0,
        threshold=0.80,
        historical_class_coverage_pass=False,
    )

    assert covered == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
        "threshold": 0.8,
        "comparator": ">=",
        "scoreability": "NOT_APPLICABLE",
        "historical_class_coverage": "PASS",
        "gate": "PASS_BY_HISTORICAL_COVERAGE",
    }
    assert uncovered["value"] is None
    assert uncovered["scoreability"] == "NOT_APPLICABLE"
    assert uncovered["historical_class_coverage"] == "NOT_PROVEN"
    assert uncovered["gate"] == "FAIL"


def test_positive_denominator_recall_retains_numeric_pass_and_fail():
    passing = evaluate_recall_metric(
        numerator=4,
        denominator=5,
        threshold=0.80,
        historical_class_coverage_pass=False,
    )
    failing = evaluate_recall_metric(
        numerator=3,
        denominator=5,
        threshold=0.80,
        historical_class_coverage_pass=True,
    )

    assert passing["scoreability"] == "SCOREABLE"
    assert passing["value"] == 0.8
    assert passing["gate"] == "PASS"
    assert failing["scoreability"] == "SCOREABLE"
    assert failing["value"] == 0.6
    assert failing["gate"] == "FAIL"
