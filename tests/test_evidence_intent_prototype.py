"""Synthetic evidence intent -> frozen V6 compiler -> Wire/native projection.

Semantic counterexamples remain unproved; neither a fake model nor fixture
expectations are an independent semantic authorization mechanism.
"""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest

from pro_a import evidence_intent_prototype as intent
from pro_a import output_decomposition as output, output_provider_record_v6 as v6
from pro_a.bounded_extraction import (OWNERSHIP_OUTPUT_SERIES_VERSION, SeriesBudget,
    create_extraction_series, initial_extraction_plan, subdivide_extraction_plan,
    expand_source_analysis_wire_v3)
from pro_a.evidence_binding import identity
from pro_a.source_analysis_wire import build_source_evidence_catalog
from lexical_record_helpers import from_canonical
from node_intent_helpers import from_valid_v4
from provider_record_v4_helpers import from_valid_v3
from test_source_analysis_wire import context, canonical_claim, empty_canonical, normal_node


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', lambda *a, **k: pytest.fail('REAL_PROVIDER_FORBIDDEN'))


def setup(text, *, budget=SeriesBudget()):
    ctx = context(text, ('NODE_A', 'NODE_B'))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_OFFLINE_INTENT', budget,
                                     series_version=OWNERSHIP_OUTPUT_SERIES_VERSION)
    return ctx, catalog, series, initial_extraction_plan(series)


def v6_record(catalog, segment, canonical):
    old = from_canonical(canonical, catalog)
    old['evidence_acknowledgements'] = [{'evidence_ref': r} for r in segment.assigned_evidence_refs]
    for family in ('node_candidates', 'source_references'):
        for obj in old[family]:
            obj['ownership_evidence_ref'] = segment.assigned_evidence_refs[0]
    value = from_valid_v4(from_valid_v3(old))
    for node in value['node_candidates']:
        del node['ownership_evidence_ref']
    return value


def new_record(value, catalog):
    """Test-only conversion of newly constructed synthetic data, never old Raw."""
    anchors = {u.evidence_ref: intent.unit_anchor(u) for u in catalog.units}
    def transform(obj):
        if type(obj) is dict:
            if set(obj) == {'evidence_ref', 'selection_mode', 'selector', 'occurrence'}:
                assert obj['selection_mode'] == 'WHOLE_UNIT'
                return {'kind': 'UNIT_ANCHOR', 'value': anchors[obj['evidence_ref']]}
            return {k: transform(v) for k, v in obj.items()}
        if type(obj) is list:
            return [transform(v) for v in obj]
        return obj
    record = transform(copy.deepcopy(value))
    record['protocol_version'] = intent.VERSION
    record['evidence_acknowledgements'] = [{'anchor_id': anchors[a['evidence_ref']]} for a in value['evidence_acknowledgements']]
    for reference in record['source_references']:
        reference['ownership_anchor'] = anchors[reference.pop('ownership_evidence_ref')]
    return record


def claim_record(catalog, segment, unit, statement=None):
    canonical = empty_canonical()
    canonical['claims'] = [canonical_claim(statement or unit.exact_text, unit)]
    old = v6_record(catalog, segment, canonical)
    return new_record(old, catalog), old


def compile_case(data, segment, record):
    ctx, catalog, series, plan = data
    return intent.compile_binding_candidate(json.dumps(record, ensure_ascii=False), series, plan, segment, catalog, ctx)


def projection(data, result):
    return expand_source_analysis_wire_v3(json.loads(result.wire_json), data[1], data[0])


