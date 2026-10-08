"""Synthetic only: original evidence survives the unchanged Native merge."""
import copy
import hashlib
import json

import pytest

from pro_a.analyzer import Analyzer, InitialExtractionPlan, PlannedExtractionPiece
from pro_a.bounded_extraction import create_extraction_series, create_segment_wire_result, EvidenceDisposition, initial_extraction_plan
from pro_a.claim_observations import (
    ADMITTED, BLOCKED, ObservationError, bind_semantic_inputs, build_native_projection,
    build_observation_ledger, guard_semantic_inputs, private_review_artifact,
    semantic_capacity_preflight,
)
from pro_a.evidence_binding import identity
from pro_a.operational_ingestion import deterministic_id
from pro_a.pipeline import build_claim_record
from pro_a.semantic_decomposition import build_semantic_claim_inputs, SemanticDecompositionError
from pro_a.source_analysis_wire import build_source_evidence_catalog
from pro_a.workbench.bounded_source_analysis import BoundedExtractionReplay
from stability_helpers import make_config
from test_bounded_extraction import result
from test_source_analysis_wire import context


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))
    monkeypatch.setattr('pro_a.llm.ChatLLM.json', lambda *a, **k: pytest.fail('PROVIDER_FORBIDDEN'))


def fixture(count):
    ctx = context('\n'.join(f'Item{i:03d}={i+1:03d}.' for i in range(count)))
    catalog = build_source_evidence_catalog(ctx)
    series = create_extraction_series(ctx, catalog, 'RUN_SYNTHETIC')
    return ctx, catalog, series, initial_extraction_plan(series)


def case(tmp_path, *, variant=None, count=3):
    ctx, catalog, series, plan = fixture(count)
    results = []
    for leaf in plan.leaves:
        original = result(ctx, catalog, series, leaf)
        wire = json.loads(original.wire_json)
        if variant is not None and not results:
            wire['claims'][1] = copy.deepcopy(wire['claims'][0])
            wire['claims'][1].update(variant)
        claimed = {c['evidence_ref'] for c in wire['claims']}
        dispositions = tuple(EvidenceDisposition(r, 'CLAIMED' if r in claimed else 'NO_INDEPENDENT_CLAIM') for r in leaf.assigned_evidence_refs)
        results.append(create_segment_wire_result(series, leaf, wire, dispositions, catalog, ctx))
    ledger = build_observation_ledger('SRC_SYNTHETIC', series, plan, tuple(results), catalog, ctx)
    raw = {'source_metadata': json.loads(results[0].wire_json)['source_metadata'],
        'node_matches': [], 'node_candidates': [], 'source_references': [], 'relation_candidates': [],
        'claims': [{**o['expanded_claim'], 'claim_ref': f'C{o["aggregate_ordinal"]}'} for o in ledger['observations']]}
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    prompt = 'SYNTHETIC_FROZEN_PROMPT'
    key = hashlib.sha256(prompt.encode()).hexdigest()
    planned = PlannedExtractionPiece(ctx.piece, 0, len(ctx.piece.source_text), (), (), prompt)
    frozen = InitialExtractionPlan(4000, 0, identity([]), (planned,), {}, identity({'synthetic': True}))
    analyzer.plan_initial_extraction = lambda *a, **k: frozen
    analyzer.llm = BoundedExtractionReplay(cfg.llm, {key: raw}, {key: {}})
    analysis = analyzer.analyze_source('synthetic.txt', ctx.piece.source_text, 'deep', adaptive_retry_policy='forbid')
    projection = build_native_projection(ledger, analysis.claims)
    records, quote, evidence = [], [], []
    for index, claim in enumerate(analysis.claims):
        claim_id = deterministic_id('CLM', {'source_sha256': ctx.source_sha256, 'claim_index': index,
            'claim': {k: v for k, v in claim.items() if not k.startswith('origin_')}})
        record = build_claim_record(claim_id, 'SRC_SYNTHETIC', claim, '', ctx.piece.source_text,
            ingestion_time='2026-01-01T00:00:00Z', created_at='2026-01-01T00:00:00Z')
        record['claim_index'] = index
        records.append(record)
        evidence.append({'claim_id': claim_id, 'original_evidence_excerpt': record['evidence_excerpt']})
        quote.append({'claim_id': claim_id, 'resolved_locator': {'locator': 'TEXT'},
            'evidence_contract': {'canonical_ready_evidence': record['evidence_excerpt']}})
    inputs = build_semantic_claim_inputs(bundle={'claims': records}, evidence_draft={'claims': evidence}, quote_fidelity={'claims': quote})
    admission = bind_semantic_inputs(ledger, projection, records, inputs)
    return ledger, projection, admission, inputs, (ctx, catalog, series, plan, results)


def test_exact_duplicates_preserve_independent_observation_ids(tmp_path):
    ledger, projection, admission, inputs, values = case(tmp_path, variant={})
    assert len(ledger['observations']) == 3 and len(projection['groups']) == 2
    assert len({o['observation_id'] for o in ledger['observations']}) == 3
    assert projection['groups'][0]['classification'] == 'EXACT_DUPLICATE'
    assert projection['groups'][0]['semantic_admission'] == ADMITTED
    assert not projection['native_projection_authoritative']
    guard_semantic_inputs(ledger, projection, admission, inputs)
    ctx, catalog, series, plan, results = values
    assert ledger == build_observation_ledger('SRC_SYNTHETIC', series, plan, tuple(reversed(results)), catalog, ctx)
    assert identity(ledger) == identity(json.loads(json.dumps(ledger)))
    review = private_review_artifact(ledger, projection)
    stored = json.loads(json.dumps(review))
    assert private_review_artifact(stored['ledger'], stored['projection']) == review


