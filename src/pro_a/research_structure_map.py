"""Bounded, read-only maps of current canonical Nodes and Relations."""
from __future__ import annotations

from collections import deque

from pro_a.research_explorer import ResearchError
from pro_a.research_navigation import ResearchNavigation, _hash, _readonly

MAX_MAP_NODES = 80
MAX_MAP_EDGES = 160
MAX_FOCUS_DEPTH = 3

SEMANTIC_GROUPS = {
    'structure': ('part_of',),
    'supply_flow': ('upstream_of', 'supplies', 'produces', 'uses', 'applied_in'),
    'dependency': ('depends_on', 'constrains', 'drives', 'benefits_from', 'exposed_to',
                   'regulated_by', 'validates', 'invalidates'),
    'competition': ('substitutes', 'competes_with'),
    'general_association': ('related_to',),
}
RELATION_GROUPS = {relation: group for group, relations in SEMANTIC_GROUPS.items()
                   for relation in relations}
SEMANTIC_GROUPS_SHA256 = _hash(SEMANTIC_GROUPS)


def _safe_scope(value):
    if value and ('/' in value or '\\' in value):
        return '[redacted]'
    return value or ''


def _node_order(node, distance):
    return distance[node['node_id']], node['canonical_name'].casefold(), node['node_id']


def _edge_order(edge, distance):
    return (min(distance[edge['from_node_id']], distance[edge['to_node_id']]),
            edge['relation_type'], edge['from_node_id'], edge['to_node_id'], edge['relation_id'])


class ResearchStructureMap:
    def __init__(self, config, *, navigation=None):
        self.config = config
        self.navigation = navigation or ResearchNavigation(config)

    def structure_map(self, domain_id, *, mode=None, node_id=None, depth=None):
        tree = self.navigation.domain_tree(domain_id)
        mode = ('relationship' if node_id else 'hierarchy') if mode is None else mode
        if mode not in ('hierarchy', 'relationship', 'focus'):
            raise ResearchError('INVALID_STRUCTURE_MAP_MODE')
        if mode != 'hierarchy' and not node_id:
            raise ResearchError('STRUCTURE_MAP_NODE_REQUIRED')
        if depth is not None and (mode != 'focus' or type(depth) is not int or not 1 <= depth <= MAX_FOCUS_DEPTH):
            raise ResearchError('INVALID_STRUCTURE_MAP_DEPTH')
        requested_depth = (depth or 2) if mode == 'focus' else (1 if mode == 'relationship' else tree['max_requested_depth'])

        with _readonly(self.config.knowledge_db) as conn:
            nodes = {row['node_id']: dict(row) for row in conn.execute('''
                SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE status='active' ''')}
            if node_id and node_id not in nodes:
                raise ResearchError('STRUCTURE_MAP_NODE_NOT_ACTIVE', 404)
            edges = [dict(row) for row in conn.execute('''
                SELECT r.relation_id,r.from_node_id,r.to_node_id,r.relation_type,
                       r.scope,r.status,r.confidence
                FROM node_relations r
                JOIN nodes source ON source.node_id=r.from_node_id AND source.status='active'
                JOIN nodes target ON target.node_id=r.to_node_id AND target.status='active'
                WHERE r.status='current' ''')]
        for edge in edges:
            group = RELATION_GROUPS.get(edge['relation_type'])
            if group is None:
                raise ResearchError('UNKNOWN_CANONICAL_RELATION_TYPE')
            edge['semantic_group'] = group
            edge['scope'] = _safe_scope(edge['scope'])

        navigation_depth = {}
        hierarchy_pairs = set()
        selected_path = set()

        def walk(item, parent=None, path=()):
            current = item['node_id']
            if current not in nodes or 'anomaly' in item:
                return
            navigation_depth.setdefault(current, item['depth'])
            if current == node_id:
                selected_path.update((*path, current))
            if parent is not None:
                hierarchy_pairs.add((current, parent))  # canonical child -> parent
            for child in item['children']:
                walk(child, current, (*path, current))

        for root in tree['roots']:
            walk(root)

        reasons = set(tree['truncation_reasons'] if mode == 'hierarchy' else ())
        if mode == 'hierarchy':
            distances = dict(navigation_depth)
            candidates = [edge for edge in edges if edge['relation_type'] == 'part_of'
                          and (edge['from_node_id'], edge['to_node_id']) in hierarchy_pairs]
        else:
            adjacent = {key: set() for key in nodes}
            for edge in edges:
                a, b = edge['from_node_id'], edge['to_node_id']
                adjacent[a].add(b)
                adjacent[b].add(a)
            distances = {node_id: 0}
            queue = deque([node_id])
            while queue:
                current = queue.popleft()
                if distances[current] >= requested_depth:
                    continue
                neighbors = sorted(adjacent[current], key=lambda key: (nodes[key]['canonical_name'].casefold(), key))
                for neighbor in neighbors:
                    if neighbor in distances:
                        continue
                    if len(distances) >= MAX_MAP_NODES:
                        reasons.add('max_nodes')
                        continue
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
            candidates = [edge for edge in edges if edge['from_node_id'] in distances
                          and edge['to_node_id'] in distances
                          and (mode == 'focus' or node_id in (edge['from_node_id'], edge['to_node_id']))]

        ordered_nodes = sorted((nodes[key] for key in distances), key=lambda item: _node_order(item, distances))
        if len(ordered_nodes) > MAX_MAP_NODES:
            reasons.add('max_nodes')
            ordered_nodes = ordered_nodes[:MAX_MAP_NODES]
        included = {item['node_id'] for item in ordered_nodes}
        ordered_edges = sorted((edge for edge in candidates if edge['from_node_id'] in included
                                and edge['to_node_id'] in included), key=lambda item: _edge_order(item, distances))
        if len(ordered_edges) > MAX_MAP_EDGES:
            reasons.add('max_edges')
            ordered_edges = ordered_edges[:MAX_MAP_EDGES]
        projected_nodes = [{**item, 'distance': distances[item['node_id']],
                            'selected': item['node_id'] == node_id,
                            'on_selected_path': mode == 'hierarchy' and item['node_id'] in selected_path,
                            'in_navigation_context': item['node_id'] in navigation_depth,
                            'navigation_depth': navigation_depth.get(item['node_id'])}
                           for item in ordered_nodes]
        if mode == 'hierarchy' and selected_path:
            for edge in ordered_edges:
                edge['on_selected_path'] = (edge['from_node_id'] in selected_path
                                            and edge['to_node_id'] in selected_path)
        result = {'domain_id': domain_id, 'display_name': tree['display_name'], 'mode': mode,
                  'selected_node_id': node_id, 'depth': requested_depth,
                  'nodes': projected_nodes, 'edges': ordered_edges,
                  'stats': {'node_count': len(projected_nodes), 'edge_count': len(ordered_edges)},
                  'available_relation_types': sorted({edge['relation_type'] for edge in ordered_edges}),
                  'truncated': bool(reasons), 'truncation_reasons': sorted(reasons),
                  'max_map_nodes': MAX_MAP_NODES, 'max_map_edges': MAX_MAP_EDGES,
                  'max_focus_depth': MAX_FOCUS_DEPTH,
                  'semantic_groups_sha256': SEMANTIC_GROUPS_SHA256}
        result['snapshot_id'] = _hash(result)
        return result
