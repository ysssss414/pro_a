"""Full-field review revisions of a verified, failed v7 Raw response.

Only candidate_inputs reconstructs the trusted archive. Recovery and authorship
do not grant acceptance, metadata authority, lifecycle selection or execution.
This first ingress admits independent Claims only; candidate Nodes stay deferred.
"""
import copy
from dataclasses import asdict
import json

from . import node_evidence_recovery as recovery, output_provider_record_v7 as v7
from .bounded_extraction import expand_source_analysis_wire_v3
from .candidate_origin import GOVERNANCE, SCOPE_FIELDS, require
from .evidence_binding import identity
from .research_quarantine import parse_prefix

VERSION = 'source-recovery-candidate-set-v1'
REVISION = 'recovered-full-field-revisions-v1'
ORIGIN_ENTRY_CONTRACT = {'version': 'recovered-v7-review-origin-v1', 'origin_version': VERSION,
    'completion_boundary': 'HUMAN_REVIEW_REQUIRED', 'semantic_review_required': True,
    'independent_claims_only': True, 'canonical_permission': False}
ENTRY_CONTRACT = {**ORIGIN_ENTRY_CONTRACT, 'version': 'recovered-v7-review-entry-v1',
    'lifecycle_contract': 'candidate-revision-lifecycle-v1'}


def _claim(obj, native, review, index, context):
    obj['normalized'] = copy.deepcopy(native['claims'][index])
    require(not (set(obj['normalized'].get('structured') or {}) &
        (set(GOVERNANCE) | {'candidate_origin', 'admission_v1', 'admission_basis_sha256'})),
        'PROVIDER_GOVERNANCE_FORBIDDEN')
    obj['evidence'] = [copy.deepcopy(p['binding']) for p in review['bindings']
                      if p['path'] == ['claims', index, 'evidence']]
    obj['context_dependencies'] = copy.deepcopy(review['claims'][index]['context_dependencies'])
    obj['review_reasons'] = copy.deepcopy(review['claims'][index]['review_reasons'])
    value = obj['normalized']
    require(set(value.get('related_node_ids', [])) <= set(context.known_node_ids),
            'CANDIDATE_UNKNOWN_NODE')
    obj['dependencies'] = [['nodes', n] for n in value.get('related_node_ids', [])]
    obj['dependencies'] += [['node_candidates', n] for n in value.get('related_candidate_names', [])]


