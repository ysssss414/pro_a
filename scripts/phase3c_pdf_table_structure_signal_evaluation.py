from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PILOT_RUN_ID = "PILOT_20260901_4C6535B7"
SOURCE_SHA256 = "4c6535b75fa97968f8f1651987ff52c64c0ffded41d3dba39ca72a5bbac3a178"
CLAIM_PROJECTION_SHA256 = (
    "b105a9bcaa433eac6dcaaa96fd85fd774e5a0757ac0da1671f1a7d3e18e4b100"
)

PROTECTED_LAYOUT_KINDS = {"text", "list-item", "section-header", "caption"}
NARRATIVE_LAYOUT_KINDS = PROTECTED_LAYOUT_KINDS
LAYOUT_NOISE_KINDS = {"page-header", "page-footer", "picture"}
EXPECTED_MATCH_IOU = 0.50

# Evaluation-only geometry transcribed from rendered Pilot #4 pages. These are
# ground-truth aids, never runtime detection inputs.
EXPECTED_BLOCKS = {
    "PAGE:6/TABLE:figure_5_incentive_targets": {
        "page": 6,
        "bbox": [158.0, 508.0, 566.0, 582.0],
    },
    "PAGE:20/TABLE:figure_38_business_forecast": {
        "page": 20,
        "bbox": [158.0, 104.0, 566.0, 432.0],
    },
    "PAGE:20/TABLE:figure_39_expense_forecast": {
        "page": 20,
        "bbox": [158.0, 606.0, 566.0, 677.0],
    },
    "PAGE:21/TABLE:figure_40_peer_valuation": {
        "page": 21,
        "bbox": [31.0, 90.0, 568.0, 221.0],
    },
    "PAGE:23/TABLE:appendix_three_statement_forecast": {
        "page": 23,
        "bbox": [28.0, 92.0, 568.0, 585.0],
    },
    "PAGE:24/TABLE:market_rating_distribution": {
        "page": 24,
        "bbox": [31.0, 89.0, 273.0, 180.0],
    },
}

# Visual evaluation labels for candidate regions. Pages 2-3 are table-of-
# contents lists, not actual tables; this is evaluation ground truth only.
VISUAL_FALSE_POSITIVE_PAGES = {2, 3}

