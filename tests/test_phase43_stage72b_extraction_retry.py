"""Same-Run recovery qualification: disposable Sources, databases and doubles."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3
import stat
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from pro_a.cloud_contract import DeterministicFakeProvider, ProviderFailure
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.domains import Domains
from pro_a.workbench.extraction_retry import prepare_extraction_retries
from pro_a.workbench.source_operations import SourceOperations, SourceOperationError
from pro_a.workbench.store import Store
from test_phase43_stage71_shared_core_pending import case
from test_workbench_stage7 import clean_pdf, upload


class Failure:
    provider_identity = 'DETERMINISTIC_FAKE'
    adapter_version = 'deterministic-fake-v1'

    def __init__(self, retryable=False):
        self.calls = []
        self.retryable = retryable

    def invoke(self, request):
        self.calls.append(request)
        raise ProviderFailure('PROVIDER_ERROR', external_outcome='KNOWN_FAILURE', retryable=self.retryable,
                              diagnostic={'failure_stage': 'HTTP_RESPONSE', 'error_class': 'HTTP_503',
                                          'http_status': 503, 'provider_request_id': 'req-stage72b-503'})


def failed(tmp_path):
    from legacy_source_fixture import historical_case
    return historical_case(tmp_path)


def retry(value, key='stage72b-retry-command-001', attempt=None, reason='Explicit synthetic extraction retry'):
    return value['service'].retry_failed_extraction(value['run_id'], attempt or value['attempt_id'],
                                                    retry_reason=reason, idempotency_key=key)


def original_rows(value):
    with Store(value['config']).connect() as c:
        return {table: [tuple(r) for r in c.execute('SELECT * FROM ' + table + ' WHERE ' + where, (ident,))]
                for table, where, ident in (
                    ('cloud_jobs', 'job_id=?', value['job_id']),
                    ('cloud_job_events', 'job_id=? ORDER BY sequence', value['job_id']),
                    ('cloud_attempts', 'attempt_id=?', value['attempt_id']),
                    ('cloud_attempt_dispatches', 'attempt_id=?', value['attempt_id']),
                    ('cloud_attempt_outcomes', 'attempt_id=?', value['attempt_id']))}


def test_success_same_run_context_history_and_no_acquisition_routing(tmp_path, monkeypatch):
    value = failed(tmp_path)
    service = value['service']
    old = original_rows(value)
    context = Domains(value['config']).read(value['run_id'])
    events = service.events(value['run_id'])['items']
    forbidden_calls = []

    def forbidden(*args, **kwargs):
        forbidden_calls.append(True)
        raise AssertionError('Acquisition/routing/source registration must not repeat')

    monkeypatch.setattr(service, 'upload', forbidden)
    monkeypatch.setattr('pro_a.workbench.source_operations.start_execution', forbidden)
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)
    with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value)
    assert service.get_run(value['run_id'])['state']=='FAILED'
    provider = DeterministicFakeProvider()
    assert service.advance_once(worker_id='synthetic-stage72b',processing_run_id=value['run_id'],provider=provider) is None
    final=service.get_run(value['run_id'])
    assert final['packet_artifact_id'] is None
    assert len(final['jobs'])==1 and final['usage']['attempts']==1
    listed = service.list()['items'][0]
    assert listed['latest_run']['usage']['attempts']==1 and provider.call_count==0
    assert forbidden_calls == []
    assert Domains(value['config']).read(value['run_id']) == context
    assert original_rows(value) == old
    assert service.events(value['run_id'])['items']==events
    with Store(value['config']).connect() as c:
        assert c.execute('SELECT count(*) FROM source_processing_runs').fetchone()[0] == 1
        assert c.execute('SELECT count(*) FROM private_sources').fetchone()[0] == 1
        assert c.execute('SELECT count(*) FROM extraction_retries').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM cloud_attempts').fetchone()[0]==1


def test_failure_diagnostics_no_auto_retry_and_retry_of_retry(tmp_path):
    value = failed(tmp_path)
    before = original_rows(value)
    provider = Failure(retryable=True)
    for key in ('stage72b-retry-command-001','stage72b-retry-command-002'):
        with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
            retry(value,key=key)
    assert value['service'].advance_once(worker_id='synthetic-stage72b',processing_run_id=value['run_id'],provider=provider) is None
    final=value['service'].get_run(value['run_id'])
    assert final['state'] == 'FAILED'
    assert provider.calls==[]
    job = value['service'].jobs.get(value['job_id'])
    diagnostic = job['failure_diagnostic']
    assert diagnostic['failure_stage'] == 'HTTP_RESPONSE'
    assert diagnostic['http_status'] == 503 and diagnostic['retryable'] is False
    assert diagnostic['error_class'] == 'HTTP_503'
    assert diagnostic['provider_request_id'] == 'req-stage72b-503'
    assert diagnostic['error_fingerprint'] and diagnostic['safe_error_summary']
    assert diagnostic['attempt_number'] == 1
    assert original_rows(value) == before


def test_duplicate_and_active_guard(tmp_path):
    value = failed(tmp_path)
    for _ in range(2):
        with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
            retry(value)
    with pytest.raises(SourceOperationError, match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value, key='stage72b-different-key-001')
    with pytest.raises(SourceOperationError, match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value, reason='Different operator intent')
    with Store(value['config']).connect() as c:
        assert c.execute('SELECT count(*) FROM extraction_retries').fetchone()[0] == 0
        assert c.execute('SELECT count(*) FROM cloud_jobs').fetchone()[0] == 1


@pytest.mark.parametrize('same_key', [True, False])
def test_concurrent_commands_allocate_once(tmp_path, same_key):
    value = failed(tmp_path)
    barrier = Barrier(2)

    def submit(index):
        barrier.wait()
        try:
            return retry(value, key=f'stage72b-concurrency-{0 if same_key else index:03}')
        except SourceOperationError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert results==['RETRY_RUNTIME_INCOMPATIBLE']*2
    with Store(value['config']).connect() as c:
        assert c.execute('SELECT count(*) FROM extraction_retries').fetchone()[0] == 0
        assert c.execute('SELECT count(*) FROM cloud_jobs').fetchone()[0] == 1


@pytest.mark.parametrize('reason', ['', ' ', ' x ', 'x' * 1001, 'a\r\nAuthorization: secret', '<script>x</script>', 'api_key=sk-secretvalue'])
def test_invalid_reason_rejected(tmp_path, reason):
    value = failed(tmp_path)
    with pytest.raises(SourceOperationError, match='INVALID_RETRY_REASON'):
        retry(value, reason=reason)


@pytest.mark.parametrize('state,stage,error', [('HUMAN_REVIEW_REQUIRED', 'HUMAN_REVIEW', None),
                                              ('FAILED', 'SOURCE_ACQUISITION', 'PROVIDER_ERROR'),
                                              ('FAILED', 'EXTRACTION_JOBS', 'SECURITY_FAILURE'),
                                              ('FAILED', 'RUN_CONTEXT', 'PROVIDER_ERROR'),
                                              ('BLOCKED', 'EXTRACTION_JOBS', None)])
def test_unsupported_run_states_rejected(tmp_path, state, stage, error):
    value = failed(tmp_path)
    with Store(value['config']).connect(operator_write=True) as c:
        c.execute('UPDATE source_processing_runs SET state=?,stage=?,error_code=? WHERE processing_run_id=?', (state, stage, error, value['run_id']))
    with pytest.raises(SourceOperationError, match='RETRY_NOT_ELIGIBLE'):
        retry(value)


def test_frozen_cloud_configuration_and_later_domain_assignment(tmp_path):
    value = failed(tmp_path)
    context = Domains(value['config']).read(value['run_id'])
    pack = Domains(value['config']).register(Path(__file__).resolve().parents[1] / 'domains/ai_hardware')
    Domains(value['config']).assign('Source', value['source']['source_id'], primary_domain='ai_hardware', packs=[pack],
                                   actor='operator', reason='Later synthetic assignment', expected_revision=0)
    old=original_rows(value)
    changed = replace(value['cloud_profile'], requested_model='different-model', timeout_seconds=1)
    value['service'] = SourceOperations(value['config'], value['source_profile'], changed)
    with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value)
    provider = Failure(True)
    value['service'].advance_once(worker_id='synthetic-stage72b', processing_run_id=value['run_id'], provider=provider)
    assert provider.calls==[] and original_rows(value)==old
    assert Domains(value['config']).read(value['run_id']) == context


def test_missing_frozen_configuration_fails_closed(tmp_path):
    value = failed(tmp_path)
    value['phase4_config'].write_text(value['phase4_config'].read_text().replace('max_output_tokens = 8192', 'max_output_tokens = 4096'))
    with pytest.raises(SourceOperationError, match='RETRY_FROZEN_CONFIG_INCOMPLETE'):
        retry(value)
    with Store(value['config']).connect() as c:
        assert c.execute('SELECT count(*) FROM extraction_retries').fetchone()[0] == 0


def test_retry_and_reprocess_are_separate(tmp_path):
    value = failed(tmp_path)
    with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value)
    with pytest.raises(SourceOperationError,match='BOUNDED_SCHEMA_REQUIRED'):
        value['service'].start(value['source']['source_id'],idempotency_key='stage72b-reprocess-command',reprocess_reason='Explicit reprocess')
    from pro_a.workbench.bounded_extraction_persistence import prepare_bounded_extraction_persistence
    prepare_bounded_extraction_persistence(value['config'])
    new = value['service'].start(value['source']['source_id'], idempotency_key='stage72b-reprocess-command', reprocess_reason='Explicit reprocess')['run']
    assert new['processing_run_id'] != value['run_id']
    assert new['runtime_identity']['whole_piece_compact']


def test_schema_additive_idempotent_and_lineage_append_only(tmp_path):
    from legacy_source_fixture import historical_case
    value=historical_case(tmp_path,'lineage')
    old = original_rows(value)
    assert prepare_extraction_retries(value['config'])['status'] == 'ALREADY_PREPARED'
    with pytest.raises(SourceOperationError,match='RETRY_ALREADY_IN_PROGRESS'):
        retry(value)
    assert original_rows(value) == old
    with Store(value['config']).connect(operator_write=True) as c:
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        with pytest.raises(sqlite3.IntegrityError, match='APPEND_ONLY'):
            c.execute("UPDATE extraction_retries SET retry_reason='changed'")
        with pytest.raises(sqlite3.IntegrityError, match='APPEND_ONLY'):
            c.execute('DELETE FROM extraction_retries')


def test_api_explicit_auth_csrf_and_no_overrides(tmp_path, monkeypatch):
    value = failed(tmp_path)
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', 's' * 40)
    app = create_app(value['config'], cloud_profile=value['cloud_profile'], source_profile=value['source_profile'])
    path = PREFIX + f"/source-operations/runs/{value['run_id']}/attempts/{value['attempt_id']}/retry"
    body = {'retry_reason': 'Explicit API retry', 'idempotency_key': 'stage72b-http-retry-001'}
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 1)) as client:
        assert client.post(path, json=body).status_code in (401, 403)
        csrf = client.post(PREFIX + '/session', json={'token': 's' * 40}, headers={'origin': value['config'].origin}).json()['csrf_token']
        headers = {'origin': value['config'].origin, 'x-csrf-token': csrf}
        for field in ('provider', 'model', 'prompt', 'domain', 'run_context', 'source'):
            assert client.post(path, json={**body, field: 'override'}, headers=headers).status_code == 422
        a = client.post(path, json=body, headers=headers)
        b = client.post(path, json=body, headers=headers)
        assert a.status_code == b.status_code == 409, a.text
        assert a.json()==b.json()
        assert not client.get(PREFIX + f"/source-operations/runs/{value['run_id']}").json()['extraction_retries']
    with Store(value['config']).connect() as c:
        assert c.execute('SELECT count(*) FROM cloud_attempt_dispatches').fetchone()[0] == 1  # original only


def test_other_run_attempt_and_active_job_rejected(tmp_path):
    value = failed(tmp_path)
    with pytest.raises(SourceOperationError, match='PROCESSING_RUN_NOT_FOUND'):
        value['service'].retry_failed_extraction('SOURCE_RUN_MISSING', value['attempt_id'],
                                                 retry_reason='Explicit retry', idempotency_key='stage72b-wrong-run-001')
    with Store(value['config']).connect(operator_write=True) as c:
        c.execute("UPDATE cloud_jobs SET state='RUNNING' WHERE job_id=?", (value['job_id'],))
    with pytest.raises(SourceOperationError, match='RETRY_ALREADY_IN_PROGRESS'):
        retry(value)


def test_direct_worker_uses_frozen_profile_and_blocks_source_drift(tmp_path):
    value = failed(tmp_path)
    from pro_a.workbench.retry_compatibility import prepare_retry_compatibility,assess_retry_compatibility
    prepare_retry_compatibility(value['config'])
    with Store(value['config']).connect() as c:
        relative = c.execute('SELECT storage_relative FROM private_sources').fetchone()[0]
    synthetic_source = value['config'].artifact_root / relative
    synthetic_source.chmod(stat.S_IWRITE | stat.S_IREAD)
    synthetic_source.write_bytes(b'changed synthetic source')
    provider = Failure()
    final=assess_retry_compatibility(value['config'],value['run_id'],value['attempt_id'],persist=False)
    assert final['status']=='BLOCKED' and 'BLOCKED_SOURCE_IDENTITY_CHANGED' in final['blockers']
    assert value['service'].jobs.run_once(provider,worker_id='synthetic-stage72b',job_id=value['job_id']) is None
    assert provider.calls == []


def test_runtime_drift_is_not_silently_overridden(tmp_path, monkeypatch):
    value = failed(tmp_path)
    from pro_a.workbench.cloud_jobs import CloudJobs
    original = CloudJobs.current_runtime

    def drift(self):
        runtime = dict(original(self))
        runtime['git_sha'] = '0' * 40
        from pro_a.cloud_contract import digest
        runtime['runtime_sha256'] = digest({k: v for k, v in runtime.items() if k != 'runtime_sha256'})
        return runtime

    monkeypatch.setattr(CloudJobs, 'current_runtime', drift)
    with pytest.raises(SourceOperationError, match='RETRY_FROZEN_CONFIG_INCOMPLETE|RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value)
    with Store(value['config']).connect() as c:
        assert c.execute('SELECT count(*) FROM extraction_retries').fetchone()[0] == 0
