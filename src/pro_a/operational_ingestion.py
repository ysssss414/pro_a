from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import analyzer as analyzer_module
from .analyzer import Analyzer
from .config import AppConfig, load_config
from .corpus_pilot import (
    BUNDLE_DOCUMENT_TYPE,
    _build_review_draft,
    _human_review_flags,
    _llm_metrics,
    _observations,
    build_pilot2_evidence_support_draft,
    phase3c_evidence_provenance_contract,
    rebind_stage1_evidence_locators,
    run_pilot2_gate_a_quote_fidelity,
)
from .gate_c_quality_hardening import phase3c_prompt_repair_status
from .llm import ChatLLM
from .parsers import ParseError, parse_source_with_diagnostics, semantic_eligible_source_text
from .pipeline import build_claim_record
from .production_authorization import build_operational_node_operation_review
from .production_promotion import (
    _audit_node_operations,
    _audit_relation_operations,
    _evidence_id,
    _immutable_claim_projection,
    canonical_sha256,
    connect_read_only,
    deterministic_id,
    production_identity,
    sha256_file,
)
from .semantic_admission import (
    ADMISSIBLE,
    BLOCKED,
    evaluate_semantic_admission,
    join_permitted_support_regions,
)
from .semantic_decomposition import (
    ChatLLMSemanticBackend,
    SEMANTIC_MAX_OUTPUT_TOKENS,
    SemanticDecomposer,
    build_semantic_claim_inputs,
    semantic_prompt_sha256,
)
from .table_claim_safety import apply_table_claim_safety_boundary_v1, load_pymupdf_word_pages


MANIFEST_DOCUMENT_TYPE = "phase3e_operational_ingestion_manifest"
CLAIM_REVIEW_DOCUMENT_TYPE = "phase3e_claim_review"
PROMOTION_PREVIEW_DOCUMENT_TYPE = "phase3e_non_executable_promotion_preview"
SCHEMA_VERSION = "1"
STAGES = (
    "SOURCE_FROZEN",
    "EXTRACTION_COMPLETE",
    "EVIDENCE_COMPLETE",
    "CLAIM_REVIEW_READY",
    "NODE_REVIEW_READY",
    "PROMOTION_PREVIEW_READY",
)
STOP_AFTER = {
    "source": "SOURCE_FROZEN",
    "extraction": "EXTRACTION_COMPLETE",
    "evidence": "EVIDENCE_COMPLETE",
    "claim-review": "CLAIM_REVIEW_READY",
    "node-review": "NODE_REVIEW_READY",
    "promotion-preview": "PROMOTION_PREVIEW_READY",
}
VALID_FIDELITY_STATUSES = {
    "EXACT_SOURCE_MATCH",
    "LAYOUT_NORMALIZED_EXACT_MATCH",
    "EXACT_ORDERED_CROSS_PAGE_SPAN",
    "PROVENANCE_MISMATCH_RECOVERED",
}


class OperationalIngestionError(RuntimeError):
    """A fail-closed operational ingestion error."""


class CleanSourceGateError(OperationalIngestionError):
    """The input is not eligible for the clean-PDF workflow."""


@dataclass(frozen=True)
class RunPaths:
    root: Path

    @property
    def manifest(self) -> Path:
        return self.root / "run_manifest.json"

    @property
    def frozen_source(self) -> Path:
        manifest = _load_json(self.manifest)
        return self.root / manifest["source"]["frozen_relative_path"]

    def path(self, relative: str) -> Path:
        return self.root / relative


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OperationalIngestionError(f"INVALID_JSON_ARTIFACT:{path.name}:{exc}") from exc
    if not isinstance(value, dict):
        raise OperationalIngestionError(f"JSON_ARTIFACT_NOT_OBJECT:{path.name}")
    return value


