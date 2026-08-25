from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


MAX_QUERY_LIMIT = 100


class ReadOnlyDatabaseError(RuntimeError):
    """The configured knowledge database cannot be queried safely."""


class ReadOnlyQuery:
    """Deterministic read model backed by a SQLite read-only connection."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn: sqlite3.Connection | None = None
        try:
            uri = f"{self.path.resolve().as_uri()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            yield conn
        except sqlite3.Error as exc:
            raise ReadOnlyDatabaseError("Knowledge database is unavailable or unreadable") from exc
        finally:
            if conn is not None:
                conn.close()

    @staticmethod
    def _validate_page(limit: int, offset: int = 0) -> None:
        if not 1 <= limit <= MAX_QUERY_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_QUERY_LIMIT}")
        if offset < 0:
            raise ValueError("offset must be non-negative")

    @staticmethod
    def _like_pattern(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return f"%{escaped}%"

    @staticmethod
    def _node_summary(row: sqlite3.Row | dict[str, Any], prefix: str = "") -> dict[str, Any]:
        return {
            "node_id": row[f"{prefix}node_id"],
            "canonical_name": row[f"{prefix}canonical_name"],
            "primary_type": row[f"{prefix}primary_type"],
        }

    @staticmethod
    def _relation(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "relation_id": row["relation_id"],
            "from_node_id": row["from_node_id"],
            "relation_type": row["relation_type"],
            "to_node_id": row["to_node_id"],
            "scope": row["scope"],
            "status": row["status"],
            "confidence": row["confidence"],
            "from_canonical_name": row["from_canonical_name"],
            "to_canonical_name": row["to_canonical_name"],
        }

    @staticmethod
    def _source_metadata(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "source_id": row["source_id"],
            "title": row["title"],
            "original_name": row["original_name"],
            "author": row["author"],
            "organization": row["organization"],
            "publication_time": row["source_publication_time"],
            "source_type": row["source_type"],
            "source_rank": row["source_rank"],
        }

    @staticmethod
    def _get_node(conn: sqlite3.Connection, node_id: str) -> sqlite3.Row | None:
        return conn.execute(
            """SELECT node_id,canonical_name,primary_type,description,status
               FROM nodes WHERE node_id=?""",
            (node_id,),
        ).fetchone()

    @staticmethod
    def _current_relations(conn: sqlite3.Connection, node_id: str) -> list[sqlite3.Row]:
        return conn.execute(
            """SELECT r.relation_id,r.from_node_id,r.relation_type,r.to_node_id,
                      r.scope,r.status,r.confidence,
                      fn.canonical_name AS from_canonical_name,
                      fn.primary_type AS from_primary_type,
                      tn.canonical_name AS to_canonical_name,
                      tn.primary_type AS to_primary_type
               FROM node_relations r
               JOIN nodes fn ON fn.node_id=r.from_node_id
               JOIN nodes tn ON tn.node_id=r.to_node_id
               WHERE r.status='current'
                 AND (r.from_node_id=? OR r.to_node_id=?)
               ORDER BY r.relation_type COLLATE NOCASE,
                        fn.canonical_name COLLATE NOCASE,
                        tn.canonical_name COLLATE NOCASE,
                        r.scope COLLATE NOCASE,r.relation_id""",
            (node_id, node_id),
        ).fetchall()

    def health(self) -> bool:
        with self.connect() as conn:
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
        return True

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT
                   (SELECT COUNT(*) FROM nodes WHERE status='active') AS active_node_count,
                   (SELECT COUNT(*) FROM node_aliases) AS alias_count,
                   (SELECT COUNT(*) FROM node_relations WHERE status='current') AS current_relation_count,
                   (SELECT COUNT(*) FROM node_relations
                    WHERE status='current' AND relation_type='part_of') AS current_part_of_count,
                   (SELECT COUNT(*) FROM sources) AS source_count,
                   (SELECT COUNT(*) FROM claims) AS claim_count,
                   (SELECT COUNT(*) FROM current_views WHERE status='official') AS current_view_count,
                   (SELECT COUNT(*) FROM knowledge_gaps
                    WHERE status IN ('open','reopened','needs_refresh')) AS open_knowledge_gap_count,
                   (SELECT COUNT(*) FROM research_questions
                    WHERE status='open') AS open_research_question_count"""
            ).fetchone()
            return dict(row)

    def search_nodes(
        self,
        query: str,
        *,
        primary_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        self._validate_page(limit)
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        pattern = self._like_pattern(query)
        with self.connect() as conn:
            rows = conn.execute(
                """WITH matches AS (
                       SELECT n.node_id,n.canonical_name,n.primary_type,
                              'canonical_name' AS matched_by,
                              n.canonical_name AS matched_text,0 AS match_order
                       FROM nodes n
                       WHERE n.status='active'
                         AND n.canonical_name LIKE ? ESCAPE '\\' COLLATE NOCASE
                         AND (? IS NULL OR n.primary_type=?)
                       UNION ALL
                       SELECT n.node_id,n.canonical_name,n.primary_type,
                              'alias' AS matched_by,a.alias AS matched_text,1 AS match_order
                       FROM node_aliases a
                       JOIN nodes n ON n.node_id=a.node_id
                       WHERE n.status='active'
                         AND a.alias LIKE ? ESCAPE '\\' COLLATE NOCASE
                         AND (? IS NULL OR n.primary_type=?)
                   ), ranked AS (
                       SELECT *,ROW_NUMBER() OVER (
                           PARTITION BY node_id
                           ORDER BY match_order,matched_text COLLATE NOCASE,matched_text
                       ) AS match_rank
                       FROM matches
                   )
                   SELECT node_id,canonical_name,primary_type,matched_by,matched_text
                   FROM ranked
                   WHERE match_rank=1
                   ORDER BY match_order,canonical_name COLLATE NOCASE,canonical_name,node_id
                   LIMIT ?""",
                (pattern, primary_type, primary_type, pattern, primary_type, primary_type, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_nodes(
        self,
        *,
        primary_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        self._validate_page(limit, offset)
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT node_id,canonical_name,primary_type
                   FROM nodes
                   WHERE status='active' AND (? IS NULL OR primary_type=?)
                   ORDER BY canonical_name COLLATE NOCASE,canonical_name,node_id
                   LIMIT ? OFFSET ?""",
                (primary_type, primary_type, limit, offset),
            ).fetchall()
            return [dict(row) for row in rows]

    def node_detail(self, node_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            node = self._get_node(conn, node_id)
            if node is None:
                return None
            aliases = [
                row["alias"]
                for row in conn.execute(
                    """SELECT alias FROM node_aliases WHERE node_id=?
                       ORDER BY alias COLLATE NOCASE,alias""",
                    (node_id,),
                ).fetchall()
            ]
            rows = self._current_relations(conn, node_id)

        incoming = [self._relation(row) for row in rows if row["to_node_id"] == node_id]
        outgoing = [self._relation(row) for row in rows if row["from_node_id"] == node_id]
        parents = {
            row["to_node_id"]: {
                "node_id": row["to_node_id"],
                "canonical_name": row["to_canonical_name"],
                "primary_type": row["to_primary_type"],
            }
            for row in rows
            if row["from_node_id"] == node_id and row["relation_type"] == "part_of"
        }
        children = {
            row["from_node_id"]: {
                "node_id": row["from_node_id"],
                "canonical_name": row["from_canonical_name"],
                "primary_type": row["from_primary_type"],
            }
            for row in rows
            if row["to_node_id"] == node_id and row["relation_type"] == "part_of"
        }
        node_result = dict(node)
        node_result.update({
            "aliases": aliases,
            "parents": sorted(parents.values(), key=lambda item: (item["canonical_name"].casefold(), item["node_id"])),
            "children": sorted(children.values(), key=lambda item: (item["canonical_name"].casefold(), item["node_id"])),
            "incoming_relations": incoming,
            "outgoing_relations": outgoing,
        })
        return node_result

    def node_neighbors(self, node_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            center = self._get_node(conn, node_id)
            if center is None:
                return None
            rows = self._current_relations(conn, node_id)

        neighbors: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row["from_node_id"] == node_id:
                neighbor = {
                    "node_id": row["to_node_id"],
                    "canonical_name": row["to_canonical_name"],
                    "primary_type": row["to_primary_type"],
                }
            else:
                neighbor = {
                    "node_id": row["from_node_id"],
                    "canonical_name": row["from_canonical_name"],
                    "primary_type": row["from_primary_type"],
                }
            neighbors[neighbor["node_id"]] = neighbor

        return {
            "center": self._node_summary(center),
            "nodes": sorted(
                neighbors.values(),
                key=lambda item: (item["canonical_name"].casefold(), item["node_id"]),
            ),
            "edges": [self._relation(row) for row in rows],
        }

    def node_claims(self, node_id: str) -> list[dict[str, Any]] | None:
        with self.connect() as conn:
            if self._get_node(conn, node_id) is None:
                return None
            rows = conn.execute(
                """SELECT c.claim_id,c.statement,c.nature,c.fact_time,c.publication_time,
                          c.status,c.confidence,c.novelty_level,c.attributed_to,c.scope,
                          c.evidence_pointer,c.evidence_excerpt,c.source_id,
                          s.title,s.original_name,s.author,s.organization,
                          s.publication_time AS source_publication_time,
                          s.source_type,s.source_rank
                   FROM claim_node_links cnl
                   JOIN claims c ON c.claim_id=cnl.claim_id
                   JOIN sources s ON s.source_id=c.source_id
                   WHERE cnl.node_id=?
                   ORDER BY COALESCE(NULLIF(c.fact_time,''),NULLIF(c.publication_time,''),
                                     c.ingestion_time,c.created_at) DESC,
                            c.publication_time DESC,c.claim_id""",
                (node_id,),
            ).fetchall()

        claims = []
        for row in rows:
            claim = {
                key: row[key]
                for key in (
                    "claim_id",
                    "statement",
                    "nature",
                    "fact_time",
                    "publication_time",
                    "status",
                    "confidence",
                    "novelty_level",
                    "attributed_to",
                    "scope",
                    "evidence_pointer",
                    "evidence_excerpt",
                    "source_id",
                )
            }
            claim["source"] = self._source_metadata(row)
            claims.append(claim)
        return claims

    def node_sources(self, node_id: str) -> list[dict[str, Any]] | None:
        with self.connect() as conn:
            if self._get_node(conn, node_id) is None:
                return None
            direct_rows = conn.execute(
                """SELECT s.source_id,s.title,s.original_name,s.author,s.organization,
                          s.publication_time AS source_publication_time,
                          s.source_type,s.source_rank,
                          snl.role,snl.link_origin,snl.evidence_excerpt
                   FROM source_node_links snl
                   JOIN sources s ON s.source_id=snl.source_id
                   WHERE snl.node_id=?
                   ORDER BY s.source_id""",
                (node_id,),
            ).fetchall()
            claim_rows = conn.execute(
                """SELECT s.source_id,s.title,s.original_name,s.author,s.organization,
                          s.publication_time AS source_publication_time,
                          s.source_type,s.source_rank,
                          cnl.role,c.claim_id,c.evidence_excerpt
                   FROM claim_node_links cnl
                   JOIN claims c ON c.claim_id=cnl.claim_id
                   JOIN sources s ON s.source_id=c.source_id
                   WHERE cnl.node_id=?
                   ORDER BY s.source_id,c.claim_id""",
                (node_id,),
            ).fetchall()

        sources: dict[str, dict[str, Any]] = {}
        provenance_keys: dict[str, set[tuple[Any, ...]]] = {}

        def add_provenance(row: sqlite3.Row, provenance: dict[str, Any]) -> None:
            source_id = row["source_id"]
            if source_id not in sources:
                sources[source_id] = {**self._source_metadata(row), "provenance": []}
                provenance_keys[source_id] = set()
            key = tuple(provenance.get(name) for name in (
                "origin_path", "role", "link_origin", "evidence_excerpt", "claim_id"
            ))
            if key not in provenance_keys[source_id]:
                provenance_keys[source_id].add(key)
                sources[source_id]["provenance"].append(provenance)

        for row in direct_rows:
            add_provenance(row, {
                "origin_path": "direct",
                "role": row["role"],
                "link_origin": row["link_origin"],
                "evidence_excerpt": row["evidence_excerpt"],
                "claim_id": None,
            })
        for row in claim_rows:
            add_provenance(row, {
                "origin_path": "claim",
                "role": row["role"],
                "link_origin": "claim",
                "evidence_excerpt": row["evidence_excerpt"],
                "claim_id": row["claim_id"],
            })

        items = list(sources.values())
        for item in items:
            item["provenance"].sort(key=lambda p: (
                0 if p["origin_path"] == "direct" else 1,
                p["claim_id"] or "",
                p["role"],
            ))
        items.sort(key=lambda item: item["source_id"])
        items.sort(key=lambda item: item["publication_time"], reverse=True)
        return items
