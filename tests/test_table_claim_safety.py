from __future__ import annotations

import copy
import json

from pro_a.corpus_pilot import build_bounded_local_subspan
from pro_a.parsers import source_units
from pro_a.table_claim_safety import (
    TABLE_CLAIM_ELIGIBLE_FAIL_OPEN,
    TABLE_DERIVED_CLAIM_INELIGIBLE,
    apply_table_claim_safety_boundary_v1,
)


def _canonical(*pages: str) -> str:
    return "\n".join(
        f"\n[[PAGE:{index}]]\n{text}" for index, text in enumerate(pages, 1)
    )


def _page_body(canonical: str, page: int) -> str:
    return dict(source_units(canonical))[f"PAGE:{page}"]


def _claim(
    canonical: str,
    evidence: str,
    *,
    page: int = 1,
    claim_id: str = "CLM_TEST",
    resolved: bool = True,
) -> dict:
    body = _page_body(canonical, page)
    start = body.find(evidence)
    locator = (
        {
            "status": "resolved",
            "locator": f"PAGE:{page}",
            "match_method": "provenance_raw_exact_substring",
            "comparison_start": start,
            "comparison_end": start + len(evidence),
        }
        if resolved
        else {"status": "unresolved", "match_method": "none"}
    )
    return {
        "claim_id": claim_id,
        "statement": "This field must not affect origin eligibility.",
        "attributed_to": "This field must not affect origin eligibility.",
        "evidence_excerpt": evidence,
        "validation": {"source_locator": locator, "model_confidence": 1.0},
        "phase3c_evidence": {
            "resolved_locator": (
                {
                    "status": "resolved",
                    "kind": "single_page",
                    "locator": f"PAGE:{page}",
                    "source": "deterministic_source_binding",
                    "authoritative": True,
                }
                if resolved
                else None
            )
        },
    }


def _words(*values: tuple[str, list[float]]) -> list[dict]:
    return [
        {
            "text": text,
            "bbox": bbox,
            "block": 0,
            "line": 0,
            "word": index,
        }
        for index, (text, bbox) in enumerate(values)
    ]


def _segment(
    *,
    page: int,
    native_kind: str,
    bbox: list[float],
    text: str,
    kind: str | None = None,
    reason: str = "",
    order: int = 1,
) -> dict:
    return {
        "page": page,
        "order": order,
        "bbox": bbox,
        "kind": kind or ("narrative" if native_kind == "text" else "unknown"),
        "native_kind": native_kind,
        "reason": reason,
        "text": text,
        "canonical_source_spans": [],
    }


def _run(canonical: str, claim: dict, segments: list[dict], word_pages: dict) -> dict:
    return apply_table_claim_safety_boundary_v1(
        canonical_source_text=canonical,
        layout_sidecar={"segments": segments},
        claims=[claim],
        word_pages=word_pages,
    )


def _table_fixture(*, effective_kind: str = "unknown", reason: str = ""):
    evidence = "Revenue 10 20"
    canonical = _canonical(evidence)
    claim = _claim(canonical, evidence)
    table = _segment(
        page=1,
        native_kind="table",
        bbox=[0.0, 0.0, 100.0, 100.0],
        text=evidence,
        kind=effective_kind,
        reason=reason,
    )
    words = {
        1: _words(
            ("Revenue", [5.0, 10.0, 35.0, 20.0]),
            ("10", [40.0, 10.0, 50.0, 20.0]),
            ("20", [55.0, 10.0, 65.0, 20.0]),
        )
    }
    return canonical, claim, table, words


def test_unique_authoritative_evidence_inside_native_table_is_ineligible():
    canonical, claim, table, words = _table_fixture()
    result = _run(canonical, claim, [table], words)
    decision = result["decisions"][0]
    assert decision["eligibility_decision"] == TABLE_DERIVED_CLAIM_INELIGIBLE
    assert decision["native_table_bbox"] == [0.0, 0.0, 100.0, 100.0]


def test_authoritative_narrative_evidence_is_eligible():
    evidence = "Narrative fact"
    canonical = _canonical(evidence)
    claim = _claim(canonical, evidence)
    narrative = _segment(
        page=1,
        native_kind="text",
        bbox=[0.0, 0.0, 100.0, 30.0],
        text=evidence,
        kind="narrative",
    )
    words = {1: _words(("Narrative", [5.0, 5.0, 35.0, 15.0]), ("fact", [40.0, 5.0, 55.0, 15.0]))}
    result = _run(canonical, claim, [narrative], words)
    assert result["decisions"][0]["eligibility_decision"] == TABLE_CLAIM_ELIGIBLE_FAIL_OPEN


def test_native_table_with_protected_overlap_fails_open():
    canonical, claim, table, words = _table_fixture()
    protected = _segment(
        page=1,
        native_kind="text",
        bbox=[90.0, 0.0, 120.0, 100.0],
        text="different protected text",
        kind="narrative",
        order=2,
    )
    result = _run(canonical, claim, [table, protected], words)
    decision = result["decisions"][0]
    assert decision["review_eligible"] is True
    assert decision["checks"]["native_table_protected_overlap_count"] == 1


