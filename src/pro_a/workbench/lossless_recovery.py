"""Fenced zero-call recovery of the precise accepted-five/unopened-22 topology."""
from datetime import datetime, timezone
import hashlib
import json
import re
import time

from pro_a import output_decomposition as output
from pro_a.evidence_binding import identity
from pro_a.source_metadata_authority import scope, validate_resolution
from .bounded_extraction_persistence import canonical, checkpoint
from .bounded_extraction_store import _event, _now
from .domains import Domains
from .extraction_retry import bounded_frozen_components
from .lossless_runtime import AUTHORIZED, accepted_results, finalize
from .review_store import schema_version

VERSION = 'bounded-lossless-aggregate-recovery-v1'
COMMITTED = 'LOSSLESS_AGGREGATE_RECOVERY_COMMITTED'


def require(value, code='LOSSLESS_RECOVERY_NOT_ELIGIBLE'):
    from .source_operations import SourceOperationError
    if not value:
        raise SourceOperationError(code)


def assessment(worker, connection, run_id, bindings):
    require(schema_version(connection) == '12', 'STOP_SCHEMA_MIGRATION_REQUIRED')
    run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
    require(run and run['state'] == 'BLOCKED' and run['stage'] == 'BOUNDED_ONLY_RESUME'
        and run['error_code'] == 'SOURCE_METADATA_CONFLICT')
    require(not connection.execute('SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?', (run_id,)).fetchone())
    require(not connection.execute('SELECT 1 FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (run_id, COMMITTED)).fetchone())
    stops = [dict(r) for r in connection.execute("SELECT * FROM source_processing_events WHERE processing_run_id=? AND event_type='SOURCE_STATE_CHANGED' ORDER BY sequence", (run_id,))
        if json.loads(r['event_json']).get('stage') == 'BOUNDED_ONLY_RESUME']
    require(stops and json.loads(stops[-1]['event_json']).get('code') == 'SOURCE_METADATA_CONFLICT')
    ledger = worker.output_batches.ledger
    accepted, unopened, series_proof, pieces = [], [], [], []
    require(len(bindings) == 5)
    for index, (value, context, catalog, bound) in enumerate(bindings):
        series, plan, state, usage = ledger._load(connection, bound.series_id)
        require(series == bound and series.series_version == 'whole-piece-output-series-v3'
            and series.budget.initial_evidence_refs == 16 and series.budget.max_cumulative_output_tokens == 384000
            and not plan.superseded_segment_ids and len(plan.leaves) == (5,6,6,6,4)[index]
            and state['state'] == 'FAILED')
        require(state['lease_expires_at'] is None or state['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
        events = list(connection.execute('SELECT * FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence', (series.series_id,)))
        failures = [e for e in events if e['event_type'] == 'SERIES_FAILED']
        require(failures and json.loads(failures[-1]['body_json'])['code'] == ('SOURCE_METADATA_CONFLICT' if index == 0 else 'UPSTREAM_SERIES_FAILED'))
        require(failures[-1]['created_at'] <= stops[-1]['created_at'])
        pieces.append({'source_piece_id': context.piece.piece_id, 'series_id': series.series_id, 'series_sha256': series.series_sha256})
        allowed_raws = set()
        for segment in plan.leaves:
            row = connection.execute('SELECT * FROM bounded_extraction_segments WHERE segment_id=?', (segment.segment_id,)).fetchone()
            attempts = list(connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=?', (segment.segment_id,)))
            result = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (segment.segment_id,)).fetchone()
            require(segment.max_output_tokens == 24000)
            require(row['lease_expires_at'] is None or row['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
            if index == 0:
                require(row['state'] == 'SUCCEEDED_COMPLETE' and result and result['result_type'] == 'COMPLETE'
                    and len(attempts) == 1 and attempts[0]['attempt_number'] == 1)
                attempt = attempts[0]
                outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt['attempt_id'],)).fetchone()
                require(outcome and outcome['external_outcome'] == outcome['classification'] == 'SUCCEEDED'
                    and outcome['finish_reason'] == 'tool_calls')
                envelope, body = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, attempt['attempt_id']+'.raw.json', outcome))
                require(envelope['http_status'] == 200 and envelope['finish_reason'] == 'tool_calls')
                stored = ledger._result(series.series_id, result)
                require(stored == output.record_to_result(body.decode('utf-8'), series, segment, catalog, context,
                    record_version=output.RECORD_VERSION))
                payload = output.segment_payload(value, context, catalog, series, segment)
                request = json.loads(attempt['request_json'])
                require(request.get('provider_record_version') == output.RECORD_VERSION
                    and request['payload_sha256'] == identity(payload)
                    and ledger._path(series.series_id, segment.segment_id+'.prompt.json').read_bytes() == canonical(payload).encode('utf-8'))
                accepted.append({'series_id': series.series_id, 'segment_id': segment.segment_id,
                    'attempt_id': attempt['attempt_id'], 'request_sha256': attempt['request_sha256'],
                    'configuration_sha256': attempt['configuration_sha256'], 'raw_sha256': outcome['artifact_sha256'],
                    'result_sha256': stored.result_sha256, 'record_sha256': result['record_sha256']})
                allowed_raws.add(attempt['attempt_id']+'.raw.json')
            else:
                require(row['state'] == 'FAILED' and not attempts and result is None)
                local = [e for e in events if json.loads(e['body_json']).get('segment_id', json.loads(e['body_json']).get('object_id')) == segment.segment_id]
                require(len(local) == 1 and local[0]['event_type'] == 'SEGMENT_CREATED')
                unopened.append({'series_id': series.series_id, 'segment_id': segment.segment_id,
                    'failure_event_sha256': failures[-1]['event_sha256'], 'fence': row['fence']})
        require(all(p.name in allowed_raws for p in ledger._path(series.series_id, 'unused').parent.glob('*.raw.json')))
        pending = 0 if index == 0 else len(plan.leaves)
        require(state['provider_call_reservations'] + pending <= series.budget.max_provider_calls
            and state['output_liability'] + 24000 * pending <= series.budget.max_cumulative_output_tokens, 'LOSSLESS_RECOVERY_BUDGET_INSUFFICIENT')
        series_proof.append({'series_id': series.series_id, 'series_sha256': series.series_sha256,
            'failure_event_sha256': failures[-1]['event_sha256'], 'fence': state['fence'],
            'frontier_version': state['frontier_version'], 'provider_calls': usage.provider_call_count})
    require(len(accepted) == 5 and len(unopened) == 22 and sum(p['provider_calls'] for p in series_proof) == 5)
    frozen = Domains(worker.config).read(run_id, connection=connection)
    source = connection.execute('SELECT * FROM private_sources WHERE source_id=?', (run['source_id'],)).fetchone()
    require(source and all(b[1].source_sha256 == source['source_sha256'] for b in bindings))
    return {'run_id': run_id, 'source_id': run['source_id'], 'source_sha256': source['source_sha256'],
        'frozen_context_sha256': frozen['context_sha256'], 'run_fence': run['fence'],
        'blocked_event_sha256': stops[-1]['event_sha256'], 'accepted': accepted, 'unopened': unopened,
        'series': series_proof, 'authority_scope': scope(run_id, run['source_id'], source['source_sha256'], pieces,
            [a['result_sha256'] for a in accepted])}


def frozen_worker(service, run_id, qualification):
    from .source_operations import SourceOperations
    with service.store.connect() as connection:
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        require(run is not None)
        profile, cloud, frozen, source = bounded_frozen_components(service.config, connection, run)
    return SourceOperations(service.config, profile, cloud, runtime_compatibility=qualification)


def authorize_recovery(service, run_id, resolution, qualification, *, idempotency_key, worker_id, reason):
    from .lossless_compatibility import validate_token, verify_worker
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', idempotency_key or '') is not None, 'INVALID_IDEMPOTENCY_KEY')
    require(re.fullmatch(r'[A-Za-z0-9_-]{3,64}', worker_id or '') is not None, 'INVALID_WORKER_ID')
    require(isinstance(reason, str) and 3 <= len(reason.strip()) <= 1000, 'INVALID_RECOVERY_REASON')
    validate_resolution(resolution)
    proof = validate_token(qualification, run_id=run_id, resolution_identity=resolution['identity'])
    worker = frozen_worker(service, run_id, qualification)
    bindings = verify_worker(worker, run_id, qualification)
    ledger = worker.output_batches.ledger
    with ledger._connection(True) as connection:
        previous = [json.loads(r[0]) for r in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (run_id, COMMITTED))]
        if previous:
            require(len(previous) == 1 and previous[0]['idempotency_key'] == idempotency_key
                and previous[0]['resolution_identity'] == resolution['identity'] and previous[0]['reason'] == reason, 'IDEMPOTENCY_CONFLICT')
            return {**previous[0]['result'], 'duplicate': True}
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        require(run['lease_owner'] is None or run['lease_expires_at'] <= datetime.now(timezone.utc).isoformat(), 'LEASE_BUSY')
        current = assessment(worker, connection, run_id, bindings)
        require(current == proof['scope'], 'LOSSLESS_RECOVERY_SCOPE_DRIFT')
        validate_resolution(resolution, bound_scope=current['authority_scope'])
        connection.execute('UPDATE source_processing_runs SET fence=fence+1 WHERE processing_run_id=?', (run_id,))
        for _, context, catalog, series in bindings:
            require(not connection.execute('SELECT 1 FROM bounded_extraction_events WHERE series_id=? AND event_type=?', (series.series_id, AUTHORIZED)).fetchone(), 'CONFLICTING_LOSSLESS_AUTHORIZATION')
            relative, sha = ledger._artifact(series.series_id, 'metadata-resolution.json', canonical(resolution).encode('utf-8'))
            _event(connection, series.series_id, AUTHORIZED, aggregate_version='lossless-sourcepiece-aggregate-v2',
                resolution_identity=resolution['identity'], artifact_relative=relative, artifact_sha256=sha,
                qualification_identity=qualification.identity, recovery_contract=VERSION)
        checkpoint('lossless_recovery_authorized')
        _, context, catalog, first = bindings[0]
        _, plan, _, _ = ledger._load(connection, first.series_id)
        final = finalize(ledger, connection, first, plan, accepted_results(ledger, connection, first, plan), catalog, context)
        checkpoint('lossless_recovery_first_aggregate')
        for item in current['unopened']:
            connection.execute("UPDATE bounded_extraction_segments SET state='PLANNED',fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE segment_id=?", (_now(), item['segment_id']))
            _event(connection, item['series_id'], 'LOSSLESS_NEVER_CALLED_SEGMENT_REOPENED', segment_id=item['segment_id'],
                failure_event_sha256=item['failure_event_sha256'], idempotency_key=idempotency_key)
        for _, _, _, series in bindings:
            connection.execute('UPDATE bounded_extraction_series SET fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE series_id=?', (_now(), series.series_id))
            if series != first:
                connection.execute("UPDATE bounded_extraction_series SET state='OPEN' WHERE series_id=?", (series.series_id,))
        checkpoint('lossless_recovery_frontier_reopened')
        relative, sha = ledger._artifact(first.series_id, 'lossless-qualification.json', canonical(qualification.evidence).encode('utf-8'))
        result = {'status': 'AUTHORIZED', 'contract_version': VERSION, 'provider_calls': 0,
            'accepted_preserved': 5, 'unopened_reopened': 22, 'aggregate_result_sha256': final['result_sha256']}
        worker._event(connection, run_id, COMMITTED, {'idempotency_key': idempotency_key, 'reason': reason,
            'resolution_identity': resolution['identity'], 'qualification_identity': qualification.identity,
            'qualification_artifact_relative': relative, 'qualification_artifact_sha256': sha,
            'series_id': first.series_id, 'result': result})
        connection.execute("UPDATE source_processing_runs SET state='EXTRACTION_PROCESSING',stage='WHOLE_PIECE_OUTPUT_DECOMPOSITION',error_code=NULL,retry_safe=0,manual_recovery_required=0,ended_at=NULL,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE processing_run_id=?", (_now(), run_id))
        worker._event(connection, run_id, 'SOURCE_STATE_CHANGED', {'state': 'EXTRACTION_PROCESSING',
            'stage': 'WHOLE_PIECE_OUTPUT_DECOMPOSITION', 'recovery_contract': VERSION})
    checkpoint('lossless_recovery_committed')
    return {**result, 'duplicate': False}


def load_worker(service, run_id):
    from .lossless_compatibility import restore_token, verify_worker
    with service.store.connect() as connection:
        rows = list(connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (run_id, COMMITTED)))
    if not rows:
        return None
    require(len(rows) == 1, 'CONFLICTING_LOSSLESS_AUTHORIZATION')
    grant = json.loads(rows[0][0])
    ledger = service.output_batches.ledger
    evidence = json.loads(ledger._read_artifact(grant['series_id'], 'lossless-qualification.json',
        {'artifact_relative': grant['qualification_artifact_relative'], 'artifact_sha256': grant['qualification_artifact_sha256']}))
    token = restore_token(evidence, grant['qualification_identity'])
    worker = frozen_worker(service, run_id, token)
    verify_worker(worker, run_id, token)
    return worker
