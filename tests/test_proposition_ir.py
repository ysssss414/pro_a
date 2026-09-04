from __future__ import annotations

import copy

import pytest

from pro_a.analyzer import Analyzer
from pro_a.llm import LLMError
from pro_a.proposition_ir import (
    COHERENCE_TYPES,
    PROPOSITION_IR_VERSION,
    classify_jiang_modality,
    derived_evidence_unit_id,
    derived_proposition_id,
    proposition_ir_schema,
    validate_proposition_ir,
)
from pro_a.semantic_admission import ADMISSIBLE, REVIEW_REQUIRED, evaluate_semantic_admission
from pro_a.semantic_decomposition import (
    SemanticDecomposer,
    build_evidence_units,
    build_semantic_claim_inputs,
    normalize_model_result,
)


def _evidence(parent_claim_id: str, text: str) -> list[dict]:
    return build_evidence_units(
        parent_claim_id=parent_claim_id,
        bounded_evidence=text,
        source_locator="PAGE:1",
    )


def _ir(parent_claim_id: str, evidence_units: list[dict], *specs: dict) -> dict:
    prepared = []
    for spec in specs:
        indexes = spec.get("support", [0])
        support = [evidence_units[index]["evidence_unit_id"] for index in indexes]
        prepared.append(
            {
                "predicate_family": spec.get("family", "status"),
                "modality": spec.get("modality", "actual"),
                "nature": spec.get("nature", "fact"),
                "support_evidence_unit_ids": support,
                "coherence_key": spec.get("key", "k1"),
                "coherence_type": spec.get("coherence_type", "INDEPENDENT"),
                "time_scope": spec.get("time_scope", "current"),
            }
        )
    prepared.sort(
        key=lambda item: next(
            unit["order"]
            for unit in evidence_units
            if unit["evidence_unit_id"] == item["support_evidence_unit_ids"][0]
        )
    )
    units = []
    for ordinal, unit in enumerate(prepared, 1):
        units.append(
            {
                "unit_id": derived_proposition_id(
                    parent_claim_id, unit["support_evidence_unit_ids"], ordinal
                ),
                **unit,
            }
        )
    return {
        "schema_version": PROPOSITION_IR_VERSION,
        "parent_claim_id": parent_claim_id,
        "ir_status": "VALID",
        "units": units,
    }


def _evaluate(parent_claim_id: str, statement: str, nature: str, ir: dict, evidence: list[dict]):
    validation = validate_proposition_ir(
        ir,
        claim_statement=statement,
        expected_parent_claim_id=parent_claim_id,
        evidence_units=evidence,
    )
    return evaluate_semantic_admission(
        statement=statement,
        attributed_to="研究机构",
        permitted_support_text=statement,
        support_region_authoritative=True,
        nature=nature,
        parent_claim_id=parent_claim_id,
        proposition_ir=ir,
        proposition_evidence_units=evidence,
        proposition_ir_validation=validation,
    )


def test_v21_schema_uses_evidence_ids_and_bounded_coherence_enum():
    schema = proposition_ir_schema()
    assert schema["$id"].endswith(PROPOSITION_IR_VERSION)
    unit = schema["properties"]["units"]["items"]
    assert unit["additionalProperties"] is False
    assert {
        "unit_id",
        "predicate_family",
        "modality",
        "nature",
        "support_evidence_unit_ids",
        "coherence_key",
        "coherence_type",
    } <= set(unit["required"])
    assert set(unit["properties"]["coherence_type"]["enum"]) == set(COHERENCE_TYPES)
    assert not ({"evidence_span", "evidence_quote", "counterparty_span"} & set(unit["properties"]))


def test_evidence_and_proposition_ids_are_deterministic_and_parent_bound():
    evidence_id = derived_evidence_unit_id("CLM_A", "项目完成验证", "PAGE:1", 0)
    assert evidence_id == derived_evidence_unit_id("CLM_A", "项目完成验证", "PAGE:1", 0)
    assert evidence_id != derived_evidence_unit_id("CLM_B", "项目完成验证", "PAGE:1", 0)
    proposition_id = derived_proposition_id("CLM_A", [evidence_id], 1)
    assert proposition_id == derived_proposition_id("CLM_A", [evidence_id], 1)
    assert proposition_id.startswith("PRP_")


