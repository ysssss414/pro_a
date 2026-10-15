"""Frozen proposals and resumable human approval using existing Schema12 events."""
from collections import Counter
import json
import re

from pro_a.evidence_binding import identity as digest
from pro_a.phase3f_review_completion import validate_completed_review_packet
from .advisory_review import AdvisoryReview, validate_promotable
from .attribution import Attribution, validate_decision
from .config import BoundaryError
from .review import require_safe_projection
from .review_workbench import ReviewWorkbench, compose, validate_partial
from .source_operations import SourceOperations
from .review_policy import ReviewPolicy, slots


def require(condition, code):
    if not condition:
        raise BoundaryError(code)


class ReviewBatch:
    def __init__(self, config):
        self.config = config
        self.reviews = ReviewWorkbench(config)
        self.store = self.reviews.store

    def events(self, connection, handle, kind):
        run = connection.execute('SELECT processing_run_id FROM source_processing_runs WHERE packet_artifact_id=?', (handle,)).fetchone()
        require(run is not None, 'CANDIDATE_NATIVE_RUN_REQUIRED')
        return run[0], [json.loads(r[0]) for r in connection.execute(
            'SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=? ORDER BY event_id',
            (run[0], kind))]

    def record(self, connection, handle, kind, value):
        run, _ = self.events(connection, handle, kind)
        SourceOperations._event(connection, run, kind, value)

    def provenance(self, handle, opinions):
        with self.store.connect() as connection:
            _, records = self.events(connection, handle, 'MCP_ADVICE_CONTEXT')
        pair = {}
        for slot, opinion in opinions.items():
            matches = [v for v in records if v['slot'] == slot and v['opinion_sha256'] == opinion['sha256']]
            require(len(matches) == 1, 'REVIEW_EXECUTION_UNVERIFIED')
            pair[slot] = matches[0]
        policy = ReviewPolicy(self.reviews).read(handle)
        if len(slots(policy)) == 2:
            require(pair['A']['execution_id'] != pair['B']['execution_id'], 'INDEPENDENT_REVIEW_REQUIRED')
        return pair

    def snapshot(self, handle, kind):
        require(kind in ('native', 'attribution'), 'BATCH_KIND_INVALID')
        from pro_a.read_model.review_context import basis
        from pro_a.read_model.service import ReadService
        packet, run, dto, review_basis = self.reviews._context(handle)
        context, _, _ = basis(ReadService(self.config), handle, 'blind', None)
        opinions = AdvisoryReview(self.reviews).read(packet, handle=handle)
        provenance = self.provenance(handle, opinions)
        binding = {'artifact_id': handle, 'packet_id': packet['packet_id'],
                   'packet_sha256': packet['immutable_packet_sha256'],
                   'packet_file_sha256': dto['packet_file_sha256'],
                   'context_sha256': context.context_sha256, 'review_basis_id': review_basis,
                   'advice_sha256': {s: o['sha256'] for s, o in opinions.items()},
                   'review_executions': provenance}
        policy = ReviewPolicy(self.reviews).read(handle)
        if policy:
            binding['review_policy'] = policy
        if kind == 'native':
            state = self.reviews.read(handle)['review']
            return binding, state, packet, run, opinions
        attribution = Attribution(self.config)
        ctx = attribution.context(handle)
        state = attribution.read(handle)
        binding['attribution_binding'] = ctx['binding']
        return binding, state, ctx, run, opinions

    def validate_native(self, context, run, opinions, policy, items):
        rows = [r for group in ('claims', 'nodes', 'relations') for r in context[group]]
        indexed = {i['candidate_id']: i for i in items}
        require(len(indexed) == len(items) == len(rows) and set(indexed) == {r['candidate_id'] for r in rows}, 'BATCH_UNIVERSE_INVALID')
        for row in rows:
            item = indexed[row['candidate_id']]
            require(set(item) == {'candidate_id', 'content_sha256', 'decision', 'reason', 'target_node_id'}, 'BATCH_ITEM_INVALID')
            require(item['content_sha256'] == row['content_sha256'], 'CONTENT_DRIFT')
            require(row['candidate_type'] == 'NODE' or item['target_node_id'] == '', 'BATCH_ITEM_INVALID')
        items = [indexed[r['candidate_id']] for r in rows]
        states = {i['candidate_id']: {**i, 'reviewer': 'Pending human approval'} for i in items}
        validate_partial(context, states, 'Pending human approval')
        completed = compose(context, states, 'Pending human approval')
        validate_completed_review_packet(completed, run)
        validate_promotable(completed, opinions, policy)
        return items, completed

    def prepare(self, handle, kind, binding, expected_revision, items, reason):
        require(kind in ('native', 'attribution'), 'BATCH_KIND_INVALID')
        actual, state, context, run, opinions = self.snapshot(handle, kind)
        require(binding == actual, 'BATCH_BINDING_DRIFT')
        require(type(expected_revision) is int and expected_revision == state['revision'], 'REVISION_CONFLICT')
        require(state['status'] == 'DRAFT', 'ALREADY_SEALED')
        require(isinstance(reason, str) and reason.strip() == reason and reason, 'BATCH_REASON_REQUIRED')
        require(isinstance(items, list) and len(items) <= 100, 'BATCH_UNIVERSE_INVALID')
        require_safe_projection({'items': items, 'reason': reason})
        # Validate before recording any proposal. The same native validators run again on approval.
        if kind == 'native':
            items, _ = self.validate_native(context, run, opinions, actual.get('review_policy'), items)
        else:
            indexed = {i['claim_id']: i for i in items}
            require(len(indexed) == len(items) == len(context['claims']) and set(indexed) == set(context['claims']), 'BATCH_UNIVERSE_INVALID')
            for cid, item in indexed.items():
                require(set(item) == {'claim_id', 'content_sha256', 'outcome', 'scope', 'links', 'reason'}, 'BATCH_ITEM_INVALID')
                row = next(r for r in context['packet']['claims'] if r['candidate_id'] == cid)
                require(item['content_sha256'] == row['content_sha256'], 'CONTENT_DRIFT')
                validate_decision(cid, item, context['claims'], context['nodes'])
            items = [indexed[cid] for cid in sorted(indexed)]
        for item in items:
            require(isinstance(item['reason'], str) and item['reason'].strip() == item['reason'] and item['reason'], 'BATCH_REASON_REQUIRED')
        proposal = {'version': 'controlled-review-batch-v1', 'kind': kind, 'binding': binding,
                    'basis_id': state['basis_id'], 'expected_revision': expected_revision,
                    'items': items, 'reason': reason, 'seal': True}
        proposal_id = digest(proposal)
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            _, previous = self.events(connection, handle, 'MCP_BATCH_PREPARED')
            if not any(p['proposal_id'] == proposal_id for p in previous):
                self.record(connection, handle, 'MCP_BATCH_PREPARED', {'proposal_id': proposal_id, 'proposal': proposal})
        return self.read(handle, proposal_id)

    def read(self, handle, proposal_id):
        require(isinstance(proposal_id, str) and re.fullmatch('[0-9a-f]{64}', proposal_id), 'BATCH_ID_INVALID')
        with self.store.connect() as connection:
            _, values = self.events(connection, handle, 'MCP_BATCH_PREPARED')
            _, approvals = self.events(connection, handle, 'MCP_BATCH_APPROVED')
        matches = [v for v in values if v['proposal_id'] == proposal_id]
        require(len(matches) == 1, 'BATCH_NOT_FOUND')
        proposal = matches[0]['proposal']
        require(digest(proposal) == proposal_id and proposal['binding']['artifact_id'] == handle, 'BATCH_BINDING_DRIFT')
        counts = dict(Counter(i.get('decision', i.get('outcome')) for i in proposal['items']))
        approved = [v for v in approvals if v['proposal_id'] == proposal_id]
        require(len(approved) <= 1, 'RECOVERY_REQUIRED')
        return {'proposal_id': proposal_id, 'proposal': proposal, 'counts': counts,
                'approved': bool(approved), 'production_authorized': False}

    def operations(self, proposal, reviewer):
        pid = digest(proposal)
        common = {'basis_id': proposal['basis_id'], 'reviewer': reviewer}
        for n, item in enumerate([*proposal['items'], None]):
            request = {**common, 'operation_id': digest({'proposal': pid, 'step': n})[:32],
                       'expected_revision': proposal['expected_revision'] + n}
            if item is None:
                request.update(reason=proposal['reason'], confirm=True)
                action = 'seal' if proposal['kind'] == 'native' else 'SEAL'
            else:
                request.update({k: v for k, v in item.items() if k != 'content_sha256'})
                action = 'decision' if proposal['kind'] == 'native' else 'SAVE'
            yield action, request

    def approve(self, handle, proposal_id, identity, *, confirm):
        require(identity.get('principal_type') == 'HUMAN_USER' and confirm is True, 'HUMAN_USER_REQUIRED')
        proposal = self.read(handle, proposal_id)['proposal']
        binding, _, context, _, _ = self.snapshot(handle, proposal['kind'])
        require(binding == proposal['binding'], 'BATCH_BINDING_DRIFT')
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            from .unified_review import records
            require(not records(connection, handle, 'UNIFIED_REVIEW_APPROVED'), 'UNIFIED_APPROVAL_LOCKED')
            _, approvals = self.events(connection, handle, 'MCP_BATCH_APPROVED')
            _, prepared = self.events(connection, handle, 'MCP_BATCH_PREPARED')
            # Resolve legacy v1 approvals through their immutable proposals; no new schema.
            for approved in approvals:
                matches = [p['proposal'] for p in prepared if p['proposal_id'] == approved['proposal_id']]
                require(len(matches) == 1, 'RECOVERY_REQUIRED')
                other = matches[0]
                require(digest(other) == approved['proposal_id'] and other['binding']['artifact_id'] == handle, 'RECOVERY_REQUIRED')
                same_basis = all(other[k] == proposal[k] for k in ('kind', 'basis_id', 'expected_revision'))
                require(not same_basis or approved['proposal_id'] == proposal_id, 'BATCH_APPROVAL_CONFLICT')
            previous = [a for a in approvals if a['proposal_id'] == proposal_id]
            if previous:
                approval = previous[0]
                require(approval['actor'] == identity['actor'], 'APPROVAL_ACTOR_MISMATCH')
            else:
                # Refresh native DB state under this lock, without holding it for file reads.
                if proposal['kind'] == 'native':
                    draft, _, _ = self.reviews._state(connection, handle, proposal['basis_id'])
                    revision = draft['revision'] if draft else 0
                    reviewer = draft['reviewer'] if draft else ''
                    sealed = bool(draft and draft['status'] == 'SEALED')
                else:
                    events, _, reviewer, sidecar = Attribution(self.config).state(connection, handle, context)
                    revision, sealed = len(events), bool(sidecar)
                require(revision == proposal['expected_revision'] and not sealed, 'REVISION_CONFLICT')
                approval = {'proposal_id': proposal_id, 'actor': identity['actor'],
                            'session_id': identity['session_id'], 'reviewer': reviewer or identity['actor']}
                self.record(connection, handle, 'MCP_BATCH_APPROVED', approval)
        # Each step has its own durable native transaction. Exact retries replay operations.
        service = self.reviews if proposal['kind'] == 'native' else Attribution(self.config)
        audit_identity = {**approval, 'principal_type': 'HUMAN_USER'}
        result = None
        for action, request in self.operations(proposal, approval['reviewer']):
            binding, _, _, _, _ = self.snapshot(handle, proposal['kind'])
            require(binding == proposal['binding'], 'BATCH_BINDING_DRIFT')
            result = service.mutate(handle, action, request, audit_identity)
        return {'proposal_id': proposal_id, 'status': 'SEALED', 'result': result, 'production_authorized': False}
