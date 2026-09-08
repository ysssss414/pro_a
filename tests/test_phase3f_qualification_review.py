from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pro_a.phase3f_qualification_review import (
    EXPECTED_CONTENT_HASHES,
    EXPECTED_PRODUCTION_SHA256,
    EXPECTED_SOURCE_PACKET_HASH,
    EXPECTED_SOURCE_PACKET_ID,
    REVIEW_SCOPE,
    SELECTED_CANDIDATES,
    QualificationReviewError,
    apply_qualification_authorization,
    build_blank_qualification_packet,
    read_review_packet,
    validate_blank_qualification_packet,
    validate_completed_qualification_packet,
    validate_qualification_manifest,
)
from pro_a.phase3f_review_completion import (
    ReviewCompletionError,
    validate_completed_review_packet,
)
from pro_a.production_promotion import canonical_sha256, sha256_file


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "workspace" / "phase3e2sl6" / "operational_run"
PRODUCTION = ROOT / "workspace" / "pro_a.db"
SOURCE_PACKET = (
    ROOT
    / "workspace"
    / "phase3f_stage1_review_completion"
    / "operational_review_packet.json"
)
QUALIFICATION_ROOT = (
    ROOT / "workspace" / "phase3f_stage1_qualification_review"
)
QUALIFICATION_PACKET = (
    QUALIFICATION_ROOT / "qualification_review_packet.json"
)
QUALIFICATION_VIEW = QUALIFICATION_ROOT / "qualification_review_view.md"
QUALIFICATION_MANIFEST = (
    QUALIFICATION_ROOT / "qualification_review_manifest.json"
)
QUALIFICATION_AUTHORIZATION = (
    QUALIFICATION_ROOT / "qualification_review_human_authorization.json"
)
COMPLETED_PACKET = (
    QUALIFICATION_ROOT / "qualification_review_packet.completed.json"
)
COMPLETION_RECEIPT = (
    QUALIFICATION_ROOT / "qualification_review_completion_receipt.json"
)
pytestmark = pytest.mark.skipif(
    not all(
        path.is_file()
        for path in (
            SOURCE_PACKET,
            QUALIFICATION_PACKET,
            QUALIFICATION_AUTHORIZATION,
            COMPLETED_PACKET,
            COMPLETION_RECEIPT,
        )
    ),
    reason="local evidence-bearing Phase 3F audit fixture is intentionally untracked",
)


@pytest.fixture(scope="module")
def blank_packet() -> dict:
    return build_blank_qualification_packet(
        SOURCE_PACKET, RUN_ROOT, PRODUCTION
    )


def _synthetic_completion(blank_packet: dict) -> dict:
    packet = copy.deepcopy(blank_packet)
    packet["human_completion"]["reviewer"] = (
        "SYNTHETIC_TEST_REVIEWER_NOT_OPERATIONAL_AUTHORITY"
    )
    for record in packet["claims"]:
        record["human_input"].update(
            {
                "decision": "DROP",
                "reason": (
                    "SYNTHETIC_QUALIFICATION_TEST_ONLY_NOT_AN_"
                    "OPERATIONAL_DECISION"
                ),
            }
        )
    node_decisions = {
        "CAND_NODE_E8A75C771486B74E": ("CREATE", ""),
        "CAND_NODE_E7C5A8860931121D": (
            "REUSE",
            "NODE_20260814_1D6371B9",
        ),
        "CAND_NODE_757A9745164C0433": ("DEFER", ""),
    }
    for record in packet["nodes"]:
        decision, target = node_decisions[record["candidate_id"]]
        record["human_input"].update(
            {
                "decision": decision,
                "reason": (
                    "SYNTHETIC_QUALIFICATION_TEST_ONLY_NOT_AN_"
                    "OPERATIONAL_DECISION"
                ),
                "target_node_id": target,
            }
        )
    packet["relations"][0]["human_input"].update(
        {
            "decision": "CREATE",
            "reason": (
                "SYNTHETIC_QUALIFICATION_TEST_ONLY_NOT_AN_"
                "OPERATIONAL_DECISION"
            ),
        }
    )
    return packet


