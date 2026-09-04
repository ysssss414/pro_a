from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from pro_a.analyzer import Analyzer
from pro_a.llm import ChatLLM, LLMError
from pro_a.operational_ingestion import (
    RunPaths,
    _build_live_extraction,
    _fixture_raw_analysis,
    _record_failure,
)
from pro_a.parsers import ParsedSource
from pro_a.production_promotion import deterministic_id

from stability_helpers import make_config


class SequenceLLM:
    available = True

    def __init__(self, *responses):
        self.responses = list(responses)
        self.systems: list[str] = []
        self.users: list[str] = []
        self._last_call_metadata: dict = {}

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._last_call_metadata)

    def json(self, system, user):
        self.systems.append(system)
        self.users.append(user)
        response = self.responses.pop(0)
        self._last_call_metadata = {
            "attempts_used": 1,
            "attempts": [{"attempt_number": 1, "response_model": "fixture"}],
        }
        if isinstance(response, BaseException):
            raise response
        return copy.deepcopy(response)


def payload(*, matches=None, candidates=None, claims=None, relations=None):
    return {
        "source_metadata": {
            "title": "Piece-local fixture",
            "author": "",
            "organization": "",
            "publication_time": "2026-09-03",
            "source_rank": "A",
            "source_origin_type": "primary",
            "summary": "Controlled offline fixture",
        },
        "node_matches": matches or [],
        "node_candidates": candidates or [],
        "claims": claims or [],
        "relation_candidates": relations or [],
        "source_references": [],
    }


def fact_claim(statement: str, evidence: str, *, related_node_ids=None):
    return {
        "statement": statement,
        "nature": "fact",
        "related_node_ids": related_node_ids or [],
        "related_candidate_names": [],
        "fact_time": "2026-09-03",
        "evidence_pointer": "[[PARA:1]]",
        "evidence_excerpt": evidence,
        "attributed_to": "",
        "scope": "",
        "assumption": "",
        "status": "current",
        "confidence": 0.9,
        "novelty_level": "N2",
        "structured": {},
    }


def event_candidate(evidence: str):
    return {
        "canonical_name": "Event Z launch",
        "primary_type": "Event",
        "aliases": [],
        "description": "A discrete product launch",
        "suggested_parent_node_ids": [],
        "reason": "Controlled Event candidate",
        "confidence": 0.8,
        "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "Track a dated discrete launch",
        "is_discrete_event": True,
        "event_time": "2026-09-01",
        "evidence_excerpt": evidence,
        "long_term_research_value": False,
        "cross_source_or_node_value": False,
        "question": "",
        "importance": "",
        "what_would_change_my_mind": "",
    }


def relation(from_node_id: str, to_node_id: str):
    return {
        "from_node_id": from_node_id,
        "relation_type": "uses",
        "to_node_id": to_node_id,
        "scope": "",
        "supporting_claim_refs": ["C1"],
        "confidence": 0.9,
        "reason": "C1 explicitly states the relation",
    }


def analyze_pieces(monkeypatch, analyzer, pieces, responses):
    monkeypatch.setattr(
        "pro_a.analyzer.chunk_source_text", lambda text, max_chars: pieces
    )
    analyzer.llm = SequenceLLM(*responses)
    return analyzer.analyze_source("controlled.txt", "".join(pieces), "standard")


def prompt_catalog(user: str) -> list[dict]:
    catalog_text = user.split(
        "已存在 Knowledge Nodes（JSON）：\n", 1
    )[1].split("\n\n本次材料文本（仅基于此材料）：", 1)[0]
    return json.loads(catalog_text)


