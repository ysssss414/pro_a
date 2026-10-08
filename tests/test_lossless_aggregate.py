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
