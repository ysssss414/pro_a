from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.operational_ingestion import (
    PROMOTION_PREVIEW_DOCUMENT_TYPE,
    RunPaths,
    _render_node_review,
    _run_promotion_preview,
    _semantic_admission_artifact,
    run_operational_ingestion,
)
from pro_a.production_authorization import build_operational_node_operation_review
from pro_a.production_promotion import PromotionError, production_identity, validate_payload


ROOT = Path(__file__).resolve().parents[1]
KNOWN_BUNDLE = ROOT / "workspace" / "phase3c" / "PILOT_20260902_572A6DF2" / "extraction_bundle.json"
KNOWN_SOURCE_DIR = ROOT / "workspace" / "phase3d" / "STAGE3D3C_FINAL_QUALIFICATION_A2AC028" / "source"
KNOWN_SIGNOFF = (
    ROOT
    / "workspace"
    / "phase3d"
    / "RELEASE_MAIN_22C36BE"
    / "artifacts"
    / "phase3c"
    / "pilot6_delegated_reviewer_signoff.json"
)
KNOWN_SOURCE = next(KNOWN_SOURCE_DIR.glob("*.pdf"), None) if KNOWN_SOURCE_DIR.is_dir() else None
KNOWN_REPLAY_AVAILABLE = bool(
    KNOWN_BUNDLE.is_file()
    and KNOWN_SOURCE is not None
    and KNOWN_SIGNOFF.is_file()
    and (ROOT / "workspace" / "pro_a.db").is_file()
)


