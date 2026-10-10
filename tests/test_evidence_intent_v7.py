"""Span parity and explicit, unproved semantic dependencies; synthetic only."""
import copy
from dataclasses import asdict
import json

import jsonschema
import pytest

from pro_a import output_provider_record_v7 as intent, output_provider_record_v6 as v6
from pro_a.analyzer import canonicalize_text
from pro_a.bounded_extraction import SeriesBudget, subdivide_extraction_plan
from pro_a.evidence_binding import resolve_evidence_binding_v2, EvidenceBindingError
from pro_a import source_analysis_provider_record as lexical
from test_evidence_intent_prototype import setup, v6_record, projection, all_families, no_provider
from test_source_analysis_wire import canonical_claim, empty_canonical


def new_record(value, catalog):
    """Inverse for newly constructed synthetic records only, never historical Raw."""
    units = {u.evidence_ref: u for u in catalog.units}
    def transform(obj):
        if type(obj) is dict:
            if set(obj) == {'evidence_ref', 'selection_mode', 'selector', 'occurrence'}:
                return intent.unit_selection(units[obj['evidence_ref']], obj['selection_mode'], obj['selector'], obj['occurrence'])
            return {k: transform(v) for k, v in obj.items()}
        if type(obj) is list:
            return [transform(v) for v in obj]
        return obj
    record = transform(copy.deepcopy(value))
    record['protocol_version'] = intent.VERSION
    for claim in record['claims']:
        claim['research_review'] = {'context_dependencies': [], 'review_reasons': []}
    record['evidence_acknowledgements'] = [{'anchor_id': intent.unit_anchor(units[a['evidence_ref']])} for a in value['evidence_acknowledgements']]
    for reference in record['source_references']:
        reference['ownership_anchor'] = intent.unit_anchor(units[reference.pop('ownership_evidence_ref')])
    return record


def claim_record(data, segment, unit, statement=None):
    canonical = empty_canonical()
    canonical['claims'] = [canonical_claim(statement or unit.exact_text, unit)]
    return v6_record(data[1], segment, canonical)


def compile_case(data, segment, record):
    return intent.compile_result(json.dumps(record, ensure_ascii=False), data[2], segment, data[1], data[0], plan=data[3])


@pytest.mark.parametrize('text', ['banana', 'x x', 'Ａ A Ａ', 'Ⅳ IV Ⅳ', r'A\&B A&B A\&B', 'Alpha\t  beta'])
def test_complete_selection_mapping_raw_normalized_occurrences_and_wire_identity(text):
    # Enumerate every substring/occurrence of these small raw and normalized units.
    # The general compiler proof is the direct, lossless mapping to v2, not an
    # assertion that this finite corpus enumerates every possible Source text.
    data = setup(text); unit = data[1].units[0]; segment = data[3].leaves[0]
    selections = [('WHOLE_UNIT', '', '1')]
    for mode, source in [('RAW_SUBSPAN', unit.exact_text), ('NORMALIZED_SUBSPAN', canonicalize_text(unit.exact_text))]:
        quotes = {source[a:b] for a in range(len(source)) for b in range(a + 1, len(source) + 1)}
        for quote in sorted(quotes):
            for occurrence in range(1, len(source) + 1):
                selection = {'evidence_ref': unit.evidence_ref, 'selection_mode': mode, 'selector': quote, 'occurrence': str(occurrence)}
                try:
                    resolve_evidence_binding_v2(lexical.selection(selection), data[1], data[0])
                except EvidenceBindingError:
                    break
                selections.append((mode, quote, str(occurrence)))
    for mode, quote, occurrence in selections:
        old = claim_record(data, segment, unit)
        old['claims'][0]['evidence'].update(selection_mode=mode, selector=quote, occurrence=occurrence)
        old['claims'][0]['evidence_pointer'] = 'arbitrary preserved native pointer'
        record = new_record(old, data[1]); before = copy.deepcopy(record)
        selection, bound = intent.resolve_intent(record['claims'][0]['evidence'], data[1], data[0], evidence_pointer=old['claims'][0]['evidence_pointer'])
        expected = resolve_evidence_binding_v2({**lexical.selection(old['claims'][0]['evidence']), 'evidence_pointer': old['claims'][0]['evidence_pointer']}, data[1], data[0])
        assert selection == old['claims'][0]['evidence'] and bound == expected
        result, review = compile_case(data, segment, record)
        reference = v6.compile_result(json.dumps(old), data[2], segment, data[1], data[0])[0]
        assert result == reference and projection(data, result) == projection(data, reference)
        assert review['bindings'][0]['binding'] == asdict(expected)
        assert record == before
    assert len(selections) > 2


