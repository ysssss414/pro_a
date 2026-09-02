from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


PILOT_RUN_ID = "PILOT_20260901_760D5031"
SOURCE_SHA256 = "760d50319760257dceaea2815374e685d089323faebcb32700dfefdaa6fd6d5c"
CLAIM_PROJECTION_SHA256 = (
    "d176a7d274b45cf76bcf853947ff7f649906737ca18667ae8ddd0d9716f1ac9d"
)
PILOT4_TREE_DIGEST = (
    "cf8263bcccd456bbde786e397ac5b81c261118562a653e20a125c1037dd940e5"
)
PILOT5_TREE_DIGEST = (
    "d856653676d8eb953a7172b673add332f660e9dae093677a7ad4151a9d1b496e"
)
PRODUCTION_SHA256 = (
    "581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250"
)
FROZEN_ARTIFACT_HASHES = {
    "extraction_bundle_stage1_1_rebound.json": (
        "a220e1f8bef259565fc6e31e1b6fb02f080af446a94cd2380359ecb031ae8121"
    ),
    "source_layout_sidecar.json": (
        "fed2687d0eccc486c5fdaf1bbce710a7afd4de724d659ddf20b505c2039e1712"
    ),
    "evidence_v2/evidence_contract_v2.json": (
        "0d9f6fa4995161074ee625d9e80d0123d5049486aa33d91df3cf33c605718bdf"
    ),
    "evidence_v2/pilot2_gate_a_quote_fidelity.json": (
        "d69681643d7724534cef1aaa0ac651754fd093d9aad47716e9bbd6ae7dc108df"
    ),
    "pilot5_independent_human_review_surface.md": (
        "09b215ead496809c1a081094caf489563931971edf84b447ed008478dd081a02"
    ),
}
DIAGNOSTIC_CANDIDATE_IDS = (
    "CLM_20260901_F244C74D",
    "CLM_20260901_BDB28301",
    "CLM_20260901_2D592B6E",
    "CLM_20260901_BDD0BF84",
    "CLM_20260901_DFEC4E23",
    "CLM_20260901_B2F0573B",
    "CLM_20260901_214DBE2A",
    "CLM_20260901_2BD36CE6",
    "CLM_20260901_7594D5EF",
)
PROTECTED_LAYOUT_KINDS = {"text", "list-item", "section-header", "caption"}
CLASSIFICATIONS = {
    "NATIVE_TABLE_EVIDENCE_UNIQUE",
    "NARRATIVE_EVIDENCE",
    "AMBIGUOUS_GEOMETRY",
    "UNRESOLVED_GEOMETRY",
    "OTHER_UNKNOWN",
}
TABLE_OVERLAP_MIN_AREA = 0.1
# The frozen sidecar serializes bboxes to four decimals. This tolerance is only
# the maximum sidecar serialization loss; it is not a semantic/geometric margin.
SIDECAR_BBOX_SERIALIZATION_EPSILON_PT = 0.0001

_MARKDOWN_ESCAPABLE = frozenset(r"\`*_{}[]()#+-.!|>~&")
_CJK = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
_PDF_PUNCTUATION = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "；": ";",
        "：": ":",
        "！": "!",
        "？": "?",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
)
_SOURCE_MARKER = re.compile(r"^\[\[(PAGE:[1-9]\d*)\]\]", re.MULTILINE)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def tree_snapshot(root: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]
    return {"files": len(rows), "digest": canonical_sha256(rows)}


def production_snapshot(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            "sha256": file_sha256(path),
            "table_counts": {
                table: connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                for table in tables
            },
            "integrity_check": connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0],
            "foreign_key_violations": len(
                connection.execute("PRAGMA foreign_key_check").fetchall()
            ),
        }
    finally:
        connection.close()


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def canonicalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")

    def restore_markdown_escape(match: re.Match[str]) -> str:
        char = match.group(1)
        return char if char in _MARKDOWN_ESCAPABLE else match.group(0)

    normalized = re.sub(r"\\(.)", restore_markdown_escape, normalized)
    return normalize_ws(normalized)


def normalize_pdf_span_text(value: str) -> str:
    normalized = canonicalize_text(value).translate(_PDF_PUNCTUATION)
    normalized = re.sub(rf"(?<={_CJK})\s+|\s+(?={_CJK})", "", normalized)
    normalized = re.sub(
        r"(?<=[0-9A-Za-z])\s*-\s*(?=[0-9A-Za-z])", "-", normalized
    )
    normalized = re.sub(r"\s+([,.;:!?)}\]])", r"\1", normalized)
    normalized = re.sub(r"([({\[])\s+", r"\1", normalized)
    return normalized


def normalize_pdf_locator_text(value: str) -> str:
    return normalize_pdf_span_text(value).rstrip(".,;:!?")


def normalize_geometry_text(value: str) -> str:
    """Frozen evaluation-only PyMuPDF word comparison normalization."""
    value = unicodedata.normalize("NFKC", value or "").translate(_PDF_PUNCTUATION)
    value = re.sub(r"\\(.)", lambda match: match.group(1), value)
    return re.sub(r"\s+", "", value).rstrip(".,;:!?")


def all_occurrences(haystack: str, needle: str) -> list[int]:
    if not needle:
        return []
    starts = []
    offset = 0
    while True:
        start = haystack.find(needle, offset)
        if start < 0:
            return starts
        starts.append(start)
        offset = start + 1


def comparison_mode(locator: dict[str, Any]) -> str | None:
    method = str(locator.get("match_method") or "")
    if method.startswith("provenance_"):
        method = method.removeprefix("provenance_")
    return {
        "raw_exact_substring": "raw",
        "canonical_exact_substring": "canonical",
        "pdf_normalized_exact_substring": "pdf_normalized",
    }.get(method)


def comparison_normalizer(mode: str | None) -> Callable[[str], str] | None:
    return {
        "raw": lambda value: value or "",
        "canonical": canonicalize_text,
        "pdf_normalized": normalize_pdf_locator_text,
    }.get(mode)


