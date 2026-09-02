from __future__ import annotations

from pathlib import Path

from pro_a.analyzer import SourceAnalysis
from pro_a.analyzer import resolve_evidence_locator
from pro_a.corpus_pilot import extract_pilot_source
from pro_a.parsers import chunk_source_text
from pro_a.parsers import ParsedSource
from pro_a.pdf_layout import (
    PDF_LAYOUT_KINDS,
    SourceSegment,
    SourceSpan,
    project_pdf_layout,
    semantic_eligible_text,
)

from stability_helpers import make_config


VERSIONS = {"pymupdf": "1.28.2", "pymupdf_layout": "1.28.2"}


def _source(*pages: str) -> str:
    return "".join(
        f"\n[[PAGE:{page_number}]]\n{text}"
        for page_number, text in enumerate(pages, 1)
    )


def _block(kind: str, text: str, bbox: tuple[float, float, float, float]):
    return {"native_kind": kind, "text": text, "bbox": list(bbox)}


def _page(page: int, *blocks: dict):
    return {"page": page, "blocks": list(blocks)}


def _project(text: str, pages: list[dict]):
    return project_pdf_layout(text, pages, adapter_versions=VERSIONS)


def test_pdf_prose_only_preserves_semantic_input_exactly():
    source = _source("Opening prose with 2026 revenue of 42.5 and 18% growth.")
    projection = _project(source, [
        _page(1, _block("text", "Opening prose with 2026 revenue of 42.5 and 18% growth.",
                        (10, 10, 280, 40))),
    ])

    assert {segment.kind for segment in projection.segments} == {"narrative"}
    assert semantic_eligible_text(source, projection.segments) == source


def test_pdf_table_only_preserves_source_and_excludes_table_before_chunking():
    source = _source("Metric 2025 2026\nRevenue 100 140")
    projection = _project(source, [
        _page(1, _block("table", "Metric 2025 2026\nRevenue 100 140", (10, 10, 280, 80))),
    ])

    eligible = semantic_eligible_text(source, projection.segments)
    chunks = chunk_source_text(eligible, 80)
    assert source == _source("Metric 2025 2026\nRevenue 100 140")
    assert projection.segments[0].kind == "table"
    assert "Revenue 100 140" not in eligible
    assert "Revenue 100 140" not in "".join(chunks)
    assert "[[PAGE:1]]" in eligible


def test_pdf_prose_table_prose_keeps_both_narrative_regions():
    source = _source("Opening narrative.\nMetric 2025 2026\nRevenue 100 140\nClosing narrative.")
    projection = _project(source, [
        _page(
            1,
            _block("text", "Opening narrative.", (10, 10, 280, 30)),
            _block("table", "Metric 2025 2026\nRevenue 100 140", (10, 40, 280, 100)),
            _block("text", "Closing narrative.", (10, 110, 280, 140)),
        ),
    ])

    eligible = semantic_eligible_text(source, projection.segments)
    assert "Opening narrative." in eligible
    assert "Closing narrative." in eligible
    assert "Metric 2025 2026" not in eligible
    assert "Revenue 100 140" not in eligible


def test_borderless_table_miss_is_unknown_and_remains_eligible():
    source = _source("Metric 2025 2026\nRevenue 100 140")
    projection = _project(source, [
        _page(1, _block("picture", "Metric 2025 2026\nRevenue 100 140", (10, 10, 280, 80))),
    ])

    assert projection.segments[0].kind == "unknown"
    assert semantic_eligible_text(source, projection.segments) == source


def test_numerical_prose_is_never_suppressed_by_content():
    prose = "In 2024 revenue was 100, margin was 42%, and 2025 guidance is 140."
    source = _source(prose)
    projection = _project(source, [
        _page(1, _block("text", prose, (10, 10, 280, 80))),
    ])

    assert projection.segments[0].kind == "narrative"
    assert semantic_eligible_text(source, projection.segments) == source


def test_prose_like_table_is_controlled_by_parser_owned_table_signal():
    table = "Topic Commentary\nDemand Customers describe demand as strong"
    source = _source(table)
    projection = _project(source, [
        _page(1, _block("table", table, (10, 10, 280, 80))),
    ])

    assert projection.segments[0].kind == "table"
    assert "Customers describe demand as strong" not in semantic_eligible_text(
        source, projection.segments,
    )


def test_protected_layout_overlap_downgrades_table_to_unknown_and_keeps_content():
    source = _source("Table row 1 2\nNarrative beside the table.")
    projection = _project(source, [
        _page(
            1,
            _block("table", "Table row 1 2", (10, 10, 180, 80)),
            _block("text", "Narrative beside the table.", (160, 20, 290, 70)),
        ),
    ])

    table = next(segment for segment in projection.segments if segment.native_kind == "table")
    assert table.kind == "unknown"
    assert table.reason == "PROTECTED_LAYOUT_OVERLAP"
    assert semantic_eligible_text(source, projection.segments) == source


def test_complete_source_and_narrative_evidence_binding_are_unchanged():
    source = _source("Narrative evidence remains exact.\nMetric A B\nValue 1 2")
    before = resolve_evidence_locator(source, "Narrative evidence remains exact.")
    projection = _project(source, [
        _page(
            1,
            _block("text", "Narrative evidence remains exact.", (10, 10, 280, 30)),
            _block("table", "Metric A B\nValue 1 2", (10, 40, 280, 100)),
        ),
    ])

    assert source == _source("Narrative evidence remains exact.\nMetric A B\nValue 1 2")
    assert resolve_evidence_locator(source, "Narrative evidence remains exact.") == before
    assert before == {"status": "resolved", "locator": "PAGE:1"}


