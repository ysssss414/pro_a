"""R2 contract qualification: synthetic providers only, no historical admission."""
from copy import deepcopy
import json
import hashlib
import socket
from types import SimpleNamespace

import pytest

from pro_a import extraction_analysis_record as core, output_decomposition as adapter
from pro_a import output_decomposition_legacy as legacy
from pro_a.bounded_extraction import aggregate_segment_wires, expand_source_analysis_wire_v3
from pro_a.analyzer import Analyzer
from pro_a.operational_ingestion import deterministic_id
from lexical_record_helpers import claim_linkages
from stability_helpers import make_config
from test_output_decomposition import fixture, record, payload


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('REAL_PROVIDER_FORBIDDEN')
    monkeypatch.setattr(socket.socket,'connect',forbidden)


def v2(value,owned):
    result=deepcopy(value);result.pop('evidence_acknowledgements')
    result['dispositions']=claim_linkages(result,owned)
    return result


class FakeNativeJsonAdapter:
    """Alternate adapter emits native normalized data, no lexical workaround."""
    def normalize(self,wire,owned,anchors):
        value=deepcopy(wire);value.pop('wire_version')
        for family in ('node_candidates','source_references'):
            for obj,ref in zip(value[family],anchors[family]):obj['ownership_evidence_ref']=ref
        value['analysis_record_version']=core.VERSION
        value['evidence_acknowledgements']=[{'evidence_ref':ref} for ref in owned]
        return value


@pytest.mark.parametrize('counts',[(0,)*16,(1,)*16,(0,2,*([3]*14)),(18,1,0,0,1,1,1,0,1,1,1,1,0,1,1,16),(3,),(0,)])
def test_native_adapter_exact_internal_wire_identity_aggregate_analyzer(tmp_path,counts):
    ctx,cat,series,plan=fixture(len(counts));batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    templates=deepcopy(value['claims'])
    value['claims']=[deepcopy(template) for template,count in zip(templates,counts) for _ in range(count)]
    old=legacy.record_to_result(json.dumps(v2(value,batch.assigned_evidence_refs)),series,batch,cat,ctx)
    lexical=adapter.normalize_record(json.dumps(value))
    fake=FakeNativeJsonAdapter().normalize(json.loads(old.wire_json),batch.assigned_evidence_refs,
        {name:[obj['ownership_evidence_ref'] for obj in value[name]] for name in ('node_candidates','source_references')})
    assert fake==lexical
    left=core.record_to_result(lexical,series,batch,cat,ctx)
    right=core.record_to_result(fake,series,batch,cat,ctx)
    assert left==right==old
    assert all(d.disposition==('CLAIMED' if count else 'NO_INDEPENDENT_CLAIM') for d,count in zip(left.dispositions,counts))
    aggregates=[aggregate_segment_wires(series,plan,(result,),cat,ctx) for result in (old,left,right)]
    assert aggregates[0]==aggregates[1]==aggregates[2]
    cfg,db=make_config(tmp_path);analyzer=Analyzer(cfg,db)
    def native(result):
        canonical=expand_source_analysis_wire_v3(json.loads(result.wire_json),cat,ctx)
        analyzer.llm=SimpleNamespace(available=True,json=lambda *a:deepcopy(canonical))
        return analyzer.analyze_source('synthetic.txt',ctx.piece.source_text,'deep',adaptive_retry_policy='forbid')
    native_results=[native(result) for result in aggregates]
    assert native_results[0]==native_results[1]==native_results[2]
    identities=[[deterministic_id('CLM',{'source_sha256':ctx.source_sha256,'claim_index':i,'claim':claim})
        for i,claim in enumerate(result.claims)] for result in native_results]
    assert identities[0]==identities[1]==identities[2]
    assert 'evidence_acknowledgements' not in left.wire_json and 'analysis_record_version' not in left.wire_json


@pytest.mark.parametrize('mutation,error',[
    ('missing','MISSING_EVIDENCE_ACKNOWLEDGEMENT'),('duplicate','DUPLICATE_EVIDENCE_ACKNOWLEDGEMENT'),
    ('foreign','FOREIGN_EVIDENCE_ACKNOWLEDGEMENT'),('invented','FOREIGN_EVIDENCE_ACKNOWLEDGEMENT'),
    ('claim_refs','INVALID_PROVIDER_RECORD_SHAPE'),('disposition','INVALID_PROVIDER_RECORD_SHAPE')])
