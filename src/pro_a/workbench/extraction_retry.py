"""Explicit, append-only retry lineage over frozen Source extraction jobs."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields
from pathlib import Path
from uuid import uuid4

from pro_a.cloud_contract import budget_for_operation, canonical, digest, now, operation_contract
from pro_a.production_promotion import sha256_file
from .cloud_jobs import CloudProfile, JobError
from .config import BoundaryError, checked_path
from .domains import Domains
from .review_store import schema_version
from .store import Store


MALFORMED_JSON_RETRY_POLICY_VERSION = "malformed-provider-json-same-batch-retry-v1"
MALFORMED_JSON_RETRY_REASON = "MALFORMED_PROVIDER_JSON"
MAX_MALFORMED_JSON_RETRIES = 1
_BOUNDED_RETRY_EVENT = "MALFORMED_PROVIDER_JSON_RETRY_AUTHORIZED"


def installed(connection):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_retries'").fetchone() is not None


def prepare_extraction_retries(config):
    """Operator-only additive extension; never invoked by API startup or reads."""
    config.validate()
    if config.mode != 'PRIVATE':
        raise BoundaryError('PRIVATE_SOURCE_MODE_REQUIRED')
    with Store(config).connect(operator_write=True) as connection:
        connection.execute('BEGIN IMMEDIATE')
        if schema_version(connection) not in ('9', '10', '11', '12'):
            raise BoundaryError('DOMAIN_SCHEMA_REQUIRED')
        if installed(connection):
            return {'status': 'ALREADY_PREPARED', 'extension': 'extraction-retry-v1'}
        connection.execute('''CREATE TABLE extraction_retries(
            attempt_id TEXT PRIMARY KEY,
            processing_run_id TEXT NOT NULL REFERENCES source_processing_runs(processing_run_id),
            root_job_id TEXT NOT NULL REFERENCES cloud_jobs(job_id),
            job_id TEXT NOT NULL UNIQUE REFERENCES cloud_jobs(job_id),
            retry_of_attempt_id TEXT NOT NULL UNIQUE REFERENCES cloud_attempts(attempt_id),
            attempt_number INTEGER NOT NULL CHECK(attempt_number > 1),
            retry_reason TEXT NOT NULL CHECK(length(retry_reason) BETWEEN 1 AND 1000),
            trigger_type TEXT NOT NULL CHECK(trigger_type='EXPLICIT_RETRY'),
            idempotency_key TEXT NOT NULL UNIQUE,
            context_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(root_job_id,attempt_number))''')
        for action in ('UPDATE', 'DELETE'):
            connection.execute(f'''CREATE TRIGGER extraction_retries_{action.lower()}_forbidden
                BEFORE {action} ON extraction_retries
                BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END''')
    return {'status': 'PREPARED', 'extension': 'extraction-retry-v1'}


def for_job(connection, job_id):
    if not installed(connection):
        return None
    return connection.execute('SELECT * FROM extraction_retries WHERE job_id=?', (job_id,)).fetchone()


def effective_job_ids(connection, run_id, operation):
    rows = connection.execute('SELECT job_id FROM source_processing_jobs WHERE processing_run_id=? '
                              'AND operation_kind=? ORDER BY ordinal', (run_id, operation)).fetchall()
    result = []
    for row in rows:
        retry = (connection.execute('SELECT job_id FROM extraction_retries WHERE root_job_id=? '
                                    'ORDER BY attempt_number DESC LIMIT 1', (row[0],)).fetchone()
                 if installed(connection) else None)
        result.append(retry[0] if retry else row[0])
    return result


def frozen_cloud(row):
    """Reconstruct only complete, self-consistent persisted execution settings."""
    from .source_operations import SourceOperationError
    try:
        value = json.loads(row['configuration_json'])
        args = {field.name: value[field.name] for field in fields(CloudProfile)}
        args['accepted_model_aliases'] = tuple(args['accepted_model_aliases'])
        profile = CloudProfile(**args)
        profile.validate()
        if canonical(profile.public_identity()) != row['configuration_json']:
            raise ValueError()
        budget = budget_for_operation(row['operation_kind'], profile.max_total_tokens)
        prompt = json.loads(row['prompt_json'])
        from ..whole_piece_compact import RESPONSE_VERSION
        whole_piece = prompt.get('operation_schema_version') in (
            'whole-piece-compact-source-analysis-response-v1', RESPONSE_VERSION)
        for field in fields(CloudProfile):
            if field.name == 'provider_adapter_version':
                expected_adapter = profile.adapter_for_operation(row['operation_kind'])
                if (row['operation_kind'] == 'SOURCE_ANALYSIS_PIECE'
                        and profile.provider != 'DETERMINISTIC_FAKE'
                        and prompt.get('operation_schema_version') == 'source-analysis-piece-v1'):
                    expected_adapter = 'source-analysis-piece-adapter-v2'
                if row[field.name] != expected_adapter:
                    raise ValueError()
                continue
            stored = (json.loads(row['accepted_model_aliases_json'])
                      if field.name == 'accepted_model_aliases' else row[field.name])
            expected = budget[field.name] if field.name in budget else value[field.name]
            if whole_piece and field.name in ('max_calls', 'max_attempts'):
                expected = 1
            if stored != expected:
                raise ValueError()
        if (row['retry_owner'] != value['retry_owner']
                or row['retry_policy_id'] != value['retry_policy_id']):
            raise ValueError()
        if row['configuration_sha256'] != value['configuration_sha256']:
            raise ValueError()
        return profile
    except (KeyError, TypeError, ValueError, JobError):
        raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE') from None


def frozen_service(service, run_id, *, required=False, failed_attempt_id=None):
    """Use frozen cloud values and the original, digest-guarded local config path.

    A hash-only config cannot reconstruct missing/edited TOML. Fail closed in
    that case; never manufacture a replacement configuration from current values.
    Runtime compatibility remains strict unless an exact-scope, independently
    validated Stage 7.2C qualification record is present.
    """
    from .source_operations import SourceOperations, SourceProfile, SourceOperationError
    from .lossless_recovery import load_worker
    lossless = load_worker(service, run_id)
    if lossless is not None:
        return lossless
    with service.store.connect() as connection:
        if not required and (not installed(connection) or not connection.execute(
                'SELECT 1 FROM extraction_retries WHERE processing_run_id=?', (run_id,)).fetchone()):
            return service
        frozen = Domains(service.config).read(run_id, connection=connection)
        if frozen is None:
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE')
        run = connection.execute(
            'SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,),
        ).fetchone()
        binding = connection.execute('SELECT config_path FROM domain_run_bindings WHERE processing_run_id=?',
                                     (run_id,)).fetchone()
        row = connection.execute('SELECT j.* FROM cloud_jobs j JOIN source_processing_jobs s ON s.job_id=j.job_id '
                                 "WHERE s.processing_run_id=? AND s.operation_kind='SOURCE_ANALYSIS_PIECE' ORDER BY s.ordinal LIMIT 1",
                                 (run_id,)).fetchone()
        if row is None:
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        profile = frozen_cloud(row)
        if profile.public_identity() != frozen['basis']['model_configuration']:
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE')
        try:
            ref = json.loads(binding['config_path'])
            source_profile = SourceProfile(Path(ref['path']), ref['max_pdf_bytes'], ref['max_extraction_pieces'])
            worker = SourceOperations(service.config, source_profile, profile)
            from .domains import config_digest
            limits = {'max_pdf_bytes': source_profile.max_pdf_bytes,
                      'max_extraction_pieces': source_profile.max_extraction_pieces}
            if config_digest(source_profile.phase4_config_path, limits) != frozen['basis']['config_sha256']:
                raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE')
        except (KeyError, ValueError, OSError, BoundaryError, SourceOperationError):
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE') from None
        stored_runtime = json.loads(row['runtime_json'])
        current_runtime = worker.jobs.current_runtime()
        if canonical(stored_runtime) != canonical(current_runtime):
            attempt_id = failed_attempt_id
            if attempt_id is None:
                lineage = connection.execute(
                    'SELECT retry_of_attempt_id FROM extraction_retries WHERE processing_run_id=? '
                    'ORDER BY attempt_number DESC LIMIT 1', (run_id,),
                ).fetchone()
                attempt_id = lineage['retry_of_attempt_id'] if lineage else None
            failed = (connection.execute('SELECT job_id FROM cloud_attempts WHERE attempt_id=?',
                                         (attempt_id,)).fetchone() if attempt_id else None)
            from .retry_compatibility import load_qualification, RetryCompatibilityError
            try:
                token = (load_qualification(
                    connection, run_id=run_id, failed_attempt_id=attempt_id,
                    source_id=run['source_id'] if run else '',
                    failed_job_id=failed['job_id'] if failed else '',
                    historical_runtime_sha256=row['runtime_sha256'],
                    target_runtime=current_runtime,
                    historical_context_sha256=frozen['context_sha256'],
                ) if attempt_id and failed else None)
            except RetryCompatibilityError:
                raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE') from None
            if token is None:
                raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE')
            worker = SourceOperations(
                service.config, source_profile, profile, runtime_compatibility=token,
            )
        try:
            Domains(service.config).guard(
                run_id, worker.jobs, worker.profile,
                runtime_compatibility=worker.runtime_compatibility,
            )
        except Exception as error:
            code = str(error)
            if code in ('PROCESSING_RUN_CONTEXT_DRIFT', 'DOMAIN_RUN_CONTEXT_DRIFT'):
                raise SourceOperationError(code) from None
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE') from None
        return worker


def _validate_retry_request(retry_reason, idempotency_key):
    from .source_operations import SourceOperationError
    if (not isinstance(retry_reason, str) or not 1 <= len(retry_reason) <= 1000
            or retry_reason != retry_reason.strip()
            or retry_reason.splitlines() != [retry_reason]
            or any(ord(c) < 32 or ord(c) == 127 or c in '<>' for c in retry_reason)
            or re.search(r'(?i)(bearer\s+|sk-[a-z0-9]{8}|(?:api[_ -]?key|token|cookie|authorization)\s*[:=])', retry_reason)):
        raise SourceOperationError('INVALID_RETRY_REASON', 422)
    if not isinstance(idempotency_key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{15,127}', idempotency_key):
        raise SourceOperationError('INVALID_IDEMPOTENCY_KEY', 422)


def bounded_frozen_components(config, connection, run):
    """Reconstruct the exact bounded worker configuration without credentials."""
    from .source_operations import SourceProfile, SourceOperationError
    frozen = Domains(config).read(run['processing_run_id'], connection=connection)
    binding = connection.execute(
        'SELECT config_path FROM domain_run_bindings WHERE processing_run_id=?',
        (run['processing_run_id'],),
    ).fetchone()
    source = connection.execute(
        'SELECT * FROM private_sources WHERE source_id=?', (run['source_id'],),
    ).fetchone()
    try:
        if frozen is None or binding is None or source is None:
            raise ValueError()
        ref = json.loads(binding['config_path'])
        source_profile = SourceProfile(
            Path(ref['path']), ref['max_pdf_bytes'], ref['max_extraction_pieces'],
        )
        source_profile.validate()
        value = frozen['basis']['model_configuration']
        args = {field.name: value[field.name] for field in fields(CloudProfile)}
        args['accepted_model_aliases'] = tuple(args['accepted_model_aliases'])
        profile = CloudProfile(**args)
        profile.validate()
        from .domains import config_digest
        limits = {'max_pdf_bytes': source_profile.max_pdf_bytes,
                  'max_extraction_pieces': source_profile.max_extraction_pieces}
        if (profile.public_identity() != value
                or config_digest(source_profile.phase4_config_path, limits)
                != frozen['basis']['config_sha256']
                or frozen['basis']['source_id'] != run['source_id']
                or sha256_file(checked_path(config.artifact_root / source['storage_relative']))
                != source['source_sha256']):
            raise ValueError()
        return source_profile, profile, frozen, source
    except (KeyError, TypeError, ValueError, OSError, BoundaryError, JobError):
        raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE') from None


def frozen_bounded_service(service, run_id, failed_attempt_id):
    """Build a bounded retry worker, requiring an exact-scope token on drift."""
    from .source_operations import SourceOperations, SourceOperationError
    with service.store.connect() as connection:
        run = connection.execute(
            'SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,),
        ).fetchone()
        if run is None:
            raise SourceOperationError('PROCESSING_RUN_NOT_FOUND', 404)
        attempt = connection.execute(
            'SELECT a.*,s.series_id FROM bounded_extraction_attempts a '
            'JOIN bounded_extraction_segments s ON s.segment_id=a.segment_id '
            'WHERE a.attempt_id=?', (failed_attempt_id,),
        ).fetchone()
        if attempt is None:
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        source_profile, profile, frozen, _ = bounded_frozen_components(
            service.config, connection, run,
        )
        worker = SourceOperations(service.config, source_profile, profile)
        historical = json.loads(run['runtime_json'])
        current = worker.jobs.current_runtime()
        token = None
        if canonical(historical) != canonical(current):
            from .retry_compatibility import load_bounded_qualification, RetryCompatibilityError
            try:
                token = load_bounded_qualification(
                    connection, run_id=run_id, failed_attempt_id=failed_attempt_id,
                    segment_id=attempt['segment_id'], series_id=attempt['series_id'],
                    source_id=run['source_id'],
                    historical_runtime_sha256=run['runtime_sha256'],
                    target_runtime=current,
                    historical_context_sha256=frozen['context_sha256'],
                )
            except RetryCompatibilityError:
                raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE') from None
            if token is None:
                raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE')
            worker = SourceOperations(
                service.config, source_profile, profile, runtime_compatibility=token,
            )
        try:
            Domains(service.config).guard(
                run_id, worker.jobs, worker.profile,
                runtime_compatibility=worker.runtime_compatibility,
            )
            from pro_a.config import load_config
            from pro_a.phase4_orchestration import _compatible
            from pro_a.phase4_retry import RetryPolicy
            _compatible(
                worker._native_root(run), run['native_execution_id'],
                load_config(worker.profile.phase4_config_path), RetryPolicy.FORBID_ALL,
                runtime_compatibility=worker.runtime_compatibility,
            )
        except Exception:
            raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE') from None
        return worker


def _bounded_retry_events(connection, *, run_id=None, series_id=None):
    where, args = ["e.event_type=?"], [_BOUNDED_RETRY_EVENT]
    if run_id is not None:
        where.append("s.processing_run_id=?")
        args.append(run_id)
    if series_id is not None:
        where.append("e.series_id=?")
        args.append(series_id)
    rows = connection.execute(
        "SELECT e.series_id,e.body_json FROM bounded_extraction_events e "
        "JOIN bounded_extraction_series s ON s.series_id=e.series_id WHERE "
        + " AND ".join(where) + " ORDER BY e.series_id,e.sequence", tuple(args),
    )
    result = []
    for row in rows:
        value = json.loads(row[1])
        value["series_id"] = row[0]
        result.append(value)
    return result


def _json_syntax_diagnostic(body):
    try:
        text = body.decode('utf-8', errors='strict')
        json.loads(text)
    except json.JSONDecodeError as error:
        return {
            'failure_class': 'PROVIDER_MALFORMED_STRUCTURED_OUTPUT',
            'parser_class': 'JSON_SYNTAX_ERROR',
            'message': error.msg, 'line': error.lineno, 'column': error.colno,
            'char_offset': error.pos,
            'byte_offset': len(text[:error.pos].encode('utf-8')),
        }
    except UnicodeError:
        return None
    return None


def bounded_attempt_for_dispatch(ledger, segment_id, owner, fence, *,
                                 payload_sha256, configuration_sha256):
    """Select only an operator-authorized retry; otherwise preserve attempt 1."""
    from pro_a.evidence_binding import identity
    from .bounded_extraction_store import _require
    with ledger._connection() as connection:
        row, (series, plan, _, _) = ledger._segment_row(connection, segment_id)
        ledger._owned(row, owner, fence)
        segment = next(item for item in plan.segments if item.segment_id == segment_id)
        latest = connection.execute(
            'SELECT * FROM bounded_extraction_attempts WHERE segment_id=? '
            'ORDER BY attempt_number DESC LIMIT 1', (segment_id,),
        ).fetchone()
        if latest is not None and latest['attempt_number'] > 1:
            if 'regeneration_contract_version' in json.loads(latest['request_json']):
                from .strict_recovery import expected_attempt_request
                from .lossless_recovery import EVIDENCE_REQUEST, evidence_expected_request
                if json.loads(latest['request_json'])['regeneration_contract_version'] == EVIDENCE_REQUEST:
                    expected_attempt_request = evidence_expected_request
                expected = expected_attempt_request(ledger, connection, series, segment, latest)
                _require(json.loads(latest['request_json']) == expected
                         and latest['request_sha256'] == identity(expected)
                         and expected['payload_sha256'] == payload_sha256
                         and latest['configuration_sha256'] == configuration_sha256,
                         'STRICT_RECOVERY_REQUEST_IDENTITY_MISMATCH')
                return dict(latest)
            events = [event for event in _bounded_retry_events(
                connection, series_id=series.series_id,
            ) if event['new_attempt_id'] == latest['attempt_id']]
            expected = ledger._request(
                series, segment, payload_sha256, configuration_sha256,
            )
            _require(len(events) == 1, 'RETRY_AUTHORIZATION_REQUIRED')
            _require(latest['attempt_number'] == 1 + MAX_MALFORMED_JSON_RETRIES,
                     'RETRY_LIMIT_EXCEEDED')
            _require(json.loads(latest['request_json']) == expected
                     and latest['request_sha256'] == identity(expected),
                     'RETRY_IDENTITY_MISMATCH')
            return dict(latest)
        if latest is not None:
            outcome = connection.execute(
                'SELECT 1 FROM bounded_extraction_outcomes WHERE attempt_id=?',
                (latest['attempt_id'],),
            ).fetchone()
            if outcome:
                raise BoundaryError('RETRY_AUTHORIZATION_REQUIRED')
    return ledger.reserve_attempt(
        segment_id, owner, fence, attempt_number=1,
        payload_sha256=payload_sha256,
        configuration_sha256=configuration_sha256,
    )


def retry_failed_bounded_extraction(service, run_id, failed_attempt_id, *,
                                    retry_reason, idempotency_key):
    """Authorize exactly one same-Batch malformed-JSON retry, without dispatch."""
    from pro_a.config import load_config
    from pro_a.evidence_binding import identity
    from . import bounded_extraction_persistence as persistence
    from .bounded_extraction_persistence import canonical as bounded_canonical
    from .bounded_extraction_store import BoundedExtractionStore, _event, _now, _record
    from .source_operations import build_source_providers, SourceOperationError

    _validate_retry_request(retry_reason, idempotency_key)
    worker = frozen_bounded_service(service, run_id, failed_attempt_id)
    run_projection = worker.get_run(run_id)
    bindings = worker.output_batches.inputs(run_projection)
    ledger = BoundedExtractionStore(worker.config)

    with ledger._connection(True) as connection:
        prior = next((event for event in _bounded_retry_events(
            connection,
        ) if event['idempotency_key'] == idempotency_key), None)
        if prior:
            if (prior['processing_run_id'], prior['retry_of_attempt_id'],
                    prior['operator_reason']) != (run_id, failed_attempt_id, retry_reason):
                raise SourceOperationError('IDEMPOTENCY_CONFLICT')
            attempt = connection.execute(
                'SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?',
                (prior['new_attempt_id'],),
            ).fetchone()
            return {'retry': prior, 'attempt': dict(attempt), 'duplicate': True}

        run = connection.execute(
            'SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,),
        ).fetchone()
        attempt = connection.execute(
            'SELECT a.*,s.series_id,s.state AS segment_state FROM bounded_extraction_attempts a '
            'JOIN bounded_extraction_segments s ON s.segment_id=a.segment_id '
            'WHERE a.attempt_id=?', (failed_attempt_id,),
        ).fetchone()
        if run is None or attempt is None:
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        series_id, segment_id = attempt['series_id'], attempt['segment_id']
        matching = [item for item in bindings if item[3].series_id == series_id]
        if len(matching) != 1:
            raise SourceOperationError('RETRY_IDENTITY_MISMATCH')
        value, context, catalog, series = matching[0]
        series_row = connection.execute(
            'SELECT * FROM bounded_extraction_series WHERE series_id=?', (series_id,),
        ).fetchone()
        segment = next((item for item in ledger._load(connection, series_id)[1].segments
                        if item.segment_id == segment_id), None)
        latest = connection.execute(
            'SELECT * FROM bounded_extraction_attempts WHERE segment_id=? '
            'ORDER BY attempt_number DESC LIMIT 1', (segment_id,),
        ).fetchone()
        outcome = connection.execute(
            'SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?',
            (failed_attempt_id,),
        ).fetchone()
        failure_events = [json.loads(row[0]) for row in connection.execute(
            "SELECT body_json FROM bounded_extraction_events WHERE series_id=? "
            "AND event_type='SEGMENT_FAILED' ORDER BY sequence", (series_id,),
        )]
        authorized = [event for event in _bounded_retry_events(
            connection, series_id=series_id,
        ) if event['segment_id'] == segment_id]
        if authorized:
            raise SourceOperationError('RETRY_LIMIT_EXCEEDED')
        if (run['state'] != 'BLOCKED' or run['stage'] != 'ORCHESTRATION'
                or run['error_code'] != 'BOUNDED_EXTRACTION_FAILED'
                or run['lease_owner'] is not None
                or series_row is None or series_row['state'] != 'FAILED'
                or attempt['segment_state'] != 'FAILED'
                or attempt['attempt_number'] != 1 or latest['attempt_id'] != failed_attempt_id
                or segment is None or outcome is None
                or outcome['external_outcome'] != 'SUCCEEDED'
                or outcome['classification'] != 'SUCCEEDED'
                or outcome['finish_reason'] != 'tool_calls'
                or type(outcome['output_tokens']) is not int
                or outcome['output_tokens'] >= segment.max_output_tokens
                or not any(event.get('attempt_id') == failed_attempt_id
                           and event.get('classification') == 'INVALID_SEGMENT_RESPONSE'
                           for event in failure_events)
                or connection.execute(
                    'SELECT 1 FROM bounded_extraction_segment_results WHERE segment_id=?',
                    (segment_id,),
                ).fetchone()
                or connection.execute(
                    'SELECT 1 FROM bounded_extraction_series_results WHERE series_id=?',
                    (series_id,),
                ).fetchone()
                or connection.execute(
                    'SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?',
                    (run_id,),
                ).fetchone()
                or connection.execute(
                    'SELECT 1 FROM bounded_extraction_attempts a '
                    'JOIN bounded_extraction_segments s USING(segment_id) '
                    'LEFT JOIN bounded_extraction_segment_results r USING(segment_id) '
                    "WHERE s.series_id=? AND s.segment_id<>? AND "
                    "(s.state<>'SUCCEEDED_COMPLETE' OR r.attempt_id<>a.attempt_id)",
                    (series_id, segment_id),
                ).fetchone()):
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')

        content = ledger._read_artifact(
            series_id, failed_attempt_id + '.raw.json', outcome,
        )
        envelope, body = ledger._decode_envelope(attempt, content)
        diagnostic = _json_syntax_diagnostic(body)
        if (diagnostic is None or envelope['http_status'] != 200
                or hashlib.sha256(content).hexdigest() != outcome['artifact_sha256']):
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')

        payload = worker.output_batches.segment_payload(
            value, context, catalog, series, segment,
        )
        prompt_content = bounded_canonical(payload).encode('utf-8')
        prompt_path = ledger._path(series_id, segment_id + '.prompt.json')
        if (not prompt_path.exists() or prompt_path.read_bytes() != prompt_content
                or hashlib.sha256(prompt_content).hexdigest()
                != json.loads(attempt['request_json'])['payload_sha256']):
            raise SourceOperationError('RETRY_IDENTITY_MISMATCH')
        providers = build_source_providers(
            load_config(worker.profile.phase4_config_path).llm, worker.jobs.profile,
        )
        configuration_sha256 = identity(
            providers[worker.output_batches.operation].configuration(),
        )
        if configuration_sha256 != attempt['configuration_sha256']:
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE')

        ordered = [item[3].series_id for item in bindings]
        target_index = ordered.index(series_id)
        for later_id in ordered[target_index + 1:]:
            later = connection.execute(
                'SELECT * FROM bounded_extraction_series WHERE series_id=?', (later_id,),
            ).fetchone()
            last = connection.execute(
                "SELECT body_json FROM bounded_extraction_events WHERE series_id=? "
                "AND event_type='SERIES_FAILED' ORDER BY sequence DESC LIMIT 1", (later_id,),
            ).fetchone()
            if (later['state'] != 'FAILED' or last is None
                    or json.loads(last[0]).get('code') != 'UPSTREAM_SERIES_FAILED'
                    or connection.execute(
                        'SELECT 1 FROM bounded_extraction_attempts a '
                        'JOIN bounded_extraction_segments s USING(segment_id) '
                        'WHERE s.series_id=?', (later_id,),
                    ).fetchone()):
                raise SourceOperationError('RETRY_NOT_ELIGIBLE')

        request = json.loads(attempt['request_json'])
        if (request != ledger._request(
                series, segment, request['payload_sha256'], configuration_sha256)
                or series_row['provider_call_reservations'] + 1 > series.budget.max_provider_calls
                or series_row['output_liability'] + segment.max_output_tokens
                > series.budget.max_cumulative_output_tokens):
            raise SourceOperationError('RETRY_IDENTITY_MISMATCH')

        retry_attempt_number = 1 + MAX_MALFORMED_JSON_RETRIES
        new_attempt_id = ledger._attempt_id(
            segment_id, retry_attempt_number, attempt['request_sha256'],
        )
        new_attempt = _record(connection, 'attempts', {
            'attempt_id': new_attempt_id, 'segment_id': segment_id,
            'attempt_number': retry_attempt_number, 'request_json': attempt['request_json'],
            'request_sha256': attempt['request_sha256'],
            'configuration_sha256': attempt['configuration_sha256'],
            'budget_identity': attempt['budget_identity'], 'created_at': _now(),
        })
        connection.execute(
            'UPDATE bounded_extraction_series SET state=\'OPEN\','
            'provider_call_reservations=provider_call_reservations+1,'
            'output_liability=output_liability+?,updated_at=? WHERE series_id=?',
            (segment.max_output_tokens, _now(), series_id),
        )
        connection.execute(
            "UPDATE bounded_extraction_segments SET state=CASE WHEN segment_id=? "
            "THEN 'RUNNING' WHEN state='FAILED' THEN 'PLANNED' ELSE state END,updated_at=? "
            "WHERE series_id=?", (segment_id, _now(), series_id),
        )
        for later_id in ordered[target_index + 1:]:
            connection.execute(
                "UPDATE bounded_extraction_series SET state='OPEN',updated_at=? WHERE series_id=?",
                (_now(), later_id),
            )
            connection.execute(
                "UPDATE bounded_extraction_segments SET state='PLANNED',updated_at=? "
                "WHERE series_id=? AND state='FAILED'", (_now(), later_id),
            )
            _event(connection, later_id, 'SERIES_REOPENED_AFTER_UPSTREAM_RETRY',
                   retry_of_attempt_id=failed_attempt_id)
        token = worker.runtime_compatibility
        retry = {
            'policy_version': MALFORMED_JSON_RETRY_POLICY_VERSION,
            'processing_run_id': run_id, 'series_id': series_id,
            'segment_id': segment_id, 'retry_of_attempt_id': failed_attempt_id,
            'new_attempt_id': new_attempt_id, 'retry_number': 1,
            'retry_reason_code': MALFORMED_JSON_RETRY_REASON,
            'operator_reason': retry_reason, 'idempotency_key': idempotency_key,
            'context_sha256': Domains(worker.config).read(
                run_id, connection=connection,
            )['context_sha256'],
            'request_sha256': attempt['request_sha256'],
            'original_raw_sha256': outcome['artifact_sha256'],
            'json_diagnostic': diagnostic,
            'compatibility_qualification_id': (
                token.record['qualification_id'] if token is not None else 'EXACT_RUNTIME'
            ),
        }
        _event(
            connection, series_id, _BOUNDED_RETRY_EVENT,
            **{key: value for key, value in retry.items() if key != 'series_id'},
        )
        _event(connection, series_id, 'ATTEMPT_RESERVED',
               attempt_id=new_attempt_id, record_sha256=new_attempt['record_sha256'])
        worker._event(connection, run_id, 'EXPLICIT_EXTRACTION_RETRY_ACCEPTED', retry)
        connection.execute(
            "UPDATE source_processing_runs SET state='EXTRACTION_PROCESSING',"
            "stage='WHOLE_PIECE_OUTPUT_DECOMPOSITION',error_code=NULL,retry_safe=0,"
            "manual_recovery_required=0,ended_at=NULL,updated_at=? "
            "WHERE processing_run_id=?", (_now(), run_id),
        )
    persistence.checkpoint('attempt_reserved')
    return {'retry': retry, 'attempt': new_attempt, 'duplicate': False}


def retry_failed_extraction(service, run_id, failed_attempt_id, *, retry_reason, idempotency_key):
    from .source_operations import SourceOperationError
    _validate_retry_request(retry_reason, idempotency_key)
    # One write transaction serializes duplicates, eligibility, sequence allocation,
    # new job/lineage insertion and the current Run projection transition.
    with service.store.connect(operator_write=True) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN IMMEDIATE')
        if not installed(connection):
            raise SourceOperationError('RETRY_SCHEMA_REQUIRED')
        prior = connection.execute('SELECT * FROM extraction_retries WHERE idempotency_key=?', (idempotency_key,)).fetchone()
        if prior:
            if (prior['processing_run_id'], prior['retry_of_attempt_id'], prior['retry_reason']) != (run_id, failed_attempt_id, retry_reason):
                raise SourceOperationError('IDEMPOTENCY_CONFLICT')
            return {'retry': dict(prior), 'job': service.jobs._project(connection, prior['job_id']), 'duplicate': True}
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        attempt = connection.execute('SELECT a.*,o.outcome,o.external_outcome FROM cloud_attempts a '
                                     'JOIN cloud_attempt_outcomes o ON o.attempt_id=a.attempt_id WHERE a.attempt_id=?',
                                     (failed_attempt_id,)).fetchone()
        if run is None or attempt is None:
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        if connection.execute('SELECT 1 FROM extraction_retries WHERE retry_of_attempt_id=?', (failed_attempt_id,)).fetchone():
            raise SourceOperationError('RETRY_ALREADY_IN_PROGRESS')
        roots = connection.execute('SELECT job_id FROM source_processing_jobs WHERE processing_run_id=?', (run_id,)).fetchall()
        retries = connection.execute('SELECT job_id FROM extraction_retries WHERE processing_run_id=?', (run_id,)).fetchall()
        ids = [r[0] for r in roots + retries]
        if (run['state'] in ('QUEUED', 'PARSING', 'EXTRACTION_PROCESSING', 'SEMANTIC_PROCESSING', 'PACKET_PREPARATION')
                or run['lease_owner'] is not None
                or any(connection.execute("SELECT 1 FROM cloud_jobs WHERE job_id=? AND state IN ('QUEUED','RUNNING')", (j,)).fetchone() for j in ids)):
            raise SourceOperationError('RETRY_ALREADY_IN_PROGRESS')
        job = connection.execute('SELECT * FROM cloud_jobs WHERE job_id=?', (attempt['job_id'],)).fetchone()
        effective = effective_job_ids(connection, run_id, 'SOURCE_ANALYSIS_PIECE')
        latest = connection.execute('SELECT attempt_id FROM cloud_attempts WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1', (attempt['job_id'],)).fetchone()
        if (run['state'] != 'FAILED' or run['stage'] != 'EXTRACTION_JOBS' or run['error_code'] != 'PROVIDER_ERROR'
                or attempt['job_id'] not in effective or job['state'] != 'FAILED'
                or job['sanitized_error'] != 'PROVIDER_ERROR' or job['phase'] != 'TERMINAL'
                or attempt['outcome'] != 'FAILED' or attempt['external_outcome'] != 'KNOWN_FAILURE'
                or latest[0] != failed_attempt_id):
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        if not service.jobs._verify_event_chain(connection, job['job_id']):
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        worker = frozen_service(
            service, run_id, required=True, failed_attempt_id=failed_attempt_id,
        )
        context = Domains(service.config).read(run_id, connection=connection)
        source = connection.execute('SELECT * FROM private_sources WHERE source_id=?', (run['source_id'],)).fetchone()
        if (source is None or job['source_id'] != source['source_id']
                or sha256_file(service.artifacts.resolve(source['storage_relative'])) != source['source_sha256']):
            raise SourceOperationError('RETRY_SOURCE_IDENTITY_MISMATCH')
        stored_runtime = json.loads(job['runtime_json'])
        current_runtime = worker.jobs.current_runtime()
        runtime_ok = stored_runtime == current_runtime
        if not runtime_ok and worker.runtime_compatibility is not None:
            try:
                from .retry_compatibility import guard_cloud_runtime
                guard_cloud_runtime(stored_runtime, current_runtime, worker.runtime_compatibility)
                runtime_ok = True
            except Exception:
                runtime_ok = False
        if (not runtime_ok or job['runtime_sha256'] != run['runtime_sha256']
                or job['runtime_json'] != run['runtime_json']):
            raise SourceOperationError('RETRY_RUNTIME_INCOMPATIBLE')
        if (job['prompt_json'] != canonical(operation_contract(job['operation_kind']))
                or job['prompt_sha256'] != operation_contract(job['operation_kind'])['prompt_bundle_sha256']):
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE')
        if frozen_cloud(job) != worker.jobs.profile:
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE')
        worker.jobs._input_payload(job)
        native_manifest = json.loads((worker._native_root(run) / 'execution_manifest.json').read_text(encoding='utf-8'))
        if native_manifest['state'] != 'SOURCE_READY':
            raise SourceOperationError('RETRY_NOT_ELIGIBLE')
        # Check native checkpoint compatibility BEFORE authorizing a provider call.
        from pro_a.config import load_config
        from pro_a.phase4_orchestration import _compatible, ExecutionBlocked
        from pro_a.phase4_retry import RetryPolicy
        try:
            _compatible(worker._native_root(run), run['native_execution_id'],
                        load_config(worker.profile.phase4_config_path), RetryPolicy.FORBID_ALL,
                        runtime_compatibility=worker.runtime_compatibility)
        except (ExecutionBlocked, ValueError, KeyError, OSError):
            raise SourceOperationError('RETRY_FROZEN_CONFIG_INCOMPLETE') from None
        parent = for_job(connection, job['job_id'])
        root_job = parent['root_job_id'] if parent else job['job_id']
        number = (parent['attempt_number'] if parent else attempt['attempt_number']) + 1
        new_job = 'JOB_' + uuid4().hex.upper()
        new_attempt = 'ATTEMPT_' + uuid4().hex.upper()
        created = now()
        # Copy only immutable execution inputs. No failure, result or call metadata.
        names = ('input_artifact_id input_sha256 source_id operation_kind runtime_json runtime_sha256 '
                 'prompt_json prompt_sha256 configuration_json configuration_sha256 native_checkpoint_json '
                 'provider requested_model accepted_model_aliases_json provider_adapter_version timeout_seconds '
                 'max_output_tokens max_calls max_attempts max_total_tokens retry_owner retry_policy_id').split()
        values = {name: job[name] for name in names}
        values.update(job_id=new_job, intent_sha256=digest({'retry_of_attempt_id': failed_attempt_id, 'job_id': new_job}),
                      state='QUEUED', phase='QUEUED', created_at=created, updated_at=created)
        connection.execute('INSERT INTO cloud_jobs(' + ','.join(values) + ') VALUES(' + ','.join('?' for _ in values) + ')', tuple(values.values()))
        lineage = dict(attempt_id=new_attempt, processing_run_id=run_id, root_job_id=root_job, job_id=new_job,
                       retry_of_attempt_id=failed_attempt_id, attempt_number=number, retry_reason=retry_reason,
                       trigger_type='EXPLICIT_RETRY', idempotency_key=idempotency_key,
                       context_sha256=context['context_sha256'], created_at=created)
        connection.execute('INSERT INTO extraction_retries VALUES(' + ','.join('?' for _ in lineage) + ')', tuple(lineage.values()))
        service.jobs._event(connection, new_job, 'EXPLICIT_EXTRACTION_RETRY_CREATED', lineage)
        service.jobs._event(connection, new_job, 'QUEUED')
        service._event(connection, run_id, 'EXPLICIT_EXTRACTION_RETRY_ACCEPTED', lineage)
        connection.execute("UPDATE source_processing_runs SET state='EXTRACTION_PROCESSING',stage='EXTRACTION_JOBS',"
                           'error_code=NULL,retry_safe=0,manual_recovery_required=0,ended_at=NULL,updated_at=? '
                           'WHERE processing_run_id=?', (created, run_id))
        return {'retry': lineage, 'job': service.jobs._project(connection, new_job), 'duplicate': False}
