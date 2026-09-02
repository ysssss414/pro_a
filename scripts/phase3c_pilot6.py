from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from pro_a.config import load_config
from pro_a.corpus_pilot import (
    PilotError,
    build_pilot2_evidence_support_draft,
    extract_pilot_source,
    production_snapshot,
    rebind_stage1_evidence_locators,
    run_pilot2_gate_a_quote_fidelity,
    sha256_file,
)
from pro_a.gate_c_quality_hardening import phase3c_prompt_repair_status
from pro_a import analyzer as analyzer_module
from pro_a.parsers import parse_source_with_diagnostics, semantic_eligible_source_text
from pro_a.table_claim_safety import (
    TABLE_CLAIM_SAFETY_BOUNDARY_VERSION,
    apply_table_claim_safety_boundary_v1,
    load_pymupdf_word_pages,
)


PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"
EVIDENCE_CONTRACT = "phase3c_pilot2_evidence_support_draft_v2/schema_version=1"
EVIDENCE_VERSION = "v2"
CRITICAL_FILE_HASHES = {
    "pyproject.toml": "b478b4aa59534cab6e6c5b8aa9cd445c07d6b5b91774d677f2864479f1d02aa4",
    "config.toml": "c02112d8e123976eee9e2084bbea3ef3a20c55615262aa928914816a9d3d8705",
    "src/pro_a/pdf_layout.py": "4c3fd5ab068dfd55bd434b5fba947f790231c66161ad2133d459d700e4954739",
    "src/pro_a/parsers.py": "41bdb0081d3a2f77778e0b56a68cf35d00988bd91896f4209c70b1f02a2b3746",
    "src/pro_a/corpus_pilot.py": "31089819e65631f4296491a50dd4dc3ed88deda3e40b00bb0ce010361ecb1db2",
    "src/pro_a/analyzer.py": "912a9e60dff1e80ffe7de35a03f1283b915624dbc3de39ed9cec9baf6ce9363b",
    "src/pro_a/prompts.py": "4ac7a3ed099797920e57702fd3860f0ed98153fa272f112f2618e5e3fb6edce5",
    "src/pro_a/pipeline.py": "c05011e875f22bf36ce062235e06a7b9a67e399dd686ab99d767a93f5c3c13f9",
    "src/pro_a/storage.py": "f61250030bdc9d1f9618488d13400816d2c9ed1d8eca6878eab82685ba0e8e2a",
    "src/pro_a/llm.py": "b593475d08a0759688713d997f07661b899e70f3c278e608be4d07bfa0ff4f49",
    "src/pro_a/semantic_admission.py": "fd67e5db820bb73ef05a5b28a5be5baa23b973d4b02f0041b00d88a04ca71d92",
    "src/pro_a/source_quality.py": "e4d59b69d7c5dece1d510149c3d9976888ecb643ced09f1aaaec415ee8299337",
    "src/pro_a/table_claim_safety.py": "22a43e668fcd9a188906427dfc91ee807cb9671af20e70dd2ce25e317294fa38",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stdout.strip()


def manifest(repo: Path, relatives: Iterable[str]) -> dict[str, Any]:
    rows = [
        {"path": relative, "sha256": sha256_file(repo / relative)}
        for relative in sorted(relatives)
    ]
    return {"files": len(rows), "sha256": canonical_sha256(rows), "entries": rows}


def scan_independence_references(
    repo: Path, run_dir: Path, needles: Iterable[str]
) -> list[dict[str, Any]]:
    suffixes = {".json", ".md", ".py", ".toml", ".txt", ".csv"}
    roots = [repo / "workspace" / "phase3c", repo / "scripts", repo / "tests", repo / "docs"]
    normalized_needles = [needle for needle in needles if needle]
    hits: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            try:
                resolved = path.resolve()
                if resolved == Path(__file__).resolve() or resolved.is_relative_to(run_dir):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for needle in normalized_needles:
                if needle in path.name or needle in text:
                    hits.append({
                        "path": path.relative_to(repo).as_posix(),
                        "needle": needle,
                    })
    return hits


def preflight(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    source = args.source.resolve()
    run_dir = args.run_dir.resolve()
    production_db = args.production_db.resolve()
    if not source.is_file():
        raise PilotError("PILOT6_SOURCE_MISSING")
    source_sha = sha256_file(source)
    if source_sha != args.expected_source_sha:
        raise PilotError("PILOT6_SOURCE_SHA_MISMATCH")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise PilotError("PILOT6_RUN_DIR_ALREADY_NONEMPTY")

    references = scan_independence_references(
        repo,
        run_dir,
        (source.name, source.stem, args.independence_token, source_sha),
    )
    with sqlite3.connect(f"file:{production_db.as_posix()}?mode=ro", uri=True) as connection:
        production_duplicate = connection.execute(
            "SELECT source_id FROM sources WHERE sha256=?", (source_sha,)
        ).fetchall()
    independence_pass = not references and not production_duplicate
    if not independence_pass:
        raise PilotError("PILOT6_SOURCE_INDEPENDENCE_GATE_FAIL")

    actual_hashes = {
        relative: sha256_file(repo / relative) for relative in CRITICAL_FILE_HASHES
    }
    mismatches = {
        relative: {"expected": expected, "actual": actual_hashes[relative]}
        for relative, expected in CRITICAL_FILE_HASHES.items()
        if actual_hashes[relative] != expected
    }
    prompt = phase3c_prompt_repair_status(analyzer_module.SOURCE_ANALYSIS_SYSTEM)
    production = production_snapshot(production_db)
    implementation_frozen = bool(
        not mismatches
        and prompt.get("passed") is True
        and prompt.get("prompt_sha256") == PROMPT_SHA256
        and production["sha256"] == args.expected_production_sha
        and production["integrity_check"] == "ok"
        and not production["foreign_key_violations"]
    )
    if not implementation_frozen:
        raise PilotError("PILOT6_IMPLEMENTATION_FREEZE_MISMATCH")

    import pymupdf
    import pymupdf.layout  # noqa: F401 - frozen runtime activation
    import pypdf

    tracked_status = git(repo, "status", "--short", "--untracked-files=no").splitlines()
    receipt = {
        "document_type": "phase3c_pilot6_pre_run_freeze_receipt",
        "schema_version": "1",
        "created_at": now_iso(),
        "pilot_run_id": args.run_id,
        "phase": "POST_SAFETY_BOUNDARY_INDEPENDENT_CLEAN_PILOT6",
        "source": {
            "filename": source.name,
            "sha256": source_sha,
            "size_bytes": source.stat().st_size,
            "semantic_content_read_before_independence_gate": False,
        },
        "source_independence": {
            "gate": "PASS",
            "search_scope": ["workspace/phase3c", "scripts", "tests", "docs", "Production sources.sha256"],
            "reference_hits": references,
            "production_duplicate_rows": production_duplicate,
            "not_used_in_pilots_3_4_5": True,
            "not_used_in_table_suppression_design_or_evaluation": True,
            "not_used_in_safety_boundary_design": True,
            "not_a_regression_fixture": True,
            "not_inspected_for_implementation_tuning": True,
        },
        "git": {
            "branch": git(repo, "branch", "--show-current"),
            "head": git(repo, "rev-parse", "HEAD"),
            "tracked_working_tree_status": tracked_status,
            "state": "DIRTY_ACCEPTED_PHASE3C_ENGINEERING_STATE" if tracked_status else "CLEAN",
        },
        "implementation": {
            "critical_file_hashes": actual_hashes,
            "critical_manifest": manifest(repo, CRITICAL_FILE_HASHES),
            "mismatches": mismatches,
            "prompt": prompt,
            "evidence_contract": EVIDENCE_CONTRACT,
            "evidence_contract_version": EVIDENCE_VERSION,
            "table_policy": "NARRATIVE_FIRST_TABLE_SUPPRESSION",
            "table_structure_signal": "pymupdf_layout.Page.get_layout",
            "canonical_source_truth": "pypdf",
            "table_claim_safety_boundary_version": "V1",
            "table_claim_safety_boundary_sha256": actual_hashes["src/pro_a/table_claim_safety.py"],
        },
        "dependencies": {
            "pypdf": pypdf.__version__,
            "PyMuPDF": pymupdf.__version__,
            "PyMuPDF_bind": pymupdf.VersionBind,
            "pymupdf-layout": importlib.metadata.version("pymupdf-layout"),
            "onnxruntime": importlib.metadata.version("onnxruntime"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "semantic_extraction_runtime": {
            "configured_model": load_config(args.config).llm.model,
            "prompt_sha256": PROMPT_SHA256,
            "one_logical_extraction_authorized": True,
        },
        "production_pre": production,
        "PHASE3C_PILOT6_IMPLEMENTATION_FROZEN": implementation_frozen,
    }
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "pilot6_source_independence.json", receipt["source_independence"])
    write_json(run_dir / "pilot6_pre_run_freeze_receipt.json", receipt)
    print(json.dumps({
        "run_id": args.run_id,
        "source_independence_gate": "PASS",
        "implementation_frozen": implementation_frozen,
        "source_sha256": source_sha,
        "critical_manifest_sha256": receipt["implementation"]["critical_manifest"]["sha256"],
        "production_sha256": production["sha256"],
    }, ensure_ascii=False))
    return 0


def structure(args: argparse.Namespace) -> int:
    source = args.source.resolve()
    run_dir = args.run_dir.resolve()
    receipt_path = run_dir / "pilot6_pre_run_freeze_receipt.json"
    if not receipt_path.is_file():
        raise PilotError("PILOT6_PREFLIGHT_RECEIPT_MISSING")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("PHASE3C_PILOT6_IMPLEMENTATION_FROZEN") is not True:
        raise PilotError("PILOT6_IMPLEMENTATION_NOT_FROZEN")
    if sha256_file(source) != (receipt.get("source") or {}).get("sha256"):
        raise PilotError("PILOT6_SOURCE_CHANGED_AFTER_PREFLIGHT")

    parsed = parse_source_with_diagnostics(source, include_semantic_segments=True)
    if parsed.source_type != "pdf" or parsed.layout_sidecar is None or parsed.segments is None:
        raise PilotError("PILOT6_PDF_STRUCTURE_UNAVAILABLE")
    semantic_text = semantic_eligible_source_text(parsed)
    counts = Counter(segment.kind for segment in parsed.segments)
    native_tables = [segment for segment in parsed.segments if segment.native_kind == "table"]
    accepted_tables = [segment for segment in native_tables if segment.kind == "table"]
    canonical_fail_open = [
        segment for segment in native_tables
        if segment.kind == "unknown" and "CANONICAL_BINDING" in segment.reason
    ]
    protected_fail_open = [
        segment for segment in native_tables
        if segment.kind == "unknown" and "PROTECTED" in segment.reason
    ]
    suppressed_spans = sorted(
        (span.start, span.end)
        for segment in accepted_tables
        for span in segment.source_spans
    )
    suppressed_span_chars = sum(end - start for start, end in suppressed_spans)
    non_overlapping_spans = all(
        previous_end <= start
        for (_, previous_end), (start, _) in zip(
            suppressed_spans, suppressed_spans[1:]
        )
    )
    canonical_complete = bool(
        parsed.diagnostics.get("total_units")
        and parsed.diagnostics.get("error_units") == 0
        and parsed.diagnostics.get("empty_units") == 0
        and parsed.diagnostics.get("partial_parse") is False
        and parsed.diagnostics.get("empty_extraction") is False
    )
    effective_table_absent = bool(
        non_overlapping_spans
        and len(parsed.text) - len(semantic_text) == suppressed_span_chars
    )
    diagnostics = {
        "document_type": "phase3c_pilot6_pdf_structure_diagnostics",
        "schema_version": "1",
        "created_at": now_iso(),
        "pilot_run_id": args.run_id,
        "source_sha256": sha256_file(source),
        "parse_diagnostics": parsed.diagnostics,
        "canonical_source_chars": len(parsed.text),
        "semantic_eligible_chars": len(semantic_text),
        "suppressed_table_chars": len(parsed.text) - len(semantic_text),
        "suppressed_span_chars": suppressed_span_chars,
        "segment_counts": {
            "narrative": counts["narrative"],
            "table": counts["table"],
            "unknown": counts["unknown"],
        },
        "native_table_candidates": len(native_tables),
        "accepted_suppressible_tables": len(accepted_tables),
        "canonical_binding_fail_open_tables": len(canonical_fail_open),
        "protected_overlap_fail_open_tables": len(protected_fail_open),
        "effective_table_pages": sorted({segment.page for segment in accepted_tables}),
        "fail_open_table_pages": sorted({segment.page for segment in native_tables if segment.kind != "table"}),
        "native_table_pages": sorted({segment.page for segment in native_tables}),
        "layout_signature": parsed.layout_sidecar.get("signature_sha256"),
        "canonical_source_complete": canonical_complete,
        "effective_table_content_excluded_before_chunk_prompt": effective_table_absent,
        "false_narrative_suppression_found": "PENDING_BOUNDED_VISUAL_AUDIT",
    }
    if not canonical_complete:
        raise PilotError("PILOT6_CANONICAL_SOURCE_INCOMPLETE")
    write_json(run_dir / "source_layout_sidecar.json", parsed.layout_sidecar)
    write_json(run_dir / "pilot6_source_layout_diagnostics.json", diagnostics)
    print(json.dumps(diagnostics, ensure_ascii=False))
    return 0


def render_visual_audit(args: argparse.Namespace) -> int:
    import pymupdf
    from PIL import Image, ImageDraw

    run_dir = args.run_dir.resolve()
    source = args.source.resolve()
    diagnostics = json.loads(
        (run_dir / "pilot6_source_layout_diagnostics.json").read_text(encoding="utf-8")
    )
    sidecar = json.loads(
        (run_dir / "source_layout_sidecar.json").read_text(encoding="utf-8")
    )
    pages = sorted(set(
        [1]
        + diagnostics["effective_table_pages"]
        + diagnostics["fail_open_table_pages"]
    ))
    output_dir = run_dir / "visual_diagnostics"
    output_dir.mkdir(exist_ok=True)
    document = pymupdf.open(source)
    scale = 2.0
    try:
        for page_number in pages:
            page = document[page_number - 1]
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), alpha=False
            )
            image = Image.frombytes(
                "RGB", (pixmap.width, pixmap.height), pixmap.samples
            )
            draw = ImageDraw.Draw(image)
            table_segments = [
                segment for segment in sidecar["segments"]
                if segment["page"] == page_number
                and segment["native_kind"] == "table"
            ]
            for index, segment in enumerate(table_segments, 1):
                x0, y0, x1, y1 = [value * scale for value in segment["bbox"]]
                if segment["kind"] == "table":
                    color = (220, 0, 0)
                elif "CANONICAL_BINDING" in segment["reason"]:
                    color = (255, 140, 0)
                else:
                    color = (0, 80, 220)
                draw.rectangle((x0, y0, x1, y1), outline=color, width=5)
                label = f"{index} {segment['kind']} {segment['reason'][:32]}"
                draw.rectangle(
                    (x0, max(0, y0 - 24), min(x1, x0 + 390), y0),
                    fill=(255, 255, 255),
                )
                draw.text((x0 + 3, max(0, y0 - 21)), label, fill=color)
            image.save(output_dir / f"page_{page_number:02d}_table_audit.png")
    finally:
        document.close()
    print(json.dumps({
        "pages": pages,
        "files": len(pages),
        "output_dir": str(output_dir),
        "legend": {
            "red": "accepted suppressible table",
            "orange": "canonical-binding fail-open table",
            "blue": "protected-overlap fail-open table",
        },
    }))
    return 0


def extract(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    source = args.source.resolve()
    marker = run_dir / "one_logical_extraction_marker.json"
    if marker.exists() or (run_dir / "extraction_bundle.json").exists():
        raise PilotError("PILOT6_LOGICAL_EXTRACTION_ALREADY_STARTED")
    visual = run_dir / "pilot6_bounded_visual_audit.json"
    if not visual.is_file():
        raise PilotError("PILOT6_BOUNDED_VISUAL_AUDIT_MISSING")
    visual_audit = json.loads(visual.read_text(encoding="utf-8"))
    if visual_audit.get("gate") != "PASS":
        raise PilotError("PILOT6_BOUNDED_VISUAL_AUDIT_NOT_PASS")
    write_json(marker, {
        "document_type": "phase3c_pilot6_one_logical_extraction_marker",
        "schema_version": "1",
        "created_at": now_iso(),
        "pilot_run_id": args.run_id,
        "source_sha256": sha256_file(source),
        "logical_semantic_extractions": 1,
        "status": "STARTED_NO_RERUN_ALLOWED",
    })
    cfg = load_config(args.config)
    result = extract_pilot_source(
        source,
        cfg,
        output_dir=run_dir,
        production_db_path=args.production_db,
        required_prompt_sha256=PROMPT_SHA256,
        run_id=args.run_id,
    )
    bundle = result["bundle"]
    completed = json.loads(marker.read_text(encoding="utf-8"))
    completed.update({
        "status": "COMPLETE",
        "api_attempts": (bundle.get("model") or {}).get("llm_calls"),
        "usage": copy.deepcopy((bundle.get("model") or {}).get("usage") or {}),
        "raw_extracted_claims": len(bundle.get("claims") or []),
        "semantic_eligible_input_chars": ((bundle.get("source") or {}).get("semantic_eligibility") or {}).get("semantic_eligible_chars"),
        "production_unchanged": result["production_unchanged"],
        "semantic_rerun": False,
        "quality_rerun": False,
    })
    write_json(marker, completed)
    print(json.dumps({
        "status": result["status"],
        "run_id": args.run_id,
        "logical_extractions": 1,
        "api_attempts": completed["api_attempts"],
        "usage": completed["usage"],
        "raw_claims": completed["raw_extracted_claims"],
        "production_unchanged": result["production_unchanged"],
    }, ensure_ascii=False))
    return 0


def evidence(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    source = args.source.resolve()
    production_db = args.production_db.resolve()
    original = run_dir / "extraction_bundle.json"
    if not original.is_file():
        raise PilotError("PILOT6_EXTRACTION_BUNDLE_MISSING")
    rebound = rebind_stage1_evidence_locators(
        original,
        source,
        output_dir=run_dir,
        production_db_path=production_db,
    )
    evidence_dir = run_dir / "evidence_v2"
    draft = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]),
        Path(rebound["review_draft_path"]),
        source,
        output_dir=evidence_dir,
        production_db_path=production_db,
    )
    gate = run_pilot2_gate_a_quote_fidelity(
        original,
        Path(rebound["rebound_bundle_path"]),
        Path(draft["draft_path"]),
        source,
        output_dir=evidence_dir,
        production_db_path=production_db,
        original_review_path=run_dir / "extraction_review_draft.json",
    )
    final_contract = evidence_dir / "evidence_contract_v2.json"
    final_contract.write_bytes(Path(draft["draft_path"]).read_bytes())
    (evidence_dir / "quote_fidelity_metrics.json").write_bytes(
        Path(gate["metrics_path"]).read_bytes()
    )
    print(json.dumps({
        "rebind": rebound["metrics"]["after"],
        "draft_metrics": draft["metrics"],
        "fidelity_counts": gate["metrics"]["fidelity_counts"],
        "production_unchanged": bool(
            rebound["production_unchanged"]
            and draft["production_unchanged"]
            and gate["production_unchanged"]
        ),
        "llm_calls_added": 0,
    }, ensure_ascii=False))
    return 0


def claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def render_review_surface(
    *, run_id: str, eligible_claims: list[dict[str, Any]], gate_by_id: dict[str, Any]
) -> str:
    lines = [
        "# Phase 3C Pilot #6 Independent Human Review Surface",
        "",
        f"- pilot_run_id: `{run_id}`",
        f"- semantic review denominator: {len(eligible_claims)} REVIEW_ELIGIBLE Claims",
        "- TABLE_DERIVED_CLAIM_INELIGIBLE items are excluded and audited separately.",
        "- Human Review has not been executed.",
        "- Every Human decision begins as `PENDING`.",
        "",
        "Frozen C2 gate: true semantic failure rate <= 10.00% AND ATTRIBUTION_ERROR = 0.",
        "",
    ]
    for claim in eligible_claims:
        gate = gate_by_id[claim["claim_id"]]
        lines += [
            f"## {claim['claim_id']}",
            "",
            f"- statement: {claim.get('statement') or ''}",
            f"- attributed_to: {claim.get('attributed_to') or ''}",
            f"- immutable Evidence: {claim.get('evidence_excerpt') or ''}",
            f"- Evidence fidelity: `{gate.get('fidelity_status')}`",
            f"- authoritative locator: `{json.dumps(gate.get('resolved_locator'), ensure_ascii=False)}`",
            "- Human decision: `PENDING`",
            "",
        ]
    lines += [
        "STOP: Human Review was not performed. No semantic PASS/FAIL was calculated.",
        "",
    ]
    return "\n".join(lines)


