"""Accepted v7 review inputs and explicit, non-authoritative child revisions.

Only candidate_inputs can attest durable acceptance. This pure projection is
reconstructed against that archive at every formal ingress; hashes are not grants.
"""
import copy
import hashlib
from dataclasses import asdict

from . import output_provider_record_v7 as v7
from .bounded_extraction import expand_source_analysis_wire_v3
from .candidate_origin import GOVERNANCE, SCOPE_FIELDS, require
from .evidence_binding import identity
from .research_quarantine import parse_prefix

VERSION = 'source-candidate-set-v2'
REVISION = 'controlled-claim-children-v1'
ENTRY = 'accepted-v7-review-entry-v1'
ORIGIN_ENTRY_CONTRACT = {'version': ENTRY, 'origin_version': VERSION,
    'accepted_record_version': v7.VERSION, 'completion_boundary': 'HUMAN_REVIEW_REQUIRED',
    'semantic_review_required': True, 'canonical_permission': False}
ENTRY_CONTRACT = {**ORIGIN_ENTRY_CONTRACT, 'version': 'accepted-v7-review-entry-v2',
    'lifecycle_contract': 'candidate-revision-lifecycle-v1'}


def build(raw, scope, segment, catalog, context, series, plan, acceptance, revisions=None, metadata_resolution=None):
    import json
    require(set(scope) == SCOPE_FIELDS | {'context_sha256'} and scope['provider_record_version'] == v7.VERSION,
            'CANDIDATE_SCOPE_INVALID')
    require(scope['source_sha256'] == context.source_sha256
            and scope['source_piece_id'] == context.piece.piece_id
            and scope['series_id'] == series.series_id and scope['series_sha256'] == series.series_sha256
            and scope['segment_id'] == segment.segment_id and scope['segment_sha256'] == segment.segment_sha256,
            'CANDIDATE_SOURCE_BINDING_MISMATCH')
    result, review = v7.compile_result(raw.decode('utf-8'), series, segment, catalog, context, plan=plan)
    require(acceptance['attempt_id'] == scope['attempt_id']
            and acceptance['result_sha256'] == result.result_sha256
            and acceptance['result_type'] == 'COMPLETE', 'CANDIDATE_ACCEPTED_RESULT_REQUIRED')
    native = expand_source_analysis_wire_v3(json.loads(result.wire_json), catalog, context)
    parsed = parse_prefix(raw)
    require(parsed['complete'], 'CANDIDATE_COMPLETE_JSON_REQUIRED')
    raw_sha = hashlib.sha256(raw).hexdigest()
    revisions = copy.deepcopy(revisions or {})
    require(type(revisions) is dict, 'CANDIDATE_REVISION_INVALID')
    objects = []
    for original in parsed['objects']:
        family, index = original['family'], original['index']
        obj = {**copy.deepcopy(original), 'observation_id': 'OBS_' + identity(
            [scope, raw_sha, family, index, original['object_sha256']]),
            'normalized': copy.deepcopy(native[family][index]) if family in native else None,
            'dependencies': [], 'evidence': [], 'errors': [], 'status': 'SEMANTIC_REVIEW_REQUIRED'}
        if family == 'claims':
            require(not (set(obj['normalized'].get('structured') or {}) &
                (set(GOVERNANCE) | {'candidate_origin', 'admission_v1', 'admission_basis_sha256'})),
                'PROVIDER_GOVERNANCE_FORBIDDEN')
            obj['evidence'] = [copy.deepcopy(p['binding']) for p in review['bindings']
                              if p['path'] == ['claims', index, 'evidence']]
            obj['context_dependencies'] = copy.deepcopy(review['claims'][index]['context_dependencies'])
            obj['review_reasons'] = copy.deepcopy(review['claims'][index]['review_reasons'])
            obj['dependencies'] = [['nodes', n] for n in obj['normalized'].get('related_node_ids', [])]
            obj['dependencies'] += [['node_candidates', n] for n in obj['normalized'].get('related_candidate_names', [])]
        elif family == 'relation_candidates':
            obj['status'] = 'DEFER'
        obj['revision_sha256'] = identity(obj)
        objects.append(obj)
    parents = {o['observation_id']: o for o in objects if o['family'] == 'claims'}
    require(set(revisions) <= set(parents), 'CANDIDATE_REVISION_TARGET_INVALID')
    for parent_id, revision in sorted(revisions.items()):
        parent = parents[parent_id]
        require(type(revision) is dict and set(revision) == {'version', 'parent_revision_sha256', 'children', 'reason', 'reviewer'}
                and revision['version'] == REVISION and revision['parent_revision_sha256'] == parent['revision_sha256'],
                'CANDIDATE_PARENT_REVISION_MISMATCH')
        require(all(type(revision[k]) is str and revision[k].strip() for k in ('reason', 'reviewer')),
                'CANDIDATE_REVISION_REASON_REQUIRED')
        children = revision['children']
        require(type(children) is list and len(children) <= 20, 'CANDIDATE_REVISION_INVALID')
        ids = set()
        for child in children:
            require(type(child) is dict and set(child) == {'child_id', 'statement', 'fact_time', 'assumption', 'status', 'context_dependencies'}
                    and all(type(child[k]) is str for k in ('child_id', 'statement', 'fact_time', 'assumption', 'status'))
                    and child['child_id'].strip() and child['statement'].strip()
                    and child['status'] in ('SEMANTIC_REVIEW_REQUIRED', 'DEFER', 'UNCERTAIN')
                    and child['child_id'] not in ids, 'CANDIDATE_CHILD_INVALID')
            ids.add(child['child_id'])
            derived = copy.deepcopy(parent)
            derived['normalized'].update({k: child[k] for k in ('statement', 'fact_time', 'assumption')})
            derived['status'] = child['status']
            # Additional context is located using v7/v2, never promoted to Primary.
            deps = child['context_dependencies']
            schema = v7.record_schema()['properties']['claims']['items']['properties']['research_review']['properties']['context_dependencies']
            v7.lexical.validate_shape(deps, schema)
            for dependency in deps:
                _, bound = v7.resolve_intent(dependency['evidence'], catalog, context)
                derived['context_dependencies'].append({**copy.deepcopy(dependency),
                    'location': {'binding': asdict(bound), 'role': 'CONTEXT'},
                    'relationship_authorization': 'NOT_ESTABLISHED'})
            derived['parent'] = {'observation_id': parent_id, 'revision_sha256': parent['revision_sha256'],
                                 'raw_claim': copy.deepcopy(parent['value'])}
            derived['semantic_revision'] = {**copy.deepcopy(revision), 'child': copy.deepcopy(child)}
            derived['semantic_revision'].pop('children')
            derived['observation_id'] = 'OBS_' + identity([parent_id, child['child_id'], REVISION])
            derived['revision_sha256'] = identity({k: v for k, v in derived.items() if k != 'revision_sha256'})
            objects.append(derived)
        parent['status'] = 'DEFER'  # Preserve raw parent; never admit parent and children implicitly.
    metadata = native['source_metadata']
    if metadata_resolution is not None:
        from .source_metadata_authority import scope as metadata_scope, validate_resolution
        bound = metadata_scope(scope['run_id'], scope['source_id'], scope['source_sha256'],
            [{'source_piece_id': scope['source_piece_id'], 'series_id': scope['series_id']}],
            [acceptance['result_sha256']])
        metadata = validate_resolution(metadata_resolution, bound_scope=bound)
    body = {'version': VERSION, 'scope': copy.deepcopy(scope), 'acceptance': copy.deepcopy(acceptance),
        'entry_contract': copy.deepcopy(ORIGIN_ENTRY_CONTRACT), 'raw_sha256': raw_sha,
        'catalog_sha256': identity(asdict(catalog)), 'research_review_sha256': identity(review),
        'source_metadata': metadata, 'provider_source_metadata': native['source_metadata'],
        'metadata_resolution': copy.deepcopy(metadata_resolution), 'objects': objects, 'revisions': revisions,
        'proposed_governance': dict(GOVERNANCE), 'coverage_authority': False, 'canonical_permission': False}
    return {**body, 'identity': identity(body)}


