"""One explicit pre-Semantic replacement; synthetic state and provider stubs only."""
import hashlib
import json
from dataclasses import replace

import pytest

from pro_a.workbench.candidate_inputs import CandidateInputs
from pro_a.workbench.source_operations import SourceOperationError
from series_binding_helpers import case, clean_pdf, rows, synthetic_providers, text, Transport, upload


REASON = 'Confirmed local hostname guard failure; outbound-only guard validated.'
KEY = 'candidate-replacement-synthetic-0001'


class Partial(Transport):
    def __call__(self, *args, **kwargs):
        response = super().__call__(*args, **kwargs)
        function = response.value['choices'][0]['message']['tool_calls'][0]['function']
        record = json.loads(function['arguments'])
        del record['claims'][-1]['nature']
        function['arguments'] = json.dumps(record)
        return response


def make_case(tmp_path, monkeypatch, *, block=True):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('EXTERNAL_NETWORK'))
    value = case(tmp_path)
    from pro_a.admission_schema import migrate
    from pro_a.production_promotion import sha256_file
    migrate(value['config'].knowledge_db, expected_sha256=sha256_file(value['config'].knowledge_db),
            backup_path=tmp_path / 'synthetic-backup.db', configured_production_path=value['config'].knowledge_db)
    source = upload(value, clean_pdf(tmp_path, text=text(3)))
    service = value['service']
    original = service.start(source['source_id'], idempotency_key='replacement-original-synthetic-0001')['run']
    original_id = original['processing_run_id']
    service.advance_once(worker_id='synthetic', processing_run_id=original_id)
    with synthetic_providers(value, Partial()) as provider:
        original = service.advance_once(worker_id='synthetic', processing_run_id=original_id, provider=provider)
        assert provider['SEMANTIC_DECOMPOSITION'].call_count == 0
    assert original['coverage_status'] == 'FAILED' and original['accepted_leaf_calls'] == 0
    attempt = rows(value, 'bounded_extraction_attempts')[0]['attempt_id']
    reference = CandidateInputs(service).publish(original_id, attempt)
    child = service.start_candidates([reference], idempotency_key='replacement-child-synthetic-0001')['run']
    child_id = child['processing_run_id']
    service.advance_once(worker_id='synthetic', processing_run_id=child_id)
    if block:
        def local_guard_failure(*args, **kwargs):
            raise RuntimeError('NETWORK_FORBIDDEN_DURING_INPUT_FREEZE')
        with monkeypatch.context() as patch:
            patch.setattr('pro_a.operational_ingestion._clean_pdf_parse', local_guard_failure)
            child = service.advance_once(worker_id='synthetic', processing_run_id=child_id)
        assert child['state'] == 'BLOCKED' and child['jobs'] == []
    else:
        child = service.advance_once(worker_id='synthetic', processing_run_id=child_id)
        assert child['state'] == 'SEMANTIC_PROCESSING'
    value.update(original_id=original_id, child_id=child_id, reference=reference, child=child, source=source)
    return value


@pytest.fixture
def blocked(tmp_path, monkeypatch):
    return make_case(tmp_path, monkeypatch)


def replacement(value, **overrides):
    request = dict(idempotency_key=KEY, reason=REASON, confirm_local_failure=True)
    request.update(overrides)
    return value['service'].replace_candidates(value['child_id'], **request)


def native_root(value):
    service = value['service']
    with service.store.connect() as connection:
        row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?',
                                 (value['child_id'],)).fetchone()
    return service._native_root(row)


def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def history(value):
    run_ids = {value['original_id'], value['child_id']}
    return {table: [r for r in rows(value, table) if r['processing_run_id'] in run_ids]
            for table in ('source_processing_runs', 'source_processing_events', 'domain_run_bindings')}


