"""Offline qualification of safe provider failure records."""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest
import requests

from pro_a.cloud_contract import (ADAPTER_VERSION, DeterministicFakeProvider, ProviderFailure,
                                  SemanticBackendProvider,
                                  SOURCE_ANALYSIS_OPERATION, SourceAnalysisPieceProvider)
from pro_a.config import LLMConfig
from pro_a.llm import ChatLLM
from pro_a.provider_diagnostics import build_failure_diagnostic
from pro_a.semantic_decomposition import ChatLLMSemanticBackend
from pro_a.workbench.cloud_jobs import CloudJobs, CloudProfile, InjectedCrash
from workbench_stage6_fixture import stage6_fixture


class Response:
    def __init__(self, payload, status=200, *, headers=None, body="{}", invalid_json=False):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.text = body
        self.content = body.encode()
        self.invalid_json = invalid_json

    def json(self):
        if self.invalid_json:
            raise ValueError("bad JSON")
        return self.payload


def completion(content='{"source_analysis":"ok"}', *, request_id="chatcmpl-synthetic"):
    return {"id": request_id, "model": "deepseek-flash",
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}}


def adapter(monkeypatch, outcome):
    monkeypatch.setenv("STAGE72A_FAKE_KEY", "offline-only")

    def post(*_args, **_kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr("pro_a.llm.requests.post", post)
    llm = ChatLLM(LLMConfig(enabled=True, api_key_env="STAGE72A_FAKE_KEY",
                            model="deepseek-flash", timeout_seconds=60,
                            max_retries=0, max_output_tokens=8192))
    provider = SourceAnalysisPieceProvider(llm, provider_identity="deepseek")
    request = SimpleNamespace(operation_kind=SOURCE_ANALYSIS_OPERATION,
                              requested_model="deepseek-flash", timeout_seconds=60,
                              max_output_tokens=8192,
                              payload={"user_prompt": "Synthetic input only."}, attempt_number=1)
    return provider, request


@pytest.mark.parametrize("name,outcome,stage,error_class,status,retryable,request_id", [
    ("401", Response({"error": {"type": "auth_error", "code": "invalid_key", "request_id": "req-body-401"}}, 401,
                     headers={"x-request-id": "req-header-401"}), "HTTP_RESPONSE", "HTTP_401", 401, False, "req-header-401"),
    ("429", Response({"error": {"type": "rate_limit", "code": "rate_limited"}}, 429,
                     headers={"x-request-id": "req-header-429"}), "HTTP_RESPONSE", "HTTP_429", 429, True, "req-header-429"),
    ("500", Response({}, 500), "HTTP_RESPONSE", "HTTP_500", 500, True, None),
    ("503", Response({}, 503), "HTTP_RESPONSE", "HTTP_503", 503, True, None),
    ("connect_timeout", requests.exceptions.ConnectTimeout("synthetic"), "TRANSPORT", "TRANSPORT_TIMEOUT", None, False, None),
    ("read_timeout", requests.exceptions.ReadTimeout("synthetic"), "TRANSPORT", "TRANSPORT_READ_TIMEOUT", None, False, None),
    ("dns", requests.exceptions.ConnectionError("synthetic"), "TRANSPORT", "TRANSPORT_CONNECT_ERROR", None, False, None),
    ("invalid_json", Response({}, 200, headers={"x-request-id": "req-json-200"}, body="{invalid", invalid_json=True),
     "PROVIDER_PARSE", "RESPONSE_JSON_PARSE_ERROR", 200, False, "req-json-200"),
    ("invalid_envelope", Response({"id": "req-envelope", "unexpected": 1}),
     "PROVIDER_PARSE", "PROVIDER_RESPONSE_SCHEMA_ERROR", 200, False, None),
    ("invalid_model_output", Response(completion("{not-json"),
                                      headers={"x-request-id": "chatcmpl-synthetic"}),
     "MODEL_OUTPUT_PARSE", "OUTPUT_PARSE_ERROR", 200, False, "chatcmpl-synthetic"),
])
def test_http_and_transport_matrix(monkeypatch, name, outcome, stage, error_class,
                                   status, retryable, request_id):
    provider, request = adapter(monkeypatch, outcome)
    with pytest.raises(ProviderFailure) as caught:
        provider.invoke(request)
    failure = caught.value
    diagnostic = build_failure_diagnostic(
        provider="deepseek", model="deepseek-flash", operation_kind=SOURCE_ANALYSIS_OPERATION,
        job_id="JOB_SYNTHETIC", call_id="ATT_SYNTHETIC", attempt_number=1,
        failure_code=failure.code, retryable=failure.retryable, details=failure.diagnostic,
    )
    assert (diagnostic["failure_stage"], diagnostic["error_class"], diagnostic["http_status"],
            diagnostic["retryable"], diagnostic["provider_request_id"]) == (
                stage, error_class, status, retryable, request_id), name
    assert diagnostic["http_response_received"] is (status is not None)
    if name == "401":
        assert (diagnostic["provider_error_type"], diagnostic["provider_error_code"]) == (
            "auth_error", "invalid_key")
        assert diagnostic["provider_error_type_present"] is True
        assert diagnostic["provider_error_code_present"] is True
    assert len(diagnostic["error_fingerprint"]) == 64
    assert diagnostic["safe_error_summary"] and len(diagnostic["safe_error_summary"]) <= 500


def test_success_has_no_failure_diagnostic(monkeypatch):
    provider, request = adapter(monkeypatch, Response(completion(),
                                                     headers={"x-request-id": "chatcmpl-synthetic"}))
    result = provider.invoke(request)
    assert result.provider_request_id == "chatcmpl-synthetic"
    assert result.output == {"source_analysis": "ok"}


def test_durable_output_validation_and_no_failed_body(tmp_path):
    case = stage6_fixture(tmp_path)
    job = case["jobs"].submit(idempotency_key="stage72a-validation",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]

    class SensitiveInvalidProvider(DeterministicFakeProvider):
        def invoke(self, request):
            result = super().invoke(request)
            return result.__class__(**{**result.__dict__, "output": {"SECRET_COMMUNITY_CONTENT": "private"}})

    result = case["jobs"].run_once(SensitiveInvalidProvider(), worker_id="synthetic", job_id=job["job_id"])
    assert result["status"] == "FAILED"
    assert result["failure_diagnostic"]["failure_stage"] == "OUTPUT_VALIDATION"
    assert result["failure_diagnostic"]["error_class"] == "OUTPUT_SCHEMA_VALIDATION_ERROR"
    artifact = case["jobs"].private_result(job["job_id"])
    assert artifact["raw_provider_output"] is None
    assert "SECRET_COMMUNITY_CONTENT" not in json.dumps(artifact)
    assert "SECRET_COMMUNITY_CONTENT" not in case["config"].state_db.read_bytes().decode("utf-8", errors="ignore")


def test_redacted_rejected_artifact_reconciles_without_repeating_call(tmp_path):
    case = stage6_fixture(tmp_path)
    job = case["jobs"].submit(idempotency_key="stage72a-reconcile-rejected",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]
    provider = DeterministicFakeProvider("invalid_output")
    with pytest.raises(InjectedCrash, match="after_result_artifact_durable"):
        case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"],
                              lease_seconds=0, fault_at="after_result_artifact_durable")
    restarted = CloudJobs(case["config"], case["profile"])
    assert restarted.reconcile()["reconciled"] == 1
    result = restarted.get(job["job_id"])
    assert result["status"] == "FAILED"
    assert result["failure_diagnostic"]["failure_stage"] == "OUTPUT_VALIDATION"
    assert provider.call_count == 1


