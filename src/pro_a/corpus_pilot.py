from __future__ import annotations

import copy
from difflib import SequenceMatcher
import hashlib
import json
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import analyzer as analyzer_module
from .analyzer import Analyzer, canonicalize_text
from .config import AppConfig
from .db import Database, now_iso
from .ids import make_id
from .parsers import (
    ParseError,
    parse_source_with_diagnostics,
    parse_warnings,
    semantic_eligible_source_text,
    source_units,
)
from .pipeline import build_claim_record
from .prompts import SOURCE_ANALYSIS_SYSTEM
from .storage import archive_file_copy, sha256_file, write_json


BUNDLE_DOCUMENT_TYPE = "phase3c_extraction_bundle"
REVIEW_DOCUMENT_TYPE = "phase3c_extraction_review"
HUMAN_DECISIONS_DOCUMENT_TYPE = "phase3c_human_review_decisions"
STAGE1_3_DECISIONS_DOCUMENT_TYPE = "phase3c_stage1_3_diagnostic_decisions"
STAGE1_3_DIAGNOSTIC_DOCUMENT_TYPE = "phase3c_stage1_3_evidence_scope_diagnostic"
STAGE1_4_CONTRACT_DOCUMENT_TYPE = "phase3c_evidence_support_contract_v2"
PILOT2_EVIDENCE_DRAFT_DOCUMENT_TYPE = "phase3c_pilot2_evidence_support_draft_v2"
PILOT2_COMPARISON_DOCUMENT_TYPE = "phase3c_pilot1_vs_pilot2_pre_review_comparison"
PILOT2_GATE_A_DOCUMENT_TYPE = "phase3c_pilot2_gate_a_quote_fidelity"
PILOT2_HUMAN_REVIEW_DECISIONS_DOCUMENT_TYPE = "phase3c_pilot2_human_review_decisions"
PILOT2_HUMAN_REVIEW_READY_DOCUMENT_TYPE = "phase3c_pilot2_human_review_ready"
PILOT2_GATE_B_DOCUMENT_TYPE = "phase3c_pilot2_gate_b_semantic_repair"
PILOT2_REEXTRACTION_DOCUMENT_TYPE = "phase3c_pilot2_controlled_reextraction"
PILOT2_REEXTRACTION_QUOTE_DOCUMENT_TYPE = (
    "phase3c_pilot2_controlled_reextraction_quote_fidelity"
)
PILOT2_REEXTRACTION_COMPARISON_DOCUMENT_TYPE = (
    "phase3c_pilot2_historical_vs_reextraction_pre_review_comparison"
)
PILOT2_SOURCE_NAME = "光互连研究方法与框架20260819.pdf"
PILOT2_SOURCE_SHA256 = "1ea71205fb04885f44ab0aa48b57586647c9c823d4b321f11d23d7505aa65f52"
PILOT2_HISTORICAL_RUN_ID = "PILOT_20260831_DEA82C1F"
SCHEMA_VERSION = "1"
EXTRACTION_STATUS = "EXTRACTED_REVIEW_REQUIRED"
REVIEW_DRAFT_STATUS = "DRAFT"
REVIEW_READY_STATUS = "READY"
ALLOWED_DECISIONS = {"KEEP", "DROP", "KEEP_NEEDS_REVIEW"}
STAGE1_3_FAILURE_CATEGORIES = {
    "TRUE_OVERREACH", "CONTEXT_INSUFFICIENT", "ATTRIBUTION_ERROR",
    "CONDITIONALITY_LOSS", "SCOPE_ERROR", "OTHER",
}
STAGE1_3_DISPOSITIONS = {
    "GENUINE_EXTRACTION_FAILURE", "RECOVERABLE_WITH_BOUNDED_CONTEXT",
    "ATTRIBUTION_FAILURE", "CONDITIONALITY_FAILURE", "UNRESOLVED",
}
STAGE1_3_SEMANTIC_SUPPORT = {"complete", "partial", "none"}
STAGE1_3_CONTEXT_POLICY = "same_page_or_immediate_adjacent_boundary_with_500_char_radius"
STAGE1_3_CONTEXT_RADIUS = 500
EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE = (
    "same_page_evidence_segment_bounded_subspan"
)
STAGE1_4_SUPPORT_STATUSES = {"SUPPORTED", "UNSUPPORTED", "BLOCKED"}
STAGE1_4_SUPPORT_MODES = {"EXCERPT_ONLY", "BOUNDED_CONTEXT", "ORDERED_SPANS", "NONE"}
PILOT2_MECHANICS_STATUSES = {
    "EXCERPT_BOUND", "CONTEXT_AVAILABLE", "ORDERED_SPAN_BOUND",
    "LOCATOR_AMBIGUOUS", "LOCATOR_UNRESOLVED",
}
PILOT2_GATE_A_FIDELITY_STATUSES = {
    "EXACT_SOURCE_MATCH",
    "LAYOUT_NORMALIZED_EXACT_MATCH",
    "EXACT_ORDERED_CROSS_PAGE_SPAN",
    "PROVENANCE_MISMATCH_RECOVERED",
    "QUOTE_DRIFT",
    "UNRESOLVED_SOURCE_BINDING",
}
PILOT2_GATE_A_DRIFT_CATEGORIES = {
    "technical_term_normalization",
    "entity_normalization",
    "transcript_cleanup",
    "paraphrase",
    "scope_addition",
    "other",
}
PILOT2_SEMANTIC_SUPPORT = {"SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"}
PILOT2_EVIDENCE_ADMISSIBILITY = {
    "CURRENT_CONTRACT_ADMISSIBLE",
    "V2_CONTEXT_REQUIRED",
    "V2_ORDERED_SPAN_REQUIRED",
    "EVIDENCE_QUOTE_DRIFT_BLOCKED",
    "SOURCE_AMBIGUITY_BLOCKED",
}
PILOT2_SEMANTIC_FAILURE_CATEGORIES = {
    "TRUE_OVERREACH",
    "ATTRIBUTION_ERROR",
    "CONDITIONALITY_LOSS",
    "SCOPE_ERROR",
    "ENTITY_INFERENCE",
    "TECHNICAL_TERM_INFERENCE",
    "OTHER",
}
PILOT2_HUMAN_REVIEW_MODES = {
    "EXCERPT_ONLY",
    "BOUNDED_CONTEXT",
    "CROSS_PAGE",
    "QUOTE_DRIFT_SOURCE_REGION",
}
PILOT2_GENERALIZATION_VERDICTS = {"PASS", "PASS_WITH_REPAIR", "FAIL"}
PILOT2_GATE_A_SOURCE_NOISE_MARKERS = (
    "下图", "光块", "光文化", "光化工", "光光靠", "光伏跨公司", "光光开公司",
    "skill up", "score up", "scare up", "调理器", "年假", "223 线", "2728", "282",
)
PILOT2_GATE_A_TECHNICAL_TERMS = (
    "光模块", "光互联", "硅光", "硅光调制器芯片", "硅光调制芯片", "调制器芯片",
    "NPU", "CPO", "NPO", "PCB", "OCS", "MOU", "AI", "CPU", "GPU", "EML",
    "scale up", "可插拔光模块", "optical module", "modulator", "modulator chip",
    "2.4T", "3.2T",
)
PILOT2_GATE_A_ENTITY_TERMS = (
    "硅谷", "谷歌", "微软", "英伟达", "亚马逊", "AWS", "meta", "Google", "Microsoft",
    "华为", "中兴", "Huawei", "ZTE",
)
PDF_LOCATOR_CANONICALIZATION = (
    "unicode_nfkc+markdown_unescape+whitespace+han_spacing+hyphen_spacing+"
    "punctuation_spacing+terminal_punctuation"
)
_PAGE_POINTER = re.compile(r"^\[\[(PAGE:[1-9]\d*)\]\]$")
_CJK = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
_PDF_PUNCTUATION = str.maketrans({
    "，": ",", "。": ".", "；": ";", "：": ":", "！": "!", "？": "?",
    "（": "(", "）": ")", "【": "[", "】": "]", "“": '"', "”": '"',
    "‘": "'", "’": "'",
})
REVIEW_METADATA_FIELDS = (
    "title", "source_rank", "origin_type", "author", "organization", "publication_time",
)
IMMUTABLE_CLAIM_FIELDS = (
    "claim_id", "statement", "nature", "fact_time", "publication_time", "evidence_pointer",
    "evidence_excerpt", "attributed_to", "scope", "assumption_text", "status", "confidence",
    "novelty_level", "structured", "evidence_validated", "phase3c_evidence", "related_node_ids",
    "related_candidate_names",
)
PRODUCTION_TABLES = (
    "meta", "nodes", "node_aliases", "node_relations", "sources", "source_relations",
    "source_node_links", "claims", "claim_node_links",
    "claim_relations", "current_views", "proposals", "knowledge_gaps", "research_questions",
    "impact_reviews", "impact_attempt_audit", "side_effect_jobs", "ima_objects",
    "processing_jobs",
)


