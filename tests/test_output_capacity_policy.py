"""24k application capacity with frozen 12k history and a 384k risk budget."""
from dataclasses import asdict
import hashlib
import json

import pytest

from pro_a import output_decomposition as output
from pro_a.bounded_extraction import (LEGACY_OUTPUT_SERIES_VERSION, V2_OUTPUT_SERIES_VERSION as OUTPUT_SERIES_VERSION,
    SeriesBudget, SegmentCallAccounting, account_series_calls, create_extraction_series,
    initial_extraction_plan, subdivide_extraction_plan)
from pro_a.config import LLMConfig
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.evidence_binding import identity
from test_output_decomposition import fixture, record, payload
from test_output_decomposition_durability import setup
from test_bounded_extraction_persistence import reserve
from test_whole_piece_compact import payload_for


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('REAL_NETWORK_FORBIDDEN'))


@pytest.mark.parametrize('limit', [23999, 24000, 24001])
def test_exact_configured_and_requested_capacity(monkeypatch, limit):
    monkeypatch.setenv('SYNTHETIC_CAPACITY_KEY', 'synthetic-only')
    cfg = LLMConfig(enabled=True, api_key_env='SYNTHETIC_CAPACITY_KEY', model='deepseek-flash', max_retries=0, max_output_tokens=limit)
    if limit != 24000:
        with pytest.raises(ValueError, match='PROVIDER_CONFIGURATION_MISMATCH'):
            output.OutputBatchProvider(cfg)
    else:
        provider = output.OutputBatchProvider(cfg)
        ctx, catalog, series, plan = fixture(1)
        body = payload(ctx, catalog, series, plan.leaves[0])
        assert body['request']['max_tokens'] == 24000
        for incorrect in (23999, 24001):
            body['request']['max_tokens'] = incorrect
            with pytest.raises(ValueError, match='OUTPUT_PROVIDER_CONFIGURATION_MISMATCH'):
                provider.invoke(body)


def test_insufficient_qualified_provider_capability_fails_closed(monkeypatch):
    monkeypatch.setattr(output.OutputBatchProvider, 'output_capability_tokens', 23999)
    with pytest.raises(ValueError, match='PROVIDER_OUTPUT_CAPABILITY_INSUFFICIENT'):
        output.OutputBatchProvider(LLMConfig(model='deepseek-flash', max_retries=0, max_output_tokens=24000))


def test_current_provider_rejects_frozen_12k_request_before_dispatch(monkeypatch):
    monkeypatch.setenv('SYNTHETIC_CAPACITY_KEY', 'synthetic-only')
    ctx, catalog, fresh, _ = fixture(16)
    old = create_extraction_series(ctx, catalog, fresh.processing_run_id, series_version=LEGACY_OUTPUT_SERIES_VERSION)
    body = payload(ctx, catalog, old, initial_extraction_plan(old).leaves[0])
    provider = output.OutputBatchProvider(LLMConfig(enabled=True, api_key_env='SYNTHETIC_CAPACITY_KEY',
        model='deepseek-flash', max_retries=0, max_output_tokens=24000))
    with pytest.raises(ValueError, match='OUTPUT_PROVIDER_CONFIGURATION_MISMATCH'):
        provider.invoke(body)
    before = output.contract(binding_version=output.LEGACY_BINDING_VERSION)
    after = output.contract(binding_version=output.V3_BINDING_VERSION)
    for field in ('research_semantic_contract', 'claim_linkage_policy', 'system_prompt_sha256',
            'provider_encoding_prompt_sha256', 'tool_schema_sha256', 'prompt_version', 'evidence_binding', 'wire'):
        assert before[field] == after[field]


