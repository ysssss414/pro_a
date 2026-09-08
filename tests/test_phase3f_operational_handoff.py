from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.db import Database
from pro_a.phase3f_operational_handoff import (
    OperationalHandoffError,
    assert_deterministic_handoff,
    build_operational_handoff_artifacts,
    validate_handoff_accounting,
    validate_handoff_payload,
    validate_operational_handoff_inputs,
)
from pro_a.phase3f_review_completion import (
    ReviewCompletionError,
    build_blank_review_packet,
    validate_completed_review_packet,
)
from pro_a.production_promotion import (
    PromotionError,
    canonical_sha256,
    payload_semantic_body,
    production_identity,
    sha256_file,
)


REVIEWER = "SYNTHETIC_HUMAN_REVIEWER"
REASON = "Synthetic contract decision; no source-derived content."
COMMIT = "1" * 40
SOURCE_ID = "SRC_SYNTHETIC_HANDOFF"
RUN_ID = "INGEST_SYNTHETIC_HANDOFF"
KEEP = "CLM_SYNTHETIC_KEEP"
DROP = "CLM_SYNTHETIC_DROP"
NEEDS_REVIEW = "CLM_SYNTHETIC_NEEDS_REVIEW"
CREATE = "CAND_NODE_SYNTHETIC_CREATE"
REUSE = "CAND_NODE_SYNTHETIC_REUSE"
DEFER = "CAND_NODE_SYNTHETIC_DEFER"
REJECT = "CAND_NODE_SYNTHETIC_REJECT"
PARENT = "PARENT_PLACEMENT_SYNTHETIC"
CREATE_NODE_ID = "NODE_SYNTHETIC_CREATED"
REUSE_NODE_ID = "NODE_SYNTHETIC_REUSE"
PARENT_NODE_ID = "NODE_SYNTHETIC_PARENT"


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _semantic_artifact(
    body: dict, *, id_field: str, hash_field: str, prefix: str
) -> dict:
    digest = canonical_sha256(body)
    return {
        **body,
        id_field: f"{prefix}_{digest[:16].upper()}",
        hash_field: digest,
    }


def _receipt(body: dict, prefix: str) -> dict:
    digest = canonical_sha256(body)
    return {
        **body,
        "receipt_id": f"{prefix}_{digest[:16].upper()}",
        "receipt_sha256": digest,
    }


def _claim(claim_id: str, source_sha256: str) -> dict:
    statement = f"Synthetic statement for {claim_id}."
    return {
        "claim_id": claim_id,
        "statement": statement,
        "nature": "fact",
        "fact_time": "2026-01-01",
        "publication_time": "2026-01-02",
        "ingestion_time": "2026-01-03T00:00:00+00:00",
        "source_id": SOURCE_ID,
        "evidence_pointer": f"synthetic:{claim_id}",
        "evidence_excerpt": statement,
        "attributed_to": "Synthetic Test",
        "scope": "contract-test",
        "assumption_text": "",
        "status": "current",
        "confidence": 1.0,
        "novelty_level": "N2",
        "structured": {"synthetic": True},
        "evidence_validated": True,
        "phase3c_evidence": {"source_sha256": source_sha256},
        "related_node_ids": [],
        "related_candidate_names": [],
        "created_at": "2026-01-03T00:00:00+00:00",
    }


def _node_record(
    candidate_id: str,
    name: str,
    node_id: str,
    *,
    aliases: list[str] | None = None,
    reuse_target: str | None = None,
) -> dict:
    target_ids = [reuse_target] if reuse_target else []
    return {
        "operation_candidate_id": candidate_id,
        "source_operation_id": f"SYNTHETIC_{candidate_id}",
        "candidate_kind": "synthetic_node",
        "proposed_name": name,
        "proposed_type": "Product",
        "proposed_aliases": aliases or [],
        "prospective_node_id": node_id,
        "supporting_claim_ids": [KEEP],
        "supporting_evidence": [
            {"claim_id": KEEP, "evidence_id": "EVD_SYNTHETIC_KEEP"}
        ],
        "phase3c_validation_state": {"status": "PASS"},
        "current_defer_reason": "",
        "exact_production_resolution": {
            "candidate_target_node_ids": target_ids,
        },
        "collision_diagnostics": {
            "prospective_node_id_exists": False,
            "package_internal_normalized_term_collisions": [],
            "production_nocase_or_nfkc_target_ids": [],
        },
        "suggested_operation": "DEFER",
        "suggestion_reason": "Synthetic advisory only.",
        "review_decision": "PENDING",
        "advisory_only": True,
        "parent_placement_suggestion": {},
    }


