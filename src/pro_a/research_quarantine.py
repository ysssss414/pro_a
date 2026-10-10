"""Read-only object forensics. Never returns an accepted wire or repaired record."""
import copy
import hashlib
import json
import math

from . import output_provider_record_v7 as v7
from . import source_analysis_provider_record as lexical
from .evidence_binding import identity

VERSION = 'NON_CANONICAL_QUARANTINE_V1'
FAMILIES = ('claims', 'node_matches', 'node_candidates', 'relation_candidates', 'source_references')


class LexicalError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LexicalError('DUPLICATE_KEY')
        result[key] = value
    return result


def _number(value):
    number = float(value)
    if not math.isfinite(number):
        raise LexicalError('NON_FINITE_NUMBER')
    return number


def _constant(_):
    raise LexicalError('NON_JSON_CONSTANT')


DECODER = json.JSONDecoder(object_pairs_hook=_pairs, parse_float=_number, parse_constant=_constant)


def _unicode(value):
    if isinstance(value, str):
        value.encode('utf-8', errors='strict')
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode(key)
            _unicode(item)
    elif isinstance(value, list):
        for item in value:
            _unicode(item)


def parse_prefix(raw):
    """Walk the actual root/array grammar; stop at the first lexical error.

    raw_decode proves each complete value's end, including escaped/nested text.
    A duplicate root field invalidates all membership proofs. Nested duplicates
    invalidate that object and stop traversal. No suffix search or JSON repair.
    Spans refer to the original UTF-8 tool argument bytes, not character offsets.
    """
    objects, document, cursor, item_start = [], {}, 0, 0
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeError:
        return {'complete': False, 'document': {}, 'objects': [],
                'error': {'code': 'INVALID_UTF8', 'byte_offset': 0, 'unresolved_item_byte_start': 0}}

    def space():
        nonlocal cursor
        while cursor < len(text) and text[cursor] in ' \t\n\r':
            cursor += 1

    def take(token):
        nonlocal cursor
        space()
        if cursor >= len(text) or text[cursor] != token:
            raise LexicalError('EXPECTED_DELIMITER')
        cursor += 1

    def decode():
        nonlocal cursor
        space()
        start = cursor
        value, cursor = DECODER.raw_decode(text, cursor)
        _unicode(value)
        return value, start, cursor

    try:
        take('{'); space()
        if cursor < len(text) and text[cursor] == '}':
            cursor += 1
        else:
            while True:
                key, _, _ = decode()
                if not isinstance(key, str):
                    raise LexicalError('NON_STRING_ROOT_KEY')
                if key in document:
                    objects.clear()
                    raise LexicalError('DUPLICATE_ROOT_KEY')
                take(':'); space()
                if key in FAMILIES and cursor < len(text) and text[cursor] == '[':
                    cursor += 1; space(); values = []
                    document[key] = values
                    if cursor < len(text) and text[cursor] == ']':
                        cursor += 1
                    else:
                        while True:
                            space(); item_start = cursor
                            value, start, end = decode()
                            # Independently decode the exact slice as well.
                            standalone, stop = DECODER.raw_decode(text[start:end])
                            if stop != end - start or standalone != value:
                                raise LexicalError('UNPROVEN_OBJECT_BOUNDARY')
                            a, b = len(text[:start].encode('utf-8')), len(text[:end].encode('utf-8'))
                            objects.append({'family': key, 'index': len(values), 'value': value,
                                'byte_span': [a, b], 'object_sha256': hashlib.sha256(raw[a:b]).hexdigest()})
                            values.append(value)
                            space()
                            if cursor < len(text) and text[cursor] == ']':
                                cursor += 1; break
                            take(',')
                else:
                    document[key], _, _ = decode()
                space()
                if cursor < len(text) and text[cursor] == '}':
                    cursor += 1; break
                take(',')
        space()
        if cursor != len(text):
            raise LexicalError('TRAILING_CONTENT')
        return {'complete': True, 'document': document, 'objects': objects, 'error': None}
    except (ValueError, UnicodeError) as error:
        return {'complete': False, 'document': document, 'objects': objects,
            'error': {'code': 'INVALID_JSON' if isinstance(error, json.JSONDecodeError) else str(error),
                      'byte_offset': len(text[:getattr(error, 'pos', cursor)].encode('utf-8')),
                      'unresolved_item_byte_start': len(text[:item_start].encode('utf-8'))}}


