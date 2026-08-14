from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pro_a.current_view import create_official_view

from stability_helpers import make_config


def test_current_view_returns_latest_revision_when_timestamps_are_equal(tmp_path: Path, monkeypatch):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Same Second Node", "Theme")

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 8, 13, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr("pro_a.current_view.datetime", FixedDateTime)
    monkeypatch.setattr("pro_a.current_view.now_iso", lambda: "2026-08-13T12:00:00+08:00")

    first = create_official_view(db, cfg, node_id, {"one_line_conclusion": "first"}, "initial")
    second = create_official_view(db, cfg, node_id, {"one_line_conclusion": "second"}, "minor")
    current = db.current_view(node_id)

    assert first["version"] == "v_20260813"
    assert second["version"] == "v_20260813_01"
    assert current["view_id"] == second["view_id"]
    assert current["version"] == "v_20260813_01"
