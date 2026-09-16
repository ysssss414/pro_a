from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import copy
import json
import sqlite3
import uuid

from fastapi.testclient import TestClient
import pytest

from pro_a.current_view_workbench import CurrentViewWorkbench, CONTRACT_SHA, VERSION, verify_package
from pro_a.operational_contract import sealed, snapshot
from pro_a.view_operator import ViewOperator, ViewOperatorConfig
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.attribution_store import prepare_attribution
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_store import prepare_reviews, schema_version
from pro_a.workbench.store import Store
from pro_a.workbench.view_store import prepare_current_views
from workbench_stage3_fixture import (COMPANY, COMPANY_CLAIM, COMPANY_CONTEXT, IDENTITY, PRODUCT,
                                      PRODUCT_CLAIM, REVIEWER, TECH, company_content, product_content,
                                      stage3_fixture, _view)


@pytest.fixture
def case(tmp_path):
    value=stage3_fixture(tmp_path); value['service']=CurrentViewWorkbench(value['config'])
    value['operator']=ViewOperator(ViewOperatorConfig(value['config'],tmp_path/'operator/ledger.sqlite3'))
    value['operator'].initialize(); return value


def save(case,node,content,primary,context=(),mode=None,**changes):
    state=case['service'].read(node); mode=mode or ('UPDATE' if state['official'] else 'INITIAL')
    body={'basis_sha256':state['basis_sha256'],'expected_revision':state['draft']['revision'] if state['draft'] else 0,
          'operation_id':uuid.uuid4().hex,'reviewer':REVIEWER,'reason':'Explicit synthetic View maintenance',
          'mode':mode,'expected_official_view_id':state['official']['view_id'] if mode=='UPDATE' and state['official'] else '',
          'content':content,'primary_claim_ids':list(primary),'context_claim_ids':list(context),
          'change_level':'minor' if mode=='UPDATE' else 'initial',**changes}
    return case['service'].save(node,body,IDENTITY)


def validate(case,node):
    draft=case['service'].read(node)['draft']
    return case['service'].validate(node,{'basis_sha256':draft['basis_sha256'],'expected_revision':draft['revision'],
        'operation_id':uuid.uuid4().hex,'reviewer':REVIEWER,'reason':'Explicit quality validation','draft_id':draft['draft_id']},IDENTITY)


def package(case,node):
    draft=case['service'].read(node)['draft']; return case['service'].qualify(node,draft['draft_id'],draft['revision'])


def reseal(value,prefix,**changes):
    body={key:copy.deepcopy(item) for key,item in value.items() if key not in ('object_id','sha256')}
    body.update(changes); return sealed(body,prefix)


def test_official_history_baseline_evidence_freshness_and_comparison(case):
    state=case['service'].read(COMPANY)
    assert state['official']['view_id']=='VIEW_STAGE3_CURRENT'
    assert state['previous_official']['view_id']=='VIEW_STAGE3_OLD'
    assert [row['view_id'] for row in state['history']]==['VIEW_STAGE3_CURRENT','VIEW_STAGE3_OLD']
    assert [row['view_id'] for row in state['baseline_views']]==['BASELINE_STAGE3']
    assert state['official_comparison']['has_changes']
    by_id={row['claim_id']:row for row in state['available_evidence']}
    assert by_id[COMPANY_CLAIM]['business_date']=='2026-02-01' and by_id[COMPANY_CLAIM]['freshness_basis']=='claim_fact_time'
    assert by_id[COMPANY_CONTEXT]['business_date'] is None and by_id[COMPANY_CONTEXT]['freshness_basis']=='unknown'
    assert by_id[COMPANY_CLAIM]['source_locator']=={'status':'resolved','locator':'TEXT'}
    assert {row['evidence_class'] for row in state['official_evidence']}=={'PRIMARY','CONTEXT_ONLY'}
    assert state['uncertainty']['core_disagreements'] and state['selection_rule'].endswith('view_id DESC')


