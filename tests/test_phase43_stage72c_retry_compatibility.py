"""Stage 7.2C bounded cross-release retry compatibility qualification."""
import json
import sqlite3
import stat

import pytest
from fastapi.testclient import TestClient

from pro_a.cloud_contract import DeterministicFakeProvider, digest
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.retry_compatibility import (
    RetryCompatibilityError,
    _validate_record,
    assess_retry_compatibility,
    load_qualification,
    prepare_retry_compatibility,
)
from pro_a.workbench.source_operations import SourceOperationError
from pro_a.workbench.store import Store
from test_phase43_stage72b_extraction_retry import failed, original_rows, retry
from test_phase43_stage71_shared_core_pending import case


@pytest.fixture(autouse=True)
def clear_surface_cache():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    _execution_surface_comparison.cache_clear()
    yield
    _execution_surface_comparison.cache_clear()


def release_drift(monkeypatch, value, *, cloud_semantic=None, native_semantic=None,
                  broad_code_drift=False):
    import pro_a.phase4_orchestration as phase4
    import pro_a.workbench.cloud_jobs as cloud_jobs
    import pro_a.workbench.retry_compatibility as compatibility

    # These jobs were created by the current source, including uncommitted repair
    # work. Model a metadata-only release of that exact synthetic execution
    # surface, not a release of the older repository HEAD.
    package = compatibility.Path(compatibility.__file__).resolve().parent.parent
    frozen_sources = {
        name: (package / name).read_bytes()
        for specification in (compatibility._CLOUD_EXECUTION_SURFACE,
                              compatibility._NATIVE_EXECUTION_SURFACE)
        for name in specification
    }
    def synthetic_sources(_historical_git_sha, specification):
        return ({name: frozen_sources[name] for name in specification},
                {name: (package / name).read_bytes() for name in specification})
    monkeypatch.setattr(compatibility, '_execution_surface_sources', synthetic_sources)
    compatibility._execution_surface_comparison.cache_clear()
    target_cloud = value['service'].jobs.current_runtime()
    target_cloud = dict(target_cloud)
    target_cloud['git_sha'] = 'f' * 40
    if broad_code_drift:
        target_cloud['domain_code_sha256'] = '1' * 64
        target_cloud['phase4_processing_code_sha256'] = '2' * 64
    if cloud_semantic:
        target_cloud[cloud_semantic] = '0' * 64
    target_cloud['runtime_sha256'] = digest({
        key: item for key, item in target_cloud.items() if key != 'runtime_sha256'
    })
    target_native = dict(phase4._runtime())
    target_native['repository_commit'] = 'f' * 40
    if broad_code_drift:
        target_native['processing_code_sha256'] = '2' * 64
    if native_semantic:
        target_native[native_semantic] = '0' * 64
    monkeypatch.setattr(
        cloud_jobs, 'runtime_identity',
        lambda adapter_version, workbench_schema_version='7': dict(target_cloud),
    )
    monkeypatch.setattr(phase4, '_runtime', lambda: dict(target_native))
    monkeypatch.setattr(compatibility, 'native_runtime', lambda: dict(target_native))
    return target_cloud, target_native


def qualify(value, *, persist=True):
    return assess_retry_compatibility(
        value['config'], value['run_id'], value['attempt_id'], persist=persist,
    )


