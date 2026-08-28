from __future__ import annotations

import json
import os
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from threading import Barrier
from types import SimpleNamespace

import pytest

import pro_a.current_view as current_view
import pro_a.human_review_intake as intake
from pro_a.current_view_pilot import (
    MLCC_NODE_ID, YUNZHONG_NODE_ID, _mlcc_draft, _yunzhong_draft, file_sha256,
)
from pro_a.db import Database
from pro_a.ima import IMAClient
from pro_a.impact_recovery import ImpactRecoveryService
from pro_a.llm import ChatLLM
from pro_a.propagation import PropagationManager
from pro_a.proposals import ProposalManager
from pro_a.query import ReadOnlyQuery
from scripts.intake_phase2_7a import main
from test_current_view_pilot import _fixture as pilot_fixture


SOURCE = "SRC_20260814_F6E1EFAD"


def forbidden(*args, **kwargs):
    pytest.fail("intake invoked a forbidden execution/side-effect boundary")


@pytest.fixture(autouse=True)
def prohibit_downstream(monkeypatch):
    for cls in (PropagationManager, ImpactRecoveryService, ProposalManager, IMAClient, ChatLLM):
        monkeypatch.setattr(cls, "__init__", forbidden)
    for name in (
        "evaluate_node", "run_batch", "resume_batch", "start_from_accepted_view",
        "enqueue_from_accepted_view", "_evaluate_impact_row", "_create_gap", "_create_rq_candidate",
        "_create_current_view_proposal", "_programmatic_evidence_sufficiency", "_evidence_profile",
    ):
        monkeypatch.setattr(PropagationManager, name, forbidden)
    monkeypatch.setattr(ProposalManager, "accept", forbidden)
    monkeypatch.setattr(current_view, "create_official_view_record", forbidden)
    monkeypatch.setattr(current_view, "create_official_view", forbidden)
    monkeypatch.setattr(current_view, "write_official_view_file", forbidden)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = pilot_fixture(tmp_path)
    db = Database(path)
    for node_id, content in ((MLCC_NODE_ID, _mlcc_draft()[0]), (YUNZHONG_NODE_ID, _yunzhong_draft()[0])):
        db.execute(
            """INSERT INTO current_views(view_id,node_id,version,change_level,content_md,content_json,
               trigger_source_id,trigger_claim_ids_json,revision_date,revision_seq,created_at)
               VALUES(?,?,?,'initial','fixture',?,?,?,'20260828',1,'2026-08-28')""",
            ("VIEW_" + node_id, node_id, "v_20260828_01", json.dumps(content, ensure_ascii=False),
             SOURCE, json.dumps(content["evidence_claim_ids"])),
        )
    db.execute("INSERT INTO claim_node_links VALUES(?,?,'related')",
               ("CLM_20260814_980FA010", YUNZHONG_NODE_ID))
    protected = tmp_path / "protected-production.db"
    shutil.copyfile(path, protected)
    monkeypatch.setattr(intake, "load_config", lambda: SimpleNamespace(db_path=protected))
    return path


def review_for(path, decision="minor", node_id=MLCC_NODE_ID):
    query = ReadOnlyQuery(path)
    source = query.source_detail(SOURCE)
    candidate = next(c for c in query.source_impact_candidates(SOURCE)["candidates"]
                     if c["node"]["node_id"] == node_id)
    return {
        "document_type": "human_impact_review", "schema_version": "1", "status": "READY",
        "source": {key: source[key] for key in intake.SOURCE_FIELDS},
        "source_id": SOURCE, "node_id": node_id, "node_name": candidate["node"]["canonical_name"],
        "node_type": candidate["node"]["primary_type"],
        "target_view_id": candidate["current_view"]["view_id"],
        "target_view_version": candidate["current_view"]["version"],
        "decision": decision, "reason": "Explicit isolated fixture human review; not Production authorization.",
        "selected_primary_claim_ids": [c["claim_id"] for c in candidate["claims"]
                                       if c["role"] == "subject" and c["status"] == "current"],
        "selected_context_claim_ids": [c["claim_id"] for c in candidate["claims"] if c["role"] == "context"],
        "candidate_claims": [{"claim_id": c["claim_id"], "role": c["role"]} for c in candidate["claims"]],
        "thesis_break": {key: "Explicit human thesis reason" if decision == "thesis" else ""
                         for key in intake.THESIS_FIELDS},
        "evidence_sufficiency": "NOT_EVALUATED",
    }


