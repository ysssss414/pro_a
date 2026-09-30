"""Dormant contracts, canonical fidelity and structural output-range simulations."""
import copy
import json
from dataclasses import FrozenInstanceError, asdict, replace
from types import SimpleNamespace

import pytest

from pro_a.analyzer import Analyzer
from pro_a.bounded_extraction import (
    SOURCE_ANALYSIS_WIRE_V3_VERSION, BoundedExtractionError,
    EvidenceDisposition, SeriesBudget, SegmentCallAccounting, account_series_calls,
    aggregate_segment_wires, create_extraction_series, create_segment_wire_result,
    expand_source_analysis_wire_v3, initial_extraction_plan, series_coverage, subdivide_extraction_plan,
)
from pro_a.operational_ingestion import deterministic_id
from pro_a.source_analysis_wire import build_source_evidence_catalog
from stability_helpers import make_config
from test_source_analysis_wire import canonical_claim, compact_fixture, context, dense_fixture, empty_canonical, mixed_fixture


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    monkeypatch.setattr("requests.sessions.Session.request", lambda *a, **k: pytest.fail("Network forbidden"))
    monkeypatch.setattr("pro_a.llm.ChatLLM.json", lambda *a, **k: pytest.fail("Provider forbidden"))


def v3(raw, catalog):
    wire = compact_fixture(raw, catalog)
    wire["wire_version"] = SOURCE_ANALYSIS_WIRE_V3_VERSION
    for original, compact in zip(raw["claims"], wire["claims"]):
        compact["evidence_pointer"] = original["evidence_pointer"]
    return wire


def fixture(count, budget=SeriesBudget()):
    ctx = context("\n".join(f"Synthetic product {i} has capacity {i + 1} units." for i in range(count)))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, "RUN_SYNTHETIC", budget)
    return ctx, catalog, series, initial_extraction_plan(series)


def result(ctx, catalog, series, leaf, *, claimed=True, label=None):
    raw = empty_canonical()
    refs = set(leaf.assigned_evidence_refs)
    units = [u for u in catalog.units if u.evidence_ref in refs]
    if claimed:
        raw["claims"] = [canonical_claim(u.exact_text, u, i + 1) for i, u in enumerate(units)]
    wire = v3(raw, catalog)
    dispositions = tuple(EvidenceDisposition(ref, label or ("CLAIMED" if claimed else "NO_INDEPENDENT_CLAIM"))
                         for ref in leaf.assigned_evidence_refs)
    return create_segment_wire_result(series, leaf, wire, dispositions, catalog, ctx)


def canonical_aggregate(ctx, catalog, series, plan):
    results = tuple(result(ctx, catalog, series, leaf) for leaf in plan.leaves)
    aggregate = aggregate_segment_wires(series, plan, results, catalog, ctx)
    return aggregate, expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, ctx)


@pytest.mark.parametrize("factory", [dense_fixture, mixed_fixture])
def test_v3_all_canonical_values_and_native_claim_ids(factory, tmp_path):
    cfg, db = make_config(tmp_path)
    if factory == mixed_fixture:
        a = db.add_node("示例产品甲", "Product")
        b = db.add_node("示例技术乙", "Technology")
        ctx, catalog, raw = mixed_fixture((a, b))
    else:
        ctx, catalog, raw = factory()
    # Explicit pointer is preserved even when unrelated to deterministic locator.
    raw["claims"][0]["evidence_pointer"] = "model supplied pointer"
    wire = v3({**raw, "claims": [{**c, "evidence_pointer": f"[[{catalog.units[0].locator}]]" if catalog.units[0].locator != "TEXT" else "TEXT"}
                               if i == 0 else c for i, c in enumerate(raw["claims"])]}, catalog)
    wire["claims"][0]["evidence_pointer"] = raw["claims"][0]["evidence_pointer"]
    expanded = expand_source_analysis_wire_v3(wire, catalog, ctx)
    assert expanded == raw
    analyzer = Analyzer(cfg, db)
    def native(value):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *args: copy.deepcopy(value))
        return analyzer.analyze_source("synthetic.txt", ctx.piece.source_text, "deep", adaptive_retry_policy="forbid")
    old, new = native(raw), native(expanded)
    assert old == new
    from pro_a.analyzer import resolve_evidence_locator
    from pro_a.pipeline import build_claim_record
    record = build_claim_record("CLM_SYNTHETIC", "SRC_SYNTHETIC", new.claims[0], "2026-09-15", ctx.piece.source_text,
                                ingestion_time="2026-09-15T00:00:00Z", created_at="2026-09-15T00:00:00Z")
    assert record["evidence_pointer"] == "model supplied pointer"
    assert record["structured"]["validation"]["source_locator"] == resolve_evidence_locator(
        ctx.piece.source_text, new.claims[0]["evidence_excerpt"])
    for index, (left, right) in enumerate(zip(old.claims, new.claims)):
        seed = lambda claim: {"source_sha256": ctx.source_sha256, "claim_index": index,
                              "claim": {k: v for k, v in claim.items() if not k.startswith("origin_")}}
        assert deterministic_id("CLM", seed(left)) == deterministic_id("CLM", seed(right))


