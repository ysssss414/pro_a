"""Explicit schema12 bounded-only operator boundary over the existing runner."""
from datetime import datetime, timedelta, timezone
import json
import re

from pro_a.cloud_contract import digest
from pro_a.config import load_config
from pro_a.phase4_orchestration import _compatible
from pro_a.phase4_retry import RetryPolicy
from . import bounded_extraction_persistence as persistence
from .config import BoundaryError
from .domains import Domains
from .extraction_retry import bounded_frozen_components, frozen_bounded_service, _bounded_retry_events
from .review_store import schema_version
from .source_operations import SourceOperationError, SourceOperations
from .stage1_scale import stage1_capacity

CONTRACT_VERSION = 'bounded-only-resume-operator-boundary-v1'
COMPLETE = 'BOUNDED_EXTRACTION_COMPLETE'
AUTHORIZED = 'BOUNDED_ONLY_RESUME_AUTHORIZED'
FINISHED = 'BOUNDED_ONLY_RESUME_FINISHED'


def contract():
    return {'version':CONTRACT_VERSION, 'plan_source':'DURABLE_FROZEN_PLAN_ONLY',
            'execution_scope':'PENDING_SEGMENTS_ONLY', 'replan_allowed':False,
            'automatic_retry':False, 'new_subdivision_allowed':False,
            'failure_policy':'STOP_ON_FIRST_NEW_FAILURE',
            'completion_boundary':'STOP_AFTER_BOUNDED_EXTRACTION',
            'semantic_registration_allowed':False, 'semantic_execution_allowed':False}


def assess_bounded_resume_compatibility(config, run_id, *, persist=False):
    """Reuse Stage7.2C for the exact historical failed -> accepted retry lineage."""
    from .retry_compatibility import assess_bounded_retry_compatibility
    from .store import Store
    with Store(config).connect() as c:
        retries = list(_bounded_retry_events(c,run_id=run_id))
    if not retries:
        raise SourceOperationError('BOUNDED_RESUME_LINEAGE_REQUIRED')
    return assess_bounded_retry_compatibility(
        config,run_id,retries[-1]['retry_of_attempt_id'],persist=persist,bounded_only_resume=True,
    )


def _worker(service, run_id):
    with service.store.connect() as c:
        row = c.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?',(run_id,)).fetchone()
        profile, cloud, _, _ = bounded_frozen_components(service.config,c,row)
        worker = SourceOperations(service.config,profile,cloud,
                                  runtime_compatibility=service.runtime_compatibility)
        if row['runtime_sha256'] != worker.jobs.current_runtime()['runtime_sha256'] and worker.runtime_compatibility is None:
            retries = list(_bounded_retry_events(c,run_id=run_id))
            from .strict_recovery import authorizations
            strict = authorizations(c, run_id)
            if strict:
                attempt_id = strict[-1]['failed_attempt_id']
            elif not retries:
                recoveries = list(c.execute("SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type='TRUNCATED_PARENT_SUBDIVIDED' ORDER BY sequence", (run_id,)))
                if not recoveries:
                    raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE')
                attempt_id = json.loads(recoveries[-1][0])['attempt_id']
            else:
                attempt_id = retries[-1]['retry_of_attempt_id']
            worker = frozen_bounded_service(service,run_id,attempt_id)
        Domains(service.config).guard(run_id,worker.jobs,worker.profile,
                                      runtime_compatibility=worker.runtime_compatibility)
        _compatible(worker._native_root(row),row['native_execution_id'],
                    load_config(worker.profile.phase4_config_path),RetryPolicy.FORBID_ALL,
                    runtime_compatibility=worker.runtime_compatibility)
    return worker


