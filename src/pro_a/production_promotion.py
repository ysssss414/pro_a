from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import shutil
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DOCUMENT_TYPE = "phase3d_promotion_payload"
PAYLOAD_VERSION = "1"
QUALIFICATION_DOCUMENT_TYPE = "phase3d_shadow_qualification_receipt"
SUPPORTED_OPERATIONS = {"CREATE", "REUSE", "UPDATE", "DEFER", "REJECT"}
EXECUTABLE_OPERATIONS = {"CREATE", "REUSE"}
PILOT6_RUN_ID = "PILOT_20260902_572A6DF2"
PILOT6_SOURCE_SHA256 = "572a6df2b583358506e2a4fb86359a07e9a1503a3507dcdd2c81a8d97c27e97a"
PILOT6_REVIEW_SURFACE_SHA256 = "aeb148d1925bc24f2ff674255f3285f08c10eb469dea853cddd2d1ab3aa81e89"
PILOT6_EXPECTED_ARTIFACT_HASHES = {
    "phase3c_rebound_bundle": "1e94c5db8a67dd556a617fb13dcca9f4fc54e3d5cf51810c7f9b722b82ccc02f",
    "table_claim_safety_boundary": "3fa68e26c0580657c4c26040ac6c0ea870d416e9d251b8f74cad9f12ff301121",
    "delegated_reviewer_signoff": "b5ac42cc44dcc54f02321a643ef399d621a88667a7153da0ee06c954783012d5",
    "generic_extraction_review_draft": "28de1f878905910b6bc9fa50ee75b27bedc829737643073abfaa8f2e02f56411",
}
IMMUTABLE_CLAIM_FIELDS = (
    "claim_id",
    "statement",
    "nature",
    "fact_time",
    "publication_time",
    "evidence_pointer",
    "evidence_excerpt",
    "attributed_to",
    "scope",
    "assumption_text",
    "status",
    "confidence",
    "novelty_level",
    "structured",
    "evidence_validated",
    "phase3c_evidence",
    "related_node_ids",
    "related_candidate_names",
)


class PromotionError(RuntimeError):
    """A fail-closed Stage 3D promotion qualification error."""


@dataclass(frozen=True)
class ArtifactPaths:
    rebound_bundle: Path
    table_boundary: Path
    reviewer_signoff: Path
    review_draft: Path

    def by_role(self) -> dict[str, Path]:
        return {
            "phase3c_rebound_bundle": Path(self.rebound_bundle),
            "table_claim_safety_boundary": Path(self.table_boundary),
            "delegated_reviewer_signoff": Path(self.reviewer_signoff),
            "generic_extraction_review_draft": Path(self.review_draft),
        }


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_id(prefix: str, identity: Any) -> str:
    return f"{prefix}_{canonical_sha256(identity)[:16].upper()}"


def nfkc_casefold(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def sqlite_nocase(value: str) -> str:
    # SQLite's built-in NOCASE collation folds ASCII characters only.
    return "".join(character.lower() if "A" <= character <= "Z" else character for character in value)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PromotionError(code)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionError(f"ARTIFACT_READ_FAILED:{Path(path)}") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"ARTIFACT_NOT_OBJECT:{Path(path)}")
    return value


