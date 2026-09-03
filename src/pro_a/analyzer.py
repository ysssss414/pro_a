from __future__ import annotations

import csv
import copy
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from .config import AppConfig
from .constants import (
    CHANGE_LEVELS, CLAIM_NATURES, CLAIM_STATUSES, NODE_TYPES, NOVELTY_LEVELS,
    RELATION_TYPES, SOURCE_ORIGIN_TYPES, SOURCE_RANKS,
)
from .db import Database
from .llm import ChatLLM, LLMError
from .parsers import chunk_source_text, chunk_text, source_units
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
_RELATION_SEMANTIC_MARKERS = {
    "upstream_of": ("上游", "upstream of"),
    "supplies": ("供应", "供货", "supply", "supplies", "supplied", "supplying"),
    "produces": ("生产", "制造", "produce", "produces", "produced", "manufacture", "manufactures", "manufactured"),
    "uses": ("采用", "使用", "搭载", "use", "uses", "used", "using"),
    "applied_in": ("应用于", "用于", "applied in", "applied to", "used in"),
    "substitutes": ("替代", "取代", "substitute", "substitutes", "replace", "replaces"),
    "depends_on": ("依赖", "取决于", "depend on", "depends on", "dependent on", "rely on", "relies on"),
    "constrains": ("制约", "限制", "约束", "constrain", "constrains", "limit", "limits"),
    "drives": ("驱动", "推动", "带动", "drive", "drives"),
    "competes_with": ("竞争", "竞品", "competes with", "competing with"),
    "benefits_from": ("受益于", "benefit from", "benefits from"),
    "exposed_to": ("暴露于", "敞口", "exposed to", "exposure to"),
    "regulated_by": ("监管", "管制", "regulated by", "governed by"),
    "validates": ("验证", "证实", "validate", "validates", "confirm", "confirms"),
    "invalidates": ("证伪", "推翻", "否定", "invalidate", "invalidates", "disprove", "disproves"),
    "related_to": ("相关", "关联", "related to", "associated with"),
}
_DIRECTIONAL_RELATION_TYPES = {
    "upstream_of", "supplies", "produces", "uses", "applied_in", "depends_on",
    "constrains", "drives", "benefits_from", "exposed_to", "regulated_by",
    "validates", "invalidates",
}
_RELATION_CANDIDATE_CLAIM_STATUSES = {"current", "pending_verification", "disputed"}
_CHINESE_RELATION_NEGATION_RE = re.compile(r"并非|不是|未曾|不再|尚未|没有|并未|不|非|未|无")
_ENGLISH_RELATION_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|without|does\s+not|do\s+not|did\s+not|is\s+not|"
    r"are\s+not|was\s+not|were\s+not|will\s+not|doesn't|don't|didn't|"
    r"isn't|aren't|wasn't|weren't)\b",
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


def scope_node_catalog(
    full_prompt_catalog: list[dict[str, Any]], piece_source_text: str,
) -> list[dict[str, Any]]:
    """Keep catalog records whose canonical name or alias occurs in this piece."""
    normalized_piece = canonicalize_text(piece_source_text).casefold()
    scoped: list[dict[str, Any]] = []
    for node in full_prompt_catalog:
        terms = [node.get("canonical_name") or "", *(node.get("aliases") or [])]
        if any(
            normalized_term in normalized_piece
            for term in terms
            if (normalized_term := canonicalize_text(str(term)).casefold())
        ):
            scoped.append(node)
    return scoped


def resolve_evidence_locator(full_text: str, evidence_excerpt: str) -> dict[str, Any]:
    """Locate normalized exact Evidence without changing its validation verdict."""
    excerpt = canonicalize_text(evidence_excerpt)
    locators = list(dict.fromkeys(
        locator for locator, body in source_units(full_text)
        if excerpt and excerpt in canonicalize_text(body)
    ))
    if len(locators) == 1:
        return {"status": "resolved", "locator": locators[0]}
    if locators:
        return {"status": "ambiguous", "locators": locators}
    return {"status": "unresolved"}


def relation_evidence_rows(full_text: str) -> list[dict[str, str]]:
    lines = (full_text or "").splitlines(keepends=True)
    for delimiter in (",", "\t", "|", ";"):
        records = []
        start_line = 0
        try:
            reader = csv.reader(lines, delimiter=delimiter)
            for row in reader:
                end_line = reader.line_num
                records.append((row, "".join(lines[start_line:end_line])))
                start_line = end_line
        except csv.Error:
            continue
        for header_index, (header, _) in enumerate(records):
            columns = [canonicalize_text(value).lstrip("\ufeff").lower() for value in header]
            if "evidence_status" not in columns:
                continue
            status_index = columns.index("evidence_status")
            return [
                {
                    "canonical_row": canonicalize_text(raw_row),
                    "evidence_status": canonicalize_text(row[status_index]).lower(),
                }
                for row, raw_row in records[header_index + 1:]
                if len(row) > status_index
            ]
    return []


