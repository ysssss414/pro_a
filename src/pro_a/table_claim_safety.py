"""Post-binding origin eligibility for Claims supported only by PDF tables.

The boundary consumes frozen canonical text, authoritative Evidence locators,
the existing PDF layout sidecar, and PyMuPDF word geometry. It does not detect
tables, interpret table content, mutate Claims/Evidence, or make semantic
judgments.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .parsers import source_units
from .pdf_layout import PROTECTED_LAYOUT_KINDS, PYMUPDF_VERSION


TABLE_CLAIM_SAFETY_BOUNDARY_VERSION = "V1"
TABLE_DERIVED_CLAIM_INELIGIBLE = "TABLE_DERIVED_CLAIM_INELIGIBLE"
TABLE_CLAIM_ELIGIBLE_FAIL_OPEN = "TABLE_CLAIM_ELIGIBLE_FAIL_OPEN"
SIDECAR_BBOX_SERIALIZATION_TOLERANCE_PT = 0.0001
PROTECTED_LAYOUT_INTERSECTION_AREA_PT2 = 0.1

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


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _canonicalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")

    def restore_markdown_escape(match: re.Match[str]) -> str:
        char = match.group(1)
        return char if char in _MARKDOWN_ESCAPABLE else match.group(0)

    normalized = re.sub(r"\\(.)", restore_markdown_escape, normalized)
    return _normalize_ws(normalized)


def _normalize_pdf_locator_text(value: str) -> str:
    normalized = _canonicalize_text(value).translate(_PDF_PUNCTUATION)
    normalized = re.sub(rf"(?<={_CJK})\s+|\s+(?={_CJK})", "", normalized)
    normalized = re.sub(
        r"(?<=[0-9A-Za-z])\s*-\s*(?=[0-9A-Za-z])", "-", normalized
    )
    normalized = re.sub(r"\s+([,.;:!?)}\]])", r"\1", normalized)
    normalized = re.sub(r"([({\[])\s+", r"\1", normalized)
    return normalized.rstrip(".,;:!?")


def _normalize_geometry_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").translate(
        _PDF_PUNCTUATION
    )
    normalized = re.sub(r"\\(.)", lambda match: match.group(1), normalized)
    return re.sub(r"\s+", "", normalized).rstrip(".,;:!?")


def _all_occurrences(haystack: str, needle: str) -> list[int]:
    if not needle:
        return []
    starts: list[int] = []
    offset = 0
    while True:
        start = haystack.find(needle, offset)
        if start < 0:
            return starts
        starts.append(start)
        offset = start + 1


def _comparison_normalizer(locator: Mapping[str, Any]):
    method = str(locator.get("match_method") or "")
    if method.startswith("provenance_"):
        method = method.removeprefix("provenance_")
    return {
        "raw_exact_substring": lambda value: value or "",
        "canonical_exact_substring": _canonicalize_text,
        "pdf_normalized_exact_substring": _normalize_pdf_locator_text,
    }.get(method)


def _intersection_area(left: Sequence[float], right: Sequence[float]) -> float:
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return width * height


def _contains(
    outer: Sequence[float],
    inner: Sequence[float],
    *,
    tolerance: float = 0.0,
) -> bool:
    return (
        outer[0] - tolerance <= inner[0]
        and outer[1] - tolerance <= inner[1]
        and inner[2] <= outer[2] + tolerance
        and inner[3] <= outer[3] + tolerance
    )


def _union_bbox(rectangles: Sequence[Sequence[float]]) -> list[float]:
    return [
        round(min(rect[0] for rect in rectangles), 4),
        round(min(rect[1] for rect in rectangles), 4),
        round(max(rect[2] for rect in rectangles), 4),
        round(max(rect[3] for rect in rectangles), 4),
    ]


def _page_bodies(canonical_source_text: str) -> dict[int, str]:
    pages: dict[int, str] = {}
    for locator, body in source_units(canonical_source_text):
        match = re.fullmatch(r"PAGE:([1-9]\d*)", locator)
        if not match:
            continue
        page = int(match.group(1))
        if page in pages:
            raise ValueError(f"duplicate canonical PDF page: {page}")
        pages[page] = body
    return pages


def _segments_by_page(
    layout_sidecar: Mapping[str, Any],
) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for value in layout_sidecar.get("segments") or []:
        if not isinstance(value, Mapping):
            raise ValueError("PDF layout sidecar segment must be an object")
        page = int(value["page"])
        bbox = value.get("bbox")
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise ValueError("PDF layout sidecar segment bbox must have four coordinates")
        result.setdefault(page, []).append(
            {
                "page": page,
                "order": int(value.get("order") or 0),
                "bbox": [float(item) for item in bbox],
                "kind": str(value.get("kind") or "unknown"),
                "native_kind": str(value.get("native_kind") or "unknown"),
                "reason": str(value.get("reason") or ""),
                "text": str(value.get("text") or ""),
            }
        )
    return result


def load_pymupdf_word_pages(
    source_path: Path,
    page_numbers: Iterable[int],
) -> dict[int, list[dict[str, Any]]]:
    """Read word geometry only; never invoke layout/table detection."""
    import pymupdf

    if pymupdf.VersionBind != PYMUPDF_VERSION:
        raise RuntimeError(
            f"PyMuPDF version mismatch: expected {PYMUPDF_VERSION}, "
            f"found {pymupdf.VersionBind}"
        )
    requested = sorted(set(int(page) for page in page_numbers))
    document = pymupdf.open(Path(source_path))
    try:
        if any(page < 1 or page > len(document) for page in requested):
            raise ValueError("authoritative PDF page is outside the document")
        return {
            page: [
                {
                    "bbox": [round(float(item), 6) for item in word[:4]],
                    "text": str(word[4]),
                    "block": int(word[5]),
                    "line": int(word[6]),
                    "word": int(word[7]),
                }
                for word in document[page - 1].get_text("words", sort=True)
            ]
            for page in requested
        }
    finally:
        document.close()


def _word_stream(words: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    chunks: list[str] = []
    char_word_indices: list[int] = []
    for index, word in enumerate(words):
        normalized = _normalize_geometry_text(str(word.get("text") or ""))
        chunks.append(normalized)
        char_word_indices.extend([index] * len(normalized))
    return {
        "text": "".join(chunks),
        "char_word_indices": char_word_indices,
    }


def _geometry_occurrences(
    evidence: str,
    words: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    stream = _word_stream(words)
    needle = _normalize_geometry_text(evidence)
    geometries = []
    for start in _all_occurrences(stream["text"], needle):
        indices = sorted(
            set(stream["char_word_indices"][start : start + len(needle)])
        )
        if not indices:
            continue
        word_bboxes = [
            [float(item) for item in words[index]["bbox"]]
            for index in indices
        ]
        geometries.append(
            {
                "stream_start": start,
                "word_indices": indices,
                "word_bboxes": word_bboxes,
                "union_bbox": _union_bbox(word_bboxes),
            }
        )
    return geometries


def _canonical_page_binding(
    *,
    page_body: str | None,
    evidence: str,
    source_locator: Mapping[str, Any],
) -> dict[str, Any]:
    normalizer = _comparison_normalizer(source_locator)
    if page_body is None or normalizer is None:
        return {"locator_slice_verified": False, "occurrence_count": 0}
    normalized_body = normalizer(page_body)
    normalized_evidence = normalizer(evidence)
    starts = _all_occurrences(normalized_body, normalized_evidence)
    comparison_start = source_locator.get("comparison_start")
    comparison_end = source_locator.get("comparison_end")
    locator_slice_verified = (
        isinstance(comparison_start, int)
        and isinstance(comparison_end, int)
        and 0 <= comparison_start <= comparison_end <= len(normalized_body)
        and normalized_body[comparison_start:comparison_end] == normalized_evidence
    )
    return {
        "locator_slice_verified": locator_slice_verified,
        "occurrence_count": len(starts),
        "occurrence_starts": starts,
    }


def _competing_narrative_occurrences(
    evidence: str,
    segments_by_page: Mapping[int, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    needle = _normalize_geometry_text(evidence)
    matches: list[dict[str, Any]] = []
    if not needle:
        return matches
    for page, segments in segments_by_page.items():
        for segment in segments:
            if segment.get("native_kind") not in PROTECTED_LAYOUT_KINDS:
                continue
            starts = _all_occurrences(
                _normalize_geometry_text(str(segment.get("text") or "")), needle
            )
            if starts:
                matches.append(
                    {
                        "page": page,
                        "order": segment.get("order"),
                        "native_kind": segment.get("native_kind"),
                        "bbox": copy.deepcopy(segment.get("bbox")),
                        "occurrence_count": len(starts),
                    }
                )
    return matches


def _decision_for_claim(
    *,
    claim: Mapping[str, Any],
    page_bodies: Mapping[int, str],
    segments_by_page: Mapping[int, Sequence[Mapping[str, Any]]],
    word_pages: Mapping[int, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    claim_id = str(claim.get("claim_id") or "")
    evidence = str(claim.get("evidence_excerpt") or "")
    evidence_contract = claim.get("phase3c_evidence") or {}
    authoritative = evidence_contract.get("resolved_locator") or {}
    authoritative_resolved = (
        authoritative.get("status") == "resolved"
        and authoritative.get("authoritative") is True
    )
    single_page = authoritative_resolved and authoritative.get("kind") == "single_page"
    locator = str(authoritative.get("locator") or "") if single_page else ""
    page_match = re.fullmatch(r"PAGE:([1-9]\d*)", locator)
    page = int(page_match.group(1)) if page_match else None

    validation = claim.get("validation") or {}
    source_locator = validation.get("source_locator") or {}
    canonical = _canonical_page_binding(
        page_body=page_bodies.get(page) if page else None,
        evidence=evidence,
        source_locator=source_locator,
    )
    geometries = (
        _geometry_occurrences(evidence, word_pages.get(page) or [])
        if page is not None
        else []
    )
    geometry = geometries[0] if len(geometries) == 1 else None
    page_segments = list(segments_by_page.get(page) or []) if page else []
    tables = [
        segment for segment in page_segments if segment.get("native_kind") == "table"
    ]
    protected = [
        segment
        for segment in page_segments
        if segment.get("native_kind") in PROTECTED_LAYOUT_KINDS
    ]
    containing_tables = []
    if geometry is not None:
        containing_tables = [
            table
            for table in tables
            if all(
                _contains(
                    table["bbox"],
                    word_bbox,
                    tolerance=SIDECAR_BBOX_SERIALIZATION_TOLERANCE_PT,
                )
                for word_bbox in geometry["word_bboxes"]
            )
        ]
    selected_table = containing_tables[0] if len(containing_tables) == 1 else None
    protected_overlaps = (
        [
            {
                "page": page,
                "order": segment.get("order"),
                "native_kind": segment.get("native_kind"),
                "bbox": copy.deepcopy(segment.get("bbox")),
                "intersection_area_pt2": round(
                    _intersection_area(selected_table["bbox"], segment["bbox"]), 6
                ),
            }
            for segment in protected
            if _intersection_area(selected_table["bbox"], segment["bbox"])
            > PROTECTED_LAYOUT_INTERSECTION_AREA_PT2
        ]
        if selected_table is not None
        else []
    )
    narrative_occurrences = _competing_narrative_occurrences(
        evidence, segments_by_page
    )

    checks = {
        "authoritative_locator_resolved": authoritative_resolved,
        "authoritative_locator_single_page": single_page and page is not None,
        "canonical_locator_slice_verified": canonical["locator_slice_verified"],
        "canonical_authoritative_page_occurrence_count": canonical["occurrence_count"],
        "canonical_authoritative_page_occurrence_unique": (
            canonical["occurrence_count"] == 1
        ),
        "page_local_word_geometry_occurrence_count": len(geometries),
        "page_local_word_geometry_occurrence_unique": len(geometries) == 1,
        "containing_native_table_count": len(containing_tables),
        "evidence_words_fully_inside_exactly_one_native_table": (
            len(containing_tables) == 1
        ),
        "native_table_protected_overlap_count": len(protected_overlaps),
        "native_table_has_no_protected_overlap": not protected_overlaps,
        "competing_narrative_occurrence_count": len(narrative_occurrences),
        "no_competing_narrative_occurrence": not narrative_occurrences,
    }
    ineligible = all(
        (
            checks["authoritative_locator_resolved"],
            checks["authoritative_locator_single_page"],
            checks["canonical_locator_slice_verified"],
            checks["canonical_authoritative_page_occurrence_unique"],
            checks["page_local_word_geometry_occurrence_unique"],
            checks["evidence_words_fully_inside_exactly_one_native_table"],
            checks["native_table_has_no_protected_overlap"],
            checks["no_competing_narrative_occurrence"],
        )
    )
    failed_checks = [
        name
        for name, passed in checks.items()
        if name
        in {
            "authoritative_locator_resolved",
            "authoritative_locator_single_page",
            "canonical_locator_slice_verified",
            "canonical_authoritative_page_occurrence_unique",
            "page_local_word_geometry_occurrence_unique",
            "evidence_words_fully_inside_exactly_one_native_table",
            "native_table_has_no_protected_overlap",
            "no_competing_narrative_occurrence",
        }
        and not passed
    ]
    return {
        "claim_id": claim_id,
        "review_eligible": not ineligible,
        "eligibility_decision": (
            TABLE_DERIVED_CLAIM_INELIGIBLE
            if ineligible
            else TABLE_CLAIM_ELIGIBLE_FAIL_OPEN
        ),
        "decision_reason": (
            TABLE_DERIVED_CLAIM_INELIGIBLE
            if ineligible
            else "KEEP_FAIL_OPEN:" + ",".join(failed_checks)
        ),
        "safety_boundary_version": TABLE_CLAIM_SAFETY_BOUNDARY_VERSION,
        "immutable_evidence_excerpt": evidence,
        "authoritative_evidence_locator": copy.deepcopy(authoritative),
        "canonical_source_locator": copy.deepcopy(source_locator),
        "native_table_bbox": (
            copy.deepcopy(selected_table.get("bbox")) if selected_table else None
        ),
        "native_table_effective_kind": (
            selected_table.get("kind") if selected_table else None
        ),
        "native_table_reason": (
            selected_table.get("reason") if selected_table else None
        ),
        "evidence_geometry": copy.deepcopy(geometry),
        "protected_narrative_overlaps": protected_overlaps,
        "competing_narrative_occurrences": narrative_occurrences,
        "checks": checks,
        "upstream_effective_table_suppression_leak": bool(
            ineligible and selected_table and selected_table.get("kind") == "table"
        ),
    }


def apply_table_claim_safety_boundary_v1(
    *,
    canonical_source_text: str,
    layout_sidecar: Mapping[str, Any],
    claims: Sequence[Mapping[str, Any]],
    word_pages: Mapping[int, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Split post-binding Claims without mutating raw Claim or Evidence content."""
    raw_before = _canonical_sha256(claims)
    pages = _page_bodies(canonical_source_text)
    segments = _segments_by_page(layout_sidecar)
    decisions = [
        _decision_for_claim(
            claim=claim,
            page_bodies=pages,
            segments_by_page=segments,
            word_pages=word_pages,
        )
        for claim in claims
    ]
    raw_after = _canonical_sha256(claims)
    if raw_before != raw_after:
        raise RuntimeError("table Claim safety boundary mutated raw Claims")
    ineligible = [
        decision
        for decision in decisions
        if decision["eligibility_decision"] == TABLE_DERIVED_CLAIM_INELIGIBLE
    ]
    eligible_ids = [
        decision["claim_id"] for decision in decisions if decision["review_eligible"]
    ]
    return {
        "boundary": "TABLE_DERIVED_CLAIM_SAFETY_BOUNDARY",
        "version": TABLE_CLAIM_SAFETY_BOUNDARY_VERSION,
        "policy": "NARRATIVE_FIRST_TABLE_SUPPRESSION",
        "raw_claims": len(claims),
        "review_eligible_claims": len(eligible_ids),
        "table_derived_claims_ineligible": len(ineligible),
        "review_eligible_claim_ids": eligible_ids,
        "table_derived_ineligible_claim_ids": [
            decision["claim_id"] for decision in ineligible
        ],
        "decisions": decisions,
        "ineligible_claim_audit": ineligible,
        "upstream_effective_table_suppression_leak_count": sum(
            decision["upstream_effective_table_suppression_leak"]
            for decision in decisions
        ),
        "raw_claims_sha256_pre": raw_before,
        "raw_claims_sha256_post": raw_after,
        "raw_claims_unchanged": raw_before == raw_after,
        "claim_wording_used": False,
        "attributed_to_used": False,
        "numeric_or_financial_heuristics_used": False,
        "model_confidence_used": False,
        "table_detection_invoked": False,
    }