def _claim_projection(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def _immutable_claim_projection(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {field: copy.deepcopy(claim.get(field)) for field in IMMUTABLE_CLAIM_FIELDS}


def converge_phase3c_artifacts(
    paths: ArtifactPaths,
    *,
    expected_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Bind the rebound bundle, table boundary, and delegated signoff exactly."""
    role_paths = paths.by_role()
    _require(set(expected_hashes) == set(role_paths), "ARTIFACT_ROLE_INVENTORY_MISMATCH")
    hashes: dict[str, str] = {}
    for role, path in role_paths.items():
        _require(path.is_file(), f"ARTIFACT_MISSING:{role}")
        hashes[role] = sha256_file(path)
        _require(hashes[role] == expected_hashes[role], f"ARTIFACT_HASH_MISMATCH:{role}")

    bundle = _load_json(paths.rebound_bundle)
    boundary = _load_json(paths.table_boundary)
    signoff = _load_json(paths.reviewer_signoff)
    review_draft = _load_json(paths.review_draft)
    _require(bundle.get("document_type") == "phase3c_extraction_bundle", "BUNDLE_DOCUMENT_TYPE_INVALID")
    _require(bundle.get("schema_version") == "1", "BUNDLE_SCHEMA_VERSION_INVALID")
    _require(boundary.get("document_type") == "phase3c_pilot6_table_claim_safety_boundary", "BOUNDARY_DOCUMENT_TYPE_INVALID")
    _require(boundary.get("schema_version") == "1", "BOUNDARY_SCHEMA_VERSION_INVALID")
    _require(boundary.get("gate") == "PASS", "BOUNDARY_GATE_NOT_PASS")
    _require(signoff.get("artifact_type") == "phase3c_pilot6_delegated_reviewer_signoff", "SIGNOFF_DOCUMENT_TYPE_INVALID")
    _require(signoff.get("artifact_version") == "v1", "SIGNOFF_VERSION_INVALID")
    _require(review_draft.get("document_type") == "phase3c_extraction_review", "REVIEW_DRAFT_DOCUMENT_TYPE_INVALID")
    _require(review_draft.get("schema_version") == "1", "REVIEW_DRAFT_SCHEMA_VERSION_INVALID")
    _require(review_draft.get("status") == "DRAFT", "GENERIC_REVIEW_MUST_REMAIN_DRAFT")

    run_id = bundle.get("pilot_run_id")
    _require(
        run_id
        and boundary.get("pilot_run_id") == run_id
        and signoff.get("pilot_run_id") == run_id
        and review_draft.get("pilot_run_id") == run_id,
        "PILOT_RUN_ID_MISMATCH",
    )
    source = bundle.get("source") or {}
    source_sha = source.get("sha256")
    source_id = source.get("proposed_source_id")
    _require(source_sha and source_sha == signoff.get("source_sha256"), "SOURCE_SHA256_MISMATCH")
    _require(source_id, "SOURCE_ID_MISSING")
    draft_source = review_draft.get("source") or {}
    _require(
        draft_source.get("sha256") == source_sha
        and draft_source.get("proposed_source_id") == source_id,
        "REVIEW_DRAFT_SOURCE_IDENTITY_MISMATCH",
    )
    _require(signoff.get("review_surface_sha256") == PILOT6_REVIEW_SURFACE_SHA256, "REVIEW_SURFACE_MISMATCH")

    claims = bundle.get("claims") or []
    _require(isinstance(claims, list), "BUNDLE_CLAIMS_INVALID")
    claim_ids = [claim.get("claim_id") for claim in claims]
    _require(len(claim_ids) == len(set(claim_ids)), "DUPLICATE_CLAIM_ID")
    _require(all(claim_id for claim_id in claim_ids), "CLAIM_ID_MISSING")
    _require(all(claim.get("source_id") == source_id for claim in claims), "CLAIM_SOURCE_ID_MISMATCH")
    draft_claims = review_draft.get("claims") or []
    _require([claim.get("claim_id") for claim in draft_claims] == claim_ids, "REVIEW_DRAFT_CLAIM_COVERAGE_MISMATCH")
    _require(all(claim.get("decision") == "PENDING" for claim in draft_claims), "GENERIC_REVIEW_DECISION_NOT_PENDING")
    _require(
        [_claim_projection(claim) for claim in draft_claims]
        == [_claim_projection(claim) for claim in claims],
        "REVIEW_DRAFT_IMMUTABLE_PROJECTION_MISMATCH",
    )

    result = boundary.get("result") or {}
    eligible_ids = result.get("review_eligible_claim_ids") or []
    ineligible_ids = result.get("table_derived_ineligible_claim_ids") or []
    _require(result.get("raw_claims") == len(claims), "RAW_CLAIM_COUNT_MISMATCH")
    _require(result.get("review_eligible_claims") == len(eligible_ids), "ELIGIBLE_CLAIM_COUNT_MISMATCH")
    _require(result.get("table_derived_claims_ineligible") == len(ineligible_ids), "INELIGIBLE_CLAIM_COUNT_MISMATCH")
    _require(len(eligible_ids) == len(set(eligible_ids)), "DUPLICATE_ELIGIBLE_CLAIM_ID")
    _require(len(ineligible_ids) == len(set(ineligible_ids)), "DUPLICATE_INELIGIBLE_CLAIM_ID")
    _require(not set(eligible_ids).intersection(ineligible_ids), "CLAIM_ADMISSION_PARTITION_OVERLAP")
    _require(set(eligible_ids).union(ineligible_ids) == set(claim_ids), "CLAIM_ADMISSION_PARTITION_MISMATCH")
    _require([claim_id for claim_id in claim_ids if claim_id in set(eligible_ids)] == eligible_ids, "ELIGIBLE_CLAIM_ORDER_MISMATCH")
    _require([claim_id for claim_id in claim_ids if claim_id in set(ineligible_ids)] == ineligible_ids, "INELIGIBLE_CLAIM_ORDER_MISMATCH")

    decisions = result.get("decisions") or []
    _require([item.get("claim_id") for item in decisions] == claim_ids, "BOUNDARY_DECISION_COVERAGE_MISMATCH")
    claim_by_id = {claim["claim_id"]: claim for claim in claims}
    eligible_set = set(eligible_ids)
    for decision in decisions:
        claim_id = decision["claim_id"]
        claim = claim_by_id[claim_id]
        _require(decision.get("immutable_evidence_excerpt") == claim.get("evidence_excerpt"), f"IMMUTABLE_EVIDENCE_MISMATCH:{claim_id}")
        if claim_id in eligible_set:
            _require(decision.get("review_eligible") is True, f"INCORRECT_TABLE_DECISION:{claim_id}")
            _require(decision.get("eligibility_decision") != "TABLE_DERIVED_CLAIM_INELIGIBLE", f"INCORRECT_TABLE_DECISION:{claim_id}")
        else:
            _require(decision.get("review_eligible") is False, f"INCORRECT_TABLE_DECISION:{claim_id}")
            _require(decision.get("eligibility_decision") == "TABLE_DERIVED_CLAIM_INELIGIBLE", f"INCORRECT_TABLE_DECISION:{claim_id}")
            _require(decision.get("decision_reason") == "TABLE_DERIVED_CLAIM_INELIGIBLE", f"INCORRECT_TABLE_REASON:{claim_id}")

    projection_sha = canonical_sha256([_claim_projection(claim) for claim in claims])
    integrity = boundary.get("claim_integrity") or {}
    _require(integrity.get("raw_claim_projection_sha256") == projection_sha, "RAW_CLAIM_PROJECTION_MISMATCH")
    _require(integrity.get("rebound_claim_projection_sha256") == projection_sha, "REBOUND_CLAIM_PROJECTION_MISMATCH")
    _require(integrity.get("boundary_input_claim_projection_sha256") == projection_sha, "BOUNDARY_CLAIM_PROJECTION_MISMATCH")
    _require(integrity.get("raw_projection_unchanged") is True, "RAW_CLAIM_PROJECTION_CHANGED")
    _require(result.get("raw_claims_unchanged") is True, "RAW_CLAIMS_CHANGED")
    _require(result.get("raw_claims_sha256_pre") == result.get("raw_claims_sha256_post"), "RAW_CLAIM_HASH_CHANGED")

    review_claims = signoff.get("claims") or []
    reviewed_ids = [item.get("claim_id") for item in review_claims]
    _require(reviewed_ids == eligible_ids, "REVIEWER_SURFACE_MISMATCH")
    _require(all(item.get("decision") == "KEEP" for item in review_claims), "REVIEWER_DECISION_NOT_KEEP")
    _require(all(item.get("true_semantic_failure") is False for item in review_claims), "REVIEWER_SEMANTIC_FAILURE")
    _require(all(item.get("attribution_error") is False for item in review_claims), "REVIEWER_ATTRIBUTION_ERROR")
    review_result = signoff.get("result") or {}
    _require(signoff.get("review_denominator") == len(eligible_ids), "REVIEW_DENOMINATOR_MISMATCH")
    _require(review_result.get("keep") == len(eligible_ids) and review_result.get("drop") == 0, "REVIEW_RESULT_COUNT_MISMATCH")
    _require(review_result.get("pilot6_semantic_gate") == "PASS", "REVIEW_GATE_NOT_PASS")

    return {
        "run_id": run_id,
        "source_id": source_id,
        "source_sha256": source_sha,
        "artifact_hashes": hashes,
        "bundle": bundle,
        "boundary": boundary,
        "signoff": signoff,
        "review_draft": review_draft,
        "raw_claim_ids": claim_ids,
        "eligible_claim_ids": eligible_ids,
        "ineligible_claim_ids": ineligible_ids,
        "immutable_claim_projection_sha256": canonical_sha256(
            [_immutable_claim_projection(claim) for claim in claims]
        ),
        "counts": {
            "raw_claims": len(claim_ids),
            "table_ineligible": len(ineligible_ids),
            "admitted_review_surface": len(eligible_ids),
            "review_keep": len(review_claims),
            "executable_accepted_claims": len(eligible_ids),
        },
    }


def _readonly_uri(path: Path) -> str:
    return f"file:{Path(path).resolve().as_posix()}?mode=ro&immutable=1"


def connect_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(_readonly_uri(path), uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def sqlite_sidecars(path: Path) -> dict[str, bool]:
    path = Path(path)
    return {suffix: Path(f"{path}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal")}


def schema_sha256(connection: sqlite3.Connection) -> str:
    rows = [
        dict(row)
        for row in connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
    ]
    return canonical_sha256(rows)


def table_names(connection: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in table_names(connection)
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    return value


def database_rows(connection: sqlite3.Connection) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for table in table_names(connection):
        columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
        result[table] = {
            json.dumps(
                {column: _json_safe(row[column]) for column in columns},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for row in connection.execute(f'SELECT * FROM "{table}"')
        }
    return result


def semantic_snapshot(rows: Mapping[str, set[str]]) -> dict[str, dict[str, Any]]:
    return {
        table: {
            "count": len(values),
            "semantic_sha256": hashlib.sha256(("\n".join(sorted(values)) + "\n").encode("utf-8")).hexdigest(),
        }
        for table, values in sorted(rows.items())
    }


def database_identity(path: Path, *, require_no_sidecars: bool = True) -> dict[str, Any]:
    path = Path(path).resolve()
    _require(path.is_file(), f"DATABASE_MISSING:{path}")
    before_sha = sha256_file(path)
    before_sidecars = sqlite_sidecars(path)
    if require_no_sidecars:
        _require(not any(before_sidecars.values()), f"SQLITE_SIDECAR_PRESENT:{before_sidecars}")
    connection = connect_read_only(path)
    try:
        schema_version_row = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        _require(schema_version_row is not None, "SCHEMA_VERSION_MISSING")
        counts = table_counts(connection)
        schema_hash = schema_sha256(connection)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
        rows = database_rows(connection)
    finally:
        connection.close()
    after_sha = sha256_file(path)
    after_sidecars = sqlite_sidecars(path)
    _require(before_sha == after_sha, "READ_ONLY_IDENTITY_CHANGED_DATABASE")
    _require(before_sidecars == after_sidecars, "READ_ONLY_IDENTITY_CHANGED_SIDECARS")
    if require_no_sidecars:
        _require(not any(after_sidecars.values()), f"SQLITE_SIDECAR_CREATED:{after_sidecars}")
    _require(integrity == "ok", f"INTEGRITY_CHECK_FAILED:{integrity}")
    _require(not foreign_keys, f"FOREIGN_KEY_CHECK_FAILED:{foreign_keys}")
    return {
        "path": str(path),
        "sha256": before_sha,
        "schema_version": schema_version_row[0],
        "schema_sha256": schema_hash,
        "counts": counts,
        "sidecars": before_sidecars,
        "integrity": integrity,
        "foreign_key_violations": foreign_keys,
        "semantic_snapshot": semantic_snapshot(rows),
    }


def production_identity(path: Path) -> dict[str, Any]:
    return database_identity(path, require_no_sidecars=True)


def _artifact_inventory(converged: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": role, "sha256": digest}
        for role, digest in sorted((converged.get("artifact_hashes") or {}).items())
    ]


def _evidence_id(source_sha: str, claim: Mapping[str, Any]) -> str:
    return deterministic_id(
        "EVD",
        {
            "source_sha256": source_sha,
            "claim_id": claim.get("claim_id"),
            "evidence_pointer": claim.get("evidence_pointer"),
            "evidence_excerpt": claim.get("evidence_excerpt"),
            "phase3c_evidence": claim.get("phase3c_evidence"),
        },
    )


def _source_row(converged: Mapping[str, Any], frozen_timestamp: str) -> dict[str, Any]:
    bundle = converged["bundle"]
    source = bundle["source"]
    reviewed = bundle.get("proposed_source_metadata") or {}
    archive_name = source["original_name"].replace("/", "_").replace("\\", "_")
    archive_path = f"archive/2026/09/02/{source['proposed_source_id']}__{archive_name}"
    metadata = {
        "summary": reviewed.get("summary") or "",
        "parse_diagnostics": source.get("parse_diagnostics") or {},
        "parse_warnings": source.get("parse_warnings") or [],
        "semantic_eligibility": source.get("semantic_eligibility") or {},
        "phase3d": {
            "source_run_id": converged["run_id"],
            "source_sha256": converged["source_sha256"],
            "input_artifacts": _artifact_inventory(converged),
            "archive_materialization": "REQUIRED_BEFORE_PRODUCTION_APPLY",
        },
    }
    return {
        "source_id": source["proposed_source_id"],
        "title": reviewed.get("title") or source["original_name"],
        "original_name": source["original_name"],
        "archived_path": archive_path,
        "sha256": source["sha256"],
        "ingestion_mode": source.get("analysis_mode") or "deep",
        "analysis_mode": source.get("analysis_mode") or "deep",
        "source_type": source.get("source_type") or "unknown",
        "source_rank": reviewed.get("source_rank") or "UNRANKED",
        "origin_type": reviewed.get("source_origin_type") or "unknown",
        "author": reviewed.get("author") or "",
        "organization": reviewed.get("organization") or "",
        "publication_time": reviewed.get("publication_time") or "",
        "ingested_at": frozen_timestamp,
        "status": "analyzed",
        "ima_media_id": "",
        "ima_kb_id": "",
        "underlying_source_id": "",
        "metadata_json": canonical_json_bytes(metadata).decode("utf-8"),
    }


def _claim_row(claim: Mapping[str, Any], frozen_timestamp: str) -> dict[str, Any]:
    return {
        "claim_id": claim["claim_id"],
        "statement": claim["statement"],
        "nature": claim["nature"],
        "fact_time": claim.get("fact_time") or "",
        "publication_time": claim.get("publication_time") or "",
        "ingestion_time": claim.get("ingestion_time") or frozen_timestamp,
        "source_id": claim["source_id"],
        "evidence_pointer": claim.get("evidence_pointer") or "",
        "evidence_excerpt": claim.get("evidence_excerpt") or "",
        "attributed_to": claim.get("attributed_to") or "",
        "scope": claim.get("scope") or "",
        "assumption_text": claim.get("assumption_text") or "",
        "status": claim.get("status") or "current",
        "confidence": claim.get("confidence"),
        "novelty_level": claim.get("novelty_level") or "N2",
        "structured_json": canonical_json_bytes(claim.get("structured") or {}).decode("utf-8"),
        "created_at": claim.get("created_at") or frozen_timestamp,
    }


def _candidate_refs(
    excerpt: str,
    accepted_claims: Sequence[Mapping[str, Any]],
    evidence_by_claim: Mapping[str, str],
) -> tuple[list[str], list[str]]:
    if not excerpt:
        return [], []
    claim_ids = [
        claim["claim_id"]
        for claim in accepted_claims
        if excerpt == (claim.get("evidence_excerpt") or "")
        or excerpt in (claim.get("evidence_excerpt") or "")
    ]
    return claim_ids, [evidence_by_claim[claim_id] for claim_id in claim_ids]


def _audit_node_operations(
    converged: Mapping[str, Any],
    accepted_claims: Sequence[Mapping[str, Any]],
    evidence_by_claim: Mapping[str, str],
) -> list[dict[str, Any]]:
    observations = converged["bundle"].get("observations") or {}
    operations: list[dict[str, Any]] = []

    def add(kind: str, index: int, candidate: Mapping[str, Any], operation: str, reason: str) -> None:
        candidate_id = deterministic_id(
            "CAND_NODE",
            {"run_id": converged["run_id"], "kind": kind, "index": index, "candidate": candidate},
        )
        excerpt = candidate.get("evidence_excerpt") or ""
        claim_refs, evidence_refs = _candidate_refs(excerpt, accepted_claims, evidence_by_claim)
        operations.append({
            "operation_id": deterministic_id("OP_NODE", {"candidate_id": candidate_id, "operation": operation}),
            "candidate_id": candidate_id,
            "candidate_kind": kind,
            "operation": operation,
            "executable": False,
            "candidate": copy.deepcopy(candidate),
            "claim_refs": claim_refs,
            "evidence_refs": evidence_refs,
            "source_sha256": converged["source_sha256"],
            "admission_state": "CLAIM_REVIEW_DOES_NOT_AUTHORIZE_NODE_MUTATION",
            "review_decision": "NOT_REVIEWED_FOR_NODE_OPERATION",
            "reason": reason,
        })

    for index, candidate in enumerate(observations.get("node_matches") or []):
        add("existing_node_match", index, candidate, "DEFER", "NO_EXPLICIT_NODE_REUSE_REVIEW")
    for index, candidate in enumerate(observations.get("node_candidates") or []):
        add("node_candidate", index, candidate, "DEFER", "NO_EXPLICIT_NODE_CREATE_OR_REUSE_REVIEW")
    for index, candidate in enumerate(observations.get("rejected_node_matches") or []):
        add("rejected_node_match", index, candidate, "REJECT", candidate.get("reason") or "PHASE3C_NODE_MATCH_REJECTED")
    for index, candidate in enumerate(observations.get("rejected_node_candidates") or []):
        validation = candidate.get("quality_validation") or {}
        reason = ",".join(validation.get("errors") or []) or "PHASE3C_NODE_CANDIDATE_REJECTED"
        add("rejected_node_candidate", index, candidate, "REJECT", reason)
    return operations


def _audit_relation_operations(converged: Mapping[str, Any]) -> list[dict[str, Any]]:
    observations = converged["bundle"].get("observations") or {}
    operations: list[dict[str, Any]] = []
    for index, candidate in enumerate(observations.get("relation_candidates") or []):
        candidate_id = deterministic_id(
            "CAND_REL", {"run_id": converged["run_id"], "kind": "relation_candidate", "index": index, "candidate": candidate}
        )
        operations.append({
            "operation_id": deterministic_id("OP_REL", {"candidate_id": candidate_id, "operation": "DEFER"}),
            "candidate_id": candidate_id,
            "operation": "DEFER",
            "executable": False,
            "candidate": copy.deepcopy(candidate),
            "claim_refs": copy.deepcopy(candidate.get("supporting_claim_refs") or []),
            "evidence_refs": [],
            "source_sha256": converged["source_sha256"],
            "review_decision": "NOT_REVIEWED_FOR_RELATION_OPERATION",
            "reason": "NO_EXPLICIT_RELATION_OPERATION_REVIEW",
        })
    for index, rejected in enumerate(observations.get("rejected_relation_candidates") or []):
        candidate = rejected.get("candidate") or {}
        candidate_id = deterministic_id(
            "CAND_REL", {"run_id": converged["run_id"], "kind": "rejected_relation", "index": index, "candidate": rejected}
        )
        operations.append({
            "operation_id": deterministic_id("OP_REL", {"candidate_id": candidate_id, "operation": "REJECT"}),
            "candidate_id": candidate_id,
            "operation": "REJECT",
            "executable": False,
            "candidate": copy.deepcopy(candidate),
            "claim_refs": copy.deepcopy(candidate.get("supporting_claim_refs") or []),
            "evidence_refs": [],
            "source_sha256": converged["source_sha256"],
            "review_decision": "PHASE3C_VALIDATION_REJECTED",
            "reason": rejected.get("reason") or "PHASE3C_RELATION_REJECTED",
            "stage": rejected.get("stage") or "",
        })
    return operations


def build_promotion_payload(
    converged: Mapping[str, Any],
    production: Mapping[str, Any],
    *,
    repository_commit: str,
    frozen_timestamp: str | None = None,
) -> dict[str, Any]:
    counts = converged.get("counts") or {}
    _require(counts.get("raw_claims") == 107, "PILOT6_RAW_CLAIM_COUNT_NOT_107")
    _require(counts.get("table_ineligible") == 3, "PILOT6_TABLE_INELIGIBLE_COUNT_NOT_3")
    _require(counts.get("admitted_review_surface") == 104, "PILOT6_ADMITTED_COUNT_NOT_104")
    _require(counts.get("review_keep") == 104, "PILOT6_REVIEW_KEEP_COUNT_NOT_104")
    _require(counts.get("executable_accepted_claims") == 104, "PILOT6_EXECUTABLE_COUNT_NOT_104")
    _require(repository_commit, "REPOSITORY_COMMIT_MISSING")
    bundle = converged["bundle"]
    claims = bundle["claims"]
    claim_by_id = {claim["claim_id"]: claim for claim in claims}
    eligible_set = set(converged["eligible_claim_ids"])
    boundary_decisions = {
        item["claim_id"]: item for item in converged["boundary"]["result"]["decisions"]
    }
    review_decisions = {
        item["claim_id"]: item for item in converged["signoff"]["claims"]
    }
    if frozen_timestamp is None:
        frozen_timestamp = next(
            (claim.get("ingestion_time") for claim in claims if claim.get("ingestion_time")),
            "2026-09-02T00:00:00+08:00",
        )

    evidence = []
    evidence_by_claim: dict[str, str] = {}
    payload_claims = []
    intended_mutations: list[dict[str, Any]] = []
    source_row = _source_row(converged, frozen_timestamp)
    intended_mutations.append({
        "mutation_id": deterministic_id("MUT", {"table": "sources", "key": source_row["source_id"], "row": source_row}),
        "table": "sources",
        "operation": "INSERT",
        "key": {"source_id": source_row["source_id"]},
        "row": source_row,
        "authorized_by": "SOURCE_ACCEPTED_ARTIFACT_SET",
    })

    for claim in claims:
        claim_id = claim["claim_id"]
        evidence_id = _evidence_id(converged["source_sha256"], claim)
        evidence_by_claim[claim_id] = evidence_id
        evidence.append({
            "evidence_id": evidence_id,
            "claim_id": claim_id,
            "source_id": converged["source_id"],
            "source_sha256": converged["source_sha256"],
            "evidence_pointer": claim.get("evidence_pointer") or "",
            "evidence_excerpt": claim.get("evidence_excerpt") or "",
            "validation": copy.deepcopy(claim.get("validation") or {}),
            "phase3c_evidence": copy.deepcopy(claim.get("phase3c_evidence") or {}),
        })
        accepted = claim_id in eligible_set
        table_decision = boundary_decisions[claim_id]
        review = review_decisions.get(claim_id)
        claim_record = {
            "claim_id": claim_id,
            "source_id": converged["source_id"],
            "evidence_id": evidence_id,
            "immutable_projection": _immutable_claim_projection(claim),
            "immutable_projection_sha256": canonical_sha256(_immutable_claim_projection(claim)),
            "table_decision": {
                "review_eligible": table_decision.get("review_eligible"),
                "eligibility_decision": table_decision.get("eligibility_decision"),
                "decision_reason": table_decision.get("decision_reason"),
                "safety_boundary_version": table_decision.get("safety_boundary_version"),
            },
            "semantic_admission": "PILOT6_DELEGATED_REVIEW_PASS" if accepted else "TABLE_DERIVED_AUDIT_ONLY",
            "reviewer_decision": copy.deepcopy(review) if review else {
                "decision": "NOT_REVIEWED",
                "reason": "TABLE_DERIVED_CLAIM_INELIGIBLE",
            },
            "executable": accepted,
            "intended_row": _claim_row(claim, frozen_timestamp) if accepted else None,
        }
        payload_claims.append(claim_record)
        if accepted:
            row = claim_record["intended_row"]
            intended_mutations.append({
                "mutation_id": deterministic_id("MUT", {"table": "claims", "key": claim_id, "row": row}),
                "table": "claims",
                "operation": "INSERT",
                "key": {"claim_id": claim_id},
                "row": row,
                "authorized_by": claim_id,
            })

    accepted_claims = [claim_by_id[claim_id] for claim_id in converged["eligible_claim_ids"]]
    node_operations = _audit_node_operations(converged, accepted_claims, evidence_by_claim)
    relation_operations = _audit_relation_operations(converged)
    claim_exclusions = [
        {
            "object_type": "Claim",
            "object_id": claim_id,
            "operation": "REJECT",
            "reason": "TABLE_DERIVED_CLAIM_INELIGIBLE",
            "audit_only": True,
            "evidence_id": evidence_by_claim[claim_id],
        }
        for claim_id in converged["ineligible_claim_ids"]
    ]
    excluded_operations = claim_exclusions + [
        {"object_type": "Node", **copy.deepcopy(operation)}
        for operation in node_operations
        if not operation["executable"]
    ] + [
        {"object_type": "Relation", **copy.deepcopy(operation)}
        for operation in relation_operations
        if not operation["executable"]
    ]
    operation_inventory = {
        "node": {operation: sum(item["operation"] == operation for item in node_operations) for operation in sorted(SUPPORTED_OPERATIONS)},
        "relation": {operation: sum(item["operation"] == operation for item in relation_operations) for operation in sorted(SUPPORTED_OPERATIONS)},
    }
    body = {
        "document_type": DOCUMENT_TYPE,
        "payload_version": PAYLOAD_VERSION,
        "metadata": {
            "source_run_id": converged["run_id"],
            "repository_commit": repository_commit,
            "production_sha256": production["sha256"],
            "production_schema_version": production["schema_version"],
            "production_schema_sha256": production["schema_sha256"],
            "production_counts": copy.deepcopy(production["counts"]),
            "source_sha256": converged["source_sha256"],
            "input_artifact_roles_and_sha256": _artifact_inventory(converged),
            "review_surface_sha256": converged["signoff"]["review_surface_sha256"],
            "frozen_timestamp": frozen_timestamp,
        },
        "sources": [{
            "source_id": converged["source_id"],
            "source_sha256": converged["source_sha256"],
            "artifact_hashes": _artifact_inventory(converged),
            "archive_copy_intent": {
                "status": "REQUIRED_BEFORE_PRODUCTION_APPLY",
                "destination": source_row["archived_path"],
            },
            "intended_row": source_row,
        }],
        "evidence": evidence,
        "claims": payload_claims,
        "node_operations": node_operations,
        "relation_operations": relation_operations,
        "excluded_operations": excluded_operations,
        "intended_mutations": intended_mutations,
        "audit": {
            "artifact_convergence": copy.deepcopy(converged["counts"]),
            "immutable_claim_projection_sha256": converged["immutable_claim_projection_sha256"],
            "review_authority": copy.deepcopy(converged["signoff"].get("review_authority") or {}),
            "operation_inventory": operation_inventory,
            "generic_review_draft": {
                "status": converged["review_draft"]["status"],
                "claim_count": len(converged["review_draft"].get("claims") or []),
                "authorization_used": False,
                "reason": "DELEGATED_104_CLAIM_SIGNOFF_IS_THE_ACCEPTANCE_AUTHORITY",
            },
            "hard_blocks": [
                "CONFIGURED_PRODUCTION_WRITE",
                "UPDATE",
                "NON_STRUCTURAL_RELATION",
                "SCHEMA_MIGRATION",
                "IMA",
                "CURRENT_VIEW",
                "PROPOSAL_PROPAGATION",
                "LLM_DURING_APPLY",
            ],
        },
    }
    payload_hash = canonical_sha256(body)
    payload = {
        "document_type": body["document_type"],
        "payload_version": body["payload_version"],
        "payload_id": f"PROMO_{payload_hash[:16].upper()}",
        "payload_hash": payload_hash,
        **{key: value for key, value in body.items() if key not in {"document_type", "payload_version"}},
    }
    validate_payload(payload)
    return payload


def payload_semantic_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in payload.items() if key not in {"payload_id", "payload_hash"}}


def validate_payload(payload: Mapping[str, Any]) -> None:
    _require(payload.get("document_type") == DOCUMENT_TYPE, "PAYLOAD_DOCUMENT_TYPE_INVALID")
    _require(payload.get("payload_version") == PAYLOAD_VERSION, "PAYLOAD_VERSION_INVALID")
    semantic_hash = canonical_sha256(payload_semantic_body(payload))
    _require(payload.get("payload_hash") == semantic_hash, "PAYLOAD_HASH_MISMATCH")
    _require(payload.get("payload_id") == f"PROMO_{semantic_hash[:16].upper()}", "PAYLOAD_ID_MISMATCH")
    metadata = payload.get("metadata") or {}
    for field in (
        "repository_commit", "production_sha256", "production_schema_version",
        "production_schema_sha256", "production_counts", "source_sha256",
        "input_artifact_roles_and_sha256",
    ):
        _require(metadata.get(field) not in (None, "", []), f"PAYLOAD_BASELINE_FIELD_MISSING:{field}")
    mutations = payload.get("intended_mutations") or []
    mutation_ids = [item.get("mutation_id") for item in mutations]
    _require(len(mutation_ids) == len(set(mutation_ids)), "DUPLICATE_MUTATION_ID")
    mutation_authorities = {item.get("authorized_by") for item in mutations}
    for operation_type, operations in (
        ("NODE", payload.get("node_operations") or []),
        ("RELATION", payload.get("relation_operations") or []),
    ):
        for operation in operations:
            decision = operation.get("operation")
            _require(decision in SUPPORTED_OPERATIONS, f"UNSUPPORTED_OPERATION:{decision}")
            executable = bool(operation.get("executable"))
            if decision == "UPDATE" and executable:
                raise PromotionError("UPDATE_NOT_EXECUTABLE_IN_STAGE3D2")
            if decision in {"DEFER", "REJECT", "UPDATE"}:
                _require(not executable, f"AUDIT_ONLY_OPERATION_MARKED_EXECUTABLE:{decision}")
                _require(operation.get("operation_id") not in mutation_authorities, f"AUDIT_ONLY_OPERATION_HAS_MUTATION:{decision}")
            if executable:
                _require(decision in EXECUTABLE_OPERATIONS, f"OPERATION_NOT_EXECUTABLE:{decision}")
                if operation_type == "RELATION":
                    relation = operation.get("final_relation") or operation.get("candidate") or {}
                    _require(relation.get("relation_type") == "part_of", "NON_STRUCTURAL_RELATION_NOT_EXECUTABLE")
    executable_claims = [claim for claim in payload.get("claims") or [] if claim.get("executable")]
    claim_mutations = [item for item in mutations if item.get("table") == "claims"]
    _require(len(executable_claims) == len(claim_mutations), "EXECUTABLE_CLAIM_MUTATION_COUNT_MISMATCH")
    for mutation in mutations:
        _require(mutation.get("operation") == "INSERT", "UNSUPPORTED_DATABASE_MUTATION")
        _require(mutation.get("table") in {
            "sources", "claims", "nodes", "node_aliases", "source_node_links",
            "claim_node_links", "node_relations",
        }, f"MUTATION_TABLE_NOT_ALLOWLISTED:{mutation.get('table')}")
        _require(isinstance(mutation.get("key"), dict) and mutation["key"], "MUTATION_KEY_MISSING")
        _require(isinstance(mutation.get("row"), dict) and mutation["row"], "MUTATION_ROW_MISSING")


def build_identity_catalog(
    nodes: Iterable[Mapping[str, Any]], aliases: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    node_rows = [dict(row) for row in nodes]
    alias_rows = [dict(row) for row in aliases]
    catalogs: dict[str, dict[str, set[str]]] = {
        "exact_canonical": {}, "exact_alias": {}, "nocase": {}, "normalized": {},
    }

    def add(catalog: str, term: str, node_id: str) -> None:
        catalogs[catalog].setdefault(term, set()).add(node_id)

    for node in node_rows:
        term = node["canonical_name"]
        add("exact_canonical", term, node["node_id"])
        add("nocase", sqlite_nocase(term), node["node_id"])
        add("normalized", nfkc_casefold(term), node["node_id"])
    for alias in alias_rows:
        term = alias["alias"]
        add("exact_alias", term, alias["node_id"])
        add("nocase", sqlite_nocase(term), alias["node_id"])
        add("normalized", nfkc_casefold(term), alias["node_id"])
    return {
        "nodes": {node["node_id"]: node for node in node_rows},
        "aliases": alias_rows,
        **catalogs,
    }


def resolve_identity(catalog: Mapping[str, Any], term: str) -> dict[str, Any]:
    exact_canonical = set((catalog.get("exact_canonical") or {}).get(term, set()))
    exact_alias = set((catalog.get("exact_alias") or {}).get(term, set()))
    nocase = set((catalog.get("nocase") or {}).get(sqlite_nocase(term), set()))
    normalized = set((catalog.get("normalized") or {}).get(nfkc_casefold(term), set()))
    all_ids = exact_canonical | exact_alias | nocase | normalized
    return {
        "term": term,
        "exact_canonical_ids": sorted(exact_canonical),
        "exact_alias_ids": sorted(exact_alias),
        "sqlite_nocase_ids": sorted(nocase),
        "nfkc_casefold_ids": sorted(normalized),
        "all_ids": sorted(all_ids),
    }


def decide_node_operation(
    candidate: Mapping[str, Any],
    *,
    requested_operation: str,
    review_decision: str,
    catalog: Mapping[str, Any],
    run_id: str,
) -> dict[str, Any]:
    _require(requested_operation in SUPPORTED_OPERATIONS, f"UNSUPPORTED_OPERATION:{requested_operation}")
    candidate_id = candidate.get("candidate_id") or deterministic_id("CAND_NODE", {"run_id": run_id, "candidate": candidate})
    base = {
        "operation_id": deterministic_id("OP_NODE", {"candidate_id": candidate_id, "requested": requested_operation}),
        "candidate_id": candidate_id,
        "candidate": copy.deepcopy(dict(candidate)),
        "claim_refs": copy.deepcopy(candidate.get("claim_refs") or []),
        "evidence_refs": copy.deepcopy(candidate.get("evidence_refs") or []),
        "review_decision": review_decision,
    }
    if requested_operation in {"DEFER", "REJECT"}:
        return {**base, "operation": requested_operation, "executable": False, "reason": candidate.get("reason") or requested_operation}
    if requested_operation == "UPDATE":
        return {**base, "operation": "UPDATE", "executable": False, "reason": "STAGE3D2_UPDATE_BLOCKED"}
    canonical_name = str(candidate.get("canonical_name") or "").strip()
    primary_type = str(candidate.get("primary_type") or "").strip()
    _require(canonical_name and primary_type, "NODE_CANDIDATE_IDENTITY_MISSING")
    if requested_operation == "CREATE":
        _require(review_decision == "APPROVE_CREATE", "NODE_CREATE_NOT_EXPLICITLY_REVIEWED")
        timestamp = candidate.get("frozen_timestamp") or "1970-01-01T00:00:00+00:00"
        node_id = candidate.get("node_id") or deterministic_id(
            "NODE", {"run_id": run_id, "canonical_name": canonical_name, "primary_type": primary_type}
        )
        aliases = sorted({str(alias).strip() for alias in candidate.get("aliases") or [] if str(alias).strip() and str(alias).strip() != canonical_name})
        return {
            **base,
            "operation": "CREATE",
            "executable": True,
            "reason": "EXPLICIT_NODE_CREATE_REVIEW",
            "aliases": aliases,
            "final_node": {
                "node_id": node_id,
                "canonical_name": canonical_name,
                "primary_type": primary_type,
                "description": candidate.get("description") or "",
                "status": "active",
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        }
    _require(review_decision == "APPROVE_REUSE", "NODE_REUSE_NOT_EXPLICITLY_REVIEWED")
    match_term = str(candidate.get("match_term") or canonical_name).strip()
    resolution = resolve_identity(catalog, match_term)
    if len(resolution["all_ids"]) != 1:
        return {
            **base,
            "operation": "DEFER",
            "executable": False,
            "reason": "ZERO_MATCH_REUSE" if not resolution["all_ids"] else "AMBIGUOUS_REUSE",
            "resolution": resolution,
        }
    target_id = resolution["all_ids"][0]
    target = (catalog.get("nodes") or {}).get(target_id)
    if not target or target.get("status") != "active" or target.get("primary_type") != primary_type:
        return {
            **base,
            "operation": "DEFER",
            "executable": False,
            "reason": "REUSE_TARGET_INACTIVE_OR_TYPE_INCOMPATIBLE",
            "resolution": resolution,
        }
    return {
        **base,
        "operation": "REUSE",
        "executable": True,
        "reason": "EXPLICIT_NODE_REUSE_REVIEW",
        "resolution": resolution,
        "resolved_target_id": target_id,
        "expected_target": {
            "node_id": target_id,
            "canonical_name": target["canonical_name"],
            "primary_type": target["primary_type"],
            "status": target["status"],
        },
        "approved_aliases": sorted({str(alias).strip() for alias in candidate.get("approved_aliases") or [] if str(alias).strip()}),
    }


def _catalog_from_connection(connection: sqlite3.Connection) -> dict[str, Any]:
    nodes = [dict(row) for row in connection.execute("SELECT node_id,canonical_name,primary_type,status FROM nodes")]
    aliases = [dict(row) for row in connection.execute("SELECT alias,node_id FROM node_aliases")]
    return build_identity_catalog(nodes, aliases)


def validate_executable_operations(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> None:
    validate_payload(payload)
    catalog = _catalog_from_connection(connection)
    package_terms: dict[str, str] = {}
    created_ids: set[str] = set()
    for operation in payload.get("node_operations") or []:
        if not operation.get("executable"):
            continue
        decision = operation["operation"]
        if decision == "CREATE":
            node = operation.get("final_node") or {}
            node_id = node.get("node_id")
            _require(node_id and node_id not in created_ids, f"PACKAGE_NODE_ID_COLLISION:{node_id}")
            created_ids.add(node_id)
            _require(node_id not in (catalog.get("nodes") or {}), f"NODE_ID_COLLISION:{node_id}")
            terms = [node.get("canonical_name")] + list(operation.get("aliases") or [])
            for index, term in enumerate(terms):
                _require(isinstance(term, str) and term.strip(), "NODE_IDENTITY_TERM_MISSING")
                resolution = resolve_identity(catalog, term)
                if resolution["all_ids"]:
                    code = "CANONICAL_COLLISION" if index == 0 else "ALIAS_COLLISION"
                    raise PromotionError(f"{code}:{term}")
                normalized = nfkc_casefold(term)
                owner = package_terms.get(normalized)
                _require(owner in (None, node_id), f"PACKAGE_INTERNAL_COLLISION:{term}")
                package_terms[normalized] = node_id
        elif decision == "REUSE":
            target_id = operation.get("resolved_target_id")
            target = (catalog.get("nodes") or {}).get(target_id)
            expected = operation.get("expected_target") or {}
            _require(target is not None, f"REUSE_TARGET_MISSING:{target_id}")
            _require(
                all(target.get(field) == expected.get(field) for field in ("node_id", "canonical_name", "primary_type", "status")),
                f"REUSE_TARGET_DRIFT:{target_id}",
            )
            _require(target.get("status") == "active", f"REUSE_TARGET_INACTIVE:{target_id}")
            candidate_type = (operation.get("candidate") or {}).get("primary_type")
            _require(not candidate_type or candidate_type == target.get("primary_type"), f"REUSE_TARGET_TYPE_INCOMPATIBLE:{target_id}")
            resolution = resolve_identity(catalog, (operation.get("resolution") or {}).get("term") or target["canonical_name"])
            _require(resolution["all_ids"] == [target_id], f"REUSE_RESOLUTION_DRIFT:{target_id}")
            for alias in operation.get("approved_aliases") or []:
                owners = resolve_identity(catalog, alias)["all_ids"]
                _require(not owners or owners == [target_id], f"ALIAS_COLLISION:{alias}")
        else:
            raise PromotionError(f"UNSUPPORTED_EXECUTABLE_NODE_OPERATION:{decision}")

    executable_relations = [item for item in payload.get("relation_operations") or [] if item.get("executable")]
    final_node_ids = set((catalog.get("nodes") or {})) | created_ids
    current_edges = {
        (row[0], row[1], row[2], row[3])
        for row in connection.execute(
            "SELECT from_node_id,relation_type,to_node_id,scope FROM node_relations WHERE status='current'"
        )
    }
    part_of_edges = {(edge[0], edge[2]) for edge in current_edges if edge[1] == "part_of"}
    for operation in executable_relations:
        relation = operation.get("final_relation") or {}
        _require(operation.get("operation") in EXECUTABLE_OPERATIONS, "RELATION_OPERATION_NOT_EXECUTABLE")
        _require(relation.get("relation_type") == "part_of", "NON_STRUCTURAL_RELATION_NOT_EXECUTABLE")
        source_id = relation.get("from_node_id")
        target_id = relation.get("to_node_id")
        _require(source_id in final_node_ids and target_id in final_node_ids, "RELATION_ENDPOINT_MISSING")
        _require(source_id != target_id, "RELATION_SELF_LOOP")
        edge = (source_id, "part_of", target_id, relation.get("scope") or "")
        _require(edge not in current_edges, "RELATION_DUPLICATE")
        graph: dict[str, set[str]] = {}
        for start, end in part_of_edges:
            graph.setdefault(start, set()).add(end)

        def reachable(start: str, destination: str) -> bool:
            pending = [start]
            seen: set[str] = set()
            while pending:
                current = pending.pop()
                if current == destination:
                    return True
                if current in seen:
                    continue
                seen.add(current)
                pending.extend(graph.get(current, ()))
            return False

        _require(not reachable(target_id, source_id), "RELATION_CYCLE")
        _require(not reachable(source_id, target_id), "RELATION_TRANSITIVE_REDUNDANCY")
        graph.setdefault(source_id, set()).add(target_id)
        part_of_edges.add((source_id, target_id))


def _paths_equivalent(first: Path, second: Path) -> bool:
    first = Path(first)
    second = Path(second)
    if first.resolve() == second.resolve():
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError:
        return False


def assert_shadow_target(shadow_path: Path, configured_production_path: Path) -> None:
    _require(
        not _paths_equivalent(shadow_path, configured_production_path),
        "CONFIGURED_PRODUCTION_WRITE_BLOCKED",
    )


def copy_production_to_shadow(production_path: Path, shadow_path: Path, expected_sha256: str) -> str:
    production_path = Path(production_path).resolve()
    shadow_path = Path(shadow_path).resolve()
    assert_shadow_target(shadow_path, production_path)
    _require(not shadow_path.exists(), f"SHADOW_TARGET_ALREADY_EXISTS:{shadow_path}")
    _require(sha256_file(production_path) == expected_sha256, "PRODUCTION_SHA_MISMATCH_BEFORE_COPY")
    _require(not any(sqlite_sidecars(production_path).values()), "PRODUCTION_SIDECAR_PRESENT_BEFORE_COPY")
    shadow_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(production_path, shadow_path)
    shadow_sha = sha256_file(shadow_path)
    _require(shadow_sha == expected_sha256, "SHADOW_PRE_SHA_MISMATCH")
    _require(sha256_file(production_path) == expected_sha256, "PRODUCTION_CHANGED_DURING_COPY")
    _require(not any(sqlite_sidecars(production_path).values()), "PRODUCTION_SIDECAR_CREATED_DURING_COPY")
    return shadow_sha


def _row_for_key(connection: sqlite3.Connection, table: str, key: Mapping[str, Any]) -> dict[str, Any] | None:
    where = " AND ".join(f'"{column}"=?' for column in key)
    row = connection.execute(
        f'SELECT * FROM "{table}" WHERE {where}', tuple(key.values())
    ).fetchone()
    return dict(row) if row is not None else None


def _row_equal(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    if set(actual) != set(expected):
        return False
    for field, expected_value in expected.items():
        actual_value = actual[field]
        if field.endswith("_json"):
            try:
                if json.loads(actual_value or "{}") != json.loads(expected_value or "{}"):
                    return False
                continue
            except (TypeError, json.JSONDecodeError):
                pass
        if actual_value != expected_value:
            return False
    return True


def _expected_replay_counts(payload: Mapping[str, Any]) -> dict[str, int]:
    counts = dict((payload.get("metadata") or {}).get("production_counts") or {})
    for mutation in payload.get("intended_mutations") or []:
        counts[mutation["table"]] = counts.get(mutation["table"], 0) + 1
    return counts


def _replay_state(connection: sqlite3.Connection, payload: Mapping[str, Any]) -> str:
    present = 0
    for mutation in payload.get("intended_mutations") or []:
        actual = _row_for_key(connection, mutation["table"], mutation["key"])
        if actual is None:
            continue
        present += 1
        if not _row_equal(actual, mutation["row"]):
            return "CONFLICT"
    if present == 0:
        return "NEW"
    if present != len(payload.get("intended_mutations") or []):
        return "CONFLICT"
    if table_counts(connection) != _expected_replay_counts(payload):
        return "CONFLICT"
    return "ALREADY_APPLIED"


def _write_authorizer(allowed_tables: set[str]):
    forbidden = {
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_REINDEX,
        sqlite3.SQLITE_ANALYZE,
    }

    def authorize(action: int, arg1: str | None, _arg2: str | None, _db: str | None, _trigger: str | None) -> int:
        if action == sqlite3.SQLITE_INSERT:
            return sqlite3.SQLITE_OK if arg1 in allowed_tables else sqlite3.SQLITE_DENY
        if action in forbidden:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    return authorize


def _insert_mutation(connection: sqlite3.Connection, mutation: Mapping[str, Any]) -> None:
    table = mutation["table"]
    row = mutation["row"]
    columns = list(row)
    placeholders = ",".join("?" for _ in columns)
    column_sql = ",".join(f'"{column}"' for column in columns)
    connection.execute(
        f'INSERT INTO "{table}"({column_sql}) VALUES({placeholders})',
        tuple(row[column] for column in columns),
    )


def _diff_rows(before: Mapping[str, set[str]], after: Mapping[str, set[str]]) -> dict[str, Any]:
    changed: dict[str, Any] = {}
    for table in sorted(set(before) | set(after)):
        before_values = before.get(table, set())
        after_values = after.get(table, set())
        added = after_values - before_values
        removed = before_values - after_values
        if added or removed:
            changed[table] = {"added": sorted(added), "removed": sorted(removed)}
    return changed


def apply_payload_to_shadow(
    payload: Mapping[str, Any],
    shadow_path: Path,
    configured_production_path: Path,
    *,
    inject_failure_after: int | None = None,
) -> dict[str, Any]:
    """Apply only to an explicit shadow. Configured Production is unconditionally blocked."""
    validate_payload(payload)
    shadow_path = Path(shadow_path).resolve()
    configured_production_path = Path(configured_production_path).resolve()
    assert_shadow_target(shadow_path, configured_production_path)
    _require(shadow_path.is_file(), "SHADOW_DATABASE_MISSING")
    pre_sha = sha256_file(shadow_path)
    connection = sqlite3.connect(shadow_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        schema_version = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        _require(schema_version == payload["metadata"]["production_schema_version"], "SHADOW_SCHEMA_VERSION_MISMATCH")
        _require(schema_sha256(connection) == payload["metadata"]["production_schema_sha256"], "SHADOW_SCHEMA_HASH_MISMATCH")
        replay_state = _replay_state(connection, payload)
        if replay_state == "CONFLICT":
            raise PromotionError("PAYLOAD_REPLAY_CONFLICT")
        if replay_state == "ALREADY_APPLIED":
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
            _require(integrity == "ok" and not foreign_keys, "IDEMPOTENT_REPLAY_DATABASE_INVALID")
            return {
                "status": "ALREADY_APPLIED",
                "idempotent": True,
                "shadow_pre_sha256": pre_sha,
                "shadow_post_sha256": pre_sha,
                "changed_tables": {},
                "foreign_key_violations": foreign_keys,
                "integrity": integrity,
            }
        _require(pre_sha == payload["metadata"]["production_sha256"], "SHADOW_NOT_EXACT_PRODUCTION_BASELINE")
        _require(table_counts(connection) == payload["metadata"]["production_counts"], "SHADOW_BASELINE_COUNTS_MISMATCH")
        validate_executable_operations(connection, payload)
        before_rows = database_rows(connection)
        allowed_tables = {mutation["table"] for mutation in payload["intended_mutations"]}
        connection.set_authorizer(_write_authorizer(allowed_tables))
        connection.execute("BEGIN IMMEDIATE")
        try:
            for index, mutation in enumerate(payload["intended_mutations"], start=1):
                _insert_mutation(connection, mutation)
                if inject_failure_after is not None and index == inject_failure_after:
                    raise PromotionError("INJECTED_TRANSACTION_FAILURE")
            connection.set_authorizer(None)
            foreign_keys = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            _require(not foreign_keys, f"SHADOW_FOREIGN_KEY_CHECK_FAILED:{foreign_keys}")
            _require(integrity == "ok", f"SHADOW_INTEGRITY_CHECK_FAILED:{integrity}")
            connection.commit()
        except Exception:
            connection.set_authorizer(None)
            connection.rollback()
            raise
        after_rows = database_rows(connection)
    finally:
        connection.close()

    changed = _diff_rows(before_rows, after_rows)
    _require(set(changed) == allowed_tables, f"UNEXPECTED_CHANGED_TABLES:{sorted(changed)}")
    expected_added: dict[str, set[str]] = {table: set() for table in allowed_tables}
    for mutation in payload["intended_mutations"]:
        expected_added[mutation["table"]].add(
            json.dumps(mutation["row"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
    for table, delta in changed.items():
        _require(not delta["removed"], f"UNEXPECTED_ROW_REMOVAL:{table}")
        _require(set(delta["added"]) == expected_added[table], f"UNEXPECTED_ROW_DELTA:{table}")
    post = database_identity(shadow_path, require_no_sidecars=True)
    return {
        "status": "COMMITTED",
        "idempotent": False,
        "shadow_pre_sha256": pre_sha,
        "shadow_post_sha256": post["sha256"],
        "changed_tables": {
            table: {"added": len(delta["added"]), "removed": len(delta["removed"])}
            for table, delta in changed.items()
        },
        "foreign_key_violations": post["foreign_key_violations"],
        "integrity": post["integrity"],
        "post_counts": post["counts"],
        "post_semantic_snapshot": post["semantic_snapshot"],
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def qualify_shadow_promotion(
    payload: Mapping[str, Any],
    *,
    production_path: Path,
    shadow_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    validate_payload(payload)
    production_path = Path(production_path).resolve()
    shadow_path = Path(shadow_path).resolve()
    receipt_path = Path(receipt_path).resolve()
    assert_shadow_target(shadow_path, production_path)
    production_pre = production_identity(production_path)
    _require(production_pre["sha256"] == payload["metadata"]["production_sha256"], "PRODUCTION_PAYLOAD_SHA_MISMATCH")
    _require(production_pre["schema_version"] == payload["metadata"]["production_schema_version"], "PRODUCTION_PAYLOAD_SCHEMA_VERSION_MISMATCH")
    _require(production_pre["schema_sha256"] == payload["metadata"]["production_schema_sha256"], "PRODUCTION_PAYLOAD_SCHEMA_HASH_MISMATCH")
    _require(production_pre["counts"] == payload["metadata"]["production_counts"], "PRODUCTION_PAYLOAD_COUNTS_MISMATCH")

    shadow_pre_sha = copy_production_to_shadow(production_path, shadow_path, production_pre["sha256"])
    apply_result = apply_payload_to_shadow(payload, shadow_path, production_path)
    replay_result = apply_payload_to_shadow(payload, shadow_path, production_path)
    _require(replay_result["status"] == "ALREADY_APPLIED", "IDEMPOTENT_REPLAY_FAILED")

    rollback_shadow = shadow_path.with_name(f"{shadow_path.stem}_rollback{shadow_path.suffix}")
    rollback_pre_sha = copy_production_to_shadow(production_path, rollback_shadow, production_pre["sha256"])
    rollback_before = database_identity(rollback_shadow, require_no_sidecars=True)
    rollback_error = ""
    try:
        apply_payload_to_shadow(payload, rollback_shadow, production_path, inject_failure_after=2)
    except PromotionError as exc:
        rollback_error = str(exc)
    _require(rollback_error == "INJECTED_TRANSACTION_FAILURE", "ROLLBACK_INJECTION_NOT_OBSERVED")
    rollback_after = database_identity(rollback_shadow, require_no_sidecars=True)
    rollback_pass = rollback_before["semantic_snapshot"] == rollback_after["semantic_snapshot"]
    _require(rollback_pass, "TRANSACTION_ROLLBACK_SEMANTIC_MISMATCH")

    restore_shadow = shadow_path.with_name(f"{shadow_path.stem}_restore{shadow_path.suffix}")
    restore_backup = shadow_path.with_name(f"{shadow_path.stem}_restore_backup{shadow_path.suffix}")
    copy_production_to_shadow(production_path, restore_shadow, production_pre["sha256"])
    copy_production_to_shadow(production_path, restore_backup, production_pre["sha256"])
    apply_payload_to_shadow(payload, restore_shadow, production_path)
    shutil.copyfile(restore_backup, restore_shadow)
    restore_identity = database_identity(restore_shadow, require_no_sidecars=True)
    restore_pass = (
        restore_identity["sha256"] == production_pre["sha256"]
        and restore_identity["semantic_snapshot"] == production_pre["semantic_snapshot"]
        and restore_identity["integrity"] == "ok"
        and not restore_identity["foreign_key_violations"]
    )
    _require(restore_pass, "RESTORE_DRILL_FAILED")

    production_post = production_identity(production_path)
    production_unchanged = (
        production_pre["sha256"] == production_post["sha256"]
        and production_pre["semantic_snapshot"] == production_post["semantic_snapshot"]
        and production_pre["sidecars"] == production_post["sidecars"]
    )
    _require(production_unchanged, "PRODUCTION_CHANGED_DURING_QUALIFICATION")
    receipt = {
        "document_type": QUALIFICATION_DOCUMENT_TYPE,
        "receipt_version": "1",
        "receipt_time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS",
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "artifact_convergence": copy.deepcopy(payload["audit"]["artifact_convergence"]),
        "operation_inventory": copy.deepcopy(payload["audit"]["operation_inventory"]),
        "production": {
            "pre_sha256": production_pre["sha256"],
            "post_sha256": production_post["sha256"],
            "schema_version": production_pre["schema_version"],
            "schema_sha256": production_pre["schema_sha256"],
            "counts": production_pre["counts"],
            "sidecars_pre": production_pre["sidecars"],
            "sidecars_post": production_post["sidecars"],
            "changed": False,
            "apply_attempted": False,
        },
        "shadow": {
            "path": str(shadow_path),
            "pre_sha256": shadow_pre_sha,
            "post_sha256": apply_result["shadow_post_sha256"],
            "changed_tables": apply_result["changed_tables"],
            "foreign_key_violations": apply_result["foreign_key_violations"],
            "integrity": apply_result["integrity"],
        },
        "idempotency": {
            "status": replay_result["status"],
            "pass": True,
            "unexpected_table_delta": replay_result["changed_tables"],
        },
        "rollback": {
            "transaction_failure": rollback_error,
            "pre_sha256": rollback_pre_sha,
            "semantic_state_restored": rollback_pass,
            "restore_drill_pass": restore_pass,
            "restored_sha256": restore_identity["sha256"],
            "status": "PASS",
        },
    }
    _write_json(receipt_path, receipt)
    return receipt
