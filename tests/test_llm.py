from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from pro_a.config import LLMConfig
from pro_a.llm import ChatLLM, LLMError


class FakeResponse:
    def __init__(self, payload, *, status_code: int = 200, text: str = ""):
        self.payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.payload


def completion(
    content: str,
    *,
    finish_reason: str = "stop",
    model: str = "deepseek-chat",
    completion_tokens: int = 3,
    prompt_tokens: int | None = None,
) -> dict:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content},
            }
        ],
        "model": model,
        "usage": {
            "completion_tokens": completion_tokens,
            **({"prompt_tokens": prompt_tokens} if prompt_tokens is not None else {}),
        },
    }


def make_llm(
    monkeypatch,
    outcomes,
    *,
    max_output_tokens: int | None = None,
):
    if not isinstance(outcomes, list):
        outcomes = [outcomes]
    captured = {"calls": []}

    def fake_post(endpoint, *, headers, json, timeout):
        captured["calls"].append(
            {
                "endpoint": endpoint,
                "headers": headers,
                "payload": json,
                "timeout": timeout,
            }
        )
        captured.update(
            endpoint=endpoint,
            headers=headers,
            payload=json,
            timeout=timeout,
        )
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setenv("TEST_PROA_LLM_API_KEY", "secret")
    monkeypatch.setattr("pro_a.llm.requests.post", fake_post)
    config_overrides = {}
    if max_output_tokens is not None:
        config_overrides["max_output_tokens"] = max_output_tokens
    cfg = LLMConfig(
        enabled=True,
        api_key_env="TEST_PROA_LLM_API_KEY",
        **config_overrides,
    )
    return ChatLLM(cfg), captured


def test_default_max_output_tokens_is_32768():
    assert LLMConfig().max_output_tokens == 32768


def test_json_request_uses_default_max_tokens(monkeypatch):
    llm, captured = make_llm(
        monkeypatch,
        FakeResponse(completion('{"ok": true}')),
    )

    llm.json("Return JSON.", "synthetic input")

    assert captured["payload"]["max_tokens"] == 32768


def test_json_returns_dict_for_stop_and_valid_json(monkeypatch):
    llm, _ = make_llm(monkeypatch, FakeResponse(completion('{"ok": true}')))

    assert llm.json("Return JSON.", "synthetic input") == {"ok": True}


def test_json_request_enforces_json_output_and_max_tokens(monkeypatch):
    llm, captured = make_llm(
        monkeypatch,
        FakeResponse(completion('{"ok": true}')),
        max_output_tokens=4321,
    )

    llm.json("Return JSON.", "synthetic input")

    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["max_tokens"] == 4321


def test_length_is_reported_as_truncation_before_parse(monkeypatch):
    llm, captured = make_llm(
        monkeypatch,
        FakeResponse(
            completion(
                '{"ok"',
                finish_reason="length",
                completion_tokens=8192,
            )
        ),
    )

    def fail_if_parsed(_content):
        raise AssertionError("partial JSON must not reach the parser")

    monkeypatch.setattr("pro_a.llm._extract_json", fail_if_parsed)

    with pytest.raises(
        LLMError,
        match=r"LLM output truncated: finish_reason=length.*completion_tokens=8192",
    ):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 1


def test_run_003_length_completion_records_parseability_tail_and_limits(monkeypatch):
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "run_003_infrastructure_failures.json").read_text(
            encoding="utf-8"
        )
    )["length_case"]
    partial = '{"node_matches": [{"node_id": "NODE_X"}'
    llm, captured = make_llm(
        monkeypatch,
        FakeResponse(completion(
            partial,
            finish_reason=fixture["finish_reason"],
            completion_tokens=fixture["completion_tokens"],
            prompt_tokens=fixture["prompt_tokens"],
        )),
        max_output_tokens=fixture["configured_max_tokens"],
    )

    with pytest.raises(LLMError, match="failure_category=output_truncation"):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 1
    attempt = llm.last_call_metadata["attempts"][0]
    assert attempt["finish_reason"] == "length"
    assert attempt["prompt_tokens"] == fixture["prompt_tokens"]
    assert attempt["completion_tokens"] == fixture["completion_tokens"]
    assert attempt["max_tokens"] == fixture["configured_max_tokens"]
    assert attempt["raw_response_syntactically_parseable"] is False
    assert attempt["content_tail"] == partial
    assert attempt["result"] == "output_truncation"


def test_stop_with_empty_content_is_reported_explicitly(monkeypatch):
    llm, captured = make_llm(monkeypatch, FakeResponse(completion("  \n")))

    with pytest.raises(LLMError, match="LLM returned empty JSON content"):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 1


def test_stop_with_malformed_json_reports_decode_error(monkeypatch):
    llm, captured = make_llm(monkeypatch, FakeResponse(completion('{"ok":')))

    with pytest.raises(
        LLMError,
        match=r"LLM returned non-JSON content:.*JSONDecodeError.*position",
    ):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": [{"finish_reason": "stop"}]},
        {"choices": [{"finish_reason": "stop", "message": {}}]},
    ],
)
def test_missing_completion_shape_is_unexpected(monkeypatch, payload):
    llm, _ = make_llm(monkeypatch, FakeResponse(payload))

    with pytest.raises(LLMError, match="Unexpected LLM response"):
        llm.json("Return JSON.", "synthetic input")


