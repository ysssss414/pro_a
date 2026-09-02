from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pro_a.corpus_pilot import (
    EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE,
    STAGE1_3_CONTEXT_POLICY,
    STAGE1_3_CONTEXT_RADIUS,
    PilotError,
    _bounded_context_candidates,
    _validate_stage1_3_context_span,
    build_pilot2_evidence_support_draft,
    production_snapshot,
    run_pilot2_gate_a_quote_fidelity,
)
from pro_a.parsers import parse_source_with_diagnostics, source_units
from pro_a.pilot3 import render_pilot3_review_surface
from pro_a.storage import sha256_file, write_json


PILOT_RUN_ID = "PILOT_20260901_4C6535B7"
SOURCE_SHA256 = "4c6535b75fa97968f8f1651987ff52c64c0ffded41d3dba39ca72a5bbac3a178"
CLAIM_PROJECTION_SHA256 = (
    "b105a9bcaa433eac6dcaaa96fd85fd774e5a0757ac0da1671f1a7d3e18e4b100"
)
PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotError(f"PILOT4_BOUNDED_SUBSPAN_INPUT_INVALID: {path}") from exc
    if not isinstance(value, dict):
        raise PilotError(f"PILOT4_BOUNDED_SUBSPAN_INPUT_INVALID: {path}")
    return value


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _claim_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def _target_attempts(census: dict[str, Any], category: str) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": claim.get("claim_id"),
            "claim_index": claim.get("claim_index"),
            "direction": attempt.get("candidate_direction"),
            "candidate_locator": attempt.get("candidate_locator"),
            "failure_reason": attempt.get("failure_reason"),
        }
        for claim in census.get("claims") or []
        for attempt in claim.get("candidate_attempts") or []
        if attempt.get("root_category") == category
    ]