def test_exact_runtime_qualification_is_append_only_and_does_not_mutate_history(tmp_path):
    value = failed(tmp_path)
    before = original_rows(value)
    assert prepare_retry_compatibility(value['config']) == {
        'status': 'PREPARED', 'extension': 'extraction-retry-cross-release-v1',
    }
    result = qualify(value)
    assert result['status'] == 'QUALIFIED' and result['blockers'] == []
    assert all(item['result'] == 'PASS' for item in result['dimensions'].values())
    assert result['record']['failed_attempt_id'] == value['attempt_id']
    assert result['record']['failed_job_id'] == value['job_id']
    assert original_rows(value) == before
    duplicate = qualify(value)
    assert duplicate['status'] == 'QUALIFIED' and duplicate['duplicate'] is True
    assert duplicate['record'] == result['record']
    with Store(value['config']).connect(operator_write=True) as connection:
        assert connection.execute(
            'SELECT count(*) FROM retry_compatibility_qualifications'
        ).fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match='APPEND_ONLY'):
            connection.execute(
                "UPDATE retry_compatibility_qualifications SET reason='changed'"
            )
        with pytest.raises(sqlite3.IntegrityError, match='APPEND_ONLY'):
            connection.execute('DELETE FROM retry_compatibility_qualifications')


def test_metadata_only_release_drift_qualifies_and_reaches_human_review(
        tmp_path, monkeypatch):
    value = failed(tmp_path)
    before = original_rows(value)
    prepare_retry_compatibility(value['config'])
    target_cloud, _ = release_drift(monkeypatch, value, broad_code_drift=True)
    result = qualify(value)
    assert result['status'] == 'QUALIFIED'
    comparison = result['evidence']['cloud_runtime']
    assert comparison['semantic_differences'] == []
    assert comparison['metadata_only_differences'] == ['git_sha', 'runtime_sha256']
    assert comparison['surface_equivalent_differences'] == [
        'domain_code_sha256', 'phase4_processing_code_sha256',
    ]
    assert result['evidence']['cloud_execution_surface']['compatible'] is True
    assert result['evidence']['native_execution_surface']['compatible'] is True
    assert result['record']['target_runtime_sha256'] == target_cloud['runtime_sha256']
    accepted = retry(value)
    assert accepted['retry']['attempt_number'] == 2
    provider = DeterministicFakeProvider()
    first = value['service'].advance_once(
        worker_id='stage72c-compatible', processing_run_id=value['run_id'], provider=provider,
    )
    final = value['service'].advance_once(
        worker_id='stage72c-compatible', processing_run_id=value['run_id'], provider=provider,
    )
    assert first['state'] == 'SEMANTIC_PROCESSING'
    assert final['state'] == 'HUMAN_REVIEW_REQUIRED'
    assert provider.call_count == 2
    assert original_rows(value) == before


def test_target_runtime_requires_an_explicit_exact_scope_qualification(tmp_path, monkeypatch):
    value = failed(tmp_path)
    release_drift(monkeypatch, value)
    with pytest.raises(SourceOperationError, match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value)
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT count(*) FROM extraction_retries').fetchone()[0] == 0


@pytest.mark.parametrize(
    'cloud_field,native_field,blocker',
    [
        ('workbench_schema_version', None, 'BLOCKED_EXECUTION_CONTRACT_CHANGED'),
        ('cloud_contract_version', None, 'BLOCKED_EXECUTION_CONTRACT_CHANGED'),
        (None, 'python', 'BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE'),
    ],
)
def test_semantic_runtime_or_native_change_fails_closed(
        tmp_path, monkeypatch, cloud_field, native_field, blocker):
    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    release_drift(
        monkeypatch, value, cloud_semantic=cloud_field, native_semantic=native_field,
    )
    result = qualify(value, persist=False)
    assert result['status'] == 'BLOCKED' and blocker in result['blockers']
    with Store(value['config']).connect() as connection:
        assert connection.execute(
            'SELECT count(*) FROM retry_compatibility_qualifications'
        ).fetchone()[0] == 0


def test_changed_execution_surface_blocks_broad_code_digest_drift(
        tmp_path, monkeypatch):
    import pro_a.workbench.retry_compatibility as compatibility

    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    release_drift(monkeypatch, value, broad_code_drift=True)
    original = compatibility._execution_surface_comparison

    def changed(kind, historical_git_sha):
        result = dict(original(kind, historical_git_sha))
        result.update(compatible=False, reason='SEMANTIC_SURFACE_CHANGED')
        return result

    monkeypatch.setattr(compatibility, '_execution_surface_comparison', changed)
    result = qualify(value, persist=False)
    assert result['status'] == 'BLOCKED'
    assert 'BLOCKED_EXECUTION_CONTRACT_CHANGED' in result['blockers']
    assert 'BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE' in result['blockers']


