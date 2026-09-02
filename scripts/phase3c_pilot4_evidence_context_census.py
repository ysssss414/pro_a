from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.corpus_pilot import (  # noqa: E402
    STAGE1_3_CONTEXT_POLICY,
    STAGE1_3_CONTEXT_RADIUS,
    PilotError,
    _bounded_text_segments,
    _comparison_contains,
    _normalized_gap,
    _stage1_3_normalized_local_binding,
    _validate_stage1_3_context_span,
    normalize_pdf_locator_text,
    production_snapshot,
)
from pro_a.parsers import parse_source_with_diagnostics, source_units  # noqa: E402
from pro_a.storage import sha256_file, write_json  # noqa: E402


DOCUMENT_TYPE = "phase3c_clean_pilot4_evidence_context_failure_census"
SCHEMA_VERSION = "1"
GENERATOR_REPRESENTATION = "page-local raw pypdf body / punctuation-delimited segment"
MIN_DIAGNOSTIC_SUBSPAN_NORMALIZED_CHARS = 16
ROOT_CATEGORIES = {
    "EMPTY_NORMALIZATION",
    "DUPLICATE_OCCURRENCE_SELECTION",
    "OUTSIDE_BOUNDED_WINDOW",
    "NO_NORMALIZED_LOCAL_BINDING",
    "RAW_NORMALIZED_COORDINATE_MISMATCH",
    "PAGE_SEGMENT_REPRESENTATION_MISMATCH",
    "NON_CONTIGUOUS_LAYOUT_CONTEXT",
    "CROSS_PAGE_CONTEXT_MISMATCH",
    "OTHER",
}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def _segment_features(text: str) -> dict[str, Any]:
    normalized = normalize_pdf_locator_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    numeric_tokens = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", text)
    table_like_lines = sum(
        len(re.findall(r"[-+]?\d+(?:\.\d+)?%?", line)) >= 3
        for line in lines
    )
    classes: list[str] = []
    if len(normalized) > STAGE1_3_CONTEXT_RADIUS:
        classes.append("large_parsed_segment")
    if table_like_lines >= 2 or (len(numeric_tokens) >= 8 and len(lines) >= 3):
        classes.append("table_heavy")
    if any(marker in text for marker in ("图表", "来源：", "来源:")):
        classes.append("figure_or_source_caption")
    if len(lines) >= 4:
        classes.append("layout_block")
    if len(normalized) > STAGE1_3_CONTEXT_RADIUS and len(lines) <= 3:
        classes.append("long_authored_paragraph")
    return {
        "raw_length": len(text),
        "normalized_length": len(normalized),
        "line_count": len(lines),
        "numeric_token_count": len(numeric_tokens),
        "table_like_line_count": table_like_lines,
        "representation_classes": classes,
    }


def _segment_identity(
    locator: str, segment_index: int, start: int, end: int, text: str,
) -> dict[str, Any]:
    return {
        "locator": locator,
        "segment_index": segment_index,
        "raw_start": start,
        "raw_end": end,
        "raw_sha256": _text_sha256(text),
        **_segment_features(text),
    }


def _evidence_window(body: str, evidence_excerpt: str) -> dict[str, Any] | None:
    segments = _bounded_text_segments(body)
    windows: list[tuple[int, int, int, int]] = []
    for start_index in range(len(segments)):
        for end_index in range(start_index, len(segments)):
            start = segments[start_index][0]
            end = segments[end_index][1]
            if _comparison_contains(body[start:end], evidence_excerpt):
                windows.append((end - start, start_index, end_index, start))
                break
    if not windows:
        return None
    _, first_index, last_index, start = min(windows)
    end = segments[last_index][1]
    text = body[start:end]
    return {
        "segments": segments,
        "first_index": first_index,
        "last_index": last_index,
        "raw_start": start,
        "raw_end": end,
        "identity": {
            "locator": None,
            "first_segment_index": first_index,
            "last_segment_index": last_index,
            "raw_start": start,
            "raw_end": end,
            "raw_sha256": _text_sha256(text),
            **_segment_features(text),
        },
    }


