"""Apply exact HUMAN_USER Stage 3 decisions to an isolated native review copy."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from pro_a.production_promotion import canonical_sha256, sha256_file
from scripts import build_phase43_stage3_double_review as frozen

PRE_HUMAN_HEAD = '1c9c6efc65d136325d9f315b9635582d1535d5ee'
AUTH_SOURCE_SHA = '38c2a8c0d0390708378f9211baaa6f17551219d16b7aee33ff4d300d44e1ff89'
PACKET_SHA = '163cb649d5c76a9a76e767fb3f065048f57d2fbd2e2c9ac9c48f7ef395cc9234'
TEMPLATE_SHA = '3d39f049ce90a9cb5123c1ca5e8bb95b62af6d9173febcef95bd0730d52b9f7f'
REVIEW_A_SHA = '900ca5e8201fbb3f226e0feb794e99e8b69ed1c1b62e9a85ef9aba4821a08a88'
REVIEW_B_SHA = '17eb1858137471393e3289e7a54b42e3ed12c7065a2d064cd43a73ba1b83852b'
RECONCILIATION_SHA = '78d46a200a202a4a1ce5d5ccb2a684577d5ca0d4c0ab227833301dd3578d76d4'
DOUBLE_VALIDATION_SHA = '182e66974abd073d726808610094bd459e5c4d952d357833e187d7646e5fcf48'
STAGE2_AUTH_SHA = '23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f'
EXPECTED_IDENTITY = {'REUSE_CANONICAL': 19, 'CREATE_NEW_CANONICAL': 12,
                     'KEEP_DOMAIN_SPECIFIC': 0, 'DEFER': 14, 'REJECT': 1}
EXPECTED_RELATION = {'REUSE_RELATION': 0, 'CREATE_RELATION': 38,
                     'KEEP_DOMAIN_SPECIFIC_RELATION': 0, 'DEFER_RELATION': 16,
                     'REJECT_RELATION': 0}
OVERRIDES = {
    'SC-CN-0033': ('CREATE_NEW_CANONICAL', '',
                   'Chiplet is a physical companion/small die Product, distinct from Chiplet Architecture / Technology. The bound Intel evidence establishes a durable independent concept.'),
    'SC-CN-0051': ('REUSE_CANONICAL', 'NODE_20260817_7A9AE357',
                   'Silicon-On-Insulator Wafers is the plural expression of the existing Silicon-on-Insulator Wafer Material. The source section and construction support the same material; no second canonical Node.'),
    'SC-CN-0031': ('CREATE_NEW_CANONICAL', '',
                   'Package Substrate is a generic package-foundation Product spanning organic laminate, ceramic and glass, broader than Advanced Package Substrate.'),
    'SC-CN-0042': ('CREATE_NEW_CANONICAL', '',
                   'Silicon Wafer Polishing is a starting-wafer mirror-polishing Technology, distinct from Advanced Packaging CMP Equipment and fabrication CMP in stage, type and scope; SUMCO evidence supports it.'),
}
STORE = frozen.ARTIFACT / 'human_qualification'


def require(condition, message):
    if not condition:
        raise ValueError('STAGE3_HUMAN_AUTHORIZATION_BINDING_FAIL: ' + message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def tracked_bytes(name, expected_sha):
    blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + name])
    require(digest(blob) == expected_sha, 'frozen Git blob drift: ' + name)
    require((ROOT / name).read_bytes().replace(b'\r\n', b'\n') == blob,
            'frozen worktree file drift: ' + name)
    return blob


def write_once(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == data, 'immutable completed artifact drift: ' + path.name)
    else:
        with path.open('xb') as stream:
            stream.write(data)


def packet_recommendations(markdown):
    """Bind the readable HUMAN_USER packet, including its A/B section membership."""
    sections = {}
    current = None
    for line in markdown.splitlines():
        if line.startswith('## Section A —'):
            current = 'A'
        elif line.startswith('## Section B —'):
            current = 'B'
        elif line.startswith('### Item '):
            match = re.fullmatch(r'### Item \d{3} — (\S+) — .+', line)
            require(match is not None and current is not None and match.group(1) not in sections,
                    'packet item heading')
            sections[match.group(1)] = {'section': current, 'recommendation': None}
        elif line.startswith('- SYSTEM_RECOMMENDED_DECISION:'):
            require(sections and current is not None, 'packet recommendation without item')
            match = re.fullmatch(r'- SYSTEM_RECOMMENDED_DECISION: `([^`]+)`\.', line)
            require(match is not None, 'packet recommendation syntax')
            last = next(reversed(sections))
            require(sections[last]['recommendation'] is None, 'duplicate packet recommendation')
            sections[last]['recommendation'] = match.group(1)
    require(len(sections) == 100 and all(v['recommendation'] for v in sections.values()) and
            Counter(v['section'] for v in sections.values()) == {'A': 96, 'B': 4},
            'packet 100-item A/B population')
    return sections


def validate_head():
    head = git('rev-parse', 'HEAD')
    remote = git('rev-parse', 'origin/codex/phase43-stage3-cross-domain-resolution')
    if head == PRE_HUMAN_HEAD:
        require(remote == PRE_HUMAN_HEAD, 'PR #65 head before qualification')
    else:
        require(git('rev-parse', 'HEAD^') == PRE_HUMAN_HEAD and
                remote in (PRE_HUMAN_HEAD, head),
                'qualification commit must directly descend from frozen PR #65 head')


def validate_frozen(authority_file):
    require(sha256_file(authority_file) == AUTH_SOURCE_SHA, 'HUMAN_USER authorization source')
    validate_head()
    items = frozen.check_binding()
    names = {
        'docs/PHASE43_STAGE3_HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md': PACKET_SHA,
        'docs/phase43_stage3_human_decision_template.json': TEMPLATE_SHA,
        'docs/phase43_stage3_ai_review_a.json': REVIEW_A_SHA,
        'docs/phase43_stage3_ai_review_b.json': REVIEW_B_SHA,
        'docs/phase43_stage3_ai_review_reconciliation.json': RECONCILIATION_SHA,
        'docs/phase43_stage3_double_review_validation.json': DOUBLE_VALIDATION_SHA,
    }
    for name, expected in names.items():
        tracked_bytes(name, expected)
    require(sha256_file(ROOT / 'docs/phase43_stage2_human_authorization.json') == STAGE2_AUTH_SHA,
            'Stage 2 HUMAN_USER decisions drift')
    result = read(frozen.ARTIFACT / 'qualification_result.json')
    require(result['production_sha_before'] == result['production_sha_after'] == frozen.PRODUCTION_SHA and
            result['stage2_packet_sha256'] == frozen.STAGE2_SHA and
            result['population_sha256'] == frozen.POPULATION_SHA,
            'automated Stage 3 binding drift')
    template = read(ROOT / 'docs/phase43_stage3_human_decision_template.json')['items']
    reconciliation = read(ROOT / 'docs/phase43_stage3_ai_review_reconciliation.json')['items']
    require([r['item_id'] for r in template] == [r['item_id'] for r in reconciliation] ==
            [r['item_id'] for r in items] and len(template) == 100,
            'frozen item identities/order')
    require(all(r['human_user_decision'] is None and
                r['system_recommended_decision'] == s['system_recommended_decision']
                for r, s in zip(template, reconciliation, strict=True)),
            'blank template / system recommendation drift')
    packet = packet_recommendations((ROOT / 'docs/PHASE43_STAGE3_HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md').read_text('utf-8'))
    require(all(packet[r['item_id']]['recommendation'] == r['system_recommended_decision'] and
                packet[r['item_id']]['section'] == ('A' if r['status'] == 'A_B_SUBSTANTIVE_AGREEMENT' else 'B')
                for r in reconciliation), 'self-contained packet/reconciliation drift')
    require({r['item_id'] for r in reconciliation if r['status'] == 'A_B_SUBSTANTIVE_DISAGREEMENT'} ==
            set(OVERRIDES), 'four-item adjudication scope')
    double = read(ROOT / 'docs/phase43_stage3_double_review_validation.json')
    require(double['result'] == 'PASS' and double['section_a'] == 96 and double['section_b'] == 4 and
            double['human_user_decisions_applied'] == 0, 'double-review qualification drift')
    return items, template, reconciliation, packet


def canonical_targets():
    path = ROOT / 'workspace/pro_a.db'
    require(sha256_file(path) == frozen.PRODUCTION_SHA, 'Production SHA before')
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA query_only=ON')
        return {row['node_id']: dict(row) for row in
                connection.execute('SELECT node_id,canonical_name,primary_type,status FROM nodes')}


def build_decisions(items, template, reconciliation, packet, catalog):
    review_a = {r['item_id']: r for r in read(ROOT / 'docs/phase43_stage3_ai_review_a.json')['items']}
    review_b = {r['item_id']: r for r in read(ROOT / 'docs/phase43_stage3_ai_review_b.json')['items']}
    decisions = []
    for item, blank, reviewed in zip(items, template, reconciliation, strict=True):
        item_id = item['item_id']
        section = packet[item_id]['section']
        recommendation = blank['system_recommended_decision']
        if section == 'A':
            decision, target = recommendation, ''
            reason = 'HUMAN_USER explicitly adopted the frozen SYSTEM_RECOMMENDED_DECISION; no independent item-level rationale was supplied.'
            require(reviewed['status'] == 'A_B_SUBSTANTIVE_AGREEMENT' and
                    review_a[item_id]['native_decision'] == review_b[item_id]['native_decision'] == decision,
                    'Section A recommendation/AI consensus drift: ' + item_id)
            if decision.startswith('REUSE_'):
                target = review_a[item_id]['target']
                require(target == review_b[item_id]['target'], 'Section A target conflict: ' + item_id)
        else:
            require(reviewed['status'] == 'A_B_SUBSTANTIVE_DISAGREEMENT' and item_id in OVERRIDES,
                    'Section B unexpected item: ' + item_id)
            decision, target, reason = OVERRIDES[item_id]
        allowed = frozen.IDENTITY if item['kind'] == 'identity' else frozen.RELATION
        require(decision in allowed, 'native decision vocabulary: ' + item_id)
        require(bool(target) == decision.startswith('REUSE_'), 'native target shape: ' + item_id)
        if decision == 'REUSE_CANONICAL':
            node = catalog.get(target)
            candidate = item['frozen_candidate']
            require(node is not None and node['status'] == 'active' and candidate is not None and
                    node['primary_type'] == candidate['content']['primary_type'],
                    'canonical target/type/status: ' + item_id)
            if item_id == 'SC-CN-0051':
                require(target == 'NODE_20260817_7A9AE357' and
                        node['canonical_name'] == 'Silicon-on-Insulator Wafer',
                        'explicit SOI Wafer target')
        if decision == 'CREATE_NEW_CANONICAL':
            require(item['frozen_candidate'] is not None and item['kind'] == 'identity',
                    'CREATE must bind admitted frozen Node candidate: ' + item_id)
        if decision == 'CREATE_RELATION':
            resolution = item['resolution']
            candidate = item['frozen_candidate']['content']
            require(resolution['outcome'] == 'CREATE_RELATION' and
                    resolution['from_node_id'] and resolution['to_node_id'] and
                    resolution['from_node_id'] != resolution['to_node_id'] and
                    resolution['relation_type'] == candidate['relation_type'] and
                    resolution['scope'] == candidate['scope'] and
                    resolution['temporal_projection'] == candidate['temporal_projection'] and
                    set(resolution['evidence_refs']) == set(candidate['evidence_refs']),
                    'frozen relation/evidence/temporal binding: ' + item_id)
        decisions.append({
            'item_id': item_id, 'object_type': item['kind'], 'section': section,
            'reviewer': 'HUMAN_USER', 'system_recommended_decision': recommendation,
            'human_user_decision': decision, 'target_id': target or None,
            'human_user_reason': reason,
            'authorization_basis': 'EXPLICIT_SECTION_A_ADOPTION' if section == 'A' else
                                   'EXPLICIT_SECTION_B_ADJUDICATION',
            'parent_item_sha256': canonical_sha256(item),
            'candidate_content_sha256': item['resolution']['candidate_content_sha256'],
            'human_input': {'decision': decision, 'target_id': target, 'reason': reason},
        })
    validate_decisions(decisions, items, template, reconciliation)
    return decisions


def validate_decisions(decisions, items, template, reconciliation):
    require(len(decisions) == len({r['item_id'] for r in decisions}) == 100,
            'exact 100 HUMAN_USER decisions')
    require([r['item_id'] for r in decisions] == [r['item_id'] for r in items] ==
            [r['item_id'] for r in template], 'decision population/order')
    require(Counter(r['section'] for r in decisions) == {'A': 96, 'B': 4} and
            all(r['reviewer'] == 'HUMAN_USER' for r in decisions),
            'reviewer / mandatory section routing')
    by_id = {r['item_id']: r for r in decisions}
    require(all(by_id[x]['human_user_decision'] == OVERRIDES[x][0] and
                (by_id[x]['target_id'] or '') == OVERRIDES[x][1] and
                by_id[x]['human_user_reason'] == OVERRIDES[x][2] for x in OVERRIDES),
            'four explicit overrides')
    for decision, item, blank, reviewed in zip(decisions, items, template, reconciliation, strict=True):
        require(decision['parent_item_sha256'] == canonical_sha256(item) and
                decision['candidate_content_sha256'] == item['resolution']['candidate_content_sha256'] and
                decision['system_recommended_decision'] == blank['system_recommended_decision'] ==
                reviewed['system_recommended_decision'] and
                decision['human_input'] == {
                    'decision': decision['human_user_decision'],
                    'target_id': decision['target_id'] or '',
                    'reason': decision['human_user_reason'],
                }, 'content, system recommendation, or native input drift')
        if decision['section'] == 'A':
            require(decision['human_user_decision'] == blank['system_recommended_decision'],
                    'Section A differs from frozen system recommendation')
    identity = Counter(r['human_user_decision'] for r in decisions if r['object_type'] == 'identity')
    relation = Counter(r['human_user_decision'] for r in decisions if r['object_type'] == 'relation')
    require({key: identity[key] for key in EXPECTED_IDENTITY} == EXPECTED_IDENTITY and
            {key: relation[key] for key in EXPECTED_RELATION} == EXPECTED_RELATION and
            sum(identity.values()) == 46 and sum(relation.values()) == 54,
            'expected aggregate decision counts')


def build_completed(parent, decisions):
    """Only outer Stage 3 human_input fields differ from the frozen native items."""
    completed = copy.deepcopy(parent)
    completed['document_type'] = 'phase43_stage3_completed_human_qualification'
    completed['stage3_human_decisions_applied'] = 100
    completed['qualification_scope'] = {
        'parent_review_population_sha256': frozen.POPULATION_SHA,
        'parent_review_file_sha256': frozen.REVIEW_FILE_SHA,
        'blank_template_git_blob_sha256': TEMPLATE_SHA,
        'authority_source_sha256': AUTH_SOURCE_SHA,
        'production_apply_authorized': False, 'official_view_activation_authorized': False,
        'full_operational_review_complete': False,
    }
    completed['human_completion'] = {'reviewer': 'HUMAN_USER', 'expected': 100,
                                     'applied': 100, 'missing': 0, 'extra': 0,
                                     'residual_sample_size': 0}
    for row, decision in zip(completed['items'], decisions, strict=True):
        require(row['item_id'] == decision['item_id'], 'native packet order')
        row['human_input'] = copy.deepcopy(decision['human_input'])
    validate_completed(parent, completed, decisions)
    return completed


def validate_completed(parent, completed, decisions):
    require(len(parent['items']) == len(completed['items']) == len(decisions) == 100,
            'native completion count')
    require(completed['population_sha256'] == parent['population_sha256'] == frozen.POPULATION_SHA and
            completed['structural_sha256'] == parent['structural_sha256'] == frozen.STRUCTURAL_SHA,
            'native completion population/structure')
    require(completed['qualification_scope']['production_apply_authorized'] is False and
            completed['qualification_scope']['official_view_activation_authorized'] is False and
            completed['qualification_scope']['full_operational_review_complete'] is False,
            'native completion authority boundary')
    for original, actual, decision in zip(parent['items'], completed['items'], decisions, strict=True):
        require(actual['human_input'] == decision['human_input'] and
                {k: v for k, v in actual.items() if k != 'human_input'} ==
                {k: v for k, v in original.items() if k != 'human_input'},
                'native candidate/evidence mutation: ' + original['item_id'])


def apply(authority_file):
    before = sha256_file(ROOT / 'workspace/pro_a.db')
    items, template, reconciliation, packet = validate_frozen(authority_file)
    catalog = canonical_targets()
    decisions = build_decisions(items, template, reconciliation, packet, catalog)
    parent = read(frozen.ARTIFACT / 'a/review_population.json')
    completed = build_completed(parent, decisions)
    stage2 = read(ROOT / 'docs/phase43_stage2_final_human_qualification_receipt.json')
    wip = stage2['wip_after']['capacity']
    require(wip['pending_review_rows'] == 274 and wip['wip_state'] == 'HARD_STOP' and
            wip['new_intake_allowed'] is False, 'frozen Stage 2 WIP boundary drift')
    require(sha256_file(ROOT / 'workspace/pro_a.db') == before == frozen.PRODUCTION_SHA,
            'Production changed before persistence')
    public_decisions = {
        'document_type': 'phase43_stage3_completed_human_decisions',
        'authority_source_sha256': AUTH_SOURCE_SHA,
        'baseline': frozen.BASELINE, 'population_sha256': frozen.POPULATION_SHA,
        'parent_review_file_sha256': frozen.REVIEW_FILE_SHA,
        'blank_template_git_blob_sha256': TEMPLATE_SHA,
        'self_contained_packet_git_blob_sha256': PACKET_SHA,
        'reviewer': 'HUMAN_USER', 'decisions': decisions,
        'production_apply_authorized': False, 'official_view_activation_authorized': False,
    }
    decision_data = json_bytes(public_decisions)
    native_data = json_bytes(completed)
    write_once(STORE / 'native_qualification.completed.json', native_data)
    write_once(ROOT / 'docs/phase43_stage3_human_decisions_completed.json', decision_data)
    require(sha256_file(frozen.ARTIFACT / 'a/review_population.json') == frozen.REVIEW_FILE_SHA and
            sha256_file(frozen.ARTIFACT / 'a/resolution.json') == frozen.RESOLUTION_FILE_SHA and
            sha256_file(ROOT / 'workspace/pro_a.db') == before == frozen.PRODUCTION_SHA and
            sha256_file(ROOT / 'docs/phase43_stage2_human_authorization.json') == STAGE2_AUTH_SHA,
            'frozen input or Production changed after persistence')
    receipt = {
        'document_type': 'phase43_stage3_final_human_qualification_receipt',
        'result': 'PASS', 'binding_result': 'PASS',
        'baseline': frozen.BASELINE, 'pr': 65, 'pr_head_before_human_qualification': PRE_HUMAN_HEAD,
        'population_sha256': frozen.POPULATION_SHA,
        'ai_hardware_input_sha256': frozen.PRODUCTION_SHA,
        'semiconductor_input_sha256': frozen.PACKAGE_SHA,
        'stage2_immutable_packet_sha256': frozen.STAGE2_SHA,
        'stage2_human_authorization_sha256': STAGE2_AUTH_SHA,
        'authority_source_sha256': AUTH_SOURCE_SHA,
        'self_contained_packet_git_blob_sha256': PACKET_SHA,
        'blank_template_git_blob_sha256': TEMPLATE_SHA,
        'review_population_file_sha256': frozen.REVIEW_FILE_SHA,
        'automated_resolution_file_sha256': frozen.RESOLUTION_FILE_SHA,
        'ai_review_a_git_blob_sha256': REVIEW_A_SHA,
        'ai_review_b_git_blob_sha256': REVIEW_B_SHA,
        'ab_reconciliation_git_blob_sha256': RECONCILIATION_SHA,
        'completed_decision_file_sha256': digest(decision_data),
        'native_completed_file_sha256': digest(native_data),
        'human_decisions': {'expected': 100, 'applied': 100, 'missing': 0, 'extra': 0,
                            'section_a': 96, 'section_b': 4, 'residual_sample_size': 0},
        'identity_decisions': EXPECTED_IDENTITY,
        'relation_decisions': EXPECTED_RELATION,
        'explicit_adjudication': {item_id: {'decision': decision, 'target': target or None,
                                           'reason': reason}
                                  for item_id, (decision, target, reason) in OVERRIDES.items()},
        'qualification': {'mandatory_human': 'PASS', 'final_human': 'PASS',
                          'residual_sample_required': False},
        'production': {'sha_before': before, 'sha_after': sha256_file(ROOT / 'workspace/pro_a.db'),
                       'write_count': 0, 'apply_executed': False, 'source_writes': 0,
                       'relation_writes': 0},
        'views': {'official_view_activations': 0, 'current_view_writes': 0},
        'wip': {'source': 'frozen Stage 2 final human qualification receipt',
                'state': wip['wip_state'], 'pending_review_rows': wip['pending_review_rows'],
                'new_intake_allowed': wip['new_intake_allowed'],
                'operational_review_complete': False, 'workbench_mutated': False},
        'stage4_started': False,
    }
    write_once(ROOT / 'docs/phase43_stage3_final_human_qualification_receipt.json', json_bytes(receipt))
    report = [
        '# Phase 4.3 Stage 3 — Final HUMAN_USER Qualification', '',
        'FINAL_HUMAN_QUALIFICATION = PASS. HUMAN_USER explicitly authorized all 100 frozen decisions '
        '(Section A 96 adoptions; Section B 4 item-level adjudications). Missing 0, extra 0; '
        'no residual sample exists.', '',
        '| Identity decision | Count |', '|---|---:|',
        *[f'| {key} | {value} |' for key, value in EXPECTED_IDENTITY.items()], '',
        '| Relation decision | Count |', '|---|---:|',
        *[f'| {key} | {value} |' for key, value in EXPECTED_RELATION.items()], '',
        'The four explicit overrides are: `SC-CN-0033` CREATE_NEW_CANONICAL (physical Chiplet Product); '
        '`SC-CN-0051` REUSE_CANONICAL `NODE_20260817_7A9AE357` (SOI Wafer Material); '
        '`SC-CN-0031` CREATE_NEW_CANONICAL (generic Package Substrate Product); '
        '`SC-CN-0042` CREATE_NEW_CANONICAL (starting-wafer polishing Technology). '
        'All four are bound to the exact HUMAN_USER authorization and frozen candidate evidence.', '',
        'Section A uses the frozen system recommendation, including seven consensus identity proposals '
        'that differ from the earlier automated outcome. AI Review A/B and system advice remain supporting '
        'evidence; only the decisions in the completed artifact are attributed to HUMAN_USER. '
        'DEFER and REJECT count as completed qualification decisions.', '',
        'The original blank template SHA-256 is `' + TEMPLATE_SHA + '` and the self-contained packet '
        'Git blob SHA-256 is `' + PACKET_SHA + '`. The completed decisions SHA-256 is `'
        + digest(decision_data) + '`. The private native completed packet SHA-256 is `'
        + digest(native_data) + '`. Within its 100 native items, only the outer Stage 3 human_input '
        'fields differ from the frozen handoff; candidate content, Source/evidence, relations, temporal semantics, '
        'and Stage 2 inner human fields remain unchanged.', '',
        'Qualification grants no Production apply, canonical mutation, Source write, Relation write, '
        'Official View activation, or Current View write. Production SHA-256 before and after: `'
        + frozen.PRODUCTION_SHA + '`. Writes 0, apply false, Official View activations 0.', '',
        'The frozen Stage 2 authoritative WIP receipt reports 274 pending review rows and HARD_STOP; '
        'new intake remains disallowed. This Stage 3 task does not change Workbench state or claim '
        'operational review sealing.', '',
        'The complete 100 decisions and hashes are in '
        '[phase43_stage3_human_decisions_completed.json](phase43_stage3_human_decisions_completed.json) '
        'and [phase43_stage3_final_human_qualification_receipt.json]'
        '(phase43_stage3_final_human_qualification_receipt.json). '
        'PR #65 remains Draft; no merge or Stage 4 work is authorized. '
        'Next: pre-merge audit of PR #65 and Phase 4.3 Stage 3 release closure.',
    ]
    write_once(ROOT / 'docs/PHASE43_STAGE3_FINAL_HUMAN_QUALIFICATION.md',
               ('\n'.join(report).rstrip('\n') + '\n').encode('utf-8'))
    require(sha256_file(ROOT / 'workspace/pro_a.db') == before and
            sha256_file(frozen.ARTIFACT / 'a/review_population.json') == frozen.REVIEW_FILE_SHA and
            sha256_file(frozen.ARTIFACT / 'a/resolution.json') == frozen.RESOLUTION_FILE_SHA and
            sha256_file(ROOT / 'docs/phase43_stage2_human_authorization.json') == STAGE2_AUTH_SHA,
            'post-report protected input drift')
    for name, expected in {
        'docs/PHASE43_STAGE3_HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md': PACKET_SHA,
        'docs/phase43_stage3_human_decision_template.json': TEMPLATE_SHA,
        'docs/phase43_stage3_ai_review_a.json': REVIEW_A_SHA,
        'docs/phase43_stage3_ai_review_b.json': REVIEW_B_SHA,
        'docs/phase43_stage3_ai_review_reconciliation.json': RECONCILIATION_SHA,
    }.items():
        tracked_bytes(name, expected)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization-file', required=True, type=Path)
    args = parser.parse_args()
    receipt = apply(args.authorization_file)
    print(json.dumps({'result': receipt['result'], 'decisions': receipt['human_decisions'],
                      'production': receipt['production']['sha_after']}, ensure_ascii=False))
