from __future__ import annotations

import pytest

from pro_a.operational_ingestion import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    _same_source_duplicate_pairs,
)


def _claim(claim_id: str, statement: str, **extra: object) -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "statement": statement,
        "nature": "expert_judgment",
        **extra,
    }


def _duplicates(left: str, right: str, **shared: object) -> dict[str, str]:
    return _same_source_duplicate_pairs(
        [
            _claim("CLM_LEFT", left, **shared),
            _claim("CLM_RIGHT", right, **shared),
        ]
    )


@pytest.mark.parametrize(
    ("case_id", "left", "right"),
    [
        (
            "economics_vs_safety",
            "在复杂部署中，标准接口的经济性更具优势。",
            "在复杂部署中，标准接口的安全性更具优势。",
        ),
        (
            "cost_vs_performance",
            "在复杂部署中，标准接口的成本优势更具普适性。",
            "在复杂部署中，标准接口的性能优势更具普适性。",
        ),
        (
            "reliability_vs_maintainability",
            "在复杂部署中，标准接口的可靠性更具优势。",
            "在复杂部署中，标准接口的可维护性更具优势。",
        ),
        (
            "capacity_vs_latency",
            "在复杂部署中，标准接口的容量表现更具优势。",
            "在复杂部署中，标准接口的时延表现更具优势。",
        ),
        (
            "power_vs_bandwidth",
            "在复杂部署中，标准接口的功率优势更具普适性。",
            "在复杂部署中，标准接口的带宽优势更具普适性。",
        ),
        (
            "different_condition",
            "若环境温度高于设计值，标准接口的传输效率将提高。",
            "若链路负载低于设计值，标准接口的传输效率将提高。",
        ),
        (
            "opposite_outcome",
            "在复杂部署中，标准接口的传输效率将提高。",
            "在复杂部署中，标准接口的传输效率将下降。",
        ),
        (
            "different_measurement",
            "测试显示标准接口的峰值带宽为100Gbps。",
            "测试显示标准接口的峰值带宽为200Gbps。",
        ),
        (
            "different_parent_subproposition",
            "系统由两类模块组成，标准接口的扩容收益相对更具普适性。",
            "标准接口的维护成本逻辑更具普适性。",
        ),
        (
            "current_vs_future",
            "当前平台的部署状态更具确定性。",
            "未来平台的部署状态更具确定性。",
        ),
        (
            "revenue_vs_margin",
            "在同一报告期内，公司的收入表现更具优势。",
            "在同一报告期内，公司的利润率表现更具优势。",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) and "_" in value else None,
)
def test_meaning_bearing_contrasts_are_not_duplicates(
    case_id: str, left: str, right: str
) -> None:
    assert case_id
    assert _duplicates(left, right) == {}


def test_same_evidence_neighborhood_does_not_override_different_claim_meaning() -> None:
    shared = {
        "source_id": "SRC_SHARED",
        "origin_piece_sha256": "a" * 64,
        "evidence_excerpt": "同一证据段讨论了标准接口的经济性与安全性。",
        "evidence_validated": True,
        "attributed_to": "研究机构",
        "scope": "标准接口",
    }

    assert _duplicates(
        "系统方案位于同一证据段，标准接口的经济性相对更具优势。",
        "标准接口的安全性逻辑更具优势。",
        **shared,
    ) == {}


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (
            "标准接口能够复用现有机房的布线基础设施。",
            "标准接口能够复用现有机房的布线基础设施。",
        ),
        (
            "标准接口能够复用现有机房的布线基础设施。",
            "标准接口 能够复用现有机房的布线基础设施！",
        ),
    ],
    ids=["exact", "layout_only"],
)
def test_exact_and_layout_only_variants_are_duplicates(left: str, right: str) -> None:
    assert _duplicates(left, right) == {"CLM_RIGHT": "CLM_LEFT"}


@pytest.mark.parametrize(
    ("left", "right", "parent_scope", "child_scope"),
    [
        (
            "专用适配器依赖部署路线，标准接口的扩容收益相对更具普适性。",
            "标准接口的扩容收益逻辑更具普适性。",
            "部署方案",
            "标准接口",
        ),
        (
            "保偏光纤等产品具有技术路线依赖，FAU和高密度连接的增量相对更具普适性。",
            "FAU和高密度连接的增量逻辑更具普适性。",
            "CPO产业链",
            "FAU和高密度连接",
        ),
    ],
    ids=["generic_parent_subproposition", "frozen_s_k_fixture"],
)
def test_genuinely_repeated_parent_subpropositions_are_duplicates(
    left: str, right: str, parent_scope: str, child_scope: str
) -> None:
    shared = {
        "source_id": "SRC_SHARED",
        "origin_piece_sha256": "a" * 64,
        "attributed_to": "研究机构",
        "evidence_validated": True,
    }
    assert _same_source_duplicate_pairs(
        [
            _claim("CLM_LEFT", left, scope=parent_scope, **shared),
            _claim("CLM_RIGHT", right, scope=child_scope, **shared),
        ]
    ) == {"CLM_RIGHT": "CLM_LEFT"}


def test_duplicate_similarity_threshold_remains_frozen() -> None:
    assert DUPLICATE_SIMILARITY_THRESHOLD == 0.92
