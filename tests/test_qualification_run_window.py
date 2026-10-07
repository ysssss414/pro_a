"""Qualification-only intake control on disposable schema12 fixtures."""
from concurrent.futures import ThreadPoolExecutor
import ast
import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from pro_a.workbench.api import PREFIX, SourceProcessRequest, create_app
from pro_a.workbench.source_operations import SourceOperationError, SourceOperations
from pro_a.workbench.stage1_scale import LIMITS, STAGE1_POLICY_VERSION, set_stage1_intake, stage1_capacity
from pro_a.workbench.store import Store
from test_phase43_stage71_shared_core_pending import case
from test_workbench_stage7 import clean_pdf, upload

REPROCESS = 'Explicit synthetic qualification reprocessing'
REASON = 'Synthetic bounded-extraction operator qualification'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))


@pytest.fixture
def full_window(tmp_path):
    value = case(tmp_path)
    source = upload(value, clean_pdf(tmp_path))
    for index in range(3):
        run = value['service'].start(source['source_id'], idempotency_key=f'qualification-window-seed-{index}',
                                     reprocess_reason=REPROCESS)['run']
        value['service']._transition(run['processing_run_id'], 'BLOCKED', 'SYNTHETIC_QUALIFICATION')
    value['source_id'] = source['source_id']
    return value


def qualify(value, key='qualification-window-explicit-0001', **changes):
    kwargs = {'idempotency_key': key, 'reprocess_reason': REPROCESS, 'qualification_reason': REASON}
    kwargs.update(changes)
    return value['service'].start_qualification_reprocess(value['source_id'], **kwargs)


def bypasses(value):
    with Store(value['config']).connect() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM source_processing_events WHERE event_type='STAGE1_RUN_WINDOW_BYPASS'")]


def test_normal_start_still_enforces_three_per_24h(full_window):
    with pytest.raises(SourceOperationError, match='STAGE1_RUN_WINDOW_LIMIT'):
        full_window['service'].start(full_window['source_id'], idempotency_key='ordinary-window-reprocess-0001',
                                     reprocess_reason=REPROCESS)
    assert LIMITS.runs_per_24h == 3
    assert not bypasses(full_window)


def test_http_process_still_blocks_and_rejects_override_fields(full_window, monkeypatch):
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', 't' * 40)
    app = create_app(full_window['config'], cloud_profile=full_window['cloud_profile'],
                     source_profile=full_window['source_profile'])
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 1)) as client:
        login = client.post(PREFIX + '/session', json={'token': 't' * 40},
                            headers={'origin': full_window['config'].origin})
        headers = {'origin': full_window['config'].origin, 'x-csrf-token': login.json()['csrf_token']}
        body = {'idempotency_key': 'http-window-reprocess-0001', 'reprocess_reason': REPROCESS}
        url = f"{PREFIX}/source-operations/{full_window['source_id']}/process"
        response = client.post(url, json=body, headers=headers)
        assert response.status_code == 409 and response.json()['detail'] == 'STAGE1_RUN_WINDOW_LIMIT'
        for name in ('bypass_run_window', 'qualification_reason', 'ignore_limits', 'force'):
            assert client.post(url, json={**body, name: True}, headers=headers).status_code == 422
    assert not bypasses(full_window)


def test_qualification_creates_atomic_durable_event_without_changing_projection(full_window):
    result = qualify(full_window)
    assert result['duplicate'] is False and result['run']['state'] == 'QUEUED'
    event, = bypasses(full_window)
    body = json.loads(event['event_json'])
    assert body == {'processing_run_id': result['run']['processing_run_id'], 'source_id': full_window['source_id'],
                    'reason': REASON, 'policy_version': STAGE1_POLICY_VERSION, 'normal_limit': 3,
                    'runs_last_24h_at_creation': 3, 'bypass_scope': 'RUN_WINDOW_ONLY',
                    'created_at': result['run']['created_at'], 'created_under_qualification_window_bypass': True}
    with Store(full_window['config']).connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity['runs_last_24h'] == 4 and capacity['new_intake_allowed'] is False
        assert connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == '12'
        assert connection.execute('SELECT count(*) FROM source_processing_jobs').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM bounded_extraction_attempts').fetchone()[0] == 0
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()


def test_paused_intake_still_blocks_qualification(full_window):
    set_stage1_intake(full_window['config'], paused=True, reason='Synthetic operator pause')
    with pytest.raises(SourceOperationError, match='STAGE1_INTAKE_PAUSED'):
        qualify(full_window)
    assert not bypasses(full_window)


@pytest.mark.parametrize('change,error', [
    ({'wip_state': 'HARD_STOP'}, 'STAGE1_REVIEW_WIP_HARD_LIMIT'),
    ({'unprojected_review_packets': 1}, 'STAGE1_REVIEW_PROJECTION_INCOMPLETE'),
])
def test_other_capacity_guards_still_block(full_window, monkeypatch, change, error):
    original = stage1_capacity
    monkeypatch.setattr('pro_a.workbench.stage1_scale.stage1_capacity',
                        lambda connection: {**original(connection), **change})
    with pytest.raises(SourceOperationError, match=error):
        qualify(full_window)
    assert not bypasses(full_window)


@pytest.mark.parametrize('reason', ['', ' ', ' leading', 'trailing ', 'x' * 1001, 'line\nbreak', '\x00'])
def test_invalid_qualification_reason_rejected(full_window, reason):
    with pytest.raises(SourceOperationError, match='INVALID_QUALIFICATION_REASON'):
        qualify(full_window, qualification_reason=reason)
    assert not bypasses(full_window)


