"""Exact provider bookkeeping; research and durable coverage semantics stay fixed."""
import copy
import json

import pytest

from pro_a import output_decomposition_legacy as output
from pro_a.bounded_extraction import EvidenceDisposition, create_segment_wire_result, aggregate_segment_wires
from lexical_record_helpers import claim_linkages, from_wire
from test_output_decomposition import fixture, record as current_record
from test_source_analysis_wire import empty_canonical, normal_node
from test_bounded_extraction import v3


def record(ctx,cat,series,batch,**kwargs):
    value=current_record(ctx,cat,series,batch,**kwargs)
    value.pop('evidence_acknowledgements')
    value['dispositions']=claim_linkages(value,batch.assigned_evidence_refs)
    return value


def accepted(ctx,cat,series,batch,value):
    return output.record_to_result(json.dumps(value),series,batch,cat,ctx)


def three_claims():
    ctx,cat,series,plan=fixture(3)
    batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    value['claims'][2]['evidence']=copy.deepcopy(value['claims'][0]['evidence'])
    value['dispositions']=claim_linkages(value,batch.assigned_evidence_refs)
    return ctx,cat,series,batch,value


def old_internal_result(ctx,cat,series,batch,value,dispositions=None):
    stripped=copy.deepcopy(value);stripped.pop('dispositions')
    for family in ('node_candidates','source_references'):
        for obj in stripped[family]:obj.pop('ownership_evidence_ref')
    wire=output.lexical.provider_record_to_wire_v3(stripped)
    used={c['evidence_ref'] for c in wire['claims']}
    old=dispositions or tuple(EvidenceDisposition(r,'CLAIMED' if r in used else 'NO_INDEPENDENT_CLAIM') for r in batch.assigned_evidence_refs)
    return create_segment_wire_result(series,batch,wire,old,cat,ctx)


def test_run12_old_mismatch_stays_rejected_v2_empty_link_passes():
    ctx,cat,series,plan=fixture(1);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    value['claims']=[];value['dispositions']=claim_linkages(value,batch.assigned_evidence_refs)
    with pytest.raises(ValueError,match='^CLAIM_DISPOSITION_MISMATCH$'):
        old_internal_result(ctx,cat,series,batch,value,(EvidenceDisposition(batch.assigned_evidence_refs[0],'CLAIMED'),))
    result=accepted(ctx,cat,series,batch,value)
    assert result.dispositions==(EvidenceDisposition(batch.assigned_evidence_refs[0],'NO_INDEPENDENT_CLAIM'),)
    value['dispositions'][0]={'evidence_ref':batch.assigned_evidence_refs[0],'disposition':'CLAIMED'}
    with pytest.raises(ValueError,match='INVALID_PROVIDER_RECORD_SHAPE'):accepted(ctx,cat,series,batch,value)


@pytest.mark.parametrize('refs,error',[
    ([], 'CLAIM_LINKAGE_MISMATCH'),(['C1'],'CLAIM_LINKAGE_MISMATCH'),(['C3'],'CLAIM_LINKAGE_MISMATCH'),
    (['C1','C2'],'CLAIM_LINKAGE_MISMATCH'),(['C1','C3','C2'],'CLAIM_LINKAGE_MISMATCH'),
    (['C1','C3','C4'],'UNKNOWN_LOCAL_CLAIM_LINK'),(['C1','C1','C3'],'DUPLICATE_LOCAL_CLAIM_LINK'),
    (['C0'],'INVALID_LOCAL_CLAIM_LINK'),(['C01'],'INVALID_LOCAL_CLAIM_LINK'),
    (['C-1'],'INVALID_LOCAL_CLAIM_LINK'),(['C1.0'],'INVALID_LOCAL_CLAIM_LINK'),
    ([' C1'],'INVALID_LOCAL_CLAIM_LINK'),(['c1'],'INVALID_LOCAL_CLAIM_LINK'),
    (['C١'],'INVALID_LOCAL_CLAIM_LINK'),(['C999999999999999999999999999999'],'UNKNOWN_LOCAL_CLAIM_LINK'),
    ([True],'INVALID_PROVIDER_RECORD_SHAPE'),([1],'INVALID_PROVIDER_RECORD_SHAPE'),
    ('C1','INVALID_PROVIDER_RECORD_SHAPE'),(None,'INVALID_PROVIDER_RECORD_SHAPE'),
])
def test_linkage_exact_set_and_local_reference_validation(refs,error):
    ctx,cat,series,batch,value=three_claims();value['dispositions'][0]['claim_refs']=refs
    with pytest.raises(ValueError,match='^'+error+'$'):accepted(ctx,cat,series,batch,value)