def test_old_new_same_source_identities_and_midpoint_are_deterministic():
    ctx, catalog, fresh, plan = fixture(16)
    old = create_extraction_series(ctx, catalog, fresh.processing_run_id, series_version=LEGACY_OUTPUT_SERIES_VERSION)
    old_plan = initial_extraction_plan(old)
    again = create_extraction_series(ctx, catalog, fresh.processing_run_id, series_version=OUTPUT_SERIES_VERSION)
    assert fresh == again and plan == initial_extraction_plan(again)
    assert fresh.source_sha256 == old.source_sha256 and fresh.eligible_evidence_refs == old.eligible_evidence_refs
    assert fresh.series_id != old.series_id and plan.leaves[0].segment_id != old_plan.leaves[0].segment_id
    assert old_plan.leaves[0].max_output_tokens == 12000 and plan.leaves[0].max_output_tokens == 24000
    assert fresh.output_budget_identity == 'operation-output-budget-v2' and old.output_budget_identity == 'operation-output-budget-v1'
    assert old.task_policy_identity == fresh.task_policy_identity and fresh.budget.max_cumulative_output_tokens == 384000
    assert asdict(fresh.budget) == {'initial_evidence_refs': 16, 'max_leaf_segments': 16,
        'max_subdivision_depth': 4, 'max_provider_calls': 32, 'max_cumulative_output_tokens': 384000}
    changed = subdivide_extraction_plan(fresh, plan, plan.leaves[0].segment_id)
    assert [len(s.assigned_evidence_refs) for s in changed.leaves] == [8, 8]
    assert all(s.max_output_tokens == 24000 for s in changed.leaves)
    historical = payload(ctx, catalog, old, old_plan.leaves[0])
    assert historical['request']['max_tokens'] == 12000
    assert historical['target']['provider_version'] == output.LEGACY_PROVIDER_VERSION
    assert old_plan == initial_extraction_plan(old)


def test_historical_released_12k_identity_vectors_and_input_restore():
    ctx, catalog, fresh, _ = fixture(16)
    old = create_extraction_series(ctx, catalog, fresh.processing_run_id, series_version=LEGACY_OUTPUT_SERIES_VERSION)
    segment = initial_extraction_plan(old).leaves[0]
    native = payload_for(ctx)
    native.update(user_prompt=ctx.piece.source_text,
        user_prompt_sha256=hashlib.sha256(ctx.piece.source_text.encode()).hexdigest(), initial_plan_sha256='a' * 64)
    frozen = output.piece_input(native, ctx.source_sha256, old.processing_run_id, 1, binding_version=output.LEGACY_BINDING_VERSION)
    body = payload(ctx, catalog, old, segment)
    # Captured from the unchanged released 3c72ae2 runtime, using only synthetic text.
    assert old.series_id == 'SERIES_B391AA8BB26C876EFA74B71902B91A83'
    assert old.series_sha256 == '3df03493968bda73652ce52c1b6252d5d66e55c35aef1f976b0ce3b3e001b758'
    assert segment.segment_id == 'SEGMENT_206B7D99A9DD0C19CF6041AEEDBF9E30'
    assert segment.segment_sha256 == '20e007906872b14bbaa3554b2f1ddc174d364e04c5a46200d9120f1408737167'
    assert identity(frozen) == '1c9c12a588bfeb037cd9bedf42fea0d79d97348a99a6cc85fcc0060ecfa5a3b5'
    assert identity(body) == '591ad9cb4aadb8fc98510c813da76e207105b7f75cbf27c55995a6672cae7b00'
    assert identity(body['request']) == '54b8228b3dc619a2baa304d12f9229830aa0c772ce9bdcaa65906018eb0e8517'
    assert output.restore_input(frozen, ctx.source_sha256, old.processing_run_id, 1)[2] == old
    current = output.piece_input(native, ctx.source_sha256, old.processing_run_id, 1, binding_version=output.V3_BINDING_VERSION)
    assert output.restore_input(current, ctx.source_sha256, old.processing_run_id, 1)[2] == fresh
    assert identity(current) != identity(frozen)
    with pytest.raises(ValueError, match='OUTPUT_INPUT_IDENTITY_MISMATCH'):
        output.restore_input({**frozen, 'binding_version': output.BINDING_VERSION}, ctx.source_sha256, old.processing_run_id, 1)


@pytest.mark.parametrize('count,allowed', [(15, True), (16, True), (17, False)])
def test_cumulative_full_liability_is_independent_of_call_ceiling(count, allowed):
    _, _, series, plan = fixture(16)
    segment = plan.leaves[0]
    calls = tuple(SegmentCallAccounting(segment.segment_id, f'synthetic-attempt-{i}', None,
        None, None, None, None, None, None, None, 'UNKNOWN') for i in range(count))
    if allowed:
        assert account_series_calls(series, plan, calls).output_token_liability == count * 24000
    else:
        with pytest.raises(ValueError, match='SERIES_BUDGET_EXCEEDED'):
            account_series_calls(series, plan, calls)
    with pytest.raises(ValueError, match='INVALID_SERIES_BUDGET'):
        SeriesBudget(max_cumulative_output_tokens=768000)


@pytest.mark.parametrize('tokens,finish,body_kind', [(18000, 'tool_calls', 'valid'),
    (24000, 'length', 'partial'), (13000, 'tool_calls', 'malformed')])
