"""Synthetic compiler/transport/durable acceptance qualification; no live providers."""
import copy
import json
from types import SimpleNamespace

import jsonschema
import pytest

from pro_a import output_decomposition as output, output_provider_record_v4 as v4, output_provider_record_v5 as v5
from pro_a import node_candidate_intent as nodes
from pro_a.bounded_extraction import create_extraction_series, initial_extraction_plan, expand_source_analysis_wire_v3
from pro_a.source_analysis_wire import _NODE_VARIANTS, _TYPE_FIELDS
from pro_a.constants import NODE_TYPES
from pro_a.evidence_binding import identity
from node_intent_helpers import from_valid_v4
from provider_record_v4_helpers import from_valid_v3
from test_provider_record_v4 import records


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))


def result(record, ctx, catalog, *, intent=True):
    version = output.INTENT_OUTPUT_SERIES_VERSION if intent else output.OUTPUT_SERIES_VERSION
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_INTENT_RUN', series_version=version)
    segment = initial_extraction_plan(series).leaves[0]
    return output.record_to_result(json.dumps(record), series, segment, catalog, ctx), series, segment


def test_documented_strict_subset_no_candidate_branches_and_explicit_selection():
    schema = v5.record_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    def visit(node):
        assert set(node) <= {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum'}
        if node['type'] == 'object':
            assert set(node['required']) == set(node['properties']) and node['additionalProperties'] is False
            for child in node['properties'].values(): visit(child)
        elif node['type'] == 'array': visit(node['items'])
    visit(schema)
    assert output.contract()['provider_record_version'] == v4.VERSION
    explicit = output.contract(binding_version=output.INTENT_BINDING_VERSION)
    assert explicit['provider_record_version'] == v5.VERSION and explicit['node_candidate_intent_version'] == nodes.VERSION
    assert explicit['research_semantic_contract'] == output.contract()['research_semantic_contract']
    assert explicit['budget'] == output.contract()['budget'] and explicit['max_output_tokens'] == 24000
    from pro_a.workbench.retry_compatibility import _CLOUD_EXECUTION_SURFACE
    assert {'node_candidate_intent.py', 'output_provider_record_v5.py'} <= _CLOUD_EXECUTION_SURFACE.keys()


@pytest.mark.parametrize('primary', sorted(NODE_TYPES))
def test_all_node_types_lossless_normalized_wire_evidence_and_order_parity(primary):
    ctx, catalog, old, _ = records()
    source = next((n for n in old['node_candidates'] if n['primary_type'] == primary), old['node_candidates'][0])
    node = copy.deepcopy(source); node['primary_type'] = primary
    active = _NODE_VARIANTS.get(primary, set())
    for field in _TYPE_FIELDS - active:
        slot = node['preserved_fields'][field]; slot['present'] = 'TRUE'
        if field == 'evidence_ref':
            slot['value'] = {'evidence_ref': catalog.units[0].evidence_ref, 'selection_mode': 'WHOLE_UNIT', 'selector': '', 'occurrence': '1'}
    old['node_candidates'] = [node]
    for claim in old['claims']: claim['related_candidate_names'] = [node['canonical_name']]
    four = from_valid_v3(old); five = from_valid_v4(four); original = copy.deepcopy(five)
    jsonschema.validate(five, v5.record_schema())
    left = v4.normalize_record(json.dumps(four)); right = v5.normalize_record(json.dumps(five))
    assert left == right and identity(left) == identity(right) and five == original
    preserved = right['node_candidates'][0].get('preserved_fields', {})
    assert set(preserved) >= _TYPE_FIELDS - active
    a, _, _ = result(four, ctx, catalog, intent=False); b, _, _ = result(five, ctx, catalog)
    assert a.wire_json == b.wire_json and a.dispositions == b.dispositions
    assert expand_source_analysis_wire_v3(json.loads(a.wire_json), catalog, ctx) == expand_source_analysis_wire_v3(json.loads(b.wire_json), catalog, ctx)
    assert a.result_sha256 != b.result_sha256  # Different frozen execution, identical research facts.


def test_mixed_node_order_explicit_false_empty_subspan_and_downstream_analyzer(tmp_path):
    from test_source_analysis_wire import make_config
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    ctx, catalog, _, four = records()
    selection = four['node_candidates'][0]['preserved_evidence_fields'][0]['value']
    selection.update(selection_mode='RAW_SUBSPAN', selector=catalog.units[0].exact_text[:5], occurrence='1')
    five = from_valid_v4(four)
    a, _, _ = result(four, ctx, catalog, intent=False); b, _, _ = result(five, ctx, catalog)
    assert a.wire_json == b.wire_json and a.dispositions == b.dispositions
    ir = v5.normalize_record(json.dumps(five))
    preserved = ir['node_candidates'][0]['preserved_fields']
    assert preserved['is_discrete_event'] is False and preserved['importance'] == ''
    assert preserved['evidence_mode'] == 'RAW_SUBSPAN' and preserved['evidence_selector'] == selection['selector']
    assert [n['canonical_name'] for n in ir['node_candidates']] == [n['canonical_name'] for n in four['node_candidates']]
    cfg, db = make_config(tmp_path)
    db.add_node('示例产品甲', 'Product', node_id='NODE_A')
    db.add_node('示例技术乙', 'Technology', node_id='NODE_B')
    analyzer = Analyzer(cfg, db)
    def analyze(wire):
        expanded = expand_source_analysis_wire_v3(json.loads(wire), catalog, ctx)
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(expanded))
        return analyzer.analyze_source('synthetic.txt', ctx.piece.source_text, 'deep', adaptive_retry_policy='forbid')
    left, right = analyze(a.wire_json), analyze(b.wire_json)
    assert left == right and all(c['evidence_validated'] for c in right.claims)
    assert len(right.claims) == len(four['claims'])
    assert len(right.node_candidates) == len(four['node_candidates'])
    assert len(right.relation_candidates) == len(four['relation_candidates'])
    def ids(analysis):
        return [deterministic_id('CLM', {'source_sha256': ctx.source_sha256, 'claim_index': i,
            'claim': {k: v for k, v in c.items() if not k.startswith('origin_')}}) for i, c in enumerate(analysis.claims)]
    assert ids(left) == ids(right)


