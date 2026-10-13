"""Installed Candidate advice publication, registration and Human seal gates."""
import copy
import json
import uuid

import pytest

from pro_a.mcp.review_context import basis
from pro_a.mcp.service import ReadService
from pro_a.workbench.advisory_review import AdvisoryReview
from pro_a.workbench.bounded_extraction_persistence import canonical
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.source_operations import SourceOperations
from series_binding_helpers import rows, synthetic_providers
from test_candidate_replacement import make_case, replacement


HUMAN = {'actor': 'synthetic-human', 'session_id': 'synthetic-session', 'principal_type': 'HUMAN_USER'}


@pytest.fixture
def advice_case(tmp_path_factory, monkeypatch):
    # No pre-created advice directories/files: use the real publication chain.
    value = make_case(tmp_path_factory.mktemp('advice'), monkeypatch)
    service = value['service']
    run_id = replacement(value)['run']['processing_run_id']
    for _ in range(2):
        service.advance_once(worker_id='synthetic', processing_run_id=run_id)
    with synthetic_providers(value) as provider:
        run = service.advance_once(worker_id='synthetic', processing_run_id=run_id, provider=provider)
    assert run['state'] == 'HUMAN_REVIEW_REQUIRED'
    handle = run['packet_artifact_id']
    reviews = ReviewWorkbench(value['config'])
    packet = reviews._context(handle)[0]
    advice = AdvisoryReview(reviews)
    assert not advice._path(packet, 'A').parent.exists()
    context, candidates, _ = basis(ReadService(value['config']), handle, 'blind', None)
    opinions = {slot: {'slot': slot, 'reviewer_type': 'MODEL', 'reviewer_id': 'synthetic-' + slot,
        'context_sha256': context.context_sha256,
        'items': [{'candidate_id': c.candidate_id, 'content_sha256': c.content_sha256,
                   'judgment': 'SUPPORTED', 'reason': 'Synthetic evidence inspected'} for c in candidates]}
        for slot in ('A', 'B')}
    value.update(handle=handle, reviews=reviews, packet=packet, advice=advice, opinions=opinions,
                 production=value['config'].knowledge_db.read_bytes())
    return value


def request(value, **extra):
    review = value['reviews'].read(value['handle'])['review']
    return {'basis_id': review['basis_id'], 'expected_revision': review['revision'],
            'operation_id': uuid.uuid4().hex, 'reviewer': 'Synthetic human',
            'reason': 'Synthetic evidence checked', 'confirm': True, **extra}


def decisions(value):
    for row in value['reviews'].read(value['handle'])['items']:
        value['reviews'].mutate(value['handle'], 'decision', request(value,
            candidate_id=row['candidate_id'], decision='KEEP' if row['candidate_type'] == 'CLAIM' else 'CREATE',
            target_node_id=''), HUMAN)


def seal(value, **extra):
    return value['reviews'].mutate(value['handle'], 'seal', request(value, **extra), HUMAN)


def events(value):
    return [json.loads(r['event_json']) for r in rows(value, 'source_processing_events')
            if r['event_type'] == 'CANDIDATE_ADVICE_SUBMITTED']


