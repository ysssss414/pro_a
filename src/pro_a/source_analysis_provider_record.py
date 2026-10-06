"""Pure lexical ProviderRecord boundary. Provider schema only assists format.

Local validation is authoritative. Wire/Evidence and native semantic acceptance
remain separate, unchanged gates. No coercion, repair or occurrence inference.
"""
import copy
import hashlib
import json
import math
import re
from decimal import Decimal

from .constants import (CLAIM_NATURES, CLAIM_STATUSES, NODE_TYPES, NOVELTY_LEVELS,
                            RELATION_TYPES, SOURCE_ORIGIN_TYPES, SOURCE_RANKS)
from .source_analysis_wire import (NODE_MATCH_ROLES, SOURCE_REFERENCE_RELATION_TYPES,
                                   _NODE_VARIANTS, _TYPE_FIELDS, _BOOL_FIELDS)
from .evidence_binding import EVIDENCE_MODES

VERSION = 'whole-piece-source-analysis-provider-record-v1'
TOOL_SCHEMA_VERSION = 'whole-piece-source-analysis-tool-schema-v1'
TOOL_NAME = 'emit_source_analysis'
LEXICAL_BOOLEANS = ('TRUE', 'FALSE')
NONE_SELECTION = {'evidence_ref': '', 'selection_mode': 'NONE', 'selector': '', 'occurrence': '1'}


def parse_object(value):
    """Decode exact JSON object text, rejecting duplicate/nonfinite/invalid Unicode."""
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError()
            result[key] = item
        return result
    def nonfinite(_):
        raise ValueError()
    def inspect(item):
        if isinstance(item, str):
            item.encode('utf-8', errors='strict')
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError()
        elif isinstance(item, list):
            for child in item:
                inspect(child)
        elif isinstance(item, dict):
            for key, child in item.items():
                inspect(key)
                inspect(child)
    try:
        if type(value) is not str:
            raise ValueError()
        value.encode('utf-8', errors='strict')
        result = json.loads(value, object_pairs_hook=unique, parse_constant=nonfinite)
        if type(result) is not dict:
            raise ValueError()
        inspect(result)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('INVALID_PROVIDER_JSON_OBJECT') from None


def boolean(value):
    if type(value) is not str or value not in LEXICAL_BOOLEANS:
        raise ValueError('INVALID_LEXICAL_BOOLEAN')
    return value == 'TRUE'


def confidence(value):
    # Preserve canonical integer/float identity, including JSON's signed zero.
    # The only permitted negative spelling is a decimal negative zero.
    if type(value) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?|-0\.0+', value):
        raise ValueError('INVALID_LEXICAL_CONFIDENCE')
    exact = Decimal(value)
    if not exact.is_finite() or not Decimal(0) <= exact <= Decimal(1):
        raise ValueError('CONFIDENCE_OUT_OF_RANGE')
    result = float(exact) if '.' in value else int(exact)
    if not math.isfinite(result) or (exact != 0 and result == 0) or (exact != 1 and result == 1):
        raise ValueError('CONFIDENCE_FLOAT_BOUNDARY_LOSS')
    return result


def occurrence(value):
    if type(value) is not str or not re.fullmatch(r'[1-9][0-9]*', value):
        raise ValueError('INVALID_LEXICAL_OCCURRENCE')
    try:
        return int(value)
    except ValueError:
        raise ValueError('UNREPRESENTABLE_OCCURRENCE') from None


