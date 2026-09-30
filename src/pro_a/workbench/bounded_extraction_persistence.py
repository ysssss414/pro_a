"""Explicit, offline Workbench v11 -> v12 preparation. No runtime activation."""
from __future__ import annotations

from dataclasses import fields
import hashlib
import json
import os
from pathlib import Path
import uuid

from pro_a.bounded_extraction import ExtractionSegment, ExtractionSeries
from .config import BoundaryError, checked_path
from .lifecycle_closure import _require_drain
from .review_store import schema_version
from .store import Store

PREFIX = "bounded_extraction_"
TABLES = tuple(PREFIX + name for name in (
    "series", "segments", "attempts", "dispatches", "outcomes",
    "segment_results", "series_results", "events",
))
JSON_FIELDS = {"eligible_evidence_refs", "budget", "stable_path", "assigned_evidence_refs"}
INTEGER_FIELDS = {"subdivision_depth", "range_start", "range_end", "max_output_tokens"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def checkpoint(name):
    """Fault-injection seam; never changes normal execution."""


def write_once(path: Path, content: bytes) -> str:
    """Caller holds the Workbench writer transaction, including artifact publication."""
    path = checked_path(path, missing=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise BoundaryError("ARTIFACT_CONFLICT")
    else:
        pending = checked_path(path.with_name(uuid.uuid4().hex + ".pending"), missing=True)
        try:
            with pending.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            # Cooperating writers are serialized by SQLite; never replace a published file.
            if path.exists():
                raise BoundaryError("ARTIFACT_CONFLICT")
            os.replace(pending, path)
            if os.name != "nt":
                descriptor = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            if pending.exists():
                pending.unlink()
    digest = hashlib.sha256(content).hexdigest()
    if hashlib.sha256(checked_path(path).read_bytes()).hexdigest() != digest:
        raise BoundaryError("ARTIFACT_HASH_MISMATCH")
    return digest


def _schema(connection):
    for name, model, key in (("series", ExtractionSeries, "series_id"),
                             ("segments", ExtractionSegment, "segment_id")):
        columns = []
        for field in fields(model):
            kind = "INTEGER" if field.name in INTEGER_FIELDS else "TEXT"
            constraint = " PRIMARY KEY" if field.name == key else ("" if field.name == "parent_segment_id" else " NOT NULL")
            if name == "segments" and field.name == "series_id":
                constraint += " REFERENCES bounded_extraction_series(series_id)"
            if field.name == "parent_segment_id":
                constraint += " REFERENCES bounded_extraction_segments(segment_id)"
            columns.append(field.name + " " + kind + constraint)
        states = ("'OPEN','SUCCEEDED_COMPLETE','FAILED','RECOVERY_REQUIRED'" if name == "series" else
                  "'PLANNED','RUNNING','SUCCEEDED_COMPLETE','SUBDIVISION_REQUIRED','SUPERSEDED_BY_CHILDREN','FAILED','RECOVERY_REQUIRED'")
        columns += [f"state TEXT NOT NULL CHECK(state IN ({states}))", "lease_owner TEXT",
                    "lease_expires_at REAL", "fence INTEGER NOT NULL DEFAULT 0 CHECK(fence>=0)",
                    "created_at TEXT NOT NULL", "updated_at TEXT NOT NULL"]
        if name == "series":
            columns += ["frontier_version INTEGER NOT NULL DEFAULT 0 CHECK(frontier_version>=0)",
                        "provider_call_reservations INTEGER NOT NULL DEFAULT 0 CHECK(provider_call_reservations>=0)",
                        "output_liability INTEGER NOT NULL DEFAULT 0 CHECK(output_liability>=0)"]
        connection.execute(f"CREATE TABLE {PREFIX + name}({','.join(columns)})")
        immutable = ",".join(f.name for f in fields(model)) + ",created_at"
        connection.execute(f"CREATE TRIGGER {PREFIX + name}_identity BEFORE UPDATE OF {immutable} "
                           f"ON {PREFIX + name} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_BOUNDED_IDENTITY'); END")
        connection.execute(f"CREATE TRIGGER {PREFIX + name}_delete BEFORE DELETE ON {PREFIX + name} "
                           "BEGIN SELECT RAISE(ABORT,'IMMUTABLE_BOUNDED_IDENTITY'); END")
    checkpoint("migration_identity_tables")
    definitions = {
        "attempts": """attempt_id TEXT PRIMARY KEY, segment_id TEXT NOT NULL REFERENCES bounded_extraction_segments(segment_id),
            attempt_number INTEGER NOT NULL CHECK(attempt_number>0), request_json TEXT NOT NULL,
            request_sha256 TEXT NOT NULL, configuration_sha256 TEXT NOT NULL, budget_identity TEXT NOT NULL,
            created_at TEXT NOT NULL, record_sha256 TEXT NOT NULL, UNIQUE(segment_id,attempt_number)""",
        "dispatches": """attempt_id TEXT PRIMARY KEY REFERENCES bounded_extraction_attempts(attempt_id),
            fence INTEGER NOT NULL, created_at TEXT NOT NULL, record_sha256 TEXT NOT NULL""",
        "outcomes": """attempt_id TEXT PRIMARY KEY REFERENCES bounded_extraction_dispatches(attempt_id),
            external_outcome TEXT NOT NULL, artifact_relative TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
            provider_request_id TEXT, input_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER,
            cached_input_tokens INTEGER, finish_reason TEXT, classification TEXT NOT NULL,
            created_at TEXT NOT NULL, record_sha256 TEXT NOT NULL""",
        "segment_results": """segment_id TEXT PRIMARY KEY REFERENCES bounded_extraction_segments(segment_id),
            attempt_id TEXT NOT NULL UNIQUE REFERENCES bounded_extraction_outcomes(attempt_id),
            result_type TEXT NOT NULL CHECK(result_type IN ('COMPLETE','SUBDIVISION_REQUIRED')),
            result_sha256 TEXT NOT NULL, artifact_relative TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL, record_sha256 TEXT NOT NULL""",
        "series_results": """series_id TEXT PRIMARY KEY REFERENCES bounded_extraction_series(series_id),
            coverage_sha256 TEXT NOT NULL, ordered_result_shas_json TEXT NOT NULL, aggregate_wire_sha256 TEXT NOT NULL,
            artifact_relative TEXT NOT NULL, artifact_sha256 TEXT NOT NULL, result_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL, record_sha256 TEXT NOT NULL""",
        "events": """series_id TEXT NOT NULL REFERENCES bounded_extraction_series(series_id), sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL, body_json TEXT NOT NULL, previous_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL, event_sha256 TEXT NOT NULL, PRIMARY KEY(series_id,sequence)""",
    }
    for name, definition in definitions.items():
        table = PREFIX + name
        connection.execute(f"CREATE TABLE {table}({definition})")
        for action in ("UPDATE", "DELETE"):
            connection.execute(f"CREATE TRIGGER {table}_{action.lower()} BEFORE {action} ON {table} "
                               "BEGIN SELECT RAISE(ABORT,'IMMUTABLE_BOUNDED_AUDIT'); END")
    connection.execute("""CREATE TRIGGER bounded_result_attempt_binding BEFORE INSERT ON bounded_extraction_segment_results
        WHEN NOT EXISTS(SELECT 1 FROM bounded_extraction_attempts WHERE attempt_id=NEW.attempt_id AND segment_id=NEW.segment_id)
        BEGIN SELECT RAISE(ABORT,'RESULT_ATTEMPT_MISMATCH'); END""")


def _drained(connection):
    _require_drain(connection)
    existing = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if PREFIX + "series" in existing and connection.execute(
        "SELECT 1 FROM bounded_extraction_series WHERE state NOT IN ('SUCCEEDED_COMPLETE','FAILED') LIMIT 1"
    ).fetchone():
        raise BoundaryError("BOUNDED_MIGRATION_REQUIRES_DRAIN")
    if PREFIX + "segments" in existing and connection.execute(
        "SELECT 1 FROM bounded_extraction_segments WHERE state NOT IN ('SUCCEEDED_COMPLETE','SUPERSEDED_BY_CHILDREN','FAILED') LIMIT 1"
    ).fetchone():
        raise BoundaryError("BOUNDED_MIGRATION_REQUIRES_DRAIN")


def prepare_bounded_extraction_persistence(config):
    """Never called by imports, workers, MCP, or the live SourceOperations path."""
    config.validate()
    path = checked_path(config.state_db)
    if any(path.with_name(path.name + s).exists() for s in ("-wal", "-shm", "-journal")):
        raise BoundaryError("BOUNDED_MIGRATION_REQUIRES_OFFLINE")
    backup = path.with_name(path.name + ".stage-bounded-extraction-v12-backup")
    receipt_path = path.with_name(path.name + ".stage-bounded-extraction-v12-migration.json")
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN EXCLUSIVE")
        version = schema_version(connection)
        if version not in ("11", "12"):
            raise BoundaryError("LIFECYCLE_SCHEMA_REQUIRED")
        _drained(connection)
        existing = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if version == "12":
            if not set(TABLES) <= existing or not backup.exists():
                raise BoundaryError("BOUNDED_SCHEMA_INCOMPLETE")
            backup_sha = hashlib.sha256(checked_path(backup).read_bytes()).hexdigest()
        else:
            if set(TABLES) & existing:
                raise BoundaryError("BOUNDED_SCHEMA_PARTIALLY_PREPARED")
            backup_sha = write_once(backup, path.read_bytes())
            _schema(connection)
            connection.execute("UPDATE workbench_meta SET value='12' WHERE key='schema_version'")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or connection.execute("PRAGMA foreign_key_check").fetchall():
            raise BoundaryError("BOUNDED_MIGRATION_INTEGRITY")
    receipt = {"document_type": "bounded_extraction_persistence_migration_v1", "schema_before": "11",
               "schema_version": "12", "backup_sha256": backup_sha, "production_writes": 0}
    # Receipt publication also uses the writer lock, including idempotent recovery.
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        write_once(receipt_path, canonical(receipt).encode("utf-8"))
    return {**receipt, "status": "ALREADY_PREPARED" if version == "12" else "BOUNDED_EXTRACTION_SCHEMA_PREPARED"}
