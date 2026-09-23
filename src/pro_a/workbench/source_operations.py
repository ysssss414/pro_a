"""Private clean-PDF Source operations over the native Phase 4 and Stage 6 seams."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, AsyncIterable, Mapping
from uuid import uuid4

from pypdf import PdfReader

from pro_a.config import load_config
from pro_a.operational_ingestion import plan_external_source_analysis
from pro_a.phase4_orchestration import resume_execution, start_execution
from pro_a.phase4_retry import RetryPolicy
from pro_a.production_promotion import canonical_sha256, deterministic_id, sha256_file
from pro_a.semantic_decomposition import (
    SEMANTIC_MAX_PARENTS_PER_BATCH,
    SemanticDecompositionError,
    partition_semantic_claims,
)
from .artifacts import Artifacts
from .cloud_jobs import CloudJobs, CloudProfile, JobError
from .config import BoundaryError, WorkbenchConfig, checked_path
from .review_store import schema_version
from .review_workbench import ReviewWorkbench
from .store import Store
from .domains import Domains


PDF_MIME = "application/pdf"
DEFAULT_MAX_PDF_BYTES = 20 * 1024 * 1024
MIN_MAX_PDF_BYTES = 1024 * 1024
MAX_MAX_PDF_BYTES = 50 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
SOURCE_ANALYSIS_OPERATION = "SOURCE_ANALYSIS_PIECE"
SEMANTIC_OPERATION = "SEMANTIC_DECOMPOSITION"
SOURCE_STATES = (
    "REGISTERED", "QUEUED", "PARSING", "EXTRACTION_PROCESSING",
    "SEMANTIC_PROCESSING", "PACKET_PREPARATION", "HUMAN_REVIEW_REQUIRED",
    "FAILED", "BLOCKED", "RECOVERY_REQUIRED",
)
TERMINAL_PROCESSING_STATES = (
    "HUMAN_REVIEW_REQUIRED", "FAILED", "BLOCKED", "RECOVERY_REQUIRED",
)
MAX_STAGE1_JOBS_PER_RUN = 31


class SourceOperationError(RuntimeError):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.status = status


@dataclass(frozen=True)
class SourceProfile:
    phase4_config_path: Path
    max_pdf_bytes: int = DEFAULT_MAX_PDF_BYTES
    max_extraction_pieces: int = 16

    def validate(self) -> None:
        path = checked_path(Path(self.phase4_config_path))
        if not path.is_file():
            raise SourceOperationError("PHASE4_CONFIG_UNAVAILABLE", 503)
        if not MIN_MAX_PDF_BYTES <= self.max_pdf_bytes <= MAX_MAX_PDF_BYTES:
            raise SourceOperationError("SOURCE_SIZE_LIMIT_INVALID", 422)
        if not 1 <= self.max_extraction_pieces <= 64:
            raise SourceOperationError("SOURCE_PIECE_LIMIT_INVALID", 422)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _safe_filename(value: str) -> str:
    candidate = PureWindowsPath(value).name
    candidate = Path(candidate).name
    candidate = "".join(character for character in candidate if character >= " " and character != "\x7f")
    candidate = candidate.strip().rstrip(".")
    if not candidate or len(candidate) > 240:
        raise SourceOperationError("INVALID_SOURCE_FILENAME", 422)
    if not candidate.lower().endswith(".pdf"):
        raise SourceOperationError("UNSUPPORTED_SOURCE_EXTENSION", 415)
    return candidate


def _cloud_jobs_table() -> str:
    return '''CREATE TABLE cloud_jobs(
        job_id TEXT PRIMARY KEY,
        input_artifact_id TEXT NOT NULL REFERENCES registered_packets(artifact_id),
        input_sha256 TEXT NOT NULL, source_id TEXT NOT NULL,
        operation_kind TEXT NOT NULL CHECK(operation_kind IN ('SEMANTIC_DECOMPOSITION','SOURCE_ANALYSIS_PIECE')),
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
    )'''


def prepare_source_operations(config: WorkbenchConfig) -> dict[str, Any]:
    """Operator-only Workbench v7 -> v8 migration with an exact Stage 6 backup."""
    config.validate()
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version in ("8", "9", "10", "11"):
            return {"status": "ALREADY_PREPARED", "schema_version": version}
        if version != "7":
            raise BoundaryError("CLOUD_JOBS_SCHEMA_REQUIRED")
    path = checked_path(config.state_db)
    backup = checked_path(path.with_name(path.name + ".stage6-backup"), missing=True)
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
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        if schema_version(connection) != "7":
            raise BoundaryError("WORKBENCH_SCHEMA_CHANGED")
        connection.execute(
            "ALTER TABLE registered_packets ADD COLUMN artifact_kind TEXT NOT NULL "
            "DEFAULT 'REVIEW_PACKET' CHECK(artifact_kind IN "
            "('REVIEW_PACKET','SOURCE_ANALYSIS_INPUT','SEMANTIC_INPUT'))"
        )
        connection.execute(_cloud_jobs_table().replace("cloud_jobs(", "cloud_jobs_stage7("))
        columns = [row[1] for row in connection.execute("PRAGMA table_info(cloud_jobs)")]
        joined = ",".join(columns)
        connection.execute(f"INSERT INTO cloud_jobs_stage7({joined}) SELECT {joined} FROM cloud_jobs")
        connection.execute("DROP TABLE cloud_jobs")
        connection.execute("ALTER TABLE cloud_jobs_stage7 RENAME TO cloud_jobs")
        connection.execute("CREATE INDEX cloud_jobs_queue ON cloud_jobs(state,created_at,job_id)")
        statements = (
            '''CREATE TABLE private_sources(
                source_id TEXT PRIMARY KEY, source_sha256 TEXT UNIQUE NOT NULL,
                size_bytes INTEGER NOT NULL CHECK(size_bytes > 0), safe_filename TEXT NOT NULL,
                mime_type TEXT NOT NULL CHECK(mime_type='application/pdf'),
                storage_artifact_id TEXT UNIQUE NOT NULL, storage_relative TEXT UNIQUE NOT NULL,
                validation_json TEXT NOT NULL, canonical_source_id TEXT,
                uploaded_at TEXT NOT NULL)''',
            '''CREATE TABLE source_upload_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT,
                outcome TEXT NOT NULL, filename_sha256 TEXT NOT NULL,
                source_sha256 TEXT, size_bytes INTEGER NOT NULL,
                detail_code TEXT NOT NULL, created_at TEXT NOT NULL)''',
            '''CREATE TABLE source_processing_runs(
                processing_run_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES private_sources(source_id),
                idempotency_key TEXT UNIQUE NOT NULL, runtime_json TEXT NOT NULL, runtime_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('REGISTERED','QUEUED','PARSING','EXTRACTION_PROCESSING','SEMANTIC_PROCESSING','PACKET_PREPARATION','HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED','RECOVERY_REQUIRED')),
                stage TEXT NOT NULL, native_execution_id TEXT, native_root_relative TEXT,
                packet_artifact_id TEXT REFERENCES registered_packets(artifact_id), packet_id TEXT,
                error_code TEXT, retry_safe INTEGER NOT NULL DEFAULT 0,
                manual_recovery_required INTEGER NOT NULL DEFAULT 0,
                reprocess_reason TEXT NOT NULL DEFAULT '', fence INTEGER NOT NULL DEFAULT 0,
                lease_owner TEXT, lease_expires_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, ended_at TEXT)''',
            '''CREATE TABLE source_processing_jobs(
                processing_run_id TEXT NOT NULL REFERENCES source_processing_runs(processing_run_id),
                ordinal INTEGER NOT NULL, operation_kind TEXT NOT NULL,
                cloud_input_artifact_id TEXT NOT NULL UNIQUE REFERENCES registered_packets(artifact_id),
                job_id TEXT NOT NULL UNIQUE REFERENCES cloud_jobs(job_id),
                PRIMARY KEY(processing_run_id,operation_kind,ordinal))''',
            '''CREATE TABLE source_cloud_inputs(
                artifact_id TEXT PRIMARY KEY REFERENCES registered_packets(artifact_id),
                processing_run_id TEXT NOT NULL REFERENCES source_processing_runs(processing_run_id),
                source_id TEXT NOT NULL REFERENCES private_sources(source_id),
                operation_kind TEXT NOT NULL, ordinal INTEGER NOT NULL,
                artifact_relative TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL,
                checkpoint_json TEXT NOT NULL,
                UNIQUE(processing_run_id,operation_kind,ordinal))''',
            '''CREATE TABLE source_processing_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                processing_run_id TEXT NOT NULL REFERENCES source_processing_runs(processing_run_id),
                sequence INTEGER NOT NULL, event_type TEXT NOT NULL, event_json TEXT NOT NULL,
                previous_sha256 TEXT NOT NULL, event_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(processing_run_id,sequence), UNIQUE(processing_run_id,event_sha256))''',
        )
        for statement in statements:
            connection.execute(statement)
        for table in ("private_sources", "source_upload_events", "source_processing_jobs",
                      "source_cloud_inputs", "source_processing_events"):
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"CREATE TRIGGER {table}_{action.lower()}_forbidden BEFORE {action} ON {table} "
                    "BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END"
                )
        connection.execute("UPDATE workbench_meta SET value='8' WHERE key='schema_version'")
    with Store(config).connect() as connection:
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise BoundaryError("SOURCE_SCHEMA_FOREIGN_KEY_FAILURE")
    return {"status": "SOURCE_OPERATIONS_SCHEMA_PREPARED", "schema_version": "8",
            "backup_sha256": hashlib.sha256(content).hexdigest()}


class _ExtractionReplay:
    def __init__(self, cfg: Any, responses: Mapping[str, dict[str, Any]], metadata: Mapping[str, dict[str, Any]]):
        self.cfg = cfg
        self._responses = {key: copy.deepcopy(value) for key, value in responses.items()}
        self._metadata = {key: copy.deepcopy(value) for key, value in metadata.items()}
        self._last: dict[str, Any] = {}

    @property
    def available(self) -> bool:
        return True

    @property
    def last_call_metadata(self) -> dict[str, Any]:
        return copy.deepcopy(self._last)

    def json(self, _system: str, user: str) -> dict[str, Any]:
        identity = hashlib.sha256(user.encode("utf-8")).hexdigest()
        if identity not in self._responses:
            raise RuntimeError("DURABLE_EXTRACTION_INPUT_MISMATCH")
        self._last = copy.deepcopy(self._metadata[identity])
        return copy.deepcopy(self._responses[identity])


class SourceOperations:
    def __init__(self, config: WorkbenchConfig, profile: SourceProfile,
                 cloud_profile: CloudProfile | None = None):
        self.config = config
        self.profile = profile
        self.profile.validate()
        if config.mode != "PRIVATE":
            raise SourceOperationError("PRIVATE_SOURCE_MODE_REQUIRED", 503)
        self.store = Store(config)
        self.artifacts = Artifacts(config)
        self.jobs = CloudJobs(config, cloud_profile)
        with self.store.connect() as connection:
            if schema_version(connection) not in ("8", "9", "10", "11"):
                raise SourceOperationError("SOURCE_OPERATIONS_SCHEMA_REQUIRED", 503)

    def _record_upload(self, *, source_id: str | None, outcome: str, filename: str,
                       source_sha256: str | None, size_bytes: int, code: str) -> None:
        with self.store.connect(operator_write=True) as connection:
            connection.execute(
                "INSERT INTO source_upload_events(source_id,outcome,filename_sha256,source_sha256,"
                "size_bytes,detail_code,created_at) VALUES(?,?,?,?,?,?,?)",
                (source_id, outcome, hashlib.sha256(filename.encode("utf-8")).hexdigest(),
                 source_sha256, size_bytes, code, _now()),
            )

    def _validate_pdf(self, path: Path, filename: str, mime_type: str, size: int,
                      digest_value: str) -> dict[str, Any]:
        if mime_type.split(";", 1)[0].strip().lower() != PDF_MIME:
            raise SourceOperationError("UNSUPPORTED_SOURCE_MIME", 415)
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise SourceOperationError("INVALID_PDF_SIGNATURE", 415)
        try:
            reader = PdfReader(path, strict=True)
            if reader.is_encrypted:
                raise SourceOperationError("ENCRYPTED_PDF_UNSUPPORTED", 422)
            pages = len(reader.pages)
            if pages < 1:
                raise SourceOperationError("EMPTY_PDF_UNSUPPORTED", 422)
            text_pages = []
            for page in reader.pages:
                text_pages.append((page.extract_text() or "").strip())
        except SourceOperationError:
            raise
        except Exception:
            raise SourceOperationError("CORRUPT_PDF_UNSUPPORTED", 422) from None
        if not any(text_pages) or any(not value for value in text_pages):
            raise SourceOperationError("OCR_REQUIRED_UNSUPPORTED", 422)
        return {
            "policy": "PRIVATE_CLEAN_PDF_COMPLETE_TEXT_V1", "gate": "PASS",
            "source_type": "pdf", "pages": pages, "text_pages": len(text_pages),
            "source_sha256": digest_value, "size_bytes": size,
            "safe_filename_sha256": hashlib.sha256(filename.encode("utf-8")).hexdigest(),
            "ocr_used": False,
        }

    async def upload(self, stream: AsyncIterable[bytes], *, filename: str,
                     mime_type: str) -> dict[str, Any]:
        safe = _safe_filename(filename)
        root = checked_path(self.config.artifact_root)
        incoming = checked_path(root / ".source-incoming", missing=True)
        incoming.mkdir(parents=True, exist_ok=True)
        temporary = checked_path(incoming / (uuid4().hex + ".upload"), missing=True)
        digest_object = hashlib.sha256()
        size = 0
        try:
            with temporary.open("xb") as output:
                async for chunk in stream:
                    if not isinstance(chunk, bytes):
                        raise SourceOperationError("INVALID_UPLOAD_CHUNK", 422)
                    size += len(chunk)
                    if size > self.profile.max_pdf_bytes:
                        raise SourceOperationError("SOURCE_TOO_LARGE", 413)
                    if chunk:
                        digest_object.update(chunk)
                        output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if size == 0:
                raise SourceOperationError("EMPTY_SOURCE", 422)
            source_sha = digest_object.hexdigest()
            validation = self._validate_pdf(temporary, safe, mime_type, size, source_sha)
            source_id = deterministic_id("SRC", {"source_sha256": source_sha})
            storage_id = deterministic_id("SOURCE_BYTES", {"source_sha256": source_sha})
            # The directory and deterministic Source ID bind the bytes while keeping
            # downstream native checkpoint paths below Windows' legacy path limit.
            relative = f"private-sources/{source_sha[:2]}/{source_id}.pdf"
            destination = checked_path(root / relative, missing=True)
            with self.store.connect() as connection:
                existing = connection.execute(
                    "SELECT * FROM private_sources WHERE source_sha256=?", (source_sha,)
                ).fetchone()
            if existing is not None:
                if sha256_file(self.artifacts.resolve(existing["storage_relative"])) != source_sha:
                    raise SourceOperationError("IMMUTABLE_SOURCE_CORRUPTED")
                self._record_upload(source_id=existing["source_id"], outcome="DUPLICATE",
                                    filename=safe, source_sha256=source_sha,
                                    size_bytes=size, code="EXACT_BYTE_DUPLICATE")
                return {**self._source_projection(existing), "duplicate": True,
                        "duplicate_code": "EXACT_BYTE_DUPLICATE"}
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            except FileExistsError:
                if sha256_file(destination) != source_sha:
                    raise SourceOperationError("IMMUTABLE_SOURCE_CONFLICT")
            else:
                with os.fdopen(descriptor, "wb") as output, temporary.open("rb") as source:
                    shutil.copyfileobj(source, output, UPLOAD_CHUNK_BYTES)
                    output.flush()
                    os.fsync(output.fileno())
            canonical_source_id = None
            try:
                with sqlite3.connect(f"{self.config.knowledge_db.as_uri()}?mode=ro", uri=True) as knowledge:
                    known = knowledge.execute("SELECT source_id FROM sources WHERE lower(sha256)=?",
                                              (source_sha.lower(),)).fetchone()
                    canonical_source_id = known[0] if known else None
            except sqlite3.Error:
                raise SourceOperationError("KNOWLEDGE_PREFLIGHT_UNAVAILABLE", 503) from None
            uploaded = _now()
            with self.store.connect(operator_write=True) as connection:
                connection.execute("BEGIN IMMEDIATE")
                prior = connection.execute(
                    "SELECT source_id FROM private_sources WHERE source_sha256=?", (source_sha,)
                ).fetchone()
                if prior:
                    row = connection.execute("SELECT * FROM private_sources WHERE source_id=?",
                                             (prior["source_id"],)).fetchone()
                else:
                    connection.execute(
                        "INSERT INTO private_sources VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (source_id, source_sha, size, safe, PDF_MIME, storage_id, relative,
                         _canonical(validation), canonical_source_id, uploaded),
                    )
                    row = connection.execute("SELECT * FROM private_sources WHERE source_id=?",
                                             (source_id,)).fetchone()
            duplicate = prior is not None
            self._record_upload(source_id=row["source_id"], outcome="DUPLICATE" if duplicate else "REGISTERED",
                                filename=safe, source_sha256=source_sha, size_bytes=size,
                                code="EXACT_BYTE_DUPLICATE" if duplicate else
                                "KNOWN_CANONICAL_SOURCE" if canonical_source_id else "VALID_CLEAN_PDF")
            return {**self._source_projection(row), "duplicate": duplicate,
                    "duplicate_code": "EXACT_BYTE_DUPLICATE" if duplicate else None}
        except SourceOperationError as error:
            self._record_upload(source_id=None, outcome="REJECTED", filename=safe,
                                source_sha256=digest_object.hexdigest() if size else None,
                                size_bytes=size, code=str(error))
            raise
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _source_projection(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
        value = dict(row)
        return {
            "source_id": value["source_id"], "source_sha256": value["source_sha256"],
            "size_bytes": value["size_bytes"], "safe_filename": value["safe_filename"],
            "mime_type": value["mime_type"], "storage_artifact_id": value["storage_artifact_id"],
            "validation": json.loads(value["validation_json"]),
            "known_canonical_source_id": value["canonical_source_id"],
            "uploaded_at": value["uploaded_at"], "private": True,
        }

    def start(self, source_id: str, *, idempotency_key: str,
              reprocess_reason: str = "",
              company_material_intent: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{15,127}", idempotency_key):
            raise SourceOperationError("INVALID_IDEMPOTENCY_KEY", 422)
        if len(reprocess_reason) > 1000 or reprocess_reason != reprocess_reason.strip():
            raise SourceOperationError("INVALID_REPROCESS_REASON", 422)
        runtime = self.jobs.current_runtime()
        runtime_sha = runtime["runtime_sha256"]
        domains = Domains(self.config)
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            source = connection.execute("SELECT * FROM private_sources WHERE source_id=?",
                                        (source_id,)).fetchone()
            if source is None:
                raise SourceOperationError("SOURCE_NOT_FOUND", 404)
            if source["canonical_source_id"]:
                raise SourceOperationError("SOURCE_ALREADY_EXISTS_IN_PRODUCTION")
            from pro_a.company_material_intent import CompanyMaterialError, read_bound, validate
            try:
                intent = validate(self.config, company_material_intent) if company_material_intent is not None else None
            except CompanyMaterialError as error:
                raise SourceOperationError(str(error), error.status) from None
            basis = (domains.basis(connection, source, runtime, self.profile, self.jobs.profile)
                     if schema_version(connection) in ("9", "10", "11") else None)

            def equivalent(row):
                if row["runtime_sha256"] != runtime_sha:
                    return False
                frozen_intent = read_bound(connection, row["processing_run_id"])
                if (frozen_intent or {}).get("intent_sha256") != (intent or {}).get("intent_sha256"):
                    return False
                frozen = domains.read(row["processing_run_id"], connection=connection)
                return ((frozen is None and basis is None) or
                        (frozen is not None and basis is not None and
                         frozen["resume_sha256"] == canonical_sha256(basis)))

            prior_key = connection.execute(
                "SELECT * FROM source_processing_runs WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if prior_key:
                if (prior_key["source_id"] != source_id
                        or not equivalent(prior_key)
                        or prior_key["reprocess_reason"] != reprocess_reason):
                    raise SourceOperationError("IDEMPOTENCY_CONFLICT")
                return {"run": self._project_run(connection, prior_key["processing_run_id"]),
                        "duplicate": True}
            rows = list(connection.execute(
                "SELECT * FROM source_processing_runs WHERE source_id=? ORDER BY created_at DESC",
                (source_id,),
            ))
            for row in rows:
                frozen_intent = read_bound(connection, row["processing_run_id"])
                if frozen_intent and intent:
                    if frozen_intent["target_company_node_id"] != intent["target_company_node_id"]:
                        raise SourceOperationError("COMPANY_MATERIAL_TARGET_CONFLICT")
                    if frozen_intent["intent_sha256"] != intent["intent_sha256"]:
                        raise SourceOperationError("COMPANY_MATERIAL_INTENT_CONFLICT")
            if any(row["state"] == "RECOVERY_REQUIRED" for row in rows):
                raise SourceOperationError("RECOVERY_REQUIRED_REQUIRES_RECONCILIATION")
            same_runtime = next((row for row in rows if equivalent(row)), None)
            if same_runtime is not None:
                if same_runtime["state"] not in ("FAILED", "BLOCKED") or not reprocess_reason:
                    return {"run": self._project_run(connection, same_runtime["processing_run_id"]),
                            "duplicate": True}
            if rows and same_runtime is None and not reprocess_reason:
                raise SourceOperationError("EXPLICIT_RUNTIME_REPROCESS_REASON_REQUIRED", 422)
            if schema_version(connection) in ("10", "11"):
                from .stage1_scale import require_stage1_intake
                try:
                    require_stage1_intake(connection)
                except BoundaryError as error:
                    raise SourceOperationError(str(error)) from None
            run_id = "SOURCE_RUN_" + uuid4().hex.upper()
            created = _now()
            connection.execute(
                f'''INSERT INTO source_processing_runs(
                    processing_run_id,source_id,idempotency_key,runtime_json,runtime_sha256,
                    state,stage,reprocess_reason,created_at,updated_at{',domain_context_required' if basis else ''})
                    VALUES(?,?,?,?,?,'QUEUED','VALIDATED',?,?,?{',1' if basis else ''})''',
                (run_id, source_id, idempotency_key, _canonical(runtime), runtime_sha,
                 reprocess_reason, created, created),
            )
            if basis is not None:
                domains.bind_run(connection, run_id, basis, self.profile, created, reprocess_reason)
            if intent is not None:
                self._event(connection, run_id, "COMPANY_MATERIAL_INTENT_BOUND", intent)
            self._event(connection, run_id, "PROCESSING_QUEUED",
                        {"runtime_sha256": runtime_sha, "source_id": source_id})
            return {"run": self._project_run(connection, run_id), "duplicate": False}

    def _event(self, connection: sqlite3.Connection, run_id: str, event_type: str,
               payload: Mapping[str, Any] | None = None) -> None:
        previous_row = connection.execute(
            "SELECT sequence,event_sha256 FROM source_processing_events "
            "WHERE processing_run_id=? ORDER BY sequence DESC LIMIT 1", (run_id,),
        ).fetchone()
        sequence = int(previous_row["sequence"] + 1) if previous_row else 1
        previous = previous_row["event_sha256"] if previous_row else "0" * 64
        created = _now()
        body = dict(payload or {})
        event_sha = canonical_sha256({"processing_run_id": run_id, "sequence": sequence,
                                      "event_type": event_type, "event": body,
                                      "previous_sha256": previous, "created_at": created})
        connection.execute(
            "INSERT INTO source_processing_events(processing_run_id,sequence,event_type,event_json,"
            "previous_sha256,event_sha256,created_at) VALUES(?,?,?,?,?,?,?)",
            (run_id, sequence, event_type, _canonical(body), previous, event_sha, created),
        )

    def _transition(self, run_id: str, state: str, stage: str, *, error: str | None = None,
                    retry_safe: bool = False, manual: bool = False, values: Mapping[str, Any] | None = None) -> None:
        assignments = ["state=?", "stage=?", "error_code=?", "retry_safe=?",
                       "manual_recovery_required=?", "updated_at=?"]
        args: list[Any] = [state, stage, error, int(retry_safe), int(manual), _now()]
        for key, value in (values or {}).items():
            if key not in {"native_execution_id", "native_root_relative", "packet_artifact_id", "packet_id"}:
                raise SourceOperationError("INTERNAL_TRANSITION_FIELD_INVALID")
            assignments.append(f"{key}=?")
            args.append(value)
        if state in TERMINAL_PROCESSING_STATES:
            assignments.append("ended_at=?")
            args.append(_now())
        args.append(run_id)
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(f"UPDATE source_processing_runs SET {','.join(assignments)} WHERE processing_run_id=?",
                               args)
            self._event(connection, run_id, "SOURCE_STATE_CHANGED",
                        {"state": state, "stage": stage, "code": error,
                         "retry_safe": retry_safe, "manual_recovery_required": manual})

    def _native_root(self, row: sqlite3.Row | Mapping[str, Any]) -> Path:
        relative = dict(row).get("native_root_relative")
        if not relative:
            raise SourceOperationError("NATIVE_CHECKPOINT_UNAVAILABLE")
        phase4 = load_config(self.profile.phase4_config_path)
        path = checked_path(phase4.root / relative)
        if not path.is_relative_to(phase4.root.resolve()):
            raise SourceOperationError("NATIVE_CHECKPOINT_UNSAFE")
        return path

    def _register_input(self, run: Mapping[str, Any], operation: str, ordinal: int,
                        payload: Mapping[str, Any], checkpoint: Mapping[str, Any]) -> str:
        checkpoint = dict(checkpoint)
        if run.get("company_material_intent"):
            checkpoint["company_material_intent_sha256"] = run["company_material_intent_sha256"]
            checkpoint["company_material_intent"] = run["company_material_intent"]
        reference = Domains(self.config).guard(run["processing_run_id"], self.jobs, self.profile)
        if reference is not None:
            checkpoint["domain_context"] = reference
        body = {
            "document_type": "phase42_stage7_cloud_input", "schema_version": "1",
            "operation_kind": operation, "source_id": run["source_id"],
            "source_sha256": run["source_sha256"],
            "processing_run_id": run["processing_run_id"],
            "native_execution_id": run["native_execution_id"],
            "payload": dict(payload), "payload_sha256": canonical_sha256(payload),
            "checkpoint": dict(checkpoint),
        }
        sha = canonical_sha256(body)
        artifact_id = "ART_" + sha[:32]
        run_storage_id = canonical_sha256(run["processing_run_id"])[:16]
        relative = f"source-runs/{run_storage_id}/cloud-inputs/{ordinal:03d}-{sha[:16]}.json"
        path = checked_path(self.config.artifact_root / relative, missing=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2,
                              allow_nan=False) + "\n").encode("utf-8")
        if path.exists():
            if path.read_bytes() != content:
                raise SourceOperationError("CLOUD_INPUT_ARTIFACT_CONFLICT")
        else:
            temporary = checked_path(path.with_name(path.name + ".tmp"), missing=True)
            with temporary.open("xb") as output:
                output.write(content); output.flush(); os.fsync(output.fileno())
            temporary.replace(path)
        file_sha = hashlib.sha256(content).hexdigest()
        kind = "SOURCE_ANALYSIS_INPUT" if operation == SOURCE_ANALYSIS_OPERATION else "SEMANTIC_INPUT"
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT * FROM source_cloud_inputs WHERE artifact_id=?",
                                          (artifact_id,)).fetchone()
            if existing:
                if existing["sha256"] != file_sha:
                    raise SourceOperationError("CLOUD_INPUT_ARTIFACT_CONFLICT")
                return artifact_id
            connection.execute(
                '''INSERT INTO registered_packets(
                    artifact_id,packet_id,packet_relative,run_relative,packet_sha256,
                    file_inventory,artifact_kind) VALUES(?,?,?,?,?,?,?)''',
                (artifact_id, "CLOUD_INPUT_" + sha.upper(), relative,
                 str(Path(relative).parent).replace("\\", "/"), file_sha,
                 _canonical({relative: file_sha}), kind),
            )
            connection.execute(
                "INSERT INTO source_cloud_inputs VALUES(?,?,?,?,?,?,?,?)",
                (artifact_id, run["processing_run_id"], run["source_id"], operation,
                 ordinal, relative, file_sha, _canonical(checkpoint)),
            )
        return artifact_id

    def _bind_job(self, run_id: str, operation: str, ordinal: int,
                  artifact_id: str) -> dict[str, Any]:
        result = self.jobs.submit(
            idempotency_key=f"stage7:{run_id}:{operation}:{ordinal}",
            input_artifact_id=artifact_id, operation_kind=operation,
        )
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT job_id,cloud_input_artifact_id FROM source_processing_jobs "
                "WHERE processing_run_id=? AND operation_kind=? AND ordinal=?",
                (run_id, operation, ordinal),
            ).fetchone()
            if prior:
                if prior["job_id"] != result["job"]["job_id"] or prior["cloud_input_artifact_id"] != artifact_id:
                    raise SourceOperationError("SOURCE_JOB_BINDING_CONFLICT")
            else:
                connection.execute("INSERT INTO source_processing_jobs VALUES(?,?,?,?,?)",
                                   (run_id, ordinal, operation, artifact_id,
                                    result["job"]["job_id"]))
                self._event(connection, run_id, "DURABLE_JOB_BOUND",
                            {"operation_kind": operation, "ordinal": ordinal,
                             "job_id": result["job"]["job_id"]})
        return result["job"]

    def _jobs_for(self, run_id: str, operation: str) -> list[dict[str, Any]]:
        with self.store.connect() as connection:
            ids = [row[0] for row in connection.execute(
                "SELECT job_id FROM source_processing_jobs WHERE processing_run_id=? "
                "AND operation_kind=? ORDER BY ordinal", (run_id, operation),
            )]
        return [self.jobs.get(job_id) for job_id in ids]

    def _propagate_job_state(self, run_id: str, jobs: list[dict[str, Any]], stage: str) -> bool:
        recovery = next((job for job in jobs if job["status"] == "RECOVERY_REQUIRED"), None)
        if recovery:
            self._transition(run_id, "RECOVERY_REQUIRED", stage,
                             error=recovery["last_error"] or "UNKNOWN_EXTERNAL_OUTCOME",
                             manual=True)
            return True
        blocked = next((job for job in jobs if job["status"].startswith("BLOCKED")), None)
        if blocked:
            self._transition(run_id, "BLOCKED", stage, error=blocked["last_error"] or "JOB_BLOCKED")
            return True
        failed = next((job for job in jobs if job["status"] == "FAILED"), None)
        if failed:
            self._transition(run_id, "FAILED", stage, error=failed["last_error"] or "JOB_FAILED",
                             retry_safe=False)
            return True
        return False

    def _run_pending_jobs(self, jobs: list[dict[str, Any]], provider: Any,
                          worker_id: str) -> list[dict[str, Any]]:
        if provider is not None:
            with self.store.connect() as connection:
                if schema_version(connection) in ("10", "11"):
                    from .stage1_scale import stage1_capacity
                    capacity = stage1_capacity(connection)
                    if (capacity["wip_state"] == "HARD_STOP"
                            or capacity["unprojected_review_packets"]
                            or capacity["intake_paused"]):
                        return jobs
            for job in jobs:
                if job["status"] == "QUEUED":
                    self.jobs.run_once(provider, worker_id=worker_id, job_id=job["job_id"])
        return [self.jobs.get(job["job_id"]) for job in jobs]

    def _extraction_replay(self, jobs: list[dict[str, Any]]) -> _ExtractionReplay:
        responses: dict[str, dict[str, Any]] = {}
        metadata: dict[str, dict[str, Any]] = {}
        for job in jobs:
            envelope = self.jobs.private_result(job["job_id"])
            normalized = envelope.get("normalized_output") or {}
            response = normalized.get("response")
            with self.store.connect() as connection:
                source_input = connection.execute(
                    "SELECT artifact_relative FROM source_cloud_inputs WHERE artifact_id=?",
                    (job["input"]["artifact_id"],),
                ).fetchone()
            document = json.loads(self.artifacts.resolve(source_input[0]).read_text(encoding="utf-8"))
            prompt_sha = document["payload"]["user_prompt_sha256"]
            responses[prompt_sha] = response
            usage = job["usage"]
            metadata[prompt_sha] = {
                "attempts_used": job["attempt_count"],
                "max_attempts": job["budget"]["max_attempts"],
                "execution_mode": "DURABLE_CLOUD_JOB",
                "job_id": job["job_id"],
                "attempts": [{
                    "attempt_number": job["attempt_count"],
                    "requested_model": job["requested_model"],
                    "response_model": job["provider_reported_model"],
                    "prompt_tokens": usage["input_tokens"],
                    "completion_tokens": usage["output_tokens"],
                    "total_tokens": usage["total_tokens"],
                    "cached_tokens": usage["cached_tokens"],
                    "finish_reason": "durable-result",
                }],
            }
        phase4 = load_config(self.profile.phase4_config_path)
        return _ExtractionReplay(phase4.llm, responses, metadata)

    def _semantic_replay(
        self,
        jobs: list[Mapping[str, Any]],
        envelopes: list[Mapping[str, Any]],
        frozen_claims: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Exactly reconstruct ordered semantic results from bounded durable jobs."""
        if len(jobs) != len(envelopes):
            raise SourceOperationError("SEMANTIC_BATCH_ENVELOPE_COUNT_MISMATCH")
        expected_ids = [str(claim.get("claim_id") or "") for claim in frozen_claims]
        if not all(expected_ids) or len(expected_ids) != len(set(expected_ids)):
            raise SourceOperationError("SEMANTIC_PARENT_IDS_MISSING_OR_DUPLICATE")
        expected_evidence = {
            str(claim["claim_id"]): [
                str(unit.get("evidence_unit_id") or "")
                for unit in claim.get("evidence_units") or []
            ]
            for claim in frozen_claims
        }
        result_by_id: dict[str, dict[str, Any]] = {}
        reconstructed_inputs: list[dict[str, Any]] = []
        call_records: list[dict[str, Any]] = []
        for batch_index, (job, envelope) in enumerate(zip(jobs, envelopes, strict=True), 1):
            with self.store.connect() as connection:
                source_input = connection.execute(
                    "SELECT artifact_relative FROM source_cloud_inputs WHERE artifact_id=?",
                    (job["input"]["artifact_id"],),
                ).fetchone()
            if source_input is None:
                raise SourceOperationError("SEMANTIC_BATCH_INPUT_MISSING")
            document = json.loads(
                self.artifacts.resolve(source_input[0]).read_text(encoding="utf-8")
            )
            batch_claims = list((document.get("payload") or {}).get("claims") or [])
            if not 1 <= len(batch_claims) <= SEMANTIC_MAX_PARENTS_PER_BATCH:
                raise SourceOperationError("SEMANTIC_BATCH_PARENT_CAP_VIOLATION")
            batch_ids = [str(claim.get("claim_id") or "") for claim in batch_claims]
            normalized = envelope.get("normalized_output") or {}
            results = copy.deepcopy(normalized.get("results") or [])
            result_ids = [str(row.get("parent_claim_id") or "") for row in results]
            if result_ids != batch_ids or len(result_ids) != len(set(result_ids)):
                raise SourceOperationError("SEMANTIC_BATCH_RESULT_ID_MISMATCH")
            for row in results:
                parent_id = str(row["parent_claim_id"])
                if parent_id in result_by_id:
                    raise SourceOperationError("SEMANTIC_DUPLICATE_PARENT_RESULT")
                evidence_ids = [
                    str(unit.get("evidence_unit_id") or "")
                    for unit in row.get("evidence_units") or []
                ]
                if evidence_ids != expected_evidence.get(parent_id):
                    raise SourceOperationError("SEMANTIC_EVIDENCE_IDENTITY_CHANGED")
                result_by_id[parent_id] = row
            reconstructed_inputs.extend(copy.deepcopy(batch_claims))
            call_records.append({
                "call_index": batch_index,
                "batch_parent_claim_ids": batch_ids,
                "batch_claim_count": len(batch_ids),
                "status": "SUCCESS",
                "metadata": {
                    "execution_mode": "DURABLE_CLOUD_JOB",
                    "job_id": job["job_id"],
                    "attempt_count": job["attempt_count"],
                    "usage": copy.deepcopy(job["usage"]),
                },
            })
        if _canonical(reconstructed_inputs) != _canonical(list(frozen_claims)):
            raise SourceOperationError("SEMANTIC_BATCH_RECONSTRUCTION_MISMATCH")
        if set(result_by_id) != set(expected_ids):
            raise SourceOperationError("SEMANTIC_PARENT_COVERAGE_MISMATCH")
        results = [result_by_id[parent_id] for parent_id in expected_ids]
        usage_known = all(job["usage"]["status"] == "KNOWN" for job in jobs)
        usage = {
            key: (sum(int(job["usage"][key] or 0) for job in jobs) if usage_known else 0)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
        return {
            "document_type": "phase3e2se1_post_extraction_semantic_decomposition",
            "schema_version": "2.1", "proposition_ir_version": "2.1",
            "architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
            "evidence_binding_architecture": "DETERMINISTIC_EVIDENCE_IDS",
            "invariants": {"MODEL_GENERATED_RAW_EVIDENCE_OFFSETS": False,
                           "PARENT_EVIDENCE_IDENTITY_DETERMINISTIC": True,
                           "PROPOSITION_SUPPORT_REFERENCES_EXISTING_EVIDENCE_IDS": True},
            "backend": ("DURABLE_CLOUD_JOB" if jobs
                        else "NO_SEMANTIC_CALL_EMPTY_PARENT_SET"),
            "batch_size": SEMANTIC_MAX_PARENTS_PER_BATCH,
            "batch_parent_cap": SEMANTIC_MAX_PARENTS_PER_BATCH,
            "batch_count": len(jobs),
            "input_parent_claim_ids": expected_ids,
            "output_parent_claim_ids": expected_ids,
            "parent_claims_before": len(expected_ids),
            "parent_claims_after": len(expected_ids),
            "parent_claim_id_match": len(expected_ids), "new_parent_claims": 0,
            "missing_parent_claims": 0, "unexpected_model_parent_ids": [],
            "primary_extraction_llm_calls": 0,
            "semantic_length_retry_changes_claims": False,
            "semantic_length_retry_changes_evidence_units": False,
            "semantic_llm_calls": sum(int(job["attempt_count"]) for job in jobs),
            "semantic_length_retries": 0,
            "usage_status": "KNOWN" if usage_known else "UNKNOWN",
            "usage": {"prompt_tokens": usage["input_tokens"],
                      "completion_tokens": usage["output_tokens"],
                      "total_tokens": usage["total_tokens"]},
            "counts": {"valid_proposition_ir_claims": len(results),
                       "ambiguous_or_invalid_ir_claims": 0,
                       "proposition_evidence_binding_failures": 0,
                       "unsupported_proposition_content": 0},
            "call_records": call_records, "results": results,
        }

    def _copy_and_register_packet(self, run: Mapping[str, Any], native_root: Path) -> dict[str, Any]:
        run_storage_id = canonical_sha256(run["processing_run_id"])[:16]
        destination_relative = f"source-runs/{run_storage_id}/native"
        destination = checked_path(self.config.artifact_root / destination_relative, missing=True)
        if destination.exists():
            raise SourceOperationError("NATIVE_PACKET_DESTINATION_EXISTS")
        shutil.copytree(native_root, destination)
        packet_relative = f"{destination_relative}/review/packet.json"
        run_relative = f"{destination_relative}/engine"
        registered = self.artifacts.register(packet_relative, run_relative)
        Domains(self.config).bind_packet(run["processing_run_id"], registered["artifact_id"])
        return registered

    def advance_once(self, *, worker_id: str, provider: Any = None,
                     processing_run_id: str | None = None,
                     lease_seconds: int = 180) -> dict[str, Any] | None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", worker_id):
            raise SourceOperationError("INVALID_WORKER_ID", 422)
        if not 0 <= lease_seconds <= 3660:
            raise SourceOperationError("INVALID_LEASE_SECONDS", 422)
        now = datetime.now(timezone.utc)
        expiry = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self.store.connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            where = "processing_run_id=? AND " if processing_run_id else ""
            args = (processing_run_id, now.isoformat()) if processing_run_id else (now.isoformat(),)
            row = connection.execute(
                f"SELECT * FROM source_processing_runs WHERE {where}state NOT IN "
                "('HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED','RECOVERY_REQUIRED') "
                "AND (lease_owner IS NULL OR lease_expires_at<=?) ORDER BY created_at LIMIT 1", args,
            ).fetchone()
            if row is None:
                return None
            fence = row["fence"] + 1
            connection.execute(
                "UPDATE source_processing_runs SET lease_owner=?,lease_expires_at=?,fence=? "
                "WHERE processing_run_id=?", (worker_id, expiry, fence, row["processing_run_id"]),
            )
            run_id = row["processing_run_id"]
        try:
            return self._advance_claimed(run_id, provider, worker_id)
        except SourceOperationError as error:
            detail = str(error)
            code = (detail if re.fullmatch(r"[A-Z][A-Z0-9_]*(?::[A-Z][A-Z0-9_]*)?", detail)
                    else "SOURCE_ORCHESTRATION_BLOCKED")
            self._transition(run_id, "BLOCKED", "ORCHESTRATION", error=code)
            return self.get_run(run_id)
        except Exception as error:
            detail = str(error)
            code = (detail if re.fullmatch(r"[A-Z][A-Z0-9_]*(?::[A-Z][A-Z0-9_]*)?", detail)
                    else f"{type(error).__name__.upper()}_ORCHESTRATION_FAILED")
            self._transition(run_id, "FAILED", "ORCHESTRATION", error=code)
            return self.get_run(run_id)
        finally:
            with self.store.connect(operator_write=True) as connection:
                connection.execute(
                    "UPDATE source_processing_runs SET lease_owner=NULL,lease_expires_at=NULL "
                    "WHERE processing_run_id=? AND lease_owner=?", (run_id, worker_id),
                )

    def _advance_claimed(self, run_id: str, provider: Any, worker_id: str) -> dict[str, Any]:
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM source_processing_runs WHERE processing_run_id=?",
                                     (run_id,)).fetchone()
            source = connection.execute("SELECT * FROM private_sources WHERE source_id=?",
                                        (row["source_id"],)).fetchone()
            from pro_a.company_material_intent import read_bound
            intent = read_bound(connection, run_id)
            for input_row in connection.execute(
                "SELECT checkpoint_json FROM source_cloud_inputs WHERE processing_run_id=?", (run_id,),
            ):
                checkpoint = json.loads(input_row[0])
                if (checkpoint.get("company_material_intent_sha256") != (intent or {}).get("intent_sha256")
                        or checkpoint.get("company_material_intent") != intent):
                    raise SourceOperationError("COMPANY_MATERIAL_INTENT_DRIFT")
        try:
            Domains(self.config).guard(run_id, self.jobs, self.profile)
        except BoundaryError as error:
            raise SourceOperationError(str(error)) from None
        if row["runtime_sha256"] != self.jobs.current_runtime()["runtime_sha256"]:
            self._transition(run_id, "BLOCKED", "RUNTIME_PREFLIGHT", error="RUNTIME_DRIFT")
            return self.get_run(run_id)
        if row["state"] == "QUEUED":
            self._transition(run_id, "PARSING", "NATIVE_SOURCE_REGISTRATION")
            stored_source = self.artifacts.resolve(source["storage_relative"])
            if (stored_source.stat().st_size != source["size_bytes"]
                    or sha256_file(stored_source) != source["source_sha256"]):
                raise SourceOperationError("IMMUTABLE_SOURCE_CORRUPTED")
            result = start_execution(
                stored_source,
                config_path=self.profile.phase4_config_path,
                retry_policy=RetryPolicy.FORBID_ALL,
                stop_after="SOURCE_READY", external_semantic=True,
            )
            if result["state"] != "SOURCE_READY":
                raise SourceOperationError(result.get("code") or "NATIVE_SOURCE_REGISTRATION_FAILED")
            phase4 = load_config(self.profile.phase4_config_path)
            native_root = Path(result["execution_root"])
            relative = native_root.relative_to(phase4.root.resolve()).as_posix()
            self._transition(run_id, "EXTRACTION_PROCESSING", "EXTRACTION_JOBS",
                             values={"native_execution_id": result["execution_id"],
                                     "native_root_relative": relative})
            plan = plan_external_source_analysis(native_root / "engine",
                                                 config_path=self.profile.phase4_config_path)
            if not plan["pieces"]:
                raise SourceOperationError("BLOCKED_EMPTY_EXTRACTION_PLAN")
            if len(plan["pieces"]) > self.profile.max_extraction_pieces:
                raise SourceOperationError("EXTRACTION_PIECE_BUDGET_EXCEEDED")
            current = self.get_run(run_id)
            checkpoint = {"native_state": "SOURCE_READY", "execution_id": result["execution_id"],
                          "run_id": plan["run_id"], "plan_sha256": plan["plan"]["initial_extraction_plan_sha256"],
                          "resume_semantics": "REFERENCE_EXISTING_NATIVE_CHECKPOINT_ONLY"}
            for ordinal, piece in enumerate(plan["pieces"], 1):
                artifact = self._register_input(current, SOURCE_ANALYSIS_OPERATION, ordinal,
                                                piece, checkpoint)
                self._bind_job(run_id, SOURCE_ANALYSIS_OPERATION, ordinal, artifact)
            return self.get_run(run_id)

        if row["state"] == "EXTRACTION_PROCESSING":
            jobs = self._run_pending_jobs(self._jobs_for(run_id, SOURCE_ANALYSIS_OPERATION),
                                          provider, worker_id)
            if self._propagate_job_state(run_id, jobs, "EXTRACTION_JOBS"):
                return self.get_run(run_id)
            if not jobs or any(job["status"] != "SUCCEEDED" for job in jobs):
                return self.get_run(run_id)
            replay = self._extraction_replay(jobs)
            native_root = self._native_root(row)
            result = resume_execution(
                native_root, execution_id=row["native_execution_id"],
                config_path=self.profile.phase4_config_path,
                retry_policy=RetryPolicy.FORBID_ALL,
                stop_after="SEMANTIC_INPUT_READY",
                extraction_llm_factory=lambda _cfg: replay,
            )
            if result["state"] != "SEMANTIC_INPUT_READY":
                raise SourceOperationError(result.get("code") or "NATIVE_EXTRACTION_FAILED")
            document = json.loads((native_root / "engine/evidence/stage6_semantic_input.json").read_text(encoding="utf-8"))
            checkpoint = {"native_state": "SEMANTIC_INPUT_READY",
                          "execution_id": row["native_execution_id"],
                          "run_id": document["run_id"], "payload_sha256": document["payload_sha256"],
                          "resume_semantics": "REFERENCE_EXISTING_NATIVE_CHECKPOINT_ONLY"}
            claims = list(document["payload"].get("claims") or [])
            input_token_budget = (
                self.jobs.profile.max_total_tokens - self.jobs.profile.max_output_tokens
            )
            try:
                batches = partition_semantic_claims(
                    claims,
                    max_parents=SEMANTIC_MAX_PARENTS_PER_BATCH,
                    max_input_tokens=input_token_budget,
                )
            except (SemanticDecompositionError, ValueError) as error:
                raise SourceOperationError(str(error)) from None
            extraction_jobs = self._jobs_for(run_id, SOURCE_ANALYSIS_OPERATION)
            if len(extraction_jobs) + len(batches) > MAX_STAGE1_JOBS_PER_RUN:
                raise SourceOperationError("SOURCE_JOB_BUDGET_EXCEEDED")
            current = self.get_run(run_id)
            partition_identity = canonical_sha256({
                "payload_sha256": document["payload_sha256"],
                "parent_cap": SEMANTIC_MAX_PARENTS_PER_BATCH,
                "input_token_budget": input_token_budget,
                "batches": [[claim["claim_id"] for claim in batch] for batch in batches],
            })
            for ordinal, batch in enumerate(batches, 1):
                batch_checkpoint = {
                    **checkpoint,
                    "semantic_partition": {
                        "partition_sha256": partition_identity,
                        "batch_index": ordinal,
                        "batch_count": len(batches),
                        "parent_claim_ids": [claim["claim_id"] for claim in batch],
                        "parent_cap": SEMANTIC_MAX_PARENTS_PER_BATCH,
                        "input_token_budget": input_token_budget,
                    },
                }
                artifact = self._register_input(
                    current, SEMANTIC_OPERATION, ordinal,
                    {"claims": batch}, batch_checkpoint,
                )
                self._bind_job(run_id, SEMANTIC_OPERATION, ordinal, artifact)
            self._transition(run_id, "SEMANTIC_PROCESSING", "SEMANTIC_JOB")
            return self.get_run(run_id)

        if row["state"] == "SEMANTIC_PROCESSING":
            jobs = self._run_pending_jobs(self._jobs_for(run_id, SEMANTIC_OPERATION),
                                          provider, worker_id)
            if self._propagate_job_state(run_id, jobs, "SEMANTIC_JOB"):
                return self.get_run(run_id)
            if any(job["status"] != "SUCCEEDED" for job in jobs):
                return self.get_run(run_id)
            native_root = self._native_root(row)
            semantic_document = json.loads(
                (native_root / "engine/evidence/stage6_semantic_input.json").read_text(
                    encoding="utf-8"
                )
            )
            envelopes = [self.jobs.private_result(job["job_id"]) for job in jobs]
            replay_result = self._semantic_replay(
                jobs, envelopes, list(semantic_document["payload"].get("claims") or [])
            )
            metadata = None
            if jobs:
                known = all(job["usage"]["status"] == "KNOWN" for job in jobs)
                metadata = {
                    "provider": jobs[0]["provider"],
                    "requested_model": jobs[0]["requested_model"],
                    "provider_reported_model": jobs[0]["provider_reported_model"],
                    "provider_reported_models": [job["provider_reported_model"] for job in jobs],
                    "job_id": jobs[0]["job_id"],
                    "job_ids": [job["job_id"] for job in jobs],
                    "attempt_count": sum(job["attempt_count"] for job in jobs),
                    "provider_calls": sum(job["attempt_count"] for job in jobs),
                    "usage": {
                        "status": "KNOWN" if known else "UNKNOWN",
                        "input_tokens": (sum(job["usage"]["input_tokens"] for job in jobs)
                                         if known else None),
                        "output_tokens": (sum(job["usage"]["output_tokens"] for job in jobs)
                                          if known else None),
                        "total_tokens": (sum(job["usage"]["total_tokens"] for job in jobs)
                                         if known else None),
                    },
                }
            result = resume_execution(
                native_root, execution_id=row["native_execution_id"],
                config_path=self.profile.phase4_config_path,
                retry_policy=RetryPolicy.FORBID_ALL,
                stop_after="REVIEW_READY", semantic_replay=lambda _inputs: copy.deepcopy(replay_result),
                semantic_execution_metadata=metadata,
            )
            if result["state"] != "STOPPED" or result.get("code") != "HUMAN_REVIEW_REQUIRED":
                raise SourceOperationError(result.get("code") or "NATIVE_PACKET_FAILED")
            self._transition(run_id, "PACKET_PREPARATION", "NATIVE_PACKET")
            registered = self._copy_and_register_packet(self.get_run(run_id), native_root)
            self._transition(run_id, "HUMAN_REVIEW_REQUIRED", "HUMAN_REVIEW",
                             values={"packet_artifact_id": registered["artifact_id"],
                                     "packet_id": registered["packet_id"]})
            return self.get_run(run_id)
        return self.get_run(run_id)

    @staticmethod
    def _project_run(connection: sqlite3.Connection, run_id: str) -> dict[str, Any]:
        row = connection.execute("SELECT * FROM source_processing_runs WHERE processing_run_id=?",
                                 (run_id,)).fetchone()
        if row is None:
            raise SourceOperationError("PROCESSING_RUN_NOT_FOUND", 404)
        source = connection.execute("SELECT * FROM private_sources WHERE source_id=?",
                                    (row["source_id"],)).fetchone()
        jobs = [dict(item) for item in connection.execute(
            "SELECT operation_kind,ordinal,job_id,cloud_input_artifact_id FROM source_processing_jobs "
            "WHERE processing_run_id=? ORDER BY operation_kind,ordinal", (run_id,),
        )]
        from pro_a.company_material_intent import read_bound
        intent = read_bound(connection, run_id)
        return {
            "processing_run_id": row["processing_run_id"], "source_id": row["source_id"],
            "company_material_intent": intent,
            "company_material_intent_sha256": intent["intent_sha256"] if intent else None,
            "source_sha256": source["source_sha256"], "state": row["state"],
            "stage": row["stage"], "runtime_identity": json.loads(row["runtime_json"]),
            "native_execution_id": row["native_execution_id"],
            "native_checkpoint": {"available": bool(row["native_execution_id"]),
                                  "completed_stage": row["stage"]},
            "packet_artifact_id": row["packet_artifact_id"], "packet_id": row["packet_id"],
            "error": ({"code": row["error_code"], "stage": row["stage"],
                       "retry_safe": bool(row["retry_safe"]),
                       "manual_recovery_required": bool(row["manual_recovery_required"]),
                       "operator_action": ("Manual job reconciliation is required."
                                           if row["manual_recovery_required"] else
                                           "Inspect the registered artifacts and start an explicit reprocess if allowed.")}
                      if row["error_code"] else None),
            "jobs": jobs, "created_at": row["created_at"], "updated_at": row["updated_at"],
            "ended_at": row["ended_at"],
        }

    def _post_processing(self, result: dict[str, Any]) -> dict[str, Any]:
        result["review"] = None
        result["attribution"] = None
        result["qualification"] = None
        result["activation_receipt"] = None
        artifact_id = result.get("packet_artifact_id")
        if not artifact_id:
            return result
        review = ReviewWorkbench(self.config).read(artifact_id)
        progress = review["review"]["progress"]
        result["review"] = {"review_id": review["review"]["review_id"],
                            "status": review["review"]["status"],
                            "required": progress["required"],
                            "completed": progress["completed"],
                            "deep_link": f"/?surface=review&artifact={artifact_id}"}
        if review["review"]["status"] != "SEALED":
            return result
        result["state"] = "REVIEW_COMPLETE"
        try:
            from .attribution import Attribution
            attribution = Attribution(self.config).read(artifact_id)
        except BoundaryError as error:
            result["state"] = "RECOVERY_REQUIRED"
            result["error"] = {
                "code": str(error), "stage": "ATTRIBUTION",
                "retry_safe": False, "manual_recovery_required": True,
                "operator_action": "Manual attribution-state reconciliation is required.",
            }
            return result
        result["attribution"] = {"status": attribution["status"],
                                 "sidecar_id": ((attribution.get("sidecar") or {}).get("object_id")),
                                 "required": attribution["required"],
                                 "completed": attribution["completed"]}
        if attribution["status"] != "SEALED":
            result["state"] = "ATTRIBUTION_REQUIRED"
            return result
        result["state"] = "ATTRIBUTION_COMPLETE"
        result["qualification"] = attribution.get("qualification")
        result["activation_receipt"] = attribution.get("receipt")
        if result["qualification"]:
            result["state"] = "QUALIFIED"
        if result["activation_receipt"]:
            result["state"] = "ACTIVATED"
        return result

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.store.connect() as connection:
            result = self._project_run(connection, run_id)
        context = Domains(self.config).read(run_id)
        result["domain_context"] = context
        result["domain_context_status"] = "FROZEN" if context else "LEGACY_NO_DOMAIN_CONTEXT"
        detailed_jobs = [self.jobs.get(item["job_id"]) for item in result.pop("jobs")]
        result["jobs"] = detailed_jobs
        usage_status = ("KNOWN" if detailed_jobs and
                        all(job["usage"]["status"] == "KNOWN" for job in detailed_jobs)
                        else "UNKNOWN")
        result["usage"] = {
            "status": usage_status,
            "input_tokens": (sum(job["usage"]["input_tokens"] for job in detailed_jobs)
                             if usage_status == "KNOWN" else None),
            "output_tokens": (sum(job["usage"]["output_tokens"] for job in detailed_jobs)
                              if usage_status == "KNOWN" else None),
            "total_tokens": (sum(job["usage"]["total_tokens"] for job in detailed_jobs)
                             if usage_status == "KNOWN" else None),
            "attempts": sum(job["attempt_count"] for job in detailed_jobs),
        }
        result["lineage"] = [
            {"kind": "SOURCE", "id": result["source_id"]},
            *([{"kind": "COMPANY_MATERIAL_INTENT", "id": result["company_material_intent_sha256"]}]
              if result["company_material_intent_sha256"] else []),
            {"kind": "PROCESSING_RUN", "id": result["processing_run_id"]},
            *({"kind": "CLOUD_JOB", "id": job["job_id"],
               "operation_kind": job["operation_kind"]} for job in detailed_jobs),
        ]
        if result.get("packet_artifact_id"):
            result["lineage"].append({"kind": "REVIEW_PACKET",
                                      "id": result["packet_artifact_id"],
                                      "packet_id": result["packet_id"]})
        return self._post_processing(result)

    @staticmethod
    def _run_overview(row: sqlite3.Row, source_sha256: str, effective_state: str,
                      usage: Mapping[str, Any] | None,
                      intent: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Bounded list projection; full job/review context stays on the detail endpoint."""
        usage = dict(usage or {})
        known = usage.get("usage_status") == "KNOWN"
        result = {
            "processing_run_id": row["processing_run_id"], "source_id": row["source_id"],
            "company_material_intent": intent,
            "company_material_intent_sha256": intent["intent_sha256"] if intent else None,
            "source_sha256": source_sha256, "state": effective_state,
            "stage": row["stage"], "runtime_identity": json.loads(row["runtime_json"]),
            "native_execution_id": row["native_execution_id"],
            "native_checkpoint": {"available": bool(row["native_execution_id"]),
                                  "completed_stage": row["stage"]},
            "packet_artifact_id": row["packet_artifact_id"], "packet_id": row["packet_id"],
            "error": ({"code": row["error_code"], "stage": row["stage"],
                       "retry_safe": bool(row["retry_safe"]),
                       "manual_recovery_required": bool(row["manual_recovery_required"]),
                       "operator_action": ("Manual job reconciliation is required."
                                           if row["manual_recovery_required"] else
                                           "Inspect the registered artifacts and start an explicit reprocess if allowed.")}
                      if row["error_code"] else None),
            "jobs": [],
            "usage": {
                "status": "KNOWN" if known else "UNKNOWN",
                "input_tokens": usage.get("input_tokens") if known else None,
                "output_tokens": usage.get("output_tokens") if known else None,
                "total_tokens": usage.get("total_tokens") if known else None,
                "attempts": int(usage.get("attempts") or 0),
            },
            "review": None, "attribution": None, "qualification": None,
            "activation_receipt": None,
            "lineage": [
                {"kind": "SOURCE", "id": row["source_id"]},
                *([{"kind": "COMPANY_MATERIAL_INTENT", "id": intent["intent_sha256"]}]
                  if intent else []),
                {"kind": "PROCESSING_RUN", "id": row["processing_run_id"]},
            ],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "ended_at": row["ended_at"], "overview_only": True,
        }
        if row["packet_artifact_id"]:
            result["lineage"].append({"kind": "REVIEW_PACKET",
                                      "id": row["packet_artifact_id"],
                                      "packet_id": row["packet_id"]})
        return result

    def source(self, source_id: str) -> dict[str, Any]:
        with self.store.connect() as connection:
            source = connection.execute("SELECT * FROM private_sources WHERE source_id=?",
                                        (source_id,)).fetchone()
            if source is None:
                raise SourceOperationError("SOURCE_NOT_FOUND", 404)
            ids = [row[0] for row in connection.execute(
                "SELECT processing_run_id FROM source_processing_runs WHERE source_id=? "
                "ORDER BY created_at DESC,processing_run_id DESC LIMIT 25", (source_id,),
            )]
            run_total = int(connection.execute(
                "SELECT COUNT(*) FROM source_processing_runs WHERE source_id=?", (source_id,)
            ).fetchone()[0])
            value = self._source_projection(source)
        value["processing_runs"] = [self.get_run(run_id) for run_id in ids]
        value["latest_run"] = value["processing_runs"][0] if ids else None
        value["company_material_intent"] = (value["latest_run"] or {}).get("company_material_intent")
        value["run_history"] = {
            "total": run_total, "limit": 25,
            "next_cursor": "25" if run_total > 25 else None,
        }
        return value

    def run_history(self, source_id: str, *, cursor: str | None = None,
                    limit: int = 25) -> dict[str, Any]:
        if not 1 <= limit <= 100 or (cursor not in (None, "") and not str(cursor).isdigit()):
            raise SourceOperationError("INVALID_CURSOR", 422)
        offset = int(cursor or 0)
        with self.store.connect() as connection:
            if connection.execute(
                "SELECT 1 FROM private_sources WHERE source_id=?", (source_id,)
            ).fetchone() is None:
                raise SourceOperationError("SOURCE_NOT_FOUND", 404)
            total = int(connection.execute(
                "SELECT COUNT(*) FROM source_processing_runs WHERE source_id=?", (source_id,)
            ).fetchone()[0])
            ids = [row[0] for row in connection.execute(
                """SELECT processing_run_id FROM source_processing_runs
                   WHERE source_id=? ORDER BY created_at DESC,processing_run_id DESC
                   LIMIT ? OFFSET ?""", (source_id, limit, offset),
            )]
        return {
            "items": [self.get_run(run_id) for run_id in ids],
            "total": total, "limit": limit, "offset": offset,
            "next_cursor": str(offset + limit) if offset + limit < total else None,
        }

    def list(self, *, status: str = "", cursor: str | None = None,
             limit: int = 25) -> dict[str, Any]:
        if not 1 <= limit <= 100 or (cursor not in (None, "") and not str(cursor).isdigit()):
            raise SourceOperationError("INVALID_CURSOR", 422)
        allowed = set(SOURCE_STATES) | {"REVIEW_COMPLETE", "ATTRIBUTION_REQUIRED",
                                        "ATTRIBUTION_COMPLETE", "QUALIFIED", "ACTIVATED"}
        if status and status not in allowed:
            raise SourceOperationError("INVALID_SOURCE_FILTER", 422)
        offset = int(cursor or 0)
        latest = ("LEFT JOIN source_processing_runs r ON r.processing_run_id=(SELECT r2.processing_run_id "
                  "FROM source_processing_runs r2 WHERE r2.source_id=s.source_id "
                  "ORDER BY r2.created_at DESC,r2.processing_run_id DESC LIMIT 1) ")
        joins = (latest + "LEFT JOIN review_drafts d ON d.artifact_id=r.packet_artifact_id "
                 "LEFT JOIN attribution_objects a ON a.artifact_id=r.packet_artifact_id "
                 "LEFT JOIN operational_packages p ON p.artifact_id=r.packet_artifact_id "
                 "LEFT JOIN operational_receipts x ON x.artifact_id=r.packet_artifact_id ")
        if status == "REGISTERED":
            where = "WHERE r.processing_run_id IS NULL"
        elif status in set(SOURCE_STATES) - {"REGISTERED", "HUMAN_REVIEW_REQUIRED"}:
            where = "WHERE r.state=?"
        elif status == "HUMAN_REVIEW_REQUIRED":
            where = "WHERE r.state='HUMAN_REVIEW_REQUIRED' AND COALESCE(d.status,'DRAFT')!='SEALED'"
        elif status in {"REVIEW_COMPLETE", "ATTRIBUTION_REQUIRED"}:
            where = "WHERE d.status='SEALED' AND a.artifact_id IS NULL"
        elif status == "ATTRIBUTION_COMPLETE":
            where = "WHERE a.artifact_id IS NOT NULL AND p.artifact_id IS NULL"
        elif status == "QUALIFIED":
            where = "WHERE p.artifact_id IS NOT NULL AND x.artifact_id IS NULL"
        elif status == "ACTIVATED":
            where = "WHERE x.artifact_id IS NOT NULL"
        else:
            where = ""
        args: tuple[Any, ...] = ((status,) if "r.state=?" in where else ())
        with self.store.connect() as connection:
            sources = list(connection.execute(
                f"SELECT s.*,r.processing_run_id AS latest_processing_run_id,"
                "CASE WHEN x.artifact_id IS NOT NULL THEN 'ACTIVATED' "
                "WHEN p.artifact_id IS NOT NULL THEN 'QUALIFIED' "
                "WHEN a.artifact_id IS NOT NULL THEN 'ATTRIBUTION_COMPLETE' "
                "WHEN d.status='SEALED' THEN 'ATTRIBUTION_REQUIRED' "
                "ELSE r.state END AS latest_effective_state "
                f"FROM private_sources s {joins} {where} "
                "ORDER BY s.uploaded_at DESC,s.source_id LIMIT ? OFFSET ?",
                (*args, limit, offset),
            ))
            total = connection.execute(
                f"SELECT COUNT(*) FROM private_sources s {joins} {where}", args).fetchone()[0]
            latest_ids = [row["latest_processing_run_id"] for row in sources
                          if row["latest_processing_run_id"]]
            run_by_id: dict[str, sqlite3.Row] = {}
            usage_by_id: dict[str, dict[str, Any]] = {}
            intent_by_id: dict[str, dict[str, Any] | None] = {}
            if latest_ids:
                placeholders = ",".join("?" for _ in latest_ids)
                run_by_id = {row["processing_run_id"]: row for row in connection.execute(
                    f"SELECT * FROM source_processing_runs WHERE processing_run_id IN ({placeholders})",
                    latest_ids,
                )}
                from pro_a.company_material_intent import read_bound
                intent_by_id = {run_id: read_bound(connection, run_id) for run_id in latest_ids}
                usage_by_id = {row["processing_run_id"]: dict(row) for row in connection.execute(
                    f'''SELECT spj.processing_run_id,COUNT(*) AS job_count,
                        COALESCE(SUM(j.attempt_count),0) AS attempts,
                        CASE WHEN SUM(CASE WHEN j.usage_status='KNOWN' THEN 1 ELSE 0 END)=COUNT(*)
                             THEN 'KNOWN' ELSE 'UNKNOWN' END AS usage_status,
                        SUM(j.input_tokens) AS input_tokens,SUM(j.output_tokens) AS output_tokens,
                        SUM(j.total_tokens) AS total_tokens
                        FROM source_processing_jobs spj JOIN cloud_jobs j ON j.job_id=spj.job_id
                        WHERE spj.processing_run_id IN ({placeholders})
                        GROUP BY spj.processing_run_id''', latest_ids,
                )}
        items = []
        for source in sources:
            value = self._source_projection(source)
            latest_id = source["latest_processing_run_id"]
            overview = (self._run_overview(
                run_by_id[latest_id], value["source_sha256"],
                source["latest_effective_state"], usage_by_id.get(latest_id),
                intent_by_id.get(latest_id),
            ) if latest_id else None)
            value["processing_runs"] = [overview] if overview else []
            value["latest_run"] = value["processing_runs"][0] if value["processing_runs"] else None
            value["company_material_intent"] = (overview or {}).get("company_material_intent")
            items.append(value)
        return {
            "items": items, "total": total, "limit": limit, "offset": offset,
            "next_cursor": str(offset + limit) if offset + limit < total else None,
            "capabilities": {
                "source_class": "PRIVATE_CLEAN_PDF",
                "mime_types": [PDF_MIME],
                "max_pdf_bytes": self.profile.max_pdf_bytes,
                "single_file": True,
                "ocr_supported": False,
            },
        }

    def events(self, run_id: str, *, cursor: str | None = None,
               limit: int = 50) -> dict[str, Any]:
        if not 1 <= limit <= 100 or (cursor not in (None, "") and not str(cursor).isdigit()):
            raise SourceOperationError("INVALID_CURSOR", 422)
        offset = int(cursor or 0)
        with self.store.connect() as connection:
            self._project_run(connection, run_id)
            rows = [dict(row) for row in connection.execute(
                "SELECT sequence,event_type,event_json,previous_sha256,event_sha256,created_at "
                "FROM source_processing_events WHERE processing_run_id=? ORDER BY sequence "
                "LIMIT ? OFFSET ?", (run_id, limit, offset),
            )]
            total = connection.execute(
                "SELECT COUNT(*) FROM source_processing_events WHERE processing_run_id=?", (run_id,)
            ).fetchone()[0]
        for row in rows:
            row["event"] = json.loads(row.pop("event_json"))
        return {"items": rows, "total": total, "limit": limit, "offset": offset,
                "next_cursor": str(offset + limit) if offset + limit < total else None}

    def metrics(self) -> dict[str, Any]:
        with self.store.connect() as connection:
            uploads = dict(connection.execute(
                "SELECT outcome,COUNT(*) FROM source_upload_events GROUP BY outcome"))
            states = dict(connection.execute(
                "SELECT state,COUNT(*) FROM source_processing_runs GROUP BY state"))
            usage = connection.execute(
                "SELECT COUNT(*),COALESCE(SUM(attempt_count),0),COALESCE(SUM(total_tokens),0) "
                "FROM cloud_jobs").fetchone()
            from .stage1_scale import stage1_capacity
            capacity = stage1_capacity(connection)
        return {"uploads": uploads, "processing": states, "cloud_jobs": usage[0],
                "provider_attempts": usage[1], "known_total_tokens": usage[2],
                "recovery_required": states.get("RECOVERY_REQUIRED", 0),
                "human_review_backlog": states.get("HUMAN_REVIEW_REQUIRED", 0),
                "stage1_capacity": capacity}
