"""Real Source Operations acceptance, synthetic transport only; no network."""
import copy
import json

import pytest

from pro_a import candidate_origin_v2 as bridge
from pro_a import output_provider_record_v7 as v7
from pro_a.candidate_origin import semantic_projection
from pro_a.workbench.candidate_inputs import CandidateInputs
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.source_operations import SourceOperationError
from series_binding_helpers import rows, synthetic_providers
from test_output_qualification import fixture, advance, FakeTransport


class SmallTransport(FakeTransport):
    """Three parents are sufficient for six revision observations and dedup."""
    def __call__(self, *args, **kwargs):
        response = super().__call__(*args, **kwargs)
        function = response.value['choices'][0]['message']['tool_calls'][0]['function']
        record = json.loads(function['arguments'])
        record['claims'] = record['claims'][:3]
        function['arguments'] = json.dumps(record)
        return response


def accepted_case(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('EXTERNAL_NETWORK'))
    value, run = fixture(tmp_path, monkeypatch, v7.VERSION)
    from pro_a.admission_schema import migrate
    from pro_a.production_promotion import sha256_file
    migrate(value['config'].knowledge_db, expected_sha256=sha256_file(value['config'].knowledge_db),
            backup_path=tmp_path / 'schema-backup.db', configured_production_path=value['config'].knowledge_db)
    rid = run['processing_run_id']
    advance(value, rid)
    advance(value, rid, SmallTransport())
    attempt = rows(value, 'bounded_extraction_segment_results')[0]['attempt_id']
    archive = CandidateInputs(value['service'])
    reference = archive.publish(rid, attempt)
    doc = archive.read(reference)
    value.update(original_id=rid, attempt=attempt, archive=archive, reference=reference, document=doc)
    return value


def children(document):
    revisions = {}
    parents = [o for o in document['objects'] if o['family'] == 'claims']
    # Six explicit semantic proposals. Duplicate second proposal intentionally
    # exercises many observations supporting one fact, not automatic splitting.
    for parent in parents[:3]:
        claim = parent['normalized']
        revisions[parent['observation_id']] = {'version': bridge.REVISION,
            'parent_revision_sha256': parent['revision_sha256'], 'reason': 'Synthetic explicit proposals',
            'reviewer': 'TEST_FIXTURE_AGENT_NOT_HUMAN', 'children': [
                {'child_id': str(i), 'statement': claim['statement'], 'fact_time': claim.get('fact_time', ''),
                 'assumption': claim.get('assumption', ''), 'status': 'SEMANTIC_REVIEW_REQUIRED',
                 'context_dependencies': []} for i in range(2)]}
    # Unselected raw parents stay visible but cannot enter this review selection.
    for parent in parents[3:]:
        revisions[parent['observation_id']] = {'version': bridge.REVISION,
            'parent_revision_sha256': parent['revision_sha256'], 'reason': 'Outside small fixture selection',
            'reviewer': 'TEST_FIXTURE_AGENT_NOT_HUMAN', 'children': []}
    return revisions


def metadata_resolution(document):
    from pro_a import source_metadata_authority as metadata
    from pro_a.evidence_binding import identity
    s = document['scope']
    scope = metadata.scope(s['run_id'], s['source_id'], s['source_sha256'],
        [{'source_piece_id': s['source_piece_id'], 'series_id': s['series_id']}],
        [document['acceptance']['result_sha256']])
    candidate = metadata.candidate_resolution(scope, [])
    return metadata.authorize_resolution(candidate, {'version': metadata.DECISION_VERSION,
        'candidate_identity': candidate['identity'], 'scope_sha256': identity(scope), 'approved': True,
        'actor': 'TEST_ONLY_SYNTHETIC_HUMAN', 'reason': 'Explicit fixture source identity',
        'decision_reference': 'TEST_FIXTURE_NOT_REAL_AUTHORIZATION',
        'values': {k: document['source_metadata'].get(k, '') for k in metadata.FIELDS if k != 'summary'},
        'summary_policy': 'PRESERVE_ALL_VARIANTS_UNRESOLVED'})


