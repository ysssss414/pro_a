import re
import sqlite3
from pathlib import Path

import pytest

from pro_a.claim_attribution_semantics import (
    COMPANY_PRIMARY_CLAIM_IDS,
    MLCC_PRIMARY_CLAIM_IDS,
    AttributionActivationError,
    activate_database,
    file_sha256,
    insert_claim_node_link,
    post_attribution_summary,
    preflight,
    validate_claim_node_role,
)
from pro_a.claim_node_activation import (
    EXPECTED_SOURCE_ID,
    LINK_CLAIM_IDS,
    NO_LINK_CLAIM_ID,
    TARGET_NODE_ID,
)
from pro_a.db import Database
from pro_a.entity_granularity import COMPANY_NAME
from pro_a.query import ReadOnlyQuery


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    db_path = tmp_path / "claim_attribution.db"
    backup_dir = tmp_path / "backups"
    Database(db_path).init_schema()
    timestamp = "2026-08-26T00:00:00+08:00"
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executemany(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                (TARGET_NODE_ID, "MLCC", "Product", "", "active", timestamp, timestamp),
                ("NODE_OTHER", "Electronics", "Industry", "", "active", timestamp, timestamp),
            ],
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
                "f" * 64,
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
                   claim_id,statement,nature,ingestion_time,source_id,evidence_pointer,
                   evidence_excerpt,status,confidence,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    claim_id,
                    f"statement {claim_id}",
                    "fact",
                    timestamp,
                    EXPECTED_SOURCE_ID,
                    "p.1",
                    f"evidence {claim_id}",
                    "needs_review" if claim_id.endswith("E53B8E9C") else "current",
                    0.0 if claim_id.endswith("E53B8E9C") else 0.8,
                    timestamp,
                )
                for claim_id in (*LINK_CLAIM_IDS, NO_LINK_CLAIM_ID)
            ],
        )
        conn.executemany(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            [(claim_id, TARGET_NODE_ID, "related") for claim_id in LINK_CLAIM_IDS],
        )
        conn.execute(
            """INSERT INTO source_node_links(
                   source_id,node_id,role,confidence,link_origin,evidence_excerpt
               ) VALUES(?,?,?,?,?,?)""",
            (EXPECTED_SOURCE_ID, "NODE_OTHER", "related", 0.8, "fixture", "Electronics"),
        )
        conn.execute(
            """INSERT INTO node_relations(
                   relation_id,from_node_id,relation_type,to_node_id,scope,status,created_at
               ) VALUES(?,?,?,?,?,?,?)""",
            ("REL_1", TARGET_NODE_ID, "part_of", "NODE_OTHER", "", "current", timestamp),
        )
        conn.execute(
            """INSERT INTO relation_evidence_links(
                   relation_id,claim_id,evidence_role,status,created_at
               ) VALUES(?,?,?,?,?)""",
            ("REL_1", MLCC_PRIMARY_CLAIM_IDS[0], "supports", "active", timestamp),
        )
        conn.execute(
            """INSERT INTO current_views(
                   view_id,node_id,version,status,change_level,content_md,created_at
               ) VALUES(?,?,?,?,?,?,?)""",
            ("VIEW_1", "NODE_OTHER", "v_20260826", "official", "minor", "View", timestamp),
        )
        conn.execute(
            """INSERT INTO research_questions(
                   rq_id,node_id,question,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?)""",
            ("RQ_1", "NODE_OTHER", "Question?", "open", timestamp, timestamp),
        )
        conn.execute(
            """INSERT INTO knowledge_gaps(
                   gap_id,node_id,title,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?)""",
            ("GAP_1", "NODE_OTHER", "Gap", "open", timestamp, timestamp),
        )
    return db_path, backup_dir


def _company_node(db_path: Path) -> sqlite3.Row | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE canonical_name=?",
            (COMPANY_NAME,),
        ).fetchone()


def _target_links(db_path: Path) -> list[tuple[str, str, str]]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            """SELECT claim_id,node_id,role FROM claim_node_links
               WHERE claim_id IN ({}) ORDER BY claim_id,node_id""".format(
                ",".join("?" for _ in LINK_CLAIM_IDS)
            ),
            LINK_CLAIM_IDS,
        ).fetchall()


@pytest.mark.parametrize("role", ["subject", "context", "related"])
def test_canonical_claim_node_roles_are_allowed(role: str):
    assert validate_claim_node_role(role) == role


def test_unknown_role_is_rejected_by_write_helper(tmp_path: Path):
    db_path, _ = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        with pytest.raises(AttributionActivationError, match="invalid Claim-Node role"):
            insert_claim_node_link(conn, NO_LINK_CLAIM_ID, TARGET_NODE_ID, "mentions")
    assert len(_target_links(db_path)) == 11