def edited_draft(path, decision="minor", node_id=MLCC_NODE_ID):
    draft = intake.prepare_review(path, review_for(path, decision, node_id))
    draft["payload"]["proposed_current_view"]["knowledge_gaps"].append(
        f"缺少{draft['payload']['human_review_handoff']['node_name']}后续独立验证证据。")
    return draft


def snapshot(path):
    with sqlite3.connect(path) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {name: conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall() for name in tables}


def blocked(path, draft, code):
    before = snapshot(path)
    with pytest.raises(intake.HumanReviewIntakeError, match=code):
        intake.submit_review(path, draft, isolated=True)
    assert snapshot(path) == before


def test_no_change_is_valid_read_only_noop(db_path):
    review = review_for(db_path, "no_change")
    review["selected_primary_claim_ids"] = []
    sha = file_sha256(db_path)
    receipt = intake.prepare_review(db_path, review)
    assert receipt["status"] == "INTAKE_VALID"
    assert receipt["action"] == "NO_PROPOSAL"
    assert receipt["canonical"] is False
    assert receipt["human_review_handoff"] == review
    blocked(db_path, receipt, "INVALID_ARTIFACT")
    assert file_sha256(db_path) == sha


def test_prepare_copies_exact_target_without_rewrite_or_persistence(db_path):
    review = review_for(db_path)
    before = snapshot(db_path)
    sha = file_sha256(db_path)
    draft = intake.prepare_review(db_path, review)
    assert draft["labels"] == intake.LABELS
    payload = draft["payload"]
    assert payload["proposed_current_view"] == _mlcc_draft()[0]
    assert payload["human_review_handoff"] == review
    assert payload["previous_view_id"] == review["target_view_id"]
    assert payload["previous_version"] == review["target_view_version"]
    assert payload["change_level"] == "minor"
    assert payload["trigger_source_id"] == SOURCE
    assert snapshot(db_path) == before
    assert file_sha256(db_path) == sha
    blocked(db_path, draft, "CHANGE_DECISION_WITHOUT_VIEW_CHANGE")


@pytest.mark.parametrize("decision", ["minor", "material", "thesis"])
@pytest.mark.parametrize("node_id", [MLCC_NODE_ID, YUNZHONG_NODE_ID])
def test_only_pending_proposal_changes_and_handoff_retained(db_path, decision, node_id):
    draft = edited_draft(db_path, decision, node_id)
    before = snapshot(db_path)
    result = intake.submit_review(db_path, draft, isolated=True)
    assert result["created"] is True and result["status"] == "pending"
    row = Database(db_path).proposal(result["proposal_id"])
    assert row["proposal_type"] == "current_view_change" and row["status"] == "pending"
    assert row["payload"] == draft["payload"]
    assert row["payload"]["change_level"] == decision
    assert row["propagation_batch_id"] == row["source_impact_id"] == ""
    assert row["reason"] == draft["payload"]["human_review_handoff"]["reason"]
    if decision == "thesis":
        assert all(row["payload"]["human_review_handoff"]["thesis_break"].values())
    after = snapshot(db_path)
    assert len(after["proposals"]) == len(before["proposals"]) + 1
    assert {k: v for k, v in after.items() if k != "proposals"} == {
        k: v for k, v in before.items() if k != "proposals"}


@pytest.mark.parametrize("key,value", [
    ("document_type", "other"), ("schema_version", 1), ("schema_version", "2"),
    ("status", "DRAFT"), ("status", "STALE"), ("decision", "MINOR"), ("decision", "initial"),
    ("decision", []), ("reason", "  "), ("node_id", None), ("target_view_version", 1),
    ("selected_primary_claim_ids", []), ("selected_primary_claim_ids", "bad"),
    ("selected_context_claim_ids", [None]), ("candidate_claims", []),
    ("candidate_claims", [{"claim_id": "CLM_BAD", "role": "unknown"}]),
    ("thesis_break", {}), ("source", {}), ("evidence_sufficiency", {"sufficient": True}),
])
def test_strict_artifact_shape(db_path, key, value):
    review = review_for(db_path)
    review[key] = value
    with pytest.raises(intake.HumanReviewIntakeError, match="INVALID_ARTIFACT"):
        intake.prepare_review(db_path, review)


