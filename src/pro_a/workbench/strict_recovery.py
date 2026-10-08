"""Explicit, exact-scope regeneration of a proven v2 bounded output failure."""
import copy
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import time

from pro_a import output_decomposition as output, source_analysis_provider_record as lexical
from pro_a import source_analysis_wire as wire
from pro_a.evidence_binding import identity, resolve_evidence_binding_v2
from . import bounded_extraction_persistence as persistence
from .bounded_extraction_persistence import canonical
from .bounded_extraction_store import _event, _record, _now
from .bounded_resume import AUTHORIZED, _events
from .domains import Domains
from .extraction_retry import frozen_bounded_service, _validate_retry_request
from .review_store import schema_version
from .source_operations import SourceOperationError

VERSION = 'bounded-strict-same-run-output-recovery-v1'
REQUEST_VERSION = 'strict-provider-lexical-regeneration-v1'
AUTHORIZED_RECOVERY = 'STRICT_SAME_RUN_RECOVERY_AUTHORIZED'
COMMITTED = 'STRICT_SAME_RUN_RECOVERY_COMMITTED'
REOPENED = 'STRICT_UPSTREAM_FAIL_CLOSED_REOPENED'
GUIDANCE = """Versioned format-only regeneration: strict-provider-lexical-regeneration-v1.
Independently generate one complete response using the unchanged complete SourcePiece,
assigned Evidence, selective materiality objective and original acceptance contract.
Previous error classes: NONDEFAULT_INACTIVE_VARIANT, ACTIVE_FIELD_IN_PRESERVED_SLOT,
UNKNOWN_LOCAL_CANDIDATE. Safe first field path: node_candidates[0].cross_source_or_node_value.
Inactive Node type slots must use their exact existing FALSE/empty-text/NONE defaults.
Only genuinely present inactive type fields belong in preserved_fields; active fields
must stay in their primary slots. Do not discard content or move fields automatically.
Every related_candidate_names entry must exactly name a valid candidate emitted in
this same response. Do not reference candidates from another Segment or invent objects.
Coverage never requires manufacturing Claims. Do not invent Candidate, Claim, Node or
Evidence. Preserve the original complete SourcePiece and assigned Evidence context.
Do not repair, copy or submit any fragment of the failed response; regenerate independently.
"""

def contract():
    return {'version': VERSION, 'request_version': REQUEST_VERSION, 'max_new_attempts': 1,
        'provider_calls': 0, 'automatic_retry': False, 'replan': False, 'subdivision': False,
        'semantic': False, 'local_acceptance_changed': False, 'research_semantics_changed': False,
        'reopen_scope': 'PROVEN_UPSTREAM_FAIL_CLOSED_UNATTEMPTED_ONLY',
        'guidance_sha256': hashlib.sha256(GUIDANCE.encode('utf-8')).hexdigest()}

def _require(value, code='STRICT_RECOVERY_NOT_ELIGIBLE'):
    if not value:
        raise SourceOperationError(code)