def inspect_response(raw, scope, segment, catalog, context, *, failure_code):
    """Diagnose v7 objects independently, retaining invalid objects and edges.

    scope must come from the durable frozen attempt, never a model-generated ID.
    Location and references do not prove natural language entailment.
    """
    if scope['provider_record_version'] != v7.VERSION:
        raise ValueError('QUARANTINE_PROTOCOL_NOT_SUPPORTED')
    parsed = parse_prefix(raw)
    schema = v7.record_schema()
    owned, known = set(segment.assigned_evidence_refs), set(context.known_node_ids)
    objects = []
    for original in parsed['objects']:
        obj = copy.deepcopy(original)
        obj.update(object_id=identity([scope, hashlib.sha256(raw).hexdigest(), original['family'], original['index'], original['object_sha256']]),
            schema_status='PASS', location_status='UNRESOLVED_EVIDENCE', ownership_status='UNRESOLVED',
            reference_status='REFERENCE_UNRESOLVED', semantic_review_status='SEMANTIC_REVIEW_REQUIRED',
            context_status='NOT_DECLARED',
            semantic_truth='NOT_ESTABLISHED', evidence=[], context_evidence=[], local_errors=[], reference_errors=[])
        value, family = obj['value'], obj['family']
        try:
            lexical.validate_shape(value, schema['properties'][family]['items'])
            if 'confidence' in value:
                lexical.confidence(value['confidence'])
            if family == 'claims':
                lexical.parse_object(value['structured_json'])
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            obj['schema_status'] = 'FAIL'
            obj['local_errors'].append({'code': 'OBJECT_SCHEMA_OR_FORMAT_INVALID'})
            objects.append(obj); continue

        def bind(intent, path, primary=True):
            try:
                _, bound = v7.resolve_intent(intent, catalog, context, evidence_pointer=value.get('evidence_pointer', ''))
                proof = {'path': path, 'binding': copy.deepcopy(bound.__dict__),
                         'role': 'PRIMARY' if primary else 'CONTEXT'}
                (obj['evidence'] if primary else obj['context_evidence']).append(proof)
                if primary and bound.evidence_ref not in owned:
                    obj['local_errors'].append({'code': 'SUPPORT_OUTSIDE_ASSIGNED_SEGMENT', 'path': path})
            except (ValueError, TypeError, KeyError) as error:
                obj['local_errors'].append({'code': 'INVALID_EVIDENCE', 'path': path, 'detail': str(error)})

        if family in ('claims', 'node_matches'):
            bind(value['evidence'], ['evidence'])
        elif family == 'node_candidates':
            for i, prop in enumerate(value['evidence_properties']):
                bind(prop['value'], ['evidence_properties', i])
        elif family == 'source_references':
            units = [u for u in catalog.units if v7.unit_anchor(u) == value['ownership_anchor']]
            if len(units) == 1:
                bind(v7.unit_selection(units[0]), ['ownership_anchor'])
            else:
                obj['local_errors'].append({'code': 'INVALID_EVIDENCE', 'path': ['ownership_anchor']})
        if family == 'claims':
            for i, dep in enumerate(value['research_review']['context_dependencies']):
                bind(dep['evidence'], ['research_review', 'context_dependencies', i], False)
                if obj['context_evidence'] and obj['context_evidence'][-1]['path'][-1] == i:
                    obj['context_evidence'][-1].update(relationship=dep['relationship'], reason=dep['reason'],
                        relationship_authorization='NOT_ESTABLISHED')
            dependencies = value['research_review']['context_dependencies']
            if dependencies:
                obj['context_status'] = 'LOCATION_VERIFIED' if len(obj['context_evidence']) == len(dependencies) else 'INVALID_EVIDENCE'
        if family == 'node_candidates':
            from .node_candidate_intent import compile_properties
            formatted = copy.deepcopy(value)
            try:
                for prop in formatted['evidence_properties']:
                    selection, _ = v7.resolve_intent(prop['value'], catalog, context)
                    prop['value'] = selection
                compile_properties(formatted)
            except (ValueError, TypeError, KeyError):
                if not any(e['code'] == 'INVALID_EVIDENCE' for e in obj['local_errors']):
                    obj['schema_status'] = 'FAIL'
                    obj['local_errors'].append({'code': 'OBJECT_PROPERTY_FORMAT_INVALID'})
        if any(e['code'] == 'INVALID_EVIDENCE' for e in obj['local_errors']):
            obj['location_status'] = 'INVALID_EVIDENCE'
        elif obj['evidence']:
            obj['location_status'] = 'LOCATION_VERIFIED'
        if any(e['code'] == 'SUPPORT_OUTSIDE_ASSIGNED_SEGMENT' for e in obj['local_errors']):
            obj['ownership_status'] = 'FAIL'
        elif obj['evidence'] and not any(e['code'] == 'INVALID_EVIDENCE' for e in obj['local_errors']):
            obj['ownership_status'] = 'PASS'
        ids = value.get('related_node_ids', []) + value.get('suggested_parent_node_ids', [])
        ids += [value[k] for k in ('node_id', 'from_node_id', 'to_node_id') if k in value]
        if any(n not in known for n in ids):
            obj['reference_errors'].append('UNKNOWN_SCOPED_NODE')
        objects.append(obj)

    by_family = {f: [o for o in objects if o['family'] == f] for f in FAMILIES}
    if parsed['complete']:
        candidates = {}
        for obj in by_family['node_candidates']:
            name = obj['value'].get('canonical_name', '') if isinstance(obj['value'], dict) else ''
            candidates.setdefault(' '.join(name.split()).lower(), []).append(obj)
        claims = {'C'+str(o['index']+1): o for o in by_family['claims']}
        # Claims' candidate references are resolved before dependent supports,
        # irrespective of the provider's root field order.
        ordered = [o for f in FAMILIES for o in by_family[f]]
        for obj in ordered:
            if obj['schema_status'] != 'PASS':
                continue
            value = obj['value']
            if obj['family'] == 'claims':
                for name in value['related_candidate_names']:
                    matches = candidates.get(' '.join(name.split()).lower(), [])
                    if len(matches) != 1 or matches[0]['schema_status'] != 'PASS':
                        obj['reference_errors'].append('MISSING_OR_AMBIGUOUS_CANDIDATE')
            elif obj['family'] == 'node_candidates':
                key = ' '.join(value['canonical_name'].split()).lower()
                if len(candidates[key]) != 1:
                    obj['reference_errors'].append('AMBIGUOUS_CANDIDATE_NAME')
                supports = [c for c in claims.values() if c['schema_status'] == 'PASS' and
                    key in [' '.join(n.split()).lower() for n in c['value']['related_candidate_names']]]
                obj['support_relationships'] = [{'family': c['family'], 'index': c['index'], 'object_id': c['object_id']} for c in supports]
                if any(c['location_status'] != 'LOCATION_VERIFIED' or c['ownership_status'] != 'PASS' or c['reference_errors'] for c in supports):
                    obj['reference_errors'].append('INVALID_SUPPORTING_CLAIM')
                for c in supports:
                    obj['evidence'].extend(copy.deepcopy(c['evidence']))
                if not obj['evidence']:
                    obj['reference_errors'].append('CANDIDATE_SUPPORT_UNRESOLVED')
                elif not obj['local_errors'] and not obj['reference_errors']:
                    obj['location_status'], obj['ownership_status'] = 'LOCATION_VERIFIED', 'PASS'
            elif obj['family'] == 'relation_candidates':
                refs = value['supporting_claim_refs']
                if not refs or len(refs) != len(set(refs)) or any(r not in claims for r in refs):
                    obj['reference_errors'].append('MISSING_OR_INVALID_CLAIM_REFERENCE')
                for ref in refs:
                    claim = claims.get(ref)
                    if claim is None:
                        continue
                    obj['evidence'].extend(copy.deepcopy(claim['evidence']))
                    if claim['schema_status'] != 'PASS' or claim['ownership_status'] != 'PASS' or claim['location_status'] != 'LOCATION_VERIFIED' or claim['reference_errors']:
                        obj['reference_errors'].append('INVALID_SUPPORTING_CLAIM')
                if obj['evidence'] and not obj['reference_errors']:
                    obj['location_status'], obj['ownership_status'] = 'LOCATION_VERIFIED', 'PASS'
            obj['reference_status'] = 'FAIL' if obj['reference_errors'] else 'LOCALLY_VERIFIED'
    global_errors = []
    if parsed['complete']:
        try:
            lexical.validate_shape(parsed['document'], schema)
            anchors = [a['anchor_id'] for a in parsed['document']['evidence_acknowledgements']]
            expected = {v7.unit_anchor(u) for u in catalog.units if u.evidence_ref in owned}
            if len(anchors) != len(set(anchors)) or set(anchors) != expected:
                global_errors.append('ASSIGNED_ACKNOWLEDGEMENT_MISMATCH')
        except (ValueError, TypeError, KeyError):
            global_errors.append('RESPONSE_SCHEMA_INVALID')
    return {'version': VERSION, 'authority': 'NON_CANONICAL', 'accepted': False, 'canonical_permission': False,
        'scope': copy.deepcopy(scope), 'raw_sha256': hashlib.sha256(raw).hexdigest(), 'raw_byte_length': len(raw),
        'original_failure_code': failure_code, 'incomplete_response': not parsed['complete'],
        'response_status': 'COMPLETE_JSON' if parsed['complete'] else 'MALFORMED_RESPONSE_PREFIX',
        'suffix_status': 'NONE' if parsed['complete'] else 'UNKNOWN_SUFFIX',
        'total_object_counts': {f: len(by_family[f]) for f in FAMILIES} if parsed['complete'] else 'UNKNOWN',
        'parse_error': parsed['error'], 'global_errors': global_errors, 'objects': objects}
