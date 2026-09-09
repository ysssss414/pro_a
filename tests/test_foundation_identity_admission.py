"""V4 identity admission, using synthetic fixtures only."""
import copy
import json

import pytest

from test_phase3f_foundation_baseline import case, complete, handoff, rec, COMMIT, TS
from test_foundation_execution_preparation import governed
from test_foundation_native_evidence import native_case, independent_review
from pro_a.foundation_execution_contract import BOUND_IDENTITY_CONTRACT, CONTRACT_SHA256, relation_review_projection
from pro_a.foundation_identity_admission import identity_plan, preview_eligibility
from pro_a.phase3f_foundation_baseline import build_review_packet, validate_review
from pro_a.production_promotion import PromotionError, canonical_sha256, deterministic_id


@pytest.fixture
def identity_case(governed):
    old = governed['blank']
    evidence = {e['evidence_id']: {k:v for k,v in e.items() if k != 'source_sha256'}
                for c in old['objects']['claims'] for e in c['content']['evidence']}
    objects = {kind:[{'candidate_id':r['candidate_id'],'content':copy.deepcopy(r['content'])} for r in rows]
               for kind,rows in old['objects'].items()}
    for row in objects['nodes']:
        row['content']['supporting_claim_ids'] = []
        row['content']['evidence_refs'] = ['E_C1']
    for row in objects['claims']:
        row['content']['raw']['subject_ref'] = 'N_EXIST'
        row['content']['row']['structured_json'] = json.dumps({'foundation_native':row['content']['raw']})
    for row in objects['aliases']:
        row['content']['raw'] = {'alias':'Independent synthetic alias','target_ref':'NC'}
    for row in objects['relations']:
        row['content'] = relation_review_projection(row,objects['claims'],old['package']['sha256'])
    packet = build_review_packet(package=old['package'],registry=old['registry'],production=old['production_baseline'],
        repository_commit=COMMIT,objects=objects,timestamp=TS,execution_contract=BOUND_IDENTITY_CONTRACT,
        identity_evidence_index=evidence)
    governed['blank'] = packet
    governed['snapshot'] = {t:governed['db'].all(f'SELECT * FROM {t}') for t in
        ('nodes','node_aliases','sources','claims','node_relations','relation_evidence_links','relation_temporal_semantics','relation_evidence_authorizations')}
    return governed


def decisions(packet):
    result = {r['candidate_id']:copy.deepcopy(r['human_input']) for rows in complete(packet)['objects'].values() for r in rows}
    result['A1']['target_id'] = 'NC'
    return result


def test_exact_reuse_and_create_without_claim_support(identity_case):
    p = identity_case['blank']; d = decisions(p)
    d['C1']['decision'] = 'KEEP_NEEDS_REVIEW'
    plan = identity_plan(p,identity_case['snapshot'],d)
    assert plan['nodes']['NR']['resolved_runtime_target_id'] == 'N_EXIST'
    assert plan['nodes']['NC']['resolved_runtime_target_id'] == deterministic_id('NODE',{'package':p['package']['sha256'],'candidate_id':'NC'})
    assert p['human_completion'] == {'reviewer':'','reason':''}


@pytest.mark.parametrize('node', ['NC','NR'])
def test_nonkeep_derived_support_is_not_identity_authority(identity_case,node):
    p = copy.deepcopy(identity_case['blank']); d = decisions(p)
    rec(p,node)['content']['supporting_claim_ids'] = ['C1']
    d['C1']['decision'] = 'KEEP_NEEDS_REVIEW'
    assert node in identity_plan(p,identity_case['snapshot'],d)['nodes']


