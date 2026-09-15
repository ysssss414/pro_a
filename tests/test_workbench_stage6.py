from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from pro_a.cloud_contract import (
    CONTRACT_VERSION, OPERATION_KIND, RETRY_OWNER, CloudContractError, CloudRequest,
    CloudResult, DeterministicFakeProvider, SemanticBackendProvider, operation_contract,
)
from pro_a.production_promotion import sha256_file
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.cloud_jobs import (
    CloudJobs, CloudProfile, InjectedCrash, JobError, digest, prepare_cloud_jobs,
)
from workbench_stage6_fixture import stage6_fixture


def submit(case, suffix="0001", *, service=None):
    target = service or case["jobs"]
    return target.submit(idempotency_key="stage6-submission-" + suffix,
                         input_artifact_id=case["artifact_id"],
                         operation_kind=OPERATION_KIND)


def expire(case, job_id):
    with closing(sqlite3.connect(case["config"].state_db)) as connection, connection:
        connection.execute("UPDATE cloud_jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE job_id=?",
                           (job_id,))


def test_schema_migration_contract_and_submission_idempotency(tmp_path):
    case = stage6_fixture(tmp_path)
    assert case["config"].state_db.with_name("workbench.sqlite3.stage5-backup").read_bytes() == case["stage5_bytes"]
    assert prepare_cloud_jobs(case["config"])["status"] == "ALREADY_PREPARED"
    contract = operation_contract(OPERATION_KIND)
    assert contract["prompt_id"] == "semantic-decomposition"
    assert len(contract["prompt_bundle_sha256"]) == 64

    first = submit(case)
    repeated = submit(case)
    assert first["duplicate"] is False and repeated["duplicate"] is True
    assert repeated["job"]["job_id"] == first["job"]["job_id"]
    assert first["job"]["status"] == "QUEUED"
    assert first["job"]["retry_owner"] == RETRY_OWNER
    assert first["job"]["runtime_identity"]["cloud_contract_version"] == CONTRACT_VERSION
    assert first["job"]["prompt_identity"]["prompt_bundle_sha256"] == contract["prompt_bundle_sha256"]
    with pytest.raises(JobError, match="IDEMPOTENCY_CONFLICT"):
        case["jobs"].submit(idempotency_key="stage6-submission-0001",
                            input_artifact_id="ART_" + "0" * 32,
                            operation_kind=OPERATION_KIND)
    second = submit(case, "0002")
    assert second["job"]["job_id"] != first["job"]["job_id"]
    with pytest.raises(Exception, match="UNSUPPORTED_CLOUD_OPERATION"):
        case["jobs"].submit(idempotency_key="stage6-submission-0003",
                            input_artifact_id=case["artifact_id"], operation_kind="SOURCE_UPLOAD")


def test_typed_contract_preserves_request_result_and_attempt_identity(tmp_path):
    case = stage6_fixture(tmp_path)
    job = submit(case)["job"]

    class TypedProvider(DeterministicFakeProvider):
        def invoke(self, request):
            assert isinstance(request, CloudRequest)
            result = super().invoke(request)
            assert isinstance(result, CloudResult)
            return result

    provider = TypedProvider()
    result = case["jobs"].run_once(provider, worker_id="typed-worker", job_id=job["job_id"])
    request = provider.request_identities[0]
    assert result["status"] == "SUCCEEDED"
    assert request["job_id"] == job["job_id"]
    assert request["operation_kind"] == job["operation_kind"]
    assert request["input_artifact_id"] == job["input"]["artifact_id"]
    assert request["input_sha256"] == job["input"]["sha256"]
    assert request["runtime_identity"] == job["runtime_identity"]
    assert request["prompt_identity"] == job["prompt_identity"]
    assert request["provider"] == job["provider"]
    assert request["requested_model"] == job["requested_model"]
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        stored = json.loads(connection.execute(
            "SELECT request_identity_json FROM cloud_attempts WHERE job_id=?", (job["job_id"],)
        ).fetchone()[0])
    assert stored == request


def test_nested_retry_owner_is_rejected():
    class Config:
        max_retries = 1

    class LLM:
        cfg = Config()

    class Backend:
        llm = LLM()

    with pytest.raises(CloudContractError, match="NESTED_RETRY_OWNER_FORBIDDEN"):
        SemanticBackendProvider(Backend(), provider_identity="CLOUD")