def test_one_segment_success_and_immutable_contracts():
    ctx, catalog, series, plan = fixture(4)
    aggregate, canonical = canonical_aggregate(ctx, catalog, series, plan)
    assert len(plan.leaves) == 1 and len(canonical["claims"]) == 4
    assert aggregate.coverage.complete and not aggregate.coverage.missing_refs
    assert series.logical_job_count == 1 and plan.leaves[0].max_output_tokens == 12000
    with pytest.raises(FrozenInstanceError):
        series.series_id = "changed"
    with pytest.raises(FrozenInstanceError):
        plan.leaves[0].segment_id = "changed"


def test_two_segment_initial_plan_and_completion_order():
    ctx, catalog, series, plan = fixture(17)
    assert [len(s.assigned_evidence_refs) for s in plan.leaves] == [16, 1]
    records = tuple(result(ctx, catalog, series, leaf) for leaf in plan.leaves)
    first = aggregate_segment_wires(series, plan, records, catalog, ctx)
    assert first == aggregate_segment_wires(series, plan, tuple(reversed(records)), catalog, ctx)
    assert len(first.coverage.closed_refs) == 17 and series.logical_job_count == 1


def test_parent_subdivision_then_children_close_without_accepting_parent():
    ctx, catalog, series, original = fixture(4)
    parent = original.leaves[0]
    incomplete = result(ctx, catalog, series, parent, claimed=False, label="SUBDIVISION_REQUIRED")
    assert not series_coverage(series, original, (incomplete,), catalog, ctx).complete
    plan = subdivide_extraction_plan(series, original, parent.segment_id)
    assert plan == subdivide_extraction_plan(series, original, parent.segment_id)
    assert plan.status(parent.segment_id) == "SUPERSEDED_BY_CHILDREN"
    assert len(parent.assigned_evidence_refs) == 4 and len(original.leaves) == 1
    assert [len(s.assigned_evidence_refs) for s in plan.leaves] == [2, 2]
    assert canonical_aggregate(ctx, catalog, series, plan)[0].coverage.complete
    with pytest.raises(BoundedExtractionError, match="SUPERSEDED"):
        aggregate_segment_wires(series, plan, (incomplete,), catalog, ctx)
    with pytest.raises(BoundedExtractionError, match="NOT_ACTIVE_LEAF"):
        subdivide_extraction_plan(series, plan, parent.segment_id)


def test_nested_subdivision_and_singleton_terminal_failure():
    ctx, catalog, series, plan = fixture(8)
    while any(len(s.assigned_evidence_refs) > 1 for s in plan.leaves):
        target = next(s for s in plan.leaves if len(s.assigned_evidence_refs) > 1)
        plan = subdivide_extraction_plan(series, plan, target.segment_id)
    assert len(plan.segments) == 15 and len(plan.leaves) == 8
    assert max(s.subdivision_depth for s in plan.leaves) == 3
    assert canonical_aggregate(ctx, catalog, series, plan)[0].coverage.complete
    with pytest.raises(BoundedExtractionError, match="EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY"):
        subdivide_extraction_plan(series, plan, plan.leaves[0].segment_id)


