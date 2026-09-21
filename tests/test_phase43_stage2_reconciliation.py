"""Targeted qualification gates; synthetic fixtures are never reviewer evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reconcile_phase43_stage2.py'
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name('reconcile_phase43_stage2.py')
spec = importlib.util.spec_from_file_location('stage2_reconcile', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def record(key='one', kind='nodes'):
    return {'candidate_id': key, 'candidate_type': kind, 'content_sha256': m.digest({}),
            'review_decision': 'ACCEPT', 'recommendation': 'ACCEPT', 'native_decision': 'CREATE',
            'proposed_operation': {'operation': 'CREATE', 'target_id': None, 'from_ref': None,
                                   'to_ref': None, 'relation_type': None, 'scope': None},
            'evidence_sufficiency': 'SUFFICIENT', 'evidence_refs': ['evidence-one'],
            'reason_codes': ['SUPPORTED'], 'concise_rationale': 'Synthetic evidence supports a leaf concept.',
            'confidence_dimensions': dict.fromkeys(m.DIMENSIONS, 'HIGH'),
            'confidence_reasons': dict.fromkeys(m.DIMENSIONS, 'Synthetic applicable evidence verified.'),
            'overall_confidence': 'HIGH', 'risk_flags': dict.fromkeys(m.RISKS, 'FALSE') | {'R01': 'UNKNOWN'},
            'risk_reasons': dict.fromkeys(m.RISKS, 'Synthetic scoped assessment.'),
            'relation_ambiguity': 'FALSE', 'materiality': 'FALSE', 'overall_human_required': True}


def review(role='A'):
    return {'reviewer_role': role, 'reviewer_identity': f'/root/review_{role.lower()}',
            'population_sha256': 'population', 'policy_bundle_sha256': 'policy',
            'prompt_sha256': 'prompt', 'scope_authorization_sha256': 'scope',
            'runtime_provenance': {'context': 'synthetic'},
            'access_manifest': [{'path': 'frozen/input.json', 'sha256': 'hash'}],
            'independence_attestation': {'peer_output_read': False, 'human_answers_read': False,
                                       'candidate_mutation': False, 'fresh_context': True},
            'records': [record()]}


def population():
    return {'ordered_population_sha256': 'population', 'policy_bundle_sha256': 'policy',
            'items': [{'candidate_id': 'one', 'candidate_type': 'nodes', 'reason_flags': ['NEW_CANONICAL_NODE']}]}


def packet():
    return {'production_apply_authorized': False, 'current_view_candidates': [],
            'objects': {'nodes': [{'candidate_id': 'one', 'content': {}, 'content_sha256': m.digest({}),
                                  'human_input': {'decision': '', 'reason': '', 'target_id': ''},
                                  'allowed_decisions': ['CREATE', 'REUSE', 'DEFER', 'REJECT']}]}}


@pytest.mark.parametrize('role', ['A', 'B'])
def test_exact_population_coverage(role):
    result = review(role)
    assert set(m.validate_review(result, population(), packet(), role)) == {'one'}
    result['records'].append(record())
    with pytest.raises(ValueError, match='EXACT_COVERAGE'):
        m.validate_review(result, population(), packet(), role)
    result['records'] = []
    with pytest.raises(ValueError, match='EXACT_COVERAGE'):
        m.validate_review(result, population(), packet(), role)


def test_independence_rejects_peer_access_and_inherited_context():
    a, b = review('A'), review('B')
    dispatch = {'reviewers': [{'role': role, 'task_name': f'/root/review_{role.lower()}', 'fork_turns': 'none'} for role in ['A', 'B']]}
    contract = {'prompt_sha256': 'prompt', 'scope_authorization_sha256': 'scope'}
    m.validate_independence(a, b, dispatch, contract)
    b['access_manifest'][0]['path'] = 'review_A/review.json'
    with pytest.raises(ValueError, match='UNAUTHORIZED_REVIEW_ACCESS'):
        m.validate_independence(a, b, dispatch, contract)
    b = review('B')
    dispatch['reviewers'][1]['fork_turns'] = 'all'
    with pytest.raises(ValueError, match='INHERITED_CONTEXT'):
        m.validate_independence(a, b, dispatch, contract)


def test_candidate_mutation_fails(tmp_path):
    path = tmp_path / 'candidate.json'
    path.write_text('{}')
    expected = {'candidate.json': m.file_sha(path)}
    m.verify_files(tmp_path, expected)
    path.write_text('{"changed":true}')
    with pytest.raises(ValueError, match='INPUT_MUTATED'):
        m.verify_files(tmp_path, expected)
    native = packet()
    native['objects']['nodes'][0]['content']['classification'] = 'REUSE'
    with pytest.raises(ValueError, match='NATIVE_CONTENT_MUTATED'):
        m.validate_native_boundary(native)


def test_comparison_deterministic_and_wording_is_not_disagreement():
    a, b = record(), record()
    assert m.compare(a, b) == 'A_B_EXACT_AGREEMENT'
    b['concise_rationale'] = 'Different concise wording of identical assessment.'
    assert m.compare(a, b) == 'A_B_SUBSTANTIVE_AGREEMENT'
    assert m.compare(a, b) == m.compare(b, a)


@pytest.mark.parametrize('field,value', [('native_decision', 'REUSE'), ('recommendation', 'HUMAN_REQUIRED'),
                                        ('evidence_sufficiency', 'INSUFFICIENT'), ('review_decision', 'REJECT')])
def test_substantive_disagreements(field, value):
    a, b = record(), record()
    b[field] = value
    assert m.compare(a, b) == 'A_B_DISAGREEMENT'


@pytest.mark.parametrize('field', ['target_id', 'from_ref', 'to_ref', 'relation_type'])
def test_target_and_relation_changes_are_disagreements(field):
    a, b = record(), record()
    b['proposed_operation'][field] = 'different'
    assert m.compare(a, b) == 'A_B_DISAGREEMENT'


def test_overlapping_exceptions_deduplicate_and_disagreement_remains():
    a, b = record(), record()
    a['risk_flags']['R05'] = b['risk_flags']['R05'] = 'TRUE'
    b['risk_flags']['R13'] = 'UNKNOWN'
    rows = m.reconcile({'one': a}, {'one': b}, population())
    assert len(rows) == 1 and rows[0]['mandatory_human']
    assert set(rows[0]['mandatory_triggers']) >= {'R05', 'R13', 'R01_A_B_DISAGREEMENT'}


@pytest.mark.parametrize('risk', m.RISKS[1:])
def test_all_mandatory_flags_survive_consensus(risk):
    a = record()
    a['risk_flags'][risk] = 'TRUE'
    row = m.reconcile({'one': a}, {'one': copy.deepcopy(a)}, population())[0]
    assert row['mandatory_human'] and risk in row['mandatory_triggers']


def test_unknown_and_low_confidence_cannot_be_accepted():
    r = review()
    r['records'][0]['confidence_dimensions']['evidence_directness'] = 'UNKNOWN'
    r['records'][0]['overall_confidence'] = 'UNKNOWN'
    with pytest.raises(ValueError, match='RISK_ESCALATION'):
        m.validate_review(r, population(), packet(), 'A')


def test_sampling_formula_reproducibility_and_coverage():
    assert m.sample_size(0) == 0
    assert m.sample_size(9) == 9
    assert m.sample_size(30) == 20
    assert m.sample_size(90) == 25
    eligible = [{'candidate_id': str(i), 'candidate_type': 'nodes' if i < 89 else 'claims',
                 'domain': 'semiconductor'} for i in range(90)]
    a = m.select_sample(eligible, 'fixed-test-seed')
    b = m.select_sample(list(reversed(eligible)), 'fixed-test-seed')
    assert a == b
    assert len(a['core_ids']) == 25
    assert len(a['selected_ids']) == len(set(a['selected_ids']))
    assert '89' in a['selected_ids']


def test_mandatory_excluded_from_residual():
    manifest = population()
    manifest['items'].append({'candidate_id': 'two', 'candidate_type': 'claims', 'reason_flags': []})
    a = {'one': record(), 'two': record('two', 'claims')}
    a['one']['risk_flags']['R05'] = 'TRUE'
    rows = m.reconcile(a, copy.deepcopy(a), manifest)
    mandatory = {r['candidate_id'] for r in rows if r['mandatory_human']}
    sample = m.select_sample([r for r in manifest['items'] if r['candidate_id'] not in mandatory], 'seed')
    assert sample['selected_ids'] == ['two']


def test_human_fields_blank_and_not_synthesized():
    native = packet()
    m.validate_native_boundary(native)
    native['objects']['nodes'][0]['human_input']['decision'] = 'CREATE'
    with pytest.raises(ValueError, match='HUMAN_DECISION_PRESENT'):
        m.validate_native_boundary(native)
    row = m.reconcile({'one': record()}, {'one': record()}, population())[0]
    assert not any(row['human_input'].values())


def test_production_hash_change_detected(tmp_path):
    path = tmp_path / 'production.db'
    path.write_bytes(b'original')
    before = {'production.db': m.file_sha(path)}
    path.write_bytes(b'mutated')
    with pytest.raises(ValueError, match='INPUT_MUTATED'):
        m.verify_files(tmp_path, before)


def test_official_view_activation_forbidden_and_governance_preserved():
    native = packet()
    native['production_apply_authorized'] = True
    with pytest.raises(ValueError, match='PRODUCTION_OR_VIEW_AUTHORITY'):
        m.validate_native_boundary(native)
    manifest = population()
    manifest['items'][0]['reason_flags'] = ['VIEW_ACTIVATION_REQUIRES_SEPARATE_GOVERNANCE']
    row = m.reconcile({'one': record()}, {'one': record()}, manifest)[0]
    assert row['mandatory_human']


def test_wip_read_is_readonly_and_count_unchanged(tmp_path):
    path = tmp_path / 'state.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE stage1_review_projection (is_pending INTEGER)')
        conn.executemany('INSERT INTO stage1_review_projection VALUES (?)', [(1,)] * 274)
    before = m.file_sha(path)
    assert m.read_wip(path) == 274
    assert m.file_sha(path) == before


def test_nonoperative_notes_and_clear_applicability_are_substantive_agreement():
    a, b = record(), record()
    b['recommendation'] = 'ACCEPT_WITH_REVIEW_NOTE'
    b['risk_flags']['R12'] = 'NOT_APPLICABLE'
    b['proposed_operation']['scope'] = 'Node identity recommendation; no native scope field'
    b['relation_ambiguity'] = b['materiality'] = 'NOT_APPLICABLE'
    assert m.compare(a, b) == 'A_B_SUBSTANTIVE_AGREEMENT'


def test_native_relation_scope_difference_remains_disagreement():
    a, b = record(kind='relations'), record(kind='relations')
    a['proposed_operation']['scope'] = 'source-scoped taxonomy'
    b['proposed_operation']['scope'] = 'global causal assertion'
    assert m.compare(a, b) == 'A_B_DISAGREEMENT'


def test_unknown_cannot_be_normalized_to_clear():
    a, b = record(), record()
    b['risk_flags']['R05'] = 'UNKNOWN'
    assert m.compare(a, b) == 'A_B_DISAGREEMENT'
