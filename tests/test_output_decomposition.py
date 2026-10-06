"""Whole semantic context / bounded output responsibility, offline only."""
import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from pro_a import output_decomposition as output
from pro_a.bounded_extraction import (OUTPUT_SERIES_VERSION, SeriesBudget, create_extraction_series,
    initial_extraction_plan, aggregate_segment_wires, expand_source_analysis_wire_v3, subdivide_extraction_plan)
from pro_a.source_analysis_wire import build_source_evidence_catalog
from lexical_record_helpers import from_wire
from test_bounded_extraction import result, v3
from test_source_analysis_wire import context, canonical_claim, empty_canonical


def fixture(count=17, *, text=None, budget=SeriesBudget()):
    ctx = context(text or '\n'.join(f'Synthetic product {i} has capacity {i+1} units.' for i in range(count)), ('NODE_SYNTHETIC',))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, 'RUN_SYNTHETIC', budget, series_version=OUTPUT_SERIES_VERSION)
    return ctx, catalog, series, initial_extraction_plan(series)


def record(ctx, catalog, series, batch, *, density=1):
    raw = empty_canonical()
    units = [u for u in catalog.units if u.evidence_ref in batch.assigned_evidence_refs]
    raw['claims'] = [canonical_claim(u.exact_text, u, i+1) for i,u in enumerate(units) for _ in range(density)]
    for i,claim in enumerate(raw['claims'],1):
        claim['claim_ref'] = f'C{i}'
    value = from_wire(v3(raw, catalog))
    value['dispositions'] = [{'evidence_ref':r,'disposition':'CLAIMED'} for r in batch.assigned_evidence_refs]
    return value


def accepted(ctx, catalog, series, batch, value=None):
    return output.record_to_result(json.dumps(value or record(ctx,catalog,series,batch)), series, batch, catalog, ctx)


def payload(ctx, catalog, series, batch):
    return output.segment_payload({'native':{'scoped_node_catalog':[]}}, ctx, catalog, series, batch)


@pytest.mark.parametrize('separator', ['\n','\n\n','\n说话人乙：\n','\n[00:20]\n','\n第二节：\n'])
def test_complete_context_owned_tags_only(separator):
    text = '以下产能数据仅指青松公司。' + separator + '该公司现有产能为100台。'
    ctx, catalog, series, plan = fixture(text=text, budget=SeriesBudget(initial_evidence_refs=1))
    target = catalog.units[-1]
    batch = plan.leaves[-1]
    rendered = output.annotated_source(ctx,catalog,batch.assigned_evidence_refs)
    assert rendered.replace('['+target.evidence_ref+']','').replace('[/'+target.evidence_ref+']','') == text
    request = payload(ctx,catalog,series,batch)
    encoded = json.dumps(request, ensure_ascii=False)
    assert '以下产能数据仅指青松公司。' in encoded and '该公司现有产能为100台。' in encoded
    assert all(u.evidence_ref not in encoded for u in catalog.units[:-1])
    value = record(ctx,catalog,series,batch)
    value['claims'][0]['statement'] = '青松公司现有产能为100台'
    bound = accepted(ctx,catalog,series,batch,value)
    canonical = expand_source_analysis_wire_v3(json.loads(bound.wire_json),catalog,ctx)
    assert canonical['claims'][0]['statement'] == '青松公司现有产能为100台'
    assert canonical['claims'][0]['evidence_excerpt'] == target.exact_text


def test_run8_foreign_id_failure_shape_is_not_selectable():
    ctx,catalog,series,plan = fixture(61)
    body = payload(ctx,catalog,series,plan.leaves[0])
    encoded = json.dumps(body, ensure_ascii=False)
    assert len(catalog.units[16:]) == 45
    assert all(u.evidence_ref not in encoded and u.exact_text in encoded for u in catalog.units[16:])
    assert sum(u.evidence_ref in encoded for u in catalog.units) == 16


@pytest.mark.parametrize('ref_kind',['owned','foreign','invented'])
@pytest.mark.parametrize('family',['claim','match','event','preserved','candidate_anchor','reference_anchor'])
def test_all_families_enforce_ownership(ref_kind,family):
    ctx,catalog,series,plan = fixture()
    batch = plan.leaves[0]
    value = record(ctx,catalog,series,batch)
    ref = batch.assigned_evidence_refs[0] if ref_kind == 'owned' else catalog.units[-1].evidence_ref if ref_kind == 'foreign' else 'EV_INVENTED'
    evidence = {'evidence_ref':ref,'selection_mode':'WHOLE_UNIT','selector':'','occurrence':'1'}
    if family == 'claim':
        value['claims'][0]['evidence'] = evidence
    elif family == 'match':
        value['node_matches'] = [{'node_id':ctx.known_node_ids[0], 'role':'primary','confidence':'0.9','reason':'','evidence':evidence}]
    elif family == 'reference_anchor':
        value['source_references'] = [{'title':'Synthetic source','relation_type':'references','note':'','ownership_evidence_ref':ref}]
    else:
        from test_source_analysis_wire import normal_node
        raw = empty_canonical()
        raw['node_candidates'] = [normal_node()]
        candidate = from_wire(v3(raw,catalog))['node_candidates'][0]
        candidate['ownership_evidence_ref'] = batch.assigned_evidence_refs[0]
        if family == 'candidate_anchor': candidate['ownership_evidence_ref'] = ref
        elif family == 'event':
            candidate.update(primary_type='Event',is_discrete_event='TRUE',event_time='2026-01-01',event_evidence=evidence)
        else:
            candidate['preserved_fields']['evidence_ref'] = {'present':'TRUE','value':evidence}
        value['node_candidates'] = [candidate]
    if ref_kind == 'owned':
        accepted(ctx,catalog,series,batch,value)
    else:
        with pytest.raises(ValueError): accepted(ctx,catalog,series,batch,value)


