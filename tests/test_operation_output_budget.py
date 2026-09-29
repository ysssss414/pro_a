"""Frozen operation budgets; all provider responses are synthetic and offline."""
import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import pro_a.cloud_contract as contract
from pro_a.cloud_contract import (
    CloudContractError, ProviderFailure, SOURCE_ANALYSIS_OPERATION, OPERATION_KIND,
    budget_for_operation, canonical, digest, operation_contract,
)
from pro_a.workbench.cloud_jobs import CloudProfile, JobError
from pro_a.workbench.domains import Domains
from pro_a.workbench.extraction_retry import frozen_cloud
from pro_a.workbench.source_operations import SourceOperationError
from test_cloud_operation_adapter_binding import setup_run, advance, jobs
from test_structured_json_reasoning_policy import assert_private_surfaces, completion, reasoning_sentinel
from test_llm import FakeResponse


BASELINE = "232b05fbbf32c7648876ec1fb58c94e0374c3bc1"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("External provider network is forbidden")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def test_authoritative_fixed_mapping_identity_and_no_environment_override(monkeypatch):
    monkeypatch.setenv("PRO_A_MAX_OUTPUT_TOKENS", "16000")
    monkeypatch.setenv("PRO_A_EXTRACTION_MAX_OUTPUT_TOKENS", "4000")
    monkeypatch.setenv("PRO_A_CLOUD_PROVIDER", "deepseek")
    monkeypatch.setenv("PRO_A_CLOUD_MODEL", "deepseek-flash")
    profile = CloudProfile.from_environment()
    assert (profile.max_output_tokens, profile.max_total_tokens) == (8192, 20000)
    expected = {SOURCE_ANALYSIS_OPERATION: {"max_output_tokens": 12000, "max_total_tokens": 20000},
                OPERATION_KIND: {"max_output_tokens": 8192, "max_total_tokens": 20000}}
    identity = profile.public_identity()
    assert identity["operation_output_budget_policy_version"] == "operation-output-budget-v1"
    assert identity["operation_output_budgets"] == expected
    for operation, budget in expected.items():
        assert budget_for_operation(operation, 20000) == budget_for_operation(operation, 20000) == budget
        changed = budget_for_operation(operation, 20000)
        changed["max_output_tokens"] = 1
        assert budget_for_operation(operation, 20000) == budget
    with pytest.raises(CloudContractError, match="UNSUPPORTED_CLOUD_OPERATION"):
        budget_for_operation("UNKNOWN", 20000)
    # The legacy base field cannot override the selected operation output mapping.
    assert replace(profile, max_output_tokens=16000).public_identity()["operation_output_budgets"] == expected


def test_budget_only_drift_changes_configuration_context_intent_and_idempotency(tmp_path, monkeypatch):
    from pro_a.processing_context import freeze_context
    value = setup_run(tmp_path, monkeypatch)
    service = value["service"]
    row = jobs(value)[0]
    before = copy.deepcopy(row)
    frozen = Domains(value["config"]).read(value["run_id"])
    assert frozen["basis"]["model_configuration"] == value["cloud_profile"].public_identity()
    with service.store.connect() as c:
        key = c.execute("SELECT idempotency_key FROM cloud_job_submissions WHERE job_id=?", (row["job_id"],)).fetchone()[0]
    monkeypatch.setitem(contract.OPERATION_MAX_OUTPUT_TOKENS, SOURCE_ANALYSIS_OPERATION, 12001)
    updated = value["cloud_profile"].public_identity()
    assert updated["configuration_sha256"] != row["configuration_sha256"]
    with pytest.raises(JobError, match="IDEMPOTENCY_CONFLICT"):
        service.jobs.submit(idempotency_key=key, input_artifact_id=row["input_artifact_id"], operation_kind=SOURCE_ANALYSIS_OPERATION)
    created = service.jobs.submit(idempotency_key="changed-budget-policy-0001", input_artifact_id=row["input_artifact_id"], operation_kind=SOURCE_ANALYSIS_OPERATION)
    with service.store.connect() as c:
        new = dict(c.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (created["job"]["job_id"],)).fetchone())
        assert dict(c.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (row["job_id"],)).fetchone()) == before
    assert new["intent_sha256"] != row["intent_sha256"] and new["max_output_tokens"] == 12001
    assert new["prompt_json"] == row["prompt_json"] and new["runtime_sha256"] == row["runtime_sha256"]
    basis = copy.deepcopy(frozen["basis"])
    basis["model_configuration"] = updated
    options = dict(run_id=value["run_id"], created_at="2026-01-01T00:00:00+00:00", actor="system", reason="Synthetic budget identity")
    assert freeze_context(basis, **options)["context_sha256"] != freeze_context(frozen["basis"], **options)["context_sha256"]
    assert Domains(value["config"]).read(value["run_id"]) == frozen


