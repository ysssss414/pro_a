from __future__ import annotations

import copy
from pathlib import Path

import pytest

from pro_a.phase3f_review_completion import (
    ReviewCompletionError,
    build_blank_review_packet,
    read_review_packet,
    validate_blank_review_packet,
    validate_completed_review_packet,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "workspace" / "phase3e2sl6" / "operational_run"
PACKET_PATH = (
    ROOT
    / "workspace"
    / "phase3f_stage1_review_completion"
    / "operational_review_packet.json"
)
SYNTHETIC_REVIEWER = "SYNTHETIC_TEST_REVIEWER_NOT_OPERATIONAL_AUTHORITY"
SYNTHETIC_REASON = "SYNTHETIC VALIDATOR FIXTURE; NOT AN OPERATIONAL DECISION."
pytestmark = pytest.mark.skipif(
    not PACKET_PATH.is_file(),
    reason="local evidence-bearing Phase 3F audit fixture is intentionally untracked",
)


@pytest.fixture
def blank_packet() -> dict:
    return read_review_packet(PACKET_PATH)


def synthetic_completed_packet(blank_packet: dict) -> dict:
    """Create an in-memory negative-only completion; never persist or authorize it."""
    packet = copy.deepcopy(blank_packet)
    packet["human_completion"]["reviewer"] = SYNTHETIC_REVIEWER
    for record in packet["claims"]:
        record["human_input"].update({"decision": "DROP", "reason": SYNTHETIC_REASON})
    for record in packet["nodes"]:
        record["human_input"].update({
            "decision": "REJECT",
            "reason": SYNTHETIC_REASON,
            "target_node_id": "",
        })
    for record in packet["relations"]:
        record["human_input"].update({"decision": "REJECT", "reason": SYNTHETIC_REASON})
    return packet


def test_real_blank_packet_is_hash_bound_deterministic_and_has_no_decisions(
    blank_packet: dict,
):
    rebuilt = build_blank_review_packet(RUN_ROOT)
    assert blank_packet == rebuilt == build_blank_review_packet(RUN_ROOT)
    receipt = validate_blank_review_packet(blank_packet, RUN_ROOT)

    assert receipt["status"] == "VALID_BLANK_REVIEW_PACKET"
    assert blank_packet["summary"] == {
        "claims_requiring_decision": 121,
        "nodes_requiring_decision": 77,
        "aliases_requiring_decision": 0,
        "relations_requiring_decision": 7,
        "total_operational_decisions_required": 205,
        "proposed_aliases_within_node_review": 97,
        "audit_only_rejected_relations": 31,
        "candidate_universe_sha256": "576792afb3e1fc798716f24f705cf655746ae58c02bbe338f4a827135e75c28a",
    }
    assert blank_packet["human_completion"]["reviewer"] == ""
    for group in ("claims", "nodes", "relations"):
        assert all(
            all(value == "" for value in record["human_input"].values())
            for record in blank_packet[group]
        )
    serialized = PACKET_PATH.read_text(encoding="utf-8")
    assert "HUMAN_KEEP" not in serialized
    assert "HUMAN_NEEDS_REPAIR" not in serialized
    assert "phase3e2sl6_human_semantic_review" not in serialized
    assert blank_packet["safety"]["evaluation_gold_used_as_authorization"] is False
    assert blank_packet["safety"]["production_apply_authorized"] is False


def test_clearly_synthetic_completed_fixture_validates_without_authorizing_production(
    blank_packet: dict,
):
    packet = synthetic_completed_packet(blank_packet)
    receipt = validate_completed_review_packet(packet, RUN_ROOT)

    assert receipt["status"] == "HUMAN_REVIEW_COMPLETE_AND_VALID"
    assert receipt["validation_scope"] == "FULL_OPERATIONAL_REVIEW_COMPLETION"
    assert receipt["total_operational_decisions_validated"] == 205
    assert receipt["decision_counts"]["claims"]["DROP"] == 121
    assert receipt["decision_counts"]["nodes"]["REJECT"] == 77
    assert receipt["decision_counts"]["relations"]["REJECT"] == 7
    assert receipt["reviewer"] == SYNTHETIC_REVIEWER
    assert receipt["llm_authorization_used"] is False
    assert receipt["production_apply_authorized"] is False


@pytest.mark.parametrize(
    ("decision", "error"),
    [
        ("", "MISSING_DECISION"),
        ("ACCEPT", "UNKNOWN_DECISION"),
        ("HUMAN_KEEP", "UNKNOWN_DECISION"),
    ],
)
def test_missing_unknown_and_gold_labels_fail_closed(
    blank_packet: dict, decision: str, error: str
):
    packet = synthetic_completed_packet(blank_packet)
    packet["claims"][0]["human_input"]["decision"] = decision
    with pytest.raises(ReviewCompletionError, match=error):
        validate_completed_review_packet(packet, RUN_ROOT)


def test_immutable_candidate_tamper_fails(blank_packet: dict):
    packet = copy.deepcopy(blank_packet)
    packet["claims"][0]["content"]["statement"] += " altered"
    with pytest.raises(ReviewCompletionError, match="IMMUTABLE_FIELDS_CHANGED"):
        validate_blank_review_packet(packet, RUN_ROOT)


def test_stale_artifact_hash_fails(blank_packet: dict):
    packet = copy.deepcopy(blank_packet)
    binding = next(
        item for item in packet["authoritative_inputs"] if item["role"] == "claim_review"
    )
    binding["file_sha256"] = "0" * 64
    with pytest.raises(ReviewCompletionError, match="STALE_PACKET_ARTIFACT_HASH"):
        validate_blank_review_packet(packet, RUN_ROOT)


def test_malformed_and_duplicate_candidate_ids_fail(blank_packet: dict):
    malformed = copy.deepcopy(blank_packet)
    malformed["claims"][0]["candidate_id"] = "bad id"
    with pytest.raises(ReviewCompletionError, match="CANDIDATE_ID_INVALID"):
        validate_blank_review_packet(malformed, RUN_ROOT)

    duplicate = copy.deepcopy(blank_packet)
    duplicate["claims"].append(copy.deepcopy(duplicate["claims"][0]))
    with pytest.raises(ReviewCompletionError, match="DUPLICATE_CANDIDATE_ID"):
        validate_blank_review_packet(duplicate, RUN_ROOT)


def test_missing_reason_and_reuse_target_fail(blank_packet: dict):
    missing_reason = synthetic_completed_packet(blank_packet)
    missing_reason["claims"][0]["human_input"]["reason"] = ""
    with pytest.raises(ReviewCompletionError, match="MISSING_REVIEW_REASON"):
        validate_completed_review_packet(missing_reason, RUN_ROOT)

    reuse = synthetic_completed_packet(blank_packet)
    exact = next(
        record
        for record in reuse["nodes"]
        if len(
            record["content"]["exact_production_resolution"].get(
                "candidate_target_node_ids", []
            )
        )
        == 1
    )
    exact["human_input"]["decision"] = "REUSE"
    with pytest.raises(ReviewCompletionError, match="REUSE_TARGET_REQUIRED"):
        validate_completed_review_packet(reuse, RUN_ROOT)

    exact["human_input"]["target_node_id"] = "NODE_WRONG_TARGET"
    with pytest.raises(ReviewCompletionError, match="REUSE_TARGET_NOT_EXACT"):
        validate_completed_review_packet(reuse, RUN_ROOT)


def test_unexpected_target_and_parent_create_dependency_fail(blank_packet: dict):
    unexpected_target = synthetic_completed_packet(blank_packet)
    unexpected_target["nodes"][0]["human_input"]["target_node_id"] = "NODE_WRONG_TARGET"
    with pytest.raises(ReviewCompletionError, match="UNEXPECTED_REUSE_TARGET"):
        validate_completed_review_packet(unexpected_target, RUN_ROOT)

    parent = synthetic_completed_packet(blank_packet)
    parent["relations"][0]["human_input"]["decision"] = "CREATE"
    with pytest.raises(
        ReviewCompletionError, match="PARENT_PLACEMENT_REQUIRES_NODE_CREATE"
    ):
        validate_completed_review_packet(parent, RUN_ROOT)


def test_wrong_run_and_extra_candidate_fail_closed(blank_packet: dict):
    wrong_run = copy.deepcopy(blank_packet)
    wrong_run["run"]["run_id"] = "INGEST_DIFFERENT_RUN"
    with pytest.raises(ReviewCompletionError, match="PACKET_RUN_MISMATCH"):
        validate_blank_review_packet(wrong_run, RUN_ROOT)

    extra = copy.deepcopy(blank_packet)
    added = copy.deepcopy(extra["claims"][0])
    added["candidate_id"] = "CLM_SYNTHETIC_EXTRA"
    extra["claims"].append(added)
    with pytest.raises(ReviewCompletionError, match="IMMUTABLE_FIELDS_CHANGED"):
        validate_blank_review_packet(extra, RUN_ROOT)


def test_duplicate_json_keys_are_rejected(tmp_path: Path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"document_type":"x","document_type":"y"}', encoding="utf-8")
    with pytest.raises(ReviewCompletionError, match="INVALID_JSON"):
        read_review_packet(path)
