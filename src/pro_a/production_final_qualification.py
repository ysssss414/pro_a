from __future__ import annotations

import copy
import json
import os
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from pro_a.production_authorization import (
    EXPECTED_DRAFT_REVIEW_ID,
    EXPECTED_DRAFT_REVIEW_SHA256,
    EXPECTED_PAYLOAD_ID,
    EXPECTED_PAYLOAD_SHA256,
    HUMAN_REVIEW_DOCUMENT_TYPE,
    REVIEW_DOCUMENT_TYPE,
)
from pro_a.production_promotion import (
    AUTHORIZATION_DOCUMENT_TYPE,
    DOCUMENT_TYPE,
    PromotionError,
    apply_payload_to_shadow,
    assert_shadow_target,
    canonical_sha256,
    connect_read_only,
    copy_production_to_shadow,
    database_identity,
    deterministic_id,
    production_identity,
    sha256_file,
    validate_executable_operations,
    validate_payload,
)


PAYLOAD_VERSION = "1"
SOURCE_MATERIALIZATION_DOCUMENT_TYPE = "phase3d3c_source_materialization_final"
QUALIFICATION_DOCUMENT_TYPE = "phase3d3c_final_shadow_qualification_receipt"
MANIFEST_DOCUMENT_TYPE = "phase3d3c_final_qualification_manifest"

EXPECTED_PRODUCTION_SHA256 = "581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250"
EXPECTED_PRODUCTION_SCHEMA_VERSION = "0.2.1"
EXPECTED_PRODUCTION_SCHEMA_SHA256 = "1732ae65db9b56bed1c98a99824ab8e71f9fe65d5fa3cb52eb393f407e107ac2"
EXPECTED_HUMAN_REVIEW_ID = "HUMAN_NODE_REVIEW_169C617EB1D94B70"
EXPECTED_HUMAN_REVIEW_SHA256 = "169c617eb1d94b70dcbfa2d961a33afefff41a7aa703dd7298bcae660a78995b"
EXPECTED_HUMAN_REVIEW_FILE_SHA256 = "1b3e8519bc8b33d836a16755082f83de1fcc200f5b377013220bf45eefe90e29"
EXPECTED_STAGE3D2_KNOWLEDGE_SHA256 = "342bc3fc07755e6abe249fb1470794e7c38082f11155a3395198cffa1af27abc"

EXPECTED_SOURCE_ID = "SRC_20260902_FDA400A0"
EXPECTED_SOURCE_NAME = (
    "20260629-华安证券-聚辰股份（688123.SH）：深耕EEPROM与SPD全球领先，"
    "卡位企业级eSSD和CXL用VPD，构筑新型AI存力优势.pdf"
)
EXPECTED_SOURCE_SIZE = 3261556
EXPECTED_SOURCE_SHA256 = "572a6df2b583358506e2a4fb86359a07e9a1503a3507dcdd2c81a8d97c27e97a"
EXPECTED_ARCHIVE_PATH = f"archive/2026/09/02/{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}"

EXPECTED_DECISION_COUNTS = {"REUSE": 6, "CREATE": 8, "DEFER": 7, "REJECT": 5}
EXPECTED_CREATE_INTENTS = {
    "CAND_NODE_7C4F495527737096": ("VPD芯片", "Product", "NODE_CD91726FADECBD73", ["VPD"]),
    "CAND_NODE_C195F1E21A50449B": ("SPD芯片", "Product", "NODE_B334985DC3F9A431", ["SPD"]),
    "CAND_NODE_B424F90448CCBA4B": ("EEPROM", "Product", "NODE_532F1A9A568EB863", ["EEPROM芯片"]),
    "CAND_NODE_58E875D3AA212A75": ("NOR Flash", "Product", "NODE_15BC05D614287450", ["NOR Flash芯片"]),
    "CAND_NODE_43BE3226A7EACED0": ("CXL内存模组", "Product", "NODE_0C9B7BABEE987AE6", ["CXL内存扩展模组"]),
    "CAND_NODE_9FC88732B95ABA3D": ("DDR5 SPD芯片", "Product", "NODE_36E210971435942C", ["DDR5 SPD"]),
    "CAND_NODE_5542649664C089A4": ("KV Cache", "Technology", "NODE_41CD0139C2DF11FB", ["键值缓存"]),
    "CAND_NODE_60282E35851EA5A9": ("EDSFF", "Standard", "NODE_FD348D13374768DC", ["企业和数据中心SSD外形尺寸"]),
}
EXPECTED_REUSE_INTENTS = {
    "CAND_NODE_26ED2DBD6A1442FC": ("PCI Express", "Standard", "NODE_20260817_10A98F3C"),
    "CAND_NODE_9D7AECC7ACD45CE2": ("Compute Express Link", "Standard", "NODE_20260817_7C89CC59"),
    "CAND_NODE_E72587262796D0F0": ("High Bandwidth Memory", "Product", "NODE_20260817_6A9A657D"),
    "CAND_NODE_B2346267C09BD58B": ("AI Server", "Product", "NODE_20260817_DB4961DB"),
    "CAND_NODE_2778934D77829E1F": ("AI Data Center", "Product", "NODE_20260817_23BDA593"),
    "CAND_NODE_F63C2FAB3DAF2CA5": ("Enterprise SSD", "Product", "NODE_20260817_BEBBBC45"),
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PromotionError(code)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _paths_equivalent(first: Path, second: Path) -> bool:
    first = Path(first)
    second = Path(second)
    if first.resolve() == second.resolve():
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError:
        return False


def _is_within(path: Path, root: Path) -> bool:
    path = Path(path).resolve()
    root = Path(root).resolve()
    return path == root or root in path.parents


def _io_path(path: Path) -> Path:
    """Use Windows extended paths for the required long archive filename."""
    path = Path(path)
    value = str(path)
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return path
    if value.startswith("\\\\"):
        return Path(f"\\\\?\\UNC\\{value[2:]}")
    return Path(f"\\\\?\\{value}")


def _safe_relative_path(value: str) -> Path:
    relative = Path(value)
    _require(value == EXPECTED_ARCHIVE_PATH, "SOURCE_ARCHIVE_PATH_MISMATCH")
    _require(not relative.is_absolute() and ".." not in relative.parts, "SOURCE_ARCHIVE_PATH_UNSAFE")
    return relative


def _stage3d2_knowledge_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sources": copy.deepcopy(payload.get("sources") or []),
        "evidence": copy.deepcopy(payload.get("evidence") or []),
        "claims": copy.deepcopy(payload.get("claims") or []),
        "knowledge_mutations": [
            copy.deepcopy(mutation)
            for mutation in payload.get("intended_mutations") or []
            if mutation.get("table") in {"sources", "claims"}
        ],
    }


