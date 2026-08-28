from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import pro_a.production_proposal_gateway as gateway
from pro_a.api import create_app
from pro_a.db import Database
from pro_a.human_review_intake import HumanReviewIntakeError, prepare_review
from pro_a.query import ReadOnlyQuery
from pro_a.storage import sha256_file
from scripts.phase2_7b_proposal_gateway import main
from test_human_review_intake import (
    MLCC_NODE_ID, SOURCE, YUNZHONG_NODE_ID, db_path, edited_draft,
    prohibit_downstream, review_for, snapshot,
)


@pytest.fixture(autouse=True)
def configured_copy(db_path, monkeypatch):
    # Only this isolated fixture is configured as canonical for gateway correctness tests.
    monkeypatch.setattr(gateway, "load_config", lambda: SimpleNamespace(db_path=db_path, root=db_path.parent))


def assert_blocked(db_path, draft, code):
    before = snapshot(db_path)
    with pytest.raises(HumanReviewIntakeError, match=code):
        gateway.apply_production(draft)
    assert snapshot(db_path) == before


@pytest.mark.parametrize("decision", ["minor", "material", "thesis"])
def test_pending_only_backup_receipt_and_all_other_tables_preserved(db_path, decision):
    draft = edited_draft(db_path, decision)
    before = snapshot(db_path)
    sha = sha256_file(db_path)
    result = gateway.apply_production(draft)
    after = snapshot(db_path)
    assert result["created"] is True and result["status"] == "pending"
    assert len(after["proposals"]) == len(before["proposals"]) + 1
    assert {k: v for k, v in after.items() if k != "proposals"} == {k: v for k, v in before.items() if k != "proposals"}
    for table in ("current_views", "nodes", "claims", "claim_node_links", "sources", "node_relations",
                  "relation_evidence_links", "impact_reviews", "impact_attempt_audit", "side_effect_jobs",
                  "research_questions", "knowledge_gaps"):
        assert after[table] == before[table]
    row = Database(db_path).proposal(result["proposal_id"])
    assert row["payload"] == draft["payload"]
    assert row["propagation_batch_id"] == row["source_impact_id"] == row["resolved_at"] == ""
    assert row["result_json"] == "{}" and row["status"] == "pending"
    assert snapshot(result["backup_location"]) == before
    assert result["pre_write_sha256"] == sha
    assert result["post_write_sha256"] == sha256_file(db_path)
    assert result["integrity_check"] == "ok" and result["foreign_key_check"] == []
    assert result["production_db_path"] == str(db_path.resolve())
    assert result["decision"] == decision and result["evidence_claim_ids"] == draft["payload"]["evidence_claim_ids"]
    assert result["target_view_id"] == draft["payload"]["previous_view_id"]
    assert result["target_view_version"] == draft["payload"]["previous_version"]
    with open(result["receipt_path"], encoding="utf-8") as stream:
        assert json.load(stream) == result


def test_no_change_is_no_proposal(db_path):
    receipt = prepare_review(db_path, review_for(db_path, "no_change"))
    before = snapshot(db_path)
    for action in (gateway.preview_production, gateway.apply_production):
        assert action(receipt) == {"status": "INTAKE_VALID", "action": "NO_PROPOSAL", "created": False}
    assert snapshot(db_path) == before
    assert not (db_path.parent / "backups").exists()


def test_preview_is_read_only_and_not_authority(db_path):
    draft = edited_draft(db_path)
    before = sha256_file(db_path)
    result = gateway.preview_production(draft)
    assert result["would_create"] is True and result["status"] == "PREVIEW_VALID"
    assert sha256_file(db_path) == before
    assert not (db_path.parent / "generated").exists()
    assert not (db_path.parent / "backups").exists()
    Database(db_path).execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (MLCC_NODE_ID,))
    assert_blocked(db_path, draft, "NODE_NOT_ACTIVE")