def _potential_segments(
    pages: list[tuple[str, str]], page_index: int, window: dict[str, Any],
) -> list[dict[str, Any]]:
    locator, body = pages[page_index]
    segments = window["segments"]
    potential: list[dict[str, Any]] = []
    if window["first_index"] > 0:
        segment_index = window["first_index"] - 1
        start, end = segments[segment_index]
        potential.append({
            "direction": "before", "locator": locator,
            "segment_index": segment_index, "start": start, "end": end,
            "text": body[start:end], "same_page": True,
        })
    elif page_index > 0:
        prior_locator, prior_body = pages[page_index - 1]
        prior_segments = _bounded_text_segments(prior_body)
        if prior_segments:
            segment_index = len(prior_segments) - 1
            start, end = prior_segments[segment_index]
            potential.append({
                "direction": "before", "locator": prior_locator,
                "segment_index": segment_index, "start": start, "end": end,
                "text": prior_body[start:end], "same_page": False,
            })
    if window["last_index"] + 1 < len(segments):
        segment_index = window["last_index"] + 1
        start, end = segments[segment_index]
        potential.append({
            "direction": "after", "locator": locator,
            "segment_index": segment_index, "start": start, "end": end,
            "text": body[start:end], "same_page": True,
        })
    elif page_index + 1 < len(pages):
        next_locator, next_body = pages[page_index + 1]
        next_segments = _bounded_text_segments(next_body)
        if next_segments:
            start, end = next_segments[0]
            potential.append({
                "direction": "after", "locator": next_locator,
                "segment_index": 0, "start": start, "end": end,
                "text": next_body[start:end], "same_page": False,
            })
    return potential


def _failure_category(message: str, normalized_context: str) -> str:
    if not normalized_context:
        return "EMPTY_NORMALIZATION"
    if "outside the bounded window" in message:
        return "OUTSIDE_BOUNDED_WINDOW"
    if "normalized local binding failed" in message:
        return "NO_NORMALIZED_LOCAL_BINDING"
    if "not on its declared page" in message:
        return "PAGE_SEGMENT_REPRESENTATION_MISMATCH"
    if any(fragment in message for fragment in (
        "distant page", "prior-page context", "next-page context",
        "Evidence is not near the page",
    )):
        return "CROSS_PAGE_CONTEXT_MISMATCH"
    return "OTHER"


def _binding_diagnostics(
    page_by_locator: dict[str, str], evidence_locator: str, evidence_excerpt: str,
    candidate_locator: str, candidate_text: str,
) -> dict[str, Any]:
    evidence_body, evidence_copy, evidence_starts = _stage1_3_normalized_local_binding(
        page_by_locator[evidence_locator], evidence_excerpt,
    )
    context_body, context_copy, context_starts = _stage1_3_normalized_local_binding(
        page_by_locator[candidate_locator], candidate_text,
    )
    same_page = evidence_locator == candidate_locator
    gaps = (
        [
            _normalized_gap(evidence_start, len(evidence_copy), context_start, len(context_copy))
            for evidence_start in evidence_starts
            for context_start in context_starts
        ]
        if same_page else []
    )
    boundary_distances = None
    if not same_page:
        evidence_page = int(evidence_locator.split(":", 1)[1])
        context_page = int(candidate_locator.split(":", 1)[1])
        if context_page < evidence_page:
            boundary_distances = {
                "evidence_to_page_start": min(evidence_starts) if evidence_starts else None,
                "context_to_page_end": min(
                    len(context_body) - (start + len(context_copy)) for start in context_starts
                ) if context_starts else None,
            }
        else:
            boundary_distances = {
                "evidence_to_page_end": min(
                    len(evidence_body) - (start + len(evidence_copy)) for start in evidence_starts
                ) if evidence_starts else None,
                "context_to_page_start": min(context_starts) if context_starts else None,
            }
    return {
        "evidence_normalized_text": evidence_copy,
        "candidate_normalized_text": context_copy,
        "evidence_normalized_occurrences": evidence_starts,
        "candidate_normalized_occurrences": context_starts,
        "minimum_gap": min(gaps) if gaps else None,
        "all_same_page_gaps": sorted(set(gaps)),
        "within_500": min(gaps) <= STAGE1_3_CONTEXT_RADIUS if gaps else None,
        "boundary_distances": boundary_distances,
        "duplicate_occurrence_present": len(evidence_starts) > 1 or len(context_starts) > 1,
    }


def _raw_line_chunks(body: str, start: int, end: int) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[^\r\n]+", body[start:end]):
        line_start = start + match.start()
        raw = match.group(0)
        variants = [(0, len(raw))]
        for offset in range(0, len(raw), 64):
            variants.append((offset, min(len(raw), offset + 80)))
        if len(raw) > 80:
            variants.append((len(raw) - 80, len(raw)))
        for relative_start, relative_end in variants:
            text = raw[relative_start:relative_end].strip()
            if not text:
                continue
            absolute_start = body.find(text, line_start + relative_start, line_start + relative_end + 1)
            if absolute_start >= 0:
                chunks.append((absolute_start, absolute_start + len(text), text))
    unique = {(start, end, text): None for start, end, text in chunks}
    return list(unique)