def validate_human_review(review: Mapping[str, Any], *, file_sha256: str) -> None:
    _require(review.get("document_type") == HUMAN_REVIEW_DOCUMENT_TYPE, "HUMAN_REVIEW_DOCUMENT_TYPE_MISMATCH")
    _require(review.get("review_status") == "HUMAN_REVIEW_COMPLETE", "HUMAN_REVIEW_NOT_COMPLETE")
    _require(review.get("human_review_id") == EXPECTED_HUMAN_REVIEW_ID, "HUMAN_REVIEW_ID_MISMATCH")
    _require(review.get("human_review_sha256") == EXPECTED_HUMAN_REVIEW_SHA256, "HUMAN_REVIEW_SHA_MISMATCH")
    _require(file_sha256 == EXPECTED_HUMAN_REVIEW_FILE_SHA256, "HUMAN_REVIEW_FILE_SHA_MISMATCH")
    _require(review.get("operation_counts") == EXPECTED_DECISION_COUNTS, "HUMAN_REVIEW_COUNTS_MISMATCH")
    authority = review.get("decision_authority") or {}
    _require(authority.get("authority") == "USER_HUMAN_REVIEW", "HUMAN_REVIEW_AUTHORITY_MISMATCH")
    _require(authority.get("llm_authorization_used") is False, "LLM_AUTHORIZATION_FORBIDDEN")

    records = review.get("records") or []
    by_id = {record.get("operation_candidate_id"): record for record in records}
    _require(len(records) == len(by_id) == 26, "HUMAN_REVIEW_UNIVERSE_MISMATCH")
    counts = Counter(record.get("human_decision") for record in records)
    _require({key: counts.get(key, 0) for key in EXPECTED_DECISION_COUNTS} == EXPECTED_DECISION_COUNTS, "HUMAN_REVIEW_RECORD_COUNTS_MISMATCH")
    for candidate_id, (name, primary_type, node_id, aliases) in EXPECTED_CREATE_INTENTS.items():
        record = by_id.get(candidate_id) or {}
        intent = record.get("reviewed_identity_intent") or {}
        _require(record.get("human_decision") == "CREATE", f"CREATE_DECISION_MISMATCH:{candidate_id}")
        _require(record.get("proposed_name") == name and record.get("proposed_type") == primary_type, f"CREATE_IDENTITY_MISMATCH:{candidate_id}")
        _require(intent.get("canonical_name") == name and intent.get("primary_type") == primary_type, f"CREATE_INTENT_MISMATCH:{candidate_id}")
        _require(intent.get("prospective_node_id") == node_id, f"CREATE_NODE_ID_MISMATCH:{candidate_id}")
        _require(intent.get("aliases") == aliases, f"CREATE_ALIAS_INTENT_MISMATCH:{candidate_id}")
    for candidate_id, (name, primary_type, target_id) in EXPECTED_REUSE_INTENTS.items():
        record = by_id.get(candidate_id) or {}
        intent = record.get("reviewed_identity_intent") or {}
        _require(record.get("human_decision") == "REUSE", f"REUSE_DECISION_MISMATCH:{candidate_id}")
        _require(record.get("proposed_name") == name and record.get("proposed_type") == primary_type, f"REUSE_IDENTITY_MISMATCH:{candidate_id}")
        _require(record.get("target_node_id") == target_id, f"HUMAN_REUSE_TARGET_MISMATCH:{candidate_id}")
        _require(intent.get("target_node_id") == target_id, f"HUMAN_REUSE_INTENT_MISMATCH:{candidate_id}")
        _require(intent.get("target_canonical_name") == name and intent.get("target_primary_type") == primary_type, f"HUMAN_REUSE_TARGET_IDENTITY_MISMATCH:{candidate_id}")
    _require(all(record.get("decision_authority") == "USER_HUMAN_REVIEW" for record in records), "RECORD_AUTHORITY_MISMATCH")
    _require(all(record.get("executable") is False for record in records), "HUMAN_REVIEW_ARTIFACT_MUST_BE_NONEXECUTABLE")
    preserved = review.get("preserved_inventory") or {}
    _require(preserved.get("prior_node_reject") == 32, "PRIOR_NODE_REJECT_INVENTORY_MISMATCH")
    _require(preserved.get("table_ineligible_claims_excluded") == 3, "TABLE_INELIGIBLE_INVENTORY_MISMATCH")
    _require(preserved.get("relation_reject") == 10, "RELATION_REJECT_INVENTORY_MISMATCH")
    _require(preserved.get("relation_review_reopened") is False, "RELATION_REVIEW_REOPENED")

    body = {key: copy.deepcopy(value) for key, value in review.items() if key not in {"human_review_id", "human_review_sha256"}}
    _require(canonical_sha256(body) == EXPECTED_HUMAN_REVIEW_SHA256, "HUMAN_REVIEW_SEMANTIC_HASH_MISMATCH")