def test_explicit_not_dispatched_failure_records_no_http_request(tmp_path):
    case = stage6_fixture(tmp_path)
    job = case["jobs"].submit(idempotency_key="stage72a-not-dispatched",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]
    result = case["jobs"].run_once(DeterministicFakeProvider("timeout_before_dispatch"),
                                   worker_id="synthetic", job_id=job["job_id"])
    diagnostic = result["failure_diagnostic"]
    assert diagnostic["failure_stage"] == "REQUEST_BUILD"
    assert diagnostic["http_request_sent"] is False
    assert diagnostic["http_response_received"] is False
    assert diagnostic["http_status"] is None


def test_unknown_exception_preserves_baseline_state_and_logs_safe_diagnostic(tmp_path, caplog):
    case = stage6_fixture(tmp_path)
    job = case["jobs"].submit(idempotency_key="stage72a-unknown",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]
    secret = "Authorization: Bearer SECRET_TEST_TOKEN api_key=SECRET_API_KEY cookie=SECRET_COOKIE private_source_text=SECRET_COMMUNITY_CONTENT"

    class UnknownProvider(DeterministicFakeProvider):
        def invoke(self, request):
            error = RuntimeError(secret)
            error.request_id = "req-exception-unknown"
            raise error

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError) as caught:
            case["jobs"].run_once(UnknownProvider(), worker_id="synthetic", job_id=job["job_id"])
    assert caught.value.args == (secret,)
    result = case["jobs"].get(job["job_id"])
    assert result["status"] == "RUNNING"
    assert result["failure_diagnostic"] is None
    assert '"error_class": "UNKNOWN_PROVIDER_ERROR"' in caplog.text
    with sqlite3.connect(case["config"].state_db) as db:
        rows = db.execute("SELECT event_json FROM cloud_job_events WHERE job_id=?", (job["job_id"],)).fetchall()
        outcomes = db.execute("SELECT provider_request_id FROM cloud_attempt_outcomes").fetchall()
    assert outcomes == []
    assert result["provider_request_id"] is None
    disclosed = json.dumps(result) + json.dumps(rows) + caplog.text
    for marker in ("SECRET_TEST_TOKEN", "SECRET_API_KEY", "SECRET_COOKIE", "SECRET_COMMUNITY_CONTENT"):
        assert marker not in disclosed