@pytest.mark.parametrize('mode',['wrong','missing','inactive'])
def test_reuse_exact_active_identity_required(identity_case,mode):
    p = identity_case['blank']; d = decisions(p); s = copy.deepcopy(identity_case['snapshot'])
    if mode == 'wrong':
        d['NR']['target_id'] = 'N_PEER'
    elif mode == 'missing':
        s['nodes'] = [n for n in s['nodes'] if n['node_id'] != 'N_EXIST']
    else:
        next(n for n in s['nodes'] if n['node_id']=='N_EXIST')['status'] = 'inactive'
    with pytest.raises(PromotionError,match='NODE_REUSE'):
        identity_plan(p,s,d)


@pytest.mark.parametrize('bad',['missing','unknown','source','hash','collision'])
def test_create_identity_provenance_and_collision_fail_closed(identity_case,bad):
    p = copy.deepcopy(identity_case['blank']); d = decisions(p)
    c = rec(p,'NC')['content']
    if bad == 'missing': c['evidence_refs'] = []
    if bad == 'unknown': c['evidence_refs'] = ['NOT_PRESENT']
    if bad == 'source': p['identity_evidence_index']['E_C1']['source_id'] = 'NOT_PRESENT'
    if bad == 'hash': p['identity_evidence_index']['E_C1']['excerpt'] = 'tampered'
    if bad == 'collision': c['canonical_name'] = 'SYNTHETIC EXISTING'
    with pytest.raises(PromotionError): identity_plan(p,identity_case['snapshot'],d)


@pytest.mark.parametrize('target',['NC','NR'])
def test_alias_candidate_reference_preserved_and_compiled(identity_case,target):
    p = copy.deepcopy(identity_case['blank']); d = decisions(p)
    rec(p,'A1')['content']['target_ref'] = target; d['A1']['target_id'] = target
    plan = identity_plan(p,identity_case['snapshot'],d)
    alias = plan['aliases']['A1']
    assert alias['approved_semantic_target_ref'] == target
    assert alias['resolved_runtime_target_id'] == plan['nodes'][target]['resolved_runtime_target_id']
    assert d['A1']['target_id'] == target


@pytest.mark.parametrize('decision',['DEFER','REJECT',''])
def test_alias_candidate_must_be_executable(identity_case,decision):
    p = identity_case['blank']; d = decisions(p); d['NC']['decision'] = decision
    with pytest.raises(PromotionError,match='NODE_REFERENCE_NON_EXECUTABLE'):
        identity_plan(p,identity_case['snapshot'],d)


@pytest.mark.parametrize('alias',['Synthetic created','SYNTHETIC CREATED','Ｓｙｎｔｈｅｔｉｃ created'])
def test_canonical_equivalent_attach_is_audited_noop(identity_case,alias):
    p = copy.deepcopy(identity_case['blank']); d = decisions(p)
    rec(p,'A1')['content']['alias'] = alias
    result = identity_plan(p,identity_case['snapshot'],d)['aliases']['A1']
    assert result['compile_effect'] == 'ATTACH_NOOP_CANONICAL_EQUIVALENT'
    assert result['human_decision'] == d['A1']['decision'] == 'ATTACH'
    assert result['runtime_alias_mutation_count'] == 0


def test_alias_different_owner_fails_even_for_target_canonical(identity_case):
    p = copy.deepcopy(identity_case['blank']); d = decisions(p); s = copy.deepcopy(identity_case['snapshot'])
    rec(p,'A1')['content']['alias'] = 'Synthetic created'
    s['node_aliases'].append({'alias':'SYNTHETIC CREATED','node_id':'N_EXIST'})
    with pytest.raises(PromotionError,match='NODE_COLLISION|ALIAS_COLLISION'):
        identity_plan(p,s,d)


