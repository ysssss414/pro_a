"""Explicit Git history is evidence, never an installed-code import fallback."""
from pathlib import Path
import os
import socket
import subprocess

import pytest

from pro_a.workbench import retry_compatibility as compatibility


SOURCE = b'def calculate():\n    return 1\n'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))
    original = socket.socket.connect
    def local_only(sock, address):
        # Windows asyncio implements its internal socketpair over loopback.
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', 'localhost', '::1'):
            return original(sock, address)
        pytest.fail('REAL_NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket, 'connect', local_only)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def commit(root):
    git(root, 'add', '--all')
    git(root, '-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
        'commit', '--quiet', '-m', 'Synthetic history evidence')
    return git(root, 'rev-parse', 'HEAD')


@pytest.fixture
def history(tmp_path, monkeypatch):
    root = tmp_path / 'history'
    source = root / 'src/pro_a/sample.py'
    source.parent.mkdir(parents=True)
    source.write_bytes(SOURCE)
    git(root, 'init', '--quiet')
    git(root, 'config', 'core.autocrlf', 'false')
    sha = commit(root)
    package = tmp_path / 'sdk/site-packages/pro_a'
    package.mkdir(parents=True)
    (package / 'sample.py').write_bytes(SOURCE)
    monkeypatch.setattr(compatibility, '__file__', str(package / 'workbench/retry_compatibility.py'))
    monkeypatch.setattr(compatibility, '_CLOUD_EXECUTION_SURFACE', {'sample.py': None})
    return root, package, source, sha


def assess(history, **kwargs):
    root, _, _, sha = history
    return compatibility._assess_execution_surface('cloud', sha,
        historical_repository_root=root, **kwargs)


def test_installed_requires_explicit_history_even_in_an_enclosing_repository(history, monkeypatch):
    root, package, _, sha = history
    git(package.parent.parent, 'init', '--quiet')
    monkeypatch.chdir(root)
    result = compatibility._assess_execution_surface('cloud', sha)
    assert not result['compatible']
    assert result['history_source_error_code'] == 'HISTORICAL_EXECUTION_REPOSITORY_REQUIRED'


def test_fixed_commit_bytes_not_history_working_tree(history):
    root, package, source, sha = history
    source.write_bytes(b'raise AssertionError("CHECKOUT_MUST_NOT_BE_IMPORTED")\n')
    historical, target = compatibility._execution_surface_sources(sha, {'sample.py': None},
        historical_repository_root=root)
    assert historical == target == {'sample.py': SOURCE}
    result = assess(history)
    assert result['compatible'] and result['reason'] == 'SEMANTIC_SURFACE_EXACT'
    assert result['historical_source_authority'] == 'EXACT_GIT_COMMIT_TREE'
    assert result['explicit_history_repository'] is True
    assert str(root) not in str(result) and str(package) not in str(result)


def test_head_drift_does_not_change_requested_commit(history):
    root, _, source, _ = history
    source.write_bytes(SOURCE.replace(b'return 1', b'return 2'))
    commit(root)
    assert assess(history)['compatible']


def test_target_stays_installed_and_semantic_drift_is_rejected(history):
    _, package, _, _ = history
    (package / 'sample.py').write_bytes(SOURCE.replace(b'return 1', b'return 2'))
    result = assess(history)
    assert not result['compatible'] and result['reason'] == 'SEMANTIC_SURFACE_CHANGED'


@pytest.mark.parametrize('mode', ['missing', 'not_repository', 'nested', 'wrong_commit'])
def test_unavailable_history_fails_closed(history, tmp_path, mode):
    root, _, _, sha = history
    if mode == 'missing':
        root = tmp_path / 'absent'
    elif mode == 'not_repository':
        root = tmp_path / 'empty'
        root.mkdir()
    elif mode == 'nested':
        root = root / 'src'
    else:
        sha = 'f' * 40
    result = compatibility._assess_execution_surface('cloud', sha, historical_repository_root=root)
    assert not result['compatible'] and result['reason'].startswith('EXECUTION_SURFACE_UNAVAILABLE:')


@pytest.mark.parametrize('sha', ['main', 'a' * 39, 'A' * 40, 'HEAD^{commit}', ''])
def test_history_requires_full_frozen_commit_identity(history, sha):
    root = history[0]
    result = compatibility._assess_execution_surface('cloud', sha, historical_repository_root=root)
    assert not result['compatible'] and result['reason'] == 'HISTORICAL_GIT_IDENTITY_INVALID'


def test_git_environment_cannot_select_another_repository(history, monkeypatch, tmp_path):
    root, _, _, _ = history
    other = tmp_path / 'unrelated'
    other.mkdir()
    git(other, 'init', '--quiet')
    monkeypatch.chdir(other)
    monkeypatch.setenv('GIT_DIR', str(other / '.git'))
    monkeypatch.setenv('GIT_WORK_TREE', str(other))
    monkeypatch.setenv('GIT_INDEX_FILE', str(other / 'bad-index'))
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', 'core.worktree')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', str(other))
    assert assess(history)['compatible']


