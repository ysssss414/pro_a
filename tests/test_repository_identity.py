"""Repository provenance cannot be inferred from an installed package's parents."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from pro_a import repository_identity as identity


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def load(root, relative='site-packages/pro_a'):
    package = root / relative
    package.mkdir(parents=True)
    path = package / 'repository_identity.py'
    shutil.copyfile(identity.__file__, path)
    spec = importlib.util.spec_from_file_location('isolated_repository_identity', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, package


def tracked_checkout(root):
    module, package = load(root, 'src/pro_a')
    (root / 'pyproject.toml').write_text('[project]\nname="pro-a"\nversion="0.5.1"\n')
    git(root, 'init', '--quiet')
    git(root, 'add', 'src', 'pyproject.toml')
    git(root, '-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
        'commit', '--quiet', '-m', 'Synthetic provenance fixture')
    return module, package


def packaged(module, package, monkeypatch):
    value = {'contract_version': identity.CONTRACT_VERSION, 'repository': identity.REPOSITORY,
             'repository_commit': 'a' * 40}
    path = package / identity.IDENTITY_FILE
    content = json.dumps(value).encode()
    path.write_bytes(content)
    entry = SimpleNamespace(hash=SimpleNamespace(mode='sha256', value=base64.urlsafe_b64encode(
        hashlib.sha256(content).digest()).decode().rstrip('=')), size=len(content),
        as_posix=lambda: 'pro_a/' + identity.IDENTITY_FILE, locate=lambda: path)
    monkeypatch.setattr(module, 'distribution', lambda name: SimpleNamespace(files=[entry]))
    monkeypatch.setattr(module, '_git', lambda *args: pytest.fail('INSTALLED_RUNTIME_CALLED_GIT'))
    return path, value, entry


def test_source_checkout_exact_identity_and_runtime_shape():
    from pro_a.phase4_orchestration import _runtime
    from pro_a.workbench.cloud_jobs import runtime_identity
    root = Path(identity.__file__).resolve().parents[2]
    expected = git(root, 'rev-parse', 'HEAD')
    value = _runtime()
    assert identity.repository_commit() == value['repository_commit'] == expected
    assert set(value) == {'repository_commit', 'contract_version', 'processing_code_sha256', 'python', 'sqlite', 'packages'}
    runtime_identity.cache_clear()
    assert runtime_identity('semantic-backend-adapter-v2', workbench_schema_version='11')['git_sha'] == expected


def test_resolver_source_bytes_remain_protected(monkeypatch):
    from pro_a import phase4_orchestration as phase4
    original = phase4._runtime()
    file_hash = phase4.sha256_file
    monkeypatch.setattr(phase4, 'sha256_file', lambda path:
                        '0' * 64 if path.name == 'repository_identity.py' else file_hash(path))
    changed = phase4._runtime()
    assert changed['repository_commit'] == original['repository_commit']
    assert changed['processing_code_sha256'] != original['processing_code_sha256']


def test_source_ignores_cwd_and_git_environment(tmp_path, monkeypatch):
    source, _ = tracked_checkout(tmp_path / 'source')
    other, _ = tracked_checkout(tmp_path / 'other')
    expected = git(tmp_path / 'source', 'rev-parse', 'HEAD')
    monkeypatch.chdir(tmp_path / 'other')
    monkeypatch.setenv('GIT_DIR', str(tmp_path / 'other/.git'))
    monkeypatch.setenv('GIT_WORK_TREE', str(tmp_path / 'other'))
    assert source.repository_commit() == expected


def test_installed_identity_never_calls_git(tmp_path, monkeypatch):
    module, package = load(tmp_path)
    packaged(module, package, monkeypatch)
    assert module.repository_commit() == 'a' * 40


def test_unrelated_enclosing_git_cannot_supply_installed_identity(tmp_path, monkeypatch):
    git(tmp_path, 'init', '--quiet')
    (tmp_path / 'other.txt').write_text('unrelated')
    git(tmp_path, 'add', 'other.txt')
    git(tmp_path, '-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
        'commit', '--quiet', '-m', 'Unrelated parent')
    assert git(tmp_path, 'rev-parse', 'HEAD') != 'a' * 40
    module, package = load(tmp_path)
    packaged(module, package, monkeypatch)
    assert module.repository_commit() == 'a' * 40


@pytest.mark.parametrize('corruption', ['json', 'commit', 'uppercase', 'version', 'repository', 'fields', 'list'])
def test_malformed_packaged_identity_fails_closed(tmp_path, monkeypatch, corruption):
    module, package = load(tmp_path)
    path, value, _ = packaged(module, package, monkeypatch)
    if corruption == 'json':
        path.write_bytes(b'{broken')
    else:
        value = {'commit': {**value, 'repository_commit': 'UNKNOWN'},
                 'uppercase': {**value, 'repository_commit': 'A' * 40},
                 'version': {**value, 'contract_version': 'unsupported'},
                 'repository': {**value, 'repository': 'other/repository'},
                 'fields': {**value, 'path': '/untrusted'}, 'list': []}[corruption]
        path.write_text(json.dumps(value))
    with pytest.raises(module.RepositoryIdentityError, match='REPOSITORY_IDENTITY_INVALID'):
        module.repository_commit()


def test_valid_metadata_tampering_is_detected_by_record(tmp_path, monkeypatch):
    module, package = load(tmp_path)
    path, value, _ = packaged(module, package, monkeypatch)
    path.write_text(json.dumps({**value, 'repository_commit': 'b' * 40}))
    with pytest.raises(module.RepositoryIdentityError, match='REPOSITORY_IDENTITY_INTEGRITY'):
        module.repository_commit()


def test_missing_installed_identity_never_falls_back(tmp_path, monkeypatch):
    module, package = load(tmp_path)
    path, _, _ = packaged(module, package, monkeypatch)
    path.unlink()
    with pytest.raises(module.RepositoryIdentityError, match='REPOSITORY_IDENTITY_UNAVAILABLE'):
        module.repository_commit()


def test_source_without_its_own_git_metadata_is_unavailable(tmp_path):
    module, _ = tracked_checkout(tmp_path / 'parent')
    nested, _ = load(tmp_path / 'parent/nested', 'src/pro_a')
    (tmp_path / 'parent/nested/pyproject.toml').write_text('[project]\nname="pro-a"\n')
    with pytest.raises(nested.RepositoryIdentityError, match='REPOSITORY_IDENTITY_UNAVAILABLE'):
        nested.repository_commit()


def test_source_git_unavailable_fails_closed(tmp_path, monkeypatch):
    module, _ = tracked_checkout(tmp_path)
    monkeypatch.setenv('PATH', str(tmp_path / 'empty-path'))
    with pytest.raises(module.RepositoryIdentityError, match='REPOSITORY_IDENTITY_UNAVAILABLE'):
        module.repository_commit()


@pytest.mark.parametrize('dirty', ['tracked', 'staged', 'untracked_source'])
def test_dirty_release_identity_is_refused(tmp_path, dirty):
    module, package = tracked_checkout(tmp_path)
    assert module.release_build_identity(tmp_path)['repository_commit'] == git(tmp_path, 'rev-parse', 'HEAD')
    if dirty == 'untracked_source':
        (package / 'extra.py').write_text('uncommitted = True\n')
    else:
        (tmp_path / 'pyproject.toml').write_text('[project]\nname="pro-a"\nversion="changed"\n')
        if dirty == 'staged':
            git(tmp_path, 'add', 'pyproject.toml')
    with pytest.raises(module.RepositoryIdentityError, match='REPOSITORY_IDENTITY_DIRTY_BUILD'):
        module.release_build_identity(tmp_path)
