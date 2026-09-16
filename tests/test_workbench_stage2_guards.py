from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

from test_workbench_stage2 import case, operation, decide, complete, package
from pro_a.operational_contract import (identity, predicted_diff, readonly, sealed, snapshot, verify_envelope)
from pro_a.operational_operator import Operator, OperatorConfig
from pro_a.operational_qualification import qualify, reconcile_registered, validate_package
from pro_a.production_promotion import canonical_sha256
from pro_a.workbench.api import create_app, PREFIX
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.config import BoundaryError, checked_path
from pro_a.workbench.store import Store
from workbench_stage2_fixture import CLAIM, CLAIM_TWO, CREATE_NODE, REUSE_NODE, IDENTITY


def test_wrong_basis_and_scope(case):
    body=operation(case,claim_id=CLAIM,outcome='NO_LINK',links=[],scope='wrong')
    with pytest.raises(BoundaryError,match='ATTRIBUTION_SCOPE_MISMATCH'): case['service'].mutate(case['handle'],'SAVE',body,IDENTITY)
    with pytest.raises(BoundaryError,match='ATTRIBUTION_BASIS_MISMATCH'): case['service'].mutate(case['handle'],'SAVE',{**body,'basis_id':'0'*64},IDENTITY)
    with pytest.raises(BoundaryError,match='ARTIFACT_NOT_REGISTERED'): case['service'].read('ART_'+'0'*32)


@pytest.mark.parametrize('table', ['current_views','research_questions','relation_evidence_links','source_node_links','meta','unknown_table'])
def test_exact_allowlist_rejects_other_tables(case,table):
    with closing(readonly(case['config'].knowledge_db)) as connection:
        with pytest.raises(BoundaryError,match='UNSUPPORTED_MUTATION'): predicted_diff(connection,[{'table':table,'operation':'INSERT','key':{},'row':{}}])


@pytest.mark.parametrize('mutation,error', [
    ({'table':'nodes','operation':'UPDATE','row':{},'key':{}},'UNSUPPORTED_MUTATION'),
    ({'table':'nodes','operation':'INSERT','row':{'node_id':'NODE_NEW','arbitrary':'x'},'key':{'node_id':'NODE_NEW'}},'UNSUPPORTED_COLUMN'),
    ({'table':'nodes','operation':'INSERT','row':{'node_id':'NODE_NEW'},'key':{'node_id':'NODE_WRONG'}},'MUTATION_KEY_INVALID'),
])
def test_mutation_shape_rejected(case,mutation,error):
    with closing(readonly(case['config'].knowledge_db)) as connection:
        with pytest.raises(BoundaryError,match=error): predicted_diff(connection,[mutation])


@pytest.mark.parametrize('table,keyfield', [('sources','source_id'),('claims','claim_id'),('nodes','node_id')])
def test_duplicate_identity_and_exact_noop(case,table,keyfield):
    envelope=package(case);eid=envelope['object_id'];op=case['operator'];op.register(eid,confirm=eid);op.execute(eid,confirm=eid)
    mutation=copy.deepcopy(next(r for r in envelope['mutations'] if r['table']==table))
    with closing(readonly(case['config'].knowledge_db)) as connection:
        assert not predicted_diff(connection,[mutation])['inserts']
        field={'sources':'title','claims':'statement','nodes':'canonical_name'}[table]
        mutation['row'][field]+=' conflicting'
        with pytest.raises(BoundaryError,match='CANONICAL_COLLISION'): predicted_diff(connection,[mutation])