@pytest.mark.parametrize("count", range(1, 65))
def test_structural_tree_bounds_and_finite_policy(count):
    ctx, catalog, series, plan = fixture(count)
    roots = len(plan.leaves)
    stopped = False
    while any(len(s.assigned_evidence_refs) > 1 for s in plan.leaves):
        target = next(s for s in plan.leaves if len(s.assigned_evidence_refs) > 1)
        try:
            plan = subdivide_extraction_plan(series, plan, target.segment_id)
        except BoundedExtractionError as exc:
            assert str(exc) == "EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY"
            stopped = True
            break
    assert len(plan.leaves) <= 16
    assert len(plan.segments) <= 2 * len(plan.leaves) - roots
    assert max(s.subdivision_depth for s in plan.leaves) <= 4
    assert series.logical_job_count == 1
    assert stopped == (count > 16)


def test_duplicate_assignment_and_missing_disposition_fail_closed():
    ctx, catalog, series, plan = fixture(3)
    leaf = plan.leaves[0]
    bad_plan = replace(plan, segments=plan.segments + (leaf,))
    with pytest.raises(BoundedExtractionError, match="DUPLICATE_SEGMENT_IDENTITY"):
        series_coverage(series, bad_plan, (), catalog, ctx)
    good = result(ctx, catalog, series, leaf)
    with pytest.raises(BoundedExtractionError, match="MISSING_OR_DUPLICATE"):
        create_segment_wire_result(series, leaf, json.loads(good.wire_json), good.dispositions[:-1], catalog, ctx)
    with pytest.raises(BoundedExtractionError, match="DUPLICATE_SEGMENT_RESULT"):
        series_coverage(series, plan, (good, good), catalog, ctx)
    assert len(series_coverage(series, plan, (), catalog, ctx).missing_refs) == 3
    with pytest.raises(BoundedExtractionError, match="COVERAGE_INCOMPLETE"):
        aggregate_segment_wires(series, plan, (), catalog, ctx)


@pytest.mark.parametrize("label", ["NO_INDEPENDENT_CLAIM", "CONTEXT_ONLY"])
def test_zero_claim_dispositions_close_without_inventing_claims(label):
    ctx, catalog, series, plan = fixture(2)
    record = result(ctx, catalog, series, plan.leaves[0], claimed=False, label=label)
    aggregate = aggregate_segment_wires(series, plan, (record,), catalog, ctx)
    assert aggregate.coverage.complete and not json.loads(aggregate.wire_json)["claims"]


def test_multiple_claims_per_ref_and_foreign_evidence():
    ctx, catalog, series, plan = fixture(2, SeriesBudget(initial_evidence_refs=1))
    leaf = plan.leaves[0]
    record = result(ctx, catalog, series, leaf)
    wire = json.loads(record.wire_json)
    wire["claims"].append({**wire["claims"][0], "statement": "Another atomic proposition."})
    assert create_segment_wire_result(series, leaf, wire, record.dispositions, catalog, ctx)
    wire["claims"][0]["evidence_ref"] = plan.leaves[1].assigned_evidence_refs[0]
    with pytest.raises(BoundedExtractionError, match="OUTSIDE_SEGMENT"):
        create_segment_wire_result(series, leaf, wire, record.dispositions, catalog, ctx)


