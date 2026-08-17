from __future__ import annotations

from pathlib import Path

import pytest

from pro_a.current_view import create_official_view
from pro_a.propagation import PropagationManager

from stability_helpers import add_source_and_claim, make_config


class ResultAnalyzer:
    available = True

    def __init__(self, result):
        self.result = result

    def review_impact(self, node, current_view_md, evidence, context):
        return self.result


class UnavailableAnalyzer:
    available = False


def no_change_result():
    return {
        "requires_change": False,
        "change_level": "none",
        "evidence_sufficiency": {"sufficient": True},
    }


def valid_theme_view(node_name: str, claim_ids: list[str]):
    claim_refs = "、".join(claim_ids)
    return {
        "one_line_conclusion": f"{node_name}的现有Evidence支持更新判断。",
        "core_logic": [f"{node_name}由新增Evidence支持（{claim_refs}）。"],
        "key_facts": [f"{node_name}获得新增事实Evidence（{claim_id}）。" for claim_id in claim_ids],
        "core_disagreements": [],
        "assumptions_to_verify": [],
        "investment_implication": f"{node_name}的投资含义需要结合后续Evidence持续验证。",
        "major_risks": [f"{node_name}的新增Evidence可能被后续资料推翻。"],
        "knowledge_gaps": [],
        "key_watch_items": [f"持续跟踪{node_name}对应Evidence。"],
        "recent_change": f"{node_name}判断更新。",
        "evidence_claim_ids": claim_ids,
        "type_specific": {},
    }