def _assert_code(code: str, action) -> None:
    with pytest.raises(QualificationReviewError) as captured:
        action()
    assert captured.value.code == code


def test_blank_slice_is_exact_hash_bound_and_non_authorizing(
    blank_packet: dict,
):
    full_sha_before = sha256_file(SOURCE_PACKET)
    production_sha_before = sha256_file(PRODUCTION)
    result = validate_blank_qualification_packet(
        blank_packet, SOURCE_PACKET, RUN_ROOT, PRODUCTION
    )

    assert blank_packet["review_scope"] == REVIEW_SCOPE
    assert blank_packet["qualification_only"] is True
    assert blank_packet["full_operational_review_complete"] is False
    assert blank_packet["production_authorization"] is False
    assert blank_packet["unselected_candidates_reviewed"] is False
    assert blank_packet["source_review_packet"]["packet_id"] == (
        EXPECTED_SOURCE_PACKET_ID
    )
    assert blank_packet["source_review_packet"][
        "immutable_packet_sha256"
    ] == EXPECTED_SOURCE_PACKET_HASH
    assert result["qualification_candidate_count"] == 7
    assert result["human_decisions_present"] is False
    assert result["ready_for_stage1_requalification"] is False
    assert sha256_file(SOURCE_PACKET) == full_sha_before
    assert sha256_file(PRODUCTION) == production_sha_before
    assert production_sha_before == EXPECTED_PRODUCTION_SHA256


def test_selected_records_exactly_match_the_full_packet(
    blank_packet: dict,
):
    full = read_review_packet(SOURCE_PACKET)
    for group, selected_ids in SELECTED_CANDIDATES.items():
        actual = blank_packet[group]
        assert [item["candidate_id"] for item in actual] == list(
            selected_ids
        )
        full_by_id = {
            item["candidate_id"]: item for item in full[group]
        }
        for record in actual:
            candidate_id = record["candidate_id"]
            assert record == full_by_id[candidate_id]
            assert record["content_sha256"] == EXPECTED_CONTENT_HASHES[
                candidate_id
            ]
            assert canonical_sha256(record["content"]) == record[
                "content_sha256"
            ]
            assert all(
                value == "" for value in record["human_input"].values()
            )


def test_parent_and_reuse_display_context_is_exact(
    blank_packet: dict,
):
    context = blank_packet["production_display_context"]
    assert context["production_sha256"] == EXPECTED_PRODUCTION_SHA256
    assert context["display_context_only"] is True
    assert context["resolved_nodes"]["parent_placement_target"] == {
        "node_id": "NODE_20260814_164548FF",
        "canonical_name": "算力",
        "primary_type": "Industry",
        "status": "active",
    }
    assert context["resolved_nodes"]["reuse_target"] == {
        "node_id": "NODE_20260814_1D6371B9",
        "canonical_name": "通信",
        "primary_type": "Industry",
        "status": "active",
    }


def test_generated_manifest_binds_packet_view_and_source():
    manifest = read_review_packet(QUALIFICATION_MANIFEST)
    validate_qualification_manifest(
        manifest,
        QUALIFICATION_PACKET,
        QUALIFICATION_VIEW,
        SOURCE_PACKET,
        RUN_ROOT,
        PRODUCTION,
    )
    assert manifest["source_review_packet"]["file_sha256"] == sha256_file(
        SOURCE_PACKET
    )
    assert manifest["qualification_review_packet"]["file_sha256"] == (
        sha256_file(QUALIFICATION_PACKET)
    )
    assert manifest["qualification_review_view"]["file_sha256"] == (
        sha256_file(QUALIFICATION_VIEW)
    )


