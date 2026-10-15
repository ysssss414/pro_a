"""Isolated one-human/two-seal contracts; never invokes an Operator or real model."""
import copy
from concurrent.futures import ThreadPoolExecutor

import pytest

from pro_a.workbench.attribution import Attribution
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_policy import ReviewPolicy
from pro_a.workbench.unified_review import UnifiedReview, records
from test_candidate_advice_submission import advice_case, HUMAN, request
from test_mcp_controlled_write import client, no_operator_apply, submit_pair, writer


def plan(value, *, mode='dual', deferred=False, no_keep=False):
    if mode == 'single':
        policy = ReviewPolicy(value['reviews'])
        policy.select(value['handle'], 'SINGLE_MODEL_HUMAN', policy.context(value['handle']), HUMAN, confirm=True)
        opinion = {k: v for k, v in value['opinions']['A'].items() if k != 'reviewer_type'}
        writer(value, isolation_attested_by_operator=False, review_mode='SINGLE_MODEL_HUMAN').submit_reviewer_advice(value['handle'], **opinion)
    else:
        submit_pair(value)
    engine = UnifiedReview(value['config'])
    ctx = engine.context(value['handle'])
    native = [{'candidate_id': r['candidate_id'], 'content_sha256': r['content_sha256'],
               'decision': ('KEEP_NEEDS_REVIEW' if no_keep else 'KEEP') if r['candidate_type'] == 'CLAIM' else 'DEFER' if deferred else 'CREATE',
               'reason': 'Synthetic explicit human draft', 'target_node_id': ''} for r in ctx['candidates']]
    preview = engine.preview(value['handle'], native)
    attrs = [{'claim_id': cid, 'content_sha256': next(i['content_sha256'] for i in native if i['candidate_id'] == cid),
              'scope': c['scope'], 'outcome': 'NO_LINK', 'links': [], 'reason': 'Anonymous subject; do not infer company'}
             for cid, c in preview['universe']['claims'].items()]
    body = dict(binding=ctx['binding'], expected_revision=ctx['revision'], native_items=native, attribution_items=attrs, reason='One complete human plan')
    return engine, body


@pytest.mark.parametrize('mode', ['single', 'dual'])
def test_one_authenticated_approval_two_seals_and_replay(advice_case, monkeypatch, mode):
    value=advice_case; engine,body=plan(value,mode=mode)
    http,headers=client(value,monkeypatch)
    base='/api/workbench/v1/reviews/'+value['handle']+'/unified'
    frozen=http.post(base+'/proposals',headers=headers,json=body)
    assert frozen.status_code==200, frozen.text
    pid=frozen.json()['proposal_id']
    approval={'proposal_id':pid,'confirm':True}
    assert http.post(base+'/approval',json=approval,headers={'Origin':value['config'].origin}).status_code==403
    assert http.post(base+'/approval',json={**approval,'principal_type':'HUMAN_USER'},headers=headers).status_code==422
    result=http.post(base+'/approval',json=approval,headers=headers)
    assert result.status_code==200,result.text
    for _ in range(100):
        if result.json()['status']=='SEALED':break
        result=http.post(base+'/approval',json=approval,headers=headers)
        assert result.status_code==200,result.text
    assert result.json()['status']=='SEALED'
    assert http.post(base+'/approval',json=approval,headers=headers).json()==result.json()
    assert value['reviews'].read(value['handle'])['review']['status']=='SEALED'
    assert Attribution(value['config']).read(value['handle'])['status']=='SEALED'
    with engine.store.connect() as db:
        assert len(records(db,value['handle'],'UNIFIED_REVIEW_APPROVED'))==1
        assert len(records(db,value['handle'],'UNIFIED_REVIEW_COMPLETED'))==1
    assert value['config'].knowledge_db.read_bytes()==value['production']


@pytest.mark.parametrize('stage,stop', [('native',0),('native',1),('attribution',0),('attribution',1),('completed',0)])
def test_resume_exact_plan_and_block_legacy_writes(advice_case,monkeypatch,stage,stop):
    value=advice_case;engine,body=plan(value);pid=engine.prepare(value['handle'],**body)['proposal_id']
    service=engine.reviews if stage=='native' else engine.attribution
    original=service.mutate
    calls=0
    def crash(*args):
        nonlocal calls
        if calls==stop:raise RuntimeError('simulated process interruption')
        calls+=1
        return original(*args)
    if stage!='completed':monkeypatch.setattr(service,'mutate',crash)
    else:
        record=engine.batch.record
        def fail_record(c,h,k,v):
            if k=='UNIFIED_REVIEW_COMPLETED':raise RuntimeError('response checkpoint interruption')
            return record(c,h,k,v)
        monkeypatch.setattr(engine.batch,'record',fail_record)
    with pytest.raises(RuntimeError):engine.approve(value['handle'],pid,HUMAN,confirm=True)
    row=body['native_items'][0]
    with pytest.raises(BoundaryError,match='UNIFIED_APPROVAL_LOCKED'):
        value['reviews'].mutate(value['handle'],'decision',request(value,**{k:v for k,v in row.items() if k!='content_sha256'}),HUMAN)
    resumed=UnifiedReview(value['config']).approve(value['handle'],pid,{**HUMAN,'session_id':'new-login'},confirm=True)
    assert resumed['status']=='SEALED'
    assert UnifiedReview(value['config']).approve(value['handle'],pid,HUMAN,confirm=True)==resumed
    assert value['config'].knowledge_db.read_bytes()==value['production']


