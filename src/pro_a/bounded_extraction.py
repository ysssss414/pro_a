"""Dormant bounded output series. No provider, persistence, or runtime binding."""
from __future__ import annotations

import copy
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from .evidence_binding import EVIDENCE_SELECTION_FIELDS, identity, resolve_evidence_binding_v2, validate_catalog
from .source_analysis_wire import (
    SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION, SourceEvidenceCatalog, SourcePieceContext,
    expand_source_analysis_wire_v2, validate_source_analysis_wire_v2,
)
from .analyzer import normalize_ws
from .output_capacity import (SEGMENT_OUTPUT_CEILING, LEGACY_SEGMENT_OUTPUT_CEILING,
    SERIES_OUTPUT_LIABILITY_CEILING, OPERATION_OUTPUT_BUDGET_POLICY_VERSION)

BOUNDED_EXTRACTION_SERIES_VERSION = "bounded-extraction-series-v1"
BOUNDED_EXTRACTION_SEGMENT_VERSION = "bounded-extraction-segment-v1"
BOUNDED_EXTRACTION_COVERAGE_VERSION = "bounded-extraction-coverage-v1"
BOUNDED_EXTRACTION_SUBDIVISION_VERSION = "bounded-extraction-subdivision-v1"
BOUNDED_EXTRACTION_POLICY_VERSION = "bounded-extraction-policy-v1"
SOURCE_ANALYSIS_WIRE_V3_VERSION = "source-analysis-wire-v3"
SOURCE_ANALYSIS_WIRE_V3_EXPANDER_VERSION = "source-analysis-wire-expander-v2"
LEGACY_OUTPUT_SERIES_VERSION = "whole-piece-output-series-v1"
LEGACY_OUTPUT_BATCH_VERSION = "whole-piece-output-batch-v1"
OUTPUT_SERIES_VERSION = "whole-piece-output-series-v2"
OUTPUT_BATCH_VERSION = "whole-piece-output-batch-v2"
OUTPUT_SERIES_VERSIONS = (LEGACY_OUTPUT_SERIES_VERSION, OUTPUT_SERIES_VERSION)
OUTPUT_COVERAGE_VERSION = "whole-piece-output-coverage-v1"
OUTPUT_SUBDIVISION_VERSION = "whole-piece-output-subdivision-v1"
OUTPUT_POLICY_VERSION = "whole-piece-output-ownership-policy-v1"


class BoundedExtractionError(ValueError):
    """Safe failure code, never Source content."""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class SeriesBudget:
    # 16-ref roots have <=4 midpoint levels; 16 leaves need <=31 tree nodes.
    initial_evidence_refs: int = 16
    max_leaf_segments: int = 16
    max_subdivision_depth: int = 4
    max_provider_calls: int = 32
    max_cumulative_output_tokens: int = SERIES_OUTPUT_LIABILITY_CEILING

    def __post_init__(self) -> None:
        if (any(type(v) is not int or v < 1 for v in asdict(self).values())
                or self.initial_evidence_refs > 16 or self.max_leaf_segments > 16
                or self.max_subdivision_depth > 4 or self.max_provider_calls > 32
                or self.max_cumulative_output_tokens > SERIES_OUTPUT_LIABILITY_CEILING):
            raise BoundedExtractionError("INVALID_SERIES_BUDGET")


@dataclass(frozen=True)
class ExtractionSeries:
    series_version: str
    series_id: str
    processing_run_id: str
    source_sha256: str
    source_piece_id: str
    source_piece_sha256: str
    source_prompt_sha256: str
    evidence_universe_sha256: str
    eligible_evidence_refs: tuple[str, ...]
    wire_contract_identity: str
    task_policy_identity: str
    output_budget_identity: str
    budget: SeriesBudget
    series_sha256: str

    @property
    def logical_job_count(self) -> int:
        return 1


