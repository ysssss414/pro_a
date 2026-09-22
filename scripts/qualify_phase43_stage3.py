"""Qualify cross-domain candidates without changing Production or Stage 2 inputs."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from pro_a.constants import NODE_TYPES, RELATION_TYPES
from pro_a.phase3f_foundation_baseline import validate_review
from pro_a.production_promotion import (
    build_identity_catalog, canonical_sha256, connect_read_only,
    resolve_identity, sha256_file,
)
from pro_a.structured_foundation import freeze_contract, qualify, read_package, runtime_digest

BASELINE = '690fc4f26e02607fb54a48053cf8faf6775621c3'
PRODUCTION_SHA = '6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1'
PACKAGE_SHA = '131421d3bbe3b968a1c72ee6e3767cfad6141a0cdaea1850ba30cccbd3932918'
AUTH_SHA = '23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f'
BRANCH = 'codex/phase43-stage3-cross-domain-resolution'
IDENTITY_OUTCOMES = ('REUSE_CANONICAL', 'CREATE_NEW_CANONICAL', 'KEEP_DOMAIN_SPECIFIC', 'DEFER', 'REJECT')
RELATION_OUTCOMES = ('REUSE_RELATION', 'CREATE_RELATION', 'KEEP_DOMAIN_SPECIFIC_RELATION', 'DEFER_RELATION', 'REJECT_RELATION')


def require(value, message):
    if not value:
        raise ValueError('STAGE3_QUALIFICATION_FAILED: ' + message)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def json_array(value):
    return value if isinstance(value, list) else json.loads(value or '[]')


def frozen_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def immutable_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == data, 'artifact replay drift: ' + str(path))
        return False
    with path.open('xb') as stream:
        stream.write(data)
    return True


def evidence_for(refs, evidence, sources, *, source_id=None, allow_empty=False):
    rows = []
    require((refs or allow_empty) and len(refs) == len(set(refs)), 'missing or duplicate evidence reference')
    for ref in refs:
        row = evidence.get(ref)
        require(row is not None and row['source_id'] in sources, 'unknown evidence/source reference')
        require(row['source_sha256'] == sources[row['source_id']]['sha256'], 'cross-source evidence leakage')
        require(hashlib.sha256(row['evidence_excerpt'].encode()).hexdigest() == row['excerpt_sha256'], 'excerpt hash drift')
        if source_id is not None:
            require(row['source_id'] == source_id, 'cross-source evidence leakage')
        rows.append(row)
    return rows


def identity_resolution(row, node, catalog, human=None):
    """Resolve one frozen cross-domain comparison row, without changing the catalog."""
    reasons = []
    name = row['observed_name']
    retrieval = resolve_identity(catalog, name)
    matches = retrieval['all_ids']
    recommendation = row['recommended_disposition']
    human_decision = (human or {}).get('human_input', {}).get('decision')
    target = None
    if node is None:
        outcome = 'DEFER'
        reasons.append('NOT_ADMITTED_IN_STAGE2')
    elif human_decision in ('DEFER', 'REJECT'):
        outcome = human_decision
        reasons.append('FROZEN_STAGE2_HUMAN_DECISION')
    elif recommendation == 'REJECT' or node['content']['raw']['disposition'] == 'REJECT':
        outcome = 'REJECT'
        reasons.append('FROZEN_STAGE2_REJECTION')
    elif recommendation == 'CROSS_DOMAIN_QUARANTINE' or node['content']['raw']['cross_domain_status'] == 'QUARANTINED':
        outcome = 'DEFER'
        reasons.append('HISTORICAL_QUARANTINE')
    elif node['content']['primary_type'] not in NODE_TYPES:
        outcome = 'DEFER'
        reasons.append('ONTOLOGY_PRESSURE')
    elif len(matches) > 1:
        outcome = 'DEFER'
        reasons.append('MULTIPLE_CATALOG_OWNERS')
    elif len(matches) == 1:
        found = catalog['nodes'][matches[0]]
        if found['primary_type'] != node['content']['primary_type']:
            outcome = 'DEFER'
            reasons.append('TYPE_MISMATCH')
        elif found['status'] != 'active' or recommendation != 'REUSE' or row['existing_node_id'] != matches[0]:
            outcome = 'DEFER'
            reasons.append('IDENTITY_TARGET_OR_STATUS_REVIEW')
        else:
            outcome, target = 'REUSE_CANONICAL', matches[0]
            reasons.append('EXACT_SHARED_CATALOG_IDENTITY')
    elif recommendation == 'CREATE' and node['content']['classification'] == 'CREATE':
        nearby = row['existing_node_id'] or node['content']['raw'].get('possible_existing_node_id')
        if nearby and nearby in catalog['nodes'] and catalog['nodes'][nearby]['primary_type'] != node['content']['primary_type']:
            outcome = 'DEFER'
            reasons.append('TYPE_MISMATCH')
        else:
            outcome = 'CREATE_NEW_CANONICAL'
            target = node['content']['resolved_node_id']
            reasons.append('DISTINCT_IDENTITY_PROPOSAL' if nearby else 'NO_SHARED_CATALOG_MATCH')
    else:
        outcome = 'DEFER'
        reasons.append('AMBIGUOUS_IDENTITY')
    if recommendation == 'REUSE' and not matches and outcome == 'DEFER':
        reasons.append('ALIAS_OR_DECORATION_REQUIRES_REVIEW')
    if node is not None:
        reasons.extend(node['content']['reasons'])
        if node['content']['raw']['cross_domain_status'] == 'QUARANTINED':
            reasons.append('HISTORICAL_QUARANTINE')
    return {
        'comparison_id': row['candidate_id'] or 'OBS_' + canonical_sha256(row)[:16].upper(),
        'candidate_id': row['candidate_id'] or None,
        'observed_name': name,
        'outcome': outcome,
        'target_node_id': target,
        'catalog_candidate_ids': matches,
        'retrieval': retrieval,
        'reasons': sorted(set(reasons)),
        'stage2_recommendation': recommendation,
        'stage2_human_decision': human_decision,
        'comparison_sha256': canonical_sha256(row),
        'candidate_content_sha256': node['content_sha256'] if node else None,
        'human_required': True,
    }


def relation_resolution(node, *, endpoints, existing, human=None):
    raw, content = node['content']['raw'], node['content']
    start, end = endpoints.get(raw['source_ref']), endpoints.get(raw['target_ref'])
    human_decision = (human or {}).get('human_input', {}).get('decision')
    reasons = list(content['reasons'])
    signature = (start, raw['relation_type'], end, raw['scope'])
    matching = [r for r in existing if
                (r['from_node_id'], r['relation_type'], r['to_node_id'], r['scope']) == signature]
    exact = sorted(r['relation_id'] for r in matching)
    temporal = content['temporal_projection']
    temporal_compatible = all(r.get('status') == temporal.get('runtime_status') and
                              r.get('valid_from') == temporal.get('valid_from') and
                              r.get('valid_to') == temporal.get('valid_to') and
                              r.get('temporal_category') == temporal.get('temporal_category')
                              for r in matching)
    if human_decision in ('DEFER', 'REJECT'):
        outcome = human_decision + '_RELATION'
        reasons.append('FROZEN_STAGE2_HUMAN_DECISION')
    elif raw['disposition'] == 'REJECT':
        outcome = 'REJECT_RELATION'
        reasons.append('FROZEN_STAGE2_REJECTION')
    elif raw['relation_type'] not in RELATION_TYPES or 'ONTOLOGY_PRESSURE' in reasons:
        outcome = 'DEFER_RELATION'
        reasons.append('ONTOLOGY_PRESSURE')
    elif 'PARENT_CYCLE' in reasons:
        outcome = 'DEFER_RELATION'
    elif not start or not end or start == end:
        outcome = 'DEFER_RELATION'
        reasons.append('ENDPOINT_AMBIGUITY')
    elif not content['evidence_bound'] or raw['direction_check'] != 'PASS' or raw['entailment_check'] != 'PASS':
        outcome = 'DEFER_RELATION'
        reasons.append('EVIDENCE_OR_DIRECTION_REVIEW')
    elif raw['existing_relation_id'] and raw['existing_relation_id'] not in exact:
        outcome = 'DEFER_RELATION'
        reasons.append('EXISTING_RELATION_TARGET_MISMATCH')
    elif len(exact) > 1:
        outcome = 'DEFER_RELATION'
        reasons.append('DUPLICATE_CANONICAL_RELATIONS')
    elif exact and not temporal_compatible:
        outcome = 'DEFER_RELATION'
        reasons.append('TEMPORAL_MISMATCH')
    elif exact:
        outcome = 'REUSE_RELATION'
        reasons.append('EXACT_ENDPOINT_TYPE_SCOPE_MATCH')
    else:
        outcome = 'CREATE_RELATION'
        reasons.append('DISTINCT_RELATION_PROPOSAL')
    return {
        'candidate_id': node['candidate_id'], 'outcome': outcome,
        'from_node_id': start, 'to_node_id': end,
        'relation_type': raw['relation_type'], 'scope': raw['scope'],
        'temporal_status': raw['temporal_status'],
        'temporal_projection': content['temporal_projection'],
        'existing_relation_ids': exact,
        'evidence_refs': content['evidence_refs'],
        'native_evidence': content['native_evidence'],
        'reasons': sorted(set(reasons)),
        'stage2_human_decision': human_decision,
        'candidate_content_sha256': node['content_sha256'],
        'human_required': True,
    }


def build(*, package_path, production_path, authorization_path, output_root):
    require(git('rev-parse', 'origin/main') == BASELINE, 'remote main drift')
    require(git('rev-parse', '--abbrev-ref', 'HEAD') == BRANCH, 'branch drift')
    subprocess.check_call(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', BASELINE, 'HEAD'])
    require(output_root.resolve().is_relative_to((ROOT / 'workspace').resolve()), 'artifact store outside workspace')
    require(not production_path.resolve().is_relative_to(output_root.resolve()), 'artifact store contains Production')
    before = sha256_file(production_path)
    require(before == PRODUCTION_SHA, 'Production baseline drift')
    package = read_package(package_path)
    require(package['sha256'] == PACKAGE_SHA, 'Stage 2 package drift')
    public_contract = json.loads((ROOT / 'docs/phase43_stage2_web_pro_backfill_import_contract.json').read_text('utf-8'))
    receipt = json.loads((ROOT / 'docs/phase43_stage2_final_human_qualification_receipt.json').read_text('utf-8'))
    require(public_contract['package_sha256'] == package['sha256'], 'Stage 2 contract package drift')
    require(public_contract['production_sha256'] == before, 'Stage 2 contract Production drift')
    require(receipt['result'] == 'PASS' and receipt['production']['write_count'] == 0, 'Stage 2 qualification drift')
    authorization_bytes = authorization_path.read_bytes().replace(b'\r\n', b'\n')
    frozen_authorization = subprocess.check_output(['git', '-C', str(ROOT), 'show',
        'HEAD:docs/phase43_stage2_human_authorization.json'])
    require(authorization_bytes == frozen_authorization and
            hashlib.sha256(frozen_authorization).hexdigest() == AUTH_SHA == receipt['authorization_file_sha256'],
            'Stage 2 human authorization drift')
    authorization = json.loads(authorization_bytes)
    require(not authorization['production_apply_authorized'] and not authorization['current_view_write_authorized'], 'Stage 2 authority drift')
    contract = freeze_contract(package, pack_root=ROOT / 'domains/semiconductor', production_path=production_path,
                               target_root=output_root, repository_commit=public_contract['repository_commit'],
                               runtime_sha256=runtime_digest())
    packet, report = qualify(package, contract, knowledge_db=production_path, pack_root=ROOT / 'domains/semiconductor')
    require(packet['immutable_packet_sha256'] == receipt['native_qualification']['parent_immutable_packet_sha256'], 'Stage 2 frozen packet drift')
    validate_review(packet, expected_sha256=packet['immutable_packet_sha256'], completed=False)
    nodes = {r['candidate_id']: r for r in packet['objects']['nodes']}
    humans = {r['item_id']: r for r in authorization['decisions']}
    require(len(humans) == len(authorization['decisions']) == 105, 'Stage 2 human decision population drift')
    all_items = {r['candidate_id']: (kind, r) for kind, rows in packet['objects'].items() for r in rows}
    require(len(all_items) == 274 and all(d['item_id'] in all_items and
            d['object_type'] == all_items[d['item_id']][0] and
            d['native_content_sha256'] == all_items[d['item_id']][1]['content_sha256'] for d in authorization['decisions']),
            'Stage 2 human content binding drift')
    evidence = {r['evidence_id']: r for r in package['tables']['evidence']}
    sources = {r['source_id']: r for r in package['tables']['sources']}
    with connect_read_only(production_path) as connection:
        canonical = {t: [dict(r) for r in connection.execute('SELECT * FROM ' + t + ' ORDER BY rowid')]
                     for t in ('nodes', 'node_aliases', 'node_relations')}
        temporal_categories = {r['relation_id']: r['temporal_category'] for r in
            connection.execute('SELECT relation_id,temporal_category FROM relation_temporal_semantics')}
        for relation in canonical['node_relations']:
            relation['temporal_category'] = temporal_categories.get(relation['relation_id'])
    catalog = build_identity_catalog(canonical['nodes'], canonical['node_aliases'])
    comparisons = package['tables']['cross_domain_reconciliation.csv']
    require(len(comparisons) == 46, 'Stage 2 comparison population drift')
    require(len({r['candidate_id'] for r in comparisons if r['candidate_id']}) == 43, 'duplicate comparison candidate')
    identities = []
    review = []
    cross_by_id = {}
    for row in comparisons:
        node = nodes.get(row['candidate_id']) if row['candidate_id'] else None
        require(not row['candidate_id'] or node is not None, 'missing Stage 2 candidate')
        refs = json_array(row['new_source_evidence'])
        bound = evidence_for(refs, evidence, sources, allow_empty=node is None)
        if node is not None:
            require(set(refs) <= set(node['content']['evidence_refs']), 'cross comparison evidence drift')
        result = identity_resolution(row, node, catalog, humans.get(row['candidate_id']))
        result['evidence_refs'] = refs
        identities.append(result)
        if row['candidate_id']:
            cross_by_id[row['candidate_id']] = result
        review.append({'kind': 'identity', 'item_id': result['comparison_id'], 'resolution': result,
                       'frozen_comparison': row, 'frozen_candidate': node,
                       'evidence': bound, 'human_input': {'decision': '', 'target_id': '', 'reason': ''}})
    endpoints = {}
    for cid, node in nodes.items():
        human_decision = humans.get(cid, {}).get('human_input', {}).get('decision')
        if cid in cross_by_id:
            endpoints[cid] = cross_by_id[cid]['target_node_id']
        elif human_decision not in ('DEFER', 'REJECT') and node['content']['classification'] in ('REUSE', 'CREATE'):
            endpoints[cid] = node['content']['resolved_node_id']
    endpoints.update({n['node_id']: n['node_id'] for n in canonical['nodes'] if n['status'] == 'active'})
    relations = []
    for node in packet['objects']['relations']:
        result = relation_resolution(node, endpoints=endpoints, existing=canonical['node_relations'], human=humans.get(node['candidate_id']))
        bound = evidence_for(result['evidence_refs'], evidence, sources)
        native = result['native_evidence']
        if native:
            evidence_for([native['evidence_ref']], evidence, sources, source_id=native['evidence_source_id'])
        relations.append(result)
        review.append({'kind': 'relation', 'item_id': result['candidate_id'], 'resolution': result,
                       'frozen_candidate': node, 'evidence': bound,
                       'human_input': {'decision': '', 'target_id': '', 'reason': ''}})
    claims = []
    for node in packet['objects']['claims']:
        content = node['content']
        require(content['evidence_bound'], 'claim evidence unbound')
        refs = [r['evidence_id'] for r in content['evidence']]
        bound = evidence_for(refs, evidence, sources, source_id=content['source_id'])
        require(all(r['source_sha256'] == content['source_sha256'] for r in bound), 'claim source hash drift')
        claims.append({'candidate_id': node['candidate_id'], 'content_sha256': node['content_sha256'],
                       'source_id': content['source_id'], 'source_sha256': content['source_sha256'],
                       'evidence': bound, 'temporal_category': content['temporal_category'],
                       'fact_time': content['row']['fact_time'], 'publication_time': content['row']['publication_time'],
                       'candidate': node})
    require(all(r['outcome'] in IDENTITY_OUTCOMES for r in identities) and
            all(r['outcome'] in RELATION_OUTCOMES for r in relations), 'unclassified comparison')
    population = {'stage2_packet_sha256': packet['immutable_packet_sha256'],
                  'stage2_package_sha256': package['sha256'], 'production_sha256': before,
                  'authorization_sha256': AUTH_SHA,
                  'comparisons': [{'id': r['comparison_id'], 'sha256': r['comparison_sha256']} for r in identities],
                  'relations': [{'id': r['candidate_id'], 'sha256': r['candidate_content_sha256']} for r in relations]}
    bundle = {'document_type': 'phase43_stage3_cross_domain_resolution',
              'baseline': BASELINE, 'population_sha256': canonical_sha256(population),
              'population': population, 'identities': identities, 'relations': relations,
              'claim_provenance': claims, 'stage2_candidate_counts': packet['counts'],
              'production_apply_executed': False, 'official_view_activations': 0}
    structural_sha = canonical_sha256(bundle)
    handoff = {'document_type': 'phase43_stage3_portable_review_handoff',
               'population_sha256': bundle['population_sha256'], 'structural_sha256': structural_sha,
               'items': review, 'stage3_human_decisions_applied': 0,
               'stage2_human_decisions_preserved': 105, 'stage2_unreviewed_preserved': 169,
               'page_size': 25, 'production_apply_authorized': False}
    output_root.mkdir(parents=True, exist_ok=True)
    handoff_text = ('# Phase 4.3 Stage 3 portable review handoff\n\n'
                    f'Population SHA-256: `{bundle["population_sha256"]}`\n\n'
                    f'Structural SHA-256: `{structural_sha}`\n\n'
                    f'Items: {len(review)}; page size: 25. All Stage 3 human decisions are blank.\n\n'
                    'Review `review_population.json` in 25-item pages. Each record includes the '
                    'frozen comparison or candidate, evidence, source identity, proposed outcome, '
                    'reasons, and an empty human-input field. Bind any later HUMAN_USER decisions '
                    'to the population and content hashes; do not edit these frozen files. '
                    'This handoff grants no Production or Official View write authority.\n')
    replay = {}
    for label in ('a', 'b'):
        base = output_root / label
        added = [immutable_write(base / name, frozen_bytes(value)) for name, value in
                 (('resolution.json', bundle), ('review_population.json', handoff))]
        added.append(immutable_write(base / 'review_handoff.md', handoff_text.encode('utf-8')))
        replay[label] = {'new_files': sum(added), 'structural_sha256': canonical_sha256(bundle),
                         'review_sha256': canonical_sha256(handoff)}
    require(replay['a']['structural_sha256'] == replay['b']['structural_sha256'] and
            replay['a']['review_sha256'] == replay['b']['review_sha256'], 'two-workspace structural drift')
    after = sha256_file(production_path)
    require(after == before, 'Production mutation')
    collisions = sum(len(r['catalog_candidate_ids']) > 1 or
                     any(reason in r['reasons'] for reason in ('TYPE_MISMATCH', 'IDENTITY_TARGET_OR_STATUS_REVIEW'))
                     for r in identities)
    result = {'status': 'AUTOMATED_RESOLUTION_PASS_REGRESSION_PENDING', 'baseline': BASELINE,
              'ai_hardware_input_sha256': before, 'semiconductor_input_sha256': package['sha256'],
              'ai_hardware_nodes': len(canonical['nodes']), 'semiconductor_nodes': len(nodes),
              'comparison_candidates': len(identities), 'population_sha256': bundle['population_sha256'],
              'identity_resolution': dict(Counter(r['outcome'] for r in identities)),
              'cross_domain_collisions': collisions,
              'unresolved_identity_conflicts': sum(r['outcome'] == 'DEFER' for r in identities),
              'ontology_pressure_cases': sum('ONTOLOGY_PRESSURE' in r['reasons'] for r in (*identities, *relations)),
              'relation_resolution': dict(Counter(r['outcome'] for r in relations)),
              'relations_compared': len(relations), 'claim_provenance_preserved': len(claims),
              'cross_source_leakage': 0, 'mandatory_exceptions': len(review),
              'human_required': len(review), 'residual_eligible': 0,
              'final_human_qualification': 'PENDING', 'workspace_a_sha': replay['a']['structural_sha256'],
              'workspace_b_sha': replay['b']['structural_sha256'], 'structural_match': True,
              'idempotent_replay': all(v['new_files'] == 0 for v in replay.values()),
              'production_sha_before': before, 'production_sha_after': after,
              'production_write_count': 0, 'apply_executed': False, 'official_view_activations': 0,
              'stage2_packet_sha256': packet['immutable_packet_sha256'],
              'stage2_qualification_unchanged': True, 'provider_calls': report['provider_calls'],
              'raw_source_extraction_calls': report['raw_source_extraction_calls']}
    immutable_write(output_root / 'qualification_result.json', frozen_bytes({k: v for k, v in result.items() if k != 'idempotent_replay'}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=ROOT / 'semiconductor_foundation_backfill_web_pro_v1')
    parser.add_argument('--production', type=Path, default=ROOT / 'workspace/pro_a.db')
    parser.add_argument('--authorization', type=Path, default=ROOT / 'docs/phase43_stage2_human_authorization.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'workspace/phase4_stage43_stage3_cross_domain_resolution/qualified_v3')
    args = parser.parse_args()
    print(json.dumps(build(package_path=args.package, production_path=args.production,
                           authorization_path=args.authorization, output_root=args.output), ensure_ascii=False, indent=2))
