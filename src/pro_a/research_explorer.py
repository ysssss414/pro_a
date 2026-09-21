"""Deterministic, bounded Stage 5 research projections over canonical knowledge."""
from __future__ import annotations

from contextlib import closing, contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata
from typing import Any, Iterator

from pro_a.direct_impact import DirectImpact
from pro_a.workbench.research_store import FollowupNotes, OBJECT_TYPES

CURRENT_VIEW_ORDER = 'revision_date DESC,revision_seq DESC,view_id DESC'
SEARCH_TYPES = ('NODE', 'CLAIM', 'SOURCE', 'RESEARCH_QUESTION', 'GAP')


class ResearchError(RuntimeError):
    def __init__(self, code: str, status: int = 422):
        super().__init__(code)
        self.status = status


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), default=str).encode()).hexdigest()


def _json(value: str | None, default: Any) -> Any:
    try:
        parsed = json.loads(value or '')
        return parsed
    except (TypeError, ValueError):
        return default


def _page(cursor: str | None, limit: int) -> tuple[int, int]:
    if not 1 <= limit <= 100:
        raise ResearchError('INVALID_CURSOR')
    if cursor in (None, ''):
        return 0, limit
    if not cursor.isascii() or not cursor.isdigit():
        raise ResearchError('INVALID_CURSOR')
    offset = int(cursor)
    if offset < 0 or offset > 10_000_000:
        raise ResearchError('INVALID_CURSOR')
    return offset, limit


def _page_result(items: list[dict], total: int, offset: int, limit: int,
                 sort_contract: str = 'business_date DESC, stable_id ASC') -> dict:
    return {
        'items': items, 'total': total, 'limit': limit, 'offset': offset,
        'cursor': str(offset) if offset else None,
        'next_cursor': str(offset + limit) if offset + limit < total else None,
        'previous_cursor': str(max(0, offset - limit)) if offset else None,
        'sort_contract': sort_contract,
    }