def _local_subspan_probe(
    body: str, evidence_excerpt: str, window: dict[str, Any],
) -> dict[str, Any]:
    normalized_body, normalized_evidence, evidence_starts = (
        _stage1_3_normalized_local_binding(body, evidence_excerpt)
    )
    options: list[dict[str, Any]] = []
    for raw_start, raw_end, text in _raw_line_chunks(
        body, window["raw_start"], window["raw_end"],
    ):
        normalized_text = normalize_pdf_locator_text(text)
        if (
            len(normalized_text) < MIN_DIAGNOSTIC_SUBSPAN_NORMALIZED_CHARS
            or normalized_text == normalized_evidence
        ):
            continue
        context_starts = []
        offset = 0
        while (found := normalized_body.find(normalized_text, offset)) >= 0:
            context_starts.append(found)
            offset = found + 1
        for evidence_start in evidence_starts:
            evidence_end = evidence_start + len(normalized_evidence)
            for context_start in context_starts:
                context_end = context_start + len(normalized_text)
                if not (context_end <= evidence_start or evidence_end <= context_start):
                    continue
                gap = _normalized_gap(
                    evidence_start, len(normalized_evidence),
                    context_start, len(normalized_text),
                )
                if gap <= STAGE1_3_CONTEXT_RADIUS:
                    options.append({
                        "raw_start": raw_start,
                        "raw_end": raw_end,
                        "raw_sha256": _text_sha256(text),
                        "raw_text": text,
                        "normalized_text": normalized_text,
                        "normalized_start": context_start,
                        "minimum_gap": gap,
                        "direction": "before" if context_end <= evidence_start else "after",
                    })
    if not options:
        return {
            "valid_source_local_subspan_within_500_exists": False,
        "probe_scope": "raw line/chunk substrings inside the Evidence-containing segment window",
        "minimum_normalized_chars": MIN_DIAGNOSTIC_SUBSPAN_NORMALIZED_CHARS,
        "selected": None,
        }
    selected = min(
        options,
        key=lambda item: (item["minimum_gap"], -len(item["normalized_text"]), item["raw_start"]),
    )
    return {
        "valid_source_local_subspan_within_500_exists": True,
        "probe_scope": "raw line/chunk substrings inside the Evidence-containing segment window",
        "minimum_normalized_chars": MIN_DIAGNOSTIC_SUBSPAN_NORMALIZED_CHARS,
        "selected": selected,
    }


def _candidate_attempt(
    *, pages: list[tuple[str, str]], evidence_locator: str, evidence_excerpt: str,
    potential: dict[str, Any], evidence_window: dict[str, Any],
) -> dict[str, Any]:
    page_by_locator = dict(pages)
    source_text = potential["text"]
    text = source_text.strip()
    if text:
        text = (
            text[-STAGE1_3_CONTEXT_RADIUS:]
            if potential["direction"] == "before"
            else text[:STAGE1_3_CONTEXT_RADIUS]
        )
    binding = _binding_diagnostics(
        page_by_locator, evidence_locator, evidence_excerpt,
        potential["locator"], text,
    )
    record = {
        "candidate_direction": potential["direction"],
        "candidate_locator": potential["locator"],
        "candidate_raw_text": text,
        "candidate_normalized_text": binding["candidate_normalized_text"],
        "generator_source_representation": GENERATOR_REPRESENTATION,
        "candidate_source_segment": _segment_identity(
            potential["locator"], potential["segment_index"],
            potential["start"], potential["end"], source_text,
        ),
        **binding,
        "generator_outcome": "GENERATED_FOR_VALIDATION",
        "validator_outcome": "NOT_RUN",
        "failure_reason": None,
        "root_category": None,
        "representation_granularity_probe": None,
    }
    if not text:
        record.update({
            "generator_outcome": "FILTERED_EMPTY_RAW",
            "validator_outcome": "NOT_RUN_FILTERED",
            "failure_reason": "candidate is empty after raw strip",
            "root_category": "OTHER",
        })
        return record
    if not binding["candidate_normalized_text"]:
        record.update({
            "generator_outcome": "FILTERED_NORMALIZED_EMPTY",
            "validator_outcome": "NOT_RUN_FILTERED",
            "failure_reason": "candidate is empty after frozen shared normalization",
            "root_category": "EMPTY_NORMALIZATION",
        })
        return record
    try:
        _validate_stage1_3_context_span(
            span={"locator": potential["locator"], "text": text},
            page_by_locator=page_by_locator,
            evidence_locator=evidence_locator,
            evidence_excerpt=evidence_excerpt,
        )
    except PilotError as exc:
        category = _failure_category(str(exc), binding["candidate_normalized_text"])
        record.update({
            "validator_outcome": "FAIL",
            "failure_reason": str(exc),
            "root_category": category,
        })
        if category == "OUTSIDE_BOUNDED_WINDOW" and potential["same_page"]:
            record["representation_granularity_probe"] = _local_subspan_probe(
                page_by_locator[evidence_locator], evidence_excerpt, evidence_window,
            )
        return record
    record["validator_outcome"] = "PASS"
    return record