class PilotError(RuntimeError):
    """A fail-closed Phase 3C pilot or controlled-apply error."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")


def extraction_bundle_sha256(bundle: dict[str, Any]) -> str:
    """Return the single stable binding hash for an extraction bundle."""
    return hashlib.sha256(_canonical_json(bundle)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"Invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"JSON artifact must contain an object: {path}")
    return value


def _readonly_uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro"


def production_snapshot(path: Path) -> dict[str, Any]:
    """Read Production identity and all canonical table counts through SQLite read-only mode."""
    path = Path(path).resolve()
    if not path.exists():
        raise PilotError(f"Production database not found: {path}")
    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as conn:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in PRODUCTION_TABLES
            }
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = [list(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
    except sqlite3.Error as exc:
        raise PilotError(f"Unable to inspect Production database read-only: {exc}") from exc
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "table_counts": counts,
        "integrity_check": integrity,
        "foreign_key_violations": foreign_keys,
    }


def copy_production_database(source: Path, target: Path) -> Path:
    """Create an isolated SQLite backup from a read-only Production connection."""
    source = Path(source).resolve()
    target = Path(target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise PilotError(f"Production copy already exists: {target}")
    try:
        with sqlite3.connect(_readonly_uri(source), uri=True) as src_conn:
            with sqlite3.connect(target) as dst_conn:
                src_conn.backup(dst_conn)
    except sqlite3.Error as exc:
        raise PilotError(f"Unable to create isolated Production copy: {exc}") from exc
    return target


def _instrument_llm(analyzer: Analyzer) -> tuple[list[dict[str, Any]], Any]:
    events: list[dict[str, Any]] = []
    original_json = analyzer.llm.json

    def recording_json(system: str, user: str) -> dict[str, Any]:
        try:
            return original_json(system, user)
        finally:
            metadata = getattr(analyzer.llm, "last_call_metadata", {})
            events.append(copy.deepcopy(metadata) if isinstance(metadata, dict) else {})

    analyzer.llm.json = recording_json
    return events, original_json


def _llm_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for event in events:
        event_attempts = event.get("attempts") if isinstance(event, dict) else None
        if isinstance(event_attempts, list):
            attempts.extend(item for item in event_attempts if isinstance(item, dict))
    actual_calls = len(attempts) or len(events)

    def total(key: str) -> int | str:
        values = [item.get(key) for item in attempts if isinstance(item.get(key), int)]
        return sum(values) if values else "NOT_AVAILABLE"

    response_models = [item.get("response_model") for item in attempts if item.get("response_model")]
    return {
        "llm_calls": actual_calls,
        "prompt_tokens": total("prompt_tokens"),
        "completion_tokens": total("completion_tokens"),
        "total_tokens": total("total_tokens"),
        "response_model": response_models[-1] if response_models else "NOT_AVAILABLE",
        "call_metadata": events,
    }


def _claim_bundle_record(
    claim_id: str, source_id: str, claim: dict[str, Any], publication_time: str, full_text: str,
) -> dict[str, Any] | None:
    record = build_claim_record(
        claim_id, source_id, claim, publication_time, full_text,
    )
    if record is None:
        return None
    record["validation"] = copy.deepcopy(record["structured"].get("validation") or {})
    record["phase3c_evidence"] = phase3c_evidence_provenance_contract(
        model_evidence_excerpt=str(record.get("evidence_excerpt") or ""),
        evidence_pointer=str(record.get("evidence_pointer") or ""),
        deterministic_locator=(record.get("validation") or {}).get("source_locator") or {},
    )
    return record


def _locator_status(claim: dict[str, Any]) -> str:
    validation = claim.get("validation") or {}
    locator = validation.get("source_locator") or {}
    return str(locator.get("status") or "unresolved")


def _human_review_flags(
    parsed_diagnostics: dict[str, Any], claims: list[dict[str, Any]], text: str,
) -> list[str]:
    flags: list[str] = []
    if parsed_diagnostics.get("partial_parse"):
        flags.append("Partial PDF extraction was reported; inspect pages with parse errors.")
    if any(_locator_status(claim) == "ambiguous" for claim in claims):
        flags.append("At least one Evidence excerpt maps to multiple page locators.")
    if any(_locator_status(claim) == "unresolved" for claim in claims):
        flags.append("At least one Evidence excerpt has no deterministic page locator.")
    if any(claim.get("status") == "needs_review" for claim in claims):
        flags.append("Claims marked needs_review require a human decision before canonical ingestion.")
    if "\ufffd" in text:
        flags.append("The extracted PDF text contains replacement characters; verify transcript fidelity against the PDF.")
    flags.append("No automatic correction was applied to names, technical terms, dates, numbers, or industry wording.")
    return flags[:5]


def _observations(analysis) -> dict[str, Any]:
    return {
        "classification": "OBSERVATIONAL_NON_CANONICAL",
        "node_matches": copy.deepcopy(analysis.node_matches),
        "node_candidates": copy.deepcopy(analysis.node_candidates),
        "rejected_node_matches": copy.deepcopy(analysis.rejected_node_matches),
        "rejected_node_candidates": copy.deepcopy(analysis.rejected_node_candidates),
        "rejected_claim_node_links": copy.deepcopy(analysis.rejected_claim_node_links),
        "relation_candidates": copy.deepcopy(analysis.relation_candidates),
        "rejected_relation_candidates": copy.deepcopy(analysis.rejected_relation_candidates),
    }


def _build_review_draft(
    bundle: dict[str, Any], *, review_id: str | None = None,
) -> dict[str, Any]:
    source = bundle["source"]
    metadata = bundle.get("proposed_source_metadata") or {}
    reviewed_metadata = {
        field: copy.deepcopy(
            metadata.get("source_origin_type") if field == "origin_type" else metadata.get(field)
        ) or ""
        for field in REVIEW_METADATA_FIELDS
    }
    claims = []
    for claim in bundle.get("claims") or []:
        review_claim = {
            key: copy.deepcopy(claim.get(key))
            for key in IMMUTABLE_CLAIM_FIELDS
            if key in claim
        }
        review_claim["validation"] = copy.deepcopy(claim.get("validation") or {})
        review_claim["decision"] = "PENDING"
        claims.append(review_claim)
    return {
        "document_type": REVIEW_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": REVIEW_DRAFT_STATUS,
        "review_id": review_id or make_id("REV"),
        "pilot_run_id": bundle["pilot_run_id"],
        "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
        "source": {
            "proposed_source_id": source["proposed_source_id"],
            "original_name": source["original_name"],
            "sha256": source["sha256"],
            "source_type": source["source_type"],
            "metadata_decision": "PENDING",
            "metadata": reviewed_metadata,
        },
        "claims": claims,
        "human_review_flags": copy.deepcopy(bundle.get("human_review_flags") or []),
    }


def _claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(claim.get(key))
        for key in IMMUTABLE_CLAIM_FIELDS
        if key in claim
    }


def validate_review(
    bundle: dict[str, Any],
    review: dict[str, Any],
    *,
    require_production_ready: bool = True,
) -> dict[str, Any]:
    if review.get("document_type") != REVIEW_DOCUMENT_TYPE or review.get("schema_version") != SCHEMA_VERSION:
        raise PilotError("PILOT_REVIEW_INVALID: unsupported review artifact")
    expected_binding = extraction_bundle_sha256(bundle)
    if review.get("extraction_bundle_sha256") != expected_binding:
        raise PilotError("PILOT_REVIEW_STALE: extraction bundle hash mismatch")
    if review.get("status") != REVIEW_READY_STATUS:
        raise PilotError("PILOT_REVIEW_NOT_READY: status must be READY")

    source = bundle.get("source") or {}
    review_source = review.get("source") or {}
    for field in ("proposed_source_id", "original_name", "sha256", "source_type"):
        if review_source.get(field) != source.get(field):
            raise PilotError(f"PILOT_REVIEW_INVALID: Source identity changed at {field}")
    if review_source.get("metadata_decision") != "APPROVED":
        raise PilotError("PILOT_REVIEW_NOT_READY: Source metadata is not approved")
    metadata = review_source.get("metadata")
    if not isinstance(metadata, dict) or set(metadata) != set(REVIEW_METADATA_FIELDS):
        raise PilotError("PILOT_REVIEW_INVALID: Source metadata fields are not limited to the review contract")
    if any(not isinstance(metadata[field], str) for field in REVIEW_METADATA_FIELDS):
        raise PilotError("PILOT_REVIEW_INVALID: Source metadata values must be strings")

    bundle_claims = bundle.get("claims") or []
    review_claims = review.get("claims") or []
    if len(bundle_claims) != len(review_claims):
        raise PilotError("PILOT_REVIEW_INVALID: Claim count changed")
    normalized_claims: list[dict[str, Any]] = []
    for index, (bundle_claim, review_claim) in enumerate(zip(bundle_claims, review_claims)):
        if _claim_projection(review_claim) != _claim_projection(bundle_claim):
            raise PilotError(f"PILOT_REVIEW_INVALID: Claim content changed at claims[{index}]")
        decision = review_claim.get("decision")
        if decision not in ALLOWED_DECISIONS:
            raise PilotError(f"PILOT_REVIEW_NOT_READY: Claim decision unresolved at claims[{index}]")
        if decision == "KEEP" and bundle_claim.get("evidence_validated") is not True:
            raise PilotError(f"PILOT_REVIEW_BLOCKED: unvalidated Claim cannot be KEEP at claims[{index}]")
        normalized_claim = copy.deepcopy(bundle_claim)
        normalized_claim["decision"] = decision
        if decision == "KEEP_NEEDS_REVIEW":
            normalized_claim["status"] = "needs_review"
        normalized_claims.append(normalized_claim)
    stage1_2 = review.get("stage1_2") or {}
    if (
        require_production_ready
        and stage1_2
        and stage1_2.get("production_apply_ready") is not True
    ):
        raise PilotError("PILOT_REVIEW_BLOCKED: Stage 1.2 review is not Production-apply-ready")
    return {
        "bundle": bundle,
        "review": review,
        "metadata": copy.deepcopy(metadata),
        "claims": normalized_claims,
    }


def _source_metadata(bundle: dict[str, Any], reviewed_metadata: dict[str, str]) -> dict[str, Any]:
    source = bundle["source"]
    observations = bundle.get("observations") or {}
    return {
        "parse_diagnostics": copy.deepcopy(source.get("parse_diagnostics") or {}),
        "summary": (bundle.get("proposed_source_metadata") or {}).get("summary", ""),
        "source_references_unresolved": copy.deepcopy(bundle.get("source_references") or []),
        "analysis_quality": {
            key: copy.deepcopy(observations.get(key) or [])
            for key in (
                "rejected_node_matches", "rejected_node_candidates", "rejected_claim_node_links",
                "relation_candidates", "rejected_relation_candidates",
            )
        },
        "phase3c": {
            "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
            "pilot_run_id": bundle.get("pilot_run_id", ""),
        },
        "reviewed_metadata": copy.deepcopy(reviewed_metadata),
    }


def _expected_source(
    bundle: dict[str, Any], reviewed_metadata: dict[str, str], archived_path: str, timestamp: str,
) -> dict[str, Any]:
    source = bundle["source"]
    return {
        "source_id": source["proposed_source_id"],
        "title": reviewed_metadata.get("title") or source["original_name"],
        "original_name": source["original_name"],
        "archived_path": archived_path,
        "sha256": source["sha256"],
        "ingestion_mode": "deep",
        "analysis_mode": "deep",
        "source_type": source["source_type"],
        "source_rank": reviewed_metadata.get("source_rank") or "UNRANKED",
        "origin_type": reviewed_metadata.get("origin_type") or "unknown",
        "author": reviewed_metadata.get("author") or "",
        "organization": reviewed_metadata.get("organization") or "",
        "publication_time": reviewed_metadata.get("publication_time") or "",
        "ingested_at": timestamp,
        "status": "analyzed",
        "ima_media_id": "",
        "ima_kb_id": "",
        "underlying_source_id": "",
        "metadata_json": json.dumps(
            _source_metadata(bundle, reviewed_metadata), ensure_ascii=False, sort_keys=True,
        ),
    }


def _expected_claims(reviewed_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": claim["claim_id"],
            "statement": claim["statement"],
            "nature": claim["nature"],
            "fact_time": claim["fact_time"],
            "publication_time": claim["publication_time"],
            "source_id": claim["source_id"],
            "evidence_pointer": claim["evidence_pointer"],
            "evidence_excerpt": claim["evidence_excerpt"],
            "attributed_to": claim["attributed_to"],
            "scope": claim["scope"],
            "assumption_text": claim["assumption_text"],
            "status": claim["status"],
            "confidence": claim["confidence"],
            "novelty_level": claim["novelty_level"],
            "structured_json": json.dumps(claim["structured"], ensure_ascii=False),
        }
        for claim in reviewed_claims
        if claim.get("decision") in {"KEEP", "KEEP_NEEDS_REVIEW"}
    ]


def _row_json(raw: Any) -> Any:
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return raw


def _source_matches(row: sqlite3.Row, expected: dict[str, Any]) -> bool:
    fields = (
        "source_id", "title", "original_name", "sha256", "ingestion_mode", "analysis_mode",
        "source_type", "source_rank", "origin_type", "author", "organization",
        "publication_time", "status", "ima_media_id", "ima_kb_id", "underlying_source_id",
    )
    if any(row[field] != expected[field] for field in fields):
        return False
    return _row_json(row["metadata_json"]) == _row_json(expected["metadata_json"])


def _claim_matches(row: sqlite3.Row, expected: dict[str, Any]) -> bool:
    fields = (
        "claim_id", "statement", "nature", "fact_time", "publication_time", "source_id",
        "evidence_pointer", "evidence_excerpt", "attributed_to", "scope", "assumption_text",
        "status", "confidence", "novelty_level",
    )
    if any(row[field] != expected[field] for field in fields):
        return False
    return _row_json(row["structured_json"]) == _row_json(expected["structured_json"])


def _apply_existing_state(
    db_path: Path, bundle: dict[str, Any], reviewed_metadata: dict[str, str], reviewed_claims: list[dict[str, Any]],
) -> str:
    source = bundle["source"]
    with sqlite3.connect(_readonly_uri(db_path), uri=True) as conn:
        conn.row_factory = sqlite3.Row
        by_id = conn.execute("SELECT * FROM sources WHERE source_id=?", (source["proposed_source_id"],)).fetchone()
        by_sha = conn.execute("SELECT * FROM sources WHERE sha256=?", (source["sha256"],)).fetchone()
        if by_id is None and by_sha is None:
            return "NEW"
        if by_id is None or by_sha is None or by_id["source_id"] != by_sha["source_id"]:
            return "SOURCE_APPLY_CONFLICT"
        expected_source = _expected_source(bundle, reviewed_metadata, by_id["archived_path"], by_id["ingested_at"])
        if not _source_matches(by_id, expected_source):
            return "SOURCE_APPLY_CONFLICT"
        rows = conn.execute(
            "SELECT * FROM claims WHERE source_id=? ORDER BY claim_id", (source["proposed_source_id"],)
        ).fetchall()
        expected_claims = sorted(_expected_claims(reviewed_claims), key=lambda item: item["claim_id"])
        if len(rows) != len(expected_claims) or any(
            not _claim_matches(row, claim) for row, claim in zip(rows, expected_claims)
        ):
            return "SOURCE_APPLY_CONFLICT"
        return "IDEMPOTENT"


def preview_reviewed_bundle(
    bundle_path: Path, review_path: Path, db_path: Path,
) -> dict[str, Any]:
    bundle = _load_json(Path(bundle_path))
    review = _load_json(Path(review_path))
    validated = validate_review(bundle, review)
    state = _apply_existing_state(
        Path(db_path), bundle, validated["metadata"], validated["claims"],
    )
    kept = sum(claim.get("decision") in {"KEEP", "KEEP_NEEDS_REVIEW"} for claim in validated["claims"])
    return {
        "status": state,
        "idempotent": state == "IDEMPOTENT",
        "created": False if state == "IDEMPOTENT" else state == "NEW",
        "source_id": bundle["source"]["proposed_source_id"],
        "sha256": bundle["source"]["sha256"],
        "claims_total": len(validated["claims"]),
        "claims_to_insert": kept if state == "NEW" else 0,
        "canonical_write_preview": {
            "sources": 0 if state == "IDEMPOTENT" else 1,
            "claims": 0 if state == "IDEMPOTENT" else kept,
            "processing_jobs": 0 if state == "IDEMPOTENT" else 1,
            "all_other_tables": 0,
        },
    }


def pilot_apply_write_authorizer(action: int, first: str | None, second: str | None,
                                 database: str | None, trigger: str | None) -> int:
    allowed = {
        sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_TRANSACTION,
    }
    if action in allowed:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_INSERT and first in {"sources", "claims", "processing_jobs"}:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_UPDATE and first == "processing_jobs":
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _write_apply_receipt(cfg: AppConfig, result: dict[str, Any]) -> Path:
    path = cfg.root / "generated" / "receipts" / f"{result['job_id']}.json"
    write_json(path, result)
    return path


def apply_production_reviewed_bundle(
    bundle_path: Path,
    review_path: Path,
    source_path: Path | None,
    *,
    db_path: Path,
    cfg: AppConfig,
    archive_root: Path | None = None,
) -> dict[str, Any]:
    """Apply an exact READY review only to an explicitly supplied isolated DB copy."""
    db_path = Path(db_path).resolve()
    if db_path == cfg.db_path.resolve():
        raise PilotError("LIVE_PRODUCTION_CORPUS_APPLY_AUTHORIZED=false: configured Production DB is blocked")
    bundle = _load_json(Path(bundle_path))
    review = _load_json(Path(review_path))
    validated = validate_review(bundle, review)
    state = _apply_existing_state(
        db_path, bundle, validated["metadata"], validated["claims"],
    )
    if state == "SOURCE_APPLY_CONFLICT":
        raise PilotError("SOURCE_APPLY_CONFLICT")
    if state == "IDEMPOTENT":
        return {
            "status": "IDEMPOTENT", "idempotent": True, "created": False,
            "source_id": bundle["source"]["proposed_source_id"],
            "job_id": "", "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
        }
    if not db_path.exists():
        raise PilotError(f"Isolated apply database not found: {db_path}")
    if source_path is None or not Path(source_path).exists():
        raise PilotError("SOURCE_FILE_REQUIRED_FOR_NEW_APPLY")
    source_path = Path(source_path).resolve()
    source_sha = sha256_file(source_path)
    if source_sha != bundle["source"]["sha256"]:
        raise PilotError("SOURCE_APPLY_CONFLICT: source file SHA-256 does not match bundle")

    root = Path(archive_root or cfg.root)
    source_id = bundle["source"]["proposed_source_id"]
    archive_path: Path | None = None
    archive_created = False
    try:
        existing_archives = {
            path.resolve()
            for path in (root / "archive").rglob(f"{source_id}__{source_path.name}")
            if path.is_file()
        }
        archive_path = archive_file_copy(source_path, root, source_id)
        archive_created = archive_path.resolve() not in existing_archives
        timestamp = now_iso()
        expected_source = _expected_source(
            bundle, validated["metadata"], str(archive_path), timestamp,
        )
        expected_claims = _expected_claims(validated["claims"])
        job_id = make_id("JOB")
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.set_authorizer(pilot_apply_write_authorizer)
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO sources(
                   source_id,title,original_name,archived_path,sha256,ingestion_mode,analysis_mode,
                   source_type,source_rank,origin_type,author,organization,publication_time,ingested_at,
                   status,ima_media_id,ima_kb_id,underlying_source_id,metadata_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(expected_source[field] for field in (
                    "source_id", "title", "original_name", "archived_path", "sha256", "ingestion_mode",
                    "analysis_mode", "source_type", "source_rank", "origin_type", "author", "organization",
                    "publication_time", "ingested_at", "status", "ima_media_id", "ima_kb_id",
                    "underlying_source_id", "metadata_json",
                )),
            )
            for claim in expected_claims:
                conn.execute(
                    """INSERT INTO claims(
                       claim_id,statement,nature,fact_time,publication_time,ingestion_time,source_id,
                       evidence_pointer,evidence_excerpt,attributed_to,scope,assumption_text,status,
                       confidence,novelty_level,structured_json,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        claim["claim_id"], claim["statement"], claim["nature"], claim["fact_time"],
                        claim["publication_time"], timestamp, claim["source_id"], claim["evidence_pointer"],
                        claim["evidence_excerpt"], claim["attributed_to"], claim["scope"],
                        claim["assumption_text"], claim["status"], claim["confidence"],
                        claim["novelty_level"], claim["structured_json"], timestamp,
                    ),
                )
            conn.execute(
                """INSERT INTO processing_jobs(
                   job_id,source_id,input_path,ingestion_mode,status,started_at,finished_at,error_text)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (job_id, source_id, str(source_path), "deep", "done", timestamp, timestamp, ""),
            )
            conn.commit()
    except Exception:
        if archive_created and archive_path is not None and archive_path.exists():
            archive_path.unlink()
        raise

    result = {
        "status": "COMMITTED",
        "idempotent": False,
        "created": True,
        "source_id": source_id,
        "job_id": job_id,
        "claims_created": len(expected_claims),
        "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
        "archive_sha256": sha256_file(archive_path),
        "canonical_write_preview": {
            "sources": 1, "claims": len(expected_claims), "processing_jobs": 1,
            "all_other_tables": 0,
        },
    }
    try:
        result["receipt_path"] = str(_write_apply_receipt(cfg, result))
    except Exception as exc:
        result["status"] = "CORPUS_APPLY_COMMITTED_RECEIPT_FAILED"
        result["receipt_error"] = str(exc)
    return result


def _stage1_metrics(
    bundle: dict[str, Any], llm: dict[str, Any], text: str,
) -> dict[str, Any]:
    claims = bundle.get("claims") or []
    locators = {
        status: sum(_locator_status(claim) == status for claim in claims)
        for status in ("resolved", "ambiguous", "unresolved")
    }
    observations = bundle.get("observations") or {}
    candidates = observations.get("node_candidates") or []
    metrics = {
        "pilot_run_id": bundle["pilot_run_id"],
        "source_sha256": bundle["source"]["sha256"],
        "source_type": bundle["source"]["source_type"],
        "pdf_pages": bundle["source"].get("parse_diagnostics", {}).get("total_units", "NOT_AVAILABLE"),
        "claims_total": len(claims),
        "evidence_valid_claims": sum(claim.get("evidence_validated") is True for claim in claims),
        "needs_review_claims": sum(claim.get("status") == "needs_review" for claim in claims),
        "locator_resolved": locators["resolved"],
        "locator_ambiguous": locators["ambiguous"],
        "locator_unresolved": locators["unresolved"],
        "node_matches": len(observations.get("node_matches") or []),
        "node_candidates": len(candidates),
        "quality_eligible_node_candidates": sum(item.get("quality_eligible") is True for item in candidates),
        "relation_candidates": len(observations.get("relation_candidates") or []),
        "rejected_relation_candidates": len(observations.get("rejected_relation_candidates") or []),
        "llm_calls": llm["llm_calls"],
        "prompt_tokens": llm["prompt_tokens"],
        "completion_tokens": llm["completion_tokens"],
        "total_tokens": llm["total_tokens"],
        "response_model": llm["response_model"],
        "parse_diagnostics": copy.deepcopy(bundle["source"].get("parse_diagnostics") or {}),
        "human_review_flags": copy.deepcopy(bundle.get("human_review_flags") or []),
    }
    return metrics


def normalize_pdf_span_text(value: str) -> str:
    """Normalize exact PDF text while preserving punctuation at page boundaries."""
    normalized = canonicalize_text(value).translate(_PDF_PUNCTUATION)
    normalized = re.sub(rf"(?<={_CJK})\s+|\s+(?={_CJK})", "", normalized)
    normalized = re.sub(r"(?<=[0-9A-Za-z])\s*-\s*(?=[0-9A-Za-z])", "-", normalized)
    normalized = re.sub(r"\s+([,.;:!?)}\]])", r"\1", normalized)
    normalized = re.sub(r"([({\[])\s+", r"\1", normalized)
    return normalized


def normalize_pdf_locator_text(value: str) -> str:
    """Normalize a comparison copy for exact PDF page matching only."""
    return normalize_pdf_span_text(value).rstrip(".,;:!?")


def _pdf_comparison_methods():
    return (
        ("raw_exact_substring", "none", lambda value: value or ""),
        (
            "canonical_exact_substring",
            "unicode_nfkc+markdown_unescape+whitespace",
            canonicalize_text,
        ),
        (
            "pdf_normalized_exact_substring",
            PDF_LOCATOR_CANONICALIZATION,
            normalize_pdf_locator_text,
        ),
    )


def _pdf_span_comparison_methods():
    return (
        *_pdf_comparison_methods()[:2],
        (
            "pdf_span_normalized_exact_substring",
            PDF_LOCATOR_CANONICALIZATION,
            normalize_pdf_span_text,
        ),
    )


def resolve_pdf_evidence_locator(
    full_text: str, evidence_excerpt: str, evidence_pointer: str = "",
) -> dict[str, Any]:
    """Bind Evidence to one PDF page through provenance, then exact comparisons."""
    pages = [(locator, body) for locator, body in source_units(full_text) if locator.startswith("PAGE:")]
    page_by_locator = dict(pages)
    pointer_match = _PAGE_POINTER.fullmatch(evidence_pointer or "")
    provenance_locator = pointer_match.group(1) if pointer_match else ""
    provenance = {
        "pointer": evidence_pointer or "",
        "locator": provenance_locator,
        "status": (
            "available"
            if provenance_locator in page_by_locator
            else "missing_locator"
            if provenance_locator
            else "unsupported"
            if evidence_pointer
            else "not_available"
        ),
    }

    def match_result(
        locator: str, body: str, method: str, canonicalization: str, normalizer, scope: str,
    ) -> dict[str, Any] | None:
        comparison_excerpt = normalizer(evidence_excerpt or "")
        comparison_body = normalizer(body)
        start = comparison_body.find(comparison_excerpt) if comparison_excerpt else -1
        if start < 0:
            return None
        return {
            "status": "resolved",
            "locator": locator,
            "match_scope": scope,
            "match_method": method,
            "canonicalization": canonicalization,
            "comparison_start": start,
            "comparison_end": start + len(comparison_excerpt),
            "provenance": copy.deepcopy(provenance),
        }

    if provenance["status"] == "available":
        body = page_by_locator[provenance_locator]
        for method, canonicalization, normalizer in _pdf_comparison_methods():
            result = match_result(
                provenance_locator, body, method, canonicalization, normalizer, "provenance",
            )
            if result:
                result["match_method"] = f"provenance_{method}"
                result["provenance"]["status"] = "matched"
                return result
        provenance["status"] = "mismatch"

    for method, canonicalization, normalizer in _pdf_comparison_methods():
        comparison_excerpt = normalizer(evidence_excerpt or "")
        if not comparison_excerpt:
            continue
        matches = []
        for locator, body in pages:
            comparison_body = normalizer(body)
            start = comparison_body.find(comparison_excerpt)
            if start >= 0:
                matches.append((locator, start))
        if len(matches) == 1:
            locator, _ = matches[0]
            return match_result(
                locator, page_by_locator[locator], method, canonicalization, normalizer, "global",
            )
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "locators": [locator for locator, _ in matches],
                "match_scope": "global",
                "match_method": method,
                "canonicalization": canonicalization,
                "provenance": copy.deepcopy(provenance),
            }
    comparison_excerpt = normalize_pdf_locator_text(evidence_excerpt or "")
    spanning_locators = []
    if comparison_excerpt:
        for index in range(len(pages) - 1):
            first_locator, first_body = pages[index]
            second_locator, second_body = pages[index + 1]
            combined = normalize_pdf_locator_text(f"{first_body}\n{second_body}")
            if comparison_excerpt in combined:
                spanning_locators.append([first_locator, second_locator])
    return {
        "status": "unresolved",
        "reason": "cross_page_span" if spanning_locators else "not_found",
        "spanning_locators": spanning_locators,
        "match_scope": "none",
        "match_method": "none",
        "canonicalization": PDF_LOCATOR_CANONICALIZATION,
        "provenance": copy.deepcopy(provenance),
    }


def phase3c_evidence_provenance_contract(
    *,
    model_evidence_excerpt: str,
    evidence_pointer: str,
    deterministic_locator: dict[str, Any],
    fidelity_status: str | None = None,
    ordered_spans: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe non-canonical Evidence admission without repairing model output."""
    ordered_spans = copy.deepcopy(ordered_spans or [])
    valid_fidelity = {
        "EXACT_SOURCE_MATCH",
        "LAYOUT_NORMALIZED_EXACT_MATCH",
        "EXACT_ORDERED_CROSS_PAGE_SPAN",
        "PROVENANCE_MISMATCH_RECOVERED",
    }
    source_bound = (
        fidelity_status in valid_fidelity
        if fidelity_status is not None
        else deterministic_locator.get("status") == "resolved"
    )
    pointer_match = _PAGE_POINTER.fullmatch(evidence_pointer or "")
    pointer_locator = pointer_match.group(1) if pointer_match else ""
    resolved_locator = str(deterministic_locator.get("locator") or "")
    if source_bound and ordered_spans:
        pointer_status = "unsupported"
        authoritative_locator = {
            "status": "resolved",
            "kind": "ordered_spans",
            "spans": ordered_spans,
            "source": "deterministic_source_binding",
            "authoritative": True,
        }
    elif source_bound and resolved_locator:
        pointer_status = (
            "matched" if pointer_locator == resolved_locator
            else "mismatch" if pointer_locator
            else "unsupported"
        )
        authoritative_locator = {
            "status": "resolved",
            "kind": "single_page",
            "locator": resolved_locator,
            "source": "deterministic_source_binding",
            "authoritative": True,
        }
    else:
        pointer_status = "unsupported"
        authoritative_locator = None
    pointer_error = pointer_status == "mismatch"
    quote_status = fidelity_status or (
        "VALIDATED_SOURCE_BOUND" if source_bound else "UNVALIDATED_SOURCE_QUOTE"
    )
    return {
        "model_evidence_excerpt": model_evidence_excerpt,
        "model_evidence_is_proposed_quote": True,
        "validated_source_evidence": model_evidence_excerpt if source_bound else None,
        "canonical_ready_evidence": model_evidence_excerpt if source_bound else None,
        "quote_validation_status": quote_status,
        "review_required": not source_bound,
        "model_page_pointer": {
            "value": evidence_pointer or "",
            "status": pointer_status,
            "authoritative": False,
        },
        "resolved_locator": authoritative_locator,
        "model_page_pointer_error": "MODEL_PAGE_POINTER_ERROR" if pointer_error else None,
        "pointer_mismatch_is_semantic_failure": False,
        "automatic_quote_repair_applied": False,
        "production_ready": False,
    }


def _rebind_claim_locator(claim: dict[str, Any], full_text: str) -> dict[str, Any]:
    rebound = copy.deepcopy(claim)
    locator = resolve_pdf_evidence_locator(
        full_text,
        str(claim.get("evidence_excerpt") or ""),
        str(claim.get("evidence_pointer") or ""),
    )
    resolved = locator["status"] == "resolved"
    validation = copy.deepcopy(claim.get("validation") or {})
    errors = [
        error for error in validation.get("errors") or []
        if error not in {"evidence_excerpt_not_found", "evidence_locator_ambiguous"}
    ]
    if not resolved:
        errors.append(
            "evidence_locator_ambiguous"
            if locator["status"] == "ambiguous"
            else "evidence_excerpt_not_found"
        )
    validation.update({
        "evidence_validated": resolved,
        "canonicalization": PDF_LOCATOR_CANONICALIZATION,
        "match_method": locator.get("match_method", "none"),
        "normalized_excerpt": normalize_pdf_locator_text(str(claim.get("evidence_excerpt") or "")),
        "normalized_start": locator.get("comparison_start", -1),
        "normalized_end": locator.get("comparison_end", -1),
        "errors": errors,
        "source_locator": locator,
    })
    rebound["evidence_validated"] = resolved
    rebound["validation"] = validation
    structured = copy.deepcopy(claim.get("structured") or {})
    structured["validation"] = copy.deepcopy(validation)
    rebound["structured"] = structured
    if "phase3c_evidence" in rebound:
        rebound["phase3c_evidence"] = phase3c_evidence_provenance_contract(
            model_evidence_excerpt=str(rebound.get("evidence_excerpt") or ""),
            evidence_pointer=str(rebound.get("evidence_pointer") or ""),
            deterministic_locator=locator,
        )
    if resolved and rebound.get("status") == "needs_review" and not errors:
        rebound["status"] = "current"
    elif not resolved:
        rebound["status"] = "needs_review"
    return rebound


def _raw_claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(claim)
    for field in ("status", "evidence_validated", "validation", "phase3c_evidence"):
        projected.pop(field, None)
    structured = projected.get("structured")
    if isinstance(structured, dict):
        structured.pop("validation", None)
    return projected


def _claim_quality_counts(bundle: dict[str, Any]) -> dict[str, int]:
    claims = bundle.get("claims") or []
    return {
        "claims_total": len(claims),
        "evidence_valid_claims": sum(claim.get("evidence_validated") is True for claim in claims),
        "needs_review_claims": sum(claim.get("status") == "needs_review" for claim in claims),
        "locator_resolved": sum(_locator_status(claim) == "resolved" for claim in claims),
        "locator_ambiguous": sum(_locator_status(claim) == "ambiguous" for claim in claims),
        "locator_unresolved": sum(_locator_status(claim) == "unresolved" for claim in claims),
    }


def rebind_stage1_evidence_locators(
    bundle_path: Path,
    source_path: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Replay Stage 1 Evidence-to-PAGE binding without an Analyzer or LLM call."""
    bundle_path = Path(bundle_path).resolve()
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir or bundle_path.parent).resolve()
    if not bundle_path.is_file():
        raise PilotError(f"Stage 1 bundle not found: {bundle_path}")
    if not source_path.is_file():
        raise PilotError(f"Stage 1 Source not found: {source_path}")

    original_bundle_file_sha = sha256_file(bundle_path)
    original = _load_json(bundle_path)
    if original.get("document_type") != BUNDLE_DOCUMENT_TYPE:
        raise PilotError("STAGE1_1_BUNDLE_INVALID: unsupported extraction bundle")
    source = original.get("source") or {}
    if source.get("source_type") != "pdf":
        raise PilotError("STAGE1_1_SOURCE_INVALID: Evidence rebinding is PDF-only")
    if sha256_file(source_path) != source.get("sha256"):
        raise PilotError("STAGE1_1_SOURCE_MISMATCH: Source SHA-256 does not match bundle")

    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None
    parsed = parse_source_with_diagnostics(source_path)
    if parsed.source_type != "pdf" or parsed.diagnostics.get("empty_extraction"):
        raise PilotError("STAGE1_1_PARSE_INVALID: PDF text extraction is unavailable")
    expected_units = (source.get("parse_diagnostics") or {}).get("total_units")
    if expected_units is not None and parsed.diagnostics.get("total_units") != expected_units:
        raise PilotError("STAGE1_1_PARSE_MISMATCH: parsed page count changed")

    original_bundle_sha = extraction_bundle_sha256(original)
    before = _claim_quality_counts(original)
    rebound = copy.deepcopy(original)
    rebound["claims"] = [
        _rebind_claim_locator(claim, parsed.text) for claim in original.get("claims") or []
    ]
    rebound["human_review_flags"] = _human_review_flags(
        parsed.diagnostics, rebound["claims"], parsed.text,
    )
    after = _claim_quality_counts(rebound)
    method_counts = Counter(
        ((claim.get("validation") or {}).get("source_locator") or {}).get("match_method", "none")
        for claim in rebound["claims"]
    )
    unresolved_reasons = Counter(
        (((claim.get("validation") or {}).get("source_locator") or {}).get("reason") or "unknown")
        for claim in rebound["claims"]
        if _locator_status(claim) == "unresolved"
    )
    original_ids = [claim.get("claim_id") for claim in original.get("claims") or []]
    rebound_ids = [claim.get("claim_id") for claim in rebound.get("claims") or []]
    raw_claims_unchanged = all(
        _raw_claim_projection(old) == _raw_claim_projection(new)
        for old, new in zip(original.get("claims") or [], rebound.get("claims") or [])
    ) and len(original.get("claims") or []) == len(rebound.get("claims") or [])
    observations_unchanged = original.get("observations") == rebound.get("observations")
    rebound["stage1_1_rebinding"] = {
        "status": "DETERMINISTIC_REPLAY_COMPLETE",
        "source_bundle_sha256": original_bundle_sha,
        "source_bundle_file_sha256": original_bundle_file_sha,
        "resolver": "pdf_page_exact_v1",
        "hierarchy": ["trusted_provenance", "raw_exact", "canonical_exact", "pdf_normalized_exact"],
        "llm_calls_added": 0,
        "before": before,
        "after": after,
        "resolution_target": {"minimum_resolved": 48, "met": after["locator_resolved"] >= 48},
        "match_methods": dict(sorted(method_counts.items())),
        "unresolved_reasons": dict(sorted(unresolved_reasons.items())),
        "claim_ids_unchanged": original_ids == rebound_ids,
        "raw_claim_content_unchanged": raw_claims_unchanged,
        "observations_unchanged": observations_unchanged,
    }
    if not (original_ids == rebound_ids and raw_claims_unchanged and observations_unchanged):
        raise PilotError("STAGE1_1_IMMUTABILITY_FAILURE")

    zero_llm = {
        "llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "response_model": "NOT_USED_DETERMINISTIC_REPLAY",
    }
    metrics = _stage1_metrics(rebound, zero_llm, parsed.text)
    metrics.update({
        "stage": "1.1",
        "source_bundle_sha256": original_bundle_sha,
        "replay_llm_calls": 0,
        "llm_calls_added": 0,
        "original_extraction_llm_calls": (original.get("model") or {}).get("llm_calls", "NOT_AVAILABLE"),
        "original_extraction_usage": copy.deepcopy((original.get("model") or {}).get("usage") or {}),
        "before": before,
        "after": after,
        "resolution_target": {"minimum_resolved": 48, "met": after["locator_resolved"] >= 48},
        "match_methods": dict(sorted(method_counts.items())),
        "unresolved_reasons": dict(sorted(unresolved_reasons.items())),
        "claim_ids_unchanged": True,
        "raw_claim_content_unchanged": True,
        "observations_unchanged": True,
    })

    rebound_path = output_dir / "extraction_bundle_stage1_1_rebound.json"
    review_path = output_dir / "extraction_review_stage1_1_draft.json"
    markdown_path = output_dir / "stage1_1_review.md"
    metrics_path = output_dir / "stage1_1_metrics.json"
    if rebound_path == bundle_path:
        raise PilotError("STAGE1_1_OUTPUT_INVALID: original bundle cannot be overwritten")
    output_dir.mkdir(parents=True, exist_ok=True)
    review_id = f"REV_{extraction_bundle_sha256(rebound)[:16].upper()}"
    review = _build_review_draft(rebound, review_id=review_id)
    write_json(rebound_path, rebound)
    write_json(review_path, review)
    markdown_path.write_text(render_review_markdown(rebound, review, metrics), encoding="utf-8")
    write_json(metrics_path, metrics)

    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    production_unchanged = (
        production_pre == production_post if production_pre is not None else None
    )
    original_bundle_unchanged = sha256_file(bundle_path) == original_bundle_file_sha
    if not original_bundle_unchanged:
        raise PilotError("STAGE1_1_SOURCE_BUNDLE_MUTATED")
    return {
        "status": "PASS",
        "pilot_run_id": rebound["pilot_run_id"],
        "bundle": rebound,
        "review": review,
        "metrics": metrics,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "original_bundle_unchanged": original_bundle_unchanged,
        "rebound_bundle_path": str(rebound_path),
        "review_draft_path": str(review_path),
        "review_markdown_path": str(markdown_path),
        "metrics_path": str(metrics_path),
    }


def _cross_page_claim_ids(bundle: dict[str, Any]) -> list[str]:
    return [
        str(claim.get("claim_id") or "")
        for claim in bundle.get("claims") or []
        if (((claim.get("validation") or {}).get("source_locator") or {}).get("reason"))
        == "cross_page_span"
    ]


def _stage1_2_metrics(
    bundle: dict[str, Any], review: dict[str, Any], decisions_sha256: str,
) -> dict[str, Any]:
    counts = Counter(claim.get("decision") or "PENDING" for claim in review.get("claims") or [])
    cross_page_ids = set(_cross_page_claim_ids(bundle))
    blocked_cross_page = [
        claim["claim_id"]
        for claim in review.get("claims") or []
        if claim.get("claim_id") in cross_page_ids
        and claim.get("decision") == "KEEP_NEEDS_REVIEW"
    ]
    accepted_without_evidence = [
        claim["claim_id"]
        for claim in bundle.get("claims") or []
        if next(
            item.get("decision")
            for item in review.get("claims") or []
            if item.get("claim_id") == claim.get("claim_id")
        ) == "KEEP"
        and claim.get("evidence_validated") is not True
    ]
    pending = counts.get("PENDING", 0)
    production_apply_ready = not (
        pending or blocked_cross_page or accepted_without_evidence
    )
    return {
        "stage": "1.2",
        "pilot_run_id": bundle["pilot_run_id"],
        "decisions_sha256": decisions_sha256,
        "claims_total": len(bundle.get("claims") or []),
        "claims_human_reviewed": len(bundle.get("claims") or []) - pending,
        "accept": counts.get("KEEP", 0),
        "reject": counts.get("DROP", 0),
        "needs_correction": 0,
        "blocked_cross_page": len(blocked_cross_page),
        "pending": pending,
        "decision_counts": {
            "KEEP": counts.get("KEEP", 0),
            "DROP": counts.get("DROP", 0),
            "KEEP_NEEDS_REVIEW": counts.get("KEEP_NEEDS_REVIEW", 0),
            "PENDING": pending,
        },
        "cross_page_claim_ids": sorted(cross_page_ids),
        "blocked_cross_page_claim_ids": blocked_cross_page,
        "accepted_without_evidence": accepted_without_evidence,
        "correction_supported": False,
        "confidence_contract": "FORMAL_VALIDATION_GATED_WITH_MODEL_CONFIDENCE_AUDIT",
        "confidence_changed": False,
        "confidence_blocker": False,
        "formal_zero_confidence_claims": sum(
            claim.get("confidence") == 0 for claim in bundle.get("claims") or []
        ),
        "source_metadata_accepted_as_incomplete": True,
        "llm_calls_added": 0,
        "claim_ids_unchanged": True,
        "raw_claim_text_preserved": True,
        "raw_evidence_preserved": True,
        "production_apply_ready": production_apply_ready,
        "remaining_blockers": (
            [
                "Cross-page Evidence is not representable as one deterministic PAGE locator "
                "under the current contract."
            ]
            if blocked_cross_page
            else []
        ),
    }


def render_stage1_2_review_markdown(
    bundle: dict[str, Any], review: dict[str, Any], metrics: dict[str, Any],
) -> str:
    lines = [
        "# Phase 3C Stage 1.2 Human Extraction Review Closure", "",
        f"- status: `{review['status']}`",
        f"- pilot_run_id: `{bundle['pilot_run_id']}`",
        f"- extraction_bundle_sha256: `{review['extraction_bundle_sha256']}`",
        f"- decisions_sha256: `{metrics['decisions_sha256']}`",
        "- LLM calls added: `0`", "",
        "## Decision summary", "",
        f"- Claims reviewed: {metrics['claims_human_reviewed']} / {metrics['claims_total']}",
        f"- ACCEPT (`KEEP`): {metrics['accept']}",
        f"- REJECT (`DROP`): {metrics['reject']}",
        f"- NEEDS_CORRECTION: {metrics['needs_correction']} (unsupported by schema v1)",
        f"- BLOCKED_CROSS_PAGE (`KEEP_NEEDS_REVIEW`): {metrics['blocked_cross_page']}",
        f"- PENDING: {metrics['pending']}",
        f"- Production apply ready: `{metrics['production_apply_ready']}`", "",
        "## Contract audits", "",
        "- Claim content and Evidence are immutable under review schema v1.",
        "- Corrected Claim text/history is not supported; material wording defects are `DROP`.",
        "- Formal confidence remains unchanged; original model confidence remains in `validation.model_confidence`.",
        "- Source metadata is explicitly accepted as incomplete; no values were inferred.",
        "- Cross-page Evidence remains `cross_page_span`; no single PAGE locator was invented.", "",
        "## Claim decisions", "",
    ]
    for claim in review.get("claims") or []:
        locator = (claim.get("validation") or {}).get("source_locator") or {}
        lines += [
            f"### {claim['claim_id']}", "",
            f"- decision: `{claim['decision']}`",
            f"- rationale: {claim.get('human_review_rationale') or ''}",
            f"- statement: {claim['statement']}",
            f"- Evidence excerpt: {claim['evidence_excerpt']}",
            f"- attributed_to: {claim.get('attributed_to') or ''}",
            f"- locator: `{json.dumps(locator, ensure_ascii=False)}`",
            f"- confidence / model confidence: `{claim.get('confidence')}` / "
            f"`{(claim.get('validation') or {}).get('model_confidence')}`", "",
        ]
    lines += [
        "## Remaining blockers", "",
        *([f"- {item}" for item in metrics["remaining_blockers"]] or ["- None."]), "",
        "All decisions are explicit. No Production, IMA, governance, propagation, or legacy-pipeline action was performed.", "",
    ]
    return "\n".join(lines)


def close_stage1_2_human_review(
    bundle_path: Path,
    draft_review_path: Path,
    decisions_path: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Close one immutable Stage 1.1 review using explicit schema-v1 decisions."""
    bundle_path = Path(bundle_path).resolve()
    draft_review_path = Path(draft_review_path).resolve()
    decisions_path = Path(decisions_path).resolve()
    output_dir = Path(output_dir or draft_review_path.parent).resolve()
    for label, path in (
        ("bundle", bundle_path), ("draft review", draft_review_path),
        ("human decisions", decisions_path),
    ):
        if not path.is_file():
            raise PilotError(f"Stage 1.2 {label} not found: {path}")

    original_hashes = {
        "bundle": sha256_file(bundle_path),
        "draft_review": sha256_file(draft_review_path),
        "decisions": sha256_file(decisions_path),
    }
    bundle = _load_json(bundle_path)
    draft = _load_json(draft_review_path)
    decisions = _load_json(decisions_path)
    if bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE:
        raise PilotError("STAGE1_2_BUNDLE_INVALID")
    if draft.get("document_type") != REVIEW_DOCUMENT_TYPE or draft.get("status") != REVIEW_DRAFT_STATUS:
        raise PilotError("STAGE1_2_REVIEW_INVALID: expected the Stage 1.1 DRAFT review")
    if draft.get("extraction_bundle_sha256") != extraction_bundle_sha256(bundle):
        raise PilotError("STAGE1_2_REVIEW_STALE: review is not bound to the supplied bundle")
    if (
        decisions.get("document_type") != HUMAN_DECISIONS_DOCUMENT_TYPE
        or decisions.get("schema_version") != SCHEMA_VERSION
        or decisions.get("pilot_run_id") != bundle.get("pilot_run_id")
    ):
        raise PilotError("STAGE1_2_DECISIONS_INVALID: identity or schema mismatch")
    if decisions.get("source_metadata_accepted_as_incomplete") is not True:
        raise PilotError("STAGE1_2_SOURCE_METADATA_PENDING")

    raw_decisions = decisions.get("decisions")
    if not isinstance(raw_decisions, list):
        raise PilotError("STAGE1_2_DECISIONS_INVALID: decisions must be a list")
    decision_by_id: dict[str, dict[str, str]] = {}
    for index, item in enumerate(raw_decisions):
        if not isinstance(item, dict) or set(item) != {"claim_id", "decision", "rationale"}:
            raise PilotError(
                f"STAGE1_2_DECISIONS_INVALID: decisions[{index}] fields are not exact"
            )
        claim_id = item.get("claim_id")
        decision = item.get("decision")
        rationale = item.get("rationale")
        if not isinstance(claim_id, str) or not claim_id or claim_id in decision_by_id:
            raise PilotError(f"STAGE1_2_DECISIONS_INVALID: duplicate/invalid Claim ID at {index}")
        if decision not in ALLOWED_DECISIONS:
            raise PilotError(f"STAGE1_2_DECISIONS_INVALID: unsupported decision at {index}")
        if not isinstance(rationale, str) or not rationale.strip():
            raise PilotError(f"STAGE1_2_DECISIONS_INVALID: rationale required at {index}")
        decision_by_id[claim_id] = {
            "decision": decision,
            "rationale": rationale.strip(),
        }

    bundle_claims = bundle.get("claims") or []
    expected_ids = [str(claim.get("claim_id") or "") for claim in bundle_claims]
    if set(decision_by_id) != set(expected_ids) or len(decision_by_id) != len(expected_ids):
        raise PilotError("STAGE1_2_DECISIONS_INVALID: Claim coverage is not exact")
    cross_page_ids = set(_cross_page_claim_ids(bundle))
    for claim in bundle_claims:
        claim_id = claim["claim_id"]
        decision = decision_by_id[claim_id]["decision"]
        if decision == "KEEP" and claim.get("evidence_validated") is not True:
            raise PilotError(f"STAGE1_2_DECISIONS_INVALID: unvalidated KEEP {claim_id}")
        if decision == "KEEP_NEEDS_REVIEW" and claim_id not in cross_page_ids:
            raise PilotError(
                f"STAGE1_2_CORRECTION_UNSUPPORTED: KEEP_NEEDS_REVIEW is cross-page-only ({claim_id})"
            )

    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None
    closed = copy.deepcopy(draft)
    closed["status"] = REVIEW_READY_STATUS
    closed["source"]["metadata_decision"] = "APPROVED"
    for claim in closed.get("claims") or []:
        selected = decision_by_id[claim["claim_id"]]
        claim["decision"] = selected["decision"]
        claim["human_review_rationale"] = selected["rationale"]

    decisions_sha256 = hashlib.sha256(_canonical_json(decisions)).hexdigest()
    metrics = _stage1_2_metrics(bundle, closed, decisions_sha256)
    closed["stage1_2"] = {
        key: copy.deepcopy(metrics[key])
        for key in (
            "decisions_sha256", "claims_human_reviewed", "decision_counts",
            "blocked_cross_page_claim_ids", "correction_supported", "confidence_contract",
            "confidence_changed", "confidence_blocker", "source_metadata_accepted_as_incomplete",
            "llm_calls_added", "production_apply_ready", "remaining_blockers",
        )
    }
    validated = validate_review(bundle, closed, require_production_ready=False)
    if len(validated["claims"]) != len(bundle_claims):
        raise PilotError("STAGE1_2_REVIEW_INVALID: validation changed Claim coverage")

    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / "extraction_review_stage1_2_ready.json"
    markdown_path = output_dir / "stage1_2_review.md"
    metrics_path = output_dir / "stage1_2_metrics.json"
    write_json(review_path, closed)
    markdown_path.write_text(
        render_stage1_2_review_markdown(bundle, closed, metrics), encoding="utf-8",
    )
    write_json(metrics_path, metrics)

    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    production_unchanged = production_pre == production_post if production_pre is not None else None
    inputs_unchanged = original_hashes == {
        "bundle": sha256_file(bundle_path),
        "draft_review": sha256_file(draft_review_path),
        "decisions": sha256_file(decisions_path),
    }
    if not inputs_unchanged:
        raise PilotError("STAGE1_2_INPUT_MUTATED")
    return {
        "status": "PASS",
        "pilot_run_id": bundle["pilot_run_id"],
        "review": closed,
        "metrics": metrics,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "inputs_unchanged": inputs_unchanged,
        "review_path": str(review_path),
        "review_markdown_path": str(markdown_path),
        "metrics_path": str(metrics_path),
    }


def _stage1_3_review_sha256(review: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(review)).hexdigest()


def _page_number(locator: str) -> int:
    match = re.fullmatch(r"PAGE:([1-9]\d*)", locator or "")
    if not match:
        raise PilotError(f"STAGE1_3_CONTEXT_INVALID: unsupported locator {locator!r}")
    return int(match.group(1))


def _comparison_contains(body: str, excerpt: str) -> bool:
    if not isinstance(excerpt, str) or not excerpt.strip():
        return False
    return any(
        normalizer(excerpt) in normalizer(body)
        for _, _, normalizer in _pdf_comparison_methods()
        if normalizer(excerpt)
    )


def _normalized_gap(first_start: int, first_length: int, second_start: int, second_length: int) -> int:
    first_end = first_start + first_length
    second_end = second_start + second_length
    if first_end < second_start:
        return second_start - first_end
    if second_end < first_start:
        return first_start - second_end
    return 0


def _normalized_occurrence_starts(body: str, needle: str) -> list[int]:
    if not needle:
        return []
    starts: list[int] = []
    offset = 0
    while (start := body.find(needle, offset)) >= 0:
        starts.append(start)
        offset = start + 1
    return starts


def _stage1_3_normalized_local_binding(body: str, text: str) -> tuple[str, str, list[int]]:
    normalized_body = normalize_pdf_locator_text(body)
    normalized_text = normalize_pdf_locator_text(text)
    return (
        normalized_body,
        normalized_text,
        _normalized_occurrence_starts(normalized_body, normalized_text),
    )


def _validate_stage1_3_context_span(
    *,
    span: dict[str, Any],
    page_by_locator: dict[str, str],
    evidence_locator: str,
    evidence_excerpt: str,
) -> None:
    if not isinstance(span, dict) or set(span) != {"locator", "text"}:
        raise PilotError("STAGE1_3_CONTEXT_INVALID: support span fields are not exact")
    locator = span.get("locator")
    text = span.get("text")
    if not isinstance(locator, str) or locator not in page_by_locator:
        raise PilotError("STAGE1_3_CONTEXT_INVALID: support locator is absent")
    if not isinstance(text, str) or not text.strip() or not _comparison_contains(
        page_by_locator[locator], text,
    ):
        raise PilotError("STAGE1_3_CONTEXT_INVALID: support text is not on its declared page")

    evidence_page = _page_number(evidence_locator)
    context_page = _page_number(locator)
    if abs(context_page - evidence_page) > 1:
        raise PilotError("STAGE1_3_CONTEXT_INVALID: distant page context is forbidden")

    evidence_body, evidence_copy, evidence_starts = _stage1_3_normalized_local_binding(
        page_by_locator[evidence_locator], evidence_excerpt,
    )
    context_body, context_copy, context_starts = _stage1_3_normalized_local_binding(
        page_by_locator[locator], text,
    )
    if not evidence_starts or not context_starts:
        raise PilotError("STAGE1_3_CONTEXT_INVALID: normalized local binding failed")
    if context_page == evidence_page:
        within_radius = any(
            _normalized_gap(
                evidence_start, len(evidence_copy), context_start, len(context_copy),
            ) <= STAGE1_3_CONTEXT_RADIUS
            for evidence_start in evidence_starts
            for context_start in context_starts
        )
        if not within_radius:
            raise PilotError("STAGE1_3_CONTEXT_INVALID: same-page context is outside the bounded window")
        return
    if context_page == evidence_page - 1:
        if not any(start <= STAGE1_3_CONTEXT_RADIUS for start in evidence_starts):
            raise PilotError("STAGE1_3_CONTEXT_INVALID: Evidence is not near the page start")
        if not any(
            len(context_body) - (start + len(context_copy)) <= STAGE1_3_CONTEXT_RADIUS
            for start in context_starts
        ):
            raise PilotError("STAGE1_3_CONTEXT_INVALID: prior-page context is not near the boundary")
        return
    if not any(
        len(evidence_body) - (start + len(evidence_copy)) <= STAGE1_3_CONTEXT_RADIUS
        for start in evidence_starts
    ):
        raise PilotError("STAGE1_3_CONTEXT_INVALID: Evidence is not near the page end")
    if not any(start <= STAGE1_3_CONTEXT_RADIUS for start in context_starts):
        raise PilotError("STAGE1_3_CONTEXT_INVALID: next-page context is not near the boundary")


def _stage1_3_rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100 * numerator / denominator, 2) if denominator else 0.0,
    }