def _write_minimal_production(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO meta VALUES('schema_version', '0.2.1');
            CREATE TABLE sources(source_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL);
            CREATE TABLE claims(claim_id TEXT PRIMARY KEY);
            CREATE TABLE nodes(
                node_id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                primary_type TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE node_aliases(
                alias TEXT NOT NULL,
                node_id TEXT NOT NULL REFERENCES nodes(node_id)
            );
            """
        )


def _write_config(path: Path, workspace: Path) -> Path:
    path.write_text(
        "\n".join(
            (
                "[workspace]",
                f'root = "{workspace.as_posix()}"',
                "",
                "[llm]",
                "enabled = false",
                'model = "fixture-model"',
                "",
                "[ima]",
                "enabled = false",
                "",
                "[pipeline]",
            )
        ),
        encoding="utf-8",
    )
    return path


def _fixture_bundle(source: Path, source_sha: str) -> dict:
    return {
        "document_type": "phase3c_extraction_bundle",
        "schema_version": "1",
        "status": "EXTRACTED_REVIEW_REQUIRED",
        "pilot_run_id": "FIXTURE",
        "source": {
            "proposed_source_id": "SRC_FIXTURE",
            "original_name": source.name,
            "sha256": source_sha,
            "source_type": "pdf",
        },
        "model": {"configured_model": "fixture-model"},
        "proposed_source_metadata": {},
        "source_references": [],
        "claims": [],
        "observations": {},
        "human_review_flags": [],
    }


def test_source_and_extraction_fixture_are_frozen_and_manifested(tmp_path: Path):
    workspace = tmp_path / "workspace"
    _write_minimal_production(workspace / "pro_a.db")
    config = _write_config(tmp_path / "config.toml", workspace)
    source = tmp_path / "clean.pdf"
    source.write_bytes(b"%PDF-1.4\nexact fixture bytes")
    import hashlib

    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    fixture = tmp_path / "extraction.json"
    fixture.write_text(json.dumps(_fixture_bundle(source, source_sha)), encoding="utf-8")
    run_dir = workspace / "ingestion" / "run"

    result = run_operational_ingestion(
        source,
        config_path=config,
        run_dir=run_dir,
        frozen_extraction_path=fixture,
        stop_after="source",
    )
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert result["run_status"] == "SOURCE_FROZEN"
    assert manifest["run_id"] == f"INGEST_{source_sha[:16].upper()}"
    assert (run_dir / "source" / source.name).read_bytes() == source.read_bytes()
    assert (run_dir / "extraction" / "frozen_extraction_input.json").read_bytes() == fixture.read_bytes()
    assert manifest["source"]["source_id"] == "SRC_FIXTURE"
    assert manifest["production_safety"]["production_write_path_enabled"] is False
    assert manifest["model"]["frozen_extraction_input_sha256"]


def test_resume_uses_frozen_source_and_detects_artifact_tampering(tmp_path: Path):
    workspace = tmp_path / "workspace"
    _write_minimal_production(workspace / "pro_a.db")
    config = _write_config(tmp_path / "config.toml", workspace)
    source = tmp_path / "clean.pdf"
    source.write_bytes(b"%PDF-1.4\nresume fixture")
    run_dir = workspace / "ingestion" / "run"
    run_operational_ingestion(source, config_path=config, run_dir=run_dir, stop_after="source")
    source.unlink()

    resumed = run_operational_ingestion(
        config_path=config, run_dir=run_dir, resume=True, stop_after="source"
    )
    assert resumed["run_status"] == "SOURCE_FROZEN"

    frozen = next((run_dir / "source").iterdir())
    frozen.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="RESUME_ARTIFACT_INVENTORY_OR_HASH_MISMATCH"):
        run_operational_ingestion(
            config_path=config, run_dir=run_dir, resume=True, stop_after="source"
        )


def test_semantic_surface_preserves_table_eligible_review_universe():
    claims = [
        {"claim_id": "CLM_KEEP", "statement": "Revenue was 42.", "attributed_to": ""},
        {"claim_id": "CLM_TABLE", "statement": "Revenue was 43.", "attributed_to": ""},
    ]
    evidence_claims = [
        {"claim_id": claim["claim_id"], "bounded_context_candidates": [], "evidence_spans": []}
        for claim in claims
    ]
    gate_claims = [
        {
            "claim_id": claim["claim_id"],
            "fidelity_status": "EXACT_SOURCE_MATCH",
            "resolved_locator": {"authoritative": True, "locator": "PAGE:1"},
            "evidence_contract": {"canonical_ready_evidence": claim["statement"]},
        }
        for claim in claims
    ]
    table_decisions = [
        {
            "claim_id": "CLM_KEEP",
            "review_eligible": True,
            "eligibility_decision": "TABLE_CLAIM_ELIGIBLE_FAIL_OPEN",
            "decision_reason": "KEEP_FAIL_OPEN",
        },
        {
            "claim_id": "CLM_TABLE",
            "review_eligible": False,
            "eligibility_decision": "TABLE_DERIVED_CLAIM_INELIGIBLE",
            "decision_reason": "TABLE_DERIVED_CLAIM_INELIGIBLE",
        },
    ]
    result = _semantic_admission_artifact(
        manifest={"run_id": "INGEST_TEST", "source": {"sha256": "a" * 64}},
        bundle={"claims": claims},
        evidence_draft={"claims": evidence_claims},
        gate={"claims": gate_claims},
        table_boundary={"decisions": table_decisions},
    )

    assert result["counts"]["raw_claims"] == 2
    assert result["counts"]["review_admitted"] == 1
    assert result["decisions"][0]["review_admitted"] is True
    assert result["decisions"][1]["review_admitted"] is False
    assert result["decisions"][1]["recommended_decision"] == "DROP"


def test_operational_node_review_reuses_exact_phase3d_resolution_logic(tmp_path: Path):
    production = tmp_path / "production.db"
    _write_minimal_production(production)
    with sqlite3.connect(production) as connection:
        connection.execute(
            "INSERT INTO nodes VALUES(?,?,?,?)",
            ("NODE_EXISTING", "Existing Product", "Product", "active"),
        )
        connection.execute(
            "INSERT INTO node_aliases VALUES(?,?)", ("EP", "NODE_EXISTING")
        )
    claims = [{
        "claim_id": "CLM_1",
        "evidence_id": "EVD_1",
        "immutable_projection": {
            "statement": "Existing Product demand increased.",
            "evidence_excerpt": "Existing Product demand increased.",
            "evidence_pointer": "[[PAGE:1]]",
            "related_node_ids": ["NODE_EXISTING"],
        },
    }]
    operations = [{
        "operation_id": "OP_1",
        "candidate_id": "CAND_1",
        "candidate_kind": "existing_node_match",
        "operation": "DEFER",
        "executable": False,
        "candidate": {
            "node_id": "NODE_EXISTING",
            "evidence_excerpt": "Existing Product demand increased.",
            "validation": {},
        },
        "claim_refs": ["CLM_1"],
        "reason": "NO_EXPLICIT_NODE_REUSE_REVIEW",
    }]

    before = production_identity(production)
    review = build_operational_node_operation_review(
        run_id="INGEST_TEST",
        source_sha256="a" * 64,
        claim_review_sha256="b" * 64,
        claims=claims,
        node_operations=operations,
        relation_operations=[],
        production_path=production,
        table_ineligible_claims=0,
    )
    after = production_identity(production)

    assert review["records"][0]["suggested_operation"] == "REUSE"
    assert review["records"][0]["exact_production_resolution"]["exact_target_node_ids"] == [
        "NODE_EXISTING"
    ]
    assert review["records"][0]["review_decision"] == "PENDING"
    assert before == after


def test_operational_node_review_labels_parent_placement_as_separate_governance(
    tmp_path: Path,
):
    production = tmp_path / "production.db"
    _write_minimal_production(production)
    with sqlite3.connect(production) as connection:
        connection.execute(
            "INSERT INTO nodes VALUES(?,?,?,?)",
            ("NODE_PARENT", "Parent Segment", "Segment", "active"),
        )
    claims = [{
        "claim_id": "CLM_CHILD",
        "evidence_id": "EVD_CHILD",
        "immutable_projection": {
            "statement": "New Product demand increased.",
            "evidence_excerpt": "New Product demand increased.",
            "evidence_pointer": "[[PAGE:1]]",
            "related_node_ids": [],
        },
    }]
    operations = [{
        "operation_id": "OP_CHILD",
        "candidate_id": "CAND_CHILD",
        "candidate_kind": "node_candidate",
        "operation": "DEFER",
        "executable": False,
        "candidate": {
            "canonical_name": "New Product",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": ["NODE_PARENT"],
            "quality_eligible": True,
            "quality_validation": {"eligible": True, "errors": []},
            "candidate_kind": "normal",
            "evidence_excerpt": "New Product demand increased.",
        },
        "claim_refs": ["CLM_CHILD"],
        "reason": "NO_EXPLICIT_NODE_CREATE_OR_REUSE_REVIEW",
    }]

    review = build_operational_node_operation_review(
        run_id="INGEST_PARENT_REVIEW",
        source_sha256="a" * 64,
        claim_review_sha256="b" * 64,
        claims=claims,
        node_operations=operations,
        relation_operations=[],
        production_path=production,
        table_ineligible_claims=0,
    )
    placement = review["records"][0]["parent_placement_suggestion"]
    markdown = _render_node_review(review)

    assert placement == {
        "suggested_parent_node_ids": ["NODE_PARENT"],
        "advisory_only": True,
        "separate_human_review_required": True,
        "authorized_by_node_create": False,
        "review_decision": "PENDING",
    }
    assert "PARENT PLACEMENT SUGGESTION" in markdown
    assert "SEPARATE HUMAN REVIEW REQUIRED" in markdown
    assert "NOT AUTHORIZED BY NODE CREATE" in markdown


def test_promotion_preview_is_non_executable_and_executor_incompatible(tmp_path: Path):
    production = tmp_path / "production.db"
    _write_minimal_production(production)
    run_dir = tmp_path / "run"
    (run_dir / "review").mkdir(parents=True)
    manifest = {
        "run_id": "INGEST_TEST",
        "source": {"source_id": "SRC_TEST", "sha256": "a" * 64},
        "production_baseline": {
            key: production_identity(production)[key]
            for key in (
                "sha256",
                "schema_version",
                "schema_sha256",
                "counts",
                "sidecars",
                "integrity",
                "foreign_key_violations",
            )
        },
    }
    (run_dir / "review" / "claim_review.json").write_text(
        json.dumps({
            "claims": [{"claim_id": "CLM_NEW", "review_admitted": True}],
        }),
        encoding="utf-8",
    )
    (run_dir / "review" / "node_operation_review.json").write_text(
        json.dumps({
            "suggestion_counts": {"REUSE": 0, "CREATE": 1, "DEFER": 0, "REJECT": 0},
            "records": [{
                "operation_candidate_id": "CAND_PARENT",
                "suggested_operation": "CREATE",
                "suggestion_reason": "PENDING_NODE_IDENTITY_REVIEW",
                "prospective_node_id": "NODE_PROSPECTIVE",
                "parent_placement_suggestion": {
                    "suggested_parent_node_ids": ["NODE_PARENT"],
                },
            }],
            "audit_operations": {"relations": []},
        }),
        encoding="utf-8",
    )
    before = production_identity(production)
    outputs = _run_promotion_preview(RunPaths(run_dir), manifest, production)
    preview = json.loads(outputs[0].read_text(encoding="utf-8"))
    after = production_identity(production)

    assert preview["document_type"] == PROMOTION_PREVIEW_DOCUMENT_TYPE
    assert preview["authorization"]["executable"] is False
    assert preview["authorization"]["production_apply_authorized"] is False
    assert "intended_mutations" not in preview
    assert preview["summary"]["node_create_suggestions"] == 1
    assert preview["summary"]["parent_placement_suggestions"] == 1
    assert preview["parent_placement_suggestions"][0] == {
        "suggestion_id": preview["parent_placement_suggestions"][0]["suggestion_id"],
        "candidate_id": "CAND_PARENT",
        "prospective_child_node_id": "NODE_PROSPECTIVE",
        "parent_node_id": "NODE_PARENT",
        "suggestion_type": "PARENT_PLACEMENT_SUGGESTION",
        "governance_status": "SEPARATE_HUMAN_REVIEW_REQUIRED",
        "authorized_by_node_create": False,
        "human_decision": "PENDING",
        "executable": False,
    }
    assert preview["relations"]["observations"] == []
    with pytest.raises(PromotionError, match="PAYLOAD_DOCUMENT_TYPE_INVALID"):
        validate_payload(preview)
    assert before == after


@pytest.mark.skipif(not KNOWN_REPLAY_AVAILABLE, reason="Frozen Phase 3C/3D replay artifacts unavailable")
def test_known_fixture_end_to_end_semantic_equivalence(tmp_path: Path):
    production = ROOT / "workspace" / "pro_a.db"
    before = production_identity(production)
    result = run_operational_ingestion(
        KNOWN_SOURCE,
        config_path=ROOT / "config.toml",
        run_dir=tmp_path / "known-replay",
        frozen_extraction_path=KNOWN_BUNDLE,
    )
    run_dir = Path(result["run_dir"])
    claims = json.loads((run_dir / "review" / "claim_review.json").read_text(encoding="utf-8"))
    nodes = json.loads((run_dir / "review" / "node_operation_review.json").read_text(encoding="utf-8"))
    preview = json.loads((run_dir / "promotion" / "promotion_preview.json").read_text(encoding="utf-8"))
    signoff = json.loads(KNOWN_SIGNOFF.read_text(encoding="utf-8"))
    admitted_ids = [item["claim_id"] for item in claims["claims"] if item["review_admitted"]]

    assert result["run_status"] == "HUMAN_REVIEW_REQUIRED"
    assert claims["metrics"]["raw_claims"] == 107
    assert claims["metrics"]["table_ineligible"] == 3
    assert claims["metrics"]["review_admitted"] == 104
    assert admitted_ids == [item["claim_id"] for item in signoff["claims"]]
    assert nodes["review_universe"]["observed"] == 26
    assert nodes["review_universe"]["admitted_claims"] == 104
    assert nodes["relation_audit"]["observed"] == 10
    assert nodes["authorization"]["all_review_decisions_pending"] is True
    assert preview["authorization"]["executable"] is False
    assert preview["authorization"]["production_apply_authorized"] is False
    assert production_identity(production) == before