def test_repeated_across_units_unique_quote_and_no_missing_occurrence_guess():
    data = setup('banana.\nbanana.\nUnique complete fact 42.')
    units = data[1].units
    positions = [intent.resolve_intent(intent.unit_selection(u, 'RAW_SUBSPAN', 'ana', str(i)), data[1], data[0])[1].source_start
                 for u in units[:2] for i in (1, 2)]
    assert len(set(positions)) == 4
    exact = {'kind': 'EXACT_QUOTE', 'unit_anchor': '', 'selection_mode': 'RAW_SUBSPAN', 'quote': 'ana', 'occurrence': '1'}
    with pytest.raises(intent.IntentBindingError, match='AMBIGUOUS'):
        intent.resolve_intent(exact, data[1], data[0])
    exact['quote'] = units[-1].exact_text
    assert intent.resolve_intent(exact, data[1], data[0])[1].evidence_ref == units[-1].evidence_ref
    for value in ('', '0', '01', '-1', '1.0', '99'):
        with pytest.raises(ValueError):
            intent.resolve_intent(intent.unit_selection(units[0], 'RAW_SUBSPAN', 'ana', value), data[1], data[0])
    with pytest.raises(ValueError):
        intent.resolve_intent(intent.unit_selection(units[0], 'NORMALIZED_SUBSPAN', 'ANA', '1'), data[1], data[0])


@pytest.mark.parametrize('boundary', ['same_segment', 'unit16_17', 'subdivision8_9', 'claim14_unit18'])
def test_context_dependencies_do_not_route_or_authorize_semantics(boundary):
    count = {'same_segment': 0, 'unit16_17': 15, 'subdivision8_9': 7, 'claim14_unit18': 16}[boundary]
    question = '青松公司的当前产能是多少？'
    answer = '青松公司现有产能为100台。' if boundary == 'claim14_unit18' else '该公司现有产能为100台。'
    data = setup('\n'.join([*[f'合成编号{i}。' for i in range(count)], question, answer,
                           *([f'合成尾部{i}。' for i in range(7)] if boundary == 'subdivision8_9' else [])]))
    if boundary == 'subdivision8_9':
        data = *data[:3], subdivide_extraction_plan(data[2], data[3], data[3].leaves[0].segment_id)
    q, a = data[1].units[count:count + 2]
    owner = next(s for s in data[3].leaves if a.evidence_ref in s.assigned_evidence_refs)
    old = claim_record(data, owner, a, '青松公司现有产能为100台。')
    record = new_record(old, data[1])
    if boundary != 'claim14_unit18':
        record['claims'][0]['research_review']['context_dependencies'] = [{
            'evidence': intent.unit_selection(q), 'relationship': 'ANAPHORA', 'reason': '模型声明的主体前指，需要人工审核。'}]
    result, review = compile_case(data, owner, record)
    assert result == v6.compile_result(json.dumps(old), data[2], owner, data[1], data[0])[0]
    assert review['claims'][0]['statuses'][-1] == 'SEMANTIC_REVIEW_REQUIRED'
    assert review['canonical_permission'] is False and review['semantic_authorization'] == 'NOT_ESTABLISHED'
    regions = intent.source_regions(data[1], data[0], owner)
    assert ''.join(r['text'] for r in regions) == data[0].piece.source_text
    assert next(r for r in regions if r.get('anchor_id') == intent.unit_anchor(q))['role'] == ('ASSIGNED' if q.evidence_ref in owner.assigned_evidence_refs else 'CONTEXT')
    if q.evidence_ref not in owner.assigned_evidence_refs:
        wrong = next(s for s in data[3].leaves if q.evidence_ref in s.assigned_evidence_refs)
        with pytest.raises(intent.IntentBindingError, match='OUTSIDE_ASSIGNED') as error:
            compile_case(data, wrong, record)
        assert error.value.details['status'] == 'UNRESOLVED_EVIDENCE' and error.value.details['scheduled'] is False


