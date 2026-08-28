from __future__ import annotations

import json
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

import pro_a.current_view as current_view
import pro_a.human_proposal_resolution as resolver
import pro_a.production_proposal_gateway as gateway
from pro_a.api import create_app
from pro_a.config import load_config
from pro_a.db import Database
from pro_a.human_review_intake import HumanReviewIntakeError, read_artifact
from pro_a.ima import IMAClient
from pro_a.impact_recovery import ImpactRecoveryService
from pro_a.llm import ChatLLM
from pro_a.propagation import PropagationManager
from pro_a.proposals import ProposalManager
from pro_a.query import ReadOnlyQuery
from pro_a.storage import sha256_file
from scripts.phase2_7c_proposal_resolution import main
from test_human_review_intake import db_path, edited_draft, forbidden, snapshot


@pytest.fixture(autouse=True)
def no_runtime(monkeypatch):
    for cls in (ProposalManager, PropagationManager, IMAClient, ImpactRecoveryService, ChatLLM):
        monkeypatch.setattr(cls, "__init__", forbidden)
    for name in ("accept", "reject"):
        monkeypatch.setattr(ProposalManager, name, forbidden)
    for name in ("start_from_accepted_view", "run_batch", "resume_batch", "evaluate_node", "_create_gap", "_create_rq_candidate"):
        monkeypatch.setattr(PropagationManager, name, forbidden)
    monkeypatch.setattr(current_view, "write_official_view_file", forbidden)
    monkeypatch.setattr(current_view, "create_official_view", forbidden)


@pytest.fixture
def configured(db_path, monkeypatch):
    path = db_path.parent / "configured" / "pro_a.db"
    path.parent.mkdir()
    shutil.copyfile(db_path, path)
    cfg = load_config()
    cfg = replace(cfg, workspace=replace(cfg.workspace, root=path.parent))
    monkeypatch.setattr(resolver, "load_config", lambda: cfg)
    monkeypatch.setattr(gateway, "load_config", lambda: cfg)
    return path


def pending(path, action="ACCEPT", decision="minor"):
    draft = edited_draft(path, decision)
    gaps = draft["payload"]["proposed_current_view"]["knowledge_gaps"]
    while gaps[-1] in gaps[:-1]:
        gaps[-1] += "仍需进一步独立复核。"
    created = gateway.apply_production(draft)
    detail = ReadOnlyQuery(path).view_proposal_detail(created["proposal_id"])
    return {"document_type": "human_view_proposal_resolution", "schema_version": "1", "status": "READY",
            "proposal_id": detail["proposal_id"], "action": action, "reason": "Explicit fixture resolution; never live authority.",
            "proposal_snapshot": detail["proposal_snapshot"]}


def blocked(path, artifact, code):
    before = snapshot(path)
    with pytest.raises(HumanReviewIntakeError, match=code):
        resolver.resolve_production(artifact)
    assert snapshot(path) == before


