"""Explicit bounded-only operator qualification; synthetic transport exclusively."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import hashlib
import json
import threading

import pytest

from pro_a.analyzer import SourcePiece
from pro_a import bounded_extraction, output_decomposition
from pro_a.cloud_contract import digest
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from pro_a.workbench import bounded_extraction_persistence as persistence
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.bounded_resume import COMPLETE, contract
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.source_operations import SourceOperationError, SourceOperations
from series_binding_helpers import Transport, ToolResponse, batch_record, request_parts, response_content, rows, synthetic_providers
from test_phase43_stage71_shared_core_pending import case
from test_workbench_stage7 import clean_pdf, upload
from test_cloud_operation_adapter_binding import setup_run


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request',lambda *a,**k:pytest.fail('EXTERNAL_NETWORK_FORBIDDEN'))


def topology(tmp_path, monkeypatch, counts=(65,81,81,81,49), *, accepted_retry=True):
    value = case(tmp_path)
    path = value['phase4_config']
    path.write_text(path.read_text().replace('enabled = false\nmodel = "fake-semantic-v1"','enabled = true\nmodel = "deepseek-flash"'),encoding='utf-8')
    monkeypatch.setenv('PROA_LLM_API_KEY','synthetic-transport-only')
    cloud = CloudProfile('deepseek','deepseek-flash')
    service = SourceOperations(value['config'],value['source_profile'],cloud)
    source = upload(value,clean_pdf(tmp_path))
    run_id = service.start(source['source_id'],idempotency_key='bounded-only-synthetic-start')['run']['processing_run_id']
    pieces = []
    plan_sha = digest({'synthetic_counts':counts})
    for ordinal,count in enumerate(counts,1):
        text = '\n'.join(f'Synthetic Company product {ordinal}-{i} has {i+1} units.' for i in range(count))
        piece = SourcePiece(ordinal,len(counts),'',0,text,text)
        pieces.append({'piece_id':piece.piece_id,'piece_index':ordinal,'piece_count':len(counts),
                       'source_text':text,'source_piece_sha256':piece.source_sha256,'user_prompt':text,
                       'user_prompt_sha256':piece.prompt_sha256,'system_prompt_sha256':hashlib.sha256(SOURCE_ANALYSIS_SYSTEM.encode()).hexdigest(),
                       'initial_plan_sha256':plan_sha,'source_piece':asdict(piece),'scoped_node_catalog':[]})
    plan = {'run_id':'SYNTHETIC_NATIVE_RUN','source_id':source['source_id'],'source_sha256':source['source_sha256'],
            'plan':{'initial_extraction_plan_sha256':plan_sha},'pieces':pieces}
    monkeypatch.setattr('pro_a.workbench.source_operations.plan_external_source_analysis',lambda *a,**k:plan)
    service.advance_once(worker_id='fixture-planner',processing_run_id=run_id)
    value.update(service=service,run_id=run_id,cloud_profile=cloud,production_before=value['config'].knowledge_db.read_bytes())
    if accepted_retry:
        transport = Transport(mode=lambda _target,n:'malformed' if n==2 else None)
        with synthetic_providers(value,transport) as providers:
            service.advance_once(worker_id='fixture-prior',processing_run_id=run_id,provider=providers)
            assert service.advance_once(worker_id='fixture-prior',processing_run_id=run_id,provider=providers)['state']=='BLOCKED'
            first = rows(value,'bounded_extraction_attempts')[-1]
            service.retry_failed_extraction(run_id,first['attempt_id'],retry_reason='MALFORMED_PROVIDER_JSON',idempotency_key='fixture-explicit-retry')
            service.output_batches.advance(service.get_run(run_id),providers,'fixture-retry')
        assert len(transport.calls)==3
    return value


def tripwires(monkeypatch):
    def forbidden(*a,**k):
        pytest.fail('BOUNDARY_TRIPWIRE')
    for name in ('pro_a.bounded_extraction.initial_extraction_plan',
                 'pro_a.workbench.bounded_extraction_store.initial_extraction_plan',
                 'pro_a.analyzer.Analyzer.plan_initial_extraction',
                 'pro_a.operational_ingestion.plan_external_source_analysis',
                 'pro_a.workbench.source_operations.plan_external_source_analysis',
                 'pro_a.bounded_extraction.subdivide_extraction_plan',
                 'pro_a.workbench.bounded_extraction_store.subdivide_extraction_plan',
                 'pro_a.workbench.bounded_extraction_store.BoundedExtractionStore.subdivide',
                 'pro_a.workbench.bounded_extraction_store.BoundedExtractionStore.subdivide_after_truncation',
                 'pro_a.workbench.bounded_extraction_store.BoundedExtractionStore.create',
                 'pro_a.workbench.bounded_source_analysis.BoundedSourceAnalysisRunner.bind',
                 'pro_a.workbench.source_operations.SourceOperations._register_input',
                 'pro_a.workbench.source_operations.SourceOperations._bind_job',
                 'pro_a.workbench.source_operations.resume_execution',
                 'pro_a.workbench.source_operations.SourceOperations._copy_and_register_packet'):
        monkeypatch.setattr(name,forbidden)


def resume(value,providers=None,*,key='bounded-only-explicit-0001',ceiling=25,worker='bounded-only-worker'):
    return value['service'].resume_bounded_extraction_only(value['run_id'],worker_id=worker,
                idempotency_key=key,max_new_calls=ceiling,provider=providers)


def events(value,kind):
    return [r for r in rows(value,'source_processing_events') if r['event_type']==kind]


def test_run13_topology_pending_only_multi_series_retry_and_aggregate(tmp_path,monkeypatch):
    value=topology(tmp_path,monkeypatch)
    before=rows(value,'bounded_extraction_attempts')
    results=rows(value,'bounded_extraction_segment_results')
    raws={p.name:p.read_bytes() for p in value['config'].artifact_root.rglob('*.raw.json')}
    assert len(rows(value,'bounded_extraction_series'))==5
    assert len(rows(value,'bounded_extraction_segments'))==27 and len(results)==2
    tripwires(monkeypatch)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        result=resume(value,providers)
        assert result['status']==COMPLETE and result['new_provider_calls']==25
        assert result['pending_segments']==0 and result['run']['stage']==COMPLETE
        assert len(transport.calls)==25 and providers['SEMANTIC_DECOMPOSITION'].call_count==0
        again=resume(value,providers)
        assert again['duplicate'] and len(transport.calls)==25
        assert resume(value,providers,key='bounded-only-after-complete')['status']=='ALREADY_BOUNDED_COMPLETE'
    assert rows(value,'bounded_extraction_attempts')[:3]==before
    assert rows(value,'bounded_extraction_segment_results')[:2]==results
    assert all(p.read_bytes()==raws[p.name] for p in value['config'].artifact_root.rglob('*.raw.json') if p.name in raws)
    assert len(rows(value,'bounded_extraction_dispatches'))==28
    assert len(rows(value,'bounded_extraction_series_results'))==5
    assert len(events(value,COMPLETE))==1
    assert not rows(value,'source_processing_jobs')
    assert value['config'].knowledge_db.read_bytes()==value['production_before']
    assert not [r for r in rows(value,'registered_packets') if r['artifact_kind']=='REVIEW_PACKET']
    bindings=value['service'].output_batches.inputs(value['service'].get_run(value['run_id']))
    accepted=rows(value,'bounded_extraction_segment_results')
    assert before[1]['attempt_id'] not in {r['attempt_id'] for r in accepted}
    for _,context,catalog,series in bindings:
        aggregate=value['service'].output_batches.ledger.aggregate(series.series_id)
        assert aggregate['coverage']['closed_refs']==list(series.eligible_evidence_refs)
        bounded_extraction.expand_source_analysis_wire_v3(aggregate['wire'],catalog,context)
    order=[request_parts(call)[0]['series_id'] for call in transport.calls]
    assert order==[binding[3].series_id for binding,count in zip(bindings,(3,6,6,6,4)) for _ in range(count)]


@pytest.mark.parametrize('mode',['malformed','truncated','unknown','invalid_shape','claim_linkage','ownership','http','oversized'])
def test_first_failure_stops_without_retry_subdivision_or_semantic(tmp_path,monkeypatch,mode):
    value=topology(tmp_path,monkeypatch)
    tripwires(monkeypatch)
    class Failure(Transport):
        def __call__(self,endpoint,**kwargs):
            if len(self.calls)!=2:
                return super().__call__(endpoint,**kwargs)
            self.calls.append(kwargs['json'])
            target,source=request_parts(kwargs['json'])
            if mode in ('malformed','truncated','unknown'):
                self.calls.pop(); self.mode=lambda _target,n:mode if n==3 else None
                return super().__call__(endpoint,**kwargs)
            if mode=='http':
                response=ToolResponse('{}'); response.status_code=503; return response
            record=batch_record(json.loads(response_content(target,source)),target)
            if mode=='invalid_shape': record['unexpected']='invalid'
            if mode=='claim_linkage': record['evidence_acknowledgements'][0]['claim_refs']=[]
            if mode=='ownership': record['node_candidates'][0]['ownership_evidence_ref']='EV_FOREIGN'
            return ToolResponse(json.dumps(record),output=24001 if mode=='oversized' else 50)
    transport=Failure()
    with synthetic_providers(value,transport) as providers:
        result=resume(value,providers)
        assert result['status'] in ('STOP_ON_FIRST_NEW_FAILURE','STOP_RECOVERY_REQUIRED')
        assert len(transport.calls)==3
        resume(value,providers,key='bounded-only-after-failure')
        assert len(transport.calls)==3
        assert providers['SEMANTIC_DECOMPOSITION'].call_count==0
    assert len(rows(value,'bounded_extraction_dispatches'))==6
    assert len(rows(value,'bounded_extraction_segments'))==27
    assert len(rows(value,'bounded_extraction_attempts'))==6
    assert not events(value,COMPLETE) and not rows(value,'source_processing_jobs')


@pytest.mark.parametrize('window',['bounded_resume_before_advance','attempt_reserved','dispatch_durable',
    'raw_artifact_durable','outcome_durable','result_accepted','aggregate_artifact_durable',
    'bounded_resume_before_complete','bounded_resume_complete_durable'])
def test_crash_windows_recover_using_existing_ledger(tmp_path,monkeypatch,window):
    value=topology(tmp_path,monkeypatch,counts=(1,),accepted_retry=False)
    tripwires(monkeypatch)
    def crash(name):
        if name==window: raise RuntimeError('SYNTHETIC_CRASH')
    monkeypatch.setattr(persistence,'checkpoint',crash)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        with pytest.raises(RuntimeError,match='SYNTHETIC_CRASH'): resume(value,providers)
        used=len(transport.calls)
        monkeypatch.setattr(persistence,'checkpoint',lambda _name:None)
        result=resume(value,providers)
        if window=='dispatch_durable':
            assert result['status']=='STOP_RECOVERY_REQUIRED' and len(transport.calls)==0
            assert not rows(value,'bounded_extraction_segment_results')
        else:
            assert result['bounded_complete'] is True,result
            assert len(transport.calls)==1
            if used: assert len(transport.calls)==used
            assert len(rows(value,'bounded_extraction_attempts'))==1
            assert len(rows(value,'bounded_extraction_series_results'))==1
            assert len(events(value,COMPLETE))==1
            assert not rows(value,'source_processing_jobs')


def test_action_ceiling_idempotency_and_concurrency(tmp_path,monkeypatch):
    value=topology(tmp_path,monkeypatch,counts=(33,),accepted_retry=False)
    tripwires(monkeypatch)
    entered,release=threading.Event(),threading.Event()
    def callback(_request): entered.set(); assert release.wait(15)
    transport=Transport(callback=callback)
    with synthetic_providers(value,transport) as providers,ThreadPoolExecutor(2) as pool:
        first=pool.submit(resume,value,providers,ceiling=1)
        assert entered.wait(15)
        duplicate=pool.submit(resume,value,providers,ceiling=1,worker='second-worker').result(timeout=15)
        assert duplicate['status']=='LEASE_BUSY'
        release.set()
        result=first.result(timeout=30)
        assert result['status']=='CALL_CEILING_REACHED' and result['new_provider_calls']==1
        assert resume(value,providers,ceiling=1)['duplicate']
        with pytest.raises(SourceOperationError,match='IDEMPOTENCY_CONFLICT'): resume(value,providers,ceiling=2)
        assert len(transport.calls)==1
        assert resume(value,providers,key='bounded-only-next-action',ceiling=2)['bounded_complete']
    assert len(transport.calls)==3


def test_last_segment_then_later_explicit_full_continuation(tmp_path,monkeypatch):
    value=setup_run(tmp_path,monkeypatch)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        with monkeypatch.context() as isolated:
            tripwires(isolated)
            assert resume(value,providers)['bounded_complete']
            assert not rows(value,'source_processing_jobs')
        assert value['service'].advance_once(worker_id='later-full-operator',processing_run_id=value['run_id'],provider=providers)['state']=='SEMANTIC_PROCESSING'
        jobs=rows(value,'source_processing_jobs')
        assert len(jobs)==1 and providers['SEMANTIC_DECOMPOSITION'].call_count==0
        value['service'].advance_once(worker_id='later-full-operator',processing_run_id=value['run_id'])
        assert rows(value,'source_processing_jobs')==jobs
        assert len(transport.calls)==1


def test_frozen_budget_cannot_be_raised_by_operator(tmp_path,monkeypatch):
    value=topology(tmp_path,monkeypatch,counts=(33,),accepted_retry=False)
    # Exercise boundary preflight independently of the unchanged store budget guards.
    original=BoundedExtractionStore.read
    def exhausted(self,sid):
        series,plan,state,usage=original(self,sid)
        return series,plan,{**state,'provider_call_reservations':series.budget.max_provider_calls},usage
    monkeypatch.setattr(BoundedExtractionStore,'read',exhausted)
    tripwires(monkeypatch)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        result=resume(value,providers,ceiling=999)
    assert result['failure_code']=='STOP_BUDGET_INSUFFICIENT'
    assert not transport.calls and not rows(value,'bounded_extraction_attempts')


def test_boundary_contract_schema_and_no_implicit_action(tmp_path,monkeypatch):
    value=topology(tmp_path,monkeypatch,counts=(1,),accepted_retry=False)
    assert contract()['plan_source']=='DURABLE_FROZEN_PLAN_ONLY'
    assert not contract()['automatic_retry'] and not contract()['semantic_registration_allowed']
    for _ in range(2): value['service'].get_run(value['run_id'])
    assert not rows(value,'bounded_extraction_dispatches')
    with value['service'].store.connect() as c:
        assert c.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0]=='12'


def test_boundary_refuses_preexisting_semantic_registration_without_dispatch(tmp_path,monkeypatch):
    from pro_a.workbench.bounded_resume import _frontier
    value=topology(tmp_path,monkeypatch,counts=(1,),accepted_retry=False)
    service=value['service']
    monkeypatch.setattr(service.output_batches,'inputs',lambda run:[])
    # A read-only precondition must fail even if full orchestration previously
    # crashed between Semantic job registration and its Run-state transition.
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,statement,args):
            assert 'SEMANTIC_DECOMPOSITION' in statement
            return self
        def fetchone(self):return (1,)
    run=service.get_run(value['run_id'])
    monkeypatch.setattr(service.store,'connect',lambda:Connection())
    with pytest.raises(SourceOperationError,match='BOUNDED_RESUME_SEMANTIC_ALREADY_REGISTERED'):
        _frontier(service,run)


def test_absent_historical_runner_remains_a_changed_surface():
    from pathlib import Path
    from pro_a.workbench import retry_compatibility as compatibility
    name='workbench/bounded_source_analysis.py'
    current=(Path(compatibility.__file__).parent.parent/name).read_bytes()
    assert compatibility._ast_sha256(b'',None,name=name)!=compatibility._ast_sha256(current,None,name=name)


@pytest.mark.parametrize('capacity',[
    {'wip_state':'HARD_STOP','unprojected_review_packets':0,'intake_paused':False},
    {'wip_state':'NORMAL','unprojected_review_packets':1,'intake_paused':False},
    {'wip_state':'NORMAL','unprojected_review_packets':0,'intake_paused':True},
])
def test_capacity_stops_before_dispatch_without_subdivision(tmp_path,monkeypatch,capacity):
    value=topology(tmp_path,monkeypatch,counts=(1,),accepted_retry=False)
    tripwires(monkeypatch)
    monkeypatch.setattr('pro_a.workbench.bounded_resume.stage1_capacity',lambda _connection:capacity)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        result=resume(value,providers)
    assert result['status']=='STOP_CAPACITY' and result['new_provider_calls']==0
    assert not transport.calls and not rows(value,'bounded_extraction_attempts')
    assert not rows(value,'source_processing_jobs') and not events(value,COMPLETE)


@pytest.mark.parametrize('kind',['cloud','native'])
def test_r2_does_not_inherit_old_boundary_cloud_authorization(kind):
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    _execution_surface_comparison.cache_clear()
    result=_execution_surface_comparison(kind,'1d700d95cc394174120ae55144660c769b4efc51')
    # R2 changes the response contract; only unchanged native research execution
    # stays exact. The historical boundary qualification cannot authorize V3.
    assert result['compatible'] is (kind=='native'),result
    # The qualification creation helper is now bound; old cloud code lacks it.
    assert result['reason']==('SEMANTIC_SURFACE_EXACT' if kind=='native'
                             else 'EXECUTION_SURFACE_UNAVAILABLE:RetryCompatibilityError'),result


@pytest.mark.parametrize('mutation',[
    ('bounded_extraction.py',b'range(root_count)',b'range(root_count+1)'),
    ('bounded_extraction.py',b'"INVALID_TERMINAL_ASSIGNMENT"',b'"CHANGED_COVERAGE"'),
    ('workbench/bounded_source_analysis.py',b'allow_new_subdivision=True',b'allow_new_subdivision=False'),
    ('workbench/bounded_source_analysis.py',b'configuration["timeout_seconds"] ==',b'configuration["timeout_seconds"] !='),
])
def test_compatibility_normalization_does_not_hide_policy_or_validation_changes(mutation):
    from pathlib import Path
    from pro_a.workbench import retry_compatibility as compatibility
    name,old,new=mutation
    source=(Path(compatibility.__file__).parent.parent/name).read_bytes()
    assert old in source
    assert compatibility._ast_sha256(source,None,name=name)!=compatibility._ast_sha256(source.replace(old,new),None,name=name)


@pytest.mark.parametrize('count',[1,16,17,49,81])
def test_frozen_root_validation_equivalent_without_planning(count):
    from dataclasses import replace
    from test_output_decomposition import fixture
    from pro_a.bounded_extraction import _plan, BoundedExtractionError
    _,_,series,plan=fixture(count)
    _plan(series,plan)
    if len(plan.segments)>1:
        with pytest.raises(BoundedExtractionError): _plan(series,replace(plan,segments=plan.segments[::-1]))
    with pytest.raises(BoundedExtractionError): _plan(series,replace(plan,segments=plan.segments[:-1]))
    changed=replace(plan.segments[0],range_end=plan.segments[0].range_end+1)
    with pytest.raises(BoundedExtractionError): _plan(series,replace(plan,segments=(changed,)+plan.segments[1:]))


def test_existing_frozen_subdivision_is_executed_without_new_children(tmp_path,monkeypatch):
    value=topology(tmp_path,monkeypatch,counts=(16,),accepted_retry=False)
    with synthetic_providers(value,Transport(mode='truncated')) as providers:
        value['service'].output_batches.advance(value['service'].get_run(value['run_id']),providers,'old-full-path')
    before=rows(value,'bounded_extraction_segments')
    assert len(before)==3 and sum(r['state']=='SUPERSEDED_BY_CHILDREN' for r in before)==1
    tripwires(monkeypatch)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        assert resume(value,providers,ceiling=2)['bounded_complete']
    assert len(transport.calls)==2
    after=rows(value,'bounded_extraction_segments')
    assert {r['segment_id'] for r in after}=={r['segment_id'] for r in before}
    assert len(rows(value,'bounded_extraction_dispatches'))==3


@pytest.mark.parametrize('window',['raw_artifact_durable','outcome_durable','result_accepted','bounded_resume_before_complete'])
def test_hard_process_crash_fresh_process_recovery_without_recall(tmp_path,monkeypatch,window):
    import os
    from pathlib import Path
    import subprocess
    import sys
    value=topology(tmp_path,monkeypatch,counts=(1,),accepted_retry=False)
    document={'config':asdict(value['config']),'phase4_config':str(value['phase4_config']),'run_id':value['run_id']}
    path=tmp_path/'synthetic-crash-input.json'
    path.write_text(json.dumps(document,default=str),encoding='utf-8')
    bootstrap='''
import json,os,socket,sys
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.source_operations import SourceOperations,SourceProfile
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench import bounded_extraction_persistence as persistence
from series_binding_helpers import synthetic_providers,Transport
def forbidden(*a,**k):raise AssertionError('NETWORK_OR_PLANNER_FORBIDDEN')
socket.socket.connect=forbidden
v=json.loads(Path(sys.argv[1]).read_text())
for key in ('knowledge_db','state_db','artifact_root'):v['config'][key]=Path(v['config'][key])
v['config']=WorkbenchConfig(**v['config']);v['cloud_profile']=CloudProfile('deepseek','deepseek-flash')
v['service']=SourceOperations(v['config'],SourceProfile(Path(v['phase4_config'])),v['cloud_profile'])
import pro_a.bounded_extraction as bounded
import pro_a.workbench.bounded_extraction_store as store
import pro_a.workbench.source_operations as operations
bounded.initial_extraction_plan=store.initial_extraction_plan=forbidden
store.BoundedExtractionStore.subdivide=store.BoundedExtractionStore.subdivide_after_truncation=forbidden
operations.plan_external_source_analysis=operations.resume_execution=forbidden
SourceOperations._register_input=SourceOperations._bind_job=forbidden
'''
    crash=bootstrap+'''
def fault(name):
 if name==sys.argv[2]:os._exit(73)
persistence.checkpoint=fault
with synthetic_providers(v,Transport()) as providers:
 v['service'].resume_bounded_extraction_only(v['run_id'],worker_id='hard-crash-worker',idempotency_key='hard-crash-action-0001',max_new_calls=1,provider=providers)
'''
    environment={**os.environ,'PYTHONPATH':os.pathsep.join((str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).parent))), 'PYTHONDONTWRITEBYTECODE':'1'}
    child=subprocess.run([sys.executable,'-c',crash,str(path),window],env=environment,capture_output=True,timeout=60)
    assert child.returncode==73,child.stderr.decode(errors='replace')
    # Simulate expiry of leases after process death; only disposable fixture rows.
    with value['service'].store.connect(operator_write=True) as c:
        c.execute("UPDATE source_processing_runs SET lease_expires_at='2000-01-01T00:00:00+00:00'")
        c.execute('UPDATE bounded_extraction_series SET lease_expires_at=0 WHERE lease_owner IS NOT NULL')
        c.execute('UPDATE bounded_extraction_segments SET lease_expires_at=0 WHERE lease_owner IS NOT NULL')
    recovery=bootstrap+'''
transport=Transport()
with synthetic_providers(v,transport) as providers:
 result=v['service'].resume_bounded_extraction_only(v['run_id'],worker_id='fresh-recovery-worker',idempotency_key='hard-crash-action-0001',max_new_calls=1,provider=providers)
 assert result['bounded_complete'] and not transport.calls
print('RECOVERED_NO_PROVIDER_RECALL')
'''
    recovered=subprocess.run([sys.executable,'-c',recovery,str(path)],env=environment,capture_output=True,timeout=60)
    assert recovered.returncode==0,recovered.stderr.decode(errors='replace')
    assert b'RECOVERED_NO_PROVIDER_RECALL' in recovered.stdout
    assert len(rows(value,'bounded_extraction_attempts'))==1 and len(rows(value,'bounded_extraction_series_results'))==1
    assert len(events(value,COMPLETE))==1


def test_accepted_retry_resume_qualification_does_not_relax_default_retry_scope(tmp_path,monkeypatch):
    from pro_a.workbench.bounded_resume import assess_bounded_resume_compatibility
    from pro_a.workbench.retry_compatibility import assess_bounded_retry_compatibility
    value=topology(tmp_path,monkeypatch,counts=(33,),accepted_retry=True)
    first=rows(value,'bounded_extraction_attempts')[1]
    before=value['config'].state_db.read_bytes()
    default=assess_bounded_retry_compatibility(value['config'],value['run_id'],first['attempt_id'],persist=False)
    assert default['status']=='BLOCKED'
    qualified=assess_bounded_resume_compatibility(value['config'],value['run_id'],persist=False)
    assert qualified['status']=='QUALIFIED',qualified
    assert qualified['evidence']['bounded_only_resume_boundary']==contract()
    assert value['config'].state_db.read_bytes()==before
    with pytest.raises(SourceOperationError,match='RETRY_LIMIT_EXCEEDED'):
        value['service'].retry_failed_extraction(value['run_id'],first['attempt_id'],retry_reason='MALFORMED_PROVIDER_JSON',idempotency_key='still-no-third-attempt')


def test_cross_release_accepted_retry_requires_new_qualification_then_resumes(tmp_path,monkeypatch):
    import pro_a.phase4_orchestration as native
    from pro_a.workbench import cloud_jobs
    from pro_a.workbench import retry_compatibility as compatibility
    from pro_a.workbench.bounded_resume import assess_bounded_resume_compatibility
    value=topology(tmp_path,monkeypatch,counts=(33,),accepted_retry=True)
    target={**value['service'].jobs.current_runtime(),'git_sha':'f'*40}
    target['runtime_sha256']=digest({k:v for k,v in target.items() if k!='runtime_sha256'})
    target_native={**native._runtime(),'repository_commit':'f'*40}
    monkeypatch.setattr(cloud_jobs,'runtime_identity',lambda *_a,**_k:target)
    monkeypatch.setattr(native,'_runtime',lambda:target_native)
    monkeypatch.setattr(compatibility,'native_runtime',lambda:target_native)
    qualified=assess_bounded_resume_compatibility(value['config'],value['run_id'],persist=True)
    assert qualified['status']=='QUALIFIED',qualified
    assert assess_bounded_resume_compatibility(value['config'],value['run_id'],persist=True)['duplicate']
    tripwires(monkeypatch)
    transport=Transport()
    with synthetic_providers(value,transport) as providers:
        assert resume(value,providers,ceiling=1)['bounded_complete']
    assert len(transport.calls)==1