def test_clearly_synthetic_seven_decision_completion_validates(
    blank_packet: dict,
):
    packet = _synthetic_completion(blank_packet)
    result = validate_completed_qualification_packet(
        packet, SOURCE_PACKET, RUN_ROOT, PRODUCTION
    )
    assert result["validation_scope"] == "STAGE1_QUALIFICATION_REVIEW_COMPLETION"
    assert result["qualification_decisions_validated"] == 7
    assert result["full_operational_review_complete"] is False
    assert result["production_authorization"] is False
    assert result["production_apply_authorized"] is False
    assert result["ready_for_stage1_requalification"] is True
    with pytest.raises(ReviewCompletionError):
        validate_completed_review_packet(packet, RUN_ROOT)


def test_source_packet_immutable_identity_is_verified(
    blank_packet: dict,
    tmp_path: Path,
):
    source = read_review_packet(SOURCE_PACKET)
    source["packet_id"] = "REVIEW_PACKET_TAMPERED"
    tampered = tmp_path / "tampered_source_packet.json"
    tampered.write_text(
        json.dumps(source, ensure_ascii=False),
        encoding="utf-8",
    )
    _assert_code(
        "SOURCE_REVIEW_PACKET_INVALID",
        lambda: build_blank_qualification_packet(
            tampered, RUN_ROOT, PRODUCTION
        ),
    )


