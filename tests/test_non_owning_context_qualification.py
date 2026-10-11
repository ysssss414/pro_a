"""Synthetic B0 falsification: passing tests do not imply Candidate B PASS."""
import copy
import json

import pytest

from non_owning_context_probe import (VERSION, lexical_graph_probe, project,
    exact_substitution_probe, direct_refs_probe)
from pro_a.analyzer import Analyzer
from pro_a.bounded_extraction import (EvidenceDisposition, create_extraction_series,
    initial_extraction_plan, subdivide_extraction_plan, create_segment_wire_result,
    aggregate_segment_wires, expand_source_analysis_wire_v3)
from pro_a.operational_ingestion import deterministic_id
from pro_a.source_analysis_wire import build_source_evidence_catalog
from test_bounded_extraction import v3
from test_source_analysis_wire import context, canonical_claim, empty_canonical


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*a, **k):
        pytest.fail('PROVIDER_FORBIDDEN')
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', forbidden)


def case(text, company='青松公司', context_index=0, **context_args):
    nodes = [{'node_id': 'NODE_PINE', 'canonical_name': '青松公司', 'aliases': []},
             {'node_id': 'NODE_POPLAR', 'canonical_name': '白杨公司', 'aliases': []}]
    ctx = context(text, tuple(n['node_id'] for n in nodes), **context_args)
    catalog = build_source_evidence_catalog(ctx)
    target = next(u for u in catalog.units if '该公司' in u.exact_text)
    dep = {'kind': 'REFERENT_RESOLUTION', 'context_evidence_ref': catalog.units[context_index].evidence_ref,
        'target_selector': '该公司', 'context_selector': company,
        'resolved_node_id': next(n['node_id'] for n in nodes if n['canonical_name'] == company)}
    graph = {'version': VERSION, 'dispositions': [{'target_evidence_ref': u.evidence_ref,
        'status': 'DEPENDENCY' if u == target else 'NO_DEPENDENCY',
        'dependencies': [dep] if u == target else []} for u in catalog.units]}
    return ctx, catalog, nodes, graph, target


def probe(data):
    ctx, catalog, nodes, graph, _ = data
    return lexical_graph_probe(graph, catalog, ctx, nodes)


@pytest.mark.parametrize('company', ['青松公司', '白杨公司'])
@pytest.mark.parametrize('subdivide', [False, True])
def test_pr100_truth_with_hand_authored_correct_dependency(company, subdivide):
    # Reconstructed from PR100 diagnostic 9c58aa16d578af31d28c468cafe6d2cb1ce01cd5.
    prefix, suffix = (7, 7) if subdivide else (15, 0)
    text = '\n'.join([f'合成仪器编号{i}已校准。' for i in range(prefix)] +
        [f'以下产能数据仅指{company}。', '该公司现有产能为100台。'] +
        [f'合成设备编号{i}已检查。' for i in range(suffix)])
    data = case(text, company, prefix)
    ctx, catalog, nodes, graph, target = data
    graph = probe(data)
    series = create_extraction_series(ctx, catalog, 'RUN_SYNTHETIC_CONTEXT')
    plan = initial_extraction_plan(series)
    if subdivide:
        plan = subdivide_extraction_plan(series, plan, plan.leaves[0].segment_id)
    assert [len(s.assigned_evidence_refs) for s in plan.leaves] == ([8, 8] if subdivide else [16, 1])
    results = []
    truth = empty_canonical()
    truth['claims'] = [canonical_claim(f'{company}现有产能为100台。', target,
        nature='data', scope=company, attributed_to='合成记录')]
    for segment in plan.leaves:
        view = project(graph, segment.assigned_evidence_refs, catalog)
        serialized = json.dumps(view, ensure_ascii=False)
        assert not any(u.evidence_ref in serialized for u in catalog.units
                       if u.evidence_ref not in segment.assigned_evidence_refs)
        has_target = target.evidence_ref in segment.assigned_evidence_refs
        assert len(view['context']) == int(has_target)
        raw = truth if has_target else empty_canonical()
        if has_target:
            exact_substitution_probe(raw['claims'][0]['statement'], target, graph['dependencies'][0])
        results.append(create_segment_wire_result(series, segment, v3(raw, catalog),
            tuple(EvidenceDisposition(ref, 'CLAIMED' if ref == target.evidence_ref else 'CONTEXT_ONLY')
                  for ref in segment.assigned_evidence_refs), catalog, ctx))
    aggregate = aggregate_segment_wires(series, plan, tuple(results), catalog, ctx)
    assert aggregate.coverage.complete
    native = Analyzer.__new__(Analyzer)
    expected = native._validate_source_output(truth, text)
    actual = native._validate_source_output(expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, ctx), text)
    assert actual == expected
    def claim_id(value):
        return deterministic_id('CLM', {'source_sha256': ctx.source_sha256, 'claim_index': 0, 'claim': value['claims'][0]})
    assert claim_id(actual) == claim_id(expected)
    # Provenance is outside the native Claim, never part of permanent identity.
    assert not any(key in actual['claims'][0] for key in ('graph_id', 'context_id', 'dependency_id'))