def _git_head(repo: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise OperationalIngestionError("REPOSITORY_COMMIT_UNAVAILABLE") from exc


def _production_baseline(path: Path) -> dict[str, Any]:
    identity = production_identity(path)
    return {
        key: copy.deepcopy(identity[key])
        for key in (
            "sha256",
            "schema_version",
            "schema_sha256",
            "counts",
            "sidecars",
            "integrity",
            "foreign_key_violations",
        )
    }


def _source_duplicates(production_path: Path, source_sha256: str) -> list[str]:
    connection = connect_read_only(production_path)
    try:
        return [
            row[0]
            for row in connection.execute(
                "SELECT source_id FROM sources WHERE sha256=? ORDER BY source_id",
                (source_sha256,),
            )
        ]
    finally:
        connection.close()


def _artifact_inventory(run_dir: Path) -> list[dict[str, Any]]:
    inventory = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        if path == run_dir / "run_manifest.json" or path.name.endswith(".tmp"):
            continue
        inventory.append({
            "path": path.relative_to(run_dir).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
    return inventory


def _save_manifest(paths: RunPaths, manifest: dict[str, Any]) -> None:
    _write_json(paths.manifest, manifest)


def _refresh_manifest(paths: RunPaths, manifest: dict[str, Any]) -> None:
    manifest["artifact_inventory"] = _artifact_inventory(paths.root)
    manifest["updated_at"] = _now_iso()
    _save_manifest(paths, manifest)


def _verify_resume(paths: RunPaths, manifest: dict[str, Any]) -> None:
    if manifest.get("document_type") != MANIFEST_DOCUMENT_TYPE:
        raise OperationalIngestionError("RESUME_MANIFEST_DOCUMENT_TYPE_INVALID")
    expected = manifest.get("artifact_inventory") or []
    actual = _artifact_inventory(paths.root)
    if actual != expected:
        raise OperationalIngestionError("RESUME_ARTIFACT_INVENTORY_OR_HASH_MISMATCH")
    source = manifest.get("source") or {}
    frozen = paths.root / str(source.get("frozen_relative_path") or "")
    if not frozen.is_file() or sha256_file(frozen) != source.get("sha256"):
        raise OperationalIngestionError("RESUME_FROZEN_SOURCE_SHA256_MISMATCH")


def _write_stage_receipt(
    paths: RunPaths,
    manifest: Mapping[str, Any],
    stage: str,
    output_paths: Sequence[Path],
) -> Path:
    receipt_path = paths.path(f"receipts/{stage.lower()}.json")
    outputs = [
        {
            "path": path.relative_to(paths.root).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in output_paths
    ]
    _write_json(receipt_path, {
        "document_type": "phase3e_stage_receipt",
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "stage": stage,
        "status": "PASS",
        "outputs": outputs,
        "production_apply_attempted": False,
        "production_write": False,
    })
    return receipt_path


def _complete_stage(
    paths: RunPaths,
    manifest: dict[str, Any],
    stage: str,
    outputs: Sequence[Path],
) -> None:
    receipt = _write_stage_receipt(paths, manifest, stage, outputs)
    completed = manifest.setdefault("completed_stages", [])
    if stage not in completed:
        completed.append(stage)
    manifest["stage_status"] = stage
    manifest.pop("last_error", None)
    _refresh_manifest(paths, manifest)
    if receipt.relative_to(paths.root).as_posix() not in {
        item["path"] for item in manifest["artifact_inventory"]
    }:
        raise OperationalIngestionError("STAGE_RECEIPT_NOT_IN_MANIFEST")


def _record_failure(
    paths: RunPaths,
    manifest: dict[str, Any],
    status: str,
    exc: BaseException,
) -> None:
    piece_context = copy.deepcopy(getattr(exc, "piece_context", None))
    call_metadata = copy.deepcopy(getattr(exc, "call_metadata", None))
    manifest["stage_status"] = status
    manifest["last_error"] = {"type": type(exc).__name__, "message": str(exc)}
    if piece_context:
        manifest["last_error"]["piece_context"] = piece_context
    failure_path = paths.path(f"receipts/{status.lower()}.json")
    failure = {
        "document_type": "phase3e_stage_failure_receipt",
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "status": status,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "production_apply_attempted": False,
        "production_write": False,
    }
    if piece_context:
        failure["piece_context"] = piece_context
    if call_metadata:
        failure["call_metadata"] = call_metadata
    _write_json(failure_path, failure)
    _refresh_manifest(paths, manifest)


class _ReadOnlyAnalyzerDatabase:
    """The subset of Database used by Analyzer, loaded through immutable SQLite."""

    def __init__(self, path: Path):
        connection = connect_read_only(path)
        try:
            nodes = [dict(row) for row in connection.execute(
                "SELECT * FROM nodes ORDER BY primary_type,canonical_name"
            )]
            aliases = [dict(row) for row in connection.execute(
                "SELECT alias,node_id FROM node_aliases ORDER BY alias"
            )]
        finally:
            connection.close()
        aliases_by_node: dict[str, list[str]] = {}
        for alias in aliases:
            aliases_by_node.setdefault(alias["node_id"], []).append(alias["alias"])
        for node in nodes:
            node["aliases"] = aliases_by_node.get(node["node_id"], [])
        self._nodes = nodes
        self._by_id = {node["node_id"]: node for node in nodes}

    def list_nodes(self, limit: int = 1000) -> list[dict[str, Any]]:
        return copy.deepcopy([node for node in self._nodes if node.get("status") == "active"][:limit])

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        node = self._by_id.get(node_id)
        return copy.deepcopy(node) if node is not None else None


def _model_config_identity(cfg: AppConfig) -> dict[str, Any]:
    body = {
        "enabled": cfg.llm.enabled,
        "base_url_sha256": hashlib.sha256(cfg.llm.base_url.encode("utf-8")).hexdigest(),
        "model": cfg.llm.model,
        "temperature": cfg.llm.temperature,
        "max_output_tokens": cfg.llm.max_output_tokens,
        "max_chunk_chars": cfg.llm.max_chunk_chars,
        "max_nodes_in_prompt": cfg.llm.max_nodes_in_prompt,
        "timeout_seconds": cfg.llm.timeout_seconds,
        "max_retries": cfg.llm.max_retries,
        "retry_backoff_seconds": cfg.llm.retry_backoff_seconds,
        "api_key_env_name": cfg.llm.api_key_env,
    }
    return {**body, "identity_sha256": canonical_sha256(body)}


def _clean_pdf_parse(source_path: Path, gate_path: Path) -> Any:
    if source_path.suffix.lower() != ".pdf":
        raise CleanSourceGateError("SUPPORTED_SOURCE_TYPES=CLEAN_PDF")
    try:
        parsed = parse_source_with_diagnostics(source_path, include_semantic_segments=True)
    except (OSError, ParseError) as exc:
        raise CleanSourceGateError(f"CLEAN_SOURCE_PARSE_FAILED:{exc}") from exc
    diagnostics = parsed.diagnostics
    checks = {
        "source_type_pdf": parsed.source_type == "pdf",
        "has_pages": bool(diagnostics.get("total_units")),
        "all_pages_have_text": (
            diagnostics.get("text_units") == diagnostics.get("total_units")
            and diagnostics.get("empty_units") == 0
        ),
        "no_parse_errors": diagnostics.get("error_units") == 0,
        "not_partial": diagnostics.get("partial_parse") is False,
        "not_empty": diagnostics.get("empty_extraction") is False,
        "not_image_only": diagnostics.get("image_only_or_no_extractable_text") is False,
        "layout_sidecar_available": parsed.layout_sidecar is not None,
        "semantic_segments_available": parsed.segments is not None,
    }
    gate = {
        "document_type": "phase3e_clean_source_gate",
        "schema_version": SCHEMA_VERSION,
        "source_sha256": sha256_file(source_path),
        "source_type": parsed.source_type,
        "policy": "CLEAN_PDF_COMPLETE_TEXT_AND_LAYOUT_V1",
        "checks": checks,
        "parse_diagnostics": copy.deepcopy(diagnostics),
        "gate": "PASS" if all(checks.values()) else "DEFER",
    }
    _write_json(gate_path, gate)
    if gate["gate"] != "PASS":
        raise CleanSourceGateError("CLEAN_SOURCE_GATE_FAILED")
    return parsed


def _build_live_extraction(
    *,
    cfg: AppConfig,
    manifest: Mapping[str, Any],
    parsed: Any,
    production_path: Path,
    layout_sidecar_relative: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    semantic_text = semantic_eligible_source_text(parsed)
    analyzer = Analyzer(cfg, _ReadOnlyAnalyzerDatabase(production_path))
    analysis = analyzer.analyze_source(
        manifest["source"]["filename"], semantic_text, "deep"
    )
    raw_responses = copy.deepcopy(analyzer.last_piece_call_records)

    llm = _llm_metrics([item["call_metadata"] for item in raw_responses])
    prompt_status = phase3c_prompt_repair_status(analyzer_module.SOURCE_ANALYSIS_SYSTEM)
    source_id = manifest["source"]["source_id"]
    source_sha = manifest["source"]["sha256"]
    frozen_timestamp = manifest["created_at"]
    claims = []
    for index, claim in enumerate(analysis.claims):
        claim_id = deterministic_id(
            "CLM",
            {
                "source_sha256": source_sha,
                "claim_index": index,
                "claim": {
                    key: value
                    for key, value in claim.items()
                    if not key.startswith("origin_")
                },
            },
        )
        record = build_claim_record(
            claim_id,
            source_id,
            claim,
            analysis.source_metadata.get("publication_time") or "",
            parsed.text,
            ingestion_time=frozen_timestamp,
            created_at=frozen_timestamp,
        )
        if record is None:
            continue
        for key in (
            "origin_chunk_index",
            "origin_split_path",
            "origin_piece_sha256",
            "origin_pieces",
        ):
            if key in claim:
                record[key] = copy.deepcopy(claim[key])
        record["validation"] = copy.deepcopy(record["structured"].get("validation") or {})
        record["phase3c_evidence"] = phase3c_evidence_provenance_contract(
            model_evidence_excerpt=str(record.get("evidence_excerpt") or ""),
            evidence_pointer=str(record.get("evidence_pointer") or ""),
            deterministic_locator=(record.get("validation") or {}).get("source_locator") or {},
        )
        record["claim_index"] = index
        claims.append(record)
    observations = _observations(analysis)
    bundle = {
        "document_type": BUNDLE_DOCUMENT_TYPE,
        "schema_version": "1",
        "status": "EXTRACTED_REVIEW_REQUIRED",
        "pilot_run_id": manifest["run_id"],
        "source": {
            "proposed_source_id": source_id,
            "original_name": manifest["source"]["filename"],
            "sha256": source_sha,
            "source_type": "pdf",
            "analysis_mode": "deep",
            "parse_diagnostics": copy.deepcopy(parsed.diagnostics),
            "parse_warnings": [],
            "layout_sidecar": {
                "path": layout_sidecar_relative,
                "sha256": canonical_sha256(parsed.layout_sidecar),
                "adapter": parsed.layout_sidecar.get("adapter"),
                "adapter_versions": copy.deepcopy(parsed.layout_sidecar.get("adapter_versions") or {}),
                "signature_sha256": parsed.layout_sidecar.get("signature_sha256"),
                "segments": len(parsed.layout_sidecar.get("segments") or []),
            },
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
            "config": _model_config_identity(cfg),
            "prompt": copy.deepcopy(prompt_status),
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
    raw_analysis = {
        "document_type": "phase3e_raw_model_analysis",
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": source_sha,
        "model": copy.deepcopy(bundle["model"]),
        "piece_local_equivalence": {
            "fixture_class": "A",
            "status": "PIECE_LOCAL_PROVENANCE_RECORDED",
            "raw_response_and_exact_piece_available": True,
        },
        "raw_model_responses": raw_responses,
        "normalized_source_analysis": asdict(analysis),
    }
    return raw_analysis, bundle


def _fixture_raw_analysis(
    manifest: Mapping[str, Any], bundle: Mapping[str, Any], fixture_sha256: str
) -> dict[str, Any]:
    return {
        "document_type": "phase3e_frozen_normalized_analysis_replay",
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "fixture_file_sha256": fixture_sha256,
        "llm_invoked": False,
        "piece_local_equivalence": {
            "fixture_class": "B",
            "status": "PIECE_LOCAL_EQUIVALENCE_NOT_DIRECTLY_PROVABLE_FROM_FIXTURE",
            "raw_response_and_exact_piece_available": False,
        },
        "model": copy.deepcopy(bundle.get("model") or {}),
        "normalized_source_analysis": {
            "source_metadata": copy.deepcopy(bundle.get("proposed_source_metadata") or {}),
            "source_references": copy.deepcopy(bundle.get("source_references") or []),
            "claims": copy.deepcopy(bundle.get("claims") or []),
            **copy.deepcopy(bundle.get("observations") or {}),
        },
    }


def _run_extraction(
    paths: RunPaths,
    manifest: dict[str, Any],
    cfg: AppConfig,
    production_path: Path,
) -> list[Path]:
    extraction_dir = paths.path("extraction")
    gate_path = extraction_dir / "clean_source_gate.json"
    parsed = _clean_pdf_parse(paths.frozen_source, gate_path)
    manifest["parser"]["runtime"] = {
        "text_parser": parsed.diagnostics.get("parser"),
        "locator_scheme": parsed.diagnostics.get("locator_scheme"),
        "layout_adapter": (parsed.diagnostics.get("pdf_layout") or {}).get("adapter"),
        "adapter_versions": copy.deepcopy(
            (parsed.diagnostics.get("pdf_layout") or {}).get("adapter_versions") or {}
        ),
    }
    layout_path = extraction_dir / "source_layout_sidecar.json"
    _write_json(layout_path, parsed.layout_sidecar)
    bundle_path = extraction_dir / "extraction_bundle.json"
    raw_path = extraction_dir / "raw_analysis.json"
    fixture_path = extraction_dir / "frozen_extraction_input.json"
    if fixture_path.is_file():
        bundle = _load_json(fixture_path)
        if bundle.get("document_type") != BUNDLE_DOCUMENT_TYPE:
            raise OperationalIngestionError("FROZEN_EXTRACTION_DOCUMENT_TYPE_INVALID")
        source = bundle.get("source") or {}
        if source.get("sha256") != manifest["source"]["sha256"] or source.get("source_type") != "pdf":
            raise OperationalIngestionError("FROZEN_EXTRACTION_SOURCE_BINDING_MISMATCH")
        shutil.copyfile(fixture_path, bundle_path)
        raw_analysis = _fixture_raw_analysis(manifest, bundle, sha256_file(fixture_path))
        manifest["model"]["extraction_mode"] = "FROZEN_NORMALIZED_EXTRACTION_REPLAY"
        manifest["model"]["llm_invoked"] = False
    else:
        raw_analysis, bundle = _build_live_extraction(
            cfg=cfg,
            manifest=manifest,
            parsed=parsed,
            production_path=production_path,
            layout_sidecar_relative="extraction/source_layout_sidecar.json",
        )
        _write_json(bundle_path, bundle)
        manifest["model"]["extraction_mode"] = "CONFIGURED_CLOUD_MODEL"
        manifest["model"]["llm_invoked"] = True
    _write_json(raw_path, raw_analysis)
    review_path = extraction_dir / "extraction_review_draft.json"
    review_id = f"REV_{canonical_sha256(bundle)[:16].upper()}"
    _write_json(review_path, _build_review_draft(bundle, review_id=review_id))
    manifest["model"]["frozen_output_sha256"] = sha256_file(raw_path)
    manifest["model"]["normalized_bundle_sha256"] = sha256_file(bundle_path)
    return [gate_path, layout_path, raw_path, bundle_path, review_path]


def _move_output(source: str, destination: Path) -> Path:
    path = Path(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    path.replace(destination)
    return destination


def _semantic_admission_artifact(
    *,
    manifest: Mapping[str, Any],
    bundle: Mapping[str, Any],
    evidence_draft: Mapping[str, Any],
    gate: Mapping[str, Any],
    table_boundary: Mapping[str, Any],
    proposition_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    proposition_results = proposition_results or {}
    draft_by_id = {item["claim_id"]: item for item in evidence_draft.get("claims") or []}
    gate_by_id = {item["claim_id"]: item for item in gate.get("claims") or []}
    table_by_id = {item["claim_id"]: item for item in table_boundary.get("decisions") or []}
    decisions = []
    for claim in bundle.get("claims") or []:
        claim_id = claim["claim_id"]
        draft = draft_by_id[claim_id]
        quote = gate_by_id[claim_id]
        table = table_by_id[claim_id]
        proposition_result = proposition_results.get(claim_id)
        resolved = quote.get("resolved_locator") or {}
        evidence_bound = bool(
            quote.get("fidelity_status") in VALID_FIDELITY_STATUSES
            and resolved.get("authoritative") is True
        )
        support_text = join_permitted_support_regions(
            text
            for text in [
                str((quote.get("evidence_contract") or {}).get("canonical_ready_evidence") or ""),
                *[
                    str(item.get("text") or "")
                    for item in draft.get("bounded_context_candidates") or []
                ],
                *[
                    str(item.get("text") or "")
                    for item in draft.get("evidence_spans") or []
                ],
            ]
            if text
        )
        guards = evaluate_semantic_admission(
            statement=str(claim.get("statement") or ""),
            attributed_to=str(claim.get("attributed_to") or ""),
            permitted_support_text=support_text,
            support_region_authoritative=evidence_bound,
            support_region_exhaustive=False,
            nature=str(claim.get("nature") or ""),
            fact_time=str(claim.get("fact_time") or ""),
            claim_status=str(claim.get("status") or ""),
            parent_claim_id=claim_id,
            proposition_ir=(
                proposition_result.get("proposition_ir")
                if proposition_result else None
            ),
            proposition_evidence_text=str(
                (quote.get("evidence_contract") or {}).get("canonical_ready_evidence")
                or claim.get("evidence_excerpt")
                or ""
            ),
            proposition_evidence_units=(
                proposition_result.get("evidence_units") or []
                if proposition_result else []
            ),
            proposition_ir_validation=(
                proposition_result.get("validation")
                if proposition_result else None
            ),
        )
        table_eligible = table.get("review_eligible") is True
        proposition_validation_status = (
            (proposition_result or {}).get("validation") or {}
        ).get("status")
        # Preserve the Phase 3C Pilot #6 review universe: table-eligible Claims
        # reach human review even when deterministic Evidence/semantic guards
        # recommend DROP or REVIEW. Admission to review is not acceptance.
        review_admitted = table_eligible
        if not table_eligible:
            recommendation = "DROP"
            reason = "TABLE_DERIVED_CLAIM_INELIGIBLE"
        elif not evidence_bound:
            recommendation = "REVIEW"
            reason = "EVIDENCE_NOT_AUTHORITATIVELY_BOUND"
        elif proposition_result and proposition_validation_status != "VALID":
            recommendation = "REVIEW"
            reason = "INVALID_OR_AMBIGUOUS_PROPOSITION_IR"
        elif guards["overall_guard_disposition"] == BLOCKED:
            recommendation = "DROP"
            reason = ",".join(guards["guard_reasons"]) or "SEMANTIC_ADMISSION_BLOCKED"
        elif guards["overall_guard_disposition"] == ADMISSIBLE:
            recommendation = "KEEP"
            reason = "DETERMINISTIC_GUARDS_ADMISSIBLE"
        else:
            recommendation = "REVIEW"
            reason = ",".join(guards["guard_reasons"]) or "SEMANTIC_REVIEW_REQUIRED"
        decisions.append({
            "claim_id": claim_id,
            "evidence_validation": {
                "fidelity_status": quote.get("fidelity_status"),
                "authoritative_locator": copy.deepcopy(resolved),
                "bound": evidence_bound,
            },
            "table_eligibility": {
                "review_eligible": table_eligible,
                "decision": table.get("eligibility_decision"),
                "reason": table.get("decision_reason"),
            },
            "semantic_admission": guards,
            "review_admitted": review_admitted,
            "recommended_decision": recommendation,
            "recommendation_reason": reason,
            "human_decision": "PENDING",
        })
    counts = Counter(item["semantic_admission"]["overall_guard_disposition"] for item in decisions)
    proposition_validations = [
        item["semantic_admission"]["proposition_ir_validation"] for item in decisions
    ]
    return {
        "document_type": "phase3e_semantic_admission",
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "policy": {
            "deterministic_guard_reused": "pro_a.semantic_admission.evaluate_semantic_admission",
            "guard_result_is_advisory": True,
            "review_admission_preserves_table_eligible_phase3c_universe": True,
            "evidence_and_semantic_failures_remain_visible_as_recommendations": True,
            "proposition_ir_is_supplementary": True,
            "semantic_architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
            "proposition_ir_inside_primary_extraction": False,
            "atomicity_then_nature": True,
            "human_decisions_remain_pending": True,
        },
        "counts": {
            "raw_claims": len(decisions),
            "review_admitted": sum(item["review_admitted"] for item in decisions),
            "guard_dispositions": dict(sorted(counts.items())),
            "proposition_ir": {
                "valid": sum(item["status"] == "VALID" for item in proposition_validations),
                "invalid": sum(item["status"] == "INVALID" for item in proposition_validations),
                "legacy_not_present": sum(
                    item["status"] == "LEGACY_NOT_PRESENT" for item in proposition_validations
                ),
            },
        },
        "decisions": decisions,
    }


def _run_evidence(
    paths: RunPaths,
    manifest: dict[str, Any],
    cfg: AppConfig,
) -> list[Path]:
    bundle_path = paths.path("extraction/extraction_bundle.json")
    extraction_review = paths.path("extraction/extraction_review_draft.json")
    source_path = paths.frozen_source
    evidence_dir = paths.path("evidence")
    rebound = rebind_stage1_evidence_locators(
        bundle_path, source_path, output_dir=evidence_dir
    )
    rebound_path = _move_output(
        rebound["rebound_bundle_path"], evidence_dir / "evidence_bound_extraction_bundle.json"
    )
    rebound_review = _move_output(
        rebound["review_draft_path"], evidence_dir / "evidence_bound_review_draft.json"
    )
    rebound_markdown = _move_output(
        rebound["review_markdown_path"], evidence_dir / "evidence_locator_review.md"
    )
    rebound_metrics = _move_output(
        rebound["metrics_path"], evidence_dir / "evidence_locator_metrics.json"
    )
    evidence_result = build_pilot2_evidence_support_draft(
        rebound_path, rebound_review, source_path, output_dir=evidence_dir
    )
    evidence_binding = _move_output(
        evidence_result["draft_path"], evidence_dir / "evidence_binding.json"
    )
    evidence_markdown = _move_output(
        evidence_result["review_surface_path"], evidence_dir / "evidence_binding.md"
    )
    evidence_metrics = _move_output(
        evidence_result["metrics_path"], evidence_dir / "evidence_binding_metrics.json"
    )
    gate_result = run_pilot2_gate_a_quote_fidelity(
        bundle_path,
        rebound_path,
        evidence_binding,
        source_path,
        output_dir=evidence_dir,
        original_review_path=extraction_review,
    )
    quote_path = _move_output(
        gate_result["gate_a_path"], evidence_dir / "quote_fidelity.json"
    )
    quote_report = _move_output(
        gate_result["report_path"], evidence_dir / "quote_fidelity.md"
    )
    quote_metrics = _move_output(
        gate_result["metrics_path"], evidence_dir / "quote_fidelity_metrics.json"
    )
    quote_surface = _move_output(
        gate_result["review_surface_path"], evidence_dir / "quote_fidelity_review.md"
    )

    bundle = _load_json(rebound_path)
    evidence_draft = _load_json(evidence_binding)
    gate = _load_json(quote_path)
    gate_by_id = {item["claim_id"]: item for item in gate.get("claims") or []}
    boundary_claims = copy.deepcopy(bundle.get("claims") or [])
    for claim in boundary_claims:
        gate_claim = gate_by_id[claim["claim_id"]]
        claim["phase3c_evidence"] = copy.deepcopy(gate_claim["evidence_contract"])
        validation = copy.deepcopy(claim.get("validation") or {})
        validation["source_locator"] = copy.deepcopy(gate_claim["gate_a_source_locator"])
        claim["validation"] = validation
    authoritative_pages = sorted({
        int(resolved["locator"].split(":", 1)[1])
        for claim in boundary_claims
        for resolved in [((claim.get("phase3c_evidence") or {}).get("resolved_locator") or {})]
        if resolved.get("kind") == "single_page" and resolved.get("locator")
    })
    parsed = parse_source_with_diagnostics(source_path)
    layout_sidecar = _load_json(paths.path("extraction/source_layout_sidecar.json"))
    table_result = apply_table_claim_safety_boundary_v1(
        canonical_source_text=parsed.text,
        layout_sidecar=layout_sidecar,
        claims=boundary_claims,
        word_pages=load_pymupdf_word_pages(source_path, authoritative_pages),
    )
    table_path = evidence_dir / "table_claim_safety.json"
    _write_json(table_path, {
        "document_type": "phase3e_table_claim_safety",
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "gate": "PASS" if table_result["raw_claims_unchanged"] else "FAIL",
        "result": table_result,
    })
    semantic_decomposition_path = evidence_dir / "semantic_decomposition.json"
    semantic_llm = ChatLLM(replace(
        cfg.llm,
        max_output_tokens=min(
            cfg.llm.max_output_tokens,
            SEMANTIC_MAX_OUTPUT_TOKENS,
        ),
    ))
    proposition_results: dict[str, Mapping[str, Any]] = {}
    if semantic_llm.available:
        semantic_inputs = build_semantic_claim_inputs(
            bundle=bundle,
            evidence_draft=evidence_draft,
            quote_fidelity=gate,
        )
        decomposition = SemanticDecomposer(
            ChatLLMSemanticBackend(semantic_llm),
            batch_size=8,
        ).run(semantic_inputs)
        proposition_results = {
            item["parent_claim_id"]: item
            for item in decomposition["results"]
        }
        manifest["semantic_model"] = {
            "stage": "POST_EXTRACTION",
            "prompt_sha256": semantic_prompt_sha256(),
            "backend": decomposition["backend"],
            "llm_calls": decomposition["semantic_llm_calls"],
            "length_retries": decomposition["semantic_length_retries"],
            "usage": copy.deepcopy(decomposition["usage"]),
            "parent_claim_universe_stable": (
                decomposition["input_parent_claim_ids"]
                == decomposition["output_parent_claim_ids"]
            ),
        }
    else:
        decomposition = {
            "document_type": "phase3e2se_post_extraction_semantic_decomposition",
            "schema_version": "1.0",
            "architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
            "status": "SKIPPED_LLM_UNAVAILABLE",
            "proposition_ir_inside_primary_extraction": False,
            "primary_extraction_claims_mutated": False,
            "results": [],
        }
        manifest["semantic_model"] = {
            "stage": "POST_EXTRACTION",
            "status": "SKIPPED_LLM_UNAVAILABLE",
            "llm_calls": 0,
        }
    _write_json(semantic_decomposition_path, decomposition)
    semantic_path = evidence_dir / "semantic_admission.json"
    _write_json(semantic_path, _semantic_admission_artifact(
        manifest=manifest,
        bundle=bundle,
        evidence_draft=evidence_draft,
        gate=gate,
        table_boundary=table_result,
        proposition_results=proposition_results,
    ))
    return [
        rebound_path,
        rebound_review,
        rebound_markdown,
        rebound_metrics,
        evidence_binding,
        evidence_markdown,
        evidence_metrics,
        quote_path,
        quote_report,
        quote_metrics,
        quote_surface,
        table_path,
        semantic_decomposition_path,
        semantic_path,
    ]


def _render_claim_review(review: Mapping[str, Any]) -> str:
    metrics = review["metrics"]
    lines = [
        "# Operational Claim Review",
        "",
        "> Human decisions are PENDING. Recommendations are advisory and do not authorize Production.",
        "",
        f"- Raw Claims: {metrics['raw_claims']}",
        f"- Review-admitted Claims: {metrics['review_admitted']}",
        f"- Table-ineligible Claims: {metrics['table_ineligible']}",
        "",
        "| Claim ID | Statement | Evidence | Evidence validation | Table | Semantic | Recommendation | Human |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for record in review["claims"]:
        clean = lambda value: str(value or "").replace("|", "\\|").replace("\n", " ")
        excerpt = clean(record["evidence_excerpt"])
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."
        lines.append(
            f"| `{record['claim_id']}` | {clean(record['statement'])} | {excerpt} | "
            f"{record['evidence_validation']['fidelity_status']} | "
            f"{'ELIGIBLE' if record['table_eligibility']['review_eligible'] else 'INELIGIBLE'} | "
            f"{record['semantic_admission']['overall_guard_disposition']} | "
            f"**{record['recommended_decision']}** | PENDING |"
        )
    lines.extend(["", "No human decision, payload authorization, or Production mutation was performed.", ""])
    return "\n".join(lines)


def _run_claim_review(paths: RunPaths, manifest: Mapping[str, Any]) -> list[Path]:
    bundle = _load_json(paths.path("evidence/evidence_bound_extraction_bundle.json"))
    semantic = _load_json(paths.path("evidence/semantic_admission.json"))
    decision_by_id = {item["claim_id"]: item for item in semantic["decisions"]}
    records = []
    for claim in bundle.get("claims") or []:
        decision = decision_by_id[claim["claim_id"]]
        records.append({
            "claim_id": claim["claim_id"],
            "statement": claim.get("statement") or "",
            "evidence_pointer": claim.get("evidence_pointer") or "",
            "evidence_excerpt": claim.get("evidence_excerpt") or "",
            **copy.deepcopy(decision),
        })
    recommendations = Counter(item["recommended_decision"] for item in records)
    review = {
        "document_type": CLAIM_REVIEW_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "review_status": "DRAFT",
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "metrics": {
            "raw_claims": len(records),
            "table_ineligible": sum(
                not item["table_eligibility"]["review_eligible"] for item in records
            ),
            "review_admitted": sum(item["review_admitted"] for item in records),
            "recommendations": {
                key: recommendations.get(key, 0) for key in ("KEEP", "DROP", "REVIEW")
            },
            "human_pending": len(records),
        },
        "claims": records,
        "authorization": {
            "human_decisions_bound": False,
            "production_apply_authorized": False,
        },
    }
    body_hash = canonical_sha256(review)
    review["review_id"] = f"CLAIM_REVIEW_{body_hash[:16].upper()}"
    review["review_sha256"] = body_hash
    json_path = paths.path("review/claim_review.json")
    markdown_path = paths.path("review/claim_review.md")
    _write_json(json_path, review)
    markdown_path.write_text(_render_claim_review(review), encoding="utf-8")
    return [json_path, markdown_path]


def _render_node_review(review: Mapping[str, Any]) -> str:
    lines = [
        "# Operational Node Operation Review",
        "",
        "> Deterministic suggestions are advisory. Every human decision is PENDING.",
        "",
        f"- Candidate universe: {review['review_universe']['observed']}",
        f"- Supporting review-admitted Claims: {review['review_universe']['admitted_claims']}",
        f"- Relation observations excluded: {review['relation_audit']['observed']}",
        "",
        "| Candidate ID | Name | Type | Aliases | Claims | Exact targets | Node suggestion | Parent placement | Reason | Human |",
        "|---|---|---|---|---:|---|---|---|---|---|",
    ]
    for record in review["records"]:
        clean = lambda value: str(value or "").replace("|", "\\|").replace("\n", " ")
        resolution = record["exact_production_resolution"]
        parent_placement = record.get("parent_placement_suggestion") or {}
        parent_ids = parent_placement.get("suggested_parent_node_ids") or []
        parent_text = (
            "PARENT PLACEMENT SUGGESTION: "
            f"{clean(', '.join(parent_ids))}; SEPARATE HUMAN REVIEW REQUIRED; "
            "NOT AUTHORIZED BY NODE CREATE"
            if parent_ids else "None"
        )
        lines.append(
            f"| `{record['operation_candidate_id']}` | {clean(record['proposed_name'])} | "
            f"{clean(record['proposed_type'])} | {clean(', '.join(record['proposed_aliases']))} | "
            f"{len(record['supporting_claim_ids'])} | "
            f"{clean(', '.join(resolution['exact_target_node_ids'])) or 'None'} | "
            f"**{record['suggested_operation']}** | {parent_text} | "
            f"{clean(record['suggestion_reason'])} | PENDING |"
        )
    lines.extend([
        "",
        "Parent placement suggestions require separate human review and are not authorized by Node CREATE.",
        "Evidence-backed semantic Relations remain audit-only and are excluded from this promotion preview.",
        "No Node or Relation mutation was authorized or attempted.",
        "",
    ])
    return "\n".join(lines)


def _run_node_review(
    paths: RunPaths,
    manifest: Mapping[str, Any],
    production_path: Path,
) -> list[Path]:
    bundle = _load_json(paths.path("evidence/evidence_bound_extraction_bundle.json"))
    claim_review_path = paths.path("review/claim_review.json")
    claim_review = _load_json(claim_review_path)
    admitted_ids = {
        item["claim_id"] for item in claim_review["claims"] if item["review_admitted"]
    }
    admitted_claims = [
        claim for claim in bundle.get("claims") or [] if claim["claim_id"] in admitted_ids
    ]
    evidence_by_claim = {
        claim["claim_id"]: _evidence_id(manifest["source"]["sha256"], claim)
        for claim in admitted_claims
    }
    converged = {
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "bundle": bundle,
    }
    node_operations = _audit_node_operations(converged, admitted_claims, evidence_by_claim)
    relation_operations = _audit_relation_operations(converged)
    review_claims = [
        {
            "claim_id": claim["claim_id"],
            "evidence_id": evidence_by_claim[claim["claim_id"]],
            "immutable_projection": _immutable_claim_projection(claim),
        }
        for claim in admitted_claims
    ]
    review = build_operational_node_operation_review(
        run_id=manifest["run_id"],
        source_sha256=manifest["source"]["sha256"],
        claim_review_sha256=sha256_file(claim_review_path),
        claims=review_claims,
        node_operations=node_operations,
        relation_operations=relation_operations,
        production_path=production_path,
        table_ineligible_claims=claim_review["metrics"]["table_ineligible"],
    )
    json_path = paths.path("review/node_operation_review.json")
    markdown_path = paths.path("review/node_operation_review.md")
    _write_json(json_path, review)
    markdown_path.write_text(_render_node_review(review), encoding="utf-8")
    return [json_path, markdown_path]


def _existing_claim_ids(production_path: Path, claim_ids: Sequence[str]) -> set[str]:
    if not claim_ids:
        return set()
    placeholders = ",".join("?" for _ in claim_ids)
    connection = connect_read_only(production_path)
    try:
        return {
            row[0]
            for row in connection.execute(
                f"SELECT claim_id FROM claims WHERE claim_id IN ({placeholders})",
                tuple(claim_ids),
            )
        }
    finally:
        connection.close()


def _render_promotion_preview(preview: Mapping[str, Any]) -> str:
    summary = preview["summary"]
    return "\n".join([
        "# Operational Promotion Preview",
        "",
        "> NON-EXECUTABLE. Human review and separate Production authorization are required.",
        "",
        f"- Source suggestion: {summary['source_suggestion']}",
        f"- Claim CREATE candidates: {summary['claim_create_candidates']}",
        f"- Claim collisions deferred: {summary['claim_collisions_deferred']}",
        f"- Node REUSE suggestions: {summary['node_reuse_suggestions']}",
        f"- Node CREATE suggestions: {summary['node_create_suggestions']}",
        f"- Node DEFER suggestions: {summary['node_defer_suggestions']}",
        f"- Parent placement suggestions (separate review): {summary['parent_placement_suggestions']}",
        f"- Relations excluded: {summary['relations_excluded']}",
        "",
        "EXECUTABLE = false",
        "PRODUCTION_APPLY_AUTHORIZED = false",
        "",
    ])


def _run_promotion_preview(
    paths: RunPaths,
    manifest: Mapping[str, Any],
    production_path: Path,
) -> list[Path]:
    claim_review_path = paths.path("review/claim_review.json")
    node_review_path = paths.path("review/node_operation_review.json")
    claim_review = _load_json(claim_review_path)
    node_review = _load_json(node_review_path)
    admitted = [item for item in claim_review["claims"] if item["review_admitted"]]
    existing_claim_ids = _existing_claim_ids(
        production_path, [item["claim_id"] for item in admitted]
    )
    source_duplicates = _source_duplicates(production_path, manifest["source"]["sha256"])
    claim_candidates = [
        {
            "claim_id": item["claim_id"],
            "suggested_operation": (
                "DEFER" if item["claim_id"] in existing_claim_ids else "CREATE"
            ),
            "reason": (
                "PRODUCTION_CLAIM_ID_COLLISION"
                if item["claim_id"] in existing_claim_ids
                else "REVIEW_ADMITTED_PENDING_HUMAN_DECISION"
            ),
            "human_decision": "PENDING",
            "executable": False,
        }
        for item in admitted
    ]
    node_counts = node_review["suggestion_counts"]
    relations = node_review["audit_operations"]["relations"]
    parent_placement_suggestions = [
        {
            "suggestion_id": deterministic_id(
                "PARENT_PLACEMENT",
                {
                    "candidate_id": record["operation_candidate_id"],
                    "parent_node_id": parent_node_id,
                },
            ),
            "candidate_id": record["operation_candidate_id"],
            "prospective_child_node_id": record["prospective_node_id"],
            "parent_node_id": parent_node_id,
            "suggestion_type": "PARENT_PLACEMENT_SUGGESTION",
            "governance_status": "SEPARATE_HUMAN_REVIEW_REQUIRED",
            "authorized_by_node_create": False,
            "human_decision": "PENDING",
            "executable": False,
        }
        for record in node_review["records"]
        for parent_node_id in (
            (record.get("parent_placement_suggestion") or {}).get(
                "suggested_parent_node_ids"
            ) or []
        )
    ]
    body = {
        "document_type": PROMOTION_PREVIEW_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "source_sha256": manifest["source"]["sha256"],
        "bindings": {
            "claim_review_sha256": sha256_file(claim_review_path),
            "node_review_sha256": sha256_file(node_review_path),
            "production_baseline": copy.deepcopy(manifest["production_baseline"]),
        },
        "source": {
            "source_id": manifest["source"]["source_id"],
            "suggested_operation": "REUSE" if source_duplicates else "CREATE",
            "existing_source_ids": source_duplicates,
            "human_decision": "PENDING",
            "executable": False,
        },
        "claim_candidates": claim_candidates,
        "node_suggestions": [
            {
                "candidate_id": record["operation_candidate_id"],
                "suggested_operation": record["suggested_operation"],
                "suggestion_reason": record["suggestion_reason"],
                "human_decision": "PENDING",
                "executable": False,
            }
            for record in node_review["records"]
        ],
        "parent_placement_suggestions": parent_placement_suggestions,
        "relations": {
            "observations": relations,
            "excluded_from_promotion": True,
            "schema_migration_attempted": False,
        },
        "summary": {
            "source_suggestion": "REUSE" if source_duplicates else "CREATE",
            "claim_create_candidates": sum(
                item["suggested_operation"] == "CREATE" for item in claim_candidates
            ),
            "claim_collisions_deferred": sum(
                item["suggested_operation"] == "DEFER" for item in claim_candidates
            ),
            "node_reuse_suggestions": node_counts.get("REUSE", 0),
            "node_create_suggestions": node_counts.get("CREATE", 0),
            "node_defer_suggestions": node_counts.get("DEFER", 0),
            "node_reject_suggestions": node_counts.get("REJECT", 0),
            "parent_placement_suggestions": len(parent_placement_suggestions),
            "relations_excluded": len(relations),
        },
        "authorization": {
            "human_claim_decisions_bound": False,
            "human_node_decisions_bound": False,
            "executable": False,
            "production_apply_authorized": False,
            "production_executor_compatible": False,
            "intended_mutations_generated": False,
        },
    }
    digest = canonical_sha256(body)
    preview = {
        **body,
        "preview_id": f"PROMOTION_PREVIEW_{digest[:16].upper()}",
        "preview_sha256": digest,
    }
    json_path = paths.path("promotion/promotion_preview.json")
    markdown_path = paths.path("promotion/promotion_summary.md")
    _write_json(json_path, preview)
    markdown_path.write_text(_render_promotion_preview(preview), encoding="utf-8")
    return [json_path, markdown_path]


def _start_new_run(
    *,
    source_path: Path,
    config: AppConfig,
    run_dir: Path | None,
    frozen_extraction_path: Path | None,
) -> tuple[RunPaths, dict[str, Any]]:
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise OperationalIngestionError(f"SOURCE_NOT_FOUND:{source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise CleanSourceGateError("SUPPORTED_SOURCE_TYPES=CLEAN_PDF")
    source_sha = sha256_file(source_path)
    run_id = f"INGEST_{source_sha[:16].upper()}"
    root = Path(run_dir or (config.root / "ingestion" / run_id)).resolve()
    repo = Path(__file__).resolve().parents[2]
    if root.is_relative_to(repo) and not root.is_relative_to(config.root.resolve()):
        raise OperationalIngestionError("RUN_DIR_MUST_BE_OUTSIDE_GIT_OR_UNDER_CONFIGURED_WORKSPACE")
    if root.exists() and any(root.iterdir()):
        raise OperationalIngestionError(f"RUN_ALREADY_EXISTS_USE_RESUME:{root}")
    paths = RunPaths(root)
    for relative in ("source", "extraction", "evidence", "review", "promotion", "receipts"):
        paths.path(relative).mkdir(parents=True, exist_ok=True)
    frozen_source = paths.path(f"source/{source_path.name}")
    shutil.copyfile(source_path, frozen_source)
    if sha256_file(frozen_source) != source_sha:
        raise OperationalIngestionError("SOURCE_FREEZE_SHA256_MISMATCH")

    source_id = deterministic_id("SRC", {"source_sha256": source_sha})
    fixture_sha = None
    if frozen_extraction_path is not None:
        frozen_extraction_path = frozen_extraction_path.resolve()
        if not frozen_extraction_path.is_file():
            raise OperationalIngestionError("FROZEN_EXTRACTION_NOT_FOUND")
        fixture = _load_json(frozen_extraction_path)
        fixture_source = fixture.get("source") or {}
        if fixture_source.get("sha256") != source_sha:
            raise OperationalIngestionError("FROZEN_EXTRACTION_SOURCE_SHA256_MISMATCH")
        if fixture_source.get("proposed_source_id"):
            source_id = fixture_source["proposed_source_id"]
        fixture_copy = paths.path("extraction/frozen_extraction_input.json")
        shutil.copyfile(frozen_extraction_path, fixture_copy)
        fixture_sha = sha256_file(fixture_copy)
        if fixture_sha != sha256_file(frozen_extraction_path):
            raise OperationalIngestionError("FROZEN_EXTRACTION_COPY_SHA256_MISMATCH")

    production_path = config.db_path.resolve()
    baseline = _production_baseline(production_path)
    prompt = phase3c_prompt_repair_status(analyzer_module.SOURCE_ANALYSIS_SYSTEM)
    manifest = {
        "document_type": MANIFEST_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "source": {
            "source_id": source_id,
            "filename": source_path.name,
            "sha256": source_sha,
            "size_bytes": frozen_source.stat().st_size,
            "source_type": "CLEAN_PDF",
            "frozen_relative_path": frozen_source.relative_to(root).as_posix(),
            "frozen_copy_sha256": sha256_file(frozen_source),
            "existing_production_source_ids": _source_duplicates(production_path, source_sha),
        },
        "parser": {
            "policy": "CLEAN_PDF_COMPLETE_TEXT_AND_LAYOUT_V1",
            "semantic_policy": "NARRATIVE_FIRST_TABLE_SUPPRESSION",
            "implementation_sha256": sha256_file(Path(__file__).with_name("parsers.py")),
        },
        "repository_commit": _git_head(repo),
        "production_baseline": baseline,
        "model": {
            "configured": _model_config_identity(config),
            "prompt_identity": prompt,
            "frozen_extraction_input_sha256": fixture_sha,
            "llm_invoked": False,
        },
        "stage_status": "SOURCE_FROZEN",
        "completed_stages": [],
        "artifact_inventory": [],
        "production_safety": {
            "read_only_access": True,
            "database_init_schema_called": False,
            "backup_created": False,
            "archive_materialized": False,
            "production_apply_attempted": False,
            "production_write_path_enabled": False,
            "production_changed": False,
        },
    }
    _save_manifest(paths, manifest)
    _complete_stage(
        paths,
        manifest,
        "SOURCE_FROZEN",
        [frozen_source, *([paths.path("extraction/frozen_extraction_input.json")] if fixture_sha else [])],
    )
    return paths, manifest


def _resume_run(
    *,
    run_dir: Path,
    source_path: Path | None,
    config: AppConfig,
) -> tuple[RunPaths, dict[str, Any]]:
    paths = RunPaths(run_dir.resolve())
    repo = Path(__file__).resolve().parents[2]
    if paths.root.is_relative_to(repo) and not paths.root.is_relative_to(config.root.resolve()):
        raise OperationalIngestionError("RUN_DIR_MUST_BE_OUTSIDE_GIT_OR_UNDER_CONFIGURED_WORKSPACE")
    if not paths.manifest.is_file():
        raise OperationalIngestionError("RESUME_MANIFEST_MISSING")
    manifest = _load_json(paths.manifest)
    _verify_resume(paths, manifest)
    if source_path is not None:
        source_path = source_path.resolve()
        if not source_path.is_file() or sha256_file(source_path) != manifest["source"]["sha256"]:
            raise OperationalIngestionError("RESUME_EXTERNAL_SOURCE_SHA256_MISMATCH")
    current = _production_baseline(config.db_path.resolve())
    if current != manifest.get("production_baseline"):
        raise OperationalIngestionError("RESUME_PRODUCTION_BASELINE_CHANGED")
    return paths, manifest


def _result(paths: RunPaths, manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "run_status": manifest["stage_status"],
        "run_dir": str(paths.root),
        "manifest": str(paths.manifest),
        "claim_review": str(paths.path("review/claim_review.json")),
        "node_review": str(paths.path("review/node_operation_review.json")),
        "promotion_preview": str(paths.path("promotion/promotion_preview.json")),
        "production_changed": manifest["production_safety"]["production_changed"],
        "production_apply_attempted": False,
    }


def run_operational_ingestion(
    source_path: Path | None = None,
    *,
    config_path: Path = Path("config.toml"),
    run_dir: Path | None = None,
    resume: bool = False,
    stop_after: str | None = None,
    frozen_extraction_path: Path | None = None,
) -> dict[str, Any]:
    """Run or resume the clean-PDF workflow through a non-executable preview."""
    if stop_after is not None and stop_after not in STOP_AFTER:
        raise OperationalIngestionError(f"STOP_AFTER_INVALID:{stop_after}")
    cfg = load_config(config_path)
    if resume:
        if run_dir is None:
            if source_path is None or not Path(source_path).is_file():
                raise OperationalIngestionError("RESUME_REQUIRES_RUN_DIR_OR_SOURCE")
            source_sha = sha256_file(Path(source_path))
            run_dir = cfg.root / "ingestion" / f"INGEST_{source_sha[:16].upper()}"
        paths, manifest = _resume_run(
            run_dir=Path(run_dir), source_path=Path(source_path) if source_path else None, config=cfg
        )
    else:
        if source_path is None:
            raise OperationalIngestionError("SOURCE_REQUIRED")
        paths, manifest = _start_new_run(
            source_path=Path(source_path),
            config=cfg,
            run_dir=Path(run_dir) if run_dir else None,
            frozen_extraction_path=(
                Path(frozen_extraction_path) if frozen_extraction_path else None
            ),
        )
    production_path = cfg.db_path.resolve()
    fixture_replay = paths.path("extraction/frozen_extraction_input.json").is_file()
    if manifest["source"]["existing_production_source_ids"] and not fixture_replay:
        exc = OperationalIngestionError("SOURCE_ALREADY_EXISTS_IN_PRODUCTION")
        _record_failure(paths, manifest, "SOURCE_REJECTED", exc)
        raise exc
    if stop_after and STOP_AFTER[stop_after] in manifest.get("completed_stages", []):
        return _result(paths, manifest)

    stage_specs = (
        (
            "EXTRACTION_COMPLETE",
            "EXTRACTION_FAILED",
            lambda: _run_extraction(paths, manifest, cfg, production_path),
        ),
        (
            "EVIDENCE_COMPLETE",
            "EVIDENCE_FAILED",
            lambda: _run_evidence(paths, manifest, cfg),
        ),
        (
            "CLAIM_REVIEW_READY",
            "REVIEW_BLOCKED",
            lambda: _run_claim_review(paths, manifest),
        ),
        (
            "NODE_REVIEW_READY",
            "REVIEW_BLOCKED",
            lambda: _run_node_review(paths, manifest, production_path),
        ),
        (
            "PROMOTION_PREVIEW_READY",
            "REVIEW_BLOCKED",
            lambda: _run_promotion_preview(paths, manifest, production_path),
        ),
    )
    for stage, failure_status, action in stage_specs:
        if stage in manifest.get("completed_stages", []):
            if stop_after and STOP_AFTER[stop_after] == stage:
                return _result(paths, manifest)
            continue
        try:
            outputs = action()
            _complete_stage(paths, manifest, stage, outputs)
        except CleanSourceGateError as exc:
            _record_failure(paths, manifest, "CLEAN_SOURCE_GATE_FAILED", exc)
            raise
        except Exception as exc:
            _record_failure(paths, manifest, failure_status, exc)
            raise
        if stop_after and STOP_AFTER[stop_after] == stage:
            return _result(paths, manifest)

    production_post = _production_baseline(production_path)
    if production_post != manifest["production_baseline"]:
        exc = OperationalIngestionError("PRODUCTION_CHANGED_DURING_OPERATIONAL_INGESTION")
        _record_failure(paths, manifest, "REVIEW_BLOCKED", exc)
        raise exc
    manifest["stage_status"] = "HUMAN_REVIEW_REQUIRED"
    manifest["production_safety"]["production_changed"] = False
    manifest["production_safety"]["production_post"] = production_post
    _refresh_manifest(paths, manifest)
    return _result(paths, manifest)