def test_direct_existing_refs_do_not_require_parallel_candidate(identity_case):
    p = identity_case['blank']; d = decisions(p); d['NR']['decision'] = 'DEFER'
    d['NP']['decision'] = 'DEFER'
    # Point all direct consumers at their frozen existing identities.
    p = copy.deepcopy(p)
    for r in p['objects']['relations']:
        r['content']['from_ref'] = 'N_EXIST'; r['content']['to_ref'] = 'N_PEER'
        d[r['candidate_id']]['decision'] = 'DEFER'
    rec(p,'B1')['content']['target_ref'] = 'N_EXIST'
    plan = identity_plan(p,identity_case['snapshot'],d)
    assert plan['references']['N_EXIST'] == 'N_EXIST'
    assert 'NR' not in plan['references']
    assert rec(p,'C1')['content']['raw']['subject_ref'] in plan['references']
    assert rec(p,'B1')['content']['target_ref'] in plan['references']


def test_synthetic_compiler_noop_and_nonkeep_claim_not_promoted(identity_case):
    from test_phase3f_foundation_baseline import reseal
    p = identity_case['blank']
    rec(p,'A1')['content']['alias'] = 'SYNTHETIC CREATED'
    reseal(identity_case)
    completed = complete(p)
    rec(completed,'A1')['human_input']['target_id'] = 'NC'
    rec(completed,'C1')['human_input']['decision'] = 'KEEP_NEEDS_REVIEW'
    rec(completed,'B1')['human_input']['decision'] = 'DEFER'
    for r in completed['objects']['relations']:
        r['human_input']['decision'] = 'DEFER'
    payload = handoff(identity_case,completed)['payload']
    assert not any(m['table']=='claims' and m['row']['claim_id']=='C1' for m in payload['intended_mutations'])
    assert not any(m['table']=='node_aliases' for m in payload['intended_mutations'])
    assert next(x for x in payload['mapping'] if x['candidate_id']=='A1')['compile_effect'] == 'ATTACH_NOOP_CANONICAL_EQUIVALENT'
    assert rec(completed,'A1')['human_input']['target_id'] == 'NC'


def test_preview_is_blank_non_authorizing_and_strict(identity_case):
    p = identity_case['blank']; d = decisions(p); before = canonical_sha256(p)
    result = preview_eligibility(p,identity_case['snapshot'],d)
    assert result['dependency_closure'] == 'PASS' and result['executable_payload_built'] is False
    assert canonical_sha256(p) == before
    validate_review(p,expected_sha256=p['immutable_packet_sha256'],completed=False)
    d['C1']['decision'] = 'KEEP_NEEDS_REVIEW'
    with pytest.raises(PromotionError,match='RELATION_CLAIM_ADMISSION_BLOCKED'):
        preview_eligibility(p,identity_case['snapshot'],d)


def test_v4_explicitly_binds_unchanged_storage_evidence_contract():
    assert BOUND_IDENTITY_CONTRACT['storage_evidence_contract_sha256'] == CONTRACT_SHA256
    assert BOUND_IDENTITY_CONTRACT['contract_sha256'] != CONTRACT_SHA256


@pytest.mark.parametrize('target',['NC','NR'])
def test_runtime_alias_mutation_uses_final_id(identity_case,target):
    from test_phase3f_foundation_baseline import reseal
    rec(identity_case['blank'],'A1')['content']['target_ref'] = target
    reseal(identity_case)
    packet = complete(identity_case['blank'])
    rec(packet,'A1')['human_input']['target_id'] = target
    before = copy.deepcopy(packet)
    payload = handoff(identity_case,packet)['payload']
    aliases = [m['row'] for m in payload['intended_mutations'] if m['table']=='node_aliases']
    expected = 'N_EXIST' if target=='NR' else deterministic_id('NODE',{'package':packet['package']['sha256'],'candidate_id':'NC'})
    assert aliases == [{'alias':'Independent synthetic alias','node_id':expected}]
    assert packet == before


