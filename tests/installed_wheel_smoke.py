"""Installed-only smoke entrypoint; copy tests out of the checkout before use.

The checkout is denied by an audit hook, not supplied as a resource fallback.
Actual paths belong in the private local report, never in a public receipt.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys


RESOURCES = {
    'schema.sql': '7df9b6ed87d04fd0e79f7df9ae5367c2caf32d2acfb34f454161c648ee90ff9e',
    'migrations/foundation_0_2_3_relation_native.sql':
        '17d0706380a4ba57c78081b9aeb37141115564b2f8210671194358d338b8e4f0',
}


def inside(path, root):
    return Path(path).resolve().is_relative_to(root)


def verify_origins(source_root):
    import pro_a
    prefix = Path(sys.prefix).resolve()
    package = Path(pro_a.__file__).resolve().parent
    distribution = importlib.metadata.distribution('pro-a')
    metadata = Path(distribution._path).resolve()
    paths = [Path(p or os.getcwd()).resolve() for p in sys.path]
    assert inside(package, prefix) and inside(metadata, prefix), 'STOP_INSTALLED_SMOKE_SOURCE_CONTAMINATION'
    assert not inside(Path.cwd(), source_root), 'STOP_INSTALLED_SMOKE_SOURCE_CONTAMINATION'
    assert not any(inside(p, source_root) for p in paths), 'STOP_INSTALLED_SMOKE_SOURCE_CONTAMINATION'
    for name, module in sys.modules.items():
        if name == 'pro_a' or name.startswith('pro_a.'):
            origin = getattr(module, '__file__', None)
            assert origin and inside(origin, package), 'STOP_INSTALLED_SMOKE_SOURCE_CONTAMINATION'
    return {'cwd': str(Path.cwd()), 'package_origin': str(package), 'metadata_origin': str(metadata),
            'sys_path': [str(p) for p in paths], 'source_tree_on_sys_path': False,
            'source_egg_info_shadowing': False}


def deny_checkout(source_root):
    def audit(event, args):
        if event in ('open', 'os.listdir', 'os.scandir', 'os.chdir', 'sqlite3.connect'):
            path = args[0]
            if isinstance(path, (str, bytes, os.PathLike)):
                if isinstance(path, bytes):
                    path = os.fsdecode(path)
                if inside(path, source_root):
                    raise PermissionError('SOURCE_CHECKOUT_ACCESS_FORBIDDEN')
    sys.addaudithook(audit)


def local_network_only():
    original = socket.socket.connect
    def connect(sock, address):
        if isinstance(address, tuple) and address[0] in ('127.0.0.1', 'localhost', '::1'):
            return original(sock, address)
        raise AssertionError('REAL_PROVIDER_NETWORK_FORBIDDEN')
    socket.socket.connect = connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--no-git', action='store_true')
    parser.add_argument('pytest_args', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    source_root = options.source_root.resolve()
    deny_checkout(source_root)
    local_network_only()
    denied = False
    try:
        (source_root / 'pyproject.toml').read_bytes()
    except PermissionError:
        denied = True
    assert denied, 'SOURCE_CHECKOUT_TRIPWIRE_NOT_ACTIVE'
    if options.no_git:
        os.environ['PATH'] = ''
    report = verify_origins(source_root)
    from pro_a.repository_identity import repository_commit
    from pro_a import extraction_analysis_record, output_decomposition
    from pro_a.workbench import bounded_resume, source_operations
    assert repository_commit() == options.expected_commit
    assert output_decomposition.RECORD_VERSION == 'whole-piece-output-batch-provider-record-v4'
    assert output_decomposition.V3_RECORD_VERSION == 'whole-piece-output-batch-provider-record-v3'
    assert extraction_analysis_record.VERSION == 'normalized-extraction-analysis-record-v1'
    assert bounded_resume.contract()['automatic_retry'] is False
    report.update(commit=options.expected_commit, source_checkout_access_denied=True,
                  no_git=options.no_git, r2_imports='PASS', real_provider_calls=0)
    result = 0
    if options.pytest_args:
        import pytest
        class Tripwire:
            def pytest_collection_finish(self, session):
                verify_origins(source_root)
            def pytest_sessionfinish(self, session, exitstatus):
                verify_origins(source_root)
        args = options.pytest_args
        if args[0] == '--':
            args = args[1:]
        result = pytest.main(args, plugins=[Tripwire()])
    report.update(verify_origins(source_root))
    report['exit_code'] = int(result)
    options.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    raise SystemExit(main())
