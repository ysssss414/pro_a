"""Explicit zero-call recovery of a proven bounded-only truncation frontier."""
from datetime import datetime, timedelta, timezone
from contextlib import nullcontext
import json
import re
import time

from pro_a.bounded_extraction import subdivide_extraction_plan
from pro_a.evidence_binding import identity
from . import bounded_extraction_persistence as persistence
from .bounded_extraction_store import BoundedExtractionStore, _event
from .bounded_resume import AUTHORIZED, _events
from .extraction_retry import frozen_bounded_service
from .review_store import schema_version
from .source_operations import SourceOperationError

VERSION = 'bounded-truncation-recovery-operator-v1'
AUTHORIZED_RECOVERY = 'TRUNCATION_RECOVERY_AUTHORIZED'
SUBDIVIDED = 'TRUNCATED_PARENT_SUBDIVIDED'
REOPENED = 'UPSTREAM_FAIL_CLOSED_REOPENED'


class _AtomicRecoveryStore(BoundedExtractionStore):
    """Transaction ownership only; the inherited engine is unchanged."""
    def __init__(self, config, connection):
        super().__init__(config)
        self.connection = connection

    def _connection(self, write=False):
        _require(self.connection.in_transaction, 'RECOVERY_TRANSACTION_REQUIRED')
        return nullcontext(self.connection)


def _worker(service, run_id, attempt_id):
    return frozen_bounded_service(service, run_id, attempt_id)


def assess_truncation_recovery_compatibility(config, run_id, attempt_id, *, persist=False,
                                           historical_repository_root=None):
    from .retry_compatibility import assess_bounded_retry_compatibility
    return assess_bounded_retry_compatibility(config, run_id, attempt_id,
        persist=persist, bounded_truncation_recovery=True,
        historical_repository_root=historical_repository_root)


def contract():
    return {'version': VERSION, 'provider_calls': 0, 'retry': False, 'replan': False,
            'semantic': False, 'automatic': False, 'subdivision_count_per_action': 1,
            'reopen_scope': 'PROVEN_UPSTREAM_FAIL_CLOSED_UNATTEMPTED_ONLY'}


def _require(value, code='NOT_TRUNCATION_RECOVERY_ELIGIBLE'):
    if not value:
        raise SourceOperationError(code)


