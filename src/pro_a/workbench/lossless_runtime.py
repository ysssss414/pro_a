"""Explicit schema12 Aggregate/Replay/Review/admission integration."""
import hashlib
import json
from dataclasses import asdict
from threading import Lock

from pro_a import claim_observations as observations
from pro_a import lossless_aggregate as aggregate
from pro_a import output_decomposition as output
from pro_a.analyzer import normalize_ws
from pro_a.evidence_binding import identity
from .artifacts import Artifacts
from .bounded_extraction_persistence import canonical, checkpoint
from .bounded_extraction_store import _event, _record, _now, _require

AUTHORIZED = 'LOSSLESS_AGGREGATE_POLICY_AUTHORIZED'
REVIEW_DURABLE = 'LOSSLESS_NATIVE_REVIEW_DURABLE'
_VERIFIED_AGGREGATES = {}
_CACHE_LOCK = Lock()


def policy(connection, series_id):
    events = list(connection.execute('SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type=?',
        (series_id, AUTHORIZED)))
    _require(len(events) <= 1, 'CONFLICTING_LOSSLESS_AUTHORIZATION')
    return json.loads(events[0][0]) if events else None


def frozen_input(ledger, connection, series):
    rows = connection.execute("SELECT * FROM source_cloud_inputs WHERE processing_run_id=? AND operation_kind='SOURCE_ANALYSIS_PIECE' ORDER BY ordinal",
        (series.processing_run_id,)).fetchall()
    matches = []
    for row in rows:
        content = Artifacts(ledger.config).resolve(row['artifact_relative']).read_bytes()
        _require(hashlib.sha256(content).hexdigest() == row['sha256'], 'BOUNDED_INPUT_ARTIFACT_MISMATCH')
        document = json.loads(content)
        value = document['payload']
        if value.get('series_id') != series.series_id:
            continue
        _require(document['payload_sha256'] == identity(value)
            and document['processing_run_id'] == series.processing_run_id
            and canonical(document['checkpoint']) == row['checkpoint_json'], 'BOUNDED_INPUT_ARTIFACT_MISMATCH')
        context, catalog, restored = output.restore_input(value, document['source_sha256'], series.processing_run_id, row['ordinal'])
        _require(restored == series, 'BOUNDED_SERIES_INPUT_BINDING_CONFLICT')
        matches.append((document['source_id'], context, catalog))
    _require(len(matches) == 1, 'BOUNDED_SERIES_INPUT_BINDING_CONFLICT')
    return matches[0]


def accepted_results(ledger, connection, series, plan):
    results = []
    for leaf in plan.leaves:
        row = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (leaf.segment_id,)).fetchone()
        state = connection.execute('SELECT state FROM bounded_extraction_segments WHERE segment_id=?', (leaf.segment_id,)).fetchone()
        _require(row is not None and row['result_type'] == 'COMPLETE' and state[0] == 'SUCCEEDED_COMPLETE', 'SERIES_COVERAGE_INCOMPLETE')
        results.append(ledger._result(series.series_id, row))
    return tuple(results)


def resolution(ledger, connection, series):
    grant = policy(connection, series.series_id)
    _require(grant is not None and grant['aggregate_version'] == aggregate.VERSION, 'LOSSLESS_AUTHORIZATION_REQUIRED')
    document = json.loads(ledger._read_artifact(series.series_id, 'metadata-resolution.json', grant))
    _require(document['identity'] == grant['resolution_identity'], 'METADATA_AUTHORITY_IDENTITY_MISMATCH')
    return document