@pytest.mark.parametrize("mutation", ["missing", "extra", "source_id", "duplicate_claim", "duplicate_primary", "thesis"])
def test_strict_artifact_structure(db_path, mutation):
    review = review_for(db_path)
    if mutation == "missing":
        del review["reason"]
    elif mutation == "extra":
        review["localStorageKey"] = "untrusted"
    elif mutation == "source_id":
        review["source"]["source_id"] = "SRC_OTHER"
    elif mutation == "duplicate_claim":
        review["candidate_claims"].append(review["candidate_claims"][0])
    elif mutation == "duplicate_primary":
        review["selected_primary_claim_ids"] *= 2
    else:
        review["decision"] = "thesis"
    with pytest.raises(intake.HumanReviewIntakeError, match="INVALID_ARTIFACT"):
        intake.prepare_review(db_path, review)


@pytest.mark.parametrize("raw", ['{', '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', '[]', 'null'])
def test_malformed_json_is_never_repaired(tmp_path, raw):
    path = tmp_path / "bad.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(intake.HumanReviewIntakeError):
        intake.read_artifact(path)


@pytest.mark.parametrize("phase", ["prepare", "submit"])
@pytest.mark.parametrize("mutation,code", [
    ("view_id", "STALE_TARGET_VIEW"), ("view_version", "STALE_TARGET_VIEW"),
    ("view_missing", "STALE_TARGET_VIEW"), ("claim_added", "CANDIDATE_EVIDENCE_CHANGED"),
    ("claim_deleted", "CANDIDATE_EVIDENCE_CHANGED"), ("role", "CANDIDATE_EVIDENCE_CHANGED"),
    ("inactive", "NODE_NOT_ACTIVE"), ("node_deleted", "NODE_NOT_FOUND"),
    ("source_deleted", "SOURCE_NOT_FOUND"), ("status", "INELIGIBLE_EVIDENCE"),
])
def test_canonical_changes_are_blocked_in_both_phases(db_path, phase, mutation, code):
    review = review_for(db_path)
    draft = edited_draft(db_path)
    db = Database(db_path)
    primary = review["selected_primary_claim_ids"][0]
    if mutation == "view_id":
        db.execute("UPDATE current_views SET view_id='VIEW_REPLACED' WHERE node_id=?", (MLCC_NODE_ID,))
    elif mutation == "view_version":
        db.execute("UPDATE current_views SET version='changed' WHERE node_id=?", (MLCC_NODE_ID,))
    elif mutation == "view_missing":
        db.execute("DELETE FROM current_views WHERE node_id=?", (MLCC_NODE_ID,))
    elif mutation == "claim_added":
        db.execute("""INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at)
                      VALUES('CLM_EXTRA','MLCC extra','fact','2026',?,'2026')""", (SOURCE,))
        db.execute("INSERT INTO claim_node_links VALUES('CLM_EXTRA',?,'subject')", (MLCC_NODE_ID,))
    elif mutation == "claim_deleted":
        db.execute("DELETE FROM claims WHERE claim_id=?", (primary,))
    elif mutation == "role":
        db.execute("UPDATE claim_node_links SET role='context' WHERE node_id=? AND claim_id=?", (MLCC_NODE_ID, primary))
    elif mutation == "inactive":
        db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (MLCC_NODE_ID,))
    elif mutation == "node_deleted":
        db.execute("DELETE FROM nodes WHERE node_id=?", (MLCC_NODE_ID,))
    elif mutation == "source_deleted":
        db.execute("DELETE FROM sources WHERE source_id=?", (SOURCE,))
    else:
        db.execute("UPDATE claims SET status='invalidated' WHERE claim_id=?", (primary,))
    before = snapshot(db_path)
    if phase == "prepare":
        with pytest.raises(intake.HumanReviewIntakeError, match=code):
            intake.prepare_review(db_path, review)
        assert snapshot(db_path) == before
    else:
        blocked(db_path, draft, code)


