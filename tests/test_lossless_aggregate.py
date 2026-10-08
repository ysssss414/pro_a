"""Synthetic authority receipts and bounded lossless aggregates; never live approval."""
import copy
import json

import pytest

from pro_a.evidence_binding import identity
from pro_a.source_metadata_authority import (
    DECISION_VERSION, FIELDS, MetadataAuthorityError, authorize_resolution,
    candidate_resolution, scope, validate_resolution,
)
from pro_a.lossless_aggregate import build_aggregate, expand_aggregate, LosslessAggregateError
from pro_a.claim_observations import build_observation_ledger
from test_claim_observations import fixture
from test_bounded_extraction import result


def synthetic_authority(bound, values=None, evidence=()):
    candidate = candidate_resolution(bound, evidence)
    decision = {'version': DECISION_VERSION, 'candidate_identity': candidate['identity'],
        'scope_sha256': identity(bound), 'approved': True, 'actor': 'SYNTHETIC_TEST_ONLY',
        'reason': 'Disposable offline qualification', 'decision_reference': 'SYNTHETIC_NOT_LIVE',
        'values': values or {'title': 'Synthetic', 'publication_time': '', 'author': 'Synthetic',
            'organization': '', 'source_rank': 'A', 'source_origin_type': 'primary'},
        'summary_policy': 'PRESERVE_ALL_VARIANTS_UNRESOLVED'}
    return authorize_resolution(candidate, decision)


def aggregate_case(count=146):
    ctx, catalog, series, plan = fixture(count)
    results = tuple(result(ctx, catalog, series, leaf) for leaf in plan.leaves)
    bound = scope(series.processing_run_id, 'SRC_SYNTHETIC', ctx.source_sha256,
        [{'source_piece_id': ctx.piece.piece_id, 'series_id': series.series_id,
          'series_sha256': series.series_sha256}], [r.result_sha256 for r in results])
    authority = synthetic_authority(bound)
    document = build_aggregate('SRC_SYNTHETIC', series, plan, results, catalog, ctx, authority)
    return document, (series, plan, results, catalog, ctx), authority


def test_model_agreement_never_confers_authority():
    _, _, authority = aggregate_case(3)
    evidence = [{'field': f, 'kind': 'MODEL_DERIVED_UNCONFIRMED', 'value': 'Same model vote',
        'source_sha256': authority['scope']['source_sha256'], 'evidence': {'segment': i}}
        for f in FIELDS for i in range(5)]
    candidate = candidate_resolution(authority['scope'], evidence)
    assert all(f['authority_kind'] == 'UNRESOLVED' for f in candidate['fields'].values())
    with pytest.raises(MetadataAuthorityError, match='NEEDS_HUMAN_RESOLUTION'):
        validate_resolution(candidate)


@pytest.mark.parametrize('count', [99, 100, 101, 146, 209])
def test_finite_aggregate_preserves_every_original(count):
    document, args, authority = aggregate_case(count)
    series, plan, results, catalog, ctx = args
    assert len(document['native_input']['claims']) == count
    assert document['claim_capacity'] == 100 * len(plan.leaves)
    assert all(len(json.loads(r.wire_json)['claims']) <= 100 for r in results)
    assert document['observation_ledger'] == build_observation_ledger('SRC_SYNTHETIC', series, plan, results, catalog, ctx)
    assert [c['claim_ref'] for c in document['native_input']['claims']] == [f'C{i}' for i in range(1, count+1)]
    assert expand_aggregate(json.loads(json.dumps(document)), *args) == document['native_input']
    assert document['source_metadata_resolution_identity'] == authority['identity']
    assert len(document['components']) == len(results)
    damaged = copy.deepcopy(document)
    damaged['native_input']['claims'].pop()
    with pytest.raises(LosslessAggregateError, match='AGGREGATE_IDENTITY_MISMATCH'):
        expand_aggregate(damaged, *args)


@pytest.mark.parametrize('field', FIELDS)
def test_resolution_fields_are_hash_bound(field):
    _, _, authority = aggregate_case(3)
    authority['fields'][field]['resolved_value'] = 'UNAUTHORIZED_EDIT'
    with pytest.raises(MetadataAuthorityError):
        validate_resolution(authority)


def test_verified_conflicts_require_explicit_disposition():
    _, _, authority = aggregate_case(3)
    evidence = [{'field': 'author', 'kind': 'VERIFIED_DOCUMENT_EVIDENCE', 'value': v,
        'source_sha256': authority['scope']['source_sha256'], 'evidence': {'page': i}}
        for i, v in enumerate(('A', 'B'), 1)]
    with pytest.raises(MetadataAuthorityError, match='CONFLICTING_AUTHORITY_EVIDENCE'):
        synthetic_authority(authority['scope'], evidence=evidence)


def test_original_segment_100_limit_is_still_enforced():
    from pro_a.bounded_extraction import create_segment_wire_result
    ctx, catalog, series, plan = fixture(1)
    original = result(ctx, catalog, series, plan.leaves[0])
    wire = json.loads(original.wire_json)
    wire['claims'] = [copy.deepcopy(wire['claims'][0]) for _ in range(101)]
    with pytest.raises(ValueError, match='bounded array'):
        create_segment_wire_result(series, plan.leaves[0], wire, original.dispositions, catalog, ctx)