def test_archive_drift_and_non_authoritative_children(tmp_path, monkeypatch):
    value = accepted_case(tmp_path, monkeypatch)
    archive, doc, service = value['archive'], value['document'], value['service']
    with pytest.raises(SourceOperationError, match='SOURCE_METADATA_AUTHORITY_REQUIRED'):
        service.start_v7_review([value['reference']], idempotency_key='unresolved-metadata-test',
                                entry_contract=bridge.ENTRY_CONTRACT)
    paths = [service.artifacts.resolve(r['artifact_relative']) for r in
             rows(value, 'bounded_extraction_outcomes') + rows(value, 'bounded_extraction_segment_results')]
    paths += [service.artifacts.resolve(r['artifact_relative']) for r in rows(value, 'source_cloud_inputs')]
    paths += [service.artifacts.resolve(r['storage_relative']) for r in rows(value, 'private_sources')]
    paths += [service.artifacts.resolve(r['artifact_relative']) for r in rows(value, 'domain_run_bindings')]
    for path in paths:
        import stat
        original = path.read_bytes()
        mode = path.stat().st_mode
        try:
            path.chmod(mode | stat.S_IWRITE)  # Deliberate corruption of this disposable fixture only.
            path.write_bytes(original + b' ')
            with pytest.raises((ValueError, BoundaryError, SourceOperationError)):
                archive.read(value['reference'])
        finally:
            path.write_bytes(original)
            path.chmod(mode)
    with service.store.connect(operator_write=True) as db:
        row = db.execute('SELECT runtime_json FROM source_processing_runs WHERE processing_run_id=?',
                         (value['original_id'],)).fetchone()
        changed = json.loads(row[0]); changed['runtime_sha256'] = '0' * 64
        db.execute('UPDATE source_processing_runs SET runtime_json=? WHERE processing_run_id=?',
                   (json.dumps(changed), value['original_id']))
    try:
        with pytest.raises((ValueError, BoundaryError, SourceOperationError)):
            archive.read(value['reference'])
    finally:
        with service.store.connect(operator_write=True) as db:
            db.execute('UPDATE source_processing_runs SET runtime_json=? WHERE processing_run_id=?',
                       (row[0], value['original_id']))
    revisions = children(doc)
    first = next(iter(revisions.values()))['children'][0]
    first['statement'] = 'Unsupported synthetic prediction of 999 units next year.'
    first['status'] = 'UNCERTAIN'
    reference = archive.publish(value['original_id'], value['attempt'], revisions,
                                metadata_resolution=metadata_resolution(doc))
    revised = archive.read(reference)
    projected = semantic_projection([revised])
    assert all(c['statement'] != first['statement'] for c in projected.claims)
    # A location-valid semantic proposal remains visible and unproved if sent to
    # review; the program does not pretend to recognize its false numeric content.
    first['status'] = 'SEMANTIC_REVIEW_REQUIRED'
    new_ref = archive.publish(value['original_id'], value['attempt'], revisions,
                              metadata_resolution=metadata_resolution(doc))
    changed = archive.read(new_ref)
    assert changed['identity'] != revised['identity']
    proposed = next(c for c in semantic_projection([changed]).claims if c['statement'] == first['statement'])
    assert proposed['candidate_observations'][0]['lineage']['semantic_status'] == 'NOT_ESTABLISHED'
    # Changed content/revision cannot use an old Advice content seal.
    from pro_a.workbench.advisory_review import validate_promotable
    from pro_a.evidence_binding import identity
    packet = {'immutable_packet_sha256': 'a' * 64, 'claims': [{'candidate_id': 'C_TEST',
        'content_sha256': changed['identity'], 'human_input': {'decision': 'KEEP'}}], 'nodes': [], 'relations': []}
    pair = {}
    for slot in ('A', 'B'):
        body = {'version': 'native-advice-v1', 'slot': slot, 'packet_sha256': 'a' * 64,
            'context_sha256': 'b' * 64, 'reviewer_id': 'TEST-' + slot, 'reviewer_type': 'MODEL',
            'items': [{'candidate_id': 'C_TEST', 'content_sha256': revised['identity'],
                       'judgment': 'SUPPORTED', 'reason': 'Old revision'}]}
        pair[slot] = {**body, 'sha256': identity(body)}
    with pytest.raises(BoundaryError):
        validate_promotable(packet, pair)
    for advice in pair.values():
        advice['items'][0].update(content_sha256=changed['identity'], judgment='UNCERTAIN')
        advice['sha256'] = identity({k: v for k, v in advice.items() if k != 'sha256'})
    with pytest.raises(BoundaryError):
        validate_promotable(packet, pair)
    assert service.get_run(value['original_id'])['coverage_status'] != 'COMPLETE'


