from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pro_a.api import create_app
from pro_a.current_view_compare import CurrentViewCompareValidationError
from pro_a.db import Database
from pro_a.query import CurrentViewCompareNotFoundError, ReadOnlyQuery


@pytest.fixture
def compare_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "compare.db"
    db = Database(path)
    db.init_schema()
    with db.connect() as conn:
        conn.executemany(
            """INSERT INTO nodes(
               node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                ("NODE_EMPTY", "Empty", "Product", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_SINGLE", "Single", "Company", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_HISTORY", "History", "Product", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_OTHER", "Other", "Product", "", "active", "2026-01-01", "2026-01-01"),
            ],
        )
        conn.executemany(
            """INSERT INTO sources(
               source_id,title,original_name,archived_path,sha256,ingestion_mode,
               source_type,source_rank,author,organization,publication_time,ingested_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                ("SRC_1", "Source One", "one.md", "archive/one.md", "a" * 64,
                 "standard", "research_report", "A", "", "", "2026-01-01", "2026-01-01"),
                ("SRC_2", "Source Two", "two.md", "archive/two.md", "b" * 64,
                 "standard", "company_filing", "B", "", "", "2026-03-01", "2026-03-01"),
            ],
        )
        conn.executemany(
            """INSERT INTO claims(
               claim_id,statement,nature,fact_time,publication_time,ingestion_time,
               source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,
               status,confidence,novelty_level,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                ("C1", "Claim one", "fact", "2026-01-01", "2026-01-01", "2026-01-01",
                 "SRC_1", "p.1", "Claim one", "", "", "current", 0.9, "N1", "2026-01-01"),
                ("C2", "Claim two", "fact", "2026-02-01", "2026-02-01", "2026-02-01",
                 "SRC_2", "p.2", "Claim two", "", "", "current", 0.8, "N1", "2026-02-01"),
            ],
        )
        conn.executemany(
            """INSERT INTO current_views(
               view_id,node_id,version,status,change_level,previous_view_id,
               content_md,content_json,trigger_source_id,trigger_claim_ids_json,
               revision_date,revision_seq,accepted_proposal_id,created_at,confirmed_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                ("VIEW_SINGLE", "NODE_SINGLE", "v_20260101", "official", "initial", None,
                 "Single", '{"one_line_conclusion":"Initial"}', "SRC_1", '["C1"]',
                 "20260101", 0, "PROP_SINGLE", "2026-01-01", "2026-01-01"),
                ("V1", "NODE_HISTORY", "v_20260101", "official", "initial", None,
                 "V1", '{"one_line_conclusion":"A","investment_implication":"Same",'
                 '"key_facts":["F1","F2"],"key_watch_items":["W1"],'
                 '"type_specific":{"demand_drivers":["D1"],"capacity":["Cap1"]}}',
                 "SRC_1", '["C1"]', "20260101", 0, "PROP_1", "2026-01-01", "2026-01-01"),
                ("V2", "NODE_HISTORY", "v_20260201", "official", "minor", "V1",
                 "V2", '{"one_line_conclusion":"B","investment_implication":"Same",'
                 '"key_facts":["F2","F3"],"key_watch_items":["W1","W2"],'
                 '"recent_change":"Stored change only",'
                 '"type_specific":{"demand_drivers":["D1","D2"],'
                 '"pricing":"Tight","capacity":["Cap1"]}}',
                 "SRC_1", '["C1","C2"]', "20260201", 0, "PROP_2", "2026-02-01", "2026-02-01"),
                ("V3", "NODE_HISTORY", "v_20260301", "official", "material", "V2",
                 "V3 malformed", "{malformed", "SRC_2", '["C2","C_MISSING"]',
                 "20260301", 0, "PROP_3", "2026-03-01", "2026-03-01"),
                ("VIEW_DRAFT", "NODE_HISTORY", "v_20260401", "draft", "major", "V3",
                 "Draft", "{}", "SRC_2", "[]", "20260401", 0, "", "2026-04-01", ""),
                ("VIEW_OTHER", "NODE_OTHER", "v_20260115", "official", "initial", None,
                 "Other", "{}", None, "[]", "20260115", 0, "PROP_OTHER", "2026-01-15", "2026-01-15"),
            ],
        )
    return path


