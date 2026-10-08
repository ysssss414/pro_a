"""Test-only inverse of valid synthetic V3 objects. Never import private raw."""
import copy
from pro_a import source_analysis_provider_record as lexical
from pro_a.output_provider_record_v4 import PRESERVED
from pro_a.source_analysis_wire import _TYPE_FIELDS, _NODE_VARIANTS
from lexical_record_helpers import from_wire


def from_valid_v3(record):
    check = copy.deepcopy(record)
    check.pop('evidence_acknowledgements', None)
    for family in ('node_candidates', 'source_references'):
        for obj in check[family]:
            obj.pop('ownership_evidence_ref', None)
    lexical.validate_provider_record(check)
    result = copy.deepcopy(record)
    for obj in result['node_candidates']:
        active = _NODE_VARIANTS.get(obj['primary_type'], set())
        slots = obj.pop('preserved_fields')
        for field in _TYPE_FIELDS - active:
            obj.pop('event_evidence' if field == 'evidence_ref' else field)
        for array, fields in PRESERVED.items():
            obj[array] = [{'field': f, 'value': copy.deepcopy(slots[f]['value'])}
                          for f in sorted(fields) if slots[f]['present'] == 'TRUE']
    return result


def from_wire_v4(wire):
    return from_valid_v3(from_wire(wire))
