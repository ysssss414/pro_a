"""Private operator routing metadata for company material processing."""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

from pro_a.production_promotion import canonical_sha256
from pro_a.research_explorer import ResearchExplorer


CONTRACT_VERSION = "company-material-intent-v1"
MATERIAL_KINDS = (
    "earnings_report", "exchange_filing", "company_announcement",
    "investor_presentation", "investor_qa", "research_report",
    "community_material", "other",
)
SOURCE_CHANNELS = (
    "company_official", "exchange_official", "broker_research", "media",
    "knowledge_community", "user_upload", "other",
)
TRUST_POLICIES = {
    "company_official": "PRIMARY_OFFICIAL",
    "exchange_official": "PRIMARY_OFFICIAL",
    "broker_research": "SECONDARY_RESEARCH",
    "media": "SECONDARY_MEDIA",
    "knowledge_community": "LOW_TRUST_CLUE_ONLY",
    "user_upload": "UNCLASSIFIED",
    "other": "UNCLASSIFIED",
}
FIELDS = frozenset(("target_company_node_id", "material_kind", "source_channel",
                    "material_date", "operator_title"))


class CompanyMaterialError(RuntimeError):
    def __init__(self, code: str, status: int = 422):
        super().__init__(code)
        self.status = status


def company(config: Any, node_id: str) -> dict[str, str]:
    with ResearchExplorer(config).connect() as connection:
        row = connection.execute(
            "SELECT node_id,canonical_name,primary_type,status FROM nodes WHERE node_id=?",
            (node_id,),
        ).fetchone()
    if row is None:
        raise CompanyMaterialError("COMPANY_MATERIAL_TARGET_NOT_FOUND", 404)
    if row["primary_type"] != "Company" or row["status"] != "active":
        raise CompanyMaterialError("COMPANY_MATERIAL_TARGET_NOT_COMPANY")
    return {"node_id": row["node_id"], "canonical_name": row["canonical_name"],
            "primary_type": row["primary_type"], "status": row["status"]}


def validate(config: Any, value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != FIELDS:
        raise CompanyMaterialError("COMPANY_MATERIAL_INTENT_INVALID")
    node_id, kind, channel = (value[key] for key in
                              ("target_company_node_id", "material_kind", "source_channel"))
    if not isinstance(node_id, str) or not node_id or len(node_id) > 200:
        raise CompanyMaterialError("COMPANY_MATERIAL_TARGET_INVALID")
    target = company(config, node_id)
    if kind not in MATERIAL_KINDS or channel not in SOURCE_CHANNELS:
        raise CompanyMaterialError("COMPANY_MATERIAL_INTENT_INVALID")
    material_date = value["material_date"]
    if material_date == "":
        material_date = None
    if material_date is not None:
        if not isinstance(material_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", material_date):
            raise CompanyMaterialError("COMPANY_MATERIAL_DATE_INVALID")
        try:
            date.fromisoformat(material_date)
        except ValueError:
            raise CompanyMaterialError("COMPANY_MATERIAL_DATE_INVALID") from None
    title = value["operator_title"]
    if title == "":
        title = None
    if title is not None and (not isinstance(title, str) or not 1 <= len(title) <= 240
                              or title != title.strip() or any(ord(c) < 32 or ord(c) == 127 for c in title)
                              or re.match(r"^(?:[A-Za-z]:[\\/]|\\\\|file://)", title, re.IGNORECASE)):
        raise CompanyMaterialError("COMPANY_MATERIAL_TITLE_INVALID")
    normalized = {"target_company_node_id": target["node_id"],
                  "material_kind": kind, "source_channel": channel,
                  "material_date": material_date, "operator_title": title}
    return {**normalized, "target_company_name": target["canonical_name"],
            "material_trust_policy": TRUST_POLICIES[channel],
            "material_date_basis": "operator_supplied" if material_date else None,
            "intent_sha256": canonical_sha256(normalized)}


def read_bound(connection: Any, run_id: str) -> dict[str, Any] | None:
    rows = list(connection.execute(
        "SELECT event_json FROM source_processing_events WHERE processing_run_id=? "
        "AND event_type='COMPANY_MATERIAL_INTENT_BOUND' ORDER BY sequence", (run_id,),
    ))
    if not rows:
        return None
    if len(rows) != 1:
        raise CompanyMaterialError("COMPANY_MATERIAL_INTENT_DRIFT")
    import json
    event = json.loads(rows[0][0])
    normalized = {key: event[key] for key in FIELDS}
    if canonical_sha256(normalized) != event.get("intent_sha256"):
        raise CompanyMaterialError("COMPANY_MATERIAL_INTENT_DRIFT")
    return event