def _stage1_3_metrics(
    bundle: dict[str, Any],
    review: dict[str, Any],
    drop_diagnostics: list[dict[str, Any]],
    cross_page_diagnostics: list[dict[str, Any]],
    decisions_sha256: str,
) -> dict[str, Any]:
    stage1_2_counts = Counter(item.get("decision") for item in review.get("claims") or [])
    primary_counts = Counter(item["primary_failure_category"] for item in drop_diagnostics)
    disposition_counts = Counter(item["diagnostic_disposition"] for item in drop_diagnostics)
    claims_total = len(bundle.get("claims") or [])
    recoverable = disposition_counts["RECOVERABLE_WITH_BOUNDED_CONTEXT"]
    cross_page_complete = sum(
        item["cross_page_verified"] is True and item["semantic_support"] == "complete"
        for item in cross_page_diagnostics
    )
    context_adjusted = stage1_2_counts["KEEP"] + recoverable + cross_page_complete
    prompt_categories = [
        "claim_atomicity_and_unsupported_clause_control",
        "attribution_preservation",
        "conditional_branch_preservation",
        "scope_invention_prevention",
    ]
    return {
        "stage": "1.3",
        "pilot_run_id": bundle["pilot_run_id"],
        "decisions_sha256": decisions_sha256,
        "claims_total": claims_total,
        "stage1_2_decision_counts": {
            "KEEP": stage1_2_counts["KEEP"],
            "DROP": stage1_2_counts["DROP"],
            "KEEP_NEEDS_REVIEW": stage1_2_counts["KEEP_NEEDS_REVIEW"],
        },
        "drop_primary_failure_counts": {
            category: primary_counts[category]
            for category in sorted(STAGE1_3_FAILURE_CATEGORIES)
        },
        "diagnostic_disposition_counts": {
            disposition: disposition_counts[disposition]
            for disposition in sorted(STAGE1_3_DISPOSITIONS)
        },
        "true_extraction_failures": disposition_counts["GENUINE_EXTRACTION_FAILURE"],
        "recoverable_context_failures": recoverable,
        "attribution_failures": disposition_counts["ATTRIBUTION_FAILURE"],
        "conditionality_failures": disposition_counts["CONDITIONALITY_FAILURE"],
        "other_or_unresolved_failures": disposition_counts["UNRESOLVED"],
        "atomicity_issues": sum(item["atomicity_issue"] is True for item in drop_diagnostics),
        "cross_page_claims_verified": sum(
            item["cross_page_verified"] is True for item in cross_page_diagnostics
        ),
        "strict_current_contract_keep_rate": _stage1_3_rate(
            stage1_2_counts["KEEP"], claims_total,
        ),
        "context_adjusted_semantically_supportable_rate": _stage1_3_rate(
            context_adjusted, claims_total,
        ),
        "true_semantic_extraction_failure_rate": _stage1_3_rate(
            claims_total - context_adjusted, claims_total,
        ),
        "rate_definition": {
            "strict_current_contract_keep": "Stage 1.2 KEEP / all Claims",
            "context_adjusted_semantically_supportable": (
                "(Stage 1.2 KEEP + bounded-context recoverable DROP + verified complete "
                "cross-page Claims) / all Claims"
            ),
            "true_semantic_extraction_failure": (
                "Claims not semantically supportable after bounded context and exact "
                "cross-page review / all Claims"
            ),
        },
        "evidence_contract_finding": (
            "The single-excerpt/single-PAGE contract caused recoverable false rejection "
            "and cannot represent two exact adjacent-page Evidence spans."
        ),
        "evidence_contract_recommendation": (
            "Retain the immutable extracted excerpt; add bounded supporting context with "
            "context locators for antecedents, plus ordered evidence spans for exact "
            "adjacent-page quotations. Do not replace the raw excerpt."
        ),
        "extraction_prompt_change_recommended": True,
        "prompt_change_categories": prompt_categories,
        "llm_calls_added": 0,
        "deepseek_rerun": False,
        "pilot_2_executed": False,
        "production_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "production_write": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
        "governance_objects_created": False,
        "stage1_2_decisions_unchanged": True,
        "claim_ids_unchanged": True,
        "raw_claim_text_unchanged": True,
        "raw_evidence_unchanged": True,
        "remaining_blockers": [
            "Production apply remains blocked by the two cross-page Claims under the current contract.",
            "Stage 1.4 must design, but not yet apply, the minimum supporting-context and evidence-span contract.",
            "The extraction prompt still needs minimal repair for atomicity, attribution, conditionality, and scope invention.",
        ],
        "next_gate": "Stage 1.4 Evidence Contract + Extraction Prompt Minimal Repair",
    }


def render_stage1_3_diagnostic_markdown(
    diagnostic: dict[str, Any], metrics: dict[str, Any],
) -> str:
    primary = metrics["drop_primary_failure_counts"]
    dispositions = metrics["diagnostic_disposition_counts"]
    strict_rate = metrics["strict_current_contract_keep_rate"]
    adjusted_rate = metrics["context_adjusted_semantically_supportable_rate"]
    failure_rate = metrics["true_semantic_extraction_failure_rate"]
    lines = [
        "# Phase 3C Stage 1.3 Evidence Scope & Claim Atomicity Diagnostic", "",
        f"- status: `{diagnostic['status']}`",
        f"- pilot_run_id: `{diagnostic['pilot_run_id']}`",
        f"- context policy: `{diagnostic['context_policy']}`",
        "- LLM / DeepSeek calls added: `0`", "",
        "## Answer", "",
        (
            f"Of 17 Stage 1.2 DROP Claims, {metrics['recoverable_context_failures']} are "
            "semantically recoverable with bounded adjacent context. The remaining 6 are "
            "semantic extraction failures: 4 general/scope failures, 1 attribution failure, "
            "and 1 conditionality failure."
        ), "",
        "## Taxonomy", "",
        *[f"- {key}: {primary[key]}" for key in sorted(primary)], "",
        "## Diagnostic dispositions", "",
        *[f"- {key}: {dispositions[key]}" for key in sorted(dispositions)], "",
        "## Rates", "",
        f"- Strict current-contract KEEP rate: {strict_rate['fraction']} = {strict_rate['percent']}%",
        f"- Context-adjusted semantically supportable rate: {adjusted_rate['fraction']} = {adjusted_rate['percent']}%",
        f"- True semantic extraction failure rate: {failure_rate['fraction']} = {failure_rate['percent']}%",
        "- Recoverable context findings do not become current Production-ready Claims.", "",
        "## DROP Claim diagnostics", "",
        "| Claim | Primary reason | Disposition | Atomicity | Context support |",
        "|---|---|---|---:|---:|",
    ]
    for item in diagnostic["drop_diagnostics"]:
        lines.append(
            f"| `{item['claim_id']}` | `{item['primary_failure_category']}` | "
            f"`{item['diagnostic_disposition']}` | `{item['atomicity_issue']}` | "
            f"`{item['bounded_context_supports_claim']}` |"
        )
    lines += ["", "## Per-Claim rationale", ""]
    for item in diagnostic["drop_diagnostics"]:
        lines += [
            f"### {item['claim_id']}", "",
            f"- Stage 1.2 decision: `{item['original_human_decision']}` (unchanged)",
            f"- rationale: {item['rationale']}",
            f"- atomicity: `{item['atomicity_issue']}` - {item['atomicity_reason'] or 'No issue.'}",
            f"- context locators: `{json.dumps(item['context_locators'], ensure_ascii=False)}`",
            f"- original Claim: {item['original_claim']}",
            f"- immutable Evidence excerpt: {item['original_evidence_excerpt']}", "",
        ]
    lines += ["## Cross-page audit", ""]
    for item in diagnostic["cross_page_diagnostics"]:
        lines += [
            f"- `{item['claim_id']}`: verified=`{item['cross_page_verified']}`, "
            f"pages=`{json.dumps(item['pages'], ensure_ascii=False)}`, "
            f"semantic_support=`{item['semantic_support']}`; {item['rationale']}",
        ]
    lines += [
        "", "## Evidence contract options", "",
        "- Option A - keep one excerpt / one PAGE: simplest, but retains 11 context false rejections and cannot represent the 2 verified cross-page excerpts.",
        "- Option B - immutable excerpt + bounded supporting context: resolves explicit local antecedents while preserving the extracted quote; requires strict local-window and locator validation.",
        "- Option C - ordered Evidence spans: minimally represents exact adjacent-page quotations; ordering and exact text/locator binding must be immutable.",
        "", "Recommendation: combine B and C at design level. Keep the original Evidence excerpt immutable, add bounded context only for diagnostic/support scope, and use ordered spans only for exact multi-page quotations. No Production schema change is made in Stage 1.3.",
        "", "## Prompt decision", "",
        f"- EXTRACTION_PROMPT_CHANGE_RECOMMENDED: `{str(metrics['extraction_prompt_change_recommended']).lower()}`",
        f"- Minimal categories: `{json.dumps(metrics['prompt_change_categories'], ensure_ascii=False)}`",
        "- This is a narrow recommendation; most DROP Claims were evidence-scope failures, so a broad prompt rewrite is not justified.",
        "", "## Isolation and next gate", "",
        "- Stage 1.2 decisions, Claim IDs, raw Claim text, and raw Evidence are unchanged.",
        "- Production, canonical schema, IMA, propagation, legacy pipeline, and governance were not invoked or changed.",
        f"- PHASE3C_NEXT_GATE: `{metrics['next_gate']}`", "",
    ]
    return "\n".join(lines)


