"""Offline provider JSON diagnostics and fail-closed admission ordering."""
import base64
import hashlib
import json

import pytest

from pro_a import output_decomposition as output
from pro_a.provider_json_forensics import (
    inspect_json_arguments,
    inspect_persisted_raw_artifact,
    inspect_provider_envelope,
)
from pro_a.source_analysis_provider_record import parse_object
from pro_a.workbench import bounded_extraction_persistence as migration
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from test_bounded_extraction_persistence import no_network
from test_output_decomposition import fixture as output_fixture
from test_phase43_stage6_lifecycle import _schema11


MALFORMED = '{"claims":[{"statement":"中文","structured_json":" "{"subject":"x"}"}]}'


def persisted(raw, *, finish_reason="tool_calls", output_tokens=4663):
    body = raw.encode("utf-8")
    return json.dumps({
        "version": "bounded-private-raw-v1",
        "attempt_id": "ATTEMPT_SYNTHETIC",
        "request_sha256": "a" * 64,
        "raw_body_base64": base64.b64encode(body).decode("ascii"),
        "raw_body_sha256": hashlib.sha256(body).hexdigest(),
        "http_status": 200,
        "provider_request_id": "request-synthetic",
        "finish_reason": finish_reason,
        "input_tokens": 100,
        "output_tokens": output_tokens,
        "total_tokens": 100 + output_tokens,
        "cached_input_tokens": 0,
        "latency_ms": 1.0,
    }, sort_keys=True, separators=(",", ":")).encode()


def test_persisted_malformed_arguments_are_deterministic_immutable_and_offline():
    artifact = persisted(MALFORMED)
    before = hashlib.sha256(artifact).hexdigest()
    reports = [inspect_persisted_raw_artifact(artifact, configured_max_output_tokens=12000)
               for _ in range(3)]
    assert reports[0] == reports[1] == reports[2]
    assert hashlib.sha256(artifact).hexdigest() == before
    assert reports[0]["persisted_envelope_json_valid"]
    assert reports[0]["persisted_envelope_identity_valid"]
    assert reports[0]["arguments"]["json_error_class"] == "QUOTE_CORRUPTION_UNESCAPED_EMBEDDED_JSON"
    assert reports[0]["arguments"]["provider_calls"] == reports[0]["provider_calls"] == 0
    assert reports[0]["output_truncation"] is False
    assert reports[0]["arguments"]["repair_attempted"] is False
    assert reports[0]["arguments"]["authoritative_admission"] is False


def test_valid_outer_provider_envelope_preserves_exact_invalid_inner_arguments():
    outer = json.dumps({
        "model": "deepseek-flash",
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {"role": "assistant", "tool_calls": [{
                "type": "function",
                "function": {"name": "emit_source_analysis", "arguments": MALFORMED},
            }]},
        }],
    }, ensure_ascii=False).encode()
    receipt, raw = inspect_provider_envelope(outer, "emit_source_analysis")
    assert receipt["outer_provider_envelope_json_valid"]
    assert receipt["outer_provider_tool_shape_valid"]
    assert receipt["arguments_type"] == "string"
    assert raw == MALFORMED.encode()
    assert receipt["arguments_sha256"] == hashlib.sha256(raw).hexdigest()
    assert inspect_json_arguments(raw)["json_valid"] is False


def test_unicode_offsets_and_bounded_sanitized_excerpt():
    raw = MALFORMED.encode()
    result = inspect_json_arguments(raw)
    assert result["json_error_line"] == 1
    assert result["json_error_column"] == result["json_error_char_offset"] + 1
    assert result["json_error_byte_offset"] > result["json_error_char_offset"]
    assert result["nearest_public_schema_key"] == "structured_json"
    assert len(result["bounded_sanitized_excerpt"]) <= 401
    assert "中文" not in result["bounded_sanitized_excerpt"]
    assert result["error_marker_in_excerpt"] <= 200


def test_valid_escaped_string_is_not_misclassified_or_admitted():
    raw = json.dumps({"x": 'quoted "value" and slash \\'}, separators=(",", ":")).encode()
    result = inspect_json_arguments(raw)
    assert result["json_valid"] is True
    assert result["json_root_type"] == "dict"
    assert result["repair_attempted"] is False
    assert result["authoritative_admission"] is False


