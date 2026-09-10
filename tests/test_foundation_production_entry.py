"""Public synthetic fixtures; no actual Production writes or real review content."""
import copy
from contextlib import closing
from dataclasses import replace
import hashlib
import json
import os
import sqlite3

import pytest

from test_phase3f_foundation_baseline import case, handoff
from test_foundation_execution_preparation import governed
from pro_a import production_promotion as engine
from pro_a.production_execution import execute_foundation_payload, validate_supported_mutations
from pro_a.foundation_production_entry import (ExecutionTargetMode, QualificationReference, ProductionAuthorization,
    execution_bindings, validate_foundation_mutations, validate_insert_dependencies)


DELTA = ['node_relations','relation_temporal_semantics','relation_evidence_authorizations','relation_evidence_links','current_views']
ENTRY_COMMIT = 'a' * 40


def data(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')


def receipt_ref(body, entry=False):
    prefix = 'production_entry_qualification_receipt' if entry else 'qualification_receipt'
    sha = engine.canonical_sha256(body)
    rid = ('SYNTHETIC_ENTRY_' if entry else 'SYNTHETIC_QUALIFICATION_') + sha[:16]
    encoded = data({**body, prefix+'_id':rid, prefix+'_semantic_sha256':sha})
    return QualificationReference(encoded, rid, sha, hashlib.sha256(encoded).hexdigest())


@pytest.fixture
def entry_case(governed):
    payload = handoff(governed)['payload']
    encoded = data(payload)
    with closing(engine.connect_read_only(governed['production'])) as conn:
        before = engine.database_rows(conn)
    after = {t:set(v) for t,v in before.items()}
    for mutation in payload['intended_mutations']:
        after[mutation['table']].add(json.dumps(mutation['row'],ensure_ascii=False,sort_keys=True,separators=(',',':')))
    predicted = data(dict(required_production_sha256=payload['metadata']['production_sha256'], payload_sha256=payload['payload_hash'],
        before_rows={t:sorted(v) for t,v in before.items()},after_rows={t:sorted(v) for t,v in after.items()}))
    body = dict(document_type='phase3f_foundation_payload_qualification_receipt', qualification_complete=True,
        qualification_state='QUALIFIED_FOR_EXPLICIT_PRODUCTION_APPLY_AUTHORIZATION',
        insert_operations=len(payload['intended_mutations']),accounting=f"{len(payload['mapping'])}/{len(payload['mapping'])}",
        payload_id=payload['payload_id'],payload_semantic_sha256=payload['payload_hash'],payload_file_sha256=hashlib.sha256(encoded).hexdigest(),
        required_pre_apply_production_sha256=payload['metadata']['production_sha256'],required_production_schema='0.2.3',
        completed_review_basis=payload['review_basis'],payload_envelope_contract=payload['payload_envelope_contract'],
        mutation_core_sha256=engine.canonical_sha256({k:payload[k] for k in ('intended_mutations','mapping','node_operations','relation_operations','claims')}),
        predicted_diff_file_sha256=hashlib.sha256(predicted).hexdigest(),
        gates={g:'PASS' for g in ('envelope_v2','shadow_apply','predicted_vs_actual','idempotency','rollback_recovery','security_wrong_basis','official_views','accounting','mutation_core','exact_entry_path','five_table_support','authorization_gates','applicable_full_regression')})
    qualification = receipt_ref(body)
    bindings = execution_bindings(payload,hashlib.sha256(encoded).hexdigest(),qualification,governed['verification']['verification_basis'],ENTRY_COMMIT)
    entry = receipt_ref({**body,'document_type':'phase3f_foundation_production_entry_qualification_receipt',
        'qualification_state':'QUALIFIED_FOR_EXPLICIT_ONE_TIME_PRODUCTION_APPLY_AUTHORIZATION',
        'entry_implementation_commit':ENTRY_COMMIT,'prior_qualification_identity':{k:bindings[k] for k in ('qualification_receipt_id','qualification_receipt_semantic_sha256','qualification_receipt_file_sha256')}},entry=True)
    bindings.update(entry_qualification_receipt_id=entry.receipt_id,entry_qualification_receipt_semantic_sha256=entry.semantic_sha256,entry_qualification_receipt_file_sha256=entry.file_sha256)
    authorization = ProductionAuthorization('SYNTHETIC_AUTH_ONCE','Synthetic user permits this exact temporary DB once.',governed['production'],bindings)
    target = governed['root'] / 'entry-shadow.db'
    engine.copy_production_to_shadow(governed['production'],target,payload['metadata']['production_sha256'])
    args = dict(payload_artifact=encoded,expected_payload_file_sha256=hashlib.sha256(encoded).hexdigest(),
        qualification=qualification,predicted_diff_artifact=predicted,target_path=target,configured_production_path=governed['production'],
        execution_commit=ENTRY_COMMIT,**governed['verification'])
    return dict(args=args,payload=payload,authorization=authorization,entry=entry,root=governed['root'])


def forbid_writable(monkeypatch):
    original = sqlite3.connect
    calls = []
    def connect(database,*args,**kwargs):
        value = str(database)
        if 'mode=ro' not in value:
            calls.append(value)
            raise AssertionError('Writable connection before rejection')
        return original(database,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',connect)
    return calls


@pytest.mark.parametrize('table',DELTA)
def test_five_table_first_insert_replay_conflicting_duplicate_and_fk(entry_case,table):
    args=entry_case['args']; target=args['target_path']
    result=execute_foundation_payload(**args)
    assert result['status']=='COMMITTED' and table in result['table_contracts']
    before=engine.sha256_file(target)
    assert execute_foundation_payload(**args)['status']=='ALREADY_APPLIED'
    assert engine.sha256_file(target)==before
    mutation=copy.deepcopy(next(m for m in entry_case['payload']['intended_mutations'] if m['table']==table))
    with closing(sqlite3.connect(target)) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conflict=copy.deepcopy(mutation)
        field={'node_relations':'scope','relation_temporal_semantics':'temporal_category','relation_evidence_authorizations':'reviewer','relation_evidence_links':'evidence_sha256','current_views':'content_md'}[table]
        conflict['row'][field]='CONFLICTING_DUPLICATE'
        with pytest.raises(sqlite3.IntegrityError): engine._insert_mutation(conn,conflict)
        conn.rollback()
        row=mutation['row']
        if table=='current_views': row.update(view_id='BASELINE_MISSING',version='baseline_MISSING',node_id='MISSING_NODE')
        elif table=='node_relations': row.update(relation_id='MISSING_REL',from_node_id='MISSING_NODE')
        elif table=='relation_evidence_authorizations': row.update(link_candidate_id='MISSING_LINK',relation_id='MISSING_REL')
        else: row['relation_id']='MISSING_REL'
        with pytest.raises(sqlite3.IntegrityError): engine._insert_mutation(conn,mutation)
        conn.rollback()
    assert engine.sha256_file(target)==before


@pytest.mark.parametrize('table',DELTA)
def test_each_new_table_late_failure_rolls_back(entry_case,table):
    args=entry_case['args']; mutations=entry_case['payload']['intended_mutations']
    point=max(i for i,m in enumerate(mutations,1) if m['table']==table)
    before=engine.database_identity(args['target_path'])
    with pytest.raises(engine.PromotionError,match='INJECTED_TRANSACTION_FAILURE'):
        execute_foundation_payload(**args,inject_failure_after=point)
    assert engine.database_identity(args['target_path'])==before


@pytest.mark.parametrize('table',DELTA)
@pytest.mark.parametrize('bad',['column','update','delete','replace','key'])
def test_table_contracts_reject_unapproved_columns_and_operations(entry_case,table,bad):
    payload=copy.deepcopy(entry_case['payload'])
    m=next(m for m in payload['intended_mutations'] if m['table']==table)
    if bad=='column': m['row']['unapproved']=1
    elif bad=='key': m['key']={'unapproved':'key'}
    else: m['operation']=bad.upper()
    with pytest.raises(engine.PromotionError): validate_foundation_mutations(payload)


def test_fk_order_is_verified_not_assumed(entry_case):
    payload=copy.deepcopy(entry_case['payload'])
    payload['intended_mutations'].reverse()
    with closing(engine.connect_read_only(entry_case['args']['target_path'])) as conn:
        with pytest.raises(engine.PromotionError,match='FOUNDATION_FK_ORDER_OR_PARENT'):
            validate_insert_dependencies(conn,payload)


@pytest.mark.parametrize('bad',['id','semantic','file','bytes','envelope','payload_sha','payload_file','core','scope','temporal','native','basis_commit','basis_production','basis_schema','missing_basis','missing_artifact','wrong_table','schema_db','baseline_db'])
def test_entry_envelope_errors_precede_writable_open(entry_case,monkeypatch,bad):
    args=dict(entry_case['args']); payload=copy.deepcopy(entry_case['payload'])
    if bad in {'id','semantic','file'}:
        key={'id':'completed_packet_id','semantic':'completed_packet_semantic_sha256','file':'completed_packet_file_sha256'}[bad]
        payload['review_basis'][key]='WRONG'
    elif bad=='bytes': args['completed_artifact']=args['completed_artifact']+b'\n'
    elif bad=='envelope': payload['payload_envelope_contract']['contract_sha256']='0'*64
    elif bad=='payload_file': args['expected_payload_file_sha256']='0'*64
    elif bad=='core': payload['intended_mutations'][0]['row']['title']='TAMPER'
    elif bad=='scope': next(m for m in payload['intended_mutations'] if m['table']=='node_relations')['row']['scope']='all'
    elif bad=='temporal': next(m for m in payload['intended_mutations'] if m['table']=='relation_temporal_semantics')['row']['temporal_category']='current'
    elif bad=='native': next(m for m in payload['intended_mutations'] if m['table']=='relation_evidence_links')['row']['evidence_id']='WRONG'
    elif bad=='wrong_table': payload['intended_mutations'][0]['table']='meta'
    elif bad.startswith('basis_'):
        field={'basis_commit':'expected_payload_implementation_commit','basis_production':'expected_production_sha256','basis_schema':'expected_schema_version'}[bad]
        args['verification_basis']=replace(args['verification_basis'],**{field:'WRONG'})
    elif bad=='missing_basis': args['verification_basis']=None
    elif bad=='missing_artifact': args['completed_artifact']=None
    elif bad in {'schema_db','baseline_db'}:
        with closing(sqlite3.connect(args['target_path'])) as conn:
            conn.execute("UPDATE meta SET value='WRONG' WHERE key='schema_version'" if bad=='schema_db' else 'PRAGMA user_version=123')
            conn.commit()
    sha=engine.canonical_sha256(engine.payload_semantic_body(payload)); payload.update(payload_hash=sha,payload_id='PROMO_'+sha[:16].upper())
    if bad=='payload_sha': payload['payload_hash']='0'*64
    args['payload_artifact']=data(payload)
    if bad!='payload_file': args['expected_payload_file_sha256']=hashlib.sha256(args['payload_artifact']).hexdigest()
    before=engine.sha256_file(args['target_path']); calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError): execute_foundation_payload(**args)
    assert calls==[] and engine.sha256_file(args['target_path'])==before


@pytest.mark.parametrize('bad',['no_auth','no_entry','wrong_payload','wrong_baseline','wrong_commit','wrong_target','shadow_target'])
def test_production_authorization_negatives_open_no_writable_db(entry_case,monkeypatch,bad):
    args=dict(entry_case['args']); args.update(mode=ExecutionTargetMode.PRODUCTION,target_path=args['configured_production_path'],authorization=entry_case['authorization'],entry_qualification=entry_case['entry'])
    if bad=='no_auth': args['authorization']=None
    elif bad=='no_entry': args['entry_qualification']=None
    elif bad=='wrong_target': args['target_path']=entry_case['args']['target_path']
    elif bad=='shadow_target': args['mode']=ExecutionTargetMode.SHADOW
    else:
        bindings=dict(args['authorization'].bindings)
        bindings[{'wrong_payload':'payload_semantic_sha256','wrong_baseline':'expected_production_sha256','wrong_commit':'entry_implementation_commit'}[bad]]='WRONG'
        args['authorization']=replace(args['authorization'],bindings=bindings)
    calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError): execute_foundation_payload(**args)
    assert calls==[]


