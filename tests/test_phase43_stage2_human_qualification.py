"""Frozen public authorization plus synthetic native governance regressions."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from pro_a.phase3f_foundation_baseline import build_review_packet, validate_review, validate_files
from pro_a.production_promotion import PromotionError, canonical_sha256, sha256_file

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('stage2_human', ROOT / 'scripts/apply_phase43_stage2_human_qualification.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def authorization():
    return json.loads((ROOT / 'docs/phase43_stage2_human_authorization.json').read_text('utf-8'))


@pytest.fixture
def template():
    return json.loads((ROOT / 'docs/phase43_stage2_human_decision_template.json').read_text('utf-8'))


def test_exact_authorized_identity_order_and_counts(authorization, template):
    MODULE.validate_decisions(authorization['decisions'], template)
    expected = {'A': {'baseline_views:ACCEPT': 8, 'claims:KEEP_NEEDS_REVIEW': 2, 'nodes:CREATE': 21},
        'B': {'aliases:DEFER': 7, 'claims:KEEP_NEEDS_REVIEW': 1, 'nodes:CREATE': 5,
              'nodes:DEFER': 23, 'nodes:REJECT': 2, 'relations:DEFER': 7},
        'C': {'aliases:ATTACH': 3, 'claims:KEEP': 2, 'nodes:CREATE': 15, 'nodes:REUSE': 2, 'relations:CREATE': 7}}
    for section, counts in expected.items():
        assert MODULE.Counter(d['object_type'] + ':' + d['human_input']['decision']
            for d in authorization['decisions'] if d['section'] == section) == counts


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'duplicate', 'reordered', 'recommendation', 'native', 'target', 'reviewer'])
def test_unauthorized_decision_changes_fail(authorization, template, mutation):
    rows = copy.deepcopy(authorization['decisions'])
    if mutation == 'missing':
        rows.pop()
    elif mutation == 'extra':
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == 'duplicate':
        rows[1] = copy.deepcopy(rows[0])
    elif mutation == 'reordered':
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == 'recommendation':
        rows[0]['system_recommended_decision'] = 'CREATE'
    elif mutation == 'native':
        rows[0]['human_input']['decision'] = 'CREATE'
    elif mutation == 'target':
        rows[0]['human_input']['target_id'] = 'UNAUTHORIZED'
    else:
        rows[0]['reviewer'] = 'AI_REVIEW_A'
    with pytest.raises(ValueError, match='HUMAN_AUTHORIZATION_BINDING_FAIL'):
        MODULE.validate_decisions(rows, template)


def test_sample_and_authority_boundaries(authorization):
    assert authorization['sample_seed'] == MODULE.SEED
    assert authorization['population_sha256'] == MODULE.POPULATION
    assert authorization['authority_source_sha256'] == MODULE.AUTHORIZATION
    assert authorization['residual_substantive_errors'] == 0
    assert authorization['residual_error_report_authority'] == 'HUMAN_USER'
    assert authorization['expanded_review_required'] is False
    for flag in ['production_apply_authorized', 'production_write_allowed',
                 'official_view_activation_authorized', 'current_view_write_authorized']:
        assert authorization[flag] is False
    original = json.loads((ROOT / 'docs/phase43_stage2_human_qualification_packet.json').read_text('utf-8'))
    assert {r['item_id'] for r in authorization['decisions'] if r['section'] == 'C'} == {
        r['candidate_id'] for r in original['items'] if r['section'] == 'C'}


@pytest.fixture
def native_fixture(authorization):
    # No private source text or database needed for the native path tests.
    package = {'mode': 'QUALIFIED_STRUCTURED_FOUNDATION_BACKFILL', 'sha256': 'a' * 64, 'inventory_sha256': 'b' * 64}
    registry = {'package_sha256': package['sha256'], 'package_inventory_sha256': package['inventory_sha256'],
        'materialization_mode': package['mode'], 'expected_sources': 1, 'qualified_provenance_sources': 1,
        'materialized_sources': 0, 'sources': [{'source_id': 'S1', 'provenance_verified': True,
        'upstream_sha256': 'c' * 64, 'expected_sha256': 'c' * 64}]}
    registry['registry_sha256'] = canonical_sha256(registry)
    objects = {kind: [] for kind in ('nodes', 'aliases', 'claims', 'relations', 'baseline_views')}
    decisions = copy.deepcopy(authorization['decisions'])
    for d in decisions:
        content = {'synthetic': d['item_id']}
        if d['object_type'] == 'claims':
            content.update(source_id='S1', source_sha256='c' * 64, evidence=[])
        objects[d['object_type']].append({'candidate_id': d['item_id'], 'content': content})
        d['native_content_sha256'] = canonical_sha256(content)
    objects['nodes'].extend({'candidate_id': f'UNSELECTED_{i:03}', 'content': {'synthetic': i}} for i in range(169))
    parent = build_review_packet(package=package, registry=registry, production={'sha256': MODULE.PRODUCTION},
        repository_commit=MODULE.IMPLEMENTATION, objects=objects, timestamp='2026-09-21T00:00:00Z')
    return parent, decisions


def test_native_scope_is_lossless_and_only_105_human_attributions(native_fixture):
    parent, decisions = native_fixture
    prior = copy.deepcopy(parent)
    blank, completed = MODULE.build_qualification(parent, decisions, 'f' * 64)
    assert parent == prior
    assert sum(map(len, parent['objects'].values())) == 274
    assert sum(map(len, completed['objects'].values())) == 105
    assert completed['packet_id'] != parent['packet_id']
    assert completed['qualification_scope']['parent_immutable_packet_sha256'] == parent['immutable_packet_sha256']
    assert completed['qualification_scope']['unselected_candidates_reviewed'] is False
    assert completed['qualification_scope']['full_operational_review_complete'] is False
    assert completed['human_completion']['reviewer'] == 'HUMAN_USER'
    assert parent['human_completion']['reviewer'] == ''
    for rows in parent['objects'].values():
        assert all(not r['human_input']['decision'] for r in rows)
    validate_review(completed, expected_sha256=blank['immutable_packet_sha256'], completed=True)
    # Even a complete qualification slice cannot become a Production handoff.
    with pytest.raises(PromotionError, match='STRUCTURED_CANDIDATE_NOT_PRODUCTION_HANDOFF'):
        validate_files(completed)


@pytest.mark.parametrize('mutation', ['missing_input', 'content', 'view', 'production', 'reviewer', 'missing_row'])
def test_native_governance_still_rejects_drift(native_fixture, mutation):
    parent, decisions = native_fixture
    blank, completed = MODULE.build_qualification(parent, decisions, 'f' * 64)
    row = completed['objects']['nodes'][0]
    if mutation == 'missing_input':
        row['human_input']['decision'] = ''
    elif mutation == 'content':
        row['content']['synthetic'] = 'tampered'
    elif mutation == 'view':
        completed['current_view_candidates'] = 1
    elif mutation == 'production':
        completed['production_apply_authorized'] = True
    elif mutation == 'reviewer':
        completed['human_completion']['reviewer'] = ''
    else:
        completed['objects']['nodes'].pop()
    with pytest.raises(PromotionError):
        validate_review(completed, expected_sha256=blank['immutable_packet_sha256'], completed=True)


def test_immutable_output_replay_and_drift(tmp_path):
    path = tmp_path / 'receipt.json'
    MODULE.immutable_write(path, b'first')
    MODULE.immutable_write(path, b'first')
    with pytest.raises(ValueError, match='immutable output drift'):
        MODULE.immutable_write(path, b'second')
    assert path.read_bytes() == b'first'


def test_committed_frozen_presentation_hashes():
    for name in ['HUMAN_QUALIFICATION_PACKET_SELF_CONTAINED.md', 'phase43_stage2_human_decision_template.json']:
        assert sha256_file(ROOT / 'docs' / name) == MODULE.BOUND_FILES['portability_v2/' + name]
