"""Generic shadow qualification plus a distinct, non-authorizing Stage 2 envelope."""
from __future__ import annotations

import copy
from contextlib import closing
import hashlib
import json

from .operational_contract import (CONTRACT_SHA, ENTRY_VERSION, KEYS, VERSION, identity, predicted_diff, readonly,
                                   require, runtime_identity, sealed, snapshot, verify, verify_envelope,
                                   _verify_envelope_integrity)
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
        if item['table'] == 'sources' and not payload['source'].get('reuse_existing_row'):
            # The generic shadow archive intent is never represented as materialized.
            item['row']['archived_path'] = 'operational_sources/' + payload['source']['source_sha256']
            metadata = json.loads(item['row']['metadata_json'])
            metadata.pop('summary', None)  # Canonical model summaries are outside the Stage 2 allowlist.
            metadata['phase42_operational'] = {'adapter_version': VERSION, 'attribution_id': sidecar['object_id'],
                                              'source_sha256': payload['source']['source_sha256'], 'materialization': 'EXTERNAL_OPERATOR_REQUIRED'}
            item['row']['metadata_json'] = encode(metadata)
        if item['table'] == 'claims':
            candidate = json.loads(item['row']['structured_json']).get('candidate_origin')
            if candidate:
                from .candidate_origin import GOVERNANCE, VERSION as ORIGIN_VERSION
                require(payload['metadata']['production_schema_version'] == '0.2.4', 'B_LITE_SCHEMA_REQUIRED')
                require(candidate.get('version') == ORIGIN_VERSION and
                        candidate.get('proposed_governance') == GOVERNANCE, 'CANDIDATE_GOVERNANCE_INVALID')
                item['row'].update(GOVERNANCE)
                item['row']['admission_basis_sha256'] = canonical_sha256({
                    'native': payload['human_authorization'],
                    'attribution': sidecar['sha256'], 'candidate': candidate})
    for claim_id, decision in sorted(sidecar['decisions'].items()):
        for link in sorted(decision['links'], key=lambda r: r['node_id']):
            row = {'claim_id': claim_id, 'node_id': link['node_id'], 'role': link['role']}
            mutations.append({'table': 'claim_node_links', 'operation': 'INSERT', 'key': {'claim_id': claim_id, 'node_id': link['node_id']},
                              'row': row, 'authorized_by': sidecar['object_id']})
    return mutations


def validate_package(envelope, context, sidecar):
    verify_envelope(envelope)
    _validate_package_binding(envelope, context, sidecar)


def _validate_package_binding(envelope, context, sidecar):
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
    return _package_projection(envelope)


def _package_projection(envelope):
    diff = envelope['predicted_diff']
    changes = []
    for action, entries in (('INSERT', diff['inserts']), ('UNCHANGED', diff['unchanged'])):
        for item in entries:
            private_columns = {'original_name', 'archived_path', 'metadata_json', 'structured_json'}
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


def registered_historical_read(config, handle):
    """Verify only stored history. This result never grants current-runtime execution."""
    service = Attribution(config)
    with service.store.connect() as connection:
        connection.execute('BEGIN')
        package = connection.execute('SELECT object_id,body FROM operational_packages WHERE artifact_id=?', (handle,)).fetchone()
        row = connection.execute('SELECT object_id,body FROM operational_receipts WHERE artifact_id=?', (handle,)).fetchone()
        history = connection.execute('''SELECT r.artifact_id,r.object_id AS receipt_id,r.body AS receipt_body,
            p.object_id AS package_id,p.body AS package_body FROM operational_receipts r
            LEFT JOIN operational_packages p ON p.artifact_id=r.artifact_id''').fetchall() if row else []
    require(package is not None or row is None, 'PACKAGE_NOT_REGISTERED')
    if package is None:
        return {'qualification': None, 'receipt': None}
    context, sidecar = service.sealed_context(handle)
    envelope = json.loads(package['body'])
    require(envelope['object_id'] == package['object_id'], 'ARTIFACT_IDENTITY_MISMATCH')
    _verify_envelope_integrity(envelope)
    _validate_package_binding(envelope, context, sidecar)
    receipt = json.loads(row['body']) if row else None
    verification = None
    if receipt is not None:
        _verify_registered_receipt(config, receipt, row['object_id'], envelope, sidecar)
        verification = _verify_history_chain(service, envelope, receipt, history)
    projected = _package_projection(envelope)
    complete = verification is None or verification['status'] == 'HISTORICAL_EXECUTION_CHAIN_VERIFIED'
    projected.update(historical_read_verified=complete, executable_under_current_runtime=False,
                     history_verification=verification,
                     original_runtime_identity=envelope['runtime_identity'],
                     operator_status=('EXECUTED_RECEIPT_VERIFIED' if complete else 'HISTORICAL_STATE_PROOF_INCOMPLETE') if receipt else 'AWAITING_OPERATOR_ACTION',
                     operator_action='Read-only registered history; current qualification and independent Operator authorization are required before any execution.')
    return {'qualification': projected, 'receipt': receipt}