@pytest.mark.parametrize('mutation',['missing','duplicate','wrong_claimed','subdivision'])
def test_dispositions_exact(mutation):
    ctx,catalog,series,plan = fixture()
    batch=plan.leaves[0]; value=record(ctx,catalog,series,batch)
    if mutation=='missing': value['dispositions'].pop()
    elif mutation=='duplicate': value['dispositions'].append(value['dispositions'][0])
    else: value['dispositions'][0]['disposition']='NO_INDEPENDENT_CLAIM' if mutation=='wrong_claimed' else 'SUBDIVISION_REQUIRED'
    with pytest.raises(ValueError): accepted(ctx,catalog,series,batch,value)


def test_metadata_conflict_and_historical_identity_distinct():
    ctx,catalog,series,plan=fixture()
    old=create_extraction_series(ctx,catalog,series.processing_run_id)
    assert old.series_id != series.series_id
    first=accepted(ctx,catalog,series,plan.leaves[0])
    value=record(ctx,catalog,series,plan.leaves[1]);value['source_metadata']['title']+=' changed'
    second=accepted(ctx,catalog,series,plan.leaves[1],value)
    with pytest.raises(ValueError,match='SOURCE_METADATA_CONFLICT'):
        aggregate_segment_wires(series,plan,(first,second),catalog,ctx)


def test_exact_canonical_native_and_permanent_identity(tmp_path):
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    from stability_helpers import make_config
    ctx,catalog,series,plan=fixture()
    results=tuple(accepted(ctx,catalog,series,b) for b in plan.leaves)
    aggregate=aggregate_segment_wires(series,plan,results,catalog,ctx)
    full=empty_canonical()
    full['claims']=[canonical_claim(u.exact_text,u,i+1) for i,u in enumerate(catalog.units)]
    # Lexical conversion supplies qualified explicit optional defaults.
    canonical=expand_source_analysis_wire_v3(output.lexical.provider_record_to_wire_v3(from_wire(v3(full,catalog))),catalog,ctx)
    decomposed=expand_source_analysis_wire_v3(json.loads(aggregate.wire_json),catalog,ctx)
    assert decomposed==canonical
    cfg,db=make_config(tmp_path)
    analyzer=Analyzer(cfg,db)
    def analyze(value):
        analyzer.llm=SimpleNamespace(available=True,json=lambda *a:copy.deepcopy(value))
        return analyzer.analyze_source('synthetic.txt',ctx.piece.source_text,'deep',adaptive_retry_policy='forbid')
    left,right=analyze(canonical),analyze(decomposed)
    assert left==right
    for i,(a,b) in enumerate(zip(left.claims,right.claims)):
        assert deterministic_id('CLM',{'source_sha256':ctx.source_sha256,'claim_index':i,'claim':a})==deterministic_id('CLM',{'source_sha256':ctx.source_sha256,'claim_index':i,'claim':b})


def test_multilevel_subdivision_full_context_and_policy():
    ctx,catalog,series,plan=fixture(16)
    plan=subdivide_extraction_plan(series,plan,plan.leaves[0].segment_id)
    assert [len(b.assigned_evidence_refs) for b in plan.leaves]==[8,8]
    plan=subdivide_extraction_plan(series,plan,plan.leaves[0].segment_id)
    assert [len(b.assigned_evidence_refs) for b in plan.leaves]==[4,4,8]
    for batch in plan.leaves:
        rendered=output.annotated_source(ctx,catalog,batch.assigned_evidence_refs)
        for ref in batch.assigned_evidence_refs:
            rendered=rendered.replace('['+ref+']','').replace('[/'+ref+']','')
        assert rendered==ctx.piece.source_text
    aggregate=aggregate_segment_wires(series,plan,tuple(accepted(ctx,catalog,series,b) for b in plan.leaves),catalog,ctx)
    assert aggregate.coverage.complete
    assert aggregate.coverage.terminal_assigned_refs==series.eligible_evidence_refs