@pytest.mark.parametrize('fault', ['missing','content','node','role','duplicate','scope','excluded'])
def test_invalid_complete_plan_never_mutates_review(advice_case,fault):
    value=advice_case;engine,body=plan(value)
    if fault=='missing':body['native_items'].pop()
    elif fault=='content':body['native_items'][0]['content_sha256']='0'*64
    elif fault=='excluded':body['native_items'][0]['decision']='DROP'
    else:
        item=body['attribution_items'][0]
        node=next(iter(engine.preview(value['handle'],body['native_items'])['universe']['nodes']))
        item.update(outcome='LINK',links=[{'node_id':node,'role':'context'}])
        if fault=='node':item['links'][0]['node_id']='NODE_UNKNOWN'
        if fault=='role':item['links'][0]['role']='invented'
        if fault=='scope':item['scope']='changed'
        if fault=='duplicate':item.update(outcome='MULTI_LINK',links=item['links']*2)
    with pytest.raises(BoundaryError):engine.prepare(value['handle'],**body)
    assert value['reviews'].read(value['handle'])['review']['revision']==0
    with engine.store.connect() as db:assert not records(db,value['handle'],'UNIFIED_REVIEW_APPROVED')


@pytest.mark.parametrize('no_keep',[True,False])
def test_empty_targets_and_no_keep(advice_case,no_keep):
    value=advice_case;engine,body=plan(value,deferred=True,no_keep=no_keep)
    for row in body['attribution_items']:row['outcome']='DEFER'
    pid=engine.prepare(value['handle'],**body)['proposal_id']
    assert engine.approve(value['handle'],pid,HUMAN,confirm=True)['status']=='SEALED'
    ctx=Attribution(value['config']).context(value['handle'])
    assert not ctx['nodes']
    assert bool(ctx['claims'])!=no_keep


def test_racing_proposals_and_model_cannot_approve(advice_case):
    value=advice_case;engine,body=plan(value)
    first=engine.prepare(value['handle'],**body)['proposal_id']
    body['reason']='Different complete plan';second=engine.prepare(value['handle'],**body)['proposal_id']
    with pytest.raises(BoundaryError,match='HUMAN_USER_REQUIRED'):
        engine.approve(value['handle'],first,{'principal_type':'MODEL'},confirm=True)
    def approve(pid):
        try:return UnifiedReview(value['config']).approve(value['handle'],pid,HUMAN,confirm=True)['status']
        except BoundaryError as e:return str(e)
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(approve,[first,second]))
    assert sorted(results)==['BATCH_APPROVAL_CONFLICT','SEALED']
    assert value['config'].knowledge_db.read_bytes()==value['production']


def test_context_drift_and_plan_tampering_fail_before_approval(advice_case,monkeypatch):
    value=advice_case;engine,body=plan(value)
    frozen=engine.prepare(value['handle'],**body);pid=frozen['proposal_id']
    original=engine.batch.snapshot
    def drift(*args):
        result=list(original(*args));result[0]={**result[0],'context_sha256':'0'*64};return tuple(result)
    monkeypatch.setattr(engine.batch,'snapshot',drift)
    before=value['config'].state_db.read_bytes()
    with pytest.raises(BoundaryError,match='BATCH_BINDING_DRIFT'):engine.approve(value['handle'],pid,HUMAN,confirm=True)
    assert value['config'].state_db.read_bytes()==before
    monkeypatch.setattr(engine.batch,'snapshot',original)
    bad=copy.deepcopy(frozen);bad['proposal']['reason']='Unapproved replacement'
    monkeypatch.setattr(engine,'read',lambda *args:bad)
    # Public read verifies the immutable digest; approval also independently checks it.
    with pytest.raises(BoundaryError,match='BATCH_BINDING_DRIFT'):engine.approve(value['handle'],pid,HUMAN,confirm=True)
    assert value['config'].state_db.read_bytes()==before


def test_non_supported_claim_cannot_be_kept(advice_case):
    value=advice_case
    value['opinions']['B']['items'][0]['judgment']='UNCERTAIN'
    with pytest.raises(BoundaryError,match='CANDIDATE_SUPPORT_UNRESOLVED'):plan(value)
    assert value['reviews'].read(value['handle'])['review']['revision']==0
