from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import LLMConfig


class LLMError(RuntimeError):
    pass


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
        }
        headers = {"Authorization": f"Bearer {self.cfg.api_key}", "Content-Type": "application/json"}
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.cfg.timeout_seconds)
        if resp.status_code >= 400:
            raise LLMError(f"LLM HTTP {resp.status_code}: {resp.text[:1000]}")
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(f"Unexpected LLM response: {data}") from e
        try:
            return _extract_json(content)
        except Exception as e:
            raise LLMError(f"LLM returned non-JSON content: {content[:2000]}") from e