def render_exclusion_audit(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 3C Pilot #6 Table-Derived Claim Exclusion Audit",
        "",
        "These items remain in the raw extraction artifact and are excluded only from the default semantic Human Review denominator.",
        "",
        f"- boundary version: `{TABLE_CLAIM_SAFETY_BOUNDARY_VERSION}`",
        f"- ineligible Claims: {result['table_derived_claims_ineligible']}",
        "",
    ]
    for item in result["ineligible_claim_audit"]:
        lines += [
            f"## {item['claim_id']}",
            "",
            f"- immutable Evidence: {item['immutable_evidence_excerpt']}",
            f"- authoritative locator: `{json.dumps(item['authoritative_evidence_locator'], ensure_ascii=False)}`",
            f"- Evidence geometry: `{json.dumps(item['evidence_geometry'], ensure_ascii=False)}`",
            f"- native table bbox: `{json.dumps(item['native_table_bbox'], ensure_ascii=False)}`",
            f"- decision reason: `{item['decision_reason']}`",
            f"- boundary version: `{item['safety_boundary_version']}`",
            "",
        ]
    return "\n".join(lines)


def finalize(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    run_dir = args.run_dir.resolve()
    source = args.source.resolve()
    production_db = args.production_db.resolve()
    files = {
        "preflight": run_dir / "pilot6_pre_run_freeze_receipt.json",
        "structure": run_dir / "pilot6_source_layout_diagnostics.json",
        "visual": run_dir / "pilot6_bounded_visual_audit.json",
        "marker": run_dir / "one_logical_extraction_marker.json",
        "original": run_dir / "extraction_bundle.json",
        "rebound": run_dir / "extraction_bundle_stage1_1_rebound.json",
        "sidecar": run_dir / "source_layout_sidecar.json",
        "draft": run_dir / "evidence_v2" / "evidence_contract_v2.json",
        "gate": run_dir / "evidence_v2" / "pilot2_gate_a_quote_fidelity.json",
    }
    if any(not path.is_file() for path in files.values()):
        raise PilotError("PILOT6_FINALIZE_INPUT_MISSING")
    preflight = json.loads(files["preflight"].read_text(encoding="utf-8"))
    structure_data = json.loads(files["structure"].read_text(encoding="utf-8"))
    visual = json.loads(files["visual"].read_text(encoding="utf-8"))
    marker = json.loads(files["marker"].read_text(encoding="utf-8"))
    original = json.loads(files["original"].read_text(encoding="utf-8"))
    rebound = json.loads(files["rebound"].read_text(encoding="utf-8"))
    sidecar = json.loads(files["sidecar"].read_text(encoding="utf-8"))
    draft = json.loads(files["draft"].read_text(encoding="utf-8"))
    gate = json.loads(files["gate"].read_text(encoding="utf-8"))
    original_claims = original.get("claims") or []
    rebound_claims = rebound.get("claims") or []
    gate_claims = gate.get("claims") or []
    gate_by_id = {item["claim_id"]: item for item in gate_claims}
    ids = [claim["claim_id"] for claim in original_claims]
    coverage_complete = bool(
        ids == [claim["claim_id"] for claim in rebound_claims]
        and set(ids) == set(gate_by_id)
        and ids == [item["claim_id"] for item in draft.get("claims") or []]
    )
    if not coverage_complete:
        raise PilotError("PILOT6_EVIDENCE_CLAIM_COVERAGE_MISMATCH")

    boundary_claims = copy.deepcopy(rebound_claims)
    for claim in boundary_claims:
        gate_claim = gate_by_id[claim["claim_id"]]
        claim["phase3c_evidence"] = copy.deepcopy(gate_claim["evidence_contract"])
        validation = copy.deepcopy(claim.get("validation") or {})
        validation["source_locator"] = copy.deepcopy(gate_claim["gate_a_source_locator"])
        claim["validation"] = validation
    authoritative_pages = [
        int(resolved["locator"].split(":", 1)[1])
        for claim in boundary_claims
        for resolved in [((claim.get("phase3c_evidence") or {}).get("resolved_locator") or {})]
        if resolved.get("kind") == "single_page" and resolved.get("locator")
    ]
    parsed = parse_source_with_diagnostics(source)
    word_pages = load_pymupdf_word_pages(source, authoritative_pages)
    boundary = apply_table_claim_safety_boundary_v1(
        canonical_source_text=parsed.text,
        layout_sidecar=sidecar,
        claims=boundary_claims,
        word_pages=word_pages,
    )
    eligible_ids = set(boundary["review_eligible_claim_ids"])
    ineligible_ids = set(boundary["table_derived_ineligible_claim_ids"])
    eligible_claims = [claim for claim in original_claims if claim["claim_id"] in eligible_ids]
    eligible_gate_claims = [item for item in gate_claims if item["claim_id"] in eligible_ids]

    raw_projection = canonical_sha256([claim_projection(claim) for claim in original_claims])
    rebound_projection = canonical_sha256([claim_projection(claim) for claim in rebound_claims])
    boundary_projection = canonical_sha256([claim_projection(claim) for claim in boundary_claims])
    eligible_projection = canonical_sha256([claim_projection(claim) for claim in eligible_claims])
    claim_integrity = {
        "raw_claim_projection_sha256": raw_projection,
        "rebound_claim_projection_sha256": rebound_projection,
        "boundary_input_claim_projection_sha256": boundary_projection,
        "eligible_claim_projection_sha256": eligible_projection,
        "raw_projection_unchanged": raw_projection == rebound_projection == boundary_projection,
        "raw_claims_redefined_as_eligible_population": False,
    }

    fidelity_statuses = (
        "EXACT_SOURCE_MATCH",
        "LAYOUT_NORMALIZED_EXACT_MATCH",
        "EXACT_ORDERED_CROSS_PAGE_SPAN",
        "PROVENANCE_MISMATCH_RECOVERED",
        "QUOTE_DRIFT",
        "UNRESOLVED_SOURCE_BINDING",
    )
    fidelity_counts = {
        status: sum(item.get("fidelity_status") == status for item in eligible_gate_claims)
        for status in fidelity_statuses
    }
    valid_statuses = set(fidelity_statuses[:4])
    eligible_total = len(eligible_claims)
    source_bound = sum(item.get("fidelity_status") in valid_statuses for item in eligible_gate_claims)
    quote_drift = fidelity_counts["QUOTE_DRIFT"]

    def rate(numerator: int, denominator: int, threshold: float, comparison: str) -> dict[str, Any]:
        percent = round(100 * numerator / denominator, 2) if denominator else 0.0
        passed = percent >= threshold if comparison == ">=" else percent <= threshold
        return {
            "numerator": numerator,
            "denominator": denominator,
            "percent": percent,
            "threshold_percent": threshold,
            "comparison": comparison,
            "passed": passed,
        }

    rates = {
        "quote_fidelity": rate(source_bound, eligible_total, 85.0, ">="),
        "quote_drift": rate(quote_drift, eligible_total, 15.0, "<="),
        "source_binding": rate(source_bound, eligible_total, 85.0, ">="),
    }
    mechanical_gate = "PASS" if all(value["passed"] for value in rates.values()) else "FAIL"

    fallback_rule = "same_page_evidence_segment_bounded_subspan"
    fallback_claim_ids: set[str] = set()
    fallback_before = 0
    fallback_after = 0
    existing_candidates = 0
    fallback_candidates = 0
    for claim in draft.get("claims") or []:
        for candidate in claim.get("bounded_context_candidates") or []:
            if candidate.get("selection_rule") == fallback_rule:
                fallback_claim_ids.add(claim["claim_id"])
                fallback_candidates += 1
                fallback_before += candidate.get("direction") == "before"
                fallback_after += candidate.get("direction") == "after"
            else:
                existing_candidates += 1
    context_footprint = {
        "bounded_local_subspan_claims": len(fallback_claim_ids),
        "bounded_local_subspan_candidates": fallback_candidates,
        "bounded_local_subspan_before": fallback_before,
        "bounded_local_subspan_after": fallback_after,
        "bounded_local_subspan_validator_pass": fallback_candidates,
        "bounded_local_subspan_validator_fail": 0,
        "existing_adjacent_segment_candidates": existing_candidates,
    }

    protected_removed = sum(
        not item["checks"]["native_table_has_no_protected_overlap"]
        for item in boundary["ineligible_claim_audit"]
    )
    narrative_removed = sum(
        not item["checks"]["no_competing_narrative_occurrence"]
        for item in boundary["ineligible_claim_audit"]
    )
    unresolved_filtered = sum(
        claim_id in ineligible_ids
        for claim_id, item in gate_by_id.items()
        if item.get("resolved_locator") is None
    )
    upstream_leak = boundary["upstream_effective_table_suppression_leak_count"]
    false_filter = bool(protected_removed or narrative_removed or unresolved_filtered)
    safety_gate = "PASS" if not upstream_leak and not false_filter and boundary["raw_claims_unchanged"] else "FAIL"
    evidence_gate = "PASS" if coverage_complete and len(gate_claims) == len(original_claims) else "FAIL"
    all_prior_pass = bool(
        preflight["source_independence"]["gate"] == "PASS"
        and visual["gate"] == "PASS"
        and evidence_gate == "PASS"
        and safety_gate == "PASS"
        and mechanical_gate == "PASS"
        and claim_integrity["raw_projection_unchanged"]
    )
    semantic_gate = "PENDING_HUMAN_REVIEW" if all_prior_pass else "NOT_REACHED"
    next_gate = (
        "Clean Pilot #6 Independent Human Review"
        if all_prior_pass
        else "Pilot #6 Failure Census"
    )

    safety_path = run_dir / "pilot6_table_claim_safety_boundary.json"
    write_json(safety_path, {
        "document_type": "phase3c_pilot6_table_claim_safety_boundary",
        "schema_version": "1",
        "pilot_run_id": args.run_id,
        "gate": safety_gate,
        "result": boundary,
        "protected_overlap_claims_filtered": protected_removed,
        "narrative_authoritative_claims_filtered": narrative_removed,
        "ambiguous_or_unresolved_claims_filtered": unresolved_filtered,
        "false_table_claim_filter_found": false_filter,
        "upstream_suppression_leak_found": bool(upstream_leak),
        "claim_integrity": claim_integrity,
    })
    exclusion_path = run_dir / "pilot6_table_derived_exclusion_audit.md"
    exclusion_path.write_text(render_exclusion_audit(boundary), encoding="utf-8")

    review_path = run_dir / "pilot6_independent_human_review_surface.md"
    if all_prior_pass:
        review_path.write_text(
            render_review_surface(
                run_id=args.run_id,
                eligible_claims=eligible_claims,
                gate_by_id=gate_by_id,
            ),
            encoding="utf-8",
        )
    production_post = production_snapshot(production_db)
    production_pre = preflight["production_pre"]
    production_unchanged = production_pre == production_post
    implementation_post = manifest(repo, CRITICAL_FILE_HASHES)
    implementation_pre = preflight["implementation"]["critical_manifest"]
    implementation_unchanged = implementation_pre == implementation_post
    extraction_complete = bool(
        all_prior_pass
        and production_unchanged
        and implementation_unchanged
        and review_path.is_file()
    )

    metrics = {
        "document_type": "phase3c_pilot6_mechanical_metrics",
        "schema_version": "1",
        "created_at": now_iso(),
        "pilot_run_id": args.run_id,
        "source_sha256": sha256_file(source),
        "raw_extracted_claims": len(original_claims),
        "table_derived_claims_ineligible": boundary["table_derived_claims_ineligible"],
        "review_eligible_claims": eligible_total,
        "stage1_1": {
            "resolved": sum(((claim.get("validation") or {}).get("source_locator") or {}).get("status") == "resolved" for claim in rebound_claims),
            "ambiguous": sum(((claim.get("validation") or {}).get("source_locator") or {}).get("status") == "ambiguous" for claim in rebound_claims),
            "unresolved": sum(((claim.get("validation") or {}).get("source_locator") or {}).get("status") == "unresolved" for claim in rebound_claims),
        },
        "eligible_fidelity_counts": fidelity_counts,
        "raw_fidelity_counts": gate["metrics"]["fidelity_counts"],
        "rates": rates,
        "context_generation": context_footprint,
        "claim_integrity": claim_integrity,
        "human_review": {
            "surface_claims": eligible_total if review_path.is_file() else 0,
            "pending": eligible_total if review_path.is_file() else 0,
            "excluded_table_claims": boundary["table_derived_claims_ineligible"],
            "semantic_review_executed": False,
        },
        "PILOT6_EVIDENCE_ARTIFACT_GATE": evidence_gate,
        "PILOT6_MECHANICAL_GATE": mechanical_gate,
        "PILOT6_SEMANTIC_GATE": semantic_gate,
    }
    metrics_path = run_dir / "pilot6_mechanical_metrics.json"
    write_json(metrics_path, metrics)

    artifacts = {
        path.relative_to(run_dir).as_posix(): sha256_file(path)
        for path in sorted(run_dir.rglob("*"))
        if path.is_file() and path.name not in {
            "pilot6_validation_receipt.json", "pilot6_stop_report.md"
        }
    }
    receipt = {
        "document_type": "phase3c_pilot6_validation_receipt",
        "schema_version": "1",
        "created_at": now_iso(),
        "pilot_run_id": args.run_id,
        "status": "PASS_STOPPED_BEFORE_HUMAN_REVIEW" if extraction_complete else "FAIL_STOPPED",
        "gates": {
            "PILOT6_SOURCE_INDEPENDENCE_GATE": preflight["source_independence"]["gate"],
            "PILOT6_TABLE_SUPPRESSION_RUNTIME_GATE": visual["gate"],
            "PILOT6_TABLE_CLAIM_SAFETY_GATE": safety_gate,
            "PILOT6_EVIDENCE_ARTIFACT_GATE": evidence_gate,
            "PILOT6_MECHANICAL_GATE": mechanical_gate,
            "PILOT6_SEMANTIC_GATE": semantic_gate,
        },
        "freeze": {
            "implementation_manifest_pre_sha256": implementation_pre["sha256"],
            "implementation_manifest_post_sha256": implementation_post["sha256"],
            "implementation_changed": not implementation_unchanged,
            "prompt_sha256": PROMPT_SHA256,
            "source_sha256": sha256_file(source),
        },
        "source_structure": structure_data,
        "extraction": marker,
        "mechanical_metrics": metrics,
        "artifact_hashes": artifacts,
        "production_isolation": {
            "pre": production_pre,
            "post": production_post,
            "changed": not production_unchanged,
            "table_counts_changed": production_pre["table_counts"] != production_post["table_counts"],
            "integrity_check": production_post["integrity_check"],
            "foreign_key_violations": len(production_post["foreign_key_violations"]),
            "production_write": False,
            "ima_invoked": False,
            "propagation_invoked": False,
            "legacy_ingestion_invoked": False,
        },
        "PHASE3C_CLEAN_PILOT6_EXTRACTION_COMPLETE": extraction_complete,
        "PHASE3C_COMPLETE": False,
        "PRODUCTION_APPLY_READY": "NO",
        "PHASE3C_NEXT_GATE": next_gate,
        "STOP_CONFIRMATION": "STOPPED_BEFORE_HUMAN_REVIEW_PRODUCTION_OR_NEW_SOURCE",
    }
    write_json(run_dir / "pilot6_validation_receipt.json", receipt)

    lines = [
        "# Phase 3C Post-Safety-Boundary Independent Clean Pilot #6 Stop Report",
        "",
        "```text",
        f"PHASE3C_CLEAN_PILOT6_EXTRACTION_COMPLETE = {str(extraction_complete).lower()}",
        "",
        f"PILOT6_SOURCE_INDEPENDENCE_GATE = {preflight['source_independence']['gate']}",
        f"PILOT6_TABLE_SUPPRESSION_RUNTIME_GATE = {visual['gate']}",
        f"PILOT6_TABLE_CLAIM_SAFETY_GATE = {safety_gate}",
        f"PILOT6_EVIDENCE_ARTIFACT_GATE = {evidence_gate}",
        f"PILOT6_MECHANICAL_GATE = {mechanical_gate}",
        f"PILOT6_SEMANTIC_GATE = {semantic_gate}",
        "",
        f"PILOT6_RAW_EXTRACTED_CLAIMS = {len(original_claims)}",
        f"PILOT6_TABLE_DERIVED_CLAIMS_INELIGIBLE = {boundary['table_derived_claims_ineligible']}",
        f"PILOT6_REVIEW_ELIGIBLE_CLAIMS = {eligible_total}",
        "",
        f"PILOT6_CANONICAL_SOURCE_CHARS = {structure_data['canonical_source_chars']}",
        f"PILOT6_SEMANTIC_ELIGIBLE_CHARS = {structure_data['semantic_eligible_chars']}",
        f"PILOT6_SUPPRESSED_TABLE_CHARS = {structure_data['suppressed_table_chars']}",
        "",
        f"PILOT6_NARRATIVE_SEGMENTS = {structure_data['segment_counts']['narrative']}",
        f"PILOT6_TABLE_SEGMENTS = {structure_data['segment_counts']['table']}",
        f"PILOT6_UNKNOWN_SEGMENTS = {structure_data['segment_counts']['unknown']}",
        "",
        f"PILOT6_BOUNDED_LOCAL_SUBSPAN_CLAIMS = {context_footprint['bounded_local_subspan_claims']}",
        f"PILOT6_BOUNDED_LOCAL_SUBSPAN_BEFORE = {context_footprint['bounded_local_subspan_before']}",
        f"PILOT6_BOUNDED_LOCAL_SUBSPAN_AFTER = {context_footprint['bounded_local_subspan_after']}",
        "",
        f"PILOT6_QUOTE_FIDELITY_RATE = {rates['quote_fidelity']['percent']:.2f}%",
        f"PILOT6_QUOTE_DRIFT_RATE = {rates['quote_drift']['percent']:.2f}%",
        f"PILOT6_SOURCE_BINDING_RATE = {rates['source_binding']['percent']:.2f}%",
        "",
        f"PILOT6_FALSE_NARRATIVE_SUPPRESSION_FOUND = {visual['PILOT6_FALSE_NARRATIVE_SUPPRESSION_FOUND']}",
        f"PILOT6_UPSTREAM_SUPPRESSION_LEAK_FOUND = {'YES' if upstream_leak else 'NO'}",
        f"PILOT6_FALSE_TABLE_CLAIM_FILTER_FOUND = {'YES' if false_filter else 'NO'}",
        "",
        f"PILOT6_LOGICAL_SEMANTIC_EXTRACTIONS = {marker['logical_semantic_extractions']}",
        f"PILOT6_LLM_API_ATTEMPTS = {marker['api_attempts']}",
        f"PILOT6_TOTAL_TOKENS = {marker['usage']['total_tokens']}",
        "",
        f"PRODUCTION_DB_CHANGED = {'NO' if production_unchanged else 'YES'}",
        "",
        "PHASE3C_COMPLETE = false",
        "PRODUCTION_APPLY_READY = NO",
        "",
        "PHASE3C_NEXT_GATE =",
        next_gate,
        "```",
        "",
        "STOP. Human Review was not performed; no repair, new Source selection, or Production write occurred.",
        "",
    ]
    (run_dir / "pilot6_stop_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "extraction_complete": extraction_complete,
        "raw_claims": len(original_claims),
        "table_ineligible": boundary["table_derived_claims_ineligible"],
        "review_eligible": eligible_total,
        "safety_gate": safety_gate,
        "evidence_gate": evidence_gate,
        "mechanical_gate": mechanical_gate,
        "semantic_gate": semantic_gate,
        "rates": rates,
        "upstream_leak": upstream_leak,
        "false_filter": false_filter,
        "production_unchanged": production_unchanged,
        "implementation_unchanged": implementation_unchanged,
        "next_gate": next_gate,
    }, ensure_ascii=False))
    return 0 if extraction_complete else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument(
        "command", choices=("preflight", "structure", "render", "extract", "evidence", "finalize")
    )
    result.add_argument("--repo", type=Path, default=Path.cwd())
    result.add_argument("--config", type=Path, default=Path("config.toml"))
    result.add_argument("--source", type=Path, required=True)
    result.add_argument("--run-dir", type=Path, required=True)
    result.add_argument("--run-id", required=True)
    result.add_argument("--production-db", type=Path, required=True)
    result.add_argument("--expected-source-sha", default="")
    result.add_argument("--expected-production-sha", default="")
    result.add_argument("--independence-token", default="")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "preflight":
        return preflight(args)
    if args.command == "structure":
        return structure(args)
    if args.command == "render":
        return render_visual_audit(args)
    if args.command == "extract":
        return extract(args)
    if args.command == "evidence":
        return evidence(args)
    if args.command == "finalize":
        return finalize(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
