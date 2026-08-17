from __future__ import annotations

from pathlib import Path

import pytest

from pro_a.analyzer import Analyzer, SourceAnalysis
from pro_a.pipeline import IngestionPipeline
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from pro_a.proposals import ProposalManager

from stability_helpers import add_source_and_claim, make_config


class StaticLLM:
    available = True

    def __init__(self, payload):
        self.payload = payload

    def json(self, system, user):
        return self.payload


class SequenceLLM:
    available = True

    def __init__(self, *payloads):
        self.payloads = list(payloads)

    def json(self, system, user):
        return self.payloads.pop(0)


def relation_nodes(db):
    return (
        db.add_node("Rubin GPU", "Product", ["Rubin"]),
        db.add_node("HBM4", "Technology", ["高带宽内存4"]),
    )


def claim(statement: str, evidence_excerpt: str) -> dict:
    return {
        "statement": statement,
        "nature": "fact",
        "related_node_ids": [],
        "related_candidate_names": [],
        "fact_time": "",
        "evidence_pointer": "[[PARA:1]]",
        "evidence_excerpt": evidence_excerpt,
        "attributed_to": "",
        "scope": "",
        "assumption": "",
        "status": "current",
        "confidence": 0.9,
        "novelty_level": "N2",
        "structured": {},
    }


def atomic_guidance_claim(statement: str) -> dict:
    item = claim(statement, statement)
    item["nature"] = "company_guidance"
    item["attributed_to"] = "NVIDIA"
    item["scope"] = "NVIDIA 产品"
    return item


def candidate(from_node_id: str, to_node_id: str, **overrides) -> dict:
    value = {
        "from_node_id": from_node_id,
        "relation_type": "uses",
        "to_node_id": to_node_id,
        "scope": "Rubin",
        "supporting_claim_refs": ["C1"],
        "confidence": 0.92,
        "reason": "C1 directly states that Rubin GPU uses HBM4",
    }
    value.update(overrides)
    return value


def source_payload(*, claims: list[dict], relation_candidates: list) -> dict:
    return {
        "source_metadata": {
            "title": "Rubin memory update",
            "author": "",
            "organization": "",
            "publication_time": "2026-08-17",
            "source_rank": "A",
            "source_origin_type": "primary",
            "summary": "Rubin memory relation evidence",
        },
        "node_matches": [],
        "node_candidates": [],
        "claims": claims,
        "relation_candidates": relation_candidates,
        "source_references": [],
    }


def directional_nodes(db):
    return (
        db.add_node("Alpha", "Product"),
        db.add_node("Beta", "Technology"),
    )


def analyze_directional_candidate(
    tmp_path: Path,
    text: str,
    relation_type: str,
    *,
    reverse_candidate: bool = False,
):
    cfg, db = make_config(tmp_path)
    alpha_id, beta_id = directional_nodes(db)
    from_node_id, to_node_id = (
        (beta_id, alpha_id) if reverse_candidate else (alpha_id, beta_id)
    )
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, text)],
        relation_candidates=[candidate(
            from_node_id, to_node_id, relation_type=relation_type,
        )],
    ))
    return analyzer.analyze_source("direction.md", text, "standard")