def build(raw, scope, segment, catalog, context, series, plan, proposal, revisions,
          metadata_resolution=None, *, b1_context=None):
    require(set(scope) == SCOPE_FIELDS | {'context_sha256'} and scope['provider_record_version']==v7.VERSION
        and scope['source_sha256']==context.source_sha256 and scope['source_piece_id']==context.piece.piece_id
        and scope['series_id']==series.series_id and scope['series_sha256']==series.series_sha256
        and scope['segment_id']==segment.segment_id and scope['segment_sha256']==segment.segment_sha256,
        'CANDIDATE_SOURCE_BINDING_MISMATCH')
    artifact = recovery.recover(raw, proposal, series, segment, catalog, context,
                                plan=plan, b1_context=b1_context)
    require(type(revisions) is dict and set(revisions) ==
        {'version', 'recovery_identity', 'reviewer', 'reason', 'claims', 'nodes', 'matches'}
        and revisions['version'] == REVISION and revisions['recovery_identity'] == artifact['identity'],
        'RECOVERED_REVISION_IDENTITY_MISMATCH')
    require(all(type(revisions[k]) is str and revisions[k].strip() for k in ('reviewer', 'reason')),
            'CANDIDATE_REVISION_REASON_REQUIRED')
    original = artifact['projected_record']
    revised = copy.deepcopy(original)
    ids = set()
    require(type(revisions['claims']) is list and 0 < len(revisions['claims']) <= 100,
            'CANDIDATE_REVISION_INVALID')
    for child in revisions['claims']:
        require(type(child) is dict and set(child) == {'child_id', 'parent_index', 'parent_sha256',
            'previous_draft', 'previous_draft_sha256', 'record', 'reason', 'field_review'},
            'CANDIDATE_CHILD_INVALID')
        i = child['parent_index']
        require(type(i) is int and 0 <= i < len(original['claims']) and
            child['parent_sha256'] == identity(original['claims'][i]), 'CANDIDATE_PARENT_REVISION_MISMATCH')
        require(type(child['child_id']) is str and child['child_id'].strip() and child['child_id'] not in ids
            and type(child['reason']) is str and child['reason'].strip(), 'CANDIDATE_CHILD_INVALID')
        ids.add(child['child_id'])
        require(type(child['previous_draft']) is dict and child['previous_draft_sha256'] == identity(child['previous_draft'])
            and type(child['field_review']) is dict and set(child['field_review']) == set(child['record'])
            and all(type(v) is str and v.strip() for v in child['field_review'].values()),
            'RECOVERED_FIELD_REVIEW_REQUIRED')
        v7.lexical.validate_shape(child['previous_draft'], v7.record_schema()['properties']['claims']['items'])
    revised['claims'] = [copy.deepcopy(c['record']) for c in revisions['claims']]
    require(type(revisions['nodes']) is list, 'CANDIDATE_REVISION_INVALID')
    seen = set()
    for change in revisions['nodes']:
        require(type(change) is dict and set(change) == {'parent_index', 'parent_sha256', 'record', 'reason'},
                'RECOVERED_NODE_REVISION_INVALID')
        i = change['parent_index']
        require(type(i) is int and 0 <= i < len(original['node_candidates']) and i not in seen
            and change['parent_sha256'] == identity(original['node_candidates'][i])
            and type(change['reason']) is str and change['reason'].strip(), 'RECOVERED_NODE_REVISION_INVALID')
        seen.add(i)
        # Identity/support edits require a different contract; descriptions and
        # research rationales have an explicit, auditable path in this version.
        require({k:v for k,v in change['record'].items() if k not in ('description','maintenance_rationale','reason')}
            == {k:v for k,v in original['node_candidates'][i].items() if k not in ('description','maintenance_rationale','reason')},
            'RECOVERED_NODE_IDENTITY_EDIT_FORBIDDEN')
        revised['node_candidates'][i] = copy.deepcopy(change['record'])
    require(type(revisions['matches']) is list and len(revisions['matches']) == len(original['node_matches']),
            'RECOVERED_MATCH_DISPOSITION_REQUIRED')
    for i, change in enumerate(revisions['matches']):
        require(type(change) is dict and set(change) == {'parent_index','parent_sha256','disposition','reason'}
            and change['parent_index'] == i and change['parent_sha256'] == identity(original['node_matches'][i])
            and change['disposition'] in ('KEEP','DEFER') and type(change['reason']) is str
            and change['reason'].strip(), 'RECOVERED_MATCH_DISPOSITION_REQUIRED')
    revised['node_matches'] = [m for m,c in zip(original['node_matches'],revisions['matches']) if c['disposition']=='KEEP']
    content = json.dumps(revised, ensure_ascii=False)
    if b1_context is not None:
        from .b1_extraction import validate_record
        validate_record(content, b1_context, catalog, context, segment)
    result, review = v7.compile_result(content, series, segment, catalog, context, plan=plan)
    native = expand_source_analysis_wire_v3(json.loads(result.wire_json), catalog, context)
    objects = []
    for item in parse_prefix(raw)['objects']:
        obj = {**copy.deepcopy(item), 'observation_id': 'OBS_'+identity(
            [scope, artifact['raw_sha256'], item['family'], item['index'], item['object_sha256']]),
            'normalized': None, 'dependencies': [], 'evidence': [], 'errors': [], 'status': 'DEFER'}
        if item['family'] == 'claims':
            _claim(obj, artifact['native'], artifact['research_review'], item['index'], context)
        elif item['family'] == 'node_matches' and revisions['matches'][item['index']]['disposition']=='KEEP':
            obj['normalized'] = copy.deepcopy(artifact['native']['node_matches'][item['index']])
            _, binding = v7.resolve_intent(item['value']['evidence'], catalog, context)
            obj['evidence'] = [asdict(binding)]
            obj['status'] = 'SEMANTIC_REVIEW_REQUIRED'
        obj['revision_sha256'] = identity(obj)
        objects.append(obj)
    parents = {o['index']:o for o in objects if o['family']=='claims'}
    for i, child in enumerate(revisions['claims']):
        parent = parents[child['parent_index']]
        obj = copy.deepcopy(parent)
        _claim(obj, native, review, i, context)
        obj.update(observation_id='OBS_'+identity([parent['observation_id'],child['child_id'],REVISION]),
            parent={'observation_id':parent['observation_id'], 'revision_sha256':parent['revision_sha256'],
                    'raw_claim':copy.deepcopy(parent['value'])},
            semantic_revision={'version':REVISION, 'reviewer':revisions['reviewer'],
                'reason':revisions['reason'], 'child':copy.deepcopy(child)})
        # Real candidate dependencies remain visible, never silently erased.
        obj['status'] = 'DEFER' if child['record']['related_candidate_names'] else 'SEMANTIC_REVIEW_REQUIRED'
        obj['revision_sha256'] = identity({k:v for k,v in obj.items() if k!='revision_sha256'})
        objects.append(obj)
    for i, obj in enumerate(o for o in objects if o['family']=='node_candidates'):
        obj['normalized'] = copy.deepcopy(native['node_candidates'][i])
        obj['semantic_revision'] = next((copy.deepcopy(c) for c in revisions['nodes'] if c['parent_index']==i),None)
        obj['revision_sha256'] = identity({k:v for k,v in obj.items() if k!='revision_sha256'})
    metadata = artifact['native']['source_metadata']
    bound = {'processing_run_id':scope['run_id'], 'source_id':scope['source_id'],
        'source_sha256':scope['source_sha256'], 'pieces':[{'source_piece_id':scope['source_piece_id'],
        'series_id':scope['series_id']}], 'recovery_identities':[artifact['identity']]}
    if metadata_resolution is not None:
        from .source_metadata_authority import validate_resolution
        metadata = validate_resolution(metadata_resolution, bound_scope=bound)
    body = {'version':VERSION, 'scope':copy.deepcopy(scope), 'raw_sha256':artifact['raw_sha256'],
        'entry_contract':copy.deepcopy(ORIGIN_ENTRY_CONTRACT), 'recovery_request':copy.deepcopy(proposal),
        'recovery':{'version':recovery.VERSION, 'identity':artifact['identity'],
                    'support_mappings':artifact['support_mappings'], 'result_sha256':artifact['result']['result_sha256'],
                    'formal_accepted':False},
        'catalog_sha256':identity(asdict(catalog)), 'objects':objects, 'revisions':copy.deepcopy(revisions),
        'source_metadata':metadata, 'provider_source_metadata':artifact['native']['source_metadata'],
        'metadata_scope':bound, 'metadata_resolution':copy.deepcopy(metadata_resolution),
        'revised_record':revised, 'revised_record_sha256':identity(revised),
        'revised_result_sha256':result.result_sha256, 'proposed_governance':dict(GOVERNANCE),
        'coverage_authority':False, 'canonical_permission':False}
    return {**body,'identity':identity(body)}


def observation(document, obj):
    from .candidate_origin_v2 import observation as v2_observation
    projected = v2_observation(document,obj)
    # These are JSON object coordinates, not filesystem paths. The private
    # archive retains the original vocabulary; the existing disclosure guard
    # remains unchanged and every support occurrence is projected explicitly.
    mappings = []
    for item in document['recovery']['support_mappings']:
        mappings.append({'original_coordinate':item['original_path'],
            'original_property':item['original_property'], 'original_binding':item['original_binding'],
            'represented_by':[{'claim_coordinate':x['claim_path'],
                'relationship_coordinate':x['relationship_path'], 'candidate_name':x['candidate_name'],
                'claim_binding':x['claim_binding']} for x in item['represented_by']]})
    projected['lineage']['recovery']['support_mappings'] = copy.deepcopy(mappings)
    return projected
