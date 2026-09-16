from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

import pytest

from pro_a.operational_contract import identity, predicted_diff, readonly, sealed, verify_envelope
from pro_a.operational_operator import Operator, OperatorConfig
from pro_a.operational_qualification import qualify
from pro_a.production_promotion import canonical_sha256
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from workbench_stage2_fixture import (stage2_fixture, CLAIM, CLAIM_TWO, CLAIM_THREE, CREATE_NODE, REUSE_NODE, REVIEWER, IDENTITY)


@pytest.fixture
def case(tmp_path):
    value=stage2_fixture(tmp_path)
    value['service']=Attribution(value['config'])
    value['operator']=Operator(OperatorConfig(value['config'],tmp_path/'operator/ledger.sqlite3'))
    value['operator'].initialize()
    return value


def operation(case, **extra):
    state=case['service'].read(case['handle'])
    return {'basis_id':state['basis_id'],'expected_revision':state['revision'],'operation_id':uuid.uuid4().hex,
            'reviewer':REVIEWER,'reason':'Explicit synthetic human attribution.',**extra}


def decide(case, claim=CLAIM, outcome='LINK', links=None, **extra):
    context=case['service'].context(case['handle'])
    body=operation(case,claim_id=claim,outcome=outcome,links=links if links is not None else [{'node_id':CREATE_NODE,'role':'subject'}],
                   scope=context['claims'].get(claim,{}).get('scope',''),**extra)
    return case['service'].mutate(case['handle'],'SAVE',body,IDENTITY)


def complete(case, third='NO_LINK'):
    decide(case)
    decide(case,CLAIM_TWO,'MULTI_LINK',[{'node_id':CREATE_NODE,'role':'context'},{'node_id':REUSE_NODE,'role':'related'}])
    decide(case,CLAIM_THREE,third,[])
    case['service'].mutate(case['handle'],'SEAL',operation(case,confirm=True),IDENTITY)
    return case['service'].read(case['handle'])['sidecar']['object_id']


def package(case):
    return qualify(case['config'],case['handle'],complete(case))


def test_explicit_attribution_qualification_apply_and_reconciliation(case):
    before=identity(case['config'].knowledge_db)
    envelope=package(case)
    assert envelope['shadow']['phase3d_validation']['production_final_apply_rejection']=='FINAL_PAYLOAD_DOCUMENT_TYPE_MISMATCH'
    assert not envelope['shadow']['payload']['link_operations']
    source=next(r['row'] for r in envelope['mutations'] if r['table']=='sources')
    assert 'summary' not in json.loads(source['metadata_json'])
    assert identity(case['config'].knowledge_db)==before
    operator=case['operator'];eid=envelope['object_id']
    operator.register(eid,confirm=eid)
    receipt=operator.execute(eid,confirm=eid)
    assert receipt['status']=='EXECUTED' and receipt['actual_mutation_counts']['claim_node_links']==3
    assert operator.reconcile(eid)==receipt
    assert case['service'].read(case['handle'])['receipt']==receipt
    with closing(readonly(case['config'].knowledge_db)) as connection:
        rows=[tuple(r) for r in connection.execute('SELECT c.source_id,c.claim_id,l.node_id,l.role FROM claims c JOIN claim_node_links l ON l.claim_id=c.claim_id ORDER BY c.claim_id,l.node_id')]
        assert len(rows)==3 and {r[2] for r in rows}=={CREATE_NODE,REUSE_NODE}
        assert connection.execute('SELECT count(*) FROM source_node_links').fetchone()[0]==0
        assert connection.execute('SELECT count(*) FROM current_views').fetchone()[0]==0
        noop=predicted_diff(connection,envelope['mutations'])
        assert not noop['inserts'] and len(noop['unchanged'])==len(envelope['mutations'])
    with pytest.raises(BoundaryError,match='ALREADY_CONSUMED'): operator.execute(eid,confirm=eid)


def test_defer_is_distinct_and_blocks_qualification(case):
    sidecar=complete(case,'DEFER')
    with pytest.raises(BoundaryError,match='ATTRIBUTION_DEFERRED'): qualify(case['config'],case['handle'],sidecar)
    assert case['service'].read(case['handle'])['decisions'][CLAIM_THREE]['outcome']=='DEFER'


def test_no_advisory_links_and_revision_idempotency(case):
    initial=case['service'].read(case['handle']);assert not initial['decisions'] and initial['required']==3
    body=operation(case,claim_id=CLAIM,outcome='LINK',links=[{'node_id':REUSE_NODE,'role':'subject'}],scope='')
    body['scope']=case['service'].context(case['handle'])['claims'][CLAIM]['scope']
    result=case['service'].mutate(case['handle'],'SAVE',body,IDENTITY)
    assert case['service'].mutate(case['handle'],'SAVE',body,{**IDENTITY,'session_id':'restart'})==result
    with pytest.raises(BoundaryError,match='REVISION_CONFLICT'):
        case['service'].mutate(case['handle'],'SAVE',{**body,'operation_id':uuid.uuid4().hex},IDENTITY)
    with pytest.raises(BoundaryError,match='IDEMPOTENCY_CONFLICT'):
        case['service'].mutate(case['handle'],'SAVE',{**body,'reason':'different'},IDENTITY)