@pytest.mark.parametrize("scenario,expected_status,usage,model_status", [
    ("success", "SUCCEEDED", "KNOWN", "EXACT"),
    ("usage_unknown", "SUCCEEDED", "UNKNOWN", "EXACT"),
    ("accepted_alias", "SUCCEEDED", "KNOWN", "ACCEPTED_ALIAS"),
    ("model_mismatch", "FAILED", "KNOWN", "MISMATCH"),
    ("invalid_output", "FAILED", "KNOWN", "EXACT"),
])
def test_provider_result_identity_usage_validation_and_private_artifact(
        tmp_path, scenario, expected_status, usage, model_status):
    case = stage6_fixture(tmp_path)
    job_id = submit(case)["job"]["job_id"]
    provider = DeterministicFakeProvider(scenario)
    result = case["jobs"].run_once(provider, worker_id="worker-a", job_id=job_id)
    assert result["status"] == expected_status
    assert result["usage"]["status"] == usage
    assert result["model_identity_status"] == model_status
    assert result["attempt_count"] == provider.call_count == 1
    if usage == "UNKNOWN":
        assert all(result["usage"][key] is None for key in
                   ("input_tokens", "output_tokens", "total_tokens", "cached_tokens"))
    else:
        assert result["usage"]["total_tokens"] == 120
    if scenario == "model_mismatch":
        assert result["last_error"] == "MODEL_IDENTITY_MISMATCH"
    if scenario == "invalid_output":
        assert result["last_error"] == "OUTPUT_VALIDATION_FAILED"
    artifacts = case["jobs"].results(job_id)
    assert artifacts["raw_output_exposed"] is False
    assert len(artifacts["items"]) == 1
    public = json.dumps({"job": result, "artifacts": artifacts})
    assert "raw_provider_output" not in public and str(case["config"].artifact_root) not in public


def test_retry_owner_attempt_counts_unknown_outcome_and_budget(tmp_path):
    rate_case = stage6_fixture(tmp_path / "rate")
    rate_job = submit(rate_case)["job"]["job_id"]
    rate = DeterministicFakeProvider("rate_limit_then_success")
    result = rate_case["jobs"].run_once(rate, worker_id="retry-owner", job_id=rate_job)
    assert result["status"] == "SUCCEEDED"
    assert result["attempt_count"] == rate.call_count == 2
    retry_events = [item["event_type"] for item in rate_case["jobs"].events(rate_job)["items"]]
    assert retry_events.count("RETRY_AUTHORIZED") == 1

    unknown_case = stage6_fixture(tmp_path / "unknown")
    unknown_job = submit(unknown_case)["job"]["job_id"]
    unknown = DeterministicFakeProvider("unknown_external_outcome")
    result = unknown_case["jobs"].run_once(unknown, worker_id="worker-u", job_id=unknown_job)
    assert result["status"] == "RECOVERY_REQUIRED" and result["recovery_required"] is True
    assert result["last_error"] == "UNKNOWN_EXTERNAL_OUTCOME"
    assert "synthetic secret diagnostics" not in json.dumps(result)
    assert unknown_case["jobs"].run_once(unknown, worker_id="worker-u2", job_id=unknown_job) is None
    assert unknown.call_count == 1

    profile = CloudProfile.demo()
    insufficient = CloudProfile(profile.provider, profile.requested_model,
                                profile.accepted_model_aliases, profile.provider_adapter_version,
                                profile.timeout_seconds, profile.max_output_tokens, profile.max_calls,
                                profile.max_attempts, 100)
    budget_case = stage6_fixture(tmp_path / "budget", profile=insufficient)
    budget_job = submit(budget_case)["job"]["job_id"]
    never_called = DeterministicFakeProvider()
    result = budget_case["jobs"].run_once(never_called, worker_id="worker-b", job_id=budget_job)
    assert result["status"] == "FAILED" and result["last_error"] == "BUDGET_EXCEEDED"
    assert never_called.call_count == 0


@pytest.mark.parametrize("scenario,expected_error", [
    ("transport_failure", "TRANSPORT_ERROR"),
    ("timeout_before_dispatch", "TIMEOUT"),
])
def test_transient_failures_stop_at_worker_attempt_budget(tmp_path, scenario, expected_error):
    case = stage6_fixture(tmp_path)
    job_id = submit(case)["job"]["job_id"]
    provider = DeterministicFakeProvider(scenario)
    result = case["jobs"].run_once(provider, worker_id="bounded-retry-worker", job_id=job_id)
    assert result["status"] == "FAILED"
    assert result["last_error"] == expected_error
    assert result["attempt_count"] == provider.call_count == case["profile"].max_attempts == 2
    events = case["jobs"].events(job_id)["items"]
    assert sum(item["event_type"] == "RETRY_AUTHORIZED" for item in events) == 1
    assert case["jobs"].run_once(provider, worker_id="another-worker", job_id=job_id) is None