def test_alias_node_relation_and_source_hash_collisions(case):
    envelope=package(case);eid=envelope['object_id'];op=case['operator'];op.register(eid,confirm=eid);op.execute(eid,confirm=eid)
    with closing(readonly(case['config'].knowledge_db)) as connection:
        alias={'table':'node_aliases','operation':'INSERT','key':{'alias':'Synthetic A'},'row':{'alias':'Synthetic A','node_id':REUSE_NODE}}
        with pytest.raises(BoundaryError,match='CANONICAL_COLLISION'): predicted_diff(connection,[alias])
        node=copy.deepcopy(next(r for r in envelope['mutations'] if r['table']=='nodes'));node['row']['node_id']='NODE_NEW';node['key']={'node_id':'NODE_NEW'}
        with pytest.raises(BoundaryError,match='NODE_COLLISION'): predicted_diff(connection,[node])
        relation=copy.deepcopy(next(r for r in envelope['mutations'] if r['table']=='node_relations'));relation['row']['relation_type']='supplies'
        with pytest.raises(BoundaryError,match='UNSUPPORTED_RELATION'): predicted_diff(connection,[relation])
        source=copy.deepcopy(next(r for r in envelope['mutations'] if r['table']=='sources'));source['row']['source_id']='SRC_NEW';source['key']={'source_id':'SRC_NEW'}
        with pytest.raises(BoundaryError,match='SOURCE_COLLISION'): predicted_diff(connection,[source])


def test_duplicate_canonical_keys_rejected(case):
    envelope=package(case)
    with closing(readonly(case['config'].knowledge_db)) as connection:
        with pytest.raises(BoundaryError,match='DUPLICATE_CANONICAL_KEY'): predicted_diff(connection,[envelope['mutations'][0],envelope['mutations'][0]])


def test_stale_baseline_and_grant_confirmation(case):
    envelope=package(case);eid=envelope['object_id'];op=case['operator']
    with pytest.raises(BoundaryError,match='OPERATOR_CONFIRMATION_REQUIRED'): op.register(eid,confirm='wrong')
    op.register(eid,confirm=eid)
    with closing(sqlite3.connect(case['config'].knowledge_db)) as connection,connection:
        connection.execute("UPDATE nodes SET description='synthetic baseline changed' WHERE node_id=?",(REUSE_NODE,))
    with pytest.raises(BoundaryError,match='STALE_BASELINE'): op.execute(eid,confirm=eid)


@pytest.mark.parametrize('field,value,error', [('schema_version','0.0.0','SCHEMA_MISMATCH'),('sha256','0'*64,'STALE_BASELINE')])
def test_wrong_envelope_baseline(case,field,value,error):
    envelope=package(case);body={k:copy.deepcopy(v) for k,v in envelope.items() if k not in ('object_id','sha256')};body['baseline'][field]=value
    bad=sealed(body,'OPERATIONAL')
    if field=='schema_version':
        with pytest.raises(BoundaryError,match=error): verify_envelope(bad)
    else:
        assert identity(case['config'].knowledge_db)['sha256']!=bad['baseline']['sha256']
        with Store(case['config']).connect(operator_write=True) as c:
            c.execute('DROP TRIGGER operational_packages_update_forbidden')
            c.execute('UPDATE operational_packages SET object_id=?,body=?',(bad['object_id'],json.dumps(bad)))
        with pytest.raises(BoundaryError,match=error): case['operator'].register(bad['object_id'],confirm=bad['object_id'])


@pytest.mark.parametrize('artifact', ['source','packet','sidecar'])
def test_immutable_input_drift(case,artifact):
    envelope=package(case)
    if artifact=='source':
        path=case['config'].artifact_root/case['run_relative']/'source/synthetic.txt';path.write_text('wrong synthetic source bytes')
    elif artifact=='packet':
        path=case['config'].artifact_root/case['packet_relative'];path.write_text('{}')
    else:
        with Store(case['config']).connect(operator_write=True) as c:
            c.execute('DROP TRIGGER attribution_objects_update_forbidden')
            value=json.loads(c.execute('SELECT body FROM attribution_objects').fetchone()[0]);value['binding']['review_id']='wrong'
            c.execute('UPDATE attribution_objects SET body=?',(json.dumps(value),))
    with pytest.raises(BoundaryError): case['operator'].register(envelope['object_id'],confirm=envelope['object_id'])


