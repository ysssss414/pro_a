from __future__ import annotations

import json

from scripts.activate_phase2_4b import (
    MLCC_NODE_ID,
    MLCC_PRIMARY,
    YUNZHONG_NODE_ID,
    YUNZHONG_PRIMARY,
    YUNZHONG_UNRESOLVED,
    approved_payloads,
)


def test_human_approved_payloads_are_exact_and_subject_scoped():
    payloads = approved_payloads()
    mlcc = payloads[MLCC_NODE_ID]
    yunzhong = payloads[YUNZHONG_NODE_ID]
    assert mlcc["one_line_conclusion"] == "据现有财通证券业绩会更新材料，2026年7月和8月MLCC单月价格环比均上涨30%以上；关于本轮周期持续时间更长及AI需求形成挤出效应，目前仅有该材料中的分析判断，尚缺独立证据交叉验证。"
    assert mlcc["evidence_claim_ids"] == MLCC_PRIMARY
    assert mlcc["type_specific"]["applications"] == []
    assert mlcc["type_specific"]["supply_capacity"] == []
    assert mlcc["type_specific"]["major_suppliers"] == []
    assert yunzhong["evidence_claim_ids"] == YUNZHONG_PRIMARY
    assert yunzhong["key_watch_items"][2] == "跟踪106、107实验室阶段进展及后续认证。"
    assert yunzhong["assumptions_to_verify"] == [
        "昀冢科技高容和超高容产品占新扩产产能比例70%以上。",
        "昀冢科技关于MLCC上行周期提前的判断。",
    ]
    assert set(YUNZHONG_UNRESOLVED).isdisjoint(yunzhong["evidence_claim_ids"])


def test_payload_serialization_keeps_uncertainty_and_guidance_semantics():
    payloads = approved_payloads()
    raw = json.dumps(payloads[YUNZHONG_NODE_ID], ensure_ascii=False)
    assert "公司" in raw
    assert "指引" in raw
    assert "70%以上" in raw
    assert "上行周期提前" in raw