def test_ambiguous_canonical_occurrence_on_authoritative_page_fails_open():
    evidence = "Revenue 10 20"
    canonical = _canonical(f"{evidence}\n{evidence}")
    claim = _claim(canonical, evidence)
    table = _segment(
        page=1,
        native_kind="table",
        bbox=[0.0, 0.0, 100.0, 100.0],
        text=evidence,
    )
    words = {
        1: _words(
            ("Revenue", [5.0, 10.0, 35.0, 20.0]),
            ("10", [40.0, 10.0, 50.0, 20.0]),
            ("20", [55.0, 10.0, 65.0, 20.0]),
            ("Revenue", [5.0, 30.0, 35.0, 40.0]),
            ("10", [40.0, 30.0, 50.0, 40.0]),
            ("20", [55.0, 30.0, 65.0, 40.0]),
        )
    }
    result = _run(canonical, claim, [table], words)
    decision = result["decisions"][0]
    assert decision["review_eligible"] is True
    assert decision["checks"]["canonical_authoritative_page_occurrence_count"] == 2


def test_whole_table_binding_failure_does_not_block_unique_claim_geometry():
    canonical, claim, table, words = _table_fixture(
        effective_kind="unknown", reason="CANONICAL_BINDING_UNRESOLVED"
    )
    result = _run(canonical, claim, [table], words)
    decision = result["decisions"][0]
    assert decision["eligibility_decision"] == TABLE_DERIVED_CLAIM_INELIGIBLE
    assert decision["native_table_reason"] == "CANONICAL_BINDING_UNRESOLVED"


def test_same_text_in_another_table_is_disambiguated_by_authoritative_page():
    evidence = "Revenue 10 20"
    canonical = _canonical(evidence, evidence)
    claim = _claim(canonical, evidence, page=1)
    segments = [
        _segment(page=1, native_kind="table", bbox=[0.0, 0.0, 100.0, 50.0], text=evidence),
        _segment(page=2, native_kind="table", bbox=[0.0, 0.0, 100.0, 50.0], text=evidence),
    ]
    words = {1: _words(("Revenue", [5.0, 5.0, 35.0, 15.0]), ("10", [40.0, 5.0, 50.0, 15.0]), ("20", [55.0, 5.0, 65.0, 15.0]))}
    result = _run(canonical, claim, segments, words)
    assert result["decisions"][0]["eligibility_decision"] == TABLE_DERIVED_CLAIM_INELIGIBLE


def test_competing_narrative_occurrence_fails_open():
    evidence = "Revenue 10 20"
    canonical = _canonical(evidence, evidence)
    claim = _claim(canonical, evidence, page=1)
    segments = [
        _segment(page=1, native_kind="table", bbox=[0.0, 0.0, 100.0, 50.0], text=evidence),
        _segment(page=2, native_kind="text", bbox=[0.0, 0.0, 100.0, 50.0], text=evidence, kind="narrative"),
    ]
    words = {1: _words(("Revenue", [5.0, 5.0, 35.0, 15.0]), ("10", [40.0, 5.0, 50.0, 15.0]), ("20", [55.0, 5.0, 65.0, 15.0]))}
    result = _run(canonical, claim, segments, words)
    decision = result["decisions"][0]
    assert decision["review_eligible"] is True
    assert decision["checks"]["competing_narrative_occurrence_count"] == 1


def test_authoritative_narrative_remains_eligible_when_same_fact_is_in_table():
    evidence = "Revenue 10 20"
    canonical = _canonical(evidence, evidence)
    claim = _claim(canonical, evidence, page=1)
    segments = [
        _segment(page=1, native_kind="text", bbox=[0.0, 0.0, 100.0, 50.0], text=evidence, kind="narrative"),
        _segment(page=2, native_kind="table", bbox=[0.0, 0.0, 100.0, 50.0], text=evidence),
    ]
    words = {1: _words(("Revenue", [5.0, 5.0, 35.0, 15.0]), ("10", [40.0, 5.0, 50.0, 15.0]), ("20", [55.0, 5.0, 65.0, 15.0]))}
    result = _run(canonical, claim, segments, words)
    assert result["decisions"][0]["eligibility_decision"] == TABLE_CLAIM_ELIGIBLE_FAIL_OPEN


def test_unresolved_evidence_locator_fails_open():
    evidence = "Revenue 10 20"
    canonical = _canonical(evidence)
    claim = _claim(canonical, evidence, resolved=False)
    result = _run(canonical, claim, [], {})
    assert result["decisions"][0]["eligibility_decision"] == TABLE_CLAIM_ELIGIBLE_FAIL_OPEN


def test_repeated_boundary_replay_is_deterministic():
    canonical, claim, table, words = _table_fixture()
    first = _run(canonical, claim, [table], words)
    second = _run(canonical, claim, [table], words)
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert encode(first) == encode(second)


def test_canonical_binding_fail_open_path_has_no_upstream_suppression_leak():
    canonical, claim, table, words = _table_fixture(
        effective_kind="unknown", reason="CANONICAL_BINDING_UNRESOLVED"
    )
    result = _run(canonical, claim, [table], words)
    assert result["upstream_effective_table_suppression_leak_count"] == 0


def test_raw_claim_and_evidence_are_not_mutated():
    canonical, claim, table, words = _table_fixture()
    frozen = copy.deepcopy(claim)
    result = _run(canonical, claim, [table], words)
    assert claim == frozen
    assert result["raw_claims_unchanged"] is True
    assert result["raw_claims_sha256_pre"] == result["raw_claims_sha256_post"]


def test_local_subspan_evidence_behavior_remains_unchanged():
    raw = "A" * 600 + "EVIDENCE" + "B" * 600
    assert build_bounded_local_subspan(raw, 600, 608, "before") == "A" * 500
    assert build_bounded_local_subspan(raw, 600, 608, "after") == "B" * 500
