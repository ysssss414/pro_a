"""Complete lexical representation and unchanged canonical/native authority."""
import copy
import json
from types import SimpleNamespace

import pytest
from pro_a import constants as c
from pro_a import source_analysis_provider_record as p
from pro_a.bounded_extraction import expand_source_analysis_wire_v3
from pro_a.evidence_binding import EVIDENCE_MODES, resolve_evidence_binding_v2
from pro_a.source_analysis_wire import (build_source_evidence_catalog, _TYPE_FIELDS, _NODE_VARIANTS,
    NODE_MATCH_ROLES, SOURCE_REFERENCE_RELATION_TYPES)
from lexical_record_helpers import from_canonical, from_wire
from test_source_analysis_wire import dense_fixture, mixed_fixture, context, empty_canonical, canonical_claim, normal_node
from test_whole_piece_compact import wire3


@pytest.mark.parametrize('factory', [dense_fixture, mixed_fixture])
def test_exact_canonical_and_deterministic(factory):
    ctx, catalog, raw = factory()
    record = from_canonical(raw, catalog)
    before = json.dumps(record, ensure_ascii=False)
    p.validate_provider_record(record)
    first = p.provider_record_to_wire_v3(record)
    second = p.provider_record_to_wire_v3(record)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert json.dumps(record, ensure_ascii=False) == before
    assert expand_source_analysis_wire_v3(first, catalog, ctx) == raw


@pytest.mark.parametrize('node_type', c.NODE_TYPES)
def test_every_node_type_and_preserved_fields(node_type):
    ctx, catalog, raw = mixed_fixture()
    # Carry all variant semantics in canonical; inactive ones must survive via
    # explicit preserved slots, never via nondefault inactive primary slots.
    candidate = normal_node('Synthetic Candidate')
    candidate.update(primary_type=node_type, is_discrete_event=True, event_time='2026-01-01',
        evidence_excerpt=catalog.units[1].exact_text, long_term_research_value=True,
        cross_source_or_node_value=True, question='Synthetic question?', importance='Synthetic importance',
        what_would_change_my_mind='Synthetic contrary evidence',
        candidate_kind='research_question' if node_type == 'ResearchQuestion' else 'normal')
    raw['node_candidates'] = [candidate]
    for claim in raw['claims']:
        claim['related_candidate_names'] = []
    record = from_canonical(raw, catalog)
    assert set(record['node_candidates'][0]['preserved_fields']) == _TYPE_FIELDS
    assert expand_source_analysis_wire_v3(p.provider_record_to_wire_v3(record), catalog, ctx) == raw


@pytest.mark.parametrize('factory', [dense_fixture, mixed_fixture])
def test_native_accept_reject_and_permanent_identity(tmp_path, factory):
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    from stability_helpers import make_config
    cfg, db = make_config(tmp_path)
    ctx, catalog, raw = factory((db.add_node('示例产品甲', 'Product'), db.add_node('示例技术乙', 'Technology'))) if factory is mixed_fixture else factory()
    expanded = expand_source_analysis_wire_v3(p.provider_record_to_wire_v3(from_canonical(raw, catalog)), catalog, ctx)
    analyzer = Analyzer(cfg, db)
    def native(value):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *args: copy.deepcopy(value))
        return analyzer.analyze_source('synthetic.txt', ctx.piece.source_text, 'deep', adaptive_retry_policy='forbid')
    left, right = native(raw), native(expanded)
    assert left == right and left.claims
    for index, (old, new) in enumerate(zip(left.claims, right.claims)):
        def identity(claim):
            return deterministic_id('CLM', {'source_sha256': ctx.source_sha256, 'claim_index': index,
                'claim': {k: v for k, v in claim.items() if not k.startswith('origin_')}})
        assert identity(old) == identity(new)


@pytest.mark.parametrize('fn,value', [(p.boolean, v) for v in [True, False, 'true', 'false', 'yes', '1', '0', '', ' TRUE', 'FALSE ']] +
    [(p.confidence, v) for v in ['', ' .8', '0.8 ', 'NaN', 'Infinity', '-0.1', '1.1', 'one', '1e-1', '.8', '01', True, .8,
        '1.00000000000000000001', '0.' + '9' * 50, '0.' + '0' * 400 + '1']] +
    [(p.occurrence, v) for v in ['', 0, -1, 1.0, True, '0', '-1', '1.0', '01', ' 1', '1 ', '1\n', 'one', '1e1', '１']])