def reconcile_registered(config, handle, receipt_id):
    """Read-only verification of a previously registered execution receipt."""
    result = registered_historical_read(config, handle)
    receipt = result['receipt']
    require(receipt is not None and receipt['object_id'] == receipt_id, 'RECEIPT_NOT_REGISTERED')
    verification = result['qualification']['history_verification']
    return {'status': verification['status'], 'receipt': receipt,
            'history_verification': verification,
            'historical_read_verified': result['qualification']['historical_read_verified'],
            'executable_under_current_runtime': False}


def _verify_registered_receipt(config, receipt, receipt_id, envelope, sidecar):
    verify(receipt, 'EXECUTION')
    require(receipt['object_id'] == receipt_id and receipt['envelope_id'] == envelope['object_id'] and receipt['adapter_version'] == VERSION and
            receipt.get('operator_entry_version') == ENTRY_VERSION and receipt.get('document_type') == 'phase42_operational_execution_receipt' and
            receipt['binding'] == envelope['binding'] and receipt['attribution_id'] == sidecar['object_id'] and
            receipt['baseline_sha256'] == envelope['baseline']['sha256'] and receipt['predicted_diff_id'] == envelope['predicted_diff']['object_id'] and
            receipt['status'] == 'EXECUTED' and receipt['transaction_result'] == 'COMMITTED', 'RECEIPT_BINDING_MISMATCH')
    counts = {}
    for item in envelope['predicted_diff']['inserts']: counts[item['table']] = counts.get(item['table'], 0) + 1
    require(receipt['actual_mutation_counts'] == counts and receipt['tables_touched'] == sorted(counts) and
            receipt['keys_touched'] == [{'table': r['table'], 'key': r['key']} for r in envelope['predicted_diff']['inserts']], 'RECEIPT_DIFF_MISMATCH')
    require(receipt['post_state_sha256'] == envelope['predicted_diff']['post_state_sha256'], 'RECOVERY_REQUIRED')
    materialized = checked_path(config.knowledge_db.parent / 'operational_sources' / envelope['source_sha256'])
    require(hashlib.sha256(materialized.read_bytes()).hexdigest() == receipt['source_sha256'] == envelope['source_sha256'], 'SOURCE_MATERIALIZATION_MISMATCH')


def _verify_history_objects(envelope, state):
    """Every authorized insert/no-op must still have its exact Canonical row."""
    diff = envelope['predicted_diff']
    require(not diff['updates'], 'HISTORICAL_INTEGRITY_INVALID')
    entries = diff['inserts'] + diff['unchanged']
    tokens = [(r['table'], canonical_sha256(r['key'])) for r in entries]
    mutations = {(r['table'], canonical_sha256(r['key'])): r for r in envelope['mutations']}
    require(len(tokens) == len(set(tokens)) == len(mutations) == len(envelope['mutations']) and set(tokens) == set(mutations), 'RECEIPT_DIFF_MISMATCH')
    require(diff['tables_touched'] == sorted({r['table'] for r in diff['inserts']}), 'RECEIPT_DIFF_MISMATCH')
    for item, token in zip(entries, tokens):
        table, key, row = item['table'], item['key'], item['row']
        require(table in KEYS and key == {k: row[k] for k in KEYS[table]}, 'MUTATION_KEY_INVALID')
        require(all(row.get(k) == v for k, v in mutations[token]['row'].items()), 'MUTATION_AUTHORITY_MISMATCH')
        matches = [r for r in state.get(table, []) if all(r.get(k) == v for k, v in key.items())]
        require(matches == [row], 'HISTORICAL_CANONICAL_OBJECT_MISMATCH')


