"""Offline evidence-intent experiment. No Run binding or admission authority.

Only new, explicitly versioned records may enter this compiler. The resulting
SegmentWireResult is a binding candidate, never a durable Accepted Segment.
Exact location/ownership does not authorize anaphora, attribution or entailment.
"""
import copy
import json

from . import output_provider_record_v6 as v6
from . import source_analysis_provider_record as lexical
from .bounded_extraction import series_coverage
from .evidence_binding import identity, resolve_evidence_binding_v2

VERSION = 'evidence-intent-offline-prototype-v1'
SCHEMA_VERSION = 'evidence-intent-offline-tool-schema-v1'


class IntentBindingError(ValueError):
    """Safe code and replayable location diagnostics, without Source text."""
    def __init__(self, code, **details):
        super().__init__(code)
        self.details = details


def record_schema():
    def replace(schema):
        if schema.get('type') == 'object':
            if set(schema['properties']) == set(lexical.selection_schema()['properties']):
                return lexical.closed({'kind': lexical.enum(('UNIT_ANCHOR', 'EXACT_QUOTE')),
                                       'value': {'type': 'string'}})
            return lexical.closed({k: replace(v) for k, v in schema['properties'].items()})
        if schema.get('type') == 'array':
            return {'type': 'array', 'items': replace(schema['items'])}
        return copy.deepcopy(schema)
    schema = replace(v6.record_schema())
    schema['properties']['protocol_version'] = lexical.enum((VERSION,))
    schema['required'].append('protocol_version')
    schema['properties']['evidence_acknowledgements']['items'] = lexical.closed({'anchor_id': {'type': 'string'}})
    reference = schema['properties']['source_references']['items']['properties']
    reference['ownership_anchor'] = reference.pop('ownership_evidence_ref')
    schema['properties']['source_references']['items']['required'] = list(reference)
    return schema


def unit_anchor(unit):
    return 'EA_' + identity({'version': VERSION, 'source': unit.source_sha256,
        'piece': unit.piece_sha256, 'ref': unit.evidence_ref,
        'span': [unit.source_start, unit.source_end]})[:24].upper()


def _target(series, plan, segment, catalog, context):
    # Reuse the existing complete plan/catalog identity checks, including active
    # leaves after subdivision. No new execution identity or relaxed validator.
    series_coverage(series, plan, (), catalog, context)
    if segment not in plan.leaves:
        raise IntentBindingError('INTENT_SEGMENT_NOT_ACTIVE_LEAF')


def request_payload(series, plan, segment, catalog, context):
    _target(series, plan, segment, catalog, context)
    regions, cursor = [], 0
    owned = set(segment.assigned_evidence_refs)
    for unit in catalog.units:
        if cursor < unit.source_start:
            regions.append({'role': 'CONTEXT', 'text': context.piece.source_text[cursor:unit.source_start]})
        region = {'role': 'ASSIGNED' if unit.evidence_ref in owned else 'CONTEXT', 'text': unit.exact_text}
        if unit.evidence_ref in owned:
            region['anchor_id'] = unit_anchor(unit)
        regions.append(region)
        cursor = unit.source_end
    if cursor < len(context.piece.source_text):
        regions.append({'role': 'CONTEXT', 'text': context.piece.source_text[cursor:]})
    return {'protocol_version': VERSION, 'schema_version': SCHEMA_VERSION,
        'series_sha256': series.series_sha256, 'segment_sha256': segment.segment_sha256,
        'known_node_ids': list(context.known_node_ids), 'source_regions': regions}


