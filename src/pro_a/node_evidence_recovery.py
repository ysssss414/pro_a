"""Opt-in, reversible offline projection onto existing explicit Claim support.

The v7 wire, scalar Node properties and acceptance/lifecycle gates are unchanged.
A reviewer classifies non-type evidence properties as support before projection.
Every occurrence must already have the same located evidence on an explicitly
linked Claim. This module neither invents support nor selects ownership evidence.
"""
import base64
import copy
from dataclasses import asdict
import hashlib
import json

from . import output_provider_record_v7 as v7
from .bounded_extraction import expand_source_analysis_wire_v3
from .evidence_binding import identity
from .source_analysis_wire import _NODE_VARIANTS

VERSION = 'offline-node-evidence-link-recovery-v1'
PLAN = 'node-evidence-support-classification-v1'
SEMANTICS = 'SUPPORT_ALREADY_EXPLICIT_ON_LINKED_CLAIMS'


def require(value, code):
    if not value:
        raise ValueError(code)


def scope(series, segment, context):
    return {'series_sha256': series.series_sha256, 'segment_sha256': segment.segment_sha256,
            'source_sha256': context.source_sha256, 'piece_sha256': context.piece.source_sha256}


def _location(binding):
    return tuple(getattr(binding, k) for k in
                 ('evidence_ref', 'mode', 'source_start', 'source_end', 'raw_excerpt_sha256'))


def recover(raw, proposal, series, segment, catalog, context, *, plan=None, b1_context=None):
    """Compile an offline artifact; never returns a formal Accepted descriptor.

    Single properties and unselected objects retain their original behavior.
    Event/type-specific and other scalar conflicts stay errors. An unrepresented
    support or dangling dependency blocks the whole projection; no partial batch
    is produced by erasing Claim.related_candidate_names.
    """
    require(type(raw) is bytes, 'RECOVERY_RAW_BYTES_REQUIRED')
    raw_sha = hashlib.sha256(raw).hexdigest()
    require(type(proposal) is dict and set(proposal) ==
            {'version', 'raw_sha256', 'scope', 'conversions'} and proposal['version'] == PLAN,
            'RECOVERY_PLAN_INVALID')
    require(proposal['raw_sha256'] == raw_sha and proposal['scope'] == scope(series, segment, context),
            'RECOVERY_SOURCE_IDENTITY_MISMATCH')
    record = v7.lexical.parse_object(raw.decode('utf8'))
    v7.lexical.validate_shape(record, v7.record_schema())
    if b1_context is not None:
        from .b1_extraction import validate_record
        validate_record(raw.decode('utf8'), b1_context, catalog, context, segment)
    projected = copy.deepcopy(record)
    conversions = proposal['conversions']
    require(type(conversions) is list, 'RECOVERY_PLAN_INVALID')
    mappings, selected = [], set()
    owned = set(segment.assigned_evidence_refs)
    for conversion in conversions:
        require(type(conversion) is dict and set(conversion) ==
                {'candidate_index', 'canonical_name', 'semantics', 'reviewer', 'reason'}, 'RECOVERY_PLAN_INVALID')
        index = conversion['candidate_index']
        require(type(index) is int and 0 <= index < len(record['node_candidates']) and index not in selected,
                'RECOVERY_TARGET_INVALID')
        selected.add(index)
        node = record['node_candidates'][index]
        require(conversion['canonical_name'] == node['canonical_name'] and conversion['semantics'] == SEMANTICS
                and all(type(conversion[k]) is str and conversion[k].strip() for k in ('reviewer', 'reason')),
                'RECOVERY_EXPLICIT_CLASSIFICATION_REQUIRED')
        require('evidence_ref' not in _NODE_VARIANTS.get(node['primary_type'], set()),
                'RECOVERY_TYPE_PROPERTY_CONFLICT')
        properties = node['evidence_properties']
        require(len(properties) > 1 and all(e['field'] == 'evidence_ref' for e in properties),
                'RECOVERY_DUPLICATE_SUPPORT_REQUIRED')
        linked = []
        for ci, claim in enumerate(record['claims']):
            if node['canonical_name'] in claim['related_candidate_names']:
                _, binding = v7.resolve_intent(claim['evidence'], catalog, context,
                                             evidence_pointer=claim['evidence_pointer'])
                require(binding.evidence_ref in owned, 'RECOVERY_SUPPORT_OUTSIDE_ASSIGNED')
                linked.append((ci, binding))
        for ei, entry in enumerate(properties):
            _, binding = v7.resolve_intent(entry['value'], catalog, context)
            require(binding.evidence_ref in owned, 'RECOVERY_SUPPORT_OUTSIDE_ASSIGNED')
            matches = [(ci, b) for ci, b in linked if _location(b) == _location(binding)]
            require(matches, 'RECOVERY_SUPPORT_NOT_EXPLICITLY_REPRESENTED')
            mappings.append({'original_path': ['node_candidates', index, 'evidence_properties', ei],
                'original_property': copy.deepcopy(entry), 'original_binding': asdict(binding),
                'represented_by': [{'claim_path': ['claims', ci],
                    'relationship_path': ['claims', ci, 'related_candidate_names'],
                    'candidate_name': node['canonical_name'], 'claim_binding': asdict(b)} for ci, b in matches]})
        # All occurrences are retained above. The existing Claim edges carry the
        # same support into v6, which independently derives set-valued ownership.
        projected['node_candidates'][index]['evidence_properties'] = []
    content = json.dumps(projected, ensure_ascii=False, allow_nan=False)
    if b1_context is not None:
        from .b1_extraction import validate_record
        validate_record(content, b1_context, catalog, context, segment)
    result, review = v7.compile_result(content, series, segment, catalog, context, plan=plan)
    native = expand_source_analysis_wire_v3(json.loads(result.wire_json), catalog, context)
    body = {'version': VERSION, 'proposal': copy.deepcopy(proposal), 'raw_sha256': raw_sha,
        'raw_base64': base64.b64encode(raw).decode('ascii'), 'original_record_sha256': identity(record),
        'projected_record': projected, 'projected_record_sha256': identity(projected),
        'support_mappings': mappings, 'result': asdict(result), 'research_review': review, 'native': native,
        'status': 'OFFLINE_COMPILED_REVIEW_REQUIRED', 'formal_accepted': False,
        'semantic_authorization': 'NOT_ESTABLISHED', 'canonical_permission': False}
    body = json.loads(json.dumps(body, ensure_ascii=False, allow_nan=False))
    return {**body, 'identity': identity(body)}


def verify(document, raw, proposal, series, segment, catalog, context, **kwargs):
    require(document == recover(raw, proposal, series, segment, catalog, context, **kwargs),
            'RECOVERY_ARTIFACT_DRIFT')
    return document