def failure_diagnostic(body, segment, catalog, context):
    """Validate original fields independently. Never repair a record to admit it."""
    record = lexical.parse_object(body.decode('utf-8', errors='strict'))
    lexical.validate_shape(record, output.record_schema(record_version=output.V3_RECORD_VERSION))
    try:
        output.normalize_record(body.decode('utf-8'), record_version=output.V3_RECORD_VERSION)
    except ValueError as error:
        _require(str(error) == 'NONDEFAULT_INACTIVE_VARIANT')
    else:
        _require(False)
    owned = set(segment.assigned_evidence_refs)
    _require(Counter(a['evidence_ref'] for a in record['evidence_acknowledgements']) == Counter(segment.assigned_evidence_refs))
    violations = []
    def selection(value, pointer=None):
        native = lexical.selection(value)
        if pointer is not None:
            native['evidence_pointer'] = pointer
        binding = resolve_evidence_binding_v2(native, catalog, context)
        _require(binding.evidence_ref in owned)
    def ids(values):
        wire._strings(values, 'node_ids')
        _require(all(v in context.known_node_ids for v in values))
    for family in ('claims', 'node_matches', 'node_candidates', 'relation_candidates'):
        for i, obj in enumerate(record[family]):
            lexical.confidence(obj['confidence'])
            path = f'{family}[{i}]'
            if family in ('claims', 'node_matches'):
                selection(obj['evidence'], obj.get('evidence_pointer'))
            if family == 'claims':
                wire._string(obj['statement'], 'claim.statement', nonempty=True)
                lexical.parse_object(obj['structured_json'])
                ids(obj['related_node_ids'])
                wire._strings(obj['related_candidate_names'], 'claim.related_candidate_names')
            elif family == 'node_matches':
                ids([obj['node_id']])
            elif family == 'node_candidates':
                wire._string(obj['canonical_name'], 'node_candidate.canonical_name', nonempty=True)
                wire._strings(obj['aliases'], 'node_candidate.aliases')
                ids(obj['suggested_parent_node_ids'])
                lexical.boolean(obj['independent_research_value'])
                _require(obj['ownership_evidence_ref'] in owned)
                active = wire._NODE_VARIANTS.get(obj['primary_type'], set())
                for field in sorted(wire._TYPE_FIELDS):
                    name = 'event_evidence' if field == 'evidence_ref' else field
                    value = obj[name]
                    if field in wire._BOOL_FIELDS:
                        lexical.boolean(value)
                    if field == 'evidence_ref' and (field in active or value != lexical.NONE_SELECTION):
                        selection(value)
                    if field not in active and value != lexical._inactive(field):
                        violations.append({'path': path + '.' + name, 'code': 'NONDEFAULT_INACTIVE_VARIANT'})
                for field, slot in obj['preserved_fields'].items():
                    p = path + '.preserved_fields.' + field
                    if lexical.boolean(slot['present']):
                        if field in active:
                            violations.append({'path': p, 'code': 'ACTIVE_FIELD_IN_PRESERVED_SLOT'})
                        if field == 'evidence_ref':
                            selection(slot['value'])
                        elif field in wire._BOOL_FIELDS:
                            lexical.boolean(slot['value'])
                    else:
                        _require(slot['value'] == lexical._inactive(field))
            elif family == 'relation_candidates':
                ids([obj['from_node_id'], obj['to_node_id']])
                refs = obj['supporting_claim_refs']
                wire._strings(refs, 'relation.supporting_claim_refs')
                _require(refs and len(set(refs)) == len(refs) and set(refs) <= {f'C{n+1}' for n in range(len(record['claims']))})
    names = {n['canonical_name'] for n in record['node_candidates']}
    for i, claim in enumerate(record['claims']):
        for j, name in enumerate(claim['related_candidate_names']):
            if name not in names:
                violations.append({'path': f'claims[{i}].related_candidate_names[{j}]', 'code': 'UNKNOWN_LOCAL_CANDIDATE'})
    for obj in record['source_references']:
        wire._string(obj['title'], 'source_reference.title', nonempty=True)
        _require(obj['ownership_evidence_ref'] in owned)
    _require(any(v['code'] == 'NONDEFAULT_INACTIVE_VARIANT' for v in violations)
             and any(v['code'] == 'UNKNOWN_LOCAL_CANDIDATE' for v in violations))
    return {'first_error': 'NONDEFAULT_INACTIVE_VARIANT', 'violations': violations,
        'counts': dict(Counter(v['code'] for v in violations)), 'evidence_checks_valid': True}

def regeneration_payload(original, context_sha256, original_request_sha256):
    payload = copy.deepcopy(original)
    payload['target'].update(regeneration_contract_version=REQUEST_VERSION,
        frozen_context_sha256=context_sha256, original_request_sha256=original_request_sha256)
    payload['request']['messages'].append({'role': 'user', 'content': GUIDANCE})
    return payload

def _request(ledger, series, segment, original, context_sha256, payload_sha256):
    return {**ledger._request(series, segment, payload_sha256, original['configuration_sha256']),
        'regeneration_contract_version': REQUEST_VERSION, 'original_request_sha256': original['request_sha256'],
        'frozen_context_sha256': context_sha256}

