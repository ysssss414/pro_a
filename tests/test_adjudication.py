import csv
import json
import sqlite3
from pathlib import Path

from pro_a.adjudication import CSV_FIELDS, build_package, write_csv, write_markdown
from pro_a.db import Database


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "adjudication.db"
    Database(path).init_schema()
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            [
                ("NODE_CHILD", "Electro-Absorption Modulated Laser", "Product", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_PARENT", "Optical Components", "Segment", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_OTHER", "AI Server", "Equipment", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_INACTIVE", "Retired Node", "Product", "", "inactive", "2026-01-01", "2026-01-01"),
            ],
        )
        conn.executemany("INSERT INTO node_aliases(alias,node_id) VALUES(?,?)", [("EML", "NODE_CHILD"), ("AI Compute", "NODE_OTHER")])
        conn.executemany(
            "INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,source_type,source_rank,organization,publication_time,ingested_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            [("SRC_1", "Optical Components Report", "one.txt", "archive/one.txt", "a" * 64, "standard", "filing", "A", "Org", "2026-01-15", "2026-01-16")],
        )
        conn.executemany(
            "INSERT INTO source_node_links(source_id,node_id,role) VALUES(?,?,?)",
            [("SRC_1", "NODE_CHILD", "primary")],
        )
        conn.executemany(
            "INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,ingestion_time,source_id,evidence_pointer,evidence_excerpt,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("CLAIM_UNION", "Optical Components and EML expanded.", "fact", "", "2026-01-15", "2026-01-16", "SRC_1", "p.4", "EML expanded.", "current", 0.8, "2026-01-16"),
                ("CLAIM_NONE", "Demand expanded.", "fact", "", "2026-01-15", "2026-01-16", "SRC_1", "p.5", "Demand expanded.", "current", 0.8, "2026-01-16"),
                ("CLAIM_LINKED", "Already linked.", "fact", "", "2026-01-15", "2026-01-16", "SRC_1", "p.6", "Already linked.", "current", 0.8, "2026-01-16"),
            ],
        )
        conn.execute("INSERT INTO claim_node_links(claim_id,node_id) VALUES(?,?)", ("CLAIM_LINKED", "NODE_CHILD"))
    return path


def test_package_contains_only_unlinked_claims_and_union_provenance(tmp_path: Path):
    package = build_package(_db(tmp_path))
    assert [item.claim_id for item in package["items"]] == ["CLAIM_NONE", "CLAIM_UNION"]
    union = next(item for item in package["items"] if item.claim_id == "CLAIM_UNION")
    assert [candidate.node_id for candidate in union.candidates] == ["NODE_CHILD", "NODE_PARENT"]
    assert union.source_linked_node_ids == ("NODE_CHILD",)
    assert union.exact_canonical_node_ids == ("NODE_PARENT",)
    assert union.exact_alias_node_ids == ("NODE_CHILD",)
    child = union.candidates[0]
    assert child.signals == ("SOURCE_LINK", "EXACT_ALIAS")
    assert child.matched_aliases == ("EML",)
    assert all(item.decision == "PENDING" and not item.selected_node_ids for item in package["items"])


def test_rendered_outputs_preserve_required_fields_and_pending_defaults(tmp_path: Path):
    package = build_package(_db(tmp_path))
    markdown = tmp_path / "package.md"
    csv_path = tmp_path / "package.csv"
    write_markdown(package, markdown)
    write_csv(package, csv_path)
    text = markdown.read_text(encoding="utf-8")
    assert "This package contains 2 unlinked Claims requiring human adjudication." in text
    assert "No Claim→Node decisions in this document are machine-approved." in text
    assert "- Decision: PENDING" in text
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    assert list(rows[0]) == CSV_FIELDS
    assert {row["decision"] for row in rows} == {"PENDING"}
    assert all(row["selected_node_ids"] == "" and row["reviewer_note"] == "" for row in rows)
    signals = json.loads(next(row["candidate_signals"] for row in rows if row["claim_id"] == "CLAIM_UNION"))
    assert signals[0]["signals"] == ["SOURCE_LINK", "EXACT_ALIAS"]
