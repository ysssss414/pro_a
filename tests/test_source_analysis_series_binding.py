"""Bounded SourceOperations execution through synthetic HTTP only."""
import json
import socket

import pytest

from pro_a.bounded_source_analysis import BOUNDED_SOURCE_ANALYSIS_OPERATION
from pro_a.workbench.source_operations import SourceOperationError
from pro_a.workbench.store import Store
from test_phase43_stage6_lifecycle import _schema11
from test_workbench_stage7 import clean_pdf, upload
from series_binding_helpers import case, providers, real_providers, start, advance, finish, rows, Transport


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original = socket.socket.connect
    def local(sock, address):
        if isinstance(address, tuple) and address[0] in ('127.0.0.1','::1'):
            return original(sock, address)
        raise AssertionError('EXTERNAL_NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket, 'connect', local)
    monkeypatch.setattr('requests.post', lambda *a, **k: pytest.fail('EXTERNAL_PROVIDER_FORBIDDEN'))


def test_schema11_new_run_fails_without_mutation(tmp_path):
    value, _ = _schema11(tmp_path)
    source = upload(value, clean_pdf(tmp_path))
    before = value['config'].state_db.read_bytes()
    with pytest.raises(SourceOperationError, match='BOUNDED_SCHEMA_REQUIRED'):
        value['service'].start(source['source_id'], idempotency_key='schema11-must-fail-0001')
    assert value['config'].state_db.read_bytes() == before
    assert not rows(value, 'source_processing_runs')


@pytest.mark.parametrize('mutation',['missing','tampered'])
def test_registered_input_integrity_precedes_real_adapter_dispatch(tmp_path,monkeypatch,mutation):
    value=case(tmp_path)
    provider,transport=providers(value,monkeypatch)
    _,run_id=start(value,tmp_path,count=1)
    advance(value,run_id,provider)
    artifact=rows(value,'source_cloud_inputs')[0]
    path=value['config'].artifact_root/artifact['artifact_relative']
    if mutation=='missing':
        path.unlink()
    else:
        path.write_bytes(path.read_bytes()+b' ')
    before=path.read_bytes() if path.exists() else None
    final=advance(value,run_id,provider,restart=True)
    assert final['state']=='BLOCKED' and final['error']['code']=='BOUNDED_INPUT_ARTIFACT_MISMATCH'
    assert not transport.calls and not rows(value,'bounded_extraction_attempts')
    assert (path.read_bytes() if path.exists() else None)==before


def test_one_series_multiple_calls_restart_canonical_semantic_packet(tmp_path, monkeypatch):
    value = case(tmp_path)
    production = value['config'].knowledge_db.read_bytes()
    provider, transport = providers(value, monkeypatch)
    _, run_id = start(value, tmp_path)
    initialized = advance(value, run_id, provider)
    assert initialized['logical_extraction_series_count'] == 1 and not transport.calls
    assert not rows(value, 'cloud_jobs') and not rows(value, 'source_processing_jobs')
    final = finish(value, run_id, provider, restart=True)
    assert final['state'] == 'HUMAN_REVIEW_REQUIRED', final.get('error')
    assert len(transport.calls) == 3
    assert final['completed_series_count'] == 1 and final['coverage_status'] == 'COMPLETE'
    assert final['packet_artifact_id'] and final['packet_id']
    assert all(r['operation_kind']=='SEMANTIC_DECOMPOSITION' for r in rows(value,'cloud_jobs'))
    assert len(rows(value,'bounded_extraction_attempts')) == 3
    assert len(rows(value,'bounded_extraction_segment_results')) == 3
    assert len(rows(value,'bounded_extraction_series_results')) == 1
    assert final['bounded_usage']['total_tokens']==450 and final['usage_scope']=='SEMANTIC_CLOUD_JOBS'
    # Compare the active aggregate with the same canonical response produced as
    # one local whole-piece value. No single-call token-fit claim is involved.
    from pro_a.bounded_source_analysis import annotated_source
    from pro_a.bounded_extraction import expand_source_analysis_wire_v3
    from series_binding_helpers import response_content
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    from stability_helpers import make_config
    payload,ctx,catalog,series=value['service'].bounded.inputs(final)[0]
    expected_wire=json.loads(response_content({'assigned_evidence_refs':series.eligible_evidence_refs},annotated_source(ctx,catalog)))['wire']
    expected=expand_source_analysis_wire_v3(expected_wire,catalog,ctx)
    actual=value['service'].bounded.replay(final,provider[BOUNDED_SOURCE_ANALYSIS_OPERATION].cfg)
    from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
    actual=actual.json(SOURCE_ANALYSIS_SYSTEM,payload['native']['user_prompt'])
    assert actual==expected
    (tmp_path/'claim-identity').mkdir()
    cfg,db=make_config(tmp_path/'claim-identity')
    analyzer=Analyzer(cfg,db)
    before=analyzer._validate_source_output(expected,ctx.piece.source_text)
    after=analyzer._validate_source_output(actual,ctx.piece.source_text)
    assert before==after
    for index,(left,right) in enumerate(zip(before['claims'],after['claims'])):
        seed=lambda claim:{'source_sha256':ctx.source_sha256,'claim_index':index,'claim':claim}
        assert deterministic_id('CLM',seed(left))==deterministic_id('CLM',seed(right))
    assert value['config'].knowledge_db.read_bytes() == production


@pytest.mark.parametrize('mode,state', [('truncated','BLOCKED'),('malformed','BLOCKED'),('unknown','RECOVERY_REQUIRED')])
def test_single_ref_failure_is_bounded_and_durable(tmp_path, monkeypatch, mode, state):
    value = case(tmp_path)
    provider, transport = providers(value, monkeypatch, Transport(mode=mode))
    _, run_id = start(value, tmp_path, count=1)
    final = finish(value, run_id, provider)
    assert final['state'] == state, final.get('error')
    assert len(transport.calls) == 1 and not rows(value,'bounded_extraction_segment_results')
    assert not rows(value,'cloud_jobs')
    series = rows(value,'bounded_extraction_series')[0]
    assert series['state'] == ('RECOVERY_REQUIRED' if mode=='unknown' else 'FAILED')
    if mode=='unknown':
        assert final['error']['manual_recovery_required'] and final['bounded_usage']['output_token_liability']==12000
    if mode=='truncated':
        assert final['error']['code'] == 'EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'
    assert advance(value, run_id, provider, restart=True) is None
    assert len(transport.calls) == 1


@pytest.mark.parametrize('mode', ['truncated','subdivide'])
def test_only_target_parent_subdivides_without_retry(tmp_path, monkeypatch, mode):
    value = case(tmp_path)
    provider, transport = providers(value, monkeypatch, Transport(mode=lambda target,n: mode if n==1 else None))
    _, run_id = start(value, tmp_path)
    advance(value, run_id, provider)
    original = rows(value,'bounded_extraction_segments')
    after = advance(value, run_id, provider)
    assert after['state'] == 'EXTRACTION_PROCESSING' and len(transport.calls)==1
    segments = rows(value,'bounded_extraction_segments')
    parent = next(r for r in segments if r['state']=='SUPERSEDED_BY_CHILDREN')
    children = [r for r in segments if r['parent_segment_id']==parent['segment_id']]
    assert len(children)==2 and all(r['max_output_tokens']==12000 for r in children)
    assert [r for r in segments if r['segment_id'] in {o['segment_id'] for o in original} and r['segment_id']!=parent['segment_id']] == [o for o in original if o['segment_id']!=parent['segment_id']]
    accepted = rows(value,'bounded_extraction_segment_results')
    assert len(accepted)==int(mode=='subdivide')
    if accepted:
        assert accepted[0]['result_type']=='SUBDIVISION_REQUIRED'
    final = finish(value,run_id,provider,restart=True)
    assert final['state']=='HUMAN_REVIEW_REQUIRED', final.get('error')
    assert len(transport.calls)==5
    assert all(r['attempt_number']==1 for r in rows(value,'bounded_extraction_attempts'))
    assert not any(r['operation_kind']=='SOURCE_ANALYSIS_PIECE' for r in rows(value,'source_processing_jobs'))


def test_repeated_truncation_terminates_with_durable_density_failure(tmp_path, monkeypatch):
    value = case(tmp_path)
    provider, transport = providers(value, monkeypatch, Transport(mode='truncated'))
    _, run_id = start(value, tmp_path)
    final = finish(value, run_id, provider, restart=True)
    assert final['state']=='BLOCKED'
    assert final['error']['code']=='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'
    assert len(transport.calls)==5
    assert rows(value,'bounded_extraction_series')[0]['state']=='FAILED'
    assert not rows(value,'bounded_extraction_segment_results') and not rows(value,'cloud_jobs')
    assert all(s['state'] in ('FAILED','SUPERSEDED_BY_CHILDREN') for s in rows(value,'bounded_extraction_segments'))
    event = rows(value,'bounded_extraction_events')[-1]
    assert event['event_type']=='SERIES_FAILED'
    assert json.loads(event['body_json'])['code']=='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'
    assert all(c['max_tokens']==12000 for c in transport.calls)


def test_multi_piece_density_failure_closes_pending_series(tmp_path,monkeypatch):
    value=case(tmp_path)
    provider,transport=providers(value,monkeypatch,Transport(mode='truncated'))
    _,run_id=start(value,tmp_path,count=155)
    final=finish(value,run_id,provider,restart=True)
    series=rows(value,'bounded_extraction_series')
    assert final['state']=='BLOCKED' and final['error']['code']=='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'
    assert len(series)>1 and all(s['state']=='FAILED' for s in series)
    assert all(s['state'] in ('FAILED','SUPERSEDED_BY_CHILDREN') for s in rows(value,'bounded_extraction_segments'))
    assert len(transport.calls)==5 and not rows(value,'cloud_jobs')


@pytest.mark.parametrize('state',['FAILED','RECOVERY_REQUIRED'])
def test_restart_after_ledger_terminal_event_before_run_transition(tmp_path,monkeypatch,state):
    value=case(tmp_path)
    provider,transport=providers(value,monkeypatch)
    _,run_id=start(value,tmp_path,count=155)
    run=advance(value,run_id,provider)
    ledger=value['service'].bounded.ledger
    series=value['service'].bounded.inputs(run)[0][3]
    fence=ledger.claim_series(series.series_id,'crash-owner',lease_seconds=600)
    if state=='FAILED':
        ledger.fail_series(series.series_id,'crash-owner',fence,'BOUNDED_EXTRACTION_FAILED')
        ledger.release(series.series_id,'crash-owner',series_fence=fence)
    else:
        payload,ctx,catalog,_=value['service'].bounded.inputs(run)[0]
        leaf=ledger.read(series.series_id)[1].leaves[0]
        from test_bounded_extraction_persistence import reserve
        sf,aid=reserve(ledger,leaf,owner='crash-owner')
        ledger.record_dispatch(aid,'crash-owner',sf)
        assert ledger.reconcile_attempt(aid,'crash-owner',sf,catalog,ctx)=='UNKNOWN_EXTERNAL_OUTCOME'
        ledger.release(series.series_id,'crash-owner',series_fence=fence,segment_id=leaf.segment_id,segment_fence=sf)
    final=advance(value,run_id,provider,restart=True)
    assert not transport.calls and not rows(value,'cloud_jobs')
    if state=='FAILED':
        assert final['state']=='BLOCKED' and all(s['state']=='FAILED' for s in rows(value,'bounded_extraction_series'))
    else:
        assert final['state']=='RECOVERY_REQUIRED' and final['error']['manual_recovery_required']
        assert final['bounded_usage']['output_token_liability']==12000


def test_prompt_is_durable_before_transport_and_raw_reasoning_is_dropped(tmp_path, monkeypatch):
    from pro_a.bounded_source_analysis import annotated_source
    from pro_a.evidence_binding import identity
    from series_binding_helpers import Response, request_parts, response_content
    value = case(tmp_path)
    seen=[]
    checks=[]
    class ForbiddenReasoning:
        def __str__(self):
            raise AssertionError('REASONING_INSPECTED')
        def __len__(self):
            raise AssertionError('REASONING_MEASURED')
    def callback(request):
        target,_=request_parts(request)
        attempt=next(r for r in rows(value,'bounded_extraction_attempts') if r['segment_id']==target['segment_id'])
        checks.append(len(rows(value,'bounded_extraction_dispatches'))==len(seen)+1)
        series=rows(value,'bounded_extraction_series')[0]
        path=value['service'].bounded.ledger._path(series['series_id'],attempt['segment_id']+'.prompt.json')
        payload=json.loads(path.read_bytes())
        checks.append(identity(payload)==json.loads(attempt['request_json'])['payload_sha256'])
        checks.append(payload['request']==request)
        seen.append(request)
    class SentinelTransport(Transport):
        def __call__(self, *args, **kwargs):
            super().__call__(*args, **kwargs)
            target, source=request_parts(kwargs['json'])
            return Response(response_content(target,source),reasoning=ForbiddenReasoning())
    provider, transport=providers(value,monkeypatch,SentinelTransport(callback=callback))
    _,run_id=start(value,tmp_path)
    advance(value,run_id,provider)
    binding=value['service'].bounded.inputs(value['service'].get_run(run_id))[0]
    payload,ctx,catalog,series=binding
    source=annotated_source(ctx,catalog)
    import re
    assert re.sub(r'\[/?EV_[A-Za-z0-9]+\]','',source)==ctx.piece.source_text
    assert len(source)>len(ctx.piece.source_text)
    native=payload['native']['user_prompt']
    final=finish(value,run_id,provider)
    assert seen and all(checks),checks
    assert final['state']=='HUMAN_REVIEW_REQUIRED'
    for request in seen:
        assert request['model']=='deepseek-flash' and request['max_tokens']==12000
        assert request['thinking']=={'type':'disabled'} and 'reasoning_effort' not in request
        assert request['response_format']=={'type':'json_object'}
        assert request['messages'][1]['content']!=native
    import base64
    for attempt in rows(value,'bounded_extraction_attempts'):
        envelope=json.loads(value['service'].bounded.ledger._path(series.series_id,attempt['attempt_id']+'.raw.json').read_bytes())
        assert 'reasoning_content' not in envelope and envelope['reasoning_tokens']==0
        assert envelope['provider_reported_model']=='deepseek-flash'
        assert isinstance(envelope['latency_ms'],(int,float))
        raw=base64.b64decode(envelope['raw_body_base64'])
        assert json.loads(raw)['wire']['wire_version']=='source-analysis-wire-v3'
    replay=value['service'].bounded.replay(final,provider[BOUNDED_SOURCE_ANALYSIS_OPERATION].cfg)
    from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
    assert len(replay.json(SOURCE_ANALYSIS_SYSTEM,native)['claims'])==33
    with pytest.raises(ValueError,match='BOUNDED_NATIVE_PROMPT_MISMATCH'):
        replay.json(SOURCE_ANALYSIS_SYSTEM,seen[0]['messages'][1]['content'])


def test_multi_piece_full_packet_and_mcp_reads(tmp_path, monkeypatch):
    from pro_a.mcp.service import ReadService
    from test_mcp_stage0 import hashes
    from pro_a.workbench.review_workbench import ReviewWorkbench
    value=case(tmp_path)
    production=value['config'].knowledge_db.read_bytes()
    provider,transport=real_providers(value,monkeypatch,Transport(mode=lambda t,n:'truncated' if n==1 else 'sparse'))
    _,run_id=start(value,tmp_path,count=155)
    final=finish(value,run_id,provider,restart=True)
    assert final['state']=='HUMAN_REVIEW_REQUIRED',final.get('error')
    assert final['logical_extraction_series_count']>1 and final['completed_series_count']==final['logical_extraction_series_count']
    assert len(transport.calls)>final['logical_extraction_series_count']
    assert value['semantic_http_calls']
    assert all(j['provider_adapter_version']=='semantic-backend-adapter-v2' for j in rows(value,'cloud_jobs'))
    assert final['logical_job_count']==final['logical_extraction_series_count']+len(final['jobs'])<=31
    packet=ReviewWorkbench(value['config']).read(final['packet_artifact_id'])
    assert packet['review']['progress']['completed']==0
    before=hashes(value['config'])
    bridge=ReadService(value['config'])
    health=bridge.pro_a_health()
    queue=bridge.list_review_queue()
    context=bridge.get_review_context(final['packet_artifact_id'])
    item=bridge.get_review_item_context(final['packet_artifact_id'],context.items[0].candidate_id)
    assert queue.items and context.items and health.read_only and item.read_only
    for result in (health,queue,context,item):
        assert 'bounded-extraction' not in result.model_dump_json()
    assert hashes(value['config'])==before and value['config'].knowledge_db.read_bytes()==production


def test_dense_five_series_twenty_five_semantic_jobs(tmp_path, monkeypatch):
    value=case(tmp_path)
    provider,transport=providers(value,monkeypatch,Transport(mode='sparse'))
    source_text='\n'.join(f'Synthetic Company product {i:03d} has capacity {i+1:03d} units in early September 2026 at this site.' for i in range(200))
    source=upload(value,clean_pdf(tmp_path,text=source_text))
    run_id=value['service'].start(source['source_id'],idempotency_key='dense-logical-budget-0001')['run']['processing_run_id']
    advance(value,run_id,provider)
    # Budget fixture exercises bounded calls independently of the native evidence
    # context search. Full native replay is qualified by the separate PDF E2E.
    from pro_a.workbench.source_operations import SourceOperations
    for _ in range(40):
        value['service']=SourceOperations(value['config'],value['source_profile'],value['cloud_profile'])
        if value['service'].bounded.advance(value['service'].get_run(run_id),provider,'dense-worker'):
            break
    from test_phase43_stage1_operator_scale import semantic_inputs
    from pro_a.semantic_decomposition import partition_semantic_claims
    batches=partition_semantic_claims(semantic_inputs(200),max_input_tokens=11808)
    assert len(batches)==25
    for ordinal,batch in enumerate(batches,1):
        artifact=value['service']._register_input(value['service'].get_run(run_id),'SEMANTIC_DECOMPOSITION',ordinal,
                                                 {'claims':batch},{'native_state':'SYNTHETIC_BUDGET_FIXTURE'})
        value['service']._bind_job(run_id,'SEMANTIC_DECOMPOSITION',ordinal,artifact)
    final=value['service'].get_run(run_id)
    assert final['completed_series_count']==final['logical_extraction_series_count']==5
    assert len(final['jobs'])==25 and final['logical_job_count']==30
    assert len(transport.calls)>5
    assert all(s['provider_call_reservations']<=32 and s['output_liability']<=384000 for s in rows(value,'bounded_extraction_series'))


def test_segment_contract_mismatch_and_old_retry_do_not_dispatch(tmp_path,monkeypatch):
    value=case(tmp_path)
    provider,transport=providers(value,monkeypatch)
    _,run_id=start(value,tmp_path)
    advance(value,run_id,provider)
    monkeypatch.setattr(provider[BOUNDED_SOURCE_ANALYSIS_OPERATION],'adapter_version','other-version')
    final=advance(value,run_id,provider)
    assert final['state']=='BLOCKED' and not transport.calls
    assert not rows(value,'bounded_extraction_attempts') and not rows(value,'cloud_jobs')
    with pytest.raises(SourceOperationError,match='BOUNDED_EXTRACTION_RETRY_OWNED_BY_SERIES'):
        value['service'].retry_failed_extraction(run_id,'SYNTHETIC_ATTEMPT',retry_reason='Synthetic explicit request',idempotency_key='bounded-retry-must-fail-0001')
