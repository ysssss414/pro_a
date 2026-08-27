from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pro_a.api import create_app
from pro_a.db import Database
from pro_a.query import ReadOnlyQuery


@pytest.fixture
def history_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "history.db"
    db = Database(path)
    db.init_schema()
    with db.connect() as conn:
        conn.executemany(
            """INSERT INTO nodes(
               node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                ("NODE_EMPTY", "Empty Node", "Product", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_SINGLE", "Single View Node", "Company", "", "active", "2026-01-01", "2026-01-01"),
                ("NODE_HISTORY", "History Node", "Product", "", "active", "2026-01-01", "2026-01-01"),
            ],
        )
        conn.executemany(
            """INSERT INTO current_views(
               view_id,node_id,version,status,change_level,previous_view_id,
               content_md,content_json,trigger_source_id,trigger_claim_ids_json,
               revision_date,revision_seq,accepted_proposal_id,created_at,confirmed_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "VIEW_SINGLE", "NODE_SINGLE", "v_20260101", "official", "initial", None,
                    "Single initial view", '{"one_line_conclusion":"Initial"}', "SRC_SINGLE",
                    '["CLAIM_SINGLE"]', "20260101", 0, "PROP_SINGLE", "2026-01-01", "2026-01-01",
                ),
                (
                    "VIEW_OLD", "NODE_HISTORY", "v_20260115", "official", "initial", None,
                    "Old historical view", '{"one_line_conclusion":"Old"}', None, "[]",
                    "20260115", 0, "PROP_OLD", "2026-04-01", "2026-01-15",
                ),
                (
                    "VIEW_MIDDLE", "NODE_HISTORY", "v_20260201", "official", "minor", "VIEW_OLD",
                    "Malformed JSON fallback view", "{malformed", None, "not-json",
                    "20260201", 0, "PROP_MIDDLE", "2026-02-01", "2026-02-01",
                ),
                (
                    "VIEW_LATEST", "NODE_HISTORY", "v_20260201_01", "official", "material", "VIEW_MIDDLE",
                    "Latest historical view", '{"one_line_conclusion":"Latest"}', "SRC_LATEST",
                    '["CLAIM_LATEST"]', "20260201", 1, "PROP_LATEST", "2026-01-01", "2026-02-02",
                ),
                (
                    "VIEW_DRAFT", "NODE_HISTORY", "v_20990101", "draft", "major", "VIEW_LATEST",
                    "Draft must stay hidden", '{"one_line_conclusion":"Draft"}', None, "[]",
                    "20990101", 0, "", "2099-01-01", "",
                ),
            ],
        )
    return path


def test_history_read_is_official_ordered_safe_and_read_only(history_db_path: Path):
    before = sha256(history_db_path.read_bytes()).hexdigest()
    query = ReadOnlyQuery(history_db_path)

    history = query.node_current_view_history("NODE_HISTORY")

    assert [view["view_id"] for view in history] == [
        "VIEW_LATEST", "VIEW_MIDDLE", "VIEW_OLD"
    ]
    assert [view["previous_view_id"] for view in history] == [
        "VIEW_MIDDLE", "VIEW_OLD", None
    ]
    assert [(view["revision_date"], view["revision_seq"]) for view in history] == [
        ("20260201", 1), ("20260201", 0), ("20260115", 0)
    ]
    assert history[0]["content_json"] == {"one_line_conclusion": "Latest"}
    assert history[1]["content_json"] == {}
    assert history[1]["trigger_claim_ids"] == []
    assert history[2]["content_md"] == "Old historical view"
    assert query.node_current_view("NODE_HISTORY") == history[0]
    assert query.node_current_view_history("NODE_SINGLE")[0]["change_level"] == "initial"
    assert query.node_current_view_history("NODE_EMPTY") == []
    with pytest.raises(KeyError):
        query.node_current_view_history("NODE_MISSING")
    assert sha256(history_db_path.read_bytes()).hexdigest() == before


def test_history_api_distinguishes_missing_empty_single_and_multiple(history_db_path: Path):
    client = TestClient(create_app(history_db_path))

    history = client.get("/api/nodes/NODE_HISTORY/current-view-history")
    assert history.status_code == 200
    assert history.json()["node_id"] == "NODE_HISTORY"
    assert [view["view_id"] for view in history.json()["views"]] == [
        "VIEW_LATEST", "VIEW_MIDDLE", "VIEW_OLD"
    ]
    assert client.get("/api/nodes/NODE_SINGLE/current-view-history").json()["views"][0]["view_id"] == "VIEW_SINGLE"
    assert client.get("/api/nodes/NODE_EMPTY/current-view-history").json() == {
        "node_id": "NODE_EMPTY",
        "views": [],
    }
    missing = client.get("/api/nodes/NODE_MISSING/current-view-history")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Node not found"}

    current = client.get("/api/nodes/NODE_HISTORY/current-view")
    assert current.status_code == 200
    assert current.json()["view_id"] == "VIEW_LATEST"
