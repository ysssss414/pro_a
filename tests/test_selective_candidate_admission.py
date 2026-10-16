"""Explicit small v4 subsets, synthetic metadata decisions, no production authority."""
import copy
import pytest
from pro_a import candidate_origin as origin
from pro_a.evidence_binding import identity
from pro_a.source_metadata_authority import (candidate_resolution, authorize_resolution,
    DECISION_VERSION, MetadataAuthorityError)
from test_candidate_origin import fixture, build


def inputs():
    values=fixture(); values[0]['claims']=[]
    for i in range(6):
        c=copy.deepcopy(fixture()[0]['claims'][0])
        c.update(statement=f'Synthetic independent assertion {i}',related_candidate_names=[],related_node_ids=[])
        values[0]['claims'].append(c)
    doc=build(values)
    accepted=[{'set_identity':doc['identity'],'result_sha256':'a'*64}]
    candidate=candidate_resolution(origin.selection_scope([doc],accepted),[])
    resolution=authorize_resolution(candidate,{'version':DECISION_VERSION,
        'candidate_identity':candidate['identity'],'scope_sha256':identity(candidate['scope']),
        'approved':True,'actor':'TEST_ONLY_HUMAN','reason':'Synthetic decision only',
        'decision_reference':'TEST_ONLY_RECEIPT','values':{'title':'Synthetic source',
        'publication_time':'','author':'','organization':'','source_rank':'UNRANKED','source_origin_type':'unknown'},
        'summary_policy':'PRESERVE_ALL_VARIANTS_UNRESOLVED'})
    selected=[o['observation_id'] for o in doc['objects'] if o['family']=='claims'][:5]
    plan=origin.make_selection([doc],selected,accepted,'b'*64,resolution)
    return doc,plan,candidate


def test_subset_preserves_origin_and_never_claims_coverage_or_authority():
    doc,plan,_=inputs();before=copy.deepcopy(doc)
    projected=origin.semantic_projection([doc],selection=plan)
    assert len(projected.claims)==5 and not projected.node_candidates
    assert projected.source_metadata['summary']==''
    assert doc==before and plan['coverage_authority'] is False and plan['canonical_permission'] is False
    assert {o['observation_id'] for c in projected.claims for o in c['candidate_observations']}=={
        o['observation_id'] for o in plan['observations']}
    assert len(origin.semantic_projection([doc]).claims)==6


def test_unapproved_metadata_and_vote_are_rejected():
    doc,plan,candidate=inputs()
    plan['metadata_resolution']=candidate
    plan['identity']=identity({k:v for k,v in plan.items() if k!='identity'})
    with pytest.raises(MetadataAuthorityError,match='NEEDS_HUMAN_RESOLUTION'):
        origin.semantic_projection([doc],selection=plan)


@pytest.mark.parametrize('damage',['missing','duplicate','revision','authority','source','result'])
def test_selection_tampering_fails_closed(damage):
    doc,plan,_=inputs()
    if damage=='missing':plan['observations'].pop()
    if damage=='duplicate':plan['observations'][-1]=plan['observations'][0]
    if damage=='revision':plan['observations'][0]['revision_sha256']='0'*64
    if damage=='authority':plan['canonical_permission']=True
    if damage=='source':plan['document_identities']=['0'*64]
    if damage=='result':plan['accepted_results'][0]['result_sha256']='0'*64
    plan['identity']=identity({k:v for k,v in plan.items() if k!='identity'})
    with pytest.raises(ValueError):origin.semantic_projection([doc],selection=plan)


def test_isolated_dependency_cannot_be_selected_even_with_resealed_document():
    doc,plan,_=inputs()
    target=next(o for o in doc['objects'] if o['observation_id']==plan['observations'][0]['observation_id'])
    target['status']='ISOLATED';target['errors']=['CANDIDATE_DEPENDENCY_UNRESOLVED']
    doc['identity']=identity({k:v for k,v in doc.items() if k!='identity'})
    with pytest.raises(ValueError):
        origin.make_selection([doc],[o['observation_id'] for o in plan['observations']],
            [{'set_identity':doc['identity'],'result_sha256':'a'*64}], 'b'*64,plan['metadata_resolution'])


def test_exact_candidate_keys_and_duplicate_exclusion_remain_stable():
    doc,plan,_=inputs();projected=origin.semantic_projection([doc],selection=plan)
    keys=[c['candidate_key'] for c in projected.claims]
    assert len(origin.semantic_projection([doc],keys[:1],plan).claims)==4
    with pytest.raises(ValueError,match='CANDIDATE_NO_ELIGIBLE_CLAIMS'):
        origin.semantic_projection([doc],keys,plan)
    assert origin.semantic_projection([doc],selection=plan).claims==projected.claims


def test_human_metadata_still_requires_valid_protocol_values():
    doc,plan,candidate=inputs()
    decision=copy.deepcopy(plan['metadata_resolution']['human_decision'])
    decision['values']['source_rank']='MODEL_CERTIFIED_FACT'
    plan['metadata_resolution']=authorize_resolution(candidate,decision)
    plan['identity']=identity({k:v for k,v in plan.items() if k!='identity'})
    with pytest.raises(ValueError):origin.semantic_projection([doc],selection=plan)


def test_v7_is_not_misrepresented_as_v4():
    doc,plan,_=inputs()
    doc['scope']['provider_record_version']='whole-piece-output-batch-provider-record-v7'
    doc['identity']=identity({k:v for k,v in doc.items() if k!='identity'})
    with pytest.raises(ValueError,match='SELECTION_INPUT_IDENTITY_INVALID'):
        origin.selection_scope([doc],[{'set_identity':doc['identity'],'result_sha256':'a'*64}])


def test_unselected_attempt_node_matches_do_not_expand_dependency_closure():
    values=fixture(); node=values[0]['node_matches'][0]['node_id']
    claim=copy.deepcopy(values[0]['claims'][0]);claim['related_candidate_names']=[];claim['related_node_ids']=[node]
    values[0]['claims']=[{**copy.deepcopy(claim),'statement':f'Synthetic selected assertion {i}'} for i in range(5)]
    first=build(values)
    other=copy.deepcopy(values);other[1]['attempt_id']='ATTEMPT_UNSELECTED'
    other[0]['node_matches'][0]['reason']='Unselected attempt observation must remain outside projection'
    second=build(other);docs=[first,second]
    accepted=[{'set_identity':d['identity'],'result_sha256':x*64} for d,x in zip(docs,('a','b'))]
    candidate=candidate_resolution(origin.selection_scope(docs,accepted),[])
    decision=copy.deepcopy(inputs()[1]['metadata_resolution']['human_decision'])
    decision.update(candidate_identity=candidate['identity'],scope_sha256=identity(candidate['scope']))
    resolution=authorize_resolution(candidate,decision)
    ids=[o['observation_id'] for o in first['objects'] if o['family']=='claims']
    plan=origin.make_selection(docs,ids,accepted,'c'*64,resolution)
    projection=origin.semantic_projection(docs,selection=plan)
    assert len(projection.claims)==5 and len(projection.node_matches)==1
    assert all(m['reason']!='Unselected attempt observation must remain outside projection' for m in projection.node_matches)
