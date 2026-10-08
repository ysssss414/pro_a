"""New lexical batches over the unchanged schema12 durable ledger."""
import base64
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from pro_a.workbench import bounded_extraction_persistence as persistence
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.store import Store
from pro_a.workbench.config import BoundaryError
from test_bounded_extraction_persistence import reserve, no_network
from test_output_decomposition import fixture, record, accepted, payload
from series_binding_helpers import case, start, synthetic_providers, Transport


def setup(tmp_path, count=16):
    value=case(tmp_path)
    ctx,catalog,series,plan=fixture(count)
    ledger=BoundedExtractionStore(value['config']);ledger.create(series)
    return value['config'],ledger,ctx,catalog,series,plan


def complete(ledger,ctx,catalog,series,batch):
    fence,aid=reserve(ledger,batch)
    assert ledger.record_dispatch(aid,'worker',fence)
    raw=json.dumps(record(ctx,catalog,series,batch)).encode()
    ledger.record_outcome(aid,'worker',fence,raw,finish_reason='tool_calls',input_tokens=100,output_tokens=50,total_tokens=150,cached_input_tokens=20)
    result=ledger.accept_result(aid,'worker',fence,catalog,ctx)
    assert result['result_sha256']==accepted(ctx,catalog,series,batch).result_sha256
    return aid


@pytest.mark.parametrize('window',['attempt_reserved','dispatch_durable','raw_artifact_durable','outcome_durable','result_accepted'])
def test_crash_recovery_without_recall(tmp_path,monkeypatch,window):
    config,ledger,ctx,catalog,series,plan=setup(tmp_path)
    batch=plan.leaves[0]
    def crash(name):
        if name==window: raise RuntimeError('SYNTHETIC_CRASH')
    monkeypatch.setattr(persistence,'checkpoint',crash)
    with pytest.raises(RuntimeError,match='SYNTHETIC_CRASH'):
        complete(ledger,ctx,catalog,series,batch)
    monkeypatch.setattr(persistence,'checkpoint',lambda _:None)
    fresh=BoundedExtractionStore(config)
    with Store(config).connect() as c:
        aid=c.execute('SELECT attempt_id FROM bounded_extraction_attempts').fetchone()[0]
    status=fresh.reconcile_attempt(aid,'worker',1,catalog,ctx)
    expected={'attempt_reserved':'RESERVED_NOT_DISPATCHED','dispatch_durable':'UNKNOWN_EXTERNAL_OUTCOME'}.get(window,'SUCCEEDED_COMPLETE')
    assert status==expected
    with Store(config).connect() as c:
        assert c.execute('SELECT count(*) FROM bounded_extraction_attempts').fetchone()[0]==1
        assert c.execute('SELECT count(*) FROM bounded_extraction_segment_results').fetchone()[0]==int(status=='SUCCEEDED_COMPLETE')