def test_explicit_reprocess_and_existing_history_required(tmp_path):
    value = case(tmp_path)
    value['source_id'] = 'SRC_NOT_REGISTERED'
    with pytest.raises(SourceOperationError, match='SOURCE_NOT_FOUND'):
        qualify(value)
    value['source_id'] = upload(value, clean_pdf(tmp_path))['source_id']
    with pytest.raises(SourceOperationError, match='QUALIFICATION_REPROCESS_REASON_REQUIRED'):
        qualify(value, reprocess_reason='')
    with pytest.raises(SourceOperationError, match='QUALIFICATION_REPROCESS_HISTORY_REQUIRED'):
        qualify(value)
    assert not bypasses(value)


def test_idempotent_replay_is_same_run_and_no_duplicate_event(full_window):
    first = qualify(full_window)
    second = qualify(full_window)
    assert second['duplicate'] and first['run']['processing_run_id'] == second['run']['processing_run_id']
    assert len(bypasses(full_window)) == 1
    with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'):
        qualify(full_window, qualification_reason='Different operator reason')


def test_concurrent_distinct_keys_preserve_existing_source_duplicate_invariant(full_window):
    def start(index):
        return qualify(full_window, key=f'qualification-concurrent-start-{index}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, range(2)))
    assert len({result['run']['processing_run_id'] for result in results}) == 1
    assert sorted(result['duplicate'] for result in results) == [False, True]
    assert len(bypasses(full_window)) == 1


def test_qualification_audit_failure_rolls_back_run(full_window, monkeypatch):
    original = full_window['service']._event
    def fail_audit(connection, run_id, event_type, payload=None):
        if event_type == 'STAGE1_RUN_WINDOW_BYPASS':
            raise RuntimeError('SYNTHETIC_AUDIT_FAILURE')
        return original(connection, run_id, event_type, payload)
    monkeypatch.setattr(full_window['service'], '_event', fail_audit)
    with pytest.raises(RuntimeError, match='SYNTHETIC_AUDIT_FAILURE'):
        qualify(full_window)
    with Store(full_window['config']).connect() as connection:
        assert connection.execute('SELECT count(*) FROM source_processing_runs').fetchone()[0] == 3
    assert not bypasses(full_window)


def test_no_public_api_frontend_or_mcp_override_exposure():
    assert 'bypass_run_window' not in inspect.signature(SourceOperations.start).parameters
    assert 'qualification_reason' not in SourceProcessRequest.model_fields
    root = Path(__file__).resolve().parents[1]
    public = [root / 'src/pro_a/workbench/api.py']
    public += list((root / 'src/pro_a/mcp').rglob('*.py'))
    for directory in ('frontend', 'web', 'ui'):
        public += [p for p in (root / directory).rglob('*') if p.is_file()]
    for path in public:
        text = path.read_text(encoding='utf-8')
        assert not any(name in text for name in ('bypass_run_window', 'start_qualification_reprocess', 'qualification_reason'))


def test_creation_dependencies_and_intake_guard_are_closed_and_bound():
    from pro_a.workbench import retry_compatibility as compatibility
    package = Path(compatibility.__file__).resolve().parent.parent
    specification = compatibility._CLOUD_EXECUTION_SURFACE
    assert specification['workbench/stage1_scale.py'] is None
    assert {'SourceOperations._start', 'SourceOperations.start_qualification_reprocess'} <= set(
        specification['workbench/source_operations.py'])
    sources = {name: (package / name).read_bytes() for name in specification}
    original = compatibility._surface_manifest(sources, specification)
    for name, marker in [('workbench/source_operations.py', b'INVALID_QUALIFICATION_REASON'),
                         ('workbench/stage1_scale.py', b'STAGE1_RUN_WINDOW_LIMIT')]:
        assert sources[name].count(marker) == 1
        changed = {**sources, name: sources[name].replace(marker, marker + b'_MUTATION', 1)}
        assert compatibility._surface_manifest(changed, specification)['semantic_surface_sha256'] != original['semantic_surface_sha256']


def test_missing_creation_helper_is_not_waived_for_historical_surface():
    from pro_a.workbench import retry_compatibility as compatibility
    package = Path(compatibility.__file__).resolve().parent.parent
    specification = compatibility._CLOUD_EXECUTION_SURFACE
    historical = {name: (package / name).read_bytes() for name in specification}
    tree = ast.parse(historical['workbench/source_operations.py'])
    service = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'SourceOperations')
    service.body = [node for node in service.body if not (isinstance(node, ast.FunctionDef) and node.name == '_start')]
    historical['workbench/source_operations.py'] = ast.unparse(tree).encode('utf-8')
    with pytest.raises(compatibility.RetryCompatibilityError):
        compatibility._surface_manifest(historical, specification)


def test_registration_does_not_waive_another_unrepresented_creation_dependency():
    from pro_a.workbench import retry_compatibility as compatibility
    package = Path(compatibility.__file__).resolve().parent.parent
    specification = compatibility._CLOUD_EXECUTION_SURFACE
    sources = {name: (package / name).read_bytes() for name in specification}
    marker = b'        runtime = self.jobs.current_runtime()'
    changed = dict(sources)
    changed['workbench/source_operations.py'] = sources['workbench/source_operations.py'].replace(
        marker, b'        self._unrepresented_creation_authorizer()\n' + marker, 1)
    assert changed != sources
    with pytest.raises(compatibility.RetryCompatibilityError, match='DEPENDENCY_UNCLOSED'):
        compatibility._surface_manifest(changed, specification)