@pytest.mark.parametrize('limit',['single','depth','leaves'])
def test_policy_fails_closed(limit):
    budget=SeriesBudget(max_subdivision_depth=1) if limit=='depth' else SeriesBudget(max_leaf_segments=1) if limit=='leaves' else SeriesBudget()
    _,_,series,plan=fixture(1 if limit=='single' else 4,budget=budget)
    if limit=='depth': plan=subdivide_extraction_plan(series,plan,plan.leaves[0].segment_id)
    with pytest.raises(ValueError,match='DENSITY_EXCEEDS_BOUNDED_POLICY'):
        subdivide_extraction_plan(series,plan,plan.leaves[0].segment_id)


def test_all_canonical_families_exact_with_duplicate_candidate(tmp_path):
    from test_source_analysis_wire import mixed_fixture
    from stability_helpers import make_config
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    cfg,db=make_config(tmp_path)
    nodes=(db.add_node('示例产品甲','Product'),db.add_node('示例技术乙','Technology'))
    ctx,catalog,full=mixed_fixture(nodes)
    # A representable ordered fixture: Claims of earlier-owned units precede later units.
    full['claims']=[full['claims'][i] for i in (0,3,1,2)]
    for i,c in enumerate(full['claims'],1): c['claim_ref']=f'C{i}'
    # A second directly supported local relation exercises a nonzero C offset.
    full['relation_candidates'].append({**full['relation_candidates'][0],'supporting_claim_refs':['C3']})
    series=create_extraction_series(ctx,catalog,'RUN_SYNTHETIC',SeriesBudget(initial_evidence_refs=2),series_version=OUTPUT_SERIES_VERSION)
    plan=initial_extraction_plan(series)
    records=[]
    for index,batch in enumerate(plan.leaves):
        raw=copy.deepcopy(full)
        raw['claims']=raw['claims'][index*2:index*2+2]
        for i,c in enumerate(raw['claims'],1): c['claim_ref']=f'C{i}'
        raw['node_candidates']=raw['node_candidates'][:2] if index==0 else [raw['node_candidates'][0],*raw['node_candidates'][2:]]
        raw['node_matches']=raw['node_matches'] if index==0 else []
        raw['source_references']=raw['source_references'] if index==0 else []
        raw['relation_candidates']=[{**raw['relation_candidates'][index],'supporting_claim_refs':['C1']}]
        value=from_wire(v3(raw,catalog))
        for family in ('node_candidates','source_references'):
            for obj in value[family]:obj['ownership_evidence_ref']=batch.assigned_evidence_refs[0]
        used={c['evidence']['evidence_ref'] for c in value['claims']}
        value['dispositions']=[{'evidence_ref':r,'disposition':'CLAIMED' if r in used else 'NO_INDEPENDENT_CLAIM'} for r in batch.assigned_evidence_refs]
        records.append(accepted(ctx,catalog,series,batch,value))
    aggregate=aggregate_segment_wires(series,plan,tuple(records),catalog,ctx)
    wire=json.loads(aggregate.wire_json)
    expected=output.lexical.provider_record_to_wire_v3(from_wire(v3(full,catalog)))
    assert wire==expected
    left=expand_source_analysis_wire_v3(expected,catalog,ctx)
    right=expand_source_analysis_wire_v3(wire,catalog,ctx)
    assert left==right==full
    assert 'ownership_evidence_ref' not in aggregate.wire_json and 'dispositions' not in aggregate.wire_json
    analyzer=Analyzer(cfg,db)
    def native(value):
        analyzer.llm=SimpleNamespace(available=True,json=lambda *a:copy.deepcopy(value))
        return analyzer.analyze_source('synthetic.txt',ctx.piece.source_text,'deep',adaptive_retry_policy='forbid')
    a,b=native(left),native(right)
    assert a==b
    assert len(a.claims)==len(full['claims'])
    for i,(old,new) in enumerate(zip(a.claims,b.claims)):
        def identity(claim):
            return deterministic_id('CLM',{'source_sha256':ctx.source_sha256,'claim_index':i,
                'claim':{k:v for k,v in claim.items() if not k.startswith('origin_')}})
        assert identity(old)==identity(new)


def test_candidate_conflict_fails_without_first_wins():
    from test_source_analysis_wire import normal_node
    ctx,catalog,series,plan=fixture(2,budget=SeriesBudget(initial_evidence_refs=1))
    results=[]
    for i,batch in enumerate(plan.leaves):
        raw=empty_canonical();raw['node_candidates']=[normal_node()]
        value=record(ctx,catalog,series,batch)
        candidate=from_wire(v3(raw,catalog))['node_candidates'][0]
        candidate['ownership_evidence_ref']=batch.assigned_evidence_refs[0]
        candidate['description']+=str(i)
        value['node_candidates']=[candidate]
        results.append(accepted(ctx,catalog,series,batch,value))
    with pytest.raises(ValueError,match='NODE_CANDIDATE_CONFLICT'):
        aggregate_segment_wires(series,plan,tuple(results),catalog,ctx)