def test_valid_direct_relation_candidate_uses_temporary_claim_ref(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "NVIDIA Rubin GPU 将采用 HBM4。"
    payload = source_payload(
        claims=[claim(text, text)],
        relation_candidates=[candidate(from_node_id, to_node_id)],
    )
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(payload)

    result = analyzer.analyze_source("sample.md", text, "standard")

    assert result.claims[0]["claim_ref"] == "C1"
    assert result.relation_candidates == [{
        "from_node_id": from_node_id,
        "relation_type": "uses",
        "to_node_id": to_node_id,
        "scope": "Rubin",
        "supporting_claim_refs": ["C1"],
        "reason": "C1 directly states that Rubin GPU uses HBM4",
        "_resolved_supporting_claim_indices": [0],
        "confidence": 0.92,
    }]
    assert result.rejected_relation_candidates == []


def test_endpoint_aliases_satisfy_dual_endpoint_gate(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin 将采用高带宽内存4。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, text)],
        relation_candidates=[candidate(from_node_id, to_node_id)],
    ))

    result = analyzer.analyze_source("alias.md", text, "standard")

    assert len(result.relation_candidates) == 1
    assert result.rejected_relation_candidates == []


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("unknown_from", "unknown from Node"),
        ("unknown_to", "unknown to Node"),
        ("inactive_from", "inactive from endpoint"),
        ("inactive_to", "inactive to endpoint"),
        ("self", "self relation not allowed"),
        ("part_of", "part_of not allowed"),
        ("invalid_type", "invalid relation_type"),
        ("empty_refs", "supporting_claim_refs must not be empty"),
        ("invalid_confidence", "confidence must be between 0 and 1"),
    ],
)
def test_candidate_structure_and_endpoints_are_rejected(
    tmp_path: Path, case: str, reason: str,
):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    item = candidate(from_node_id, to_node_id)
    if case == "unknown_from":
        item["from_node_id"] = "NODE_MISSING_FROM"
    elif case == "unknown_to":
        item["to_node_id"] = "NODE_MISSING_TO"
    elif case == "inactive_from":
        db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (from_node_id,))
    elif case == "inactive_to":
        db.execute("UPDATE nodes SET status='inactive' WHERE node_id=?", (to_node_id,))
    elif case == "self":
        item["to_node_id"] = from_node_id
    elif case == "part_of":
        item["relation_type"] = "part_of"
    elif case == "invalid_type":
        item["relation_type"] = "invented_relation"
    elif case == "empty_refs":
        item["supporting_claim_refs"] = []
    elif case == "invalid_confidence":
        item["confidence"] = 1.1
    text = "Rubin GPU 将采用 HBM4。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, text)], relation_candidates=[item],
    ))

    result = analyzer.analyze_source("invalid.md", text, "standard")

    assert result.relation_candidates == []
    assert reason in result.rejected_relation_candidates[0]["reason"]


@pytest.mark.parametrize(
    ("ref", "excerpt", "reason", "stage"),
    [
        ("C9", "Rubin GPU 将采用 HBM4。", "unknown supporting_claim_ref", "claim_reference"),
        ("C1", "原文并不存在这条证据", "supporting Claim rejected", "claim_reference"),
    ],
)
def test_candidate_claim_reference_must_resolve_to_validated_claim(
    tmp_path: Path, ref: str, excerpt: str, reason: str, stage: str,
):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin GPU 将采用 HBM4。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, excerpt)],
        relation_candidates=[candidate(
            from_node_id, to_node_id, supporting_claim_refs=[ref],
        )],
    ))

    result = analyzer.analyze_source("refs.md", text, "standard")

    rejection = result.rejected_relation_candidates[0]
    assert result.relation_candidates == []
    assert reason in rejection["reason"]
    assert rejection["stage"] == stage


def test_two_claims_cannot_combine_separate_endpoints(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin GPU 是下一代 GPU。HBM4 是下一代高带宽内存技术。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[
            claim("Rubin GPU 是下一代 GPU。", "Rubin GPU 是下一代 GPU。"),
            claim("HBM4 是下一代高带宽内存技术。", "HBM4 是下一代高带宽内存技术。"),
        ],
        relation_candidates=[candidate(
            from_node_id, to_node_id, supporting_claim_refs=["C1", "C2"],
        )],
    ))

    result = analyzer.analyze_source("leap.md", text, "standard")

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "evidence"
    assert "both endpoints" in result.rejected_relation_candidates[0]["reason"]


def test_candidate_reason_cannot_replace_endpoint_evidence(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "这两项技术都受到市场关注。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, text)],
        relation_candidates=[candidate(
            from_node_id, to_node_id,
            reason="Rubin GPU explicitly uses HBM4",
        )],
    ))

    result = analyzer.analyze_source("reason.md", text, "standard")

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "evidence"


