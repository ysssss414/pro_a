"""Separate explicit human attribution over an immutable Stage 1 review."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from pro_a.claim_attribution_semantics import ROLE_SEMANTICS, validate_claim_node_role
from pro_a.operational_contract import require, runtime_identity, sealed, verify
from pro_a.production_promotion import canonical_sha256
from .config import checked_path
from .review import require_safe_projection
from .review_store import schema_version
from .review_workbench import ReviewError, ReviewWorkbench, encode
from .store import Store


def validate_decision(claim_id, decision, claims, nodes):
    require(claim_id in claims, 'NOT_REVIEWABLE')
    outcome, links = decision.get('outcome'), decision.get('links')
    require(outcome in ('LINK', 'MULTI_LINK', 'NO_LINK', 'DEFER') and isinstance(links, list), 'ATTRIBUTION_OUTCOME_INVALID')
    require((outcome == 'LINK' and len(links) == 1) or (outcome == 'MULTI_LINK' and len(links) >= 2) or
            (outcome in ('NO_LINK', 'DEFER') and not links), 'ATTRIBUTION_LINK_COUNT_INVALID')
    require(len({link.get('node_id') for link in links}) == len(links), 'DUPLICATE_ATTRIBUTION')
    require(decision.get('scope') == claims[claim_id]['scope'], 'ATTRIBUTION_SCOPE_MISMATCH')
    for link in links:
        require(set(link) == {'node_id', 'role'} and link['node_id'] in nodes, 'ATTRIBUTION_NODE_INVALID')
        require(link['role'] in ROLE_SEMANTICS, 'ATTRIBUTION_ROLE_INVALID')
        validate_claim_node_role(link['role'])


class Attribution:
    def __init__(self, config):
        self.config, self.store, self.reviews = config, Store(config), ReviewWorkbench(config)

    def context(self, handle):
        review = self.reviews.read(handle)
        require(review.get('review', {}).get('status') == 'SEALED', 'NATIVE_REVIEW_NOT_SEALED')
        with self.store.connect() as connection:
            require(schema_version(connection) in ('3', '4', '5', '6'), 'ATTRIBUTION_SCHEMA_REQUIRED')
            packet = json.loads(connection.execute("SELECT body FROM sealed_review_artifacts WHERE artifact_id=? AND kind='completed_packet'", (handle,)).fetchone()[0])
        blank, run, _ = self.reviews.artifacts.native(handle)
        bundle = json.loads(checked_path(run / 'evidence/evidence_bound_extraction_bundle.json').read_text(encoding='utf-8'))
        bundle_claims = {c['claim_id']: c for c in bundle['claims']}
        claims = {c['candidate_id']: {'candidate_id': c['candidate_id'], 'content': c['content'],
                  'scope': bundle_claims[c['candidate_id']].get('scope', '')} for c in packet['claims'] if c['human_input']['decision'] == 'KEEP'}
        nodes = {}
        for row in packet['nodes']:
            human, content = row['human_input'], row['content']
            if human['decision'] not in ('CREATE', 'REUSE'): continue
            node_id = content['prospective_node_id'] if human['decision'] == 'CREATE' else human['target_node_id']
            require(node_id not in nodes, 'AMBIGUOUS_NODE_IDENTITY')
            nodes[node_id] = {'node_id': node_id, 'candidate_id': row['candidate_id'], 'decision': human['decision'], 'content': content}
        binding = {'artifact_id': handle, 'packet_id': packet['packet_id'], 'review_id': review['review']['review_id'],
                   'sealed_objects': review['review']['sealed']['objects'], 'source': review['source'],
                   'claims': sorted(claims), 'nodes': sorted(nodes), 'schema_version': packet['production_baseline']['schema_version'],
                   'runtime_identity': runtime_identity()}
        return {'binding': binding, 'basis_id': canonical_sha256(binding), 'packet': packet, 'blank': blank, 'run': run,
                'bundle': bundle, 'claims': claims, 'nodes': nodes, 'review': review}

    def state(self, connection, handle, context):
        events, states, reviewer = [], {}, ''
        for row in connection.execute('SELECT * FROM attribution_events WHERE artifact_id=? ORDER BY revision', (handle,)):
            event = json.loads(row['event_json'])
            require(event['revision'] == len(events) + 1 == row['revision'] and event['basis_id'] == context['basis_id'], 'RECOVERY_REQUIRED')
            require(not reviewer or reviewer == event['reviewer'], 'RECOVERY_REQUIRED')
            reviewer = event['reviewer']
            if event['kind'] == 'SAVE':
                claim = event['claim_id']
                require(event['old'] == states.get(claim), 'RECOVERY_REQUIRED')
                validate_decision(claim, event['new'], context['claims'], context['nodes'])
                states[claim] = event['new']
            else:
                require(event['kind'] == 'SEAL', 'RECOVERY_REQUIRED')
            events.append(event)
        stored = connection.execute('SELECT * FROM attribution_objects WHERE artifact_id=?', (handle,)).fetchone()
        sidecar = json.loads(stored['body']) if stored else None
        require(bool(sidecar) == bool(events and events[-1]['kind'] == 'SEAL'), 'RECOVERY_REQUIRED')
        if sidecar:
            verify(sidecar, 'ATTRIBUTION')
            require(sidecar['binding'] == context['binding'] and sidecar['decisions'] == states and sidecar['revision'] == len(events)
                    and sidecar['object_id'] == stored['object_id'] and set(states) == set(context['claims']), 'ATTRIBUTION_BASIS_MISMATCH')
        return events, states, reviewer, sidecar

    def read(self, handle):
        context = self.context(handle)
        with self.store.connect() as connection:
            connection.execute('BEGIN')
            events, states, reviewer, sidecar = self.state(connection, handle, context)
            package = connection.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()
            receipt = connection.execute('SELECT body FROM operational_receipts WHERE artifact_id=?', (handle,)).fetchone()
        from pro_a.operational_qualification import package_projection
        if receipt:
            from pro_a.operational_qualification import reconcile_registered
            reconcile_registered(self.config, handle, json.loads(receipt[0])['object_id'])
        result = {'basis_id': context['basis_id'], 'binding': context['binding'], 'revision': len(events), 'reviewer': reviewer,
                  'status': 'SEALED' if sidecar else 'DRAFT', 'claims': list(context['claims'].values()), 'nodes': list(context['nodes'].values()),
                  'decisions': states, 'audit': events, 'roles': ROLE_SEMANTICS, 'required': len(context['claims']), 'completed': len(states),
                  'sidecar': sidecar, 'qualification': package_projection(json.loads(package[0])) if package else None,
                  'receipt': json.loads(receipt[0]) if receipt else None, 'production_authorized': False}
        require_safe_projection(result)
        return result

    def mutate(self, handle, action, request, identity):
        context = self.context(handle)
        require(request['basis_id'] == context['basis_id'], 'ATTRIBUTION_BASIS_MISMATCH')
        for key in ('reviewer', 'reason'):
            require(bool(request.get(key)) and request[key] == request[key].strip(), 'VALIDATION_ERROR')
        require_safe_projection(request)
        fingerprint = canonical_sha256({'action': action, 'request': request, 'actor': identity['actor']})
        with self.store.connect(operator_write=True) as connection:
            connection.execute('PRAGMA synchronous=FULL'); connection.execute('BEGIN IMMEDIATE')
            events, states, reviewer, sidecar = self.state(connection, handle, context)
            previous = connection.execute('SELECT * FROM attribution_events WHERE artifact_id=? AND operation_id=?', (handle, request['operation_id'])).fetchone()
            if previous:
                require(previous['request_sha256'] == fingerprint, 'IDEMPOTENCY_CONFLICT')
                return json.loads(previous['response_json'])
            require(not sidecar, 'ALREADY_SEALED')
            if request['expected_revision'] != len(events): raise ReviewError('REVISION_CONFLICT', current_revision=len(events))
            require(not reviewer or reviewer == request['reviewer'], 'REVIEWER_MISMATCH')
            event = {'kind': action, 'basis_id': context['basis_id'], 'revision': len(events) + 1, 'reviewer': request['reviewer'],
                     'reason': request['reason'], 'actor': identity['actor'], 'session_id': identity['session_id'],
                     'timestamp': datetime.now(timezone.utc).isoformat(), 'operation_id': request['operation_id']}
            if action == 'SAVE':
                claim = request['claim_id']
                decision = {k: request[k] for k in ('outcome', 'links', 'scope', 'reason', 'reviewer')}
                validate_decision(claim, decision, context['claims'], context['nodes'])
                event.update(claim_id=claim, old=states.get(claim), new=decision)
            elif action == 'SEAL':
                require(request.get('confirm') is True and set(states) == set(context['claims']), 'ATTRIBUTION_INCOMPLETE')
                sidecar = sealed({'document_type': 'phase42_explicit_claim_node_attribution', 'version': '1', 'binding': context['binding'],
                                  'revision': event['revision'], 'decisions': states, 'reviewer': request['reviewer'], 'timestamp': event['timestamp'],
                                  'seal_reason': request['reason'], 'production_authorized': False}, 'ATTRIBUTION')
                connection.execute('INSERT INTO attribution_objects VALUES(?,?,?)', (handle, sidecar['object_id'], encode(sidecar)))
            else: require(False, 'ATTRIBUTION_ACTION_INVALID')
            response = {'revision': event['revision'], 'sidecar_id': sidecar['object_id'] if sidecar else None}
            self.reviews.artifacts.read(handle)
            connection.execute('INSERT INTO attribution_events VALUES(?,?,?,?,?,?)',
                               (handle, event['revision'], request['operation_id'], fingerprint, encode(event), encode(response)))
        return response

    def sealed_context(self, handle):
        context = self.context(handle)
        with self.store.connect() as connection:
            _, _, _, sidecar = self.state(connection, handle, context)
        require(sidecar is not None, 'ATTRIBUTION_NOT_SEALED')
        return context, sidecar
