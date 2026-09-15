"""Durable human overlay; native inputs and Production are never mutation targets."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json

from pro_a.phase3f_review_completion import (
    ReviewCompletionError, _validate_completed_human_inputs, validate_completed_review_packet,
)
from pro_a.production_promotion import canonical_sha256
from .artifacts import Artifacts
from .config import BoundaryError
from .review import require_safe_projection
from .review_store import schema_version
from .store import Store

GROUPS = ('claims', 'nodes', 'relations')


class ReviewError(BoundaryError):
    def __init__(self, code, *, status=409, current_revision=None, native_code=None):
        super().__init__(code)
        self.status = status
        self.current_revision = current_revision
        self.native_code = native_code


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def compose(blank, states, reviewer):
    completed = copy.deepcopy(blank)
    completed['human_completion']['reviewer'] = reviewer
    for group in GROUPS:
        for row in completed[group]:
            state = states.get(row['candidate_id'], {})
            for field in row['human_input']:
                row['human_input'][field] = state.get(field, '')
    return completed


def validate_partial(blank, states, reviewer):
    """Native human-input rules on ONLY explicit decisions, not completion accounting."""
    partial = compose(blank, states, reviewer)
    for group in GROUPS:
        partial[group] = [row for row in partial[group] if row['human_input']['decision']]
    try:
        _validate_completed_human_inputs(partial)
    except ReviewCompletionError as error:
        code = 'DEPENDENCY_INVALID' if error.code.startswith(('PARENT_', 'RELATION_')) else 'VALIDATION_ERROR'
        raise ReviewError(code, status=422, native_code=error.code) from None


def available_actions(blank, row, states):
    """Probe the unchanged native validator; probe values are never stored or sealed."""
    allowed, blocked = [], {}
    probe_blank = {'human_completion': {'reviewer': ''}, **{group: [] for group in GROUPS}}
    group = {'CLAIM': 'claims', 'NODE': 'nodes', 'PARENT_PLACEMENT': 'relations'}[row['candidate_type']]
    probe_blank[group] = [row]
    if row['candidate_type'] == 'PARENT_PLACEMENT':
        probe_blank['nodes'] = [child for child in blank['nodes'] if child['candidate_id'] == row['content']['child_node_candidate_id']]
    for decision in row['allowed_decisions']:
        targets = (row['content'].get('exact_production_resolution') or {}).get('candidate_target_node_ids') or []
        probe = {'decision': decision, 'reason': 'Capability validation only',
                 'target_node_id': targets[0] if decision == 'REUSE' and len(targets) == 1 else ''}
        try:
            proposed = {**states, row['candidate_id']: probe}
            validate_partial(probe_blank, proposed, 'Capability validation only')
            allowed.append(decision)
        except ReviewError as error:
            blocked[decision] = error.native_code
    return {'available_decisions': allowed, 'blocked_decisions': blocked,
            'reuse_target': targets[0] if len(targets) == 1 else None}


def invalidate_parents(blank, row, states):
    invalidated = []
    if row['candidate_type'] == 'NODE' and states.get(row['candidate_id'], {}).get('decision') != 'CREATE':
        for parent in blank['relations']:
            parent_id = parent['candidate_id']
            if parent['content']['child_node_candidate_id'] == row['candidate_id'] and states.get(parent_id, {}).get('decision') == 'CREATE':
                invalidated.append((parent_id, states.pop(parent_id)))
    return invalidated


class ReviewWorkbench:
    def __init__(self, config):
        self.config = config
        self.store = Store(config)
        self.artifacts = Artifacts(config)

    def _context(self, handle):
        try:
            blank, run, dto = self.artifacts.native(handle)
        except BoundaryError as error:
            if str(error) in ('ARTIFACT_HASH_MISMATCH', 'ARTIFACT_CHANGED_DURING_READ'):
                raise ReviewError('IMMUTABLE_FIELD_DRIFT') from None
            if str(error) in ('REGISTRY_IDENTITY_MISMATCH', 'NATIVE_PACKET_UNAVAILABLE'):
                raise ReviewError('ARTIFACT_IDENTITY_MISMATCH') from None
            raise
        basis = canonical_sha256({key: dto[key] for key in ('artifact_id', 'packet_id', 'packet_file_sha256', 'immutable_packet_sha256', 'mode')})
        return blank, run, dto, basis

    def _state(self, connection, handle, basis):
        draft = connection.execute('SELECT * FROM review_drafts WHERE artifact_id=?', (handle,)).fetchone()
        if draft and draft['basis_id'] != basis:
            raise ReviewError('ARTIFACT_IDENTITY_MISMATCH')
        states = {row['candidate_id']: json.loads(row['state_json']) for row in connection.execute('SELECT * FROM review_decisions WHERE artifact_id=?', (handle,))}
        audit = []
        for row in connection.execute('SELECT * FROM review_audit WHERE artifact_id=? ORDER BY event_id', (handle,)):
            event = dict(row)
            event['old_state'] = json.loads(event.pop('old_json'))
            event['new_state'] = json.loads(event.pop('new_json'))
            audit.append(event)
        if draft and (not audit or max(row['revision'] for row in audit) != draft['revision']):
            raise ReviewError('RECOVERY_REQUIRED')
        replayed = {}
        for event in audit:
            candidate_id = event['candidate_id']
            if candidate_id is not None:
                if event['old_state'] != replayed.get(candidate_id):
                    raise ReviewError('RECOVERY_REQUIRED')
                if event['new_state'] is None: replayed.pop(candidate_id, None)
                else: replayed[candidate_id] = event['new_state']
        operations = {row[0] for row in connection.execute('SELECT operation_id FROM review_operations WHERE artifact_id=?', (handle,))}
        if replayed != states or operations != {event['operation_id'] for event in audit}:
            raise ReviewError('RECOVERY_REQUIRED')
        if draft and (len(operations) != draft['revision'] or (draft['status'] == 'SEALED') != (audit[-1]['event_type'] == 'SEALED')):
            raise ReviewError('RECOVERY_REQUIRED')
        return dict(draft) if draft else None, states, audit

    def _sealed(self, connection, handle, draft, blank, run, states):
        objects = list(connection.execute('SELECT * FROM sealed_review_artifacts WHERE artifact_id=? ORDER BY kind', (handle,)))
        if not draft or draft['status'] != 'SEALED':
            if objects:
                raise ReviewError('RECOVERY_REQUIRED')
            return None
        if {row['kind'] for row in objects} != {'completed_packet', 'completion_receipt'}:
            raise ReviewError('RECOVERY_REQUIRED')
        decoded = {}
        for row in objects:
            content = bytes(row['body'])
            if hashlib.sha256(content).hexdigest() != row['sha256'] or row['object_id'] != row['kind'].upper() + '_' + row['sha256']:
                raise ReviewError('RECOVERY_REQUIRED')
            try:
                decoded[row['kind']] = json.loads(content)
            except (ValueError, UnicodeError):
                raise ReviewError('RECOVERY_REQUIRED') from None
        completed = compose(blank, states, draft['reviewer'])
        if decoded['completed_packet'] != completed:
            raise ReviewError('RECOVERY_REQUIRED')
        try:
            validation = validate_completed_review_packet(completed, run)
        except ReviewCompletionError:
            raise ReviewError('RECOVERY_REQUIRED') from None
        if decoded['completion_receipt'] != validation:
            raise ReviewError('RECOVERY_REQUIRED')
        return {'objects': [{key: row[key] for key in ('kind', 'object_id', 'sha256')} for row in objects],
                'validation': validation, 'production_authorized': False, 'qualification_created': False}

    def read(self, handle):
        blank, run, dto, basis = self._context(handle)
        with self.store.connect() as connection:
            connection.execute('BEGIN')
            if schema_version(connection) == '1':
                return {**dto, 'review': {'enabled': False}}
            draft, states, audit = self._state(connection, handle, basis)
            native = [row for group in GROUPS for row in blank[group]]
            if set(states) - {row['candidate_id'] for row in native}:
                raise ReviewError('RECOVERY_REQUIRED')
            if states:
                try:
                    validate_partial(blank, states, draft['reviewer'])
                except ReviewError:
                    raise ReviewError('RECOVERY_REQUIRED') from None
            sealed = self._sealed(connection, handle, draft, blank, run, states)
        rows = []
        for row in native:
            candidate_id = row['candidate_id']
            state = states.get(candidate_id)
            capability = available_actions(blank, row, states)
            events = [event for event in audit if event['candidate_id'] == candidate_id]
            decision = state['decision'] if state else ''
            content = row['content']
            guards = content.get('semantic_admission') or {}
            warning = bool(guards.get('guard_reasons') or content.get('current_defer_reason') or content.get('review_admitted') is False)
            queues = ['completed', 'recently_decided'] if state else ['needs_review']
            if row['candidate_type'] == 'NODE': queues.append('entity_resolution')
            if row['candidate_type'] == 'PARENT_PLACEMENT': queues.append('parent_placement')
            if decision in ('DEFER', 'KEEP_NEEDS_REVIEW'): queues.append('deferred')
            if warning: queues.append('high_attention')
            rows.append({'candidate_id': candidate_id, 'state': state, 'queues': queues, **capability,
                         'decision_effect': row['decision_effects'].get(decision),
                         'nonpromotable': decision in ('DEFER', 'KEEP_NEEDS_REVIEW', 'REJECT', 'DROP'),
                         'undo_event_id': events[-1]['event_id'] if events and events[-1]['event_type'] == 'SAVE' and not sealed else None})
        progress = {'total_native_rows': len(native), 'required': len(native), 'completed': len(states),
                    'remaining': len(native) - len(states), 'excluded': blank['excluded_relation_inventory']['count'],
                    'deferred': sum('deferred' in row['queues'] for row in rows),
                    'nonpromotable': sum(row['nonpromotable'] for row in rows),
                    'warnings': sum('high_attention' in row['queues'] for row in rows), 'invalid': 0,
                    'dependency_blocked': sum(row['blocked_decisions'].get('CREATE') == 'PARENT_PLACEMENT_REQUIRES_NODE_CREATE' for row in rows)}
        result = {**dto, 'review': {'enabled': True, 'basis_id': basis, 'review_id': 'REVIEW_' + basis,
            'revision': draft['revision'] if draft else 0, 'reviewer': draft['reviewer'] if draft else '',
            'status': draft['status'] if draft else 'DRAFT', 'progress': progress, 'rows': rows, 'audit': audit, 'sealed': sealed},
            'capabilities': {**dto['capabilities'], 'read_only': bool(sealed), 'decision_save_available': not bool(sealed)}}
        require_safe_projection(result)
        return result

    def _write_state(self, connection, handle, candidate_id, state):
        if state is None:
            connection.execute('DELETE FROM review_decisions WHERE artifact_id=? AND candidate_id=?', (handle, candidate_id))
        else:
            connection.execute('INSERT INTO review_decisions VALUES(?,?,?) ON CONFLICT(artifact_id,candidate_id) DO UPDATE SET state_json=excluded.state_json', (handle, candidate_id, encode(state)))

    def _audit(self, connection, handle, request, identity, revision, kind, candidate_id, old, new, reason, timestamp):
        connection.execute('INSERT INTO review_audit(artifact_id,revision,operation_id,candidate_id,event_type,old_json,new_json,actor,session_id,reviewer,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (handle, revision, request['operation_id'], candidate_id, kind, encode(old), encode(new), identity['actor'], identity['session_id'], request['reviewer'], reason, timestamp))

    def _publish(self, connection, handle, kind, value):
        body = encode(value).encode('utf-8')
        sha = hashlib.sha256(body).hexdigest()
        object_id = kind.upper() + '_' + sha
        connection.execute('INSERT INTO sealed_review_artifacts VALUES(?,?,?,?,?)', (handle, kind, object_id, sha, body))
        return {'kind': kind, 'object_id': object_id, 'sha256': sha}

    def mutate(self, handle, action, request, identity):
        blank, run, dto, basis = self._context(handle)
        if request['basis_id'] != basis:
            raise ReviewError('IMMUTABLE_FIELD_DRIFT')
        for key in ('reviewer', 'reason'):
            value = request.get(key, '')
            if not value or value != value.strip():
                raise ReviewError('VALIDATION_ERROR', status=422)
        require_safe_projection({'reviewer': request['reviewer'], 'reason': request['reason']})
        fingerprint = canonical_sha256({'action': action, 'request': request, 'actor': identity['actor']})
        with self.store.connect(operator_write=True) as connection:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('BEGIN IMMEDIATE')
            if schema_version(connection) not in ('2', '3', '4', '5', '6'):
                raise ReviewError('REVIEW_SCHEMA_REQUIRED')
            draft, states, audit = self._state(connection, handle, basis)
            self._sealed(connection, handle, draft, blank, run, states)
            operation = connection.execute('SELECT * FROM review_operations WHERE artifact_id=? AND operation_id=?', (handle, request['operation_id'])).fetchone()
            if operation:
                if operation['request_sha256'] != fingerprint:
                    raise ReviewError('IDEMPOTENCY_CONFLICT')
                return json.loads(operation['response_json'])
            if draft and draft['status'] == 'SEALED':
                raise ReviewError('ALREADY_SEALED')
            revision = draft['revision'] if draft else 0
            if request['expected_revision'] != revision:
                raise ReviewError('REVISION_CONFLICT', current_revision=revision)
            if draft and draft['reviewer'] != request['reviewer']:
                raise ReviewError('REVIEWER_MISMATCH', status=422)
            timestamp = datetime.now(timezone.utc).isoformat()
            revision += 1
            if draft is None:
                connection.execute('INSERT INTO review_drafts VALUES(?,?,?,?,?,?,?)',
                    (handle, 'REVIEW_' + basis, basis, request['reviewer'], 0, 'DRAFT', timestamp))
            response = {'operation_id': request['operation_id'], 'revision': revision}
            if action in ('decision', 'undo'):
                native = {row['candidate_id']: row for group in GROUPS for row in blank[group]}
                candidate_id = request['candidate_id']
                if candidate_id not in native:
                    raise ReviewError('NOT_REVIEWABLE', status=422)
                row = native[candidate_id]
                old = states.get(candidate_id)
                if action == 'undo':
                    events = [event for event in audit if event['candidate_id'] == candidate_id]
                    if not events or events[-1]['event_type'] != 'SAVE' or events[-1]['event_id'] != request['event_id']:
                        raise ReviewError('UNDO_NOT_AVAILABLE')
                    new = events[-1]['old_state']
                    if new is not None:
                        new = {**new, 'revision': revision, 'updated_at': timestamp, 'actor': identity['actor'], 'session_id': identity['session_id']}
                else:
                    new = {key: request.get(key, '') for key in ('decision', 'reason', 'target_node_id', 'reviewer')}
                    new.update(actor=identity['actor'], session_id=identity['session_id'], revision=revision, updated_at=timestamp)
                    if not new['decision'] or (row['candidate_type'] != 'NODE' and new['target_node_id']):
                        raise ReviewError('VALIDATION_ERROR', status=422)
                proposed = {**states}
                if new is None: proposed.pop(candidate_id, None)
                else: proposed[candidate_id] = new
                invalidated = invalidate_parents(blank, row, proposed)
                validate_partial(blank, proposed, request['reviewer'])
                self._write_state(connection, handle, candidate_id, new)
                self._audit(connection, handle, request, identity, revision, 'UNDO' if action == 'undo' else 'SAVE', candidate_id, old, new, request['reason'], timestamp)
                for parent_id, old_parent in invalidated:
                    self._write_state(connection, handle, parent_id, None)
                    self._audit(connection, handle, request, identity, revision, 'DEPENDENCY_INVALIDATED', parent_id, old_parent, None,
                                'Child decision no longer permits parent CREATE; explicit review is required.', timestamp)
                response['invalidated_items'] = [item[0] for item in invalidated]
            elif action == 'seal':
                if request.get('confirm') is not True:
                    raise ReviewError('SEAL_CONFIRMATION_REQUIRED', status=422)
                completed = compose(blank, states, request['reviewer'])
                try:
                    validation = validate_completed_review_packet(completed, run)
                except ReviewCompletionError as error:
                    raise ReviewError('VALIDATION_ERROR', status=422, native_code=error.code) from None
                response['objects'] = [self._publish(connection, handle, 'completed_packet', completed),
                                       self._publish(connection, handle, 'completion_receipt', validation)]
                response['production_authorized'] = False
                self._audit(connection, handle, request, identity, revision, 'SEALED', None, {'status': 'DRAFT'},
                            {'status': 'SEALED', 'objects': response['objects'], 'production_authorized': False}, request['reason'], timestamp)
            else:
                raise ReviewError('VALIDATION_ERROR', status=422)
            # Re-check frozen input identities before publishing any Workbench transaction.
            self.artifacts.read(handle)
            connection.execute('UPDATE review_drafts SET revision=?,status=?,updated_at=? WHERE artifact_id=?',
                (revision, 'SEALED' if action == 'seal' else 'DRAFT', timestamp, handle))
            connection.execute('INSERT INTO review_operations VALUES(?,?,?,?)', (handle, request['operation_id'], fingerprint, encode(response)))
        return response

    def validate_completion(self, handle, expected_revision, basis_id):
        blank, run, _, basis = self._context(handle)
        if basis != basis_id:
            raise ReviewError('IMMUTABLE_FIELD_DRIFT')
        with self.store.connect() as connection:
            connection.execute('BEGIN')
            if schema_version(connection) not in ('2', '3', '4', '5', '6'):
                raise ReviewError('REVIEW_SCHEMA_REQUIRED')
            draft, states, _ = self._state(connection, handle, basis)
            revision = draft['revision'] if draft else 0
            if revision != expected_revision:
                raise ReviewError('REVISION_CONFLICT', current_revision=revision)
            try:
                validation = validate_completed_review_packet(compose(blank, states, draft['reviewer'] if draft else ''), run)
            except ReviewCompletionError as error:
                raise ReviewError('VALIDATION_ERROR', status=422, native_code=error.code) from None
        return {'revision': revision, 'validation': validation, 'production_authorized': False}

    def sealed_result(self, handle):
        result = self.read(handle)['review']
        if not result.get('sealed'):
            raise ReviewError('REVIEW_NOT_SEALED')
        return result['sealed']
