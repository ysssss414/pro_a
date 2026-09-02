from __future__ import annotations

import copy
import json
import shutil
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from pro_a.production_final_qualification import (
    EXPECTED_ARCHIVE_PATH,
    EXPECTED_DECISION_COUNTS,
    EXPECTED_HUMAN_REVIEW_FILE_SHA256,
    EXPECTED_SOURCE_ID,
    EXPECTED_SOURCE_NAME,
    EXPECTED_SOURCE_SHA256,
    apply_final_package_to_shadow,
    build_authorization_bound_payload,
    final_payload_semantic_body,
    freeze_source_package,
    materialize_source_to_shadow,
    preflight_final_payload,
    qualify_final_shadow,
    validate_final_payload,
    validate_human_review,
)
from pro_a.production_promotion import (
    PromotionError,
    canonical_sha256,
    copy_production_to_shadow,
    production_identity,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
STAGE3D2 = ROOT / "workspace" / "phase3d" / "STAGE3D2_QUALIFICATION_F6A9ECB_V2"
STAGE3D3A = ROOT / "workspace" / "phase3d" / "STAGE3D3A_AUTHORIZATION_PREP_637D772"
STAGE3D3B = ROOT / "workspace" / "phase3d" / "STAGE3D3B_HUMAN_REVIEW_637D772"
RECOVERY = ROOT / "workspace" / "phase3d" / "STAGE3D_SOURCE_RECOVERY_A2AC028"
PRODUCTION = STAGE3D2 / "production_shadow_restore.db"
SOURCE = RECOVERY / f"{EXPECTED_SOURCE_ID}.pdf"
INPUT_PATHS = {
    "qualification": STAGE3D2 / "phase3d_promotion_payload.json",
    "draft": STAGE3D3A / "node_operation_review.json",
    "human": STAGE3D3B / "node_operation_review_human.json",
    "recovery": RECOVERY / "source_recovery_receipt.json",
}
AVAILABLE = PRODUCTION.is_file() and SOURCE.is_file() and all(path.is_file() for path in INPUT_PATHS.values())
requires_stage3d3c = pytest.mark.skipif(not AVAILABLE, reason="Frozen local Stage 3D.3C inputs unavailable")


@pytest.fixture(scope="session")
def inputs() -> dict[str, dict]:
    if not AVAILABLE:
        pytest.skip("Frozen local Stage 3D.3C inputs unavailable")
    return {name: json.loads(path.read_text(encoding="utf-8")) for name, path in INPUT_PATHS.items()}


def build_payload(tmp_path: Path, inputs: dict[str, dict]) -> tuple[dict, Path, dict]:
    package = tmp_path / "source" / f"{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}"
    materialization = freeze_source_package(
        SOURCE,
        package,
        production_root=PRODUCTION.parent,
    )
    payload = build_authorization_bound_payload(
        qualification_payload=inputs["qualification"],
        draft_review=inputs["draft"],
        human_review=inputs["human"],
        human_review_file_sha256=sha256_file(INPUT_PATHS["human"]),
        source_materialization=materialization,
        production=production_identity(PRODUCTION),
        repository_commit="a2ac028ac90f4eea2b8d9c916d6538ac14fe7aea",
        source_recovery_receipt_sha256=sha256_file(INPUT_PATHS["recovery"]),
    )
    return payload, package, materialization


def rehash(payload: dict) -> dict:
    changed = copy.deepcopy(payload)
    digest = canonical_sha256(final_payload_semantic_body(changed))
    changed["payload_hash"] = digest
    changed["payload_id"] = f"PROMO_{digest[:16].upper()}"
    return changed


@requires_stage3d3c
def test_exact_source_freezes_deterministically_and_wrong_bytes_fail(tmp_path: Path):
    first = freeze_source_package(
        SOURCE,
        tmp_path / "one" / f"{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}",
        production_root=PRODUCTION.parent,
    )
    second = freeze_source_package(
        SOURCE,
        tmp_path / "two" / f"{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}",
        production_root=PRODUCTION.parent,
    )
    assert first["package"]["relative_path"] == second["package"]["relative_path"]
    assert first["package"]["sha256"] == second["package"]["sha256"] == EXPECTED_SOURCE_SHA256
    assert first["package"]["size"] == second["package"]["size"] == 3261556

    wrong = tmp_path / "wrong" / EXPECTED_SOURCE_NAME
    wrong.parent.mkdir()
    wrong.write_bytes(b"same filename, wrong bytes")
    with pytest.raises(PromotionError, match="SOURCE_SIZE_MISMATCH"):
        freeze_source_package(wrong, tmp_path / "bad-package.pdf", production_root=PRODUCTION.parent)


@requires_stage3d3c
def test_production_archive_collision_is_rejected(tmp_path: Path):
    production_root = tmp_path / "production"
    destination = production_root / Path(EXPECTED_ARCHIVE_PATH)
    destination.parent.mkdir(parents=True)
    shutil.copy2(SOURCE, destination)
    with pytest.raises(PromotionError, match="PRODUCTION_ARCHIVE_COLLISION"):
        freeze_source_package(
            SOURCE,
            tmp_path / "package" / f"{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}",
            production_root=production_root,
        )


@requires_stage3d3c
def test_exact_human_review_binding_and_tampering_fail(inputs: dict[str, dict]):
    review = inputs["human"]
    validate_human_review(review, file_sha256=EXPECTED_HUMAN_REVIEW_FILE_SHA256)
    with pytest.raises(PromotionError, match="HUMAN_REVIEW_FILE_SHA_MISMATCH"):
        validate_human_review(review, file_sha256="0" * 64)

    reuse = copy.deepcopy(review)
    reuse["records"][0]["target_node_id"] = "NODE_WRONG"
    with pytest.raises(PromotionError, match="HUMAN_REUSE_TARGET_MISMATCH"):
        validate_human_review(reuse, file_sha256=EXPECTED_HUMAN_REVIEW_FILE_SHA256)

    create = copy.deepcopy(review)
    record = next(item for item in create["records"] if item["human_decision"] == "CREATE")
    record["reviewed_identity_intent"]["aliases"] = ["CMM-D"]
    with pytest.raises(PromotionError, match="CREATE_ALIAS_INTENT_MISMATCH"):
        validate_human_review(create, file_sha256=EXPECTED_HUMAN_REVIEW_FILE_SHA256)


@requires_stage3d3c
def test_final_payload_is_deterministic_and_has_exact_inventory(tmp_path: Path, inputs: dict[str, dict]):
    first, _, _ = build_payload(tmp_path / "first", inputs)
    second, _, _ = build_payload(tmp_path / "second", inputs)
    assert first == second
    assert first["payload_hash"] == canonical_sha256(final_payload_semantic_body(first))
    assert first["human_authorization"]["decision_counts"] == EXPECTED_DECISION_COUNTS
    assert first["human_authorization"]["llm_authorization_used"] is False
    assert first["production_apply_authorized"] is False
    assert first["qualified_execution_target"] == "SHADOW_ONLY"
    assert Counter(item["table"] for item in first["intended_mutations"]) == Counter({
        "sources": 1,
        "claims": 104,
        "nodes": 8,
        "node_aliases": 8,
    })
    assert Counter(item["operation"] for item in first["node_operations"]) == Counter(EXPECTED_DECISION_COUNTS)
    assert len(first["relation_operations"]) == 10
    assert all(item["operation"] == "REJECT" and not item["executable"] for item in first["relation_operations"])
    assert first["audit"]["link_policy"]["decision"] == "NONE"
    assert first["audit"]["preserved_pre_review_node_reject_count"] == 32


@requires_stage3d3c
def test_final_payload_binds_source_human_and_production(tmp_path: Path, inputs: dict[str, dict]):
    payload, _, _ = build_payload(tmp_path, inputs)
    source = copy.deepcopy(payload)
    source["source_materialization"]["package_sha256"] = "0" * 64
    with pytest.raises(PromotionError, match="FINAL_SOURCE_PACKAGE_SHA_MISMATCH"):
        validate_final_payload(rehash(source))

    human = copy.deepcopy(payload)
    human["human_authorization"]["human_review_id"] = "HUMAN_WRONG"
    with pytest.raises(PromotionError, match="FINAL_HUMAN_REVIEW_ID_MISMATCH"):
        validate_final_payload(rehash(human))

    baseline = copy.deepcopy(payload)
    baseline["metadata"]["production_sha256"] = "0" * 64
    with pytest.raises(PromotionError, match="FINAL_PRODUCTION_SHA_BINDING_MISMATCH"):
        validate_final_payload(rehash(baseline))


@requires_stage3d3c
def test_defer_reject_relation_and_link_mutations_cannot_become_executable(tmp_path: Path, inputs: dict[str, dict]):
    payload, _, _ = build_payload(tmp_path, inputs)
    deferred = copy.deepcopy(payload)
    record = next(item for item in deferred["node_operations"] if item["operation"] == "DEFER")
    record["executable"] = True
    with pytest.raises(PromotionError, match="AUDIT_ONLY_OPERATION_MARKED_EXECUTABLE"):
        validate_final_payload(rehash(deferred))

    unexpected = copy.deepcopy(payload)
    unexpected["intended_mutations"].append({
        "mutation_id": "MUT_UNAUTHORIZED_LINK",
        "table": "source_node_links",
        "operation": "INSERT",
        "key": {"source_id": EXPECTED_SOURCE_ID, "node_id": "NODE_20260817_10A98F3C"},
        "row": {
            "source_id": EXPECTED_SOURCE_ID,
            "node_id": "NODE_20260817_10A98F3C",
            "role": "related",
            "confidence": None,
            "link_origin": "phase3d",
            "derived_from_node_id": "",
            "evidence_excerpt": "",
            "evidence_validation_json": "{}",
        },
        "authorized_by": "UNAUTHORIZED",
    })
    with pytest.raises(PromotionError, match="FINAL_MUTATION_INVENTORY_MISMATCH"):
        validate_final_payload(rehash(unexpected))


@requires_stage3d3c
def test_final_preflight_and_production_write_blocks(tmp_path: Path, inputs: dict[str, dict]):
    payload, package, _ = build_payload(tmp_path / "build", inputs)
    result = preflight_final_payload(
        payload,
        production_path=PRODUCTION,
        source_package_path=package,
        production_root=PRODUCTION.parent,
    )
    assert result["status"] == "PASS"
    assert result["claims"] == {"executable": 104, "table_ineligible_excluded": 3, "id_conflicts": 0}
    with pytest.raises(PromotionError, match="PRODUCTION_ARCHIVE_WRITE_BLOCKED"):
        materialize_source_to_shadow(
            payload,
            source_package_path=package,
            shadow_filesystem_root=PRODUCTION.parent,
            production_root=PRODUCTION.parent,
        )
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        apply_final_package_to_shadow(
            payload,
            shadow_path=PRODUCTION,
            configured_production_path=PRODUCTION,
            source_package_path=package,
            shadow_filesystem_root=tmp_path / "blocked-filesystem",
            production_root=PRODUCTION.parent,
        )


@requires_stage3d3c
def test_conflicting_replay_fails_closed(tmp_path: Path, inputs: dict[str, dict]):
    payload, package, _ = build_payload(tmp_path / "build", inputs)
    shadow = tmp_path / "shadow.db"
    filesystem = tmp_path / "filesystem"
    copy_production_to_shadow(PRODUCTION, shadow, payload["metadata"]["production_sha256"])
    apply_final_package_to_shadow(
        payload,
        shadow_path=shadow,
        configured_production_path=PRODUCTION,
        source_package_path=package,
        shadow_filesystem_root=filesystem,
        production_root=PRODUCTION.parent,
    )
    connection = sqlite3.connect(shadow)
    try:
        connection.execute("UPDATE nodes SET description='drift' WHERE node_id='NODE_CD91726FADECBD73'")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(PromotionError, match="PAYLOAD_REPLAY_CONFLICT"):
        apply_final_package_to_shadow(
            payload,
            shadow_path=shadow,
            configured_production_path=PRODUCTION,
            source_package_path=package,
            shadow_filesystem_root=filesystem,
            production_root=PRODUCTION.parent,
        )


@requires_stage3d3c
def test_full_final_shadow_rehearsal_replay_rollback_source_cleanup_and_restore(
    tmp_path: Path,
    inputs: dict[str, dict],
):
    payload, package, _ = build_payload(tmp_path / "build", inputs)
    production_before = production_identity(PRODUCTION)
    output = tmp_path / "qualification"
    output.mkdir()
    receipt = qualify_final_shadow(
        payload,
        production_path=PRODUCTION,
        production_root=PRODUCTION.parent,
        source_package_path=package,
        output_dir=output,
        receipt_path=output / "receipt.json",
    )
    assert receipt["status"] == "PASS"
    assert receipt["shadow"]["pre_sha256"] == production_before["sha256"]
    assert receipt["shadow"]["changed_tables"] == {
        "claims": {"added": 104, "removed": 0},
        "node_aliases": {"added": 8, "removed": 0},
        "nodes": {"added": 8, "removed": 0},
        "sources": {"added": 1, "removed": 0},
    }
    assert receipt["shadow"]["integrity"] == "ok"
    assert receipt["shadow"]["foreign_key_violations"] == []
    assert receipt["shadow"]["archive_inventory"] == [{
        "path": EXPECTED_ARCHIVE_PATH,
        "size": 3261556,
        "sha256": EXPECTED_SOURCE_SHA256,
    }]
    assert receipt["idempotency"]["database_status"] == "ALREADY_APPLIED"
    assert receipt["idempotency"]["source_status"] == "ALREADY_MATERIALIZED"
    assert receipt["rollback"]["status"] == "PASS"
    assert receipt["source_failure"]["status"] == "PASS"
    assert receipt["restore"]["status"] == "PASS"
    assert receipt["restore"]["restored_sha256"] == production_before["sha256"]
    production_after = production_identity(PRODUCTION)
    assert production_after["sha256"] == production_before["sha256"]
    assert production_after["sidecars"] == production_before["sidecars"]
