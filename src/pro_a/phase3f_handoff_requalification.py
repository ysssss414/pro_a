"""Qualification-only Phase 3F Stage 1 adapter for Phase 3D validators."""

from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .phase3f_qualification_review import read_review_packet, validate_completed_qualification_packet
from .production_final_qualification import validate_final_payload
from .production_promotion import (
    DOCUMENT_TYPE as PHASE3D_DOCUMENT_TYPE,
    PAYLOAD_VERSION,
    PromotionError,
    apply_payload_to_shadow,
    build_identity_catalog,
    canonical_json_bytes,
    canonical_sha256,
    copy_production_to_shadow,
    decide_node_operation,
    deterministic_id,
    payload_semantic_body,
    production_identity,
    sha256_file,
    validate_executable_operations,
    validate_payload,
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


def _readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _catalog(production_path: Path) -> dict[str, Any]:
    connection = _readonly_connection(production_path)
    try:
        nodes = [dict(row) for row in connection.execute("SELECT node_id,canonical_name,primary_type,status FROM nodes")]
        aliases = [dict(row) for row in connection.execute("SELECT alias,node_id FROM node_aliases")]
    finally:
        connection.close()
    return build_identity_catalog(nodes, aliases)


def _claim_row(claim: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    return {
        "claim_id": claim["claim_id"], "statement": claim["statement"], "nature": claim["nature"],
        "fact_time": claim.get("fact_time") or "", "publication_time": claim.get("publication_time") or "",
        "ingestion_time": claim.get("ingestion_time") or timestamp, "source_id": claim["source_id"],
        "evidence_pointer": claim.get("evidence_pointer") or "", "evidence_excerpt": claim.get("evidence_excerpt") or "",
        "attributed_to": claim.get("attributed_to") or "", "scope": claim.get("scope") or "",
        "assumption_text": claim.get("assumption_text") or "", "status": claim.get("status") or "current",
        "confidence": claim.get("confidence"), "novelty_level": claim.get("novelty_level") or "N2",
        "structured_json": canonical_json_bytes(claim.get("structured") or {}).decode("utf-8"),
        "created_at": claim.get("created_at") or timestamp,
    }


def _source_row(bundle: Mapping[str, Any], timestamp: str, bindings: list[dict[str, Any]]) -> dict[str, Any]:
    source, reviewed = bundle["source"], bundle.get("proposed_source_metadata") or {}
    name = str(source["original_name"]).replace("/", "_").replace("\\", "_")
    date_path = str(reviewed.get("publication_time") or "1970-01-01").replace("-", "/")
    metadata = {
        "summary": reviewed.get("summary") or "", "parse_diagnostics": source.get("parse_diagnostics") or {},
        "parse_warnings": source.get("parse_warnings") or [], "semantic_eligibility": source.get("semantic_eligibility") or {},
        "phase3f_stage1": {"review_scope": REVIEW_SCOPE, "qualification_only": True, "production_authorization": False,
                           "archive_materialization": "NOT_AUTHORIZED", "input_artifacts": bindings},
    }
    return {
        "source_id": source["proposed_source_id"], "title": reviewed.get("title") or source["original_name"],
        "original_name": source["original_name"], "archived_path": f"archive/{date_path}/{source['proposed_source_id']}__{name}",
        "sha256": source["sha256"], "ingestion_mode": source.get("analysis_mode") or "deep",
        "analysis_mode": source.get("analysis_mode") or "deep", "source_type": source.get("source_type") or "unknown",
        "source_rank": reviewed.get("source_rank") or "UNRANKED", "origin_type": reviewed.get("source_origin_type") or "unknown",
        "author": reviewed.get("author") or "", "organization": reviewed.get("organization") or "",
        "publication_time": reviewed.get("publication_time") or "", "ingested_at": timestamp, "status": "analyzed",
        "ima_media_id": "", "ima_kb_id": "", "underlying_source_id": "",
        "metadata_json": canonical_json_bytes(metadata).decode("utf-8"),
    }


def _mutation(table: str, key: Mapping[str, Any], row: Mapping[str, Any], authority: str) -> dict[str, Any]:
    body = {"table": table, "operation": "INSERT", "key": dict(key), "row": dict(row), "authorized_by": authority}
    return {"mutation_id": deterministic_id("MUT", body), **body}


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


def _node_operation(
    record: Mapping[str, Any], packet: Mapping[str, Any], catalog: Mapping[str, Any],
    accepted_claim_ids: set[str], evidence_ids: Mapping[str, str], timestamp: str,
) -> dict[str, Any]:
    content, human = record["content"], record["human_input"]
    requested = human["decision"]
    claim_refs = sorted(accepted_claim_ids.intersection(content.get("supporting_claim_ids") or []))
    candidate = {
        "candidate_id": record["candidate_id"], "canonical_name": content["proposed_name"],
        "primary_type": content["proposed_type"], "aliases": content.get("proposed_aliases") or [],
        "node_id": content["prospective_node_id"], "match_term": content["proposed_name"], "approved_aliases": [],
        "claim_refs": claim_refs, "evidence_refs": [evidence_ids[item] for item in claim_refs],
        "frozen_timestamp": timestamp, "reason": human["reason"],
        "qualification_record_content_sha256": record["content_sha256"],
    }
    operation = decide_node_operation(
        candidate, requested_operation=requested,
        review_decision={"CREATE": "APPROVE_CREATE", "REUSE": "APPROVE_REUSE"}.get(requested, requested),
        catalog=catalog, run_id=packet["run"]["run_id"],
    )
    operation["qualification_authorization"] = {
        "decision": requested, "reason": human["reason"], "target_node_id": human.get("target_node_id") or "",
        "packet_id": packet["packet_id"],
    }
    if requested == "REUSE":
        _require(operation.get("executable") is True, "AUTHORIZED_REUSE_NOT_RESOLVED")
        _require(operation.get("resolved_target_id") == human.get("target_node_id"), "AUTHORIZED_REUSE_TARGET_MISMATCH")
    return operation


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


def _mapping_record(record: Mapping[str, Any], phase3d_object: Mapping[str, Any] | None) -> dict[str, Any]:
    decision, promotable = record["human_input"]["decision"], phase3d_object is not None
    return {
        "candidate_type": record["candidate_type"], "candidate_id": record["candidate_id"],
        "qualification_record_content_sha256": record["content_sha256"], "human_decision": decision,
        "human_reason": record["human_input"]["reason"], "target_node_id": record["human_input"].get("target_node_id") or "",
        "disposition": "QUALIFICATION_PROMOTABLE" if promotable else "QUALIFICATION_BLOCKED",
        "block_reason": "" if promotable else f"HUMAN_{decision}_NON_PROMOTABLE",
        "phase3d_object": copy.deepcopy(phase3d_object),
    }


def validate_qualification_only_payload(payload: Mapping[str, Any]) -> None:
    """Prove that a Phase 3D-shaped candidate remains non-Production."""
    validate_payload(payload)
    for field, expected in (("document_type", PHASE3D_DOCUMENT_TYPE), ("review_scope", REVIEW_SCOPE),
                            ("qualification_only", True), ("full_operational_review_complete", False),
                            ("production_authorization", False), ("production_apply_authorized", False),
                            ("unselected_candidates_reviewed", False), ("qualified_execution_target", EXECUTION_TARGET)):
        _require(payload.get(field) == expected, "QUALIFICATION_ONLY_GUARD_MISMATCH", field)
    authority = payload.get("human_authorization") or {}
    _require(authority.get("production_authorization") is False and authority.get("production_apply_authorized") is False,
             "QUALIFICATION_AUTHORITY_BOUNDARY_INVALID")


def _phase3d_validation(payload: Mapping[str, Any], production_path: Path) -> dict[str, Any]:
    before = production_identity(production_path)
    validate_qualification_only_payload(payload)
    connection = _readonly_connection(production_path)
    try:
        validate_executable_operations(connection, payload)
        for mutation in payload["intended_mutations"]:
            where = " AND ".join(f'"{field}"=?' for field in mutation["key"])
            found = connection.execute(f'SELECT 1 FROM "{mutation["table"]}" WHERE {where} LIMIT 1',
                                       tuple(mutation["key"].values())).fetchone()
            _require(found is None, "PRODUCTION_ROW_ALREADY_EXISTS", mutation["mutation_id"])
    finally:
        connection.close()

    rejection = ""
    try:
        validate_final_payload(payload)
    except PromotionError as exc:
        rejection = str(exc)
    _require(rejection == "FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH", "PRODUCTION_FINAL_APPLY_GUARD_NOT_PROVEN", rejection)
    with tempfile.TemporaryDirectory(prefix="phase3f_stage1_requalification_") as raw:
        root, shadow = Path(raw), Path(raw) / "shadow.db"
        copy_production_to_shadow(production_path, shadow, before["sha256"])
        applied = apply_payload_to_shadow(payload, shadow, production_path)
        replay = apply_payload_to_shadow(payload, shadow, production_path)
        rollback = root / "rollback.db"
        copy_production_to_shadow(production_path, rollback, before["sha256"])
        rollback_sha, error = sha256_file(rollback), ""
        try:
            apply_payload_to_shadow(payload, rollback, production_path, inject_failure_after=2)
        except PromotionError as exc:
            error = str(exc)
        _require(error == "INJECTED_TRANSACTION_FAILURE", "ROLLBACK_INJECTION_NOT_OBSERVED")
        _require(sha256_file(rollback) == rollback_sha, "SHADOW_ROLLBACK_HASH_MISMATCH")
    after = production_identity(production_path)
    _require(before == after, "PRODUCTION_CHANGED")
    return {
        "payload_validation": "PASS", "preapply_validation": "PASS", "qualification_only_guard": "PASS",
        "production_final_apply_guard": "PASS", "production_final_apply_rejection": rejection,
        "shadow_apply": applied["status"], "shadow_integrity": applied["integrity"],
        "shadow_foreign_key_violations": len(applied["foreign_key_violations"]),
        "shadow_changed_tables": applied["changed_tables"], "shadow_post_counts": applied["post_counts"],
        "idempotent_replay": "PASS" if replay["status"] == "ALREADY_APPLIED" else "FAIL", "rollback": "PASS",
        "production_sha256": after["sha256"], "production_integrity": after["integrity"],
        "production_foreign_key_violations": len(after["foreign_key_violations"]), "production_changed": False,
    }


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
    claims_by_id, nodes_by_id = _records(packet, "claims"), _records(packet, "nodes")
    bundle_claims = {item["claim_id"]: item for item in bundle["claims"]}
    keep, timestamp = bundle_claims[KEEP_CLAIM], bundle_claims[KEEP_CLAIM]["created_at"]
    evidence_ids = {item["claim_id"]: item["evidence_id"] for node in packet["nodes"]
                    for item in node["content"].get("supporting_evidence") or []}
    for claim_id in (KEEP_CLAIM, REVIEW_CLAIM, DROP_CLAIM):
        claim = bundle_claims[claim_id]
        evidence_ids.setdefault(claim_id, deterministic_id("EVD", {
            "source_sha256": packet["source"]["source_sha256"], "claim_id": claim_id,
            "evidence_pointer": claim.get("evidence_pointer"), "evidence_excerpt": claim.get("evidence_excerpt"),
            "phase3c_evidence": claim.get("phase3c_evidence"),
        }))
    claim_items = []
    for claim_id in (KEEP_CLAIM, REVIEW_CLAIM, DROP_CLAIM):
        record, source_claim = claims_by_id[claim_id], bundle_claims[claim_id]
        executable = claim_id == KEEP_CLAIM
        claim_items.append({
            "claim_id": claim_id, "evidence_id": evidence_ids[claim_id], "immutable_claim": copy.deepcopy(source_claim),
            "qualification_record_content_sha256": record["content_sha256"],
            "reviewer_decision": {**copy.deepcopy(record["human_input"]), "reviewer": packet["human_completion"]["reviewer"],
                                  "packet_id": packet["packet_id"], "immutable_packet_sha256": packet["immutable_packet_sha256"]},
            "table_eligibility": copy.deepcopy(record["content"]["table_eligibility"]),
            "semantic_admission": copy.deepcopy(record["content"]["semantic_admission"]), "executable": executable,
            "disposition": "QUALIFICATION_PROMOTABLE" if executable else "QUALIFICATION_BLOCKED",
            "block_reason": "" if executable else f"HUMAN_{record['human_input']['decision']}_NON_PROMOTABLE",
        })

    catalog = _catalog(production_path)
    node_operations = [_node_operation(nodes_by_id[item], packet, catalog, {KEEP_CLAIM}, evidence_ids, timestamp)
                       for item in (CREATE_NODE, REUSE_NODE, DEFER_NODE)]
    relation_operations = _build_relation_operations(packet, node_operations, timestamp)
    phase3d_objects: dict[str, dict[str, Any]] = {
        KEEP_CLAIM: {"object_type": "CLAIM", "claim_id": KEEP_CLAIM,
                     "evidence_id": evidence_ids[KEEP_CLAIM], "executable": True}}
    for operation in node_operations + relation_operations:
        if operation["executable"]:
            phase3d_objects[operation["candidate_id"]] = {
                "object_type": "NODE_OPERATION" if operation in node_operations else "RELATION_OPERATION",
                "operation_id": operation["operation_id"], "operation": operation["operation"],
                "node_id": (operation.get("final_node") or {}).get("node_id") or operation.get("resolved_target_id"),
                "relation_id": (operation.get("final_relation") or {}).get("relation_id"), "executable": True,
            }
            phase3d_objects[operation["candidate_id"]] = {
                key: value for key, value in phase3d_objects[operation["candidate_id"]].items() if value is not None}
    selected = packet["claims"] + packet["nodes"] + packet["relations"]
    mapping_records = [_mapping_record(item, phase3d_objects.get(item["candidate_id"])) for item in selected]
    mapping_body = {
        "document_type": MAPPING_DOCUMENT_TYPE, "schema_version": SCHEMA_VERSION, "review_scope": REVIEW_SCOPE,
        "qualification_only": True, "full_operational_review_complete": False, "production_authorization": False,
        "production_apply_authorized": False, "unselected_candidates_reviewed": False,
        "source_qualification_packet": {"packet_id": packet["packet_id"],
                                        "immutable_packet_sha256": packet["immutable_packet_sha256"],
                                        "completed_packet_sha256": completion["completed_packet_sha256"]},
        "records": mapping_records, "counts": {"qualification_candidates": 7, "promotable": 4, "blocked": 3},
    }
    mapping_hash = canonical_sha256(mapping_body)
    mapping = {**mapping_body, "mapping_id": f"HANDOFF_MAPPING_{mapping_hash[:16].upper()}", "mapping_sha256": mapping_hash}

    source_row = _source_row(bundle, timestamp, bindings)
    mutations = [_mutation("sources", {"source_id": source_row["source_id"]}, source_row,
                           f"{packet['packet_id']}:QUALIFICATION_ONLY_SOURCE_LINEAGE")]
    claim_row = _claim_row(keep, timestamp)
    mutations.append(_mutation("claims", {"claim_id": KEEP_CLAIM}, claim_row, KEEP_CLAIM))
    create_operation = next(item for item in node_operations if item["candidate_id"] == CREATE_NODE)
    node_row = create_operation["final_node"]
    mutations.append(_mutation("nodes", {"node_id": node_row["node_id"]}, node_row, create_operation["operation_id"]))
    for alias in create_operation["aliases"]:
        row = {"alias": alias, "node_id": node_row["node_id"]}
        mutations.append(_mutation("node_aliases", row, row, create_operation["operation_id"]))
    relation_row = relation_operations[0]["final_relation"]
    mutations.append(_mutation("node_relations", {"relation_id": relation_row["relation_id"]}, relation_row,
                               relation_operations[0]["operation_id"]))

    payload_body = {
        "document_type": PHASE3D_DOCUMENT_TYPE, "payload_version": PAYLOAD_VERSION, "review_scope": REVIEW_SCOPE,
        "qualification_only": True, "full_operational_review_complete": False, "production_authorization": False,
        "production_apply_authorized": False, "unselected_candidates_reviewed": False,
        "qualified_execution_target": EXECUTION_TARGET, "adapter_type": ADAPTER_TYPE,
        "metadata": {
            "repository_commit": repository_commit, "production_sha256": production["sha256"],
            "production_schema_version": production["schema_version"], "production_schema_sha256": production["schema_sha256"],
            "production_counts": production["counts"], "source_sha256": packet["source"]["source_sha256"],
            "source_id": packet["source"]["source_id"], "run_id": packet["run"]["run_id"], "frozen_timestamp": timestamp,
            "input_artifact_roles_and_sha256": [{"role": item["role"], "file_sha256": item["file_sha256"]} for item in bindings],
            "input_artifacts": bindings,
        },
        "human_authorization": {
            "review_scope": REVIEW_SCOPE, "reviewer": completion["reviewer"], "authority_source": completion["authority_source"],
            "packet_id": packet["packet_id"], "immutable_packet_sha256": packet["immutable_packet_sha256"],
            "completed_packet_sha256": completion["completed_packet_sha256"], "completion_receipt_id": prior_receipt["receipt_id"],
            "completion_receipt_sha256": prior_receipt["receipt_sha256"], "qualification_decisions_validated": 7,
            "full_operational_review_complete": False, "production_authorization": False,
            "production_apply_authorized": False, "unselected_candidates_reviewed": False,
        },
        "handoff_mapping": {"mapping_id": mapping["mapping_id"], "mapping_sha256": mapping["mapping_sha256"]},
        "source": {"source_id": packet["source"]["source_id"], "source_sha256": packet["source"]["source_sha256"],
                   "qualification_only_lineage_insert": True, "production_source_authorization": False},
        "evidence": [{"evidence_id": item["evidence_id"], "claim_id": item["claim_id"],
                      "evidence_pointer": item["immutable_claim"].get("evidence_pointer"),
                      "evidence_excerpt": item["immutable_claim"].get("evidence_excerpt"),
                      "validation": item["immutable_claim"].get("validation") or {},
                      "phase3c_evidence": item["immutable_claim"].get("phase3c_evidence") or {}} for item in claim_items],
        "claims": claim_items, "node_operations": node_operations, "relation_operations": relation_operations,
        "link_operations": [], "intended_mutations": mutations,
        "excluded_from_promotion": [{"candidate_type": item["candidate_type"], "candidate_id": item["candidate_id"],
                                     "decision": item["human_decision"], "reason": item["block_reason"]}
                                    for item in mapping_records if item["disposition"] == "QUALIFICATION_BLOCKED"],
        "audit": {"qualification_candidate_count": 7, "qualification_promotable_count": 4,
                  "qualification_blocked_count": 3, "source_insert_count": 1, "executable_claim_count": 1,
                  "executable_node_operation_count": 2, "executable_relation_operation_count": 1,
                  "link_operation_count": 0, "llm_calls": 0, "full_review_candidate_count": 205,
                  "full_review_candidates_authorized": 0},
    }
    payload_hash = canonical_sha256(payload_body)
    payload = {**payload_body, "payload_id": f"PROMO_{payload_hash[:16].upper()}", "payload_hash": payload_hash}
    _require(payload_semantic_body(payload) == payload_body, "PAYLOAD_SEMANTIC_BODY_MISMATCH")
    phase3d = _phase3d_validation(payload, production_path)

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
