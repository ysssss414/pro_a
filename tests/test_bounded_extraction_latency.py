"""Latency durability, conservative safety and immutable outcome observations."""
import json

import pytest

from pro_a.evidence_binding import identity
from pro_a.workbench import bounded_extraction_store as module
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from test_bounded_extraction_persistence import setup, no_network, body, reserve, rows
from test_bounded_extraction_recovery import race, inject


@pytest.fixture
def calls(monkeypatch):
    captured = []
    original = module.account_series_calls
    def capture(series, plan, values):
        captured[:] = values
        return original(series, plan, values)
    monkeypatch.setattr(module, "account_series_calls", capture)
    return captured


@pytest.mark.parametrize("latency", [0, -0.0, 123, 123.456, None])
def test_latency_round_trip_identity_and_fresh_accounting(setup, calls, latency):
    config, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    fence, aid = reserve(ledger, segment)
    ledger.record_dispatch(aid, "worker", fence)
    raw, _ = body(ctx, catalog, series, segment)
    outcome = ledger.record_outcome(aid, "worker", fence, raw, finish_reason="stop", output_tokens=20, latency_ms=latency)
    envelope = json.loads(ledger._path(series.series_id, aid + ".raw.json").read_bytes())
    assert envelope["latency_ms"] == latency
    assert type(envelope["latency_ms"]) is type(latency)
    digest = envelope.pop("envelope_sha256")
    assert digest == identity(envelope)
    assert digest != identity({**envelope, "latency_ms": 1})
    with Store(config).connect() as c:
        stored = dict(c.execute("SELECT * FROM bounded_extraction_outcomes").fetchone())
    assert stored == outcome and stored["latency_ms"] == latency
    digest = stored.pop("record_sha256")
    assert digest == identity(stored)
    assert digest != identity({**stored, "latency_ms": 1.0})
    ledger.accept_result(aid, "worker", fence, catalog, ctx)
    accounting = BoundedExtractionStore(config).read(series.series_id)[3]
    assert len(calls) == 1 and calls[0].latency_ms == latency
    assert accounting.latency_ms == latency and accounting.output_token_liability == 20


@pytest.mark.parametrize("latency", [-1, True, float("nan"), float("inf"), -float("inf"), "123.456"])
def test_invalid_latency_rejected_before_artifact_or_outcome(setup, latency):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    before = rows(config)
    with pytest.raises(BoundaryError, match="^INVALID_CALL_LATENCY$"):
        ledger.record_outcome(aid, "worker", fence, body(ctx, catalog, series, plan.leaves[0])[0], latency_ms=latency)
    assert rows(config) == before
    assert not ledger._path(series.series_id, aid + ".raw.json").exists()
    with pytest.raises(BoundaryError, match="DURABLE_OUTCOME_REQUIRED"):
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    assert rows(config) == before
    accounting = BoundedExtractionStore(config).read(series.series_id)[3]
    assert accounting.latency_ms is None and accounting.output_token_liability == 12000
    assert not ledger.record_dispatch(aid, "worker", fence)


@pytest.mark.parametrize("second_latency", [0, 7.25, None])
def test_multiple_calls_sum_only_when_all_known(setup, calls, second_latency):
    config, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    fence, aid = reserve(ledger, segment)
    ledger.record_dispatch(aid, "worker", fence)
    ledger.record_outcome(aid, "worker", fence, b"invalid synthetic JSON", finish_reason="stop", output_tokens=20, latency_ms=12.5)
    with pytest.raises(BoundaryError, match="INVALID_SEGMENT_RESPONSE"):
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    _, aid2 = reserve(ledger, segment, number=2, fence=fence)
    ledger.record_dispatch(aid2, "worker", fence)
    ledger.record_outcome(aid2, "worker", fence, body(ctx, catalog, series, segment)[0], finish_reason="stop", output_tokens=30, latency_ms=second_latency)
    ledger.accept_result(aid2, "worker", fence, catalog, ctx)
    accounting = BoundedExtractionStore(config).read(series.series_id)[3]
    assert [c.latency_ms for c in calls] == [12.5, second_latency]
    assert accounting.latency_ms == (None if second_latency is None else 12.5 + second_latency)
    assert accounting.provider_call_count == 2 and accounting.output_token_liability == 50