@pytest.mark.parametrize("mutation,code", [
    ("artifact", "DRAFT_ENVELOPE_CHANGED"), ("non_ready", "INVALID_ARTIFACT"),
    ("node_missing", "NODE_NOT_FOUND"), ("node_inactive", "NODE_NOT_ACTIVE"),
    ("node_name", "NODE_IDENTITY_CHANGED"), ("node_type", "NODE_IDENTITY_CHANGED"),
    ("source_missing", "SOURCE_NOT_FOUND"), ("view_id", "STALE_TARGET_VIEW"),
    ("view_version", "STALE_TARGET_VIEW"), ("claim_added", "CANDIDATE_EVIDENCE_CHANGED"),
    ("claim_removed", "CANDIDATE_EVIDENCE_CHANGED"), ("role_changed", "CANDIDATE_EVIDENCE_CHANGED"),
    ("context_primary", "INELIGIBLE_EVIDENCE"), ("related_primary", "INELIGIBLE_EVIDENCE"),
    ("needs_review", "INELIGIBLE_EVIDENCE"), ("terminal", "INELIGIBLE_EVIDENCE"),
    ("unknown_status", "INELIGIBLE_EVIDENCE"), ("no_edit", "CHANGE_DECISION_WITHOUT_VIEW_CHANGE"),
    ("metadata_only", "CHANGE_DECISION_WITHOUT_VIEW_CHANGE"), ("quality", "FROZEN_CURRENT_VIEW_VALIDATION_FAILED"),
    ("legacy_id", "DRAFT_ENVELOPE_CHANGED"), ("wrong_type", "DRAFT_ENVELOPE_CHANGED"),
])
def test_gateway_reuses_frozen_stale_and_content_gates(db_path, mutation, code):
    draft = edited_draft(db_path, node_id=YUNZHONG_NODE_ID if mutation == "related_primary" else MLCC_NODE_ID)
    payload = draft["payload"]
    review = payload["human_review_handoff"]
    primary = review["selected_primary_claim_ids"][0]
    db = Database(db_path)
    if mutation == "artifact":
        draft["document_type"] = "arbitrary_payload"
    elif mutation == "non_ready":
        review["status"] = "DRAFT"
    elif mutation == "node_missing":
        db.execute("DELETE FROM nodes WHERE node_id=?", (review["node_id"],))
    elif mutation in {"node_inactive", "node_name", "node_type"}:
        column, value = {"node_inactive": ("status", "inactive"), "node_name": ("canonical_name", "renamed"),
                         "node_type": ("primary_type", "Company")}[mutation]
        db.execute(f"UPDATE nodes SET {column}=? WHERE node_id=?", (value, review["node_id"]))
    elif mutation == "source_missing":
        db.execute("DELETE FROM sources WHERE source_id=?", (SOURCE,))
    elif mutation in {"view_id", "view_version"}:
        db.execute(f"UPDATE current_views SET {'view_id' if mutation == 'view_id' else 'version'}='changed' WHERE node_id=?",
                   (review["node_id"],))
    elif mutation == "claim_added":
        db.execute("""INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at)
                      VALUES('CLM_EXTRA','Extra','fact','2026',?,'2026')""", (SOURCE,))
        db.execute("INSERT INTO claim_node_links VALUES('CLM_EXTRA',?,'subject')", (review["node_id"],))
    elif mutation == "claim_removed":
        db.execute("DELETE FROM claims WHERE claim_id=?", (primary,))
    elif mutation == "role_changed":
        db.execute("UPDATE claim_node_links SET role='context' WHERE claim_id=? AND node_id=?", (primary, review["node_id"]))
    elif mutation in {"context_primary", "related_primary"}:
        role = mutation.split("_")[0]
        review["selected_primary_claim_ids"] = [next(c["claim_id"] for c in review["candidate_claims"] if c["role"] == role)]
    elif mutation in {"needs_review", "terminal", "unknown_status"}:
        status = {"needs_review": "needs_review", "terminal": "expired", "unknown_status": "future_status"}[mutation]
        db.execute("UPDATE claims SET status=? WHERE claim_id=?", (status, primary))
    elif mutation in {"no_edit", "metadata_only"}:
        draft = prepare_review(db_path, review)
        if mutation == "metadata_only":
            draft["payload"]["proposed_current_view"]["recent_change"] = "Metadata only"
    elif mutation == "quality":
        payload["proposed_current_view"]["core_logic"] = ["MLCC without any Claim citation"]
    elif mutation == "legacy_id":
        draft["source_impact_id"] = "IMPACT_UNAUTHORIZED"
    else:
        draft["proposal_type"] = "new_node"
    assert_blocked(db_path, draft, code)


def test_idempotency_conflict_and_immutable_pending(db_path):
    draft = edited_draft(db_path)
    first = gateway.apply_production(draft)
    before = snapshot(db_path)
    sha = sha256_file(db_path)
    second = gateway.apply_production(deepcopy(draft))
    assert second["proposal_id"] == first["proposal_id"] and second["created"] is False
    assert second["backup_location"] == ""
    assert sha256_file(db_path) == sha and snapshot(db_path) == before
    assert gateway.preview_production(draft)["would_create"] is False
    draft["payload"]["proposed_current_view"]["knowledge_gaps"].append("缺少MLCC后续验证。")
    assert_blocked(db_path, draft, "PENDING_PROPOSAL_CONFLICT")


def test_two_concurrent_exact_gateway_submissions(db_path):
    draft = edited_draft(db_path)
    barrier = Barrier(2)
    def submit():
        barrier.wait()
        return gateway.apply_production(deepcopy(draft))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert len({r["proposal_id"] for r in results}) == 1
    assert sum(r["created"] for r in results) == 1
    assert len(snapshot(db_path)["proposals"]) == 1


