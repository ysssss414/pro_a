"""Offline wire policy, nullable token accounting, and reasoning-text privacy."""
import copy
import json
import logging
from types import SimpleNamespace

import pytest

from pro_a.cloud_contract import (
    CloudContractError, CloudResult, ProviderFailure, OPERATION_KIND,
    SOURCE_ANALYSIS_OPERATION, adapter_version_for_operation, operation_contract,
)
from pro_a.provider_diagnostics import safe_reasoning_tokens
from pro_a.workbench.cloud_jobs import CloudProfile
from test_cloud_operation_adapter_binding import setup_run, advance, jobs
from test_llm import FakeResponse, make_llm
from test_provider_output_failure_telemetry import diagnostic


BASELINE = "7d34055477a1997888db1c7315ab0d59becc17a0"


def reasoning_sentinel():
    return "_".join(("PRIVATE_REASONING", "SENTINEL_DO_NOT_PERSIST"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No external provider network is authorized")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def completion(count, *, finish="stop", content="{}", output_tokens=200):
    return {"model": "deepseek-flash", "choices": [{"finish_reason": finish,
        "message": {"content": content, "reasoning_content": reasoning_sentinel()}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": output_tokens,
                  "total_tokens": 100 + output_tokens,
                  "completion_tokens_details": {"reasoning_tokens": count}}}


@pytest.mark.parametrize("count,expected", [
    (0, 0), (1, 1), (25, 25), (200, 200), (None, None),
    (True, None), (-1, None), (1.5, None), ("100", None),
    (10_000_001, None), (201, None),
])
def test_reasoning_count_validation_and_generic_default(monkeypatch, count, expected):
    llm, captured = make_llm(monkeypatch, FakeResponse(completion(count)))
    assert llm.json("system", "user") == {}
    assert "thinking" not in captured["payload"] and "reasoning_effort" not in captured["payload"]
    metadata = llm.last_call_metadata
    assert metadata["attempts"][0]["reasoning_tokens"] == expected
    assert diagnostic(reasoning_tokens=count, completion_tokens=200)["reasoning_tokens"] == expected
    assert reasoning_sentinel() not in json.dumps(metadata)


def test_missing_breakdown_is_unknown_and_explicit_wire_is_additive(monkeypatch):
    response = completion(None)
    response["usage"].pop("completion_tokens_details")
    llm, captured = make_llm(monkeypatch, [FakeResponse(response), FakeResponse(response)], max_output_tokens=8192)
    llm.json("system", "user")
    default = copy.deepcopy(captured["payload"])
    llm.json("system", "user", thinking_mode="disabled")
    assert captured["payload"] == {**default, "thinking": {"type": "disabled"}}
    assert llm.last_call_metadata["attempts"][0]["reasoning_tokens"] is None
    assert captured["payload"]["max_tokens"] == 8192
    assert captured["payload"]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("mode", ["enabled", "other", True, 1])
def test_generic_rejects_unsupported_thinking_before_dispatch(monkeypatch, mode):
    from pro_a.llm import LLMError
    llm, captured = make_llm(monkeypatch, FakeResponse(completion(0)))
    with pytest.raises(LLMError, match="UNSUPPORTED_THINKING_MODE"):
        llm.json("system", "user", thinking_mode=mode)
    assert captured["calls"] == []


@pytest.mark.parametrize("shape", ["schema", "content_type", "http", "retry_http", "invalid_json"])
def test_response_envelope_errors_do_not_disclose_reasoning(monkeypatch, shape, caplog):
    from pro_a.llm import LLMError
    data = completion(0)
    if shape == "schema":
        del data["choices"][0]["message"]["content"]
    elif shape == "content_type":
        data["choices"][0]["message"]["content"] = None
    response = FakeResponse(data, status_code=400 if shape == "http" else 503 if shape == "retry_http" else 200,
                            text=json.dumps(data))
    if shape == "invalid_json":
        def invalid():
            raise ValueError(reasoning_sentinel())
        response.json = invalid
    llm, _ = make_llm(monkeypatch, response)
    llm.cfg.max_retries = 0
    with caplog.at_level(logging.DEBUG), pytest.raises(LLMError) as caught:
        llm.json("system", "user")
    assert reasoning_sentinel() not in str(caught.value) + caplog.text + json.dumps(llm.last_call_metadata)


def result(**changes):
    base = dict(provider="deepseek", requested_model="deepseek-flash", provider_reported_model="deepseek-flash",
        provider_request_id=None, operation_kind=SOURCE_ANALYSIS_OPERATION, attempt_number=1,
        started_at="2026-01-01T00:00:00+00:00", ended_at="2026-01-01T00:00:00+00:00", latency_ms=0,
        finish_reason="stop", usage_status="KNOWN", input_tokens=100, output_tokens=200,
        total_tokens=300, cached_tokens=None, output={})
    return CloudResult(**{**base, **changes})


@pytest.mark.parametrize("count", [True, -1, 1.5, "100", 10_000_001, 201])
def test_cloud_result_rejects_invalid_reasoning_counts(count):
    with pytest.raises(CloudContractError, match="INVALID_PROVIDER_RESULT"):
        result(reasoning_tokens=count)


def test_cloud_result_nullable_usage_and_fingerprint_stability():
    assert result().reasoning_tokens is None
    assert result(reasoning_tokens=0).reasoning_tokens == 0
    assert result(reasoning_tokens=200).reasoning_tokens == 200
    unknown = dict(usage_status="UNKNOWN", input_tokens=None, output_tokens=None, total_tokens=None)
    assert result(**unknown).reasoning_tokens is None
    with pytest.raises(CloudContractError):
        result(**unknown, reasoning_tokens=0)
    assert safe_reasoning_tokens(10_000_000, 10_000_000) == 10_000_000
    first = diagnostic(output_parse_kind="TRUNCATED", finish_reason="length", reasoning_tokens=1, completion_tokens=8192)
    other = diagnostic(output_parse_kind="TRUNCATED", finish_reason="length", reasoning_tokens=8192, completion_tokens=8192)
    assert first["error_fingerprint"] == other["error_fingerprint"]


def assert_private_surfaces(value, caplog, tmp_path):
    service = value["service"]
    with service.store.connect() as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_schema WHERE type='table'")]
        database = json.dumps({t: [list(r) for r in c.execute('SELECT * FROM "' + t + '"')] for t in tables})
        assert c.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0] == 0
    dtos = [service.jobs.get(j["job_id"]) for j in jobs(value)]
    receipt = json.dumps({"states": [j["status"] for j in dtos], "privacy": "PASS"})
    (tmp_path / "qualification-receipt.json").write_text(receipt, encoding="utf-8")
    surfaces = database + json.dumps(dtos) + caplog.text + receipt
    for artifact in value["config"].artifact_root.rglob("*.json"):
        surfaces += artifact.read_text(encoding="utf-8")
    assert reasoning_sentinel() not in surfaces
    assert "reasoning_content" not in surfaces
    assert value["config"].knowledge_db.read_bytes() == value["production_before"]
    assert value["production_writes"] == []


def test_structured_dual_adapter_e2e_reasoning_zero_durable_and_private(tmp_path, monkeypatch, caplog, record_property):
    from pro_a import analyzer
    value = setup_run(tmp_path, monkeypatch)
    original = __import__("requests").post
    calls = []
    def post(*args, **kwargs):
        payload = kwargs["json"]
        assert payload["thinking"] == {"type": "disabled"}
        assert "reasoning_effort" not in payload
        assert payload["model"] == "deepseek-flash" and payload["max_tokens"] == 8192
        assert payload["response_format"] == {"type": "json_object"}
        calls.append(payload["messages"][0]["content"])
        response = original(*args, **kwargs)
        data = response.json()
        data["usage"] = {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300,
                         "completion_tokens_details": {"reasoning_tokens": 0}}
        data["choices"][0]["message"]["reasoning_content"] = reasoning_sentinel()
        response.json = lambda: data
        return response
    monkeypatch.setattr("pro_a.llm.requests.post", post)
    with caplog.at_level(logging.DEBUG):
        assert advance(value)["state"] == "SEMANTIC_PROCESSING"
        final = advance(value)
    assert final["state"] == "HUMAN_REVIEW_REQUIRED" and final["packet_id"] and final["packet_artifact_id"]
    assert len(calls) == 2 and len(set(calls)) == 2
    assert analyzer.FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS == 5000
    for row in jobs(value):
        contract = operation_contract(row["operation_kind"])
        assert json.loads(row["prompt_json"]) == contract
        assert contract["thinking_policy_version"] == "structured-json-reasoning-v1"
        assert contract["thinking_mode"] == "disabled"
        assert row["provider_adapter_version"] == adapter_version_for_operation(row["operation_kind"])
        assert row["provider_adapter_version"].endswith("-v2")
        assert (row["max_output_tokens"], row["max_total_tokens"]) == (8192, 20000)
        assert value["service"].jobs.private_result(row["job_id"])["usage"]["reasoning_tokens"] == 0
        with value["service"].store.connect() as c:
            completed = [json.loads(r[0]) for r in c.execute("SELECT event_json FROM cloud_job_events WHERE job_id=? AND event_type='PROVIDER_ATTEMPT_COMPLETED'", (row["job_id"],))]
            assert len(completed) == 1 and completed[0]["reasoning_tokens"] == 0
            assert value["service"].jobs._verify_event_chain(c, row["job_id"])
    assert_private_surfaces(value, caplog, tmp_path)
    record_property("structured_http_calls", len(calls))
    record_property("reasoning_tokens", 0)
    record_property("packet_registered", True)
    record_property("privacy_sentinel_absent", True)


def test_truncation_reasoning_count_is_durable_without_content(tmp_path, monkeypatch, caplog):
    value = setup_run(tmp_path, monkeypatch)
    monkeypatch.setattr("pro_a.llm.requests.post", lambda *a, **k: FakeResponse(
        completion(8192, finish="length", content="", output_tokens=8192)))
    with caplog.at_level(logging.DEBUG):
        assert advance(value)["state"] == "FAILED"
    job = value["service"].jobs.get(jobs(value)[0]["job_id"])
    d = job["failure_diagnostic"]
    assert (d["output_parse_kind"], d["finish_reason"], d["completion_tokens"], d["reasoning_tokens"], d["content_length"]) == ("TRUNCATED", "length", 8192, 8192, 0)
    assert d["retryable"] is False and job["attempt_count"] == 1
    assert_private_surfaces(value, caplog, tmp_path)


@pytest.mark.parametrize("operation", [SOURCE_ANALYSIS_OPERATION, OPERATION_KIND])
@pytest.mark.parametrize("field,value", [("thinking_mode", "enabled"), ("thinking_policy_version", "other"), ("provider_adapter_version", "legacy-v1")])
def test_policy_mismatch_fails_before_dispatch(tmp_path, monkeypatch, operation, field, value):
    setup = setup_run(tmp_path, monkeypatch)
    identity = operation_contract(operation)
    identity[field] = value
    request = SimpleNamespace(operation_kind=operation, prompt_identity=identity)
    with pytest.raises(ProviderFailure, match="PROVIDER_REASONING_POLICY_MISMATCH") as caught:
        setup["providers"][operation].invoke(request)
    assert caught.value.external_outcome == "NOT_DISPATCHED" and not caught.value.retryable
    assert setup["http_calls"] == []


def test_baseline_execution_surfaces_fail_closed():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    _execution_surface_comparison.cache_clear()
    for kind in ("cloud", "native"):
        comparison = _execution_surface_comparison(kind, BASELINE)
        assert comparison["compatible"] is False and comparison["reason"] == "SEMANTIC_SURFACE_CHANGED"


def test_semantic_backend_without_explicit_policy_fails_closed():
    from pro_a.cloud_contract import SemanticBackendProvider
    backend = SimpleNamespace(decompose_batch=lambda *a: pytest.fail("Must not dispatch"))
    provider = SemanticBackendProvider(backend, provider_identity="deepseek")
    request = SimpleNamespace(operation_kind=OPERATION_KIND, prompt_identity=operation_contract(OPERATION_KIND))
    with pytest.raises(ProviderFailure, match="PROVIDER_REASONING_POLICY_MISMATCH"):
        provider.invoke(request)


def test_historical_adapter_profile_cannot_normalize_to_v2():
    from pro_a.workbench.cloud_jobs import JobError
    profile = CloudProfile("deepseek", "deepseek-flash", provider_adapter_version="semantic-backend-adapter-v1")
    before = profile.public_identity()
    with pytest.raises(JobError, match="CLOUD_PROFILE_INVALID"):
        profile.validate()
    assert profile.public_identity() == before


def test_policy_changes_frozen_job_intent_and_old_jobs_fail_closed(tmp_path, monkeypatch):
    import pro_a.cloud_contract as contract_module
    from pro_a.cloud_contract import canonical
    from pro_a.workbench.extraction_retry import frozen_cloud
    from pro_a.workbench.source_operations import SourceOperationError
    value = setup_run(tmp_path, monkeypatch)
    row = jobs(value)[0]
    before = copy.deepcopy(row)
    monkeypatch.setattr(contract_module, "STRUCTURED_JSON_REASONING_POLICY_VERSION", "future-policy")
    new = value["service"].jobs.submit(idempotency_key="different-reasoning-policy-0001",
        input_artifact_id=row["input_artifact_id"], operation_kind=SOURCE_ANALYSIS_OPERATION)
    with value["service"].store.connect() as c:
        changed = dict(c.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (new["job"]["job_id"],)).fetchone())
        assert changed["intent_sha256"] != row["intent_sha256"]
        assert changed["prompt_json"] != row["prompt_json"]
        assert changed["prompt_sha256"] == row["prompt_sha256"]
        assert dict(c.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (row["job_id"],)).fetchone()) == before
    legacy = copy.deepcopy(row)
    configuration = CloudProfile("deepseek", "deepseek-flash", provider_adapter_version="semantic-backend-adapter-v1").public_identity()
    legacy.update(provider_adapter_version="source-analysis-piece-adapter-v1",
                  configuration_json=canonical(configuration), configuration_sha256=configuration["configuration_sha256"])
    frozen_before = copy.deepcopy(legacy)
    with pytest.raises(SourceOperationError, match="RETRY_FROZEN_CONFIG_INCOMPLETE"):
        frozen_cloud(legacy)
    assert legacy == frozen_before