def create_extraction_series(context: SourcePieceContext, catalog: SourceEvidenceCatalog,
                             processing_run_id: str, budget: SeriesBudget = SeriesBudget(), *,
                             series_version: str = BOUNDED_EXTRACTION_SERIES_VERSION) -> ExtractionSeries:
    validate_catalog(catalog, context)
    if not isinstance(processing_run_id, str) or not processing_run_id.strip() or not isinstance(budget, SeriesBudget):
        raise BoundedExtractionError("INVALID_SERIES_INPUT")
    universe = identity({"catalog": asdict(catalog), "known_node_ids": context.known_node_ids})
    if series_version not in (BOUNDED_EXTRACTION_SERIES_VERSION, *OUTPUT_SERIES_VERSIONS):
        raise BoundedExtractionError("INVALID_SERIES_VERSION")
    values = {"series_version": series_version, "processing_run_id": processing_run_id,
              "source_sha256": context.source_sha256, "source_piece_id": context.piece.piece_id,
              "source_piece_sha256": context.piece.source_sha256, "source_prompt_sha256": context.piece.prompt_sha256,
              "evidence_universe_sha256": universe, "eligible_evidence_refs": tuple(u.evidence_ref for u in catalog.units),
              "wire_contract_identity": SOURCE_ANALYSIS_WIRE_V3_VERSION,
              "task_policy_identity": OUTPUT_POLICY_VERSION if series_version in OUTPUT_SERIES_VERSIONS else BOUNDED_EXTRACTION_POLICY_VERSION,
              "output_budget_identity": OPERATION_OUTPUT_BUDGET_POLICY_VERSION if series_version == OUTPUT_SERIES_VERSION else "operation-output-budget-v1",
              "budget": asdict(budget)}
    series_id = "SERIES_" + identity(values)[:32].upper()
    sha = identity({**values, "series_id": series_id})
    return ExtractionSeries(**{**values, "budget": budget}, series_id=series_id, series_sha256=sha)


def _series(series: ExtractionSeries) -> None:
    if not isinstance(series, ExtractionSeries):
        raise BoundedExtractionError("INVALID_SERIES")
    values = asdict(series)
    sha = values.pop("series_sha256")
    sid = values.pop("series_id")
    if (series.series_version not in (BOUNDED_EXTRACTION_SERIES_VERSION, *OUTPUT_SERIES_VERSIONS)
            or series.wire_contract_identity != SOURCE_ANALYSIS_WIRE_V3_VERSION
            or series.task_policy_identity != (OUTPUT_POLICY_VERSION if series.series_version in OUTPUT_SERIES_VERSIONS else BOUNDED_EXTRACTION_POLICY_VERSION)
            or series.output_budget_identity != (OPERATION_OUTPUT_BUDGET_POLICY_VERSION if series.series_version == OUTPUT_SERIES_VERSION else "operation-output-budget-v1")
            or len(set(series.eligible_evidence_refs)) != len(series.eligible_evidence_refs)
            or sid != "SERIES_" + identity(values)[:32].upper()
            or sha != identity({**values, "series_id": sid})):
        raise BoundedExtractionError("SERIES_IDENTITY_MISMATCH")
    SeriesBudget(**asdict(series.budget))


@dataclass(frozen=True)
class ExtractionSegment:
    segment_version: str
    segment_id: str
    series_id: str
    parent_segment_id: str | None
    subdivision_depth: int
    stable_path: tuple[int, ...]
    range_start: int
    range_end: int
    assigned_evidence_refs: tuple[str, ...]
    assigned_evidence_sha256: str
    wire_schema_identity: str
    max_output_tokens: int
    segment_sha256: str


def _segment(series: ExtractionSeries, lo: int, hi: int, path: tuple[int, ...],
             parent: ExtractionSegment | None = None) -> ExtractionSegment:
    refs = series.eligible_evidence_refs[lo:hi]
    values = {"segment_version": (OUTPUT_BATCH_VERSION if series.series_version == OUTPUT_SERIES_VERSION else
              LEGACY_OUTPUT_BATCH_VERSION if series.series_version == LEGACY_OUTPUT_SERIES_VERSION else BOUNDED_EXTRACTION_SEGMENT_VERSION), "series_id": series.series_id,
              "parent_segment_id": parent.segment_id if parent else None,
              "subdivision_depth": parent.subdivision_depth + 1 if parent else 0,
              "stable_path": path, "range_start": lo, "range_end": hi, "assigned_evidence_refs": refs,
              "assigned_evidence_sha256": identity(refs), "wire_schema_identity": series.wire_contract_identity,
              "max_output_tokens": SEGMENT_OUTPUT_CEILING if series.series_version == OUTPUT_SERIES_VERSION else LEGACY_SEGMENT_OUTPUT_CEILING}
    seed = {**values, "series_sha256": series.series_sha256,
            "parent_segment_sha256": parent.segment_sha256 if parent else None,
            "subdivision_policy": OUTPUT_SUBDIVISION_VERSION if series.series_version in OUTPUT_SERIES_VERSIONS else BOUNDED_EXTRACTION_SUBDIVISION_VERSION}
    sid = "SEGMENT_" + identity(seed)[:32].upper()
    return ExtractionSegment(**values, segment_id=sid, segment_sha256=identity({**seed, "segment_id": sid}))


