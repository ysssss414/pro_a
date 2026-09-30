"""Dormant exact Evidence selection; provider selectors never supply offsets."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .analyzer import _MARKDOWN_ESCAPABLE, canonicalize_text
from .source_analysis_wire import SourceEvidenceCatalog, SourcePieceContext, build_source_evidence_catalog

SOURCE_ANALYSIS_EVIDENCE_BINDING_VERSION = "source-analysis-evidence-binding-v2"
EVIDENCE_SELECTION_FIELDS = frozenset(("evidence_ref", "evidence_selector", "evidence_occurrence", "evidence_mode", "evidence_pointer"))


class EvidenceBindingError(ValueError):
    """Safe error code only; no Source or provider text in errors."""


def identity(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_catalog(catalog: SourceEvidenceCatalog, context: SourcePieceContext) -> None:
    if catalog != build_source_evidence_catalog(context):
        raise EvidenceBindingError("EVIDENCE_CATALOG_BINDING_MISMATCH")
    if any(type(getattr(u, field)) is not int for u in catalog.units
           for field in ("ordinal", "block_ordinal", "source_start", "source_end")):
        raise EvidenceBindingError("INVALID_EVIDENCE_CATALOG_SPAN")


@dataclass(frozen=True)
class EvidenceBinding:
    binding_version: str
    evidence_ref: str
    mode: str
    source_start: int
    source_end: int
    source_locator: str
    evidence_excerpt: str
    evidence_pointer: str
    raw_excerpt_sha256: str
    binding_sha256: str


def _positions(text: str, selector: str) -> list[int]:
    return [m.start() for m in re.finditer("(?=" + re.escape(selector) + ")", text)]


def _normalized_with_spans(raw: str) -> tuple[str, list[tuple[int, int]]]:
    # The native profile is NFKC -> Markdown unescape -> whitespace collapse.
    # Reject nonseparable compositions instead of guessing their raw provenance.
    chars, spans = [], []
    for index, char in enumerate(raw):
        normalized = unicodedata.normalize("NFKC", char)
        chars.extend(normalized)
        spans.extend([(index, index + 1)] * len(normalized))
    if "".join(chars) != unicodedata.normalize("NFKC", raw):
        raise EvidenceBindingError("UNSUPPORTED_NORMALIZATION")
    restored, origins = [], []
    index = 0
    while index < len(chars):
        if chars[index] == "\\" and index + 1 < len(chars) and chars[index + 1] in _MARKDOWN_ESCAPABLE:
            restored.append(chars[index + 1])
            origins.append((spans[index][0], spans[index + 1][1]))
            index += 2
        else:
            restored.append(chars[index])
            origins.append(spans[index])
            index += 1
    text, mapping = [], []
    for match in re.finditer(r"\s+|\S", "".join(restored)):
        text.append(" " if match.group().isspace() else match.group())
        mapping.append((origins[match.start()][0], origins[match.end() - 1][1]))
    while text and text[0] == " ":
        text.pop(0)
        mapping.pop(0)
    while text and text[-1] == " ":
        text.pop()
        mapping.pop()
    normalized = "".join(text)
    if normalized != canonicalize_text(raw):
        raise EvidenceBindingError("UNSUPPORTED_NORMALIZATION")
    return normalized, mapping


def resolve_evidence_binding_v2(selection: dict, catalog: SourceEvidenceCatalog,
                                context: SourcePieceContext) -> EvidenceBinding:
    validate_catalog(catalog, context)
    if not isinstance(selection, dict) or "evidence_ref" not in selection or selection.keys() - EVIDENCE_SELECTION_FIELDS:
        raise EvidenceBindingError("INVALID_EVIDENCE_SELECTION")
    ref = selection["evidence_ref"]
    unit = next((u for u in catalog.units if u.evidence_ref == ref), None)
    if unit is None:
        raise EvidenceBindingError("FOREIGN_EVIDENCE_REF")
    pointer = selection.get("evidence_pointer", "")
    if not isinstance(pointer, str):
        raise EvidenceBindingError("INVALID_EVIDENCE_POINTER")
    selector = selection.get("evidence_selector")
    occurrence = selection.get("evidence_occurrence")
    requested = selection.get("evidence_mode")
    if requested is not None and requested not in ("WHOLE_UNIT", "RAW_SUBSPAN", "NORMALIZED_SUBSPAN"):
        raise EvidenceBindingError("INVALID_EVIDENCE_MODE")
    if "evidence_occurrence" in selection and (type(occurrence) is not int or occurrence <= 0):
        raise EvidenceBindingError("INVALID_EVIDENCE_OCCURRENCE")
    if "evidence_selector" not in selection:
        if "evidence_occurrence" in selection or requested in ("RAW_SUBSPAN", "NORMALIZED_SUBSPAN"):
            raise EvidenceBindingError("EVIDENCE_SELECTOR_REQUIRED")
        lo, hi, excerpt, mode = 0, len(unit.exact_text), unit.exact_text, "WHOLE_UNIT"
    else:
        if not isinstance(selector, str) or not selector or requested == "WHOLE_UNIT":
            raise EvidenceBindingError("INVALID_EVIDENCE_SELECTOR")
        positions = _positions(unit.exact_text, selector) if requested != "NORMALIZED_SUBSPAN" else []
        candidates = [(p, p + len(selector)) for p in positions]
        mode = "RAW_SUBSPAN"
        if not candidates and requested != "RAW_SUBSPAN":
            normalized, spans = _normalized_with_spans(unit.exact_text)
            target = canonicalize_text(selector)
            if not target or target != selector:
                raise EvidenceBindingError("UNSUPPORTED_NORMALIZED_SELECTOR")
            candidates = []
            for p in _positions(normalized, target):
                a, b = spans[p][0], spans[p + len(target) - 1][1]
                # Partial NFKC expansions and discontinuous/incorrect provenance fail.
                if canonicalize_text(unit.exact_text[a:b]) == target and (a, b) not in candidates:
                    candidates.append((a, b))
            mode = "NORMALIZED_SUBSPAN"
        if not candidates:
            raise EvidenceBindingError("EVIDENCE_SELECTOR_NOT_FOUND")
        candidates.sort()
        if len(candidates) > 1 and occurrence is None:
            raise EvidenceBindingError("EVIDENCE_SELECTOR_AMBIGUOUS")
        chosen = occurrence if occurrence is not None else 1
        if chosen > len(candidates):
            raise EvidenceBindingError("INVALID_EVIDENCE_OCCURRENCE")
        lo, hi = candidates[chosen - 1]
        raw = unit.exact_text[lo:hi]
        excerpt = raw if mode == "RAW_SUBSPAN" else canonicalize_text(raw)
    start, end = unit.source_start + lo, unit.source_start + hi
    raw = context.piece.source_text[start:end]
    raw_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    values = {"binding_version": SOURCE_ANALYSIS_EVIDENCE_BINDING_VERSION, "evidence_ref": ref,
              "mode": mode, "source_start": start, "source_end": end, "source_locator": unit.locator,
              "evidence_excerpt": excerpt, "evidence_pointer": pointer, "raw_excerpt_sha256": raw_sha}
    return EvidenceBinding(**values, binding_sha256=identity(values))
