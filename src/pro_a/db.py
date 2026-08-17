from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .constants import NODE_TYPES, RELATION_TYPES
from .ids import make_id


CURRENT_VIEW_ORDER = "revision_date DESC,revision_seq DESC,view_id DESC"
RELATION_EVIDENCE_ROLES = {"supports", "contradicts"}
RELATION_EVIDENCE_STATUSES = {"active", "retired"}


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
            self._migrate_0_2_to_0_2_1(conn)
            self._migrate_0_2_1_to_0_2_2(conn)
            conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','0.2.2')")

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
        conn.execute("DROP INDEX IF EXISTS idx_proposals_source_impact")
        conn.execute(
            """CREATE UNIQUE INDEX idx_proposals_source_impact
               ON proposals(source_impact_id)
               WHERE source_impact_id<>'' AND status IN ('pending','accepted')"""
        )

    def _migrate_0_2_to_0_2_1(self, conn: sqlite3.Connection) -> None:
        self._add_column(conn, "claims", "attributed_to TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "source_node_links", "link_origin TEXT NOT NULL DEFAULT 'legacy'")
        self._add_column(conn, "source_node_links", "derived_from_node_id TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "source_node_links", "evidence_excerpt TEXT NOT NULL DEFAULT ''")
        self._add_column(conn, "source_node_links", "evidence_validation_json TEXT NOT NULL DEFAULT '{}'")

    def _migrate_0_2_1_to_0_2_2(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS relation_evidence_links (
               relation_id TEXT NOT NULL REFERENCES node_relations(relation_id) ON DELETE CASCADE,
               claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
               evidence_role TEXT NOT NULL CHECK(evidence_role IN ('supports', 'contradicts')),
               status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'retired')),
               created_at TEXT NOT NULL,
               PRIMARY KEY(relation_id, claim_id, evidence_role)
               )"""
        )
        conn.execute(
            """INSERT OR IGNORE INTO relation_evidence_links(
               relation_id,claim_id,evidence_role,status,created_at
               )
               SELECT relation_id,evidence_claim_id,'supports','active',created_at
               FROM node_relations
               WHERE evidence_claim_id IS NOT NULL AND TRIM(evidence_claim_id)<>''"""
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
        canonical_name = canonical_name.strip()
        if not canonical_name:
            raise ValueError("Node canonical_name is required")
        if primary_type not in NODE_TYPES:
            raise ValueError(f"Invalid Node Type: {primary_type}")
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
            for row_number, row in enumerate(csv.DictReader(f), 2):
                name = (row.get("canonical_name") or "").strip()
                typ = (row.get("primary_type") or "").strip()
                if not name or not typ:
                    continue
                if typ not in NODE_TYPES:
                    raise ValueError(f"Node seed row {row_number}: invalid primary_type {typ!r}")
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

    def add_relation_evidence(
        self,
        relation_id: str,
        claim_id: str,
        *,
        evidence_role: str = "supports",
        status: str = "active",
    ) -> bool:
        if evidence_role not in RELATION_EVIDENCE_ROLES:
            raise ValueError(f"Invalid relation evidence role: {evidence_role}")
        if status not in RELATION_EVIDENCE_STATUSES:
            raise ValueError(f"Invalid relation evidence status: {status}")
        with self.transaction(immediate=True) as conn:
            if not conn.execute(
                "SELECT 1 FROM node_relations WHERE relation_id=?", (relation_id,)
            ).fetchone():
                raise ValueError(f"Unknown Relation: {relation_id}")
            if not conn.execute(
                "SELECT 1 FROM claims WHERE claim_id=?", (claim_id,)
            ).fetchone():
                raise ValueError(f"Unknown evidence Claim: {claim_id}")
            cursor = conn.execute(
                """INSERT OR IGNORE INTO relation_evidence_links(
                   relation_id,claim_id,evidence_role,status,created_at
                   ) VALUES(?,?,?,?,?)""",
                (relation_id, claim_id, evidence_role, status, now_iso()),
            )
        return bool(cursor.rowcount)

    def relation_evidence(self, relation_id: str) -> list[dict[str, Any]]:
        if not self.one("SELECT 1 FROM node_relations WHERE relation_id=?", (relation_id,)):
            raise ValueError(f"Unknown Relation: {relation_id}")
        return self.all(
            """SELECT rel.relation_id,rel.claim_id,rel.evidence_role,
                      rel.status AS evidence_status,rel.created_at AS evidence_created_at,
                      c.source_id,c.statement,c.status,c.confidence
               FROM relation_evidence_links rel
               JOIN claims c ON c.claim_id=rel.claim_id
               WHERE rel.relation_id=?
               ORDER BY rel.claim_id,rel.evidence_role""",
            (relation_id,),
        )

    def add_relation(self, from_node_id: str, relation_type: str, to_node_id: str, **kwargs) -> str:
        if relation_type not in RELATION_TYPES:
            raise ValueError(f"Invalid relation_type: {relation_type}")
        scope = (kwargs.get("scope") or "").strip()
        evidence_claim_id = (kwargs.get("evidence_claim_id") or "").strip()
        requested_status = kwargs.get("status", "current")
        with self.transaction(immediate=True) as conn:
            if not conn.execute(
                "SELECT 1 FROM nodes WHERE node_id=?", (from_node_id,)
            ).fetchone():
                raise ValueError(f"Unknown from Node: {from_node_id}")
            if not conn.execute(
                "SELECT 1 FROM nodes WHERE node_id=?", (to_node_id,)
            ).fetchone():
                raise ValueError(f"Unknown to Node: {to_node_id}")
            if evidence_claim_id and not conn.execute(
                "SELECT 1 FROM claims WHERE claim_id=?", (evidence_claim_id,)
            ).fetchone():
                raise ValueError(f"Unknown evidence Claim: {evidence_claim_id}")

            existing = conn.execute(
                """SELECT relation_id,status FROM node_relations
                   WHERE from_node_id=? AND relation_type=? AND to_node_id=? AND scope=?""",
                (from_node_id, relation_type, to_node_id, scope),
            ).fetchone()
            if existing:
                relation_id = existing["relation_id"]
                if evidence_claim_id:
                    conn.execute(
                        """INSERT OR IGNORE INTO relation_evidence_links(
                           relation_id,claim_id,evidence_role,status,created_at
                           ) VALUES(?,?,'supports','active',?)""",
                        (relation_id, evidence_claim_id, now_iso()),
                    )
                elif relation_type != "part_of" and existing["status"] == "current":
                    supporting = conn.execute(
                        """SELECT 1 FROM relation_evidence_links
                           WHERE relation_id=? AND evidence_role='supports' AND status='active'
                           LIMIT 1""",
                        (relation_id,),
                    ).fetchone()
                    if not supporting:
                        raise ValueError(
                            "A current non-part_of Relation requires a supporting Claim"
                        )
                return relation_id

            if relation_type != "part_of" and requested_status == "current" and not evidence_claim_id:
                raise ValueError("A current non-part_of Relation requires a supporting Claim")

            relation_id = make_id("REL")
            created_at = now_iso()
            conn.execute(
                """INSERT INTO node_relations(
                   relation_id,from_node_id,relation_type,to_node_id,scope,valid_from,valid_to,confidence,status,evidence_claim_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (relation_id, from_node_id, relation_type, to_node_id, scope, kwargs.get("valid_from", ""),
                 kwargs.get("valid_to", ""), kwargs.get("confidence"), requested_status,
                 evidence_claim_id or None, created_at),
            )
            if evidence_claim_id:
                conn.execute(
                    """INSERT INTO relation_evidence_links(
                       relation_id,claim_id,evidence_role,status,created_at
                       ) VALUES(?,?,'supports','active',?)""",
                    (relation_id, evidence_claim_id, created_at),
                )
        return relation_id

    def seed_relations_csv(self, csv_path: Path) -> int:
        required = {"from_name", "relation_type", "to_name", "scope"}
        prepared: list[tuple[str, str, str, str]] = []
        with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Relation seed missing columns: {', '.join(sorted(missing))}")
            for row_number, row in enumerate(reader, 2):
                from_name = (row.get("from_name") or "").strip()
                relation_type = (row.get("relation_type") or "").strip()
                to_name = (row.get("to_name") or "").strip()
                scope = (row.get("scope") or "").strip()
                if not any((from_name, relation_type, to_name, scope)):
                    continue
                if not from_name or not relation_type or not to_name:
                    raise ValueError(f"Relation seed row {row_number}: from_name, relation_type and to_name are required")
                if relation_type not in RELATION_TYPES:
                    raise ValueError(f"Relation seed row {row_number}: invalid relation_type {relation_type!r}")
                if relation_type != "part_of":
                    raise ValueError(
                        f"Relation seed row {row_number}: only supports part_of; got {relation_type!r}"
                    )
                from_node = self.find_node_by_name_or_alias(from_name)
                if not from_node:
                    raise ValueError(f"Relation seed row {row_number}: Node not found: {from_name}")
                to_node = self.find_node_by_name_or_alias(to_name)
                if not to_node:
                    raise ValueError(f"Relation seed row {row_number}: Node not found: {to_name}")
                prepared.append((from_node["node_id"], relation_type, to_node["node_id"], scope))

        inserted = 0
        with self.transaction(immediate=True) as conn:
            for from_node_id, relation_type, to_node_id, scope in prepared:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO node_relations(
                       relation_id,from_node_id,relation_type,to_node_id,scope,created_at
                       ) VALUES(?,?,?,?,?,?)""",
                    (make_id("REL"), from_node_id, relation_type, to_node_id, scope, now_iso()),
                )
                inserted += cursor.rowcount
        return inserted

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
            f"""SELECT * FROM current_views WHERE node_id=? AND status='official'
                ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1""",
            (node_id,),
        )

    def versions(self, node_id: str) -> list[str]:
        return [r["version"] for r in self.all("SELECT version FROM current_views WHERE node_id=?", (node_id,))]

    def pending_proposals(self) -> list[dict[str, Any]]:
        return self.all("SELECT * FROM proposals WHERE status='pending' ORDER BY created_at")

    def pending_new_node_proposal_exists(self, name: str) -> bool:
        return bool(self.one(
            """SELECT proposal_id FROM proposals
               WHERE proposal_type='new_node' AND status='pending' AND payload_json LIKE ? LIMIT 1""",
            (f'%"canonical_name": "{name}"%',),
        ))

    def add_proposal(self, proposal_type: str, payload: dict[str, Any], target_node_id: str | None = None,
                     reason: str = "", propagation_batch_id: str = "", source_impact_id: str = "") -> str:
        if source_impact_id:
            existing = self.one(
                """SELECT proposal_id FROM proposals
                   WHERE source_impact_id=? AND status IN ('pending','accepted')""",
                (source_impact_id,),
            )
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
