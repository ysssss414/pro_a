from __future__ import annotations

import copy
import json
import os
import shutil
import sqlite3
from pathlib import Path

import pytest

from pro_a.production_promotion import (
    ArtifactPaths,
    PILOT6_EXPECTED_ARTIFACT_HASHES,
    PromotionError,
    apply_payload_to_shadow,
    assert_shadow_target,
    build_identity_catalog,
    build_promotion_payload,
    canonical_sha256,
    converge_phase3c_artifacts,
    connect_read_only,
    copy_production_to_shadow,
    database_identity,
    decide_node_operation,
    payload_semantic_body,
    production_identity,
    qualify_shadow_promotion,
    resolve_identity,
    sha256_file,
    validate_executable_operations,
    validate_payload,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "workspace" / "phase3c" / "PILOT_20260902_572A6DF2"
STAGE3D2 = ROOT / "workspace" / "phase3d" / "STAGE3D2_QUALIFICATION_F6A9ECB_V2"
PRODUCTION = STAGE3D2 / "production_shadow_restore.db"
SIGNOFF = ROOT / "artifacts" / "phase3c" / "pilot6_delegated_reviewer_signoff.json"
PILOT6_AVAILABLE = all((
    (RUN_DIR / "extraction_bundle_stage1_1_rebound.json").is_file(),
    (RUN_DIR / "pilot6_table_claim_safety_boundary.json").is_file(),
    (RUN_DIR / "extraction_review_draft.json").is_file(),
    SIGNOFF.is_file(),
    PRODUCTION.is_file(),
))
requires_pilot6 = pytest.mark.skipif(not PILOT6_AVAILABLE, reason="Frozen local Pilot 6 qualification artifacts unavailable")


def artifact_paths(root: Path = RUN_DIR, signoff: Path = SIGNOFF) -> ArtifactPaths:
    return ArtifactPaths(
        rebound_bundle=root / "extraction_bundle_stage1_1_rebound.json",
        table_boundary=root / "pilot6_table_claim_safety_boundary.json",
        reviewer_signoff=signoff,
        review_draft=root / "extraction_review_draft.json",
    )


@pytest.fixture(scope="session")
def converged() -> dict:
    if not PILOT6_AVAILABLE:
        pytest.skip("Frozen local Pilot 6 qualification artifacts unavailable")
    return converge_phase3c_artifacts(
        artifact_paths(), expected_hashes=PILOT6_EXPECTED_ARTIFACT_HASHES,
    )


@pytest.fixture(scope="session")
def production() -> dict:
    if not PILOT6_AVAILABLE:
        pytest.skip("Configured Production fixture unavailable")
    return production_identity(PRODUCTION)


@pytest.fixture(scope="session")
def payload(converged: dict, production: dict) -> dict:
    return build_promotion_payload(
        converged,
        production,
        repository_commit="f6a9ecb55a53052656fb6ecb8ac95aea2d7e956d",
    )


def rehash(value: dict) -> dict:
    result = copy.deepcopy(value)
    digest = canonical_sha256(payload_semantic_body(result))
    result["payload_hash"] = digest
    result["payload_id"] = f"PROMO_{digest[:16].upper()}"
    return result


def copy_artifacts(tmp_path: Path) -> tuple[ArtifactPaths, dict[str, str]]:
    run = tmp_path / "run"
    run.mkdir()
    bundle = run / "extraction_bundle_stage1_1_rebound.json"
    boundary = run / "pilot6_table_claim_safety_boundary.json"
    review_draft = run / "extraction_review_draft.json"
    signoff = tmp_path / "signoff.json"
    shutil.copy2(RUN_DIR / bundle.name, bundle)
    shutil.copy2(RUN_DIR / boundary.name, boundary)
    shutil.copy2(RUN_DIR / review_draft.name, review_draft)
    shutil.copy2(SIGNOFF, signoff)
    return artifact_paths(run, signoff), dict(PILOT6_EXPECTED_ARTIFACT_HASHES)


def rewrite_json(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_expected(expected: dict[str, str], role: str, path: Path) -> None:
    expected[role] = sha256_file(path)


@requires_pilot6
def test_exact_pilot6_artifact_convergence_107_to_104(converged: dict):
    assert converged["counts"] == {
        "raw_claims": 107,
        "table_ineligible": 3,
        "admitted_review_surface": 104,
        "review_keep": 104,
        "executable_accepted_claims": 104,
    }
    assert converged["ineligible_claim_ids"] == [
        "CLM_20260902_35679678",
        "CLM_20260902_438AEFC8",
        "CLM_20260902_22A043B8",
    ]
    assert converged["review_draft"]["status"] == "DRAFT"
    assert {claim["decision"] for claim in converged["review_draft"]["claims"]} == {"PENDING"}


@requires_pilot6
def test_modified_artifact_hash_fails(tmp_path: Path):
    paths, expected = copy_artifacts(tmp_path)
    paths.rebound_bundle.write_bytes(paths.rebound_bundle.read_bytes() + b"\n")
    with pytest.raises(PromotionError, match="ARTIFACT_HASH_MISMATCH:phase3c_rebound_bundle"):
        converge_phase3c_artifacts(paths, expected_hashes=expected)


@requires_pilot6
@pytest.mark.parametrize("change", ["missing", "extra"])
def test_missing_or_extra_claim_fails(tmp_path: Path, change: str):
    paths, expected = copy_artifacts(tmp_path)

    def mutate(bundle: dict) -> None:
        if change == "missing":
            bundle["claims"].pop()
        else:
            extra = copy.deepcopy(bundle["claims"][-1])
            extra["claim_id"] = "CLM_20260902_EXTRA0001"
            bundle["claims"].append(extra)

    rewrite_json(paths.rebound_bundle, mutate)
    update_expected(expected, "phase3c_rebound_bundle", paths.rebound_bundle)
    with pytest.raises(PromotionError):
        converge_phase3c_artifacts(paths, expected_hashes=expected)


@requires_pilot6
def test_reviewer_surface_mismatch_fails(tmp_path: Path):
    paths, expected = copy_artifacts(tmp_path)
    rewrite_json(paths.reviewer_signoff, lambda value: value.__setitem__("review_surface_sha256", "0" * 64))
    update_expected(expected, "delegated_reviewer_signoff", paths.reviewer_signoff)
    with pytest.raises(PromotionError, match="REVIEW_SURFACE_MISMATCH"):
        converge_phase3c_artifacts(paths, expected_hashes=expected)


@requires_pilot6
def test_incorrect_table_decision_fails(tmp_path: Path):
    paths, expected = copy_artifacts(tmp_path)

    def mutate(boundary: dict) -> None:
        boundary["result"]["decisions"][0]["review_eligible"] = False

    rewrite_json(paths.table_boundary, mutate)
    update_expected(expected, "table_claim_safety_boundary", paths.table_boundary)
    with pytest.raises(PromotionError, match="INCORRECT_TABLE_DECISION"):
        converge_phase3c_artifacts(paths, expected_hashes=expected)


@requires_pilot6
def test_payload_is_deterministic_with_deterministic_ids_and_hash(converged: dict, production: dict):
    first = build_promotion_payload(converged, production, repository_commit="f6a9ecb")
    second = build_promotion_payload(converged, production, repository_commit="f6a9ecb")
    assert first == second
    assert first["payload_id"] == second["payload_id"]
    assert first["payload_hash"] == canonical_sha256(payload_semantic_body(first))


@requires_pilot6
def test_payload_binds_baseline_and_changes_when_baseline_changes(converged: dict, production: dict):
    first = build_promotion_payload(converged, production, repository_commit="f6a9ecb")
    different = copy.deepcopy(production)
    different["sha256"] = "0" * 64
    second = build_promotion_payload(converged, different, repository_commit="f6a9ecb")
    assert first["payload_hash"] != second["payload_hash"]
    assert first["metadata"]["production_counts"] == production["counts"]
    assert len(first["metadata"]["input_artifact_roles_and_sha256"]) == 4
    assert first["audit"]["generic_review_draft"]["authorization_used"] is False


@requires_pilot6
def test_payload_preserves_audit_chain_and_excludes_audit_only_operations(payload: dict):
    evidence_ids = {item["evidence_id"] for item in payload["evidence"]}
    assert len(payload["claims"]) == 107
    assert all(claim["evidence_id"] in evidence_ids for claim in payload["claims"])
    assert sum(claim["executable"] for claim in payload["claims"]) == 104
    assert {item["table"] for item in payload["intended_mutations"]} == {"sources", "claims"}
    mutation_authorities = {item["authorized_by"] for item in payload["intended_mutations"]}
    assert not mutation_authorities.intersection(
        operation["operation_id"]
        for operation in payload["node_operations"] + payload["relation_operations"]
    )


@requires_pilot6
def test_accepted_claim_does_not_authorize_node_or_relation_mutation(payload: dict):
    assert payload["audit"]["operation_inventory"]["node"] == {
        "CREATE": 0, "DEFER": 26, "REJECT": 32, "REUSE": 0, "UPDATE": 0,
    }
    assert payload["audit"]["operation_inventory"]["relation"] == {
        "CREATE": 0, "DEFER": 0, "REJECT": 10, "REUSE": 0, "UPDATE": 0,
    }
    assert all(not operation["executable"] for operation in payload["node_operations"])
    assert all(not operation["executable"] for operation in payload["relation_operations"])


def test_exact_reviewed_create_and_reuse_decisions():
    catalog = build_identity_catalog(
        [{"node_id": "NODE_EXISTING", "canonical_name": "Existing", "primary_type": "Technology", "status": "active"}],
        [{"alias": "Existing Alias", "node_id": "NODE_EXISTING"}],
    )
    create = decide_node_operation(
        {"canonical_name": "New Node", "primary_type": "Technology", "aliases": ["New Alias"]},
        requested_operation="CREATE",
        review_decision="APPROVE_CREATE",
        catalog=catalog,
        run_id="RUN",
    )
    reuse = decide_node_operation(
        {"canonical_name": "Existing", "match_term": "Existing Alias", "primary_type": "Technology"},
        requested_operation="REUSE",
        review_decision="APPROVE_REUSE",
        catalog=catalog,
        run_id="RUN",
    )
    assert create["operation"] == "CREATE" and create["executable"]
    assert reuse["operation"] == "REUSE" and reuse["resolved_target_id"] == "NODE_EXISTING"


@pytest.mark.parametrize(
    ("nodes", "aliases", "reason"),
    [
        ([], [], "ZERO_MATCH_REUSE"),
        (
            [
                {"node_id": "N1", "canonical_name": "One", "primary_type": "Technology", "status": "active"},
                {"node_id": "N2", "canonical_name": "Two", "primary_type": "Technology", "status": "active"},
            ],
            [{"alias": "Shared", "node_id": "N1"}, {"alias": "Shared", "node_id": "N2"}],
            "AMBIGUOUS_REUSE",
        ),
    ],
)
def test_zero_or_ambiguous_reuse_defers_and_never_creates(nodes: list[dict], aliases: list[dict], reason: str):
    catalog = build_identity_catalog(nodes, aliases)
    operation = decide_node_operation(
        {"canonical_name": "Shared", "match_term": "Shared", "primary_type": "Technology"},
        requested_operation="REUSE",
        review_decision="APPROVE_REUSE",
        catalog=catalog,
        run_id="RUN",
    )
    assert operation["operation"] == "DEFER"
    assert operation["reason"] == reason
    assert not operation["executable"]


def test_inactive_or_type_incompatible_reuse_defers():
    catalog = build_identity_catalog(
        [{"node_id": "N1", "canonical_name": "Target", "primary_type": "Company", "status": "inactive"}],
        [],
    )
    operation = decide_node_operation(
        {"canonical_name": "Target", "primary_type": "Technology"},
        requested_operation="REUSE",
        review_decision="APPROVE_REUSE",
        catalog=catalog,
        run_id="RUN",
    )
    assert operation["operation"] == "DEFER"
    assert operation["reason"] == "REUSE_TARGET_INACTIVE_OR_TYPE_INCOMPATIBLE"


@requires_pilot6
def test_update_non_structural_relation_and_unsupported_operation_fail_closed(payload: dict):
    update = copy.deepcopy(payload)
    update["node_operations"].append({
        "operation_id": "OP_UPDATE", "operation": "UPDATE", "executable": True,
    })
    with pytest.raises(PromotionError, match="UPDATE_NOT_EXECUTABLE"):
        validate_payload(rehash(update))

    relation = copy.deepcopy(payload)
    relation["relation_operations"].append({
        "operation_id": "OP_REL", "operation": "CREATE", "executable": True,
        "final_relation": {"relation_type": "uses"},
    })
    with pytest.raises(PromotionError, match="NON_STRUCTURAL_RELATION"):
        validate_payload(rehash(relation))

    unsupported = copy.deepcopy(payload)
    unsupported["node_operations"].append({
        "operation_id": "OP_BAD", "operation": "UPSERT", "executable": False,
    })
    with pytest.raises(PromotionError, match="UNSUPPORTED_OPERATION"):
        validate_payload(rehash(unsupported))


def executable_create(node_id: str, canonical: str, aliases: list[str] | None = None) -> dict:
    return {
        "operation_id": f"OP_{node_id}",
        "candidate_id": f"CAND_{node_id}",
        "operation": "CREATE",
        "executable": True,
        "candidate": {"canonical_name": canonical, "primary_type": "Technology"},
        "aliases": aliases or [],
        "final_node": {
            "node_id": node_id,
            "canonical_name": canonical,
            "primary_type": "Technology",
            "description": "",
            "status": "active",
            "created_at": "2026-09-02T00:00:00+08:00",
            "updated_at": "2026-09-02T00:00:00+08:00",
        },
    }


def with_node_operations(payload: dict, operations: list[dict]) -> dict:
    changed = copy.deepcopy(payload)
    changed["node_operations"] = operations
    changed["relation_operations"] = []
    changed["excluded_operations"] = []
    return rehash(changed)


@requires_pilot6
def test_node_id_canonical_alias_and_package_internal_collisions(payload: dict):
    connection = connect_read_only(PRODUCTION)
    try:
        node = dict(connection.execute("SELECT node_id,canonical_name FROM nodes ORDER BY node_id LIMIT 1").fetchone())
        alias = connection.execute("SELECT alias FROM node_aliases ORDER BY alias LIMIT 1").fetchone()[0]
        with pytest.raises(PromotionError, match="NODE_ID_COLLISION"):
            validate_executable_operations(connection, with_node_operations(payload, [executable_create(node["node_id"], "Unique Stage3D Name")]))
        with pytest.raises(PromotionError, match="CANONICAL_COLLISION"):
            validate_executable_operations(connection, with_node_operations(payload, [executable_create("NODE_NEW_CANON", node["canonical_name"])]))
        with pytest.raises(PromotionError, match="ALIAS_COLLISION"):
            validate_executable_operations(connection, with_node_operations(payload, [executable_create("NODE_NEW_ALIAS", "Unique Alias Owner", [alias])]))
        package = [
            executable_create("NODE_PACKAGE_1", "Ｍemory"),
            executable_create("NODE_PACKAGE_2", "memory"),
        ]
        with pytest.raises(PromotionError, match="PACKAGE_INTERNAL_COLLISION"):
            validate_executable_operations(connection, with_node_operations(payload, package))
    finally:
        connection.close()


@requires_pilot6
def test_reuse_target_drift_and_inactive_target_fail(payload: dict, tmp_path: Path):
    shadow = tmp_path / "drift.db"
    shutil.copy2(PRODUCTION, shadow)
    connection = sqlite3.connect(shadow)
    connection.row_factory = sqlite3.Row
    try:
        target = dict(connection.execute(
            "SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE status='active' ORDER BY node_id LIMIT 1"
        ).fetchone())
        operation = {
            "operation_id": "OP_REUSE", "candidate_id": "CAND_REUSE",
            "operation": "REUSE", "executable": True,
            "candidate": {"canonical_name": target["canonical_name"], "primary_type": target["primary_type"]},
            "resolved_target_id": target["node_id"],
            "resolution": {"term": target["canonical_name"]},
            "expected_target": {**target, "canonical_name": target["canonical_name"] + " drift"},
            "approved_aliases": [],
        }
        with pytest.raises(PromotionError, match="REUSE_TARGET_DRIFT"):
            validate_executable_operations(connection, with_node_operations(payload, [operation]))

        operation["expected_target"] = target
        connection.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (target["node_id"],))
        connection.commit()
        operation["expected_target"] = {**target, "status": "inactive"}
        with pytest.raises(PromotionError, match="REUSE_TARGET_INACTIVE"):
            validate_executable_operations(connection, with_node_operations(payload, [operation]))
    finally:
        connection.close()


@requires_pilot6
def test_configured_production_path_and_samefile_are_hard_blocked(payload: dict):
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        apply_payload_to_shadow(payload, PRODUCTION, PRODUCTION)
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        assert_shadow_target(PRODUCTION.parent / "." / PRODUCTION.name, PRODUCTION)


@requires_pilot6
def test_symlink_equivalent_production_path_is_blocked(tmp_path: Path):
    link = tmp_path / "production-link.db"
    try:
        os.symlink(PRODUCTION, link)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this platform")
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        assert_shadow_target(link, PRODUCTION)


@requires_pilot6
def test_shadow_apply_exact_delta_fk_integrity_and_idempotency(payload: dict, production: dict, tmp_path: Path):
    shadow = tmp_path / "shadow.db"
    copy_production_to_shadow(PRODUCTION, shadow, production["sha256"])
    first = apply_payload_to_shadow(payload, shadow, PRODUCTION)
    second = apply_payload_to_shadow(payload, shadow, PRODUCTION)
    assert first["status"] == "COMMITTED"
    assert first["changed_tables"] == {
        "claims": {"added": 104, "removed": 0},
        "sources": {"added": 1, "removed": 0},
    }
    assert first["foreign_key_violations"] == []
    assert first["integrity"] == "ok"
    assert second["status"] == "ALREADY_APPLIED"
    assert second["changed_tables"] == {}


@requires_pilot6
def test_conflicting_replay_fails(payload: dict, production: dict, tmp_path: Path):
    shadow = tmp_path / "shadow.db"
    copy_production_to_shadow(PRODUCTION, shadow, production["sha256"])
    apply_payload_to_shadow(payload, shadow, PRODUCTION)
    connection = sqlite3.connect(shadow)
    try:
        connection.execute(
            "UPDATE claims SET statement=statement || ' drift' WHERE claim_id=?",
            (next(item["claim_id"] for item in payload["claims"] if item["executable"]),),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(PromotionError, match="PAYLOAD_REPLAY_CONFLICT"):
        apply_payload_to_shadow(payload, shadow, PRODUCTION)


@requires_pilot6
def test_injected_failure_rolls_back_semantic_state(payload: dict, production: dict, tmp_path: Path):
    shadow = tmp_path / "rollback.db"
    copy_production_to_shadow(PRODUCTION, shadow, production["sha256"])
    before = database_identity(shadow)
    with pytest.raises(PromotionError, match="INJECTED_TRANSACTION_FAILURE"):
        apply_payload_to_shadow(payload, shadow, PRODUCTION, inject_failure_after=2)
    after = database_identity(shadow)
    assert after["semantic_snapshot"] == before["semantic_snapshot"]
    assert after["counts"] == before["counts"]


@requires_pilot6
def test_qualification_proves_restore_and_production_unchanged(payload: dict, production: dict, tmp_path: Path, monkeypatch):
    from pro_a.db import Database

    def forbidden_init_schema(_self):
        raise AssertionError("init_schema must not run")

    monkeypatch.setattr(Database, "init_schema", forbidden_init_schema)
    pre_sha = sha256_file(PRODUCTION)
    pre_sidecars = {suffix: Path(f"{PRODUCTION}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal")}
    receipt = qualify_shadow_promotion(
        payload,
        production_path=PRODUCTION,
        shadow_path=tmp_path / "qualified.db",
        receipt_path=tmp_path / "receipt.json",
    )
    post_sidecars = {suffix: Path(f"{PRODUCTION}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal")}
    assert receipt["status"] == "PASS"
    assert receipt["rollback"]["semantic_state_restored"] is True
    assert receipt["rollback"]["restore_drill_pass"] is True
    assert receipt["production"]["changed"] is False
    assert receipt["production"]["apply_attempted"] is False
    assert sha256_file(PRODUCTION) == pre_sha == production["sha256"]
    assert post_sidecars == pre_sidecars == {"-wal": False, "-shm": False, "-journal": False}