@pytest.mark.parametrize('window',[None,'subdivision_child_inserted','subdivision_parent_superseded','subdivision_committed'])
def test_truncated_parent_atomic_children_full_context(tmp_path,monkeypatch,window):
    config,ledger,ctx,catalog,series,plan=setup(tmp_path)
    parent=plan.leaves[0]
    fence,aid=reserve(ledger,parent);ledger.record_dispatch(aid,'worker',fence)
    raw=b'{"claims": [PRIVATE_SYNTHETIC_PARTIAL'
    outcome=ledger.record_outcome(aid,'worker',fence,raw,finish_reason='length',output_tokens=12000)
    path=config.artifact_root/outcome['artifact_relative']; immutable=path.read_bytes()
    assert base64.b64decode(json.loads(immutable)['raw_body_base64'])==raw
    # No parser may be called for a truncated result.
    with monkeypatch.context() as patch:
        patch.setattr('pro_a.output_decomposition.record_to_result',lambda *a:pytest.fail('PARTIAL_PARSE'))
        with pytest.raises(BoundaryError,match='RAW_OUTCOME_NOT_ACCEPTABLE'):
            ledger.accept_result(aid,'worker',fence,catalog,ctx)
    def crash(name):
        if name==window: raise RuntimeError('SYNTHETIC_CRASH')
    monkeypatch.setattr(persistence,'checkpoint',crash)
    if window:
        with pytest.raises(RuntimeError,match='SYNTHETIC_CRASH'):
            ledger.subdivide_after_truncation(parent.segment_id,'worker',fence,expected_frontier_version=0)
    monkeypatch.setattr(persistence,'checkpoint',lambda _:None)
    ledger=BoundedExtractionStore(config)
    children=ledger.subdivide_after_truncation(parent.segment_id,'worker',fence,expected_frontier_version=ledger.read(series.series_id)[2]['frontier_version'])
    assert [len(b.assigned_evidence_refs) for b in children]==[8,8]
    for child in children:
        body=payload(ctx,catalog,series,child)['request']['messages'][1]['content']
        assert all(u.exact_text in body for u in catalog.units)
        assert all(u.evidence_ref not in body for u in catalog.units if u.evidence_ref not in child.assigned_evidence_refs)
        complete(ledger,ctx,catalog,series,child)
        ledger=BoundedExtractionStore(config) # crash boundary between child results
    sf=ledger.claim_series(series.series_id,'coordinator')
    ledger.finalize(series.series_id,'coordinator',sf,expected_frontier_version=1,catalog=catalog,context=ctx)
    usage=ledger.read(series.series_id)[3]
    assert usage.provider_call_count==3 and usage.output_token_liability==12100
    assert path.read_bytes()==immutable
    assert len(ledger.aggregate(series.series_id)['wire']['claims'])==16
    with pytest.raises(BoundaryError): reserve(ledger,parent,number=2,fence=fence)


def test_two_workers_cannot_dispatch_twice(tmp_path):
    config,ledger,ctx,catalog,series,plan=setup(tmp_path)
    batch=plan.leaves[0]
    def worker(owner):
        instance=BoundedExtractionStore(config)
        try:
            fence,aid=reserve(instance,batch,owner=owner)
            return instance.record_dispatch(aid,owner,fence)
        except BoundaryError as e: return str(e)
    with ThreadPoolExecutor(2) as pool:
        outcomes=list(pool.map(worker,['one','two']))
    assert outcomes.count(True)==1 and outcomes.count('LEASE_BUSY')==1
    assert ledger.read(series.series_id)[3].provider_call_count==1


@pytest.mark.parametrize('mode',['success','truncated','unknown','malformed'])
def test_series_orchestration_synthetic_only(tmp_path,mode):
    value=case(tmp_path)
    _,rid=start(value,tmp_path,count=18)
    service=value['service']
    run=service.advance_once(worker_id='output-test',processing_run_id=rid)
    assert run['state']=='EXTRACTION_PROCESSING',run.get('error')
    transport=Transport(mode=(lambda t,n:'truncated' if n==1 else None) if mode=='truncated' else None if mode=='success' else mode)
    with synthetic_providers(value,transport) as providers:
        for _ in range(20):
            run=service.advance_once(worker_id='output-test',processing_run_id=rid,provider=providers)
            if run['state'] in ('HUMAN_REVIEW_REQUIRED','BLOCKED','FAILED','RECOVERY_REQUIRED'): break
    assert run['extraction_execution_mode']=='WHOLE_PIECE_OUTPUT_DECOMPOSITION'
    assert run['logical_extraction_series_count']==1
    assert run['logical_job_count']==1+len(run['jobs'])
    assert run['provider_call_count']==len(transport.calls)
    if mode in ('success','truncated'):
        assert run['state']=='HUMAN_REVIEW_REQUIRED',run.get('error')
        assert run['coverage_status']=='COMPLETE'
        assert run['subdivision_count']==int(mode=='truncated')
    else:
        assert run['state']=='RECOVERY_REQUIRED' if mode=='unknown' else run['state']=='BLOCKED'
        assert len(transport.calls)==1 and run['subdivision_count']==0