@pytest.mark.parametrize(("raw", "classification"), [
    (b'{"x":"unterminated}', "UNTERMINATED_STRING"),
    (b'{"x":"\\q"}', "INVALID_BACKSLASH_SEQUENCE"),
    (b'{"x":"a\nb"}', "INVALID_CONTROL_CHARACTER"),
    (b'{"x":1}{"y":2}', "EXTRA_TRAILING_CONTENT"),
    (b'{"x":"\\u12G4"}', "MALFORMED_UNICODE_ESCAPE"),
    (b'{"x":[{"y":1}', "MISSING_COMMA_OR_QUOTE_CORRUPTION"),
])
def test_syntax_classes_are_strict_and_never_repaired(raw, classification):
    result = inspect_json_arguments(raw)
    assert result["json_valid"] is False
    assert result["json_error_class"] == classification
    assert result["repair_attempted"] is False
    assert result["authoritative_admission"] is False


def test_syntax_failure_precedes_record_shape_evidence_and_segment_result(monkeypatch):
    ctx, catalog, series, plan = output_fixture(1)
    reached = []
    def forbidden(name):
        def fail(*args, **kwargs):
            reached.append(name)
            pytest.fail(name + " MUST_NOT_RUN")
        return fail
    monkeypatch.setattr(output.lexical, "validate_shape", forbidden("record_schema"))
    monkeypatch.setattr(output, "resolve_evidence_binding_v2", forbidden("evidence_binding"))
    monkeypatch.setattr(output, "create_segment_wire_result", forbidden("segment_result"))
    with pytest.raises(ValueError, match="INVALID_PROVIDER_JSON_OBJECT"):
        output.record_to_result(MALFORMED, series, plan.leaves[0], catalog, ctx)
    assert reached == []
    with pytest.raises(ValueError, match="INVALID_PROVIDER_JSON_OBJECT"):
        parse_object(MALFORMED)


def test_persistence_and_reconcile_fail_closed_without_call_accounting_growth(tmp_path):
    case, _ = _schema11(tmp_path)
    config = case["config"]
    migration.prepare_bounded_extraction_persistence(config)
    ctx, catalog, series, plan = output_fixture(1)
    ledger = BoundedExtractionStore(config)
    ledger.create(series)
    segment = plan.leaves[0]
    fence = ledger.claim_segment(segment.segment_id, "worker", lease_seconds=600)
    attempt = ledger.reserve_attempt(segment.segment_id, "worker", fence, attempt_number=1,
        payload_sha256="a" * 64, configuration_sha256="b" * 64)
    attempt_id = attempt["attempt_id"]
    ledger.record_dispatch(attempt_id, "worker", fence)
    production_before = config.knowledge_db.read_bytes()
    outcome = ledger.record_outcome(attempt_id, "worker", fence, MALFORMED.encode(),
        finish_reason="tool_calls", input_tokens=100, output_tokens=50, total_tokens=150,
        cached_input_tokens=0, latency_ms=1.0)
    raw_path = config.artifact_root / outcome["artifact_relative"]
    raw_before = raw_path.read_bytes()
    assert ledger.read(series.series_id)[3].provider_call_count == 1
    with pytest.raises(BoundaryError, match="INVALID_SEGMENT_RESPONSE"):
        ledger.accept_result(attempt_id, "worker", fence, catalog, ctx)
    with pytest.raises(BoundaryError):
        ledger.reconcile_attempt(attempt_id, "worker", fence, catalog, ctx)
    assert raw_path.read_bytes() == raw_before
    assert ledger.read(series.series_id)[3].provider_call_count == 1
    assert config.knowledge_db.read_bytes() == production_before
    with Store(config).connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM bounded_extraction_attempts").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM bounded_extraction_outcomes").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM bounded_extraction_segment_results").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM bounded_extraction_series_results").fetchone()[0] == 0


def test_finish_reason_not_eof_shape_controls_truncation_classification():
    nontruncated = inspect_persisted_raw_artifact(
        persisted(MALFORMED, finish_reason="tool_calls", output_tokens=4663),
        configured_max_output_tokens=12000)
    truncated = inspect_persisted_raw_artifact(
        persisted('{"x":', finish_reason="length", output_tokens=12000),
        configured_max_output_tokens=12000)
    assert nontruncated["output_truncation"] is False
    assert nontruncated["arguments"]["ends_with_object_close"] is True
    assert truncated["output_truncation"] is True
