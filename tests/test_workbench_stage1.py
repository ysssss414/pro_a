from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

from fastapi.testclient import TestClient
import pytest

from pro_a.phase3f_review_completion import validate_completed_review_packet
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.artifacts import Artifacts, digest
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.review_workbench import ReviewError, ReviewWorkbench
from pro_a.workbench.store import Store
from workbench_fixture import CLAIM, NODE, make_fixture

PARENT = 'PARENT_PLACEMENT_SYNTHETIC_STAGE0'
REVIEWER = 'Synthetic Human Reviewer'
IDENTITY = {'actor': 'operator', 'session_id': 'synthetic-session-one'}
TOKEN = 'synthetic-session-secret-for-stage1-tests-only'


@pytest.fixture
def case(tmp_path, monkeypatch):
    value = make_fixture(tmp_path, node_profile='create')
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', TOKEN)
    Store(value['config']).initialize()
    value['handle'] = Artifacts(value['config']).register(value['packet_relative'], value['run_relative'])['artifact_id']
    value['state_before_migration'] = digest(value['config'].state_db)
    prepare_reviews(value['config'])
    value['service'] = ReviewWorkbench(value['config'])
    return value


def operation(case, **extra):
    review = case['service'].read(case['handle'])['review']
    return {'basis_id': review['basis_id'], 'expected_revision': review['revision'], 'operation_id': uuid.uuid4().hex,
            'reviewer': REVIEWER, 'reason': 'Explicit synthetic human reason.', **extra}


def decide(case, candidate_id=CLAIM, decision='KEEP', **extra):
    request = operation(case, candidate_id=candidate_id, decision=decision, target_node_id='', **extra)
    return case['service'].mutate(case['handle'], 'decision', request, IDENTITY)


def complete(case, claim='KEEP_NEEDS_REVIEW'):
    decide(case, CLAIM, claim)
    decide(case, NODE, 'CREATE')
    decide(case, PARENT, 'CREATE')


def test_migration_is_explicit_preserves_registry_and_backs_up(case):
    path = case['config'].state_db
    assert digest(path.with_name(path.name + '.stage0-backup')) == case['state_before_migration']
    assert prepare_reviews(case['config'])['status'] == 'ALREADY_PREPARED'
    assert Artifacts(case['config']).read(case['handle'])['packet_id'] == case['packet']['packet_id']


def test_no_advisory_prefill_and_deterministic_queues(case):
    review = case['service'].read(case['handle'])['review']
    assert review['revision'] == 0 and not review['audit'] and review['reviewer'] == ''
    assert review['progress'] == {'total_native_rows': 3, 'required': 3, 'completed': 0, 'remaining': 3, 'excluded': 1,
        'deferred': 0, 'nonpromotable': 0, 'warnings': 0, 'invalid': 0, 'dependency_blocked': 1}
    assert all(row['state'] is None and 'needs_review' in row['queues'] for row in review['rows'])
    assert review['rows'][1]['available_decisions'] == ['CREATE', 'DEFER', 'REJECT']
    assert review['rows'][2]['available_decisions'] == ['DEFER', 'REJECT']


@pytest.mark.parametrize('decision', ['KEEP', 'DROP', 'KEEP_NEEDS_REVIEW'])
def test_claim_decisions_are_explicit_native_and_durable(case, decision):
    decide(case, decision=decision)
    restored = ReviewWorkbench(case['config']).read(case['handle'])['review']
    state = restored['rows'][0]['state']
    assert state['decision'] == decision and state['reviewer'] == REVIEWER
    assert state['reason'] == 'Explicit synthetic human reason.' and state['session_id'] == IDENTITY['session_id']
    assert restored['revision'] == 1 and len(restored['audit']) == 1
    if decision == 'KEEP_NEEDS_REVIEW':
        assert restored['rows'][0]['nonpromotable'] and restored['rows'][0]['decision_effect'] == 'DEFERRED_NON_PROMOTABLE'


