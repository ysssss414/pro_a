from __future__ import annotations

import copy
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pro_a.production_promotion import (
    PromotionError,
    build_identity_catalog,
    canonical_sha256,
    connect_read_only,
    deterministic_id,
    nfkc_casefold,
    production_identity,
    resolve_identity,
    sha256_file,
    validate_payload,
)


REVIEW_DOCUMENT_TYPE = "phase3d3a_node_operation_review"
SOURCE_DOCUMENT_TYPE = "phase3d3a_source_materialization"
MANIFEST_DOCUMENT_TYPE = "phase3d3a_authorization_prep_manifest"
HUMAN_REVIEW_DOCUMENT_TYPE = "phase3d3b_human_node_operation_review"
HUMAN_MANIFEST_DOCUMENT_TYPE = "phase3d3b_human_review_manifest"
SCHEMA_VERSION = "1"

EXPECTED_DRAFT_REVIEW_ID = "NODE_REVIEW_457B1DB8E16AB858"
EXPECTED_DRAFT_REVIEW_SHA256 = "457b1db8e16ab8585ac8aede67b783a6139f55638d86a6958c967db73673bf37"
EXPECTED_PAYLOAD_ID = "PROMO_2938849C91722C57"
EXPECTED_PAYLOAD_SHA256 = "2938849c91722c578b11c18bf6056d46d906d4c1839707da3ae10f473c6a647d"
EXPECTED_SOURCE_SHA256 = "572a6df2b583358506e2a4fb86359a07e9a1503a3507dcdd2c81a8d97c27e97a"


_HUMAN_DECISION_ROWS = (
    (
        "CAND_NODE_26ED2DBD6A1442FC", "REUSE", "NODE_20260817_10A98F3C",
        "Unique active exact Standard target with admitted Claim support.",
    ),
    (
        "CAND_NODE_9D7AECC7ACD45CE2", "REUSE", "NODE_20260817_7C89CC59",
        "Unique active exact Standard target; CXL aliases resolve consistently.",
    ),
    (
        "CAND_NODE_E72587262796D0F0", "REUSE", "NODE_20260817_6A9A657D",
        "Unique active exact Product target with admitted Claim support.",
    ),
    (
        "CAND_NODE_B2346267C09BD58B", "REUSE", "NODE_20260817_DB4961DB",
        "Unique active exact Product target with admitted Claim support.",
    ),
    (
        "CAND_NODE_D165AC3C72E91B14", "DEFER", None,
        "Existing target is identifiable, but there is no deterministic admitted-Claim linkage in this promotion surface.",
    ),
    (
        "CAND_NODE_2778934D77829E1F", "REUSE", "NODE_20260817_23BDA593",
        "Unique active exact Product target with admitted Claim support.",
    ),
    (
        "CAND_NODE_7C4F495527737096", "CREATE", None,
        "Canonical Product concept is sufficiently supported. VPD should be treated as an alias of this Node. The separate VPD candidate is rejected as duplicate.",
    ),
    (
        "CAND_NODE_C195F1E21A50449B", "CREATE", None,
        "Valid generic Product concept with extensive admitted Claim support. SPD should be treated as an alias. A distinct DDR5-specific subtype is also justified.",
    ),
    (
        "CAND_NODE_B424F90448CCBA4B", "CREATE", None,
        "Stable Product category with extensive admitted Claim support and no Production collision.",
    ),
    (
        "CAND_NODE_334EE0153DF753B9", "DEFER", None,
        "Underlying Product concept is plausible, but proposed alias 温度传感器芯片 is too broad for global alias governance. Canonicalization/alias repair is required before CREATE.",
    ),
    (
        "CAND_NODE_58E875D3AA212A75", "CREATE", None,
        "Stable Product category with adequate admitted Claim support and no Production collision.",
    ),
    (
        "CAND_NODE_F539F80F27EFABDC", "DEFER", None,
        "Canonical Product concept is valid, but proposed alias 马达驱动芯片 is too broad. Alias repair is required before CREATE.",
    ),
    (
        "CAND_NODE_1BA93BFE9E4C7FD4", "DEFER", None,
        "No deterministic admitted-Claim linkage.",
    ),
    (
        "CAND_NODE_65B1EC90F3812AEE", "REJECT", None,
        "Research topic/question, not a canonical Node. Keep out of Node creation; use the ResearchQuestion layer if needed.",
    ),
    (
        "CAND_NODE_82778263B3EE6AAB", "REJECT", None,
        "Research topic/question, not a canonical Node. Keep out of Node creation; use the ResearchQuestion layer if needed.",
    ),
    (
        "CAND_NODE_D39B55382E6098D2", "DEFER", None,
        "Underlying Product concept may be valid, but current aliases conflate the EDSFF Standard with the Product category. Identity/alias repair is required.",
    ),
    (
        "CAND_NODE_43BE3226A7EACED0", "CREATE", None,
        "Valid generic CXL memory-module Product concept with admitted Claim support. Prefer this candidate over the duplicate English generic candidate.",
    ),
    (
        "CAND_NODE_9FC88732B95ABA3D", "CREATE", None,
        "Distinct DDR5-specific Product layer with multiple dedicated market, competition, and product Claims; not merely a duplicate of generic SPD芯片.",
    ),
    (
        "CAND_NODE_7DB06F5F691270CF", "DEFER", None,
        "Company identity is strongly supported, but proposed type Entity must be normalized to Company before canonical CREATE.",
    ),
    (
        "CAND_NODE_529AA01F61DD9AAE", "REJECT", None,
        "Duplicate of SPD芯片; SPD is an alias, not a second canonical Node.",
    ),
    (
        "CAND_NODE_935CA33A2E606936", "REJECT", None,
        "Duplicate of VPD芯片; VPD is an alias, not a second canonical Node.",
    ),
    (
        "CAND_NODE_F63C2FAB3DAF2CA5", "REUSE", "NODE_20260817_BEBBBC45",
        "Unique active exact Product target; Enterprise SSD/eSSD/企业级SSD identity is already canonicalized.",
    ),
    (
        "CAND_NODE_6236100CBA90F567", "REJECT", None,
        "Duplicates CXL内存模组. Proposed alias CMM-D incorrectly conflates Samsung's product family with the generic CXL memory-module category.",
    ),
    (
        "CAND_NODE_5542649664C089A4", "CREATE", None,
        "Stable Technology concept with direct admitted Claim support and no Production collision.",
    ),
    (
        "CAND_NODE_60282E35851EA5A9", "CREATE", None,
        "Clearly supported as an SNIA-defined Standard/form-factor specification; keep separate from EDSFF-based SSD products.",
    ),
    (
        "CAND_NODE_DA43E723E28FB27E", "DEFER", None,
        "Potential Theme, but only one admitted Claim supports it. Current evidence is insufficient to establish it as a stable canonical Theme rather than source-specific analytical framing.",
    ),
)