def test_negative_lexical_matrix(fn, value):
    with pytest.raises(ValueError):
        fn(value)


@pytest.mark.parametrize('fn,value,expected', [(p.boolean, 'TRUE', True), (p.boolean, 'FALSE', False),
    (p.confidence, '0', 0), (p.confidence, '0.8', .8), (p.confidence, '1', 1),
    (p.occurrence, '1', 1), (p.occurrence, '2', 2)])
def test_valid_lexical(fn, value, expected):
    assert fn(value) == expected and type(fn(value)) is type(expected)


def selection_record(family, mode, selector, occurrence):
    ctx = context('[[PARA:1]]capacity capacity ＡＢＣ', ('NODE_A',))
    catalog = build_source_evidence_catalog(ctx)
    raw = empty_canonical()
    raw['claims'] = [canonical_claim('Synthetic measurement.', catalog.units[0])]
    raw['node_matches'] = [{'node_id': 'NODE_A', 'role': 'primary', 'confidence': .8, 'reason': '', 'evidence_excerpt': catalog.units[0].exact_text}]
    node = normal_node()
    node.update(primary_type='Event' if family == 'event' else 'Entity', is_discrete_event=True,
                event_time='2026-01-01', evidence_excerpt=catalog.units[0].exact_text)
    raw['node_candidates'] = [node]
    record = from_canonical(raw, catalog)
    if family == 'event':
        target = record['node_candidates'][0]['event_evidence']
    elif family == 'preserved':
        target = record['node_candidates'][0]['preserved_fields']['evidence_ref']['value']
    else:
        target = record[family][0]['evidence']
    target.update(selection_mode=mode, selector=selector, occurrence=occurrence)
    return ctx, catalog, record, target


@pytest.mark.parametrize('family', ['claims', 'node_matches', 'event', 'preserved'])
@pytest.mark.parametrize('mode,selector,occurrence,valid', [('WHOLE_UNIT', '', '1', True),
    ('RAW_SUBSPAN', 'capacity', '1', True), ('RAW_SUBSPAN', 'capacity', '2', True),
    ('RAW_SUBSPAN', 'ＡＢＣ', '1', True), ('NORMALIZED_SUBSPAN', 'ABC', '1', True),
    ('RAW_SUBSPAN', 'capacity', '0', False), ('RAW_SUBSPAN', 'capacity', '-1', False),
    ('RAW_SUBSPAN', 'capacity', '1.0', False), ('RAW_SUBSPAN', 'capacity', '3', False),
    ('RAW_SUBSPAN', '', '1', False), ('RAW_SUBSPAN', 'ABC', '1', False),
    ('WHOLE_UNIT', 'capacity', '1', False), ('WHOLE_UNIT', '', '2', False), ('NONE', '', '1', False)])
def test_evidence_all_families(family, mode, selector, occurrence, valid):
    ctx, catalog, record, target = selection_record(family, mode, selector, occurrence)
    if valid:
        wire = p.provider_record_to_wire_v3(record)
        bound = resolve_evidence_binding_v2(p.selection(target), catalog, ctx)
        if selector == 'capacity':
            assert bound.source_start == (ctx.piece.source_text.index(selector) if occurrence == '1' else ctx.piece.source_text.rindex(selector))
        expand_source_analysis_wire_v3(wire, catalog, ctx)
    else:
        with pytest.raises(ValueError):
            expand_source_analysis_wire_v3(p.provider_record_to_wire_v3(record), catalog, ctx)


@pytest.mark.parametrize('family', ['claims', 'node_matches', 'event', 'preserved'])
@pytest.mark.parametrize('change', ['foreign', 'missing_occurrence', 'boolean_occurrence', 'wrong_bool'])
def test_run9_equivalent_and_foreign_fail(family, change):
    ctx, catalog, record, target = selection_record(family, 'RAW_SUBSPAN', 'capacity', '1')
    if change == 'foreign':
        target['evidence_ref'] = 'EV_FOREIGN'
    elif change == 'missing_occurrence':
        del target['occurrence']
    elif change == 'boolean_occurrence':
        target['occurrence'] = True
    else:
        record['node_candidates'][0]['independent_research_value'] = 'yes'
    with pytest.raises(ValueError):
        expand_source_analysis_wire_v3(p.provider_record_to_wire_v3(record), catalog, ctx)