def test_http_failure_is_durable_without_provider_body(tmp_path, monkeypatch, caplog):
    profile = CloudProfile("deepseek", "deepseek-flash", (), ADAPTER_VERSION,
                           60, 8192, 1, 1, 20000)
    case = stage6_fixture(tmp_path, profile=profile)
    job = case["jobs"].submit(idempotency_key="stage72a-http-failure",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]
    secret = "Authorization: Bearer SECRET_TEST_TOKEN api_key=SECRET_API_KEY cookie=SECRET_COOKIE private_source_text=SECRET_COMMUNITY_CONTENT"
    _, _ = adapter(monkeypatch, Response({"error": {"type": "auth_error", "code": "invalid_key"}},
                                       401, headers={"x-request-id": "req-safe-401"}, body=secret))
    llm = ChatLLM(LLMConfig(enabled=True, api_key_env="STAGE72A_FAKE_KEY",
                            model="deepseek-flash", timeout_seconds=60,
                            max_retries=0, max_output_tokens=8192))
    provider = SemanticBackendProvider(ChatLLMSemanticBackend(llm), provider_identity="deepseek")
    with caplog.at_level(logging.DEBUG):
        result = case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"])
    assert result["status"] == "FAILED"
    diagnostic = result["failure_diagnostic"]
    assert (diagnostic["failure_stage"], diagnostic["error_class"], diagnostic["http_status"],
            diagnostic["provider_request_id"], diagnostic["retryable"]) == (
                "HTTP_RESPONSE", "HTTP_401", 401, "req-safe-401", False)
    with sqlite3.connect(case["config"].state_db) as db:
        request_id = db.execute("SELECT provider_request_id FROM cloud_attempt_outcomes").fetchone()[0]
    assert request_id == result["provider_request_id"] == "req-safe-401"
    disclosed = case["config"].state_db.read_bytes().decode("utf-8", errors="ignore") + caplog.text
    for marker in ("SECRET_TEST_TOKEN", "SECRET_API_KEY", "SECRET_COOKIE", "SECRET_COMMUNITY_CONTENT"):
        assert marker not in disclosed