def _make_case(
    root: Path, *, alias_collision: bool = False, create_collision: bool = False
) -> dict:
    production_path = root / "production.db"
    database = Database(production_path)
    database.init_schema()
    with database.connect() as connection:
        connection.executemany(
            """INSERT INTO nodes(
               node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                (
                    REUSE_NODE_ID,
                    "Existing Synthetic Node",
                    "Product",
                    "Synthetic existing node.",
                    "active",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
                (
                    PARENT_NODE_ID,
                    "Synthetic Parent",
                    "Category",
                    "Synthetic parent node.",
                    "active",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
            ],
        )
        connection.execute(
            "INSERT INTO node_aliases(alias,node_id) VALUES(?,?)",
            ("Existing Synthetic Alias", REUSE_NODE_ID),
        )
    production = production_identity(production_path)
    baseline = {key: value for key, value in production.items() if key != "path"}

    run_root = root / "run"
    source_path = run_root / "source" / "synthetic-source.txt"
    source_path.parent.mkdir(parents=True)
    source_bytes = b"SYNTHETIC PUBLIC-SAFE CONTRACT FIXTURE\n"
    source_path.write_bytes(source_bytes)
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()

    claims = [_claim(claim_id, source_sha256) for claim_id in (KEEP, DROP, NEEDS_REVIEW)]
    bundle = {
        "document_type": "phase3c_extraction_bundle",
        "schema_version": "1",
        "source": {
            "proposed_source_id": SOURCE_ID,
            "sha256": source_sha256,
            "original_name": source_path.name,
            "source_type": "synthetic_text",
            "analysis_mode": "synthetic",
            "parse_diagnostics": {},
            "parse_warnings": [],
            "semantic_eligibility": {"status": "PASS"},
        },
        "proposed_source_metadata": {
            "title": "Synthetic Handoff Fixture",
            "publication_time": "2026-01-02",
            "source_rank": "SYNTHETIC",
            "source_origin_type": "test_fixture",
        },
        "claims": claims,
        "observations": {},
    }
    bundle_path = run_root / "evidence" / "evidence_bound_extraction_bundle.json"
    _write(bundle_path, bundle)

    claim_review_body = {
        "document_type": "phase3e_claim_review",
        "schema_version": "1",
        "review_status": "DRAFT",
        "run_id": RUN_ID,
        "source_sha256": source_sha256,
        "claims": [
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "evidence_pointer": claim["evidence_pointer"],
                "evidence_excerpt": claim["evidence_excerpt"],
                "evidence_validation": {"status": "PASS"},
                "table_eligibility": {"eligible": True},
                "semantic_admission": {"overall_guard_disposition": "ADMIT"},
                "scope_preservation": {"status": "PASS"},
                "review_admitted": True,
                "recommended_decision": "KEEP",
                "recommendation_reason": "Synthetic advisory.",
                "duplicate_of_claim_id": "",
                "duplicate_reconciliation": {},
                "human_decision": "PENDING",
            }
            for claim in claims
        ],
        "authorization": {"human_decisions_bound": False},
    }
    claim_review = _semantic_artifact(
        claim_review_body,
        id_field="review_id",
        hash_field="review_sha256",
        prefix="CLAIM_REVIEW",
    )
    claim_review_path = run_root / "review" / "claim_review.json"
    _write(claim_review_path, claim_review)

    create_name = (
        "Existing Synthetic Node" if create_collision else "Created Synthetic Node"
    )
    create_aliases = [
        "Existing Synthetic Alias" if alias_collision else "Created Synthetic Alias"
    ]
    node_records = [
        _node_record(CREATE, create_name, CREATE_NODE_ID, aliases=create_aliases),
        _node_record(
            REUSE,
            "Existing Synthetic Node",
            "NODE_SYNTHETIC_REUSE_PROSPECTIVE",
            reuse_target=REUSE_NODE_ID,
        ),
        _node_record(DEFER, "Deferred Synthetic Node", "NODE_SYNTHETIC_DEFERRED"),
        _node_record(REJECT, "Rejected Synthetic Node", "NODE_SYNTHETIC_REJECTED"),
    ]
    node_review_body = {
        "document_type": "phase3e_node_operation_review",
        "schema_version": "1",
        "review_status": "DRAFT",
        "operational_run": {
            "run_id": RUN_ID,
            "source_sha256": source_sha256,
            "claim_review_sha256": sha256_file(claim_review_path),
        },
        "records": node_records,
        "production_baseline": baseline,
        "audit_operations": {"relations": []},
    }
    node_review = _semantic_artifact(
        node_review_body,
        id_field="review_id",
        hash_field="review_sha256",
        prefix="NODE_REVIEW",
    )
    node_review_path = run_root / "review" / "node_operation_review.json"
    _write(node_review_path, node_review)

    parent_suggestion = {
        "suggestion_id": PARENT,
        "candidate_id": CREATE,
        "prospective_child_node_id": CREATE_NODE_ID,
        "parent_node_id": PARENT_NODE_ID,
        "suggestion_type": "SYNTHETIC_PARENT",
        "governance_status": "HUMAN_REVIEW_REQUIRED",
        "authorized_by_node_create": False,
        "human_decision": "PENDING",
        "executable": False,
    }
    preview_body = {
        "document_type": "phase3e_non_executable_promotion_preview",
        "schema_version": "1",
        "run_id": RUN_ID,
        "source_sha256": source_sha256,
        "parent_placement_suggestions": [parent_suggestion],
        "authorization": {
            "human_claim_decisions_bound": False,
            "human_node_decisions_bound": False,
            "executable": False,
            "production_apply_authorized": False,
            "production_executor_compatible": False,
            "intended_mutations_generated": False,
        },
        "bindings": {"production_baseline": baseline},
    }
    preview = _semantic_artifact(
        preview_body,
        id_field="preview_id",
        hash_field="preview_sha256",
        prefix="PROMOTION_PREVIEW",
    )
    preview_path = run_root / "promotion" / "promotion_preview.json"
    _write(preview_path, preview)

    relative_paths = [
        "evidence/evidence_bound_extraction_bundle.json",
        "review/claim_review.json",
        "review/node_operation_review.json",
        "promotion/promotion_preview.json",
        "source/synthetic-source.txt",
    ]
    inventory = [
        {
            "path": relative,
            "sha256": sha256_file(run_root / relative),
            "size_bytes": (run_root / relative).stat().st_size,
        }
        for relative in relative_paths
    ]
    manifest = {
        "document_type": "phase3e_operational_ingestion_manifest",
        "schema_version": "1",
        "run_id": RUN_ID,
        "repository_commit": COMMIT,
        "stage_status": "HUMAN_REVIEW_REQUIRED",
        "source": {
            "source_id": SOURCE_ID,
            "filename": source_path.name,
            "sha256": source_sha256,
            "size_bytes": len(source_bytes),
            "source_type": "SYNTHETIC_TEXT",
            "frozen_relative_path": "source/synthetic-source.txt",
            "frozen_copy_sha256": source_sha256,
        },
        "production_baseline": baseline,
        "artifact_inventory": inventory,
    }
    _write(run_root / "run_manifest.json", manifest)

    completed = build_blank_review_packet(run_root)
    completed["human_completion"]["reviewer"] = REVIEWER
    claim_decisions = {KEEP: "KEEP", DROP: "DROP", NEEDS_REVIEW: "KEEP_NEEDS_REVIEW"}
    for record in completed["claims"]:
        record["human_input"].update(
            {"decision": claim_decisions[record["candidate_id"]], "reason": REASON}
        )
    node_decisions = {
        CREATE: ("CREATE", ""),
        REUSE: ("REUSE", REUSE_NODE_ID),
        DEFER: ("DEFER", ""),
        REJECT: ("REJECT", ""),
    }
    for record in completed["nodes"]:
        decision, target = node_decisions[record["candidate_id"]]
        record["human_input"].update(
            {"decision": decision, "reason": REASON, "target_node_id": target}
        )
    completed["relations"][0]["human_input"].update(
        {"decision": "CREATE", "reason": REASON}
    )
    completion = validate_completed_review_packet(completed, run_root)
    completed_path = root / "completed-review.json"
    _write(completed_path, completed)

    authorization_body = {
        "document_type": "synthetic_human_operational_authorization",
        "schema_version": "1",
        "authorization_status": "SYNTHETIC_USER_HUMAN_REVIEW",
        "reviewer": REVIEWER,
        "packet_binding": {
            "packet_id": completed["packet_id"],
            "immutable_packet_sha256": completed["immutable_packet_sha256"],
            "run_id": RUN_ID,
            "source_id": SOURCE_ID,
            "source_sha256": source_sha256,
        },
        "safety": {
            "production_authorization": False,
            "production_apply_authorized": False,
        },
    }
    authorization = {
        **authorization_body,
        "authorization_semantic_sha256": canonical_sha256(authorization_body),
    }
    authorization_path = root / "authorization.json"
    _write(authorization_path, authorization)

    receipt_body = {
        "document_type": "synthetic_operational_review_completion_receipt",
        "schema_version": "1",
        "status": "HUMAN_REVIEW_COMPLETE_AND_VALID",
        "reviewer": REVIEWER,
        "packet_id": completed["packet_id"],
        "run_id": RUN_ID,
        "source_id": SOURCE_ID,
        "source_sha256": source_sha256,
        "authorization_file_sha256": sha256_file(authorization_path),
        "authorization_semantic_sha256": authorization[
            "authorization_semantic_sha256"
        ],
        "authorization_artifact": {
            "role": "human_operational_authorization",
            "file_sha256": sha256_file(authorization_path),
        },
        "completed_artifacts": [
            {
                "role": "completed_operational_review_packet",
                "file_sha256": sha256_file(completed_path),
            }
        ],
        "completion_validation": completion,
        "completion_checks": {"all_human_decisions_complete": True},
        "production_before": {"sha256": production["sha256"]},
        "safety": {
            "production_apply_authorized": False,
            "production_mutation_permitted": False,
        },
    }
    completion_receipt = _receipt(receipt_body, "SYNTHETIC_COMPLETION")
    receipt_path = root / "completion-receipt.json"
    _write(receipt_path, completion_receipt)
    return {
        "root": root,
        "run_root": run_root,
        "production_path": production_path,
        "completed_path": completed_path,
        "authorization_path": authorization_path,
        "receipt_path": receipt_path,
        "production": production,
    }


def _kwargs(case: dict) -> dict:
    return {
        "completed_packet_path": case["completed_path"],
        "authorization_path": case["authorization_path"],
        "completion_receipt_path": case["receipt_path"],
        "run_root": case["run_root"],
        "production_path": case["production_path"],
        "repository_root": case["root"],
    }


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rewrite(path: Path, value: dict) -> None:
    _write(path, value)


def _rehash_payload(payload: dict) -> dict:
    body = payload_semantic_body(payload)
    digest = canonical_sha256(body)
    return {
        **body,
        "payload_id": f"PROMO_{digest[:16].upper()}",
        "payload_hash": digest,
    }


def test_generic_handoff_builds_one_phase3d_payload_and_is_deterministic(
    tmp_path: Path,
) -> None:
    case = _make_case(tmp_path)
    first = build_operational_handoff_artifacts(**_kwargs(case))
    second = build_operational_handoff_artifacts(**_kwargs(case))
    assert_deterministic_handoff(first, second)

    mapping = first["handoff_mapping.json"]
    payload = first["promotion_payload.json"]
    validation = first["phase3d_validation_receipt.json"]["phase3d_validation"]
    receipt = first["operational_handoff_receipt.json"]
    assert mapping["counts"] == {
        "total_candidates": 8,
        "executable": 4,
        "blocked": 4,
        "by_candidate_type": {"CLAIM": 3, "NODE": 4, "PARENT_PLACEMENT": 1},
        "by_human_decision": {
            "CREATE": 2,
            "DEFER": 1,
            "DROP": 1,
            "KEEP": 1,
            "KEEP_NEEDS_REVIEW": 1,
            "REJECT": 1,
            "REUSE": 1,
        },
        "by_disposition": {
            "BLOCKED_HUMAN_DEFER": 1,
            "BLOCKED_HUMAN_DROP": 1,
            "BLOCKED_HUMAN_KEEP_NEEDS_REVIEW": 1,
            "BLOCKED_HUMAN_REJECT": 1,
            "EXECUTABLE": 4,
        },
    }
    assert [item["table"] for item in payload["intended_mutations"]] == [
        "sources",
        "claims",
        "nodes",
        "node_aliases",
        "node_relations",
    ]
    assert payload["metadata"]["repository_commit"] == COMMIT
    assert payload["production_authorization"] is False
    assert payload["production_apply_authorized"] is False
    assert payload["full_operational_review_complete"] is True
    assert payload["link_operations"] == []
    assert validation["payload_validation"] == "PASS"
    assert validation["shadow_apply"] == "COMMITTED"
    assert validation["semantic_diff"] == "PASS"
    assert validation["idempotent_replay"] == "PASS"
    assert validation["rollback_qualification"] == "PASS"
    assert validation["production_final_apply_rejection"] == (
        "FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH"
    )
    assert receipt["no_silent_loss"] is True
    assert production_identity(case["production_path"]) == case["production"]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("document_type", "wrong_packet", "OPERATIONAL_PACKET_DOCUMENT_TYPE_INVALID"),
        ("schema_version", "999", "OPERATIONAL_PACKET_SCHEMA_VERSION_INVALID"),
    ],
)
def test_wrong_operational_packet_identity_fails_closed(
    tmp_path: Path, field: str, value: str, error: str
) -> None:
    case = _make_case(tmp_path)
    packet = _load(case["completed_path"])
    packet[field] = value
    _rewrite(case["completed_path"], packet)
    with pytest.raises(OperationalHandoffError, match=error):
        validate_operational_handoff_inputs(**_kwargs(case))


def test_incomplete_review_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    packet = _load(case["completed_path"])
    packet["claims"][0]["human_input"]["decision"] = ""
    _rewrite(case["completed_path"], packet)
    with pytest.raises(ReviewCompletionError, match="MISSING_DECISION"):
        validate_operational_handoff_inputs(**_kwargs(case))


def test_candidate_content_hash_drift_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    packet = _load(case["completed_path"])
    packet["claims"][0]["content_sha256"] = "0" * 64
    _rewrite(case["completed_path"], packet)
    with pytest.raises(ReviewCompletionError, match="IMMUTABLE_FIELDS_CHANGED"):
        validate_operational_handoff_inputs(**_kwargs(case))


@pytest.mark.parametrize(
    ("section", "field", "value", "error"),
    [
        ("run", "run_id", "INGEST_OTHER", "AUTHORIZATION_PACKET_BINDING_MISMATCH"),
        ("source", "source_id", "SRC_OTHER", "AUTHORIZATION_PACKET_BINDING_MISMATCH"),
    ],
)
def test_source_and_run_mismatch_fail_closed(
    tmp_path: Path, section: str, field: str, value: str, error: str
) -> None:
    case = _make_case(tmp_path)
    packet = _load(case["completed_path"])
    packet[section][field] = value
    _rewrite(case["completed_path"], packet)
    with pytest.raises(OperationalHandoffError, match=error):
        validate_operational_handoff_inputs(**_kwargs(case))


def test_production_baseline_mismatch_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    with sqlite3.connect(case["production_path"]) as connection:
        connection.execute(
            """INSERT INTO nodes(
               node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                "NODE_SYNTHETIC_DRIFT",
                "Synthetic Drift",
                "Product",
                "",
                "active",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
    with pytest.raises(OperationalHandoffError, match="PRODUCTION_BASELINE_MISMATCH"):
        validate_operational_handoff_inputs(**_kwargs(case))


def test_completion_receipt_mismatch_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    receipt = _load(case["receipt_path"])
    receipt["source_id"] = "SRC_OTHER"
    _rewrite(case["receipt_path"], receipt)
    with pytest.raises(
        OperationalHandoffError, match="COMPLETION_RECEIPT_HASH_MISMATCH"
    ):
        validate_operational_handoff_inputs(**_kwargs(case))


def test_human_authorization_mismatch_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    authorization = _load(case["authorization_path"])
    authorization["packet_binding"]["packet_id"] = "REVIEW_PACKET_OTHER"
    _rewrite(case["authorization_path"], authorization)
    with pytest.raises(
        OperationalHandoffError, match="AUTHORIZATION_SEMANTIC_HASH_MISMATCH"
    ):
        validate_operational_handoff_inputs(**_kwargs(case))


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("decision", "ACCEPT", "UNKNOWN_DECISION"),
        ("reason", "", "MISSING_REVIEW_REASON"),
    ],
)
def test_unknown_decision_and_missing_reason_fail_closed(
    tmp_path: Path, field: str, value: str, error: str
) -> None:
    case = _make_case(tmp_path)
    packet = _load(case["completed_path"])
    packet["claims"][0]["human_input"][field] = value
    _rewrite(case["completed_path"], packet)
    with pytest.raises(ReviewCompletionError, match=error):
        validate_operational_handoff_inputs(**_kwargs(case))