def test_single_unit_strict_schema_and_full_fact_without_execution_metadata():
    data = setup('青松公司现有产能为100台。')
    ctx, catalog, series, plan = data
    record, old = claim_record(catalog, plan.leaves[0], catalog.units[0])
    jsonschema.Draft202012Validator.check_schema(intent.record_schema())
    jsonschema.validate(record, intent.record_schema())
    result, proof = compile_case(data, plan.leaves[0], record)
    assert result == v6.compile_result(json.dumps(old), series, plan.leaves[0], catalog, ctx)[0]
    assert projection(data, result)['claims'][0]['statement'] == catalog.units[0].exact_text
    assert proof['status'] == 'NON_CANONICAL_BINDING_CANDIDATE' and proof['segment_accepted'] is False
    assert proof['semantic_authorization'] == 'NOT_ESTABLISHED'
    assert set(record['claims'][0]['evidence']) == {'kind', 'value'}
    schema = json.dumps(intent.record_schema())
    assert all(k not in schema for k in ('evidence_selector', 'occurrence', 'anyOf', 'ownership_evidence_ref'))


@pytest.mark.parametrize('boundary', ['same_segment', 'unit16_17', 'subdivision8_9'])
def test_question_answer_ownership_without_losing_context(boundary):
    question = '青松公司的当前产能是多少？'
    answer = '该公司现有产能为100台。'
    padding = [f'合成事项{i}有独立编号{i}。' for i in range(15 if boundary == 'unit16_17' else 7 if boundary == 'subdivision8_9' else 0)]
    tail = [f'合成后缀{i}有独立编号{i}。' for i in range(7)] if boundary == 'subdivision8_9' else []
    data = setup('\n'.join([*padding, question, answer, *tail]))
    ctx, catalog, series, plan = data
    if boundary == 'subdivision8_9':
        plan = subdivide_extraction_plan(series, plan, plan.leaves[0].segment_id)
        data = ctx, catalog, series, plan
    q = next(u for u in catalog.units if u.exact_text == question)
    a = next(u for u in catalog.units if u.exact_text == answer)
    owner = next(s for s in plan.leaves if a.evidence_ref in s.assigned_evidence_refs)
    qowner = next(s for s in plan.leaves if q.evidence_ref in s.assigned_evidence_refs)
    payload = intent.request_payload(series, plan, owner, catalog, ctx)
    assert ''.join(r['text'] for r in payload['source_regions']) == ctx.piece.source_text
    question_region = next(r for r in payload['source_regions'] if r['text'] == question)
    assert question_region['role'] == ('ASSIGNED' if owner == qowner else 'CONTEXT')
    if owner != qowner:
        assert 'anchor_id' not in question_region
        foreign, _ = claim_record(catalog, qowner, q)
        foreign['claims'][0]['statement'] = '青松公司现有产能为100台。'
        foreign['claims'][0]['evidence'] = {'kind': 'EXACT_QUOTE', 'value': answer}
        untouched = copy.deepcopy(foreign)
        with pytest.raises(intent.IntentBindingError, match='INTENT_SUPPORT_OUTSIDE_ASSIGNED_SEGMENT') as failure:
            compile_case(data, qowner, foreign)
        assert failure.value.details['owner_segment_ids'] == [owner.segment_id]
        assert failure.value.details['scheduled'] is False and foreign == untouched
    record, _ = claim_record(catalog, owner, a, '青松公司现有产能为100台。')
    result, proof = compile_case(data, owner, record)
    assert projection(data, result)['claims'][0]['statement'] == '青松公司现有产能为100台。'
    assert projection(data, result)['claims'][0]['evidence_excerpt'] == answer
    assert proof['semantic_authorization'] == 'NOT_ESTABLISHED'  # Representation is not referent proof.


@pytest.mark.parametrize('text,quote', [
    ('产能为100台。\n产能为100台。', '产能为100台。'),
    ('banana', 'ana'),
])
def test_duplicate_quotes_are_unresolved_but_explicit_unit_anchors_are_distinct(text, quote):
    data = setup(text); catalog, plan = data[1], data[3]
    # Repeated text cannot use the existing inverse fixture; construct one valid
    # new synthetic record first, then replace only its evidence intent.
    seed = setup('独立合成事实。')
    record, _ = claim_record(seed[1], seed[3].leaves[0], seed[1].units[0])
    record['evidence_acknowledgements'] = [{'anchor_id': intent.unit_anchor(u)} for u in catalog.units]
    record['claims'][0]['evidence'] = {'kind': 'EXACT_QUOTE', 'value': quote}
    with pytest.raises(intent.IntentBindingError, match='INTENT_QUOTE_AMBIGUOUS'):
        compile_case(data, plan.leaves[0], record)
    results = []
    for unit in catalog.units:
        record['claims'][0]['evidence'] = {'kind': 'UNIT_ANCHOR', 'value': intent.unit_anchor(unit)}
        results.append(compile_case(data, plan.leaves[0], record)[1]['bindings'][0]['binding'])
    assert len({r['source_start'] for r in results}) == len(catalog.units)