def test_fresh_process_raw_recovery_and_aggregate_crash(tmp_path,monkeypatch):
    import os,sys,subprocess
    from dataclasses import asdict
    from pathlib import Path
    config,ledger,ctx,catalog,series,plan=setup(tmp_path,4)
    batch=plan.leaves[0]
    fence,aid=reserve(ledger,batch);ledger.record_dispatch(aid,'worker',fence)
    value={'config':asdict(config),'attempt_id':aid,'fence':fence,'raw':json.dumps(record(ctx,catalog,series,batch)),
           'context':asdict(ctx),'catalog':asdict(catalog)}
    path=tmp_path/'crash.json';path.write_text(json.dumps(value,default=str),encoding='utf-8')
    bootstrap='''
import json,sys,socket,os
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench import bounded_extraction_persistence as persistence
from pro_a.analyzer import SourcePiece
from pro_a.source_analysis_wire import SourcePieceContext,build_source_evidence_catalog
def forbidden(*a,**k):raise AssertionError('NETWORK_FORBIDDEN')
socket.socket.connect=forbidden
v=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for key in ('knowledge_db','state_db','artifact_root'):v['config'][key]=Path(v['config'][key])
ledger=BoundedExtractionStore(WorkbenchConfig(**v['config']))
'''
    crash=bootstrap+'''
def fault(name):
 if name=='raw_artifact_durable':os._exit(73)
persistence.checkpoint=fault
ledger.record_outcome(v['attempt_id'],'worker',v['fence'],v['raw'].encode(),finish_reason='tool_calls',output_tokens=33)
'''
    child=subprocess.run([sys.executable,'-B','-c',crash,str(path)],capture_output=True,timeout=60)
    assert child.returncode==73,child.stderr.decode(errors='replace')
    recovery=bootstrap+'''
c=v['context'];ctx=SourcePieceContext(c['source_sha256'],SourcePiece(**c['piece']),tuple(c['known_node_ids']))
assert ledger.reconcile_attempt(v['attempt_id'],'worker',v['fence'],build_source_evidence_catalog(ctx),ctx)=='SUCCEEDED_COMPLETE'
print('RECOVERED_WITHOUT_PROVIDER')
'''
    child=subprocess.run([sys.executable,'-B','-c',recovery,str(path)],capture_output=True,timeout=60)
    assert child.returncode==0 and child.stdout.strip()==b'RECOVERED_WITHOUT_PROVIDER',child.stderr.decode(errors='replace')
    sf=ledger.claim_series(series.series_id,'coordinator')
    def fault(name):
        if name=='aggregate_artifact_durable':raise RuntimeError('SYNTHETIC_CRASH')
    monkeypatch.setattr(persistence,'checkpoint',fault)
    with pytest.raises(RuntimeError,match='SYNTHETIC_CRASH'):
        ledger.finalize(series.series_id,'coordinator',sf,expected_frontier_version=0,catalog=catalog,context=ctx)
    immutable=ledger._path(series.series_id,'aggregate.json').read_bytes()
    monkeypatch.setattr(persistence,'checkpoint',lambda _:None)
    fresh=BoundedExtractionStore(config)
    fresh.finalize(series.series_id,'coordinator',sf,expected_frontier_version=0,catalog=catalog,context=ctx)
    assert ledger._path(series.series_id,'aggregate.json').read_bytes()==immutable
    assert fresh.read(series.series_id)[3].provider_call_count==1


def test_mcp_output_counts_readonly_and_private(tmp_path,monkeypatch):
    from pro_a.mcp.service import ReadService
    from test_mcp_bounded_reads import snapshot
    value=case(tmp_path);_,rid=start(value,tmp_path,count=18)
    service=value['service'];service.advance_once(worker_id='mcp-output-test',processing_run_id=rid)
    with synthetic_providers(value,Transport(mode='truncated')) as providers:
        run=service.advance_once(worker_id='mcp-output-test',processing_run_id=rid,provider=providers)
    before=snapshot(value['config'])
    original=Store.connect
    def readonly(self,*,operator_write=False):
        assert not operator_write
        return original(self)
    monkeypatch.setattr(Store,'connect',readonly)
    reader=ReadService(value['config'])
    projected=reader.get_processing_run(rid)
    assert projected.output_decomposition.provider_call_count==1
    assert projected.output_decomposition.truncated_parent_calls==1
    assert projected.output_decomposition.output_liability_tokens==24000
    public=projected.model_dump_json()
    assert 'EV_' not in public and 'Synthetic Company product' not in public and 'raw_body' not in public
    assert reader.operations.get_run(rid)==run
    assert snapshot(value['config'])==before


