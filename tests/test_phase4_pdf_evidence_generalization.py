import copy
import json
from pathlib import Path

import pytest

from pro_a.corpus_pilot import (
    _ordered_cross_page_spans,
    normalize_pdf_span_text,
    resolve_pdf_evidence_locator,
)


def bind(pages, quote, pointer="[[PAGE:4]]", layout=None):
    text = "\n".join(f"[[{key}]]\n{body}" for key, body in pages.items())
    locator = resolve_pdf_evidence_locator(text, quote, pointer, layout_sidecar=layout)
    spans = _ordered_cross_page_spans(pages, locator, quote, layout_sidecar=layout)
    return locator, spans


@pytest.mark.parametrize("source,quote", [
    ("虚构驿站记录显示，\n青色风铃保持静止。", "虚构驿站记录显示，青色风铃保持静止。"),
    ("虚构道具包括 pebble、\nribbon、paper风车。", "虚构道具包括 pebble、ribbon、paper风车。"),
    ("虚构道具包括 pebble、 \r\n  ribbon。", "虚构道具包括 pebble、ribbon。"),
])
def test_chinese_separator_physical_wrap(source, quote):
    locator, spans = bind({"PAGE:4": source}, quote)
    assert locator["status"] == "resolved"
    assert locator["match_method"] == "provenance_pdf_normalized_exact_substring"
    assert spans == []


@pytest.mark.parametrize("source,quote", [
    ("X731", "X932"), ("37um", "43um"), ("473枚纸币", "829枚纸币"),
    ("17cm", "17kg"), ("甲公司", "乙公司"), ("Alpha Beta", "Beta Alpha"),
    ("AB 12", "AB12"), ("12 34", "1234"), ("Na Cl", "NaCl"),
    ("N m", "Nm"), ("A/B", "AB"), ("A,B", "AB"),
    ("Alpha,\nBeta", "Alpha,Beta"), ("Alpha Beta", "AlphaBeta"),
    ("型号，AB 12", "型号，AB12"), ("型号、AB 12", "型号、AB12"),
])
def test_meaningful_distinctions_are_not_collapsed(source, quote):
    assert normalize_pdf_span_text(source) != normalize_pdf_span_text(quote)
    locator, spans = bind({"PAGE:4": source}, quote)
    assert locator["status"] != "resolved" and spans == []


def test_repeated_single_page_quote_is_ambiguous():
    locator, spans = bind({"PAGE:4": "甲，\n47型。甲，\n47型。"}, "甲，47型。")
    assert locator["status"] == "ambiguous" and spans == []


PAGES = {"PAGE:4": "Context. Alpha demand rises.", "PAGE:5": "Beta supply falls. Tail."}
QUOTE = "Alpha demand rises. Beta supply falls."


@pytest.mark.parametrize("pointer", ["[[PAGE:4]]", "[[PAGE:4]][[PAGE:5]]"])
def test_adjacent_plain_and_sequence_pointers(pointer):
    locator, spans = bind(PAGES, QUOTE, pointer)
    assert locator["reason"] == "cross_page_span"
    assert [s["locator"] for s in spans] == ["PAGE:4", "PAGE:5"]
    assert all(s["exact_source_text"] and s["text"] in PAGES[s["locator"]] for s in spans)


@pytest.mark.parametrize("pointer", [
    "[[PAGE:5]][[PAGE:4]]", "[[PAGE:4]][[PAGE:4]]", "[[PAGE:4]][[PAGE:6]]",
    "[[PAGE:4]][[PAGE:x]]", "[[PAGE:4]][[PAGE:5]", "[[PAGE:0]][[PAGE:1]]",
    "[[PAGE:4]]garbage[[PAGE:5]]", "[[PAGE:4]][[PAGE:05]]",
])
def test_invalid_pointer_sequence_fails_explicitly(pointer):
    locator, spans = bind(PAGES, QUOTE, pointer)
    assert locator["reason"] == "invalid_page_sequence" and spans == []


@pytest.mark.parametrize("pages,quote", [
    ({**PAGES, "PAGE:4": "Missing prefix."}, QUOTE),
    ({**PAGES, "PAGE:5": "Missing suffix."}, QUOTE),
    ({"PAGE:4": PAGES["PAGE:4"], "PAGE:5": "Other.", "PAGE:6": PAGES["PAGE:5"]}, QUOTE),
    (dict(reversed(list(PAGES.items()))), QUOTE),
    (PAGES, "Beta supply falls. Alpha demand rises."),
    ({**PAGES, "PAGE:4": "Alpha demand rises. Alpha demand rises."}, QUOTE),
    ({**PAGES, "PAGE:5": "Beta supply falls. Beta supply falls."}, QUOTE),
])
def test_incomplete_reversed_or_ambiguous_continuations_fail(pages, quote):
    locator, spans = bind(pages, quote)
    assert locator["status"] != "resolved" and spans == []