@pytest.mark.parametrize('reverse_claim_refs',[False,True])
@pytest.mark.parametrize('reverse_records',[False,True])
def test_multi_claim_and_linkage_order_have_identical_internal_result(reverse_claim_refs,reverse_records):
    ctx,cat,series,batch,value=three_claims()
    expected=old_internal_result(ctx,cat,series,batch,value)
    if reverse_claim_refs:value['dispositions'][0]['claim_refs'].reverse()
    if reverse_records:value['dispositions'].reverse()
    untouched=copy.deepcopy(value)
    result=accepted(ctx,cat,series,batch,value)
    assert result==expected and value==untouched
    assert [d.disposition for d in result.dispositions]==['CLAIMED','CLAIMED','NO_INDEPENDENT_CLAIM']
    assert 'claim_refs' not in result.wire_json


@pytest.mark.parametrize('mutation,error',[
    ('missing','MISSING_EVIDENCE_LINKAGE'),('duplicate','DUPLICATE_EVIDENCE_LINKAGE'),
    ('invented','FOREIGN_EVIDENCE_LINKAGE'),('foreign','FOREIGN_EVIDENCE_LINKAGE')])
def test_every_assigned_unit_exactly_once(mutation,error):
    ctx,cat,series,plan=fixture(17);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    if mutation=='missing':value['dispositions'].pop()
    elif mutation=='duplicate':value['dispositions'].append(copy.deepcopy(value['dispositions'][0]))
    else:value['dispositions'][0]['evidence_ref']=cat.units[-1].evidence_ref if mutation=='foreign' else 'EV_INVENTED'
    with pytest.raises(ValueError,match='^'+error+'$'):accepted(ctx,cat,series,batch,value)


@pytest.mark.parametrize('family',['candidate','Theme','ResearchQuestion','node_match','source_reference','Event','preserved'])
def test_non_claim_families_never_count_as_claim(family):
    ctx,cat,series,plan=fixture(1);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    ref=batch.assigned_evidence_refs[0];selection=copy.deepcopy(value['claims'][0]['evidence'])
    value['claims']=[];value['dispositions']=claim_linkages(value,batch.assigned_evidence_refs)
    if family=='node_match':
        value['node_matches']=[{'node_id':ctx.known_node_ids[0],'role':'primary','confidence':'0.9','reason':'','evidence':selection}]
    elif family=='source_reference':
        value['source_references']=[{'title':'Synthetic source','relation_type':'references','note':'','ownership_evidence_ref':ref}]
    else:
        raw=empty_canonical();raw['node_candidates']=[normal_node()]
        node=from_wire(v3(raw,cat))['node_candidates'][0];node['ownership_evidence_ref']=ref
        if family=='Event':node.update(primary_type='Event',is_discrete_event='TRUE',event_time='2026-01-01',event_evidence=selection)
        elif family=='Theme':node.update(primary_type='Theme',long_term_research_value='TRUE',cross_source_or_node_value='TRUE')
        elif family=='ResearchQuestion':node.update(primary_type='ResearchQuestion',question='Synthetic question?',importance='Synthetic importance',what_would_change_my_mind='Synthetic measurement')
        elif family=='preserved':node['preserved_fields']['evidence_ref']={'present':'TRUE','value':selection}
        value['node_candidates']=[node]
    result=accepted(ctx,cat,series,batch,value)
    assert result==old_internal_result(ctx,cat,series,batch,value)
    assert result.dispositions[0].disposition=='NO_INDEPENDENT_CLAIM'
    value['dispositions'][0]['claim_refs']=['C1']
    with pytest.raises(ValueError,match='UNKNOWN_LOCAL_CLAIM_LINK'):accepted(ctx,cat,series,batch,value)


