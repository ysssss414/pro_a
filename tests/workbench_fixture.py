"""Public-safe blank-only fixture. Never completes review or calls a model/executor."""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3

from pro_a.db import Database
from pro_a.foundation_schema_preparation import apply_synthetic_migration
from pro_a.phase3f_review_completion import build_blank_review_packet
from pro_a.production_promotion import canonical_sha256, production_identity, sha256_file
from pro_a.workbench.config import WorkbenchConfig

SOURCE = 'SRC_SYNTHETIC_STAGE0'
RUN = 'INGEST_SYNTHETIC_STAGE0'
CLAIM = 'CLM_SYNTHETIC_STAGE0'
NODE = 'CAND_NODE_SYNTHETIC_STAGE0'
STATEMENT = 'Synthetic material A has a measured value of 12 units.'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def seal(body, prefix, id_field, hash_field):
    digest = canonical_sha256(body)
    return {**body, id_field: f'{prefix}_{digest[:16].upper()}', hash_field: digest}


def make_fixture(root: Path, *, mode='DEMO', origin='http://127.0.0.1:8000', remote=False, node_profile='stage0'):
    knowledge = root / 'knowledge' / 'synthetic.db'
    Database(knowledge).init_schema()
    migration = apply_synthetic_migration(knowledge, configured_production_path=root / 'never-open-production.db', expected_sha256=sha256_file(knowledge))
    if mode == 'DEMO':
        with closing(sqlite3.connect(knowledge)) as connection, connection:
            connection.execute("INSERT INTO meta VALUES('workbench_fixture_kind','SYNTHETIC_PUBLIC_SAFE')")
    if node_profile == 'reuse':
        with closing(sqlite3.connect(knowledge)) as connection, connection:
            connection.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES('NODE_SYNTHETIC_EXISTING','Existing synthetic material','Product','Public-safe fixture','active','2026-01-01','2026-01-01')")
    baseline = {k: v for k, v in production_identity(knowledge).items() if k != 'path'}
    artifacts = root / 'artifacts'
    run = artifacts / 'EXEC_SYNTHETIC_STAGE0' / 'engine'
    source = run / 'source' / 'synthetic.txt'
    source.parent.mkdir(parents=True)
    source.write_text(STATEMENT + '\n', encoding='utf-8', newline='\n')
    source_sha = sha256_file(source)
    claim = {'claim_id': CLAIM, 'statement': STATEMENT, 'evidence_pointer': 'synthetic:paragraph:1', 'evidence_excerpt': STATEMENT}
    write(run / 'evidence/evidence_bound_extraction_bundle.json', {
        'document_type': 'phase3c_extraction_bundle', 'schema_version': '1',
        'source': {'proposed_source_id': SOURCE, 'sha256': source_sha}, 'claims': [claim]})
    review = seal({'document_type': 'phase3e_claim_review', 'schema_version': '1', 'review_status': 'DRAFT',
                   'run_id': RUN, 'source_sha256': source_sha, 'claims': [{**claim,
                       'evidence_validation': {'bound': True, 'fidelity_status': 'EXACT',
                           'authoritative_locator': {'status': 'resolved', 'authoritative': True, 'locator': 'synthetic:paragraph:1',
                                                     'paragraph': 1, 'section': 'Synthetic measurements'}},
                       'table_eligibility': {'review_eligible': True},
                       'semantic_admission': {'overall_guard_disposition': 'ADMIT', 'guard_reasons': []},
                       'scope_preservation': {'status': 'PASS'}, 'review_admitted': True,
                       'recommended_decision': 'KEEP', 'recommendation_reason': 'Synthetic advisory only.',
                       'duplicate_of_claim_id': '', 'duplicate_reconciliation': {}, 'human_decision': 'PENDING'}],
                   'authorization': {'human_decisions_bound': False}}, 'CLAIM_REVIEW', 'review_id', 'review_sha256')
    claim_path = run / 'review/claim_review.json'
    write(claim_path, review)
    node = {'operation_candidate_id': NODE, 'source_operation_id': 'OP_SYNTHETIC_STAGE0', 'candidate_kind': 'synthetic_node',
            'proposed_name': 'Synthetic material A', 'proposed_type': 'Product', 'proposed_aliases': ['Synthetic A'],
            'prospective_node_id': 'NODE_SYNTHETIC_STAGE0', 'supporting_claim_ids': [CLAIM],
            'supporting_evidence': [{**claim, 'evidence_id': 'EVD_SYNTHETIC_STAGE0'}],
            'phase3c_validation_state': {'status': 'PASS'}, 'current_defer_reason': '',
            'exact_production_resolution': {'candidate_target_node_ids': []}, 'collision_diagnostics': {},
            'suggested_operation': 'DEFER', 'suggestion_reason': 'Synthetic advisory only.',
            'review_decision': 'PENDING', 'advisory_only': True, 'parent_placement_suggestion': {}}
    if node_profile != 'stage0':
        node['collision_diagnostics'] = {'prospective_node_id_exists': False, 'package_internal_normalized_term_collisions': [],
            'production_nocase_or_nfkc_target_ids': ['NODE_SYNTHETIC_EXISTING'] if node_profile == 'reuse' else []}
    if node_profile == 'reuse':
        node['exact_production_resolution'] = {'candidate_target_node_ids': ['NODE_SYNTHETIC_EXISTING'],
            'candidate_targets': [{'node_id': 'NODE_SYNTHETIC_EXISTING', 'canonical_name': 'Existing synthetic material', 'primary_type': 'Product'}]}
    write(run / 'review/node_operation_review.json', seal({
        'document_type': 'phase3e_node_operation_review', 'schema_version': '1', 'review_status': 'DRAFT',
        'operational_run': {'run_id': RUN, 'source_sha256': source_sha, 'claim_review_sha256': sha256_file(claim_path)},
        'records': [node], 'production_baseline': baseline,
        'audit_operations': {'relations': [{'candidate_id': 'REL_SYNTHETIC_EXCLUDED'}]}},
        'NODE_REVIEW', 'review_id', 'review_sha256'))
    write(run / 'promotion/promotion_preview.json', seal({
        'document_type': 'phase3e_non_executable_promotion_preview', 'schema_version': '1', 'run_id': RUN, 'source_sha256': source_sha,
        'parent_placement_suggestions': [{'suggestion_id': 'PARENT_PLACEMENT_SYNTHETIC_STAGE0', 'candidate_id': NODE,
            'prospective_child_node_id': 'NODE_SYNTHETIC_STAGE0', 'parent_node_id': 'NODE_SYNTHETIC_PARENT',
            'suggestion_type': 'SYNTHETIC_PARENT', 'governance_status': 'HUMAN_REVIEW_REQUIRED',
            'authorized_by_node_create': False, 'human_decision': 'PENDING', 'executable': False}],
        'authorization': {k: False for k in ('human_claim_decisions_bound', 'human_node_decisions_bound', 'executable',
            'production_apply_authorized', 'production_executor_compatible', 'intended_mutations_generated')},
        'bindings': {'production_baseline': baseline}}, 'PROMOTION_PREVIEW', 'preview_id', 'preview_sha256'))
    relatives = ['evidence/evidence_bound_extraction_bundle.json', 'review/claim_review.json',
                 'review/node_operation_review.json', 'promotion/promotion_preview.json', 'source/synthetic.txt']
    write(run / 'run_manifest.json', {
        'document_type': 'phase3e_operational_ingestion_manifest', 'schema_version': '1', 'run_id': RUN,
        'repository_commit': '766c304d6a90f5ddf8873c2c8fb430ca3ac7846c', 'stage_status': 'HUMAN_REVIEW_REQUIRED',
        'source': {'source_id': SOURCE, 'filename': source.name, 'sha256': source_sha, 'size_bytes': source.stat().st_size,
                   'source_type': 'SYNTHETIC_TEXT', 'frozen_relative_path': 'source/synthetic.txt', 'frozen_copy_sha256': source_sha},
        'production_baseline': baseline,
        'artifact_inventory': [{'path': p, 'sha256': sha256_file(run / p), 'size_bytes': (run / p).stat().st_size} for p in relatives]})
    packet = build_blank_review_packet(run)
    packet_path = artifacts / 'EXEC_SYNTHETIC_STAGE0/review/packet.json'
    write(packet_path, packet)
    config = WorkbenchConfig(mode, knowledge, root / 'state/workbench.sqlite3', artifacts, origin, remote=remote)
    return {'config': config, 'packet': packet, 'packet_relative': packet_path.relative_to(artifacts).as_posix(),
            'run_relative': run.relative_to(artifacts).as_posix(), 'migration': migration}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--origin', default='http://127.0.0.1:5173')
    parser.add_argument('--node-profile', choices=('stage0', 'create', 'reuse'), default='stage0')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    fixture = make_fixture(args.output.resolve(), origin=args.origin, node_profile=args.node_profile)
    config = fixture['config']
    toml = '[workbench]\n' + '\n'.join(f'{key} = {json.dumps(str(value).replace(chr(92), "/"))}' for key, value in {
        'mode': config.mode, 'knowledge_db': config.knowledge_db, 'state_db': config.state_db,
        'artifact_root': config.artifact_root, 'origin': config.origin, 'session_token_env': config.session_token_env}.items()) + '\nremote = false\n'
    (args.output / 'workbench.toml').write_text(toml, encoding='utf-8')
    print(json.dumps({'packet_id': fixture['packet']['packet_id'], 'packet': fixture['packet_relative'], 'run': fixture['run_relative']}))
