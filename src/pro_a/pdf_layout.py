"""Authoritative PDF layout sidecar for semantic-input eligibility.

PyMuPDF supplies structure only. The complete pypdf Source text remains the
canonical provenance and Evidence view; table removal masks only exact spans
bound back to that canonical text.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PDF_LAYOUT_KINDS = ("narrative", "table", "unknown")
PROTECTED_LAYOUT_KINDS = {"text", "list-item", "section-header", "caption"}
PYMUPDF_VERSION = "1.28.2"
PYMUPDF_LAYOUT_VERSION = "1.28.2"
PDF_LAYOUT_ADAPTER = "pymupdf_layout.Page.get_layout"

_PAGE_MARKER = re.compile(r"^\[\[PAGE:([1-9]\d*)\]\]", re.MULTILINE)


@dataclass(frozen=True)
class SourceSpan:
    page: int
    start: int
    end: int


@dataclass(frozen=True)
class SourceSegment:
    page: int
    bbox: tuple[float, float, float, float]
    kind: str
    text: str
    order: int
    source_spans: tuple[SourceSpan, ...] = ()
    native_kind: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PdfLayoutProjection:
    segments: tuple[SourceSegment, ...]
    signature_sha256: str
    adapter_versions: Mapping[str, str]


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bbox(value: Sequence[Any]) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise ValueError("PDF layout bbox must contain four coordinates")
    return tuple(round(float(item), 4) for item in value)  # type: ignore[return-value]


def _intersection_area(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return width * height


def _page_source_ranges(text: str) -> dict[int, tuple[int, int]]:
    markers = list(_PAGE_MARKER.finditer(text))
    ranges: dict[int, tuple[int, int]] = {}
    for index, marker in enumerate(markers):
        page = int(marker.group(1))
        if page in ranges:
            raise ValueError(f"duplicate canonical PAGE marker: {page}")
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        ranges[page] = (marker.end(), end)
    return ranges


def _compact_with_map(value: str) -> tuple[str, list[int]]:
    compact: list[str] = []
    source_indices: list[int] = []
    for index, char in enumerate(value):
        for normalized in unicodedata.normalize("NFKC", char):
            if normalized.isspace():
                continue
            compact.append(normalized)
            source_indices.append(index)
    return "".join(compact), source_indices


def _compact(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKC", value or "")
        if not char.isspace()
    )


def _all_occurrences(haystack: str, needle: str) -> list[tuple[int, int]]:
    if not needle:
        return []
    occurrences: list[tuple[int, int]] = []
    start = 0
    while True:
        found = haystack.find(needle, start)
        if found < 0:
            return occurrences
        occurrences.append((found, found + len(needle)))
        start = found + 1


def _ordered_bindings(
    candidates: Sequence[Sequence[tuple[int, int]]],
    *,
    limit: int = 2,
) -> list[list[tuple[int, int]]]:
    solutions: list[list[tuple[int, int]]] = []

    def visit(index: int, after: int, selected: list[tuple[int, int]]) -> None:
        if len(solutions) >= limit:
            return
        if index == len(candidates):
            solutions.append(list(selected))
            return
        for occurrence in candidates[index]:
            if occurrence[0] < after:
                continue
            selected.append(occurrence)
            visit(index + 1, occurrence[1], selected)
            selected.pop()

    visit(0, 0, [])
    return solutions


def _bind_table_text(
    *,
    page: int,
    canonical_text: str,
    page_start: int,
    page_end: int,
    layout_text: str,
) -> tuple[tuple[SourceSpan, ...], str]:
    page_text = canonical_text[page_start:page_end]
    normalized_page, source_indices = _compact_with_map(page_text)
    lines = [_compact(line) for line in (layout_text or "").splitlines()]
    lines = [line for line in lines if line]
    if not normalized_page or not lines:
        return (), "CANONICAL_BINDING_UNRESOLVED"
    full_occurrences = _all_occurrences(normalized_page, _compact(layout_text))
    if len(full_occurrences) == 1:
        start, end = full_occurrences[0]
        return (
            SourceSpan(
                page=page,
                start=page_start + source_indices[start],
                end=page_start + source_indices[end - 1] + 1,
            ),
        ), "PARSER_TABLE_CANONICAL_BINDING_RESOLVED"
    candidates = [_all_occurrences(normalized_page, line) for line in lines]
    if any(not occurrences for occurrences in candidates):
        return (), "CANONICAL_BINDING_UNRESOLVED"
    if all(len(occurrences) == 1 for occurrences in candidates):
        spans = tuple(
            SourceSpan(
                page=page,
                start=page_start + source_indices[start],
                end=page_start + source_indices[end - 1] + 1,
            )
            for ((start, end),) in candidates
        )
        return spans, "PARSER_TABLE_CANONICAL_BINDING_RESOLVED"
    solutions = _ordered_bindings(candidates)
    if not solutions:
        return (), "CANONICAL_BINDING_UNRESOLVED"
    if len(solutions) > 1:
        return (), "CANONICAL_BINDING_AMBIGUOUS"
    spans = tuple(
        SourceSpan(
            page=page,
            start=page_start + source_indices[start],
            end=page_start + source_indices[end - 1] + 1,
        )
        for start, end in solutions[0]
    )
    return spans, "PARSER_TABLE_CANONICAL_BINDING_RESOLVED"


def project_pdf_layout(
    canonical_text: str,
    layout_pages: Iterable[Mapping[str, Any]],
    *,
    adapter_versions: Mapping[str, str],
) -> PdfLayoutProjection:
    """Project parser-owned layout blocks onto the immutable canonical Source."""
    page_ranges = _page_source_ranges(canonical_text)
    segments: list[SourceSegment] = []
    signature: list[dict[str, Any]] = []

    for page_row in layout_pages:
        page = int(page_row["page"])
        if page not in page_ranges:
            raise ValueError(f"layout page {page} is absent from canonical Source")
        blocks = [
            {
                "index": index,
                "bbox": _bbox(block["bbox"]),
                "native_kind": str(block.get("native_kind") or "unknown"),
                "text": str(block.get("text") or ""),
            }
            for index, block in enumerate(page_row.get("blocks") or [])
        ]
        classified: dict[int, tuple[str, tuple[SourceSpan, ...], str]] = {}
        table_signature: list[dict[str, Any]] = []
        for block in blocks:
            native_kind = block["native_kind"]
            if native_kind in PROTECTED_LAYOUT_KINDS:
                classified[block["index"]] = (
                    "narrative", (), "PARSER_NATIVE_NARRATIVE",
                )
                continue
            if native_kind != "table":
                classified[block["index"]] = (
                    "unknown", (), "PARSER_NATIVE_UNKNOWN",
                )
                continue
            protected_overlap = any(
                other["native_kind"] in PROTECTED_LAYOUT_KINDS
                and _intersection_area(block["bbox"], other["bbox"]) > 0.1
                for other in blocks
            )
            if protected_overlap:
                kind, spans, reason = "unknown", (), "PROTECTED_LAYOUT_OVERLAP"
                layout_kind = "unknown"
            else:
                layout_kind = "table"
                spans, reason = _bind_table_text(
                    page=page,
                    canonical_text=canonical_text,
                    page_start=page_ranges[page][0],
                    page_end=page_ranges[page][1],
                    layout_text=block["text"],
                )
                kind = "table" if spans else "unknown"
            classified[block["index"]] = kind, spans, reason
            table_signature.append({
                "bbox": list(block["bbox"]),
                "effective_kind": layout_kind,
            })

        signature.append({"page": page, "tables": table_signature})
        ordered = sorted(
            blocks,
            key=lambda block: (
                block["bbox"][1], block["bbox"][0],
                block["bbox"][3], block["bbox"][2], block["index"],
            ),
        )
        for order, block in enumerate(ordered, 1):
            kind, spans, reason = classified[block["index"]]
            if kind not in PDF_LAYOUT_KINDS:
                raise ValueError(f"unsupported PDF layout kind: {kind!r}")
            segments.append(SourceSegment(
                page=page,
                bbox=block["bbox"],
                kind=kind,
                text=block["text"],
                order=order,
                source_spans=spans,
                native_kind=block["native_kind"],
                reason=reason,
            ))

    return PdfLayoutProjection(
        segments=tuple(segments),
        signature_sha256=_canonical_sha256(signature),
        adapter_versions=dict(adapter_versions),
    )


def _load_native_pdf_layout(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    import pymupdf
    import pymupdf.layout

    if pymupdf.VersionBind != PYMUPDF_VERSION:
        raise RuntimeError(
            f"PyMuPDF version mismatch: expected {PYMUPDF_VERSION}, "
            f"found {pymupdf.VersionBind}"
        )
    pymupdf.layout.activate()
    pages: list[dict[str, Any]] = []
    document = pymupdf.open(path)
    try:
        for page_number, page in enumerate(document, 1):
            page.get_layout()
            blocks = []
            for item in page.layout_information or []:
                bbox = _bbox(item[:4])
                blocks.append({
                    "bbox": list(bbox),
                    "native_kind": str(item[-1]),
                    "text": page.get_text(
                        "text", clip=pymupdf.Rect(bbox), sort=True,
                    ).strip(),
                })
            pages.append({"page": page_number, "blocks": blocks})
    finally:
        document.close()
    return pages, {
        "pymupdf": pymupdf.VersionBind,
        "pymupdf_layout": PYMUPDF_LAYOUT_VERSION,
    }


def parse_pdf_layout(path: Path, canonical_text: str) -> PdfLayoutProjection:
    pages, versions = _load_native_pdf_layout(Path(path))
    return project_pdf_layout(
        canonical_text, pages, adapter_versions=versions,
    )


def semantic_eligible_text(
    canonical_text: str,
    segments: Iterable[SourceSegment] | None,
) -> str:
    """Exclude only exact canonical spans owned by effective table segments."""
    if not segments:
        return canonical_text
    spans = sorted(
        (
            span
            for segment in segments
            if segment.kind == "table"
            for span in segment.source_spans
        ),
        key=lambda span: (span.start, span.end),
    )
    if not spans:
        return canonical_text
    cursor = 0
    parts: list[str] = []
    for span in spans:
        if span.start < cursor or span.end < span.start or span.end > len(canonical_text):
            raise ValueError("invalid or overlapping canonical table span")
        parts.append(canonical_text[cursor:span.start])
        cursor = span.end
    parts.append(canonical_text[cursor:])
    return "".join(parts)


def layout_sidecar(projection: PdfLayoutProjection) -> dict[str, Any]:
    return {
        "adapter": PDF_LAYOUT_ADAPTER,
        "adapter_versions": dict(projection.adapter_versions),
        "signature_sha256": projection.signature_sha256,
        "segment_text_role": "layout_overlap_diagnostic_not_source_truth",
        "segments": [
            {
                "page": segment.page,
                "bbox": list(segment.bbox),
                "kind": segment.kind,
                "text": segment.text,
                "order": segment.order,
                "native_kind": segment.native_kind,
                "reason": segment.reason,
                "canonical_source_spans": [
                    {"page": span.page, "start": span.start, "end": span.end}
                    for span in segment.source_spans
                ],
            }
            for segment in projection.segments
        ],
    }
