from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.cli import main
from pro_a.db import Database
from pro_a.proposals import ProposalManager

from stability_helpers import add_source_and_claim, make_config


def add_claim(
    db: Database,
    claim_id: str,
    node_id: str,
    *,
    status: str = "current",
) -> None:
    add_source_and_claim(
        db,
        source_id=f"SRC_{claim_id}",
        claim_id=claim_id,
        node_id=node_id,
        source_rank="A",
        origin_type="primary",
        confidence=0.90,
    )
    if status != "current":
        db.execute("UPDATE claims SET status=? WHERE claim_id=?", (status, claim_id))


def relation_context(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id = db.add_node("Relation Proposal From", "Product")
    to_node_id = db.add_node("Relation Proposal To", "Application")
    add_claim(db, "CLM_REL_1", from_node_id)
    add_claim(db, "CLM_REL_2", from_node_id)
    manager = ProposalManager(cfg, db, object())
    return cfg, db, manager, from_node_id, to_node_id


def propose(
    db: Database,
    from_node_id: str,
    to_node_id: str,
    *,
    relation_type: str = "uses",
    scope: str = "Rubin",
    claim_ids: list[str] | None = None,
    confidence: float | None = 0.9,
) -> str:
    return db.propose_relation(
        from_node_id,
        relation_type,
        to_node_id,
        scope=scope,
        supporting_claim_ids=claim_ids if claim_ids is not None else ["CLM_REL_1"],
        confidence=confidence,
        reason="Explicit Relation Evidence",
    )


@pytest.mark.parametrize("endpoint", ["from", "to"])
def test_relation_proposal_rejects_unknown_node(tmp_path: Path, endpoint: str):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    if endpoint == "from":
        from_node_id = "NODE_MISSING_FROM"
    else:
        to_node_id = "NODE_MISSING_TO"

    with pytest.raises(ValueError, match=f"Unknown {endpoint} Node"):
        propose(db, from_node_id, to_node_id)

    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0


@pytest.mark.parametrize("endpoint", ["from", "to"])
def test_relation_proposal_rejects_inactive_node(tmp_path: Path, endpoint: str):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    inactive_id = from_node_id if endpoint == "from" else to_node_id
    db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (inactive_id,))

    with pytest.raises(ValueError, match=f"{endpoint} Node is not active"):
        propose(db, from_node_id, to_node_id)


def test_relation_proposal_rejects_self_relation(tmp_path: Path):
    _, db, _, from_node_id, _ = relation_context(tmp_path)

    with pytest.raises(ValueError, match="cannot relate a Node to itself"):
        propose(db, from_node_id, from_node_id)


@pytest.mark.parametrize(
    ("relation_type", "message"),
    [("invented_relation", "Invalid relation_type"), ("part_of", "does not support part_of")],
)
def test_relation_proposal_rejects_invalid_or_structural_type(
    tmp_path: Path, relation_type: str, message: str,
):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    with pytest.raises(ValueError, match=message):
        propose(db, from_node_id, to_node_id, relation_type=relation_type)