def test_reuse_without_exact_target_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    packet = _load(case["completed_path"])
    record = next(item for item in packet["nodes"] if item["candidate_id"] == REUSE)
    record["human_input"]["target_node_id"] = ""
    _rewrite(case["completed_path"], packet)
    with pytest.raises(ReviewCompletionError, match="REUSE_TARGET_REQUIRED"):
        validate_operational_handoff_inputs(**_kwargs(case))


@pytest.mark.parametrize("claim_id", [DROP, NEEDS_REVIEW])
def test_non_promotable_claim_cannot_appear_as_executable(
    tmp_path: Path, claim_id: str
) -> None:
    case = _make_case(tmp_path)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    payload = copy.deepcopy(artifacts["promotion_payload.json"])
    claim = next(item for item in payload["claims"] if item["claim_id"] == claim_id)
    claim["executable"] = True
    payload = _rehash_payload(payload)
    with pytest.raises(
        (PromotionError, OperationalHandoffError),
        match="EXECUTABLE_CLAIM_MUTATION_COUNT_MISMATCH|NON_KEEP_CLAIM_EXECUTABLE",
    ):
        validate_handoff_payload(payload)


@pytest.mark.parametrize(("candidate_id", "decision"), [(DEFER, "DEFER"), (REJECT, "REJECT")])
def test_non_promotable_node_cannot_appear_as_executable(
    tmp_path: Path, candidate_id: str, decision: str
) -> None:
    case = _make_case(tmp_path)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    payload = copy.deepcopy(artifacts["promotion_payload.json"])
    operation = next(
        item for item in payload["node_operations"] if item["candidate_id"] == candidate_id
    )
    operation["executable"] = True
    payload = _rehash_payload(payload)
    with pytest.raises(PromotionError, match=f"AUDIT_ONLY_OPERATION_MARKED_EXECUTABLE:{decision}"):
        validate_handoff_payload(payload)


