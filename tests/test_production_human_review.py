from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pro_a.production_authorization import (
    authoritative_human_decisions,
    bind_human_node_review,
)
from pro_a.production_promotion import PromotionError, apply_payload_to_shadow, production_identity


ROOT = Path(__file__).resolve().parents[1]
STAGE3D2 = ROOT / "workspace" / "phase3d" / "STAGE3D2_QUALIFICATION_F6A9ECB_V2"
STAGE3D3A = ROOT / "workspace" / "phase3d" / "STAGE3D3A_AUTHORIZATION_PREP_637D772"
PRODUCTION = STAGE3D2 / "production_shadow_restore.db"
AVAILABLE = all((
    (STAGE3D2 / "phase3d_promotion_payload.json").is_file(),
    (STAGE3D3A / "node_operation_review.json").is_file(),
    (STAGE3D3A / "source_materialization.json").is_file(),
    PRODUCTION.is_file(),
))
requires_stage3d3a = pytest.mark.skipif(not AVAILABLE, reason="Frozen local Stage 3D.3A package unavailable")


@pytest.fixture(scope="session")
def inputs() -> tuple[dict, dict, dict]:
    if not AVAILABLE:
        pytest.skip("Frozen local Stage 3D.3A package unavailable")
    return tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (
            STAGE3D3A / "node_operation_review.json",
            STAGE3D2 / "phase3d_promotion_payload.json",
            STAGE3D3A / "source_materialization.json",
        )
    )


def bind(inputs: tuple[dict, dict, dict], decisions: list[dict] | None = None) -> dict:
    draft, payload, source = inputs
    return bind_human_node_review(
        draft_review=draft,
        payload=payload,
        source_materialization=source,
        decisions=decisions if decisions is not None else authoritative_human_decisions(),
        production_path=PRODUCTION,
    )


@requires_stage3d3a
def test_exact_26_human_decisions_bind_with_expected_counts(inputs: tuple[dict, dict, dict]):
    review = bind(inputs)
    assert review["review_status"] == "HUMAN_REVIEW_COMPLETE"
    assert review["human_review_universe"]["observed"] == 26
    assert review["operation_counts"] == {"REUSE": 6, "CREATE": 8, "DEFER": 7, "REJECT": 5}
    assert review["decision_authority"]["authority"] == "USER_HUMAN_REVIEW"
    assert review["decision_authority"]["llm_authorization_used"] is False
    records = {record["operation_candidate_id"]: record for record in review["records"]}
    assert "VPD" in records["CAND_NODE_7C4F495527737096"]["reviewed_identity_intent"]["aliases"]
    assert "SPD" in records["CAND_NODE_C195F1E21A50449B"]["reviewed_identity_intent"]["aliases"]
    assert "CMM-D" not in records["CAND_NODE_43BE3226A7EACED0"]["reviewed_identity_intent"]["aliases"]
    assert records["CAND_NODE_60282E35851EA5A9"]["reviewed_identity_intent"]["primary_type"] == "Standard"
    assert all(record["executable"] is False for record in review["records"])


@requires_stage3d3a
def test_wrong_candidate_id_fails(inputs: tuple[dict, dict, dict]):
    decisions = authoritative_human_decisions()
    decisions[0]["operation_candidate_id"] = "CAND_NODE_WRONG"
    with pytest.raises(PromotionError, match="HUMAN_DECISION_UNIVERSE_MISMATCH"):
        bind(inputs, decisions)


@requires_stage3d3a
def test_missing_decision_fails(inputs: tuple[dict, dict, dict]):
    decisions = authoritative_human_decisions()[:-1]
    with pytest.raises(PromotionError, match="HUMAN_DECISION_COUNT_MISMATCH"):
        bind(inputs, decisions)


@requires_stage3d3a
def test_duplicate_decision_fails(inputs: tuple[dict, dict, dict]):
    decisions = authoritative_human_decisions()
    decisions[-1] = copy.deepcopy(decisions[0])
    with pytest.raises(PromotionError, match="DUPLICATE_HUMAN_DECISION"):
        bind(inputs, decisions)


@requires_stage3d3a
def test_wrong_reuse_target_fails(inputs: tuple[dict, dict, dict]):
    decisions = authoritative_human_decisions()
    decisions[0]["target_node_id"] = "NODE_WRONG"
    with pytest.raises(PromotionError, match="HUMAN_REUSE_TARGET_MISMATCH"):
        bind(inputs, decisions)


@requires_stage3d3a
@pytest.mark.parametrize("decision", ["CREATE", "DEFER", "REJECT"])
def test_unexpected_decision_classification_fails(
    inputs: tuple[dict, dict, dict], decision: str,
):
    decisions = authoritative_human_decisions()
    decisions[0]["decision"] = decision
    decisions[0]["target_node_id"] = None
    with pytest.raises(PromotionError, match="HUMAN_DECISION_CLASSIFICATION_MISMATCH"):
        bind(inputs, decisions)


@requires_stage3d3a
def test_defer_and_rejected_duplicates_remain_nonexecutable(inputs: tuple[dict, dict, dict]):
    review = bind(inputs)
    records = {record["operation_candidate_id"]: record for record in review["records"]}
    for candidate_id in (
        "CAND_NODE_529AA01F61DD9AAE",
        "CAND_NODE_935CA33A2E606936",
        "CAND_NODE_6236100CBA90F567",
        "CAND_NODE_D165AC3C72E91B14",
        "CAND_NODE_334EE0153DF753B9",
    ):
        assert records[candidate_id]["executable"] is False
        assert records[candidate_id]["execution_state"] == "HUMAN_DECISION_NONEXECUTABLE"


@requires_stage3d3a
def test_source_blocker_prevents_executable_or_final_payload(inputs: tuple[dict, dict, dict]):
    review = bind(inputs)
    assert review["source_blocker"] == {
        "expected_source_sha256": "572a6df2b583358506e2a4fb86359a07e9a1503a3507dcdd2c81a8d97c27e97a",
        "source_file_found": False,
        "source_sha_match": False,
        "source_archive_materialization_ready": False,
    }
    assert review["authorization_state"]["executable"] is False
    assert review["authorization_state"]["blocked_by"] == ["SOURCE_ARCHIVE_MATERIALIZATION"]
    assert review["authorization_state"]["final_production_payload_generated"] is False
    assert review["authorization_state"]["production_apply_authorized"] is False


@requires_stage3d3a
def test_production_unchanged_and_hard_blocked(inputs: tuple[dict, dict, dict]):
    before = production_identity(PRODUCTION)
    review = bind(inputs)
    after = production_identity(PRODUCTION)
    assert before["sha256"] == review["production_baseline"]["sha256"] == after["sha256"]
    assert before["sidecars"] == after["sidecars"] == {"-wal": False, "-shm": False, "-journal": False}
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        apply_payload_to_shadow(inputs[1], PRODUCTION, PRODUCTION)