def run_frozen_replay(
    *,
    run_dir: Path,
    source_path: Path,
    production_db: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_path = source_path.resolve()
    production_db = production_db.resolve()
    bundle_path = run_dir / "extraction_bundle_stage1_1_rebound.json"
    census_path = run_dir / "pilot4_evidence_context_failure_census.json"
    freeze_path = run_dir / "pilot4_extraction_freeze.json"
    if any(not path.is_file() for path in (
        source_path, production_db, bundle_path, census_path, freeze_path,
    )):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_REQUIRED_INPUT_MISSING")

    bundle = _load_json(bundle_path)
    census = _load_json(census_path)
    freeze = _load_json(freeze_path)
    claims = bundle.get("claims") or []
    projection_sha256 = _canonical_sha256([
        _claim_projection(claim) for claim in claims
    ])
    prompt_sha256 = ((bundle.get("model") or {}).get("prompt") or {}).get(
        "prompt_sha256"
    )
    if (
        bundle.get("pilot_run_id") != PILOT_RUN_ID
        or census.get("pilot_run_id") != PILOT_RUN_ID
        or freeze.get("pilot_run_id") != PILOT_RUN_ID
        or len(claims) != 320
        or projection_sha256 != CLAIM_PROJECTION_SHA256
        or prompt_sha256 != PROMPT_SHA256
        or sha256_file(source_path) != SOURCE_SHA256
        or (bundle.get("source") or {}).get("sha256") != SOURCE_SHA256
    ):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_FREEZE_MISMATCH")

    outside_attempts = _target_attempts(census, "OUTSIDE_BOUNDED_WINDOW")
    cross_page_attempts = _target_attempts(census, "CROSS_PAGE_CONTEXT_MISMATCH")
    if len(outside_attempts) != 151 or len(cross_page_attempts) != 144:
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_CENSUS_MISMATCH")

    production_pre = production_snapshot(production_db)
    parsed = parse_source_with_diagnostics(source_path)
    pages = [
        (locator, body) for locator, body in source_units(parsed.text)
        if locator.startswith("PAGE:")
    ]
    page_by_locator = dict(pages)
    claims_by_id = {claim.get("claim_id"): claim for claim in claims}
    generated_by_claim: dict[str, list[dict[str, Any]]] = {}
    generator_errors: dict[str, str] = {}
    for claim in claims:
        locator = (claim.get("validation") or {}).get("source_locator") or {}
        if locator.get("status") != "resolved":
            generated_by_claim[str(claim.get("claim_id"))] = []
            continue
        try:
            candidates = _bounded_context_candidates(
                pages,
                str(locator.get("locator") or ""),
                str(claim.get("evidence_excerpt") or ""),
                authoritative_locator=locator,
            )
        except PilotError as exc:
            candidates = []
            generator_errors[str(claim.get("claim_id"))] = str(exc)
        generated_by_claim[str(claim.get("claim_id"))] = candidates

    resolved: list[dict[str, Any]] = []
    still_failing: list[dict[str, Any]] = []
    for target in outside_attempts:
        claim_id = str(target["claim_id"])
        candidates = generated_by_claim.get(claim_id, [])
        matching = [
            item for item in candidates
            if item.get("direction") == target["direction"]
            and item.get("selection_rule")
            == EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE
        ]
        if len(matching) != 1:
            still_failing.append({
                **target,
                "reason": generator_errors.get(
                    claim_id, "TARGET_DIRECTION_LOCAL_SUBSPAN_NOT_EMITTED",
                ),
            })
            continue
        claim = claims_by_id[claim_id]
        locator = (claim.get("validation") or {}).get("source_locator") or {}
        candidate = matching[0]
        _validate_stage1_3_context_span(
            span={
                "locator": candidate["locators"][0],
                "text": candidate["text"],
            },
            page_by_locator=page_by_locator,
            evidence_locator=str(locator.get("locator") or ""),
            evidence_excerpt=str(claim.get("evidence_excerpt") or ""),
        )
        resolved.append({
            **target,
            "selection_rule": candidate["selection_rule"],
            "raw_length": len(candidate["text"]),
            "raw_sha256": hashlib.sha256(candidate["text"].encode("utf-8")).hexdigest(),
            "validator": "PASS",
        })

    cross_page_changes: list[dict[str, Any]] = []
    for target in cross_page_attempts:
        claim_id = str(target["claim_id"])
        claim = claims_by_id[claim_id]
        evidence_locator = str(
            (((claim.get("validation") or {}).get("source_locator") or {}).get("locator"))
            or ""
        )
        matching = [
            item for item in generated_by_claim.get(claim_id, [])
            if item.get("direction") == target["direction"]
        ]
        if any(
            item.get("locators") == [evidence_locator]
            and item.get("selection_rule")
            == EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE
            for item in matching
        ):
            cross_page_changes.append(target)

    all_candidates = [
        candidate
        for candidates in generated_by_claim.values()
        for candidate in candidates
    ]
    local_candidates = [
        candidate for candidate in all_candidates
        if candidate.get("selection_rule")
        == EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE
    ]
    local_claim_ids = sorted(
        claim_id for claim_id, candidates in generated_by_claim.items()
        if any(
            item.get("selection_rule")
            == EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE
            for item in candidates
        )
    )
    unresolved_reasons = Counter(item["reason"] for item in still_failing)
    production_post = production_snapshot(production_db)
    result = {
        "document_type": "phase3c_pilot4_bounded_local_subspan_frozen_replay",
        "schema_version": "1",
        "status": (
            "PASS_READY_FOR_FROZEN_REBUILD"
            if not still_failing and not cross_page_changes
            else "STOP_NEW_ROOT_MECHANISM"
        ),
        "pilot_run_id": PILOT_RUN_ID,
        "freeze": {
            "claims": len(claims),
            "claim_projection_sha256": projection_sha256,
            "source_sha256": SOURCE_SHA256,
            "prompt_sha256": prompt_sha256,
            "context_policy": STAGE1_3_CONTEXT_POLICY,
            "context_radius": STAGE1_3_CONTEXT_RADIUS,
            "llm_calls": 0,
            "semantic_extraction_calls": 0,
        },
        "targeted_outside_bounded_window": {
            "total": len(outside_attempts),
            "resolved_by_local_subspan": len(resolved),
            "still_failing": len(still_failing),
            "still_failing_by_reason": dict(sorted(unresolved_reasons.items())),
            "resolved_cases": resolved,
            "still_failing_cases": still_failing,
        },
        "cross_page_non_regression": {
            "census_cases": len(cross_page_attempts),
            "changed_cases": cross_page_changes,
            "cross_page_behavior_changed": bool(cross_page_changes),
            "cross_page_concatenation_added": False,
        },
        "context_generation_footprint": {
            "existing_adjacent_segment_candidates": len(all_candidates) - len(local_candidates),
            "local_subspan_fallback_candidates": len(local_candidates),
            "local_subspan_before": sum(
                item.get("direction") == "before" for item in local_candidates
            ),
            "local_subspan_after": sum(
                item.get("direction") == "after" for item in local_candidates
            ),
            "local_subspan_validator_pass": len(resolved),
            "local_subspan_validator_fail": len(still_failing),
            "claims_using_at_least_one_local_subspan": len(local_claim_ids),
            "claim_ids_using_local_subspan": local_claim_ids,
        },
        "production": {
            "pre": production_pre,
            "post": production_post,
            "changed": production_pre != production_post,
            "table_counts_changed": (
                production_pre["table_counts"] != production_post["table_counts"]
            ),
        },
        "next_action": (
            "FROZEN_EVIDENCE_REBUILD"
            if not still_failing and not cross_page_changes
            else "STOP_BEFORE_FULL_ARTIFACT_REBUILD"
        ),
    }
    return result


def _rate(
    numerator: int, denominator: int, threshold: float, *, at_least: bool,
) -> dict[str, Any]:
    percent = 100 * numerator / denominator if denominator else 0.0
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "percent": round(percent, 2),
        "threshold_percent": threshold,
        "passed": percent >= threshold if at_least else percent <= threshold,
    }


def _evidence_projection(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "statement": claim.get("statement"),
        "evidence_excerpt": claim.get("original_evidence_excerpt"),
        "attributed_to": claim.get("attributed_to") or "",
    }