def compile_binding_candidate(content, series, plan, segment, catalog, context):
    """All-or-nothing binding proof. No rewriting, routing or partial acceptance."""
    _target(series, plan, segment, catalog, context)
    record = lexical.parse_object(content)
    lexical.validate_shape(record, record_schema())
    anchors = {unit_anchor(unit): unit for unit in catalog.units}
    if len(anchors) != len(catalog.units):
        raise IntentBindingError('INTENT_ANCHOR_AMBIGUOUS')
    owned = set(segment.assigned_evidence_refs)
    bindings = []

    def resolve(intent, path):
        if intent['kind'] == 'UNIT_ANCHOR':
            unit = anchors.get(intent['value'])
            if unit is None:
                raise IntentBindingError('INTENT_UNKNOWN_ANCHOR', path=path)
            selection = {'evidence_ref': unit.evidence_ref, 'selection_mode': 'WHOLE_UNIT',
                         'selector': '', 'occurrence': '1'}
        else:
            quote = intent['value']
            if not quote:
                raise IntentBindingError('INTENT_EMPTY_QUOTE', path=path)
            text = context.piece.source_text
            start = text.find(quote)
            if start < 0:
                raise IntentBindingError('INTENT_QUOTE_NOT_FOUND', path=path)
            if text.find(quote, start + 1) >= 0:
                raise IntentBindingError('INTENT_QUOTE_AMBIGUOUS', path=path)
            end = start + len(quote)
            units = [u for u in catalog.units if u.source_start <= start and end <= u.source_end]
            if len(units) != 1:
                raise IntentBindingError('INTENT_QUOTE_NOT_IN_SINGLE_UNIT', path=path)
            unit = units[0]
            selection = {'evidence_ref': unit.evidence_ref, 'selection_mode': 'RAW_SUBSPAN',
                         'selector': quote, 'occurrence': '1'}
        bound = resolve_evidence_binding_v2(lexical.selection(selection), catalog, context)
        if unit.evidence_ref not in owned:
            raise IntentBindingError('INTENT_SUPPORT_OUTSIDE_ASSIGNED_SEGMENT', path=path,
                evidence_ref=unit.evidence_ref, source_span=[bound.source_start, bound.source_end],
                owner_segment_ids=[s.segment_id for s in plan.leaves if unit.evidence_ref in s.assigned_evidence_refs],
                scheduled=False)
        bindings.append({'path': path, 'intent': copy.deepcopy(intent), 'selection': selection,
                         'binding': copy.deepcopy(bound.__dict__)})
        return selection

    compiled = copy.deepcopy(record)
    del compiled['protocol_version']
    for family in ('claims', 'node_matches'):
        for index, obj in enumerate(compiled[family]):
            obj['evidence'] = resolve(obj['evidence'], [family, index, 'evidence'])
    for index, candidate in enumerate(compiled['node_candidates']):
        for ei, entry in enumerate(candidate['evidence_properties']):
            entry['value'] = resolve(entry['value'], ['node_candidates', index, 'evidence_properties', ei, 'value'])
    for index, ack in enumerate(compiled['evidence_acknowledgements']):
        selection = resolve({'kind': 'UNIT_ANCHOR', 'value': ack['anchor_id']}, ['evidence_acknowledgements', index])
        compiled['evidence_acknowledgements'][index] = {'evidence_ref': selection['evidence_ref']}
    for index, reference in enumerate(compiled['source_references']):
        selection = resolve({'kind': 'UNIT_ANCHOR', 'value': reference.pop('ownership_anchor')}, ['source_references', index])
        reference['ownership_evidence_ref'] = selection['evidence_ref']
    result, ownership = v6.compile_result(json.dumps(compiled, ensure_ascii=False), series, segment, catalog, context)
    return result, {'version': VERSION, 'schema_sha256': identity(record_schema()),
        'provider_record_sha256': identity(record), 'compiled_record_sha256': identity(compiled),
        'series_sha256': series.series_sha256, 'segment_sha256': segment.segment_sha256,
        'bindings': bindings, 'candidate_ownership': ownership,
        'result_sha256': result.result_sha256, 'segment_accepted': False,
        'semantic_authorization': 'NOT_ESTABLISHED', 'status': 'NON_CANONICAL_BINDING_CANDIDATE'}
