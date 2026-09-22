"""Focused safeguards for the Stage 3 advisory double-review handoff."""
import json

import pytest

from scripts import build_phase43_stage3_double_review as review


def interpretation(**changes):
    values = {'identity_boundary': 'same', 'object_type': 'compatible',
              'scope': 'compatible', 'granularity': 'same', 'quarantine': 'clear',
              'ontology': 'compatible', 'evidence_sufficiency': 'sufficient',
              'temporal': 'compatible'}
    return {**values, **changes}


def row(item_id='SC-CN-0001', decision='REUSE_CANONICAL', target='NODE_1', **changes):
    values = {'item_id': item_id, 'kind': 'identity', 'recommendation': 'Verified identity',
              'native_decision': decision, 'target': target, 'confidence': 'HIGH',
              'reason': 'Exact canonical name and type agree.',
              'evidence_assessment': 'SC-EV-1 supports the named concept.',
              'risk_flags': ['MANDATORY_HUMAN'], 'materiality': 'MEDIUM',
              'source_identity': {'source_ids': ['SC-PHYS-1'], 'source_sha256': ['sha-1']},
              'evidence_ids': ['SC-EV-1'],
              'temporal_scope': 'source-scoped', 'reviewer_interpretation': interpretation()}
    return {**values, **changes}


def item(item_id='SC-CN-0001', outcome='REUSE_CANONICAL', reasons=None):
    return {'item_id': item_id, 'kind': 'identity', 'resolution': {
        'outcome': outcome, 'reasons': reasons or [], 'target_node_id': 'NODE_1'},
        'evidence': [{'evidence_id': 'SC-EV-1', 'source_id': 'SC-PHYS-1', 'source_sha256': 'sha-1'}]}


def access(role='A', peer=False):
    base = 'workspace/phase4_stage43_stage3_cross_domain_resolution/qualified_v3/' + role.lower()
    return {'reviewer': role, 'fork_turns': 'none',
            'frozen_review_file_sha256': review.REVIEW_FILE_SHA,
            'population_sha256': review.POPULATION_SHA, 'peer_output_accessed': peer,
            'same_model_provider_os_independence_claimed': False,
            'review_output_sha256': 'abc', 'input_files': [
                {'path': base + '/review_population.json', 'sha256': review.REVIEW_FILE_SHA},
                {'path': base + '/resolution.json', 'sha256': review.RESOLUTION_FILE_SHA},
                {'path': 'docs/PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION_CONTRACT.md',
                 'sha256': review.file_sha(review.ROOT / 'docs/PHASE43_STAGE3_CROSS_DOMAIN_RESOLUTION_CONTRACT.md')},
            ]}


def test_fresh_review_context_rejects_peer_access():
    review.validate_access('A', access(), 'abc')
    with pytest.raises(ValueError, match='access/isolation'):
        review.validate_access('A', access(peer=True), 'abc')
    with pytest.raises(ValueError, match='access/isolation'):
        review.validate_access('B', access(), 'abc')


def test_review_exact_100_coverage_and_no_extra_or_duplicates():
    items = [item(f'SC-CN-{n:04d}') for n in range(100)]
    rows = [row(f'SC-CN-{n:04d}') for n in range(100)]
    document = {'reviewer': 'A', 'population_sha256': review.POPULATION_SHA, 'items': rows}
    assert len(review.validate_review('A', document, items)) == 100
    for changed in (rows[:-1], rows + [row('SC-CN-0100')], rows[:-1] + [rows[0]]):
        with pytest.raises(ValueError, match='coverage/duplicates'):
            review.validate_review('A', {**document, 'items': changed}, items)


def test_review_rejects_mismatched_evidence_and_local_paths():
    items = [item(f'SC-CN-{n:04d}') for n in range(100)]
    rows = [row(f'SC-CN-{n:04d}') for n in range(100)]
    document = {'reviewer': 'A', 'population_sha256': review.POPULATION_SHA, 'items': rows}
    rows[0] = {**rows[0], 'evidence_ids': ['SC-EV-WRONG']}
    with pytest.raises(ValueError, match='evidence IDs drift'):
        review.validate_review('A', document, items)
    rows[0] = {**rows[0], 'evidence_ids': ['SC-EV-1'], 'reason': r'D:\private\file'}
    with pytest.raises(ValueError, match='local path leakage'):
        review.validate_review('A', document, items)