@pytest.mark.parametrize(
    'name,original,replacement',
    [
        (
            'workbench/cloud_jobs.py',
            b'PROMPT_IDENTITY_MISMATCH',
            b'PROMPT_IDENTITY_BYPASS',
        ),
        (
            'workbench/source_operations.py',
            b'BLOCKED_EMPTY_EXTRACTION_PLAN',
            b'BYPASSED_EMPTY_EXTRACTION_PLAN',
        ),
    ],
)
def test_execution_surface_manifest_covers_retry_execution_dependencies(
        name, original, replacement):
    import pro_a.workbench.retry_compatibility as compatibility

    package = compatibility.Path(compatibility.__file__).resolve().parent.parent
    sources = {
        path: (package / path).read_bytes()
        for path in compatibility._CLOUD_EXECUTION_SURFACE
    }
    assert sources[name].count(original) == 1
    changed = dict(sources)
    changed[name] = sources[name].replace(original, replacement, 1)

    before = compatibility._surface_manifest(
        sources, compatibility._CLOUD_EXECUTION_SURFACE,
    )
    after = compatibility._surface_manifest(
        changed, compatibility._CLOUD_EXECUTION_SURFACE,
    )
    assert after['semantic_surface_sha256'] != before['semantic_surface_sha256']


@pytest.mark.parametrize(
    'kind,name,original,replacement,blocker',
    [
        (
            'cloud', 'workbench/cloud_jobs.py',
            b'guard_cloud_runtime(stored_runtime, current_runtime, self.runtime_compatibility)',
            b'bypass_cloud_runtime(stored_runtime, current_runtime, self.runtime_compatibility)',
            'BLOCKED_EXECUTION_CONTRACT_CHANGED',
        ),
        (
            'cloud', 'workbench/domains.py',
            b'processing_context.guard_resume(frozen, current)',
            b'processing_context.skip_resume(frozen, current)',
            'BLOCKED_EXECUTION_CONTRACT_CHANGED',
        ),
        (
            'cloud', 'workbench/source_operations.py',
            b'guard_cloud_runtime(\n                    json.loads(row["runtime_json"]), current_runtime,',
            b'bypass_cloud_runtime(\n                    json.loads(row["runtime_json"]), current_runtime,',
            'BLOCKED_EXECUTION_CONTRACT_CHANGED',
        ),
        (
            'native', 'phase4_orchestration.py',
            b'guard_native_runtime(identity["runtime"], current_runtime, runtime_compatibility)',
            b'bypass_native_runtime(identity["runtime"], current_runtime, runtime_compatibility)',
            'BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE',
        ),
        (
            'native', 'phase4_orchestration.py',
            b'runtime_compatibility=runtime_compatibility,',
            b'runtime_override=runtime_compatibility,',
            'BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE',
        ),
    ],
)
def test_semantic_surface_mutation_makes_qualification_block(
        tmp_path, monkeypatch, kind, name, original, replacement, blocker):
    import pro_a.workbench.retry_compatibility as compatibility

    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    release_drift(monkeypatch, value, broad_code_drift=True)
    package = compatibility.Path(compatibility.__file__).resolve().parent.parent

    def adversarial_sources(_historical_git_sha, specification):
        historical = {path: (package / path).read_bytes() for path in specification}
        target = dict(historical)
        selected = (
            specification is compatibility._CLOUD_EXECUTION_SURFACE
            if kind == 'cloud'
            else specification is compatibility._NATIVE_EXECUTION_SURFACE
        )
        if selected:
            assert target[name].count(original) == 1
            target[name] = target[name].replace(original, replacement, 1)
        return historical, target

    monkeypatch.setattr(compatibility, '_execution_surface_sources', adversarial_sources)
    compatibility._execution_surface_comparison.cache_clear()
    try:
        result = qualify(value, persist=False)
    finally:
        compatibility._execution_surface_comparison.cache_clear()
    assert result['status'] == 'BLOCKED'
    assert blocker in result['blockers']
    surface = result['evidence'][f'{kind}_execution_surface']
    assert surface['compatible'] is False
    assert surface['reason'] == 'SEMANTIC_SURFACE_CHANGED'