def parse_frozen_page_bodies(source: Path) -> dict[str, str]:
    from pypdf import PdfReader

    parts = []
    for page_number, page in enumerate(PdfReader(str(source)).pages, 1):
        parts.append(f"\n[[PAGE:{page_number}]]\n{page.extract_text() or ''}")
    full_text = "\n".join(parts)
    markers = list(_SOURCE_MARKER.finditer(full_text))
    pages: dict[str, str] = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(full_text)
        pages[marker.group(1)] = full_text[marker.end() : end]
    return pages


def rect_intersection_area(left: list[float], right: list[float]) -> float:
    x0 = max(left[0], right[0])
    y0 = max(left[1], right[1])
    x1 = min(left[2], right[2])
    y1 = min(left[3], right[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def rect_contains(
    outer: list[float], inner: list[float], *, epsilon: float = 0.0
) -> bool:
    return (
        outer[0] - epsilon <= inner[0]
        and outer[1] - epsilon <= inner[1]
        and inner[2] <= outer[2] + epsilon
        and inner[3] <= outer[3] + epsilon
    )


def rect_center_inside(outer: list[float], inner: list[float]) -> bool:
    x = (inner[0] + inner[2]) / 2
    y = (inner[1] + inner[3]) / 2
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def union_bbox(rectangles: list[list[float]]) -> list[float]:
    return [
        round(min(rect[0] for rect in rectangles), 4),
        round(min(rect[1] for rect in rectangles), 4),
        round(max(rect[2] for rect in rectangles), 4),
        round(max(rect[3] for rect in rectangles), 4),
    ]


def page_word_stream(page: Any) -> dict[str, Any]:
    words = page.get_text("words", sort=True)
    chunks: list[str] = []
    char_word_indices: list[int] = []
    for word_index, word in enumerate(words):
        normalized = normalize_geometry_text(str(word[4]))
        chunks.append(normalized)
        char_word_indices.extend([word_index] * len(normalized))
    return {
        "text": "".join(chunks),
        "char_word_indices": char_word_indices,
        "words": words,
    }


def table_has_protected_overlap(
    table: dict[str, Any], protected: list[dict[str, Any]]
) -> bool:
    return any(
        rect_intersection_area(table["bbox"], segment["bbox"])
        > TABLE_OVERLAP_MIN_AREA
        for segment in protected
    )


def occurrence_geometry(
    *,
    page_number: int,
    start: int,
    needle_length: int,
    stream: dict[str, Any],
    page_segments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    word_indices = sorted(
        set(stream["char_word_indices"][start : start + needle_length])
    )
    if not word_indices:
        return None
    word_bboxes = [
        [round(float(value), 6) for value in stream["words"][index][:4]]
        for index in word_indices
    ]
    tables = [segment for segment in page_segments if segment["native_kind"] == "table"]
    protected = [
        segment
        for segment in page_segments
        if segment["native_kind"] in PROTECTED_LAYOUT_KINDS
    ]
    full_tables = [
        table
        for table in tables
        if all(
            rect_contains(
                table["bbox"],
                word_bbox,
                epsilon=SIDECAR_BBOX_SERIALIZATION_EPSILON_PT,
            )
            for word_bbox in word_bboxes
        )
    ]
    intersecting_tables = [
        table
        for table in tables
        if any(
            rect_intersection_area(table["bbox"], word_bbox)
            > TABLE_OVERLAP_MIN_AREA
            for word_bbox in word_bboxes
        )
    ]
    protected_intersections = [
        segment
        for segment in protected
        if any(
            rect_intersection_area(segment["bbox"], word_bbox)
            > TABLE_OVERLAP_MIN_AREA
            for word_bbox in word_bboxes
        )
    ]
    narrative_by_centers = all(
        any(rect_center_inside(segment["bbox"], word_bbox) for segment in protected)
        for word_bbox in word_bboxes
    )
    table_by_centers = any(
        rect_center_inside(table["bbox"], word_bbox)
        for table in tables
        for word_bbox in word_bboxes
    )
    hit_segments = [
        segment
        for segment in page_segments
        if any(
            rect_intersection_area(segment["bbox"], word_bbox)
            > TABLE_OVERLAP_MIN_AREA
            for word_bbox in word_bboxes
        )
    ]
    return {
        "page": page_number,
        "stream_start": start,
        "word_indices": word_indices,
        "word_bboxes": word_bboxes,
        "union_bbox": union_bbox(word_bboxes),
        "native_layout_kinds": sorted(
            {segment["native_kind"] for segment in hit_segments}
        ),
        "effective_layout_kinds": sorted({segment["kind"] for segment in hit_segments}),
        "full_table_candidates": full_tables,
        "intersecting_table_candidates": intersecting_tables,
        "protected_intersections": protected_intersections,
        "narrative_by_word_centers": narrative_by_centers and not table_by_centers,
    }


def unknown_reason(reason: str | None) -> str | None:
    if reason == "CANONICAL_BINDING_UNRESOLVED":
        return "canonical binding failure"
    if reason == "PROTECTED_LAYOUT_OVERLAP":
        return "protected-layout overlap"
    if reason and "UNKNOWN" in reason:
        return "other"
    return None


def normalized_segment_occurrences(
    *, evidence: str, segments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    needle = normalize_geometry_text(evidence)
    results = []
    for segment in segments:
        if segment["native_kind"] not in PROTECTED_LAYOUT_KINDS:
            continue
        starts = all_occurrences(normalize_geometry_text(segment.get("text") or ""), needle)
        if starts:
            results.append(
                {
                    "page": segment["page"],
                    "order": segment["order"],
                    "native_kind": segment["native_kind"],
                    "bbox": segment["bbox"],
                    "occurrence_count": len(starts),
                }
            )
    return results


def build_claim_row(
    *,
    claim: dict[str, Any],
    quote: dict[str, Any],
    page_bodies: dict[str, str],
    word_streams: dict[int, dict[str, Any]],
    segments_by_page: dict[int, list[dict[str, Any]]],
    all_segments: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence = str(claim.get("evidence_excerpt") or "")
    resolved = quote.get("resolved_locator") or {}
    locator_candidates = [
        ("gate_a_source_locator", quote.get("gate_a_source_locator") or {}),
        ("original_source_locator", quote.get("original_source_locator") or {}),
        (
            "bundle_source_locator",
            claim.get("validation", {}).get("source_locator") or {},
        ),
    ]
    locator_variant = locator_candidates[0][0]
    locator = locator_candidates[0][1]
    authoritative_resolved = (
        resolved.get("status") == "resolved"
        and resolved.get("kind") == "single_page"
        and resolved.get("authoritative") is True
        and isinstance(resolved.get("locator"), str)
    )
    locator_value = resolved.get("locator") if authoritative_resolved else None
    page_number = int(locator_value.split(":")[1]) if locator_value else None

    canonical_locator_verified = False
    if locator_value in page_bodies:
        for candidate_name, candidate_locator in locator_candidates:
            candidate_mode = comparison_mode(candidate_locator)
            candidate_normalizer = comparison_normalizer(candidate_mode)
            if candidate_normalizer is None:
                continue
            comparison_start = candidate_locator.get("comparison_start")
            comparison_end = candidate_locator.get("comparison_end")
            normalized_body = candidate_normalizer(page_bodies[locator_value])
            normalized_evidence = candidate_normalizer(evidence)
            if (
                isinstance(comparison_start, int)
                and isinstance(comparison_end, int)
                and 0 <= comparison_start <= comparison_end <= len(normalized_body)
                and normalized_body[comparison_start:comparison_end]
                == normalized_evidence
            ):
                locator_variant = candidate_name
                locator = candidate_locator
                canonical_locator_verified = True
                break

    mode = comparison_mode(locator)
    normalizer = comparison_normalizer(mode)
    canonical_page_counts: dict[str, int] = {}
    canonical_occurrence_locations: list[dict[str, Any]] = []
    if normalizer is not None:
        normalized_evidence = normalizer(evidence)
        for page_locator, body in page_bodies.items():
            starts = all_occurrences(normalizer(body), normalized_evidence)
            canonical_page_counts[page_locator] = len(starts)
            canonical_occurrence_locations.extend(
                {"locator": page_locator, "comparison_start": start}
                for start in starts
            )
        if locator_value in page_bodies and not canonical_locator_verified:
            comparison_start = locator.get("comparison_start")
            comparison_end = locator.get("comparison_end")
            normalized_body = normalizer(page_bodies[locator_value])
            canonical_locator_verified = (
                isinstance(comparison_start, int)
                and isinstance(comparison_end, int)
                and 0 <= comparison_start <= comparison_end <= len(normalized_body)
                and normalized_body[comparison_start:comparison_end]
                == normalized_evidence
            )

    geometry_occurrences_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    geometry_needle = normalize_geometry_text(evidence)
    if geometry_needle:
        for candidate_page, stream in word_streams.items():
            for start in all_occurrences(stream["text"], geometry_needle):
                geometry = occurrence_geometry(
                    page_number=candidate_page,
                    start=start,
                    needle_length=len(geometry_needle),
                    stream=stream,
                    page_segments=segments_by_page[candidate_page],
                )
                if geometry is not None:
                    geometry_occurrences_by_page[candidate_page].append(geometry)
    page_geometries = geometry_occurrences_by_page.get(page_number, []) if page_number else []
    authoritative_geometry = page_geometries[0] if len(page_geometries) == 1 else None

    protected_segment_matches = normalized_segment_occurrences(
        evidence=evidence, segments=all_segments
    )
    narrative_geometry_occurrences = [
        {
            "page": geometry["page"],
            "stream_start": geometry["stream_start"],
            "union_bbox": geometry["union_bbox"],
        }
        for geometries in geometry_occurrences_by_page.values()
        for geometry in geometries
        if geometry["narrative_by_word_centers"]
    ]
    alternative_narrative_occurrence = bool(
        protected_segment_matches or narrative_geometry_occurrences
    )
    if authoritative_geometry and authoritative_geometry["narrative_by_word_centers"]:
        alternative_narrative_occurrence = bool(
            len(narrative_geometry_occurrences) > 1
            or any(
                match["page"] != page_number
                for match in protected_segment_matches
            )
        )

    full_tables = (
        authoritative_geometry["full_table_candidates"]
        if authoritative_geometry
        else []
    )
    selected_table = full_tables[0] if len(full_tables) == 1 else None
    page_protected = (
        [
            segment
            for segment in segments_by_page[page_number]
            if segment["native_kind"] in PROTECTED_LAYOUT_KINDS
        ]
        if page_number
        else []
    )
    selected_table_protected_overlap = (
        table_has_protected_overlap(selected_table, page_protected)
        if selected_table
        else False
    )
    canonical_page_occurrences = (
        canonical_page_counts.get(locator_value, 0) if locator_value else 0
    )
    strict_table = all(
        (
            authoritative_resolved,
            canonical_locator_verified,
            canonical_page_occurrences == 1,
            len(page_geometries) == 1,
            len(full_tables) == 1,
            not selected_table_protected_overlap,
            not alternative_narrative_occurrence,
        )
    )

    if not authoritative_resolved or not canonical_locator_verified:
        classification = "UNRESOLVED_GEOMETRY"
    elif canonical_page_occurrences > 1 or len(page_geometries) > 1 or len(full_tables) > 1:
        classification = "AMBIGUOUS_GEOMETRY"
    elif not page_geometries:
        classification = "UNRESOLVED_GEOMETRY"
    elif strict_table:
        classification = "NATIVE_TABLE_EVIDENCE_UNIQUE"
    elif selected_table and alternative_narrative_occurrence:
        classification = "AMBIGUOUS_GEOMETRY"
    elif authoritative_geometry and authoritative_geometry["narrative_by_word_centers"]:
        classification = "NARRATIVE_EVIDENCE"
    else:
        classification = "OTHER_UNKNOWN"
    if classification not in CLASSIFICATIONS:
        raise RuntimeError("Claim did not receive exactly one diagnostic classification")

    table_reason = selected_table.get("reason") if selected_table else None
    effective_kind = (
        selected_table.get("kind")
        if selected_table
        else "narrative"
        if authoritative_geometry
        and authoritative_geometry["narrative_by_word_centers"]
        else "unknown"
        if authoritative_geometry
        else None
    )
    protected_evidence_intersections = (
        authoritative_geometry["protected_intersections"]
        if authoritative_geometry
        else []
    )
    return {
        "claim_id": claim["claim_id"],
        "diagnostic_candidate_failure": claim["claim_id"] in DIAGNOSTIC_CANDIDATE_IDS,
        "statement": claim.get("statement") or "",
        "attributed_to": claim.get("attributed_to") or "",
        "evidence": evidence,
        "authoritative_locator": resolved,
        "quote_fidelity_class": quote.get("fidelity_status"),
        "source_page": page_number,
        "canonical_locator_variant_used": locator_variant,
        "canonical_locator_match_method": locator.get("match_method"),
        "canonical_locator_verified": canonical_locator_verified,
        "canonical_page_occurrence_count": canonical_page_occurrences,
        "canonical_source_occurrence_count": len(canonical_occurrence_locations),
        "canonical_source_occurrence_locations": canonical_occurrence_locations,
        "evidence_unique_in_canonical_source": len(canonical_occurrence_locations) == 1,
        "page_local_pdf_geometry_occurrence_count": len(page_geometries),
        "pdf_geometry_uniquely_resolved": len(page_geometries) == 1,
        "pdf_geometry": (
            {
                key: authoritative_geometry[key]
                for key in (
                    "union_bbox",
                    "word_bboxes",
                    "word_indices",
                    "native_layout_kinds",
                    "effective_layout_kinds",
                )
            }
            if authoritative_geometry
            else None
        ),
        "native_pymupdf_layout_kind_at_geometry": (
            authoritative_geometry["native_layout_kinds"]
            if authoritative_geometry
            else []
        ),
        "native_table_candidate_bbox": selected_table.get("bbox") if selected_table else None,
        "native_table_candidate_page_order": (
            selected_table.get("order") if selected_table else None
        ),
        "effective_runtime_kind": effective_kind,
        "effective_runtime_reason": table_reason,
        "effective_unknown_reason_category": unknown_reason(table_reason),
        "evidence_geometry_fully_inside_native_table": bool(selected_table),
        "native_table_has_protected_narrative_overlap": selected_table_protected_overlap,
        "evidence_geometry_intersects_protected_narrative": bool(
            protected_evidence_intersections
        ),
        "protected_narrative_intersections": [
            {
                "page": segment["page"],
                "order": segment["order"],
                "native_kind": segment["native_kind"],
                "bbox": segment["bbox"],
            }
            for segment in protected_evidence_intersections
        ],
        "alternative_narrative_occurrence": alternative_narrative_occurrence,
        "alternative_narrative_geometry_occurrences": narrative_geometry_occurrences,
        "alternative_narrative_segment_matches": protected_segment_matches,
        "all_pdf_geometry_occurrences": [
            {
                "page": geometry["page"],
                "stream_start": geometry["stream_start"],
                "union_bbox": geometry["union_bbox"],
                "native_layout_kinds": geometry["native_layout_kinds"],
            }
            for geometries in geometry_occurrences_by_page.values()
            for geometry in geometries
        ],
        "diagnostic_class": classification,
        "boundary_v1_drop": classification == "NATIVE_TABLE_EVIDENCE_UNIQUE",
        "upstream_path": (
            "accepted upstream table"
            if selected_table and selected_table.get("kind") == "table"
            else "canonical-binding fail-open unknown"
            if table_reason == "CANONICAL_BINDING_UNRESOLVED"
            else "protected-overlap fail-open unknown"
            if selected_table_protected_overlap
            else "not table-classified"
        ),
    }


def digit_token(value: str) -> str:
    token = value.replace(".", "").lstrip("0")
    return token or "0"


def numeric_fingerprint(value: str) -> list[str]:
    return [digit_token(token) for token in _NUMBER.findall(value)]


def longest_common_contiguous_length(left: list[str], right: list[str]) -> int:
    best = 0
    for left_index in range(len(left)):
        for right_index in range(len(right)):
            length = 0
            while (
                left_index + length < len(left)
                and right_index + length < len(right)
                and left[left_index + length] == right[right_index + length]
            ):
                length += 1
            best = max(best, length)
    return best


def text_label(value: str) -> str:
    normalized = normalize_geometry_text(value)
    return re.sub(r"[\d%./()\-+]+", "", normalized)


def longest_common_text_run(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    best = 0
    for left_char in left:
        current = [0]
        for index, right_char in enumerate(right, 1):
            length = previous[index - 1] + 1 if left_char == right_char else 0
            current.append(length)
            best = max(best, length)
        previous = current
    return best


def redundancy_census(rows: list[dict[str, Any]]) -> dict[str, Any]:
    table_rows = [row for row in rows if row["boundary_v1_drop"]]
    narrative_rows = [
        row
        for row in rows
        if not row["boundary_v1_drop"]
        and (
            row["diagnostic_class"] == "NARRATIVE_EVIDENCE"
            or row["alternative_narrative_segment_matches"]
        )
    ]
    results = []
    for table_row in table_rows:
        table_numbers = numeric_fingerprint(table_row["evidence"])
        matches = []
        for narrative_row in narrative_rows:
            narrative_numbers = numeric_fingerprint(narrative_row["evidence"])
            common_numbers = longest_common_contiguous_length(
                table_numbers, narrative_numbers
            )
            common_text = longest_common_text_run(
                text_label(table_row["statement"]),
                text_label(narrative_row["statement"]),
            )
            if common_numbers >= 3 and common_text >= 4:
                matches.append(
                    {
                        "narrative_claim_id": narrative_row["claim_id"],
                        "narrative_statement": narrative_row["statement"],
                        "narrative_evidence": narrative_row["evidence"],
                        "narrative_provenance_basis": (
                            "unique word geometry in protected native narrative layout"
                            if narrative_row["diagnostic_class"] == "NARRATIVE_EVIDENCE"
                            else "exact Evidence occurrence in protected native narrative segment"
                        ),
                        "ordered_numeric_tokens_matched": common_numbers,
                        "longest_common_nonnumeric_text_run": common_text,
                        "scope": "mechanical ordered-vector overlap only; not semantic equivalence",
                    }
                )
        results.append(
            {
                "table_claim_id": table_row["claim_id"],
                "table_statement": table_row["statement"],
                "table_evidence": table_row["evidence"],
                "obvious_mechanical_narrative_cross_references": matches,
                "substantially_represented_mechanically": bool(matches),
            }
        )
    return {
        "boundary_input": False,
        "method": (
            "Evaluation-only ordered numeric-token overlap after decimal-point removal, "
            "requiring at least three contiguous matching tokens plus at least four "
            "contiguous nonnumeric statement characters. The retained comparison Claim must "
            "have either protected narrative word geometry or an exact Evidence occurrence "
            "inside a protected native narrative segment. No embedding, LLM, or semantic "
            "equivalence is used; results are cross-references, not truth labels."
        ),
        "claims_checked": len(results),
        "claims_with_obvious_mechanical_narrative_cross_reference": sum(
            row["substantially_represented_mechanically"] for row in results
        ),
        "rows": results,
    }


def md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["feasibility_metrics"]
    leakage = report["table_leakage_census"]
    isolation = report["isolation"]
    lines = [
        "# Phase 3C Pilot #5 Table-Derived Claim Failure Census",
        "",
        "Design and mechanical census only. No safety filter was implemented; no Pilot #5 "
        "artifact, Evidence, Human Review decision, semantic extraction, or Production state "
        "was modified.",
        "",
        "## Outcome",
        "",
        f"- `PHASE3C_PILOT5_TABLE_CLAIM_FAILURE_CENSUS_COMPLETE = {str(report['complete']).lower()}`",
        f"- `NATIVE_TABLE_EVIDENCE_UNIQUE_CLAIMS = {metrics['native_table_evidence_unique_claims']}`",
        f"- `CANDIDATE_FAILURES_CAPTURED_BY_BOUNDARY = {metrics['candidate_failures_captured']} / 9`",
        f"- `NON_CANDIDATE_CLAIMS_CAPTURED_BY_BOUNDARY = {metrics['non_candidate_claims_captured']} / 41`",
        f"- `UPSTREAM_SUPPRESSION_LEAK_FOUND = {leakage['upstream_suppression_leak_found']}`",
        f"- `TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY = {report['architecture_decision']['recommendation']}`",
        "",
        "## Exact boundary selection rule",
        "",
        report["mechanical_contract"]["selection_rule"],
        "",
        "The authoritative page is allowed to disambiguate same Evidence text appearing in "
        "another table elsewhere in the Source. A competing narrative occurrence still fails "
        "open. No wording, number-density, year, financial-vocabulary, or model-confidence "
        "signal participates in classification.",
        "",
        "## Diagnostic 9-Claim census",
        "",
        "| Claim | Locator | Fidelity | Canonical Source unique | Page geometry | Native/effective | Unknown reason | Fully in table | Protected intersect | Narrative alternative | Class |",
        "|---|---|---|---:|---:|---|---|---:|---:|---:|---|",
    ]
    for row in report["diagnostic_failure_census"]:
        lines.append(
            "| "
            + " | ".join(
                md_escape(value)
                for value in (
                    row["claim_id"],
                    row["authoritative_locator"].get("locator"),
                    row["quote_fidelity_class"],
                    row["evidence_unique_in_canonical_source"],
                    row["page_local_pdf_geometry_occurrence_count"],
                    "/".join(row["native_pymupdf_layout_kind_at_geometry"])
                    + "/"
                    + str(row["effective_runtime_kind"]),
                    row["effective_unknown_reason_category"],
                    row["evidence_geometry_fully_inside_native_table"],
                    row["evidence_geometry_intersects_protected_narrative"],
                    row["alternative_narrative_occurrence"],
                    row["diagnostic_class"],
                )
            )
            + " |"
        )
    lines.extend(["", "### Claim details", ""])
    for row in report["diagnostic_failure_census"]:
        lines.extend(
            [
                f"- `{row['claim_id']}`",
                f"  - Statement: {row['statement']}",
                f"  - Attributed to: {row['attributed_to']}",
                f"  - Evidence: {row['evidence']}",
                f"  - Geometry bbox: {(row['pdf_geometry'] or {}).get('union_bbox')}",
                f"  - Native table bbox: {row['native_table_candidate_bbox']}",
                f"  - Canonical occurrences: {row['canonical_source_occurrence_locations']}",
            ]
        )
    lines.extend(
        [
            "",
            "## All-50 origin replay",
            "",
            "| Diagnostic class | Claims |",
            "|---|---:|",
        ]
    )
    for name in sorted(CLASSIFICATIONS):
        lines.append(f"| `{name}` | {report['all_50_origin_replay']['class_counts'].get(name, 0)} |")
    lines.extend(
        [
            "",
            "| Claim | Page | Candidate set | Class | Boundary action |",
            "|---|---:|---:|---|---|",
        ]
    )
    for row in report["all_50_origin_replay"]["claims"]:
        lines.append(
            f"| `{row['claim_id']}` | {row['source_page'] or ''} | "
            f"{row['diagnostic_candidate_failure']} | `{row['diagnostic_class']}` | "
            f"{'DROP' if row['boundary_v1_drop'] else 'KEEP / FAIL-OPEN'} |"
        )
    lines.extend(
        [
            "",
            "## Feasibility metrics",
            "",
            f"- Candidate failures: {metrics['candidate_failures_captured']} captured, "
            f"{metrics['candidate_failures_not_captured']} not captured.",
            f"- Remaining Claims: {metrics['non_candidate_claims_captured']} captured, "
            f"{metrics['non_candidate_claims_retained']} retained.",
            f"- False-positive non-candidate capture: {metrics['false_positive_non_candidate_capture']}.",
            "",
            "## Table leakage census",
            "",
            f"- Native-table unique Claims: {leakage['native_table_evidence_unique_claims']}.",
            f"- Pages: {leakage['pages']}.",
            f"- Canonical-binding fail-open table Claims: {leakage['canonical_binding_fail_open_table_claims']}.",
            f"- Protected-overlap table Claims: {leakage['protected_overlap_table_claims']}.",
            f"- Upstream effective-table leaks: {len(leakage['upstream_suppression_leak_claim_ids'])}.",
            "",
            "## Redundancy/value check",
            "",
            report["redundancy_value_check"]["method"],
            "",
        ]
    )
    for row in report["redundancy_value_check"]["rows"]:
        if row["obvious_mechanical_narrative_cross_references"]:
            refs = ", ".join(
                f"`{match['narrative_claim_id']}`"
                for match in row["obvious_mechanical_narrative_cross_references"]
            )
            lines.append(f"- `{row['table_claim_id']}` -> {refs}")
    lines.extend(
        [
            "",
            "## Architecture decision",
            "",
            f"`TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY = {report['architecture_decision']['recommendation']}`",
            "",
            report["architecture_decision"]["rationale"],
            "",
            f"Smallest later implementation location: {report['architecture_decision']['smallest_implementation_location']}",
            "",
            "No implementation was performed in this task.",
            "",
            "## Minimal later implementation surface",
            "",
        ]
    )
    for item in report["architecture_decision"]["minimal_later_changes"]:
        lines.append(f"- {item}")
    lines.extend(["", "Proposed deterministic fixtures:", ""])
    for index, item in enumerate(report["architecture_decision"]["fixtures"], 1):
        lines.append(f"{index}. {item}")
    lines.extend(
        [
            "",
            "## Isolation",
            "",
            f"- Pilot #5 pre/post: `{isolation['pilot5_pre']}` / `{isolation['pilot5_post']}`.",
            f"- Pilot #4 pre/post: `{isolation['pilot4_pre']}` / `{isolation['pilot4_post']}`.",
            f"- Production pre/post SHA: `{isolation['production_pre']['sha256']}` / "
            f"`{isolation['production_post']['sha256']}`.",
            f"- Production table counts changed: {isolation['production_table_counts_changed']}.",
            f"- Integrity: {isolation['production_post']['integrity_check']}; FK violations: "
            f"{isolation['production_post']['foreign_key_violations']}.",
            "- LLM calls: 0; semantic extraction calls: 0; Human Review decisions changed: 0.",
            "- IMA: NO; Propagation: NO; Legacy ingestion: NO; Production write: NO.",
            "",
            "## STOP",
            "",
            "STOPPED after design and mechanical census. No filter was implemented and Human Review remains PENDING=50.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pilot5-dir", type=Path, required=True)
    parser.add_argument("--pilot4-dir", type=Path, required=True)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--pymupdf-deps", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    pilot5_dir = args.pilot5_dir.resolve()
    pilot4_dir = args.pilot4_dir.resolve()
    production_db = args.production_db.resolve()
    pymupdf_deps = args.pymupdf_deps.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.is_relative_to(pilot5_dir) or output_dir.is_relative_to(pilot4_dir):
        raise RuntimeError("census output must remain outside frozen Pilot directories")
    if str(pymupdf_deps) not in sys.path:
        sys.path.insert(0, str(pymupdf_deps))
    import pymupdf

    pilot4_pre = tree_snapshot(pilot4_dir)
    pilot5_pre = tree_snapshot(pilot5_dir)
    production_pre = production_snapshot(production_db)
    if pilot4_pre != {"files": 38, "digest": PILOT4_TREE_DIGEST}:
        raise RuntimeError("Pilot #4 frozen tree changed before census")
    if pilot5_pre != {"files": 42, "digest": PILOT5_TREE_DIGEST}:
        raise RuntimeError("Pilot #5 frozen tree changed before census")
    if production_pre["sha256"] != PRODUCTION_SHA256:
        raise RuntimeError("Production SHA changed before census")
    if file_sha256(source) != SOURCE_SHA256:
        raise RuntimeError("Pilot #5 Source SHA mismatch")
    for relative, expected_hash in FROZEN_ARTIFACT_HASHES.items():
        if file_sha256(pilot5_dir / relative) != expected_hash:
            raise RuntimeError(f"frozen Pilot #5 artifact changed: {relative}")

    bundle = load_json(pilot5_dir / "extraction_bundle_stage1_1_rebound.json")
    sidecar = load_json(pilot5_dir / "source_layout_sidecar.json")
    quotes = load_json(
        pilot5_dir / "evidence_v2" / "pilot2_gate_a_quote_fidelity.json"
    )
    evidence_contract = load_json(
        pilot5_dir / "evidence_v2" / "evidence_contract_v2.json"
    )
    claims = bundle.get("claims") or []
    quote_by_id = {row["claim_id"]: row for row in quotes.get("claims") or []}
    if bundle.get("pilot_run_id") != PILOT_RUN_ID or len(claims) != 50:
        raise RuntimeError("Pilot #5 bundle freeze mismatch")
    if len(quote_by_id) != 50 or len(evidence_contract.get("claims") or []) != 50:
        raise RuntimeError("Pilot #5 Evidence Claim count mismatch")
    projection = canonical_sha256(
        [
            {
                "claim_id": claim.get("claim_id"),
                "statement": claim.get("statement"),
                "evidence_excerpt": claim.get("evidence_excerpt"),
                "attributed_to": claim.get("attributed_to") or "",
            }
            for claim in claims
        ]
    )
    if projection != CLAIM_PROJECTION_SHA256:
        raise RuntimeError("Pilot #5 Claim projection changed")
    if set(DIAGNOSTIC_CANDIDATE_IDS) - {claim["claim_id"] for claim in claims}:
        raise RuntimeError("diagnostic candidate Claim set is incomplete")

    all_segments = sidecar.get("segments") or []
    segments_by_page = {
        page: [segment for segment in all_segments if segment["page"] == page]
        for page in range(1, 13)
    }
    document = pymupdf.open(source)
    try:
        if len(document) != 12:
            raise RuntimeError("Pilot #5 PDF page count changed")
        word_streams = {
            page_number: page_word_stream(document[page_number - 1])
            for page_number in range(1, len(document) + 1)
        }
    finally:
        document.close()
    page_bodies = parse_frozen_page_bodies(source)
    rows = [
        build_claim_row(
            claim=claim,
            quote=quote_by_id[claim["claim_id"]],
            page_bodies=page_bodies,
            word_streams=word_streams,
            segments_by_page=segments_by_page,
            all_segments=all_segments,
        )
        for claim in claims
    ]
    if len(rows) != 50 or any(row["diagnostic_class"] not in CLASSIFICATIONS for row in rows):
        raise RuntimeError("all-50 classification invariant failed")

    candidate_rows = [row for row in rows if row["diagnostic_candidate_failure"]]
    non_candidate_rows = [row for row in rows if not row["diagnostic_candidate_failure"]]
    table_rows = [row for row in rows if row["boundary_v1_drop"]]
    candidate_captured = sum(row["boundary_v1_drop"] for row in candidate_rows)
    non_candidate_captured = sum(row["boundary_v1_drop"] for row in non_candidate_rows)
    upstream_leaks = [
        row
        for row in table_rows
        if row["upstream_path"] == "accepted upstream table"
    ]
    protected_overlap_rows = [
        row
        for row in rows
        if row["evidence_geometry_fully_inside_native_table"]
        and row["native_table_has_protected_narrative_overlap"]
    ]
    canonical_fail_open_rows = [
        row
        for row in table_rows
        if row["upstream_path"] == "canonical-binding fail-open unknown"
    ]
    table_groups: dict[str, dict[str, Any]] = {}
    for row in table_rows:
        key = canonical_sha256(
            {"page": row["source_page"], "bbox": row["native_table_candidate_bbox"]}
        )[:12]
        group = table_groups.setdefault(
            key,
            {
                "native_table_candidate_id": (
                    f"PAGE:{row['source_page']}/TABLE_BBOX:{key}"
                ),
                "page": row["source_page"],
                "bbox": row["native_table_candidate_bbox"],
                "effective_runtime_kind": row["effective_runtime_kind"],
                "effective_runtime_reason": row["effective_runtime_reason"],
                "upstream_path": row["upstream_path"],
                "claim_ids": [],
            },
        )
        group["claim_ids"].append(row["claim_id"])

    recommendation = (
        "NOT_NEEDED_UPSTREAM_BUG"
        if upstream_leaks
        else "UNSAFE_FALSE_POSITIVES"
        if non_candidate_captured
        else "BLOCKED_INSUFFICIENT_GEOMETRY"
        if not table_rows
        else "FEASIBLE_MINIMAL"
    )
    next_gate = (
        "Table-Derived Claim Safety Boundary Minimal Implementation"
        if recommendation == "FEASIBLE_MINIMAL"
        else "Pilot #5 Failure Design Blocker"
    )
    redundancy = redundancy_census(rows)

    pilot4_post = tree_snapshot(pilot4_dir)
    pilot5_post = tree_snapshot(pilot5_dir)
    production_post = production_snapshot(production_db)
    isolation_ok = all(
        (
            pilot4_pre == pilot4_post,
            pilot5_pre == pilot5_post,
            production_pre == production_post,
            production_post["integrity_check"] == "ok",
            production_post["foreign_key_violations"] == 0,
        )
    )
    pending = sum(
        row.get("human_decision") == "PENDING" for row in quotes.get("claims") or []
    )
    complete = (
        len(candidate_rows) == 9
        and len(non_candidate_rows) == 41
        and pending == 50
        and isolation_ok
    )

    report = {
        "document_type": "phase3c_pilot5_table_claim_failure_census",
        "schema_version": "1",
        "pilot_run_id": PILOT_RUN_ID,
        "complete": complete,
        "scope": {
            "design_and_mechanical_census_only": True,
            "safety_filter_implemented": False,
            "pdf_table_detector_modified": False,
            "semantic_extraction_modified": False,
            "evidence_modified_or_rebuilt": False,
            "llm_calls": 0,
            "semantic_extraction_calls": 0,
            "human_review_performed": False,
            "production_write": False,
        },
        "freeze": {
            "source_sha256": file_sha256(source),
            "claim_projection_sha256": projection,
            "claims": len(claims),
            "human_review_pending": pending,
            "frozen_artifact_hashes": FROZEN_ARTIFACT_HASHES,
        },
        "mechanical_contract": {
            "name": "TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY_V1",
            "selection_rule": (
                "After authoritative Evidence resolution, DROP only when the frozen "
                "single-page locator is mechanically verified, the Evidence has exactly "
                "one occurrence on that canonical page and exactly one PyMuPDF word-geometry "
                "occurrence on that page, every Evidence word bbox is contained in exactly "
                "one parser-owned native table bbox (allowing only 0.0001 pt frozen-sidecar "
                "serialization tolerance), that table bbox has no >0.1 pt^2 intersection "
                "with protected text/list-item/section-header/caption geometry, and no "
                "competing narrative occurrence exists elsewhere. Otherwise KEEP/fail-open."
            ),
            "authoritative_page_disambiguates_other_table_occurrence": True,
            "canonical_source_global_uniqueness_reported_but_not_required": True,
            "protected_layout_kinds": sorted(PROTECTED_LAYOUT_KINDS),
            "sidecar_bbox_serialization_epsilon_pt": (
                SIDECAR_BBOX_SERIALIZATION_EPSILON_PT
            ),
            "table_protected_overlap_min_area_pt2": TABLE_OVERLAP_MIN_AREA,
            "claim_wording_used": False,
            "numeric_or_financial_heuristics_used": False,
            "model_confidence_used": False,
            "diagnostic_class_definitions": {
                "NATIVE_TABLE_EVIDENCE_UNIQUE": (
                    "Authoritative single-page locator verified; one canonical occurrence "
                    "and one word-geometry occurrence on that page; geometry fully inside "
                    "exactly one native table; no protected overlap or narrative competitor."
                ),
                "NARRATIVE_EVIDENCE": (
                    "Unique page-local word geometry whose word centers are wholly owned by "
                    "protected native narrative layout and not by native table geometry."
                ),
                "AMBIGUOUS_GEOMETRY": (
                    "Multiple canonical/page geometries, multiple containing tables, or a "
                    "table occurrence competing with a narrative occurrence."
                ),
                "UNRESOLVED_GEOMETRY": (
                    "Authoritative locator or frozen locator slice cannot be verified, or "
                    "no exact PyMuPDF word geometry is available."
                ),
                "OTHER_UNKNOWN": (
                    "A unique geometry exists but satisfies neither the strict table class "
                    "nor protected narrative ownership; KEEP/fail-open."
                ),
            },
            "runtime_versions": {
                "pymupdf": getattr(pymupdf, "__version__", "UNKNOWN"),
                "pypdf": __import__("pypdf").__version__,
                "frozen_sidecar_adapter": sidecar.get("adapter"),
                "frozen_sidecar_adapter_versions": sidecar.get("adapter_versions"),
            },
        },
        "diagnostic_failure_census": candidate_rows,
        "all_50_origin_replay": {
            "claims_total": len(rows),
            "class_counts": {
                name: sum(row["diagnostic_class"] == name for row in rows)
                for name in sorted(CLASSIFICATIONS)
            },
            "claims": rows,
        },
        "feasibility_metrics": {
            "candidate_failures_total": 9,
            "candidate_failures_captured": candidate_captured,
            "candidate_failures_not_captured": 9 - candidate_captured,
            "candidate_failures_not_captured_ids": [
                row["claim_id"] for row in candidate_rows if not row["boundary_v1_drop"]
            ],
            "non_candidate_claims_total": 41,
            "non_candidate_claims_captured": non_candidate_captured,
            "non_candidate_claims_captured_ids": [
                row["claim_id"] for row in non_candidate_rows if row["boundary_v1_drop"]
            ],
            "non_candidate_claims_retained": 41 - non_candidate_captured,
            "false_positive_non_candidate_capture": non_candidate_captured,
            "native_table_evidence_unique_claims": len(table_rows),
        },
        "table_leakage_census": {
            "native_table_evidence_unique_claims": len(table_rows),
            "claim_ids": [row["claim_id"] for row in table_rows],
            "pages": sorted({row["source_page"] for row in table_rows}),
            "native_table_candidates": list(table_groups.values()),
            "upstream_suppression_leak_found": "YES" if upstream_leaks else "NO",
            "upstream_suppression_leak_claim_ids": [
                row["claim_id"] for row in upstream_leaks
            ],
            "canonical_binding_fail_open_table_claims": len(canonical_fail_open_rows),
            "canonical_binding_fail_open_table_claim_ids": [
                row["claim_id"] for row in canonical_fail_open_rows
            ],
            "protected_overlap_table_claims": len(protected_overlap_rows),
            "protected_overlap_table_claim_ids": [
                row["claim_id"] for row in protected_overlap_rows
            ],
        },
        "redundancy_value_check": redundancy,
        "architecture_decision": {
            "recommendation": recommendation,
            "rationale": (
                f"The parser/provenance-only boundary captures {candidate_captured}/9 "
                f"diagnostic candidates and {non_candidate_captured}/41 non-candidates; "
                f"upstream effective-table leaks={len(upstream_leaks)}. It preserves "
                "fail-open behavior and changes neither canonical Source nor Evidence."
            ),
            "smallest_implementation_location": (
                "immediately after Evidence authoritative occurrence resolution and before "
                "Human Review surface construction / downstream Claim eligibility"
            ),
            "minimal_later_changes": [
                "Reuse the frozen PyMuPDF layout sidecar and authoritative Evidence locator.",
                "Add one deterministic Claim-eligibility predicate at the post-binding boundary; do not alter the PDF table detector.",
                "Exclude only predicate-positive Claims from downstream review/acceptance while retaining fail-open Claims unchanged.",
                "Add focused unit/regression fixtures; do not change Production or Evidence schemas.",
            ],
            "fixtures": [
                "Unique Evidence fully inside a native table is rejected.",
                "Narrative Evidence is retained.",
                "Table geometry with protected narrative overlap is retained.",
                "Ambiguous Evidence occurrence is retained.",
                "Whole-table canonical binding failure plus unique individual Evidence geometry is rejected.",
                "Same fact in narrative and table with authoritative narrative Evidence is retained.",
                "Repeated parse is deterministic.",
                "No effective upstream table leakage regression.",
            ],
            "production_schema_change_required": "NO",
            "evidence_contract_change_required": "NO",
            "prompt_change_required": "NO",
            "table_detector_change_required": "NO",
        },
        "isolation": {
            "pilot5_pre": pilot5_pre,
            "pilot5_post": pilot5_post,
            "pilot5_unchanged": pilot5_pre == pilot5_post,
            "pilot4_pre": pilot4_pre,
            "pilot4_post": pilot4_post,
            "pilot4_unchanged": pilot4_pre == pilot4_post,
            "production_pre": production_pre,
            "production_post": production_post,
            "production_unchanged": production_pre == production_post,
            "production_table_counts_changed": (
                production_pre["table_counts"] != production_post["table_counts"]
            ),
            "ima_invoked": False,
            "propagation_invoked": False,
            "legacy_ingestion_invoked": False,
            "production_write": False,
        },
        "phase_state": {
            "PHASE3C_COMPLETE": False,
            "PRODUCTION_APPLY_READY": "NO",
            "PHASE3C_NEXT_GATE": next_gate,
            "STOP_CONFIRMATION": "STOPPED_BEFORE_IMPLEMENTATION_AND_HUMAN_REVIEW",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "phase3c_pilot5_table_claim_failure_census.json"
    markdown_path = output_dir / "phase3c_pilot5_table_claim_failure_census.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "complete": complete,
                "class_counts": report["all_50_origin_replay"]["class_counts"],
                "candidate_captured": candidate_captured,
                "non_candidate_captured": non_candidate_captured,
                "upstream_leaks": len(upstream_leaks),
                "recommendation": recommendation,
                "json": str(json_path),
                "markdown": str(markdown_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