def closed(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def enum(values):
    return {'type': 'string', 'enum': sorted(values)}


def selection_schema(*, optional=False):
    return closed({'evidence_ref': {'type': 'string'}, 'selection_mode': enum((*EVIDENCE_MODES, 'NONE') if optional else EVIDENCE_MODES),
                   'selector': {'type': 'string'}, 'occurrence': {'type': 'string'}})


def validate_shape(value, schema):
    kind = schema['type']
    if kind == 'object':
        if type(value) is not dict or set(value) != set(schema['properties']):
            raise ValueError('INVALID_PROVIDER_RECORD_SHAPE')
        for key, child in schema['properties'].items():
            validate_shape(value[key], child)
    elif kind == 'array':
        if type(value) is not list:
            raise ValueError('INVALID_PROVIDER_RECORD_SHAPE')
        for child in value:
            validate_shape(child, schema['items'])
    elif type(value) is not str or ('enum' in schema and value not in schema['enum']):
        raise ValueError('INVALID_PROVIDER_RECORD_SHAPE')
    else:
        try:
            value.encode('utf-8', errors='strict')
        except UnicodeError:
            raise ValueError('INVALID_PROVIDER_RECORD_STRING') from None


def selection(value):
    validate_shape(value, selection_schema())
    if not value['evidence_ref'].strip():
        raise ValueError('EMPTY_PROVIDER_EVIDENCE_REF')
    selected = occurrence(value['occurrence'])
    if value['selection_mode'] == 'WHOLE_UNIT':
        if value['selector'] != '' or value['occurrence'] != '1':
            raise ValueError('INVALID_WHOLE_SELECTION')
        return {'evidence_ref': value['evidence_ref']}
    if not value['selector']:
        raise ValueError('EMPTY_SUBSPAN_SELECTOR')
    return {'evidence_ref': value['evidence_ref'], 'evidence_mode': value['selection_mode'],
            'evidence_selector': value['selector'], 'evidence_occurrence': selected}


def record_schema():
    text = {'type': 'string'}
    strings = {'type': 'array', 'items': text}
    return closed({
        'source_metadata': closed({**{k: text for k in ('title', 'publication_time', 'author', 'organization', 'summary')},
            'source_rank': enum(SOURCE_RANKS), 'source_origin_type': enum(SOURCE_ORIGIN_TYPES)}),
        'claims': {'type': 'array', 'items': closed({
            **{k: text for k in ('statement', 'attributed_to', 'fact_time', 'scope', 'evidence_pointer', 'confidence', 'assumption', 'structured_json')},
            'nature': enum(CLAIM_NATURES), 'status': enum(CLAIM_STATUSES), 'novelty_level': enum(NOVELTY_LEVELS),
            'related_node_ids': strings, 'related_candidate_names': strings, 'evidence': selection_schema()})},
        'node_matches': {'type': 'array', 'items': closed({'node_id': text, 'role': enum(NODE_MATCH_ROLES),
            'confidence': text, 'reason': text, 'evidence': selection_schema()})},
        'node_candidates': {'type': 'array', 'items': closed({
            **{k: text for k in ('canonical_name', 'confidence', 'maintenance_rationale', 'description', 'reason')},
            'primary_type': enum(NODE_TYPES), 'independent_research_value': enum(LEXICAL_BOOLEANS),
            'aliases': strings, 'suggested_parent_node_ids': strings,
            **{k: enum(LEXICAL_BOOLEANS) if k in _BOOL_FIELDS else text
               for k in sorted(_TYPE_FIELDS - {'evidence_ref'})},
            'event_evidence': selection_schema(optional=True),
            'preserved_fields': closed({k: closed({'present': enum(LEXICAL_BOOLEANS),
                'value': selection_schema(optional=True) if k == 'evidence_ref' else
                         enum(LEXICAL_BOOLEANS) if k in _BOOL_FIELDS else text}) for k in sorted(_TYPE_FIELDS)})})},
        'relation_candidates': {'type': 'array', 'items': closed({
            **{k: text for k in ('from_node_id', 'to_node_id', 'scope', 'confidence', 'reason')},
            'relation_type': enum(sorted(set(RELATION_TYPES) - {'part_of'})), 'supporting_claim_refs': strings})},
        'source_references': {'type': 'array', 'items': closed({'title': text,
            'relation_type': enum(SOURCE_REFERENCE_RELATION_TYPES), 'note': text})}})


def _inactive(field):
    return NONE_SELECTION if field == 'evidence_ref' else 'FALSE' if field in _BOOL_FIELDS else ''


def _variant_value(target, field, value):
    if field == 'evidence_ref':
        target.update(selection(value))
    else:
        target[field] = boolean(value) if field in _BOOL_FIELDS else value


def provider_record_to_wire_v3(record):
    # Bound authoritative arrays before recursively walking/copying their items.
    if type(record) is dict:
        for family in ('claims', 'node_candidates'):
            if type(record.get(family)) is list and len(record[family]) > 100:
                raise ValueError('PROVIDER_RECORD_ARRAY_LIMIT')
    validate_shape(record, record_schema())
    wire = copy.deepcopy(record)
    wire['wire_version'] = 'source-analysis-wire-v3'
    for family in ('claims', 'node_matches', 'node_candidates', 'relation_candidates'):
        for obj in wire[family]:
            obj['confidence'] = confidence(obj['confidence'])
            if family in ('claims', 'node_matches'):
                obj.update(selection(obj.pop('evidence')))
            if family == 'claims':
                obj['structured'] = parse_object(obj.pop('structured_json'))
            if family == 'node_candidates':
                obj['independent_research_value'] = boolean(obj['independent_research_value'])
                active = _NODE_VARIANTS.get(obj['primary_type'], set())
                preserved = obj.pop('preserved_fields')
                projected = {}
                for field in sorted(_TYPE_FIELDS):
                    value = obj.pop('event_evidence' if field == 'evidence_ref' else field)
                    if field in active:
                        _variant_value(projected, field, value)
                    elif value != _inactive(field):
                        raise ValueError('NONDEFAULT_INACTIVE_VARIANT')
                obj.update(projected)
                projected = {}
                for field, slot in preserved.items():
                    present = boolean(slot['present'])
                    if present:
                        if field in active:
                            raise ValueError('ACTIVE_FIELD_IN_PRESERVED_SLOT')
                        _variant_value(projected, field, slot['value'])
                    elif slot['value'] != _inactive(field):
                        raise ValueError('NONDEFAULT_ABSENT_PRESERVED_SLOT')
                if projected:
                    obj['preserved_fields'] = projected
    # Retain explicit empty optional values. Existing expansion supplies the same
    # canonical defaults when omitted; qualification proves equivalence. No
    # statements, Node IDs, selectors, pointers or evidence refs are rewritten.
    return wire


def validate_provider_record(record):
    provider_record_to_wire_v3(record)


def tool_schema_sha256():
    return hashlib.sha256(json.dumps(record_schema(), ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()