def test_latest_order_and_order_independent_snapshot(db_path):
    review = review_for(db_path)
    review["candidate_claims"].reverse()
    db = Database(db_path)
    for view_id, date, seq, status in [
        ("VIEW_OLDER", "20260827", 999, "official"),
        ("VIEW_EARLIER_SEQ", "20260828", 0, "official"),
        ("VIEW_!TIE", "20260828", 1, "official"),
        ("VIEW_FUTURE_DRAFT", "20990101", 99, "draft"),
    ]:
        db.execute("""INSERT INTO current_views(view_id,node_id,version,status,change_level,content_md,
                      content_json,revision_date,revision_seq,created_at)
                      VALUES(?,?,?,?,'minor','','{}',?,?,'2099')""",
                   (view_id, MLCC_NODE_ID, "v_" + view_id, status, date, seq))
    assert intake.prepare_review(db_path, review)["payload"]["previous_view_id"] == review["target_view_id"]
    db.execute("UPDATE current_views SET view_id='VIEW_ZZZ' WHERE view_id='VIEW_!TIE'")
    with pytest.raises(intake.HumanReviewIntakeError, match="STALE_TARGET_VIEW"):
        intake.prepare_review(db_path, review)


@pytest.mark.parametrize("node_id,role", [(MLCC_NODE_ID, "context"), (YUNZHONG_NODE_ID, "related")])
def test_non_subject_primary_rejected(db_path, node_id, role):
    review = review_for(db_path, node_id=node_id)
    review["selected_primary_claim_ids"] = [next(c["claim_id"] for c in review["candidate_claims"] if c["role"] == role)]
    with pytest.raises(intake.HumanReviewIntakeError, match="INELIGIBLE_EVIDENCE"):
        intake.prepare_review(db_path, review)


@pytest.mark.parametrize("status", ["needs_review", "invalidated", "superseded", "expired", "updated", "unknown", ""])
def test_ineligible_primary_status(db_path, status):
    review = review_for(db_path)
    Database(db_path).execute("UPDATE claims SET status=? WHERE claim_id=?", (status, review["selected_primary_claim_ids"][0]))
    with pytest.raises(intake.HumanReviewIntakeError, match="INELIGIBLE_EVIDENCE"):
        intake.prepare_review(db_path, review)


@pytest.mark.parametrize("status", ["current", "pending_verification", "disputed", " CURRENT "])
def test_eligible_statuses_are_not_scored(db_path, status):
    review = review_for(db_path)
    Database(db_path).execute("UPDATE claims SET status=? WHERE claim_id=?", (status, review["selected_primary_claim_ids"][0]))
    assert intake.prepare_review(db_path, review)["payload"]["human_review_handoff"]["evidence_sufficiency"] == "NOT_EVALUATED"


@pytest.mark.parametrize("mutation", ["recent_change", "whitespace", "list_order", "list_duplicate", "evidence_order"])
def test_metadata_and_compare_normalization_do_not_satisfy_human_edit(db_path, mutation):
    draft = intake.prepare_review(db_path, review_for(db_path))
    content = draft["payload"]["proposed_current_view"]
    if mutation == "recent_change":
        content["recent_change"] = "A human reason alone is not View content"
    elif mutation == "whitespace":
        content["one_line_conclusion"] = "  " + content["one_line_conclusion"] + "  "
    elif mutation == "list_order":
        content["core_logic"].reverse()
    elif mutation == "list_duplicate":
        content["core_logic"].append(content["core_logic"][0])
    else:
        content["evidence_claim_ids"].reverse()
    blocked(db_path, draft, "CHANGE_DECISION_WITHOUT_VIEW_CHANGE")


@pytest.mark.parametrize("field", ["change_level", "previous_view_id", "evidence_claim_ids", "trigger_source_id", "node_id"])
def test_draft_envelope_cannot_override_review(db_path, field):
    draft = edited_draft(db_path)
    draft["payload"][field] = "tampered"
    blocked(db_path, draft, "DRAFT_ENVELOPE_CHANGED")


@pytest.mark.parametrize("kind", ["missing_citation", "expert_fact", "expert_attribution", "numeric_scope", "missing_dimension"])
def test_frozen_product_validator_is_not_weakened(db_path, kind):
    draft = edited_draft(db_path)
    content = draft["payload"]["proposed_current_view"]
    if kind == "missing_citation":
        content["core_logic"][0] = "MLCC周期需验证。"
    elif kind == "expert_fact":
        content["key_facts"].append(content["core_logic"][0])
    elif kind == "expert_attribution":
        content["core_logic"][0] = content["core_logic"][0].replace("分析师判断认为，", "")
    elif kind == "numeric_scope":
        content["one_line_conclusion"] += " MLCC产能80亿颗/月。"
    else:
        del content["type_specific"]["pricing"]
    blocked(db_path, draft, "FROZEN_CURRENT_VIEW_VALIDATION_FAILED")


