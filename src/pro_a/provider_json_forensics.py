"""Offline, content-minimizing diagnostics for provider JSON boundaries.

This module is intentionally outside every admission path.  It never repairs
provider output, calls a provider, or returns parsed provider records.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sanitized_shape(value: str) -> str:
    """Retain JSON punctuation/whitespace while redacting string content."""
    result: list[str] = []
    inside, escaped = False, False
    for character in value:
        if character == '"' and not escaped:
            result.append(character)
            inside = not inside
        elif character == "\\":
            result.append(character)
        elif character in "{}[],:":
            result.append(character)
        elif character in "\r\n\t ":
            result.append({"\r": "\\r", "\n": "\\n", "\t": "\\t", " ": " "}[character])
        else:
            result.append("x" if inside else "0" if character.isdigit() else "x")
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    return "".join(result)


def _nearest_schema_key(value: str, position: int) -> str | None:
    matches = list(re.finditer(r'"([A-Za-z_]+)"\s*:', value[max(0, position - 256):position]))
    return matches[-1].group(1) if matches else None


def _error_class(value: str, error: json.JSONDecodeError) -> str:
    message = error.msg.lower()
    if "unterminated string" in message:
        return "UNTERMINATED_STRING"
    if "invalid \\u" in message:
        return "MALFORMED_UNICODE_ESCAPE"
    if "invalid \\escape" in message:
        return "INVALID_BACKSLASH_SEQUENCE"
    if "invalid control character" in message:
        return "INVALID_CONTROL_CHARACTER"
    if "extra data" in message:
        return "EXTRA_TRAILING_CONTENT"
    if message == "expecting ',' delimiter":
        key = _nearest_schema_key(value, error.pos)
        before = value[max(0, error.pos - 4):error.pos]
        current = value[error.pos:error.pos + 1]
        if key == "structured_json" and current in "[{" and before.endswith('"'):
            return "QUOTE_CORRUPTION_UNESCAPED_EMBEDDED_JSON"
        return "MISSING_COMMA_OR_QUOTE_CORRUPTION"
    if "expecting property name enclosed in double quotes" in message:
        return "INVALID_OBJECT_MEMBER_OR_TRAILING_COMMA"
    if "expecting ':' delimiter" in message:
        return "MISSING_COLON"
    if "expecting value" in message and error.pos >= len(value.rstrip()):
        return "PARTIAL_VALUE_AT_EOF"
    return "OTHER_JSON_SYNTAX_ERROR"


def inspect_json_arguments(raw: bytes, *, excerpt_chars: int = 200) -> dict[str, Any]:
    """Inspect exact UTF-8 argument bytes without returning their private text."""
    if type(raw) is not bytes or not 0 <= excerpt_chars <= 1000:
        raise ValueError("INVALID_FORENSIC_INPUT")
    receipt: dict[str, Any] = {
        "raw_bytes": len(raw),
        "raw_sha256": _sha256(raw),
        "first_64_bytes_sha256": _sha256(raw[:64]),
        "last_64_bytes_sha256": _sha256(raw[-64:]),
        "repair_attempted": False,
        "authoritative_admission": False,
        "provider_calls": 0,
    }
    try:
        value = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        receipt.update({
            "utf8_valid": False,
            "json_valid": False,
            "json_error_class": "INVALID_UTF8",
            "json_error_char_offset": None,
            "json_error_byte_offset": error.start,
        })
        return receipt
    receipt.update({
        "utf8_valid": True,
        "raw_chars": len(value),
        "first_64_sanitized_repr": repr(_sanitized_shape(value[:64])),
        "last_64_sanitized_repr": repr(_sanitized_shape(value[-64:])),
        "ends_with_object_close": value.rstrip().endswith("}"),
        "tail_whitespace_chars": len(value) - len(value.rstrip()),
    })
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        start, end = max(0, error.pos - excerpt_chars), min(len(value), error.pos + excerpt_chars + 1)
        sanitized = _sanitized_shape(value[start:end])
        receipt.update({
            "json_valid": False,
            "json_error_class": _error_class(value, error),
            "json_error_message": error.msg,
            "json_error_line": error.lineno,
            "json_error_column": error.colno,
            "json_error_char_offset": error.pos,
            "json_error_byte_offset": len(value[:error.pos].encode("utf-8")),
            "json_error_codepoint": ord(value[error.pos]) if error.pos < len(value) else None,
            "nearest_public_schema_key": _nearest_schema_key(value, error.pos),
            "excerpt_start_char": start,
            "excerpt_end_char_exclusive": end,
            "error_marker_in_excerpt": error.pos - start,
            "bounded_sanitized_excerpt": sanitized,
            "bounded_sanitized_repr": repr(sanitized),
        })
        return receipt
    receipt.update({
        "json_valid": True,
        "json_root_type": type(parsed).__name__,
        "json_error_class": None,
        "authoritative_admission": False,
    })
    return receipt


def inspect_provider_envelope(body: bytes, expected_tool_name: str) -> tuple[dict[str, Any], bytes | None]:
    """Inspect Layer A and extract, but do not parse, Layer B arguments."""
    receipt: dict[str, Any] = {
        "outer_bytes": len(body),
        "outer_sha256": _sha256(body),
        "outer_provider_envelope_json_valid": False,
        "outer_provider_tool_shape_valid": False,
        "provider_calls": 0,
    }
    try:
        data = json.loads(body.decode("utf-8", errors="strict"))
        receipt["outer_provider_envelope_json_valid"] = True
        if type(data) is not dict or type(data["choices"]) is not list or len(data["choices"]) != 1:
            raise ValueError()
        choice = data["choices"][0]
        message, calls = choice["message"], choice["message"]["tool_calls"]
        if message["role"] != "assistant" or type(calls) is not list or len(calls) != 1:
            raise ValueError()
        call = calls[0]
        if call["type"] != "function" or call["function"]["name"] != expected_tool_name:
            raise ValueError()
        arguments = call["function"]["arguments"]
        if type(arguments) is not str:
            raise ValueError()
        raw = arguments.encode("utf-8", errors="strict")
        receipt.update({
            "outer_provider_tool_shape_valid": True,
            "tool_name": expected_tool_name,
            "arguments_type": "string",
            "arguments_bytes": len(raw),
            "arguments_sha256": _sha256(raw),
            "finish_reason": choice.get("finish_reason"),
        })
        return receipt, raw
    except (UnicodeError, json.JSONDecodeError, ValueError, KeyError, TypeError, IndexError):
        return receipt, None


def inspect_persisted_raw_artifact(content: bytes, *, configured_max_output_tokens: int | None = None) -> dict[str, Any]:
    """Inspect the append-only local raw envelope and its exact argument bytes."""
    receipt: dict[str, Any] = {
        "artifact_bytes": len(content),
        "artifact_sha256": _sha256(content),
        "persisted_envelope_json_valid": False,
        "persisted_envelope_identity_valid": False,
        "provider_calls": 0,
    }
    try:
        envelope = json.loads(content.decode("utf-8", errors="strict"))
        receipt["persisted_envelope_json_valid"] = True
        raw = base64.b64decode(envelope["raw_body_base64"], validate=True)
        if type(envelope["raw_body_sha256"]) is not str or _sha256(raw) != envelope["raw_body_sha256"]:
            raise ValueError()
        receipt["persisted_envelope_identity_valid"] = True
    except (UnicodeError, json.JSONDecodeError, ValueError, KeyError, TypeError):
        return receipt
    finish, output = envelope.get("finish_reason"), envelope.get("output_tokens")
    truncation: bool | str = "unresolved"
    if finish == "length":
        truncation = True
    elif (finish in ("stop", "tool_calls") and type(output) is int
          and type(configured_max_output_tokens) is int and output < configured_max_output_tokens):
        truncation = False
    receipt.update({
        "attempt_id": envelope.get("attempt_id"),
        "request_sha256": envelope.get("request_sha256"),
        "http_status": envelope.get("http_status"),
        "finish_reason": finish,
        "output_tokens": output,
        "configured_max_output_tokens": configured_max_output_tokens,
        "output_truncation": truncation,
        "arguments": inspect_json_arguments(raw),
    })
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect one private persisted provider raw artifact offline.")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--max-output-tokens", type=int)
    args = parser.parse_args(argv)
    content = args.artifact.read_bytes()
    if args.expected_sha256 and _sha256(content) != args.expected_sha256:
        raise SystemExit("ARTIFACT_SHA256_MISMATCH")
    print(json.dumps(inspect_persisted_raw_artifact(
        content, configured_max_output_tokens=args.max_output_tokens), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
