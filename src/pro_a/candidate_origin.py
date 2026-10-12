"""Versioned candidate input from complete v4 responses, independent of Coverage.

Eligibility here permits semantic review, never acceptance or Canonical writes.
The Workbench producer supplies and revalidates the durable execution identity.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
import json
import re

from . import output_provider_record_v4 as v4
from .evidence_binding import (EVIDENCE_SELECTION_FIELDS, identity,
                               resolve_evidence_binding_v2, validate_catalog)
from .research_quarantine import FAMILIES, parse_prefix

VERSION = 'source-candidate-set-v1'
POLICY = 'independent-candidate-isolation-v1'
GOVERNANCE = {
    'admission_semantics': 'SOURCE_ASSERTION',
    'reality_support': 'UNVERIFIED',
    'current_view_use': 'CLUE_ONLY',
}
SCOPE_FIELDS = {
    'source_id', 'source_sha256', 'source_ingestion_time', 'run_id', 'runtime_identity',
    'series_id', 'series_sha256', 'source_piece_id', 'segment_id',
    'segment_sha256', 'attempt_id', 'request_sha256',
    'configuration_sha256', 'provider_record_version', 'raw_artifact_sha256',
    'outcome_sha256',
}


def require(value, code):
    if not value:
        raise ValueError(code)


def build(raw, scope, segment, catalog, context, revisions=None):
    """Preserve every original object and propagate only declared dependencies.

    A byte range proves response membership, not support of a natural-language
    assertion. Support must subsequently be judged on the frozen review packet.
    """
    require(type(scope) is dict and set(scope) == SCOPE_FIELDS, 'CANDIDATE_SCOPE_INVALID')
    require(all(type(scope[k]) is str and re.fullmatch('[0-9a-f]{64}', scope[k])
                for k in SCOPE_FIELDS if k.endswith('sha256')),
            'CANDIDATE_SCOPE_DIGEST_INVALID')
    require(scope['provider_record_version'] == v4.VERSION, 'CANDIDATE_PROTOCOL_UNSUPPORTED')
    require(scope['source_sha256'] == context.source_sha256
            and scope['source_piece_id'] == context.piece.piece_id
            and scope['segment_id'] == segment.segment_id
            and scope['segment_sha256'] == segment.segment_sha256
            and scope['series_id'] == segment.series_id, 'CANDIDATE_SOURCE_BINDING_MISMATCH')
    validate_catalog(catalog, context)
    parsed = parse_prefix(raw)
    require(parsed['complete'], 'CANDIDATE_COMPLETE_JSON_REQUIRED')
    document = parsed['document']
    schema = v4.record_schema()
    require(set(document) == set(schema['properties']), 'CANDIDATE_CONTAINER_INVALID')
    for key in set(document) - set(FAMILIES):
        v4.validate_shape(document[key], schema['properties'][key])
    require(all(type(document[f]) is list for f in FAMILIES), 'CANDIDATE_CONTAINER_INVALID')
    require(len(document['claims']) <= 100 and len(document['node_candidates']) <= 100,
            'CANDIDATE_OBJECT_LIMIT')
    owned = set(segment.assigned_evidence_refs)
    acknowledgements = [a['evidence_ref'] for a in document['evidence_acknowledgements']]
    require(len(acknowledgements) == len(owned) and set(acknowledgements) == owned,
            'CANDIDATE_OWNERSHIP_SCOPE_INVALID')
    empty = {**copy.deepcopy(document), **{f: [] for f in FAMILIES}}
    # The shared metadata is validated once; corrupt shared scope blocks all.
    metadata = v4.normalize_record(json.dumps(empty))['source_metadata']
    raw_sha = hashlib.sha256(raw).hexdigest()
    revisions = revisions or {}
    require(type(revisions) is dict, 'CANDIDATE_REVISION_INVALID')
    objects = []
    for original in parsed['objects']:
        family, index, value = original['family'], original['index'], original['value']
        obj = copy.deepcopy(original)
        obj.update(observation_id='OBS_' + identity([scope, raw_sha, family, index,
                    original['object_sha256']]), dependencies=[], errors=[], evidence=[],
                   status='SEMANTIC_REVIEW_REQUIRED', normalized=None)
        try:
            value = copy.deepcopy(value)
            if obj['observation_id'] in revisions:
                revision = revisions[obj['observation_id']]
                require(family == 'claims' and type(revision) is dict and set(revision) ==
                    {'evidence_ref', 'source_start', 'source_end', 'reason', 'reviewer'}, 'CANDIDATE_REVISION_INVALID')
                require(all(type(revision[k]) is str and revision[k].strip() for k in ('reason', 'reviewer')),
                        'CANDIDATE_REVISION_REASON_REQUIRED')
                unit = next((u for u in catalog.units if u.evidence_ref == revision['evidence_ref']), None)
                lo, hi = revision['source_start'], revision['source_end']
                require(unit is not None and unit.evidence_ref in owned and type(lo) is int and type(hi) is int
                        and unit.source_start <= lo < hi <= unit.source_end, 'CANDIDATE_EXACT_RANGE_INVALID')
                selector = context.piece.source_text[lo:hi]
                positions = [m.start() for m in re.finditer('(?=' + re.escape(selector) + ')', unit.exact_text)]
                require(lo - unit.source_start in positions, 'CANDIDATE_EXACT_RANGE_INVALID')
                value['evidence'] = {'evidence_ref': unit.evidence_ref, 'selection_mode': 'RAW_SUBSPAN',
                    'selector': selector, 'occurrence': str(positions.index(lo - unit.source_start) + 1)}
                value['evidence_pointer'] = unit.locator
            v4.validate_shape(value, schema['properties'][family]['items'])
            isolated = {**copy.deepcopy(empty), family: [copy.deepcopy(value)]}
            normalized = v4.normalize_record(json.dumps(isolated, ensure_ascii=False))[family][0]
            if family == 'claims':
                require(not (set(normalized.get('structured') or {}) &
                             (set(GOVERNANCE) | {'admission_v1', 'admission_basis_sha256'})),
                        'PROVIDER_GOVERNANCE_FORBIDDEN')
                require(bool(normalized['statement'].strip()), 'CANDIDATE_STATEMENT_REQUIRED')
                obj['dependencies'] = [['node_candidates', name] for name in normalized.get('related_candidate_names', [])]
                obj['dependencies'] += [['nodes', node] for node in normalized.get('related_node_ids', [])]
            if family in ('claims', 'node_matches'):
                bound = resolve_evidence_binding_v2(
                    {k: v for k, v in normalized.items() if k in EVIDENCE_SELECTION_FIELDS}, catalog, context)
                require(bound.evidence_ref in owned, 'CANDIDATE_EVIDENCE_OUTSIDE_OWNER')
                obj['evidence'].append(asdict(bound))
            if family in ('node_candidates', 'source_references'):
                require(normalized['ownership_evidence_ref'] in owned, 'CANDIDATE_EVIDENCE_OUTSIDE_OWNER')
            if family == 'node_candidates':
                require(bool(normalized['canonical_name'].strip()), 'CANDIDATE_NAME_REQUIRED')
                obj['dependencies'] = [['nodes', node] for node in normalized.get('suggested_parent_node_ids', [])]
                for fields in (normalized, normalized.get('preserved_fields') or {}):
                    if 'evidence_ref' in fields:
                        bound = resolve_evidence_binding_v2(
                            {k: v for k, v in fields.items() if k in EVIDENCE_SELECTION_FIELDS}, catalog, context)
                        require(bound.evidence_ref in owned, 'CANDIDATE_EVIDENCE_OUTSIDE_OWNER')
                        obj['evidence'].append(asdict(bound))
            if family == 'node_matches':
                require(normalized['node_id'] in context.known_node_ids, 'CANDIDATE_UNKNOWN_NODE')
            if family == 'relation_candidates':
                # Relations are not part of this admission contract's write set.
                raise ValueError('CANDIDATE_RELATION_DEFERRED')
            obj['normalized'] = normalized
        except (ValueError, KeyError, TypeError) as error:
            obj['errors'].append(str(error) if isinstance(error, ValueError) else 'CANDIDATE_OBJECT_INVALID')
            obj['status'] = 'ISOLATED'
        objects.append(obj)
    candidates = {}
    for obj in objects:
        if (obj['family'] == 'node_candidates' and isinstance(obj['value'], dict)
                and isinstance(obj['value'].get('canonical_name'), str)):
            candidates.setdefault(obj['value'].get('canonical_name'), []).append(obj)
    node_matches = {}
    for obj in objects:
        if (obj['family'] == 'node_matches' and isinstance(obj['value'], dict)
                and isinstance(obj['value'].get('node_id'), str)):
            node_matches.setdefault(obj['value'].get('node_id'), []).append(obj)
    for group in candidates.values():
        if len(group) > 1:
            for obj in group:
                obj['status'] = 'ISOLATED'
                obj['errors'].append('CANDIDATE_IDENTITY_AMBIGUOUS')
    # Resolve candidate prerequisites before Claims, independent of root order.
    for family_order in ('node_candidates', 'claims'):
        for obj in (o for o in objects if o['family'] == family_order):
            for family, target in obj['dependencies']:
                if family == 'nodes':
                    valid = target in context.known_node_ids and all(
                        m['status'] != 'ISOLATED' for m in node_matches.get(target, []))
                else:
                    matches = candidates.get(target, [])
                    valid = len(matches) == 1 and matches[0]['status'] != 'ISOLATED'
                if not valid:
                    obj['errors'].append('CANDIDATE_DEPENDENCY_UNRESOLVED')
                    obj['status'] = 'ISOLATED'
    require(set(revisions) <= {o['observation_id'] for o in objects}, 'CANDIDATE_REVISION_TARGET_INVALID')
    require(all(o['status'] != 'ISOLATED' for o in objects if o['observation_id'] in revisions),
            'CANDIDATE_REVISION_REJECTED')
    for family_order in ('node_matches', 'node_candidates', 'claims', 'relation_candidates', 'source_references'):
        for obj in (o for o in objects if o['family'] == family_order):
            prerequisite = [candidates[name][0]['revision_sha256'] for family, name in obj['dependencies']
                            if family == 'node_candidates' and len(candidates.get(name, [])) == 1]
            prerequisite += [m['revision_sha256'] for family, name in obj['dependencies']
                             if family == 'nodes' for m in node_matches.get(name, [])]
            obj['revision_sha256'] = identity({**{k: obj[k] for k in
                ('observation_id', 'normalized', 'evidence', 'dependencies', 'status', 'errors')},
                'prerequisite_revisions': prerequisite, 'range_revision': revisions.get(obj['observation_id'])})
    body = {'version': VERSION, 'scope': copy.deepcopy(scope),
            'raw_sha256': raw_sha, 'catalog_sha256': identity(asdict(catalog)),
            'source_metadata': metadata, 'objects': objects,
            'proposed_governance': dict(GOVERNANCE),
            'coverage_authority': False, 'canonical_permission': False}
    if revisions:
        body.update(revisions=copy.deepcopy(revisions),
                    original_identity=build(raw, scope, segment, catalog, context)['identity'])
    return {**body, 'identity': identity(body)}


def verify(document, raw, scope, segment, catalog, context):
    require(document == build(raw, scope, segment, catalog, context), 'CANDIDATE_ORIGIN_DRIFT')
    return document


def semantic_projection(documents, excluded_keys=()):
    """Batch exact eligible observations without granting support or Node authority."""
    from .analyzer import SourceAnalysis
    require(bool(documents), 'CANDIDATE_INPUT_REQUIRED')
    sources = {(d['scope']['source_id'], d['scope']['source_sha256']) for d in documents}
    require(len(sources) == 1, 'CANDIDATE_SOURCE_CONFLICT')
    require(len({identity(d['source_metadata']) for d in documents}) == 1,
            'CANDIDATE_SOURCE_METADATA_CONFLICT')
    claims, matches, nodes, refs = [], [], [], []
    seen = {}
    for document in documents:
        require(document.get('version') == VERSION and document.get('identity') == identity(
            {k: v for k, v in document.items() if k != 'identity'}), 'CANDIDATE_ORIGIN_DRIFT')
        for obj in document['objects']:
            if obj['status'] != 'SEMANTIC_REVIEW_REQUIRED':
                continue
            value = copy.deepcopy(obj['normalized'])
            value.pop('ownership_evidence_ref', None)
            if obj['family'] in ('claims', 'node_matches'):
                binding = obj['evidence'][0]
                value = {k: v for k, v in value.items() if k not in EVIDENCE_SELECTION_FIELDS}
                value.update(evidence_excerpt=binding['evidence_excerpt'],
                             evidence_pointer=binding['evidence_pointer'], evidence_validated=True)
            if obj['family'] == 'claims':
                # Final native construction can normalize text; the final Packet
                # freezes that result together with the original observation.
                key = identity({'source': list(sources)[0], 'content': {k: v for k, v in value.items()
                    if k not in ('confidence', 'evidence_validated', 'evidence_pointer', 'related_node_ids', 'related_candidate_names')},
                    'subjects': sorted(value.get('related_node_ids', [])),
                    'candidates': sorted([{k: v for k, v in n['normalized'].items() if k != 'confidence'}
                        for n in document['objects']
                        if n['family'] == 'node_candidates' and n['status'] == 'SEMANTIC_REVIEW_REQUIRED'
                        and n['normalized']['canonical_name'] in value.get('related_candidate_names', [])],
                        key=lambda n: n['canonical_name']),
                    'publication_time': document['source_metadata'].get('publication_time') or '',
                    'evidence': [{k: b[k] for k in ('source_start', 'source_end', 'evidence_excerpt', 'source_locator')}
                                 for b in obj['evidence']]})
                if key in excluded_keys:
                    continue
                observation = {'set_identity': document.get('original_identity', document['identity']), 'observation_id': obj['observation_id'],
                               'revision_sha256': obj['revision_sha256'], 'dependencies': obj['dependencies']}
                if key in seen:
                    seen[key]['candidate_observations'].append(observation)
                else:
                    value['candidate_key'] = key
                    value['candidate_observations'] = [observation]
                    claims.append(value)
                    seen[key] = value
            elif obj['family'] == 'node_matches':
                matches.append(value)
            elif obj['family'] == 'node_candidates':
                nodes.append(value)
            elif obj['family'] == 'source_references':
                refs.append(value)
    # Exact repeated ancillary objects from multiple Attempts remain one native
    # proposal; every original observation is retained in the frozen documents.
    for rows in (nodes, matches, refs):
        rows[:] = {identity(row): row for row in rows}.values()
    if excluded_keys:
        required_nodes = {name for c in claims for name in c.get('related_candidate_names', [])}
        nodes = [n for n in nodes if n['canonical_name'] in required_nodes]
    require(bool(claims), 'CANDIDATE_NO_ELIGIBLE_CLAIMS')
    return SourceAnalysis(copy.deepcopy(documents[0]['source_metadata']), matches, nodes, claims, refs)
