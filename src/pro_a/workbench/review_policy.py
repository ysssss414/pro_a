"""Human-selected, append-only policy; absent policy retains legacy dual review."""
import json

from pro_a.evidence_binding import identity as digest
from .config import BoundaryError

VERSION = 'source-support-review-policy-v1'
MODES = ('SINGLE_MODEL_HUMAN', 'DUAL_MODEL_HUMAN')
EVENT = 'REVIEW_POLICY_SELECTED'


def require(value, code='REVIEW_POLICY_INVALID'):
    if not value:
        raise BoundaryError(code)


def slots(policy):
    return ('A',) if policy and policy['mode'] == MODES[0] else ('A', 'B')


class ReviewPolicy:
    def __init__(self, reviews):
        self.reviews = reviews

    def read(self, handle, *, connection=None):
        if connection is None:
            with self.reviews.store.connect() as db:
                return self.read(handle, connection=db)
        rows = connection.execute('''SELECT e.event_json FROM source_processing_events e
            JOIN source_processing_runs r ON r.processing_run_id=e.processing_run_id
            WHERE r.packet_artifact_id=? AND e.event_type=?''', (handle, EVENT)).fetchall()
        if not rows:
            return None
        require(len(rows) == 1)
        policy = json.loads(rows[0][0])
        require(set(policy) == {'version', 'mode', 'binding', 'selected_by', 'sha256'})
        require(policy['sha256'] == digest({k: v for k, v in policy.items() if k != 'sha256'}))
        require(policy['version'] == VERSION and policy['mode'] in MODES)
        require(set(policy['selected_by']) == {'actor', 'session_id', 'principal_type'})
        require(policy['selected_by']['principal_type'] == 'HUMAN_USER'
                and all(policy['selected_by'].values()))
        packet, _, dto, basis = self.reviews._context(handle)
        binding = policy['binding']
        require(set(binding) == {'artifact_id', 'packet_sha256', 'packet_file_sha256',
                                'review_basis_id', 'context_sha256'})
        require(binding == {**binding, 'artifact_id': handle,
                            'packet_sha256': packet['immutable_packet_sha256'],
                            'packet_file_sha256': dto['packet_file_sha256'], 'review_basis_id': basis},
                'REVIEW_POLICY_BINDING_DRIFT')
        return policy

    def context(self, handle):
        from pro_a.read_model.review_context import basis
        from pro_a.read_model.service import ReadService
        packet, _, dto, review_basis = self.reviews._context(handle)
        context, _, _ = basis(ReadService(self.reviews.config), handle, 'blind', None)
        return {'artifact_id': handle, 'packet_sha256': packet['immutable_packet_sha256'],
                'packet_file_sha256': dto['packet_file_sha256'], 'review_basis_id': review_basis,
                'context_sha256': context.context_sha256}

    def select(self, handle, mode, binding, identity, *, confirm):
        from .advisory_review import AdvisoryReview, required
        from .source_operations import SourceOperations
        require(identity.get('principal_type') == 'HUMAN_USER' and confirm is True, 'HUMAN_USER_REQUIRED')
        require(mode in MODES)
        require(binding == self.context(handle), 'REVIEW_POLICY_BINDING_DRIFT')
        packet = self.reviews._context(handle)[0]
        require(required(packet), 'CANDIDATE_REVIEW_REQUIRED')
        with self.reviews.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            from .candidate_lifecycle import require_handle
            require_handle(self.reviews.config, handle, connection=connection)
            require(connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == '12',
                    'WORKBENCH_SCHEMA_REQUIRED')
            previous = self.read(handle, connection=connection)
            if previous:
                require(previous['mode'] == mode and previous['binding'] == binding, 'REVIEW_POLICY_IMMUTABLE')
                return previous
            draft, _, _ = self.reviews._state(connection, handle, binding['review_basis_id'])
            require(not draft or (draft['status'] == 'DRAFT' and draft['revision'] == 0), 'REVIEW_POLICY_TOO_LATE')
            run = connection.execute('SELECT processing_run_id FROM source_processing_runs WHERE packet_artifact_id=?', (handle,)).fetchone()
            require(run is not None, 'CANDIDATE_NATIVE_RUN_REQUIRED')
            started = connection.execute('''SELECT 1 FROM source_processing_events WHERE processing_run_id=?
                AND event_type IN ('CANDIDATE_ADVICE_SUBMITTED', 'MCP_ADVICE_CONTEXT', 'MCP_BATCH_PREPARED', 'MCP_BATCH_APPROVED')''', (run[0],)).fetchone()
            require(not started and not any(AdvisoryReview(self.reviews)._path(packet, s).exists() for s in ('A', 'B')),
                    'REVIEW_POLICY_TOO_LATE')
            require(binding == self.context(handle), 'REVIEW_POLICY_BINDING_DRIFT')
            policy = {'version': VERSION, 'mode': mode, 'binding': binding,
                      'selected_by': {k: identity[k] for k in ('actor', 'session_id', 'principal_type')}}
            policy['sha256'] = digest(policy)
            SourceOperations._event(connection, run[0], EVENT, policy)
        return policy
