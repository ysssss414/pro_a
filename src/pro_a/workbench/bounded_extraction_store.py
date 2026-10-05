"""Dormant bounded-extraction ledger. This module never calls a provider.

SQLite serializes all mutations and immutable artifact publication. Raw bodies
use a private, base64 envelope; body parsing is possible only after DB binding.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import asdict, fields
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import time

from pro_a.bounded_extraction import (
    EvidenceDisposition, ExtractionPlan, ExtractionSegment, ExtractionSeries,
    SegmentCallAccounting, SegmentWireResult, SeriesBudget, SOURCE_ANALYSIS_WIRE_V3_EXPANDER_VERSION, _plan, _series,
    account_series_calls, aggregate_segment_wires, create_segment_wire_result,
    initial_extraction_plan, subdivide_extraction_plan,
)
from pro_a.evidence_binding import identity
from pro_a.provider_diagnostics import safe_identifier
from . import bounded_extraction_persistence as persistence
from .bounded_extraction_persistence import JSON_FIELDS, PREFIX, canonical, write_once
from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


def _now():
    return datetime.now(timezone.utc).isoformat()


def _require(condition, code):
    if not condition:
        raise BoundaryError(code)


def _sha(value):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "INVALID_IDENTITY_SHA")
    return value


def _record(connection, table, values):
    row = {**values, "record_sha256": identity(values)}
    connection.execute(f"INSERT INTO {PREFIX + table}({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
    return row


def _verified(row):
    value = dict(row)
    sha = value.pop("record_sha256")
    _require(identity(value) == sha, "BOUNDED_RECORD_IDENTITY_MISMATCH")
    return dict(row)


def _model(row, model):
    values = {f.name: row[f.name] for f in fields(model)}
    for key in values.keys() & JSON_FIELDS:
        values[key] = SeriesBudget(**json.loads(values[key])) if key == "budget" else tuple(json.loads(values[key]))
    return model(**values)


def _insert_model(connection, table, model, state):
    row = asdict(model)
    for key in row.keys() & JSON_FIELDS:
        row[key] = canonical(row[key])
    row.update(state=state, created_at=_now(), updated_at=_now())
    connection.execute(f"INSERT INTO {PREFIX + table}({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))


def _event(connection, series_id, event_type, **body):
    previous = connection.execute("SELECT sequence,event_sha256 FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence DESC LIMIT 1", (series_id,)).fetchone()
    value = {"series_id": series_id, "sequence": previous[0] + 1 if previous else 1,
             "event_type": event_type, "body_json": canonical(body),
             "previous_sha256": previous[1] if previous else "0" * 64, "created_at": _now()}
    value["event_sha256"] = identity(value)
    connection.execute(f"INSERT INTO bounded_extraction_events({','.join(value)}) VALUES({','.join('?' for _ in value)})", tuple(value.values()))


class BoundedExtractionStore:
    def __init__(self, config):
        config.validate()
        self.config = config
        self.store = Store(config)

    @contextmanager
    def _connection(self, write=False):
        with self.store.connect(operator_write=write) as connection:
            _require(schema_version(connection) == "12", "BOUNDED_SCHEMA_REQUIRED")
            connection.execute("PRAGMA foreign_keys=ON")
            if write:
                connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection

    def _path(self, series_id, name):
        # IDs and path components come from verified deterministic identities only.
        _require(re.fullmatch(r"SERIES_[0-9A-F]{32}", series_id), "INVALID_SERIES_ID")
        _require(re.fullmatch(r"[A-Za-z0-9_.-]+", name), "UNSAFE_PATH")
        root = checked_path(self.config.artifact_root)
        path = checked_path(root / "bounded-extraction" / series_id / name, missing=True)
        _require(path.is_relative_to(root), "UNSAFE_PATH")
        return path

    def _artifact(self, series_id, name, content):
        path = self._path(series_id, name)
        sha = write_once(path, content)
        return path.relative_to(self.config.artifact_root.resolve()).as_posix(), sha

    def _read_artifact(self, series_id, name, row):
        path = self._path(series_id, name)
        _require(row["artifact_relative"] == path.relative_to(self.config.artifact_root.resolve()).as_posix(), "ARTIFACT_PATH_MISMATCH")
        content = checked_path(path).read_bytes()
        _require(hashlib.sha256(content).hexdigest() == row["artifact_sha256"], "ARTIFACT_HASH_MISMATCH")
        return content

    def _load(self, connection, series_id):
        row = connection.execute("SELECT * FROM bounded_extraction_series WHERE series_id=?", (series_id,)).fetchone()
        _require(row is not None, "UNKNOWN_SERIES")
        series = _model(row, ExtractionSeries)
        _series(series)
        segments = connection.execute("SELECT * FROM bounded_extraction_segments WHERE series_id=? ORDER BY rowid", (series_id,)).fetchall()
        plan = ExtractionPlan(series_id, tuple(_model(r, ExtractionSegment) for r in segments),
                              tuple(r["segment_id"] for r in segments if r["state"] == "SUPERSEDED_BY_CHILDREN"))
        _plan(series, plan)
        previous = "0" * 64
        for seq, event in enumerate(connection.execute("SELECT * FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence", (series_id,)), 1):
            value = dict(event)
            sha = value.pop("event_sha256")
            _require(value["sequence"] == seq and value["previous_sha256"] == previous and identity(value) == sha, "EVENT_CHAIN_MISMATCH")
            previous = sha
        _require(previous != "0" * 64, "EVENT_CHAIN_MISMATCH")
        calls = []
        for segment in plan.segments:
            previous_request = None
            for number, attempt in enumerate(connection.execute("SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number", (segment.segment_id,)), 1):
                attempt = _verified(attempt)
                request = json.loads(attempt["request_json"])
                _require(number == attempt["attempt_number"] and request == self._request(series, segment, request["payload_sha256"], attempt["configuration_sha256"])
                         and identity(request) == attempt["request_sha256"] and attempt["budget_identity"] == series.output_budget_identity
                         and attempt["attempt_id"] == self._attempt_id(segment.segment_id, number, attempt["request_sha256"])
                         and previous_request in (None, attempt["request_sha256"]), "ATTEMPT_IDENTITY_MISMATCH")
                previous_request = attempt["request_sha256"]
                dispatch = connection.execute("SELECT * FROM bounded_extraction_dispatches WHERE attempt_id=?", (attempt["attempt_id"],)).fetchone()
                if dispatch:
                    _verified(dispatch)
                outcome = connection.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (attempt["attempt_id"],)).fetchone()
                if outcome:
                    _require(dispatch is not None, "OUTCOME_WITHOUT_DISPATCH")
                    _verified(outcome)
                    self._read_artifact(series_id, attempt["attempt_id"] + ".raw.json", outcome)
                calls.append(SegmentCallAccounting(
                    segment.segment_id, attempt["attempt_id"], outcome["provider_request_id"] if outcome else None,
                    *(outcome[f] if outcome else None for f in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens")),
                    outcome["latency_ms"] if outcome else None, outcome["finish_reason"] if outcome else None, outcome["artifact_sha256"] if outcome else None,
                    outcome["external_outcome"] if outcome else "UNKNOWN"))
            accepted = connection.execute("SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?", (segment.segment_id,)).fetchone()
            if accepted:
                _verified(accepted)
                result = self._result(series_id, accepted)
                _require(result.segment_sha256 == segment.segment_sha256, "SEGMENT_RESULT_IDENTITY_MISMATCH")
                binding = connection.execute("SELECT segment_id FROM bounded_extraction_attempts WHERE attempt_id=?", (accepted["attempt_id"],)).fetchone()
                _require(binding is not None and binding[0] == segment.segment_id, "RESULT_ATTEMPT_MISMATCH")
        accounting = account_series_calls(series, plan, tuple(calls))
        _require(row["provider_call_reservations"] == accounting.provider_call_count and row["output_liability"] == accounting.output_token_liability, "BUDGET_LEDGER_MISMATCH")
        _require(row["frontier_version"] == len(plan.superseded_segment_ids), "FRONTIER_IDENTITY_MISMATCH")
        final = connection.execute("SELECT * FROM bounded_extraction_series_results WHERE series_id=?", (series_id,)).fetchone()
        if final:
            self._final_result(series, plan, connection, final)
        return series, plan, dict(row), accounting

    def read(self, series_id):
        with self._connection() as connection:
            return self._load(connection, series_id)

    def create(self, series):
        plan = initial_extraction_plan(series)
        with self._connection(True) as connection:
            if connection.execute("SELECT 1 FROM bounded_extraction_series WHERE series_id=?", (series.series_id,)).fetchone():
                self._load(connection, series.series_id)
                return series.series_id
            _insert_model(connection, "series", series, "OPEN")
            _event(connection, series.series_id, "SERIES_CREATED", series_sha256=series.series_sha256)
            for segment in plan.segments:
                _insert_model(connection, "segments", segment, "PLANNED")
                _event(connection, series.series_id, "SEGMENT_CREATED", segment_id=segment.segment_id)
        return series.series_id

    def _segment_row(self, connection, segment_id):
        row = connection.execute("SELECT * FROM bounded_extraction_segments WHERE segment_id=?", (segment_id,)).fetchone()
        _require(row is not None, "UNKNOWN_SEGMENT")
        loaded = self._load(connection, row["series_id"])
        return dict(row), loaded

    @staticmethod
    def _owned(row, owner, fence, now=None):
        _require(row["lease_owner"] == owner and row["fence"] == fence and row["lease_expires_at"] is not None
                 and row["lease_expires_at"] > (time.time() if now is None else now), "STALE_FENCE")

    def _claim(self, table, key, object_id, owner, lease_seconds, now):
        _require(isinstance(owner, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", owner), "INVALID_LEASE_OWNER")
        _require(type(lease_seconds) in (int, float) and math.isfinite(lease_seconds) and lease_seconds > 0, "INVALID_LEASE")
        now = time.time() if now is None else now
        with self._connection(True) as connection:
            if table == "segments":
                row, _ = self._segment_row(connection, object_id)
            else:
                _, _, row, _ = self._load(connection, object_id)
            _require(row["lease_expires_at"] is None or row["lease_expires_at"] <= now, "LEASE_BUSY")
            fence = row["fence"] + 1
            state = "RUNNING" if table == "segments" and row["state"] == "PLANNED" else row["state"]
            connection.execute(f"UPDATE {PREFIX + table} SET lease_owner=?,lease_expires_at=?,fence=?,state=?,updated_at=? WHERE {key}=?", (owner, now + lease_seconds, fence, state, _now(), object_id))
            _event(connection, row["series_id"], "SEGMENT_CLAIMED" if table == "segments" else "SERIES_CLAIMED", object_id=object_id, fence=fence)
            return fence

    def claim_segment(self, segment_id, owner, *, lease_seconds=60, now=None):
        return self._claim("segments", "segment_id", segment_id, owner, lease_seconds, now)

    def claim_series(self, series_id, owner, *, lease_seconds=60, now=None):
        return self._claim("series", "series_id", series_id, owner, lease_seconds, now)

    @staticmethod
    def _request(series, segment, payload_sha256, configuration_sha256):
        return {"series_sha256": series.series_sha256, "segment_sha256": segment.segment_sha256,
                "payload_sha256": _sha(payload_sha256), "configuration_sha256": _sha(configuration_sha256),
                "budget_identity": series.output_budget_identity, "max_output_tokens": segment.max_output_tokens}

    @staticmethod
    def _attempt_id(segment_id, number, request_sha):
        return "ATTEMPT_" + identity([segment_id, number, request_sha])[:32].upper()

    def reserve_attempt(self, segment_id, owner, fence, *, attempt_number, payload_sha256, configuration_sha256):
        _require(type(attempt_number) is int and attempt_number > 0, "INVALID_ATTEMPT_NUMBER")
        with self._connection(True) as connection:
            row, (series, plan, series_row, _) = self._segment_row(connection, segment_id)
            self._owned(row, owner, fence)
            _require(series_row["state"] == "OPEN" and row["state"] in ("RUNNING", "FAILED"), "SEGMENT_NOT_DISPATCHABLE")
            segment = next(s for s in plan.segments if s.segment_id == segment_id)
            request = self._request(series, segment, payload_sha256, configuration_sha256)
            request_sha = identity(request)
            attempts = connection.execute("SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number", (segment_id,)).fetchall()
            if attempt_number <= len(attempts):
                existing = attempts[attempt_number - 1]
                _require(existing["request_sha256"] == request_sha, "RETRY_IDENTITY_MISMATCH")
                return dict(existing)
            _require(attempt_number == len(attempts) + 1, "ATTEMPT_SEQUENCE_MISMATCH")
            if attempts:
                previous = attempts[-1]
                _require(previous["request_sha256"] == request_sha, "RETRY_IDENTITY_MISMATCH")
                outcome = connection.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (previous["attempt_id"],)).fetchone()
                _require(outcome is not None and outcome["external_outcome"] != "UNKNOWN" and row["state"] == "FAILED", "PREVIOUS_ATTEMPT_UNRESOLVED")
            _require(not connection.execute("SELECT 1 FROM bounded_extraction_segment_results WHERE segment_id=?", (segment_id,)).fetchone(), "SEGMENT_ALREADY_ACCEPTED")
            _require(series_row["provider_call_reservations"] + 1 <= series.budget.max_provider_calls
                     and series_row["output_liability"] + segment.max_output_tokens <= series.budget.max_cumulative_output_tokens, "SERIES_BUDGET_EXCEEDED")
            attempt = _record(connection, "attempts", {"attempt_id": self._attempt_id(segment_id, attempt_number, request_sha),
                "segment_id": segment_id, "attempt_number": attempt_number, "request_json": canonical(request),
                "request_sha256": request_sha, "configuration_sha256": configuration_sha256,
                "budget_identity": series.output_budget_identity, "created_at": _now()})
            connection.execute("UPDATE bounded_extraction_series SET provider_call_reservations=provider_call_reservations+1,output_liability=output_liability+?,updated_at=? WHERE series_id=?", (segment.max_output_tokens, _now(), series.series_id))
            connection.execute("UPDATE bounded_extraction_segments SET state='RUNNING',updated_at=? WHERE segment_id=?", (_now(), segment_id))
            _event(connection, series.series_id, "ATTEMPT_RESERVED", attempt_id=attempt["attempt_id"], record_sha256=attempt["record_sha256"])
        persistence.checkpoint("attempt_reserved")
        return attempt

    def _attempt(self, connection, attempt_id, owner, fence):
        attempt = connection.execute("SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        _require(attempt is not None, "UNKNOWN_ATTEMPT")
        row, loaded = self._segment_row(connection, attempt["segment_id"])
        self._owned(row, owner, fence)
        return dict(attempt), row, loaded

    def record_dispatch(self, attempt_id, owner, fence):
        """True grants this caller the sole dispatch; False MUST NOT call a provider."""
        with self._connection(True) as connection:
            attempt, row, (_, _, series_row, _) = self._attempt(connection, attempt_id, owner, fence)
            if connection.execute("SELECT 1 FROM bounded_extraction_dispatches WHERE attempt_id=?", (attempt_id,)).fetchone():
                return False
            _require(row["state"] == "RUNNING" and series_row["state"] == "OPEN", "SEGMENT_NOT_DISPATCHABLE")
            _record(connection, "dispatches", {"attempt_id": attempt_id, "fence": fence, "created_at": _now()})
            _event(connection, row["series_id"], "DISPATCH_INTENT_RECORDED", attempt_id=attempt_id)
        persistence.checkpoint("dispatch_durable")
        return True

    @staticmethod
    def _envelope(attempt, raw_body, *, http_status=200, provider_request_id=None, finish_reason=None,
                  input_tokens=None, output_tokens=None, total_tokens=None, cached_input_tokens=None, latency_ms=None,
                  provider_reported_model=None, reasoning_tokens=None):
        _require(type(raw_body) is bytes, "RAW_BYTES_REQUIRED")
        _require(http_status is None or type(http_status) is int and 100 <= http_status <= 599, "INVALID_HTTP_STATUS")
        _require(provider_request_id is None or isinstance(provider_request_id, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", provider_request_id), "INVALID_PROVIDER_REQUEST_ID")
        _require(finish_reason in (None, "stop", "length", "error", "content_filter"), "INVALID_FINISH_REASON")
        usage = dict(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens, cached_input_tokens=cached_input_tokens)
        _require(all(v is None or type(v) is int and v >= 0 for v in usage.values()), "INVALID_CALL_USAGE")
        if latency_ms is not None:
            _require(type(latency_ms) in (int, float), "INVALID_CALL_LATENCY")
            try:
                finite = math.isfinite(latency_ms)
            except OverflowError:
                finite = False
            _require(finite and latency_ms >= 0, "INVALID_CALL_LATENCY")
        _require(provider_reported_model is None or safe_identifier(provider_reported_model) == provider_reported_model,
                 "INVALID_PROVIDER_MODEL")
        _require(reasoning_tokens is None or type(reasoning_tokens) is int and reasoning_tokens >= 0,
                 "INVALID_REASONING_TOKENS")
        value = {"version": "bounded-private-raw-v1", "attempt_id": attempt["attempt_id"], "request_sha256": attempt["request_sha256"],
                 "raw_body_base64": base64.b64encode(raw_body).decode("ascii"), "raw_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                 "http_status": http_status, "provider_request_id": provider_request_id, "finish_reason": finish_reason, **usage,
                 "latency_ms": latency_ms,
                 **{k: v for k, v in {"provider_reported_model": provider_reported_model, "reasoning_tokens": reasoning_tokens}.items() if v is not None}}
        return {**value, "envelope_sha256": identity(value)}

    def _decode_envelope(self, attempt, content):
        try:
            value = json.loads(content)
            body = base64.b64decode(value["raw_body_base64"], validate=True)
            metadata = {k: value[k] for k in (
                "http_status", "provider_request_id", "finish_reason", "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "latency_ms")}
            metadata.update({k: value[k] for k in ("provider_reported_model", "reasoning_tokens") if k in value})
            expected = self._envelope(attempt, body, **metadata)
            _require(value == expected, "RAW_ENVELOPE_IDENTITY_MISMATCH")
            return value, body
        except (ValueError, KeyError, TypeError):
            raise BoundaryError("RAW_ENVELOPE_IDENTITY_MISMATCH") from None

    def _bind_outcome(self, connection, attempt, row, envelope, content):
        sid = row["series_id"]
        path = self._path(sid, attempt["attempt_id"] + ".raw.json")
        digest = hashlib.sha256(content).hexdigest()
        existing = connection.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (attempt["attempt_id"],)).fetchone()
        if existing:
            _require(existing["artifact_sha256"] == digest, "ARTIFACT_CONFLICT")
            return dict(existing)
        external = ("TRUNCATED" if envelope["finish_reason"] == "length" else
                    "UNKNOWN" if envelope["http_status"] is None else
                    "FAILED" if envelope["http_status"] != 200 or envelope["finish_reason"] in ("error", "content_filter") else "SUCCEEDED")
        usage = {k: envelope[k] for k in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens")}
        # Invalid reported usage remains private and auditable, but cannot release liability.
        invalid = (usage["output_tokens"] is not None and usage["output_tokens"] > 12000
                   or usage["cached_input_tokens"] is not None and usage["input_tokens"] is not None and usage["cached_input_tokens"] > usage["input_tokens"]
                   or all(usage[k] is not None for k in ("input_tokens", "output_tokens", "total_tokens")) and usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"])
        if invalid or external == "UNKNOWN":
            usage = dict.fromkeys(usage)
        outcome = _record(connection, "outcomes", {"attempt_id": attempt["attempt_id"], "external_outcome": external,
            "artifact_relative": path.relative_to(self.config.artifact_root.resolve()).as_posix(), "artifact_sha256": digest,
            "provider_request_id": envelope["provider_request_id"], **usage,
            # Hash SQLite's REAL representation, including its positive zero.
            "latency_ms": float(envelope["latency_ms"] or 0.0) if envelope["latency_ms"] is not None else None,
            "finish_reason": envelope["finish_reason"],
            "classification": "INVALID_USAGE" if invalid else external, "created_at": _now()})
        actual = usage["output_tokens"] if usage["output_tokens"] is not None else 12000
        connection.execute("UPDATE bounded_extraction_series SET output_liability=output_liability-12000+?,updated_at=? WHERE series_id=?", (actual, _now(), sid))
        _event(connection, sid, "PROVIDER_OUTCOME_DURABLE", attempt_id=attempt["attempt_id"], record_sha256=outcome["record_sha256"])
        return outcome

    def record_outcome(self, attempt_id, owner, fence, raw_body, **metadata):
        with self._connection(True) as connection:
            attempt, row, _ = self._attempt(connection, attempt_id, owner, fence)
            _require(connection.execute("SELECT 1 FROM bounded_extraction_dispatches WHERE attempt_id=?", (attempt_id,)).fetchone(), "DISPATCH_REQUIRED")
            envelope = self._envelope(attempt, raw_body, **metadata)
            content = canonical(envelope).encode("utf-8")
            self._artifact(row["series_id"], attempt_id + ".raw.json", content)
            persistence.checkpoint("raw_artifact_durable")
            outcome = self._bind_outcome(connection, attempt, row, envelope, content)
        persistence.checkpoint("outcome_durable")
        return outcome

    def _result(self, series_id, row):
        value = json.loads(self._read_artifact(series_id, row["segment_id"] + ".result.json", row))
        sha = value.pop("result_sha256")
        _require(identity(value) == sha == row["result_sha256"] and value["segment_id"] == row["segment_id"], "SEGMENT_RESULT_IDENTITY_MISMATCH")
        result = SegmentWireResult(**{**value, "dispositions": tuple(EvidenceDisposition(**d) for d in value["dispositions"])}, result_sha256=sha)
        kind = "SUBDIVISION_REQUIRED" if any(d.disposition == "SUBDIVISION_REQUIRED" for d in result.dispositions) else "COMPLETE"
        _require(kind == row["result_type"], "SEGMENT_RESULT_IDENTITY_MISMATCH")
        return result

    def accept_result(self, attempt_id, owner, fence, catalog, context):
        failure = None
        with self._connection(True) as connection:
            attempt, row, (series, plan, _, _) = self._attempt(connection, attempt_id, owner, fence)
            existing = connection.execute("SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?", (row["segment_id"],)).fetchone()
            if existing:
                _require(existing["attempt_id"] == attempt_id, "SEGMENT_ALREADY_ACCEPTED")
                return dict(existing)
            _require(row["state"] in ("RUNNING", "RECOVERY_REQUIRED"), "SEGMENT_NOT_ACCEPTABLE")
            outcome = connection.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (attempt_id,)).fetchone()
            _require(outcome is not None, "DURABLE_OUTCOME_REQUIRED")
            if outcome["external_outcome"] != "SUCCEEDED" or outcome["classification"] == "INVALID_USAGE":
                failure = "RAW_OUTCOME_NOT_ACCEPTABLE"
            else:
                content = self._read_artifact(series.series_id, attempt_id + ".raw.json", outcome)
                _, body = self._decode_envelope(attempt, content)
                try:
                    document = json.loads(body)
                    _require(type(document) is dict and set(document) == {"wire", "dispositions"}, "INVALID_SEGMENT_RESPONSE")
                    dispositions = tuple(EvidenceDisposition(**v) for v in document["dispositions"])
                    segment = next(s for s in plan.segments if s.segment_id == row["segment_id"])
                    result = create_segment_wire_result(series, segment, document["wire"], dispositions, catalog, context)
                    if any(d.disposition == "SUBDIVISION_REQUIRED" for d in dispositions):
                        _require(not document["wire"]["claims"] and all(d.disposition == "SUBDIVISION_REQUIRED" for d in dispositions), "INVALID_SEGMENT_RESPONSE")
                except (ValueError, TypeError, KeyError, UnicodeError):
                    failure = "INVALID_SEGMENT_RESPONSE"
            if failure:
                state = "RECOVERY_REQUIRED" if outcome["external_outcome"] == "UNKNOWN" else "FAILED"
                connection.execute("UPDATE bounded_extraction_segments SET state=?,updated_at=? WHERE segment_id=?", (state, _now(), row["segment_id"]))
                if state == "RECOVERY_REQUIRED":
                    connection.execute("UPDATE bounded_extraction_series SET state='RECOVERY_REQUIRED',updated_at=? WHERE series_id=?", (_now(), series.series_id))
                _event(connection, series.series_id, "SEGMENT_" + state, attempt_id=attempt_id, classification=failure)
            else:
                relative, digest = self._artifact(series.series_id, row["segment_id"] + ".result.json", canonical(asdict(result)).encode("utf-8"))
                kind = "SUBDIVISION_REQUIRED" if any(d.disposition == "SUBDIVISION_REQUIRED" for d in result.dispositions) else "COMPLETE"
                accepted = _record(connection, "segment_results", {"segment_id": row["segment_id"], "attempt_id": attempt_id,
                    "result_type": kind, "result_sha256": result.result_sha256, "artifact_relative": relative,
                    "artifact_sha256": digest, "created_at": _now()})
                _event(connection, series.series_id, "SEGMENT_RESULT_ACCEPTED", segment_id=row["segment_id"], record_sha256=accepted["record_sha256"])
        if failure:
            raise BoundaryError(failure)
        persistence.checkpoint("result_accepted")
        self.close_segment(row["segment_id"], owner, fence)
        return accepted

    def close_segment(self, segment_id, owner, fence):
        with self._connection(True) as connection:
            row, _ = self._segment_row(connection, segment_id)
            self._owned(row, owner, fence)
            accepted = connection.execute("SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?", (segment_id,)).fetchone()
            _require(accepted is not None, "SEGMENT_RESULT_REQUIRED")
            target = "SUCCEEDED_COMPLETE" if accepted["result_type"] == "COMPLETE" else "SUBDIVISION_REQUIRED"
            if row["state"] in (target, "SUPERSEDED_BY_CHILDREN"):
                return target
            _require(row["state"] in ("RUNNING", "RECOVERY_REQUIRED"), "INVALID_SEGMENT_TRANSITION")
            connection.execute("UPDATE bounded_extraction_segments SET state=?,updated_at=? WHERE segment_id=?", (target, _now(), segment_id))
            _event(connection, row["series_id"], "SEGMENT_COMPLETED" if target == "SUCCEEDED_COMPLETE" else "SEGMENT_SUBDIVISION_REQUIRED", segment_id=segment_id)
        return target

    def reconcile_attempt(self, attempt_id, owner, fence, catalog, context):
        with self._connection(True) as connection:
            attempt, row, _ = self._attempt(connection, attempt_id, owner, fence)
            accepted = connection.execute("SELECT 1 FROM bounded_extraction_segment_results WHERE segment_id=?", (row["segment_id"],)).fetchone()
            dispatch = connection.execute("SELECT 1 FROM bounded_extraction_dispatches WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not dispatch:
                return "RESERVED_NOT_DISPATCHED"
            path = self._path(row["series_id"], attempt_id + ".raw.json")
            if not path.exists():
                if row["state"] != "RECOVERY_REQUIRED":
                    connection.execute("UPDATE bounded_extraction_segments SET state='RECOVERY_REQUIRED',updated_at=? WHERE segment_id=?", (_now(), row["segment_id"]))
                    connection.execute("UPDATE bounded_extraction_series SET state='RECOVERY_REQUIRED',updated_at=? WHERE series_id=?", (_now(), row["series_id"]))
                    _event(connection, row["series_id"], "SERIES_RECOVERY_REQUIRED", attempt_id=attempt_id)
                return "UNKNOWN_EXTERNAL_OUTCOME"
            content = checked_path(path).read_bytes()
            envelope, _ = self._decode_envelope(attempt, content)
            self._bind_outcome(connection, attempt, row, envelope, content)
        if accepted:
            return self.close_segment(row["segment_id"], owner, fence)
        self.accept_result(attempt_id, owner, fence, catalog, context)
        return self.close_segment(row["segment_id"], owner, fence)

    def subdivide(self, segment_id, owner, fence, *, expected_frontier_version):
        with self._connection(True) as connection:
            row, (series, plan, series_row, _) = self._segment_row(connection, segment_id)
            self._owned(row, owner, fence)
            if row["state"] == "SUPERSEDED_BY_CHILDREN":
                return tuple(s for s in plan.segments if s.parent_segment_id == segment_id)
            _require(series_row["state"] == "OPEN" and series_row["frontier_version"] == expected_frontier_version, "STALE_FRONTIER")
            accepted = connection.execute("SELECT result_type FROM bounded_extraction_segment_results WHERE segment_id=?", (segment_id,)).fetchone()
            _require(row["state"] == "SUBDIVISION_REQUIRED" and accepted and accepted[0] == "SUBDIVISION_REQUIRED", "VALID_SUBDIVISION_RESULT_REQUIRED")
            children = self._subdivision(connection, series, plan, segment_id)
        persistence.checkpoint("subdivision_committed")
        return children

    @staticmethod
    def _subdivision(connection, series, plan, segment_id):
        changed = subdivide_extraction_plan(series, plan, segment_id)
        children = tuple(s for s in changed.segments if s.parent_segment_id == segment_id)
        for child in children:
            _insert_model(connection, "segments", child, "PLANNED")
            persistence.checkpoint("subdivision_child_inserted")
        connection.execute("UPDATE bounded_extraction_segments SET state='SUPERSEDED_BY_CHILDREN',updated_at=? WHERE segment_id=?", (_now(), segment_id))
        persistence.checkpoint("subdivision_parent_superseded")
        connection.execute("UPDATE bounded_extraction_series SET frontier_version=frontier_version+1,updated_at=? WHERE series_id=?", (_now(), series.series_id))
        _event(connection, series.series_id, "SEGMENT_SUPERSEDED", segment_id=segment_id)
        _event(connection, series.series_id, "CHILD_SEGMENTS_CREATED", segment_ids=[s.segment_id for s in children])
        return children

    def subdivide_after_truncation(self, segment_id, owner, fence, *, expected_frontier_version):
        with self._connection(True) as connection:
            row, (series, plan, series_row, _) = self._segment_row(connection, segment_id)
            self._owned(row, owner, fence)
            latest = connection.execute("SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number DESC LIMIT 1", (segment_id,)).fetchone()
            _require(latest is not None, "DURABLE_TRUNCATION_REQUIRED")
            outcome = connection.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (latest["attempt_id"],)).fetchone()
            _require(outcome and outcome["external_outcome"] == "TRUNCATED" and outcome["finish_reason"] == "length", "DURABLE_TRUNCATION_REQUIRED")
            envelope, _ = self._decode_envelope(latest, self._read_artifact(series.series_id, latest["attempt_id"] + ".raw.json", outcome))
            _require(envelope["finish_reason"] == "length" and not connection.execute("SELECT 1 FROM bounded_extraction_segment_results WHERE segment_id=?", (segment_id,)).fetchone(), "TRUNCATION_RESULT_CONFLICT")
            if row["state"] == "SUPERSEDED_BY_CHILDREN":
                events = connection.execute("SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type='SEGMENT_OVERFLOW_SUBDIVIDED'", (series.series_id,))
                _require(any(json.loads(e[0])["attempt_id"] == latest["attempt_id"] for e in events), "DURABLE_TRUNCATION_REQUIRED")
                return tuple(s for s in plan.segments if s.parent_segment_id == segment_id)
            _require(series_row["state"] == "OPEN" and series_row["frontier_version"] == expected_frontier_version, "STALE_FRONTIER")
            _require(segment_id in {s.segment_id for s in plan.leaves}, "SEGMENT_NOT_ACTIVE_LEAF")
            _require(series_row["provider_call_reservations"] + 2 <= series.budget.max_provider_calls
                     and series_row["output_liability"] + 24000 <= series.budget.max_cumulative_output_tokens,
                     "EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY")
            children = self._subdivision(connection, series, plan, segment_id)
            _event(connection, series.series_id, "SEGMENT_OVERFLOW_SUBDIVIDED", segment_id=segment_id,
                   attempt_id=latest["attempt_id"], outcome_record_sha256=outcome["record_sha256"],
                   child_segment_ids=[s.segment_id for s in children], frontier_version=expected_frontier_version+1)
        persistence.checkpoint("subdivision_committed")
        return children

    def fail_series(self, series_id, owner, fence, code):
        _require(isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]+", code), "INVALID_FAILURE_CODE")
        with self._connection(True) as connection:
            _, _, row, _ = self._load(connection, series_id)
            self._owned(row, owner, fence)
            if row["state"] == "FAILED":
                return
            _require(row["state"] == "OPEN", "SERIES_NOT_FAILABLE")
            connection.execute("UPDATE bounded_extraction_segments SET state='FAILED',updated_at=? WHERE series_id=? AND state NOT IN ('SUCCEEDED_COMPLETE','SUPERSEDED_BY_CHILDREN')", (_now(), series_id))
            connection.execute("UPDATE bounded_extraction_series SET state='FAILED',updated_at=? WHERE series_id=?", (_now(), series_id))
            _event(connection, series_id, "SERIES_FAILED", code=code)

    def release(self, series_id, owner, *, series_fence, segment_id=None, segment_fence=None):
        with self._connection(True) as connection:
            for table, key, value, fence in (("series", "series_id", series_id, series_fence),
                                           ("segments", "segment_id", segment_id, segment_fence)):
                if value is not None:
                    connection.execute(f"UPDATE {PREFIX+table} SET lease_owner=NULL,lease_expires_at=NULL WHERE {key}=? AND lease_owner=? AND fence=?", (value, owner, fence))

    def aggregate(self, series_id):
        with self._connection() as connection:
            _, _, row, _ = self._load(connection, series_id)
            _require(row["state"] == "SUCCEEDED_COMPLETE", "SERIES_COVERAGE_INCOMPLETE")
            final = connection.execute("SELECT * FROM bounded_extraction_series_results WHERE series_id=?", (series_id,)).fetchone()
            _require(final is not None, "DURABLE_SERIES_RESULT_REQUIRED")
            return json.loads(self._read_artifact(series_id, "aggregate.json", final))

    def _final_result(self, series, plan, connection, row):
        _verified(row)
        content = self._read_artifact(series.series_id, "aggregate.json", row)
        document = json.loads(content)
        _require(identity(document["coverage"]) == row["coverage_sha256"], "COVERAGE_IDENTITY_MISMATCH")
        coverage = document["coverage"]
        _require(coverage["series_sha256"] == series.series_sha256 and not coverage["missing_refs"]
                 and not coverage["duplicate_terminal_assignment_refs"] and coverage["closed_refs"] == list(series.eligible_evidence_refs)
                 and coverage["terminal_assigned_refs"] == [r for s in plan.leaves for r in s.assigned_evidence_refs], "COVERAGE_IDENTITY_MISMATCH")
        shas = [connection.execute("SELECT result_sha256 FROM bounded_extraction_segment_results WHERE segment_id=?", (s.segment_id,)).fetchone()[0] for s in plan.leaves]
        _require(json.loads(row["ordered_result_shas_json"]) == shas == document["ordered_segment_result_sha256"], "SERIES_RESULT_IDENTITY_MISMATCH")
        aggregate_identity = {"series_id": series.series_id, "wire_json": canonical(document["wire"]),
                              "coverage": {k: v for k, v in coverage.items() if k != "series_sha256"},
                              "ordered_segment_result_sha256": shas, "expander_version": SOURCE_ANALYSIS_WIRE_V3_EXPANDER_VERSION}
        aggregate_identity["coverage"]["coverage_sha256"] = row["coverage_sha256"]
        _require(identity(aggregate_identity) == row["aggregate_wire_sha256"], "AGGREGATE_IDENTITY_MISMATCH")
        semantic = {k: row[k] for k in ("series_id", "coverage_sha256", "ordered_result_shas_json", "aggregate_wire_sha256", "artifact_relative", "artifact_sha256")}
        _require(identity(semantic) == row["result_sha256"], "SERIES_RESULT_IDENTITY_MISMATCH")
        return dict(row)

    def finalize(self, series_id, owner, fence, *, expected_frontier_version, catalog, context):
        with self._connection(True) as connection:
            series, plan, row, _ = self._load(connection, series_id)
            self._owned(row, owner, fence)
            existing = connection.execute("SELECT * FROM bounded_extraction_series_results WHERE series_id=?", (series_id,)).fetchone()
            if existing:
                return dict(existing)
            _require(row["frontier_version"] == expected_frontier_version, "STALE_FRONTIER")
            _require(row["state"] == "OPEN", "SERIES_NOT_FINALIZABLE")
            # An unbound dispatch anywhere in the tree prevents closure, even on superseded parents.
            unresolved = connection.execute("""SELECT 1 FROM bounded_extraction_attempts a JOIN bounded_extraction_segments s USING(segment_id)
                LEFT JOIN bounded_extraction_outcomes o USING(attempt_id) WHERE s.series_id=? AND (o.attempt_id IS NULL OR o.external_outcome='UNKNOWN') LIMIT 1""", (series_id,)).fetchone()
            _require(not unresolved, "UNRESOLVED_ATTEMPT")
            results = []
            for leaf in plan.leaves:
                state = connection.execute("SELECT state FROM bounded_extraction_segments WHERE segment_id=?", (leaf.segment_id,)).fetchone()[0]
                accepted = connection.execute("SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?", (leaf.segment_id,)).fetchone()
                _require(state == "SUCCEEDED_COMPLETE" and accepted and accepted["result_type"] == "COMPLETE", "SERIES_COVERAGE_INCOMPLETE")
                results.append(self._result(series_id, accepted))
            aggregate = aggregate_segment_wires(series, plan, tuple(results), catalog, context)
            coverage = asdict(aggregate.coverage)
            coverage_sha = coverage.pop("coverage_sha256")
            document = {"wire": json.loads(aggregate.wire_json), "coverage": {"series_sha256": series.series_sha256, **coverage},
                        "ordered_segment_result_sha256": aggregate.ordered_segment_result_sha256}
            relative, digest = self._artifact(series_id, "aggregate.json", canonical(document).encode("utf-8"))
            persistence.checkpoint("aggregate_artifact_durable")
            semantic = {"series_id": series_id, "coverage_sha256": coverage_sha,
                "ordered_result_shas_json": canonical(aggregate.ordered_segment_result_sha256), "aggregate_wire_sha256": aggregate.aggregate_wire_sha256,
                "artifact_relative": relative, "artifact_sha256": digest}
            final = _record(connection, "series_results", {**semantic, "result_sha256": identity(semantic), "created_at": _now()})
            connection.execute("UPDATE bounded_extraction_series SET state='SUCCEEDED_COMPLETE',updated_at=? WHERE series_id=?", (_now(), series_id))
            _event(connection, series_id, "SERIES_COVERAGE_CLOSED", coverage_sha256=coverage_sha)
            _event(connection, series_id, "SERIES_RESULT_DURABLE", result_sha256=final["result_sha256"])
        return final