def test_substantive_disagreement_and_native_operation_conflict():
    a = row()
    b = row(decision='DEFER', target=None)
    comparison = review.compare_reviews(a, b)
    assert comparison['status'] == 'A_B_SUBSTANTIVE_DISAGREEMENT'
    assert comparison['native_operation_conflict']
    assert review.system_decision(item(), a, b, comparison)[0] == 'DEFER'


def test_canonical_target_conflict_even_with_same_native_operation():
    comparison = review.compare_reviews(row(), row(target='NODE_2'))
    assert comparison['target_conflict']
    assert not comparison['native_operation_conflict']


def test_material_evidence_type_scope_and_temporal_conflicts():
    a = row()
    b = row(reviewer_interpretation=interpretation(
        evidence_sufficiency='limited', object_type='mismatch', temporal='mismatch'))
    comparison = review.compare_reviews(a, b)
    assert comparison['evidence_conflict']
    assert comparison['type_scope_conflict']
    assert comparison['temporal_conflict']


def test_wording_and_non_material_confidence_differences_are_ignored():
    a = row()
    b = row(reason='Different wording.', confidence='MEDIUM')
    assert review.compare_reviews(a, b)['status'] == 'A_B_SUBSTANTIVE_AGREEMENT'


def test_pinned_semantic_reconciliation_retains_nonmaterial_label_differences():
    a = row(item_id='SC-CN-0043', decision='CREATE_NEW_CANONICAL', target=None,
            reviewer_interpretation=interpretation(scope='mismatch'))
    b = row(item_id='SC-CN-0043', decision='CREATE_NEW_CANONICAL', target=None,
            reviewer_interpretation=interpretation(scope='compatible'))
    result = review.semantic_reconciliation(item('SC-CN-0043'), a, b, review.compare_reviews(a, b))
    assert result['status'] == 'A_B_SUBSTANTIVE_AGREEMENT'
    assert result['nonmaterial_interpretation_differences'] == ['scope']


def test_pinned_material_operation_conflict_stays_in_section_b():
    a = row(item_id='SC-CN-0033', decision='CREATE_NEW_CANONICAL', target=None)
    b = row(item_id='SC-CN-0033', decision='DEFER', target=None)
    result = review.semantic_reconciliation(item('SC-CN-0033'), a, b, review.compare_reviews(a, b))
    assert result['status'] == 'A_B_SUBSTANTIVE_DISAGREEMENT'
    assert result['native_operation_conflict']


def test_system_advice_is_deterministic_and_preserves_frozen_exceptions():
    a = row()
    b = row()
    comparison = review.compare_reviews(a, b)
    assert review.system_decision(item(), a, b, comparison) == review.system_decision(item(), a, b, comparison)
    for reason in ('HISTORICAL_QUARANTINE', 'ONTOLOGY_PRESSURE', 'TEMPORAL_MISMATCH',
                   'TYPE_MISMATCH', 'FROZEN_STAGE2_HUMAN_DECISION'):
        assert review.system_decision(item(reasons=[reason]), a, b, comparison)[0] == 'DEFER'


def test_public_packet_and_blank_human_decisions_when_generated():
    docs = review.ROOT / 'docs'
    packet_path = docs / 'PHASE43_STAGE3_HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md'
    if not packet_path.exists():
        pytest.skip('double-review output has not yet been generated')
    packet = packet_path.read_text(encoding='utf-8')
    template = json.loads((docs / 'phase43_stage3_human_decision_template.json').read_text(encoding='utf-8'))
    reconciled = json.loads((docs / 'phase43_stage3_ai_review_reconciliation.json').read_text(encoding='utf-8'))
    assert len(template['items']) == len(reconciled['items']) == 100
    assert packet.count('HUMAN_USER_DECISION = PENDING') == 100
    assert packet.count('VALID NATIVE OPTIONS:') == 100
    assert all(row['human_user_decision'] is None for row in template['items'])
    assert all(row['human_user_decision'] is None for row in reconciled['items'])
    for row in template['items']:
        assert row['item_id'] in packet
    assert not review.LOCAL_PATH.search(packet)


def test_production_immutable_during_read_only_binding_when_available():
    db = review.ROOT / 'workspace/pro_a.db'
    if not db.exists() or not (review.ARTIFACT / 'a/review_population.json').exists():
        pytest.skip('private qualification inputs unavailable')
    before = review.sha256_file(db)
    assert len(review.check_binding()) == 100
    assert review.sha256_file(db) == before == review.PRODUCTION_SHA
