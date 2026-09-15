"""Stage 3 Current View read, draft, validation, qualification and reconciliation."""
from __future__ import annotations

import copy
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .current_view import render_current_view
from .current_view_compare import compare_view_content
from .current_view_pilot import CurrentViewPilotError, _validate_frozen_content_contract
from .db import CURRENT_VIEW_ORDER
from .human_review_intake import PRIMARY_STATUSES
from .operational_contract import identity, readonly, require, sealed, snapshot, verify
from .production_promotion import canonical_sha256
from .query import ReadOnlyQuery
from .workbench.config import BoundaryError
from .workbench.review_store import schema_version
from .workbench.store import Store


VERSION = 'phase42-view-v1'
ENTRY_VERSION = 'phase42-view-operator-v1'
SUPPORTED_TYPES = ('Company', 'Product')
CHANGE_LEVELS = ('initial', 'minor', 'material', 'thesis')
CONTRACT = Path(__file__).resolve().parents[2] / 'docs/PHASE4_STAGE42_STAGE3_VIEW_CONTRACT.json'
CONTRACT_SHA = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
CONTENT_FIELDS = ('one_line_conclusion', 'core_logic', 'key_facts', 'core_disagreements',
                  'assumptions_to_verify', 'investment_implication', 'major_risks',
                  'knowledge_gaps', 'key_watch_items', 'recent_change',
                  'evidence_claim_ids', 'type_specific')
VIEW_COLUMNS = ('view_id', 'node_id', 'version', 'status', 'change_level', 'previous_view_id',
                'content_md', 'content_json', 'trigger_source_id', 'trigger_claim_ids_json',
                'revision_date', 'revision_seq', 'accepted_proposal_id', 'created_at', 'confirmed_at')
PACKAGE_FIELDS = {'document_type', 'adapter_version', 'operator_entry_version', 'contract_sha256',
                  'runtime_identity', 'node_id', 'node_type', 'mode', 'draft_id', 'draft_revision',
                  'draft_basis_sha256', 'quality_validation', 'evidence_basis', 'baseline',
                  'predicted_diff', 'production_authorized', 'object_id', 'sha256'}
DIFF_FIELDS = {'operation', 'table', 'key', 'row', 'old_official_view_id',
               'new_official_view_id', 'pre_state_sha256', 'post_state_sha256',
               'unrelated_tables_sha256', 'object_id', 'sha256'}


def runtime_identity():
    root = Path(__file__).resolve().parent
    names = ('current_view_workbench.py', 'view_operator.py', 'current_view.py',
             'current_view_compare.py', 'current_view_pilot.py', 'human_review_intake.py',
             'query.py', 'workbench/view_store.py')
    return canonical_sha256({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                             for name in names})


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _official(connection, node_id):
    row = connection.execute(f"""SELECT * FROM current_views WHERE node_id=? AND status='official'
                               ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1""", (node_id,)).fetchone()
    return ReadOnlyQuery._current_view_result(row) if row else None


def _views(connection, node_id, status):
    rows = connection.execute(f"""SELECT * FROM current_views WHERE node_id=? AND status=?
                                ORDER BY {CURRENT_VIEW_ORDER}""", (node_id, status)).fetchall()
    return [ReadOnlyQuery._current_view_result(row) for row in rows]


