"""Activate the two human-approved Phase 2.4B Current Views.

This is intentionally a finite activation script: it contains only the two
payloads approved in the Phase 2.4B handoff and delegates persistence to the
existing proposal/confirmation/apply contract.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from pro_a.config import load_config
from pro_a.current_view_pilot import file_sha256
from pro_a.db import Database
from pro_a.proposals import ProposalManager
from pro_a.analyzer import Analyzer

MLCC_NODE_ID = "NODE_20260817_DABE52FE"
YUNZHONG_NODE_ID = "NODE_20260826_BC260F3E"
MLCC_NAME = "MLCC"
YUNZHONG_NAME = "昀冢科技"
MLCC_PRIMARY = [
    "CLM_20260814_980FA010",
    "CLM_20260814_BAED6789",
    "CLM_20260814_D2C7FCD1",
]
YUNZHONG_PRIMARY = [
    "CLM_20260814_541F5C31",
    "CLM_20260814_8E4B9E25",
    "CLM_20260814_939CAEDD",
    "CLM_20260814_9A069D06",
    "CLM_20260814_BA7AC415",
    "CLM_20260814_E1A48290",
]
YUNZHONG_UNRESOLVED = ["CLM_20260814_0B6E52F8", "CLM_20260814_E53B8E9C"]


def approved_payloads() -> dict[str, dict]:
    mlcc = {
        "one_line_conclusion": "据现有财通证券业绩会更新材料，2026年7月和8月MLCC单月价格环比均上涨30%以上；关于本轮周期持续时间更长及AI需求形成挤出效应，目前仅有该材料中的分析判断，尚缺独立证据交叉验证。",
        "core_logic": [
            "据该材料，2026年7月和8月MLCC单月价格环比均上涨30%以上。",
            "该材料判断，本轮MLCC周期持续期可能长于上一轮；当前应作为分析判断而非已确认行业事实使用。",
            "该材料判断，国内外MLCC原厂所呈现的产业趋势相符，且AI需求带来的产能挤出效应较明显；当前尚缺独立证据验证。",
        ],
        "key_facts": ["据该材料，2026年7月和8月MLCC单月价格环比均上涨30%以上。"],
        "core_disagreements": ["MLCC周期长度与AI挤出判断尚待独立证据验证。"],
        "assumptions_to_verify": ["需验证MLCC价格变化能否由更多原厂或市场数据交叉确认。"],
        "investment_implication": "现有证据首先指向MLCC价格端改善，但来源单一，尚不足以确认完整行业上行周期；周期持续性及AI挤出效应需等待更多原厂、供需、库存和价格数据验证。",
        "major_risks": [
            "MLCC价格数据目前来自单一二手Source，尚需独立来源复核。",
            "本轮周期可能更长及AI挤出效应目前属于分析判断，不能作为已确认行业事实使用。",
        ],
        "knowledge_gaps": ["缺少MLCC行业供需、库存与多家原厂价格的独立交叉验证。"],
        "key_watch_items": ["跟踪MLCC行业供需与库存。", "跟踪国内外MLCC厂商竞争与定价。", "跟踪AI及其他下游应用需求。"],
        "recent_change": "首次建立 official Current View。",
        "evidence_claim_ids": MLCC_PRIMARY,
        "type_specific": {
            "applications": [],
            "demand_drivers": ["该材料判断，AI需求带来的产能挤出效应较明显；当前尚缺独立证据验证。"],
            "supply_capacity": [],
            "pricing": ["据该材料，2026年7月和8月MLCC单月价格环比均上涨30%以上。"],
            "major_suppliers": [],
            "product_evolution": [],
        },
    }
    yunzhong = {
        "one_line_conclusion": "据现有财通证券业绩会更新材料，昀冢科技MLCC业务正处于产能爬坡与持续扩产阶段，同时推进高容/超高容及车规产品；现有扩产数据大部分属于公司未来指引，兑现情况仍需持续验证。",
        "core_logic": [
            "据该材料，公司一期产线当前出货量约80亿颗/月，并指引2026Q4达到120亿颗/月、2026年底满产。",
            "据该材料，公司二期投资7.5亿元，指引2026年底开始导入量产、2027Q3完成爬坡、2027年底月产能达到220亿颗。",
            "据该材料，公司计划自2026H2围绕高容和超高容产品扩产，较原定2027年导入量产计划提前。",
            "据该材料，公司三期投资7.5亿元，指引2028年开始量产爬坡、2028H2陆续达产、2028年底月产能超过400亿颗。",
            "据该材料，公司车规级高容产品已完成认证，106、107进入实验室阶段。",
            "据该材料，公司2026年6月MLCC单月营收较2026年4月接近翻倍。",
        ],
        "key_facts": [
            "据该材料，公司一期产线当前出货量约80亿颗/月，并指引2026Q4达到120亿颗/月、2026年底满产。",
            "据该材料，公司二期投资7.5亿元，指引2026年底开始导入量产、2027Q3完成爬坡、2027年底月产能达到220亿颗。",
            "据该材料，公司计划自2026H2围绕高容和超高容产品扩产，较原定2027年导入量产计划提前。",
            "据该材料，公司三期投资7.5亿元，指引2028年开始量产爬坡、2028H2陆续达产、2028年底月产能超过400亿颗。",
            "据该材料，公司车规级高容产品已完成认证，106、107进入实验室阶段。",
            "据该材料，公司2026年6月MLCC单月营收较2026年4月接近翻倍。",
        ],
        "core_disagreements": ["昀冢科技扩产路径主要来自公司指引，实际投产、爬坡和产能兑现仍需后续事实验证。"],
        "assumptions_to_verify": [
            "昀冢科技高容和超高容产品占新扩产产能比例70%以上。",
            "昀冢科技关于MLCC上行周期提前的判断。",
        ],
        "investment_implication": "现有证据显示昀冢科技MLCC业务处于产能扩张、产品结构升级和车规验证推进阶段；若一期爬坡及后续二、三期扩产按指引兑现，公司MLCC业务规模仍有较大提升空间，但当前未来产能主要属于公司指引而非已实现产能。",
        "major_risks": [
            "扩产时间表主要属于公司指引，实际投产与爬坡存在兑现风险。",
            "MLCC单月营收数据目前缺少更多期间和独立来源交叉验证。",
            "车规产品后续进展需继续验证。",
        ],
        "knowledge_gaps": ["缺少扩产实际兑现、良率、客户结构、MLCC持续收入、产品认证后续进度的独立跟踪证据。"],
        "key_watch_items": [
            "跟踪一期产线2026Q4出货目标及2026年底满产指引兑现。",
            "跟踪二期、三期实际投产、爬坡进度及月产能兑现。",
            "跟踪106、107实验室阶段进展及后续认证。",
            "跟踪MLCC月度收入增长的持续性。",
        ],
        "recent_change": "首次建立 official Current View。",
        "evidence_claim_ids": YUNZHONG_PRIMARY,
        "type_specific": {},
    }
    return {MLCC_NODE_ID: mlcc, YUNZHONG_NODE_ID: yunzhong}


def _proposal_payload(node_id: str, content: dict) -> dict:
    evidence = content["evidence_claim_ids"]
    unresolved = YUNZHONG_UNRESOLVED if node_id == YUNZHONG_NODE_ID else []
    return {
        "node_id": node_id,
        "change_level": "initial",
        "reason": "Phase 2.4B human-approved Current View activation",
        "scope_normalization_notes": [
            "Direct assertions use role=subject only.",
            "context is review-only; related is prohibited as direct support.",
        ],
        "evidence_sufficiency": {"sufficient": False, "verdict": "PARTIAL"},
        "proposed_current_view": content,
        "evidence_claim_ids": evidence,
        "trigger_source_id": "SRC_20260814_F6E1EFAD",
        "previous_view_id": "",
        "previous_version": "",
        "context": {
            "phase": "2.4B",
            "human_confirmation_state": "confirmed",
            "reviewer": "human",
            "knowledge_sufficiency": "PARTIAL",
            "unresolved_claim_ids": unresolved,
        },
    }


def _counts(db: Database) -> dict:
    return db.one("SELECT COUNT(*) AS total, SUM(status='official') AS official FROM current_views")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--db", default=None)
    parser.add_argument("--artifact", default="artifacts/phase2_4a/current_view_pilot_review.json")
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    db_path = Path(args.db) if args.db else cfg.root / "pro_a.db"
    db = Database(db_path)
    payloads = approved_payloads()

    with db.connect() as conn:
        existing_views = {
            row["node_id"]: dict(row)
            for row in conn.execute(
                "SELECT * FROM current_views WHERE node_id IN (?,?) AND status='official'",
                (MLCC_NODE_ID, YUNZHONG_NODE_ID),
            )
        }
        existing_proposals = {
            row["target_node_id"]: dict(row)
            for row in conn.execute(
                "SELECT * FROM proposals WHERE proposal_type='current_view_change' AND target_node_id IN (?,?)",
                (MLCC_NODE_ID, YUNZHONG_NODE_ID),
            )
        }
        if len(existing_views) == 2 and len(existing_proposals) == 2 and all(
            existing_proposals[node_id]["status"] == "accepted"
            and json.loads(existing_views[node_id]["content_json"]) == payloads[node_id]
            and json.loads(existing_views[node_id]["trigger_claim_ids_json"]) == payloads[node_id]["evidence_claim_ids"]
            for node_id in (MLCC_NODE_ID, YUNZHONG_NODE_ID)
        ):
            print(json.dumps({
                "already_applied": True,
                "write_needed": False,
                "writes": 0,
                "view_ids": [existing_views[node_id]["view_id"] for node_id in (MLCC_NODE_ID, YUNZHONG_NODE_ID)],
                "proposal_ids": [existing_proposals[node_id]["proposal_id"] for node_id in (MLCC_NODE_ID, YUNZHONG_NODE_ID)],
                "sha": file_sha256(db_path),
            }, ensure_ascii=False, indent=2))
            return 0
        nodes = {
            row["node_id"]: dict(row)
            for row in conn.execute("SELECT * FROM nodes WHERE node_id IN (?,?)", (MLCC_NODE_ID, YUNZHONG_NODE_ID))
        }
        expected = {
            MLCC_NODE_ID: (MLCC_NAME, "Product"),
            YUNZHONG_NODE_ID: (YUNZHONG_NAME, "Company"),
        }
        for node_id, (name, node_type) in expected.items():
            node = nodes.get(node_id)
            if not node or (node["canonical_name"], node["primary_type"], node["status"]) != (name, node_type, "active"):
                raise RuntimeError(f"identity drift for {node_id}")
        if conn.execute("SELECT COUNT(*) FROM current_views WHERE node_id IN (?,?)", (MLCC_NODE_ID, YUNZHONG_NODE_ID)).fetchone()[0]:
            raise RuntimeError("PARTIAL_OR_CONFLICTING_DRIFT: target Current View already exists")
        existing = conn.execute("SELECT COUNT(*) FROM proposals WHERE proposal_type='current_view_change' AND target_node_id IN (?,?)", (MLCC_NODE_ID, YUNZHONG_NODE_ID)).fetchone()[0]
        if existing:
            raise RuntimeError("PARTIAL_OR_CONFLICTING_DRIFT: target proposal already exists")

    artifact = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    if artifact.get("artifact_only_proposals") != 2:
        raise RuntimeError("Phase 2.4A artifact mismatch")

    pre_sha = file_sha256(db_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.parent / "backups" / f"pro_a_pre_phase2_4b_{stamp}.db"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup)
    if file_sha256(backup) != pre_sha:
        raise RuntimeError("backup SHA mismatch")

    # Proposal insertion is the frozen creation step; acceptance is delegated
    # to ProposalManager, which performs the atomic view apply per proposal.
    proposal_ids = []
    for node_id in (MLCC_NODE_ID, YUNZHONG_NODE_ID):
        content = payloads[node_id]
        proposal_ids.append(db.add_proposal(
            "current_view_change", _proposal_payload(node_id, content),
            target_node_id=node_id, reason="Phase 2.4B human-approved Current View activation",
        ))

    manager = ProposalManager(cfg, db, Analyzer(cfg, db))
    results = [manager.accept(proposal_id) for proposal_id in proposal_ids]
    post_sha = file_sha256(db_path)
    if post_sha == pre_sha:
        raise RuntimeError("successful apply did not change Production DB")
    print(json.dumps({"pre_sha": pre_sha, "post_sha": post_sha, "backup": str(backup), "proposal_ids": proposal_ids, "results": results}, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
