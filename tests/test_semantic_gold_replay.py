from __future__ import annotations

import copy

from pro_a.semantic_gold_replay import (
    build_post_hardening_replay,
    recompute_semantic_recommendations,
)


def _runtime_inputs(statement: str, nature: str = "data"):
    claim_id = "TEST_CLAIM"
    return {
        "run_id": "TEST_RUN",
        "source_sha256": "0" * 64,
        "extracted_bundle": {
            "claims": [{
                "claim_id": claim_id,
                "statement": statement,
                "attributed_to": "研究机构",
                "nature": nature,
                "fact_time": "2026",
                "status": "current",
            }],
        },
        "evidence_support": {
            "claims": [{
                "claim_id": claim_id,
                "bounded_context_candidates": [],
                "evidence_spans": [],
            }],
        },
        "quote_fidelity": {
            "claims": [{
                "claim_id": claim_id,
                "fidelity_status": "LAYOUT_NORMALIZED_EXACT_MATCH",
                "resolved_locator": {"authoritative": True, "locator": "PAGE:1"},
                "evidence_contract": {"canonical_ready_evidence": statement},
            }],
        },
        "table_boundary": {
            "decisions": [{
                "claim_id": claim_id,
                "review_eligible": True,
                "eligibility_decision": "ELIGIBLE",
                "decision_reason": "NARRATIVE_SUPPORT",
            }],
        },
    }


def test_runtime_replay_has_no_human_gold_input_and_preserves_review_mapping():
    inputs = _runtime_inputs("产品已量产，最高支持7200 MT/s。")
    replay = recompute_semantic_recommendations(**inputs)
    decision = replay["decisions"][0]
    assert replay["policy"]["human_gold_used_as_runtime_input"] is False
    assert decision["semantic_admission"]["atomicity_guard"]["status"] == "REVIEW_REQUIRED"
    assert decision["recommended_decision"] == "REVIEW"


def test_gold_labels_are_applied_only_after_runtime_recommendation():
    inputs = _runtime_inputs("产品已量产，最高支持7200 MT/s。")
    new_semantic = recompute_semantic_recommendations(**inputs)
    old_semantic = copy.deepcopy(new_semantic)
    old_semantic["decisions"][0]["recommended_decision"] = "KEEP"
    old_semantic["decisions"][0]["semantic_admission"].pop("atomicity_guard")
    old_semantic["decisions"][0]["semantic_admission"].pop("nature_consistency_guard")
    human_review = {
        "run_id": "TEST_RUN",
        "source_sha256": "0" * 64,
        "claim_decisions": [{
            "claim_id": "TEST_CLAIM",
            "human_semantic_decision": "NEEDS_REPAIR",
        }],
    }
    repair_draft = {
        "repair_entries": [{
            "original_claim_id": "TEST_CLAIM",
            "repair_reason_code": "ATOMICITY",
            "human_review_note": "Split event and specification.",
            "original_claim_snapshot": {"evidence_pointer": "[[PAGE:1]]"},
        }],
    }
    artifact = build_post_hardening_replay(
        old_semantic=old_semantic,
        new_semantic=new_semantic,
        human_review=human_review,
        repair_draft=repair_draft,
        quote_fidelity=inputs["quote_fidelity"],
    )
    row = artifact["per_claim"][0]
    assert row["old_recommendation"] == "KEEP"
    assert row["new_recommendation"] == "REVIEW"
    assert row["human_gold_label"] == "NEEDS_REPAIR"
    assert row["changed_guards"] == ["atomicity_guard"]
    assert artifact["atomicity_metrics"]["gold_recall"] == 1.0
