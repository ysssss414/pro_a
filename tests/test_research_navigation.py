"""Focused Stage 4A read projection checks against disposable canonical fixtures."""
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from pro_a.research_explorer import ResearchError
from pro_a.research_navigation import ResearchNavigation


REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def fixture(tmp_path):
    db = tmp_path / 'canonical.db'
    with sqlite3.connect(db) as conn:
        conn.executescript('''CREATE TABLE nodes(node_id TEXT PRIMARY KEY,canonical_name TEXT,
            primary_type TEXT,status TEXT);
            CREATE TABLE node_relations(relation_id TEXT PRIMARY KEY,from_node_id TEXT,
            to_node_id TEXT,relation_type TEXT,status TEXT);''')
        conn.executemany('INSERT INTO nodes VALUES(?,?,?,?)', [
            ('ROOT_A', 'Root A', 'Industry', 'active'),
            ('ROOT_B', 'Root B', 'Industry', 'active'),
            ('NODE_Z', 'zeta', 'Product', 'active'),
            ('NODE_A', 'Alpha', 'Product', 'active'),
            ('NODE_C', 'Child', 'Product', 'active'),
            ('INACTIVE', 'Inactive', 'Product', 'retired'),
        ])
        conn.executemany('INSERT INTO node_relations VALUES(?,?,?,?,?)', [
            ('R1', 'NODE_Z', 'ROOT_A', 'part_of', 'current'),
            ('R2', 'NODE_A', 'ROOT_A', 'part_of', 'current'),
            ('R3', 'NODE_C', 'NODE_A', 'part_of', 'current'),
            ('R4', 'INACTIVE', 'ROOT_A', 'part_of', 'current'),
            ('R5', 'ROOT_B', 'ROOT_A', 'part_of', 'retired'),
        ])
    specs = tmp_path / 'specs'
    specs.mkdir()
    for domain in ('ai_hardware', 'semiconductor'):
        spec = json.loads((REPO / 'research_navigation' / f'{domain}.json').read_text(encoding='utf-8'))
        spec['root_node_ids'] = ['ROOT_A' if domain == 'ai_hardware' else 'ROOT_B']
        (specs / f'{domain}.json').write_text(json.dumps(spec), encoding='utf-8')
    config = SimpleNamespace(knowledge_db=db, state_db=tmp_path / 'workbench.db')
    return ResearchNavigation(config, spec_dir=specs), db, specs, config


def edit_spec(specs, domain, change):
    path = specs / f'{domain}.json'
    spec = json.loads(path.read_text(encoding='utf-8'))
    change(spec)
    path.write_text(json.dumps(spec), encoding='utf-8')


def test_specs_roots_pack_binding_and_privacy(fixture):
    nav, db, specs, _ = fixture
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    assert nav.validate_navigation_specs()
    domains = nav.list_domains()['domains']
    assert [row['domain_id'] for row in domains] == ['ai_hardware', 'semiconductor']
    assert domains[0]['domain_pack_lifecycle'] == 'PROPOSED'
    assert not domains[0]['domain_pack_registered']
    assert domains[0]['domain_pack_sha256'] == json.loads((specs / 'ai_hardware.json').read_text())['domain_pack']['sha256']
    assert domains[0]['root_nodes'][0]['node_id'] == 'ROOT_A'
    assert str(REPO) not in json.dumps(nav.list_domains())
    assert str(db) not in json.dumps(nav.list_domains())
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


def test_invalid_spec_pack_and_roots_rejected(fixture):
    nav, _, specs, _ = fixture
    with pytest.raises(ResearchError, match='NAVIGATION_DOMAIN_NOT_FOUND'):
        nav.domain_tree('unknown')
    edit_spec(specs, 'ai_hardware', lambda s: s.update(root_node_ids=['MISSING']))
    with pytest.raises(ResearchError, match='NAVIGATION_ROOT_NOT_ACTIVE'):
        nav.validate_navigation_specs()
    edit_spec(specs, 'ai_hardware', lambda s: s.update(root_node_ids=['INACTIVE']))
    with pytest.raises(ResearchError, match='NAVIGATION_ROOT_NOT_ACTIVE'):
        nav.domain_tree('ai_hardware')
    edit_spec(specs, 'ai_hardware', lambda s: s['domain_pack'].update(sha256='0' * 64))
    with pytest.raises(ResearchError, match='NAVIGATION_SPEC_INVALID'):
        nav.list_domains()


