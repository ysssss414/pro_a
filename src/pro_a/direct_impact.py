"""Deterministic, bounded direct-impact projection over recorded relationships."""
from __future__ import annotations

import base64
from contextlib import closing
from datetime import datetime, timezone
import json
from typing import Any

from .db import CURRENT_VIEW_ORDER
from .operational_contract import readonly, require
from .production_promotion import canonical_sha256
from .workbench.config import BoundaryError
from .workbench.review_store import schema_version
from .workbench.store import Store


ATTENTION_OUTCOMES = {'NO_CHANGE', 'MINOR', 'MATERIAL', 'THESIS'}
ROLE_ORDER = {'subject': 0, 'context': 1, 'related': 2}
REASON_ORDER = {
    'CLAIM_CITED_BY_VIEW': 0,
    'NODE_HAS_OFFICIAL_VIEW': 1,
    'CLAIM_ATTRIBUTED_TO_NODE': 2,
    'STAGED_VIEW_DEPENDENCY': 3,
    'RECORDED_CONTRADICTION': 4,
    'TEMPORAL_SUPERSESSION': 5,
    'RECORDED_RELATION_EVIDENCE': 6,
    'SOURCE_CONTAINS_CLAIM': 7,
}


class ImpactError(BoundaryError):
    def __init__(self, code: str, status: int = 409, current_revision: int | None = None):
        super().__init__(code)
        self.status = status
        self.current_revision = current_revision


def _json(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or '')
    except (TypeError, json.JSONDecodeError):
        return fallback
    return value if isinstance(value, type(fallback)) else fallback


def _step(object_type: str, object_id: str, label: str, status: str = '') -> dict[str, str]:
    return {'object_type': object_type, 'object_id': object_id, 'label': label, 'status': status or 'unknown'}


def _source_token(source_id: str) -> str:
    return base64.urlsafe_b64encode(source_id.encode()).decode().rstrip('=')


def _source_from_impact_id(impact_id: str) -> str:
    try:
        prefix, encoded, digest = impact_id.split('.')
        if prefix != 'IMP' or len(digest) != 64:
            raise ValueError
        return base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)).decode()
    except (ValueError, UnicodeError):
        raise ImpactError('IMPACT_PATH_NOT_FOUND', 404) from None


