from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import AppConfig


def write_receipt(cfg: AppConfig, job_id: str, data: dict[str, Any]) -> Path:
    path = cfg.root / "generated" / "receipts" / f"{job_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Ingestion Receipt — {job_id}", ""]
    for key in ["status", "mode", "source_id", "title", "source_type", "archived_path", "ima_status"]:
        if key in data:
            lines.append(f"- **{key}**: {data.get(key)}")
    if data.get("parse_diagnostics") is not None:
        lines += ["", "## Source Format / Parse Quality", "",
                  f"- parse_diagnostics: `{json.dumps(data['parse_diagnostics'], ensure_ascii=False)}`"]
        lines += [f"- {warning}" for warning in data.get("parse_warnings", [])]
    audit = data.get("audit") or {}
    source = audit.get("source") or {}
    nodes = audit.get("nodes") or []
    node_proposals = audit.get("node_proposals") or []
    relation_candidates = audit.get("relation_candidates") or []
    relation_proposals = audit.get("relation_proposals") or []
    rejected_relation_candidates = audit.get("rejected_relation_candidates") or []
    claims = audit.get("claims") or []
    claim_relations = audit.get("claim_relations") or []
    impacts = audit.get("impact_reviews") or []
    cv_proposals = audit.get("current_view_proposals") or []
    gaps = audit.get("knowledge_gaps") or []
    rq_candidates = audit.get("research_question_candidates") or []
    analysis_quality = (source.get("metadata") or {}).get("analysis_quality") or {}
    rejected_matches = analysis_quality.get("rejected_node_matches") or []
    rejected_candidates = analysis_quality.get("rejected_node_candidates") or []
    rejected_claim_links = analysis_quality.get("rejected_claim_node_links") or []
    lines += [
        "", "## 处理结果", "",
        f"- Existing Nodes matched: {len(nodes)}",
        f"- Candidate Node Proposals: {len(node_proposals)}",
        f"- Relation Candidates: accepted {len(relation_candidates)}, rejected {len(rejected_relation_candidates)}",
        f"- Relation Proposals: {len(relation_proposals)}",
        f"- Claims created: {len(claims)}",
        f"- Historical comparisons: {len(claim_relations)}",
        f"- Impact Reviews: {len(impacts)}",
        f"- Current View Proposals: {len(cv_proposals)}",
        f"- Knowledge Gaps: {len(gaps)}",
        f"- Research Question Candidates: {len(rq_candidates)}", "",
        f"- Rejected unsupported Node Matches: {len(rejected_matches)}",
        f"- Rejected unsupported Claim-Node Links: {len(rejected_claim_links)}",
        f"- Rejected low-quality Node Candidates: {len(rejected_candidates)}", "",
        "## Source Metadata", "",
        f"- Source ID: `{source.get('source_id', data.get('source_id', ''))}`",
        f"- Title: {source.get('title', data.get('title', ''))}",
        f"- Type / Rank / Origin: {source.get('source_type', '')} / {source.get('source_rank', '')} / {source.get('origin_type', '')}",
        f"- Author / Organization: {source.get('author', '')} / {source.get('organization', '')}",
        f"- Publication / Ingestion: {source.get('publication_time', '')} / {source.get('ingested_at', '')}",
        f"- Analysis mode / Status: {source.get('analysis_mode', '')} / {source.get('status', '')}",
        f"- Metadata: `{json.dumps(source.get('metadata') or {}, ensure_ascii=False)}`", "",
        "## Existing Nodes", "",
    ]
    lines += [
        f"- `{node['node_id']}` {node['canonical_name']} ({node['primary_type']}) — role={node['role']}, "
        f"origin={node.get('link_origin', '')}, confidence={node.get('confidence')}, "
        f"evidence_validated={node.get('evidence_validation', {}).get('evidence_validated', False)}"
        for node in nodes
    ] or ["- None"]
    lines += ["", "## Candidate Node Proposals", ""]
    lines += [
        f"- `{proposal['proposal_id']}` {proposal['payload'].get('canonical_name', '')} "
        f"({proposal['payload'].get('primary_type', '')}) — status={proposal['status']}, "
        f"confidence={proposal['payload'].get('confidence')}, "
        f"related_claims={len(proposal['payload'].get('related_claim_ids') or [])}"
        for proposal in node_proposals
    ] or ["- None"]
    lines += ["", "## Relation Proposals", ""]
    lines += [
        f"- `{proposal['proposal_id']}` `{proposal['payload'].get('from_node_id', '')}` "
        f"--{proposal['payload'].get('relation_type', '')}--> "
        f"`{proposal['payload'].get('to_node_id', '')}` — status={proposal['status']}, "
        f"supporting_claims={len(proposal['payload'].get('supporting_claim_ids') or [])}"
        for proposal in relation_proposals
    ] or ["- None"]
    lines += ["", "## Rejected Relation Candidates", ""]
    lines += [
        f"- stage={item.get('stage', '')}, reason={item.get('reason', '')}, "
        f"candidate=`{json.dumps(item.get('candidate'), ensure_ascii=False)}`"
        for item in rejected_relation_candidates
    ] or ["- None"]
    lines += ["", "## Claims", ""]
    lines += [
        f"- `{claim['claim_id']}` [{claim['nature']} / {claim['status']} / {claim['novelty_level']}] "
        f"confidence={claim.get('confidence')}, attributed_to={claim.get('attributed_to', '')}, "
        f"evidence_validated={claim.get('evidence_validated')} — {claim['statement']}"
        for claim in claims
    ] or ["- None"]
    lines += ["", "## Historical Compare", ""]
    lines += [
        f"- `{relation['from_claim_id']}` {relation['relation_type']} `{relation['to_claim_id']}` — {relation.get('reason', '')}"
        for relation in claim_relations
    ] or ["- None"]
    lines += ["", "## Impact Reviews", ""]
    lines += [
        f"- `{impact['impact_id']}` node=`{impact['node_id']}` status={impact['status']} "
        f"change_level={impact.get('result_change_level') or impact.get('result', {}).get('change_level', '')} "
        f"proposal=`{impact.get('proposal_id') or ''}` — {impact.get('result', {}).get('reason', '')}"
        for impact in impacts
    ] or ["- None"]
    lines += ["", "## Current View Proposals", ""]
    lines += [
        f"- `{proposal['proposal_id']}` node=`{proposal.get('target_node_id') or ''}` "
        f"level={proposal['payload'].get('change_level', '')} status={proposal['status']}"
        for proposal in cv_proposals
    ] or ["- None"]
    lines += ["", "## Knowledge Gaps", ""]
    lines += [
        f"- `{gap['gap_id']}` {gap['title']} — status={gap['status']}"
        for gap in gaps
    ] or ["- None"]
    lines += ["", "## Research Question Candidates", ""]
    lines += [
        f"- `{proposal['proposal_id']}` {proposal['payload'].get('question') or proposal['payload'].get('canonical_name', '')} "
        f"— status={proposal['status']}"
        for proposal in rq_candidates
    ] or ["- None"]
    lines.append("")
    if data.get("warnings"):
        lines += ["## Warnings", *[f"- {x}" for x in data["warnings"]], ""]
    if data.get("node_proposals") or data.get("relation_proposals") or data.get("current_view_proposals"):
        lines += ["## 需要确认", ""]
        for p in [
            *data.get("node_proposals", []),
            *data.get("relation_proposals", []),
            *data.get("current_view_proposals", []),
        ]:
            lines.append(f"- `{p}`")
        lines.append("")
    lines += ["## JSON", "```json", json.dumps(data, ensure_ascii=False, indent=2, default=str), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_proposal(cfg: AppConfig, proposal: dict[str, Any]) -> Path:
    proposal_id = proposal["proposal_id"]
    path = cfg.root / "review" / "proposals" / f"{proposal_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = proposal.get("payload")
    if payload is None:
        raw = proposal.get("payload_json", "{}")
        payload = json.loads(raw)
    lines = [
        f"# Proposal — {proposal_id}", "",
        f"- type: {proposal.get('proposal_type')}",
        f"- status: {proposal.get('status')}",
        f"- target_node_id: {proposal.get('target_node_id') or ''}",
        f"- reason: {proposal.get('reason') or ''}",
        f"- propagation_batch_id: {proposal.get('propagation_batch_id') or ''}",
        "", "```json", json.dumps(payload, ensure_ascii=False, indent=2), "```", "",
        "CLI:", f"- 接受：`pro-a proposals accept {proposal_id}`",
        f"- 拒绝：`pro-a proposals reject {proposal_id} --reason \"...\"`", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
