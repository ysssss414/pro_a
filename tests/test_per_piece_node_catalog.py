from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import pro_a.analyzer as analyzer_module
from pro_a.analyzer import Analyzer, scope_node_catalog
from pro_a.llm import LLMError
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM, SOURCE_ANALYSIS_USER

from stability_helpers import make_config


def payload(*, matches=None, candidates=None, claims=None, relations=None):
    return {
        "source_metadata": {
            "title": "Per-piece catalog fixture",
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


def prompt_catalog(user: str) -> list[dict]:
    catalog_text = user.split(
        "已存在 Knowledge Nodes（JSON）：\n", 1
    )[1].split("\n\n本次材料文本（仅基于此材料）：", 1)[0]
    return json.loads(catalog_text)


def fact_claim(statement: str, evidence: str, node_ids: list[str]):
    return {
        "statement": statement,
        "nature": "fact",
        "related_node_ids": node_ids,
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


def new_candidate(parent_ids: list[str]):
    return {
        "canonical_name": "Gamma accelerator",
        "primary_type": "Product",
        "aliases": [],
        "description": "A controlled new product candidate",
        "suggested_parent_node_ids": parent_ids,
        "reason": "Worth independent tracking",
        "confidence": 0.8,
        "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "Track product adoption over time",
        "is_discrete_event": False,
        "event_time": "",
        "evidence_excerpt": "",
        "long_term_research_value": True,
        "cross_source_or_node_value": True,
        "question": "",
        "importance": "",
        "what_would_change_my_mind": "",
    }


class SequenceLLM:
    available = True

    def __init__(self, *responses):
        self.responses = list(responses)
        self.users: list[str] = []
        self._last_call_metadata: dict = {}

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._last_call_metadata)

    def json(self, system, user):
        self.users.append(user)
        response = self.responses.pop(0)
        self._last_call_metadata = {
            "attempts_used": 1,
            "attempts": [{"attempt_number": 1, "finish_reason": "stop"}],
        }
        if isinstance(response, BaseException):
            raise response
        return copy.deepcopy(response)


def test_scope_node_catalog_uses_evidence_canonicalization_family_without_mutation():
    full_catalog = [
        {
            "node_id": "NODE_NFKC",
            "canonical_name": "Ａｌｐｈａ   Link",
            "primary_type": "Technology",
            "aliases": [],
        },
        {
            "node_id": "NODE_ALIAS",
            "canonical_name": "Compute Fabric",
            "primary_type": "Technology",
            "aliases": ["Memory   Pool"],
        },
        {
            "node_id": "NODE_MARKDOWN",
            "canonical_name": "HBM_4",
            "primary_type": "Product",
            "aliases": [],
        },
        {
            "node_id": "NODE_MISSING",
            "canonical_name": "Unmentioned Node",
            "primary_type": "Theme",
            "aliases": [],
        },
    ]
    before = copy.deepcopy(full_catalog)

    scoped = scope_node_catalog(
        full_catalog,
        "alpha link uses a Memory\n\tPool beside HBM\\_4.",
    )

    assert [node["node_id"] for node in scoped] == [
        "NODE_NFKC", "NODE_ALIAS", "NODE_MARKDOWN",
    ]
    assert scoped[0] is full_catalog[0]
    assert full_catalog == before
    assert scope_node_catalog(full_catalog, "No known term occurs here.") == []


def test_short_alias_keeps_existing_exact_substring_semantics():
    catalog = [{
        "node_id": "NODE_AI",
        "canonical_name": "Artificial Intelligence",
        "primary_type": "Technology",
        "aliases": ["AI"],
    }]

    assert scope_node_catalog(catalog, "SAIL platform") == catalog


def test_empty_scope_still_calls_model_and_keeps_new_candidate(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    db.add_node("Unmentioned Existing Node", "Technology")
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(payload(candidates=[new_candidate([])]))
    monkeypatch.setattr(
        analyzer_module, "chunk_source_text", lambda text, max_chars: [text]
    )

    result = analyzer.analyze_source(
        "empty-scope.txt", "Gamma accelerator is introduced.", "deep"
    )

    assert len(analyzer.llm.users) == 1
    assert prompt_catalog(analyzer.llm.users[0]) == []
    assert [item["canonical_name"] for item in result.node_candidates] == [
        "Gamma accelerator"
    ]
    assert analyzer.last_piece_call_records[0]["full_prompt_catalog_count"] == 1
    assert analyzer.last_piece_call_records[0]["scoped_node_catalog_count"] == 0


def test_recursive_truncation_children_rescope_from_full_catalog(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    terms = [
        "AlphaTerm", "BravoTerm", "CharlieTerm", "DeltaTerm",
        "EchoTerm", "FoxtrotTerm", "GolfTerm", "HotelTerm",
    ]
    node_ids = [db.add_node(term, "Technology") for term in terms]
    child_1 = " ".join(terms[:3])
    child_2 = " ".join(terms[3:])
    grandchild_1 = terms[0]
    grandchild_2 = " ".join(terms[1:3])
    parent = f"{child_1}\n{child_2}"
    analyzer = Analyzer(cfg, db)
    analyzer.llm = SequenceLLM(
        LLMError("failure_category=output_truncation"),
        LLMError("failure_category=output_truncation"),
        payload(), payload(), payload(),
    )
    monkeypatch.setattr(
        analyzer_module, "chunk_source_text", lambda text, max_chars: [parent]
    )

    def split_piece(text, max_chars):
        if text == parent:
            return [child_1, child_2]
        if text == child_1:
            return [grandchild_1, grandchild_2]
        raise AssertionError(f"unexpected recursive split: {text!r}")

    monkeypatch.setattr(analyzer_module, "chunk_text", split_piece)

    analyzer.analyze_source("recursive.txt", parent, "deep")

    catalogs = [prompt_catalog(user) for user in analyzer.llm.users]
    assert [[node["node_id"] for node in catalog] for catalog in catalogs] == [
        node_ids,
        node_ids[:3],
        node_ids[:1],
        node_ids[1:3],
        node_ids[3:],
    ]
    records = analyzer.last_piece_call_records
    assert [record["split_path"] for record in records] == [
        "", "1", "1.1", "1.2", "2",
    ]
    assert [record["scoped_node_catalog_count"] for record in records] == [
        8, 3, 1, 2, 5,
    ]
    assert [record["full_prompt_catalog_count"] for record in records] == [8] * 5
    assert [record["call_status"] for record in records] == [
        "failed", "failed", "success", "success", "success",
    ]


class ThresholdLLM:
    available = True

    def __init__(self, threshold: int):
        self.threshold = threshold
        self.catalog_counts: list[int] = []
        self._last_call_metadata: dict = {}

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._last_call_metadata)

    def json(self, system, user):
        count = len(prompt_catalog(user))
        self.catalog_counts.append(count)
        self._last_call_metadata = {
            "attempts_used": 1,
            "attempts": [{"attempt_number": 1, "finish_reason": "stop"}],
        }
        if count > self.threshold:
            raise LLMError("failure_category=output_truncation")
        return payload()


def test_scoping_avoids_catalog_cardinality_truncation_without_limit_changes(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    terms = [f"DistinctTerm{index}" for index in range(6)]
    for term in terms:
        db.add_node(term, "Technology")
    analyzer = Analyzer(cfg, db)
    analyzer.llm = ThresholdLLM(threshold=2)
    piece = f"{terms[0]} and {terms[1]} are discussed."
    max_output_tokens = cfg.llm.max_output_tokens

    old_equivalent_user = SOURCE_ANALYSIS_USER.format(
        mode="deep",
        filename="cardinality.txt",
        nodes_json=json.dumps(analyzer.node_catalog(), ensure_ascii=False),
        text=f"[[CHUNK:1/1]]\n{piece}",
    )
    with pytest.raises(LLMError, match="output_truncation"):
        analyzer.llm.json(SOURCE_ANALYSIS_SYSTEM, old_equivalent_user)

    monkeypatch.setattr(
        analyzer_module, "chunk_source_text", lambda text, max_chars: [piece]
    )
    analyzer.analyze_source("cardinality.txt", piece, "deep")

    assert analyzer.llm.catalog_counts == [6, 2]
    assert analyzer.last_piece_call_records[0]["call_status"] == "success"
    assert cfg.llm.max_output_tokens == max_output_tokens == 32768


class CatalogAwareLLM:
    available = True

    def __init__(self, alpha_id: str, beta_id: str, parent_id: str):
        self.alpha_id = alpha_id
        self.beta_id = beta_id
        self.parent_id = parent_id
        self.catalog_ids: list[list[str]] = []
        self._last_call_metadata: dict = {}

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._last_call_metadata)

    def json(self, system, user):
        catalog_ids = [node["node_id"] for node in prompt_catalog(user)]
        self.catalog_ids.append(catalog_ids)
        self._last_call_metadata = {
            "attempts_used": 1,
            "attempts": [{"attempt_number": 1, "finish_reason": "stop"}],
        }
        evidence = "Alpha uses Beta."
        return payload(
            matches=[{
                "node_id": self.alpha_id,
                "role": "primary",
                "confidence": 0.9,
                "reason": "locally explicit",
                "evidence_excerpt": evidence,
            }],
            candidates=[new_candidate(
                [self.parent_id] if self.parent_id in catalog_ids else []
            )],
            claims=[fact_claim(
                "Alpha uses Beta.", evidence, [self.alpha_id, self.beta_id]
            )],
            relations=[{
                "from_node_id": self.alpha_id,
                "relation_type": "uses",
                "to_node_id": self.beta_id,
                "scope": "",
                "supporting_claim_refs": ["C1"],
                "confidence": 0.9,
                "reason": "C1 directly states the relation",
            }],
        )


def authoritative_projection(result):
    return {
        "node_matches": [item["node_id"] for item in result.node_matches],
        "claim_node_ids": [
            item["related_node_ids"] for item in result.claims
            if item["evidence_validated"] is True
        ],
        "relations": [
            (
                item["from_node_id"], item["relation_type"],
                item["to_node_id"], item["supporting_claim_refs"],
            )
            for item in result.relation_candidates
        ],
        "new_nodes": [
            (item["canonical_name"], item["primary_type"], item["quality_eligible"])
            for item in result.node_candidates
        ],
    }


def test_controlled_authoritative_equivalence_allows_only_parent_advisory_change(
    tmp_path: Path, monkeypatch,
):
    cfg, db = make_config(tmp_path)
    alpha_id = db.add_node("Alpha", "Entity")
    beta_id = db.add_node("Beta", "Technology")
    parent_id = db.add_node("Hidden Parent", "Segment")
    piece = "Alpha uses Beta. Gamma accelerator is introduced."
    monkeypatch.setattr(
        analyzer_module, "chunk_source_text", lambda text, max_chars: [piece]
    )
    real_scope = analyzer_module.scope_node_catalog

    baseline = Analyzer(cfg, db)
    baseline.llm = CatalogAwareLLM(alpha_id, beta_id, parent_id)
    monkeypatch.setattr(
        analyzer_module,
        "scope_node_catalog",
        lambda full_prompt_catalog, piece_source_text: full_prompt_catalog,
    )
    baseline_result = baseline.analyze_source("equivalence.txt", piece, "deep")

    scoped = Analyzer(cfg, db)
    scoped.llm = CatalogAwareLLM(alpha_id, beta_id, parent_id)
    monkeypatch.setattr(analyzer_module, "scope_node_catalog", real_scope)
    scoped_result = scoped.analyze_source("equivalence.txt", piece, "deep")

    assert set(baseline.llm.catalog_ids[0]) == {alpha_id, beta_id, parent_id}
    assert scoped.llm.catalog_ids == [[
        node_id for node_id in baseline.llm.catalog_ids[0]
        if node_id != parent_id
    ]]
    assert authoritative_projection(scoped_result) == authoritative_projection(
        baseline_result
    )
    assert baseline_result.node_candidates[0]["suggested_parent_node_ids"] == [
        parent_id
    ]
    assert scoped_result.node_candidates[0]["suggested_parent_node_ids"] == []
    assert scoped_result.node_candidates[0]["quality_eligible"] is True
    assert scoped_result.node_matches[0]["evidence_validated"] is True
    assert scoped_result.claims[0]["related_node_ids"] == [alpha_id, beta_id]
    assert len(scoped_result.relation_candidates) == 1
