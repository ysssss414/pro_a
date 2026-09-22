"""Stage 4B maps use only current, active canonical rows."""
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from pro_a.research_explorer import ResearchError
from pro_a.research_navigation import ResearchNavigation
from pro_a.research_structure_map import ResearchStructureMap, RELATION_GROUPS, SEMANTIC_GROUPS_SHA256
import pro_a.research_structure_map as structure_module


@pytest.fixture
def case(tmp_path):
    db = tmp_path / 'canonical.db'
    with sqlite3.connect(db) as conn:
        conn.executescript('''CREATE TABLE nodes(node_id TEXT PRIMARY KEY,canonical_name TEXT,
            primary_type TEXT,status TEXT);
            CREATE TABLE node_relations(relation_id TEXT PRIMARY KEY,from_node_id TEXT,
            to_node_id TEXT,relation_type TEXT,scope TEXT,status TEXT,confidence REAL);''')
        conn.executemany('INSERT INTO nodes VALUES(?,?,?,?)', [
            ('A', 'AI root', 'Industry', 'active'), ('A1', 'Memory', 'Segment', 'active'),
            ('A2', 'Compute', 'Segment', 'active'), ('A3', 'Packaging', 'Segment', 'active'),
            ('B', 'Semi root', 'Industry', 'active'), ('OUT', 'Outside', 'Material', 'active'),
            ('OLD', 'Retired', 'Product', 'retired')])
        conn.executemany('INSERT INTO node_relations VALUES(?,?,?,?,?,?,?)', [
            ('R1', 'A1', 'A', 'part_of', '', 'current', None),
            ('R2', 'A2', 'A', 'part_of', '', 'current', None),
            ('R3', 'A3', 'A', 'part_of', '', 'current', None),
            ('R4', 'A1', 'OUT', 'uses', '/private/source/file.pdf', 'current', .8),
            ('R5', 'OUT', 'A1', 'depends_on', '', 'current', .7),
            ('R6', 'A2', 'A1', 'supplies', '', 'current', .6),
            ('R7', 'OUT', 'A2', 'related_to', '', 'current', None),
            ('H', 'A1', 'B', 'part_of', '', 'historical', None),
            ('I', 'OLD', 'A1', 'part_of', '', 'current', None)])
    specs = tmp_path / 'specs'
    specs.mkdir()
    repo = Path(__file__).resolve().parents[1]
    for domain, root in [('ai_hardware', 'A'), ('semiconductor', 'B')]:
        value = json.loads((repo / 'research_navigation' / f'{domain}.json').read_text(encoding='utf-8'))
        value['root_node_ids'] = [root]
        (specs / f'{domain}.json').write_text(json.dumps(value), encoding='utf-8')
    config = SimpleNamespace(knowledge_db=db, state_db=tmp_path / 'workbench.db')
    nav = ResearchNavigation(config, spec_dir=specs)
    return ResearchStructureMap(config, navigation=nav), db


def test_hierarchy_relationship_focus_and_privacy(case):
    maps, db = case
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    hierarchy = maps.structure_map('ai_hardware')
    assert hierarchy['mode'] == 'hierarchy'
    assert hierarchy['stats'] == {'node_count': 4, 'edge_count': 3}
    assert {item['relation_id'] for item in hierarchy['edges']} == {'R1', 'R2', 'R3'}
    assert all(item['from_node_id'] != 'A' for item in hierarchy['edges'])
    selected_hierarchy = maps.structure_map('ai_hardware', mode='hierarchy', node_id='A1')
    assert {item['node_id'] for item in selected_hierarchy['nodes'] if item['on_selected_path']} == {'A', 'A1'}
    assert {item['relation_id'] for item in selected_hierarchy['edges'] if item['on_selected_path']} == {'R1'}
    direct = maps.structure_map('ai_hardware', mode='relationship', node_id='A1')
    assert direct['depth'] == 1
    assert {item['relation_id'] for item in direct['edges']} == {'R1', 'R4', 'R5', 'R6'}
    assert {item['node_id'] for item in direct['nodes']} == {'A', 'A1', 'A2', 'OUT'}
    assert next(item for item in direct['nodes'] if item['node_id'] == 'OUT')['in_navigation_context'] is False
    assert next(item for item in direct['edges'] if item['relation_id'] == 'R4')['scope'] == '[redacted]'
    assert '/private/' not in json.dumps(direct)
    focus = maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=2)
    assert focus['stats'] == {'node_count': 5, 'edge_count': 7}
    assert next(item for item in focus['nodes'] if item['node_id'] == 'OUT')['distance'] == 2
    assert all(item['status'] == 'active' for item in focus['nodes'])
    assert all(item['status'] == 'current' for item in focus['edges'])
    assert focus == maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=2)
    assert len(focus['snapshot_id']) == 64
    assert focus['semantic_groups_sha256'] == SEMANTIC_GROUPS_SHA256
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


