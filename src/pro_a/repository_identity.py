"""One authority for checkout provenance and immutable installed-wheel identity."""
from __future__ import annotations

import base64
import hashlib
from importlib.metadata import PackageNotFoundError, distribution
import json
import os
from pathlib import Path
import re
import subprocess


CONTRACT_VERSION = 'pro-a-build-repository-identity-v1'
REPOSITORY = 'ysssss414/pro_a'
IDENTITY_FILE = '_build_identity.json'


class RepositoryIdentityError(ValueError):
    pass


def _commit(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{40}', value) is None:
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_INVALID')
    return value


def _git(root, *arguments):
    # A caller's Git overrides cannot select another repository or index.
    environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    try:
        return subprocess.check_output(['git', '-C', str(root), *arguments],
                                       env=environment, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_UNAVAILABLE') from None


def checkout_commit(root):
    root = Path(root).resolve()
    if (not (root / '.git').exists()
            or (root / 'src/pro_a/repository_identity.py').resolve() != Path(__file__).resolve()
            or not (root / 'pyproject.toml').is_file()):
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_UNAVAILABLE')
    if Path(_git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_UNAVAILABLE')
    _git(root, 'ls-files', '--error-unmatch', 'pyproject.toml', 'src/pro_a/repository_identity.py')
    return _commit(_git(root, 'rev-parse', '--verify', 'HEAD^{commit}'))


def release_build_identity(root):
    commit = checkout_commit(root)
    if (_git(root, 'status', '--porcelain', '--untracked-files=no')
            or _git(root, 'ls-files', '--others', '--exclude-standard', 'src/pro_a')):
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_DIRTY_BUILD')
    return {'contract_version': CONTRACT_VERSION, 'repository': REPOSITORY,
            'repository_commit': commit}


def _packaged_commit(path):
    try:
        content = path.read_bytes()
        value = json.loads(content)
    except (OSError, ValueError, UnicodeError):
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_INVALID') from None
    if (not isinstance(value, dict)
            or set(value) != {'contract_version', 'repository', 'repository_commit'}
            or value['contract_version'] != CONTRACT_VERSION or value['repository'] != REPOSITORY):
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_INVALID')
    commit = _commit(value['repository_commit'])
    try:
        entries = distribution('pro-a').files or ()
    except PackageNotFoundError:
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_UNAVAILABLE') from None
    entries = [entry for entry in entries if entry.as_posix() == 'pro_a/' + IDENTITY_FILE
               and Path(entry.locate()).resolve() == path.resolve()]
    digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
    if (len(entries) != 1 or entries[0].hash is None or entries[0].hash.mode != 'sha256'
            or entries[0].hash.value != digest or entries[0].size != len(content)):
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_INTEGRITY')
    return commit


def repository_commit():
    package = Path(__file__).resolve().parent
    metadata = package / IDENTITY_FILE
    if metadata.exists():
        return _packaged_commit(metadata)
    # Installed distributions lacking metadata cannot inherit an enclosing HEAD.
    root = package.parents[1]
    if package != root / 'src/pro_a':
        raise RepositoryIdentityError('REPOSITORY_IDENTITY_UNAVAILABLE')
    return checkout_commit(root)
