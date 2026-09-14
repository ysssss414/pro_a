from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from pro_a.db import Database
from pro_a.phase3f_review_completion import validate_blank_review_packet
from pro_a.query import ReadOnlyQuery
from pro_a.workbench.api import COOKIE, PREFIX, create_app
from pro_a.workbench.artifacts import Artifacts, digest
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from workbench_fixture import CLAIM, STATEMENT, make_fixture, write

TOKEN = 'synthetic-session-secret-for-stage0-tests-only'


@pytest.fixture
def case(tmp_path, monkeypatch):
    fixture = make_fixture(tmp_path)
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', TOKEN)
    Store(fixture['config']).initialize()
    fixture['registry'] = Artifacts(fixture['config'])
    return fixture


def register(case):
    return case['registry'].register(case['packet_relative'], case['run_relative'])['artifact_id']


def client(case):
    config = case['config']
    return TestClient(create_app(config), base_url=config.origin, client=('127.0.0.1', 51000))


def login(client, origin='http://127.0.0.1:8000'):
    response = client.post(PREFIX + '/session', headers={'Origin': origin}, json={'token': TOKEN})
    assert response.status_code == 200
    return response


def test_native_blank_projection_and_counts(case):
    config, packet = case['config'], case['packet']
    validation = validate_blank_review_packet(packet, run_root=config.artifact_root / case['run_relative'])
    handle = register(case)
    assert register(case) == handle
    dto = case['registry'].read(handle)
    assert validation['status'] == dto['validation_state'] == 'VALID_BLANK_REVIEW_PACKET'
    native = [row for group in ('claims', 'nodes', 'aliases', 'relations') for row in packet[group]]
    assert len(dto['items']) == packet['summary']['total_operational_decisions_required'] == 3
    assert dto['summary'] == packet['summary']
    for row, projected in zip(native, dto['items'], strict=True):
        for key in projected:
            assert projected[key] == row[key]
    assert dto['items'][0]['content']['evidence_excerpt'] == STATEMENT
    assert dto['items'][0]['content']['evidence_validation']['authoritative_locator']['paragraph'] == 1
    assert dto['excluded_relation_inventory'] == packet['excluded_relation_inventory']
    assert dto['excluded_relation_inventory']['count'] == 1
    assert 'filename' not in dto['source'] and 'source_sha256' in dto['source']
    assert not dto['capabilities']['decision_save_available']
    encoded = json.dumps(dto)
    for forbidden in ('filename', 'frozen_relative_path', str(config.artifact_root), 'repository_commit', 'raw_model_response'):
        assert forbidden not in encoded