def test_validator_rejects_parent_drift_and_nonexistent_evidence_reference():
    evidence = _evidence("CLM_WRONG", "甲项目完成验证。")
    ir = _ir("CLM_WRONG", evidence, {"support": [0]})
    ir["units"][0]["support_evidence_unit_ids"] = ["EVDU_0000000000000000"]
    ir["units"][0]["unit_id"] = derived_proposition_id(
        "CLM_WRONG", ir["units"][0]["support_evidence_unit_ids"], 1
    )
    result = validate_proposition_ir(
        ir, expected_parent_claim_id="CLM_RIGHT", evidence_units=evidence
    )
    assert result["status"] == "INVALID"
    assert {"PARENT_CLAIM_ID_MISMATCH", "SUPPORT_EVIDENCE_ID_NOT_FOUND"} <= set(
        result["issue_codes"]
    )
    assert result["evidence_binding_failures"] == 1


def test_validator_rejects_raw_offsets_and_duplicate_units():
    evidence = _evidence("CLM_1", "产品完成验证。")
    ir = _ir("CLM_1", evidence, {"support": [0]})
    duplicate = copy.deepcopy(ir["units"][0])
    duplicate["unit_id"] = derived_proposition_id(
        "CLM_1", duplicate["support_evidence_unit_ids"], 2
    )
    duplicate["evidence_span"] = [0, 4]
    ir["units"].append(duplicate)
    result = validate_proposition_ir(
        ir, expected_parent_claim_id="CLM_1", evidence_units=evidence
    )
    assert result["valid"] is False
    assert "UNSUPPORTED_PROPOSITION_CONTENT" in result["issue_codes"]
    assert "DUPLICATE_PROPOSITION_UNIT" in result["issue_codes"]


