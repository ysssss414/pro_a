"""Stage 3 identity, relation, provenance, replay, and read-only boundaries."""
from __future__ import annotations

import hashlib

import pytest

from pro_a.production_promotion import build_identity_catalog
from scripts.qualify_phase43_stage3 import (
    evidence_for, identity_resolution, immutable_write, relation_resolution,
)


def catalog(*nodes, aliases=()):
    return build_identity_catalog(
        [{'node_id': nid, 'canonical_name': name, 'primary_type': kind, 'status': 'active'}
         for nid, name, kind in nodes],
        [{'alias': alias, 'node_id': nid} for alias, nid in aliases],
    )


def comparison(name='Chiplet', recommendation='REUSE', existing='N1', cid='SC-CN-1'):
    return {'candidate_id': cid, 'observed_name': name,
            'recommended_disposition': recommendation, 'existing_node_id': existing}


def node(kind='Product', disposition='REUSE', classification='REUSE', status='GOVERNED_REUSE'):
    return {'content_sha256': 'frozen-content',
            'content': {'primary_type': kind, 'classification': classification,
                        'resolved_node_id': 'PROPOSED_1', 'reasons': [],
                        'raw': {'disposition': disposition, 'cross_domain_status': status,
                                'possible_existing_node_id': ''}}}


def relation(rel_type='uses', *, scope='exact scope', evidence=True, disposition='ACCEPTABLE'):
    return {'candidate_id': 'SC-RL-1', 'content_sha256': 'relation-content',
            'content': {'raw': {'source_ref': 'SC-CN-A', 'target_ref': 'SC-CN-B',
                                'relation_type': rel_type, 'scope': scope,
                                'temporal_status': 'categorical_source_scoped',
                                'disposition': disposition, 'direction_check': 'PASS',
                                'entailment_check': 'PASS', 'existing_relation_id': ''},
                        'reasons': [], 'evidence_bound': evidence, 'evidence_refs': ['EV1'],
                        'native_evidence': {'evidence_ref': 'EV1'},
                        'temporal_projection': {'runtime_status': 'categorical',
                                                'temporal_category': 'categorical_source_scoped',
                                                'valid_from': '', 'valid_to': ''}}}


def endpoints():
    return {'SC-CN-A': 'N1', 'SC-CN-B': 'N2'}


def existing(rel_type='uses', scope='exact scope'):
    return [{'relation_id': 'R1', 'from_node_id': 'N1', 'to_node_id': 'N2',
             'relation_type': rel_type, 'scope': scope, 'status': 'categorical',
             'temporal_category': 'categorical_source_scoped', 'valid_from': '', 'valid_to': ''}]


def test_exact_canonical_reuse_across_domain_labels():
    shared = catalog(('N1', 'NVIDIA', 'Company'))
    row = comparison('NVIDIA')
    candidate = node(kind='Company')
    assert identity_resolution(row, candidate, shared)['target_node_id'] == 'N1'
    assert identity_resolution({**row, 'primary_domain': 'semiconductor'}, candidate, shared)['outcome'] == 'REUSE_CANONICAL'


def test_registered_alias_retrieves_same_canonical_id():
    shared = catalog(('N1', 'NVIDIA', 'Company'), aliases=(('NVDA', 'N1'),))
    result = identity_resolution(comparison('NVDA'), node(kind='Company'), shared)
    assert result['outcome'] == 'REUSE_CANONICAL'
    assert result['retrieval']['exact_alias_ids'] == ['N1']


def test_generic_vs_vendor_specific_identity_is_distinct_proposal():
    shared = catalog(('N1', 'Server DRAM', 'Product'))
    row = comparison('Dynamic Random-Access Memory', 'CREATE', 'N1')
    candidate = node(disposition='CREATE', classification='CREATE', status='DISTINCT_BROADER_OR_DIFFERENT_OBJECT')
    result = identity_resolution(row, candidate, shared)
    assert result['outcome'] == 'CREATE_NEW_CANONICAL'
    assert result['target_node_id'] != 'N1'


def test_parent_child_near_match_does_not_merge():
    shared = catalog(('N1', 'Chiplet Architecture', 'Technology'))
    result = identity_resolution(comparison('Chiplet', 'REVIEW', 'N1'), node(), shared)
    assert result['outcome'] == 'DEFER'
    assert result['target_node_id'] is None


def test_type_mismatch_defers_even_with_exact_name():
    shared = catalog(('N1', 'Chiplet', 'Technology'))
    result = identity_resolution(comparison(), node(kind='Product'), shared)
    assert result['outcome'] == 'DEFER'
    assert 'TYPE_MISMATCH' in result['reasons']


