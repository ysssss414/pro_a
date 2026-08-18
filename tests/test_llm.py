from __future__ import annotations

import pytest

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
) -> dict:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content},
            }
        ],
        "model": model,
        "usage": {"completion_tokens": completion_tokens},
    }


def make_llm(monkeypatch, response: FakeResponse, *, max_output_tokens: int = 8192):
    captured = {}

    def fake_post(endpoint, *, headers, json, timeout):
        captured.update(
            endpoint=endpoint,
            headers=headers,
            payload=json,
            timeout=timeout,
        )
        return response

    monkeypatch.setenv("TEST_PROA_LLM_API_KEY", "secret")
    monkeypatch.setattr("pro_a.llm.requests.post", fake_post)
    cfg = LLMConfig(
        enabled=True,
        api_key_env="TEST_PROA_LLM_API_KEY",
        max_output_tokens=max_output_tokens,
    )
    return ChatLLM(cfg), captured


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
    llm, _ = make_llm(
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


def test_stop_with_empty_content_is_reported_explicitly(monkeypatch):
    llm, _ = make_llm(monkeypatch, FakeResponse(completion("  \n")))

    with pytest.raises(LLMError, match="LLM returned empty JSON content"):
        llm.json("Return JSON.", "synthetic input")


def test_stop_with_malformed_json_reports_decode_error(monkeypatch):
    llm, _ = make_llm(monkeypatch, FakeResponse(completion('{"ok":')))

    with pytest.raises(
        LLMError,
        match=r"LLM returned non-JSON content:.*JSONDecodeError.*position",
    ):
        llm.json("Return JSON.", "synthetic input")


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


def test_http_failure_behavior_is_preserved(monkeypatch):
    llm, _ = make_llm(
        monkeypatch,
        FakeResponse({}, status_code=429, text="rate limited"),
    )

    with pytest.raises(LLMError, match="LLM HTTP 429: rate limited"):
        llm.json("Return JSON.", "synthetic input")


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
    llm, _ = make_llm(
        monkeypatch,
        FakeResponse(completion("{}", finish_reason=finish_reason)),
    )

    with pytest.raises(LLMError, match=message):
        llm.json("Return JSON.", "synthetic input")
