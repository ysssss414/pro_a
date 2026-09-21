"""Offline, lossless qualified-package adapter; never calls providers or applies data."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from difflib import get_close_matches
from pathlib import Path

from .constants import CLAIM_NATURES, NODE_TYPES, RELATION_TYPES
from .domain_packs import load_pack
from .foundation_execution_contract import project_temporal
from .phase3f_foundation_baseline import build_review_packet, seal
from .production_promotion import (
    build_identity_catalog, canonical_sha256, connect_read_only, deterministic_id,
    nfkc_casefold, production_identity, resolve_identity, sha256_file,
)
from .workbench.config import BoundaryError, checked_path
from .relation_structure import directed_path_exists

MODE = 'QUALIFIED_STRUCTURED_FOUNDATION_BACKFILL'
VERSION = 'qualified-structured-foundation-v1'
MAX_FILES, MAX_FILE_BYTES, MAX_ROWS = 128, 8 * 1024 * 1024, 10000
TABLES = {
    'nodes': ('foundation_nodes_candidate.csv', 'candidate_id', 'NODE_OBSERVATIONS'),
    'aliases': ('foundation_aliases_candidate.csv', 'alias_candidate_id', 'ALIAS_CANDIDATES'),
    'claims': ('foundation_temporal_claims.jsonl', 'claim_candidate_id', 'TEMPORAL_CLAIMS'),
    'relations': ('foundation_relations_candidate.csv', 'relation_candidate_id', 'RELATION_CANDIDATES'),
    'evidence': ('evidence_registry.jsonl', 'evidence_id', 'EVIDENCE_SPANS'),
    'native_evidence': ('foundation_relation_native_evidence_candidate.jsonl', 'native_evidence_candidate_id', 'NATIVE_RELATION_EVIDENCE_CANDIDATES'),
    'sources': ('source_inventory.csv', 'source_id', 'PHYSICAL_SOURCES'),
}


def runtime_digest():
    root = Path(__file__).parent
    return canonical_sha256({p.relative_to(root).as_posix(): sha256_file(p)
                             for p in sorted(root.rglob('*.py'))})


def require(ok, code):
    if not ok:
        raise BoundaryError(code)


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'STRUCTURED_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, 'STRUCTURED_NONFINITE_NUMBER'))


def array(value):
    return value if isinstance(value, list) else _json(value) if value else []


def read_package(root):
    """Verify qualified structured bytes only. Raw source paths are never opened."""
    root = checked_path(Path(root))
    files = {}
    for path in sorted(root.rglob('*')):
        checked_path(path)
        if not path.is_file():
            continue
        require(len(files) < MAX_FILES and path.stat().st_size <= MAX_FILE_BYTES, 'STRUCTURED_PACKAGE_SIZE_LIMIT')
        files[path.relative_to(root).as_posix()] = path.read_bytes()
        require(sum(map(len, files.values())) <= 64 * 1024 * 1024, 'STRUCTURED_PACKAGE_TOTAL_SIZE_LIMIT')
    required = {'PACKAGE_SHA256SUMS.json', 'run_manifest.json', 'qa/validation_report.json',
                'PASS_A_IDENTITY_FREEZE.json', 'source_scope_receipt.csv', 'baseline_views/index.json',
                'current_view_candidates/index.json', 'provenance/source_manifest_as_uploaded.json',
                'provenance/source_scope_receipt_as_uploaded.csv', *(v[0] for v in TABLES.values())}
    require(required <= files.keys(), 'STRUCTURED_REQUIRED_FILE_MISSING')
    hashes = _json(files['PACKAGE_SHA256SUMS.json'])
    actual = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    require(hashes.get('algorithm') == 'SHA-256', 'STRUCTURED_HASH_ALGORITHM_INVALID')
    require(set(files) == set(hashes['files']) | set(hashes['exclusions']), 'STRUCTURED_UNACCOUNTED_FILE')
    require(all(actual.get(name) == digest for name, digest in hashes['files'].items()), 'STRUCTURED_PACKAGE_HASH_MISMATCH')
    receipt, manifest = (_json(files[name]) for name in ('qa/validation_report.json', 'run_manifest.json'))
    checks = receipt.get('checks', [])
    require(receipt.get('result') == 'PASS' and not receipt.get('failed_checks')
            and len(checks) == receipt.get('checks_run') == receipt.get('checks_passed')
            and all(row.get('result') == 'PASS' for row in checks), 'UPSTREAM_QUALIFICATION_CONFLICT')
    require(manifest.get('package_name') and manifest.get('artifact_schema') == 'WEB_CANDIDATE_HANDOFF_V1_NOT_RUNTIME_PAYLOAD', 'STRUCTURED_PACKAGE_IDENTITY_UNRESOLVED')
    for name, prior in manifest['inputs'].items():
        projection = {'semiconductor_P0_manifest_final.json': 'provenance/source_manifest_as_uploaded.json',
                      'semiconductor_P0_source_scope_receipt.csv': 'provenance/source_scope_receipt_as_uploaded.csv'}.get(name)
        if projection:
            require(actual[projection] == prior['sha256'], 'STRUCTURED_MANIFEST_PROVENANCE_CONFLICT')
    tables = {}
    # Every structured file is parsed; every byte remains in the immutable package inventory.
    for name, data in files.items():
        if name.endswith('.csv'):
            reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
            require(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), 'STRUCTURED_CSV_HEADER_INVALID')
            rows = list(reader)
            require(len(rows) <= MAX_ROWS and all(None not in row and all(v is not None for v in row.values()) for row in rows), 'STRUCTURED_TABLE_TRUNCATED_OR_OVERSIZE')
            tables[name] = rows
        elif name.endswith('.jsonl'):
            rows = [_json(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]
            require(len(rows) <= MAX_ROWS, 'STRUCTURED_ROW_LIMIT')
            tables[name] = rows
        elif name.endswith('.json'):
            tables[name] = _json(data)
    for kind, (name, key, metric) in TABLES.items():
        rows = tables[name]
        require(len(rows) == manifest['metrics'][metric], 'STRUCTURED_DECLARED_COUNT_MISMATCH')
        require(all(row.get(key) for row in rows) and len({row[key] for row in rows}) == len(rows), 'STRUCTURED_DUPLICATE_OBJECT_ID')
        tables[kind] = rows
    sources = tables['sources']
    slots = [slot for row in sources for slot in row['logical_source_slots'].split(';')]
    require(len(slots) == len(set(slots)) == manifest['metrics']['LOGICAL_SOURCE_SLOTS'], 'STRUCTURED_LOGICAL_SOURCE_COUNT_MISMATCH')
    require(len({row['sha256'] for row in sources}) == len(sources), 'STRUCTURED_DUPLICATE_SOURCE_BYTES')
    require(len(tables['baseline_views/index.json']) == manifest['metrics']['BASELINE_VIEWS'], 'STRUCTURED_VIEW_COUNT_MISMATCH')
    require(len(tables['current_view_candidates/index.json']['candidates']) == manifest['metrics']['CURRENT_VIEW_CANDIDATES'], 'STRUCTURED_VIEW_COUNT_MISMATCH')
    freeze = tables['PASS_A_IDENTITY_FREEZE.json']
    require(freeze['candidate_identity_sha256'] == actual[TABLES['nodes'][0]]
            and freeze['alias_candidates_sha256'] == actual[TABLES['aliases'][0]], 'STRUCTURED_IDENTITY_FREEZE_CONFLICT')
    return {'root': root, 'manifest': manifest, 'tables': tables, 'files': files,
            'inventory': actual, 'sha256': canonical_sha256(actual)}


def freeze_contract(package, *, pack_root, production_path, target_root, repository_commit, runtime_sha256):
    pack = load_pack(Path(pack_root))
    require(pack.manifest['domain_id'], 'DOMAIN_REQUIRED')
    return seal({
        'mode': MODE, 'adapter_version': VERSION, 'package_name': package['manifest']['package_name'],
        'package_sha256': package['sha256'], 'inventory': package['inventory'],
        'manifest_sha256': package['inventory']['run_manifest.json'],
        'qualification_receipt_sha256': package['inventory']['qa/validation_report.json'],
        'logical_source_count': package['manifest']['metrics']['LOGICAL_SOURCE_SLOTS'],
        'physical_source_count': len(package['tables']['sources']), 'domain_pack': pack.identity,
        'canonical_schema_version': '0.2.3', 'workbench_schema_version': '10',
        'repository_commit': repository_commit, 'runtime_sha256': runtime_sha256,
        'production_sha256': sha256_file(Path(production_path)),
        'target_root': str(Path(target_root).resolve()),
        'provider_calls_required': False, 'raw_pdf_validation_required': False,
        'raw_pdf_extraction_required': False, 'production_write_allowed': False,
        'ordinary_operator_runs_per_24h': 3, 'review_page_default': 25, 'review_page_max': 100,
        'review_wip_soft': 100, 'review_wip_hard': 200, 'worker_concurrency': 1,
        'max_objects_per_package': MAX_ROWS,
    }, 'contract_sha256')


def _snapshot(connection, table):
    # Bounded catalog load; no unbounded full-database materialization.
    rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid LIMIT ?', (MAX_ROWS + 1,)).fetchall()
    require(len(rows) <= MAX_ROWS, 'STRUCTURED_CATALOG_LIMIT')
    return [dict(row) for row in rows]


def qualify(package, contract, *, knowledge_db, pack_root):
    """Shared candidate classification; recommendations are never human decisions."""
    require(contract['contract_sha256'] == canonical_sha256({k: v for k, v in contract.items() if k != 'contract_sha256'}), 'IMPORT_CONTRACT_DRIFT')
    require(contract['mode'] == MODE and contract['production_write_allowed'] is False, 'PRODUCTION_WRITE_FORBIDDEN')
    require(contract['adapter_version'] == VERSION and contract['runtime_sha256'] == runtime_digest(), 'IMPORT_RUNTIME_DRIFT')
    require(package['sha256'] == contract['package_sha256'] and package['inventory'] == contract['inventory'], 'IMPORT_PACKAGE_DRIFT')
    pack = load_pack(Path(pack_root))
    require(pack.identity == contract['domain_pack'], 'IMPORT_DOMAIN_DRIFT')
    require(sha256_file(Path(knowledge_db)) == contract['production_sha256'], 'IMPORT_BASELINE_DRIFT')
    connection = connect_read_only(Path(knowledge_db))
    try:
        snapshot = {name: _snapshot(connection, name) for name in ('nodes', 'node_aliases', 'sources', 'node_relations')}
    finally:
        connection.close()
    catalog = build_identity_catalog(snapshot['nodes'], snapshot['node_aliases'])
    tables = package['tables']
    sources, source_refs = [], {}
    for raw in tables['sources']:
        matches = [row['source_id'] for row in snapshot['sources'] if row['sha256'].lower() == raw['sha256'].lower()]
        collisions = [row for row in snapshot['sources'] if row['source_id'] == raw['source_id'] and row['sha256'].lower() != raw['sha256'].lower()]
        status = 'REVIEW' if len(matches) > 1 or collisions else 'REUSE' if matches else 'CREATE'
        resolved = matches[0] if len(matches) == 1 and not collisions else deterministic_id('SRC', {'source_sha256': raw['sha256']}) if not matches and not collisions else None
        entry = {'source_id': raw['source_id'], 'resolved_source_id': resolved, 'resolution': status,
                 'collision': bool(collisions or len(matches) > 1), 'expected_sha256': raw['sha256'],
                 'upstream_sha256': raw['sha256'], 'provenance_verified': True, 'raw': raw}
        sources.append(entry)
        source_refs[raw['source_id']] = entry
    evidence = {row['evidence_id']: row for row in tables['evidence']}

    def binding(refs, source_id=None, source_sha=None):
        if not refs or len(refs) != len(set(refs)):
            return False
        for ref in refs:
            e = evidence.get(ref)
            if not e or e['source_id'] not in source_refs:
                return False
            source = source_refs[e['source_id']]
            if (not source['resolved_source_id'] or e.get('source_sha256') != source['expected_sha256']
                    or source_id is not None and e['source_id'] != source_id
                    or source_sha is not None and e['source_sha256'] != source_sha
                    or not e.get('evidence_excerpt') or not e.get('pdf_page') or not e.get('section')
                    or hashlib.sha256(e['evidence_excerpt'].encode()).hexdigest() != e.get('excerpt_sha256')):
                return False
        return True

    objects = {kind: [] for kind in ('nodes', 'aliases', 'claims', 'relations', 'baseline_views')}
    refs = {nid: nid for nid, row in catalog['nodes'].items() if row['status'] == 'active'}
    names = Counter(nfkc_casefold(row['proposed_canonical_name']) for row in tables['nodes'])
    accounting = []

    def add(kind, cid, raw, content, outcome, reasons):
        mapping = {key: 'NORMALIZED_MAPPING' if key in content and raw[key] != content[key]
                   else 'DIRECT_MAPPING' if key in content else 'REVIEW_REQUIRED' for key in raw}
        # Raw content is preserved in full; fields not mapped to canonical columns
        # stay explicitly classified as candidate-only review context.
        content.update(raw=raw, classification=outcome, reasons=sorted(set(reasons)), field_mapping=mapping)
        content['human_required'] = bool(reasons) or outcome in ('REVIEW', 'DEFER')
        objects[kind].append({'candidate_id': cid, 'content': content})
        accounting.append({'kind': kind, 'object_id': cid, 'content_sha256': canonical_sha256(raw)})

    for raw in tables['nodes']:
        cid, name, typ = raw['candidate_id'], raw['proposed_canonical_name'], raw['proposed_primary_type']
        matches = resolve_identity(catalog, name)['all_ids']
        reasons, resolved = [], None
        e_refs = array(raw['evidence_refs'])
        if typ not in NODE_TYPES or typ not in pack.manifest['supported_node_types']:
            outcome, reasons = 'DEFER', ['ONTOLOGY_PRESSURE']
        elif raw.get('disposition') == 'REJECT':
            outcome = 'REJECT'
        elif (len(matches) > 1 or names[nfkc_casefold(name)] > 1):
            outcome, reasons = 'REVIEW', ['IDENTITY_COLLISION']
        elif not binding(e_refs):
            outcome, reasons = 'REVIEW', ['EVIDENCE_WARNING']
        elif raw.get('existing_node_id') and matches != [raw['existing_node_id']]:
            outcome, reasons = 'REVIEW', ['IDENTITY_TARGET_MISMATCH']
        elif len(matches) == 1 and catalog['nodes'][matches[0]]['primary_type'] == typ and matches[0] in refs:
            resolved, outcome = matches[0], 'REUSE'
        elif matches or raw.get('existing_node_id') or raw.get('possible_existing_node_id') or raw.get('disposition') in ('REVIEW', 'CROSS_DOMAIN_QUARANTINE'):
            outcome, reasons = 'REVIEW', ['AMBIGUOUS_IDENTITY']
        elif get_close_matches(nfkc_casefold(name), [nfkc_casefold(n['canonical_name']) for n in catalog['nodes'].values() if n['primary_type'] == typ], n=1, cutoff=.92):
            outcome, reasons = 'REVIEW', ['NEAR_DUPLICATE_IDENTITY']
        else:
            outcome = 'CREATE'
            resolved = deterministic_id('NODE', {'package': package['sha256'], 'candidate_id': cid})
            reasons = ['NEW_CANONICAL_NODE']
        confidence = float(raw.get('confidence') or 0)
        if confidence < .5:
            reasons.append('LOW_OR_UNKNOWN_CONFIDENCE')
        if resolved:
            refs[cid] = resolved
        add('nodes', cid, raw, {'canonical_name': name, 'primary_type': typ, 'resolved_node_id': resolved,
            'evidence_refs': e_refs, 'confidence': confidence, 'identity_matches': matches,
            'create_reason': 'NO_SHARED_CATALOG_MATCH_WITH_BOUND_IDENTITY_EVIDENCE' if outcome == 'CREATE' else None}, outcome, reasons)
    alias_terms = Counter(nfkc_casefold(row['alias']) for row in tables['aliases'])
    for raw in tables['aliases']:
        target = refs.get(raw['target_existing_node_id'] or raw['target_candidate_id'])
        owners = resolve_identity(catalog, raw['alias'])['all_ids']
        collision = bool(owners and owners != [target]) or alias_terms[nfkc_casefold(raw['alias'])] > 1
        reasons = ['ALIAS_COLLISION'] if collision else ['ALIAS_OWNERSHIP_REVIEW']
        outcome = 'REVIEW' if collision or not target or raw.get('disposition') == 'REVIEW' else 'ACCEPTABLE'
        if not binding(array(raw['evidence_refs'])):
            outcome, reasons = 'REVIEW', [*reasons, 'EVIDENCE_WARNING']
        if raw.get('disposition') == 'REJECT':
            outcome = 'REJECT'
        add('aliases', raw['alias_candidate_id'], raw, {'alias': raw['alias'], 'target_ref': target,
            'evidence_refs': array(raw['evidence_refs']), 'alias_collision': collision}, outcome, reasons)
    for raw in tables['claims']:
        e_ref = raw.get('evidence_ref')
        good = binding([e_ref], raw.get('source_id'), raw.get('source_sha256'))
        good = good and raw.get('evidence_excerpt') == evidence[e_ref]['evidence_excerpt']
        reasons = []
        if not good:
            reasons.append('EVIDENCE_WARNING')
        if raw.get('nature') not in CLAIM_NATURES:
            reasons.append('ONTOLOGY_PRESSURE')
        if raw['subject_ref'] not in refs:
            reasons.append('SUBJECT_REVIEW')
        if not raw.get('confidence') or raw['confidence'] < .5:
            reasons.append('LOW_OR_UNKNOWN_CONFIDENCE')
        if not raw.get('review_ready'):
            reasons.append('UPSTREAM_REVIEW_REQUIRED')
        outcome = 'REVIEW' if reasons or not raw.get('review_ready') else 'ACCEPTABLE'
        row = {'claim_id': raw['claim_candidate_id'], 'statement': raw['statement'], 'nature': raw['nature'],
            'source_id': source_refs.get(raw['source_id'], {}).get('resolved_source_id'),
            'fact_time': raw.get('fact_time') or '', 'publication_time': raw.get('publication_time') or '',
            'ingestion_time': package['manifest']['generated_at'], 'created_at': package['manifest']['generated_at'],
            'evidence_pointer': json.dumps(raw.get('evidence_locator', {}), ensure_ascii=False, sort_keys=True),
            'evidence_excerpt': raw.get('evidence_excerpt', ''), 'attributed_to': raw.get('attribution', ''),
            'scope': raw.get('scope', ''), 'status': 'needs_review', 'confidence': raw.get('confidence'),
            'structured_json': json.dumps({'foundation_native': raw}, ensure_ascii=False, sort_keys=True)}
        add('claims', raw['claim_candidate_id'], raw, {'statement': raw['statement'],
            'source_id': raw['source_id'], 'source_sha256': raw['source_sha256'],
            'canonical_source_id': source_refs.get(raw['source_id'], {}).get('resolved_source_id'),
            'subject_ref': refs.get(raw['subject_ref']), 'evidence': [evidence[e_ref]] if good else [],
            'evidence_bound': bool(good), 'temporal_category': raw['temporal_category'],
            'nature': raw['nature'], 'confidence': raw.get('confidence'), 'row': row}, outcome, reasons)
    native = {row['relation_candidate_id']: row for row in tables['native_evidence']}
    for raw in tables['relations']:
        reasons = []
        start, end = refs.get(raw['source_ref']), refs.get(raw['target_ref'])
        e_refs = array(raw['evidence_refs'])
        if raw['relation_type'] not in RELATION_TYPES or raw['relation_type'] not in pack.manifest['supported_relations']:
            reasons.append('ONTOLOGY_PRESSURE')
        if not start or not end or start == end or raw['direction_check'] != 'PASS' or raw.get('disposition') != 'ACCEPTABLE':
            reasons.append('RELATION_AMBIGUITY')
        if raw.get('confidence') is None or float(raw['confidence']) < .5:
            reasons.append('LOW_OR_UNKNOWN_CONFIDENCE')
        if raw['relation_type'] in ('part_of', 'drives', 'constrains', 'benefits_from'):
            reasons.append('PARENT_OR_CAUSAL_REVIEW')
        n = native.get(raw['relation_candidate_id'])
        bound = binding(e_refs)
        if n:
            bound = bound and binding([n['evidence_ref']], n['evidence_source_id'], n['source_sha256'])
            bound = bound and all(n[k] == raw[k] for k in ('source_ref','relation_type','target_ref','scope'))
            bound = bound and n['evidence_excerpt'] == evidence.get(n['evidence_ref'], {}).get('evidence_excerpt')
        if not bound or not n or raw['entailment_check'] != 'PASS':
            reasons.append('EVIDENCE_WARNING')
        existing = [row['relation_id'] for row in snapshot['node_relations'] if
                    (row['from_node_id'], row['relation_type'], row['to_node_id'], row['scope']) == (start, raw['relation_type'], end, raw['scope'])]
        if raw['relation_type'] == 'part_of' and start and end and directed_path_exists(
                [(r['from_node_id'], r['to_node_id']) for r in snapshot['node_relations'] if r['relation_type'] == 'part_of'], end, start):
            reasons.append('PARENT_CYCLE')
        add('relations', raw['relation_candidate_id'], raw, {'from_ref': start, 'to_ref': end,
            'relation_type': raw['relation_type'], 'scope': raw['scope'], 'evidence_refs': e_refs,
            'evidence_bound': bool(bound), 'existing_relation_ids': existing,
            'native_evidence': n, 'temporal_status': raw['temporal_status'], 'temporal_projection': project_temporal(raw)},
            'REJECT' if raw.get('disposition') == 'REJECT' else 'REVIEW' if reasons else 'ACCEPTABLE', reasons)
    for index, raw in enumerate(tables['baseline_views/index.json']):
        cid = raw.get('candidate_id') or raw.get('baseline_view_candidate_id') or raw.get('baseline_view_id') or raw.get('view_candidate_id') or deterministic_id('BASELINE_CAND', raw)
        add('baseline_views', cid, raw, {'target_ref': refs.get(raw.get('node_ref')),
            'official_view_directly_affected': True}, 'REVIEW', ['VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE'])
    registry = seal({'materialization_mode': MODE, 'package_sha256': package['sha256'],
        'package_inventory_sha256': canonical_sha256(package['inventory']), 'sources': sources,
        'expected_sources': len(sources), 'qualified_provenance_sources': len(sources),
        'materialized_sources': 0}, 'registry_sha256')
    package_binding = {'mode': MODE, 'sha256': package['sha256'],
        'inventory_sha256': canonical_sha256(package['inventory']), 'object_accounting': accounting,
        'manifest_sha256': contract['manifest_sha256'], 'qualification_receipt_sha256': contract['qualification_receipt_sha256']}
    baseline = production_identity(Path(knowledge_db))
    baseline.pop('path', None)
    packet = build_review_packet(package=package_binding, registry=registry, production=baseline,
        repository_commit=contract['repository_commit'], objects=objects,
        timestamp=package['manifest']['generated_at'])
    counts = {kind: dict(Counter(row['content']['classification'] for row in rows)) for kind, rows in packet['objects'].items()}
    reasons = Counter(reason for rows in packet['objects'].values() for row in rows for reason in row['content']['reasons'])
    report = {'mode': MODE, 'package_sha256': package['sha256'], 'classifications': counts,
        'sources': dict(Counter(row['resolution'] for row in sources)), 'source_collisions': sum(row['collision'] for row in sources),
        'alias_collisions': sum(row['content']['alias_collision'] for row in objects['aliases']),
        'mandatory_exceptions': sum(row['content']['human_required'] for rows in objects.values() for row in rows),
        'exception_reasons': dict(reasons), 'candidate_objects': sum(packet['counts'].values()),
        'evidence_objects': len(evidence), 'native_relation_evidence_objects': len(tables['native_evidence']),
        'current_view_candidates': tables['current_view_candidates/index.json'],
        'provider_calls': 0, 'raw_source_extraction_calls': 0, 'production_write_count': 0,
        'production_apply_executed': False, 'final_human_qualification': 'PENDING',
        'structural_sha256': canonical_sha256({'registry': registry, 'objects': packet['objects']}),
        'lossless_package_inventory': package['inventory']}
    primary_files = {v[0] for v in TABLES.values()} | {'baseline_views/index.json'}
    report['supplemental_object_accounting'] = {
        name: {'classification': 'DIRECT_MAPPING', 'mapping_target': 'IMMUTABLE_CANDIDATE_CONTEXT_ARTIFACT',
               'objects': len(value) if isinstance(value, list) else 1, 'sha256': package['inventory'][name]}
        for name, value in tables.items() if name in package['inventory'] and name not in primary_files}
    return packet, report
