from __future__ import annotations

import copy
from pathlib import Path

import pytest

from pro_a.phase3f_handoff_requalification import (
    ADAPTER_TYPE,
    HandoffRequalificationError,
    REVIEW_SCOPE,
    _build_relation_operations,
    build_requalification_artifacts,
    validate_qualification_only_payload,
)
from pro_a.production_promotion import canonical_sha256, payload_semantic_body


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "workspace" / "phase3e2sl6" / "operational_run"
QUALIFICATION_ROOT = ROOT / "workspace" / "phase3f_stage1_qualification_review"
SOURCE_PACKET = (
    ROOT
    / "workspace"
    / "phase3f_stage1_review_completion"
    / "operational_review_packet.json"
)
PRODUCTION = ROOT / "workspace" / "pro_a.db"
TEST_REPOSITORY_COMMIT = "1" * 40
pytestmark = pytest.mark.skipif(
    not all(
        path.is_file()
        for path in (
            RUN_ROOT / "evidence" / "evidence_bound_extraction_bundle.json",
            SOURCE_PACKET,
            QUALIFICATION_ROOT / "qualification_review_packet.completed.json",
        )
    ),
    reason="local evidence-bearing Phase 3F audit fixture is intentionally untracked",
)


def _build() -> dict:
    return build_requalification_artifacts(
        repository_commit=TEST_REPOSITORY_COMMIT,
        blank_packet_path=QUALIFICATION_ROOT / "qualification_review_packet.json",
        completed_packet_path=(
            QUALIFICATION_ROOT / "qualification_review_packet.completed.json"
        ),
        authorization_path=(
            QUALIFICATION_ROOT / "qualification_review_human_authorization.json"
        ),
        completion_receipt_path=(
            QUALIFICATION_ROOT / "qualification_review_completion_receipt.json"
        ),
        qualification_manifest_path=(
            QUALIFICATION_ROOT / "qualification_review_manifest.json"
        ),
        qualification_view_path=(
            QUALIFICATION_ROOT / "qualification_review_view.md"
        ),
        source_packet_path=SOURCE_PACKET,
        run_root=RUN_ROOT,
        production_path=PRODUCTION,
        repository_root=ROOT,
    )


@pytest.fixture(scope="module")
def artifacts() -> dict:
    return _build()


def _rehash_payload(payload: dict) -> dict:
    body = payload_semantic_body(payload)
    digest = canonical_sha256(body)
    return {
        **body,
        "payload_id": f"PROMO_{digest[:16].upper()}",
        "payload_hash": digest,
    }


def test_exact_seven_item_handoff_and_phase3d_validation(artifacts: dict) -> None:
    mapping = artifacts["handoff_mapping.json"]
    payload = artifacts["qualification_promotion_candidate.json"]
    validation = artifacts["phase3d_validation_receipt.json"]
    receipt = artifacts["stage1_requalification_receipt.json"]

    assert mapping["review_scope"] == REVIEW_SCOPE
    assert mapping["counts"] == {
        "qualification_candidates": 7,
        "promotable": 4,
        "blocked": 3,
    }
    by_id = {item["candidate_id"]: item for item in mapping["records"]}
    assert by_id["CLM_07152FCFBF4C3D1B"]["disposition"] == "QUALIFICATION_PROMOTABLE"
    assert by_id["CAND_NODE_E8A75C771486B74E"]["phase3d_object"]["operation"] == "CREATE"
    assert by_id["CAND_NODE_E7C5A8860931121D"]["phase3d_object"] == {
        "object_type": "NODE_OPERATION",
        "operation_id": by_id["CAND_NODE_E7C5A8860931121D"]["phase3d_object"]["operation_id"],
        "operation": "REUSE",
        "node_id": "NODE_20260814_1D6371B9",
        "executable": True,
    }
    assert by_id["PARENT_PLACEMENT_67ADDE309C1A5CAB"]["phase3d_object"]["operation"] == "CREATE"
    for candidate_id in (
        "CLM_74B65D5D09781B64",
        "CLM_229114C7C3F70FE9",
        "CAND_NODE_757A9745164C0433",
    ):
        assert by_id[candidate_id]["disposition"] == "QUALIFICATION_BLOCKED"
        assert by_id[candidate_id]["phase3d_object"] is None

    assert payload["adapter_type"] == ADAPTER_TYPE
    assert payload["qualified_execution_target"] == "SHADOW_ONLY_QUALIFICATION"
    assert payload["link_operations"] == []
    assert [item["table"] for item in payload["intended_mutations"]] == [
        "sources",
        "claims",
        "nodes",
        "node_aliases",
        "node_aliases",
        "node_relations",
    ]
    assert validation["status"] == "PASS"
    assert validation["phase3d_validation"]["payload_validation"] == "PASS"
    assert validation["phase3d_validation"]["preapply_validation"] == "PASS"
    assert validation["phase3d_validation"]["shadow_apply"] == "COMMITTED"
    assert validation["phase3d_validation"]["idempotent_replay"] == "PASS"
    assert validation["phase3d_validation"]["rollback"] == "PASS"
    assert receipt["status"] == "PASS"
    assert receipt["production_changed"] is False
    assert receipt["phase3f_stage2_started"] is False
    assert receipt["llm_calls"] == 0


def test_qualification_only_boundary_cannot_be_widened(artifacts: dict) -> None:
    payload = copy.deepcopy(
        artifacts["qualification_promotion_candidate.json"]
    )
    payload["production_authorization"] = True
    payload = _rehash_payload(payload)
    with pytest.raises(
        HandoffRequalificationError,
        match="QUALIFICATION_ONLY_GUARD_MISMATCH: production_authorization",
    ):
        validate_qualification_only_payload(payload)


def test_parent_placement_requires_executable_create_child(artifacts: dict) -> None:
    payload = artifacts["qualification_promotion_candidate.json"]
    relation = payload["relation_operations"][0]
    child_id = relation["candidate"]["child_node_candidate_id"]
    child = copy.deepcopy(
        next(
            item
            for item in payload["node_operations"]
            if item["candidate_id"] == child_id
        )
    )
    child["executable"] = False
    completed_relation = {
        "run": {"run_id": payload["metadata"]["run_id"]},
        "relations": [
            {
                "candidate_id": relation["candidate_id"],
                "content": copy.deepcopy(relation["candidate"]),
                "human_input": {
                    "decision": "CREATE",
                    "reason": relation["reason"],
                },
            }
        ],
    }
    with pytest.raises(
        HandoffRequalificationError,
        match="PARENT_PLACEMENT_CREATE_CONDITION_FAILED",
    ):
        _build_relation_operations(
            completed_relation,
            [child],
            payload["metadata"]["frozen_timestamp"],
        )


def test_requalification_build_is_deterministic(artifacts: dict) -> None:
    assert _build() == artifacts