def test_update_draft_persists_qualifies_activates_and_reconciles(case):
    content=company_content('Synthetic Company updated official conclusion')
    saved=save(case,COMPANY,content,[COMPANY_CLAIM],[COMPANY_CONTEXT]); assert saved['status']=='DRAFT'
    restarted=CurrentViewWorkbench(case['config']); assert restarted.read(COMPANY)['draft']['content']==content
    assert validate(case,COMPANY)['status']=='VALIDATED'
    envelope=package(case,COMPANY); verify_package(envelope)
    assert envelope['adapter_version']==VERSION and not envelope['production_authorized']
    assert envelope['predicted_diff']['row']['previous_view_id']=='VIEW_STAGE3_CURRENT'
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory=sqlite3.Row; before=snapshot(connection)
    op=case['operator']; pid=envelope['object_id']; op.register(pid,confirm=pid)
    receipt=op.execute(pid,confirm=pid); assert receipt['actual_mutation_counts']=={'current_views':1}
    assert op.reconcile(pid)==receipt
    verified=restarted.reconcile(COMPANY,receipt['object_id']); assert verified['status']=='VERIFIED'
    state=restarted.read(COMPANY); assert state['official']['view_id']==envelope['predicted_diff']['row']['view_id']
    assert state['official']['previous_view_id']=='VIEW_STAGE3_CURRENT' and len(state['history'])==3
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory=sqlite3.Row; after=snapshot(connection)
    assert {k:v for k,v in before.items() if k!='current_views'}=={k:v for k,v in after.items() if k!='current_views'}
    with pytest.raises(BoundaryError,match='ALREADY_CONSUMED'): op.execute(pid,confirm=pid)


def test_initial_product_qualifies_and_race_is_rejected(case):
    save(case,PRODUCT,product_content(),[PRODUCT_CLAIM]); validate(case,PRODUCT)
    envelope=package(case,PRODUCT); assert envelope['mode']=='INITIAL' and envelope['predicted_diff']['old_official_view_id'] is None
    pid=envelope['object_id']; case['operator'].register(pid,confirm=pid); receipt=case['operator'].execute(pid,confirm=pid)
    case['operator'].reconcile(pid); assert case['service'].reconcile(PRODUCT,receipt['object_id'])['status']=='VERIFIED'
    assert case['service'].read(PRODUCT)['official']['previous_view_id'] is None
    with pytest.raises(BoundaryError,match='INITIAL_VIEW_RACE'):
        save(case,PRODUCT,product_content('Another initial'),[PRODUCT_CLAIM],mode='INITIAL')


def test_company_without_view_is_initially_eligible(tmp_path):
    value=stage3_fixture(tmp_path); service=CurrentViewWorkbench(value['config'])
    with closing(sqlite3.connect(value['knowledge'])) as connection,connection:
        connection.execute("DELETE FROM current_views WHERE node_id=? AND status='official'",(COMPANY,))
    case={'service':service}; assert service.read(COMPANY)['capabilities']['initial_supported']
    save(case,COMPANY,company_content('Synthetic Company initial conclusion'),[COMPANY_CLAIM],mode='INITIAL')
    validate(case,COMPANY); assert package(case,COMPANY)['mode']=='INITIAL'


def test_no_change_context_primary_unsupported_and_invalid_citation_reject(case,tmp_path):
    save(case,COMPANY,company_content(),[COMPANY_CLAIM])
    with pytest.raises(BoundaryError,match='NO_EFFECTIVE_CHANGE'): validate(case,COMPANY)
    other=stage3_fixture(tmp_path/'other'); other['service']=CurrentViewWorkbench(other['config'])
    save(other,COMPANY,company_content('Changed'),[COMPANY_CONTEXT])
    with pytest.raises(BoundaryError,match='PRIMARY_EVIDENCE_INVALID'): validate(other,COMPANY)
    with pytest.raises(BoundaryError,match='UNSUPPORTED_NODE_TYPE'):
        save(case,TECH,company_content('Unsupported'),[COMPANY_CLAIM],mode='INITIAL')
    third=stage3_fixture(tmp_path/'third'); third['service']=CurrentViewWorkbench(third['config'])
    bad=company_content('Changed'); bad['evidence_claim_ids']=['CLM_MISSING']
    save(third,COMPANY,bad,[COMPANY_CLAIM])
    with pytest.raises(BoundaryError,match='PRIMARY_EVIDENCE_INVALID'): validate(third,COMPANY)


