"""Explicit, hash-authorized schema-only execution; never imports Foundation data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

from .foundation_schema_preparation import require_execution_schema
from .production_promotion import (
    PromotionError, database_identity, database_rows, semantic_snapshot,
    sha256_file, sqlite_sidecars,
)

AUTHORIZED_SQL_SHA256 = "17d0706380a4ba57c78081b9aeb37141115564b2f8210671194358d338b8e4f0"
SQL_PATH = Path(__file__).with_name("migrations") / "foundation_0_2_3_relation_native.sql"


def require(condition, message):
    if not condition:
        raise PromotionError(message)


def frozen_statements(data):
    """Split the authorized bytes, including triggers, without rebuilding SQL."""
    require(hashlib.sha256(data).hexdigest() == AUTHORIZED_SQL_SHA256, "AUTHORIZED_SQL_SHA_MISMATCH")
    statements, pending = [], ""
    for line in data.decode("utf-8").splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending)
            pending = ""
    require(not pending.strip(), "INCOMPLETE_AUTHORIZED_SQL")
    require(statements[1].strip() == "BEGIN IMMEDIATE;" and statements[-1].strip() == "COMMIT;", "TRANSACTION_ENVELOPE_DRIFT")
    return statements


def verify_legacy_rows(before, after):
    """Preserve all original rows, allowing only the reviewed meta/link delta."""
    for table, rows in before.items():
        if table not in {"meta", "relation_evidence_links"}:
            require(rows == after.get(table), "MIGRATION_EXISTING_ROWS_CHANGED:" + table)
    old_meta = {json.loads(r)["key"]: json.loads(r)["value"] for r in before["meta"]}
    new_meta = {json.loads(r)["key"]: json.loads(r)["value"] for r in after["meta"]}
    from .foundation_execution_contract import CONTRACT_SHA256
    require(new_meta == {**old_meta, "schema_version": "0.2.3", "foundation_execution_contract_sha256": CONTRACT_SHA256}, "UNEXPECTED_META_DELTA")
    old_links = [json.loads(r) for r in before.get("relation_evidence_links", [])]
    keys = {(r["relation_id"], r["claim_id"], r["evidence_role"]) for r in old_links}
    for encoded in before["node_relations"]:
        row = json.loads(encoded)
        cid = row["evidence_claim_id"]
        key = (row["relation_id"], cid, "supports")
        if cid and cid.strip() and key not in keys:
            old_links.append(dict(relation_id=row["relation_id"], claim_id=cid, evidence_role="supports", status="active", created_at=row["created_at"]))
            keys.add(key)
    expected = [{**r, "provenance_mode": "CLAIM_LINKED", "evidence_id": "", "source_id": None,
                 "source_sha256": "", "evidence_sha256": "", "authorization_id": None} for r in old_links]
    actual = [json.loads(r) for r in after["relation_evidence_links"]]
    require(sorted(expected, key=lambda r: (r["relation_id"], r["claim_id"], r["evidence_role"])) ==
            sorted(actual, key=lambda r: (r["relation_id"], r["claim_id"] or "", r["evidence_role"])), "UNEXPECTED_LEGACY_LINK_DELTA")
    require(not after["relation_temporal_semantics"] and not after["relation_evidence_authorizations"], "FOUNDATION_CONTENT_INSERTED")
    require(set(after) == set(before) | {"relation_evidence_links", "relation_temporal_semantics", "relation_evidence_authorizations"}, "UNEXPECTED_TABLE_DELTA")
    return {"legacy_rows_preserved": True, "before": semantic_snapshot(before), "after": semantic_snapshot(after),
            "legacy_evidence_backfill_count": len(actual) - len(before.get("relation_evidence_links", [])), "active_native_links": 0}


def execute_authorized_schema_migration(path, *, configured_production_path, expected_old_sha256,
                                        expected_sql_sha256, backup_path, inject_failure_after=None):
    """Caller must complete human/commit/input preflight first. No retry or repair.

    BEGIN IMMEDIATE reserves the only writer before backup. COMMIT from the exact
    file is delayed until contract, integrity, FK and all legacy rows pass. The
    failure injection is for synthetic tests only and never changes SQL bytes.
    """
    path, backup_path = Path(path).resolve(), Path(backup_path).resolve()
    require(path == Path(configured_production_path).resolve(), "CONFIGURED_PRODUCTION_PATH_MISMATCH")
    require(not path.is_symlink() and path.stat().st_nlink == 1, "PRODUCTION_LINK_ALIAS_FORBIDDEN")
    require(backup_path != path and not backup_path.exists(), "RECOVERY_ARTIFACT_MUST_BE_NEW")
    require(expected_sql_sha256 == AUTHORIZED_SQL_SHA256, "AUTHORIZED_SQL_SHA_MISMATCH")
    statements = frozen_statements(SQL_PATH.read_bytes())
    before_identity = database_identity(path)
    require(before_identity["sha256"] == expected_old_sha256, "AUTHORIZED_OLD_PRODUCTION_SHA_MISMATCH")
    require(before_identity["schema_version"] == "0.2.1", "AUTHORIZED_SOURCE_SCHEMA_MISMATCH")
    connection = sqlite3.connect(path, timeout=0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "UNVALIDATED_JOURNAL_MODE")
        connection.execute(statements[0])
        connection.execute(statements[1])
        require(sha256_file(path) == expected_old_sha256 and not any(sqlite_sidecars(path).values()), "PRODUCTION_CHANGED_BEFORE_WRITE_RESERVATION")
        before = database_rows(connection)
        require(semantic_snapshot(before) == before_identity["semantic_snapshot"], "PRODUCTION_CHANGED_BEFORE_BACKUP")
        # No DDL/DML has run. Byte copy is offline with respect to all writers.
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("rb") as source, backup_path.open("xb") as backup:
            import shutil
            shutil.copyfileobj(source, backup)
            backup.flush()
            import os
            os.fsync(backup.fileno())
        backup_identity = database_identity(backup_path)
        require(backup_identity["sha256"] == expected_old_sha256, "OFFLINE_BACKUP_SHA_MISMATCH")
        require(backup_identity["semantic_snapshot"] == before_identity["semantic_snapshot"], "OFFLINE_BACKUP_SEMANTIC_MISMATCH")
        for index, statement in enumerate(statements[2:-1], 1):
            connection.execute(statement)
            if index == inject_failure_after:
                raise PromotionError("INJECTED_AUTHORIZED_MIGRATION_FAILURE")
        require_execution_schema(connection)
        require(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "MIGRATION_INTEGRITY_FAILED")
        require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "MIGRATION_FK_FAILED")
        legacy = verify_legacy_rows(before, database_rows(connection))
        connection.execute(statements[-1])
    except Exception as error:
        if connection.in_transaction:
            connection.rollback()
        connection.close()
        restored = database_identity(path)
        require(restored == before_identity, "MIGRATION_FAILURE_OLD_BYTE_STATE_NOT_PRESERVED")
        raise PromotionError("MIGRATION_STOP_ROLLED_BACK_OLD_BYTES_VERIFIED:" + str(error)) from error
    finally:
        connection.close()
    after_identity = database_identity(path)
    require(after_identity["schema_version"] == "0.2.3", "POST_COMMIT_SCHEMA_MISMATCH")
    return {"status": "SCHEMA_MIGRATED_ONLY", "before": before_identity, "after": after_identity,
            "backup": backup_identity, "sql_sha256": expected_sql_sha256, "legacy_diff": legacy,
            "write_quiescence": "BEGIN IMMEDIATE reserved sole writer before byte backup through COMMIT; no checkpoint required; DELETE journal; sidecars absent before/after"}
