"""Synthetic V4 encoding qualification; no real provider or historical repair."""
import copy
import json
from dataclasses import asdict

import jsonschema
import pytest

from pro_a import output_decomposition as output, output_provider_record_v4 as v4
from pro_a import extraction_analysis_record as normalized
from pro_a.bounded_extraction import create_extraction_series, initial_extraction_plan, expand_source_analysis_wire_v3
from pro_a.constants import NODE_TYPES
from pro_a.evidence_binding import identity
from pro_a.source_analysis_wire import _TYPE_FIELDS, _NODE_VARIANTS
from lexical_record_helpers import from_canonical
from provider_record_v4_helpers import from_valid_v3
from test_source_analysis_wire import mixed_fixture


def records():
    ctx, catalog, native = mixed_fixture()
    old = from_canonical(native, catalog)
    old['evidence_acknowledgements'] = [{'evidence_ref': u.evidence_ref} for u in catalog.units]
    for family in ('node_candidates', 'source_references'):
        for obj in old[family]:
            obj['ownership_evidence_ref'] = catalog.units[0].evidence_ref
    # Explicit inactive values, including false/empty, are research data when present.
    slots = old['node_candidates'][0]['preserved_fields']
    slots['is_discrete_event'] = {'present': 'TRUE', 'value': 'FALSE'}
    slots['importance'] = {'present': 'TRUE', 'value': ''}
    slots['evidence_ref'] = {'present': 'TRUE', 'value': {'evidence_ref': catalog.units[0].evidence_ref,
        'selection_mode': 'WHOLE_UNIT', 'selector': '', 'occurrence': '1'}}
    old['claims'][0]['related_candidate_names'] = [n['canonical_name'] for n in old['node_candidates']]
    return ctx, catalog, old, from_valid_v3(old)


def result(record, ctx, catalog, *, legacy=False):
    version = output.V2_OUTPUT_SERIES_VERSION if legacy else output.OUTPUT_SERIES_VERSION
    series = create_extraction_series(ctx, catalog, 'V4_SYNTHETIC_RUN', series_version=version)
    segment = initial_extraction_plan(series).leaves[0]
    return output.record_to_result(json.dumps(record), series, segment, catalog, ctx), series, segment