@pytest.mark.parametrize('decision', ['CREATE', 'DEFER', 'REJECT'])
def test_node_decisions(case, decision):
    decide(case, NODE, decision)
    assert case['service'].read(case['handle'])['review']['rows'][1]['state']['decision'] == decision


def test_exact_reuse_and_collision_capabilities(tmp_path):
    case = make_fixture(tmp_path, node_profile='reuse')
    Store(case['config']).initialize()
    case['handle'] = Artifacts(case['config']).register(case['packet_relative'], case['run_relative'])['artifact_id']
    prepare_reviews(case['config'])
    case['service'] = ReviewWorkbench(case['config'])
    node = case['service'].read(case['handle'])['review']['rows'][1]
    assert node['available_decisions'] == ['REUSE', 'DEFER', 'REJECT']
    for target in ('', 'NODE_SYNTHETIC_WRONG'):
        request = operation(case, candidate_id=NODE, decision='REUSE', target_node_id=target)
        with pytest.raises(ReviewError, match='VALIDATION_ERROR'):
            case['service'].mutate(case['handle'], 'decision', request, IDENTITY)
    request = operation(case, candidate_id=NODE, decision='REUSE', target_node_id='NODE_SYNTHETIC_EXISTING')
    case['service'].mutate(case['handle'], 'decision', request, IDENTITY)
    decide(case, PARENT, 'DEFER')
    decide(case, CLAIM, 'KEEP')
    review = case['service'].read(case['handle'])['review']
    assert case['service'].validate_completion(case['handle'], review['revision'], review['basis_id'])['validation']['status'] == 'HUMAN_REVIEW_COMPLETE_AND_VALID'


@pytest.mark.parametrize('decision', ['CREATE', 'DEFER', 'REJECT'])
def test_parent_decisions(case, decision):
    if decision == 'CREATE': decide(case, NODE, 'CREATE')
    decide(case, PARENT, decision)
    assert case['service'].read(case['handle'])['review']['rows'][2]['state']['decision'] == decision


@pytest.mark.parametrize('candidate_id', ['REL_SYNTHETIC_EXCLUDED', 'ALIAS_SYNTHETIC', 'UNKNOWN'])
def test_non_reviewable_item_rejected(case, candidate_id):
    with pytest.raises(ReviewError, match='NOT_REVIEWABLE'):
        decide(case, candidate_id, 'ACCEPT')
    assert case['service'].read(case['handle'])['review']['revision'] == 0


def test_concurrent_revision_and_idempotency(case):
    first = operation(case, candidate_id=CLAIM, decision='KEEP', target_node_id='')
    second = {**first, 'operation_id': uuid.uuid4().hex, 'decision': 'DROP'}
    def submit(request):
        try: return case['service'].mutate(case['handle'], 'decision', request, IDENTITY)
        except ReviewError as error: return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, (first, second)))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 'REVISION_CONFLICT' in results
    winner = first if isinstance(results[0], dict) else second
    replay = case['service'].mutate(case['handle'], 'decision', winner, {**IDENTITY, 'session_id': 'restarted-session'})
    assert replay == next(result for result in results if isinstance(result, dict))
    assert len(case['service'].read(case['handle'])['review']['audit']) == 1
    with pytest.raises(ReviewError, match='IDEMPOTENCY_CONFLICT'):
        case['service'].mutate(case['handle'], 'decision', {**winner, 'reason': 'A different request.'}, IDENTITY)


def test_undo_restores_state_and_appends_history(case):
    decide(case, decision='KEEP')
    decide(case, decision='DROP')
    review = case['service'].read(case['handle'])['review']
    request = operation(case, candidate_id=CLAIM, event_id=review['rows'][0]['undo_event_id'], reason='Undo the most recent explicit change.')
    case['service'].mutate(case['handle'], 'undo', request, IDENTITY)
    result = case['service'].read(case['handle'])['review']
    assert result['rows'][0]['state']['decision'] == 'KEEP'
    assert [event['event_type'] for event in result['audit']] == ['SAVE', 'SAVE', 'UNDO']
    assert result['rows'][0]['undo_event_id'] is None
    assert result['audit'][:2] == review['audit']


