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
    continued = load_evidence_worker(service, run_id)
    if continued is not None:
        return continued
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


# This is a separate operator contract. It never repeats or changes the original
# metadata/lossless authorization, and never repairs a rejected provider record.
EVIDENCE_VERSION = 'bounded-evidence-selector-regeneration-v1'
EVIDENCE_REQUEST = 'strict-assigned-evidence-regeneration-v1'
EVIDENCE_AUTHORIZED = 'EVIDENCE_SELECTOR_REGENERATION_AUTHORIZED'
EVIDENCE_COMMITTED = 'EVIDENCE_SELECTOR_REGENERATION_COMMITTED'
EVIDENCE_GUIDANCE = '''Versioned guidance: strict-assigned-evidence-regeneration-v1.
Independently regenerate using the unchanged full SourcePiece, assigned Evidence,
Node Catalog, ProviderRecord v4 schema and MATERIALITY_WEIGHTED_SELECTIVE_EXTRACTION.
Only reference Evidence assigned to this Segment. RAW_SUBSPAN.selector must be a
continuous, character-for-character literal substring of the exact_text belonging
to its named evidence_ref. Never cross Evidence unit boundaries, copy a selector
from an unassigned unit, or use a summary, paraphrase or synonym as RAW_SUBSPAN.
WHOLE_UNIT requires selector="" and occurrence="1" and is appropriate only when
the entire Evidence unit supports the Claim. If a smaller original fragment is
needed, select a literal subspan that actually exists within the named unit.
Do not emit a Claim or Node match without reliable assigned Evidence support.
Never invent Evidence. Acknowledge every assigned unit exactly once; coverage
does not require a Claim per unit. Preserve materiality-weighted selective research
and useful information; do not artificially suppress valid findings to pass checks.
Do not copy, repair or submit any part of the failed response.
'''


def evidence_contract():
    return {'version': EVIDENCE_VERSION, 'request_version': EVIDENCE_REQUEST,
        'guidance_sha256': hashlib.sha256(EVIDENCE_GUIDANCE.encode()).hexdigest(),
        'new_attempts_max': 1, 'provider_calls': 0, 'automatic_retry': False,
        'replan': False, 'subdivision': False, 'semantic': False}


def evidence_diagnostic(body, series, segment, catalog, context):
    """Inspect original selections independently; never return a repaired record."""
    from collections import Counter
    from pro_a.evidence_binding import EVIDENCE_SELECTION_FIELDS, resolve_evidence_binding_v2
    record = output.normalize_record(body.decode('utf-8'), record_version=output.RECORD_VERSION)
    try:
        output.record_to_result(body.decode('utf-8'), series, segment, catalog, context)
    except ValueError as error:
        require(str(error) == 'EVIDENCE_SELECTOR_NOT_FOUND', 'EVIDENCE_FAILURE_NOT_ELIGIBLE')
    else:
        require(False, 'EVIDENCE_FAILURE_NOT_ELIGIBLE')
    owned = set(segment.assigned_evidence_refs)
    require(Counter(a['evidence_ref'] for a in record['evidence_acknowledgements']) == Counter(owned))
    violations = []
    def selection(obj, path):
        require(obj['evidence_ref'] in owned, 'OUTPUT_OWNERSHIP_VIOLATION')
        try:
            resolve_evidence_binding_v2({k:v for k,v in obj.items() if k in EVIDENCE_SELECTION_FIELDS}, catalog, context)
        except ValueError as error:
            require(str(error) == 'EVIDENCE_SELECTOR_NOT_FOUND' and path.startswith(('$.claims[', '$.node_matches[')),
                'EVIDENCE_FAILURE_NOT_ELIGIBLE')
            violations.append({'path': path + '.evidence.selector', 'code': str(error)})
    names = {n['canonical_name'] for n in record['node_candidates']}
    for family in ('claims', 'node_matches'):
        for i, obj in enumerate(record[family]):
            selection(obj, f'$.{family}[{i}]')
            require(set(obj.get('related_node_ids', [obj['node_id']] if family == 'node_matches' else [])) <= set(context.known_node_ids))
            require(set(obj.get('related_candidate_names', [])) <= names)
    for family in ('node_candidates', 'source_references'):
        for obj in record[family]:
            require(obj['ownership_evidence_ref'] in owned, 'OUTPUT_OWNERSHIP_VIOLATION')
            require(set(obj.get('suggested_parent_node_ids', [])) <= set(context.known_node_ids))
            for selected in (obj, obj.get('preserved_fields', {})):
                if 'evidence_ref' in selected:
                    selection(selected, '$.' + family)
    for obj in record['relation_candidates']:
        require({obj['from_node_id'], obj['to_node_id']} <= set(context.known_node_ids))
        refs = obj['supporting_claim_refs']
        require(refs and len(refs) == len(set(refs)) and set(refs) <= {f'C{i+1}' for i in range(len(record['claims']))})
    require(Counter(v['path'].split('[')[0] for v in violations) == {'$.claims': 26, '$.node_matches': 5}
        and violations[0]['path'] == '$.claims[0].evidence.selector', 'EVIDENCE_FAILURE_NOT_ELIGIBLE')
    return {'first_error': 'EVIDENCE_SELECTOR_NOT_FOUND', 'violations': violations}


