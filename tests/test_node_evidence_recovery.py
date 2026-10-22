"""Synthetic offline recovery: no production path, grant or real transport."""
import base64
import copy
import hashlib
import json

import pytest

from pro_a import node_evidence_recovery as recovery, output_provider_record_v7 as v7
from test_evidence_intent_prototype import setup, v6_record
from test_evidence_intent_v7 import new_record
from test_source_analysis_wire import canonical_claim, empty_canonical, normal_node


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NO_NETWORK'))
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', lambda *a, **k: pytest.fail('NO_PROVIDER'))


def case(*, same=False, single=False):
    data = setup('青松技术支持第一项研究。\n青松技术支持第二项研究。')
    ctx, catalog, series, plan = data
    segment = plan.leaves[0]
    canonical = empty_canonical()
    canonical['claims'] = [canonical_claim(u.exact_text, u, i) for i, u in enumerate(catalog.units, 1)]
    node = normal_node('青松技术')
    node['primary_type'] = 'Technology'
    canonical['node_candidates'] = [node]
    for claim in canonical['claims']:
        claim['related_candidate_names'] = ['青松技术']
    record = new_record(v6_record(catalog, segment, canonical), catalog)
    evidence = [v7.unit_selection(catalog.units[0]), v7.unit_selection(catalog.units[0 if same else 1])]
    record['node_candidates'][0]['evidence_properties'] = [{'field':'evidence_ref','value':e} for e in evidence[:1 if single else 2]]
    return data, record


def run(data, record, *, conversions=True):
    ctx, catalog, series, plan = data
    raw = json.dumps(record, ensure_ascii=False).encode()
    proposal = {'version':recovery.PLAN, 'raw_sha256':hashlib.sha256(raw).hexdigest(),
        'scope':recovery.scope(series, plan.leaves[0], ctx), 'conversions':[
            {'candidate_index':0,'canonical_name':'青松技术','semantics':recovery.SEMANTICS,
             'reviewer':'TEST_MODEL_NOT_HUMAN','reason':'Explicit synthetic support classification'}] if conversions else []}
    return raw, proposal, recovery.recover(raw, proposal, series, plan.leaves[0], catalog, ctx, plan=plan)


def test_single_evidence_preserves_existing_native_behavior():
    data, record = case(single=True)
    raw, proposal, artifact = run(data, record, conversions=False)
    result, review = v7.compile_result(raw.decode(), data[2], data[3].leaves[0], data[1], data[0], plan=data[3])
    assert artifact['result']['wire_json'] == result.wire_json and artifact['research_review'] == json.loads(json.dumps(review))
    assert artifact['projected_record'] == record and not artifact['support_mappings']


@pytest.mark.parametrize('same', [False, True])
def test_distinct_and_identical_occurrences_all_retained_on_existing_claim_edges(same):
    data, record = case(same=same)
    before = copy.deepcopy(record)
    with pytest.raises(ValueError, match='DUPLICATE_NODE_INTENT_PROPERTY:evidence_ref'):
        v7.compile_result(json.dumps(record), data[2], data[3].leaves[0], data[1], data[0])
    raw, proposal, artifact = run(data, record)
    assert record == before and base64.b64decode(artifact['raw_base64']) == raw
    assert len(artifact['support_mappings']) == 2
    assert len({m['original_binding']['binding_sha256'] for m in artifact['support_mappings']}) == (1 if same else 2)
    assert [m['original_property'] for m in artifact['support_mappings']] == record['node_candidates'][0]['evidence_properties']
    assert artifact['projected_record']['claims'] == record['claims']
    assert len(artifact['research_review']['candidate_ownership']['candidates'][0]['evidence_refs']) == 2
    assert artifact['formal_accepted'] is False and artifact['canonical_permission'] is False
    assert artifact['semantic_authorization'] == 'NOT_ESTABLISHED'
    ctx, cat, series, plan = data
    assert recovery.verify(artifact, raw, proposal, series, plan.leaves[0], cat, ctx, plan=plan) == artifact
    assert run(data, record)[2]['identity'] == artifact['identity']


@pytest.mark.parametrize('fault', ['missing_edge','changed_span','unknown_candidate','remove_candidate','scalar_duplicate','scalar_duplicate_same','event_type'])
def test_no_silent_drop_no_dependency_erasure_or_scalar_relaxation(fault):
    data, record = case()
    node = record['node_candidates'][0]
    if fault == 'missing_edge': record['claims'][1]['related_candidate_names'] = []
    elif fault == 'changed_span':
        record['claims'][1]['evidence'] = v7.unit_selection(data[1].units[1], 'RAW_SUBSPAN', '第二项研究', '1')
    elif fault == 'unknown_candidate': record['claims'][0]['related_candidate_names'].append('不存在的候选')
    elif fault == 'remove_candidate': record['node_candidates'] = []
    elif fault in ('scalar_duplicate','scalar_duplicate_same'):
        node['text_properties'] = [{'field':'importance','value':'a'},
                                   {'field':'importance','value':'a' if fault.endswith('_same') else 'b'}]
    else: node['primary_type'] = 'Event'
    before = copy.deepcopy(record)
    with pytest.raises(ValueError): run(data, record)
    assert record == before


@pytest.mark.parametrize('fault', ['raw','scope','permission','map','claim','classification'])
def test_frozen_identity_trace_and_permissions_cannot_be_forged(fault):
    data, record = case()
    raw, proposal, artifact = run(data, record)
    ctx, cat, series, plan = data
    changed = copy.deepcopy(artifact)
    if fault == 'raw': raw += b' '
    elif fault == 'scope': proposal['scope']['source_sha256'] = '0'*64
    elif fault == 'permission': changed['canonical_permission'] = True
    elif fault == 'map': changed['support_mappings'].pop()
    elif fault == 'claim': changed['projected_record']['claims'][0]['related_candidate_names'] = []
    else: proposal['conversions'][0]['semantics'] = 'GUESS_OWNERSHIP'
    with pytest.raises(ValueError): recovery.verify(changed, raw, proposal, series, plan.leaves[0], cat, ctx, plan=plan)


def test_unselected_duplicate_still_rejected():
    data, record = case()
    with pytest.raises(ValueError, match='DUPLICATE_NODE_INTENT_PROPERTY:evidence_ref'):
        run(data, record, conversions=False)


def test_offline_artifact_is_not_a_formal_origin_or_lifecycle_selection():
    from pro_a import candidate_origin, candidate_origin_v2
    data, record = case()
    _, _, artifact = run(data, record)
    assert artifact['version'] not in candidate_origin.VERSIONS
    assert candidate_origin_v2.ENTRY_CONTRACT['accepted_record_version'] == v7.VERSION
    assert artifact['formal_accepted'] is False and 'acceptance' not in artifact
    assert 'lifecycle_binding' not in artifact and 'human_decision' not in artifact
