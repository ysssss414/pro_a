"""Generic Phase 3F completed-review handoff to Phase 3D qualification."""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .phase3f_review_completion import (
    PACKET_DOCUMENT_TYPE,
    PACKET_SCHEMA_VERSION,
    read_review_packet,
    validate_completed_review_packet,
)
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
    database_identity,
    decide_node_operation,
    deterministic_id,
    nfkc_casefold,
    payload_semantic_body,
    production_identity,
    resolve_identity,
    sha256_file,
    validate_executable_operations,
    validate_payload,
)
from .relation_structure import directed_path_exists


SCHEMA_VERSION = "1"
FULL_REVIEW_SCOPE = "PHASE3F_FULL_OPERATIONAL_REVIEW"
EXECUTION_TARGET = "SHADOW_ONLY_QUALIFICATION"
ADAPTER_TYPE = "GENERIC_FULL_OPERATIONAL_REVIEW_TO_PHASE3D_HANDOFF"
MAPPING_DOCUMENT_TYPE = "phase3f_operational_handoff_mapping"
VALIDATION_DOCUMENT_TYPE = "phase3f_operational_phase3d_validation_receipt"
RECEIPT_DOCUMENT_TYPE = "phase3f_operational_handoff_receipt"


class OperationalHandoffError(RuntimeError):
    """A stable fail-closed generic operational-handoff error."""


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise OperationalHandoffError(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class HandoffPolicy:
    """Mode-specific boundary values consumed by the single handoff core."""

    review_scope: str
    qualification_only: bool
    full_operational_review_complete: bool
    unselected_candidates_reviewed: bool
    adapter_type: str
    mapping_document_type: str
    legacy_qualification_labels: bool = False


FULL_OPERATIONAL_POLICY = HandoffPolicy(
    review_scope=FULL_REVIEW_SCOPE,
    qualification_only=False,
    full_operational_review_complete=True,
    unselected_candidates_reviewed=True,
    adapter_type=ADAPTER_TYPE,
    mapping_document_type=MAPPING_DOCUMENT_TYPE,
)


def _semantic(body: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    digest = canonical_sha256(body)
    return {
        **copy.deepcopy(dict(body)),
        "receipt_id": f"{prefix}_{digest[:16].upper()}",
        "receipt_sha256": digest,
    }


def _validate_semantic_receipt(receipt: Mapping[str, Any]) -> None:
    body = {
        key: copy.deepcopy(value)
        for key, value in receipt.items()
        if key not in {"receipt_id", "receipt_sha256"}
    }
    digest = canonical_sha256(body)
    _require(
        receipt.get("receipt_sha256") == digest,
        "COMPLETION_RECEIPT_HASH_MISMATCH",
    )
    receipt_id = receipt.get("receipt_id")
    _require(
        isinstance(receipt_id, str)
        and receipt_id.endswith(f"_{digest[:16].upper()}"),
        "COMPLETION_RECEIPT_ID_MISMATCH",
    )


def _binding(role: str, path: Path, root: Path) -> dict[str, Any]:
    _require(path.is_file(), "INPUT_ARTIFACT_MISSING", role)
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.resolve().as_posix()
    return {
        "role": role,
        "relative_path": relative,
        "file_sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def _catalog(production_path: Path) -> dict[str, Any]:
    connection = _readonly_connection(production_path)
    try:
        nodes = [
            dict(row)
            for row in connection.execute(
                "SELECT node_id,canonical_name,primary_type,status FROM nodes"
            )
        ]
        aliases = [
            dict(row)
            for row in connection.execute("SELECT alias,node_id FROM node_aliases")
        ]
        part_of_edges = {
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                "SELECT from_node_id,to_node_id FROM node_relations "
                "WHERE relation_type='part_of'"
            )
        }
    finally:
        connection.close()
    catalog = build_identity_catalog(nodes, aliases)
    catalog["part_of_edges"] = part_of_edges
    return catalog


def _existing_ids(production_path: Path, table: str, field: str) -> set[str]:
    connection = _readonly_connection(production_path)
    try:
        return {str(row[0]) for row in connection.execute(f'SELECT "{field}" FROM "{table}"')}
    finally:
        connection.close()


def _claim_row(claim: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    return {
        "claim_id": claim["claim_id"],
        "statement": claim["statement"],
        "nature": claim["nature"],
        "fact_time": claim.get("fact_time") or "",
        "publication_time": claim.get("publication_time") or "",
        "ingestion_time": claim.get("ingestion_time") or timestamp,
        "source_id": claim["source_id"],
        "evidence_pointer": claim.get("evidence_pointer") or "",
        "evidence_excerpt": claim.get("evidence_excerpt") or "",
        "attributed_to": claim.get("attributed_to") or "",
        "scope": claim.get("scope") or "",
        "assumption_text": claim.get("assumption_text") or "",
        "status": claim.get("status") or "current",
        "confidence": claim.get("confidence"),
        "novelty_level": claim.get("novelty_level") or "N2",
        "structured_json": canonical_json_bytes(claim.get("structured") or {}).decode(
            "utf-8"
        ),
        "created_at": claim.get("created_at") or timestamp,
    }


def _source_row(
    packet: Mapping[str, Any],
    bundle: Mapping[str, Any],
    timestamp: str,
    bindings: Sequence[Mapping[str, Any]],
    policy: HandoffPolicy,
) -> dict[str, Any]:
    source = bundle["source"]
    reviewed = bundle.get("proposed_source_metadata") or {}
    name = str(source["original_name"]).replace("/", "_").replace("\\", "_")
    date_path = str(reviewed.get("publication_time") or "1970-01-01").replace(
        "-", "/"
    )
    metadata = {
        "summary": reviewed.get("summary") or "",
        "parse_diagnostics": source.get("parse_diagnostics") or {},
        "parse_warnings": source.get("parse_warnings") or [],
        "semantic_eligibility": source.get("semantic_eligibility") or {},
        "phase3f_handoff": {
            "review_scope": policy.review_scope,
            "qualification_only": policy.qualification_only,
            "full_operational_review_complete": policy.full_operational_review_complete,
            "production_authorization": False,
            "archive_materialization": "NOT_AUTHORIZED",
            "input_artifacts": copy.deepcopy(list(bindings)),
        },
    }
    return {
        "source_id": source["proposed_source_id"],
        "title": reviewed.get("title") or source["original_name"],
        "original_name": source["original_name"],
        "archived_path": (
            f"archive/{date_path}/{source['proposed_source_id']}__{name}"
        ),
        "sha256": source["sha256"],
        "ingestion_mode": source.get("analysis_mode") or "deep",
        "analysis_mode": source.get("analysis_mode") or "deep",
        "source_type": source.get("source_type") or "unknown",
        "source_rank": reviewed.get("source_rank") or "UNRANKED",
        "origin_type": reviewed.get("source_origin_type") or "unknown",
        "author": reviewed.get("author") or "",
        "organization": reviewed.get("organization") or "",
        "publication_time": reviewed.get("publication_time") or "",
        "ingested_at": timestamp,
        "status": "analyzed",
        "ima_media_id": "",
        "ima_kb_id": "",
        "underlying_source_id": "",
        "metadata_json": canonical_json_bytes(metadata).decode("utf-8"),
    }


def _mutation(
    table: str,
    key: Mapping[str, Any],
    row: Mapping[str, Any],
    authority: str,
) -> dict[str, Any]:
    body = {
        "table": table,
        "operation": "INSERT",
        "key": dict(key),
        "row": dict(row),
        "authorized_by": authority,
    }
    return {"mutation_id": deterministic_id("MUT", body), **body}


def _records(packet: Mapping[str, Any], group: str) -> list[Mapping[str, Any]]:
    return sorted(packet.get(group) or [], key=lambda item: item["candidate_id"])


def _frozen_timestamp(bundle: Mapping[str, Any]) -> str:
    for claim in bundle.get("claims") or []:
        value = claim.get("created_at") or claim.get("ingestion_time")
        if isinstance(value, str) and value:
            return value
    reviewed = bundle.get("proposed_source_metadata") or {}
    publication = reviewed.get("publication_time")
    if isinstance(publication, str) and publication:
        return f"{publication}T00:00:00+00:00"
    return "1970-01-01T00:00:00+00:00"


def _evidence_id(source_sha256: str, claim: Mapping[str, Any]) -> str:
    return deterministic_id(
        "EVD",
        {
            "source_sha256": source_sha256,
            "claim_id": claim.get("claim_id"),
            "evidence_pointer": claim.get("evidence_pointer"),
            "evidence_excerpt": claim.get("evidence_excerpt"),
            "phase3c_evidence": claim.get("phase3c_evidence"),
        },
    )


def _blocked_operation(
    operation: Mapping[str, Any], requested: str, reason: str
) -> dict[str, Any]:
    return {
        **copy.deepcopy(dict(operation)),
        "operation": requested,
        "executable": False,
        "reason": reason,
    }


def _node_operations(
    packet: Mapping[str, Any],
    catalog: Mapping[str, Any],
    accepted_claim_ids: set[str],
    evidence_ids: Mapping[str, str],
    timestamp: str,
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    created_ids: set[str] = set()
    package_terms: dict[str, str] = {}
    for record in _records(packet, "nodes"):
        content = record["content"]
        human = record["human_input"]
        requested = human["decision"]
        claim_refs = sorted(
            accepted_claim_ids.intersection(content.get("supporting_claim_ids") or [])
        )
        candidate = {
            "candidate_id": record["candidate_id"],
            "canonical_name": content.get("proposed_name"),
            "primary_type": content.get("proposed_type"),
            "aliases": copy.deepcopy(content.get("proposed_aliases") or []),
            "node_id": content.get("prospective_node_id"),
            "match_term": content.get("proposed_name"),
            "approved_aliases": [],
            "claim_refs": claim_refs,
            "evidence_refs": [evidence_ids[item] for item in claim_refs],
            "frozen_timestamp": timestamp,
            "reason": human["reason"],
            "review_record_content_sha256": record["content_sha256"],
        }
        operation = decide_node_operation(
            candidate,
            requested_operation=requested,
            review_decision={
                "CREATE": "APPROVE_CREATE",
                "REUSE": "APPROVE_REUSE",
            }.get(requested, requested),
            catalog=catalog,
            run_id=packet["run"]["run_id"],
        )
        operation["review_authorization"] = {
            "decision": requested,
            "reason": human["reason"],
            "target_node_id": human.get("target_node_id") or "",
            "packet_id": packet["packet_id"],
            "record_content_sha256": record["content_sha256"],
        }
        if requested == "CREATE":
            node = operation.get("final_node") or {}
            node_id = node.get("node_id")
            reason = ""
            if not node_id or node_id in created_ids or node_id in (catalog.get("nodes") or {}):
                reason = f"NODE_ID_COLLISION:{node_id}"
            else:
                terms = [node.get("canonical_name"), *(operation.get("aliases") or [])]
                for index, term in enumerate(terms):
                    if resolve_identity(catalog, str(term))["all_ids"]:
                        prefix = "CANONICAL_COLLISION" if index == 0 else "ALIAS_COLLISION"
                        reason = f"{prefix}:{term}"
                        break
                    owner = package_terms.get(nfkc_casefold(str(term)))
                    if owner not in (None, node_id):
                        reason = f"PACKAGE_INTERNAL_COLLISION:{term}"
                        break
            if reason:
                operation = _blocked_operation(operation, requested, reason)
            else:
                created_ids.add(str(node_id))
                for term in [node.get("canonical_name"), *(operation.get("aliases") or [])]:
                    package_terms[nfkc_casefold(str(term))] = str(node_id)
        elif requested == "REUSE":
            target = human.get("target_node_id")
            if operation.get("executable") is not True:
                operation = _blocked_operation(
                    operation, requested, str(operation.get("reason") or "REUSE_NOT_RESOLVED")
                )
            elif operation.get("resolved_target_id") != target:
                operation = _blocked_operation(
                    operation, requested, "AUTHORIZED_REUSE_TARGET_MISMATCH"
                )
        operations.append(operation)
    return operations


def _relation_operations(
    packet: Mapping[str, Any],
    node_operations: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    node_by_id = {item["candidate_id"]: item for item in node_operations}
    existing_node_ids = set(catalog.get("nodes") or {})
    created_node_ids = {
        (item.get("final_node") or {}).get("node_id")
        for item in node_operations
        if item.get("operation") == "CREATE" and item.get("executable") is True
    }
    final_node_ids = existing_node_ids | {item for item in created_node_ids if item}
    connection_edges = set(catalog.get("part_of_edges") or set())
    operations: list[dict[str, Any]] = []
    for record in _records(packet, "relations"):
        content = record["content"]
        human = record["human_input"]
        requested = human["decision"]
        base = {
            "operation_id": deterministic_id(
                "OP_REL",
                {"candidate_id": record["candidate_id"], "requested": requested},
            ),
            "candidate_id": record["candidate_id"],
            "candidate": copy.deepcopy(content),
            "operation": requested,
            "executable": False,
            "reason": f"HUMAN_{requested}_NON_PROMOTABLE",
            "review_authorization": {
                "decision": requested,
                "reason": human["reason"],
                "packet_id": packet["packet_id"],
                "record_content_sha256": record["content_sha256"],
            },
        }
        if requested != "CREATE":
            operations.append(base)
            continue
        child_operation = node_by_id.get(content.get("child_node_candidate_id"))
        reason = ""
        if not child_operation or not (
            child_operation.get("operation") == "CREATE"
            and child_operation.get("executable") is True
        ):
            reason = "PARENT_PLACEMENT_CREATE_CONDITION_FAILED"
        child_id = content.get("prospective_child_node_id")
        parent_id = content.get("parent_node_id")
        if not reason and content.get("relation_type") != "part_of":
            reason = "RELATION_TYPE_NOT_SUPPORTED"
        if not reason and (child_id not in final_node_ids or parent_id not in final_node_ids):
            reason = "RELATION_ENDPOINT_MISSING"
        if not reason and child_id == parent_id:
            reason = "RELATION_SELF_LOOP"
        if not reason and (str(child_id), str(parent_id)) in connection_edges:
            reason = "RELATION_DUPLICATE"
        if not reason and directed_path_exists(connection_edges, str(parent_id), str(child_id)):
            reason = "RELATION_CYCLE"
        if not reason and directed_path_exists(connection_edges, str(child_id), str(parent_id)):
            reason = "RELATION_TRANSITIVE_REDUNDANCY"
        if reason:
            base["reason"] = reason
            operations.append(base)
            continue
        relation = {
            "relation_id": deterministic_id(
                "REL", {"candidate_id": record["candidate_id"], "content": content}
            ),
            "from_node_id": child_id,
            "relation_type": content["relation_type"],
            "to_node_id": parent_id,
            "scope": "",
            "valid_from": "",
            "valid_to": "",
            "confidence": None,
            "status": "current",
            "evidence_claim_id": None,
            "created_at": timestamp,
        }
        base.update(
            {
                "executable": True,
                "reason": human["reason"],
                "final_relation": relation,
            }
        )
        connection_edges.add((str(child_id), str(parent_id)))
        operations.append(base)
    return operations


def _phase3d_object(
    candidate_type: str, value: Mapping[str, Any]
) -> dict[str, Any] | None:
    if value.get("executable") is not True:
        return None
    if candidate_type == "CLAIM":
        return {
            "object_type": "CLAIM",
            "claim_id": value["claim_id"],
            "evidence_id": value["evidence_id"],
            "executable": True,
        }
    if candidate_type == "NODE":
        return {
            key: item
            for key, item in {
                "object_type": "NODE_OPERATION",
                "operation_id": value["operation_id"],
                "operation": value["operation"],
                "node_id": (value.get("final_node") or {}).get("node_id")
                or value.get("resolved_target_id"),
                "executable": True,
            }.items()
            if item is not None
        }
    return {
        "object_type": "RELATION_OPERATION",
        "operation_id": value["operation_id"],
        "operation": value["operation"],
        "relation_id": (value.get("final_relation") or {}).get("relation_id"),
        "executable": True,
    }


def _disposition(
    record: Mapping[str, Any],
    phase3d_object: Mapping[str, Any] | None,
    operation_reason: str,
    policy: HandoffPolicy,
) -> tuple[str, str]:
    decision = record["human_input"]["decision"]
    if phase3d_object is not None:
        if policy.legacy_qualification_labels:
            return "QUALIFICATION_PROMOTABLE", ""
        return "EXECUTABLE", ""
    if policy.legacy_qualification_labels:
        return "QUALIFICATION_BLOCKED", f"HUMAN_{decision}_NON_PROMOTABLE"
    if decision == "DROP":
        return "BLOCKED_HUMAN_DROP", "HUMAN_DROP_NON_PROMOTABLE"
    if decision == "KEEP_NEEDS_REVIEW":
        return (
            "BLOCKED_HUMAN_KEEP_NEEDS_REVIEW",
            "HUMAN_KEEP_NEEDS_REVIEW_NON_PROMOTABLE",
        )
    if decision == "DEFER":
        return "BLOCKED_HUMAN_DEFER", "HUMAN_DEFER_NON_PROMOTABLE"
    if decision == "REJECT":
        return "BLOCKED_HUMAN_REJECT", "HUMAN_REJECT_NON_PROMOTABLE"
    return "BLOCKED_EXISTING_PAYLOAD_CONTRACT", operation_reason


def _mapping_record(
    record: Mapping[str, Any],
    phase3d_object: Mapping[str, Any] | None,
    operation_reason: str,
    policy: HandoffPolicy,
) -> dict[str, Any]:
    disposition, block_reason = _disposition(
        record, phase3d_object, operation_reason, policy
    )
    return {
        "candidate_type": record["candidate_type"],
        "candidate_id": record["candidate_id"],
        "qualification_record_content_sha256": record["content_sha256"],
        "human_decision": record["human_input"]["decision"],
        "human_reason": record["human_input"]["reason"],
        "target_node_id": record["human_input"].get("target_node_id") or "",
        "disposition": disposition,
        "block_reason": block_reason,
        "phase3d_object": copy.deepcopy(phase3d_object),
    }


def validate_handoff_accounting(
    mapping: Mapping[str, Any], payload: Mapping[str, Any]
) -> None:
    body = {
        key: copy.deepcopy(value)
        for key, value in mapping.items()
        if key not in {"mapping_id", "mapping_sha256"}
    }
    digest = canonical_sha256(body)
    _require(mapping.get("mapping_sha256") == digest, "MAPPING_HASH_MISMATCH")
    _require(
        mapping.get("mapping_id") == f"HANDOFF_MAPPING_{digest[:16].upper()}",
        "MAPPING_ID_MISMATCH",
    )
    records = mapping.get("records") or []
    actual_ids = [item.get("candidate_id") for item in records]
    payload_ids = [item.get("claim_id") for item in payload.get("claims") or []]
    payload_ids += [
        item.get("candidate_id") for item in payload.get("node_operations") or []
    ]
    payload_ids += [
        item.get("candidate_id") for item in payload.get("relation_operations") or []
    ]
    _require(len(actual_ids) == len(set(actual_ids)), "DUPLICATE_MAPPING_CANDIDATE")
    _require(set(actual_ids) == set(payload_ids), "SILENT_CANDIDATE_OMISSION")
    _require(len(actual_ids) == len(payload_ids), "SILENT_CANDIDATE_OMISSION")
    executable = sum(item.get("phase3d_object") is not None for item in records)
    _require(
        executable == sum(item.get("executable") is True for item in payload.get("claims") or [])
        + sum(item.get("executable") is True for item in payload.get("node_operations") or [])
        + sum(item.get("executable") is True for item in payload.get("relation_operations") or []),
        "MAPPING_EXECUTABLE_COUNT_MISMATCH",
    )
    for item in records:
        if item.get("phase3d_object") is None:
            _require(bool(item.get("block_reason")), "MAPPING_BLOCK_REASON_MISSING")


def validate_handoff_payload(
    payload: Mapping[str, Any], policy: HandoffPolicy = FULL_OPERATIONAL_POLICY
) -> None:
    validate_payload(payload)
    for field, expected in (
        ("document_type", PHASE3D_DOCUMENT_TYPE),
        ("review_scope", policy.review_scope),
        ("qualification_only", policy.qualification_only),
        (
            "full_operational_review_complete",
            policy.full_operational_review_complete,
        ),
        ("production_authorization", False),
        ("production_apply_authorized", False),
        ("unselected_candidates_reviewed", policy.unselected_candidates_reviewed),
        ("qualified_execution_target", EXECUTION_TARGET),
    ):
        _require(payload.get(field) == expected, "HANDOFF_BOUNDARY_INVALID", field)
    authority = payload.get("human_authorization") or {}
    _require(
        authority.get("production_authorization") is False
        and authority.get("production_apply_authorized") is False,
        "HANDOFF_AUTHORITY_BOUNDARY_INVALID",
    )
    for claim in payload.get("claims") or []:
        decision = (claim.get("reviewer_decision") or {}).get("decision")
        if claim.get("executable") is True:
            _require(decision == "KEEP", "NON_KEEP_CLAIM_EXECUTABLE", str(claim.get("claim_id")))
    for operation in payload.get("node_operations") or []:
        decision = (operation.get("review_authorization") or {}).get("decision")
        if operation.get("executable") is True:
            _require(decision in {"CREATE", "REUSE"}, "NON_AUTHORIZED_NODE_EXECUTABLE")
            _require(operation.get("operation") == decision, "NODE_DECISION_OPERATION_MISMATCH")
    for operation in payload.get("relation_operations") or []:
        decision = (operation.get("review_authorization") or {}).get("decision")
        if operation.get("executable") is True:
            _require(decision == "CREATE", "NON_AUTHORIZED_RELATION_EXECUTABLE")
            _require(operation.get("operation") == "CREATE", "RELATION_DECISION_OPERATION_MISMATCH")

    mutations = payload.get("intended_mutations") or []
    claim_mutations = {
        item["key"].get("claim_id")
        for item in mutations
        if item.get("table") == "claims"
    }
    executable_claims = {
        item.get("claim_id")
        for item in payload.get("claims") or []
        if item.get("executable") is True
    }
    _require(claim_mutations == executable_claims, "CLAIM_MUTATION_AUTHORITY_MISMATCH")
    node_mutations = {
        item["key"].get("node_id")
        for item in mutations
        if item.get("table") == "nodes"
    }
    executable_nodes = {
        (item.get("final_node") or {}).get("node_id")
        for item in payload.get("node_operations") or []
        if item.get("executable") is True and item.get("operation") == "CREATE"
    }
    _require(node_mutations == executable_nodes, "NODE_MUTATION_AUTHORITY_MISMATCH")
    alias_mutations = {
        (item["row"].get("alias"), item["row"].get("node_id"))
        for item in mutations
        if item.get("table") == "node_aliases"
    }
    executable_aliases = {
        (alias, (item.get("final_node") or {}).get("node_id"))
        for item in payload.get("node_operations") or []
        if item.get("executable") is True and item.get("operation") == "CREATE"
        for alias in item.get("aliases") or []
    }
    _require(
        alias_mutations == executable_aliases,
        "ALIAS_MUTATION_AUTHORITY_MISMATCH",
    )
    relation_mutations = {
        item["key"].get("relation_id")
        for item in mutations
        if item.get("table") == "node_relations"
    }
    executable_relations = {
        (item.get("final_relation") or {}).get("relation_id")
        for item in payload.get("relation_operations") or []
        if item.get("executable") is True
    }
    _require(
        relation_mutations == executable_relations,
        "RELATION_MUTATION_AUTHORITY_MISMATCH",
    )
    source_mutations = {
        item["key"].get("source_id")
        for item in mutations
        if item.get("table") == "sources"
    }
    _require(
        source_mutations == {payload.get("source", {}).get("source_id")},
        "SOURCE_MUTATION_AUTHORITY_MISMATCH",
    )
    _require(
        not (payload.get("link_operations") or [])
        and not any(
            item.get("table") in {"claim_node_links", "source_node_links"}
            for item in mutations
        ),
        "UNAUTHORIZED_LINK_MUTATION",
    )
    _require(
        not any(
            item.get("table")
            in {
                "current_views",
                "proposals",
                "knowledge_gaps",
                "research_questions",
                "ima_objects",
            }
            for item in mutations
        ),
        "UNAUTHORIZED_OBJECT_MUTATION",
    )


def assert_deterministic_handoff(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> None:
    _require(first == second, "DETERMINISTIC_RERUN_MISMATCH")


def _materialize_receipt_authorized_decisions(
    packet: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply only per-candidate overlays already sealed by the completion receipt."""
    expanded = copy.deepcopy(dict(packet))
    completion = receipt.get("completion_validation") or {}
    overlays = completion.get("authorized_decision_overlays")
    if overlays is None:
        overlays = completion.get("batch_expansion_audit") or []
    _require(isinstance(overlays, list), "COMPLETION_DECISION_OVERLAYS_INVALID")
    records = {
        item["candidate_id"]: item
        for group in ("claims", "nodes", "relations")
        for item in expanded.get(group) or []
    }
    seen: set[str] = set()
    reviewer = (expanded.get("human_completion") or {}).get("reviewer")
    for overlay in overlays:
        _require(isinstance(overlay, dict), "COMPLETION_DECISION_OVERLAY_INVALID")
        candidate_id = overlay.get("candidate_id")
        _require(
            isinstance(candidate_id, str) and candidate_id in records,
            "COMPLETION_DECISION_OVERLAY_CANDIDATE_UNKNOWN",
            str(candidate_id),
        )
        _require(
            candidate_id not in seen,
            "COMPLETION_DECISION_OVERLAY_DUPLICATE",
            candidate_id,
        )
        seen.add(candidate_id)
        record = records[candidate_id]
        expected_hash = overlay.get("candidate_content_sha256") or overlay.get(
            "content_sha256"
        )
        _require(
            expected_hash == record.get("content_sha256"),
            "COMPLETION_DECISION_OVERLAY_CONTENT_MISMATCH",
            candidate_id,
        )
        _require(
            overlay.get("reviewer") == reviewer,
            "COMPLETION_DECISION_OVERLAY_REVIEWER_MISMATCH",
            candidate_id,
        )
        human = record["human_input"]
        _require(
            all(value == "" for value in human.values()),
            "COMPLETION_DECISION_OVERLAY_CONFLICT",
            candidate_id,
        )
        human["decision"] = overlay.get("decision")
        human["reason"] = overlay.get("reason")
        if "target_node_id" in human:
            human["target_node_id"] = overlay.get("target_node_id") or ""
    return expanded


def _phase3d_validation(
    payload: Mapping[str, Any],
    mapping: Mapping[str, Any],
    production_path: Path,
    policy: HandoffPolicy,
) -> dict[str, Any]:
    before = production_identity(production_path)
    validate_handoff_payload(payload, policy)
    validate_handoff_accounting(mapping, payload)
    connection = _readonly_connection(production_path)
    try:
        validate_executable_operations(connection, payload)
        for mutation in payload["intended_mutations"]:
            where = " AND ".join(f'"{field}"=?' for field in mutation["key"])
            found = connection.execute(
                f'SELECT 1 FROM "{mutation["table"]}" WHERE {where} LIMIT 1',
                tuple(mutation["key"].values()),
            ).fetchone()
            _require(found is None, "PRODUCTION_ROW_ALREADY_EXISTS", mutation["mutation_id"])
    finally:
        connection.close()

    final_rejection = ""
    try:
        validate_final_payload(payload)
    except PromotionError as exc:
        final_rejection = str(exc)
    _require(
        final_rejection == "FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH",
        "PRODUCTION_FINAL_APPLY_GUARD_NOT_PROVEN",
        final_rejection,
    )

    with tempfile.TemporaryDirectory(prefix="phase3f_operational_handoff_") as raw:
        root = Path(raw)
        shadow = root / "shadow.db"
        copy_production_to_shadow(production_path, shadow, before["sha256"])
        applied = apply_payload_to_shadow(payload, shadow, production_path)
        replay = apply_payload_to_shadow(payload, shadow, production_path)

        rollback = root / "rollback.db"
        copy_production_to_shadow(production_path, rollback, before["sha256"])
        rollback_before = database_identity(rollback, require_no_sidecars=True)
        rollback_error = ""
        try:
            apply_payload_to_shadow(
                payload,
                rollback,
                production_path,
                inject_failure_after=max(1, min(2, len(payload["intended_mutations"]))),
            )
        except PromotionError as exc:
            rollback_error = str(exc)
        _require(
            rollback_error == "INJECTED_TRANSACTION_FAILURE",
            "ROLLBACK_INJECTION_NOT_OBSERVED",
        )
        rollback_after = database_identity(rollback, require_no_sidecars=True)
        _require(
            rollback_before["semantic_snapshot"] == rollback_after["semantic_snapshot"],
            "SHADOW_ROLLBACK_SEMANTIC_MISMATCH",
        )

        restore = root / "restore.db"
        restore_backup = root / "restore_backup.db"
        copy_production_to_shadow(production_path, restore, before["sha256"])
        copy_production_to_shadow(production_path, restore_backup, before["sha256"])
        apply_payload_to_shadow(payload, restore, production_path)
        shutil.copyfile(restore_backup, restore)
        restored = database_identity(restore, require_no_sidecars=True)
        _require(
            {key: value for key, value in restored.items() if key != "path"}
            == {key: value for key, value in before.items() if key != "path"},
            "SHADOW_RESTORE_MISMATCH",
        )

    after = production_identity(production_path)
    _require(before == after, "PRODUCTION_CHANGED")
    operation_counts = Counter(
        mutation["table"] for mutation in payload["intended_mutations"]
    )
    return {
        "payload_validation": "PASS",
        "preapply_validation": "PASS",
        "handoff_boundary": "PASS",
        "production_final_apply_guard": "PASS",
        "production_final_apply_rejection": final_rejection,
        "shadow_apply": applied["status"],
        "semantic_diff": "PASS",
        "shadow_integrity": applied["integrity"],
        "shadow_foreign_key_violations": len(applied["foreign_key_violations"]),
        "shadow_changed_tables": applied["changed_tables"],
        "shadow_post_counts": applied["post_counts"],
        "idempotent_replay": (
            "PASS" if replay["status"] == "ALREADY_APPLIED" else "FAIL"
        ),
        "rollback": "PASS",
        "rollback_qualification": "PASS",
        "restore": "PASS",
        "operation_counts": dict(sorted(operation_counts.items())),
        "production_sha256": after["sha256"],
        "production_integrity": after["integrity"],
        "production_foreign_key_violations": len(after["foreign_key_violations"]),
        "production_changed": False,
    }


def build_handoff_core(
    *,
    packet: Mapping[str, Any],
    completion: Mapping[str, Any],
    completion_receipt: Mapping[str, Any],
    bundle: Mapping[str, Any],
    production_path: str | Path,
    repository_commit: str,
    bindings: Sequence[Mapping[str, Any]],
    authority: Mapping[str, Any],
    policy: HandoffPolicy,
) -> dict[str, Any]:
    """Build mapping and Phase 3D payload for the selected immutable review contract."""
    if packet.get("document_type") == "phase3f_foundation_baseline_review_packet":
        from .phase3f_foundation_baseline import build_foundation_handoff
        return build_foundation_handoff(
            packet=packet, blank_packet=bundle["blank_packet"],
            production_path=production_path, repository_commit=repository_commit,
        )
    production_path = Path(production_path).resolve()
    _require(
        isinstance(repository_commit, str) and len(repository_commit) == 40,
        "REPOSITORY_COMMIT_INVALID",
    )
    production = production_identity(production_path)
    source_id = packet["source"]["source_id"]
    source_sha256 = packet["source"]["source_sha256"]
    _require(bundle["source"]["proposed_source_id"] == source_id, "BUNDLE_SOURCE_ID_MISMATCH")
    _require(bundle["source"]["sha256"] == source_sha256, "BUNDLE_SOURCE_SHA_MISMATCH")
    bundle_claims = {item["claim_id"]: item for item in bundle.get("claims") or []}
    claim_records = _records(packet, "claims")
    _require(
        all(item["candidate_id"] in bundle_claims for item in claim_records),
        "BUNDLE_CLAIM_MISSING",
    )
    timestamp = _frozen_timestamp(bundle)
    evidence_ids = {
        claim_id: _evidence_id(source_sha256, claim)
        for claim_id, claim in bundle_claims.items()
    }
    existing_claim_ids = _existing_ids(production_path, "claims", "claim_id")
    _require(
        source_id not in _existing_ids(production_path, "sources", "source_id"),
        "SOURCE_ID_COLLISION",
        source_id,
    )

    claim_items: list[dict[str, Any]] = []
    accepted_claim_ids: set[str] = set()
    claim_phase3d: dict[str, dict[str, Any]] = {}
    for record in claim_records:
        claim_id = record["candidate_id"]
        source_claim = bundle_claims[claim_id]
        _require(source_claim.get("source_id") == source_id, "CLAIM_SOURCE_MISMATCH", claim_id)
        human = record["human_input"]
        executable = human["decision"] == "KEEP" and claim_id not in existing_claim_ids
        block_reason = ""
        if human["decision"] == "KEEP" and not executable:
            block_reason = f"CLAIM_ID_COLLISION:{claim_id}"
        item = {
            "claim_id": claim_id,
            "source_id": source_id,
            "evidence_id": evidence_ids[claim_id],
            "immutable_claim": copy.deepcopy(source_claim),
            "qualification_record_content_sha256": record["content_sha256"],
            "reviewer_decision": {
                **copy.deepcopy(human),
                "reviewer": packet["human_completion"]["reviewer"],
                "packet_id": packet["packet_id"],
                "immutable_packet_sha256": packet["immutable_packet_sha256"],
            },
            "table_eligibility": copy.deepcopy(record["content"]["table_eligibility"]),
            "semantic_admission": copy.deepcopy(record["content"]["semantic_admission"]),
            "executable": executable,
            "disposition": "EXECUTABLE" if executable else "BLOCKED",
            "block_reason": block_reason
            or ("" if executable else f"HUMAN_{human['decision']}_NON_PROMOTABLE"),
        }
        claim_items.append(item)
        if executable:
            accepted_claim_ids.add(claim_id)
            claim_phase3d[claim_id] = _phase3d_object("CLAIM", item) or {}

    catalog = _catalog(production_path)
    node_operations = _node_operations(
        packet, catalog, accepted_claim_ids, evidence_ids, timestamp
    )
    relation_operations = _relation_operations(
        packet, node_operations, catalog, timestamp
    )
    node_by_candidate = {item["candidate_id"]: item for item in node_operations}
    relation_by_candidate = {
        item["candidate_id"]: item for item in relation_operations
    }

    mapping_records: list[dict[str, Any]] = []
    for record in claim_records:
        claim_id = record["candidate_id"]
        item = next(value for value in claim_items if value["claim_id"] == claim_id)
        mapping_records.append(
            _mapping_record(
                record,
                claim_phase3d.get(claim_id),
                item["block_reason"],
                policy,
            )
        )
    for record in _records(packet, "nodes"):
        operation = node_by_candidate[record["candidate_id"]]
        mapping_records.append(
            _mapping_record(
                record,
                _phase3d_object("NODE", operation),
                str(operation.get("reason") or "NODE_NOT_EXECUTABLE"),
                policy,
            )
        )
    for record in _records(packet, "relations"):
        operation = relation_by_candidate[record["candidate_id"]]
        mapping_records.append(
            _mapping_record(
                record,
                _phase3d_object("PARENT_PLACEMENT", operation),
                str(operation.get("reason") or "RELATION_NOT_EXECUTABLE"),
                policy,
            )
        )
    mapping_records.sort(key=lambda item: (item["candidate_type"], item["candidate_id"]))
    executable_count = sum(item["phase3d_object"] is not None for item in mapping_records)
    if policy.legacy_qualification_labels:
        mapping_counts: dict[str, Any] = {
            "qualification_candidates": len(mapping_records),
            "promotable": executable_count,
            "blocked": len(mapping_records) - executable_count,
        }
    else:
        mapping_counts = {
            "total_candidates": len(mapping_records),
            "executable": executable_count,
            "blocked": len(mapping_records) - executable_count,
            "by_candidate_type": dict(
                sorted(Counter(item["candidate_type"] for item in mapping_records).items())
            ),
            "by_human_decision": dict(
                sorted(Counter(item["human_decision"] for item in mapping_records).items())
            ),
            "by_disposition": dict(
                sorted(Counter(item["disposition"] for item in mapping_records).items())
            ),
        }
    mapping_body = {
        "document_type": policy.mapping_document_type,
        "schema_version": SCHEMA_VERSION,
        "review_scope": policy.review_scope,
        "qualification_only": policy.qualification_only,
        "full_operational_review_complete": policy.full_operational_review_complete,
        "production_authorization": False,
        "production_apply_authorized": False,
        "unselected_candidates_reviewed": policy.unselected_candidates_reviewed,
        "source_review_packet": {
            "packet_id": packet["packet_id"],
            "immutable_packet_sha256": packet["immutable_packet_sha256"],
            "completed_packet_sha256": completion["completed_packet_sha256"],
        },
        "records": mapping_records,
        "counts": mapping_counts,
        "no_silent_loss": True,
    }
    mapping_hash = canonical_sha256(mapping_body)
    mapping = {
        **mapping_body,
        "mapping_id": f"HANDOFF_MAPPING_{mapping_hash[:16].upper()}",
        "mapping_sha256": mapping_hash,
    }

    source_row = _source_row(packet, bundle, timestamp, bindings, policy)
    mutations = [
        _mutation(
            "sources",
            {"source_id": source_id},
            source_row,
            f"{packet['packet_id']}:SOURCE_LINEAGE",
        )
    ]
    for item in sorted(
        (value for value in claim_items if value["executable"]),
        key=lambda value: value["claim_id"],
    ):
        row = _claim_row(item["immutable_claim"], timestamp)
        mutations.append(
            _mutation(
                "claims",
                {"claim_id": item["claim_id"]},
                row,
                item["claim_id"],
            )
        )
    for operation in node_operations:
        if operation.get("operation") != "CREATE" or operation.get("executable") is not True:
            continue
        node = operation["final_node"]
        mutations.append(
            _mutation(
                "nodes",
                {"node_id": node["node_id"]},
                node,
                operation["operation_id"],
            )
        )
        for alias in sorted(operation.get("aliases") or []):
            row = {"alias": alias, "node_id": node["node_id"]}
            mutations.append(
                _mutation("node_aliases", row, row, operation["operation_id"])
            )
    for operation in relation_operations:
        if operation.get("executable") is not True:
            continue
        relation = operation["final_relation"]
        mutations.append(
            _mutation(
                "node_relations",
                {"relation_id": relation["relation_id"]},
                relation,
                operation["operation_id"],
            )
        )

    evidence = [
        {
            "evidence_id": evidence_ids[claim_id],
            "claim_id": claim_id,
            "source_id": source_id,
            "source_sha256": source_sha256,
            "evidence_pointer": claim.get("evidence_pointer") or "",
            "evidence_excerpt": claim.get("evidence_excerpt") or "",
            "validation": copy.deepcopy(claim.get("validation") or {}),
            "phase3c_evidence": copy.deepcopy(claim.get("phase3c_evidence") or {}),
        }
        for claim_id, claim in sorted(bundle_claims.items())
        if claim_id in {record["candidate_id"] for record in claim_records}
    ]
    operation_counts = Counter(item["table"] for item in mutations)
    payload_body = {
        "document_type": PHASE3D_DOCUMENT_TYPE,
        "payload_version": PAYLOAD_VERSION,
        "review_scope": policy.review_scope,
        "qualification_only": policy.qualification_only,
        "full_operational_review_complete": policy.full_operational_review_complete,
        "production_authorization": False,
        "production_apply_authorized": False,
        "unselected_candidates_reviewed": policy.unselected_candidates_reviewed,
        "qualified_execution_target": EXECUTION_TARGET,
        "adapter_type": policy.adapter_type,
        "metadata": {
            "repository_commit": repository_commit,
            "production_sha256": production["sha256"],
            "production_schema_version": production["schema_version"],
            "production_schema_sha256": production["schema_sha256"],
            "production_counts": production["counts"],
            "source_sha256": source_sha256,
            "source_id": source_id,
            "run_id": packet["run"]["run_id"],
            "frozen_timestamp": timestamp,
            "input_artifact_roles_and_sha256": [
                {"role": item["role"], "file_sha256": item["file_sha256"]}
                for item in bindings
            ],
            "input_artifacts": copy.deepcopy(list(bindings)),
        },
        "human_authorization": {
            "review_scope": policy.review_scope,
            "decision_authority": packet["human_completion"]["decision_authority"],
            "reviewer": completion["reviewer"],
            "authority_source": authority.get("authority_source") or "USER_HUMAN_REVIEW",
            "packet_id": packet["packet_id"],
            "immutable_packet_sha256": packet["immutable_packet_sha256"],
            "completed_packet_sha256": completion["completed_packet_sha256"],
            "completion_receipt_id": completion_receipt["receipt_id"],
            "completion_receipt_sha256": completion_receipt["receipt_sha256"],
            "authorization_file_sha256": authority.get("authorization_file_sha256") or "",
            "authorization_semantic_sha256": authority.get("authorization_semantic_sha256") or "",
            "decisions_validated": completion["total_operational_decisions_validated"],
            "decision_counts": copy.deepcopy(completion["decision_counts"]),
            "full_operational_review_complete": policy.full_operational_review_complete,
            "production_authorization": False,
            "production_apply_authorized": False,
            "unselected_candidates_reviewed": policy.unselected_candidates_reviewed,
            "llm_authorization_used": False,
        },
        "handoff_mapping": {
            "mapping_id": mapping["mapping_id"],
            "mapping_sha256": mapping["mapping_sha256"],
        },
        "source": {
            "source_id": source_id,
            "source_sha256": source_sha256,
            "qualification_only_lineage_insert": policy.qualification_only,
            "production_source_authorization": False,
        },
        "sources": [
            {
                "source_id": source_id,
                "source_sha256": source_sha256,
                "artifact_hashes": [
                    {"role": item["role"], "file_sha256": item["file_sha256"]}
                    for item in bindings
                ],
                "archive_copy_intent": {
                    "status": "NOT_AUTHORIZED_DURING_QUALIFICATION",
                    "destination": source_row["archived_path"],
                },
                "intended_row": source_row,
            }
        ],
        "evidence": evidence,
        "claims": claim_items,
        "node_operations": node_operations,
        "relation_operations": relation_operations,
        "link_operations": [],
        "intended_mutations": mutations,
        "excluded_from_promotion": [
            {
                "candidate_type": item["candidate_type"],
                "candidate_id": item["candidate_id"],
                "decision": item["human_decision"],
                "reason": item["block_reason"],
            }
            for item in mapping_records
            if item["phase3d_object"] is None
        ],
        "audit": {
            "reviewed_candidate_count": len(mapping_records),
            "executable_candidate_count": executable_count,
            "blocked_candidate_count": len(mapping_records) - executable_count,
            "source_insert_count": operation_counts.get("sources", 0),
            "executable_claim_count": sum(item["executable"] for item in claim_items),
            "executable_node_operation_count": sum(
                item.get("executable") is True for item in node_operations
            ),
            "executable_relation_operation_count": sum(
                item.get("executable") is True for item in relation_operations
            ),
            "link_operation_count": 0,
            "operation_counts": dict(sorted(operation_counts.items())),
            "llm_calls": 0,
            "no_silent_loss": True,
        },
    }
    payload_hash = canonical_sha256(payload_body)
    payload = {
        **payload_body,
        "payload_id": f"PROMO_{payload_hash[:16].upper()}",
        "payload_hash": payload_hash,
    }
    _require(
        payload_semantic_body(payload) == payload_body,
        "PAYLOAD_SEMANTIC_BODY_MISMATCH",
    )
    validate_handoff_payload(payload, policy)
    validate_handoff_accounting(mapping, payload)
    phase3d = _phase3d_validation(payload, mapping, production_path, policy)
    return {"mapping": mapping, "payload": payload, "phase3d_validation": phase3d}


def validate_operational_handoff_inputs(
    *,
    completed_packet_path: str | Path,
    authorization_path: str | Path,
    completion_receipt_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
    repository_root: str | Path,
    additional_completed_artifacts: Mapping[str, str | Path] | None = None,
) -> dict[str, Any]:
    """Validate completed review, authority lineage, and frozen baselines."""
    root = Path(repository_root).resolve()
    run_root = Path(run_root).resolve()
    production_path = Path(production_path).resolve()
    completed_packet_path = Path(completed_packet_path).resolve()
    authorization_path = Path(authorization_path).resolve()
    completion_receipt_path = Path(completion_receipt_path).resolve()
    packet = read_review_packet(completed_packet_path)
    _require(
        packet.get("document_type") == PACKET_DOCUMENT_TYPE,
        "OPERATIONAL_PACKET_DOCUMENT_TYPE_INVALID",
    )
    _require(
        packet.get("schema_version") == PACKET_SCHEMA_VERSION,
        "OPERATIONAL_PACKET_SCHEMA_VERSION_INVALID",
    )
    _require(
        packet["safety"].get("production_apply_authorized") is False
        and packet["safety"].get("production_mutation_permitted") is False,
        "OPERATIONAL_PACKET_PRODUCTION_AUTHORITY_INVALID",
    )
    production = production_identity(production_path)
    baseline = packet.get("production_baseline") or {}
    for field in ("sha256", "schema_version", "schema_sha256", "counts"):
        _require(
            baseline.get(field) == production.get(field),
            "PRODUCTION_BASELINE_MISMATCH",
            field,
        )

    authorization = read_review_packet(authorization_path)
    auth_hash = authorization.get("authorization_semantic_sha256")
    auth_body = {
        key: copy.deepcopy(value)
        for key, value in authorization.items()
        if key != "authorization_semantic_sha256"
    }
    _require(
        auth_hash == canonical_sha256(auth_body),
        "AUTHORIZATION_SEMANTIC_HASH_MISMATCH",
    )
    expected_binding = {
        "packet_id": packet["packet_id"],
        "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "run_id": packet["run"]["run_id"],
        "source_id": packet["source"]["source_id"],
        "source_sha256": packet["source"]["source_sha256"],
    }
    _require(
        authorization.get("packet_binding") == expected_binding,
        "AUTHORIZATION_PACKET_BINDING_MISMATCH",
    )
    _require(
        authorization.get("reviewer") == packet["human_completion"].get("reviewer"),
        "AUTHORIZATION_REVIEWER_MISMATCH",
    )
    auth_safety = authorization.get("safety") or {}
    _require(
        auth_safety.get("production_authorization") is False
        and auth_safety.get("production_apply_authorized") is False,
        "AUTHORIZATION_PRODUCTION_BOUNDARY_INVALID",
    )
    authorization_file_sha256 = sha256_file(authorization_path)

    receipt = read_review_packet(completion_receipt_path)
    _validate_semantic_receipt(receipt)
    for field, expected in (
        ("packet_id", packet["packet_id"]),
        ("run_id", packet["run"]["run_id"]),
        ("source_id", packet["source"]["source_id"]),
        ("source_sha256", packet["source"]["source_sha256"]),
        ("reviewer", packet["human_completion"].get("reviewer")),
        ("authorization_file_sha256", authorization_file_sha256),
        ("authorization_semantic_sha256", auth_hash),
    ):
        _require(receipt.get(field) == expected, "COMPLETION_RECEIPT_MISMATCH", field)
    expanded_packet = _materialize_receipt_authorized_decisions(packet, receipt)
    completion = validate_completed_review_packet(expanded_packet, run_root)
    _require(
        completion["total_operational_decisions_validated"]
        == expanded_packet["summary"]["total_operational_decisions_required"],
        "INCOMPLETE_OPERATIONAL_REVIEW",
    )
    receipt_completion = receipt.get("completion_validation") or {}
    sealed_packet_completion = receipt_completion.get("packet_completion")
    if sealed_packet_completion is None:
        sealed_packet_completion = receipt_completion
    _require(
        sealed_packet_completion == completion,
        "COMPLETION_RECEIPT_MISMATCH",
        "packet_completion",
    )
    auth_artifact = receipt.get("authorization_artifact") or {}
    _require(
        auth_artifact.get("file_sha256") == authorization_file_sha256,
        "COMPLETION_RECEIPT_MISMATCH",
        "authorization_artifact",
    )
    checks = receipt.get("completion_checks") or {}
    _require(checks and all(value is True for value in checks.values()), "INCOMPLETE_COMPLETION_RECEIPT")
    receipt_safety = receipt.get("safety") or {}
    _require(
        receipt_safety.get("production_apply_authorized") is False
        and receipt_safety.get("production_mutation_permitted") is False,
        "COMPLETION_RECEIPT_PRODUCTION_BOUNDARY_INVALID",
    )
    receipt_production = receipt.get("production_before") or {}
    _require(
        receipt_production.get("sha256") == production["sha256"],
        "COMPLETION_RECEIPT_MISMATCH",
        "production_before",
    )

    supplied = {
        role: Path(path).resolve()
        for role, path in (additional_completed_artifacts or {}).items()
    }
    completed_bindings = {
        item.get("role"): item for item in receipt.get("completed_artifacts") or []
    }
    packet_binding = completed_bindings.pop("completed_operational_review_packet", None)
    _require(
        packet_binding is not None
        and packet_binding.get("file_sha256") == sha256_file(completed_packet_path),
        "COMPLETED_PACKET_FILE_HASH_MISMATCH",
    )
    _require(
        set(completed_bindings) == set(supplied),
        "COMPLETION_ARTIFACT_SET_MISMATCH",
    )
    for role, artifact in completed_bindings.items():
        _require(
            supplied[role].is_file()
            and artifact.get("file_sha256") == sha256_file(supplied[role]),
            "COMPLETION_ARTIFACT_HASH_MISMATCH",
            role,
        )

    bundle_path = run_root / "evidence" / "evidence_bound_extraction_bundle.json"
    bundle = read_review_packet(bundle_path)
    bindings = [copy.deepcopy(item) for item in packet["authoritative_inputs"]]
    bindings.extend(
        [
            _binding("completed_operational_review_packet", completed_packet_path, root),
            _binding("human_operational_authorization", authorization_path, root),
            _binding("review_completion_receipt", completion_receipt_path, root),
        ]
    )
    bindings.extend(_binding(role, path, root) for role, path in supplied.items())
    bindings.sort(key=lambda item: (item["role"], item.get("relative_path") or ""))
    return {
        "packet": expanded_packet,
        "completion": completion,
        "completion_receipt": receipt,
        "bundle": bundle,
        "production": production,
        "bindings": bindings,
        "authority": {
            "authority_source": authorization.get("authorization_status")
            or "USER_HUMAN_REVIEW",
            "authorization_file_sha256": authorization_file_sha256,
            "authorization_semantic_sha256": auth_hash,
        },
        "repository_commit": packet["run"]["manifest_repository_commit"],
    }


def build_operational_handoff_artifacts(**kwargs: Any) -> dict[str, dict[str, Any]]:
    """Build deterministic full-operational handoff and qualification artifacts."""
    validated = validate_operational_handoff_inputs(**kwargs)
    core = build_handoff_core(
        packet=validated["packet"],
        completion=validated["completion"],
        completion_receipt=validated["completion_receipt"],
        bundle=validated["bundle"],
        production_path=kwargs["production_path"],
        repository_commit=validated["repository_commit"],
        bindings=validated["bindings"],
        authority=validated["authority"],
        policy=FULL_OPERATIONAL_POLICY,
    )
    mapping = core["mapping"]
    payload = core["payload"]
    phase3d = core["phase3d_validation"]
    validation_receipt = _semantic(
        {
            "document_type": VALIDATION_DOCUMENT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "review_scope": FULL_REVIEW_SCOPE,
            "qualification_only": False,
            "full_operational_review_complete": True,
            "production_authorization": False,
            "production_apply_authorized": False,
            "payload_id": payload["payload_id"],
            "payload_hash": payload["payload_hash"],
            "mapping_id": mapping["mapping_id"],
            "mapping_sha256": mapping["mapping_sha256"],
            "adapter_type": ADAPTER_TYPE,
            "phase3d_validation": phase3d,
            "llm_calls": 0,
        },
        "PHASE3D_VALIDATION",
    )
    mapping_counts = mapping["counts"]
    receipt = _semantic(
        {
            "document_type": RECEIPT_DOCUMENT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "review_scope": FULL_REVIEW_SCOPE,
            "qualification_only": False,
            "full_operational_review_complete": True,
            "production_authorization": False,
            "production_apply_authorized": False,
            "packet_id": validated["packet"]["packet_id"],
            "immutable_packet_sha256": validated["packet"]["immutable_packet_sha256"],
            "completed_packet_sha256": validated["completion"]["completed_packet_sha256"],
            "human_decisions_present": True,
            "decisions_validated": validated["completion"]["total_operational_decisions_validated"],
            "handoff_mapping_id": mapping["mapping_id"],
            "handoff_mapping_sha256": mapping["mapping_sha256"],
            "promotion_payload_id": payload["payload_id"],
            "promotion_payload_sha256": payload["payload_hash"],
            "phase3d_validation_receipt_id": validation_receipt["receipt_id"],
            "phase3d_validation_receipt_sha256": validation_receipt["receipt_sha256"],
            "mapping_counts": mapping_counts,
            "operation_counts": payload["audit"]["operation_counts"],
            "no_silent_loss": True,
            "phase3d_payload_validation": phase3d["payload_validation"],
            "phase3d_preapply_validation": phase3d["preapply_validation"],
            "shadow_apply": phase3d["shadow_apply"],
            "semantic_diff": phase3d["semantic_diff"],
            "idempotent_replay": phase3d["idempotent_replay"],
            "rollback_qualification": phase3d["rollback_qualification"],
            "production_sha256_before": validated["production"]["sha256"],
            "production_sha256_after": phase3d["production_sha256"],
            "production_integrity": phase3d["production_integrity"],
            "production_foreign_key_violations": phase3d[
                "production_foreign_key_violations"
            ],
            "production_changed": False,
            "llm_calls": 0,
        },
        "OPERATIONAL_HANDOFF",
    )
    return {
        "handoff_mapping.json": mapping,
        "promotion_payload.json": payload,
        "phase3d_validation_receipt.json": validation_receipt,
        "operational_handoff_receipt.json": receipt,
    }


def write_operational_handoff_artifacts(
    output_dir: str | Path, **kwargs: Any
) -> dict[str, dict[str, Any]]:
    """Write deterministic LF-only artifacts after all qualification checks pass."""
    artifacts = build_operational_handoff_artifacts(**kwargs)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        content = json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        path = output_dir / name
        if path.exists():
            _require(
                path.read_text(encoding="utf-8") == content,
                "OUTPUT_FILE_EXISTS_WITH_DIFFERENT_CONTENT",
                name,
            )
            continue
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    return artifacts
