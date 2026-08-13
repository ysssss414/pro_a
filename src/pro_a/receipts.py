from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import AppConfig


def write_receipt(cfg: AppConfig, job_id: str, data: dict[str, Any]) -> Path:
    path = cfg.root / "generated" / "receipts" / f"{job_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Ingestion Receipt — {job_id}", ""]
    for key in ["status", "mode", "source_id", "title", "archived_path", "ima_status"]:
        if key in data:
            lines.append(f"- **{key}**: {data.get(key)}")
    lines += ["", "## 处理结果", "", f"- Nodes matched: {len(data.get('node_matches', []))}",
              f"- New Node proposals: {len(data.get('node_proposals', []))}",
              f"- Claims created: {len(data.get('claims', []))}",
              f"- Current View proposals: {len(data.get('current_view_proposals', []))}",
              f"- Knowledge Gaps: {len(data.get('knowledge_gaps', []))}", ""]
    if data.get("warnings"):
        lines += ["## Warnings", *[f"- {x}" for x in data["warnings"]], ""]
    if data.get("node_proposals") or data.get("current_view_proposals"):
        lines += ["## 需要确认", ""]
        for p in [*data.get("node_proposals", []), *data.get("current_view_proposals", [])]:
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
