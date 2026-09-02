from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from pro_a.corpus_pilot import production_snapshot
from pro_a.parsers import parse_source_with_diagnostics, semantic_eligible_source_text
from pro_a.storage import sha256_file, write_json


PILOT_RUN_ID = "PILOT_20260901_4C6535B7"
SOURCE_SHA256 = "4c6535b75fa97968f8f1651987ff52c64c0ffded41d3dba39ca72a5bbac3a178"
CLAIM_PROJECTION_SHA256 = (
    "b105a9bcaa433eac6dcaaa96fd85fd774e5a0757ac0da1671f1a7d3e18e4b100"
)
ACCEPTED_LAYOUT_SIGNATURE = (
    "ae858149d987bba4a64b3c9b2ba3bc59325437507125dd2aef6d786562279922"
)


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
            "sha256": sha256_file(path),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]
    return {"files": len(rows), "digest": canonical_sha256(rows)}


def bbox_iou(left: list[float], right: list[float]) -> float:
    x0 = max(left[0], right[0])
    y0 = max(left[1], right[1])
    x1 = min(left[2], right[2])
    y1 = min(left[3], right[3])
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return 0.0 if union <= 0 else intersection / union


def center_inside(inner: list[float], outer: tuple[float, float, float, float]) -> bool:
    x = (inner[0] + inner[2]) / 2
    y = (inner[1] + inner[3]) / 2
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--counterfactual", type=Path, required=True)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--frozen-pilot-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    bundle_path = args.bundle.resolve()
    evaluation_path = args.evaluation.resolve()
    counterfactual_path = args.counterfactual.resolve()
    production_db = args.production_db.resolve()
    frozen_pilot_dir = args.frozen_pilot_dir.resolve()
    output = args.output.resolve()

    if sha256_file(source) != SOURCE_SHA256:
        raise RuntimeError("Pilot #4 Source SHA mismatch")
    bundle = load_json(bundle_path)
    evaluation = load_json(evaluation_path)
    counterfactual = load_json(counterfactual_path)
    claims = bundle.get("claims") or []
    projection_sha = canonical_sha256([
        {
            "claim_id": claim.get("claim_id"),
            "statement": claim.get("statement"),
            "evidence_excerpt": claim.get("evidence_excerpt"),
            "attributed_to": claim.get("attributed_to") or "",
        }
        for claim in claims
    ])
    if (
        bundle.get("pilot_run_id") != PILOT_RUN_ID
        or len(claims) != 320
        or projection_sha != CLAIM_PROJECTION_SHA256
    ):
        raise RuntimeError("Pilot #4 Claim freeze mismatch")
    if counterfactual.get("pilot_run_id") != PILOT_RUN_ID:
        raise RuntimeError("Pilot #4 counterfactual identity mismatch")

    frozen_pre = tree_snapshot(frozen_pilot_dir)
    production_pre = production_snapshot(production_db)
    canonical_only = parse_source_with_diagnostics(source)
    first = parse_source_with_diagnostics(source, include_semantic_segments=True)
    second = parse_source_with_diagnostics(source, include_semantic_segments=True)
    if canonical_only.text != first.text or first.text != second.text:
        raise RuntimeError("canonical Source text changed under layout parsing")
    first_signature = first.diagnostics["pdf_layout"]["signature_sha256"]
    second_signature = second.diagnostics["pdf_layout"]["signature_sha256"]
    if first_signature != ACCEPTED_LAYOUT_SIGNATURE or second_signature != first_signature:
        raise RuntimeError("accepted Pilot #4 layout signature mismatch")

    runtime_tables = [
        segment for segment in first.segments or ()
        if segment.native_kind == "table" and segment.kind == "table"
    ]
    raw_table_candidates = [
        segment for segment in first.segments or () if segment.native_kind == "table"
    ]
    protected_unknown = [
        segment for segment in raw_table_candidates
        if segment.reason == "PROTECTED_LAYOUT_OVERLAP"
    ]
    binding_unknown = [
        segment for segment in raw_table_candidates
        if segment.reason.startswith("CANONICAL_BINDING_")
    ]
    page24 = [
        segment for segment in raw_table_candidates if segment.page == 24
    ]
    if len(page24) != 1 or page24[0].kind != "unknown":
        raise RuntimeError("page-24 mixed table did not remain unknown")

    runtime_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
    for segment in runtime_tables:
        runtime_by_page.setdefault(segment.page, []).append(segment.bbox)
    expected_blocks = []
    for block in evaluation["retrospective_manifest_comparison"]["blocks"]:
        candidates = runtime_by_page.get(int(block["page"]), [])
        best_iou = max(
            (bbox_iou(block["expected_bbox"], list(bbox)) for bbox in candidates),
            default=0.0,
        )
        expected_blocks.append({
            "block_id": block["block_id"],
            "page": block["page"],
            "best_runtime_iou": round(best_iou, 6),
            "runtime_table_detected": best_iou >= 0.50,
        })
    if sum(row["runtime_table_detected"] for row in expected_blocks) != 5:
        raise RuntimeError("expected Pilot #4 runtime table-block replay mismatch")

    claim_rows = evaluation["pilot4_claim_geometry"]["claim_rows"]
    inside_by_origin: Counter[str] = Counter()
    totals_by_origin: Counter[str] = Counter()
    for row in claim_rows:
        origin = str(row["origin_class"])
        totals_by_origin[origin] += 1
        page = row.get("page")
        occurrence_bboxes = row.get("occurrence_bboxes") or []
        inside = bool(page) and any(
            center_inside(occurrence, table_bbox)
            for occurrence in occurrence_bboxes
            for table_bbox in runtime_by_page.get(int(page), [])
        )
        inside_by_origin[origin] += int(inside)

    suppressible = inside_by_origin["table_derived"]
    retained_table = totals_by_origin["table_derived"] - suppressible
    narrative_suppressed = inside_by_origin["narrative_derived"]
    review_set = len(claims) - suppressible
    review_reduction = suppressible / len(claims) * 100
    if (
        suppressible != 188
        or retained_table != 10
        or narrative_suppressed != 0
        or review_set != 132
        or round(review_reduction, 2) != 58.75
        or totals_by_origin["mixed_or_uncertain"] != 3
        or totals_by_origin["unresolved_origin"] != 19
    ):
        raise RuntimeError("Pilot #4 runtime Claim counterfactual mismatch")

    semantic_text = semantic_eligible_source_text(first)
    production_post = production_snapshot(production_db)
    frozen_post = tree_snapshot(frozen_pilot_dir)
    result = {
        "document_type": "phase3c_table_suppression_runtime_replay",
        "schema_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "DETERMINISTIC_NO_LLM_FROZEN_PILOT4_COUNTERFACTUAL",
        "frozen_inputs": {
            "pilot_run_id": PILOT_RUN_ID,
            "source": str(source),
            "source_sha256": sha256_file(source),
            "bundle": str(bundle_path),
            "bundle_sha256": sha256_file(bundle_path),
            "claim_projection_sha256": projection_sha,
            "evaluation": str(evaluation_path),
            "evaluation_sha256": sha256_file(evaluation_path),
            "counterfactual": str(counterfactual_path),
            "counterfactual_sha256": sha256_file(counterfactual_path),
            "claims": len(claims),
        },
        "runtime_layout": {
            "adapter": first.diagnostics["pdf_layout"]["adapter"],
            "adapter_versions": first.diagnostics["pdf_layout"]["adapter_versions"],
            "first_signature_sha256": first_signature,
            "second_signature_sha256": second_signature,
            "stable": first_signature == second_signature,
            "accepted_signature_reproduced": first_signature == ACCEPTED_LAYOUT_SIGNATURE,
            "segments": len(first.segments or ()),
            "segment_kind_counts": dict(Counter(
                segment.kind for segment in first.segments or ()
            )),
            "raw_table_candidates": len(raw_table_candidates),
            "overlap_guard_effective_table_candidates": (
                len(raw_table_candidates) - len(protected_unknown)
            ),
            "canonical_source_bound_table_candidates": len(runtime_tables),
            "canonical_binding_fail_open_unknown": len(binding_unknown),
            "protected_overlap_unknown": len(protected_unknown),
            "page24_mixed_table_kind": page24[0].kind,
            "page24_content_eligible": page24[0].kind == "unknown",
        },
        "semantic_eligibility": {
            "policy": "NARRATIVE_FIRST_TABLE_SUPPRESSION",
            "canonical_source_sha256": hashlib.sha256(
                first.text.encode("utf-8")
            ).hexdigest(),
            "canonical_source_chars": len(first.text),
            "semantic_eligible_chars": len(semantic_text),
            "excluded_chars": len(first.text) - len(semantic_text),
            "canonical_source_text_changed": False,
            "filter_before_chunking": True,
            "evidence_uses_complete_source": True,
        },
        "expected_block_replay": {
            "expected": 6,
            "runtime_effective_detected": 5,
            "blocks": expected_blocks,
        },
        "claim_counterfactual": {
            "origin_totals": dict(totals_by_origin),
            "inside_runtime_table_by_origin": dict(inside_by_origin),
            "pilot4_runtime_suppressible_table_claims": suppressible,
            "pilot4_runtime_retained_table_claims": retained_table,
            "pilot4_runtime_narrative_claims_suppressed": narrative_suppressed,
            "pilot4_runtime_counterfactual_review_set": review_set,
            "pilot4_runtime_counterfactual_review_reduction_percent": round(
                review_reduction, 2
            ),
            "mixed_uncertain_force_classified": False,
            "unresolved_force_classified": False,
        },
        "calls": {"llm": 0, "semantic_extraction": 0},
        "isolation": {
            "frozen_pilot_pre": frozen_pre,
            "frozen_pilot_post": frozen_post,
            "frozen_pilot_changed": frozen_pre != frozen_post,
            "production_pre": production_pre,
            "production_post": production_post,
            "production_changed": production_pre != production_post,
            "ima": "NO",
            "propagation": "NO",
            "legacy_ingestion": "NO",
        },
        "final_state": {
            "phase3c_table_suppression_implementation_complete": True,
            "pymupdf_runtime_dependency_gate": "PASS",
            "pdf_segment_structure_implemented": True,
            "semantic_eligibility_filter_implemented": True,
            "canonical_source_text_changed": "NO",
            "evidence_contract_changed": "NO",
            "production_schema_changed": "NO",
            "phase3c_complete": False,
            "production_apply_ready": "NO",
            "phase3c_next_gate": "Post-Repair Independent Clean Pilot",
        },
    }
    if result["isolation"]["frozen_pilot_changed"] or result["isolation"]["production_changed"]:
        raise RuntimeError("frozen Pilot #4 or Production changed during replay")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps(result["final_state"], ensure_ascii=False, indent=2))
    print(json.dumps(result["claim_counterfactual"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