def test_direct_existing_consumers_and_schema_023_e2e(identity_case):
    from contextlib import closing
    from test_phase3f_foundation_baseline import reseal
    from pro_a.production_promotion import apply_payload_to_shadow, copy_production_to_shadow, connect_read_only
    from pro_a.foundation_schema_preparation import require_execution_schema
    p = identity_case['blank']
    for r in p['objects']['relations']:
        if r['content']['from_ref'] == 'NR': r['content']['from_ref'] = 'N_EXIST'
        if r['content']['to_ref'] == 'NR': r['content']['to_ref'] = 'N_EXIST'
        if r['content']['to_ref'] == 'NP': r['content']['to_ref'] = 'N_PEER'
    rec(p,'B1')['content']['target_ref'] = 'N_EXIST'
    rec(p,'A1')['content']['target_ref'] = 'N_EXIST'
    reseal(identity_case)
    packet = complete(p)
    rec(packet,'A1')['human_input']['target_id'] = 'N_EXIST'
    rec(packet,'NR')['human_input']['decision'] = 'DEFER'
    rec(packet,'NP')['human_input']['decision'] = 'REJECT'
    payload = handoff(identity_case,packet)['payload']
    assert any(m['table']=='current_views' and m['row']['node_id']=='N_EXIST' for m in payload['intended_mutations'])
    assert any(m['table']=='node_relations' and m['row']['to_node_id']=='N_EXIST' for m in payload['intended_mutations'])
    assert any(m['table']=='claims' and m['row']['claim_id']=='C1' for m in payload['intended_mutations'])
    shadow = identity_case['root'] / 'v4-synthetic-shadow.db'
    copy_production_to_shadow(identity_case['production'],shadow,p['production_baseline']['sha256'])
    apply_payload_to_shadow(payload,shadow,identity_case['production'], **identity_case["verification"])
    with closing(connect_read_only(shadow)) as conn:
        require_execution_schema(conn)
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('decision',['KEEP_NEEDS_REVIEW','DROP'])
def test_v4_claim_linked_stays_strict_in_real_synthetic_compiler(identity_case,decision):
    p = complete(identity_case['blank'])
    rec(p,'A1')['human_input']['target_id']='NC'
    rec(p,'C1')['human_input']['decision']=decision
    with pytest.raises(PromotionError,match='RELATION_CLAIM_ADMISSION_BLOCKED'):
        handoff(identity_case,p)


def test_v4_baseline_support_stays_strict(identity_case):
    p = complete(identity_case['blank']); rec(p,'A1')['human_input']['target_id']='NC'
    rec(p,'C1')['human_input']['decision']='KEEP_NEEDS_REVIEW'
    for r in p['objects']['relations']: r['human_input']['decision']='DEFER'
    with pytest.raises(PromotionError,match='BASELINE_CLAIM_NON_EXECUTABLE'):
        handoff(identity_case,p)


def test_v4_keep_qualification_and_candidate_subject_stay_strict(identity_case):
    from test_phase3f_foundation_baseline import reseal
    p = identity_case['blank']
    rec(p,'C1')['content']['qualification_status']='REVIEW_REQUIRED'
    reseal(identity_case)
    completed=complete(p); rec(completed,'A1')['human_input']['target_id']='NC'
    with pytest.raises(PromotionError,match='CLAIM_EXCEPTION_UNRESOLVED'):
        handoff(identity_case,completed)
    rec(p,'C1')['content']['qualification_status']='DETERMINISTICALLY_MAPPABLE'
    rec(p,'C1')['content']['raw']['subject_ref']='NC'
    rec(p,'C1')['content']['row']['structured_json']=json.dumps({'foundation_native':rec(p,'C1')['content']['raw']})
    reseal(identity_case)
    completed=complete(p); rec(completed,'A1')['human_input']['decision']='DEFER'; rec(completed,'NC')['human_input']['decision']='DEFER'
    with pytest.raises(PromotionError,match='KEEP_CLAIM_WITH_NONEXECUTABLE_SUBJECT'):
        handoff(identity_case,completed)