def layout_fixture():
    def seg(page, order, text, bbox, kind="narrative", native="text"):
        return {"page": page, "order": order, "text": text, "bbox": bbox,
                "kind": kind, "native_kind": native}
    return {"segments": [
        seg(4, 1, "axis 0 100", [0, 10, 100, 50], "unknown", "picture"),
        seg(4, 2, PAGES["PAGE:4"], [0, 80, 100, 90]),
        seg(4, 3, "Footer", [0, 95, 100, 99], "unknown", "page-footer"),
        seg(5, 1, "Header", [0, 0, 100, 10], "unknown", "page-header"),
        seg(5, 2, PAGES["PAGE:5"], [0, 15, 100, 25]),
    ]}


LAYOUT_PAGES = {"PAGE:4": PAGES["PAGE:4"] + "\naxis 0 100\nFooter",
                "PAGE:5": "Header\n" + PAGES["PAGE:5"]}


def test_layout_reordering_uses_grounded_edges_without_deleting_source():
    pages, layout = copy.deepcopy(LAYOUT_PAGES), layout_fixture()
    before = copy.deepcopy((pages, layout))
    locator, spans = bind(pages, QUOTE, layout=layout)
    assert locator["layout_continuation"] is True and len(spans) == 2
    assert all("layout_boundary" in s and s["text"] in pages[s["locator"]] for s in spans)
    assert (pages, layout) == before


@pytest.mark.parametrize("mutation", ["interior_picture", "interior_unknown", "unbound_text",
                                         "duplicate_order", "missing_bbox", "missing_second_page"])
def test_layout_is_not_permission_to_skip_arbitrary_content(mutation):
    layout = layout_fixture()
    if mutation.startswith("interior"):
        layout["segments"][0]["bbox"] = [0, 91, 100, 94]
        if mutation == "interior_unknown":
            layout["segments"][0]["native_kind"] = "unknown"
    elif mutation == "unbound_text":
        layout["segments"][1]["text"] += " invented"
    elif mutation == "duplicate_order":
        layout["segments"][0]["order"] = 2
    elif mutation == "missing_bbox":
        layout["segments"][0].pop("bbox")
    else:
        layout["segments"] = [s for s in layout["segments"] if s["page"] == 4]
    assert bind(LAYOUT_PAGES, QUOTE, layout=layout)[1] == []


def test_partial_layout_cannot_authorize_a_span():
    assert bind(LAYOUT_PAGES, QUOTE)[1] == []
    assert bind({**LAYOUT_PAGES, "PAGE:5": "Header\nMissing."}, QUOTE, layout=layout_fixture())[1] == []


def test_single_page_evidence_does_not_expand():
    locator, spans = bind(PAGES, "Alpha demand rises.", layout=layout_fixture())
    assert locator["status"] == "resolved" and locator["locator"] == "PAGE:4" and spans == []


def test_synthetic_four_claim_evidence_patterns():
    fixture = json.loads((Path(__file__).parent / "fixtures/phase4_gate_c_pdf_evidence.json").read_bytes())
    for claim in fixture["claims"]:
        locator, spans = bind(fixture["pages"], claim["quote"], claim["pointer"], fixture["layout"])
        if claim["expected_pages"]:
            assert [s["locator"] for s in spans] == claim["expected_pages"]
            assert normalize_pdf_span_text("\n".join(s["text"] for s in spans)) == normalize_pdf_span_text(claim["quote"])
        else:
            assert locator["status"] == "resolved"


def test_table_boundary_consumes_declared_locator_normalization():
    from pro_a.table_claim_safety import _comparison_normalizer
    pages = {"PAGE:4": "前文，\n47型。后文收入2093 年为53 枚。"}
    quote = "后文收入2093年为53枚。"
    locator, _ = bind(pages, quote)
    normalizer = _comparison_normalizer(locator)
    # source_units retains a leading newline; normalization removes it.
    assert normalizer(pages["PAGE:4"])[locator["comparison_start"]:locator["comparison_end"]] == normalizer(quote)
    historical = {**locator, "canonicalization": locator["canonicalization"].replace("+cjk_separator_linewrap", "")}
    old_normalizer = _comparison_normalizer(historical)
    assert old_normalizer(pages["PAGE:4"]) != normalizer(pages["PAGE:4"])
    assert old_normalizer("前文，\n47型。") == "前文, 47型"


def test_incomplete_span_stays_non_authoritative_in_fidelity_contract():
    from pro_a.corpus_pilot import _gate_a_claim_record
    pages = {"PAGE:4": PAGES["PAGE:4"], "PAGE:5": "Missing."}
    claim = {"claim_id": "C_PARTIAL", "statement": QUOTE, "evidence_excerpt": QUOTE,
             "evidence_pointer": "[[PAGE:4]][[PAGE:5]]"}
    result = _gate_a_claim_record(claim, list(pages.items()), pages, {})
    assert result["resolved_locator"] is None
    assert result["evidence_contract"]["canonical_ready_evidence"] is None
