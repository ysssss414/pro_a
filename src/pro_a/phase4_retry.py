"""Phase 4 transport attempt ownership; no semantic repair or provider routing."""

from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import Callable
from uuid import uuid4

from .config import LLMConfig
from .llm import ChatLLM, LLMError


class RetryPolicy(str, Enum):
    ALLOW_OPERATIONAL = "ALLOW_OPERATIONAL"
    FORBID_SEMANTIC = "FORBID_SEMANTIC"
    FORBID_ALL = "FORBID_ALL"

    def transport_config(self, config: LLMConfig) -> LLMConfig:
        if config.max_retries < 0:
            raise ValueError("NEGATIVE_TRANSPORT_RETRY_BUDGET")
        return replace(config, max_retries=0) if self is self.FORBID_ALL else config


class ExecutionLLM(ChatLLM):
    """Keep the existing HTTP retry loop; record each dispatch before it occurs.

    All Phase 4 policies forbid semantic regeneration/splitting. The first two
    allow only the configured finite transport retry loop. No task-level retry
    wraps that loop, and a completed stage is never regenerated on resume.
    """

    def __init__(self, config: LLMConfig, *, policy: RetryPolicy,
                 emit: Callable[[dict], None], offline: bool = False):
        super().__init__(policy.transport_config(config))
        self.policy = policy
        self.emit = emit
        self.offline = offline
        self.call_id = ""

    def json(self, system: str, user: str) -> dict:
        self.call_id = f"CALL_{uuid4().hex.upper()}"
        self.emit({"call_id": self.call_id, "event": "CALL_STARTED",
                   "owner": "phase4.orchestration", "policy": self.policy.value,
                   "kind": "INITIAL", "reason": "NEXT_UNCOMMITTED_STAGE_TASK",
                   "result_replacement": False})
        if self.offline:
            self.emit({"call_id": self.call_id, "event": "OFFLINE_CALL_BLOCKED"})
            raise LLMError("FROZEN_REPLAY_NETWORK_FORBIDDEN")
        try:
            return super().json(system, user)
        finally:
            self.emit({"call_id": self.call_id, "event": "CALL_FINISHED",
                       "metadata": self.last_call_metadata,
                       "result_replacement": False})

    def _record_attempt(self, attempt_number: int, **kwargs) -> None:
        super()._record_attempt(attempt_number, **kwargs)
        self.emit({"call_id": self.call_id, "event": "TRANSPORT_RESULT",
                   "owner": "ChatLLM.transport", "policy": self.policy.value,
                   "kind": "INITIAL" if attempt_number == 1 else "TRANSPORT_RETRY",
                   "reason": "INITIAL_REQUEST" if attempt_number == 1 else "PRIOR_TRANSIENT_FAILURE",
                   "result_replacement": False, **self._attempt_events[-1]})

    def _sleep_before_retry(self, attempt_number: int) -> None:
        # A durable intent precedes both backoff and the next HTTP dispatch.
        if self.policy is RetryPolicy.FORBID_ALL:
            raise LLMError("FORBIDDEN_TRANSPORT_RETRY")
        self.emit({"call_id": self.call_id, "event": "RETRY_AUTHORIZED",
                   "owner": "ChatLLM.transport", "policy": self.policy.value,
                   "attempt_number": attempt_number + 1,
                   "kind": "TRANSPORT_RETRY", "reason": "PRIOR_TRANSIENT_FAILURE",
                   "result_replacement": False})
        super()._sleep_before_retry(attempt_number)