def test_acknowledgement_closed_exact_coverage(mutation,error):
    ctx,cat,series,plan=fixture(17);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    acknowledgements=value['evidence_acknowledgements']
    if mutation=='missing':acknowledgements.pop()
    elif mutation=='duplicate':acknowledgements.append(deepcopy(acknowledgements[0]))
    elif mutation in ('foreign','invented'):acknowledgements[0]['evidence_ref']=cat.units[-1].evidence_ref if mutation=='foreign' else 'EV_INVENTED'
    else:acknowledgements[0][mutation]=[] if mutation=='claim_refs' else 'CLAIMED'
    with pytest.raises(ValueError,match='^'+error+'$'):adapter.record_to_result(json.dumps(value),series,batch,cat,ctx)


@pytest.mark.parametrize('mutation',['foreign','missing','absent_selector','empty_selector'])
def test_claim_requires_valid_normalized_binding_before_derivation(mutation,monkeypatch):
    ctx,cat,series,plan=fixture(17);batch=plan.leaves[0];value=adapter.normalize_record(json.dumps(record(ctx,cat,series,batch)))
    claim=value['claims'][0]
    if mutation=='foreign':claim['evidence_ref']=cat.units[-1].evidence_ref
    elif mutation=='missing':claim.pop('evidence_ref')
    else:claim.update(evidence_mode='RAW_SUBSPAN',evidence_selector='' if mutation=='empty_selector' else 'ABSENT',evidence_occurrence=1)
    def forbidden(*a,**k):pytest.fail('DISPOSITION_BEFORE_VALID_BINDING')
    monkeypatch.setattr(core,'EvidenceDisposition',forbidden)
    with pytest.raises(ValueError):core.record_to_result(value,series,batch,cat,ctx)


def test_no_minimum_claim_count_and_no_low_value_omission_coverage_failure():
    ctx,cat,series,plan=fixture(16);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    value['claims']=[]
    result=adapter.record_to_result(json.dumps(value),series,batch,cat,ctx)
    assert json.loads(result.wire_json)['claims']==[]
    assert len(result.dispositions)==16 and all(d.disposition=='NO_INDEPENDENT_CLAIM' for d in result.dispositions)


@pytest.mark.parametrize('field',['provider','model','request_id','http_status','latency','usage','finish_reason','tool_calls','thinking','raw_artifact'])
def test_provider_telemetry_not_research_ir(field):
    ctx,cat,series,plan=fixture(1);batch=plan.leaves[0]
    value=adapter.normalize_record(json.dumps(record(ctx,cat,series,batch)));value[field]='synthetic'
    with pytest.raises(ValueError,match='INVALID_NORMALIZED_ANALYSIS_RECORD'):core.record_to_result(value,series,batch,cat,ctx)


def test_lexical_nested_json_decoded_and_native_confidence_before_neutral_boundary():
    ctx,cat,series,plan=fixture(1);value=record(ctx,cat,series,plan.leaves[0])
    value['claims'][0].update(structured_json='{"metrics":{"value":3,"verified":true}}',confidence='0.9')
    neutral=adapter.normalize_record(json.dumps(value))
    claim=neutral['claims'][0]
    assert claim['structured']=={'metrics':{'value':3,'verified':True}} and type(claim['confidence']) is float
    assert 'structured_json' not in claim and 'evidence' not in claim
    assert claim['evidence_ref'] and 'selection_mode' not in claim
    with pytest.raises(ValueError):
        value['claims'][0]['structured_json']='{"a":1,"a":2}'
        adapter.normalize_record(json.dumps(value))


def test_native_boolean_and_other_family_adapter_equivalence():
    from test_source_analysis_wire import empty_canonical,normal_node
    from test_bounded_extraction import v3 as wire_v3
    from lexical_record_helpers import from_wire
    ctx,cat,series,plan=fixture(1);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    raw=empty_canonical();raw['node_candidates']=[normal_node()]
    candidate=from_wire(wire_v3(raw,cat))['node_candidates'][0]
    candidate['ownership_evidence_ref']=batch.assigned_evidence_refs[0];value['node_candidates']=[candidate]
    neutral=adapter.normalize_record(json.dumps(value))
    assert type(neutral['node_candidates'][0]['independent_research_value']) is bool
    accepted=core.record_to_result(neutral,series,batch,cat,ctx)
    fake=FakeNativeJsonAdapter().normalize(json.loads(accepted.wire_json),batch.assigned_evidence_refs,
        {'node_candidates':[batch.assigned_evidence_refs[0]],'source_references':[]})
    assert fake==neutral and core.record_to_result(fake,series,batch,cat,ctx)==accepted