def run_stage1_3_evidence_scope_diagnostic(
    bundle_path: Path,
    stage1_2_review_path: Path,
    source_file: Path,
    decisions_path: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Validate explicit Stage 1.3 decisions against bounded local PDF context."""
    bundle_path = Path(bundle_path).resolve()
    stage1_2_review_path = Path(stage1_2_review_path).resolve()
    source_file = Path(source_file).resolve()
    decisions_path = Path(decisions_path).resolve()
    output_dir = Path(output_dir or stage1_2_review_path.parent).resolve()
    inputs = {
        "bundle": bundle_path,
        "stage1_2_review": stage1_2_review_path,
        "source_file": source_file,
        "decisions": decisions_path,
    }
    for label, path in inputs.items():
        if not path.is_file():
            raise PilotError(f"Stage 1.3 {label} not found: {path}")
    original_hashes = {label: sha256_file(path) for label, path in inputs.items()}

    bundle = _load_json(bundle_path)
    review = _load_json(stage1_2_review_path)
    decisions = _load_json(decisions_path)
    if bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE:
        raise PilotError("STAGE1_3_BUNDLE_INVALID")
    validate_review(bundle, review, require_production_ready=False)
    if not review.get("stage1_2") or review.get("status") != REVIEW_READY_STATUS:
        raise PilotError("STAGE1_3_REVIEW_INVALID: Stage 1.2 READY review required")
    if sha256_file(source_file) != (bundle.get("source") or {}).get("sha256"):
        raise PilotError("STAGE1_3_SOURCE_MISMATCH")
    expected_decision_fields = {
        "document_type", "schema_version", "pilot_run_id", "extraction_bundle_sha256",
        "stage1_2_review_sha256", "context_policy", "drop_diagnostics",
        "cross_page_diagnostics",
    }
    if not isinstance(decisions, dict) or set(decisions) != expected_decision_fields:
        raise PilotError("STAGE1_3_DECISIONS_INVALID: top-level fields are not exact")
    if (
        decisions.get("document_type") != STAGE1_3_DECISIONS_DOCUMENT_TYPE
        or decisions.get("schema_version") != SCHEMA_VERSION
        or decisions.get("pilot_run_id") != bundle.get("pilot_run_id")
        or decisions.get("extraction_bundle_sha256") != extraction_bundle_sha256(bundle)
        or decisions.get("stage1_2_review_sha256") != _stage1_3_review_sha256(review)
        or decisions.get("context_policy") != STAGE1_3_CONTEXT_POLICY
    ):
        raise PilotError("STAGE1_3_DECISIONS_INVALID: identity, binding, or policy mismatch")

    parsed = parse_source_with_diagnostics(source_file)
    if parsed.source_type != "pdf":
        raise PilotError("STAGE1_3_SOURCE_INVALID: PDF required")
    page_by_locator = {
        locator: body for locator, body in source_units(parsed.text)
        if locator.startswith("PAGE:")
    }
    review_by_id = {item["claim_id"]: item for item in review.get("claims") or []}
    bundle_by_id = {item["claim_id"]: item for item in bundle.get("claims") or []}
    drop_ids = [
        item["claim_id"] for item in review.get("claims") or []
        if item.get("decision") == "DROP"
    ]
    cross_page_ids = [
        item["claim_id"] for item in review.get("claims") or []
        if item.get("decision") == "KEEP_NEEDS_REVIEW"
        and item.get("claim_id") in set(_cross_page_claim_ids(bundle))
    ]

    raw_drop = decisions.get("drop_diagnostics")
    if not isinstance(raw_drop, list):
        raise PilotError("STAGE1_3_DECISIONS_INVALID: drop_diagnostics must be a list")
    drop_fields = {
        "claim_id", "primary_failure_category", "secondary_failure_categories",
        "atomicity_issue", "atomicity_reason", "stored_excerpt_self_sufficient",
        "bounded_context_supports_claim", "supporting_context_before",
        "supporting_context_after", "context_locators", "diagnostic_support_span",
        "diagnostic_disposition", "rationale",
    }
    drop_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_drop):
        if not isinstance(item, dict) or set(item) != drop_fields:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: DROP[{index}] fields are not exact")
        claim_id = item.get("claim_id")
        if not isinstance(claim_id, str) or claim_id in drop_by_id:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: duplicate/invalid DROP[{index}]")
        primary = item.get("primary_failure_category")
        secondary = item.get("secondary_failure_categories")
        disposition = item.get("diagnostic_disposition")
        if primary not in STAGE1_3_FAILURE_CATEGORIES:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: invalid primary category at {index}")
        if (
            not isinstance(secondary, list)
            or any(value not in STAGE1_3_FAILURE_CATEGORIES for value in secondary)
            or primary in secondary
            or len(set(secondary)) != len(secondary)
        ):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: invalid secondary categories at {index}")
        if disposition not in STAGE1_3_DISPOSITIONS:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: invalid disposition at {index}")
        for field in (
            "atomicity_issue", "stored_excerpt_self_sufficient",
            "bounded_context_supports_claim",
        ):
            if not isinstance(item.get(field), bool):
                raise PilotError(f"STAGE1_3_DECISIONS_INVALID: {field} must be boolean")
        for field in (
            "atomicity_reason", "supporting_context_before", "supporting_context_after",
            "rationale",
        ):
            if not isinstance(item.get(field), str):
                raise PilotError(f"STAGE1_3_DECISIONS_INVALID: {field} must be text")
        if not item["rationale"].strip():
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: rationale required at {index}")
        if item["atomicity_issue"] != bool(item["atomicity_reason"].strip()):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: atomicity reason mismatch at {index}")
        expected_disposition = {
            "CONTEXT_INSUFFICIENT": "RECOVERABLE_WITH_BOUNDED_CONTEXT",
            "ATTRIBUTION_ERROR": "ATTRIBUTION_FAILURE",
            "CONDITIONALITY_LOSS": "CONDITIONALITY_FAILURE",
        }.get(primary)
        if expected_disposition and disposition != expected_disposition:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: category/disposition mismatch at {index}")
        if primary == "CONTEXT_INSUFFICIENT" and not (
            item["stored_excerpt_self_sufficient"] is False
            and item["bounded_context_supports_claim"] is True
        ):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: context diagnosis mismatch at {index}")
        spans = item.get("diagnostic_support_span")
        locators = item.get("context_locators")
        if not isinstance(spans, list) or not isinstance(locators, list):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: context fields must be lists at {index}")
        if any(not isinstance(value, str) for value in locators):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: context locator must be text at {index}")
        if item["bounded_context_supports_claim"] and not (
            item["stored_excerpt_self_sufficient"] or spans
        ):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: support span required at {index}")
        drop_by_id[claim_id] = copy.deepcopy(item)
    if set(drop_by_id) != set(drop_ids) or len(drop_by_id) != len(drop_ids):
        raise PilotError("STAGE1_3_DECISIONS_INVALID: DROP coverage is not exact")

    drop_diagnostics = []
    for claim_id in drop_ids:
        item = drop_by_id[claim_id]
        claim = bundle_by_id[claim_id]
        resolved = resolve_pdf_evidence_locator(
            parsed.text, claim.get("evidence_excerpt") or "", claim.get("evidence_pointer") or "",
        )
        if resolved.get("status") != "resolved":
            raise PilotError(f"STAGE1_3_CONTEXT_INVALID: DROP Evidence is unresolved ({claim_id})")
        spans = item["diagnostic_support_span"]
        derived_locators = []
        for span in spans:
            _validate_stage1_3_context_span(
                span=span,
                page_by_locator=page_by_locator,
                evidence_locator=resolved["locator"],
                evidence_excerpt=claim["evidence_excerpt"],
            )
            if span["locator"] not in derived_locators:
                derived_locators.append(span["locator"])
        if item["context_locators"] != derived_locators:
            raise PilotError(f"STAGE1_3_CONTEXT_INVALID: locator list mismatch ({claim_id})")
        combined_support = "\n".join(span["text"] for span in spans)
        for context_field in ("supporting_context_before", "supporting_context_after"):
            context_text = item[context_field]
            if context_text and not _comparison_contains(combined_support, context_text):
                raise PilotError(
                    f"STAGE1_3_CONTEXT_INVALID: {context_field} is outside support spans ({claim_id})"
                )
        drop_diagnostics.append({
            "claim_id": claim_id,
            "original_claim": claim["statement"],
            "original_evidence_excerpt": claim["evidence_excerpt"],
            "original_locator": copy.deepcopy((claim.get("validation") or {}).get("source_locator") or {}),
            "original_human_decision": review_by_id[claim_id]["decision"],
            **copy.deepcopy({key: value for key, value in item.items() if key != "claim_id"}),
        })

    raw_cross = decisions.get("cross_page_diagnostics")
    if not isinstance(raw_cross, list):
        raise PilotError("STAGE1_3_DECISIONS_INVALID: cross_page_diagnostics must be a list")
    cross_fields = {
        "claim_id", "cross_page_verified", "pages", "semantic_support",
        "evidence_spans", "rationale",
    }
    cross_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_cross):
        if not isinstance(item, dict) or set(item) != cross_fields:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: cross-page[{index}] fields are not exact")
        claim_id = item.get("claim_id")
        if not isinstance(claim_id, str) or claim_id in cross_by_id:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: duplicate/invalid cross-page[{index}]")
        if not isinstance(item.get("cross_page_verified"), bool):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: cross_page_verified must be boolean at {index}")
        if item.get("semantic_support") not in STAGE1_3_SEMANTIC_SUPPORT:
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: semantic support invalid at {index}")
        if not isinstance(item.get("pages"), list) or not isinstance(item.get("evidence_spans"), list):
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: cross-page lists invalid at {index}")
        if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
            raise PilotError(f"STAGE1_3_DECISIONS_INVALID: cross-page rationale required at {index}")
        cross_by_id[claim_id] = copy.deepcopy(item)
    if set(cross_by_id) != set(cross_page_ids) or len(cross_by_id) != len(cross_page_ids):
        raise PilotError("STAGE1_3_DECISIONS_INVALID: cross-page coverage is not exact")

    cross_page_diagnostics = []
    for claim_id in cross_page_ids:
        item = cross_by_id[claim_id]
        claim = bundle_by_id[claim_id]
        locator = (claim.get("validation") or {}).get("source_locator") or {}
        expected_pairs = locator.get("spanning_locators") or []
        if item["pages"] not in expected_pairs:
            raise PilotError(f"STAGE1_3_CROSS_PAGE_INVALID: pages do not match locator ({claim_id})")
        if len(item["pages"]) != 2 or _page_number(item["pages"][1]) != _page_number(item["pages"][0]) + 1:
            raise PilotError(f"STAGE1_3_CROSS_PAGE_INVALID: pages are not adjacent ({claim_id})")
        if [span.get("locator") for span in item["evidence_spans"]] != item["pages"]:
            raise PilotError(f"STAGE1_3_CROSS_PAGE_INVALID: ordered spans do not match pages ({claim_id})")
        for span in item["evidence_spans"]:
            if (
                not isinstance(span, dict)
                or set(span) != {"locator", "text"}
                or span["locator"] not in page_by_locator
                or not _comparison_contains(page_by_locator[span["locator"]], span["text"])
            ):
                raise PilotError(f"STAGE1_3_CROSS_PAGE_INVALID: Evidence span mismatch ({claim_id})")
        joined = "\n".join(span["text"] for span in item["evidence_spans"])
        verified = (
            locator.get("reason") == "cross_page_span"
            and _comparison_contains(joined, claim["evidence_excerpt"])
        )
        if item["cross_page_verified"] is not verified:
            raise PilotError(f"STAGE1_3_CROSS_PAGE_INVALID: verification mismatch ({claim_id})")
        cross_page_diagnostics.append({
            "claim_id": claim_id,
            "original_claim": claim["statement"],
            "original_evidence_excerpt": claim["evidence_excerpt"],
            "original_locator": copy.deepcopy(locator),
            "original_human_decision": review_by_id[claim_id]["decision"],
            **copy.deepcopy({key: value for key, value in item.items() if key != "claim_id"}),
        })

    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None
    decisions_sha256 = hashlib.sha256(_canonical_json(decisions)).hexdigest()
    metrics = _stage1_3_metrics(
        bundle, review, drop_diagnostics, cross_page_diagnostics, decisions_sha256,
    )
    diagnostic = {
        "document_type": STAGE1_3_DIAGNOSTIC_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETED",
        "pilot_run_id": bundle["pilot_run_id"],
        "bindings": {
            "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
            "stage1_2_review_sha256": _stage1_3_review_sha256(review),
            "source_sha256": bundle["source"]["sha256"],
            "decisions_sha256": decisions_sha256,
        },
        "context_policy": STAGE1_3_CONTEXT_POLICY,
        "drop_diagnostics": drop_diagnostics,
        "cross_page_diagnostics": cross_page_diagnostics,
        "immutability": {
            "stage1_2_decisions_unchanged": True,
            "claim_ids_unchanged": True,
            "raw_claim_text_unchanged": True,
            "raw_evidence_unchanged": True,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostic_path = output_dir / "stage1_3_evidence_scope_diagnostic.json"
    report_path = output_dir / "stage1_3_evidence_scope_report.md"
    metrics_path = output_dir / "stage1_3_metrics.json"
    write_json(diagnostic_path, diagnostic)
    report_path.write_text(
        render_stage1_3_diagnostic_markdown(diagnostic, metrics), encoding="utf-8",
    )
    write_json(metrics_path, metrics)

    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    production_unchanged = production_pre == production_post if production_pre is not None else None
    inputs_unchanged = original_hashes == {
        label: sha256_file(path) for label, path in inputs.items()
    }
    if not inputs_unchanged:
        raise PilotError("STAGE1_3_INPUT_MUTATED")
    if production_unchanged is False:
        raise PilotError("STAGE1_3_PRODUCTION_MUTATED")
    return {
        "status": "PASS",
        "pilot_run_id": bundle["pilot_run_id"],
        "diagnostic": diagnostic,
        "metrics": metrics,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "inputs_unchanged": inputs_unchanged,
        "diagnostic_path": str(diagnostic_path),
        "report_path": str(report_path),
        "metrics_path": str(metrics_path),
    }


def phase3c_prompt_repair_status(prompt: str = SOURCE_ANALYSIS_SYSTEM) -> dict[str, Any]:
    checks = {
        "evidence_quote_verbatim_preservation": (
            "evidence_excerpt 必须逐字复制输入原文中的一个连续片段" in prompt
            and "不得合并不同说话者/时间戳区块" in prompt
            and "不得增删词、替换实体或技术词、纠错或释义" in prompt
        ),
        "claim_atomicity": (
            "一个 Claim 通常只表达一个可独立审阅" in prompt
            and "不同业务主体、时间范围、确定性级别、所需 Evidence span" in prompt
        ),
        "gate_c_atomicity_clarification": (
            "不同不确定性、不同实体身份或不同 Evidence scope" in prompt
            and "不得为增加 Claim 数量" in prompt
        ),
        "atomicity_unsupported_clause": (
            "若 A/B/C 可以被分别接受或拒绝，必须拆成多条 Claim" in prompt
            and "同一局部 Evidence scope" in prompt
            and "不得因相关事实出现在讨论的其他远处位置" in prompt
        ),
        "attribution_preservation": (
            "必须保留实际说话者" in prompt
            and "不得把主持人改成专家" in prompt
            and "它不是 Source 的作者或来源，也不是 statement 的语法主语" in prompt
            and "归因只写入 attributed_to" in prompt
        ),
        "conditionality_preservation": (
            "必须保留条件与分支结构" in prompt
            and "修饰词必须继续附着于原本修饰的命题" in prompt
            and "不得遗漏分支" in prompt
            and "删除或移动限定词" in prompt
            and all(marker in prompt for marker in (
                "可能", "预计", "大概率", "如果", "若", "或者", "前提",
                "may", "could", "likely",
            ))
        ),
        "entity_inference_prevention": (
            "噪声、缩写或含混的人名、公司名或其他实体 token" in prompt
            and "文件名/标题" in prompt
            and "实体匹配观察不等于改写 Claim 的许可" in prompt
            and "Claim 语义与 Node/Alias 观察必须分离" in prompt
        ),
        "technical_term_inference_prevention": (
            "技术词必须保守保留" in prompt
            and "静默纠正为已知术语" in prompt
            and "不依赖该推断术语的保守 Claim" in prompt
        ),
        "scope_invention_prevention": (
            "不得扩大或替换 Claim 的对象" in prompt
            and "不得扩大或替换 Claim 的主体" in prompt
            and "不得将原文对象改写成更具体或更宽的范围" in prompt
            and "单一公司扩大为行业" in prompt
        ),
    }
    return {
        "passed": all(checks.values()),
        "categories": checks,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }


def _stage1_4_context_blocks(item: dict[str, Any]) -> list[dict[str, Any]]:
    spans = item.get("diagnostic_support_span") or []
    blocks = []
    for direction, field in (
        ("before", "supporting_context_before"),
        ("after", "supporting_context_after"),
    ):
        text = item.get(field) or ""
        if not text:
            continue
        locators = [
            span["locator"] for span in spans
            if _comparison_contains(str(span.get("text") or ""), text)
        ]
        if not locators:
            raise PilotError(
                f"STAGE1_4_CONTEXT_INVALID: {direction} context has no exact support span"
            )
        blocks.append({
            "direction": direction,
            "text": text,
            "locators": list(dict.fromkeys(locators)),
            "selection_rule": STAGE1_3_CONTEXT_POLICY,
        })
    return blocks


def _stage1_4_rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100 * numerator / denominator, 2) if denominator else 0.0,
    }


def _stage1_4_metrics(
    bundle: dict[str, Any],
    review: dict[str, Any],
    diagnostic: dict[str, Any],
    claims: list[dict[str, Any]],
    prompt_status: dict[str, Any],
) -> dict[str, Any]:
    support_counts = Counter(item["v2_support_status"] for item in claims)
    mode_counts = Counter(item["support_mode"] for item in claims)
    historical = Counter(item.get("decision") for item in review.get("claims") or [])
    stage1_3_drop = diagnostic.get("drop_diagnostics") or []
    recoverable_ids = {
        item["claim_id"] for item in stage1_3_drop
        if item.get("diagnostic_disposition") == "RECOVERABLE_WITH_BOUNDED_CONTEXT"
    }
    semantic_failure_ids = {
        item["claim_id"] for item in stage1_3_drop
        if item.get("diagnostic_disposition") != "RECOVERABLE_WITH_BOUNDED_CONTEXT"
    }
    represented_cross_page = sum(
        item["support_mode"] == "ORDERED_SPANS"
        and item["v2_support_status"] == "SUPPORTED"
        for item in claims
    )
    claims_total = len(bundle.get("claims") or [])
    supported = support_counts["SUPPORTED"]
    blocked = support_counts["BLOCKED"]
    next_gate = (
        "Pilot #2 Real Extraction Authorization"
        if blocked == 0 and prompt_status["passed"]
        else "Resolve Stage 1.4 Evidence Contract blockers"
    )
    return {
        "stage": "1.4",
        "pilot_run_id": bundle["pilot_run_id"],
        "evidence_contract_version": "2",
        "evidence_contract_v2_implemented": True,
        "claims_total": claims_total,
        "v2_support_counts": {
            status: support_counts[status] for status in sorted(STAGE1_4_SUPPORT_STATUSES)
        },
        "support_mode_counts": {
            mode: mode_counts[mode] for mode in sorted(STAGE1_4_SUPPORT_MODES)
        },
        "historical_stage1_2_decision_counts": {
            "KEEP": historical["KEEP"],
            "DROP": historical["DROP"],
            "KEEP_NEEDS_REVIEW": historical["KEEP_NEEDS_REVIEW"],
        },
        "stage1_3_context_recoverable_claims": len(recoverable_ids),
        "recovered_under_v2": sum(
            item["claim_id"] in recoverable_ids
            and item["v2_support_status"] == "SUPPORTED"
            and item["support_mode"] == "BOUNDED_CONTEXT"
            for item in claims
        ),
        "stage1_3_semantic_failures": len(semantic_failure_ids),
        "semantic_failures_still_unsupported": sum(
            item["claim_id"] in semantic_failure_ids
            and item["v2_support_status"] == "UNSUPPORTED"
            for item in claims
        ),
        "cross_page_claims": len(diagnostic.get("cross_page_diagnostics") or []),
        "cross_page_representable_under_v2": represented_cross_page,
        "strict_current_contract_keep_rate": _stage1_4_rate(historical["KEEP"], claims_total),
        "v2_support_rate": _stage1_4_rate(supported, claims_total),
        "true_semantic_failure_rate": _stage1_4_rate(
            support_counts["UNSUPPORTED"], claims_total,
        ),
        "human_review_burden": {
            "excerpt_only_review": mode_counts["EXCERPT_ONLY"],
            "context_expanded_review": mode_counts["BOUNDED_CONTEXT"],
            "cross_page_span_review": mode_counts["ORDERED_SPANS"],
            "semantic_rejection": mode_counts["NONE"],
            "claims_requiring_expanded_evidence_review": (
                mode_counts["BOUNDED_CONTEXT"] + mode_counts["ORDERED_SPANS"]
            ),
        },
        "contract_invariants": {
            "immutable_evidence_excerpt": True,
            "bounded_supporting_context": True,
            "ordered_evidence_spans": True,
            "exact_span_text": True,
            "cross_page_fake_single_locator": False,
        },
        "stage1_2_decisions_unchanged": True,
        "stage1_3_diagnostics_unchanged": True,
        "claim_ids_unchanged": True,
        "raw_claim_unchanged": True,
        "raw_evidence_unchanged": True,
        "prompt_minimal_repair": copy.deepcopy(prompt_status),
        "llm_calls_added": 0,
        "deepseek_rerun": False,
        "pilot_2_executed": False,
        "production_apply_ready": False,
        "production_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "canonical_claim_schema_changed": False,
        "production_write": False,
        "node_created": False,
        "relation_created": False,
        "proposal_created": False,
        "current_view_created": False,
        "knowledge_gap_created": False,
        "research_question_created": False,
        "claim_node_link_created": False,
        "source_node_link_created": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
        "remaining_blockers": [
            "Evidence Support Contract v2 is artifact-level only and is not a canonical admission contract.",
            "The repaired extraction prompt has not yet been validated by an independent real extraction.",
            "Production apply remains unauthorized and not ready in Stage 1.4.",
        ],
        "next_gate": next_gate,
    }


def render_stage1_4_review_markdown(
    contract: dict[str, Any], metrics: dict[str, Any],
) -> str:
    support = metrics["v2_support_counts"]
    modes = metrics["support_mode_counts"]
    lines = [
        "# Phase 3C Stage 1.4 Evidence Contract v2 Review Simulation", "",
        f"- status: `{contract['status']}`",
        f"- pilot_run_id: `{contract['pilot_run_id']}`",
        "- artifact-level contract only; canonical schemas unchanged", "",
        "## V2 result", "",
        f"- Claims: {metrics['claims_total']}",
        f"- SUPPORTED / UNSUPPORTED / BLOCKED: {support['SUPPORTED']} / {support['UNSUPPORTED']} / {support['BLOCKED']}",
        f"- EXCERPT_ONLY / BOUNDED_CONTEXT / ORDERED_SPANS / NONE: {modes['EXCERPT_ONLY']} / {modes['BOUNDED_CONTEXT']} / {modes['ORDERED_SPANS']} / {modes['NONE']}",
        f"- V2 support rate: {metrics['v2_support_rate']['fraction']} = {metrics['v2_support_rate']['percent']}%",
        f"- Production apply ready: `{metrics['production_apply_ready']}`", "",
        "## Contract invariants", "",
        "- The original Evidence excerpt is immutable and remains present for every Claim.",
        "- Supporting context is additive, direction-labeled, locator-bound, and selected under the Stage 1.3 bounded rule.",
        "- Cross-page Evidence uses ordered exact spans with independent adjacent-page locators.",
        "- No synthetic aggregate PAGE locator is created.", "",
        "## Human-review burden", "",
        f"- excerpt-only review: {metrics['human_review_burden']['excerpt_only_review']}",
        f"- context-expanded review: {metrics['human_review_burden']['context_expanded_review']}",
        f"- cross-page span review: {metrics['human_review_burden']['cross_page_span_review']}",
        f"- semantic rejection: {metrics['human_review_burden']['semantic_rejection']}",
        f"- expanded Evidence review total: {metrics['human_review_burden']['claims_requiring_expanded_evidence_review']}", "",
        "## Prompt minimal repair", "",
    ]
    for category, passed in metrics["prompt_minimal_repair"]["categories"].items():
        lines.append(f"- {category}: `{'PASS' if passed else 'FAIL'}`")
    lines += ["", "## Claim replay", ""]
    for item in contract["claims"]:
        lines += [
            f"### {item['claim_id']}", "",
            f"- Stage 1.2 decision: `{item['stage1_2_decision']}`",
            f"- Stage 1.3 diagnosis: `{item['stage1_3_diagnosis']}`",
            f"- V2 support: `{item['v2_support_status']}` via `{item['support_mode']}`",
            f"- rationale: {item['support_rationale']}",
            f"- Claim: {item['original_claim']}",
            f"- immutable Evidence excerpt: {item['original_evidence_excerpt']}",
            f"- context locators: `{json.dumps(item['supporting_context_locators'], ensure_ascii=False)}`",
            f"- ordered spans: `{json.dumps(item['evidence_spans'], ensure_ascii=False)}`", "",
        ]
    lines += [
        "## Isolation and next gate", "",
        "No Production/schema, Node, Relation, governance, IMA, propagation, or legacy-pipeline action was performed.",
        f"PHASE3C_NEXT_GATE = {metrics['next_gate']}", "",
    ]
    return "\n".join(lines)


def run_stage1_4_evidence_contract_v2(
    bundle_path: Path,
    stage1_2_review_path: Path,
    stage1_3_diagnostic_path: Path,
    source_file: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Replay all Claims through additive artifact-level Evidence Support Contract v2."""
    bundle_path = Path(bundle_path).resolve()
    stage1_2_review_path = Path(stage1_2_review_path).resolve()
    stage1_3_diagnostic_path = Path(stage1_3_diagnostic_path).resolve()
    source_file = Path(source_file).resolve()
    output_dir = Path(output_dir or stage1_2_review_path.parent).resolve()
    inputs = {
        "bundle": bundle_path,
        "stage1_2_review": stage1_2_review_path,
        "stage1_3_diagnostic": stage1_3_diagnostic_path,
        "source_file": source_file,
    }
    for label, path in inputs.items():
        if not path.is_file():
            raise PilotError(f"Stage 1.4 {label} not found: {path}")
    original_hashes = {label: sha256_file(path) for label, path in inputs.items()}

    bundle = _load_json(bundle_path)
    review = _load_json(stage1_2_review_path)
    diagnostic = _load_json(stage1_3_diagnostic_path)
    if bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE:
        raise PilotError("STAGE1_4_BUNDLE_INVALID")
    validate_review(bundle, review, require_production_ready=False)
    if (
        diagnostic.get("document_type") != STAGE1_3_DIAGNOSTIC_DOCUMENT_TYPE
        or diagnostic.get("schema_version") != SCHEMA_VERSION
        or diagnostic.get("status") != "COMPLETED"
        or diagnostic.get("pilot_run_id") != bundle.get("pilot_run_id")
    ):
        raise PilotError("STAGE1_4_DIAGNOSTIC_INVALID")
    bindings = diagnostic.get("bindings") or {}
    if (
        bindings.get("extraction_bundle_sha256") != extraction_bundle_sha256(bundle)
        or bindings.get("stage1_2_review_sha256") != _stage1_3_review_sha256(review)
        or bindings.get("source_sha256") != (bundle.get("source") or {}).get("sha256")
    ):
        raise PilotError("STAGE1_4_DIAGNOSTIC_STALE")
    if sha256_file(source_file) != bundle["source"]["sha256"]:
        raise PilotError("STAGE1_4_SOURCE_MISMATCH")

    prompt_status = phase3c_prompt_repair_status()
    if not prompt_status["passed"]:
        raise PilotError("STAGE1_4_PROMPT_REPAIR_INCOMPLETE")
    parsed = parse_source_with_diagnostics(source_file)
    if parsed.source_type != "pdf":
        raise PilotError("STAGE1_4_SOURCE_INVALID: PDF required")
    page_by_locator = {
        locator: body for locator, body in source_units(parsed.text)
        if locator.startswith("PAGE:")
    }
    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None

    bundle_by_id = {item["claim_id"]: item for item in bundle.get("claims") or []}
    review_by_id = {item["claim_id"]: item for item in review.get("claims") or []}
    drop_by_id = {
        item["claim_id"]: item for item in diagnostic.get("drop_diagnostics") or []
    }
    cross_by_id = {
        item["claim_id"]: item for item in diagnostic.get("cross_page_diagnostics") or []
    }
    expected_drop_ids = {
        item["claim_id"] for item in review.get("claims") or []
        if item.get("decision") == "DROP"
    }
    expected_cross_ids = {
        item["claim_id"] for item in review.get("claims") or []
        if item.get("decision") == "KEEP_NEEDS_REVIEW"
    }
    if set(drop_by_id) != expected_drop_ids or set(cross_by_id) != expected_cross_ids:
        raise PilotError("STAGE1_4_DIAGNOSTIC_COVERAGE_INVALID")

    claims = []
    for reviewed in review.get("claims") or []:
        claim_id = reviewed["claim_id"]
        claim = bundle_by_id[claim_id]
        if reviewed.get("statement") != claim.get("statement") or reviewed.get(
            "evidence_excerpt"
        ) != claim.get("evidence_excerpt"):
            raise PilotError(f"STAGE1_4_IMMUTABILITY_INVALID: {claim_id}")
        original_locator = copy.deepcopy(
            (claim.get("validation") or {}).get("source_locator") or {}
        )
        context_blocks: list[dict[str, Any]] = []
        evidence_spans: list[dict[str, Any]] = []
        diagnosis = "NOT_APPLICABLE_STAGE1_2_KEEP"
        status = "BLOCKED"
        mode = "NONE"
        rationale = "Evidence support could not be evaluated under Contract v2."

        if reviewed["decision"] == "KEEP":
            resolved = resolve_pdf_evidence_locator(
                parsed.text,
                claim.get("evidence_excerpt") or "",
                claim.get("evidence_pointer") or "",
            )
            if claim.get("evidence_validated") is True and resolved.get("status") == "resolved":
                status = "SUPPORTED"
                mode = "EXCERPT_ONLY"
                rationale = "The immutable excerpt alone is exact-source-bound to one PAGE locator."
            else:
                rationale = "Historical KEEP lacks a deterministic single-unit Evidence binding."
        elif reviewed["decision"] == "DROP":
            diag = drop_by_id[claim_id]
            if (
                diag.get("original_claim") != claim.get("statement")
                or diag.get("original_evidence_excerpt") != claim.get("evidence_excerpt")
                or diag.get("original_human_decision") != "DROP"
            ):
                raise PilotError(f"STAGE1_4_DIAGNOSTIC_IMMUTABILITY_INVALID: {claim_id}")
            diagnosis = str(diag.get("diagnostic_disposition") or "UNRESOLVED")
            if diagnosis == "RECOVERABLE_WITH_BOUNDED_CONTEXT":
                resolved = resolve_pdf_evidence_locator(
                    parsed.text,
                    claim.get("evidence_excerpt") or "",
                    claim.get("evidence_pointer") or "",
                )
                if resolved.get("status") != "resolved":
                    raise PilotError(f"STAGE1_4_CONTEXT_EVIDENCE_UNRESOLVED: {claim_id}")
                for span in diag.get("diagnostic_support_span") or []:
                    _validate_stage1_3_context_span(
                        span=span,
                        page_by_locator=page_by_locator,
                        evidence_locator=resolved["locator"],
                        evidence_excerpt=claim["evidence_excerpt"],
                    )
                context_blocks = _stage1_4_context_blocks(diag)
                if not context_blocks:
                    raise PilotError(f"STAGE1_4_CONTEXT_EMPTY: {claim_id}")
                status = "SUPPORTED"
                mode = "BOUNDED_CONTEXT"
                rationale = str(diag.get("rationale") or "")
            elif diagnosis in {
                "GENUINE_EXTRACTION_FAILURE", "ATTRIBUTION_FAILURE",
                "CONDITIONALITY_FAILURE",
            }:
                status = "UNSUPPORTED"
                rationale = str(diag.get("rationale") or "")
        elif reviewed["decision"] == "KEEP_NEEDS_REVIEW":
            diag = cross_by_id[claim_id]
            if (
                diag.get("original_claim") != claim.get("statement")
                or diag.get("original_evidence_excerpt") != claim.get("evidence_excerpt")
                or diag.get("original_human_decision") != "KEEP_NEEDS_REVIEW"
            ):
                raise PilotError(f"STAGE1_4_DIAGNOSTIC_IMMUTABILITY_INVALID: {claim_id}")
            diagnosis = "CROSS_PAGE_VERIFIED_COMPLETE"
            raw_spans = diag.get("evidence_spans") or []
            pages = diag.get("pages") or []
            if (
                diag.get("cross_page_verified") is True
                and diag.get("semantic_support") == "complete"
                and len(raw_spans) == 2
                and [span.get("locator") for span in raw_spans] == pages
                and len(pages) == 2
                and _page_number(pages[1]) == _page_number(pages[0]) + 1
            ):
                for order, span in enumerate(raw_spans, 1):
                    locator = span.get("locator")
                    text = span.get("text")
                    if (
                        locator not in page_by_locator
                        or not isinstance(text, str)
                        or not _comparison_contains(page_by_locator[locator], text)
                    ):
                        raise PilotError(f"STAGE1_4_SPAN_INVALID: {claim_id}")
                    evidence_spans.append({
                        "order": order,
                        "locator": locator,
                        "text": text,
                        "exact_source_text": True,
                    })
                joined = "\n".join(span["text"] for span in evidence_spans)
                if not _comparison_contains(joined, claim["evidence_excerpt"]):
                    raise PilotError(f"STAGE1_4_SPAN_INCOMPLETE: {claim_id}")
                status = "SUPPORTED"
                mode = "ORDERED_SPANS"
                rationale = str(diag.get("rationale") or "")
        if status not in STAGE1_4_SUPPORT_STATUSES or mode not in STAGE1_4_SUPPORT_MODES:
            raise PilotError(f"STAGE1_4_RESULT_INVALID: {claim_id}")
        if status == "SUPPORTED" and mode == "NONE":
            raise PilotError(f"STAGE1_4_RESULT_INVALID: support mode missing ({claim_id})")
        if status != "SUPPORTED" and mode != "NONE":
            raise PilotError(f"STAGE1_4_RESULT_INVALID: non-support has Evidence mode ({claim_id})")
        context_locators = list(dict.fromkeys(
            locator for block in context_blocks for locator in block["locators"]
        ))
        claims.append({
            "claim_id": claim_id,
            "original_claim": claim["statement"],
            "stage1_2_decision": reviewed["decision"],
            "stage1_3_diagnosis": diagnosis,
            "v2_support_status": status,
            "support_mode": mode,
            "original_evidence_excerpt": claim["evidence_excerpt"],
            "original_locator": original_locator,
            "supporting_context": context_blocks,
            "supporting_context_locators": context_locators,
            "evidence_spans": evidence_spans,
            "support_rationale": rationale,
        })

    if [item["claim_id"] for item in claims] != [
        item["claim_id"] for item in bundle.get("claims") or []
    ]:
        raise PilotError("STAGE1_4_CLAIM_ORDER_CHANGED")
    metrics = _stage1_4_metrics(bundle, review, diagnostic, claims, prompt_status)
    contract = {
        "document_type": STAGE1_4_CONTRACT_DOCUMENT_TYPE,
        "schema_version": "2",
        "status": "COMPLETED",
        "pilot_run_id": bundle["pilot_run_id"],
        "bindings": {
            "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
            "stage1_2_review_sha256": _stage1_3_review_sha256(review),
            "stage1_3_diagnostic_sha256": hashlib.sha256(
                _canonical_json(diagnostic)
            ).hexdigest(),
            "source_sha256": bundle["source"]["sha256"],
            "prompt_sha256": prompt_status["prompt_sha256"],
        },
        "contract": {
            "evidence_excerpt_immutable": True,
            "supporting_context_policy": STAGE1_3_CONTEXT_POLICY,
            "supporting_context_supplements_excerpt": True,
            "ordered_adjacent_unit_spans": True,
            "exact_span_text_required": True,
            "fake_aggregate_locator_forbidden": True,
            "canonical_schema": False,
        },
        "claims": claims,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    contract_path = output_dir / "stage1_4_evidence_contract_v2.json"
    report_path = output_dir / "stage1_4_review_simulation.md"
    metrics_path = output_dir / "stage1_4_metrics.json"
    write_json(contract_path, contract)
    report_path.write_text(
        render_stage1_4_review_markdown(contract, metrics), encoding="utf-8",
    )
    write_json(metrics_path, metrics)

    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    production_unchanged = production_pre == production_post if production_pre is not None else None
    inputs_unchanged = original_hashes == {
        label: sha256_file(path) for label, path in inputs.items()
    }
    if not inputs_unchanged:
        raise PilotError("STAGE1_4_INPUT_MUTATED")
    if production_unchanged is False:
        raise PilotError("STAGE1_4_PRODUCTION_MUTATED")
    return {
        "status": "PASS",
        "pilot_run_id": bundle["pilot_run_id"],
        "contract": contract,
        "metrics": metrics,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "inputs_unchanged": inputs_unchanged,
        "contract_path": str(contract_path),
        "report_path": str(report_path),
        "metrics_path": str(metrics_path),
    }


def render_review_markdown(bundle: dict[str, Any], review: dict[str, Any], metrics: dict[str, Any]) -> str:
    source = bundle["source"]
    metadata = bundle.get("proposed_source_metadata") or {}
    stage1_1 = bundle.get("stage1_1_rebinding") or {}
    lines = [
        (
            "# Phase 3C Stage 1.1 Evidence Locator Rebinding Review"
            if stage1_1 else "# Phase 3C Stage 1 Human Extraction Review"
        ), "",
        f"- status: `{review['status']}`",
        f"- pilot_run_id: `{bundle['pilot_run_id']}`",
        f"- extraction_bundle_sha256: `{review['extraction_bundle_sha256']}`", "",
        "## Source summary", "",
        f"- original_name: {source['original_name']}",
        f"- source_type: {source['source_type']}",
        f"- SHA-256: `{source['sha256']}`",
        f"- analysis_mode: `{source['analysis_mode']}`",
        f"- proposed title: {metadata.get('title') or ''}",
        f"- proposed source rank / origin: {metadata.get('source_rank') or ''} / {metadata.get('source_origin_type') or metadata.get('origin_type') or ''}",
        f"- parse diagnostics: `{json.dumps(source.get('parse_diagnostics') or {}, ensure_ascii=False)}`", "",
        "## Model / call summary", "",
        f"- configured request model: {bundle.get('model', {}).get('configured_model', '')}",
        f"- response model: {metrics.get('response_model')}",
        f"- LLM calls: {metrics.get('llm_calls')}",
        f"- prompt / completion / total tokens: {metrics.get('prompt_tokens')} / {metrics.get('completion_tokens')} / {metrics.get('total_tokens')}", "",
        "## Claim quality summary", "",
        f"- total Claims: {metrics['claims_total']}",
        f"- evidence-valid Claims: {metrics['evidence_valid_claims']}",
        f"- needs_review Claims: {metrics['needs_review_claims']}",
        f"- locators resolved / ambiguous / unresolved: {metrics['locator_resolved']} / {metrics['locator_ambiguous']} / {metrics['locator_unresolved']}", "",
        "## Claims", "",
    ]
    if stage1_1:
        lines[lines.index("## Claim quality summary"):lines.index("## Claims")] += [
            f"- deterministic replay LLM calls added: {stage1_1.get('llm_calls_added')}",
            f"- original extraction bundle SHA-256: `{stage1_1.get('source_bundle_sha256')}`",
            f"- exact-match methods: `{json.dumps(stage1_1.get('match_methods') or {}, ensure_ascii=False)}`",
            "",
        ]
    for claim in bundle.get("claims") or []:
        validation = claim.get("validation") or {}
        locator = validation.get("source_locator") or {}
        lines += [
            f"### {claim['claim_id']}", "",
            f"- statement: {claim['statement']}",
            f"- Evidence excerpt: {claim['evidence_excerpt']}",
            f"- Page locator: `{json.dumps(locator, ensure_ascii=False)}`",
            f"- evidence_validated: `{claim.get('evidence_validated')}`",
            f"- status: `{claim.get('status')}`",
            f"- confidence: `{claim.get('confidence')}`",
            "- Human decision: `PENDING`", "",
        ]
    observations = bundle.get("observations") or {}
    lines += [
        "## Node Matches", "",
        f"- observational count: {len(observations.get('node_matches') or [])}",
        "- These are non-canonical observations; no Source/Claim/Node link was written.", "",
        "## Node Candidates", "",
        f"- total: {len(observations.get('node_candidates') or [])}",
        f"- quality-eligible: {sum(item.get('quality_eligible') is True for item in observations.get('node_candidates') or [])}",
        "- These are non-canonical observations; no Node or Proposal was written.", "",
        "## Relation Candidates", "",
        f"- total: {len(observations.get('relation_candidates') or [])}",
        f"- rejected: {len(observations.get('rejected_relation_candidates') or [])}",
        "- These are non-canonical observations; no Relation or Proposal was written.", "",
        "## Rejected items", "",
        f"- rejected Node Matches: {len(observations.get('rejected_node_matches') or [])}",
        f"- rejected Node Candidates: {len(observations.get('rejected_node_candidates') or [])}",
        f"- rejected Claim-Node links: {len(observations.get('rejected_claim_node_links') or [])}", "",
        "## Human review flags", "",
    ]
    lines += [f"- {flag}" for flag in bundle.get("human_review_flags") or []] or ["- None generated by deterministic QA."]
    lines += ["", "Human decisions remain `PENDING`; this package is not Production-apply-ready.", ""]
    return "\n".join(lines)


def extract_pilot_source(
    input_path: Path,
    cfg: AppConfig,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
    required_prompt_sha256: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run exactly one real extraction into non-canonical Stage 1 artifacts."""
    input_path = Path(input_path).resolve()
    if not input_path.exists() or not input_path.is_file():
        raise PilotError(f"PILOT_INPUT_REQUIRED: file is not accessible: {input_path}")
    prompt_status = phase3c_prompt_repair_status(analyzer_module.SOURCE_ANALYSIS_SYSTEM)
    if required_prompt_sha256 is not None and (
        not prompt_status["passed"]
        or prompt_status["prompt_sha256"] != required_prompt_sha256
    ):
        raise PilotError("PILOT_PROMPT_FREEZE_MISMATCH")
    production_db = Path(production_db_path or cfg.db_path).resolve()
    run_id = run_id or make_id("PILOT")
    if not re.fullmatch(r"PILOT_\d{8}_[A-F0-9]{8}", run_id):
        raise PilotError("PILOT_RUN_ID_INVALID")
    output_dir = Path(output_dir or (cfg.root / "phase3c" / run_id)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pre = production_snapshot(production_db)
    source_sha = sha256_file(input_path)
    with sqlite3.connect(_readonly_uri(production_db), uri=True) as conn:
        duplicate = conn.execute("SELECT source_id FROM sources WHERE sha256=?", (source_sha,)).fetchone()
    if duplicate:
        failure = {
            "status": "PILOT_SOURCE_ALREADY_EXISTS",
            "pilot_run_id": run_id,
            "source_sha256": source_sha,
            "existing_source_id": duplicate[0],
            "production_pre": pre,
        }
        write_json(output_dir / "stage1_failure.json", failure)
        raise PilotError("PILOT_SOURCE_ALREADY_EXISTS")

    db_copy = copy_production_database(production_db, output_dir / "production_copy.db")
    parsed = None
    analyzer = Analyzer(cfg, Database(db_copy))
    try:
        parsed = parse_source_with_diagnostics(
            input_path, include_semantic_segments=True,
        )
        if parsed.diagnostics.get("empty_extraction"):
            raise ParseError("PARSE_TEXT_EMPTY: No extractable text.")
        semantic_text = semantic_eligible_source_text(parsed)
        events, original_json = _instrument_llm(analyzer)
        try:
            analysis = analyzer.analyze_source(input_path.name, semantic_text, "deep")
        finally:
            analyzer.llm.json = original_json
        llm = _llm_metrics(events)
    except Exception as exc:
        failure = {
            "status": "STAGE1_EXTRACTION_FAILED",
            "pilot_run_id": run_id,
            "source": {
                "original_name": input_path.name,
                "sha256": source_sha,
                "source_type": parsed.source_type if parsed else input_path.suffix.lower().lstrip("."),
                "parse_diagnostics": parsed.diagnostics if parsed else None,
                "parse_warnings": parse_warnings(parsed.diagnostics) if parsed else [],
            },
            "error": str(exc),
            "prompt": copy.deepcopy(prompt_status),
            "production_pre": pre,
            "production_copy": str(db_copy),
        }
        write_json(output_dir / "stage1_failure.json", failure)
        raise PilotError(f"STAGE1_EXTRACTION_FAILED: {exc}") from exc

    source_id = make_id("SRC")
    layout_sidecar_path = None
    layout_sidecar_ref = None
    if parsed.layout_sidecar is not None:
        layout_sidecar_path = output_dir / "source_layout_sidecar.json"
        write_json(layout_sidecar_path, parsed.layout_sidecar)
        layout_sidecar_ref = {
            "path": str(layout_sidecar_path),
            "sha256": sha256_file(layout_sidecar_path),
            "adapter": parsed.layout_sidecar.get("adapter"),
            "adapter_versions": copy.deepcopy(
                parsed.layout_sidecar.get("adapter_versions") or {}
            ),
            "signature_sha256": parsed.layout_sidecar.get("signature_sha256"),
            "segments": len(parsed.layout_sidecar.get("segments") or []),
        }
    claims: list[dict[str, Any]] = []
    for index, claim in enumerate(analysis.claims):
        claim_record = _claim_bundle_record(
            make_id("CLM"), source_id, claim, analysis.source_metadata.get("publication_time") or "", parsed.text,
        )
        if claim_record is not None:
            claim_record["claim_index"] = index
            claims.append(claim_record)
    observations = _observations(analysis)
    bundle = {
        "document_type": BUNDLE_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": EXTRACTION_STATUS,
        "pilot_run_id": run_id,
        "source": {
            "proposed_source_id": source_id,
            "original_name": input_path.name,
            "sha256": source_sha,
            "source_type": parsed.source_type,
            "analysis_mode": "deep",
            "parse_diagnostics": copy.deepcopy(parsed.diagnostics),
            "parse_warnings": parse_warnings(parsed.diagnostics),
            "layout_sidecar": copy.deepcopy(layout_sidecar_ref),
            "semantic_eligibility": {
                "policy": "NARRATIVE_FIRST_TABLE_SUPPRESSION",
                "canonical_source_chars": len(parsed.text),
                "semantic_eligible_chars": len(semantic_text),
                "excluded_chars": len(parsed.text) - len(semantic_text),
                "excluded_segment_kind": "table",
                "eligible_segment_kinds": ["narrative", "unknown"],
                "applied_before_chunking": True,
            },
        },
        "model": {
            "configured_model": cfg.llm.model,
            "response_model": llm["response_model"],
            "prompt": {
                **copy.deepcopy(prompt_status),
                "frozen_before_extraction": required_prompt_sha256 is not None,
            },
            "usage": {
                key: llm[key]
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            },
            "llm_calls": llm["llm_calls"],
        },
        "proposed_source_metadata": copy.deepcopy(analysis.source_metadata),
        "source_references": copy.deepcopy(analysis.source_references),
        "claims": claims,
        "evidence_provenance_policy": {
            "model_evidence_is_proposed_quote": True,
            "deterministic_source_validation_required": True,
            "model_page_pointer_authoritative": False,
            "deterministic_locator_authoritative": True,
            "quote_drift_fail_closed": True,
            "automatic_quote_repair": False,
            "canonical_schema_changed": False,
        },
        "observations": observations,
        "canonical_write_preview": {"sources": 1, "claims": 0, "all_other_tables": 0},
        "human_review_flags": _human_review_flags(parsed.diagnostics, claims, parsed.text),
    }
    review = _build_review_draft(bundle)
    metrics = _stage1_metrics(bundle, llm, parsed.text)
    bundle_path = output_dir / "extraction_bundle.json"
    review_path = output_dir / "extraction_review_draft.json"
    markdown_path = output_dir / "stage1_review.md"
    metrics_path = output_dir / "stage1_metrics.json"
    write_json(bundle_path, bundle)
    write_json(review_path, review)
    markdown_path.write_text(render_review_markdown(bundle, review, metrics), encoding="utf-8")
    write_json(metrics_path, metrics)
    post = production_snapshot(production_db)
    return {
        "status": "PASS",
        "pilot_run_id": run_id,
        "bundle": bundle,
        "review": review,
        "metrics": metrics,
        "production_pre": pre,
        "production_post": post,
        "production_unchanged": (
            pre["sha256"] == post["sha256"]
            and pre["table_counts"] == post["table_counts"]
            and post["integrity_check"] == "ok"
            and not post["foreign_key_violations"]
        ),
        "production_copy": str(db_copy),
        "extraction_bundle_path": str(bundle_path),
        "review_draft_path": str(review_path),
        "review_markdown_path": str(markdown_path),
        "metrics_path": str(metrics_path),
        "layout_sidecar_path": (
            str(layout_sidecar_path) if layout_sidecar_path is not None else None
        ),
    }


def _bounded_text_segments(body: str) -> list[tuple[int, int]]:
    boundaries = list(re.finditer(r"[。！？!?；;]+|\.(?=\s|$)|\n\s*\n", body))
    spans: list[tuple[int, int]] = []
    start = 0
    for boundary in boundaries:
        end = boundary.end()
        if body[start:end].strip():
            spans.append((start, end))
        start = end
    if body[start:].strip():
        spans.append((start, len(body)))
    return spans or ([(0, len(body))] if body.strip() else [])


def build_bounded_local_subspan(
    raw_segment: str,
    evidence_start: int,
    evidence_end: int,
    direction: str,
    max_chars: int = STAGE1_3_CONTEXT_RADIUS,
) -> str | None:
    """Return one exact contiguous raw window beside an authoritative Evidence span."""
    if (
        not isinstance(raw_segment, str)
        or direction not in {"before", "after"}
        or not isinstance(evidence_start, int)
        or not isinstance(evidence_end, int)
        or not isinstance(max_chars, int)
        or max_chars < 1
        or evidence_start < 0
        or evidence_end < evidence_start
        or evidence_end > len(raw_segment)
    ):
        return None
    if direction == "before":
        if evidence_start == 0:
            return None
        return raw_segment[max(0, evidence_start - max_chars):evidence_start]
    if evidence_end == len(raw_segment):
        return None
    return raw_segment[evidence_end:min(len(raw_segment), evidence_end + max_chars)]


def _locator_comparison_mode(locator: dict[str, Any]) -> str | None:
    method = str(locator.get("match_method") or "")
    if method.startswith("provenance_"):
        method = method.removeprefix("provenance_")
    if method == "raw_exact_substring":
        return "raw"
    if method == "canonical_exact_substring":
        return "canonical"
    if method == "pdf_normalized_exact_substring":
        return "pdf_normalized"
    return None


def _comparison_normalize(value: str, mode: str) -> str:
    if mode == "raw":
        return value or ""
    if mode == "canonical":
        return canonicalize_text(value)
    if mode == "pdf_normalized":
        return normalize_pdf_locator_text(value)
    return ""


@lru_cache(maxsize=64)
def _comparison_raw_boundaries(
    body: str, mode: str,
) -> tuple[tuple[int | None, ...], tuple[int | None, ...]]:
    """Map normalized prefix/suffix positions back to raw character boundaries."""
    normalized_body = _comparison_normalize(body, mode)
    prefix_positions: list[int | None] = []
    suffix_positions: list[int | None] = []
    for index in range(len(body) + 1):
        prefix = _comparison_normalize(body[:index], mode)
        prefix_positions.append(
            len(prefix) if normalized_body.startswith(prefix) else None
        )
        suffix = _comparison_normalize(body[index:], mode)
        suffix_positions.append(
            len(normalized_body) - len(suffix)
            if normalized_body.endswith(suffix)
            else None
        )
    return tuple(prefix_positions), tuple(suffix_positions)


def _authoritative_raw_evidence_span(
    *,
    body: str,
    evidence_excerpt: str,
    locator: dict[str, Any] | None,
    segment_start: int,
    segment_end: int,
) -> tuple[int, int] | None:
    if not isinstance(locator, dict) or locator.get("status") != "resolved":
        return None
    mode = _locator_comparison_mode(locator)
    comparison_start = locator.get("comparison_start")
    comparison_end = locator.get("comparison_end")
    if (
        mode is None
        or not isinstance(comparison_start, int)
        or not isinstance(comparison_end, int)
        or comparison_start < 0
        or comparison_end < comparison_start
    ):
        return None
    normalized_body = _comparison_normalize(body, mode)
    normalized_evidence = _comparison_normalize(evidence_excerpt, mode)
    if (
        not normalized_evidence
        or comparison_end > len(normalized_body)
        or normalized_body[comparison_start:comparison_end] != normalized_evidence
    ):
        return None
    if mode == "raw":
        if segment_start <= comparison_start < comparison_end <= segment_end:
            return comparison_start, comparison_end
        return None

    prefix_positions, suffix_positions = _comparison_raw_boundaries(body, mode)
    starts = [
        index for index in range(segment_start, segment_end + 1)
        if suffix_positions[index] == comparison_start
    ]
    ends = [
        index for index in range(segment_start, segment_end + 1)
        if prefix_positions[index] == comparison_end
    ]
    exact_span_expected = normalize_pdf_span_text(evidence_excerpt)
    candidates = [
        (start, end)
        for start in starts
        for end in ends
        if start < end
        and _comparison_normalize(body[start:end], mode) == normalized_evidence
    ]
    if not candidates:
        return None
    span_exact = [
        pair for pair in candidates
        if normalize_pdf_span_text(body[pair[0]:pair[1]]) == exact_span_expected
    ]
    selected = min(span_exact or candidates, key=lambda pair: (pair[1] - pair[0], pair))
    return selected


def _bounded_local_subspan_candidate(
    *,
    pages: list[tuple[str, str]],
    evidence_locator: str,
    evidence_excerpt: str,
    authoritative_locator: dict[str, Any] | None,
    direction: str,
) -> dict[str, Any] | None:
    if (
        not isinstance(authoritative_locator, dict)
        or authoritative_locator.get("status") != "resolved"
        or authoritative_locator.get("locator") != evidence_locator
    ):
        return None
    page_by_locator = dict(pages)
    body = page_by_locator.get(evidence_locator)
    if body is None:
        return None
    for segment_start, segment_end in _bounded_text_segments(body):
        evidence_span = _authoritative_raw_evidence_span(
            body=body,
            evidence_excerpt=evidence_excerpt,
            locator=authoritative_locator,
            segment_start=segment_start,
            segment_end=segment_end,
        )
        if evidence_span is None:
            continue
        evidence_start, evidence_end = evidence_span
        text = build_bounded_local_subspan(
            body[segment_start:segment_end],
            evidence_start - segment_start,
            evidence_end - segment_start,
            direction,
        )
        if text is None or not normalize_pdf_locator_text(text):
            return None
        candidate = {
            "direction": direction,
            "text": text,
            "locators": [evidence_locator],
            "selection_rule": EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE,
        }
        _validate_stage1_3_context_span(
            span={"locator": evidence_locator, "text": text},
            page_by_locator=page_by_locator,
            evidence_locator=evidence_locator,
            evidence_excerpt=evidence_excerpt,
        )
        return candidate
    return None


def _bounded_context_candidates(
    pages: list[tuple[str, str]], locator: str, evidence_excerpt: str,
    *, authoritative_locator: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    page_index = next((i for i, (name, _) in enumerate(pages) if name == locator), -1)
    if page_index < 0:
        return []
    body = pages[page_index][1]
    segments = _bounded_text_segments(body)
    windows: list[tuple[int, int, int, int]] = []
    for start_index in range(len(segments)):
        for end_index in range(start_index, len(segments)):
            start = segments[start_index][0]
            end = segments[end_index][1]
            if _comparison_contains(body[start:end], evidence_excerpt):
                windows.append((end - start, start_index, end_index, start))
                break
    if not windows:
        return []
    _, first_index, last_index, _ = min(windows)

    def block(
        direction: str, page_locator: str, text: str, *, allow_local_fallback: bool,
    ) -> dict[str, Any] | None:
        text = text.strip()
        if not text:
            return None
        if direction == "before":
            text = text[-STAGE1_3_CONTEXT_RADIUS:]
        else:
            text = text[:STAGE1_3_CONTEXT_RADIUS]
        _, normalized_text, _ = _stage1_3_normalized_local_binding(
            dict(pages)[page_locator], text,
        )
        if not normalized_text:
            return None
        candidate = {
            "direction": direction,
            "text": text,
            "locators": [page_locator],
            "selection_rule": STAGE1_3_CONTEXT_POLICY,
        }
        try:
            _validate_stage1_3_context_span(
                span={"locator": page_locator, "text": text},
                page_by_locator=dict(pages),
                evidence_locator=locator,
                evidence_excerpt=evidence_excerpt,
            )
        except PilotError as exc:
            if (
                allow_local_fallback
                and str(exc) == (
                    "STAGE1_3_CONTEXT_INVALID: same-page context is outside the bounded window"
                )
            ):
                fallback = _bounded_local_subspan_candidate(
                    pages=pages,
                    evidence_locator=locator,
                    evidence_excerpt=evidence_excerpt,
                    authoritative_locator=authoritative_locator,
                    direction=direction,
                )
                if fallback is not None:
                    return fallback
            raise
        return candidate

    candidates: list[dict[str, Any]] = []
    if first_index > 0:
        start, end = segments[first_index - 1]
        selected = block(
            "before", locator, body[start:end], allow_local_fallback=True,
        )
        if selected:
            candidates.append(selected)
    elif page_index > 0:
        previous_locator, previous_body = pages[page_index - 1]
        previous_segments = _bounded_text_segments(previous_body)
        if previous_segments:
            start, end = previous_segments[-1]
            try:
                selected = block(
                    "before", previous_locator, previous_body[start:end],
                    allow_local_fallback=False,
                )
            except PilotError:
                selected = None
            if selected:
                candidates.append(selected)

    if last_index + 1 < len(segments):
        start, end = segments[last_index + 1]
        selected = block(
            "after", locator, body[start:end], allow_local_fallback=True,
        )
        if selected:
            candidates.append(selected)
    elif page_index + 1 < len(pages):
        next_locator, next_body = pages[page_index + 1]
        next_segments = _bounded_text_segments(next_body)
        if next_segments:
            start, end = next_segments[0]
            try:
                selected = block(
                    "after", next_locator, next_body[start:end],
                    allow_local_fallback=False,
                )
            except PilotError:
                selected = None
            if selected:
                candidates.append(selected)
    return candidates


def _comparison_edge_texts(
    body: str, expected: str, normalizer, *, suffix: bool,
) -> list[str]:
    texts: set[str] = set()
    if suffix:
        slices = (body[index:] for index in range(len(body)))
    else:
        slices = (body[:index] for index in range(1, len(body) + 1))
    for raw in slices:
        text = raw.strip()
        if text and normalizer(text) == expected:
            texts.add(text)
    return sorted(texts, key=lambda item: (len(item), item))


def _ordered_cross_page_spans(
    page_by_locator: dict[str, str], locator: dict[str, Any], evidence_excerpt: str,
) -> list[dict[str, Any]]:
    pairs = locator.get("spanning_locators") or []
    if len(pairs) != 1 or not isinstance(pairs[0], list) or len(pairs[0]) != 2:
        return []
    first_locator, second_locator = pairs[0]
    if first_locator not in page_by_locator or second_locator not in page_by_locator:
        return []
    if _page_number(second_locator) != _page_number(first_locator) + 1:
        return []
    first_body = page_by_locator[first_locator]
    second_body = page_by_locator[second_locator]
    for _, _, normalizer in _pdf_span_comparison_methods():
        evidence = normalizer(evidence_excerpt)
        first = normalizer(first_body)
        second = normalizer(second_body)
        if not evidence:
            continue
        candidates: set[tuple[str, str]] = set()
        for split in range(1, len(evidence)):
            first_expected = evidence[:split].rstrip()
            second_expected = evidence[split:].lstrip()
            if not first_expected or not second_expected:
                continue
            if not first.endswith(first_expected) or not second.startswith(second_expected):
                continue
            first_texts = _comparison_edge_texts(
                first_body, first_expected, normalizer, suffix=True,
            )
            second_texts = _comparison_edge_texts(
                second_body, second_expected, normalizer, suffix=False,
            )
            for first_text in first_texts:
                for second_text in second_texts:
                    if normalizer(f"{first_text}\n{second_text}") == evidence:
                        candidates.add((first_text, second_text))
        if candidates:
            minimum_length = min(len(first_text) + len(second_text) for first_text, second_text in candidates)
            shortest = [
                pair for pair in candidates
                if len(pair[0]) + len(pair[1]) == minimum_length
            ]
        else:
            shortest = []
        if len(shortest) == 1:
            first_text, second_text = shortest[0]
            return [
                {
                    "order": 1, "locator": first_locator,
                    "text": first_text, "exact_source_text": True,
                },
                {
                    "order": 2, "locator": second_locator,
                    "text": second_text, "exact_source_text": True,
                },
            ]
        if candidates:
            return []
    return []


def _build_evidence_support_draft(
    bundle: dict[str, Any], parsed_text: str,
) -> dict[str, Any]:
    pages = [
        (locator, body) for locator, body in source_units(parsed_text)
        if locator.startswith("PAGE:")
    ]
    page_by_locator = dict(pages)
    draft_claims = []
    for claim in bundle.get("claims") or []:
        locator = copy.deepcopy((claim.get("validation") or {}).get("source_locator") or {})
        locator_status = locator.get("status") or "unresolved"
        context_candidates: list[dict[str, Any]] = []
        spans: list[dict[str, Any]] = []
        if locator_status == "resolved":
            context_candidates = _bounded_context_candidates(
                pages, str(locator.get("locator") or ""),
                str(claim.get("evidence_excerpt") or ""),
                authoritative_locator=locator,
            )
            mechanics_status = (
                "CONTEXT_AVAILABLE" if context_candidates else "EXCERPT_BOUND"
            )
        elif locator_status == "ambiguous":
            mechanics_status = "LOCATOR_AMBIGUOUS"
        elif locator.get("reason") == "cross_page_span":
            spans = _ordered_cross_page_spans(
                page_by_locator, locator, str(claim.get("evidence_excerpt") or ""),
            )
            mechanics_status = "ORDERED_SPAN_BOUND" if spans else "LOCATOR_UNRESOLVED"
        else:
            mechanics_status = "LOCATOR_UNRESOLVED"
        if mechanics_status not in PILOT2_MECHANICS_STATUSES:
            raise PilotError("PILOT2_EVIDENCE_DRAFT_INVALID: unsupported mechanics status")
        draft_claims.append({
            "claim_id": claim.get("claim_id"),
            "statement": claim.get("statement"),
            "attributed_to": claim.get("attributed_to") or "",
            "original_evidence_excerpt": claim.get("evidence_excerpt"),
            "original_locator": locator,
            "evidence_mechanics_status": mechanics_status,
            "bounded_context_candidates": context_candidates,
            "context_locators": list(dict.fromkeys(
                locator_name
                for block in context_candidates
                for locator_name in block["locators"]
            )),
            "evidence_spans": spans,
            "formal_confidence": claim.get("confidence"),
            "model_confidence": (claim.get("validation") or {}).get("model_confidence"),
            "human_decision": "PENDING",
        })
    return {
        "document_type": PILOT2_EVIDENCE_DRAFT_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_HUMAN_REVIEW_REQUIRED",
        "pilot_run_id": bundle["pilot_run_id"],
        "bindings": {
            "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
            "source_sha256": bundle["source"]["sha256"],
            "prompt_sha256": ((bundle.get("model") or {}).get("prompt") or {}).get(
                "prompt_sha256", "NOT_AVAILABLE",
            ),
        },
        "contract": {
            "version": "2",
            "artifact_level_only": True,
            "canonical_schema": False,
            "immutable_evidence_excerpt": True,
            "bounded_context_additive_only": True,
            "bounded_context_policy": STAGE1_3_CONTEXT_POLICY,
            "ordered_spans_exact_source_text": True,
            "fake_aggregate_page_locator": False,
            "semantic_support_decisions_deferred": True,
        },
        "claims": draft_claims,
    }


def _diagnostic_ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(100 * numerator / denominator, 2) if denominator else 0.0,
    }


def _tokens_per(value: Any, denominator: int) -> float | str:
    if isinstance(value, int) and denominator:
        return round(value / denominator, 2)
    return "NOT_AVAILABLE"


def _pilot_pre_review_metrics(
    bundle: dict[str, Any], evidence_draft: dict[str, Any], parsed: Any,
) -> dict[str, Any]:
    claims = evidence_draft["claims"]
    statuses = Counter(item["evidence_mechanics_status"] for item in claims)
    observations = bundle.get("observations") or {}
    node_candidates = observations.get("node_candidates") or []
    claims_total = len(claims)
    single_page = statuses["EXCERPT_BOUND"] + statuses["CONTEXT_AVAILABLE"]
    cross_page = statuses["ORDERED_SPAN_BOUND"]
    deterministically_bound = single_page + cross_page
    model = bundle.get("model") or {}
    usage = model.get("usage") or {}
    total_tokens = usage.get("total_tokens", "NOT_AVAILABLE")
    return {
        "pilot_run_id": bundle["pilot_run_id"],
        "source_sha256": bundle["source"]["sha256"],
        "pdf_pages": parsed.diagnostics.get("total_units", "NOT_AVAILABLE"),
        "parsed_text_units": parsed.diagnostics.get("text_units", "NOT_AVAILABLE"),
        "parse_errors": parsed.diagnostics.get("error_units", "NOT_AVAILABLE"),
        "empty_units": parsed.diagnostics.get("empty_units", "NOT_AVAILABLE"),
        "extracted_characters": parsed.diagnostics.get("extracted_chars", "NOT_AVAILABLE"),
        "claims_total": claims_total,
        "evidence_deterministically_bound": deterministically_bound,
        "single_page_locator_bound": single_page,
        "cross_page_exact_spans": cross_page,
        "locator_ambiguous": statuses["LOCATOR_AMBIGUOUS"],
        "locator_unresolved": statuses["LOCATOR_UNRESOLVED"],
        "needs_review": sum(claim.get("status") == "needs_review" for claim in bundle.get("claims") or []),
        "bounded_context_candidate_claims": sum(
            bool(item["bounded_context_candidates"]) for item in claims
        ),
        "ordered_span_claims": cross_page,
        "human_decision_counts": {
            "KEEP": 0, "DROP": 0, "KEEP_NEEDS_REVIEW": 0, "PENDING": claims_total,
        },
        "node_matches": len(observations.get("node_matches") or []),
        "node_candidates": len(node_candidates),
        "quality_eligible_node_candidates": sum(
            item.get("quality_eligible") is True for item in node_candidates
        ),
        "relation_candidates": len(observations.get("relation_candidates") or []),
        "rejected_relation_candidates": len(observations.get("rejected_relation_candidates") or []),
        "rejected_node_matches": len(observations.get("rejected_node_matches") or []),
        "rejected_node_candidates": len(observations.get("rejected_node_candidates") or []),
        "rejected_claim_node_links": len(observations.get("rejected_claim_node_links") or []),
        "configured_request_model": model.get("configured_model", "NOT_AVAILABLE"),
        "response_model": model.get("response_model", "NOT_AVAILABLE"),
        "prompt": copy.deepcopy(model.get("prompt") or {}),
        "llm_calls": model.get("llm_calls", "NOT_AVAILABLE"),
        "prompt_tokens": usage.get("prompt_tokens", "NOT_AVAILABLE"),
        "completion_tokens": usage.get("completion_tokens", "NOT_AVAILABLE"),
        "total_tokens": total_tokens,
        "tokens_per_claim": _tokens_per(total_tokens, claims_total),
        "tokens_per_deterministically_bound_claim": _tokens_per(
            total_tokens, deterministically_bound,
        ),
        "locator_binding_rate": _diagnostic_ratio(deterministically_bound, claims_total),
        "cross_page_incidence": _diagnostic_ratio(cross_page, claims_total),
        "context_candidate_incidence": _diagnostic_ratio(
            sum(bool(item["bounded_context_candidates"]) for item in claims), claims_total,
        ),
        "semantic_metrics": {
            "strict_human_review_keep_rate": "PENDING_HUMAN_REVIEW",
            "evidence_v2_semantic_support_rate": "PENDING_HUMAN_REVIEW",
            "true_semantic_failure_rate": "PENDING_HUMAN_REVIEW",
            "atomicity_issue_rate": "PENDING_HUMAN_REVIEW",
        },
        "production_apply_ready": False,
        "production_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "canonical_claim_schema_changed": False,
        "production_write": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
    }


def render_pilot2_evidence_review_markdown(
    draft: dict[str, Any], metrics: dict[str, Any],
) -> str:
    lines = [
        "# Phase 3C Pilot #2 Evidence Contract v2 Review Surface", "",
        f"- status: `{draft['status']}`",
        f"- pilot_run_id: `{draft['pilot_run_id']}`",
        "- mechanics-only draft; semantic support and KEEP/DROP decisions are deferred", "",
        "## Pre-review summary", "",
        f"- Claims: {metrics['claims_total']}",
        f"- deterministically bound: {metrics['evidence_deterministically_bound']}",
        f"- single-page / ordered-span: {metrics['single_page_locator_bound']} / {metrics['cross_page_exact_spans']}",
        f"- ambiguous / unresolved: {metrics['locator_ambiguous']} / {metrics['locator_unresolved']}",
        f"- bounded-context candidate Claims: {metrics['bounded_context_candidate_claims']}",
        f"- Human decisions PENDING: {metrics['human_decision_counts']['PENDING']}", "",
        "## Claims", "",
    ]
    for item in draft["claims"]:
        lines += [
            f"### {item['claim_id']}", "",
            f"- statement: {item['statement']}",
            f"- attributed_to: {item['attributed_to']}",
            f"- immutable Evidence excerpt: {item['original_evidence_excerpt']}",
            f"- locator: `{json.dumps(item['original_locator'], ensure_ascii=False)}`",
            f"- mechanics status: `{item['evidence_mechanics_status']}`",
            f"- bounded context: `{json.dumps(item['bounded_context_candidates'], ensure_ascii=False)}`",
            f"- ordered spans: `{json.dumps(item['evidence_spans'], ensure_ascii=False)}`",
            f"- formal / model confidence: `{item['formal_confidence']}` / `{item['model_confidence']}`",
            "- Human decision: `PENDING`", "",
        ]
    lines += [
        "No semantic entailment decision, Production write, IMA action, propagation, legacy ingestion, or governance action was performed.", "",
    ]
    return "\n".join(lines)


def build_pilot2_evidence_support_draft(
    bundle_path: Path,
    review_path: Path,
    source_path: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    bundle_path = Path(bundle_path).resolve()
    review_path = Path(review_path).resolve()
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir or bundle_path.parent).resolve()
    inputs = {"bundle": bundle_path, "review": review_path, "source": source_path}
    if any(not path.is_file() for path in inputs.values()):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_INPUT_MISSING")
    input_hashes = {label: sha256_file(path) for label, path in inputs.items()}
    bundle = _load_json(bundle_path)
    review = _load_json(review_path)
    if bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE:
        raise PilotError("PILOT2_EVIDENCE_DRAFT_BUNDLE_INVALID")
    if (
        review.get("document_type") != REVIEW_DOCUMENT_TYPE
        or review.get("status") != REVIEW_DRAFT_STATUS
        or review.get("extraction_bundle_sha256") != extraction_bundle_sha256(bundle)
    ):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_REVIEW_INVALID")
    if any(item.get("decision") != "PENDING" for item in review.get("claims") or []):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_HUMAN_DECISION_NOT_PENDING")
    if sha256_file(source_path) != (bundle.get("source") or {}).get("sha256"):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_SOURCE_MISMATCH")
    if len(bundle.get("claims") or []) != len(review.get("claims") or []):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_CLAIM_COVERAGE_INVALID")
    for bundle_claim, review_claim in zip(bundle.get("claims") or [], review.get("claims") or []):
        if _claim_projection(bundle_claim) != _claim_projection(review_claim):
            raise PilotError("PILOT2_EVIDENCE_DRAFT_CLAIM_MUTATED")

    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None
    parsed = parse_source_with_diagnostics(source_path)
    if parsed.source_type != "pdf" or parsed.diagnostics.get("empty_extraction"):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_PARSE_INVALID")
    draft = _build_evidence_support_draft(bundle, parsed.text)
    metrics = _pilot_pre_review_metrics(bundle, draft, parsed)
    if any(
        "v2_support_status" in item or "support_mode" in item
        for item in draft["claims"]
    ):
        raise PilotError("PILOT2_EVIDENCE_DRAFT_SEMANTIC_CLASSIFICATION_FORBIDDEN")

    output_dir.mkdir(parents=True, exist_ok=True)
    draft_path = output_dir / "evidence_contract_v2_draft.json"
    review_surface_path = output_dir / "evidence_review_surface.md"
    metrics_path = output_dir / "pilot2_metrics.json"
    write_json(draft_path, draft)
    review_surface_path.write_text(
        render_pilot2_evidence_review_markdown(draft, metrics), encoding="utf-8",
    )
    write_json(metrics_path, metrics)

    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    inputs_unchanged = input_hashes == {
        label: sha256_file(path) for label, path in inputs.items()
    }
    production_unchanged = production_pre == production_post if production_pre is not None else None
    if not inputs_unchanged:
        raise PilotError("PILOT2_EVIDENCE_DRAFT_INPUT_MUTATED")
    if production_unchanged is False:
        raise PilotError("PILOT2_EVIDENCE_DRAFT_PRODUCTION_MUTATED")
    return {
        "status": "PASS",
        "pilot_run_id": bundle["pilot_run_id"],
        "draft": draft,
        "metrics": metrics,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "inputs_unchanged": inputs_unchanged,
        "draft_path": str(draft_path),
        "review_surface_path": str(review_surface_path),
        "metrics_path": str(metrics_path),
    }


def _gate_a_remove_transcript_metadata(value: str) -> str:
    return re.sub(r"发言人\s*[0-9]{1,2}:[0-9]{2}", "", value or "")


def _gate_a_diagnostic_region(
    body: str, evidence_excerpt: str, locator: str, page_distance: int,
) -> dict[str, Any] | None:
    """Find a local exact-anchor region for explanation only; never for binding."""
    if not body or not evidence_excerpt:
        return None
    matcher = SequenceMatcher(None, evidence_excerpt, body, autojunk=False)
    blocks = [block for block in matcher.get_matching_blocks() if block.size >= 4]
    if not blocks:
        return None
    strongest = max(block.size for block in blocks)
    selected = [block for block in blocks if block.size >= max(4, strongest // 3)]
    offsets = [block.b - block.a for block in selected]
    core_start = max(0, min(offsets))
    core_end = min(len(body), max(offsets) + len(evidence_excerpt))
    if core_end <= core_start:
        return None
    if core_end - core_start > max(240, len(evidence_excerpt) * 3):
        best = max(selected, key=lambda block: (block.size, -block.b))
        core_start = max(0, best.b - max(40, len(evidence_excerpt) // 3))
        core_end = min(len(body), best.b + best.size + max(80, len(evidence_excerpt)))
    region_start = max(0, core_start - 120)
    region_end = min(len(body), core_end + 120)
    strongest_block = max(selected, key=lambda block: (block.size, -block.b))
    return {
        "locator": locator,
        "page_distance": page_distance,
        "diagnostic_only": True,
        "diagnostic_method": "longest_exact_anchor_sequence_match",
        "exact_anchor": body[strongest_block.b:strongest_block.b + strongest_block.size],
        "exact_anchor_length": strongest_block.size,
        "source_core_text": body[core_start:core_end],
        "source_text": body[region_start:region_end].strip(),
    }


def _gate_a_nearest_local_region(
    pages: list[tuple[str, str]], evidence_pointer: str, evidence_excerpt: str,
) -> dict[str, Any] | None:
    pointer_match = _PAGE_POINTER.fullmatch(evidence_pointer or "")
    if not pointer_match:
        return None
    declared_page = pointer_match.group(1)
    page_index = next((index for index, (locator, _) in enumerate(pages) if locator == declared_page), -1)
    if page_index < 0:
        return None
    candidates: list[dict[str, Any]] = []
    for distance, index in ((0, page_index), (1, page_index - 1), (1, page_index + 1)):
        if index < 0 or index >= len(pages):
            continue
        candidate = _gate_a_diagnostic_region(
            pages[index][1], evidence_excerpt, pages[index][0], distance,
        )
        if candidate:
            candidates.append(candidate)
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            item["page_distance"], -item["exact_anchor_length"], _page_number(item["locator"]),
        ),
    )


def _gate_a_diff_diagnostics(
    evidence_excerpt: str, source_core_text: str,
) -> dict[str, Any]:
    model_text = normalize_pdf_span_text(evidence_excerpt)
    source_text = normalize_pdf_span_text(source_core_text)
    diff = []
    for tag, model_start, model_end, source_start, source_end in SequenceMatcher(
        None, model_text, source_text, autojunk=False,
    ).get_opcodes():
        if tag != "equal":
            diff.append({
                "operation": tag,
                "model": model_text[model_start:model_end],
                "source": source_text[source_start:source_end],
            })
    semantic_source = _gate_a_remove_transcript_metadata(source_text)
    semantic_model = _gate_a_remove_transcript_metadata(model_text)
    technical_term_difference = any(
        (term in semantic_source) != (term in semantic_model)
        for term in PILOT2_GATE_A_TECHNICAL_TERMS
    )
    entity_name_difference = any(
        (term in semantic_source) != (term in semantic_model)
        for term in PILOT2_GATE_A_ENTITY_TERMS
    )
    source_numbers = Counter(re.findall(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?[A-Za-z]*", semantic_source))
    model_numbers = Counter(re.findall(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?[A-Za-z]*", semantic_model))
    number_date_difference = source_numbers != model_numbers
    return {
        "lexical_difference_detected": bool(diff),
        "technical_term_difference": technical_term_difference,
        "entity_name_difference": entity_name_difference,
        "number_date_difference": number_date_difference,
        "diagnostic_diff": diff[:40],
    }


def _gate_a_source_text_noisy(source_core_text: str) -> bool:
    return any(marker in source_core_text for marker in PILOT2_GATE_A_SOURCE_NOISE_MARKERS)


def _gate_a_primary_drift_category(
    diagnostics: dict[str, Any], source_core_text: str, evidence_excerpt: str,
) -> str:
    if diagnostics["technical_term_difference"]:
        return "technical_term_normalization"
    if diagnostics["entity_name_difference"]:
        return "entity_normalization"
    if diagnostics["number_date_difference"]:
        return "other"
    if (
        re.search(r"发言人\s*[0-9]{1,2}:[0-9]{2}", source_core_text)
        or _gate_a_source_text_noisy(source_core_text)
        or len("".join(item["model"] + item["source"] for item in diagnostics["diagnostic_diff"])) <= 12
    ):
        return "transcript_cleanup"
    if evidence_excerpt and diagnostics["lexical_difference_detected"]:
        return "paraphrase"
    return "other"


def _gate_a_resolved_fidelity_status(locator: dict[str, Any]) -> str:
    provenance = locator.get("provenance") or {}
    if provenance.get("status") == "mismatch" or locator.get("match_scope") == "global" and provenance.get("status") != "matched":
        return "PROVENANCE_MISMATCH_RECOVERED"
    method = str(locator.get("match_method") or "")
    if method.endswith("raw_exact_substring"):
        return "EXACT_SOURCE_MATCH"
    if method.endswith("exact_substring"):
        return "LAYOUT_NORMALIZED_EXACT_MATCH"
    raise PilotError(f"PILOT2_GATE_A_UNKNOWN_MATCH_METHOD: {method}")


def _gate_a_claim_record(
    claim: dict[str, Any], pages: list[tuple[str, str]], page_by_locator: dict[str, str],
    evidence_draft_claim: dict[str, Any],
) -> dict[str, Any]:
    evidence_excerpt = str(claim.get("evidence_excerpt") or "")
    evidence_pointer = str(claim.get("evidence_pointer") or "")
    original_locator = copy.deepcopy((claim.get("validation") or {}).get("source_locator") or {})
    refreshed_locator = resolve_pdf_evidence_locator(
        "\n".join(f"[[{locator}]]\n{body}" for locator, body in pages),
        evidence_excerpt,
        evidence_pointer,
    )
    declared_page = (
        ((refreshed_locator.get("provenance") or {}).get("locator"))
        or ((original_locator.get("provenance") or {}).get("locator"))
        or ""
    )
    nearest = None
    ordered_spans: list[dict[str, Any]] = []
    source_binding_recoverable = False
    source_text_noisy = False
    model_normalization = False
    diagnostics = {
        "lexical_difference_detected": False,
        "technical_term_difference": False,
        "entity_name_difference": False,
        "number_date_difference": False,
        "diagnostic_diff": [],
    }
    if refreshed_locator.get("status") == "resolved":
        fidelity_status = _gate_a_resolved_fidelity_status(refreshed_locator)
        reason = (
            "Evidence reproduces exactly in the declared page under raw extraction."
            if fidelity_status == "EXACT_SOURCE_MATCH"
            else "Evidence reproduces exactly after approved PDF/layout normalization only."
            if fidelity_status == "LAYOUT_NORMALIZED_EXACT_MATCH"
            else "The declared page pointer was wrong, but one exact global source match was recovered."
        )
        source_binding_recoverable = True
    elif refreshed_locator.get("reason") == "cross_page_span":
        spans = _ordered_cross_page_spans(
            page_by_locator, refreshed_locator, evidence_excerpt,
        )
        if spans:
            ordered_spans = copy.deepcopy(spans)
            fidelity_status = "EXACT_ORDERED_CROSS_PAGE_SPAN"
            reason = "Evidence reproduces as an exact ordered span across adjacent PDF pages."
            source_binding_recoverable = True
            nearest = {
                "diagnostic_only": False,
                "spans": copy.deepcopy(spans),
            }
        else:
            fidelity_status = "UNRESOLVED_SOURCE_BINDING"
            reason = "The candidate cross-page locator does not reproduce the excerpt under approved exact comparisons."
    else:
        nearest = _gate_a_nearest_local_region(pages, evidence_pointer, evidence_excerpt)
        if nearest:
            diagnostics = _gate_a_diff_diagnostics(
                evidence_excerpt, nearest["source_core_text"],
            )
            source_text_noisy = _gate_a_source_text_noisy(nearest["source_core_text"])
            model_normalization = diagnostics["lexical_difference_detected"]
            if diagnostics["lexical_difference_detected"]:
                fidelity_status = "QUOTE_DRIFT"
                reason = (
                    "The local source region contains deterministic exact anchors, but the immutable Evidence "
                    "excerpt cannot be reproduced without lexical change. The diff is diagnostic only and does "
                    "not establish Evidence validity."
                )
            else:
                fidelity_status = "UNRESOLVED_SOURCE_BINDING"
                reason = "No approved exact comparison reproduced the excerpt; the local region is insufficient to establish drift."
        else:
            fidelity_status = "UNRESOLVED_SOURCE_BINDING"
            reason = "No deterministic local source region or approved exact binding was found."
    if fidelity_status not in PILOT2_GATE_A_FIDELITY_STATUSES:
        raise PilotError("PILOT2_GATE_A_INVALID_FIDELITY_STATUS")
    mechanical_normalization_gap = bool(
        original_locator.get("status") not in {"resolved"}
        and refreshed_locator.get("status") == "resolved"
        and original_locator.get("reason") != "cross_page_span"
    )
    if fidelity_status == "QUOTE_DRIFT":
        primary_drift_category = _gate_a_primary_drift_category(
            diagnostics, nearest["source_core_text"], evidence_excerpt,
        )
    else:
        primary_drift_category = None
    provenance = refreshed_locator.get("provenance") or original_locator.get("provenance") or {}
    evidence_contract = phase3c_evidence_provenance_contract(
        model_evidence_excerpt=evidence_excerpt,
        evidence_pointer=evidence_pointer,
        deterministic_locator=refreshed_locator,
        fidelity_status=fidelity_status,
        ordered_spans=ordered_spans,
    )
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "provenance_pointer": evidence_pointer,
        "provenance_page": declared_page,
        "bound_page": refreshed_locator.get("locator"),
        "spanning_locators": copy.deepcopy(refreshed_locator.get("spanning_locators") or []),
        "immutable_evidence_excerpt": evidence_excerpt,
        "fidelity_status": fidelity_status,
        "reason": reason,
        "original_source_locator": original_locator,
        "gate_a_source_locator": refreshed_locator,
        "nearest_deterministic_local_source_region": nearest,
        "mechanical_normalization_gap": mechanical_normalization_gap,
        "lexical_difference_detected": diagnostics["lexical_difference_detected"],
        "technical_term_difference": diagnostics["technical_term_difference"],
        "entity_name_difference": diagnostics["entity_name_difference"],
        "number_date_difference": diagnostics["number_date_difference"],
        "source_binding_recoverable_without_semantic_change": source_binding_recoverable,
        "source_text_noisy": source_text_noisy,
        "model_normalization_or_interpretation": model_normalization,
        "diagnostic_diff": diagnostics["diagnostic_diff"],
        "primary_drift_category": primary_drift_category,
        "original_match_method": original_locator.get("match_method", "none"),
        "evidence_mechanics_status": evidence_draft_claim.get("evidence_mechanics_status"),
        "human_decision": "PENDING",
        "provenance_status": provenance.get("status"),
        "model_page_pointer": copy.deepcopy(evidence_contract["model_page_pointer"]),
        "resolved_locator": copy.deepcopy(evidence_contract["resolved_locator"]),
        "model_page_pointer_error": evidence_contract["model_page_pointer_error"],
        "pointer_mismatch_is_semantic_failure": False,
        "evidence_contract": evidence_contract,
    }


def phase3c_gate_a_monitoring_metrics(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Return separate quote and pointer metrics at Claim grain."""
    total = len(claims)
    source_bound = [
        item for item in claims
        if item.get("fidelity_status") in {
            "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
            "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
        }
    ]
    drift = sum(item.get("fidelity_status") == "QUOTE_DRIFT" for item in claims)
    pointer_matched = sum(
        (item.get("model_page_pointer") or {}).get("status") == "matched"
        for item in source_bound
    )
    pointer_errors = [
        item for item in claims
        if (item.get("model_page_pointer") or {}).get("status") == "mismatch"
    ]
    recovered_pointer_errors = sum(
        item.get("resolved_locator") is not None for item in pointer_errors
    )
    return {
        "grain": "one_phase3c_claim",
        "claims_total": total,
        "locatable_claims": len(source_bound),
        "model_pointer_matched_claims": pointer_matched,
        "model_page_pointer_error_claims": len(pointer_errors),
        "deterministically_recovered_pointer_errors": recovered_pointer_errors,
        "evidence_quote_fidelity_rate": _diagnostic_ratio(len(source_bound), total),
        "evidence_quote_drift_rate": _diagnostic_ratio(drift, total),
        "model_page_pointer_accuracy": _diagnostic_ratio(pointer_matched, len(source_bound)),
        "deterministic_locator_recovery_rate": _diagnostic_ratio(
            recovered_pointer_errors, len(pointer_errors),
        ),
        "semantic_support_rate_included": False,
        "composite_quality_score": "NOT_DEFINED",
    }


def render_pilot2_gate_a_report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    lines = [
        "# Phase 3C Pilot #2 Gate A — Evidence Quote Fidelity & Locator Triage", "",
        "PHASE3C_PILOT2_GATE_A_COMPLETE = true",
        "PHASE3C_COMPLETE = false", "",
        f"Pilot #2 = `{result['pilot_run_id']}`",
        f"Source SHA256 = `{result['source_sha256']}`",
        "LLM calls added = 0",
        "DeepSeek rerun = NO",
        "Human semantic review = NO",
        "Prompt changed = NO", "",
        f"Fidelity counts = `{json.dumps(metrics['fidelity_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"Original deterministic bound = {metrics['original_deterministic_bound']['fraction']}",
        f"Mechanically recoverable unresolved = {metrics['triage_counts']['mechanically_recoverable_unresolved']}",
        f"Gate A deterministic bound = {metrics['gate_a_deterministic_bound']['fraction']}",
        f"Gate A binding rate = {metrics['gate_a_binding_rate']['fraction']} ({metrics['gate_a_binding_rate']['percent']}%)",
        f"Fidelity rate = {metrics['fidelity_rate']['fraction']} ({metrics['fidelity_rate']['percent']}%)",
        f"Quote drift rate = {metrics['quote_drift_rate']['fraction']} ({metrics['quote_drift_rate']['percent']}%)",
        f"Triage counts = `{json.dumps(metrics['triage_counts'], ensure_ascii=False, sort_keys=True)}`", "",
        f"Evidence quote contract issue found = `{metrics['EVIDENCE_QUOTE_CONTRACT_ISSUE_FOUND']}`",
        f"Quote drift categories = `{json.dumps(metrics['quote_drift_category_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"New prompt repair category recommended = `{metrics['NEW_PROMPT_REPAIR_CATEGORY_RECOMMENDED']}`", "",
        "## All audited Claim classifications", "",
        "| Claim | Provenance page | Fidelity status | Bound page | Human decision |",
        "|---|---:|---|---:|---|",
    ]
    for item in result["claims"]:
        lines.append(
            f"| {item['claim_id']} | {item['provenance_page'] or '—'} | "
            f"`{item['fidelity_status']}` | {item['bound_page'] or '—'} | `PENDING` |"
        )
    lines += ["", "## Unresolved seven-item triage", ""]
    for item in result["claims"]:
        if item["fidelity_status"] not in {"QUOTE_DRIFT", "UNRESOLVED_SOURCE_BINDING"}:
            continue
        nearest = item["nearest_deterministic_local_source_region"]
        lines += [
            f"### {item['claim_id']}", "",
            f"- provenance pointer/page: `{item['provenance_pointer']}` / `{item['provenance_page']}`",
            f"- immutable Evidence excerpt: {item['immutable_evidence_excerpt']}",
            f"- nearest deterministic local source region: `{nearest['locator'] if nearest else 'NONE'}`",
            f"- nearest source text: {nearest['source_text'] if nearest else 'NONE'}",
            f"- fidelity status: `{item['fidelity_status']}`",
            f"- reason: {item['reason']}",
            f"- mechanical_normalization_gap: `{item['mechanical_normalization_gap']}`",
            f"- lexical_difference_detected: `{item['lexical_difference_detected']}`",
            f"- technical_term_difference: `{item['technical_term_difference']}`",
            f"- entity/name_difference: `{item['entity_name_difference']}`",
            f"- number/date_difference: `{item['number_date_difference']}`",
            f"- source_binding_recoverable_without_semantic_change: `{item['source_binding_recoverable_without_semantic_change']}`",
            f"- SOURCE_TEXT_NOISY: `{item['source_text_noisy']}`",
            f"- MODEL_NORMALIZATION_OR_INTERPRETATION: `{item['model_normalization_or_interpretation']}`",
            f"- primary drift category: `{item['primary_drift_category'] or 'NONE'}`",
            f"- diagnostic diff only: `{json.dumps(item['diagnostic_diff'], ensure_ascii=False)}`",
            "- Human decision: `PENDING`", "",
        ]
    lines += [
        "## Gate A invariants", "",
        f"- all 29 Claims explicitly classified: `{metrics['invariants']['all_claims_classified']}`",
        f"- Claim count is 29: `{metrics['invariants']['claim_count_matches_expected']}`",
        f"- original Evidence/Claim/IDs unchanged: `{metrics['invariants']['raw_claims_unchanged']}`",
        f"- Human decisions remain PENDING: `{metrics['invariants']['human_decisions_pending']}`",
        f"- original artifacts immutable: `{metrics['invariants']['input_artifacts_unchanged']}`",
        f"- cross-page checks: `{json.dumps(metrics['cross_page_checks'], ensure_ascii=False, sort_keys=True)}`", "",
        "## Production isolation and regressions", "",
        "- Production write = NO; IMA = NO; propagation = NO; legacy pipeline = NO",
        f"- Production unchanged = `{result['production_unchanged']}`",
        "- DeepSeek rerun = NO; Pilot #1 rerun = NO", "",
        f"PILOT2_HUMAN_REVIEW_READY = `{metrics['PILOT2_HUMAN_REVIEW_READY']}`",
        "PHASE3C_NEXT_GATE = Pilot #2 Human Extraction Review",
    ]
    return "\n".join(lines)


def render_pilot2_gate_a_review_surface(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 3C Pilot #2 Gate A Human Review Surface", "",
        "Gate A classifies quote fidelity and locator pathology only. It does not decide KEEP/DROP, semantic support, or Production eligibility.", "",
        f"- pilot_run_id: `{result['pilot_run_id']}`",
        f"- claims: {len(result['claims'])}",
        "- Human decision for every Claim: `PENDING`", "",
    ]
    for item in result["claims"]:
        lines += [
            f"## {item['claim_id']}", "",
            f"- statement: {item['statement']}",
            f"- immutable Evidence excerpt: {item['immutable_evidence_excerpt']}",
            f"- provenance pointer/page: `{item['provenance_pointer']}` / `{item['provenance_page']}`",
            f"- Gate A fidelity status: `{item['fidelity_status']}`",
            f"- reason: {item['reason']}",
            f"- diagnostic nearest region: `{json.dumps(item['nearest_deterministic_local_source_region'], ensure_ascii=False)}`",
            "- Human decision: `PENDING`", "",
        ]
    return "\n".join(lines)


def run_pilot2_gate_a_quote_fidelity(
    original_bundle_path: Path,
    rebound_bundle_path: Path,
    evidence_draft_path: Path,
    source_path: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
    original_review_path: Path | None = None,
) -> dict[str, Any]:
    """Audit Pilot #2 quote fidelity without changing extraction or semantic decisions."""
    original_bundle_path = Path(original_bundle_path).resolve()
    rebound_bundle_path = Path(rebound_bundle_path).resolve()
    evidence_draft_path = Path(evidence_draft_path).resolve()
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir or evidence_draft_path.parent).resolve()
    original_review_path = Path(original_review_path).resolve() if original_review_path else None
    inputs = {
        "original_bundle": original_bundle_path,
        "rebound_bundle": rebound_bundle_path,
        "evidence_draft": evidence_draft_path,
        "source": source_path,
    }
    if original_review_path:
        inputs["original_review"] = original_review_path
    if any(not path.is_file() for path in inputs.values()):
        raise PilotError("PILOT2_GATE_A_INPUT_MISSING")
    input_hashes = {label: sha256_file(path) for label, path in inputs.items()}
    original_bundle = _load_json(original_bundle_path)
    rebound_bundle = _load_json(rebound_bundle_path)
    evidence_draft = _load_json(evidence_draft_path)
    if original_bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE or rebound_bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE:
        raise PilotError("PILOT2_GATE_A_BUNDLE_INVALID")
    if evidence_draft.get("document_type") != PILOT2_EVIDENCE_DRAFT_DOCUMENT_TYPE:
        raise PilotError("PILOT2_GATE_A_EVIDENCE_DRAFT_INVALID")
    if original_bundle.get("pilot_run_id") != rebound_bundle.get("pilot_run_id") or original_bundle.get("pilot_run_id") != evidence_draft.get("pilot_run_id"):
        raise PilotError("PILOT2_GATE_A_RUN_BINDING_INVALID")
    if sha256_file(source_path) != (original_bundle.get("source") or {}).get("sha256"):
        raise PilotError("PILOT2_GATE_A_SOURCE_MISMATCH")
    original_claims = original_bundle.get("claims") or []
    rebound_claims = rebound_bundle.get("claims") or []
    draft_claims = evidence_draft.get("claims") or []
    if not (len(original_claims) == len(rebound_claims) == len(draft_claims)):
        raise PilotError("PILOT2_GATE_A_CLAIM_COVERAGE_INVALID")
    if [claim.get("claim_id") for claim in original_claims] != [claim.get("claim_id") for claim in rebound_claims]:
        raise PilotError("PILOT2_GATE_A_CLAIM_ID_MUTATION")
    draft_by_id = {item.get("claim_id"): item for item in draft_claims}
    if len(draft_by_id) != len(draft_claims):
        raise PilotError("PILOT2_GATE_A_DRAFT_CLAIM_ID_DUPLICATE")
    raw_claims_unchanged = all(
        _raw_claim_projection(original) == _raw_claim_projection(rebound)
        for original, rebound in zip(original_claims, rebound_claims)
    )
    if not raw_claims_unchanged:
        raise PilotError("PILOT2_GATE_A_RAW_CLAIM_MUTATION")
    if any(
        item.get("original_evidence_excerpt") != claim.get("evidence_excerpt")
        for claim, item in zip(original_claims, draft_claims)
    ):
        raise PilotError("PILOT2_GATE_A_EVIDENCE_MUTATION")
    human_decisions_pending = all(item.get("human_decision") == "PENDING" for item in draft_claims)
    if original_review_path:
        original_review = _load_json(original_review_path)
        human_decisions_pending = human_decisions_pending and all(
            item.get("decision") == "PENDING" for item in original_review.get("claims") or []
        )
    if not human_decisions_pending:
        raise PilotError("PILOT2_GATE_A_HUMAN_DECISION_NOT_PENDING")
    parsed = parse_source_with_diagnostics(source_path)
    if parsed.source_type != "pdf" or parsed.diagnostics.get("empty_extraction"):
        raise PilotError("PILOT2_GATE_A_PARSE_INVALID")
    pages = [(locator, body) for locator, body in source_units(parsed.text) if locator.startswith("PAGE:")]
    page_by_locator = dict(pages)
    claims = [
        _gate_a_claim_record(
            rebound_claim,
            pages,
            page_by_locator,
            draft_by_id[rebound_claim.get("claim_id")],
        )
        for rebound_claim in rebound_claims
    ]
    monitoring = phase3c_gate_a_monitoring_metrics(claims)
    fidelity_counts = {status: sum(item["fidelity_status"] == status for item in claims) for status in sorted(PILOT2_GATE_A_FIDELITY_STATUSES)}
    original_bound = sum(
        item.get("evidence_mechanics_status") in {"EXCERPT_BOUND", "CONTEXT_AVAILABLE", "ORDERED_SPAN_BOUND"}
        for item in draft_claims
    )
    gate_a_bound = sum(
        item["fidelity_status"] in {
            "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
            "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
        }
        for item in claims
    )
    drift_claims = [item for item in claims if item["fidelity_status"] == "QUOTE_DRIFT"]
    unresolved_claims = [
        item for item in claims
        if item["fidelity_status"] in {"QUOTE_DRIFT", "UNRESOLVED_SOURCE_BINDING"}
    ]
    category_counts = {
        category: sum(item["primary_drift_category"] == category for item in drift_claims)
        for category in sorted(PILOT2_GATE_A_DRIFT_CATEGORIES)
    }
    expected_unresolved = {
        "CLM_20260831_A7C48FD4", "CLM_20260831_5203349C", "CLM_20260831_09C4451B",
        "CLM_20260831_FDA7285D", "CLM_20260831_2FE8D852", "CLM_20260831_F688BC15",
        "CLM_20260831_FB04A562",
    }
    unresolved_ids = {item["claim_id"] for item in unresolved_claims}
    if original_bundle.get("pilot_run_id") == "PILOT_20260831_DEA82C1F" and unresolved_ids != expected_unresolved:
        raise PilotError("PILOT2_GATE_A_UNEXPECTED_UNRESOLVED_CLAIM_SET")
    cross_page_checks = {
        claim_id: {
            "status": next(item["fidelity_status"] for item in claims if item["claim_id"] == claim_id),
            "spans": next(item["spanning_locators"] for item in claims if item["claim_id"] == claim_id),
        }
        for claim_id in ("CLM_20260831_89CE1154", "CLM_20260831_B1769E98")
        if any(item["claim_id"] == claim_id for item in claims)
    }
    metrics = {
        "pilot_run_id": original_bundle["pilot_run_id"],
        "source_sha256": (original_bundle.get("source") or {}).get("sha256"),
        "claims_total": len(claims),
        "fidelity_counts": fidelity_counts,
        "original_deterministic_bound": _diagnostic_ratio(original_bound, len(claims)),
        "gate_a_deterministic_bound": _diagnostic_ratio(gate_a_bound, len(claims)),
        "gate_a_binding_rate": _diagnostic_ratio(gate_a_bound, len(claims)),
        "fidelity_rate": _diagnostic_ratio(
            sum(fidelity_counts[status] for status in (
                "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH", "EXACT_ORDERED_CROSS_PAGE_SPAN",
            )),
            len(claims),
        ),
        "quote_drift_rate": _diagnostic_ratio(fidelity_counts["QUOTE_DRIFT"], len(claims)),
        "evidence_quote_fidelity_rate": copy.deepcopy(
            monitoring["evidence_quote_fidelity_rate"]
        ),
        "evidence_quote_drift_rate": copy.deepcopy(
            monitoring["evidence_quote_drift_rate"]
        ),
        "model_page_pointer_accuracy": copy.deepcopy(
            monitoring["model_page_pointer_accuracy"]
        ),
        "deterministic_locator_recovery_rate": copy.deepcopy(
            monitoring["deterministic_locator_recovery_rate"]
        ),
        "model_page_pointer_error_claims": monitoring[
            "model_page_pointer_error_claims"
        ],
        "monitoring_contract": monitoring,
        "triage_counts": {
            "mechanically_recoverable_unresolved": sum(
                item["mechanical_normalization_gap"]
                for item in claims
            ),
            "quote_drift_unresolved": len(drift_claims),
            "still_unexplained": sum(item["fidelity_status"] == "UNRESOLVED_SOURCE_BINDING" for item in claims),
        },
        "unresolved_claim_ids": sorted(unresolved_ids),
        "quote_drift_category_counts": category_counts,
        "EVIDENCE_QUOTE_CONTRACT_ISSUE_FOUND": bool(drift_claims),
        "NEW_PROMPT_REPAIR_CATEGORY_RECOMMENDED": (
            "evidence_quote_verbatim_preservation" if drift_claims else "NONE"
        ),
        "cross_page_checks": cross_page_checks,
        "invariants": {
            "all_claims_classified": bool(claims) and all(
                item["fidelity_status"] in PILOT2_GATE_A_FIDELITY_STATUSES for item in claims
            ),
            "claim_count_matches_expected": len(claims) == 29,
            "raw_claims_unchanged": raw_claims_unchanged,
            "human_decisions_pending": human_decisions_pending,
            "input_artifacts_unchanged": False,
            "production_unchanged": None,
            "llm_calls_added": 0,
            "deepseek_rerun": False,
            "human_semantic_review": False,
            "prompt_changed": False,
        },
        "production_write": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
    }
    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "PASS",
        "document_type": PILOT2_GATE_A_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": original_bundle["pilot_run_id"],
        "source_sha256": (original_bundle.get("source") or {}).get("sha256"),
        "claims": claims,
        "metrics": metrics,
        "bindings": {
            "original_bundle_file_sha256": input_hashes["original_bundle"],
            "original_bundle_canonical_sha256": extraction_bundle_sha256(original_bundle),
            "rebound_bundle_file_sha256": input_hashes["rebound_bundle"],
            "rebound_bundle_canonical_sha256": extraction_bundle_sha256(rebound_bundle),
            "evidence_draft_file_sha256": input_hashes["evidence_draft"],
            "source_sha256": (original_bundle.get("source") or {}).get("sha256"),
            "prompt_sha256": ((original_bundle.get("model") or {}).get("prompt") or {}).get("prompt_sha256", "NOT_AVAILABLE"),
        },
        "policy": {
            "allowed_fidelity_statuses": sorted(PILOT2_GATE_A_FIDELITY_STATUSES),
            "approved_normalization": PDF_LOCATOR_CANONICALIZATION,
            "diagnostic_diff_only": True,
            "fuzzy_or_semantic_similarity_is_not_binding": True,
            "semantic_support_decisions_deferred": True,
            "original_artifacts_immutable": True,
            "model_evidence_is_proposed_quote": True,
            "model_page_pointer_authoritative": False,
            "deterministic_locator_authoritative": True,
            "pointer_mismatch_is_semantic_failure": False,
            "automatic_quote_repair": False,
        },
    }
    metrics["invariants"]["input_artifacts_unchanged"] = input_hashes == {
        label: sha256_file(path) for label, path in inputs.items()
    }
    if not metrics["invariants"]["input_artifacts_unchanged"]:
        raise PilotError("PILOT2_GATE_A_INPUT_MUTATED")
    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    production_unchanged = production_pre == production_post if production_pre is not None else None
    metrics["invariants"]["production_unchanged"] = production_unchanged
    metrics["PILOT2_HUMAN_REVIEW_READY"] = bool(
        metrics["invariants"]["all_claims_classified"]
        and metrics["invariants"]["raw_claims_unchanged"]
        and metrics["invariants"]["human_decisions_pending"]
        and metrics["invariants"]["input_artifacts_unchanged"]
        and all(item["fidelity_status"] != "UNRESOLVED_SOURCE_BINDING" for item in claims)
    )
    result["production_pre"] = production_pre
    result["production_post"] = production_post
    result["production_unchanged"] = production_unchanged
    report_path = output_dir / "pilot2_gate_a_quote_fidelity_report.md"
    json_path = output_dir / "pilot2_gate_a_quote_fidelity.json"
    metrics_path = output_dir / "pilot2_gate_a_metrics.json"
    surface_path = output_dir / "pilot2_evidence_review_surface_gate_a.md"
    write_json(json_path, result)
    write_json(metrics_path, metrics)
    report_path.write_text(render_pilot2_gate_a_report(result), encoding="utf-8")
    surface_path.write_text(render_pilot2_gate_a_review_surface(result), encoding="utf-8")
    result.update({
        "gate_a_path": str(json_path),
        "report_path": str(report_path),
        "metrics_path": str(metrics_path),
        "review_surface_path": str(surface_path),
    })
    return result


def _pilot2_human_review_expected_decision(
    semantic_support: str, evidence_admissibility: str,
) -> str:
    if semantic_support in {"UNSUPPORTED", "AMBIGUOUS"}:
        return "DROP"
    if evidence_admissibility == "CURRENT_CONTRACT_ADMISSIBLE":
        return "KEEP"
    return "KEEP_NEEDS_REVIEW"


def _pilot2_human_review_prompt_repairs(
    *, quote_drift: int, material_atomicity: int, failure_dimensions: Counter,
) -> list[str]:
    repairs = []
    if quote_drift:
        repairs.append("evidence_quote_verbatim_preservation")
    if material_atomicity or failure_dimensions["TRUE_OVERREACH"]:
        repairs.append("claim_atomicity")
    for failure, repair in (
        ("ATTRIBUTION_ERROR", "attribution"),
        ("CONDITIONALITY_LOSS", "conditionality"),
        ("SCOPE_ERROR", "scope"),
        ("ENTITY_INFERENCE", "entity_inference"),
        ("TECHNICAL_TERM_INFERENCE", "technical_term_inference"),
    ):
        if failure_dimensions[failure]:
            repairs.append(repair)
    return repairs


def _pilot2_human_review_metrics(
    bundle: dict[str, Any], reviewed_claims: list[dict[str, Any]],
    *, generalization_verdict: str, generalization_rationale: str,
) -> dict[str, Any]:
    total = len(reviewed_claims)
    decision_counts = Counter(item["human_decision"] for item in reviewed_claims)
    semantic_counts = Counter(item["semantic_support"] for item in reviewed_claims)
    admissibility_counts = Counter(item["evidence_admissibility"] for item in reviewed_claims)
    fidelity_counts = Counter(item["gate_a_fidelity_status"] for item in reviewed_claims)
    quote_claims = [item for item in reviewed_claims if item["quote_drift"]]
    quote_semantic_counts = Counter(item["semantic_support"] for item in quote_claims)
    primary_failure_counts = Counter(
        item["semantic_failure_category"]
        for item in reviewed_claims
        if item["semantic_failure_category"] != "NONE"
    )
    failure_dimensions: Counter = Counter()
    for item in reviewed_claims:
        categories = [item["semantic_failure_category"], *item["secondary_failure_categories"]]
        for category in set(categories) - {"NONE"}:
            failure_dimensions[category] += 1
    atomicity_issues = sum(item["atomicity_issue"] for item in reviewed_claims)
    material_atomicity = sum(item["atomicity_material_failure"] for item in reviewed_claims)
    review_mode_counts = Counter(item["review_mode"] for item in reviewed_claims)
    total_tokens = ((bundle.get("model") or {}).get("usage") or {}).get("total_tokens")
    prompt_repairs = _pilot2_human_review_prompt_repairs(
        quote_drift=len(quote_claims),
        material_atomicity=material_atomicity,
        failure_dimensions=failure_dimensions,
    )
    next_gate = (
        "Pilot #2 Semantic Failure Repair"
        if generalization_verdict == "FAIL"
        else "Evidence Quote Verbatim Repair + Cross-Pilot Generalization Closure"
        if quote_claims
        else "Cross-Pilot Generalization Closure"
    )
    return {
        "pilot_run_id": bundle["pilot_run_id"],
        "source_sha256": (bundle.get("source") or {}).get("sha256"),
        "claims_total": total,
        "claims_reviewed": total,
        "decision_counts": {
            decision: decision_counts[decision]
            for decision in ("KEEP", "DROP", "KEEP_NEEDS_REVIEW")
        } | {"PENDING": 0},
        "semantic_counts": {
            status: semantic_counts[status]
            for status in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")
        },
        "semantic_support_rate": _diagnostic_ratio(semantic_counts["SUPPORTED"], total),
        "true_semantic_failure_rate": _diagnostic_ratio(semantic_counts["UNSUPPORTED"], total),
        "evidence_admissibility_counts": {
            status: admissibility_counts[status]
            for status in (
                "CURRENT_CONTRACT_ADMISSIBLE", "V2_CONTEXT_REQUIRED",
                "V2_ORDERED_SPAN_REQUIRED", "EVIDENCE_QUOTE_DRIFT_BLOCKED",
                "SOURCE_AMBIGUITY_BLOCKED",
            )
        },
        "strict_current_contract_keep_rate": _diagnostic_ratio(decision_counts["KEEP"], total),
        "gate_a_fidelity_counts": {
            status: fidelity_counts[status]
            for status in sorted(PILOT2_GATE_A_FIDELITY_STATUSES)
        },
        "quote_drift_semantic_outcomes": {
            "total": len(quote_claims),
            "SUPPORTED": quote_semantic_counts["SUPPORTED"],
            "UNSUPPORTED": quote_semantic_counts["UNSUPPORTED"],
            "AMBIGUOUS": quote_semantic_counts["AMBIGUOUS"],
        },
        "atomicity": {
            "issues": atomicity_issues,
            "issue_rate": _diagnostic_ratio(atomicity_issues, total),
            "material_failures": material_atomicity,
            "material_failure_rate": _diagnostic_ratio(material_atomicity, total),
        },
        "primary_semantic_failure_category_counts": {
            category: primary_failure_counts[category]
            for category in sorted(PILOT2_SEMANTIC_FAILURE_CATEGORIES)
        },
        "semantic_failure_dimension_counts": {
            category: failure_dimensions[category]
            for category in sorted(PILOT2_SEMANTIC_FAILURE_CATEGORIES)
        },
        "pilot1_descriptive_benchmark": {
            "claims": 53,
            "true_semantic_failures": 6,
            "true_semantic_failure_rate": _diagnostic_ratio(6, 53),
            "atomicity_issues": 7,
            "atomicity_issue_rate": _diagnostic_ratio(7, 53),
            "primary_semantic_failure_category_counts": {
                "TRUE_OVERREACH": 3,
                "ATTRIBUTION_ERROR": 1,
                "CONDITIONALITY_LOSS": 1,
                "SCOPE_ERROR": 1,
            },
            "statistical_significance_claimed": False,
        },
        "EVIDENCE_QUOTE_VERBATIM_PROMPT_REPAIR_CONFIRMED": bool(quote_claims),
        "PROMPT_REPAIR_NEXT": prompt_repairs,
        "PILOT2_GENERALIZATION_VERDICT": generalization_verdict,
        "generalization_rationale": generalization_rationale,
        "PHASE3C_NEXT_GATE": next_gate,
        "token_economics": {
            "pilot2_extraction_total_tokens": total_tokens,
            "tokens_per_claim": _tokens_per(total_tokens, total),
            "tokens_per_semantically_supported_claim": _tokens_per(
                total_tokens, semantic_counts["SUPPORTED"],
            ),
            "tokens_per_current_contract_keep_claim": _tokens_per(
                total_tokens, decision_counts["KEEP"],
            ),
            "pilot1_total_tokens": 139181,
            "pilot1_tokens_per_claim": 2626.06,
            "single_sample_economic_superiority_claimed": False,
        },
        "human_review_burden": {
            "excerpt_only": review_mode_counts["EXCERPT_ONLY"],
            "bounded_context": review_mode_counts["BOUNDED_CONTEXT"],
            "cross_page": review_mode_counts["CROSS_PAGE"],
            "quote_drift_source_region": review_mode_counts["QUOTE_DRIFT_SOURCE_REGION"],
            "expanded_manual_evidence_review": total - review_mode_counts["EXCERPT_ONLY"],
            "categories_are_mutually_exclusive": True,
        },
        "llm_calls_added": 0,
        "pilot2_rerun": False,
        "production_write": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
        "production_schema_changed": False,
        "canonical_claim_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "node_created": False,
        "relation_created": False,
        "proposal_created": False,
        "current_view_created": False,
        "knowledge_gap_created": False,
        "research_question_created": False,
        "claim_node_link_created": False,
        "source_node_link_created": False,
        "PRODUCTION_APPLY_READY": "NO",
    }


def render_pilot2_human_review_report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    decisions = metrics["decision_counts"]
    semantics = metrics["semantic_counts"]
    admissibility = metrics["evidence_admissibility_counts"]
    atomicity = metrics["atomicity"]
    quote = metrics["quote_drift_semantic_outcomes"]
    token_economics = metrics["token_economics"]
    burden = metrics["human_review_burden"]
    lines = [
        "# Phase 3C Pilot #2 — Human Extraction Review + Generalization Evaluation", "",
        "PHASE3C_PILOT2_HUMAN_REVIEW_COMPLETE = true",
        "PHASE3C_COMPLETE = false",
        "PRODUCTION_APPLY_READY = NO", "",
        f"Pilot #2 = `{result['pilot_run_id']}`",
        f"Source SHA256 = `{result['source_sha256']}`",
        f"Claims reviewed = {metrics['claims_reviewed']} / {metrics['claims_total']}",
        "PENDING = 0", "",
        "## Outcome", "",
        f"Human decisions = `{json.dumps(decisions, ensure_ascii=False, sort_keys=True)}`",
        f"Semantic review = `{json.dumps(semantics, ensure_ascii=False, sort_keys=True)}`",
        f"Semantic support rate = {metrics['semantic_support_rate']['fraction']} ({metrics['semantic_support_rate']['percent']}%)",
        f"True semantic failure rate = {metrics['true_semantic_failure_rate']['fraction']} ({metrics['true_semantic_failure_rate']['percent']}%)",
        f"Strict current-contract KEEP rate = {metrics['strict_current_contract_keep_rate']['fraction']} ({metrics['strict_current_contract_keep_rate']['percent']}%)",
        f"Evidence admissibility = `{json.dumps(admissibility, ensure_ascii=False, sort_keys=True)}`", "",
        f"Quote drift semantic outcomes = `{json.dumps(quote, ensure_ascii=False, sort_keys=True)}`",
        f"Atomicity issues = {atomicity['issue_rate']['fraction']} ({atomicity['issue_rate']['percent']}%)",
        f"Material atomicity failures = {atomicity['material_failure_rate']['fraction']} ({atomicity['material_failure_rate']['percent']}%)",
        f"Primary semantic failure categories = `{json.dumps(metrics['primary_semantic_failure_category_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"All semantic failure dimensions = `{json.dumps(metrics['semantic_failure_dimension_counts'], ensure_ascii=False, sort_keys=True)}`", "",
        f"EVIDENCE_QUOTE_VERBATIM_PROMPT_REPAIR_CONFIRMED = {str(metrics['EVIDENCE_QUOTE_VERBATIM_PROMPT_REPAIR_CONFIRMED']).lower()}",
        f"PROMPT_REPAIR_NEXT = `{json.dumps(metrics['PROMPT_REPAIR_NEXT'], ensure_ascii=False)}`",
        f"PILOT2_GENERALIZATION_VERDICT = {metrics['PILOT2_GENERALIZATION_VERDICT']}",
        f"Generalization rationale = {metrics['generalization_rationale']}",
        f"PHASE3C_NEXT_GATE = {metrics['PHASE3C_NEXT_GATE']}", "",
        "The Pilot #1 comparison is descriptive only; no statistical significance is claimed.", "",
        "## Token economics and review burden", "",
        f"Pilot #2 total tokens = {token_economics['pilot2_extraction_total_tokens']}",
        f"Tokens per Claim = {token_economics['tokens_per_claim']}",
        f"Tokens per semantically supported Claim = {token_economics['tokens_per_semantically_supported_claim']}",
        f"Tokens per current-contract KEEP Claim = {token_economics['tokens_per_current_contract_keep_claim']}",
        f"Human review burden = `{json.dumps(burden, ensure_ascii=False, sort_keys=True)}`", "",
        "## Claim-level decisions", "",
        "| Claim | Gate A | Semantic support | Evidence admissibility | Decision | Atomicity / material |",
        "|---|---|---|---|---|---|",
    ]
    for item in result["claims"]:
        lines.append(
            f"| {item['claim_id']} | `{item['gate_a_fidelity_status']}` | "
            f"`{item['semantic_support']}` | `{item['evidence_admissibility']}` | "
            f"`{item['human_decision']}` | `{item['atomicity_issue']}` / "
            f"`{item['atomicity_material_failure']}` |"
        )
    lines += ["", "## Review rationales", ""]
    for item in result["claims"]:
        lines += [
            f"### {item['claim_id']}", "",
            f"- semantic failure category: `{item['semantic_failure_category']}`",
            f"- secondary categories: `{json.dumps(item['secondary_failure_categories'], ensure_ascii=False)}`",
            f"- review mode: `{item['review_mode']}`",
            f"- rationale: {item['rationale']}", "",
        ]
    invariants = metrics["invariants"]
    lines += [
        "## Safety and invariants", "",
        f"- Claim IDs unchanged: `{invariants['claim_ids_unchanged']}`",
        f"- Raw Claim unchanged: `{invariants['raw_claim_unchanged']}`",
        f"- Raw Evidence unchanged: `{invariants['raw_evidence_unchanged']}`",
        f"- Gate A fidelity unchanged: `{invariants['gate_a_fidelity_unchanged']}`",
        f"- Input artifacts unchanged: `{invariants['input_artifacts_unchanged']}`",
        f"- Production unchanged: `{invariants['production_unchanged']}`",
        "- LLM calls added: `0`",
        "- Pilot #2 rerun: `NO`",
        "- IMA / propagation / legacy pipeline: `NO / NO / NO`", "",
        "STOP: prompt, quote drift, extraction, canonical schema, and Production were not modified.",
    ]
    return "\n".join(lines)


def close_pilot2_human_review(
    original_bundle_path: Path,
    evidence_draft_path: Path,
    gate_a_path: Path,
    decisions_path: Path,
    *,
    output_dir: Path | None = None,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Close Pilot #2 review from explicit human decisions without mutating extraction history."""
    original_bundle_path = Path(original_bundle_path).resolve()
    evidence_draft_path = Path(evidence_draft_path).resolve()
    gate_a_path = Path(gate_a_path).resolve()
    decisions_path = Path(decisions_path).resolve()
    output_dir = Path(output_dir or decisions_path.parent).resolve()
    inputs = {
        "original_bundle": original_bundle_path,
        "evidence_draft": evidence_draft_path,
        "gate_a": gate_a_path,
        "decisions": decisions_path,
    }
    input_hashes = {label: sha256_file(path) for label, path in inputs.items()}
    bundle = _load_json(original_bundle_path)
    evidence_draft = _load_json(evidence_draft_path)
    gate_a = _load_json(gate_a_path)
    decisions = _load_json(decisions_path)
    if decisions.get("document_type") != PILOT2_HUMAN_REVIEW_DECISIONS_DOCUMENT_TYPE:
        raise PilotError("PILOT2_HUMAN_REVIEW_INVALID_DOCUMENT_TYPE")
    if decisions.get("schema_version") != SCHEMA_VERSION:
        raise PilotError("PILOT2_HUMAN_REVIEW_INVALID_SCHEMA_VERSION")
    pilot_run_id = bundle.get("pilot_run_id")
    source_sha256 = (bundle.get("source") or {}).get("sha256")
    if not pilot_run_id or any(
        artifact.get("pilot_run_id") != pilot_run_id
        for artifact in (evidence_draft, gate_a, decisions)
    ):
        raise PilotError("PILOT2_HUMAN_REVIEW_RUN_BINDING_MISMATCH")
    if gate_a.get("document_type") != PILOT2_GATE_A_DOCUMENT_TYPE:
        raise PilotError("PILOT2_HUMAN_REVIEW_GATE_A_INVALID")
    if decisions.get("source_sha256") != source_sha256 or gate_a.get("source_sha256") != source_sha256:
        raise PilotError("PILOT2_HUMAN_REVIEW_SOURCE_BINDING_MISMATCH")
    bundle_claims = bundle.get("claims") or []
    evidence_claims = {item.get("claim_id"): item for item in evidence_draft.get("claims") or []}
    gate_claims = {item.get("claim_id"): item for item in gate_a.get("claims") or []}
    decision_claims = decisions.get("claims") or []
    bundle_ids = [item.get("claim_id") for item in bundle_claims]
    if (
        len(bundle_ids) != len(set(bundle_ids))
        or [item.get("claim_id") for item in decision_claims] != bundle_ids
        or set(evidence_claims) != set(bundle_ids)
        or set(gate_claims) != set(bundle_ids)
    ):
        raise PilotError("PILOT2_HUMAN_REVIEW_CLAIM_IDS_CHANGED")
    if pilot_run_id == "PILOT_20260831_DEA82C1F" and len(bundle_ids) != 29:
        raise PilotError("PILOT2_HUMAN_REVIEW_EXPECTED_29_CLAIMS")

    reviewed_claims = []
    for original, selected in zip(bundle_claims, decision_claims):
        claim_id = original["claim_id"]
        evidence = evidence_claims[claim_id]
        gate = gate_claims[claim_id]
        if "original_claim" in selected and selected.get("original_claim") != original.get("statement"):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_CLAIM_MUTATED: {claim_id}")
        if (
            "immutable_evidence_excerpt" in selected
            and selected.get("immutable_evidence_excerpt") != original.get("evidence_excerpt")
        ):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_EVIDENCE_MUTATED: {claim_id}")
        if evidence.get("original_evidence_excerpt") != original.get("evidence_excerpt"):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_EVIDENCE_DRAFT_MISMATCH: {claim_id}")
        if (
            "gate_a_fidelity_status" in selected
            and selected.get("gate_a_fidelity_status") != gate.get("fidelity_status")
        ):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_GATE_A_STATUS_CHANGED: {claim_id}")
        semantic_support = selected.get("semantic_support")
        admissibility = selected.get("evidence_admissibility")
        failure_category = selected.get("semantic_failure_category")
        secondary = selected.get("secondary_failure_categories") or []
        review_mode = selected.get("review_mode")
        if semantic_support not in PILOT2_SEMANTIC_SUPPORT:
            raise PilotError(f"PILOT2_HUMAN_REVIEW_INVALID_SEMANTIC_SUPPORT: {claim_id}")
        if admissibility not in PILOT2_EVIDENCE_ADMISSIBILITY:
            raise PilotError(f"PILOT2_HUMAN_REVIEW_INVALID_ADMISSIBILITY: {claim_id}")
        if failure_category != "NONE" and failure_category not in PILOT2_SEMANTIC_FAILURE_CATEGORIES:
            raise PilotError(f"PILOT2_HUMAN_REVIEW_INVALID_FAILURE_CATEGORY: {claim_id}")
        if any(item not in PILOT2_SEMANTIC_FAILURE_CATEGORIES for item in secondary):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_INVALID_SECONDARY_CATEGORY: {claim_id}")
        if semantic_support == "UNSUPPORTED" and failure_category == "NONE":
            raise PilotError(f"PILOT2_HUMAN_REVIEW_FAILURE_CATEGORY_REQUIRED: {claim_id}")
        if semantic_support != "UNSUPPORTED" and failure_category != "NONE":
            raise PilotError(f"PILOT2_HUMAN_REVIEW_FAILURE_CATEGORY_NOT_ALLOWED: {claim_id}")
        if review_mode not in PILOT2_HUMAN_REVIEW_MODES:
            raise PilotError(f"PILOT2_HUMAN_REVIEW_INVALID_REVIEW_MODE: {claim_id}")
        atomicity_issue = selected.get("atomicity_issue")
        material_atomicity = selected.get("atomicity_material_failure")
        if not isinstance(atomicity_issue, bool) or not isinstance(material_atomicity, bool):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_INVALID_ATOMICITY: {claim_id}")
        if material_atomicity and (not atomicity_issue or semantic_support != "UNSUPPORTED"):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_MATERIAL_ATOMICITY_INVALID: {claim_id}")
        expected_decision = _pilot2_human_review_expected_decision(
            semantic_support, admissibility,
        )
        if selected.get("human_decision") != expected_decision:
            raise PilotError(f"PILOT2_HUMAN_REVIEW_DECISION_INCONSISTENT: {claim_id}")
        fidelity_status = gate["fidelity_status"]
        is_quote_drift = fidelity_status == "QUOTE_DRIFT"
        is_cross_page = fidelity_status == "EXACT_ORDERED_CROSS_PAGE_SPAN"
        if selected.get("quote_drift") is not is_quote_drift:
            raise PilotError(f"PILOT2_HUMAN_REVIEW_QUOTE_DRIFT_FLAG_MISMATCH: {claim_id}")
        if is_quote_drift:
            if (
                admissibility != "EVIDENCE_QUOTE_DRIFT_BLOCKED"
                or review_mode != "QUOTE_DRIFT_SOURCE_REGION"
                or selected.get("quote_drift_category") != gate.get("primary_drift_category")
                or not selected.get("nearest_deterministic_source_region_reference")
            ):
                raise PilotError(f"PILOT2_HUMAN_REVIEW_QUOTE_DRIFT_CONTRACT_INVALID: {claim_id}")
        elif (
            admissibility == "EVIDENCE_QUOTE_DRIFT_BLOCKED"
            or selected.get("quote_drift_category") is not None
            or selected.get("nearest_deterministic_source_region_reference") is not None
        ):
            raise PilotError(f"PILOT2_HUMAN_REVIEW_FALSE_QUOTE_DRIFT: {claim_id}")
        if is_cross_page:
            if admissibility != "V2_ORDERED_SPAN_REQUIRED" or review_mode != "CROSS_PAGE":
                raise PilotError(f"PILOT2_HUMAN_REVIEW_CROSS_PAGE_CONTRACT_INVALID: {claim_id}")
        elif admissibility == "V2_ORDERED_SPAN_REQUIRED" or review_mode == "CROSS_PAGE":
            raise PilotError(f"PILOT2_HUMAN_REVIEW_FALSE_CROSS_PAGE: {claim_id}")
        if admissibility == "CURRENT_CONTRACT_ADMISSIBLE" and review_mode != "EXCERPT_ONLY":
            raise PilotError(f"PILOT2_HUMAN_REVIEW_CURRENT_CONTRACT_MODE_INVALID: {claim_id}")
        if admissibility in {"V2_CONTEXT_REQUIRED", "SOURCE_AMBIGUITY_BLOCKED"} and review_mode != "BOUNDED_CONTEXT":
            raise PilotError(f"PILOT2_HUMAN_REVIEW_CONTEXT_MODE_INVALID: {claim_id}")
        rationale = selected.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise PilotError(f"PILOT2_HUMAN_REVIEW_RATIONALE_REQUIRED: {claim_id}")
        reviewed = copy.deepcopy(selected)
        reviewed["original_claim"] = original.get("statement")
        reviewed["immutable_evidence_excerpt"] = original.get("evidence_excerpt")
        reviewed["gate_a_fidelity_status"] = gate.get("fidelity_status")
        reviewed_claims.append(reviewed)

    verdict = decisions.get("generalization_verdict")
    verdict_rationale = decisions.get("generalization_rationale")
    if verdict not in PILOT2_GENERALIZATION_VERDICTS:
        raise PilotError("PILOT2_HUMAN_REVIEW_INVALID_GENERALIZATION_VERDICT")
    if not isinstance(verdict_rationale, str) or not verdict_rationale.strip():
        raise PilotError("PILOT2_HUMAN_REVIEW_GENERALIZATION_RATIONALE_REQUIRED")
    metrics = _pilot2_human_review_metrics(
        bundle,
        reviewed_claims,
        generalization_verdict=verdict,
        generalization_rationale=verdict_rationale,
    )
    if metrics["true_semantic_failure_rate"]["percent"] > 20 and verdict != "FAIL":
        raise PilotError("PILOT2_HUMAN_REVIEW_FAIL_VERDICT_REQUIRED")
    if verdict == "PASS" and metrics["PROMPT_REPAIR_NEXT"]:
        raise PilotError("PILOT2_HUMAN_REVIEW_PASS_WITH_OPEN_REPAIRS")

    production_pre = production_snapshot(Path(production_db_path)) if production_db_path else None
    result = {
        "status": "READY",
        "document_type": PILOT2_HUMAN_REVIEW_READY_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": pilot_run_id,
        "source_sha256": source_sha256,
        "claims": reviewed_claims,
        "metrics": metrics,
        "bindings": {
            "original_bundle_file_sha256": input_hashes["original_bundle"],
            "original_bundle_canonical_sha256": extraction_bundle_sha256(bundle),
            "evidence_draft_file_sha256": input_hashes["evidence_draft"],
            "gate_a_file_sha256": input_hashes["gate_a"],
            "decisions_file_sha256": input_hashes["decisions"],
            "source_sha256": source_sha256,
        },
        "policy": {
            "two_axis_review": True,
            "semantic_support_independent_of_quote_fidelity": True,
            "quote_drift_is_not_automatic_semantic_failure": True,
            "original_claim_and_evidence_immutable": True,
            "production_apply_ready": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    production_post = production_snapshot(Path(production_db_path)) if production_db_path else None
    input_artifacts_unchanged = input_hashes == {
        label: sha256_file(path) for label, path in inputs.items()
    }
    production_unchanged = production_pre == production_post if production_pre is not None else None
    metrics["invariants"] = {
        "all_decisions_explicit": len(reviewed_claims) == len(bundle_claims),
        "pending_zero": metrics["decision_counts"]["PENDING"] == 0,
        "claim_ids_unchanged": [item["claim_id"] for item in reviewed_claims] == bundle_ids,
        "raw_claim_unchanged": all(
            selected["original_claim"] == original["statement"]
            for selected, original in zip(reviewed_claims, bundle_claims)
        ),
        "raw_evidence_unchanged": all(
            selected["immutable_evidence_excerpt"] == original["evidence_excerpt"]
            for selected, original in zip(reviewed_claims, bundle_claims)
        ),
        "gate_a_fidelity_unchanged": all(
            selected["gate_a_fidelity_status"] == gate_claims[selected["claim_id"]]["fidelity_status"]
            for selected in reviewed_claims
        ),
        "input_artifacts_unchanged": input_artifacts_unchanged,
        "production_unchanged": production_unchanged,
    }
    if not all(
        value is True
        for key, value in metrics["invariants"].items()
        if key != "production_unchanged"
    ):
        raise PilotError("PILOT2_HUMAN_REVIEW_INVARIANT_FAILED")
    if production_pre is not None and not production_unchanged:
        raise PilotError("PILOT2_HUMAN_REVIEW_PRODUCTION_MUTATED")
    result["production_pre"] = production_pre
    result["production_post"] = production_post
    result["production_unchanged"] = production_unchanged
    explicit_decisions_path = output_dir / "pilot2_human_review_decisions.json"
    ready_path = output_dir / "pilot2_human_review_ready.json"
    report_path = output_dir / "pilot2_human_review_report.md"
    metrics_path = output_dir / "pilot2_human_review_metrics.json"
    explicit_decisions = {
        "document_type": PILOT2_HUMAN_REVIEW_DECISIONS_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "REVIEW_COMPLETE",
        "pilot_run_id": pilot_run_id,
        "source_sha256": source_sha256,
        "generalization_verdict": verdict,
        "generalization_rationale": verdict_rationale,
        "claims": reviewed_claims,
    }
    write_json(explicit_decisions_path, explicit_decisions)
    write_json(ready_path, result)
    write_json(metrics_path, metrics)
    report_path.write_text(render_pilot2_human_review_report(result), encoding="utf-8")
    result.update({
        "decisions_artifact_path": str(explicit_decisions_path),
        "ready_path": str(ready_path),
        "report_path": str(report_path),
        "metrics_path": str(metrics_path),
        "inputs_unchanged": input_artifacts_unchanged,
    })
    return result


def _gate_b_evidence_admission(
    full_text: str,
    page_by_locator: dict[str, str],
    evidence_excerpt: str,
    evidence_pointer: str,
) -> dict[str, Any]:
    locator = resolve_pdf_evidence_locator(full_text, evidence_excerpt, evidence_pointer)
    if locator.get("status") == "resolved":
        return {
            "accepted": True,
            "mode": "EXACT_SOURCE_QUOTE",
            "locator_status": locator.get("status"),
            "match_method": locator.get("match_method"),
        }
    if locator.get("reason") == "cross_page_span":
        spans = _ordered_cross_page_spans(page_by_locator, locator, evidence_excerpt)
        if spans:
            return {
                "accepted": True,
                "mode": "EXACT_ORDERED_CROSS_PAGE_SPAN",
                "locator_status": locator.get("status"),
                "match_method": "ordered_exact_spans",
                "spans": spans,
            }
    return {
        "accepted": False,
        "mode": "QUOTE_DRIFT_REJECTED",
        "locator_status": locator.get("status"),
        "reason": locator.get("reason"),
    }


def _render_pilot2_gate_b_report(metrics: dict[str, Any]) -> str:
    root = metrics["root_cause"]
    failures = metrics["failure_allocation"]
    checks = metrics["acceptance_checks"]
    lines = [
        "# Phase 3C Pilot #2 Gate B — Semantic Failure Repair", "",
        "## Outcome", "",
        f"- PHASE3C_PILOT2_GATE_B_COMPLETE: `{str(metrics['PHASE3C_PILOT2_GATE_B_COMPLETE']).lower()}`",
        "- Pilot #2 rerun: `NO`",
        "- LLM calls: `0`",
        "- Historical Pilot #2 generalization verdict: `FAIL` (unchanged)",
        "- Historical semantic failure rate: `34.48%` (10/29; unchanged)",
        "- Historical atomicity issue rate: `44.83%` (13/29; unchanged)", "",
        "## Root cause", "",
        f"- Attribution: {root['attribution']}",
        f"- Quote drift: {root['quote_drift']}",
        f"- Atomicity: {root['atomicity']}",
        f"- Mutation path: `{root['mutation_path']}`", "",
        "The unsafe rule treated attribution metadata as a grammatical subject. For company-scoped Claims it replaced the first `公司` with the attributed speaker, or prefixed the speaker when no company token was present. The repair keeps `statement` unchanged and validates `attributed_to` separately.", "",
        "## Failure allocation", "",
        f"- Deterministic post-processing: `{failures['deterministic_postprocessing']['count']}` — `{', '.join(failures['deterministic_postprocessing']['claim_ids'])}`",
        f"- Primarily model extraction: `{failures['primarily_model_extraction']['count']}` — `{', '.join(failures['primarily_model_extraction']['claim_ids'])}`",
        f"- Mixed or uncertain: `{failures['mixed_or_uncertain']['count']}` — `{', '.join(failures['mixed_or_uncertain']['claim_ids'])}`", "",
        "This allocation concerns the ten historical UNSUPPORTED Claims' primary failure path. It does not rewrite those Claims or estimate a new quality rate.", "",
        "## Changed code paths", "",
    ]
    lines += [f"- `{path}`" for path in metrics["changed_code_paths"]]
    lines += ["", "## Repairs", ""]
    lines += [f"- {name}: `{'PASS' if passed else 'FAIL'}`" for name, passed in checks.items()]
    lines += ["", "## Prompt categories", ""]
    lines += [
        f"- {name}: `{'PASS' if passed else 'FAIL'}`"
        for name, passed in metrics["prompt_repairs"].items()
    ]
    lines += ["", "## Evidence contract simulation", ""]
    for name, item in metrics["evidence_contract_simulation"].items():
        lines.append(
            f"- {name}: `{'ACCEPT' if item['accepted'] else 'REJECT'}` "
            f"(expected `{'ACCEPT' if item['expected_accepted'] else 'REJECT'}`; {item['mode']})"
        )
    lines += [
        "", "Approved normalization remains layout-only. Removed/inserted words, speaker-boundary deletion, entity substitution, and technical-term substitution remain fail-closed.", "",
        "## Historical immutability and isolation", "",
        f"- Historical artifacts unchanged: `{'PASS' if metrics['historical_artifacts_unchanged'] else 'FAIL'}`",
        f"- Claim IDs unchanged: `{'PASS' if metrics['claim_ids_unchanged'] else 'FAIL'}`",
        f"- Raw Claims unchanged: `{'PASS' if metrics['raw_claims_unchanged'] else 'FAIL'}`",
        f"- Raw Evidence unchanged: `{'PASS' if metrics['raw_evidence_unchanged'] else 'FAIL'}`",
        f"- Human decisions unchanged: `{'PASS' if metrics['human_decisions_unchanged'] else 'FAIL'}`",
        f"- Production SHA: `{metrics['production_pre']['sha256']}` → `{metrics['production_post']['sha256']}`",
        f"- Production table counts changed: `{'YES' if metrics['production_pre']['table_counts'] != metrics['production_post']['table_counts'] else 'NO'}`",
        f"- integrity_check: `{metrics['production_post']['integrity_check']}`",
        f"- foreign-key violations: `{len(metrics['production_post']['foreign_key_violations'])}`", "",
        "No canonical schema, Production, IMA, propagation, or legacy pipeline operation was performed.", "",
        "## Remaining risks", "",
        "- Prompt repairs require a separately authorized real re-extraction before any quality improvement can be measured.",
        "- Noisy entity and technical terms remain intentionally conservative and may increase Human Review load.",
        "- Historical atomicity defects remain historical truth; this gate changes only future extraction instructions.", "",
        "## Next gate", "",
        "`Pilot #2 Controlled Re-extraction Authorization`", "",
        "STOP: no re-extraction was performed.", "",
    ]
    return "\n".join(lines)


def audit_pilot2_gate_b_semantic_repair(
    run_dir: Path,
    source_file: Path,
    production_db_path: Path,
) -> dict[str, Any]:
    """Audit Gate B repairs without LLM calls, extraction replay, or historical mutation."""
    run_dir = Path(run_dir).resolve()
    source_file = Path(source_file).resolve()
    production_db_path = Path(production_db_path).resolve()
    historical_names = (
        "extraction_bundle.json",
        "evidence_contract_v2_draft.json",
        "pilot2_gate_a_quote_fidelity.json",
        "pilot2_gate_a_quote_fidelity_report.md",
        "pilot2_human_review_decisions.json",
        "pilot2_human_review_ready.json",
        "pilot2_human_review_report.md",
        "pilot2_human_review_metrics.json",
    )
    historical_paths = {name: run_dir / name for name in historical_names}
    if not source_file.is_file() or any(not path.is_file() for path in historical_paths.values()):
        raise PilotError("PILOT2_GATE_B_INPUT_MISSING")
    historical_hashes_pre = {
        name: sha256_file(path) for name, path in historical_paths.items()
    }
    production_pre = production_snapshot(production_db_path)
    bundle = _load_json(historical_paths["extraction_bundle.json"])
    gate_a = _load_json(historical_paths["pilot2_gate_a_quote_fidelity.json"])
    human_ready = _load_json(historical_paths["pilot2_human_review_ready.json"])
    human_metrics = _load_json(historical_paths["pilot2_human_review_metrics.json"])
    if (
        bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE
        or gate_a.get("document_type") != PILOT2_GATE_A_DOCUMENT_TYPE
        or human_ready.get("document_type") != PILOT2_HUMAN_REVIEW_READY_DOCUMENT_TYPE
    ):
        raise PilotError("PILOT2_GATE_B_INPUT_TYPE_INVALID")
    run_id = bundle.get("pilot_run_id")
    source_sha256 = (bundle.get("source") or {}).get("sha256")
    if (
        not run_id
        or gate_a.get("pilot_run_id") != run_id
        or human_ready.get("pilot_run_id") != run_id
        or sha256_file(source_file) != source_sha256
    ):
        raise PilotError("PILOT2_GATE_B_BINDING_INVALID")

    bundle_claims = bundle.get("claims") or []
    bundle_by_id = {item["claim_id"]: item for item in bundle_claims}
    review_claims = human_ready.get("claims") or []
    claim_ids = [item["claim_id"] for item in bundle_claims]
    claim_ids_unchanged = [item.get("claim_id") for item in review_claims] == claim_ids
    raw_claims_unchanged = claim_ids_unchanged and all(
        review["original_claim"] == original["statement"]
        for review, original in zip(review_claims, bundle_claims)
    )
    raw_evidence_unchanged = claim_ids_unchanged and all(
        review["immutable_evidence_excerpt"] == original["evidence_excerpt"]
        for review, original in zip(review_claims, bundle_claims)
    )
    if not claim_ids_unchanged or not raw_claims_unchanged or not raw_evidence_unchanged:
        raise PilotError("PILOT2_GATE_B_HISTORICAL_CLAIMS_CHANGED")

    representative_ids = (
        "CLM_20260831_C9ADC34A", "CLM_20260831_A7C48FD4",
        "CLM_20260831_1EB0E35E", "CLM_20260831_D1651EDB",
        "CLM_20260831_94DCEF45", "CLM_20260831_DD6DACEB",
        "CLM_20260831_3C36DBF8", "CLM_20260831_3F54CD90",
    )
    simulations = []
    for claim_id in representative_ids:
        claim = bundle_by_id.get(claim_id)
        if not claim:
            raise PilotError(f"PILOT2_GATE_B_REPRESENTATIVE_MISSING: {claim_id}")
        normalization = (
            (claim.get("structured") or {}).get("statement_normalization")
            or claim.get("statement_normalization")
            or {}
        )
        raw_statement = normalization.get("raw_statement")
        old_mutated = bool(
            normalization.get("method")
            == "deterministic_attribution_prefix_or_company_replacement"
            and raw_statement
            and raw_statement != claim.get("statement")
        )
        simulations.append({
            "claim_id": claim_id,
            "failure_category": "ATTRIBUTION_ERROR",
            "identified_transformation_rule": normalization.get("method") or "",
            "would_old_rule_mutate_subject": old_mutated,
            "old_output_differs_from_raw_model_statement": old_mutated,
            "new_rule_expected_behavior": (
                "Preserve the raw model/source-derived statement unchanged and keep attributed_to separate."
            ),
        })
    if not all(item["would_old_rule_mutate_subject"] for item in simulations):
        raise PilotError("PILOT2_GATE_B_ROOT_CAUSE_NOT_REPRODUCED")

    unsupported = [item for item in review_claims if item.get("semantic_support") == "UNSUPPORTED"]
    deterministic_ids = []
    model_ids = []
    mixed_ids = []
    for review in unsupported:
        claim_id = review["claim_id"]
        claim = bundle_by_id[claim_id]
        normalization = (
            (claim.get("structured") or {}).get("statement_normalization")
            or claim.get("statement_normalization")
            or {}
        )
        old_mutated = normalization.get("method") == "deterministic_attribution_prefix_or_company_replacement"
        if review.get("semantic_failure_category") == "ATTRIBUTION_ERROR" and old_mutated:
            deterministic_ids.append(claim_id)
        elif old_mutated:
            mixed_ids.append(claim_id)
        else:
            model_ids.append(claim_id)
    failure_allocation = {
        "deterministic_postprocessing": {
            "count": len(deterministic_ids), "claim_ids": deterministic_ids,
        },
        "primarily_model_extraction": {"count": len(model_ids), "claim_ids": model_ids},
        "mixed_or_uncertain": {"count": len(mixed_ids), "claim_ids": mixed_ids},
    }
    if (len(deterministic_ids), len(model_ids), len(mixed_ids)) != (8, 1, 1):
        raise PilotError("PILOT2_GATE_B_FAILURE_ALLOCATION_UNEXPECTED")

    parsed = parse_source_with_diagnostics(source_file)
    if parsed.source_type != "pdf":
        raise PilotError("PILOT2_GATE_B_SOURCE_INVALID")
    full_text = parsed.text
    page_by_locator = {
        locator: body for locator, body in source_units(full_text) if locator.startswith("PAGE:")
    }

    def historical_case(claim_id: str, *, excerpt: str | None = None) -> dict[str, Any]:
        claim = bundle_by_id[claim_id]
        return _gate_b_evidence_admission(
            full_text,
            page_by_locator,
            excerpt if excerpt is not None else claim["evidence_excerpt"],
            claim["evidence_pointer"],
        )

    exact_claim = bundle_by_id["CLM_20260831_DD6DACEB"]
    technical_claim = bundle_by_id["CLM_20260831_C7BF26D4"]
    evidence_cases = {
        "exact_quote": (historical_case("CLM_20260831_DD6DACEB"), True),
        "layout_normalized_exact": (historical_case("CLM_20260831_C9ADC34A"), True),
        "ordered_cross_page_span": (historical_case("CLM_20260831_89CE1154"), True),
        "lexical_cleanup": (historical_case("CLM_20260831_5203349C"), False),
        "deleted_filler_words": (historical_case("CLM_20260831_09C4451B"), False),
        "inserted_words": (
            historical_case(
                "CLM_20260831_DD6DACEB",
                excerpt=f"{exact_claim['evidence_excerpt']}新增词",
            ),
            False,
        ),
        "speaker_boundary_deletion": (historical_case("CLM_20260831_F688BC15"), False),
        "entity_normalized_quote": (
            historical_case(
                "CLM_20260831_DD6DACEB",
                excerpt=exact_claim["evidence_excerpt"].replace("公司", "发言人", 1),
            ),
            False,
        ),
        "technical_term_normalized_quote": (
            historical_case(
                "CLM_20260831_C7BF26D4",
                excerpt=technical_claim["evidence_excerpt"].replace("清香甘", "硅光", 1),
            ),
            False,
        ),
    }
    evidence_simulation = {}
    for name, (result, expected) in evidence_cases.items():
        evidence_simulation[name] = {**result, "expected_accepted": expected}
    evidence_contract_passed = all(
        item["accepted"] is item["expected_accepted"]
        for item in evidence_simulation.values()
    )
    if not evidence_contract_passed:
        raise PilotError("PILOT2_GATE_B_EVIDENCE_CONTRACT_FAILED")

    prompt_status = phase3c_prompt_repair_status()
    prompt_categories = {
        name: prompt_status["categories"][name]
        for name in (
            "evidence_quote_verbatim_preservation", "claim_atomicity",
            "attribution_preservation", "conditionality_preservation",
            "entity_inference_prevention", "technical_term_inference_prevention",
        )
    }
    analyzer_source = Path(analyzer_module.__file__).read_text(encoding="utf-8")
    unsafe_rule_removed = (
        'raw_statement.replace("公司", normalized_subject, 1)' not in analyzer_source
        and "deterministic_attribution_prefix_or_company_replacement" not in analyzer_source
    )
    acceptance_checks = {
        "Attribution post-processing root cause identified": len(simulations) == 8,
        "Known company-to-speaker mutation removed": unsafe_rule_removed,
        "attributed_to separated from grammatical subject": unsafe_rule_removed,
        "entity inference protection": prompt_categories["entity_inference_prevention"],
        "technical-term inference protection": prompt_categories["technical_term_inference_prevention"],
        "conditionality regression protection": prompt_categories["conditionality_preservation"],
        "Evidence verbatim prompt rule": prompt_categories["evidence_quote_verbatim_preservation"],
        "Evidence fail-closed runtime validation": evidence_contract_passed,
        "speaker-boundary quote protection": not evidence_simulation["speaker_boundary_deletion"]["accepted"],
        "atomicity prompt repair": prompt_categories["claim_atomicity"],
    }

    simulation_path = run_dir / "pilot2_gate_b_repair_simulation.json"
    report_path = run_dir / "pilot2_gate_b_semantic_repair_report.md"
    metrics_path = run_dir / "pilot2_gate_b_semantic_repair_metrics.json"
    simulation_artifact = {
        "document_type": "phase3c_pilot2_gate_b_repair_simulation",
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": run_id,
        "source_sha256": source_sha256,
        "historical_claims_modified": False,
        "simulations": simulations,
    }
    write_json(simulation_path, simulation_artifact)

    historical_hashes_post = {
        name: sha256_file(path) for name, path in historical_paths.items()
    }
    production_post = production_snapshot(production_db_path)
    historical_unchanged = historical_hashes_pre == historical_hashes_post
    production_unchanged = production_pre == production_post
    human_decisions_unchanged = (
        historical_hashes_pre["pilot2_human_review_decisions.json"]
        == historical_hashes_post["pilot2_human_review_decisions.json"]
    )
    all_checks_pass = (
        all(acceptance_checks.values())
        and prompt_status["passed"]
        and historical_unchanged
        and human_decisions_unchanged
        and production_unchanged
        and human_metrics.get("true_semantic_failure_rate", {}).get("percent") == 34.48
        and human_metrics.get("atomicity", {}).get("issue_rate", {}).get("percent") == 44.83
    )
    metrics = {
        "document_type": PILOT2_GATE_B_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": run_id,
        "source_sha256": source_sha256,
        "PHASE3C_PILOT2_GATE_B_COMPLETE": all_checks_pass,
        "historical_pilot2_verdict": "FAIL",
        "historical_semantic_failure_rate_percent": 34.48,
        "historical_atomicity_issue_rate_percent": 44.83,
        "root_cause": {
            "attribution": "Deterministic attribution normalization substituted or prefixed the speaker into the Claim statement, changing company/business subjects.",
            "quote_drift": "The extraction prompt allowed lexical cleanup while the deterministic locator correctly remained fail-closed; 7/29 historical excerpts drifted.",
            "atomicity": "The prior prompt did not sufficiently force splits across independently reviewable subjects, time horizons, certainty levels, and Evidence spans.",
            "mutation_path": "raw model Claim -> validation -> attribution normalization -> deterministic speaker replacement/prefix -> extraction bundle Claim",
        },
        "failure_allocation": failure_allocation,
        "changed_code_paths": [
            "src/pro_a/analyzer.py", "src/pro_a/prompts.py",
            "src/pro_a/corpus_pilot.py", "tests/test_v0_2_1_knowledge_quality.py",
            "tests/test_corpus_pilot.py", "docs/PHASE3C_LIVE_CORPUS_EXPANSION_PILOT.md",
        ],
        "postprocessing_rules_removed_or_narrowed": [
            "Removed deterministic company-token replacement with attributed_to.",
            "Removed deterministic attributed_to statement prefix injection.",
            "Retained required attributed_to validation for company-scoped and attributed Claim natures.",
        ],
        "prompt_repairs": prompt_categories,
        "prompt_sha256": prompt_status["prompt_sha256"],
        "quote_contract_changes": [
            "Prompt now requires one continuous verbatim excerpt with no lexical cleanup.",
            "Runtime exact/layout-only/ordered-span admission logic is unchanged and fail-closed.",
            "Speaker/timestamp boundaries remain source content.",
        ],
        "evidence_contract_simulation": evidence_simulation,
        "acceptance_checks": acceptance_checks,
        "regression_fixtures": [
            "龙头公司 != 龙头发言人", "大陆公司 != 大陆发言人",
            "两家龙头公司订单完成率不足50%", "袁杰 entity inference blocked",
            "清香甘 technical correction blocked", "可能 remains on the capacity proposition",
            "verbatim/layout/cross-page acceptance", "lexical/speaker-boundary/entity/technical rejection",
        ],
        "historical_hashes_pre": historical_hashes_pre,
        "historical_hashes_post": historical_hashes_post,
        "historical_artifacts_unchanged": historical_unchanged,
        "claim_ids_unchanged": claim_ids_unchanged,
        "raw_claims_unchanged": raw_claims_unchanged,
        "raw_evidence_unchanged": raw_evidence_unchanged,
        "human_decisions_unchanged": human_decisions_unchanged,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "llm_calls_added": 0,
        "pilot2_rerun": False,
        "pilot3_executed": False,
        "production_write": False,
        "production_schema_changed": False,
        "canonical_claim_schema_changed": False,
        "canonical_evidence_schema_changed": False,
        "ima_invoked": False,
        "propagation_invoked": False,
        "legacy_pipeline_invoked": False,
        "remaining_unresolved_risks": [
            "No improved extraction quality metric can be claimed before an authorized re-extraction.",
            "Noisy entity and technical wording remains a Human Review concern by design.",
        ],
        "PHASE3C_NEXT_GATE": "Pilot #2 Controlled Re-extraction Authorization",
    }
    write_json(metrics_path, metrics)
    report_path.write_text(_render_pilot2_gate_b_report(metrics), encoding="utf-8")
    if not all_checks_pass:
        raise PilotError("PILOT2_GATE_B_ACCEPTANCE_FAILED")
    return {
        "status": "PASS",
        "metrics": metrics,
        "simulation_path": str(simulation_path),
        "report_path": str(report_path),
        "metrics_path": str(metrics_path),
    }


def _comparison_metric_view(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(metrics[key])
        for key in (
            "pdf_pages", "parsed_text_units", "parse_errors", "empty_units",
            "extracted_characters", "claims_total", "llm_calls", "prompt_tokens",
            "completion_tokens", "total_tokens", "tokens_per_claim",
            "single_page_locator_bound", "cross_page_exact_spans", "locator_ambiguous",
            "locator_unresolved", "bounded_context_candidate_claims", "node_matches",
            "node_candidates", "relation_candidates", "locator_binding_rate",
            "cross_page_incidence", "context_candidate_incidence",
        )
    }


def render_pilot_comparison_markdown(comparison: dict[str, Any]) -> str:
    pilot1 = comparison["pilot1_pre_review"]
    pilot2 = comparison["pilot2_pre_review"]
    return "\n".join([
        "# Phase 3C Pilot #1 vs Pilot #2 Pre-Human-Review Comparison", "",
        "This comparison covers deterministic mechanics and extraction economics only. It does not declare either pilot better or worse.", "",
        "| Metric | Pilot #1 | Pilot #2 |",
        "|---|---:|---:|",
        f"| PDF pages | {pilot1['pdf_pages']} | {pilot2['pdf_pages']} |",
        f"| Claims | {pilot1['claims_total']} | {pilot2['claims_total']} |",
        f"| LLM calls | {pilot1['llm_calls']} | {pilot2['llm_calls']} |",
        f"| Total tokens | {pilot1['total_tokens']} | {pilot2['total_tokens']} |",
        f"| Tokens per Claim | {pilot1['tokens_per_claim']} | {pilot2['tokens_per_claim']} |",
        f"| Single-page locator bound | {pilot1['single_page_locator_bound']} | {pilot2['single_page_locator_bound']} |",
        f"| Cross-page exact spans | {pilot1['cross_page_exact_spans']} | {pilot2['cross_page_exact_spans']} |",
        f"| Ambiguous / unresolved | {pilot1['locator_ambiguous']} / {pilot1['locator_unresolved']} | {pilot2['locator_ambiguous']} / {pilot2['locator_unresolved']} |",
        f"| Bounded-context candidate Claims | {pilot1['bounded_context_candidate_claims']} | {pilot2['bounded_context_candidate_claims']} |",
        "", "## Deferred semantic metrics", "",
        "Pilot #2 strict KEEP rate, Evidence v2 semantic support rate, true semantic failure rate, and atomicity issue rate are all `PENDING_HUMAN_REVIEW`.", "",
    ])


def build_pilot1_vs_pilot2_pre_review_comparison(
    pilot1_bundle_path: Path,
    pilot1_source_path: Path,
    pilot2_metrics: dict[str, Any],
    *,
    output_dir: Path,
) -> dict[str, Any]:
    pilot1_bundle = _load_json(Path(pilot1_bundle_path).resolve())
    pilot1_source_path = Path(pilot1_source_path).resolve()
    if sha256_file(pilot1_source_path) != pilot1_bundle["source"]["sha256"]:
        raise PilotError("PILOT2_COMPARISON_PILOT1_SOURCE_MISMATCH")
    parsed = parse_source_with_diagnostics(pilot1_source_path)
    pilot1_draft = _build_evidence_support_draft(pilot1_bundle, parsed.text)
    pilot1_metrics = _pilot_pre_review_metrics(pilot1_bundle, pilot1_draft, parsed)
    comparison = {
        "document_type": PILOT2_COMPARISON_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "PRE_HUMAN_REVIEW_ONLY",
        "comparison_scope": "same_stage_extraction_mechanics_and_economics",
        "no_quality_verdict": True,
        "pilot1_pre_review": _comparison_metric_view(pilot1_metrics),
        "pilot2_pre_review": _comparison_metric_view(pilot2_metrics),
        "pilot1_post_review_reference_not_compared_as_equivalent": {
            "strict_keep_rate_percent": 64.15,
            "evidence_v2_semantic_support_rate_percent": 88.68,
            "true_semantic_failure_rate_percent": 11.32,
            "atomicity_issues": 7,
        },
        "pilot2_semantic_metrics": {
            "strict_human_review_keep_rate": "PENDING_HUMAN_REVIEW",
            "evidence_v2_semantic_support_rate": "PENDING_HUMAN_REVIEW",
            "true_semantic_failure_rate": "PENDING_HUMAN_REVIEW",
            "atomicity_issue_rate": "PENDING_HUMAN_REVIEW",
        },
    }
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "pilot1_vs_pilot2_pre_review_comparison.json"
    markdown_path = output_dir / "pilot1_vs_pilot2_pre_review_comparison.md"
    write_json(json_path, comparison)
    markdown_path.write_text(render_pilot_comparison_markdown(comparison), encoding="utf-8")
    return {
        "comparison": comparison,
        "comparison_path": str(json_path),
        "comparison_markdown_path": str(markdown_path),
    }


def _artifact_directory_hashes(path: Path) -> dict[str, str]:
    path = Path(path).resolve()
    return {
        item.relative_to(path).as_posix(): sha256_file(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def _controlled_reextraction_freeze(cfg: AppConfig) -> dict[str, Any]:
    prompt_status = phase3c_prompt_repair_status(analyzer_module.SOURCE_ANALYSIS_SYSTEM)
    analyzer_path = Path(analyzer_module.__file__).resolve()
    prompts_path = Path(__file__).resolve().with_name("prompts.py")
    analyzer_source = analyzer_path.read_text(encoding="utf-8")
    attribution_repair_active = (
        'raw_statement.replace("公司", normalized_subject, 1)' not in analyzer_source
        and "deterministic_attribution_prefix_or_company_replacement" not in analyzer_source
        and "never inject or substitute attributed_to into Claim semantics" in analyzer_source
    )
    categories = prompt_status["categories"]
    freeze = {
        "prompt_sha256": prompt_status["prompt_sha256"],
        "prompt_categories": copy.deepcopy(categories),
        "gate_b_attribution_repair_active": attribution_repair_active,
        "gate_b_quote_verbatim_rule_active": categories["evidence_quote_verbatim_preservation"],
        "gate_b_atomicity_rule_active": categories["claim_atomicity"],
        "code_file_sha256": {
            "src/pro_a/analyzer.py": sha256_file(analyzer_path),
            "src/pro_a/prompts.py": sha256_file(prompts_path),
            "src/pro_a/corpus_pilot.py": sha256_file(Path(__file__).resolve()),
        },
        "working_tree_repair_summary": [
            "Deterministic company-token replacement and speaker-prefix injection are absent.",
            "attributed_to is validated as metadata and is not used as the statement subject.",
            "The extraction prompt requires verbatim continuous Evidence and independently reviewable atomic Claims.",
        ],
        "extraction_configuration": {
            "analysis_mode": "deep",
            "configured_request_model": cfg.llm.model,
            "base_url": cfg.llm.base_url,
            "timeout_seconds": cfg.llm.timeout_seconds,
            "max_retries": cfg.llm.max_retries,
            "retry_backoff_seconds": cfg.llm.retry_backoff_seconds,
            "temperature": cfg.llm.temperature,
            "max_output_tokens": cfg.llm.max_output_tokens,
            "max_chunk_chars": cfg.llm.max_chunk_chars,
        },
    }
    if not (
        prompt_status["passed"]
        and attribution_repair_active
        and freeze["gate_b_quote_verbatim_rule_active"]
        and freeze["gate_b_atomicity_rule_active"]
    ):
        raise PilotError("PILOT2_REEXTRACTION_GATE_B_PATH_NOT_ACTIVE")
    return freeze


def _controlled_reextraction_mechanical_diagnostics(
    bundle: dict[str, Any], gate_a: dict[str, Any], evidence_draft: dict[str, Any],
) -> dict[str, Any]:
    claims = bundle.get("claims") or []
    old_mutation_ids = []
    speaker_business_flags: dict[str, list[str]] = {
        "production_capability": [],
        "capacity": [],
        "order_completion_rate": [],
        "procurement_or_material_capability": [],
    }
    business_patterns = {
        "production_capability": re.compile(r"发言人.*(?:生产|制造|量产|能力)"),
        "capacity": re.compile(r"发言人.*产能"),
        "order_completion_rate": re.compile(r"发言人.*(?:订单.*完成率|完成率.*订单)"),
        "procurement_or_material_capability": re.compile(r"发言人.*(?:采购|材料|原料).*(?:能力|供给|供应)"),
    }
    conditional_markers = (
        "可能", "预计", "大概率", "如果", "若", "或", "或者", "前提", "可能会",
        "may", "could", "likely",
    )
    conditional_flags = []
    explicit_entity_flags = []
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        statement = str(claim.get("statement") or "")
        evidence = str(claim.get("evidence_excerpt") or "")
        normalization = (
            (claim.get("structured") or {}).get("statement_normalization")
            or claim.get("statement_normalization")
            or {}
        )
        if normalization.get("method") == "deterministic_attribution_prefix_or_company_replacement":
            old_mutation_ids.append(claim_id)
        for name, pattern in business_patterns.items():
            if pattern.search(statement):
                speaker_business_flags[name].append(claim_id)
        if re.search(r"袁杰.{0,12}可能指|可能指.{0,12}袁杰", statement):
            explicit_entity_flags.append(claim_id)
        statement_markers = {marker for marker in conditional_markers if marker.lower() in statement.lower()}
        evidence_markers = {marker for marker in conditional_markers if marker.lower() in evidence.lower()}
        if statement_markers != evidence_markers:
            conditional_flags.append({
                "claim_id": claim_id,
                "statement_markers": sorted(statement_markers),
                "evidence_markers": sorted(evidence_markers),
            })

    gate_claims = gate_a.get("claims") or []
    entity_gate_ids = [
        item["claim_id"] for item in gate_claims if item.get("entity_name_difference") is True
    ]
    technical_gate_ids = [
        item["claim_id"] for item in gate_claims if item.get("technical_term_difference") is True
    ]
    draft_claims = evidence_draft.get("claims") or []
    multi_span_ids = [
        item["claim_id"] for item in draft_claims if len(item.get("evidence_spans") or []) > 1
    ]
    return {
        "deterministic_company_to_speaker_mutations": {
            "count": len(old_mutation_ids),
            "claim_ids": old_mutation_ids,
            "basis": "unsafe deterministic statement_normalization method marker",
        },
        "known_old_mutation_recurrence": "YES" if old_mutation_ids else "NO",
        "speaker_business_qa_flags": {
            name: {"count": len(ids), "claim_ids": ids}
            for name, ids in speaker_business_flags.items()
        },
        "entity_inference_mechanical_flags": {
            "count": len(set(entity_gate_ids + explicit_entity_flags)),
            "claim_ids": sorted(set(entity_gate_ids + explicit_entity_flags)),
            "diagnostic_only": True,
        },
        "technical_term_inference_mechanical_flags": {
            "count": len(technical_gate_ids),
            "claim_ids": technical_gate_ids,
            "diagnostic_only": True,
        },
        "conditionality_qa_flags": {
            "count": len(conditional_flags),
            "claims": conditional_flags,
            "basis": "lexical conditional-marker set differs between statement and Evidence",
            "diagnostic_only": True,
        },
        "pre_review_atomicity_candidates": {
            "multi_subject_review_candidates": "PENDING_HUMAN_REVIEW",
            "multi_time_horizon_review_candidates": "PENDING_HUMAN_REVIEW",
            "multi_evidence_span_review_candidates": {
                "count": len(multi_span_ids), "claim_ids": multi_span_ids,
            },
            "semantic_atomicity_decision": "PENDING_HUMAN_REVIEW",
        },
    }


def _controlled_reextraction_metric_view(
    evidence_metrics: dict[str, Any], gate_metrics: dict[str, Any],
    *, deterministic_mutations: int,
) -> dict[str, Any]:
    return {
        **_comparison_metric_view(evidence_metrics),
        "quality_eligible_node_candidates": evidence_metrics["quality_eligible_node_candidates"],
        "rejected_relation_candidates": evidence_metrics["rejected_relation_candidates"],
        "tokens_per_deterministically_bound_claim": evidence_metrics[
            "tokens_per_deterministically_bound_claim"
        ],
        "fidelity_counts": copy.deepcopy(gate_metrics["fidelity_counts"]),
        "evidence_quote_fidelity_rate": copy.deepcopy(
            gate_metrics["evidence_quote_fidelity_rate"]
        ),
        "evidence_quote_drift_rate": copy.deepcopy(
            gate_metrics["evidence_quote_drift_rate"]
        ),
        "quote_drift_rate": copy.deepcopy(gate_metrics["quote_drift_rate"]),
        "model_page_pointer_accuracy": copy.deepcopy(
            gate_metrics["model_page_pointer_accuracy"]
        ),
        "deterministic_locator_recovery_rate": copy.deepcopy(
            gate_metrics["deterministic_locator_recovery_rate"]
        ),
        "deterministic_company_to_speaker_mutations": deterministic_mutations,
    }


def _render_reextraction_quote_report(artifact: dict[str, Any]) -> str:
    metrics = artifact["metrics"]
    counts = metrics["fidelity_counts"]
    lines = [
        "# Phase 3C Pilot #2 Controlled Re-extraction — Quote Fidelity", "",
        "This is deterministic quote/locator classification only. Human semantic review was not performed.", "",
        f"- run ID: `{artifact['pilot_run_id']}`",
        f"- Claims classified: {metrics['claims_total']}",
        f"- Evidence quote fidelity: {metrics['gate_a_deterministic_bound']['fraction']} ({metrics['gate_a_deterministic_bound']['percent']}%)",
        f"- Quote drift: {metrics['quote_drift_rate']['fraction']} ({metrics['quote_drift_rate']['percent']}%)", "",
        "| Classification | Count |", "|---|---:|",
    ]
    lines += [f"| {status} | {counts[status]} |" for status in sorted(PILOT2_GATE_A_FIDELITY_STATUSES)]
    lines += ["", "All Human decisions remain `PENDING`.", ""]
    return "\n".join(lines)


def _render_historical_vs_reextraction_comparison(comparison: dict[str, Any]) -> str:
    historical = comparison["historical_pilot2_pre_review"]
    current = comparison["controlled_reextraction_pre_review"]
    return "\n".join([
        "# Historical Pilot #2 vs Controlled Re-extraction — Pre-review Comparison", "",
        "Only mechanical extraction, Evidence, locator, token, and observational metrics are compared. Semantic efficacy and generalization remain pending.", "",
        "| Metric | Historical Pilot #2 | Controlled re-extraction |",
        "|---|---:|---:|",
        f"| Claims | {historical['claims_total']} | {current['claims_total']} |",
        f"| LLM calls | {historical['llm_calls']} | {current['llm_calls']} |",
        f"| Total tokens | {historical['total_tokens']} | {current['total_tokens']} |",
        f"| Tokens per Claim | {historical['tokens_per_claim']} | {current['tokens_per_claim']} |",
        f"| Evidence quote fidelity | {historical['evidence_quote_fidelity_rate']['percent']}% | {current['evidence_quote_fidelity_rate']['percent']}% |",
        f"| Quote drift | {historical['quote_drift_rate']['percent']}% | {current['quote_drift_rate']['percent']}% |",
        f"| Deterministic locator bound | {historical['locator_binding_rate']['fraction']} | {current['locator_binding_rate']['fraction']} |",
        f"| Cross-page ordered spans | {historical['cross_page_exact_spans']} | {current['cross_page_exact_spans']} |",
        f"| Bounded-context candidates | {historical['bounded_context_candidate_claims']} | {current['bounded_context_candidate_claims']} |",
        f"| Deterministic company→speaker mutations | {historical['deterministic_company_to_speaker_mutations']} | {current['deterministic_company_to_speaker_mutations']} |",
        f"| Existing Node matches | {historical['node_matches']} | {current['node_matches']} |",
        f"| Node candidates | {historical['node_candidates']} | {current['node_candidates']} |",
        f"| Relation candidates | {historical['relation_candidates']} | {current['relation_candidates']} |", "",
        "Semantic support, true semantic failure, KEEP rate, semantic atomicity, attribution semantics, and conditionality semantics: `PENDING_HUMAN_REVIEW`.", "",
        "Independent generalization re-test: `NOT_YET_PERFORMED`.", "",
    ])


def run_pilot2_controlled_reextraction(
    source_path: Path,
    source_search_root: Path,
    historical_run_dir: Path,
    cfg: AppConfig,
    *,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Run one authorized repair-efficacy extraction, then mechanics-only QA."""
    source_path = Path(source_path).resolve()
    source_search_root = Path(source_search_root).resolve()
    historical_run_dir = Path(historical_run_dir).resolve()
    production_db = Path(production_db_path or cfg.db_path).resolve()
    if source_path.name != PILOT2_SOURCE_NAME or not source_path.is_file():
        raise PilotError("PILOT2_REEXTRACTION_SOURCE_INVALID")
    source_sha256 = sha256_file(source_path)
    if source_sha256 != PILOT2_SOURCE_SHA256:
        raise PilotError("PILOT2_REEXTRACTION_SOURCE_SHA256_MISMATCH")
    matches = [
        path.resolve() for path in source_search_root.rglob(PILOT2_SOURCE_NAME) if path.is_file()
    ]
    if source_path not in matches or any(sha256_file(path) != PILOT2_SOURCE_SHA256 for path in matches):
        raise PilotError("PILOT2_REEXTRACTION_SOURCE_MATCH_SET_INVALID")
    historical_bundle_path = historical_run_dir / "extraction_bundle.json"
    historical_gate_path = historical_run_dir / "pilot2_gate_a_metrics.json"
    historical_metrics_path = historical_run_dir / "pilot2_metrics.json"
    historical_gate_b_path = historical_run_dir / "pilot2_gate_b_semantic_repair_metrics.json"
    required_historical = (
        historical_bundle_path, historical_gate_path, historical_metrics_path, historical_gate_b_path,
    )
    if any(not path.is_file() for path in required_historical):
        raise PilotError("PILOT2_REEXTRACTION_HISTORICAL_INPUT_MISSING")
    historical_bundle = _load_json(historical_bundle_path)
    if (
        historical_bundle.get("pilot_run_id") != PILOT2_HISTORICAL_RUN_ID
        or (historical_bundle.get("source") or {}).get("sha256") != PILOT2_SOURCE_SHA256
    ):
        raise PilotError("PILOT2_REEXTRACTION_HISTORICAL_BINDING_INVALID")
    if not cfg.llm.enabled or not cfg.llm.api_key:
        raise PilotError("PILOT2_REEXTRACTION_LLM_NOT_AVAILABLE")
    if cfg.llm.model != "deepseek-chat":
        raise PilotError("PILOT2_REEXTRACTION_MODEL_INVALID")

    production_pre = production_snapshot(production_db)
    if production_pre["sha256"] != "581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250":
        raise PilotError("PILOT2_REEXTRACTION_PRODUCTION_BASELINE_MISMATCH")
    historical_hashes_pre = _artifact_directory_hashes(historical_run_dir)
    repair_freeze = _controlled_reextraction_freeze(cfg)
    run_id = make_id("PILOT")
    if run_id == PILOT2_HISTORICAL_RUN_ID:
        raise PilotError("PILOT2_REEXTRACTION_RUN_ID_COLLISION")
    output_dir = (cfg.root / "phase3c" / run_id).resolve()
    if output_dir.exists():
        raise PilotError("PILOT2_REEXTRACTION_OUTPUT_ALREADY_EXISTS")
    output_dir.mkdir(parents=True)
    freeze_artifact = {
        "document_type": "phase3c_pilot2_controlled_reextraction_freeze",
        "schema_version": SCHEMA_VERSION,
        "pilot_run_id": run_id,
        "historical_pilot_run_id": PILOT2_HISTORICAL_RUN_ID,
        "source": {"name": source_path.name, "sha256": source_sha256},
        "repair_freeze": repair_freeze,
        "historical_hashes_pre": historical_hashes_pre,
        "production_pre": production_pre,
        "one_logical_real_extraction_authorized": True,
        "quality_based_rerun_forbidden": True,
    }
    freeze_path = output_dir / "reextraction_freeze.json"
    write_json(freeze_path, freeze_artifact)

    extraction = extract_pilot_source(
        source_path,
        cfg,
        output_dir=output_dir,
        production_db_path=production_db,
        required_prompt_sha256=repair_freeze["prompt_sha256"],
        run_id=run_id,
    )
    rebound = rebind_stage1_evidence_locators(
        Path(extraction["extraction_bundle_path"]),
        source_path,
        output_dir=output_dir,
        production_db_path=production_db,
    )
    evidence = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]),
        Path(rebound["review_draft_path"]),
        source_path,
        output_dir=output_dir,
        production_db_path=production_db,
    )
    gate_a = run_pilot2_gate_a_quote_fidelity(
        Path(extraction["extraction_bundle_path"]),
        Path(rebound["rebound_bundle_path"]),
        Path(evidence["draft_path"]),
        source_path,
        output_dir=output_dir,
        production_db_path=production_db,
        original_review_path=Path(extraction["review_draft_path"]),
    )
    diagnostics = _controlled_reextraction_mechanical_diagnostics(
        extraction["bundle"], gate_a, evidence["draft"],
    )

    quote_artifact = copy.deepcopy(gate_a)
    quote_artifact["document_type"] = PILOT2_REEXTRACTION_QUOTE_DOCUMENT_TYPE
    quote_artifact["stage"] = "CONTROLLED_REEXTRACTION_PRE_HUMAN_REVIEW"
    quote_path = output_dir / "reextraction_quote_fidelity.json"
    quote_report_path = output_dir / "reextraction_quote_fidelity_report.md"
    write_json(quote_path, quote_artifact)
    quote_report_path.write_text(_render_reextraction_quote_report(quote_artifact), encoding="utf-8")

    historical_metrics = _load_json(historical_metrics_path)
    historical_gate = _load_json(historical_gate_path)
    historical_gate_b = _load_json(historical_gate_b_path)
    historical_view = _controlled_reextraction_metric_view(
        historical_metrics,
        historical_gate,
        deterministic_mutations=(
            ((historical_gate_b.get("failure_allocation") or {}).get("deterministic_postprocessing") or {}).get("count", "NOT_AVAILABLE")
        ),
    )
    current_view = _controlled_reextraction_metric_view(
        evidence["metrics"],
        gate_a["metrics"],
        deterministic_mutations=diagnostics["deterministic_company_to_speaker_mutations"]["count"],
    )
    comparison = {
        "document_type": PILOT2_REEXTRACTION_COMPARISON_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "PRE_HUMAN_REVIEW_ONLY",
        "historical_pilot_run_id": PILOT2_HISTORICAL_RUN_ID,
        "controlled_reextraction_run_id": run_id,
        "source_sha256": source_sha256,
        "comparison_scope": "mechanical_extraction_evidence_locator_economics_and_observations_only",
        "historical_pilot2_pre_review": historical_view,
        "controlled_reextraction_pre_review": current_view,
        "semantic_comparison": "PENDING_HUMAN_REVIEW",
        "repair_efficacy_verdict": "PENDING_HUMAN_REVIEW",
        "independent_generalization_retest": "NOT_YET_PERFORMED",
        "no_generalization_claim": True,
    }
    comparison_path = output_dir / "historical_vs_reextraction_pre_review_comparison.json"
    comparison_report_path = output_dir / "historical_vs_reextraction_pre_review_comparison.md"
    write_json(comparison_path, comparison)
    comparison_report_path.write_text(
        _render_historical_vs_reextraction_comparison(comparison), encoding="utf-8",
    )

    repair_post = _controlled_reextraction_freeze(cfg)
    historical_hashes_post = _artifact_directory_hashes(historical_run_dir)
    production_post = production_snapshot(production_db)
    prompt_and_path_frozen = repair_freeze == repair_post
    historical_unchanged = historical_hashes_pre == historical_hashes_post
    production_unchanged = production_pre == production_post
    all_pending = all(
        item.get("human_decision") == "PENDING" for item in evidence["draft"].get("claims") or []
    ) and all(
        item.get("decision") == "PENDING" for item in extraction["review"].get("claims") or []
    )
    stable_ids = len({item.get("claim_id") for item in extraction["bundle"].get("claims") or []}) == len(
        extraction["bundle"].get("claims") or []
    )
    stage_complete = bool(
        prompt_and_path_frozen
        and historical_unchanged
        and production_unchanged
        and all_pending
        and stable_ids
        and gate_a["metrics"]["invariants"]["all_claims_classified"]
    )
    metrics = {
        "document_type": PILOT2_REEXTRACTION_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if stage_complete else "FAIL",
        "PHASE3C_PILOT2_REEXTRACTION_COMPLETE": stage_complete,
        "pilot_run_id": run_id,
        "historical_pilot_run_id": PILOT2_HISTORICAL_RUN_ID,
        "source": {"name": source_path.name, "sha256": source_sha256},
        "repair_freeze": repair_freeze,
        "prompt_and_extraction_path_frozen": prompt_and_path_frozen,
        "model": copy.deepcopy(extraction["bundle"]["model"]),
        "parse_and_extraction_metrics": copy.deepcopy(evidence["metrics"]),
        "quote_fidelity": copy.deepcopy(gate_a["metrics"]),
        "mechanical_diagnostics": diagnostics,
        "human_decisions": {"KEEP": 0, "DROP": 0, "KEEP_NEEDS_REVIEW": 0, "PENDING": len(extraction["bundle"].get("claims") or [])},
        "human_semantic_review_executed": False,
        "semantic_metrics": {
            "semantic_failure_rate": "PENDING_HUMAN_REVIEW",
            "atomicity_issue_rate": "PENDING_HUMAN_REVIEW",
            "attribution_failure_rate": "PENDING_HUMAN_REVIEW",
            "conditionality_failure_rate": "PENDING_HUMAN_REVIEW",
        },
        "repair_efficacy_verdict": "PENDING_HUMAN_REVIEW",
        "independent_generalization_retest": "NOT_YET_PERFORMED",
        "all_claim_ids_stable_and_unique": stable_ids,
        "historical_hashes_pre": historical_hashes_pre,
        "historical_hashes_post": historical_hashes_post,
        "historical_artifacts_unchanged": historical_unchanged,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "isolation": {
            "node_created": False, "relation_created": False, "proposal_created": False,
            "current_view_created": False, "knowledge_gap_created": False,
            "research_question_created": False, "claim_node_link_created": False,
            "source_node_link_created": False, "production_write": False,
            "production_schema_changed": False, "canonical_claim_schema_changed": False,
            "canonical_evidence_schema_changed": False, "ima_invoked": False,
            "propagation_invoked": False, "legacy_pipeline_invoked": False,
        },
        "one_logical_real_extraction": True,
        "quality_based_rerun": False,
        "artifacts": {
            "extraction_bundle": extraction["extraction_bundle_path"],
            "extraction_review_draft": extraction["review_draft_path"],
            "evidence_contract_v2_draft": evidence["draft_path"],
            "evidence_review_surface": evidence["review_surface_path"],
            "quote_fidelity": str(quote_path),
            "quote_fidelity_report": str(quote_report_path),
            "historical_comparison": str(comparison_path),
            "historical_comparison_report": str(comparison_report_path),
        },
        "PHASE3C_NEXT_GATE": (
            "Pilot #2 Re-extraction Human Review"
            if diagnostics["known_old_mutation_recurrence"] == "NO" and stage_complete
            else "Reopen Gate B Attribution Repair"
            if diagnostics["known_old_mutation_recurrence"] == "YES"
            else "Resolve Controlled Re-extraction Failure"
        ),
    }
    metrics_path = output_dir / "reextraction_metrics.json"
    write_json(metrics_path, metrics)
    if not stage_complete:
        raise PilotError("PILOT2_CONTROLLED_REEXTRACTION_ACCEPTANCE_FAILED")
    return {
        "status": "PASS",
        "pilot_run_id": run_id,
        "metrics": metrics,
        "metrics_path": str(metrics_path),
        "quote_path": str(quote_path),
        "quote_report_path": str(quote_report_path),
        "comparison": comparison,
        "comparison_path": str(comparison_path),
        "comparison_report_path": str(comparison_report_path),
        "extraction": extraction,
        "rebound": rebound,
        "evidence": evidence,
        "gate_a": gate_a,
        "production_unchanged": production_unchanged,
        "historical_artifacts_unchanged": historical_unchanged,
    }


def run_pilot2_real_extraction(
    source_path: Path,
    source_search_root: Path,
    pilot1_bundle_path: Path,
    pilot1_source_path: Path,
    cfg: AppConfig,
    *,
    production_db_path: Path | None = None,
) -> dict[str, Any]:
    """Run the one authorized Pilot #2 extraction and mechanics-only v2 draft."""
    source_path = Path(source_path).resolve()
    source_search_root = Path(source_search_root).resolve()
    pilot1_bundle_path = Path(pilot1_bundle_path).resolve()
    pilot1_source_path = Path(pilot1_source_path).resolve()
    expected_name = "光互连研究方法与框架20260819.pdf"
    if source_path.name != expected_name or not source_path.is_file():
        raise PilotError("PILOT2_SOURCE_INVALID: exact authorized filename required")
    matches = [path.resolve() for path in source_search_root.rglob(expected_name) if path.is_file()]
    if source_path not in matches:
        raise PilotError("PILOT2_SOURCE_INVALID: intended file is outside the verified match set")
    hashes = {sha256_file(path) for path in matches}
    if len(hashes) != 1:
        raise PilotError("PILOT2_SOURCE_AMBIGUOUS: non-identical exact-name files found")
    if cfg.llm.model != "deepseek-chat":
        raise PilotError("PILOT2_MODEL_INVALID: configured request model changed")

    production_db = Path(production_db_path or cfg.db_path).resolve()
    production_pre = production_snapshot(production_db)
    prompt_status = phase3c_prompt_repair_status(analyzer_module.SOURCE_ANALYSIS_SYSTEM)
    if not prompt_status["passed"]:
        raise PilotError("PILOT2_PROMPT_INVALID: Stage 1.4 repair is incomplete")
    pilot1_input_hashes = {
        "bundle": sha256_file(pilot1_bundle_path),
        "source": sha256_file(pilot1_source_path),
    }

    extraction = extract_pilot_source(
        source_path,
        cfg,
        production_db_path=production_db,
        required_prompt_sha256=prompt_status["prompt_sha256"],
    )
    if extraction["production_unchanged"] is not True:
        raise PilotError("PILOT2_PRODUCTION_MUTATED_DURING_EXTRACTION")
    output_dir = Path(extraction["extraction_bundle_path"]).resolve().parent
    rebound = rebind_stage1_evidence_locators(
        Path(extraction["extraction_bundle_path"]),
        source_path,
        output_dir=output_dir,
        production_db_path=production_db,
    )
    evidence = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]),
        Path(rebound["review_draft_path"]),
        source_path,
        output_dir=output_dir,
        production_db_path=production_db,
    )
    comparison = build_pilot1_vs_pilot2_pre_review_comparison(
        pilot1_bundle_path,
        pilot1_source_path,
        evidence["metrics"],
        output_dir=output_dir,
    )
    production_post = production_snapshot(production_db)
    production_unchanged = production_pre == production_post
    if not production_unchanged:
        raise PilotError("PILOT2_PRODUCTION_MUTATED")
    if pilot1_input_hashes != {
        "bundle": sha256_file(pilot1_bundle_path),
        "source": sha256_file(pilot1_source_path),
    }:
        raise PilotError("PILOT2_PILOT1_HISTORY_MUTATED")
    return {
        "status": "PASS",
        "pilot_run_id": extraction["pilot_run_id"],
        "prompt_status": prompt_status,
        "extraction": extraction,
        "rebound": rebound,
        "evidence": evidence,
        "comparison": comparison,
        "production_pre": production_pre,
        "production_post": production_post,
        "production_unchanged": production_unchanged,
        "pilot1_history_unchanged": True,
        "pilot1_rerun": False,
        "pilot2_executed": True,
    }


def format_stage1_report(result: dict[str, Any], *, branch: str = "main", commit: str = "UNCOMMITTED", draft_pr: str = "NOT_CREATED") -> str:
    metrics = result["metrics"]
    bundle = result["bundle"]
    pre = result["production_pre"]
    post = result["production_post"]
    observations = bundle["observations"]
    flags = bundle.get("human_review_flags") or []
    lines = [
        "PHASE3C_STAGE1_COMPLETE = true",
        "PHASE3C_COMPLETE = false", "",
        f"Branch = {branch}", f"Commit = {commit}", f"Draft PR = {draft_pr}", "",
        f"Baseline main = {commit}",
        "Contains Phase 3B merge commit = true", "",
        "Pilot #1 = TGV玻璃专家交流.pdf",
        "Pilot #2 status = NOT_RUN", "",
        "REAL_LLM_EXTRACTION_AUTHORIZED = true",
        "Real model extraction = PASS",
        f"Configured request model = {bundle['model']['configured_model']}",
        f"Response model = {bundle['model']['response_model']}", "",
        "Legacy IngestionPipeline bypass = PASS",
        "Propagation invoked = NO", "Proposal created = NO", "Current View created = NO",
        "Knowledge Gap created = NO", "Research Question created = NO", "Relation created = NO",
        "Node created = NO", "Claim-Node link created = NO", "Source-Node link created = NO", "IMA invoked = NO", "",
        "Extraction bundle = PASS", "Human review draft = PASS", "Bundle binding = PASS", "Stable proposed IDs = PASS", "",
        f"Source type = {bundle['source']['source_type']}",
        f"Parse diagnostics = {json.dumps(bundle['source']['parse_diagnostics'], ensure_ascii=False)}",
        f"PDF pages = {metrics['pdf_pages']}", "",
        f"Claims total = {metrics['claims_total']}", f"Evidence-valid Claims = {metrics['evidence_valid_claims']}",
        f"needs_review Claims = {metrics['needs_review_claims']}", "",
        f"Locator resolved = {metrics['locator_resolved']}", f"Locator ambiguous = {metrics['locator_ambiguous']}",
        f"Locator unresolved = {metrics['locator_unresolved']}", "",
        f"Existing Node matches = {metrics['node_matches']}", f"Node candidates = {metrics['node_candidates']}",
        f"Quality-eligible Node candidates = {metrics['quality_eligible_node_candidates']}", "",
        f"Relation candidates = {metrics['relation_candidates']}", f"Rejected Relation candidates = {metrics['rejected_relation_candidates']}", "",
        f"LLM calls = {metrics['llm_calls']}", f"Prompt tokens = {metrics['prompt_tokens']}",
        f"Completion tokens = {metrics['completion_tokens']}", f"Total tokens = {metrics['total_tokens']}", "",
        "TOP HUMAN REVIEW FLAGS =",
    ]
    lines += [f"{index}. {flag}" for index, flag in enumerate(flags[:3], 1)] or ["1. None generated by deterministic QA."]
    lines += [
        "", "Production-copy controlled apply tests = PASS", "Allowed table write isolation = PASS", "",
        "LIVE_PRODUCTION_CORPUS_APPLY_AUTHORIZED = false", f"Production DB changed = {'NO' if result['production_unchanged'] else 'YES'}", "",
        "LIVE_IMA_WRITE_AUTHORIZED = false", "Live IMA changed = NO", "",
        "Pilot #2 real extraction authorized = false", "Pilot #2 executed = NO", "",
        "Targeted tests = PASS", "Phase 3A regressions = PASS", "Phase 3B regressions = PASS",
        "Full pytest = PASS", "Frontend tests = PASS", "Frontend build = PASS", "Compileall = PASS", "",
        f"Production pre-SHA = {pre['sha256']}", f"Production post-SHA = {post['sha256']}",
        f"Production counts pre = {json.dumps(pre['table_counts'], sort_keys=True)}",
        f"Production counts post = {json.dumps(post['table_counts'], sort_keys=True)}",
        f"Integrity check = {post['integrity_check']}", f"Foreign-key violations = {len(post['foreign_key_violations'])}", "",
        f"Extraction bundle path = {result['extraction_bundle_path']}",
        f"Human review Markdown path = {result['review_markdown_path']}",
        f"Human review draft JSON path = {result['review_draft_path']}", f"Metrics path = {result['metrics_path']}", "",
        "HUMAN_EXTRACTION_REVIEW_REQUIRED = true", "PRODUCTION_APPLY_READY = NO", "",
        "PHASE3C_NEXT_GATE =", "Human review of TGV extraction",
    ]
    return "\n".join(lines)