def test_candidate_cannot_reference_other_claim_when_relation_evidence_exists(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin GPU 将采用 HBM4。市场仍在增长。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[
            claim("Rubin GPU 将采用 HBM4。", "Rubin GPU 将采用 HBM4。"),
            claim("市场仍在增长。", "市场仍在增长。"),
        ],
        relation_candidates=[candidate(
            from_node_id, to_node_id, supporting_claim_refs=["C2"],
        )],
    ))

    result = analyzer.analyze_source("wrong-ref.md", text, "standard")

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "evidence"


@pytest.mark.parametrize(
    ("relation_type", "text"),
    [
        ("upstream_of", "Alpha 是 Beta 的上游。"),
        ("supplies", "Alpha 供应 Beta。"),
        ("produces", "Alpha 生产 Beta。"),
        ("uses", "Alpha 使用 Beta。"),
        ("applied_in", "Alpha 应用于 Beta。"),
        ("depends_on", "Alpha 依赖 Beta。"),
        ("constrains", "Alpha 制约 Beta。"),
        ("drives", "Alpha 驱动 Beta。"),
        ("benefits_from", "Alpha 受益于 Beta。"),
        ("exposed_to", "Alpha 暴露于 Beta。"),
        ("regulated_by", "Alpha 受 Beta 监管。"),
        ("validates", "Alpha 验证 Beta。"),
        ("invalidates", "Alpha 证伪 Beta。"),
    ],
)
def test_directional_relation_accepts_only_explicit_safe_pattern(
    tmp_path: Path, relation_type: str, text: str,
):
    result = analyze_directional_candidate(tmp_path, text, relation_type)

    assert result.relation_candidates[0]["relation_type"] == relation_type
    assert result.rejected_relation_candidates == []


@pytest.mark.parametrize(
    ("text", "relation_type"),
    [
        ("Alpha 由 Beta 供应。", "supplies"),
        ("Alpha 由 Beta 生产。", "produces"),
        ("Alpha 被 Beta 使用。", "uses"),
        ("Alpha 监管 Beta。", "regulated_by"),
    ],
)
def test_reversed_direction_is_rejected(
    tmp_path: Path, text: str, relation_type: str,
):
    result = analyze_directional_candidate(tmp_path, text, relation_type)

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "semantic"
    assert result.rejected_relation_candidates[0]["reason"] == "reversed relation direction"


@pytest.mark.parametrize(
    ("text", "relation_type"),
    [
        ("Alpha 由 Beta 供应。", "supplies"),
        ("Alpha 被 Beta 使用。", "uses"),
    ],
)
def test_safe_passive_pattern_can_support_actual_direction(
    tmp_path: Path, text: str, relation_type: str,
):
    result = analyze_directional_candidate(
        tmp_path, text, relation_type, reverse_candidate=True,
    )

    assert len(result.relation_candidates) == 1
    assert result.rejected_relation_candidates == []


def test_complex_direction_syntax_is_conservatively_rejected(tmp_path: Path):
    result = analyze_directional_candidate(
        tmp_path, "Alpha 围绕 Beta 的供应关系展开讨论。", "supplies",
    )

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "semantic"
    assert result.rejected_relation_candidates[0]["reason"] == "semantic direction unsupported"


@pytest.mark.parametrize(
    ("text", "relation_type"),
    [
        ("Alpha 不依赖 Beta。", "depends_on"),
        ("Alpha 并未采用 Beta。", "uses"),
        ("Alpha 未采用 Beta。", "uses"),
        ("Alpha 不使用 Beta。", "uses"),
        ("Alpha 不再使用 Beta。", "uses"),
        ("Alpha 与 Beta 不相关。", "related_to"),
        ("Alpha 不受益于 Beta。", "benefits_from"),
        ("Alpha 不受 Beta 监管。", "regulated_by"),
        ("Alpha does not use Beta.", "uses"),
        ("Alpha is not related to Beta.", "related_to"),
    ],
)
def test_explicit_negation_rejects_positive_relation(
    tmp_path: Path, text: str, relation_type: str,
):
    result = analyze_directional_candidate(tmp_path, text, relation_type)

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "semantic"
    assert result.rejected_relation_candidates[0]["reason"] == "negated relation evidence"