def test_budget_is_reserved_before_call_and_actual_usage_reconciles(tmp_path):
    case = stage6_fixture(tmp_path)
    job_id = submit(case)["job"]["job_id"]

    class ReservationProvider(DeterministicFakeProvider):
        def invoke(self, request):
            with closing(sqlite3.connect(case["config"].state_db)) as connection:
                phase, calls, tokens = connection.execute(
                    "SELECT phase,reserved_calls,reserved_tokens FROM cloud_jobs WHERE job_id=?",
                    (job_id,),
                ).fetchone()
            assert phase == "CALL_POSSIBLE"
            assert calls == 1 and tokens == request.max_output_tokens
            return super().invoke(request)

    provider = ReservationProvider()
    result = case["jobs"].run_once(provider, worker_id="budget-worker", job_id=job_id)
    assert result["status"] == "SUCCEEDED"
    assert result["budget"]["reserved_calls"] == result["budget"]["reserved_tokens"] == 0
    assert result["usage"]["total_tokens"] == 120

    invalid = CloudProfile("DETERMINISTIC_FAKE", "fake-semantic-v1", (),
                           "deterministic-fake-v1", 30, 131_073, 1, 1, 200_000)
    invalid_case = stage6_fixture(tmp_path / "invalid-profile")
    with pytest.raises(JobError, match="CLOUD_BUDGET_INVALID"):
        CloudJobs(invalid_case["config"], invalid)


def test_two_workers_contend_and_only_one_calls_provider(tmp_path):
    case = stage6_fixture(tmp_path)
    job_id = submit(case)["job"]["job_id"]
    provider = DeterministicFakeProvider(delay_seconds=.15)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda worker: case["jobs"].run_once(provider, worker_id=worker, job_id=job_id),
            ("worker-one", "worker-two"),
        ))
    assert provider.call_count == 1
    assert case["jobs"].get(job_id)["status"] == "SUCCEEDED"
    assert sum(item is not None for item in results) == 1
    events = case["jobs"].events(job_id)["items"]
    assert sum(item["event_type"] == "LEASE_ACQUIRED" for item in events) == 1


@pytest.mark.parametrize("fault,expected,requeued,reconciled,provider_calls", [
    ("before_claim", "QUEUED", 0, 0, 0),
    ("after_claim", "QUEUED", 1, 0, 0),
    ("after_dispatch_intent", "QUEUED", 1, 0, 0),
    ("before_network_call", "RECOVERY_REQUIRED", 0, 0, 0),
    ("after_provider_response", "RECOVERY_REQUIRED", 0, 0, 1),
    ("before_result_artifact_durable", "RECOVERY_REQUIRED", 0, 0, 1),
    ("after_result_artifact_durable", "SUCCEEDED", 0, 1, 1),
    ("before_terminal_update", "SUCCEEDED", 0, 1, 1),
    ("after_terminal_update", "SUCCEEDED", 0, 0, 1),
])
def test_crash_matrix_and_cold_restart(tmp_path, fault, expected, requeued, reconciled, provider_calls):
    case = stage6_fixture(tmp_path)
    job_id = submit(case)["job"]["job_id"]
    provider = DeterministicFakeProvider()
    with pytest.raises(InjectedCrash):
        case["jobs"].run_once(provider, worker_id="crashing-worker", job_id=job_id,
                              lease_seconds=0, fault_at=fault)
    restarted = CloudJobs(case["config"], case["profile"])
    recovery = restarted.reconcile()
    assert recovery["requeued"] == requeued
    assert recovery["reconciled"] == reconciled
    state = restarted.get(job_id)["status"]
    assert state == expected
    assert provider.call_count == provider_calls
    if state == "QUEUED" and fault != "before_claim":
        completed = restarted.run_once(provider, worker_id="restart-worker", job_id=job_id)
        assert completed["status"] == "SUCCEEDED"
        assert provider.call_count == 1
    elif state == "RECOVERY_REQUIRED":
        assert restarted.run_once(provider, worker_id="restart-worker", job_id=job_id) is None
        assert provider.call_count == provider_calls
    assert restarted.reconcile()["reconciled"] == 0