def test_preview_link_cannot_be_used_as_runtime_authority(identity_case):
    from pro_a.foundation_execution_contract import evidence_link_row, authorization_row
    p=identity_case['blank']; preview=preview_eligibility(p,identity_case['snapshot'],decisions(p))
    link=preview['relation_checks'][0]['evidence_eligibility'][0]
    with pytest.raises(PromotionError,match='PREVIEW_IS_NOT_RUNTIME_AUTHORITY'):
        evidence_link_row(link,'R_SYNTHETIC',TS)
    with pytest.raises(PromotionError,match='PREVIEW_IS_NOT_RUNTIME_AUTHORITY'):
        authorization_row(link,rec(p,'R1'),'R_SYNTHETIC',p)


def test_reuse_alias_noop_compares_actual_target_canonical(identity_case):
    p=copy.deepcopy(identity_case['blank']); d=decisions(p); s=copy.deepcopy(identity_case['snapshot'])
    s['node_aliases'].append({'alias':'Existing synonym','node_id':'N_EXIST'})
    rec(p,'NR')['content']['canonical_name']='Existing synonym'
    rec(p,'A1')['content']['target_ref']='NR'; d['A1']['target_id']='NR'
    rec(p,'A1')['content']['alias']='SYNTHETIC EXISTING'
    result=identity_plan(p,s,d)['aliases']['A1']
    assert result['compile_effect']=='ATTACH_NOOP_CANONICAL_EQUIVALENT'
    rec(p,'A1')['content']['alias']='Existing synonym'
    assert identity_plan(p,s,d)['aliases']['A1']['compile_effect']=='ATTACH_NOOP_ALREADY_PRESENT'


def test_v4_native_authority_reuses_exact_schema_guards(native_case):
    from contextlib import closing
    from pro_a.production_promotion import copy_production_to_shadow, apply_payload_to_shadow, connect_read_only
    from pro_a.foundation_schema_preparation import require_execution_schema
    old=native_case['blank']
    evidence={e['evidence_id']:{k:v for k,v in e.items() if k!='source_sha256'} for c in old['objects']['claims'] for e in c['content']['evidence']}
    objects={kind:[{'candidate_id':r['candidate_id'],'content':copy.deepcopy(r['content'])} for r in rows] for kind,rows in old['objects'].items()}
    for r in objects['nodes']:
        r['content']['evidence_refs']=['E_C1']; r['content']['supporting_claim_ids']=[]
    for r in objects['claims']:
        r['content']['raw']['subject_ref']='N_EXIST'
        r['content']['row']['structured_json']=json.dumps({'foundation_native':r['content']['raw']})
    for r in objects['relations']:
        r['content']=relation_review_projection(r,objects['claims'],old['package']['sha256'],r['content']['relation_native_authorizations'])
    native_case['blank']=build_review_packet(package=old['package'],registry=old['registry'],production=old['production_baseline'],
        repository_commit=COMMIT,objects=objects,timestamp=TS,execution_contract=BOUND_IDENTITY_CONTRACT,
        evidence_governance_manifest=native_case['manifest'],identity_evidence_index=evidence)
    packet=independent_review(native_case)
    rec(packet,'A1')['human_input']['target_id']='NC'
    payload=handoff(native_case,packet)['payload']
    shadow=native_case['root']/'native-v4-shadow.db'
    copy_production_to_shadow(native_case['production'],shadow,old['production_baseline']['sha256'])
    apply_payload_to_shadow(payload,shadow,native_case['production'], **native_case["verification"])
    with closing(connect_read_only(shadow)) as conn:
        require_execution_schema(conn)
        assert conn.execute("SELECT count(*) FROM relation_evidence_links WHERE provenance_mode='RELATION_NATIVE' AND status='active'").fetchone()[0]==2
        assert conn.execute("SELECT count(*) FROM claims WHERE claim_id='C1'").fetchone()[0]==0
    assert packet['evidence_governance_manifest']==old['evidence_governance_manifest']
