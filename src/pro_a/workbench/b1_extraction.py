"""Explicit B1 Source Operations selection; no automatic or Web/MCP intake."""
from pro_a.b1_extraction import BINDING, VERSION
from .extraction_retry import _validate_retry_request
from .source_operations import SourceOperations, SourceOperationError
from . import output_qualification


def start(service, source_id, *, request_contract, reason, idempotency_key):
    if request_contract != VERSION:
        raise SourceOperationError('B1_CONTRACT_SELECTION_REQUIRED')
    _validate_retry_request(reason, idempotency_key)
    worker = SourceOperations(service.config, service.profile, service.jobs.profile,
                              _output_binding_version=BINDING)
    return worker.start(source_id, idempotency_key=idempotency_key, reprocess_reason=reason)


def frozen_worker(service, run_id):
    worker = output_qualification.frozen_worker(service, run_id)
    if worker.output_batches.binding_version != BINDING:
        raise SourceOperationError('B1_CONTRACT_SELECTION_REQUIRED')
    return worker


def providers(service, run_id):
    frozen_worker(service, run_id)
    return output_qualification.providers(service, run_id)


def advance(service, run_id, *, worker_id, provider=None):
    return frozen_worker(service, run_id).advance_once(worker_id=worker_id,
        processing_run_id=run_id, provider=provider)
