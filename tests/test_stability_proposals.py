from __future__ import annotations

from pathlib import Path

import pytest

from pro_a.analyzer import Analyzer
from pro_a.current_view import create_official_view
from pro_a.ima import IMAError
from pro_a.proposals import ProposalManager

from stability_helpers import current_view_payload, make_config


class NoChangeAnalyzer:
    available = True

    def review_impact(self, node, current_view_md, evidence, context):
        return {
            "requires_change": False,
            "change_level": "none",
            "evidence_sufficiency": {"sufficient": True},
        }


class ExplodingAnalyzer:
    available = True

    def review_impact(self, node, current_view_md, evidence, context):
        raise RuntimeError("forced propagation failure")


class FailingIMA:
    available = True

    def upload_file(self, *args, **kwargs):
        raise IMAError("forced IMA failure")


class RecoveringIMA:
    available = True

    def __init__(self):
        self.fail = True

    def upload_file(self, *args, **kwargs):
        if self.fail:
            raise IMAError("temporary IMA failure")
        return {"media_id": "MEDIA_OK", "skipped": False}


def test_accept_db_phase_failure_rolls_back_view_and_proposal(tmp_path: Path, monkeypatch):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Atomic Node", "Theme")
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "atomic"), target_node_id=node_id)
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())

    def explode(*args, **kwargs):
        raise RuntimeError("forced database phase failure")

    monkeypatch.setattr(manager.propagation, "start_from_accepted_view", explode)
    with pytest.raises(RuntimeError, match="database phase"):
        manager.accept(pid)

    assert db.proposal(pid)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 0


def test_accept_same_proposal_is_idempotent(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Idempotent Node", "Theme")
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "once"), target_node_id=node_id)
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())

    first = manager.accept(pid)
    second = manager.accept(pid)

    assert first["view_id"] == second["view_id"]
    assert first["version"] == second["version"]
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 1
    assert db.proposal(pid)["status"] == "accepted"


def test_accept_same_new_node_proposal_is_idempotent(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    pid = db.add_proposal(
        "new_node",
        {"canonical_name": "One Node", "primary_type": "Theme", "aliases": [], "related_claim_ids": []},
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())

    first = manager.accept(pid)
    second = manager.accept(pid)

    assert second == first
    assert db.one("SELECT COUNT(*) AS n FROM nodes")["n"] == 1


def test_stale_current_view_proposal_is_not_accepted(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Stale Node", "Theme")
    create_official_view(db, cfg, node_id, {"one_line_conclusion": "v1"}, "initial")
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "proposal-on-v1"), target_node_id=node_id)
    create_official_view(db, cfg, node_id, {"one_line_conclusion": "v2"}, "minor")
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())

    with pytest.raises(ValueError, match="stale"):
        manager.accept(pid)

    assert db.proposal(pid)["status"] == "stale"
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 2


def test_propagation_failure_after_commit_is_persisted_for_retry(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Propagation Source", "Theme")
    neighbor_id = db.add_node("Propagation Target", "Theme")
    db.add_relation(node_id, "related_to", neighbor_id)
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "accepted"), target_node_id=node_id)
    manager = ProposalManager(cfg, db, ExplodingAnalyzer())

    result = manager.accept(pid)

    assert result["view_id"]
    assert db.proposal(pid)["status"] == "accepted"
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 1
    retry = db.one("SELECT status,last_error,attempts FROM impact_reviews WHERE node_id=?", (neighbor_id,))
    assert retry["status"] == "retry"
    assert "forced propagation failure" in retry["last_error"]
    assert retry["attempts"] == 1


def test_ima_failure_after_commit_is_persisted_for_retry(tmp_path: Path):
    cfg, db = make_config(tmp_path, ima_enabled=True)
    node_id = db.add_node("IMA Node", "Theme")
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "accepted"), target_node_id=node_id)
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    manager.ima = FailingIMA()

    result = manager.accept(pid)

    assert result["view_id"]
    assert db.proposal(pid)["status"] == "accepted"
    retry = db.one("SELECT status,last_error,attempts FROM side_effect_jobs WHERE job_type='ima_sync_current_view'")
    assert retry["status"] == "retry"
    assert "forced IMA failure" in retry["last_error"]
    assert retry["attempts"] == 1


def test_reaccept_accepted_proposal_retries_side_effect_without_new_view(tmp_path: Path):
    cfg, db = make_config(tmp_path, ima_enabled=True)
    node_id = db.add_node("Recoverable IMA Node", "Theme")
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "accepted"), target_node_id=node_id)
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    ima = RecoveringIMA()
    manager.ima = ima

    first = manager.accept(pid)
    assert db.one("SELECT status FROM side_effect_jobs WHERE job_type='ima_sync_current_view'")["status"] == "retry"

    ima.fail = False
    second = manager.accept(pid)

    assert second["view_id"] == first["view_id"]
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 1
    job = db.one("SELECT status,attempts FROM side_effect_jobs WHERE job_type='ima_sync_current_view'")
    assert job == {"status": "done", "attempts": 2}


def test_markdown_failure_after_commit_is_retryable_without_new_view(tmp_path: Path, monkeypatch):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Recoverable Markdown Node", "Theme")
    pid = db.add_proposal("current_view_change", current_view_payload(db, node_id, "accepted"), target_node_id=node_id)
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    original = manager._write_view

    monkeypatch.setattr(manager, "_write_view", lambda view_id: (_ for _ in ()).throw(OSError("disk unavailable")))
    first = manager.accept(pid)

    assert db.proposal(pid)["status"] == "accepted"
    assert db.one("SELECT status FROM side_effect_jobs WHERE job_type='write_current_view_markdown'")["status"] == "retry"

    monkeypatch.setattr(manager, "_write_view", original)
    second = manager.accept(pid)

    assert second["view_id"] == first["view_id"]
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 1
    job = db.one("SELECT status,attempts FROM side_effect_jobs WHERE job_type='write_current_view_markdown'")
    assert job == {"status": "done", "attempts": 2}
    assert Path(second["path"]).exists()