def test_recursive_order_depth_and_determinism(fixture):
    nav, _, _, _ = fixture
    first = nav.domain_tree('ai_hardware')
    assert first == nav.domain_tree('ai_hardware')
    assert first['visible_node_count'] == 5
    assert [child['canonical_name'] for child in first['roots'][0]['children']] == ['Alpha', 'Inactive', 'zeta']
    assert first['roots'][0]['children'][1]['status'] == 'retired'
    assert first['roots'][0]['children'][0]['children'][0]['node_id'] == 'NODE_C'
    shallow = nav.domain_tree('ai_hardware', max_depth=0)
    assert shallow['truncated'] and shallow['truncation_reasons'] == ['max_depth']
    assert shallow['roots'][0]['child_count'] == 3
    with pytest.raises(ResearchError, match='INVALID_NAVIGATION_DEPTH'):
        nav.domain_tree('ai_hardware', max_depth=13)


def test_multi_root_cycle_duplicate_path_and_node_bound(fixture):
    nav, db, specs, _ = fixture
    edit_spec(specs, 'ai_hardware', lambda s: s.update(root_node_ids=['ROOT_A', 'ROOT_B']))
    with sqlite3.connect(db) as conn:
        conn.executemany('INSERT INTO node_relations VALUES(?,?,?,?,?)', [
            ('R6', 'NODE_C', 'ROOT_B', 'part_of', 'current'),
            ('R7', 'ROOT_A', 'NODE_C', 'part_of', 'current'),
        ])
    tree = nav.domain_tree('ai_hardware')
    assert tree['root_count'] == 2
    anomalies = []

    def walk(node):
        if 'anomaly' in node:
            anomalies.append(node['anomaly'])
        for child in node['children']:
            walk(child)

    for root in tree['roots']:
        walk(root)
    assert 'cycle' in anomalies
    assert 'duplicate_path' in anomalies
    with sqlite3.connect(db) as conn:
        conn.executemany('INSERT INTO nodes VALUES(?,?,?,?)',
                         [(f'X{i:04}', f'Item {i:04}', 'Product', 'active') for i in range(1002)])
        conn.executemany('INSERT INTO node_relations VALUES(?,?,?,?,?)',
                         [(f'RX{i:04}', f'X{i:04}', 'ROOT_B', 'part_of', 'current') for i in range(1002)])
    bounded = nav.domain_tree('semiconductor')
    assert bounded['visible_node_count'] == 1000
    assert bounded['truncated'] and 'max_nodes' in bounded['truncation_reasons']


def test_contexts_do_not_infer_operational_assignment(fixture):
    nav, _, specs, config = fixture
    edit_spec(specs, 'semiconductor', lambda s: s.update(root_node_ids=['ROOT_A']))
    context = nav.node_domain_context('NODE_A')
    assert {item['domain_id'] for item in context['navigation_contexts']} == {'ai_hardware', 'semiconductor'}
    assert context['operational_domain_assignments'] == []
    with sqlite3.connect(config.state_db) as conn:
        conn.execute('CREATE TABLE domain_assignments(object_type TEXT,object_id TEXT,revision INTEGER,primary_domain TEXT)')
        conn.execute('INSERT INTO domain_assignments VALUES(?,?,?,?)', ('Node', 'NODE_A', 1, 'operations_only'))
    context = nav.node_domain_context('NODE_A')
    assert context['operational_domain_assignments'] == [{'primary_domain': 'operations_only', 'revision': 1}]
    assert all(item['domain_id'] != 'operations_only' for item in context['navigation_contexts'])
    with pytest.raises(ResearchError, match='NODE_NOT_FOUND'):
        nav.node_domain_context('UNKNOWN')


def test_registry_identity_drift_rejected(fixture):
    nav, _, _, config = fixture
    with sqlite3.connect(config.state_db) as conn:
        conn.execute('CREATE TABLE domain_pack_registry(domain_id TEXT,version TEXT,sha256 TEXT,root TEXT)')
        conn.execute('INSERT INTO domain_pack_registry VALUES(?,?,?,?)', ('ai_hardware', '1.0.0', '0' * 64, '/private/path'))
    with pytest.raises(ResearchError, match='NAVIGATION_SPEC_INVALID'):
        nav.list_domains()


def test_absent_registry_row_does_not_infer_qualification(fixture):
    nav, _, specs, config = fixture
    identity = json.loads((specs / 'ai_hardware.json').read_text())['domain_pack']
    with sqlite3.connect(config.state_db) as conn:
        conn.execute('CREATE TABLE domain_pack_registry(domain_id TEXT,version TEXT,sha256 TEXT,root TEXT)')
        conn.execute('INSERT INTO domain_pack_registry VALUES(?,?,?,?)',
                     ('ai_hardware', identity['version'], identity['sha256'], '/private/path'))
    first, second = nav.list_domains()['domains']
    assert first['domain_pack_registered'] is True
    assert second['domain_pack_registered'] is False
    assert '/private/path' not in json.dumps(nav.list_domains())
