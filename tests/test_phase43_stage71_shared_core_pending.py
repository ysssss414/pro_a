"""Stage 7.1 pending-domain processing on disposable schema 11 fixtures."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from pro_a.cloud_contract import DeterministicFakeProvider
from pro_a.processing_context import validate_context
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.domains import Domains, prepare_domains
from pro_a.workbench.lifecycle_closure import prepare_stage6_lifecycle
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.source_operations import SourceOperationError
from pro_a.workbench.stage1_scale import Stage1ReviewProjection, prepare_stage1_scale, stage1_capacity
from pro_a.workbench.store import Store
from test_phase43_stage7_community import COMPANY, bundle
from test_workbench_stage7 import clean_pdf, upload
from workbench_stage7_fixture import stage7_fixture


def case(tmp_path):
    value = stage7_fixture(tmp_path)
    prepare_domains(value['config'])
    prepare_stage1_scale(value['config'])
    prepare_stage6_lifecycle(value['config'])
    return value


def finish(value, run_id):
    provider = DeterministicFakeProvider()
    for _ in range(3):
        result = value['service'].advance_once(worker_id='stage71-fake', provider=provider,
                                               processing_run_id=run_id)
    assert result['state'] == 'HUMAN_REVIEW_REQUIRED'
    assert provider.call_count == 2
    return result


def test_generic_pending_packet_and_later_assignment_are_immutable(tmp_path):
    value = case(tmp_path)
    source = upload(value, clean_pdf(tmp_path))
    service = value['service']
    run_id = service.start(source['source_id'], idempotency_key='stage71-generic-pending-0001')['run']['processing_run_id']
    context = Domains(value['config']).read(run_id)
    assert context['contract_version'] == 'run-processing-context-v2'
    assert context['basis']['processing_scope']['mode'] == 'SHARED_CORE_PENDING'
    assert context['basis']['processing_scope']['primary_domain'] is None
    assert context['basis']['processing_scope']['packs'] == []
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM domain_pack_registry').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM domain_assignments').fetchone()[0] == 0
        assert connection.execute('SELECT domain_context_required FROM source_processing_runs WHERE processing_run_id=?',
                                  (run_id,)).fetchone()[0] == 1
    final = finish(value, run_id)
    packet_id = final['packet_artifact_id']
    packet_before = ReviewWorkbench(value['config']).read(packet_id)
    assert packet_before['processing_scope_mode'] == 'SHARED_CORE'
    assert packet_before['domain_assignment_status'] == 'PENDING'
    assert Stage1ReviewProjection(value['config']).rebuild(packet_id)['artifact_id'] == packet_id
    with Store(value['config']).connect() as connection:
        assert stage1_capacity(connection)['operational_pending_review_rows'] > 0
    pack = Domains(value['config']).register(Path(__file__).resolve().parents[1] / 'domains/ai_hardware')
    Domains(value['config']).assign('Source', source['source_id'], primary_domain='ai_hardware', packs=[pack],
                                   actor='operator', reason='Later explicit assignment', expected_revision=0)
    assert Domains(value['config']).read(run_id) == context
    assert Domains(value['config']).guard(run_id, service.jobs, value['source_profile'])
    assert service.get_run(run_id)['processing_scope_mode'] == 'SHARED_CORE'
    assert ReviewWorkbench(value['config']).read(packet_id) == packet_before
    Stage1ReviewProjection(value['config']).rebuild(packet_id)
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM stage1_review_projection_domains WHERE artifact_id=?',
                                  (packet_id,)).fetchone()[0] == 0
    with pytest.raises(SourceOperationError, match='REPROCESS_REASON'):
        service.start(source['source_id'], idempotency_key='stage71-assigned-reprocess-0001')
    next_run = service.start(source['source_id'], idempotency_key='stage71-assigned-reprocess-0001',
                             reprocess_reason='Explicit Domain reprocessing')['run']
    assert next_run['processing_run_id'] != run_id
    assert Domains(value['config']).read(next_run['processing_run_id'])['contract_version'] == 'run-domain-context-v1'
    assert Domains(value['config']).read(run_id) == context


@pytest.mark.parametrize('change', ['domain', 'packs', 'status', 'mode', 'identity', 'prompt', 'runtime',
                                    'config', 'model', 'source'])
def test_pending_context_rejects_corruption(tmp_path, change):
    value = case(tmp_path)
    source = upload(value, clean_pdf(tmp_path))
    run_id = value['service'].start(source['source_id'], idempotency_key='stage71-context-0001')['run']['processing_run_id']
    context = deepcopy(Domains(value['config']).read(run_id))
    basis = context['basis']
    if change == 'domain': basis['processing_scope']['primary_domain'] = 'ai_hardware'
    elif change == 'packs': basis['processing_scope']['packs'] = [{'domain_id': 'ai_hardware'}]
    elif change == 'status': basis['processing_scope']['domain_assignment_status'] = 'ASSIGNED'
    elif change == 'mode': basis['processing_scope']['mode'] = 'DOMAIN_ASSIGNED'
    elif change == 'identity': basis['processing_scope']['shared_core_sha256'] = '0' * 64
    elif change == 'prompt': basis['prompt_sha256'] = '0' * 64
    elif change == 'runtime': basis['runtime']['git_sha'] = '0' * 40
    elif change == 'config': basis['config_sha256'] = '0' * 64
    elif change == 'model': basis['model_configuration']['requested_model'] = 'wrong'
    elif change == 'source': basis['source_sha256'] = '0' * 64
    with pytest.raises(BoundaryError):
        validate_context(context)


def test_community_pending_without_registered_domain(tmp_path):
    value = case(tmp_path)
    with sqlite3.connect(value['config'].knowledge_db) as connection:
        connection.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
                           "VALUES(?, 'Synthetic Company', 'Company', 'Synthetic', 'active', '2026-09-23', '2026-09-23')",
                           (COMPANY,))
    from pro_a.community_material import import_bundle, preview
    raw = bundle()
    summary = preview(value['config'], raw, COMPANY)
    assert summary['processing_scope'] == {'mode': 'SHARED_CORE_PENDING', 'domain_assignment_status': 'PENDING'}
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM private_sources').fetchone()[0] == 0
    first = asyncio.run(import_bundle(value['service'], raw, COMPANY, None, 'operator'))
    second = asyncio.run(import_bundle(value['service'], raw, COMPANY, None, 'operator'))
    assert second['duplicate'] is True
    assert second['run']['processing_run_id'] == first['run']['processing_run_id']
    run_id = first['run']['processing_run_id']
    assert first['run']['processing_scope_mode'] == 'SHARED_CORE'
    assert first['run']['company_material_intent']['material_trust_policy'] == 'LOW_TRUST_CLUE_ONLY'
    assert [row['event_type'] for row in value['service'].events(run_id)['items'][:3]] == [
        'KNOWLEDGE_COMMUNITY_BUNDLE_BOUND', 'COMPANY_MATERIAL_INTENT_BOUND', 'PROCESSING_QUEUED']
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM domain_pack_registry').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM domain_assignments').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM private_sources').fetchone()[0] == 1
        assert connection.execute('SELECT COUNT(*) FROM source_processing_runs').fetchone()[0] == 1
    final = finish(value, run_id)
    assert ReviewWorkbench(value['config']).read(final['packet_artifact_id'])['domain_assignment_status'] == 'PENDING'


def test_community_http_preview_and_import_without_domain_header(tmp_path, monkeypatch):
    value = case(tmp_path)
    with sqlite3.connect(value['config'].knowledge_db) as connection:
        connection.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
                           "VALUES(?, 'Synthetic Company', 'Company', 'Synthetic', 'active', '2026-09-23', '2026-09-23')",
                           (COMPANY,))
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', 's' * 40)
    app = create_app(value['config'], cloud_profile=value['cloud_profile'], source_profile=value['source_profile'])
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 1)) as client:
        csrf = client.post(PREFIX + '/session', json={'token': 's' * 40},
                           headers={'origin': value['config'].origin}).json()['csrf_token']
        headers = {'origin': value['config'].origin, 'x-csrf-token': csrf,
                   'content-type': 'application/zip', 'x-company-node-id': COMPANY}
        assert client.get(PREFIX + '/source-operations/community-domains').json()['items'] == []
        inspected = client.post(PREFIX + '/source-operations/community-preview', content=bundle(), headers=headers)
        assert inspected.status_code == 200
        assert inspected.json()['processing_scope']['mode'] == 'SHARED_CORE_PENDING'
        with Store(value['config']).connect() as connection:
            assert connection.execute('SELECT COUNT(*) FROM private_sources').fetchone()[0] == 0
        imported = client.post(PREFIX + '/source-operations/community-import', content=bundle(), headers=headers)
        assert imported.status_code == 200, imported.text
        assert imported.json()['run']['processing_scope_mode'] == 'SHARED_CORE'


def test_v2_allows_shaped_non_network_provider_but_v1_stays_blocked(tmp_path):
    value = case(tmp_path)
    source = upload(value, clean_pdf(tmp_path))
    run_id = value['service'].start(source['source_id'], idempotency_key='stage71-provider-0001')['run']['processing_run_id']
    fake = DeterministicFakeProvider()
    first = value['service'].advance_once(worker_id='stage71-provider', provider=fake, processing_run_id=run_id)

    class ShapedProvider:
        provider_identity = fake.provider_identity
        adapter_version = fake.adapter_version

        def invoke(self, request):
            return fake.invoke(request)

    result = value['service'].jobs.run_once(ShapedProvider(), worker_id='stage71-provider',
                                            job_id=first['jobs'][0]['job_id'])
    assert result['status'] == 'SUCCEEDED'
    assert fake.call_count == 1
    pack = Domains(value['config']).register(Path(__file__).resolve().parents[1] / 'domains/ai_hardware')
    assigned_source = upload(value, clean_pdf(tmp_path, name='assigned.pdf', text='Different synthetic Source evidence.'))
    Domains(value['config']).assign('Source', assigned_source['source_id'], primary_domain='ai_hardware', packs=[pack],
                                   actor='operator', reason='Explicit Domain', expected_revision=0)
    assigned = value['service'].start(assigned_source['source_id'],
                                       idempotency_key='stage71-provider-v1-0001')['run']['processing_run_id']
    queued = value['service'].advance_once(worker_id='stage71-provider', provider=fake, processing_run_id=assigned)
    blocked = value['service'].jobs.run_once(ShapedProvider(), worker_id='stage71-provider',
                                             job_id=queued['jobs'][0]['job_id'])
    assert blocked['status'] != 'SUCCEEDED'
    assert 'DOMAIN_ACTIVATION_REQUIRED' in str(blocked)