def evidence_grants(connection, run_id):
    return [json.loads(r[0]) for r in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=? ORDER BY sequence', (run_id, EVIDENCE_COMMITTED))]


def original_lossless_grant(worker, connection, run_id):
    """The original immutable token is data here, never a token for this runtime."""
    rows = list(connection.execute('SELECT * FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (run_id, COMMITTED)))
    require(len(rows) == 1, 'LOSSLESS_CONTINUATION_ORIGINAL_GRANT_REQUIRED')
    grant = json.loads(rows[0]['event_json'])
    token = json.loads(worker.output_batches.ledger._read_artifact(grant['series_id'], 'lossless-qualification.json',
        {'artifact_relative': grant['qualification_artifact_relative'], 'artifact_sha256': grant['qualification_artifact_sha256']}))
    require(identity(token) == grant['qualification_identity'] and token['scope']['run_id'] == run_id
        and token['resolution_identity'] == grant['resolution_identity'], 'LOSSLESS_CONTINUATION_ORIGINAL_TOKEN_DRIFT')
    return dict(rows[0]), grant, token


def evidence_assessment(worker, connection, run_id, failed_attempt_id, bindings):
    from .lossless_runtime import policy, resolution
    require(schema_version(connection) == '12', 'STOP_SCHEMA_MIGRATION_REQUIRED')
    run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
    require(run and (run['state'], run['stage'], run['error_code']) == ('BLOCKED', 'BOUNDED_ONLY_RESUME', 'BOUNDED_EXTRACTION_FAILED'), 'EVIDENCE_RECOVERY_NOT_ELIGIBLE')
    require(not evidence_grants(connection, run_id), 'EVIDENCE_REGENERATION_ALREADY_AUTHORIZED')
    require(not connection.execute('SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?', (run_id,)).fetchone())
    prior_row, prior, prior_token = original_lossless_grant(worker, connection, run_id)
    stops = [dict(r) for r in connection.execute("SELECT * FROM source_processing_events WHERE processing_run_id=? AND event_type='SOURCE_STATE_CHANGED' ORDER BY sequence", (run_id,))
        if json.loads(r['event_json']).get('stage') == 'BOUNDED_ONLY_RESUME']
    require(stops and stops[-1]['sequence'] > prior_row['sequence'] and json.loads(stops[-1]['event_json']).get('code') == run['error_code'])
    ledger = worker.output_batches.ledger
    accepted, unopened, series_proof, failed = [], [], [], []
    require(len(bindings) == 5)
    for index, (value, context, catalog, bound) in enumerate(bindings):
        series, plan, state, usage = ledger._load(connection, bound.series_id)
        require(series == bound and series.series_version == 'whole-piece-output-series-v3'
            and series.budget.initial_evidence_refs == 16 and series.budget.max_cumulative_output_tokens == 384000
            and not plan.superseded_segment_ids and len(plan.leaves) == (5,6,6,6,4)[index]
            and state['state'] == ('SUCCEEDED_COMPLETE' if index == 0 else 'FAILED'))
        require(state['lease_expires_at'] is None or state['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
        grant = policy(connection, series.series_id)
        require(grant and grant['qualification_identity'] == prior['qualification_identity'] and grant['recovery_contract'] == VERSION)
        authority = resolution(ledger, connection, series)
        validate_resolution(authority, bound_scope=prior_token['scope']['authority_scope'])
        require(authority['identity'] == prior['resolution_identity'])
        events = list(connection.execute('SELECT * FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence', (series.series_id,)))
        failures = [r for r in events if r['event_type'] == 'SERIES_FAILED']
        if index:
            require(failures and json.loads(failures[-1]['body_json'])['code'] == ('INVALID_SEGMENT_RESPONSE' if index == 1 else 'UPSTREAM_SERIES_FAILED')
                and prior_row['created_at'] <= failures[-1]['created_at'] <= stops[-1]['created_at'])
        pending, raws = 0, set()
        for segment in plan.leaves:
            row = connection.execute('SELECT * FROM bounded_extraction_segments WHERE segment_id=?', (segment.segment_id,)).fetchone()
            attempts = list(connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=?', (segment.segment_id,)))
            result = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (segment.segment_id,)).fetchone()
            require(segment.max_output_tokens == 24000)
            require(row['lease_expires_at'] is None or row['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
            if not attempts:
                require(index > 0 and row['state'] == 'FAILED' and result is None)
                local = [r for r in events if json.loads(r['body_json']).get('segment_id', json.loads(r['body_json']).get('object_id')) == segment.segment_id]
                require([r['event_type'] for r in local] == ['SEGMENT_CREATED', 'LOSSLESS_NEVER_CALLED_SEGMENT_REOPENED'])
                unopened.append({'series_id': series.series_id, 'segment_id': segment.segment_id, 'fence': row['fence']})
                pending += 1
                continue
            require(len(attempts) == 1 and attempts[0]['attempt_number'] == 1, 'EVIDENCE_REGENERATION_ATTEMPT_LIMIT')
            attempt = attempts[0]
            outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt['attempt_id'],)).fetchone()
            require(outcome and outcome['external_outcome'] == outcome['classification'] == 'SUCCEEDED'
                and outcome['finish_reason'] == 'tool_calls' and type(outcome['output_tokens']) is int and 0 <= outcome['output_tokens'] < 24000)
            raw = ledger._read_artifact(series.series_id, attempt['attempt_id'] + '.raw.json', outcome)
            envelope, body = ledger._decode_envelope(attempt, raw)
            require(envelope['http_status'] == 200 and envelope['finish_reason'] == 'tool_calls')
            raws.add(attempt['attempt_id'] + '.raw.json')
            payload = output.segment_payload(value, context, catalog, series, segment)
            request = json.loads(attempt['request_json'])
            require(request.get('provider_record_version') == output.RECORD_VERSION and request['payload_sha256'] == identity(payload)
                and ledger._path(series.series_id, segment.segment_id + '.prompt.json').read_bytes() == canonical(payload).encode())
            proof = {'series_id': series.series_id, 'segment_id': segment.segment_id, 'attempt_id': attempt['attempt_id'],
                'request_sha256': attempt['request_sha256'], 'raw_sha256': outcome['artifact_sha256'], 'attempt_record_sha256': attempt['record_sha256']}
            if result:
                require(row['state'] == 'SUCCEEDED_COMPLETE' and result['result_type'] == 'COMPLETE')
                stored = ledger._result(series.series_id, result)
                require(stored == output.record_to_result(body.decode(), series, segment, catalog, context))
                accepted.append({**proof, 'result_sha256': result['result_sha256'], 'record_sha256': result['record_sha256']})
            else:
                require(index == 1 and row['state'] == 'FAILED' and attempt['attempt_id'] == failed_attempt_id)
                local = [r for r in events if r['event_type'] == 'SEGMENT_FAILED' and json.loads(r['body_json']).get('attempt_id') == failed_attempt_id]
                require(len(local) == 1 and json.loads(local[0]['body_json'])['classification'] == 'INVALID_SEGMENT_RESPONSE')
                failed.append({**proof, 'diagnostic': evidence_diagnostic(body, series, segment, catalog, context), 'fence': row['fence'],
                    'assigned_evidence_identity': identity([u.__dict__ for u in catalog.units if u.evidence_ref in segment.assigned_evidence_refs])})
                pending += 1
        require(all(p.name in raws for p in ledger._path(series.series_id, 'unused').parent.glob('*.raw.json')))
        require(state['provider_call_reservations'] + pending <= series.budget.max_provider_calls
            and state['output_liability'] + 24000 * pending <= series.budget.max_cumulative_output_tokens, 'EVIDENCE_REGENERATION_BUDGET_INSUFFICIENT')
        series_proof.append({'series_id': series.series_id, 'fence': state['fence'], 'frontier_version': state['frontier_version'],
            'event_sha256': events[-1]['event_sha256'], 'calls': usage.provider_call_count})
    require(len(accepted) == 6 and len(unopened) == 20 and len(failed) == 1 and sum(p['calls'] for p in series_proof) == 7)
    first = bindings[0][3].series_id
    aggregate = connection.execute('SELECT * FROM bounded_extraction_series_results WHERE series_id=?', (first,)).fetchone()
    document = json.loads(ledger._read_artifact(first, 'aggregate.json', aggregate))
    require(aggregate['result_sha256'] == prior['result']['aggregate_result_sha256']
        and document['identity'] == prior_token['accepted_aggregate_identity']
        and document['observation_ledger']['identity'] == prior_token['accepted_observation_ledger_identity']
        and len(document['observation_ledger']['observations']) == 146)
    frozen = Domains(worker.config).read(run_id, connection=connection)
    return {'run_id': run_id, 'source_id': run['source_id'], 'run_fence': run['fence'], 'frozen_context_sha256': frozen['context_sha256'],
        'blocked_event_sha256': stops[-1]['event_sha256'], 'accepted': accepted, 'unopened': unopened, 'failed': failed[0],
        'series': series_proof, 'original_grant': prior_row, 'original_token_identity': identity(prior_token),
        'first_aggregate': dict(aggregate), 'resolution_identity': prior['resolution_identity']}


def evidence_payload(original, proof):
    import copy
    payload = copy.deepcopy(original)
    payload['target'].update(regeneration_contract_version=EVIDENCE_REQUEST,
        original_attempt_id=proof['failed']['attempt_id'], original_request_sha256=proof['failed']['request_sha256'],
        frozen_context_sha256=proof['frozen_context_sha256'],
        assigned_evidence_identity=proof['failed']['assigned_evidence_identity'],
        regeneration_guidance_sha256=evidence_contract()['guidance_sha256'])
    payload['request']['messages'].append({'role': 'user', 'content': EVIDENCE_GUIDANCE})
    return payload


def evidence_request(ledger, series, segment, original, proof, prompt_sha):
    return {**ledger._request(series, segment, prompt_sha, original['configuration_sha256']),
        **{k:v for k,v in evidence_payload({'target': {}, 'request': {'messages': []}}, proof)['target'].items()}}


def evidence_request_material(worker, proof, bindings, connection=None):
    ledger = worker.output_batches.ledger
    value, context, catalog, series = next(b for b in bindings if b[3].series_id == proof['failed']['series_id'])
    if connection is None:
        with ledger._connection() as c:
            return evidence_request_material(worker, proof, bindings, c)
    _, plan, _, _ = ledger._load(connection, series.series_id)
    segment = next(s for s in plan.leaves if s.segment_id == proof['failed']['segment_id'])
    original = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?', (proof['failed']['attempt_id'],)).fetchone()
    payload = evidence_payload(output.segment_payload(value, context, catalog, series, segment), proof)
    content = canonical(payload).encode()
    sha = hashlib.sha256(content).hexdigest()
    request = evidence_request(ledger, series, segment, original, proof, sha)
    request_sha = identity(request)
    return ({'attempt_id': ledger._attempt_id(segment.segment_id, 2, request_sha), 'request': request,
        'request_sha256': request_sha, 'prompt_sha256': sha}, content, original, segment)


def evidence_expected_request(ledger, connection, series, segment, attempt):
    from .lossless_compatibility import restore_continuation
    require(attempt['attempt_number'] == 2, 'EVIDENCE_REGENERATION_ATTEMPT_LIMIT')
    committed = evidence_grants(connection, series.processing_run_id)
    grants = [json.loads(r[0]) for r in connection.execute('SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type=?', (series.series_id, EVIDENCE_AUTHORIZED))]
    source = [json.loads(r[0]) for r in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (series.processing_run_id, EVIDENCE_AUTHORIZED))]
    require(len(committed) == len(grants) == len(source) == 1 and {**grants[0], 'series_id': series.series_id} == source[0] == committed[0]['grant'],
        'EVIDENCE_REGENERATION_AUTHORIZATION_REQUIRED')
    grant = source[0]
    token = restore_continuation(json.loads(ledger._read_artifact(series.series_id, 'evidence-continuation.json', grant)), grant['qualification_identity'])
    proof = token.evidence['scope']
    require(proof['run_id'] == series.processing_run_id and proof['failed']['segment_id'] == segment.segment_id
        and proof['failed']['series_id'] == series.series_id and token.evidence['new_request']['attempt_id'] == attempt['attempt_id'])
    frozen = Domains(ledger.config).read(series.processing_run_id, connection=connection)
    require(frozen['context_sha256'] == proof['frozen_context_sha256'])
    original = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? AND attempt_number=1', (segment.segment_id,)).fetchone()
    require(original and original['attempt_id'] == proof['failed']['attempt_id'] and original['request_sha256'] == proof['failed']['request_sha256'])
    content = ledger._path(series.series_id, segment.segment_id + '.prompt.json').read_bytes()
    require(hashlib.sha256(content).hexdigest() == json.loads(original['request_json'])['payload_sha256'])
    regenerated = canonical(evidence_payload(json.loads(content), proof)).encode()
    prompt_sha = hashlib.sha256(regenerated).hexdigest()
    request = evidence_request(ledger, series, segment, original, proof, prompt_sha)
    require(token.evidence['new_request'] == {'attempt_id': attempt['attempt_id'], 'request': request,
        'request_sha256': identity(request), 'prompt_sha256': prompt_sha}
        and ledger._path(series.series_id, attempt['attempt_id'] + '.prompt.json').read_bytes() == regenerated,
        'EVIDENCE_REGENERATION_REQUEST_DRIFT')
    return request


def evidence_dispatch_payload(ledger, segment_id, original_payload):
    from .strict_recovery import dispatch_payload
    with ledger._connection() as connection:
        attempt = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number DESC LIMIT 1', (segment_id,)).fetchone()
        if attempt is None or json.loads(attempt['request_json']).get('regeneration_contract_version') != EVIDENCE_REQUEST:
            return dispatch_payload(ledger, segment_id, original_payload)
        _, (series, plan, _, _) = ledger._segment_row(connection, segment_id)
        segment = next(s for s in plan.leaves if s.segment_id == segment_id)
        expected = evidence_expected_request(ledger, connection, series, segment, attempt)
        original = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? AND attempt_number=1', (segment_id,)).fetchone()
        require(identity(original_payload) == json.loads(original['request_json'])['payload_sha256'] and json.loads(attempt['request_json']) == expected)
        content = ledger._path(series.series_id, attempt['attempt_id'] + '.prompt.json').read_bytes()
        return json.loads(content), attempt['attempt_id'] + '.prompt.json'


def authorize_evidence_regeneration(service, run_id, failed_attempt_id, qualification, *, idempotency_key, worker_id, reason):
    from .lossless_compatibility import validate_continuation, verify_worker
    from .bounded_extraction_store import _record
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', idempotency_key or '') is not None, 'INVALID_IDEMPOTENCY_KEY')
    require(re.fullmatch(r'[A-Za-z0-9_-]{3,64}', worker_id or '') is not None, 'INVALID_WORKER_ID')
    require(isinstance(reason, str) and 3 <= len(reason.strip()) <= 1000, 'INVALID_RECOVERY_REASON')
    evidence = validate_continuation(qualification, run_id=run_id)
    require(evidence['scope']['failed']['attempt_id'] == failed_attempt_id, 'EVIDENCE_CONTINUATION_SCOPE_MISMATCH')
    worker = frozen_worker(service, run_id, qualification)
    bindings = verify_worker(worker, run_id, qualification)
    ledger = worker.output_batches.ledger
    with ledger._connection(True) as connection:
        previous = evidence_grants(connection, run_id)
        if previous:
            require(len(previous) == 1 and previous[0]['grant']['idempotency_key'] == idempotency_key
                and previous[0]['grant']['reason'] == reason and previous[0]['grant']['qualification_identity'] == qualification.identity,
                'IDEMPOTENCY_CONFLICT')
            return {**previous[0]['result'], 'duplicate': True}
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        require(run['lease_owner'] is None or run['lease_expires_at'] <= datetime.now(timezone.utc).isoformat(), 'LEASE_BUSY')
        proof = evidence_assessment(worker, connection, run_id, failed_attempt_id, bindings)
        require(proof == evidence['scope'], 'EVIDENCE_REGENERATION_SCOPE_DRIFT')
        material, content, original, segment = evidence_request_material(worker, proof, bindings, connection)
        require(material == evidence['new_request'], 'EVIDENCE_REGENERATION_REQUEST_DRIFT')
        sid = proof['failed']['series_id']
        relative, sha = ledger._artifact(sid, 'evidence-continuation.json', canonical(evidence).encode())
        grant = {'contract': evidence_contract(), 'qualification_identity': qualification.identity,
            'original_qualification_identity': proof['original_token_identity'], 'original_grant_sha256': proof['original_grant']['event_sha256'],
            'artifact_relative': relative, 'artifact_sha256': sha, 'series_id': sid,
            'idempotency_key': idempotency_key, 'reason': reason, 'failed_attempt_id': failed_attempt_id}
        connection.execute('UPDATE source_processing_runs SET fence=fence+1 WHERE processing_run_id=?', (run_id,))
        _event(connection, sid, EVIDENCE_AUTHORIZED, **{k:v for k,v in grant.items() if k != 'series_id'})
        worker._event(connection, run_id, EVIDENCE_AUTHORIZED, grant)
        checkpoint('evidence_regeneration_authorized')
        ledger._artifact(sid, material['attempt_id'] + '.prompt.json', content)
        attempt = _record(connection, 'attempts', {'attempt_id': material['attempt_id'], 'segment_id': segment.segment_id,
            'attempt_number': 2, 'request_json': canonical(material['request']), 'request_sha256': material['request_sha256'],
            'configuration_sha256': original['configuration_sha256'], 'budget_identity': original['budget_identity'], 'created_at': _now()})
        connection.execute('UPDATE bounded_extraction_series SET provider_call_reservations=provider_call_reservations+1,output_liability=output_liability+24000 WHERE series_id=?', (sid,))
        _event(connection, sid, 'ATTEMPT_RESERVED', attempt_id=material['attempt_id'], record_sha256=attempt['record_sha256'])
        checkpoint('evidence_regeneration_attempt_reserved')
        for item in [proof['failed'], *proof['unopened']]:
            connection.execute("UPDATE bounded_extraction_segments SET state='PLANNED',fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE segment_id=?", (_now(), item['segment_id']))
            _event(connection, item['series_id'], 'EVIDENCE_REGENERATION_FRONTIER_REOPENED', segment_id=item['segment_id'], qualification_identity=qualification.identity)
        for affected in {sid} | {p['series_id'] for p in proof['unopened']}:
            connection.execute("UPDATE bounded_extraction_series SET state='OPEN',fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE series_id=?", (_now(), affected))
        checkpoint('evidence_regeneration_frontier_reopened')
        result = {'status': 'AUTHORIZED', 'provider_calls': 0, 'contract_version': EVIDENCE_VERSION,
            'new_attempt_id': material['attempt_id'], 'request_sha256': material['request_sha256'], 'prompt_sha256': material['prompt_sha256'],
            'accepted_preserved': 6, 'unopened_reopened': 20, 'new_attempt_number': 2}
        worker._event(connection, run_id, EVIDENCE_COMMITTED, {'grant': grant, 'result': result})
        connection.execute("UPDATE source_processing_runs SET state='EXTRACTION_PROCESSING',stage='WHOLE_PIECE_OUTPUT_DECOMPOSITION',error_code=NULL,retry_safe=0,manual_recovery_required=0,ended_at=NULL,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE processing_run_id=?", (_now(), run_id))
        worker._event(connection, run_id, 'SOURCE_STATE_CHANGED', {'state': 'EXTRACTION_PROCESSING', 'stage': 'WHOLE_PIECE_OUTPUT_DECOMPOSITION', 'recovery_contract': EVIDENCE_VERSION})
    checkpoint('evidence_regeneration_committed')
    return {**result, 'duplicate': False}


def load_evidence_worker(service, run_id):
    from .lossless_compatibility import restore_continuation, verify_worker
    with service.store.connect() as connection:
        grants = evidence_grants(connection, run_id)
    if not grants:
        return None
    require(len(grants) == 1, 'CONFLICTING_EVIDENCE_REGENERATION_AUTHORIZATION')
    grant = grants[0]['grant']
    evidence = json.loads(service.output_batches.ledger._read_artifact(grant['series_id'], 'evidence-continuation.json', grant))
    token = restore_continuation(evidence, grant['qualification_identity'])
    worker = frozen_worker(service, run_id, token)
    verify_worker(worker, run_id, token)
    return worker