def test_reads_leave_databases_and_execution_unchanged(case, monkeypatch):
    config = case['config']
    handle = register(case)
    before = case['registry'].inventory(case['packet_relative'], case['run_relative'])
    db_hashes = [digest(path) for path in (config.knowledge_db, config.state_db)]
    connects = []
    original = sqlite3.connect
    def tracked(database, *args, **kwargs):
        connects.append((str(database), kwargs.get('uri')))
        assert str(database).startswith('file:') and '?mode=ro' in str(database) and kwargs.get('uri') is True
        return original(database, *args, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', tracked)
    def forbidden(*args, **kwargs):
        pytest.fail('Unsafe init_schema/model/apply entry point reached')
    monkeypatch.setattr(Database, 'init_schema', forbidden)
    import pro_a.production_execution as execution
    monkeypatch.setattr(execution, 'execute_authorized_production', forbidden)
    monkeypatch.setattr(execution, 'execute_foundation_payload', forbidden)
    import pro_a.semantic_decomposition as semantic
    for name in dir(semantic):
        if name.endswith('Backend') and isinstance(getattr(semantic, name), type):
            monkeypatch.setattr(getattr(semantic, name), '__init__', forbidden)
    c = client(case)
    login(c)
    assert c.get(PREFIX + '/review-packets').status_code == 200
    assert c.get(PREFIX + '/review-packets/' + handle).status_code == 200
    assert c.get('/api/stats').status_code == 200
    assert connects and all(uri for _, uri in connects)
    assert before == case['registry'].inventory(case['packet_relative'], case['run_relative'])
    assert db_hashes == [digest(path) for path in (config.knowledge_db, config.state_db)]


def test_readonly_uri_is_enforced_even_after_query_only_disabled(case):
    # Negative write probe targets ONLY the synthetic DB; never real Production.
    with ReadOnlyQuery(case['config'].knowledge_db).connect() as connection:
        connection.execute('PRAGMA query_only=OFF')
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            connection.execute("INSERT INTO meta VALUES('forbidden','probe')")


@pytest.mark.parametrize('relative', ['../private.json', '/private.json', 'C:/private.json', 'run/../../private.json', 'run\\private.json', 'file:///private.json'])
def test_path_escape_rejected(case, relative):
    with pytest.raises(BoundaryError, match='UNSAFE_PATH'):
        case['registry'].register(relative, case['run_relative'])


def test_unregistered_handle_and_arbitrary_http_paths(case):
    c = client(case)
    login(c)
    for suffix in ('ART_' + '0' * 32, 'packet.json', 'C%3A%5Cprivate.json'):
        response = c.get(PREFIX + '/review-packets/' + suffix)
        assert response.status_code == 404
        assert str(case['config'].artifact_root) not in response.text


@pytest.mark.parametrize('target', ['packet', 'source'])
def test_hash_tampering_fails_closed(case, target):
    handle = register(case)
    root = case['config'].artifact_root
    path = root / case['packet_relative'] if target == 'packet' else root / case['run_relative'] / 'source/synthetic.txt'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(BoundaryError, match='ARTIFACT_HASH_MISMATCH'):
        case['registry'].read(handle)
    c = client(case)
    login(c)
    assert c.get(PREFIX + '/review-packets/' + handle).status_code == 409


def test_invalid_blank_packet_rejected_without_rewrite(case):
    path = case['config'].artifact_root / case['packet_relative']
    packet = json.loads(path.read_text())
    packet['claims'][0]['human_input']['decision'] = 'KEEP'
    write(path, packet)
    before = digest(path)
    with pytest.raises(BoundaryError, match='NATIVE_PACKET_UNAVAILABLE'):
        register(case)
    assert digest(path) == before


def test_hardlink_rejected(case, tmp_path):
    handle = register(case)
    path = case['config'].artifact_root / case['packet_relative']
    (tmp_path / 'outside-packet.json').hardlink_to(path)
    with pytest.raises(BoundaryError, match='HARDLINK_FORBIDDEN'):
        case['registry'].read(handle)


def test_directory_link_rejected(case, tmp_path):
    link = case['config'].artifact_root / 'escape'
    outside = tmp_path / 'outside'
    outside.mkdir()
    if sys.platform == 'win32':
        # Native PowerShell junction creation; no shell deletion/relocation.
        subprocess.run(['powershell', '-NoProfile', '-Command',
                        f"New-Item -ItemType Junction -Path '{str(link).replace(chr(39), chr(39) * 2)}' -Target '{str(outside).replace(chr(39), chr(39) * 2)}' | Out-Null"], check=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(BoundaryError, match='LINK_FORBIDDEN'):
        case['registry'].resolve('escape')
    with pytest.raises(BoundaryError, match='LINK_FORBIDDEN'):
        case['registry'].register(case['packet_relative'], 'escape')


def test_manifest_traversal_rejected_before_native_validator(case, monkeypatch):
    path = case['config'].artifact_root / case['run_relative'] / 'run_manifest.json'
    manifest = json.loads(path.read_text())
    manifest['source']['frozen_relative_path'] = '../../outside-secret'
    write(path, manifest)
    import pro_a.workbench.artifacts as module
    monkeypatch.setattr(module, 'validate_blank_review_packet', lambda *a, **kw: pytest.fail('native validator reached before path guard'))
    with pytest.raises(BoundaryError, match='UNSAFE_PATH'):
        register(case)


def test_remote_session_origin_csrf_and_cookie(case):
    config = replace(case['config'], origin='https://research.invalid', remote=True)
    c = TestClient(create_app(config), base_url=config.origin, client=('203.0.113.5', 50000))
    for route in ('/api/health', '/api/stats', PREFIX + '/review-packets', '/docs'):
        assert c.get(route).status_code == 401
    assert c.post(PREFIX + '/session', json={'token': TOKEN}).status_code == 403
    assert c.post(PREFIX + '/session', headers={'Origin': 'https://attacker.invalid'}, json={'token': TOKEN}).status_code == 403
    response = login(c, config.origin)
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=strict' in cookie
    assert c.get(PREFIX + '/session').json()['actor'] == 'operator'
    assert c.get('/api/health').status_code == 200
    assert c.get('/api/health', headers={'Origin': 'https://attacker.invalid'}).status_code == 403
    assert c.post(PREFIX + '/review-packets', headers={'Origin': config.origin}).status_code == 403
    assert c.post(PREFIX + '/review-packets', headers={'Origin': config.origin, 'X-CSRF-Token': response.json()['csrf_token']}).status_code == 405
    c.cookies.set(COOKIE, 'tampered')
    assert c.get('/api/health').status_code == 401


def test_bad_login_never_echoes_secret(case):
    c = client(case)
    for token in ('SENSITIVE', 'not-the-correct-secret' * 2):
        response = c.post(PREFIX + '/session', headers={'Origin': case['config'].origin}, json={'token': token})
        assert response.status_code in (401, 422)
        assert token not in response.text
    assert c.get('/api/health', headers={'Host': 'attacker.invalid'}).status_code == 403
    remote = TestClient(create_app(case['config']), base_url=case['config'].origin, client=('203.0.113.5', 1))
    assert remote.get('/api/health').status_code == 403


def test_private_demo_isolation_and_schema_fail_closed(case, tmp_path):
    with pytest.raises(BoundaryError, match='KNOWLEDGE_MODE_MISMATCH'):
        create_app(replace(case['config'], mode='PRIVATE'))
    private = make_fixture(tmp_path / 'private', mode='PRIVATE')
    Store(private['config']).initialize()
    with pytest.raises(BoundaryError, match='KNOWLEDGE_MODE_MISMATCH'):
        create_app(replace(private['config'], mode='DEMO'))
    with pytest.raises(BoundaryError, match='ARTIFACT_MODE_MISMATCH'):
        create_app(replace(private['config'], state_db=case['config'].state_db, artifact_root=case['config'].artifact_root, mode='PRIVATE'))


@pytest.mark.parametrize('kind', ['old', 'unknown', 'missing_contract', 'missing_db'])
def test_schema_rejection_never_bootstraps(case, monkeypatch, kind):
    path = case['config'].knowledge_db
    if kind == 'missing_db':
        path.unlink()
    else:
        with closing(sqlite3.connect(path)) as connection, connection:
            if kind == 'missing_contract':
                connection.execute("DELETE FROM meta WHERE key='foundation_execution_contract_sha256'")
            else:
                connection.execute("UPDATE meta SET value=? WHERE key='schema_version'", ('0.2.2' if kind == 'old' else '9.9',))
    before = digest(path) if path.exists() else None
    monkeypatch.setattr(Database, 'init_schema', lambda *a: pytest.fail('Unsafe bootstrap'))
    with pytest.raises(BoundaryError):
        create_app(case['config'])
    assert (digest(path) if path.exists() else None) == before


def test_explorer_get_compatibility(case):
    from pro_a.api import create_app as explorer
    baseline = TestClient(explorer(db_path=case['config'].knowledge_db))
    secured = client(case)
    login(secured)
    for route in ('/api/health', '/api/stats', '/api/nodes', '/api/nodes/search?q=synthetic', '/api/nodes/MISSING', '/api/sources/MISSING'):
        old, new = baseline.get(route), secured.get(route)
        assert (old.status_code, old.json()) == (new.status_code, new.json())


def test_state_isolated_and_only_registry_tables(case):
    config = case['config']
    for state in (config.knowledge_db, config.artifact_root / 'state.db'):
        with pytest.raises(BoundaryError, match='STATE_NOT_ISOLATED'):
            replace(config, state_db=state).validate()
    with Store(config).connect() as connection:
        assert {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {'workbench_meta', 'registered_packets'}
    with ReadOnlyQuery(config.knowledge_db).connect() as connection:
        assert connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '0.2.3'


def test_disclosure_is_rejected_instead_of_dropping_evidence(case):
    from pro_a.workbench.review import project
    packet = case['packet']
    packet['claims'][0]['content']['evidence_validation']['raw_model_response'] = 'private raw payload'
    with pytest.raises(BoundaryError, match='PROJECTION_DISCLOSURE_FORBIDDEN'):
        project(packet, {'status': 'VALID_BLANK_REVIEW_PACKET'}, 'ART_' + '1' * 32, 'a' * 64, 'DEMO')


@pytest.mark.parametrize('value', ['C:/private/source.pdf', '/data/private/source.pdf', 'file:///private/source.pdf', 'refs/heads/private-review'])
def test_projection_rejects_private_locations(value):
    from pro_a.workbench.review import require_safe_projection
    with pytest.raises(BoundaryError, match='PROJECTION_DISCLOSURE_FORBIDDEN'):
        require_safe_projection({'evidence_pointer': value})


def test_projection_preserves_public_url_and_native_locator():
    from pro_a.workbench.review import require_safe_projection
    require_safe_projection({'evidence_pointer': 'pdf:p1:paragraph:2', 'evidence_excerpt': 'Synthetic reference https://example.invalid/report.'})
