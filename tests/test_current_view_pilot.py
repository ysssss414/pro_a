import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.current_view_pilot import (
    MLCC_CONTEXT_CLAIM_IDS,
    MLCC_FORBIDDEN_PRIMARY_TEXT,
    MLCC_NAME,
    MLCC_NODE_ID,
    MLCC_SUBJECT_CLAIM_IDS,
    YUNZHONG_NAME,
    YUNZHONG_NODE_ID,
    YUNZHONG_SUBJECT_CLAIM_IDS,
    CurrentViewPilotError,
    _validate_node_proposal,
    build_review_package,
    file_sha256,
    generate_review_package,
)
from pro_a.db import Database


CLAIM_ROWS = {
    "CLM_20260814_0B6E52F8": (
        "昀冢科技高容和超高容产品占新扩产产能比例70%以上。",
        "company_guidance", "2026H2", "needs_review", 0.0, "公司",
    ),
    "CLM_20260814_541F5C31": (
        "昀冢科技一期产线当前出货量80亿颗/月，预计2026Q4达120亿颗/月，2026年底满产。",
        "company_guidance", "2026Q4", "current", 0.8, "公司",
    ),
    "CLM_20260814_8E4B9E25": (
        "昀冢科技二期投资7.5亿元，预计2026年底开始导入量产，2027Q3完成爬坡，2027年底月产能达220亿颗。",
        "company_guidance", "2027年底", "current", 0.8, "公司",
    ),
    "CLM_20260814_939CAEDD": (
        "昀冢科技针对超高容量产计划提前半年，原计划2027年导入量产，现计划2026H2围绕高容超高容扩产。",
        "company_guidance", "2026H2", "current", 0.8, "公司",
    ),
    "CLM_20260814_980FA010": (
        "2026年7月和8月MLCC单月价格环比上涨30%以上。",
        "data", "2026-07/2026-08", "current", 0.9, "公司",
    ),
    "CLM_20260814_9A069D06": (
        "昀冢科技三期投资7.5亿元，预计2028年开始量产爬坡，2028H2陆续达产，2028年底月产能超400亿颗。",
        "company_guidance", "2028年底", "current", 0.8, "公司",
    ),
    "CLM_20260814_BA7AC415": (
        "昀冢科技车规级高容产品已完成认证，106、107进入实验室阶段。",
        "fact", "2026-08-13", "current", 0.8, "公司",
    ),
    "CLM_20260814_BAED6789": (
        "本轮MLCC周期持续期将长于上一轮周期。",
        "expert_judgment", "", "current", 0.7, "行业",
    ),
    "CLM_20260814_D2C7FCD1": (
        "国内MLCC原厂与海外MLCC原厂业绩报中看到的产业趋势相符合，AI挤出效应明显。",
        "expert_judgment", "", "current", 0.7, "行业",
    ),
    "CLM_20260814_E1A48290": (
        "2026年6月MLCC单月营收相较于4月将近翻倍。",
        "data", "2026-06", "current", 0.9, "公司",
    ),
    "CLM_20260814_E53B8E9C": (
        "昀冢科技原预判MLCC上行周期于2026H2开始，但实际提前半年到来。",
        "company_guidance", "2026H2", "needs_review", 0.0, "行业",
    ),
}


def _fixture(tmp_path: Path) -> Path:
    db_path = tmp_path / "pilot.db"
    Database(db_path).init_schema()
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO nodes(
                   node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                (MLCC_NODE_ID, MLCC_NAME, "Product", "", "active", "2026-08-17", "2026-08-17"),
                (YUNZHONG_NODE_ID, YUNZHONG_NAME, "Company", "", "active", "2026-08-26", "2026-08-26"),
            ],
        )
        conn.execute(
            """INSERT INTO sources(
                   source_id,title,original_name,archived_path,sha256,ingestion_mode,
                   analysis_mode,source_type,source_rank,origin_type,publication_time,
                   ingested_at,status
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "SRC_20260814_F6E1EFAD",
                "财通电子&新科技 昀冢科技业绩说明会更新：MLCC业绩答卷&未来指引双超预期",
                "source.md", "archive/source.md", "a" * 64, "standard", "standard",
                "md", "B", "secondary", "2026-08-13", "2026-08-14", "analyzed",
            ),
        )
        for claim_id, (statement, nature, fact_time, status, confidence, scope) in CLAIM_ROWS.items():
            conn.execute(
                """INSERT INTO claims(
                       claim_id,statement,nature,fact_time,publication_time,ingestion_time,
                       source_id,scope,status,confidence,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    claim_id, statement, nature, fact_time, "2026-08-13", "2026-08-14",
                    "SRC_20260814_F6E1EFAD", scope, status, confidence, "2026-08-14",
                ),
            )
        conn.executemany(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            [(claim_id, MLCC_NODE_ID, "subject") for claim_id in MLCC_SUBJECT_CLAIM_IDS]
            + [(claim_id, MLCC_NODE_ID, "context") for claim_id in MLCC_CONTEXT_CLAIM_IDS]
            + [(claim_id, YUNZHONG_NODE_ID, "subject") for claim_id in YUNZHONG_SUBJECT_CLAIM_IDS],
        )
    return db_path


def _proposal(package: dict, name: str) -> dict:
    return package["nodes"][name]


