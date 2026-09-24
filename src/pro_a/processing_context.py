"""Immutable Shared Core processing context; separate from Domain assignment v1."""
from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path

from .cloud_contract import operation_contract
from .constants import CLAIM_NODE_ROLES, NODE_TYPES, RELATION_TYPES
from .domain_packs import canonical, digest, fields, require, sha, text

VERSION = 'run-processing-context-v2'
SHARED_CORE_CONTRACT = 'shared-core-processing-v1'
POLICY = 'LIVE_SHARED_CORE_BOUNDED'
BASIS_FIELDS = ('source_id source_sha256 input_artifact_id scope_sha256 processing_scope '
                'runtime prompt_sha256 config_sha256 model_configuration execution_policy')


def shared_core_sha256():
    root = Path(__file__).parent
    return digest({'contract_version': SHARED_CORE_CONTRACT,
                   'prompt_sha256': digest([operation_contract(op) for op in ('SOURCE_ANALYSIS_PIECE', 'SEMANTIC_DECOMPOSITION')]),
                   'node_types': NODE_TYPES, 'relation_types': RELATION_TYPES,
                   'claim_node_roles': sorted(CLAIM_NODE_ROLES),
                   'source_evidence_rules_sha256': hashlib.sha256((root / 'operational_ingestion.py').read_bytes()).hexdigest(),
                   'semantic_evidence_rules_sha256': hashlib.sha256((root / 'semantic_decomposition.py').read_bytes()).hexdigest()})


def validate_basis(basis):
    fields(basis, BASIS_FIELDS)
    for name in ('source_id', 'input_artifact_id'):
        text(basis[name], 200)
    for name in ('source_sha256', 'scope_sha256', 'prompt_sha256', 'config_sha256'):
        sha(basis[name])
    scope = basis['processing_scope']
    fields(scope, 'mode domain_assignment_status primary_domain packs shared_core_contract shared_core_sha256')
    require(scope['mode'] == 'SHARED_CORE_PENDING' and scope['domain_assignment_status'] == 'PENDING'
            and scope['primary_domain'] is None and scope['packs'] == []
            and scope['shared_core_contract'] == SHARED_CORE_CONTRACT, 'PROCESSING_SCOPE_INVALID')
    sha(scope['shared_core_sha256'])
    require(scope['shared_core_sha256'] == shared_core_sha256(), 'SHARED_CORE_IDENTITY_DRIFT')
    runtime = basis['runtime']
    require(isinstance(runtime, dict) and 'runtime_sha256' in runtime and 'git_sha' in runtime)
    sha(runtime['runtime_sha256'])
    require(digest({k: v for k, v in runtime.items() if k != 'runtime_sha256'}) == runtime['runtime_sha256'], 'CONTEXT_RUNTIME_CORRUPT')
    model = basis['model_configuration']
    fields(model, 'provider requested_model accepted_model_aliases provider_adapter_version timeout_seconds max_output_tokens max_calls max_attempts max_total_tokens retry_owner retry_policy_id hidden_fallback configuration_sha256')
    require(digest({k: v for k, v in model.items() if k != 'configuration_sha256'}) == model['configuration_sha256'], 'CONTEXT_MODEL_CORRUPT')
    require(basis['execution_policy'] == POLICY, 'PROCESSING_POLICY_INVALID')


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
    require(frozen['resume_sha256'] == digest(current_basis), 'PROCESSING_RUN_CONTEXT_DRIFT')
