"""Deterministic Phase 3F operational human-review packet and validator."""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .production_promotion import canonical_sha256, sha256_file


PACKET_DOCUMENT_TYPE = "phase3f_operational_review_packet"
PACKET_SCHEMA_VERSION = "1"
PACKET_STATUS = "HUMAN_COMPLETION_REQUIRED"
DECISION_AUTHORITY = "USER_HUMAN_REVIEW"

CLAIM_DECISIONS = ("KEEP", "DROP", "KEEP_NEEDS_REVIEW")
NODE_DECISIONS = ("CREATE", "REUSE", "DEFER", "REJECT")
PARENT_PLACEMENT_DECISIONS = ("CREATE", "DEFER", "REJECT")

CLAIM_ID = re.compile(r"CLM_[A-Z0-9][A-Z0-9_]*\Z")
NODE_CANDIDATE_ID = re.compile(r"CAND_NODE_[A-Z0-9][A-Z0-9_]*\Z")
PARENT_PLACEMENT_ID = re.compile(r"PARENT_PLACEMENT_[A-Z0-9][A-Z0-9_]*\Z")
RUN_ID = re.compile(r"INGEST_[A-Z0-9][A-Z0-9_]*\Z")
SOURCE_ID = re.compile(r"SRC_[A-Z0-9][A-Z0-9_]*\Z")
NODE_ID = re.compile(r"NODE_[A-Z0-9][A-Z0-9_]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")

_JSON_ARTIFACTS = (
    ("evidence_bound_extraction_bundle", "evidence/evidence_bound_extraction_bundle.json"),
    ("claim_review", "review/claim_review.json"),
    ("node_operation_review", "review/node_operation_review.json"),
    ("promotion_preview", "promotion/promotion_preview.json"),
)

_ROOT_FIELDS = {
    "document_type",
    "schema_version",
    "packet_status",
    "packet_id",
    "immutable_packet_sha256",
    "contract_basis",
    "run",
    "source",
    "production_baseline",
    "authoritative_inputs",
    "decision_contract",
    "summary",
    "human_completion",
    "claims",
    "nodes",
    "aliases",
    "relations",
    "excluded_relation_inventory",
    "safety",
}
_RECORD_FIELDS = {
    "candidate_type",
    "candidate_id",
    "provenance",
    "content",
    "content_sha256",
    "allowed_decisions",
    "decision_effects",
    "human_input",
}


