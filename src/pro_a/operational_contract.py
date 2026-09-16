"""Versioned Stage 2 contract and pure/read-only canonical validation helpers."""
from __future__ import annotations

import copy
from contextlib import closing
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import sqlite3

from .foundation_schema_preparation import require_execution_schema
from .production_promotion import canonical_sha256, database_identity, nfkc_casefold
from .workbench.config import BoundaryError, checked_path

VERSION = 'phase42-operational-v1'
ENTRY_VERSION = 'phase42-operator-v1'
WEB_REQUEST = ContextVar('pro_a_unprivileged_web_request', default=False)
CONTRACT_SHA = '6d2dc5bf1d2d5c8e2945da86cd5bd25f0f4b3bb306e2946ad67738fdc9e16a7c'
KEYS = {'sources': ('source_id',), 'claims': ('claim_id',), 'nodes': ('node_id',),
        'node_aliases': ('alias',), 'node_relations': ('relation_id',), 'claim_node_links': ('claim_id', 'node_id')}


def require(condition, code):
    if not condition:
        raise BoundaryError(code)


def sealed(body, prefix):
    digest = canonical_sha256(body)
    return {**copy.deepcopy(body), 'object_id': prefix + '_' + digest, 'sha256': digest}


def verify(value, prefix):
    body = {k: v for k, v in value.items() if k not in ('object_id', 'sha256')}
    require(value == sealed(body, prefix), 'ARTIFACT_IDENTITY_MISMATCH')
    return body


def runtime_identity():
    root = Path(__file__).resolve().parent
    names = ('operational_contract.py', 'operational_qualification.py', 'operational_operator.py',
             'workbench/attribution.py', 'phase3f_operational_handoff.py', 'phase3f_review_completion.py',
             'claim_attribution_semantics.py', 'foundation_schema_preparation.py', 'production_promotion.py')
    return canonical_sha256({name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names})


def readonly(path):
    path = checked_path(Path(path))
    for suffix in ('-journal', '-wal', '-shm'):
        require(not checked_path(Path(str(path) + suffix), missing=True).exists(), 'RECOVERY_REQUIRED')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection


def identity(path):
    path = checked_path(Path(path))
    with closing(readonly(path)) as connection:
        require_execution_schema(connection)
    return {k: v for k, v in database_identity(path).items() if k != 'path'}


def snapshot(connection, schema='main'):
    require(schema in ('main', 'canonical'), 'SCHEMA_INVALID')
    tables = [r[0] for r in connection.execute(f"SELECT name FROM {schema}.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {table: sorted([dict(r) for r in connection.execute(f'SELECT * FROM {schema}."{table}"')], key=lambda r: json.dumps(r, sort_keys=True)) for table in tables}


def predicted_diff(connection, mutations):
    """Exact insert/no-op classification; never update a conflicting existing row."""
    before = snapshot(connection)
    after = copy.deepcopy(before)
    inserts, unchanged, seen = [], [], set()
    for mutation in mutations:
        table, row = mutation.get('table'), mutation.get('row')
        require(table in KEYS and mutation.get('operation') == 'INSERT' and isinstance(row, dict), 'UNSUPPORTED_MUTATION')
        key = {k: row.get(k) for k in KEYS[table]}
        require(all(v is not None and v != '' for v in key.values()) and mutation.get('key') == key, 'MUTATION_KEY_INVALID')
        token = (table, canonical_sha256(key))
        require(token not in seen, 'DUPLICATE_CANONICAL_KEY')
        seen.add(token)
        columns = {r[1]: r for r in connection.execute(f'PRAGMA table_info("{table}")')}
        require(set(row) <= set(columns), 'UNSUPPORTED_COLUMN')
        full = {}
        for name, definition in columns.items():
            if name in row: full[name] = row[name]
            elif definition[4] is not None:
                default = definition[4]
                full[name] = connection.execute('SELECT ' + default).fetchone()[0]
            else: full[name] = None
            require(not definition[3] or full[name] is not None, 'MISSING_REQUIRED_COLUMN')
        if table == 'node_relations':
            require(row.get('relation_type') == 'part_of' and row.get('status') == 'current', 'UNSUPPORTED_RELATION')
        matches = [old for old in after[table] if all(old[k] == v for k, v in key.items())]
        if matches:
            require(matches == [full], 'CANONICAL_COLLISION')
            unchanged.append({'table': table, 'key': key, 'row': full})
            continue
        if table == 'sources': require(not any(old['sha256'] == full['sha256'] for old in after[table]), 'SOURCE_COLLISION')
        if table == 'nodes':
            term = nfkc_casefold(full['canonical_name'])
            require(not any(nfkc_casefold(old['canonical_name']) == term for old in after['nodes']) and
                    not any(nfkc_casefold(old['alias']) == term for old in after['node_aliases']), 'NODE_COLLISION')
        if table == 'node_aliases':
            term = nfkc_casefold(full['alias'])
            require(not any(nfkc_casefold(old['alias']) == term for old in after['node_aliases']) and
                    not any(nfkc_casefold(old['canonical_name']) == term and old['node_id'] != full['node_id'] for old in after['nodes']), 'ALIAS_COLLISION')
        if table == 'node_relations':
            require(not any(all(old[k] == full[k] for k in ('from_node_id', 'relation_type', 'to_node_id', 'scope')) for old in after[table]), 'RELATION_COLLISION')
        after[table].append(full)
        inserts.append({'table': table, 'key': key, 'row': full})
    for table in after: after[table].sort(key=lambda r: json.dumps(r, sort_keys=True))
    return sealed({'inserts': inserts, 'updates': [], 'unchanged': unchanged,
                   'tables_touched': sorted({r['table'] for r in inserts}),
                   'pre_state_sha256': canonical_sha256(before), 'post_state_sha256': canonical_sha256(after)}, 'DIFF')


def verify_envelope(envelope):
    verify(envelope, 'OPERATIONAL')
    require(envelope.get('adapter_version') == VERSION and envelope.get('contract_sha256') == CONTRACT_SHA, 'ADAPTER_VERSION_MISMATCH')
    require(envelope.get('runtime_identity') == runtime_identity(), 'RUNTIME_IDENTITY_MISMATCH')
    require(envelope.get('baseline', {}).get('schema_version') == '0.2.3', 'SCHEMA_MISMATCH')
    verify(envelope['attribution'], 'ATTRIBUTION')
    verify(envelope['predicted_diff'], 'DIFF')
    require(envelope.get('production_authorized') is False, 'QUALIFICATION_NOT_AUTHORIZATION')
    for row in envelope['mutations']:
        require(row.get('table') in KEYS and row.get('operation') == 'INSERT', 'UNSUPPORTED_MUTATION')
        if row['table'] == 'node_relations': require(row['row'].get('relation_type') == 'part_of', 'UNSUPPORTED_RELATION')