def test_subject_only_primary_evidence(tmp_path: Path):
    package = build_review_package(_fixture(tmp_path))
    assert _proposal(package, MLCC_NAME)["primary_evidence_claim_ids"] == list(MLCC_SUBJECT_CLAIM_IDS)
    assert set(_proposal(package, YUNZHONG_NAME)["primary_evidence_claim_ids"]) == (
        set(YUNZHONG_SUBJECT_CLAIM_IDS) - {"CLM_20260814_0B6E52F8", "CLM_20260814_E53B8E9C"}
    )


def test_context_claim_rejected_as_direct_support(tmp_path: Path):
    db_path = _fixture(tmp_path)
    package = build_review_package(db_path)
    proposal = _proposal(package, MLCC_NAME)
    proposal["primary_evidence_claim_ids"].append("CLM_20260814_541F5C31")
    proposal["payload"]["evidence_claim_ids"].append("CLM_20260814_541F5C31")
    with pytest.raises(CurrentViewPilotError, match="role=subject"):
        state = _claims_for_node(db_path, MLCC_NODE_ID)
        _validate_node_proposal(proposal, _node_for(db_path, MLCC_NODE_ID), state)


def test_related_claim_rejected_as_direct_support(tmp_path: Path):
    db_path = _fixture(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE claim_node_links SET role='related' WHERE claim_id=? AND node_id=?",
            (MLCC_SUBJECT_CLAIM_IDS[0], MLCC_NODE_ID),
        )
    with pytest.raises(CurrentViewPilotError, match="subject Claim drift"):
        build_review_package(db_path)


def test_company_specific_context_leakage_into_mlcc_fails(tmp_path: Path):
    db_path = _fixture(tmp_path)
    package = build_review_package(db_path)
    proposal = _proposal(package, MLCC_NAME)
    proposal["payload"]["proposed_current_view"]["one_line_conclusion"] += " 80亿颗/月"
    with pytest.raises(CurrentViewPilotError, match="Company-only context"):
        _validate_node_proposal(
            proposal, _node_for(db_path, MLCC_NODE_ID), _claims_for_node(db_path, MLCC_NODE_ID)
        )


def test_expert_judgment_is_preserved(tmp_path: Path):
    proposal = _proposal(build_review_package(_fixture(tmp_path)), MLCC_NAME)
    expert = [
        item for item in proposal["review_sections"]["primary_assertions"]
        if item["evidence_kind"] == "expert_judgment"
    ]
    assert len(expert) == 2
    assert all("分析师判断" in item["text"] and "已确认" in item["text"] for item in expert)


def test_company_guidance_is_preserved(tmp_path: Path):
    proposal = _proposal(build_review_package(_fixture(tmp_path)), YUNZHONG_NAME)
    guidance = [
        item for item in proposal["review_sections"]["primary_assertions"]
        if item["evidence_kind"] == "company_guidance"
    ]
    assert len(guidance) == 4
    assert all("公司" in item["text"] for item in guidance)


def test_needs_review_is_conservative(tmp_path: Path):
    proposal = _proposal(build_review_package(_fixture(tmp_path)), YUNZHONG_NAME)
    unresolved = proposal["review_sections"]["uncertainty"]
    assert {item["claim_ids"][0] for item in unresolved} == {
        "CLM_20260814_0B6E52F8", "CLM_20260814_E53B8E9C"
    }
    assert all(item["handling"] == "UNRESOLVED_ONLY" for item in unresolved)


def test_source_traceability_is_complete(tmp_path: Path):
    package = build_review_package(_fixture(tmp_path))
    for proposal in package["nodes"].values():
        assert proposal["validation"]["source_traceability"] is True
        assert all(item["source_id"] and item["source_title"] for item in proposal["review_sections"]["evidence"])


def test_exactly_two_pilot_nodes(tmp_path: Path):
    package = build_review_package(_fixture(tmp_path))
    assert set(package["nodes"]) == {MLCC_NAME, YUNZHONG_NAME}
    assert package["artifact_only_proposals"] == 2


def test_no_final_current_view_write_without_confirmation(tmp_path: Path):
    db_path = _fixture(tmp_path)
    artifact = tmp_path / "artifacts" / "review.json"
    report = tmp_path / "report.md"
    pre_sha = file_sha256(db_path)
    package = generate_review_package(db_path, artifact, report)
    assert file_sha256(db_path) == pre_sha
    assert package["production"]["current_views_created"] == 0
    assert package["production"]["proposals_created_in_db"] == 0
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM current_views").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM proposals").fetchone()[0] == 0
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    assert persisted["human_review_required"] is True
    assert persisted["production_write_authorized_for_current_view"] is False
    assert report.exists()


def test_mlcc_primary_text_has_no_forbidden_context(tmp_path: Path):
    proposal = _proposal(build_review_package(_fixture(tmp_path)), MLCC_NAME)
    text = json.dumps(proposal["payload"]["proposed_current_view"], ensure_ascii=False)
    assert all(token not in text for token in MLCC_FORBIDDEN_PRIMARY_TEXT)


def _node_for(db_path: Path, node_id: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        node = dict(conn.execute(
            "SELECT node_id,canonical_name,primary_type,description,status FROM nodes WHERE node_id=?",
            (node_id,),
        ).fetchone())
        node["aliases"] = []
        return node


def _claims_for_node(db_path: Path, node_id: str) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            """SELECT cnl.node_id,cnl.role,c.*,s.title AS source_title,s.source_rank,
                      s.origin_type,s.underlying_source_id,s.source_id AS evidence_source_id
               FROM claim_node_links cnl JOIN claims c ON c.claim_id=cnl.claim_id
               JOIN sources s ON s.source_id=c.source_id WHERE cnl.node_id=? ORDER BY c.claim_id""",
            (node_id,),
        ).fetchall()]