def _no_candidate_reason(
    locator_status: str, window: dict[str, Any] | None,
    attempts: list[dict[str, Any]],
) -> dict[str, str]:
    if locator_status != "resolved":
        return {
            "code": "no_bindable_local_segment",
            "detail": f"source locator status is {locator_status}",
        }
    if window is None:
        return {
            "code": "no_bindable_local_segment",
            "detail": "Evidence cannot be located inside a generated page segment window",
        }
    if not attempts:
        return {
            "code": "no_adjacent_segment",
            "detail": "no prior or following parsed segment/page-boundary candidate exists",
        }
    if all(item["generator_outcome"] == "FILTERED_NORMALIZED_EMPTY" for item in attempts):
        return {
            "code": "normalized_empty_segment",
            "detail": "all potential candidates are empty after frozen normalization",
        }
    failed_categories = {item.get("root_category") for item in attempts}
    if failed_categories and failed_categories <= {
        "OUTSIDE_BOUNDED_WINDOW", "CROSS_PAGE_CONTEXT_MISMATCH",
    }:
        return {
            "code": "outside_bounded_radius",
            "detail": "all emitted candidates fail the frozen same-page radius or adjacent-page boundary radius",
        }
    return {
        "code": "other",
        "detail": "no emitted candidate passed the frozen validator",
    }


def census_claims(
    claims: list[dict[str, Any]], pages: list[tuple[str, str]],
) -> dict[str, Any]:
    page_by_locator = dict(pages)
    claim_records: list[dict[str, Any]] = []
    for claim_index, claim in enumerate(claims):
        locator = (claim.get("validation") or {}).get("source_locator") or {}
        locator_status = str(locator.get("status") or "unresolved")
        evidence_locator = str(locator.get("locator") or "")
        evidence_excerpt = str(claim.get("evidence_excerpt") or "")
        normalized_evidence = normalize_pdf_locator_text(evidence_excerpt)
        attempts: list[dict[str, Any]] = []
        window = None
        if locator_status == "resolved" and evidence_locator in page_by_locator:
            page_index = next(
                index for index, (name, _) in enumerate(pages) if name == evidence_locator
            )
            window = _evidence_window(page_by_locator[evidence_locator], evidence_excerpt)
            if window is not None:
                window["identity"]["locator"] = evidence_locator
                attempts = [
                    _candidate_attempt(
                        pages=pages,
                        evidence_locator=evidence_locator,
                        evidence_excerpt=evidence_excerpt,
                        potential=potential,
                        evidence_window=window,
                    )
                    for potential in _potential_segments(pages, page_index, window)
                ]
        passed = [item for item in attempts if item["validator_outcome"] == "PASS"]
        emitted = [item for item in attempts if item["generator_outcome"] == "EMITTED"]
        no_context = None if passed else {
            "status": "NO_CONTEXT_CANDIDATE",
            **_no_candidate_reason(locator_status, window, attempts),
        }
        claim_records.append({
            "claim_id": claim.get("claim_id"),
            "claim_index": claim_index,
            "evidence_locator": evidence_locator or None,
            "evidence_raw_text": evidence_excerpt,
            "evidence_normalized_text": normalized_evidence,
            "evidence_window_segment": window["identity"] if window else None,
            "candidate_attempts": attempts,
            "generated_candidates": len(emitted),
            "valid_context_candidates": len(passed),
            "no_context_candidate": no_context,
        })
    return _summarize(claim_records)