def finalize(ledger, connection, series, plan, results, catalog, context):
    authority = resolution(ledger, connection, series)
    document = aggregate.build_aggregate(authority['scope']['source_id'], series, plan, results, catalog, context, authority)
    relative, sha = ledger._artifact(series.series_id, 'aggregate.json', canonical(document).encode('utf-8'))
    checkpoint('lossless_aggregate_artifact_durable')
    semantic = {'series_id': series.series_id, 'coverage_sha256': document['coverage_sha256'],
        'ordered_result_shas_json': canonical(document['ordered_segment_result_sha256']),
        'aggregate_wire_sha256': document['identity'], 'artifact_relative': relative, 'artifact_sha256': sha}
    final = _record(connection, 'series_results', {**semantic, 'result_sha256': identity(semantic), 'created_at': _now()})
    connection.execute("UPDATE bounded_extraction_series SET state='SUCCEEDED_COMPLETE',updated_at=? WHERE series_id=?", (_now(), series.series_id))
    _event(connection, series.series_id, 'SERIES_COVERAGE_CLOSED', coverage_sha256=document['coverage_sha256'])
    _event(connection, series.series_id, 'SERIES_RESULT_DURABLE', result_sha256=final['result_sha256'], aggregate_version=aggregate.VERSION,
        observation_ledger_identity=document['observation_ledger']['identity'])
    return final


def verify_final(ledger, connection, series, plan, row, document):
    source_id, context, catalog = frozen_input(ledger, connection, series)
    authority = resolution(ledger, connection, series)
    results = accepted_results(ledger, connection, series, plan)
    # _load still verifies every durable event/record/file on every read. Cache
    # only the pure reconstruction, keyed by all its inputs, never by a path or
    # a self-asserted document identity. Bound memory across completed Sources.
    key = identity({'source_id': source_id, 'series': asdict(series), 'plan': asdict(plan),
        'results': [asdict(r) for r in results], 'catalog': asdict(catalog),
        'context': asdict(context), 'authority': authority})
    expected = _VERIFIED_AGGREGATES.get(key)
    if expected is None:
        expected = aggregate.build_aggregate(source_id, series, plan, results, catalog, context, authority)
        with _CACHE_LOCK:
            if key not in _VERIFIED_AGGREGATES and len(_VERIFIED_AGGREGATES) >= 8:
                _VERIFIED_AGGREGATES.pop(next(iter(_VERIFIED_AGGREGATES)))
            _VERIFIED_AGGREGATES[key] = expected
    _require(document == expected and document['identity'] == row['aggregate_wire_sha256']
        and document['coverage_sha256'] == row['coverage_sha256']
        and canonical(document['ordered_segment_result_sha256']) == row['ordered_result_shas_json'], 'AGGREGATE_IDENTITY_MISMATCH')
    semantic = {k: row[k] for k in ('series_id', 'coverage_sha256', 'ordered_result_shas_json',
        'aggregate_wire_sha256', 'artifact_relative', 'artifact_sha256')}
    _require(identity(semantic) == row['result_sha256'], 'SERIES_RESULT_IDENTITY_MISMATCH')
    return dict(row)


def replay_if_authorized(runner, run, cfg):
    from .bounded_source_analysis import BoundedExtractionReplay
    bindings = runner.inputs(run)
    with runner.ledger._connection() as connection:
        grants = [policy(connection, b[3].series_id) for b in bindings]
    if not any(grants):
        return None
    _require(all(grants), 'LOSSLESS_SOURCE_POLICY_INCOMPLETE')
    responses, metadata, candidates = {}, {}, {}
    authority_identity = None
    for value, context, catalog, series in bindings:
        document = runner.ledger.aggregate(series.series_id)  # Rebuild-verified by _load.
        _require(document.get('version') == aggregate.VERSION, 'LOSSLESS_SOURCE_POLICY_INCOMPLETE')
        authority_identity = authority_identity or document['source_metadata_resolution_identity']
        _require(authority_identity == document['source_metadata_resolution_identity'], 'SOURCE_METADATA_AUTHORITY_CONFLICT')
        for original in document['observation_ledger']['original_segment_results']:
            for candidate in json.loads(original['wire_json']).get('node_candidates', []):
                key = normalize_ws(candidate['canonical_name']).lower()
                _require(key not in candidates or candidates[key] == candidate, 'NODE_CANDIDATE_CONFLICT')
                candidates[key] = candidate
        key = value['native']['user_prompt_sha256']
        _require(key not in responses, 'BOUNDED_NATIVE_PROMPT_MISMATCH')
        responses[key] = document['native_input']
        metadata[key] = {'execution_mode': aggregate.REPLAY_VERSION, 'series_id': series.series_id,
            'aggregate_identity': document['identity'], 'observation_ledger_identity': document['observation_ledger']['identity'],
            'native_projection_authoritative': False, 'attempts_used': runner.ledger.read(series.series_id)[3].provider_call_count}
    return BoundedExtractionReplay(cfg, responses, metadata)