def _verify_history_chain(service, envelope, receipt, registered):
    """Prove only chains present in trusted append-only Workbench registrations.

    Delta cancellation below checks registered pre/post commitments algebraically.
    Its temporary row sets are NOT recovered historical snapshots or new evidence.
    A missing registration never gets filled from the current database or a client.
    """
    with closing(readonly(service.config.knowledge_db)) as connection:
        connection.execute('BEGIN')
        require(connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok' and
                not connection.execute('PRAGMA foreign_key_check').fetchall(), 'RECOVERY_REQUIRED')
        current = snapshot(connection)
    current_sha = canonical_sha256(current)
    _verify_history_objects(envelope, current)
    chain = [(envelope, receipt)]
    result = {'status': 'HISTORICAL_STATE_PROOF_INCOMPLETE',
              'receipt_integrity': 'HISTORICAL_RECEIPT_INTEGRITY_VERIFIED',
              'canonical_objects': 'EXACT_MATCH',
              'original_post_state_sha256': receipt['post_state_sha256'],
              'current_state_sha256': current_sha, 'registered_receipt_chain': [receipt['object_id']],
              'execution_authorized': False}
    seen = {envelope['object_id']}
    while chain[-1][1]['post_state_sha256'] != current_sha:
        successors = []
        for row in registered:
            if row['package_id'] in seen or row['package_body'] is None:
                continue
            candidate = json.loads(row['package_body'])
            if candidate['predicted_diff']['pre_state_sha256'] == chain[-1][1]['post_state_sha256']:
                successors.append((row, candidate))
        if not successors:
            result['reason'] = 'NO_REGISTERED_SUCCESSOR_TO_CURRENT_STATE'
            return result
        require(len(successors) == 1, 'HISTORICAL_CHAIN_AMBIGUOUS')
        row, candidate = successors[0]
        require(candidate['object_id'] == row['package_id'], 'ARTIFACT_IDENTITY_MISMATCH')
        _verify_envelope_integrity(candidate)
        context, sidecar = service.sealed_context(row['artifact_id'])
        _validate_package_binding(candidate, context, sidecar)
        following = json.loads(row['receipt_body'])
        _verify_registered_receipt(service.config, following, row['receipt_id'], candidate, sidecar)
        _verify_history_objects(candidate, current)
        chain.append((candidate, following))
        seen.add(candidate['object_id'])
        result['registered_receipt_chain'].append(following['object_id'])
    # Complete registered chain: verify every exact delta against both committed
    # state hashes, including the requested execution. Never persist derived rows.
    proof_rows = copy.deepcopy(current)
    for item, executed in reversed(chain):
        diff = item['predicted_diff']
        require(canonical_sha256(proof_rows) == executed['post_state_sha256'], 'HISTORICAL_INTEGRITY_INVALID')
        _verify_history_objects(item, proof_rows)
        for inserted in diff['inserts']:
            proof_rows[inserted['table']].remove(inserted['row'])
        require(canonical_sha256(proof_rows) == diff['pre_state_sha256'], 'HISTORICAL_INTEGRITY_INVALID')
    result['status'] = 'HISTORICAL_EXECUTION_CHAIN_VERIFIED'
    result['reason'] = 'REGISTERED_CHAIN_AND_EXACT_DELTAS_MATCH_CURRENT_STATE'
    return result