def test_real_adapter_output_rejection_retains_http_200_without_body(tmp_path, monkeypatch):
    profile = CloudProfile("deepseek", "deepseek-flash", (), ADAPTER_VERSION,
                           60, 8192, 1, 1, 20000)
    case = stage6_fixture(tmp_path, profile=profile)
    job = case["jobs"].submit(idempotency_key="stage72a-http-output-rejected",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]
    adapter(monkeypatch, Response(completion('{"SECRET_COMMUNITY_CONTENT":"private"}',
                                                 request_id="chatcmpl-output-rejected"),
                                  headers={"x-request-id": "chatcmpl-output-rejected"}))
    llm = ChatLLM(LLMConfig(enabled=True, api_key_env="STAGE72A_FAKE_KEY",
                            model="deepseek-flash", timeout_seconds=60,
                            max_retries=0, max_output_tokens=8192))
    provider = SemanticBackendProvider(ChatLLMSemanticBackend(llm), provider_identity="deepseek")
    result = case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"])
    assert result["status"] == "FAILED"
    diagnostic = result["failure_diagnostic"]
    assert (diagnostic["failure_stage"], diagnostic["error_class"],
            diagnostic["http_status"], diagnostic["provider_request_id"]) == (
                "OUTPUT_VALIDATION", "OUTPUT_SCHEMA_VALIDATION_ERROR", 200,
                "chatcmpl-output-rejected")
    assert diagnostic["http_response_received"] is True
    assert case["jobs"].private_result(job["job_id"])["raw_provider_output"] is None
    assert "SECRET_COMMUNITY_CONTENT" not in case["config"].state_db.read_bytes().decode("utf-8", errors="ignore")


def test_fingerprint_clusters_same_failure_without_request_identity():
    common = dict(provider="deepseek", model="deepseek-flash", operation_kind=SOURCE_ANALYSIS_OPERATION,
                  job_id="JOB_1", call_id="ATT_1", attempt_number=1,
                  failure_code="RATE_LIMITED", retryable=True)
    first = build_failure_diagnostic(**common, details={"failure_stage": "HTTP_RESPONSE", "error_class": "HTTP_429",
                                                       "http_status": 429, "provider_request_id": "req-one"})
    second = build_failure_diagnostic(**{**common, "job_id": "JOB_2", "call_id": "ATT_2"},
                                      details={"failure_stage": "HTTP_RESPONSE", "error_class": "HTTP_429",
                                               "http_status": 429, "provider_request_id": "req-two"})
    assert first["error_fingerprint"] == second["error_fingerprint"]


def test_untrusted_identifier_fields_are_dropped():
    diagnostic = build_failure_diagnostic(
        provider="deepseek", model="deepseek-flash", operation_kind=SOURCE_ANALYSIS_OPERATION,
        job_id="JOB_SYNTHETIC", call_id="ATT_SYNTHETIC", attempt_number=1,
        failure_code="PROVIDER_ERROR", retryable=False,
        details={"failure_stage": "HTTP_RESPONSE", "error_class": "HTTP_401",
                 "http_status": 401, "provider_request_id": "SECRET_TEST_TOKEN",
                 "provider_error_type": "SECRET_COMMUNITY_CONTENT",
                 "provider_error_code": "SECRET_API_KEY"},
    )
    assert diagnostic["provider_request_id"] is None
    assert diagnostic["provider_error_type"] is None
    assert diagnostic["provider_error_code"] is None
    assert "SECRET" not in json.dumps(diagnostic)


