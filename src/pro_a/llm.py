from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import LLMConfig


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


class ChatLLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    @property
    def available(self) -> bool:
        return bool(self.cfg.enabled and self.cfg.api_key and self.cfg.base_url and self.cfg.model)

    def json(self, system: str, user: str) -> dict[str, Any]:
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
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.cfg.timeout_seconds)
        if resp.status_code >= 400:
            raise LLMError(f"LLM HTTP {resp.status_code}: {resp.text[:1000]}")
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

        details = _completion_details(data, choice, content)
        if finish_reason == "length":
            raise LLMError(f"LLM output truncated: {details}")
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
        return parsed