def _assessment(worker, connection, run_id, attempt_id, bindings):
    """Prove each leaf's history, not just the count of failed rows."""
    _require(schema_version(connection) == '12', 'BOUNDED_SCHEMA_REQUIRED')
    run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
    _require(run is not None and run['state'] == 'BLOCKED' and run['stage'] == 'BOUNDED_ONLY_RESUME'
             and run['error_code'] == 'BOUNDED_EXTRACTION_FAILED')
    _require(not connection.execute('SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?', (run_id,)).fetchone())
    source_events = list(connection.execute('SELECT * FROM source_processing_events WHERE processing_run_id=? ORDER BY sequence', (run_id,)))
    stops = [e for e in source_events if e['event_type'] == 'SOURCE_STATE_CHANGED'
             and json.loads(e['event_json']).get('stage') == 'BOUNDED_ONLY_RESUME']
    starts = [e for e in source_events if e['event_type'] == AUTHORIZED]
    _require(stops and starts and starts[-1]['sequence'] < stops[-1]['sequence'])
    stop = stops[-1]
    _require(json.loads(stop['event_json']).get('code') == run['error_code'])
    start = starts[-1]
    attempt = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
    _require(attempt is not None and start['created_at'] <= attempt['created_at'] <= stop['created_at'])
    ledger = worker.output_batches.ledger
    loaded, reopened, actual_failures, active = [], [], [], 0
    root = root_failure = None
    for _, _, _, bound in bindings:
        series, plan, state, usage = ledger._load(connection, bound.series_id)
        _require(series == bound and state['state'] in ('FAILED', 'SUCCEEDED_COMPLETE'))
        _require(state['lease_expires_at'] is None or state['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
        events = list(connection.execute('SELECT * FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence', (series.series_id,)))
        failures = [e for e in events if e['event_type'] == 'SERIES_FAILED']
        if state['state'] == 'FAILED':
            _require(failures and start['created_at'] <= failures[-1]['created_at'] <= stop['created_at'])
        known_attempts = {r[0] for r in connection.execute('SELECT a.attempt_id FROM bounded_extraction_attempts a JOIN bounded_extraction_segments s USING(segment_id) WHERE s.series_id=?', (series.series_id,))}
        _require(all(p.name in {a + '.raw.json' for a in known_attempts} for p in ledger._path(series.series_id, 'unused').parent.glob('*.raw.json')))
        active += len(plan.leaves)
        for segment in plan.leaves:
            row = connection.execute('SELECT * FROM bounded_extraction_segments WHERE segment_id=?', (segment.segment_id,)).fetchone()
            _require(row['lease_expires_at'] is None or row['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
            attempts = list(connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number', (segment.segment_id,)))
            accepted = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (segment.segment_id,)).fetchone()
            if row['state'] == 'SUCCEEDED_COMPLETE':
                _require(accepted is not None)
                continue
            _require(row['state'] == 'FAILED' and accepted is None and state['state'] == 'FAILED')
            if attempts:
                actual_failures.append(attempts[-1]['attempt_id'])
                if attempts[-1]['attempt_id'] == attempt_id:
                    root = (series, plan, state, segment)
                    matching = [e for e in events if e['event_type'] == 'SEGMENT_FAILED'
                                and json.loads(e['body_json']).get('attempt_id') == attempt_id]
                    _require(matching and json.loads(matching[-1]['body_json']).get('classification') == 'RAW_OUTCOME_NOT_ACCEPTABLE')
                    root_failure = matching[-1]
                    _require(root_failure['created_at'] <= failures[-1]['created_at'])
            else:
                # No Attempt implies no legal dispatch/raw binding/result. An
                # orphan raw is rejected by the Series artifact inventory above.
                _require(not connection.execute('SELECT 1 FROM bounded_extraction_outcomes o JOIN bounded_extraction_attempts a USING(attempt_id) WHERE a.segment_id=?', (segment.segment_id,)).fetchone())
                _require(all(e['event_type'] in ('SEGMENT_CREATED', REOPENED)
                             for e in events if json.loads(e['body_json']).get('segment_id', json.loads(e['body_json']).get('object_id')) == segment.segment_id))
                reopened.append({'series_id': series.series_id, 'segment_id': segment.segment_id,
                                 'failure_event_sha256': failures[-1]['event_sha256']})
        loaded.append((series, plan, state, usage, failures[-1] if failures else None))
    _require(root is not None and actual_failures == [attempt_id])
    series, plan, state, parent = root
    outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt_id,)).fetchone()
    _require(outcome is not None and outcome['external_outcome'] == 'TRUNCATED'
             and outcome['classification'] == 'TRUNCATED' and outcome['finish_reason'] == 'length')
    envelope, _ = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, attempt_id + '.raw.json', outcome))
    _require(envelope['finish_reason'] == 'length' and envelope['http_status'] == 200)
    root_index = [item[0].series_id for item in loaded].index(series.series_id)
    for index, (item, _, item_state, _, failure) in enumerate(loaded):
        if item_state['state'] != 'FAILED':
            continue
        _require(index >= root_index and root_failure['created_at'] <= failure['created_at'])
        _require(json.loads(failure['body_json'])['code'] == ('BOUNDED_EXTRACTION_FAILED' if index == root_index else 'UPSTREAM_SERIES_FAILED'))
    changed = subdivide_extraction_plan(series, plan, parent.segment_id)
    children = tuple(s for s in changed.segments if s.parent_segment_id == parent.segment_id)
    for item, _, item_state, _, _ in loaded:
        pending = [r for r in reopened if r['series_id'] == item.series_id]
        liability = sum(s.max_output_tokens for s in (children if item.series_id == series.series_id else ()))
        liability += len(pending) * 12000
        reservations = len(pending) + (len(children) if item.series_id == series.series_id else 0)
        _require(item_state['provider_call_reservations'] + reservations <= item.budget.max_provider_calls
                 and item_state['output_liability'] + liability <= item.budget.max_cumulative_output_tokens,
                 'EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY')
    return {'run_id': run_id, 'attempt_id': attempt_id, 'series_id': series.series_id,
            'parent_segment_id': parent.segment_id, 'raw_sha256': outcome['artifact_sha256'],
            'root_failure_event_sha256': root_failure['event_sha256'], 'blocked_event_sha256': stop['event_sha256'],
            'frontier_version': state['frontier_version'], 'reopen': reopened,
            'child_segment_ids': [s.segment_id for s in children],
            'child_assigned_ref_counts': [len(s.assigned_evidence_refs) for s in children],
            'active_leaves_before': active, 'active_leaves_after': active + 1,
            'pending_after_recovery': len(reopened) + 2,
            'provider_calls_before': sum(item[3].provider_call_count for item in loaded)}


def assess_truncation_recovery(service, run_id, attempt_id):
    """Read-only eligibility and deterministic topology; no response parsing."""
    worker = _worker(service, run_id, attempt_id)
    bindings = worker.output_batches.inputs(worker.get_run(run_id))
    with worker.store.connect() as connection:
        return _assessment(worker, connection, run_id, attempt_id, bindings)