def _segment_contract(series: ExtractionSeries, segment: ExtractionSegment) -> None:
    if (not isinstance(segment, ExtractionSegment) or not isinstance(segment.stable_path, tuple)
            or not segment.stable_path or any(type(i) is not int for i in segment.stable_path)
            or any(type(getattr(segment, field)) is not int for field in
                   ("subdivision_depth", "range_start", "range_end", "max_output_tokens"))):
        raise BoundedExtractionError("INVALID_SEGMENT_IDENTITY")
    root = segment.stable_path[0]
    lo = root * series.budget.initial_evidence_refs
    hi = min(lo + series.budget.initial_evidence_refs, len(series.eligible_evidence_refs))
    if root < 0 or lo >= hi or len(segment.stable_path) - 1 > series.budget.max_subdivision_depth:
        raise BoundedExtractionError("INVALID_SEGMENT_IDENTITY")
    expected = _segment(series, lo, hi, (root,))
    for branch in segment.stable_path[1:]:
        if branch not in (0, 1) or hi - lo < 2:
            raise BoundedExtractionError("INVALID_SEGMENT_IDENTITY")
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if branch == 0 else (mid, hi)
        expected = _segment(series, lo, hi, expected.stable_path + (branch,), expected)
    if segment != expected:
        raise BoundedExtractionError("SEGMENT_IDENTITY_MISMATCH")


@dataclass(frozen=True)
class ExtractionPlan:
    series_id: str
    segments: tuple[ExtractionSegment, ...]
    superseded_segment_ids: tuple[str, ...] = ()

    @property
    def leaves(self) -> tuple[ExtractionSegment, ...]:
        return tuple(sorted((s for s in self.segments if s.segment_id not in self.superseded_segment_ids),
                            key=lambda s: s.range_start))

    def status(self, segment_id: str) -> str:
        if not any(s.segment_id == segment_id for s in self.segments):
            raise BoundedExtractionError("UNKNOWN_SEGMENT")
        return "SUPERSEDED_BY_CHILDREN" if segment_id in self.superseded_segment_ids else "LEAF"


def initial_extraction_plan(series: ExtractionSeries) -> ExtractionPlan:
    _series(series)
    size, count = series.budget.initial_evidence_refs, len(series.eligible_evidence_refs)
    roots = tuple(_segment(series, lo, min(lo + size, count), (index,))
                  for index, lo in enumerate(range(0, count, size)))
    if len(roots) > series.budget.max_leaf_segments:
        raise BoundedExtractionError("EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY")
    return ExtractionPlan(series.series_id, roots)