@pytest.mark.parametrize('links,outcome,error', [
    ([{'node_id':'NODE_WRONG','role':'subject'}],'LINK','ATTRIBUTION_NODE_INVALID'),
    ([{'node_id':CREATE_NODE,'role':'supporting'}],'LINK','ATTRIBUTION_ROLE_INVALID'),
    ([{'node_id':CREATE_NODE,'role':'subject'}],'MULTI_LINK','ATTRIBUTION_LINK_COUNT_INVALID'),
    ([{'node_id':CREATE_NODE,'role':'subject'}],'NO_LINK','ATTRIBUTION_LINK_COUNT_INVALID'),
    ([], 'LINK','ATTRIBUTION_LINK_COUNT_INVALID'),
])
def test_invalid_attribution(case,links,outcome,error):
    with pytest.raises(BoundaryError,match=error): decide(case,outcome=outcome,links=links)


def test_dropped_and_noncanonical_claims_cannot_link(tmp_path):
    case=stage2_fixture(tmp_path,claim_decisions=('KEEP','DROP','KEEP_NEEDS_REVIEW'))
    case['service']=Attribution(case['config'])
    assert case['service'].read(case['handle'])['required']==1
    for claim in (CLAIM_TWO,CLAIM_THREE,'CLM_UNKNOWN'):
        with pytest.raises(BoundaryError,match='NOT_REVIEWABLE'): decide(case,claim)


def test_sealed_attribution_immutable_and_exact_stage1_objects_preserved(case):
    with Store(case['config']).connect() as connection: before=[tuple(r) for r in connection.execute('SELECT * FROM sealed_review_artifacts')]
    complete(case)
    with pytest.raises(BoundaryError,match='ALREADY_SEALED'): decide(case)
    with Store(case['config']).connect(operator_write=True) as connection:
        with pytest.raises(sqlite3.IntegrityError,match='APPEND_ONLY'): connection.execute('DELETE FROM attribution_objects')
    with Store(case['config']).connect() as connection: assert [tuple(r) for r in connection.execute('SELECT * FROM sealed_review_artifacts')]==before


@pytest.mark.parametrize('point',['insert','before_commit','after_commit','receipt_export'])
def test_transaction_failure_and_postcommit_recovery(case,point):
    envelope=package(case);eid=envelope['object_id'];operator=case['operator'];operator.register(eid,confirm=eid)
    before=identity(case['config'].knowledge_db)
    def fail(where,_):
        if where==point: raise RuntimeError('synthetic fault')
    with pytest.raises((RuntimeError,BoundaryError)): operator.execute(eid,confirm=eid,fault=fail)
    if point in ('insert','before_commit'):
        assert identity(case['config'].knowledge_db)['semantic_snapshot']==before['semantic_snapshot']
        assert operator.execute(eid,confirm=eid)['status']=='EXECUTED'
    else:
        with pytest.raises(BoundaryError,match='ALREADY_CONSUMED'): operator.execute(eid,confirm=eid)
    assert operator.reconcile(eid)['status']=='EXECUTED'


def test_concurrent_grant_one_execution(case):
    envelope=package(case);eid=envelope['object_id'];operator=case['operator'];operator.register(eid,confirm=eid)
    def execute():
        try: return operator.execute(eid,confirm=eid)['status']
        except BoundaryError as error: return str(error)
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda _:execute(),range(2)))
    assert sorted(results)==['ALREADY_CONSUMED','EXECUTED']


def test_staging_repeat_and_tamper_guards(case):
    envelope=package(case)
    assert qualify(case['config'],case['handle'],envelope['attribution']['object_id'])==envelope
    for field,value,error in [('adapter_version','wrong','ADAPTER_VERSION_MISMATCH'),('runtime_identity','0'*64,'RUNTIME_IDENTITY_MISMATCH')]:
        body={k:v for k,v in envelope.items() if k not in ('object_id','sha256')};body[field]=value
        with pytest.raises(BoundaryError,match=error): verify_envelope(sealed(body,'OPERATIONAL'))
    bad=copy.deepcopy(envelope);bad['predicted_diff']['inserts'][0]['row']['title']='changed'
    with pytest.raises(BoundaryError,match='ARTIFACT_IDENTITY_MISMATCH'): verify_envelope(bad)
