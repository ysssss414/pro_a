"""Read-only company material timeline over private intent and canonical links."""
from __future__ import annotations

import json
import unicodedata
from typing import Any

from pro_a.company_material_intent import CompanyMaterialError, company, read_bound
from pro_a.production_promotion import canonical_sha256
from pro_a.query import ReadOnlyQuery
from pro_a.research_explorer import ResearchExplorer
from pro_a.workbench.store import Store


TIMELINE_VERSION = "company-material-timeline-v1"


def _lifecycle(state: str) -> str:
    if state == "ACTIVATED":
        return "activated"
    if state == "QUALIFIED":
        return "qualified_unapplied"
    if state in ("ATTRIBUTION_REQUIRED", "ATTRIBUTION_COMPLETE", "REVIEW_COMPLETE"):
        return "attribution_required"
    if state == "HUMAN_REVIEW_REQUIRED":
        return "human_review"
    if state in ("FAILED", "BLOCKED", "RECOVERY_REQUIRED"):
        return state.lower()
    return "processing" if state != "REGISTERED" else "uploaded"


def _sort_key(row: dict[str, Any]) -> tuple:
    # DESC for dates, then a stable ascending Source ID. ISO 8601 sorts lexically.
    def descend(value: str | None) -> tuple[int, tuple[int, ...]]:
        return (0 if value else 1, tuple(-ord(char) for char in value or ""))
    return (descend(row["material_date"]), descend(row["publication_time"]),
            descend(row["ingested_at"]), descend(row["uploaded_at"]), row["source_id"])