def test_accepted_origin_revision_and_native_packet(tmp_path, monkeypatch):
    value = accepted_case(tmp_path, monkeypatch)
    service, archive, doc = value['service'], value['archive'], value['document']
    assert doc['version'] == bridge.VERSION and not doc['canonical_permission']
    assert doc['scope']['provider_record_version'] == v7.VERSION
    with pytest.raises(BoundaryError, match='CANDIDATE_ATTEMPT_OUTSIDE_RUN'):
        archive.publish(value['original_id'], 'ATTEMPT_FORGED')
    revisions = children(doc)
    reference = archive.publish(value['original_id'], value['attempt'], revisions,
                                metadata_resolution=metadata_resolution(doc))
    revised = archive.read(reference)
    derived = [o for o in revised['objects'] if 'parent' in o]
    assert len(derived) == 6 and all(o['parent']['raw_claim'] == o['value'] for o in derived)
    analysis = semantic_projection([revised])
    assert len(analysis.claims) == 3
    assert all(len(c['candidate_observations']) == 2 for c in analysis.claims)
    with pytest.raises(ValueError, match='CANDIDATE_PARENT_REVISION_MISMATCH'):
        bad = copy.deepcopy(revisions)
        next(iter(bad.values()))['parent_revision_sha256'] = '0' * 64
        archive.publish(value['original_id'], value['attempt'], bad)
    with pytest.raises(ValueError, match='CANDIDATE_CHILD_INVALID'):
        bad = copy.deepcopy(revisions)
        next(iter(bad.values()))['children'][0]['status'] = 'KEEP'
        archive.publish(value['original_id'], value['attempt'], bad)
    with pytest.raises(SourceOperationError, match='CANDIDATE_REVIEW_ENTRY_CONTRACT_REQUIRED'):
        service.start_candidates([reference], idempotency_key='unversioned-entry-synthetic')
    select_document(value, revised)
    run = service.start_v7_review([reference], idempotency_key='v7-review-synthetic-0001',
                                  entry_contract=bridge.ENTRY_CONTRACT)['run']
    rid = run['processing_run_id']
    for _ in range(2):
        run = service.advance_once(worker_id='synthetic', processing_run_id=rid)
    with synthetic_providers(value) as provider:
        provider['SEMANTIC_DECOMPOSITION'].provider_identity = service.jobs.profile.provider
        provider['SEMANTIC_DECOMPOSITION'].adapter_version = service.jobs.profile.adapter_for_operation('SEMANTIC_DECOMPOSITION')
        run = service.advance_once(worker_id='synthetic', processing_run_id=rid, provider=provider)
    assert run['state'] == 'HUMAN_REVIEW_REQUIRED', run.get('error')
    from pro_a.read_model.review_context import basis
    from pro_a.read_model.service import ReadService
    _, candidates, _ = basis(ReadService(value['config']), run['packet_artifact_id'], 'blind', None)
    claims = [c for c in candidates if c.candidate_type == 'CLAIM']
    assert len(claims) == 3
    for claim in claims:
        for observation in claim.content.candidate_origin.observations:
            lineage = observation.lineage
            assert lineage.parent and lineage.semantic_revision
            assert lineage.raw_claim['attributed_to']
            assert lineage.primary_evidence[0]['evidence_excerpt']
            assert lineage.acceptance['attempt_id'] == value['attempt']
            assert lineage.scope['runtime_identity']['runtime_sha256'] == doc['scope']['runtime_identity']['runtime_sha256']
    assert service.get_run(value['original_id'])['state'] == 'EXTRACTION_PROCESSING'
    isolated_review_chain(value, run, tmp_path, monkeypatch)