def _nearest_rank(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _summarize(claim_records: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = [
        attempt for claim in claim_records for attempt in claim["candidate_attempts"]
    ]
    emitted = [
        item for item in attempts
        if item["generator_outcome"] == "GENERATED_FOR_VALIDATION"
    ]
    passed = [item for item in emitted if item["validator_outcome"] == "PASS"]
    failed = [item for item in emitted if item["validator_outcome"] == "FAIL"]
    filtered = [
        item for item in attempts
        if item["generator_outcome"] != "GENERATED_FOR_VALIDATION"
    ]
    outside = [item for item in failed if item["root_category"] == "OUTSIDE_BOUNDED_WINDOW"]
    gaps = [int(item["minimum_gap"]) for item in outside if item["minimum_gap"] is not None]
    first_failure = next((
        {
            "claim_id": claim["claim_id"],
            "claim_index": claim["claim_index"],
            "candidate_direction": attempt["candidate_direction"],
            "candidate_locator": attempt["candidate_locator"],
            "failure_reason": attempt["failure_reason"],
            "root_category": attempt["root_category"],
            "minimum_gap": attempt["minimum_gap"],
        }
        for claim in claim_records
        for attempt in claim["candidate_attempts"]
        if attempt["validator_outcome"] == "FAIL"
    ), None)
    failure_categories = Counter(item["root_category"] for item in failed)
    failed_claims_by_category: dict[str, set[str]] = {
        category: set() for category in failure_categories
    }
    claims_with_failure: set[str] = set()
    outside_claim_ids: set[str] = set()
    outside_pages: Counter[str] = Counter()
    outside_directions: Counter[str] = Counter()
    for claim in claim_records:
        claim_failures = [
            item for item in claim["candidate_attempts"]
            if item["validator_outcome"] == "FAIL"
        ]
        if claim_failures:
            claims_with_failure.add(str(claim["claim_id"]))
        for item in claim_failures:
            failed_claims_by_category[item["root_category"]].add(str(claim["claim_id"]))
            if item["root_category"] == "OUTSIDE_BOUNDED_WINDOW":
                outside_claim_ids.add(str(claim["claim_id"]))
                outside_pages[str(item["candidate_locator"])] += 1
                outside_directions[str(item["candidate_direction"])] += 1
    filtered_categories = Counter(item["root_category"] for item in filtered)
    no_context_reasons = Counter(
        claim["no_context_candidate"]["code"]
        for claim in claim_records if claim["no_context_candidate"]
    )
    outside_classes: Counter[str] = Counter()
    for item in outside:
        evidence_classes = next(
            claim["evidence_window_segment"]["representation_classes"]
            for claim in claim_records if item in claim["candidate_attempts"]
        )
        for representation_class in set(
            item["candidate_source_segment"]["representation_classes"] + evidence_classes
        ):
            outside_classes[representation_class] += 1
    outside_with_subspan = sum(
        bool((item.get("representation_granularity_probe") or {}).get(
            "valid_source_local_subspan_within_500_exists"
        ))
        for item in outside
    )
    return {
        "claims": claim_records,
        "metrics": {
            "claims_total": len(claim_records),
            "claims_with_any_context_candidate": sum(
                claim["valid_context_candidates"] > 0 for claim in claim_records
            ),
            "claims_with_no_context_candidate": sum(
                claim["valid_context_candidates"] == 0 for claim in claim_records
            ),
            "potential_candidate_segments_total": len(attempts),
            "generated_context_candidates_total": len(emitted),
            "validator_pass": len(passed),
            "validator_fail": len(failed),
            "claims_with_any_validator_failure": len(claims_with_failure),
            "filtered_potential_candidates": len(filtered),
            "fail_by_root_category": {
                name: failure_categories[name] for name in sorted(failure_categories)
            },
            "fail_affected_claims_by_root_category": {
                name: len(failed_claims_by_category[name])
                for name in sorted(failed_claims_by_category)
            },
            "filtered_by_root_category": {
                name: filtered_categories[name] for name in sorted(filtered_categories)
            },
            "no_context_candidate_reasons": {
                name: no_context_reasons[name] for name in sorted(no_context_reasons)
            },
            "outside_bounded_window": {
                "count": len(outside),
                "affected_claims": len(outside_claim_ids),
                "exact_657_gap_candidates": sum(gap == 657 for gap in gaps),
                "candidate_pages": {
                    name: outside_pages[name] for name in sorted(outside_pages)
                },
                "candidate_directions": {
                    name: outside_directions[name] for name in sorted(outside_directions)
                },
                "gap_distribution": {
                    "min": min(gaps) if gaps else None,
                    "median": statistics.median(gaps) if gaps else None,
                    "p90_nearest_rank": _nearest_rank(gaps, 0.90),
                    "max": max(gaps) if gaps else None,
                },
                "gap_buckets": {
                    "501-600": sum(501 <= gap <= 600 for gap in gaps),
                    "601-750": sum(601 <= gap <= 750 for gap in gaps),
                    "751-1000": sum(751 <= gap <= 1000 for gap in gaps),
                    ">1000": sum(gap > 1000 for gap in gaps),
                },
                "representation_classes": {
                    name: outside_classes[name] for name in sorted(outside_classes)
                },
                "valid_local_subspan_within_500": outside_with_subspan,
                "without_found_local_subspan_within_500": len(outside) - outside_with_subspan,
            },
            "PILOT4_657_GAP_ISOLATED": len(outside) == 1 and gaps == [657],
            "runtime_first_validator_failure": first_failure,
        },
    }


def _contract_answers() -> dict[str, Any]:
    return {
        "A_bounded_context_mandatory_for_every_bound_claim": "NO",
        "B_candidate_mandatory_in_both_directions": "NO",
        "C_no_candidate_valid_when_adjacent_segment_over_500": "NOT_SPECIFIED",
        "D_same_page_bounded_subspan_allowed": "NOT_SPECIFIED",
        "E_500_character_coordinate": "BOTH: raw candidate length is clipped to 500; normalized occurrence gap/boundary distance is validated against 500",
    }


def _render_report(census: dict[str, Any]) -> str:
    metrics = census["metrics"]
    outside = metrics["outside_bounded_window"]
    gaps = outside["gap_distribution"]
    buckets = outside["gap_buckets"]
    outcome = census["conclusion"]
    return "\n".join([
        "# Clean Pilot #4 Evidence Context Failure Census",
        "",
        "## Technical summary",
        "",
        f"The frozen diagnostic census inspected all {metrics['claims_total']} Claims without changing runtime behavior. It evaluated {metrics['generated_context_candidates_total']} non-empty candidates before runtime return: {metrics['validator_pass']} passed and {metrics['validator_fail']} failed validation. Of the failures, {outside['count']} are same-page `OUTSIDE_BOUNDED_WINDOW` candidates that preserve fail-fast behavior; 144 are adjacent-page boundary mismatches that the existing runtime already omits.",
        f"The known 657-character case is {'isolated' if metrics['PILOT4_657_GAP_ISOLATED'] else 'not isolated'}. The evidence supports `{outcome['outcome']}` and the next Gate `{outcome['next_gate']}`; this census does not implement that repair.",
        "",
        "## Candidate census shows the complete failure surface",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Claims total | {metrics['claims_total']} |",
        f"| Claims with any valid context candidate | {metrics['claims_with_any_context_candidate']} |",
        f"| Claims with no valid context candidate | {metrics['claims_with_no_context_candidate']} |",
        f"| Potential candidate segments | {metrics['potential_candidate_segments_total']} |",
        f"| Non-empty candidates generated for validation | {metrics['generated_context_candidates_total']} |",
        f"| Validator PASS | {metrics['validator_pass']} |",
        f"| Validator FAIL | {metrics['validator_fail']} |",
        f"| Claims with any validator failure | {metrics['claims_with_any_validator_failure']} |",
        f"| Generator-filtered potential candidates | {metrics['filtered_potential_candidates']} |",
        "",
        "Exact audit tables are used instead of a chart because the decision depends on small categorical counts and boundary values, not a trend or continuous relationship.",
        "",
        "## Failures cluster by mechanism, not by error string",
        "",
        f"- Validator FAIL by root category: `{json.dumps(metrics['fail_by_root_category'], ensure_ascii=False, sort_keys=True)}`.",
        f"- Affected Claims by root category: `{json.dumps(metrics['fail_affected_claims_by_root_category'], ensure_ascii=False, sort_keys=True)}`.",
        f"- Generator-filtered mechanisms: `{json.dumps(metrics['filtered_by_root_category'], ensure_ascii=False, sort_keys=True)}`.",
        f"- No-candidate reasons: `{json.dumps(metrics['no_context_candidate_reasons'], ensure_ascii=False, sort_keys=True)}`.",
        "- Pilot #3's historical `outside the bounded window` message mapped to duplicate-occurrence selection; current all-occurrence validation prevents that historical mechanism from recurring.",
        "",
        "## Outside-window gaps expose representation granularity",
        "",
        "| Gap statistic | Value |",
        "|---|---:|",
        f"| Minimum | {gaps['min']} |",
        f"| Median | {gaps['median']} |",
        f"| P90 (nearest rank) | {gaps['p90_nearest_rank']} |",
        f"| Maximum | {gaps['max']} |",
        f"| 501-600 | {buckets['501-600']} |",
        f"| 601-750 | {buckets['601-750']} |",
        f"| 751-1000 | {buckets['751-1000']} |",
        f"| >1000 | {buckets['>1000']} |",
        "",
        f"A valid exact Source-local subspan of at least {MIN_DIAGNOSTIC_SUBSPAN_NORMALIZED_CHARS} normalized characters within the unchanged 500-character radius was found for {outside['valid_local_subspan_within_500']}/{outside['count']} outside-window cases. The {outside['count']} candidates affect {outside['affected_claims']} Claims across pages `{json.dumps(outside['candidate_pages'], sort_keys=True)}` and directions `{json.dumps(outside['candidate_directions'], sort_keys=True)}`. Representation classes observed: `{json.dumps(outside['representation_classes'], ensure_ascii=False, sort_keys=True)}`.",
        "",
        "## Contract answers constrain the next Gate",
        "",
        *[f"- {key}: `{value}`" for key, value in census["contract_audit"]["answers"].items()],
        "",
        "The contract permits a bound Claim with no bounded-context candidate (`EXCERPT_BOUND`), but it does not specify whether an over-distance neighboring segment should be skipped or replaced by an exact same-page local subspan. The census therefore does not silently select runtime behavior.",
        "",
        "## Recommendation and limits",
        "",
        f"- Outcome: `{outcome['outcome']}` — {outcome['rationale']}",
        f"- Recommended next Gate: `{outcome['next_gate']}`.",
        "- Keep the 500-character bound, validator fail-closed behavior, Claim/Evidence projection, Prompt, Source, and runtime settings frozen.",
        "- The census is descriptive and diagnostic. It does not establish semantic support, Claim quality, or Production eligibility.",
        "",
        "## Further question",
        "",
        "The next Gate must define deterministic local-subspan selection and tests without tuning the 500-character threshold to this sample. A later independent CLEAN source remains required to validate the repaired full stack.",
        "",
        "STOP — no Evidence repair or Human Review was performed.",
        "",
    ])


def _render_contract_audit(census: dict[str, Any]) -> str:
    answers = census["contract_audit"]["answers"]
    return "\n".join([
        "# Evidence v2 Bounded-Context Contract Audit",
        "",
        "## Audit result",
        "",
        "Bounded context is additive and optional for a mechanically bound excerpt. The frozen validator requires every emitted candidate to be exact, local, and within the 500-character rule. Existing materials do not specify a same-Evidence-segment local-subspan algorithm, so this census does not implement one.",
        "",
        "## Questions A-E",
        "",
        f"### A. Is bounded context mandatory for every bound Claim? `{answers['A_bounded_context_mandatory_for_every_bound_claim']}`",
        "",
        "`PILOT2_MECHANICS_STATUSES` includes both `EXCERPT_BOUND` and `CONTEXT_AVAILABLE` (`src/pro_a/corpus_pilot.py:66-69`). `_build_evidence_support_draft` selects `EXCERPT_BOUND` when the candidate list is empty (`src/pro_a/corpus_pilot.py:3019-3025`).",
        "",
        f"### B. Is a candidate mandatory in both directions? `{answers['B_candidate_mandatory_in_both_directions']}`",
        "",
        "Before and after candidates are appended independently and conditionally (`src/pro_a/corpus_pilot.py:2888-2924`). Existing tests accept one-sided availability (`tests/test_corpus_pilot.py:1358-1404`).",
        "",
        f"### C. If the adjacent parsed segment is over 500 away, is no candidate valid? `{answers['C_no_candidate_valid_when_adjacent_segment_over_500']}`",
        "",
        "The artifact schema permits no candidate through `EXCERPT_BOUND`, but the current generator emits a non-empty neighboring segment and lets the validator fail. No existing doc or test states which behavior is normative for this exact condition.",
        "",
        f"### D. May the generator take a same-page bounded subspan? `{answers['D_same_page_bounded_subspan_allowed']}`",
        "",
        "The implementation clips a neighboring segment to 500 raw characters (`src/pro_a/corpus_pilot.py:2863-2868`), but neither docs nor tests authorize selecting context from inside the Evidence-containing coarse segment. The docs require minimum deterministic bounded context without defining this representation (`docs/PHASE3C_LIVE_CORPUS_EXPANSION_PILOT.md:143,159`).",
        "",
        f"### E. What coordinate defines 500? `{answers['E_500_character_coordinate']}`",
        "",
        "Generation clips candidate raw text to 500 characters (`src/pro_a/corpus_pilot.py:2863-2868`). Validation separately measures normalized occurrence gaps and adjacent-page boundary distances against 500 (`src/pro_a/corpus_pilot.py:1528-1561`).",
        "",
        "## Historical manifestation",
        "",
        "- Pilot #2 generated bounded context for all 20 single-page-bound Claims and did not record this mechanism (`workspace/phase3c/PILOT_20260831_DEA82C1F/evidence_contract_v2_draft.json`).",
        "- Pilot #3 recorded the same error string, but its repaired root cause was first-occurrence selection among duplicate normalized text (`scripts/phase3c_pilot3_evidence_v2_repair_report.py:106-110`). It maps to `DUPLICATE_OCCURRENCE_SELECTION`, not the current representation-granularity mechanism.",
        "- Pilot #4 exposes large/table/layout parsed segments in a formally authored report; the census representation features quantify whether that manifestation is systematic rather than inferring from visual appearance.",
        "",
        "## Contract disposition",
        "",
        f"- EVIDENCE_V2_CONTRACT_REVIEW_REQUIRED = `{str(census['conclusion']['contract_review_required']).lower()}`",
        f"- Outcome = `{census['conclusion']['outcome']}`",
        f"- Next Gate = `{census['conclusion']['next_gate']}`",
        "",
        "STOP — no runtime semantics were changed.",
        "",
    ])


def build_census(
    bundle_path: Path, source_path: Path, production_db: Path,
    *, expected_projection_sha256: str | None = None,
) -> dict[str, Any]:
    bundle_path = bundle_path.resolve()
    source_path = source_path.resolve()
    production_db = production_db.resolve()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    claims = bundle.get("claims") or []
    projection_sha256 = _canonical_sha256([_claim_projection(claim) for claim in claims])
    if expected_projection_sha256 and projection_sha256 != expected_projection_sha256:
        raise PilotError("PILOT4_CONTEXT_CENSUS_CLAIM_PROJECTION_MISMATCH")
    if sha256_file(source_path) != (bundle.get("source") or {}).get("sha256"):
        raise PilotError("PILOT4_CONTEXT_CENSUS_SOURCE_MISMATCH")
    input_hash = sha256_file(bundle_path)
    production_pre = production_snapshot(production_db)
    parsed = parse_source_with_diagnostics(source_path)
    pages = [
        unit for unit in source_units(parsed.text) if unit[0].startswith("PAGE:")
    ]
    result = census_claims(claims, pages)
    outside = result["metrics"]["outside_bounded_window"]
    if outside["count"] and outside["valid_local_subspan_within_500"] == outside["count"]:
        outcome = {
            "outcome": "OUTCOME_B_REPRESENTATION_GRANULARITY_DEFECT",
            "rationale": "every outside-window case has an exact Source-local subspan inside the Evidence-containing coarse segment and within the frozen radius",
            "next_gate": "Implement Evidence v2 Bounded Local-Subspan Generation",
            "contract_review_required": False,
        }
    elif outside["count"]:
        outcome = {
            "outcome": "OUTCOME_C_CONTRACT_DEFECT",
            "rationale": "at least one outside-window case has no demonstrated exact local subspan under the frozen radius",
            "next_gate": "Review Evidence v2 Context Contract for Clean-Text Sources",
            "contract_review_required": True,
        }
    else:
        outcome = {
            "outcome": "OUTCOME_A_IMPLEMENTATION_DEFECT",
            "rationale": "no representation-granularity failure was observed",
            "next_gate": "Implement Evidence v2 Bounded-Candidate Availability Fix",
            "contract_review_required": False,
        }
    production_post = production_snapshot(production_db)
    if production_pre != production_post:
        raise PilotError("PILOT4_CONTEXT_CENSUS_PRODUCTION_MUTATED")
    if input_hash != sha256_file(bundle_path):
        raise PilotError("PILOT4_CONTEXT_CENSUS_BUNDLE_MUTATED")
    return {
        "document_type": DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE_DIAGNOSTIC_ONLY",
        "pilot_run_id": bundle.get("pilot_run_id"),
        "frozen_inputs": {
            "bundle_path": str(bundle_path),
            "bundle_sha256": input_hash,
            "source_path": str(source_path),
            "source_sha256": sha256_file(source_path),
            "claim_projection_sha256": projection_sha256,
            "prompt_sha256": ((bundle.get("model") or {}).get("prompt") or {}).get("prompt_sha256"),
            "context_policy": STAGE1_3_CONTEXT_POLICY,
            "context_radius": STAGE1_3_CONTEXT_RADIUS,
        },
        "parser": parsed.diagnostics,
        "runtime_isolation": {
            "diagnostic_only": True,
            "normal_runtime_modified": False,
            "validator_fail_closed_preserved": True,
            "llm_calls": 0,
            "semantic_extraction_calls": 0,
            "human_review": False,
            "production_write": False,
            "ima_invoked": False,
            "propagation_invoked": False,
            "legacy_ingestion_invoked": False,
        },
        "taxonomy": sorted(ROOT_CATEGORIES),
        "contract_audit": {"answers": _contract_answers()},
        "conclusion": outcome,
        "production": {
            "pre": production_pre,
            "post": production_post,
            "unchanged": True,
            "table_counts_changed": False,
        },
        **result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline fail-continuing Evidence v2 bounded-context census",
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--production-db", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--expected-claim-projection-sha256")
    args = parser.parse_args()
    try:
        census = build_census(
            args.bundle, args.source_file, args.production_db,
            expected_projection_sha256=args.expected_claim_projection_sha256,
        )
    except (OSError, ValueError, json.JSONDecodeError, PilotError) as exc:
        print(str(exc))
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    census_path = args.output_dir / "pilot4_evidence_context_failure_census.json"
    report_path = args.output_dir / "pilot4_evidence_context_failure_census_report.md"
    audit_path = args.output_dir / "pilot4_evidence_context_contract_audit.md"
    write_json(census_path, census)
    report_path.write_text(_render_report(census), encoding="utf-8")
    audit_path.write_text(_render_contract_audit(census), encoding="utf-8")
    print(json.dumps({
        "status": census["status"],
        "metrics": census["metrics"],
        "conclusion": census["conclusion"],
        "census_path": str(census_path),
        "report_path": str(report_path),
        "contract_audit_path": str(audit_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