def test_revision_idempotency_stale_basis_and_web_guard(case):
    state=case['service'].read(COMPANY); request={'basis_sha256':state['basis_sha256'],'expected_revision':0,
        'operation_id':uuid.uuid4().hex,'reviewer':REVIEWER,'reason':'Idempotent save','mode':'UPDATE',
        'expected_official_view_id':state['official']['view_id'],'content':company_content('Changed'),
        'primary_claim_ids':[COMPANY_CLAIM],'context_claim_ids':[],'change_level':'minor'}
    first=case['service'].save(COMPANY,request,IDENTITY); assert case['service'].save(COMPANY,request,IDENTITY)==first
    with pytest.raises(BoundaryError,match='REVISION_CONFLICT'):
        case['service'].save(COMPANY,{**request,'operation_id':uuid.uuid4().hex},IDENTITY)
    with closing(sqlite3.connect(case['knowledge'])) as connection,connection:
        connection.execute("UPDATE claims SET status='needs_review' WHERE claim_id=?",(COMPANY_CLAIM,))
    assert case['service'].read(COMPANY)['draft']['status']=='STALE'
    with pytest.raises(BoundaryError,match='BASELINE_STALE'):
        case['service'].save(COMPANY,{**request,'expected_revision':1,'operation_id':uuid.uuid4().hex},IDENTITY)
    from pro_a.operational_contract import WEB_REQUEST
    marker=WEB_REQUEST.set(True)
    try:
        with pytest.raises(BoundaryError,match='WEB_VIEW_ACTIVATION_FORBIDDEN'): case['operator'].connect()
    finally: WEB_REQUEST.reset(marker)


def test_precommit_rollback_postcommit_uncertainty_and_concurrency(case,tmp_path):
    save(case,COMPANY,company_content('Synthetic Company changed'),[COMPANY_CLAIM]); validate(case,COMPANY); envelope=package(case,COMPANY)
    pid=envelope['object_id']; case['operator'].register(pid,confirm=pid)
    def pre(point,_index):
        if point=='before_commit': raise RuntimeError('synthetic precommit failure')
    with pytest.raises(RuntimeError): case['operator'].execute(pid,confirm=pid,fault=pre)
    assert case['service'].read(COMPANY)['official']['view_id']=='VIEW_STAGE3_CURRENT'
    def post(point,_index):
        if point=='receipt_export': raise OSError('synthetic receipt failure')
    with pytest.raises(BoundaryError,match='RECOVERY_REQUIRED'): case['operator'].execute(pid,confirm=pid,fault=post)
    assert case['operator'].reconcile(pid)['status']=='EXECUTED'
    with pytest.raises(BoundaryError,match='ALREADY_CONSUMED'): case['operator'].execute(pid,confirm=pid)
    fresh=stage3_fixture(tmp_path/'concurrent'); fresh['service']=CurrentViewWorkbench(fresh['config'])
    fresh['operator']=ViewOperator(ViewOperatorConfig(fresh['config'],tmp_path/'concurrent-operator/ledger.sqlite3')); fresh['operator'].initialize()
    save(fresh,COMPANY,company_content('Synthetic Company concurrent change'),[COMPANY_CLAIM]); validate(fresh,COMPANY); env=package(fresh,COMPANY)
    eid=env['object_id']; fresh['operator'].register(eid,confirm=eid)
    def execute():
        try: return fresh['operator'].execute(eid,confirm=eid)['status']
        except BoundaryError as error: return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _x:execute(),range(2)))
    assert set(results) <= {'EXECUTED','ALREADY_CONSUMED','RECOVERY_REQUIRED'}
    assert fresh['operator'].reconcile(eid)['status']=='EXECUTED'
    assert len(fresh['service'].read(COMPANY)['history'])==3


def test_ambiguous_official_order_uses_canonical_tie_break_and_exact_predecessor(case):
    with closing(sqlite3.connect(case['knowledge'])) as connection,connection:
        _view(connection,'VIEW_Z_STAGE3_TIE',COMPANY,'v_20260201_tie',
              company_content('Synthetic Company tie-break winner'),'20260201',0,'VIEW_STAGE3_OLD')
    state=case['service'].read(COMPANY)
    assert state['official']['view_id']=='VIEW_Z_STAGE3_TIE'
    assert state['history'][1]['view_id']=='VIEW_STAGE3_CURRENT'
    assert state['previous_official']['view_id']=='VIEW_STAGE3_OLD'
    assert state['official_comparison']['has_changes']


def test_missing_historical_citation_is_visible_and_never_fabricated(case):
    with closing(sqlite3.connect(case['knowledge'])) as connection,connection:
        connection.execute("UPDATE current_views SET trigger_claim_ids_json='[\"CLM_STAGE3_MISSING\"]' WHERE view_id='VIEW_STAGE3_CURRENT'")
    state=case['service'].read(COMPANY)
    broken=[item for item in state['official_evidence'] if not item['resolved']]
    assert broken==[{'claim_id':'CLM_STAGE3_MISSING','resolved':False,'officially_referenced':True,
                     'evidence_class':'PRIMARY','error':'EVIDENCE_NOT_FOUND'}]
    assert not any(item.get('statement') for item in broken)


