"""Generic shadow qualification plus a distinct, non-authorizing Stage 2 envelope."""
from __future__ import annotations

import copy
from contextlib import closing
import hashlib
import json

from .operational_contract import (CONTRACT_SHA, VERSION, identity, predicted_diff, readonly,
                                   require, runtime_identity, sealed, snapshot, verify, verify_envelope)
from .phase3f_operational_handoff import FULL_OPERATIONAL_POLICY, build_handoff_core, validate_handoff_payload
from .phase3f_review_completion import validate_completed_review_packet
from .production_promotion import canonical_sha256
from .workbench.attribution import Attribution, validate_decision
from .workbench.config import checked_path
from .workbench.review_workbench import encode


def materialized_source(context):
    source = context['packet']['source']
    manifest = json.loads(checked_path(context['run'] / 'run_manifest.json').read_text(encoding='utf-8'))
    relative = manifest['source']['frozen_relative_path']
    path = checked_path(context['run'] / relative)
    require(path.is_relative_to(context['run']), 'UNSAFE_PATH')
    body = path.read_bytes()
    require(hashlib.sha256(body).hexdigest() == source['source_sha256'] and len(body) == source['size_bytes'], 'SOURCE_MATERIALIZATION_MISMATCH')
    return body


def adapter_mutations(core, sidecar):
    """Only the new adapter adds explicit links; the generic shadow payload stays intact."""
    payload = core['payload']
    validate_handoff_payload(payload, FULL_OPERATIONAL_POLICY)
    mutations = copy.deepcopy(payload['intended_mutations'])
    for item in mutations:
        if item['table'] == 'node_aliases': item['key'] = {'alias': item['row']['alias']}
        if item['table'] == 'sources':
            # The generic shadow archive intent is never represented as materialized.
            item['row']['archived_path'] = 'operational_sources/' + payload['source']['source_sha256']
            metadata = json.loads(item['row']['metadata_json'])
            metadata.pop('summary', None)  # Canonical model summaries are outside the Stage 2 allowlist.
            metadata['phase42_operational'] = {'adapter_version': VERSION, 'attribution_id': sidecar['object_id'],
                                              'source_sha256': payload['source']['source_sha256'], 'materialization': 'EXTERNAL_OPERATOR_REQUIRED'}
            item['row']['metadata_json'] = encode(metadata)
    for claim_id, decision in sorted(sidecar['decisions'].items()):
        for link in sorted(decision['links'], key=lambda r: r['node_id']):
            row = {'claim_id': claim_id, 'node_id': link['node_id'], 'role': link['role']}
            mutations.append({'table': 'claim_node_links', 'operation': 'INSERT', 'key': {'claim_id': claim_id, 'node_id': link['node_id']},
                              'row': row, 'authorized_by': sidecar['object_id']})
    return mutations


def validate_package(envelope, context, sidecar):
    verify_envelope(envelope)
    require(envelope['binding'] == context['binding'] and envelope['attribution'] == sidecar, 'ATTRIBUTION_BASIS_MISMATCH')
    require(envelope['source_sha256'] == context['packet']['source']['source_sha256'], 'SOURCE_MATERIALIZATION_MISMATCH')
    materialized_source(context)
    require(set(sidecar['decisions']) == set(context['claims']), 'ATTRIBUTION_INCOMPLETE')
    for claim, decision in sidecar['decisions'].items():
        validate_decision(claim, decision, context['claims'], context['nodes'])
        require(decision['outcome'] != 'DEFER', 'ATTRIBUTION_DEFERRED')
    require(envelope['mutations'] == adapter_mutations(envelope['shadow'], sidecar), 'MUTATION_AUTHORITY_MISMATCH')
    claimed = {r['key']['claim_id'] for r in envelope['mutations'] if r['table'] == 'claims'}
    require(claimed == set(context['claims']), 'CLAIM_QUALIFICATION_BLOCKED')
    for operation in envelope['shadow']['payload']['node_operations']:
        if operation['review_authorization']['decision'] in ('CREATE', 'REUSE'):
            require(operation.get('executable') is True, 'NODE_QUALIFICATION_BLOCKED')
    for operation in envelope['shadow']['payload']['relation_operations']:
        if operation['review_authorization']['decision'] == 'CREATE': require(operation.get('executable') is True, 'PARENT_QUALIFICATION_BLOCKED')


