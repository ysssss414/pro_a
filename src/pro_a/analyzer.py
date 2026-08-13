from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .config import AppConfig
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
                claim["evidence_validated"] = evidence_found(str(claim.get("evidence_excerpt", "")), text)
                if not claim["evidence_validated"]:
                    claim["status"] = "needs_review"
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
        return self.llm.json(CLAIM_COMPARE_SYSTEM, user)

    def review_impact(self, node: dict[str, Any], current_view_md: str, evidence: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            raise LLMError("LLM unavailable")
        user = IMPACT_USER.format(
            node_json=json.dumps(node, ensure_ascii=False),
            current_view=current_view_md or "<NO_CURRENT_VIEW>",
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            context_json=json.dumps(context, ensure_ascii=False),
        )
        return self.llm.json(IMPACT_SYSTEM, user)