def recover_truncated_bounded_extraction(service, run_id, attempt_id, *, worker_id, idempotency_key, reason):
    if not isinstance(worker_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{3,64}', worker_id):
        raise SourceOperationError('INVALID_WORKER_ID', 422)
    if not isinstance(idempotency_key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', idempotency_key):
        raise SourceOperationError('INVALID_IDEMPOTENCY_KEY', 422)
    if (not isinstance(reason, str) or not reason or reason != reason.strip() or len(reason) > 1000
            or re.search(r'[\x00-\x1f\x7f]', reason)):
        raise SourceOperationError('INVALID_RECOVERY_REASON', 422)
    worker = _worker(service, run_id, attempt_id)
    bindings = worker.output_batches.inputs(worker.get_run(run_id))
    with worker.store.connect(operator_write=True) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        previous = _events(connection, run_id, SUBDIVIDED, idempotency_key)
        if previous:
            _require(len(previous) == 1 and previous[0]['attempt_id'] == attempt_id
                     and previous[0]['reason'] == reason, 'IDEMPOTENCY_CONFLICT')
            return {**previous[0]['result'], 'duplicate': True}
        recovered = [json.loads(e[0]) for e in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (run_id, SUBDIVIDED))]
        _require(not any(e['attempt_id'] == attempt_id for e in recovered), 'ALREADY_RECOVERED')
        row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        now = datetime.now(timezone.utc)
        _require(row is not None and (row['lease_owner'] is None or row['lease_expires_at'] <= now.isoformat()), 'LEASE_BUSY')
        assessment = _assessment(worker, connection, run_id, attempt_id, bindings)
        expiry = time.time() + worker.jobs.profile.timeout_seconds + 60
        connection.execute('UPDATE source_processing_runs SET fence=fence+1,lease_owner=?,lease_expires_at=? WHERE processing_run_id=?',
                           (worker_id, (now + timedelta(seconds=worker.jobs.profile.timeout_seconds + 60)).isoformat(), run_id))
        authorization = {'idempotency_key': idempotency_key, 'reason': reason, 'contract': contract(),
                         'attempt_id': attempt_id, 'assessment_sha256': identity(assessment)}
        worker._event(connection, run_id, AUTHORIZED_RECOVERY, authorization)
        persistence.checkpoint('truncation_recovery_authorized')
        affected = {assessment['series_id']} | {r['series_id'] for r in assessment['reopen']}
        for series_id in sorted(affected):
            connection.execute("UPDATE bounded_extraction_series SET state='OPEN',fence=fence+1,lease_owner=?,lease_expires_at=? WHERE series_id=?", (worker_id, expiry, series_id))
        parent_id = assessment['parent_segment_id']
        connection.execute('UPDATE bounded_extraction_segments SET fence=fence+1,lease_owner=?,lease_expires_at=? WHERE segment_id=?', (worker_id, expiry, parent_id))
        fence = connection.execute('SELECT fence FROM bounded_extraction_segments WHERE segment_id=?', (parent_id,)).fetchone()[0]
        atomic = _AtomicRecoveryStore(worker.config, connection)
        children = atomic.subdivide_after_truncation(parent_id, worker_id, fence,
            expected_frontier_version=assessment['frontier_version'])
        persistence.checkpoint('truncation_recovery_frontier_incremented')
        _require([s.segment_id for s in children] == assessment['child_segment_ids'])
        for item in assessment['reopen']:
            connection.execute("UPDATE bounded_extraction_segments SET state='PLANNED',fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE segment_id=?", (now.isoformat(), item['segment_id']))
            _event(connection, item['series_id'], REOPENED, segment_id=item['segment_id'], root_attempt_id=attempt_id,
                   historical_failure_event_sha256=item['failure_event_sha256'], idempotency_key=idempotency_key)
        worker._event(connection, run_id, REOPENED, {'idempotency_key': idempotency_key, 'root_attempt_id': attempt_id,
                       'segment_ids': [r['segment_id'] for r in assessment['reopen']]})
        persistence.checkpoint('truncation_recovery_upstream_reopened')
        result = {'status': 'RECOVERED', 'contract_version': VERSION, **assessment, 'provider_calls': 0}
        worker._event(connection, run_id, SUBDIVIDED, {**authorization, 'result': result})
        persistence.checkpoint('truncation_recovery_before_run_restored')
        connection.execute("UPDATE source_processing_runs SET state='EXTRACTION_PROCESSING',stage='WHOLE_PIECE_OUTPUT_DECOMPOSITION',error_code=NULL,retry_safe=0,manual_recovery_required=0,ended_at=NULL,updated_at=?,lease_owner=NULL,lease_expires_at=NULL WHERE processing_run_id=?", (now.isoformat(), run_id))
        worker._event(connection, run_id, 'SOURCE_STATE_CHANGED', {'state': 'EXTRACTION_PROCESSING',
                       'stage': 'WHOLE_PIECE_OUTPUT_DECOMPOSITION', 'recovery_contract': VERSION})
        connection.execute('UPDATE bounded_extraction_series SET lease_owner=NULL,lease_expires_at=NULL WHERE processing_run_id=? AND lease_owner=?', (run_id, worker_id))
        connection.execute('UPDATE bounded_extraction_segments SET lease_owner=NULL,lease_expires_at=NULL WHERE segment_id=? AND lease_owner=?', (parent_id, worker_id))
    persistence.checkpoint('truncation_recovery_committed')
    return {**result, 'duplicate': False}
