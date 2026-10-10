"""Pre-implementation qualification of strict Segment-local information loss.

These diagnostic tests reproduce a STOP condition, not a released projection.
All text, Nodes and canonical truth below are synthetic. No provider is called.
"""
import copy
import hashlib
import json

import pytest

from pro_a.analyzer import Analyzer, scope_node_catalog
from pro_a.bounded_extraction import (
    EvidenceDisposition, aggregate_segment_wires, create_extraction_series,
    create_segment_wire_result, expand_source_analysis_wire_v3,
    initial_extraction_plan, subdivide_extraction_plan,
)
from pro_a.operational_ingestion import deterministic_id
from pro_a.source_analysis_wire import SourcePieceContext, build_source_evidence_catalog
from stability_helpers import make_config
from test_bounded_extraction import v3
from test_source_analysis_wire import canonical_claim, empty_canonical


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('PROVIDER_FORBIDDEN_DURING_BOUNDARY_QUALIFICATION')
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', forbidden)


def fixture(tmp_path, company, prefix, suffix=0):
    cfg, db = make_config(tmp_path)
    db.add_node(company, 'Entity')
    analyzer = Analyzer(cfg, db)
    units = [f'合成仪器编号{i}已完成校准。' for i in range(prefix)]
    units += [f'以下产能数据仅指{company}。', '该公司现有产能为100台。']
    units += [f'合成设备编号{i}已完成检查。' for i in range(suffix)]
    source = '[[PARA:1]]\n' + '\n'.join(units)
    native = analyzer.plan_initial_extraction('synthetic.txt', source, 'deep', adaptive_retry_policy='forbid')
    assert len(native.pieces) == 1
    piece = native.pieces[0]
    context = SourcePieceContext(hashlib.sha256(source.encode()).hexdigest(),
                                piece.source_piece, piece.scoped_node_ids)
    catalog = build_source_evidence_catalog(context)
    assert [unit.exact_text for unit in catalog.units] == units
    assert catalog.units[prefix].block_ordinal == catalog.units[prefix + 1].block_ordinal
    assert catalog.units[prefix].locator == catalog.units[prefix + 1].locator == 'PARA:1'
    series = create_extraction_series(context, catalog, 'RUN_SYNTHETIC_BOUNDARY')
    raw = empty_canonical()
    raw['claims'] = [canonical_claim(f'{company}现有产能为100台。', catalog.units[prefix + 1],
        nature='data', attributed_to='合成记录', scope=company)]
    return analyzer, piece, context, catalog, series, initial_extraction_plan(series), raw


def local_input(piece, catalog, segment):
    """Exactly the user-specified source interval and frozen Node subset.

    This is an audit oracle, not a production request renderer. Opaque IDs and
    hashes remain distinct and are not treated as semantic Source context.
    """
    units = catalog.units[segment.range_start:segment.range_end]
    assert tuple(unit.evidence_ref for unit in units) == segment.assigned_evidence_refs
    assert tuple(unit.ordinal for unit in units) == tuple(range(segment.range_start + 1, segment.range_end + 1))
    text = piece.source_piece.source_text[units[0].source_start:units[-1].source_end]
    for unit in units:
        assert piece.source_piece.source_text[unit.source_start:unit.source_end] == unit.exact_text
    return text, scope_node_catalog(list(piece.scoped_node_catalog), text)


def native_truth(analyzer, context, catalog, raw):
    expanded = expand_source_analysis_wire_v3(v3(raw, catalog), catalog, context)
    expected = analyzer._validate_source_output(raw, context.piece.source_text)
    actual = analyzer._validate_source_output(expanded, context.piece.source_text)
    assert actual == expected and actual['claims'][0]['evidence_validated']
    return actual['claims'][0]


def test_same_segment_retains_adjacent_antecedent_and_measurement(tmp_path):
    analyzer, piece, context, catalog, series, plan, raw = fixture(tmp_path, '青松公司', 14)
    assert len(catalog.units) == 16 and len(plan.leaves) == 1
    text, nodes = local_input(piece, catalog, plan.leaves[0])
    assert '青松公司' in text and '100台' in text
    assert len(nodes) == 1
    dispositions = tuple(EvidenceDisposition(unit.evidence_ref,
        'CLAIMED' if unit.ordinal == 16 else 'CONTEXT_ONLY') for unit in catalog.units)
    result = create_segment_wire_result(series, plan.leaves[0], v3(raw, catalog), dispositions, catalog, context)
    aggregate = aggregate_segment_wires(series, plan, (result,), catalog, context)
    assert aggregate.coverage.complete
    expanded = expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, context)
    assert analyzer._validate_source_output(expanded, context.piece.source_text)['claims'] == [
        native_truth(analyzer, context, catalog, raw)]


