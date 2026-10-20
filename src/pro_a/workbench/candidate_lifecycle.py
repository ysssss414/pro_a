"""Explicit v7 revision selection. History is immutable; selection is not support."""
from contextlib import contextmanager
import hashlib
import json
import re
import sqlite3

from pro_a.evidence_binding import identity as digest
from .config import BoundaryError
from .store import Store

VERSION = 'candidate-revision-lifecycle-v1'
PROPOSAL = 'CANDIDATE_REVISIONS_PUBLISHED'
DECISION = 'CANDIDATE_REVISION_DECIDED'


def require(value, code):
    if not value:
        raise BoundaryError(code)


def reference(document, obj):
    scope = document['scope']
    parent = obj.get('parent')
    body = {k: scope[k] for k in ('source_id', 'source_sha256', 'run_id', 'attempt_id')}
    body.update(raw_sha256=document['raw_sha256'],
        parent_observation_id=parent['observation_id'] if parent else obj['observation_id'],
        child_id=obj['semantic_revision']['child']['child_id'] if parent else None)
    return {**body, 'logical_id': digest({'version': VERSION, **body}),
            'revision_sha256': obj['revision_sha256']}


def register(document, connection):
    if document['version'] != 'source-candidate-set-v2':
        return
    from .source_operations import SourceOperations
    body = {'version': VERSION, 'origin_identity': document['identity'],
            'references': [reference(document, o) for o in document['objects'] if o['family'] == 'claims']}
    prior = [json.loads(r[0]) for r in connection.execute(
        'SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?',
        (document['scope']['run_id'], PROPOSAL))]
    matches = [p for p in prior if p['origin_identity'] == document['identity']]
    require(not matches or matches == [body], 'CANDIDATE_LIFECYCLE_PUBLICATION_DRIFT')
    if not matches:
        SourceOperations._event(connection, document['scope']['run_id'], PROPOSAL, body)


def _head(state):
    if not state['epoch']:
        return None
    return digest({k: state[k] for k in ('logical_id', 'epoch', 'current_revision', 'selection_sha256')})


def _transition(states, request, decision_sha):
    ref, action, replacement = request['reference'], request['action'], request['replacement']
    state = states[ref['logical_id']]
    require(request['expected_head'] == _head(state), 'CANDIDATE_REVISION_STALE_HEAD')
    version = ref['revision_sha256']
    require(state['versions'].get(version) == 'AVAILABLE' or
            state['versions'].get(version) == 'ACTIVE', 'CANDIDATE_REVISION_TERMINAL')
    if action == 'SELECT':
        require(state['current_revision'] is None and state['versions'][version] == 'AVAILABLE'
                and replacement is None, 'CANDIDATE_REVISION_TRANSITION_INVALID')
        state['versions'][version] = 'ACTIVE'
        state.update(current_revision=version, selection_sha256=decision_sha)
    elif action == 'REPLACE':
        require(state['current_revision'] == version and state['versions'][version] == 'ACTIVE',
                'CANDIDATE_REVISION_NOT_CURRENT')
        require(replacement is not None and replacement['logical_id'] == ref['logical_id']
                and replacement['revision_sha256'] != version, 'CANDIDATE_REVISION_CROSS_OBJECT')
        new = replacement['revision_sha256']
        require(state['versions'].get(new) == 'AVAILABLE', 'CANDIDATE_REVISION_TERMINAL')
        state['versions'][version] = 'SUPERSEDED'
        state['versions'][new] = 'ACTIVE'
        state.update(current_revision=new, selection_sha256=decision_sha)
    elif action == 'REVOKE':
        require(replacement is None, 'CANDIDATE_REVISION_TRANSITION_INVALID')
        state['versions'][version] = 'REVOKED'
        if state['current_revision'] == version:
            state.update(current_revision=None, selection_sha256=None)
    else:
        raise BoundaryError('CANDIDATE_REVISION_TRANSITION_INVALID')
    state['epoch'] += 1
    return {'head_sha256': _head(state), 'current_revision': state['current_revision'],
            'selection_sha256': state['selection_sha256'], 'decision_sha256': decision_sha}


