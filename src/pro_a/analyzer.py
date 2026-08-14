from __future__ import annotations

import copy
import json
import re
import unicodedata
from dataclasses import dataclass, field
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
    CANDIDATE_BACKFILL_SYSTEM, CANDIDATE_BACKFILL_USER,
    CLAIM_COMPARE_SYSTEM, CLAIM_COMPARE_USER, IMPACT_SYSTEM, IMPACT_USER,
    SOURCE_ANALYSIS_SYSTEM, SOURCE_ANALYSIS_USER,
)


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


_MARKDOWN_ESCAPABLE = frozenset(r"\`*_{}[]()#+-.!|>~&")
_NON_DISCRETE_EVENT_TERMS = ("模式", "机制", "策略", "计划", "状态", "周期", "趋势", "挤兑")
_DEFAULT_NON_NODE_NAME_TERMS = (
    "经营计划", "扩产计划", "产能计划", "价格策略", "调价模式", "供需机制",
    "周期", "产能挤兑",
)
_ATTRIBUTED_NATURES = {
    "company_guidance", "expert_judgment", "broker_forecast", "market_rumor",
    "user_judgment", "ai_inference",
}
_ATTRIBUTION_SUFFIXES = ("业绩说明会", "管理层", "公司方面", "公司")
_FUTURE_OR_JUDGMENT_RE = re.compile(
    r"预计|预期|计划|目标|指引|展望|看好|认为|判断|可能|有望|拟|将(?:于|在)?|"
    r"expected|forecast|guidance|target|will",
    re.IGNORECASE,
)
_MIXED_ACTUAL_GUIDANCE_SPLIT_RE = re.compile(
    r"[，,；;]\s*(?=预计|预期|计划|目标|指引|展望|拟|将(?:于|在)?|"
    r"expected|forecast|guidance|target|will)",
    re.IGNORECASE,
)
_ACTUAL_OBSERVATION_RE = re.compile(
    r"当前|目前|截至|现有|当月|本月|单月|实际|已经|已完成|\d",
    re.IGNORECASE,
)


def canonicalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")

    def restore_markdown_escape(match: re.Match[str]) -> str:
        char = match.group(1)
        return char if char in _MARKDOWN_ESCAPABLE else match.group(0)

    normalized = re.sub(r"\\(.)", restore_markdown_escape, normalized)
    return normalize_ws(normalized)


def evidence_match(excerpt: str, full_text: str) -> dict[str, Any]:
    normalized_excerpt = canonicalize_text(excerpt)
    normalized_text = canonicalize_text(full_text)
    start = normalized_text.find(normalized_excerpt) if normalized_excerpt else -1
    validated = start >= 0
    return {
        "evidence_validated": validated,
        "canonicalization": "unicode_nfkc+markdown_unescape+whitespace",
        "match_method": "normalized_exact_substring",
        "normalized_excerpt": normalized_excerpt,
        "normalized_start": start,
        "normalized_end": start + len(normalized_excerpt) if validated else -1,
    }


def attribution_subjects(attributed_to: str) -> list[str]:
    full = canonicalize_text(attributed_to)
    subjects = [full] if full else []
    shortened = re.sub(r"\([^()]{1,30}\)$", "", full).strip()
    changed = True
    while shortened and changed:
        changed = False
        for suffix in _ATTRIBUTION_SUFFIXES:
            if shortened.endswith(suffix) and len(shortened) > len(suffix):
                shortened = shortened[:-len(suffix)].strip()
                changed = True
                break
    if shortened and shortened not in subjects:
        subjects.append(shortened)
    return subjects


