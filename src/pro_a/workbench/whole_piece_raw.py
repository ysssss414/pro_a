"""Schema12 private raw artifact and append-only event linkage, before parsing.

No outcomes/results table is repurposed: their existing validation-result meaning
is retained. A raw artifact without its event is reconciled at its deterministic
attempt path; a dispatch without that artifact never permits another call.
"""
from dataclasses import asdict, replace
import hashlib
import json
import os
from uuid import uuid4

from pro_a.cloud_contract import CloudResult, CloudContractError, validate_output, operation_contract, digest
from pro_a.whole_piece_compact import RESPONSE_VERSION, parse
from .config import checked_path


def enabled(identity):
    return identity.get('operation_schema_version') == RESPONSE_VERSION


def raw_path(jobs, request):
    # Existing validated CloudJob path machinery owns the generated identifiers.
    path, relative = jobs._artifact_path(request.job_id, request.attempt_id)
    return checked_path(path.with_suffix('.raw.json'), missing=True), relative.removesuffix('.json') + '.raw.json'


def persist(jobs, connection, request, result):
    from .cloud_jobs import JobError
    if digest(request.prompt_identity) != digest(operation_contract('SOURCE_ANALYSIS_PIECE')):
        raise JobError('WHOLE_PIECE_TOOL_SCHEMA_IDENTITY_MISMATCH')
    attempt = connection.execute(
        'SELECT a.job_id,a.request_sha256 FROM cloud_attempts a JOIN cloud_attempt_dispatches d '
        'ON d.attempt_id=a.attempt_id WHERE a.attempt_id=?', (request.attempt_id,),
    ).fetchone()
    if attempt is None or attempt['job_id'] != request.job_id or attempt['request_sha256'] != request.request_sha256:
        raise JobError('WHOLE_PIECE_RAW_DISPATCH_BINDING_MISMATCH')
    if type(result.output) is not str:
        raise JobError('WHOLE_PIECE_RAW_CONTENT_REQUIRED')
    result = jobs._durable_result(request, result,
        'EXACT' if result.provider_reported_model == request.requested_model else 'ACCEPTED_ALIAS')
    result = replace(result, transport_diagnostic={'http_status': 200})
    body = result.output.encode('utf-8')
    envelope = {'document_type': 'whole-piece-private-tool-raw-v1',
                'tool_identity': {k: request.prompt_identity[k] for k in
                    ('tool_name', 'tool_strict', 'tool_schema_version', 'tool_schema_sha256', 'provider_record_version')}, 'job_id': request.job_id,
                'attempt_id': request.attempt_id, 'request_sha256': request.request_sha256,
                'content_sha256': hashlib.sha256(body).hexdigest(), 'content_bytes': len(body),
                'result': asdict(result)}
    content = (json.dumps(envelope, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    sha = hashlib.sha256(content).hexdigest()
    path, relative = raw_path(jobs, request)
    if path.exists():
        if path.read_bytes() != content:
            raise JobError('WHOLE_PIECE_RAW_ARTIFACT_CONFLICT')
    else:
        temporary = checked_path(path.with_name(path.name + '.' + uuid4().hex + '.tmp'), missing=True)
        with temporary.open('xb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise JobError('WHOLE_PIECE_RAW_ARTIFACT_CORRUPT')
    event = {'attempt_id': request.attempt_id, 'request_sha256': request.request_sha256,
             'artifact_relative': relative, 'sha256': sha, 'content_sha256': envelope['content_sha256'],
             'content_bytes': len(body)}
    prior = connection.execute("SELECT event_json FROM cloud_job_events WHERE job_id=? AND event_type='WHOLE_PIECE_RAW_DURABLE'",
                               (request.job_id,)).fetchall()
    if prior:
        if len(prior) != 1 or json.loads(prior[0][0]) != event:
            raise JobError('WHOLE_PIECE_RAW_BINDING_MISMATCH')
    else:
        jobs._event(connection, request.job_id, 'WHOLE_PIECE_RAW_DURABLE', event)
    return result


def restore(jobs, connection, request):
    from .cloud_jobs import JobError
    path, _ = raw_path(jobs, request)
    if not path.exists():
        if connection.execute("SELECT 1 FROM cloud_job_events WHERE job_id=? AND event_type='WHOLE_PIECE_RAW_DURABLE'",
                              (request.job_id,)).fetchone():
            raise JobError('WHOLE_PIECE_RAW_ARTIFACT_MISSING')
        return None
    try:
        envelope = json.loads(path.read_bytes())
        if (envelope['job_id'] != request.job_id or envelope['attempt_id'] != request.attempt_id
                or envelope['request_sha256'] != request.request_sha256):
            raise ValueError()
        result = CloudResult(**envelope['result'])
        # Reconstruct exact envelope/bytes and immutable event; never accept
        # a modified artifact, injected fields, or a different request binding.
        return persist(jobs, connection, request, result)
    except (OSError, ValueError, TypeError, KeyError, CloudContractError):
        raise JobError('WHOLE_PIECE_RAW_ARTIFACT_INVALID') from None


def evaluate(request, result, aliases):
    if result.provider != request.provider or result.requested_model != request.requested_model:
        model, error = 'MISMATCH', 'PROVIDER_IDENTITY_MISMATCH'
    elif result.provider_reported_model == request.requested_model:
        model, error = 'EXACT', None
    elif result.provider_reported_model in aliases:
        model, error = 'ACCEPTED_ALIAS', None
    else:
        model, error = 'MISMATCH', 'MODEL_IDENTITY_MISMATCH'
    normalized, status, canonical = None, 'NOT_RUN', None
    if error is None:
        if result.finish_reason == 'length':
            error, status = 'WHOLE_PIECE_COMPACT_OUTPUT_LIMIT', 'TRUNCATED'
        elif (result.finish_reason != 'tool_calls' or result.operation_kind != request.operation_kind
                or result.attempt_number != request.attempt_number
                or (result.output_tokens is not None and result.output_tokens > 12000)
                or (result.usage_status == 'KNOWN' and result.input_tokens + result.output_tokens != result.total_tokens)):
            error, status = 'INVALID_PROVIDER_OUTCOME', 'FAIL'
        else:
            try:
                canonical = parse(result.output, request.payload)
                normalized = validate_output(request, canonical)
                status = 'PASS'
            except (ValueError, CloudContractError):
                error, status = 'OUTPUT_VALIDATION_FAILED', 'FAIL'
    return replace(result, output=canonical), normalized, status, model, error