def test_documented_strict_subset_and_disjoint_complete_branches():
    schema = output.record_schema()
    def visit(node):
        assert set(node) <= {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum', 'anyOf'}
        if 'anyOf' in node:
            for branch in node['anyOf']: visit(branch)
        elif node['type'] == 'object':
            assert set(node['required']) == set(node['properties']) and node['additionalProperties'] is False
            for child in node['properties'].values(): visit(child)
        elif node['type'] == 'array': visit(node['items'])
    visit(schema)
    branches = schema['properties']['node_candidates']['items']['anyOf']
    assert len(branches) == 4
    types = [set(b['properties']['primary_type']['enum']) for b in branches]
    assert set.union(*types) == set(NODE_TYPES)
    assert sum(map(len,types)) == len(NODE_TYPES)
    for branch in branches:
        primary = branch['properties']['primary_type']['enum'][0]
        expected = {'event_evidence' if f == 'evidence_ref' else f for f in _NODE_VARIANTS.get(primary,set())}
        actual = set(branch['properties']) & ((_TYPE_FIELDS-{'evidence_ref'}) | {'event_evidence'})
        assert actual == expected
    jsonschema.Draft202012Validator.check_schema(schema)


def test_v3_v4_normalized_wire_expansion_linkage_order_and_identity_parity():
    ctx, catalog, old, new = records()
    original = copy.deepcopy(new)
    jsonschema.validate(new, output.record_schema())
    left = output.normalize_record(json.dumps(old), record_version=output.V3_RECORD_VERSION)
    right = output.normalize_record(json.dumps(new))
    assert left == right and identity(left) == identity(right)
    assert new == original and old != new
    assert [n['canonical_name'] for n in right['node_candidates']] == [n['canonical_name'] for n in old['node_candidates']]
    preserved = right['node_candidates'][0]['preserved_fields']
    assert preserved['is_discrete_event'] is False and preserved['importance'] == ''
    assert preserved['evidence_ref'] == catalog.units[0].evidence_ref
    assert 'event_time' not in preserved
    a, old_series, _ = result(old,ctx,catalog,legacy=True)
    b, new_series, _ = result(new,ctx,catalog)
    assert a.wire_json == b.wire_json and a.dispositions == b.dispositions
    assert expand_source_analysis_wire_v3(json.loads(a.wire_json),catalog,ctx) == expand_source_analysis_wire_v3(json.loads(b.wire_json),catalog,ctx)
    assert old_series.series_id != new_series.series_id and a.result_sha256 != b.result_sha256
    assert b == result(new,ctx,catalog)[0]
    assert normalized.VERSION == 'normalized-extraction-analysis-record-v1'


@pytest.mark.parametrize('primary', sorted(set(NODE_TYPES) - set(_NODE_VARIANTS)))
def test_every_other_type_and_empty_preserved_arrays(primary):
    ctx,catalog,old,new = records()
    obj=new['node_candidates'][0]
    obj['primary_type']=primary
    for array in v4.PRESERVED:obj[array]=[]
    new['node_candidates']=[obj]
    new['claims'][0]['related_candidate_names']=[obj['canonical_name']]
    # Keep only the references valid for this intentionally smaller response.
    for claim in new['claims']:claim['related_candidate_names']=[obj['canonical_name']]
    ir=output.normalize_record(json.dumps(new))
    assert 'preserved_fields' not in ir['node_candidates'][0]
    assert not set(ir['node_candidates'][0]) & _TYPE_FIELDS


@pytest.mark.parametrize('mutation', ['wrong_branch','missing_active','extra_inactive','duplicate_preserved','preserved_active',
    'invalid_boolean','invalid_selector','foreign_evidence','unknown_candidate','duplicate_candidate','malformed_nested','unsupported_field',
    'wrong_preserved_type','unknown_preserved_name','none_preserved_evidence'])
def test_invalid_output_fails_closed_without_mutation(mutation):
    ctx,catalog,old,new = records()
    event=next(n for n in new['node_candidates'] if n['primary_type']=='Event')
    if mutation=='wrong_branch':event['primary_type']='Theme'
    elif mutation=='missing_active':del event['event_time']
    elif mutation=='extra_inactive':event['importance']='unrelated'
    elif mutation=='duplicate_preserved':new['node_candidates'][0]['preserved_text_fields'] *= 2
    elif mutation=='preserved_active':event['preserved_boolean_fields']=[{'field':'is_discrete_event','value':'TRUE'}]
    elif mutation=='invalid_boolean':event['is_discrete_event']=True
    elif mutation=='invalid_selector':event['event_evidence']['selector']='unsupported selector'
    elif mutation=='foreign_evidence':event['event_evidence']['evidence_ref']='EV_FOREIGN'
    elif mutation=='unknown_candidate':new['claims'][0]['related_candidate_names']=['ABSENT_CANDIDATE']
    elif mutation=='duplicate_candidate':new['node_candidates'].append(copy.deepcopy(new['node_candidates'][0]))
    elif mutation=='malformed_nested':event['event_evidence']=[]
    elif mutation=='unsupported_field':event['extra']='unsupported'
    elif mutation=='wrong_preserved_type':new['node_candidates'][0]['preserved_text_fields'][0]['value']=False
    elif mutation=='unknown_preserved_name':new['node_candidates'][0]['preserved_text_fields'][0]['field']='invented'
    else:new['node_candidates'][0]['preserved_evidence_fields'][0]['value']['selection_mode']='NONE'
    original=copy.deepcopy(new)
    with pytest.raises(ValueError):result(new,ctx,catalog)
    assert new==original


def test_historical_v3_is_not_v4_and_invalid_v3_is_never_repaired():
    ctx,catalog,old,new=records()
    assert output.normalize_record(json.dumps(old),record_version=output.V3_RECORD_VERSION)
    with pytest.raises(ValueError):output.normalize_record(json.dumps(old))
    with pytest.raises(ValueError):output.normalize_record(json.dumps(new),record_version=output.V3_RECORD_VERSION)
    old['node_candidates'][0]['cross_source_or_node_value']='TRUE'
    original=copy.deepcopy(old)
    with pytest.raises(ValueError,match='NONDEFAULT_INACTIVE_VARIANT'):
        output.normalize_record(json.dumps(old),record_version=output.V3_RECORD_VERSION)
    with pytest.raises(ValueError):output.normalize_record(json.dumps(old))
    assert old==original


def test_execution_versions_and_frozen_capacity_are_distinct():
    old=output.contract(binding_version=output.V3_BINDING_VERSION);new=output.contract()
    for name in ('binding_version','provider_version','provider_record_version','tool_schema_version','provider_encoding_contract_version','series','batch'):
        assert new[name]!=old[name]
    assert new['research_semantic_contract']==old['research_semantic_contract']
    assert new['budget']==old['budget'] and new['max_output_tokens']==old['max_output_tokens']==24000
    assert new['budget']['max_cumulative_output_tokens']==384000 and new['budget']['initial_evidence_refs']==16
    assert output.record_version_for_series(old['series'])==output.V3_RECORD_VERSION
    assert output.record_version_for_series(new['series'])==v4.VERSION
    from pro_a.workbench.retry_compatibility import _CLOUD_EXECUTION_SURFACE
    assert 'output_provider_record_v4.py' in _CLOUD_EXECUTION_SURFACE


def test_clean_run_v4_transport_ownership_aggregation_and_boundaries(tmp_path, monkeypatch):
    from test_bounded_only_resume import topology, resume
    from series_binding_helpers import Transport, synthetic_providers, rows, request_parts
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))
    value = topology(tmp_path, monkeypatch, counts=(17,), accepted_retry=False)
    transport = Transport()
    with synthetic_providers(value, transport) as providers:
        completed = resume(value, providers, ceiling=2)
        assert completed['bounded_complete'] and len(transport.calls) == 2
        assert providers['SEMANTIC_DECOMPOSITION'].call_count == 0
    for request in transport.calls:
        target, _ = request_parts(request)
        assert target['provider_record_version'] == v4.VERSION
        assert target['binding_version'] == output.BINDING_VERSION
        assert request['max_tokens'] == 24000
        assert request['tools'][0]['function']['strict'] is True
        assert request['tools'][0]['function']['parameters'] == output.record_schema()
    assert len(rows(value, 'bounded_extraction_segment_results')) == 2
    assert len(rows(value, 'bounded_extraction_series_results')) == 1
    assert not rows(value, 'source_processing_jobs')
    assert value['config'].knowledge_db.read_bytes() == value['production_before']