@pytest.mark.parametrize('mutation', ['missing_active', 'missing_owner', 'duplicate_property', 'unknown_property',
    'boolean_type', 'wrong_property_family', 'unknown_node_type', 'duplicate_candidate', 'unknown_candidate',
    'foreign_owner', 'foreign_evidence', 'invalid_nested_evidence', 'none_evidence', 'invalid_occurrence',
    'invalid_selector', 'missing_ack', 'duplicate_ack', 'foreign_ack', 'extra_field', 'missing_claim_evidence'])
def test_rejection_is_explicit_without_mutation_or_loss(mutation):
    ctx, catalog, _, four = records(); five = from_valid_v4(four)
    event = next(n for n in five['node_candidates'] if n['primary_type'] == 'Event')
    evidence = event['evidence_properties'][0]['value']
    if mutation == 'missing_active': event['text_properties'] = []
    elif mutation == 'missing_owner': del event['ownership_evidence_ref']
    elif mutation == 'duplicate_property': event['boolean_properties'] *= 2
    elif mutation == 'unknown_property': event['text_properties'].append({'field': 'invented', 'value': 'x'})
    elif mutation == 'boolean_type': event['boolean_properties'][0]['value'] = False
    elif mutation == 'wrong_property_family': event['text_properties'].append({'field': 'is_discrete_event', 'value': 'FALSE'})
    elif mutation == 'unknown_node_type': event['primary_type'] = 'Invented'
    elif mutation == 'duplicate_candidate': five['node_candidates'].append(copy.deepcopy(five['node_candidates'][0]))
    elif mutation == 'unknown_candidate': five['claims'][0]['related_candidate_names'] = ['ABSENT']
    elif mutation == 'foreign_owner': event['ownership_evidence_ref'] = 'EV_FOREIGN'
    elif mutation == 'foreign_evidence': evidence['evidence_ref'] = 'EV_FOREIGN'
    elif mutation == 'invalid_nested_evidence': event['evidence_properties'][0]['value'] = []
    elif mutation == 'none_evidence': evidence['selection_mode'] = 'NONE'
    elif mutation == 'invalid_occurrence': evidence['occurrence'] = '0'
    elif mutation == 'invalid_selector': evidence['selector'] = 'unsupported selector'
    elif mutation == 'missing_ack': five['evidence_acknowledgements'].pop()
    elif mutation == 'duplicate_ack': five['evidence_acknowledgements'].append(five['evidence_acknowledgements'][0])
    elif mutation == 'foreign_ack': five['evidence_acknowledgements'][0]['evidence_ref'] = 'EV_FOREIGN'
    elif mutation == 'extra_field': event['invented'] = 'unsupported'
    else: del five['claims'][0]['evidence']
    before = copy.deepcopy(five)
    with pytest.raises(ValueError): result(five, ctx, catalog)
    assert five == before