def test_operation_adapter_repair_is_not_compatible_with_pre_binding_release():
    import subprocess
    import pro_a.workbench.retry_compatibility as compatibility

    package = compatibility.Path(compatibility.__file__).resolve().parent.parent
    root = package.parents[1]
    baseline = '1966c24d37644d02c9c0c3496725a177ab437106'
    for kind, specification in (
            ('cloud', compatibility._CLOUD_EXECUTION_SURFACE),
            ('native', compatibility._NATIVE_EXECUTION_SURFACE)):
        historical = {
            name: subprocess.check_output(
                ['git', 'show', f'{baseline}:src/pro_a/{name}'], cwd=root,
            )
            for name in specification
        }
        target = {name: (package / name).read_bytes() for name in specification}
        if kind == 'cloud':
            # The old profile lacks the operation-binding dependency. Its
            # execution surface must fail closed, never normalize to this repair.
            with pytest.raises(RetryCompatibilityError):
                compatibility._surface_manifest(historical, specification)
            continue
        before = compatibility._surface_manifest(historical, specification)
        after = compatibility._surface_manifest(target, specification)
        assert after['semantic_surface_sha256'] == before['semantic_surface_sha256']


def test_unrepresented_helper_dependency_fails_closed():
    import pro_a.workbench.retry_compatibility as compatibility

    package = compatibility.Path(compatibility.__file__).resolve().parent.parent
    sources = {
        path: (package / path).read_bytes()
        for path in compatibility._CLOUD_EXECUTION_SURFACE
    }
    marker = b'        if fault_at is not None and fault_at not in FAULT_POINTS:'
    assert sources['workbench/cloud_jobs.py'].count(marker) == 1
    line_ending = (
        b'\r\n' if b'\r\n' in sources['workbench/cloud_jobs.py'] else b'\n'
    )
    changed = dict(sources)
    changed['workbench/cloud_jobs.py'] = sources['workbench/cloud_jobs.py'].replace(
        marker,
        b'        self._unrepresented_authorizer()' + line_ending + marker,
        1,
    )
    with pytest.raises(RetryCompatibilityError, match='DEPENDENCY_UNCLOSED'):
        compatibility._surface_manifest(
            changed, compatibility._CLOUD_EXECUTION_SURFACE,
        )


