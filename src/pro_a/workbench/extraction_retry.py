"""Explicit, append-only retry lineage over frozen Source extraction jobs."""
from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from uuid import uuid4

from pro_a.cloud_contract import budget_for_operation, canonical, digest, now, operation_contract
from pro_a.production_promotion import sha256_file
from .cloud_jobs import CloudProfile, JobError
from .config import BoundaryError
from .domains import Domains
from .review_store import schema_version
from .store import Store


def installed(connection):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_retries'").fetchone() is not None


def prepare_extraction_retries(config):
    """Operator-only additive extension; never invoked by API startup or reads."""
    config.validate()
    if config.mode != 'PRIVATE':
        raise BoundaryError('PRIVATE_SOURCE_MODE_REQUIRED')
    with Store(config).connect(operator_write=True) as connection:
        connection.execute('BEGIN IMMEDIATE')
        if schema_version(connection) not in ('9', '10', '11'):
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
        for field in fields(CloudProfile):
            if field.name == 'provider_adapter_version':
                if row[field.name] != profile.adapter_for_operation(row['operation_kind']):
                    raise ValueError()
                continue
            stored = (json.loads(row['accepted_model_aliases_json'])
                      if field.name == 'accepted_model_aliases' else row[field.name])
            expected = budget[field.name] if field.name in budget else value[field.name]
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


def retry_failed_extraction(service, run_id, failed_attempt_id, *, retry_reason, idempotency_key):
    from .source_operations import SourceOperationError
    if (not isinstance(retry_reason, str) or not 1 <= len(retry_reason) <= 1000
            or retry_reason != retry_reason.strip()
            or retry_reason.splitlines() != [retry_reason]
            or any(ord(c) < 32 or ord(c) == 127 or c in '<>' for c in retry_reason)
            or re.search(r'(?i)(bearer\s+|sk-[a-z0-9]{8}|(?:api[_ -]?key|token|cookie|authorization)\s*[:=])', retry_reason)):
        raise SourceOperationError('INVALID_RETRY_REASON', 422)
    if not isinstance(idempotency_key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{15,127}', idempotency_key):
        raise SourceOperationError('INVALID_IDEMPOTENCY_KEY', 422)
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