@pytest.mark.parametrize('subdivide', [False, True], ids=['initial-16-ref-boundary', 'subdivision-8-ref-boundary'])
def test_cross_segment_loses_subject_information_required_by_native_truth(tmp_path, subdivide):
    semantic_inputs, truths, identities = [], [], []
    for number, company in enumerate(('青松公司', '白杨公司')):
        path = tmp_path / str(number)
        path.mkdir()
        prefix, suffix = (7, 7) if subdivide else (15, 0)
        analyzer, piece, context, catalog, series, plan, raw = fixture(path, company, prefix, suffix)
        if subdivide:
            # The unchanged parent contains enough context. Its deterministic
            # children split the adjacent antecedent and measurement.
            text, nodes = local_input(piece, catalog, plan.leaves[0])
            assert company in text and '100台' in text and len(nodes) == 1
            plan = subdivide_extraction_plan(series, plan, plan.leaves[0].segment_id)
        assert len(plan.leaves) == 2
        assert [len(leaf.assigned_evidence_refs) for leaf in plan.leaves] == ([8, 8] if subdivide else [16, 1])
        first, second = plan.leaves
        left_text, _ = local_input(piece, catalog, first)
        right_text, right_nodes = local_input(piece, catalog, second)
        assert company in left_text and '100台' not in left_text
        assert company not in right_text and '该公司现有产能为100台。' in right_text
        assert right_nodes == []
        semantic_inputs.append((right_text, right_nodes))
        truth = native_truth(analyzer, context, catalog, raw)
        truths.append(truth['statement'])
        identities.append((context.source_sha256, series.series_id, second.segment_id))
        # Declining an unresolved subject is legitimate local behavior; coverage
        # accounting can still complete, but concatenate-only aggregation does
        # not recover the missing canonical Claim.
        results = tuple(create_segment_wire_result(series, leaf, v3(empty_canonical(), catalog),
            tuple(EvidenceDisposition(ref, 'CONTEXT_ONLY') for ref in leaf.assigned_evidence_refs),
            catalog, context) for leaf in plan.leaves)
        aggregate = aggregate_segment_wires(series, plan, results, catalog, context)
        assert aggregate.coverage.complete
        expanded = expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, context)
        assert expanded['claims'] == [] and raw['claims']
        expected_id = deterministic_id('CLM', {'source_sha256': context.source_sha256,
            'claim_index': 0, 'claim': truth})
        assert expected_id and not expanded['claims']
    assert semantic_inputs[0] == semantic_inputs[1]
    assert truths == ['青松公司现有产能为100台。', '白杨公司现有产能为100台。']
    assert identities[0] != identities[1]  # No assertion that request bytes match.


def test_frozen_aggregator_does_not_resolve_pronoun_claim_from_other_segment(tmp_path):
    analyzer, piece, context, catalog, series, plan, raw = fixture(tmp_path, '青松公司', 15)
    truth = native_truth(analyzer, context, catalog, raw)
    generic = copy.deepcopy(raw)
    generic['claims'][0].update(statement='该公司现有产能为100台。', scope='')
    results = []
    for leaf in plan.leaves:
        response = generic if leaf.range_start == 16 else empty_canonical()
        results.append(create_segment_wire_result(series, leaf, v3(response, catalog),
            tuple(EvidenceDisposition(ref, 'CLAIMED' if leaf.range_start == 16 else 'CONTEXT_ONLY')
                  for ref in leaf.assigned_evidence_refs), catalog, context))
    aggregate = aggregate_segment_wires(series, plan, tuple(results), catalog, context)
    assert aggregate.coverage.complete
    expanded = expand_source_analysis_wire_v3(json.loads(aggregate.wire_json), catalog, context)
    actual = analyzer._validate_source_output(expanded, context.piece.source_text)['claims'][0]
    assert actual['statement'] == '该公司现有产能为100台。' != truth['statement']
    def claim_id(claim):
        return deterministic_id('CLM', {'source_sha256': context.source_sha256, 'claim_index': 0, 'claim': claim})
    assert claim_id(actual) != claim_id(truth)
