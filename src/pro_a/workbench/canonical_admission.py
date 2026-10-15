"""Exact second-human authorization. This module cannot execute an Operator."""
from contextlib import closing
from datetime import datetime, timezone
import json

from pro_a.operational_contract import (CONTRACT_SHA, identity, predicted_diff, readonly,
                                       require, runtime_identity, sealed, verify)
from pro_a.operational_qualification import (package_projection, qualify, validate_package,
                                            registered_historical_read)
from pro_a.process_boundary import require_readonly_boundary
from pro_a.production_promotion import canonical_sha256
from .unified_review import UnifiedReview, records


PLAN = 'CANONICAL_ADMISSION_PREPARED'
APPROVAL = 'CANONICAL_ADMISSION_APPROVED'
STATUS = 'CANONICAL_ADMISSION_STATUS'


class CanonicalAdmission:
    def __init__(self, config):
        self.config = config
        self.unified = UnifiedReview(config)
        self.store, self.batch = self.unified.store, self.unified.batch

    def p1(self, handle):
        with self.store.connect() as db:
            approvals = records(db, handle, 'UNIFIED_REVIEW_APPROVED')
        require(len(approvals) == 1, 'P1_APPROVAL_REQUIRED')
        value = self.unified.read(handle, approvals[0]['proposal_id'])
        require(value['status'] == 'SEALED', 'P1_COMPLETION_REQUIRED')
        return value

    def envelope(self, handle):
        with self.store.connect() as db:
            row = db.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()
        require(row is not None, 'PACKAGE_NOT_REGISTERED')
        return json.loads(row[0])

    def prepare(self, handle):
        p1 = self.p1(handle)
        envelope = qualify(self.config, handle, p1['result']['attribution_id'])
        plan = self.build_plan(handle, p1, envelope)
        self.check(handle, plan, before_execution=True)
        with self.store.connect(operator_write=True) as db:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            prior = records(db, handle, PLAN)
            require(not prior or prior == [plan], 'ADMISSION_PLAN_CONFLICT')
            if not prior: self.batch.record(db, handle, PLAN, plan)
        return self.read(handle)

    def build_plan(self, handle, p1, envelope):
        """Reconstruct every displayed field from sealed authority, never a client plan."""
        info = self.config.knowledge_db.stat()
        diff = envelope['predicted_diff']
        counts = {}
        for row in diff['inserts']:
            counts[row['table']] = counts.get(row['table'], 0) + 1
        projection = package_projection(envelope)
        return sealed({'version': 'canonical-admission-v1', 'artifact_id': handle,
            'p1_proposal_id': p1['proposal_id'], 'p1_approval_sha256': canonical_sha256(p1['approval']),
            'p1_binding': p1['proposal']['binding'], 'p1_runtime_identity': p1['proposal']['runtime_identity'],
            'p1_completed_sha256': canonical_sha256(p1['result']), 'native_objects': p1['result']['native'],
            'attribution_id': p1['result']['attribution_id'], 'binding': envelope['binding'],
            'source_sha256': envelope['source_sha256'], 'runtime_identity': runtime_identity(),
            'contract_sha256': CONTRACT_SHA, 'target_file_id': [info.st_dev, info.st_ino],
            'baseline': envelope['baseline'], 'envelope_id': envelope['object_id'],
            'diff_id': diff['object_id'], 'pre_state_sha256': diff['pre_state_sha256'],
            'post_state_sha256': diff['post_state_sha256'], 'changes': projection['changes'],
            'insert_counts': counts, 'unchanged_count': len(diff['unchanged']),
            'native_items': p1['proposal']['native_items'], 'attribution_items': p1['proposal']['attribution_items'],
            'evidence': p1['proposal']['universe'],
            'excluded': [r for r in p1['proposal']['native_items'] if r['decision'] not in ('KEEP', 'CREATE', 'REUSE')],
            'authorization_scope': 'ONE_EXACT_ENVELOPE_INSERT_OR_NOOP',
            'governance': 'SOURCE_ASSERTION / UNVERIFIED / CLUE_ONLY; no Official Current View change'}, 'ADMISSION')
    def check(self, handle, plan, *, before_execution):
        verify(plan, 'ADMISSION')
        require(plan['artifact_id'] == handle and plan['runtime_identity'] == runtime_identity() and
                plan['contract_sha256'] == CONTRACT_SHA, 'ADMISSION_RUNTIME_MISMATCH')
        p1 = self.p1(handle)
        require(plan['p1_proposal_id'] == p1['proposal_id'] and
                plan['p1_approval_sha256'] == canonical_sha256(p1['approval']) and
                plan['p1_completed_sha256'] == canonical_sha256(p1['result']) and
                plan['native_objects'] == p1['result']['native'] and
                plan['attribution_id'] == p1['result']['attribution_id'], 'ADMISSION_P1_MISMATCH')
        envelope = self.envelope(handle)
        context, sidecar = self.unified.attribution.sealed_context(handle)
        validate_package(envelope, context, sidecar)
        info = self.config.knowledge_db.stat()
        require(plan['target_file_id'] == [info.st_dev, info.st_ino], 'TARGET_IDENTITY_MISMATCH')
        require(plan == self.build_plan(handle, p1, envelope), 'ADMISSION_BINDING_MISMATCH')
        if before_execution:
            require(identity(self.config.knowledge_db) == plan['baseline'], 'STALE_BASELINE')
            with closing(readonly(self.config.knowledge_db)) as db:
                require(predicted_diff(db, envelope['mutations']) == envelope['predicted_diff'], 'PREDICTED_DIFF_MISMATCH')
        return envelope

    def approved(self, handle, *, before_execution):
        with self.store.connect() as db:
            plans, approvals = records(db, handle, PLAN), records(db, handle, APPROVAL)
        require(len(plans) == len(approvals) == 1, 'P2_HUMAN_APPROVAL_REQUIRED')
        plan, approval = plans[0], approvals[0]
        verify(approval, 'PRODUCTION_APPROVAL')
        require(approval['plan_id'] == plan['object_id'] and approval['artifact_id'] == handle and
                approval['envelope_id'] == plan['envelope_id'] and approval['diff_id'] == plan['diff_id'] and
                approval['principal_type'] == 'HUMAN_USER' and bool(approval['actor']) and bool(approval['session_id']) and
                approval['boundary'] == {'scheme': 'WINDOWS_MANDATORY_INTEGRITY', 'web_integrity': 4096},
                'ADMISSION_APPROVAL_MISMATCH')
        envelope = self.check(handle, plan, before_execution=before_execution)
        return plan, approval, envelope

    def approve(self, handle, plan_id, identity, *, confirm):
        require(identity.get('principal_type') == 'HUMAN_USER' and identity.get('actor') and
                identity.get('session_id') and confirm is True, 'HUMAN_USER_REQUIRED')
        boundary = require_readonly_boundary(self.config)
        with self.store.connect() as db:
            plans, approvals = records(db, handle, PLAN), records(db, handle, APPROVAL)
        require(len(plans) == 1 and plans[0]['object_id'] == plan_id, 'ADMISSION_PLAN_MISMATCH')
        if approvals:
            require(len(approvals) == 1 and approvals[0]['actor'] == identity['actor'] and
                    approvals[0]['plan_id'] == plan_id, 'APPROVAL_ACTOR_MISMATCH')
            return self.read(handle)
        plan = plans[0]
        self.check(handle, plan, before_execution=True)
        approval = sealed({'plan_id': plan_id, 'artifact_id': handle, 'envelope_id': plan['envelope_id'],
            'diff_id': plan['diff_id'], 'principal_type': 'HUMAN_USER', 'actor': identity['actor'],
            'session_id': identity['session_id'], 'boundary': boundary,
            'timestamp': datetime.now(timezone.utc).isoformat()}, 'PRODUCTION_APPROVAL')
        with self.store.connect(operator_write=True) as db:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            prior = records(db, handle, APPROVAL)
            require(not prior or (len(prior) == 1 and prior[0]['plan_id'] == plan_id and
                    prior[0]['actor'] == identity['actor']), 'ADMISSION_APPROVAL_CONFLICT')
            if not prior: self.batch.record(db, handle, APPROVAL, approval)
        return self.read(handle)

    def read(self, handle):
        with self.store.connect() as db:
            plans, approvals = records(db, handle, PLAN), records(db, handle, APPROVAL)
            events = records(db, handle, STATUS)
        require(len(plans) <= 1 and len(approvals) <= 1, 'RECOVERY_REQUIRED')
        if not plans:
            p1 = self.p1(handle)
            return {'status': 'QUALIFICATION_REQUIRED', 'p1_proposal_id': p1['proposal_id'], 'plan': None}
        plan = plans[0]; verify(plan, 'ADMISSION')
        if approvals:
            verify(approvals[0], 'PRODUCTION_APPROVAL')
            require(approvals[0]['plan_id'] == plan['object_id'] and approvals[0]['artifact_id'] == handle and
                    approvals[0]['envelope_id'] == plan['envelope_id'] and approvals[0]['diff_id'] == plan['diff_id'],
                    'ADMISSION_APPROVAL_MISMATCH')
        result = {'status': 'AUTHORIZED_PENDING_OPERATOR' if approvals else 'AWAITING_SECOND_APPROVAL',
                  'plan': plan, 'approval': approvals[0] if approvals else None, 'execution': None}
        if events:
            event = events[-1]
            require(approvals and event['approval_id'] == approvals[0]['object_id'] and
                    event['plan_id'] == plan['object_id'], 'ADMISSION_STATUS_MISMATCH')
            result.update(status=event['status'], execution=event)
        history = registered_historical_read(self.config, handle)
        if history['receipt']:
            require(approvals and history['receipt']['envelope_id'] == plan['envelope_id'], 'RECEIPT_BINDING_MISMATCH')
            proof = history['qualification']['history_verification']
            result.update(status='RECONCILED' if proof['status'] == 'HISTORICAL_EXECUTION_CHAIN_VERIFIED' else proof['status'],
                          receipt=history['receipt'], history_verification=proof)
        return result


def require_p2_if_unified(config, handle, envelope_id):
    """Every privileged entry checks P2 for P1 materials, including legacy CLI."""
    service = CanonicalAdmission(config)
    with service.store.connect() as db:
        unified = records(db, handle, 'UNIFIED_REVIEW_APPROVED')
    if unified:
        _, _, envelope = service.approved(handle, before_execution=False)
        require(envelope['object_id'] == envelope_id, 'ADMISSION_ENVELOPE_MISMATCH')
