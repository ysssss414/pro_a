"""Qualified structured Foundation packets in the existing Workbench registry."""
from __future__ import annotations

import json
from pathlib import Path

from pro_a.phase3f_foundation_baseline import validate_review
from pro_a.production_promotion import canonical_sha256, sha256_file
from pro_a.structured_foundation import MODE, qualify, read_package, require
from .config import checked_path
from .review import require_safe_projection
from .stage1_scale import stage1_capacity
from .store import Store


def is_foundation(packet):
    return packet.get('package', {}).get('mode') == MODE


def projection_rows(packet):
    """Explicit public DTO; all original fields remain in the private native packet."""
    types = {'nodes': 'NODE', 'claims': 'CLAIM', 'aliases': 'ALIAS',
             'relations': 'RELATION', 'baseline_views': 'BASELINE_VIEW'}
    rows = []
    for kind, records in packet['objects'].items():
        for row in records:
            c = row['content']
            content = {key: c[key] for key in ('canonical_name', 'primary_type', 'statement', 'alias',
                'target_ref', 'from_ref', 'to_ref', 'relation_type', 'scope', 'subject_ref',
                'resolved_node_id', 'canonical_source_id', 'classification', 'reasons',
                'confidence', 'evidence_refs', 'evidence_bound', 'temporal_category',
                'existing_relation_ids', 'human_required') if key in c}
            content['native_content_sha256'] = row['content_sha256']
            content['original_fields_preserved_in_native_packet'] = True
            content['exact_production_resolution'] = {'candidate_target_node_ids': c.get('identity_matches', [])}
            content['evidence_warning'] = 'EVIDENCE_WARNING' in c['reasons']
            content['review_admitted'] = not content['evidence_warning']
            content['relation_ambiguity'] = any('AMBIGU' in reason or 'CAUSAL' in reason for reason in c['reasons'])
            content['domain_novelty'] = 'ONTOLOGY_PRESSURE' in c['reasons']
            content['official_view_directly_affected'] = kind == 'baseline_views'
            content['collision_diagnostics'] = {'package_internal_normalized_term_collisions':
                ['REVIEW_REQUIRED'] if any('COLLISION' in r for r in c['reasons']) else []}
            rows.append({'candidate_id': row['candidate_id'], 'candidate_type': types[kind],
                'content': content, 'content_sha256': row['content_sha256'],
                'allowed_decisions': row['allowed_decisions'], 'decision_effects': {},
                'structured_import': True})
    for source in packet['registry']['sources']:
        if source['resolution'] == 'REVIEW':
            rows.append({'candidate_id': 'SOURCE_REVIEW_' + canonical_sha256(source),
                'candidate_type': 'SOURCE', 'content': {'classification': 'REVIEW',
                    'reasons': ['SOURCE_IDENTITY_COLLISION'], 'human_required': True},
                'content_sha256': canonical_sha256(source), 'allowed_decisions': ['DEFER'],
                'decision_effects': {}, 'structured_import': True})
    return rows


def validate_projection(packet, run, artifact_id, packet_sha, mode):
    require(mode == 'PRIVATE', 'STRUCTURED_IMPORT_PRIVATE_ONLY')
    require(is_foundation(packet), 'STRUCTURED_PACKET_MODE_INVALID')
    validate_review(packet, expected_sha256=packet['immutable_packet_sha256'], completed=False)
    contract = json.loads((run / 'import_contract.json').read_text(encoding='utf-8'))
    package = read_package(run / 'package')
    require(package['sha256'] == contract['package_sha256'] == packet['package']['sha256'], 'STRUCTURED_REGISTERED_PACKAGE_DRIFT')
    require(contract['contract_sha256'] == canonical_sha256({k: v for k, v in contract.items() if k != 'contract_sha256'}), 'IMPORT_CONTRACT_DRIFT')
    rows = projection_rows(packet)
    dto = {'artifact_id': artifact_id, 'packet_id': packet['packet_id'], 'packet_file_sha256': packet_sha,
        'immutable_packet_sha256': packet['immutable_packet_sha256'], 'run_id': packet['package']['sha256'],
        'mode': mode, 'validation_state': 'VALID_BLANK_STRUCTURED_FOUNDATION_PACKET', 'packet_status': 'DRAFT',
        'source': {'source_id': None, 'source_sha256': None, 'size_bytes': None, 'source_type': MODE},
        'summary': {'total_operational_decisions_required': len(rows), 'counts': packet['counts']},
        'items': rows, 'excluded_relation_inventory': [],
        'domain_ids': [contract['domain_pack']['domain_id']],
        'capabilities': {'read_only': True, 'decision_save_available': False,
            'native_decisions_are_metadata_only': True, 'native_foundation_review_required': True}}
    require_safe_projection(dto)
    return dto


def import_package(config, *, package_root, contract, pack_root):
    """One bounded, offline package registration; replay reuses the same packet."""
    from .artifacts import Artifacts
    require(config.mode == 'PRIVATE', 'STRUCTURED_IMPORT_PRIVATE_ONLY')
    config.validate()
    target = checked_path(Path(contract['target_root']))
    require(all(Path(p).resolve().is_relative_to(target) for p in
                (config.knowledge_db, config.state_db, config.artifact_root)), 'IMPORT_TARGET_NOT_ISOLATED')
    config.artifact_root.mkdir(parents=True, exist_ok=True)
    lock = config.artifact_root / '.foundation-import.lock'
    with lock.open('x') as handle:
        try:
            package = read_package(package_root)
            packet, report = qualify(package, contract, knowledge_db=config.knowledge_db, pack_root=pack_root)
            relative = 'foundation-imports/' + package['sha256'][:24]
            destination = checked_path(config.artifact_root / relative, missing=True)
            packet_path = destination / 'foundation_packet.json'
            with Store(config).connect() as connection:
                capacity = stage1_capacity(connection)
                require(capacity.get('enabled'), 'STAGE1_SCHEMA_REQUIRED')
                exists = connection.execute('SELECT 1 FROM registered_packets WHERE packet_id=?', (packet['packet_id'],)).fetchone()
                if not exists:
                    require(not capacity['intake_paused'] and capacity['wip_state'] != 'HARD_STOP'
                            and not capacity['unprojected_review_packets'], 'STAGE1_STRUCTURED_IMPORT_CAPACITY_BLOCKED')
            def immutable(path, data):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    require(path.read_bytes() == data, 'STRUCTURED_IMPORT_REPLAY_DRIFT')
                else:
                    with path.open('xb') as stream:
                        stream.write(data)
            for name, data in package['files'].items():
                immutable(destination / 'package' / name, data)
            for name, value in [('import_contract.json', contract), ('qualification.json', report),
                                ('foundation_packet.json', packet)]:
                immutable(destination / name, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
            registered = Artifacts(config).register(relative + '/foundation_packet.json', relative)
            require(sha256_file(config.knowledge_db) == contract['production_sha256'], 'IMPORT_KNOWLEDGE_CHANGED')
            return {**registered, 'report': report, 'packet_relative': relative + '/foundation_packet.json',
                    'duplicate': bool(exists), 'provider_calls': 0, 'raw_source_extraction_calls': 0}
        finally:
            handle.close()
            lock.unlink()