def test_company_guidance_attribution_required(db_path):
    draft = edited_draft(db_path, node_id=YUNZHONG_NODE_ID)
    content = draft["payload"]["proposed_current_view"]
    content["key_facts"][0] = content["key_facts"][0].replace("公司表示，昀冢科技", "")
    blocked(db_path, draft, "FROZEN_CURRENT_VIEW_VALIDATION_FAILED")


def test_single_company_scope_cannot_become_industry_fact(db_path):
    draft = edited_draft(db_path)
    for cid in draft["payload"]["evidence_claim_ids"]:
        Database(db_path).execute("UPDATE claims SET scope='公司',attributed_to='MLCC' WHERE claim_id=?", (cid,))
    draft["payload"]["proposed_current_view"]["one_line_conclusion"] = "MLCC行业已确认长期上行。"
    blocked(db_path, draft, "exceeds single-company Evidence scope")


@pytest.mark.parametrize("field", ["one_line_conclusion", "key_facts", "type_specific", "assumptions_to_verify"])
def test_context_cannot_leak_even_with_a_valid_primary_citation(db_path, field):
    draft = edited_draft(db_path)
    payload = draft["payload"]
    text = f"MLCC [{payload['evidence_claim_ids'][0]}] [{payload['human_review_handoff']['selected_context_claim_ids'][0]}]"
    content = payload["proposed_current_view"]
    if field == "one_line_conclusion":
        content[field] += text
    elif field == "type_specific":
        content[field]["extra"] = {"nested": text}
    else:
        content[field].append(text)
    blocked(db_path, draft, "NON_PRIMARY_DIRECT_SUPPORT")


def test_needs_review_only_in_explicitly_unresolved_fields(db_path):
    draft = edited_draft(db_path, node_id=YUNZHONG_NODE_ID)
    content = draft["payload"]["proposed_current_view"]
    content["key_facts"].append(content["assumptions_to_verify"][0])
    blocked(db_path, draft, "NON_PRIMARY_DIRECT_SUPPORT")
    content["key_facts"].pop()
    content["assumptions_to_verify"][0] = content["assumptions_to_verify"][0].replace("needs_review", "confirmed")
    # The status of a different unresolved item must not authorize this item.
    blocked(db_path, draft, "NON_PRIMARY_DIRECT_SUPPORT")


def test_exact_repeat_is_idempotent_and_conflicting_content_is_not_merged(db_path):
    draft = edited_draft(db_path)
    first = intake.submit_review(db_path, draft, isolated=True)
    sha = file_sha256(db_path)
    second = intake.submit_review(db_path, json.loads(json.dumps(draft, sort_keys=True)), isolated=True)
    assert second == {**first, "created": False}
    assert file_sha256(db_path) == sha
    draft["payload"]["proposed_current_view"]["knowledge_gaps"].append("缺少MLCC新增独立证据。")
    blocked(db_path, draft, "PENDING_PROPOSAL_CONFLICT")