def test_retry_subdivision_reprocess_and_call_accounting():
    ctx, catalog, series, plan = fixture(4)
    parent = plan.leaves[0]
    def call(attempt, output=100, outcome="SUCCEEDED"):
        return SegmentCallAccounting(parent.segment_id, attempt, "provider-" + attempt,
                                     50 if output is not None else None, output,
                                     50 + output if output is not None else None,
                                     20 if output is not None else None, 10.0, "stop", None, outcome)
    usage = account_series_calls(series, plan, (call("attempt1", 12000, "TRUNCATED"), call("attempt2")))
    assert usage.provider_call_count == 2 and usage.output_tokens == 12100
    assert usage.total_tokens == 12200 and usage.cached_tokens == 40
    unknown = account_series_calls(series, plan, (call("unknown", None, "UNKNOWN"),))
    assert unknown.total_tokens is None and unknown.unknown_usage_calls == 1 and unknown.output_token_liability == 12000
    children = subdivide_extraction_plan(series, plan, parent.segment_id)
    assert all(s.segment_id != parent.segment_id for s in children.leaves)
    assert create_extraction_series(ctx, catalog, "RUN_REPROCESS").series_id != series.series_id
    assert series.logical_job_count == 1 and parent == plan.leaves[0]
    with pytest.raises(BoundedExtractionError, match="CALL_IDENTITY"):
        account_series_calls(series, plan, (call("same"), call("same")))
    with pytest.raises(BoundedExtractionError, match="SERIES_BUDGET_EXCEEDED"):
        account_series_calls(series, plan, tuple(call(str(i)) for i in range(33)))


def test_crash_replay_reconstructs_exact_contracts_and_wire():
    ctx, catalog, series, original = fixture(6)
    split_ids, plan = [], original
    for _ in range(2):
        target = plan.leaves[0].segment_id
        split_ids.append(target)
        plan = subdivide_extraction_plan(series, plan, target)
    records = tuple(result(ctx, catalog, series, leaf) for leaf in plan.leaves)
    before = aggregate_segment_wires(series, plan, records, catalog, ctx)
    journal = json.loads(json.dumps({"split_ids": split_ids, "records": [asdict(r) for r in records]}))
    replay = initial_extraction_plan(create_extraction_series(ctx, catalog, "RUN_SYNTHETIC"))
    for segment_id in journal["split_ids"]:
        replay = subdivide_extraction_plan(series, replay, segment_id)
    restored = tuple(create_segment_wire_result(series, next(s for s in replay.leaves if s.segment_id == item["segment_id"]),
                     json.loads(item["wire_json"]), tuple(EvidenceDisposition(**d) for d in item["dispositions"]), catalog, ctx)
                     for item in journal["records"])
    assert replay == plan and restored == records
    assert aggregate_segment_wires(series, replay, restored, catalog, ctx) == before
    with pytest.raises(BoundedExtractionError, match="RESULT_IDENTITY_MISMATCH"):
        aggregate_segment_wires(series, replay, (replace(restored[0], result_sha256="tampered"), *restored[1:]), catalog, ctx)


@pytest.mark.parametrize("text", [
    "专家：若订单充足，产能可能增长。\n主持人：需求如何？\n" * 12,
    "Question: what is the outlook?\nAnswer: sales may increase if demand recovers.\n" * 10,
    "Technical density: A uses B; B depends on C; output is conditional.\n" * 24,
    "Company announces a new factory. The project is subject to permits.\n" * 10,
    "Broker forecast: earnings may grow, conditional on prices. Risks remain.\n" * 10,
    "item,relationship,evidence_status\nGPU,uses HBM,present\nGPU,uses HBM,present\n" * 8,
    "Filing: no material change.\n\n" * 12,
    "Mixed 专家：capacity可能增长20%。 If orders arrive, revenue may increase.\n" * 18,
])
def test_generalization_fixed_initial_policy(text):
    ctx = context(text)
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, "RUN_GENERALIZATION")
    plan = initial_extraction_plan(series)
    assert len(plan.leaves) <= 16
    assert all(1 <= len(s.assigned_evidence_refs) <= 16 for s in plan.leaves)
    assert tuple(ref for s in plan.leaves for ref in s.assigned_evidence_refs) == series.eligible_evidence_refs
    records = tuple(result(ctx, catalog, series, leaf, claimed=False, label="CONTEXT_ONLY") for leaf in plan.leaves)
    assert series_coverage(series, plan, records, catalog, ctx).complete


def size_benchmark():
    ctx, catalog, raw = dense_fixture()
    old = compact_fixture(raw, catalog)
    corrected = v3(raw, catalog)
    assert expand_source_analysis_wire_v3(corrected, catalog, ctx) == raw
    size = lambda value: {"chars": len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
                          "bytes": len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))}
    values = {"canonical": size(raw), "foundation_wire_v2": size(old), "corrected_wire_v3": size(corrected)}
    values["corrected_reduction_percent"] = {unit: 100 * (1 - values["corrected_wire_v3"][unit] / values["canonical"][unit]) for unit in ("chars", "bytes")}
    return values