@pytest.mark.parametrize('mode', ['server_rejects_schema', 'old_v3_response'])
def test_clean_run_stops_without_fallback_on_schema_or_encoding_rejection(tmp_path, monkeypatch, mode):
    from test_bounded_only_resume import topology, resume
    from series_binding_helpers import Transport, synthetic_providers, rows, request_parts, response_content, batch_record
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))
    class Rejected(Transport):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            if mode == 'server_rejects_schema':
                response.status_code = 400
            else:
                target, source = request_parts(kwargs['json'])
                target['provider_record_version'] = output.V3_RECORD_VERSION
                old = batch_record(json.loads(response_content(target, source)), target)
                response.value['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = json.dumps(old)
            return response
    value = topology(tmp_path, monkeypatch, counts=(17,), accepted_retry=False)
    transport = Rejected()
    with synthetic_providers(value, transport) as providers:
        stopped = resume(value, providers, ceiling=2)
        assert stopped['status'] == 'STOP_ON_FIRST_NEW_FAILURE' and len(transport.calls) == 1
        assert providers['SEMANTIC_DECOMPOSITION'].call_count == 0
    assert not rows(value, 'bounded_extraction_segment_results')
    assert not rows(value, 'bounded_extraction_series_results')
    assert value['config'].knowledge_db.read_bytes() == value['production_before']


@pytest.mark.parametrize('primary', ['Event', 'Theme', 'ResearchQuestion', 'Entity'])
def test_all_legal_inactive_fields_preserve_explicit_presence(primary):
    ctx, catalog, old, _ = records()
    node = next(n for n in old['node_candidates'] if n['primary_type'] == primary)
    active = _NODE_VARIANTS.get(primary, set())
    for field in _TYPE_FIELDS - active:
        slot = node['preserved_fields'][field]
        slot['present'] = 'TRUE'
        if field == 'evidence_ref':
            slot['value'] = {'evidence_ref':catalog.units[0].evidence_ref, 'selection_mode':'WHOLE_UNIT', 'selector':'', 'occurrence':'1'}
    new = from_valid_v3(old)
    left = output.normalize_record(json.dumps(old), record_version=output.V3_RECORD_VERSION)
    right = output.normalize_record(json.dumps(new))
    assert left == right
    projected = next(n for n in right['node_candidates'] if n['primary_type'] == primary)
    assert set(projected['preserved_fields']) >= _TYPE_FIELDS - active
    assert result(old, ctx, catalog, legacy=True)[0].wire_json == result(new, ctx, catalog)[0].wire_json