def _plan(series: ExtractionSeries, plan: ExtractionPlan) -> None:
    _series(series)
    if not isinstance(plan, ExtractionPlan) or plan.series_id != series.series_id:
        raise BoundedExtractionError("PLAN_SERIES_MISMATCH")
    by_id = {s.segment_id: s for s in plan.segments}
    if len(by_id) != len(plan.segments) or len(set(plan.superseded_segment_ids)) != len(plan.superseded_segment_ids):
        raise BoundedExtractionError("DUPLICATE_SEGMENT_IDENTITY")
    roots = tuple(s for s in plan.segments if s.parent_segment_id is None)
    root_count = (len(series.eligible_evidence_refs) + series.budget.initial_evidence_refs - 1) // series.budget.initial_evidence_refs
    if len(roots) != root_count or tuple(s.stable_path for s in roots) != tuple((i,) for i in range(root_count)):
        raise BoundedExtractionError("INVALID_INITIAL_ASSIGNMENT")
    expected_superseded = set()
    for parent in plan.segments:
        children = tuple(s for s in plan.segments if s.parent_segment_id == parent.segment_id)
        if children:
            if parent.range_end - parent.range_start < 2:
                raise BoundedExtractionError("INVALID_SUBDIVISION")
            mid = (parent.range_start + parent.range_end) // 2
            expected = (_segment(series, parent.range_start, mid, parent.stable_path + (0,), parent),
                        _segment(series, mid, parent.range_end, parent.stable_path + (1,), parent))
            if children != expected:
                raise BoundedExtractionError("INVALID_SUBDIVISION")
            expected_superseded.add(parent.segment_id)
    if set(plan.superseded_segment_ids) != expected_superseded:
        raise BoundedExtractionError("INVALID_PARENT_STATUS")
    for segment in plan.segments:
        _segment_contract(series, segment)
        if (segment.parent_segment_id is not None and segment.parent_segment_id not in by_id
                or any(type(getattr(segment, field)) is not int for field in
                       ("subdivision_depth", "range_start", "range_end", "max_output_tokens"))
                or not isinstance(segment.stable_path, tuple) or any(type(i) is not int for i in segment.stable_path)
                or segment.subdivision_depth > series.budget.max_subdivision_depth):
            raise BoundedExtractionError("INVALID_SEGMENT_LINEAGE")
    cursor = 0
    for leaf in plan.leaves:
        if leaf.range_start != cursor or leaf.range_end <= cursor:
            raise BoundedExtractionError("INVALID_TERMINAL_ASSIGNMENT")
        cursor = leaf.range_end
    if cursor != len(series.eligible_evidence_refs) or len(plan.leaves) > series.budget.max_leaf_segments:
        raise BoundedExtractionError("INVALID_TERMINAL_ASSIGNMENT")


def subdivide_extraction_plan(series: ExtractionSeries, plan: ExtractionPlan, segment_id: str) -> ExtractionPlan:
    _plan(series, plan)
    parent = next((s for s in plan.leaves if s.segment_id == segment_id), None)
    if parent is None:
        raise BoundedExtractionError("SEGMENT_NOT_ACTIVE_LEAF")
    if (parent.range_end - parent.range_start < 2
            or parent.subdivision_depth >= series.budget.max_subdivision_depth
            or len(plan.leaves) >= series.budget.max_leaf_segments):
        raise BoundedExtractionError("EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY")
    mid = (parent.range_start + parent.range_end) // 2
    children = (_segment(series, parent.range_start, mid, parent.stable_path + (0,), parent),
                _segment(series, mid, parent.range_end, parent.stable_path + (1,), parent))
    return ExtractionPlan(series.series_id, plan.segments + children, plan.superseded_segment_ids + (parent.segment_id,))


def _wire_v2_projection(wire: dict, catalog: SourceEvidenceCatalog, context: SourcePieceContext) -> tuple[dict, list[tuple[dict, Any]]]:
    if not isinstance(wire, dict) or wire.get("wire_version") != SOURCE_ANALYSIS_WIRE_V3_VERSION:
        raise BoundedExtractionError("INVALID_WIRE_VERSION")
    projected = copy.deepcopy(wire)
    projected["wire_version"] = SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION
    bindings = []
    for family in ("claims", "node_matches", "node_candidates"):
        objects = projected.get(family, [])
        if not isinstance(objects, list):
            raise BoundedExtractionError("INVALID_WIRE_ARRAY")
        for obj in objects:
            if not isinstance(obj, dict):
                raise BoundedExtractionError("INVALID_WIRE_OBJECT")
            targets = [obj]
            if family == "node_candidates" and isinstance(obj.get("preserved_fields"), dict):
                targets.append(obj["preserved_fields"])
            for target in targets:
                if family == "claims" and "evidence_pointer" not in target:
                    raise BoundedExtractionError("CANONICAL_EVIDENCE_POINTER_REQUIRED")
                if "evidence_ref" in target:
                    selection = {key: target[key] for key in EVIDENCE_SELECTION_FIELDS if key in target}
                    if family != "claims" and "evidence_pointer" in target:
                        raise BoundedExtractionError("UNSUPPORTED_EVIDENCE_POINTER_FIELD")
                    binding = resolve_evidence_binding_v2(selection, catalog, context)
                    for key in EVIDENCE_SELECTION_FIELDS - {"evidence_ref"}:
                        target.pop(key, None)
                    bindings.append((target, binding))
                elif target.keys() & (EVIDENCE_SELECTION_FIELDS - {"evidence_ref"}):
                    raise BoundedExtractionError("EVIDENCE_REF_REQUIRED")
    validate_source_analysis_wire_v2(projected, catalog, context)
    return projected, bindings