@pytest.mark.parametrize('field,value',[('qualification_state','REVOKED'),('insert_operations',999)])
def test_receipt_state_and_accounting_not_just_self_hash(entry_case,monkeypatch,field,value):
    args=dict(entry_case['args']); body=json.loads(args['qualification'].artifact)
    body.pop('qualification_receipt_id'); body.pop('qualification_receipt_semantic_sha256')
    body[field]=value; args['qualification']=receipt_ref(body)
    calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError): execute_foundation_payload(**args)
    assert calls==[]


@pytest.mark.parametrize('alias',['hardlink','symlink','resolved'])
def test_shadow_path_aliases_stay_blocked(entry_case,monkeypatch,alias):
    args=dict(entry_case['args']); original=args['configured_production_path']; target=entry_case['root']/('alias-'+alias+'.db')
    if alias=='resolved': target=original.parent/'unused'/ '..'/original.name
    else:
        try:
            if alias=='hardlink': os.link(original,target)
            else: target.symlink_to(original)
        except OSError:
            pytest.skip('Path alias creation unavailable on platform')
    args['target_path']=target
    calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError,match='CONFIGURED_PRODUCTION_WRITE_BLOCKED'): execute_foundation_payload(**args)
    assert calls==[]


def test_synthetic_production_success_and_one_time_journal(entry_case,monkeypatch):
    args=dict(entry_case['args']); args.update(mode=ExecutionTargetMode.PRODUCTION,target_path=args['configured_production_path'],authorization=entry_case['authorization'],entry_qualification=entry_case['entry'])
    assert execute_foundation_payload(**args)['status']=='COMMITTED'
    calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError,match='FOUNDATION_AUTHORIZATION_ALREADY_ATTEMPTED'): execute_foundation_payload(**args)
    assert calls==[]