def test_alias_collision_is_explicitly_blocked(tmp_path: Path) -> None:
    case = _make_case(tmp_path, alias_collision=True)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    mapping = artifacts["handoff_mapping.json"]
    record = next(item for item in mapping["records"] if item["candidate_id"] == CREATE)
    assert record["disposition"] == "BLOCKED_EXISTING_PAYLOAD_CONTRACT"
    assert record["block_reason"] == "ALIAS_COLLISION:Existing Synthetic Alias"
    assert all(
        item["key"].get("node_id") != CREATE_NODE_ID
        for item in artifacts["promotion_payload.json"]["intended_mutations"]
    )


def test_create_collision_is_explicitly_blocked(tmp_path: Path) -> None:
    case = _make_case(tmp_path, create_collision=True)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    mapping = artifacts["handoff_mapping.json"]
    record = next(item for item in mapping["records"] if item["candidate_id"] == CREATE)
    assert record["disposition"] == "BLOCKED_EXISTING_PAYLOAD_CONTRACT"
    assert record["block_reason"].startswith("CANONICAL_COLLISION:")
    assert all(
        item["key"].get("node_id") != CREATE_NODE_ID
        for item in artifacts["promotion_payload.json"]["intended_mutations"]
    )


def test_silent_candidate_omission_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    mapping = copy.deepcopy(artifacts["handoff_mapping.json"])
    mapping["records"].pop()
    body = {
        key: value
        for key, value in mapping.items()
        if key not in {"mapping_id", "mapping_sha256"}
    }
    digest = canonical_sha256(body)
    mapping["mapping_id"] = f"HANDOFF_MAPPING_{digest[:16].upper()}"
    mapping["mapping_sha256"] = digest
    with pytest.raises(OperationalHandoffError, match="SILENT_CANDIDATE_OMISSION"):
        validate_handoff_accounting(mapping, artifacts["promotion_payload.json"])