def _evidence(connection, node_id):
    rows = connection.execute('''SELECT c.*,l.role,s.title AS source_title,
              s.publication_time AS source_publication_time,s.source_rank,s.source_type,s.organization,s.sha256 AS source_sha256,
              s.origin_type,s.underlying_source_id
            FROM claim_node_links l JOIN claims c ON c.claim_id=l.claim_id
            JOIN sources s ON s.source_id=c.source_id WHERE l.node_id=? ORDER BY c.claim_id''', (node_id,)).fetchall()
    result = []
    for raw in rows:
        row = dict(raw)
        if row['fact_time']:
            business_date, basis = row['fact_time'], 'claim_fact_time'
        elif row['publication_time']:
            business_date, basis = row['publication_time'], 'claim_publication_time'
        elif row['source_publication_time']:
            business_date, basis = row['source_publication_time'], 'source_publication_time'
        else:
            business_date, basis = None, 'unknown'
        result.append({
            'claim_id': row['claim_id'], 'statement': row['statement'], 'nature': row['nature'],
            'status': row['status'], 'confidence': row['confidence'], 'role': row['role'],
            'scope': row['scope'], 'attributed_to': row['attributed_to'],
            'source_id': row['source_id'], 'source_rank': row['source_rank'],
            'origin_type': row['origin_type'], 'underlying_source_id': row['underlying_source_id'],
            'evidence_excerpt': row['evidence_excerpt'], 'evidence_pointer': row['evidence_pointer'],
            'source_locator': ReadOnlyQuery._source_locator(row['structured_json']),
            'source': {'source_id': row['source_id'], 'title': row['source_title'],
                       'publication_time': row['source_publication_time'], 'source_rank': row['source_rank'],
                       'source_type': row['source_type'], 'organization': row['organization'],
                       'sha256': row['source_sha256']},
            'business_date': business_date, 'freshness_basis': basis,
            'primary_eligible': row['role'] == 'subject' and row['status'].strip().lower() in PRIMARY_STATUSES,
        })
    return result


def _basis(node, official, evidence):
    return canonical_sha256({'node': node, 'official': official, 'evidence': evidence,
                             'schema': '0.2.3', 'runtime': runtime_identity()})


def _uncertainty(content, evidence):
    content = content if isinstance(content, dict) else {}
    return {
        'core_disagreements': content.get('core_disagreements') if isinstance(content.get('core_disagreements'), list) else [],
        'assumptions_to_verify': content.get('assumptions_to_verify') if isinstance(content.get('assumptions_to_verify'), list) else [],
        'knowledge_gaps': content.get('knowledge_gaps') if isinstance(content.get('knowledge_gaps'), list) else [],
        'review_needed_claims': [item['claim_id'] for item in evidence if item['status'].strip().lower() == 'needs_review'],
    }


def _draft(connection, node_id, basis):
    row = connection.execute('SELECT * FROM view_drafts WHERE node_id=?', (node_id,)).fetchone()
    if row is None:
        return None
    body = json.loads(row['body'])
    events = [json.loads(event[0]) for event in connection.execute(
        'SELECT event_json FROM view_draft_events WHERE node_id=? ORDER BY revision', (node_id,))]
    require(len(events) == row['revision'] and events[-1]['body'] == body, 'RECOVERY_REQUIRED')
    return {'draft_id': row['draft_id'], 'revision': row['revision'], 'reviewer': row['reviewer'],
            'status': 'STALE' if row['basis_sha256'] != basis else row['status'],
            'basis_sha256': row['basis_sha256'], 'updated_at': row['updated_at'], **body,
            'audit': [{k: event[k] for k in ('revision', 'action', 'reviewer', 'reason', 'updated_at')}
                      for event in events]}


