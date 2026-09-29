"""Allowlisted, content-free diagnostics for cloud provider failures."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_REQUEST_ID = re.compile(r"(?:chatcmpl[-_]|req[-_]|request[-_])[A-Za-z0-9._:-]{1,119}\Z|[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z")
_PROVIDER_ERROR_VALUES = {
    "api_error", "auth_error", "authentication_error", "invalid_key",
    "invalid_api_key", "invalid_request_error", "model_error", "model_not_found",
    "quota_exceeded", "insufficient_quota", "rate_limit", "rate_limited",
    "rate_limit_error", "server_error", "service_unavailable",
}
_CLASSES = {
    "TRANSPORT_DNS_ERROR", "TRANSPORT_CONNECT_ERROR", "TRANSPORT_TLS_ERROR",
    "TRANSPORT_TIMEOUT", "TRANSPORT_READ_TIMEOUT", "TRANSPORT_CONNECTION_RESET",
    "HTTP_4XX", "HTTP_401", "HTTP_403", "HTTP_404", "HTTP_408",
    "HTTP_409", "HTTP_422", "HTTP_429", "HTTP_5XX", "HTTP_500",
    "HTTP_502", "HTTP_503", "HTTP_504", "PROVIDER_API_ERROR",
    "RESPONSE_EMPTY", "RESPONSE_CONTENT_TYPE_INVALID", "RESPONSE_DECODE_ERROR",
    "RESPONSE_JSON_PARSE_ERROR", "PROVIDER_RESPONSE_SCHEMA_ERROR",
    "OUTPUT_PARSE_ERROR", "OUTPUT_SCHEMA_VALIDATION_ERROR",
    "INTERNAL_PROVIDER_ADAPTER_ERROR", "UNKNOWN_PROVIDER_ERROR",
}
_STAGES = {"ROUTING", "REQUEST_BUILD", "TRANSPORT", "HTTP_RESPONSE",
           "PROVIDER_PARSE", "MODEL_OUTPUT_PARSE", "OUTPUT_VALIDATION",
           "PERSISTENCE", "UNKNOWN"}
_FINISH_REASONS = {"stop", "length", "content_filter", "insufficient_system_resource",
                   "tool_calls", "function_call"}
_OUTPUT_PARSE_KINDS = {"TRUNCATED", "MALFORMED_JSON", "NON_OBJECT_JSON", "EMPTY_CONTENT",
                       "CONTENT_FILTER", "INSUFFICIENT_SYSTEM_RESOURCE", "TOOL_CALLS",
                       "UNEXPECTED_FINISH_REASON"}


def _bounded_integer(value: Any, maximum: int) -> int | None:
    return value if type(value) is int and 0 <= value <= maximum else None


def _output_diagnostic(info: Mapping[str, Any]) -> dict[str, Any]:
    finish = info.get("finish_reason")
    kind = info.get("output_parse_kind")
    length = _bounded_integer(info.get("content_length"), 100_000_000)
    position = _bounded_integer(info.get("raw_response_json_error_position"), 100_000_000)
    if position is not None and length is not None and position > length:
        position = None
    content_hash = info.get("content_sha256")
    syntax = info.get("raw_response_syntactically_parseable")
    return {
        "finish_reason": finish if isinstance(finish, str) and finish in _FINISH_REASONS else None,
        "response_model": safe_identifier(info.get("response_model")),
        **{key: _bounded_integer(info.get(key), 10_000_000)
           for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens")},
        "content_length": length,
        "content_sha256": content_hash if isinstance(content_hash, str) and re.fullmatch(r"[0-9a-f]{64}", content_hash) else None,
        "raw_response_syntactically_parseable": syntax if type(syntax) is bool else None,
        "raw_response_json_error_position": position,
        "output_parse_kind": kind if isinstance(kind, str) and kind in _OUTPUT_PARSE_KINDS else None,
    }


def safe_identifier(value: Any) -> str | None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        return None
    if any(marker in value.upper() for marker in ("SECRET", "TOKEN", "COOKIE", "BEARER", "API_KEY")):
        return None
    return value


def safe_request_id(value: Any) -> str | None:
    identifier = safe_identifier(value)
    return identifier if identifier and _REQUEST_ID.fullmatch(identifier) else None


def safe_provider_error_value(value: Any) -> str | None:
    return value if isinstance(value, str) and value in _PROVIDER_ERROR_VALUES else None


def safe_timestamp(value: Any) -> str | None:
    return value if _safe_time(value) else None


def http_error_class(status: int) -> str:
    specific = f"HTTP_{status}"
    if specific in _CLASSES:
        return specific
    return "HTTP_4XX" if 400 <= status < 500 else "HTTP_5XX" if 500 <= status < 600 else "PROVIDER_API_ERROR"


def build_failure_diagnostic(*, provider: str, model: str, operation_kind: str,
                             job_id: str, call_id: str, attempt_number: int,
                             failure_code: str, retryable: bool,
                             details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Never copy free-form exception, request, or response text into durable state."""
    info = details or {}
    status = info.get("http_status")
    status = status if type(status) is int and 100 <= status <= 599 else None
    error_class = info.get("error_class")
    error_class = error_class if isinstance(error_class, str) and error_class in _CLASSES else "UNKNOWN_PROVIDER_ERROR"
    stage = info.get("failure_stage")
    stage = stage if isinstance(stage, str) and stage in _STAGES else "UNKNOWN"
    operation = "EXTRACTION" if operation_kind == "SOURCE_ANALYSIS_PIECE" else "OTHER"
    provider_name = safe_identifier(provider)
    model_name = safe_identifier(model)
    provider_type = safe_provider_error_value(info.get("provider_error_type"))
    provider_code = safe_provider_error_value(info.get("provider_error_code"))
    fingerprint_input = [provider_name, model_name, operation, stage, error_class,
                         status, provider_type, provider_code]
    output = _output_diagnostic(info if stage == "MODEL_OUTPUT_PARSE" else {})
    if output["output_parse_kind"] is not None or output["finish_reason"] is not None:
        fingerprint_input.extend((output["output_parse_kind"], output["finish_reason"]))
    fingerprint = hashlib.sha256(json.dumps(fingerprint_input, separators=(",", ":")).encode()).hexdigest()
    summary = (f"HTTP {status} from provider API" if stage == "HTTP_RESPONSE" and status is not None
               else f"{error_class.replace('_', ' ').lower()} after HTTP {status}" if status is not None
               else error_class.replace("_", " ").lower())
    size = info.get("response_size_bytes")
    payload_size = info.get("request_payload_size_bytes")
    duration = info.get("duration_ms")
    return {
        "provider_name": provider_name, "model_name": model_name,
        "endpoint_class": "CHAT_COMPLETIONS", "operation_type": operation,
        "job_id": job_id, "call_id": call_id, "attempt_number": attempt_number,
        "provider_request_id": safe_request_id(info.get("provider_request_id")),
        "failure_stage": stage, "error_class": error_class,
        "provider_error_type": provider_type, "provider_error_code": provider_code,
        "provider_error_type_present": info.get("provider_error_type_present") if type(info.get("provider_error_type_present")) is bool else None,
        "provider_error_code_present": info.get("provider_error_code_present") if type(info.get("provider_error_code_present")) is bool else None,
        "http_status": status, "http_request_sent": info.get("http_request_sent") if type(info.get("http_request_sent")) is bool else None,
        "http_response_received": (True if status is not None else
                                   False if stage in ("TRANSPORT", "REQUEST_BUILD") else None),
        "retryable": retryable, "provider_failure_code": safe_identifier(failure_code),
        "started_at": safe_timestamp(info.get("started_at")),
        "finished_at": safe_timestamp(info.get("finished_at")),
        "duration_ms": round(duration, 3) if type(duration) in (int, float) and 0 <= duration < 86400000 else None,
        "response_content_type": info.get("response_content_type") if info.get("response_content_type") in ("application/json", "other", None) else None,
        "response_size_bytes": size if type(size) is int and 0 <= size < 100000000 else None,
        "request_payload_size_bytes": payload_size if type(payload_size) is int and 0 <= payload_size < 100000000 else None,
        "error_fingerprint": fingerprint, "safe_error_summary": summary[:500],
        **output,
    }


def _safe_time(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", value))