def test_invented_relation_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    payload = copy.deepcopy(artifacts["promotion_payload.json"])
    payload["relation_operations"].append(
        {
            "operation_id": "OP_REL_INVENTED",
            "candidate_id": "PARENT_PLACEMENT_INVENTED",
            "candidate": {
                "relation_type": "part_of",
                "prospective_child_node_id": CREATE_NODE_ID,
                "parent_node_id": PARENT_NODE_ID,
            },
            "operation": "CREATE",
            "executable": True,
            "reason": "invented",
            "final_relation": {
                "relation_id": "REL_INVENTED",
                "from_node_id": CREATE_NODE_ID,
                "relation_type": "part_of",
                "to_node_id": PARENT_NODE_ID,
            },
        }
    )
    payload = _rehash_payload(payload)
    with pytest.raises(OperationalHandoffError, match="NON_AUTHORIZED_RELATION_EXECUTABLE"):
        validate_handoff_payload(payload)


@pytest.mark.parametrize(
    "field", ["production_authorization", "production_apply_authorized"]
)
def test_production_authority_cannot_be_enabled(
    tmp_path: Path, field: str
) -> None:
    case = _make_case(tmp_path)
    artifacts = build_operational_handoff_artifacts(**_kwargs(case))
    payload = copy.deepcopy(artifacts["promotion_payload.json"])
    payload[field] = True
    payload = _rehash_payload(payload)
    with pytest.raises(OperationalHandoffError, match=f"HANDOFF_BOUNDARY_INVALID: {field}"):
        validate_handoff_payload(payload)


def test_deterministic_rerun_mismatch_fails_closed(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    first = build_operational_handoff_artifacts(**_kwargs(case))
    second = copy.deepcopy(first)
    second["promotion_payload.json"]["payload_id"] = "PROMO_DIFFERENT"
    with pytest.raises(OperationalHandoffError, match="DETERMINISTIC_RERUN_MISMATCH"):
        assert_deterministic_handoff(first, second)
