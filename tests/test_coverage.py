import sqlite3
from pathlib import Path

import pytest

from pro_a.coverage import exact_node_matches, run_audit, write_csv_outputs
from pro_a.db import Database


@pytest.fixture
def coverage_db_path() -> Path:
    path = Path("workspace") / "coverage_test.db"
    path.unlink(missing_ok=True)
    Database(path).init_schema()
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            [
                ("NODE_CHILD", "Electro-Absorption Modulated Laser", "Product", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_PARENT", "Optical Components", "Segment", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_OTHER", "AI Server", "Equipment", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_RQ", "Adoption Question", "ResearchQuestion", "", "active", "2026-01-01", "2026-01-01"),
            ],
        )
        conn.executemany("INSERT INTO node_aliases(alias,node_id) VALUES(?,?)", [("EML", "NODE_CHILD"), ("Photonics", "NODE_PARENT")])
        conn.executemany(
            "INSERT INTO node_relations(relation_id,from_node_id,relation_type,to_node_id,scope,confidence,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
            [("REL_PART", "NODE_CHILD", "part_of", "NODE_PARENT", "", 1.0, "current", "2026-01-01"), ("REL_USES", "NODE_OTHER", "uses", "NODE_CHILD", "", 0.8, "current", "2026-01-02")],
        )
        conn.executemany(
            "INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,source_type,source_rank,ingested_at) VALUES(?,?,?,?,?,?,?,?,?)",
            [("SRC_1", "Optical Components Report", "one.txt", "archive/one.txt", "a" * 64, "standard", "filing", "A", "2026-01-01"), ("SRC_2", "AI Infrastructure Update", "two.txt", "archive/two.txt", "b" * 64, "standard", "report", "B", "2026-01-01")],
        )
        conn.executemany(
            "INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,ingestion_time,source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,status,confidence,novelty_level,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [("CLAIM_1", "EML is used in optical transmitters.", "fact", "", "2026-01-15", "2026-01-16", "SRC_1", "p.3", "EML is used.", "", "optics", "current", 0.9, "N1", "2026-01-16"), ("CLAIM_2", "AI infrastructure demand is growing.", "forecast", "", "2026-02-15", "2026-02-16", "SRC_2", "p.2", "Demand is growing.", "", "equipment", "current", 0.7, "N2", "2026-02-16")],
        )
        conn.executemany("INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)", [("CLAIM_1", "NODE_CHILD", "subject"), ("CLAIM_2", "NODE_CHILD", "related")])
        conn.execute("INSERT INTO relation_evidence_links(relation_id,claim_id,evidence_role,status,created_at) VALUES(?,?,?,?,?)", ("REL_USES", "CLAIM_1", "supports", "active", "2026-01-16"))
        conn.execute("INSERT INTO source_node_links(source_id,node_id,role,confidence,link_origin,derived_from_node_id,evidence_excerpt) VALUES(?,?,?,?,?,?,?)", ("SRC_1", "NODE_CHILD", "primary", 0.95, "existing_node_match", "", "EML"))
        conn.executemany(
            "INSERT INTO current_views(view_id,node_id,version,status,change_level,content_md,content_json,trigger_claim_ids_json,revision_date,revision_seq,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            [("VIEW_OLD", "NODE_CHILD", "v_20260101", "official", "minor", "Old", "{}", "[]", "20260101", 0, "2026-01-01"), ("VIEW_CURRENT", "NODE_CHILD", "v_20260201", "official", "material", "Current", "{}", '["CLAIM_1"]', "20260201", 1, "2026-02-01")],
        )
        conn.executemany(
            "INSERT INTO knowledge_gaps(gap_id,node_id,title,description,status,source_claim_ids_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            [("GAP_1", "NODE_CHILD", "Open", "", "open", '["CLAIM_1"]', "2026-01-01", "2026-01-01"), ("GAP_2", "NODE_CHILD", "Resolved", "", "resolved", "[]", "2026-01-01", "2026-01-01")],
        )
        conn.execute("INSERT INTO research_questions(rq_id,node_id,question,created_at,updated_at) VALUES(?,?,?,?,?)", ("RQ_1", "NODE_CHILD", "Will adoption accelerate?", "2026-01-01", "2026-01-01"))
    conn.close()
    yield path
    path.unlink(missing_ok=True)


def _add_unlinked_claims(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,ingestion_time,source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,status,confidence,novelty_level,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("CLAIM_CANONICAL_MISMATCH", "Optical Components expanded in this period.", "fact", "", "2026-01-15", "2026-01-16", "SRC_1", "p.4", "Optical Components expanded.", "", "optics", "current", 0.8, "N1", "2026-01-16"),
                ("CLAIM_MULTI_MATCH", "EML and AI Server demand both increased.", "fact", "", "2026-02-15", "2026-02-16", "SRC_2", "p.2", "EML and AI Server demand increased.", "", "equipment", "current", 0.8, "N1", "2026-02-16"),
            ],
        )
    conn.close()


