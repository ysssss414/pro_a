"""Source-original IMA integration metadata; no canonical knowledge or View writes."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config
from .db import now_iso
from .ids import make_id
from .ima import IMAClient, IMAError
from .storage import write_json


REMOTE_STAGES = {"duplicate_check", "create_media", "cos_upload", "add_knowledge"}


def source_sync_write_authorizer(action, first, second, database, trigger):
    if action == sqlite3.SQLITE_INSERT:
        allowed = first == "ima_objects"
    elif action == sqlite3.SQLITE_UPDATE:
        allowed = (first == "sources" and second in {"ima_media_id", "ima_kb_id"}) or (
            first == "ima_objects" and second in {"ima_folder_id", "ima_media_id", "title", "synced_at", "status"})
    else:
        if action == sqlite3.SQLITE_FUNCTION and second == "load_extension":
            return sqlite3.SQLITE_DENY
        if action in {sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                      sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_RECURSIVE}:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK if allowed and database == "main" and trigger is None else sqlite3.SQLITE_DENY


@contextmanager
def _connect(path: Path, *, write: bool = False):
    # mode=rw never initializes a missing Production DB or runs migrations.
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode={'rw' if write else 'ro'}", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        if write:
            conn.set_authorizer(source_sync_write_authorizer)
        else:
            conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        yield conn
        if write:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def source_mapping_status(source: dict, mappings: list[dict], target_kb: str | None) -> str:
    """Pure consistency gate shared by preview, sync and read-only observability."""
    media, kb = source["ima_media_id"], source["ima_kb_id"]
    if len(mappings) > 1 or bool(media) != bool(kb) or (kb and target_kb is not None and kb != target_kb):
        return "LOCAL_MAPPING_CONFLICT"
    if not mappings:
        return "LOCAL_MAPPING_CONFLICT" if media else "NOT_MAPPED"
    row = mappings[0]
    if not row["ima_kb_id"] or (target_kb is not None and row["ima_kb_id"] != target_kb):
        return "LOCAL_MAPPING_CONFLICT"
    if row["status"] == "synced":
        valid = bool(media.strip()) and media == row["ima_media_id"] and kb == row["ima_kb_id"]
        return "IDEMPOTENT" if valid else "LOCAL_MAPPING_CONFLICT"
    if media or kb:
        return "LOCAL_MAPPING_CONFLICT"
    if row["status"] == "remote_state_uncertain":
        return "REMOTE_STATE_UNCERTAIN"
    if row["status"] in {"name_conflict_unresolved", "skipped_same_name"} and not row["ima_media_id"]:
        return "REMOTE_NAME_EXISTS_UNRESOLVED"
    if row["status"] == "sync_failed" and not row["ima_media_id"]:
        return "RETRY_SAFE"
    return "LOCAL_MAPPING_CONFLICT"


def source_ima_observability(source: dict, mappings: list[dict], target_kb: str | None) -> dict:
    state = source_mapping_status(source, mappings, target_kb)
    status, message = {
        "IDEMPOTENT": ("synced", "Synced to IMA"),
        "NOT_MAPPED": ("not_synced", "Not synced to IMA"),
        "RETRY_SAFE": ("sync_failed", "IMA sync failed"),
        "REMOTE_NAME_EXISTS_UNRESOLVED": ("name_conflict_unresolved", "IMA object exists by name, but remote identity is unresolved"),
        "REMOTE_STATE_UNCERTAIN": ("remote_state_uncertain", "IMA remote state is uncertain; reconciliation required"),
        "LOCAL_MAPPING_CONFLICT": ("local_mapping_conflict", "IMA local mapping is inconsistent; reconciliation required"),
    }[state]
    return {"status": status, "target_configured": bool(target_kb), "mapped": state == "IDEMPOTENT",
            "message": message}


def _state(conn, source_id: str) -> tuple[dict | None, list[dict]]:
    source = conn.execute(
        "SELECT source_id,original_name,archived_path,ima_media_id,ima_kb_id FROM sources WHERE source_id=?",
        (source_id,),
    ).fetchone()
    mappings = [dict(r) for r in conn.execute(
        "SELECT * FROM ima_objects WHERE local_object_type='source' AND local_object_id=? ORDER BY mapping_id",
        (source_id,),
    )]
    return dict(source) if source is not None else None, mappings


def _mapping_snapshot(source, mappings) -> dict:
    return {"source": {k: source[k] for k in ("ima_media_id", "ima_kb_id")} if source else None,
            "objects": mappings}


def _preflight(cfg: AppConfig, client: IMAClient, source: dict | None) -> tuple[str, int | None, int | None]:
    if not cfg.ima.enabled:
        return "DISABLED", None, None
    if not client.available:
        return "CREDENTIALS_MISSING", None, None
    if not cfg.ima.upload_originals:
        return "UPLOAD_ORIGINALS_DISABLED", None, None
    if not cfg.ima.source_kb_id.strip():
        return "SOURCE_KB_NOT_CONFIGURED", None, None
    if source is None:
        return "SOURCE_NOT_FOUND", None, None
    path = Path(source["archived_path"])
    media_type, size = None, None
    try:
        if not path.is_file():
            return "ARCHIVE_FILE_MISSING", None, None
        size = path.stat().st_size
        media_type = client._media_type(path)
        media_type, _, size = client._preflight(path)
    except IMAError as exc:
        return exc.code, media_type, size
    except OSError:
        return "ARCHIVE_FILE_MISSING", media_type, size
    return "READY", media_type, size


def _preview(cfg: AppConfig, client: IMAClient, source_id: str, source: dict | None, mappings: list[dict]) -> dict:
    preflight, media_type, size = _preflight(cfg, client, source)
    local = source_mapping_status(source, mappings, cfg.ima.source_kb_id) if source else "NOT_MAPPED"
    result = {
        "source_id": source_id, "original_name": source["original_name"] if source else "",
        "title": f"[{source_id}] {source['original_name']}" if source else "",
        "media_type": media_type, "file_size": size, "target_kb_id": cfg.ima.source_kb_id,
        "target_folder_id": cfg.ima.source_folder_id, "target_folder_configured": bool(cfg.ima.source_folder_id),
        "preflight_status": preflight, "local_mapping_status": local,
        "would_upload": preflight == "READY" and local in {"NOT_MAPPED", "RETRY_SAFE"},
        "mapping_before": _mapping_snapshot(source, mappings), "remote_stages_attempted": [],
        "stage": "preflight", "media_id": mappings[0]["ima_media_id"] if len(mappings) == 1 else "",
        "remote_state_uncertain": local == "REMOTE_STATE_UNCERTAIN",
        "status": "preview", "result_classification": preflight,
    }
    if local == "IDEMPOTENT":
        result.update(status="synced", result_classification=local)
    elif local in {"LOCAL_MAPPING_CONFLICT", "REMOTE_STATE_UNCERTAIN", "REMOTE_NAME_EXISTS_UNRESOLVED"}:
        result.update(status={"LOCAL_MAPPING_CONFLICT": "failed", "REMOTE_STATE_UNCERTAIN": "remote_state_uncertain",
                              "REMOTE_NAME_EXISTS_UNRESOLVED": "name_conflict_unresolved"}[local], result_classification=local)
    elif preflight != "READY":
        result["status"] = "disabled" if preflight in {"DISABLED", "UPLOAD_ORIGINALS_DISABLED"} else "failed"
    result["mapping_after"] = result["mapping_before"]
    return result


def preview_source_sync(cfg: AppConfig, source_id: str, *, client: IMAClient | None = None) -> dict[str, Any]:
    """Only local reads, including credential availability; zero remote calls and DB writes."""
    client = client or IMAClient(cfg.ima)
    try:
        with _connect(cfg.db_path) as conn:
            return _preview(cfg, client, source_id, *_state(conn, source_id))
    except (sqlite3.Error, OSError):
        result = _preview(cfg, client, source_id, None, [])
        result.update(status="failed", preflight_status="LOCAL_DATABASE_UNAVAILABLE",
                      result_classification="LOCAL_DATABASE_UNAVAILABLE", mapping_before=None, mapping_after=None)
        return result


def _write_mapping(conn, cfg, source, existing, status: str, media_id: str) -> dict:
    if status == "synced" and not media_id.strip():
        raise IMAError("Synced mapping requires a media identity", code="SYNC_MEDIA_ID_EMPTY", stage="local_mapping_commit")
    mapping_id = existing["mapping_id"] if existing else make_id("IMA")
    values = (cfg.ima.source_folder_id, media_id, f"[{source['source_id']}] {source['original_name']}",
              now_iso() if status == "synced" else "", status)
    if existing:
        conn.execute("UPDATE ima_objects SET ima_folder_id=?,ima_media_id=?,title=?,synced_at=?,status=? WHERE mapping_id=?",
                     (*values, mapping_id))
    else:
        conn.execute("""INSERT INTO ima_objects(mapping_id,local_object_type,local_object_id,ima_kb_id,
                     ima_folder_id,ima_media_id,title,synced_at,status) VALUES(?,'source',?,?,?,?,?,?,?)""",
                     (mapping_id, source["source_id"], cfg.ima.source_kb_id, *values))
    if status == "synced":
        conn.execute("UPDATE sources SET ima_media_id=?,ima_kb_id=? WHERE source_id=?",
                     (media_id, cfg.ima.source_kb_id, source["source_id"]))
    return dict(conn.execute("SELECT * FROM ima_objects WHERE mapping_id=?", (mapping_id,)).fetchone())


def _persist_outcome(cfg, source, expected, status: str, media_id: str) -> dict:
    with _connect(cfg.db_path, write=True) as conn:
        current, mappings = _state(conn, source["source_id"])
        if current != source or mappings != [expected]:
            raise IMAError("IMA local mapping changed during upload", code="LOCAL_MAPPING_CONFLICT",
                           stage="local_mapping_commit", media_id=media_id, remote_state_uncertain=True)
        return _write_mapping(conn, cfg, source, expected, status, media_id)


def sync_source(cfg: AppConfig, source_id: str, *, client: IMAClient | None = None) -> dict[str, Any]:
    """Shared ingestion/explicit-CLI path. No scheduler and no uncertain upload retries."""
    client = client or IMAClient(cfg.ima)
    result = preview_source_sync(cfg, source_id, client=client)
    if not result["would_upload"]:
        return result
    try:
        with _connect(cfg.db_path, write=True) as conn:
            # Repeat all local gates under a writer lock before reserving an attempt.
            source, mappings = _state(conn, source_id)
            result = _preview(cfg, client, source_id, source, mappings)
            if not result["would_upload"]:
                return result
            # Durable before any network: crash/commit failure cannot invite a blind retry.
            expected = _write_mapping(conn, cfg, source, mappings[0] if mappings else None,
                                      "remote_state_uncertain", "")
    except (sqlite3.Error, OSError):
        result.update(status="failed", stage="local_mapping_commit", result_classification="LOCAL_MAPPING_COMMIT_FAILED")
        return result

    stages: list[str] = []

    def on_stage(stage: str, media_id: str) -> None:
        nonlocal expected
        if media_id and expected["ima_media_id"] != media_id:
            try:
                expected = _persist_outcome(cfg, source, expected, "remote_state_uncertain", media_id)
            except (sqlite3.Error, OSError):
                raise IMAError("Known remote identity could not be recorded", code="LOCAL_MAPPING_COMMIT_FAILED",
                               stage="local_mapping_commit", media_id=media_id, remote_state_uncertain=True) from None
        stages.append(stage)

    try:
        uploaded = client.upload_file(Path(source["archived_path"]), cfg.ima.source_kb_id,
                                      cfg.ima.source_folder_id, title=result["title"],
                                      on_stage=on_stage, check_duplicate=True)
        if uploaded.get("skipped"):
            status, code, media_id = "name_conflict_unresolved", "REMOTE_NAME_EXISTS_UNRESOLVED", ""
        else:
            media_id = uploaded.get("media_id")
            if not isinstance(media_id, str) or not media_id.strip():
                raise IMAError("Upload completed without a media identity", code="SYNC_MEDIA_ID_EMPTY",
                               stage="add_knowledge", remote_state_uncertain=True)
            status, code = "synced", "SYNCED"
        stage = "duplicate_check" if status == "name_conflict_unresolved" else "local_mapping_commit"
        uncertain = False
    except Exception as exc:
        uncertain = "create_media" in stages or (isinstance(exc, IMAError) and exc.remote_state_uncertain)
        status = "remote_state_uncertain" if uncertain else "sync_failed"
        # Only our stable category and stage reach ordinary receipts, never exception text.
        code = exc.code if isinstance(exc, IMAError) else "IMA_UPLOAD_FAILED"
        stage = exc.stage if isinstance(exc, IMAError) else (stages[-1] if stages else "preflight")
        media_id = (exc.media_id if isinstance(exc, IMAError) else "") or expected["ima_media_id"]

    try:
        _persist_outcome(cfg, source, expected, status, media_id)
    except (sqlite3.Error, OSError, IMAError) as exc:
        uncertain = uncertain or "create_media" in stages
        status = "remote_state_uncertain" if uncertain else "sync_failed"
        code = "LOCAL_MAPPING_CONFLICT" if isinstance(exc, IMAError) and exc.code == "LOCAL_MAPPING_CONFLICT" else "LOCAL_MAPPING_COMMIT_FAILED"
        stage = "local_mapping_commit"
    result.update(status="failed" if status == "sync_failed" else status, result_classification=code,
                  stage=stage, remote_stages_attempted=stages, media_id=media_id, remote_state_uncertain=uncertain)
    try:
        with _connect(cfg.db_path) as conn:
            result["mapping_after"] = _mapping_snapshot(*_state(conn, source_id))
    except (sqlite3.Error, OSError):
        result["mapping_after"] = None
    return result


def _run_operation(cfg: AppConfig, source_id: str, operation: str, *, client: IMAClient | None = None) -> dict:
    if operation not in {"preview-source", "sync-production-source"}:
        raise ValueError("Unknown IMA Source operation")
    receipt = {"timestamp": now_iso(), "operation": operation,
               **preview_source_sync(cfg, source_id, client=client)}
    path = cfg.root / "generated" / "receipts" / f"phase3b_{make_id('IMA')}.json"
    receipt["receipt_path"] = str(path)
    # Establish a writable audit artifact before allowing any remote side effect.
    write_json(path, receipt)
    if operation == "sync-production-source":
        receipt.update(sync_source(cfg, source_id, client=client))
        try:
            write_json(path, receipt)
        except OSError:
            receipt["receipt_error"] = "SYNC_RECEIPT_WRITE_FAILED"
    return receipt


def preview_production_source(source_id: str) -> dict:
    return _run_operation(load_config(), source_id, "preview-source")


def sync_production_source(source_id: str) -> dict:
    """Only this named standalone operation grants configured-Production sync authority."""
    return _run_operation(load_config(), source_id, "sync-production-source")