def test_wrong_materialized_bytes_block_operator(case):
    envelope=package(case);eid=envelope['object_id'];op=case['operator'];op.register(eid,confirm=eid)
    path=case['config'].knowledge_db.parent/'operational_sources'/envelope['source_sha256'];path.parent.mkdir();path.write_bytes(b'wrong')
    with pytest.raises(BoundaryError,match='SOURCE_MATERIALIZATION_MISMATCH'): op.execute(eid,confirm=eid)


def test_atomic_attribution_event_failure(case):
    with Store(case['config']).connect(operator_write=True) as c:
        c.execute("CREATE TRIGGER injected BEFORE INSERT ON attribution_events BEGIN SELECT RAISE(ABORT,'FAULT'); END")
    with pytest.raises(sqlite3.IntegrityError,match='FAULT'): decide(case)
    assert case['service'].read(case['handle'])['revision']==0


def test_receipt_identity_and_poststate_must_match(case):
    envelope=package(case);eid=envelope['object_id'];op=case['operator'];op.register(eid,confirm=eid);receipt=op.execute(eid,confirm=eid)
    with pytest.raises(BoundaryError,match='RECEIPT_NOT_REGISTERED'): reconcile_registered(case['config'],case['handle'],receipt['object_id'])
    op.reconcile(eid)
    assert reconcile_registered(case['config'],case['handle'],receipt['object_id'])['status']=='VERIFIED'
    with closing(sqlite3.connect(case['config'].knowledge_db)) as c,c:
        c.execute("UPDATE claims SET statement='changed after commit' WHERE claim_id=?",(CLAIM,))
    with pytest.raises(BoundaryError,match='RECOVERY_REQUIRED'): reconcile_registered(case['config'],case['handle'],receipt['object_id'])


def test_actual_process_crash_after_commit_keeps_consumption(case,tmp_path):
    envelope=package(case);eid=envelope['object_id'];op=case['operator'];op.register(eid,confirm=eid)
    config=case['config']
    workbench=tmp_path/'workbench.toml'
    workbench.write_text('[workbench]\n'+ '\n'.join(f'{k} = {json.dumps(str(v).replace(chr(92),"/"))}' for k,v in {
        'mode':config.mode,'knowledge_db':config.knowledge_db,'state_db':config.state_db,'artifact_root':config.artifact_root,'origin':config.origin}.items())+'\nremote = false\n')
    operator=tmp_path/'operator.toml';operator.write_text('[operator]\nworkbench_config = "workbench.toml"\nledger = "operator/ledger.sqlite3"\n')
    import os
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('operational_crash_worker.py')),str(operator),eid],env=env,capture_output=True,text=True)
    assert result.returncode==73,result.stderr
    reopened=Operator(OperatorConfig.load(operator))
    with pytest.raises(BoundaryError,match='ALREADY_CONSUMED'): reopened.execute(eid,confirm=eid)
    assert reopened.reconcile(eid)['status']=='EXECUTED'


def test_privileged_path_hardlink_and_traversal_guards(case,tmp_path):
    import os
    path=tmp_path/'linked-ledger.sqlite3';os.link(case['operator'].config.ledger,path)
    try:
        with pytest.raises(BoundaryError,match='HARDLINK_FORBIDDEN'): Operator(OperatorConfig(case['config'],path)).connect()
    finally: path.unlink()
    with pytest.raises(BoundaryError,match='UNSAFE_PATH'): checked_path(tmp_path/'operator'/'..'/'operator'/'ledger.sqlite3')
    with pytest.raises(BoundaryError,match='OPERATOR_NOT_ISOLATED'): Operator(OperatorConfig(case['config'],case['config'].state_db)).connect()