def test_connection_error_then_success(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr("pro_a.llm.time.sleep", sleep_calls.append)
    llm, captured = make_llm(
        monkeypatch,
        [
            requests.exceptions.ConnectionError("connection aborted"),
            FakeResponse(completion('{"ok": true}')),
        ],
    )

    assert llm.json("Return JSON.", "synthetic input") == {"ok": True}
    assert len(captured["calls"]) == 2
    assert sleep_calls == [2.0]
    assert llm.last_call_metadata["attempts_used"] == 2
    first_attempt = llm.last_call_metadata["attempts"][0]
    assert first_attempt["attempt_number"] == 1
    assert first_attempt["max_attempts"] == 3
    assert first_attempt["exception_class"] == "ConnectionError"
    assert first_attempt["requested_model"] == "deepseek-chat"
    assert first_attempt["max_tokens"] == 32768
    assert first_attempt["will_retry"] is True
    assert llm.last_call_metadata["attempts"][1]["http_status"] == 200


def test_two_ssl_errors_then_success(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr("pro_a.llm.time.sleep", sleep_calls.append)
    llm, captured = make_llm(
        monkeypatch,
        [
            requests.exceptions.SSLError("first"),
            requests.exceptions.SSLError("second"),
            FakeResponse(completion('{"ok": true}')),
        ],
    )

    assert llm.json("Return JSON.", "synthetic input") == {"ok": True}
    assert len(captured["calls"]) == 3
    assert sleep_calls == [2.0, 4.0]
    assert llm.last_call_metadata["attempts_used"] == 3


def test_timeout_exhaustion_reports_attempts(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr("pro_a.llm.time.sleep", sleep_calls.append)
    llm, captured = make_llm(
        monkeypatch,
        [
            requests.exceptions.Timeout("first"),
            requests.exceptions.Timeout("second"),
            requests.exceptions.Timeout("third"),
        ],
    )

    with pytest.raises(
        LLMError,
        match=r"failure_category=transport; attempts=3; final_exception_class=Timeout",
    ):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 3
    assert sleep_calls == [2.0, 4.0]


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_retryable_http_status_then_success(monkeypatch, status_code):
    sleep_calls = []
    monkeypatch.setattr("pro_a.llm.time.sleep", sleep_calls.append)
    llm, captured = make_llm(
        monkeypatch,
        [
            FakeResponse({}, status_code=status_code, text="retryable"),
            FakeResponse(completion('{"ok": true}')),
        ],
    )

    assert llm.json("Return JSON.", "synthetic input") == {"ok": True}
    assert len(captured["calls"]) == 2
    assert sleep_calls == [2.0]
    assert llm.last_call_metadata["attempts"][0]["http_status"] == status_code


def test_retryable_http_exhaustion_reports_final_status(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr("pro_a.llm.time.sleep", sleep_calls.append)
    llm, captured = make_llm(
        monkeypatch,
        [
            FakeResponse({}, status_code=503, text="unavailable"),
            FakeResponse({}, status_code=503, text="unavailable"),
            FakeResponse({}, status_code=503, text="unavailable"),
        ],
    )

    with pytest.raises(
        LLMError,
        match=r"failure_category=http_status; attempts=3; final_status=503",
    ):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 3
    assert sleep_calls == [2.0, 4.0]


@pytest.mark.parametrize("status_code", [400, 401, 402, 422])
def test_non_retryable_http_status_is_attempted_once(monkeypatch, status_code):
    llm, captured = make_llm(
        monkeypatch,
        FakeResponse({}, status_code=status_code, text="not retryable"),
    )

    with pytest.raises(LLMError, match=rf"LLM HTTP {status_code}: not retryable"):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 1


def test_fenced_json_remains_backward_compatible(monkeypatch):
    llm, _ = make_llm(
        monkeypatch,
        FakeResponse(completion('```json\n{"ok": true}\n```')),
    )

    assert llm.json("Return JSON.", "synthetic input") == {"ok": True}


@pytest.mark.parametrize(
    ("finish_reason", "message"),
    [
        ("content_filter", "LLM JSON output blocked"),
        ("insufficient_system_resource", "LLM JSON output interrupted"),
        ("tool_calls", "LLM returned tool calls instead of JSON content"),
        ("other", "Unexpected LLM finish_reason"),
    ],
)
def test_non_stop_finish_reasons_are_distinguished(
    monkeypatch,
    finish_reason,
    message,
):
    llm, captured = make_llm(
        monkeypatch,
        FakeResponse(completion("{}", finish_reason=finish_reason)),
    )

    with pytest.raises(LLMError, match=message):
        llm.json("Return JSON.", "synthetic input")

    assert len(captured["calls"]) == 1