EXPECTED_CREATE_IDENTITIES = {
    "CAND_NODE_7C4F495527737096": ("VPD芯片", "Product"),
    "CAND_NODE_C195F1E21A50449B": ("SPD芯片", "Product"),
    "CAND_NODE_B424F90448CCBA4B": ("EEPROM", "Product"),
    "CAND_NODE_58E875D3AA212A75": ("NOR Flash", "Product"),
    "CAND_NODE_43BE3226A7EACED0": ("CXL内存模组", "Product"),
    "CAND_NODE_9FC88732B95ABA3D": ("DDR5 SPD芯片", "Product"),
    "CAND_NODE_5542649664C089A4": ("KV Cache", "Technology"),
    "CAND_NODE_60282E35851EA5A9": ("EDSFF", "Standard"),
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PromotionError(code)


def _source_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    validate_payload(payload)
    sources = payload.get("sources") or []
    _require(len(sources) == 1, "SOURCE_CONTRACT_COUNT_MISMATCH")
    source = sources[0]
    row = source.get("intended_row") or {}
    destination = (source.get("archive_copy_intent") or {}).get("destination")
    metadata = json.loads(row.get("metadata_json") or "{}")
    size = ((metadata.get("parse_diagnostics") or {}).get("file_size"))
    _require(source.get("source_id") and source.get("source_sha256"), "SOURCE_IDENTITY_MISSING")
    _require(row.get("original_name") and destination and size, "SOURCE_ARCHIVE_CONTRACT_MISSING")
    _require(row.get("sha256") == source.get("source_sha256"), "SOURCE_ROW_SHA_MISMATCH")
    _require(row.get("archived_path") == destination, "SOURCE_ARCHIVE_DESTINATION_MISMATCH")
    return {
        "source_id": source["source_id"],
        "original_name": row["original_name"],
        "expected_sha256": source["source_sha256"],
        "expected_size": size,
        "logical_destination": destination,
        "archive_filename": Path(destination).name,
    }


def prepare_source_materialization(
    payload: Mapping[str, Any],
    *,
    candidate_paths: Iterable[Path],
    production_root: Path,
    staging_root: Path,
    searched_locations: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify and optionally stage the exact source without touching Production."""
    contract = _source_contract(payload)
    production_root = Path(production_root).resolve()
    staging_root = Path(staging_root).resolve()
    real_destination = (production_root / contract["logical_destination"]).resolve()
    _require(
        real_destination == production_root or production_root in real_destination.parents,
        "SOURCE_ARCHIVE_DESTINATION_OUTSIDE_PRODUCTION_ROOT",
    )

    candidates: list[dict[str, Any]] = []
    exact_paths: list[Path] = []
    for raw_path in sorted({Path(path).resolve() for path in candidate_paths}, key=str):
        if not raw_path.is_file():
            candidates.append({"path": str(raw_path), "status": "NOT_A_FILE"})
            continue
        digest = sha256_file(raw_path)
        size = raw_path.stat().st_size
        name_match = raw_path.name == contract["original_name"]
        sha_match = digest == contract["expected_sha256"]
        size_match = size == contract["expected_size"]
        candidates.append({
            "path": str(raw_path),
            "filename_match": name_match,
            "sha256": digest,
            "sha_match": sha_match,
            "size": size,
            "size_match": size_match,
        })
        if sha_match and size_match:
            exact_paths.append(raw_path)

    resolved = exact_paths[0] if exact_paths else None
    if real_destination.is_file():
        real_sha = sha256_file(real_destination)
        collision = "IDENTICAL" if real_sha == contract["expected_sha256"] else "CONFLICT"
    elif real_destination.exists():
        real_sha = None
        collision = "CONFLICT_NON_FILE"
    else:
        real_sha = None
        collision = "ABSENT"

    staged_path: Path | None = None
    staged_sha: str | None = None
    method = "NOT_PERFORMED_SOURCE_MISSING"
    staged_copy_verified = False
    if resolved is not None:
        _require(collision in {"ABSENT", "IDENTICAL"}, "REAL_ARCHIVE_COLLISION_CONFLICT")
        staging_root.mkdir(parents=True, exist_ok=True)
        staged_path = staging_root / contract["archive_filename"]
        if staged_path.exists():
            _require(staged_path.is_file(), "STAGED_ARCHIVE_COLLISION_NON_FILE")
            _require(sha256_file(staged_path) == contract["expected_sha256"], "STAGED_ARCHIVE_COLLISION_CONFLICT")
            method = "VERIFIED_EXISTING_STAGED_COPY"
        else:
            shutil.copy2(resolved, staged_path)
            method = "DISPOSABLE_BYTE_COPY"
        staged_sha = sha256_file(staged_path)
        staged_copy_verified = staged_sha == contract["expected_sha256"]
        _require(staged_copy_verified, "STAGED_ARCHIVE_SHA_MISMATCH")

    ready = bool(resolved and staged_copy_verified and collision in {"ABSENT", "IDENTICAL"})
    return {
        "document_type": SOURCE_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "READY" if ready else "BLOCKED_SOURCE_MISSING",
        "source": copy.deepcopy(contract),
        "search": {
            "authoritative_condition": "candidate_file_sha256 == expected_source_sha256",
            "searched_locations": list(searched_locations),
            "candidate_results": candidates,
            "exact_match_count": len(exact_paths),
        },
        "resolved_source_path": str(resolved) if resolved else None,
        "resolved_source_sha256": contract["expected_sha256"] if resolved else None,
        "resolved_source_size": resolved.stat().st_size if resolved else None,
        "real_archive": {
            "path": str(real_destination),
            "collision_status": collision,
            "existing_sha256": real_sha,
            "mutated": False,
        },
        "materialization": {
            "method": method,
            "staged_path": str(staged_path) if staged_path else None,
            "staged_sha256": staged_sha,
            "staged_copy_verified": staged_copy_verified,
            "real_archive_copy_performed": False,
        },
        "flags": {
            "source_file_found": resolved is not None,
            "source_sha_match": resolved is not None,
            "source_archive_materialization_ready": ready,
            "production_changed": False,
            "production_apply_attempted": False,
        },
    }


def _load_catalog(production_path: Path) -> tuple[dict[str, Any], dict[str, list[str]]]:
    connection = connect_read_only(production_path)
    try:
        nodes = [
            dict(row)
            for row in connection.execute(
                "SELECT node_id,canonical_name,primary_type,status FROM nodes ORDER BY node_id"
            )
        ]
        aliases = [
            dict(row)
            for row in connection.execute(
                "SELECT alias,node_id FROM node_aliases ORDER BY alias,node_id"
            )
        ]
    finally:
        connection.close()
    aliases_by_node: dict[str, list[str]] = {}
    for alias in aliases:
        aliases_by_node.setdefault(alias["node_id"], []).append(alias["alias"])
    return build_identity_catalog(nodes, aliases), aliases_by_node


def _claim_text(claim: Mapping[str, Any]) -> str:
    projection = claim.get("immutable_projection") or {}
    return "\n".join((
        str(projection.get("statement") or ""),
        str(projection.get("evidence_excerpt") or ""),
    ))


def _supporting_claims(
    operation: Mapping[str, Any],
    claims: Sequence[Mapping[str, Any]],
    terms: Sequence[str],
    target_node_id: str | None,
) -> list[Mapping[str, Any]]:
    direct_ids = set(operation.get("claim_refs") or [])
    evidence_excerpt = str((operation.get("candidate") or {}).get("evidence_excerpt") or "").strip()
    normalized_terms = [nfkc_casefold(term) for term in terms if str(term).strip()]
    result: list[Mapping[str, Any]] = []
    for claim in claims:
        projection = claim.get("immutable_projection") or {}
        text = nfkc_casefold(_claim_text(claim))
        related_node_ids = set(projection.get("related_node_ids") or [])
        excerpt_match = bool(
            evidence_excerpt
            and (
                nfkc_casefold(evidence_excerpt) in text
                or text in nfkc_casefold(evidence_excerpt)
            )
        )
        if (
            claim.get("claim_id") in direct_ids
            or (target_node_id and target_node_id in related_node_ids)
            or any(term in text for term in normalized_terms)
            or excerpt_match
        ):
            result.append(claim)
    return result


def _candidate_term_owners(operations: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    owners: dict[str, set[str]] = {}
    for operation in operations:
        if operation.get("candidate_kind") != "node_candidate":
            continue
        candidate = operation.get("candidate") or {}
        terms = [candidate.get("canonical_name"), *(candidate.get("aliases") or [])]
        for term in terms:
            if str(term or "").strip():
                owners.setdefault(nfkc_casefold(str(term).strip()), set()).add(operation["candidate_id"])
    return {term: sorted(ids) for term, ids in owners.items() if len(ids) > 1}


def _resolution_summary(
    catalog: Mapping[str, Any], terms: Sequence[str]
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    term_results = [resolve_identity(catalog, term) for term in terms]
    exact_ids = sorted({
        node_id
        for result in term_results
        for node_id in result["exact_canonical_ids"] + result["exact_alias_ids"]
    })
    target_ids = sorted({node_id for result in term_results for node_id in result["all_ids"]})
    targets = [copy.deepcopy(catalog["nodes"][node_id]) for node_id in target_ids]
    return term_results, exact_ids, targets


def _suggest_operation(
    *,
    candidate_kind: str,
    candidate: Mapping[str, Any],
    support_count: int,
    exact_ids: Sequence[str],
    targets: Sequence[Mapping[str, Any]],
    internal_collisions: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    if support_count == 0:
        return "DEFER", "NO_DETERMINISTIC_ADMITTED_CLAIM_LINKAGE"
    active_targets = [target for target in targets if target.get("status") == "active"]
    proposed_type = candidate.get("primary_type")
    compatible = [target for target in active_targets if target.get("primary_type") == proposed_type]
    if len(exact_ids) == 1 and len(active_targets) == 1 and len(compatible) == 1 and not internal_collisions:
        return "REUSE", "UNIQUE_ACTIVE_EXACT_TYPE_COMPATIBLE_TARGET_WITH_CLAIM_SUPPORT"
    if exact_ids or targets:
        return "DEFER", "EXISTING_IDENTITY_OR_TYPE_RESOLUTION_REQUIRES_HUMAN_REVIEW"
    if internal_collisions:
        return "DEFER", "PACKAGE_INTERNAL_IDENTITY_COLLISION"
    if candidate_kind == "EXISTING_NODE_OBSERVATION":
        return "DEFER", "EXISTING_TARGET_DID_NOT_RESOLVE_EXACTLY"
    quality = candidate.get("quality_validation") or {}
    if candidate.get("primary_type") == "ResearchQuestion":
        return "DEFER", "RESEARCH_QUESTION_IS_NOT_AUTOMATICALLY_A_CANONICAL_NODE"
    if candidate.get("candidate_kind") != "normal" or candidate.get("quality_eligible") is not True or quality.get("eligible") is not True:
        return "DEFER", "CANDIDATE_QUALITY_NOT_SUFFICIENT_FOR_CREATE_SUGGESTION"
    return "CREATE", "NO_PRODUCTION_COLLISION_AND_QUALIFYING_ADMITTED_CLAIM_SUPPORT"


def _build_advisory_node_records(
    *,
    operations: Sequence[Mapping[str, Any]],
    claims: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    aliases_by_node: Mapping[str, Sequence[str]],
    source_run_id: str,
) -> list[dict[str, Any]]:
    """Apply the Stage 3D.3A resolution/suggestion logic to one review universe."""
    admitted_ids = {claim["claim_id"] for claim in claims}
    internal_owners = _candidate_term_owners(operations)
    records: list[dict[str, Any]] = []

    for operation in operations:
        candidate = operation.get("candidate") or {}
        if operation.get("candidate_kind") == "existing_node_match":
            candidate_kind = "EXISTING_NODE_OBSERVATION"
            target_node_id = candidate.get("node_id")
            _require(target_node_id in catalog["nodes"], f"EXISTING_NODE_TARGET_MISSING:{target_node_id}")
            target = catalog["nodes"][target_node_id]
            proposed_name = target["canonical_name"]
            proposed_type = target["primary_type"]
            terms = [proposed_name, *(aliases_by_node.get(target_node_id) or [])]
            suggestion_candidate = {**candidate, "primary_type": proposed_type}
            validation = candidate.get("validation") or {}
        else:
            candidate_kind = "NODE_CANDIDATE"
            target_node_id = None
            proposed_name = str(candidate.get("canonical_name") or "").strip()
            proposed_type = str(candidate.get("primary_type") or "").strip()
            _require(proposed_name and proposed_type, f"NODE_CANDIDATE_IDENTITY_MISSING:{operation.get('candidate_id')}")
            terms = [proposed_name, *(candidate.get("aliases") or [])]
            suggestion_candidate = candidate
            validation = candidate.get("quality_validation") or {}

        terms = list(dict.fromkeys(str(term).strip() for term in terms if str(term).strip()))
        supporting = _supporting_claims(operation, claims, terms, target_node_id)
        _require(
            set(operation.get("claim_refs") or []).issubset(admitted_ids),
            f"NODE_OPERATION_REFERENCES_INELIGIBLE_CLAIM:{operation.get('candidate_id')}",
        )
        term_results, exact_ids, targets = _resolution_summary(catalog, terms)
        collisions = [
            {"normalized_term": nfkc_casefold(term), "candidate_ids": internal_owners[nfkc_casefold(term)]}
            for term in terms
            if nfkc_casefold(term) in internal_owners
        ]
        prospective_node_id = deterministic_id(
            "NODE",
            {
                "source_run_id": source_run_id,
                "candidate_id": operation.get("candidate_id"),
                "canonical_name": proposed_name,
                "primary_type": proposed_type,
            },
        )
        suggestion, suggestion_reason = _suggest_operation(
            candidate_kind=candidate_kind,
            candidate=suggestion_candidate,
            support_count=len(supporting),
            exact_ids=exact_ids,
            targets=targets,
            internal_collisions=collisions,
        )
        evidence = []
        for claim in supporting[:5]:
            projection = claim["immutable_projection"]
            evidence.append({
                "claim_id": claim["claim_id"],
                "evidence_id": claim.get("evidence_id"),
                "statement": projection.get("statement"),
                "evidence_pointer": projection.get("evidence_pointer"),
                "evidence_excerpt": projection.get("evidence_excerpt"),
            })
        records.append({
            "operation_candidate_id": operation["candidate_id"],
            "source_operation_id": operation["operation_id"],
            "candidate_kind": candidate_kind,
            "proposed_name": proposed_name,
            "proposed_type": proposed_type,
            "proposed_aliases": terms[1:],
            "prospective_node_id": prospective_node_id,
            "supporting_claim_ids": [claim["claim_id"] for claim in supporting],
            "supporting_evidence": evidence,
            "phase3c_validation_state": copy.deepcopy(validation),
            "current_defer_reason": operation.get("reason"),
            "exact_production_resolution": {
                "terms": term_results,
                "exact_target_node_ids": exact_ids,
                "candidate_target_node_ids": [target["node_id"] for target in targets],
                "candidate_targets": targets,
            },
            "collision_diagnostics": {
                "prospective_node_id_exists": prospective_node_id in catalog["nodes"],
                "package_internal_normalized_term_collisions": collisions,
                "production_nocase_or_nfkc_target_ids": sorted({
                    node_id for result in term_results for node_id in result["all_ids"]
                }),
            },
            "suggested_operation": suggestion,
            "suggestion_reason": suggestion_reason,
            "advisory_only": True,
            "review_decision": "PENDING",
            "reviewer": None,
            "review_reason": None,
        })
    return records


def build_node_operation_review(
    payload: Mapping[str, Any], production_path: Path
) -> dict[str, Any]:
    """Build the deterministic advisory surface; never authorize an operation."""
    validate_payload(payload)
    baseline = production_identity(production_path)
    metadata = payload.get("metadata") or {}
    _require(baseline["sha256"] == metadata.get("production_sha256"), "PRODUCTION_BASELINE_SHA_MISMATCH")
    _require(baseline["schema_sha256"] == metadata.get("production_schema_sha256"), "PRODUCTION_BASELINE_SCHEMA_MISMATCH")
    _require(baseline["counts"] == metadata.get("production_counts"), "PRODUCTION_BASELINE_COUNTS_MISMATCH")

    node_operations = payload.get("node_operations") or []
    deferred = [operation for operation in node_operations if operation.get("operation") == "DEFER"]
    rejected = [operation for operation in node_operations if operation.get("operation") == "REJECT"]
    relations = payload.get("relation_operations") or []
    relation_rejects = [operation for operation in relations if operation.get("operation") == "REJECT"]
    _require(len(deferred) == 26, "NODE_DEFER_UNIVERSE_MISMATCH")
    _require(len(rejected) == 32, "NODE_REJECT_UNIVERSE_MISMATCH")
    _require(len(relations) == len(relation_rejects) == 10, "RELATION_REJECT_UNIVERSE_MISMATCH")
    _require(all(not operation.get("executable") for operation in deferred + rejected + relation_rejects), "NONEXECUTABLE_OPERATION_BECAME_EXECUTABLE")

    claims = [claim for claim in payload.get("claims") or [] if claim.get("executable") is True]
    _require(len(claims) == 104, "ADMITTED_CLAIM_UNIVERSE_MISMATCH")
    catalog, aliases_by_node = _load_catalog(production_path)
    records = _build_advisory_node_records(
        operations=deferred,
        claims=claims,
        catalog=catalog,
        aliases_by_node=aliases_by_node,
        source_run_id=str(metadata.get("source_run_id") or ""),
    )

    deferred_ids = [operation["candidate_id"] for operation in deferred]
    rejected_ids = {operation["candidate_id"] for operation in rejected}
    record_ids = [record["operation_candidate_id"] for record in records]
    _require(record_ids == deferred_ids, "NODE_REVIEW_ORDER_OR_UNIVERSE_MISMATCH")
    _require(not rejected_ids.intersection(record_ids), "REJECTED_NODE_INCLUDED_IN_REVIEW")
    counts = Counter(record["suggested_operation"] for record in records)
    body = {
        "document_type": REVIEW_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "review_status": "DRAFT",
        "qualification_payload": {
            "payload_id": payload["payload_id"],
            "payload_sha256": payload["payload_hash"],
        },
        "production_baseline": {
            "sha256": baseline["sha256"],
            "schema_version": baseline["schema_version"],
            "schema_sha256": baseline["schema_sha256"],
            "counts": baseline["counts"],
            "sidecars": baseline["sidecars"],
        },
        "review_universe": {
            "expected": 26,
            "observed": len(records),
            "candidate_ids": record_ids,
            "candidate_ids_sha256": canonical_sha256(record_ids),
            "admitted_claims": len(claims),
            "admitted_claim_ids_sha256": canonical_sha256([claim["claim_id"] for claim in claims]),
            "rejected_nodes_excluded": len(rejected),
            "table_ineligible_claims_excluded": len(payload.get("claims") or []) - len(claims),
        },
        "suggestion_counts": {operation: counts.get(operation, 0) for operation in ("REUSE", "CREATE", "DEFER", "REJECT")},
        "relation_audit": {
            "relation_reject_expected": 10,
            "relation_reject_observed": len(relation_rejects),
            "relation_review_reopened": False,
        },
        "records": records,
        "authorization": {
            "all_review_decisions_pending": all(record["review_decision"] == "PENDING" for record in records),
            "llm_authorization_used": False,
            "production_apply_authorized": False,
            "final_production_payload_generated": False,
        },
    }
    digest = canonical_sha256(body)
    return {
        **body,
        "review_id": f"NODE_REVIEW_{digest[:16].upper()}",
        "review_sha256": digest,
    }


def build_operational_node_operation_review(
    *,
    run_id: str,
    source_sha256: str,
    claim_review_sha256: str,
    claims: Sequence[Mapping[str, Any]],
    node_operations: Sequence[Mapping[str, Any]],
    relation_operations: Sequence[Mapping[str, Any]],
    production_path: Path,
    table_ineligible_claims: int,
) -> dict[str, Any]:
    """Reuse Stage 3D.3A diagnostics for an unapproved Phase 3E review package."""
    deferred = [item for item in node_operations if item.get("operation") == "DEFER"]
    rejected = [item for item in node_operations if item.get("operation") == "REJECT"]
    _require(bool(run_id and source_sha256 and claim_review_sha256), "OPERATIONAL_REVIEW_BINDING_MISSING")
    _require(
        all(not item.get("executable") for item in [*node_operations, *relation_operations]),
        "OPERATIONAL_REVIEW_CONTAINS_EXECUTABLE_OPERATION",
    )
    baseline = production_identity(production_path)
    catalog, aliases_by_node = _load_catalog(production_path)
    records = _build_advisory_node_records(
        operations=deferred,
        claims=claims,
        catalog=catalog,
        aliases_by_node=aliases_by_node,
        source_run_id=run_id,
    )
    for record, operation in zip(records, deferred):
        candidate = operation.get("candidate") or {}
        raw_parent_ids = candidate.get("suggested_parent_node_ids") or []
        if not isinstance(raw_parent_ids, list):
            raw_parent_ids = []
        parent_ids = list(dict.fromkeys(
            parent_id.strip() for parent_id in raw_parent_ids
            if isinstance(parent_id, str) and parent_id.strip()
        ))
        record["parent_placement_suggestion"] = {
            "suggested_parent_node_ids": parent_ids,
            "advisory_only": True,
            "separate_human_review_required": bool(parent_ids),
            "authorized_by_node_create": False,
            "review_decision": "PENDING" if parent_ids else "NOT_APPLICABLE",
        }
    record_ids = [record["operation_candidate_id"] for record in records]
    _require(
        record_ids == [operation["candidate_id"] for operation in deferred],
        "OPERATIONAL_NODE_REVIEW_ORDER_OR_UNIVERSE_MISMATCH",
    )
    counts = Counter(record["suggested_operation"] for record in records)
    relation_deferred = sum(item.get("operation") == "DEFER" for item in relation_operations)
    relation_rejected = sum(item.get("operation") == "REJECT" for item in relation_operations)
    body = {
        "document_type": "phase3e_node_operation_review",
        "schema_version": SCHEMA_VERSION,
        "review_status": "DRAFT",
        "operational_run": {
            "run_id": run_id,
            "source_sha256": source_sha256,
            "claim_review_sha256": claim_review_sha256,
        },
        "production_baseline": {
            "sha256": baseline["sha256"],
            "schema_version": baseline["schema_version"],
            "schema_sha256": baseline["schema_sha256"],
            "counts": baseline["counts"],
            "sidecars": baseline["sidecars"],
        },
        "review_universe": {
            "expected": len(deferred),
            "observed": len(records),
            "candidate_ids": record_ids,
            "candidate_ids_sha256": canonical_sha256(record_ids),
            "admitted_claims": len(claims),
            "admitted_claim_ids_sha256": canonical_sha256([claim["claim_id"] for claim in claims]),
            "rejected_nodes_excluded": len(rejected),
            "table_ineligible_claims_excluded": table_ineligible_claims,
        },
        "suggestion_counts": {
            operation: counts.get(operation, 0)
            for operation in ("REUSE", "CREATE", "DEFER", "REJECT")
        },
        "relation_audit": {
            "observed": len(relation_operations),
            "deferred": relation_deferred,
            "rejected": relation_rejected,
            "relations_excluded_from_promotion": True,
            "relation_review_reopened": False,
        },
        "audit_operations": {
            "node_rejected": copy.deepcopy(rejected),
            "relations": copy.deepcopy(list(relation_operations)),
        },
        "records": records,
        "authorization": {
            "all_review_decisions_pending": all(
                record["review_decision"] == "PENDING" for record in records
            ),
            "llm_authorization_used": False,
            "production_apply_authorized": False,
            "final_production_payload_generated": False,
        },
    }
    digest = canonical_sha256(body)
    return {
        **body,
        "review_id": f"NODE_REVIEW_{digest[:16].upper()}",
        "review_sha256": digest,
    }


def render_node_operation_review_markdown(review: Mapping[str, Any]) -> str:
    _require(review.get("review_status") == "DRAFT", "NODE_REVIEW_NOT_DRAFT")

    def clean(value: Any) -> str:
        return str(value or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = [
        "# Stage 3D.3A Node Operation Review",
        "",
        "> DRAFT human-review package. Suggestions are deterministic and advisory only; every decision is PENDING.",
        "",
        f"Qualification payload: `{review['qualification_payload']['payload_id']}` / `{review['qualification_payload']['payload_sha256']}`",
        f"Production baseline SHA256: `{review['production_baseline']['sha256']}`",
        f"Review universe: **{review['review_universe']['observed']}** of {review['review_universe']['expected']}",
        "",
        "| # | Candidate ID | Kind | Name | Type | Claims | Suggestion | Decision |",
        "|---:|---|---|---|---|---:|---|---|",
    ]
    for index, record in enumerate(review["records"], 1):
        lines.append(
            f"| {index} | `{record['operation_candidate_id']}` | {clean(record['candidate_kind'])} | "
            f"{clean(record['proposed_name'])} | {clean(record['proposed_type'])} | "
            f"{len(record['supporting_claim_ids'])} | **{record['suggested_operation']}** | PENDING |"
        )
    for index, record in enumerate(review["records"], 1):
        resolution = record["exact_production_resolution"]
        targets = resolution["candidate_targets"]
        target_text = ", ".join(
            f"{target['node_id']} — {target['canonical_name']} ({target['primary_type']}, {target['status']})"
            for target in targets
        ) or "None"
        collisions = record["collision_diagnostics"]["package_internal_normalized_term_collisions"]
        collision_text = ", ".join(
            f"{item['normalized_term']}: {', '.join(item['candidate_ids'])}" for item in collisions
        ) or "None"
        lines.extend([
            "",
            f"## {index}. {clean(record['proposed_name'])}",
            "",
            f"- Candidate: `{record['operation_candidate_id']}` ({record['candidate_kind']})",
            f"- Proposed type: `{clean(record['proposed_type'])}`",
            f"- Current defer reason: {clean(record['current_defer_reason'])}",
            f"- Exact/normalized Production targets: {clean(target_text)}",
            f"- Package-internal collisions: {clean(collision_text)}",
            f"- Advisory suggestion: **{record['suggested_operation']}** — {clean(record['suggestion_reason'])}",
            "- Human decision: **PENDING** (reviewer and reason unset)",
        ])
        if record["supporting_evidence"]:
            lines.extend(["", "Supporting admitted Claim evidence:", ""])
            for evidence in record["supporting_evidence"]:
                excerpt = clean(evidence["evidence_excerpt"])
                if len(excerpt) > 360:
                    excerpt = excerpt[:357] + "..."
                lines.append(
                    f"- `{evidence['claim_id']}` {clean(evidence['evidence_pointer'])}: {excerpt}"
                )
        else:
            lines.extend(["", "Supporting admitted Claim evidence: **none deterministically linked; keep DEFER.**"])
    lines.extend([
        "",
        "## Relation audit",
        "",
        "The ten Relation observations remain REJECT. Relation review was not reopened.",
        "",
    ])
    return "\n".join(lines)


def build_authorization_manifest(
    *,
    repository_commit: str,
    payload: Mapping[str, Any],
    production_pre: Mapping[str, Any],
    production_post: Mapping[str, Any],
    source_materialization: Mapping[str, Any],
    node_review: Mapping[str, Any],
    artifact_paths: Sequence[Path],
) -> dict[str, Any]:
    _require(production_pre["sha256"] == production_post["sha256"], "PRODUCTION_CHANGED_DURING_STAGE3D3A")
    _require(production_pre["counts"] == production_post["counts"], "PRODUCTION_COUNTS_CHANGED_DURING_STAGE3D3A")
    return {
        "document_type": MANIFEST_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_AUTHORIZATION_PREPARATION_COMPLETE",
        "repository_commit": repository_commit,
        "qualification_payload": {
            "payload_id": payload["payload_id"],
            "payload_sha256": payload["payload_hash"],
        },
        "artifacts": [
            {"name": Path(path).name, "sha256": sha256_file(path), "size": Path(path).stat().st_size}
            for path in artifact_paths
        ],
        "source_archive_materialization_ready": source_materialization["flags"]["source_archive_materialization_ready"],
        "node_review": {
            "review_id": node_review["review_id"],
            "review_sha256": node_review["review_sha256"],
            "review_status": node_review["review_status"],
            "universe": node_review["review_universe"]["observed"],
            "pending": sum(record["review_decision"] == "PENDING" for record in node_review["records"]),
            "suggestion_counts": node_review["suggestion_counts"],
        },
        "relation_audit": copy.deepcopy(node_review["relation_audit"]),
        "production": {
            "pre_sha256": production_pre["sha256"],
            "post_sha256": production_post["sha256"],
            "changed": False,
            "apply_attempted": False,
        },
        "final_production_payload_generated": False,
        "production_apply_authorized": False,
        "recommended_next_action": "EXPLICIT_HUMAN_REVIEW_OF_26_NODE_OPERATION_RECORDS",
    }


def authoritative_human_decisions() -> list[dict[str, Any]]:
    return [
        {
            "operation_candidate_id": candidate_id,
            "decision": decision,
            "target_node_id": target_node_id,
            "decision_reason": reason,
        }
        for candidate_id, decision, target_node_id, reason in _HUMAN_DECISION_ROWS
    ]


def _validate_draft_binding(
    draft_review: Mapping[str, Any], payload: Mapping[str, Any]
) -> None:
    validate_payload(payload)
    _require(payload.get("payload_id") == EXPECTED_PAYLOAD_ID, "QUALIFICATION_PAYLOAD_ID_MISMATCH")
    _require(payload.get("payload_hash") == EXPECTED_PAYLOAD_SHA256, "QUALIFICATION_PAYLOAD_SHA_MISMATCH")
    _require(draft_review.get("document_type") == REVIEW_DOCUMENT_TYPE, "DRAFT_REVIEW_DOCUMENT_TYPE_MISMATCH")
    _require(draft_review.get("review_status") == "DRAFT", "PRIOR_REVIEW_NOT_DRAFT")
    _require(draft_review.get("review_id") == EXPECTED_DRAFT_REVIEW_ID, "DRAFT_REVIEW_ID_MISMATCH")
    _require(draft_review.get("review_sha256") == EXPECTED_DRAFT_REVIEW_SHA256, "DRAFT_REVIEW_SHA_MISMATCH")
    draft_body = {
        key: copy.deepcopy(value)
        for key, value in draft_review.items()
        if key not in {"review_id", "review_sha256"}
    }
    _require(canonical_sha256(draft_body) == EXPECTED_DRAFT_REVIEW_SHA256, "DRAFT_REVIEW_CONTENT_HASH_MISMATCH")
    binding = draft_review.get("qualification_payload") or {}
    _require(binding.get("payload_id") == EXPECTED_PAYLOAD_ID, "DRAFT_PAYLOAD_ID_MISMATCH")
    _require(binding.get("payload_sha256") == EXPECTED_PAYLOAD_SHA256, "DRAFT_PAYLOAD_SHA_MISMATCH")
    records = draft_review.get("records") or []
    record_ids = [record.get("operation_candidate_id") for record in records]
    payload_deferred_ids = [
        operation.get("candidate_id")
        for operation in payload.get("node_operations") or []
        if operation.get("operation") == "DEFER"
    ]
    _require(len(record_ids) == len(set(record_ids)) == 26, "DRAFT_REVIEW_UNIVERSE_DUPLICATE_OR_COUNT_MISMATCH")
    _require(record_ids == payload_deferred_ids, "DRAFT_REVIEW_UNIVERSE_MISMATCH")
    payload_node_rejects = [
        operation
        for operation in payload.get("node_operations") or []
        if operation.get("operation") == "REJECT"
    ]
    payload_relations = payload.get("relation_operations") or []
    payload_ineligible_claims = [
        claim for claim in payload.get("claims") or [] if claim.get("executable") is not True
    ]
    _require(len(payload_node_rejects) == 32, "PAYLOAD_NODE_REJECTION_INVENTORY_MISMATCH")
    _require(
        len(payload_relations) == 10
        and all(operation.get("operation") == "REJECT" for operation in payload_relations),
        "PAYLOAD_RELATION_REJECTION_INVENTORY_MISMATCH",
    )
    _require(len(payload_ineligible_claims) == 3, "PAYLOAD_TABLE_INELIGIBLE_INVENTORY_MISMATCH")
    _require((draft_review.get("review_universe") or {}).get("rejected_nodes_excluded") == 32, "PRIOR_NODE_REJECTION_INVENTORY_MISMATCH")
    _require((draft_review.get("review_universe") or {}).get("table_ineligible_claims_excluded") == 3, "TABLE_INELIGIBLE_CLAIM_INVENTORY_MISMATCH")
    relation_audit = draft_review.get("relation_audit") or {}
    _require(relation_audit.get("relation_reject_observed") == 10, "RELATION_REJECTION_INVENTORY_MISMATCH")
    _require(relation_audit.get("relation_review_reopened") is False, "RELATION_REVIEW_WAS_REOPENED")


def _validate_human_decisions(
    decisions: Sequence[Mapping[str, Any]], draft_review: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    ids = [decision.get("operation_candidate_id") for decision in decisions]
    _require(len(ids) == 26, "HUMAN_DECISION_COUNT_MISMATCH")
    _require(len(ids) == len(set(ids)), "DUPLICATE_HUMAN_DECISION")
    draft_ids = [record["operation_candidate_id"] for record in draft_review["records"]]
    _require(set(ids) == set(draft_ids), "HUMAN_DECISION_UNIVERSE_MISMATCH")
    expected = {
        decision["operation_candidate_id"]: decision
        for decision in authoritative_human_decisions()
    }
    supplied = {decision["operation_candidate_id"]: dict(decision) for decision in decisions}
    for candidate_id, expected_decision in expected.items():
        actual = supplied[candidate_id]
        _require(actual.get("decision") == expected_decision["decision"], f"HUMAN_DECISION_CLASSIFICATION_MISMATCH:{candidate_id}")
        _require(actual.get("target_node_id") == expected_decision["target_node_id"], f"HUMAN_REUSE_TARGET_MISMATCH:{candidate_id}")
        _require(actual.get("decision_reason") == expected_decision["decision_reason"], f"HUMAN_DECISION_REASON_MISMATCH:{candidate_id}")
    counts = Counter(decision["decision"] for decision in supplied.values())
    _require(
        {operation: counts.get(operation, 0) for operation in ("REUSE", "CREATE", "DEFER", "REJECT")}
        == {"REUSE": 6, "CREATE": 8, "DEFER": 7, "REJECT": 5},
        "HUMAN_DECISION_TOTALS_MISMATCH",
    )
    return supplied


def _validate_reviewed_identity_intents(
    decisions: Mapping[str, Mapping[str, Any]],
    draft_by_id: Mapping[str, Mapping[str, Any]],
    catalog: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    intents: dict[str, dict[str, Any]] = {}
    package_terms: dict[str, str] = {}
    for candidate_id, (expected_name, expected_type) in EXPECTED_CREATE_IDENTITIES.items():
        _require(decisions[candidate_id]["decision"] == "CREATE", f"EXPECTED_CREATE_NOT_APPROVED:{candidate_id}")
        record = draft_by_id[candidate_id]
        _require(
            (record.get("proposed_name"), record.get("proposed_type")) == (expected_name, expected_type),
            f"CREATE_IDENTITY_MISMATCH:{candidate_id}",
        )
        aliases = list(dict.fromkeys(
            str(alias).strip()
            for alias in record.get("proposed_aliases") or []
            if str(alias).strip() and str(alias).strip() != expected_name
        ))
        if candidate_id == "CAND_NODE_7C4F495527737096":
            _require("VPD" in aliases, "VPD_ALIAS_REQUIRED")
        if candidate_id == "CAND_NODE_C195F1E21A50449B":
            _require("SPD" in aliases, "SPD_ALIAS_REQUIRED")
        if candidate_id == "CAND_NODE_43BE3226A7EACED0":
            _require("CMM-D" not in aliases, "CMM_D_GENERIC_ALIAS_FORBIDDEN")
        if candidate_id == "CAND_NODE_60282E35851EA5A9":
            _require(expected_type == "Standard", "EDSFF_MUST_REMAIN_STANDARD")
        prospective_node_id = record.get("prospective_node_id")
        _require(prospective_node_id not in catalog["nodes"], f"REVIEWED_CREATE_NODE_ID_COLLISION:{prospective_node_id}")
        for term in [expected_name, *aliases]:
            _require(not resolve_identity(catalog, term)["all_ids"], f"REVIEWED_CREATE_PRODUCTION_COLLISION:{term}")
            normalized = nfkc_casefold(term)
            owner = package_terms.get(normalized)
            _require(owner in {None, candidate_id}, f"REVIEWED_CREATE_PACKAGE_COLLISION:{term}")
            package_terms[normalized] = candidate_id
        intents[candidate_id] = {
            "canonical_name": expected_name,
            "primary_type": expected_type,
            "aliases": aliases,
            "prospective_node_id": prospective_node_id,
            "collision_check": "PASS_CURRENT_PRODUCTION_BASELINE",
        }

    for candidate_id, decision in decisions.items():
        if decision["decision"] != "REUSE":
            continue
        record = draft_by_id[candidate_id]
        target_id = decision["target_node_id"]
        target = catalog["nodes"].get(target_id)
        _require(target is not None, f"REVIEWED_REUSE_TARGET_MISSING:{target_id}")
        _require(target.get("status") == "active", f"REVIEWED_REUSE_TARGET_INACTIVE:{target_id}")
        _require(target.get("primary_type") == record.get("proposed_type"), f"REVIEWED_REUSE_TARGET_TYPE_MISMATCH:{target_id}")
        terms = [record.get("proposed_name"), *(record.get("proposed_aliases") or [])]
        current_ids = sorted({
            node_id
            for term in terms
            for node_id in resolve_identity(catalog, term)["all_ids"]
        })
        _require(current_ids == [target_id], f"REVIEWED_REUSE_RESOLUTION_MISMATCH:{candidate_id}")
        _require(
            (record.get("exact_production_resolution") or {}).get("candidate_target_node_ids") == [target_id],
            f"DRAFT_REUSE_RESOLUTION_MISMATCH:{candidate_id}",
        )
        intents[candidate_id] = {
            "target_node_id": target_id,
            "target_canonical_name": target["canonical_name"],
            "target_primary_type": target["primary_type"],
            "target_status": target["status"],
            "resolution_check": "PASS_CURRENT_PRODUCTION_BASELINE",
        }
    return intents


def bind_human_node_review(
    *,
    draft_review: Mapping[str, Any],
    payload: Mapping[str, Any],
    source_materialization: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    production_path: Path,
) -> dict[str, Any]:
    """Bind explicit user human review without creating an executable payload."""
    _validate_draft_binding(draft_review, payload)
    supplied = _validate_human_decisions(decisions, draft_review)
    _require(
        source_materialization.get("document_type") == SOURCE_DOCUMENT_TYPE,
        "SOURCE_MATERIALIZATION_DOCUMENT_TYPE_MISMATCH",
    )
    _require(source_materialization.get("status") == "BLOCKED_SOURCE_MISSING", "SOURCE_MATERIALIZATION_STATUS_MISMATCH")
    source = source_materialization.get("source") or {}
    source_flags = source_materialization.get("flags") or {}
    source_id = ((payload.get("sources") or [{}])[0]).get("source_id")
    _require(source.get("source_id") == source_id, "SOURCE_BLOCKER_ID_MISMATCH")
    _require(source.get("expected_sha256") == EXPECTED_SOURCE_SHA256, "SOURCE_BLOCKER_SHA_MISMATCH")
    _require(source_flags.get("source_file_found") is False, "SOURCE_FILE_STATE_MISMATCH")
    _require(source_flags.get("source_sha_match") is False, "SOURCE_SHA_STATE_MISMATCH")
    _require(source_flags.get("source_archive_materialization_ready") is False, "SOURCE_GATE_UNEXPECTEDLY_READY")
    _require((source_materialization.get("real_archive") or {}).get("mutated") is False, "REAL_ARCHIVE_MUTATION_RECORDED")
    _require(
        (source_materialization.get("materialization") or {}).get("real_archive_copy_performed") is False,
        "REAL_ARCHIVE_COPY_RECORDED",
    )

    production = production_identity(production_path)
    draft_baseline = draft_review.get("production_baseline") or {}
    _require(production["sha256"] == draft_baseline.get("sha256"), "PRODUCTION_BASELINE_DRIFT")
    _require(production["schema_sha256"] == draft_baseline.get("schema_sha256"), "PRODUCTION_SCHEMA_DRIFT")
    _require(production["counts"] == draft_baseline.get("counts"), "PRODUCTION_COUNTS_DRIFT")
    catalog, _ = _load_catalog(production_path)
    draft_by_id = {
        record["operation_candidate_id"]: record
        for record in draft_review["records"]
    }
    intents = _validate_reviewed_identity_intents(supplied, draft_by_id, catalog)

    reviewed_records: list[dict[str, Any]] = []
    for expected in authoritative_human_decisions():
        candidate_id = expected["operation_candidate_id"]
        draft_record = draft_by_id[candidate_id]
        decision = supplied[candidate_id]
        reviewed_records.append({
            "operation_candidate_id": candidate_id,
            "candidate_kind": draft_record["candidate_kind"],
            "proposed_name": draft_record["proposed_name"],
            "proposed_type": draft_record["proposed_type"],
            "supporting_claim_ids": copy.deepcopy(draft_record["supporting_claim_ids"]),
            "prior_deterministic_suggestion": draft_record["suggested_operation"],
            "human_decision": decision["decision"],
            "target_node_id": decision["target_node_id"],
            "human_decision_reason": decision["decision_reason"],
            "reviewed_identity_intent": copy.deepcopy(intents.get(candidate_id)),
            "decision_authority": "USER_HUMAN_REVIEW",
            "executable": False,
            "execution_state": (
                "REVIEWED_BUT_SOURCE_ARCHIVE_MATERIALIZATION_BLOCKED"
                if decision["decision"] in {"CREATE", "REUSE"}
                else "HUMAN_DECISION_NONEXECUTABLE"
            ),
        })

    counts = Counter(record["human_decision"] for record in reviewed_records)
    body = {
        "document_type": HUMAN_REVIEW_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "review_status": "HUMAN_REVIEW_COMPLETE",
        "prior_draft_review": {
            "review_id": EXPECTED_DRAFT_REVIEW_ID,
            "review_sha256": EXPECTED_DRAFT_REVIEW_SHA256,
        },
        "qualification_payload": {
            "payload_id": EXPECTED_PAYLOAD_ID,
            "payload_sha256": EXPECTED_PAYLOAD_SHA256,
        },
        "decision_authority": {
            "authority": "USER_HUMAN_REVIEW",
            "basis": "Explicit user confirmation of the exact 26-record decision set for Stage 3D.3B.",
            "llm_authorization_used": False,
        },
        "production_baseline": {
            "sha256": production["sha256"],
            "schema_version": production["schema_version"],
            "schema_sha256": production["schema_sha256"],
            "counts": production["counts"],
            "sidecars": production["sidecars"],
        },
        "human_review_universe": {
            "expected": 26,
            "observed": len(reviewed_records),
            "candidate_ids": [record["operation_candidate_id"] for record in reviewed_records],
            "candidate_ids_sha256": canonical_sha256(
                [record["operation_candidate_id"] for record in reviewed_records]
            ),
        },
        "operation_counts": {
            operation: counts.get(operation, 0)
            for operation in ("REUSE", "CREATE", "DEFER", "REJECT")
        },
        "records": reviewed_records,
        "preserved_inventory": {
            "prior_node_reject": 32,
            "table_ineligible_claims_excluded": 3,
            "relation_reject": 10,
            "relation_review_reopened": False,
        },
        "source_blocker": {
            "expected_source_sha256": EXPECTED_SOURCE_SHA256,
            "source_file_found": False,
            "source_sha_match": False,
            "source_archive_materialization_ready": False,
        },
        "authorization_state": {
            "executable": False,
            "blocked_by": ["SOURCE_ARCHIVE_MATERIALIZATION"],
            "final_production_payload_generated": False,
            "production_apply_authorized": False,
            "production_apply_attempted": False,
        },
    }
    digest = canonical_sha256(body)
    return {
        **body,
        "human_review_id": f"HUMAN_NODE_REVIEW_{digest[:16].upper()}",
        "human_review_sha256": digest,
    }


def render_human_node_review_markdown(review: Mapping[str, Any]) -> str:
    _require(review.get("review_status") == "HUMAN_REVIEW_COMPLETE", "HUMAN_REVIEW_NOT_COMPLETE")

    def clean(value: Any) -> str:
        return str(value or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = [
        "# Stage 3D.3B Human Node Review Closure",
        "",
        "> Human review is complete for the 26 Node operation records only. This artifact is non-executable and does not authorize Production apply.",
        "",
        f"Prior draft: `{review['prior_draft_review']['review_id']}` / `{review['prior_draft_review']['review_sha256']}`",
        f"Qualification payload: `{review['qualification_payload']['payload_id']}` / `{review['qualification_payload']['payload_sha256']}`",
        f"Decision authority: `{review['decision_authority']['authority']}`; LLM authorization used: `false`",
        f"Blocked by: `{review['authorization_state']['blocked_by'][0]}`",
        "",
        "| # | Candidate ID | Name | Type | Human decision | Target | Executable |",
        "|---:|---|---|---|---|---|---|",
    ]
    for index, record in enumerate(review["records"], 1):
        lines.append(
            f"| {index} | `{record['operation_candidate_id']}` | {clean(record['proposed_name'])} | "
            f"{clean(record['proposed_type'])} | **{record['human_decision']}** | "
            f"{clean(record['target_node_id']) or '—'} | false |"
        )
    for index, record in enumerate(review["records"], 1):
        lines.extend([
            "",
            f"## {index}. {clean(record['proposed_name'])} — {record['human_decision']}",
            "",
            f"- Candidate: `{record['operation_candidate_id']}`",
            f"- Human reason: {clean(record['human_decision_reason'])}",
            f"- Prior deterministic suggestion: `{record['prior_deterministic_suggestion']}` (not the human decision)",
            f"- REUSE target: `{record['target_node_id']}`" if record["target_node_id"] else "- REUSE target: none",
            "- Executable: `false`",
        ])
        intent = record.get("reviewed_identity_intent")
        if intent and record["human_decision"] == "CREATE":
            aliases = ", ".join(f"`{clean(alias)}`" for alias in intent["aliases"]) or "none"
            lines.append(
                f"- Frozen CREATE identity: `{clean(intent['canonical_name'])}` / `{clean(intent['primary_type'])}`; aliases: {aliases}"
            )
    lines.extend([
        "",
        "## Safety closure",
        "",
        "- Relation REJECT remains 10; Relation review was not reopened.",
        "- Source file remains missing and the exact-SHA materialization gate remains blocked.",
        "- Final Production payload generated: `false`.",
        "- Production apply authorized: `false`.",
        "",
    ])
    return "\n".join(lines)


def build_human_review_manifest(
    *,
    repository_commit: str,
    human_review: Mapping[str, Any],
    production_pre: Mapping[str, Any],
    production_post: Mapping[str, Any],
    artifact_paths: Sequence[Path],
) -> dict[str, Any]:
    _require(production_pre["sha256"] == production_post["sha256"], "PRODUCTION_CHANGED_DURING_STAGE3D3B")
    _require(production_pre["counts"] == production_post["counts"], "PRODUCTION_COUNTS_CHANGED_DURING_STAGE3D3B")
    _require(production_pre["sidecars"] == production_post["sidecars"], "PRODUCTION_SIDECARS_CHANGED_DURING_STAGE3D3B")
    return {
        "document_type": HUMAN_MANIFEST_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "HUMAN_REVIEW_CLOSURE_COMPLETE_SOURCE_BLOCKED",
        "repository_commit": repository_commit,
        "human_review": {
            "human_review_id": human_review["human_review_id"],
            "human_review_sha256": human_review["human_review_sha256"],
            "review_status": human_review["review_status"],
            "decision_authority": "USER_HUMAN_REVIEW",
            "universe": human_review["human_review_universe"]["observed"],
            "operation_counts": copy.deepcopy(human_review["operation_counts"]),
        },
        "prior_draft_review": copy.deepcopy(human_review["prior_draft_review"]),
        "qualification_payload": copy.deepcopy(human_review["qualification_payload"]),
        "artifacts": [
            {"name": Path(path).name, "sha256": sha256_file(path), "size": Path(path).stat().st_size}
            for path in artifact_paths
        ],
        "source_blocker": copy.deepcopy(human_review["source_blocker"]),
        "relation_state": {
            "relation_reject": 10,
            "relation_review_reopened": False,
        },
        "authorization_state": copy.deepcopy(human_review["authorization_state"]),
        "production": {
            "pre_sha256": production_pre["sha256"],
            "post_sha256": production_post["sha256"],
            "sidecars_pre": production_pre["sidecars"],
            "sidecars_post": production_post["sidecars"],
            "changed": False,
            "apply_attempted": False,
        },
        "recommended_next_action": (
            "Supply/find exact Source bytes matching "
            "572a6df2b583358506e2a4fb86359a07e9a1503a3507dcdd2c81a8d97c27e97a"
        ),
    }
