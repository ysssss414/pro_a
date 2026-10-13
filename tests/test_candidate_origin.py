"""Candidate membership and isolation; synthetic inputs, no provider calls."""
import copy
from dataclasses import replace
import json

import pytest

from pro_a import candidate_origin as origin, output_decomposition as output
from pro_a.bounded_extraction import create_extraction_series, initial_extraction_plan
from test_provider_record_v4 import records


def fixture():
    context, catalog, _, record = records()
    series = create_extraction_series(context, catalog, 'CANDIDATE_SYNTHETIC_RUN',
                                      series_version=output.OUTPUT_SERIES_VERSION)
    segment = initial_extraction_plan(series).leaves[0]
    scope = {k: 'a' * 64 for k in origin.SCOPE_FIELDS}
    scope.update(source_id='SRC_SYNTHETIC', source_sha256=context.source_sha256,
                 source_ingestion_time='2026-10-12T00:00:00+00:00',
                 run_id=series.processing_run_id, runtime_identity={'synthetic': True},
                 series_id=series.series_id, series_sha256=series.series_sha256,
                 source_piece_id=context.piece.piece_id, segment_id=segment.segment_id,
                 segment_sha256=segment.segment_sha256, attempt_id='ATTEMPT_SYNTHETIC_1',
                 provider_record_version=origin.v4.VERSION)
    return record, scope, segment, catalog, context


def build(values):
    record, scope, segment, catalog, context = values
    return origin.build(json.dumps(record, ensure_ascii=False).encode(), scope, segment, catalog, context)


def test_mixed_response_keeps_unrelated_objects_and_original_membership():
    values = fixture()
    record = values[0]
    good = copy.deepcopy(record['claims'][0])
    good['related_candidate_names'] = []
    missing = copy.deepcopy(good)
    del missing['nature']
    foreign = copy.deepcopy(good)
    foreign['evidence']['evidence_ref'] = 'EV_FOREIGN'
    record['claims'] = [good, missing, foreign, record['claims'][0]]
    del record['node_candidates'][0]['primary_type']
    original = copy.deepcopy(record)
    result = build(values)
    claims = [o for o in result['objects'] if o['family'] == 'claims']
    assert [o['status'] for o in claims] == ['SEMANTIC_REVIEW_REQUIRED', 'ISOLATED', 'ISOLATED', 'ISOLATED']
    assert result['canonical_permission'] is False and result['coverage_authority'] is False
    raw = json.dumps(record, ensure_ascii=False).encode()
    for obj in result['objects']:
        a, b = obj['byte_span']
        assert json.loads(raw[a:b]) == obj['value']
    assert record == original


@pytest.mark.parametrize('raw', [b'{"claims":[{}]', b'{"claims":[],"claims":[]}', b'{"claims":[NaN]}'])
def test_incomplete_duplicate_or_nonfinite_json_has_no_origin(raw):
    _, scope, segment, catalog, context = fixture()
    with pytest.raises(ValueError, match='CANDIDATE_COMPLETE_JSON_REQUIRED'):
        origin.build(raw, scope, segment, catalog, context)


def test_shared_catalog_corruption_blocks_entire_scope():
    record, scope, segment, catalog, context = fixture()
    corrupted = replace(catalog, units=(replace(catalog.units[0], exact_text='replaced'), *catalog.units[1:]))
    with pytest.raises(ValueError, match='CATALOG_BINDING_MISMATCH'):
        build((record, scope, segment, corrupted, context))


def test_malformed_and_ambiguous_entities_only_isolate_their_dependents():
    values = fixture()
    record = values[0]
    independent = copy.deepcopy(record['claims'][0])
    independent['related_candidate_names'] = []
    independent['related_node_ids'] = []
    record['claims'] = [record['claims'][0], independent]
    record['node_candidates'].append(copy.deepcopy(record['node_candidates'][0]))
    record['node_candidates'].append({'canonical_name': []})
    record['node_matches'].append({'node_id': []})
    result = build(values)
    claims = [o for o in result['objects'] if o['family'] == 'claims']
    assert claims[0]['status'] == 'ISOLATED' and claims[-1]['status'] == 'SEMANTIC_REVIEW_REQUIRED'
    assert len(origin.semantic_projection([result]).claims) == 1