@pytest.mark.parametrize('background,answer,statement,relationship', [
    ('以下产能数据仅指青松公司。白杨公司与本次产能数据无关。', '该公司现有产能为100台。', '白杨公司现有产能为100台。', 'ANAPHORA'),
    ('青松公司和白杨公司均参加了会议。', '该公司现有产能为100台。', '青松公司现有产能为100台。', 'ANAPHORA'),
    ('前文合成条件。', '青松公司现有产能为100台。', '青松公司现有产能为900台。', 'BACKGROUND'),
    ('合成前文业务语境。', '这一领域将继续增长。', '青松公司的业务将继续增长。', 'ANAPHORA'),
    ('2026年合成经营计划。', '次年计划增长。', '2027年计划增长。', 'TEMPORAL_INHERITANCE'),
    ('管理层在合成会议上发言。', '若需求恢复，预计产能可能增长。', '产能已经增长。', 'CONDITION'),
    ('合成专家甲发言。', '我们预计青松公司有望增长。', '青松公司有望增长。', 'ATTRIBUTION'),
    ('合成关系背景。', '青松公司不依赖白杨公司。', '青松公司依赖白杨公司。', 'BACKGROUND'),
])
def test_location_pass_never_means_truth_confirmation(background, answer, statement, relationship):
    data = setup(background + '\n' + answer); owner = data[3].leaves[0]
    old = claim_record(data, owner, data[1].units[-1], statement)
    record = new_record(old, data[1])
    record['claims'][0]['research_review'] = {'context_dependencies': [{
        'evidence': intent.unit_selection(data[1].units[0]), 'relationship': relationship, 'reason': '合成待审依赖。'}],
        'review_reasons': ['主体、时间、数值、条件或归因未获得确定性语义授权。']}
    result, review = compile_case(data, owner, record)
    assert projection(data, result)['claims'][0]['statement'] == statement  # No automatic correction or rejection by a fake truth oracle.
    claim = review['claims'][0]
    assert claim['statuses'] == ['LOCATION_VERIFIED', 'CONTEXT_DEPENDENCY_DECLARED', 'SEMANTIC_REVIEW_REQUIRED']
    assert claim['semantic_truth'] == 'NOT_ESTABLISHED'
    assert claim['context_dependencies'][0]['relationship_authorization'] == 'NOT_ESTABLISHED'
    assert not review['canonical_permission']
    record['claims'][0]['research_review']['context_dependencies'][0]['evidence']['unit_anchor'] = 'EA_FORGED'
    with pytest.raises(ValueError):
        compile_case(data, owner, record)