@pytest.mark.parametrize("relation_type", ["uses", "supplies", "depends_on", "related_to"])
def test_association_only_text_fails_semantic_gate(
    tmp_path: Path, relation_type: str,
):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin GPU 与 HBM4 是当前 AI 硬件研究的两个重点。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, text)],
        relation_candidates=[candidate(
            from_node_id, to_node_id, relation_type=relation_type,
        )],
    ))

    result = analyzer.analyze_source("association.md", text, "standard")

    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["stage"] == "semantic"
    assert result.rejected_relation_candidates[0]["reason"] == "semantic support insufficient"


def test_explicit_related_to_wording_can_pass_without_being_a_fallback(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin GPU 与 HBM4 明确相关。"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = StaticLLM(source_payload(
        claims=[claim(text, text)],
        relation_candidates=[candidate(
            from_node_id, to_node_id, relation_type="related_to",
        )],
    ))

    result = analyzer.analyze_source("related.md", text, "standard")

    assert result.relation_candidates[0]["relation_type"] == "related_to"
    assert result.rejected_relation_candidates == []


def test_source_prompt_forbids_external_knowledge_and_claim_splicing():
    assert "禁止输出 part_of" in SOURCE_ANALYSIS_SYSTEM
    assert "不得拼接多条 Claim" in SOURCE_ANALYSIS_SYSTEM
    assert "常识或外部知识" in SOURCE_ANALYSIS_SYSTEM
    assert "related_to 不是语义不清时的兜底" in SOURCE_ANALYSIS_SYSTEM
    assert "Rubin GPU 将采用 HBM4" in SOURCE_ANALYSIS_SYSTEM
    assert "A 不依赖 B" in SOURCE_ANALYSIS_SYSTEM
    assert "A 由 B 供应" in SOURCE_ANALYSIS_SYSTEM
    assert "A 被 B 使用" in SOURCE_ANALYSIS_SYSTEM