def claim_uses_missing_relation_evidence(
    claim: dict[str, Any], rows: list[dict[str, str]],
) -> bool:
    excerpt = canonicalize_text(str(claim.get("evidence_excerpt") or ""))
    matching_statuses = [
        row["evidence_status"]
        for row in rows
        if excerpt and excerpt in row["canonical_row"]
    ]
    return bool(matching_statuses) and all(status == "missing" for status in matching_statuses)


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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourcePiece:
    """Bind Source content separately from the marker-wrapped prompt material."""

    chunk_index: int
    chunk_count: int
    split_path: str
    split_depth: int
    source_text: str
    prompt_text: str

    @property
    def source_sha256(self) -> str:
        return _sha256_text(self.source_text)

    @property
    def prompt_sha256(self) -> str:
        return _sha256_text(self.prompt_text)

    @property
    def piece_id(self) -> str:
        identity = json.dumps(
            {
                "chunk_index": self.chunk_index,
                "chunk_count": self.chunk_count,
                "split_path": self.split_path,
                "split_depth": self.split_depth,
                "source_piece_sha256": self.source_sha256,
                "prompt_piece_sha256": self.prompt_sha256,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"PIECE_{_sha256_text(identity)[:16].upper()}"

    def origin(self) -> dict[str, Any]:
        return {
            "piece_id": self.piece_id,
            "origin_chunk_index": self.chunk_index,
            "origin_chunk_count": self.chunk_count,
            "origin_split_path": self.split_path,
            "origin_split_depth": self.split_depth,
            "origin_piece_sha256": self.source_sha256,
        }

    def diagnostic(self) -> dict[str, Any]:
        return {
            "piece_id": self.piece_id,
            "chunk_index": self.chunk_index,
            "chunk_count": self.chunk_count,
            "split_path": self.split_path,
            "split_depth": self.split_depth,
            "source_piece_sha256": self.source_sha256,
            "source_piece_chars": len(self.source_text),
            "prompt_piece_sha256": self.prompt_sha256,
            "prompt_piece_chars": len(self.prompt_text),
        }


@dataclass(frozen=True)
class PieceAnalysisResponse:
    piece: SourcePiece
    raw_response: dict[str, Any]


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
    relation_candidates: list[dict[str, Any]] = field(default_factory=list)
    rejected_relation_candidates: list[dict[str, Any]] = field(default_factory=list)


class Analyzer:
    def __init__(self, cfg: AppConfig, db: Database):
        self.cfg = cfg
        self.db = db
        self.llm = ChatLLM(cfg.llm)
        self.last_piece_call_records: list[dict[str, Any]] = []

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

    @staticmethod
    def _attach_piece_origin(item: dict[str, Any], piece: SourcePiece) -> None:
        origin = piece.origin()
        origin.update({
            "evidence_validated": item.get("evidence_validated") is True,
            "evidence_excerpt_sha256": _sha256_text(
                str(item.get("evidence_excerpt") or "")
            ),
        })
        item.update({
            "origin_chunk_index": origin["origin_chunk_index"],
            "origin_split_path": origin["origin_split_path"],
            "origin_piece_sha256": origin["origin_piece_sha256"],
            "origin_pieces": [origin],
        })

    @staticmethod
    def _merge_piece_origins(
        target: dict[str, Any], incoming: dict[str, Any]
    ) -> None:
        origins = target.setdefault("origin_pieces", [])
        seen = {
            (
                item.get("piece_id"),
                item.get("origin_piece_sha256"),
                item.get("origin_split_path"),
            )
            for item in origins
            if isinstance(item, dict)
        }
        for origin in incoming.get("origin_pieces") or []:
            if not isinstance(origin, dict):
                continue
            key = (
                origin.get("piece_id"),
                origin.get("origin_piece_sha256"),
                origin.get("origin_split_path"),
            )
            if key not in seen:
                origins.append(copy.deepcopy(origin))
                seen.add(key)

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

    def _validate_node_candidate(
        self,
        candidate: Any,
        index: int,
        full_text: str,
        source_rank: str,
    ) -> dict[str, Any]:
        path = f"node_candidates[{index}]"
        candidate = self._object(candidate, path)
        if not normalize_ws(str(candidate.get("canonical_name") or "")):
            self._invalid(f"{path}.canonical_name", "field is required")
        primary_type = candidate.get("primary_type")
        if primary_type not in NODE_TYPES:
            self._invalid(
                f"{path}.primary_type", f"unsupported Node Type {primary_type!r}"
            )
        kind = candidate.get("candidate_kind") or "normal"
        if kind not in {"normal", "research_question"}:
            self._invalid(f"{path}.candidate_kind", f"unsupported value {kind!r}")
        if (kind == "research_question") != (primary_type == "ResearchQuestion"):
            self._invalid(path, "ResearchQuestion type and candidate_kind must agree")
        candidate["candidate_kind"] = kind
        self._confidence(candidate, path)
        self._list(candidate.get("aliases") or [], f"{path}.aliases")
        parent_ids = self._list(
            candidate.get("suggested_parent_node_ids") or [],
            f"{path}.suggested_parent_node_ids",
        )
        valid_parent_ids: list[str] = []
        unknown_parent_ids: list[str] = []
        for parent_index, parent_id in enumerate(parent_ids):
            if not isinstance(parent_id, str) or not parent_id.strip():
                self._invalid(
                    f"{path}.suggested_parent_node_ids[{parent_index}]",
                    "must be a non-empty Node ID",
                )
            if self.db.get_node(parent_id):
                valid_parent_ids.append(parent_id)
            else:
                unknown_parent_ids.append(parent_id)
        candidate["suggested_parent_node_ids"] = valid_parent_ids
        quality = self._candidate_quality(candidate, full_text, source_rank)
        if unknown_parent_ids:
            quality["eligible"] = False
            quality["errors"].extend(
                f"unknown_suggested_parent_node_id:{node_id}"
                for node_id in unknown_parent_ids
            )
            candidate["rejected_suggested_parent_node_ids"] = unknown_parent_ids
        candidate["quality_eligible"] = quality["eligible"]
        candidate["quality_validation"] = quality
        return candidate

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

    @staticmethod
    def _node_evidence_terms(node: dict[str, Any]) -> list[str]:
        terms: list[str] = []
        for raw in [node.get("canonical_name") or "", *(node.get("aliases") or [])]:
            term = canonicalize_text(str(raw)).lower()
            if term and term not in terms:
                terms.append(term)
        return terms

    @classmethod
    def _claim_identifies_relation_endpoints(
        cls, claim: dict[str, Any], from_node: dict[str, Any], to_node: dict[str, Any]
    ) -> bool:
        evidence = canonicalize_text(str(claim.get("evidence_excerpt") or "")).lower()
        return bool(
            evidence
            and any(term in evidence for term in cls._node_evidence_terms(from_node))
            and any(term in evidence for term in cls._node_evidence_terms(to_node))
        )

    @classmethod
    def _term_spans(cls, text: str, terms: list[str]) -> list[tuple[int, int, str]]:
        spans: list[tuple[int, int, str]] = []
        for term in terms:
            start = text.find(term)
            while start >= 0:
                span = (start, start + len(term), term)
                if span not in spans:
                    spans.append(span)
                start = text.find(term, start + 1)
        return spans

    @staticmethod
    def _relation_marker_matches(
        text: str, relation_type: str,
    ) -> list[tuple[int, int, str]]:
        matches: list[tuple[int, int, str]] = []
        for marker in sorted(
            _RELATION_SEMANTIC_MARKERS.get(relation_type) or (), key=len, reverse=True,
        ):
            if marker.isascii():
                pattern = re.compile(
                    rf"(?<![a-z]){re.escape(marker)}(?![a-z])", re.IGNORECASE,
                )
                found = (
                    (match.start(), match.end(), match.group(0).lower())
                    for match in pattern.finditer(text)
                )
            else:
                found_items: list[tuple[int, int, str]] = []
                start = text.find(marker)
                while start >= 0:
                    found_items.append((start, start + len(marker), marker))
                    start = text.find(marker, start + 1)
                found = iter(found_items)
            for item in found:
                if item not in matches:
                    matches.append(item)
        return matches

    @staticmethod
    def _is_negated_relation_marker(
        text: str,
        from_span: tuple[int, int, str],
        to_span: tuple[int, int, str],
        marker_span: tuple[int, int, str],
    ) -> bool:
        start = min(from_span[0], to_span[0], marker_span[0])
        end = max(from_span[1], to_span[1], marker_span[1])
        context = list(text[start:end])
        for endpoint in (from_span, to_span):
            for index in range(endpoint[0] - start, endpoint[1] - start):
                context[index] = " "
        normalized = "".join(context)
        return bool(
            _CHINESE_RELATION_NEGATION_RE.search(normalized)
            or _ENGLISH_RELATION_NEGATION_RE.search(normalized)
        )

    @staticmethod
    def _directionally_supported(
        text: str,
        relation_type: str,
        from_span: tuple[int, int, str],
        to_span: tuple[int, int, str],
        marker_span: tuple[int, int, str],
    ) -> bool:
        from_start, from_end, _ = from_span
        to_start, to_end, _ = to_span
        marker_start, marker_end, marker = marker_span
        if from_start < to_start:
            between = text[from_end:to_start]
            marker_between = from_end <= marker_start and marker_end <= to_start
            marker_after = to_end <= marker_start <= to_end + 24
            if marker_between:
                if relation_type == "regulated_by":
                    return marker in {"regulated by", "governed by"}
                return True
            if marker_after:
                if relation_type == "supplies":
                    return bool(re.search(r"向|为|给", between)) and not re.search(r"由|被", between)
                if relation_type == "upstream_of":
                    return bool(re.search(r"是|位于|属于", between))
                if relation_type == "regulated_by":
                    return bool(re.search(r"受|由", between))
                if relation_type in {"related_to", "competes_with"}:
                    return bool(re.search(r"与|和|同|跟|&", between))
            return False

        if to_start < from_start:
            between = text[to_end:from_start]
            marker_between = to_end <= marker_start and marker_end <= from_start
            marker_after = from_end <= marker_start <= from_end + 24
            if relation_type in {"supplies", "produces", "uses"}:
                if marker_after and re.search(r"由|被", between):
                    return True
                if marker_between and re.search(r"\bby\b", text[marker_end:from_start]):
                    return True
            if relation_type == "regulated_by" and marker_between:
                return marker in {"监管", "管制"}
        return False

    @staticmethod
    def _is_reversed_direction_pattern(
        text: str,
        relation_type: str,
        from_span: tuple[int, int, str],
        to_span: tuple[int, int, str],
        marker_span: tuple[int, int, str],
    ) -> bool:
        from_start, from_end, _ = from_span
        to_start, to_end, _ = to_span
        marker_start, marker_end, marker = marker_span
        if from_start < to_start:
            between = text[from_end:to_start]
            marker_between = from_end <= marker_start and marker_end <= to_start
            marker_after = to_end <= marker_start <= to_end + 24
            if (
                relation_type in {"supplies", "produces", "uses"}
                and marker_between
                and (
                    re.search(r"被|由", text[from_end:marker_start])
                    or re.search(r"\bby\b", text[marker_end:to_start])
                )
            ):
                return True
            if (
                relation_type in {"supplies", "produces", "uses"}
                and marker_after
                and re.search(r"由|被", between)
            ):
                return True
            if (
                relation_type == "regulated_by"
                and marker_between
                and marker in {"监管", "管制"}
            ):
                return True
        if to_start < from_start:
            marker_between = to_end <= marker_start and marker_end <= from_start
            if not marker_between:
                return False
            if (
                relation_type in {"supplies", "produces", "uses"}
                and re.search(r"\bby\b", text[marker_end:from_start])
            ):
                return False
            if relation_type == "regulated_by" and marker in {"监管", "管制"}:
                return False
            return True
        return False

    @classmethod
    def _text_relation_semantic_status(
        cls,
        text: str,
        from_node: dict[str, Any],
        relation_type: str,
        to_node: dict[str, Any],
    ) -> str:
        normalized = canonicalize_text(text).lower()
        from_spans = cls._term_spans(normalized, cls._node_evidence_terms(from_node))
        to_spans = cls._term_spans(normalized, cls._node_evidence_terms(to_node))
        marker_spans = cls._relation_marker_matches(normalized, relation_type)
        if not from_spans or not to_spans or not marker_spans:
            return "semantic_unsupported"

        saw_negated = False
        saw_reversed = False
        saw_direction_unsupported = False
        saw_supported = False
        for from_span in from_spans:
            for to_span in to_spans:
                if not (from_span[1] <= to_span[0] or to_span[1] <= from_span[0]):
                    continue
                relation_end = max(from_span[1], to_span[1]) + 24
                for marker_span in marker_spans:
                    if not min(from_span[0], to_span[0]) <= marker_span[0] <= relation_end:
                        continue
                    if cls._is_negated_relation_marker(
                        normalized, from_span, to_span, marker_span,
                    ):
                        saw_negated = True
                        continue
                    if (
                        relation_type in _DIRECTIONAL_RELATION_TYPES
                        and cls._is_reversed_direction_pattern(
                            normalized, relation_type, from_span, to_span, marker_span,
                        )
                    ):
                        saw_reversed = True
                        continue
                    if cls._directionally_supported(
                        normalized, relation_type, from_span, to_span, marker_span,
                    ):
                        saw_supported = True
                        continue
                    saw_direction_unsupported = True
        if saw_negated:
            return "negated"
        if saw_reversed:
            return "reversed"
        if saw_supported:
            return "supported"
        if saw_direction_unsupported:
            return "direction_unsupported"
        return "semantic_unsupported"

    @classmethod
    def _claim_relation_semantic_status(
        cls,
        claim: dict[str, Any],
        from_node: dict[str, Any],
        relation_type: str,
        to_node: dict[str, Any],
    ) -> str:
        statuses = [
            cls._text_relation_semantic_status(
                str(claim.get(field) or ""), from_node, relation_type, to_node,
            )
            for field in ("statement", "evidence_excerpt")
        ]
        if "negated" in statuses:
            return "negated"
        if statuses == ["supported", "supported"]:
            return "supported"
        if "reversed" in statuses:
            return "reversed"
        if "direction_unsupported" in statuses:
            return "direction_unsupported"
        return "semantic_unsupported"

    @classmethod
    def _claim_semantically_supports_relation(
        cls,
        claim: dict[str, Any],
        from_node: dict[str, Any],
        relation_type: str,
        to_node: dict[str, Any],
    ) -> bool:
        """Conservative lexical gate; extraction prompt and human approval remain authoritative."""
        return cls._claim_relation_semantic_status(
            claim, from_node, relation_type, to_node,
        ) == "supported"

    def _validate_relation_candidates(
        self, raw_candidates: Any, claims: list[dict[str, Any]], full_text: str = ""
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        candidates = self._list(raw_candidates or [], "relation_candidates")
        evidence_rows = relation_evidence_rows(full_text)
        claim_by_ref: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for claim_index, claim in enumerate(claims):
            refs = [claim.get("claim_ref"), *(claim.get("_relation_claim_refs") or [])]
            for ref in refs:
                if not isinstance(ref, str) or not ref:
                    continue
                resolved = (claim_index, claim)
                if resolved not in claim_by_ref.setdefault(ref, []):
                    claim_by_ref[ref].append(resolved)

        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        def reject(candidate: Any, reason: str, stage: str) -> None:
            rejected.append({
                "candidate": copy.deepcopy(candidate),
                "reason": reason,
                "stage": stage,
            })

        for raw_candidate in candidates:
            if not isinstance(raw_candidate, dict):
                reject(raw_candidate, "malformed candidate: expected an object", "structure")
                continue
            candidate = copy.deepcopy(raw_candidate)
            candidate.pop("_resolved_supporting_claim_indices", None)
            from_node_id = candidate.get("from_node_id")
            to_node_id = candidate.get("to_node_id")
            relation_type = candidate.get("relation_type")
            if not isinstance(from_node_id, str) or not from_node_id.strip():
                reject(candidate, "malformed candidate: from_node_id is required", "structure")
                continue
            if not isinstance(to_node_id, str) or not to_node_id.strip():
                reject(candidate, "malformed candidate: to_node_id is required", "structure")
                continue
            if not isinstance(relation_type, str) or not relation_type:
                reject(candidate, "malformed candidate: relation_type is required", "structure")
                continue
            from_node_id = from_node_id.strip()
            to_node_id = to_node_id.strip()
            scope = candidate.get("scope", "")
            if not isinstance(scope, str):
                reject(candidate, "malformed candidate: scope must be a string", "structure")
                continue
            reason = candidate.get("reason", "")
            if not isinstance(reason, str):
                reject(candidate, "malformed candidate: reason must be a string", "structure")
                continue
            confidence = candidate.get("confidence")
            if confidence is not None and (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0.0 <= confidence <= 1.0
            ):
                reject(candidate, "malformed candidate: confidence must be between 0 and 1", "structure")
                continue
            raw_refs = candidate.get("supporting_claim_refs")
            if not isinstance(raw_refs, list) or not raw_refs:
                reject(candidate, "supporting_claim_refs must not be empty", "structure")
                continue
            refs: list[str] = []
            malformed_ref = False
            for ref in raw_refs:
                if not isinstance(ref, str) or not ref.strip():
                    malformed_ref = True
                    break
                normalized_ref = ref.strip()
                if normalized_ref not in refs:
                    refs.append(normalized_ref)
            if malformed_ref:
                reject(candidate, "malformed candidate: supporting_claim_refs must contain Claim refs", "structure")
                continue

            from_node = self.db.get_node(from_node_id)
            to_node = self.db.get_node(to_node_id)
            if not from_node:
                reject(candidate, f"unknown from Node: {from_node_id}", "endpoint")
                continue
            if not to_node:
                reject(candidate, f"unknown to Node: {to_node_id}", "endpoint")
                continue
            if from_node.get("status") != "active":
                reject(candidate, f"inactive from endpoint: {from_node_id}", "endpoint")
                continue
            if to_node.get("status") != "active":
                reject(candidate, f"inactive to endpoint: {to_node_id}", "endpoint")
                continue
            if from_node_id == to_node_id:
                reject(candidate, "self relation not allowed", "endpoint")
                continue
            if relation_type not in RELATION_TYPES:
                reject(candidate, f"invalid relation_type: {relation_type}", "endpoint")
                continue
            if relation_type == "part_of":
                reject(candidate, "part_of not allowed", "endpoint")
                continue

            resolved_claim_indices: list[int] = []
            resolution_error = ""
            resolution_stage = "claim_reference"
            for ref in refs:
                resolved = claim_by_ref.get(ref)
                if not resolved:
                    resolution_error = f"unknown supporting_claim_ref: {ref}"
                    break
                if any(
                    claim_uses_missing_relation_evidence(claim, evidence_rows)
                    for _, claim in resolved
                ):
                    resolution_error = (
                        "supporting Claim source row marks relation Evidence missing"
                    )
                    resolution_stage = "evidence"
                    break
                validated = [
                    (claim_index, claim) for claim_index, claim in resolved
                    if claim.get("evidence_validated") is True
                    and claim.get("status") in _RELATION_CANDIDATE_CLAIM_STATUSES
                ]
                if not validated:
                    resolution_error = f"supporting Claim rejected: {ref}"
                    break
                evaluations: list[tuple[int, str]] = []
                for claim_index, claim in validated:
                    if not self._claim_identifies_relation_endpoints(
                        claim, from_node, to_node,
                    ):
                        evaluations.append((claim_index, "endpoint_unsupported"))
                        continue
                    evaluations.append((
                        claim_index,
                        self._claim_relation_semantic_status(
                            claim, from_node, relation_type, to_node,
                        ),
                    ))
                eligible = [
                    claim_index for claim_index, status in evaluations
                    if status == "supported"
                ]
                if len(eligible) == 1:
                    if eligible[0] not in resolved_claim_indices:
                        resolved_claim_indices.append(eligible[0])
                    continue
                if len(eligible) > 1:
                    resolution_error = (
                        "ambiguous atomic Claim ref: multiple relation-supporting children"
                    )
                    resolution_stage = "claim_resolution"
                    break
                if len(resolved) > 1:
                    resolution_error = "atomic Claim ref has no relation-supporting child"
                    resolution_stage = "claim_resolution"
                    break
                statuses = {status for _, status in evaluations}
                if "negated" in statuses:
                    resolution_error = "negated relation evidence"
                    resolution_stage = "semantic"
                elif "reversed" in statuses:
                    resolution_error = "reversed relation direction"
                    resolution_stage = "semantic"
                elif "direction_unsupported" in statuses:
                    resolution_error = "semantic direction unsupported"
                    resolution_stage = "semantic"
                elif "endpoint_unsupported" in statuses:
                    resolution_error = (
                        "no single supporting Claim explicitly identifies both endpoints"
                    )
                    resolution_stage = "evidence"
                else:
                    resolution_error = "semantic support insufficient"
                    resolution_stage = "semantic"
                break
            if resolution_error:
                reject(candidate, resolution_error, resolution_stage)
                continue

            normalized = {
                "from_node_id": from_node_id,
                "relation_type": relation_type,
                "to_node_id": to_node_id,
                "scope": scope.strip(),
                "supporting_claim_refs": refs,
                "reason": reason.strip(),
                "_resolved_supporting_claim_indices": resolved_claim_indices,
            }
            if confidence is not None:
                normalized["confidence"] = float(confidence)
            accepted.append(normalized)
        return accepted, rejected

    def _validate_source_output(
        self, raw: Any, piece_source_text: str
    ) -> dict[str, Any]:
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
        validated_matches: list[dict[str, Any]] = []
        rejected_unknown_matches: list[dict[str, Any]] = []
        for index, match in enumerate(matches):
            path = f"node_matches[{index}]"
            match = self._object(match, path)
            node_id = match.get("node_id")
            if not isinstance(node_id, str) or not self.db.get_node(node_id):
                excerpt = match.get("evidence_excerpt")
                validation = evidence_match(
                    excerpt if isinstance(excerpt, str) else "", piece_source_text
                )
                model_confidence = match.get("confidence")
                if isinstance(model_confidence, bool) or not isinstance(
                    model_confidence, (int, float)
                ):
                    model_confidence = None
                validation.update({
                    "excerpt_located": validation["evidence_validated"],
                    "node_name_or_alias_found": False,
                    "evidence_validated": False,
                    "model_confidence": model_confidence,
                    "errors": ["unknown_node_id"],
                })
                match["evidence_validated"] = False
                match["validation"] = validation
                match["rejection_reason"] = "unknown_node_id"
                rejected_unknown_matches.append(match)
                continue
            role = match.get("role") or "related"
            if role not in {"primary", "related"}:
                self._invalid(f"{path}.role", f"unsupported value {role!r}")
            match["role"] = role
            model_confidence = self._confidence(match, path)
            excerpt = match.get("evidence_excerpt")
            excerpt_present = isinstance(excerpt, str) and bool(normalize_ws(excerpt))
            validation = evidence_match(
                excerpt if excerpt_present else "", piece_source_text
            )
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
            if not excerpt_present:
                validation["errors"] = ["evidence_excerpt_missing"]
            elif validation["evidence_validated"]:
                validation["errors"] = []
            else:
                validation["errors"] = [
                    "node_name_or_alias_not_in_evidence"
                    if excerpt_located else "evidence_excerpt_not_found"
                ]
            match["evidence_validated"] = validation["evidence_validated"]
            match["validation"] = validation
            validated_matches.append(match)
        data["node_matches"] = validated_matches
        data["rejected_node_matches"] = rejected_unknown_matches

        candidates = self._list(data.get("node_candidates") or [], "node_candidates")
        isolated_candidates: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            path = f"node_candidates[{index}]"
            try:
                isolated_candidates.append(
                    self._validate_node_candidate(
                        candidate,
                        index,
                        piece_source_text,
                        str(metadata.get("source_rank") or "UNRANKED"),
                    )
                )
            except LLMError as exc:
                rejected = (
                    copy.deepcopy(candidate)
                    if isinstance(candidate, dict)
                    else {"raw_value": copy.deepcopy(candidate)}
                )
                rejected["quality_eligible"] = False
                rejected["quality_validation"] = {
                    "eligible": False,
                    "errors": ["invalid_subobject"],
                    "path": path,
                    "schema_error": str(exc),
                }
                rejected["rejection_reason"] = str(exc)
                isolated_candidates.append(rejected)
        data["node_candidates"] = isolated_candidates

        raw_claims = self._list(data.get("claims") or [], "claims")
        for index, claim in enumerate(raw_claims):
            if isinstance(claim, dict):
                # The model-facing reference is deterministic and local to this response.
                claim["claim_ref"] = f"C{index + 1}"
        claims = self._normalize_claim_atomicity(raw_claims)
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
            structured = self._object(claim.get("structured") or {}, f"{path}.structured")
            structured_company = canonicalize_text(str(structured.get("company") or ""))
            company_scope = (
                nature == "company_guidance" or "公司" in scope or "企业" in scope
                or bool(structured_company)
            )
            requires_attribution = company_scope or nature in _ATTRIBUTED_NATURES
            if requires_attribution and not attributed_to:
                self._invalid(f"{path}.attributed_to", "attribution is required")
            # Attribution metadata records who made the statement; it is not the
            # statement's grammatical subject. Preserve model/source wording and
            # never inject or substitute attributed_to into Claim semantics.
            raw_related_node_ids = self._list(
                claim.get("related_node_ids") or [], f"{path}.related_node_ids"
            )
            related_node_ids: list[str] = []
            rejected_unknown_node_links: list[dict[str, Any]] = []
            for node_index, node_id in enumerate(raw_related_node_ids):
                if not isinstance(node_id, str) or not node_id.strip():
                    self._invalid(
                        f"{path}.related_node_ids[{node_index}]",
                        "must be a non-empty Node ID",
                    )
                if self.db.get_node(node_id):
                    related_node_ids.append(node_id)
                else:
                    rejected_unknown_node_links.append({
                        "claim_statement": str(claim.get("statement") or ""),
                        "node_id": node_id,
                        "evidence_excerpt": str(claim.get("evidence_excerpt") or ""),
                        "reason": "unknown_node_id",
                    })
            self._list(claim.get("related_candidate_names") or [], f"{path}.related_candidate_names")
            validation = evidence_match(
                str(claim.get("evidence_excerpt") or ""), piece_source_text
            )
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
            rejected_node_links = rejected_unknown_node_links
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

        relation_candidates, rejected_relation_candidates = self._validate_relation_candidates(
            data.get("relation_candidates") or [], claims, piece_source_text,
        )
        data["relation_candidates"] = relation_candidates
        data["rejected_relation_candidates"] = rejected_relation_candidates

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
        self.last_piece_call_records = []
        if not self.available:
            raise LLMError("LLM unavailable")
        chunks = chunk_source_text(text, self.cfg.llm.max_chunk_chars)
        full_prompt_catalog = self.node_catalog()
        merged = {
            "source_metadata": {}, "node_matches": [], "node_candidates": [], "claims": [],
            "source_references": [], "relation_candidates": [],
        }
        rejected_matches: list[dict[str, Any]] = []
        rejected_candidates: list[dict[str, Any]] = []
        rejected_claim_links: list[dict[str, Any]] = []
        rejected_relation_candidates: list[dict[str, Any]] = []
        claim_index_by_statement: dict[str, int] = {}
        next_relation_claim_ref = 1
        seen_matches: set[str] = set()
        match_by_node_id: dict[str, dict[str, Any]] = {}
        seen_candidates: set[str] = set()
        raw_outputs: list[PieceAnalysisResponse] = []
        for idx, chunk in enumerate(chunks, 1):
            def analyze_piece(
                piece: str, split_path: str = "", split_depth: int = 0
            ) -> list[PieceAnalysisResponse]:
                split_marker = (
                    f"\n[[TRUNCATION_SPLIT:{split_path}]]" if split_path else ""
                )
                prompt_piece_text = (
                    f"[[CHUNK:{idx}/{len(chunks)}]]{split_marker}\n{piece}"
                )
                source_piece = SourcePiece(
                    chunk_index=idx,
                    chunk_count=len(chunks),
                    split_path=split_path,
                    split_depth=split_depth,
                    source_text=piece,
                    prompt_text=prompt_piece_text,
                )
                scoped_node_catalog = scope_node_catalog(
                    full_prompt_catalog, source_piece.source_text
                )
                catalog_json = json.dumps(scoped_node_catalog, ensure_ascii=False)
                user = SOURCE_ANALYSIS_USER.format(
                    mode=mode,
                    filename=filename,
                    nodes_json=catalog_json,
                    text=prompt_piece_text,
                )
                piece_diagnostic = {
                    **source_piece.diagnostic(),
                    "full_prompt_catalog_count": len(full_prompt_catalog),
                    "scoped_node_catalog_count": len(scoped_node_catalog),
                    "scoped_node_ids": [
                        str(node.get("node_id") or "")
                        for node in scoped_node_catalog
                    ],
                }
                call_record = {
                    **piece_diagnostic,
                    "source_piece": {
                        "text": source_piece.source_text,
                        "sha256": source_piece.source_sha256,
                        "chars": len(source_piece.source_text),
                    },
                    "prompt_piece": {
                        "prefix": source_piece.prompt_text[
                            :len(source_piece.prompt_text) - len(source_piece.source_text)
                        ],
                        "sha256": source_piece.prompt_sha256,
                        "chars": len(source_piece.prompt_text),
                        "reconstruction": "prompt_piece.prefix + source_piece.text",
                    },
                    "system_prompt_sha256": _sha256_text(SOURCE_ANALYSIS_SYSTEM),
                    "user_prompt_sha256": _sha256_text(user),
                }
                try:
                    raw_response = self.llm.json(SOURCE_ANALYSIS_SYSTEM, user)
                except LLMError as exc:
                    failed_record = {
                        **call_record,
                        "call_status": "failed",
                        "raw_model_json": None,
                        "call_metadata": copy.deepcopy(
                            getattr(self.llm, "last_call_metadata", {})
                        ),
                    }
                    self.last_piece_call_records.append(failed_record)
                    is_truncation = "failure_category=output_truncation" in str(exc)
                    if is_truncation and split_depth < 3:
                        pieces = chunk_text(piece, max(2000, (len(piece) + 1) // 2))
                        if len(pieces) >= 2:
                            recovered: list[PieceAnalysisResponse] = []
                            for split_index, subpiece in enumerate(pieces, 1):
                                child_path = (
                                    f"{split_path}.{split_index}"
                                    if split_path else str(split_index)
                                )
                                recovered.extend(
                                    analyze_piece(
                                        subpiece, child_path, split_depth + 1
                                    )
                                )
                            return recovered
                    terminal = LLMError(str(exc))
                    terminal.piece_context = piece_diagnostic
                    terminal.call_metadata = copy.deepcopy(
                        failed_record["call_metadata"]
                    )
                    raise terminal from exc
                self.last_piece_call_records.append({
                    **call_record,
                    "call_status": "success",
                    "raw_model_json": copy.deepcopy(raw_response),
                    "call_metadata": copy.deepcopy(
                        getattr(self.llm, "last_call_metadata", {})
                    ),
                })
                return [PieceAnalysisResponse(source_piece, raw_response)]

            raw_outputs.extend(analyze_piece(chunk))

        for response_index, response in enumerate(raw_outputs, 1):
            try:
                data = self._validate_source_output(
                    response.raw_response, response.piece.source_text
                )
            except LLMError as exc:
                terminal = LLMError(str(exc))
                terminal.piece_context = response.piece.diagnostic()
                raise terminal from exc
            for match in [
                *(data.get("node_matches") or []),
                *(data.get("rejected_node_matches") or []),
            ]:
                self._attach_piece_origin(match, response.piece)
            for claim in data.get("claims") or []:
                self._attach_piece_origin(claim, response.piece)
            if response_index == 1:
                merged["source_metadata"] = data.get("source_metadata") or {}
            rejected_matches.extend(data.get("rejected_node_matches") or [])
            for m in data.get("node_matches") or []:
                key = str(m.get("node_id", ""))
                if not m.get("evidence_validated"):
                    rejected_matches.append(m)
                elif key and key not in seen_matches:
                    seen_matches.add(key)
                    merged["node_matches"].append(m)
                    match_by_node_id[key] = m
                elif key:
                    self._merge_piece_origins(match_by_node_id[key], m)
            for c in data.get("node_candidates") or []:
                key = normalize_ws(str(c.get("canonical_name", ""))).lower()
                if not c.get("quality_eligible"):
                    rejected_candidates.append(c)
                elif key and key not in seen_candidates:
                    seen_candidates.add(key)
                    merged["node_candidates"].append(c)
            local_to_global_refs: dict[str, list[str]] = {}
            for claim in data.get("claims") or []:
                local_ref = str(claim.get("claim_ref") or "")
                if local_ref and local_ref not in local_to_global_refs:
                    local_to_global_refs[local_ref] = [f"C{next_relation_claim_ref}"]
                    next_relation_claim_ref += 1
            for claim in data.get("claims") or []:
                local_ref = str(claim.get("claim_ref") or "")
                statement = normalize_ws(str(claim.get("statement", "")))
                key = statement.lower()
                if not statement:
                    continue
                global_ref = (local_to_global_refs.get(local_ref) or [""])[0]
                if key in claim_index_by_statement:
                    merged_claim = merged["claims"][claim_index_by_statement[key]]
                    self._merge_piece_origins(merged_claim, claim)
                    relation_refs = merged_claim.setdefault("_relation_claim_refs", [])
                    if global_ref and global_ref not in relation_refs:
                        relation_refs.append(global_ref)
                else:
                    claim_index_by_statement[key] = len(merged["claims"])
                    if global_ref:
                        claim["claim_ref"] = global_ref
                        claim["_relation_claim_refs"] = [global_ref]
                    rejected_claim_links.extend(claim.get("rejected_related_node_links") or [])
                    merged["claims"].append(claim)

            def remap_refs(candidate: dict[str, Any]) -> dict[str, Any]:
                mapped = copy.deepcopy(candidate)
                mapped.pop("_resolved_supporting_claim_indices", None)
                global_refs: list[str] = []
                for ref in mapped.get("supporting_claim_refs") or []:
                    for global_ref in local_to_global_refs.get(ref, [ref]):
                        if global_ref not in global_refs:
                            global_refs.append(global_ref)
                mapped["supporting_claim_refs"] = global_refs
                return mapped

            merged["relation_candidates"].extend(
                remap_refs(candidate) for candidate in data.get("relation_candidates") or []
            )
            for rejection in data.get("rejected_relation_candidates") or []:
                normalized_rejection = copy.deepcopy(rejection)
                if isinstance(normalized_rejection.get("candidate"), dict):
                    normalized_rejection["candidate"] = remap_refs(
                        normalized_rejection["candidate"]
                    )
                rejected_relation_candidates.append(normalized_rejection)
            merged["source_references"].extend(data.get("source_references") or [])
        # Only candidates that passed their own piece and same-response Claims
        # reach this Source-level pass. Revalidation may reject after ref remap,
        # but a locally rejected candidate is absent and cannot be resurrected.
        merged["relation_candidates"], remap_rejections = self._validate_relation_candidates(
            merged["relation_candidates"], merged["claims"], text,
        )
        rejected_relation_candidates.extend(remap_rejections)
        return SourceAnalysis(
            **merged,
            rejected_node_matches=rejected_matches,
            rejected_node_candidates=rejected_candidates,
            rejected_claim_node_links=rejected_claim_links,
            rejected_relation_candidates=rejected_relation_candidates,
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