@pytest.mark.parametrize("latency", [123.456, None])
def test_unknown_external_outcome_latency_does_not_release_liability(setup, calls, latency):
    config, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    fence, aid = reserve(ledger, segment)
    ledger.record_dispatch(aid, "worker", fence)
    outcome = ledger.record_outcome(aid, "worker", fence, b"synthetic unknown", http_status=None, output_tokens=20, latency_ms=latency)
    assert outcome["external_outcome"] == "UNKNOWN" and outcome["latency_ms"] == latency
    with pytest.raises(BoundaryError, match="RAW_OUTCOME_NOT_ACCEPTABLE"):
        ledger.reconcile_attempt(aid, "worker", fence, catalog, ctx)
    accounting = BoundedExtractionStore(config).read(series.series_id)[3]
    assert calls[0].latency_ms == latency and accounting.latency_ms == latency
    assert accounting.output_token_liability == 12000 and calls[0].outcome == "UNKNOWN"
    assert ledger.read(series.series_id)[2]["state"] == "RECOVERY_REQUIRED"
    assert not ledger.record_dispatch(aid, "worker", fence)
    with pytest.raises(BoundaryError, match="SEGMENT_NOT_DISPATCHABLE"):
        reserve(ledger, segment, number=2, fence=fence)


def test_invalid_usage_keeps_valid_latency_and_private_usage(setup, calls):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    outcome = ledger.record_outcome(aid, "worker", fence, b"synthetic", output_tokens=12001, latency_ms=123.456)
    assert outcome["classification"] == "INVALID_USAGE" and outcome["latency_ms"] == 123.456
    envelope = json.loads(ledger._path(series.series_id, aid + ".raw.json").read_bytes())
    assert envelope["output_tokens"] == 12001 and envelope["latency_ms"] == 123.456
    accounting = BoundedExtractionStore(config).read(series.series_id)[3]
    assert calls[0].latency_ms == accounting.latency_ms == 123.456
    assert accounting.output_token_liability == 12000
    with pytest.raises(BoundaryError, match="RAW_OUTCOME_NOT_ACCEPTABLE"):
        ledger.accept_result(aid, "worker", fence, catalog, ctx)


@pytest.mark.parametrize("window", ["raw_artifact_durable", "outcome_durable", "result_accepted"])
def test_latency_crash_c_d_e_segment_accounting(setup, calls, monkeypatch, window):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    inject(monkeypatch, window)
    with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
        ledger.record_outcome(aid, "worker", fence, body(ctx, catalog, series, plan.leaves[0])[0], finish_reason="stop", latency_ms=123.456)
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    monkeypatch.setattr(module.persistence, "checkpoint", lambda name: None)
    artifact = ledger._path(series.series_id, aid + ".raw.json").read_bytes()
    assert json.loads(artifact)["latency_ms"] == 123.456
    fresh = BoundedExtractionStore(config)
    assert fresh.reconcile_attempt(aid, "worker", fence, catalog, ctx) == "SUCCEEDED_COMPLETE"
    assert fresh.reconcile_attempt(aid, "worker", fence, catalog, ctx) == "SUCCEEDED_COMPLETE"
    assert fresh.read(series.series_id)[3].latency_ms == 123.456
    assert len(calls) == 1 and calls[0].latency_ms == 123.456
    assert not fresh.record_dispatch(aid, "worker", fence)
    assert fresh._path(series.series_id, aid + ".raw.json").read_bytes() == artifact
    with Store(config).connect() as c:
        assert [r[0] for r in c.execute("SELECT latency_ms FROM bounded_extraction_outcomes")] == [123.456]
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_segment_results").fetchone()[0] == 1


@pytest.mark.parametrize("different", [False, True])
def test_concurrent_outcome_latency_is_immutable(setup, different):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    raw = body(ctx, catalog, series, plan.leaves[0])[0]
    observed = race(config, lambda s, i: s.record_outcome(aid, "worker", fence, raw, finish_reason="stop", latency_ms=789.5 if different and i else 123.456))
    if different:
        assert sum(v == "ARTIFACT_CONFLICT" for v in observed) == 1
        winner = next(v for v in observed if isinstance(v, dict))
    else:
        assert observed[0] == observed[1]
        winner = observed[0]
    with Store(config).connect() as c:
        assert [dict(r) for r in c.execute("SELECT * FROM bounded_extraction_outcomes")] == [winner]
    assert BoundedExtractionStore(config).read(series.series_id)[3].latency_ms == winner["latency_ms"]


def test_latency_corruption_breaks_outcome_identity(setup):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    ledger.record_outcome(aid, "worker", fence, b"synthetic", latency_ms=123.456)
    with Store(config).connect(operator_write=True) as c:
        c.execute("DROP TRIGGER bounded_extraction_outcomes_update")
        c.execute("UPDATE bounded_extraction_outcomes SET latency_ms=789.5")
    with pytest.raises(BoundaryError, match="BOUNDED_RECORD_IDENTITY_MISMATCH"):
        BoundedExtractionStore(config).read(series.series_id)