@pytest.mark.parametrize("decision", ["minor", "material", "thesis"])
def test_accept_exact_content_provenance_and_only_two_tables(configured, decision):
    artifact = pending(configured, decision=decision)
    before = snapshot(configured)
    original = Database(configured).proposal(artifact["proposal_id"])
    assert resolver.preview_resolution(artifact)["would_resolve"] is True
    receipt = resolver.resolve_production(artifact)
    after = snapshot(configured)
    assert len(after["proposals"]) == len(before["proposals"])
    assert len(after["current_views"]) == len(before["current_views"]) + 1
    assert {k:v for k,v in before.items() if k not in {"proposals", "current_views"}} == {
        k:v for k,v in after.items() if k not in {"proposals", "current_views"}}
    payload = artifact["proposal_snapshot"]["payload"]
    view = Database(configured).current_view(payload["node_id"])
    assert json.loads(view["content_json"]) == payload["proposed_current_view"]
    assert view["accepted_proposal_id"] == artifact["proposal_id"]
    assert view["previous_view_id"] == payload["previous_view_id"]
    assert view["status"] == "official" and view["change_level"] == decision
    assert view["trigger_source_id"] == payload["trigger_source_id"]
    assert json.loads(view["trigger_claim_ids_json"]) == payload["evidence_claim_ids"]
    row = Database(configured).proposal(artifact["proposal_id"])
    assert row["payload_json"] == original["payload_json"] and row["reason"] == original["reason"]
    assert row["status"] == "accepted" and row["resolved_at"]
    assert row["source_impact_id"] == row["propagation_batch_id"] == ""
    result = json.loads(row["result_json"])
    assert result["human_resolution"] == {**artifact, "resolved_at": row["resolved_at"]}
    assert result["activation_scope"] == "DIRECT_VIEW_ONLY" and "path" not in result
    assert snapshot(receipt["backup_location"]) == before
    assert receipt["new_view_id"] == view["view_id"] and receipt["new_version"] == view["version"]
    assert receipt["integrity_check"] == "ok" and receipt["foreign_key_check"] == []
    assert receipt["post_write_sha256"] == sha256_file(configured)
    assert not (configured.parent / "generated" / "current_views").exists()
    assert json.loads(open(receipt["receipt_path"], encoding="utf-8").read()) == receipt


@pytest.mark.parametrize("action", ["ACCEPT", "REJECT"])
def test_exact_replay_and_conflicts(configured, action):
    artifact = pending(configured, action)
    first = resolver.resolve_production(artifact)
    before = snapshot(configured)
    sha = sha256_file(configured)
    second = resolver.resolve_production(deepcopy(artifact))
    assert second["result"] == first["result"]
    assert second["resolved"] is False and second["idempotent"] is True and second["backup_location"] == ""
    assert resolver.preview_resolution(artifact)["idempotent"] is True
    assert snapshot(configured) == before and sha256_file(configured) == sha
    for key, value in (("reason", "Different final reason"), ("action", "REJECT" if action == "ACCEPT" else "ACCEPT")):
        changed = deepcopy(artifact)
        changed[key] = value
        blocked(configured, changed, "PROPOSAL_RESOLUTION_CONFLICT")


@pytest.mark.parametrize("field,value", [("reason", " "), ("action", "MODIFY"), ("document_type", "other"),
    ("schema_version", 1), ("status", "DRAFT"), ("proposal_snapshot", []), ("proposal_id", "")])
def test_artifact_shape_rejections(configured, field, value):
    artifact = pending(configured)
    artifact[field] = value
    blocked(configured, artifact, "INVALID_ARTIFACT")


@pytest.mark.parametrize("field", ["created_at", "target_node_id", "payload", "proposal_id", "proposal_type"])
def test_exact_snapshot_rejections(configured, field):
    artifact = pending(configured)
    if field == "proposal_id":
        artifact[field] = "PROP_MISSING"
    elif field == "payload":
        artifact["proposal_snapshot"][field]["proposed_current_view"]["recent_change"] = "tampered"
    else:
        artifact["proposal_snapshot"][field] = "changed"
    code = "PROPOSAL_NOT_FOUND" if field == "proposal_id" else "INVALID_ARTIFACT" if field == "proposal_type" else "RESOLUTION_ARTIFACT_STALE"
    blocked(configured, artifact, code)


