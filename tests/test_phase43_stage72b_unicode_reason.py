"""Unicode single-line retry reasons: real service/API, disposable state only."""
import pytest
from fastapi.testclient import TestClient

from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.source_operations import SourceOperationError
from pro_a.workbench.store import Store
from test_phase43_stage72b_extraction_retry import failed, retry


# All C0 controls and DEL retain their existing rejection. NEL/LS/PS cover
# Unicode line boundaries outside ASCII; standalone/trailing cases matter too.
INVALID_REASONS = (
    *('a' + chr(code) + 'b' for code in (*range(32), 127, 0x85, 0x2028, 0x2029)),
    '\u0085', '\u2028', '\u2029', 'a\u0085', 'a\u2028', 'a\u2029',
    'a\r\nb', ' leading', 'trailing ', '\u3000reason', 'reason\u3000',
    '<reason>', 'Bearer synthetic-secret', 'api_key=synthetic-secret',
    'token=synthetic-secret', 'cookie=synthetic-secret', 'authorization=synthetic-secret',
)
VALID_REASONS = (
    'Stage 7.2 retry after diagnostics release',
    '诊断能力发布后执行一次显式重试',
    '中文 + English 123',
    '1234567890',
    'Retry: diagnostics ready; explicit command (1).',
    '诊断完成，执行重试；请核验（第１次）。',
    '诊断\u3000完成 ✅',
    '重' * 1000,
)


def retry_state(value):
    with Store(value['config']).connect() as connection:
        return {table: [tuple(row) for row in connection.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
                for table in ('source_processing_runs', 'cloud_jobs', 'cloud_attempts',
                              'extraction_retries', 'source_processing_events', 'cloud_job_events',
                              'cloud_attempt_dispatches', 'cloud_attempt_outcomes')}


def test_service_invalid_reason_matrix_has_no_writes(tmp_path):
    value = failed(tmp_path)
    before = retry_state(value)
    for reason in (*INVALID_REASONS, '', 'x' * 1001):
        with pytest.raises(SourceOperationError, match='^INVALID_RETRY_REASON$') as error:
            retry(value, reason=reason)
        assert error.value.status == 422
        assert retry_state(value) == before, repr(reason)


def test_api_invalid_reason_matrix_has_no_writes(tmp_path, monkeypatch):
    value = failed(tmp_path)
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', 's' * 40)
    app = create_app(value['config'], cloud_profile=value['cloud_profile'], source_profile=value['source_profile'])
    path = PREFIX + f"/source-operations/runs/{value['run_id']}/attempts/{value['attempt_id']}/retry"
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 1)) as client:
        csrf = client.post(PREFIX + '/session', json={'token': 's' * 40},
                           headers={'origin': value['config'].origin}).json()['csrf_token']
        headers = {'origin': value['config'].origin, 'x-csrf-token': csrf}
        before = retry_state(value)
        for reason in INVALID_REASONS:
            response = client.post(path, json={'retry_reason': reason, 'idempotency_key': 'stage72b-r1-invalid-reason'}, headers=headers)
            assert response.status_code == 422, repr(reason)
            assert response.json() == {'detail': 'INVALID_RETRY_REASON'}, repr(reason)
            assert retry_state(value) == before, repr(reason)
        # Pydantic's existing min/max boundary remains unchanged.
        for reason in ('', 'x' * 1001):
            response = client.post(path, json={'retry_reason': reason, 'idempotency_key': 'stage72b-r1-invalid-reason'}, headers=headers)
            assert response.status_code == 422
            assert retry_state(value) == before


@pytest.mark.parametrize('reason', VALID_REASONS, ids=['english', 'chinese', 'mixed', 'digits', 'punctuation', 'fullwidth', 'space-emoji', 'max-length'])
def test_valid_unicode_reason_preserved(tmp_path, monkeypatch, reason):
    value = failed(tmp_path)
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', 's' * 40)
    app = create_app(value['config'], cloud_profile=value['cloud_profile'], source_profile=value['source_profile'])
    path = PREFIX + f"/source-operations/runs/{value['run_id']}/attempts/{value['attempt_id']}/retry"
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 1)) as client:
        csrf = client.post(PREFIX + '/session', json={'token': 's' * 40},
                           headers={'origin': value['config'].origin}).json()['csrf_token']
        response = client.post(path, json={'retry_reason': reason, 'idempotency_key': 'stage72b-r1-valid-reason'},
                               headers={'origin': value['config'].origin, 'x-csrf-token': csrf})
        assert response.status_code == 200
        accepted = response.json()
    assert accepted['retry']['retry_reason'] == reason
    duplicate = retry(value, key='stage72b-r1-valid-reason', reason=reason)
    assert duplicate['duplicate'] and duplicate['retry'] == accepted['retry']
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT retry_reason FROM extraction_retries').fetchone()[0] == reason
        assert connection.execute('SELECT count(*) FROM source_processing_runs').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM cloud_attempt_dispatches').fetchone()[0] == 1  # Original fake failure only.