@pytest.mark.parametrize('status,expected',[(None,'UNKNOWN'),(503,'FAILED')])
def test_length_cannot_subdivide_unknown_or_http_failure(tmp_path,status,expected):
    _,ledger,ctx,catalog,series,plan=setup(tmp_path,4)
    batch=plan.leaves[0]
    fence,aid=reserve(ledger,batch);ledger.record_dispatch(aid,'worker',fence)
    outcome=ledger.record_outcome(aid,'worker',fence,b'partial',http_status=status,finish_reason='length')
    assert outcome['external_outcome']==expected
    with pytest.raises(BoundaryError,match='DURABLE_TRUNCATION_REQUIRED'):
        ledger.subdivide_after_truncation(batch.segment_id,'worker',fence,expected_frontier_version=0)
    assert len(ledger.read(series.series_id)[1].leaves)==1


def test_projection_distinguishes_reservation_dispatch_and_known_outcome(tmp_path):
    from types import SimpleNamespace
    from pro_a.workbench.output_decomposition import OutputDecompositionRunner
    config,ledger,ctx,catalog,series,plan=setup(tmp_path,4)
    runner=SimpleNamespace(ledger=ledger)
    def projection():
        with Store(config).connect() as c:
            return OutputDecompositionRunner.projection(runner,c,series.processing_run_id)
    fence,aid=reserve(ledger,plan.leaves[0])
    reserved=projection()
    assert reserved['reserved_attempt_count']==1 and reserved['provider_call_count']==0
    ledger.record_dispatch(aid,'worker',fence)
    dispatched=projection()
    assert dispatched['provider_call_count']==dispatched['unknown_outcome_call_count']==1
    assert dispatched['confirmed_provider_call_count']==0
    ledger.record_outcome(aid,'worker',fence,b'partial',finish_reason='length',output_tokens=12000)
    known=projection()
    assert known['confirmed_provider_call_count']==1 and known['unknown_outcome_call_count']==0


def test_multilevel_subdivision_durable_canonical_equivalence(tmp_path):
    from pro_a.bounded_extraction import aggregate_segment_wires
    config,ledger,ctx,catalog,series,plan=setup(tmp_path)
    original=aggregate_segment_wires(series,plan,(accepted(ctx,catalog,series,plan.leaves[0]),),catalog,ctx)
    parents=[plan.leaves[0]]
    for depth in range(2):
        children=[]
        for parent in parents:
            fence,aid=reserve(ledger,parent);ledger.record_dispatch(aid,'worker',fence)
            ledger.record_outcome(aid,'worker',fence,b'not parseable',finish_reason='length',output_tokens=12000)
            children.extend(ledger.subdivide_after_truncation(parent.segment_id,'worker',fence,
                expected_frontier_version=ledger.read(series.series_id)[2]['frontier_version']))
        assert all(len(child.assigned_evidence_refs)==8//(2**depth) for child in children)
        for child in children:
            request=json.dumps(payload(ctx,catalog,series,child),ensure_ascii=False)
            assert all(u.exact_text in request for u in catalog.units)
            assert all(u.evidence_ref not in request for u in catalog.units if u.evidence_ref not in child.assigned_evidence_refs)
        parents=children
    for child in parents:
        complete(ledger,ctx,catalog,series,child)
        ledger=BoundedExtractionStore(config)
    sf=ledger.claim_series(series.series_id,'coordinator')
    ledger.finalize(series.series_id,'coordinator',sf,expected_frontier_version=3,catalog=catalog,context=ctx)
    usage=ledger.read(series.series_id)[3]
    assert usage.provider_call_count==7 and usage.output_token_liability==36200
    assert ledger.aggregate(series.series_id)['wire']==json.loads(original.wire_json)
