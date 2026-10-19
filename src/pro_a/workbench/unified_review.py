"""One frozen human approval, two native seals; Schema12 event coordination."""
import json
import re

from pro_a.evidence_binding import identity as digest
from pro_a.operational_contract import runtime_identity
from .attribution import Attribution, validate_decision
from .review import require_safe_projection
from .review_batch import ReviewBatch, require


def records(connection, handle, kind):
    # Legacy schemas have no source-processing events and retain their old flow.
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='source_processing_events'").fetchone():
        return []
    return [json.loads(r[0]) for r in connection.execute(
        'SELECT e.event_json FROM source_processing_events e JOIN source_processing_runs r '
        'ON e.processing_run_id=r.processing_run_id WHERE r.packet_artifact_id=? AND e.event_type=? ORDER BY e.event_id',
        (handle, kind))]


def operations(proposal, pid, kind, reviewer, basis_id):
    items = proposal['native_items' if kind == 'native' else 'attribution_items']
    revision = proposal['expected_revision'] if kind == 'native' else 0
    for n, item in enumerate([*items, None]):
        request = {'basis_id': basis_id, 'reviewer': reviewer,
                   'expected_revision': revision + n,
                   'operation_id': digest({'unified_proposal': pid, 'stage': kind, 'step': n})[:32]}
        if item is None:
            request.update(reason=proposal['reason'], confirm=True)
            action = 'seal' if kind == 'native' else 'SEAL'
        else:
            request.update({k: v for k, v in item.items() if k != 'content_sha256'})
            action = 'decision' if kind == 'native' else 'SAVE'
        yield action, request


def guard_operation(connection, handle, kind, action, request, identity):
    """Called inside BOTH legacy write transactions; no unapproved interleaving."""
    approvals = records(connection, handle, 'UNIFIED_REVIEW_APPROVED')
    if not approvals:
        require(not identity.get('unified_proposal_id'), 'UNIFIED_APPROVAL_REQUIRED')
        return
    require(len(approvals) == 1, 'RECOVERY_REQUIRED')
    approval = approvals[0]
    pid = approval['proposal_id']
    require(identity.get('unified_proposal_id') == pid and
            identity.get('actor') == approval['actor'] and
            identity.get('session_id') == approval['session_id'] and
            identity.get('principal_type') == 'HUMAN_USER', 'UNIFIED_APPROVAL_LOCKED')
    prepared = [p for p in records(connection, handle, 'UNIFIED_REVIEW_PREPARED') if p['proposal_id'] == pid]
    require(len(prepared) == 1 and digest(prepared[0]['proposal']) == pid, 'RECOVERY_REQUIRED')
    proposal = prepared[0]['proposal']
    require(proposal['runtime_identity'] == runtime_identity(), 'RUNTIME_IDENTITY_MISMATCH')
    expected = list(operations(proposal, pid, kind, approval['reviewer'], request['basis_id']))
    require((action, request) in expected, 'UNIFIED_OPERATION_MISMATCH')


