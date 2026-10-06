"""Whole-piece qualification uses synthetic content and no external provider."""
import copy
import json
from dataclasses import asdict
from dataclasses import replace
from types import SimpleNamespace

import pytest
from lexical_record_helpers import from_wire

from pro_a.bounded_extraction import expand_source_analysis_wire_v3
from pro_a.source_analysis_wire import build_source_evidence_catalog
from test_source_analysis_wire import (
    compact_fixture, context, dense_fixture, mixed_fixture, empty_canonical,
    canonical_claim,
)


def wire3(raw, catalog):
    wire = compact_fixture(raw, catalog)
    wire['wire_version'] = 'source-analysis-wire-v3'
    for claim, original in zip(wire['claims'], raw['claims']):
        claim['evidence_pointer'] = original['evidence_pointer']
    return wire


def payload_for(ctx):
    return {'source_piece': asdict(ctx.piece), 'source_text': ctx.piece.source_text,
            'piece_id': ctx.piece.piece_id, 'source_piece_sha256': ctx.piece.source_sha256,
            'source_sha256': ctx.source_sha256,
            'scoped_node_catalog': [{'node_id': n, 'canonical_name': n} for n in ctx.known_node_ids]}


@pytest.mark.parametrize('role', ['primary', 'related', 'PRIMARY', 'Related', ' primary ', 'Company', 'supplier', 'customer'])
def test_prompt_validator_exact_enum_parity(role):
    from pro_a.whole_piece_compact import SYSTEM, ENUM_TABLE, parse
    from pro_a.source_analysis_wire import NODE_MATCH_ROLES
    from pro_a.source_analysis_provider_record import record_schema
    assert set(record_schema()['properties']['node_matches']['items']['properties']['role']['enum']) == set(NODE_MATCH_ROLES)
    assert ENUM_TABLE['node_matches[].role'] is NODE_MATCH_ROLES
    ctx, catalog, raw = mixed_fixture()
    wire = wire3(raw, catalog)
    wire['node_matches'][0]['role'] = role
    if role in NODE_MATCH_ROLES:
        assert parse(json.dumps(from_wire(wire)), payload_for(ctx))['node_matches'][0]['role'] == role
    else:
        with pytest.raises(ValueError, match='INVALID_WHOLE_PIECE_LEXICAL_RESPONSE'):
            parse(json.dumps(from_wire(wire)), payload_for(ctx))


def test_whole_piece_render_and_strict_envelope():
    from pro_a.whole_piece_compact import parse, render
    ctx, catalog, raw = dense_fixture()
    payload = payload_for(ctx)
    request = render(payload)
    user = request['messages'][1]['content']
    for unit in catalog.units:
        assert '[' + unit.evidence_ref + ']' + unit.exact_text in user
    assert 'assigned_evidence_refs' not in user and 'dispositions' not in user
    assert request['max_tokens'] == 12000
    assert parse(json.dumps(from_wire(wire3(raw, catalog))), payload) == raw
    for content in ['{', '{"wire":{},"wire":{}}', '{"wire":{},"dispositions":[]}', '{"wire":NaN}']:
        with pytest.raises(ValueError, match='INVALID_WHOLE_PIECE_LEXICAL_RESPONSE'):
            parse(content, payload)


@pytest.mark.parametrize('change', ['foreign_ref', 'foreign_source', 'wrong_piece', 'unknown_node', 'offset', 'catalog', 'relation'])
def test_whole_piece_rejects_invalid_provenance(change):
    from pro_a.whole_piece_compact import parse
    ctx, catalog, raw = mixed_fixture()
    wire, payload = wire3(raw, catalog), payload_for(ctx)
    if change == 'foreign_ref':
        wire['claims'][0]['evidence_ref'] = 'EV_INVENTED'
    elif change == 'foreign_source':
        payload['source_sha256'] = 'a' * 64
    elif change == 'wrong_piece':
        payload['source_piece']['chunk_index'] = 2
    elif change == 'unknown_node':
        wire['node_matches'][0]['node_id'] = 'NODE_INVENTED'
    elif change == 'offset':
        wire['claims'][0]['source_start'] = 0
    elif change == 'relation':
        wire['relation_candidates'][0]['supporting_claim_refs'] = ['C999']
    else:
        with pytest.raises(ValueError):
            expand_source_analysis_wire_v3(wire, replace(catalog, units=catalog.units[:-1]), ctx)
        return
    with pytest.raises(ValueError, match='INVALID_WHOLE_PIECE_LEXICAL_RESPONSE'):
        parse(json.dumps(from_wire(wire)), payload)