class CurrentViewWorkbench:
    def __init__(self, config):
        self.config = config
        self.store = Store(config)

    def _context(self, node_id):
        with closing(readonly(self.config.knowledge_db)) as connection:
            node_row = connection.execute('SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE node_id=?', (node_id,)).fetchone()
            require(node_row is not None, 'VIEW_NOT_FOUND')
            node = dict(node_row)
            official = _official(connection, node_id)
            history = _views(connection, node_id, 'official')
            baselines = _views(connection, node_id, 'baseline')
            evidence = _evidence(connection, node_id)
        return node, official, history, baselines, evidence, _basis(node, official, evidence)

    def read(self, node_id):
        node, official, history, baselines, evidence, basis = self._context(node_id)
        with self.store.connect() as connection:
            require(schema_version(connection) in ('4', '5', '6'), 'CURRENT_VIEW_SCHEMA_REQUIRED')
            draft = _draft(connection, node_id, basis)
            packages = [json.loads(row[0]) for row in connection.execute(
                'SELECT body FROM view_activation_packages WHERE node_id=? ORDER BY object_id', (node_id,))]
            receipts = [json.loads(row[0]) for row in connection.execute(
                'SELECT body FROM view_activation_receipts WHERE node_id=? ORDER BY object_id', (node_id,))]
        official_ids = set(official['trigger_claim_ids']) if official else set()
        official_evidence = [{**item, 'resolved': True,
                              'officially_referenced': item['claim_id'] in official_ids,
                              'evidence_class': 'PRIMARY' if item['claim_id'] in official_ids else 'CONTEXT_ONLY'}
                             for item in evidence if item['claim_id'] in official_ids or item['role'] == 'context']
        resolved_ids = {item['claim_id'] for item in official_evidence}
        official_evidence.extend({'claim_id': claim_id, 'resolved': False,
                                  'officially_referenced': True, 'evidence_class': 'PRIMARY',
                                  'error': 'EVIDENCE_NOT_FOUND'} for claim_id in sorted(official_ids - resolved_ids))
        predecessor_id = official.get('previous_view_id') if official else None
        previous = next((item for item in history if item['view_id'] == predecessor_id), None)
        comparison = compare_view_content(previous['content_json'], official['content_json']) if previous and official else None
        return {
            'node': node, 'selection_rule': CURRENT_VIEW_ORDER, 'official': official,
            'previous_official': previous, 'history': history, 'baseline_views': baselines,
            'history_labels': [{'view_id': item['view_id'], 'state': 'OFFICIAL' if index == 0 else 'PRIOR_OFFICIAL'}
                               for index, item in enumerate(history)],
            'official_comparison': comparison, 'official_evidence': official_evidence,
            'available_evidence': evidence, 'freshness': [{'claim_id': item['claim_id'],
                'business_date': item['business_date'], 'basis': item['freshness_basis']} for item in evidence],
            'uncertainty': _uncertainty(official['content_json'] if official else {}, evidence),
            'basis_sha256': basis, 'draft': draft,
            'activation_packages': [{'object_id': item['object_id'], 'draft_revision': item['draft_revision'],
                                      'predicted_diff': item['predicted_diff'], 'production_authorized': False}
                                     for item in packages],
            'activation_receipts': [{'object_id': item['object_id'], 'package_id': item['package_id'],
                                      'status': item['status']} for item in receipts],
            'capabilities': {'initial_supported': node['primary_type'] in SUPPORTED_TYPES and official is None,
                             'update_supported': node['primary_type'] in SUPPORTED_TYPES and official is not None,
                             'browser_activation': False, 'canonical_write': False},
        }

    def save(self, node_id, request, identity):
        node, official, _history, _baselines, evidence, basis = self._context(node_id)
        require(request['basis_sha256'] == basis, 'BASELINE_STALE')
        require(node['status'] == 'active', 'UNSUPPORTED_NODE_TYPE')
        require(node['primary_type'] in SUPPORTED_TYPES, 'UNSUPPORTED_NODE_TYPE')
        mode = request['mode']
        require(mode in ('INITIAL', 'UPDATE'), 'INVALID_REQUEST')
        change_level = request['change_level']
        require(change_level in CHANGE_LEVELS, 'INVALID_REQUEST')
        if mode == 'INITIAL':
            require(official is None and request['expected_official_view_id'] == '', 'INITIAL_VIEW_RACE')
            require(change_level == 'initial', 'INVALID_REQUEST')
        else:
            require(official is not None, 'VIEW_NOT_FOUND')
            require(request['expected_official_view_id'] == official['view_id'], 'BASELINE_STALE')
            require(change_level != 'initial', 'INVALID_REQUEST')
        require(request['reviewer'].strip() == request['reviewer'] and request['reviewer'], 'INVALID_REQUEST')
        require(request['reason'].strip() == request['reason'] and request['reason'], 'INVALID_REQUEST')
        content = request['content']
        require(isinstance(content, dict) and set(content) <= set(CONTENT_FIELDS), 'QUALITY_VALIDATION_FAILED')
        try:
            _json(content)
        except (TypeError, ValueError):
            raise BoundaryError('QUALITY_VALIDATION_FAILED') from None
        available = {item['claim_id'] for item in evidence}
        primary = request['primary_claim_ids']
        context = request['context_claim_ids']
        require(isinstance(primary, list) and isinstance(context, list) and
                all(isinstance(item, str) and item and item == item.strip() for item in primary + context),
                'EVIDENCE_NOT_FOUND')
        require(len(primary) == len(set(primary)) and len(context) == len(set(context)), 'EVIDENCE_NOT_FOUND')
        require(set(primary + context) <= available, 'EVIDENCE_NOT_FOUND')
        body = {'mode': mode, 'expected_official_view_id': request['expected_official_view_id'],
                'content': content, 'primary_claim_ids': primary, 'context_claim_ids': context,
                'change_level': change_level, 'quality_validation': None}
        fingerprint = canonical_sha256({'action': 'SAVE', 'request': request, 'actor': identity['actor']})
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            require(schema_version(connection) in ('4', '5', '6'), 'CURRENT_VIEW_SCHEMA_REQUIRED')
            old = connection.execute('SELECT * FROM view_drafts WHERE node_id=?', (node_id,)).fetchone()
            operation = connection.execute('SELECT request_sha256,response_json FROM view_draft_events WHERE node_id=? AND operation_id=?', (node_id, request['operation_id'])).fetchone()
            if operation:
                require(operation['request_sha256'] == fingerprint, 'IDEMPOTENCY_CONFLICT')
                return json.loads(operation['response_json'])
            revision = old['revision'] if old else 0
            require(request['expected_revision'] == revision, 'REVISION_CONFLICT')
            require(old is None or old['reviewer'] == request['reviewer'], 'REVIEWER_MISMATCH')
            updated = datetime.now(timezone.utc).isoformat()
            revision += 1
            draft_id = old['draft_id'] if old else 'VIEWDRAFT_' + canonical_sha256({'node_id': node_id, 'reviewer': request['reviewer'], 'basis': basis})
            event = {'revision': revision, 'action': 'SAVE', 'body': body, 'reviewer': request['reviewer'],
                     'reason': request['reason'], 'updated_at': updated}
            response = {'draft_id': draft_id, 'revision': revision, 'status': 'DRAFT', 'basis_sha256': basis}
            connection.execute('''INSERT INTO view_drafts VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(node_id) DO UPDATE SET revision=excluded.revision,basis_sha256=excluded.basis_sha256,
                status=excluded.status,body=excluded.body,updated_at=excluded.updated_at''',
                (node_id, draft_id, revision, basis, request['reviewer'], 'DRAFT', _json(body), updated))
            connection.execute('INSERT INTO view_draft_events VALUES(?,?,?,?,?,?)',
                (node_id, revision, request['operation_id'], fingerprint, _json(event), _json(response)))
        return response

    def _quality(self, node_id, draft):
        node, official, _history, _baselines, evidence, basis = self._context(node_id)
        require(draft['basis_sha256'] == basis, 'BASELINE_STALE')
        require(node['primary_type'] in SUPPORTED_TYPES and node['status'] == 'active', 'UNSUPPORTED_NODE_TYPE')
        if draft['mode'] == 'INITIAL':
            require(official is None and draft['expected_official_view_id'] == '', 'INITIAL_VIEW_RACE')
        else:
            require(official is not None and official['view_id'] == draft['expected_official_view_id'], 'BASELINE_STALE')
            require(compare_view_content(official['content_json'], draft['content'])['has_changes'], 'NO_EFFECTIVE_CHANGE')
        by_id = {item['claim_id']: item for item in evidence}
        require(bool(draft['primary_claim_ids']), 'PRIMARY_EVIDENCE_INVALID')
        require(all(cid in by_id and by_id[cid]['primary_eligible'] for cid in draft['primary_claim_ids']), 'PRIMARY_EVIDENCE_INVALID')
        require(all(cid in by_id and by_id[cid]['role'] == 'context' for cid in draft['context_claim_ids']), 'PRIMARY_EVIDENCE_INVALID')
        require(draft['content'].get('evidence_claim_ids') == draft['primary_claim_ids'], 'PRIMARY_EVIDENCE_INVALID')
        try:
            _validate_frozen_content_contract(node, draft['content'], [by_id[cid] for cid in draft['primary_claim_ids']])
        except CurrentViewPilotError:
            raise BoundaryError('QUALITY_VALIDATION_FAILED') from None
        return {'status': 'PASS', 'validator': 'existing_frozen_current_view_contract',
                'node_type_supported': True, 'primary_evidence_subject_only': True,
                'context_excluded_from_primary': True, 'citation_identities_exact': True}

    def validate(self, node_id, request, identity):
        current = self.read(node_id)['draft']
        require(current is not None, 'VIEW_NOT_FOUND')
        require(request['draft_id'] == current['draft_id'], 'DRAFT_IDENTITY_MISMATCH')
        require(request['basis_sha256'] == current['basis_sha256'], 'BASELINE_STALE')
        require(request['expected_revision'] == current['revision'], 'REVISION_CONFLICT')
        quality = self._quality(node_id, current)
        body = {key: copy.deepcopy(current[key]) for key in ('mode', 'expected_official_view_id', 'content', 'primary_claim_ids', 'context_claim_ids', 'change_level')}
        body['quality_validation'] = quality
        fingerprint = canonical_sha256({'action': 'VALIDATE', 'request': request, 'actor': identity['actor']})
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT * FROM view_drafts WHERE node_id=?', (node_id,)).fetchone()
            operation = connection.execute('SELECT request_sha256,response_json FROM view_draft_events WHERE node_id=? AND operation_id=?', (node_id, request['operation_id'])).fetchone()
            if operation:
                require(operation['request_sha256'] == fingerprint, 'IDEMPOTENCY_CONFLICT')
                return json.loads(operation['response_json'])
            require(row['revision'] == request['expected_revision'] and row['basis_sha256'] == request['basis_sha256'], 'REVISION_CONFLICT')
            require(row['reviewer'] == request['reviewer'], 'REVIEWER_MISMATCH')
            revision = row['revision'] + 1
            updated = datetime.now(timezone.utc).isoformat()
            response = {'draft_id': row['draft_id'], 'revision': revision, 'status': 'VALIDATED', 'quality_validation': quality}
            event = {'revision': revision, 'action': 'VALIDATE', 'body': body, 'reviewer': request['reviewer'],
                     'reason': request['reason'], 'updated_at': updated}
            connection.execute('UPDATE view_drafts SET revision=?,status=?,body=?,updated_at=? WHERE node_id=?',
                               (revision, 'VALIDATED', _json(body), updated, node_id))
            connection.execute('INSERT INTO view_draft_events VALUES(?,?,?,?,?,?)',
                               (node_id, revision, request['operation_id'], fingerprint, _json(event), _json(response)))
        return response

    def qualify(self, node_id, draft_id, revision):
        state = self.read(node_id)
        draft = state['draft']
        require(draft is not None and draft['draft_id'] == draft_id and draft['revision'] == revision,
                'DRAFT_IDENTITY_MISMATCH')
        require(draft['status'] == 'VALIDATED', 'QUALITY_VALIDATION_FAILED')
        quality = self._quality(node_id, draft)
        with self.store.connect() as connection:
            existing = connection.execute('SELECT body FROM view_activation_packages WHERE node_id=? AND draft_revision=?', (node_id, revision)).fetchone()
            if existing:
                return json.loads(existing[0])
        with closing(readonly(self.config.knowledge_db)) as connection:
            before = snapshot(connection)
            node = state['node']
            official = state['official']
            timestamp = draft['updated_at']
            revision_date = timestamp[:10].replace('-', '')
            seq = connection.execute("SELECT MAX(revision_seq) FROM current_views WHERE node_id=? AND revision_date=? AND status='official'", (node_id, revision_date)).fetchone()[0]
            revision_seq = 0 if seq is None else int(seq) + 1
            version = f'v_{revision_date}' if revision_seq == 0 else f'v_{revision_date}_{revision_seq:02d}'
            proposed_id = 'VIEW_STAGE42_' + canonical_sha256({'draft_id': draft_id, 'revision': revision})[:32].upper()
            previous_id = official['view_id'] if official else None
            previous_version = official['version'] if official else ''
            row = {'view_id': proposed_id, 'node_id': node_id, 'version': version, 'status': 'official',
                   'change_level': draft['change_level'].lower(), 'previous_view_id': previous_id,
                   'content_md': render_current_view(node, version, draft['content'], draft['change_level'].lower(), previous_version),
                   'content_json': json.dumps(draft['content'], ensure_ascii=False),
                   'trigger_source_id': sorted({item['source']['source_id'] for item in state['available_evidence']
                                                if item['claim_id'] in draft['primary_claim_ids']})[0],
                   'trigger_claim_ids_json': json.dumps(draft['primary_claim_ids'], ensure_ascii=False),
                   'revision_date': revision_date, 'revision_seq': revision_seq, 'accepted_proposal_id': '',
                   'created_at': timestamp, 'confirmed_at': timestamp}
            after = copy.deepcopy(before)
            require(not any(item['view_id'] == proposed_id or (item['node_id'], item['version']) == (node_id, version)
                            for item in after['current_views']), 'VIEW_IDENTITY_COLLISION')
            after['current_views'].append(row)
            after['current_views'].sort(key=lambda item: json.dumps(item, sort_keys=True))
            diff = sealed({'operation': 'INSERT', 'table': 'current_views', 'key': {'view_id': proposed_id},
                           'row': row, 'old_official_view_id': previous_id,
                           'new_official_view_id': proposed_id,
                           'pre_state_sha256': canonical_sha256(before), 'post_state_sha256': canonical_sha256(after),
                           'unrelated_tables_sha256': canonical_sha256({k:v for k,v in before.items() if k != 'current_views'})}, 'VIEWDIFF')
        by_id = {item['claim_id']: item for item in state['available_evidence']}
        def evidence_identity(claim_id, role):
            item = by_id[claim_id]
            return {'claim_id': claim_id, 'role': role, 'status': item['status'],
                    'source_id': item['source_id'], 'source_sha256': item['source']['sha256']}
        evidence_basis = sealed({
            'primary': [evidence_identity(claim_id, 'subject') for claim_id in draft['primary_claim_ids']],
            'context': [evidence_identity(claim_id, 'context') for claim_id in draft['context_claim_ids']],
        }, 'VIEWEVIDENCE')
        body = {'document_type': 'phase42_view_activation_package', 'adapter_version': VERSION,
                'operator_entry_version': ENTRY_VERSION, 'contract_sha256': CONTRACT_SHA,
                'runtime_identity': runtime_identity(), 'node_id': node_id, 'node_type': state['node']['primary_type'],
                'mode': draft['mode'], 'draft_id': draft_id, 'draft_revision': revision,
                'draft_basis_sha256': draft['basis_sha256'], 'quality_validation': quality,
                'evidence_basis': evidence_basis,
                'baseline': identity(self.config.knowledge_db), 'predicted_diff': diff,
                'production_authorized': False}
        package = sealed(body, 'VIEWPACKAGE')
        with self.store.connect(operator_write=True) as connection:
            connection.execute('INSERT OR IGNORE INTO view_activation_packages VALUES(?,?,?,?)',
                               (package['object_id'], node_id, revision, _json(package)))
            stored = json.loads(connection.execute('SELECT body FROM view_activation_packages WHERE node_id=? AND draft_revision=?', (node_id, revision)).fetchone()[0])
            require(stored == package, 'PACKAGE_IDENTITY_COLLISION')
        return package

    def reconcile(self, node_id, receipt_id):
        with self.store.connect() as connection:
            row = connection.execute('SELECT body FROM view_activation_receipts WHERE object_id=? AND node_id=?', (receipt_id, node_id)).fetchone()
            require(row is not None, 'RECEIPT_NOT_REGISTERED')
            receipt = json.loads(row[0])
            verify(receipt, 'VIEWEXECUTION')
            package_row = connection.execute('SELECT body FROM view_activation_packages WHERE object_id=?', (receipt['package_id'],)).fetchone()
            require(package_row is not None, 'RECEIPT_MISMATCH')
            package = json.loads(package_row[0])
            verify_package(package)
        require(receipt['adapter_version'] == VERSION and receipt['status'] == 'EXECUTED', 'RECEIPT_MISMATCH')
        require(receipt['predicted_diff_id'] == package['predicted_diff']['object_id'], 'RECEIPT_MISMATCH')
        require(receipt['evidence_basis_id'] == package['evidence_basis']['object_id'], 'RECEIPT_MISMATCH')
        with closing(readonly(self.config.knowledge_db)) as connection:
            current = _official(connection, node_id)
            require(current and current['view_id'] == package['predicted_diff']['row']['view_id'], 'RECOVERY_REQUIRED')
            require(canonical_sha256(snapshot(connection)) == package['predicted_diff']['post_state_sha256'], 'RECOVERY_REQUIRED')
        return {'status': 'VERIFIED', 'receipt_id': receipt_id, 'package_id': receipt['package_id'],
                'official_view_id': current['view_id']}