def test_atomic_split_maps_only_unique_relation_supporting_child(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = (
        "NVIDIA Rubin GPU 当前带宽为1TB/s，"
        "预计 NVIDIA Rubin GPU 将采用 HBM4。"
    )
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = StaticLLM(source_payload(
        claims=[atomic_guidance_claim(text)],
        relation_candidates=[candidate(
            from_node_id, to_node_id, scope="C1 / Rubin",
        )],
    ))
    request = cfg.root / "inbox" / "standard" / "atomic.md"
    request.write_text(text, encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "analyzed"
    assert len(result["claims"]) == 2
    claims_by_id = {
        row["claim_id"]: row
        for row in db.all(
            "SELECT claim_id,statement FROM claims WHERE source_id=? ORDER BY created_at,claim_id",
            (result["source_id"],),
        )
    }
    supporting_id = next(
        claim_id for claim_id, row in claims_by_id.items()
        if "采用 HBM4" in row["statement"]
    )
    unrelated_id = next(claim_id for claim_id in claims_by_id if claim_id != supporting_id)
    proposal = db.proposal(result["relation_proposals"][0])
    assert proposal["payload"]["supporting_claim_ids"] == [supporting_id]
    assert unrelated_id not in proposal["payload"]["supporting_claim_ids"]
    assert "supporting_claim_refs" not in proposal["payload"]
    assert "_resolved_supporting_claim_indices" not in proposal["payload"]
    assert "C1" not in proposal["payload"]["scope"]
    assert "C1" not in proposal["payload"]["reason"]

    accepted = ProposalManager(cfg, db, pipeline.analyzer).accept(proposal["proposal_id"])
    assert [
        item["claim_id"] for item in db.relation_evidence(accepted["relation_id"])
    ] == [supporting_id]


def test_atomic_split_with_no_relation_supporting_child_is_rejected(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = (
        "NVIDIA Rubin GPU 当前带宽为1TB/s，"
        "预计 NVIDIA Rubin GPU 明年扩产；HBM4 同期发布。"
    )
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = StaticLLM(source_payload(
        claims=[atomic_guidance_claim(text)],
        relation_candidates=[candidate(from_node_id, to_node_id)],
    ))
    request = cfg.root / "inbox" / "standard" / "atomic-zero.md"
    request.write_text(text, encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "analyzed"
    assert len(result["claims"]) == 2
    assert result["relation_proposals"] == []
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0
    rejection = result["audit"]["rejected_relation_candidates"][0]
    assert rejection["stage"] == "claim_resolution"
    assert rejection["reason"] == "atomic Claim ref has no relation-supporting child"


def test_atomic_ref_with_multiple_relation_children_is_ambiguous(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    analyzer = Analyzer(cfg, db)
    claims = [
        {
            **claim("Rubin GPU 使用 HBM4。", "Rubin GPU 使用 HBM4。"),
            "claim_ref": "C1",
            "evidence_validated": True,
        },
        {
            **claim("Rubin GPU 采用 HBM4。", "Rubin GPU 采用 HBM4。"),
            "claim_ref": "C1",
            "evidence_validated": True,
        },
    ]

    accepted, rejected = analyzer._validate_relation_candidates(
        [candidate(from_node_id, to_node_id)], claims,
    )

    assert accepted == []
    assert rejected[0]["stage"] == "claim_resolution"
    assert "ambiguous" in rejected[0]["reason"]


def test_chunk_merge_recomputes_global_relation_child_index(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    unrelated = "独立市场数据保持稳定。"
    atomic_text = (
        "NVIDIA Rubin GPU 当前带宽为1TB/s，"
        "预计 NVIDIA Rubin GPU 将采用 HBM4。"
    )
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(
        source_payload(
            claims=[claim(unrelated, unrelated)], relation_candidates=[],
        ),
        source_payload(
            claims=[atomic_guidance_claim(atomic_text)],
            relation_candidates=[candidate(from_node_id, to_node_id)],
        ),
    )
    monkeypatch.setattr(
        "pro_a.analyzer.chunk_text", lambda text, max_chars: [unrelated, atomic_text],
    )

    result = analyzer.analyze_source(
        "chunks.md", f"{unrelated}\n{atomic_text}", "standard",
    )

    assert len(result.claims) == 3
    relation_candidate = result.relation_candidates[0]
    assert relation_candidate["supporting_claim_refs"] == ["C2"]
    assert relation_candidate["_resolved_supporting_claim_indices"] == [2]
    assert "采用 HBM4" in result.claims[2]["statement"]


class PipelineAnalyzer:
    available = True

    def __init__(self, from_node_id: str, to_node_id: str, *, candidates=None, claims=None):
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.candidates = candidates
        self.claims = claims

    def analyze_source(self, filename, text, mode):
        claims = self.claims or [{
            **claim("Rubin GPU 将采用 HBM4。", "Rubin GPU 将采用 HBM4。"),
            "claim_ref": "C1",
            "evidence_validated": True,
            "validation": {"evidence_validated": True, "model_confidence": 0.9},
        }]
        candidates = self.candidates or [candidate(self.from_node_id, self.to_node_id)]
        resolved_candidates = []
        for item in candidates:
            normalized = dict(item)
            indices: list[int] = []
            for ref in normalized.get("supporting_claim_refs") or []:
                matches = [
                    index for index, claim_item in enumerate(claims)
                    if claim_item.get("claim_ref") == ref
                ]
                if len(matches) != 1:
                    break
                indices.append(matches[0])
            else:
                normalized["_resolved_supporting_claim_indices"] = indices
            resolved_candidates.append(normalized)
        return SourceAnalysis(
            source_metadata=source_payload(claims=[], relation_candidates=[])["source_metadata"],
            node_matches=[],
            node_candidates=[],
            claims=claims,
            source_references=[],
            relation_candidates=resolved_candidates,
        )

    def backfill_candidate_claims(self, candidates, claims):
        return {}


def test_pipeline_maps_temp_ref_to_persistent_claim_and_only_creates_proposal(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    pipeline = IngestionPipeline(cfg, db)
    analyzer = PipelineAnalyzer(from_node_id, to_node_id)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "relation.md"
    request.write_text("Rubin GPU 将采用 HBM4。", encoding="utf-8")

    result = pipeline.process_all()[0]

    proposal_id = result["relation_proposals"][0]
    proposal = db.proposal(proposal_id)
    persisted_claim_id = result["claims"][0]
    assert proposal["status"] == "pending"
    assert proposal["payload"]["supporting_claim_ids"] == [persisted_claim_id]
    assert persisted_claim_id.startswith("CLM_")
    assert "supporting_claim_refs" not in proposal["payload"]
    assert "_resolved_supporting_claim_indices" not in proposal["payload"]
    assert "C1" not in proposal["payload"]["reason"]
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM relation_evidence_links")["n"] == 0
    assert result["audit"]["relation_proposals"][0]["proposal_id"] == proposal_id
    receipt = Path(result["receipt_path"]).read_text(encoding="utf-8")
    assert "## Relation Proposals" in receipt
    assert "Relation Candidates: accepted 1, rejected 0" in receipt


def test_pipeline_unresolved_temp_ref_creates_no_proposal_and_is_audited(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    analyzer = PipelineAnalyzer(
        from_node_id,
        to_node_id,
        candidates=[candidate(
            from_node_id, to_node_id, supporting_claim_refs=["C9"],
        )],
    )
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "unresolved.md"
    request.write_text("Rubin GPU 将采用 HBM4。", encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "analyzed"
    assert result["relation_proposals"] == []
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 0
    rejection = result["audit"]["rejected_relation_candidates"][0]
    assert rejection["stage"] == "proposal_mapping"
    assert "lacks resolved supporting Claim indices" in rejection["reason"]


def test_same_identity_candidates_merge_persistent_claims(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    claims = [
        {
            **claim("Rubin GPU 将采用 HBM4。", "Rubin GPU 将采用 HBM4。"),
            "claim_ref": "C1",
            "evidence_validated": True,
            "validation": {"evidence_validated": True},
        },
        {
            **claim("Rubin GPU 使用 HBM4 扩展带宽。", "Rubin GPU 使用 HBM4 扩展带宽。"),
            "claim_ref": "C2",
            "evidence_validated": True,
            "validation": {"evidence_validated": True},
        },
    ]
    candidates = [
        candidate(from_node_id, to_node_id, supporting_claim_refs=["C1"]),
        candidate(from_node_id, to_node_id, supporting_claim_refs=["C2"]),
    ]
    analyzer = PipelineAnalyzer(
        from_node_id, to_node_id, candidates=candidates, claims=claims,
    )
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "merge.md"
    request.write_text("Rubin GPU 将采用 HBM4。Rubin GPU 使用 HBM4 扩展带宽。", encoding="utf-8")

    result = pipeline.process_all()[0]

    assert len(result["relation_proposals"]) == 1
    proposal = db.proposal(result["relation_proposals"][0])
    assert proposal["payload"]["supporting_claim_ids"] == result["claims"]
    assert db.one("SELECT COUNT(*) AS n FROM proposals")["n"] == 1


def test_pipeline_recovers_stale_pending_and_synchronizes_artifact(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    add_source_and_claim(
        db,
        source_id="SRC_OLD_RELATION_CANDIDATE",
        claim_id="CLM_OLD_RELATION_CANDIDATE",
        node_id=from_node_id,
        source_rank="A",
        origin_type="primary",
        confidence=0.9,
    )
    old_proposal_id = db.propose_relation(
        from_node_id,
        "uses",
        to_node_id,
        scope="Rubin",
        supporting_claim_ids=["CLM_OLD_RELATION_CANDIDATE"],
    )
    db.execute(
        "UPDATE claims SET status='invalidated' WHERE claim_id='CLM_OLD_RELATION_CANDIDATE'"
    )
    pipeline = IngestionPipeline(cfg, db)
    analyzer = PipelineAnalyzer(from_node_id, to_node_id)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "recover.md"
    request.write_text("Rubin GPU 将采用 HBM4。", encoding="utf-8")

    result = pipeline.process_all()[0]

    new_proposal_id = result["relation_proposals"][0]
    assert new_proposal_id != old_proposal_id
    assert db.proposal(old_proposal_id)["status"] == "stale"
    artifact = cfg.root / "review" / "proposals" / f"{old_proposal_id}.md"
    artifact_text = artifact.read_text(encoding="utf-8")
    assert "- status: stale" in artifact_text
    assert "no longer valid" in artifact_text


def test_existing_formal_relation_still_gets_pending_proposal_without_evidence_attach(
    tmp_path: Path,
):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    add_source_and_claim(
        db,
        source_id="SRC_FORMAL_RELATION_BASE",
        claim_id="CLM_FORMAL_RELATION_BASE",
        node_id=from_node_id,
        source_rank="A",
        origin_type="primary",
        confidence=0.9,
    )
    relation_id = db.add_relation(
        from_node_id,
        "uses",
        to_node_id,
        scope="Rubin",
        evidence_claim_id="CLM_FORMAL_RELATION_BASE",
    )
    pipeline = IngestionPipeline(cfg, db)
    analyzer = PipelineAnalyzer(from_node_id, to_node_id)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "existing.md"
    request.write_text("Rubin GPU 将采用 HBM4。", encoding="utf-8")

    result = pipeline.process_all()[0]

    assert len(result["relation_proposals"]) == 1
    assert db.proposal(result["relation_proposals"][0])["status"] == "pending"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 1
    assert [item["claim_id"] for item in db.relation_evidence(relation_id)] == [
        "CLM_FORMAL_RELATION_BASE"
    ]


def test_relation_candidate_pipeline_is_isolated_from_impact_and_propagation(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    pipeline = IngestionPipeline(cfg, db)
    analyzer = PipelineAnalyzer(from_node_id, to_node_id)
    pipeline.analyzer = analyzer
    pipeline.propagation.analyzer = analyzer
    request = cfg.root / "inbox" / "standard" / "isolated.md"
    request.write_text("Rubin GPU 将采用 HBM4。", encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["relation_proposals"]
    assert db.one("SELECT COUNT(*) AS n FROM impact_reviews")["n"] == 0
    assert db.one(
        "SELECT COUNT(*) AS n FROM proposals WHERE proposal_type='current_view_change'"
    )["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM current_views")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM knowledge_gaps")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM research_questions")["n"] == 0


def test_mock_llm_positive_sample_creates_pending_relation_proposal(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "NVIDIA Rubin GPU 将采用 HBM4。HBM4 带宽相比上一代提升。"
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = StaticLLM(source_payload(
        claims=[claim(
            "NVIDIA Rubin GPU 将采用 HBM4。",
            "NVIDIA Rubin GPU 将采用 HBM4。",
        )],
        relation_candidates=[candidate(from_node_id, to_node_id)],
    ))
    request = cfg.root / "inbox" / "standard" / "positive.md"
    request.write_text(text, encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "analyzed"
    assert len(result["relation_proposals"]) == 1
    proposal = db.proposal(result["relation_proposals"][0])
    assert proposal["proposal_type"] == "node_relation"
    assert proposal["status"] == "pending"
    assert proposal["payload"]["supporting_claim_ids"] == result["claims"]
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0


def test_mock_llm_negative_sample_creates_no_relation_proposal(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    from_node_id, to_node_id = relation_nodes(db)
    text = "Rubin GPU 是下一代 AI GPU。HBM4 是下一代高带宽内存技术。"
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = StaticLLM(source_payload(
        claims=[
            claim("Rubin GPU 是下一代 AI GPU。", "Rubin GPU 是下一代 AI GPU。"),
            claim("HBM4 是下一代高带宽内存技术。", "HBM4 是下一代高带宽内存技术。"),
        ],
        relation_candidates=[candidate(
            from_node_id, to_node_id, supporting_claim_refs=["C1", "C2"],
        )],
    ))
    request = cfg.root / "inbox" / "standard" / "negative.md"
    request.write_text(text, encoding="utf-8")

    result = pipeline.process_all()[0]

    assert result["status"] == "analyzed"
    assert result["relation_proposals"] == []
    assert result["rejected_relation_candidates"][0]["stage"] == "evidence"
    assert db.one("SELECT COUNT(*) AS n FROM node_relations")["n"] == 0
