"""Frozen foundation snapshots, separate from official Current View ordering.

Guard installation is explicit and NEVER part of promotion/shadow application.
An existing database without these guards cannot accept baseline mutations.
"""
from __future__ import annotations

import sqlite3


BASELINE_GUARDS = {
    "foundation_baseline_replace": """CREATE TRIGGER foundation_baseline_replace
BEFORE INSERT ON current_views WHEN EXISTS (
 SELECT 1 FROM current_views WHERE status='baseline' AND (
 view_id=NEW.view_id OR (node_id=NEW.node_id AND version=NEW.version)))
BEGIN SELECT RAISE(ABORT,'FROZEN_BASELINE_REPLACE_FORBIDDEN'); END""",
    "foundation_baseline_insert": """CREATE TRIGGER foundation_baseline_insert
BEFORE INSERT ON current_views WHEN NEW.status='baseline'
BEGIN
 SELECT CASE WHEN substr(NEW.version,1,9)<>'baseline_'
 OR EXISTS (SELECT 1 FROM current_views WHERE view_id=NEW.view_id
            OR (node_id=NEW.node_id AND version=NEW.version))
 OR COALESCE(NEW.previous_view_id,'')<>'' OR NEW.revision_seq<>0
 OR NEW.accepted_proposal_id<>'' OR NEW.change_level<>'baseline'
 THEN RAISE(ABORT,'INVALID_BASELINE_IDENTITY') END;
END""",
    "foundation_baseline_update": """CREATE TRIGGER foundation_baseline_update
BEFORE UPDATE ON current_views WHEN OLD.status='baseline' OR NEW.status='baseline'
BEGIN SELECT RAISE(ABORT,'FROZEN_BASELINE_UPDATE_FORBIDDEN'); END""",
    "foundation_baseline_delete": """CREATE TRIGGER foundation_baseline_delete
BEFORE DELETE ON current_views WHEN OLD.status='baseline'
BEGIN SELECT RAISE(ABORT,'FROZEN_BASELINE_DELETE_FORBIDDEN'); END""",
    "foundation_official_predecessor": """CREATE TRIGGER foundation_official_predecessor
BEFORE INSERT ON current_views WHEN NEW.status='official'
BEGIN
 SELECT CASE WHEN substr(NEW.version,1,9)='baseline_' OR EXISTS (
 SELECT 1 FROM current_views WHERE view_id=NEW.previous_view_id AND status='baseline')
 THEN RAISE(ABORT,'BASELINE_IS_NOT_OFFICIAL_PREDECESSOR') END;
END""",
    "foundation_official_predecessor_update": """CREATE TRIGGER foundation_official_predecessor_update
BEFORE UPDATE ON current_views WHEN NEW.status='official'
BEGIN
 SELECT CASE WHEN substr(NEW.version,1,9)='baseline_' OR EXISTS (
 SELECT 1 FROM current_views WHERE view_id=NEW.previous_view_id AND status='baseline')
 THEN RAISE(ABORT,'BASELINE_IS_NOT_OFFICIAL_PREDECESSOR') END;
END""",
}


def install_baseline_guards(connection: sqlite3.Connection) -> None:
    """Explicit schema preparation for disposable fixtures or a separately approved migration."""
    for name, sql in BASELINE_GUARDS.items():
        existing = connection.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (name,)).fetchone()
        if existing is None:
            connection.execute(sql)
        elif existing[0] != sql:
            raise ValueError(f"BASELINE_GUARD_DRIFT:{name}")


def require_baseline_guards(connection: sqlite3.Connection) -> None:
    for name, sql in BASELINE_GUARDS.items():
        existing = connection.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (name,)).fetchone()
        if existing is None or existing[0] != sql:
            raise ValueError(f"BASELINE_SCHEMA_PRECONDITION_MISSING:{name}")


def baseline_reference(connection: sqlite3.Connection, node_id: str) -> list[dict]:
    """Historical context only. Does not choose or replace the official predecessor."""
    return [dict(row) for row in connection.execute(
        "SELECT * FROM current_views WHERE node_id=? AND status='baseline' ORDER BY view_id", (node_id,)
    )]