@pytest.mark.parametrize('source,statement', [
    ('以下产能数据仅指青松公司。\n白杨公司与本次产能数据无关。\n该公司现有产能为100台。', '白杨公司现有产能为100台。'),
    ('青松公司和白杨公司均参加了会议。\n该公司现有产能为100台。', '青松公司现有产能为100台。'),
    ('青松公司现有产能为100台。', '青松公司现有产能为200台。'),
])
def test_exact_location_never_authorizes_exclusion_anaphora_or_false_measurement(source, statement):
    data = setup(source); catalog, plan = data[1], data[3]
    record, _ = claim_record(catalog, plan.leaves[0], catalog.units[-1], statement)
    result, proof = compile_case(data, plan.leaves[0], record)
    claim = projection(data, result)['claims'][0]
    assert claim['statement'] == statement and claim['evidence_excerpt'] == catalog.units[-1].exact_text
    assert proof['semantic_authorization'] == 'NOT_ESTABLISHED' and not proof['segment_accepted']
    # Deliberately demonstrate the PR101 limitation, not a pretend NLI PASS:
    # exact binding succeeds for the wrong/excluded or ambiguous subject too.


def test_whole_raw_subspan_native_and_permanent_identity_parity(tmp_path):
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    from stability_helpers import make_config
    from types import SimpleNamespace
    data = setup('[[PARA:1]]\n青松公司现有产能为100台。')
    record, old = claim_record(data[1], data[3].leaves[0], data[1].units[0])
    whole, _ = compile_case(data, data[3].leaves[0], record)
    record['claims'][0]['evidence'] = {'kind': 'EXACT_QUOTE', 'value': data[1].units[0].exact_text}
    raw, proof = compile_case(data, data[3].leaves[0], record)
    assert projection(data, whole) == projection(data, raw)
    cfg, db = make_config(tmp_path); analyzer = Analyzer(cfg, db)
    def native(result):
        canonical = projection(data, result)
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(canonical))
        return analyzer.analyze_source('synthetic.txt', data[0].piece.source_text, 'deep', adaptive_retry_policy='forbid')
    left, right = native(whole), native(raw)
    assert left == right
    seed = lambda c: {'source_sha256': data[0].source_sha256, 'claim_index': 0,
                       'claim': {k: v for k, v in c.items() if not k.startswith('origin_')}}
    assert deterministic_id('CLM', seed(left.claims[0])) == deterministic_id('CLM', seed(right.claims[0]))
    assert proof['bindings'][0]['binding']['mode'] == 'RAW_SUBSPAN'
    record['claims'][0]['evidence']['value'] = '产能为100台'
    subspan, _ = compile_case(data, data[3].leaves[0], record)
    old['claims'][0]['evidence'].update(selection_mode='RAW_SUBSPAN', selector='产能为100台', occurrence='1')
    expected = v6.compile_result(json.dumps(old), data[2], data[3].leaves[0], data[1], data[0])[0]
    assert subspan == expected  # Arbitrary unique RAW_SUBSPAN is preserved, not enlarged.