def test_dual_adapter_e2e_above_8192_and_frozen_reconstruction(tmp_path, monkeypatch, caplog, record_property):
    from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
    value = setup_run(tmp_path, monkeypatch)
    post = __import__("requests").post
    requests_seen = []
    def capture(url, **kwargs):
        payload = kwargs["json"]
        extraction = payload["messages"][0]["content"] == SOURCE_ANALYSIS_SYSTEM
        output = 12000 if extraction else 8192
        assert payload["max_tokens"] == output
        assert payload["thinking"] == {"type": "disabled"} and "reasoning_effort" not in payload
        assert payload["response_format"] == {"type": "json_object"}
        requests_seen.append(output)
        response = post(url, **kwargs)
        data = response.json()
        data["usage"] = completion(0, output_tokens=10000 if extraction else 200)["usage"]
        data["choices"][0]["message"]["reasoning_content"] = reasoning_sentinel()
        response.json = lambda: data
        return response
    monkeypatch.setattr("pro_a.llm.requests.post", capture)
    frozen_requests = []
    for provider in value["providers"].values():
        invoke = provider.invoke
        def capture_request(request, invoke=invoke):
            frozen_requests.append(request)
            return invoke(request)
        monkeypatch.setattr(provider, "invoke", capture_request)
    assert advance(value)["state"] == "SEMANTIC_PROCESSING"
    final = advance(value)
    assert final["state"] == "HUMAN_REVIEW_REQUIRED" and final["packet_id"] and final["packet_artifact_id"]
    assert requests_seen == [12000, 8192]
    rows = jobs(value)
    for row in rows:
        expected = 12000 if row["operation_kind"] == SOURCE_ANALYSIS_OPERATION else 8192
        assert (row["max_output_tokens"], row["max_total_tokens"]) == (expected, 20000)
        profile = frozen_cloud(row)
        assert profile.max_output_tokens == 8192 and profile.public_identity() == json.loads(row["configuration_json"])
        assert row["state"] == "SUCCEEDED" and row["validation_status"] == "PASS" and row["attempt_count"] == 1
        result = value["service"].jobs.private_result(row["job_id"])
        assert result["usage"]["reasoning_tokens"] == 0 and result["finish_reason"] == "stop"
        assert row["output_tokens"] == (10000 if expected == 12000 else 200)
        request = next(r for r in frozen_requests if r.job_id == row["job_id"])
        assert request.max_output_tokens == request.budget_identity["max_output_tokens"] == expected
        assert request.budget_identity["max_total_tokens"] == 20000
        assert request.budget_identity["reserved_output_tokens"] == expected
    semantic = next(row for row in rows if row["operation_kind"] == OPERATION_KIND)
    assert json.loads(semantic["native_checkpoint_json"])["semantic_partition"]["input_token_budget"] == 11808
    with value["service"].store.connect() as c:
        from pro_a.workbench.review_store import schema_version
        assert schema_version(c) == "11"
    assert_private_surfaces(value, caplog, tmp_path)
    record_property("extraction_completion_tokens", 10000)
    record_property("wire_output_budgets", "12000/8192")
    record_property("semantic_input_budget", 11808)
    record_property("packet_registered", True)