def test_dependency_invalidation_is_immediate_atomic_and_audited(case):
    with pytest.raises(ReviewError, match='DEPENDENCY_INVALID'):
        decide(case, PARENT, 'CREATE')
    decide(case, NODE, 'CREATE')
    decide(case, PARENT, 'CREATE')
    assert 'DEFER' in case['service'].read(case['handle'])['review']['rows'][1]['available_decisions']
    result = decide(case, NODE, 'DEFER')
    assert result['invalidated_items'] == [PARENT]
    review = case['service'].read(case['handle'])['review']
    assert review['rows'][2]['state'] is None and review['progress']['remaining'] == 2
    assert review['audit'][-1]['event_type'] == 'DEPENDENCY_INVALIDATED'
    assert review['audit'][-1]['revision'] == review['audit'][-2]['revision']
    with pytest.raises(ReviewError, match='DEPENDENCY_INVALID'):
        decide(case, PARENT, 'CREATE')
    assert review == case['service'].read(case['handle'])['review']


def test_completion_and_seal_are_native_separate_atomic_and_immutable(case):
    registry = Artifacts(case['config'])
    before = registry.inventory(case['packet_relative'], case['run_relative'])
    knowledge_before = digest(case['config'].knowledge_db)
    review = case['service'].read(case['handle'])['review']
    with pytest.raises(ReviewError, match='VALIDATION_ERROR'):
        case['service'].validate_completion(case['handle'], review['revision'], review['basis_id'])
    complete(case)
    review = case['service'].read(case['handle'])['review']
    validated = case['service'].validate_completion(case['handle'], review['revision'], review['basis_id'])
    assert validated['validation']['total_operational_decisions_validated'] == 3
    request = operation(case, confirm=True, reason='Explicitly confirm review-only sealing.')
    receipt = case['service'].mutate(case['handle'], 'seal', request, IDENTITY)
    assert len(receipt['objects']) == 2 and not receipt['production_authorized']
    restored = ReviewWorkbench(case['config']).read(case['handle'])
    assert restored['review']['status'] == 'SEALED' and restored['capabilities']['read_only']
    assert restored['review']['progress']['nonpromotable'] == 1
    assert case['service'].mutate(case['handle'], 'seal', request, IDENTITY) == receipt
    with Store(case['config']).connect() as connection:
        completed = json.loads(connection.execute("SELECT body FROM sealed_review_artifacts WHERE kind='completed_packet'").fetchone()[0])
    assert validate_completed_review_packet(completed, case['config'].artifact_root / case['run_relative']) == validated['validation']
    assert completed['claims'][0]['human_input']['decision'] == 'KEEP_NEEDS_REVIEW'
    assert registry.inventory(case['packet_relative'], case['run_relative']) == before
    assert digest(case['config'].knowledge_db) == knowledge_before
    with pytest.raises(ReviewError, match='ALREADY_SEALED'):
        decide(case, decision='DROP')
    with Store(case['config']).connect(operator_write=True) as connection:
        for table in ('sealed_review_artifacts', 'review_audit', 'review_operations'):
            with pytest.raises(sqlite3.IntegrityError, match='APPEND_ONLY'):
                connection.execute(f'DELETE FROM {table}')


@pytest.mark.parametrize('table', ['review_decisions', 'review_audit'])
def test_decision_and_audit_failures_roll_back_together(case, table):
    with Store(case['config']).connect(operator_write=True) as connection:
        connection.execute(f"CREATE TRIGGER injected_failure BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'INJECTED_FAILURE'); END")
    with pytest.raises(sqlite3.IntegrityError, match='INJECTED_FAILURE'):
        decide(case)
    restored = ReviewWorkbench(case['config']).read(case['handle'])['review']
    assert restored['revision'] == 0 and restored['progress']['completed'] == 0 and not restored['audit']