def all_families(data, segment):
    catalog = data[1]; raw = empty_canonical(); unit = catalog.units[0]
    raw['claims'] = [canonical_claim(unit.exact_text, unit, related_node_ids=['NODE_A'], related_candidate_names=['青松公司'])]
    event = normal_node('合成事件')
    event.update(primary_type='Event', is_discrete_event=True, event_time='2026-09-15', evidence_excerpt=unit.exact_text)
    raw['node_candidates'] = [normal_node('青松公司'), event]
    raw['claims'][0]['related_candidate_names'].append('合成事件')
    raw['node_matches'] = [{'node_id': 'NODE_A', 'role': 'primary', 'confidence': 0.9, 'reason': '', 'evidence_excerpt': unit.exact_text}]
    raw['relation_candidates'] = [{'from_node_id': 'NODE_A', 'to_node_id': 'NODE_B', 'relation_type': 'related_to',
        'scope': '合成范围', 'confidence': 0.9, 'reason': '', 'supporting_claim_refs': ['C1']}]
    raw['source_references'] = [{'title': '合成来源', 'relation_type': 'references', 'note': '合成引用'}]
    old = v6_record(catalog, segment, raw)
    return new_record(old, catalog), old


@pytest.mark.parametrize('mutation', [None, 'unknown_claim', 'unknown_candidate', 'unsupported_candidate', 'foreign_match', 'foreign_candidate', 'foreign_reference'])
def test_all_reference_families_use_existing_authoritative_validation(mutation):
    data = setup('青松公司于2026-09-15举办合成事件。\n独立的上下文。', budget=SeriesBudget(initial_evidence_refs=1))
    record, old = all_families(data, data[3].leaves[0])
    foreign = {'kind': 'EXACT_QUOTE', 'value': data[1].units[-1].exact_text}
    if mutation == 'unknown_claim': record['relation_candidates'][0]['supporting_claim_refs'] = ['C2']
    elif mutation == 'unknown_candidate': record['claims'][0]['related_candidate_names'] = ['不存在的候选']
    elif mutation == 'unsupported_candidate': record['claims'][0]['related_candidate_names'] = ['合成事件']
    elif mutation == 'foreign_match': record['node_matches'][0]['evidence'] = foreign
    elif mutation == 'foreign_candidate': record['node_candidates'][1]['evidence_properties'][0]['value'] = foreign
    elif mutation == 'foreign_reference': record['source_references'][0]['ownership_anchor'] = intent.unit_anchor(data[1].units[-1])
    original = copy.deepcopy(record)
    if mutation:
        with pytest.raises(ValueError): compile_case(data, data[3].leaves[0], record)
    else:
        result, proof = compile_case(data, data[3].leaves[0], record)
        expected, ownership = v6.compile_result(json.dumps(old), data[2], data[3].leaves[0], data[1], data[0])
        assert result == expected and proof['candidate_ownership'] == ownership
        assert len(projection(data, result)['relation_candidates']) == 1
        assert len(proof['candidate_ownership']['candidates'][1]['supports']) == 2
    assert original == record


