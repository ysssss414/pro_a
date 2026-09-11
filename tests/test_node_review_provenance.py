"""Operational review eligibility, independent of identity/operation advice."""
import copy
import sqlite3

import pytest

from pro_a.constants import NODE_TYPES
from pro_a.production_authorization import build_operational_node_operation_review
from pro_a.production_promotion import PromotionError
from test_operational_ingestion import _write_minimal_production


@pytest.fixture
def inputs(tmp_path):
    db = tmp_path / "production.db"
    _write_minimal_production(db)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO nodes VALUES(?,?,?,?)", ("NODE_KNOWN", "Known product", "Product", "active"))
    claim = {"claim_id": "CLM_1", "evidence_id": "EVD_1", "immutable_projection": {
        "statement": "The observed product is available.",
        "evidence_excerpt": "The observed product is available.",
        "evidence_pointer": "[[PAGE:1]]", "related_node_ids": []}}
    state = {"claim_id": "CLM_1", "review_admitted": True,
             "evidence_validation": {"bound": True, "authoritative_locator": {
                 "status": "resolved", "kind": "single_page", "locator": "PAGE:1", "authoritative": True}},
             "semantic_admission": {"overall_guard_disposition": "ADMISSIBLE"}}
    operation = {"operation_id": "OP_1", "candidate_id": "CAND_1", "candidate_kind": "node_candidate",
                 "operation": "DEFER", "executable": False, "claim_refs": ["CLM_1"],
                 "evidence_refs": ["EVD_1"], "source_sha256": "a" * 64,
                 "reason": "NO_EXPLICIT_NODE_CREATE_OR_REUSE_REVIEW",
                 "candidate": {"canonical_name": "New product", "primary_type": "Product", "aliases": [],
                               "candidate_kind": "normal", "quality_eligible": True,
                               "quality_validation": {"eligible": True}, "suggested_parent_node_ids": ["NODE_KNOWN"]}}
    return {"run_id": "INGEST_TEST", "source_sha256": "a" * 64, "claim_review_sha256": "b" * 64,
            "claim_review": {"run_id": "INGEST_TEST", "source_sha256": "a" * 64, "claims": [state]},
            "claims": [claim], "node_operations": [operation], "relation_operations": [],
            "production_path": db, "table_ineligible_claims": 0}


def run(inputs):
    before = copy.deepcopy(inputs)
    result = build_operational_node_operation_review(**inputs)
    assert inputs == before
    return result


@pytest.mark.parametrize("node_type", sorted(NODE_TYPES))
def test_all_node_types_with_grounded_retained_claim_are_reviewable(inputs, node_type):
    inputs["node_operations"][0]["candidate"]["primary_type"] = node_type
    result = run(inputs)
    assert result["records"][0]["supporting_claim_ids"] == ["CLM_1"]
    assert result["provenance_eligibility"]["records"][0]["classification"] == "REVIEWABLE_CLAIM_GROUNDED"


@pytest.mark.parametrize("advice", ["CREATE", "REUSE", "DEFER"])
def test_valid_provenance_survives_identity_advice(inputs, advice):
    candidate = inputs["node_operations"][0]["candidate"]
    if advice == "REUSE":
        candidate["canonical_name"] = "Known product"
    elif advice == "DEFER":
        candidate["quality_eligible"] = False
    result = run(inputs)
    assert result["records"][0]["suggested_operation"] == advice


@pytest.mark.parametrize("node_type", sorted(NODE_TYPES))
def test_no_support_excluded_for_every_type_and_defer_is_not_authority(inputs, node_type):
    op = inputs["node_operations"][0]
    op["candidate"]["primary_type"] = node_type
    op["claim_refs"] = []
    op["evidence_refs"] = []
    result = run(inputs)
    assert result["records"] == []
    excluded = result["audit_operations"]["node_unsupported"][0]
    assert excluded["operation"] == op
    assert excluded["record"]["suggested_operation"] == "DEFER"
    assert excluded["record"]["supporting_claim_ids"] == []
    assert result["audit_operations"]["parent_placement_excluded"][0]["candidate_id"] == op["candidate_id"]