@pytest.mark.parametrize('kind', ['completed_packet', 'completion_receipt'])
def test_artifact_publication_failures_are_atomic(case, kind):
    complete(case)
    before = case['service'].read(case['handle'])['review']
    with Store(case['config']).connect(operator_write=True) as connection:
        connection.execute(f"CREATE TRIGGER injected_failure BEFORE INSERT ON sealed_review_artifacts WHEN NEW.kind='{kind}' BEGIN SELECT RAISE(ABORT,'INJECTED_FAILURE'); END")
    with pytest.raises(sqlite3.IntegrityError, match='INJECTED_FAILURE'):
        case['service'].mutate(case['handle'], 'seal', operation(case, confirm=True), IDENTITY)
    assert ReviewWorkbench(case['config']).read(case['handle'])['review'] == before
    with Store(case['config']).connect() as connection:
        assert connection.execute('SELECT count(*) FROM sealed_review_artifacts').fetchone()[0] == 0


def test_ambiguous_persisted_state_requires_recovery(case):
    complete(case)
    case['service'].mutate(case['handle'], 'seal', operation(case, confirm=True), IDENTITY)
    with Store(case['config']).connect(operator_write=True) as connection:
        connection.execute('DROP TRIGGER sealed_review_artifacts_delete_forbidden')
        connection.execute("DELETE FROM sealed_review_artifacts WHERE kind='completion_receipt'")
    with pytest.raises(ReviewError, match='RECOVERY_REQUIRED'):
        case['service'].read(case['handle'])


def test_stage0_boundary_and_mutation_authentication(case):
    config = replace(case['config'], origin='https://research.invalid', remote=True)
    client = TestClient(create_app(config), base_url=config.origin, client=('203.0.113.6', 50000))
    route = PREFIX + '/reviews/' + case['handle']
    body = operation(case, candidate_id=CLAIM, decision='KEEP', target_node_id='')
    assert client.post(route + '/decisions', json=body, headers={'Origin': config.origin}).status_code == 401
    session = client.post(PREFIX + '/session', json={'token': TOKEN}, headers={'Origin': config.origin}).json()
    assert client.post(route + '/decisions', json=body, headers={'Origin': config.origin}).status_code == 403
    headers = {'Origin': config.origin, 'X-CSRF-Token': session['csrf_token']}
    assert client.post(route + '/decisions', json=body, headers=headers).status_code == 200
    assert client.post(route + '/decisions', json=body, headers=headers).status_code == 200
    stale = {**body, 'operation_id': uuid.uuid4().hex, 'decision': 'DROP'}
    conflict = client.post(route + '/decisions', json=stale, headers=headers)
    assert conflict.status_code == 409 and conflict.json()['detail'] == 'REVISION_CONFLICT'
    invalid = client.post(route + '/decisions', json={**body, 'content': {'filename': 'private.pdf'}}, headers=headers)
    assert invalid.status_code == 422 and invalid.json()['detail'] == 'IMMUTABLE_FIELD_DRIFT'
    assert 'private.pdf' not in invalid.text
    assert client.get('/api/stats').status_code == 200


def test_frozen_input_drift_is_rejected(case):
    request = operation(case, candidate_id=CLAIM, decision='KEEP', target_node_id='')
    packet = case['config'].artifact_root / case['packet_relative']
    packet.write_bytes(packet.read_bytes() + b' ')
    with pytest.raises(ReviewError, match='IMMUTABLE_FIELD_DRIFT'):
        case['service'].mutate(case['handle'], 'decision', request, IDENTITY)