@pytest.mark.parametrize('field,value', [('attributed_to', 'Another source'), ('fact_time', '2026'),
    ('scope', 'Another scope'), ('nature', 'ai_inference'), ('status', 'disputed'),
    ('novelty_level', 'N1'), ('structured', {'quantity': 17}), ('confidence', 0.5), ('assumption', 'Conditional')])
def test_material_differences_block_full_set_but_normal_claim_preflights(tmp_path, field, value):
    ledger, projection, admission, inputs, _ = case(tmp_path, variant={field: value})
    group = projection['groups'][0]
    assert group['classification'] == 'NON_EQUIVALENT_OBSERVATIONS'
    assert field in group['differing_fields'] and group['semantic_admission'] == BLOCKED
    with pytest.raises(ObservationError, match=BLOCKED):
        guard_semantic_inputs(ledger, projection, admission, inputs)
    guard_semantic_inputs(ledger, projection, admission, inputs[1:])
    report = semantic_capacity_preflight(ledger, projection, admission, input_token_budget=50000, extraction_jobs=5)
    assert report['eligible_parent_claims'] == 1 and report['blocked_parent_claims'] == 1
    assert report['semantic_batch_count'] == 1 and report['projected_total_logical_jobs'] == 6
    review = private_review_artifact(ledger, projection)
    assert review['ledger'] == ledger and review['projection'] == projection and not review['decisions_applied']


def test_same_assertion_different_evidence_requires_review(tmp_path):
    ctx, catalog, _, _ = fixture(3)
    second = catalog.units[1]
    ledger, projection, admission, inputs, _ = case(tmp_path, variant={'evidence_ref': second.evidence_ref})
    assert projection['groups'][0]['classification'] == 'SAME_ASSERTION_MULTIPLE_EVIDENCE'
    with pytest.raises(ObservationError, match=BLOCKED):
        guard_semantic_inputs(ledger, projection, admission, inputs)
    assert ledger['observations'][0]['evidence'] != ledger['observations'][1]['evidence']


@pytest.mark.parametrize('fault', ['missing_ref', 'duplicate_ref', 'foreign_ref', 'missing_claim', 'wrong_statement'])
def test_projection_mapping_never_guesses(tmp_path, fault):
    ledger, projection, _, _, _ = case(tmp_path, variant={})
    claims = [copy.deepcopy(g['native_claim']) for g in projection['groups']]
    if fault == 'missing_ref': claims[0].pop('_relation_claim_refs')
    if fault == 'duplicate_ref': claims[0]['_relation_claim_refs'].append('C1')
    if fault == 'foreign_ref': claims[0]['_relation_claim_refs'][0] = 'C99'
    if fault == 'missing_claim': claims.pop()
    if fault == 'wrong_statement': claims[0]['statement'] += ' guessed'
    with pytest.raises(ObservationError, match='STOP_PROJECTION_MAPPING_AMBIGUOUS'):
        build_native_projection(ledger, claims)


def test_resealed_admission_flags_cannot_override_blocked_group(tmp_path):
    ledger, projection, admission, inputs, _ = case(tmp_path, variant={'scope': 'Changed'})
    admission['bindings'][0]['semantic_admission'] = ADMITTED
    admission['identity'] = identity({k: v for k, v in admission.items() if k != 'identity'})
    with pytest.raises(ObservationError, match='SEMANTIC_OBSERVATION_INPUT_MISMATCH'):
        guard_semantic_inputs(ledger, projection, admission, inputs)


@pytest.mark.parametrize('fault', ['ledger', 'projection', 'payload', 'duplicate_input', 'foreign_input'])
def test_identity_and_input_tampering_rejected(tmp_path, fault):
    ledger, projection, admission, inputs, _ = case(tmp_path)
    if fault == 'ledger': ledger['observations'][0]['claim']['scope'] = 'Changed'
    if fault == 'projection': projection['groups'][0]['observation_ids'] = []
    if fault == 'payload': inputs[0]['evidence_units'] = []
    if fault == 'duplicate_input': inputs.append(inputs[0])
    if fault == 'foreign_input': inputs[0]['claim_id'] = 'FOREIGN'
    with pytest.raises(ObservationError):
        guard_semantic_inputs(ledger, projection, admission, inputs)


@pytest.mark.parametrize('count,batches,within', [(99,13,True),(100,13,True),(101,13,True),(146,19,True),(208,26,True),(209,27,False)])
def test_actual_native_unique_population_and_existing_semantic_capacity(tmp_path, count, batches, within):
    ledger, projection, admission, inputs, _ = case(tmp_path, count=count)
    assert len(ledger['observations']) == len(projection['groups']) == len(inputs) == count
    report = semantic_capacity_preflight(ledger, projection, admission, input_token_budget=50000, extraction_jobs=5)
    assert report['semantic_batch_count'] == batches
    assert (report['job_budget_status'] == 'WITHIN_BUDGET') == within
    assert report['all_observations_admitted']


def test_token_budget_fails_closed(tmp_path):
    ledger, projection, admission, _, _ = case(tmp_path)
    with pytest.raises(SemanticDecompositionError, match='SEMANTIC_PARENT_TOKEN_BUDGET_EXCEEDED'):
        semantic_capacity_preflight(ledger, projection, admission, input_token_budget=1, extraction_jobs=5)