def test_first_pair_identity_idempotency_and_human_seal(advice_case):
    value = advice_case
    advice, packet, handle = value['advice'], value['packet'], value['handle']
    saved = {}
    for slot in ('A', 'B'):
        saved[slot] = advice.submit(handle, value['opinions'][slot])
        path = advice._path(packet, slot)
        assert path.read_bytes() == canonical(saved[slot]).encode('utf-8')
        assert saved[slot]['packet_sha256'] == packet['immutable_packet_sha256']
        assert saved[slot]['context_sha256'] == value['opinions'][slot]['context_sha256']
        assert events(value)[-1] == {'slot': slot, 'packet_sha256': packet['immutable_packet_sha256'],
                                    'opinion_sha256': saved[slot]['sha256']}
        before = value['config'].state_db.read_bytes()
        assert advice.submit(handle, value['opinions'][slot]) == saved[slot]
        assert value['config'].state_db.read_bytes() == before
        conflict = copy.deepcopy(value['opinions'][slot])
        conflict['items'][0]['reason'] = 'Different submitted content'
        with pytest.raises(BoundaryError, match='ADVICE_SUBMISSION_CONFLICT'):
            advice.submit(handle, conflict)
        if slot == 'A':
            with pytest.raises(BoundaryError, match='DUAL_ADVICE_REQUIRED'):
                advice.read(packet, handle=handle)
    assert advice.read(packet, handle=handle) == saved
    assert len(events(value)) == 2
    with pytest.raises(BoundaryError, match='VALIDATION_ERROR'):
        seal(value)  # Complete A/B does not create Human decisions.
    decisions(value)
    with pytest.raises(BoundaryError, match='SEAL_CONFIRMATION_REQUIRED'):
        seal(value, confirm=False)
    with pytest.raises(BoundaryError, match='HUMAN_USER_REQUIRED'):
        value['reviews'].mutate(handle, 'seal', request(value), {**HUMAN, 'principal_type': 'MODEL'})
    assert seal(value)['production_authorized'] is False
    assert value['reviews'].read(handle)['review']['status'] == 'SEALED'
    assert value['config'].knowledge_db.read_bytes() == value['production']


@pytest.mark.parametrize('fault', ['publication', 'registration'])
def test_publication_failure_cannot_authorize_and_exact_replay_recovers(advice_case, monkeypatch, fault):
    value = advice_case
    advice, packet, handle = value['advice'], value['packet'], value['handle']
    path = advice._path(packet, 'A')
    decisions(value)
    with monkeypatch.context() as patch:
        if fault == 'publication':
            import pro_a.workbench.bounded_extraction_persistence as persistence
            original = persistence.os.replace
            def fail_publish(source, target):
                if target == path:
                    raise OSError('SYNTHETIC_PUBLICATION_FAILURE')
                return original(source, target)
            patch.setattr(persistence.os, 'replace', fail_publish)
        else:
            original = SourceOperations._event
            def fail_register(connection, run_id, kind, payload):
                original(connection, run_id, kind, payload)
                if kind == 'CANDIDATE_ADVICE_SUBMITTED':
                    raise OSError('SYNTHETIC_REGISTRATION_FAILURE')
            patch.setattr(SourceOperations, '_event', staticmethod(fail_register))
        with pytest.raises(OSError, match='SYNTHETIC_'):
            advice.submit(handle, value['opinions']['A'])
    assert path.exists() == (fault == 'registration')
    assert not list(path.parent.glob('*.pending'))
    assert not events(value)
    code = 'ADVICE_REGISTERED_IDENTITY_MISMATCH' if path.exists() else 'DUAL_ADVICE_REQUIRED'
    with pytest.raises(BoundaryError, match=code):
        advice.read(packet, handle=handle)
    with pytest.raises(BoundaryError, match=code):
        seal(value)
    assert not rows(value, 'sealed_review_artifacts')
    if path.exists():
        conflict = copy.deepcopy(value['opinions']['A'])
        conflict['items'][0]['reason'] = 'Cannot replace an unregistered immutable file'
        with pytest.raises(BoundaryError, match='ARTIFACT_CONFLICT'):
            advice.submit(handle, conflict)
        assert not events(value)
    for slot in ('A', 'B'):
        advice.submit(handle, value['opinions'][slot])
        if slot == 'A':
            with pytest.raises(BoundaryError, match='DUAL_ADVICE_REQUIRED'):
                seal(value)
    assert len(events(value)) == 2
    assert set(advice.read(packet, handle=handle)) == {'A', 'B'}
    assert seal(value)['production_authorized'] is False
    assert value['config'].knowledge_db.read_bytes() == value['production']