class ReviewCompletionError(ValueError):
    """A stable fail-closed review-packet validation error."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ReviewCompletionError(code, detail)


def _read_json(path: Path) -> dict[str, Any]:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "INVALID_JSON", f"duplicate key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ReviewCompletionError("INVALID_JSON", f"non-JSON constant: {value}")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=invalid_constant,
        )
        json.dumps(value, allow_nan=False)
    except ReviewCompletionError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReviewCompletionError("INVALID_JSON", f"{path}: {exc}") from exc
    _require(isinstance(value, dict), "INVALID_ARTIFACT", f"object required: {path}")
    return value


def read_review_packet(path: str | Path) -> dict[str, Any]:
    """Read a review packet without accepting duplicate keys or non-JSON values."""
    return _read_json(Path(path))


def _semantic_identity(
    artifact: Mapping[str, Any],
    *,
    id_field: str,
    hash_field: str,
    id_prefix: str,
) -> str:
    body = {
        key: copy.deepcopy(value)
        for key, value in artifact.items()
        if key not in {id_field, hash_field}
    }
    digest = canonical_sha256(body)
    _require(artifact.get(hash_field) == digest, "ARTIFACT_SEMANTIC_HASH_MISMATCH", hash_field)
    _require(
        artifact.get(id_field) == f"{id_prefix}_{digest[:16].upper()}",
        "ARTIFACT_ID_MISMATCH",
        id_field,
    )
    return digest


def _safe_source_path(run_root: Path, relative_path: Any) -> Path:
    _require(isinstance(relative_path, str) and relative_path, "SOURCE_PATH_INVALID")
    normalized = relative_path.replace("\\", "/")
    _require(not normalized.startswith("/") and ".." not in normalized.split("/"), "SOURCE_PATH_INVALID")
    path = (run_root / normalized).resolve()
    root = run_root.resolve()
    _require(path != root and root in path.parents, "SOURCE_PATH_INVALID")
    return path


def _input_artifact_binding(
    role: str,
    relative_path: str,
    path: Path,
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "role": role,
        "relative_path": relative_path.replace("\\", "/"),
        "file_sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    if artifact is not None:
        binding["document_type"] = artifact.get("document_type")
        if role == "claim_review":
            binding.update({
                "artifact_id": artifact.get("review_id"),
                "semantic_sha256": artifact.get("review_sha256"),
            })
        elif role == "node_operation_review":
            binding.update({
                "artifact_id": artifact.get("review_id"),
                "semantic_sha256": artifact.get("review_sha256"),
            })
        elif role == "promotion_preview":
            binding.update({
                "artifact_id": artifact.get("preview_id"),
                "semantic_sha256": artifact.get("preview_sha256"),
            })
        elif role == "run_manifest":
            binding["artifact_id"] = artifact.get("run_id")
    return binding


def _load_frozen_run(run_root: Path) -> dict[str, Any]:
    run_root = run_root.resolve()
    manifest_path = run_root / "run_manifest.json"
    manifest = _read_json(manifest_path)
    artifacts = {
        role: _read_json(run_root / relative)
        for role, relative in _JSON_ARTIFACTS
    }
    claim_review = artifacts["claim_review"]
    node_review = artifacts["node_operation_review"]
    preview = artifacts["promotion_preview"]
    bundle = artifacts["evidence_bound_extraction_bundle"]

    _require(manifest.get("document_type") == "phase3e_operational_ingestion_manifest", "MANIFEST_TYPE_INVALID")
    _require(manifest.get("schema_version") == "1", "MANIFEST_VERSION_INVALID")
    run_id = manifest.get("run_id")
    _require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id), "RUN_ID_INVALID")
    _require(manifest.get("stage_status") == "HUMAN_REVIEW_REQUIRED", "RUN_NOT_AT_HUMAN_REVIEW_GATE")

    source = manifest.get("source") or {}
    source_id = source.get("source_id")
    source_sha256 = source.get("sha256")
    _require(isinstance(source_id, str) and SOURCE_ID.fullmatch(source_id), "SOURCE_ID_INVALID")
    _require(isinstance(source_sha256, str) and SHA256.fullmatch(source_sha256), "SOURCE_SHA256_INVALID")
    source_relative = str(source.get("frozen_relative_path") or "").replace("\\", "/")
    source_path = _safe_source_path(run_root, source_relative)
    _require(source_path.is_file(), "FROZEN_SOURCE_MISSING")
    _require(sha256_file(source_path) == source_sha256, "FROZEN_SOURCE_HASH_MISMATCH")
    _require(source.get("frozen_copy_sha256") == source_sha256, "FROZEN_SOURCE_BINDING_MISMATCH")

    _require(claim_review.get("document_type") == "phase3e_claim_review", "CLAIM_REVIEW_TYPE_INVALID")
    _require(claim_review.get("schema_version") == "1", "CLAIM_REVIEW_VERSION_INVALID")
    _require(claim_review.get("review_status") == "DRAFT", "CLAIM_REVIEW_NOT_DRAFT")
    _require(claim_review.get("run_id") == run_id, "CLAIM_REVIEW_RUN_MISMATCH")
    _require(claim_review.get("source_sha256") == source_sha256, "CLAIM_REVIEW_SOURCE_MISMATCH")
    _semantic_identity(
        claim_review,
        id_field="review_id",
        hash_field="review_sha256",
        id_prefix="CLAIM_REVIEW",
    )
    claims = claim_review.get("claims") or []
    _require(isinstance(claims, list) and claims, "CLAIM_REVIEW_EMPTY")
    _require(all(item.get("human_decision") == "PENDING" for item in claims), "CLAIM_DECISION_ALREADY_PRESENT")
    _require((claim_review.get("authorization") or {}).get("human_decisions_bound") is False, "CLAIM_REVIEW_ALREADY_AUTHORIZED")

    _require(node_review.get("document_type") == "phase3e_node_operation_review", "NODE_REVIEW_TYPE_INVALID")
    _require(node_review.get("schema_version") == "1", "NODE_REVIEW_VERSION_INVALID")
    _require(node_review.get("review_status") == "DRAFT", "NODE_REVIEW_NOT_DRAFT")
    operational_run = node_review.get("operational_run") or {}
    _require(operational_run.get("run_id") == run_id, "NODE_REVIEW_RUN_MISMATCH")
    _require(operational_run.get("source_sha256") == source_sha256, "NODE_REVIEW_SOURCE_MISMATCH")
    _require(
        operational_run.get("claim_review_sha256")
        == sha256_file(run_root / "review/claim_review.json"),
        "NODE_CLAIM_REVIEW_BINDING_MISMATCH",
    )
    _semantic_identity(
        node_review,
        id_field="review_id",
        hash_field="review_sha256",
        id_prefix="NODE_REVIEW",
    )
    nodes = node_review.get("records") or []
    _require(isinstance(nodes, list) and nodes, "NODE_REVIEW_EMPTY")
    _require(all(item.get("review_decision") == "PENDING" for item in nodes), "NODE_DECISION_ALREADY_PRESENT")
    _require(all(item.get("advisory_only") is True for item in nodes), "NODE_SUGGESTION_NOT_ADVISORY")

    _require(preview.get("document_type") == "phase3e_non_executable_promotion_preview", "PREVIEW_TYPE_INVALID")
    _require(preview.get("schema_version") == "1", "PREVIEW_VERSION_INVALID")
    _require(preview.get("run_id") == run_id, "PREVIEW_RUN_MISMATCH")
    _require(preview.get("source_sha256") == source_sha256, "PREVIEW_SOURCE_MISMATCH")
    _semantic_identity(
        preview,
        id_field="preview_id",
        hash_field="preview_sha256",
        id_prefix="PROMOTION_PREVIEW",
    )
    authorization = preview.get("authorization") or {}
    for field in (
        "human_claim_decisions_bound",
        "human_node_decisions_bound",
        "executable",
        "production_apply_authorized",
        "production_executor_compatible",
        "intended_mutations_generated",
    ):
        _require(authorization.get(field) is False, "PREVIEW_UNEXPECTED_AUTHORIZATION", field)

    _require(bundle.get("document_type") == "phase3c_extraction_bundle", "BUNDLE_TYPE_INVALID")
    _require(bundle.get("schema_version") == "1", "BUNDLE_VERSION_INVALID")
    bundle_source = bundle.get("source") or {}
    _require(bundle_source.get("proposed_source_id") == source_id, "BUNDLE_SOURCE_ID_MISMATCH")
    _require(bundle_source.get("sha256") == source_sha256, "BUNDLE_SOURCE_SHA_MISMATCH")
    bundle_claims = bundle.get("claims") or []
    claim_ids = [item.get("claim_id") for item in claims]
    bundle_ids = [item.get("claim_id") for item in bundle_claims]
    _require(claim_ids == bundle_ids, "CLAIM_BUNDLE_UNIVERSE_MISMATCH")
    _require(len(claim_ids) == len(set(claim_ids)), "DUPLICATE_CANDIDATE_ID", "Claim")
    bundle_by_id = {item["claim_id"]: item for item in bundle_claims}
    for item in claims:
        claim_id = item.get("claim_id")
        _require(isinstance(claim_id, str) and CLAIM_ID.fullmatch(claim_id), "CANDIDATE_ID_INVALID", str(claim_id))
        source_claim = bundle_by_id[claim_id]
        for field in ("statement", "evidence_pointer", "evidence_excerpt"):
            _require(item.get(field) == source_claim.get(field), "CLAIM_CONTENT_BINDING_MISMATCH", f"{claim_id}:{field}")

    node_ids = [item.get("operation_candidate_id") for item in nodes]
    _require(len(node_ids) == len(set(node_ids)), "DUPLICATE_CANDIDATE_ID", "Node")
    for item in nodes:
        candidate_id = item.get("operation_candidate_id")
        _require(
            isinstance(candidate_id, str) and NODE_CANDIDATE_ID.fullmatch(candidate_id),
            "CANDIDATE_ID_INVALID",
            str(candidate_id),
        )
        _require(set(item.get("supporting_claim_ids") or []).issubset(claim_ids), "NODE_CLAIM_REFERENCE_INVALID", candidate_id)

    parent_suggestions = preview.get("parent_placement_suggestions") or []
    _require(isinstance(parent_suggestions, list), "PARENT_PLACEMENT_LIST_INVALID")
    parent_ids = [item.get("suggestion_id") for item in parent_suggestions]
    _require(len(parent_ids) == len(set(parent_ids)), "DUPLICATE_CANDIDATE_ID", "Parent placement")
    node_id_set = set(node_ids)
    for item in parent_suggestions:
        suggestion_id = item.get("suggestion_id")
        _require(
            isinstance(suggestion_id, str) and PARENT_PLACEMENT_ID.fullmatch(suggestion_id),
            "CANDIDATE_ID_INVALID",
            str(suggestion_id),
        )
        _require(item.get("candidate_id") in node_id_set, "PARENT_NODE_CANDIDATE_MISSING", str(suggestion_id))
        _require(item.get("human_decision") == "PENDING", "PARENT_DECISION_ALREADY_PRESENT", str(suggestion_id))
        _require(item.get("authorized_by_node_create") is False, "PARENT_PLACEMENT_ALREADY_AUTHORIZED", str(suggestion_id))
        _require(item.get("executable") is False, "PARENT_PLACEMENT_ALREADY_EXECUTABLE", str(suggestion_id))

    production = copy.deepcopy(manifest.get("production_baseline") or {})
    node_baseline = node_review.get("production_baseline") or {}
    _require(
        all(production.get(key) == value for key, value in node_baseline.items()),
        "PRODUCTION_BASELINE_BINDING_MISMATCH",
    )
    _require(production == (preview.get("bindings") or {}).get("production_baseline"), "PREVIEW_BASELINE_BINDING_MISMATCH")

    inventory = {
        item.get("path"): item
        for item in manifest.get("artifact_inventory") or []
        if isinstance(item, dict)
    }
    bindings = [
        _input_artifact_binding("run_manifest", "run_manifest.json", manifest_path, manifest)
    ]
    for role, relative in _JSON_ARTIFACTS:
        path = run_root / relative
        binding = _input_artifact_binding(role, relative, path, artifacts[role])
        frozen = inventory.get(relative) or {}
        _require(
            frozen.get("sha256") == binding["file_sha256"]
            and frozen.get("size_bytes") == binding["size_bytes"],
            "FROZEN_ARTIFACT_HASH_MISMATCH",
            relative,
        )
        bindings.append(binding)
    source_binding = _input_artifact_binding("frozen_source", source_relative, source_path, None)
    frozen_source = inventory.get(source_relative) or {}
    _require(
        frozen_source.get("sha256") == source_binding["file_sha256"]
        and frozen_source.get("size_bytes") == source_binding["size_bytes"],
        "FROZEN_ARTIFACT_HASH_MISMATCH",
        source_relative,
    )
    bindings.append(source_binding)

    return {
        "manifest": manifest,
        "bundle": bundle,
        "claim_review": claim_review,
        "node_review": node_review,
        "preview": preview,
        "bindings": bindings,
        "source_relative": source_relative,
    }


def _claim_guard_summary(admission: Mapping[str, Any]) -> dict[str, Any]:
    proposition = admission.get("proposition_ir_validation") or {}
    return {
        "overall_guard_disposition": admission.get("overall_guard_disposition"),
        "guard_reasons": copy.deepcopy(admission.get("guard_reasons") or []),
        "proposition_ir_validation": {
            "status": proposition.get("status"),
            "issue_codes": copy.deepcopy(proposition.get("issue_codes") or []),
        },
    }


def _record(
    *,
    candidate_type: str,
    candidate_id: str,
    provenance: Mapping[str, Any],
    content: Mapping[str, Any],
    allowed_decisions: tuple[str, ...],
    decision_effects: Mapping[str, str],
    include_target: bool,
) -> dict[str, Any]:
    human_input = {"decision": "", "reason": ""}
    if include_target:
        human_input["target_node_id"] = ""
    frozen_content = copy.deepcopy(dict(content))
    return {
        "candidate_type": candidate_type,
        "candidate_id": candidate_id,
        "provenance": copy.deepcopy(dict(provenance)),
        "content": frozen_content,
        "content_sha256": canonical_sha256(frozen_content),
        "allowed_decisions": list(allowed_decisions),
        "decision_effects": copy.deepcopy(dict(decision_effects)),
        "human_input": human_input,
    }


def build_blank_review_packet(run_root: str | Path) -> dict[str, Any]:
    """Build a blank packet from one frozen Phase 3E operational run."""
    frozen = _load_frozen_run(Path(run_root))
    manifest = frozen["manifest"]
    claim_review = frozen["claim_review"]
    node_review = frozen["node_review"]
    preview = frozen["preview"]
    run_id = manifest["run_id"]
    source = manifest["source"]
    source_id = source["source_id"]
    source_sha256 = source["sha256"]

    claim_provenance = {
        "run_id": run_id,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "review_artifact_role": "claim_review",
        "review_id": claim_review["review_id"],
        "review_semantic_sha256": claim_review["review_sha256"],
        "review_file_sha256": next(
            item["file_sha256"] for item in frozen["bindings"] if item["role"] == "claim_review"
        ),
        "evidence_bundle_file_sha256": next(
            item["file_sha256"]
            for item in frozen["bindings"]
            if item["role"] == "evidence_bound_extraction_bundle"
        ),
    }
    claims = []
    for item in claim_review["claims"]:
        content = {
            "statement": item.get("statement"),
            "evidence_pointer": item.get("evidence_pointer"),
            "evidence_excerpt": item.get("evidence_excerpt"),
            "evidence_validation": copy.deepcopy(item.get("evidence_validation") or {}),
            "table_eligibility": copy.deepcopy(item.get("table_eligibility") or {}),
            "semantic_admission": _claim_guard_summary(item.get("semantic_admission") or {}),
            "scope_preservation": copy.deepcopy(item.get("scope_preservation") or {}),
            "review_admitted": item.get("review_admitted"),
            "advisory_recommendation": item.get("recommended_decision"),
            "advisory_recommendation_reason": item.get("recommendation_reason"),
            "duplicate_of_claim_id": item.get("duplicate_of_claim_id"),
            "duplicate_reconciliation": item.get("duplicate_reconciliation"),
            "current_operational_decision": item.get("human_decision"),
        }
        claims.append(_record(
            candidate_type="CLAIM",
            candidate_id=item["claim_id"],
            provenance=claim_provenance,
            content=content,
            allowed_decisions=CLAIM_DECISIONS,
            decision_effects={
                "KEEP": "PROMOTION_AUTHORIZING_CONDITIONAL",
                "DROP": "NON_PROMOTABLE",
                "KEEP_NEEDS_REVIEW": "DEFERRED_NON_PROMOTABLE",
            },
            include_target=False,
        ))

    node_provenance = {
        "run_id": run_id,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "review_artifact_role": "node_operation_review",
        "review_id": node_review["review_id"],
        "review_semantic_sha256": node_review["review_sha256"],
        "review_file_sha256": next(
            item["file_sha256"]
            for item in frozen["bindings"]
            if item["role"] == "node_operation_review"
        ),
        "claim_review_semantic_sha256": claim_review["review_sha256"],
    }
    nodes = []
    for item in node_review["records"]:
        content = {
            "source_operation_id": item.get("source_operation_id"),
            "candidate_kind": item.get("candidate_kind"),
            "proposed_name": item.get("proposed_name"),
            "proposed_type": item.get("proposed_type"),
            "proposed_aliases": copy.deepcopy(item.get("proposed_aliases") or []),
            "prospective_node_id": item.get("prospective_node_id"),
            "supporting_claim_ids": copy.deepcopy(item.get("supporting_claim_ids") or []),
            "supporting_evidence": copy.deepcopy(item.get("supporting_evidence") or []),
            "phase3c_validation_state": copy.deepcopy(item.get("phase3c_validation_state") or {}),
            "current_defer_reason": item.get("current_defer_reason"),
            "exact_production_resolution": copy.deepcopy(item.get("exact_production_resolution") or {}),
            "collision_diagnostics": copy.deepcopy(item.get("collision_diagnostics") or {}),
            "advisory_suggestion": item.get("suggested_operation"),
            "advisory_suggestion_reason": item.get("suggestion_reason"),
            "current_operational_decision": item.get("review_decision"),
            "parent_placement_suggestion": copy.deepcopy(item.get("parent_placement_suggestion") or {}),
        }
        nodes.append(_record(
            candidate_type="NODE",
            candidate_id=item["operation_candidate_id"],
            provenance=node_provenance,
            content=content,
            allowed_decisions=NODE_DECISIONS,
            decision_effects={
                "CREATE": "PROMOTION_AUTHORIZING_CONDITIONAL",
                "REUSE": "PROMOTION_AUTHORIZING_CONDITIONAL",
                "DEFER": "DEFERRED_NON_PROMOTABLE",
                "REJECT": "NON_PROMOTABLE",
            },
            include_target=True,
        ))

    preview_binding = next(
        item for item in frozen["bindings"] if item["role"] == "promotion_preview"
    )
    relation_provenance = {
        "run_id": run_id,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "review_artifact_role": "promotion_preview_parent_placement",
        "review_id": preview["preview_id"],
        "review_semantic_sha256": preview["preview_sha256"],
        "review_file_sha256": preview_binding["file_sha256"],
        "node_review_semantic_sha256": node_review["review_sha256"],
    }
    relations = []
    for item in preview.get("parent_placement_suggestions") or []:
        content = {
            "child_node_candidate_id": item.get("candidate_id"),
            "prospective_child_node_id": item.get("prospective_child_node_id"),
            "relation_type": "part_of",
            "parent_node_id": item.get("parent_node_id"),
            "suggestion_type": item.get("suggestion_type"),
            "governance_status": item.get("governance_status"),
            "authorized_by_node_create": item.get("authorized_by_node_create"),
            "current_operational_decision": item.get("human_decision"),
            "executable": item.get("executable"),
        }
        relations.append(_record(
            candidate_type="PARENT_PLACEMENT",
            candidate_id=item["suggestion_id"],
            provenance=relation_provenance,
            content=content,
            allowed_decisions=PARENT_PLACEMENT_DECISIONS,
            decision_effects={
                "CREATE": "PROMOTION_AUTHORIZING_CONDITIONAL_ON_NODE_CREATE",
                "DEFER": "DEFERRED_NON_PROMOTABLE",
                "REJECT": "NON_PROMOTABLE",
            },
            include_target=False,
        ))

    rejected_relations = node_review.get("audit_operations", {}).get("relations") or []
    rejected_relation_ids = [item.get("candidate_id") for item in rejected_relations]
    proposed_aliases = sum(len(item["content"]["proposed_aliases"]) for item in nodes)
    universe = [
        {"candidate_type": item["candidate_type"], "candidate_id": item["candidate_id"]}
        for item in [*claims, *nodes, *relations]
    ]
    total = len(universe)
    body = {
        "document_type": PACKET_DOCUMENT_TYPE,
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_status": PACKET_STATUS,
        "contract_basis": {
            "stage0_contract_commit": "849eb91339d9d57679fd8fb33951f5f13591f49d",
            "stage1_census_commit": "2a915656dc724c28f09d7819da7d9496828dafa3",
            "stage_name": "PHASE3F_STAGE1_REVIEW_COMPLETION_INPUT_GATE",
        },
        "run": {
            "run_id": run_id,
            "manifest_repository_commit": manifest.get("repository_commit"),
            "manifest_stage_status": manifest.get("stage_status"),
        },
        "source": {
            "source_id": source_id,
            "filename": source.get("filename"),
            "source_sha256": source_sha256,
            "size_bytes": source.get("size_bytes"),
            "source_type": source.get("source_type"),
            "frozen_relative_path": frozen["source_relative"],
        },
        "production_baseline": copy.deepcopy(manifest.get("production_baseline") or {}),
        "authoritative_inputs": copy.deepcopy(frozen["bindings"]),
        "decision_contract": {
            "decision_authority": DECISION_AUTHORITY,
            "claim": {
                "allowed": list(CLAIM_DECISIONS),
                "promotion_authorizing": ["KEEP"],
                "non_promotable": ["DROP"],
                "defer_promotion": ["KEEP_NEEDS_REVIEW"],
                "reason_required": True,
            },
            "node": {
                "allowed": list(NODE_DECISIONS),
                "promotion_authorizing": ["CREATE", "REUSE"],
                "non_promotable": ["REJECT"],
                "defer_promotion": ["DEFER"],
                "reason_required": True,
                "reuse_target_node_id_required": True,
            },
            "parent_placement": {
                "allowed": list(PARENT_PLACEMENT_DECISIONS),
                "promotion_authorizing": ["CREATE"],
                "non_promotable": ["REJECT"],
                "defer_promotion": ["DEFER"],
                "reason_required": True,
                "create_requires_linked_node_create": True,
            },
            "aliases": {
                "separate_decision_rows": False,
                "policy": "IMMUTABLE_PART_OF_NODE_IDENTITY_REVIEW",
            },
        },
        "summary": {
            "claims_requiring_decision": len(claims),
            "nodes_requiring_decision": len(nodes),
            "aliases_requiring_decision": 0,
            "relations_requiring_decision": len(relations),
            "total_operational_decisions_required": total,
            "proposed_aliases_within_node_review": proposed_aliases,
            "audit_only_rejected_relations": len(rejected_relations),
            "candidate_universe_sha256": canonical_sha256(universe),
        },
        "human_completion": {
            "decision_authority": DECISION_AUTHORITY,
            "reviewer": "",
        },
        "claims": claims,
        "nodes": nodes,
        "aliases": [],
        "relations": relations,
        "excluded_relation_inventory": {
            "policy": "PHASE3E_RELATIONS_EXCLUDED_FROM_PROMOTION",
            "relation_review_reopened": False,
            "count": len(rejected_relations),
            "candidate_ids": rejected_relation_ids,
            "candidate_ids_sha256": canonical_sha256(rejected_relation_ids),
        },
        "safety": {
            "operational_decisions_prefilled": False,
            "evaluation_gold_included": False,
            "evaluation_gold_used_as_authorization": False,
            "llm_authorization_used": False,
            "production_apply_authorized": False,
            "production_mutation_permitted": False,
        },
    }
    digest = canonical_sha256(body)
    return {
        **body,
        "packet_id": f"REVIEW_PACKET_{digest[:16].upper()}",
        "immutable_packet_sha256": digest,
    }


def _exact_keys(value: Any, expected: set[str], name: str) -> None:
    _require(isinstance(value, dict) and set(value) == expected, "PACKET_STRUCTURE_INVALID", name)


def _validate_packet_structure(packet: Mapping[str, Any]) -> None:
    _exact_keys(packet, _ROOT_FIELDS, "root")
    _exact_keys(packet.get("human_completion"), {"decision_authority", "reviewer"}, "human_completion")
    _require(packet["human_completion"].get("decision_authority") == DECISION_AUTHORITY, "DECISION_AUTHORITY_INVALID")
    _require(isinstance(packet["human_completion"].get("reviewer"), str), "REVIEWER_INVALID")
    groups = (
        ("claims", "CLAIM", {"decision", "reason"}),
        ("nodes", "NODE", {"decision", "reason", "target_node_id"}),
        ("relations", "PARENT_PLACEMENT", {"decision", "reason"}),
    )
    for group, candidate_type, human_fields in groups:
        records = packet.get(group)
        _require(isinstance(records, list), "PACKET_STRUCTURE_INVALID", group)
        for record in records:
            _exact_keys(record, _RECORD_FIELDS, f"{group} record")
            _require(record.get("candidate_type") == candidate_type, "CANDIDATE_TYPE_INVALID", group)
            _exact_keys(record.get("human_input"), human_fields, f"{group}.human_input")
            for field in human_fields:
                _require(isinstance(record["human_input"].get(field), str), "HUMAN_INPUT_INVALID", f"{group}:{field}")
    _require(packet.get("aliases") == [], "ALIAS_DECISION_ROWS_FORBIDDEN")


def _validate_candidate_ids(packet: Mapping[str, Any]) -> None:
    patterns = {
        "claims": CLAIM_ID,
        "nodes": NODE_CANDIDATE_ID,
        "relations": PARENT_PLACEMENT_ID,
    }
    all_ids = []
    for group, pattern in patterns.items():
        ids = [item.get("candidate_id") for item in packet[group]]
        for candidate_id in ids:
            _require(
                isinstance(candidate_id, str) and pattern.fullmatch(candidate_id),
                "CANDIDATE_ID_INVALID",
                str(candidate_id),
            )
        _require(len(ids) == len(set(ids)), "DUPLICATE_CANDIDATE_ID", group)
        all_ids.extend(ids)
    _require(len(all_ids) == len(set(all_ids)), "DUPLICATE_CANDIDATE_ID", "cross-type")


def _blank_human_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    blank = copy.deepcopy(dict(packet))
    blank["human_completion"]["reviewer"] = ""
    for group in ("claims", "nodes", "relations"):
        for record in blank[group]:
            for field in record["human_input"]:
                record["human_input"][field] = ""
    return blank


def _validate_immutable_packet(
    packet: Mapping[str, Any], run_root: str | Path
) -> dict[str, Any]:
    _validate_packet_structure(packet)
    _validate_candidate_ids(packet)
    expected = build_blank_review_packet(run_root)
    _require(packet.get("run") == expected["run"], "PACKET_RUN_MISMATCH")
    _require(packet.get("source") == expected["source"], "PACKET_SOURCE_MISMATCH")
    _require(
        packet.get("authoritative_inputs") == expected["authoritative_inputs"],
        "STALE_PACKET_ARTIFACT_HASH",
    )
    _require(packet.get("packet_id") == expected["packet_id"], "PACKET_ID_MISMATCH")
    _require(
        packet.get("immutable_packet_sha256") == expected["immutable_packet_sha256"],
        "PACKET_HASH_MISMATCH",
    )
    _require(_blank_human_fields(packet) == expected, "IMMUTABLE_FIELDS_CHANGED")
    return expected


def validate_blank_review_packet(
    packet: Mapping[str, Any], run_root: str | Path
) -> dict[str, Any]:
    """Validate the authoritative template and require every human field blank."""
    _validate_immutable_packet(packet, run_root)
    _require(packet["human_completion"]["reviewer"] == "", "BLANK_PACKET_REVIEWER_NOT_BLANK")
    for group in ("claims", "nodes", "relations"):
        for record in packet[group]:
            _require(
                all(value == "" for value in record["human_input"].values()),
                "BLANK_PACKET_DECISION_NOT_BLANK",
                record["candidate_id"],
            )
    return {
        "document_type": "phase3f_blank_review_packet_validation",
        "schema_version": "1",
        "status": "VALID_BLANK_REVIEW_PACKET",
        "packet_id": packet["packet_id"],
        "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "run_id": packet["run"]["run_id"],
        "source_id": packet["source"]["source_id"],
        "summary": copy.deepcopy(packet["summary"]),
        "production_apply_authorized": False,
    }


def _completed_text(value: str, code: str, candidate_id: str) -> str:
    _require(bool(value.strip()), code, candidate_id)
    _require(value == value.strip(), "HUMAN_INPUT_PADDING_INVALID", candidate_id)
    return value


def _validate_completed_human_inputs(
    packet: Mapping[str, Any],
) -> tuple[str, dict[str, dict[str, int]], int]:
    """Validate only supplied human inputs after packet immutability is proven."""
    reviewer = _completed_text(
        packet["human_completion"]["reviewer"], "REVIEWER_REQUIRED", "packet"
    )
    counts: dict[str, Counter[str]] = {}
    node_decisions: dict[str, str] = {}

    for group in ("claims", "nodes", "relations"):
        counts[group] = Counter()
        for record in packet[group]:
            candidate_id = record["candidate_id"]
            human = record["human_input"]
            decision = _completed_text(human["decision"], "MISSING_DECISION", candidate_id)
            _require(decision in record["allowed_decisions"], "UNKNOWN_DECISION", f"{candidate_id}:{decision}")
            _completed_text(human["reason"], "MISSING_REVIEW_REASON", candidate_id)
            counts[group][decision] += 1

            if group == "nodes":
                target = human["target_node_id"]
                node_decisions[candidate_id] = decision
                if decision == "REUSE":
                    _completed_text(target, "REUSE_TARGET_REQUIRED", candidate_id)
                    _require(NODE_ID.fullmatch(target) is not None, "REUSE_TARGET_INVALID", candidate_id)
                    resolution = record["content"].get("exact_production_resolution") or {}
                    candidate_targets = resolution.get("candidate_target_node_ids") or []
                    _require(candidate_targets == [target], "REUSE_TARGET_NOT_EXACT", candidate_id)
                else:
                    _require(target == "", "UNEXPECTED_REUSE_TARGET", candidate_id)
                if decision == "CREATE":
                    prospective = record["content"].get("prospective_node_id")
                    _require(isinstance(prospective, str) and NODE_ID.fullmatch(prospective), "CREATE_NODE_ID_INVALID", candidate_id)
                    collision = record["content"].get("collision_diagnostics") or {}
                    _require(collision.get("prospective_node_id_exists") is False, "CREATE_COLLISION_PRESENT", candidate_id)
                    _require(not collision.get("package_internal_normalized_term_collisions"), "CREATE_COLLISION_PRESENT", candidate_id)
                    _require(not collision.get("production_nocase_or_nfkc_target_ids"), "CREATE_COLLISION_PRESENT", candidate_id)

    for record in packet["relations"]:
        if record["human_input"]["decision"] != "CREATE":
            continue
        child_candidate = record["content"].get("child_node_candidate_id")
        _require(
            node_decisions.get(child_candidate) == "CREATE",
            "PARENT_PLACEMENT_REQUIRES_NODE_CREATE",
            record["candidate_id"],
        )
        child_id = record["content"].get("prospective_child_node_id")
        parent_id = record["content"].get("parent_node_id")
        _require(isinstance(child_id, str) and NODE_ID.fullmatch(child_id), "RELATION_ENDPOINT_INVALID", record["candidate_id"])
        _require(isinstance(parent_id, str) and NODE_ID.fullmatch(parent_id), "RELATION_ENDPOINT_INVALID", record["candidate_id"])
        _require(child_id != parent_id, "RELATION_SELF_LOOP", record["candidate_id"])

    decision_counts = {
        group: {decision: counts[group].get(decision, 0) for decision in allowed}
        for group, allowed in (
            ("claims", CLAIM_DECISIONS),
            ("nodes", NODE_DECISIONS),
            ("relations", PARENT_PLACEMENT_DECISIONS),
        )
    }
    total = sum(sum(group.values()) for group in counts.values())
    return reviewer, decision_counts, total


def validate_completed_review_packet(
    packet: Mapping[str, Any], run_root: str | Path
) -> dict[str, Any]:
    """Validate full-run human completion without making or changing a decision."""
    _validate_immutable_packet(packet, run_root)
    reviewer, decision_counts, total = _validate_completed_human_inputs(packet)
    return {
        "document_type": "phase3f_operational_review_completion_validation",
        "schema_version": "1",
        "status": "HUMAN_REVIEW_COMPLETE_AND_VALID",
        "validation_scope": "FULL_OPERATIONAL_REVIEW_COMPLETION",
        "packet_id": packet["packet_id"],
        "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "completed_packet_sha256": canonical_sha256(packet),
        "run_id": packet["run"]["run_id"],
        "source_id": packet["source"]["source_id"],
        "source_sha256": packet["source"]["source_sha256"],
        "decision_authority": DECISION_AUTHORITY,
        "reviewer": reviewer,
        "decision_counts": decision_counts,
        "total_operational_decisions_validated": total,
        "llm_authorization_used": False,
        "production_apply_authorized": False,
    }


def render_review_markdown(packet: Mapping[str, Any]) -> str:
    """Render a concise non-authoritative view of the blank JSON packet."""
    summary = packet["summary"]
    lines = [
        "# Phase 3F Operational Human Review",
        "",
        "> REVIEW VIEW ONLY. Edit the authoritative JSON packet, not this file.",
        "> All decisions are blank. Advisory suggestions and evaluation data are not authorization.",
        "",
        f"- Packet: `{packet['packet_id']}`",
        f"- Run: `{packet['run']['run_id']}`",
        f"- Source: `{packet['source']['source_id']}` / `{packet['source']['source_sha256']}`",
        f"- Claims requiring decisions: `{summary['claims_requiring_decision']}`",
        f"- Nodes requiring decisions: `{summary['nodes_requiring_decision']}`",
        f"- Separate Alias decisions: `{summary['aliases_requiring_decision']}`",
        f"- Parent-placement Relation decisions: `{summary['relations_requiring_decision']}`",
        f"- Total decisions required: `{summary['total_operational_decisions_required']}`",
        "",
        "## Claims",
        "",
        "Allowed: `KEEP`, `DROP`, `KEEP_NEEDS_REVIEW`. Every decision requires a reason.",
        "",
        "| Claim ID | Statement | Evidence | Guards | Advisory only | Human decision | Reason |",
        "|---|---|---|---|---|---|---|",
    ]

    def clean(value: Any, limit: int = 220) -> str:
        text = str(value or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        return text if len(text) <= limit else text[: limit - 3] + "..."

    for record in packet["claims"]:
        content = record["content"]
        semantic = content["semantic_admission"]
        lines.append(
            f"| `{record['candidate_id']}` | {clean(content['statement'])} | "
            f"{clean(content['evidence_excerpt'])} `{clean(content['evidence_pointer'], 80)}` | "
            f"{clean(semantic['overall_guard_disposition'], 80)} | "
            f"{clean(content['advisory_recommendation'], 80)} |  |  |"
        )

    lines.extend([
        "",
        "## Nodes",
        "",
        "Allowed: `CREATE`, `REUSE`, `DEFER`, `REJECT`. Every decision requires a reason; `REUSE` also requires `target_node_id`.",
        "",
        "| Candidate ID | Name / type | Aliases | Exact target candidates | Advisory only | Human decision | Target | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for record in packet["nodes"]:
        content = record["content"]
        targets = (content["exact_production_resolution"] or {}).get("candidate_target_node_ids") or []
        lines.append(
            f"| `{record['candidate_id']}` | {clean(content['proposed_name'], 120)} / "
            f"{clean(content['proposed_type'], 60)} | {clean(', '.join(content['proposed_aliases']), 150)} | "
            f"{clean(', '.join(targets), 150)} | {clean(content['advisory_suggestion'], 60)} |  |  |  |"
        )

    lines.extend([
        "",
        "## Parent-placement Relations",
        "",
        "Allowed: `CREATE`, `DEFER`, `REJECT`. Every decision requires a reason; `CREATE` requires the linked Node decision to be `CREATE`.",
        "",
        "| Suggestion ID | Child candidate | Prospective child | Parent | Relation | Human decision | Reason |",
        "|---|---|---|---|---|---|---|",
    ])
    for record in packet["relations"]:
        content = record["content"]
        lines.append(
            f"| `{record['candidate_id']}` | `{content['child_node_candidate_id']}` | "
            f"`{content['prospective_child_node_id']}` | `{content['parent_node_id']}` | "
            f"`{content['relation_type']}` |  |  |"
        )
    lines.extend([
        "",
        "## Excluded inventory",
        "",
        f"- Proposed aliases are reviewed only as immutable Node identity content: `{summary['proposed_aliases_within_node_review']}`.",
        f"- Phase 3E audit-only rejected non-structural Relations: `{summary['audit_only_rejected_relations']}`.",
        "- S-L6 evaluation gold is omitted and supplies no operational decision.",
        "- This packet grants no Production apply authority.",
        "",
    ])
    return "\n".join(lines)


def write_blank_review_packet(
    *,
    run_root: str | Path,
    packet_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    """Write deterministic workspace artifacts; never access a mutation path."""
    packet = build_blank_review_packet(run_root)
    validate_blank_review_packet(packet, run_root)
    packet_path = Path(packet_path)
    markdown_path = Path(markdown_path)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with packet_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
    with markdown_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_review_markdown(packet))
    return packet
