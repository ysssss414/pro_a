"""Measure Stage 6 local job-control overhead without provider latency."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import time
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))

from pro_a.cloud_contract import DeterministicFakeProvider, OPERATION_KIND
from pro_a.production_promotion import sha256_file
from pro_a.workbench.cloud_jobs import InjectedCrash
from workbench_stage6_fixture import stage6_fixture


THRESHOLDS_MS = {
    "job_enqueue_p95": 500.0,
    "job_status_p95": 100.0,
    "event_fetch_p95": 100.0,
    "worker_claim_p95": 250.0,
    "terminal_reconciliation_p95": 500.0,
}


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * quantile) - 1)], 3)


def elapsed(callable_) -> tuple[float, object]:
    started = time.perf_counter()
    result = callable_()
    return (time.perf_counter() - started) * 1000, result


def measure(root: Path) -> dict:
    case = stage6_fixture(root)
    jobs = case["jobs"]
    production_before = sha256_file(case["config"].knowledge_db)

    enqueue: list[float] = []
    job_ids: list[str] = []
    for index in range(31):
        duration, result = elapsed(lambda index=index: jobs.submit(
            idempotency_key=f"stage6-performance-enqueue-{index:04d}",
            input_artifact_id=case["artifact_id"], operation_kind=OPERATION_KIND,
        ))
        enqueue.append(duration)
        job_ids.append(result["job"]["job_id"])

    status = [elapsed(lambda: jobs.get(job_ids[0]))[0] for _ in range(101)]
    events = [elapsed(lambda: jobs.events(job_ids[0], limit=100))[0] for _ in range(101)]

    claims: list[float] = []
    for index, job_id in enumerate(job_ids):
        duration, claimed = elapsed(
            lambda index=index, job_id=job_id: jobs._claim(
                f"performance-worker-{index:04d}", job_id, 600
            )
        )
        assert claimed is not None
        claims.append(duration)

    reconciliation: list[float] = []
    fake_provider_calls = 0
    for index in range(15):
        submitted = jobs.submit(
            idempotency_key=f"stage6-performance-reconcile-{index:04d}",
            input_artifact_id=case["artifact_id"], operation_kind=OPERATION_KIND,
        )
        provider = DeterministicFakeProvider()
        try:
            jobs.run_once(provider, worker_id=f"reconcile-worker-{index:04d}",
                          job_id=submitted["job"]["job_id"], lease_seconds=0,
                          fault_at="after_result_artifact_durable")
        except InjectedCrash:
            pass
        else:  # pragma: no cover - qualification invariant
            raise AssertionError("FAULT_INJECTION_NOT_TRIGGERED")
        duration, reconciled = elapsed(jobs.reconcile)
        assert reconciled["reconciled"] == 1
        reconciliation.append(duration)
        fake_provider_calls += provider.call_count

    with sqlite3.connect(case["config"].state_db) as connection:
        durable_attempts = connection.execute("SELECT COUNT(*) FROM cloud_attempts").fetchone()[0]
    production_after = sha256_file(case["config"].knowledge_db)
    metrics = {
        "job_enqueue_p50": percentile(enqueue, .50),
        "job_enqueue_p95": percentile(enqueue, .95),
        "job_status_p95": percentile(status, .95),
        "event_fetch_p95": percentile(events, .95),
        "worker_claim_p95": percentile(claims, .95),
        "terminal_reconciliation_p95": percentile(reconciliation, .95),
    }
    checks = {name: metrics[name] <= threshold for name, threshold in THRESHOLDS_MS.items()}
    return {
        "document_type": "phase42_stage6_operational_performance",
        "schema_version": "1",
        "provider_sleep_included": False,
        "thresholds_ms": THRESHOLDS_MS,
        "sample_counts": {"job_enqueue": len(enqueue), "job_status": len(status),
                          "event_fetch": len(events), "worker_claim": len(claims),
                          "terminal_reconciliation": len(reconciliation)},
        "metrics_ms": metrics,
        "checks": checks,
        "gate": "PASS" if all(checks.values()) else "FAIL",
        "performance_setup_fake_provider_calls": fake_provider_calls,
        "performance_setup_durable_attempts": durable_attempts,
        "production_before_sha256": production_before,
        "production_after_sha256": production_after,
        "production_changed": production_before != production_after,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    report = measure(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if report["gate"] != "PASS" or report["production_changed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
