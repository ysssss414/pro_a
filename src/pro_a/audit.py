from __future__ import annotations

import json
from typing import Any

from .constants import NODE_PARENT_PLACEMENT_PROPOSAL_TYPE
from .db import Database


def _json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def build_source_audit(db: Database, source_id: str) -> dict[str, Any]:
    source = db.one("SELECT * FROM sources WHERE source_id=?", (source_id,))
    if not source:
        raise KeyError(source_id)
    source["metadata"] = _json(source.pop("metadata_json", "{}"), {})

    nodes = db.all(
        """SELECT n.node_id,n.canonical_name,n.primary_type,n.description,l.role,l.confidence,
                  l.link_origin,l.derived_from_node_id,l.evidence_excerpt,l.evidence_validation_json
           FROM source_node_links l JOIN nodes n ON n.node_id=l.node_id
           WHERE l.source_id=? ORDER BY CASE l.role WHEN 'primary' THEN 0 ELSE 1 END,n.canonical_name""",
        (source_id,),
    )
    for node in nodes:
        node["evidence_validation"] = _json(node.pop("evidence_validation_json", "{}"), {})
        node["aliases"] = [
            row["alias"] for row in db.all(
                "SELECT alias FROM node_aliases WHERE node_id=? ORDER BY alias", (node["node_id"],)
            )
        ]

    claims = db.all(
        "SELECT * FROM claims WHERE source_id=? ORDER BY created_at,claim_id", (source_id,)
    )
    for claim in claims:
        structured = _json(claim.pop("structured_json", "{}"), {})
        validation = structured.get("validation") or {}
        claim["structured"] = structured
        claim["validation"] = validation
        claim["evidence_validated"] = bool(validation.get("evidence_validated"))
        claim["related_nodes"] = db.all(
            """SELECT n.node_id,n.canonical_name,n.primary_type,l.role
               FROM claim_node_links l JOIN nodes n ON n.node_id=l.node_id
               WHERE l.claim_id=? ORDER BY n.canonical_name""",
            (claim["claim_id"],),
        )

    claim_ids = {claim["claim_id"] for claim in claims}
    claim_relations: list[dict[str, Any]] = []
    if claim_ids:
        placeholders = ",".join("?" for _ in claim_ids)
        params = [*claim_ids, *claim_ids]
        claim_relations = db.all(
            f"""SELECT r.*,fc.statement AS from_statement,tc.statement AS to_statement
                FROM claim_relations r
                JOIN claims fc ON fc.claim_id=r.from_claim_id
                JOIN claims tc ON tc.claim_id=r.to_claim_id
                WHERE r.from_claim_id IN ({placeholders}) OR r.to_claim_id IN ({placeholders})
                ORDER BY r.created_at,r.relation_id""",
            params,
        )

    jobs = db.all(
        "SELECT * FROM processing_jobs WHERE source_id=? ORDER BY started_at,job_id", (source_id,)
    )
    job_ids = {job["job_id"] for job in jobs}

    impact_reviews = []
    for impact in db.all("SELECT * FROM impact_reviews ORDER BY created_at,impact_id"):
        context = _json(impact.get("payload_json"), {})
        recorded = _json(impact.get("reason"), {})
        if isinstance(recorded, dict) and "result" in recorded:
            result = recorded.get("result") or {}
            context = recorded.get("context") or context
        else:
            result = {}
        if impact.get("trigger_id") != source_id and context.get("trigger_source_id") != source_id:
            continue
        impact["context"] = context
        impact["result"] = result
        impact.pop("payload_json", None)
        impact_reviews.append(impact)
    impact_ids = {impact["impact_id"] for impact in impact_reviews}

    proposal_inventory = []
    related_proposals = []
    for proposal in db.all("SELECT * FROM proposals ORDER BY created_at,proposal_id"):
        payload = _json(proposal.pop("payload_json", "{}"), {})
        proposal["payload"] = payload
        proposal_inventory.append(proposal)
        related_claims: set[str] = set()
        for key in ("related_claim_ids", "evidence_claim_ids", "supporting_claim_ids"):
            related_claims.update(payload.get(key) or [])
        related = (
            payload.get("source_id") == source_id
            or payload.get("trigger_source_id") == source_id
            or proposal.get("source_impact_id") in impact_ids
            or proposal.get("propagation_batch_id") in job_ids
            or bool(claim_ids & related_claims)
        )
        if related:
            related_proposals.append(proposal)
    related_new_node_ids = {
        proposal["proposal_id"] for proposal in related_proposals
        if proposal["proposal_type"] == "new_node"
    }
    related_ids = {proposal["proposal_id"] for proposal in related_proposals}
    related_proposals.extend(
        proposal for proposal in proposal_inventory
        if proposal["proposal_id"] not in related_ids
        and proposal["proposal_type"] == NODE_PARENT_PLACEMENT_PROPOSAL_TYPE
        and proposal["payload"].get("origin_new_node_proposal_id") in related_new_node_ids
    )
    related_proposals.sort(key=lambda item: (item["created_at"], item["proposal_id"]))

    current_view_proposals = [
        proposal for proposal in related_proposals
        if proposal["proposal_type"] == "current_view_change"
    ]
    relation_proposals = [
        proposal for proposal in related_proposals
        if proposal["proposal_type"] == "node_relation"
    ]
    parent_placement_proposals = [
        proposal for proposal in related_proposals
        if proposal["proposal_type"] == NODE_PARENT_PLACEMENT_PROPOSAL_TYPE
    ]
    research_question_candidates = [
        proposal for proposal in related_proposals
        if proposal["proposal_type"] == "new_node"
        and (
            proposal["payload"].get("candidate_kind") == "research_question"
            or proposal["payload"].get("primary_type") == "ResearchQuestion"
        )
    ]
    rq_ids = {proposal["proposal_id"] for proposal in research_question_candidates}
    node_proposals = [
        proposal for proposal in related_proposals
        if proposal["proposal_type"] == "new_node" and proposal["proposal_id"] not in rq_ids
    ]

    knowledge_gaps = []
    for gap in db.all("SELECT * FROM knowledge_gaps ORDER BY created_at,gap_id"):
        source_claim_ids = _json(gap.pop("source_claim_ids_json", "[]"), [])
        if claim_ids & set(source_claim_ids):
            gap["source_claim_ids"] = source_claim_ids
            knowledge_gaps.append(gap)

    return {
        "source": source,
        "nodes": nodes,
        "claims": claims,
        "claim_relations": claim_relations,
        "impact_reviews": impact_reviews,
        "node_proposals": node_proposals,
        "parent_placement_proposals": parent_placement_proposals,
        "relation_proposals": relation_proposals,
        "relation_candidates": (
            (source.get("metadata") or {}).get("analysis_quality") or {}
        ).get("relation_candidates") or [],
        "rejected_relation_candidates": (
            (source.get("metadata") or {}).get("analysis_quality") or {}
        ).get("rejected_relation_candidates") or [],
        "current_view_proposals": current_view_proposals,
        "knowledge_gaps": knowledge_gaps,
        "research_question_candidates": research_question_candidates,
        "source_relations": db.all(
            """SELECT * FROM source_relations
               WHERE from_source_id=? OR to_source_id=? ORDER BY created_at,relation_id""",
            (source_id, source_id),
        ),
        "processing_jobs": jobs,
    }