def authorizations(connection, run_id):
    return [json.loads(r[0]) for r in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=? ORDER BY sequence', (run_id, COMMITTED))]

def expected_attempt_request(ledger, connection, series, segment, attempt):
    """Fail closed unless the independently frozen Attempt 2 has exact lineage."""
    _require(attempt['attempt_number'] == 2, 'STRICT_RECOVERY_ATTEMPT_LIMIT')
    original = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? AND attempt_number=1', (segment.segment_id,)).fetchone()
    _require(original is not None)
    grants = [json.loads(r[0]) for r in connection.execute('SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type=?', (series.series_id, AUTHORIZED_RECOVERY))]
    matches = [g for g in grants if g.get('new_attempt_id') == attempt['attempt_id']]
    _require(len(matches) == 1, 'STRICT_RECOVERY_AUTHORIZATION_REQUIRED')
    grant = matches[0]
    source_grants = [json.loads(r[0]) for r in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?', (series.processing_run_id, AUTHORIZED_RECOVERY))]
    committed = authorizations(connection, series.processing_run_id)
    _require(len(source_grants) == len(committed) == 1
             and identity({k: v for k, v in source_grants[0].items() if k != 'series_id'}) == identity(grant)
             and committed[0]['result']['new_attempt_id'] == attempt['attempt_id'], 'STRICT_RECOVERY_AUTHORIZATION_REQUIRED')
    frozen = Domains(ledger.config).read(series.processing_run_id, connection=connection)
    _require(grant['contract'] == contract() and grant['failed_attempt_id'] == original['attempt_id']
             and grant['segment_id'] == segment.segment_id and grant['run_id'] == series.processing_run_id
             and grant['original_request_sha256'] == original['request_sha256']
             and grant['frozen_context_sha256'] == frozen['context_sha256'])
    outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (original['attempt_id'],)).fetchone()
    _require(outcome is not None and grant['original_raw_sha256'] == outcome['artifact_sha256'])
    original_prompt = ledger._path(series.series_id, segment.segment_id + '.prompt.json').read_bytes()
    _require(hashlib.sha256(original_prompt).hexdigest() == json.loads(original['request_json'])['payload_sha256'])
    payload = regeneration_payload(json.loads(original_prompt), frozen['context_sha256'], original['request_sha256'])
    content = canonical(payload).encode('utf-8')
    prompt_sha256 = hashlib.sha256(content).hexdigest()
    expected = _request(ledger, series, segment, original, frozen['context_sha256'], prompt_sha256)
    _require(grant['new_request_sha256'] == identity(expected) and grant['new_prompt_sha256'] == prompt_sha256
             and attempt['attempt_id'] == ledger._attempt_id(segment.segment_id, 2, identity(expected))
             and ledger._path(series.series_id, attempt['attempt_id'] + '.prompt.json').read_bytes() == content,
             'STRICT_RECOVERY_REQUEST_IDENTITY_MISMATCH')
    return expected

def dispatch_payload(ledger, segment_id, original_payload):
    """Normal dispatch is byte-identical. Only a proven strict Attempt uses guidance."""
    with ledger._connection() as connection:
        row, (series, plan, _, _) = ledger._segment_row(connection, segment_id)
        attempt = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number DESC LIMIT 1', (segment_id,)).fetchone()
        if attempt is None or 'regeneration_contract_version' not in json.loads(attempt['request_json']):
            return original_payload, segment_id + '.prompt.json'
        segment = next(s for s in plan.segments if s.segment_id == segment_id)
        expected = expected_attempt_request(ledger, connection, series, segment, attempt)
        _require(json.loads(attempt['request_json']) == expected)
        original = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? AND attempt_number=1', (segment_id,)).fetchone()
        _require(hashlib.sha256(canonical(original_payload).encode('utf-8')).hexdigest() == json.loads(original['request_json'])['payload_sha256'])
        return regeneration_payload(original_payload, expected['frozen_context_sha256'], original['request_sha256']), attempt['attempt_id'] + '.prompt.json'

def _assessment(worker, connection, run_id, attempt_id, bindings):
    _require(schema_version(connection) == '12')
    run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
    _require(not authorizations(connection, run_id), 'STRICT_RECOVERY_ALREADY_AUTHORIZED')
    _require(run is not None and run['state'] == 'BLOCKED' and run['stage'] == 'BOUNDED_ONLY_RESUME'
             and run['error_code'] == 'BOUNDED_EXTRACTION_FAILED')
    _require(not connection.execute('SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?', (run_id,)).fetchone())
    history = list(connection.execute('SELECT * FROM source_processing_events WHERE processing_run_id=? ORDER BY sequence', (run_id,)))
    starts = [r for r in history if r['event_type'] == AUTHORIZED]
    stops = [r for r in history if r['event_type'] == 'SOURCE_STATE_CHANGED' and json.loads(r['event_json']).get('stage') == 'BOUNDED_ONLY_RESUME']
    _require(starts and stops and starts[-1]['sequence'] < stops[-1]['sequence'])
    start, stop = starts[-1], stops[-1]
    _require(json.loads(stop['event_json']).get('code') == run['error_code'])
    ledger = worker.output_batches.ledger
    reopened, accepted, failures, loaded, target = [], [], [], [], None
    for value, context, catalog, bound in bindings:
        series, plan, state, usage = ledger._load(connection, bound.series_id)
        _require(series == bound and series.series_version == 'whole-piece-output-series-v2'
                 and series.output_budget_identity == 'operation-output-budget-v2'
                 and series.budget.max_cumulative_output_tokens == 384000
                 and series.budget.initial_evidence_refs == 16 and not plan.superseded_segment_ids
                 and state['state'] in ('FAILED', 'SUCCEEDED_COMPLETE'))
        _require(state['lease_expires_at'] is None or state['lease_expires_at'] <= time.time(), 'LEASE_BUSY')
        events = list(connection.execute('SELECT * FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence', (series.series_id,)))
        series_failures = [e for e in events if e['event_type'] == 'SERIES_FAILED']
        if state['state'] == 'FAILED':
            _require(series_failures and start['created_at'] <= series_failures[-1]['created_at'] <= stop['created_at'])
        known_attempts = {r[0] for r in connection.execute('SELECT a.attempt_id FROM bounded_extraction_attempts a JOIN bounded_extraction_segments s USING(segment_id) WHERE s.series_id=?', (series.series_id,))}
        _require(all(p.name in {a + '.raw.json' for a in known_attempts} for p in ledger._path(series.series_id, 'unused').parent.glob('*.raw.json')))
        for segment in plan.leaves:
            row = connection.execute('SELECT * FROM bounded_extraction_segments WHERE segment_id=?', (segment.segment_id,)).fetchone()
            attempts = list(connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number', (segment.segment_id,)))
            result = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (segment.segment_id,)).fetchone()
            _require(segment.max_output_tokens == 24000 and (row['lease_expires_at'] is None or row['lease_expires_at'] <= time.time()), 'LEASE_BUSY')
            if row['state'] == 'SUCCEEDED_COMPLETE':
                _require(result is not None)
                accepted.append({'segment_id': segment.segment_id, 'record_sha256': result['record_sha256']})
                continue
            _require(row['state'] == 'FAILED' and result is None and state['state'] == 'FAILED')
            if attempts:
                _require(len(attempts) == 1 and attempts[0]['attempt_number'] == 1, 'STRICT_RECOVERY_ATTEMPT_LIMIT')
                failures.append(attempts[0]['attempt_id'])
                _require(attempts[0]['attempt_id'] == attempt_id and start['created_at'] <= attempts[0]['created_at'] <= stop['created_at'])
                matching = [e for e in events if e['event_type'] == 'SEGMENT_FAILED' and json.loads(e['body_json']).get('attempt_id') == attempt_id]
                _require(len(matching) == 1 and json.loads(matching[0]['body_json']).get('classification') == 'INVALID_SEGMENT_RESPONSE')
                target = (value, context, catalog, series, segment, attempts[0], matching[0])
            else:
                _require(all(e['event_type'] in ('SEGMENT_CREATED',) for e in events if json.loads(e['body_json']).get('segment_id', json.loads(e['body_json']).get('object_id')) == segment.segment_id))
                reopened.append({'series_id': series.series_id, 'segment_id': segment.segment_id, 'failure_event_sha256': series_failures[-1]['event_sha256']})
        loaded.append((series, plan, state, series_failures[-1] if series_failures else None))
    _require(target is not None and failures == [attempt_id] and len(accepted) == 1)
    value, context, catalog, series, segment, attempt, failure = target
    outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt_id,)).fetchone()
    _require(outcome is not None and outcome['external_outcome'] == outcome['classification'] == 'SUCCEEDED'
             and outcome['finish_reason'] == 'tool_calls' and type(outcome['output_tokens']) is int
             and 0 <= outcome['output_tokens'] < segment.max_output_tokens)
    envelope, body = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, attempt_id + '.raw.json', outcome))
    _require(envelope['http_status'] == 200 and envelope['finish_reason'] == 'tool_calls')
    diagnostic = failure_diagnostic(body, segment, catalog, context)
    original = output.segment_payload(value, context, catalog, series, segment)
    original_content = canonical(original).encode('utf-8')
    request = json.loads(attempt['request_json'])
    _require(request.get('provider_record_version') == output.V3_RECORD_VERSION
             and ledger._path(series.series_id, segment.segment_id + '.prompt.json').read_bytes() == original_content
             and hashlib.sha256(original_content).hexdigest() == request['payload_sha256'])
    from pro_a.config import load_config
    from .source_operations import build_source_providers
    providers = build_source_providers(load_config(worker.profile.phase4_config_path).llm, worker.jobs.profile,
                                      output_binding_version=output.V3_BINDING_VERSION)
    _require(identity(providers[output.OPERATION].configuration()) == attempt['configuration_sha256'], 'STRICT_RECOVERY_FROZEN_CONFIG_MISMATCH')
    root_index = [item[0].series_id for item in loaded].index(series.series_id)
    for i, (item, plan, state, series_failure) in enumerate(loaded):
        if state['state'] == 'FAILED':
            _require(i >= root_index and failure['created_at'] <= series_failure['created_at']
                     and json.loads(series_failure['body_json'])['code'] == ('BOUNDED_EXTRACTION_FAILED' if i == root_index else 'UPSTREAM_SERIES_FAILED'))
        pending = {r['segment_id'] for r in reopened if r['series_id'] == item.series_id}
        liability = sum(s.max_output_tokens for s in plan.leaves if s.segment_id in pending) + (24000 if item.series_id == series.series_id else 0)
        _require(state['provider_call_reservations'] + len(pending) + int(item.series_id == series.series_id) <= item.budget.max_provider_calls
                 and state['output_liability'] + liability <= item.budget.max_cumulative_output_tokens,
                 'STOP_STRICT_RECOVERY_BUDGET_INSUFFICIENT')
    frozen = Domains(worker.config).read(run_id, connection=connection)
    return {'run_id': run_id, 'series_id': series.series_id, 'segment_id': segment.segment_id,
        'failed_attempt_id': attempt_id, 'original_request_sha256': attempt['request_sha256'],
        'original_raw_sha256': outcome['artifact_sha256'], 'frozen_context_sha256': frozen['context_sha256'],
        'failure_event_sha256': failure['event_sha256'], 'blocked_event_sha256': stop['event_sha256'],
        'diagnostic': diagnostic, 'reopen': reopened, 'accepted': accepted,
        'provider_calls_before': sum(s['provider_call_reservations'] for _, _, s, _ in loaded)}