@pytest.mark.parametrize('mode',['WHOLE_UNIT','RAW_SUBSPAN','NORMALIZED_SUBSPAN'])
def test_invalid_claim_selection_rejected_before_disposition_derivation(monkeypatch,mode):
    ctx,cat,series,plan=fixture(1);batch=plan.leaves[0];value=record(ctx,cat,series,batch)
    evidence=value['claims'][0]['evidence'];evidence['selection_mode']=mode
    evidence['selector']='absent synthetic substring'
    def forbidden(*args,**kwargs):pytest.fail('DERIVED_BEFORE_CLAIM_EVIDENCE_VALID')
    monkeypatch.setattr(output,'EvidenceDisposition',forbidden)
    with pytest.raises(ValueError):accepted(ctx,cat,series,batch,value)


@pytest.mark.parametrize('count',[1,2,17])
@pytest.mark.parametrize('density',[1,3])
def test_v1_v2_internal_and_aggregate_exact_equivalence(count,density):
    ctx,cat,series,plan=fixture(count);old=[];new=[]
    for batch in plan.leaves:
        value=record(ctx,cat,series,batch,density=density)
        old.append(old_internal_result(ctx,cat,series,batch,value));new.append(accepted(ctx,cat,series,batch,value))
    assert old==new
    assert aggregate_segment_wires(series,plan,tuple(old),cat,ctx)==aggregate_segment_wires(series,plan,tuple(new),cat,ctx)


def test_provider_versions_and_closed_schema():
    schema=output.record_schema()['properties']['dispositions']['items']
    assert schema['additionalProperties'] is False
    assert set(schema['required'])=={'evidence_ref','claim_refs'}
    assert schema['properties']['claim_refs']=={'type':'array','items':{'type':'string'}}
    assert output.RECORD_VERSION.endswith('-v2')


@pytest.mark.parametrize('window',['raw_artifact_durable','outcome_durable'])
def test_recovery_revalidates_bad_linkage_without_recall(tmp_path,monkeypatch,window):
    from pro_a.workbench import bounded_extraction_persistence as persistence
    from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
    from pro_a.workbench.config import BoundaryError
    from pro_a.workbench.store import Store
    from test_output_decomposition_durability import setup
    from test_bounded_extraction_persistence import reserve
    config,ledger,ctx,cat,series,plan=setup(tmp_path,1)
    batch=plan.leaves[0];fence,aid=reserve(ledger,batch)
    ledger.record_dispatch(aid,'worker',fence)
    value=record(ctx,cat,series,batch);value['dispositions'][0]['claim_refs']=[]
    def crash(name):
        if name==window:raise RuntimeError('SYNTHETIC_CRASH')
    monkeypatch.setattr(persistence,'checkpoint',crash)
    with pytest.raises(RuntimeError,match='SYNTHETIC_CRASH'):
        ledger.record_outcome(aid,'worker',fence,json.dumps(value).encode(),finish_reason='tool_calls',output_tokens=50)
    path=ledger._path(series.series_id,aid+'.raw.json');immutable=path.read_bytes()
    monkeypatch.setattr(persistence,'checkpoint',lambda _:None)
    fresh=BoundedExtractionStore(config)
    with pytest.raises(BoundaryError,match='^INVALID_SEGMENT_RESPONSE$'):
        fresh.reconcile_attempt(aid,'worker',fence,cat,ctx)
    assert path.read_bytes()==immutable
    assert fresh.read(series.series_id)[3].provider_call_count==1
    with Store(config).connect() as c:
        assert c.execute('SELECT state FROM bounded_extraction_segments').fetchone()[0]=='FAILED'
        assert c.execute('SELECT count(*) FROM bounded_extraction_segment_results').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM bounded_extraction_segments').fetchone()[0]==1
        assert c.execute('SELECT count(*) FROM bounded_extraction_attempts').fetchone()[0]==1