def test_all_research_fields_references_strict_schema_and_native_claim_identity(tmp_path):
    from pro_a.analyzer import Analyzer
    from pro_a.operational_ingestion import deterministic_id
    from stability_helpers import make_config
    from types import SimpleNamespace
    data = setup('青松公司于2026-09-15举办合成事件。')
    _, old = all_families(data, data[3].leaves[0]); record = new_record(old, data[1])
    jsonschema.Draft202012Validator.check_schema(intent.record_schema())
    jsonschema.validate(record, intent.record_schema())
    assert 'anyOf' not in json.dumps(intent.record_schema())
    result, review = compile_case(data, data[3].leaves[0], record)
    reference, ownership = v6.compile_result(json.dumps(old), data[2], data[3].leaves[0], data[1], data[0])
    assert result == reference and review['candidate_ownership'] == ownership
    cfg, db = make_config(tmp_path); analyzer = Analyzer(cfg, db)
    def native(result):
        analyzer.llm = SimpleNamespace(available=True, json=lambda *a: copy.deepcopy(projection(data, result)))
        return analyzer.analyze_source('synthetic.txt', data[0].piece.source_text, 'deep', adaptive_retry_policy='forbid')
    left, right = native(result), native(reference)
    assert left == right
    seed = lambda c: {'source_sha256': data[0].source_sha256, 'claim_index': 0,
                      'claim': {k: v for k, v in c.items() if not k.startswith('origin_')}}
    assert deterministic_id('CLM', seed(left.claims[0])) == deterministic_id('CLM', seed(right.claims[0]))
    for family, field, value in [('relation_candidates', 'supporting_claim_refs', ['C2']), ('claims', 'related_candidate_names', ['不存在的候选'])]:
        invalid = copy.deepcopy(record); invalid[family][0][field] = value
        with pytest.raises(ValueError):
            compile_case(data, data[3].leaves[0], invalid)


def test_review_attachment_publication_crash_and_same_raw_recovery(tmp_path, monkeypatch):
    from pro_a.bounded_extraction import create_extraction_series, initial_extraction_plan, EVIDENCE_INTENT_OUTPUT_SERIES_VERSION
    from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
    from pro_a.workbench.config import BoundaryError
    from series_binding_helpers import case, rows
    from test_bounded_extraction_persistence import reserve
    value = case(tmp_path); production = value['config'].knowledge_db.read_bytes()
    ctx, catalog, _, _ = setup('青松公司现有产能为100台。')
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_ATTACHMENT_RUN', series_version=EVIDENCE_INTENT_OUTPUT_SERIES_VERSION)
    plan = initial_extraction_plan(series); segment = plan.leaves[0]
    data = ctx, catalog, series, plan
    record = new_record(claim_record(data, segment, catalog.units[0]), catalog)
    ledger = BoundedExtractionStore(value['config']); ledger.create(series)
    fence, aid = reserve(ledger, segment)
    ledger.record_dispatch(aid, 'worker', fence)
    ledger.record_outcome(aid, 'worker', fence, json.dumps(record).encode(), finish_reason='tool_calls', input_tokens=100, output_tokens=50, total_tokens=150)
    before_calls = rows(value, 'bounded_extraction_attempts')
    original = ledger._artifact
    def crash(series_id, name, content):
        published = original(series_id, name, content)
        if name.endswith('.review.json'):
            raise RuntimeError('SYNTHETIC_ATTACHMENT_PUBLICATION_CRASH')
        return published
    monkeypatch.setattr(ledger, '_artifact', crash)
    with pytest.raises(RuntimeError, match='PUBLICATION_CRASH'):
        ledger.accept_result(aid, 'worker', fence, catalog, ctx)
    assert not rows(value, 'bounded_extraction_segment_results')
    attachment = ledger._path(series.series_id, segment.segment_id+'.review.json')
    immutable = attachment.read_bytes()
    fresh = BoundedExtractionStore(value['config'])
    accepted = fresh.accept_result(aid, 'worker', fence, catalog, ctx)
    assert attachment.read_bytes() == immutable and rows(value, 'bounded_extraction_attempts') == before_calls
    assert fresh.read(series.series_id)[3].provider_call_count == 1
    result, review = compile_case(data, segment, record)
    assert accepted['result_sha256'] == result.result_sha256 and json.loads(immutable) == review
    assert value['config'].knowledge_db.read_bytes() == production and not rows(value, 'source_processing_jobs')
    # An accepted extraction never trusts a missing/changed independent attachment.
    attachment.write_bytes(b'{}')
    with pytest.raises(BoundaryError, match='ARTIFACT_HASH_MISMATCH'):
        BoundedExtractionStore(value['config']).read(series.series_id)