def test_reasoning_count_survives_result_artifact_crash_recovery(tmp_path):
    from pro_a.cloud_contract import DeterministicFakeProvider
    from pro_a.workbench.cloud_jobs import CloudJobs, InjectedCrash
    from test_workbench_stage6 import submit
    from workbench_stage6_fixture import stage6_fixture
    fixture = stage6_fixture(tmp_path)
    job_id = submit(fixture)["job"]["job_id"]
    provider = DeterministicFakeProvider()
    with pytest.raises(InjectedCrash):
        fixture["jobs"].run_once(provider, worker_id="reasoning-crash", job_id=job_id,
                                 lease_seconds=0, fault_at="after_result_artifact_durable")
    restarted = CloudJobs(fixture["config"], fixture["profile"])
    assert restarted.reconcile()["reconciled"] == 1
    assert restarted.private_result(job_id)["usage"]["reasoning_tokens"] == 0
    with restarted.store.connect() as c:
        events = [json.loads(r[0]) for r in c.execute("SELECT event_json FROM cloud_job_events WHERE job_id=? AND event_type='PROVIDER_ATTEMPT_COMPLETED'", (job_id,))]
        assert len(events) == 1 and events[0]["reasoning_tokens"] == 0
        assert restarted._verify_event_chain(c, job_id)
    assert restarted.reconcile()["reconciled"] == 0 and provider.call_count == 1