def _frontier(worker, run):
    bindings = worker.output_batches.inputs(run)
    pending, recoverable, snapshots, budgets = [], [], [], []
    calls = 0
    with worker.store.connect() as c:
        if c.execute("SELECT 1 FROM source_processing_jobs WHERE processing_run_id=? AND operation_kind='SEMANTIC_DECOMPOSITION'",(run['processing_run_id'],)).fetchone():
            raise SourceOperationError('BOUNDED_RESUME_SEMANTIC_ALREADY_REGISTERED')
        for _, _, _, bound in bindings:
            series, plan, state, _ = worker.output_batches.ledger.read(bound.series_id)
            if state['state'] not in ('OPEN','SUCCEEDED_COMPLETE'):
                raise SourceOperationError('BOUNDED_FRONTIER_NOT_EXECUTABLE')
            snapshots.append({'series':series.series_sha256,'segments':[s.segment_sha256 for s in plan.segments],
                              'superseded':plan.superseded_segment_ids})
            new_reservations = new_liability = 0
            for segment in sorted(plan.leaves,key=lambda s:(s.range_start,s.stable_path)):
                row = c.execute('SELECT state FROM bounded_extraction_segments WHERE segment_id=?',(segment.segment_id,)).fetchone()
                if row['state'] == 'SUCCEEDED_COMPLETE':
                    continue
                if row['state'] not in ('PLANNED','RUNNING','RECOVERY_REQUIRED'):
                    raise SourceOperationError('BOUNDED_FRONTIER_NOT_EXECUTABLE')
                attempt = c.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number DESC LIMIT 1',(segment.segment_id,)).fetchone()
                dispatched = attempt and c.execute('SELECT 1 FROM bounded_extraction_dispatches WHERE attempt_id=?',(attempt['attempt_id'],)).fetchone()
                pending.append(segment.segment_id)
                if dispatched:
                    recoverable.append(segment.segment_id)
                elif attempt is None:
                    new_reservations += 1
                    new_liability += segment.max_output_tokens
            budgets.append(state['provider_call_reservations']+new_reservations <= series.budget.max_provider_calls
                           and state['output_liability']+new_liability <= series.budget.max_cumulative_output_tokens)
            calls += c.execute('SELECT count(*) FROM bounded_extraction_dispatches d JOIN bounded_extraction_attempts a USING(attempt_id) JOIN bounded_extraction_segments s USING(segment_id) WHERE s.series_id=?',(series.series_id,)).fetchone()[0]
    return {'identity':digest(snapshots),'pending':pending,'recoverable':recoverable,'calls':calls,
            'within_budget':all(budgets),'complete':all(worker.output_batches.ledger.read(b[3].series_id)[2]['state']=='SUCCEEDED_COMPLETE' for b in bindings)}


def _events(connection, run_id, event_type, key):
    return [json.loads(r[0]) for r in connection.execute(
        'SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=? ORDER BY sequence',
        (run_id,event_type)) if json.loads(r[0]).get('idempotency_key') == key]


def _owned(connection, run_id, worker_id, fence):
    row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?',(run_id,)).fetchone()
    if row['lease_owner'] != worker_id or row['fence'] != fence or row['lease_expires_at'] <= datetime.now(timezone.utc).isoformat():
        raise SourceOperationError('STALE_RUN_FENCE')