def test_replacement_preserves_history_replays_and_reaches_registered_packet(blocked):
    value, service = blocked, blocked['service']
    before_history = history(value)
    before_files = inventory(value['config'].artifact_root)
    before_native = inventory(native_root(value))
    production = value['config'].knowledge_db.read_bytes()
    before_attempts = rows(value, 'bounded_extraction_attempts')
    duplicate = service.start_candidates([value['reference']], idempotency_key='replacement-different-key-0001')
    assert duplicate['duplicate'] and duplicate['run']['processing_run_id'] == value['child_id']
    assert len(rows(value, 'source_processing_runs')) == 2
    started = replacement(value)
    child = started['run']
    new_id = child['processing_run_id']
    assert not started['duplicate'] and new_id != value['child_id']
    assert child['candidate_origin'] == value['child']['candidate_origin']
    assert child['candidate_replacement'] == {'previous_run_id': value['child_id'], 'reason': REASON,
        'failure_kind': 'LOCAL_EXECUTION_GUARD_GETHOSTNAME_BLOCKED'}
    assert replacement(value)['run']['processing_run_id'] == new_id
    service.advance_once(worker_id='synthetic', processing_run_id=new_id)
    child = service.advance_once(worker_id='synthetic', processing_run_id=new_id)
    assert child['state'] == 'SEMANTIC_PROCESSING' and len(child['jobs']) == 1
    with service.store.connect() as connection:
        new_row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (new_id,)).fetchone()
    manifest = json.loads((service._native_root(new_row) / 'execution_manifest.json').read_text())
    assert manifest['state'] == 'SEMANTIC_INPUT_READY'
    with synthetic_providers(value) as provider:
        child = service.advance_once(worker_id='synthetic', processing_run_id=new_id, provider=provider)
        assert provider['SEMANTIC_DECOMPOSITION'].call_count == 1
        assert provider['WHOLE_PIECE_OUTPUT_BATCH'].transport.calls == []
    assert child['state'] == 'HUMAN_REVIEW_REQUIRED' and child['packet_id'] and child['packet_artifact_id']
    from pro_a.workbench.review_workbench import ReviewWorkbench
    review = ReviewWorkbench(value['config']).read(child['packet_artifact_id'])
    assert review['review']['status'] != 'SEALED'
    from pro_a.mcp.service import ReadService
    assert ReadService(value['config']).get_review_context(child['packet_artifact_id'])
    assert replacement(value)['run']['processing_run_id'] == new_id
    with pytest.raises(SourceOperationError, match='CANDIDATE_REPLACEMENT_LIMIT_REACHED'):
        replacement(value, idempotency_key='replacement-another-request-0001')
    with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'):
        replacement(value, reason=REASON + ' Changed reason.')
    assert history(value) == before_history
    assert inventory(native_root(value)) == before_native
    after_files = inventory(value['config'].artifact_root)
    assert all(after_files[k] == v for k, v in before_files.items())
    assert rows(value, 'bounded_extraction_attempts') == before_attempts
    assert value['config'].knowledge_db.read_bytes() == production
    assert len(rows(value, 'source_processing_runs')) == 3
    assert not rows(value, 'sealed_review_artifacts')


@pytest.mark.parametrize('reason,confirm', [('', True), ('   ', True), (REASON, False), (REASON, 1)])
def test_explicit_confirmation_and_reason_required(blocked, reason, confirm):
    with pytest.raises(SourceOperationError, match='CONFIRMATION_REQUIRED'):
        replacement(blocked, reason=reason, confirm_local_failure=confirm)
    assert len(rows(blocked, 'source_processing_runs')) == 2