def freeze_source_package(
    source_path: Path,
    package_path: Path,
    *,
    production_root: Path,
    logical_destination: str = EXPECTED_ARCHIVE_PATH,
) -> dict[str, Any]:
    """Freeze exact Source bytes outside the real Production archive."""
    source_path = Path(source_path).resolve()
    package_path = Path(package_path).resolve()
    production_root = Path(production_root).resolve()
    relative = _safe_relative_path(logical_destination)
    real_destination = (production_root / relative).resolve()
    real_archive_root = (production_root / relative.parts[0]).resolve()
    source_io = _io_path(source_path)
    package_io = _io_path(package_path)
    real_destination_io = _io_path(real_destination)
    _require(source_io.is_file(), "SOURCE_FILE_MISSING")
    _require(source_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SOURCE_SIZE_MISMATCH")
    source_sha = sha256_file(source_io)
    _require(source_sha == EXPECTED_SOURCE_SHA256, "SOURCE_SHA_MISMATCH")
    _require(not _paths_equivalent(package_path, real_destination), "PRODUCTION_ARCHIVE_WRITE_BLOCKED")
    _require(not _is_within(package_path, real_archive_root), "PRODUCTION_ARCHIVE_WRITE_BLOCKED")
    _require(not real_destination_io.exists(), "PRODUCTION_ARCHIVE_COLLISION")
    collisions = list(real_destination.parent.glob(f"{EXPECTED_SOURCE_ID}__*")) if real_destination.parent.exists() else []
    _require(not collisions, "PRODUCTION_ARCHIVE_SOURCE_ID_COLLISION")

    status = "FROZEN"
    if package_io.exists():
        _require(package_io.is_file(), "SOURCE_PACKAGE_PATH_NOT_FILE")
        _require(package_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SOURCE_PACKAGE_CONFLICT")
        _require(sha256_file(package_io) == EXPECTED_SOURCE_SHA256, "SOURCE_PACKAGE_CONFLICT")
        status = "ALREADY_FROZEN"
    else:
        package_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_io, package_io)
    package_sha = sha256_file(package_io)
    _require(package_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SOURCE_PACKAGE_SIZE_MISMATCH")
    _require(package_sha == source_sha == EXPECTED_SOURCE_SHA256, "SOURCE_PACKAGE_SHA_MISMATCH")
    return {
        "document_type": SOURCE_MATERIALIZATION_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "SOURCE_PACKAGE_FROZEN",
        "source": {
            "source_id": EXPECTED_SOURCE_ID,
            "original_name": EXPECTED_SOURCE_NAME,
            "original_recovery_path": str(source_path),
            "original_size": EXPECTED_SOURCE_SIZE,
            "original_sha256": source_sha,
        },
        "package": {
            "path": str(package_path),
            "relative_path": f"source/{package_path.name}",
            "size": package_io.stat().st_size,
            "sha256": package_sha,
            "status": status,
        },
        "production_archive": {
            "logical_destination": logical_destination,
            "resolved_destination": str(real_destination),
            "destination_exists": False,
            "source_id_prefix_collision_count": 0,
            "copy_performed": False,
        },
        "flags": {
            "source_package_frozen": True,
            "source_sha_match": True,
            "source_archive_materialization_qualified": False,
            "production_changed": False,
            "production_apply_attempted": False,
            "production_apply_authorized": False,
        },
    }


def _build_node_operations(human_review: Mapping[str, Any], frozen_timestamp: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for record in human_review["records"]:
        candidate_id = record["operation_candidate_id"]
        decision = record["human_decision"]
        operation_id = deterministic_id("OP_NODE", {
            "candidate_id": candidate_id,
            "decision": decision,
            "human_review_sha256": EXPECTED_HUMAN_REVIEW_SHA256,
        })
        base = {
            "operation_id": operation_id,
            "candidate_id": candidate_id,
            "operation": decision,
            "candidate": {
                "canonical_name": record["proposed_name"],
                "primary_type": record["proposed_type"],
            },
            "claim_refs": copy.deepcopy(record.get("supporting_claim_ids") or []),
            "review_decision": "USER_HUMAN_REVIEW",
            "review_reason": record["human_decision_reason"],
        }
        if decision == "CREATE":
            intent = record["reviewed_identity_intent"]
            base.update({
                "executable": True,
                "aliases": copy.deepcopy(intent["aliases"]),
                "final_node": {
                    "node_id": intent["prospective_node_id"],
                    "canonical_name": intent["canonical_name"],
                    "primary_type": intent["primary_type"],
                    "description": "",
                    "status": "active",
                    "created_at": frozen_timestamp,
                    "updated_at": frozen_timestamp,
                },
            })
        elif decision == "REUSE":
            intent = record["reviewed_identity_intent"]
            base.update({
                "executable": True,
                "resolved_target_id": intent["target_node_id"],
                "resolution": {"term": intent["target_canonical_name"], "method": "EXACT_UNIQUE_CURRENT_PRODUCTION"},
                "expected_target": {
                    "node_id": intent["target_node_id"],
                    "canonical_name": intent["target_canonical_name"],
                    "primary_type": intent["target_primary_type"],
                    "status": intent["target_status"],
                },
                "approved_aliases": [],
            })
        else:
            base.update({"executable": False, "execution_state": "AUDIT_ONLY_NONEXECUTABLE"})
        result.append(base)
    return result


def _build_node_mutations(node_operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for operation in node_operations:
        if operation["operation"] != "CREATE":
            continue
        node = operation["final_node"]
        result.append({
            "mutation_id": deterministic_id("MUT", {"table": "nodes", "key": node["node_id"], "row": node}),
            "table": "nodes",
            "operation": "INSERT",
            "key": {"node_id": node["node_id"]},
            "row": copy.deepcopy(node),
            "authorized_by": operation["operation_id"],
        })
        for alias in operation["aliases"]:
            row = {"alias": alias, "node_id": node["node_id"]}
            result.append({
                "mutation_id": deterministic_id("MUT", {"table": "node_aliases", "key": alias, "row": row}),
                "table": "node_aliases",
                "operation": "INSERT",
                "key": {"alias": alias},
                "row": row,
                "authorized_by": operation["operation_id"],
            })
    return result


def build_authorization_bound_payload(
    *,
    qualification_payload: Mapping[str, Any],
    draft_review: Mapping[str, Any],
    human_review: Mapping[str, Any],
    human_review_file_sha256: str,
    source_materialization: Mapping[str, Any],
    production: Mapping[str, Any],
    repository_commit: str,
    source_recovery_receipt_sha256: str,
) -> dict[str, Any]:
    validate_payload(qualification_payload)
    _require(qualification_payload.get("document_type") == DOCUMENT_TYPE, "QUALIFICATION_PAYLOAD_DOCUMENT_TYPE_MISMATCH")
    _require(qualification_payload.get("payload_id") == EXPECTED_PAYLOAD_ID, "QUALIFICATION_PAYLOAD_ID_MISMATCH")
    _require(qualification_payload.get("payload_hash") == EXPECTED_PAYLOAD_SHA256, "QUALIFICATION_PAYLOAD_SHA_MISMATCH")
    _require(canonical_sha256(_stage3d2_knowledge_projection(qualification_payload)) == EXPECTED_STAGE3D2_KNOWLEDGE_SHA256, "QUALIFICATION_KNOWLEDGE_BINDING_MISMATCH")
    _require(draft_review.get("document_type") == REVIEW_DOCUMENT_TYPE, "DRAFT_REVIEW_DOCUMENT_TYPE_MISMATCH")
    _require(draft_review.get("review_id") == EXPECTED_DRAFT_REVIEW_ID, "DRAFT_REVIEW_ID_MISMATCH")
    _require(draft_review.get("review_sha256") == EXPECTED_DRAFT_REVIEW_SHA256, "DRAFT_REVIEW_SHA_MISMATCH")
    validate_human_review(human_review, file_sha256=human_review_file_sha256)
    _require(repository_commit, "REPOSITORY_COMMIT_MISSING")
    _require(source_recovery_receipt_sha256, "SOURCE_RECOVERY_RECEIPT_SHA_MISSING")
    _require(source_materialization.get("document_type") == SOURCE_MATERIALIZATION_DOCUMENT_TYPE, "SOURCE_MATERIALIZATION_DOCUMENT_TYPE_MISMATCH")
    _require(source_materialization.get("status") == "SOURCE_PACKAGE_FROZEN", "SOURCE_PACKAGE_NOT_FROZEN")
    source = source_materialization.get("source") or {}
    package = source_materialization.get("package") or {}
    archive = source_materialization.get("production_archive") or {}
    _require(source.get("source_id") == EXPECTED_SOURCE_ID, "SOURCE_ID_MISMATCH")
    _require(source.get("original_name") == EXPECTED_SOURCE_NAME, "SOURCE_NAME_MISMATCH")
    _require(source.get("original_sha256") == package.get("sha256") == EXPECTED_SOURCE_SHA256, "SOURCE_BINDING_SHA_MISMATCH")
    _require(source.get("original_size") == package.get("size") == EXPECTED_SOURCE_SIZE, "SOURCE_BINDING_SIZE_MISMATCH")
    _require(archive.get("logical_destination") == EXPECTED_ARCHIVE_PATH, "SOURCE_ARCHIVE_PATH_MISMATCH")
    _require(archive.get("destination_exists") is False and archive.get("source_id_prefix_collision_count") == 0, "SOURCE_ARCHIVE_COLLISION")

    _require(production.get("sha256") == EXPECTED_PRODUCTION_SHA256, "PRODUCTION_BASELINE_DRIFT")
    _require(production.get("schema_version") == EXPECTED_PRODUCTION_SCHEMA_VERSION, "PRODUCTION_SCHEMA_VERSION_DRIFT")
    _require(production.get("schema_sha256") == EXPECTED_PRODUCTION_SCHEMA_SHA256, "PRODUCTION_SCHEMA_DRIFT")
    for binding in (qualification_payload.get("metadata") or {}, human_review.get("production_baseline") or {}):
        _require(binding.get("production_sha256", binding.get("sha256")) == production["sha256"], "PRODUCTION_BINDING_SHA_MISMATCH")
        _require(binding.get("production_schema_sha256", binding.get("schema_sha256")) == production["schema_sha256"], "PRODUCTION_BINDING_SCHEMA_MISMATCH")
        _require(binding.get("production_counts", binding.get("counts")) == production["counts"], "PRODUCTION_BINDING_COUNTS_MISMATCH")

    frozen_timestamp = qualification_payload["metadata"]["frozen_timestamp"]
    node_operations = _build_node_operations(human_review, frozen_timestamp)
    relation_operations = copy.deepcopy(qualification_payload["relation_operations"])
    knowledge_mutations = copy.deepcopy(_stage3d2_knowledge_projection(qualification_payload)["knowledge_mutations"])
    node_mutations = _build_node_mutations(node_operations)
    intended_mutations = knowledge_mutations + node_mutations
    excluded_claims = [
        copy.deepcopy(item)
        for item in qualification_payload["excluded_operations"]
        if item.get("object_type") == "Claim"
    ]
    excluded_operations = excluded_claims + [
        {"object_type": "Node", **copy.deepcopy(operation)}
        for operation in node_operations
        if not operation["executable"]
    ] + [
        {"object_type": "Relation", **copy.deepcopy(operation)}
        for operation in relation_operations
    ]
    prior_rejections = [
        {
            "operation_id": item["operation_id"],
            "candidate_id": item["candidate_id"],
            "reason": item["reason"],
        }
        for item in qualification_payload["node_operations"]
        if item["operation"] == "REJECT"
    ]
    phase3c_hashes = copy.deepcopy(qualification_payload["metadata"]["input_artifact_roles_and_sha256"])
    body = {
        "document_type": AUTHORIZATION_DOCUMENT_TYPE,
        "payload_version": PAYLOAD_VERSION,
        "metadata": {
            "source_run_id": qualification_payload["metadata"]["source_run_id"],
            "repository_commit": repository_commit,
            "production_sha256": production["sha256"],
            "production_schema_version": production["schema_version"],
            "production_schema_sha256": production["schema_sha256"],
            "production_counts": copy.deepcopy(production["counts"]),
            "source_id": EXPECTED_SOURCE_ID,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "source_package_sha256": package["sha256"],
            "source_recovery_receipt_sha256": source_recovery_receipt_sha256,
            "phase3c_artifact_roles_and_sha256": phase3c_hashes,
            "input_artifact_roles_and_sha256": [
                *phase3c_hashes,
                {"role": "stage3d2_qualification_payload", "sha256": EXPECTED_PAYLOAD_SHA256},
                {"role": "stage3d3a_review_universe", "sha256": EXPECTED_DRAFT_REVIEW_SHA256},
                {"role": "stage3d3b_human_review", "sha256": EXPECTED_HUMAN_REVIEW_SHA256},
                {"role": "stage3d3b_human_review_file", "sha256": human_review_file_sha256},
                {"role": "frozen_source_package", "sha256": package["sha256"]},
            ],
            "stage3d2_qualification": {"payload_id": EXPECTED_PAYLOAD_ID, "payload_sha256": EXPECTED_PAYLOAD_SHA256},
            "stage3d3a_review": {"review_id": EXPECTED_DRAFT_REVIEW_ID, "review_sha256": EXPECTED_DRAFT_REVIEW_SHA256},
            "stage3d3b_human_review": {
                "human_review_id": EXPECTED_HUMAN_REVIEW_ID,
                "human_review_sha256": EXPECTED_HUMAN_REVIEW_SHA256,
                "human_review_file_sha256": human_review_file_sha256,
            },
            "frozen_timestamp": frozen_timestamp,
        },
        "source_materialization": {
            "source_id": EXPECTED_SOURCE_ID,
            "original_name": EXPECTED_SOURCE_NAME,
            "size": EXPECTED_SOURCE_SIZE,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "package_relative_path": package["relative_path"],
            "package_sha256": package["sha256"],
            "archive_logical_destination": EXPECTED_ARCHIVE_PATH,
            "production_archive_collision_status": "ABSENT",
            "production_archive_copy_authorized": False,
        },
        "sources": copy.deepcopy(qualification_payload["sources"]),
        "evidence": copy.deepcopy(qualification_payload["evidence"]),
        "claims": copy.deepcopy(qualification_payload["claims"]),
        "node_operations": node_operations,
        "relation_operations": relation_operations,
        "excluded_operations": excluded_operations,
        "intended_mutations": intended_mutations,
        "human_authorization": {
            "human_review_id": EXPECTED_HUMAN_REVIEW_ID,
            "human_review_sha256": EXPECTED_HUMAN_REVIEW_SHA256,
            "human_review_file_sha256": human_review_file_sha256,
            "decision_authority": "USER_HUMAN_REVIEW",
            "llm_authorization_used": False,
            "human_review_universe": 26,
            "decision_counts": copy.deepcopy(EXPECTED_DECISION_COUNTS),
            "production_apply_authorized": False,
        },
        "audit": {
            "artifact_convergence": copy.deepcopy(qualification_payload["audit"]["artifact_convergence"]),
            "stage3d2_knowledge_projection_sha256": EXPECTED_STAGE3D2_KNOWLEDGE_SHA256,
            "operation_inventory": {
                "source": {"CREATE": 1},
                "claim": {"CREATE": 104, "REJECT": 3},
                "node": copy.deepcopy(EXPECTED_DECISION_COUNTS),
                "relation": {"CREATE": 0, "REUSE": 0, "DEFER": 0, "REJECT": 10},
                "alias": {"CREATE": 8},
                "claim_node_link": {"CREATE": 0},
                "source_node_link": {"CREATE": 0},
            },
            "link_policy": {
                "claim_node_link_create": 0,
                "source_node_link_create": 0,
                "decision": "NONE",
                "reason": "Supporting Claim IDs are provenance only; no deterministic database-link role is authorized by the bound artifacts.",
            },
            "preserved_pre_review_node_rejections": prior_rejections,
            "preserved_pre_review_node_reject_count": len(prior_rejections),
            "relation_review_reopened": False,
            "reuse_alias_mutations": 0,
            "hard_blocks": [
                "CONFIGURED_PRODUCTION_WRITE",
                "REAL_PRODUCTION_ARCHIVE_WRITE",
                "SCHEMA_MIGRATION",
                "RELATION_MUTATION",
                "IMA",
                "CURRENT_VIEW",
                "PROPOSAL_PROPAGATION",
                "LLM_DURING_APPLY",
            ],
        },
        "qualified_execution_target": "SHADOW_ONLY",
        "production_apply_authorized": False,
    }
    digest = canonical_sha256(body)
    payload = {
        "document_type": body["document_type"],
        "payload_version": body["payload_version"],
        "payload_id": f"PROMO_{digest[:16].upper()}",
        "payload_hash": digest,
        **{key: value for key, value in body.items() if key not in {"document_type", "payload_version"}},
    }
    validate_final_payload(payload)
    return payload


def final_payload_semantic_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in payload.items() if key not in {"payload_id", "payload_hash"}}


def validate_final_payload(payload: Mapping[str, Any]) -> None:
    validate_payload(payload)
    _require(payload.get("document_type") == AUTHORIZATION_DOCUMENT_TYPE, "FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH")
    _require(payload.get("payload_version") == PAYLOAD_VERSION, "FINAL_PAYLOAD_VERSION_MISMATCH")
    digest = canonical_sha256(final_payload_semantic_body(payload))
    _require(payload.get("payload_hash") == digest, "FINAL_PAYLOAD_HASH_MISMATCH")
    _require(payload.get("payload_id") == f"PROMO_{digest[:16].upper()}", "FINAL_PAYLOAD_ID_MISMATCH")
    metadata = payload.get("metadata") or {}
    _require(metadata.get("production_sha256") == EXPECTED_PRODUCTION_SHA256, "FINAL_PRODUCTION_SHA_BINDING_MISMATCH")
    _require(metadata.get("production_schema_version") == EXPECTED_PRODUCTION_SCHEMA_VERSION, "FINAL_SCHEMA_VERSION_BINDING_MISMATCH")
    _require(metadata.get("production_schema_sha256") == EXPECTED_PRODUCTION_SCHEMA_SHA256, "FINAL_SCHEMA_SHA_BINDING_MISMATCH")
    _require(metadata.get("source_id") == EXPECTED_SOURCE_ID, "FINAL_SOURCE_ID_BINDING_MISMATCH")
    _require(metadata.get("source_sha256") == metadata.get("source_package_sha256") == EXPECTED_SOURCE_SHA256, "FINAL_SOURCE_SHA_BINDING_MISMATCH")
    _require((metadata.get("stage3d2_qualification") or {}) == {"payload_id": EXPECTED_PAYLOAD_ID, "payload_sha256": EXPECTED_PAYLOAD_SHA256}, "FINAL_STAGE3D2_BINDING_MISMATCH")
    _require((metadata.get("stage3d3a_review") or {}) == {"review_id": EXPECTED_DRAFT_REVIEW_ID, "review_sha256": EXPECTED_DRAFT_REVIEW_SHA256}, "FINAL_STAGE3D3A_BINDING_MISMATCH")
    human = payload.get("human_authorization") or {}
    _require(human.get("human_review_id") == EXPECTED_HUMAN_REVIEW_ID, "FINAL_HUMAN_REVIEW_ID_MISMATCH")
    _require(human.get("human_review_sha256") == EXPECTED_HUMAN_REVIEW_SHA256, "FINAL_HUMAN_REVIEW_SHA_MISMATCH")
    _require(human.get("human_review_file_sha256") == EXPECTED_HUMAN_REVIEW_FILE_SHA256, "FINAL_HUMAN_REVIEW_FILE_SHA_MISMATCH")
    _require(human.get("decision_authority") == "USER_HUMAN_REVIEW", "FINAL_HUMAN_AUTHORITY_MISMATCH")
    _require(human.get("llm_authorization_used") is False, "FINAL_LLM_AUTHORIZATION_FORBIDDEN")
    _require(human.get("human_review_universe") == 26 and human.get("decision_counts") == EXPECTED_DECISION_COUNTS, "FINAL_HUMAN_REVIEW_UNIVERSE_MISMATCH")
    _require(human.get("production_apply_authorized") is False, "FINAL_PRODUCTION_AUTHORIZATION_FORBIDDEN")
    _require(payload.get("production_apply_authorized") is False, "FINAL_PRODUCTION_AUTHORIZATION_FORBIDDEN")
    _require(payload.get("qualified_execution_target") == "SHADOW_ONLY", "FINAL_EXECUTION_TARGET_INVALID")

    source = payload.get("source_materialization") or {}
    _require(source.get("source_id") == EXPECTED_SOURCE_ID, "FINAL_SOURCE_ID_MISMATCH")
    _require(source.get("original_name") == EXPECTED_SOURCE_NAME, "FINAL_SOURCE_NAME_MISMATCH")
    _require(source.get("size") == EXPECTED_SOURCE_SIZE, "FINAL_SOURCE_SIZE_MISMATCH")
    _require(source.get("source_sha256") == source.get("package_sha256") == EXPECTED_SOURCE_SHA256, "FINAL_SOURCE_PACKAGE_SHA_MISMATCH")
    _require(source.get("archive_logical_destination") == EXPECTED_ARCHIVE_PATH, "FINAL_ARCHIVE_PATH_MISMATCH")
    _require(source.get("production_archive_copy_authorized") is False, "REAL_ARCHIVE_COPY_AUTHORIZED")

    knowledge = _stage3d2_knowledge_projection(payload)
    _require(canonical_sha256(knowledge) == EXPECTED_STAGE3D2_KNOWLEDGE_SHA256, "FINAL_KNOWLEDGE_BINDING_MISMATCH")
    claims = payload.get("claims") or []
    _require(len(claims) == 107, "FINAL_RAW_CLAIM_COUNT_MISMATCH")
    _require(sum(bool(claim.get("executable")) for claim in claims) == 104, "FINAL_EXECUTABLE_CLAIM_COUNT_MISMATCH")
    _require(sum(not bool(claim.get("executable")) for claim in claims) == 3, "FINAL_EXCLUDED_CLAIM_COUNT_MISMATCH")

    node_operations = payload.get("node_operations") or []
    node_counts = Counter(operation.get("operation") for operation in node_operations)
    _require({key: node_counts.get(key, 0) for key in EXPECTED_DECISION_COUNTS} == EXPECTED_DECISION_COUNTS, "FINAL_NODE_OPERATION_COUNTS_MISMATCH")
    by_id = {operation.get("candidate_id"): operation for operation in node_operations}
    _require(len(by_id) == len(node_operations) == 26, "FINAL_NODE_OPERATION_UNIVERSE_MISMATCH")
    for candidate_id, (name, primary_type, node_id, aliases) in EXPECTED_CREATE_INTENTS.items():
        operation = by_id.get(candidate_id) or {}
        node = operation.get("final_node") or {}
        _require(operation.get("operation") == "CREATE" and operation.get("executable") is True, f"FINAL_CREATE_NOT_EXECUTABLE:{candidate_id}")
        _require((node.get("canonical_name"), node.get("primary_type"), node.get("node_id")) == (name, primary_type, node_id), f"FINAL_CREATE_IDENTITY_MISMATCH:{candidate_id}")
        _require(operation.get("aliases") == aliases, f"FINAL_CREATE_ALIASES_MISMATCH:{candidate_id}")
    for candidate_id, (name, primary_type, target_id) in EXPECTED_REUSE_INTENTS.items():
        operation = by_id.get(candidate_id) or {}
        expected = operation.get("expected_target") or {}
        _require(operation.get("operation") == "REUSE" and operation.get("executable") is True, f"FINAL_REUSE_NOT_EXECUTABLE:{candidate_id}")
        _require(operation.get("resolved_target_id") == target_id, f"FINAL_REUSE_TARGET_MISMATCH:{candidate_id}")
        _require((expected.get("canonical_name"), expected.get("primary_type"), expected.get("node_id")) == (name, primary_type, target_id), f"FINAL_REUSE_IDENTITY_MISMATCH:{candidate_id}")
        _require(operation.get("approved_aliases") == [], f"FINAL_REUSE_ALIAS_MUTATION_FORBIDDEN:{candidate_id}")
    _require(all(not operation.get("executable") for operation in node_operations if operation.get("operation") in {"DEFER", "REJECT"}), "FINAL_AUDIT_NODE_EXECUTABLE")

    relations = payload.get("relation_operations") or []
    _require(len(relations) == 10, "FINAL_RELATION_COUNT_MISMATCH")
    _require(all(operation.get("operation") == "REJECT" and not operation.get("executable") for operation in relations), "FINAL_RELATION_EXECUTABLE")
    mutations = payload.get("intended_mutations") or []
    mutation_counts = Counter(mutation.get("table") for mutation in mutations)
    _require(mutation_counts == Counter({"sources": 1, "claims": 104, "nodes": 8, "node_aliases": 8}), "FINAL_MUTATION_INVENTORY_MISMATCH")
    mutation_authorities = {mutation.get("authorized_by") for mutation in mutations}
    _require(not any(operation["operation_id"] in mutation_authorities for operation in node_operations if operation["operation"] in {"DEFER", "REJECT"}), "AUDIT_ONLY_NODE_HAS_MUTATION")
    _require(not any(operation["operation_id"] in mutation_authorities for operation in relations), "RELATION_HAS_MUTATION")
    _require("CMM-D" not in {mutation["row"].get("alias") for mutation in mutations if mutation["table"] == "node_aliases"}, "CMM_D_ALIAS_FORBIDDEN")
    audit = payload.get("audit") or {}
    _require(audit.get("reuse_alias_mutations") == 0, "REUSE_ALIAS_MUTATIONS_FORBIDDEN")
    _require((audit.get("link_policy") or {}).get("claim_node_link_create") == 0, "CLAIM_NODE_LINK_NOT_AUTHORIZED")
    _require((audit.get("link_policy") or {}).get("source_node_link_create") == 0, "SOURCE_NODE_LINK_NOT_AUTHORIZED")
    _require(audit.get("preserved_pre_review_node_reject_count") == 32, "PRIOR_NODE_REJECTIONS_NOT_PRESERVED")


def _archive_collision_state(production_root: Path, logical_destination: str) -> dict[str, Any]:
    relative = _safe_relative_path(logical_destination)
    destination = (Path(production_root).resolve() / relative).resolve()
    collisions = list(destination.parent.glob(f"{EXPECTED_SOURCE_ID}__*")) if destination.parent.exists() else []
    return {
        "destination": str(destination),
        "destination_exists": _io_path(destination).exists(),
        "source_id_prefix_collisions": sorted(str(path.resolve()) for path in collisions),
    }


def preflight_final_payload(
    payload: Mapping[str, Any],
    *,
    production_path: Path,
    source_package_path: Path,
    production_root: Path,
) -> dict[str, Any]:
    validate_final_payload(payload)
    production = production_identity(production_path)
    _require(production["sha256"] == EXPECTED_PRODUCTION_SHA256, "PRODUCTION_BASELINE_DRIFT")
    _require(production["schema_version"] == EXPECTED_PRODUCTION_SCHEMA_VERSION, "PRODUCTION_SCHEMA_VERSION_DRIFT")
    _require(production["schema_sha256"] == EXPECTED_PRODUCTION_SCHEMA_SHA256, "PRODUCTION_SCHEMA_DRIFT")
    _require(production["counts"] == payload["metadata"]["production_counts"], "PRODUCTION_COUNTS_DRIFT")
    source_package_path = Path(source_package_path).resolve()
    source_package_io = _io_path(source_package_path)
    _require(source_package_io.is_file(), "SOURCE_PACKAGE_MISSING")
    _require(source_package_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SOURCE_PACKAGE_SIZE_MISMATCH")
    _require(sha256_file(source_package_io) == EXPECTED_SOURCE_SHA256, "SOURCE_PACKAGE_SHA_MISMATCH")
    archive = _archive_collision_state(production_root, EXPECTED_ARCHIVE_PATH)
    _require(not archive["destination_exists"], "PRODUCTION_ARCHIVE_COLLISION")
    _require(not archive["source_id_prefix_collisions"], "PRODUCTION_ARCHIVE_SOURCE_ID_COLLISION")

    connection = connect_read_only(production_path)
    try:
        source_id_count = connection.execute("SELECT COUNT(*) FROM sources WHERE source_id=?", (EXPECTED_SOURCE_ID,)).fetchone()[0]
        source_sha_rows = connection.execute("SELECT source_id FROM sources WHERE sha256=?", (EXPECTED_SOURCE_SHA256,)).fetchall()
        _require(source_id_count == 0, "SOURCE_ID_ALREADY_EXISTS")
        _require(not source_sha_rows, "SOURCE_SHA_ALREADY_EXISTS")
        claim_ids = [claim["claim_id"] for claim in payload["claims"] if claim["executable"]]
        placeholders = ",".join("?" for _ in claim_ids)
        existing_claims = connection.execute(f"SELECT claim_id FROM claims WHERE claim_id IN ({placeholders})", claim_ids).fetchall()
        _require(not existing_claims, "CLAIM_ID_ALREADY_EXISTS")
        validate_executable_operations(connection, payload)
    finally:
        connection.close()
    return {
        "status": "PASS",
        "production": {
            "sha256": production["sha256"],
            "schema_version": production["schema_version"],
            "schema_sha256": production["schema_sha256"],
            "counts": production["counts"],
            "integrity": production["integrity"],
            "foreign_key_violations": production["foreign_key_violations"],
            "sidecars": production["sidecars"],
        },
        "source": {
            "source_id_absent": True,
            "source_sha_absent": True,
            "package_sha256": EXPECTED_SOURCE_SHA256,
            "archive_collision": archive,
        },
        "claims": {"executable": 104, "table_ineligible_excluded": 3, "id_conflicts": 0},
        "nodes": {"create": 8, "reuse": 6, "defer": 7, "reject": 5},
        "relations": {"executable": 0, "reject": 10},
    }


def filesystem_inventory(root: Path) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    if not root.exists():
        return []
    files = []
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        path_io = _io_path(path)
        if path_io.is_file():
            files.append({
                "path": path.relative_to(root).as_posix(),
                "size": path_io.stat().st_size,
                "sha256": sha256_file(path_io),
            })
    return files


def materialize_source_to_shadow(
    payload: Mapping[str, Any],
    *,
    source_package_path: Path,
    shadow_filesystem_root: Path,
    production_root: Path,
    inject_failure: bool = False,
) -> dict[str, Any]:
    validate_final_payload(payload)
    source_package_path = Path(source_package_path).resolve()
    shadow_filesystem_root = Path(shadow_filesystem_root).resolve()
    production_root = Path(production_root).resolve()
    relative = _safe_relative_path(payload["source_materialization"]["archive_logical_destination"])
    destination = (shadow_filesystem_root / relative).resolve()
    real_destination = (production_root / relative).resolve()
    _require(_is_within(destination, shadow_filesystem_root), "SHADOW_ARCHIVE_DESTINATION_OUTSIDE_ROOT")
    _require(not _paths_equivalent(destination, real_destination), "PRODUCTION_ARCHIVE_WRITE_BLOCKED")
    _require(not _is_within(destination, (production_root / relative.parts[0]).resolve()), "PRODUCTION_ARCHIVE_WRITE_BLOCKED")
    source_package_io = _io_path(source_package_path)
    _require(source_package_io.is_file(), "SOURCE_PACKAGE_MISSING")
    _require(source_package_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SOURCE_PACKAGE_SIZE_MISMATCH")
    _require(sha256_file(source_package_io) == EXPECTED_SOURCE_SHA256, "SOURCE_PACKAGE_SHA_MISMATCH")
    destination_io = _io_path(destination)
    if destination_io.exists():
        _require(destination_io.is_file(), "SHADOW_ARCHIVE_DESTINATION_NOT_FILE")
        _require(destination_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SHADOW_ARCHIVE_REPLAY_CONFLICT")
        _require(sha256_file(destination_io) == EXPECTED_SOURCE_SHA256, "SHADOW_ARCHIVE_REPLAY_CONFLICT")
        return {
            "status": "ALREADY_MATERIALIZED",
            "path": str(destination),
            "relative_path": relative.as_posix(),
            "size": destination_io.stat().st_size,
            "sha256": EXPECTED_SOURCE_SHA256,
            "idempotent": True,
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = destination.parent / ".stage3d-source.tmp"
    staged_io = _io_path(staged)
    _require(not staged_io.exists(), "SHADOW_ARCHIVE_STAGING_COLLISION")
    try:
        shutil.copy2(_io_path(source_package_path), staged_io)
        _require(staged_io.stat().st_size == EXPECTED_SOURCE_SIZE, "SHADOW_ARCHIVE_STAGED_SIZE_MISMATCH")
        _require(sha256_file(staged_io) == EXPECTED_SOURCE_SHA256, "SHADOW_ARCHIVE_STAGED_SHA_MISMATCH")
        if inject_failure:
            raise PromotionError("INJECTED_SOURCE_MATERIALIZATION_FAILURE")
        os.replace(staged_io, destination_io)
    except Exception:
        if staged_io.exists():
            staged_io.unlink()
        _remove_shadow_source(shadow_filesystem_root, production_root)
        raise
    finally:
        if staged_io.exists():
            staged_io.unlink()
    _require(sha256_file(destination_io) == EXPECTED_SOURCE_SHA256, "SHADOW_ARCHIVE_FINAL_SHA_MISMATCH")
    return {
        "status": "MATERIALIZED",
        "path": str(destination),
        "relative_path": relative.as_posix(),
        "size": destination_io.stat().st_size,
        "sha256": EXPECTED_SOURCE_SHA256,
        "idempotent": False,
    }


def _remove_shadow_source(shadow_filesystem_root: Path, production_root: Path) -> None:
    shadow_filesystem_root = Path(shadow_filesystem_root).resolve()
    production_root = Path(production_root).resolve()
    relative = _safe_relative_path(EXPECTED_ARCHIVE_PATH)
    destination = (shadow_filesystem_root / relative).resolve()
    real_destination = (production_root / relative).resolve()
    _require(_is_within(destination, shadow_filesystem_root), "SHADOW_ARCHIVE_CLEANUP_OUTSIDE_ROOT")
    _require(not _paths_equivalent(destination, real_destination), "PRODUCTION_ARCHIVE_CLEANUP_BLOCKED")
    destination_io = _io_path(destination)
    if destination_io.exists():
        destination_io.unlink()
    parent = destination.parent
    while parent != shadow_filesystem_root and _is_within(parent, shadow_filesystem_root):
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
    try:
        shadow_filesystem_root.rmdir()
    except OSError:
        pass


def apply_final_package_to_shadow(
    payload: Mapping[str, Any],
    *,
    shadow_path: Path,
    configured_production_path: Path,
    source_package_path: Path,
    shadow_filesystem_root: Path,
    production_root: Path,
    inject_db_failure_after: int | None = None,
    inject_materialization_failure: bool = False,
) -> dict[str, Any]:
    validate_final_payload(payload)
    assert_shadow_target(shadow_path, configured_production_path)
    materialization = materialize_source_to_shadow(
        payload,
        source_package_path=source_package_path,
        shadow_filesystem_root=shadow_filesystem_root,
        production_root=production_root,
        inject_failure=inject_materialization_failure,
    )
    try:
        database = apply_payload_to_shadow(
            payload,
            shadow_path,
            configured_production_path,
            inject_failure_after=inject_db_failure_after,
        )
    except Exception:
        if materialization["status"] == "MATERIALIZED":
            _remove_shadow_source(shadow_filesystem_root, production_root)
        raise
    return {"source_materialization": materialization, "database": database}


def qualify_final_shadow(
    payload: Mapping[str, Any],
    *,
    production_path: Path,
    production_root: Path,
    source_package_path: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    production_path = Path(production_path).resolve()
    production_root = Path(production_root).resolve()
    source_package_path = Path(source_package_path).resolve()
    output_dir = Path(output_dir).resolve()
    receipt_path = Path(receipt_path).resolve()
    preflight = preflight_final_payload(
        payload,
        production_path=production_path,
        source_package_path=source_package_path,
        production_root=production_root,
    )
    production_pre = production_identity(production_path)
    real_archive_pre = filesystem_inventory(production_root / "archive")

    shadow_path = output_dir / "final_shadow.db"
    shadow_filesystem = output_dir / "final_shadow_filesystem"
    shadow_pre_sha = copy_production_to_shadow(production_path, shadow_path, production_pre["sha256"])
    applied = apply_final_package_to_shadow(
        payload,
        shadow_path=shadow_path,
        configured_production_path=production_path,
        source_package_path=source_package_path,
        shadow_filesystem_root=shadow_filesystem,
        production_root=production_root,
    )
    expected_inventory = [{
        "path": EXPECTED_ARCHIVE_PATH,
        "size": EXPECTED_SOURCE_SIZE,
        "sha256": EXPECTED_SOURCE_SHA256,
    }]
    shadow_inventory = filesystem_inventory(shadow_filesystem)
    _require(shadow_inventory == expected_inventory, "SHADOW_ARCHIVE_POSTFLIGHT_MISMATCH")

    replay = apply_final_package_to_shadow(
        payload,
        shadow_path=shadow_path,
        configured_production_path=production_path,
        source_package_path=source_package_path,
        shadow_filesystem_root=shadow_filesystem,
        production_root=production_root,
    )
    _require(replay["database"]["status"] == "ALREADY_APPLIED", "FINAL_IDEMPOTENT_DB_REPLAY_FAILED")
    _require(replay["source_materialization"]["status"] == "ALREADY_MATERIALIZED", "FINAL_IDEMPOTENT_SOURCE_REPLAY_FAILED")
    _require(filesystem_inventory(shadow_filesystem) == expected_inventory, "FINAL_IDEMPOTENT_ARCHIVE_CHANGED")

    rollback_shadow = output_dir / "final_shadow_rollback.db"
    rollback_filesystem = output_dir / "final_shadow_rollback_filesystem"
    copy_production_to_shadow(production_path, rollback_shadow, production_pre["sha256"])
    rollback_before = database_identity(rollback_shadow, require_no_sidecars=True)
    rollback_error = ""
    try:
        apply_final_package_to_shadow(
            payload,
            shadow_path=rollback_shadow,
            configured_production_path=production_path,
            source_package_path=source_package_path,
            shadow_filesystem_root=rollback_filesystem,
            production_root=production_root,
            inject_db_failure_after=2,
        )
    except PromotionError as exc:
        rollback_error = str(exc)
    _require(rollback_error == "INJECTED_TRANSACTION_FAILURE", "FINAL_ROLLBACK_INJECTION_NOT_OBSERVED")
    rollback_after = database_identity(rollback_shadow, require_no_sidecars=True)
    rollback_pass = rollback_before["semantic_snapshot"] == rollback_after["semantic_snapshot"]
    _require(rollback_pass, "FINAL_DB_ROLLBACK_SEMANTIC_MISMATCH")
    _require(filesystem_inventory(rollback_filesystem) == [], "FINAL_DB_FAILURE_SOURCE_CLEANUP_FAILED")

    source_failure_shadow = output_dir / "final_shadow_source_failure.db"
    source_failure_filesystem = output_dir / "final_shadow_source_failure_filesystem"
    copy_production_to_shadow(production_path, source_failure_shadow, production_pre["sha256"])
    source_failure_error = ""
    try:
        apply_final_package_to_shadow(
            payload,
            shadow_path=source_failure_shadow,
            configured_production_path=production_path,
            source_package_path=source_package_path,
            shadow_filesystem_root=source_failure_filesystem,
            production_root=production_root,
            inject_materialization_failure=True,
        )
    except PromotionError as exc:
        source_failure_error = str(exc)
    _require(source_failure_error == "INJECTED_SOURCE_MATERIALIZATION_FAILURE", "SOURCE_FAILURE_INJECTION_NOT_OBSERVED")
    source_failure_identity = database_identity(source_failure_shadow, require_no_sidecars=True)
    _require(source_failure_identity["sha256"] == production_pre["sha256"], "SOURCE_FAILURE_CHANGED_DATABASE")
    _require(filesystem_inventory(source_failure_filesystem) == [], "SOURCE_FAILURE_CLEANUP_FAILED")

    restore_shadow = output_dir / "final_shadow_restore.db"
    restore_backup = output_dir / "final_shadow_restore_backup.db"
    restore_filesystem = output_dir / "final_shadow_restore_filesystem"
    copy_production_to_shadow(production_path, restore_shadow, production_pre["sha256"])
    copy_production_to_shadow(production_path, restore_backup, production_pre["sha256"])
    apply_final_package_to_shadow(
        payload,
        shadow_path=restore_shadow,
        configured_production_path=production_path,
        source_package_path=source_package_path,
        shadow_filesystem_root=restore_filesystem,
        production_root=production_root,
    )
    shutil.copyfile(restore_backup, restore_shadow)
    _remove_shadow_source(restore_filesystem, production_root)
    restore_identity = database_identity(restore_shadow, require_no_sidecars=True)
    restore_pass = (
        restore_identity["sha256"] == production_pre["sha256"]
        and restore_identity["semantic_snapshot"] == production_pre["semantic_snapshot"]
        and restore_identity["integrity"] == "ok"
        and not restore_identity["foreign_key_violations"]
        and filesystem_inventory(restore_filesystem) == []
    )
    _require(restore_pass, "FINAL_RESTORE_DRILL_FAILED")

    production_post = production_identity(production_path)
    real_archive_post = filesystem_inventory(production_root / "archive")
    production_unchanged = (
        production_pre["sha256"] == production_post["sha256"] == EXPECTED_PRODUCTION_SHA256
        and production_pre["semantic_snapshot"] == production_post["semantic_snapshot"]
        and production_pre["sidecars"] == production_post["sidecars"]
    )
    _require(production_unchanged, "PRODUCTION_CHANGED_DURING_FINAL_QUALIFICATION")
    _require(real_archive_pre == real_archive_post, "PRODUCTION_ARCHIVE_CHANGED_DURING_FINAL_QUALIFICATION")
    receipt = {
        "document_type": QUALIFICATION_DOCUMENT_TYPE,
        "receipt_version": "1",
        "receipt_time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS",
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "preflight": preflight,
        "source_package": {
            "path": str(source_package_path),
            "size": _io_path(source_package_path).stat().st_size,
            "sha256": sha256_file(_io_path(source_package_path)),
        },
        "production": {
            "pre_sha256": production_pre["sha256"],
            "post_sha256": production_post["sha256"],
            "schema_version": production_pre["schema_version"],
            "schema_sha256": production_pre["schema_sha256"],
            "counts": production_pre["counts"],
            "integrity": production_post["integrity"],
            "foreign_key_violations": production_post["foreign_key_violations"],
            "sidecars_pre": production_pre["sidecars"],
            "sidecars_post": production_post["sidecars"],
            "archive_inventory_pre": real_archive_pre,
            "archive_inventory_post": real_archive_post,
            "archive_changed": False,
            "changed": False,
            "apply_attempted": False,
            "apply_authorized": False,
        },
        "shadow": {
            "path": str(shadow_path),
            "pre_sha256": shadow_pre_sha,
            "post_sha256": applied["database"]["shadow_post_sha256"],
            "changed_tables": applied["database"]["changed_tables"],
            "foreign_key_violations": applied["database"]["foreign_key_violations"],
            "integrity": applied["database"]["integrity"],
            "source_materialization": applied["source_materialization"],
            "archive_inventory": shadow_inventory,
        },
        "idempotency": {
            "database_status": replay["database"]["status"],
            "source_status": replay["source_materialization"]["status"],
            "changed_tables": replay["database"]["changed_tables"],
            "pass": True,
        },
        "rollback": {
            "transaction_failure": rollback_error,
            "semantic_state_restored": rollback_pass,
            "source_cleanup_pass": True,
            "status": "PASS",
        },
        "source_failure": {
            "failure": source_failure_error,
            "database_unchanged": True,
            "source_cleanup_pass": True,
            "status": "PASS",
        },
        "restore": {
            "restored_sha256": restore_identity["sha256"],
            "semantic_state_restored": restore_pass,
            "archive_state_restored": True,
            "integrity": restore_identity["integrity"],
            "foreign_key_violations": restore_identity["foreign_key_violations"],
            "status": "PASS",
        },
    }
    _write_json(receipt_path, receipt)
    return receipt


def build_manifest(output_dir: Path, *, repository_commit: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    roles = {
        "source_package": output_dir / "source" / f"{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}",
        "source_materialization": output_dir / "source_materialization_final.json",
        "authorization_bound_payload": output_dir / "phase3d_authorization_bound_payload.json",
        "final_shadow_qualification_receipt": output_dir / "phase3d_final_shadow_qualification_receipt.json",
    }
    artifacts = []
    for role, path in roles.items():
        path_io = _io_path(path)
        _require(path_io.is_file(), f"MANIFEST_ARTIFACT_MISSING:{role}")
        artifacts.append({
            "role": role,
            "path": str(path),
            "size": path_io.stat().st_size,
            "sha256": sha256_file(path_io),
        })
    return {
        "document_type": MANIFEST_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "PASS",
        "repository_commit": repository_commit,
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "artifacts": artifacts,
        "flags": {
            "phase3d_stage3d3c_complete": True,
            "production_apply_authorized": False,
            "production_changed": False,
            "production_apply_attempted": False,
        },
    }