@pytest.mark.parametrize(
    'mutation,blocker',
    [
        ('source', 'BLOCKED_SOURCE_IDENTITY_CHANGED'),
        ('input', 'BLOCKED_INPUT_ARTIFACT_CHANGED'),
        ('prompt', 'BLOCKED_EXECUTION_CONTRACT_CHANGED'),
        ('provider', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
        ('model', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
        ('aliases', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
        ('adapter', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
        ('limit', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
        ('retry_policy', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
        ('configuration', 'BLOCKED_FROZEN_CONFIG_UNRECOVERABLE'),
    ],
)
def test_authoritative_execution_evidence_changes_fail_closed(
        tmp_path, mutation, blocker):
    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    with Store(value['config']).connect(operator_write=True) as connection:
        job = connection.execute(
            'SELECT * FROM cloud_jobs WHERE job_id=?', (value['job_id'],),
        ).fetchone()
        if mutation == 'source':
            source = connection.execute(
                'SELECT storage_relative FROM private_sources WHERE source_id=?',
                (value['source']['source_id'],),
            ).fetchone()
            path = value['config'].artifact_root.joinpath(source[0])
            path.chmod(stat.S_IWRITE | stat.S_IREAD)
            path.write_bytes(b'changed')
        elif mutation == 'input':
            source_input = connection.execute(
                'SELECT artifact_relative FROM source_cloud_inputs WHERE artifact_id=?',
                (job['input_artifact_id'],),
            ).fetchone()
            value['config'].artifact_root.joinpath(source_input[0]).write_text(
                '{}', encoding='utf-8',
            )
        elif mutation == 'prompt':
            connection.execute(
                "UPDATE cloud_jobs SET prompt_sha256=? WHERE job_id=?", ('0' * 64, value['job_id']),
            )
        elif mutation == 'provider':
            connection.execute(
                "UPDATE cloud_jobs SET provider='OTHER' WHERE job_id=?", (value['job_id'],),
            )
        elif mutation == 'model':
            connection.execute(
                "UPDATE cloud_jobs SET requested_model='other-model' WHERE job_id=?", (value['job_id'],),
            )
        elif mutation == 'aliases':
            connection.execute(
                "UPDATE cloud_jobs SET accepted_model_aliases_json='[]' WHERE job_id=?",
                (value['job_id'],),
            )
        elif mutation == 'adapter':
            connection.execute(
                "UPDATE cloud_jobs SET provider_adapter_version='other-adapter' WHERE job_id=?",
                (value['job_id'],),
            )
        elif mutation == 'limit':
            connection.execute(
                'UPDATE cloud_jobs SET timeout_seconds=timeout_seconds-1,'
                'max_output_tokens=max_output_tokens-1,max_calls=max_calls-1,'
                'max_attempts=max_attempts-1,max_total_tokens=max_total_tokens-1 WHERE job_id=?',
                (value['job_id'],),
            )
        elif mutation == 'retry_policy':
            connection.execute(
                "UPDATE cloud_jobs SET retry_policy_id='other-policy' WHERE job_id=?",
                (value['job_id'],),
            )
        else:
            value['phase4_config'].write_text(
                value['phase4_config'].read_text(encoding='utf-8').replace(
                    'max_output_tokens = 8192', 'max_output_tokens = 4096',
                ),
                encoding='utf-8',
            )
    result = qualify(value, persist=False)
    assert result['status'] == 'BLOCKED' and blocker in result['blockers']


def test_context_semantic_drift_and_later_assignment_are_distinguished(
        tmp_path, monkeypatch):
    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    original = __import__(
        'pro_a.workbench.domains', fromlist=['Domains'],
    ).Domains.pending_basis

    def changed(source, runtime, profile, cloud_profile):
        basis = original(source, runtime, profile, cloud_profile)
        basis['execution_policy'] = 'CHANGED_POLICY'
        return basis

    monkeypatch.setattr('pro_a.workbench.domains.Domains.pending_basis', staticmethod(changed))
    result = qualify(value, persist=False)
    assert result['status'] == 'BLOCKED'
    assert 'BLOCKED_CONTEXT_SEMANTIC_DRIFT' in result['blockers']


def test_shared_core_or_native_checkpoint_drift_fails_closed(tmp_path, monkeypatch):
    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    monkeypatch.setattr('pro_a.processing_context.shared_core_sha256', lambda: '0' * 64)
    shared = qualify(value, persist=False)
    assert shared['status'] == 'BLOCKED'
    assert 'BLOCKED_CONTEXT_SEMANTIC_DRIFT' in shared['blockers']

    monkeypatch.undo()
    with Store(value['config']).connect() as connection:
        run = connection.execute(
            'SELECT * FROM source_processing_runs WHERE processing_run_id=?',
            (value['run_id'],),
        ).fetchone()
    native_root = value['service']._native_root(run)
    manifest_path = native_root / 'execution_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['state'] = 'FAILED'
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    native = qualify(value, persist=False)
    assert native['status'] == 'BLOCKED'
    assert 'BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE' in native['blockers']


def test_record_is_non_transferable_and_evidence_hash_is_verified(tmp_path):
    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    result = qualify(value)
    record = dict(result['record'])
    record['evidence_sha256'] = '0' * 64
    with pytest.raises(RetryCompatibilityError, match='EVIDENCE_MISMATCH'):
        _validate_record(record)
    with Store(value['config']).connect() as connection:
        assert load_qualification(
            connection, run_id='SOURCE_RUN_WRONG', failed_attempt_id=value['attempt_id'],
            source_id=value['source']['source_id'], failed_job_id=value['job_id'],
            historical_runtime_sha256=result['record']['historical_runtime_sha256'],
            target_runtime=value['service'].jobs.current_runtime(),
            historical_context_sha256=result['record']['historical_context_sha256'],
        ) is None
        assert load_qualification(
            connection, run_id=value['run_id'], failed_attempt_id=value['attempt_id'],
            source_id=value['source']['source_id'], failed_job_id=value['job_id'],
            historical_runtime_sha256='0' * 64,
            target_runtime=value['service'].jobs.current_runtime(),
            historical_context_sha256=result['record']['historical_context_sha256'],
        ) is None
        wrong_target = dict(value['service'].jobs.current_runtime())
        wrong_target['runtime_sha256'] = '0' * 64
        assert load_qualification(
            connection, run_id=value['run_id'], failed_attempt_id=value['attempt_id'],
            source_id=value['source']['source_id'], failed_job_id=value['job_id'],
            historical_runtime_sha256=result['record']['historical_runtime_sha256'],
            target_runtime=wrong_target,
            historical_context_sha256=result['record']['historical_context_sha256'],
        ) is None


def test_stale_qualification_after_contract_change_is_not_used(tmp_path, monkeypatch):
    value = failed(tmp_path)
    prepare_retry_compatibility(value['config'])
    release_drift(monkeypatch, value)
    assert qualify(value)['status'] == 'QUALIFIED'
    monkeypatch.setattr(
        'pro_a.workbench.retry_compatibility.compatibility_contract_sha256',
        lambda: '0' * 64,
    )
    with pytest.raises(SourceOperationError, match='RETRY_RUNTIME_INCOMPATIBLE'):
        retry(value)


def test_api_cannot_supply_or_invent_compatibility(tmp_path, monkeypatch):
    value = failed(tmp_path)
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', 's' * 40)
    app = create_app(
        value['config'], cloud_profile=value['cloud_profile'],
        source_profile=value['source_profile'],
    )
    path = PREFIX + (
        f"/source-operations/runs/{value['run_id']}/attempts/{value['attempt_id']}/retry"
    )
    body = {
        'retry_reason': 'Explicit API retry',
        'idempotency_key': 'stage72c-http-retry-001',
        'compatible': True,
    }
    with TestClient(
            app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 1)) as client:
        csrf = client.post(
            PREFIX + '/session', json={'token': 's' * 40},
            headers={'origin': value['config'].origin},
        ).json()['csrf_token']
        response = client.post(
            path, json=body,
            headers={'origin': value['config'].origin, 'x-csrf-token': csrf},
        )
    assert response.status_code == 422
    with Store(value['config']).connect() as connection:
        assert connection.execute('SELECT count(*) FROM extraction_retries').fetchone()[0] == 0


def test_qualification_extension_preparation_is_explicit_and_idempotent(tmp_path):
    value = failed(tmp_path)
    assert prepare_retry_compatibility(value['config'])['status'] == 'PREPARED'
    assert prepare_retry_compatibility(value['config'])['status'] == 'ALREADY_PREPARED'


def test_qualification_extension_requires_explicit_retry_extension(tmp_path):
    value = case(tmp_path)
    with pytest.raises(BoundaryError, match='RETRY_SCHEMA_REQUIRED'):
        prepare_retry_compatibility(value['config'])