def _read(connection, run_id):
    states, registered, decisions = {}, {}, {}
    previous = '0' * 64
    for sequence, row in enumerate(connection.execute('SELECT * FROM source_processing_events '
            'WHERE processing_run_id=? ORDER BY sequence', (run_id,)), 1):
        body = json.loads(row['event_json'])
        require(row['sequence'] == sequence and row['previous_sha256'] == previous and
                row['event_sha256'] == digest({'processing_run_id': run_id, 'sequence': sequence,
                    'event_type': row['event_type'], 'event': body, 'previous_sha256': previous,
                    'created_at': row['created_at']}), 'CANDIDATE_LIFECYCLE_EVENT_CORRUPT')
        previous = row['event_sha256']
        if row['event_type'] not in (PROPOSAL, DECISION):
            continue
        require(body['version'] == VERSION, 'CANDIDATE_LIFECYCLE_VERSION_UNSUPPORTED')
        if row['event_type'] == PROPOSAL:
            for ref in body['references']:
                require(ref['run_id'] == run_id and reference_key(ref) == ref['logical_id'],
                        'CANDIDATE_LIFECYCLE_REGISTRY_CORRUPT')
                key = (ref['logical_id'], ref['revision_sha256'])
                require(key not in registered or registered[key] == ref, 'CANDIDATE_LIFECYCLE_REGISTRY_CORRUPT')
                registered[key] = ref
                state = states.setdefault(ref['logical_id'], {'logical_id': ref['logical_id'], 'epoch': 0,
                    'current_revision': None, 'selection_sha256': None, 'versions': {}})
                state['versions'].setdefault(ref['revision_sha256'], 'AVAILABLE')
        else:
            request = body['request']
            require(body['decision_sha256'] == digest({'version': VERSION, 'request': request}),
                    'CANDIDATE_LIFECYCLE_EVENT_CORRUPT')
            require(request['identity']['principal_type'] == 'HUMAN_USER'
                    and request['identity']['actor'] and request['identity']['session_id'], 'HUMAN_USER_REQUIRED')
            for ref in (request['reference'], request['replacement']):
                if ref is not None:
                    require(registered.get((ref['logical_id'],ref['revision_sha256'])) == ref,
                            'CANDIDATE_REVISION_UNREGISTERED')
            require(request['idempotency_key'] not in decisions, 'CANDIDATE_LIFECYCLE_EVENT_CORRUPT')
            result = _transition(states, request, body['decision_sha256'])
            require(result == body['result'], 'CANDIDATE_LIFECYCLE_EVENT_CORRUPT')
            decisions[request['idempotency_key']] = body
    return states, registered, decisions


def reference_key(ref):
    return digest({'version': VERSION, **{k:v for k,v in ref.items() if k not in ('logical_id','revision_sha256')}})


class RevisionLifecycle:
    def __init__(self, config):
        self.config, self.store = config, Store(config)

    def read(self, ref):
        with self.store.connect() as db:
            states, registered, _ = _read(db, ref['run_id'])
        require(registered.get((ref['logical_id'],ref['revision_sha256'])) == ref, 'CANDIDATE_REVISION_UNREGISTERED')
        state = states[ref['logical_id']]
        return {**state, 'head_sha256': _head(state)}

    def decide(self, action, ref, *, expected_head, identity: dict, reason, idempotency_key,
               replacement=None, confirm=False):
        require(set(identity) == {'actor','session_id','principal_type'}
                and identity['principal_type'] == 'HUMAN_USER' and confirm is True
                and all(type(v) is str and v.strip() for v in identity.values()), 'HUMAN_USER_REQUIRED')
        require(type(reason) is str and 0 < len(reason.strip()) <= 1000, 'CANDIDATE_REVISION_REASON_REQUIRED')
        require(type(idempotency_key) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._:-]{15,127}', idempotency_key),
                'INVALID_IDEMPOTENCY_KEY')
        require(action in ('SELECT','REPLACE','REVOKE'), 'CANDIDATE_REVISION_TRANSITION_INVALID')
        request = {'action':action, 'reference':ref, 'replacement':replacement, 'expected_head':expected_head,
                   'identity':dict(identity), 'reason':reason, 'idempotency_key':idempotency_key}
        with self.store.connect(operator_write=True) as db:
            db.execute('PRAGMA synchronous=FULL')
            try:
                db.execute('BEGIN IMMEDIATE')
            except sqlite3.OperationalError as exc:
                if getattr(exc, 'sqlite_errorcode', None) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                    raise BoundaryError('CANDIDATE_REVISION_CONCURRENT_WRITE') from exc
                raise
            states, registered, decisions = _read(db, ref['run_id'])
            prior = decisions.get(idempotency_key)
            if prior:
                require(prior['request'] == request, 'IDEMPOTENCY_CONFLICT')
                return prior
            for item in (ref,replacement):
                if item is not None:
                    require(registered.get((item['logical_id'],item['revision_sha256'])) == item,
                            'CANDIDATE_REVISION_UNREGISTERED')
            decision_sha = digest({'version':VERSION, 'request':request})
            result = _transition(states, request, decision_sha)
            body = {'version':VERSION, 'request':request, 'decision_sha256':decision_sha, 'result':result}
            from .source_operations import SourceOperations
            SourceOperations._event(db, ref['run_id'], DECISION, body)
        return body