def test_other_piece_evidence_cannot_validate_match_claim_event_or_relation(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    alpha_id = db.add_node("Alpha", "Product")
    beta_id = db.add_node("Beta", "Technology")
    piece_a = "This piece contains unrelated local text."
    remote = "Alpha uses Beta. Event Z launched on 2026-09-01."
    response_a = payload(
        matches=[{
            "node_id": alpha_id,
            "role": "primary",
            "confidence": 0.9,
            "reason": "remote-only evidence",
            "evidence_excerpt": "Alpha uses Beta.",
        }],
        candidates=[event_candidate("Event Z launched on 2026-09-01.")],
        claims=[fact_claim(
            "Alpha uses Beta.", "Alpha uses Beta.",
            related_node_ids=[alpha_id, beta_id],
        )],
        relations=[relation(alpha_id, beta_id)],
    )
    analyzer = Analyzer(cfg, db)

    result = analyze_pieces(
        monkeypatch, analyzer, [piece_a, remote], [response_a, payload()]
    )

    assert result.node_matches == []
    assert result.rejected_node_matches[0]["validation"]["errors"] == [
        "evidence_excerpt_not_found"
    ]
    assert result.rejected_node_matches[0]["origin_chunk_index"] == 1
    assert result.claims[0]["evidence_validated"] is False
    assert result.claims[0]["status"] == "needs_review"
    assert result.claims[0]["confidence"] == 0.0
    assert result.claims[0]["origin_chunk_index"] == 1
    assert result.node_candidates == []
    rejected_event = result.rejected_node_candidates[0]
    assert rejected_event["event_evidence_validation"]["evidence_validated"] is False
    assert "event_evidence_excerpt_not_found" in rejected_event["quality_validation"]["errors"]
    assert result.relation_candidates == []
    assert result.rejected_relation_candidates[0]["reason"] == (
        "supporting Claim rejected: C1"
    )


def test_same_piece_positive_cases_preserve_existing_semantics_and_origins(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    alpha_id = db.add_node("Alpha", "Product")
    beta_id = db.add_node("Beta", "Technology")
    piece_a = "Alpha uses Beta. Event Z launched on 2026-09-01."
    response_a = payload(
        matches=[{
            "node_id": alpha_id,
            "role": "primary",
            "confidence": 0.9,
            "reason": "local evidence",
            "evidence_excerpt": "Alpha uses Beta.",
        }],
        candidates=[event_candidate("Event Z launched on 2026-09-01.")],
        claims=[fact_claim(
            "Alpha uses Beta.", "Alpha uses Beta.",
            related_node_ids=[alpha_id, beta_id],
        )],
        relations=[relation(alpha_id, beta_id)],
    )
    analyzer = Analyzer(cfg, db)

    result = analyze_pieces(
        monkeypatch, analyzer, [piece_a, "Unrelated second piece."],
        [response_a, payload()],
    )

    assert [item["node_id"] for item in result.node_matches] == [alpha_id]
    assert result.node_matches[0]["evidence_validated"] is True
    assert result.claims[0]["evidence_validated"] is True
    assert result.claims[0]["status"] == "current"
    assert result.claims[0]["related_node_ids"] == [alpha_id, beta_id]
    assert [item["canonical_name"] for item in result.node_candidates] == [
        "Event Z launch"
    ]
    assert result.relation_candidates[0]["relation_type"] == "uses"
    assert result.node_matches[0]["origin_chunk_index"] == 1
    assert result.claims[0]["origin_chunk_index"] == 1
    assert result.claims[0]["origin_piece_sha256"] == hashlib.sha256(
        piece_a.encode("utf-8")
    ).hexdigest()
    first_catalog = prompt_catalog(analyzer.llm.users[0])
    assert [node["node_id"] for node in first_catalog] == [alpha_id, beta_id]
    assert analyzer.last_piece_call_records[0]["full_prompt_catalog_count"] == 2
    assert analyzer.last_piece_call_records[0]["scoped_node_catalog_count"] == 2
    assert analyzer.last_piece_call_records[0]["scoped_node_ids"] == [
        alpha_id, beta_id,
    ]


def test_repeated_text_passes_in_its_origin_and_duplicate_merge_keeps_all_origins(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    alpha_id = db.add_node("Alpha", "Product")
    repeated = "Alpha demand increased."
    repeated_payload = payload(
        matches=[{
            "node_id": alpha_id,
            "role": "primary",
            "confidence": 0.9,
            "reason": "repeated local evidence",
            "evidence_excerpt": repeated,
        }],
        claims=[fact_claim(repeated, repeated, related_node_ids=[alpha_id])],
    )
    analyzer = Analyzer(cfg, db)

    result = analyze_pieces(
        monkeypatch,
        analyzer,
        [repeated, repeated],
        [repeated_payload, repeated_payload],
    )

    assert len(result.node_matches) == 1
    assert len(result.claims) == 1
    assert result.node_matches[0]["evidence_validated"] is True
    assert result.claims[0]["evidence_validated"] is True
    assert [
        item["origin_chunk_index"]
        for item in result.node_matches[0]["origin_pieces"]
    ] == [1, 2]
    assert [
        item["origin_chunk_index"] for item in result.claims[0]["origin_pieces"]
    ] == [1, 2]
    assert len({
        item["piece_id"] for item in result.claims[0]["origin_pieces"]
    }) == 2


def test_recursive_split_children_keep_distinct_piece_provenance(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    child_1 = "Child one evidence."
    child_2 = "Child two evidence."
    full_text = child_1 + child_2
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(
        LLMError("failure_category=output_truncation"),
        payload(claims=[
            fact_claim(child_1, child_1),
            fact_claim(child_2, child_2),
        ]),
        payload(claims=[fact_claim(child_2, child_2)]),
    )
    monkeypatch.setattr(
        "pro_a.analyzer.chunk_source_text", lambda text, max_chars: [full_text]
    )
    monkeypatch.setattr(
        "pro_a.analyzer.chunk_text", lambda text, max_chars: [child_1, child_2]
    )

    result = analyzer.analyze_source("recursive.txt", full_text, "standard")

    assert [claim["origin_split_path"] for claim in result.claims] == ["1", "1"]
    assert [claim["origin_chunk_index"] for claim in result.claims] == [1, 1]
    assert result.claims[0]["evidence_validated"] is True
    assert result.claims[1]["evidence_validated"] is False
    assert result.claims[1]["status"] == "needs_review"
    assert [
        origin["origin_split_path"]
        for origin in result.claims[1]["origin_pieces"]
    ] == ["1", "2"]
    assert [
        origin["evidence_validated"]
        for origin in result.claims[1]["origin_pieces"]
    ] == [False, True]
    assert [record["call_status"] for record in analyzer.last_piece_call_records] == [
        "failed", "success", "success"
    ]
    assert all(
        "full_prompt_catalog_count" in record
        and "scoped_node_catalog_count" in record
        for record in analyzer.last_piece_call_records
    )
    children = analyzer.last_piece_call_records[1:]
    assert [record["split_path"] for record in children] == ["1", "2"]
    assert [record["source_piece"]["text"] for record in children] == [
        child_1, child_2
    ]
    assert "[[TRUNCATION_SPLIT:1]]" in children[0]["prompt_piece"]["prefix"]
    assert "[[TRUNCATION_SPLIT:1]]" not in children[0]["source_piece"]["text"]
    assert children[0]["source_piece"]["sha256"] != children[1]["source_piece"]["sha256"]


def test_each_piece_catalog_is_scoped_without_full_source_leakage(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    alpha_id = db.add_node("Alpha", "Product")
    cxl_id = db.add_node("Compute Express Link", "Technology", ["CXL"])
    analyzer = Analyzer(cfg, db)

    analyze_pieces(
        monkeypatch,
        analyzer,
        ["Alpha is discussed here.", "Compute Express Link is discussed here."],
        [payload(), payload()],
    )

    assert len(analyzer.llm.users) == 2
    first, second = [prompt_catalog(user) for user in analyzer.llm.users]
    assert [node["node_id"] for node in first] == [alpha_id]
    assert cxl_id not in json.dumps(first, ensure_ascii=False)
    assert [node["node_id"] for node in second] == [cxl_id]
    assert [
        record["scoped_node_catalog_count"]
        for record in analyzer.last_piece_call_records
    ] == [1, 1]


def test_phase3e_raw_analysis_records_exact_piece_and_bundle_claim_origin(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    cfg.llm.enabled = True
    monkeypatch.setenv(cfg.llm.api_key_env, "offline-fixture-key")
    source_text = "Local evidence is visible."
    response = payload(claims=[fact_claim(source_text, source_text)])

    def offline_json(self: ChatLLM, system: str, user: str):
        self._attempt_events = [{
            "attempt_number": 1,
            "response_model": "offline-fixture",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }]
        return copy.deepcopy(response)

    monkeypatch.setattr(ChatLLM, "json", offline_json)
    parsed = ParsedSource(
        text=source_text,
        source_type="pdf",
        diagnostics={"partial_parse": False},
        segments=None,
        layout_sidecar={
            "adapter": "offline",
            "adapter_versions": {},
            "signature_sha256": "a" * 64,
            "segments": [],
        },
    )
    manifest = {
        "run_id": "INGEST_OFFLINE",
        "created_at": "2026-09-03T00:00:00+08:00",
        "source": {
            "source_id": "SRC_OFFLINE",
            "filename": "offline.pdf",
            "sha256": "b" * 64,
        },
    }

    raw, bundle = _build_live_extraction(
        cfg=cfg,
        manifest=manifest,
        parsed=parsed,
        production_path=cfg.db_path,
        layout_sidecar_relative="extraction/source_layout_sidecar.json",
    )

    call = raw["raw_model_responses"][0]
    assert raw["piece_local_equivalence"]["fixture_class"] == "A"
    assert call["source_piece"]["text"] == source_text
    assert call["source_piece"]["chars"] == len(source_text)
    assert call["source_piece"]["sha256"] == hashlib.sha256(
        source_text.encode("utf-8")
    ).hexdigest()
    prompt_piece_text = call["prompt_piece"]["prefix"] + call["source_piece"]["text"]
    assert prompt_piece_text == f"[[CHUNK:1/1]]\n{source_text}"
    assert call["prompt_piece"]["sha256"] == hashlib.sha256(
        prompt_piece_text.encode("utf-8")
    ).hexdigest()
    assert call["raw_model_json"] == response
    assert call["call_metadata"]["attempts"][0]["total_tokens"] == 30
    assert call["full_prompt_catalog_count"] == 0
    assert call["scoped_node_catalog_count"] == 0
    assert call["scoped_node_ids"] == []
    normalized_claim = raw["normalized_source_analysis"]["claims"][0]
    assert bundle["claims"][0]["origin_piece_sha256"] == normalized_claim[
        "origin_piece_sha256"
    ]
    semantic_claim = {
        key: value
        for key, value in normalized_claim.items()
        if not key.startswith("origin_")
    }
    assert bundle["claims"][0]["claim_id"] == deterministic_id(
        "CLM",
        {
            "source_sha256": manifest["source"]["sha256"],
            "claim_index": 0,
            "claim": semantic_claim,
        },
    )


def test_class_b_fixture_is_explicitly_not_piece_equivalence_proof():
    raw = _fixture_raw_analysis(
        {"run_id": "INGEST_B", "source": {"sha256": "c" * 64}},
        {"model": {}, "claims": [], "observations": {}},
        "d" * 64,
    )

    assert raw["piece_local_equivalence"] == {
        "fixture_class": "B",
        "status": "PIECE_LOCAL_EQUIVALENCE_NOT_DIRECTLY_PROVABLE_FROM_FIXTURE",
        "raw_response_and_exact_piece_available": False,
    }


def test_terminal_truncation_failure_receipt_keeps_compact_piece_identity(
    tmp_path: Path,
):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(LLMError("failure_category=output_truncation"))

    with pytest.raises(LLMError) as raised:
        analyzer.analyze_source("short.txt", "short piece", "standard")

    piece_context = raised.value.piece_context
    assert piece_context["chunk_index"] == 1
    assert piece_context["split_path"] == ""
    assert piece_context["source_piece_chars"] == len("short piece")
    assert piece_context["full_prompt_catalog_count"] == 0
    assert piece_context["scoped_node_catalog_count"] == 0
    assert piece_context["scoped_node_ids"] == []
    assert "source_text" not in piece_context
    paths = RunPaths(tmp_path / "run")
    paths.path("receipts").mkdir(parents=True)
    manifest = {
        "run_id": "INGEST_FAILURE",
        "source": {"sha256": "e" * 64},
    }
    _record_failure(paths, manifest, "EXTRACTION_FAILED", raised.value)
    receipt = json.loads(
        paths.path("receipts/extraction_failed.json").read_text(encoding="utf-8")
    )

    assert receipt["piece_context"] == piece_context
    assert "raw_model_json" not in receipt
    assert "source_piece" not in receipt


def test_frozen_acceptance_policy_blocks_adaptive_semantic_reextraction(
    tmp_path: Path,
):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(
        LLMError("failure_category=output_truncation"),
        payload(),
        payload(),
    )
    source = "独立句子。" * 1000

    with pytest.raises(LLMError, match="output_truncation"):
        analyzer.analyze_source(
            "acceptance.pdf",
            source,
            "deep",
            adaptive_retry_policy="forbid",
        )

    assert len(analyzer.llm.users) == 1
    assert len(analyzer.last_piece_call_records) == 1
    assert analyzer.last_piece_call_records[0]["adaptive_retry_policy"] == "forbid"
    assert analyzer.last_piece_call_records[0]["adaptive_retry_blocked"] is True


def test_frozen_acceptance_policy_preserves_normal_chunk_fan_out(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(payload(), payload())
    monkeypatch.setattr(
        "pro_a.analyzer.chunk_source_text",
        lambda text, max_chars: ["first normal chunk", "second normal chunk"],
    )

    analyzer.analyze_source(
        "acceptance.pdf",
        "first normal chunksecond normal chunk",
        "deep",
        adaptive_retry_policy="forbid",
    )

    assert len(analyzer.llm.users) == 2
    assert [row["chunk_index"] for row in analyzer.last_piece_call_records] == [1, 2]
    assert all(row["split_depth"] == 0 for row in analyzer.last_piece_call_records)


def test_frozen_acceptance_policy_preserves_identical_input_transport_retry_metadata(
    tmp_path: Path,
):
    class TransportRetryLLM(SequenceLLM):
        def json(self, system, user):
            result = super().json(system, user)
            self._last_call_metadata = {
                "attempts_used": 2,
                "attempts": [
                    {"attempt_number": 1, "result": "transport_error"},
                    {"attempt_number": 2, "result": "success"},
                ],
                "semantic_inputs_identical": True,
            }
            return result

    cfg, db = make_config(tmp_path)
    analyzer = Analyzer(cfg, db)
    analyzer.llm = TransportRetryLLM(payload())

    analyzer.analyze_source(
        "acceptance.pdf",
        "one fixed semantic input",
        "deep",
        adaptive_retry_policy="forbid",
    )

    assert len(analyzer.last_piece_call_records) == 1
    metadata = analyzer.last_piece_call_records[0]["call_metadata"]
    assert metadata["attempts_used"] == 2
    assert metadata["semantic_inputs_identical"] is True
