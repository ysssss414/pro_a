"""Build the portable, presentation-only Stage 4D qualified overlay."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from pro_a.production_promotion import canonical_sha256, sha256_file

ROOT = Path(__file__).resolve().parents[1]
STAGE3_REVIEW = ROOT / 'workspace/phase4_stage43_stage3_cross_domain_resolution/qualified_v3/a/review_population.json'
STAGE3_RESOLUTION = STAGE3_REVIEW.with_name('resolution.json')
DECISIONS = ROOT / 'docs/phase43_stage3_human_decisions_completed.json'
STAGE2_AUTH = ROOT / 'docs/phase43_stage2_human_authorization.json'
STAGE2_PACKET = ROOT / 'docs/phase43_stage2_human_qualification_packet.json'
STAGE3_RECEIPT = ROOT / 'docs/phase43_stage3_final_human_qualification_receipt.json'
PRODUCTION = ROOT / 'workspace/pro_a.db'
OUTPUT = ROOT / 'research_overlay/phase43_stage3_cross_domain_v1.json'
AUTHORITY_OUTPUT = ROOT / 'docs/phase43_stage4d_endpoint_authority.json'
MANIFEST_OUTPUT = ROOT / 'docs/phase43_stage4d_overlay_source_manifest.json'

EXPECTED = {
    'production_sha256': '6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1',
    'stage2_human_authorization_sha256': '23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f',
    'stage2_packet_sha256': '3faee260ecce3542d12a114fe24f17242a591630258f4ea477acaf7fd21a19be',
    'stage3_completed_decisions_sha256': '34f91757f881e26f87502e1ae096ec24b8e207d85ba218d5be8179867940ef52',
    'stage3_review_population_sha256': '2ec173f05215e9d62323ff1cde07108fbcf5eab1afcaf6a020ee438875f04a92',
    'stage3_automated_resolution_sha256': '4ee619c8d597f6ffcacb357efd7eddce750b1a2bc6fe3a21c7a9a78f182f4065',
    'stage3_population_sha256': '207f4f57f78f0fe0034a3bb17edd38cc911a21cd322ea753ac02edc41a70babb',
}
STAGE3_RECEIPT_SHA = '4a68d3ff7dcd5ac2c2f3b77664d12ede295adf1885c30c2bd14397c797a9cde5'
SEMICONDUCTOR_PACKAGE_SHA = '131421d3bbe3b968a1c72ee6e3767cfad6141a0cdaea1850ba30cccbd3932918'
STAGE2_SUPPORT = {'SC-CN-' + value for value in (
    '0004', '0006', '0007', '0009', '0100', '0101', '0060', '0034', '0046',
    '0056', '0072', '0073', '0074', '0161', '0088', '0090', '0120')}
REFERENCE_IDS = {'SC-CN-' + value for value in (
    '0008', '0024', '0039', '0040', '0041', '0044', '0047', '0048', '0053',
    '0058', '0059', '0062', '0064', '0065', '0067', '0068', '0069', '0076',
    '0079', '0080', '0103', '0104', '0105', '0106', '0119', '0160')}


def require(value, detail):
    if not value:
        raise ValueError('QUALIFIED_OVERLAY_BINDING_FAILED: ' + detail)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def safe(value, limit=500):
    value = str(value or '').strip()
    require(len(value) <= limit and not any(ch in value for ch in ('\\', '\r', '\n', '\0')),
            'unsafe or oversized public field')
    require(not (len(value) > 2 and value[1:3] == ':/'), 'local path')
    return value


def evidence(item):
    return [{
        'evidence_id': safe(row['evidence_id'], 100),
        'source_id': safe(row['source_id'], 100),
        'source_title': safe(row.get('filename'), 200),
        'section': safe(row.get('section'), 160),
        'pdf_page': row.get('pdf_page'),
        'as_of_date': safe(row.get('as_of_date'), 40),
        'excerpt': safe(row.get('evidence_excerpt', '')[:360], 360),
    } for row in item.get('evidence', [])[:8]]


def write_exact(path, value):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def build():
    require(sha256_file(STAGE3_RECEIPT) == STAGE3_RECEIPT_SHA, 'Stage 3 final receipt')
    for name, path in (
        ('production_sha256', PRODUCTION),
        ('stage2_human_authorization_sha256', STAGE2_AUTH),
        ('stage2_packet_sha256', STAGE2_PACKET),
        ('stage3_completed_decisions_sha256', DECISIONS),
        ('stage3_review_population_sha256', STAGE3_REVIEW),
        ('stage3_automated_resolution_sha256', STAGE3_RESOLUTION),
    ):
        require(sha256_file(path) == EXPECTED[name], name)
    a2, a3, packet, review, resolution = map(read, (STAGE2_AUTH, DECISIONS, STAGE2_PACKET, STAGE3_REVIEW, STAGE3_RESOLUTION))
    receipt = read(STAGE3_RECEIPT)
    require(receipt['binding_result'] == 'PASS' and
            receipt['semiconductor_input_sha256'] == SEMICONDUCTOR_PACKAGE_SHA and
            receipt['review_population_file_sha256'] == EXPECTED['stage3_review_population_sha256'] and
            receipt['completed_decision_file_sha256'] == EXPECTED['stage3_completed_decisions_sha256'],
            'Stage 3 final receipt binding')
    require(a3['population_sha256'] == review['population_sha256'] ==
            resolution['population_sha256'] == EXPECTED['stage3_population_sha256'], 'Stage 3 population')
    d2 = {row['item_id']: row for row in a2['decisions']}
    d3 = {row['item_id']: row for row in a3['decisions']}
    p2 = {row['candidate_id']: row for row in packet['items']}
    items = {row['item_id']: row for row in review['items']}
    require(len(d3) == len(items) == 100 and set(d3) == set(items), '100 decision population')
    require(all(row['reviewer'] == 'HUMAN_USER' for row in d3.values()), 'Stage 3 reviewer')
    for cid, decision in d3.items():
        item = items[cid]
        require(decision['parent_item_sha256'] == canonical_sha256(item), 'parent item ' + cid)
        candidate = item['frozen_candidate']
        require(decision['candidate_content_sha256'] == item['resolution']['candidate_content_sha256'] ==
                (candidate['content_sha256'] if candidate else None), 'candidate content ' + cid)
        require(candidate is not None or decision['human_user_decision'] == 'DEFER',
                'unbound active candidate ' + cid)
        require(decision['object_type'] == item['kind'], 'object type ' + cid)
    identity_counts = Counter(row['human_user_decision'] for row in d3.values() if row['object_type'] == 'identity')
    relation_counts = Counter(row['human_user_decision'] for row in d3.values() if row['object_type'] == 'relation')
    require(identity_counts == {'REUSE_CANONICAL': 19, 'CREATE_NEW_CANONICAL': 12, 'DEFER': 14, 'REJECT': 1},
            'identity counts')
    require(relation_counts == {'CREATE_RELATION': 38, 'DEFER_RELATION': 16}, 'relation counts')
    with sqlite3.connect(f'{PRODUCTION.resolve().as_uri()}?mode=ro', uri=True) as conn:
        active = {row[0]: {'display_name': row[1], 'primary_type': row[2]}
                  for row in conn.execute("SELECT node_id,canonical_name,primary_type FROM nodes WHERE status='active'")}
        current_relations = {(row[0], row[1], row[2], row[3]) for row in
                             conn.execute("SELECT from_node_id,relation_type,to_node_id,scope FROM node_relations WHERE status='current'")}
    identities = {'reuse': [], 'stage3_create': [], 'stage2_support': [], 'deferred': [], 'rejected': []}
    for cid, decision in sorted(d3.items()):
        if decision['object_type'] != 'identity':
            continue
        item = items[cid]
        content = item['frozen_candidate']['content'] if item['frozen_candidate'] else None
        row = {
            'candidate_id': cid, 'candidate_content_sha256': decision['candidate_content_sha256'],
            'display_name': safe(content['canonical_name'] if content else item['resolution']['observed_name'], 180),
            'primary_type': safe(content['primary_type'] if content else 'Unadmitted observation', 80),
            'human_decision': decision['human_user_decision'],
            'human_reason': safe(decision['human_user_reason'], 600),
            'authorization_basis': safe(decision['authorization_basis'], 100),
            'reviewer': 'HUMAN_USER', 'qualification_stage': 'Stage 3',
            'evidence': evidence(item),
            'qualification_population_sha256': EXPECTED['stage3_population_sha256'],
            'qualification_decision_sha256': EXPECTED['stage3_completed_decisions_sha256'],
            'production_applied': False,
        }
        outcome = decision['human_user_decision']
        if outcome == 'REUSE_CANONICAL':
            target = decision['target_id']
            require(target in active, 'inactive reuse target ' + cid)
            row['reuse_target_node_id'] = target
            identities['reuse'].append(row)
        elif outcome == 'CREATE_NEW_CANONICAL':
            row['visual_id'] = 'qualified-stage3:' + cid
            identities['stage3_create'].append(row)
        elif outcome == 'DEFER':
            identities['deferred'].append({**row, 'research_eligible': False, 'map_eligible': False})
        else:
            identities['rejected'].append({**row, 'research_eligible': False, 'map_eligible': False})
    used_stage2, refs, endpoint_occurrences = set(), {}, []
    create_relations, deferred_relations = [], []
    for cid, decision in sorted(d3.items()):
        if decision['object_type'] != 'relation':
            continue
        item = items[cid]
        raw = item['frozen_candidate']['content']['raw']
        if decision['human_user_decision'] == 'DEFER_RELATION':
            deferred_relations.append({
                'candidate_id': cid, 'human_decision': 'DEFER_RELATION',
                'human_reason': safe(decision['human_user_reason'], 600),
                'from_label': safe(raw['source_name'], 180), 'to_label': safe(raw['target_name'], 180),
                'relation_type': safe(raw['relation_type'], 80),
                'research_eligible': False, 'map_eligible': False,
            })
            continue
        endpoints = []
        for side, label in (('source', 'from'), ('target', 'to')):
            ref = raw[side + '_ref']
            if ref in active:
                authority, visual, source_sha, source_decision = ('production_canonical', 'canonical:' + ref,
                    EXPECTED['production_sha256'], 'active')
            elif ref in d3:
                authority, source_sha, source_decision = ('stage3_human_identity',
                    EXPECTED['stage3_completed_decisions_sha256'], d3[ref]['human_user_decision'])
                require(source_decision in ('REUSE_CANONICAL', 'CREATE_NEW_CANONICAL'), 'Stage 3 endpoint conflict ' + cid)
                visual = ('canonical:' + d3[ref]['target_id'] if source_decision == 'REUSE_CANONICAL'
                          else 'qualified-stage3:' + ref)
            elif ref in d2:
                authority, source_sha, source_decision = ('stage2_human_identity',
                    EXPECTED['stage2_human_authorization_sha256'], d2[ref]['human_user_decision'])
                require(d2[ref]['reviewer'] == 'HUMAN_USER' and d2[ref]['object_type'] == 'nodes' and
                        source_decision == 'CREATE', 'Stage 2 endpoint conflict ' + cid)
                require(ref in p2 and p2[ref]['candidate_type'] == 'nodes' and
                        all(p2[ref][role]['content_sha256'] == d2[ref]['native_content_sha256']
                            for role in ('ai_review_a', 'ai_review_b')), 'Stage 2 content binding ' + ref)
                used_stage2.add(ref)
                visual = 'qualified-stage2:' + ref
            else:
                authority, visual, source_sha, source_decision = ('relation_scoped_reference',
                    'endpoint-ref:' + ref, EXPECTED['stage3_completed_decisions_sha256'], 'RELATION_ONLY')
                require(ref.startswith('SC-CN-'), 'unknown endpoint ' + cid)
                name = safe(raw[side + '_name'], 180)
                require(ref not in refs or refs[ref]['display_name'] == name, 'ambiguous endpoint label ' + ref)
                refs[ref] = {'candidate_ref': ref, 'visual_id': visual, 'display_name': name,
                             'primary_type': 'Unqualified reference', 'knowledge_state': 'relation_endpoint_reference',
                             'identity_qualified': False, 'relation_qualified': True,
                             'research_eligible': False, 'search_eligible': False,
                             'hierarchy_eligible': False, 'canonical_eligible': False,
                             'current_view_eligible': False, 'direct_impact_eligible': False,
                             'relation_anchor_eligible': True}
            require(not visual.startswith('canonical:') or visual[10:] in active, 'canonical endpoint missing ' + cid)
            endpoint = {'candidate_ref': ref, 'authority': authority, 'decision': source_decision,
                        'target': visual, 'visual_id': visual, 'source_artifact_sha256': source_sha}
            endpoints.append(endpoint)
            endpoint_occurrences.append({'relation_id': cid, 'side': label, **endpoint})
        if all(endpoint['visual_id'].startswith('canonical:') for endpoint in endpoints):
            require((endpoints[0]['visual_id'][10:], raw['relation_type'], endpoints[1]['visual_id'][10:],
                     raw['scope']) not in current_relations, 'canonical relation drift ' + cid)
        create_relations.append({
            'candidate_id': cid, 'visual_id': 'qualified:' + cid,
            'candidate_content_sha256': decision['candidate_content_sha256'],
            'from_visual_id': endpoints[0]['visual_id'], 'to_visual_id': endpoints[1]['visual_id'],
            'from_endpoint_authority': endpoints[0]['authority'],
            'to_endpoint_authority': endpoints[1]['authority'],
            'relation_type': safe(raw['relation_type'], 80), 'scope': safe(raw['scope'], 240),
            'temporal_status': safe(raw['temporal_status'], 80),
            'temporal_projection': item['frozen_candidate']['content']['temporal_projection'],
            'human_decision': 'CREATE_RELATION', 'human_reason': safe(decision['human_user_reason'], 600),
            'authorization_basis': safe(decision['authorization_basis'], 100),
            'reviewer': 'HUMAN_USER', 'qualification_stage': 'Stage 3',
            'evidence': evidence(item),
            'qualification_population_sha256': EXPECTED['stage3_population_sha256'],
            'qualification_decision_sha256': EXPECTED['stage3_completed_decisions_sha256'],
            'production_applied': False,
        })
    require(used_stage2 == STAGE2_SUPPORT, '17 Stage 2 support set')
    require(set(refs) == REFERENCE_IDS, '26 reference set')
    for ref in sorted(used_stage2):
        decision, packet_item = d2[ref], p2[ref]
        summary = packet_item['candidate_summary']
        identities['stage2_support'].append({
            'candidate_id': ref, 'visual_id': 'qualified-stage2:' + ref,
            'candidate_content_sha256': decision['native_content_sha256'],
            'display_name': safe(summary['名称'], 180), 'primary_type': safe(summary['Node 类型'], 80),
            'human_decision': 'CREATE', 'human_reason': safe(decision['human_input']['reason'], 600),
            'authorization_basis': 'Stage 2 HUMAN_USER authorization', 'reviewer': 'HUMAN_USER',
            'qualification_stage': 'Stage 2', 'evidence': [{
                'evidence_id': safe(row['evidence_id'], 100),
                'source_id': safe(row['source_id'], 100), 'section': safe(row.get('section'), 160),
                'pdf_page': row.get('pdf_page'), 'source_sha256': row['source_sha256']}
                for row in packet_item['evidence_pointers'][:8]],
            'qualification_population_sha256': SEMICONDUCTOR_PACKAGE_SHA,
            'qualification_decision_sha256': EXPECTED['stage2_human_authorization_sha256'],
            'production_applied': False,
        })
    reference_backed = sum('relation_scoped_reference' in
                           (row['from_endpoint_authority'], row['to_endpoint_authority']) for row in create_relations)
    require(len(create_relations) == 38 and len(endpoint_occurrences) == 76 and reference_backed == 21,
            '38/38 relation renderability')
    overlay = {
        'overlay_id': 'phase43-stage3-cross-domain-qualified-v1',
        'contract_version': 'qualified-overlay-v1', 'qualification_stage': 'Phase 4.3 Stage 3 + Stage 2 endpoint support',
        'source_bindings': EXPECTED, 'identities': identities,
        'endpoint_references': [refs[key] for key in sorted(refs)],
        'relations': {'create': create_relations, 'deferred': deferred_relations},
        'counts': {'stage3_identity': dict(identity_counts), 'stage3_relation': dict(relation_counts),
                   'stage2_support': len(used_stage2), 'endpoint_references': len(refs),
                   'relation_endpoint_occurrences': len(endpoint_occurrences),
                   'full_identity_authority_relations': 38 - reference_backed,
                   'reference_backed_relations': reference_backed,
                   'unique_reuse_targets': len({row['reuse_target_node_id'] for row in identities['reuse']})},
    }
    overlay['overlay_sha256'] = canonical_sha256(overlay)
    authority = {'contract_version': 'qualified-endpoint-authority-v1',
                 'overlay_sha256': overlay['overlay_sha256'], 'endpoints': endpoint_occurrences}
    manifest = {**EXPECTED, 'overlay_id': overlay['overlay_id'], 'overlay_sha256': overlay['overlay_sha256'],
                'overlay_file_sha256': None, 'stage2_packet_file_sha256': EXPECTED['stage2_packet_sha256'],
                'stage2_semiconductor_package_sha256': SEMICONDUCTOR_PACKAGE_SHA,
                'stage3_final_receipt_sha256': STAGE3_RECEIPT_SHA,
                'overlay_builder_code_sha256': sha256_file(Path(__file__))}
    if __name__ == '__main__':
        manifest['overlay_file_sha256'] = write_exact(OUTPUT, overlay)
        write_exact(AUTHORITY_OUTPUT, authority)
        write_exact(MANIFEST_OUTPUT, manifest)
    return overlay


if __name__ == '__main__':
    result = build()
    print(json.dumps({'overlay_sha256': result['overlay_sha256'], 'counts': result['counts']}, sort_keys=True))