def test_durable_outcomes_accept_more_than_12k_without_parsing_truncation(tmp_path, monkeypatch, tokens, finish, body_kind):
    _, ledger, ctx, catalog, series, plan = setup(tmp_path)
    segment = plan.leaves[0]
    fence, aid = reserve(ledger, segment)
    assert ledger.record_dispatch(aid, 'worker', fence)
    raw = json.dumps(record(ctx, catalog, series, segment)).encode() if body_kind == 'valid' else b'{"claims":['
    if finish == 'length':
        monkeypatch.setattr(output, 'record_to_result', lambda *a, **k: pytest.fail('PARTIAL_RECORD_PARSED'))
    outcome = ledger.record_outcome(aid, 'worker', fence, raw, finish_reason=finish,
        input_tokens=100, output_tokens=tokens, total_tokens=100 + tokens, cached_input_tokens=0)
    if body_kind == 'valid':
        assert ledger.accept_result(aid, 'worker', fence, catalog, ctx)
        assert outcome['external_outcome'] == 'SUCCEEDED'
    else:
        with pytest.raises((ValueError, BoundaryError)):
            ledger.accept_result(aid, 'worker', fence, catalog, ctx)
        assert outcome['external_outcome'] == ('TRUNCATED' if finish == 'length' else 'SUCCEEDED')
        with ledger._connection() as connection:
            assert not connection.execute('SELECT 1 FROM bounded_extraction_segment_results WHERE attempt_id=?', (aid,)).fetchone()
        if body_kind == 'malformed':
            from pro_a.workbench.extraction_retry import _json_syntax_diagnostic
            assert _json_syntax_diagnostic(raw)['failure_class'] == 'PROVIDER_MALFORMED_STRUCTURED_OUTPUT'
    assert ledger.read(series.series_id)[3].output_token_liability == tokens


@pytest.mark.parametrize('budget,allowed', [(72000, True), (48000, False)])
def test_parent_liability_and_both_child_reservations(tmp_path, budget, allowed):
    config, _, ctx, catalog, _, _ = setup(tmp_path)
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_CAPACITY_BUDGET',
        SeriesBudget(max_cumulative_output_tokens=budget), series_version=OUTPUT_SERIES_VERSION)
    ledger = BoundedExtractionStore(config)
    ledger.create(series)
    parent = initial_extraction_plan(series).leaves[0]
    fence, aid = reserve(ledger, parent)
    ledger.record_dispatch(aid, 'worker', fence)
    ledger.record_outcome(aid, 'worker', fence, b'{', finish_reason='length', output_tokens=24000)
    version = ledger.read(series.series_id)[2]['frontier_version']
    if allowed:
        children = ledger.subdivide_after_truncation(parent.segment_id, 'worker', fence, expected_frontier_version=version)
        assert [len(s.assigned_evidence_refs) for s in children] == [8, 8]
        for child in children:
            reserve(ledger, child)
        assert ledger.read(series.series_id)[2]['output_liability'] == 72000
    else:
        with pytest.raises(BoundaryError, match='EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY'):
            ledger.subdivide_after_truncation(parent.segment_id, 'worker', fence, expected_frontier_version=version)
    assert ledger.read(series.series_id)[3].output_token_liability == (72000 if allowed else 24000)


def test_persisted_full_liability_reservations_at_360k_384k_and_overflow(tmp_path):
    config, _, ctx, catalog, _, _ = setup(tmp_path)
    series = create_extraction_series(ctx, catalog, 'SYNTHETIC_RESERVATION_BOUNDARY',
        SeriesBudget(initial_evidence_refs=2), series_version=OUTPUT_SERIES_VERSION)
    ledger = BoundedExtractionStore(config)
    ledger.create(series)
    children = []
    for parent in initial_extraction_plan(series).leaves:
        fence, aid = reserve(ledger, parent)
        ledger.record_dispatch(aid, 'worker', fence)
        ledger.record_outcome(aid, 'worker', fence, b'{', finish_reason='length', output_tokens=24000)
        version = ledger.read(series.series_id)[2]['frontier_version']
        children.extend(ledger.subdivide_after_truncation(parent.segment_id, 'worker', fence, expected_frontier_version=version))
    for child in children[:7]:
        reserve(ledger, child)
    assert ledger.read(series.series_id)[2]['output_liability'] == 360000
    reserve(ledger, children[7])
    before = ledger.read(series.series_id)[3]
    assert before.output_token_liability == 384000 and before.provider_call_count == 16
    with pytest.raises(BoundaryError, match='SERIES_BUDGET_EXCEEDED'):
        reserve(ledger, children[8])
    assert ledger.read(series.series_id)[3] == before
