from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any

from .config import AppConfig
from .constants import (
    CHANGE_LEVELS, CLAIM_NATURES, CLAIM_STATUSES, NODE_TYPES, NOVELTY_LEVELS,
    SOURCE_ORIGIN_TYPES, SOURCE_RANKS,
)
from .db import Database
from .llm import ChatLLM, LLMError
from .parsers import chunk_text
from .prompts import (
    CLAIM_COMPARE_SYSTEM, CLAIM_COMPARE_USER, IMPACT_SYSTEM, IMPACT_USER,
    SOURCE_ANALYSIS_SYSTEM, SOURCE_ANALYSIS_USER,
)


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def evidence_found(excerpt: str, full_text: str) -> bool:
    e = normalize_ws(excerpt)
    t = normalize_ws(full_text)
    if not e:
        return False
    if e in t:
        return True
    # tolerate punctuation/space differences for Chinese/English mixed text
    strip = lambda x: re.sub(r"[\s\u3000，。；：、,.!?;:'\"“”‘’()（）\[\]【】]+", "", x)
    es, ts = strip(excerpt), strip(full_text)
    return bool(es and es in ts)


@dataclass
class SourceAnalysis:
    source_metadata: dict[str, Any]
    node_matches: list[dict[str, Any]]
    node_candidates: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    source_references: list[dict[str, Any]]


