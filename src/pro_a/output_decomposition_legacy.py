"""Frozen v1/v2 acceptance only. Never upgrade or repair a historical record."""
import copy
from collections import Counter
import re

from . import source_analysis_provider_record as lexical
from .bounded_extraction import EvidenceDisposition, create_segment_wire_result
from .evidence_binding import resolve_evidence_binding_v2

V1 = 'whole-piece-output-batch-provider-record-v1'
RECORD_VERSION = 'whole-piece-output-batch-provider-record-v2'


def record_schema(version=RECORD_VERSION):
    if version not in (V1, RECORD_VERSION):
        raise ValueError('UNSUPPORTED_HISTORICAL_PROVIDER_CONTRACT')
    schema = lexical.record_schema()
    for family in ('node_candidates', 'source_references'):
        item = schema['properties'][family]['items']
        item['properties']['ownership_evidence_ref'] = {'type': 'string'}
        item['required'].append('ownership_evidence_ref')
    field = {'disposition': lexical.enum(('CLAIMED', 'NO_INDEPENDENT_CLAIM'))} if version == V1 else {
        'claim_refs': {'type': 'array', 'items': {'type': 'string'}}}
    schema['properties']['dispositions'] = {'type': 'array', 'items': lexical.closed({'evidence_ref': {'type': 'string'}, **field})}
    schema['required'].append('dispositions')
    return schema


def record_to_result(content, series, segment, catalog, context, *, record_version=RECORD_VERSION):
    record = lexical.parse_object(content)
    lexical.validate_shape(record, record_schema(record_version))
    owned = set(segment.assigned_evidence_refs)
    stripped = copy.deepcopy(record)
    linkages = stripped.pop('dispositions')
    if record_version != V1:
        refs = [item['evidence_ref'] for item in linkages]
        if set(refs) - owned:raise ValueError('FOREIGN_EVIDENCE_LINKAGE')
        if any(count != 1 for count in Counter(refs).values()):raise ValueError('DUPLICATE_EVIDENCE_LINKAGE')
        if set(refs) != owned:raise ValueError('MISSING_EVIDENCE_LINKAGE')
    for family in ('node_candidates','source_references'):
        for obj in stripped[family]:
            if obj.pop('ownership_evidence_ref') not in owned:raise ValueError('OUTPUT_OWNERSHIP_VIOLATION')
    selections = [obj['evidence'] for family in ('claims','node_matches') for obj in stripped[family]]
    for obj in stripped['node_candidates']:
        if obj['event_evidence']['selection_mode'] != 'NONE':selections.append(obj['event_evidence'])
        preserved = obj['preserved_fields']['evidence_ref']
        if preserved['present'] == 'TRUE':selections.append(preserved['value'])
    if any(selection['evidence_ref'] not in owned for selection in selections):raise ValueError('OUTPUT_OWNERSHIP_VIOLATION')
    if record_version == V1:
        dispositions = tuple(EvidenceDisposition(**item) for item in linkages)
    else:
        expected = {ref: set() for ref in owned}
        for index, claim in enumerate(stripped['claims'], 1):
            selection = lexical.selection(claim['evidence'])
            resolve_evidence_binding_v2(selection, catalog, context)
            expected[selection['evidence_ref']].add(f'C{index}')
        valid_refs = {f'C{i}' for i in range(1, len(stripped['claims']) + 1)}
        for item in linkages:
            refs = item['claim_refs']
            if any(not re.fullmatch(r'C[1-9][0-9]*', ref) for ref in refs):raise ValueError('INVALID_LOCAL_CLAIM_LINK')
            if len(set(refs)) != len(refs):raise ValueError('DUPLICATE_LOCAL_CLAIM_LINK')
            if set(refs) - valid_refs:raise ValueError('UNKNOWN_LOCAL_CLAIM_LINK')
            if set(refs) != expected[item['evidence_ref']]:raise ValueError('CLAIM_LINKAGE_MISMATCH')
        dispositions = tuple(EvidenceDisposition(ref, 'CLAIMED' if expected[ref] else 'NO_INDEPENDENT_CLAIM')
                             for ref in segment.assigned_evidence_refs)
    return create_segment_wire_result(series, segment, lexical.provider_record_to_wire_v3(stripped), dispositions, catalog, context)
