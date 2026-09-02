from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from pro_a.parsers import parse_source_with_diagnostics
from pro_a.table_claim_safety import (
    TABLE_CLAIM_SAFETY_BOUNDARY_VERSION,
    TABLE_DERIVED_CLAIM_INELIGIBLE,
    apply_table_claim_safety_boundary_v1,
    load_pymupdf_word_pages,
)


PILOT_RUN_ID = "PILOT_20260901_760D5031"
SOURCE_SHA256 = "760d50319760257dceaea2815374e685d089323faebcb32700dfefdaa6fd6d5c"
RAW_CLAIM_PROJECTION_SHA256 = (
    "d176a7d274b45cf76bcf853947ff7f649906737ca18667ae8ddd0d9716f1ac9d"
)
PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"
PILOT4_TREE = {
    "files": 38,
    "digest": "cf8263bcccd456bbde786e397ac5b81c261118562a653e20a125c1037dd940e5",
}
PILOT5_TREE = {
    "files": 42,
    "digest": "d856653676d8eb953a7172b673add332f660e9dae093677a7ad4151a9d1b496e",
}
PRODUCTION_SHA256 = "581978e1c587b065a6eef9c980013af3de1a9e8a8781857385404c9f61105250"
FROZEN_HASHES = {
    "bundle": "a220e1f8bef259565fc6e31e1b6fb02f080af446a94cd2380359ecb031ae8121",
    "sidecar": "fed2687d0eccc486c5fdaf1bbce710a7afd4de724d659ddf20b505c2039e1712",
    "evidence": "0d9f6fa4995161074ee625d9e80d0123d5049486aa33d91df3cf33c605718bdf",
    "quote": "d69681643d7724534cef1aaa0ac651754fd093d9aad47716e9bbd6ae7dc108df",
    "human_surface": "09b215ead496809c1a081094caf489563931971edf84b447ed008478dd081a02",
    "prompt_source": "4ac7a3ed099797920e57702fd3860f0ed98153fa272f112f2618e5e3fb6edce5",
    "table_detector": "4c3fd5ab068dfd55bd434b5fba947f790231c66161ad2133d459d700e4954739",
    "corpus_pilot": "31089819e65631f4296491a50dd4dc3ed88deda3e40b00bb0ce010361ecb1db2",
}
EXPECTED_INELIGIBLE_IDS = (
    "CLM_20260901_F244C74D",
    "CLM_20260901_BDB28301",
    "CLM_20260901_2D592B6E",
    "CLM_20260901_BDD0BF84",
    "CLM_20260901_DFEC4E23",
    "CLM_20260901_B2F0573B",
    "CLM_20260901_214DBE2A",
    "CLM_20260901_2BD36CE6",
    "CLM_20260901_7594D5EF",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def tree_snapshot(root: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]
    return {"files": len(rows), "digest": canonical_sha256(rows)}


def production_snapshot(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            "sha256": file_sha256(path),
            "table_counts": {
                table: connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                for table in tables
            },
            "integrity_check": connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0],
            "foreign_key_violations": len(
                connection.execute("PRAGMA foreign_key_check").fetchall()
            ),
        }
    finally:
        connection.close()


def claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def render_counterfactual_surface(
    *,
    claims_by_id: dict[str, dict[str, Any]],
    result: dict[str, Any],
) -> str:
    lines = [
        "# Pilot #5 Counterfactual Origin-Eligible Review Surface",
        "",
        "**COUNTERFACTUAL ONLY**",
        "",
        "**HUMAN REVIEW NOT EXECUTED**",
        "",
        f"- raw extracted Claims: {result['raw_claims']}",
        f"- review-eligible Claims: {result['review_eligible_claims']}",
        f"- table-derived ineligible Claims: {result['table_derived_claims_ineligible']}",
        f"- boundary version: `{result['version']}`",
        "",
        "The frozen Pilot #5 Human Review surface was not changed. Every item below "
        "remains mechanically projected and has no Human decision.",
        "",
        "## Review-eligible Claims",
        "",
    ]
    for claim_id in result["review_eligible_claim_ids"]:
        claim = claims_by_id[claim_id]
        lines.extend(
            [
                f"### {claim_id}",
                "",
                f"- statement: {claim.get('statement') or ''}",
                f"- Evidence: {claim.get('evidence_excerpt') or ''}",
                "- Origin eligibility: `REVIEW_ELIGIBLE`",
                "- Human decision: `NOT_EXECUTED`",
                "",
            ]
        )
    lines.extend(["## Table-derived ineligible Claims", ""])
    for decision in result["ineligible_claim_audit"]:
        lines.extend(
            [
                f"### {decision['claim_id']}",
                "",
                f"- authoritative locator: `{json.dumps(decision['authoritative_evidence_locator'], ensure_ascii=False)}`",
                f"- immutable Evidence: {decision['immutable_evidence_excerpt']}",
                f"- native table bbox: `{decision['native_table_bbox']}`",
                f"- Evidence geometry: `{json.dumps(decision['evidence_geometry'], ensure_ascii=False)}`",
                f"- Origin eligibility: `{decision['eligibility_decision']}`",
                f"- reason: `{decision['decision_reason']}`",
                f"- boundary version: `{decision['safety_boundary_version']}`",
                "- Human decision: `NOT_EXECUTED`",
                "",
            ]
        )
    lines.extend(
        [
            "STOP. This surface is not a Human Review result and is not Production-ready.",
            "",
        ]
    )
    return "\n".join(lines)


