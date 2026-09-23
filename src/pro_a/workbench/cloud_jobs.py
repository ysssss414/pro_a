"""Durable single-worker jobs for the Stage 6 cloud contract."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from pro_a.cloud_contract import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    OPERATION_KIND,
    RETRY_OWNER,
    RETRY_POLICY_ID,
    CloudContractError,
    CloudProvider,
    CloudRequest,
    CloudResult,
    ProviderFailure,
    canonical,
    digest,
    now,
    operation_contract,
    validate_output,
)
from pro_a.phase4_orchestration import _runtime as phase4_runtime
from pro_a.production_promotion import sha256_file
from pro_a.semantic_decomposition import build_evidence_units
from .artifacts import Artifacts
from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


STATES = (
    "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "RECOVERY_REQUIRED",
    "BLOCKED_RUNTIME_DRIFT", "BLOCKED",
)
TERMINAL_STATES = ("SUCCEEDED", "FAILED", "RECOVERY_REQUIRED", "BLOCKED_RUNTIME_DRIFT", "BLOCKED")
ACTIVE_PHASES = ("CLAIMED", "DISPATCH_INTENT", "CALL_POSSIBLE", "RESULT_DURABLE")
FAULT_POINTS = (
    "before_claim", "after_claim", "after_dispatch_intent", "before_network_call",
    "after_provider_response", "before_result_artifact_durable",
    "after_result_artifact_durable", "before_terminal_update", "after_terminal_update",
)


class JobError(RuntimeError):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.status = status


class InjectedCrash(RuntimeError):
    pass


@dataclass(frozen=True)
class CloudProfile:
    provider: str
    requested_model: str
    accepted_model_aliases: tuple[str, ...] = ()
    provider_adapter_version: str = ADAPTER_VERSION
    timeout_seconds: int = 120
    max_output_tokens: int = 8192
    max_calls: int = 2
    max_attempts: int = 2
    max_total_tokens: int = 20_000

    @classmethod
    def demo(cls) -> "CloudProfile":
        return cls("DETERMINISTIC_FAKE", "fake-semantic-v1", ("fake-equivalent-v1",),
                   "deterministic-fake-v1", 30, 8192, 2, 2, 20_000)

    @classmethod
    def from_environment(cls) -> "CloudProfile | None":
        provider = os.environ.get("PRO_A_CLOUD_PROVIDER", "").strip()
        model = os.environ.get("PRO_A_CLOUD_MODEL", "").strip()
        if not provider or not model:
            return None
        return cls(provider, model)

    def validate(self) -> None:
        identity = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
        if (not identity.fullmatch(self.provider) or not identity.fullmatch(self.requested_model)
                or not identity.fullmatch(self.provider_adapter_version)
                or any(not identity.fullmatch(item) for item in self.accepted_model_aliases)):
            raise JobError("CLOUD_PROFILE_INVALID", 422)
        if not (1 <= self.timeout_seconds <= 3600 and 1 <= self.max_output_tokens <= 131072
                and 1 <= self.max_calls <= 10 and 1 <= self.max_attempts <= self.max_calls
                and 1 <= self.max_total_tokens <= 1_000_000):
            raise JobError("CLOUD_BUDGET_INVALID", 422)

    def public_identity(self) -> dict[str, Any]:
        value = asdict(self)
        value["accepted_model_aliases"] = list(self.accepted_model_aliases)
        value["retry_owner"] = RETRY_OWNER
        value["retry_policy_id"] = RETRY_POLICY_ID
        value["hidden_fallback"] = False
        value["configuration_sha256"] = digest(value)
        return value


@lru_cache(maxsize=None)
def runtime_identity(adapter_version: str, *, workbench_schema_version: str = "7") -> dict[str, Any]:
    """Identify code loaded by this process; a new process resolves changed code."""
    phase4 = phase4_runtime()
    value = {
        "git_sha": phase4["repository_commit"],
        "phase4_contract_version": phase4["contract_version"],
        "phase4_processing_code_sha256": phase4["processing_code_sha256"],
        "cloud_contract_version": CONTRACT_VERSION,
        "workbench_schema_version": workbench_schema_version,
        "provider_adapter_version": adapter_version,
    }
    if workbench_schema_version in ("9", "10", "11"):
        package = Path(__file__).parent.parent
        names = ('domain_packs.py', 'run_context.py', 'workbench/domains.py',
                 'workbench/source_operations.py', 'workbench/cloud_jobs.py', 'workbench/artifacts.py')
        value["domain_contract_version"] = "run-domain-context-v1"
        value["domain_code_sha256"] = digest({name: sha256_file(package / name) for name in names})
    value["runtime_sha256"] = digest(value)
    return value


def prepare_cloud_jobs(config):
    """Operator-only Workbench v6 -> v7 migration with an exact Stage 5 backup."""
    config.validate()
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version in ("7", "8", "9", "10", "11"):
            return {"status": "ALREADY_PREPARED", "schema_version": version}
        if version != "6":
            raise BoundaryError("RESEARCH_SCHEMA_REQUIRED")
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + ".stage5-backup"), missing=True)
    content = path.read_bytes()
    if backup.exists():
        if backup.read_bytes() != content:
            raise BoundaryError("WORKBENCH_BACKUP_CONFLICT")
    else:
        with backup.open("xb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        if schema_version(connection) != "6":
            raise BoundaryError("WORKBENCH_SCHEMA_CHANGED")
        statements = (
            '''CREATE TABLE cloud_jobs(
                job_id TEXT PRIMARY KEY,
                input_artifact_id TEXT NOT NULL REFERENCES registered_packets(artifact_id),
                input_sha256 TEXT NOT NULL, source_id TEXT NOT NULL,
                operation_kind TEXT NOT NULL CHECK(operation_kind='SEMANTIC_DECOMPOSITION'),
                intent_sha256 TEXT NOT NULL, runtime_json TEXT NOT NULL, runtime_sha256 TEXT NOT NULL,
                prompt_json TEXT NOT NULL, prompt_sha256 TEXT NOT NULL,
                configuration_json TEXT NOT NULL, configuration_sha256 TEXT NOT NULL,
                native_checkpoint_json TEXT NOT NULL,
                provider TEXT NOT NULL, requested_model TEXT NOT NULL,
                accepted_model_aliases_json TEXT NOT NULL, provider_adapter_version TEXT NOT NULL,
                timeout_seconds INTEGER NOT NULL, max_output_tokens INTEGER NOT NULL,
                max_calls INTEGER NOT NULL, max_attempts INTEGER NOT NULL, max_total_tokens INTEGER NOT NULL,
                retry_owner TEXT NOT NULL, retry_policy_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','RECOVERY_REQUIRED','BLOCKED_RUNTIME_DRIFT','BLOCKED')),
                phase TEXT NOT NULL, attempt_count INTEGER NOT NULL DEFAULT 0,
                fence INTEGER NOT NULL DEFAULT 0, lease_owner TEXT, lease_expires_at TEXT,
                reserved_calls INTEGER NOT NULL DEFAULT 0, reserved_tokens INTEGER NOT NULL DEFAULT 0,
                usage_status TEXT NOT NULL DEFAULT 'UNKNOWN', input_tokens INTEGER,
                output_tokens INTEGER, total_tokens INTEGER, cached_tokens INTEGER,
                model_identity_status TEXT, provider_reported_model TEXT, provider_request_id TEXT,
                result_artifact_id TEXT, validation_status TEXT NOT NULL DEFAULT 'NOT_RUN',
                sanitized_error TEXT, created_at TEXT NOT NULL, started_at TEXT, ended_at TEXT, updated_at TEXT NOT NULL
            )''',
            '''CREATE INDEX cloud_jobs_queue ON cloud_jobs(state,created_at,job_id)''',
            '''CREATE TABLE cloud_job_submissions(
                idempotency_key TEXT PRIMARY KEY, intent_sha256 TEXT NOT NULL,
                job_id TEXT NOT NULL UNIQUE REFERENCES cloud_jobs(job_id), response_json TEXT NOT NULL
            )''',
            '''CREATE TABLE cloud_attempts(
                attempt_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES cloud_jobs(job_id),
                attempt_number INTEGER NOT NULL, fence INTEGER NOT NULL,
                request_sha256 TEXT NOT NULL, request_identity_json TEXT NOT NULL,
                dispatch_intent_at TEXT NOT NULL,
                UNIQUE(job_id,attempt_number)
            )''',
            '''CREATE TABLE cloud_attempt_dispatches(
                attempt_id TEXT PRIMARY KEY REFERENCES cloud_attempts(attempt_id),
                call_possible_at TEXT NOT NULL
            )''',
            '''CREATE TABLE cloud_attempt_outcomes(
                attempt_id TEXT PRIMARY KEY REFERENCES cloud_attempts(attempt_id),
                outcome TEXT NOT NULL, external_outcome TEXT NOT NULL,
                provider_reported_model TEXT, provider_request_id TEXT,
                usage_status TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
                total_tokens INTEGER, cached_tokens INTEGER, latency_ms REAL,
                finish_reason TEXT, sanitized_error TEXT, ended_at TEXT NOT NULL
            )''',
            '''CREATE TABLE cloud_job_results(
                result_artifact_id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE REFERENCES cloud_jobs(job_id),
                attempt_id TEXT NOT NULL UNIQUE REFERENCES cloud_attempts(attempt_id),
                artifact_relative TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL,
                validation_status TEXT NOT NULL, validation_identity TEXT NOT NULL,
                created_at TEXT NOT NULL
            )''',
            '''CREATE TABLE cloud_job_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES cloud_jobs(job_id),
                sequence INTEGER NOT NULL, event_type TEXT NOT NULL, event_json TEXT NOT NULL,
                previous_sha256 TEXT NOT NULL, event_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL, UNIQUE(job_id,sequence), UNIQUE(job_id,event_sha256)
            )''',
        )
        for statement in statements:
            connection.execute(statement)
        for table in ("cloud_job_submissions", "cloud_attempts", "cloud_attempt_dispatches", "cloud_attempt_outcomes",
                      "cloud_job_results", "cloud_job_events"):
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"CREATE TRIGGER {table}_{action.lower()}_forbidden BEFORE {action} ON {table} "
                    "BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END"
                )
        connection.execute("UPDATE workbench_meta SET value='7' WHERE key='schema_version'")
    return {"status": "CLOUD_JOBS_SCHEMA_PREPARED", "schema_version": "7",
            "backup_sha256": hashlib.sha256(content).hexdigest()}


class CloudJobs:
    def __init__(self, config, profile: CloudProfile | None = None,
                 *, runtime: Mapping[str, Any] | None = None):
        self.config = config
        self.store = Store(config)
        self.artifacts = Artifacts(config)
        self.profile = profile if profile is not None else (
            CloudProfile.demo() if config.mode == "DEMO" else CloudProfile.from_environment()
        )
        if self.profile is not None:
            self.profile.validate()
        self._runtime_override = dict(runtime) if runtime is not None else None
        self._registered_identity_cache: dict[str, tuple[dict, dict]] = {}

    def current_runtime(self) -> dict[str, Any]:
        if self.profile is None:
            raise JobError("CLOUD_PROFILE_REQUIRED", 503)
        if self._runtime_override is not None:
            return dict(self._runtime_override)
        with self.store.connect() as connection:
            version = schema_version(connection)
        return dict(runtime_identity(self.profile.provider_adapter_version,
                                     workbench_schema_version=version))

    @staticmethod
    def _event(connection: sqlite3.Connection, job_id: str, event_type: str,
               value: Mapping[str, Any] | None = None) -> None:
        prior = connection.execute(
            "SELECT sequence,event_sha256 FROM cloud_job_events WHERE job_id=? ORDER BY sequence DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        sequence = int(prior["sequence"] + 1) if prior else 1
        previous = str(prior["event_sha256"]) if prior else "0" * 64
        created = now()
        body = dict(value or {})
        body_json = canonical(body)
        event_sha = digest({"job_id": job_id, "sequence": sequence, "event_type": event_type,
                            "event": body, "previous_sha256": previous, "created_at": created})
        connection.execute(
            "INSERT INTO cloud_job_events(job_id,sequence,event_type,event_json,previous_sha256,event_sha256,created_at) VALUES(?,?,?,?,?,?,?)",
            (job_id, sequence, event_type, body_json, previous, event_sha, created),
        )

    @staticmethod
    def _verify_event_chain(connection: sqlite3.Connection, job_id: str) -> bool:
        previous = "0" * 64
        expected_sequence = 1
        for row in connection.execute(
                "SELECT * FROM cloud_job_events WHERE job_id=? ORDER BY sequence", (job_id,)):
            if row["sequence"] != expected_sequence or row["previous_sha256"] != previous:
                return False
            body = json.loads(row["event_json"])
            expected = digest({"job_id": job_id, "sequence": row["sequence"],
                               "event_type": row["event_type"], "event": body,
                               "previous_sha256": previous, "created_at": row["created_at"]})
            if expected != row["event_sha256"]:
                return False
            previous = expected
            expected_sequence += 1
        return expected_sequence > 1

    def _native_identity(self, artifact_id: str) -> tuple[dict, Path, dict, dict]:
        with self.store.connect() as connection:
            version = schema_version(connection)
            source_input = (connection.execute(
                "SELECT * FROM source_cloud_inputs WHERE artifact_id=?", (artifact_id,)
            ).fetchone() if version in ("8", "9", "10", "11") else None)
        if source_input is not None:
            try:
                path = self.artifacts.resolve(source_input["artifact_relative"])
            except BoundaryError:
                raise JobError("INPUT_ARTIFACT_UNAVAILABLE") from None
            if sha256_file(path) != source_input["sha256"]:
                raise JobError("INPUT_ARTIFACT_HASH_MISMATCH")
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                required = {
                    "document_type", "schema_version", "operation_kind", "source_id",
                    "source_sha256", "processing_run_id", "native_execution_id",
                    "payload", "payload_sha256", "checkpoint",
                }
                if (not isinstance(document, dict) or set(document) != required
                        or document["document_type"] != "phase42_stage7_cloud_input"
                        or document["schema_version"] != "1"
                        or document["operation_kind"] != source_input["operation_kind"]
                        or document["source_id"] != source_input["source_id"]
                        or document["processing_run_id"] != source_input["processing_run_id"]
                        or document["payload_sha256"] != digest(document["payload"])
                        or canonical(document["checkpoint"]) != source_input["checkpoint_json"]):
                    raise JobError("INPUT_ARTIFACT_BINDING_MISMATCH")
            except JobError:
                raise
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                raise JobError("INPUT_ARTIFACT_INVALID") from None
            from .domains import Domains
            try:
                reference = Domains(self.config).guard(document["processing_run_id"], self)
                if document["checkpoint"].get("domain_context") != reference:
                    raise JobError("INPUT_DOMAIN_CONTEXT_MISMATCH")
            except BoundaryError as error:
                raise JobError(str(error)) from None
            directory = path.parent
            dto = {"packet_file_sha256": source_input["sha256"],
                   "source": {"source_id": source_input["source_id"]}}
            return document, directory, dto, document["checkpoint"]
        packet, run, dto = self.artifacts.native(artifact_id)
        manifest = json.loads(checked_path(run / "run_manifest.json").read_text(encoding="utf-8"))
        checkpoint = {
            "run_id": manifest["run_id"],
            "stage_status": manifest["stage_status"],
            "manifest_sha256": sha256_file(run / "run_manifest.json"),
            "resume_semantics": "REFERENCE_EXISTING_NATIVE_CHECKPOINT_ONLY",
        }
        return packet, run, dto, checkpoint

    def _registered_identity(self, artifact_id: str) -> tuple[dict, dict]:
        """Reuse a validated immutable registration while enqueueing in this process.

        Provider dispatch still calls ``_native_identity`` and revalidates the
        registered files before any external call.
        """
        cached = self._registered_identity_cache.get(artifact_id)
        if cached is None:
            _, _, dto, checkpoint = self._native_identity(artifact_id)
            cached = (dto, checkpoint)
            self._registered_identity_cache[artifact_id] = cached
        return cached

    def submit(self, *, idempotency_key: str, input_artifact_id: str,
               operation_kind: str = OPERATION_KIND) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{15,127}", idempotency_key):
            raise JobError("INVALID_IDEMPOTENCY_KEY", 422)
        if self.profile is None:
            raise JobError("CLOUD_PROFILE_REQUIRED", 503)
        operation = operation_contract(operation_kind)
        runtime = self.current_runtime()
        configuration = self.profile.public_identity()
        with self.store.connect() as connection:
            prior = connection.execute(
                "SELECT s.job_id,j.input_artifact_id,j.operation_kind,j.runtime_sha256,j.prompt_json,"
                "j.configuration_sha256 FROM cloud_job_submissions s "
                "JOIN cloud_jobs j ON j.job_id=s.job_id WHERE s.idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if prior:
                if (prior["input_artifact_id"] != input_artifact_id
                        or prior["operation_kind"] != operation_kind
                        or prior["runtime_sha256"] != runtime["runtime_sha256"]
                        or prior["prompt_json"] != canonical(operation)
                        or prior["configuration_sha256"] != configuration["configuration_sha256"]):
                    raise JobError("IDEMPOTENCY_CONFLICT")
                return {"job": self._project(connection, prior["job_id"]), "duplicate": True}
        dto, checkpoint = self._registered_identity(input_artifact_id)
        prompt_sha = operation["prompt_bundle_sha256"]
        intent = {
            "contract_version": CONTRACT_VERSION,
            "input_artifact_id": input_artifact_id,
            "input_sha256": dto["packet_file_sha256"],
            "source_id": dto["source"]["source_id"],
            "operation": operation,
            "runtime": runtime,
            "configuration": configuration,
            "native_checkpoint": checkpoint,
        }
        intent_sha = digest(intent)
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            if schema_version(connection) not in ("7", "8", "9", "10", "11"):
                raise BoundaryError("CLOUD_JOBS_SCHEMA_REQUIRED")
            prior = connection.execute(
                "SELECT intent_sha256,job_id,response_json FROM cloud_job_submissions WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if prior:
                if prior["intent_sha256"] != intent_sha:
                    raise JobError("IDEMPOTENCY_CONFLICT")
                return {"job": self._project(connection, prior["job_id"]), "duplicate": True}
            job_id = "JOB_" + uuid4().hex.upper()
            created = now()
            connection.execute('''INSERT INTO cloud_jobs(
                job_id,input_artifact_id,input_sha256,source_id,operation_kind,intent_sha256,
                runtime_json,runtime_sha256,prompt_json,prompt_sha256,configuration_json,configuration_sha256,
                native_checkpoint_json,provider,requested_model,accepted_model_aliases_json,provider_adapter_version,
                timeout_seconds,max_output_tokens,max_calls,max_attempts,max_total_tokens,retry_owner,retry_policy_id,
                state,phase,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                job_id, input_artifact_id, dto["packet_file_sha256"], dto["source"]["source_id"],
                operation_kind, intent_sha, canonical(runtime), runtime["runtime_sha256"],
                canonical(operation), prompt_sha, canonical(configuration), configuration["configuration_sha256"],
                canonical(checkpoint), self.profile.provider, self.profile.requested_model,
                canonical(list(self.profile.accepted_model_aliases)), self.profile.provider_adapter_version,
                self.profile.timeout_seconds, self.profile.max_output_tokens, self.profile.max_calls,
                self.profile.max_attempts, self.profile.max_total_tokens, RETRY_OWNER, RETRY_POLICY_ID,
                "QUEUED", "QUEUED", created, created,
            ))
            self._event(connection, job_id, "JOB_CREATED", {
                "operation_kind": operation_kind, "input_artifact_id": input_artifact_id,
                "input_sha256": dto["packet_file_sha256"], "runtime_sha256": runtime["runtime_sha256"],
                "prompt_sha256": prompt_sha, "configuration_sha256": configuration["configuration_sha256"],
            })
            self._event(connection, job_id, "QUEUED")
            response = {"job_id": job_id, "intent_sha256": intent_sha}
            connection.execute("INSERT INTO cloud_job_submissions VALUES(?,?,?,?)",
                               (idempotency_key, intent_sha, job_id, canonical(response)))
            return {"job": self._project(connection, job_id), "duplicate": False}

    @staticmethod
    def _project(connection: sqlite3.Connection, job_id: str) -> dict[str, Any]:
        row = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise JobError("JOB_NOT_FOUND", 404)
        result = dict(row)
        return {
            "job_id": result["job_id"],
            "operation_kind": result["operation_kind"],
            "input": {"artifact_id": result["input_artifact_id"],
                      "sha256": result["input_sha256"], "source_id": result["source_id"]},
            "status": result["state"], "phase": result["phase"],
            "provider": result["provider"], "requested_model": result["requested_model"],
            "provider_reported_model": result["provider_reported_model"],
            "model_identity_status": result["model_identity_status"],
            "provider_request_id": result["provider_request_id"],
            "provider_adapter_version": result["provider_adapter_version"],
            "runtime_identity": json.loads(result["runtime_json"]),
            "prompt_identity": json.loads(result["prompt_json"]),
            "configuration_identity": json.loads(result["configuration_json"]),
            "native_checkpoint": json.loads(result["native_checkpoint_json"]),
            "retry_owner": result["retry_owner"], "retry_policy_id": result["retry_policy_id"],
            "attempt_count": result["attempt_count"],
            "budget": {"max_calls": result["max_calls"], "max_attempts": result["max_attempts"],
                       "max_output_tokens": result["max_output_tokens"],
                       "max_total_tokens": result["max_total_tokens"],
                       "reserved_calls": result["reserved_calls"],
                       "reserved_tokens": result["reserved_tokens"]},
            "usage": {"status": result["usage_status"], "input_tokens": result["input_tokens"],
                      "output_tokens": result["output_tokens"], "total_tokens": result["total_tokens"],
                      "cached_tokens": result["cached_tokens"]},
            "validation_status": result["validation_status"],
            "result_artifact": ({"artifact_id": result["result_artifact_id"],
                                 "status": result["validation_status"]}
                                if result["result_artifact_id"] else None),
            "last_error": result["sanitized_error"],
            "recovery_required": result["state"] == "RECOVERY_REQUIRED",
            "created_at": result["created_at"], "started_at": result["started_at"],
            "ended_at": result["ended_at"], "updated_at": result["updated_at"],
        }

    def get(self, job_id: str) -> dict[str, Any]:
        with self.store.connect() as connection:
            return self._project(connection, job_id)

    def list(self, *, status: str = "", cursor: str | None = None, limit: int = 25) -> dict[str, Any]:
        if status and status not in STATES:
            raise JobError("INVALID_JOB_FILTER", 422)
        if not 1 <= limit <= 100 or (cursor not in (None, "") and not str(cursor).isdigit()):
            raise JobError("INVALID_CURSOR", 422)
        offset = int(cursor or 0)
        clauses, args = (["state=?"], [status]) if status else ([], [])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.store.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM cloud_jobs{where}", args).fetchone()[0]
            ids = [row[0] for row in connection.execute(
                f"SELECT job_id FROM cloud_jobs{where} ORDER BY created_at DESC,job_id LIMIT ? OFFSET ?",
                (*args, limit, offset),
            )]
            items = [self._project(connection, job_id) for job_id in ids]
        return {"items": items, "total": total, "limit": limit, "offset": offset,
                "next_cursor": str(offset + limit) if offset + limit < total else None,
                "previous_cursor": str(max(0, offset - limit)) if offset else None,
                "sort_contract": "created_at DESC, job_id ASC"}

    def events(self, job_id: str, *, cursor: str | None = None, limit: int = 50) -> dict[str, Any]:
        if not 1 <= limit <= 100 or (cursor not in (None, "") and not str(cursor).isdigit()):
            raise JobError("INVALID_CURSOR", 422)
        offset = int(cursor or 0)
        with self.store.connect() as connection:
            self._project(connection, job_id)
            rows = [dict(row) for row in connection.execute('''SELECT sequence,event_type,event_json,
                previous_sha256,event_sha256,created_at FROM cloud_job_events WHERE job_id=?
                ORDER BY sequence LIMIT ? OFFSET ?''', (job_id, limit, offset))]
            total = connection.execute("SELECT COUNT(*) FROM cloud_job_events WHERE job_id=?",
                                       (job_id,)).fetchone()[0]
        for row in rows:
            row["event"] = json.loads(row.pop("event_json"))
        return {"items": rows, "total": total, "limit": limit, "offset": offset,
                "next_cursor": str(offset + limit) if offset + limit < total else None}

    def results(self, job_id: str) -> dict[str, Any]:
        with self.store.connect() as connection:
            self._project(connection, job_id)
            rows = [dict(row) for row in connection.execute('''SELECT result_artifact_id,attempt_id,
                artifact_relative,sha256,validation_status,validation_identity,created_at FROM cloud_job_results
                WHERE job_id=? ORDER BY created_at,result_artifact_id''', (job_id,))]
        for row in rows:
            path, expected_relative = self._artifact_path(job_id, row["attempt_id"], create=False)
            if (row.pop("artifact_relative") != expected_relative or not path.exists()
                    or sha256_file(path) != row["sha256"]):
                raise JobError("RESULT_ARTIFACT_HASH_MISMATCH")
        return {"items": rows, "private_artifacts": True, "raw_output_exposed": False}

    def _input_payload(self, row: sqlite3.Row) -> dict[str, Any]:
        document, run, dto, checkpoint = self._native_identity(row["input_artifact_id"])
        if dto["packet_file_sha256"] != row["input_sha256"]:
            raise JobError("INPUT_ARTIFACT_HASH_MISMATCH")
        if checkpoint != json.loads(row["native_checkpoint_json"]):
            raise JobError("NATIVE_CHECKPOINT_DRIFT")
        if document.get("document_type") == "phase42_stage7_cloud_input":
            if document["operation_kind"] != row["operation_kind"]:
                raise JobError("INPUT_ARTIFACT_BINDING_MISMATCH")
            return dict(document["payload"])
        bundle_path = checked_path(run / "evidence/evidence_bound_extraction_bundle.json")
        if not bundle_path.is_relative_to(run):
            raise JobError("INPUT_ARTIFACT_INVALID")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        claims = []
        for claim in bundle.get("claims") or []:
            evidence_text = str(claim.get("evidence_excerpt") or claim.get("statement") or "")
            locator = str(claim.get("evidence_pointer") or "")
            claims.append({
                "claim_id": str(claim["claim_id"]),
                "claim_text": str(claim["statement"]),
                "evidence_units": build_evidence_units(
                    parent_claim_id=str(claim["claim_id"]), bounded_evidence=evidence_text,
                    source_locator=locator,
                ),
                "attribution": str(claim.get("attributed_to") or ""),
                "scope": str(claim.get("scope") or ""),
                "fact_time": str(claim.get("fact_time") or ""),
                "assigned_nature": str(claim.get("nature") or "fact"),
            })
        if not 1 <= len(claims) <= 10 or any(not item["evidence_units"] for item in claims):
            raise JobError("CLOUD_INPUT_NOT_QUALIFIED")
        return {"claims": claims}

    def _preflight(self, job_id: str, provider: CloudProvider, worker_id: str, fence: int) -> dict[str, Any]:
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise JobError("JOB_NOT_FOUND", 404)
            if not self._verify_event_chain(connection, job_id):
                raise JobError("JOB_EVENT_CHAIN_INCONSISTENT")
        if row["lease_owner"] != worker_id or row["fence"] != fence:
            raise JobError("WORKER_FENCE_LOST")
        try:
            stored_runtime = json.loads(row["runtime_json"])
            stored_runtime_hash = stored_runtime["runtime_sha256"]
            runtime_basis = dict(stored_runtime)
            del runtime_basis["runtime_sha256"]
            current_runtime = self.current_runtime()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise JobError("RUNTIME_IDENTITY_CORRUPT") from None
        if (stored_runtime_hash != digest(runtime_basis)
                or row["runtime_sha256"] != stored_runtime_hash
                or canonical(stored_runtime) != canonical(current_runtime)):
            raise JobError("RUNTIME_DRIFT")
        current_prompt = operation_contract(row["operation_kind"])
        if (canonical(current_prompt) != row["prompt_json"]
                or row["prompt_sha256"] != current_prompt["prompt_bundle_sha256"]):
            raise JobError("PROMPT_IDENTITY_MISMATCH")
        try:
            stored_configuration = json.loads(row["configuration_json"])
            stored_configuration_hash = stored_configuration["configuration_sha256"]
            configuration_basis = dict(stored_configuration)
            del configuration_basis["configuration_sha256"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise JobError("CONFIGURATION_IDENTITY_CORRUPT") from None
        if (stored_configuration_hash != digest(configuration_basis)
                or row["configuration_sha256"] != stored_configuration_hash
                or canonical(stored_configuration) != canonical(self.profile.public_identity())):
            raise JobError("CONFIGURATION_IDENTITY_MISMATCH")
        if (provider.provider_identity != row["provider"]
                or provider.adapter_version != row["provider_adapter_version"]):
            raise JobError("PROVIDER_CONTRACT_MISMATCH")
        checkpoint = json.loads(row["native_checkpoint_json"])
        context = checkpoint.get("domain_context")
        if context is not None:
            from pro_a.cloud_contract import DeterministicFakeProvider
            if not isinstance(context, dict):
                raise JobError("INPUT_DOMAIN_CONTEXT_MISMATCH")
            if context.get("contract_version") == "run-domain-context-v1" and type(provider) is not DeterministicFakeProvider:
                raise JobError("DOMAIN_ACTIVATION_REQUIRED")
            if context.get("contract_version") not in ("run-domain-context-v1", "run-processing-context-v2"):
                raise JobError("INPUT_DOMAIN_CONTEXT_MISMATCH")
        return self._input_payload(row)

    def _claim(self, worker_id: str, job_id: str | None, lease_seconds: int) -> tuple[str, int] | None:
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            claimed_at = now()
            if schema_version(connection) in ("10", "11") and connection.execute(
                """SELECT 1 FROM cloud_jobs
                   WHERE state='RUNNING' AND lease_expires_at>? LIMIT 1""",
                (claimed_at,),
            ).fetchone():
                return None
            if job_id:
                row = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (job_id,)).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM cloud_jobs WHERE state='QUEUED' ORDER BY created_at,job_id LIMIT 1"
                ).fetchone()
            if row is None:
                if job_id:
                    raise JobError("JOB_NOT_FOUND", 404)
                return None
            if row["state"] != "QUEUED":
                return None
            fence = row["fence"] + 1
            started = row["started_at"] or claimed_at
            expiry = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat()
            connection.execute('''UPDATE cloud_jobs SET state='RUNNING',phase='CLAIMED',fence=?,
                lease_owner=?,lease_expires_at=?,started_at=?,updated_at=? WHERE job_id=? AND state='QUEUED' ''',
                               (fence, worker_id, expiry, started, claimed_at, row["job_id"]))
            if connection.total_changes == 0:
                return None
            self._event(connection, row["job_id"], "LEASE_ACQUIRED",
                        {"worker_id": worker_id, "fence": fence, "lease_expires_at": expiry})
            return row["job_id"], fence

    @staticmethod
    def _owned(connection: sqlite3.Connection, job_id: str, worker_id: str, fence: int) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (job_id,)).fetchone()
        if (row is None or row["state"] != "RUNNING" or row["lease_owner"] != worker_id
                or row["fence"] != fence):
            raise JobError("WORKER_FENCE_LOST")
        return row

    def _dispatch_intent(self, job_id: str, worker_id: str, fence: int,
                         payload: Mapping[str, Any]) -> tuple[CloudRequest, str]:
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._owned(connection, job_id, worker_id, fence)
            attempt_number = row["attempt_count"] + 1
            budget_exceeded = (attempt_number > row["max_attempts"] or attempt_number > row["max_calls"]
                    or row["max_output_tokens"] > row["max_total_tokens"]
                    or ((row["total_tokens"] or 0) + row["max_output_tokens"] > row["max_total_tokens"]))
            if budget_exceeded:
                ended = now()
                connection.execute('''UPDATE cloud_jobs SET state='FAILED',phase='TERMINAL',
                    sanitized_error='BUDGET_EXCEEDED',lease_owner=NULL,lease_expires_at=NULL,
                    ended_at=?,updated_at=? WHERE job_id=?''', (ended, ended, job_id))
                self._event(connection, job_id, "FAILED", {"code": "BUDGET_EXCEEDED"})
                request = None
                attempt_id = ""
            else:
                attempt_id = "ATTEMPT_" + uuid4().hex.upper()
                runtime = json.loads(row["runtime_json"])
                prompt = json.loads(row["prompt_json"])
                configuration = json.loads(row["configuration_json"])
                budget = {"max_calls": row["max_calls"], "max_attempts": row["max_attempts"],
                          "max_output_tokens": row["max_output_tokens"],
                          "max_total_tokens": row["max_total_tokens"],
                          "reserved_call": attempt_number, "reserved_output_tokens": row["max_output_tokens"]}
                request = CloudRequest(
                    job_id=job_id, attempt_id=attempt_id, attempt_number=attempt_number,
                    operation_kind=row["operation_kind"], input_artifact_id=row["input_artifact_id"],
                    input_sha256=row["input_sha256"], source_id=row["source_id"],
                    runtime_identity=runtime, schema_version=schema_version(connection), provider=row["provider"],
                    requested_model=row["requested_model"], prompt_identity=prompt,
                    configuration_identity=configuration, timeout_seconds=row["timeout_seconds"],
                    max_output_tokens=row["max_output_tokens"], retry_policy_id=row["retry_policy_id"],
                    budget_identity=budget, payload=payload,
                )
                identity = request.public_identity()
                connection.execute('''INSERT INTO cloud_attempts(attempt_id,job_id,attempt_number,fence,
                    request_sha256,request_identity_json,dispatch_intent_at) VALUES(?,?,?,?,?,?,?)''',
                                   (attempt_id, job_id, attempt_number, fence, request.request_sha256,
                                    canonical(identity), now()))
                connection.execute('''UPDATE cloud_jobs SET phase='DISPATCH_INTENT',attempt_count=?,
                    reserved_calls=1,reserved_tokens=?,updated_at=? WHERE job_id=?''',
                                   (attempt_number, row["max_output_tokens"], now(), job_id))
                self._event(connection, job_id, "BUDGET_RESERVED",
                            {"attempt_id": attempt_id, "calls": 1,
                             "output_tokens": row["max_output_tokens"]})
                self._event(connection, job_id, "DISPATCH_INTENT_RECORDED",
                            {"attempt_id": attempt_id, "attempt_number": attempt_number,
                             "request_sha256": request.request_sha256})
        if request is None:
            raise JobError("BUDGET_EXCEEDED")
        return request, attempt_id

    def _mark_call_possible(self, job_id: str, attempt_id: str, worker_id: str, fence: int) -> None:
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._owned(connection, job_id, worker_id, fence)
            called = now()
            connection.execute("INSERT INTO cloud_attempt_dispatches VALUES(?,?)",
                               (attempt_id, called))
            connection.execute("UPDATE cloud_jobs SET phase='CALL_POSSIBLE',updated_at=? WHERE job_id=?",
                               (called, job_id))
            self._event(connection, job_id, "PROVIDER_ATTEMPT_STARTED",
                        {"attempt_id": attempt_id})

    def _record_provider_failure(self, job_id: str, attempt_id: str, worker_id: str,
                                 fence: int, failure: ProviderFailure) -> bool:
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._owned(connection, job_id, worker_id, fence)
            ended = now()
            connection.execute('''INSERT INTO cloud_attempt_outcomes(attempt_id,outcome,external_outcome,
                usage_status,sanitized_error,ended_at) VALUES(?,?,?,?,?,?)''',
                               (attempt_id, "FAILED", failure.external_outcome,
                                "UNKNOWN", failure.code, ended))
            self._event(connection, job_id, "PROVIDER_ATTEMPT_FAILED",
                        {"attempt_id": attempt_id, "code": failure.code,
                         "external_outcome": failure.external_outcome})
            if failure.external_outcome == "UNKNOWN":
                connection.execute('''UPDATE cloud_jobs SET state='RECOVERY_REQUIRED',phase='UNKNOWN',
                    sanitized_error='UNKNOWN_EXTERNAL_OUTCOME',usage_status='UNKNOWN',
                    reserved_calls=0,reserved_tokens=0,lease_owner=NULL,lease_expires_at=NULL,
                    ended_at=?,updated_at=? WHERE job_id=?''', (ended, ended, job_id))
                self._event(connection, job_id, "RECOVERY_REQUIRED",
                            {"code": "UNKNOWN_EXTERNAL_OUTCOME", "automatic_retry": False})
                return False
            retry = failure.retryable and row["attempt_count"] < min(row["max_attempts"], row["max_calls"])
            if retry:
                connection.execute('''UPDATE cloud_jobs SET phase='CLAIMED',sanitized_error=?,
                    reserved_calls=0,reserved_tokens=0,updated_at=? WHERE job_id=?''',
                                   (failure.code, ended, job_id))
                self._event(connection, job_id, "RETRY_AUTHORIZED",
                            {"owner": RETRY_OWNER, "prior_attempt_id": attempt_id,
                             "next_attempt_number": row["attempt_count"] + 1})
                return True
            connection.execute('''UPDATE cloud_jobs SET state='FAILED',phase='TERMINAL',sanitized_error=?,
                reserved_calls=0,reserved_tokens=0,lease_owner=NULL,lease_expires_at=NULL,
                ended_at=?,updated_at=? WHERE job_id=?''', (failure.code, ended, ended, job_id))
            self._event(connection, job_id, "FAILED", {"code": failure.code})
            return False

    def _artifact_path(self, job_id: str, attempt_id: str, *, create: bool = True) -> tuple[Path, str]:
        relative = f"cloud-results/{job_id}/{attempt_id}.json"
        root = checked_path(self.config.artifact_root)
        directory = checked_path(root / "cloud-results" / job_id, missing=True)
        if create:
            directory.mkdir(parents=True, exist_ok=True)
            directory = checked_path(directory)
        if not directory.is_relative_to(root):
            raise JobError("RESULT_ARTIFACT_PATH_INVALID")
        return checked_path(directory / f"{attempt_id}.json", missing=True), relative

    def _write_result_artifact(self, request: CloudRequest, result: CloudResult,
                               validation_status: str, normalized: Mapping[str, Any] | None,
                               model_identity_status: str,
                               terminal_error: str | None) -> tuple[Path, str, str]:
        path, relative = self._artifact_path(request.job_id, request.attempt_id)
        envelope = {
            "document_type": "phase42_stage6_private_cloud_result",
            "schema_version": "1", "contract_version": CONTRACT_VERSION,
            "job_id": request.job_id, "attempt_id": request.attempt_id,
            "request_sha256": request.request_sha256,
            "provider": result.provider, "requested_model": result.requested_model,
            "provider_reported_model": result.provider_reported_model,
            "provider_request_id": result.provider_request_id,
            "operation_kind": result.operation_kind, "attempt_number": result.attempt_number,
            "started_at": result.started_at, "ended_at": result.ended_at,
            "latency_ms": result.latency_ms, "finish_reason": result.finish_reason,
            "usage": {"status": result.usage_status, "input_tokens": result.input_tokens,
                      "output_tokens": result.output_tokens, "total_tokens": result.total_tokens,
                      "cached_tokens": result.cached_tokens},
            "model_identity_status": model_identity_status,
            "validation_status": validation_status,
            "normalized_error": terminal_error,
            "raw_provider_output": result.output,
            "normalized_output": normalized,
        }
        content = (json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2,
                              allow_nan=False) + "\n").encode("utf-8")
        sha = hashlib.sha256(content).hexdigest()
        if path.exists():
            if path.read_bytes() != content:
                raise JobError("RESULT_ARTIFACT_CONFLICT")
            return path, relative, sha
        temporary = checked_path(path.with_name(path.name + ".tmp"), missing=True)
        with temporary.open("xb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
        return path, relative, sha

    def _register_result(self, request: CloudRequest, result: CloudResult, relative: str,
                         sha: str, validation_status: str, model_status: str,
                         worker_id: str, fence: int, *, terminal_error: str | None = None) -> None:
        result_id = "RESULT_" + sha[:32].upper()
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._owned(connection, request.job_id, worker_id, fence)
            existing = connection.execute("SELECT * FROM cloud_job_results WHERE job_id=?",
                                          (request.job_id,)).fetchone()
            if existing and existing["sha256"] != sha:
                raise JobError("RESULT_ARTIFACT_CONFLICT")
            if not existing:
                connection.execute('''INSERT INTO cloud_job_results VALUES(?,?,?,?,?,?,?,?)''',
                                   (result_id, request.job_id, request.attempt_id, relative, sha,
                                    validation_status, digest({"validator": "existing-proposition-ir-v2.1",
                                                               "status": validation_status}), now()))
                connection.execute('''INSERT INTO cloud_attempt_outcomes(attempt_id,outcome,external_outcome,
                    provider_reported_model,provider_request_id,usage_status,input_tokens,output_tokens,
                    total_tokens,cached_tokens,latency_ms,finish_reason,sanitized_error,ended_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                request.attempt_id, "COMPLETED" if terminal_error is None else "REJECTED",
                    "KNOWN_SUCCESS",
                    result.provider_reported_model, result.provider_request_id, result.usage_status,
                    result.input_tokens, result.output_tokens, result.total_tokens, result.cached_tokens,
                    result.latency_ms, result.finish_reason, terminal_error, result.ended_at,
                ))
            values = {
                "usage_status": result.usage_status, "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens, "total_tokens": result.total_tokens,
                "cached_tokens": result.cached_tokens, "model_identity_status": model_status,
                "provider_reported_model": result.provider_reported_model,
                "provider_request_id": result.provider_request_id, "result_artifact_id": result_id,
                "validation_status": validation_status, "sanitized_error": terminal_error,
            }
            connection.execute('''UPDATE cloud_jobs SET phase='RESULT_DURABLE',reserved_calls=0,
                reserved_tokens=0,usage_status=:usage_status,input_tokens=:input_tokens,
                output_tokens=:output_tokens,total_tokens=:total_tokens,cached_tokens=:cached_tokens,
                model_identity_status=:model_identity_status,provider_reported_model=:provider_reported_model,
                provider_request_id=:provider_request_id,result_artifact_id=:result_artifact_id,
                validation_status=:validation_status,sanitized_error=:sanitized_error,updated_at=:updated_at
                WHERE job_id=:job_id''', {**values, "updated_at": now(), "job_id": request.job_id})
            self._event(connection, request.job_id, "PROVIDER_ATTEMPT_COMPLETED",
                        {"attempt_id": request.attempt_id, "usage_status": result.usage_status,
                         "model_identity_status": model_status})
            self._event(connection, request.job_id, "OUTPUT_VALIDATED",
                        {"attempt_id": request.attempt_id, "status": validation_status})
            self._event(connection, request.job_id, "RESULT_REGISTERED",
                        {"result_artifact_id": result_id, "sha256": sha,
                         "validation_status": validation_status})

    def _terminal(self, job_id: str, worker_id: str, fence: int, *, error: str | None = None) -> None:
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._owned(connection, job_id, worker_id, fence)
            ended = now()
            state = "FAILED" if error else "SUCCEEDED"
            connection.execute('''UPDATE cloud_jobs SET state=?,phase='TERMINAL',sanitized_error=?,
                lease_owner=NULL,lease_expires_at=NULL,ended_at=?,updated_at=? WHERE job_id=?''',
                               (state, error, ended, ended, job_id))
            self._event(connection, job_id, state,
                        {"code": error} if error else {"result_registered": True})

    @staticmethod
    def _fault(point: str | None, expected: str) -> None:
        if point == expected:
            raise InjectedCrash(expected)

    def run_once(self, provider: CloudProvider, *, worker_id: str,
                 job_id: str | None = None, lease_seconds: int | None = None,
                 fault_at: str | None = None) -> dict[str, Any] | None:
        if fault_at is not None and fault_at not in FAULT_POINTS:
            raise ValueError("INVALID_FAULT_POINT")
        effective_lease = (self.profile.timeout_seconds + 60
                           if lease_seconds is None and self.profile is not None
                           else 180 if lease_seconds is None else lease_seconds)
        if not 0 <= effective_lease <= 3660:
            raise ValueError("INVALID_LEASE_SECONDS")
        self._fault(fault_at, "before_claim")
        claimed = self._claim(worker_id, job_id, effective_lease)
        if claimed is None:
            return None
        current_job, fence = claimed
        self._fault(fault_at, "after_claim")
        try:
            payload = self._preflight(current_job, provider, worker_id, fence)
        except (JobError, BoundaryError, CloudContractError) as error:
            code = str(error)
            state = "BLOCKED_RUNTIME_DRIFT" if code == "RUNTIME_DRIFT" else "BLOCKED"
            with self.store.connect(operator_write=True) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._owned(connection, current_job, worker_id, fence)
                ended = now()
                connection.execute('''UPDATE cloud_jobs SET state=?,phase='TERMINAL',sanitized_error=?,
                    lease_owner=NULL,lease_expires_at=NULL,ended_at=?,updated_at=? WHERE job_id=?''',
                                   (state, code, ended, ended, current_job))
                self._event(connection, current_job, state, {"code": code})
            return self.get(current_job)
        while True:
            try:
                request, attempt_id = self._dispatch_intent(current_job, worker_id, fence, payload)
            except JobError as error:
                if str(error) == "BUDGET_EXCEEDED":
                    return self.get(current_job)
                raise
            self._fault(fault_at, "after_dispatch_intent")
            self._mark_call_possible(current_job, attempt_id, worker_id, fence)
            self._fault(fault_at, "before_network_call")
            try:
                result = provider.invoke(request)
            except ProviderFailure as failure:
                retry = self._record_provider_failure(current_job, attempt_id, worker_id, fence, failure)
                if retry:
                    continue
                return self.get(current_job)
            self._fault(fault_at, "after_provider_response")
            with self.store.connect() as connection:
                job_row = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?",
                                             (current_job,)).fetchone()
                aliases = set(json.loads(job_row["accepted_model_aliases_json"]))
            if result.provider != request.provider or result.requested_model != request.requested_model:
                model_status, terminal_error = "MISMATCH", "PROVIDER_IDENTITY_MISMATCH"
            elif result.provider_reported_model == request.requested_model:
                model_status, terminal_error = "EXACT", None
            elif result.provider_reported_model in aliases:
                model_status, terminal_error = "ACCEPTED_ALIAS", None
            else:
                model_status, terminal_error = "MISMATCH", "MODEL_IDENTITY_MISMATCH"
            normalized = None
            validation_status = "NOT_RUN"
            if terminal_error is None:
                try:
                    normalized = validate_output(request, result.output)
                    validation_status = "PASS"
                except CloudContractError:
                    validation_status = "FAIL"
                    terminal_error = "OUTPUT_VALIDATION_FAILED"
            self._fault(fault_at, "before_result_artifact_durable")
            _, relative, sha = self._write_result_artifact(
                request, result, validation_status, normalized, model_status, terminal_error
            )
            self._fault(fault_at, "after_result_artifact_durable")
            self._register_result(request, result, relative, sha, validation_status, model_status,
                                  worker_id, fence, terminal_error=terminal_error)
            self._fault(fault_at, "before_terminal_update")
            self._terminal(current_job, worker_id, fence, error=terminal_error)
            self._fault(fault_at, "after_terminal_update")
            return self.get(current_job)

    def _reconcile_artifact(self, connection: sqlite3.Connection, row: sqlite3.Row) -> bool:
        attempt = connection.execute(
            "SELECT * FROM cloud_attempts WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1",
            (row["job_id"],),
        ).fetchone()
        if attempt is None:
            return False
        path, relative = self._artifact_path(row["job_id"], attempt["attempt_id"], create=False)
        if not path.exists():
            return False
        try:
            content = path.read_bytes()
            envelope = json.loads(content)
            required = {
                "document_type", "schema_version", "contract_version", "job_id", "attempt_id",
                "request_sha256", "provider", "requested_model", "provider_reported_model",
                "provider_request_id", "operation_kind", "attempt_number", "started_at", "ended_at",
                "latency_ms", "finish_reason", "usage", "model_identity_status", "validation_status",
                "normalized_error", "raw_provider_output", "normalized_output",
            }
            if (not isinstance(envelope, dict) or set(envelope) != required
                    or envelope["document_type"] != "phase42_stage6_private_cloud_result"
                    or envelope["schema_version"] != "1"
                    or envelope["contract_version"] != CONTRACT_VERSION
                    or envelope["job_id"] != row["job_id"]
                    or envelope["attempt_id"] != attempt["attempt_id"]
                    or envelope["request_sha256"] != attempt["request_sha256"]):
                raise JobError("RESULT_ARTIFACT_BINDING_MISMATCH")
            expected_content = (json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2,
                                           allow_nan=False) + "\n").encode("utf-8")
            if content != expected_content:
                raise JobError("RESULT_ARTIFACT_ENCODING_MISMATCH")
            payload = self._input_payload(row)
            attempt_identity = json.loads(attempt["request_identity_json"])
            request = CloudRequest(
                job_id=row["job_id"], attempt_id=attempt["attempt_id"],
                attempt_number=attempt["attempt_number"], operation_kind=row["operation_kind"],
                input_artifact_id=row["input_artifact_id"], input_sha256=row["input_sha256"],
                source_id=row["source_id"], runtime_identity=json.loads(row["runtime_json"]),
                schema_version=str(attempt_identity["schema_version"]), provider=row["provider"], requested_model=row["requested_model"],
                prompt_identity=json.loads(row["prompt_json"]),
                configuration_identity=json.loads(row["configuration_json"]),
                timeout_seconds=row["timeout_seconds"], max_output_tokens=row["max_output_tokens"],
                retry_policy_id=row["retry_policy_id"], budget_identity=attempt_identity["budget_identity"],
                payload=payload,
            )
            if request.public_identity() != attempt_identity or request.request_sha256 != attempt["request_sha256"]:
                raise JobError("RESULT_ARTIFACT_BINDING_MISMATCH")
            usage = envelope["usage"]
            result = CloudResult(
                provider=envelope["provider"], requested_model=envelope["requested_model"],
                provider_reported_model=envelope["provider_reported_model"],
                provider_request_id=envelope["provider_request_id"], operation_kind=envelope["operation_kind"],
                attempt_number=envelope["attempt_number"], started_at=envelope["started_at"],
                ended_at=envelope["ended_at"], latency_ms=envelope["latency_ms"],
                finish_reason=envelope["finish_reason"], usage_status=usage["status"],
                input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
                total_tokens=usage.get("total_tokens"), cached_tokens=usage.get("cached_tokens"),
                output=envelope["raw_provider_output"],
            )
            aliases = set(json.loads(row["accepted_model_aliases_json"]))
            if result.provider != request.provider or result.requested_model != request.requested_model:
                model_status, terminal_error = "MISMATCH", "PROVIDER_IDENTITY_MISMATCH"
            elif result.provider_reported_model == request.requested_model:
                model_status, terminal_error = "EXACT", None
            elif result.provider_reported_model in aliases:
                model_status, terminal_error = "ACCEPTED_ALIAS", None
            else:
                model_status, terminal_error = "MISMATCH", "MODEL_IDENTITY_MISMATCH"
            normalized = None
            validation_status = "NOT_RUN"
            if terminal_error is None:
                try:
                    normalized = validate_output(request, result.output)
                    validation_status = "PASS"
                except CloudContractError:
                    validation_status = "FAIL"
                    terminal_error = "OUTPUT_VALIDATION_FAILED"
            if (envelope["model_identity_status"] != model_status
                    or envelope["validation_status"] != validation_status
                    or envelope["normalized_error"] != terminal_error
                    or canonical(envelope["normalized_output"]) != canonical(normalized)):
                raise JobError("RESULT_ARTIFACT_VALIDATION_MISMATCH")
        except JobError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, CloudContractError):
            raise JobError("RESULT_ARTIFACT_INVALID") from None
        sha = hashlib.sha256(content).hexdigest()
        result_id = "RESULT_" + sha[:32].upper()
        existing = connection.execute("SELECT * FROM cloud_job_results WHERE job_id=?",
                                      (row["job_id"],)).fetchone()
        if existing and (existing["attempt_id"] != attempt["attempt_id"]
                         or existing["artifact_relative"] != relative
                         or existing["sha256"] != sha
                         or existing["validation_status"] != validation_status
                         or existing["result_artifact_id"] != result_id):
            raise JobError("RESULT_REGISTRATION_CONFLICT")
        if not existing:
            connection.execute("INSERT INTO cloud_job_results VALUES(?,?,?,?,?,?,?,?)", (
                result_id, row["job_id"], attempt["attempt_id"], relative, sha,
                validation_status, digest({"validator": "existing-proposition-ir-v2.1",
                                           "status": validation_status}), now(),
            ))
            connection.execute('''INSERT INTO cloud_attempt_outcomes(attempt_id,outcome,external_outcome,
                provider_reported_model,provider_request_id,usage_status,input_tokens,output_tokens,total_tokens,
                cached_tokens,latency_ms,finish_reason,sanitized_error,ended_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                attempt["attempt_id"], "COMPLETED" if validation_status == "PASS" else "REJECTED",
                "KNOWN_SUCCESS",
                envelope["provider_reported_model"], envelope.get("provider_request_id"), usage["status"],
                usage.get("input_tokens"), usage.get("output_tokens"), usage.get("total_tokens"),
                usage.get("cached_tokens"), envelope["latency_ms"], envelope["finish_reason"],
                terminal_error, envelope["ended_at"],
            ))
            connection.execute('''UPDATE cloud_jobs SET phase='RESULT_DURABLE',result_artifact_id=?,
                validation_status=?,model_identity_status=?,provider_reported_model=?,provider_request_id=?,
                usage_status=?,input_tokens=?,output_tokens=?,total_tokens=?,cached_tokens=?,
                reserved_calls=0,reserved_tokens=0,sanitized_error=?,updated_at=? WHERE job_id=?''', (
                result_id, validation_status, envelope["model_identity_status"],
                envelope["provider_reported_model"], envelope.get("provider_request_id"), usage["status"],
                usage.get("input_tokens"), usage.get("output_tokens"), usage.get("total_tokens"),
                usage.get("cached_tokens"), terminal_error, now(), row["job_id"],
            ))
            self._event(connection, row["job_id"], "RECONCILED",
                        {"from": "DURABLE_RESULT_ARTIFACT", "provider_call_repeated": False})
        return True

    def private_result(self, job_id: str) -> dict[str, Any]:
        """Return a verified private result to trusted orchestration code only."""
        self.results(job_id)
        with self.store.connect() as connection:
            job = connection.execute("SELECT state FROM cloud_jobs WHERE job_id=?", (job_id,)).fetchone()
            row = connection.execute(
                "SELECT attempt_id,artifact_relative,sha256 FROM cloud_job_results WHERE job_id=?",
                (job_id,),
            ).fetchone()
        if job is None:
            raise JobError("JOB_NOT_FOUND", 404)
        if row is None or job["state"] not in ("SUCCEEDED", "FAILED"):
            raise JobError("RESULT_NOT_AVAILABLE")
        path, expected = self._artifact_path(job_id, row["attempt_id"], create=False)
        if row["artifact_relative"] != expected or sha256_file(path) != row["sha256"]:
            raise JobError("RESULT_ARTIFACT_HASH_MISMATCH")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            raise JobError("RESULT_ARTIFACT_INVALID") from None

    def reconcile(self) -> dict[str, int]:
        counts = {"requeued": 0, "reconciled": 0, "recovery_required": 0,
                  "runtime_blocked": 0, "unchanged": 0}
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = list(connection.execute(
                "SELECT * FROM cloud_jobs WHERE state NOT IN ('SUCCEEDED','FAILED','RECOVERY_REQUIRED','BLOCKED_RUNTIME_DRIFT','BLOCKED') ORDER BY created_at,job_id"
            ))
            current_runtime_sha = self.current_runtime().get("runtime_sha256")
            current_time = datetime.now(timezone.utc)
            for row in rows:
                if not self._verify_event_chain(connection, row["job_id"]):
                    connection.execute('''UPDATE cloud_jobs SET state='RECOVERY_REQUIRED',phase='UNKNOWN',
                        sanitized_error='JOB_EVENT_CHAIN_INCONSISTENT',lease_owner=NULL,lease_expires_at=NULL,
                        ended_at=?,updated_at=? WHERE job_id=?''', (now(), now(), row["job_id"]))
                    counts["recovery_required"] += 1
                    continue
                if row["runtime_sha256"] != current_runtime_sha:
                    connection.execute('''UPDATE cloud_jobs SET state='BLOCKED_RUNTIME_DRIFT',phase='TERMINAL',
                        sanitized_error='RUNTIME_DRIFT',lease_owner=NULL,lease_expires_at=NULL,
                        ended_at=?,updated_at=? WHERE job_id=?''', (now(), now(), row["job_id"]))
                    self._event(connection, row["job_id"], "BLOCKED_RUNTIME_DRIFT",
                                {"automatic_resume": False})
                    counts["runtime_blocked"] += 1
                    continue
                if row["state"] == "QUEUED":
                    counts["unchanged"] += 1
                    continue
                expiry = datetime.fromisoformat(row["lease_expires_at"]) if row["lease_expires_at"] else current_time
                if expiry > current_time:
                    counts["unchanged"] += 1
                    continue
                try:
                    artifact_ready = self._reconcile_artifact(connection, row)
                except (JobError, BoundaryError, CloudContractError) as error:
                    code = str(error)
                    connection.execute('''UPDATE cloud_jobs SET state='RECOVERY_REQUIRED',phase='UNKNOWN',
                        sanitized_error=?,lease_owner=NULL,lease_expires_at=NULL,
                        reserved_calls=0,reserved_tokens=0,ended_at=?,updated_at=? WHERE job_id=?''',
                                       (code, now(), now(), row["job_id"]))
                    self._event(connection, row["job_id"], "RECOVERY_REQUIRED",
                                {"code": code, "automatic_retry": False})
                    counts["recovery_required"] += 1
                    continue
                if artifact_ready:
                    refreshed = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?",
                                                   (row["job_id"],)).fetchone()
                    error = (None if refreshed["validation_status"] == "PASS"
                             and refreshed["model_identity_status"] in ("EXACT", "ACCEPTED_ALIAS")
                             else refreshed["sanitized_error"] or "OUTPUT_VALIDATION_FAILED")
                    state = "SUCCEEDED" if error is None else "FAILED"
                    connection.execute('''UPDATE cloud_jobs SET state=?,phase='TERMINAL',sanitized_error=?,
                        lease_owner=NULL,lease_expires_at=NULL,ended_at=?,updated_at=? WHERE job_id=?''',
                                       (state, error, now(), now(), row["job_id"]))
                    self._event(connection, row["job_id"], state,
                                {"reconciled": True, "provider_call_repeated": False})
                    counts["reconciled"] += 1
                elif row["phase"] in ("CLAIMED", "DISPATCH_INTENT"):
                    attempt = connection.execute(
                        "SELECT * FROM cloud_attempts WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1",
                        (row["job_id"],),
                    ).fetchone()
                    if attempt and not connection.execute(
                            "SELECT 1 FROM cloud_attempt_outcomes WHERE attempt_id=?",
                            (attempt["attempt_id"],)).fetchone():
                        connection.execute('''INSERT INTO cloud_attempt_outcomes(attempt_id,outcome,
                            external_outcome,usage_status,sanitized_error,ended_at)
                            VALUES(?,'ABANDONED','NOT_DISPATCHED','UNKNOWN','WORKER_LOST_BEFORE_CALL',?)''',
                                           (attempt["attempt_id"], now()))
                    connection.execute('''UPDATE cloud_jobs SET state='QUEUED',phase='QUEUED',
                        lease_owner=NULL,lease_expires_at=NULL,reserved_calls=0,reserved_tokens=0,
                        updated_at=? WHERE job_id=?''', (now(), row["job_id"]))
                    self._event(connection, row["job_id"], "REQUEUED",
                                {"reason": "PROVEN_PRE_DISPATCH", "provider_call_repeated": False})
                    counts["requeued"] += 1
                else:
                    connection.execute('''UPDATE cloud_jobs SET state='RECOVERY_REQUIRED',phase='UNKNOWN',
                        sanitized_error='UNKNOWN_EXTERNAL_OUTCOME',lease_owner=NULL,lease_expires_at=NULL,
                        reserved_calls=0,reserved_tokens=0,ended_at=?,updated_at=? WHERE job_id=?''',
                                       (now(), now(), row["job_id"]))
                    self._event(connection, row["job_id"], "RECOVERY_REQUIRED",
                                {"automatic_retry": False})
                    counts["recovery_required"] += 1
        return counts