@dataclass
class SourceAnalysis:
    source_metadata: dict[str, Any]
    node_matches: list[dict[str, Any]]
    node_candidates: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    source_references: list[dict[str, Any]]
    rejected_node_matches: list[dict[str, Any]] = field(default_factory=list)
    rejected_node_candidates: list[dict[str, Any]] = field(default_factory=list)
    rejected_claim_node_links: list[dict[str, Any]] = field(default_factory=list)


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

    @staticmethod
    def _candidate_quality(
        candidate: dict[str, Any], full_text: str, source_rank: str
    ) -> dict[str, Any]:
        errors: list[str] = []
        primary_type = candidate.get("primary_type")
        if primary_type == "ResearchQuestion":
            return {"eligible": True, "errors": []}
        if candidate.get("independent_research_value") is not True:
            errors.append("independent_research_value_not_confirmed")
        if not normalize_ws(str(candidate.get("maintenance_rationale") or "")):
            errors.append("maintenance_rationale_missing")
        if source_rank not in {"S", "A", "B"}:
            errors.append("source_not_high_quality_for_first_node")
        candidate_name = normalize_ws(str(candidate.get("canonical_name") or ""))
        if any(term in candidate_name for term in _DEFAULT_NON_NODE_NAME_TERMS):
            errors.append("candidate_is_plan_strategy_mechanism_or_state")
        if primary_type == "Event":
            name = candidate_name
            description = normalize_ws(str(candidate.get("description") or ""))
            if any(term in f"{name} {description}" for term in _NON_DISCRETE_EVENT_TERMS):
                errors.append("event_is_mechanism_strategy_plan_or_state")
            if candidate.get("is_discrete_event") is not True:
                errors.append("event_not_discrete")
            if not normalize_ws(str(candidate.get("event_time") or "")):
                errors.append("event_time_missing")
            event_validation = evidence_match(
                str(candidate.get("evidence_excerpt") or ""), full_text
            )
            candidate["event_evidence_validation"] = event_validation
            if not event_validation["evidence_validated"]:
                errors.append("event_evidence_excerpt_not_found")
        if primary_type == "Theme":
            if candidate.get("long_term_research_value") is not True:
                errors.append("theme_lacks_long_term_research_value")
            if candidate.get("cross_source_or_node_value") is not True:
                errors.append("theme_lacks_cross_source_or_node_value")
        return {"eligible": not errors, "errors": errors}

    @staticmethod
    def _atomic_statement(claim: dict[str, Any], fragment: str) -> str:
        statement = normalize_ws(fragment).strip("，,；;。 ")
        structured = claim.get("structured") or {}
        company = canonicalize_text(str(structured.get("company") or ""))
        metric = canonicalize_text(str(structured.get("metric") or ""))
        prefix = ""
        if company and company not in statement:
            prefix += company
        if metric and metric not in statement:
            prefix += metric
        return f"{prefix}{statement}。"

    @classmethod
    def _normalize_claim_atomicity(cls, claims: list[Any]) -> list[Any]:
        normalized: list[Any] = []
        for item in claims:
            if not isinstance(item, dict):
                normalized.append(item)
                continue
            if not isinstance(item.get("structured") or {}, dict):
                normalized.append(item)
                continue
            statement = canonicalize_text(str(item.get("statement") or ""))
            if item.get("nature") != "company_guidance":
                normalized.append(item)
                continue

            split = _MIXED_ACTUAL_GUIDANCE_SPLIT_RE.search(statement)
            actual_text = statement[:split.start()] if split else ""
            future_text = statement[split.end():] if split else ""
            if (
                split
                and _ACTUAL_OBSERVATION_RE.search(actual_text)
                and _FUTURE_OR_JUDGMENT_RE.search(future_text)
            ):
                for segment, fragment, nature in (
                    ("actual", actual_text, "data" if re.search(r"\d", actual_text) else "fact"),
                    ("guidance", future_text, "company_guidance"),
                ):
                    atomic = copy.deepcopy(item)
                    atomic["statement"] = cls._atomic_statement(atomic, fragment)
                    atomic["nature"] = nature
                    structured = dict(atomic.get("structured") or {})
                    structured["claim_normalization"] = {
                        "method": "mixed_actual_guidance_split",
                        "segment": segment,
                        "original_statement": str(item.get("statement") or ""),
                    }
                    atomic["structured"] = structured
                    normalized.append(atomic)
                continue

            if not _FUTURE_OR_JUDGMENT_RE.search(statement) and _ACTUAL_OBSERVATION_RE.search(statement):
                item["nature"] = "data" if re.search(r"\d", statement) else "fact"
                structured = dict(item.get("structured") or {})
                structured["claim_normalization"] = {
                    "method": "actual_observation_nature_correction",
                    "raw_nature": "company_guidance",
                    "normalized_nature": item["nature"],
                }
                item["structured"] = structured
            normalized.append(item)
        return normalized

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
            model_confidence = self._confidence(match, path)
            excerpt = match.get("evidence_excerpt")
            if not isinstance(excerpt, str) or not normalize_ws(excerpt):
                self._invalid(f"{path}.evidence_excerpt", "field is required")
            validation = evidence_match(excerpt, full_text)
            excerpt_located = validation["evidence_validated"]
            node = self.db.get_node(node_id) or {}
            node_terms = [node.get("canonical_name") or "", *(node.get("aliases") or [])]
            normalized_excerpt = validation["normalized_excerpt"]
            node_name_or_alias_found = any(
                canonicalize_text(term) in normalized_excerpt
                for term in node_terms if canonicalize_text(term)
            )
            validation["excerpt_located"] = excerpt_located
            validation["node_name_or_alias_found"] = node_name_or_alias_found
            validation["evidence_validated"] = excerpt_located and node_name_or_alias_found
            validation["model_confidence"] = model_confidence
            validation["errors"] = (
                [] if validation["evidence_validated"] else [
                    "node_name_or_alias_not_in_evidence"
                    if excerpt_located else "evidence_excerpt_not_found"
                ]
            )
            match["evidence_validated"] = validation["evidence_validated"]
            match["validation"] = validation

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
            quality = self._candidate_quality(
                candidate, full_text, str(metadata.get("source_rank") or "UNRANKED"),
            )
            candidate["quality_eligible"] = quality["eligible"]
            candidate["quality_validation"] = quality

        claims = self._normalize_claim_atomicity(
            self._list(data.get("claims") or [], "claims")
        )
        data["claims"] = claims
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
            if "attributed_to" not in claim or not isinstance(claim.get("attributed_to"), str):
                self._invalid(f"{path}.attributed_to", "field is required and must be a string")
            attributed_to = normalize_ws(claim.get("attributed_to") or "")
            claim["attributed_to"] = attributed_to
            scope = normalize_ws(str(claim.get("scope") or ""))
            statement = canonicalize_text(str(claim.get("statement") or ""))
            structured = self._object(claim.get("structured") or {}, f"{path}.structured")
            structured_company = canonicalize_text(str(structured.get("company") or ""))
            company_scope = (
                nature == "company_guidance" or "公司" in scope or "企业" in scope
                or bool(structured_company)
            )
            requires_attribution = company_scope or nature in _ATTRIBUTED_NATURES
            if requires_attribution and not attributed_to:
                self._invalid(f"{path}.attributed_to", "attribution is required")
            subjects = attribution_subjects(attributed_to)
            statement_subjects = [structured_company] if structured_company else subjects
            has_explicit_noncompany_attribution = (
                not company_scope
                and bool(re.match(r"^.{1,40}(?:认为|判断|指出|表示|披露|称|预计)", statement))
            )
            if (
                requires_attribution
                and not any(subject in statement for subject in statement_subjects)
                and not has_explicit_noncompany_attribution
            ):
                raw_statement = str(claim.get("statement") or "")
                normalized_subject = structured_company or (subjects[-1] if subjects else attributed_to)
                if company_scope and "公司" in raw_statement:
                    normalized_statement = raw_statement.replace("公司", normalized_subject, 1)
                elif company_scope:
                    normalized_statement = f"{normalized_subject}{raw_statement}"
                else:
                    normalized_statement = f"{attributed_to}判断，{raw_statement}"
                claim["statement"] = normalize_ws(normalized_statement)
                claim["statement_normalization"] = {
                    "raw_statement": raw_statement,
                    "attribution_injected": True,
                    "attributed_to": attributed_to,
                    "method": "deterministic_attribution_prefix_or_company_replacement",
                }
            related_node_ids = self._node_ids(
                claim.get("related_node_ids") or [], f"{path}.related_node_ids"
            )
            self._list(claim.get("related_candidate_names") or [], f"{path}.related_candidate_names")
            validation = evidence_match(str(claim.get("evidence_excerpt") or ""), full_text)
            validated = validation["evidence_validated"]
            errors = [] if validated else ["evidence_excerpt_not_found"]
            claim["evidence_validated"] = validated
            claim["validation"] = {
                **validation, "model_confidence": model_confidence, "errors": errors,
            }
            if not validated:
                claim["status"] = "needs_review"
                claim["confidence"] = 0.0
            accepted_node_ids: list[str] = []
            rejected_node_links: list[dict[str, Any]] = []
            for node_id in related_node_ids:
                node = self.db.get_node(node_id) or {}
                node_terms = [node.get("canonical_name") or "", *(node.get("aliases") or [])]
                explicit = validated and any(
                    canonicalize_text(term) in validation["normalized_excerpt"]
                    for term in node_terms if canonicalize_text(term)
                )
                if explicit:
                    accepted_node_ids.append(node_id)
                else:
                    rejected_node_links.append({
                        "claim_statement": str(claim.get("statement") or ""),
                        "node_id": node_id,
                        "evidence_excerpt": str(claim.get("evidence_excerpt") or ""),
                        "reason": (
                            "node_name_or_alias_not_in_evidence"
                            if validated else "evidence_excerpt_not_found"
                        ),
                    })
            claim["related_node_ids"] = accepted_node_ids
            claim["rejected_related_node_links"] = rejected_node_links

        references = self._list(data.get("source_references") or [], "source_references")
        for index, reference in enumerate(references):
            self._object(reference, f"source_references[{index}]")
        return data

    def backfill_candidate_claims(
        self, candidates: list[dict[str, Any]], claims: list[dict[str, Any]]
    ) -> dict[str, list[int]]:
        candidate_by_key = {
            normalize_ws(str(candidate.get("canonical_name") or "")).lower(): candidate
            for candidate in candidates
            if candidate.get("quality_eligible") is True
        }
        mapping = {key: [] for key in candidate_by_key}
        eligible_claims = [
            (index, item) for index, item in enumerate(claims)
            if item.get("evidence_validated") is True and item.get("status") != "needs_review"
        ]
        if not candidate_by_key or not eligible_claims:
            return mapping
        claim_refs = {f"C{index + 1}": index for index, _ in eligible_claims}
        user = CANDIDATE_BACKFILL_USER.format(
            candidates_json=json.dumps(list(candidate_by_key.values()), ensure_ascii=False),
            claims_json=json.dumps([
                {
                    "claim_ref": ref,
                    "statement": claims[index].get("statement", ""),
                    "attributed_to": claims[index].get("attributed_to", ""),
                    "evidence_excerpt": claims[index].get("evidence_excerpt", ""),
                    "scope": claims[index].get("scope", ""),
                    "structured": claims[index].get("structured") or {},
                    "initial_related_candidate_names": claims[index].get("related_candidate_names") or [],
                }
                for ref, index in claim_refs.items()
            ], ensure_ascii=False),
        )
        raw = self.llm.json(CANDIDATE_BACKFILL_SYSTEM, user)
        data = self._object(raw, "candidate_claim_backfill")
        links = self._list(data.get("candidate_claim_links"), "candidate_claim_links")
        seen: set[str] = set()
        for index, link in enumerate(links):
            path = f"candidate_claim_links[{index}]"
            link = self._object(link, path)
            name = normalize_ws(str(link.get("candidate_name") or ""))
            key = name.lower()
            if key not in candidate_by_key:
                self._invalid(f"{path}.candidate_name", f"unknown Candidate Node {name!r}")
            if key in seen:
                self._invalid(f"{path}.candidate_name", f"duplicate Candidate Node {name!r}")
            seen.add(key)
            refs = self._list(link.get("related_claim_refs"), f"{path}.related_claim_refs")
            resolved: list[int] = []
            for ref_index, ref in enumerate(refs):
                if ref not in claim_refs:
                    self._invalid(
                        f"{path}.related_claim_refs[{ref_index}]", f"unknown validated Claim ref {ref!r}",
                    )
                if claim_refs[ref] not in resolved:
                    resolved.append(claim_refs[ref])
            mapping[key] = resolved
        missing = set(candidate_by_key) - seen
        if missing:
            self._invalid(
                "candidate_claim_links", "missing Candidate Nodes: " + ", ".join(sorted(missing)),
            )
        candidate_aliases: dict[str, str] = {}
        for key, candidate in candidate_by_key.items():
            for name in [candidate.get("canonical_name") or "", *(candidate.get("aliases") or [])]:
                alias = canonicalize_text(str(name)).lower()
                if alias:
                    candidate_aliases[alias] = key
        for claim_index, claim in eligible_claims:
            for name in claim.get("related_candidate_names") or []:
                key = candidate_aliases.get(canonicalize_text(str(name)).lower())
                if key and claim_index not in mapping[key]:
                    mapping[key].append(claim_index)
        canonical_by_key = {
            key: canonicalize_text(str(candidate.get("canonical_name") or "")).lower()
            for key, candidate in candidate_by_key.items()
        }
        for broad_key, broad_name in canonical_by_key.items():
            if not broad_name:
                continue
            for specific_key, specific_name in canonical_by_key.items():
                if broad_key == specific_key or broad_name not in specific_name:
                    continue
                mapping[broad_key].extend(mapping[specific_key])
        for key in mapping:
            mapping[key] = sorted(set(mapping[key]))
        return mapping

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
        rejected_matches: list[dict[str, Any]] = []
        rejected_candidates: list[dict[str, Any]] = []
        rejected_claim_links: list[dict[str, Any]] = []
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
                if not m.get("evidence_validated"):
                    rejected_matches.append(m)
                elif key and key not in seen_matches:
                    seen_matches.add(key)
                    merged["node_matches"].append(m)
            for c in data.get("node_candidates") or []:
                key = normalize_ws(str(c.get("canonical_name", ""))).lower()
                if not c.get("quality_eligible"):
                    rejected_candidates.append(c)
                elif key and key not in seen_candidates:
                    seen_candidates.add(key)
                    merged["node_candidates"].append(c)
            for claim in data.get("claims") or []:
                statement = normalize_ws(str(claim.get("statement", "")))
                key = statement.lower()
                if not statement or key in seen_claims:
                    continue
                seen_claims.add(key)
                rejected_claim_links.extend(claim.get("rejected_related_node_links") or [])
                merged["claims"].append(claim)
            merged["source_references"].extend(data.get("source_references") or [])
        return SourceAnalysis(
            **merged,
            rejected_node_matches=rejected_matches,
            rejected_node_candidates=rejected_candidates,
            rejected_claim_node_links=rejected_claim_links,
        )


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
            required_attributions_json=json.dumps(
                context.get("required_claim_attributions") or {}, ensure_ascii=False,
            ),
        )
        data = self.llm.json(IMPACT_SYSTEM, user)
        return self._validate_impact_output(data, evidence)
