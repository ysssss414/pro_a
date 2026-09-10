"""External completed-artifact authority, separate from V4 review semantics.

The caller supplies the basis from a trusted authorization, never from the
payload under verification. No database is opened by this module.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .production_promotion import PromotionError, canonical_sha256


CONTRACT = {
    "contract_id": "FOUNDATION_PROMOTION_PAYLOAD_ENVELOPE_CONTRACT_V2_COMPLETED_ARTIFACT_BOUND",
    "outer_payload_self_hash_is_not_authorization": True,
    "trusted_external_review_basis_required": True,
    "completed_packet_id_required": True,
    "completed_packet_semantic_sha_required": True,
    "completed_packet_file_sha_required": True,
    "actual_completed_artifact_recomputation_required": True,
    "three_way_binding_required": True,
    "completed_semantic_algorithm": "Remove only human_completion.completed_packet_semantic_sha256; JSON ensure_ascii=False sort_keys=True separators=(comma,colon); UTF-8 SHA256, no newline",
    "review_and_payload_implementation_commits_are_separate": True,
    "legacy_foundation_without_external_artifact_binding_qualifies": False,
}
BOUND_CONTRACT = {**CONTRACT, "contract_sha256": canonical_sha256(CONTRACT)}


@dataclass(frozen=True)
class PayloadVerificationBasis:
    expected_completed_packet_id: str
    expected_completed_packet_semantic_sha256: str
    expected_completed_packet_file_sha256: str
    expected_review_execution_contract_sha256: str | None
    expected_production_sha256: str
    expected_schema_version: str
    expected_review_basis_implementation_commit: str
    expected_payload_implementation_commit: str


def require(condition, code):
    if not condition:
        raise PromotionError(code)


def artifact_bytes(artifact):
    require(isinstance(artifact, (bytes, str, Path)), "COMPLETED_ARTIFACT_REQUIRED")
    try:
        return artifact if isinstance(artifact, bytes) else Path(artifact).read_bytes()
    except OSError as error:
        raise PromotionError("COMPLETED_ARTIFACT_UNREADABLE") from error


def completed_semantic_sha256(packet):
    body = copy.deepcopy(packet)
    require(isinstance(body.get("human_completion"), dict), "COMPLETED_ARTIFACT_STATE_INVALID")
    body["human_completion"].pop("completed_packet_semantic_sha256", None)
    data = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_completed_artifact(basis, artifact):
    require(isinstance(basis, PayloadVerificationBasis), "TRUSTED_VERIFICATION_BASIS_REQUIRED")
    data = artifact_bytes(artifact)
    file_sha = hashlib.sha256(data).hexdigest()
    require(file_sha == basis.expected_completed_packet_file_sha256, "COMPLETED_ARTIFACT_FILE_SHA_MISMATCH")
    try:
        packet = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise PromotionError("COMPLETED_ARTIFACT_JSON_INVALID") from error
    require(isinstance(packet, dict), "COMPLETED_ARTIFACT_JSON_INVALID")
    semantic_sha = completed_semantic_sha256(packet)
    human = packet["human_completion"]
    require(human.get("completed_packet_semantic_sha256") == semantic_sha, "COMPLETED_ARTIFACT_SEMANTIC_DECLARATION_MISMATCH")
    require(semantic_sha == basis.expected_completed_packet_semantic_sha256, "COMPLETED_ARTIFACT_SEMANTIC_SHA_MISMATCH")
    require(human.get("completed_packet_id") == basis.expected_completed_packet_id and bool(basis.expected_completed_packet_id), "COMPLETED_ARTIFACT_ID_MISMATCH")
    require(human.get("state") == "COMPLETED" and human.get("content_decision_authority") == "EXPLICIT_HUMAN_APPROVAL", "COMPLETED_ARTIFACT_STATE_INVALID")
    require(packet.get("repository_commit") == basis.expected_review_basis_implementation_commit, "REVIEW_BASIS_IMPLEMENTATION_MISMATCH")
    require(packet.get("execution_contract", {}).get("contract_sha256") == basis.expected_review_execution_contract_sha256, "REVIEW_EXECUTION_CONTRACT_BINDING_MISMATCH")
    baseline = packet.get("production_baseline", {})
    require(baseline.get("sha256") == basis.expected_production_sha256, "PRODUCTION_TRUSTED_BINDING_MISMATCH")
    require(baseline.get("schema_version") == basis.expected_schema_version, "SCHEMA_TRUSTED_BINDING_MISMATCH")
    return packet, {
        "completed_packet_id": human["completed_packet_id"],
        "completed_packet_semantic_sha256": semantic_sha,
        "completed_packet_file_sha256": file_sha,
        "review_execution_contract_sha256": basis.expected_review_execution_contract_sha256,
        "review_basis_implementation_commit": basis.expected_review_basis_implementation_commit,
    }


def verify_payload_review_basis(payload, basis, completed_artifact):
    packet, expected = verify_completed_artifact(basis, completed_artifact)
    bound = payload.get("review_basis") or {}
    for field, code in (
        ("completed_packet_id", "COMPLETED_PACKET_ID_BINDING_MISMATCH"),
        ("completed_packet_semantic_sha256", "COMPLETED_PACKET_SEMANTIC_BINDING_MISMATCH"),
        ("completed_packet_file_sha256", "COMPLETED_PACKET_FILE_BINDING_MISMATCH"),
        ("review_execution_contract_sha256", "REVIEW_EXECUTION_CONTRACT_BINDING_MISMATCH"),
        ("review_basis_implementation_commit", "REVIEW_BASIS_IMPLEMENTATION_MISMATCH"),
    ):
        require(field in bound and bound[field] == expected[field], code)
    require(bound == expected, "PAYLOAD_REVIEW_BASIS_SCHEMA_MISMATCH")
    require(canonical_sha256(payload.get("payload_envelope_contract")) == canonical_sha256(BOUND_CONTRACT), "PAYLOAD_ENVELOPE_CONTRACT_MISMATCH")
    require(canonical_sha256(payload.get("foundation_review")) == canonical_sha256(packet), "EMBEDDED_COMPLETED_ARTIFACT_MISMATCH")
    metadata = payload.get("metadata") or {}
    require(metadata.get("review_basis_implementation_commit") == basis.expected_review_basis_implementation_commit, "REVIEW_BASIS_IMPLEMENTATION_MISMATCH")
    require(metadata.get("repository_commit") == metadata.get("payload_builder_verifier_implementation_commit") == basis.expected_payload_implementation_commit, "PAYLOAD_IMPLEMENTATION_BINDING_MISMATCH")
    require(metadata.get("input_artifact_roles_and_sha256") == [{"role": "foundation_review", "file_sha256": expected["completed_packet_file_sha256"]}], "COMPLETED_PACKET_FILE_BINDING_MISMATCH")
    require(metadata.get("production_sha256") == basis.expected_production_sha256, "PRODUCTION_TRUSTED_BINDING_MISMATCH")
    require(metadata.get("production_schema_version") == basis.expected_schema_version, "SCHEMA_TRUSTED_BINDING_MISMATCH")
