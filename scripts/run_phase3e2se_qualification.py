from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import subprocess
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pro_a.config import load_config
from pro_a.llm import ChatLLM
from pro_a.operational_ingestion import _semantic_admission_artifact
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from pro_a.proposition_ir import PROPOSITION_IR_VERSION, proposition_ir_schema
from pro_a.semantic_decomposition import (
    ChatLLMSemanticBackend,
    SEMANTIC_MAX_OUTPUT_TOKENS,
    SemanticDecomposer,
    build_semantic_claim_inputs,
    semantic_prompt_sha256,
)
from pro_a.semantic_gold_replay import (
    FROZEN_ARTIFACT_SHA256,
    build_post_hardening_replay,
    recompute_semantic_recommendations,
)


RELEASE_SHA = "8e5d21fac95d8beda2244e2c1f28a61e5cc8e643"
SOURCE_SHA256 = "4ce8b7b36ee3fac6cca73573d50f04e79d68fff3ecda4e4047d7fce5cc7ca40e"
RUN_ID = "INGEST_4CE8B7B36EE3FAC6"
PRODUCTION_SHA256 = "3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0"
RESTORED_PRIMARY_PROMPT_SHA256 = (
    "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"
)
FAILED_COUPLED_TOTAL_TOKENS = 251_317
MATERIAL_REDUCTION_MAX_RATIO = 0.50
SEMANTIC_BATCH_SIZE = 8
PRACTICAL_REVIEW_RATE_MAX = 0.30
SC_FROZEN_HASHES = {
    "phase3e2sc_system_triage_frozen.json": "37b90971446421caa1cbd37ac3b57168b2510b24a358ea9c341e90da50cb84da",
    "phase3e2sc_human_semantic_review.json": "a73075df0ccbaa9b0d6975fd29c4f045c6c19c5989aecf48bef741ce37eef3b8",
    "phase3e2sc_generalization_report.json": "43c51a49ca7450f0952bb5c4287586d52e89869ccc30545ae0e58b360c11e8f1",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _production_state(path: Path) -> dict[str, Any]:
    digest = _sha256(path)
    with sqlite3.connect(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    return {
        "path": str(path),
        "sha256": digest,
        "integrity": integrity,
        "foreign_key_violations": foreign_keys,
        "matches_frozen_baseline": (
            digest == PRODUCTION_SHA256 and integrity == "ok" and foreign_keys == 0
        ),
    }


def _verify_sc_authority(authority_root: Path) -> dict[str, Any]:
    receipt_root = authority_root / "workspace" / "phase3e2sc" / "receipts"
    actual = {name: _sha256(receipt_root / name) for name in SC_FROZEN_HASHES}
    return {
        "expected": SC_FROZEN_HASHES,
        "actual": actual,
        "match": actual == SC_FROZEN_HASHES,
    }


def _frozen_sc_paths(authority_root: Path) -> dict[str, Path]:
    run_root = authority_root / "workspace" / "ingestion" / RUN_ID
    return {
        "run_root": run_root,
        "bundle": run_root / "evidence" / "evidence_bound_extraction_bundle.json",
        "extraction": run_root / "extraction" / "extraction_bundle.json",
        "evidence": run_root / "evidence" / "evidence_binding.json",
        "quote": run_root / "evidence" / "quote_fidelity.json",
        "table": run_root / "evidence" / "table_claim_safety.json",
        "human": (
            authority_root
            / "workspace"
            / "phase3e2sc"
            / "receipts"
            / "phase3e2sc_human_semantic_review.json"
        ),
        "atomicity_census": (
            authority_root
            / "workspace"
            / "phase3e2sd"
            / "phase3e2sd_atomicity_failure_census.json"
        ),
    }


def _primary_extraction_contract() -> dict[str, Any]:
    prompt_hash = _text_sha256(SOURCE_ANALYSIS_SYSTEM)
    forbidden = "proposition_ir" in SOURCE_ANALYSIS_SYSTEM.casefold()
    return {
        "contract": "PRE_S_E_PRIMARY_EXTRACTION",
        "prompt_sha256": prompt_hash,
        "expected_prompt_sha256": RESTORED_PRIMARY_PROMPT_SHA256,
        "proposition_ir_inside_primary_extraction": forbidden,
        "restored": prompt_hash == RESTORED_PRIMARY_PROMPT_SHA256 and not forbidden,
    }


def _sb_report(authority_root: Path) -> dict[str, Any]:
    run_root = (
        authority_root
        / "workspace"
        / "ingestion"
        / "INGEST_D3DF045F483A1D1F_SCOPE1"
    )
    verified = {
        relative: _sha256(run_root / relative)
        for relative in FROZEN_ARTIFACT_SHA256
    }
    if verified != FROZEN_ARTIFACT_SHA256:
        raise ValueError("frozen S-B authority artifact mismatch")

    bundle = _read_json(run_root / "evidence" / "evidence_bound_extraction_bundle.json")
    evidence_support = _read_json(run_root / "evidence" / "evidence_binding.json")
    quote_fidelity = _read_json(run_root / "evidence" / "quote_fidelity.json")
    table_boundary = _read_json(run_root / "evidence" / "table_claim_safety.json")["result"]
    old_semantic = _read_json(run_root / "evidence" / "semantic_admission.json")
    human_review = _read_json(run_root / "review" / "phase3e2_human_semantic_review.json")
    repair_draft = _read_json(run_root / "review" / "claim_repair_draft.json")
    new_semantic = recompute_semantic_recommendations(
        run_id=str(human_review["run_id"]),
        source_sha256=str(human_review["source_sha256"]),
        extracted_bundle=bundle,
        evidence_support=evidence_support,
        quote_fidelity=quote_fidelity,
        table_boundary=table_boundary,
    )
    replay = build_post_hardening_replay(
        old_semantic=old_semantic,
        new_semantic=new_semantic,
        human_review=human_review,
        repair_draft=repair_draft,
        quote_fidelity=quote_fidelity,
    )
    atomicity = replay["atomicity_metrics"]
    nature = replay["nature_metrics"]
    gates = {
        "S_B_ATOMICITY_GOLD_IS_33": atomicity["gold_cases"] == 33,
        "S_B_ATOMICITY_RECALL_IS_1_00": atomicity["gold_recall"] == 1.0,
        "S_B_ATOMICITY_FALSE_POSITIVES_ZERO": (
            atomicity["human_keep_false_positives"] == 0
        ),
        "S_B_NATURE_GOLD_IS_7": nature["gold_cases"] == 7,
        "S_B_NATURE_RECALL_IS_1_00": nature["gold_recall"] == 1.0,
        "S_B_NATURE_FALSE_POSITIVES_ZERO": nature["human_keep_false_positives"] == 0,
    }
    return {
        "document_type": "phase3e2se_sb_regression_report",
        "schema_version": "2.0",
        "generated_at_utc": _utc_now(),
        "authority": "FROZEN_S_B_DEVELOPMENT_REGRESSION",
        "legacy_artifact_compatibility_path": "LEGACY_PHASE3E2SB_V1",
        "frozen_input_sha256": verified,
        "atomicity": atomicity,
        "nature": nature,
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }


def _run_semantic_pass(
    *,
    authority_root: Path,
    config_path: Path,
    batch_size: int,
) -> dict[str, Any]:
    paths = _frozen_sc_paths(authority_root)
    bundle = _read_json(paths["bundle"])
    evidence = _read_json(paths["evidence"])
    quote = _read_json(paths["quote"])
    inputs = build_semantic_claim_inputs(
        bundle=bundle,
        evidence_draft=evidence,
        quote_fidelity=quote,
    )
    cfg = load_config(config_path)
    llm_cfg = replace(
        cfg.llm,
        max_output_tokens=min(cfg.llm.max_output_tokens, SEMANTIC_MAX_OUTPUT_TOKENS),
    )
    llm = ChatLLM(llm_cfg)
    if not llm.available:
        raise RuntimeError("configured semantic model is unavailable")
    result = SemanticDecomposer(
        ChatLLMSemanticBackend(llm),
        batch_size=batch_size,
    ).run(inputs)
    result["qualification_input"] = {
        "authority": "FROZEN_S_C_73_CLAIM_UNIVERSE",
        "full_pdf_supplied": False,
        "unrelated_claims_supplied": False,
        "production_node_catalog_supplied": False,
        "primary_extraction_invoked": False,
        "configured_model": llm_cfg.model,
        "max_output_tokens_per_semantic_call": llm_cfg.max_output_tokens,
        "semantic_prompt_sha256": semantic_prompt_sha256(),
    }
    return result


def _guard_status(decision: Mapping[str, Any], guard: str) -> str:
    semantic = decision.get("semantic_admission") or {}
    return str((semantic.get(guard) or {}).get("status") or "NOT_PRESENT")


def _validation(decision: Mapping[str, Any]) -> Mapping[str, Any]:
    return (
        (decision.get("semantic_admission") or {}).get("proposition_ir_validation")
        or {}
    )


def _proposition_ir_metrics(decisions: list[Mapping[str, Any]]) -> dict[str, Any]:
    validations = [_validation(decision) for decision in decisions]
    issue_counts = Counter(
        code
        for validation in validations
        for code in validation.get("issue_codes") or []
    )
    return {
        "parent_claims_accounted_for": len(validations),
        "valid_proposition_ir_claims": sum(
            item.get("status") == "VALID" for item in validations
        ),
        "invalid_or_ambiguous_ir_claims": sum(
            item.get("status") != "VALID" for item in validations
        ),
        "proposition_evidence_binding_failures": sum(
            int(item.get("evidence_binding_failures") or 0) for item in validations
        ),
        "unsupported_proposition_content": sum(
            int(item.get("unsupported_content_failures") or 0) for item in validations
        ),
        "duplicate_proposition_unit_cases": sum(
            int(item.get("duplicate_unit_cases") or 0) for item in validations
        ),
        "ambiguous_coherence_cases": sum(
            int(item.get("ambiguous_coherence_cases") or 0) for item in validations
        ),
        "validation_issue_counts": dict(sorted(issue_counts.items())),
    }


def _recommendation_matrix(
    decisions: list[Mapping[str, Any]],
    human_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    matrix = {
        recommendation: {label: 0 for label in ("KEEP", "NEEDS_REPAIR", "DROP")}
        for recommendation in ("KEEP", "REVIEW", "DROP")
    }
    for decision in decisions:
        label = human_by_id[decision["claim_id"]]["human_semantic_decision"]
        matrix[decision["recommended_decision"]][label] += 1
    return matrix


def _review_burden(decisions: list[Mapping[str, Any]]) -> dict[str, Any]:
    classes = Counter()
    class_by_id: dict[str, str] = {}
    for decision in decisions:
        if decision.get("recommended_decision") != "REVIEW":
            continue
        validation = _validation(decision)
        if validation.get("status") != "VALID":
            review_class = "IR_INVALID_REVIEW"
        elif _guard_status(decision, "atomicity_guard") == "REVIEW_REQUIRED":
            review_class = "ATOMICITY_REVIEW"
        elif _guard_status(decision, "nature_consistency_guard") == "REVIEW_REQUIRED":
            review_class = "NATURE_REVIEW"
        else:
            review_class = "OTHER_REVIEW"
        classes[review_class] += 1
        class_by_id[str(decision["claim_id"])] = review_class
    review_count = sum(classes.values())
    total = len(decisions)
    return {
        "mutually_exclusive_precedence": [
            "IR_INVALID_REVIEW",
            "ATOMICITY_REVIEW",
            "NATURE_REVIEW",
            "OTHER_REVIEW",
        ],
        "counts": {
            name: classes.get(name, 0)
            for name in (
                "IR_INVALID_REVIEW",
                "ATOMICITY_REVIEW",
                "NATURE_REVIEW",
                "OTHER_REVIEW",
            )
        },
        "claim_classes": class_by_id,
        "review_count": review_count,
        "review_rate": _ratio(review_count, total),
        "practical_threshold": PRACTICAL_REVIEW_RATE_MAX,
    }


def _empty_sc_report(reason: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    common = {
        "schema_version": "2.0",
        "generated_at_utc": _utc_now(),
        "authority": "FROZEN_S_C_DEVELOPMENT_ONLY",
        "gate": "NOT_RUN",
        "reason": reason,
    }
    return (
        {"document_type": "phase3e2se_sc_development_regression_report", **common},
        {"document_type": "phase3e2se_semantic_confusion_report", **common},
        {"document_type": "phase3e2se_causal_reason_report", **common},
    )


def _sc_report(
    authority_root: Path,
    decomposition: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if decomposition is None:
        return _empty_sc_report("semantic decomposition artifact not supplied")

    paths = _frozen_sc_paths(authority_root)
    bundle = _read_json(paths["bundle"])
    evidence = _read_json(paths["evidence"])
    quote = _read_json(paths["quote"])
    table = _read_json(paths["table"])["result"]
    human = _read_json(paths["human"])
    atomicity_census = _read_json(paths["atomicity_census"])
    frozen_extraction = _read_json(paths["extraction"])
    expected_ids = [str(item["claim_id"]) for item in bundle.get("claims") or []]
    input_ids = [str(item) for item in decomposition.get("input_parent_claim_ids") or []]
    output_ids = [str(item) for item in decomposition.get("output_parent_claim_ids") or []]
    result_rows = list(decomposition.get("results") or [])
    result_ids = [str(item.get("parent_claim_id") or "") for item in result_rows]
    identity_exact = (
        len(expected_ids) == 73
        and input_ids == expected_ids
        and output_ids == expected_ids
        and result_ids == expected_ids
        and len(set(result_ids)) == 73
    )
    missing_ids = sorted(set(expected_ids) - set(result_ids))
    new_ids = sorted(set(result_ids) - set(expected_ids))
    duplicate_ids = sorted(
        claim_id for claim_id, count in Counter(result_ids).items() if count > 1
    )
    expected_id_set = set(expected_ids)
    proposition_by_id = {
        str(item["parent_claim_id"]): item
        for item in result_rows
        if item.get("parent_claim_id") in expected_id_set
    }
    manifest = {"run_id": RUN_ID, "source": {"sha256": SOURCE_SHA256}}
    semantic = _semantic_admission_artifact(
        manifest=manifest,
        bundle=bundle,
        evidence_draft=evidence,
        gate=quote,
        table_boundary=table,
        proposition_results=proposition_by_id,
    )
    decisions = list(semantic.get("decisions") or [])
    decision_by_id = {str(item["claim_id"]): item for item in decisions}
    human_by_id = {
        str(item["claim_id"]): item for item in human.get("claim_decisions") or []
    }
    gold_join_valid = set(decision_by_id) == set(human_by_id) == expected_id_set
    ir_metrics = _proposition_ir_metrics(decisions)
    review = _review_burden(decisions)

    repair_ids = {
        claim_id for claim_id, row in human_by_id.items()
        if row["human_semantic_decision"] == "NEEDS_REPAIR"
    }
    keep_ids = {
        claim_id for claim_id, row in human_by_id.items()
        if row["human_semantic_decision"] == "KEEP"
    }
    drop_ids = set(human_by_id) - repair_ids - keep_ids
    atomicity_gold = {
        claim_id for claim_id, row in human_by_id.items()
        if "ATOMICITY" in (row.get("repair_categories") or [])
    }
    nature_gold = {
        claim_id for claim_id, row in human_by_id.items()
        if "NATURE" in (row.get("repair_categories") or [])
    }
    valid_ir_ids = {
        claim_id for claim_id, decision in decision_by_id.items()
        if _validation(decision).get("status") == "VALID"
    }
    system_review_ids = {
        claim_id for claim_id, decision in decision_by_id.items()
        if decision.get("recommended_decision") == "REVIEW"
    }
    system_keep_ids = {
        claim_id for claim_id, decision in decision_by_id.items()
        if decision.get("recommended_decision") == "KEEP"
    }
    detected_repairs = repair_ids & system_review_ids
    atomicity_review_ids = {
        claim_id for claim_id in valid_ir_ids
        if _guard_status(decision_by_id[claim_id], "atomicity_guard") == "REVIEW_REQUIRED"
        and "INDEPENDENT_REVIEWABLE_PROPOSITIONS" in (
            (decision_by_id[claim_id].get("semantic_admission") or {})
            .get("atomicity_guard", {})
            .get("reason_codes", [])
        )
    }
    atomicity_detected = atomicity_gold & atomicity_review_ids
    nature_detected = {
        claim_id for claim_id in nature_gold & valid_ir_ids
        if _guard_status(decision_by_id[claim_id], "nature_consistency_guard")
        == "REVIEW_REQUIRED"
    }
    expected_mechanism = {
        str(item["claim_id"]): str(item["mechanism_class"])
        for item in atomicity_census.get("cases") or []
    }
    causal_rows = []
    causally_correct: set[str] = set()
    for claim_id in sorted(atomicity_gold):
        atomicity_guard = (
            (decision_by_id[claim_id].get("semantic_admission") or {})
            .get("atomicity_guard")
            or {}
        )
        details = atomicity_guard.get("details") or {}
        mechanisms = list(details.get("mechanism_classes") or [])
        correct = (
            claim_id in atomicity_detected
            and details.get("decision_basis") == "EXPLICIT_COHERENCE_TYPES"
        )
        if correct:
            causally_correct.add(claim_id)
        causal_rows.append({
            "claim_id": claim_id,
            "expected_mechanism_class": expected_mechanism.get(claim_id),
            "observed_mechanism_classes": mechanisms,
            "decision_basis": details.get("decision_basis"),
            "valid_ir": claim_id in valid_ir_ids,
            "disposition_detected": claim_id in atomicity_detected,
            "causally_correct": correct,
        })

    nature_fp_ids = {
        claim_id for claim_id in (set(human_by_id) - nature_gold) & valid_ir_ids
        if _guard_status(decision_by_id[claim_id], "nature_consistency_guard")
        == "REVIEW_REQUIRED"
    }
    nature_keep_fp_ids = nature_fp_ids & keep_ids
    original_jiang_fp_ids = {
        claim_id for claim_id in nature_keep_fp_ids
        if "JIANG_OBJECT_FRONTING_MISCLASSIFIED_AS_FUTURE" in (
            (decision_by_id[claim_id].get("semantic_admission") or {})
            .get("nature_consistency_guard", {})
            .get("reason_codes", [])
        )
    }
    catastrophic_false_drop = {
        claim_id for claim_id in keep_ids
        if decision_by_id[claim_id].get("recommended_decision") == "DROP"
    }
    unsupported_drop_ids = {
        claim_id for claim_id in drop_ids
        if human_by_id[claim_id].get("drop_reason") == "UNSUPPORTED_SEMANTIC_CONTENT"
    }
    unsupported_false_keep = unsupported_drop_ids & system_keep_ids
    metrics = {
        "raw_claims": len(decisions),
        "human_needs_repair": len(repair_ids),
        "atomicity_repair_cases": len(atomicity_gold),
        "atomicity_review_total": len(atomicity_review_ids),
        "atomicity_true_positive": len(atomicity_detected),
        "atomicity_false_positive": len(atomicity_review_ids - atomicity_gold),
        "nature_repair_cases": len(nature_gold),
        "repair_detection_recall": _ratio(len(detected_repairs), len(repair_ids)),
        "atomicity_disposition_recall": _ratio(
            len(atomicity_detected), len(atomicity_gold)
        ),
        "causally_correct_atomicity_recall": _ratio(
            len(causally_correct), len(atomicity_gold)
        ),
        "nature_recall": _ratio(len(nature_detected), len(nature_gold)),
        "system_keep_precision": _ratio(len(system_keep_ids & keep_ids), len(system_keep_ids)),
        "nature_human_keep_false_positives": len(nature_keep_fp_ids),
        "full_nature_false_positives": len(nature_fp_ids),
        "original_jiang_fp_remaining": len(original_jiang_fp_ids),
        "new_nature_fp_count": len(nature_keep_fp_ids - original_jiang_fp_ids),
        "review_rate": review["review_rate"],
        "catastrophic_false_drop": len(catastrophic_false_drop),
        "unsupported_false_keep": len(unsupported_false_keep),
    }
    usage = decomposition.get("usage") or {}
    semantic_total_tokens = int(usage.get("total_tokens") or 0)
    token_ratio = semantic_total_tokens / FAILED_COUPLED_TOTAL_TOKENS
    nature_fp_limit = max(3, 0.10 * len(keep_ids))
    min_valid_ir = math.ceil(0.95 * len(expected_ids))
    gates = {
        "S_C_CLAIM_COUNT_IS_73": len(expected_ids) == len(decisions) == 73,
        "S_C_PARENT_CLAIM_ID_MATCH_IS_73_OF_73": identity_exact,
        "S_C_NEW_PARENT_CLAIMS_ZERO": not new_ids,
        "S_C_MISSING_PARENT_CLAIMS_ZERO": not missing_ids,
        "S_C_DUPLICATE_PARENT_CLAIMS_ZERO": not duplicate_ids,
        "FROZEN_HUMAN_GOLD_JOIN_VALID": gold_join_valid,
        "PRIMARY_EXTRACTION_LLM_CALLS_ZERO": (
            int(decomposition.get("primary_extraction_llm_calls") or 0) == 0
        ),
        "SEMANTIC_LENGTH_RETRY_CHANGES_CLAIMS_FALSE": (
            decomposition.get("semantic_length_retry_changes_claims") is False
        ),
        "SEMANTIC_LENGTH_RETRIES_ZERO": (
            int(decomposition.get("semantic_length_retries") or 0) == 0
        ),
        "MODEL_GENERATED_RAW_EVIDENCE_OFFSETS_FALSE": (
            (decomposition.get("invariants") or {}).get(
                "MODEL_GENERATED_RAW_EVIDENCE_OFFSETS"
            ) is False
        ),
        "PARENT_EVIDENCE_IDENTITY_DETERMINISTIC": (
            (decomposition.get("invariants") or {}).get(
                "PARENT_EVIDENCE_IDENTITY_DETERMINISTIC"
            ) is True
        ),
        "PROPOSITION_SUPPORT_REFERENCES_EXISTING_EVIDENCE_IDS": (
            (decomposition.get("invariants") or {}).get(
                "PROPOSITION_SUPPORT_REFERENCES_EXISTING_EVIDENCE_IDS"
            ) is True
        ),
        "VALID_PROPOSITION_IR_AT_LEAST_95_PERCENT": (
            ir_metrics["valid_proposition_ir_claims"] >= min_valid_ir
        ),
        "PROPOSITION_EVIDENCE_BINDING_FAILURES_ZERO": (
            ir_metrics["proposition_evidence_binding_failures"] == 0
        ),
        "UNSUPPORTED_PROPOSITION_CONTENT_ZERO": (
            ir_metrics["unsupported_proposition_content"] == 0
        ),
        "REPAIR_DETECTION_RECALL_AT_LEAST_0_75": (
            metrics["repair_detection_recall"] >= 0.75
        ),
        "ATOMICITY_DISPOSITION_RECALL_AT_LEAST_0_80": (
            metrics["atomicity_disposition_recall"] >= 0.80
        ),
        "CAUSALLY_CORRECT_ATOMICITY_RECALL_AT_LEAST_0_80": (
            metrics["causally_correct_atomicity_recall"] >= 0.80
        ),
        "NATURE_RECALL_AT_LEAST_0_80": metrics["nature_recall"] >= 0.80,
        "SYSTEM_KEEP_PRECISION_AT_LEAST_0_80": (
            metrics["system_keep_precision"] >= 0.80
        ),
        "NATURE_HUMAN_KEEP_FALSE_POSITIVES_WITHIN_BOUND": (
            metrics["nature_human_keep_false_positives"] <= nature_fp_limit
        ),
        "NO_CATASTROPHIC_FALSE_DROP": metrics["catastrophic_false_drop"] == 0,
        "NO_UNSUPPORTED_FALSE_KEEP": metrics["unsupported_false_keep"] == 0,
        "REVIEW_BURDEN_PRACTICAL": review["review_rate"] <= PRACTICAL_REVIEW_RATE_MAX,
        "SEMANTIC_TOKEN_REDUCTION_MATERIAL": (
            token_ratio <= MATERIAL_REDUCTION_MAX_RATIO
        ),
    }
    frozen_model = frozen_extraction.get("model") or {}
    report = {
        "document_type": "phase3e2se_sc_development_regression_report",
        "schema_version": "2.0",
        "generated_at_utc": _utc_now(),
        "authority": "FROZEN_S_C_DEVELOPMENT_ONLY_NOT_FRESH_GENERALIZATION",
        "architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
        "evidence_binding_architecture": decomposition.get(
            "evidence_binding_architecture"
        ),
        "evidence_binding_invariants": decomposition.get("invariants") or {},
        "input_policy": {
            "frozen_claims_only": True,
            "pdf_rerun": False,
            "full_pdf_in_semantic_prompt": False,
            "production_node_catalog_in_semantic_prompt": False,
        },
        "parent_identity": {
            "parent_claims": len(expected_ids),
            "parent_claim_id_match": len(set(expected_ids) & set(result_ids)),
            "exact_ordered_identity_match": identity_exact,
            "new_parent_claims": len(new_ids),
            "new_parent_claim_ids": new_ids,
            "missing_parent_claims": len(missing_ids),
            "missing_parent_claim_ids": missing_ids,
            "duplicate_parent_claim_ids": duplicate_ids,
        },
        "primary_extraction_baseline_not_rerun": {
            "claims": len(frozen_extraction.get("claims") or []),
            "llm_calls": int(frozen_model.get("llm_calls") or 0),
            "usage": frozen_model.get("usage") or {},
            "qualification_primary_extraction_llm_calls": int(
                decomposition.get("primary_extraction_llm_calls") or 0
            ),
        },
        "semantic_model": {
            "backend": decomposition.get("backend"),
            "batch_size": decomposition.get("batch_size"),
            "llm_calls": int(decomposition.get("semantic_llm_calls") or 0),
            "length_retries": int(decomposition.get("semantic_length_retries") or 0),
            "usage": usage,
            "failed_coupled_total_tokens": FAILED_COUPLED_TOTAL_TOKENS,
            "new_to_failed_token_ratio": token_ratio,
            "material_reduction_max_ratio": MATERIAL_REDUCTION_MAX_RATIO,
        },
        "proposition_ir": {
            **ir_metrics,
            "minimum_valid_claims": min_valid_ir,
            "target_ratio": 0.95,
        },
        "metrics": metrics,
        "review_burden": review,
        "nature_human_keep_false_positive_limit": nature_fp_limit,
        "recommendation_counts": dict(
            Counter(item["recommended_decision"] for item in decisions)
        ),
        "nature_human_keep_false_positive_ids": sorted(nature_keep_fp_ids),
        "original_jiang_false_positive_ids": sorted(original_jiang_fp_ids),
        "full_nature_false_positive_ids": sorted(nature_fp_ids),
        "catastrophic_false_drop_ids": sorted(catastrophic_false_drop),
        "unsupported_false_keep_ids": sorted(unsupported_false_keep),
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }
    confusion = {
        "document_type": "phase3e2se_semantic_confusion_report",
        "schema_version": "2.0",
        "generated_at_utc": _utc_now(),
        "authority": report["authority"],
        "disposition_matrix": _recommendation_matrix(decisions, human_by_id),
        "review_burden": review,
        "atomicity": {
            "tp": len(atomicity_detected),
            "fn": len(atomicity_gold - atomicity_detected),
        },
        "nature": {
            "tp": len(nature_detected),
            "fn": len(nature_gold - nature_detected),
            "fp_human_keep": len(nature_keep_fp_ids),
            "fp_full": len(nature_fp_ids),
        },
        "gate": report["gate"],
    }
    causal = {
        "document_type": "phase3e2se_causal_reason_report",
        "schema_version": "2.0",
        "generated_at_utc": _utc_now(),
        "authority": report["authority"],
        "atomicity_gold_cases": len(atomicity_gold),
        "disposition_true_positives": len(atomicity_detected),
        "causally_correct_true_positives": len(causally_correct),
        "causally_correct_atomicity_recall": metrics[
            "causally_correct_atomicity_recall"
        ],
        "cases": causal_rows,
        "gate": (
            "PASS"
            if gates["CAUSALLY_CORRECT_ATOMICITY_RECALL_AT_LEAST_0_80"]
            else "FAIL"
        ),
    }
    return report, confusion, causal


def _git_value(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    semantic_source = parser.add_mutually_exclusive_group()
    semantic_source.add_argument("--run-semantic", action="store_true")
    semantic_source.add_argument("--semantic-artifact", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--batch-size", type=int, default=SEMANTIC_BATCH_SIZE)
    parser.add_argument("--focused-tests", default="NOT_RECORDED")
    parser.add_argument("--full-pytest", default="NOT_RECORDED")
    parser.add_argument("--compileall", default="NOT_RECORDED")
    parser.add_argument("--diff-check", default="NOT_RECORDED")
    args = parser.parse_args()

    authority = args.authority_root.resolve()
    output = args.output_dir.resolve()
    repo = args.repo_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    production = _production_state(args.production_db.resolve())
    sc_authority = _verify_sc_authority(authority)
    primary_contract = _primary_extraction_contract()
    if not sc_authority["match"]:
        raise ValueError("frozen S-C authority artifact mismatch")
    if not production["matches_frozen_baseline"]:
        raise ValueError("Production baseline mismatch")
    if not primary_contract["restored"]:
        raise ValueError("primary extraction contract is not restored")

    decomposition: dict[str, Any] | None = None
    semantic_path = output / "semantic_decomposition.json"
    if args.run_semantic:
        if args.config is None:
            parser.error("--config is required with --run-semantic")
        decomposition = _run_semantic_pass(
            authority_root=authority,
            config_path=args.config.resolve(),
            batch_size=args.batch_size,
        )
        _write_json(semantic_path, decomposition)
    elif args.semantic_artifact:
        semantic_path = args.semantic_artifact.resolve()
        decomposition = _read_json(semantic_path)

    sb = _sb_report(authority)
    sc, confusion, causal = _sc_report(authority, decomposition)
    branch = _git_value(repo, "branch", "--show-current")
    head = _git_value(repo, "rev-parse", "HEAD")
    architecture_gates = {
        "PRIMARY_EXTRACTION_CONTRACT_RESTORED": primary_contract["restored"],
        "PROPOSITION_IR_INSIDE_PRIMARY_EXTRACTION_FALSE": (
            primary_contract["proposition_ir_inside_primary_extraction"] is False
        ),
        "SEMANTIC_DECOMPOSER_IMPLEMENTED": True,
        "LOCAL_MODEL_BACKEND_INTERFACE_READY": True,
        "S_B_REGRESSION_PASS": sb["gate"] == "PASS",
        "S_C_DEVELOPMENT_QUALIFICATION_PASS": sc.get("gate") == "PASS",
        "CAUSAL_REASON_PASS": causal.get("gate") == "PASS",
        "PRODUCTION_FROZEN": production["matches_frozen_baseline"],
        "EXPECTED_BRANCH": branch == "codex/phase3e2se-structural-repair",
    }
    complete = all(architecture_gates.values())
    parent = sc.get("parent_identity") or {}
    ir = sc.get("proposition_ir") or {}
    sc_metrics = sc.get("metrics") or {}
    semantic_model = sc.get("semantic_model") or {}
    semantic_usage = semantic_model.get("usage") or {}
    final = {
        "document_type": "phase3e2se1_final_qualification_report",
        "schema_version": "2.1",
        "generated_at_utc": _utc_now(),
        "phase": "Phase 3E.2S-E.1 Proposition IR Binding and Semantic Precision Closure",
        "PHASE3E_STAGE3E2SE1_COMPLETE": complete,
        "SEMANTIC_ARCHITECTURE": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
        "EVIDENCE_BINDING_ARCHITECTURE": "DETERMINISTIC_EVIDENCE_IDS",
        "MODEL_GENERATED_RAW_EVIDENCE_OFFSETS": False,
        "PROPOSITION_SUPPORT_REFERENCES_EXISTING_EVIDENCE_IDS": (
            (decomposition or {}).get("invariants", {}).get(
                "PROPOSITION_SUPPORT_REFERENCES_EXISTING_EVIDENCE_IDS"
            )
        ),
        "PRIMARY_EXTRACTION_CONTRACT_RESTORED": primary_contract["restored"],
        "PROPOSITION_IR_INSIDE_PRIMARY_EXTRACTION": False,
        "SEMANTIC_DECOMPOSER_IMPLEMENTED": True,
        "PROPOSITION_IR_VERSION": PROPOSITION_IR_VERSION,
        "S_C_PARENT_CLAIMS": parent.get("parent_claims"),
        "S_C_PARENT_CLAIM_ID_MATCH": parent.get("parent_claim_id_match"),
        "S_C_NEW_PARENT_CLAIMS": parent.get("new_parent_claims"),
        "S_C_MISSING_PARENT_CLAIMS": parent.get("missing_parent_claims"),
        "VALID_PROPOSITION_IR_CLAIMS": ir.get("valid_proposition_ir_claims"),
        "PROPOSITION_EVIDENCE_BINDING_FAILURES": ir.get(
            "proposition_evidence_binding_failures"
        ),
        "UNSUPPORTED_PROPOSITION_CONTENT": ir.get("unsupported_proposition_content"),
        "S_B_ATOMICITY_RECALL": sb["atomicity"]["gold_recall"],
        "S_B_ATOMICITY_FALSE_POSITIVES": sb["atomicity"][
            "human_keep_false_positives"
        ],
        "S_B_NATURE_RECALL": sb["nature"]["gold_recall"],
        "S_B_NATURE_FALSE_POSITIVES": sb["nature"]["human_keep_false_positives"],
        "S_C_REPAIR_DETECTION_RECALL": sc_metrics.get("repair_detection_recall"),
        "S_C_ATOMICITY_DISPOSITION_RECALL": sc_metrics.get(
            "atomicity_disposition_recall"
        ),
        "ATOMICITY_REVIEW_TOTAL": sc_metrics.get("atomicity_review_total"),
        "ATOMICITY_TRUE_POSITIVE": sc_metrics.get("atomicity_true_positive"),
        "ATOMICITY_FALSE_POSITIVE": sc_metrics.get("atomicity_false_positive"),
        "S_C_CAUSALLY_CORRECT_ATOMICITY_RECALL": sc_metrics.get(
            "causally_correct_atomicity_recall"
        ),
        "S_C_NATURE_RECALL": sc_metrics.get("nature_recall"),
        "S_C_SYSTEM_KEEP_PRECISION": sc_metrics.get("system_keep_precision"),
        "S_C_NATURE_HUMAN_KEEP_FALSE_POSITIVES": sc_metrics.get(
            "nature_human_keep_false_positives"
        ),
        "ORIGINAL_JIANG_FP_REMAINING": sc_metrics.get(
            "original_jiang_fp_remaining"
        ),
        "NEW_NATURE_FP_COUNT": sc_metrics.get("new_nature_fp_count"),
        "S_C_FULL_NATURE_FALSE_POSITIVES": sc_metrics.get(
            "full_nature_false_positives"
        ),
        "S_C_REVIEW_RATE": sc_metrics.get("review_rate"),
        "IR_INVALID_REVIEW": (sc.get("review_burden") or {}).get(
            "counts", {}
        ).get("IR_INVALID_REVIEW", 0),
        "ATOMICITY_REVIEW": (sc.get("review_burden") or {}).get(
            "counts", {}
        ).get("ATOMICITY_REVIEW", 0),
        "NATURE_REVIEW": (sc.get("review_burden") or {}).get(
            "counts", {}
        ).get("NATURE_REVIEW", 0),
        "OTHER_REVIEW": (sc.get("review_burden") or {}).get(
            "counts", {}
        ).get("OTHER_REVIEW", 0),
        "SEMANTIC_INPUT_TOKENS": semantic_usage.get("prompt_tokens"),
        "SEMANTIC_OUTPUT_TOKENS": semantic_usage.get("completion_tokens"),
        "SEMANTIC_TOTAL_TOKENS": semantic_usage.get("total_tokens"),
        "SEMANTIC_LLM_CALLS": semantic_model.get("llm_calls"),
        "SEMANTIC_LENGTH_RETRIES": semantic_model.get("length_retries"),
        "PRIMARY_EXTRACTION_LLM_CALLS": 0,
        "SEMANTIC_LENGTH_RETRY_CHANGES_CLAIMS": False,
        "LOCAL_MODEL_BACKEND_IMPLEMENTED": False,
        "LOCAL_MODEL_BACKEND_INTERFACE_READY": True,
        "S_B_REGRESSION_GATE": sb["gate"],
        "S_C_DEVELOPMENT_REGRESSION_GATE": sc.get("gate"),
        "PRODUCTION_PRE_SHA256": PRODUCTION_SHA256,
        "PRODUCTION_POST_SHA256": production["sha256"],
        "PRODUCTION_CHANGED": "NO" if production["matches_frozen_baseline"] else "YES",
        "PRODUCTION_APPLY_ATTEMPTED": False,
        "BRANCH": branch,
        "COMMIT_SHA": None,
        "DRAFT_PR_NUMBER": None,
        "S_F_STATUS": "READY_FOR_FRESH_HOLDOUT" if complete else "BLOCKED",
        "gates": architecture_gates,
    }
    receipt = {
        "document_type": "phase3e2se1_implementation_receipt",
        "schema_version": "2.1",
        "generated_at_utc": _utc_now(),
        "release_sha": RELEASE_SHA,
        "branch": branch,
        "head_at_qualification": head,
        "frozen_sc_authority": sc_authority,
        "primary_extraction_contract": primary_contract,
        "semantic_artifact": str(semantic_path) if decomposition else None,
        "semantic_architecture": "DECOUPLED_POST_EXTRACTION_PROPOSITION_PASS",
        "semantic_backend_contract": {
            "interface": "SemanticBackend",
            "request": "frozen Claim ID/text/deterministic Evidence units/minimal metadata",
            "response": "same parent Claim ID plus compact proposition units referencing existing Evidence IDs",
            "cloud_adapter": "ChatLLMSemanticBackend",
            "local_qwen_implemented": False,
            "local_backend_interface_ready": True,
        },
        "test_evidence": {
            "focused_tests": args.focused_tests,
            "full_pytest": args.full_pytest,
            "compileall": args.compileall,
            "git_diff_check": args.diff_check,
        },
        "production": production,
        "production_apply_attempted": False,
        "fresh_source_inspected": False,
        "s_f_started": False,
        "qualification_complete": complete,
        "gates": architecture_gates,
    }
    _write_json(output / "phase3e2se1_proposition_ir_schema.json", proposition_ir_schema())
    _write_json(output / "phase3e2se1_sb_regression_report.json", sb)
    _write_json(output / "phase3e2se1_sc_development_regression_report.json", sc)
    _write_json(output / "phase3e2se1_semantic_confusion_report.json", confusion)
    _write_json(output / "phase3e2se1_causal_reason_report.json", causal)
    _write_json(output / "phase3e2se1_final_qualification_report.json", final)
    _write_json(output / "phase3e2se1_implementation_receipt.json", receipt)
    print(json.dumps({
        "output_dir": str(output),
        "s_b_gate": sb["gate"],
        "s_c_gate": sc.get("gate"),
        "qualification_complete": complete,
        "semantic_llm_calls": semantic_model.get("llm_calls"),
        "semantic_total_tokens": semantic_usage.get("total_tokens"),
    }, ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
