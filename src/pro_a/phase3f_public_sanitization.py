"""Deterministic Git-safe projections for Phase 3F Stage 1 audit artifacts."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .phase3f_qualification_review import read_review_packet
from .production_promotion import canonical_sha256, sha256_file


SCHEMA_VERSION = "1"
REVIEW_SCOPE = "PHASE3F_STAGE1_HANDOFF_QUALIFICATION_ONLY"
SAFETY_FLAGS = {
    "qualification_only": True,
    "full_operational_review_complete": False,
    "production_authorization": False,
    "production_apply_authorized": False,
    "unselected_candidates_reviewed": False,
    "phase3f_stage2_started": False,
}


def _artifact(body: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    digest = canonical_sha256(body)
    return {
        **copy.deepcopy(dict(body)),
        "artifact_id": f"{prefix}_{digest[:16].upper()}",
        "artifact_sha256": digest,
    }


def _reason_hash(record: Mapping[str, Any]) -> str:
    reason = (record.get("human_input") or {}).get("reason") or ""
    return canonical_sha256(reason) if reason else ""


def _record_ref(record: Mapping[str, Any]) -> dict[str, Any]:
    provenance = record.get("provenance") or {}
    human = record.get("human_input") or {}
    return {
        "candidate_type": record.get("candidate_type"),
        "candidate_id": record.get("candidate_id"),
        "content_sha256": record.get("content_sha256"),
        "provenance": {
            key: copy.deepcopy(provenance[key])
            for key in (
                "run_id", "source_id", "source_sha256", "review_artifact_role",
                "review_id", "review_semantic_sha256", "review_file_sha256",
                "evidence_bundle_file_sha256", "claim_review_semantic_sha256",
                "node_review_semantic_sha256",
            )
            if key in provenance
        },
        "allowed_decisions": copy.deepcopy(record.get("allowed_decisions") or []),
        "decision": human.get("decision") or "",
        "decision_reason_sha256": _reason_hash(record),
        "target_node_id": human.get("target_node_id") or "",
    }


def _input_binding(role: str, path: Path, root: Path) -> dict[str, Any]:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.resolve().as_posix()
    return {
        "role": role,
        "local_relative_path": relative,
        "file_sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "tracked": False,
        "local_only": True,
    }


def build_review_surface_projection(packet: Mapping[str, Any], *, file_sha256: str) -> dict[str, Any]:
    records = {
        group: [_record_ref(item) for item in packet.get(group) or []]
        for group in ("claims", "nodes", "aliases", "relations")
    }
    body = {
        "document_type": "phase3f_stage1_operational_review_public_audit",
        "schema_version": SCHEMA_VERSION,
        "source_packet": {
            "packet_id": packet["packet_id"],
            "immutable_packet_sha256": packet["immutable_packet_sha256"],
            "file_sha256": file_sha256,
        },
        "run": copy.deepcopy(packet["run"]),
        "source": {
            key: packet["source"].get(key)
            for key in ("source_id", "source_sha256", "size_bytes", "source_type")
        },
        "production_baseline": {
            key: copy.deepcopy(packet["production_baseline"].get(key))
            for key in ("sha256", "schema_version", "schema_sha256", "counts")
        },
        "candidate_universe_sha256": packet["summary"]["candidate_universe_sha256"],
        "counts": copy.deepcopy(packet["summary"]),
        "records": records,
        "source_text_included": False,
        "local_evidence_retained": True,
    }
    return _artifact(body, "PUBLIC_REVIEW_AUDIT")


def build_qualification_projection(
    blank: Mapping[str, Any], completed: Mapping[str, Any], authorization: Mapping[str, Any],
    receipt: Mapping[str, Any], *, input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    records = {
        group: [_record_ref(item) for item in completed[group]]
        for group in ("claims", "nodes", "relations")
    }
    body = {
        "document_type": "phase3f_stage1_qualification_public_audit",
        "schema_version": SCHEMA_VERSION,
        "review_scope": REVIEW_SCOPE,
        **SAFETY_FLAGS,
        "packet_id": completed["packet_id"],
        "immutable_packet_sha256": completed["immutable_packet_sha256"],
        "completed_packet_sha256": receipt["completed_packet_sha256"],
        "source_review_packet": copy.deepcopy(completed["source_review_packet"]),
        "run_id": completed["run"]["run_id"],
        "source_id": completed["source"]["source_id"],
        "source_sha256": completed["source"]["source_sha256"],
        "reviewer": authorization["reviewer"],
        "authority_source": authorization["authority_source"],
        "decision_counts": copy.deepcopy(receipt["decision_counts"]),
        "records": records,
        "input_file_sha256": dict(sorted(input_hashes.items())),
        "blank_packet_human_decisions_present": False,
        "source_text_included": False,
        "local_evidence_retained": True,
    }
    return _artifact(body, "PUBLIC_QUALIFICATION_AUDIT")


def _node_operation(operation: Mapping[str, Any]) -> dict[str, Any]:
    candidate = operation.get("candidate") or {}
    final_node = operation.get("final_node") or {}
    authority = operation.get("qualification_authorization") or {}
    return {
        "operation_id": operation["operation_id"],
        "candidate_id": operation["candidate_id"],
        "candidate_content_sha256": candidate.get("qualification_record_content_sha256"),
        "operation": operation["operation"],
        "executable": operation["executable"],
        "claim_refs": copy.deepcopy(operation.get("claim_refs") or []),
        "evidence_refs": copy.deepcopy(operation.get("evidence_refs") or []),
        "resolved_target_id": operation.get("resolved_target_id"),
        "final_node_id": final_node.get("node_id"),
        "final_node_type": final_node.get("primary_type"),
        "alias_sha256": sorted(canonical_sha256(item) for item in operation.get("aliases") or []),
        "decision": authority.get("decision"),
        "decision_reason_sha256": canonical_sha256(authority.get("reason") or ""),
        "target_node_id": authority.get("target_node_id") or "",
    }


def _relation_operation(operation: Mapping[str, Any]) -> dict[str, Any]:
    relation = operation.get("final_relation") or {}
    authority = operation.get("qualification_authorization") or {}
    return {
        "operation_id": operation["operation_id"],
        "candidate_id": operation["candidate_id"],
        "operation": operation["operation"],
        "executable": operation["executable"],
        "relation_id": relation.get("relation_id"),
        "from_node_id": relation.get("from_node_id"),
        "relation_type": relation.get("relation_type"),
        "to_node_id": relation.get("to_node_id"),
        "decision": authority.get("decision"),
        "decision_reason_sha256": canonical_sha256(authority.get("reason") or ""),
        "conditional_on_node_candidate_id": authority.get("conditional_on_node_candidate_id"),
    }


def _mutation_key(mutation: Mapping[str, Any]) -> dict[str, Any]:
    key = copy.deepcopy(mutation["key"])
    if mutation["table"] == "node_aliases":
        key["alias_sha256"] = canonical_sha256(key.pop("alias"))
    return key


def build_handoff_projection(
    mapping: Mapping[str, Any], payload: Mapping[str, Any], validation: Mapping[str, Any],
    receipt: Mapping[str, Any], *, input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    mapping_records = []
    for item in mapping["records"]:
        mapping_records.append({
            key: copy.deepcopy(value)
            for key, value in item.items()
            if key != "human_reason"
        } | {"human_reason_sha256": canonical_sha256(item["human_reason"])})
    claims = []
    for item in payload["claims"]:
        claims.append({
            "claim_id": item["claim_id"],
            "evidence_id": item["evidence_id"],
            "qualification_record_content_sha256": item["qualification_record_content_sha256"],
            "evidence_pointer": item["immutable_claim"].get("evidence_pointer"),
            "decision": item["reviewer_decision"]["decision"],
            "decision_reason_sha256": canonical_sha256(item["reviewer_decision"]["reason"]),
            "executable": item["executable"],
            "disposition": item["disposition"],
            "block_reason": item["block_reason"],
        })
    body = {
        "document_type": "phase3f_stage1_handoff_requalification_public_audit",
        "schema_version": SCHEMA_VERSION,
        "review_scope": REVIEW_SCOPE,
        **SAFETY_FLAGS,
        "mapping": {
            "mapping_id": mapping["mapping_id"],
            "mapping_sha256": mapping["mapping_sha256"],
            "counts": copy.deepcopy(mapping["counts"]),
            "records": mapping_records,
        },
        "payload": {
            "payload_id": payload["payload_id"],
            "payload_hash": payload["payload_hash"],
            "adapter_type": payload["adapter_type"],
            "qualified_execution_target": payload["qualified_execution_target"],
            "metadata": copy.deepcopy(payload["metadata"]),
            "human_authorization": copy.deepcopy(payload["human_authorization"]),
            "source": copy.deepcopy(payload["source"]),
            "claims": claims,
            "node_operations": [_node_operation(item) for item in payload["node_operations"]],
            "relation_operations": [_relation_operation(item) for item in payload["relation_operations"]],
            "mutation_audit": [{
                "mutation_id": item["mutation_id"],
                "table": item["table"],
                "operation": item["operation"],
                "key": _mutation_key(item),
                "row_sha256": canonical_sha256(item["row"]),
                "authorized_by": item["authorized_by"],
            } for item in payload["intended_mutations"]],
            "audit": copy.deepcopy(payload["audit"]),
        },
        "phase3d_validation": copy.deepcopy(validation),
        "stage1_requalification_receipt": copy.deepcopy(receipt),
        "input_file_sha256": dict(sorted(input_hashes.items())),
        "source_text_included": False,
        "local_evidence_retained": True,
    }
    return _artifact(body, "PUBLIC_HANDOFF_AUDIT")


def write_public_audit(
    *, repository_root: str | Path, review_packet_path: str | Path,
    qualification_root: str | Path, handoff_root: str | Path, output_dir: str | Path,
) -> dict[str, dict[str, Any]]:
    root = Path(repository_root).resolve()
    review_path, qualification_root = Path(review_packet_path).resolve(), Path(qualification_root).resolve()
    handoff_root, output_dir = Path(handoff_root).resolve(), Path(output_dir)
    qpaths = {
        "blank_packet": qualification_root / "qualification_review_packet.json",
        "completed_packet": qualification_root / "qualification_review_packet.completed.json",
        "authorization": qualification_root / "qualification_review_human_authorization.json",
        "completion_receipt": qualification_root / "qualification_review_completion_receipt.json",
    }
    hpaths = {
        "handoff_mapping": handoff_root / "handoff_mapping.json",
        "promotion_candidate": handoff_root / "qualification_promotion_candidate.json",
        "phase3d_validation_receipt": handoff_root / "phase3d_validation_receipt.json",
        "stage1_requalification_receipt": handoff_root / "stage1_requalification_receipt.json",
    }
    q = {name: read_review_packet(path) for name, path in qpaths.items()}
    h = {name: read_review_packet(path) for name, path in hpaths.items()}
    artifacts = {
        "operational_review_public_audit.json": build_review_surface_projection(
            read_review_packet(review_path), file_sha256=sha256_file(review_path)
        ),
        "qualification_review_public_audit.json": build_qualification_projection(
            q["blank_packet"], q["completed_packet"], q["authorization"], q["completion_receipt"],
            input_hashes={name: sha256_file(path) for name, path in qpaths.items()},
        ),
        "handoff_requalification_public_audit.json": build_handoff_projection(
            h["handoff_mapping"], h["promotion_candidate"], h["phase3d_validation_receipt"],
            h["stage1_requalification_receipt"],
            input_hashes={name: sha256_file(path) for name, path in hpaths.items()},
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        with (output_dir / name).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    manifest_body = {
        "document_type": "phase3f_stage1_public_audit_manifest",
        "schema_version": SCHEMA_VERSION,
        "review_scope": REVIEW_SCOPE,
        **SAFETY_FLAGS,
        "public_repository": "https://github.com/ysssss414/pro_a.git",
        "source_text_included": False,
        "local_evidence_retained": True,
        "local_untracked_inputs": [
            _input_binding("operational_review_packet", review_path, root),
            *[_input_binding(name, path, root) for name, path in sorted(qpaths.items())],
            *[_input_binding(name, path, root) for name, path in sorted(hpaths.items())],
        ],
        "sanitized_artifacts": [{
            "relative_path": f"workspace/phase3f_stage1_public_audit/{name}",
            "file_sha256": sha256_file(output_dir / name),
            "artifact_id": artifact["artifact_id"],
            "artifact_sha256": artifact["artifact_sha256"],
        } for name, artifact in sorted(artifacts.items())],
    }
    manifest = _artifact(manifest_body, "PUBLIC_AUDIT_MANIFEST")
    with (output_dir / "public_audit_manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return {**artifacts, "public_audit_manifest.json": manifest}