@pytest.mark.parametrize("phase", ["before", "during"])
def test_injected_failures_roll_back(db_path, monkeypatch, phase):
    draft = edited_draft(db_path)
    original = Database.add_proposal
    def fail(*args, **kwargs):
        if phase == "during":
            original(*args, **kwargs)
        raise RuntimeError("injected failure")
    monkeypatch.setattr(Database, "add_proposal", fail)
    before = snapshot(db_path)
    with pytest.raises(RuntimeError, match="injected"):
        gateway.apply_production(draft)
    assert snapshot(db_path) == before


@pytest.mark.parametrize("table", [
    "proposals", "current_views", "nodes", "node_aliases", "claims", "claim_node_links", "sources",
    "node_relations", "relation_evidence_links", "impact_reviews", "impact_attempt_audit", "side_effect_jobs",
    "research_questions", "knowledge_gaps",
])
@pytest.mark.parametrize("verb", ["INSERT", "UPDATE", "DELETE"])
def test_write_authorizer_denies_every_noninsert_proposal_write(db_path, table, verb):
    if table == "proposals" and verb == "INSERT":
        assert gateway.apply_production(edited_draft(db_path))["created"] is True
        return
    with Database(db_path).transaction(immediate=True) as conn:
        column = conn.execute(f'PRAGMA table_info("{table}")').fetchone()[1]
        conn.set_authorizer(gateway.proposal_write_authorizer)
        sql = {"INSERT": f'INSERT INTO "{table}" DEFAULT VALUES',
               "UPDATE": f'UPDATE "{table}" SET "{column}"="{column}"', "DELETE": f'DELETE FROM "{table}"'}[verb]
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            conn.execute(sql)


def test_trigger_side_effect_is_denied_and_rolls_back(db_path):
    Database(db_path).execute("""CREATE TRIGGER bad_effect AFTER INSERT ON proposals
                                 BEGIN UPDATE nodes SET description='forbidden'; END""")
    before = snapshot(db_path)
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        gateway.apply_production(edited_draft(db_path))
    assert snapshot(db_path) == before


@pytest.mark.parametrize("sql", ["PRAGMA user_version=99", "CREATE TABLE forbidden(x)",
                                 "ATTACH DATABASE ':memory:' AS extra", "DROP TABLE proposals"])
def test_guard_denies_schema_and_connection_write_escape(db_path, sql):
    with Database(db_path).transaction(immediate=True) as conn:
        conn.set_authorizer(gateway.proposal_write_authorizer)
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            conn.execute(sql)


def test_backup_failure_prevents_insert(db_path, monkeypatch):
    def fail(*args):
        raise OSError("backup failed")
    monkeypatch.setattr(gateway, "_backup", fail)
    before = snapshot(db_path)
    with pytest.raises(OSError, match="backup failed"):
        gateway.apply_production(edited_draft(db_path))
    assert snapshot(db_path) == before


def test_receipt_failure_does_not_falsely_report_rollback(db_path, monkeypatch):
    def fail(*args):
        raise OSError("receipt failed")
    monkeypatch.setattr(gateway, "write_json", fail)
    with pytest.raises(HumanReviewIntakeError, match="PROPOSAL_COMMITTED_RECEIPT_FAILED"):
        gateway.apply_production(edited_draft(db_path))
    assert len(snapshot(db_path)["proposals"]) == 1
    assert Database(db_path).one("SELECT status FROM proposals")["status"] == "pending"


def test_config_only_cli_has_no_db_override_or_default_write(db_path, tmp_path, capsys):
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(edited_draft(db_path)), encoding="utf-8")
    assert main(["preview", "--draft", str(path)]) == 0
    assert not snapshot(db_path)["proposals"]
    with pytest.raises(SystemExit):
        main(["--draft", str(path)])
    with pytest.raises(SystemExit):
        main(["apply-production", "--db", str(db_path), "--draft", str(path)])
    assert main(["apply-production", "--draft", str(path)]) == 0
    assert len(snapshot(db_path)["proposals"]) == 1


def test_read_queue_empty_and_legacy_payloads_excluded(db_path):
    db = Database(db_path)
    for payload in ({}, {"human_review_handoff": {}}, [], "bad"):
        db.add_proposal("current_view_change", payload, target_node_id=MLCC_NODE_ID)
    db.execute("UPDATE proposals SET payload_json='{' WHERE proposal_id=(SELECT MIN(proposal_id) FROM proposals)")
    db.add_proposal("new_node", edited_draft(db_path)["payload"], target_node_id=MLCC_NODE_ID)
    before = sha256_file(db_path)
    query = ReadOnlyQuery(db_path)
    assert query.list_view_proposals() == []
    assert query.view_proposal_detail("missing") is None
    for row in db.all("SELECT proposal_id FROM proposals"):
        assert query.view_proposal_detail(row["proposal_id"]) is None
    assert sha256_file(db_path) == before


