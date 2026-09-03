from __future__ import annotations

from pathlib import Path

import pytest

from pro_a.audit import build_source_audit
from pro_a.constants import NODE_PARENT_PLACEMENT_PROPOSAL_TYPE
from pro_a.proposals import ProposalManager

from stability_helpers import add_source_and_claim, make_config


class NoChangeAnalyzer:
    available = True

    def review_impact(self, node, current_view_md, evidence, context):
        return {
            "requires_change": False,
            "change_level": "none",
            "evidence_sufficiency": {"sufficient": True},
        }


def accept_new_node(
    tmp_path: Path,
    parent_ids: list[str],
    *,
    name: str = "Governed Child",
):
    cfg, db = make_config(tmp_path)
    proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": name,
            "primary_type": "Product",
            "aliases": [],
            "description": "A separately governed Node identity",
            "suggested_parent_node_ids": parent_ids,
            "reason": "Model-advisory ontology placement",
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    result = manager.accept(proposal_id)
    return db, manager, proposal_id, result


def test_parent_placement_accept_creates_exactly_one_part_of_without_evidence(
    tmp_path: Path,
):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Governed Parent", "Segment")
    proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Governed Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(proposal_id)
    parent_proposal_id = node_result["parent_placement_proposal_ids"][0]

    first = manager.accept(parent_proposal_id)
    second = manager.accept(parent_proposal_id)

    assert second == first
    assert first["created_new_relation"] is True
    assert first["relation_evidence_created"] is False
    assert db.proposal(parent_proposal_id)["status"] == "accepted"
    assert db.one(
        """SELECT COUNT(*) AS n FROM node_relations
           WHERE from_node_id=? AND relation_type='part_of' AND to_node_id=?""",
        (node_result["node_id"], parent_id),
    )["n"] == 1
    assert db.one("SELECT COUNT(*) AS n FROM relation_evidence_links")["n"] == 0