def test_validation_depth_and_semantic_groups(case):
    maps, _ = case
    assert RELATION_GROUPS['part_of'] == 'structure'
    assert RELATION_GROUPS['uses'] == 'supply_flow'
    assert RELATION_GROUPS['depends_on'] == 'dependency'
    assert RELATION_GROUPS['competes_with'] == 'competition'
    assert RELATION_GROUPS['related_to'] == 'general_association'
    with pytest.raises(ResearchError, match='NAVIGATION_DOMAIN_NOT_FOUND'):
        maps.structure_map('missing')
    with pytest.raises(ResearchError, match='INVALID_STRUCTURE_MAP_MODE'):
        maps.structure_map('ai_hardware', mode='invented')
    with pytest.raises(ResearchError, match='STRUCTURE_MAP_NODE_REQUIRED'):
        maps.structure_map('ai_hardware', mode='relationship')
    with pytest.raises(ResearchError, match='STRUCTURE_MAP_NODE_NOT_ACTIVE'):
        maps.structure_map('ai_hardware', mode='focus', node_id='OLD')
    with pytest.raises(ResearchError, match='STRUCTURE_MAP_NODE_NOT_ACTIVE'):
        maps.structure_map('ai_hardware', mode='focus', node_id='UNKNOWN')
    for depth in (0, 4):
        with pytest.raises(ResearchError, match='INVALID_STRUCTURE_MAP_DEPTH'):
            maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=depth)
    assert maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=1)['stats']['node_count'] == 4
    assert maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=3)['depth'] == 3


def test_cycles_duplicates_and_bounds(case, monkeypatch):
    maps, db = case
    with sqlite3.connect(db) as conn:
        conn.executemany('INSERT INTO node_relations VALUES(?,?,?,?,?,?,?)', [
            ('CYCLE', 'A', 'A1', 'part_of', '', 'current', None),
            ('PARALLEL', 'A1', 'A', 'part_of', '', 'current', None)])
    result = maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=3)
    assert len({item['node_id'] for item in result['nodes']}) == result['stats']['node_count']
    assert len({item['relation_id'] for item in result['edges']}) == result['stats']['edge_count']
    assert result['stats']['node_count'] <= 80 and result['stats']['edge_count'] <= 160
    monkeypatch.setattr(structure_module, 'MAX_MAP_NODES', 2)
    small = maps.structure_map('ai_hardware', mode='relationship', node_id='A')
    assert small['stats']['node_count'] == 2
    assert small['truncated'] and 'max_nodes' in small['truncation_reasons']
    monkeypatch.setattr(structure_module, 'MAX_MAP_NODES', 80)
    monkeypatch.setattr(structure_module, 'MAX_MAP_EDGES', 1)
    small = maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=2)
    assert small['stats']['edge_count'] == 1
    assert small['truncated'] and 'max_edges' in small['truncation_reasons']
    assert small == maps.structure_map('ai_hardware', mode='focus', node_id='A', depth=2)