@pytest.mark.parametrize('field', sorted(_TYPE_FIELDS))
@pytest.mark.parametrize('where', ['inactive', 'absent_preserved'])
def test_no_silent_discard(field, where):
    ctx, catalog, raw = mixed_fixture()
    record = from_canonical(raw, catalog)
    obj = record['node_candidates'][0]
    value = {'evidence_ref': catalog.units[0].evidence_ref, 'selection_mode': 'WHOLE_UNIT', 'selector': '', 'occurrence': '1'} if field == 'evidence_ref' else 'TRUE' if field in p._BOOL_FIELDS else 'Not default'
    if where == 'inactive':
        obj['event_evidence' if field == 'evidence_ref' else field] = value
    else:
        obj['preserved_fields'][field]['value'] = value
    with pytest.raises(ValueError):
        p.validate_provider_record(record)


def paths(value, schema, path=()):
    if schema['type'] == 'object':
        for key, child in schema['properties'].items():
            yield path, key
            yield from paths(value[key], child, path + (key,))
    elif schema['type'] == 'array':
        for index, child in enumerate(value):
            yield from paths(child, schema['items'], path + (index,))


def sample():
    _, catalog, raw = mixed_fixture()
    return from_canonical(raw, catalog)


@pytest.mark.parametrize('path,key', list(paths(sample(), p.record_schema())))
def test_every_required_field(path, key):
    record = sample()
    target = record
    for item in path:
        target = target[item]
    del target[key]
    with pytest.raises(ValueError, match='SHAPE'):
        p.validate_provider_record(record)


@pytest.mark.parametrize('change', ['extra_root', 'extra_nested', 'enum', 'primitive', 'object', 'array', 'claim_limit', 'candidate_limit'])
def test_shape_and_limits(change):
    record = sample()
    if change == 'extra_root': record['wire'] = {}
    elif change == 'extra_nested': record['claims'][0]['offset'] = '1'
    elif change == 'enum': record['node_matches'][0]['role'] = 'supplier'
    elif change == 'primitive': record['claims'][0]['confidence'] = .8
    elif change == 'object': record['claims'][0]['evidence'] = []
    elif change == 'array': record['claims'] = {}
    else:
        family = 'claims' if change == 'claim_limit' else 'node_candidates'
        record[family] = [record[family][0]] * 101
    with pytest.raises(ValueError): p.validate_provider_record(record)


def test_schema_profile_and_enum_parity():
    schema = p.record_schema()
    def inspect(node):
        assert node['type'] in ('string', 'object', 'array')
        assert not set(node) - {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum'}
        if node['type'] == 'object':
            assert node['additionalProperties'] is False and set(node['required']) == set(node['properties'])
            for child in node['properties'].values(): inspect(child)
        if node['type'] == 'array': inspect(node['items'])
    inspect(schema)
    root = schema['properties']
    for group, field, values in [('claims', 'nature', c.CLAIM_NATURES), ('claims', 'status', c.CLAIM_STATUSES),
        ('claims', 'novelty_level', c.NOVELTY_LEVELS), ('node_candidates', 'primary_type', c.NODE_TYPES),
        ('node_candidates', 'independent_research_value', p.LEXICAL_BOOLEANS), ('node_matches', 'role', NODE_MATCH_ROLES),
        ('relation_candidates', 'relation_type', set(c.RELATION_TYPES)-{'part_of'}),
        ('source_references', 'relation_type', SOURCE_REFERENCE_RELATION_TYPES)]:
        assert set(root[group]['items']['properties'][field]['enum']) == set(values)
    for field, values in [('source_rank', c.SOURCE_RANKS), ('source_origin_type', c.SOURCE_ORIGIN_TYPES)]:
        assert set(root['source_metadata']['properties'][field]['enum']) == set(values)
    assert set(p.selection_schema()['properties']['selection_mode']['enum']) == set(EVIDENCE_MODES)
    assert set(p.selection_schema(optional=True)['properties']['selection_mode']['enum']) == set(EVIDENCE_MODES) | {'NONE'}