@pytest.mark.parametrize('changes,code', [
    ({'state': 'RECOVERY_REQUIRED'}, 'FAILURE_NOT_ELIGIBLE'),
    ({'state': 'QUEUED'}, 'FAILURE_NOT_ELIGIBLE'),
    ({'ended_at': None}, 'FAILURE_NOT_ELIGIBLE'),
    ({'manual_recovery_required': 1}, 'FAILURE_NOT_ELIGIBLE'),
    ({'error_code': 'EVIDENCE_FAILURE'}, 'FAILURE_NOT_ELIGIBLE'),
    ({'packet_id': 'SYNTHETIC_PACKET'}, 'PACKET_EXISTS'),
    ({'packet_artifact_id': 'SYNTHETIC_SEALED_PACKET'}, 'PACKET_EXISTS'),
])
def test_ineligible_failure_and_packet_rejected(blocked, changes, code):
    with blocked['service'].store.connect(operator_write=True) as connection:
        connection.execute('UPDATE source_processing_runs SET ' + ','.join(k + '=?' for k in changes)
                           + ' WHERE processing_run_id=?', (*changes.values(), blocked['child_id']))
    with pytest.raises(SourceOperationError, match=code):
        replacement(blocked)
    assert len(rows(blocked, 'source_processing_runs')) == 2


@pytest.mark.parametrize('fault', ['source', 'raw', 'origin', 'native', 'side_effect', 'context'])
def test_identity_drift_and_unreconciled_side_effects_rejected(blocked, fault):
    service = blocked['service']
    if fault == 'source':
        source = rows(blocked, 'private_sources')[0]
        path = service.artifacts.resolve(source['storage_relative'])
        path.chmod(0o600)
        path.write_bytes(b'corrupted synthetic source')
    elif fault == 'raw':
        attempt = rows(blocked, 'bounded_extraction_attempts')[0]['attempt_id']
        path = next(blocked['config'].artifact_root.rglob(attempt + '.raw.json'))
        path.chmod(0o600)
        path.write_bytes(b'corrupted synthetic raw')
    elif fault == 'origin':
        path = service.artifacts.resolve(blocked['reference']['artifact_relative'])
        path.chmod(0o600)
        document = json.loads(path.read_text())
        document['identity'] = 'f' * 64
        path.write_text(json.dumps(document))
    elif fault == 'native':
        (native_root(blocked) / 'execution_manifest.json').write_text('{}')
    elif fault == 'side_effect':
        (native_root(blocked) / 'unreconciled-result.json').write_text('{}')
    else:
        service.jobs.profile = replace(service.jobs.profile, max_calls=service.jobs.profile.max_calls + 1)
    with pytest.raises((SourceOperationError, ValueError, RuntimeError)):
        replacement(blocked)
    assert len(rows(blocked, 'source_processing_runs')) == 2


def test_replacement_never_bypasses_ordinary_run_limit(blocked, tmp_path):
    source = upload(blocked, clean_pdf(tmp_path, 'different-synthetic.pdf', text='Another synthetic source.'))
    blocked['service'].start(source['source_id'], idempotency_key='replacement-capacity-third-0001')
    with pytest.raises(SourceOperationError, match='STAGE1_RUN_WINDOW_LIMIT'):
        replacement(blocked)
    assert len(rows(blocked, 'source_processing_runs')) == 3
    assert history(blocked)['source_processing_runs'][1]['state'] == 'BLOCKED'


def test_replacement_of_a_replacement_cannot_restart_the_chain(blocked, monkeypatch):
    service = blocked['service']
    new_id = replacement(blocked)['run']['processing_run_id']
    service.advance_once(worker_id='synthetic', processing_run_id=new_id)
    def fail(*args, **kwargs):
        raise RuntimeError('NETWORK_FORBIDDEN_DURING_INPUT_FREEZE')
    monkeypatch.setattr('pro_a.operational_ingestion._clean_pdf_parse', fail)
    new_run = service.advance_once(worker_id='synthetic', processing_run_id=new_id)
    assert new_run['state'] == 'BLOCKED' and not new_run['jobs']
    with pytest.raises(SourceOperationError, match='CANDIDATE_REPLACEMENT_LIMIT_REACHED'):
        service.replace_candidates(new_id, idempotency_key='replacement-chain-forbidden-0001',
                                   reason=REASON, confirm_local_failure=True)
    assert len(rows(blocked, 'source_processing_runs')) == 3