def render_implementation_report(report: dict[str, Any]) -> str:
    replay = report["replay"]
    invariants = report["invariants"]
    tests = report["tests"]
    isolation = report["isolation"]
    return "\n".join(
        [
            "# Phase 3C Table-Derived Claim Safety Boundary V1",
            "",
            "## Outcome",
            "",
            f"- implementation complete: `{str(report['implementation_complete']).lower()}`",
            f"- raw Pilot #5 Claims: `{replay['raw_claims']}`",
            f"- table-derived ineligible: `{replay['table_derived_claims_ineligible']}`",
            f"- review eligible: `{replay['review_eligible_claims']}`",
            f"- non-candidate filtered: `{replay['non_candidate_claims_filtered']}`",
            f"- frozen replay IDs match: `{replay['filtered_claim_ids_match_frozen_replay']}`",
            "",
            "## Implementation boundary",
            "",
            "The V1 helper runs after authoritative Evidence resolution and before "
            "Human Review/downstream eligibility. It consumes canonical page text, the "
            "existing sidecar, and a cached PyMuPDF word pass. It never calls table "
            "detection, interprets table content, or mutates raw Claims/Evidence.",
            "",
            "Ineligible disposition: `TABLE_DERIVED_CLAIM_INELIGIBLE`.",
            "",
            "## Frozen Pilot #5 deterministic replay",
            "",
            f"- selected IDs: `{json.dumps(replay['table_derived_ineligible_claim_ids'], ensure_ascii=False)}`",
            f"- replay deterministic: `{replay['deterministic_replay']}`",
            f"- upstream effective-table leakage: `{replay['upstream_effective_table_suppression_leak_count']}`",
            f"- protected-overlap Claims removed: `{replay['protected_overlap_claims_removed']}`",
            f"- narrative/non-candidate Claims removed: `{replay['non_candidate_claims_filtered']}`",
            f"- raw projection SHA: `{replay['raw_claim_projection_sha256']}`",
            f"- eligible projection SHA: `{replay['eligible_claim_projection_sha256']}`",
            "",
            "## Invariants",
            "",
            *[
                f"- {name}: `{value}`"
                for name, value in invariants.items()
            ],
            "",
            "## Validation",
            "",
            f"- targeted tests: `{tests['targeted_tests']}`",
            f"- full pytest: `{tests['full_pytest']}`",
            f"- frontend tests: `{tests['frontend_tests']}`",
            f"- frontend build: `{tests['frontend_build']}`",
            f"- compileall: `{tests['compileall']}`",
            f"- git diff check: `{tests['git_diff_check']}`",
            "",
            "## Isolation",
            "",
            f"- frozen Pilot #5 changed: `{isolation['frozen_pilot5_changed']}`",
            f"- frozen Pilot #4 changed: `{isolation['frozen_pilot4_changed']}`",
            f"- Production DB changed: `{isolation['production_db_changed']}`",
            f"- Production counts changed: `{isolation['production_table_counts_changed']}`",
            f"- integrity / FK: `{isolation['production_post']['integrity_check']}` / "
            f"`{isolation['production_post']['foreign_key_violations']}`",
            "- IMA / Propagation / Legacy ingestion / Production write: `NO / NO / NO / NO`",
            "",
            "## Next gate",
            "",
            "`Post-Safety-Boundary Independent Clean Pilot #6`",
            "",
            "STOP. Pilot #6 Source was not selected or run. Human Review was not executed.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pilot5-dir", type=Path, required=True)
    parser.add_argument("--pilot4-dir", type=Path, required=True)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--targeted-tests", choices=("PASS", "FAIL", "NOT_RUN"), default="NOT_RUN"
    )
    parser.add_argument(
        "--full-pytest", choices=("PASS", "FAIL", "NOT_RUN"), default="NOT_RUN"
    )
    parser.add_argument(
        "--frontend-tests", choices=("PASS", "FAIL", "NOT_RUN"), default="NOT_RUN"
    )
    parser.add_argument(
        "--frontend-build", choices=("PASS", "FAIL", "NOT_RUN"), default="NOT_RUN"
    )
    parser.add_argument(
        "--compileall", choices=("PASS", "FAIL", "NOT_RUN"), default="NOT_RUN"
    )
    parser.add_argument(
        "--git-diff-check", choices=("PASS", "FAIL", "NOT_RUN"), default="NOT_RUN"
    )
    args = parser.parse_args()

    source = args.source.resolve()
    pilot5_dir = args.pilot5_dir.resolve()
    pilot4_dir = args.pilot4_dir.resolve()
    production_db = args.production_db.resolve()
    output_dir = args.output_dir.resolve()
    repo_root = args.repo_root.resolve()
    if output_dir.is_relative_to(pilot5_dir) or output_dir.is_relative_to(pilot4_dir):
        raise RuntimeError("safety-boundary replay output must be outside frozen Pilots")

    files = {
        "bundle": pilot5_dir / "extraction_bundle_stage1_1_rebound.json",
        "sidecar": pilot5_dir / "source_layout_sidecar.json",
        "evidence": pilot5_dir / "evidence_v2" / "evidence_contract_v2.json",
        "quote": pilot5_dir / "evidence_v2" / "pilot2_gate_a_quote_fidelity.json",
        "human_surface": pilot5_dir / "pilot5_independent_human_review_surface.md",
        "prompt_source": repo_root / "src" / "pro_a" / "prompts.py",
        "table_detector": repo_root / "src" / "pro_a" / "pdf_layout.py",
        "corpus_pilot": repo_root / "src" / "pro_a" / "corpus_pilot.py",
    }
    if file_sha256(source) != SOURCE_SHA256:
        raise RuntimeError("Pilot #5 Source SHA mismatch")
    for name, expected in FROZEN_HASHES.items():
        if file_sha256(files[name]) != expected:
            raise RuntimeError(f"frozen invariant changed before replay: {name}")

    pilot5_pre = tree_snapshot(pilot5_dir)
    pilot4_pre = tree_snapshot(pilot4_dir)
    production_pre = production_snapshot(production_db)
    if pilot5_pre != PILOT5_TREE or pilot4_pre != PILOT4_TREE:
        raise RuntimeError("frozen Pilot tree changed before replay")
    if production_pre["sha256"] != PRODUCTION_SHA256:
        raise RuntimeError("Production changed before replay")

    bundle = load_json(files["bundle"])
    sidecar = load_json(files["sidecar"])
    evidence = load_json(files["evidence"])
    if bundle.get("pilot_run_id") != PILOT_RUN_ID:
        raise RuntimeError("Pilot #5 run ID mismatch")
    claims = bundle.get("claims") or []
    if len(claims) != 50 or len(evidence.get("claims") or []) != 50:
        raise RuntimeError("Pilot #5 raw/Evidence Claim count changed")
    raw_projection = canonical_sha256([claim_projection(claim) for claim in claims])
    if raw_projection != RAW_CLAIM_PROJECTION_SHA256:
        raise RuntimeError("Pilot #5 raw Claim projection changed")
    if ((bundle.get("model") or {}).get("prompt") or {}).get("prompt_sha256") != PROMPT_SHA256:
        raise RuntimeError("Pilot #5 Prompt SHA changed")

    parsed = parse_source_with_diagnostics(source)
    if parsed.source_type != "pdf" or parsed.diagnostics.get("total_units") != 12:
        raise RuntimeError("Pilot #5 canonical PDF parse changed")
    authoritative_pages = []
    for claim in claims:
        locator = ((claim.get("phase3c_evidence") or {}).get("resolved_locator") or {})
        if locator.get("kind") == "single_page" and locator.get("locator"):
            authoritative_pages.append(int(locator["locator"].split(":")[1]))
    word_pages = load_pymupdf_word_pages(source, authoritative_pages)
    first = apply_table_claim_safety_boundary_v1(
        canonical_source_text=parsed.text,
        layout_sidecar=sidecar,
        claims=claims,
        word_pages=word_pages,
    )
    second = apply_table_claim_safety_boundary_v1(
        canonical_source_text=parsed.text,
        layout_sidecar=sidecar,
        claims=claims,
        word_pages=word_pages,
    )
    deterministic = canonical_sha256(first) == canonical_sha256(second)
    filtered_match = tuple(first["table_derived_ineligible_claim_ids"]) == EXPECTED_INELIGIBLE_IDS
    expected_set = set(EXPECTED_INELIGIBLE_IDS)
    non_candidate_filtered = sum(
        claim_id not in expected_set
        for claim_id in first["table_derived_ineligible_claim_ids"]
    )
    protected_overlap_removed = sum(
        not decision["checks"]["native_table_has_no_protected_overlap"]
        for decision in first["ineligible_claim_audit"]
    )
    eligible_claims = [
        claim for claim in claims if claim["claim_id"] in set(first["review_eligible_claim_ids"])
    ]
    eligible_projection = canonical_sha256(
        [claim_projection(claim) for claim in eligible_claims]
    )

    pilot5_post = tree_snapshot(pilot5_dir)
    pilot4_post = tree_snapshot(pilot4_dir)
    production_post = production_snapshot(production_db)
    frozen_hashes_post = {name: file_sha256(path) for name, path in files.items()}
    frozen_hashes_unchanged = all(
        frozen_hashes_post[name] == expected for name, expected in FROZEN_HASHES.items()
    )
    tests = {
        "targeted_tests": args.targeted_tests,
        "full_pytest": args.full_pytest,
        "frontend_tests": args.frontend_tests,
        "frontend_build": args.frontend_build,
        "compileall": args.compileall,
        "git_diff_check": args.git_diff_check,
    }
    validation_complete = all(value == "PASS" for value in tests.values())
    replay_pass = all(
        (
            deterministic,
            filtered_match,
            first["raw_claims"] == 50,
            first["table_derived_claims_ineligible"] == 9,
            first["review_eligible_claims"] == 41,
            non_candidate_filtered == 0,
            protected_overlap_removed == 0,
            first["upstream_effective_table_suppression_leak_count"] == 0,
            first["raw_claims_unchanged"],
        )
    )
    isolation_pass = all(
        (
            pilot5_pre == pilot5_post,
            pilot4_pre == pilot4_post,
            production_pre == production_post,
            production_post["integrity_check"] == "ok",
            production_post["foreign_key_violations"] == 0,
            frozen_hashes_unchanged,
        )
    )
    implementation_complete = replay_pass and isolation_pass and validation_complete

    replay = {
        "document_type": "phase3c_pilot5_table_claim_safety_replay",
        "schema_version": "1",
        "pilot_run_id": PILOT_RUN_ID,
        "boundary_version": TABLE_CLAIM_SAFETY_BOUNDARY_VERSION,
        "status": "PASS" if replay_pass else "FAIL",
        "raw_claims": first["raw_claims"],
        "table_derived_claims_ineligible": first["table_derived_claims_ineligible"],
        "review_eligible_claims": first["review_eligible_claims"],
        "non_candidate_claims_filtered": non_candidate_filtered,
        "table_derived_ineligible_claim_ids": first["table_derived_ineligible_claim_ids"],
        "filtered_claim_ids_match_frozen_replay": "YES" if filtered_match else "NO",
        "review_eligible_claim_ids": first["review_eligible_claim_ids"],
        "ineligible_claim_audit": first["ineligible_claim_audit"],
        "upstream_effective_table_suppression_leak_count": first[
            "upstream_effective_table_suppression_leak_count"
        ],
        "protected_overlap_claims_removed": protected_overlap_removed,
        "deterministic_replay": deterministic,
        "first_result_sha256": canonical_sha256(first),
        "second_result_sha256": canonical_sha256(second),
        "raw_claim_projection_sha256": raw_projection,
        "eligible_claim_projection_sha256": eligible_projection,
        "canonical_source_text_sha256": hashlib.sha256(
            parsed.text.encode("utf-8")
        ).hexdigest(),
        "raw_claims_remain_auditable": True,
        "raw_extraction_redefined_as_41_claims": False,
        "semantic_failure_labels_created": False,
        "human_review_executed": False,
        "llm_calls": 0,
        "semantic_extraction_calls": 0,
    }
    report = {
        "document_type": "phase3c_table_claim_safety_boundary_implementation",
        "schema_version": "1",
        "implementation_complete": implementation_complete,
        "boundary_version": TABLE_CLAIM_SAFETY_BOUNDARY_VERSION,
        "disposition": TABLE_DERIVED_CLAIM_INELIGIBLE,
        "replay": replay,
        "invariants": {
            "CANONICAL_SOURCE_TEXT_CHANGED": "NO",
            "RAW_CLAIM_PROJECTION_CHANGED": "NO",
            "EVIDENCE_CONTRACT_CHANGED": "NO",
            "PROMPT_CHANGED": "NO",
            "TABLE_DETECTOR_CHANGED": "NO",
            "PRODUCTION_SCHEMA_CHANGED": "NO",
            "LOCAL_SUBSPAN_BEHAVIOR_CHANGED": "NO",
        },
        "tests": tests,
        "implementation": {
            "module": "src/pro_a/table_claim_safety.py",
            "module_sha256": file_sha256(repo_root / "src" / "pro_a" / "table_claim_safety.py"),
            "table_detection_invoked": False,
            "word_geometry_pages_loaded_once": sorted(word_pages),
            "claim_ids_used_by_runtime_predicate": False,
            "claim_wording_used": False,
            "numeric_or_financial_heuristics_used": False,
            "model_confidence_used": False,
        },
        "isolation": {
            "pilot5_pre": pilot5_pre,
            "pilot5_post": pilot5_post,
            "frozen_pilot5_changed": "NO" if pilot5_pre == pilot5_post else "YES",
            "pilot4_pre": pilot4_pre,
            "pilot4_post": pilot4_post,
            "frozen_pilot4_changed": "NO" if pilot4_pre == pilot4_post else "YES",
            "production_pre": production_pre,
            "production_post": production_post,
            "production_db_changed": "NO" if production_pre == production_post else "YES",
            "production_table_counts_changed": "NO" if production_pre["table_counts"] == production_post["table_counts"] else "YES",
            "frozen_artifact_hashes_post": frozen_hashes_post,
            "frozen_artifact_hashes_unchanged": frozen_hashes_unchanged,
            "ima_invoked": False,
            "propagation_invoked": False,
            "legacy_ingestion_invoked": False,
            "production_write": False,
        },
        "phase_state": {
            "PHASE3C_COMPLETE": False,
            "PRODUCTION_APPLY_READY": "NO",
            "PHASE3C_NEXT_GATE": "Post-Safety-Boundary Independent Clean Pilot #6",
            "STOP_CONFIRMATION": "STOPPED_BEFORE_PILOT6_HUMAN_REVIEW_AND_PRODUCTION",
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    replay_path = output_dir / "phase3c_pilot5_table_claim_safety_replay.json"
    surface_path = output_dir / "phase3c_pilot5_counterfactual_eligible_review_surface.md"
    report_path = output_dir / "phase3c_table_claim_safety_boundary_implementation_report.md"
    replay_path.write_text(
        json.dumps(replay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    claims_by_id = {claim["claim_id"]: claim for claim in claims}
    surface_path.write_text(
        render_counterfactual_surface(claims_by_id=claims_by_id, result=first),
        encoding="utf-8",
    )
    report_path.write_text(render_implementation_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "implementation_complete": implementation_complete,
                "replay_status": replay["status"],
                "raw_claims": replay["raw_claims"],
                "ineligible": replay["table_derived_claims_ineligible"],
                "eligible": replay["review_eligible_claims"],
                "non_candidate_filtered": replay["non_candidate_claims_filtered"],
                "filtered_ids_match": replay["filtered_claim_ids_match_frozen_replay"],
                "deterministic": replay["deterministic_replay"],
                "next_gate": report["phase_state"]["PHASE3C_NEXT_GATE"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if replay_pass and isolation_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