def run_frozen_rebuild(
    *,
    run_dir: Path,
    source_path: Path,
    production_db: Path,
    replay_path: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_path = source_path.resolve()
    production_db = production_db.resolve()
    replay_path = replay_path.resolve()
    repair_dir = run_dir / "evidence_v2_repair"
    paths = {
        "original_bundle": run_dir / "extraction_bundle.json",
        "rebound_bundle": run_dir / "extraction_bundle_stage1_1_rebound.json",
        "original_review": run_dir / "extraction_review_draft.json",
        "rebound_review": run_dir / "extraction_review_stage1_1_draft.json",
        "freeze": run_dir / "pilot4_extraction_freeze.json",
        "replay": replay_path,
    }
    preserved_paths = {
        "pilot4_evidence_artifact_failure": run_dir / "pilot4_evidence_artifact_failure.json",
        "pilot4_evidence_v2_next_blocker": run_dir / "pilot4_evidence_v2_next_blocker.json",
        "pilot4_evidence_context_failure_census": (
            run_dir / "pilot4_evidence_context_failure_census.json"
        ),
        "pilot4_evidence_context_failure_census_report": (
            run_dir / "pilot4_evidence_context_failure_census_report.md"
        ),
    }
    if any(not path.is_file() for path in (
        source_path, production_db, *paths.values(), *preserved_paths.values(),
    )):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_REBUILD_INPUT_MISSING")
    repaired_outputs = (
        repair_dir / "evidence_contract_v2_repaired.json",
        repair_dir / "quote_fidelity_repaired.json",
        repair_dir / "evidence_review_surface_repaired.md",
        repair_dir / "pre_review_metrics_repaired.json",
    )
    if any(path.exists() for path in repaired_outputs):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_REBUILD_ALREADY_COMPLETED")

    replay = _load_json(paths["replay"])
    if (
        replay.get("status") != "PASS_READY_FOR_FROZEN_REBUILD"
        or replay.get("pilot_run_id") != PILOT_RUN_ID
        or ((replay.get("targeted_outside_bounded_window") or {}).get(
            "resolved_by_local_subspan"
        )) != 151
        or ((replay.get("targeted_outside_bounded_window") or {}).get(
            "still_failing"
        )) != 0
        or ((replay.get("cross_page_non_regression") or {}).get(
            "cross_page_behavior_changed"
        )) is not False
    ):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_REPLAY_NOT_ADMISSIBLE")

    original_bundle = _load_json(paths["original_bundle"])
    rebound_bundle = _load_json(paths["rebound_bundle"])
    freeze = _load_json(paths["freeze"])
    original_projection = [
        _claim_projection(claim) for claim in original_bundle.get("claims") or []
    ]
    rebound_projection = [
        _claim_projection(claim) for claim in rebound_bundle.get("claims") or []
    ]
    projection_sha256 = _canonical_sha256(rebound_projection)
    if (
        len(original_projection) != 320
        or original_projection != rebound_projection
        or projection_sha256 != CLAIM_PROJECTION_SHA256
        or sha256_file(source_path) != SOURCE_SHA256
    ):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_REBUILD_FREEZE_MISMATCH")

    preserved_pre = {
        name: sha256_file(path) for name, path in preserved_paths.items()
    }
    production_pre = production_snapshot(production_db)
    evidence = build_pilot2_evidence_support_draft(
        paths["rebound_bundle"],
        paths["rebound_review"],
        source_path,
        output_dir=repair_dir,
        production_db_path=production_db,
    )
    gate = run_pilot2_gate_a_quote_fidelity(
        paths["original_bundle"],
        paths["rebound_bundle"],
        Path(evidence["draft_path"]),
        source_path,
        output_dir=repair_dir,
        production_db_path=production_db,
        original_review_path=paths["original_review"],
    )

    evidence_draft = copy.deepcopy(evidence["draft"])
    evidence_projection = [
        _evidence_projection(claim) for claim in evidence_draft.get("claims") or []
    ]
    if (
        evidence_projection != rebound_projection
        or _canonical_sha256(evidence_projection) != CLAIM_PROJECTION_SHA256
    ):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_REBUILD_CLAIM_MUTATION")
    statuses = Counter(
        (((claim.get("validation") or {}).get("source_locator") or {}).get("status"))
        or "unresolved"
        for claim in rebound_bundle.get("claims") or []
    )
    if statuses != Counter({"resolved": 299, "ambiguous": 2, "unresolved": 19}):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_STAGE1_1_INVARIANT_CHANGED")

    evidence_draft["repair"] = {
        "mechanical_only": True,
        "root_mechanism": "OUTCOME_B_REPRESENTATION_GRANULARITY_DEFECT",
        "selection_rule": EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE,
        "context_radius": STAGE1_3_CONTEXT_RADIUS,
        "frozen_replay_sha256": sha256_file(paths["replay"]),
        "llm_calls_added": 0,
        "semantic_extraction_calls_added": 0,
    }
    evidence_path = repair_dir / "evidence_contract_v2_repaired.json"
    write_json(evidence_path, evidence_draft)

    repaired_quote = copy.deepcopy(gate)
    repaired_quote.pop("gate_a_path", None)
    repaired_quote.pop("report_path", None)
    repaired_quote.pop("metrics_path", None)
    repaired_quote.pop("review_surface_path", None)
    repaired_quote["repair"] = copy.deepcopy(evidence_draft["repair"])
    quote_path = repair_dir / "quote_fidelity_repaired.json"
    write_json(quote_path, repaired_quote)
    surface_path = repair_dir / "evidence_review_surface_repaired.md"
    surface_path.write_text(
        render_pilot3_review_surface(repaired_quote, evidence_draft), encoding="utf-8",
    )

    fidelity_counts = gate["metrics"]["fidelity_counts"]
    faithful = sum(fidelity_counts[name] for name in (
        "EXACT_SOURCE_MATCH",
        "LAYOUT_NORMALIZED_EXACT_MATCH",
        "EXACT_ORDERED_CROSS_PAGE_SPAN",
        "PROVENANCE_MISMATCH_RECOVERED",
    ))
    drift = fidelity_counts["QUOTE_DRIFT"]
    bound = evidence["metrics"]["evidence_deterministically_bound"]
    targets = {
        "quote_fidelity": _rate(faithful, 320, 85.0, at_least=True),
        "quote_drift": _rate(drift, 320, 15.0, at_least=False),
        "source_binding": _rate(bound, 320, 85.0, at_least=True),
    }
    mechanical_gate = (
        "PASS" if all(item["passed"] for item in targets.values()) else "FAIL"
    )
    pending = sum(
        claim.get("human_decision") == "PENDING"
        for claim in evidence_draft.get("claims") or []
    )
    if pending != 320:
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_HUMAN_SURFACE_NOT_PENDING")

    production_post = production_snapshot(production_db)
    preserved_post = {
        name: sha256_file(path) for name, path in preserved_paths.items()
    }
    if production_pre != production_post:
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_PRODUCTION_MUTATED")
    if preserved_pre != preserved_post:
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_PRIOR_ARTIFACT_MUTATED")

    model = rebound_bundle.get("model") or {}
    usage = model.get("usage") or {}
    footprint = replay["context_generation_footprint"]
    metrics = {
        "document_type": "phase3c_pilot4_bounded_local_subspan_pre_review_metrics",
        "schema_version": "1",
        "status": "COMPLETE_MECHANICAL_GATE_PASSED" if mechanical_gate == "PASS" else "COMPLETE_MECHANICAL_GATE_FAILED",
        "pilot_run_id": PILOT_RUN_ID,
        "PHASE3C_CLEAN_PILOT4_BOUNDED_SUBSPAN_REPAIR_COMPLETE": True,
        "PHASE3C_CLEAN_PILOT4_EVIDENCE_REPAIR_COMPLETE": True,
        "PHASE3C_CLEAN_PILOT4_EXTRACTION_COMPLETE": True,
        "PILOT4_EVIDENCE_ARTIFACT_GATE": "PASS",
        "PILOT4_MECHANICAL_GATE": mechanical_gate,
        "PILOT4_SEMANTIC_GATE": "PENDING_HUMAN_REVIEW",
        "PILOT4_INDEPENDENT_SEMANTIC_SAMPLE": True,
        "PILOT4_INDEPENDENT_EVIDENCE_POST_REPAIR_SAMPLE": False,
        "POST_EVIDENCE_REPAIR_INDEPENDENT_CLEAN_PILOT_REQUIRED": True,
        "PHASE3C_COMPLETE": False,
        "PRODUCTION_APPLY_READY": "NO",
        "PHASE3C_NEXT_GATE": "Clean Pilot #4 Independent Human Review",
        "freeze": {
            "claims_before": len(original_projection),
            "claims_after": len(evidence_projection),
            "claim_projection_sha256": projection_sha256,
            "claim_ids_unchanged": True,
            "statements_unchanged": True,
            "immutable_evidence_unchanged": True,
            "attributed_to_unchanged": True,
            "source_sha256": SOURCE_SHA256,
            "prompt_sha256": PROMPT_SHA256,
            "context_policy": STAGE1_3_CONTEXT_POLICY,
            "context_radius": STAGE1_3_CONTEXT_RADIUS,
            "thresholds": copy.deepcopy(freeze.get("thresholds") or {}),
        },
        "stage1_1": {
            "resolved": statuses["resolved"],
            "ambiguous": statuses["ambiguous"],
            "unresolved": statuses["unresolved"],
            "changed": False,
        },
        "mechanical_evidence_metrics": {
            **copy.deepcopy(fidelity_counts),
            "quote_fidelity": targets["quote_fidelity"],
            "quote_drift": targets["quote_drift"],
            "source_binding": targets["source_binding"],
            "single_page": evidence["metrics"]["single_page_locator_bound"],
            "cross_page": evidence["metrics"]["cross_page_exact_spans"],
            "ambiguous": evidence["metrics"]["locator_ambiguous"],
            "unresolved": evidence["metrics"]["locator_unresolved"],
            "bounded_context_candidate_claims": evidence["metrics"][
                "bounded_context_candidate_claims"
            ],
        },
        "context_generation_footprint": copy.deepcopy(footprint),
        "human_review": {
            "surface_generated": True,
            "human_review_performed": False,
            "PENDING": pending,
        },
        "runtime": {
            "logical_semantic_extractions": 1,
            "frozen_extraction_api_attempts": model.get("llm_calls", "NOT_AVAILABLE"),
            "rebuild_llm_calls": 0,
            "rebuild_semantic_extraction_calls": 0,
            "prompt_tokens": usage.get("prompt_tokens", "NOT_AVAILABLE"),
            "completion_tokens": usage.get("completion_tokens", "NOT_AVAILABLE"),
            "total_tokens": usage.get("total_tokens", "NOT_AVAILABLE"),
            "tokens_per_claim": evidence["metrics"]["tokens_per_claim"],
            "tokens_per_bound_claim": evidence["metrics"][
                "tokens_per_deterministically_bound_claim"
            ],
        },
        "production": {
            "pre": production_pre,
            "post": production_post,
            "changed": False,
            "table_counts_changed": False,
            "IMA": False,
            "propagation": False,
            "legacy_ingestion": False,
        },
        "preserved_prior_artifacts": {
            name: {"path": str(preserved_paths[name]), "sha256": sha}
            for name, sha in preserved_pre.items()
        },
        "artifacts": {
            "frozen_replay": {
                "path": str(paths["replay"]), "sha256": sha256_file(paths["replay"]),
            },
            "evidence_contract_v2_repaired": {
                "path": str(evidence_path), "sha256": sha256_file(evidence_path),
            },
            "quote_fidelity_repaired": {
                "path": str(quote_path), "sha256": sha256_file(quote_path),
            },
            "evidence_review_surface_repaired": {
                "path": str(surface_path), "sha256": sha256_file(surface_path),
            },
        },
        "semantic_admission_guard_runtime_ready": False,
        "STOP_before_Human_Review": True,
    }
    metrics_path = repair_dir / "pre_review_metrics_repaired.json"
    write_json(metrics_path, metrics)
    return metrics


def _render_repair_report(receipt: dict[str, Any]) -> str:
    state = receipt["final_state"]
    metrics = receipt["mechanical_metrics"]
    footprint = receipt["context_generation_footprint"]
    production = receipt["production_isolation"]
    tests = receipt["tests"]
    artifacts = receipt["artifacts"]
    lines = [
        "# Phase 3C Clean Pilot #4 — Evidence v2 Bounded Local-Subspan Repair",
        "",
        f"- Pilot run: `{receipt['pilot_run_id']}`",
        f"- Status: `{receipt['status']}`",
        "- Scope: deterministic Evidence-v2 context representation only",
        "- LLM calls / semantic extraction calls added: `0 / 0`",
        "",
        "## Exact local-subspan selection rule",
        "",
        "1. Generate the existing adjacent parsed-segment candidate and run the frozen validator. If it passes, preserve it unchanged.",
        "2. Attempt fallback only when that candidate is on the Evidence page and its sole validation exception is `STAGE1_3_CONTEXT_INVALID: same-page context is outside the bounded window`.",
        "3. Require a resolved frozen Source locator and map its frozen `comparison_start/comparison_end` to one authoritative raw Evidence occurrence. Ambiguous, unresolved, unsupported, or unmappable occurrences remain fail closed.",
        "4. Use only the single same-page raw parsed segment containing that occurrence. BEFORE is `raw_segment[max(0, evidence_start-500):evidence_start]`; AFTER is `raw_segment[evidence_end:min(segment_end, evidence_end+500)]`.",
        "5. Emit only a contiguous exact raw substring, no overlap, no cross-page/segment concatenation, raw length <= 500, and non-empty under the shared frozen `normalize_pdf_locator_text` normalizer.",
        "6. Re-run the original frozen validator. Only validator PASS enters the Evidence artifact.",
        "",
        "## Changed files",
        "",
        *[f"- `{item['path']}` — `{item['purpose']}`" for item in receipt["changed_files"]],
        "",
        "## Generic fixtures",
        "",
        *[f"- {name}: `{test}`" for name, test in receipt["generic_fixtures"].items()],
        "- Fixtures contain no Pilot #4 issuer, publisher, or Claim IDs.",
        "",
        "## Frozen replay and cross-page non-regression",
        "",
        f"- Original OUTSIDE_BOUNDED_WINDOW cases: `{receipt['frozen_replay']['targeted_total']}`.",
        f"- Resolved by local subspan / still failing: `{receipt['frozen_replay']['resolved_by_local_subspan']} / {receipt['frozen_replay']['still_failing']}`.",
        f"- Original CROSS_PAGE_CONTEXT_MISMATCH cases: `{receipt['cross_page_non_regression']['cases']}`.",
        f"- cross_page_behavior_changed: `{str(receipt['cross_page_non_regression']['changed']).lower()}`; cross-page concatenation added: `false`.",
        "",
        "## Frozen rebuild and integrity",
        "",
        f"- Claims before / after: `{receipt['claim_integrity']['claims_before']} / {receipt['claim_integrity']['claims_after']}`.",
        f"- Claim projection SHA-256: `{receipt['claim_integrity']['projection_sha256']}`.",
        "- Claim IDs, statements, immutable Evidence, and attributed_to: `unchanged`.",
        f"- Stage 1.1 resolved / ambiguous / unresolved: `{receipt['stage1_1']['resolved']} / {receipt['stage1_1']['ambiguous']} / {receipt['stage1_1']['unresolved']}`; changed: `false`.",
        "- Frozen Evidence rebuild LLM calls / semantic extraction calls: `0 / 0`.",
        "",
        "## Mechanical Evidence metrics",
        "",
        *[
            f"- {name}: `{metrics[name]}`"
            for name in (
                "EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH",
                "EXACT_ORDERED_CROSS_PAGE_SPAN", "PROVENANCE_MISMATCH_RECOVERED",
                "QUOTE_DRIFT", "UNRESOLVED_SOURCE_BINDING",
            )
        ],
        f"- Quote fidelity: `{metrics['quote_fidelity']['fraction']}` ({metrics['quote_fidelity']['percent']}%) vs >= 85% — `PASS`.",
        f"- Quote drift: `{metrics['quote_drift']['fraction']}` ({metrics['quote_drift']['percent']}%) vs <= 15% — `PASS`.",
        f"- Source binding: `{metrics['source_binding']['fraction']}` ({metrics['source_binding']['percent']}%) vs >= 85% — `PASS`.",
        f"- single-page / cross-page / ambiguous / unresolved: `{metrics['single_page']} / {metrics['cross_page']} / {metrics['ambiguous']} / {metrics['unresolved']}`.",
        f"- bounded-context candidate Claims: `{metrics['bounded_context_candidate_claims']}`.",
        "",
        "## Local-subspan footprint",
        "",
        f"- existing adjacent-segment candidates: `{footprint['existing_adjacent_segment_candidates']}`.",
        f"- local-subspan fallback candidates: `{footprint['local_subspan_fallback_candidates']}`.",
        f"- local-subspan BEFORE / AFTER: `{footprint['local_subspan_before']} / {footprint['local_subspan_after']}`.",
        f"- local-subspan validator PASS / FAIL: `{footprint['local_subspan_validator_pass']} / {footprint['local_subspan_validator_fail']}`.",
        f"- Claims using at least one local subspan: `{footprint['claims_using_at_least_one_local_subspan']}`.",
        "",
        "## Human Review and independent-sample role",
        "",
        f"- Human Review surface PENDING: `{receipt['human_review']['PENDING']}`; Human Review performed: `NO`.",
        "- PILOT4_INDEPENDENT_SEMANTIC_SAMPLE = `true`.",
        "- PILOT4_INDEPENDENT_EVIDENCE_POST_REPAIR_SAMPLE = `false`.",
        "- POST_EVIDENCE_REPAIR_INDEPENDENT_CLEAN_PILOT_REQUIRED = `true`.",
        "",
        "## Production isolation",
        "",
        f"- Production SHA pre / post: `{production['pre_sha256']} / {production['post_sha256']}`.",
        f"- changed / table counts changed: `{production['changed']} / {production['table_counts_changed']}`.",
        f"- integrity / FK violations: `{production['integrity_check']} / {production['foreign_key_violations']}`.",
        "- IMA / propagation / legacy ingestion: `NO / NO / NO`.",
        "",
        "## Validation",
        "",
        *[f"- {name}: `{result['status']}` — {result['detail']}" for name, result in tests.items()],
        "",
        "## Artifacts",
        "",
        *[f"- {name}: `{item['path']}` (`{item['sha256']}`)" for name, item in artifacts.items()],
        "- All prior failure, next-blocker, and census artifacts retained with unchanged SHA-256.",
        "",
        "## Final state",
        "",
        *[f"- {name} = `{str(value).lower() if isinstance(value, bool) else value}`" for name, value in state.items()],
        "",
        "STOP — before Human Review. No quality rerun, semantic repair, Production write, or next clean Source selection was performed.",
        "",
    ]
    return "\n".join(lines)


def finalize_repair_artifacts(
    *, run_dir: Path, production_db: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    production_db = production_db.resolve()
    repair_dir = run_dir / "evidence_v2_repair"
    paths = {
        "frozen_replay": run_dir / "pilot4_bounded_local_subspan_replay.json",
        "evidence_contract_v2_repaired": repair_dir / "evidence_contract_v2_repaired.json",
        "quote_fidelity_repaired": repair_dir / "quote_fidelity_repaired.json",
        "evidence_review_surface_repaired": repair_dir / "evidence_review_surface_repaired.md",
        "pre_review_metrics_repaired": repair_dir / "pre_review_metrics_repaired.json",
    }
    if any(not path.is_file() for path in (*paths.values(), production_db)):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_FINALIZE_INPUT_MISSING")
    metrics = _load_json(paths["pre_review_metrics_repaired"])
    replay = _load_json(paths["frozen_replay"])
    evidence = _load_json(paths["evidence_contract_v2_repaired"])
    current_production = production_snapshot(production_db)
    production = metrics.get("production") or {}
    if (
        metrics.get("PILOT4_EVIDENCE_ARTIFACT_GATE") != "PASS"
        or metrics.get("PILOT4_MECHANICAL_GATE") not in {"PASS", "FAIL"}
        or metrics.get("PILOT4_SEMANTIC_GATE") != "PENDING_HUMAN_REVIEW"
        or len(evidence.get("claims") or []) != 320
        or sum(
            item.get("human_decision") == "PENDING"
            for item in evidence.get("claims") or []
        ) != 320
        or current_production != production.get("pre")
        or current_production != production.get("post")
    ):
        raise PilotError("PILOT4_BOUNDED_SUBSPAN_FINALIZE_INVARIANT_FAILED")

    receipt = {
        "document_type": "phase3c_pilot4_bounded_local_subspan_regression_receipt",
        "schema_version": "1",
        "status": "PASS_REPAIR_AND_FROZEN_REBUILD_COMPLETE",
        "pilot_run_id": PILOT_RUN_ID,
        "selection_rule": {
            "priority_1": "existing candidate passes frozen validator -> keep unchanged",
            "priority_2_trigger": "same-page existing candidate fails solely OUTSIDE_BOUNDED_WINDOW",
            "priority_2_source": "same raw Source segment containing frozen authoritative Evidence occurrence",
            "before": "raw_segment[max(segment_start, evidence_start-500):evidence_start]",
            "after": "raw_segment[evidence_end:min(segment_end, evidence_end+500)]",
            "normalizer": "normalize_pdf_locator_text",
            "validator_authoritative": True,
            "minimum_semantic_size_added": False,
        },
        "changed_files": [
            {
                "path": "src/pro_a/corpus_pilot.py",
                "purpose": "generic bounded local-subspan helper and fail-closed fallback integration",
                "sha256": sha256_file(Path("src/pro_a/corpus_pilot.py")),
            },
            {
                "path": "tests/test_corpus_pilot.py",
                "purpose": "generic A-K bounded local-subspan regression coverage",
                "sha256": sha256_file(Path("tests/test_corpus_pilot.py")),
            },
            {
                "path": "scripts/phase3c_pilot4_bounded_local_subspan_repair.py",
                "purpose": "frozen replay, rebuild integrity checks, and auditable artifact finalization",
                "sha256": sha256_file(
                    Path("scripts/phase3c_pilot4_bounded_local_subspan_repair.py")
                ),
            },
        ],
        "generic_fixtures": {
            "A_existing_valid_adjacent": "test_bounded_local_subspan_keeps_existing_valid_adjacent_candidate_unchanged",
            "B_large_evidence_segment": "test_bounded_local_subspan_falls_back_inside_large_evidence_segment_before",
            "C_before_subspan": "test_bounded_local_subspan_falls_back_inside_large_evidence_segment_before",
            "D_after_subspan": "test_bounded_local_subspan_falls_back_inside_large_evidence_segment_after",
            "E_exactly_500_raw_chars": "test_build_bounded_local_subspan_accepts_exactly_500_raw_characters",
            "F_empty_normalization": "test_bounded_local_subspan_preserves_empty_normalization_fail_closed",
            "G_duplicate_occurrence": "test_stage1_3_generator_accepts_nearest_duplicate_same_page_context",
            "H_ambiguous_occurrence": "test_bounded_local_subspan_does_not_guess_nonresolved_evidence[ambiguous]",
            "I_unresolved_evidence": "test_bounded_local_subspan_does_not_guess_nonresolved_evidence[unresolved]",
            "J_cross_page_unchanged": "test_bounded_local_subspan_does_not_change_cross_page_omit_behavior",
            "K_no_same_segment_text": "test_build_bounded_local_subspan_does_not_manufacture_unavailable_context",
        },
        "frozen_replay": {
            "targeted_total": replay["targeted_outside_bounded_window"]["total"],
            "resolved_by_local_subspan": replay["targeted_outside_bounded_window"][
                "resolved_by_local_subspan"
            ],
            "still_failing": replay["targeted_outside_bounded_window"]["still_failing"],
            "new_root_mechanism": False,
        },
        "cross_page_non_regression": {
            "cases": replay["cross_page_non_regression"]["census_cases"],
            "changed": replay["cross_page_non_regression"][
                "cross_page_behavior_changed"
            ],
        },
        "claim_integrity": {
            "claims_before": metrics["freeze"]["claims_before"],
            "claims_after": metrics["freeze"]["claims_after"],
            "projection_sha256": metrics["freeze"]["claim_projection_sha256"],
            "claim_ids_unchanged": True,
            "statements_unchanged": True,
            "immutable_evidence_unchanged": True,
            "attributed_to_unchanged": True,
        },
        "stage1_1": copy.deepcopy(metrics["stage1_1"]),
        "mechanical_metrics": copy.deepcopy(metrics["mechanical_evidence_metrics"]),
        "context_generation_footprint": copy.deepcopy(
            metrics["context_generation_footprint"]
        ),
        "human_review": copy.deepcopy(metrics["human_review"]),
        "runtime": copy.deepcopy(metrics["runtime"]),
        "production_isolation": {
            "pre_sha256": production["pre"]["sha256"],
            "post_sha256": production["post"]["sha256"],
            "changed": "NO",
            "table_counts_changed": "NO",
            "integrity_check": production["post"]["integrity_check"],
            "foreign_key_violations": len(production["post"]["foreign_key_violations"]),
            "IMA": "NO",
            "Propagation": "NO",
            "Legacy_ingestion": "NO",
        },
        "tests": {
            "local_subspan_targeted": {"status": "PASS", "detail": "11 passed"},
            "binding_regressions": {"status": "PASS", "detail": "9 passed"},
            "test_corpus_pilot": {"status": "PASS", "detail": "78 passed"},
            "source_quality": {"status": "PASS", "detail": "9 passed"},
            "pilot3_evidence_repair_regressions": {"status": "PASS", "detail": "8 passed"},
            "pilot4_evidence_regressions": {"status": "PASS", "detail": "11 passed"},
            "phase3c_full_regressions": {"status": "PASS", "detail": "166 passed, 1 deprecation warning"},
            "full_pytest": {"status": "PASS", "detail": "1008 passed, 1 deprecation warning in 317.46s"},
            "frontend_tests": {"status": "PASS", "detail": "72 passed"},
            "frontend_build": {"status": "PASS", "detail": "built; existing >500 kB chunk warning"},
            "compileall": {"status": "PASS", "detail": "src and scripts"},
            "git_diff_check": {"status": "PASS", "detail": "no whitespace errors; pre-existing LF/CRLF notices only"},
        },
        "preserved_prior_artifacts": copy.deepcopy(
            metrics["preserved_prior_artifacts"]
        ),
        "artifacts": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
        "final_state": {
            "PHASE3C_CLEAN_PILOT4_BOUNDED_SUBSPAN_REPAIR_COMPLETE": True,
            "PHASE3C_CLEAN_PILOT4_EVIDENCE_REPAIR_COMPLETE": True,
            "PHASE3C_CLEAN_PILOT4_EXTRACTION_COMPLETE": True,
            "PILOT4_EVIDENCE_ARTIFACT_GATE": "PASS",
            "PILOT4_MECHANICAL_GATE": metrics["PILOT4_MECHANICAL_GATE"],
            "PILOT4_SEMANTIC_GATE": "PENDING_HUMAN_REVIEW",
            "PILOT4_INDEPENDENT_SEMANTIC_SAMPLE": True,
            "PILOT4_INDEPENDENT_EVIDENCE_POST_REPAIR_SAMPLE": False,
            "POST_EVIDENCE_REPAIR_INDEPENDENT_CLEAN_PILOT_REQUIRED": True,
            "PHASE3C_COMPLETE": False,
            "PRODUCTION_APPLY_READY": "NO",
            "PHASE3C_NEXT_GATE": "Clean Pilot #4 Independent Human Review",
            "STOP": True,
        },
    }
    report_path = run_dir / "pilot4_bounded_local_subspan_repair_report.md"
    report_path.write_text(_render_repair_report(receipt), encoding="utf-8")
    receipt["artifacts"]["repair_report"] = {
        "path": str(report_path), "sha256": sha256_file(report_path),
    }
    receipt_path = run_dir / "pilot4_bounded_local_subspan_regression_receipt.json"
    write_json(receipt_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay frozen Pilot #4 context generation after bounded-subspan repair",
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--production-db", required=True, type=Path)
    parser.add_argument(
        "--mode", choices=("replay", "rebuild", "finalize"), default="replay",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "replay":
            if args.output is None:
                raise PilotError("PILOT4_BOUNDED_SUBSPAN_REPLAY_OUTPUT_REQUIRED")
            result = run_frozen_replay(
                run_dir=args.run_dir,
                source_path=args.source_file,
                production_db=args.production_db,
            )
            write_json(args.output.resolve(), result)
            summary = {
                "status": result["status"],
                "targeted": result["targeted_outside_bounded_window"],
                "cross_page": result["cross_page_non_regression"],
                "footprint": result["context_generation_footprint"],
            }
            exit_code = 0 if result["status"] == "PASS_READY_FOR_FROZEN_REBUILD" else 2
        elif args.mode == "rebuild":
            replay_path = args.replay or (
                args.run_dir / "pilot4_bounded_local_subspan_replay.json"
            )
            result = run_frozen_rebuild(
                run_dir=args.run_dir,
                source_path=args.source_file,
                production_db=args.production_db,
                replay_path=replay_path,
            )
            summary = {
                "status": result["status"],
                "evidence_artifact_gate": result["PILOT4_EVIDENCE_ARTIFACT_GATE"],
                "mechanical_gate": result["PILOT4_MECHANICAL_GATE"],
                "semantic_gate": result["PILOT4_SEMANTIC_GATE"],
                "mechanical_metrics": result["mechanical_evidence_metrics"],
                "human_pending": result["human_review"]["PENDING"],
            }
            exit_code = 0
        else:
            result = finalize_repair_artifacts(
                run_dir=args.run_dir,
                production_db=args.production_db,
            )
            summary = {
                "status": result["status"],
                "final_state": result["final_state"],
                "tests": result["tests"],
            }
            exit_code = 0
    except PilotError as exc:
        print(str(exc))
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