def qualify(config, handle, expected_sidecar_id):
    service = Attribution(config)
    context, sidecar = service.sealed_context(handle)
    require(sidecar['object_id'] == expected_sidecar_id, 'ATTRIBUTION_BASIS_MISMATCH')
    require(all(d['outcome'] != 'DEFER' for d in sidecar['decisions'].values()), 'ATTRIBUTION_DEFERRED')
    with service.store.connect() as connection:
        stored = connection.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()
    if stored:
        value = json.loads(stored[0]); validate_package(value, context, sidecar)
        return value
    baseline = identity(config.knowledge_db)
    native_baseline = context['packet']['production_baseline']
    require(all(native_baseline[k] == baseline[k] for k in ('sha256', 'schema_sha256', 'schema_version', 'counts')), 'STALE_BASELINE')
    materialized_source(context)
    validation = validate_completed_review_packet(context['packet'], context['run'])
    receipt_sha = canonical_sha256(validation)
    completion_receipt = {'receipt_id': 'STAGE1_NATIVE_' + receipt_sha, 'receipt_sha256': receipt_sha}
    core = build_handoff_core(packet=context['packet'], completion=validation, completion_receipt=completion_receipt,
        bundle=context['bundle'], production_path=config.knowledge_db, repository_commit='5bcfc97741cbc19c3d4229faa97f7176d823dcdc',
        bindings=context['packet']['authoritative_inputs'], authority={'authority_source': 'EXPLICIT_SEALED_NATIVE_HUMAN_REVIEW'}, policy=FULL_OPERATIONAL_POLICY)
    require(core['phase3d_validation']['production_final_apply_rejection'] == 'FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH', 'HISTORICAL_GUARD_CHANGED')
    mutations = adapter_mutations(core, sidecar)
    with closing(readonly(config.knowledge_db)) as connection:
        diff = predicted_diff(connection, mutations)
    envelope = sealed({'document_type': 'phase42_guarded_operational_envelope', 'adapter_version': VERSION,
        'contract_sha256': CONTRACT_SHA, 'runtime_identity': runtime_identity(), 'binding': context['binding'],
        'baseline': baseline, 'source_sha256': context['packet']['source']['source_sha256'],
        'attribution': sidecar, 'shadow': core, 'mutations': mutations, 'predicted_diff': diff,
        'production_authorized': False, 'status': 'AWAITING_OPERATOR_ACTION'}, 'OPERATIONAL')
    validate_package(envelope, context, sidecar)
    require(identity(config.knowledge_db) == baseline, 'STALE_BASELINE')
    with service.store.connect(operator_write=True) as connection:
        connection.execute('PRAGMA synchronous=FULL'); connection.execute('BEGIN IMMEDIATE')
        existing = connection.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()
        if existing:
            require(json.loads(existing[0]) == envelope, 'QUALIFICATION_CONFLICT')
        else: connection.execute('INSERT INTO operational_packages VALUES(?,?,?)', (handle, envelope['object_id'], encode(envelope)))
    return envelope


def package_projection(envelope):
    verify_envelope(envelope)
    diff = envelope['predicted_diff']
    changes = []
    for action, entries in (('INSERT', diff['inserts']), ('UNCHANGED', diff['unchanged'])):
        for item in entries:
            private_columns = {'original_name', 'archived_path', 'metadata_json'}
            if item['table'] == 'sources': private_columns |= {'title', 'author', 'organization'}
            values = {key: value for key, value in item['row'].items() if key not in private_columns}
            withheld = {key: canonical_sha256(value) for key, value in item['row'].items() if key not in values}
            # Column names are values; private metadata contents are never projected.
            changes.append({'action': action, 'table': item['table'], 'key': item['key'], 'values': values,
                            'withheld_columns': [{'column': key, 'sha256': value} for key, value in withheld.items()]})
    return {'object_id': envelope['object_id'], 'adapter_version': VERSION, 'status': envelope['status'],
            'baseline_sha256': envelope['baseline']['sha256'], 'diff_id': diff['object_id'], 'changes': changes,
            'tables_touched': diff['tables_touched'], 'shadow_validation': envelope['shadow']['phase3d_validation'],
            'operator_action': 'External operator must inspect the complete registered envelope and explicitly authorize execution.',
            'production_authorized': False}


def reconcile_registered(config, handle, receipt_id):
    """HTTP can verify only a receipt previously registered by the external operator."""
    service = Attribution(config)
    context, sidecar = service.sealed_context(handle)
    with service.store.connect() as connection:
        row = connection.execute('SELECT body FROM operational_receipts WHERE artifact_id=? AND object_id=?', (handle, receipt_id)).fetchone()
        package = connection.execute('SELECT body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()
    require(row is not None and package is not None, 'RECEIPT_NOT_REGISTERED')
    receipt, envelope = json.loads(row[0]), json.loads(package[0])
    verify(receipt, 'EXECUTION'); validate_package(envelope, context, sidecar)
    require(receipt['object_id'] == receipt_id and receipt['envelope_id'] == envelope['object_id'] and receipt['adapter_version'] == VERSION and
            receipt['binding'] == envelope['binding'] and receipt['attribution_id'] == sidecar['object_id'] and
            receipt['baseline_sha256'] == envelope['baseline']['sha256'] and receipt['predicted_diff_id'] == envelope['predicted_diff']['object_id'] and
            receipt['status'] == 'EXECUTED' and receipt['transaction_result'] == 'COMMITTED', 'RECEIPT_BINDING_MISMATCH')
    counts = {}
    for item in envelope['predicted_diff']['inserts']: counts[item['table']] = counts.get(item['table'], 0) + 1
    require(receipt['actual_mutation_counts'] == counts and receipt['tables_touched'] == sorted(counts) and
            receipt['keys_touched'] == [{'table': r['table'], 'key': r['key']} for r in envelope['predicted_diff']['inserts']], 'RECEIPT_DIFF_MISMATCH')
    with closing(readonly(config.knowledge_db)) as connection:
        require(receipt['post_state_sha256'] == canonical_sha256(snapshot(connection)) == envelope['predicted_diff']['post_state_sha256'], 'RECOVERY_REQUIRED')
    materialized = checked_path(config.knowledge_db.parent / 'operational_sources' / envelope['source_sha256'])
    require(hashlib.sha256(materialized.read_bytes()).hexdigest() == receipt['source_sha256'] == envelope['source_sha256'], 'SOURCE_MATERIALIZATION_MISMATCH')
    return {'status': 'VERIFIED', 'receipt': receipt}
