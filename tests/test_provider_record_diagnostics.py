import copy
import json
import pytest
from pro_a import output_provider_record_v4 as v4
from pro_a.provider_record_diagnostics import diagnose_shape
from test_provider_record_v4 import records


def test_multiple_missing_ownership_fields_are_located_without_exposing_values():
    _, _, _, record = records()
    plain = record['node_candidates'][0]
    for array in v4.PRESERVED: plain[array] = []
    record['node_candidates'] = [dict(copy.deepcopy(plain), canonical_name='PRIVATE_SENTINEL_'+str(i)) for i in range(12)]
    bad = [2, 3, 4, 5, 7, 8, 9, 10, 11]
    for i in bad: del record['node_candidates'][i]['ownership_evidence_ref']
    before = copy.deepcopy(record); errors = diagnose_shape(record, v4.record_schema())
    assert [e['path'] for e in errors] == [['node_candidates', i] for i in bad]
    assert all(e['causes'] == [{'path': ['node_candidates', i], 'reason': 'required',
        'missing_fields': ['ownership_evidence_ref']}] for e, i in zip(errors, bad))
    assert 'PRIVATE_SENTINEL' not in json.dumps(errors) and record == before
    with pytest.raises(ValueError, match='INVALID_PROVIDER_VARIANT_BRANCH'): v4.normalize_record(json.dumps(record))


@pytest.mark.parametrize('kind', ['extra', 'type', 'enum', 'nested'])
def test_shape_reasons_nested_paths_and_redaction(kind):
    _, _, _, record = records(); node = record['node_candidates'][0]
    if kind == 'extra': node['PRIVATE_FIELD_SENTINEL'] = 'PRIVATE_VALUE_SENTINEL'
    elif kind == 'type': node['aliases'] = 'PRIVATE_VALUE_SENTINEL'
    elif kind == 'enum': node['independent_research_value'] = 'PRIVATE_VALUE_SENTINEL'
    else: node['preserved_evidence_fields'][0]['value']['occurrence'] = False
    errors = diagnose_shape(record, v4.record_schema())
    assert errors and 'PRIVATE_' not in json.dumps(errors)
    causes = errors[0]['causes']
    assert causes[0]['reason'] == {'extra': 'additionalProperties', 'type': 'type', 'enum': 'enum', 'nested': 'type'}[kind]
    if kind == 'nested': assert causes[0]['path'][-4:] == ['preserved_evidence_fields', 0, 'value', 'occurrence']


def test_legal_record_passes_both_validators():
    _, _, _, record = records()
    assert diagnose_shape(record, v4.record_schema()) == []
    assert v4.normalize_record(json.dumps(record))
