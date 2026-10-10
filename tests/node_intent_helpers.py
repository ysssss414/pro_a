"""Valid synthetic V4 -> intent fixtures only; never used on historical Raw."""
import copy
import json

from pro_a import output_provider_record_v4 as v4
from pro_a.node_candidate_intent import PROPERTY_FIELDS
from pro_a.source_analysis_wire import _NODE_VARIANTS, _TYPE_FIELDS


def from_valid_v4(record):
    v4.normalize_record(json.dumps(record))
    result = copy.deepcopy(record)
    for node in result['node_candidates']:
        active = _NODE_VARIANTS.get(node['primary_type'], set())
        props = {f: node.pop('event_evidence' if f == 'evidence_ref' else f) for f in active}
        for array in v4.PRESERVED:
            for entry in node.pop(array):
                assert entry['field'] not in props
                props[entry['field']] = entry['value']
        assert set(props) <= _TYPE_FIELDS
        for array, fields in PROPERTY_FIELDS.items():
            node[array] = [{'field': f, 'value': props[f]} for f in sorted(fields & props.keys())]
    return result
