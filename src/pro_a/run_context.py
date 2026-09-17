"""Versioned immutable companions over the existing cloud/runtime identities."""
from __future__ import annotations

from datetime import datetime
from .domain_packs import canonical, digest, fields, require, sha, text

VERSION = 'run-domain-context-v1'
BASIS_FIELDS = 'source_id source_sha256 input_artifact_id scope_sha256 assignment_revision composition runtime prompt_sha256 config_sha256 model_configuration execution_policy'


def validate_basis(basis):
    fields(basis, BASIS_FIELDS)
    for name in ('source_id', 'input_artifact_id'):
        text(basis[name], 200)
    for name in ('source_sha256', 'scope_sha256', 'prompt_sha256', 'config_sha256'):
        sha(basis[name])
    require(type(basis['assignment_revision']) is int and basis['assignment_revision'] > 0)
    composition = basis['composition']
    fields(composition, 'primary_domain packs sha256')
    require(isinstance(composition['packs'], list) and composition['packs'])
    ids = []
    for pack in composition['packs']:
        fields(pack, 'domain_id version sha256')
        text(pack['domain_id'], 48)
        text(pack['version'], 80)
        sha(pack['sha256'])
        ids.append(pack['domain_id'])
    require(ids == sorted(set(ids)) and composition['primary_domain'] in ids)
    sha(composition['sha256'])
    runtime = basis['runtime']
    require(isinstance(runtime, dict) and 'runtime_sha256' in runtime and 'git_sha' in runtime)
    sha(runtime['runtime_sha256'])
    require(digest({k: v for k, v in runtime.items() if k != 'runtime_sha256'}) == runtime['runtime_sha256'], 'CONTEXT_RUNTIME_CORRUPT')
    model = basis['model_configuration']
    fields(model, 'provider requested_model accepted_model_aliases provider_adapter_version timeout_seconds max_output_tokens max_calls max_attempts max_total_tokens retry_owner retry_policy_id hidden_fallback configuration_sha256')
    require(digest({k: v for k, v in model.items() if k != 'configuration_sha256'}) == model['configuration_sha256'], 'CONTEXT_MODEL_CORRUPT')
    require(basis['execution_policy'] == 'OFFLINE_REPLAY_ONLY', 'DOMAIN_ACTIVATION_REQUIRED')


def freeze_context(basis, *, run_id, created_at, actor, reason):
    validate_basis(basis)
    for item in (run_id, actor, reason):
        text(item)
    try:
        require(datetime.fromisoformat(created_at).tzinfo is not None)
    except (ValueError, TypeError):
        require(False, 'CONTEXT_TIMESTAMP_INVALID')
    body = {'contract_version': VERSION, 'run_id': run_id, 'created_at': created_at,
            'actor': actor, 'reason': reason, 'basis': basis, 'resume_sha256': digest(basis)}
    return {**body, 'context_sha256': digest(body)}


def validate_context(value):
    fields(value, 'contract_version run_id created_at actor reason basis resume_sha256 context_sha256')
    require(value['contract_version'] == VERSION, 'CONTEXT_VERSION_UNSUPPORTED')
    expected = freeze_context(value['basis'], run_id=value['run_id'], created_at=value['created_at'],
                              actor=value['actor'], reason=value['reason'])
    require(canonical(value) == canonical(expected), 'FROZEN_CONTEXT_CORRUPT')
    return value


def guard_resume(frozen, current_basis):
    validate_context(frozen)
    validate_basis(current_basis)
    require(frozen['resume_sha256'] == digest(current_basis), 'DOMAIN_RUN_CONTEXT_DRIFT')