@pytest.mark.parametrize("defect", ["not_retained", "unbound", "ambiguous", "non_authoritative", "blocked", "unknown_state", "missing_state"])
def test_claim_exists_but_is_not_qualifying_support(inputs, defect):
    state = inputs["claim_review"]["claims"][0]
    if defect == "not_retained":
        state["review_admitted"] = False
    elif defect == "unbound":
        state["evidence_validation"]["bound"] = False
    elif defect == "ambiguous":
        state["evidence_validation"]["authoritative_locator"]["status"] = "ambiguous"
    elif defect == "non_authoritative":
        state["evidence_validation"]["authoritative_locator"]["authoritative"] = False
    elif defect in {"blocked", "unknown_state"}:
        state["semantic_admission"]["overall_guard_disposition"] = "BLOCKED" if defect == "blocked" else "UNKNOWN"
    else:
        state.pop("evidence_validation")
    result = run(inputs)
    assert result["records"] == []
    excluded = result["audit_operations"]["node_unsupported"][0]
    assert excluded["record"]["supporting_claim_ids"] == ["CLM_1"]
    assert result["provenance_eligibility"]["records"][0]["nonqualifying_support_claim_ids"] == ["CLM_1"]


def test_review_required_is_not_human_rejection(inputs):
    inputs["claim_review"]["claims"][0]["semantic_admission"]["overall_guard_disposition"] = "REVIEW_REQUIRED"
    assert run(inputs)["records"][0]["supporting_claim_ids"] == ["CLM_1"]


def test_valid_and_invalid_support_preserves_visible_dependencies(inputs):
    other = copy.deepcopy(inputs["claims"][0]); other["claim_id"] = "CLM_2"
    inputs["claims"].append(other)
    state = copy.deepcopy(inputs["claim_review"]["claims"][0]); state["claim_id"] = "CLM_2"
    state["evidence_validation"]["bound"] = False
    inputs["claim_review"]["claims"].append(state)
    inputs["node_operations"][0]["claim_refs"].append("CLM_2")
    result = run(inputs)
    assert result["records"][0]["supporting_claim_ids"] == ["CLM_1", "CLM_2"]
    row = result["provenance_eligibility"]["records"][0]
    assert row["qualifying_claim_ids"] == ["CLM_1"]
    assert row["nonqualifying_support_claim_ids"] == ["CLM_2"]


def test_policy_rejection_never_resurrected_by_grounded_evidence(inputs):
    inputs["node_operations"][0]["operation"] = "REJECT"
    result = run(inputs)
    assert result["records"] == []
    assert result["audit_operations"]["node_rejected"] == inputs["node_operations"]
    assert result["provenance_eligibility"]["records"][0]["classification"] == "EXCLUDED_POLICY_REJECTION"


@pytest.mark.parametrize("locator", [None, {"status": "ambiguous"}, {"status": "resolved", "authoritative": True, "locator": "PAGE:1"}])
def test_direct_observation_evidence_cannot_opt_into_foundation_authority(inputs, locator):
    op = inputs["node_operations"][0]; op["claim_refs"] = []; op["evidence_refs"] = []
    op["candidate"].update(evidence_excerpt="Different raw observation.", evidence_validated=True,
                           validation={"source_locator": locator, "source_sha256": "a" * 64})
    result = run(inputs)
    assert result["records"] == []
    assert result["audit_operations"]["node_unsupported"][0]["operation"] == op
    assert result["provenance_eligibility"]["direct_evidence_only_authorized"] is False


def test_semantic_name_similarity_does_not_invent_claim_linkage(inputs):
    op = inputs["node_operations"][0]; op["claim_refs"] = []; op["evidence_refs"] = []
    op["candidate"]["canonical_name"] = "Automobile"
    inputs["claims"][0]["immutable_projection"].update(statement="A car is available.", evidence_excerpt="A car is available.")
    result = run(inputs)
    assert result["records"] == []
    assert result["audit_operations"]["node_unsupported"][0]["record"]["supporting_claim_ids"] == []


@pytest.mark.parametrize("field", ["run_id", "source_sha256"])
def test_cross_source_or_run_claim_state_cannot_qualify(inputs, field):
    inputs["claim_review"][field] = "OTHER"
    with pytest.raises(PromotionError, match="NODE_CLAIM_REVIEW_SOURCE_OR_RUN_MISMATCH"):
        run(inputs)