def test_missing_semantic_fields_and_duplicate_properties_have_specific_errors():
    _, _, _, four = records(); five = from_valid_v4(four)
    event = next(n for n in five['node_candidates'] if n['primary_type'] == 'Event')
    event['text_properties'] = []
    with pytest.raises(ValueError, match='MISSING_NODE_INTENT_PROPERTY:event_time'): nodes.compile_candidate(event)
    event['boolean_properties'] *= 2
    with pytest.raises(ValueError, match='DUPLICATE_NODE_INTENT_PROPERTY:is_discrete_event'): nodes.compile_candidate(event)


def test_old_and_new_raw_are_never_shape_routed_or_reinterpreted():
    ctx, catalog, three, four = records(); five = from_valid_v4(four)
    for record, version in ((three, output.V3_RECORD_VERSION), (four, v4.VERSION), (five, v5.VERSION)):
        assert output.normalize_record(json.dumps(record), record_version=version)
        for other in {output.V3_RECORD_VERSION, v4.VERSION, v5.VERSION} - {version}:
            with pytest.raises(ValueError): output.normalize_record(json.dumps(record), record_version=other)
    _, old_series, old_segment = result(four, ctx, catalog, intent=False)
    with pytest.raises(ValueError, match='PROVIDER_RECORD_SERIES_VERSION_MISMATCH'):
        output.record_to_result(json.dumps(five), old_series, old_segment, catalog, ctx, record_version=v5.VERSION)
    assert output.record_version_for_series(old_series.series_version) == v4.VERSION
    _, new_series, new_segment = result(five, ctx, catalog)
    for old_version in (output.legacy.V1, output.legacy.RECORD_VERSION, output.V3_RECORD_VERSION, v4.VERSION):
        with pytest.raises(ValueError, match='PROVIDER_RECORD_SERIES_VERSION_MISMATCH'):
            output.record_to_result('{}', new_series, new_segment, catalog, ctx, record_version=old_version)


def test_fake_provider_to_existing_durable_segment_ledger(tmp_path, monkeypatch):
    from pro_a.config import LLMConfig
    from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
    from pro_a.workbench.bounded_extraction_persistence import prepare_bounded_extraction_persistence
    from test_phase43_stage6_lifecycle import _schema11
    from series_binding_helpers import ToolResponse
    ctx, catalog, _, four = records(); five = from_valid_v4(four)
    pure, series, segment = result(five, ctx, catalog)
    value, _ = _schema11(tmp_path); config = value['config']; prepare_bounded_extraction_persistence(config)
    production = config.knowledge_db.read_bytes(); ledger = BoundedExtractionStore(config); ledger.create(series)
    monkeypatch.setenv('PRO_A_INTENT_SYNTHETIC_KEY', 'synthetic-only')
    calls = []
    def transport(endpoint, **kwargs):
        calls.append(copy.deepcopy(kwargs['json']))
        assert kwargs['json']['tools'][0]['function']['parameters'] == v5.record_schema()
        assert kwargs['allow_redirects'] is False
        return ToolResponse(json.dumps(five))
    provider = output.OutputBatchProvider(LLMConfig(enabled=True, api_key_env='PRO_A_INTENT_SYNTHETIC_KEY',
        model='deepseek-flash', max_retries=0, max_output_tokens=24000), transport=transport, binding_version=output.INTENT_BINDING_VERSION)
    payload = output.segment_payload({'native': {'scoped_node_catalog': []}}, ctx, catalog, series, segment)
    fence = ledger.claim_segment(segment.segment_id, 'intent_test', lease_seconds=600)
    attempt = ledger.reserve_attempt(segment.segment_id, 'intent_test', fence, attempt_number=1,
        payload_sha256=identity(payload), configuration_sha256=identity(provider.configuration()))
    assert json.loads(attempt['request_json'])['provider_record_version'] == v5.VERSION
    assert ledger.record_dispatch(attempt['attempt_id'], 'intent_test', fence)
    raw = provider.invoke(payload)
    ledger.record_outcome(attempt['attempt_id'], 'intent_test', fence, raw.content,
        http_status=raw.http_status, finish_reason=raw.finish_reason, input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens, total_tokens=raw.total_tokens, cached_input_tokens=raw.cached_input_tokens)
    accepted = ledger.accept_result(attempt['attempt_id'], 'intent_test', fence, catalog, ctx)
    assert accepted['result_sha256'] == pure.result_sha256 and len(calls) == 1
    ledger.close_segment(segment.segment_id, 'intent_test', fence)
    assert BoundedExtractionStore(config).read(series.series_id)[2]['state'] == 'OPEN'
    with ledger._connection() as connection:
        assert connection.execute('SELECT count(*) FROM source_processing_jobs').fetchone()[0] == 0
        assert connection.execute('SELECT state FROM bounded_extraction_segments').fetchone()[0] == 'SUCCEEDED_COMPLETE'
    assert config.knowledge_db.read_bytes() == production