def test_historical_v1_v2_raw_stays_rejected_and_new_v3_distinct():
    ctx,cat,series,plan=fixture(1);batch=plan.leaves[0];current=record(ctx,cat,series,batch);current['claims']=[]
    old=v2(current,batch.assigned_evidence_refs);old['dispositions'][0]['claim_refs']=['C1']
    original=deepcopy(old)
    with pytest.raises(ValueError,match='UNKNOWN_LOCAL_CLAIM_LINK'):
        adapter.record_to_result(json.dumps(old),series,batch,cat,ctx,record_version=legacy.RECORD_VERSION)
    with pytest.raises(ValueError,match='INVALID_PROVIDER_RECORD_SHAPE'):
        adapter.record_to_result(json.dumps(old),series,batch,cat,ctx)
    old_v1=deepcopy(old);old_v1['dispositions']=[{'evidence_ref':batch.assigned_evidence_refs[0],'disposition':'CLAIMED'}]
    with pytest.raises(ValueError,match='CLAIM_DISPOSITION_MISMATCH'):
        adapter.record_to_result(json.dumps(old_v1),series,batch,cat,ctx,record_version=legacy.V1)
    assert adapter.record_to_result(json.dumps(current),series,batch,cat,ctx).dispositions[0].disposition=='NO_INDEPENDENT_CLAIM'
    assert old==original


def test_dense_wrong_mapping_historical_decision_not_reinterpreted():
    ctx,cat,series,plan=fixture(16);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    templates=deepcopy(value['claims']);counts=(18,1,0,0,1,1,1,0,1,1,1,1,0,1,1,16)
    value['claims']=[deepcopy(c) for c,count in zip(templates,counts) for _ in range(count)]
    old=v2(value,batch.assigned_evidence_refs)
    old['dispositions'][0]['claim_refs'].pop()
    for i in (1,4,5,6,8,9,10,11,13,14):old['dispositions'][i]['claim_refs']=['C'+str(int(old['dispositions'][i]['claim_refs'][0][1:])-1)]
    old['dispositions'][15]['claim_refs']=['C'+str(i) for i in range(28,43)]
    before=json.dumps(old,sort_keys=True)
    with pytest.raises(ValueError,match='CLAIM_LINKAGE_MISMATCH'):
        adapter.record_to_result(json.dumps(old),series,batch,cat,ctx,record_version=legacy.RECORD_VERSION)
    new=adapter.record_to_result(json.dumps(value),series,batch,cat,ctx)
    assert len(json.loads(new.wire_json)['claims'])==44 and json.dumps(old,sort_keys=True)==before


def test_frozen_selective_semantic_and_separate_encoding_identities():
    semantic=core.contract();execution=adapter.contract()
    assert semantic['extraction_objective']=='MATERIALITY_WEIGHTED_SELECTIVE_EXTRACTION'
    assert semantic['execution_coverage_required'] and not semantic['claim_per_evidence_required']
    assert semantic['every_emitted_claim_requires_valid_evidence'] and not semantic['raw_fact_recall_100_percent_required']
    assert not any(word in json.dumps(semantic).lower() for word in ('deepseek','tool_calls','structured_json','thinking'))
    assert 'Claims=[] 完全合法' in core.SEMANTIC_SYSTEM
    assert execution['research_semantic_contract']==semantic
    assert execution['provider_encoding_contract_version']==adapter.ENCODING_VERSION
    assert execution['provider_encoding_prompt_sha256']!=semantic['semantic_prompt_sha256']
    schema=adapter.record_schema()
    assert 'dispositions' not in schema['properties']
    assert set(schema['properties']['evidence_acknowledgements']['items']['properties'])=={'evidence_ref'}
    assert 'claim_refs' not in json.dumps(schema) .replace('supporting_claim_refs','')
    ctx,cat,series,plan=fixture(1);request=payload(ctx,cat,series,plan.leaves[0])['request']
    assert (request['model'],request['temperature'],request['max_tokens'],request['thinking'])==('deepseek-flash',0.1,12000,{'type':'disabled'})


