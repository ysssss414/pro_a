"""Read-only presentation of frozen, HUMAN_USER-qualified cross-domain decisions."""
from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path

from pro_a.production_promotion import canonical_sha256, sha256_file
from pro_a.research_explorer import ResearchError
from pro_a.research_navigation import _readonly
from pro_a.research_structure_map import (MAX_FOCUS_DEPTH, MAX_MAP_EDGES, MAX_MAP_NODES,
                                          RELATION_GROUPS, ResearchStructureMap, _safe_scope)

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = ROOT / 'research_overlay/phase43_stage3_cross_domain_v1.json'
MANIFEST = ROOT / 'docs/phase43_stage4d_overlay_source_manifest.json'
STAGE2_AUTH = ROOT / 'docs/phase43_stage2_human_authorization.json'
STAGE3_DECISIONS = ROOT / 'docs/phase43_stage3_human_decisions_completed.json'
EXPECTED_OVERLAY_SHA = 'aa917e07895d7912e5bfe9c41763af3fbd705127a6fd797e858f1bef2816bfb5'
EXPECTED_PRODUCTION_SHA = '6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1'
EXPECTED_STAGE2_SHA = '23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f'
EXPECTED_STAGE3_SHA = '34f91757f881e26f87502e1ae096ec24b8e207d85ba218d5be8179867940ef52'


def fail():
    raise ResearchError('QUALIFIED_OVERLAY_BINDING_FAILED')