ATOMICITY_FAMILIES = [
    (
        "LIFECYCLE_STATUS_SEQUENCE",
        "项目完成研发，工艺正在验证，产品已量产。",
        [
            {"family": "lifecycle", "support": [0], "key": "k1"},
            {"family": "status", "support": [1], "key": "k2"},
            {"family": "lifecycle", "support": [2], "key": "k3"},
        ],
    ),
    (
        "CAPABILITY_CHAIN_AND_SCALE_METRIC_BUNDLE",
        "产品支持高压转换，业务收入达到10亿元。",
        [
            {"family": "capability", "support": [0], "key": "k1"},
            {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
        ],
    ),
    (
        "INDEPENDENT_COUNTERPARTY_PROJECT_ORDER_STATES",
        "Meta项目已定点，NVIDIA项目正在送样。",
        [
            {"family": "status", "support": [0], "key": "k1"},
            {"family": "status", "support": [1], "key": "k2"},
        ],
    ),
    (
        "MULTIPLE_PRODUCT_CAPABILITIES_OR_SPEC_PLUS_SUITABILITY",
        "产品可耐高温，并适用于AI机柜。",
        [
            {"family": "capability", "modality": "capability", "support": [0], "key": "k1"},
            {"family": "application", "support": [1], "key": "k2"},
        ],
    ),
    (
        "TOPOLOGY_COUNT_AND_ROUTE_BUNDLE",
        "系统采用三层拓扑，电力沿母线传输。",
        [
            {"family": "configuration", "support": [0], "key": "k1"},
            {"family": "architecture_route", "support": [1], "key": "k2"},
        ],
    ),
]


@pytest.mark.parametrize("mechanism,statement,specs", ATOMICITY_FAMILIES)
def test_all_s_d_atomicity_mechanisms_are_structurally_detected(mechanism, statement, specs):
    evidence = _evidence("CLM_TEST", statement)
    result = _evaluate(
        "CLM_TEST", statement, "fact", _ir("CLM_TEST", evidence, *specs), evidence
    )
    assert result["atomicity_guard"]["status"] == REVIEW_REQUIRED
    assert result["atomicity_guard"]["details"]["decision_basis"] == "EXPLICIT_COHERENCE_TYPES"
    assert mechanism in result["atomicity_guard"]["details"]["mechanism_classes"]


KEEP_CONTRASTS = [
    ("coordinated material specification", "材料纯度99.9%，导电率98%IACS。", "measurement", "SPEC_VECTOR"),
    ("paired simulation outputs", "仿真温升15℃，压降0.2V。", "measurement", "SIMULATION_SCENARIO"),
    ("one-product comparison vector", "产品A更轻，导电率更高。", "comparison", "COMPARISON_VECTOR"),
    ("one derived calculation", "根据P=UI，计算功率为400kW。", "calculation", "OTHER_COHERENT"),
    ("bounded reporting vector", "本期收入10亿元，利润2亿元。", "measurement", "REPORTING_VECTOR"),
    ("sequential architecture route", "电力经整流器进入母线，再到GPU。", "architecture_route", "SEQUENTIAL_ROUTE"),
    ("bounded analyst causal judgment", "功率上升导致电流增加，温升增加。", "causal_judgment", "CAUSAL_JUDGMENT"),
    ("product specification vector", "产品额定电流5000A，耐压800V。", "measurement", "SPEC_VECTOR"),
]


@pytest.mark.parametrize("_name,statement,family,coherence_type", KEEP_CONTRASTS)
def test_coherent_vectors_are_protected(_name, statement, family, coherence_type):
    evidence = _evidence("CLM_KEEP", statement)
    nature = "data" if family in {"measurement", "calculation"} else "fact"
    specs = [
        {
            "family": family,
            "nature": nature,
            "support": [index],
            "key": "k1",
            "coherence_type": coherence_type,
        }
        for index in range(len(evidence))
    ]
    result = _evaluate(
        "CLM_KEEP", statement, nature, _ir("CLM_KEEP", evidence, *specs), evidence
    )
    assert result["atomicity_guard"]["status"] == ADMISSIBLE
    assert result["atomicity_guard"]["reason_codes"] == ["COHERENT_VECTOR_OR_SCENARIO"]


@pytest.mark.parametrize(
    "statement,expected",
    [
        ("预计将提升效率", "FUTURE_AUXILIARY"),
        ("800V架构将进一步提高绝缘要求", "FUTURE_AUXILIARY"),
        ("将800V转换为50V", "OBJECT_FRONTING_DISPOSAL"),
        ("将方案应用于机柜", "OBJECT_FRONTING_DISPOSAL"),
        ("将冷却通道集成到母线", "OBJECT_FRONTING_DISPOSAL"),
        ("将路径分割为两段", "OBJECT_FRONTING_DISPOSAL"),
        ("可将温升控制在10℃", "OBJECT_FRONTING_CAPABILITY"),
        ("提出将高压电分配至机柜", "PROPOSAL_COMPLEMENT"),
    ],
)
def test_jiang_uses_local_syntax(statement, expected):
    assert classify_jiang_modality(statement) == expected


@pytest.mark.parametrize(
    "statement,family,nature",
    [
        ("Meta 800V项目已获定点。", "status", "fact"),
        ("NVIDIA 800V产品正在验证。", "status", "fact"),
        ("2026年该产品已量产。", "lifecycle", "fact"),
        ("NVL72系统处于运行状态。", "status", "fact"),
        ("产能达到60万吨。", "measurement", "data"),
    ],
)
def test_fact_vs_data_depends_on_proposition_not_digits(statement, family, nature):
    evidence = _evidence("CLM_NATURE", statement)
    ir = _ir(
        "CLM_NATURE", evidence, {"support": [0], "family": family, "nature": nature}
    )
    result = _evaluate("CLM_NATURE", statement, nature, ir, evidence)
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_reported_architecture_proposal_may_remain_fact():
    statement = "NVIDIA提出将高压电直接分配至机柜。"
    evidence = _evidence("CLM_PROPOSAL", statement)
    ir = _ir(
        "CLM_PROPOSAL",
        evidence,
        {"support": [0], "family": "architecture_route", "nature": "fact", "modality": "proposal"},
    )
    result = _evaluate("CLM_PROPOSAL", statement, "fact", ir, evidence)
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_quantitative_comparison_is_valid_data():
    statement = "铜导电率约101%IACS，而铝约55%IACS。"
    evidence = _evidence("CLM_COMPARISON", statement)
    ir = _ir(
        "CLM_COMPARISON",
        evidence,
        {
            "support": list(range(len(evidence))),
            "family": "comparison",
            "nature": "data",
            "coherence_type": "COMPARISON_VECTOR",
        },
    )
    result = _evaluate("CLM_COMPARISON", statement, "data", ir, evidence)
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_attributed_epistemic_nature_exact_match_is_admissible():
    statement = "800V架构将进一步提高绝缘要求。"
    evidence = _evidence("CLM_JUDGMENT", statement)
    ir = _ir(
        "CLM_JUDGMENT",
        evidence,
        {
            "support": [0],
            "family": "causal_judgment",
            "nature": "expert_judgment",
            "modality": "future",
            "time_scope": "future",
        },
    )
    result = _evaluate("CLM_JUDGMENT", statement, "expert_judgment", ir, evidence)
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_nature_runs_after_atomicity_per_unit():
    statement = "项目已定点，收入达到10亿元。"
    evidence = _evidence("CLM_MIXED", statement)
    ir = _ir(
        "CLM_MIXED",
        evidence,
        {"support": [0], "family": "status", "nature": "fact", "key": "k1"},
        {"support": [1], "family": "measurement", "nature": "data", "key": "k2"},
    )
    result = _evaluate("CLM_MIXED", statement, "data", ir, evidence)
    assert result["atomicity_guard"]["status"] == REVIEW_REQUIRED
    assert result["nature_consistency_guard"]["status"] == REVIEW_REQUIRED
    assert result["nature_consistency_guard"]["details"]["evaluation_order"] == "AFTER_ATOMICITY"


@pytest.mark.parametrize(
    ("statement", "specs", "expected_type", "expected_reason"),
    [
        (
            "2026年第一季度指标值为2.08亿元，同比增长23.01%。",
            [
                {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
            "REPORTING_VECTOR",
            "SAME_PERIOD_VALUE_AND_GROWTH",
        ),
        (
            "该指标从2020年的0.89增长至2025年的4.45，CAGR为37.99%。",
            [
                {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
            "REPORTING_VECTOR",
            "TIME_SERIES_WITH_DERIVED_GROWTH",
        ),
        (
            "共获得308项授权，其中甲地区209项、乙地区99项。",
            [
                {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
            "REPORTING_VECTOR",
            "TOTAL_AND_COMPONENT_DISTRIBUTION",
        ),
        (
            "指标A由9.72%降至4.75%，指标B由4.96%降至1.79%。",
            [
                {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
            "COMPARISON_VECTOR",
            "ALIGNED_PAIRED_COMPARISON",
        ),
        (
            "上层类别占总量7%，其中下层类别占上层类别49%。",
            [
                {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
            "REPORTING_VECTOR",
            "NESTED_COMPOSITION_VECTOR",
        ),
        (
            "主体于2004年成立，2008年首个产品量产，2015年设立子公司，2019年上市。",
            [
                {"family": "lifecycle", "nature": "fact", "support": [0], "key": "k1"},
                {"family": "lifecycle", "nature": "fact", "support": [1], "key": "k2"},
                {"family": "lifecycle", "nature": "fact", "support": [2], "key": "k3"},
                {"family": "lifecycle", "nature": "fact", "support": [3], "key": "k4"},
            ],
            "SEQUENTIAL_ROUTE",
            "EXPLICIT_CHRONOLOGICAL_HISTORY_SEQUENCE",
        ),
        (
            "该产品取得技术突破，首次应用并实现量产，显著提升客户良率。",
            [
                {"family": "status", "nature": "fact", "support": [0], "key": "k1"},
                {"family": "status", "nature": "fact", "support": [1], "key": "k2"},
                {"family": "measurement", "nature": "fact", "support": [2], "key": "k3"},
            ],
            "CAUSAL_JUDGMENT",
            "BREAKTHROUGH_APPLICATION_OUTCOME_CHAIN",
        ),
        (
            "该工艺通过机械与化学作用实现平整，可将落差控制在5nm以内。",
            [
                {"family": "capability", "nature": "fact", "support": [0], "key": "k1"},
                {
                    "family": "measurement",
                    "modality": "capability",
                    "nature": "fact",
                    "support": [1],
                    "key": "k2",
                },
            ],
            "CAUSAL_JUDGMENT",
            "MECHANISM_WITH_BOUNDED_CAPABILITY_OUTCOME",
        ),
        (
            "平台覆盖类型甲、乙与丙，其中多款子类型已实现量产。",
            [
                {
                    "family": "capability",
                    "nature": "fact",
                    "support": [0],
                    "key": "k1",
                    "coherence_type": "SPEC_VECTOR",
                },
                {"family": "lifecycle", "nature": "fact", "support": [1], "key": "k2"},
            ],
            "SINGLE_EVENT_ATTRIBUTES",
            "SPEC_VECTOR_WITH_NESTED_LIFECYCLE_ATTRIBUTE",
        ),
    ],
)
def test_fragmented_existing_coherence_classes_are_boundedly_reconciled(
    statement, specs, expected_type, expected_reason
):
    evidence = _evidence("CLM_RECONCILE", statement)
    result = _evaluate(
        "CLM_RECONCILE",
        statement,
        specs[0]["nature"],
        _ir("CLM_RECONCILE", evidence, *specs),
        evidence,
    )
    atomicity = result["atomicity_guard"]
    assert atomicity["status"] == ADMISSIBLE
    assert atomicity["reason_codes"] == ["COHERENT_VECTOR_OR_SCENARIO"]
    assert atomicity["details"]["bounded_coherence_override"] == {
        "coherence_type": expected_type,
        "reason": expected_reason,
    }


@pytest.mark.parametrize(
    ("statement", "specs"),
    [
        (
            "产品甲在客户一量产，产品乙在客户二送样。",
            [
                {"family": "status", "nature": "fact", "support": [0], "key": "k1"},
                {"family": "status", "nature": "fact", "support": [1], "key": "k2"},
            ],
        ),
        (
            "平台的产品甲已量产，产品乙仍在验证。",
            [
                {"family": "status", "nature": "fact", "support": [0], "key": "k1"},
                {"family": "status", "nature": "fact", "support": [1], "key": "k2"},
            ],
        ),
        (
            "该技术用于节点甲，独立市场占比为45%。",
            [
                {"family": "application", "nature": "fact", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
        ),
        (
            "总体指标从15%升至34%，尤其在较窄范围内另一指标超过50%。",
            [
                {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
                {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
            ],
        ),
        (
            "同一主体的项目甲已定点，项目乙正在送样。",
            [
                {"family": "status", "nature": "fact", "support": [0], "key": "k1"},
                {"family": "status", "nature": "fact", "support": [1], "key": "k2"},
            ],
        ),
    ],
)
def test_bounded_coherence_reconciliation_preserves_independent_negative_contrasts(
    statement, specs
):
    evidence = _evidence("CLM_NEGATIVE", statement)
    result = _evaluate(
        "CLM_NEGATIVE",
        statement,
        "data" if all(spec["nature"] == "data" for spec in specs) else "fact",
        _ir("CLM_NEGATIVE", evidence, *specs),
        evidence,
    )
    assert result["atomicity_guard"]["status"] == REVIEW_REQUIRED
    assert result["atomicity_guard"]["reason_codes"] == [
        "INDEPENDENT_REVIEWABLE_PROPOSITIONS"
    ]


def test_nature_precision_allows_status_units_in_a_coherent_ranked_data_snapshot():
    statement = "截至2026年第一季度，第一位主体占29.57%，第二位主体占18.89%。"
    evidence = _evidence("CLM_RANKED", statement)
    ir = _ir(
        "CLM_RANKED",
        evidence,
        {"family": "status", "nature": "data", "support": [0, 1], "key": "k1"},
        {"family": "status", "nature": "data", "support": [2], "key": "k2"},
    )
    result = _evaluate("CLM_RANKED", statement, "data", ir, evidence)
    assert result["atomicity_guard"]["status"] == ADMISSIBLE
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_nature_precision_allows_identity_inside_a_market_structure_data_vector():
    statement = "核心厂商包括甲、乙、丙等，前三大厂商合计占全球约65%的份额。"
    evidence = _evidence("CLM_MARKET_STRUCTURE", statement)
    result = _evaluate(
        "CLM_MARKET_STRUCTURE",
        statement,
        "data",
        _ir(
            "CLM_MARKET_STRUCTURE",
            evidence,
            {"family": "identity", "nature": "data", "support": [0], "key": "k1"},
            {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
        ),
        evidence,
    )
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_nature_precision_allows_nonquantitative_outcome_and_capability_bound_fact():
    qualitative = "技术改进已落地，显著提升最终质量。"
    evidence = _evidence("CLM_QUALITATIVE", qualitative)
    result = _evaluate(
        "CLM_QUALITATIVE",
        qualitative,
        "fact",
        _ir(
            "CLM_QUALITATIVE",
            evidence,
            {"family": "status", "nature": "fact", "support": [0], "key": "k1"},
            {"family": "measurement", "nature": "fact", "support": [1], "key": "k2"},
        ),
        evidence,
    )
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE

    bounded = "该结构形成稳定界面，可将偏差控制在5nm以内。"
    evidence = _evidence("CLM_BOUND", bounded)
    result = _evaluate(
        "CLM_BOUND",
        bounded,
        "fact",
        _ir(
            "CLM_BOUND",
            evidence,
            {"family": "capability", "nature": "fact", "support": [0], "key": "k1"},
            {
                "family": "measurement",
                "modality": "capability",
                "nature": "fact",
                "support": [1],
                "key": "k2",
            },
        ),
        evidence,
    )
    assert result["nature_consistency_guard"]["status"] == ADMISSIBLE


def test_nature_precision_preserves_future_and_independent_fact_data_reviews():
    future = "2025年规模为10亿元，预计2026年增至12亿元。"
    evidence = _evidence("CLM_FUTURE", future)
    result = _evaluate(
        "CLM_FUTURE",
        future,
        "data",
        _ir(
            "CLM_FUTURE",
            evidence,
            {"family": "measurement", "nature": "data", "support": [0], "key": "k1"},
            {
                "family": "measurement",
                "modality": "future",
                "nature": "data",
                "support": [1],
                "key": "k2",
                "time_scope": "future",
            },
        ),
        evidence,
    )
    assert result["atomicity_guard"]["status"] == ADMISSIBLE
    assert result["nature_consistency_guard"]["status"] == REVIEW_REQUIRED
    assert "FORWARD_OR_CONDITIONAL_PROPOSITION_CLASSIFIED_AS_FACT_OR_DATA" in result[
        "nature_consistency_guard"
    ]["reason_codes"]

    mixed = "技术用于节点甲，独立市场占比为45%。"
    evidence = _evidence("CLM_MIXED_PROTECT", mixed)
    result = _evaluate(
        "CLM_MIXED_PROTECT",
        mixed,
        "data",
        _ir(
            "CLM_MIXED_PROTECT",
            evidence,
            {"family": "application", "nature": "fact", "support": [0], "key": "k1"},
            {"family": "measurement", "nature": "data", "support": [1], "key": "k2"},
        ),
        evidence,
    )
    assert result["atomicity_guard"]["status"] == REVIEW_REQUIRED
    assert result["nature_consistency_guard"]["status"] == REVIEW_REQUIRED


def test_legacy_claims_use_explicit_compatibility_path():
    result = evaluate_semantic_admission(
        statement="产品已量产，最高支持7200 MT/s。",
        attributed_to="研究机构",
        permitted_support_text="产品已量产，最高支持7200 MT/s。",
        support_region_authoritative=True,
        nature="data",
    )
    assert result["proposition_ir_validation"]["status"] == "LEGACY_NOT_PRESENT"
    assert result["semantic_pipeline"]["compatibility_path"] == "LEGACY_PHASE3E2SB_V1"


def test_analyzer_never_splits_or_reclassifies_parent_claims():
    claims = [{
        "statement": "公司目前完成验证，预计2027年量产。",
        "nature": "company_guidance",
        "structured": {"company": "公司"},
    }]
    assert Analyzer._normalize_claim_atomicity(copy.deepcopy(claims)) == claims


class FakeBackend:
    backend_name = "fake-local-compatible"

    def __init__(self, *, truncate_above: int | None = None):
        self.truncate_above = truncate_above
        self.calls: list[list[str]] = []
        self.evidence_ids_by_call: list[dict[str, list[str]]] = []
        self._metadata: dict = {}

    @property
    def last_call_metadata(self):
        return self._metadata

    def decompose_batch(self, claims):
        self.calls.append([item["claim_id"] for item in claims])
        self.evidence_ids_by_call.append({
            item["claim_id"]: [unit["evidence_unit_id"] for unit in item["evidence_units"]]
            for item in claims
        })
        if self.truncate_above is not None and len(claims) > self.truncate_above:
            self._metadata = {"attempts": [{
                "finish_reason": "length", "prompt_tokens": 40,
                "completion_tokens": 50, "total_tokens": 90,
            }]}
            raise LLMError("failure_category=output_truncation")
        self._metadata = {"attempts": [{
            "finish_reason": "stop", "prompt_tokens": 20,
            "completion_tokens": 10, "total_tokens": 30,
        }]}
        return {"claims": [{
            "parent_claim_id": item["claim_id"],
            "ir_status": "VALID",
            "units": [{
                "predicate_family": "status",
                "modality": "actual",
                "nature": "fact",
                "support_evidence_unit_ids": [item["evidence_units"][0]["evidence_unit_id"]],
                "coherence_key": "k1",
                "coherence_type": "INDEPENDENT",
                "time_scope": "current",
            }],
        } for item in claims]}


def _semantic_inputs(count: int) -> list[dict]:
    result = []
    for index in range(count):
        claim_id = f"CLM_{index}"
        text = f"项目{index}已验证。"
        result.append({
            "claim_id": claim_id,
            "claim_text": text,
            "evidence_units": _evidence(claim_id, text),
            "attribution": "研究机构",
            "scope": "",
            "fact_time": "",
            "assigned_nature": "fact",
        })
    return result


def test_semantic_decomposer_preserves_exact_parent_universe_and_order():
    inputs = _semantic_inputs(13)
    result = SemanticDecomposer(FakeBackend(), batch_size=8).run(inputs)
    expected = [item["claim_id"] for item in inputs]
    assert result["input_parent_claim_ids"] == expected
    assert result["output_parent_claim_ids"] == expected
    assert result["parent_claim_id_match"] == 13
    assert result["new_parent_claims"] == result["missing_parent_claims"] == 0
    assert result["counts"]["valid_proposition_ir_claims"] == 13
    assert result["invariants"]["MODEL_GENERATED_RAW_EVIDENCE_OFFSETS"] is False


def test_length_retry_never_changes_claims_or_evidence_identity():
    backend = FakeBackend(truncate_above=2)
    inputs = _semantic_inputs(4)
    result = SemanticDecomposer(backend, batch_size=4).run(inputs)
    assert [len(batch) for batch in backend.calls] == [4, 2, 2]
    assert result["semantic_length_retries"] == 1
    assert result["semantic_length_retry_changes_claims"] is False
    assert result["semantic_length_retry_changes_evidence_units"] is False
    first_ids = backend.evidence_ids_by_call[0]
    for later in backend.evidence_ids_by_call[1:]:
        for claim_id, ids in later.items():
            assert ids == first_ids[claim_id]


def test_free_text_and_raw_offset_model_fields_are_rejected():
    claim = _semantic_inputs(1)[0]
    raw = {
        "parent_claim_id": claim["claim_id"],
        "ir_status": "VALID",
        "units": [{
            "predicate_family": "status",
            "modality": "actual",
            "nature": "fact",
            "support_evidence_unit_ids": [claim["evidence_units"][0]["evidence_unit_id"]],
            "coherence_key": "k1",
            "coherence_type": "INDEPENDENT",
            "time_scope": "current",
            "evidence_span": [0, 3],
        }],
    }
    normalized = normalize_model_result(claim, raw)
    assert normalized["validation"]["status"] == "AMBIGUOUS"
    assert normalized["validation"]["unsupported_content_failures"] == 1
    assert "evidence_span" not in normalized["proposition_ir"]["units"][0]


def test_semantic_input_builder_contains_only_evidence_units_not_raw_evidence():
    bundle = {"claims": [{
        "claim_id": "CLM_1", "statement": "项目完成验证。",
        "evidence_excerpt": "项目完成验证", "nature": "fact",
    }]}
    evidence = {"claims": [{"claim_id": "CLM_1", "original_evidence_excerpt": "项目完成验证"}]}
    quote = {"claims": [{
        "claim_id": "CLM_1",
        "resolved_locator": {"locator": "PAGE:1"},
        "evidence_contract": {"canonical_ready_evidence": "项目完成验证"},
    }]}
    first = build_semantic_claim_inputs(
        bundle=bundle, evidence_draft=evidence, quote_fidelity=quote
    )
    second = build_semantic_claim_inputs(
        bundle=bundle, evidence_draft=evidence, quote_fidelity=quote
    )
    assert set(first[0]) == {
        "claim_id", "claim_text", "evidence_units", "attribution",
        "scope", "fact_time", "assigned_nature",
    }
    assert first[0]["evidence_units"] == second[0]["evidence_units"]
    assert "bounded_evidence" not in first[0]
    assert "pdf" not in str(first).lower()
    assert "node" not in str(first).lower()