def test_multi_segment_and_relation_supporting_claim_refs_unchanged():
    ctx,cat,series,plan=fixture(17);old=[];new=[];fake=[]
    for batch in plan.leaves:
        value=record(ctx,cat,series,batch)
        value['relation_candidates']=[{'from_node_id':ctx.known_node_ids[0],'to_node_id':ctx.known_node_ids[0],
            'relation_type':'related_to','scope':'','supporting_claim_refs':['C1'],'confidence':'0.9','reason':''}]
        old.append(legacy.record_to_result(json.dumps(v2(value,batch.assigned_evidence_refs)),series,batch,cat,ctx))
        new.append(adapter.record_to_result(json.dumps(value),series,batch,cat,ctx))
        native=FakeNativeJsonAdapter().normalize(json.loads(old[-1].wire_json),batch.assigned_evidence_refs,{'node_candidates':[],'source_references':[]})
        fake.append(core.record_to_result(native,series,batch,cat,ctx))
    assert aggregate_segment_wires(series,plan,tuple(old),cat,ctx)==aggregate_segment_wires(series,plan,tuple(new),cat,ctx)==aggregate_segment_wires(series,plan,tuple(fake),cat,ctx)


@pytest.mark.parametrize('response',['historical_mismatch','v3_under_old_attempt'])
def test_ledger_original_unversioned_attempt_uses_frozen_contract(tmp_path,monkeypatch,response):
    from test_output_decomposition_durability import setup
    from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
    from pro_a.workbench.config import BoundaryError
    from pro_a.workbench.store import Store
    config,ledger,ctx,cat,series,plan=setup(tmp_path,1);batch=plan.leaves[0]
    prompt=json.dumps({'target':{'provider_record_version':legacy.RECORD_VERSION}},separators=(',',':')).encode()
    prompt_path=ledger._path(series.series_id,batch.segment_id+'.prompt.json')
    prompt_path.parent.mkdir(parents=True,exist_ok=True)
    prompt_path.write_bytes(prompt)
    original=ledger._request
    def old_request(*args,**kwargs):return original(*args,provider_record_version='')
    monkeypatch.setattr(ledger,'_request',old_request)
    fence=ledger.claim_segment(batch.segment_id,'worker')
    attempt=ledger.reserve_attempt(batch.segment_id,'worker',fence,attempt_number=1,
        payload_sha256=hashlib.sha256(prompt).hexdigest(),configuration_sha256='b'*64)
    assert 'provider_record_version' not in json.loads(attempt['request_json'])
    ledger.record_dispatch(attempt['attempt_id'],'worker',fence)
    value=record(ctx,cat,series,batch)
    if response=='historical_mismatch':
        value=v2(value,batch.assigned_evidence_refs);value['dispositions'][0]['claim_refs']=[]
    ledger.record_outcome(attempt['attempt_id'],'worker',fence,json.dumps(value).encode(),finish_reason='tool_calls',output_tokens=50)
    path=ledger._path(series.series_id,attempt['attempt_id']+'.raw.json');raw=path.read_bytes()
    fresh=BoundedExtractionStore(config)
    with pytest.raises(BoundaryError,match='INVALID_SEGMENT_RESPONSE'):fresh.reconcile_attempt(attempt['attempt_id'],'worker',fence,cat,ctx)
    assert path.read_bytes()==raw and fresh.read(series.series_id)[3].provider_call_count==1
    with Store(config).connect() as c:
        assert c.execute('SELECT count(*) FROM bounded_extraction_segment_results').fetchone()[0]==0
        assert dict(c.execute('SELECT * FROM bounded_extraction_attempts').fetchone())==attempt


def test_current_attempt_pins_v3_contract_without_schema_migration(tmp_path):
    from test_output_decomposition_durability import setup,complete
    from pro_a.workbench.store import Store
    from pro_a.workbench.review_store import schema_version
    config,ledger,ctx,cat,series,plan=setup(tmp_path,1)
    complete(ledger,ctx,cat,series,plan.leaves[0])
    with Store(config).connect() as c:
        request=json.loads(c.execute('SELECT request_json FROM bounded_extraction_attempts').fetchone()[0])
        assert request['provider_record_version']==adapter.RECORD_VERSION
        assert schema_version(c)=='12'