def isolated_review_chain(value, run, root, monkeypatch, before_execute=None):
    """Synthetic review authorities; actual existing services and SQLite writes."""
    from contextlib import closing
    from pro_a.workbench.review_workbench import ReviewWorkbench
    from pro_a.workbench.review_policy import ReviewPolicy
    from pro_a.read_model.review_context import basis
    from pro_a.read_model.service import ReadService
    from pro_a.review_engine import ReviewEngine, ReviewerConfig
    from pro_a.review_execution import Reason
    from pro_a.workbench.unified_review import UnifiedReview
    from pro_a.workbench.canonical_admission import CanonicalAdmission
    from pro_a.operational_operator import OperatorConfig
    from pro_a.operator_handoff import OperatorHandoff
    from pro_a.operational_contract import readonly, snapshot
    from pro_a.production_promotion import canonical_sha256
    cfg, handle = value['config'], run['packet_artifact_id']
    human = {'actor': 'TEST_ONLY_HUMAN', 'session_id': 'TEST_ONLY_SESSION', 'principal_type': 'HUMAN_USER'}
    def save(name, obj):
        (root / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    policy = ReviewPolicy(ReviewWorkbench(cfg))
    policy.select(handle, 'SINGLE_MODEL_HUMAN', policy.context(handle), human, confirm=True)
    context, candidates, _ = basis(ReadService(cfg), handle, 'blind', None)
    answer = {'context_sha256': context.context_sha256, 'items': [
        {'candidate_id': c.candidate_id, 'content_sha256': c.content_sha256, 'judgment': 'SUPPORTED',
         'reason': {k: 'TEST FIXTURE: source assertion only; reality unverified. Explicit synthetic evidence reviewed.'
                    for k in Reason.model_fields}} for c in candidates]}
    class Mock:
        model = 'TEST_ONLY_REVIEW'
        calls = 0
        def identity(self): return {'kind': 'SYNTHETIC', 'model': self.model}
        @property
        def metadata(self): return {'attempts': [{'attempt_number': 1}] if self.calls else []}
        def infer(self, system, user):
            self.calls += 1
            assert 'untrusted data' in system
            save('p0-input.json', json.loads(user))
            return answer
    backend = Mock()
    engine = ReviewEngine(cfg, ReviewerConfig(enabled=True, artifact_ids=(handle,), slot='A',
        reviewer_id='TEST_ONLY_REVIEWER', execution_id='TEST_ONLY_EXECUTION', model=backend.model,
        isolation_attested_by_operator=False, review_mode='SINGLE_MODEL_HUMAN'))
    p0 = engine.run(handle, context.context_sha256, backend, task_id='TEST_ONLY_P0')
    assert p0['status'] == 'SUCCEEDED'
    assert engine.run(handle, context.context_sha256, backend, task_id='TEST_ONLY_P0') == p0
    save('p0-receipt.json', p0)
    unified = UnifiedReview(cfg)
    ctx = unified.context(handle)
    native = [{'candidate_id': c['candidate_id'], 'content_sha256': c['content_sha256'],
               'decision': 'KEEP' if c['candidate_type'] == 'CLAIM' else 'CREATE',
               'reason': 'TEST FIXTURE explicit Human decision', 'target_node_id': ''} for c in ctx['candidates']]
    for decision, candidate in zip(native, ctx['candidates']):
        targets = (candidate['content'].get('exact_production_resolution') or {}).get('candidate_target_node_ids', [])
        if candidate['candidate_type'] == 'NODE' and len(targets) == 1:
            decision.update(decision='REUSE', target_node_id=targets[0])
    preview = unified.preview(handle, native)
    attrs = [{'claim_id': cid, 'content_sha256': next(c['content_sha256'] for c in native if c['candidate_id'] == cid),
              'scope': c['scope'], 'outcome': 'NO_LINK', 'links': [],
              'reason': 'TEST FIXTURE: no inferred anonymous entity'} for cid, c in preview['universe']['claims'].items()]
    pid = unified.prepare(handle, binding=ctx['binding'], expected_revision=ctx['revision'],
                          native_items=native, attribution_items=attrs, reason='TEST ONLY')['proposal_id']
    with pytest.raises(BoundaryError):
        unified.approve(handle, pid, {**human, 'principal_type': 'MODEL'}, confirm=True)
    save('p1-receipt.json', unified.approve(handle, pid, human, confirm=True))
    admission = CanonicalAdmission(cfg)
    plan = admission.prepare(handle)['plan']
    save('p2-plan.json', plan)
    worker = OperatorHandoff(OperatorConfig(cfg, root / 'operator/ledger.db'))
    worker.operator.initialize()
    with pytest.raises(BoundaryError, match='P2_HUMAN_APPROVAL_REQUIRED'):
        worker.operator.register(plan['envelope_id'], confirm=plan['envelope_id'])
    with monkeypatch.context() as patch:
        patch.setattr('pro_a.workbench.canonical_admission.require_readonly_boundary',
            lambda _: (_ for _ in ()).throw(BoundaryError('UNPRIVILEGED_PROCESS_REQUIRED')))
        with pytest.raises(BoundaryError, match='UNPRIVILEGED_PROCESS_REQUIRED'):
            admission.approve(handle, plan['object_id'], human, confirm=True)
    with monkeypatch.context() as patch:
        patch.setattr('pro_a.workbench.canonical_admission.require_readonly_boundary',
            lambda _: {'scheme': 'WINDOWS_MANDATORY_INTEGRITY', 'web_integrity': 4096})
        patch.setattr('pro_a.operator_handoff.integrity_level', lambda: 8192)
        admission.approve(handle, plan['object_id'], human, confirm=True)
        if before_execute is not None:
            return before_execute(admission, worker, handle, plan, human)
        result = worker.run(handle)
        assert result['status'] == 'RECONCILED'
        before = cfg.knowledge_db.read_bytes()
        assert worker.run(handle)['receipt'] == result['receipt']
        assert cfg.knowledge_db.read_bytes() == before
    assert result['receipt']['actual_mutation_counts'] == plan['insert_counts']
    with closing(readonly(cfg.knowledge_db)) as db:
        assert canonical_sha256(snapshot(db)) == plan['post_state_sha256']
        claims = [dict(r) for r in db.execute('SELECT * FROM claims')]
        assert len(claims) == 3
        assert all((c['admission_semantics'], c['reality_support'], c['current_view_use']) ==
                   ('SOURCE_ASSERTION', 'UNVERIFIED', 'CLUE_ONLY') for c in claims)
        assert db.execute('SELECT count(*) FROM current_views').fetchone()[0] == 0
    save('operator-receipt.json', result)
    save('canonical-readback.json', claims)
    save('chain-receipt.json', {'status': 'SYNTHETIC_CHAIN_PASS', 'provider_calls': 0,
        'real_human_authorizations': 0, 'production_writes': 0, 'canonical_claims': len(claims),
        'duplicate_child_observations_retained': 6, 'repeat_increment': 0,
        'windows_integrity': 'SIMULATED_POSITIVE_WITH_NEGATIVE_GUARD_TEST',
        'real_b1_production_qualification': False})


def select_document(value, document):
    from pro_a.workbench.candidate_lifecycle import RevisionLifecycle, _required
    lifecycle = RevisionLifecycle(value['config'])
    for i, ref in enumerate(_required([document])):
        state = lifecycle.read(ref)
        if state['current_revision'] is None:
            lifecycle.decide('SELECT', ref, expected_head=state['head_sha256'],
                identity={'actor':'TEST_FIXTURE_HUMAN','session_id':'TEST_FIXTURE_SESSION','principal_type':'HUMAN_USER'},
                reason='TEST FIXTURE explicit initial selection', idempotency_key='test-select-'+str(i).zfill(8), confirm=True)
