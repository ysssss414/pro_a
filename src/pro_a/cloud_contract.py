"""Provider-neutral Stage 6 contract over the existing semantic backend."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from .analyzer import canonicalize_text
from .llm import ChatLLM, LLMError
from .prompts import SOURCE_ANALYSIS_SYSTEM, SOURCE_ANALYSIS_USER
from .semantic_decomposition import (
    MODEL_RESULT_FIELDS,
    MODEL_UNIT_FIELDS,
    SEMANTIC_DECOMPOSITION_SYSTEM,
    SEMANTIC_DECOMPOSITION_USER,
    SemanticBackend,
    normalize_model_result,
    semantic_prompt_sha256,
)


CONTRACT_VERSION = "cloud-inference-v1"
OPERATION_KIND = "SEMANTIC_DECOMPOSITION"
SOURCE_ANALYSIS_OPERATION = "SOURCE_ANALYSIS_PIECE"
OPERATION_KINDS = (OPERATION_KIND, SOURCE_ANALYSIS_OPERATION)
RETRY_OWNER = "DURABLE_CLOUD_WORKER"
RETRY_POLICY_ID = "stage6-operational-retry-v1"
PROMPT_ID = "semantic-decomposition"
PROMPT_VERSION = "2.1"
ADAPTER_VERSION = "semantic-backend-adapter-v1"
SOURCE_ANALYSIS_ADAPTER_VERSION = "source-analysis-piece-adapter-v1"
USAGE_STATUSES = ("KNOWN", "UNKNOWN")
OUTCOME_STATUSES = ("NOT_DISPATCHED", "KNOWN_FAILURE", "UNKNOWN")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def operation_contract(operation_kind: str) -> dict[str, Any]:
    if operation_kind == OPERATION_KIND:
        combined = hashlib.sha256(
            (SEMANTIC_DECOMPOSITION_SYSTEM + "\0" + SEMANTIC_DECOMPOSITION_USER).encode("utf-8")
        ).hexdigest()
        return {
            "operation_kind": OPERATION_KIND,
            "operation_schema_version": "semantic-decomposition-result-v2.1",
            "prompt_id": PROMPT_ID,
            "prompt_version": PROMPT_VERSION,
            "system_prompt_sha256": semantic_prompt_sha256(),
            "prompt_bundle_sha256": combined,
            "validator": "existing-proposition-ir-v2.1",
        }
    if operation_kind == SOURCE_ANALYSIS_OPERATION:
        system_sha = hashlib.sha256(SOURCE_ANALYSIS_SYSTEM.encode("utf-8")).hexdigest()
        combined = hashlib.sha256(
            (SOURCE_ANALYSIS_SYSTEM + "\0" + SOURCE_ANALYSIS_USER).encode("utf-8")
        ).hexdigest()
        return {
            "operation_kind": SOURCE_ANALYSIS_OPERATION,
            "operation_schema_version": "source-analysis-piece-v1",
            "prompt_id": "source-analysis-piece",
            "prompt_version": "phase3e2sl6",
            "system_prompt_sha256": system_sha,
            "prompt_bundle_sha256": combined,
            "validator": "bounded-source-analysis-piece-v1+native-analyzer-replay",
        }
    raise CloudContractError("UNSUPPORTED_CLOUD_OPERATION", 422)


class CloudContractError(RuntimeError):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.status = status


class ProviderFailure(RuntimeError):
    """A bounded failure. private_detail must never enter job state or public DTOs."""

    def __init__(self, code: str, *, retryable: bool, external_outcome: str,
                 private_detail: str = "", diagnostic: Mapping[str, Any] | None = None):
        if external_outcome not in OUTCOME_STATUSES:
            raise ValueError("INVALID_EXTERNAL_OUTCOME")
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.external_outcome = external_outcome
        self.private_detail = private_detail
        self.diagnostic = dict(diagnostic or {})


def _llm_provider_failure(error: LLMError, metadata: Mapping[str, Any]) -> ProviderFailure:
    attempts = list(metadata.get("attempts") or [])
    last = attempts[-1] if attempts else {}
    status = last.get("http_status")
    if status == 429:
        code, retryable, external = "RATE_LIMITED", True, "KNOWN_FAILURE"
    elif status in (500, 503):
        code, retryable, external = "PROVIDER_UNAVAILABLE", True, "KNOWN_FAILURE"
    elif status in (401, 403):
        code, retryable, external = "AUTHENTICATION_ERROR", False, "KNOWN_FAILURE"
    elif "transport failure" in str(error):
        code, retryable, external = "UNKNOWN_EXTERNAL_OUTCOME", False, "UNKNOWN"
    else:
        code, retryable, external = "PROVIDER_ERROR", False, "KNOWN_FAILURE"
    return ProviderFailure(code, retryable=retryable, external_outcome=external,
                           diagnostic=last)


@dataclass(frozen=True)
class CloudRequest:
    job_id: str
    attempt_id: str
    attempt_number: int
    operation_kind: str
    input_artifact_id: str
    input_sha256: str
    source_id: str
    runtime_identity: Mapping[str, Any]
    schema_version: str
    provider: str
    requested_model: str
    prompt_identity: Mapping[str, Any]
    configuration_identity: Mapping[str, Any]
    timeout_seconds: int
    max_output_tokens: int
    retry_policy_id: str
    budget_identity: Mapping[str, Any]
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.operation_kind not in OPERATION_KINDS:
            raise CloudContractError("UNSUPPORTED_CLOUD_OPERATION", 422)
        if self.attempt_number < 1 or self.timeout_seconds < 1 or self.max_output_tokens < 1:
            raise CloudContractError("INVALID_CLOUD_REQUEST", 422)
        for value in (self.input_sha256,
                      str(self.prompt_identity.get("prompt_bundle_sha256", "")),
                      str(self.configuration_identity.get("configuration_sha256", ""))):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise CloudContractError("INVALID_CLOUD_REQUEST", 422)
        if not self.job_id or not self.attempt_id or not self.provider or not self.requested_model:
            raise CloudContractError("INVALID_CLOUD_REQUEST", 422)

    def public_identity(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "job_id": self.job_id,
            "attempt_id": self.attempt_id,
            "attempt_number": self.attempt_number,
            "operation_kind": self.operation_kind,
            "input_artifact_id": self.input_artifact_id,
            "input_sha256": self.input_sha256,
            "source_id": self.source_id,
            "runtime_identity": dict(self.runtime_identity),
            "schema_version": self.schema_version,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "prompt_identity": dict(self.prompt_identity),
            "configuration_identity": dict(self.configuration_identity),
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
            "retry_policy_id": self.retry_policy_id,
            "budget_identity": dict(self.budget_identity),
            "payload_sha256": digest(self.payload),
        }

    @property
    def request_sha256(self) -> str:
        return digest(self.public_identity())


@dataclass(frozen=True)
class CloudResult:
    provider: str
    requested_model: str
    provider_reported_model: str
    provider_request_id: str | None
    operation_kind: str
    attempt_number: int
    started_at: str
    ended_at: str
    latency_ms: float
    finish_reason: str
    usage_status: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_tokens: int | None
    output: Mapping[str, Any]
    transport_diagnostic: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.usage_status not in USAGE_STATUSES:
            raise CloudContractError("INVALID_PROVIDER_RESULT")
        values = (self.input_tokens, self.output_tokens, self.total_tokens, self.cached_tokens)
        if self.usage_status == "UNKNOWN" and any(value is not None for value in values):
            raise CloudContractError("INVALID_PROVIDER_RESULT")
        if self.usage_status == "KNOWN" and any(
                value is None for value in (self.input_tokens, self.output_tokens, self.total_tokens)):
            raise CloudContractError("INVALID_PROVIDER_RESULT")
        if any(value is not None and value < 0 for value in values):
            raise CloudContractError("INVALID_PROVIDER_RESULT")
        if self.operation_kind not in OPERATION_KINDS or self.attempt_number < 1:
            raise CloudContractError("INVALID_PROVIDER_RESULT")


class CloudProvider(Protocol):
    provider_identity: str
    adapter_version: str

    def invoke(self, request: CloudRequest) -> CloudResult: ...


class SemanticBackendProvider:
    """Reuse SemanticBackend with its inner transport retries explicitly disabled."""

    adapter_version = ADAPTER_VERSION

    def __init__(self, backend: SemanticBackend, *, provider_identity: str):
        llm = getattr(backend, "llm", None)
        if llm is not None and getattr(getattr(llm, "cfg", None), "max_retries", None) != 0:
            raise CloudContractError("NESTED_RETRY_OWNER_FORBIDDEN")
        self.backend = backend
        self.provider_identity = provider_identity

    def invoke(self, request: CloudRequest) -> CloudResult:
        if request.operation_kind != OPERATION_KIND:
            raise ProviderFailure("PROVIDER_OPERATION_UNSUPPORTED", retryable=False,
                                  external_outcome="NOT_DISPATCHED")
        llm = getattr(self.backend, "llm", None)
        cfg = getattr(llm, "cfg", None)
        if cfg is not None and (
                cfg.model != request.requested_model
                or cfg.timeout_seconds != request.timeout_seconds
                or cfg.max_output_tokens != request.max_output_tokens
                or cfg.max_retries != 0):
            raise ProviderFailure("PROVIDER_CONFIGURATION_MISMATCH", retryable=False,
                                  external_outcome="NOT_DISPATCHED")
        started_at = now()
        started = time.perf_counter()
        try:
            output = self.backend.decompose_batch(request.payload["claims"])
        except LLMError as error:
            raise _llm_provider_failure(error, dict(self.backend.last_call_metadata or {})) from error
        metadata = dict(self.backend.last_call_metadata or {})
        attempts = list(metadata.get("attempts") or [])
        last = attempts[-1] if attempts else {}
        usage_values = (last.get("prompt_tokens"), last.get("completion_tokens"),
                        last.get("total_tokens"))
        known = all(isinstance(value, int) and value >= 0 for value in usage_values)
        return CloudResult(
            provider=self.provider_identity,
            requested_model=request.requested_model,
            provider_reported_model=str(last.get("response_model") or ""),
            provider_request_id=(str(last["provider_request_id"])
                                 if last.get("provider_request_id") else None),
            operation_kind=request.operation_kind,
            attempt_number=request.attempt_number,
            started_at=started_at,
            ended_at=now(),
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            finish_reason=str(last.get("finish_reason") or "UNKNOWN"),
            usage_status="KNOWN" if known else "UNKNOWN",
            input_tokens=int(usage_values[0]) if known else None,
            output_tokens=int(usage_values[1]) if known else None,
            total_tokens=int(usage_values[2]) if known else None,
            cached_tokens=(int(last["cached_tokens"])
                           if known and isinstance(last.get("cached_tokens"), int) else None),
            output=output,
            transport_diagnostic=last,
        )


class SourceAnalysisPieceProvider:
    """One existing Source-analysis prompt per durable provider attempt."""

    adapter_version = SOURCE_ANALYSIS_ADAPTER_VERSION

    def __init__(self, llm: ChatLLM, *, provider_identity: str):
        if getattr(getattr(llm, "cfg", None), "max_retries", None) != 0:
            raise CloudContractError("NESTED_RETRY_OWNER_FORBIDDEN")
        self.llm = llm
        self.provider_identity = provider_identity

    def invoke(self, request: CloudRequest) -> CloudResult:
        if request.operation_kind != SOURCE_ANALYSIS_OPERATION:
            raise ProviderFailure("PROVIDER_OPERATION_UNSUPPORTED", retryable=False,
                                  external_outcome="NOT_DISPATCHED")
        cfg = self.llm.cfg
        if (cfg.model != request.requested_model
                or cfg.timeout_seconds != request.timeout_seconds
                or cfg.max_output_tokens != request.max_output_tokens
                or cfg.max_retries != 0):
            raise ProviderFailure("PROVIDER_CONFIGURATION_MISMATCH", retryable=False,
                                  external_outcome="NOT_DISPATCHED")
        user_prompt = request.payload.get("user_prompt")
        if not isinstance(user_prompt, str) or not user_prompt:
            raise ProviderFailure("INVALID_REQUEST", retryable=False,
                                  external_outcome="NOT_DISPATCHED")
        started_at = now()
        started = time.perf_counter()
        try:
            output = self.llm.json(SOURCE_ANALYSIS_SYSTEM, user_prompt)
        except LLMError as error:
            raise _llm_provider_failure(error, dict(self.llm.last_call_metadata or {})) from error
        metadata = dict(self.llm.last_call_metadata or {})
        attempts = list(metadata.get("attempts") or [])
        last = attempts[-1] if attempts else {}
        usage_values = (last.get("prompt_tokens"), last.get("completion_tokens"),
                        last.get("total_tokens"))
        known = all(isinstance(value, int) and value >= 0 for value in usage_values)
        return CloudResult(
            provider=self.provider_identity,
            requested_model=request.requested_model,
            provider_reported_model=str(last.get("response_model") or ""),
            provider_request_id=(str(last["provider_request_id"])
                                 if last.get("provider_request_id") else None),
            operation_kind=request.operation_kind,
            attempt_number=request.attempt_number,
            started_at=started_at,
            ended_at=now(),
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            finish_reason=str(last.get("finish_reason") or "UNKNOWN"),
            usage_status="KNOWN" if known else "UNKNOWN",
            input_tokens=int(usage_values[0]) if known else None,
            output_tokens=int(usage_values[1]) if known else None,
            total_tokens=int(usage_values[2]) if known else None,
            cached_tokens=(int(last["cached_tokens"])
                           if known and isinstance(last.get("cached_tokens"), int) else None),
            output=output,
            transport_diagnostic=last,
        )


class DeterministicFakeProvider:
    """Offline acceptance provider; it never opens a socket or reads credentials."""

    provider_identity = "DETERMINISTIC_FAKE"
    adapter_version = "deterministic-fake-v1"

    def __init__(self, scenario: str = "success", *, delay_seconds: float = 0.0):
        self.scenario = scenario
        self.delay_seconds = delay_seconds
        self.call_count = 0
        self.request_identities: list[dict[str, Any]] = []

    def invoke(self, request: CloudRequest) -> CloudResult:
        self.call_count += 1
        self.request_identities.append(request.public_identity())
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        if self.scenario == "rate_limit_then_success" and self.call_count == 1:
            raise ProviderFailure("RATE_LIMITED", retryable=True,
                                  external_outcome="KNOWN_FAILURE")
        if self.scenario == "transport_failure":
            raise ProviderFailure("TRANSPORT_ERROR", retryable=True,
                                  external_outcome="NOT_DISPATCHED")
        if self.scenario == "timeout_before_dispatch":
            raise ProviderFailure("TIMEOUT", retryable=True,
                                  external_outcome="NOT_DISPATCHED")
        if self.scenario == "unknown_external_outcome":
            raise ProviderFailure("UNKNOWN_EXTERNAL_OUTCOME", retryable=False,
                                  external_outcome="UNKNOWN",
                                  private_detail="synthetic secret diagnostics")
        if request.operation_kind == SOURCE_ANALYSIS_OPERATION:
            output = ({} if self.scenario == "invalid_output"
                      else self._source_analysis_output(request))
            reported = ("fake-equivalent-v1" if self.scenario == "accepted_alias"
                        else "fake-drift-v2" if self.scenario == "model_mismatch"
                        else request.requested_model)
            return self._result(request, output, reported)
        claims = []
        for claim in request.payload.get("claims", []):
            evidence = list(claim.get("evidence_units") or [])
            support = [evidence[0]["evidence_unit_id"]] if evidence else []
            claims.append({
                "parent_claim_id": claim["claim_id"],
                "ir_status": "VALID",
                "units": [{
                    "predicate_family": "measurement",
                    "modality": "actual",
                    "nature": claim.get("assigned_nature") or "fact",
                    "support_evidence_unit_ids": support,
                    "coherence_key": "k1",
                    "coherence_type": "INDEPENDENT",
                    "time_scope": "unspecified",
                }],
            })
        output: Mapping[str, Any] = {"claims": claims}
        if self.scenario == "invalid_output":
            output = {"unexpected": True}
        reported = ("fake-equivalent-v1" if self.scenario == "accepted_alias"
                    else "fake-drift-v2" if self.scenario == "model_mismatch"
                    else request.requested_model)
        return self._result(request, output, reported)

    def _result(self, request: CloudRequest, output: Mapping[str, Any],
                reported: str) -> CloudResult:
        known = self.scenario != "usage_unknown"
        started_at = now()
        return CloudResult(
            provider=self.provider_identity,
            requested_model=request.requested_model,
            provider_reported_model=reported,
            provider_request_id=f"FAKE_REQ_{self.call_count:04d}",
            operation_kind=request.operation_kind,
            attempt_number=request.attempt_number,
            started_at=started_at,
            ended_at=now(),
            latency_ms=0.0,
            finish_reason="stop",
            usage_status="KNOWN" if known else "UNKNOWN",
            input_tokens=100 if known else None,
            output_tokens=20 if known else None,
            total_tokens=120 if known else None,
            cached_tokens=5 if known else None,
            output=output,
        )

    @staticmethod
    def _source_analysis_output(request: CloudRequest) -> Mapping[str, Any]:
        text = str(request.payload.get("source_text") or "")
        lines = [line.strip() for line in text.splitlines()
                 if line.strip() and not line.strip().startswith("[[")]
        evidence = next((line for line in lines if "Stage Seven" in line),
                        lines[0] if lines else "")
        return {
            "source_metadata": {
                "title": "Stage Seven Synthetic Source",
                "author": "",
                "organization": "",
                "publication_time": "2026-09-15",
                "source_rank": "A",
                "source_origin_type": "primary",
                "summary": "Deterministic offline Source-operation fixture.",
            },
            "node_matches": [],
            "node_candidates": [{
                "canonical_name": "Stage Seven Synthetic Company",
                "primary_type": "Entity",
                "aliases": [],
                "description": "Synthetic company used only for offline Stage 7 qualification.",
                "suggested_parent_node_ids": [],
                "reason": "The clean PDF explicitly names the company.",
                "confidence": 0.95,
                "candidate_kind": "normal",
                "independent_research_value": True,
                "maintenance_rationale": "Retained synthetic qualification entity.",
                "is_discrete_event": False,
                "event_time": "",
                "evidence_excerpt": evidence,
                "long_term_research_value": True,
                "cross_source_or_node_value": True,
                "question": "",
                "importance": "",
                "what_would_change_my_mind": "",
            }],
            "claims": [{
                "statement": evidence,
                "nature": "fact",
                "related_node_ids": [],
                "related_candidate_names": ["Stage Seven Synthetic Company"],
                "fact_time": "2026",
                "evidence_pointer": "provider-proposed; deterministic binding follows",
                "evidence_excerpt": evidence,
                "attributed_to": "Stage Seven Synthetic Company",
                "scope": "synthetic qualification",
                "assumption": "",
                "status": "current",
                "confidence": 0.95,
                "novelty_level": "N2",
                "structured": {},
            }] if evidence else [],
            "relation_candidates": [],
            "source_references": [],
        }


def validate_output(request: CloudRequest, output: Mapping[str, Any]) -> dict[str, Any]:
    """Run the existing Proposition IR validator without another provider call."""
    if request.operation_kind == SOURCE_ANALYSIS_OPERATION:
        required = {"source_metadata", "node_matches", "node_candidates", "claims",
                    "source_references"}
        if (not isinstance(output, Mapping) or not required.issubset(output)
                or not isinstance(output.get("source_metadata"), Mapping)
                or any(not isinstance(output.get(key), list)
                       for key in ("node_matches", "node_candidates", "claims",
                                   "source_references"))
                or len(output["claims"]) > 100 or len(output["node_candidates"]) > 100):
            raise CloudContractError("OUTPUT_VALIDATION_FAILED")
        source_text = canonicalize_text(str(request.payload.get("source_text") or ""))
        for claim in output["claims"]:
            if not isinstance(claim, Mapping):
                raise CloudContractError("OUTPUT_VALIDATION_FAILED")
            excerpt = canonicalize_text(str(claim.get("evidence_excerpt") or ""))
            if not excerpt or excerpt not in source_text:
                raise CloudContractError("OUTPUT_VALIDATION_FAILED")
        return {
            "document_type": "phase42_stage7_validated_source_analysis_piece",
            "schema_version": "1",
            "contract_version": CONTRACT_VERSION,
            "operation_kind": request.operation_kind,
            "input_artifact_id": request.input_artifact_id,
            "input_sha256": request.input_sha256,
            "piece_id": request.payload.get("piece_id"),
            "response": dict(output),
        }
    if set(output) != {"claims"} or not isinstance(output.get("claims"), list):
        raise CloudContractError("OUTPUT_VALIDATION_FAILED")
    raw_rows = output["claims"]
    inputs = list(request.payload.get("claims") or [])
    expected = [item.get("claim_id") for item in inputs]
    actual = [item.get("parent_claim_id") if isinstance(item, Mapping) else None
              for item in raw_rows]
    if actual != expected or len(actual) != len(set(actual)):
        raise CloudContractError("OUTPUT_VALIDATION_FAILED")
    normalized = []
    for claim, row in zip(inputs, raw_rows, strict=True):
        if (not isinstance(row, Mapping) or set(row) - MODEL_RESULT_FIELDS
                or row.get("ir_status") not in ("VALID", "AMBIGUOUS")
                or not isinstance(row.get("units"), list)):
            raise CloudContractError("OUTPUT_VALIDATION_FAILED")
        if any(not isinstance(unit, Mapping) or set(unit) != MODEL_UNIT_FIELDS
               for unit in row["units"]):
            raise CloudContractError("OUTPUT_VALIDATION_FAILED")
        item = normalize_model_result(claim, row)
        validation = item["validation"]
        if (validation.get("status") != "VALID"
                or validation.get("evidence_binding_failures") != 0
                or validation.get("unsupported_content_failures") != 0):
            raise CloudContractError("OUTPUT_VALIDATION_FAILED")
        normalized.append(item)
    return {
        "document_type": "phase42_stage6_validated_semantic_decomposition",
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "operation_kind": request.operation_kind,
        "input_artifact_id": request.input_artifact_id,
        "input_sha256": request.input_sha256,
        "prompt_bundle_sha256": request.prompt_identity["prompt_bundle_sha256"],
        "results": normalized,
    }
