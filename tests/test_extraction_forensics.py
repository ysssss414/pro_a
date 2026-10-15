"""Synthetic evidence, zero network, no production recovery authorization."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from pro_a.workbench.extraction_forensics import inspect_accepted_run, project_claims
from pro_a.workbench.config import BoundaryError
from pro_a.source_metadata_authority import MetadataAuthorityError, validate_resolution
from test_candidate_origin import build, fixture
from test_bounded_only_resume import topology
from test_lossless_recovery import ConflictingMetadata
from series_binding_helpers import synthetic_providers


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))


def stopped(tmp_path, monkeypatch):
    value = topology(tmp_path, monkeypatch, counts=(17, 1), accepted_retry=False)
    transport = ConflictingMetadata()
    with synthetic_providers(value, transport) as providers:
        for _ in range(5):
            run = value['service'].advance_once(worker_id='synthetic-stop', processing_run_id=value['run_id'], provider=providers)
            if run['state'] == 'BLOCKED':
                break
    run = value['service'].get_run(value['run_id'])
    assert run['error']['code'] == 'SOURCE_METADATA_CONFLICT'
    assert len(transport.calls) == 2
    return value, {'expected_runtime_sha256': run['runtime_identity']['runtime_sha256'],
                   'expected_context_sha256': run['domain_context']['context_sha256']}


def test_wrong_semantics_and_pointer_are_never_admitted():
    values = fixture()
    values[0]['claims'][0]['statement'] = 'Unsupported synthetic assertion unrelated to evidence'
    doc = build(values)
    original = copy.deepcopy(doc)
    projected = project_claims([doc])
    assert projected['claims'] and all(r['semantic_status'] == 'UNCERTAIN' and
        r['production_admission'] == 'NOT_AUTHORIZED' for r in projected['claims'])
    assert doc == original


def test_duplicate_ids_rejected_and_independent_evidence_preserved():
    doc = build(fixture())
    with pytest.raises(BoundaryError, match='FORENSIC_DUPLICATE_OBSERVATION'):
        project_claims([doc, doc])
    second = copy.deepcopy(doc)
    for obj in second['objects']:
        obj['observation_id'] += '_SECOND'
        for e in obj['evidence']:
            e['evidence_pointer'] = '[[PAGE:999]]'
            e['source_locator'] = 'PAGE:1'
    result = project_claims([doc, second])
    assert len(result['claims']) == 2 * len(project_claims([doc])['claims'])
    assert any(e['pointer_locator_conflict'] for r in result['claims'] for e in r['evidence'])
    assert all(r['production_admission'] == 'NOT_AUTHORIZED' for r in result['claims'])


@pytest.mark.parametrize('damage', ['missing', 'errors'])
def test_incomplete_evidence_is_rejected(damage):
    doc = build(fixture())
    claim = next(o for o in doc['objects'] if o['family'] == 'claims')
    if damage == 'missing':
        claim['evidence'] = []
    else:
        claim['errors'] = ['INVALID_BINDING']
    with pytest.raises(BoundaryError, match='FORENSIC_INCOMPLETE_EVIDENCE'):
        project_claims([doc])


def test_rebuild_is_read_only_idempotent_and_concurrent(tmp_path, monkeypatch):
    value, expected = stopped(tmp_path, monkeypatch)
    cfg = value['config']
    before = cfg.state_db.read_bytes()
    def read():
        return inspect_accepted_run(cfg, value['run_id'], **expected)
    a = read()
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r == a for r in pool.map(lambda _: read(), range(2)))
    assert cfg.state_db.read_bytes() == before
    assert cfg.knowledge_db.read_bytes() == value['production_before']
    assert [b['status'] for b in a['batches']] == ['ACCEPTED_PRESERVED'] * 2 + ['NEVER_CALLED']
    assert a['status'] == 'SALVAGE_ONLY' and not a['resume_authorized']
    assert a['new_provider_calls'] == a['writes'] == 0
    with pytest.raises(MetadataAuthorityError, match='NEEDS_HUMAN_RESOLUTION'):
        validate_resolution(a['metadata_candidate'])


@pytest.mark.parametrize('field,code', [('expected_runtime_sha256','FORENSIC_RUNTIME_DRIFT'),
    ('expected_context_sha256','FORENSIC_CONTEXT_DRIFT')])
def test_drift_fails_closed(tmp_path, monkeypatch, field, code):
    value, expected = stopped(tmp_path, monkeypatch)
    expected[field] = '0' * 64
    with pytest.raises(BoundaryError, match=code):
        inspect_accepted_run(value['config'], value['run_id'], **expected)


def test_interruption_leaves_no_state_and_next_read_reconstructs(tmp_path, monkeypatch):
    value, expected = stopped(tmp_path, monkeypatch)
    cfg = value['config']; before = cfg.state_db.read_bytes()
    with monkeypatch.context() as interruption:
        interruption.setattr('pro_a.workbench.extraction_forensics.inspect_attempt',
                            lambda *a, **k: (_ for _ in ()).throw(InterruptedError('SYNTHETIC_STOP')))
        with pytest.raises(InterruptedError):
            inspect_accepted_run(cfg, value['run_id'], **expected)
    assert cfg.state_db.read_bytes() == before
    assert inspect_accepted_run(cfg, value['run_id'], **expected)['status'] == 'SALVAGE_ONLY'
    assert cfg.state_db.read_bytes() == before


def test_raw_tampering_is_rejected(tmp_path, monkeypatch):
    value, expected = stopped(tmp_path, monkeypatch)
    path = next(value['config'].artifact_root.glob('bounded-extraction/*/*.raw.json'))
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(BoundaryError, match='ARTIFACT_HASH_MISMATCH'):
        inspect_accepted_run(value['config'], value['run_id'], **expected)


def test_runtime_body_cannot_reuse_a_valid_recorded_digest(tmp_path, monkeypatch):
    from pro_a.workbench.candidate_inputs import CandidateArchive
    value, expected = stopped(tmp_path, monkeypatch)
    original = CandidateArchive.get_run
    def tampered(archive, run_id):
        run = original(archive, run_id)
        run['runtime_identity']['git_sha'] = 'untrusted-body-with-retained-digest'
        return run
    monkeypatch.setattr(CandidateArchive, 'get_run', tampered)
    with pytest.raises(BoundaryError, match='FORENSIC_RUNTIME_CONTEXT_MISMATCH'):
        inspect_accepted_run(value['config'], value['run_id'], **expected)