def test_web_mutation_boundaries_and_no_apply_route(case,monkeypatch):
    token='synthetic-stage2-browser-token-for-tests-only'
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN',token)
    monkeypatch.setattr(Operator,'execute',lambda *a,**k:pytest.fail('Web invoked privileged writer'))
    app=create_app(case['config'])
    assert not any('apply' in route.path.lower() or 'activate' in route.path.lower() for route in app.routes)
    client=TestClient(app,base_url=case['config'].origin,client=('127.0.0.1',1))
    path=PREFIX+'/attribution/'+case['handle']
    assert client.get(path).status_code==401
    session=client.post(PREFIX+'/session',headers={'Origin':case['config'].origin},json={'token':token}).json()
    body=operation(case,claim_id=CLAIM,outcome='NO_LINK',links=[],scope='synthetic scope')
    assert client.post(path+'/decisions',json=body).status_code==403
    headers={'Origin':case['config'].origin,'X-CSRF-Token':session['csrf_token']}
    assert client.post(path+'/decisions',headers=headers,json=body).status_code==200
    response=client.post(path+'/decisions',headers=headers,json={**body,'path':'C:/private/source.pdf'})
    assert response.status_code==422 and 'private' not in response.text
    assert client.get('/api/stats').status_code==200


@pytest.mark.parametrize('collision',['node','alias','reuse'])
def test_generic_shadow_rejects_actual_catalog_collisions(tmp_path,collision):
    from workbench_stage2_fixture import stage2_fixture
    case=stage2_fixture(tmp_path,collision=collision);case['service']=Attribution(case['config'])
    with pytest.raises((BoundaryError, RuntimeError)):
        package(case)
    with Store(case['config']).connect() as c: assert c.execute('SELECT count(*) FROM operational_packages').fetchone()[0]==0


def test_journal_uncertainty_is_explicit_stop(case):
    path=Path(str(case['operator'].config.ledger)+'-journal');path.write_bytes(b'synthetic uncertain journal')
    with pytest.raises(BoundaryError,match='RECOVERY_REQUIRED'): case['operator'].connect()


def test_request_context_blocks_privileged_bypass_before_writable_open(case,monkeypatch):
    from pro_a.operational_contract import WEB_REQUEST
    original=sqlite3.connect
    def guarded(database,*args,**kwargs):
        assert '?mode=rw' not in str(database), 'Web context attempted writable open'
        return original(database,*args,**kwargs)
    marker=WEB_REQUEST.set(True);monkeypatch.setattr(sqlite3,'connect',guarded)
    try:
        with pytest.raises(BoundaryError,match='WEB_APPLY_FORBIDDEN'): case['operator'].connect()
        with pytest.raises(BoundaryError,match='WEB_APPLY_FORBIDDEN'): case['operator'].initialize()
    finally: WEB_REQUEST.reset(marker)


def test_missing_attribution_and_duplicate_links_rejected(case):
    with pytest.raises(BoundaryError,match='ATTRIBUTION_INCOMPLETE'): case['service'].mutate(case['handle'],'SEAL',operation(case,confirm=True),IDENTITY)
    with pytest.raises(BoundaryError,match='DUPLICATE_ATTRIBUTION'):
        decide(case,outcome='MULTI_LINK',links=[{'node_id':CREATE_NODE,'role':'subject'},{'node_id':CREATE_NODE,'role':'context'}])


def test_operator_directory_alias_rejected(case,tmp_path):
    link=tmp_path/'operator-alias';target=case['operator'].config.ledger.parent
    if sys.platform=='win32':
        subprocess.run(['powershell','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{str(link).replace(chr(39),chr(39)*2)}' -Target '{str(target).replace(chr(39),chr(39)*2)}' | Out-Null"],check=True,capture_output=True)
    else: link.symlink_to(target,target_is_directory=True)
    with pytest.raises(BoundaryError,match='LINK_FORBIDDEN'): Operator(OperatorConfig(case['config'],link/'ledger.sqlite3')).connect()
