"""Exact-file transaction probes on synthetic databases only."""
import sqlite3

import pytest

from test_phase3f_foundation_baseline import case
from pro_a.foundation_schema_migration import (
    AUTHORIZED_SQL_SHA256, SQL_PATH, execute_authorized_schema_migration, frozen_statements,
)
from pro_a.foundation_schema_preparation import require_execution_schema
from pro_a.production_promotion import PromotionError, database_identity, sha256_file


@pytest.fixture
def migration_case(case):
    case["db"].execute("UPDATE meta SET value='0.2.1' WHERE key='schema_version'")
    return case


def migrate(c, **overrides):
    options = dict(configured_production_path=c["production"], expected_old_sha256=sha256_file(c["production"]),
                   expected_sql_sha256=AUTHORIZED_SQL_SHA256, backup_path=c["root"] / "recovery.db")
    options.update(overrides)
    return execute_authorized_schema_migration(c["production"], **options)


def test_exact_authorized_file_migration_preserves_legacy(migration_case):
    c = migration_case
    old = database_identity(c["production"])
    result = migrate(c)
    assert result["before"] == old and result["backup"]["sha256"] == old["sha256"]
    assert result["after"]["schema_version"] == "0.2.3"
    assert result["legacy_diff"]["legacy_rows_preserved"]
    assert result["legacy_diff"]["active_native_links"] == 0
    with c["db"].connect() as con:
        require_execution_schema(con)


@pytest.mark.parametrize("after", [1, 5, 15, len(frozen_statements(SQL_PATH.read_bytes())) - 3])
def test_exact_file_failure_restores_old_bytes(migration_case, after):
    c = migration_case
    old = database_identity(c["production"])
    with pytest.raises(PromotionError, match="STOP_ROLLED_BACK_OLD_BYTES_VERIFIED.*INJECTED"):
        migrate(c, inject_failure_after=after)
    assert database_identity(c["production"]) == old
    assert sha256_file(c["root"] / "recovery.db") == old["sha256"]


@pytest.mark.parametrize("field,error", [("expected_old_sha256", "OLD_PRODUCTION_SHA"), ("expected_sql_sha256", "SQL_SHA")])
def test_authorization_mismatch_is_read_only(migration_case, field, error):
    c = migration_case
    old = database_identity(c["production"])
    with pytest.raises(PromotionError, match=error):
        migrate(c, **{field: "0" * 64})
    assert database_identity(c["production"]) == old and not (c["root"] / "recovery.db").exists()


def test_wrong_configured_path_is_rejected(migration_case):
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_PATH"):
        migrate(migration_case, configured_production_path=migration_case["root"] / "other.db")


def test_recovery_artifact_never_overwritten(migration_case):
    c = migration_case
    path = c["root"] / "recovery.db"
    path.write_bytes(b"original recovery")
    with pytest.raises(PromotionError, match="RECOVERY_ARTIFACT"):
        migrate(c)
    assert path.read_bytes() == b"original recovery"


def test_concurrent_writer_stops_without_mutation(migration_case):
    c = migration_case
    old = database_identity(c["production"])
    with sqlite3.connect(c["production"], isolation_level=None) as writer:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(PromotionError, match="STOP_ROLLED_BACK_OLD_BYTES_VERIFIED.*locked"):
            migrate(c)
        writer.rollback()
    assert database_identity(c["production"]) == old and not (c["root"] / "recovery.db").exists()


def test_altered_sql_rejected():
    with pytest.raises(PromotionError, match="AUTHORIZED_SQL_SHA_MISMATCH"):
        frozen_statements(SQL_PATH.read_bytes() + b"\n")