def test_source_binding_and_candidate_content_tamper_fail(
    blank_packet: dict,
):
    source_binding_tamper = copy.deepcopy(blank_packet)
    source_binding_tamper["source_review_packet"][
        "immutable_packet_sha256"
    ] = "0" * 64
    _assert_code(
        "IMMUTABLE_FIELDS_CHANGED",
        lambda: validate_blank_qualification_packet(
            source_binding_tamper, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )

    content_tamper = copy.deepcopy(blank_packet)
    content_tamper["claims"][0]["content"]["statement"] += "tampered"
    _assert_code(
        "IMMUTABLE_FIELDS_CHANGED",
        lambda: validate_blank_qualification_packet(
            content_tamper, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )


def test_missing_and_unknown_selected_decisions_fail_closed(
    blank_packet: dict,
):
    missing = _synthetic_completion(blank_packet)
    missing["claims"][0]["human_input"]["decision"] = ""
    _assert_code(
        "MISSING_DECISION",
        lambda: validate_completed_qualification_packet(
            missing, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )

    unknown = _synthetic_completion(blank_packet)
    unknown["claims"][0]["human_input"]["decision"] = "APPROVE"
    _assert_code(
        "UNKNOWN_DECISION",
        lambda: validate_completed_qualification_packet(
            unknown, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )


def test_reuse_requires_the_exact_target(blank_packet: dict):
    missing = _synthetic_completion(blank_packet)
    missing["nodes"][1]["human_input"]["target_node_id"] = ""
    _assert_code(
        "REUSE_TARGET_REQUIRED",
        lambda: validate_completed_qualification_packet(
            missing, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )

    wrong = _synthetic_completion(blank_packet)
    wrong["nodes"][1]["human_input"][
        "target_node_id"
    ] = "NODE_20260814_164548FF"
    _assert_code(
        "REUSE_TARGET_NOT_EXACT",
        lambda: validate_completed_qualification_packet(
            wrong, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )


def test_relation_create_requires_explicit_child_node_create(
    blank_packet: dict,
):
    packet = _synthetic_completion(blank_packet)
    packet["nodes"][0]["human_input"]["decision"] = "DEFER"
    _assert_code(
        "PARENT_PLACEMENT_REQUIRES_NODE_CREATE",
        lambda: validate_completed_qualification_packet(
            packet, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )


@pytest.mark.parametrize(
    "field",
    (
        "full_operational_review_complete",
        "production_authorization",
        "unselected_candidates_reviewed",
    ),
)
def test_qualification_packet_cannot_masquerade(
    blank_packet: dict,
    field: str,
):
    packet = copy.deepcopy(blank_packet)
    packet[field] = True
    _assert_code(
        "QUALIFICATION_SCOPE_MASQUERADE",
        lambda: validate_blank_qualification_packet(
            packet, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )


def test_no_unselected_candidate_can_enter_the_slice(
    blank_packet: dict,
):
    full = read_review_packet(SOURCE_PACKET)
    selected = set(SELECTED_CANDIDATES["claims"])
    extra = next(
        item for item in full["claims"] if item["candidate_id"] not in selected
    )
    packet = copy.deepcopy(blank_packet)
    packet["claims"].append(extra)
    _assert_code(
        "QUALIFICATION_CANDIDATE_SET_INVALID",
        lambda: validate_blank_qualification_packet(
            packet, SOURCE_PACKET, RUN_ROOT, PRODUCTION
        ),
    )


def test_explicit_packet_bound_human_authorization_validates(
    blank_packet: dict,
):
    authorization = read_review_packet(QUALIFICATION_AUTHORIZATION)
    blank_sha_before = sha256_file(QUALIFICATION_PACKET)
    production_sha_before = sha256_file(PRODUCTION)
    completed, receipt = apply_qualification_authorization(
        blank_packet,
        authorization,
        SOURCE_PACKET,
        RUN_ROOT,
        PRODUCTION,
    )
    assert receipt["qualification_decisions_validated"] == 7
    assert receipt["validation_scope"] == (
        "STAGE1_QUALIFICATION_REVIEW_COMPLETION"
    )
    assert receipt["full_operational_review_complete"] is False
    assert receipt["production_authorization"] is False
    assert receipt["production_apply_authorized"] is False
    assert [item["human_input"]["decision"] for item in completed["claims"]] == [
        "KEEP",
        "KEEP_NEEDS_REVIEW",
        "DROP",
    ]
    assert [item["human_input"]["decision"] for item in completed["nodes"]] == [
        "CREATE",
        "REUSE",
        "DEFER",
    ]
    assert completed["relations"][0]["human_input"]["decision"] == "CREATE"
    assert sha256_file(QUALIFICATION_PACKET) == blank_sha_before
    assert sha256_file(PRODUCTION) == production_sha_before


def test_authorization_wrong_packet_or_extra_candidate_fails(
    blank_packet: dict,
):
    authorization = read_review_packet(QUALIFICATION_AUTHORIZATION)
    wrong_packet = copy.deepcopy(authorization)
    wrong_packet["packet_id"] = "QUALIFICATION_REVIEW_PACKET_WRONG"
    _assert_code(
        "AUTHORIZATION_BINDING_INVALID",
        lambda: apply_qualification_authorization(
            blank_packet,
            wrong_packet,
            SOURCE_PACKET,
            RUN_ROOT,
            PRODUCTION,
        ),
    )

    extra = copy.deepcopy(authorization)
    extra["claims"].append(copy.deepcopy(extra["claims"][0]))
    _assert_code(
        "AUTHORIZATION_CANDIDATE_SET_INVALID",
        lambda: apply_qualification_authorization(
            blank_packet,
            extra,
            SOURCE_PACKET,
            RUN_ROOT,
            PRODUCTION,
        ),
    )


def test_persisted_completed_packet_and_receipt_match_authorization(
    blank_packet: dict,
):
    authorization = read_review_packet(QUALIFICATION_AUTHORIZATION)
    expected, validation = apply_qualification_authorization(
        blank_packet,
        authorization,
        SOURCE_PACKET,
        RUN_ROOT,
        PRODUCTION,
    )
    completed = read_review_packet(COMPLETED_PACKET)
    receipt = read_review_packet(COMPLETION_RECEIPT)
    assert completed == expected
    assert receipt["completed_packet_sha256"] == validation[
        "completed_packet_sha256"
    ]
    assert receipt["completed_qualification_packet"]["file_sha256"] == (
        sha256_file(COMPLETED_PACKET)
    )
    body = {
        key: value
        for key, value in receipt.items()
        if key not in {"receipt_id", "receipt_sha256"}
    }
    assert canonical_sha256(body) == receipt["receipt_sha256"]
    assert receipt["receipt_id"] == (
        f"QUALIFICATION_COMPLETION_{receipt['receipt_sha256'][:16].upper()}"
    )
