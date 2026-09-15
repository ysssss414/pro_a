"""Retain deterministic Stage 6 fake-provider scenarios and exact counters."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import os
import socket
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))

from pro_a.cloud_contract import DeterministicFakeProvider, OPERATION_KIND, digest
from pro_a.production_promotion import sha256_file
from pro_a.workbench.cloud_jobs import CloudJobs, CloudProfile, InjectedCrash
from workbench_stage6_fixture import stage6_fixture


def submit(case, key: str):
    return case["jobs"].submit(idempotency_key=key, input_artifact_id=case["artifact_id"],
                               operation_kind=OPERATION_KIND)


def attempt_count(case) -> int:
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        return connection.execute("SELECT COUNT(*) FROM cloud_attempts").fetchone()[0]


def snapshot(case, job_id: str, provider_calls: int, **extra) -> dict:
    return {
        "job": case["jobs"].get(job_id),
        "events": case["jobs"].events(job_id)["items"],
        "artifacts": case["jobs"].results(job_id),
        "fake_provider_calls": provider_calls,
        "durable_attempts": attempt_count(case),
        **extra,
    }


def run(root: Path, fixtures: Path) -> dict:
    fixtures.mkdir(parents=True, exist_ok=True)
    scenarios: dict[str, dict] = {}
    production_pairs: list[tuple[str, str]] = []
    duplicate_prevented = 0

    def new_case(name: str, *, profile=None):
        case = stage6_fixture(root / name, profile=profile)
        case["production_before"] = sha256_file(case["config"].knowledge_db)
        return case

    def retain(name: str, case, job_id: str, provider_calls: int, **extra):
        value = snapshot(case, job_id, provider_calls, **extra)
        production_after = sha256_file(case["config"].knowledge_db)
        production_pairs.append((case["production_before"], production_after))
        value["production_before_sha256"] = case["production_before"]
        value["production_after_sha256"] = production_after
        scenarios[name] = value
        (fixtures / f"{name}.json").write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    success = new_case("normal_success")
    success_job = submit(success, "offline-normal-success-0001")["job"]["job_id"]
    success_provider = DeterministicFakeProvider()
    success["jobs"].run_once(success_provider, worker_id="normal-worker", job_id=success_job)
    retain("normal_success", success, success_job, success_provider.call_count)

    rate = new_case("rate_limit_retry")
    rate_job = submit(rate, "offline-rate-limit-retry-0001")["job"]["job_id"]
    rate_provider = DeterministicFakeProvider("rate_limit_then_success")
    rate["jobs"].run_once(rate_provider, worker_id="retry-worker", job_id=rate_job)
    retain("rate_limit_retry", rate, rate_job, rate_provider.call_count)

    unknown_usage = new_case("usage_unknown")
    usage_job = submit(unknown_usage, "offline-usage-unknown-0001")["job"]["job_id"]
    usage_provider = DeterministicFakeProvider("usage_unknown")
    unknown_usage["jobs"].run_once(usage_provider, worker_id="usage-worker", job_id=usage_job)
    retain("usage_unknown", unknown_usage, usage_job, usage_provider.call_count)

    mismatch = new_case("model_mismatch")
    mismatch_job = submit(mismatch, "offline-model-mismatch-0001")["job"]["job_id"]
    mismatch_provider = DeterministicFakeProvider("model_mismatch")
    mismatch["jobs"].run_once(mismatch_provider, worker_id="model-worker", job_id=mismatch_job)
    retain("model_mismatch", mismatch, mismatch_job, mismatch_provider.call_count)

    duplicate = new_case("duplicate_submit")
    first = submit(duplicate, "offline-duplicate-submit-0001")
    repeated = submit(duplicate, "offline-duplicate-submit-0001")
    assert repeated["duplicate"] and repeated["job"]["job_id"] == first["job"]["job_id"]
    duplicate_provider = DeterministicFakeProvider()
    duplicate["jobs"].run_once(duplicate_provider, worker_id="duplicate-worker",
                               job_id=first["job"]["job_id"])
    assert duplicate["jobs"].run_once(duplicate_provider, worker_id="duplicate-worker-2",
                                      job_id=first["job"]["job_id"]) is None
    duplicate_prevented += 1
    retain("duplicate_submit", duplicate, first["job"]["job_id"], duplicate_provider.call_count,
           duplicate_response=True)

    contention = new_case("worker_contention")
    contention_job = submit(contention, "offline-worker-contention-0001")["job"]["job_id"]
    contention_provider = DeterministicFakeProvider(delay_seconds=.1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda worker: contention["jobs"].run_once(
                contention_provider, worker_id=worker, job_id=contention_job
            ),
            ("worker-one", "worker-two"),
        ))
    assert contention_provider.call_count == 1 and sum(item is not None for item in outcomes) == 1
    duplicate_prevented += 1
    retain("worker_contention", contention, contention_job, contention_provider.call_count)

    predispatch = new_case("predispatch_crash")
    predispatch_job = submit(predispatch, "offline-predispatch-crash-0001")["job"]["job_id"]
    predispatch_provider = DeterministicFakeProvider()
    try:
        predispatch["jobs"].run_once(
            predispatch_provider, worker_id="crash-worker", job_id=predispatch_job,
            lease_seconds=0, fault_at="after_dispatch_intent",
        )
    except InjectedCrash:
        pass
    else:  # pragma: no cover - qualification invariant
        raise AssertionError("FAULT_INJECTION_NOT_TRIGGERED")
    recovery = CloudJobs(predispatch["config"], predispatch["profile"])
    assert recovery.reconcile()["requeued"] == 1
    recovery.run_once(predispatch_provider, worker_id="restart-worker", job_id=predispatch_job)
    retain("predispatch_crash", predispatch, predispatch_job, predispatch_provider.call_count,
           recovery_action="REQUEUED_PROVEN_PRE_DISPATCH")

    ambiguous = new_case("unknown_external_outcome")
    ambiguous_job = submit(ambiguous, "offline-unknown-outcome-0001")["job"]["job_id"]
    ambiguous_provider = DeterministicFakeProvider("unknown_external_outcome")
    ambiguous["jobs"].run_once(ambiguous_provider, worker_id="ambiguous-worker", job_id=ambiguous_job)
    restarted_ambiguous = CloudJobs(ambiguous["config"], ambiguous["profile"])
    assert restarted_ambiguous.run_once(ambiguous_provider, worker_id="restart-worker",
                                        job_id=ambiguous_job) is None
    assert ambiguous_provider.call_count == 1
    duplicate_prevented += 1
    retain("unknown_external_outcome", ambiguous, ambiguous_job, ambiguous_provider.call_count,
           automatic_retry=False)

    durable = new_case("durable_result_reconciliation")
    durable_job = submit(durable, "offline-durable-result-0001")["job"]["job_id"]
    durable_provider = DeterministicFakeProvider()
    try:
        durable["jobs"].run_once(
            durable_provider, worker_id="durable-worker", job_id=durable_job,
            lease_seconds=0, fault_at="after_result_artifact_durable",
        )
    except InjectedCrash:
        pass
    else:  # pragma: no cover - qualification invariant
        raise AssertionError("FAULT_INJECTION_NOT_TRIGGERED")
    durable_restart = CloudJobs(durable["config"], durable["profile"])
    assert durable_restart.reconcile()["reconciled"] == 1
    assert durable_restart.run_once(durable_provider, worker_id="restart-worker", job_id=durable_job) is None
    duplicate_prevented += 1
    retain("durable_result_reconciliation", durable, durable_job, durable_provider.call_count,
           provider_call_repeated=False)

    drift = new_case("runtime_drift")
    drift_job = submit(drift, "offline-runtime-drift-0001")["job"]["job_id"]
    changed_runtime = dict(drift["jobs"].current_runtime())
    changed_runtime["git_sha"] = "f" * 40
    runtime_basis = dict(changed_runtime)
    runtime_basis.pop("runtime_sha256")
    changed_runtime["runtime_sha256"] = digest(runtime_basis)
    drift_restart = CloudJobs(drift["config"], drift["profile"], runtime=changed_runtime)
    assert drift_restart.reconcile()["runtime_blocked"] == 1
    drift_provider = DeterministicFakeProvider()
    assert drift_restart.run_once(drift_provider, worker_id="drift-worker", job_id=drift_job) is None
    retain("runtime_drift", drift, drift_job, drift_provider.call_count)

    base_profile = CloudProfile.demo()
    insufficient = CloudProfile(
        base_profile.provider, base_profile.requested_model, base_profile.accepted_model_aliases,
        base_profile.provider_adapter_version, base_profile.timeout_seconds,
        base_profile.max_output_tokens, base_profile.max_calls, base_profile.max_attempts, 100,
    )
    budget = new_case("budget_rejection", profile=insufficient)
    budget_job = submit(budget, "offline-budget-rejection-0001")["job"]["job_id"]
    budget_provider = DeterministicFakeProvider()
    budget["jobs"].run_once(budget_provider, worker_id="budget-worker", job_id=budget_job)
    retain("budget_rejection", budget, budget_job, budget_provider.call_count)

    fake_calls = sum(item["fake_provider_calls"] for item in scenarios.values())
    durable_attempts = sum(item["durable_attempts"] for item in scenarios.values())
    checks = {
        "normal_success": scenarios["normal_success"]["job"]["status"] == "SUCCEEDED",
        "rate_limit_then_success": scenarios["rate_limit_retry"]["fake_provider_calls"] == 2,
        "usage_unknown": scenarios["usage_unknown"]["job"]["usage"]["status"] == "UNKNOWN",
        "model_mismatch_failed": scenarios["model_mismatch"]["job"]["last_error"] == "MODEL_IDENTITY_MISMATCH",
        "duplicate_call_prevention": duplicate_prevented == 4,
        "worker_fencing": scenarios["worker_contention"]["fake_provider_calls"] == 1,
        "unknown_not_retried": scenarios["unknown_external_outcome"]["fake_provider_calls"] == 1,
        "durable_result_reconciled": scenarios["durable_result_reconciliation"]["job"]["status"] == "SUCCEEDED",
        "runtime_drift_blocked": scenarios["runtime_drift"]["job"]["status"] == "BLOCKED_RUNTIME_DRIFT",
        "budget_rejected_before_call": scenarios["budget_rejection"]["fake_provider_calls"] == 0,
        "production_unchanged": all(before == after for before, after in production_pairs),
    }
    return {
        "document_type": "phase42_stage6_offline_acceptance",
        "schema_version": "1",
        "network_socket_connect_patched_to_fail": True,
        "provider_credentials_present": False,
        "scenario_count": len(scenarios),
        "scenarios": sorted(scenarios),
        "checks": checks,
        "gate": "PASS" if all(checks.values()) else "FAIL",
        "counters": {
            "live_network_provider_calls": 0,
            "live_cloud_model_calls": 0,
            "local_model_calls": 0,
            "fake_provider_calls": fake_calls,
            "fake_provider_attempts": durable_attempts,
            "duplicate_provider_calls_prevented": duplicate_prevented,
            "recovery_required_cases": 1,
            "cold_restart_duplicate_provider_calls": 0,
            "production_write_attempts": 0,
            "production_apply_attempts": 0,
        },
        "counter_definitions": {
            "fake_provider_calls": "DeterministicFakeProvider.invoke entries",
            "fake_provider_attempts": "durable cloud_attempts rows, including proven pre-dispatch abandoned attempts",
            "duplicate_provider_calls_prevented": "duplicate submit, losing worker, unknown-outcome restart, and durable-result restart",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for name in ("PROA_LLM_API_KEY", "PRO_A_CLOUD_PROVIDER", "PRO_A_CLOUD_MODEL"):
        os.environ.pop(name, None)
    root = args.root.resolve()
    fixtures = args.fixtures.resolve()
    output = args.output.resolve()
    with patch.object(socket.socket, "connect", side_effect=AssertionError("NETWORK_DISABLED")):
        report = run(root, fixtures)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if report["gate"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