def test_exact_matching_uses_canonical_alias_and_ascii_boundaries():
    nodes = {"GPU_NODE": {"canonical_name": "Graphics Processor"}, "RAIL_NODE": {"canonical_name": "RAIL"}}
    aliases = {"GPU": "GPU_NODE", "AI": "GPU_NODE"}
    canonical, alias = exact_node_matches("GPU and Graphics Processor", nodes, aliases)
    assert canonical == {"GPU_NODE"}
    assert alias == {"GPU_NODE"}
    canonical, alias = exact_node_matches("RAIL production", {"GPU_NODE": nodes["GPU_NODE"]}, aliases)
    assert canonical == set()
    assert alias == set()


def test_coverage_counts_levels_and_relationship_direction(coverage_db_path: Path):
    result = run_audit(coverage_db_path)
    summary = result["summary"]
    assert summary["active_nodes"] == 4
    assert summary["sources"] == 2
    assert summary["claims"] == 2
    assert summary["current_relations"] == 2
    assert summary["current_part_of"] == 1
    assert summary["current_functional_relations"] == 1
    assert summary["knowledge_level_distribution"] == {"LEVEL_0_STRUCTURE_ONLY": 3, "LEVEL_1_SOURCE_CONNECTED": 0, "LEVEL_2_EVIDENCE_CONNECTED": 0, "LEVEL_3_CANONICAL_VIEW": 0, "LEVEL_4_RESEARCH_ACTIVE": 1}
    child = next(row for row in result["node_coverage"] if row["node_id"] == "NODE_CHILD")
    assert child["parent_count"] == 1
    assert child["child_count"] == 0
    assert child["part_of_out_count"] == 1
    assert child["part_of_in_count"] == 0
    assert child["functional_relation_count"] == 1
    assert child["source_count"] == 1
    assert child["claim_count"] == 2


def test_claim_signal_buckets_and_unlinked_rows(coverage_db_path: Path):
    _add_unlinked_claims(coverage_db_path)
    result = run_audit(coverage_db_path)
    by_id = {row["claim_id"]: row for row in result["claim_coverage"]}
    assert by_id["CLAIM_1"]["audit_bucket"] == "HIGH_SIGNAL_REVIEW_CANDIDATE"
    assert "EXACT_ALIAS_MENTION" in by_id["CLAIM_1"]["coverage_labels"]
    assert by_id["CLAIM_2"]["audit_bucket"] == "NO_SAFE_SIGNAL"
    assert "NO_DETERMINISTIC_NODE_SIGNAL" in by_id["CLAIM_2"]["coverage_labels"]
    assert by_id["CLAIM_CANONICAL_MISMATCH"]["audit_bucket"] == "AMBIGUOUS_REVIEW_CANDIDATE"
    assert "EXACT_CANONICAL_MENTION" in by_id["CLAIM_CANONICAL_MISMATCH"]["coverage_labels"]
    assert by_id["CLAIM_MULTI_MATCH"]["audit_bucket"] == "AMBIGUOUS_REVIEW_CANDIDATE"
    assert "MULTIPLE_EXACT_NODE_MENTIONS" in by_id["CLAIM_MULTI_MATCH"]["coverage_labels"]
    assert result["summary"]["unlinked_claims"] == 2
    assert result["summary"]["high_signal_review_candidates"] == 1
    assert result["summary"]["ambiguous_review_candidates"] == 2
    assert result["summary"]["no_safe_signal"] == 1
    assert result["summary"]["claim_node_activation_ready"] == "PARTIAL"


def test_csv_outputs_are_deterministic_and_have_required_files(coverage_db_path: Path):
    result = run_audit(coverage_db_path)
    output = Path("workspace") / "coverage_csv_test"
    output.mkdir(exist_ok=True)
    for old in output.glob("*.csv"):
        old.unlink()
    paths = write_csv_outputs(result, output)
    assert [path.name for path in paths] == ["node_coverage.csv", "source_coverage.csv", "claim_coverage.csv", "unlinked_claims.csv"]
    assert paths[0].read_text(encoding="utf-8").splitlines()[0].startswith("node_id,canonical_name")
    assert paths[-1].read_text(encoding="utf-8").splitlines()[0].startswith("claim_id,source_id")
    for path in paths:
        path.unlink(missing_ok=True)
    output.rmdir()
