"""Qualification probes, not an adapter. Synthetic inputs and no Provider calls."""
import json
import copy

import pytest

from pro_a import candidate_origin as origin, output_provider_record_v7 as v7
from pro_a.workbench.advisory_review import AdvisoryReview
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_workbench import ReviewWorkbench
from test_candidate_origin import fixture, build
from workbench_stage6_fixture import stage6_fixture
from pro_a.workbench.source_operations import prepare_source_operations
from pro_a.evidence_binding import identity
from test_lossless_aggregate import aggregate_case, synthetic_authority


def test_v7_cannot_be_presented_as_existing_v4_candidate_origin():
    record, scope, segment, catalog, context = fixture()
    scope['provider_record_version'] = v7.VERSION
    with pytest.raises(ValueError, match='CANDIDATE_PROTOCOL_UNSUPPORTED'):
        origin.build(json.dumps(record).encode(), scope, segment, catalog, context)


def test_range_revision_cannot_smuggle_a_new_statement():
    values = fixture()
    record, scope, segment, catalog, context = values
    record['claims'][0]['related_candidate_names'] = []
    original = build(values)
    parent = next(o for o in original['objects'] if o['family'] == 'claims')
    unit = catalog.units[0]
    revision = {'evidence_ref': unit.evidence_ref, 'source_start': unit.source_start,
                'source_end': unit.source_end, 'reason': 'Synthetic only',
                'reviewer': 'Synthetic proposer', 'statement': 'Unauthorized child assertion'}
    raw = json.dumps(record, ensure_ascii=False).encode()
    with pytest.raises(ValueError, match='CANDIDATE_REVISION_REJECTED'):
        origin.build(raw, scope, segment, catalog, context, {parent['observation_id']: revision})
    assert build(values) == original


def test_legacy_packet_registration_does_not_create_p0_candidate_authority(tmp_path):
    fixture_value = stage6_fixture(tmp_path)
    config = fixture_value['config']
    prepare_source_operations(config)
    handle = fixture_value['artifact_id']
    reviews = ReviewWorkbench(config)
    before = config.knowledge_db.read_bytes()
    with pytest.raises(BoundaryError, match='CANDIDATE_REVIEW_REQUIRED'):
        AdvisoryReview(reviews).submit(handle, {})
    assert config.knowledge_db.read_bytes() == before
    with reviews.store.connect() as db:
        assert db.execute('SELECT count(*) FROM sealed_review_artifacts').fetchone()[0] == 0


def test_cross_batch_metadata_text_is_not_silently_voted_or_overwritten():
    left = build(fixture())
    values = fixture()
    values[0]['source_metadata']['title'] = 'Different synthetic batch title'
    right = build(values)
    with pytest.raises(ValueError, match='CANDIDATE_SOURCE_METADATA_CONFLICT'):
        origin.semantic_projection([left, right])


def test_explicit_unknown_author_and_date_remain_unknown():
    _, _, authority = aggregate_case(3)
    values = {'title': 'Synthetic source', 'publication_time': '', 'author': '',
              'organization': '', 'source_rank': 'UNRANKED', 'source_origin_type': 'unknown'}
    resolved = synthetic_authority(authority['scope'], values=values)
    for field in ('publication_time', 'author', 'organization'):
        assert resolved['fields'][field]['resolved_value'] == ''


def test_partially_supported_compound_cannot_reuse_full_support_approval():
    # Judgment is explicitly simulated, not supplied by a text-splitting algorithm.
    from pro_a.workbench.advisory_review import validate_promotable
    packet = {'immutable_packet_sha256': 'a' * 64, 'claims': [
        {'candidate_id': 'CLM_SYNTHETIC', 'content_sha256': 'b' * 64,
         'content': {'statement': 'Synthetic capacity is 12; a future order is confirmed.',
                     'evidence_excerpt': 'Synthetic capacity is 12.'},
         'human_input': {'decision': 'KEEP'}}], 'nodes': [], 'relations': []}
    opinions = {}
    for slot in ('A', 'B'):
        body = {'version': 'native-advice-v1', 'slot': slot,
                'packet_sha256': packet['immutable_packet_sha256'],
                'context_sha256': 'c' * 64, 'reviewer_type': 'MODEL',
                'reviewer_id': 'synthetic-' + slot, 'items': [
                    {'candidate_id': 'CLM_SYNTHETIC', 'content_sha256': 'b' * 64,
                     'judgment': 'UNCERTAIN', 'reason': 'Order clause has no source support.'}]}
        opinions[slot] = {**body, 'sha256': identity(body)}
    before = copy.deepcopy(packet)
    with pytest.raises(BoundaryError, match='CANDIDATE_SUPPORT_UNRESOLVED'):
        validate_promotable(packet, opinions)
    assert packet == before