def test_fake_tool_response_complete_compiler_path_and_process_replay(tmp_path):
    from series_binding_helpers import ToolResponse
    data = setup('青松公司于2026-09-15举办合成事件。')
    record, _ = all_families(data, data[3].leaves[0])
    payload = intent.request_payload(data[2], data[3], data[3].leaves[0], data[1], data[0])
    calls = []
    def fake_provider(request):
        calls.append(copy.deepcopy(request))
        assert request['tools'][0]['function']['parameters'] == intent.record_schema()
        return ToolResponse(json.dumps(record)).json()
    request = {'messages': [{'role': 'user', 'content': json.dumps(payload)}],
        'tools': [{'type': 'function', 'function': {'name': 'emit_source_analysis', 'strict': True, 'parameters': intent.record_schema()}}]}
    response = fake_provider(request)
    content = response['choices'][0]['message']['tool_calls'][0]['function']['arguments']
    jsonschema.validate(json.loads(content), intent.record_schema())
    result, proof = intent.compile_binding_candidate(content, data[2], data[3], data[3].leaves[0], data[1], data[0])
    envelope = {'text': data[0].piece.source_text, 'response': response, 'request': request,
        'series': asdict(data[2]), 'segment': asdict(data[3].leaves[0]), 'result': asdict(result), 'proof': proof}
    path = tmp_path/'synthetic-review.json'; path.write_text(json.dumps(envelope, ensure_ascii=False), encoding='utf-8')
    immutable = path.read_bytes()
    replay = subprocess.run([sys.executable, '-B', '-c', '''
import json,sys
from pathlib import Path
from test_evidence_intent_prototype import setup
from pro_a import evidence_intent_prototype as intent
from dataclasses import asdict
data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
ctx,catalog,series,plan=setup(data['text'])
assert json.loads(json.dumps(asdict(series)))==data['series']
assert json.loads(json.dumps(asdict(plan.leaves[0])))==data['segment']
content=data['response']['choices'][0]['message']['tool_calls'][0]['function']['arguments']
result,proof=intent.compile_binding_candidate(content,series,plan,plan.leaves[0],catalog,ctx)
assert json.loads(json.dumps(asdict(result)))==data['result']
assert proof==data['proof'] and proof['segment_accepted'] is False
print('OFFLINE_REPLAY_PASS')
''', str(path)], capture_output=True, timeout=60,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join([str(Path(__file__).parent), *sys.path])})
    assert replay.returncode == 0, replay.stderr.decode(errors='replace')
    assert b'OFFLINE_REPLAY_PASS' in replay.stdout and path.read_bytes() == immutable
    assert len(calls) == 1 and not proof['segment_accepted']


def test_frozen_runtime_does_not_accept_or_shape_route_new_prototype(tmp_path):
    from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
    from pro_a.workbench.config import BoundaryError
    from pro_a.workbench.store import Store
    from series_binding_helpers import case
    from test_bounded_extraction_persistence import reserve
    data = setup('青松公司现有产能为100台。')
    record, old = claim_record(data[1], data[3].leaves[0], data[1].units[0])
    value = case(tmp_path); config = value['config']; before = config.knowledge_db.read_bytes()
    ledger = BoundedExtractionStore(config); ledger.create(data[2])
    fence, aid = reserve(ledger, data[3].leaves[0]); assert ledger.record_dispatch(aid, 'worker', fence)
    ledger.record_outcome(aid, 'worker', fence, json.dumps(record).encode(), finish_reason='tool_calls', input_tokens=10, output_tokens=10, total_tokens=20)
    with pytest.raises(BoundaryError, match='INVALID_SEGMENT_RESPONSE'):
        ledger.accept_result(aid, 'worker', fence, data[1], data[0])
    with Store(config).connect() as c:
        assert c.execute('SELECT count(*) FROM bounded_extraction_segment_results').fetchone()[0] == 0
        assert c.execute('SELECT count(*) FROM source_processing_jobs').fetchone()[0] == 0
    assert config.knowledge_db.read_bytes() == before
    assert output.contract()['provider_record_version'] == output.RECORD_VERSION
    with pytest.raises(ValueError):
        output.record_schema(record_version=intent.VERSION)
    with pytest.raises(ValueError):
        compile_case(data, data[3].leaves[0], old)


@pytest.mark.parametrize('intent_value,code', [
    ({'kind': 'EXACT_QUOTE', 'value': '缺失原文'}, 'INTENT_QUOTE_NOT_FOUND'),
    ({'kind': 'EXACT_QUOTE', 'value': '事实甲。\n事实乙。'}, 'INTENT_QUOTE_NOT_IN_SINGLE_UNIT'),
    ({'kind': 'UNIT_ANCHOR', 'value': 'EA_FORGED'}, 'INTENT_UNKNOWN_ANCHOR'),
])
def test_unresolved_location_preserves_original_input(intent_value, code):
    data = setup('事实甲。\n事实乙。')
    record, _ = claim_record(data[1], data[3].leaves[0], data[1].units[0])
    record['claims'][0]['evidence'] = intent_value; original = copy.deepcopy(record)
    with pytest.raises(intent.IntentBindingError, match=code):
        compile_case(data, data[3].leaves[0], record)
    assert record == original
