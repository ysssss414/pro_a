"""Offline operator preflight and coordinated Workbench backup/restore."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
from typing import Any
from uuid import uuid4

from .config import BoundaryError, WorkbenchConfig, checked_path
from .store import Store


BACKUP_FORMAT = "phase42-workbench-backup-v1"
DEFAULT_WINDOWS_PATH_LIMIT = 240
ARTIFACT_PATH_RESERVE = 112


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_inventory(root: Path) -> list[dict[str, Any]]:
    result = []
    for directory, directories, names in os.walk(root, followlinks=False):
        directories.sort()
        names.sort()
        for name in [*directories, *names]:
            checked_path(Path(directory) / name)
        for name in names:
            path = checked_path(Path(directory) / name)
            if path.is_file():
                result.append({
                    "path": path.relative_to(root).as_posix(),
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                })
    return result


def _require_copy_headroom(root: Path, relative_paths: list[str]) -> None:
    if os.name != "nt":
        return
    longest = max((len(str(root / Path(relative))) for relative in relative_paths),
                  default=len(str(root)))
    if longest > DEFAULT_WINDOWS_PATH_LIMIT:
        raise BoundaryError("PATH_LENGTH_UNSAFE")


def path_preflight(config: WorkbenchConfig, *, limit: int = DEFAULT_WINDOWS_PATH_LIMIT) -> dict[str, Any]:
    """Report deterministic legacy-Windows path headroom without creating files."""
    if not 180 <= limit <= 32767:
        raise BoundaryError("PATH_LIMIT_INVALID")
    paths = {
        "knowledge_db": len(str(config.knowledge_db)),
        "state_db_with_migration_backup": len(str(config.state_db)) + len(".stage6-backup"),
        "artifact_generated_path": len(str(config.artifact_root)) + 1 + ARTIFACT_PATH_RESERVE,
    }
    longest = max(paths.values())
    return {
        "status": "PASS" if longest <= limit else "FAIL",
        "limit": limit,
        "artifact_path_reserve": ARTIFACT_PATH_RESERVE,
        "estimated_lengths": paths,
        "longest_estimated_path": longest,
        "maximum_artifact_root_chars": limit - ARTIFACT_PATH_RESERVE - 1,
        "recommended_workspace_root_max_chars": 96,
    }


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}


def _active_work(connection: sqlite3.Connection) -> dict[str, int]:
    tables = _tables(connection)
    cloud = (connection.execute(
        "SELECT COUNT(*) FROM cloud_jobs WHERE state IN ('QUEUED','RUNNING')"
    ).fetchone()[0] if "cloud_jobs" in tables else 0)
    source = (connection.execute(
        "SELECT COUNT(*) FROM source_processing_runs WHERE state NOT IN "
        "('HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED','RECOVERY_REQUIRED')"
    ).fetchone()[0] if "source_processing_runs" in tables else 0)
    return {"cloud_jobs": cloud, "source_processing_runs": source}


def _safe_output(config: WorkbenchConfig, output: Path) -> Path:
    output = checked_path(output, missing=True)
    protected = (
        checked_path(config.knowledge_db), checked_path(config.state_db),
        checked_path(config.artifact_root),
    )
    if any(output == path or output.is_relative_to(path) or path.is_relative_to(output)
           for path in protected):
        raise BoundaryError("BACKUP_PATH_OVERLAP")
    return output


def create_backup(config: WorkbenchConfig, output: Path) -> dict[str, Any]:
    """Create a coherent backup while holding the sole SQLite writer lock.

    Operators must stop the HTTP service and workers first. The active-state check
    makes that drain requirement observable; the exclusive lock rejects a live
    writer instead of producing a best-effort copy.
    """
    config.validate()
    output = _safe_output(config, output)
    if output.exists():
        raise BoundaryError("BACKUP_DESTINATION_EXISTS")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = checked_path(output.with_name(output.name + ".partial-" + uuid4().hex), missing=True)
    source_artifacts = checked_path(config.artifact_root)
    relative_paths = [row["path"] for row in _artifact_inventory(source_artifacts)]
    _require_copy_headroom(partial / "artifacts", relative_paths)
    partial.mkdir()
    try:
        state_copy = partial / "workbench.sqlite3"
        artifact_copy = partial / "artifacts"
        source_path = checked_path(config.state_db)
        connection = sqlite3.connect(source_path, timeout=0)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BoundaryError("WORKBENCH_INTEGRITY_FAILED")
            active = _active_work(connection)
            if any(active.values()):
                raise BoundaryError("WORKBENCH_DRAIN_REQUIRED")
            if connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal":
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("BEGIN EXCLUSIVE")
            shutil.copyfile(source_path, state_copy)
            shutil.copytree(source_artifacts, artifact_copy)
            connection.rollback()
        except sqlite3.OperationalError as error:
            raise BoundaryError("WORKBENCH_DRAIN_REQUIRED") from error
        finally:
            connection.close()
        with closing(sqlite3.connect(state_copy)) as copied:
            if copied.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BoundaryError("BACKUP_INTEGRITY_FAILED")
            schema = dict(copied.execute(
                "SELECT key,value FROM workbench_meta WHERE key IN ('schema_version','mode')"
            ))
        inventory = _artifact_inventory(artifact_copy)
        manifest = {
            "document_type": BACKUP_FORMAT,
            "schema_version": "1",
            "workbench_schema_version": schema["schema_version"],
            "mode": schema["mode"],
            "consistency": "QUIESCED_EXCLUSIVE_LOCK",
            "active_work": active,
            "configuration_contract": {
                "absolute_paths_stored": False,
                "secrets_stored": False,
                "restore_config_required": True,
                "session_token_stored": False,
            },
            "state": {"path": "workbench.sqlite3", "sha256": _sha256(state_copy),
                      "size_bytes": state_copy.stat().st_size},
            "artifacts": inventory,
        }
        (partial / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(partial, output)
        return {"status": "BACKUP_COMPLETE", "backup_format": BACKUP_FORMAT,
                "workbench_schema_version": schema["schema_version"],
                "artifact_files": len(inventory), "state_sha256": manifest["state"]["sha256"]}
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def _load_and_verify_backup(backup: Path) -> dict[str, Any]:
    backup = checked_path(backup)
    if not backup.is_dir():
        raise BoundaryError("BACKUP_UNAVAILABLE")
    manifest_path = checked_path(backup / "manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        raise BoundaryError("BACKUP_MANIFEST_INVALID") from None
    if (manifest.get("document_type") != BACKUP_FORMAT
            or manifest.get("schema_version") != "1"):
        raise BoundaryError("BACKUP_MANIFEST_INVALID")
    state = checked_path(backup / manifest["state"]["path"])
    if _sha256(state) != manifest["state"]["sha256"]:
        raise BoundaryError("BACKUP_HASH_MISMATCH")
    artifact_root = checked_path(backup / "artifacts")
    if _artifact_inventory(artifact_root) != manifest["artifacts"]:
        raise BoundaryError("BACKUP_HASH_MISMATCH")
    return manifest


def restore_backup(config: WorkbenchConfig, backup: Path) -> dict[str, Any]:
    """Restore into empty Workbench locations and rebind configured private paths."""
    config.validate()
    manifest = _load_and_verify_backup(backup)
    if manifest["mode"] != config.mode:
        raise BoundaryError("BACKUP_MODE_MISMATCH")
    state = checked_path(config.state_db, missing=True)
    artifacts = checked_path(config.artifact_root, missing=True)
    if state.exists() or artifacts.exists():
        raise BoundaryError("RESTORE_DESTINATION_NOT_EMPTY")
    if state.parent == artifacts or artifacts.parent == state:
        raise BoundaryError("RESTORE_PATH_OVERLAP")
    state.parent.mkdir(parents=True, exist_ok=True)
    artifacts.parent.mkdir(parents=True, exist_ok=True)
    suffix = ".restore-" + uuid4().hex
    state_partial = checked_path(state.with_name(state.name + suffix), missing=True)
    artifact_partial = checked_path(artifacts.with_name(artifacts.name + suffix), missing=True)
    _require_copy_headroom(artifact_partial, [row["path"] for row in manifest["artifacts"]])
    moved_artifacts = False
    try:
        shutil.copyfile(checked_path(backup / manifest["state"]["path"]), state_partial)
        shutil.copytree(checked_path(backup / "artifacts"), artifact_partial)
        if _artifact_inventory(artifact_partial) != manifest["artifacts"]:
            raise BoundaryError("RESTORE_HASH_MISMATCH")
        with closing(sqlite3.connect(state_partial)) as connection, connection:
            connection.execute("PRAGMA foreign_keys=ON")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BoundaryError("RESTORE_INTEGRITY_FAILED")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise BoundaryError("RESTORE_FOREIGN_KEY_FAILED")
            for key, value in config.bindings().items():
                if key != "schema_version":
                    connection.execute("UPDATE workbench_meta SET value=? WHERE key=?", (value, key))
        os.replace(artifact_partial, artifacts)
        moved_artifacts = True
        os.replace(state_partial, state)
        with Store(config).connect() as connection:
            restored_schema = dict(connection.execute(
                "SELECT key,value FROM workbench_meta WHERE key='schema_version'"
            ))["schema_version"]
        return {"status": "RESTORE_COMPLETE", "backup_format": BACKUP_FORMAT,
                "workbench_schema_version": restored_schema,
                "artifact_files": len(manifest["artifacts"]),
                "paths_rebound": True}
    except Exception:
        if state_partial.exists():
            state_partial.unlink()
        if artifact_partial.exists():
            shutil.rmtree(artifact_partial)
        if moved_artifacts and artifacts.exists() and not state.exists():
            shutil.rmtree(artifacts)
        raise