def test_parent_placement_reject_preserves_node_source_and_claim_links(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Placement Parent", "Segment")
    anchor_id = db.add_node("Claim Anchor", "Application")
    add_source_and_claim(
        db,
        source_id="SRC_PARENT_REJECT",
        claim_id="CLM_PARENT_REJECT",
        node_id=anchor_id,
        source_rank="A",
        origin_type="primary",
        confidence=0.9,
    )
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Independent Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "source_id": "SRC_PARENT_REJECT",
            "related_claim_ids": ["CLM_PARENT_REJECT"],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    parent_proposal_id = node_result["parent_placement_proposal_ids"][0]

    manager.reject(parent_proposal_id, "Taxonomy placement not approved")
    audit = build_source_audit(db, "SRC_PARENT_REJECT")

    assert db.get_node(node_result["node_id"])["status"] == "active"
    assert db.proposal(node_proposal_id)["status"] == "accepted"
    assert db.proposal(parent_proposal_id)["status"] == "rejected"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0
    assert db.one(
        "SELECT COUNT(*) AS n FROM source_node_links WHERE source_id=? AND node_id=?",
        ("SRC_PARENT_REJECT", node_result["node_id"]),
    )["n"] == 1
    assert db.one(
        "SELECT COUNT(*) AS n FROM claim_node_links WHERE claim_id=? AND node_id=?",
        ("CLM_PARENT_REJECT", node_result["node_id"]),
    )["n"] == 1
    assert [
        proposal["proposal_id"] for proposal in audit["parent_placement_proposals"]
    ] == [parent_proposal_id]


def test_multiple_parent_suggestions_are_independently_reviewable(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    first_parent_id = db.add_node("First Parent", "Segment")
    second_parent_id = db.add_node("Second Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Multi-parent Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [first_parent_id, second_parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    first_proposal_id, second_proposal_id = node_result[
        "parent_placement_proposal_ids"
    ]

    manager.accept(first_proposal_id)
    manager.reject(second_proposal_id, "Only the first placement is approved")

    assert db.proposal(first_proposal_id)["status"] == "accepted"
    assert db.proposal(second_proposal_id)["status"] == "rejected"
    assert db.all(
        """SELECT to_node_id FROM node_relations
           WHERE from_node_id=? AND relation_type='part_of' ORDER BY to_node_id""",
        (node_result["node_id"],),
    ) == [{"to_node_id": first_parent_id}]


def test_duplicate_pending_parent_placement_proposal_is_reused(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Deduplicated Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Deduplicated Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    first_id = node_result["parent_placement_proposal_ids"][0]
    payload = db.proposal(first_id)["payload"]

    second_id = db.add_proposal(NODE_PARENT_PLACEMENT_PROPOSAL_TYPE, payload)

    assert second_id == first_id
    assert db.one(
        """SELECT COUNT(*) AS n FROM proposals
           WHERE proposal_type=? AND status='pending'""",
        (NODE_PARENT_PLACEMENT_PROPOSAL_TYPE,),
    )["n"] == 1


def test_missing_parent_fails_closed_at_parent_review_acceptance(tmp_path: Path):
    db, manager, _, node_result = accept_new_node(tmp_path, ["NODE_MISSING"])
    parent_proposal_id = node_result["parent_placement_proposal_ids"][0]

    with pytest.raises(ValueError, match="Unknown parent Node"):
        manager.accept(parent_proposal_id)

    assert db.proposal(parent_proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_missing_child_fails_closed_at_parent_review_acceptance(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Orphaned Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Deleted Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    parent_proposal_id = node_result["parent_placement_proposal_ids"][0]
    db.execute("DELETE FROM nodes WHERE node_id=?", (node_result["node_id"],))

    with pytest.raises(ValueError, match="Unknown child Node"):
        manager.accept(parent_proposal_id)

    assert db.proposal(parent_proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_inactive_parent_fails_closed_at_parent_review_acceptance(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Inactive Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Inactive-parent Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    parent_proposal_id = node_result["parent_placement_proposal_ids"][0]
    db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (parent_id,))

    with pytest.raises(ValueError, match="parent Node is not active"):
        manager.accept(parent_proposal_id)

    assert db.proposal(parent_proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_inactive_child_fails_closed_at_parent_review_acceptance(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Active Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Inactive Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    parent_proposal_id = node_result["parent_placement_proposal_ids"][0]
    db.execute(
        "UPDATE nodes SET status='inactive' WHERE node_id=?",
        (node_result["node_id"],),
    )

    with pytest.raises(ValueError, match="child Node is not active"):
        manager.accept(parent_proposal_id)

    assert db.proposal(parent_proposal_id)["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_self_parent_fails_closed(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    existing_id = db.add_node("Existing Identity", "Product")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Existing Identity",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [existing_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    assert node_result["node_id"] == existing_id

    with pytest.raises(ValueError, match="own parent"):
        manager.accept(node_result["parent_placement_proposal_ids"][0])

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_cycle_creation_fails_closed(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Cycle Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Cycle Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    db.add_relation(parent_id, "part_of", node_result["node_id"])

    with pytest.raises(ValueError, match="introduce a cycle"):
        manager.accept(node_result["parent_placement_proposal_ids"][0])

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1


def test_existing_parent_relation_fails_closed(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    parent_id = db.add_node("Duplicate Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Duplicate Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [parent_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    db.add_relation(node_result["node_id"], "part_of", parent_id)

    with pytest.raises(ValueError, match="Relation already exists"):
        manager.accept(node_result["parent_placement_proposal_ids"][0])

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1


def test_transitively_redundant_parent_placement_fails_closed(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    root_id = db.add_node("Root Parent", "Industry")
    middle_id = db.add_node("Middle Parent", "Segment")
    node_proposal_id = db.add_proposal(
        "new_node",
        {
            "canonical_name": "Redundant Child",
            "primary_type": "Product",
            "aliases": [],
            "suggested_parent_node_ids": [root_id],
            "related_claim_ids": [],
        },
    )
    manager = ProposalManager(cfg, db, NoChangeAnalyzer())
    node_result = manager.accept(node_proposal_id)
    db.add_relation(node_result["node_id"], "part_of", middle_id)
    db.add_relation(middle_id, "part_of", root_id)

    with pytest.raises(ValueError, match="transitively redundant"):
        manager.accept(node_result["parent_placement_proposal_ids"][0])

    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 2
