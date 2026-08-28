from pathlib import Path

import pytest

from pro_a.query import ReadOnlyDatabaseError, ReadOnlyQuery


def test_stats_use_current_and_open_semantics(read_db_path: Path):
    assert ReadOnlyQuery(read_db_path).stats() == {
        "active_node_count": 4,
        "alias_count": 2,
        "current_relation_count": 2,
        "current_part_of_count": 1,
        "source_count": 2,
        "claim_count": 2,
        "current_view_count": 2,
        "open_knowledge_gap_count": 2,
        "open_research_question_count": 1,
    }


def test_canonical_and_alias_search_retain_canonical_identity(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)

    canonical = query.search_nodes("OPTICAL")
    assert canonical[0] == {
        "node_id": "NODE_PARENT",
        "canonical_name": "Optical Components",
        "primary_type": "Segment",
        "matched_by": "canonical_name",
        "matched_text": "Optical Components",
    }

    alias = query.search_nodes("eml")
    assert alias == [{
        "node_id": "NODE_CHILD",
        "canonical_name": "Electro-Absorption Modulated Laser",
        "primary_type": "Product",
        "matched_by": "alias",
        "matched_text": "EML",
    }]


def test_search_primary_type_filter(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    assert query.search_nodes("eml", primary_type="Segment") == []
    assert query.search_nodes("eml", primary_type="Product")[0]["node_id"] == "NODE_CHILD"


def test_node_list_pagination_filter_and_limit_cap(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    page = query.list_nodes(limit=2, offset=1)
    assert [node["node_id"] for node in page] == ["NODE_CHILD", "NODE_PARENT"]
    assert query.list_nodes(primary_type="Equipment") == [{
        "node_id": "NODE_OTHER",
        "canonical_name": "AI Server",
        "primary_type": "Equipment",
    }]
    with pytest.raises(ValueError, match="between 1 and 100"):
        query.list_nodes(limit=101)


def test_node_detail_preserves_part_of_direction_and_relations(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    child = query.node_detail("NODE_CHILD")
    parent = query.node_detail("NODE_PARENT")

    assert child["aliases"] == ["EML"]
    assert [node["node_id"] for node in child["parents"]] == ["NODE_PARENT"]
    assert child["children"] == []
    assert [relation["relation_id"] for relation in child["incoming_relations"]] == ["REL_USES"]
    assert [relation["relation_id"] for relation in child["outgoing_relations"]] == ["REL_PART"]
    assert [node["node_id"] for node in parent["children"]] == ["NODE_CHILD"]
    assert query.node_detail("NODE_MISSING") is None


def test_node_neighbors_are_current_one_hop_graph(read_db_path: Path):
    result = ReadOnlyQuery(read_db_path).node_neighbors("NODE_CHILD")
    assert result["center"]["node_id"] == "NODE_CHILD"
    assert [node["node_id"] for node in result["nodes"]] == ["NODE_OTHER", "NODE_PARENT"]
    assert {edge["relation_id"] for edge in result["edges"]} == {"REL_PART", "REL_USES"}


def test_node_claims_include_source_provenance_in_stable_time_order(read_db_path: Path):
    claims = ReadOnlyQuery(read_db_path).node_claims("NODE_CHILD")
    assert [claim["claim_id"] for claim in claims] == ["CLAIM_2", "CLAIM_1"]
    assert [claim["link_role"] for claim in claims] == ["related", "subject"]
    assert claims[0]["source"] == {
        "source_id": "SRC_2",
        "title": "AI Infrastructure Update",
        "original_name": "ai-update.md",
        "author": "Analyst Two",
        "organization": "Second Org",
        "publication_time": "2026-02-15",
        "source_type": "research_report",
        "source_rank": "B",
    }


def test_node_sources_deduplicate_direct_and_claim_paths(read_db_path: Path):
    sources = ReadOnlyQuery(read_db_path).node_sources("NODE_CHILD")
    assert [source["source_id"] for source in sources] == ["SRC_2", "SRC_1"]
    source_1 = next(source for source in sources if source["source_id"] == "SRC_1")
    assert [item["origin_path"] for item in source_1["provenance"]] == ["direct", "claim"]
    assert source_1["provenance"][0]["link_origin"] == "existing_node_match"
    assert source_1["provenance"][1]["claim_id"] == "CLAIM_1"


def test_current_view_uses_official_revision_order_and_parses_json(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    result = query.node_current_view("NODE_CHILD")

    assert result["view_id"] == "VIEW_CURRENT"
    assert result["version"] == "v_20260301_01"
    assert result["content_json"] == {"thesis": "accelerating", "risks": ["pricing"]}
    assert result["trigger_claim_ids"] == ["CLAIM_1", "CLAIM_MISSING"]
    assert query.node_current_view("NODE_PARENT") is None
    with pytest.raises(KeyError):
        query.node_current_view("NODE_MISSING")


def test_research_question_parses_fields_and_resolves_claims_safely(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    result = query.node_research_question("NODE_CHILD")

    assert result["current_answer"].startswith("Adoption is accelerating")
    assert result["key_variables"][1] == {"variable": "pricing", "direction": "down"}
    assert result["supporting_claim_ids"] == ["CLAIM_1", "CLAIM_MISSING"]
    assert result["supporting_claims"][0]["statement"].startswith("EML is used")
    assert result["supporting_claims"][1] == {
        "claim_id": "CLAIM_MISSING",
        "statement": None,
        "status": None,
        "confidence": None,
    }
    assert result["opposing_claims"][0]["claim_id"] == "CLAIM_2"
    assert query.node_research_question("NODE_PARENT") is None
    with pytest.raises(KeyError):
        query.node_research_question("NODE_MISSING")


def test_knowledge_gaps_parse_json_and_prioritize_open_like_statuses(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    gaps = query.node_knowledge_gaps("NODE_CHILD")

    assert [gap["gap_id"] for gap in gaps] == ["GAP_REFRESH", "GAP_OPEN", "GAP_DONE"]
    assert gaps[1]["source_claim_ids"] == ["CLAIM_1", "CLAIM_MISSING"]
    assert gaps[2]["resolution_claim_id"] == "CLAIM_1"
    assert query.node_knowledge_gaps("NODE_PARENT") == []
    with pytest.raises(KeyError):
        query.node_knowledge_gaps("NODE_MISSING")


def test_source_detail_includes_metadata_nodes_claims_and_evidence(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    result = query.source_detail("SRC_1")

    assert result["analysis_mode"] == "standard"
    assert result["origin_type"] == "local_file"
    assert result["underlying_source_id"] == "SRC_BASE"
    assert "archived_path" not in result
    assert result["linked_nodes"] == [{
        "node_id": "NODE_CHILD",
        "canonical_name": "Electro-Absorption Modulated Laser",
        "primary_type": "Product",
        "role": "primary",
        "confidence": 0.95,
        "link_origin": "existing_node_match",
        "derived_from_node_id": "NODE_PARENT",
        "evidence_excerpt": "EML",
    }]
    assert result["claims"][0]["claim_id"] == "CLAIM_1"
    assert result["claims"][0]["evidence_excerpt"].startswith("EML is used")
    assert result["claims"][0]["linked_nodes"][0]["node_id"] == "NODE_CHILD"
    assert query.source_detail("SRC_MISSING") is None


def test_query_connection_rejects_writes(read_db_path: Path):
    query = ReadOnlyQuery(read_db_path)
    with pytest.raises(ReadOnlyDatabaseError):
        with query.connect() as conn:
            conn.execute("CREATE TABLE forbidden(value TEXT)")


@pytest.mark.parametrize("raw", [None, "broken", "[]", '{"parse_diagnostics":[]}',
                                  '{"parse_diagnostics":{"format":[]}}',
                                  '{"parse_diagnostics":{"format":"pdf","file_size":true}}'])
def test_legacy_or_malformed_parse_metadata_is_not_presented_as_success(raw):
    assert ReadOnlyQuery._parse_diagnostics(raw) is None


@pytest.mark.parametrize("value", [None, [], {"status": "resolved", "locator": "C:/private/file.pdf"},
                                    {"status": "resolved", "locator": "SHEET:C:/private"},
                                    {"status": "ambiguous", "locators": ["PAGE:1", "PAGE:1"]}])
def test_malformed_source_locator_is_not_exposed(value):
    import json
    assert ReadOnlyQuery._source_locator(json.dumps({"validation": {"source_locator": value}})) is None