@pytest.mark.parametrize("operation,field,invalid", [
    (SOURCE_ANALYSIS_OPERATION, "max_output_tokens", 11999), (SOURCE_ANALYSIS_OPERATION, "max_output_tokens", 12001),
    (OPERATION_KIND, "max_output_tokens", 8191), (OPERATION_KIND, "max_output_tokens", 8193),
    (SOURCE_ANALYSIS_OPERATION, "max_total_tokens", 19999), (OPERATION_KIND, "max_total_tokens", 20001),
])
def test_frozen_budget_row_drift_fails_without_normalization(tmp_path, monkeypatch, operation, field, invalid):
    value = setup_run(tmp_path, monkeypatch)
    if operation == OPERATION_KIND:
        assert advance(value)["state"] == "SEMANTIC_PROCESSING"
    row = next(j for j in jobs(value) if j["operation_kind"] == operation)
    assert frozen_cloud(row).max_output_tokens == 8192
    row[field] = invalid
    original = copy.deepcopy(row)
    with pytest.raises(SourceOperationError, match="RETRY_FROZEN_CONFIG_INCOMPLETE"):
        frozen_cloud(row)
    assert row == original


def test_historical_v2_8192_configuration_remains_incompatible(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    row = jobs(value)[0]
    configuration = json.loads(row["configuration_json"])
    del configuration["operation_output_budget_policy_version"], configuration["operation_output_budgets"], configuration["configuration_sha256"]
    configuration["configuration_sha256"] = digest(configuration)
    row.update(configuration_json=canonical(configuration), configuration_sha256=configuration["configuration_sha256"], max_output_tokens=8192)
    before = copy.deepcopy(row)
    assert row["provider_adapter_version"] == "source-analysis-piece-adapter-v2"
    with pytest.raises(SourceOperationError, match="RETRY_FROZEN_CONFIG_INCOMPLETE"):
        frozen_cloud(row)
    assert row == before


def test_historical_context_is_readable_without_budget_backfill(tmp_path, monkeypatch):
    from pro_a.processing_context import freeze_context, validate_context, guard_resume
    value = setup_run(tmp_path, monkeypatch)
    basis = Domains(value["config"]).read(value["run_id"])["basis"]
    legacy_basis = copy.deepcopy(basis)
    model = legacy_basis["model_configuration"]
    del model["operation_output_budget_policy_version"], model["operation_output_budgets"], model["configuration_sha256"]
    model["configuration_sha256"] = digest(model)
    legacy = freeze_context(legacy_basis, run_id=value["run_id"], created_at="2026-01-01T00:00:00+00:00", actor="system", reason="Historical synthetic context")
    before = copy.deepcopy(legacy)
    validate_context(legacy)
    with pytest.raises(ValueError, match="PROCESSING_RUN_CONTEXT_DRIFT"):
        guard_resume(legacy, basis)
    assert legacy == before


@pytest.mark.parametrize("operation", [SOURCE_ANALYSIS_OPERATION, OPERATION_KIND])
@pytest.mark.parametrize("overrun", [0, 1])
def test_cumulative_budget_reservation_boundary(tmp_path, monkeypatch, operation, overrun):
    value = setup_run(tmp_path, monkeypatch)
    if operation == OPERATION_KIND:
        assert advance(value)["state"] == "SEMANTIC_PROCESSING"
    row = next(j for j in jobs(value) if j["operation_kind"] == operation)
    prior_usage = 20000 - row["max_output_tokens"] + overrun
    with value["service"].store.connect(operator_write=True) as c:
        c.execute("UPDATE cloud_jobs SET total_tokens=? WHERE job_id=?", (prior_usage, row["job_id"]))
    before = len(value["http_calls"])
    result = value["service"].jobs.run_once(value["providers"][operation], worker_id="cumulative-budget", job_id=row["job_id"])
    if overrun:
        assert result["status"] == "FAILED" and result["last_error"] == "BUDGET_EXCEEDED"
        assert len(value["http_calls"]) == before and result["attempt_count"] == 0
    else:
        assert result["status"] == "SUCCEEDED" and len(value["http_calls"]) == before + 1


@pytest.mark.parametrize("operation,bad_output", [(SOURCE_ANALYSIS_OPERATION, 8192), (OPERATION_KIND, 12000)])
def test_provider_budget_mismatch_fails_before_dispatch(tmp_path, monkeypatch, operation, bad_output):
    value = setup_run(tmp_path, monkeypatch)
    provider = value["providers"][operation]
    llm = provider.llm if operation == SOURCE_ANALYSIS_OPERATION else provider.backend.llm
    request = SimpleNamespace(operation_kind=operation, prompt_identity=operation_contract(operation), requested_model=llm.cfg.model,
                              timeout_seconds=llm.cfg.timeout_seconds, max_output_tokens=bad_output)
    with pytest.raises(ProviderFailure) as caught:
        provider.invoke(request)
    assert caught.value.external_outcome == "NOT_DISPATCHED" and not value["http_calls"]


@pytest.mark.parametrize("size", [8001, 11807, 11808, 11809])
def test_semantic_input_boundary_stays_11808(size):
    from pro_a.semantic_decomposition import partition_semantic_claims, semantic_prompt_token_upper_bound, SemanticDecompositionError
    claim = dict(claim_id="synthetic-budget-claim", claim_text="", evidence_units=[])
    claim["claim_text"] = "x" * (size - semantic_prompt_token_upper_bound([claim]))
    assert semantic_prompt_token_upper_bound([claim]) == size
    budget = budget_for_operation(OPERATION_KIND, 20000)
    limit = budget["max_total_tokens"] - budget["max_output_tokens"]
    assert limit == 11808
    if size <= limit:
        assert partition_semantic_claims([claim], max_input_tokens=limit) == [[claim]]
    else:
        with pytest.raises(SemanticDecompositionError, match="SEMANTIC_PARENT_TOKEN_BUDGET_EXCEEDED"):
            partition_semantic_claims([claim], max_input_tokens=limit)


@pytest.mark.parametrize("operation", [SOURCE_ANALYSIS_OPERATION, OPERATION_KIND])
def test_output_above_total_fails_existing_budget_gate(tmp_path, monkeypatch, operation):
    from workbench_stage6_fixture import stage6_fixture
    from pro_a.cloud_contract import DeterministicFakeProvider
    monkeypatch.setitem(contract.OPERATION_MAX_OUTPUT_TOKENS, operation, 20001)
    if operation == SOURCE_ANALYSIS_OPERATION:
        value = setup_run(tmp_path, monkeypatch)
        assert advance(value)["state"] == "FAILED"
        row = jobs(value)[0]
        assert row["sanitized_error"] == "BUDGET_EXCEEDED" and row["attempt_count"] == 0
        assert not value["http_calls"]
        return
    value = stage6_fixture(tmp_path)
    job = value["jobs"].submit(idempotency_key="operation-insufficient-total-0001", input_artifact_id=value["artifact_id"], operation_kind=operation)
    provider = DeterministicFakeProvider()
    result = value["jobs"].run_once(provider, worker_id="budget", job_id=job["job"]["job_id"])
    assert result["status"] == "FAILED" and result["last_error"] == "BUDGET_EXCEEDED"
    assert provider.call_count == 0


def test_truncation_at_12000_retains_existing_telemetry(tmp_path, monkeypatch, caplog):
    value = setup_run(tmp_path, monkeypatch)
    monkeypatch.setattr("pro_a.llm.requests.post", lambda *a, **k: FakeResponse(completion(0, finish="length", content="{", output_tokens=12000)))
    assert advance(value)["state"] == "FAILED"
    row = jobs(value)[0]
    failure = value["service"].jobs.get(row["job_id"])["failure_diagnostic"]
    assert row["max_output_tokens"] == failure["completion_tokens"] == 12000
    assert failure["output_parse_kind"] == "TRUNCATED" and failure["reasoning_tokens"] == 0
    assert failure["finish_reason"] == "length" and failure["retryable"] is False
    assert row["attempt_count"] == 1
    assert_private_surfaces(value, caplog, tmp_path)


def test_baseline_cloud_execution_surface_fails_closed():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    _execution_surface_comparison.cache_clear()
    result = _execution_surface_comparison("cloud", BASELINE)
    assert result["compatible"] is False and result["reason"] == "SEMANTIC_SURFACE_CHANGED"