def test_compare_query_resolves_claims_and_preserves_read_only_invariant(compare_db_path: Path):
    before = sha256(compare_db_path.read_bytes()).hexdigest()
    query = ReadOnlyQuery(compare_db_path)

    result = query.node_current_view_compare("NODE_HISTORY", "V1", "V2")

    assert result["base"]["view_id"] == "V1"
    assert result["target"] == {
        "view_id": "V2", "version": "v_20260201", "revision_date": "20260201",
        "revision_seq": 0, "change_level": "minor", "previous_view_id": "V1",
        "recent_change": "Stored change only",
    }
    assert result["list_changes"]["key_facts"] == {
        "added": ["F3"], "removed": ["F1"], "unchanged": ["F2"]
    }
    assert result["type_specific_changes"]["demand_drivers"]["added"] == ["D2"]
    assert result["evidence"]["added"] == [{
        "claim_id": "C2", "resolved": True, "statement": "Claim two",
        "status": "current", "confidence": 0.8, "source_id": "SRC_2",
        "source_title": "Source Two", "source_rank": "B",
    }]
    assert result["evidence"]["unchanged"][0]["claim_id"] == "C1"
    assert sha256(compare_db_path.read_bytes()).hexdigest() == before


def test_compare_query_malformed_json_and_unresolved_claim_are_safe(compare_db_path: Path):
    result = ReadOnlyQuery(compare_db_path).node_current_view_compare(
        "NODE_HISTORY", "V2", "V3"
    )

    assert result["scalar_changes"][0]["after"] == ""
    assert result["type_specific_changes"]["capacity"]["status"] == "dimension_removed"
    assert result["evidence"]["added"] == [{
        "claim_id": "C_MISSING", "resolved": False, "statement": None,
        "status": None, "confidence": None, "source_id": None,
        "source_title": None, "source_rank": None,
    }]
    assert [item["claim_id"] for item in result["evidence"]["removed"]] == ["C1"]
    assert [item["claim_id"] for item in result["evidence"]["unchanged"]] == ["C2"]
    assert result["trigger_source_change"]["status"] == "changed"


def test_compare_query_rejects_invalid_pairs_and_missing_records(compare_db_path: Path):
    query = ReadOnlyQuery(compare_db_path)
    with pytest.raises(CurrentViewCompareValidationError, match="different"):
        query.node_current_view_compare("NODE_HISTORY", "V1", "V1")
    with pytest.raises(CurrentViewCompareValidationError, match="requested Node"):
        query.node_current_view_compare("NODE_HISTORY", "V1", "VIEW_OTHER")
    with pytest.raises(CurrentViewCompareValidationError, match="official"):
        query.node_current_view_compare("NODE_HISTORY", "V3", "VIEW_DRAFT")
    with pytest.raises(CurrentViewCompareValidationError, match="older"):
        query.node_current_view_compare("NODE_HISTORY", "V2", "V1")
    with pytest.raises(CurrentViewCompareNotFoundError):
        query.node_current_view_compare("NODE_HISTORY", "V1", "VIEW_MISSING")
    with pytest.raises(KeyError):
        query.node_current_view_compare("NODE_MISSING", "V1", "V2")


def test_compare_api_contract_and_error_statuses(compare_db_path: Path):
    client = TestClient(create_app(compare_db_path))
    response = client.get(
        "/api/nodes/NODE_HISTORY/current-view-compare",
        params={"base_view_id": "V1", "target_view_id": "V2"},
    )
    assert response.status_code == 200
    assert response.json()["evidence"]["added"][0]["statement"] == "Claim two"

    cases = [
        ("NODE_HISTORY", "V1", "V1", 422),
        ("NODE_HISTORY", "V2", "V1", 422),
        ("NODE_HISTORY", "V1", "VIEW_OTHER", 422),
        ("NODE_HISTORY", "V3", "VIEW_DRAFT", 422),
        ("NODE_HISTORY", "V1", "VIEW_MISSING", 404),
        ("NODE_MISSING", "V1", "V2", 404),
    ]
    for node_id, base_id, target_id, expected in cases:
        result = client.get(
            f"/api/nodes/{node_id}/current-view-compare",
            params={"base_view_id": base_id, "target_view_id": target_id},
        )
        assert result.status_code == expected

    assert client.get("/api/nodes/NODE_EMPTY/current-view-history").json()["views"] == []
    assert len(client.get("/api/nodes/NODE_SINGLE/current-view-history").json()["views"]) == 1
    assert len(client.get("/api/nodes/NODE_HISTORY/current-view-history").json()["views"]) == 3
