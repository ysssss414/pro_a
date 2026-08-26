import csv
import sqlite3
from pathlib import Path

import pytest

from pro_a.claim_node_activation import (
    EXPECTED_SOURCE_ID,
    LINK_CLAIM_IDS,
    NO_LINK_CLAIM_ID,
    TARGET_NODE_ID,
    ActivationError,
    activate_database,
    decisions,
    file_sha256,
    preflight,
)
from pro_a.db import Database


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    db_path = tmp_path / "activation.db"
    package_path = tmp_path / "adjudication.csv"
    backup_dir = tmp_path / "backups"
    Database(db_path).init_schema()
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            [
                (TARGET_NODE_ID, "MLCC", "Product", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_OTHER", "Semiconductor", "Industry", "", "active", "2026-01-01", "2026-01-01"),
            ],
        )
        conn.execute("INSERT INTO node_aliases(alias,node_id) VALUES(?,?)", ("MLCC", TARGET_NODE_ID))
        conn.execute(
            """INSERT INTO sources(
               source_id,title,original_name,archived_path,sha256,ingestion_mode,
               source_type,source_rank,metadata_json,ingested_at,status)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                EXPECTED_SOURCE_ID,
                "Company MLCC update",
                "mlcc.md",
                "archive/mlcc.md",
                "a" * 64,
                "standard",
                "md",
                "B",
                '{"summary":"MLCC update"}',
                "2026-01-01",
                "analyzed",
            ),
        )
        conn.execute(
            "INSERT INTO source_node_links(source_id,node_id,role) VALUES(?,?,?)",
            (EXPECTED_SOURCE_ID, "NODE_OTHER", "related"),
        )
        for claim_id in sorted((*LINK_CLAIM_IDS, NO_LINK_CLAIM_ID)):
            conn.execute(
                """INSERT INTO claims(
                   claim_id,statement,nature,ingestion_time,source_id,evidence_excerpt,
                   status,confidence,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    claim_id,
                    f"Statement for {claim_id}",
                    "fact",
                    "2026-01-01",
                    EXPECTED_SOURCE_ID,
                    f"Evidence for {claim_id}",
                    "current",
                    0.8,
                    "2026-01-01",
                ),
            )
    with package_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("claim_id", "source_id", "source_title", "statement"),
        )
        writer.writeheader()
        for claim_id in sorted((*LINK_CLAIM_IDS, NO_LINK_CLAIM_ID)):
            writer.writerow(
                {
                    "claim_id": claim_id,
                    "source_id": EXPECTED_SOURCE_ID,
                    "source_title": "Company MLCC update",
                    "statement": f"Statement for {claim_id}",
                }
            )
    return db_path, package_path, backup_dir


def _insert_link(db_path: Path, claim_id: str, node_id: str, role: str = "related") -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            (claim_id, node_id, role),
        )


def _link_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM claim_node_links").fetchone()[0]


def test_human_decision_allowlist_is_exact():
    rows = decisions()
    assert len([row for row in rows if row["decision"] == "LINK"]) == 11
    assert len([row for row in rows if row["decision"] == "NO_LINK"]) == 1
    assert all(
        row["selected_node_ids"] == [TARGET_NODE_ID]
        for row in rows
        if row["decision"] == "LINK"
    )
    assert next(row for row in rows if row["decision"] == "NO_LINK")["selected_node_ids"] == []


def test_unknown_claim_and_wrong_target_node_abort(tmp_path: Path):
    db_path, package_path, _ = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM claims WHERE claim_id=?", (LINK_CLAIM_IDS[0],))
    with pytest.raises(ActivationError, match="reviewed Claim missing"):
        preflight(db_path, package_path)

    db_path, package_path, _ = _fixture(tmp_path / "wrong_target")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE nodes SET canonical_name='Not MLCC' WHERE node_id=?",
            (TARGET_NODE_ID,),
        )
    with pytest.raises(ActivationError, match="target Node identity/status mismatch"):
        preflight(db_path, package_path)


def test_conflicting_and_no_link_existing_links_abort(tmp_path: Path):
    db_path, package_path, _ = _fixture(tmp_path)
    _insert_link(db_path, LINK_CLAIM_IDS[0], "NODE_OTHER")
    with pytest.raises(ActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        preflight(db_path, package_path)

    db_path, package_path, _ = _fixture(tmp_path / "no_link")
    _insert_link(db_path, NO_LINK_CLAIM_ID, TARGET_NODE_ID)
    with pytest.raises(ActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        preflight(db_path, package_path)


def test_source_mlcc_signal_missing_aborts(tmp_path: Path):
    db_path, package_path, _ = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE sources SET title='Company update',original_name='update.md',metadata_json='{}' WHERE source_id=?",
            (EXPECTED_SOURCE_ID,),
        )
    with pytest.raises(ActivationError, match="no exact MLCC"):
        preflight(db_path, package_path)


def test_apply_inserts_all_links_and_preserves_unrelated_tables(tmp_path: Path):
    db_path, package_path, backup_dir = _fixture(tmp_path)
    result = activate_database(db_path, package_path, backup_dir)
    assert result["links_inserted"] == 11
    assert result["backup_sha"] == result["pre_sha"]
    assert result["post_sha"] != result["pre_sha"]
    assert not any(result["preserved_table_changes"].values())
    assert result["post"]["pre_existing_desired_links"] == 11
    assert result["post"]["no_link_claim_link_count"] == 0
    assert result["post"]["unexpected_claim_node_links"] == []
    assert _link_count(db_path) == 11


def test_successful_rerun_is_idempotent(tmp_path: Path):
    db_path, package_path, backup_dir = _fixture(tmp_path)
    activate_database(db_path, package_path, backup_dir)
    pre_rerun_sha = file_sha256(db_path)
    result = activate_database(db_path, package_path, backup_dir)
    assert result["write_needed"] is False
    assert result["idempotent_already_applied"] is True
    assert result["links_inserted"] == 0
    assert result["post_sha"] == pre_rerun_sha
    assert _link_count(db_path) == 11


def test_partial_state_stops_without_filling_remaining_links(tmp_path: Path):
    db_path, package_path, backup_dir = _fixture(tmp_path)
    for claim_id in LINK_CLAIM_IDS[:5]:
        _insert_link(db_path, claim_id, TARGET_NODE_ID)
    with pytest.raises(ActivationError, match="PARTIAL_OR_CONFLICTING_DRIFT"):
        activate_database(db_path, package_path, backup_dir)
    assert _link_count(db_path) == 5


def test_transaction_rolls_back_all_links_on_insert_error(tmp_path: Path):
    db_path, package_path, backup_dir = _fixture(tmp_path)
    blocked_claim_id = LINK_CLAIM_IDS[5]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""CREATE TRIGGER block_one_activation
                BEFORE INSERT ON claim_node_links
                WHEN NEW.claim_id='{blocked_claim_id}'
                BEGIN SELECT RAISE(ABORT, 'blocked test insert'); END"""
        )
    with pytest.raises(sqlite3.IntegrityError, match="blocked test insert"):
        activate_database(db_path, package_path, backup_dir)
    assert _link_count(db_path) == 0