def guard_native_admission(service, run, native_root, semantic_document, *, worker_id, fence):
    """Durable complete Review first, then all-or-nothing admission before Job creation."""
    from .source_operations import SourceOperationError
    bindings = service.output_batches.inputs(run)
    ledger = service.output_batches.ledger
    with ledger._connection() as connection:
        grants = [policy(connection, b[3].series_id) for b in bindings]
    if not any(grants):
        return
    _require(all(grants), 'LOSSLESS_SOURCE_POLICY_INCOMPLETE')
    from pro_a.phase4_orchestration import _compatible
    from pro_a.phase4_retry import RetryPolicy
    from pro_a.config import load_config
    from .bounded_resume import _owned
    with service.store.connect() as connection:
        native = connection.execute('SELECT native_execution_id FROM source_processing_runs WHERE processing_run_id=?',
            (run['processing_run_id'],)).fetchone()
    _compatible(native_root, native[0], load_config(service.profile.phase4_config_path),
        RetryPolicy.FORBID_ALL, runtime_compatibility=service.runtime_compatibility)
    documents = [ledger.aggregate(b[3].series_id) for b in bindings]
    manifest = observations.combine_observation_ledgers([d['observation_ledger'] for d in documents])
    engine = native_root / 'engine'
    raw = json.loads((engine / 'extraction/raw_analysis.json').read_text(encoding='utf-8'))
    bundle = json.loads((engine / 'extraction/extraction_bundle.json').read_text(encoding='utf-8'))
    _require(bundle['source']['sha256'] == run['source_sha256']
        and semantic_document['source_sha256'] == run['source_sha256']
        and semantic_document['payload_sha256'] == identity(semantic_document['payload']), 'NATIVE_SOURCE_IDENTITY_MISMATCH')
    projection = observations.build_native_projection(manifest, raw['normalized_source_analysis']['claims'])
    review = observations.private_review_artifact(manifest, projection)
    inputs = semantic_document['payload']['claims']
    admission = observations.bind_semantic_inputs(manifest, projection, bundle['claims'], inputs)
    with ledger._connection(True) as connection:
        _owned(connection, run['processing_run_id'], worker_id, fence)
        sid = bindings[0][3].series_id
        relative, digest = ledger._artifact(sid, 'review-' + review['identity'] + '.json', canonical(review).encode('utf-8'))
        ar, ash = ledger._artifact(sid, 'admission-' + admission['identity'] + '.json', canonical(admission).encode('utf-8'))
        event = {'review_identity': review['identity'], 'artifact_relative': relative, 'artifact_sha256': digest,
            'admission_identity': admission['identity'], 'admission_artifact_relative': ar, 'admission_artifact_sha256': ash,
            'ordered_aggregate_identities': [d['identity'] for d in documents],
            'native_claims_sha256': projection['native_claims_sha256'], 'semantic_payload_sha256': semantic_document['payload_sha256'],
            'production_admission': 'NOT_AUTHORIZED'}
        existing = [json.loads(r[0]) for r in connection.execute('SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type=?',
            (run['processing_run_id'], REVIEW_DURABLE))]
        _require(not existing or existing == [event], 'LOSSLESS_NATIVE_REVIEW_CONFLICT')
        checkpoint('lossless_review_artifact_durable')
        if not existing:
            service._event(connection, run['processing_run_id'], REVIEW_DURABLE, event)
    checkpoint('lossless_review_committed')
    try:
        observations.guard_semantic_inputs(manifest, projection, admission, inputs)
    except observations.ObservationError as error:
        raise SourceOperationError(str(error)) from None
