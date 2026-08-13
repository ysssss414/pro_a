from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .ids import make_id


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def transaction(self, *, immediate: bool = False):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema)
            self._migrate_0_1_to_0_1_1(conn)
            conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','0.1.1')")

    @staticmethod
    def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    def _add_column(self, conn: sqlite3.Connection, table: str, definition: str) -> None:
        name = definition.split()[0]
        if name not in self._columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

    def _migrate_0_1_to_0_1_1(self, conn: sqlite3.Connection) -> None:
        legacy_source_columns = self._columns(conn, "sources")
        self._add_column(conn, "sources", "underlying_source_id TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "sources", "analysis_mode TEXT NOT NULL DEFAULT 'archive'")
        if "analysis_mode" not in legacy_source_columns:
            conn.execute("UPDATE sources SET analysis_mode=ingestion_mode WHERE status='analyzed'")
        self._add_column(conn, "current_views", "revision_date TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "current_views", "revision_seq INTEGER NOT NULL DEFAULT 0")
        self._add_column(conn, "current_views", "accepted_proposal_id TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "proposals", "source_impact_id TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "proposals", "result_json TEXT NOT NULL DEFAULT '{}'")

        for row in conn.execute("SELECT view_id,version FROM current_views").fetchall():
            version = row["version"]
            revision_date = version[2:10] if version.startswith("v_") and len(version) >= 10 else ""
            revision_seq = 0
            if len(version) > 11 and version[10] == "_":
                try:
                    revision_seq = int(version[11:])
                except ValueError:
                    revision_seq = 0
            conn.execute(
                "UPDATE current_views SET revision_date=?,revision_seq=? WHERE view_id=?",
                (revision_date, revision_seq, row["view_id"]),
            )

        impact_columns = self._columns(conn, "impact_reviews")
        if "target_view_version" not in impact_columns:
            conn.execute("ALTER TABLE impact_reviews RENAME TO impact_reviews_v0_1")
            conn.executescript(
                """
                CREATE TABLE impact_reviews (
                    impact_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_id TEXT NOT NULL,
                    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
                    path_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result_change_level TEXT NOT NULL DEFAULT '',
                    proposal_id TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    target_view_version TEXT NOT NULL DEFAULT '<none>',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    queue_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL DEFAULT '',
                    UNIQUE(batch_id, node_id, target_view_version)
                );
                CREATE INDEX idx_impact_work_queue
                ON impact_reviews(batch_id, status, queue_order, created_at);
                """
            )
            conn.execute(
                """INSERT INTO impact_reviews(
                   impact_id,batch_id,trigger_type,trigger_id,node_id,path_type,status,result_change_level,
                   proposal_id,reason,target_view_version,payload_json,attempts,last_error,queue_order,created_at,evaluated_at)
                   SELECT impact_id,batch_id,trigger_type,trigger_id,node_id,path_type,status,result_change_level,
                   proposal_id,reason,'<none>',reason,0,'',
                   CASE path_type WHEN 'structural' THEN 10 WHEN 'related' THEN 20 ELSE 0 END,
                   created_at,evaluated_at FROM impact_reviews_v0_1"""
            )
            conn.execute("DROP TABLE impact_reviews_v0_1")

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_current_views_revision
            ON current_views(node_id, revision_date DESC, revision_seq DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_current_views_proposal
            ON current_views(accepted_proposal_id) WHERE accepted_proposal_id<>'';
            CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_source_impact
            ON proposals(source_impact_id) WHERE source_impact_id<>'';
            CREATE INDEX IF NOT EXISTS idx_impact_work_queue
            ON impact_reviews(batch_id, status, queue_order, created_at);
            CREATE TABLE IF NOT EXISTS side_effect_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(job_type, object_id)
            );
            CREATE INDEX IF NOT EXISTS idx_side_effect_jobs_status
            ON side_effect_jobs(status, created_at);
            """
        )

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None

    def all(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self.connect() as conn:
            conn.execute(sql, tuple(params))

    def add_node(self, canonical_name: str, primary_type: str, aliases: list[str] | None = None,
                 description: str = "", node_id: str | None = None) -> str:
        node_id = node_id or make_id("NODE")
        ts = now_iso()
        aliases = aliases or []
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT node_id FROM nodes WHERE canonical_name=? AND primary_type=?",
                (canonical_name, primary_type),
            ).fetchone()
            if existing:
                return existing["node_id"]
            conn.execute(
                "INSERT INTO nodes(node_id,canonical_name,primary_type,description,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (node_id, canonical_name, primary_type, description, ts, ts),
            )
            for alias in [canonical_name, *aliases]:
                alias = alias.strip()
                if alias:
                    conn.execute("INSERT OR IGNORE INTO node_aliases(alias,node_id) VALUES(?,?)", (alias, node_id))
        return node_id

    def seed_nodes_csv(self, csv_path: Path) -> int:
        count = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("canonical_name") or "").strip()
                typ = (row.get("primary_type") or "").strip()
                if not name or not typ:
                    continue
                aliases = [x.strip() for x in (row.get("aliases") or "").split("|") if x.strip()]
                before = self.one("SELECT node_id FROM nodes WHERE canonical_name=? AND primary_type=?", (name, typ))
                self.add_node(name, typ, aliases, (row.get("description") or "").strip())
                if not before:
                    count += 1
        return count

    def list_nodes(self, limit: int = 1000) -> list[dict[str, Any]]:
        nodes = self.all("SELECT * FROM nodes WHERE status='active' ORDER BY primary_type, canonical_name LIMIT ?", (limit,))
        for n in nodes:
            n["aliases"] = [r["alias"] for r in self.all("SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias", (n["node_id"],))]
        return nodes

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        node = self.one("SELECT * FROM nodes WHERE node_id=?", (node_id,))
        if node:
            node["aliases"] = [r["alias"] for r in self.all("SELECT alias FROM node_aliases WHERE node_id=?", (node_id,))]
        return node

    def find_node_by_name_or_alias(self, name: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT n.* FROM node_aliases a JOIN nodes n ON n.node_id=a.node_id WHERE a.alias=? COLLATE NOCASE LIMIT 1",
            (name,),
        )

    def add_relation(self, from_node_id: str, relation_type: str, to_node_id: str, **kwargs) -> str:
        rel_id = make_id("REL")
        with self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO node_relations(
                   relation_id,from_node_id,relation_type,to_node_id,scope,valid_from,valid_to,confidence,status,evidence_claim_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (rel_id, from_node_id, relation_type, to_node_id, kwargs.get("scope", ""), kwargs.get("valid_from", ""),
                 kwargs.get("valid_to", ""), kwargs.get("confidence"), kwargs.get("status", "current"),
                 kwargs.get("evidence_claim_id"), now_iso()),
            )
        return rel_id

    def neighbors(self, node_id: str) -> dict[str, list[dict[str, Any]]]:
        structural = []
        related = []
        rows = self.all(
            "SELECT * FROM node_relations WHERE status='current' AND (from_node_id=? OR to_node_id=?)",
            (node_id, node_id),
        )
        for r in rows:
            other = r["to_node_id"] if r["from_node_id"] == node_id else r["from_node_id"]
            item = {**r, "other_node_id": other, "direction": "out" if r["from_node_id"] == node_id else "in"}
            if r["relation_type"] == "part_of":
                structural.append(item)
            else:
                related.append(item)
        return {"structural": structural, "related": related}

    def current_view(self, node_id: str) -> dict[str, Any] | None:
        return self.one(
            """SELECT * FROM current_views WHERE node_id=? AND status='official'
               ORDER BY revision_date DESC,revision_seq DESC,view_id DESC LIMIT 1""",
            (node_id,),
        )

    def versions(self, node_id: str) -> list[str]:
        return [r["version"] for r in self.all("SELECT version FROM current_views WHERE node_id=?", (node_id,))]

    def pending_proposals(self) -> list[dict[str, Any]]:
        return self.all("SELECT * FROM proposals WHERE status='pending' ORDER BY created_at")

    def add_proposal(self, proposal_type: str, payload: dict[str, Any], target_node_id: str | None = None,
                     reason: str = "", propagation_batch_id: str = "", source_impact_id: str = "") -> str:
        if source_impact_id:
            existing = self.one("SELECT proposal_id FROM proposals WHERE source_impact_id=?", (source_impact_id,))
            if existing:
                return existing["proposal_id"]
        proposal_id = make_id("PROP")
        self.execute(
            """INSERT INTO proposals(proposal_id,proposal_type,target_node_id,payload_json,status,reason,
               propagation_batch_id,source_impact_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (proposal_id, proposal_type, target_node_id, json.dumps(payload, ensure_ascii=False), "pending", reason,
             propagation_batch_id, source_impact_id, now_iso()),
        )
        return proposal_id

    def proposal(self, proposal_id: str) -> dict[str, Any] | None:
        row = self.one("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,))
        if row:
            row["payload"] = json.loads(row["payload_json"])
        return row
