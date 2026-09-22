"""Frozen HUMAN_USER qualification and native handoff safeguards."""
import copy
from collections import Counter

import pytest

from scripts import apply_phase43_stage3_human_qualification as human


def completed():
    path = human.ROOT / 'docs/phase43_stage3_human_decisions_completed.json'
    if not path.is_file():
        pytest.skip('completed Stage 3 qualification artifact is not present')
    return human.read(path)


def private_handoff():
    path = human.frozen.ARTIFACT / 'a/review_population.json'
    native = human.STORE / 'native_qualification.completed.json'
    if not path.is_file() or not native.is_file():
        pytest.skip('private Stage 3 native handoff is not present')
    return human.read(path), human.read(native)


def test_frozen_pr_head_binding_and_commit_replay(monkeypatch):
    base = human.PRE_HUMAN_HEAD
    child = 'a' * 40
    values = {'HEAD': base, 'HEAD^': 'b' * 40,
              'origin/codex/phase43-stage3-cross-domain-resolution': base}
    monkeypatch.setattr(human, 'git', lambda *args: values[args[-1]])
    human.validate_head()
    values['HEAD'] = child
    values['HEAD^'] = base
    human.validate_head()
    values['origin/codex/phase43-stage3-cross-domain-resolution'] = child
    human.validate_head()
    values['origin/codex/phase43-stage3-cross-domain-resolution'] = 'c' * 40
    with pytest.raises(ValueError, match='STAGE3_HUMAN_AUTHORIZATION_BINDING_FAIL'):
        human.validate_head()
    values['origin/codex/phase43-stage3-cross-domain-resolution'] = child
    values['HEAD^'] = 'd' * 40
    with pytest.raises(ValueError, match='STAGE3_HUMAN_AUTHORIZATION_BINDING_FAIL'):
        human.validate_head()


def test_exact_human_decisions_and_frozen_system_recommendations():
    document = completed()
    rows = document['decisions']
    blank = human.read(human.ROOT / 'docs/phase43_stage3_human_decision_template.json')['items']
    reconciliation = human.read(human.ROOT / 'docs/phase43_stage3_ai_review_reconciliation.json')['items']
    assert len(rows) == len({row['item_id'] for row in rows}) == len(blank) == 100
    assert [row['item_id'] for row in rows] == [row['item_id'] for row in blank]
    assert Counter(row['section'] for row in rows) == {'A': 96, 'B': 4}
    assert all(row['reviewer'] == 'HUMAN_USER' and row['human_input']['decision']
               for row in rows)
    assert all(row['human_user_decision'] == template['system_recommended_decision'] ==
               reviewed['system_recommended_decision']
               for row, template, reviewed in zip(rows, blank, reconciliation, strict=True)
               if row['section'] == 'A')
    assert all(template['human_user_decision'] is None for template in blank)
    assert all(reviewed['human_user_decision'] is None for reviewed in reconciliation)
    assert {row['item_id'] for row in rows if row['section'] == 'B'} == set(human.OVERRIDES)
    for row in rows:
        assert row['human_input'] == {'decision': row['human_user_decision'],
                                      'target_id': row['target_id'] or '',
                                      'reason': row['human_user_reason']}


def test_exact_four_overrides_targets_and_aggregate_counts():
    rows = completed()['decisions']
    by_id = {row['item_id']: row for row in rows}
    for item_id, (decision, target, reason) in human.OVERRIDES.items():
        row = by_id[item_id]
        assert (row['human_user_decision'], row['target_id'] or '',
                row['human_user_reason']) == (decision, target, reason)
    assert by_id['SC-CN-0051']['target_id'] == 'NODE_20260817_7A9AE357'
    assert {key: Counter(row['human_user_decision'] for row in rows
                         if row['object_type'] == 'identity')[key]
            for key in human.EXPECTED_IDENTITY} == human.EXPECTED_IDENTITY
    assert {key: Counter(row['human_user_decision'] for row in rows
                         if row['object_type'] == 'relation')[key]
            for key in human.EXPECTED_RELATION} == human.EXPECTED_RELATION
    assert sum(row['human_user_decision'] in ('DEFER', 'REJECT', 'DEFER_RELATION')
               for row in rows) == 31