def test_concurrent_requests_cannot_create_two_replacements(blocked):
    from concurrent.futures import ThreadPoolExecutor
    def request(key):
        try:
            return replacement(blocked, idempotency_key=key)['run']['processing_run_id']
        except SourceOperationError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, ['replacement-concurrent-key-0001', 'replacement-concurrent-key-0002']))
    assert results.count('CANDIDATE_REPLACEMENT_LIMIT_REACHED') == 1
    assert len(rows(blocked, 'source_processing_runs')) == 3


def test_release_runtime_change_does_not_change_frozen_processing_context(blocked):
    from pro_a.production_promotion import canonical_sha256
    service = blocked['service']
    runtime = service.jobs.current_runtime()
    runtime['git_sha'] = 'f' * 40
    runtime['runtime_sha256'] = canonical_sha256({k: v for k, v in runtime.items() if k != 'runtime_sha256'})
    service.jobs._runtime_override = runtime
    result = replacement(blocked)
    assert result['run']['runtime_identity']['git_sha'] == 'f' * 40
    assert result['run']['candidate_origin'] == blocked['child']['candidate_origin']


@pytest.mark.parametrize('scenario', ['success', 'unknown_external_outcome'])
def test_actual_stub_semantic_dispatch_or_unknown_outcome_not_replaceable(tmp_path, monkeypatch, scenario):
    value = make_case(tmp_path, monkeypatch, block=False)
    from pro_a.cloud_contract import DeterministicFakeProvider
    stub = DeterministicFakeProvider(scenario)
    child = value['service'].advance_once(worker_id='synthetic', processing_run_id=value['child_id'], provider=stub)
    assert stub.call_count == 1
    assert child['state'] == ('HUMAN_REVIEW_REQUIRED' if scenario == 'success' else 'RECOVERY_REQUIRED')
    with pytest.raises(SourceOperationError, match='FAILURE_NOT_ELIGIBLE'):
        replacement(value)
    assert len(rows(value, 'source_processing_runs')) == 2


def test_api_requires_authenticated_explicit_replacement_and_replays(blocked, monkeypatch):
    from fastapi.testclient import TestClient
    from pro_a.workbench.api import create_app, PREFIX
    token = 'synthetic-replacement-browser-token-tests-only'
    monkeypatch.setenv(blocked['config'].session_token_env, token)
    client = TestClient(create_app(blocked['config'], cloud_profile=blocked['cloud_profile'],
        source_profile=blocked['source_profile']), base_url=blocked['config'].origin, client=('127.0.0.1', 1))
    endpoint = PREFIX + '/source-operations/runs/' + blocked['child_id'] + '/candidate-replacement'
    body = {'idempotency_key': KEY, 'reason': REASON, 'confirm_local_failure': True}
    assert client.post(endpoint, json=body).status_code == 403
    session = client.post(PREFIX + '/session', headers={'Origin': blocked['config'].origin}, json={'token': token}).json()
    headers = {'Origin': blocked['config'].origin, 'X-CSRF-Token': session['csrf_token']}
    assert client.post(endpoint, headers={'Origin': blocked['config'].origin}, json=body).status_code == 403
    assert client.post(endpoint, headers=headers, json={k: v for k, v in body.items() if k != 'reason'}).status_code == 422
    assert client.post(endpoint, headers=headers, json={**body, 'references': [blocked['reference']]}).status_code == 422
    assert client.post(endpoint, headers=headers, json={**body, 'confirm_local_failure': False}).status_code == 422
    first = client.post(endpoint, headers=headers, json=body)
    assert first.status_code == 200, first.text
    again = client.post(endpoint, headers=headers, json=body)
    assert again.status_code == 200 and again.json()['duplicate']
    assert first.json()['run']['processing_run_id'] == again.json()['run']['processing_run_id']
    assert len(rows(blocked, 'source_processing_runs')) == 3
