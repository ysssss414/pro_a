from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any

import requests

from .config import LLMConfig


logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 503}
_RETRYABLE_EXCEPTIONS = (
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


class LLMError(RuntimeError):
    pass


def _completion_details(data: dict[str, Any], choice: dict[str, Any], content: str) -> str:
    usage = data.get("usage")
    completion_tokens = usage.get("completion_tokens", "unknown") if isinstance(usage, dict) else "unknown"
    return (
        f"finish_reason={choice['finish_reason']}; "
        f"model={data.get('model', 'unknown')}; "
        f"completion_tokens={completion_tokens}; "
        f"content_length={len(content)}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _raw_json_syntax(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.I)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return {
            "raw_response_syntactically_parseable": False,
            "raw_response_json_error": exc.msg,
            "raw_response_json_error_position": exc.pos,
        }
    return {
        "raw_response_syntactically_parseable": True,
        "raw_response_json_type": type(parsed).__name__,
    }


class ChatLLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self._attempt_events: list[dict[str, Any]] = []

    @property
    def last_call_metadata(self) -> dict[str, Any]:
        return {
            "attempts_used": len(self._attempt_events),
            "max_attempts": 1 + self.cfg.max_retries,
            "attempts": [dict(event) for event in self._attempt_events],
        }

    @property
    def available(self) -> bool:
        return bool(self.cfg.enabled and self.cfg.api_key and self.cfg.base_url and self.cfg.model)

    def _record_attempt(
        self,
        attempt_number: int,
        *,
        http_status: int | None = None,
        exception_class: str | None = None,
        will_retry: bool = False,
    ) -> None:
        event = {
            "attempt_number": attempt_number,
            "max_attempts": 1 + self.cfg.max_retries,
            "requested_model": self.cfg.model,
            "max_tokens": self.cfg.max_output_tokens,
            "http_status": http_status,
            "exception_class": exception_class,
            "will_retry": will_retry,
        }
        self._attempt_events.append(event)
        log = logger.warning if will_retry else logger.info
        log(
            "LLM attempt: attempt_number=%s max_attempts=%s "
            "exception_class=%s http_status=%s requested_model=%s max_tokens=%s "
            "will_retry=%s",
            attempt_number,
            event["max_attempts"],
            exception_class,
            http_status,
            self.cfg.model,
            self.cfg.max_output_tokens,
            will_retry,
        )

    def _sleep_before_retry(self, attempt_number: int) -> None:
        time.sleep(self.cfg.retry_backoff_seconds * (2 ** (attempt_number - 1)))

    def json(self, system: str, user: str) -> dict[str, Any]:
        self._attempt_events = []
        if not self.available:
            raise LLMError("LLM is disabled or API key is missing")
        endpoint = self.cfg.base_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.cfg.temperature,
            "response_format": {"type": "json_object"},
            "max_tokens": self.cfg.max_output_tokens,
        }
        headers = {"Authorization": f"Bearer {self.cfg.api_key}", "Content-Type": "application/json"}
        max_attempts = 1 + self.cfg.max_retries
        for attempt_number in range(1, max_attempts + 1):
            try:
                resp = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.cfg.timeout_seconds,
                )
            except _RETRYABLE_EXCEPTIONS as e:
                will_retry = attempt_number < max_attempts
                self._record_attempt(
                    attempt_number,
                    exception_class=type(e).__name__,
                    will_retry=will_retry,
                )
                if will_retry:
                    self._sleep_before_retry(attempt_number)
                    continue
                raise LLMError(
                    "LLM transport failure: failure_category=transport; "
                    f"attempts={attempt_number}; final_exception_class={type(e).__name__}: {e}"
                ) from e

            will_retry = (
                resp.status_code in _RETRYABLE_STATUS_CODES
                and attempt_number < max_attempts
            )
            self._record_attempt(
                attempt_number,
                http_status=resp.status_code,
                will_retry=will_retry,
            )
            if will_retry:
                self._sleep_before_retry(attempt_number)
                continue
            if resp.status_code in _RETRYABLE_STATUS_CODES:
                raise LLMError(
                    "LLM HTTP retry exhausted: failure_category=http_status; "
                    f"attempts={attempt_number}; final_status={resp.status_code}: {resp.text[:1000]}"
                )
            if resp.status_code >= 400:
                raise LLMError(f"LLM HTTP {resp.status_code}: {resp.text[:1000]}")
            break

        try:
            data = resp.json()
        except ValueError as e:
            raise LLMError(f"Unexpected LLM response: invalid JSON body: {resp.text[:1000]}") from e
        try:
            choice = data["choices"][0]
            finish_reason = choice["finish_reason"]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Unexpected LLM response: {data}") from e

        if not isinstance(content, str):
            raise LLMError(f"Unexpected LLM response: {data}")

        usage = data.get("usage")
        self._attempt_events[-1].update(
            response_model=data.get("model"),
            finish_reason=finish_reason,
            prompt_tokens=(
                usage.get("prompt_tokens") if isinstance(usage, dict) else None
            ),
            completion_tokens=(
                usage.get("completion_tokens") if isinstance(usage, dict) else None
            ),
            total_tokens=(
                usage.get("total_tokens") if isinstance(usage, dict) else None
            ),
            content_length=len(content),
            content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            **_raw_json_syntax(content),
        )

        details = _completion_details(data, choice, content)
        if finish_reason == "length":
            self._attempt_events[-1].update(
                result="output_truncation",
                content_tail=content[-500:],
            )
            syntax = self._attempt_events[-1]
            raise LLMError(
                f"LLM output truncated: {details}; "
                "failure_category=output_truncation; "
                f"configured_max_tokens={self.cfg.max_output_tokens}; "
                "raw_response_syntactically_parseable="
                f"{syntax['raw_response_syntactically_parseable']}; "
                f"content_tail={json.dumps(content[-500:], ensure_ascii=False)}"
            )
        if finish_reason == "content_filter":
            raise LLMError(f"LLM JSON output blocked: {details}")
        if finish_reason == "insufficient_system_resource":
            raise LLMError(f"LLM JSON output interrupted: {details}")
        if finish_reason == "tool_calls":
            raise LLMError(f"LLM returned tool calls instead of JSON content: {details}")
        if finish_reason != "stop":
            raise LLMError(f"Unexpected LLM finish_reason: {details}")
        if not content.strip():
            raise LLMError(f"LLM returned empty JSON content: {details}")

        try:
            parsed = _extract_json(content)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"LLM returned non-JSON content: {details}; "
                f"JSONDecodeError: {e.msg} at position {e.pos}; "
                f"content={content[:2000]}"
            ) from e
        if not isinstance(parsed, dict):
            raise LLMError(f"LLM returned non-object JSON content: {details}")
        self._attempt_events[-1]["result"] = "success"
        return parsed
