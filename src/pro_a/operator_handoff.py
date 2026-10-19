"""Independent, non-networked P2 worker. Never loaded by Web or MCP."""
import argparse
from contextlib import closing, contextmanager
import json
from pathlib import Path
import time

from .operational_contract import WEB_REQUEST, require
from .operational_operator import Operator, OperatorConfig, _execution_lock
from .process_boundary import integrity_level
from .workbench.canonical_admission import CanonicalAdmission, APPROVAL, STATUS
from .workbench.config import BoundaryError
from .workbench.review_workbench import encode
from .workbench.unified_review import records


@contextmanager
def handoff_lock(path):
    # msvcrt.LK_LOCK waits only ten seconds. A complete qualification may take
    # longer; contention must not look like an ambiguous Canonical commit.
    for attempt in range(6):
        lock = _execution_lock(path)
        try:
            lock.__enter__()
            break
        except OSError:
            if attempt == 5: raise
            time.sleep(.1)
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


class OperatorHandoff:
    def __init__(self, config):
        require(not WEB_REQUEST.get(), 'WEB_APPLY_FORBIDDEN')
        self.operator = Operator(config)
        self.admission = CanonicalAdmission(config.workbench)

    def pending(self):
        with self.admission.store.connect() as db:
            return [r[0] for r in db.execute('SELECT DISTINCT r.packet_artifact_id FROM source_processing_events e '
                'JOIN source_processing_runs r ON r.processing_run_id=e.processing_run_id '
                'LEFT JOIN operational_receipts receipt ON receipt.artifact_id=r.packet_artifact_id '
                'WHERE e.event_type=? AND receipt.object_id IS NULL', (APPROVAL,))]

    def record(self, handle, plan, approval, status, **extra):
        event = {'plan_id': plan['object_id'], 'approval_id': approval['object_id'], 'status': status, **extra}
        with self.admission.store.connect(operator_write=True) as db:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            prior = records(db, handle, STATUS)
            if not prior or prior[-1] != event:
                self.admission.batch.record(db, handle, STATUS, event)
        return event

    def run(self, handle, *, fault=None):
        require(not WEB_REQUEST.get() and integrity_level() >= 8192, 'INDEPENDENT_OPERATOR_REQUIRED')
        config = self.operator.config
        # Separate queue lock spans register/execute/reconcile and all workers.
        with handoff_lock(config.ledger.with_name(config.ledger.name + '.handoff')):
            historical = self.admission.read(handle)
            if historical.get('receipt'):
                # Completed history is read under its original runtime. It is
                # never requalified or converted into fresh execution authority.
                return historical
            plan, approval = historical.get('plan'), historical.get('approval')
            require(plan and approval, 'P2_HUMAN_APPROVAL_REQUIRED')
            try:
                plan, approval, envelope = self.admission.approved(handle, before_execution=False)
                eid = envelope['object_id']
                with closing(self.operator.connect()) as db:
                    grants = [dict(r) for r in db.execute('SELECT * FROM grants')]
                with self.admission.store.connect() as db:
                    reconciled = {r[0] for r in db.execute('SELECT object_id FROM operational_receipts')}
                for grant in grants:
                    if grant['envelope_id'] != eid:
                        require(grant['status'] == 'CONSUMED' and grant['receipt'] and
                                json.loads(grant['receipt'])['object_id'] in reconciled, 'OTHER_EXECUTION_RECOVERY_REQUIRED')
                grant = next((g for g in grants if g['envelope_id'] == eid), None)
                if grant and grant['status'] == 'CONSUMED':
                    receipt = json.loads(grant['receipt'])
                    if receipt['object_id'] in reconciled:
                        result = self.admission.read(handle)
                        require(result['status'] == 'RECONCILED', 'RECOVERY_REQUIRED')
                        return result
                    self.record(handle, plan, approval, 'COMMITTED', grant_status='CONSUMED', receipt_id=receipt['object_id'])
                else:
                    self.admission.check(handle, plan, before_execution=True)
                    self.record(handle, plan, approval, 'RUNNING', grant_status=grant['status'] if grant else 'NOT_REGISTERED')
                    self.operator.register(eid, confirm=eid)
                    if fault: fault('registered', None)
                    # READY on a restart means no committed transaction. Existing
                    # Operator journal checks and baseline checks still apply.
                    receipt = self.operator.execute(eid, confirm=eid, fault=fault)
                    self.record(handle, plan, approval, 'COMMITTED', grant_status='CONSUMED', receipt_id=receipt['object_id'])
                if fault: fault('before_reconcile', None)
                receipt = self.operator.reconcile(eid)
                self.record(handle, plan, approval, 'RECONCILED', grant_status='CONSUMED', receipt_id=receipt['object_id'],
                            post_state_sha256=receipt['post_state_sha256'], actual_mutation_counts=receipt['actual_mutation_counts'],
                            source_materialization_verified=True, canonical_queryable=True)
                return self.admission.read(handle)
            except Exception as error:
                code = str(error) if isinstance(error, BoundaryError) else 'HANDOFF_INTERRUPTED'
                # Do not infer rollback from a timeout/exception. The next worker
                # reads the durable grant before deciding which technical step remains.
                status = 'BLOCKED' if code.startswith(('CANDIDATE_REVISION_', 'CANDIDATE_LIFECYCLE_')) or code in ('STALE_BASELINE', 'TARGET_IDENTITY_MISMATCH', 'OTHER_EXECUTION_RECOVERY_REQUIRED',
                    'ADMISSION_RUNTIME_MISMATCH', 'ADMISSION_BINDING_MISMATCH', 'RUNTIME_IDENTITY_MISMATCH',
                    'ADMISSION_APPROVAL_MISMATCH', 'ADMISSION_P1_MISMATCH') else 'RECOVERY_REQUIRED'
                self.record(handle, plan, approval, status, error_code=code)
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    worker = OperatorHandoff(OperatorConfig.load(args.config))
    require(integrity_level() >= 8192, 'INDEPENDENT_OPERATOR_REQUIRED')
    while True:
        for handle in worker.pending():
            try:
                value = worker.run(handle)
                print(encode({'artifact_id': handle, 'status': value['status']}), flush=True)
            except Exception as error:
                print(encode({'artifact_id': handle, 'status': 'RECOVERY_REQUIRED',
                              'error_code': str(error) if isinstance(error, BoundaryError) else 'HANDOFF_INTERRUPTED'}), flush=True)
        if not args.watch: break
        time.sleep(5)


if __name__ == '__main__':
    main()