def test_clean_apply_creates_company_and_exact_role_matrix(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    result = activate_database(db_path, backup_dir)
    company = _company_node(db_path)

    assert result["write_needed"] is True
    assert result["company_links_inserted"] == 8
    assert result["mlcc_role_updates"] == 11
    assert company is not None
    assert dict(company) == {
        "node_id": result["company_node_id"],
        "canonical_name": COMPANY_NAME,
        "primary_type": "Company",
        "status": "active",
    }
    assert re.fullmatch(r"NODE_\d{8}_[A-F0-9]{8}", result["company_node_id"])
    assert result["backup_sha"] == result["pre_sha"]
    assert result["post_sha"] != result["pre_sha"]
    assert not any(result["preserved_table_changes"].values())
    assert result["pre"]["node_aliases"] == result["post"]["node_aliases"]
    assert result["post"]["counts"]["nodes"] == result["pre"]["counts"]["nodes"] + 1
    assert (
        result["post"]["counts"]["claim_node_links"]
        == result["pre"]["counts"]["claim_node_links"] + 8
    )

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM node_aliases WHERE node_id=?", (result["company_node_id"],)
        ).fetchone()[0] == 0
        mlcc_roles = dict(
            conn.execute(
                "SELECT claim_id,role FROM claim_node_links WHERE node_id=?",
                (TARGET_NODE_ID,),
            ).fetchall()
        )
        company_roles = dict(
            conn.execute(
                "SELECT claim_id,role FROM claim_node_links WHERE node_id=?",
                (result["company_node_id"],),
            ).fetchall()
        )
        assert {mlcc_roles[claim_id] for claim_id in MLCC_PRIMARY_CLAIM_IDS} == {"subject"}
        assert {mlcc_roles[claim_id] for claim_id in COMPANY_PRIMARY_CLAIM_IDS} == {"context"}
        assert company_roles == {claim_id: "subject" for claim_id in COMPANY_PRIMARY_CLAIM_IDS}
        assert conn.execute(
            "SELECT COUNT(*) FROM claim_node_links WHERE claim_id=?", (NO_LINK_CLAIM_ID,)
        ).fetchone()[0] == 0


def test_atomic_failure_rolls_back_node_links_and_roles(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    blocked_claim = COMPANY_PRIMARY_CLAIM_IDS[4]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""CREATE TRIGGER block_company_link
                BEFORE INSERT ON claim_node_links
                WHEN NEW.claim_id='{blocked_claim}' AND NEW.node_id<>'{TARGET_NODE_ID}'
                BEGIN SELECT RAISE(ABORT, 'blocked Phase 2.3F test insert'); END"""
        )

    with pytest.raises(sqlite3.IntegrityError, match="blocked Phase 2.3F test insert"):
        activate_database(db_path, backup_dir)
    assert _company_node(db_path) is None
    assert len(_target_links(db_path)) == 11
    assert {role for _, _, role in _target_links(db_path)} == {"related"}


def test_partial_company_link_is_rejected(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            ("NODE_COMPANY", COMPANY_NAME, "Company", "", "active", "2026-08-26", "2026-08-26"),
        )
        conn.execute(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            (COMPANY_PRIMARY_CLAIM_IDS[0], "NODE_COMPANY", "subject"),
        )
    with pytest.raises(AttributionActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        activate_database(db_path, backup_dir)


def test_partial_role_migration_is_rejected(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE claim_node_links SET role='subject' WHERE claim_id=? AND node_id=?",
            (MLCC_PRIMARY_CLAIM_IDS[0], TARGET_NODE_ID),
        )
    with pytest.raises(AttributionActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        activate_database(db_path, backup_dir)


def test_wrong_existing_role_is_rejected(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE claim_node_links SET role='mentions' WHERE claim_id=? AND node_id=?",
            (MLCC_PRIMARY_CLAIM_IDS[0], TARGET_NODE_ID),
        )
    with pytest.raises(AttributionActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        activate_database(db_path, backup_dir)


def test_duplicate_company_canonical_nodes_are_rejected(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                ("NODE_COMPANY_1", COMPANY_NAME, "Entity", "", "active", "2026-08-26", "2026-08-26"),
                ("NODE_COMPANY_2", COMPANY_NAME, "Company", "", "active", "2026-08-26", "2026-08-26"),
            ],
        )
    with pytest.raises(AttributionActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        activate_database(db_path, backup_dir)


def test_full_state_rerun_is_idempotent(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    first = activate_database(db_path, backup_dir)
    pre_rerun_sha = file_sha256(db_path)
    second = activate_database(db_path, backup_dir)

    assert second["write_needed"] is False
    assert second["idempotent_already_applied"] is True
    assert second["company_node_created"] is False
    assert second["company_links_inserted"] == 0
    assert second["mlcc_role_updates"] == 0
    assert second["company_node_id"] == first["company_node_id"]
    assert second["post_sha"] == pre_rerun_sha == file_sha256(db_path)
    assert second["backup_path"] == ""


def test_preserved_objects_no_link_and_read_surface_are_safe(tmp_path: Path):
    db_path, backup_dir = _fixture(tmp_path)
    pre = preflight(db_path)
    result = activate_database(db_path, backup_dir)
    post = preflight(db_path)
    summary = post_attribution_summary(db_path)

    assert pre["preserved_state"] == post["preserved_state"]
    assert post["no_link_claim_link_count"] == 0
    assert summary["nodes_with_subject_claims"] == 2
    assert summary["nodes_with_context_claims"] == 1
    assert summary["unlinked_claims"] == 1
    query = ReadOnlyQuery(db_path)
    mlcc_claims = query.node_claims(TARGET_NODE_ID)
    company_claims = query.node_claims(result["company_node_id"])
    assert mlcc_claims is not None and company_claims is not None
    assert sum(claim["link_role"] == "subject" for claim in mlcc_claims) == 3
    assert sum(claim["link_role"] == "context" for claim in mlcc_claims) == 8
    assert {claim["link_role"] for claim in company_claims} == {"subject"}
    assert NO_LINK_CLAIM_ID not in {claim["claim_id"] for claim in [*mlcc_claims, *company_claims]}
