import copy

import pytest

from pro_a.constants import NODE_TYPES
from pro_a.corpus_pilot import resolve_pdf_evidence_locator, _ordered_cross_page_spans
from pro_a.production_authorization import build_operational_node_operation_review
from test_operational_ingestion import _write_minimal_production


PAGES = {"PAGE:4": "Context. Alpha demand rises.", "PAGE:5": "Beta supply falls. Tail."}
EXCERPT = "Alpha demand rises.\n[[PAGE:5]]\nBeta supply falls."


def spans(excerpt=EXCERPT, pointer="[[PAGE:4]]", pages=None):
    pages = PAGES if pages is None else pages
    text = "\n".join(f"[[{key}]]\n{body}" for key, body in pages.items())
    locator = resolve_pdf_evidence_locator(text, excerpt, pointer)
    return _ordered_cross_page_spans(pages, locator, excerpt)


def test_structural_two_page_span():
    assert spans() == [
        {"order": 1, "locator": "PAGE:4", "text": "Alpha demand rises.", "exact_source_text": True},
        {"order": 2, "locator": "PAGE:5", "text": "Beta supply falls.", "exact_source_text": True},
    ]


def test_live_pattern_markdown_fragments_and_layout_normalization():
    pages = {"PAGE:7": "前文。\n供货情况：\n- **器件**：甲公司 \n- **引擎**：乙公司",
             "PAGE:8": "- **组装**：丙公司\n后文。"}
    excerpt = "供货情况：\n- **器件**：甲公司\n- **引擎**：乙公司\n[[PAGE:8]]\n- **组装**：丙公司"
    result = spans(excerpt, "[[PAGE:7]]", pages)
    assert [s["locator"] for s in result] == ["PAGE:7", "PAGE:8"]
    assert all(s["text"] in pages[s["locator"]] for s in result)


@pytest.mark.parametrize("excerpt", [
    "Missing.\n[[PAGE:5]]\nBeta supply falls.",
    "Alpha demand rises.\n[[PAGE:5]]\nMissing.",
    "Alpha demand rises.\n[[PAGE:5]]",  # Missing fragment, not an empty match.
    "[[PAGE:5]]\nBeta supply falls.",
    "Alpha demand rises.\n[[PAGE:3]]\nBeta supply falls.",
    "Beta supply falls.\n[[PAGE:5]]\nAlpha demand rises.",
    "Alpha demand rises.\n[[PAGE:x]]\nBeta supply falls.",
    "Alpha demand rises.\n[[PAGE:5]\nBeta supply falls.",
    "Alpha demand rose.\n[[PAGE:5]]\nBeta supply falls.",  # No fuzzy repair.
    "Alpha demand rises.\n[[PAGE:8]]\nBeta supply falls.",
])
def test_structural_invalid_fragments_fail_closed(excerpt):
    assert spans(excerpt) == []


def test_ambiguous_fragment_fails():
    assert spans(pages={**PAGES, "PAGE:4": "Alpha demand rises. Alpha demand rises."}) == []


def test_reversed_source_page_order_fails():
    assert spans(pages=dict(reversed(list(PAGES.items())))) == []


def test_no_distant_page_search():
    assert spans(pages={"PAGE:4": PAGES["PAGE:4"], "PAGE:8": PAGES["PAGE:5"]}) == []


def test_three_consecutive_structural_pages_use_existing_span_representation():
    result = spans("Alpha demand rises.\n[[PAGE:5]]\nMiddle.\n[[PAGE:6]]\nEnd.",
                   pages={"PAGE:4": PAGES["PAGE:4"], "PAGE:5": "Middle.", "PAGE:6": "End. Tail."})
    assert [s["locator"] for s in result] == ["PAGE:4", "PAGE:5", "PAGE:6"]


def test_existing_single_page_exact_unchanged():
    result = resolve_pdf_evidence_locator("[[PAGE:4]]\n" + PAGES["PAGE:4"], "Alpha demand rises.", "[[PAGE:4]]")
    assert result["status"] == "resolved"
    assert result["match_method"] == "provenance_raw_exact_substring"
    assert result["comparison_start"] == 10  # source_units retains the leading page newline.


def test_existing_layout_normalized_single_page_unchanged():
    result = resolve_pdf_evidence_locator("[[PAGE:4]]\nAlpha  demand\nrises.", "Alpha demand rises.", "[[PAGE:4]]")
    assert result["status"] == "resolved"
    assert result["match_method"] == "provenance_canonical_exact_substring"


def test_existing_unmarked_ordered_cross_page_unchanged():
    assert spans("Alpha demand rises. Beta supply falls.") == spans()


def review(tmp_path, node_type="ResearchQuestion", supported=False):
    db = tmp_path / "production.db"
    _write_minimal_production(db)
    operation = {"operation_id": "OP_Q", "candidate_id": "CAND_Q", "operation": "DEFER",
                 "candidate_kind": "node_candidate", "executable": False, "claim_refs": [],
                 "candidate": {"canonical_name": "Demand question", "primary_type": node_type,
                               "aliases": [], "suggested_parent_node_ids": ["PARENT"],
                               "quality_eligible": True, "quality_validation": {"eligible": True},
                               "candidate_kind": "research_question" if node_type == "ResearchQuestion" else "normal"}}
    claims = []
    if supported:
        operation["claim_refs"] = ["CLM_Q"]
        claims = [{"claim_id": "CLM_Q", "evidence_id": "EVD_Q",
            "review_admitted": True,
            "evidence_validation": {"bound": True, "authoritative_locator": {
                "status": "resolved", "kind": "single_page", "locator": "PAGE:1", "authoritative": True}},
            "semantic_admission": {"overall_guard_disposition": "REVIEW_REQUIRED"},
            "immutable_projection": {
            "statement": "Demand question is stated.", "evidence_excerpt": "Demand question is stated.",
            "evidence_pointer": "[[PAGE:1]]", "related_node_ids": []}}]
    before = copy.deepcopy(operation)
    result = build_operational_node_operation_review(
        run_id="INGEST_Q", source_sha256="a" * 64, claim_review_sha256="b" * 64,
        claim_review={"run_id": "INGEST_Q", "source_sha256": "a" * 64, "claims": claims},
        claims=claims, node_operations=[operation], relation_operations=[], production_path=db,
        table_ineligible_claims=0)
    assert operation == before
    return result


def test_research_question_valid_type_but_unsupported_excluded_with_parents(tmp_path):
    assert "ResearchQuestion" in NODE_TYPES
    result = review(tmp_path)
    assert result["records"] == []
    excluded = result["audit_operations"]["node_unsupported"]
    assert excluded[0]["candidate_id"] == "CAND_Q"
    assert excluded[0]["record"]["supporting_claim_ids"] == []
    assert excluded[0]["operation"]["claim_refs"] == []
    assert excluded[0]["reason"] == "RESEARCH_QUESTION_WITHOUT_DETERMINISTIC_EVIDENCE"
    parent = result["audit_operations"]["parent_placement_excluded"][0]
    assert parent["candidate_id"] == "CAND_Q" and parent["reason"].startswith("CHILD_NODE_EXCLUDED:")
    assert parent["executable"] is False


@pytest.mark.parametrize("node_type", ["Product", "Technology", "Company", "ResearchQuestion"])
def test_supported_node_types_remain_reviewable(tmp_path, node_type):
    result = review(tmp_path, node_type, supported=True)
    assert len(result["records"]) == 1
    assert result["records"][0]["supporting_claim_ids"] == ["CLM_Q"]
    assert "node_unsupported" not in result["audit_operations"]