def expand_source_analysis_wire_v3(wire: dict, catalog: SourceEvidenceCatalog, context: SourcePieceContext) -> dict:
    projected, bindings = _wire_v2_projection(wire, catalog, context)
    canonical = expand_source_analysis_wire_v2(projected, catalog, context)
    # Projection keeps object order. Match targets by their in-memory identity.
    by_object = {id(obj): binding for obj, binding in bindings}
    for family in ("claims", "node_matches", "node_candidates"):
        for old, new in zip(projected.get(family, []), canonical[family]):
            binding = by_object.get(id(old))
            if binding is None and isinstance(old.get("preserved_fields"), dict):
                binding = by_object.get(id(old["preserved_fields"]))
            if binding is not None:
                new["evidence_excerpt"] = binding.evidence_excerpt
                if family == "claims":
                    new["evidence_pointer"] = binding.evidence_pointer
    return canonical


@dataclass(frozen=True)
class EvidenceDisposition:
    evidence_ref: str
    disposition: str


@dataclass(frozen=True)
class SegmentWireResult:
    segment_id: str
    segment_sha256: str
    wire_json: str
    dispositions: tuple[EvidenceDisposition, ...]
    result_sha256: str


def create_segment_wire_result(series: ExtractionSeries, segment: ExtractionSegment, wire: dict,
                               dispositions: tuple[EvidenceDisposition, ...],
                               catalog: SourceEvidenceCatalog, context: SourcePieceContext) -> SegmentWireResult:
    if series != create_extraction_series(context, catalog, series.processing_run_id, series.budget, series_version=series.series_version):
        raise BoundedExtractionError("SERIES_INPUT_BINDING_MISMATCH")
    if segment.series_id != series.series_id:
        raise BoundedExtractionError("SEGMENT_SERIES_MISMATCH")
    _segment_contract(series, segment)
    projected, bindings = _wire_v2_projection(wire, catalog, context)
    assigned = set(segment.assigned_evidence_refs)
    if any(binding.evidence_ref not in assigned for _, binding in bindings):
        raise BoundedExtractionError("CLAIM_OUTSIDE_SEGMENT")
    claimed = {obj["evidence_ref"] for obj in projected["claims"]}
    if (not isinstance(dispositions, tuple) or any(not isinstance(d, EvidenceDisposition) for d in dispositions)
            or Counter(d.evidence_ref for d in dispositions) != Counter(segment.assigned_evidence_refs)):
        raise BoundedExtractionError("MISSING_OR_DUPLICATE_DISPOSITION")
    for item in dispositions:
        if series.series_version in OUTPUT_SERIES_VERSIONS and item.disposition not in ("CLAIMED", "NO_INDEPENDENT_CLAIM"):
            raise BoundedExtractionError("INVALID_OUTPUT_DISPOSITION")
        if (item.disposition not in ("CLAIMED", "NO_INDEPENDENT_CLAIM", "CONTEXT_ONLY", "SUBDIVISION_REQUIRED")
                or (item.disposition == "CLAIMED") != (item.evidence_ref in claimed)):
            raise BoundedExtractionError("CLAIM_DISPOSITION_MISMATCH")
    # Canonicalize disposition order from the system assignment, never the model.
    by_ref = {d.evidence_ref: d for d in dispositions}
    ordered = tuple(by_ref[ref] for ref in segment.assigned_evidence_refs)
    values = {"segment_id": segment.segment_id, "segment_sha256": segment.segment_sha256,
              "wire_json": _json(wire), "dispositions": [asdict(d) for d in ordered]}
    return SegmentWireResult(**{**values, "dispositions": ordered}, result_sha256=identity(values))


@dataclass(frozen=True)
class SeriesCoverage:
    coverage_version: str
    eligible_evidence_refs: tuple[str, ...]
    terminal_assigned_refs: tuple[str, ...]
    closed_refs: tuple[str, ...]
    missing_refs: tuple[str, ...]
    duplicate_terminal_assignment_refs: tuple[str, ...]
    coverage_sha256: str

    @property
    def complete(self) -> bool:
        return not self.missing_refs and not self.duplicate_terminal_assignment_refs


