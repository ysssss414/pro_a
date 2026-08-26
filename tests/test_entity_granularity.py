import json
import sqlite3
from pathlib import Path

from pro_a.claim_node_activation import (
    EXPECTED_SOURCE_ID,
    LINK_CLAIM_IDS,
    TARGET_NODE_ID,
)
from pro_a.db import Database
from pro_a.entity_granularity import (
    COMPANY_NAME,
    build_claim_attribution_proposals,
    build_company_node_proposal,
    file_sha256,
    generate_review_package,
    lookup_company_node,
    review_claims,
)


def _fixture(tmp_path: Path) -> Path:
    db_path = tmp_path / "entity_granularity.db"
    Database(db_path).init_schema()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                TARGET_NODE_ID,
                "MLCC",
                "Product",
                "",
                "active",
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.execute(
            """INSERT INTO sources(
                   source_id,title,original_name,archived_path,sha256,ingestion_mode,
                   analysis_mode,source_type,publication_time,ingested_at,status
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                EXPECTED_SOURCE_ID,
                "昀冢科技业绩说明会更新：MLCC",
                "source.md",
                "archive/source.md",
                "a" * 64,
                "standard",
                "standard",
                "md",
                "2026-08-13",
                "2026-08-14",
                "analyzed",
            ),
        )
        conn.executemany(
            """INSERT INTO claims(
                   claim_id,statement,nature,ingestion_time,source_id,evidence_excerpt,
                   scope,status,confidence,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    claim_id,
                    f"fixture statement {claim_id}",
                    "fact",
                    "2026-08-14",
                    EXPECTED_SOURCE_ID,
                    f"fixture evidence {claim_id}",
                    "",
                    "current",
                    0.8,
                    "2026-08-14",
                )
                for claim_id in LINK_CLAIM_IDS
            ],
        )
        conn.executemany(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            [(claim_id, TARGET_NODE_ID, "related") for claim_id in LINK_CLAIM_IDS],
        )
    return db_path


def _row_by_id(rows: list[dict[str, str]], claim_id: str) -> dict[str, str]:
    return next(row for row in rows if row["claim_id"] == claim_id)


def test_company_node_lookup_is_exact_and_deterministic(tmp_path: Path):
    db_path = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                "NODE_COMPANY_NEAR",
                "昀冢科技控股",
                "Entity",
                "",
                "active",
                "2026-01-01",
                "2026-01-01",
            ),
        )

    no_exact = lookup_company_node(db_path)
    assert no_exact["exists"] is False
    assert no_exact["canonical_exact_matches"] == []
    assert len(no_exact["deterministic_substring_diagnostics"]["canonical_name"]) == 1

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO node_aliases(alias,node_id) VALUES(?,?)",
            (COMPANY_NAME, "NODE_COMPANY_NEAR"),
        )
    exact_alias = lookup_company_node(db_path)
    assert exact_alias["exists"] is True
    assert exact_alias["canonical_exact_matches"] == []
    assert exact_alias["matched_nodes"] == [
        {
            "node_id": "NODE_COMPANY_NEAR",
            "canonical_name": "昀冢科技控股",
            "primary_type": "Entity",
            "status": "active",
            "aliases": [COMPANY_NAME],
        }
    ]


def test_frozen_attribution_classification_fixture(tmp_path: Path):
    review = review_claims(_fixture(tmp_path))
    assert review["counts"] == {
        "AMBIGUOUS": 0,
        "COMPANY_PRIMARY": 0,
        "COMPANY_PRIMARY_MLCC_CONTEXT": 8,
        "MLCC_PRIMARY": 3,
    }
    revenue = _row_by_id(review["rows"], "CLM_20260814_E1A48290")
    price = _row_by_id(review["rows"], "CLM_20260814_980FA010")
    assert revenue["primary_subject_candidate"] == COMPANY_NAME
    assert revenue["mlcc_semantic_role"] == "CONTEXT"
    assert price["primary_subject_candidate"] == "MLCC"
    assert price["mlcc_semantic_role"] == "PRIMARY_SUBJECT"


def test_mlcc_current_view_eligibility_is_explicit(tmp_path: Path):
    rows = review_claims(_fixture(tmp_path))["rows"]
    eligible = {
        row["claim_id"]
        for row in rows
        if row["current_view_eligible"] == "true"
    }
    assert eligible == {
        "CLM_20260814_980FA010",
        "CLM_20260814_BAED6789",
        "CLM_20260814_D2C7FCD1",
    }
    assert all(
        row["current_view_eligible"] == "false"
        for row in rows
        if row["primary_subject_candidate"] == COMPANY_NAME
    )


def test_company_and_claim_proposals_are_review_only(tmp_path: Path):
    db_path = _fixture(tmp_path)
    review = review_claims(db_path)
    company = build_company_node_proposal(
        review["rows"], lookup_company_node(db_path)
    )
    assert company is not None
    assert company["canonical_name"] == COMPANY_NAME
    assert company["proposed_type"] == "Company"
    assert company["primary_type"] == "Company"
    assert company["explicit_aliases"] == []
    assert len(company["supporting_claim_ids"]) == 8
    assert company["production_write_authorized"] is False

    proposals = build_claim_attribution_proposals(review["rows"])
    assert len(proposals) == 11
    assert {
        row["recommended_action"] for row in proposals
    } == {"KEEP_MLCC_ONLY", "ADD_COMPANY_REVIEW_MLCC_ROLE"}


def test_package_generation_does_not_write_database(tmp_path: Path):
    db_path = _fixture(tmp_path)
    artifact_dir = tmp_path / "artifacts"
    report_path = tmp_path / "report.md"
    pre_sha = file_sha256(db_path)
    result = generate_review_package(db_path, artifact_dir, report_path)
    post_sha = file_sha256(db_path)

    assert result["production_db_changed"] is False
    assert result["pre_sha"] == result["post_sha"] == pre_sha == post_sha
    assert report_path.exists()
    assert (artifact_dir / "claim_attribution_review.csv").exists()
    assert (artifact_dir / "claim_attribution_proposal.csv").exists()
    proposal = json.loads(
        (artifact_dir / "company_node_proposal.json").read_text(encoding="utf-8")
    )
    assert proposal["production_write_authorized"] is False
