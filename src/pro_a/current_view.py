from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig
from .db import CURRENT_VIEW_ORDER, Database, now_iso
from .ids import make_id


def _bullets(items: list[Any]) -> str:
    if not items:
        return "- 暂无"
    return "\n".join(
        f"- {json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, dict) else item}"
        for item in items
    )


def render_current_view(node: dict[str, Any], version: str, data: dict[str, Any], change_level: str,
                        previous_version: str = "") -> str:
    lines = [
        "---",
        f"node_id: {node['node_id']}",
        f"node_name: {node['canonical_name']}",
        f"node_type: {node['primary_type']}",
        f"version: {version}",
        f"change_level: {change_level}",
        f"previous_version: {previous_version}",
        "document_type: current_view",
        "---",
        "",
        f"# {node['canonical_name']} — Current View {version}",
        "",
        "## 一句话结论",
        data.get("one_line_conclusion") or "暂无明确结论",
        "",
        "## 核心逻辑",
        _bullets(data.get("core_logic") or []),
        "",
        "## 关键事实",
        _bullets(data.get("key_facts") or []),
        "",
        "## 核心分歧",
        _bullets(data.get("core_disagreements") or []),
        "",
        "## 待验证假设",
        _bullets(data.get("assumptions_to_verify") or []),
        "",
        "## 投资含义",
        data.get("investment_implication") or "暂无",
        "",
        "## 主要风险",
        _bullets(data.get("major_risks") or []),
        "",
        "## Knowledge Gaps",
        _bullets(data.get("knowledge_gaps") or []),
        "",
        "## Key Watch Items",
        _bullets(data.get("key_watch_items") or []),
        "",
        "## 最近变化",
        (data.get("recent_change") or ("首次建立" if change_level == "initial" else "暂无")),
        "",
    ]
    type_specific = data.get("type_specific") or {}
    if type_specific:
        lines += ["## Type-specific", ""]
        for k, v in type_specific.items():
            lines.append(f"### {k}")
            if isinstance(v, list):
                lines.append(_bullets(v))
            elif isinstance(v, dict):
                lines.append("```json")
                lines.append(json.dumps(v, ensure_ascii=False, indent=2))
                lines.append("```")
            else:
                lines.append(str(v))
            lines.append("")
    evidence = data.get("evidence_claim_ids") or []
    lines += ["## Evidence", _bullets(evidence), ""]
    return "\n".join(lines)


def create_official_view_record(conn, cfg: AppConfig, node_id: str, data: dict[str, Any], change_level: str,
                                trigger_source_id: str = "", trigger_claim_ids: list[str] | None = None,
                                accepted_proposal_id: str = "") -> dict[str, Any]:
    node_row = conn.execute("SELECT * FROM nodes WHERE node_id=?", (node_id,)).fetchone()
    node = dict(node_row) if node_row else None
    if not node:
        raise KeyError(f"Unknown node: {node_id}")
    previous_row = conn.execute(
        f"""SELECT * FROM current_views WHERE node_id=? AND status='official'
            ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1""",
        (node_id,),
    ).fetchone()
    previous = dict(previous_row) if previous_row else None
    revision_date = datetime.now().strftime("%Y%m%d")
    seq_row = conn.execute(
        "SELECT MAX(revision_seq) AS seq FROM current_views WHERE node_id=? AND revision_date=?",
        (node_id, revision_date),
    ).fetchone()
    revision_seq = (seq_row["seq"] + 1) if seq_row and seq_row["seq"] is not None else 0
    version = f"v_{revision_date}" if revision_seq == 0 else f"v_{revision_date}_{revision_seq:02d}"
    previous_version = previous["version"] if previous else ""
    content_md = render_current_view(node, version, data, change_level, previous_version)
    view_id = make_id("VIEW")
    ts = now_iso()
    conn.execute(
        """INSERT INTO current_views(view_id,node_id,version,status,change_level,previous_view_id,content_md,content_json,
           trigger_source_id,trigger_claim_ids_json,revision_date,revision_seq,accepted_proposal_id,created_at,confirmed_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (view_id, node_id, version, "official", change_level, previous["view_id"] if previous else None,
         content_md, json.dumps(data, ensure_ascii=False), trigger_source_id,
         json.dumps(trigger_claim_ids or [], ensure_ascii=False), revision_date, revision_seq, accepted_proposal_id, ts, ts),
    )
    out_dir = cfg.root / "generated" / "current_views" / node_id
    path = out_dir / f"Current_View_{version}.md"
    return {"view_id": view_id, "node_id": node_id, "version": version, "path": path, "content_md": content_md,
            "previous_view": previous}


def write_official_view_file(view: dict[str, Any]) -> Path:
    path = Path(view["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(view["content_md"], encoding="utf-8")
    return path


def create_official_view(db: Database, cfg: AppConfig, node_id: str, data: dict[str, Any], change_level: str,
                         trigger_source_id: str = "", trigger_claim_ids: list[str] | None = None) -> dict[str, Any]:
    with db.transaction(immediate=True) as conn:
        view = create_official_view_record(
            conn, cfg, node_id, data, change_level, trigger_source_id, trigger_claim_ids,
        )
    write_official_view_file(view)
    return view