def test_size_benchmark_preserves_pointer_and_reports_cost_separately():
    measured = size_benchmark()
    assert measured["corrected_wire_v3"]["chars"] < measured["canonical"]["chars"]
    assert measured["corrected_wire_v3"]["chars"] > measured["foundation_wire_v2"]["chars"]


def test_local_c1_refs_are_remapped_and_cross_segment_refs_rejected():
    ctx = context("Product Alpha uses Material Beta. Product Alpha uses Material Beta again.", ("NODE_A", "NODE_B"))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, "RUN_RELATIONS", SeriesBudget(initial_evidence_refs=1))
    plan = initial_extraction_plan(series)
    records = []
    for leaf in plan.leaves:
        base = result(ctx, catalog, series, leaf)
        wire = json.loads(base.wire_json)
        wire["relation_candidates"] = [{"from_node_id": "NODE_A", "to_node_id": "NODE_B", "relation_type": "uses",
                                        "supporting_claim_refs": ["C1"], "scope": "Product Alpha", "confidence": 0.9}]
        records.append(create_segment_wire_result(series, leaf, wire, base.dispositions, catalog, ctx))
    aggregate = aggregate_segment_wires(series, plan, tuple(records), catalog, ctx)
    assert [r["supporting_claim_refs"] for r in json.loads(aggregate.wire_json)["relation_candidates"]] == [["C1"], ["C2"]]
    wire["relation_candidates"][0]["supporting_claim_refs"] = ["C2"]
    with pytest.raises(ValueError, match="local ordinal"):
        create_segment_wire_result(series, plan.leaves[-1], wire, records[-1].dispositions, catalog, ctx)


def test_candidate_exact_dedup_conflicts_and_first_metadata():
    ctx, catalog, series, plan = fixture(2, SeriesBudget(initial_evidence_refs=1))
    records = []
    candidate = {"canonical_name": "Synthetic Product", "primary_type": "Product", "confidence": 0.9,
                 "independent_research_value": True, "maintenance_rationale": "Synthetic reason"}
    for index, leaf in enumerate(plan.leaves):
        base = result(ctx, catalog, series, leaf)
        wire = json.loads(base.wire_json)
        wire["source_metadata"]["title"] = f"Metadata {index}"
        wire["node_candidates"] = [copy.deepcopy(candidate)]
        records.append(create_segment_wire_result(series, leaf, wire, base.dispositions, catalog, ctx))
    aggregate = json.loads(aggregate_segment_wires(series, plan, tuple(reversed(records)), catalog, ctx).wire_json)
    assert aggregate["source_metadata"]["title"] == "Metadata 0"
    assert aggregate["node_candidates"] == [candidate]
    wire["node_candidates"][0]["maintenance_rationale"] = "Semantically different reason"
    changed = create_segment_wire_result(series, plan.leaves[-1], wire, records[-1].dispositions, catalog, ctx)
    with pytest.raises(BoundedExtractionError, match="NODE_CANDIDATE_CONFLICT"):
        aggregate_segment_wires(series, plan, (records[0], changed), catalog, ctx)


@pytest.mark.parametrize("field,value", [("max_output_tokens", 16000), ("range_start", True), ("segment_id", "forged"),
                                         ("assigned_evidence_refs", ("EV_FOREIGN",))])
def test_segment_identity_cannot_be_mutated(field, value):
    ctx, catalog, series, plan = fixture(1)
    forged = replace(plan.leaves[0], **{field: value})
    with pytest.raises(BoundedExtractionError, match="SEGMENT_IDENTITY"):
        result(ctx, catalog, series, forged, claimed=False)


def test_aggregate_keeps_native_100_claim_limit():
    ctx, catalog, series, plan = fixture(2, SeriesBudget(initial_evidence_refs=1))
    records = []
    for leaf in plan.leaves:
        base = result(ctx, catalog, series, leaf)
        wire = json.loads(base.wire_json)
        wire["claims"] = [{**wire["claims"][0], "statement": f"Synthetic atomic proposition {i}"} for i in range(51)]
        records.append(create_segment_wire_result(series, leaf, wire, base.dispositions, catalog, ctx))
    with pytest.raises(ValueError, match="bounded array"):
        aggregate_segment_wires(series, plan, tuple(records), catalog, ctx)


