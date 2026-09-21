"""Apply the exact Stage 2 HUMAN_USER authorization to a native review slice.

No ingestion, sampling, Workbench mutation, handoff or Production apply. The
274-object original stays blank. The separate 105-object qualification packet
retains native content, binds its parent, and passes the existing native validator.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import sqlite3
import subprocess

from pro_a.phase3f_foundation_baseline import build_review_packet, seal, validate_review
from pro_a.production_promotion import canonical_sha256, deterministic_id, sha256_file
from pro_a.workbench.stage1_scale import stage1_capacity, require_stage1_intake
from pro_a.workbench.config import BoundaryError

POPULATION = 'b363748e9aa05be4d66d7ff5c3d0008e9a80df29a25741f72d60c7c32c983b51'
SEED = 'b2c61c6d67fd29f4e1105905de7afc1fd2c63291573b189136f8d23b7d244642'
PRODUCTION = '6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1'
AUTHORIZATION = '3c69b1f9423f9072d42ae17748f40d4a558bccc201fa3f5b404dbbef3d08d41c'
BRANCH = 'codex/phase43-stage2-semiconductor-foundation-ingestion'
IMPLEMENTATION = 'e551e75b7c28d6ba3ed5d39cf6cf5b37db0b565f'
BASELINE = '8e07cc2b7270ac08cb4166b5f62b4dc76f396f35'
BOUND_FILES = {
    'human_qualification_packet.private.json': 'ac721ae49241cade45224a4fad9020ea7d70407df00be1809a8663f2fa756bb3',
    'reconciliation.json': '3631ead5334528a174a97683105fe5a1125b6e90fe9748f92c787be9c6b58b9b',
    'residual_sample.json': '44051e472043f12bb416e7947d4f67a0f16d8785a4154d963e96726bbaed09a3',
    'review_A/review.json': '9e5735f73a039c58b598ba48d1d78d5bf434c22a8ce6c15e464f22c8aa5f9edf',
    'review_B/review.json': 'f32d03eaf14494486a7d0dc89e2f20ccbe9ad950a69b1d80d0b16fb37ebdb08f',
    'portability_v2/HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md': 'fd82076c74a200a2ff96f3914eb00bb5d208f8c875a63b9739f88127856956a1',
    'portability_v2/phase43_stage2_human_decision_template.json': '1c29d024f2b90fd48311c93c0ac9122eaf7b52e8ff2d92e0470d219a01b3c086',
}
EXPECTED_COUNTS = {'CREATE': 48, 'DEFER': 37, 'KEEP_AS_BASELINE_CANDIDATE': 8,
                   'KEEP_NEEDS_REVIEW': 3, 'KEEP': 2, 'REJECT': 2,
                   'ALIAS_ACCEPT_OWNER': 3, 'NODE_REUSE': 2}
CONFLICTS = {'SC-AL-0009': 'DEFER', 'SC-CL-0019': 'KEEP_NEEDS_REVIEW',
             'SC-CN-0015': 'DEFER', 'SC-CN-0028': 'REJECT', 'SC-CN-0050': 'DEFER',
             'SC-CN-0093': 'DEFER', 'SC-CN-0122': 'REJECT'}


def require(condition, message):
    if not condition:
        raise ValueError('HUMAN_AUTHORIZATION_BINDING_FAIL: ' + message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def immutable_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == data, 'immutable output drift: ' + path.name)
    else:
        with path.open('xb') as stream:
            stream.write(data)


def write_json(path, value):
    immutable_write(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())


def decision_counts(decisions):
    return dict(Counter('ALIAS_ACCEPT_OWNER' if d['system_recommended_decision'].startswith('ACCEPT_OWNER ')
                        else 'NODE_REUSE' if d['system_recommended_decision'].startswith('REUSE ')
                        else d['system_recommended_decision'] for d in decisions))


def native_input(recommendation):
    operation, _, target = recommendation.partition(' ')
    operation = {'KEEP_AS_BASELINE_CANDIDATE': 'ACCEPT', 'ACCEPT_OWNER': 'ATTACH'}.get(operation, operation)
    require(bool(target) == (operation in {'ATTACH', 'REUSE'}), 'native target shape')
    return {'decision': operation, 'target_id': target,
            'reason': 'HUMAN_USER explicitly adopted frozen SYSTEM_RECOMMENDED_DECISION: '
                      + recommendation + '. Qualification only; no Production apply or Current View activation.'}


def validate_decisions(decisions, template):
    require(len(decisions) == len(template) == 105, '105 decisions required')
    require(len({d['item_id'] for d in decisions}) == 105, 'duplicate decision')
    for actual, frozen in zip(decisions, template, strict=True):
        require(all(actual[k] == frozen[k] for k in ('item_id', 'section', 'object_type', 'system_recommended_decision')),
                'decision identity or recommendation drift')
        require(actual['reviewer'] == 'HUMAN_USER', 'reviewer')
        require(actual['human_user_decision'] == frozen['system_recommended_decision'], 'human override')
        require(actual['human_input'] == native_input(frozen['system_recommended_decision']), 'native decision drift')
    require(decision_counts(decisions) == EXPECTED_COUNTS, 'aggregate counts')
    require(Counter(d['section'] for d in decisions) == {'A': 31, 'B': 45, 'C': 29}, 'section counts')
    by_id = {d['item_id']: d for d in decisions}
    require(all(by_id[cid]['human_user_decision'] == value for cid, value in CONFLICTS.items()), 'seven conflicts')


def build_qualification(parent, decisions, parent_file_sha):
    """Lossless selection of existing records, never requalify or create candidates."""
    validate_review(parent, expected_sha256=parent['immutable_packet_sha256'], completed=False)
    by_id = {d['item_id']: d for d in decisions}
    require(len(by_id) == len(decisions) == 105, 'scope identity count')
    objects = {kind: [copy.deepcopy(r) for r in rows if r['candidate_id'] in by_id]
               for kind, rows in parent['objects'].items()}
    require(sum(map(len, objects.values())) == 105, 'scope outside original packet')
    scope = {'parent_packet_id': parent['packet_id'], 'parent_packet_sha256': parent_file_sha,
             'parent_immutable_packet_sha256': parent['immutable_packet_sha256'],
             'population_sha256': POPULATION, 'authorization_sha256': AUTHORIZATION,
             'ordered_authorized_ids': [d['item_id'] for d in decisions],
             'full_operational_review_complete': False, 'unselected_candidates_reviewed': False,
             'official_view_activation_authorized': False, 'current_view_write_authorized': False}
    blank = build_review_packet(package=parent['package'], registry=parent['registry'],
        production=parent['production_baseline'], repository_commit=parent['repository_commit'],
        objects=objects, timestamp=parent['frozen_timestamp'])
    require(blank['objects'] == objects, 'lossless native record selection')
    blank.pop('immutable_packet_sha256')
    blank['qualification_scope'] = scope
    blank['packet_id'] = deterministic_id('FOUNDATION_QUALIFICATION', scope)
    blank = seal(blank, 'immutable_packet_sha256')
    validate_review(blank, expected_sha256=blank['immutable_packet_sha256'], completed=False)
    completed = copy.deepcopy(blank)
    completed['human_completion'] = {'reviewer': 'HUMAN_USER',
        'reason': 'Exact 105-item frozen Stage 2 qualification authorization; remaining 169 objects unreviewed by HUMAN_USER.'}
    for kind, rows in completed['objects'].items():
        for row in rows:
            supplied = by_id[row['candidate_id']]
            require(supplied['object_type'] == kind and supplied['native_content_sha256'] == row['content_sha256'], 'native content binding')
            row['human_input'] = copy.deepcopy(supplied['human_input'])
    validate_review(completed, expected_sha256=blank['immutable_packet_sha256'], completed=True)
    return blank, completed


def capacity(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        result = stage1_capacity(connection)
        try:
            require_stage1_intake(connection)
            guard = 'ALLOWED'
        except BoundaryError as error:
            guard = str(error)
    return {'capacity': result, 'new_intake_guard': guard, 'connection_mode': 'ro'}


def apply(root, production, state_db, authorization_file, output, repository):
    # All authority and immutable inputs are checked before creating any decisions.
    require(sha256_file(authorization_file) == AUTHORIZATION, 'HUMAN_USER authorization source')
    for name, expected in BOUND_FILES.items():
        require(sha256_file(root / name) == expected, name)
    require(sha256_file(production) == PRODUCTION, 'Production SHA')
    git = lambda *args: subprocess.check_output(['git', '-C', str(repository), *args], text=True).strip()
    require(git('rev-parse', '--abbrev-ref', 'HEAD') == BRANCH, 'branch')
    head = git('rev-parse', 'HEAD')
    for ancestor in (BASELINE, IMPLEMENTATION):
        git('merge-base', '--is-ancestor', ancestor, head)
    manifest = read(root / 'frozen/population_manifest.json')
    require(canonical_sha256(manifest['items']) == manifest['ordered_population_sha256'] == POPULATION, 'population')
    require(len(manifest['items']) == manifest['total_items'] == 274, 'population count')
    native_path = root / 'frozen/foundation_packet.json'
    require(sha256_file(native_path) == manifest['native_packet_sha256'], 'native packet file')
    parent = read(native_path)
    validate_review(parent, expected_sha256=manifest['native_immutable_packet_sha256'], completed=False)
    native = {r['candidate_id']: (kind, r) for kind, rows in parent['objects'].items() for r in rows}
    require(len(native) == 274 and all(native[x['candidate_id']][0] == x['candidate_type'] and
        native[x['candidate_id']][1]['content_sha256'] == x['content_sha256'] for x in manifest['items']), '274 native identities')
    sample = read(root / 'residual_sample.json')
    require(sample['seed'] == SEED and len(sample['selected_ids']) == 29, 'sample membership')
    packet = read(root / 'human_qualification_packet.private.json')
    template = read(root / 'portability_v2/phase43_stage2_human_decision_template.json')
    markdown = (root / 'portability_v2/HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md').read_text('utf-8')
    require(re.findall(r'^- \*\*ITEM_ID\*\* = (.+)$', markdown, re.M) == [d['item_id'] for d in template], 'Markdown IDs')
    require(re.findall(r'^- \*\*SYSTEM_RECOMMENDED_DECISION\*\* = (.+)$', markdown, re.M) ==
            [d['system_recommended_decision'] for d in template], 'Markdown recommendations')
    require([d['item_id'] for d in template] == [i['candidate_id'] for i in packet['items']], 'frozen packet IDs')
    require({d['item_id'] for d in template if d['section'] == 'C'} == set(sample['selected_ids']), 'residual IDs')
    reconciliation = read(root / 'reconciliation.json')
    require({d['item_id'] for d in template if d['section'] != 'C'} ==
            {r['candidate_id'] for r in reconciliation if r['mandatory_human']}, 'mandatory IDs')
    protected = {str(p): sha256_file(p) for p in root.rglob('*') if p.is_file() and not p.is_relative_to(output)}
    protected.update({str(p): sha256_file(p) for p in (production, state_db, authorization_file)})
    before_capacity = capacity(state_db)
    decisions = [{**d, 'reviewer': 'HUMAN_USER', 'human_user_decision': d['system_recommended_decision'],
        'human_user_note': 'Explicit user adoption without item-level overrides.',
        'native_content_sha256': native[d['item_id']][1]['content_sha256'],
        'human_input': native_input(d['system_recommended_decision'])} for d in template]
    validate_decisions(decisions, template)
    blank, completed = build_qualification(parent, decisions, manifest['native_packet_sha256'])
    after_capacity = capacity(state_db)
    require(before_capacity == after_capacity, 'capacity changed during qualification')
    require(all(sha256_file(Path(p)) == h for p, h in protected.items()), 'frozen evidence or database changed')
    authorization = {'document_type': 'phase43_stage2_exact_human_qualification_authorization',
        'reviewer': 'HUMAN_USER', 'authority_source_sha256': AUTHORIZATION,
        'population_sha256': POPULATION, 'frozen_file_bindings': BOUND_FILES,
        'sample_seed': SEED, 'production_apply_authorized': False, 'production_write_allowed': False,
        'official_view_activation_authorized': False, 'current_view_write_authorized': False,
        'residual_substantive_errors': 0, 'residual_error_report_authority': 'HUMAN_USER',
        'expanded_review_required': False, 'decisions': decisions}
    write_json(output / 'native_qualification.blank.json', blank)
    write_json(output / 'native_qualification.completed.json', completed)
    write_json(output / 'phase43_stage2_human_authorization.json', authorization)
    write_json(output / 'protected_inputs.json', protected)
    result = {'document_type': 'phase43_stage2_native_human_qualification_validation',
        'result': 'PASS', 'binding_result': 'PASS', 'population_sha256': POPULATION,
        'sample_seed': SEED, 'bindings': BOUND_FILES, 'authority_source_sha256': AUTHORIZATION,
        'human_decisions': {'expected': 105, 'applied': 105, 'missing': 0, 'extra': 0,
                            'unselected_without_human_attribution': 169},
        'decision_counts': decision_counts(decisions), 'node_create': 41, 'relation_create': 7,
        'sections': dict(Counter(d['section'] for d in decisions)),
        'qualification': {'mandatory_human': 'PASS', 'residual_sample': 'PASS', 'final_human': 'PASS'},
        'residual_sample': {'size': 29, 'substantive_errors': 0, 'report_authority': 'HUMAN_USER',
                            'result': 'PASS', 'expanded_review_required': False},
        'native_qualification': {'parent_immutable_packet_sha256': parent['immutable_packet_sha256'],
            'immutable_packet_sha256': blank['immutable_packet_sha256'],
            'completed_file_sha256': sha256_file(output / 'native_qualification.completed.json'),
            'blank_file_sha256': sha256_file(output / 'native_qualification.blank.json'),
            'validator': 'pro_a.phase3f_foundation_baseline.validate_review',
            'full_operational_review_complete': False, 'original_274_packet_preserved': True},
        'authorization_file_sha256': sha256_file(output / 'phase43_stage2_human_authorization.json'),
        'frozen_supporting_files_checked': len(protected), 'frozen_supporting_files_unchanged': True,
        'protected_manifest_sha256': sha256_file(output / 'protected_inputs.json'),
        'views': {'baseline_candidates_kept': 8, 'official_view_activations': 0, 'current_view_writes': 0},
        'production': {'sha_before': PRODUCTION, 'sha_after': sha256_file(production), 'write_count': 0,
                       'apply_executed': False, 'apply_authorized': False},
        'wip_before': before_capacity, 'wip_after': after_capacity,
        'wip_note': 'Foundation Workbench projection is read-only; native qualification does not seal operational Source review or remove audit rows.',
        'git_binding': {'branch': BRANCH, 'implementation': IMPLEMENTATION, 'head': head, 'stage1_baseline': BASELINE,
                        'pr': 'https://github.com/ysssss414/pro_a/pull/64'},
        'stage3_started': False}
    write_json(output / 'qualification_validation.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('review-root', 'production', 'state-db', 'authorization-file', 'output', 'repository'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(apply(args.review_root, args.production, args.state_db,
                          args.authorization_file, args.output, args.repository), ensure_ascii=False, indent=2))