def test_repeated_layout_projection_has_stable_canonical_signature():
    source = _source("Before\nMetric A B\nValue 1 2\nAfter")
    pages = [_page(
        1,
        _block("text", "Before", (10, 10, 280, 30)),
        _block("table", "Metric A B\nValue 1 2", (10, 40, 280, 100)),
        _block("text", "After", (10, 110, 280, 140)),
    )]

    first = _project(source, pages)
    second = _project(source, pages)
    assert first.signature_sha256 == second.signature_sha256
    assert first.segments == second.segments


def test_ambiguous_canonical_binding_fails_open_without_guessing():
    source = _source("Repeated row\nRepeated row")
    projection = _project(source, [
        _page(1, _block("table", "Repeated row", (10, 10, 280, 80))),
    ])

    assert projection.segments[0].kind == "unknown"
    assert projection.segments[0].reason == "CANONICAL_BINDING_AMBIGUOUS"
    assert semantic_eligible_text(source, projection.segments) == source


def test_tables_remain_page_local_without_cross_page_reconstruction():
    source = _source("Header A\nRow A", "Header B\nRow B")
    projection = _project(source, [
        _page(1, _block("table", "Header A\nRow A", (10, 10, 280, 80))),
        _page(2, _block("table", "Header B\nRow B", (10, 10, 280, 80))),
    ])

    tables = [segment for segment in projection.segments if segment.kind == "table"]
    assert [segment.page for segment in tables] == [1, 2]
    assert all(segment.source_spans for segment in tables)
    assert all(len({span.page for span in segment.source_spans}) == 1 for segment in tables)
    eligible = semantic_eligible_text(source, projection.segments)
    assert "Row A" not in eligible and "Row B" not in eligible
    assert eligible.count("[[PAGE:") == 2
    assert set(PDF_LAYOUT_KINDS) == {"narrative", "table", "unknown"}


def test_phase3c_extraction_receives_filtered_text_while_evidence_uses_full_source(
    tmp_path, monkeypatch,
):
    cfg, _ = make_config(tmp_path)
    source_path = cfg.root / "clean.pdf"
    source_path.write_bytes(b"deterministic fixture identity")
    full_text = _source("Narrative evidence.\nMetric 2025 2026\nRevenue 100 140")
    table_start = full_text.index("Metric 2025 2026")
    table_end = full_text.index("Revenue 100 140") + len("Revenue 100 140")
    segment = SourceSegment(
        page=1,
        bbox=(10.0, 40.0, 280.0, 100.0),
        kind="table",
        text="Metric 2025 2026\nRevenue 100 140",
        order=1,
        source_spans=(SourceSpan(1, table_start, table_end),),
        native_kind="table",
        reason="PARSER_TABLE_CANONICAL_BINDING_RESOLVED",
    )
    diagnostics = {
        "format": "pdf", "parser": "pypdf", "locator_scheme": "PAGE",
        "file_size": source_path.stat().st_size, "unit_type": "page",
        "total_units": 1, "text_units": 1, "error_units": 0,
        "empty_units": 0, "extracted_chars": 47,
        "empty_extraction": False, "partial_parse": False,
        "image_only_or_no_extractable_text": False,
        "pdf_layout": {"signature_sha256": "fixture"},
    }
    parsed = ParsedSource(
        full_text,
        "pdf",
        diagnostics,
        (segment,),
        {"adapter": "fixture", "segments": []},
    )

    def fake_parse(path, *, include_semantic_segments=False):
        assert path == source_path
        assert include_semantic_segments is True
        return parsed

    captured = {}

    class StubLLM:
        available = True
        last_call_metadata = {}

        def json(self, system, user):  # pragma: no cover
            raise AssertionError("LLM must not be called by the fixture Analyzer")

    class CapturingAnalyzer:
        available = True

        def __init__(self, config, database):
            self.llm = StubLLM()

        def analyze_source(self, filename, text, mode):
            captured["text"] = text
            return SourceAnalysis(
                source_metadata={"title": "Fixture", "publication_time": "2026-09-01"},
                node_matches=[], node_candidates=[], source_references=[],
                relation_candidates=[],
                claims=[{
                    "statement": "Narrative evidence.",
                    "nature": "fact",
                    "evidence_excerpt": "Narrative evidence.",
                    "evidence_validated": True,
                    "validation": {"evidence_validated": True, "errors": []},
                    "structured": {},
                    "related_node_ids": [],
                    "related_candidate_names": [],
                }],
            )

    monkeypatch.setattr("pro_a.corpus_pilot.parse_source_with_diagnostics", fake_parse)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", CapturingAnalyzer)
    result = extract_pilot_source(
        source_path, cfg, output_dir=cfg.root / "stage1",
    )

    assert "Narrative evidence." in captured["text"]
    assert "Revenue 100 140" not in captured["text"]
    assert result["bundle"]["source"]["semantic_eligibility"][
        "applied_before_chunking"
    ] is True
    claim = result["bundle"]["claims"][0]
    assert claim["validation"]["source_locator"] == {
        "status": "resolved", "locator": "PAGE:1",
    }
    assert result["bundle"]["source"]["semantic_eligibility"][
        "canonical_source_chars"
    ] == len(full_text)
    assert Path(result["layout_sidecar_path"]).is_file()
    assert "Narrative evidence." not in str(
        result["bundle"]["source"]["layout_sidecar"]
    )