def verify_package(package):
    verify(package, 'VIEWPACKAGE')
    require(set(package) == PACKAGE_FIELDS and package['document_type'] == 'phase42_view_activation_package',
            'ADAPTER_VERSION_MISMATCH')
    require(package['adapter_version'] == VERSION and package['operator_entry_version'] == ENTRY_VERSION,
            'ADAPTER_VERSION_MISMATCH')
    require(package['contract_sha256'] == CONTRACT_SHA, 'ADAPTER_VERSION_MISMATCH')
    require(package['runtime_identity'] == runtime_identity(), 'RUNTIME_IDENTITY_MISMATCH')
    require(package['node_type'] in SUPPORTED_TYPES, 'UNSUPPORTED_NODE_TYPE')
    require(package['mode'] in ('INITIAL', 'UPDATE') and isinstance(package['draft_revision'], int)
            and package['draft_revision'] > 0, 'DRAFT_IDENTITY_MISMATCH')
    require(package['production_authorized'] is False, 'ACTIVATION_NOT_AUTHORIZED')
    require(package['quality_validation'].get('status') == 'PASS', 'QUALITY_VALIDATION_FAILED')
    verify(package['evidence_basis'], 'VIEWEVIDENCE')
    require(set(package['evidence_basis']) == {'primary', 'context', 'object_id', 'sha256'} and
            bool(package['evidence_basis']['primary']), 'PRIMARY_EVIDENCE_INVALID')
    primary_ids, context_ids = [], []
    for role, destination in (('subject', primary_ids), ('context', context_ids)):
        key = 'primary' if role == 'subject' else 'context'
        for item in package['evidence_basis'][key]:
            require(set(item) == {'claim_id', 'role', 'status', 'source_id', 'source_sha256'} and
                    item['role'] == role and all(isinstance(item[field], str) and item[field]
                    for field in ('claim_id', 'status', 'source_id')) and
                    isinstance(item['source_sha256'], str) and len(item['source_sha256']) == 64,
                    'PRIMARY_EVIDENCE_INVALID')
            destination.append(item['claim_id'])
    require(len(primary_ids) == len(set(primary_ids)) and len(context_ids) == len(set(context_ids)) and
            not set(primary_ids) & set(context_ids), 'PRIMARY_EVIDENCE_INVALID')
    verify(package['predicted_diff'], 'VIEWDIFF')
    diff = package['predicted_diff']
    require(set(diff) == DIFF_FIELDS and diff['operation'] == 'INSERT' and diff['table'] == 'current_views' and
            diff['key'] == {'view_id': diff['row']['view_id']} and diff['row']['status'] == 'official',
            'UNSUPPORTED_MUTATION')
    require(set(diff['row']) == set(VIEW_COLUMNS) and json.loads(diff['row']['trigger_claim_ids_json']) == primary_ids,
            'PRIMARY_EVIDENCE_INVALID')
    require(diff['row']['node_id'] == package['node_id'], 'DRAFT_IDENTITY_MISMATCH')
    require(diff['new_official_view_id'] == diff['row']['view_id'] and
            diff['old_official_view_id'] == diff['row']['previous_view_id'], 'PREDICTED_DIFF_MISMATCH')
    require((package['mode'] == 'INITIAL' and diff['old_official_view_id'] is None and
             diff['row']['change_level'] == 'initial') or
            (package['mode'] == 'UPDATE' and isinstance(diff['old_official_view_id'], str) and
             bool(diff['old_official_view_id']) and diff['row']['change_level'] != 'initial'),
            'PREDICTED_DIFF_MISMATCH')
    return package