def test_git_replace_cannot_reinterpret_history(history):
    root, _, source, original = history
    source.write_bytes(SOURCE.replace(b'return 1', b'return 999'))
    replacement = commit(root)
    git(root, 'replace', original, replacement)
    assert assess(history)['compatible']


def test_explicit_history_is_not_cached_after_repository_disappears(history):
    root = history[0]
    assert assess(history)['compatible']
    (root / '.git').rename(root / '.git.saved')
    assert not assess(history)['compatible']


def test_missing_git_does_not_waive_history(history, monkeypatch):
    monkeypatch.setenv('PATH', '')
    result = assess(history)
    assert not result['compatible'] and result['reason'].startswith('EXECUTION_SURFACE_UNAVAILABLE:')


def test_git_blob_bytes_are_hash_verified(history, monkeypatch):
    original = compatibility.subprocess.run
    def corrupted(command, *args, **kwargs):
        result = original(command, *args, **kwargs)
        if 'cat-file' in command and 'blob' in command:
            result.stdout = b'def calculate():\n    return 999\n'
        return result
    monkeypatch.setattr(compatibility.subprocess, 'run', corrupted)
    result = assess(history)
    assert not result['compatible']
    assert result['history_source_error_code'] == 'HISTORICAL_EXECUTION_BLOB_INTEGRITY'


def test_link_boundary_failure_is_closed(history, monkeypatch):
    from pro_a.workbench.config import BoundaryError
    def forbidden(_path):
        raise BoundaryError('LINK_FORBIDDEN')
    monkeypatch.setattr(compatibility, 'checked_path', forbidden)
    result = assess(history)
    assert not result['compatible']
    assert result['history_source_error_code'] == 'HISTORICAL_EXECUTION_REPOSITORY_UNAVAILABLE'


def test_missing_historical_module_is_not_equivalence(history):
    git(history[0], 'rm', 'src/pro_a/sample.py')
    missing = commit(history[0])
    result = compatibility._assess_execution_surface('cloud', missing, historical_repository_root=history[0])
    assert not result['compatible'] and result['reason'] == 'SEMANTIC_SURFACE_CHANGED'


def test_source_checkout_default_still_uses_own_repository(history, monkeypatch):
    root, _, _, sha = history
    monkeypatch.setattr(compatibility, '__file__', str(root / 'src/pro_a/workbench/retry_compatibility.py'))
    result = compatibility._assess_execution_surface('cloud', sha)
    assert result['compatible'] and not result['explicit_history_repository']


def test_explicit_missing_history_blocks_even_when_runtime_identities_match(tmp_path, monkeypatch):
    from test_truncation_recovery_operator import stopped, snapshot
    from pro_a.workbench.truncation_recovery import assess_truncation_recovery_compatibility
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    before = snapshot(value)
    result = assess_truncation_recovery_compatibility(value['config'], value['run_id'], value['attempt_id'],
        persist=False, historical_repository_root=tmp_path / 'missing')
    assert result['status'] == 'BLOCKED'
    assert 'BLOCKED_EXECUTION_CONTRACT_CHANGED' in result['blockers']
    assert snapshot(value) == before


def test_official_truncation_assessment_uses_real_history_without_response_reinterpretation(tmp_path, monkeypatch):
    from test_truncation_recovery_operator import stopped, snapshot
    from pro_a.workbench.truncation_recovery import assess_truncation_recovery_compatibility
    value = stopped(tmp_path, monkeypatch, counts=(33,))
    before = snapshot(value)
    root = Path(os.environ['PRO_A_HISTORY_TEST_REPOSITORY']) if 'PRO_A_HISTORY_TEST_REPOSITORY' in os.environ else Path(compatibility.__file__).resolve().parents[3]
    result = assess_truncation_recovery_compatibility(value['config'], value['run_id'], value['attempt_id'],
        persist=False, historical_repository_root=root)
    assert result['status'] == 'QUALIFIED', result['blockers']
    assert result['evidence']['cloud_execution_surface']['explicit_history_repository']
    assert result['evidence']['native_execution_surface']['explicit_history_repository']
    assert snapshot(value) == before


def test_no_public_surface_or_execution_operator_receives_history_parameter():
    import inspect
    from pro_a.workbench.source_operations import SourceOperations
    package = Path(compatibility.__file__).resolve().parent.parent
    for name in ('workbench/api.py', 'mcp/server.py'):
        assert 'historical_repository_root' not in (package / name).read_text(encoding='utf-8')
    for action in (SourceOperations.start, SourceOperations.resume_bounded_extraction_only,
                   SourceOperations.recover_truncated_bounded_extraction):
        assert 'historical_repository_root' not in inspect.signature(action).parameters