@pytest.mark.parametrize('kind', ['completed_packet', 'completion_receipt'])
def test_process_crash_recovers_atomic_publication_and_can_retry(case, tmp_path, kind):
    complete(case)
    before = case['service'].read(case['handle'])['review']
    request = operation(case, confirm=True)
    config = {key: str(value) if isinstance(value, Path) else value for key,value in asdict(case['config']).items()}
    payload = tmp_path / 'crash-request.json'
    payload.write_text(json.dumps({'config': config, 'handle': case['handle'], 'request': request, 'identity': IDENTITY, 'crash_after': kind}))
    environment = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('workbench_crash_worker.py')), str(payload)], env=environment, capture_output=True, timeout=30)
    assert result.returncode == 73, result.stderr.decode(errors='replace')
    create_app(case['config'])  # Native SQLite hot-journal recovery, on Workbench only.
    service = ReviewWorkbench(case['config'])
    assert service.read(case['handle'])['review'] == before
    service.mutate(case['handle'], 'seal', request, IDENTITY)
    assert service.read(case['handle'])['review']['status'] == 'SEALED'


def test_concurrent_duplicate_posts_have_one_audit_event(case):
    request = operation(case, candidate_id=CLAIM, decision='KEEP', target_node_id='')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ReviewWorkbench(case['config']).mutate(case['handle'], 'decision', request, IDENTITY), range(2)))
    assert results[0] == results[1]
    assert len(case['service'].read(case['handle'])['review']['audit']) == 1


def test_undo_node_invalidates_parent_and_sealed_undo_is_forbidden(case):
    decide(case, NODE, 'CREATE')
    decide(case, PARENT, 'CREATE')
    review = case['service'].read(case['handle'])['review']
    request = operation(case, candidate_id=NODE, event_id=review['rows'][1]['undo_event_id'])
    response = case['service'].mutate(case['handle'], 'undo', request, IDENTITY)
    assert response['invalidated_items'] == [PARENT]
    restored = case['service'].read(case['handle'])['review']
    assert restored['rows'][1]['state'] is None and restored['rows'][2]['state'] is None
    complete(case)
    case['service'].mutate(case['handle'], 'seal', operation(case, confirm=True), IDENTITY)
    with pytest.raises(ReviewError, match='ALREADY_SEALED'):
        case['service'].mutate(case['handle'], 'undo', operation(case, candidate_id=NODE, event_id=1), IDENTITY)


@pytest.mark.parametrize('field,value', [('reason', ''), ('reason', ' padded '), ('reviewer', ''), ('reviewer', ' padded ')])
def test_invalid_human_text_never_persists(case, field, value):
    with pytest.raises(ReviewError, match='VALIDATION_ERROR'):
        request = operation(case, candidate_id=CLAIM, decision='KEEP', target_node_id='', **{field: value})
        case['service'].mutate(case['handle'], 'decision', request, IDENTITY)
    assert case['service'].read(case['handle'])['review']['revision'] == 0


def test_seal_requires_exact_completion_and_explicit_confirmation(case):
    with pytest.raises(ReviewError, match='SEAL_CONFIRMATION_REQUIRED'):
        case['service'].mutate(case['handle'], 'seal', operation(case, confirm=False), IDENTITY)
    with pytest.raises(ReviewError, match='VALIDATION_ERROR'):
        case['service'].mutate(case['handle'], 'seal', operation(case, confirm=True), IDENTITY)
    assert case['service'].read(case['handle'])['review']['revision'] == 0


def test_dependency_audit_failure_rolls_back_every_affected_row(case):
    complete(case)
    before = case['service'].read(case['handle'])['review']
    with Store(case['config']).connect(operator_write=True) as connection:
        connection.execute("CREATE TRIGGER injected_failure BEFORE INSERT ON review_audit WHEN NEW.event_type='DEPENDENCY_INVALIDATED' BEGIN SELECT RAISE(ABORT,'INJECTED_FAILURE'); END")
    with pytest.raises(sqlite3.IntegrityError, match='INJECTED_FAILURE'):
        decide(case, NODE, 'DEFER')
    assert case['service'].read(case['handle'])['review'] == before


