"""Test-only inverse; production never repairs Wire/provider responses."""
import copy
import json
from decimal import Decimal

from pro_a.source_analysis_provider_record import NONE_SELECTION, _inactive
from pro_a.source_analysis_wire import _TYPE_FIELDS, _BOOL_FIELDS
from test_source_analysis_wire import compact_fixture


def evidence(obj):
    return {'evidence_ref': obj.pop('evidence_ref'), 'selection_mode': obj.pop('evidence_mode', 'WHOLE_UNIT'),
            'selector': obj.pop('evidence_selector', ''), 'occurrence': str(obj.pop('evidence_occurrence', 1))}


def from_wire(wire):
    record = copy.deepcopy(wire)
    record.pop('wire_version')
    for field in ('author', 'organization', 'summary'):
        record['source_metadata'].setdefault(field, '')
    for family in ('claims', 'node_matches', 'node_candidates', 'relation_candidates', 'source_references'):
        record.setdefault(family, [])
        for obj in record[family]:
            if 'confidence' in obj:
                obj['confidence'] = format(Decimal(str(obj['confidence'])), 'f')
            if family in ('claims', 'node_matches'):
                obj['evidence'] = evidence(obj)
            if family == 'claims':
                for field, default in {'related_node_ids': [], 'related_candidate_names': [], 'assumption': '', 'status': 'current'}.items():
                    obj.setdefault(field, default)
                obj['structured_json'] = json.dumps(obj.pop('structured', {}), ensure_ascii=False, allow_nan=False)
            elif family == 'node_candidates':
                obj['independent_research_value'] = 'TRUE' if obj['independent_research_value'] else 'FALSE'
                for field in ('aliases', 'suggested_parent_node_ids'):
                    obj.setdefault(field, [])
                for field in ('description', 'reason'):
                    obj.setdefault(field, '')
                preserved = obj.pop('preserved_fields', {})
                slots = {}
                for field in sorted(_TYPE_FIELDS):
                    present = field in preserved
                    value = (evidence(preserved) if field == 'evidence_ref' else preserved.pop(field)) if present else copy.deepcopy(_inactive(field))
                    if present and field in _BOOL_FIELDS:
                        value = 'TRUE' if value else 'FALSE'
                    slots[field] = {'present': 'TRUE' if present else 'FALSE', 'value': value}
                assert not preserved
                obj['preserved_fields'] = slots
                obj['event_evidence'] = evidence(obj) if 'evidence_ref' in obj else copy.deepcopy(NONE_SELECTION)
                for field in sorted(_TYPE_FIELDS - {'evidence_ref'}):
                    if field in _BOOL_FIELDS:
                        obj[field] = 'TRUE' if obj.get(field, False) else 'FALSE'
                    else:
                        obj.setdefault(field, '')
            if family in ('node_matches', 'relation_candidates'):
                obj.setdefault('reason', '')
            if family == 'source_references':
                obj.setdefault('note', '')
    return record


def from_canonical(raw, catalog):
    wire = compact_fixture(raw, catalog)
    wire['wire_version'] = 'source-analysis-wire-v3'
    for claim, original in zip(wire['claims'], raw['claims']):
        claim['evidence_pointer'] = original['evidence_pointer']
    return from_wire(wire)


def claim_linkages(record, refs):
    return [{'evidence_ref': ref, 'claim_refs': [f'C{i}' for i,c in enumerate(record['claims'],1)
            if c['evidence']['evidence_ref'] == ref]} for ref in refs]