def _semantic_job(tmp_path, monkeypatch, outcome):
    profile = CloudProfile("deepseek", "deepseek-flash", (), ADAPTER_VERSION,
                           60, 8192, 1, 1, 20000)
    case = stage6_fixture(tmp_path, profile=profile)
    job = case["jobs"].submit(idempotency_key="stage72a-r1-synthetic",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]
    adapter(monkeypatch, outcome)
    llm = ChatLLM(LLMConfig(enabled=True, api_key_env="STAGE72A_FAKE_KEY",
                            model="deepseek-flash", timeout_seconds=60,
                            max_retries=0, max_output_tokens=8192))
    provider = SemanticBackendProvider(ChatLLMSemanticBackend(llm), provider_identity="deepseek")
    return case, job, provider


def test_http_401_diagnostic_parser_failure_preserves_auth_state(tmp_path, monkeypatch):
    class BrokenJson(Response):
        def json(self):
            raise RuntimeError("SECRET_TEST_TOKEN")

    case, job, provider = _semantic_job(
        tmp_path, monkeypatch,
        BrokenJson({}, 401, headers={"x-request-id": "req-r1-auth"}, body="unauthorized"),
    )
    result = case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"])
    assert (result["status"], result["last_error"]) == ("FAILED", "AUTHENTICATION_ERROR")
    diagnostic = result["failure_diagnostic"]
    assert (diagnostic["http_status"], diagnostic["failure_stage"],
            diagnostic["error_class"], diagnostic["provider_request_id"],
            diagnostic["retryable"]) == (401, "HTTP_RESPONSE", "HTTP_401", "req-r1-auth", False)
    assert b"SECRET_TEST_TOKEN" not in case["config"].state_db.read_bytes()


@pytest.mark.parametrize("outcome,stage", [
    (Response({}, 200, invalid_json=True), "PROVIDER_PARSE"),
    (Response(completion("{not-json")), "MODEL_OUTPUT_PARSE"),
    (Response(completion('{"unexpected":true}')), "OUTPUT_VALIDATION"),
])
def test_http_200_context_survives_later_failure(tmp_path, monkeypatch, outcome, stage):
    case, job, provider = _semantic_job(tmp_path, monkeypatch, outcome)
    result = case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"])
    assert result["status"] == "FAILED"
    assert result["failure_diagnostic"]["http_status"] == 200
    assert result["failure_diagnostic"]["failure_stage"] == stage


def test_http_200_context_survives_durable_artifact_recovery(tmp_path, monkeypatch):
    outcome = Response(completion('{"unexpected":true}', request_id="SECRET_API_KEY"),
                       headers={"x-request-id": "req-r1-recovery"})
    case, job, provider = _semantic_job(tmp_path, monkeypatch, outcome)
    with pytest.raises(InjectedCrash, match="after_result_artifact_durable"):
        case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"],
                              lease_seconds=0, fault_at="after_result_artifact_durable")
    restarted = CloudJobs(case["config"], case["profile"])
    assert restarted.reconcile()["reconciled"] == 1
    result = restarted.get(job["job_id"])
    assert result["status"] == "FAILED"
    assert (result["failure_diagnostic"]["http_status"],
            result["failure_diagnostic"]["provider_request_id"]) == (200, "req-r1-recovery")
    assert b"SECRET_API_KEY" not in case["config"].state_db.read_bytes()
    assert "SECRET_API_KEY" not in json.dumps(restarted.private_result(job["job_id"]))


def test_untrusted_response_identity_is_absent_from_failed_surfaces(tmp_path, monkeypatch, caplog):
    markers = ("SECRET_TEST_TOKEN", "SECRET_API_KEY", "SECRET_COOKIE", "SECRET_COMMUNITY_CONTENT")
    outcome = Response(completion('{"SECRET_COMMUNITY_CONTENT":"private"}',
                                  request_id="SECRET_API_KEY"),
                       headers={"x-request-id": "req-SECRET_TEST_TOKEN",
                                "set-cookie": "SECRET_COOKIE"})
    case, job, provider = _semantic_job(tmp_path, monkeypatch, outcome)
    with caplog.at_level(logging.DEBUG):
        result = case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"])
    assert result["status"] == "FAILED"
    assert result["provider_request_id"] is None
    assert result["failure_diagnostic"]["provider_request_id"] is None
    disclosed = (case["config"].state_db.read_bytes().decode("utf-8", errors="ignore")
                 + json.dumps(result) + json.dumps(case["jobs"].private_result(job["job_id"]))
                 + caplog.text)
    assert all(marker not in disclosed for marker in markers)