def series_coverage(series: ExtractionSeries, plan: ExtractionPlan, results: tuple[SegmentWireResult, ...],
                    catalog: SourceEvidenceCatalog, context: SourcePieceContext) -> SeriesCoverage:
    _plan(series, plan)
    if series != create_extraction_series(context, catalog, series.processing_run_id, series.budget, series_version=series.series_version):
        raise BoundedExtractionError("SERIES_INPUT_BINDING_MISMATCH")
    leaves = {s.segment_id: s for s in plan.leaves}
    accepted, closed = set(), set()
    for result in results:
        if result.segment_id not in leaves:
            raise BoundedExtractionError("SUPERSEDED_OR_FOREIGN_SEGMENT_RESULT")
        if result.segment_id in accepted:
            raise BoundedExtractionError("DUPLICATE_SEGMENT_RESULT")
        accepted.add(result.segment_id)
        expected = create_segment_wire_result(series, leaves[result.segment_id], json.loads(result.wire_json),
                                              result.dispositions, catalog, context)
        if result != expected:
            raise BoundedExtractionError("SEGMENT_RESULT_IDENTITY_MISMATCH")
        if all(d.disposition != "SUBDIVISION_REQUIRED" for d in result.dispositions):
            closed.update(d.evidence_ref for d in result.dispositions)
    assigned = tuple(ref for leaf in plan.leaves for ref in leaf.assigned_evidence_refs)
    counts = Counter(assigned)
    eligible = series.eligible_evidence_refs
    values = {"coverage_version": OUTPUT_COVERAGE_VERSION if series.series_version in OUTPUT_SERIES_VERSIONS else BOUNDED_EXTRACTION_COVERAGE_VERSION, "eligible_evidence_refs": eligible,
              "terminal_assigned_refs": assigned, "closed_refs": tuple(ref for ref in eligible if ref in closed),
              "missing_refs": tuple(ref for ref in eligible if ref not in closed),
              "duplicate_terminal_assignment_refs": tuple(ref for ref in eligible if counts[ref] > 1)}
    return SeriesCoverage(**values, coverage_sha256=identity({"series_sha256": series.series_sha256, **values}))


@dataclass(frozen=True)
class AggregateWireResult:
    series_id: str
    wire_json: str
    coverage: SeriesCoverage
    ordered_segment_result_sha256: tuple[str, ...]
    aggregate_wire_sha256: str


def aggregate_segment_wires(series: ExtractionSeries, plan: ExtractionPlan, results: tuple[SegmentWireResult, ...],
                             catalog: SourceEvidenceCatalog, context: SourcePieceContext) -> AggregateWireResult:
    coverage = series_coverage(series, plan, results, catalog, context)
    if not coverage.complete:
        raise BoundedExtractionError("SERIES_COVERAGE_INCOMPLETE")
    by_id = {r.segment_id: r for r in results}
    wire = {"wire_version": SOURCE_ANALYSIS_WIRE_V3_VERSION, "source_metadata": {}, "claims": [],
            "node_matches": [], "node_candidates": [], "relation_candidates": [], "source_references": []}
    candidate_keys = {}
    def candidate_semantics(candidate: dict) -> dict | str:
        if series.series_version in OUTPUT_SERIES_VERSIONS:
            return _json(candidate)
        value = copy.deepcopy(candidate)
        for obj in (value, value.get("preserved_fields", {})):
            for field in EVIDENCE_SELECTION_FIELDS:
                obj.pop(field, None)
        return value
    ordered_sha = []
    for leaf in plan.leaves:
        result = by_id[leaf.segment_id]
        part = json.loads(result.wire_json)
        ordered_sha.append(result.result_sha256)
        if not wire["source_metadata"]:
            wire["source_metadata"] = part["source_metadata"]
        elif series.series_version in OUTPUT_SERIES_VERSIONS and _json(wire["source_metadata"]) != _json(part["source_metadata"]):
            raise BoundedExtractionError("SOURCE_METADATA_CONFLICT")
        offset = len(wire["claims"])
        wire["claims"].extend(part["claims"])
        wire["node_matches"].extend(part.get("node_matches", []))
        wire["source_references"].extend(part.get("source_references", []))
        for candidate in part.get("node_candidates", []):
            key = normalize_ws(candidate["canonical_name"]).lower()
            if key in candidate_keys and candidate_semantics(candidate_keys[key]) != candidate_semantics(candidate):
                raise BoundedExtractionError("NODE_CANDIDATE_CONFLICT")
            if key not in candidate_keys:
                candidate_keys[key] = candidate
                wire["node_candidates"].append(candidate)
        for relation in part.get("relation_candidates", []):
            remapped = copy.deepcopy(relation)
            remapped["supporting_claim_refs"] = [f"C{offset + int(ref[1:])}" for ref in relation["supporting_claim_refs"]]
            wire["relation_candidates"].append(remapped)
    _wire_v2_projection(wire, catalog, context)  # Aggregate caps and references remain enforced.
    content = _json(wire)
    values = {"series_id": series.series_id, "wire_json": content, "coverage": asdict(coverage),
              "ordered_segment_result_sha256": ordered_sha, "expander_version": SOURCE_ANALYSIS_WIRE_V3_EXPANDER_VERSION}
    return AggregateWireResult(series.series_id, content, coverage, tuple(ordered_sha), identity(values))