def test_result_registration_is_idempotent_and_corruption_fails_closed(tmp_path):
    durable = stage6_fixture(tmp_path / "durable")
    durable_job = submit(durable)["job"]["job_id"]
    provider = DeterministicFakeProvider()
    with pytest.raises(InjectedCrash, match="before_terminal_update"):
        durable["jobs"].run_once(provider, worker_id="durable-worker", job_id=durable_job,
                                 lease_seconds=0, fault_at="before_terminal_update")
    restarted = CloudJobs(durable["config"], durable["profile"])
    assert restarted.reconcile()["reconciled"] == 1
    assert restarted.reconcile()["reconciled"] == 0
    assert provider.call_count == 1
    with closing(sqlite3.connect(durable["config"].state_db)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM cloud_job_results WHERE job_id=?", (durable_job,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM cloud_attempt_outcomes WHERE attempt_id IN "
            "(SELECT attempt_id FROM cloud_attempts WHERE job_id=?)", (durable_job,)
        ).fetchone()[0] == 1
    durable_artifact = next((durable["config"].artifact_root / "cloud-results" / durable_job).glob("*.json"))
    durable_artifact.write_bytes(durable_artifact.read_bytes() + b" ")
    with pytest.raises(JobError, match="RESULT_ARTIFACT_HASH_MISMATCH"):
        restarted.results(durable_job)

    corrupt = stage6_fixture(tmp_path / "corrupt")
    corrupt_job = submit(corrupt)["job"]["job_id"]
    corrupt_provider = DeterministicFakeProvider()
    with pytest.raises(InjectedCrash, match="after_result_artifact_durable"):
        corrupt["jobs"].run_once(corrupt_provider, worker_id="corrupt-worker", job_id=corrupt_job,
                                 lease_seconds=0, fault_at="after_result_artifact_durable")
    artifact = next((corrupt["config"].artifact_root / "cloud-results" / corrupt_job).glob("*.json"))
    artifact.write_bytes(artifact.read_bytes() + b" ")
    recovery = CloudJobs(corrupt["config"], corrupt["profile"]).reconcile()
    assert recovery["recovery_required"] == 1
    state = CloudJobs(corrupt["config"], corrupt["profile"]).get(corrupt_job)
    assert state["status"] == "RECOVERY_REQUIRED"
    assert state["last_error"] == "RESULT_ARTIFACT_ENCODING_MISMATCH"
    assert corrupt_provider.call_count == 1


def test_cold_restart_preserves_queued_success_failed_and_unknown_states(tmp_path):
    queued = stage6_fixture(tmp_path / "queued")
    queued_job = submit(queued)["job"]["job_id"]
    assert CloudJobs(queued["config"], queued["profile"]).get(queued_job)["status"] == "QUEUED"

    success = stage6_fixture(tmp_path / "success")
    success_job = submit(success)["job"]["job_id"]
    success_provider = DeterministicFakeProvider()
    success["jobs"].run_once(success_provider, worker_id="success-worker", job_id=success_job)
    success_restart = CloudJobs(success["config"], success["profile"])
    assert success_restart.get(success_job)["status"] == "SUCCEEDED"
    assert success_restart.run_once(success_provider, worker_id="repeat-worker", job_id=success_job) is None

    failed = stage6_fixture(tmp_path / "failed")
    failed_job = submit(failed)["job"]["job_id"]
    failed_provider = DeterministicFakeProvider("invalid_output")
    failed["jobs"].run_once(failed_provider, worker_id="failed-worker", job_id=failed_job)
    failed_restart = CloudJobs(failed["config"], failed["profile"])
    assert failed_restart.get(failed_job)["status"] == "FAILED"
    assert failed_restart.run_once(failed_provider, worker_id="repeat-worker", job_id=failed_job) is None

    unknown = stage6_fixture(tmp_path / "unknown")
    unknown_job = submit(unknown)["job"]["job_id"]
    unknown_provider = DeterministicFakeProvider("unknown_external_outcome")
    unknown["jobs"].run_once(unknown_provider, worker_id="unknown-worker", job_id=unknown_job)
    unknown_restart = CloudJobs(unknown["config"], unknown["profile"])
    assert unknown_restart.get(unknown_job)["status"] == "RECOVERY_REQUIRED"
    assert unknown_restart.run_once(unknown_provider, worker_id="repeat-worker", job_id=unknown_job) is None
    assert success_provider.call_count == failed_provider.call_count == unknown_provider.call_count == 1


