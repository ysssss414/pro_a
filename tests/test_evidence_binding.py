"""Exact selector candidates, native-only normalization and explicit pointers."""
from dataclasses import replace

import pytest

from pro_a.evidence_binding import EvidenceBindingError, resolve_evidence_binding_v2
from pro_a.source_analysis_wire import build_source_evidence_catalog
from test_source_analysis_wire import context


def binding(text, **fields):
    ctx = context(text)
    catalog = build_source_evidence_catalog(ctx)
    selection = {"evidence_ref": catalog.units[0].evidence_ref, "evidence_pointer": "legacy pointer", **fields}
    return resolve_evidence_binding_v2(selection, catalog, ctx), ctx


def test_whole_unit_and_pointer_are_separate_from_locator():
    bound, ctx = binding("[[PAGE:3]]Alpha, beta; gamma.")
    assert bound.mode == "WHOLE_UNIT" and bound.evidence_excerpt == "Alpha, beta; gamma."
    assert bound.evidence_pointer == "legacy pointer" and bound.source_locator == "PAGE:3"
    assert ctx.piece.source_text[bound.source_start:bound.source_end] == bound.evidence_excerpt


def test_raw_subspan_unique_and_overlapping_occurrences():
    bound, _ = binding("Alpha beta gamma", evidence_selector="beta")
    assert bound.mode == "RAW_SUBSPAN" and bound.evidence_excerpt == "beta"
    with pytest.raises(EvidenceBindingError, match="AMBIGUOUS"):
        binding("banana", evidence_selector="ana")
    first, _ = binding("banana", evidence_selector="ana", evidence_occurrence=1)
    second, _ = binding("banana", evidence_selector="ana", evidence_occurrence=2)
    assert first.source_start == 1 and second.source_start == 3
    assert first.evidence_excerpt == second.evidence_excerpt == "ana"


@pytest.mark.parametrize("value", [0, -1, True, 1.0, "1", None, 3])
def test_invalid_occurrence_fail_closed(value):
    with pytest.raises(EvidenceBindingError, match="OCCURRENCE"):
        binding("x x", evidence_selector="x", evidence_occurrence=value)


@pytest.mark.parametrize("fields", [
    {"evidence_occurrence": 1}, {"evidence_mode": "RAW_SUBSPAN"}, {"evidence_mode": "NORMALIZED_SUBSPAN"},
    {"evidence_selector": ""}, {"evidence_selector": None}, {"evidence_mode": "unknown"},
    {"evidence_selector": "Alpha. Beta"}, {"evidence_selector": "Alpha gamma"},
    {"evidence_selector": "alpha", "evidence_mode": "RAW_SUBSPAN"},
    {"source_start": 1}, {"source_end": 2}, {"evidence_ref": "EV_FOREIGN"},
])
def test_invalid_selection_cross_parent_noncontiguous_and_model_offsets(fields):
    with pytest.raises(EvidenceBindingError):
        binding("Alpha. Beta gamma", **fields)


@pytest.mark.parametrize("text, selector, expected_raw", [
    (r"高容\&超高容占新扩产产能比例70%以上", "高容&超高容占新扩产产能比例70%以上", r"高容\&超高容占新扩产产能比例70%以上"),
    ("ＡＢＣ capacity", "ABC", "ＡＢＣ"),
    ("Alpha\n\t beta gamma", "Alpha beta", "Alpha\n\t beta"),
    ("Ⅳ units", "IV", "Ⅳ"),
])
def test_normalized_subspan_has_exact_raw_origin_and_legacy_canonical_value(text, selector, expected_raw):
    bound, ctx = binding(text, evidence_selector=selector)
    assert bound.mode == "NORMALIZED_SUBSPAN" and bound.evidence_excerpt == selector
    assert ctx.piece.source_text[bound.source_start:bound.source_end] == expected_raw
    assert bound.evidence_pointer == "legacy pointer"


def test_raw_match_precedence_and_normalized_repeated_candidates():
    bound, _ = binding("Ａ A", evidence_selector="A")
    assert bound.mode == "RAW_SUBSPAN" and bound.source_start == 2
    with pytest.raises(EvidenceBindingError, match="AMBIGUOUS"):
        binding("Ａ Ａ", evidence_selector="A")
    bound, _ = binding("Ａ Ａ", evidence_selector="A", evidence_occurrence=2)
    assert bound.mode == "NORMALIZED_SUBSPAN" and bound.source_start == 2


@pytest.mark.parametrize("text, selector", [("e\u0301", "é"), ("Ⅳ", "I"), ("a-b", "a b"), ("A", "a")])
def test_unsupported_composition_partial_expansion_and_fuzzy_matching_fail(text, selector):
    with pytest.raises(EvidenceBindingError):
        binding(text, evidence_selector=selector)


def test_forged_catalog_span_is_rejected():
    ctx = context("Alpha beta")
    catalog = build_source_evidence_catalog(ctx)
    forged = replace(catalog, units=(replace(catalog.units[0], source_start=1),))
    with pytest.raises(EvidenceBindingError, match="CATALOG_BINDING_MISMATCH"):
        resolve_evidence_binding_v2({"evidence_ref": catalog.units[0].evidence_ref}, forged, ctx)