def test_native_completion_preserves_parent_candidates_and_evidence():
    parent, native = private_handoff()
    decisions = completed()['decisions']
    template = human.read(human.ROOT / 'docs/phase43_stage3_human_decision_template.json')['items']
    reconciliation = human.read(human.ROOT / 'docs/phase43_stage3_ai_review_reconciliation.json')['items']
    human.validate_decisions(decisions, parent['items'], template, reconciliation)
    human.validate_completed(parent, native, decisions)
    assert native['human_completion'] == {
        'reviewer': 'HUMAN_USER', 'expected': 100, 'applied': 100,
        'missing': 0, 'extra': 0, 'residual_sample_size': 0}
    assert all(row['human_input'] == decision['human_input']
               for row, decision in zip(native['items'], decisions, strict=True))
    for row in native['items']:
        if row['kind'] == 'relation' and row['human_input']['decision'] == 'CREATE_RELATION':
            candidate = row['frozen_candidate']['content']
            resolution = row['resolution']
            assert set(candidate['evidence_refs']) == set(resolution['evidence_refs'])
            assert (candidate['relation_type'], candidate['scope'],
                    candidate['temporal_projection']) == (
                    resolution['relation_type'], resolution['scope'],
                    resolution['temporal_projection'])


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'duplicate', 'section_a',
                                      'override', 'target', 'native', 'reviewer', 'parent_hash'])
def test_native_validator_rejects_unauthorized_changes(mutation):
    parent, _ = private_handoff()
    rows = copy.deepcopy(completed()['decisions'])
    template = human.read(human.ROOT / 'docs/phase43_stage3_human_decision_template.json')['items']
    reconciliation = human.read(human.ROOT / 'docs/phase43_stage3_ai_review_reconciliation.json')['items']
    if mutation == 'missing':
        rows.pop()
    elif mutation == 'extra':
        rows.append(copy.deepcopy(rows[0]))
        rows[-1]['item_id'] = 'EXTRA'
    elif mutation == 'duplicate':
        rows[1]['item_id'] = rows[0]['item_id']
    elif mutation == 'section_a':
        first = next(row for row in rows if row['section'] == 'A')
        first['human_user_decision'] = 'DEFER'
    elif mutation == 'override':
        next(row for row in rows if row['item_id'] == 'SC-CN-0033')['human_user_decision'] = 'DEFER'
    elif mutation == 'target':
        next(row for row in rows if row['item_id'] == 'SC-CN-0051')['target_id'] = 'OTHER_NODE'
    elif mutation == 'native':
        rows[0]['human_input']['decision'] = 'DEFER'
    elif mutation == 'reviewer':
        rows[0]['reviewer'] = 'AI_REVIEW_A'
    else:
        rows[0]['parent_item_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='STAGE3_HUMAN_AUTHORIZATION_BINDING_FAIL'):
        human.validate_decisions(rows, parent['items'], template, reconciliation)


def test_immutable_input_hashes_and_production_boundary():
    receipt_path = human.ROOT / 'docs/phase43_stage3_final_human_qualification_receipt.json'
    if not receipt_path.is_file():
        pytest.skip('completed Stage 3 receipt is not present')
    receipt = human.read(receipt_path)
    for name, expected in {
        'docs/PHASE43_STAGE3_HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md': human.PACKET_SHA,
        'docs/phase43_stage3_human_decision_template.json': human.TEMPLATE_SHA,
        'docs/phase43_stage3_ai_review_a.json': human.REVIEW_A_SHA,
        'docs/phase43_stage3_ai_review_b.json': human.REVIEW_B_SHA,
        'docs/phase43_stage3_ai_review_reconciliation.json': human.RECONCILIATION_SHA,
    }.items():
        assert human.sha256_file(human.ROOT / name) == expected
    assert human.sha256_file(human.ROOT / 'docs/phase43_stage3_human_decisions_completed.json') == \
        receipt['completed_decision_file_sha256']
    assert receipt['human_decisions'] == {'expected': 100, 'applied': 100, 'missing': 0,
                                           'extra': 0, 'section_a': 96, 'section_b': 4,
                                           'residual_sample_size': 0}
    assert receipt['qualification']['final_human'] == 'PASS'
    assert receipt['production'] == {'sha_before': human.frozen.PRODUCTION_SHA,
                                     'sha_after': human.frozen.PRODUCTION_SHA,
                                     'write_count': 0, 'apply_executed': False,
                                     'source_writes': 0, 'relation_writes': 0}
    assert receipt['views'] == {'official_view_activations': 0, 'current_view_writes': 0}
    db = human.ROOT / 'workspace/pro_a.db'
    if db.is_file():
        assert human.sha256_file(db) == human.frozen.PRODUCTION_SHA