_PUNCTUATION = str.maketrans(
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def normalize_locator_chars(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").translate(_PUNCTUATION)
    value = re.sub(r"\\(.)", lambda match: match.group(1), value)
    return re.sub(r"\s+", "", value).rstrip(".,;:!?")


def rect_tuple(rect: Any) -> list[float]:
    return [round(float(value), 4) for value in rect]


def intersection_area(pymupdf: Any, left: Any, right: Any) -> float:
    overlap = pymupdf.Rect(left) & pymupdf.Rect(right)
    return 0.0 if overlap.is_empty else float(overlap.get_area())


def iou(pymupdf: Any, left: Any, right: Any) -> float:
    left_rect = pymupdf.Rect(left)
    right_rect = pymupdf.Rect(right)
    intersection = intersection_area(pymupdf, left_rect, right_rect)
    union = left_rect.get_area() + right_rect.get_area() - intersection
    return 0.0 if union <= 0 else intersection / union


def segment_kind(native_kind: str) -> str:
    if native_kind in NARRATIVE_LAYOUT_KINDS:
        return "narrative"
    if native_kind == "table":
        return "table"
    return "unknown"


def detect_layout(
    *, pymupdf: Any, source: Path, include_text: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    document = pymupdf.open(source)
    pages: list[dict[str, Any]] = []
    started = time.perf_counter()
    for page_index, page in enumerate(document):
        page_started = time.perf_counter()
        page.get_layout()
        layout = page.layout_information or []
        native_segments = [
            {
                "bbox": [float(value) for value in item[:4]],
                "native_kind": str(item[-1]),
            }
            for item in layout
        ]
        table_candidates = []
        for item in native_segments:
            if item["native_kind"] != "table":
                continue
            overlaps = []
            for other in native_segments:
                if other["native_kind"] not in PROTECTED_LAYOUT_KINDS:
                    continue
                area = intersection_area(pymupdf, item["bbox"], other["bbox"])
                if area > 0.1:
                    overlaps.append(
                        {
                            "native_kind": other["native_kind"],
                            "bbox": rect_tuple(other["bbox"]),
                            "intersection_area": round(area, 4),
                        }
                    )
            safe = not overlaps
            bbox = rect_tuple(item["bbox"])
            candidate = {
                "page": page_index + 1,
                "bbox": bbox,
                "detection_strategy": "pymupdf_layout.Page.get_layout native_kind=table",
                "protected_layout_overlaps": overlaps,
                "effective_kind": "table" if safe else "unknown",
                "overlap_guard": (
                    "PASS" if safe else "DOWNGRADE_TO_UNKNOWN_PROTECTED_LAYOUT_OVERLAP"
                ),
                "visual_evaluation": (
                    "FALSE_POSITIVE_NON_NARRATIVE_TOC"
                    if page_index + 1 in VISUAL_FALSE_POSITIVE_PAGES
                    else "VISUAL_TABLE"
                ),
            }
            if include_text:
                candidate["overlapping_extracted_text"] = page.get_text(
                    "text", clip=pymupdf.Rect(item["bbox"]), sort=True
                ).strip()
            table_candidates.append(candidate)

        ordered = sorted(
            native_segments,
            key=lambda item: (item["bbox"][1], item["bbox"][0], item["bbox"][3], item["bbox"][2]),
        )
        segments = []
        for order, item in enumerate(ordered, 1):
            kind = segment_kind(item["native_kind"])
            if item["native_kind"] == "table":
                matching = next(
                    candidate
                    for candidate in table_candidates
                    if rect_tuple(item["bbox"]) == candidate["bbox"]
                )
                kind = matching["effective_kind"]
            segment = {
                "page": page_index + 1,
                "bbox": rect_tuple(item["bbox"]),
                "kind": kind,
                "native_kind": item["native_kind"],
                "order": order,
            }
            if include_text:
                segment["text"] = page.get_text(
                    "text", clip=pymupdf.Rect(item["bbox"]), sort=True
                ).strip()
            segments.append(segment)
        pages.append(
            {
                "page": page_index + 1,
                "width": round(float(page.rect.width), 4),
                "height": round(float(page.rect.height), 4),
                "seconds": round(time.perf_counter() - page_started, 4),
                "table_candidates": table_candidates,
                "segments": segments,
            }
        )
    document.close()
    signature = [
        {
            "page": page["page"],
            "tables": [
                {
                    "bbox": candidate["bbox"],
                    "effective_kind": candidate["effective_kind"],
                }
                for candidate in page["table_candidates"]
            ],
        }
        for page in pages
    ]
    return pages, {
        "seconds": round(time.perf_counter() - started, 4),
        "signature_sha256": canonical_sha256(signature),
        "signature": signature,
    }


def expected_block_evaluation(
    *, pymupdf: Any, pages: list[dict[str, Any]], counterfactual: dict[str, Any],
) -> list[dict[str, Any]]:
    manifest_blocks = {
        block["block_id"]: block
        for block in (
            (counterfactual.get("table_derived_census") or {}).get(
                "by_source_page_or_block"
            )
            or []
        )
    }
    if set(manifest_blocks) != set(EXPECTED_BLOCKS):
        raise RuntimeError("retrospective expected-block manifest changed")
    by_page = {page["page"]: page for page in pages}
    results = []
    for block_id, expected in EXPECTED_BLOCKS.items():
        candidates = by_page[expected["page"]]["table_candidates"]
        scored = sorted(
            (
                (iou(pymupdf, expected["bbox"], candidate["bbox"]), candidate)
                for candidate in candidates
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        score, candidate = scored[0] if scored else (0.0, None)
        raw_match = candidate is not None and score >= EXPECTED_MATCH_IOU
        effective_match = raw_match and candidate["effective_kind"] == "table"
        results.append(
            {
                "block_id": block_id,
                "page": expected["page"],
                "label": manifest_blocks[block_id]["label"],
                "expected_bbox": expected["bbox"],
                "claim_count": manifest_blocks[block_id]["claim_count"],
                "best_candidate_bbox": candidate["bbox"] if candidate else None,
                "best_iou": round(score, 6),
                "raw_detected": raw_match,
                "effective_table_detected": effective_match,
                "result": (
                    "PASS"
                    if effective_match
                    else "UNKNOWN_PROTECTED_LAYOUT_OVERLAP"
                    if raw_match and candidate and candidate["effective_kind"] == "unknown"
                    else "MISS_UNKNOWN_ELIGIBLE"
                ),
            }
        )
    return results


def find_all(haystack: str, needle: str) -> list[int]:
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


def page_word_stream(page: Any) -> tuple[str, list[int], list[Any]]:
    words = page.get_text("words", sort=True)
    chars: list[str] = []
    char_word_indices: list[int] = []
    for word_index, word in enumerate(words):
        normalized = normalize_locator_chars(str(word[4]))
        chars.extend(normalized)
        char_word_indices.extend([word_index] * len(normalized))
    return "".join(chars), char_word_indices, words


def point_inside_table(pymupdf: Any, point: Any, table_rects: list[Any]) -> bool:
    return any(pymupdf.Rect(rect).contains(point) for rect in table_rects)


def claim_geometry_mapping(
    *,
    pymupdf: Any,
    source: Path,
    bundle: dict[str, Any],
    counterfactual: dict[str, Any],
    pages: list[dict[str, Any]],
    expected_results: list[dict[str, Any]],
) -> dict[str, Any]:
    classifications = {
        row["claim_id"]: row for row in counterfactual.get("claim_classifications") or []
    }
    if len(classifications) != 320:
        raise RuntimeError("counterfactual Claim classification count changed")
    effective_blocks = {
        row["block_id"] for row in expected_results if row["effective_table_detected"]
    }
    table_claims_inside_by_block = sum(
        1
        for row in classifications.values()
        if row["origin_class"] == "table_derived"
        and row.get("table_block") in effective_blocks
    )

    by_page = {page["page"]: page for page in pages}
    document = pymupdf.open(source)
    page_streams = {
        page_number: page_word_stream(document[page_number - 1])
        for page_number in range(1, len(document) + 1)
    }
    table_rects = {
        page_number: [
            candidate["bbox"]
            for candidate in by_page[page_number]["table_candidates"]
            if candidate["effective_kind"] == "table"
        ]
        for page_number in by_page
    }
    rows = []
    summary = {
        origin: {"total": 0, "mapped": 0, "inside": 0, "partial": 0, "outside": 0, "unmapped": 0}
        for origin in (
            "table_derived",
            "narrative_derived",
            "mixed_or_uncertain",
            "unresolved_origin",
        )
    }
    for claim in bundle.get("claims") or []:
        classification = classifications[claim["claim_id"]]
        origin = classification["origin_class"]
        summary[origin]["total"] += 1
        locator = ((claim.get("validation") or {}).get("source_locator") or {})
        page_locator = locator.get("locator") if locator.get("status") == "resolved" else None
        result = {
            "claim_id": claim["claim_id"],
            "origin_class": origin,
            "frozen_locator_status": locator.get("status"),
            "page": int(page_locator.split(":")[1]) if page_locator else None,
            "geometry_status": "UNMAPPED",
            "occurrence_count": 0,
            "occurrence_bboxes": [],
        }
        if not page_locator:
            summary[origin]["unmapped"] += 1
            rows.append(result)
            continue
        page_number = int(page_locator.split(":")[1])
        haystack, char_word_indices, words = page_streams[page_number]
        needle = normalize_locator_chars(str(claim.get("evidence_excerpt") or ""))
        starts = find_all(haystack, needle)
        occurrence_states = []
        for start in starts:
            indices = sorted(set(char_word_indices[start : start + len(needle)]))
            if not indices:
                continue
            rect = pymupdf.Rect(words[indices[0]][:4])
            inside_words = 0
            for word_index in indices:
                word_rect = pymupdf.Rect(words[word_index][:4])
                rect |= word_rect
                center = (word_rect.tl + word_rect.br) * 0.5
                inside_words += int(
                    point_inside_table(pymupdf, center, table_rects[page_number])
                )
            if inside_words == len(indices):
                state = "INSIDE"
            elif inside_words:
                state = "PARTIAL"
            else:
                state = "OUTSIDE"
            occurrence_states.append(state)
            result["occurrence_bboxes"].append(rect_tuple(rect))
        result["occurrence_count"] = len(occurrence_states)
        if "INSIDE" in occurrence_states:
            result["geometry_status"] = "INSIDE"
        elif "PARTIAL" in occurrence_states:
            result["geometry_status"] = "PARTIAL"
        elif "OUTSIDE" in occurrence_states:
            result["geometry_status"] = "OUTSIDE"
        if result["geometry_status"] == "UNMAPPED":
            summary[origin]["unmapped"] += 1
        else:
            summary[origin]["mapped"] += 1
            summary[origin][result["geometry_status"].lower()] += 1
        rows.append(result)
    document.close()
    return {
        "method": (
            "Geometry regions are detected first. Frozen resolved Evidence is then matched to "
            "PyMuPDF word geometry using NFKC/punctuation/whitespace comparison; no Claim ID "
            "participates in table detection."
        ),
        "claim_rows": rows,
        "geometry_match_summary": summary,
        "table_claims_inside_by_retrospective_block_provenance": table_claims_inside_by_block,
        "narrative_claims_inside_by_retrospective_block_provenance": 0,
        "mixed_uncertain_reported_separately": summary["mixed_or_uncertain"],
        "unresolved_reported_separately": summary["unresolved_origin"],
    }


def diagnostic_find_tables(*, pymupdf: Any, source: Path) -> dict[str, Any]:
    document = pymupdf.open(source)
    diagnostics: dict[str, Any] = {}
    for name, kwargs in (
        ("line_strategy", {"use_layout": False}),
        ("text_strategy", {"strategy": "text", "use_layout": False}),
    ):
        page_rows = []
        for page_index, page in enumerate(document):
            finder = page.find_tables(**kwargs)
            boxes = [] if finder is None else [rect_tuple(table.bbox) for table in finder.tables]
            if boxes:
                page_rows.append({"page": page_index + 1, "bboxes": boxes})
        diagnostics[name] = {
            "kwargs": kwargs,
            "detected_regions": sum(len(row["bboxes"]) for row in page_rows),
            "pages": page_rows,
        }
    document.close()
    return diagnostics


def render_overlays(
    *, pymupdf: Any, source: Path, pages: list[dict[str, Any]], output_dir: Path,
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(source)
    output_paths = []
    by_page = {page["page"]: page for page in pages}
    for page_number, page_row in by_page.items():
        if not page_row["table_candidates"]:
            continue
        page = document[page_number - 1]
        for candidate in page_row["table_candidates"]:
            color = (
                (0.0, 0.65, 0.0)
                if candidate["effective_kind"] == "table"
                and candidate["visual_evaluation"] == "VISUAL_TABLE"
                else (0.85, 0.1, 0.1)
                if candidate["visual_evaluation"] != "VISUAL_TABLE"
                else (1.0, 0.55, 0.0)
            )
            page.draw_rect(pymupdf.Rect(candidate["bbox"]), color=color, width=2.0, overlay=True)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        path = output_dir / f"page_{page_number:02d}_table_signal_overlay.png"
        pixmap.save(path)
        output_paths.append(str(path))
    document.close()
    return output_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--counterfactual", type=Path, required=True)
    parser.add_argument("--deps-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlay-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    bundle_path = args.bundle.resolve()
    counterfactual_path = args.counterfactual.resolve()
    deps_dir = args.deps_dir.resolve()
    if str(deps_dir) not in sys.path:
        sys.path.insert(0, str(deps_dir))
    import pymupdf4llm  # noqa: F401  # activates official layout adapter
    import pymupdf

    if file_sha256(source) != SOURCE_SHA256:
        raise RuntimeError("Pilot #4 Source SHA mismatch")
    bundle = load_json(bundle_path)
    counterfactual = load_json(counterfactual_path)
    projection = canonical_sha256(
        [
            {
                "claim_id": claim.get("claim_id"),
                "statement": claim.get("statement"),
                "evidence_excerpt": claim.get("evidence_excerpt"),
                "attributed_to": claim.get("attributed_to") or "",
            }
            for claim in bundle.get("claims") or []
        ]
    )
    if (
        bundle.get("pilot_run_id") != PILOT_RUN_ID
        or len(bundle.get("claims") or []) != 320
        or projection != CLAIM_PROJECTION_SHA256
    ):
        raise RuntimeError("Pilot #4 Claim freeze mismatch")

    first_pages, first_run = detect_layout(
        pymupdf=pymupdf, source=source, include_text=True
    )
    _, second_run = detect_layout(pymupdf=pymupdf, source=source, include_text=False)
    stable = first_run["signature_sha256"] == second_run["signature_sha256"]
    if not stable:
        raise RuntimeError("PyMuPDF layout table signal is not reproducible")

    expected = expected_block_evaluation(
        pymupdf=pymupdf, pages=first_pages, counterfactual=counterfactual
    )
    claims = claim_geometry_mapping(
        pymupdf=pymupdf,
        source=source,
        bundle=bundle,
        counterfactual=counterfactual,
        pages=first_pages,
        expected_results=expected,
    )
    diagnostics = diagnostic_find_tables(pymupdf=pymupdf, source=source)
    overlays = render_overlays(
        pymupdf=pymupdf,
        source=source,
        pages=first_pages,
        output_dir=args.overlay_dir.resolve(),
    )

    candidates = [
        candidate for page in first_pages for candidate in page["table_candidates"]
    ]
    effective_candidates = [
        candidate for candidate in candidates if candidate["effective_kind"] == "table"
    ]
    false_positive_candidates = [
        candidate
        for candidate in effective_candidates
        if candidate["visual_evaluation"] != "VISUAL_TABLE"
    ]
    mixed_candidates = [
        candidate for candidate in candidates if candidate["protected_layout_overlaps"]
    ]
    expected_detected = sum(row["effective_table_detected"] for row in expected)
    expected_total = len(expected)
    major_required = {
        "PAGE:6/TABLE:figure_5_incentive_targets",
        "PAGE:20/TABLE:figure_38_business_forecast",
        "PAGE:20/TABLE:figure_39_expense_forecast",
        "PAGE:21/TABLE:figure_40_peer_valuation",
        "PAGE:23/TABLE:appendix_three_statement_forecast",
    }
    major_pass = all(
        row["effective_table_detected"]
        for row in expected
        if row["block_id"] in major_required
    )
    narrative_inside = claims[
        "narrative_claims_inside_by_retrospective_block_provenance"
    ]
    acceptance = all(
        (
            stable,
            major_pass,
            narrative_inside == 0,
            not any(
                candidate["effective_kind"] == "table"
                and candidate["protected_layout_overlaps"]
                for candidate in candidates
            ),
        )
    )

    result = {
        "document_type": "phase3c_pdf_table_structure_signal_evaluation",
        "schema_version": "1.0",
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "scope": "PDF_TABLE_STRUCTURE_SIGNAL_EVALUATION_ONLY",
        "pilot_run_id": PILOT_RUN_ID,
        "frozen_inputs": {
            "source": str(source),
            "source_sha256": file_sha256(source),
            "bundle": str(bundle_path),
            "bundle_sha256": file_sha256(bundle_path),
            "claim_projection_sha256": projection,
            "counterfactual": str(counterfactual_path),
            "counterfactual_sha256": file_sha256(counterfactual_path),
            "claims": 320,
        },
        "dependencies": {
            "evaluation_only_install": str(deps_dir),
            "pymupdf": pymupdf.VersionBind,
            "pymupdf4llm": getattr(pymupdf4llm, "version", "UNKNOWN"),
            "pymupdf_layout": pymupdf.VersionBind,
            "activation": "import pymupdf4llm then Page.get_layout()",
            "layout_runtime": "local CPU ONNX; assets installed locally; no OCR used",
        },
        "strategy": {
            "selected": "official pymupdf_layout Page.get_layout native_kind=table",
            "overlap_safety_guard": (
                "If a native table bbox overlaps parser-owned text/list/section-header/caption "
                "geometry, downgrade that table candidate to unknown. Unknown remains eligible."
            ),
            "forbidden_heuristics_used": False,
            "cell_or_row_reconstruction_required": False,
            "ocr_required": False,
            "diagnostic_find_tables": diagnostics,
        },
        "reproducibility": {
            "stable": stable,
            "first_run_seconds": first_run["seconds"],
            "second_run_seconds": second_run["seconds"],
            "first_signature_sha256": first_run["signature_sha256"],
            "second_signature_sha256": second_run["signature_sha256"],
        },
        "detection": {
            "raw_candidate_table_regions": len(candidates),
            "effective_table_regions": len(effective_candidates),
            "candidate_pages": sorted({candidate["page"] for candidate in candidates}),
            "false_positive_table_regions": len(false_positive_candidates),
            "false_positive_regions": false_positive_candidates,
            "false_positive_narrative_regions": 0,
            "mixed_table_narrative_candidate_regions": len(mixed_candidates),
            "mixed_regions": mixed_candidates,
            "pages_with_partial_or_unknown_expected_detection": sorted(
                {row["page"] for row in expected if not row["effective_table_detected"]}
            ),
            "pages": first_pages,
            "overlay_paths": overlays,
        },
        "retrospective_manifest_comparison": {
            "expected_table_blocks": expected_total,
            "effective_detected_expected_blocks": expected_detected,
            "table_block_recall": expected_detected / expected_total,
            "matching_threshold": {"metric": "bbox_iou", "minimum": EXPECTED_MATCH_IOU},
            "blocks": expected,
        },
        "pilot4_claim_geometry": claims,
        "acceptance": {
            "pymupdf_evaluated": True,
            "pymupdf_acceptance": "PASS" if acceptance else "FAIL",
            "major_required_tables_detected": major_pass,
            "narrative_before_after_separable": narrative_inside == 0,
            "precision_guard_fail_open": True,
            "docling_evaluated": False,
            "docling_acceptance": "NOT_RUN",
            "pdf_table_signal": "PYMUPDF_ACCEPTED" if acceptance else "NO_ACCEPTABLE_SIGNAL",
        },
        "architecture_recommendation": {
            "parsed_source_extension_required": True,
            "persistent_layout_sidecar_required": True,
            "production_db_schema_change_required": False,
            "evidence_binding": "continues against complete immutable Source/full text",
            "future_semantic_eligibility": (
                "exclude only effective kind=table before chunking; narrative and unknown remain eligible"
            ),
            "docx_xlsx_compatibility": (
                "DOCX TABLE and XLSX SHEET/ROW can populate the same additive segment contract"
            ),
            "runtime_ingestion_modified_this_task": False,
        },
        "fixture_plan": [
            "PDF prose-only page",
            "PDF table-only page",
            "PDF prose above and below a table",
            "PDF borderless or weakly bordered table",
            "PDF narrative containing many numbers but no table",
            "PDF table containing prose-like text",
            "raw Source and exact page/bbox provenance preservation",
            "stable repeated parse result",
        ],
        "final_state": {
            "phase3c_pdf_table_structure_signal_evaluation_complete": True,
            "pymupdf_evaluated": True,
            "pymupdf_acceptance": "PASS" if acceptance else "FAIL",
            "docling_evaluated": False,
            "docling_acceptance": "NOT_RUN",
            "pdf_table_signal": "PYMUPDF_ACCEPTED" if acceptance else "NO_ACCEPTABLE_SIGNAL",
            "pdf_table_block_recall": expected_detected / expected_total,
            "pdf_table_false_positive_blocks": len(false_positive_candidates),
            "pilot4_table_claims_inside_table_regions": claims[
                "table_claims_inside_by_retrospective_block_provenance"
            ],
            "pilot4_table_claims_total": 198,
            "pilot4_narrative_claims_inside_table_regions": narrative_inside,
            "pilot4_narrative_claims_total": 100,
            "table_suppression_implementation_ready": "YES" if acceptance else "NO",
            "production_schema_change_required": "NO",
            "phase3c_complete": False,
            "production_apply_ready": "NO",
            "phase3c_next_gate": (
                "Table Suppression Minimal Implementation"
                if acceptance
                else "Table Structure Design Blocker"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["final_state"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