def _required(documents, excluded=()):
    from pro_a.candidate_origin import semantic_projection
    analysis = semantic_projection(documents, excluded)
    selected = {o['observation_id'] for c in analysis.claims for o in c['candidate_observations']}
    result = {}
    for document in documents:
        objects = {o['observation_id']:o for o in document['objects'] if o['family'] == 'claims'}
        for oid in selected & objects.keys():
            obj = objects[oid]
            for item in ([objects[obj['parent']['observation_id']],obj] if obj.get('parent') else [obj]):
                ref = reference(document,item)
                result[(ref['logical_id'],ref['revision_sha256'])] = ref
    return [result[key] for key in sorted(result)]


def freeze(config, documents, excluded=(), *, connection=None):
    if connection is None:
        with Store(config).connect() as db:
            return freeze(config,documents,excluded,connection=db)
    bindings, runs = [], {}
    for ref in _required(documents, excluded):
        if ref['run_id'] not in runs:
            runs[ref['run_id']] = _read(connection, ref['run_id'])
        states, registered, _ = runs[ref['run_id']]
        require(registered.get((ref['logical_id'],ref['revision_sha256'])) == ref, 'CANDIDATE_REVISION_UNREGISTERED')
        state = states[ref['logical_id']]
        require(state['versions'][ref['revision_sha256']] == 'ACTIVE'
                and state['current_revision'] == ref['revision_sha256'], 'CANDIDATE_REVISION_NOT_CURRENT')
        bindings.append({'reference':ref, 'selection_sha256':state['selection_sha256']})
    return {'version':VERSION, 'bindings':bindings}


def require_documents(config, documents, binding, excluded=(), *, connection=None):
    require(binding is not None, 'CANDIDATE_LIFECYCLE_BINDING_REQUIRED')
    require(freeze(config,documents,excluded,connection=connection) == binding, 'CANDIDATE_REVISION_SELECTION_CHANGED')


def require_handle(config, handle, *, connection=None):
    if connection is None:
        with Store(config).connect() as db:
            return require_handle(config,handle,connection=db)
    row = connection.execute('SELECT run_relative,file_inventory FROM registered_packets WHERE artifact_id=?', (handle,)).fetchone()
    require(row is not None, 'ARTIFACT_NOT_FOUND')
    from .artifacts import Artifacts
    archive, inventory = Artifacts(config), json.loads(row['file_inventory'])
    def read(relative):
        content = archive.resolve(relative).read_bytes()
        require(hashlib.sha256(content).hexdigest() == inventory.get(relative), 'ARTIFACT_HASH_MISMATCH')
        return json.loads(content)
    manifest_path = row['run_relative']+'/run_manifest.json'
    if manifest_path not in inventory:
        return  # Legacy foundation packets have no Candidate Origin manifest.
    manifest = read(manifest_path)
    if (manifest.get('candidate_origin') or {}).get('version') != 'source-candidate-set-v2':
        return
    data = read(row['run_relative']+'/extraction/candidate_input.json')
    require_documents(config,data['documents'],data.get('lifecycle_binding'),data.get('excluded_keys',()),connection=connection)


@contextmanager
def execution_guard(config, envelope_id):
    # Same durable reservation as SELECT/REPLACE/REVOKE, held through Canonical
    # and Grant commit. Acquire state before Canonical to avoid reversed ordering.
    with Store(config).connect(operator_write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT artifact_id FROM operational_packages WHERE object_id=?', (envelope_id,)).fetchone()
        if row is not None:
            require_handle(config,row['artifact_id'],connection=db)
        yield
