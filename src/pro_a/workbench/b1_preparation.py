"""Immutable request preparation on the existing ledger; no Attempt or budget authority."""
from dataclasses import replace
import hashlib
import json

from pro_a import b1_extraction as b1, output_decomposition as output
from pro_a.config import load_config
from pro_a.evidence_binding import identity
from .bounded_extraction_persistence import canonical
from .bounded_extraction_store import _event
from .config import BoundaryError
from . import output_qualification

VERSION = 'b1-request-preparation-v1'
EVENT = 'B1_REQUEST_PREPARED'


def require(value, code):
    if not value:
        raise BoundaryError(code)


def _basis(worker, run):
    require(worker.output_batches.binding_version == b1.BINDING, 'B1_PREPARATION_CONTRACT_REQUIRED')
    bindings = worker.output_batches.inputs(run)
    require(len(bindings) == 1, 'B1_SINGLE_PIECE_REQUIRED')
    value, context, catalog, series = bindings[0]
    _, plan, state, _ = worker.output_batches.ledger.read(series.series_id)
    require(len(plan.leaves) == 1 and state['state'] == 'OPEN', 'B1_PREPARATION_SERIES_NOT_OPEN')
    return value, context, catalog, series, plan.leaves[0]


def _unattempted(connection, series_id):
    require(not connection.execute('''SELECT 1 FROM bounded_extraction_attempts a
        JOIN bounded_extraction_segments s USING(segment_id) WHERE s.series_id=?''', (series_id,)).fetchone(),
        'B1_PREPARATION_AFTER_ATTEMPT_FORBIDDEN')


def _records(connection, series_id):
    return [json.loads(r[0]) for r in connection.execute(
        'SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type=? ORDER BY sequence',
        (series_id, EVENT))]


def prepare(service, run_id):
    worker = output_qualification.frozen_worker(service, run_id)
    run = worker.get_run(run_id)
    value, context, catalog, series, segment = _basis(worker, run)
    require(value['native'].get('source_scope') is not None, 'B1_EXPLICIT_SCOPE_REQUIRED')
    cfg = replace(load_config(worker.profile.phase4_config_path).llm, max_output_tokens=12000,
                  max_retries=0, timeout_seconds=worker.jobs.profile.timeout_seconds)
    # Construction/prepare never invokes transport, availability or credentials.
    provider = output.OutputBatchProvider(cfg, binding_version=b1.BINDING,
                                         b1_counter=b1.LocalCounter(worker.profile.phase4_config_path))
    payload = worker.output_batches.segment_payload(value, context, catalog, series, segment)
    payload['request_wire_json'] = json.dumps(payload['request'], allow_nan=False)
    payload = provider.prepare_payload(payload)
    configuration = provider.configuration()
    body = {'version': VERSION, 'processing_run_id': run_id, 'source_sha256': run['source_sha256'],
        'series_id': series.series_id, 'series_sha256': series.series_sha256,
        'segment_id': segment.segment_id, 'segment_sha256': segment.segment_sha256,
        'input_sha256': identity(value), 'runtime_sha256': run['runtime_identity']['runtime_sha256'],
        'configuration_sha256': identity(configuration), 'configuration': configuration,
        'payload_json': json.dumps(payload, ensure_ascii=False, allow_nan=False),
        'wire_body_sha256': hashlib.sha256(payload['request_wire_json'].encode('utf8')).hexdigest(),
        'request_object_sha256': identity(payload['request']),
        'budget_reservation_authority': False, 'dispatch_authority': False}
    preparation_sha = identity(body)
    ledger = worker.output_batches.ledger
    with ledger._connection(True) as connection:
        _unattempted(connection, series.series_id)
        records = _records(connection, series.series_id)
        previous = next((r for r in records if r['preparation_sha256'] == preparation_sha), None)
        relative, digest = ledger._artifact(series.series_id, 'prepared-' + preparation_sha + '.json',
                                            canonical(body).encode('utf8'))
        event = {'version': VERSION, 'preparation_sha256': preparation_sha,
                 'artifact_relative': relative, 'artifact_sha256': digest}
        require(previous is None or previous == event, 'B1_PREPARATION_IDEMPOTENCY_CONFLICT')
        if previous is None:
            _event(connection, series.series_id, EVENT, **event)
    return {**event, 'wire_body_sha256': body['wire_body_sha256'],
            'request_object_sha256': body['request_object_sha256'],
            'input_tokens': payload['request_token_preflight']['input_tokens'],
            'budget_reserved': False, 'dispatched': False}


def frozen_payload(worker, run, value, context, catalog, series, segment, provider):
    """Dispatch consumes exactly the latest prepared wire, with fresh frozen guards."""
    ledger = worker.output_batches.ledger
    with ledger._connection() as connection:
        records = _records(connection, series.series_id)
    require(bool(records), 'B1_REQUEST_NOT_PREPARED')
    event = records[-1]
    path = worker.artifacts.resolve(event['artifact_relative'])
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == event['artifact_sha256'], 'B1_PREPARED_ARTIFACT_DRIFT')
    body = json.loads(raw)
    require(identity(body) == event['preparation_sha256'] and body['version'] == VERSION
        and body['processing_run_id'] == run['processing_run_id']
        and body['source_sha256'] == run['source_sha256']
        and body['runtime_sha256'] == run['runtime_identity']['runtime_sha256']
        and body['input_sha256'] == identity(value) and body['series_sha256'] == series.series_sha256
        and body['segment_sha256'] == segment.segment_sha256
        and body['configuration_sha256'] == identity(provider.configuration()), 'B1_PREPARED_IDENTITY_DRIFT')
    payload = json.loads(body['payload_json'])
    expected = worker.output_batches.segment_payload(value, context, catalog, series, segment)
    expected['request_wire_json'] = json.dumps(expected['request'], allow_nan=False)
    expected = provider.prepare_payload(expected)
    require(payload == expected and body['wire_body_sha256'] == hashlib.sha256(
        payload['request_wire_json'].encode('utf8')).hexdigest(), 'B1_PREPARED_REQUEST_DRIFT')
    return payload