def test_schema4_preparation_is_explicit_backed_up_idempotent_and_append_only(tmp_path):
    value=stage3_fixture(tmp_path); config=value['config']
    backup=config.state_db.with_name(config.state_db.name+'.stage2-backup')
    assert backup.is_file()
    with closing(sqlite3.connect(backup)) as connection:
        assert connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0]=='3'
    assert prepare_current_views(config)=={'status':'ALREADY_PREPARED','schema_version':'4'}
    assert prepare_reviews(config)['schema_version']=='4'
    assert prepare_attribution(config)['schema_version']=='4'
    with Store(config).connect() as connection:
        assert schema_version(connection)=='4'
        tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'view_drafts','view_draft_events','view_activation_packages','view_activation_receipts'} <= tables
    service=CurrentViewWorkbench(config); local={'service':service}
    save(local,COMPANY,company_content('Synthetic Company append-only check'),[COMPANY_CLAIM])
    with Store(config).connect(operator_write=True) as connection:
        with pytest.raises(sqlite3.IntegrityError,match='APPEND_ONLY'):
            connection.execute("UPDATE view_draft_events SET event_json='{}'")
        with pytest.raises(sqlite3.IntegrityError,match='APPEND_ONLY'):
            connection.execute('DELETE FROM view_drafts')


def test_stage2_attribution_remains_operable_after_schema4(tmp_path):
    from workbench_stage2_fixture import CLAIM, CREATE_NODE, IDENTITY as STAGE2_IDENTITY, REVIEWER as STAGE2_REVIEWER, stage2_fixture
    value=stage2_fixture(tmp_path); config=value['config']; service=Attribution(config)
    with Store(config).connect() as connection:
        sealed_before=[tuple(row) for row in connection.execute('SELECT * FROM sealed_review_artifacts ORDER BY artifact_id,kind')]
    prepare_current_views(config)
    state=service.read(value['handle']); context=service.context(value['handle'])
    body={'basis_id':state['basis_id'],'expected_revision':state['revision'],'operation_id':uuid.uuid4().hex,
          'reviewer':STAGE2_REVIEWER,'reason':'Explicit Stage 2 compatibility decision.','claim_id':CLAIM,
          'outcome':'LINK','links':[{'node_id':CREATE_NODE,'role':'subject'}],
          'scope':context['claims'][CLAIM]['scope']}
    assert service.mutate(value['handle'],'SAVE',body,STAGE2_IDENTITY)['revision']==1
    assert prepare_attribution(config)['schema_version']=='4'
    with Store(config).connect() as connection:
        sealed_after=[tuple(row) for row in connection.execute('SELECT * FROM sealed_review_artifacts ORDER BY artifact_id,kind')]
    assert sealed_after==sealed_before


@pytest.mark.parametrize(('mutation','error'),[
    ({'adapter_version':'phase42-view-v0'},'ADAPTER_VERSION_MISMATCH'),
    ({'contract_sha256':'0'*64},'ADAPTER_VERSION_MISMATCH'),
    ({'node_type':'Technology'},'UNSUPPORTED_NODE_TYPE'),
    ({'production_authorized':True},'ACTIVATION_NOT_AUTHORIZED'),
])
def test_activation_package_rejects_wrong_version_type_and_authorization(case,mutation,error):
    save(case,COMPANY,company_content('Synthetic Company package check'),[COMPANY_CLAIM]); validate(case,COMPANY)
    with pytest.raises(BoundaryError,match=error): verify_package(reseal(package(case,COMPANY),'VIEWPACKAGE',**mutation))


def test_activation_package_rejects_wrong_diff_and_evidence_identity(case):
    save(case,COMPANY,company_content('Synthetic Company package boundary'),[COMPANY_CLAIM]); validate(case,COMPANY)
    value=package(case,COMPANY)
    diff=reseal(value['predicted_diff'],'VIEWDIFF',operation='UPDATE')
    with pytest.raises(BoundaryError,match='UNSUPPORTED_MUTATION'):
        verify_package(reseal(value,'VIEWPACKAGE',predicted_diff=diff))
    evidence=copy.deepcopy(value['evidence_basis'])
    evidence['primary'][0]['role']='context'
    evidence=reseal(evidence,'VIEWEVIDENCE')
    with pytest.raises(BoundaryError,match='PRIMARY_EVIDENCE_INVALID'):
        verify_package(reseal(value,'VIEWPACKAGE',evidence_basis=evidence))


