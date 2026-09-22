"""Read-only presentation navigation over current canonical part_of relations."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from pro_a.domain_packs import load_pack
from pro_a.research_explorer import ResearchError

DOMAIN_IDS = ('ai_hardware', 'semiconductor')
MAX_REQUESTED_DEPTH = 12
MAX_TREE_NODES = 1000
_REPO = Path(__file__).resolve().parents[2]
_SPEC_FIELDS = {'contract_version', 'domain_id', 'display_name', 'root_node_ids',
                'hierarchy_relation', 'default_max_depth', 'domain_pack'}


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _unique_fields(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate navigation spec field')
        value[key] = item
    return value


@contextmanager
def _readonly(path):
    connection = sqlite3.connect(f'{Path(path).resolve(strict=True).as_uri()}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    try:
        connection.execute('BEGIN')
        yield connection
    finally:
        connection.close()


class ResearchNavigation:
    def __init__(self, config, *, spec_dir: Path | None = None, packs_dir: Path | None = None):
        self.config = config
        self.spec_dir = spec_dir or _REPO / 'research_navigation'
        self.packs_dir = packs_dir or _REPO / 'domains'

    def _metadata(self, domain_id):
        path = Path(self.config.state_db)
        if not path.is_file():
            return 'NOT_REGISTERED'
        with _readonly(path) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='domain_pack_registry'").fetchone():
                return 'NOT_REGISTERED'
            rows = conn.execute('SELECT version,sha256 FROM domain_pack_registry WHERE domain_id=?', (domain_id,)).fetchall()
            return [(row['version'], row['sha256']) for row in rows] if rows else 'NOT_REGISTERED'

    def _spec(self, domain_id):
        if domain_id not in DOMAIN_IDS:
            raise ResearchError('NAVIGATION_DOMAIN_NOT_FOUND', 404)
        path = self.spec_dir / f'{domain_id}.json'
        try:
            raw = path.read_bytes()
            spec = json.loads(raw, object_pairs_hook=_unique_fields)
            valid = (isinstance(spec, dict) and set(spec) == _SPEC_FIELDS
                     and spec['contract_version'] == 'research-navigation-v1'
                     and spec['domain_id'] == domain_id
                     and isinstance(spec['display_name'], str)
                     and 1 <= len(spec['display_name']) <= 80
                     and not any(char in spec['display_name'] for char in '/\\\r\n')
                     and spec['hierarchy_relation'] == 'part_of'
                     and type(spec['default_max_depth']) is int
                     and 0 <= spec['default_max_depth'] <= 8
                     and isinstance(spec['root_node_ids'], list)
                     and 1 <= len(spec['root_node_ids']) <= MAX_TREE_NODES
                     and len(set(spec['root_node_ids'])) == len(spec['root_node_ids'])
                     and all(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_:-]{1,100}', value)
                             for value in spec['root_node_ids'])
                     and isinstance(spec['domain_pack'], dict)
                     and set(spec['domain_pack']) == {'version', 'sha256'})
            if not valid:
                raise ValueError('invalid navigation spec')
            pack = load_pack(self.packs_dir / domain_id)
            if (pack.identity != {'domain_id': domain_id, **spec['domain_pack']}):
                raise ValueError('domain pack identity drift')
            registered = self._metadata(domain_id)
            if registered != 'NOT_REGISTERED' and (pack.identity['version'], pack.sha256) not in registered:
                raise ValueError('domain pack registry identity drift')
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ResearchError('NAVIGATION_SPEC_INVALID') from error
        return spec, hashlib.sha256(raw).hexdigest(), pack.manifest['lifecycle']['state'], registered != 'NOT_REGISTERED'

    def validate_navigation_specs(self):
        with _readonly(self.config.knowledge_db) as conn:
            for domain_id in DOMAIN_IDS:
                spec, _, _, _ = self._spec(domain_id)
                for root in spec['root_node_ids']:
                    row = conn.execute('SELECT status FROM nodes WHERE node_id=?', (root,)).fetchone()
                    if row is None or row['status'] != 'active':
                        raise ResearchError('NAVIGATION_ROOT_NOT_ACTIVE')
        return True

    @staticmethod
    def _graph(conn):
        nodes = {row['node_id']: dict(row) for row in conn.execute(
            'SELECT node_id,canonical_name,primary_type,status FROM nodes')}
        children = {node_id: set() for node_id in nodes}
        for row in conn.execute('''SELECT from_node_id,to_node_id FROM node_relations
                                   WHERE relation_type='part_of' AND status='current' '''):
            if row['from_node_id'] in nodes and row['to_node_id'] in nodes:
                children[row['to_node_id']].add(row['from_node_id'])
        ordered = {key: sorted(ids, key=lambda child: (nodes[child]['canonical_name'].casefold(), child))
                   for key, ids in children.items()}
        return nodes, ordered

    def domain_tree(self, domain_id, *, max_depth=None):
        spec, sha, lifecycle, registered = self._spec(domain_id)
        depth_limit = spec['default_max_depth'] if max_depth is None else max_depth
        if type(depth_limit) is not int or not 0 <= depth_limit <= MAX_REQUESTED_DEPTH:
            raise ResearchError('INVALID_NAVIGATION_DEPTH')
        with _readonly(self.config.knowledge_db) as conn:
            nodes, children = self._graph(conn)
        if any(root not in nodes or nodes[root]['status'] != 'active' for root in spec['root_node_ids']):
            raise ResearchError('NAVIGATION_ROOT_NOT_ACTIVE')
        visible, deepest, truncation, visited = 0, 0, set(), set()

        def visit(node_id, depth, ancestors):
            nonlocal visible, deepest
            visible += 1
            deepest = max(deepest, depth)
            value = {**nodes[node_id], 'depth': depth, 'child_count': len(children[node_id]),
                     'has_children': bool(children[node_id]), 'children': []}
            if node_id in ancestors:
                value['anomaly'] = 'cycle'
                return value
            if node_id in visited:
                value['anomaly'] = 'duplicate_path'
                return value
            visited.add(node_id)
            if depth >= depth_limit:
                if children[node_id]:
                    truncation.add('max_depth')
                return value
            for child in children[node_id]:
                if visible >= MAX_TREE_NODES:
                    truncation.add('max_nodes')
                    break
                value['children'].append(visit(child, depth + 1, ancestors | {node_id}))
            return value

        roots = []
        for root in spec['root_node_ids']:
            if visible >= MAX_TREE_NODES:
                truncation.add('max_nodes')
                break
            roots.append(visit(root, 0, set()))
        result = {'domain_id': domain_id, 'display_name': spec['display_name'],
                  'navigation_spec_version': spec['contract_version'], 'navigation_spec_sha256': sha,
                  'domain_pack_version': spec['domain_pack']['version'],
                  'domain_pack_sha256': spec['domain_pack']['sha256'],
                  'domain_pack_lifecycle': lifecycle, 'domain_pack_registered': registered,
                  'root_count': len(spec['root_node_ids']), 'roots': roots,
                  'visible_node_count': visible, 'max_tree_depth': deepest,
                  'max_requested_depth': depth_limit, 'max_tree_nodes': MAX_TREE_NODES,
                  'truncated': bool(truncation), 'truncation_reasons': sorted(truncation),
                  'sort_contract': 'canonical_name.casefold(), node_id'}
        result['snapshot_id'] = _hash(result)
        return result

    def list_domains(self):
        items = []
        for domain_id in DOMAIN_IDS:
            tree = self.domain_tree(domain_id)
            items.append({key: tree[key] for key in (
                'domain_id', 'display_name', 'navigation_spec_version', 'navigation_spec_sha256',
                'domain_pack_version', 'domain_pack_sha256', 'domain_pack_lifecycle',
                'domain_pack_registered', 'root_count', 'visible_node_count', 'max_tree_depth', 'truncated')}
                         | {'root_nodes': [{key: node[key] for key in ('node_id', 'canonical_name', 'primary_type', 'status')}
                                           for node in tree['roots']]})
        return {'domains': items, 'snapshot_id': _hash(items)}

    def node_domain_context(self, node_id):
        with _readonly(self.config.knowledge_db) as conn:
            if not conn.execute('SELECT 1 FROM nodes WHERE node_id=?', (node_id,)).fetchone():
                raise ResearchError('NODE_NOT_FOUND', 404)
        contexts = []
        for domain_id in DOMAIN_IDS:
            tree = self.domain_tree(domain_id, max_depth=MAX_REQUESTED_DEPTH)

            def walk(node, root_id, path):
                route = [*path, node['node_id']]
                if node['node_id'] == node_id and 'anomaly' not in node:
                    contexts.append({'domain_id': domain_id, 'display_name': tree['display_name'],
                                     'root_node_id': root_id, 'path_from_root': route,
                                     'depth': node['depth']})
                for child in node['children']:
                    walk(child, root_id, route)

            for root in tree['roots']:
                walk(root, root['node_id'], [])
        assignments = []
        path = Path(self.config.state_db)
        if path.is_file():
            with _readonly(path) as conn:
                if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='domain_assignments'").fetchone():
                    assignments = [dict(row) for row in conn.execute('''SELECT primary_domain,revision
                        FROM domain_assignments WHERE object_type='Node' AND object_id=?
                        ORDER BY revision DESC LIMIT 1''', (node_id,))]
        return {'node_id': node_id, 'navigation_contexts': contexts,
                'operational_domain_assignments': assignments}