class Analyzer:
    def __init__(self, cfg: AppConfig, db: Database):
        self.cfg = cfg
        self.db = db
        self.llm = ChatLLM(cfg.llm)

    @property
    def available(self) -> bool:
        return self.llm.available

    def node_catalog(self) -> list[dict[str, Any]]:
        rows = self.db.list_nodes(self.cfg.llm.max_nodes_in_prompt)
        return [
            {"node_id": r["node_id"], "canonical_name": r["canonical_name"], "primary_type": r["primary_type"], "aliases": r.get("aliases", [])}
            for r in rows
        ]

    @staticmethod
    def _invalid(path: str, message: str) -> None:
        raise LLMError(f"Invalid LLM output at {path}: {message}")

    def _object(self, value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            self._invalid(path, "expected an object")
        return value

    def _list(self, value: Any, path: str) -> list[Any]:
        if not isinstance(value, list):
            self._invalid(path, "expected an array")
        return value

    def _confidence(self, item: dict[str, Any], path: str) -> float:
        if "confidence" not in item:
            self._invalid(f"{path}.confidence", "field is required")
        value = item.get("confidence")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self._invalid(f"{path}.confidence", "must be a number between 0 and 1")
        value = float(value)
        if not 0.0 <= value <= 1.0:
            self._invalid(f"{path}.confidence", "must be between 0 and 1")
        item["confidence"] = value
        return value

    def _node_ids(self, value: Any, path: str) -> list[str]:
        ids = self._list(value, path)
        for index, node_id in enumerate(ids):
            if not isinstance(node_id, str) or not node_id.strip():
                self._invalid(f"{path}[{index}]", "must be a non-empty Node ID")
            if not self.db.get_node(node_id):
                self._invalid(f"{path}[{index}]", f"unknown Node ID {node_id!r}")
        return ids

    def _claim_ids(self, value: Any, allowed: set[str], path: str) -> list[str]:
        ids = self._list(value, path)
        for index, claim_id in enumerate(ids):
            if not isinstance(claim_id, str) or claim_id not in allowed:
                self._invalid(f"{path}[{index}]", f"unknown Claim ID {claim_id!r}")
        return ids

    def _validate_source_output(self, raw: Any, full_text: str) -> dict[str, Any]:
        data = copy.deepcopy(self._object(raw, "source_analysis"))
        metadata = self._object(data.get("source_metadata") or {}, "source_metadata")
        metadata["source_rank"] = metadata.get("source_rank") or "UNRANKED"
        metadata["source_origin_type"] = metadata.get("source_origin_type") or "unknown"
        if metadata["source_rank"] not in SOURCE_RANKS:
            self._invalid("source_metadata.source_rank", f"unsupported value {metadata['source_rank']!r}")
        if metadata["source_origin_type"] not in SOURCE_ORIGIN_TYPES:
            self._invalid(
                "source_metadata.source_origin_type",
                f"unsupported value {metadata['source_origin_type']!r}",
            )
        data["source_metadata"] = metadata

        matches = self._list(data.get("node_matches") or [], "node_matches")
        for index, match in enumerate(matches):
            path = f"node_matches[{index}]"
            match = self._object(match, path)
            node_id = match.get("node_id")
            if not isinstance(node_id, str) or not self.db.get_node(node_id):
                self._invalid(f"{path}.node_id", f"unknown Node ID {node_id!r}")
            role = match.get("role") or "related"
            if role not in {"primary", "related"}:
                self._invalid(f"{path}.role", f"unsupported value {role!r}")
            match["role"] = role
            self._confidence(match, path)

        candidates = self._list(data.get("node_candidates") or [], "node_candidates")
        for index, candidate in enumerate(candidates):
            path = f"node_candidates[{index}]"
            candidate = self._object(candidate, path)
            if not normalize_ws(str(candidate.get("canonical_name") or "")):
                self._invalid(f"{path}.canonical_name", "field is required")
            primary_type = candidate.get("primary_type")
            if primary_type not in NODE_TYPES:
                self._invalid(f"{path}.primary_type", f"unsupported Node Type {primary_type!r}")
            kind = candidate.get("candidate_kind") or "normal"
            if kind not in {"normal", "research_question"}:
                self._invalid(f"{path}.candidate_kind", f"unsupported value {kind!r}")
            if (kind == "research_question") != (primary_type == "ResearchQuestion"):
                self._invalid(path, "ResearchQuestion type and candidate_kind must agree")
            candidate["candidate_kind"] = kind
            self._confidence(candidate, path)
            self._list(candidate.get("aliases") or [], f"{path}.aliases")
            self._node_ids(
                candidate.get("suggested_parent_node_ids") or [],
                f"{path}.suggested_parent_node_ids",
            )

        claims = self._list(data.get("claims") or [], "claims")
        for index, claim in enumerate(claims):
            path = f"claims[{index}]"
            claim = self._object(claim, path)
            if not normalize_ws(str(claim.get("statement") or "")):
                self._invalid(f"{path}.statement", "field is required")
            nature = claim.get("nature") or "fact"
            status = claim.get("status") or "current"
            novelty = claim.get("novelty_level") or "N2"
            if nature not in CLAIM_NATURES:
                self._invalid(f"{path}.nature", f"unsupported value {nature!r}")
            if status not in CLAIM_STATUSES:
                self._invalid(f"{path}.status", f"unsupported value {status!r}")
            if novelty not in NOVELTY_LEVELS:
                self._invalid(f"{path}.novelty_level", f"unsupported value {novelty!r}")
            claim["nature"] = nature
            claim["status"] = status
            claim["novelty_level"] = novelty
            model_confidence = self._confidence(claim, path)
            self._node_ids(claim.get("related_node_ids") or [], f"{path}.related_node_ids")
            self._list(claim.get("related_candidate_names") or [], f"{path}.related_candidate_names")
            self._object(claim.get("structured") or {}, f"{path}.structured")
            validated = evidence_found(str(claim.get("evidence_excerpt") or ""), full_text)
            errors = [] if validated else ["evidence_excerpt_not_found"]
            claim["evidence_validated"] = validated
            claim["validation"] = {
                "evidence_validated": validated,
                "model_confidence": model_confidence,
                "errors": errors,
            }
            if not validated:
                claim["status"] = "needs_review"
                claim["confidence"] = 0.0

        references = self._list(data.get("source_references") or [], "source_references")
        for index, reference in enumerate(references):
            self._object(reference, f"source_references[{index}]")
        return data

    def _validate_compare_output(
        self, raw: Any, new_claims: list[dict[str, Any]], history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        data = copy.deepcopy(self._object(raw, "claim_compare"))
        new_ids = {item["claim_id"] for item in new_claims}
        history_ids = {item["claim_id"] for item in history}
        comparisons = self._list(data.get("comparisons") or [], "comparisons")
        for index, comparison in enumerate(comparisons):
            path = f"comparisons[{index}]"
            comparison = self._object(comparison, path)
            new_id = comparison.get("new_claim_id")
            classification = comparison.get("classification")
            related_id = comparison.get("related_claim_id") or ""
            if new_id not in new_ids:
                self._invalid(f"{path}.new_claim_id", f"unknown new Claim ID {new_id!r}")
            if classification not in {"new", "corroborates", "updates", "contradicts", "duplicate"}:
                self._invalid(f"{path}.classification", f"unsupported value {classification!r}")
            if classification != "new" and related_id not in history_ids:
                self._invalid(f"{path}.related_claim_id", f"unknown historical Claim ID {related_id!r}")
            if "independent_evidence" in comparison and not isinstance(comparison["independent_evidence"], bool):
                self._invalid(f"{path}.independent_evidence", "must be boolean")
        return data

    def _validate_impact_output(self, raw: Any, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        data = copy.deepcopy(self._object(raw, "impact_review"))
        requires_change = data.get("requires_change")
        if not isinstance(requires_change, bool):
            self._invalid("impact_review.requires_change", "must be boolean")
        level = data.get("change_level") or "none"
        if level not in {*CHANGE_LEVELS, "none"}:
            self._invalid("impact_review.change_level", f"unsupported value {level!r}")
        if requires_change and level == "none":
            self._invalid("impact_review.change_level", "cannot be none when requires_change is true")
        if not requires_change and level != "none":
            self._invalid("impact_review.change_level", "must be none when requires_change is false")
        data["change_level"] = level
        evidence_ids = {str(item["claim_id"]) for item in evidence if item.get("claim_id")}
        sufficiency = self._object(data.get("evidence_sufficiency") or {}, "evidence_sufficiency")
        for key in ("direct_primary_claim_ids", "decisive_primary_claim_ids"):
            self._claim_ids(sufficiency.get(key) or [], evidence_ids, f"evidence_sufficiency.{key}")
        proposed = self._object(data.get("proposed_current_view") or {}, "proposed_current_view")
        self._claim_ids(
            proposed.get("evidence_claim_ids") or [], evidence_ids,
            "proposed_current_view.evidence_claim_ids",
        )
        gaps = self._list(data.get("knowledge_gaps") or [], "knowledge_gaps")
        for index, gap in enumerate(gaps):
            gap = self._object(gap, f"knowledge_gaps[{index}]")
            self._claim_ids(
                gap.get("source_claim_ids") or [], evidence_ids,
                f"knowledge_gaps[{index}].source_claim_ids",
            )
        candidates = self._list(
            data.get("research_question_candidates") or [], "research_question_candidates"
        )
        for index, candidate in enumerate(candidates):
            candidate = self._object(candidate, f"research_question_candidates[{index}]")
            self._node_ids(
                candidate.get("related_node_ids") or [],
                f"research_question_candidates[{index}].related_node_ids",
            )
        return data

    def analyze_source(self, filename: str, text: str, mode: str) -> SourceAnalysis:
        if not self.available:
            raise LLMError("LLM unavailable")
        chunks = chunk_text(text, self.cfg.llm.max_chunk_chars)
        catalog_json = json.dumps(self.node_catalog(), ensure_ascii=False)
        merged = {
            "source_metadata": {}, "node_matches": [], "node_candidates": [], "claims": [], "source_references": []
        }
        seen_claims: set[str] = set()
        seen_matches: set[str] = set()
        seen_candidates: set[str] = set()
        for idx, chunk in enumerate(chunks, 1):
            user = SOURCE_ANALYSIS_USER.format(
                mode=mode,
                filename=filename,
                nodes_json=catalog_json,
                text=f"[[CHUNK:{idx}/{len(chunks)}]]\n{chunk}",
            )
            data = self.llm.json(SOURCE_ANALYSIS_SYSTEM, user)
            data = self._validate_source_output(data, text)
            if idx == 1:
                merged["source_metadata"] = data.get("source_metadata") or {}
            for m in data.get("node_matches") or []:
                key = str(m.get("node_id", ""))
                if key and key not in seen_matches:
                    seen_matches.add(key)
                    merged["node_matches"].append(m)
            for c in data.get("node_candidates") or []:
                key = normalize_ws(str(c.get("canonical_name", ""))).lower()
                if key and key not in seen_candidates:
                    seen_candidates.add(key)
                    merged["node_candidates"].append(c)
            for claim in data.get("claims") or []:
                statement = normalize_ws(str(claim.get("statement", "")))
                key = statement.lower()
                if not statement or key in seen_claims:
                    continue
                seen_claims.add(key)
                merged["claims"].append(claim)
            merged["source_references"].extend(data.get("source_references") or [])
        return SourceAnalysis(**merged)


    def compare_claims(self, node: dict[str, Any], new_claims: list[dict[str, Any]], history: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.available:
            raise LLMError("LLM unavailable")
        user = CLAIM_COMPARE_USER.format(
            node_json=json.dumps(node, ensure_ascii=False),
            new_claims_json=json.dumps(new_claims, ensure_ascii=False),
            history_json=json.dumps(history, ensure_ascii=False),
        )
        data = self.llm.json(CLAIM_COMPARE_SYSTEM, user)
        return self._validate_compare_output(data, new_claims, history)

    def review_impact(self, node: dict[str, Any], current_view_md: str, evidence: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            raise LLMError("LLM unavailable")
        user = IMPACT_USER.format(
            node_json=json.dumps(node, ensure_ascii=False),
            current_view=current_view_md or "<NO_CURRENT_VIEW>",
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            context_json=json.dumps(context, ensure_ascii=False),
        )
        data = self.llm.json(IMPACT_SYSTEM, user)
        return self._validate_impact_output(data, evidence)
