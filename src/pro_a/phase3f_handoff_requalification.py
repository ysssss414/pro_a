"""Qualification-only Phase 3F Stage 1 adapter for Phase 3D validators."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .phase3f_qualification_review import read_review_packet, validate_completed_qualification_packet
from .phase3f_operational_handoff import (
    HandoffPolicy,
    OperationalHandoffError,
    build_handoff_core,
    validate_handoff_payload,
)
from .production_promotion import (
    canonical_sha256,
    deterministic_id,
    production_identity,
    sha256_file,
)


SCHEMA_VERSION = "1"
REVIEW_SCOPE = "PHASE3F_STAGE1_HANDOFF_QUALIFICATION_ONLY"
EXECUTION_TARGET = "SHADOW_ONLY_QUALIFICATION"
ADAPTER_TYPE = (
    "MINIMAL_QUALIFICATION_ONLY_DETERMINISTIC_ADAPTER_"
    "USING_EXISTING_PHASE3D_VALIDATORS"
)
MAPPING_DOCUMENT_TYPE = "phase3f_stage1_handoff_mapping"
VALIDATION_DOCUMENT_TYPE = "phase3f_stage1_phase3d_validation_receipt"
RECEIPT_DOCUMENT_TYPE = "phase3f_stage1_requalification_receipt"

KEEP_CLAIM = "CLM_07152FCFBF4C3D1B"
REVIEW_CLAIM = "CLM_74B65D5D09781B64"
DROP_CLAIM = "CLM_229114C7C3F70FE9"
CREATE_NODE = "CAND_NODE_E8A75C771486B74E"
REUSE_NODE = "CAND_NODE_E7C5A8860931121D"
DEFER_NODE = "CAND_NODE_757A9745164C0433"
CREATE_PARENT = "PARENT_PLACEMENT_67ADDE309C1A5CAB"
EXPECTED_DECISIONS = {
    "claims": {KEEP_CLAIM: "KEEP", REVIEW_CLAIM: "KEEP_NEEDS_REVIEW", DROP_CLAIM: "DROP"},
    "nodes": {CREATE_NODE: "CREATE", REUSE_NODE: "REUSE", DEFER_NODE: "DEFER"},
    "relations": {CREATE_PARENT: "CREATE"},
}
HANDOFF_POLICY = HandoffPolicy(
    review_scope=REVIEW_SCOPE,
    qualification_only=True,
    full_operational_review_complete=False,
    unselected_candidates_reviewed=False,
    adapter_type=ADAPTER_TYPE,
    mapping_document_type=MAPPING_DOCUMENT_TYPE,
    legacy_qualification_labels=True,
)


class HandoffRequalificationError(RuntimeError):
    """A stable fail-closed Stage 1 requalification error."""


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise HandoffRequalificationError(f"{code}: {detail}" if detail else code)


def _binding(role: str, path: Path, root: Path) -> dict[str, Any]:
    _require(path.is_file(), "INPUT_ARTIFACT_MISSING", role)
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.resolve().as_posix()
    return {"role": role, "relative_path": relative, "file_sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def _semantic(body: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    digest = canonical_sha256(body)
    return {**copy.deepcopy(dict(body)), "receipt_id": f"{prefix}_{digest[:16].upper()}", "receipt_sha256": digest}


def _validate_receipt(receipt: Mapping[str, Any], prefix: str) -> None:
    body = {k: copy.deepcopy(v) for k, v in receipt.items() if k not in {"receipt_id", "receipt_sha256"}}
    digest = canonical_sha256(body)
    _require(receipt.get("receipt_sha256") == digest, "INPUT_RECEIPT_HASH_MISMATCH")
    _require(receipt.get("receipt_id") == f"{prefix}_{digest[:16].upper()}", "INPUT_RECEIPT_ID_MISMATCH")


def _records(packet: Mapping[str, Any], group: str) -> dict[str, Mapping[str, Any]]:
    return {item["candidate_id"]: item for item in packet[group]}


def _validate_inputs(
    *, completed_packet_path: Path, authorization_path: Path, completion_receipt_path: Path,
    source_packet_path: Path, run_root: Path, production_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    packet = read_review_packet(completed_packet_path)
    validation = validate_completed_qualification_packet(packet, source_packet_path, run_root, production_path)
    _require(validation["qualification_decisions_validated"] == 7, "DECISION_COUNT_INVALID")
    for group, expected in EXPECTED_DECISIONS.items():
        actual = {item["candidate_id"]: item["human_input"]["decision"] for item in packet[group]}
        _require(actual == expected, "QUALIFICATION_DECISIONS_MISMATCH", group)
    for field, expected in (("review_scope", REVIEW_SCOPE), ("qualification_only", True),
                            ("full_operational_review_complete", False), ("production_authorization", False),
                            ("unselected_candidates_reviewed", False)):
        _require(packet.get(field) == expected, "QUALIFICATION_BOUNDARY_INVALID", field)

    authorization = read_review_packet(authorization_path)
    _require(authorization.get("packet_id") == packet["packet_id"], "AUTHORIZATION_PACKET_MISMATCH")
    _require(authorization.get("immutable_packet_sha256") == packet["immutable_packet_sha256"], "AUTHORIZATION_HASH_MISMATCH")
    for group in EXPECTED_DECISIONS:
        actual = _records(packet, group)
        for item in authorization[group]:
            target = actual.get(item["candidate_id"])
            _require(target is not None, "AUTHORIZATION_CANDIDATE_MISMATCH")
            for field in ("decision", "reason", "target_node_id"):
                if field in item:
                    _require(item[field] == target["human_input"].get(field), "AUTHORIZATION_DECISION_MISMATCH")

    receipt = read_review_packet(completion_receipt_path)
    _validate_receipt(receipt, "QUALIFICATION_COMPLETION")
    _require(receipt.get("completed_packet_sha256") == validation["completed_packet_sha256"], "COMPLETION_RECEIPT_MISMATCH")
    _require((receipt.get("completed_qualification_packet") or {}).get("file_sha256") == sha256_file(completed_packet_path),
             "COMPLETED_PACKET_FILE_HASH_MISMATCH")
    validation["authority_source"] = authorization["authority_source"]
    return packet, validation, receipt


def _build_relation_operations(
    completed: Mapping[str, Any], node_operations: list[Mapping[str, Any]], timestamp: str
) -> list[dict[str, Any]]:
    record = completed["relations"][0]
    content, human = record["content"], record["human_input"]
    child = next((item for item in node_operations if item["candidate_id"] == content["child_node_candidate_id"]), None)
    _require(child is not None, "RELATION_CHILD_OPERATION_MISSING")
    _require(child.get("operation") == "CREATE" and child.get("executable") is True,
             "PARENT_PLACEMENT_CREATE_CONDITION_FAILED")
    _require((child.get("final_node") or {}).get("node_id") == content["prospective_child_node_id"],
             "PARENT_PLACEMENT_CHILD_ID_MISMATCH")
    relation = {
        "relation_id": deterministic_id("REL", {"candidate_id": record["candidate_id"], "content": content}),
        "from_node_id": content["prospective_child_node_id"], "relation_type": content["relation_type"],
        "to_node_id": content["parent_node_id"], "scope": "", "valid_from": "", "valid_to": "",
        "confidence": None, "status": "current", "evidence_claim_id": None, "created_at": timestamp,
    }
    operation_id = deterministic_id("OP_REL", {"candidate_id": record["candidate_id"], "relation": relation})
    return [{
        "operation_id": operation_id, "candidate_id": record["candidate_id"], "candidate": copy.deepcopy(content),
        "operation": human["decision"], "executable": True, "reason": human["reason"], "final_relation": relation,
        "qualification_authorization": {"decision": human["decision"], "reason": human["reason"],
                                        "packet_id": completed["packet_id"],
                                        "conditional_on_node_candidate_id": content["child_node_candidate_id"]},
    }]


def validate_qualification_only_payload(payload: Mapping[str, Any]) -> None:
    """Prove that a Phase 3D-shaped candidate remains non-Production."""
    try:
        validate_handoff_payload(payload, HANDOFF_POLICY)
    except OperationalHandoffError as exc:
        message = str(exc)
        if message.startswith("HANDOFF_BOUNDARY_INVALID:"):
            field = message.split(":", 1)[1].strip()
            raise HandoffRequalificationError(
                f"QUALIFICATION_ONLY_GUARD_MISMATCH: {field}"
            ) from exc
        raise


def build_requalification_artifacts(
    *, repository_commit: str, blank_packet_path: str | Path, completed_packet_path: str | Path,
    authorization_path: str | Path, completion_receipt_path: str | Path,
    qualification_manifest_path: str | Path, qualification_view_path: str | Path,
    source_packet_path: str | Path, run_root: str | Path, production_path: str | Path,
    repository_root: str | Path,
) -> dict[str, dict[str, Any]]:
    """Build and validate the four deterministic Stage 1 artifacts."""
    root, run_root, production_path = Path(repository_root).resolve(), Path(run_root).resolve(), Path(production_path).resolve()
    paths = {
        "blank_qualification_packet": Path(blank_packet_path).resolve(),
        "completed_qualification_packet": Path(completed_packet_path).resolve(),
        "qualification_authorization": Path(authorization_path).resolve(),
        "qualification_completion_receipt": Path(completion_receipt_path).resolve(),
        "qualification_manifest": Path(qualification_manifest_path).resolve(),
        "qualification_view": Path(qualification_view_path).resolve(),
        "source_review_packet": Path(source_packet_path).resolve(),
    }
    _require(isinstance(repository_commit, str) and len(repository_commit) == 40, "REPOSITORY_COMMIT_INVALID")
    packet, completion, prior_receipt = _validate_inputs(
        completed_packet_path=paths["completed_qualification_packet"], authorization_path=paths["qualification_authorization"],
        completion_receipt_path=paths["qualification_completion_receipt"], source_packet_path=paths["source_review_packet"],
        run_root=run_root, production_path=production_path,
    )
    evidence_bundle_path = run_root / "evidence" / "evidence_bound_extraction_bundle.json"
    bundle = read_review_packet(evidence_bundle_path)
    _require(sha256_file(evidence_bundle_path) == packet["claims"][0]["provenance"]["evidence_bundle_file_sha256"],
             "EVIDENCE_BUNDLE_HASH_MISMATCH")
    _require(bundle["source"]["sha256"] == packet["source"]["source_sha256"], "SOURCE_SHA_BINDING_MISMATCH")
    bindings = sorted([_binding(role, path, root) for role, path in paths.items()]
                      + [_binding("evidence_bound_extraction_bundle", evidence_bundle_path, root)], key=lambda item: item["role"])
    production = production_identity(production_path)
    completion_for_core = {
        **completion,
        "total_operational_decisions_validated": completion[
            "qualification_decisions_validated"
        ],
    }
    core = build_handoff_core(
        packet=packet,
        completion=completion_for_core,
        completion_receipt=prior_receipt,
        bundle=bundle,
        production_path=production_path,
        repository_commit=repository_commit,
        bindings=bindings,
        authority={
            "authority_source": completion["authority_source"],
            "authorization_file_sha256": sha256_file(paths["qualification_authorization"]),
            "authorization_semantic_sha256": "",
        },
        policy=HANDOFF_POLICY,
    )
    mapping = core["mapping"]
    payload = core["payload"]
    phase3d = core["phase3d_validation"]

    validation_receipt = _semantic({
        "document_type": VALIDATION_DOCUMENT_TYPE, "schema_version": SCHEMA_VERSION, "status": "PASS",
        "review_scope": REVIEW_SCOPE, "qualification_only": True, "full_operational_review_complete": False,
        "production_authorization": False, "production_apply_authorized": False,
        "unselected_candidates_reviewed": False, "payload_id": payload["payload_id"], "payload_hash": payload["payload_hash"],
        "mapping_id": mapping["mapping_id"], "mapping_sha256": mapping["mapping_sha256"], "adapter_type": ADAPTER_TYPE,
        "phase3d_validation": phase3d, "llm_calls": 0,
    }, "PHASE3D_VALIDATION")
    receipt = _semantic({
        "document_type": RECEIPT_DOCUMENT_TYPE, "schema_version": SCHEMA_VERSION, "status": "PASS",
        "review_scope": REVIEW_SCOPE, "qualification_only": True, "full_operational_review_complete": False,
        "production_authorization": False, "production_apply_authorized": False, "unselected_candidates_reviewed": False,
        "qualification_packet_id": packet["packet_id"], "qualification_immutable_packet_sha256": packet["immutable_packet_sha256"],
        "qualification_completed_packet_sha256": completion["completed_packet_sha256"], "human_decisions_present": True,
        "qualification_decisions_validated": 7, "stage1_requalification_executed": True,
        "handoff_mapping_id": mapping["mapping_id"], "handoff_mapping_sha256": mapping["mapping_sha256"],
        "promotion_payload_id": payload["payload_id"], "promotion_payload_sha256": payload["payload_hash"],
        "phase3d_validation_receipt_id": validation_receipt["receipt_id"],
        "phase3d_validation_receipt_sha256": validation_receipt["receipt_sha256"],
        "promotable_counts": {"claims": 1, "nodes_create": 1, "nodes_reuse": 1, "parent_placements_create": 1},
        "blocked_counts": {"claims_keep_needs_review": 1, "claims_drop": 1, "nodes_defer": 1},
        "direct_handoff_found_before_adapter": False, "direct_handoff_found_after_adapter": True, "adapter_type": ADAPTER_TYPE,
        "phase3d_payload_validation": phase3d["payload_validation"], "phase3d_preapply_validation": phase3d["preapply_validation"],
        "shadow_apply": phase3d["shadow_apply"], "idempotent_replay": phase3d["idempotent_replay"], "rollback": phase3d["rollback"],
        "production_sha256_before": production["sha256"], "production_sha256_after": phase3d["production_sha256"],
        "production_integrity": phase3d["production_integrity"],
        "production_foreign_key_violations": phase3d["production_foreign_key_violations"],
        "production_changed": False, "llm_calls": 0, "phase3f_stage2_started": False,
        "final_stop_reason": "STAGE1_QUALIFICATION_HANDOFF_REQUALIFIED_STOP_BEFORE_STAGE2",
    }, "STAGE1_REQUALIFICATION")
    return {"handoff_mapping.json": mapping, "qualification_promotion_candidate.json": payload,
            "phase3d_validation_receipt.json": validation_receipt, "stage1_requalification_receipt.json": receipt}


def write_requalification_artifacts(output_dir: str | Path, **kwargs: Any) -> dict[str, dict[str, Any]]:
    """Write deterministic LF-only JSON after all validation passes."""
    artifacts = build_requalification_artifacts(**kwargs)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        with (output_dir / name).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return artifacts