@dataclass(frozen=True)
class SegmentCallAccounting:
    segment_id: str
    attempt_identity: str
    provider_request_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_tokens: int | None
    latency_ms: float | None
    finish_reason: str | None
    raw_wire_sha256: str | None
    outcome: str


@dataclass(frozen=True)
class SeriesCallAccounting:
    provider_call_count: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_tokens: int | None
    latency_ms: float | None
    unknown_usage_calls: int
    output_token_liability: int
    provider_request_ids: tuple[str | None, ...]
    finish_reasons: tuple[str | None, ...]
    raw_wire_hashes: tuple[str | None, ...]
    segment_outcomes: tuple[tuple[str, str], ...]


def account_series_calls(series: ExtractionSeries, plan: ExtractionPlan,
                         calls: tuple[SegmentCallAccounting, ...]) -> SeriesCallAccounting:
    _plan(series, plan)
    ceilings = {s.segment_id: s.max_output_tokens for s in plan.segments}
    if len({c.attempt_identity for c in calls}) != len(calls) or any(c.segment_id not in ceilings for c in calls):
        raise BoundedExtractionError("INVALID_CALL_IDENTITY")
    for call in calls:
        if (not isinstance(call.attempt_identity, str) or not call.attempt_identity
                or call.outcome not in ("SUCCEEDED", "FAILED", "TRUNCATED", "UNKNOWN")
                or call.latency_ms is not None and (type(call.latency_ms) not in (int, float)
                    or not math.isfinite(call.latency_ms) or call.latency_ms < 0)):
            raise BoundedExtractionError("INVALID_CALL_ACCOUNTING")
        for field in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens"):
            value = getattr(call, field)
            if value is not None and (type(value) is not int or value < 0):
                raise BoundedExtractionError("INVALID_CALL_USAGE")
        if (call.output_tokens is not None and call.output_tokens > ceilings[call.segment_id]
                or call.cached_tokens is not None and call.input_tokens is not None and call.cached_tokens > call.input_tokens
                or call.total_tokens is not None and call.input_tokens is not None and call.output_tokens is not None
                and call.total_tokens != call.input_tokens + call.output_tokens):
            raise BoundedExtractionError("INVALID_CALL_USAGE")
    liability = sum(c.output_tokens if c.output_tokens is not None else ceilings[c.segment_id] for c in calls)
    if len(calls) > series.budget.max_provider_calls or liability > series.budget.max_cumulative_output_tokens:
        raise BoundedExtractionError("SERIES_BUDGET_EXCEEDED")
    def total(field):
        values = [getattr(c, field) for c in calls]
        return sum(values) if all(v is not None for v in values) else None
    return SeriesCallAccounting(len(calls), *(total(f) for f in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens", "latency_ms")),
                                sum(any(getattr(c, f) is None for f in ("input_tokens", "output_tokens", "total_tokens")) for c in calls),
                                liability, tuple(c.provider_request_id for c in calls), tuple(c.finish_reason for c in calls),
                                tuple(c.raw_wire_sha256 for c in calls), tuple((c.segment_id, c.outcome) for c in calls))