def test_operator_requires_exact_confirmation_draft_and_baseline(case):
    save(case,COMPANY,company_content('Synthetic Company operator binding'),[COMPANY_CLAIM]); validate(case,COMPANY)
    value=package(case,COMPANY); package_id=value['object_id']
    with pytest.raises(BoundaryError,match='OPERATOR_CONFIRMATION_REQUIRED'):
        case['operator'].register(package_id,confirm='wrong')
    save(case,COMPANY,company_content('Synthetic Company later edit'),[COMPANY_CLAIM])
    with pytest.raises(BoundaryError,match='DRAFT_IDENTITY_MISMATCH'):
        case['operator'].register(package_id,confirm=package_id)

    other=stage3_fixture(case['config'].state_db.parent/'baseline-case'); other['service']=CurrentViewWorkbench(other['config'])
    other['operator']=ViewOperator(ViewOperatorConfig(other['config'],case['config'].state_db.parent/'baseline-operator/ledger.sqlite3'))
    other['operator'].initialize(); save(other,COMPANY,company_content('Synthetic Company baseline check'),[COMPANY_CLAIM]); validate(other,COMPANY)
    envelope=package(other,COMPANY); eid=envelope['object_id']; other['operator'].register(eid,confirm=eid)
    with closing(sqlite3.connect(other['knowledge'])) as connection,connection:
        connection.execute("INSERT INTO meta VALUES('synthetic_unrelated_change','changed')")
    with pytest.raises(BoundaryError,match='BASELINE_STALE'):
        other['operator'].execute(eid,confirm=eid)
    assert other['service'].read(COMPANY)['official']['view_id']=='VIEW_STAGE3_CURRENT'


def test_initial_boundaries_missing_primary_empty_content_and_mode_mismatch(tmp_path):
    value=stage3_fixture(tmp_path); service=CurrentViewWorkbench(value['config']); local={'service':service}
    with closing(sqlite3.connect(value['knowledge'])) as connection,connection:
        connection.execute("DELETE FROM current_views WHERE node_id=? AND status='official'",(COMPANY,))
    save(local,COMPANY,company_content('Synthetic Company missing primary'),[])
    with pytest.raises(BoundaryError,match='PRIMARY_EVIDENCE_INVALID'): validate(local,COMPANY)
    value2=stage3_fixture(tmp_path/'empty'); local2={'service':CurrentViewWorkbench(value2['config'])}
    with closing(sqlite3.connect(value2['knowledge'])) as connection,connection:
        connection.execute("DELETE FROM current_views WHERE node_id=? AND status='official'",(COMPANY,))
    empty=company_content(''); save(local2,COMPANY,empty,[COMPANY_CLAIM])
    with pytest.raises(BoundaryError,match='QUALITY_VALIDATION_FAILED'): validate(local2,COMPANY)
    state=service.read(COMPANY)
    request={'basis_sha256':state['basis_sha256'],'expected_revision':state['draft']['revision'],
             'operation_id':uuid.uuid4().hex,'reviewer':REVIEWER,'reason':'Explicit mode mismatch',
             'mode':'INITIAL','expected_official_view_id':'','content':company_content('Synthetic Company mode'),
             'primary_claim_ids':[COMPANY_CLAIM],'context_claim_ids':[],'change_level':'minor'}
    with pytest.raises(BoundaryError,match='INVALID_REQUEST'): service.save(COMPANY,request,IDENTITY)


