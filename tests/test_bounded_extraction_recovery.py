"""Crash windows, independent SQLite workers and conservative liability."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from pro_a.bounded_extraction import SeriesBudget
from pro_a.workbench import bounded_extraction_persistence as migration
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from test_bounded_extraction import fixture
from test_bounded_extraction_persistence import setup, no_network, body, reserve, complete


def inject(monkeypatch, window):
    def crash(name):
        if name == window:
            raise RuntimeError("SYNTHETIC_CRASH")
    monkeypatch.setattr(migration, "checkpoint", crash)


@pytest.mark.parametrize("window", ["attempt_reserved", "dispatch_durable", "raw_artifact_durable", "outcome_durable", "result_accepted"])
def test_crash_a_through_e_fresh_instance(setup, monkeypatch, window):
    config, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    fence = ledger.claim_segment(segment.segment_id, "worker", lease_seconds=600)
    inject(monkeypatch, window)
    with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
        _, aid = reserve(ledger, segment, fence=fence)
        ledger.record_dispatch(aid, "worker", fence)
        ledger.record_outcome(aid, "worker", fence, body(ctx, catalog, series, segment)[0], finish_reason="stop", output_tokens=20)
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    monkeypatch.setattr(migration, "checkpoint", lambda name: None)
    fresh = BoundedExtractionStore(config)
    with Store(config).connect() as c:
        aid = c.execute("SELECT attempt_id FROM bounded_extraction_attempts").fetchone()[0]
    status = fresh.reconcile_attempt(aid, "worker", fence, catalog, ctx)
    if window == "attempt_reserved":
        assert status == "RESERVED_NOT_DISPATCHED"
        assert reserve(fresh, segment, fence=fence)[1] == aid
        assert fresh.record_dispatch(aid, "worker", fence)
    elif window == "dispatch_durable":
        assert status == "UNKNOWN_EXTERNAL_OUTCOME"
        assert not fresh.record_dispatch(aid, "worker", fence)
        assert fresh.read(series.series_id)[2]["state"] == "RECOVERY_REQUIRED"
        assert fresh.read(series.series_id)[3].output_token_liability == 12000
        with pytest.raises(BoundaryError, match="NOT_DISPATCHABLE"):
            reserve(fresh, segment, number=2, fence=fence)
    else:
        assert status == "SUCCEEDED_COMPLETE"
        assert fresh.reconcile_attempt(aid, "worker", fence, catalog, ctx) == status
        assert fresh.read(series.series_id)[3].output_token_liability == 20
    with Store(config).connect() as c:
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_attempts").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_segment_results").fetchone()[0] == int(window not in ("attempt_reserved", "dispatch_durable"))


@pytest.mark.parametrize("window", ["subdivision_child_inserted", "subdivision_parent_superseded", "subdivision_committed"])
def test_crash_f_atomic_subdivision(setup, monkeypatch, window):
    config, ledger, ctx, catalog, series, plan = setup
    parent = plan.leaves[0]
    fence, _, _ = complete(ledger, ctx, catalog, series, parent, True)
    inject(monkeypatch, window)
    with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
        ledger.subdivide(parent.segment_id, "worker", fence, expected_frontier_version=0)
    monkeypatch.setattr(migration, "checkpoint", lambda name: None)
    fresh = BoundedExtractionStore(config)
    _, recovered, row, _ = fresh.read(series.series_id)
    assert len(recovered.segments) == (3 if window == "subdivision_committed" else 1)
    assert row["frontier_version"] == int(window == "subdivision_committed")
    children = fresh.subdivide(parent.segment_id, "worker", fence, expected_frontier_version=0)
    assert len(children) == 2
    assert fresh.subdivide(parent.segment_id, "worker", fence, expected_frontier_version=0) == children
    assert fresh.read(series.series_id)[2]["frontier_version"] == 1


def test_crash_g_aggregate_artifact_reconciles(setup, monkeypatch):
    config, ledger, ctx, catalog, series, plan = setup
    complete(ledger, ctx, catalog, series, plan.leaves[0])
    sf = ledger.claim_series(series.series_id, "coordinator", lease_seconds=600)
    inject(monkeypatch, "aggregate_artifact_durable")
    with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
        ledger.finalize(series.series_id, "coordinator", sf, expected_frontier_version=0, catalog=catalog, context=ctx)
    monkeypatch.setattr(migration, "checkpoint", lambda name: None)
    artifact = ledger._path(series.series_id, "aggregate.json")
    before = artifact.read_bytes()
    with Store(config).connect() as c:
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_series_results").fetchone()[0] == 0
    fresh = BoundedExtractionStore(config)
    final = fresh.finalize(series.series_id, "coordinator", sf, expected_frontier_version=0, catalog=catalog, context=ctx)
    assert fresh.finalize(series.series_id, "coordinator", sf, expected_frontier_version=0, catalog=catalog, context=ctx) == final
    assert artifact.read_bytes() == before


def test_subprocess_abrupt_exit_after_raw_fsync(setup, tmp_path):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    # A real process exits without Python finally handlers or SQLite close.
    payload = {"config": {k: str(v) if isinstance(v, Path) else v for k, v in asdict(config).items()},
               "attempt_id": aid, "fence": fence, "raw": body(ctx, catalog, series, plan.leaves[0])[0].decode()}
    path = tmp_path / "subprocess.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    script = '''
import json, os, socket, sys
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench import bounded_extraction_persistence as p
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
def forbidden(*a, **k): raise RuntimeError("NETWORK_FORBIDDEN")
socket.socket.connect = forbidden
v=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for k in ("knowledge_db","state_db","artifact_root"): v["config"][k]=Path(v["config"][k])
def crash(name):
 if name == "raw_artifact_durable": os._exit(73)
p.checkpoint=crash
BoundedExtractionStore(WorkbenchConfig(**v["config"])).record_outcome(v["attempt_id"],"worker",v["fence"],v["raw"].encode(),finish_reason="stop",output_tokens=33)
'''
    child = subprocess.run([sys.executable, "-c", script, str(path)], env=os.environ.copy(), capture_output=True, timeout=30)
    assert child.returncode == 73, child.stderr.decode(errors="replace")
    fresh = BoundedExtractionStore(config)
    assert fresh.reconcile_attempt(aid, "worker", fence, catalog, ctx) == "SUCCEEDED_COMPLETE"
    assert fresh.read(series.series_id)[3].provider_call_count == 1


def race(config, action):
    barrier = threading.Barrier(2)
    def worker(index):
        ledger = BoundedExtractionStore(config)
        barrier.wait(timeout=10)
        try:
            return action(ledger, index)
        except BoundaryError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(worker, range(2)))


def test_concurrent_claim_reserve_dispatch_accept_subdivide_finalize(setup):
    config, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    claimed = race(config, lambda s, i: s.claim_segment(segment.segment_id, "worker" + str(i), lease_seconds=600))
    assert sorted(map(str, claimed)) == ["1", "LEASE_BUSY"]
    owner = "worker" + str(claimed.index(1))
    attempts = race(config, lambda s, i: reserve(s, segment, owner, fence=1)[1])
    assert attempts[0] == attempts[1]
    aid = attempts[0]
    assert sorted(race(config, lambda s, i: s.record_dispatch(aid, owner, 1))) == [False, True]
    raw, _ = body(ctx, catalog, series, segment, True)
    ledger.record_outcome(aid, owner, 1, raw, finish_reason="stop", output_tokens=10)
    accepted = race(config, lambda s, i: s.accept_result(aid, owner, 1, catalog, ctx))
    assert accepted[0] == accepted[1]
    children = race(config, lambda s, i: s.subdivide(segment.segment_id, owner, 1, expected_frontier_version=0))
    assert children[0] == children[1] and len(children[0]) == 2
    for child in children[0]:
        complete(ledger, ctx, catalog, series, child)
    sf = ledger.claim_series(series.series_id, "coordinator", lease_seconds=600)
    finals = race(config, lambda s, i: s.finalize(series.series_id, "coordinator", sf, expected_frontier_version=1, catalog=catalog, context=ctx))
    assert finals[0] == finals[1]
    with Store(config).connect() as c:
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_attempts").fetchone()[0] == 3
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_series_results").fetchone()[0] == 1


@pytest.mark.parametrize("operation", ["dispatch", "outcome", "accept", "subdivide", "close"])
def test_stale_segment_fence_rejects_every_write(setup, operation):
    config, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    expired = time.time() - 10
    fence = ledger.claim_segment(segment.segment_id, "a", lease_seconds=1, now=expired)
    # Reserve under a current lease first, then prove every old-fence mutation fails.
    fresh_fence = ledger.claim_segment(segment.segment_id, "b", lease_seconds=600)
    _, aid = reserve(ledger, segment, "b", fence=fresh_fence)
    assert fresh_fence == fence + 1
    actions = {
        "dispatch": lambda: ledger.record_dispatch(aid, "a", fence),
        "outcome": lambda: ledger.record_outcome(aid, "a", fence, b"{}"),
        "accept": lambda: ledger.accept_result(aid, "a", fence, catalog, ctx),
        "subdivide": lambda: ledger.subdivide(segment.segment_id, "a", fence, expected_frontier_version=0),
        "close": lambda: ledger.close_segment(segment.segment_id, "a", fence),
    }
    before = config.state_db.read_bytes()
    with pytest.raises(BoundaryError, match="STALE_FENCE"):
        actions[operation]()
    assert config.state_db.read_bytes() == before


def test_stale_frontier_and_series_fence(setup):
    _, ledger, ctx, catalog, series, plan = setup
    sf = ledger.claim_series(series.series_id, "old", lease_seconds=1, now=time.time() - 10)
    new = ledger.claim_series(series.series_id, "new", lease_seconds=600)
    with pytest.raises(BoundaryError, match="STALE_FENCE"):
        ledger.finalize(series.series_id, "old", sf, expected_frontier_version=0, catalog=catalog, context=ctx)
    fence, _, _ = complete(ledger, ctx, catalog, series, plan.leaves[0], True)
    with pytest.raises(BoundaryError, match="STALE_FRONTIER"):
        ledger.subdivide(plan.leaves[0].segment_id, "worker", fence, expected_frontier_version=1)
    ledger.subdivide(plan.leaves[0].segment_id, "worker", fence, expected_frontier_version=0)
    with pytest.raises(BoundaryError, match="STALE_FRONTIER"):
        ledger.finalize(series.series_id, "new", new, expected_frontier_version=0, catalog=catalog, context=ctx)


@pytest.mark.parametrize("budget,output", [(SeriesBudget(max_provider_calls=2), 5),
    (SeriesBudget(max_cumulative_output_tokens=24000), None)])
def test_budget_exact_and_one_above_with_retry(setup, budget, output):
    config, ledger, *_ = setup
    ctx, catalog, series, plan = fixture(2, budget)
    ledger.create(series)
    segment = plan.leaves[0]
    fence, aid = reserve(ledger, segment)
    for number in (1, 2):
        if number == 2:
            _, aid = reserve(ledger, segment, number=number, fence=fence)
        ledger.record_dispatch(aid, "worker", fence)
        ledger.record_outcome(aid, "worker", fence, b"malformed", finish_reason="stop", output_tokens=output)
        with pytest.raises(BoundaryError, match="INVALID_SEGMENT_RESPONSE"):
            ledger.accept_result(aid, "worker", fence, catalog, ctx)
    usage = ledger.read(series.series_id)[3]
    assert usage.provider_call_count == 2
    assert usage.output_token_liability == (10 if output is not None else 24000)
    with pytest.raises(BoundaryError, match="SERIES_BUDGET_EXCEEDED"):
        reserve(ledger, segment, number=3, fence=fence)
    assert ledger.read(series.series_id)[3] == usage


def test_truncated_parent_retry_valid_subdivision_children_share_budget(setup):
    _, ledger, ctx, catalog, series, plan = setup
    parent = plan.leaves[0]
    fence, aid = reserve(ledger, parent)
    ledger.record_dispatch(aid, "worker", fence)
    ledger.record_outcome(aid, "worker", fence, b'{"wire":', finish_reason="length", output_tokens=12000)
    with pytest.raises(BoundaryError, match="RAW_OUTCOME_NOT_ACCEPTABLE"):
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    _, retry = reserve(ledger, parent, number=2, fence=fence)
    ledger.record_dispatch(retry, "worker", fence)
    ledger.record_outcome(retry, "worker", fence, body(ctx, catalog, series, parent, True)[0], finish_reason="stop", output_tokens=20)
    ledger.accept_result(retry, "worker", fence, catalog, ctx)
    children = ledger.subdivide(parent.segment_id, "worker", fence, expected_frontier_version=0)
    for child in children:
        complete(ledger, ctx, catalog, series, child)
    usage = ledger.read(series.series_id)[3]
    assert usage.provider_call_count == 4 and usage.output_token_liability == 12120


def test_atomic_budget_race_between_distinct_segments(setup):
    config, ledger, *_ = setup
    _, _, series, plan = fixture(2, SeriesBudget(initial_evidence_refs=1, max_provider_calls=1))
    ledger.create(series)
    for segment in plan.leaves:
        ledger.claim_segment(segment.segment_id, "worker", lease_seconds=600)
    outcomes = race(config, lambda s, i: reserve(s, plan.leaves[i], fence=1)[1])
    assert sum(v == "SERIES_BUDGET_EXCEEDED" for v in outcomes) == 1
    assert ledger.read(series.series_id)[3].provider_call_count == 1


def test_default_32_calls_384000_liability_exact_and_above(setup):
    _, ledger, ctx, catalog, series, plan = setup
    segment = plan.leaves[0]
    fence, aid = reserve(ledger, segment)
    for number in range(1, 33):
        if number > 1:
            _, aid = reserve(ledger, segment, number=number, fence=fence)
        ledger.record_dispatch(aid, "worker", fence)
        ledger.record_outcome(aid, "worker", fence, b"incomplete", finish_reason="length", output_tokens=12000)
        with pytest.raises(BoundaryError, match="RAW_OUTCOME_NOT_ACCEPTABLE"):
            ledger.accept_result(aid, "worker", fence, catalog, ctx)
    usage = ledger.read(series.series_id)[3]
    assert usage.provider_call_count == 32 and usage.output_token_liability == 384000
    with pytest.raises(BoundaryError, match="SERIES_BUDGET_EXCEEDED"):
        reserve(ledger, segment, number=33, fence=fence)


def test_one_token_over_reservation_is_rejected(setup):
    _, ledger, *_ = setup
    ctx, catalog, series, plan = fixture(2, SeriesBudget(max_cumulative_output_tokens=12000))
    ledger.create(series)
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    ledger.record_outcome(aid, "worker", fence, b"invalid", output_tokens=1)
    with pytest.raises(BoundaryError, match="INVALID_SEGMENT_RESPONSE"):
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    with pytest.raises(BoundaryError, match="SERIES_BUDGET_EXCEEDED"):
        reserve(ledger, plan.leaves[0], number=2, fence=fence)