def test_audit_and_state_divergence_requires_recovery(case):
    decide(case)
    with Store(case['config']).connect(operator_write=True) as connection:
        state = json.loads(connection.execute('SELECT state_json FROM review_decisions').fetchone()[0])
        state['decision'] = 'DROP'
        connection.execute('UPDATE review_decisions SET state_json=?', (json.dumps(state),))
    with pytest.raises(ReviewError, match='RECOVERY_REQUIRED'):
        case['service'].read(case['handle'])


def test_all_web_writes_are_workbench_only_and_no_executor_or_model_is_used(case, monkeypatch):
    from pro_a.db import Database
    import pro_a.production_execution as execution
    import pro_a.semantic_decomposition as semantic
    import pro_a.llm as llm
    def forbidden(*args, **kwargs): pytest.fail('Forbidden Production/model/init path')
    monkeypatch.setattr(Database, 'init_schema', forbidden)
    monkeypatch.setattr(execution, 'execute_authorized_production', forbidden)
    monkeypatch.setattr(execution, 'execute_foundation_payload', forbidden)
    monkeypatch.setattr(semantic.ChatLLMSemanticBackend, '__init__', forbidden)
    monkeypatch.setattr(llm.ChatLLM, '__init__', forbidden)
    original = sqlite3.connect
    opened = []
    def track(database, *args, **kwargs):
        assert kwargs.get('uri') is True
        text = str(database)
        opened.append(text)
        assert text.startswith('file:')
        if '?mode=rw' in text:
            assert text == case['config'].state_db.resolve().as_uri() + '?mode=rw'
        else:
            assert '?mode=ro' in text
        return original(database, *args, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', track)
    client = TestClient(create_app(case['config']), base_url=case['config'].origin, client=('127.0.0.1', 1))
    session = client.post(PREFIX + '/session', headers={'Origin': case['config'].origin}, json={'token': TOKEN}).json()
    headers = {'Origin': case['config'].origin, 'X-CSRF-Token': session['csrf_token']}
    route = PREFIX + '/reviews/' + case['handle']
    for candidate, decision in ((CLAIM, 'KEEP_NEEDS_REVIEW'), (NODE, 'CREATE'), (PARENT, 'CREATE')):
        body = operation(case, candidate_id=candidate, decision=decision, target_node_id='')
        assert client.post(route + '/decisions', headers=headers, json=body).status_code == 200
    assert client.post(route + '/seal', headers=headers, json=operation(case, confirm=True)).status_code == 200
    assert client.get(route + '/sealed').status_code == 200
    assert client.get('/api/stats').status_code == 200
    assert any('?mode=rw' in uri for uri in opened)


def test_review_write_surface_requires_explicit_migration(tmp_path, monkeypatch):
    fixture = make_fixture(tmp_path)
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', TOKEN)
    Store(fixture['config']).initialize()
    handle = Artifacts(fixture['config']).register(fixture['packet_relative'], fixture['run_relative'])['artifact_id']
    client = TestClient(create_app(fixture['config']), base_url=fixture['config'].origin, client=('127.0.0.1', 1))
    session = client.post(PREFIX + '/session', headers={'Origin': fixture['config'].origin}, json={'token': TOKEN}).json()
    assert ReviewWorkbench(fixture['config']).read(handle)['review'] == {'enabled': False}
    response = client.post(PREFIX + '/reviews/' + handle + '/validate', headers={'Origin': fixture['config'].origin, 'X-CSRF-Token': session['csrf_token']},
                           json={'expected_revision': 0, 'basis_id': ReviewWorkbench(fixture['config'])._context(handle)[3]})
    assert response.status_code == 409 and response.json()['detail'] == 'REVIEW_SCHEMA_REQUIRED'