class CompanyMaterials:
    def __init__(self, config: Any):
        self.config = config

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        query = query.strip()
        if not query or not 1 <= limit <= 50:
            raise CompanyMaterialError("INVALID_FILTER")
        needle = unicodedata.normalize("NFKC", query).casefold()
        with ResearchExplorer(self.config).connect() as connection:
            rows = connection.execute('''SELECT n.node_id,n.canonical_name,n.primary_type,n.status
                FROM nodes n LEFT JOIN node_aliases a ON a.node_id=n.node_id
                WHERE n.primary_type='Company' AND n.status='active'
                  AND (instr(nfkc_casefold(n.canonical_name),?)>0
                       OR instr(nfkc_casefold(COALESCE(a.alias,'')),?)>0)
                GROUP BY n.node_id,n.canonical_name,n.primary_type,n.status
                ORDER BY CASE WHEN nfkc_casefold(n.canonical_name)=? THEN 0 ELSE 1 END,
                         nfkc_casefold(n.canonical_name),n.node_id LIMIT ?''',
                (needle, needle, needle, limit)).fetchall()
        return {"items": [dict(row) for row in rows]}

    def timeline(self, node_id: str, *, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
        target = company(self.config, node_id)
        if not 1 <= limit <= 100 or (cursor not in (None, "") and
                                      (not cursor.isascii() or not cursor.isdigit())):
            raise CompanyMaterialError("INVALID_CURSOR")
        offset = int(cursor or 0)
        if offset > 10_000_000:
            raise CompanyMaterialError("INVALID_CURSOR")
        private: dict[str, dict[str, Any]] = {}
        with Store(self.config).connect() as connection:
            rows = connection.execute('''SELECT r.*,s.safe_filename,s.uploaded_at,s.canonical_source_id,
                d.status review_status,a.artifact_id attribution_artifact_id,
                p.artifact_id qualification_artifact_id,x.artifact_id activation_artifact_id
                FROM source_processing_runs r
                JOIN private_sources s ON s.source_id=r.source_id
                JOIN source_processing_events e ON e.processing_run_id=r.processing_run_id
                    AND e.event_type='COMPANY_MATERIAL_INTENT_BOUND'
                LEFT JOIN review_drafts d ON d.artifact_id=r.packet_artifact_id
                LEFT JOIN attribution_objects a ON a.artifact_id=r.packet_artifact_id
                LEFT JOIN operational_packages p ON p.artifact_id=r.packet_artifact_id
                LEFT JOIN operational_receipts x ON x.artifact_id=r.packet_artifact_id
                WHERE json_extract(e.event_json,'$.target_company_node_id')=?
                ORDER BY r.created_at DESC,r.processing_run_id DESC''', (node_id,)).fetchall()
            for row in rows:
                source_id = row["source_id"]
                if source_id in private:
                    continue
                intent = read_bound(connection, row["processing_run_id"])
                if intent is None:
                    continue
                state = ("ACTIVATED" if row["activation_artifact_id"] else
                         "QUALIFIED" if row["qualification_artifact_id"] else
                         "ATTRIBUTION_COMPLETE" if row["attribution_artifact_id"] else
                         "ATTRIBUTION_REQUIRED" if row["review_status"] == "SEALED" else row["state"])
                private[source_id] = {
                    "material_id": f"company-material:{node_id}:{source_id}",
                    "source_id": source_id, "processing_run_id": row["processing_run_id"],
                    "title": intent["operator_title"] or row["safe_filename"],
                    "title_basis": "operator_title" if intent["operator_title"] else "safe_filename",
                    "material_kind": intent["material_kind"],
                    "source_channel": intent["source_channel"],
                    "material_trust_policy": intent["material_trust_policy"],
                    "material_date": intent["material_date"],
                    "material_date_basis": intent["material_date_basis"],
                    "lifecycle": _lifecycle(state), "state": state,
                    "private": True, "canonical": False,
                    "association_basis": "company_material_intent",
                    "review_status": row["review_status"],
                    "attribution_status": "SEALED" if row["attribution_artifact_id"] else
                                          "DRAFT" if row["review_status"] == "SEALED" else None,
                    "qualification_status": "QUALIFIED" if row["qualification_artifact_id"] else None,
                    "canonical_source_id": None, "claim_count": None,
                    "linked_node_count": None, "linked_nodes": None,
                    "current_view_impact_candidate_count": None,
                    "uploaded_at": row["uploaded_at"], "publication_time": None,
                    "ingested_at": None, "updated_at": row["updated_at"],
                    "packet_artifact_id": row["packet_artifact_id"],
                    "company_material_intent_sha256": intent["intent_sha256"],
                }
        production_source_ids: set[str] = set()
        with ResearchExplorer(self.config).connect() as connection:
            source_rows = connection.execute('''SELECT DISTINCT s.source_id,s.title,s.publication_time,
                s.ingested_at,s.source_type,s.source_rank,s.status
                FROM sources s WHERE
                EXISTS(SELECT 1 FROM source_node_links sl
                       WHERE sl.source_id=s.source_id AND sl.node_id=?) OR
                EXISTS(SELECT 1 FROM claims c JOIN claim_node_links cl ON cl.claim_id=c.claim_id
                       WHERE c.source_id=s.source_id AND cl.node_id=?)
                ORDER BY s.source_id''', (node_id, node_id)).fetchall()
            for source in source_rows:
                source_id = source["source_id"]
                row = private.get(source_id)
                source_basis = connection.execute(
                    "SELECT 1 FROM source_node_links WHERE source_id=? AND node_id=? LIMIT 1",
                    (source_id, node_id),
                ).fetchone() is not None
                claim_basis = connection.execute('''SELECT 1 FROM claims c
                    JOIN claim_node_links cl ON cl.claim_id=c.claim_id
                    WHERE c.source_id=? AND cl.node_id=? LIMIT 1''',
                    (source_id, node_id)).fetchone() is not None
                basis = ("source_node_link+claim_node_link" if source_basis and claim_basis else
                         "source_node_link" if source_basis else "claim_node_link")
                links = [dict(item) for item in connection.execute('''SELECT n.node_id,n.canonical_name,
                    n.primary_type,GROUP_CONCAT(DISTINCT l.role) roles
                    FROM nodes n JOIN (
                      SELECT sl.node_id,sl.role FROM source_node_links sl WHERE sl.source_id=?
                      UNION ALL
                      SELECT cl.node_id,cl.role FROM claims c
                      JOIN claim_node_links cl ON cl.claim_id=c.claim_id WHERE c.source_id=?
                    ) l ON l.node_id=n.node_id
                    GROUP BY n.node_id,n.canonical_name,n.primary_type
                    ORDER BY n.canonical_name COLLATE NOCASE,n.node_id LIMIT 10''',
                    (source_id, source_id))]
                link_count = connection.execute('''SELECT COUNT(DISTINCT node_id) FROM (
                    SELECT node_id FROM source_node_links WHERE source_id=?
                    UNION SELECT cl.node_id FROM claims c JOIN claim_node_links cl
                        ON cl.claim_id=c.claim_id WHERE c.source_id=?)''',
                    (source_id, source_id)).fetchone()[0]
                claim_count = connection.execute(
                    "SELECT COUNT(*) FROM claims WHERE source_id=?", (source_id,),
                ).fetchone()[0]
                if row is None:
                    row = {"material_id": f"canonical-material:{node_id}:{source_id}",
                           "source_id": source_id, "processing_run_id": None,
                           "material_kind": None, "source_channel": None,
                           "material_trust_policy": None, "material_date": None,
                           "material_date_basis": None, "private": False,
                           "review_status": None, "attribution_status": None,
                           "qualification_status": None, "uploaded_at": None,
                           "packet_artifact_id": None,
                           "company_material_intent_sha256": None}
                    private[source_id] = row
                row.update({"title": source["title"], "title_basis": "canonical_source",
                            "lifecycle": "activated", "state": "ACTIVATED", "canonical": True,
                            "association_basis": basis, "canonical_source_id": source_id,
                            "claim_count": claim_count, "linked_node_count": link_count,
                            "linked_nodes": links, "publication_time": source["publication_time"],
                            "ingested_at": source["ingested_at"],
                            "updated_at": row.get("updated_at") or source["ingested_at"]})
            for source_id in private:
                if connection.execute("SELECT 1 FROM sources WHERE source_id=?", (source_id,)).fetchone():
                    production_source_ids.add(source_id)
        query = ReadOnlyQuery(self.config.knowledge_db)
        for row in private.values():
            if row["canonical"]:
                impact = query.source_impact_candidates(row["source_id"])
                row["current_view_impact_candidate_count"] = len(impact["candidates"]) if impact else None
        materials = sorted((row for row in private.values()
                            if row["canonical"] or (row["state"] != "ACTIVATED" and
                                                     row["source_id"] not in production_source_ids)), key=_sort_key)
        structural = {"contract_version": TIMELINE_VERSION, "company": target,
                      "materials": materials, "counts": {"total": len(materials),
                      "private": sum(not item["canonical"] for item in materials),
                      "canonical": sum(item["canonical"] for item in materials)}}
        return {**structural, "materials": materials[offset:offset + limit],
                "limit": limit, "next_cursor": str(offset + limit) if offset + limit < len(materials) else None,
                "snapshot_id": canonical_sha256(structural)}