def test_multiple_alias_owners_never_silently_reassigned():
    shared = catalog(('N1', 'A', 'Company'), ('N2', 'B', 'Company'),
                     aliases=(('COMMON', 'N1'), ('COMMON', 'N2')))
    result = identity_resolution(comparison('COMMON'), node(kind='Company'), shared)
    assert result['outcome'] == 'DEFER'
    assert result['catalog_candidate_ids'] == ['N1', 'N2']


def test_historical_quarantine_is_retained():
    candidate = node(status='QUARANTINED')
    result = identity_resolution(comparison(recommendation='CROSS_DOMAIN_QUARANTINE'), candidate, catalog())
    assert result['outcome'] == 'DEFER'
    assert 'HISTORICAL_QUARANTINE' in result['reasons']


def test_unadmitted_observation_and_ontology_pressure_defer():
    assert identity_resolution(comparison(cid=''), None, catalog())['outcome'] == 'DEFER'
    assert identity_resolution(comparison('Unknown', 'CREATE', ''),
                               node(kind='Unsupported', disposition='CREATE', classification='CREATE'),
                               catalog())['outcome'] == 'DEFER'


def test_stage2_human_rejection_cannot_be_overridden():
    human = {'human_input': {'decision': 'REJECT'}}
    result = identity_resolution(comparison(), node(), catalog(('N1', 'Chiplet', 'Product')), human)
    assert result['outcome'] == 'REJECT'


def test_exact_relation_duplicate_reuses_existing_id():
    result = relation_resolution(relation(), endpoints=endpoints(), existing=existing())
    assert result['outcome'] == 'REUSE_RELATION'
    assert result['existing_relation_ids'] == ['R1']


def test_different_relation_type_and_scope_coexist():
    for candidate in (relation('supplies'), relation(scope='different source scope')):
        result = relation_resolution(candidate, endpoints=endpoints(), existing=existing())
        assert result['outcome'] == 'CREATE_RELATION'
        assert result['existing_relation_ids'] == []


def test_same_edge_with_different_temporal_category_defers():
    prior = existing()
    prior[0]['temporal_category'] = 'vendor_scoped_2025'
    result = relation_resolution(relation(), endpoints=endpoints(), existing=prior)
    assert result['outcome'] == 'DEFER_RELATION'
    assert result['existing_relation_ids'] == ['R1']
    assert 'TEMPORAL_MISMATCH' in result['reasons']


def test_relation_endpoint_ambiguity_defers():
    result = relation_resolution(relation(), endpoints={'SC-CN-A': 'N1'}, existing=[])
    assert result['outcome'] == 'DEFER_RELATION'
    assert 'ENDPOINT_AMBIGUITY' in result['reasons']


def test_relation_ontology_pressure_and_evidence_risk_defer():
    assert relation_resolution(relation('unsupported'), endpoints=endpoints(), existing=[])['outcome'] == 'DEFER_RELATION'
    candidate = relation()
    candidate['content']['reasons'] = ['ONTOLOGY_PRESSURE']
    assert relation_resolution(candidate, endpoints=endpoints(), existing=[])['outcome'] == 'DEFER_RELATION'
    assert relation_resolution(relation(evidence=False), endpoints=endpoints(), existing=[])['outcome'] == 'DEFER_RELATION'


def test_relation_existing_target_mismatch_defers():
    candidate = relation()
    candidate['content']['raw']['existing_relation_id'] = 'OTHER'
    assert relation_resolution(candidate, endpoints=endpoints(), existing=existing())['outcome'] == 'DEFER_RELATION'


def test_frozen_human_relation_defer_is_preserved():
    human = {'human_input': {'decision': 'DEFER'}}
    assert relation_resolution(relation(), endpoints=endpoints(), existing=[], human=human)['outcome'] == 'DEFER_RELATION'


def test_claim_source_binding_blocks_cross_source_leakage():
    excerpt = 'exact source excerpt'
    evidence = {'EV1': {'evidence_id': 'EV1', 'source_id': 'S1', 'source_sha256': 'hash1',
                        'evidence_excerpt': excerpt, 'excerpt_sha256': hashlib.sha256(excerpt.encode()).hexdigest()}}
    sources = {'S1': {'source_id': 'S1', 'sha256': 'hash1'}, 'S2': {'source_id': 'S2', 'sha256': 'hash2'}}
    assert evidence_for(['EV1'], evidence, sources, source_id='S1')[0]['source_id'] == 'S1'
    with pytest.raises(ValueError, match='cross-source evidence leakage'):
        evidence_for(['EV1'], evidence, sources, source_id='S2')


def test_immutable_replay_adds_no_duplicate_or_changed_artifact(tmp_path):
    target = tmp_path / 'stage3' / 'resolution.json'
    assert immutable_write(target, b'fixed') is True
    assert immutable_write(target, b'fixed') is False
    with pytest.raises(ValueError, match='artifact replay drift'):
        immutable_write(target, b'changed')