class QualifiedResearchOverlay:
    def __init__(self, config, *, structure_map=None, overlay_path=None, manifest_path=None):
        self.config = config
        self.structure_map_service = structure_map or ResearchStructureMap(config)
        self.overlay_path = overlay_path or OVERLAY
        self.manifest_path = manifest_path or MANIFEST

    def _load(self):
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding='utf-8'))
            if sha256_file(self.config.knowledge_db) != EXPECTED_PRODUCTION_SHA:
                fail()
            if sha256_file(STAGE2_AUTH) != EXPECTED_STAGE2_SHA or sha256_file(STAGE3_DECISIONS) != EXPECTED_STAGE3_SHA:
                fail()
            if sha256_file(self.overlay_path) != manifest['overlay_file_sha256']:
                fail()
            overlay = json.loads(self.overlay_path.read_text(encoding='utf-8'))
            digest = overlay.pop('overlay_sha256')
            if (digest != EXPECTED_OVERLAY_SHA or canonical_sha256(overlay) != digest or
                    manifest['overlay_sha256'] != digest or
                    overlay['source_bindings']['production_sha256'] != EXPECTED_PRODUCTION_SHA or
                    overlay['source_bindings']['stage2_human_authorization_sha256'] != EXPECTED_STAGE2_SHA or
                    overlay['source_bindings']['stage3_completed_decisions_sha256'] != EXPECTED_STAGE3_SHA or
                    overlay['counts']['stage2_support'] != 17 or
                    overlay['counts']['endpoint_references'] != 26 or
                    len(overlay['relations']['create']) != 38):
                fail()
            overlay['overlay_sha256'] = digest
            return overlay
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ResearchError('QUALIFIED_OVERLAY_BINDING_FAILED') from error

    def summary(self):
        value = self._load()
        return {
            'overlay_id': value['overlay_id'], 'contract_version': value['contract_version'],
            'overlay_sha256': value['overlay_sha256'], 'binding_status': 'PASS',
            'qualification_stage': value['qualification_stage'],
            'population_sha256': value['source_bindings']['stage3_population_sha256'],
            'human_decisions_sha256': value['source_bindings']['stage3_completed_decisions_sha256'],
            'production_sha256': value['source_bindings']['production_sha256'],
            'identity': value['counts']['stage3_identity'],
            'relations': value['counts']['stage3_relation'],
            'stage2_support_nodes': value['counts']['stage2_support'],
            'endpoint_references': value['counts']['endpoint_references'],
            'visible_qualified_nodes': len(value['identities']['stage3_create']) + len(value['identities']['stage2_support']),
            'canonical_reuse_annotations': value['counts']['unique_reuse_targets'],
            'visible_qualified_relations': len(value['relations']['create']),
            'full_identity_authority_relations': value['counts']['full_identity_authority_relations'],
            'reference_backed_relations': value['counts']['reference_backed_relations'],
        }

    def node(self, candidate_id):
        value = self._load()
        for key in ('stage3_create', 'stage2_support'):
            for row in value['identities'][key]:
                if row['candidate_id'] == candidate_id:
                    relations = [rel for rel in value['relations']['create']
                                 if row['visual_id'] in (rel['from_visual_id'], rel['to_visual_id'])]
                    return {**row, 'knowledge_state': 'qualified_identity', 'production_canonical': False,
                            'relations': relations, 'current_view': None,
                            'current_view_message': 'No Official Current View — object is not in Production.'}
        raise ResearchError('QUALIFIED_NODE_NOT_FOUND', 404)

    def relation(self, candidate_id):
        value = self._load()
        for row in value['relations']['create']:
            if row['candidate_id'] == candidate_id:
                return {**row, 'knowledge_state': 'qualified_relation',
                        'qualification_population_sha256': value['source_bindings']['stage3_population_sha256'],
                        'qualification_decision_sha256': value['source_bindings']['stage3_completed_decisions_sha256']}
        raise ResearchError('QUALIFIED_RELATION_NOT_FOUND', 404)

    def canonical_provenance(self, node_id):
        value = self._load()
        with _readonly(self.config.knowledge_db) as conn:
            if not conn.execute("SELECT 1 FROM nodes WHERE node_id=? AND status='active'", (node_id,)).fetchone():
                raise ResearchError('NODE_NOT_FOUND', 404)
        visual = 'canonical:' + node_id
        return {'node_id': node_id,
                'qualified_reuse_candidates': [row for row in value['identities']['reuse']
                                               if row['reuse_target_node_id'] == node_id],
                'qualified_relations': [row for row in value['relations']['create']
                                        if visual in (row['from_visual_id'], row['to_visual_id'])],
                'production_applied': False}

    def governance(self):
        value = self._load()
        return {
            'deferred_identities': value['identities']['deferred'],
            'deferred_relations': value['relations']['deferred'],
            'rejected_identities': value['identities']['rejected'],
            'endpoint_references': value['endpoint_references'],
        }

    def search(self, query):
        value = self._load()
        term = query.strip().casefold()
        if len(term) < 2:
            return {'results': []}
        rows = [row for key in ('stage3_create', 'stage2_support')
                for row in value['identities'][key]
                if term in row['display_name'].casefold()]
        rows.sort(key=lambda row: (row['display_name'].casefold(), row['candidate_id']))
        return {'results': [{'candidate_id': row['candidate_id'], 'display_name': row['display_name'],
                             'primary_type': row['primary_type'], 'qualification_stage': row['qualification_stage'],
                             'knowledge_state': 'qualified_identity', 'production_applied': False}
                            for row in rows[:30]]}

    def structure_map(self, domain_id, *, mode=None, node_id=None, qualified_id=None, depth=None):
        value = self._load()
        if node_id and qualified_id:
            raise ResearchError('QUALIFIED_SELECTION_CONFLICT')
        mode = mode or ('relationship' if node_id or qualified_id else 'hierarchy')
        if mode not in ('hierarchy', 'relationship', 'focus'):
            raise ResearchError('INVALID_STRUCTURE_MAP_MODE')
        if mode != 'hierarchy' and not (node_id or qualified_id):
            raise ResearchError('STRUCTURE_MAP_NODE_REQUIRED')
        if depth is not None and (mode != 'focus' or type(depth) is not int or not 1 <= depth <= MAX_FOCUS_DEPTH):
            raise ResearchError('INVALID_STRUCTURE_MAP_DEPTH')
        requested_depth = depth or 2 if mode == 'focus' else 1
        canonical_hierarchy = self.structure_map_service.structure_map(domain_id, mode='hierarchy')
        navigation = {row['node_id'] for row in canonical_hierarchy['nodes']}
        with _readonly(self.config.knowledge_db) as conn:
            all_nodes = {row['node_id']: dict(row) for row in conn.execute(
                "SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE status='active'")}
            all_edges = [dict(row) for row in conn.execute('''
                SELECT r.relation_id,r.from_node_id,r.to_node_id,r.relation_type,r.scope,r.status,r.confidence
                FROM node_relations r JOIN nodes a ON a.node_id=r.from_node_id AND a.status='active'
                JOIN nodes b ON b.node_id=r.to_node_id AND b.status='active'
                WHERE r.status='current' ''')]
        if node_id and node_id not in all_nodes:
            raise ResearchError('STRUCTURE_MAP_NODE_NOT_ACTIVE', 404)
        qualified_rows = {row['candidate_id']: row for key in ('stage3_create', 'stage2_support')
                          for row in value['identities'][key]}
        if qualified_id and qualified_id not in qualified_rows:
            raise ResearchError('QUALIFIED_NODE_NOT_FOUND', 404)
        reuse = {}
        for row in value['identities']['reuse']:
            reuse.setdefault(row['reuse_target_node_id'], []).append(row['candidate_id'])
        nodes = {}
        for nid, row in all_nodes.items():
            visual = 'canonical:' + nid
            nodes[visual] = {
                'visual_id': visual, 'knowledge_state': 'canonical', 'canonical_node_id': nid,
                'qualified_candidate_id': None, 'endpoint_reference_id': None,
                'display_name': row['canonical_name'], 'primary_type': row['primary_type'],
                'qualified_reuse_candidate_ids': sorted(reuse.get(nid, [])),
                'in_navigation_context': nid in navigation,
            }
        for row in qualified_rows.values():
            nodes[row['visual_id']] = {
                'visual_id': row['visual_id'], 'knowledge_state': 'qualified_identity',
                'canonical_node_id': None, 'qualified_candidate_id': row['candidate_id'],
                'endpoint_reference_id': None, 'display_name': row['display_name'],
                'primary_type': row['primary_type'], 'qualification_stage': row['qualification_stage'],
                'in_navigation_context': False,
            }
        for row in value['endpoint_references']:
            nodes[row['visual_id']] = {
                'visual_id': row['visual_id'], 'knowledge_state': 'relation_endpoint_reference',
                'canonical_node_id': None, 'qualified_candidate_id': None,
                'endpoint_reference_id': row['candidate_ref'], 'display_name': row['display_name'],
                'primary_type': row['primary_type'], 'identity_qualified': False,
                'relation_anchor_eligible': True, 'in_navigation_context': False,
            }
        edges = [{
            'visual_id': 'canonical:' + row['relation_id'], 'knowledge_state': 'canonical',
            'canonical_relation_id': row['relation_id'], 'qualified_relation_id': None,
            'from_visual_id': 'canonical:' + row['from_node_id'],
            'to_visual_id': 'canonical:' + row['to_node_id'], 'relation_type': row['relation_type'],
            'semantic_group': RELATION_GROUPS[row['relation_type']], 'scope': _safe_scope(row['scope']),
            'confidence': row['confidence'], 'from_endpoint_authority': 'production_canonical',
            'to_endpoint_authority': 'production_canonical',
        } for row in all_edges]
        edges += [{
            'visual_id': row['visual_id'], 'knowledge_state': 'qualified_relation',
            'canonical_relation_id': None, 'qualified_relation_id': row['candidate_id'],
            'from_visual_id': row['from_visual_id'], 'to_visual_id': row['to_visual_id'],
            'relation_type': row['relation_type'], 'semantic_group': RELATION_GROUPS[row['relation_type']],
            'scope': row['scope'], 'confidence': None,
            'from_endpoint_authority': row['from_endpoint_authority'],
            'to_endpoint_authority': row['to_endpoint_authority'],
            'qualification_provenance': 'Phase 4.3 Stage 3 · HUMAN_USER · not applied',
            'candidate_content_sha256': row['candidate_content_sha256'],
            'qualification_population_sha256': row['qualification_population_sha256'],
            'qualification_decision_sha256': row['qualification_decision_sha256'],
        } for row in value['relations']['create']]
        selected = ('canonical:' + node_id if node_id else
                    qualified_rows[qualified_id]['visual_id'] if qualified_id else None)
        reasons = set(canonical_hierarchy['truncation_reasons'] if mode == 'hierarchy' else ())
        omitted = 0
        if mode == 'hierarchy':
            included = {'canonical:' + row['node_id'] for row in canonical_hierarchy['nodes']}
            distances = {'canonical:' + row['node_id']: row['distance'] for row in canonical_hierarchy['nodes']}
            hierarchy_edges = {'canonical:' + row['relation_id'] for row in canonical_hierarchy['edges']}
            candidates = [row for row in edges if row['visual_id'] in hierarchy_edges]
            pending = [row for row in edges if row['knowledge_state'] == 'qualified_relation'
                       and row['relation_type'] == 'part_of']
            omitted = sum(any(endpoint.startswith('endpoint-ref:') for endpoint in
                              (row['from_visual_id'], row['to_visual_id'])) for row in pending)
            pending = [row for row in pending if not any(endpoint.startswith('endpoint-ref:') for endpoint in
                       (row['from_visual_id'], row['to_visual_id']))]
            changed = True
            while changed:
                changed = False
                for row in pending:
                    child, parent = row['from_visual_id'], row['to_visual_id']
                    if parent in included and child not in included and len(included) < MAX_MAP_NODES:
                        included.add(child); distances[child] = distances[parent] + 1; changed = True
                    if child in included and parent in included and row not in candidates:
                        candidates.append(row)
            if len(included) >= MAX_MAP_NODES and any(row['to_visual_id'] in included and
                                                      row['from_visual_id'] not in included for row in pending):
                reasons.add('max_nodes')
        else:
            adjacent = {key: set() for key in nodes}
            for row in edges:
                a, b = row['from_visual_id'], row['to_visual_id']
                adjacent[a].add(b); adjacent[b].add(a)
            distances = {selected: 0}
            queue = deque([selected])
            while queue:
                current = queue.popleft()
                if distances[current] >= requested_depth:
                    continue
                for neighbor in sorted(adjacent[current], key=lambda key: (nodes[key]['display_name'].casefold(), key)):
                    if neighbor in distances:
                        continue
                    if len(distances) >= MAX_MAP_NODES:
                        reasons.add('max_nodes'); continue
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
            included = set(distances)
            candidates = [row for row in edges if row['from_visual_id'] in included and
                          row['to_visual_id'] in included and
                          (mode == 'focus' or selected in (row['from_visual_id'], row['to_visual_id']))]
        ordered_nodes = sorted(included, key=lambda key: (distances[key], nodes[key]['display_name'].casefold(), key))
        if len(ordered_nodes) > MAX_MAP_NODES:
            reasons.add('max_nodes'); ordered_nodes = ordered_nodes[:MAX_MAP_NODES]
        included = set(ordered_nodes)
        ordered_edges = sorted((row for row in candidates if row['from_visual_id'] in included and
                                row['to_visual_id'] in included),
                               key=lambda row: (min(distances[row['from_visual_id']], distances[row['to_visual_id']]),
                                                row['relation_type'], row['visual_id']))
        if len(ordered_edges) > MAX_MAP_EDGES:
            reasons.add('max_edges'); ordered_edges = ordered_edges[:MAX_MAP_EDGES]
        projected = [{**nodes[key], 'distance': distances[key], 'selected': key == selected}
                     for key in ordered_nodes]
        result = {
            'domain_id': domain_id, 'display_name': canonical_hierarchy['display_name'], 'mode': mode,
            'selected_node_id': node_id, 'selected_qualified_id': qualified_id,
            'selected_visual_id': selected, 'depth': requested_depth,
            'nodes': projected, 'edges': ordered_edges,
            'stats': {'canonical_nodes': sum(row['knowledge_state'] == 'canonical' for row in projected),
                      'qualified_nodes': sum(row['knowledge_state'] == 'qualified_identity' for row in projected),
                      'endpoint_references': sum(row['knowledge_state'] == 'relation_endpoint_reference' for row in projected),
                      'canonical_relations': sum(row['knowledge_state'] == 'canonical' for row in ordered_edges),
                      'qualified_relations': sum(row['knowledge_state'] == 'qualified_relation' for row in ordered_edges)},
            'omitted_reference_hierarchy_relations': omitted,
            'contains_relation_scoped_reference': any(row['knowledge_state'] == 'relation_endpoint_reference'
                                                      for row in projected),
            'truncated': bool(reasons), 'truncation_reasons': sorted(reasons),
            'max_map_nodes': MAX_MAP_NODES, 'max_map_edges': MAX_MAP_EDGES,
            'max_focus_depth': MAX_FOCUS_DEPTH, 'overlay_sha256': value['overlay_sha256'],
        }
        result['snapshot_id'] = canonical_sha256(result)
        return result