def test_impact_unique_key_includes_target_current_view_version(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Versioned Impact Node", "Theme")
    manager = PropagationManager(cfg, db, ResultAnalyzer(no_change_result()))

    first = manager.evaluate_node(
        batch_id="BATCH_1", trigger_type="source", trigger_id="SRC_1", node_id=node_id,
        path_type="direct", claim_ids=[],
    )
    duplicate = manager.evaluate_node(
        batch_id="BATCH_1", trigger_type="source", trigger_id="SRC_1", node_id=node_id,
        path_type="direct", claim_ids=[],
    )
    create_official_view(db, cfg, node_id, {"one_line_conclusion": "new target"}, "initial")
    after_new_version = manager.evaluate_node(
        batch_id="BATCH_1", trigger_type="current_view", trigger_id="VIEW_1", node_id=node_id,
        path_type="related", claim_ids=[],
    )

    assert first["status"] == "no_change"
    assert duplicate["status"] == "already_reviewed"
    assert after_new_version["status"] == "no_change"
    rows = db.all("SELECT target_view_version FROM impact_reviews WHERE batch_id='BATCH_1' ORDER BY created_at")
    assert len(rows) == 2
    assert len({row["target_view_version"] for row in rows}) == 2


def test_structural_impact_pauses_related_queue_when_llm_is_unavailable(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    source_id = db.add_node("Queue Source", "Theme")
    structural_id = db.add_node("Queue Parent", "Theme")
    related_id = db.add_node("Queue Related", "Theme")
    db.add_relation(source_id, "part_of", structural_id)
    add_source_and_claim(
        db,
        source_id="SRC_QUEUE_RELATION",
        claim_id="CLM_QUEUE_RELATION",
        node_id=source_id,
        source_rank="A",
        origin_type="primary",
        confidence=0.90,
    )
    db.add_relation(
        source_id,
        "related_to",
        related_id,
        evidence_claim_id="CLM_QUEUE_RELATION",
    )
    view = create_official_view(db, cfg, source_id, {"one_line_conclusion": "changed"}, "initial")
    manager = PropagationManager(cfg, db, UnavailableAnalyzer())

    manager.start_from_accepted_view(
        view,
        {"evidence_claim_ids": [], "previous_version": "", "change_level": "initial", "reason": "changed"},
        "BATCH_QUEUE",
    )

    structural = db.one("SELECT status,queue_order FROM impact_reviews WHERE node_id=?", (structural_id,))
    related = db.one("SELECT status,queue_order FROM impact_reviews WHERE node_id=?", (related_id,))
    assert structural == {"status": "needs_llm", "queue_order": 10}
    assert related == {"status": "pending", "queue_order": 20}


@pytest.mark.parametrize("change_level", ["material", "thesis"])
def test_insufficient_evidence_cannot_create_material_or_thesis_proposal(tmp_path: Path, change_level: str):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node(f"Insufficient {change_level}", "Theme")
    claim_id = f"CLM_{change_level}"
    add_source_and_claim(
        db,
        source_id=f"SRC_{change_level}",
        claim_id=claim_id,
        node_id=node_id,
        source_rank="D",
        origin_type="secondary",
        confidence=0.30,
    )
    result = {
        "requires_change": True,
        "change_level": change_level,
        "reason": "model requested a high-level change",
        "evidence_sufficiency": {
            "sufficient": True,
            "direct_primary_claim_ids": [claim_id],
            "decisive_primary_claim_ids": [claim_id],
            "invalidated_core_assumption": "assumption",
            "logic_chain_failure": "chain",
            "conclusion_change": "conclusion",
        },
        "proposed_current_view": {"one_line_conclusion": "must be blocked"},
    }
    manager = PropagationManager(cfg, db, ResultAnalyzer(result))

    reviewed = manager.evaluate_node(
        batch_id=f"BATCH_{change_level}", trigger_type="source", trigger_id=f"SRC_{change_level}",
        node_id=node_id, path_type="direct", claim_ids=[claim_id], trigger_source_id=f"SRC_{change_level}",
    )

    assert reviewed["status"] == "no_change"
    assert reviewed["proposal_id"] == ""
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0


def test_material_change_accepts_one_high_quality_direct_primary(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Sufficient Material", "Theme")
    add_source_and_claim(
        db, source_id="SRC_PRIMARY", claim_id="CLM_PRIMARY", node_id=node_id,
        source_rank="A", origin_type="primary", confidence=0.90,
    )
    result = {
        "requires_change": True,
        "change_level": "material",
        "reason": "direct primary evidence",
        "evidence_sufficiency": {
            "sufficient": True,
            "direct_primary_claim_ids": ["CLM_PRIMARY"],
        },
        "proposed_current_view": valid_theme_view("Sufficient Material", ["CLM_PRIMARY"]),
    }
    manager = PropagationManager(cfg, db, ResultAnalyzer(result))

    reviewed = manager.evaluate_node(
        batch_id="BATCH_PRIMARY", trigger_type="source", trigger_id="SRC_PRIMARY", node_id=node_id,
        path_type="direct", claim_ids=["CLM_PRIMARY"], trigger_source_id="SRC_PRIMARY",
    )

    assert reviewed["status"] == "proposed"
    assert reviewed["proposal_id"]


def test_thesis_change_accepts_two_independent_high_quality_sources_with_broken_assumption(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    node_id = db.add_node("Sufficient Thesis", "Theme")
    add_source_and_claim(
        db, source_id="SRC_A", claim_id="CLM_A", node_id=node_id,
        source_rank="S", origin_type="primary", confidence=0.90,
    )
    add_source_and_claim(
        db, source_id="SRC_B", claim_id="CLM_B", node_id=node_id,
        source_rank="A", origin_type="secondary", confidence=0.85,
    )
    result = {
        "requires_change": True,
        "change_level": "thesis",
        "reason": "two independent sources invalidate the core thesis",
        "evidence_sufficiency": {
            "sufficient": True,
            "invalidated_core_assumption": "the core demand assumption failed",
            "logic_chain_failure": "demand no longer supports utilization",
            "conclusion_change": "the investment direction reverses",
        },
        "proposed_current_view": valid_theme_view("Sufficient Thesis", ["CLM_A", "CLM_B"]),
    }
    manager = PropagationManager(cfg, db, ResultAnalyzer(result))

    reviewed = manager.evaluate_node(
        batch_id="BATCH_THESIS", trigger_type="source", trigger_id="SRC_A", node_id=node_id,
        path_type="direct", claim_ids=["CLM_A", "CLM_B"], trigger_source_id="SRC_A",
    )

    assert reviewed["status"] == "proposed"
    assert reviewed["proposal_id"]