def test_acknowledgement_does_not_require_claims_or_invent_relations():
    ctx, catalog, _, four = records(); five = from_valid_v4(four)
    for family in ('claims', 'node_candidates', 'node_matches', 'relation_candidates'):
        five[family] = []
    accepted, _, _ = result(five, ctx, catalog)
    assert all(d.disposition == 'NO_INDEPENDENT_CLAIM' for d in accepted.dispositions)
    wire = json.loads(accepted.wire_json)
    assert not wire['claims'] and not wire['relation_candidates']


@pytest.mark.parametrize('version,expected', [
    (output.legacy.V1, '2ab5a19cc47dabd4f7999b58cd8b5c5d4a0b3f3523f2df4d389af7e030f24454'),
    (output.legacy.RECORD_VERSION, '2ab5a19cc47dabd4f7999b58cd8b5c5d4a0b3f3523f2df4d389af7e030f24454'),
    (output.V3_RECORD_VERSION, 'e0b9f904964db6681b2336058324e6501cd7b24c2feed683c2d51e7ddb84a668'),
    (v4.VERSION, '8ef4740b4f86af31b66af05eb3962f881a3cf3bc34c688bc1f03f9d5e661f5b6'),
])
def test_synthetic_historical_result_identity_from_released_baseline(version, expected):
    # Existing result identities captured from actual release 26c3be797cbd502a6773332e014ae8a19473a349.
    from lexical_record_helpers import claim_linkages
    ctx, catalog, three, four = records()
    record = copy.deepcopy(four if version == v4.VERSION else three)
    series_version = output.OUTPUT_SERIES_VERSION if version == v4.VERSION else output.V2_OUTPUT_SERIES_VERSION
    if version in (output.legacy.V1, output.legacy.RECORD_VERSION):
        series_version = output.LEGACY_OUTPUT_SERIES_VERSION
        record.pop('evidence_acknowledgements')
        record['dispositions'] = claim_linkages(record, [u.evidence_ref for u in catalog.units])
        if version == output.legacy.V1:
            record['dispositions'] = [{'evidence_ref': d['evidence_ref'],
                'disposition': 'CLAIMED' if d['claim_refs'] else 'NO_INDEPENDENT_CLAIM'} for d in record['dispositions']]
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_HISTORY_PARITY', series_version=series_version)
    segment = initial_extraction_plan(series).leaves[0]
    accepted = output.record_to_result(json.dumps(record), series, segment, catalog, ctx, record_version=version)
    assert accepted.result_sha256 == expected


@pytest.mark.parametrize('binding', [output.LEGACY_BINDING_VERSION, output.V3_BINDING_VERSION, output.BINDING_VERSION])
def test_historical_schema_and_prompt_identities_are_frozen(binding):
    selected = output.contract(binding_version=binding)
    expected = ('bfed5e705202ad9c39947421bb8f9481a282b69e9330ff7663afeea10ba7b2e4',
                '0918be280f4f7f7ddd03f2f6acf55b673f3aee9bf2a40e999f94dbfb8b6bf9e1') if binding == output.BINDING_VERSION else (
                'c859e3b7a8b9023da1598d651c7e337b1c6f8721645242388996dc33892e9e77',
                '4b0eacf536ebff2b2cc7cc1a48251bd58d57b94ec4a18d028acbbe8bf41365b1')
    assert (selected['tool_schema_sha256'], selected['system_prompt_sha256']) == expected