@pytest.mark.parametrize('selector,mode,occurrence,expected', [
    ('capacity', 'RAW_SUBSPAN', 2, 'capacity'), ('ABC', 'NORMALIZED_SUBSPAN', 1, 'ABC'),
    ('capacity', 'RAW_SUBSPAN', None, None), ('ABC', 'RAW_SUBSPAN', 1, None),
])
def test_whole_piece_selector_contract(selector, mode, occurrence, expected):
    from pro_a.whole_piece_compact import parse
    ctx = context('capacity capacity ＡＢＣ')
    catalog = build_source_evidence_catalog(ctx)
    raw = empty_canonical()
    raw['claims'] = [canonical_claim('Synthetic measurement.', catalog.units[0])]
    wire = wire3(raw, catalog)
    wire['claims'][0].update(evidence_selector=selector, evidence_mode=mode)
    if occurrence is not None:
        wire['claims'][0]['evidence_occurrence'] = occurrence
    record = from_wire(wire)
    if occurrence is None:
        del record['claims'][0]['evidence']['occurrence']
    if expected is None:
        with pytest.raises(ValueError):
            parse(json.dumps(record), payload_for(ctx))
    else:
        assert parse(json.dumps(record), payload_for(ctx))['claims'][0]['evidence_excerpt'] == expected


def test_whole_piece_ambiguity_does_not_require_dependency_graph():
    from pro_a.whole_piece_compact import parse, render
    ctx = context('青松公司与白杨公司讨论产能。\n该公司现有产能为100台。')
    catalog = build_source_evidence_catalog(ctx)
    raw = empty_canonical()
    raw['claims'] = [canonical_claim('青松公司现有产能为100台。', catalog.units[-1])]
    assert parse(json.dumps(from_wire(wire3(raw, catalog))), payload_for(ctx)) == raw
    assert '青松公司与白杨公司' in render(payload_for(ctx))['messages'][1]['content']
    # This proves provenance/representation only, not the model's antecedent choice.
    assert set(raw) == {'source_metadata', 'claims', 'node_matches', 'node_candidates', 'relation_candidates', 'source_references'}


@pytest.mark.parametrize('claims,expected_jobs,within_budget', [(200, 30, True), (208, 31, True), (209, 32, False), (500, 68, False)])
def test_five_piece_semantic_job_budget(claims, expected_jobs, within_budget):
    from pro_a.semantic_decomposition import partition_semantic_claims
    from pro_a.workbench.source_operations import MAX_STAGE1_JOBS_PER_RUN
    from test_phase43_stage1_operator_scale import semantic_inputs
    batches = partition_semantic_claims(semantic_inputs(claims), max_input_tokens=11808)
    assert 5 + len(batches) == expected_jobs
    assert (5 + len(batches) <= MAX_STAGE1_JOBS_PER_RUN) is within_budget


@pytest.mark.parametrize('factory', [dense_fixture, mixed_fixture])
def test_gate_a_whole_piece_v3_exact_canonical(factory):
    ctx, catalog, raw = factory()
    assert expand_source_analysis_wire_v3(wire3(raw, catalog), catalog, ctx) == raw


@pytest.mark.parametrize('boundary', [8, 16])
@pytest.mark.parametrize('name', ['青松公司', '白杨公司'])
def test_gate_a_boundary_and_antecedent_are_whole_context(boundary, name):
    text = '\n'.join([name + '介绍生产情况。'] + ['这是背景材料。'] * (boundary - 1)
                     + ['该公司现有产能为100台。']
                     + (['这是后续背景材料。'] * 7 if boundary == 8 else []))
    ctx = context(text)
    catalog = build_source_evidence_catalog(ctx)
    raw = empty_canonical()
    raw['claims'] = [canonical_claim(name + '现有产能为100台。', catalog.units[boundary])]
    wire = wire3(raw, catalog)
    assert expand_source_analysis_wire_v3(wire, catalog, ctx) == raw
    assert name in ctx.piece.source_text
    assert len(catalog.units) == (16 if boundary == 8 else 17)
    from pro_a.whole_piece_compact import render
    prompt = render(payload_for(ctx))['messages'][1]['content']
    assert all(unit.exact_text in prompt for unit in catalog.units)
    assert set(wire) <= {'wire_version', 'source_metadata', 'claims'}


@pytest.mark.parametrize('factory', [dense_fixture, mixed_fixture])
def test_gate_a_native_and_permanent_identity(tmp_path, factory):
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    from stability_helpers import make_config
    cfg, db = make_config(tmp_path)
    if factory is mixed_fixture:
        ctx, catalog, raw = factory((db.add_node('示例产品甲', 'Product'), db.add_node('示例技术乙', 'Technology')))
    else:
        ctx, catalog, raw = factory()
    expanded = expand_source_analysis_wire_v3(wire3(raw, catalog), catalog, ctx)
    analyzer = Analyzer(cfg, db)
    def native(response):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(response))
        return analyzer.analyze_source('synthetic.txt', ctx.piece.source_text, 'deep', adaptive_retry_policy='forbid')
    left, right = native(raw), native(expanded)
    assert left == right
    assert left.claims
    for index, (old, new) in enumerate(zip(left.claims, right.claims)):
        def identity(claim):
            return deterministic_id('CLM', {'source_sha256': ctx.source_sha256, 'claim_index': index,
                'claim': {k: v for k, v in claim.items() if not k.startswith('origin_')}})
        assert identity(old) == identity(new)