def test_submission_identity_includes_runtime_and_prompt(tmp_path, monkeypatch):
    case = stage6_fixture(tmp_path)
    original = submit(case)["job"]
    changed_runtime = dict(case["jobs"].current_runtime())
    changed_runtime["git_sha"] = "f" * 40
    runtime_basis = dict(changed_runtime)
    runtime_basis.pop("runtime_sha256")
    changed_runtime["runtime_sha256"] = digest(runtime_basis)
    runtime_jobs = CloudJobs(case["config"], case["profile"], runtime=changed_runtime)
    with pytest.raises(JobError, match="IDEMPOTENCY_CONFLICT"):
        submit(case, service=runtime_jobs)
    different_runtime = submit(case, "runtime-0002", service=runtime_jobs)["job"]
    assert different_runtime["job_id"] != original["job_id"]
    assert different_runtime["runtime_identity"]["runtime_sha256"] != original["runtime_identity"]["runtime_sha256"]

    import pro_a.workbench.cloud_jobs as cloud_jobs_module
    original_contract = cloud_jobs_module.operation_contract

    def changed_contract(operation_kind):
        value = original_contract(operation_kind)
        return {**value, "prompt_version": "2.2-test", "prompt_bundle_sha256": "e" * 64}

    monkeypatch.setattr(cloud_jobs_module, "operation_contract", changed_contract)
    with pytest.raises(JobError, match="IDEMPOTENCY_CONFLICT"):
        submit(case)
    different_prompt = submit(case, "prompt-0003")["job"]
    assert different_prompt["job_id"] != original["job_id"]
    assert different_prompt["prompt_identity"]["prompt_bundle_sha256"] != original["prompt_identity"]["prompt_bundle_sha256"]