class ResearchExplorer:
    def __init__(self, config):
        self.config = config
        self.impacts = DirectImpact(config)
        self.notes = FollowupNotes(config)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        path = Path(self.config.knowledge_db).resolve(strict=True)
        connection = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function(
            'nfkc_casefold', 1,
            lambda value: unicodedata.normalize('NFKC', str(value or '')).casefold(),
            deterministic=True,
        )
        connection.execute('PRAGMA query_only=ON')
        try:
            connection.execute('BEGIN')
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _safe_source(row: sqlite3.Row | dict) -> dict:
        return {key: row[key] for key in (
            'source_id', 'title', 'source_type', 'source_rank', 'origin_type', 'author',
            'organization', 'publication_time', 'ingested_at', 'ingestion_mode',
            'analysis_mode', 'status', 'underlying_source_id') if key in row.keys()}

    @staticmethod
    def _view(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        value = dict(row)
        value['content_json'] = _json(value.get('content_json'), {})
        value['trigger_claim_ids'] = _json(value.pop('trigger_claim_ids_json', '[]'), [])
        return value

    @staticmethod
    def _with_snapshot(value: dict) -> dict:
        value['research_snapshot'] = {
            'snapshot_id': _canonical_sha(value),
            'consistency': 'CANONICAL_TRANSACTIONAL_READ_WITH_INDIVIDUALLY_VERSIONED_WORKBENCH_PROJECTIONS',
            'cache': 'NONE',
        }
        return value

    def home(self) -> dict:
        open_notes = self.notes.list(status='OPEN', limit=10)['notes']
        with self.connect() as conn:
            stats = {}
            for key, sql in {
                'nodes': "SELECT COUNT(*) FROM nodes WHERE status='active'",
                'claims': 'SELECT COUNT(*) FROM claims',
                'sources': 'SELECT COUNT(*) FROM sources',
                'official_views': "SELECT COUNT(*) FROM current_views WHERE status='official'",
                'open_questions': "SELECT COUNT(*) FROM research_questions WHERE status='open'",
                'open_gaps': "SELECT COUNT(*) FROM knowledge_gaps WHERE status IN ('open','reopened','needs_refresh')",
            }.items():
                stats[key] = int(conn.execute(sql).fetchone()[0])
            views = [self._view(row) for row in conn.execute(f'''SELECT view_id,node_id,version,status,change_level,
                    content_json,trigger_claim_ids_json,revision_date,revision_seq,confirmed_at
                    FROM current_views WHERE status='official' ORDER BY {CURRENT_VIEW_ORDER} LIMIT 10''')]
            recent_sources = [self._safe_source(row) for row in conn.execute('''SELECT source_id,title,source_type,source_rank,
                    origin_type,author,organization,publication_time,ingested_at,ingestion_mode,analysis_mode,status,underlying_source_id
                    FROM sources ORDER BY ingested_at DESC,source_id LIMIT 10''')]
            gaps = [dict(row) for row in conn.execute('''SELECT g.gap_id,g.node_id,n.canonical_name,g.title,g.status,g.freshness_due
                    FROM knowledge_gaps g JOIN nodes n ON n.node_id=g.node_id
                    WHERE g.status IN ('open','reopened','needs_refresh')
                    ORDER BY CASE WHEN g.freshness_due='' THEN 1 ELSE 0 END,g.freshness_due,g.gap_id LIMIT 10''')]
            questions = [dict(row) for row in conn.execute('''SELECT q.rq_id,q.node_id,n.canonical_name,q.question,q.status,q.confidence
                    FROM research_questions q JOIN nodes n ON n.node_id=q.node_id
                    WHERE q.status='open' ORDER BY q.updated_at DESC,q.rq_id LIMIT 10''')]
            direct_routes = {'NODE': 'node', 'CLAIM': 'claim', 'SOURCE': 'source', 'RELATION': 'relation'}
            for note in open_notes:
                note['route_kind'] = direct_routes.get(note['object_type'], 'home')
                note['route_id'] = note['object_id']
            for object_type, table, id_column in (
                ('GAP', 'knowledge_gaps', 'gap_id'),
                ('RESEARCH_QUESTION', 'research_questions', 'rq_id'),
            ):
                relevant = [note for note in open_notes if note['object_type'] == object_type]
                if not relevant:
                    continue
                marks = ','.join('?' for _ in relevant)
                node_ids = {row[id_column]: row['node_id'] for row in conn.execute(
                    f'SELECT {id_column},node_id FROM {table} WHERE {id_column} IN ({marks})',
                    [note['object_id'] for note in relevant])}
                for note in relevant:
                    if note['object_id'] in node_ids:
                        note['route_kind'] = 'node'
                        note['route_id'] = node_ids[note['object_id']]
            value = {'stats': stats, 'recent_official_views': views,
                     'recent_sources': recent_sources, 'open_gaps': gaps,
                     'open_questions': questions, 'open_notes': open_notes}
        value['impact'] = self.impacts.changes(limit=10, offset=0)
        return self._with_snapshot(value)

    def search(self, q: str, *, object_type: str = '', limit: int = 30) -> dict:
        q = q.strip()
        if not q or not 1 <= limit <= 50:
            raise ResearchError('INVALID_FILTER')
        if object_type and object_type not in SEARCH_TYPES:
            raise ResearchError('UNSUPPORTED_RESEARCH_OBJECT')
        needle = unicodedata.normalize('NFKC', q).casefold()
        results: list[dict] = []
        with self.connect() as conn:
            if object_type in ('', 'NODE'):
                rows = conn.execute('''SELECT n.node_id,n.canonical_name,n.primary_type,n.status,
                        GROUP_CONCAT(a.alias,' | ') AS matched_aliases,
                        MIN(CASE WHEN nfkc_casefold(n.canonical_name)=? THEN 0
                                 WHEN nfkc_casefold(a.alias)=? THEN 1
                                 WHEN instr(nfkc_casefold(n.canonical_name),?)>0 THEN 2 ELSE 3 END) AS match_rank
                        FROM nodes n LEFT JOIN node_aliases a ON a.node_id=n.node_id
                        WHERE instr(nfkc_casefold(n.canonical_name),?)>0
                           OR instr(nfkc_casefold(COALESCE(a.alias,'')),?)>0
                        GROUP BY n.node_id,n.canonical_name,n.primary_type,n.status
                        ORDER BY match_rank,nfkc_casefold(n.canonical_name),n.canonical_name,n.node_id
                        LIMIT ?''',
                    (needle, needle, needle, needle, needle, limit)).fetchall()
                results.extend({'object_type': 'NODE', 'object_id': r['node_id'],
                                'label': r['canonical_name'], 'subtitle': r['primary_type'],
                                'node_type': r['primary_type'], 'status': r['status'],
                                'matched_aliases': (r['matched_aliases'] or '').split(' | ') if r['matched_aliases'] else [],
                                '_rank': r['match_rank']} for r in rows)
            specs = (
                ('CLAIM', 'claims', 'claim_id', 'statement', 'nature', 'status'),
                ('SOURCE', 'sources', 'source_id', 'title', 'source_type', 'status'),
                ('RESEARCH_QUESTION', 'research_questions', 'rq_id', 'question', 'importance', 'status'),
                ('GAP', 'knowledge_gaps', 'gap_id', 'title', 'description', 'status'),
            )
            for kind, table, id_col, label_col, subtitle_col, status_col in specs:
                if object_type not in ('', kind):
                    continue
                node_column = 'node_id' if kind in ('RESEARCH_QUESTION', 'GAP') else "'' node_id"
                for row in conn.execute(f'''SELECT {id_col} object_id,{label_col} label,
                        {subtitle_col} subtitle,{status_col} status,
                        {node_column},
                        CASE WHEN nfkc_casefold({label_col})=? THEN 0 ELSE 3 END match_rank
                        FROM {table} WHERE instr(nfkc_casefold({label_col}),?)>0
                        ORDER BY match_rank,{id_col} LIMIT ?''', (needle, needle, limit)):
                    results.append({'object_type': kind, 'object_id': row['object_id'],
                                    'label': row['label'], 'subtitle': row['subtitle'],
                                    'status': row['status'], 'node_id': row['node_id'], '_rank': row['match_rank']})
        type_rank = {'NODE': 0, 'SOURCE': 1, 'CLAIM': 2, 'RESEARCH_QUESTION': 3, 'GAP': 4}
        results.sort(key=lambda item: (item.pop('_rank'), type_rank[item['object_type']],
                                       item['label'].casefold(), item['object_id']))
        results = results[:limit]
        return self._with_snapshot({'query': q, 'object_type': object_type or 'ALL',
                                    'match_mode': 'DETERMINISTIC_CASE_INSENSITIVE_SUBSTRING',
                                    'limit': limit, 'results': results})

    @staticmethod
    def _claim_filters(filters: dict) -> tuple[list[str], list[Any]]:
        clauses, args = [], []
        scalar = {'source_id': 'c.source_id', 'node_id': 'cnl.node_id', 'role': 'cnl.role',
                  'nature': 'c.nature', 'status': 'c.status'}
        for key, column in scalar.items():
            value = filters.get(key)
            if value:
                clauses.append(f'{column}=?'); args.append(value)
        if filters.get('q'):
            clauses.append('lower(c.statement) LIKE ?'); args.append('%' + filters['q'].casefold() + '%')
        date_expr = "COALESCE(NULLIF(c.fact_time,''),NULLIF(c.publication_time,''),NULLIF(c.ingestion_time,''),c.created_at)"
        if filters.get('date_from'):
            clauses.append(date_expr + '>=?'); args.append(filters['date_from'])
        if filters.get('date_to'):
            clauses.append(date_expr + '<=?'); args.append(filters['date_to'])
        if filters.get('linked') is not None:
            clauses.append(('' if filters['linked'] else 'NOT ') +
                           'EXISTS(SELECT 1 FROM claim_node_links x WHERE x.claim_id=c.claim_id)')
        if filters.get('cited') is not None:
            clauses.append(('' if filters['cited'] else 'NOT ') + '''EXISTS(
                SELECT 1 FROM current_views v,json_each(CASE WHEN json_valid(v.trigger_claim_ids_json)
                    THEN v.trigger_claim_ids_json ELSE '[]' END) j
                WHERE v.status='official' AND j.value=c.claim_id)''')
        return clauses, args

    def _claim_page(self, conn: sqlite3.Connection, filters: dict, cursor: str | None, limit: int) -> dict:
        offset, limit = _page(cursor, limit)
        clauses, args = self._claim_filters(filters)
        join = ' LEFT JOIN claim_node_links cnl ON cnl.claim_id=c.claim_id '
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        total = int(conn.execute(f'SELECT COUNT(DISTINCT c.claim_id) FROM claims c{join}{where}', args).fetchone()[0])
        rows = [dict(row) for row in conn.execute(f'''SELECT DISTINCT c.claim_id,c.statement,c.nature,c.fact_time,
                c.publication_time,c.ingestion_time,c.status,c.confidence,c.scope,c.attributed_to,
                c.evidence_pointer,c.evidence_excerpt,c.source_id,s.title AS source_title,
                COALESCE(NULLIF(c.fact_time,''),NULLIF(c.publication_time,''),NULLIF(c.ingestion_time,''),c.created_at) business_date
                FROM claims c JOIN sources s ON s.source_id=c.source_id{join}{where}
                ORDER BY business_date DESC,c.claim_id LIMIT ? OFFSET ?''', (*args, limit, offset))]
        ids = [row['claim_id'] for row in rows]
        nodes: dict[str, list[dict]] = {item: [] for item in ids}
        citations: dict[str, list[dict]] = {item: [] for item in ids}
        if ids:
            marks = ','.join('?' for _ in ids)
            for row in conn.execute(f'''SELECT l.claim_id,l.role,n.node_id,n.canonical_name,n.primary_type
                    FROM claim_node_links l JOIN nodes n ON n.node_id=l.node_id
                    WHERE l.claim_id IN ({marks}) ORDER BY l.claim_id,
                    CASE l.role WHEN 'subject' THEN 0 WHEN 'context' THEN 1 ELSE 2 END,
                    n.canonical_name COLLATE NOCASE,n.node_id''', ids):
                nodes[row['claim_id']].append(dict(row))
            for row in conn.execute(f'''WITH ranked AS (
                    SELECT view_id,node_id,version,revision_date,trigger_claim_ids_json,
                    ROW_NUMBER() OVER(PARTITION BY node_id ORDER BY {CURRENT_VIEW_ORDER}) view_rank
                    FROM current_views WHERE status='official')
                    SELECT j.value claim_id,v.view_id,v.node_id,v.version,v.revision_date,v.view_rank
                    FROM ranked v,json_each(CASE WHEN json_valid(v.trigger_claim_ids_json)
                        THEN v.trigger_claim_ids_json ELSE '[]' END) j
                    WHERE j.value IN ({marks}) ORDER BY j.value,v.view_rank,v.node_id,v.view_id''', ids):
                citations[row['claim_id']].append(dict(row))
        for row in rows:
            row['linked_nodes'] = nodes[row['claim_id']]
            row['official_view_citations'] = citations[row['claim_id']]
        return _page_result(rows, total, offset, limit)

    def claims(self, *, cursor: str | None = None, limit: int = 25, **filters) -> dict:
        with self.connect() as conn:
            value = {'filters': filters, **self._claim_page(conn, filters, cursor, limit)}
        return self._with_snapshot(value)

    def claim(self, claim_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute('''SELECT c.claim_id,c.statement,c.nature,c.fact_time,c.publication_time,c.ingestion_time,
                    c.status,c.confidence,c.scope,c.attributed_to,c.evidence_pointer,c.evidence_excerpt,c.structured_json,
                    s.source_id,s.title,s.source_type,s.source_rank,s.origin_type,s.author,s.organization,
                    s.publication_time source_publication_time,s.ingested_at,s.ingestion_mode,s.analysis_mode,
                    s.status source_status,s.underlying_source_id
                    FROM claims c JOIN sources s ON s.source_id=c.source_id WHERE c.claim_id=?''', (claim_id,)).fetchone()
            if row is None:
                raise ResearchError('CLAIM_NOT_FOUND', 404)
            claim = {key: row[key] for key in ('claim_id','statement','nature','fact_time','publication_time',
                'ingestion_time','status','confidence','scope','attributed_to','evidence_pointer','evidence_excerpt')}
            claim['source_locator'] = _json(row['structured_json'], {}).get('validation', {}).get('source_locator')
            source = {'source_id': row['source_id'], 'title': row['title'], 'source_type': row['source_type'],
                'source_rank': row['source_rank'], 'origin_type': row['origin_type'], 'author': row['author'],
                'organization': row['organization'], 'publication_time': row['source_publication_time'],
                'ingested_at': row['ingested_at'], 'ingestion_mode': row['ingestion_mode'],
                'analysis_mode': row['analysis_mode'], 'status': row['source_status'],
                'underlying_source_id': row['underlying_source_id']}
            linked_nodes = [dict(r) for r in conn.execute('''SELECT l.role,n.node_id,n.canonical_name,n.primary_type,n.status
                    FROM claim_node_links l JOIN nodes n ON n.node_id=l.node_id WHERE l.claim_id=?
                    ORDER BY l.role,n.canonical_name COLLATE NOCASE,n.node_id''', (claim_id,))]
            citations = [dict(r) for r in conn.execute(f'''WITH ranked AS (
                    SELECT view_id,node_id,version,status,revision_date,trigger_claim_ids_json,
                    ROW_NUMBER() OVER(PARTITION BY node_id ORDER BY {CURRENT_VIEW_ORDER}) view_rank
                    FROM current_views WHERE status='official')
                    SELECT v.view_id,v.node_id,n.canonical_name,v.version,v.status,v.revision_date,v.view_rank
                    FROM ranked v JOIN nodes n ON n.node_id=v.node_id,
                    json_each(CASE WHEN json_valid(v.trigger_claim_ids_json) THEN v.trigger_claim_ids_json ELSE '[]' END) j
                    WHERE j.value=? ORDER BY v.view_rank,v.node_id,v.view_id''', (claim_id,))]
            claim_relations = [dict(r) for r in conn.execute('''SELECT r.relation_id,r.relation_type,r.reason,r.created_at,
                    r.from_claim_id,r.to_claim_id,fc.statement from_statement,tc.statement to_statement
                    FROM claim_relations r JOIN claims fc ON fc.claim_id=r.from_claim_id
                    JOIN claims tc ON tc.claim_id=r.to_claim_id
                    WHERE r.from_claim_id=? OR r.to_claim_id=? ORDER BY r.created_at,r.relation_id''', (claim_id, claim_id))]
            relation_evidence = [dict(r) for r in conn.execute('''SELECT l.relation_id,l.evidence_role,l.status,r.relation_type,r.from_node_id,r.to_node_id
                    FROM relation_evidence_links l JOIN node_relations r ON r.relation_id=l.relation_id
                    WHERE l.claim_id=? ORDER BY l.relation_id,l.evidence_role''', (claim_id,))]
            value = {'claim': claim, 'source': source, 'linked_nodes': linked_nodes,
                     'official_view_citations': citations, 'claim_relations': claim_relations,
                     'relation_evidence': relation_evidence}
        value['impact'] = self.impacts.claim(claim_id)
        value['notes'] = self.notes.list(object_type='CLAIM', object_id=claim_id)['notes']
        return self._with_snapshot(value)

    @staticmethod
    def _source_filters(filters: dict) -> tuple[list[str], list[Any]]:
        clauses, args = [], []
        for key, column in {'source_type': 's.source_type', 'status': 's.status'}.items():
            if filters.get(key): clauses.append(f'{column}=?'); args.append(filters[key])
        if filters.get('q'):
            clauses.append("lower(s.title || ' ' || COALESCE(s.organization,'') || ' ' || COALESCE(s.author,'')) LIKE ?")
            args.append('%' + filters['q'].casefold() + '%')
        date_expr = "COALESCE(NULLIF(s.publication_time,''),s.ingested_at)"
        if filters.get('date_from'): clauses.append(date_expr + '>=?'); args.append(filters['date_from'])
        if filters.get('date_to'): clauses.append(date_expr + '<=?'); args.append(filters['date_to'])
        if filters.get('has_claims') is not None:
            clauses.append(('' if filters['has_claims'] else 'NOT ') +
                           'EXISTS(SELECT 1 FROM claims c WHERE c.source_id=s.source_id)')
        if filters.get('has_attribution') is not None:
            clauses.append(('' if filters['has_attribution'] else 'NOT ') + '''EXISTS(
                SELECT 1 FROM claims c JOIN claim_node_links l ON l.claim_id=c.claim_id WHERE c.source_id=s.source_id
                UNION SELECT 1 FROM source_node_links sl WHERE sl.source_id=s.source_id)''')
        return clauses, args

    def _source_page(self, conn: sqlite3.Connection, filters: dict, cursor: str | None, limit: int) -> dict:
        offset, limit = _page(cursor, limit)
        clauses, args = self._source_filters(filters)
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        total = int(conn.execute(f'SELECT COUNT(*) FROM sources s{where}', args).fetchone()[0])
        rows = []
        for row in conn.execute(f'''SELECT s.source_id,s.title,s.source_type,s.source_rank,s.origin_type,s.author,
                s.organization,s.publication_time,s.ingested_at,s.ingestion_mode,s.analysis_mode,s.status,
                s.underlying_source_id,COUNT(DISTINCT c.claim_id) claim_count,
                COUNT(DISTINCT l.node_id) attributed_node_count,
                COALESCE(NULLIF(s.publication_time,''),s.ingested_at) business_date
                FROM sources s LEFT JOIN claims c ON c.source_id=s.source_id
                LEFT JOIN claim_node_links l ON l.claim_id=c.claim_id{where}
                GROUP BY s.source_id ORDER BY business_date DESC,s.source_id LIMIT ? OFFSET ?''', (*args, limit, offset)):
            rows.append(dict(row))
        return _page_result(rows, total, offset, limit)

    def sources(self, *, cursor: str | None = None, limit: int = 25, **filters) -> dict:
        with self.connect() as conn:
            value = {'filters': filters, **self._source_page(conn, filters, cursor, limit)}
        return self._with_snapshot(value)

    def source(self, source_id: str, *, claim_cursor: str | None = None, claim_limit: int = 25,
               claim_q: str = '', claim_status: str = '', claim_nature: str = '') -> dict:
        with self.connect() as conn:
            row = conn.execute('''SELECT source_id,title,source_type,source_rank,origin_type,author,organization,
                    publication_time,ingested_at,ingestion_mode,analysis_mode,status,underlying_source_id
                    FROM sources WHERE source_id=?''', (source_id,)).fetchone()
            if row is None:
                raise ResearchError('SOURCE_NOT_FOUND', 404)
            source = self._safe_source(row)
            filters = {'source_id': source_id, 'q': claim_q, 'status': claim_status, 'nature': claim_nature}
            claims = self._claim_page(conn, filters, claim_cursor, claim_limit)
            nodes = [dict(r) for r in conn.execute('''SELECT DISTINCT n.node_id,n.canonical_name,n.primary_type,
                    CASE WHEN sl.node_id IS NOT NULL THEN 'source' ELSE 'claim' END attribution_path
                    FROM nodes n LEFT JOIN source_node_links sl ON sl.node_id=n.node_id AND sl.source_id=?
                    LEFT JOIN claim_node_links l ON l.node_id=n.node_id
                    LEFT JOIN claims c ON c.claim_id=l.claim_id AND c.source_id=?
                    WHERE sl.node_id IS NOT NULL OR c.claim_id IS NOT NULL
                    ORDER BY n.canonical_name COLLATE NOCASE,n.node_id''', (source_id, source_id))]
            views = [dict(r) for r in conn.execute('''SELECT DISTINCT v.view_id,v.node_id,n.canonical_name,v.version,v.status,v.revision_date
                    FROM current_views v JOIN nodes n ON n.node_id=v.node_id,
                    json_each(CASE WHEN json_valid(v.trigger_claim_ids_json) THEN v.trigger_claim_ids_json ELSE '[]' END) j
                    JOIN claims c ON c.claim_id=j.value
                    WHERE v.status='official' AND c.source_id=?
                    ORDER BY v.revision_date DESC,v.view_id''', (source_id,))]
            value = {'source': source, 'claims': claims, 'explicit_nodes': nodes,
                     'official_view_citations': views}
        value['impact'] = self.impacts.source(source_id)
        value['notes'] = self.notes.list(object_type='SOURCE', object_id=source_id)['notes']
        return self._with_snapshot(value)

    def node(self, node_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute('SELECT node_id,canonical_name,primary_type,description,status,created_at,updated_at FROM nodes WHERE node_id=?', (node_id,)).fetchone()
            if row is None:
                raise ResearchError('NODE_NOT_FOUND', 404)
            node = dict(row)
            node['aliases'] = [r[0] for r in conn.execute('SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias COLLATE NOCASE,alias', (node_id,))]
            view = self._view(conn.execute(f'''SELECT view_id,node_id,version,status,change_level,previous_view_id,
                    content_md,content_json,trigger_source_id,trigger_claim_ids_json,revision_date,revision_seq,
                    accepted_proposal_id,created_at,confirmed_at FROM current_views
                    WHERE node_id=? AND status='official' ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1''', (node_id,)).fetchone())
            claims = self._claim_page(conn, {'node_id': node_id}, None, 20)
            source_ids = [r[0] for r in conn.execute('''SELECT DISTINCT s.source_id FROM sources s
                    LEFT JOIN source_node_links sl ON sl.source_id=s.source_id AND sl.node_id=?
                    LEFT JOIN claims c ON c.source_id=s.source_id
                    LEFT JOIN claim_node_links l ON l.claim_id=c.claim_id AND l.node_id=?
                    WHERE sl.node_id IS NOT NULL OR l.node_id IS NOT NULL
                    ORDER BY s.source_id LIMIT 20''', (node_id, node_id))]
            sources = []
            if source_ids:
                marks = ','.join('?' for _ in source_ids)
                sources = [dict(r) for r in conn.execute(f'''SELECT source_id,title,source_type,source_rank,publication_time,
                        ingested_at,status FROM sources WHERE source_id IN ({marks})
                        ORDER BY COALESCE(NULLIF(publication_time,''),ingested_at) DESC,source_id''', source_ids)]
            relations = [dict(r) for r in conn.execute('''SELECT r.relation_id,r.from_node_id,fn.canonical_name from_name,
                    r.relation_type,r.to_node_id,tn.canonical_name to_name,r.scope,r.valid_from,r.valid_to,
                    r.confidence,r.status,r.created_at,COUNT(e.relation_id) evidence_count
                    FROM node_relations r JOIN nodes fn ON fn.node_id=r.from_node_id JOIN nodes tn ON tn.node_id=r.to_node_id
                    LEFT JOIN relation_evidence_links e ON e.relation_id=r.relation_id
                    WHERE r.from_node_id=? OR r.to_node_id=? GROUP BY r.relation_id
                    ORDER BY CASE r.status WHEN 'current' THEN 0 WHEN 'categorical' THEN 1 ELSE 2 END,
                             r.relation_type,r.relation_id''', (node_id, node_id))]
            question_row = conn.execute('SELECT * FROM research_questions WHERE node_id=?', (node_id,)).fetchone()
            question = dict(question_row) if question_row else None
            if question:
                for field in ('supporting_claim_ids_json','opposing_claim_ids_json','key_variables_json'):
                    question[field.removesuffix('_json')] = _json(question.pop(field), [])
            gaps = []
            for gap in conn.execute('''SELECT * FROM knowledge_gaps WHERE node_id=? ORDER BY
                    CASE WHEN status IN ('open','reopened','needs_refresh') THEN 0 ELSE 1 END,
                    CASE WHEN freshness_due='' THEN 1 ELSE 0 END,freshness_due,gap_id''', (node_id,)):
                item = dict(gap); item['source_claim_ids'] = _json(item.pop('source_claim_ids_json'), []); gaps.append(item)
            counts = {'sources': len(source_ids), 'claims': claims['total'],
                      'official_views': int(view is not None), 'questions': int(question is not None), 'gaps': len(gaps)}
            level = ('LEVEL_4_RESEARCH_ACTIVE' if question or gaps else 'LEVEL_3_CANONICAL_VIEW' if view
                     else 'LEVEL_2_EVIDENCE_CONNECTED' if counts['claims'] else 'LEVEL_1_SOURCE_CONNECTED' if counts['sources']
                     else 'LEVEL_0_STRUCTURE_ONLY')
            value = {'node': node, 'current_view': view, 'claims': claims, 'sources': sources,
                     'relations': relations, 'research_question': question, 'knowledge_gaps': gaps,
                     'coverage': {'knowledge_level': level, **counts,
                                  'coverage_is_attribution': False, 'canonical_write': False}}
        value['impact'] = self.impacts.node(node_id)
        value['notes'] = self.notes.list(object_type='NODE', object_id=node_id)['notes']
        return self._with_snapshot(value)

    def relations(self, *, cursor: str | None = None, limit: int = 25,
                  node_id: str = '', status: str = '', relation_type: str = '') -> dict:
        offset, limit = _page(cursor, limit)
        clauses, args = [], []
        if node_id: clauses.append('(r.from_node_id=? OR r.to_node_id=?)'); args.extend((node_id, node_id))
        if status: clauses.append('r.status=?'); args.append(status)
        if relation_type: clauses.append('r.relation_type=?'); args.append(relation_type)
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        with self.connect() as conn:
            total = int(conn.execute(f'SELECT COUNT(*) FROM node_relations r{where}', args).fetchone()[0])
            rows = [dict(r) for r in conn.execute(f'''SELECT r.relation_id,r.from_node_id,fn.canonical_name from_name,
                    r.relation_type,r.to_node_id,tn.canonical_name to_name,r.scope,r.valid_from,r.valid_to,
                    r.confidence,r.status,r.created_at,COUNT(e.relation_id) evidence_count
                    FROM node_relations r JOIN nodes fn ON fn.node_id=r.from_node_id JOIN nodes tn ON tn.node_id=r.to_node_id
                    LEFT JOIN relation_evidence_links e ON e.relation_id=r.relation_id{where}
                    GROUP BY r.relation_id ORDER BY CASE r.status WHEN 'current' THEN 0 WHEN 'categorical' THEN 1 ELSE 2 END,
                    r.relation_type,r.relation_id LIMIT ? OFFSET ?''', (*args, limit, offset))]
            value = {'filters': {'node_id': node_id, 'status': status, 'relation_type': relation_type},
                     **_page_result(rows, total, offset, limit,
                                    'status(current,categorical,historical), relation_type ASC, relation_id ASC')}
        return self._with_snapshot(value)

    def relation(self, relation_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute('''SELECT r.*,fn.canonical_name from_name,fn.primary_type from_type,
                    tn.canonical_name to_name,tn.primary_type to_type,t.temporal_category,
                    t.valid_from_supplied,t.valid_to_supplied,t.provenance_json
                    FROM node_relations r JOIN nodes fn ON fn.node_id=r.from_node_id
                    JOIN nodes tn ON tn.node_id=r.to_node_id
                    LEFT JOIN relation_temporal_semantics t ON t.relation_id=r.relation_id
                    WHERE r.relation_id=?''', (relation_id,)).fetchone()
            if row is None:
                raise ResearchError('RELATION_NOT_FOUND', 404)
            relation = dict(row); relation['temporal_provenance'] = _json(relation.pop('provenance_json'), {})
            evidence = [dict(r) for r in conn.execute('''SELECT e.relation_id,e.claim_id,e.evidence_role,e.status,e.provenance_mode,e.evidence_id,
                    e.source_id native_source_id,c.statement,c.evidence_pointer,c.evidence_excerpt,
                    COALESCE(e.source_id,c.source_id) source_id,s.title source_title
                    FROM relation_evidence_links e LEFT JOIN claims c ON c.claim_id=e.claim_id
                    LEFT JOIN sources s ON s.source_id=COALESCE(e.source_id,c.source_id)
                    WHERE e.relation_id=? ORDER BY e.evidence_role,e.claim_id,e.evidence_id''', (relation_id,))]
            history = [dict(r) for r in conn.execute('''SELECT relation_id,from_node_id,relation_type,to_node_id,scope,
                    valid_from,valid_to,confidence,status,created_at FROM node_relations
                    WHERE relation_type=? AND ((from_node_id=? AND to_node_id=?) OR (from_node_id=? AND to_node_id=?))
                    ORDER BY created_at,relation_id''', (relation['relation_type'], relation['from_node_id'],
                                                        relation['to_node_id'], relation['to_node_id'],
                                                        relation['from_node_id']))]
            value = {'relation': relation, 'evidence': evidence, 'history': history,
                     'status_semantics': {'current': relation['status'] == 'current',
                                          'categorical': relation['status'] == 'categorical',
                                          'historical': relation['status'] not in ('current','categorical')}}
        value['notes'] = self.notes.list(object_type='RELATION', object_id=relation_id)['notes']
        return self._with_snapshot(value)

    def coverage(self, *, cursor: str | None = None, limit: int = 25) -> dict:
        offset, limit = _page(cursor, limit)
        with self.connect() as conn:
            active_nodes = int(conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE status='active'"
            ).fetchone()[0])
            total_nodes = int(conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
            node_rows = [dict(row) for row in conn.execute('''
                SELECT n.node_id,n.canonical_name,n.primary_type,
                  (SELECT COUNT(*) FROM node_aliases a WHERE a.node_id=n.node_id) alias_count,
                  (SELECT COUNT(*) FROM node_relations r WHERE r.status='current'
                    AND r.relation_type='part_of' AND r.from_node_id=n.node_id) parent_count,
                  (SELECT COUNT(*) FROM node_relations r WHERE r.status='current'
                    AND r.relation_type='part_of' AND r.to_node_id=n.node_id) child_count,
                  (SELECT COUNT(DISTINCT l.source_id) FROM source_node_links l
                    WHERE l.node_id=n.node_id) source_count,
                  (SELECT COUNT(DISTINCT l.claim_id) FROM claim_node_links l
                    WHERE l.node_id=n.node_id) claim_count,
                  (SELECT COUNT(*) FROM current_views v WHERE v.node_id=n.node_id
                    AND v.status='official') current_view_count,
                  (SELECT COUNT(*) FROM research_questions q WHERE q.node_id=n.node_id)
                    research_question_count,
                  (SELECT COUNT(*) FROM knowledge_gaps g WHERE g.node_id=n.node_id)
                    knowledge_gap_count,
                  (SELECT COUNT(*) FROM node_relations r WHERE r.status='current'
                    AND r.relation_type<>'part_of'
                    AND (r.from_node_id=n.node_id OR r.to_node_id=n.node_id)) functional_relation_count
                FROM nodes n WHERE n.status='active'
                ORDER BY n.primary_type COLLATE NOCASE,n.primary_type,
                         n.canonical_name COLLATE NOCASE,n.canonical_name,n.node_id
                LIMIT ? OFFSET ?''', (limit, offset))]
            for row in node_rows:
                if row['research_question_count'] or row['knowledge_gap_count']:
                    row['knowledge_level'] = 'LEVEL_4_RESEARCH_ACTIVE'
                elif row['current_view_count']:
                    row['knowledge_level'] = 'LEVEL_3_CANONICAL_VIEW'
                elif row['claim_count']:
                    row['knowledge_level'] = 'LEVEL_2_EVIDENCE_CONNECTED'
                elif row['source_count']:
                    row['knowledge_level'] = 'LEVEL_1_SOURCE_CONNECTED'
                else:
                    row['knowledge_level'] = 'LEVEL_0_STRUCTURE_ONLY'
            unlinked_total = int(conn.execute('''SELECT COUNT(*) FROM claims c
                WHERE NOT EXISTS(SELECT 1 FROM claim_node_links l WHERE l.claim_id=c.claim_id)''').fetchone()[0])
            unlinked = [dict(row) for row in conn.execute('''SELECT c.claim_id,c.source_id,
                    s.title source_title,s.source_type,s.source_rank,c.statement,c.evidence_excerpt,
                    c.nature,c.status,c.confidence,c.evidence_pointer,0 claim_node_link_count
                FROM claims c JOIN sources s ON s.source_id=c.source_id
                WHERE NOT EXISTS(SELECT 1 FROM claim_node_links l WHERE l.claim_id=c.claim_id)
                ORDER BY c.claim_id LIMIT ? OFFSET ?''', (limit, offset))]
            summary_row = conn.execute('''SELECT
                (SELECT COUNT(*) FROM node_aliases) alias_count,
                (SELECT COUNT(*) FROM sources) sources,
                (SELECT COUNT(*) FROM claims) claims,
                (SELECT COUNT(*) FROM claim_node_links) claim_node_links,
                (SELECT COUNT(*) FROM current_views WHERE status='official') current_views,
                (SELECT COUNT(*) FROM research_questions) research_questions,
                (SELECT COUNT(*) FROM knowledge_gaps) knowledge_gaps,
                (SELECT COUNT(*) FROM knowledge_gaps WHERE status='open') open_knowledge_gaps,
                (SELECT COUNT(*) FROM node_relations WHERE status='current') current_relations,
                (SELECT COUNT(*) FROM node_relations WHERE status='current' AND relation_type='part_of') current_part_of
            ''').fetchone()
            node_coverage = {
                'with_sources': int(conn.execute('''SELECT COUNT(*) FROM nodes n WHERE n.status='active'
                    AND EXISTS(SELECT 1 FROM source_node_links l WHERE l.node_id=n.node_id)''').fetchone()[0]),
                'with_claims': int(conn.execute('''SELECT COUNT(*) FROM nodes n WHERE n.status='active'
                    AND EXISTS(SELECT 1 FROM claim_node_links l WHERE l.node_id=n.node_id)''').fetchone()[0]),
                'with_current_view': int(conn.execute('''SELECT COUNT(*) FROM nodes n WHERE n.status='active'
                    AND EXISTS(SELECT 1 FROM current_views v WHERE v.node_id=n.node_id AND v.status='official')''').fetchone()[0]),
                'with_rq': int(conn.execute('''SELECT COUNT(*) FROM nodes n WHERE n.status='active'
                    AND EXISTS(SELECT 1 FROM research_questions q WHERE q.node_id=n.node_id)''').fetchone()[0]),
                'with_gaps': int(conn.execute('''SELECT COUNT(*) FROM nodes n WHERE n.status='active'
                    AND EXISTS(SELECT 1 FROM knowledge_gaps g WHERE g.node_id=n.node_id)''').fetchone()[0]),
            }
            gaps = [dict(row) for row in conn.execute('''SELECT g.gap_id,g.node_id,n.canonical_name,g.title,
                    g.description,g.status,g.freshness_due,g.resolution_claim_id
                    FROM knowledge_gaps g JOIN nodes n ON n.node_id=g.node_id
                    ORDER BY CASE WHEN g.status IN ('open','reopened','needs_refresh') THEN 0 ELSE 1 END,
                             CASE WHEN g.freshness_due='' THEN 1 ELSE 0 END,g.freshness_due,g.gap_id LIMIT 25''')]
        gap_notes: dict[str, list[dict]] = {}
        for note in self.notes.list(object_type='GAP', limit=100)['notes']:
            gap_notes.setdefault(note['object_id'], []).append(note)
        for gap in gaps:
            gap['notes'] = gap_notes.get(gap['gap_id'], [])
        summary = {
            'total_nodes': total_nodes, 'active_nodes': active_nodes,
            'inactive_nodes': total_nodes - active_nodes,
            **dict(summary_row), 'unlinked_claims': unlinked_total,
            'node_coverage': node_coverage,
            'projection_mode': 'BOUNDED_SQL_PAGE_V1',
        }
        value = {'summary': summary,
                 'node_coverage': _page_result(node_rows, active_nodes, offset, limit,
                                               'primary_type ASC, canonical_name ASC, node_id ASC'),
                 'unlinked_claims': _page_result(unlinked, unlinked_total, offset, limit,
                                                 'claim_id ASC'),
                 'knowledge_gaps': gaps,
                 'coverage_is_attribution': False, 'canonical_write': False,
                 'match_semantics': 'HEURISTIC_AUDIT_ONLY'}
        return self._with_snapshot(value)

    def questions(self, *, cursor: str | None = None, limit: int = 25, status: str = '') -> dict:
        return self._research_rows('research_questions', 'rq_id', cursor, limit, status)

    def gaps(self, *, cursor: str | None = None, limit: int = 25, status: str = '') -> dict:
        return self._research_rows('knowledge_gaps', 'gap_id', cursor, limit, status)

    def _research_rows(self, table: str, id_col: str, cursor: str | None, limit: int, status: str) -> dict:
        offset, limit = _page(cursor, limit)
        where, args = (' WHERE x.status=?', [status]) if status else ('', [])
        with self.connect() as conn:
            total = int(conn.execute(f'SELECT COUNT(*) FROM {table} x{where}', args).fetchone()[0])
            rows = []
            for row in conn.execute(f'''SELECT x.*,n.canonical_name,n.primary_type FROM {table} x
                    JOIN nodes n ON n.node_id=x.node_id{where}
                    ORDER BY x.updated_at DESC,x.{id_col} LIMIT ? OFFSET ?''', (*args, limit, offset)):
                item = dict(row)
                for field in tuple(item):
                    if field.endswith('_json'):
                        item[field.removesuffix('_json')] = _json(item.pop(field), [])
                rows.append(item)
            value = {'status_filter': status,
                     **_page_result(rows, total, offset, limit, f'updated_at DESC, {id_col} ASC')}
        return self._with_snapshot(value)

    def validate_object(self, object_type: str, object_id: str) -> None:
        if object_type not in OBJECT_TYPES:
            raise ResearchError('UNSUPPORTED_RESEARCH_OBJECT')
        table, column = {
            'NODE': ('nodes', 'node_id'), 'CLAIM': ('claims', 'claim_id'),
            'SOURCE': ('sources', 'source_id'), 'RELATION': ('node_relations', 'relation_id'),
            'GAP': ('knowledge_gaps', 'gap_id'), 'RESEARCH_QUESTION': ('research_questions', 'rq_id'),
        }[object_type]
        with self.connect() as conn:
            if conn.execute(f'SELECT 1 FROM {table} WHERE {column}=?', (object_id,)).fetchone() is None:
                raise ResearchError(object_type + '_NOT_FOUND' if object_type in ('NODE','CLAIM','SOURCE','RELATION') else 'UNSUPPORTED_RESEARCH_OBJECT', 404)