def test_relation_proposal_requires_explicit_supporting_claim(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    with pytest.raises(ValueError, match="at least one supporting Claim"):
        propose(db, from_node_id, to_node_id, claim_ids=[])


def test_relation_proposal_rejects_unknown_claim(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    with pytest.raises(ValueError, match="Unknown supporting Claim: CLM_MISSING"):
        propose(db, from_node_id, to_node_id, claim_ids=["CLM_MISSING"])


def test_relation_proposal_rejects_needs_review_claim(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    db.execute("UPDATE claims SET status='needs_review' WHERE claim_id='CLM_REL_1'")

    with pytest.raises(ValueError, match="Supporting Claim needs review"):
        propose(db, from_node_id, to_node_id)


@pytest.mark.parametrize("status", ["updated", "invalidated", "expired"])
def test_relation_proposal_rejects_inactive_supporting_claim(
    tmp_path: Path, status: str,
):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    db.execute("UPDATE claims SET status=? WHERE claim_id='CLM_REL_1'", (status,))

    with pytest.raises(ValueError, match="cannot be used as active Evidence"):
        propose(db, from_node_id, to_node_id)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_relation_proposal_rejects_out_of_range_confidence(
    tmp_path: Path, confidence: float,
):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    with pytest.raises(ValueError, match="between 0 and 1"):
        propose(db, from_node_id, to_node_id, confidence=confidence)


def test_pending_relation_proposal_deduplicates_and_merges_claims(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    first = propose(db, from_node_id, to_node_id, scope="  Rubin  ")
    second = propose(
        db,
        from_node_id,
        to_node_id,
        scope="Rubin",
        claim_ids=["CLM_REL_1", "CLM_REL_2", "CLM_REL_2"],
    )

    assert second == first
    proposal = db.proposal(first)
    assert proposal["payload"]["scope"] == "Rubin"
    assert proposal["payload"]["supporting_claim_ids"] == ["CLM_REL_1", "CLM_REL_2"]
    assert proposal["source_impact_id"] == ""
    assert proposal["propagation_batch_id"] == ""
    assert db.one(
        "SELECT COUNT(*) AS n FROM proposals WHERE proposal_type='node_relation'"
    )["n"] == 1


def test_pending_relation_proposal_identity_includes_scope_and_type(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    first = propose(db, from_node_id, to_node_id)
    different_scope = propose(db, from_node_id, to_node_id, scope="Blackwell")
    different_type = propose(
        db, from_node_id, to_node_id, relation_type="depends_on",
    )

    assert len({first, different_scope, different_type}) == 3


def test_invalid_pending_relation_recovers_to_new_proposal_and_syncs_artifact(
    tmp_path: Path, capsys,
):
    cfg, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    base_args = [
        "--config",
        str(cfg.config_path),
        "relations",
        "propose",
        from_node_id,
        "uses",
        to_node_id,
        "--scope",
        "Rubin",
    ]
    main([*base_args, "--evidence-claim-id", "CLM_REL_1"])
    first_id = capsys.readouterr().out.strip()
    first_payload = db.proposal(first_id)["payload"]
    db.execute("UPDATE claims SET status='invalidated' WHERE claim_id='CLM_REL_1'")

    main([*base_args, "--evidence-claim-id", "CLM_REL_2"])
    second_id = capsys.readouterr().out.strip()

    assert second_id != first_id
    first = db.proposal(first_id)
    second = db.proposal(second_id)
    assert first["status"] == "stale"
    assert first["payload"] == first_payload
    assert first["payload"]["supporting_claim_ids"] == ["CLM_REL_1"]
    assert first["resolved_at"]
    assert "no longer valid" in first["reason"]
    assert "CLM_REL_1" in first["reason"]
    assert "status=invalidated" in first["reason"]
    assert second["status"] == "pending"
    assert second["payload"]["supporting_claim_ids"] == ["CLM_REL_2"]
    assert db.one(
        """SELECT COUNT(*) AS n FROM proposals
           WHERE proposal_type='node_relation' AND status='pending'"""
    )["n"] == 1

    artifact = (
        cfg.root / "review" / "proposals" / f"{first_id}.md"
    ).read_text(encoding="utf-8")
    assert "- status: stale" in artifact
    assert first["reason"] in artifact
    assert '"CLM_REL_1"' in artifact

    accepted = manager.accept(second_id)
    assert [
        (item["claim_id"], item["evidence_role"], item["evidence_status"])
        for item in db.relation_evidence(accepted["relation_id"])
    ] == [("CLM_REL_2", "supports", "active")]


def test_recovery_keeps_valid_pending_merge_behavior(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    first_id = propose(db, from_node_id, to_node_id, claim_ids=["CLM_REL_1"])
    stale_ids: list[str] = []

    second_id = db.propose_relation(
        from_node_id,
        "uses",
        to_node_id,
        scope="Rubin",
        supporting_claim_ids=["CLM_REL_2"],
        _stale_proposal_ids=stale_ids,
    )

    assert second_id == first_id
    assert stale_ids == []
    assert db.proposal(first_id)["payload"]["supporting_claim_ids"] == [
        "CLM_REL_1",
        "CLM_REL_2",
    ]


def test_invalid_new_request_does_not_stale_old_pending_proposal(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    first_id = propose(db, from_node_id, to_node_id, claim_ids=["CLM_REL_1"])
    db.execute(
        "UPDATE claims SET status='invalidated' WHERE claim_id IN ('CLM_REL_1','CLM_REL_2')"
    )
    stale_ids: list[str] = []

    with pytest.raises(ValueError, match="CLM_REL_2.*status=invalidated"):
        db.propose_relation(
            from_node_id,
            "uses",
            to_node_id,
            scope="Rubin",
            supporting_claim_ids=["CLM_REL_2"],
            _stale_proposal_ids=stale_ids,
        )

    assert stale_ids == []
    assert db.proposal(first_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 1


def test_inactive_new_endpoint_does_not_start_pending_recovery(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    first_id = propose(db, from_node_id, to_node_id, claim_ids=["CLM_REL_1"])
    db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (to_node_id,))
    stale_ids: list[str] = []

    with pytest.raises(ValueError, match="to Node is not active"):
        db.propose_relation(
            from_node_id,
            "uses",
            to_node_id,
            scope="Rubin",
            supporting_claim_ids=["CLM_REL_2"],
            _stale_proposal_ids=stale_ids,
        )

    assert stale_ids == []
    assert db.proposal(first_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 1


def test_pending_recovery_rolls_back_stale_if_new_insert_fails(
    tmp_path: Path, monkeypatch,
):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    first_id = propose(db, from_node_id, to_node_id, claim_ids=["CLM_REL_1"])
    first_reason = db.proposal(first_id)["reason"]
    db.execute("UPDATE claims SET status='invalidated' WHERE claim_id='CLM_REL_1'")
    monkeypatch.setattr("pro_a.db.make_id", lambda prefix: first_id)
    stale_ids: list[str] = []

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint"):
        db.propose_relation(
            from_node_id,
            "uses",
            to_node_id,
            scope="Rubin",
            supporting_claim_ids=["CLM_REL_2"],
            _stale_proposal_ids=stale_ids,
        )

    first = db.proposal(first_id)
    assert stale_ids == []
    assert first["status"] == "pending"
    assert first["reason"] == first_reason
    assert first["resolved_at"] == ""
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 1


def isolated_state(db: Database) -> dict[str, int]:
    return {
        "impact_reviews": db.one("SELECT COUNT(*) AS n FROM impact_reviews")["n"],
        "current_view_proposals": db.one(
            "SELECT COUNT(*) AS n FROM proposals WHERE proposal_type='current_view_change'"
        )["n"],
        "current_views": db.one("SELECT COUNT(*) AS n FROM current_views")["n"],
        "knowledge_gaps": db.one("SELECT COUNT(*) AS n FROM knowledge_gaps")["n"],
        "research_questions": db.one("SELECT COUNT(*) AS n FROM research_questions")["n"],
    }


def test_accept_new_relation_is_atomic_idempotent_and_isolated(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    before = isolated_state(db)
    proposal_id = propose(
        db,
        from_node_id,
        to_node_id,
        scope="  Rubin  ",
        claim_ids=["CLM_REL_1", "CLM_REL_2"],
    )

    first = manager.accept(proposal_id)
    second = manager.accept(proposal_id)

    assert second == first
    assert first == {
        "relation_id": first["relation_id"],
        "created_new_relation": True,
        "attached_claim_ids": ["CLM_REL_1", "CLM_REL_2"],
        "already_attached_claim_ids": [],
    }
    assert "view_id" not in first
    assert "propagation_batch_id" not in first
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1
    relation = db.one(
        "SELECT * FROM node_relations WHERE relation_id=?", (first["relation_id"],)
    )
    assert relation["scope"] == "Rubin"
    assert relation["confidence"] == 0.9
    assert relation["evidence_claim_id"] == "CLM_REL_1"
    assert [item["claim_id"] for item in db.relation_evidence(first["relation_id"])] == [
        "CLM_REL_1",
        "CLM_REL_2",
    ]
    assert isolated_state(db) == before


def test_accept_existing_relation_only_adds_missing_evidence(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    relation_id = db.add_relation(
        from_node_id,
        "uses",
        to_node_id,
        scope="Rubin",
        evidence_claim_id="CLM_REL_1",
    )
    proposal_id = propose(
        db,
        from_node_id,
        to_node_id,
        claim_ids=["CLM_REL_1", "CLM_REL_2"],
    )

    result = manager.accept(proposal_id)

    assert result == {
        "relation_id": relation_id,
        "created_new_relation": False,
        "attached_claim_ids": ["CLM_REL_2"],
        "already_attached_claim_ids": ["CLM_REL_1"],
    }
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1
    assert db.one("SELECT COUNT(*) AS n FROM relation_evidence_links")["n"] == 2


@pytest.mark.parametrize("changed_object", ["node", "claim"])
def test_accept_revalidates_mutable_database_state(
    tmp_path: Path, changed_object: str,
):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    proposal_id = propose(db, from_node_id, to_node_id)
    if changed_object == "node":
        db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (to_node_id,))
        message = "to Node is not active"
    else:
        db.execute("UPDATE claims SET status='needs_review' WHERE claim_id='CLM_REL_1'")
        message = "Supporting Claim needs review"

    with pytest.raises(ValueError, match=message):
        manager.accept(proposal_id)

    assert db.proposal(proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM relation_evidence_links")["n"] == 0


def test_accept_revalidates_payload_structure(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    proposal_id = propose(db, from_node_id, to_node_id)
    payload = db.proposal(proposal_id)["payload"]
    payload.pop("to_node_id")
    db.execute(
        "UPDATE proposals SET payload_json=? WHERE proposal_id=?",
        (json.dumps(payload), proposal_id),
    )

    with pytest.raises(ValueError, match="to_node_id is required"):
        manager.accept(proposal_id)

    assert db.proposal(proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_generic_node_relation_proposal_entry_uses_validation_and_dedup(tmp_path: Path):
    _, db, _, from_node_id, to_node_id = relation_context(tmp_path)
    payload = {
        "from_node_id": from_node_id,
        "relation_type": "uses",
        "to_node_id": to_node_id,
        "scope": " Rubin ",
        "supporting_claim_ids": ["CLM_REL_1"],
        "confidence": 0.9,
        "reason": "explicit",
    }

    first = db.add_proposal("node_relation", payload)
    second = db.add_proposal(
        "node_relation",
        {**payload, "scope": "Rubin", "supporting_claim_ids": ["CLM_REL_2"]},
    )

    assert second == first
    assert db.proposal(first)["payload"]["supporting_claim_ids"] == [
        "CLM_REL_1",
        "CLM_REL_2",
    ]

    with pytest.raises(ValueError, match="does not support part_of"):
        db.add_proposal("node_relation", {**payload, "relation_type": "part_of"})
    with pytest.raises(ValueError, match="Impact Recovery or propagation"):
        db.add_proposal("node_relation", payload, propagation_batch_id="BATCH_BAD")


@pytest.mark.parametrize(
    ("relation_type", "message"),
    [("part_of", "does not support part_of"), ("invented_relation", "Invalid relation_type")],
)
def test_accept_revalidates_relation_type_after_proposal_creation(
    tmp_path: Path, relation_type: str, message: str,
):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    proposal_id = propose(db, from_node_id, to_node_id)
    payload = db.proposal(proposal_id)["payload"]
    payload["relation_type"] = relation_type
    db.execute(
        "UPDATE proposals SET payload_json=? WHERE proposal_id=?",
        (json.dumps(payload), proposal_id),
    )

    with pytest.raises(ValueError, match=message):
        manager.accept(proposal_id)

    assert db.proposal(proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_accept_rejects_supporting_claim_deleted_after_creation(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    proposal_id = propose(db, from_node_id, to_node_id)
    db.execute("DELETE FROM claims WHERE claim_id='CLM_REL_1'")

    with pytest.raises(ValueError, match="Unknown supporting Claim: CLM_REL_1"):
        manager.accept(proposal_id)

    assert db.proposal(proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_existing_retired_evidence_causes_full_accept_rollback(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    add_claim(db, "CLM_REL_BASE", from_node_id)
    relation_id = db.add_relation(
        from_node_id,
        "uses",
        to_node_id,
        scope="Rubin",
        evidence_claim_id="CLM_REL_BASE",
    )
    db.add_relation_evidence(
        relation_id,
        "CLM_REL_2",
        evidence_role="supports",
        status="retired",
    )
    proposal_id = propose(
        db,
        from_node_id,
        to_node_id,
        claim_ids=["CLM_REL_1", "CLM_REL_2"],
    )

    with pytest.raises(ValueError, match="supporting Evidence is not active"):
        manager.accept(proposal_id)

    assert db.proposal(proposal_id)["status"] == "pending"
    assert db.one(
        """SELECT COUNT(*) AS n FROM relation_evidence_links
           WHERE relation_id=? AND claim_id='CLM_REL_1'""",
        (relation_id,),
    )["n"] == 0


def test_accept_does_not_reactivate_existing_relation(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    relation_id = db.add_relation(
        from_node_id,
        "uses",
        to_node_id,
        scope="Rubin",
        evidence_claim_id="CLM_REL_1",
    )
    db.execute("UPDATE node_relations SET status='retired' WHERE relation_id=?", (relation_id,))
    proposal_id = propose(
        db, from_node_id, to_node_id, claim_ids=["CLM_REL_2"],
    )

    with pytest.raises(ValueError, match="Existing Relation is not current"):
        manager.accept(proposal_id)

    assert db.one(
        "SELECT status FROM node_relations WHERE relation_id=?", (relation_id,)
    )["status"] == "retired"
    assert db.proposal(proposal_id)["status"] == "pending"


def test_reject_relation_proposal_only_changes_proposal_status(tmp_path: Path):
    _, db, manager, from_node_id, to_node_id = relation_context(tmp_path)
    proposal_id = propose(db, from_node_id, to_node_id)
    before = isolated_state(db)

    manager.reject(proposal_id, "Relation evidence is insufficient")

    proposal = db.proposal(proposal_id)
    assert proposal["status"] == "rejected"
    assert proposal["reason"] == "Relation evidence is insufficient"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM relation_evidence_links")["n"] == 0
    assert isolated_state(db) == before


def test_relation_propose_cli_supports_repeated_evidence_flags(
    tmp_path: Path, capsys,
):
    cfg, db, _, from_node_id, to_node_id = relation_context(tmp_path)

    main([
        "--config",
        str(cfg.config_path),
        "relations",
        "propose",
        from_node_id,
        "uses",
        to_node_id,
        "--scope",
        "Rubin",
        "--evidence-claim-id",
        "CLM_REL_1",
        "--evidence-claim-id",
        "CLM_REL_2",
        "--confidence",
        "0.9",
        "--reason",
        "Rubin explicitly uses this component",
    ])
    proposal_id = capsys.readouterr().out.strip()

    proposal = db.proposal(proposal_id)
    assert proposal["proposal_type"] == "node_relation"
    assert proposal["payload"] == {
        "from_node_id": from_node_id,
        "relation_type": "uses",
        "to_node_id": to_node_id,
        "scope": "Rubin",
        "supporting_claim_ids": ["CLM_REL_1", "CLM_REL_2"],
        "reason": "Rubin explicitly uses this component",
        "confidence": 0.9,
    }
    assert proposal["source_impact_id"] == ""
    assert proposal["propagation_batch_id"] == ""
