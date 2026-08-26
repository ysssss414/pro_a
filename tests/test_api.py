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
    assert response.json()[0]["source"]["source_id"] == "SRC_2"


def test_node_sources(client: TestClient):
    response = client.get("/api/nodes/NODE_CHILD/sources")
    assert response.status_code == 200
    assert len(response.json()) == 2
    source_1 = next(source for source in response.json() if source["source_id"] == "SRC_1")
    assert {item["origin_path"] for item in source_1["provenance"]} == {"direct", "claim"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/nodes/NODE_MISSING",
        "/api/nodes/NODE_MISSING/neighbors",
        "/api/nodes/NODE_MISSING/claims",
        "/api/nodes/NODE_MISSING/sources",
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