def test_concurrent_exact_submissions_share_one_pending_proposal(db_path):
    draft = edited_draft(db_path)
    barrier = Barrier(2)
    def submit():
        barrier.wait()
        return intake.submit_review(db_path, deepcopy(draft), isolated=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert results[0]["proposal_id"] == results[1]["proposal_id"]
    assert sum(r["created"] for r in results) == 1
    assert len(snapshot(db_path)["proposals"]) == 1


def test_persistence_uses_existing_boundary_and_rolls_back(db_path, monkeypatch):
    original = Database.add_proposal
    def fail_after_insert(self, *args, **kwargs):
        assert kwargs["_conn"].in_transaction
        original(self, *args, **kwargs)
        raise RuntimeError("injected failure after INSERT")
    monkeypatch.setattr(Database, "add_proposal", fail_after_insert)
    before = snapshot(db_path)
    with pytest.raises(RuntimeError, match="injected"):
        intake.submit_review(db_path, edited_draft(db_path), isolated=True)
    assert snapshot(db_path) == before


def test_production_and_unacknowledged_writes_blocked(db_path):
    draft = edited_draft(db_path)
    with pytest.raises(intake.HumanReviewIntakeError, match="ISOLATED_DB_REQUIRED"):
        intake.submit_review(db_path, draft)
    production = intake.load_config().db_path
    blocked(production, draft, "PRODUCTION_WRITE_NOT_AUTHORIZED")
    assert intake.prepare_review(production, review_for(production))["status"] == "HUMAN_EDIT_REQUIRED"


def test_hardlink_alias_cannot_bypass_production_guard(db_path, tmp_path):
    alias = tmp_path / "isolated-looking.db"
    os.link(intake.load_config().db_path, alias)
    blocked(alias, edited_draft(db_path), "PRODUCTION_WRITE_NOT_AUTHORIZED")


def test_no_change_cannot_be_disguised_as_change_draft(db_path):
    draft = edited_draft(db_path)
    draft["payload"]["human_review_handoff"]["decision"] = "no_change"
    blocked(db_path, draft, "NO_PROPOSAL")


def test_unchanged_content_requires_edit_even_with_fewer_selected_claims(db_path):
    review = review_for(db_path)
    review["selected_primary_claim_ids"] = review["selected_primary_claim_ids"][:1]
    blocked(db_path, intake.prepare_review(db_path, review), "CHANGE_DECISION_WITHOUT_VIEW_CHANGE")


@pytest.mark.parametrize("mutation", ["missing_primary", "bad_context", "subject_outside_snapshot"])
def test_selected_evidence_requires_exact_candidate_membership(db_path, mutation):
    review = review_for(db_path)
    if mutation == "missing_primary":
        review["selected_primary_claim_ids"].append("CLM_MISSING")
    elif mutation == "bad_context":
        review["selected_context_claim_ids"].append(review["selected_primary_claim_ids"][0])
    else:
        Database(db_path).execute(
            """INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at)
               VALUES('SRC_OTHER','Other','other.md','','other','standard','2026')""")
        Database(db_path).execute(
            """INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at)
               VALUES('CLM_OTHER_SOURCE','MLCC other','fact','2026','SRC_OTHER','2026')""")
        Database(db_path).execute("INSERT INTO claim_node_links VALUES('CLM_OTHER_SOURCE',?,'subject')", (MLCC_NODE_ID,))
        review["selected_primary_claim_ids"].append("CLM_OTHER_SOURCE")
    with pytest.raises(intake.HumanReviewIntakeError, match="INELIGIBLE_EVIDENCE"):
        intake.prepare_review(db_path, review)


def test_repeat_still_revalidates_eligibility(db_path):
    draft = edited_draft(db_path)
    intake.submit_review(db_path, draft, isolated=True)
    Database(db_path).execute("UPDATE claims SET status='invalidated' WHERE claim_id=?",
                              (draft["payload"]["evidence_claim_ids"][0],))
    blocked(db_path, draft, "INELIGIBLE_EVIDENCE")


def test_only_proposal_insert_is_authorized_in_submit_transaction(db_path, monkeypatch):
    original = Database.transaction
    writes = []
    @contextmanager
    def restricted(self, **kwargs):
        with original(self, **kwargs) as conn:
            def authorize(action, table, column, database, trigger):
                if action in {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}:
                    writes.append((action, table))
                    if action != sqlite3.SQLITE_INSERT or table != "proposals":
                        return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            conn.set_authorizer(authorize)
            yield conn
    monkeypatch.setattr(Database, "transaction", restricted)
    intake.submit_review(db_path, edited_draft(db_path), isolated=True)
    assert writes == [(sqlite3.SQLITE_INSERT, "proposals")]


def test_cli_prepare_and_isolated_submit(db_path, tmp_path, capsys):
    review_path = tmp_path / "review.json"
    draft_path = tmp_path / "draft.json"
    review_path.write_text(json.dumps(review_for(db_path)), encoding="utf-8")
    args = ["prepare", "--db", str(db_path), "--review", str(review_path), "--output", str(draft_path)]
    assert main(args) == 0
    assert main(args) == 2  # Never overwrite an artifact or database.
    draft = intake.read_artifact(draft_path)
    draft["payload"]["proposed_current_view"]["knowledge_gaps"].append("缺少MLCC后续验证证据。")
    draft_path.write_text(json.dumps(draft), encoding="utf-8")
    capsys.readouterr()
    assert main(["submit", "--isolated-db", str(db_path), "--draft", str(draft_path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pending"
    assert main(["submit", "--isolated-db", str(intake.load_config().db_path), "--draft", str(draft_path)]) == 2
    assert "PRODUCTION_WRITE_NOT_AUTHORIZED" in capsys.readouterr().err