def test_runtime_and_registered_input_drift_block_without_call(tmp_path):
    runtime_case = stage6_fixture(tmp_path / "runtime")
    runtime_job = submit(runtime_case)["job"]["job_id"]
    changed = dict(runtime_case["jobs"].current_runtime())
    changed["runtime_sha256"] = "0" * 64
    restarted = CloudJobs(runtime_case["config"], runtime_case["profile"], runtime=changed)
    recovery = restarted.reconcile()
    assert recovery["runtime_blocked"] == 1
    assert restarted.get(runtime_job)["status"] == "BLOCKED_RUNTIME_DRIFT"

    artifact_case = stage6_fixture(tmp_path / "artifact")
    artifact_job = submit(artifact_case)["job"]["job_id"]
    packet_path = artifact_case["config"].artifact_root / artifact_case["packet_relative"]
    packet_path.write_text(packet_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    provider = DeterministicFakeProvider()
    result = artifact_case["jobs"].run_once(provider, worker_id="artifact-worker", job_id=artifact_job)
    assert result["status"] == "BLOCKED" and provider.call_count == 0
    assert "ARTIFACT" in result["last_error"] or result["last_error"] == "NATIVE_PACKET_UNAVAILABLE"


def test_prompt_checkpoint_and_event_chain_corruption_block_without_call(tmp_path):
    prompt_case = stage6_fixture(tmp_path / "prompt")
    prompt_job = submit(prompt_case)["job"]["job_id"]
    with closing(sqlite3.connect(prompt_case["config"].state_db)) as connection, connection:
        connection.execute("UPDATE cloud_jobs SET prompt_json='{}' WHERE job_id=?", (prompt_job,))
    prompt_provider = DeterministicFakeProvider()
    result = prompt_case["jobs"].run_once(prompt_provider, worker_id="prompt-worker", job_id=prompt_job)
    assert result["status"] == "BLOCKED" and result["last_error"] == "PROMPT_IDENTITY_MISMATCH"
    assert prompt_provider.call_count == 0

    checkpoint_case = stage6_fixture(tmp_path / "checkpoint")
    checkpoint_job = submit(checkpoint_case)["job"]["job_id"]
    with closing(sqlite3.connect(checkpoint_case["config"].state_db)) as connection, connection:
        connection.execute("UPDATE cloud_jobs SET native_checkpoint_json='{}' WHERE job_id=?", (checkpoint_job,))
    checkpoint_provider = DeterministicFakeProvider()
    result = checkpoint_case["jobs"].run_once(
        checkpoint_provider, worker_id="checkpoint-worker", job_id=checkpoint_job)
    assert result["status"] == "BLOCKED" and result["last_error"] == "NATIVE_CHECKPOINT_DRIFT"
    assert checkpoint_provider.call_count == 0

    event_case = stage6_fixture(tmp_path / "events")
    event_job = submit(event_case)["job"]["job_id"]
    with closing(sqlite3.connect(event_case["config"].state_db)) as connection, connection:
        with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY"):
            connection.execute("UPDATE cloud_job_events SET event_json='{}' WHERE job_id=?", (event_job,))
        connection.execute("DROP TRIGGER cloud_job_events_update_forbidden")
        connection.execute("UPDATE cloud_job_events SET event_json='{}' WHERE job_id=? AND sequence=1",
                           (event_job,))
    recovery = CloudJobs(event_case["config"], event_case["profile"]).reconcile()
    assert recovery["recovery_required"] == 1
    assert event_case["jobs"].get(event_job)["last_error"] == "JOB_EVENT_CHAIN_INCONSISTENT"


def test_authenticated_api_enqueues_only_and_sanitizes_projection(tmp_path, monkeypatch):
    case = stage6_fixture(tmp_path)
    token = "synthetic-stage6-browser-token-for-tests-only"
    monkeypatch.setenv(case["config"].session_token_env, token)
    production_before = sha256_file(case["config"].knowledge_db)
    with TestClient(create_app(case["config"], cloud_profile=case["profile"]),
                    base_url=case["config"].origin, client=("127.0.0.1", 1)) as client:
        assert client.get(PREFIX + "/jobs").status_code == 401
        login = client.post(PREFIX + "/session", headers={"Origin": case["config"].origin},
                            json={"token": token})
        csrf = login.json()["csrf_token"]
        body = {"idempotency_key": "stage6-api-submission-0001",
                "input_artifact_id": case["artifact_id"],
                "operation_kind": OPERATION_KIND}
        first = client.post(PREFIX + "/jobs", headers={"Origin": case["config"].origin,
                            "X-CSRF-Token": csrf}, json=body)
        second = client.post(PREFIX + "/jobs", headers={"Origin": case["config"].origin,
                             "X-CSRF-Token": csrf}, json=body)
        assert first.status_code == 200 and second.json()["duplicate"] is True
        arbitrary_prompt = client.post(
            PREFIX + "/jobs", headers={"Origin": case["config"].origin, "X-CSRF-Token": csrf},
            json={**body, "prompt": "browser supplied prompt is forbidden"},
        )
        assert arbitrary_prompt.status_code == 422
        assert arbitrary_prompt.json() == {"detail": "INVALID_REQUEST"}
        job_id = first.json()["job"]["job_id"]
        assert first.json()["job"]["status"] == "QUEUED"
        assert client.get(PREFIX + "/jobs").json()["total"] == 1
        assert client.get(PREFIX + f"/jobs/{job_id}").status_code == 200
        assert client.get(PREFIX + f"/jobs/{job_id}/events").json()["total"] == 2
        artifacts = client.get(PREFIX + f"/jobs/{job_id}/artifacts").json()
        assert artifacts == {"items": [], "private_artifacts": True, "raw_output_exposed": False}
        disclosure = json.dumps({"job": first.json(), "events": client.get(
            PREFIX + f"/jobs/{job_id}/events").json(), "artifacts": artifacts})
        assert token not in disclosure and str(case["config"].artifact_root) not in disclosure
        assert "Authorization" not in disclosure and "raw_provider_output" not in disclosure
    assert sha256_file(case["config"].knowledge_db) == production_before
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM cloud_attempts").fetchone()[0] == 0


def test_private_provider_diagnostic_and_source_content_are_not_persisted_in_job_db(tmp_path):
    case = stage6_fixture(tmp_path)
    job_id = submit(case)["job"]["job_id"]
    provider = DeterministicFakeProvider("unknown_external_outcome")
    result = case["jobs"].run_once(provider, worker_id="privacy-worker", job_id=job_id)
    assert result["last_error"] == "UNKNOWN_EXTERNAL_OUTCOME"
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        stage6_rows = [row for table in (
            "cloud_jobs", "cloud_job_submissions", "cloud_attempts", "cloud_attempt_dispatches",
            "cloud_attempt_outcomes", "cloud_job_results", "cloud_job_events",
        ) for row in connection.execute(f"SELECT * FROM {table}")]
        database_text = json.dumps(stage6_rows, default=str)
        event_text = "\n".join(row[0] for row in connection.execute(
            "SELECT event_json FROM cloud_job_events WHERE job_id=?", (job_id,)
        ))
    assert "synthetic secret diagnostics" not in database_text
    assert str(case["config"].artifact_root) not in database_text
    assert "Authorization" not in database_text
    assert "synthetic secret diagnostics" not in event_text
    assert "raw_provider_output" not in event_text