def test_local_relations_and_summary_variants_survive_global_projection():
    from pro_a.bounded_extraction import create_extraction_series, create_segment_wire_result, initial_extraction_plan, SeriesBudget
    from pro_a.source_analysis_wire import build_source_evidence_catalog
    from test_source_analysis_wire import context
    ctx = context('Product Alpha uses Material Beta. Product Alpha uses Material Beta again.', ('NODE_A', 'NODE_B'))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, 'RUN_RELATIONS', SeriesBudget(initial_evidence_refs=1))
    plan = initial_extraction_plan(series)
    results = []
    for i, leaf in enumerate(plan.leaves):
        original = result(ctx, catalog, series, leaf)
        wire = json.loads(original.wire_json)
        wire['source_metadata']['summary'] = f'Original synthetic summary {i}'
        wire['relation_candidates'] = [{'from_node_id': 'NODE_A', 'to_node_id': 'NODE_B', 'relation_type': 'uses',
            'supporting_claim_refs': ['C1'], 'scope': 'Product Alpha', 'confidence': 0.9}]
        results.append(create_segment_wire_result(series, leaf, wire, original.dispositions, catalog, ctx))
    bound = scope(series.processing_run_id, 'SRC_SYNTHETIC', ctx.source_sha256,
        [{'source_piece_id': ctx.piece.piece_id, 'series_id': series.series_id, 'series_sha256': series.series_sha256}],
        [r.result_sha256 for r in results])
    document = build_aggregate('SRC_SYNTHETIC', series, plan, tuple(results), catalog, ctx, synthetic_authority(bound))
    assert [r['supporting_claim_refs'] for r in document['native_input']['relation_candidates']] == [['C1'], ['C2']]
    assert [p['metadata_variant']['summary'] for p in document['components']] == ['Original synthetic summary 0', 'Original synthetic summary 1']
    assert document['native_input']['source_metadata']['summary'] == ''
    assert [o['binding']['local_claim_ordinal'] for o in document['observation_ledger']['observations']] == [1, 1]
    assert [o['aggregate_ordinal'] for o in document['observation_ledger']['observations']] == [1, 2]


def test_five_series_native_cross_piece_merge_is_losslessly_reviewable(tmp_path):
    import hashlib
    from pro_a.analyzer import Analyzer, InitialExtractionPlan, PlannedExtractionPiece
    from pro_a.bounded_extraction import create_extraction_series, initial_extraction_plan
    from pro_a.source_analysis_wire import build_source_evidence_catalog
    from pro_a.claim_observations import combine_observation_ledgers, build_native_projection, private_review_artifact, BLOCKED
    from pro_a.workbench.bounded_source_analysis import BoundedExtractionReplay
    from test_source_analysis_wire import context
    from stability_helpers import make_config
    values = []
    for i in range(1, 6):
        ctx = context(f'Common assertion.\nPiece{i} unique assertion.', source_sha='a'*64, chunk_index=i)
        catalog = build_source_evidence_catalog(ctx)
        series = create_extraction_series(ctx, catalog, 'SYNTHETIC_MULTI_SERIES')
        plan = initial_extraction_plan(series)
        results = tuple(result(ctx, catalog, series, leaf) for leaf in plan.leaves)
        values.append((series, plan, results, catalog, ctx))
    bound = scope('SYNTHETIC_MULTI_SERIES', 'SRC_SYNTHETIC', 'a'*64,
        [{'source_piece_id': c.piece.piece_id, 'series_id': s.series_id, 'series_sha256': s.series_sha256}
         for s, _, _, _, c in values], [r.result_sha256 for _, _, rr, _, _ in values for r in rr])
    authority = synthetic_authority(bound)
    aggregates = [build_aggregate('SRC_SYNTHETIC', s, p, rr, cat, ctx, authority) for s, p, rr, cat, ctx in values]
    manifest = combine_observation_ledgers([d['observation_ledger'] for d in aggregates])
    planned, responses = [], {}
    for i, (args, document) in enumerate(zip(values, aggregates)):
        ctx = args[-1]
        prompt = f'SYNTHETIC_FROZEN_{i}'
        planned.append(PlannedExtractionPiece(ctx.piece, 0, len(ctx.piece.source_text), (), (), prompt))
        responses[hashlib.sha256(prompt.encode()).hexdigest()] = document['native_input']
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.plan_initial_extraction = lambda *a, **k: InitialExtractionPlan(4000, 0, identity([]), tuple(planned), {}, identity({'synthetic': True}))
    analyzer.llm = BoundedExtractionReplay(cfg.llm, responses, {k: {} for k in responses})
    analysis = analyzer.analyze_source('synthetic.txt', '\n'.join(v[-1].piece.source_text for v in values), 'deep', adaptive_retry_policy='forbid')
    projection = build_native_projection(manifest, analysis.claims)
    assert len(projection['groups']) == 6
    common = projection['groups'][0]
    assert common['native_claim']['_relation_claim_refs'] == ['C1', 'C3', 'C5', 'C7', 'C9']
    assert len(common['observation_ids']) == 5 and common['semantic_admission'] == BLOCKED
    mapped = [o for g in projection['groups'] for o in g['observation_ids']]
    assert len(mapped) == len(set(mapped)) == 10
    review = private_review_artifact(manifest, projection)
    stored = json.loads(json.dumps(review))
    assert private_review_artifact(stored['ledger'], stored['projection']) == review
    assert len(stored['ledger']['series_ledgers']) == 5