def observation(document, obj):
    scope = copy.deepcopy(document['scope'])
    runtime = scope['runtime_identity']
    scope['runtime_identity'] = {k: runtime[k] for k in
        ('runtime_sha256', 'git_sha', 'domain_code_sha256', 'phase4_processing_code_sha256')}
    scope['runtime_identity']['output_contract_sha256'] = identity(runtime['whole_piece_output_decomposition'])
    scope['schema_sha256'] = runtime['whole_piece_output_decomposition']['tool_schema_sha256']
    # The private archive retains the complete runtime and resolver attachment.
    # P0 gets their frozen identities and exact evidence, without paths or budget
    # schema keys forbidden by the existing disclosure boundary.
    contexts = [{**{k: copy.deepcopy(v) for k, v in d.items() if k not in ('location', 'relationship_authorization')},
                 'relationship_status': d['relationship_authorization'],
                 'location': {'binding': copy.deepcopy(d['location']['binding']), 'role': 'CONTEXT'}}
                for d in obj['context_dependencies']]
    return {'set_identity': document['identity'], 'observation_id': obj['observation_id'],
        'revision_sha256': obj['revision_sha256'], 'dependencies': obj['dependencies'],
        'lineage': {'scope': scope, 'acceptance': {k: v for k, v in document['acceptance'].items() if k != 'artifact_relative'},
            'entry_contract': copy.deepcopy(document['entry_contract']),
            'raw_sha256': document['raw_sha256'], 'raw_claim': copy.deepcopy(obj['value']),
            'parent': copy.deepcopy(obj.get('parent')), 'semantic_revision': copy.deepcopy(obj.get('semantic_revision')),
            'primary_evidence': copy.deepcopy(obj['evidence']),
            'context_dependencies': contexts,
            'source_metadata': copy.deepcopy(document['source_metadata']),
            'provider_source_metadata': copy.deepcopy(document['provider_source_metadata']),
            'metadata_resolution': copy.deepcopy(document['metadata_resolution']),
            'review_reasons': copy.deepcopy(obj['review_reasons']),
            'semantic_status': 'NOT_ESTABLISHED', 'canonical_permission': False}}