def test_untrusted_provider_error_and_nested_transport_metadata_are_absent(tmp_path, monkeypatch, caplog):
    marker = "SECRET_TEST_TOKEN"
    response = Response({"error": {"type": "SECRET_API_KEY", "code": "SECRET_COOKIE",
                                   "nested": {"token": "SECRET_COMMUNITY_CONTENT"}}},
                        401, headers={"x-request-id": "req-SECRET_TEST_TOKEN"}, body=marker)
    case, job, provider = _semantic_job(tmp_path / "http", monkeypatch, response)
    with caplog.at_level(logging.DEBUG):
        result = case["jobs"].run_once(provider, worker_id="synthetic", job_id=job["job_id"])
    assert result["last_error"] == "AUTHENTICATION_ERROR"
    assert result["failure_diagnostic"]["provider_error_type"] is None
    assert result["failure_diagnostic"]["provider_error_code"] is None
    assert result["failure_diagnostic"]["provider_request_id"] is None
    error = requests.exceptions.ConnectionError(marker)
    error.metadata = {"nested": {"cookie": "SECRET_COOKIE"}}
    other, other_job, other_provider = _semantic_job(tmp_path / "transport", monkeypatch, error)
    with caplog.at_level(logging.DEBUG):
        transport = other["jobs"].run_once(other_provider, worker_id="synthetic",
                                            job_id=other_job["job_id"])
    assert transport["status"] == "RECOVERY_REQUIRED"
    assert transport["failure_diagnostic"]["http_status"] is None
    disclosed = (case["config"].state_db.read_bytes().decode("utf-8", errors="ignore")
                 + other["config"].state_db.read_bytes().decode("utf-8", errors="ignore")
                 + json.dumps(result) + json.dumps(transport) + caplog.text)
    assert all(value not in disclosed for value in
               (marker, "SECRET_API_KEY", "SECRET_COOKIE", "SECRET_COMMUNITY_CONTENT"))


def test_completion_id_alone_is_not_request_id(monkeypatch):
    provider, request = adapter(monkeypatch, Response(completion(request_id="req-completion-only")))
    assert provider.invoke(request).provider_request_id is None


def test_all_provider_result_strings_are_sanitized_before_failure_persistence(tmp_path, caplog):
    case = stage6_fixture(tmp_path)
    job = case["jobs"].submit(idempotency_key="stage72a-r1-result-taint",
                              input_artifact_id=case["artifact_id"],
                              operation_kind="SEMANTIC_DECOMPOSITION")["job"]

    class TaintedResult(DeterministicFakeProvider):
        def invoke(self, request):
            result = super().invoke(request)
            return replace(result, provider="SECRET_TEST_TOKEN",
                           requested_model="SECRET_API_KEY",
                           provider_reported_model="SECRET_COOKIE",
                           provider_request_id="req-SECRET_COMMUNITY_CONTENT",
                           started_at="SECRET_TEST_TOKEN", ended_at="SECRET_API_KEY",
                           latency_ms="SECRET_COOKIE", finish_reason="SECRET_COMMUNITY_CONTENT")

    with caplog.at_level(logging.DEBUG):
        result = case["jobs"].run_once(TaintedResult(), worker_id="synthetic", job_id=job["job_id"])
    assert (result["status"], result["last_error"]) == ("FAILED", "PROVIDER_IDENTITY_MISMATCH")
    disclosed = (case["config"].state_db.read_bytes().decode("utf-8", errors="ignore")
                 + json.dumps(result) + json.dumps(case["jobs"].private_result(job["job_id"]))
                 + caplog.text)
    assert all(marker not in disclosed for marker in
               ("SECRET_TEST_TOKEN", "SECRET_API_KEY", "SECRET_COOKIE", "SECRET_COMMUNITY_CONTENT"))