def assess_strict_recovery_compatibility(config, run_id, attempt_id, *, persist=False, historical_repository_root=None):
    from .retry_compatibility import assess_bounded_retry_compatibility
    return assess_bounded_retry_compatibility(config, run_id, attempt_id, persist=persist,
        bounded_strict_recovery=True, historical_repository_root=historical_repository_root)

def authorize_strict_same_run_recovery(service, run_id, failed_attempt_id, *, idempotency_key, worker_id, reason):
    _validate_retry_request(reason, idempotency_key)
    _require(isinstance(worker_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{3,64}', worker_id), 'INVALID_WORKER_ID')
    worker = frozen_bounded_service(service, run_id, failed_attempt_id)
    bindings = worker.output_batches.inputs(worker.get_run(run_id))
    ledger = worker.output_batches.ledger
    with worker.store.connect(operator_write=True) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        prior = _events(connection, run_id, COMMITTED, idempotency_key)
        if prior:
            _require(len(prior) == 1 and prior[0]['failed_attempt_id'] == failed_attempt_id and prior[0]['reason'] == reason, 'IDEMPOTENCY_CONFLICT')
            return {**prior[0]['result'], 'duplicate': True}
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        now = datetime.now(timezone.utc)
        _require(run is not None and (run['lease_owner'] is None or run['lease_expires_at'] <= now.isoformat()), 'LEASE_BUSY')
        proof = _assessment(worker, connection, run_id, failed_attempt_id, bindings)
        value, context, catalog, series = next(b for b in bindings if b[3].series_id == proof['series_id'])
        _, plan, _, _ = ledger._load(connection, series.series_id)
        segment = next(s for s in plan.segments if s.segment_id == proof['segment_id'])
        original = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?', (failed_attempt_id,)).fetchone()
        payload = regeneration_payload(output.segment_payload(value, context, catalog, series, segment), proof['frozen_context_sha256'], original['request_sha256'])
        content = canonical(payload).encode('utf-8')
        prompt_sha = hashlib.sha256(content).hexdigest()
        request = _request(ledger, series, segment, original, proof['frozen_context_sha256'], prompt_sha)
        request_sha = identity(request)
        new_id = ledger._attempt_id(segment.segment_id, 2, request_sha)
        grant = {**proof, 'contract': contract(), 'new_attempt_id': new_id, 'new_request_sha256': request_sha,
            'new_prompt_sha256': prompt_sha, 'idempotency_key': idempotency_key, 'reason': reason,
            'qualification_id': worker.runtime_compatibility.record['qualification_id'] if worker.runtime_compatibility else 'EXACT_RUNTIME'}
        if worker.runtime_compatibility is not None:
            evidence = json.loads(worker.runtime_compatibility.record['evidence_json'])
            qualified = evidence.get('strict_regeneration_request', {})
            _require(evidence.get('strict_recovery_contract') == contract()
                     and qualified.get('new_request_sha256') == request_sha
                     and qualified.get('new_prompt_sha256') == prompt_sha,
                     'STOP_STRICT_RECOVERY_RUNTIME_INCOMPATIBLE')
        connection.execute('UPDATE source_processing_runs SET fence=fence+1,lease_owner=?,lease_expires_at=? WHERE processing_run_id=?',
            (worker_id, (now + timedelta(seconds=worker.jobs.profile.timeout_seconds + 60)).isoformat(), run_id))
        _event(connection, series.series_id, AUTHORIZED_RECOVERY, **{k: v for k, v in grant.items() if k != 'series_id'})
        worker._event(connection, run_id, AUTHORIZED_RECOVERY, grant)
        persistence.checkpoint('strict_recovery_authorized')
        ledger._artifact(series.series_id, new_id + '.prompt.json', content)
        attempt = _record(connection, 'attempts', {'attempt_id': new_id, 'segment_id': segment.segment_id,
            'attempt_number': 2, 'request_json': canonical(request), 'request_sha256': request_sha,
            'configuration_sha256': original['configuration_sha256'], 'budget_identity': original['budget_identity'], 'created_at': _now()})
        connection.execute("UPDATE bounded_extraction_series SET provider_call_reservations=provider_call_reservations+1,output_liability=output_liability+24000 WHERE series_id=?", (series.series_id,))
        _event(connection, series.series_id, 'ATTEMPT_RESERVED', attempt_id=new_id, record_sha256=attempt['record_sha256'])
        persistence.checkpoint('strict_recovery_attempt_reserved')
        affected = {series.series_id} | {r['series_id'] for r in proof['reopen']}
        for sid in affected:
            connection.execute("UPDATE bounded_extraction_series SET state='OPEN',fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE series_id=?", (_now(), sid))
        for item in [{'series_id': series.series_id, 'segment_id': segment.segment_id}] + proof['reopen']:
            connection.execute("UPDATE bounded_extraction_segments SET state='PLANNED',fence=fence+1,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE segment_id=?", (_now(), item['segment_id']))
            _event(connection, item['series_id'], REOPENED, segment_id=item['segment_id'], root_attempt_id=failed_attempt_id, idempotency_key=idempotency_key)
        persistence.checkpoint('strict_recovery_frontier_reopened')
        result = {'status': 'AUTHORIZED', 'contract_version': VERSION, 'provider_calls': 0,
            'failed_attempt_id': failed_attempt_id, 'new_attempt_id': new_id, 'new_attempt_number': 2,
            'request_sha256': request_sha, 'prompt_sha256': prompt_sha, 'upstream_unattempted_count': len(proof['reopen'])}
        worker._event(connection, run_id, COMMITTED, {'failed_attempt_id': failed_attempt_id, 'reason': reason, 'idempotency_key': idempotency_key, 'result': result})
        connection.execute("UPDATE source_processing_runs SET state='EXTRACTION_PROCESSING',stage='WHOLE_PIECE_OUTPUT_DECOMPOSITION',error_code=NULL,retry_safe=0,manual_recovery_required=0,ended_at=NULL,updated_at=?,lease_owner=NULL,lease_expires_at=NULL WHERE processing_run_id=?", (_now(), run_id))
        worker._event(connection, run_id, 'SOURCE_STATE_CHANGED', {'state': 'EXTRACTION_PROCESSING', 'stage': 'WHOLE_PIECE_OUTPUT_DECOMPOSITION', 'recovery_contract': VERSION})
    persistence.checkpoint('strict_recovery_committed')
    return {**result, 'duplicate': False}