@pytest.mark.parametrize("latency", [-1, True, float("nan"), float("inf")])
def test_invalid_latency_is_rejected(latency):
    ctx, catalog, series, plan = fixture(1)
    call = SegmentCallAccounting(plan.leaves[0].segment_id, "attempt", None, None, None, None, None, latency, None, None, "UNKNOWN")
    with pytest.raises(BoundedExtractionError, match="CALL_ACCOUNTING"):
        account_series_calls(series, plan, (call,))


def test_dense_multisegment_aggregation_matches_existing_canonical_and_claim_ids(tmp_path):
    ctx, catalog, raw = dense_fixture()
    series = create_extraction_series(ctx, catalog, "RUN_DENSE_GOLDEN")
    plan = initial_extraction_plan(series)
    records = []
    for leaf in plan.leaves:
        part = copy.deepcopy(raw)
        assigned = set(leaf.assigned_evidence_refs)
        quotes = {u.exact_text for u in catalog.units if u.evidence_ref in assigned}
        part["claims"] = [c for c in part["claims"] if c["evidence_excerpt"] in quotes]
        local_evidence = next(u.exact_text for u in catalog.units if u.evidence_ref in assigned)
        for candidate in part["node_candidates"]:
            if candidate.get("evidence_excerpt"):
                candidate["evidence_excerpt"] = local_evidence
        for index, claim in enumerate(part["claims"], 1):
            claim["claim_ref"] = f"C{index}"
        records.append(create_segment_wire_result(series, leaf, v3(part, catalog),
                       tuple(EvidenceDisposition(ref, "CLAIMED") for ref in leaf.assigned_evidence_refs), catalog, ctx))
    aggregate = aggregate_segment_wires(series, plan, tuple(reversed(records)), catalog, ctx)
    expanded = expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, ctx)
    assert len(plan.leaves) == 3 and expanded == raw
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    old = analyzer._validate_source_output(copy.deepcopy(raw), ctx.piece.source_text)
    new = analyzer._validate_source_output(copy.deepcopy(expanded), ctx.piece.source_text)
    assert old == new
    for index, (left, right) in enumerate(zip(old["claims"], new["claims"])):
        seed = lambda c: {"source_sha256": ctx.source_sha256, "claim_index": index, "claim": c}
        assert deterministic_id("CLM", seed(left)) == deterministic_id("CLM", seed(right))


def test_v3_occurrence_and_normalized_bindings_expand_exact_legacy_values():
    ctx = context(r"[[PAGE:1]]capacity capacity \& ＡＢＣ")
    catalog = build_source_evidence_catalog(ctx)
    unit = catalog.units[0]
    raw = empty_canonical()
    raw["claims"] = [canonical_claim("First standalone claim.", unit, 1), canonical_claim("Second standalone claim.", unit, 2)]
    wire = v3(raw, catalog)
    wire["claims"][0].update(evidence_selector="capacity", evidence_occurrence=2, evidence_pointer="legacy row label")
    wire["claims"][1].update(evidence_selector="& ABC", evidence_pointer="legacy normalized label")
    raw["claims"][0].update(evidence_excerpt="capacity", evidence_pointer="legacy row label")
    raw["claims"][1].update(evidence_excerpt="& ABC", evidence_pointer="legacy normalized label")
    assert expand_source_analysis_wire_v3(wire, catalog, ctx) == raw
    series = create_extraction_series(ctx, catalog, "RUN_BINDING_GOLDEN")
    plan = initial_extraction_plan(series)
    record = create_segment_wire_result(series, plan.leaves[0], wire, (EvidenceDisposition(unit.evidence_ref, "CLAIMED"),), catalog, ctx)
    aggregate = aggregate_segment_wires(series, plan, (record,), catalog, ctx)
    assert expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, ctx) == raw