def test_read_list_stable_order_and_pagination(db_path):
    ids = []
    for decision in ("minor", "material", "thesis"):
        ids.append(gateway.apply_production(edited_draft(db_path, decision))["proposal_id"])
    Database(db_path).execute("UPDATE proposals SET created_at='2026-08-28'")
    query = ReadOnlyQuery(db_path)
    assert [r["proposal_id"] for r in query.list_view_proposals()] == sorted(ids, reverse=True)
    assert query.list_view_proposals(limit=1, offset=1)[0]["proposal_id"] == sorted(ids, reverse=True)[1]
    Database(db_path).add_proposal("current_view_change", {}, target_node_id=MLCC_NODE_ID)
    assert len(query.list_view_proposals()) == 3


def test_detail_metadata_evidence_diff_and_read_only_api(db_path):
    draft = edited_draft(db_path, "thesis")
    proposal_id = gateway.apply_production(draft)["proposal_id"]
    before = sha256_file(db_path)
    client = TestClient(create_app(db_path))
    row = client.get("/api/view-proposals").json()[0]
    assert row["node_name"] == "MLCC" and row["node_type"] == "Product"
    assert row["human_review_origin"] is True and row["status"] == "pending"
    detail = client.get(f"/api/view-proposals/{proposal_id}").json()
    assert detail["canonical_alignment"] == "CURRENT"
    assert detail["reason"] == draft["payload"]["human_review_handoff"]["reason"]
    assert detail["thesis_break"] == draft["payload"]["human_review_handoff"]["thesis_break"]
    assert len(detail["primary_evidence"]) == 3 and len(detail["context_evidence"]) == 8
    assert all(c["role"] == "subject" for c in detail["primary_evidence"])
    assert all(c["role"] == "context" for c in detail["context_evidence"])
    assert detail["diff"]["list_changes"]["knowledge_gaps"]["added"] == [draft["payload"]["proposed_current_view"]["knowledge_gaps"][-1]]
    assert "target" not in detail["diff"]  # No fake official target record.
    assert detail["trigger_source"]["source_id"] == SOURCE
    assert "archived_path" not in json.dumps(detail)
    assert "production_db_path" not in json.dumps(detail)
    assert client.get("/api/view-proposals/missing").status_code == 404
    for method, url in (("POST", "/api/view-proposals"), ("PUT", f"/api/view-proposals/{proposal_id}"),
                        ("POST", f"/api/view-proposals/{proposal_id}/accept"), ("POST", f"/api/view-proposals/{proposal_id}/reject")):
        assert client.request(method, url, json={}).status_code in {404, 405}
    assert sha256_file(db_path) == before


@pytest.mark.parametrize("mutation,alignment", [
    ("view", "STALE_TARGET_VIEW"), ("candidate", "CANDIDATE_EVIDENCE_CHANGED"),
    ("eligibility", "EVIDENCE_INELIGIBLE"), ("node", "NODE_NOT_ACTIVE"), ("source", "SOURCE_NOT_FOUND"),
])
def test_read_time_alignment_never_updates_pending_status(db_path, mutation, alignment):
    draft = edited_draft(db_path)
    proposal_id = gateway.apply_production(draft)["proposal_id"]
    db = Database(db_path)
    if mutation == "view":
        original = db.one("SELECT * FROM current_views WHERE node_id=?", (MLCC_NODE_ID,))
        original.update(view_id="VIEW_NEW", version="v_new", revision_seq=99)
        db.execute(f"INSERT INTO current_views({','.join(original)}) VALUES({','.join('?' for _ in original)})", tuple(original.values()))
    elif mutation == "candidate":
        db.execute("DELETE FROM claim_node_links WHERE node_id=? AND role='context'", (MLCC_NODE_ID,))
    elif mutation == "eligibility":
        db.execute("UPDATE claims SET status='invalidated' WHERE claim_id=?", (draft["payload"]["evidence_claim_ids"][0],))
    elif mutation == "node":
        db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (MLCC_NODE_ID,))
    else:
        db.execute("DELETE FROM sources WHERE source_id=?", (SOURCE,))
    before = sha256_file(db_path)
    detail = ReadOnlyQuery(db_path).view_proposal_detail(proposal_id)
    assert detail["canonical_alignment"] == alignment and detail["status"] == "pending"
    assert db.proposal(proposal_id)["status"] == "pending"
    if mutation == "view":
        assert detail["target_official_view"]["view_id"] == draft["payload"]["previous_view_id"]
        assert detail["diff"]["has_changes"] is True
    assert sha256_file(db_path) == before
