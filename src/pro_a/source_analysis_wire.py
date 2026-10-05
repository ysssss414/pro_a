"""Dormant, pure Source Analysis wire foundation; no provider or runtime binding."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from .analyzer import FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS, SourcePiece
from .constants import (
    CLAIM_NATURES, CLAIM_STATUSES, NODE_TYPES, NOVELTY_LEVELS, RELATION_TYPES,
    SOURCE_ORIGIN_TYPES, SOURCE_RANKS,
)
from .parsers import SOURCE_MARKER


SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION = "source-analysis-wire-v2"
SOURCE_ANALYSIS_EVIDENCE_UNIT_VERSION = "source-analysis-evidence-unit-v1"
SOURCE_ANALYSIS_WIRE_EXPANDER_VERSION = "source-analysis-wire-expander-v1"
NODE_MATCH_ROLES = ("primary", "related")
SOURCE_REFERENCE_RELATION_TYPES = ("references", "updates", "derived_from")


class SourceAnalysisWireError(ValueError):
    """A terminal invalid wire/catalog; messages never contain Source text."""


@dataclass(frozen=True)
class SourcePieceContext:
    source_sha256: str
    piece: SourcePiece
    known_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceEvidenceUnit:
    evidence_ref: str
    source_sha256: str
    piece_id: str
    piece_sha256: str
    locator: str
    ordinal: int
    block_ordinal: int
    source_start: int
    source_end: int
    exact_text: str
    exact_text_sha256: str


@dataclass(frozen=True)
class SourceEvidenceCatalog:
    contract_version: str
    source_sha256: str
    piece_id: str
    piece_sha256: str
    units: tuple[SourceEvidenceUnit, ...]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fail(path: str, reason: str) -> None:
    raise SourceAnalysisWireError(f"{path}: {reason}")


def _context(context: SourcePieceContext) -> None:
    if not isinstance(context, SourcePieceContext) or not isinstance(context.piece, SourcePiece):
        _fail("context", "SourcePieceContext required")
    if not isinstance(context.source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", context.source_sha256):
        _fail("context", "immutable Source SHA required")
    if not isinstance(context.piece.source_text, str) or len(context.piece.source_text) > FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS:
        _fail("context", "piece exceeds frozen capacity")
    ids = context.known_node_ids
    if not isinstance(ids, tuple) or any(not isinstance(v, str) or not v.strip() for v in ids) or len(set(ids)) != len(ids):
        _fail("context", "unique frozen Node IDs required")


# Conservative hard blocks: paragraphs, potential line-start speaker/label headers,
# and timestamp headers. A label boundary is not a claim of speaker identity.
_BLOCK_START = re.compile(
    r"\r?\n[ \t]*\r?\n|(?m:^[ \t]*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?|[^。！？!?：:\r\n]+[：:]))"
)
_INLINE_BLOCK = re.compile(
    r"\[\d{1,2}:\d{2}(?::\d{2})?\]|(?<!\w)(?:主持人|专家|发言人|说话人|提问者|回答者|问|答|Speaker[ \t]+\d+)[：:]"
)
_SENTENCE_END = re.compile(r"[。！？!?]+[”’\"')）]*|(?<!\.)\.(?!\.)(?=\s|$)")
_ABBREVIATIONS = frozenset(("mr", "mrs", "ms", "dr", "prof", "e.g", "i.e", "vs", "etc"))


def build_source_evidence_catalog(context: SourcePieceContext) -> SourceEvidenceCatalog:
    """Exact piece-local code-point spans, generated without any Claim/model state.

    Markers and boundary whitespace remain in SourcePiece; selectable spans cover
    all other represented text without normalization. No comma/semicolon or
    arbitrary length split is made; a long utterance is bounded by the 4k piece.
    """
    _context(context)
    piece = context.piece
    text = piece.source_text
    markers = list(SOURCE_MARKER.finditer(text))
    regions = [("TEXT", 0, markers[0].start() if markers else len(text))]
    regions.extend((m.group(1), m.end(), markers[i+1].start() if i+1 < len(markers) else len(text))
                   for i, m in enumerate(markers))
    units: list[SourceEvidenceUnit] = []
    block_ordinal = 0
    for locator, start, end in regions:
        body = text[start:end]
        if body.strip() == "[PAGE_PARSE_ERROR]":
            continue
        boundaries = sorted({0, len(body), *(m.start() for m in _BLOCK_START.finditer(body)),
                             *(m.start() for m in _INLINE_BLOCK.finditer(body))})
        for left, right in zip(boundaries, boundaries[1:]):
            block_ordinal += 1
            block = body[left:right]
            cuts = [0]
            for match in _SENTENCE_END.finditer(block):
                if match.group() == ".":
                    word = re.search(r"([A-Za-z.]+)$", block[:match.start()])
                    if word and (word[1].lower() in _ABBREVIATIONS or len(word[1]) == 1
                                 or re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word[1])):
                        continue
                cuts.append(match.end())
            cuts.append(len(block))
            for lo, hi in zip(cuts, cuts[1:]):
                while lo < hi and block[lo].isspace():
                    lo += 1
                while hi > lo and block[hi-1].isspace():
                    hi -= 1
                if lo == hi:
                    continue
                source_start, source_end = start+left+lo, start+left+hi
                exact = text[source_start:source_end]
                ordinal = len(units)+1
                identity = {
                    "contract_version": SOURCE_ANALYSIS_EVIDENCE_UNIT_VERSION,
                    "source_sha256": context.source_sha256, "piece_id": piece.piece_id,
                    "piece_sha256": piece.source_sha256, "locator": locator,
                    "ordinal": ordinal, "block_ordinal": block_ordinal,
                    "source_start": source_start, "source_end": source_end,
                    "exact_text_sha256": _sha(exact),
                }
                ref = "EV_" + _sha(json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False))[:16].upper()
                units.append(SourceEvidenceUnit(ref, context.source_sha256, piece.piece_id,
                    piece.source_sha256, locator, ordinal, block_ordinal, source_start, source_end, exact, _sha(exact)))
    return SourceEvidenceCatalog(SOURCE_ANALYSIS_EVIDENCE_UNIT_VERSION, context.source_sha256,
                                 piece.piece_id, piece.source_sha256, tuple(units))


_METADATA_DEFAULTS = {"author": "", "organization": "", "summary": ""}
_CLAIM_DEFAULTS = {"related_node_ids": [], "related_candidate_names": [], "assumption": "", "status": "current", "structured": {}}
_NODE_DEFAULTS = {
    "aliases": [], "description": "", "suggested_parent_node_ids": [], "reason": "",
    "is_discrete_event": False, "event_time": "", "evidence_excerpt": "",
    "long_term_research_value": False, "cross_source_or_node_value": False,
    "question": "", "importance": "", "what_would_change_my_mind": "",
}
_NODE_VARIANTS = {
    "Event": {"is_discrete_event", "event_time", "evidence_ref"},
    "Theme": {"long_term_research_value", "cross_source_or_node_value"},
    "ResearchQuestion": {"question", "importance", "what_would_change_my_mind"},
}
_TYPE_FIELDS = set().union(*_NODE_VARIANTS.values())
_BOOL_FIELDS = {"is_discrete_event", "long_term_research_value", "cross_source_or_node_value"}


def _object(value: Any, path: str, required: set[str], optional: set[str]) -> dict:
    if not isinstance(value, dict):
        _fail(path, "object required")
    if not required <= value.keys() or value.keys() - required - optional:
        _fail(path, "missing or unsupported fields")
    return value


def _string(value: Any, path: str, *, nonempty: bool = False) -> None:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        _fail(path, "string required")


def _confidence(value: Any, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 or not math.isfinite(value):
        _fail(path, "finite confidence in 0..1 required")


def _enum(value: Any, choices: list[str] | set[str] | tuple[str, ...], path: str) -> None:
    if not isinstance(value, str) or value not in choices:
        _fail(path, "unsupported enum")


def _strings(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        _fail(path, "array required")
    for item in value:
        _string(item, path, nonempty=True)
    return value


def _json(value: Any, path: str) -> None:
    # structured is the existing canonical open JSON object, not a second wire.
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            _json(item, path)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _json(item, path)
        return
    _fail(path, "JSON value required")


def validate_source_analysis_wire_v2(wire: Any, catalog: SourceEvidenceCatalog,
                                     context: SourcePieceContext) -> None:
    """Strict shape/reference validation; existing native semantic gates still run."""
    expected = build_source_evidence_catalog(context)
    if not isinstance(catalog, SourceEvidenceCatalog) or catalog != expected:
        _fail("evidence_catalog", "immutable binding or content mismatch")
    for unit in catalog.units:
        if any(type(getattr(unit, field)) is not int for field in ("ordinal", "block_ordinal", "source_start", "source_end")):
            _fail("evidence_catalog", "integer ordinals and spans required")
    refs = {u.evidence_ref: u for u in catalog.units}
    if len(refs) != len(catalog.units):
        _fail("evidence_catalog", "ambiguous identity")
    def evidence(value: Any, path: str) -> None:
        if not isinstance(value, str) or value not in refs:
            _fail(path, "unknown or foreign evidence_ref")
    def node_ids(value: Any, path: str) -> None:
        if any(v not in context.known_node_ids for v in _strings(value, path)):
            _fail(path, "unknown Node ID")
    def items(group: str, limit: int | None = None) -> list:
        value = wire.get(group, [])
        if not isinstance(value, list) or (limit is not None and len(value) > limit):
            _fail(group, "bounded array required")
        return value
    _object(wire, "wire", {"wire_version", "source_metadata", "claims"},
            {"node_matches", "node_candidates", "relation_candidates", "source_references"})
    _enum(wire["wire_version"], {SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION}, "wire_version")
    metadata = _object(wire["source_metadata"], "source_metadata",
        {"title", "publication_time", "source_rank", "source_origin_type"}, set(_METADATA_DEFAULTS))
    for field in metadata:
        _string(metadata[field], "source_metadata."+field)
    _enum(metadata["source_rank"], SOURCE_RANKS, "source_metadata.source_rank")
    _enum(metadata["source_origin_type"], SOURCE_ORIGIN_TYPES, "source_metadata.source_origin_type")
    candidates = items("node_candidates", 100)
    candidate_names = []
    for candidate in candidates:
        common = {"canonical_name", "primary_type", "confidence", "independent_research_value", "maintenance_rationale"}
        _object(candidate, "node_candidate", common,
                {"aliases", "description", "suggested_parent_node_ids", "reason", "preserved_fields"} | _TYPE_FIELDS)
        _enum(candidate["primary_type"], NODE_TYPES, "node_candidate.primary_type")
        variant = _NODE_VARIANTS.get(candidate["primary_type"], set())
        _object(candidate, "node_candidate", common | variant,
                {"aliases", "description", "suggested_parent_node_ids", "reason", "preserved_fields"})
        _string(candidate["canonical_name"], "node_candidate.canonical_name", nonempty=True)
        candidate_names.append(candidate["canonical_name"])
        _confidence(candidate["confidence"], "node_candidate.confidence")
        if not isinstance(candidate["independent_research_value"], bool):
            _fail("node_candidate.independent_research_value", "boolean required")
        _string(candidate["maintenance_rationale"], "node_candidate.maintenance_rationale")
        for field in ("description", "reason"):
            if field in candidate:
                _string(candidate[field], "node_candidate."+field)
        _strings(candidate.get("aliases", []), "node_candidate.aliases")
        node_ids(candidate.get("suggested_parent_node_ids", []), "node_candidate.suggested_parent_node_ids")
        preserved = _object(candidate.get("preserved_fields", {}), "node_candidate.preserved_fields", set(), _TYPE_FIELDS-variant)
        for field, value in {**{f: candidate[f] for f in variant}, **preserved}.items():
            if field == "evidence_ref":
                evidence(value, "node_candidate.evidence_ref")
            elif field in _BOOL_FIELDS:
                if not isinstance(value, bool):
                    _fail("node_candidate."+field, "boolean required")
            else:
                _string(value, "node_candidate."+field)
    for match in items("node_matches"):
        _object(match, "node_match", {"node_id", "role", "confidence", "evidence_ref"}, {"reason"})
        node_ids([match["node_id"]], "node_match.node_id")
        _enum(match["role"], NODE_MATCH_ROLES, "node_match.role")
        _confidence(match["confidence"], "node_match.confidence")
        _string(match.get("reason", ""), "node_match.reason")
        evidence(match["evidence_ref"], "node_match.evidence_ref")
    claims = items("claims", 100)
    for claim in claims:
        required = {"statement", "nature", "evidence_ref", "attributed_to", "fact_time", "scope", "confidence", "novelty_level"}
        _object(claim, "claim", required, set(_CLAIM_DEFAULTS))
        _string(claim["statement"], "claim.statement", nonempty=True)
        for field in ("attributed_to", "fact_time", "scope", "assumption"):
            _string(claim.get(field, ""), "claim."+field)
        _enum(claim["nature"], CLAIM_NATURES, "claim.nature")
        _enum(claim.get("status", "current"), CLAIM_STATUSES, "claim.status")
        _enum(claim["novelty_level"], NOVELTY_LEVELS, "claim.novelty_level")
        _confidence(claim["confidence"], "claim.confidence")
        evidence(claim["evidence_ref"], "claim.evidence_ref")
        node_ids(claim.get("related_node_ids", []), "claim.related_node_ids")
        if any(name not in candidate_names for name in _strings(claim.get("related_candidate_names", []), "claim.related_candidate_names")):
            _fail("claim.related_candidate_names", "unknown candidate")
        structured = claim.get("structured", {})
        if not isinstance(structured, dict):
            _fail("claim.structured", "object required")
        _json(structured, "claim.structured")
    claim_refs = {f"C{i+1}" for i in range(len(claims))}
    for relation in items("relation_candidates"):
        _object(relation, "relation", {"from_node_id", "relation_type", "to_node_id", "scope", "supporting_claim_refs", "confidence"}, {"reason"})
        node_ids([relation["from_node_id"], relation["to_node_id"]], "relation.endpoints")
        _enum(relation["relation_type"], set(RELATION_TYPES)-{"part_of"}, "relation.relation_type")
        _string(relation["scope"], "relation.scope")
        _string(relation.get("reason", ""), "relation.reason")
        _confidence(relation["confidence"], "relation.confidence")
        support = _strings(relation["supporting_claim_refs"], "relation.supporting_claim_refs")
        if not support or len(set(support)) != len(support) or any(ref not in claim_refs for ref in support):
            _fail("relation.supporting_claim_refs", "unique local ordinal references required")
    for reference in items("source_references"):
        _object(reference, "source_reference", {"title", "relation_type"}, {"note"})
        _string(reference["title"], "source_reference.title", nonempty=True)
        _enum(reference["relation_type"], SOURCE_REFERENCE_RELATION_TYPES, "source_reference.relation_type")
        _string(reference.get("note", ""), "source_reference.note")


def expand_source_analysis_wire_v2(wire: dict, evidence_catalog: SourceEvidenceCatalog,
                                    source_piece_context: SourcePieceContext) -> dict[str, Any]:
    """Validate, then reconstruct full canonical values; never annotate provenance.

    The existing Analyzer attaches origins and performs all native semantic gates.
    This function does not invoke it or alter permanent Claim identity.
    """
    validate_source_analysis_wire_v2(wire, evidence_catalog, source_piece_context)
    refs = {u.evidence_ref: u for u in evidence_catalog.units}
    result = {"source_metadata": {**_METADATA_DEFAULTS, **copy.deepcopy(wire["source_metadata"])},
              "node_matches": [], "node_candidates": [], "claims": [], "relation_candidates": [], "source_references": []}
    for match in wire.get("node_matches", []):
        obj = {"reason": "", **copy.deepcopy(match)}
        obj["evidence_excerpt"] = refs[obj.pop("evidence_ref")].exact_text
        result["node_matches"].append(obj)
    for candidate in wire.get("node_candidates", []):
        obj = {**copy.deepcopy(_NODE_DEFAULTS), **copy.deepcopy(candidate)}
        obj.update(obj.pop("preserved_fields", {}))
        obj["candidate_kind"] = "research_question" if obj["primary_type"] == "ResearchQuestion" else "normal"
        if "evidence_ref" in obj:
            obj["evidence_excerpt"] = refs[obj.pop("evidence_ref")].exact_text
        result["node_candidates"].append(obj)
    for index, claim in enumerate(wire["claims"], 1):
        obj = {**copy.deepcopy(_CLAIM_DEFAULTS), **copy.deepcopy(claim)}
        unit = refs[obj.pop("evidence_ref")]
        obj.update(claim_ref=f"C{index}", evidence_pointer=f"[[{unit.locator}]]" if unit.locator != "TEXT" else "TEXT", evidence_excerpt=unit.exact_text)
        result["claims"].append(obj)
    result["relation_candidates"] = [{"reason": "", **copy.deepcopy(r)} for r in wire.get("relation_candidates", [])]
    result["source_references"] = [{"note": "", **copy.deepcopy(r)} for r in wire.get("source_references", [])]
    return result