class UnifiedReview:
    def __init__(self, config):
        self.config = config
        self.batch = ReviewBatch(config)
        self.reviews, self.store = self.batch.reviews, self.batch.store
        self.attribution = Attribution(config)

    def context(self, handle):
        binding, state, packet, run, opinions = self.batch.snapshot(handle, 'native')
        with self.store.connect() as connection:
            from pro_a.company_material_intent import read_bound
            run_id, _ = self.batch.events(connection, handle, 'UNIFIED_REVIEW_PREPARED')
            intent = read_bound(connection, run_id)
            prepared = records(connection, handle, 'UNIFIED_REVIEW_PREPARED')
            approved = records(connection, handle, 'UNIFIED_REVIEW_APPROVED')
        # No Attribution.context call here: draft proposals cannot masquerade as seals.
        return {'binding': binding, 'revision': state['revision'], 'basis_id': state['basis_id'],
                'status': state['status'], 'runtime_identity': runtime_identity(),
                'candidates': [r for g in ('claims', 'nodes', 'relations') for r in packet[g]],
                'advice': opinions, 'intent': intent,
                'draft_decisions': {r['candidate_id']: r.get('state') for r in state['rows']},
                'capabilities': {r['candidate_id']: {k: r[k] for k in ('available_decisions', 'blocked_decisions', 'reuse_target')} for r in state['rows']},
                'proposal_ids': [p['proposal_id'] for p in prepared],
                'approved_proposal_id': approved[0]['proposal_id'] if len(approved) == 1 else None,
                'production_authorized': False}

    def validate(self, handle, native_items):
        binding, state, packet, run, opinions = self.batch.snapshot(handle, 'native')
        require(isinstance(native_items, list) and len(native_items) <= 100, 'BATCH_UNIVERSE_INVALID')
        require_safe_projection(native_items)
        native_items, completed = self.batch.validate_native(packet, run, opinions, binding.get('review_policy'), native_items)
        with self.store.connect() as connection:
            from pro_a.company_material_intent import read_bound
            run_id, _ = self.batch.events(connection, handle, 'UNIFIED_REVIEW_PREPARED')
            intent = read_bound(connection, run_id)
        _, _, _, claims, nodes = self.attribution.universe(handle, completed, intent)
        for item in native_items:
            self.reason(item['reason'])
        universe = {'claims': claims, 'nodes': nodes}
        return binding, state, native_items, universe

    @staticmethod
    def reason(value):
        require(isinstance(value, str) and 0 < len(value) <= 8000 and value.strip() == value, 'BATCH_REASON_REQUIRED')

    def preview(self, handle, native_items):
        binding, state, native_items, universe = self.validate(handle, native_items)
        return {'binding': binding, 'revision': state['revision'], 'basis_id': state['basis_id'],
                'native_items': native_items, 'universe': universe,
                'universe_sha256': digest(universe), 'production_authorized': False}

    def prepare(self, handle, binding, expected_revision, native_items, attribution_items, reason):
        actual, state, native_items, universe = self.validate(handle, native_items)
        require(binding == actual, 'BATCH_BINDING_DRIFT')
        require(type(expected_revision) is int and expected_revision == state['revision'], 'REVISION_CONFLICT')
        require(state['status'] == 'DRAFT', 'ALREADY_SEALED')
        self.reason(reason)
        require(isinstance(attribution_items, list) and len(attribution_items) <= 100, 'BATCH_UNIVERSE_INVALID')
        require_safe_projection({'items': attribution_items, 'reason': reason})
        indexed = {i['claim_id']: i for i in attribution_items}
        require(len(indexed) == len(attribution_items) and set(indexed) == set(universe['claims']), 'BATCH_UNIVERSE_INVALID')
        hashes = {i['candidate_id']: i['content_sha256'] for i in native_items}
        for cid, item in indexed.items():
            require(set(item) == {'claim_id', 'content_sha256', 'outcome', 'scope', 'links', 'reason'}, 'BATCH_ITEM_INVALID')
            require(item['content_sha256'] == hashes[cid], 'CONTENT_DRIFT')
            self.reason(item['reason'])
            validate_decision(cid, item, universe['claims'], universe['nodes'])
        proposal = {'version': 'unified-human-review-v1', 'binding': actual, 'basis_id': state['basis_id'],
                    'expected_revision': expected_revision, 'runtime_identity': runtime_identity(),
                    'native_items': native_items, 'attribution_items': [indexed[cid] for cid in sorted(indexed)],
                    'universe': universe, 'universe_sha256': digest(universe), 'reason': reason,
                    'steps': ['NATIVE_DECISIONS', 'NATIVE_SEAL', 'ATTRIBUTION_DECISIONS', 'ATTRIBUTION_SEAL']}
        pid = digest(proposal)
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            from .candidate_lifecycle import require_handle
            require_handle(self.config, handle, connection=connection)
            require(not records(connection, handle, 'UNIFIED_REVIEW_APPROVED'), 'UNIFIED_APPROVAL_LOCKED')
            if not any(p['proposal_id'] == pid for p in records(connection, handle, 'UNIFIED_REVIEW_PREPARED')):
                self.batch.record(connection, handle, 'UNIFIED_REVIEW_PREPARED', {'proposal_id': pid, 'proposal': proposal})
        return self.read(handle, pid)

    def read(self, handle, pid):
        require(isinstance(pid, str) and re.fullmatch('[0-9a-f]{64}', pid), 'BATCH_ID_INVALID')
        with self.store.connect() as connection:
            prepared = [p for p in records(connection, handle, 'UNIFIED_REVIEW_PREPARED') if p['proposal_id'] == pid]
            approvals = [p for p in records(connection, handle, 'UNIFIED_REVIEW_APPROVED') if p['proposal_id'] == pid]
            completed = [p for p in records(connection, handle, 'UNIFIED_REVIEW_COMPLETED') if p['proposal_id'] == pid]
        require(len(prepared) == 1, 'BATCH_NOT_FOUND')
        proposal = prepared[0]['proposal']
        require(digest(proposal) == pid and proposal['binding']['artifact_id'] == handle, 'BATCH_BINDING_DRIFT')
        require(len(approvals) <= 1 and len(completed) <= 1, 'RECOVERY_REQUIRED')
        return {'proposal_id': pid, 'proposal': proposal, 'approved': bool(approvals),
                'approval': approvals[0] if approvals else None, 'status': 'SEALED' if completed else 'APPROVED' if approvals else 'PREPARED',
                'result': completed[0] if completed else None, 'production_authorized': False}

    def check(self, handle, proposal):
        actual, _, items, universe = self.validate(handle, proposal['native_items'])
        require(actual == proposal['binding'] and items == proposal['native_items'] and
                universe == proposal['universe'] and digest(universe) == proposal['universe_sha256'], 'BATCH_BINDING_DRIFT')
        require(runtime_identity() == proposal['runtime_identity'], 'RUNTIME_IDENTITY_MISMATCH')
        for item in proposal['attribution_items']:
            validate_decision(item['claim_id'], item, universe['claims'], universe['nodes'])

    def approve(self, handle, pid, identity, *, confirm, max_steps=None):
        require(identity.get('principal_type') == 'HUMAN_USER' and confirm is True and
                bool(identity.get('actor')) and bool(identity.get('session_id')), 'HUMAN_USER_REQUIRED')
        frozen = self.read(handle, pid)
        proposal = frozen['proposal']
        require(digest(proposal) == pid, 'BATCH_BINDING_DRIFT')
        self.check(handle, proposal)
        with self.store.connect(operator_write=True) as connection:
            connection.execute('PRAGMA synchronous=FULL'); connection.execute('BEGIN IMMEDIATE')
            from .candidate_lifecycle import require_handle
            require_handle(self.config, handle, connection=connection)
            approvals = records(connection, handle, 'UNIFIED_REVIEW_APPROVED')
            require(len(approvals) <= 1, 'RECOVERY_REQUIRED')
            if approvals:
                approval = approvals[0]
                require(approval['proposal_id'] == pid, 'BATCH_APPROVAL_CONFLICT')
                require(approval['actor'] == identity['actor'], 'APPROVAL_ACTOR_MISMATCH')
                if identity['session_id'] != approval['session_id']:
                    resumed = {'proposal_id': pid, 'actor': identity['actor'], 'session_id': identity['session_id'],
                               'original_approval_session_id': approval['session_id']}
                    if resumed not in records(connection, handle, 'UNIFIED_REVIEW_RESUMED'):
                        self.batch.record(connection, handle, 'UNIFIED_REVIEW_RESUMED', resumed)
            else:
                require(not records(connection, handle, 'MCP_BATCH_APPROVED'), 'BATCH_APPROVAL_CONFLICT')
                draft, _, _ = self.reviews._state(connection, handle, proposal['basis_id'])
                require((draft['revision'] if draft else 0) == proposal['expected_revision'] and
                        (not draft or draft['status'] == 'DRAFT'), 'REVISION_CONFLICT')
                require(not connection.execute('SELECT 1 FROM attribution_events WHERE artifact_id=?', (handle,)).fetchone(), 'ATTRIBUTION_STATE_CONFLICT')
                approval = {'proposal_id': pid, 'actor': identity['actor'], 'session_id': identity['session_id'],
                            'reviewer': draft['reviewer'] if draft else identity['actor']}
                self.batch.record(connection, handle, 'UNIFIED_REVIEW_APPROVED', approval)
        audit_identity = {**approval, 'principal_type': 'HUMAN_USER', 'unified_proposal_id': pid}
        applied = 0

        def execute_step(kind, service, action, request):
            nonlocal applied
            from pro_a.production_promotion import canonical_sha256
            table = 'review_operations' if kind == 'native' else 'attribution_events'
            with self.store.connect() as connection:
                previous = connection.execute('SELECT request_sha256 FROM ' + table +
                    ' WHERE artifact_id=? AND operation_id=?', (handle, request['operation_id'])).fetchone()
            if previous:
                require(previous[0] == canonical_sha256({'action': action, 'request': request, 'actor': approval['actor']}),
                        'IDEMPOTENCY_CONFLICT')
                return False
            self.check(handle, proposal)
            service.mutate(handle, action, request, audit_identity)
            applied += 1
            return max_steps is not None and applied >= max_steps

        def progress(kind, step, total):
            return {**self.read(handle, pid), 'progress': {'stage': kind, 'completed_steps': step, 'total_steps': total}}

        for n, (action, request) in enumerate(operations(proposal, pid, 'native', approval['reviewer'], proposal['basis_id'])):
            if execute_step('native', self.reviews, action, request):
                return progress('native', n + 1, len(proposal['native_items']) + 1)
        # Only now may the original sealed-only context be used. Exact targets must match preview.
        ctx = self.attribution.context(handle)
        require({'claims': ctx['claims'], 'nodes': ctx['nodes']} == proposal['universe'], 'ATTRIBUTION_UNIVERSE_DRIFT')
        for n, (action, request) in enumerate(operations(proposal, pid, 'attribution', approval['reviewer'], ctx['basis_id'])):
            if execute_step('attribution', self.attribution, action, request):
                return progress('attribution', n + 1, len(proposal['attribution_items']) + 1)
        _, sidecar = self.attribution.sealed_context(handle)
        result = {'proposal_id': pid, 'native': self.reviews.sealed_result(handle)['objects'],
                  'attribution_id': sidecar['object_id'], 'attribution_sha256': sidecar['sha256'], 'production_authorized': False}
        with self.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            from .candidate_lifecycle import require_handle
            require_handle(self.config, handle, connection=connection)
            completed = records(connection, handle, 'UNIFIED_REVIEW_COMPLETED')
            require(not completed or completed == [result], 'RECOVERY_REQUIRED')
            if not completed:
                self.batch.record(connection, handle, 'UNIFIED_REVIEW_COMPLETED', result)
        return self.read(handle, pid)