@pytest.mark.parametrize('joiner', ['\n\n', '\n专家：', '\n10:01 ', '\n产能说明：'])
def test_explicit_graph_crosses_parser_boundaries(joiner):
    data = case('以下产能数据仅指青松公司。' + joiner + '该公司现有产能为100台。')
    graph = probe(data)
    assert data[1].units[0].block_ordinal != data[4].block_ordinal
    assert len(project(graph, (data[4].evidence_ref,), data[1])['context']) == 1


@pytest.mark.parametrize('foreign', ['青松公司2028年产能将达到9999台。', '青松公司客户包括A公司和B公司。'])
def test_selector_projection_and_exact_delta_exclude_foreign_facts(foreign):
    data = case(foreign + '该公司当前产能为100台。')
    graph = probe(data)
    view = project(graph, (data[4].evidence_ref,), data[1])
    assert view['context'][0]['context_selector'] == '青松公司'
    visible = json.dumps(view, ensure_ascii=False)
    assert all(word not in visible for word in ('9999', '2028', '将达到', '客户', 'A公司', 'B公司'))
    exact_substitution_probe('青松公司当前产能为100台。', data[4], graph['dependencies'][0])
    for statement in (foreign, '青松公司当前产能为9999台。', '青松公司2028年产能为100台。'):
        with pytest.raises(ValueError, match='UNAUTHORIZED_STATEMENT_DELTA'):
            exact_substitution_probe(statement, data[4], graph['dependencies'][0])


@pytest.mark.parametrize('mutation,code', [
    ({'target_selector': '不存在'}, 'EVIDENCE_SELECTOR_NOT_FOUND'),
    ({'context_selector': '青松'}, 'INVALID_RESOLVED_NODE'),
    ({'context_selector': '不存在'}, 'EVIDENCE_SELECTOR_NOT_FOUND'),
    ({'resolved_node_id': 'NODE_INVENTED'}, 'INVALID_RESOLVED_NODE'),
    ({'kind': 'GENERAL_CONTEXT'}, 'UNSUPPORTED_KIND'),
    ({'field': 'scope'}, 'INVALID_DEPENDENCY_SHAPE'),
    ({'context_evidence_ref': 'CTX_SYNTHETIC'}, 'INVALID_CONTEXT_REF')])
def test_structural_negative_dependencies(mutation, code):
    data = case('以下产能数据仅指青松公司。该公司现有产能为100台。')
    data[3]['dispositions'][-1]['dependencies'][0].update(mutation)
    with pytest.raises(ValueError, match=code):
        probe(data)


@pytest.mark.parametrize('field', ['claims', 'statement', 'node_candidates', 'relation_candidates', 'source_metadata'])
def test_resolver_cannot_output_extraction(field):
    data = case('青松公司。该公司现有产能为100台。')
    data[3][field] = []
    with pytest.raises(ValueError, match='INVALID_GRAPH_SHAPE'):
        probe(data)