@pytest.mark.parametrize("change,code", [
    ("view", "STALE_TARGET_VIEW"), ("version", "STALE_TARGET_VIEW"),
    ("added", "CANDIDATE_EVIDENCE_CHANGED"), ("removed", "CANDIDATE_EVIDENCE_CHANGED"),
    ("role", "CANDIDATE_EVIDENCE_CHANGED"), ("ineligible", "EVIDENCE_INELIGIBLE"),
    ("inactive", "NODE_NOT_ACTIVE"), ("identity", "NODE_IDENTITY_CHANGED"),
    ("source", "SOURCE_NOT_FOUND"), ("frozen", "FROZEN_CURRENT_VIEW_VALIDATION_FAILED"),
    ("no_change", "CHANGE_DECISION_WITHOUT_VIEW_CHANGE"),
])
def test_accept_revalidates_and_reject_still_works(configured, change, code):
    artifact = pending(configured)
    payload = artifact["proposal_snapshot"]["payload"]
    node = payload["node_id"]
    primary = payload["evidence_claim_ids"][0]
    db = Database(configured)
    if change in {"view", "version"}:
        db.execute(f"UPDATE current_views SET {'view_id' if change == 'view' else 'version'}='CHANGED' WHERE node_id=?", (node,))
    elif change == "added":
        db.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) VALUES('CLM_EXTRA','extra','fact','2026',?,'2026')", (payload["trigger_source_id"],))
        db.execute("INSERT INTO claim_node_links VALUES('CLM_EXTRA',?,'subject')", (node,))
    elif change == "removed":
        db.execute("DELETE FROM claim_node_links WHERE claim_id=? AND node_id=?", (primary, node))
    elif change == "role":
        db.execute("UPDATE claim_node_links SET role='context' WHERE claim_id=? AND node_id=?", (primary, node))
    elif change == "ineligible":
        db.execute("UPDATE claims SET status='needs_review' WHERE claim_id=?", (primary,))
    elif change in {"inactive", "identity"}:
        db.execute(f"UPDATE nodes SET {'status' if change == 'inactive' else 'canonical_name'}=? WHERE node_id=?",
                   ("inactive" if change == "inactive" else "Changed", node))
    elif change == "source":
        db.execute("DELETE FROM sources WHERE source_id=?", (payload["trigger_source_id"],))
    else:
        if change == "frozen":
            payload["proposed_current_view"]["core_logic"] = ["MLCC without required citation"]
        else:
            payload["proposed_current_view"] = json.loads(db.current_view(node)["content_json"])
        # Corrupted pending fixture must still be revalidated despite matching snapshot.
        db.execute("UPDATE proposals SET payload_json=? WHERE proposal_id=?", (json.dumps(payload), artifact["proposal_id"]))
    blocked(configured, artifact, code)
    before = snapshot(configured)
    artifact["action"] = "REJECT"
    result = resolver.resolve_production(artifact)
    assert result["status"] == "rejected" and result["new_view_id"] == ""
    after = snapshot(configured)
    assert {k:v for k,v in before.items() if k != "proposals"} == {k:v for k,v in after.items() if k != "proposals"}


@pytest.mark.parametrize("field,value", [("proposal_type", "new_node"), ("source_impact_id", "IMPACT_1"),
    ("propagation_batch_id", "BATCH_1"), ("payload_json", "malformed"), ("payload_json", "{}")])
def test_legacy_or_malformed_never_resolved(configured, field, value):
    artifact = pending(configured, "REJECT")
    Database(configured).execute(f"UPDATE proposals SET {field}=? WHERE proposal_id=?", (value, artifact["proposal_id"]))
    blocked(configured, artifact, "NOT_HUMAN_VIEW_PROPOSAL")


def test_same_day_revision_uses_existing_helper(configured, monkeypatch):
    class FrozenDate(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 8, 28)
    monkeypatch.setattr(current_view, "datetime", FrozenDate)
    db = Database(configured)
    db.execute("UPDATE current_views SET version='v_20260828',revision_seq=0")
    first = pending(configured)
    accepted = resolver.resolve_production(first)
    assert accepted["new_version"] == "v_20260828_01"
    second = pending(configured)
    accepted2 = resolver.resolve_production(second)
    assert accepted2["new_version"] == "v_20260828_02"
    assert accepted2["previous_view_id"] == accepted["new_view_id"]