def test_attempt_and_content_changes_invalidate_old_origin():
    values = fixture()
    result = build(values)
    record, scope, segment, catalog, context = values
    changed = {**scope, 'attempt_id': 'ATTEMPT_SYNTHETIC_2'}
    raw = json.dumps(record, ensure_ascii=False).encode()
    with pytest.raises(ValueError, match='CANDIDATE_ORIGIN_DRIFT'):
        origin.verify(result, raw, changed, segment, catalog, context)
    other = origin.build(raw, changed, segment, catalog, context)
    assert result['objects'][0]['observation_id'] != other['objects'][0]['observation_id']


def test_provider_cannot_grant_governance_and_missing_nature_does_not_default():
    values = fixture()
    record = values[0]
    record['claims'][0]['structured_json'] = json.dumps({'admission_semantics': 'FACTUAL_KNOWLEDGE'})
    result = build(values)
    claim = next(o for o in result['objects'] if o['family'] == 'claims')
    assert claim['status'] == 'ISOLATED'
    assert 'PROVIDER_GOVERNANCE_FORBIDDEN' in claim['errors']


@pytest.mark.parametrize('local_revision', [False, True])
def test_durable_failed_attempt_input_does_not_change_history(tmp_path_factory, monkeypatch, local_revision):
    # Advice publication adds a packet hash and a UUID pending filename.
    # Keep the synthetic root short enough for ordinary Windows paths.
    tmp_path = tmp_path_factory.mktemp('candidate')
    from series_binding_helpers import case, start, Transport, synthetic_providers, rows
    from pro_a.workbench.candidate_inputs import CandidateInputs
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))

    class Mixed(Transport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            function = response.value['choices'][0]['message']['tool_calls'][0]['function']
            record = json.loads(function['arguments'])
            record['claims'][0]['statement'] = 'Synthetic Company operating profit was 999999 units.'
            record['claims'][0]['related_candidate_names'] = []
            bad_node = copy.deepcopy(record['node_candidates'][0])
            bad_node['canonical_name'] = 'Incorrect synthetic entity'
            del bad_node['primary_type']
            record['node_candidates'].append(bad_node)
            dependent = copy.deepcopy(record['claims'][-1])
            dependent['related_candidate_names'] = ['Incorrect synthetic entity']
            record['claims'].append(dependent)
            bad = copy.deepcopy(record['claims'][0])
            del bad['nature']
            record['claims'].append(bad)
            record['source_metadata'].update(source_rank='UNRANKED', source_origin_type='unknown')
            function['arguments'] = json.dumps(record)
            return response

    value = case(tmp_path)
    from pro_a.admission_schema import migrate
    from pro_a.production_promotion import sha256_file
    migrate(value['config'].knowledge_db, expected_sha256=sha256_file(value['config'].knowledge_db),
            backup_path=tmp_path / 'before-b-lite.sqlite3', configured_production_path=value['config'].knowledge_db)
    from series_binding_helpers import text, upload, clean_pdf
    source = upload(value, clean_pdf(tmp_path, text='Synthetic anonymous interview title.\n' + text(3)))
    run_id = value['service'].start(source['source_id'], idempotency_key='candidate-mixed-source-0001')['run']['processing_run_id']
    service = value['service']
    service.advance_once(worker_id='candidate-test', processing_run_id=run_id)
    with synthetic_providers(value, Mixed()) as provider:
        service.advance_once(worker_id='candidate-test', processing_run_id=run_id, provider=provider)
    assert not rows(value, 'bounded_extraction_segment_results')
    attempts = rows(value, 'bounded_extraction_attempts')
    before = value['config'].state_db.read_bytes()
    production = value['config'].knowledge_db.read_bytes()
    inputs = CandidateInputs(service)
    reference = inputs.publish(run_id, attempts[0]['attempt_id'])
    result = inputs.read(reference)
    assert any(o['status'] == 'SEMANTIC_REVIEW_REQUIRED' for o in result['objects'] if o['family'] == 'claims')
    assert any(o['status'] == 'ISOLATED' for o in result['objects'] if o['family'] == 'claims')
    assert reference == inputs.publish(run_id, attempts[0]['attempt_id'])
    assert value['config'].state_db.read_bytes() == before
    assert value['config'].knowledge_db.read_bytes() == production
    from pro_a.phase4_orchestration import start_execution, resume_execution
    from pathlib import Path
    input_path = tmp_path / 'candidate-input.json'
    input_path.write_text(json.dumps({'documents': [result]}), encoding='utf-8')
    with service.store.connect() as connection:
        source = connection.execute('SELECT storage_relative FROM private_sources WHERE source_id=?',
                                    (result['scope']['source_id'],)).fetchone()
    native = start_execution(service.artifacts.resolve(source[0]),
                             config_path=value['phase4_config'], external_semantic=True,
                             candidate_input_path=input_path, stop_after='SEMANTIC_INPUT_READY')
    assert native['state'] == 'SEMANTIC_INPUT_READY', native
    root = Path(native['execution_root'])
    manifest = json.loads((root / 'engine/run_manifest.json').read_text(encoding='utf-8'))
    assert manifest['schema_version'] == '2' and manifest['model']['llm_invoked'] is False
    assert manifest['model']['extraction_mode'] == 'VERIFIED_CANDIDATE_ORIGIN'
    assert value['config'].knowledge_db.read_bytes() == production
    from fastapi.testclient import TestClient
    from pro_a.workbench.api import create_app, PREFIX
    token = 'synthetic-candidate-browser-token-tests-only'
    monkeypatch.setenv(value['config'].session_token_env, token)
    client = TestClient(create_app(value['config'], cloud_profile=value['cloud_profile'],
        source_profile=value['source_profile']), base_url=value['config'].origin, client=('127.0.0.1', 1))
    endpoint = PREFIX + '/source-operations/runs/' + run_id + '/candidates'
    assert client.post(endpoint, json={}).status_code == 403
    session = client.post(PREFIX + '/session', headers={'Origin': value['config'].origin}, json={'token': token}).json()
    headers = {'Origin': value['config'].origin, 'X-CSRF-Token': session['csrf_token']}
    assert client.post(endpoint, headers={'Origin': value['config'].origin}, json={}).status_code == 403
    response = client.post(endpoint, headers=headers, json={'idempotency_key': 'candidate-synthetic-child-0001'})
    assert response.status_code == 200, response.text
    child = response.json()['run']
    child_id = child['processing_run_id']
    assert child_id != run_id and child['candidate_origin']['version'] == origin.VERSION
    from pro_a.workbench.stage1_scale import stage1_capacity
    with service.store.connect() as connection:
        assert stage1_capacity(connection)['runs_last_24h'] == 2
    service.advance_once(worker_id='candidate-test', processing_run_id=child_id)
    child = service.advance_once(worker_id='candidate-test', processing_run_id=child_id)
    assert child['state'] == 'SEMANTIC_PROCESSING', child
    assert len(child['jobs']) == 1
    assert len(rows(value, 'bounded_extraction_attempts')) == len(attempts)
    with synthetic_providers(value) as provider:
        child = service.advance_once(worker_id='candidate-test', processing_run_id=child_id, provider=provider)
    assert child['state'] == 'HUMAN_REVIEW_REQUIRED', child
    from pro_a.workbench.review_workbench import ReviewWorkbench
    from pro_a.workbench.advisory_review import AdvisoryReview
    from pro_a.workbench.config import BoundaryError
    from pro_a.mcp.service import ReadService
    from pro_a.mcp.review_context import basis
    from pro_a.workbench.attribution import Attribution
    import uuid
    reviews = ReviewWorkbench(value['config'])
    handle = child['packet_artifact_id']
    review = reviews.read(handle)
    request = {'basis_id': review['review']['basis_id'], 'expected_revision': 0,
               'operation_id': uuid.uuid4().hex, 'reviewer': 'Synthetic user',
               'reason': 'Synthetic evidence checked', 'confirm': True}
    human = {'actor': 'synthetic-user', 'session_id': 'synthetic-session', 'principal_type': 'HUMAN_USER'}
    with pytest.raises(BoundaryError, match='HUMAN_USER_REQUIRED'):
        reviews.mutate(handle, 'seal', request, {**human, 'principal_type': 'MODEL'})
    revision = 0
    delayed = [r['candidate_id'] for r in review['items'] if r['candidate_type'] == 'CLAIM' and '999999' not in r['content']['statement']][-1]
    title_claims = {r['candidate_id'] for r in review['items'] if r['candidate_type'] == 'CLAIM' and '999999' in r['content']['statement']}
    for row in review['items']:
        decision = 'KEEP' if row['candidate_type'] == 'CLAIM' else 'CREATE'
        if row['candidate_id'] == delayed or row['candidate_id'] in title_claims:
            decision = 'DROP'
        changed = reviews.mutate(handle, 'decision', {**request, 'expected_revision': revision,
            'operation_id': uuid.uuid4().hex, 'candidate_id': row['candidate_id'],
            'decision': decision, 'target_node_id': ''}, human)
        revision = changed['revision']
    request.update(expected_revision=revision, operation_id=uuid.uuid4().hex)
    with pytest.raises(BoundaryError, match='DUAL_ADVICE_REQUIRED'):
        reviews.mutate(handle, 'seal', request, human)
    context, candidates, _ = basis(ReadService(value['config']), handle, 'blind', None)
    exported = client.get(PREFIX + '/reviews/' + handle + '/advice-context').json()
    assert exported['context']['context_sha256'] == context.context_sha256 and 'canonical_nodes' in exported
    for slot in ('A', 'B'):
        posted = client.post(PREFIX + '/reviews/' + handle + '/advice', headers=headers, json={
            'slot': slot, 'reviewer_type': 'MODEL', 'reviewer_id': 'synthetic-reviewer-' + slot,
            'context_sha256': context.context_sha256,
            'items': [{'candidate_id': c.candidate_id, 'content_sha256': c.content_sha256,
                       'judgment': 'UNSUPPORTED' if c.candidate_id in title_claims else 'SUPPORTED',
                       'reason': 'Title cannot support an operating assertion' if c.candidate_id in title_claims else 'Synthetic support inspected'} for c in candidates]})
        assert posted.status_code == 200, posted.text
        if slot == 'A':
            with pytest.raises(BoundaryError, match='DUAL_ADVICE_REQUIRED'):
                reviews.mutate(handle, 'seal', request, human)
    if local_revision:
        # A local exact-range revision gets a new Packet, while unchanged objects
        # can explicitly carry forward the same reviewers' registered advice.
        selected = next(o for o in result['objects'] if o['family'] == 'claims'
                        and o['status'] == 'SEMANTIC_REVIEW_REQUIRED' and '999999' not in o['value']['statement'])
        bound = selected['evidence'][0]
        revised_ref = inputs.publish(run_id, attempts[0]['attempt_id'], {
            selected['observation_id']: {'evidence_ref': bound['evidence_ref'],
                'source_start': bound['source_start'], 'source_end': bound['source_end'],
                'reason': 'Synthetic human confirms exact span', 'reviewer': human['actor']}})
        revised_run = service.start_candidates([revised_ref], idempotency_key='candidate-synthetic-revision-0001')['run']
        revised_id = revised_run['processing_run_id']
        service.advance_once(worker_id='candidate-test', processing_run_id=revised_id)
        service.advance_once(worker_id='candidate-test', processing_run_id=revised_id)
        with synthetic_providers(value) as provider:
            revised_run = service.advance_once(worker_id='candidate-test', processing_run_id=revised_id, provider=provider)
        revised_handle = revised_run['packet_artifact_id']
        new_context, new_candidates, _ = basis(ReadService(value['config']), revised_handle, 'blind', None)
        old_content = {c.candidate_id: c.content_sha256 for c in candidates}
        changed = [c for c in new_candidates if old_content.get(c.candidate_id) != c.content_sha256]
        unchanged = [c for c in new_candidates if old_content.get(c.candidate_id) == c.content_sha256]
        assert changed and any(c.candidate_type == 'CLAIM' for c in unchanged)
        changed_claims = {c.candidate_id for c in changed if c.candidate_type == 'CLAIM'}
        dependent_nodes = [c for c in new_candidates if c.candidate_type == 'NODE'
                           and changed_claims.intersection(c.content.supporting_claim_ids)]
        assert dependent_nodes and all(c in changed for c in dependent_nodes)
        assert all(c.content.supporting_claim_revisions for c in dependent_nodes)
        for slot in ('A', 'B'):
            reused = {'slot': slot, 'reviewer_type': 'MODEL', 'reviewer_id': 'synthetic-reviewer-' + slot,
                      'context_sha256': new_context.context_sha256, 'reuse_from': handle, 'items': []}
            with pytest.raises(BoundaryError, match='ADVICE_UNIVERSE_INVALID'):
                AdvisoryReview(reviews).submit(revised_handle, reused)
            reused['items'] = [{'candidate_id': c.candidate_id, 'content_sha256': c.content_sha256,
                               'judgment': 'SUPPORTED', 'reason': 'Changed exact range reviewed anew'} for c in changed]
            recorded = AdvisoryReview(reviews).submit(revised_handle, reused)
            assert set(recorded['reused_advice']) == {c.candidate_id for c in unchanged}
        revised_review = reviews.read(revised_handle)['review']
        assert revised_review['status'] != 'SEALED' and revised_review['revision'] == 0
        assert not revised_review.get('sealed')
        # No Human decisions or authorizations are transferred to the revised Packet.
        with pytest.raises(BoundaryError):
            reviews.mutate(revised_handle, 'seal', {**request, 'basis_id': revised_review['basis_id'],
                'expected_revision': 0, 'operation_id': uuid.uuid4().hex}, human)
        return
    reviews.mutate(handle, 'seal', request, human)
    assert reviews.read(handle)['review']['status'] == 'SEALED'
    attribution = Attribution(value['config'])
    draft = attribution.read(handle)
    with pytest.raises(BoundaryError, match='HUMAN_USER_REQUIRED'):
        attribution.mutate(handle, 'SEAL', {**request, 'basis_id': draft['basis_id']},
                           {**human, 'principal_type': 'MODEL'})
    revision = 0
    for claim in draft['claims']:
        saved = attribution.mutate(handle, 'SAVE', {**request, 'basis_id': draft['basis_id'],
            'operation_id': uuid.uuid4().hex, 'expected_revision': revision,
            'claim_id': claim['candidate_id'], 'outcome': 'NO_LINK', 'scope': claim['scope'], 'links': []}, human)
        revision = saved['revision']
    attribution.mutate(handle, 'SEAL', {**request, 'basis_id': draft['basis_id'],
        'operation_id': uuid.uuid4().hex, 'expected_revision': revision}, human)
    assert value['config'].knowledge_db.read_bytes() == production
    from pro_a.operational_qualification import qualify
    from pro_a.operational_operator import Operator, OperatorConfig
    from pro_a.operational_contract import readonly
    from contextlib import closing
    envelope = qualify(value['config'], handle, attribution.read(handle)['sidecar']['object_id'])
    assert value['config'].knowledge_db.read_bytes() == production
    operator = Operator(OperatorConfig(value['config'], tmp_path / 'operator/ledger.sqlite3'))
    operator.initialize()
    eid = envelope['object_id']
    with pytest.raises(BoundaryError):
        operator.execute(eid, confirm=eid)
    operator.register(eid, confirm=eid)
    receipt = operator.execute(eid, confirm=eid)
    assert receipt['status'] == 'EXECUTED'
    assert operator.reconcile(eid) == receipt
    with closing(readonly(value['config'].knowledge_db)) as connection:
        admitted = list(connection.execute('SELECT * FROM claims WHERE source_id=?', (result['scope']['source_id'],)))
        assert admitted and all(c['admission_semantics'] == 'SOURCE_ASSERTION' and
            c['reality_support'] == 'UNVERIFIED' and c['current_view_use'] == 'CLUE_ONLY' and
            len(c['admission_basis_sha256']) == 64 for c in admitted)
    # Later batch admits the previously deferred statement with exact Source reuse.
    second = service.start_candidates([reference], idempotency_key='candidate-synthetic-child-0002')['run']
    second_id = second['processing_run_id']
    assert second_id != child_id
    service.advance_once(worker_id='candidate-test', processing_run_id=second_id)
    service.advance_once(worker_id='candidate-test', processing_run_id=second_id)
    with synthetic_providers(value) as provider:
        second = service.advance_once(worker_id='candidate-test', processing_run_id=second_id, provider=provider)
    assert second['state'] == 'HUMAN_REVIEW_REQUIRED', second
    second_handle = second['packet_artifact_id']
    state = reviews.read(second_handle)
    request = {**request, 'basis_id': state['review']['basis_id'], 'expected_revision': 0}
    revision = 0
    reused_node = None
    for row in state['items']:
        native = next(r for r in state['review']['rows'] if r['candidate_id'] == row['candidate_id'])
        decision = 'KEEP' if row['candidate_type'] == 'CLAIM' else 'REUSE'
        if row['candidate_id'] in title_claims:
            decision = 'DROP'
        if decision == 'REUSE':
            reused_node = native['reuse_target']
            assert reused_node
        changed = reviews.mutate(second_handle, 'decision', {**request,
            'expected_revision': revision, 'operation_id': uuid.uuid4().hex,
            'candidate_id': row['candidate_id'], 'decision': decision,
            'target_node_id': reused_node if decision == 'REUSE' else ''}, human)
        revision = changed['revision']
    context, candidates, _ = basis(ReadService(value['config']), second_handle, 'blind', None)
    for slot in ('A', 'B'):
        AdvisoryReview(reviews).submit(second_handle, {'slot': slot, 'reviewer_type': 'MODEL',
            'reviewer_id': 'synthetic-reviewer-' + slot, 'context_sha256': context.context_sha256,
            'items': [{'candidate_id': c.candidate_id, 'content_sha256': c.content_sha256,
                       'judgment': 'UNSUPPORTED' if c.candidate_id in title_claims else 'SUPPORTED',
                       'reason': 'Synthetic second batch checked'} for c in candidates]})
    reviews.mutate(second_handle, 'seal', {**request, 'expected_revision': revision,
        'operation_id': uuid.uuid4().hex}, human)
    draft = attribution.read(second_handle)
    revision = 0
    for claim in draft['claims']:
        saved = attribution.mutate(second_handle, 'SAVE', {**request, 'basis_id': draft['basis_id'],
            'operation_id': uuid.uuid4().hex, 'expected_revision': revision,
            'claim_id': claim['candidate_id'], 'outcome': 'LINK', 'scope': claim['scope'],
            'links': [{'node_id': reused_node, 'role': 'subject'}]}, human)
        revision = saved['revision']
    attribution.mutate(second_handle, 'SEAL', {**request, 'basis_id': draft['basis_id'],
        'operation_id': uuid.uuid4().hex, 'expected_revision': revision}, human)
    with closing(readonly(value['config'].knowledge_db)) as connection:
        source_before = dict(connection.execute('SELECT * FROM sources WHERE source_id=?', (result['scope']['source_id'],)).fetchone())
    second_envelope = qualify(value['config'], second_handle, attribution.read(second_handle)['sidecar']['object_id'])
    assert any(m['table'] == 'sources' for m in second_envelope['predicted_diff']['unchanged'])
    assert not any(m['table'] in ('sources', 'nodes') for m in second_envelope['predicted_diff']['inserts'])
    eid = second_envelope['object_id']
    operator.register(eid, confirm=eid)
    assert operator.execute(eid, confirm=eid)['status'] == 'EXECUTED'
    zero = service.start_candidates([reference], idempotency_key='candidate-synthetic-zero-0003')
    assert zero['status'] == 'ZERO_INCREMENT' and zero['rejected_count'] == len(title_claims)
    with service.store.connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity['runs_last_24h'] == 3 and not capacity['new_intake_allowed']
    assert all('999999' not in c['row']['statement'] for c in second_envelope['mutations'] if c['table'] == 'claims')
    with closing(readonly(value['config'].knowledge_db)) as connection:
        assert source_before == dict(connection.execute('SELECT * FROM sources WHERE source_id=?', (result['scope']['source_id'],)).fetchone())
        assert connection.execute('SELECT count(*) FROM claims WHERE source_id=?', (result['scope']['source_id'],)).fetchone()[0] == 3
    from pro_a.research_explorer import ResearchExplorer
    explorer = ResearchExplorer(value['config'])
    visible = explorer.claims(source_id=result['scope']['source_id'])['items']
    assert len(visible) == 3 and all(c['reality_support'] == 'UNVERIFIED' for c in visible)
    assert explorer.claim(delayed)['claim']['current_view_use'] == 'CLUE_ONLY'
    reads = ReadService(value['config'])
    assert reads.get_node_evidence(reused_node).claims[0].admission_semantics == 'SOURCE_ASSERTION'
    safe_source = reads.get_source(result['scope']['source_id'], claim_limit=2)
    assert len(safe_source.canonical.claims) == 2 and safe_source.canonical.next_claim_cursor
    assert all(c.current_view_use == 'CLUE_ONLY' for c in safe_source.canonical.claims)
    assert 'structured_json' not in safe_source.model_dump_json() and 'artifact_relative' not in safe_source.model_dump_json()
    import sqlite3
    with sqlite3.connect(value['config'].knowledge_db) as connection:
        with pytest.raises(sqlite3.IntegrityError, match='CURRENT_VIEW_REVIEWED_BASIS_REQUIRED'):
            connection.execute("INSERT INTO current_views(view_id,node_id,version,change_level,content_md,content_json,created_at) VALUES(?,?,?,?,?,?,?)",
                ('VIEW_SYNTHETIC_DENIED', reused_node, '1', 'initial', 'Unsupported official view',
                 json.dumps({'evidence_claim_ids': [delayed]}), '2026-10-12'))
    assert len(rows(value, 'bounded_extraction_attempts')) == len(attempts)
    assert not rows(value, 'bounded_extraction_segment_results')

def test_precise_range_revision_retains_raw_and_only_invalidates_affected_claim():
    values = fixture()
    record, scope, segment, catalog, context = values
    claim = record['claims'][0]
    claim['related_candidate_names'] = []
    claim['related_node_ids'] = []
    record['claims'] = [claim, copy.deepcopy(claim)]
    record['claims'][1]['statement'] += ' Second synthetic observation.'
    claim['evidence'].update(selection_mode='RAW_SUBSPAN', selector='Not in source', occurrence='1')
    original = build(values)
    objects = [o for o in original['objects'] if o['family'] == 'claims']
    unit = catalog.units[0]
    revisions = {objects[0]['observation_id']: {'evidence_ref': unit.evidence_ref,
        'source_start': unit.source_start, 'source_end': unit.source_end,
        'reason': 'Human selected exact original span', 'reviewer': 'Synthetic human'}}
    raw = json.dumps(record, ensure_ascii=False).encode()
    revised = origin.build(raw, scope, segment, catalog, context, revisions)
    revised_claims = [o for o in revised['objects'] if o['family'] == 'claims']
    assert revised['raw_sha256'] == original['raw_sha256']
    assert revised_claims[0]['value'] == objects[0]['value']
    assert revised_claims[0]['status'] == 'SEMANTIC_REVIEW_REQUIRED'
    assert revised_claims[0]['evidence'][0]['evidence_excerpt'] == unit.exact_text
    assert revised_claims[0]['revision_sha256'] != objects[0]['revision_sha256']
    assert revised_claims[1]['revision_sha256'] == objects[1]['revision_sha256']
    assert revised['original_identity'] == original['identity']


def test_same_content_different_attempts_and_order_deduplicate():
    values = fixture()
    record, scope, segment, catalog, context = values
    left = build(values)
    right = origin.build(json.dumps(record, ensure_ascii=False).encode(), {**scope, 'attempt_id': 'ATTEMPT_OTHER'}, segment, catalog, context)
    a = origin.semantic_projection([left, right])
    b = origin.semantic_projection([right, left])
    assert len(a.claims) == len(origin.semantic_projection([left]).claims)
    assert len(a.node_candidates) == len(origin.semantic_projection([left]).node_candidates)
    assert len(a.node_matches) == len(origin.semantic_projection([left]).node_matches)
    assert {c['candidate_key'] for c in a.claims} == {c['candidate_key'] for c in b.claims}
    assert all(len(c['candidate_observations']) == 2 for c in a.claims)


def test_split_chinese_word_requires_explicit_exact_range_revision():
    from test_source_analysis_wire import context as make_context, empty_canonical, canonical_claim
    from pro_a.source_analysis_wire import build_source_evidence_catalog
    from lexical_record_helpers import from_canonical
    from provider_record_v4_helpers import from_valid_v3
    ctx = make_context('匿名专家表示，预\n计明年产能增加。')
    catalog = build_source_evidence_catalog(ctx)
    unit = next(u for u in catalog.units if '预\n计' in u.exact_text)
    native = empty_canonical()
    native['claims'] = [canonical_claim('专家预计明年产能增加。', unit)]
    record = from_canonical(native, catalog)
    record['evidence_acknowledgements'] = [{'evidence_ref': u.evidence_ref} for u in catalog.units]
    record = from_valid_v3(record)
    record['claims'][0]['evidence'].update(selection_mode='NORMALIZED_SUBSPAN', selector='预计', occurrence='1')
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_NEWLINE', series_version=output.OUTPUT_SERIES_VERSION)
    segment = initial_extraction_plan(series).leaves[0]
    scope = {**fixture()[1], 'source_sha256': ctx.source_sha256, 'source_piece_id': ctx.piece.piece_id,
             'run_id': series.processing_run_id, 'series_id': series.series_id, 'series_sha256': series.series_sha256,
             'segment_id': segment.segment_id, 'segment_sha256': segment.segment_sha256}
    raw = json.dumps(record, ensure_ascii=False).encode()
    original = origin.build(raw, scope, segment, catalog, ctx)
    claim = next(o for o in original['objects'] if o['family'] == 'claims')
    assert claim['status'] == 'ISOLATED'
    revised = origin.build(raw, scope, segment, catalog, ctx, {claim['observation_id']: {
        'evidence_ref': unit.evidence_ref, 'source_start': unit.source_start, 'source_end': unit.source_end,
        'reason': 'Human selects the complete original sentence across its line break', 'reviewer': 'Synthetic human'}})
    fixed = next(o for o in revised['objects'] if o['family'] == 'claims')
    assert fixed['status'] == 'SEMANTIC_REVIEW_REQUIRED'
    assert fixed['value'] == claim['value'] and revised['raw_sha256'] == original['raw_sha256']
    assert '预\n计' in fixed['evidence'][0]['evidence_excerpt']


def test_advice_requires_distinct_reviewers_exact_revision_and_support():
    from pro_a.workbench.advisory_review import validate, validate_promotable
    from pro_a.workbench.config import BoundaryError
    from pro_a.evidence_binding import identity
    packet = {'immutable_packet_sha256': 'a' * 64, 'claims': [{'candidate_id': 'C_SYNTHETIC',
              'content_sha256': 'b' * 64, 'human_input': {'decision': 'KEEP'}}], 'nodes': [], 'relations': []}
    def advice(slot):
        body = {'version': 'native-advice-v1', 'slot': slot, 'packet_sha256': 'a' * 64,
                'context_sha256': 'c' * 64, 'reviewer_id': 'synthetic-' + slot, 'reviewer_type': 'MODEL',
                'items': [{'candidate_id': 'C_SYNTHETIC', 'content_sha256': 'b' * 64,
                           'judgment': 'SUPPORTED', 'reason': 'Synthetic exact evidence inspected'}]}
        return {**body, 'sha256': identity(body)}
    pair = {slot: advice(slot) for slot in ('A', 'B')}
    validate_promotable(packet, pair)
    for kind in ('same_reviewer', 'context', 'revision', 'unsupported'):
        changed = copy.deepcopy(pair)
        b = changed['B']
        if kind == 'same_reviewer': b['reviewer_id'] = changed['A']['reviewer_id']
        if kind == 'context': b['context_sha256'] = 'd' * 64
        if kind == 'revision': b['items'][0]['content_sha256'] = 'e' * 64
        if kind == 'unsupported': b['items'][0]['judgment'] = 'UNSUPPORTED'
        b['sha256'] = identity({k: v for k, v in b.items() if k != 'sha256'})
        with pytest.raises(BoundaryError):
            validate_promotable(packet, changed)
    with pytest.raises(BoundaryError, match='DUAL_ADVICE_REQUIRED'):
        validate(packet, {'A': pair['A']})

def test_new_run_failure_policy_continues_only_preplanned_unrelated_segments(tmp_path, monkeypatch):
    from series_binding_helpers import case, start, synthetic_providers, Transport, rows
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))
    value = case(tmp_path)
    _, run_id = start(value, tmp_path, count=90)
    service = value['service']
    run = service.advance_once(worker_id='isolation-test', processing_run_id=run_id)
    assert run['failure_isolation_policy'] == origin.POLICY
    planned = rows(value, 'bounded_extraction_segments')
    assert len(planned) > 1
    transport = Transport(mode=lambda target, number: 'malformed' if number == 1 else None)
    with synthetic_providers(value, transport) as providers:
        for _ in range(len(planned) + 6):
            run = service.advance_once(worker_id='isolation-test', processing_run_id=run_id, provider=providers)
            if run['state'] in ('FAILED', 'BLOCKED', 'RECOVERY_REQUIRED', 'HUMAN_REVIEW_REQUIRED'):
                break
    assert len(transport.calls) == len(planned)
    assert len(rows(value, 'bounded_extraction_attempts')) == len(planned)
    assert len(rows(value, 'bounded_extraction_segments')) == len(planned)
    assert run['coverage_status'] == 'FAILED' and run['state'] in ('FAILED', 'BLOCKED')
    accepted = rows(value, 'bounded_extraction_segment_results')
    assert len(accepted) == len(planned) - 1
    assert service.advance_once(worker_id='isolation-test', processing_run_id=run_id) is None
