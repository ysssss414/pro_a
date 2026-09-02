from __future__ import annotations

import json
from pathlib import Path

import pytest

from pro_a.production_authorization import (
    build_node_operation_review,
    prepare_source_materialization,
)
from pro_a.production_promotion import (
    PromotionError,
    apply_payload_to_shadow,
    canonical_sha256,
    production_identity,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
STAGE3D2 = ROOT / "workspace" / "phase3d" / "STAGE3D2_QUALIFICATION_F6A9ECB_V2"
PAYLOAD_PATH = STAGE3D2 / "phase3d_promotion_payload.json"
PRODUCTION = STAGE3D2 / "production_shadow_restore.db"
AVAILABLE = PAYLOAD_PATH.is_file() and PRODUCTION.is_file()
requires_stage3d2 = pytest.mark.skipif(not AVAILABLE, reason="Frozen local Stage 3D.2 artifacts unavailable")


@pytest.fixture(scope="session")
def payload() -> dict:
    if not AVAILABLE:
        pytest.skip("Frozen local Stage 3D.2 artifacts unavailable")
    return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def review(payload: dict) -> dict:
    return build_node_operation_review(payload, PRODUCTION)


@requires_stage3d2
def test_exact_26_node_review_universe_excludes_rejects_and_relations(payload: dict, review: dict):
    deferred = {item["candidate_id"] for item in payload["node_operations"] if item["operation"] == "DEFER"}
    rejected = {item["candidate_id"] for item in payload["node_operations"] if item["operation"] == "REJECT"}
    reviewed = {item["operation_candidate_id"] for item in review["records"]}
    assert len(deferred) == len(reviewed) == review["review_universe"]["observed"] == 26
    assert reviewed == deferred
    assert reviewed.isdisjoint(rejected)
    assert review["review_universe"]["rejected_nodes_excluded"] == 32
    assert review["review_universe"]["table_ineligible_claims_excluded"] == 3
    assert review["relation_audit"] == {
        "relation_reject_expected": 10,
        "relation_reject_observed": 10,
        "relation_review_reopened": False,
    }


@requires_stage3d2
def test_review_is_deterministic_pending_and_advisory(payload: dict, review: dict):
    second = build_node_operation_review(payload, PRODUCTION)
    assert review == second
    assert review["review_sha256"] == canonical_sha256({
        key: value for key, value in review.items() if key not in {"review_id", "review_sha256"}
    })
    assert review["review_status"] == "DRAFT"
    assert {record["review_decision"] for record in review["records"]} == {"PENDING"}
    assert all(record["advisory_only"] for record in review["records"])
    assert review["authorization"]["llm_authorization_used"] is False


@requires_stage3d2
def test_ambiguous_and_unsupported_candidates_remain_defer(review: dict):
    by_name = {record["proposed_name"]: record for record in review["records"]}
    assert by_name["VPD芯片"]["suggested_operation"] == "DEFER"
    assert by_name["SPD芯片"]["suggested_operation"] == "DEFER"
    assert by_name["NFC芯片"]["supporting_claim_ids"] == []
    assert by_name["NFC芯片"]["suggested_operation"] == "DEFER"


@requires_stage3d2
def test_exact_production_resolution_is_bound_and_deterministic(review: dict):
    enterprise = next(record for record in review["records"] if record["proposed_name"] == "Enterprise SSD")
    assert enterprise["suggested_operation"] == "REUSE"
    assert len(enterprise["exact_production_resolution"]["exact_target_node_ids"]) == 1
    assert enterprise["exact_production_resolution"]["candidate_targets"][0]["status"] == "active"


@requires_stage3d2
def test_source_wrong_bytes_same_name_fails_closed(payload: dict, tmp_path: Path):
    source = payload["sources"][0]["intended_row"]
    wrong = tmp_path / source["original_name"]
    wrong.write_bytes(b"not the source pdf")
    before = production_identity(PRODUCTION)
    artifact = prepare_source_materialization(
        payload,
        candidate_paths=[wrong],
        production_root=PRODUCTION.parent,
        staging_root=tmp_path / "staging",
    )
    after = production_identity(PRODUCTION)
    assert artifact["search"]["candidate_results"][0]["filename_match"] is True
    assert artifact["search"]["candidate_results"][0]["sha_match"] is False
    assert artifact["flags"]["source_file_found"] is False
    assert artifact["flags"]["source_archive_materialization_ready"] is False
    assert before["sha256"] == after["sha256"]


@requires_stage3d2
def test_staged_copy_preserves_exact_sha_and_real_archive_is_untouched(payload: dict, tmp_path: Path):
    changed = json.loads(json.dumps(payload))
    exact = tmp_path / "source.pdf"
    exact.write_bytes(b"exact source test bytes")
    digest = sha256_file(exact)
    row = changed["sources"][0]["intended_row"]
    metadata = json.loads(row["metadata_json"])
    metadata["parse_diagnostics"]["file_size"] = exact.stat().st_size
    row["original_name"] = exact.name
    row["sha256"] = digest
    row["archived_path"] = "archive/test/SRC_TEST__source.pdf"
    row["metadata_json"] = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    changed["sources"][0]["source_id"] = "SRC_TEST"
    changed["sources"][0]["source_sha256"] = digest
    changed["sources"][0]["archive_copy_intent"]["destination"] = row["archived_path"]
    changed["metadata"]["source_sha256"] = digest
    # Source preparation validates the payload, so bind the synthetic source contract.
    semantic = {key: value for key, value in changed.items() if key not in {"payload_id", "payload_hash"}}
    changed["payload_hash"] = canonical_sha256(semantic)
    changed["payload_id"] = f"PROMO_{changed['payload_hash'][:16].upper()}"

    production_root = tmp_path / "production-root"
    production_root.mkdir()
    artifact = prepare_source_materialization(
        changed,
        candidate_paths=[exact],
        production_root=production_root,
        staging_root=tmp_path / "staging",
    )
    staged = Path(artifact["materialization"]["staged_path"])
    assert artifact["flags"]["source_archive_materialization_ready"] is True
    assert sha256_file(staged) == sha256_file(exact) == digest
    assert not (production_root / row["archived_path"]).exists()
    assert artifact["real_archive"]["mutated"] is False


@requires_stage3d2
def test_stage3d2_configured_production_hard_block_remains(payload: dict):
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        apply_payload_to_shadow(payload, PRODUCTION, PRODUCTION)
