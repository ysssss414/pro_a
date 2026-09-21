"""Read-only Stage 2 qualification reconciliation. No production/runtime imports."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import secrets
import sqlite3

RISKS = tuple(f'R{i:02}' for i in range(1, 15))
DIMENSIONS = ('evidence_directness', 'attribution_clarity', 'temporal_clarity',
              'unit_scope_completeness', 'relation_causal_explicitness',
              'entity_resolution_clarity', 'outcome_completeness',
              'conflict_accounting', 'rubric_applicability_clarity')
RISK_STATES = {'TRUE', 'FALSE', 'UNKNOWN', 'NOT_APPLICABLE'}
CONFIDENCE_STATES = {'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN', 'NOT_APPLICABLE'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical(value)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f'FROZEN_OUTPUT_CONFLICT: {path.name}')
        return
    with path.open('xb') as stream:
        stream.write(content)


def confidence(dimensions):
    values = set(dimensions.values())
    for state in ('LOW', 'UNKNOWN', 'MEDIUM'):
        if state in values:
            return state
    return 'HIGH'


def validate_review(review, manifest, packet, role):
    if review['reviewer_role'] != role:
        raise ValueError('REVIEWER_ROLE')
    if review['population_sha256'] != manifest['ordered_population_sha256']:
        raise ValueError('POPULATION_BINDING')
    if review['policy_bundle_sha256'] != manifest['policy_bundle_sha256']:
        raise ValueError('POLICY_BINDING')
    native = {r['candidate_id']: (kind, r) for kind, rows in packet['objects'].items() for r in rows}
    records = review['records']
    ids = [r['candidate_id'] for r in records]
    if len(ids) != len(set(ids)) or set(ids) != set(native):
        raise ValueError('EXACT_COVERAGE')
    for row in records:
        if 'output_record_sha256' in row:
            payload = {k: v for k, v in row.items() if k != 'output_record_sha256'}
            if digest(payload) != row['output_record_sha256']:
                raise ValueError('REVIEW_RECORD_HASH')
        kind, obj = native[row['candidate_id']]
        if row['candidate_type'] != kind or row['content_sha256'] != obj['content_sha256']:
            raise ValueError('CANDIDATE_BINDING')
        if row['native_decision'] not in obj['allowed_decisions']:
            raise ValueError('NATIVE_DECISION')
        operation = row['proposed_operation']
        if set(operation) != {'operation', 'target_id', 'from_ref', 'to_ref', 'relation_type', 'scope'}:
            raise ValueError('PROPOSED_OPERATION_FIELDS')
        if operation['operation'] != row['native_decision']:
            raise ValueError('PROPOSED_OPERATION_DECISION')
        if row['native_decision'] in {'REUSE', 'ATTACH'} and kind in {'nodes', 'aliases'} and not operation['target_id']:
            raise ValueError('CANONICAL_TARGET_REQUIRED')
        if row['review_decision'] not in {'ACCEPT', 'EDIT', 'REJECT', 'DEFER'}:
            raise ValueError('REVIEW_DECISION')
        if row['recommendation'] not in {'ACCEPT', 'ACCEPT_WITH_REVIEW_NOTE', 'REJECT', 'HUMAN_REQUIRED'}:
            raise ValueError('RECOMMENDATION')
        if set(row['risk_flags']) != set(RISKS) or not set(row['risk_flags'].values()) <= RISK_STATES:
            raise ValueError('RISK_COVERAGE')
        dims = row['confidence_dimensions']
        if set(dims) != set(DIMENSIONS) or not set(dims.values()) <= CONFIDENCE_STATES:
            raise ValueError('CONFIDENCE_COVERAGE')
        if row['overall_confidence'] != confidence(dims):
            raise ValueError('CONFIDENCE_AGGREGATION')
        if row['risk_flags']['R01'] != 'UNKNOWN' or row['overall_human_required'] is not True:
            raise ValueError('BLIND_R01')
        for key in RISKS:
            if not row['risk_reasons'].get(key, '').strip():
                raise ValueError('RISK_REASON')
        for key in DIMENSIONS:
            if not row['confidence_reasons'].get(key, '').strip():
                raise ValueError('CONFIDENCE_REASON')
        mandatory = any(row['risk_flags'][key] in {'TRUE', 'UNKNOWN'} for key in RISKS[1:])
        mandatory |= row['overall_confidence'] in {'LOW', 'UNKNOWN'}
        if mandatory and row['recommendation'] != 'HUMAN_REQUIRED':
            raise ValueError('RISK_ESCALATION')
        if row['overall_confidence'] in {'LOW', 'UNKNOWN'} and row['risk_flags']['R02'] not in {'TRUE', 'UNKNOWN'}:
            raise ValueError('R02_ESCALATION')
        ambiguity, materiality = row['relation_ambiguity'], row['materiality']
        if ambiguity not in RISK_STATES or materiality not in RISK_STATES:
            raise ValueError('RELATION_ASSESSMENT_ENUM')
        if ambiguity == 'UNKNOWN' or materiality == 'UNKNOWN':
            expected = 'UNKNOWN'
        elif ambiguity == 'NOT_APPLICABLE' or materiality == 'NOT_APPLICABLE':
            expected = 'NOT_APPLICABLE'
        else:
            expected = 'TRUE' if ambiguity == materiality == 'TRUE' else 'FALSE'
        if row['risk_flags']['R08'] != expected:
            raise ValueError('R08_SEMANTICS')
        if not row['concise_rationale'].strip() or not row['reason_codes']:
            raise ValueError('PER_ITEM_REASON')
        if row['evidence_sufficiency'] not in {'SUFFICIENT', 'INSUFFICIENT', 'UNKNOWN'}:
            raise ValueError('EVIDENCE_SUFFICIENCY')
        if row['evidence_sufficiency'] in {'INSUFFICIENT', 'UNKNOWN'} and row['risk_flags']['R03'] not in {'TRUE', 'UNKNOWN'}:
            raise ValueError('EVIDENCE_GAP_ESCALATION')
        if row.get('human_input') or row.get('human_approval'):
            raise ValueError('FABRICATED_HUMAN_DECISION')
    return {r['candidate_id']: r for r in records}


def substantive(row):
    # Only native semantic operation fields participate. Node/alias/baseline-view
    # objects have no native scope field; reviewers used it for narrative notes.
    operation = dict(row['proposed_operation'])
    if row['candidate_type'] in {'nodes', 'aliases', 'baseline_views'}:
        operation.pop('scope')
    recommendation = row['recommendation']
    if recommendation == 'ACCEPT_WITH_REVIEW_NOTE':
        recommendation = 'ACCEPT'
    risks = {key: state if state in {'TRUE', 'UNKNOWN'} else 'CLEAR'
             for key, state in row['risk_flags'].items() if key != 'R01'}
    result = {'review_decision': row['review_decision'], 'recommendation': recommendation,
              'native_decision': row['native_decision'], 'proposed_operation': operation,
              'evidence_sufficiency': row['evidence_sufficiency'], 'risk_flags': risks,
              'confidence_gate': row['overall_confidence'] if row['overall_confidence'] in {'LOW', 'UNKNOWN'} else 'SUFFICIENT'}
    # Necessary/positive R08 differences are always preserved. On non-relations,
    # auxiliary FALSE/N/A descriptions with a clear R08 do not change an outcome.
    if row['candidate_type'] == 'relations' or risks['R08'] != 'CLEAR':
        result['relation_ambiguity'] = row['relation_ambiguity']
        result['materiality'] = row['materiality']
    return result


def compare(a, b):
    if substantive(a) != substantive(b):
        return 'A_B_DISAGREEMENT'
    assessment = ('review_decision', 'recommendation', 'native_decision', 'proposed_operation',
                  'evidence_sufficiency', 'evidence_refs', 'reason_codes', 'concise_rationale',
                  'confidence_dimensions', 'confidence_reasons', 'overall_confidence',
                  'risk_flags', 'risk_reasons', 'relation_ambiguity', 'materiality')
    if all(a[k] == b[k] for k in assessment):
        return 'A_B_EXACT_AGREEMENT'
    return 'A_B_SUBSTANTIVE_AGREEMENT'


def reconcile(a, b, manifest):
    rows = []
    for item in manifest['items']:
        key = item['candidate_id']
        left, right = a[key], b[key]
        status = compare(left, right)
        triggers = set()
        if status == 'A_B_DISAGREEMENT':
            triggers.add('R01_A_B_DISAGREEMENT')
        for review in (left, right):
            for risk in RISKS[1:]:
                if review['risk_flags'][risk] in {'TRUE', 'UNKNOWN'}:
                    triggers.add(risk)
            if review['overall_confidence'] in {'LOW', 'UNKNOWN'}:
                triggers.add('R02')
            if review['recommendation'] == 'HUMAN_REQUIRED':
                triggers.add('REVIEWER_UNRESOLVED_HUMAN_REQUIRED')
        # Stage2 view governance remains mandatory, regardless of AI consensus.
        if 'VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE' in item['reason_flags']:
            triggers.add('VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE')
        rows.append({'candidate_id': key, 'candidate_type': item['candidate_type'],
                     'comparison': status, 'final_r01': 'TRUE' if status == 'A_B_DISAGREEMENT' else 'FALSE',
                     'mandatory_triggers': sorted(triggers), 'mandatory_human': bool(triggers),
                     'initial_reasons_preserved': item['reason_flags'],
                     'formal_mutation_authority': 'EXPLICIT_HUMAN_REQUIRED_NOT_GRANTED',
                     'human_input': {'decision': '', 'reason': '', 'target_id': ''}})
    return rows


def sample_size(n):
    if n == 0:
        return 0
    defects = math.ceil(n / 10)
    for size in range(n + 1):
        misses = math.comb(n - defects, size) if size <= n - defects else 0
        if 20 * misses <= math.comb(n, size):
            return min(n, max(20, size))
    raise AssertionError('unreachable')


def select_sample(eligible, seed):
    if len({r['candidate_id'] for r in eligible}) != len(eligible):
        raise ValueError('DUPLICATE_ELIGIBLE_ID')
    eligible = sorted(eligible, key=lambda r: r['candidate_id'])
    n = sample_size(len(eligible))
    # Fixed-seed SHA256 scores define the versioned no-replacement permutation.
    ranked = sorted(eligible, key=lambda r: (hashlib.sha256((seed + '\0' + r['candidate_id']).encode()).hexdigest(), r['candidate_id']))
    core = [r['candidate_id'] for r in ranked[:n]]
    chosen = set(core)
    supplements = []
    for axis in ('domain', 'polarity', 'challenge_level', 'candidate_type'):
        for category in sorted({r.get(axis, 'NOT_PROVIDED') for r in eligible}):
            members = [r for r in ranked if r.get(axis, 'NOT_PROVIDED') == category]
            if not any(r['candidate_id'] in chosen for r in members):
                key = members[0]['candidate_id']
                chosen.add(key)
                supplements.append({'candidate_id': key, 'axis': axis, 'category': category})
    return {'eligible_count': len(eligible), 'eligible_population_sha256': digest(eligible),
            'eligible_ids': [r['candidate_id'] for r in eligible], 'seed': seed,
            'algorithm': 'SHA256(seed UTF8 + NUL + candidate_id UTF8) ascending; candidate_id tie-break; v1',
            'seed_source': 'secrets.token_hex(32), generated once after eligible manifest freeze',
            'sampling_regime': 'B', 'error_prevalence_scenario': 0.1, 'detection_probability_target': 0.95,
            'minimum_random_core': 20, 'core_size': n, 'core_ids': core,
            'coverage_supplements': supplements, 'selected_ids': core + [r['candidate_id'] for r in supplements],
            'coverage_axis_order': ['domain', 'polarity', 'challenge_level', 'candidate_type'],
            'missing_strata_semantics': 'NOT_PROVIDED is missing metadata, not invented Gold challenge/polarity labels',
            'human_quality_gate': 'PENDING' if eligible else 'NOT_APPLICABLE_EMPTY_RESIDUAL',
            'human_error_tolerance': 0, 'human_results': []}


def verify_files(root, hashes):
    for relative, expected in hashes.items():
        if file_sha(Path(root) / relative) != expected:
            raise ValueError(f'INPUT_MUTATED: {relative}')


def validate_independence(a, b, dispatch, contract, root=None):
    if a['reviewer_identity'] == b['reviewer_identity']:
        raise ValueError('SAME_REVIEWER_IDENTITY')
    if {r['role'] for r in dispatch['reviewers']} != {'A', 'B'}:
        raise ValueError('DISPATCH_ROLES')
    if any(r['fork_turns'] != 'none' for r in dispatch['reviewers']):
        raise ValueError('INHERITED_CONTEXT')
    for review in (a, b):
        for key in ('prompt_sha256', 'scope_authorization_sha256'):
            if review[key] != contract[key]:
                raise ValueError('REVIEW_CONTRACT_BINDING')
        if not review['access_manifest'] or not review['runtime_provenance'] or not review['independence_attestation']:
            raise ValueError('MISSING_ACTUAL_PROVENANCE')
        attestation = review['independence_attestation']
        for key in ('peer_output_read', 'human_answers_read', 'candidate_mutation'):
            if attestation.get(key) is not False:
                raise ValueError('INDEPENDENCE_ATTESTATION')
        if attestation.get('fresh_context') is not True:
            raise ValueError('INDEPENDENCE_CONTEXT')
        role = review['reviewer_role']
        if review['reviewer_identity'] != next(r['task_name'] for r in dispatch['reviewers'] if r['role'] == role):
            raise ValueError('DISPATCH_IDENTITY')
        for access in review['access_manifest']:
            path = access['path'].replace('\\', '/')
            if '..' in path.split('/') or ':' in path or path.startswith('/'):
                raise ValueError('ACCESS_PATH_ESCAPE')
            if not (path.startswith('frozen/') or path.startswith(f'review_{role}/') or path in {
                    'review_prompt_v1.txt', 'review_contract.json', 'scope_authorization.json'}):
                raise ValueError('UNAUTHORIZED_REVIEW_ACCESS')
            if root is not None and file_sha(root / path) != access['sha256']:
                raise ValueError('ACCESS_HASH_MISMATCH')
    # Access manifests are additionally audited against frozen paths and actual
    # dispatch/transcript records. This is procedural, not OS-enforced isolation.


def validate_native_boundary(packet):
    if packet['production_apply_authorized'] is not False or packet['current_view_candidates']:
        raise ValueError('PRODUCTION_OR_VIEW_AUTHORITY')
    for rows in packet['objects'].values():
        for row in rows:
            if any(value != '' for value in row['human_input'].values()):
                raise ValueError('HUMAN_DECISION_PRESENT')
            if digest(row['content']) != row['content_sha256']:
                raise ValueError('NATIVE_CONTENT_MUTATED')


def read_wip(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        return conn.execute('SELECT SUM(is_pending) FROM stage1_review_projection').fetchone()[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root
    frozen = root / 'frozen'
    manifest = load(frozen / 'population_manifest.json')
    packet = load(frozen / 'foundation_packet.json')
    contract = load(root / 'review_contract.json')
    if file_sha(frozen / 'input_files.json') != contract['input_files_manifest_sha256']:
        raise ValueError('INPUT_MANIFEST_BINDING')
    if file_sha(frozen / 'population_manifest.json') != contract['review_population_manifest_sha256']:
        raise ValueError('POPULATION_MANIFEST_BINDING')
    if digest(manifest['items']) != manifest['ordered_population_sha256']:
        raise ValueError('ORDERED_POPULATION_DIGEST')
    input_hashes = load(frozen / 'input_files.json')
    actual_files = {p.relative_to(frozen).as_posix() for p in frozen.rglob('*') if p.is_file()}
    if actual_files != set(input_hashes) | {'input_files.json'}:
        raise ValueError('FROZEN_FILE_SET_MUTATED')
    verify_files(frozen, input_hashes)
    validate_native_boundary(packet)
    protected = load(root / 'protected_inputs_before.json')
    state_paths = [Path(path) for path in protected if Path(path).name == 'workbench.sqlite3']
    if len(state_paths) != 1 or read_wip(state_paths[0]) != 274:
        raise ValueError('WIP_BOUNDARY')
    for path, expected in load(root / 'protected_inputs_before.json').items():
        if file_sha(path) != expected:
            raise ValueError('PROTECTED_INPUT_MUTATED')
    reviews = [load(root / f'review_{role}' / 'review.json') for role in ('A', 'B')]
    for review in reviews:
        for row in review['records']:
            if 'output_record_sha256' not in row:
                raise ValueError('REVIEW_RECORD_HASH_REQUIRED')
            if row['input_manifest_sha256'] not in {
                    contract['review_population_manifest_sha256'], contract['input_files_manifest_sha256']}:
                raise ValueError('REVIEW_RECORD_INPUT_BINDING')
    for role in ('A', 'B'):
        directory = root / f'review_{role}'
        if file_sha(directory / 'review.json') != (directory / 'review.sha256').read_text().strip().split()[0]:
            raise ValueError('REVIEW_SEAL')
    validate_independence(*reviews, load(root / 'dispatch_receipt.json'), contract, root)
    a, b = [validate_review(review, manifest, packet, role) for review, role in zip(reviews, ('A', 'B'))]
    rows = reconcile(a, b, manifest)
    write_once(root / 'reconciliation.json', rows)
    mandatory_ids = {r['candidate_id'] for r in rows if r['mandatory_human']}
    eligible = [r for r in manifest['items'] if r['candidate_id'] not in mandatory_ids]
    write_once(root / 'eligible_population.json', eligible)
    seed_path = root / 'sampling_seed.json'
    if not seed_path.exists():
        write_once(seed_path, {'seed': secrets.token_hex(32) if eligible else None, 'eligible_population_sha256': digest(eligible)})
    seed = load(seed_path)
    if seed['eligible_population_sha256'] != digest(eligible):
        raise ValueError('SEED_POPULATION_DRIFT')
    sample = select_sample(eligible, seed['seed'])
    if mandatory_ids.intersection(sample['selected_ids']):
        raise ValueError('MANDATORY_IN_SAMPLE')
    write_once(root / 'residual_sample.json', sample)
    print(json.dumps({'reviewed': len(rows), 'mandatory': len(mandatory_ids),
                      'eligible': len(eligible), 'sample': len(sample['selected_ids'])}))


if __name__ == '__main__':
    main()