def test_synthetic_postcommit_failure_uses_governed_restore_and_blocks_retry(entry_case,monkeypatch):
    from pro_a import production_execution as execution
    args=dict(entry_case['args']); args.update(mode=ExecutionTargetMode.PRODUCTION,target_path=args['configured_production_path'],authorization=entry_case['authorization'],entry_qualification=entry_case['entry'])
    before=engine.database_identity(args['target_path'])
    original=execution._write_json_atomic
    def fail_completion(path,value,**kwargs):
        if value['state']=='COMPLETE': raise RuntimeError('SYNTHETIC_POSTCOMMIT_FAILURE')
        return original(path,value,**kwargs)
    monkeypatch.setattr(execution,'_write_json_atomic',fail_completion)
    with pytest.raises(RuntimeError,match='SYNTHETIC_POSTCOMMIT_FAILURE'): execute_foundation_payload(**args)
    assert engine.database_identity(args['target_path'])==before
    journal=args['target_path'].parent/'foundation-executions'/args['authorization'].authorization_id/'execution_journal.json'
    assert json.loads(journal.read_text())['state']=='FAILED_RESTORED'
    calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError,match='FOUNDATION_AUTHORIZATION_ALREADY_ATTEMPTED'): execute_foundation_payload(**args)
    assert calls==[]


@pytest.mark.parametrize('bad',['qualification_bytes','qualification_identity','prediction_bytes','entry_bytes','entry_commit'])
def test_external_receipt_and_prediction_failures_precede_open(entry_case,monkeypatch,bad):
    args=dict(entry_case['args'])
    if bad=='qualification_bytes': args['qualification']=replace(args['qualification'],artifact=args['qualification'].artifact+b'\n')
    if bad=='qualification_identity': args['qualification']=replace(args['qualification'],receipt_id='WRONG')
    if bad=='prediction_bytes': args['predicted_diff_artifact']+=b'\n'
    if bad.startswith('entry_'):
        args.update(mode=ExecutionTargetMode.PRODUCTION,target_path=args['configured_production_path'],authorization=entry_case['authorization'],entry_qualification=entry_case['entry'])
        if bad=='entry_bytes': args['entry_qualification']=replace(args['entry_qualification'],artifact=args['entry_qualification'].artifact+b'\n')
        else: args['execution_commit']='b'*40
    calls=forbid_writable(monkeypatch)
    with pytest.raises(engine.PromotionError): execute_foundation_payload(**args)
    assert calls==[]