@pytest.mark.parametrize("action", ["ACCEPT", "REJECT"])
def test_concurrent_exact_resolution(configured, action):
    artifact = pending(configured, action)
    barrier = Barrier(2)
    def run():
        barrier.wait()
        return resolver.resolve_production(deepcopy(artifact))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(r["resolved"] for r in results) == [False, True]
    assert results[0]["result"] == results[1]["result"]


@pytest.mark.parametrize("phase", ["backup", "after_view", "after_update", "receipt"])
def test_failure_transaction_and_postcommit_reporting(configured, monkeypatch, phase):
    artifact = pending(configured)
    before = snapshot(configured)
    if phase == "backup":
        monkeypatch.setattr(resolver, "_backup", lambda *args: (_ for _ in ()).throw(OSError("backup failed")))
    elif phase == "after_view":
        original = resolver.create_official_view_record
        def failed(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("injected after View")
        monkeypatch.setattr(resolver, "create_official_view_record", failed)
    elif phase == "after_update":
        original = resolver._persist
        def failed(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("injected after update")
        monkeypatch.setattr(resolver, "_persist", failed)
    else:
        monkeypatch.setattr(resolver, "write_json", lambda *args: (_ for _ in ()).throw(OSError("receipt failed")))
    with pytest.raises((OSError, HumanReviewIntakeError)) as error:
        resolver.resolve_production(artifact)
    if phase == "receipt":
        assert "RESOLUTION_COMMITTED_RECEIPT_FAILED" in str(error.value)
        assert artifact["proposal_id"] in str(error.value) and "ACCEPT" in str(error.value) and "backup=" in str(error.value)
        assert Database(configured).proposal(artifact["proposal_id"])["status"] == "accepted"
    else:
        assert snapshot(configured) == before


FORBIDDEN_TABLES = ["side_effect_jobs", "impact_reviews", "impact_attempt_audit", "nodes", "node_aliases", "claims",
                    "claim_node_links", "sources", "source_node_links", "node_relations", "relation_evidence_links",
                    "research_questions", "knowledge_gaps", "ima_objects", "processing_jobs"]


@pytest.mark.parametrize("accept", [True, False])
@pytest.mark.parametrize("table", FORBIDDEN_TABLES)
def test_authorizer_other_tables(accept, table):
    with sqlite3.connect(":memory:") as conn:
        conn.execute(f'CREATE TABLE "{table}"(value TEXT)')
        conn.set_authorizer(resolver.resolution_write_authorizer(accept))
        for sql in (f'INSERT INTO "{table}" VALUES(NULL)', f'UPDATE "{table}" SET value=NULL', f'DELETE FROM "{table}"'):
            with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
                conn.execute(sql)


@pytest.mark.parametrize("accept", [True, False])
def test_authorizer_protects_payload_reason_views_and_schema(accept):
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE proposals(status TEXT,result_json TEXT,resolved_at TEXT,payload_json TEXT,reason TEXT)")
        conn.execute("CREATE TABLE current_views(value TEXT)")
        conn.set_authorizer(resolver.resolution_write_authorizer(accept))
        conn.execute("UPDATE proposals SET status='rejected',result_json='{}',resolved_at='now'")
        for sql in ("UPDATE proposals SET payload_json='{}'", "UPDATE proposals SET reason='overwrite'",
                    "INSERT INTO proposals DEFAULT VALUES", "DELETE FROM proposals", "UPDATE current_views SET value=NULL",
                    "DELETE FROM current_views", "CREATE TABLE forbidden(x)", "PRAGMA user_version=2", "ATTACH ':memory:' AS other"):
            with pytest.raises(sqlite3.DatabaseError):
                conn.execute(sql)
        if accept:
            conn.execute("INSERT INTO current_views VALUES(NULL)")
        else:
            with pytest.raises(sqlite3.DatabaseError):
                conn.execute("INSERT INTO current_views VALUES(NULL)")


def test_trigger_write_is_blocked_and_rolls_back(configured):
    artifact = pending(configured)
    Database(configured).execute("CREATE TRIGGER bad AFTER INSERT ON current_views BEGIN UPDATE nodes SET status='inactive'; END")
    before = snapshot(configured)
    with pytest.raises(sqlite3.DatabaseError):
        resolver.resolve_production(artifact)
    assert snapshot(configured) == before


def test_read_api_terminal_history_and_no_write_routes(configured):
    client = TestClient(create_app(configured))
    artifact = pending(configured)
    accepted = resolver.resolve_production(artifact)
    reject = pending(configured, "REJECT")
    resolver.resolve_production(reject)
    sha = sha256_file(configured)
    assert client.get("/api/view-proposals").json() == []
    for status, art in (("accepted", artifact), ("rejected", reject)):
        rows = client.get(f"/api/view-proposals?status={status}").json()
        assert len(rows) == 1 and rows[0]["proposal_id"] == art["proposal_id"]
        detail = client.get("/api/view-proposals/" + art["proposal_id"]).json()
        assert detail["resolution"]["reason"] == art["reason"]
        assert detail["resolution"]["action"] == art["action"]
        assert detail["proposal_snapshot"] == art["proposal_snapshot"]
        assert "path" not in detail["resolution"]
    detail = client.get("/api/view-proposals/" + artifact["proposal_id"]).json()
    assert detail["resolution"]["view_id"] == accepted["new_view_id"]
    assert detail["canonical_alignment"] == "STALE_TARGET_VIEW"  # original BASE is now historical
    assert detail["diff"]["has_changes"] is True
    assert client.get("/api/view-proposals?status=all").status_code == 422
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert client.request(method, "/api/view-proposals/" + artifact["proposal_id"]).status_code == 405
    assert sha256_file(configured) == sha

    # Invalid terminal provenance must not appear as auditable resolution history.
    db = Database(configured)
    db.execute("UPDATE current_views SET accepted_proposal_id='' WHERE view_id=?", (accepted["new_view_id"],))
    assert client.get("/api/view-proposals?status=accepted").json() == []
    assert client.get("/api/view-proposals/" + artifact["proposal_id"]).status_code == 404
    with pytest.raises(HumanReviewIntakeError, match="PROPOSAL_RESOLUTION_CONFLICT"):
        resolver.preview_resolution(artifact)
    db.execute("UPDATE proposals SET result_json='{}' WHERE proposal_id=?", (reject["proposal_id"],))
    assert client.get("/api/view-proposals?status=rejected").json() == []
    assert client.get("/api/view-proposals/" + reject["proposal_id"]).status_code == 404


def test_isolated_guard_and_cli_intent(configured, monkeypatch, capsys):
    artifact = pending(configured, "REJECT")
    with pytest.raises(HumanReviewIntakeError, match="PRODUCTION_WRITE_NOT_AUTHORIZED"):
        resolver.resolve_isolated(configured, artifact)
    other = configured.parent / "isolated.db"
    shutil.copyfile(configured, other)
    assert resolver.resolve_isolated(other, artifact)["status"] == "rejected"
    file = configured.parent / "resolution.json"
    file.write_text(json.dumps(artifact), encoding="utf-8")
    sha = sha256_file(configured)
    assert main(["preview", "--resolution", str(file)]) == 0
    assert sha256_file(configured) == sha
    assert main(["apply-production", "--resolution", str(file)]) == 0
    assert Database(configured).proposal(artifact["proposal_id"])["status"] == "rejected"
    with pytest.raises(SystemExit):
        main(["--resolution", str(file)])
    with pytest.raises(SystemExit):
        main(["apply-production", "--resolution", str(file), "--db", str(other)])
    file.write_text('{"action":"ACCEPT","action":"REJECT"}', encoding="utf-8")
    with pytest.raises(HumanReviewIntakeError, match="INVALID_JSON"):
        read_artifact(file)