def test_ambiguous_selector_and_incomplete_graph_rejected():
    data = case('青松公司与青松公司同名。该公司现有产能为100台。')
    with pytest.raises(ValueError, match='EVIDENCE_SELECTOR_AMBIGUOUS'):
        probe(data)
    data[3]['dispositions'].pop()
    with pytest.raises(ValueError, match='INCOMPLETE_GRAPH'):
        probe(data)


@pytest.mark.parametrize('kind', ['different_source', 'different_piece', 'self'])
def test_foreign_or_self_dependency(kind):
    data = case('青松公司。该公司现有产能为100台。')
    other = case('青松公司。该公司现有产能为100台。',
        **({'source_sha': 'a'*64} if kind == 'different_source' else {'chunk_index': 2}))
    data[3]['dispositions'][-1]['dependencies'][0]['context_evidence_ref'] = (
        data[4].evidence_ref if kind == 'self' else other[1].units[0].evidence_ref)
    with pytest.raises(ValueError, match='INVALID_CONTEXT_REF'):
        probe(data)


def test_context_and_foreign_ev_cannot_be_direct_evidence():
    data = case('青松公司。该公司现有产能为100台。')
    graph = probe(data)
    for ref in (graph['dependencies'][0]['context_id'], data[1].units[0].evidence_ref):
        with pytest.raises(ValueError, match='NON_OWNED_PRIMARY_EVIDENCE'):
            direct_refs_probe([ref], [data[4].evidence_ref])


def test_wrong_antecedent_passes_lexical_proofs_but_must_not_be_accepted():
    """STOP evidence: syntactic graph completeness is not semantic edge proof."""
    text = '以下产能数据仅指青松公司。白杨公司与本次产能数据无关。该公司现有产能为100台。'
    data = case(text, '白杨公司', 1)
    graph = probe(data)
    wrong = '白杨公司现有产能为100台。'
    exact_substitution_probe(wrong, data[4], graph['dependencies'][0])
    assert graph['semantic_authorization'] == 'UNPROVEN'
    assert wrong != '青松公司现有产能为100台。'
    # Native validation also checks Evidence binding, not referent truth.
    raw = empty_canonical()
    raw['claims'] = [canonical_claim(wrong, data[4], nature='data')]
    assert Analyzer.__new__(Analyzer)._validate_source_output(raw, text)['claims'][0]['evidence_validated']


def test_ambiguous_two_antecedents_are_not_rejected_by_lexical_proofs():
    text = '青松公司和白杨公司均参加了会议。该公司现有产能为100台。'
    for company in ('青松公司', '白杨公司'):
        data = case(text, company)
        graph = probe(data)
        exact_substitution_probe(f'{company}现有产能为100台。', data[4], graph['dependencies'][0])
        assert graph['semantic_authorization'] == 'UNPROVEN'


def test_no_dependency_and_explicit_ambiguity_do_not_project_context():
    data = case('青松公司。该公司现有产能为100台。')
    for status in ('NO_DEPENDENCY', 'AMBIGUOUS_DEPENDENCY'):
        data[3]['dispositions'][-1].update(status=status, dependencies=[])
        assert project(probe(data), (data[4].evidence_ref,), data[1])['context'] == []


def test_cycle_and_duplicate_disposition_fail_closed():
    data = case('青松公司提到该公司。白杨公司提到该公司。')
    for index, row in enumerate(data[3]['dispositions']):
        row.update(status='DEPENDENCY', dependencies=[{'kind': 'REFERENT_RESOLUTION',
            'context_evidence_ref': data[1].units[1-index].evidence_ref, 'target_selector': '该公司',
            'context_selector': ('白杨公司', '青松公司')[index],
            'resolved_node_id': ('NODE_POPLAR', 'NODE_PINE')[index]}])
    with pytest.raises(ValueError, match='CIRCULAR_DEPENDENCY'):
        probe(data)
    data[3]['dispositions'].append(copy.deepcopy(data[3]['dispositions'][0]))
    with pytest.raises(ValueError, match='INCOMPLETE_GRAPH'):
        probe(data)
