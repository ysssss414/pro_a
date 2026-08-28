from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pro_a.api import create_app


@pytest.fixture
def client(read_db_path: Path) -> TestClient:
    return TestClient(create_app(read_db_path))


def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stats(client: TestClient):
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json()["active_node_count"] == 4
    assert response.json()["current_part_of_count"] == 1


def test_nodes(client: TestClient):
    response = client.get("/api/nodes", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    assert response.json()[0]["node_id"] == "NODE_CHILD"


def test_node_search(client: TestClient):
    response = client.get("/api/nodes/search", params={"q": "eml", "primary_type": "Product"})
    assert response.status_code == 200
    assert response.json()[0]["matched_by"] == "alias"
    assert response.json()[0]["node_id"] == "NODE_CHILD"


def test_node_detail(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD")
    assert response.status_code == 200
    assert response.json()["parents"][0]["node_id"] == "NODE_PARENT"


def test_node_neighbors(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/neighbors")
    assert response.status_code == 200
    assert len(response.json()["nodes"]) == 2
    assert len(response.json()["edges"]) == 2


def test_node_claims(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/claims")
    assert response.status_code == 200
    assert response.json()[0]["claim_id"] == "CLAIM_2"
    assert response.json()[0]["link_role"] == "related"
    assert response.json()[0]["source"]["source_id"] == "SRC_2"


def test_node_sources(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/sources")
    assert response.status_code == 200
    assert len(response.json()) == 2
    source_1 = next(source for source in response.json() if source["source_id"] == "SRC_1")
    assert {item["origin_path"] for item in source_1["provenance"]} == {"direct", "claim"}


def test_node_current_view_returns_current_or_null(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/current-view")
    assert response.status_code == 200
    assert response.json()["view_id"] == "VIEW_CURRENT"
    assert response.json()["content_json"]["thesis"] == "accelerating"
    assert client.get("/api/nodes/NODE_PARENT/current-view").json() is None


def test_node_research_question_returns_resolved_claims_or_null(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/research-question")
    assert response.status_code == 200
    assert response.json()["supporting_claims"][0]["claim_id"] == "CLAIM_1"
    assert response.json()["supporting_claims"][1]["statement"] is None
    assert client.get("/api/nodes/NODE_PARENT/research-question").json() is None


def test_node_knowledge_gaps_returns_ordered_list_or_empty(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/knowledge-gaps")
    assert response.status_code == 200
    assert [gap["gap_id"] for gap in response.json()] == [
        "GAP_REFRESH", "GAP_OPEN", "GAP_DONE"
    ]
    assert client.get("/api/nodes/NODE_PARENT/knowledge-gaps").json() == []


def test_source_detail_returns_structured_knowledge_links(client: TestClient):
    response = client.get("/api/sources/SRC_1")
    assert response.status_code == 200
    assert response.json()["linked_nodes"][0]["node_id"] == "NODE_CHILD"
    assert response.json()["claims"][0]["linked_nodes"][0]["role"] == "subject"
    assert "archived_path" not in response.json()


def test_source_not_found(client: TestClient):
    response = client.get("/api/sources/SRC_MISSING")
    assert response.status_code == 404
    assert response.json() == {"detail": "Source not found"}


def test_source_parse_observability_allowlists_metadata_and_preserves_pointer(read_db_path: Path, tmp_path: Path):
    import json
    from pro_a.db import Database
    from pro_a.parsers import parse_source_with_diagnostics
    from multiformat_helpers import write_source

    path = tmp_path / "fixture.pdf"
    write_source(path)
    diag = parse_source_with_diagnostics(path).diagnostics
    db = Database(read_db_path)
    db.execute("UPDATE sources SET metadata_json=? WHERE source_id='SRC_1'", (json.dumps({
        "parse_diagnostics": {**diag, "local_path": "PRIVATE_SECRET", "error": "PRIVATE_SECRET"},
        "ima_credentials": "PRIVATE_SECRET", "analysis_quality": {"path": "PRIVATE_SECRET"},
    }),))
    db.execute("UPDATE claims SET structured_json=? WHERE claim_id='CLAIM_1'", (json.dumps({
        "validation": {"source_locator": {"status": "resolved", "locator": "PAGE:2", "secret": "PRIVATE_SECRET"}},
        "private": "PRIVATE_SECRET",
    }),))
    with TestClient(create_app(read_db_path)) as client:
        detail = client.get("/api/sources/SRC_1")
        claims = client.get("/api/nodes/NODE_CHILD/claims")
    assert detail.status_code == claims.status_code == 200
    assert detail.json()["parse_diagnostics"] == diag
    assert detail.json()["claims"][0]["source_locator"]["locator"] == "PAGE:2"
    node_claim = next(c for c in claims.json() if c["claim_id"] == "CLAIM_1")
    assert node_claim["source_locator"]["locator"] == "PAGE:2"
    assert node_claim["evidence_pointer"] == detail.json()["claims"][0]["evidence_pointer"]
    assert "PRIVATE_SECRET" not in detail.text + claims.text
    assert "metadata_json" not in detail.text and "archived_path" not in detail.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/nodes/NODE_MISSING",
        "/api/nodes/NODE_MISSING/neighbors",
        "/api/nodes/NODE_MISSING/claims",
        "/api/nodes/NODE_MISSING/sources",
        "/api/nodes/NODE_MISSING/current-view",
        "/api/nodes/NODE_MISSING/research-question",
        "/api/nodes/NODE_MISSING/knowledge-gaps",
    ],
)
def test_node_not_found(path: str, client: TestClient):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {"detail": "Node not found"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/nodes?limit=0",
        "/api/nodes?offset=-1",
        "/api/nodes/search",
    ],
)
def test_invalid_parameters_return_422(path: str, client: TestClient):
    assert client.get(path).status_code == 422


def test_limit_cap_returns_422(client: TestClient):
    assert client.get("/api/nodes", params={"limit": 101}).status_code == 422
    assert client.get("/api/nodes/search", params={"q": "eml", "limit": 101}).status_code == 422


def test_unavailable_database_returns_503_without_creating_it(tmp_path: Path):
    missing = tmp_path / "missing.db"
    response = TestClient(create_app(missing)).get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "Knowledge database unavailable"}
    assert not missing.exists()