def test_workbench_api_auth_csrf_external_handoff_and_explorer_get(case,monkeypatch):
    token='synthetic-stage3-browser-token-for-tests-only'
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN',token)
    monkeypatch.setattr(ViewOperator,'execute',lambda *_a,**_k:pytest.fail('Web invoked privileged View operator'))
    app=create_app(case['config'])
    assert not any('apply' in route.path.lower() or 'activate' in route.path.lower() for route in app.routes)
    client=TestClient(app,base_url=case['config'].origin,client=('127.0.0.1',1))
    path=PREFIX+'/current-views/'+COMPANY
    assert client.get(path).status_code==401
    session=client.post(PREFIX+'/session',headers={'Origin':case['config'].origin},json={'token':token}).json()
    state=client.get(path).json(); assert state['official']['view_id']=='VIEW_STAGE3_CURRENT'
    body={'basis_sha256':state['basis_sha256'],'expected_revision':0,'operation_id':uuid.uuid4().hex,
          'reviewer':REVIEWER,'reason':'Explicit browser API draft','mode':'UPDATE',
          'expected_official_view_id':'VIEW_STAGE3_CURRENT',
          'content':company_content('Synthetic Company browser update'),'primary_claim_ids':[COMPANY_CLAIM],
          'context_claim_ids':[COMPANY_CONTEXT],'change_level':'minor'}
    assert client.put(path+'/draft',json=body).status_code==403
    headers={'Origin':case['config'].origin,'X-CSRF-Token':session['csrf_token']}
    response=client.put(path+'/draft',headers=headers,json={**body,'private_path':'C:/private/source.pdf'})
    assert response.status_code==422 and 'private' not in response.text.lower()
    assert client.put(path+'/draft',headers=headers,json=body).status_code==200
    draft=client.get(path).json()['draft']
    action={'basis_sha256':draft['basis_sha256'],'expected_revision':draft['revision'],
            'operation_id':uuid.uuid4().hex,'reviewer':REVIEWER,'reason':'Explicit browser validation',
            'draft_id':draft['draft_id']}
    assert client.post(path+'/validate',headers=headers,json=action).status_code==200
    draft=client.get(path).json()['draft']
    qualified=client.post(path+'/qualify',headers=headers,json={'draft_id':draft['draft_id'],'revision':draft['revision']})
    assert qualified.status_code==200
    assert qualified.json()['operator_action']=='EXTERNAL_OPERATOR_REQUIRED' and qualified.json()['production_authorized'] is False
    assert client.post(path+'/activate',headers=headers,json={}).status_code==404
    assert client.get('/api/stats').status_code==200


def test_initial_company_disposable_activation_and_receipt_reconciliation(tmp_path):
    value=stage3_fixture(tmp_path); service=CurrentViewWorkbench(value['config']); local={'service':service}
    with closing(sqlite3.connect(value['knowledge'])) as connection,connection:
        connection.execute("DELETE FROM current_views WHERE node_id=? AND status='official'",(COMPANY,))
    operator=ViewOperator(ViewOperatorConfig(value['config'],tmp_path/'operator/ledger.sqlite3')); operator.initialize()
    save(local,COMPANY,company_content('Synthetic Company initial activated View'),[COMPANY_CLAIM],mode='INITIAL')
    validate(local,COMPANY); envelope=package(local,COMPANY); package_id=envelope['object_id']
    operator.register(package_id,confirm=package_id); receipt=operator.execute(package_id,confirm=package_id)
    operator.reconcile(package_id)
    assert service.reconcile(COMPANY,receipt['object_id'])['official_view_id']==envelope['predicted_diff']['new_official_view_id']
    assert service.read(COMPANY)['official']['previous_view_id'] is None


def test_evidence_role_change_makes_draft_stale_then_primary_ineligible(case):
    save(case,COMPANY,company_content('Synthetic Company role-change draft'),[COMPANY_CLAIM])
    with closing(sqlite3.connect(case['knowledge'])) as connection,connection:
        connection.execute("UPDATE claim_node_links SET role='context' WHERE claim_id=? AND node_id=?",(COMPANY_CLAIM,COMPANY))
    assert case['service'].read(COMPANY)['draft']['status']=='STALE'
    with pytest.raises(BoundaryError,match='BASELINE_STALE'): validate(case,COMPANY)
    save(case,COMPANY,company_content('Synthetic Company explicitly re-evaluated'),[COMPANY_CLAIM])
    with pytest.raises(BoundaryError,match='PRIMARY_EVIDENCE_INVALID'): validate(case,COMPANY)


def test_registered_receipt_must_match_package_evidence_basis(case):
    save(case,COMPANY,company_content('Synthetic Company receipt check'),[COMPANY_CLAIM]); validate(case,COMPANY)
    envelope=package(case,COMPANY); package_id=envelope['object_id']
    case['operator'].register(package_id,confirm=package_id)
    receipt=case['operator'].execute(package_id,confirm=package_id)
    fake=reseal(receipt,'VIEWEXECUTION',evidence_basis_id='VIEWEVIDENCE_'+'0'*64)
    with Store(case['config']).connect(operator_write=True) as connection:
        connection.execute('INSERT INTO view_activation_receipts VALUES(?,?,?,?)',
                           (fake['object_id'],package_id,COMPANY,json.dumps(fake,sort_keys=True,separators=(',',':'))))
    with pytest.raises(BoundaryError,match='RECEIPT_MISMATCH'):
        case['service'].reconcile(COMPANY,fake['object_id'])