def resume_bounded_extraction_only(service, run_id, *, worker_id, idempotency_key, max_new_calls, provider=None):
    """One explicit, fenced action; repeat its key to recover, not to raise its ceiling."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{2,127}',worker_id):
        raise SourceOperationError('INVALID_WORKER_ID',422)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}',idempotency_key):
        raise SourceOperationError('INVALID_IDEMPOTENCY_KEY',422)
    if type(max_new_calls) is not int or max_new_calls < 0:
        raise SourceOperationError('INVALID_CALL_CEILING',422)
    now = datetime.now(timezone.utc)
    expiry = (now+timedelta(seconds=service.jobs.profile.timeout_seconds+60)).isoformat()
    with service.store.connect(operator_write=True) as c:
        c.execute('BEGIN IMMEDIATE')
        if schema_version(c) != '12':
            raise SourceOperationError('BOUNDED_SCHEMA_REQUIRED')
        row = c.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?',(run_id,)).fetchone()
        if row is None:
            raise SourceOperationError('PROCESSING_RUN_NOT_FOUND',404)
        previous = _events(c,run_id,AUTHORIZED,idempotency_key)
        finished = _events(c,run_id,FINISHED,idempotency_key)
        if previous and previous[0]['requested_ceiling'] != max_new_calls:
            raise SourceOperationError('IDEMPOTENCY_CONFLICT',409)
        if finished:
            return {**finished[0],'duplicate':True,'run':service.get_run(run_id)}
        if row['state'] != 'EXTRACTION_PROCESSING':
            return {'status':'STOP_EXISTING_RUN_STATE','run':service.get_run(run_id),'new_provider_calls':0}
        if row['lease_owner'] is not None and row['lease_expires_at'] > now.isoformat():
            return {'status':'LEASE_BUSY','new_provider_calls':0}
        fence = row['fence']+1
        c.execute('UPDATE source_processing_runs SET lease_owner=?,lease_expires_at=?,fence=? WHERE processing_run_id=?',
                  (worker_id,expiry,fence,run_id))
    try:
        worker = _worker(service,run_id)
        run = worker.get_run(run_id)
        frontier = _frontier(worker,run)
        if not frontier['within_budget']:
            raise SourceOperationError('STOP_BUDGET_INSUFFICIENT')
        with worker.store.connect(operator_write=True) as c:
            c.execute('BEGIN IMMEDIATE'); _owned(c,run_id,worker_id,fence)
            if not previous:
                authorization = {'idempotency_key':idempotency_key,'contract':contract(),
                                 'requested_ceiling':max_new_calls,'effective_ceiling':min(max_new_calls,len(frontier['pending'])-len(frontier['recoverable'])),
                                 'frozen_frontier_sha256':frontier['identity'],'calls_before':frontier['calls']}
                worker._event(c,run_id,AUTHORIZED,authorization)
            else:
                authorization = previous[0]
                if authorization['contract'] != contract() or authorization['frozen_frontier_sha256'] != frontier['identity']:
                    raise SourceOperationError('BOUNDED_FROZEN_PLAN_DRIFT')
        completed_before = frontier['complete']
        while not frontier['complete']:
            recover = bool(frontier['recoverable'])
            if recover and frontier['pending'][0] != frontier['recoverable'][0]:
                raise SourceOperationError('BOUNDED_PENDING_STATE_INCONSISTENT')
            used = frontier['calls']-authorization['calls_before']
            if used < 0 or used > authorization['effective_ceiling']:
                raise SourceOperationError('BOUNDED_CALL_CEILING_EXCEEDED')
            if not recover and frontier['pending'] and used == authorization['effective_ceiling']:
                status = 'CALL_CEILING_REACHED'; break
            if not recover and frontier['pending'] and provider is None:
                status = 'PROVIDER_REQUIRED'; break
            with worker.store.connect(operator_write=True) as c:
                c.execute('BEGIN IMMEDIATE'); _owned(c,run_id,worker_id,fence)
                capacity = stage1_capacity(c)
                if not recover and provider is not None and (capacity['wip_state']=='HARD_STOP' or capacity['unprojected_review_packets'] or capacity['intake_paused']):
                    status = 'STOP_CAPACITY'; break
                expiry = (datetime.now(timezone.utc)+timedelta(seconds=worker.jobs.profile.timeout_seconds+60)).isoformat()
                c.execute('UPDATE source_processing_runs SET lease_expires_at=? WHERE processing_run_id=?',(expiry,run_id))
            persistence.checkpoint('bounded_resume_before_advance')
            worker.output_batches.advance(worker.get_run(run_id),None if recover else provider,worker_id,
                                          allow_new_subdivision=False)
            if worker.get_run(run_id)['state'] != 'EXTRACTION_PROCESSING':
                return {'status':'STOP_RECOVERY_REQUIRED','run':worker.get_run(run_id)}
            updated = _frontier(worker,worker.get_run(run_id))
            if updated == frontier:
                status = 'LEASE_BUSY'; break
            frontier = updated
        else:
            persistence.checkpoint('bounded_resume_before_complete')
            with worker.store.connect(operator_write=True) as c:
                c.execute('BEGIN IMMEDIATE'); _owned(c,run_id,worker_id,fence)
                existing = c.execute('SELECT 1 FROM source_processing_events WHERE processing_run_id=? AND event_type=?',(run_id,COMPLETE)).fetchone()
                if not existing:
                    finals = [dict(r) for r in c.execute('SELECT r.series_id,r.result_sha256 FROM bounded_extraction_series_results r JOIN bounded_extraction_series s USING(series_id) WHERE s.processing_run_id=? ORDER BY r.series_id',(run_id,))]
                    worker._event(c,run_id,COMPLETE,{'contract_version':CONTRACT_VERSION,'frozen_frontier_sha256':frontier['identity'],'series_results':finals,'provider_calls':frontier['calls'],'semantic_not_started':True})
                    c.execute('UPDATE source_processing_runs SET stage=?,updated_at=? WHERE processing_run_id=?',(COMPLETE,datetime.now(timezone.utc).isoformat(),run_id))
            persistence.checkpoint('bounded_resume_complete_durable')
            status = 'ALREADY_BOUNDED_COMPLETE' if completed_before and existing else COMPLETE
        result = {'status':status,'idempotency_key':idempotency_key,'contract_version':CONTRACT_VERSION,
                  'new_provider_calls':frontier['calls']-authorization['calls_before'],
                  'pending_segments':len(frontier['pending']),'bounded_complete':frontier['complete']}
        with worker.store.connect(operator_write=True) as c:
            c.execute('BEGIN IMMEDIATE'); _owned(c,run_id,worker_id,fence)
            worker._event(c,run_id,FINISHED,result)
        return {**result,'duplicate':False,'run':worker.get_run(run_id)}
    except (SourceOperationError,BoundaryError) as error:
        with service.store.connect(operator_write=True) as c:
            c.execute('BEGIN IMMEDIATE'); _owned(c,run_id,worker_id,fence)
            stamp = datetime.now(timezone.utc).isoformat()
            c.execute("UPDATE source_processing_runs SET state='BLOCKED',stage='BOUNDED_ONLY_RESUME',error_code=?,retry_safe=0,manual_recovery_required=0,updated_at=?,ended_at=? WHERE processing_run_id=?",(str(error),stamp,stamp,run_id))
            service._event(c,run_id,'SOURCE_STATE_CHANGED',{'state':'BLOCKED','stage':'BOUNDED_ONLY_RESUME','code':str(error),'retry_safe':False,'manual_recovery_required':False})
        return {'status':'STOP_ON_FIRST_NEW_FAILURE','failure_code':str(error),'run':service.get_run(run_id)}
    finally:
        with service.store.connect(operator_write=True) as c:
            c.execute('UPDATE source_processing_runs SET lease_owner=NULL,lease_expires_at=NULL WHERE processing_run_id=? AND lease_owner=? AND fence=?',(run_id,worker_id,fence))
