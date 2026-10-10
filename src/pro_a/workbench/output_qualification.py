"""Internal Operator entry. No Web/MCP route, automatic intake or Semantic work."""
import json

from pro_a import output_decomposition as output
from pro_a.cloud_contract import digest
from pro_a.config import load_config
from .domains import Domains
from .extraction_retry import bounded_frozen_components, _validate_retry_request
from .source_operations import SourceOperations, SourceOperationError, build_source_providers

VERSION = 'semantic-intent-operator-qualification-v1'


def qualification_contract(binding_version):
    if binding_version not in (output.INTENT_BINDING_VERSION, output.OWNERSHIP_BINDING_VERSION, output.EVIDENCE_INTENT_BINDING_VERSION):
        raise SourceOperationError('UNSUPPORTED_OUTPUT_QUALIFICATION_BINDING')
    return {'version': 'evidence-intent-operator-qualification-v2' if binding_version == output.EVIDENCE_INTENT_BINDING_VERSION else VERSION, 'binding_version': binding_version,
            'completion_boundary': 'STOP_AFTER_BOUNDED_EXTRACTION', 'semantic_registration_allowed': False}


def start(service, source_id, *, record_version, reason, idempotency_key):
    _validate_retry_request(reason, idempotency_key)
    bindings = {output.intent.VERSION: output.INTENT_BINDING_VERSION,
                output.ownership.VERSION: output.OWNERSHIP_BINDING_VERSION,
                output.evidence_intent.VERSION: output.EVIDENCE_INTENT_BINDING_VERSION}
    if record_version not in bindings:
        raise SourceOperationError('UNSUPPORTED_OUTPUT_QUALIFICATION_BINDING')
    worker = SourceOperations(service.config, service.profile, service.jobs.profile,
                              _output_binding_version=bindings[record_version])
    # The standard intake, idempotency, config and domain guards all still apply.
    return worker.start(source_id, idempotency_key=idempotency_key, reprocess_reason=reason)


def frozen_worker(service, run_id):
    with service.store.connect() as connection:
        run = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        if run is None:
            raise SourceOperationError('PROCESSING_RUN_NOT_FOUND', 404)
        runtime = json.loads(run['runtime_json'])
        basis = {k: v for k, v in runtime.items() if k != 'runtime_sha256'}
        if digest(basis) != runtime.get('runtime_sha256') or runtime['runtime_sha256'] != run['runtime_sha256']:
            raise SourceOperationError('RUNTIME_IDENTITY_CORRUPT')
        selected = runtime.get('output_operator_qualification', {})
        binding = selected.get('binding_version')
        if selected != qualification_contract(binding):
            raise SourceOperationError('OUTPUT_QUALIFICATION_IDENTITY_MISMATCH')
        profile, cloud, _, _ = bounded_frozen_components(service.config, connection, run)
    worker = SourceOperations(service.config, profile, cloud, _output_binding_version=binding)
    if worker.jobs.current_runtime() != runtime:
        raise SourceOperationError('RUNTIME_DRIFT')
    Domains(service.config).guard(run_id, worker.jobs, worker.profile)
    return worker


def providers(service, run_id):
    worker = frozen_worker(service, run_id)
    return build_source_providers(load_config(worker.profile.phase4_config_path).llm, worker.jobs.profile,
                                  output_binding_version=worker.output_batches.binding_version)


def advance(service, run_id, *, worker_id, provider=None):
    worker = frozen_worker(service, run_id)
    return worker.advance_once(worker_id=worker_id, processing_run_id=run_id, provider=provider)


def resume(service, run_id, *, worker_id, idempotency_key, max_new_calls, provider=None):
    worker = frozen_worker(service, run_id)
    return worker.resume_bounded_extraction_only(run_id, worker_id=worker_id,
        idempotency_key=idempotency_key, max_new_calls=max_new_calls, provider=provider)