class DirectImpact:
    """All knowledge edges are read in one SQLite snapshot; there is no cache."""

    def __init__(self, config):
        self.config = config
        self.store = Store(config)

    @staticmethod
    def _item(source_id: str, *, impact_type: str, target_type: str, target_id: str,
              path_steps: list[dict[str, str]], relationship_types: list[str],
              reason_code: str, official_or_staged: str = 'RECORDED',
              attribution_role: str | None = None, evidence_refs: list[dict[str, str]] | None = None,
              temporal_status: dict[str, Any] | None = None,
              current_status: str = 'current', is_current_impact: bool = True) -> dict[str, Any]:
        identity = {
            'origin_type': 'SOURCE', 'origin_id': source_id, 'target_type': target_type,
            'target_id': target_id, 'impact_type': impact_type, 'reason_code': reason_code,
            'relationship_types': relationship_types,
            'path': [(step['object_type'], step['object_id']) for step in path_steps],
        }
        digest = canonical_sha256(identity)
        return {
            'impact_id': f'IMP.{_source_token(source_id)}.{digest}',
            'impact_type': impact_type,
            'origin_type': 'SOURCE', 'origin_id': source_id,
            'target_type': target_type, 'target_id': target_id,
            'path_steps': path_steps, 'relationship_types': relationship_types,
            'attribution_role': attribution_role,
            'official_or_staged': official_or_staged,
            'reason_code': reason_code,
            'evidence_refs': evidence_refs or [],
            'temporal_status': temporal_status or {'effective_date': 'unknown', 'temporal_relation': 'none'},
            'current_status': current_status or 'unknown',
            'is_current_impact': is_current_impact,
        }

    @staticmethod
    def _where(values: list[str]) -> tuple[str, tuple[str, ...]]:
        return ','.join('?' for _ in values), tuple(values)

    def _project(self, connection, sources: list[dict[str, Any]], query_count: list[int]) -> dict[str, Any]:
        source_ids = [row['source_id'] for row in sources]
        source_by_id = {row['source_id']: row for row in sources}
        if not source_ids:
            return self._finish([], {}, [], [], query_count)
        source_marks, source_args = self._where(source_ids)

        query_count[0] += 1
        claims = [dict(row) for row in connection.execute(
            f'''SELECT claim_id,statement,nature,fact_time,publication_time,ingestion_time,
                       source_id,status,confidence,evidence_pointer,evidence_excerpt
                FROM claims WHERE source_id IN ({source_marks}) ORDER BY source_id,claim_id''', source_args)]
        claim_ids = [row['claim_id'] for row in claims]
        claims_by_id = {row['claim_id']: row for row in claims}
        claim_marks, claim_args = self._where(claim_ids) if claim_ids else ('NULL', ())

        query_count[0] += 1
        links = [dict(row) for row in connection.execute(
            f'''SELECT l.claim_id,l.node_id,l.role,n.canonical_name,n.primary_type,n.status AS node_status
                FROM claim_node_links l JOIN nodes n ON n.node_id=l.node_id
                WHERE l.claim_id IN ({claim_marks}) ORDER BY l.claim_id,l.node_id''', claim_args)]

        query_count[0] += 1
        claim_relations = [dict(row) for row in connection.execute(
            f'''SELECT r.relation_id,r.from_claim_id,r.relation_type,r.to_claim_id,r.reason,r.created_at,
                       f.statement AS from_statement,f.status AS from_status,f.source_id AS from_source_id,
                       t.statement AS to_statement,t.status AS to_status,t.source_id AS to_source_id
                FROM claim_relations r JOIN claims f ON f.claim_id=r.from_claim_id
                JOIN claims t ON t.claim_id=r.to_claim_id
                WHERE r.from_claim_id IN ({claim_marks}) OR r.to_claim_id IN ({claim_marks})
                ORDER BY r.relation_id''', claim_args + claim_args)]
        related_claim_ids = sorted({r['from_claim_id'] for r in claim_relations} | {r['to_claim_id'] for r in claim_relations})
        relevant_claim_ids = sorted(set(claim_ids) | set(related_claim_ids))
        relevant_marks, relevant_args = self._where(relevant_claim_ids) if relevant_claim_ids else ('NULL', ())
        linked_node_ids = sorted({row['node_id'] for row in links})
        node_marks, node_args = self._where(linked_node_ids) if linked_node_ids else ('NULL', ())

        query_count[0] += 1
        view_rows = [dict(row) for row in connection.execute(
            f'''WITH ranked AS (
                    SELECT view_id,node_id,version,status,change_level,trigger_claim_ids_json,
                           revision_date,revision_seq,created_at,
                           ROW_NUMBER() OVER (PARTITION BY node_id ORDER BY {CURRENT_VIEW_ORDER}) AS view_rank
                    FROM current_views WHERE status='official')
                SELECT ranked.*,citation.value AS citation_id,
                       CASE WHEN cited.claim_id IS NULL THEN 0 ELSE 1 END AS citation_resolved
                FROM ranked
                LEFT JOIN json_each(CASE WHEN json_valid(ranked.trigger_claim_ids_json)
                    THEN ranked.trigger_claim_ids_json ELSE '[]' END) citation
                LEFT JOIN claims cited ON cited.claim_id=citation.value
                WHERE view_rank=1 AND (
                    node_id IN ({node_marks}) OR EXISTS (
                        SELECT 1 FROM json_each(CASE WHEN json_valid(trigger_claim_ids_json)
                            THEN trigger_claim_ids_json ELSE '[]' END) WHERE value IN ({relevant_marks})))
                ORDER BY node_id,view_id''', node_args + relevant_args)]
        view_map: dict[str, dict[str, Any]] = {}
        for row in view_rows:
            view = view_map.setdefault(row['view_id'], {key: row[key] for key in (
                'view_id', 'node_id', 'version', 'status', 'change_level', 'revision_date',
                'revision_seq', 'created_at', 'view_rank')})
            view.setdefault('trigger_claim_ids', [])
            view.setdefault('citation_refs', [])
            if isinstance(row['citation_id'], str):
                view['trigger_claim_ids'].append(row['citation_id'])
                view['citation_refs'].append({'claim_id': row['citation_id'],
                    'status': 'RESOLVED' if row['citation_resolved'] else 'EVIDENCE_NOT_RESOLVED'})
        views = list(view_map.values())
        view_by_node = {row['node_id']: row for row in views}

        query_count[0] += 1
        relation_evidence = [dict(row) for row in connection.execute(
            f'''SELECT e.relation_id,e.claim_id,e.evidence_role,e.status AS evidence_status,
                       e.provenance_mode,e.evidence_id,e.source_id,
                       r.from_node_id,r.relation_type,r.to_node_id,r.scope,r.valid_from,r.valid_to,
                       r.status AS relation_status,fn.canonical_name AS from_name,tn.canonical_name AS to_name,
                       t.temporal_category,t.valid_from_supplied,t.valid_to_supplied
                FROM relation_evidence_links e JOIN node_relations r ON r.relation_id=e.relation_id
                JOIN nodes fn ON fn.node_id=r.from_node_id JOIN nodes tn ON tn.node_id=r.to_node_id
                LEFT JOIN relation_temporal_semantics t ON t.relation_id=r.relation_id
                WHERE e.claim_id IN ({claim_marks}) OR (e.provenance_mode='RELATION_NATIVE' AND e.source_id IN ({source_marks}))
                ORDER BY e.relation_id,e.evidence_role,e.claim_id,e.evidence_id''', claim_args + source_args)]

        knowledge_basis = {'sources': sources, 'claims': claims, 'links': links, 'views': views,
                           'claim_relations': claim_relations, 'relation_evidence': relation_evidence}
        items: list[dict[str, Any]] = []
        source_steps = {sid: _step('SOURCE', sid, source_by_id[sid]['title'], source_by_id[sid]['status']) for sid in source_ids}

        for claim in claims:
            path = [source_steps[claim['source_id']], _step('CLAIM', claim['claim_id'], claim['statement'], claim['status'])]
            items.append(self._item(claim['source_id'], impact_type='CLAIM_CHANGE', target_type='CLAIM',
                target_id=claim['claim_id'], path_steps=path, relationship_types=['SOURCE_HAS_CLAIM'],
                reason_code='SOURCE_CONTAINS_CLAIM', evidence_refs=[{'claim_id': claim['claim_id'], 'source_id': claim['source_id']}],
                temporal_status={'effective_date': claim['fact_time'] or claim['publication_time'] or 'unknown',
                                 'temporal_relation': 'recorded_claim_status'}, current_status=claim['status'],
                is_current_impact=claim['status'] == 'current'))

        link_by_claim: dict[str, list[dict[str, Any]]] = {}
        for link in links:
            link_by_claim.setdefault(link['claim_id'], []).append(link)
            claim = claims_by_id[link['claim_id']]
            source_id = claim['source_id']
            claim_path = [source_steps[source_id], _step('CLAIM', claim['claim_id'], claim['statement'], claim['status'])]
            node_step = _step('NODE', link['node_id'], link['canonical_name'], link['node_status'])
            active = link['node_status'] == 'active'
            items.append(self._item(source_id, impact_type='DIRECT_NODE', target_type='NODE', target_id=link['node_id'],
                path_steps=claim_path + [node_step], relationship_types=['SOURCE_HAS_CLAIM', 'EXPLICIT_ATTRIBUTION'],
                attribution_role=link['role'], reason_code='CLAIM_ATTRIBUTED_TO_NODE',
                evidence_refs=[{'claim_id': claim['claim_id'], 'source_id': source_id}],
                current_status=link['node_status'], is_current_impact=active))
            view = view_by_node.get(link['node_id']) if active else None
            if view:
                items.append(self._item(source_id, impact_type='OFFICIAL_VIEW', target_type='VIEW', target_id=view['view_id'],
                    path_steps=claim_path + [node_step, _step('VIEW', view['view_id'], view['version'], 'official')],
                    relationship_types=['SOURCE_HAS_CLAIM', 'EXPLICIT_ATTRIBUTION', 'NODE_CURRENT_OFFICIAL_VIEW'],
                    attribution_role=link['role'], reason_code='NODE_HAS_OFFICIAL_VIEW', official_or_staged='OFFICIAL',
                    evidence_refs=[{'claim_id': claim['claim_id'], 'source_id': source_id}, *view['citation_refs']],
                    temporal_status={'effective_date': view['revision_date'] or 'unknown', 'temporal_relation': 'official_revision'},
                    current_status='official'))

        for view in views:
            for claim_id in sorted(set(view['trigger_claim_ids']) & set(claim_ids)):
                claim = claims_by_id[claim_id]
                source_id = claim['source_id']
                items.append(self._item(source_id, impact_type='OFFICIAL_VIEW', target_type='VIEW', target_id=view['view_id'],
                    path_steps=[source_steps[source_id], _step('CLAIM', claim_id, claim['statement'], claim['status']),
                                _step('VIEW', view['view_id'], view['version'], 'official')],
                    relationship_types=['SOURCE_HAS_CLAIM', 'EXPLICIT_VIEW_CITATION'],
                    reason_code='CLAIM_CITED_BY_VIEW', official_or_staged='OFFICIAL',
                    evidence_refs=[{'claim_id': claim_id, 'source_id': source_id}],
                    temporal_status={'effective_date': view['revision_date'] or 'unknown', 'temporal_relation': 'official_revision'},
                    current_status='official'))

        for relation in claim_relations:
            selected = relation['from_claim_id'] if relation['from_claim_id'] in claims_by_id else relation['to_claim_id']
            other = relation['to_claim_id'] if selected == relation['from_claim_id'] else relation['from_claim_id']
            claim = claims_by_id[selected]
            other_label = relation['to_statement'] if other == relation['to_claim_id'] else relation['from_statement']
            other_status = relation['to_status'] if other == relation['to_claim_id'] else relation['from_status']
            relation_type = relation['relation_type'].lower()
            if relation_type not in {'contradicts', 'updates'}:
                continue
            reason = 'RECORDED_CONTRADICTION' if relation_type == 'contradicts' else 'TEMPORAL_SUPERSESSION'
            source_id = claim['source_id']
            path = [source_steps[source_id], _step('CLAIM', selected, claim['statement'], claim['status']),
                    _step('CLAIM_RELATION', relation['relation_id'], relation_type, 'recorded'),
                    _step('CLAIM', other, other_label, other_status)]
            items.append(self._item(source_id, impact_type='CONTRADICTION' if relation_type == 'contradicts' else 'TEMPORAL_CHANGE',
                target_type='CLAIM', target_id=other, path_steps=path,
                relationship_types=['SOURCE_HAS_CLAIM', relation_type.upper()], reason_code=reason,
                evidence_refs=[{'claim_id': selected, 'source_id': source_id}, {'claim_id': other, 'source_id': relation['to_source_id'] if other == relation['to_claim_id'] else relation['from_source_id']}],
                temporal_status={'effective_date': relation['created_at'] or 'unknown', 'temporal_relation': relation_type,
                                 'superseded_state': other_status if relation_type == 'updates' else 'not_applicable'},
                current_status=other_status))
            for view in views:
                if other in view['trigger_claim_ids']:
                    items.append(self._item(source_id, impact_type='OFFICIAL_VIEW', target_type='VIEW', target_id=view['view_id'],
                        path_steps=path + [_step('VIEW', view['view_id'], view['version'], 'official')],
                        relationship_types=['SOURCE_HAS_CLAIM', relation_type.upper(), 'EXPLICIT_VIEW_CITATION'],
                        reason_code=reason, official_or_staged='OFFICIAL',
                        evidence_refs=[{'claim_id': selected, 'source_id': source_id}, {'claim_id': other, 'source_id': relation['to_source_id'] if other == relation['to_claim_id'] else relation['from_source_id']}],
                        temporal_status={'effective_date': view['revision_date'] or 'unknown', 'temporal_relation': relation_type},
                        current_status='official'))

        for relation in relation_evidence:
            claim = claims_by_id.get(relation['claim_id'])
            source_id = claim['source_id'] if claim else relation['source_id']
            if source_id not in source_by_id:
                continue
            path = [source_steps[source_id]]
            if claim:
                path.append(_step('CLAIM', claim['claim_id'], claim['statement'], claim['status']))
            path.extend([_step('RELATION', relation['relation_id'], relation['relation_type'], relation['relation_status']),
                         _step('NODE', relation['from_node_id'], relation['from_name']),
                         _step('NODE', relation['to_node_id'], relation['to_name'])])
            status = relation['relation_status'] or 'unknown'
            current = status == 'current' and relation['evidence_status'] == 'active'
            reason = 'RECORDED_CONTRADICTION' if relation['evidence_role'] == 'contradicts' else 'RECORDED_RELATION_EVIDENCE'
            category = 'CURRENT' if current else 'CATEGORICAL' if status == 'categorical' else 'HISTORICAL'
            items.append(self._item(source_id, impact_type='RELATION_EVIDENCE', target_type='RELATION',
                target_id=relation['relation_id'], path_steps=path,
                relationship_types=['RELATION_EVIDENCE_' + relation['evidence_role'].upper(), relation['relation_type'].upper()],
                reason_code=reason, official_or_staged=category,
                evidence_refs=[{'claim_id': relation['claim_id'] or '', 'source_id': source_id,
                                'evidence_id': relation['evidence_id'] or ''}],
                temporal_status={'effective_date': relation['valid_from'] if relation['valid_from_supplied'] else 'unknown',
                                 'valid_to': relation['valid_to'] if relation['valid_to_supplied'] else 'unknown',
                                 'temporal_relation': relation['temporal_category'] or 'unknown'},
                current_status=status, is_current_impact=current))

        with self.store.connect() as workbench:
            workbench.execute('BEGIN')
            require(schema_version(workbench) in ('5', '6'), 'IMPACT_SCHEMA_REQUIRED')
            query_count[0] += 1
            drafts = [dict(row) for row in workbench.execute('SELECT node_id,draft_id,revision,status,body,updated_at FROM view_drafts ORDER BY node_id')]
            query_count[0] += 1
            draft_events: dict[str, list[dict[str, Any]]] = {}
            for row in workbench.execute('SELECT node_id,event_json FROM view_draft_events ORDER BY node_id,revision'):
                draft_events.setdefault(row['node_id'], []).append(_json(row['event_json'], {}))
            relevant_drafts = []
            for draft in drafts:
                body = _json(draft['body'], {})
                events = draft_events.get(draft['node_id'], [])
                require(len(events) == draft['revision'] and bool(events) and events[-1].get('body') == body,
                        'RECOVERY_REQUIRED')
                draft['primary_claim_ids'] = [v for v in body.get('primary_claim_ids', []) if isinstance(v, str)]
                draft['context_claim_ids'] = [v for v in body.get('context_claim_ids', []) if isinstance(v, str)]
                if draft['node_id'] in linked_node_ids or set(draft['primary_claim_ids'] + draft['context_claim_ids']) & set(claim_ids):
                    relevant_drafts.append(draft)
            for draft in relevant_drafts:
                for claim_id in sorted(set(draft['primary_claim_ids'] + draft['context_claim_ids']) & set(claim_ids)):
                    claim = claims_by_id[claim_id]
                    source_id = claim['source_id']
                    role = 'subject' if claim_id in draft['primary_claim_ids'] else 'context'
                    items.append(self._item(source_id, impact_type='DRAFT_VIEW', target_type='VIEW_DRAFT', target_id=draft['draft_id'],
                        path_steps=[source_steps[source_id], _step('CLAIM', claim_id, claim['statement'], claim['status']),
                                    _step('VIEW_DRAFT', draft['draft_id'], f"revision {draft['revision']}", draft['status'])],
                        relationship_types=['SOURCE_HAS_CLAIM', 'EXPLICIT_DRAFT_EVIDENCE'],
                        attribution_role=role, reason_code='STAGED_VIEW_DEPENDENCY', official_or_staged='STAGED',
                        evidence_refs=[{'claim_id': claim_id, 'source_id': source_id}],
                        temporal_status={'effective_date': draft['updated_at'] or 'unknown', 'temporal_relation': 'staged_revision'},
                        current_status=draft['status']))

            knowledge_sha = canonical_sha256(knowledge_basis)
            staged_sha = canonical_sha256(relevant_drafts)
            snapshot_id = canonical_sha256({'knowledge': knowledge_sha, 'staged': staged_sha})
            source_snapshot_ids = {
                source_id: canonical_sha256({
                    'source': source_by_id[source_id],
                    'items': [item for item in items if item['origin_id'] == source_id],
                    'drafts': [draft for draft in relevant_drafts if set(
                        draft['primary_claim_ids'] + draft['context_claim_ids']) & {
                            claim['claim_id'] for claim in claims if claim['source_id'] == source_id}],
                })
                for source_id in source_ids
            }
            item_ids = [item['impact_id'] for item in items]
            query_count[0] += 1
            attention: dict[str, dict[str, Any]] = {}
            if item_ids:
                marks, args = self._where(item_ids)
                attention = {row['impact_id']: dict(row) for row in workbench.execute(
                    f'SELECT * FROM impact_attention_states WHERE impact_id IN ({marks})', args)}

        for item in items:
            state = attention.get(item['impact_id'])
            item_snapshot_id = source_snapshot_ids[item['origin_id']]
            item['attention_state'] = None if state is None else {
                'outcome': state['outcome'], 'revision': state['revision'], 'reviewer': state['reviewer'],
                'actor': state['actor'], 'reason': state['reason'], 'updated_at': state['updated_at'],
                'status': 'CURRENT' if state['snapshot_id'] == item_snapshot_id else 'STALE',
                'snapshot_id': state['snapshot_id'],
            }
            item['snapshot_id'] = item_snapshot_id
        items.sort(key=lambda item: (REASON_ORDER.get(item['reason_code'], 99),
                                     ROLE_ORDER.get(item['attribution_role'] or '', 99),
                                     item['target_type'], item['target_id'], item['impact_id']))
        changes = []
        by_source: dict[str, list[dict[str, Any]]] = {sid: [] for sid in source_ids}
        for item in items:
            by_source[item['origin_id']].append(item)
        for source in sources:
            source_claims = [row for row in claims if row['source_id'] == source['source_id']]
            changes.append({
                'source': source,
                'evidence_date': source['publication_time'] or 'unknown',
                'current_status': source['status'] or 'unknown',
                'claim_count': len(source_claims),
                'claims': [{key: row[key] for key in ('claim_id', 'statement', 'status', 'fact_time', 'publication_time')} for row in source_claims],
                'snapshot_id': source_snapshot_ids[source['source_id']],
                'items': by_source[source['source_id']],
            })
        return {'snapshot': {'snapshot_id': snapshot_id, 'knowledge_sha256': knowledge_sha,
                             'workbench_projection_sha256': staged_sha, 'cache': 'NONE',
                             'consistency': 'TRANSACTIONAL_READ_SNAPSHOT', 'query_count': query_count[0]},
                'changes': changes, 'items': items}

    @staticmethod
    def _finish(sources, _claims, _links, _views, query_count):
        empty = canonical_sha256({'knowledge': [], 'staged': []})
        return {'snapshot': {'snapshot_id': empty, 'knowledge_sha256': empty,
                             'workbench_projection_sha256': empty, 'cache': 'NONE',
                             'consistency': 'TRANSACTIONAL_READ_SNAPSHOT', 'query_count': query_count[0]},
                'changes': [], 'items': []}

    def changes(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ImpactError('INVALID_REQUEST', 422)
        count = [0]
        with closing(readonly(self.config.knowledge_db)) as connection:
            connection.execute('BEGIN')
            count[0] += 1
            sources = [dict(row) for row in connection.execute(
                '''SELECT source_id,title,publication_time,ingested_at,status,source_type,source_rank
                   FROM sources ORDER BY ingested_at DESC,source_id LIMIT ? OFFSET ?''', (limit, offset))]
            result = self._project(connection, sources, count)
        result['limit'] = limit
        result['offset'] = offset
        return result

    def source(self, source_id: str) -> dict[str, Any]:
        count = [0]
        with closing(readonly(self.config.knowledge_db)) as connection:
            connection.execute('BEGIN')
            count[0] += 1
            row = connection.execute('''SELECT source_id,title,publication_time,ingested_at,status,source_type,source_rank
                                        FROM sources WHERE source_id=?''', (source_id,)).fetchone()
            if row is None:
                raise ImpactError('TARGET_NOT_FOUND', 404)
            result = self._project(connection, [dict(row)], count)
        return result

    def item(self, impact_id: str) -> dict[str, Any]:
        source_id = _source_from_impact_id(impact_id)
        result = self.source(source_id)
        item = next((row for row in result['items'] if row['impact_id'] == impact_id), None)
        if item is None:
            raise ImpactError('IMPACT_PATH_NOT_FOUND', 404)
        return {'snapshot': result['snapshot'], 'item': item}

    def claim(self, claim_id: str) -> dict[str, Any]:
        count = [0]
        with closing(readonly(self.config.knowledge_db)) as connection:
            connection.execute('BEGIN')
            count[0] += 1
            row = connection.execute('''SELECT s.source_id,s.title,s.publication_time,s.ingested_at,
                                               s.status,s.source_type,s.source_rank
                                        FROM claims c JOIN sources s ON s.source_id=c.source_id
                                        WHERE c.claim_id=?''', (claim_id,)).fetchone()
            if row is None:
                raise ImpactError('TARGET_NOT_FOUND', 404)
            result = self._project(connection, [dict(row)], count)
        result['items'] = [item for item in result['items'] if any(
            step['object_type'] == 'CLAIM' and step['object_id'] == claim_id for step in item['path_steps'])]
        result['claim_id'] = claim_id
        return result

    def node(self, node_id: str) -> dict[str, Any]:
        count = [0]
        with closing(readonly(self.config.knowledge_db)) as connection:
            connection.execute('BEGIN')
            count[0] += 1
            node = connection.execute('SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE node_id=?', (node_id,)).fetchone()
            if node is None:
                raise ImpactError('TARGET_NOT_FOUND', 404)
            count[0] += 1
            sources = [dict(row) for row in connection.execute(f'''WITH ranked AS (
                    SELECT node_id,trigger_claim_ids_json,
                           ROW_NUMBER() OVER(PARTITION BY node_id ORDER BY {CURRENT_VIEW_ORDER}) rank
                    FROM current_views WHERE status='official'),
                cited AS (SELECT value AS claim_id FROM ranked,json_each(
                    CASE WHEN json_valid(trigger_claim_ids_json) THEN trigger_claim_ids_json ELSE '[]' END)
                    WHERE node_id=? AND rank=1)
                SELECT DISTINCT s.source_id,s.title,s.publication_time,s.ingested_at,s.status,s.source_type,s.source_rank
                FROM sources s JOIN claims c ON c.source_id=s.source_id
                WHERE EXISTS(SELECT 1 FROM claim_node_links l WHERE l.claim_id=c.claim_id AND l.node_id=?)
                   OR c.claim_id IN (SELECT claim_id FROM cited)
                ORDER BY s.source_id LIMIT 100''', (node_id, node_id))]
            projected = self._project(connection, sources, count)
        items = [item for item in projected['items'] if any(
            step['object_type'] == 'NODE' and step['object_id'] == node_id for step in item['path_steps'])]
        return {'node': dict(node), 'items': items,
                'snapshot': projected['snapshot'], 'cache': 'NONE'}

    def view(self, view_id: str) -> dict[str, Any]:
        count = [0]
        with closing(readonly(self.config.knowledge_db)) as connection:
            connection.execute('BEGIN')
            count[0] += 1
            row = connection.execute(f'''WITH ranked AS (
                    SELECT view_id,node_id,trigger_claim_ids_json,status,
                           ROW_NUMBER() OVER(PARTITION BY node_id ORDER BY {CURRENT_VIEW_ORDER}) rank
                    FROM current_views WHERE status='official')
                SELECT * FROM ranked WHERE view_id=? AND rank=1''', (view_id,)).fetchone()
            if row is None:
                raise ImpactError('NONCURRENT_RELATION', 409)
            claims = [v for v in _json(row['trigger_claim_ids_json'], []) if isinstance(v, str)]
            count[0] += 1
            if claims:
                marks, args = self._where(claims)
                sources = [dict(r) for r in connection.execute(
                    f'''SELECT DISTINCT s.source_id,s.title,s.publication_time,s.ingested_at,s.status,s.source_type,s.source_rank
                        FROM claims c JOIN sources s ON s.source_id=c.source_id
                        WHERE c.claim_id IN ({marks}) ORDER BY s.source_id LIMIT 100''', args)]
            else:
                sources = []
            projected = self._project(connection, sources, count)
        items = [item for item in projected['items'] if item['target_type'] == 'VIEW' and item['target_id'] == view_id]
        return {'view_id': view_id, 'items': items,
                'snapshot': projected['snapshot'], 'cache': 'NONE'}

    def set_attention(self, impact_id: str, request: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
        current = self.item(impact_id)
        if request.get('snapshot_id') != current['item']['snapshot_id']:
            raise ImpactError('STALE_SNAPSHOT', 409)
        if request.get('outcome') not in ATTENTION_OUTCOMES:
            raise ImpactError('INVALID_REQUEST', 422)
        fingerprint = canonical_sha256({'action': 'ATTENTION', 'request': request, 'actor': identity['actor']})
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            require(schema_version(connection) in ('5', '6'), 'IMPACT_SCHEMA_REQUIRED')
            prior = connection.execute('SELECT request_sha256,response_json FROM impact_attention_events WHERE impact_id=? AND operation_id=?',
                                       (impact_id, request['operation_id'])).fetchone()
            if prior:
                if prior['request_sha256'] != fingerprint:
                    raise ImpactError('IDEMPOTENCY_CONFLICT', 409)
                return json.loads(prior['response_json'])
            old = connection.execute('SELECT * FROM impact_attention_states WHERE impact_id=?', (impact_id,)).fetchone()
            revision = old['revision'] if old else 0
            if request['expected_revision'] != revision:
                raise ImpactError('REVISION_CONFLICT', 409, revision)
            if old and old['reviewer'] != request['reviewer']:
                raise ImpactError('REVIEWER_MISMATCH', 409)
            revision += 1
            updated = datetime.now(timezone.utc).isoformat()
            state = {'impact_id': impact_id, 'snapshot_id': request['snapshot_id'], 'outcome': request['outcome'],
                     'revision': revision, 'reviewer': request['reviewer'], 'actor': identity['actor'],
                     'reason': request['reason'], 'updated_at': updated, 'status': 'CURRENT'}
            response = {'attention_state': state, 'canonical_write': False, 'production_authorized': False}
            connection.execute('''INSERT INTO impact_attention_states VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(impact_id) DO UPDATE SET snapshot_id=excluded.snapshot_id,outcome=excluded.outcome,
                revision=excluded.revision,reason=excluded.reason,updated_at=excluded.updated_at''',
                (impact_id, request['snapshot_id'], request['outcome'], revision, request['reviewer'],
                 identity['actor'], request['reason'], updated))
            event = {'action': 'ATTENTION', 'old': dict(old) if old else None, 'new': state}
            connection.execute('INSERT INTO impact_attention_events VALUES(?,?,?,?,?,?)',
                (impact_id, revision, request['operation_id'], fingerprint,
                 json.dumps(event, sort_keys=True, separators=(',', ':')),
                 json.dumps(response, sort_keys=True, separators=(',', ':'))))
        return response
