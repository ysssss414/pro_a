from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.operational_ingestion import _semantic_admission_artifact
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from pro_a.proposition_ir import COHERENCE_TYPES, proposition_ir_schema
from pro_a.semantic_decomposition import semantic_prompt_sha256
from run_phase3e2se_qualification import _sb_report, _sc_report


BASE_IMPLEMENTATION_SHA = "6b06da0fd1204430bbc27b3d80b50009e8e6e787"
PRODUCTION_SHA256 = "3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0"
SF_SOURCE_SHA256 = "ab12c54c7c0ed3b3ca195afe1755e23287d8382e05374c2f0555dcd3e996f247"
SC_DECOMPOSITION_SHA256 = "aeec40c3c8a92dc5569bfc407fe840308cc02cd5221da209c2052d889e8f0051"
PRIMARY_PROMPT_SHA256 = "4bc28ae13b1b23f1645bec2b133bc264b50aa0b3f29fc61df67b45465129dfa5"
SEMANTIC_PROMPT_SHA256 = "e3e26589f1f6b3a223b64f821ab4f2749e32152395b953bf534df71e025bee54"
EXPECTED_BRANCH = "codex/phase3e2sh-bounded-review-precision"
EXACT_FIDELITY = {"EXACT_SOURCE_MATCH", "LAYOUT_NORMALIZED_EXACT_MATCH"}

PROTECTED_ATOMICITY_IDS = {
    "CLM_44D1E097202C4575",
    "CLM_57BF5345C4897D40",
    "CLM_7C10EC2D9B49B30C",
    "CLM_AFB19D811D321922",
}
PORTFOLIO_IDS = {"CLM_66F37A21E4BF5B73", "CLM_6A4D42B42BE4F58F"}
KNOWN_NATURE_FALSE_NEGATIVE = "CLM_4B5627F66A5E8AED"


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


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _guard(decision: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    return (decision.get("semantic_admission") or {}).get(key) or {}


def _validation(decision: Mapping[str, Any]) -> Mapping[str, Any]:
    return (decision.get("semantic_admission") or {}).get(
        "proposition_ir_validation"
    ) or {}


def _production_state(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    uri = f"file:{resolved.as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    sidecars = {
        suffix: Path(f"{resolved}{suffix}").exists()
        for suffix in ("-wal", "-shm", "-journal")
    }
    digest = _sha256(resolved)
    return {
        "path": str(resolved),
        "sha256": digest,
        "integrity": integrity,
        "foreign_key_violations": foreign_keys,
        "sidecars_present": sidecars,
        "matches_frozen_baseline": (
            digest == PRODUCTION_SHA256
            and integrity == "ok"
            and foreign_keys == 0
            and not any(sidecars.values())
        ),
    }


def _semantic_replay(run_root: Path, decomposition: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _read_json(run_root / "run_manifest.json")
    results = {
        str(item["parent_claim_id"]): item
        for item in decomposition.get("results") or []
    }
    return _semantic_admission_artifact(
        manifest=manifest,
        bundle=_read_json(run_root / "evidence/evidence_bound_extraction_bundle.json"),
        evidence_draft=_read_json(run_root / "evidence/evidence_binding.json"),
        gate=_read_json(run_root / "evidence/quote_fidelity.json"),
        table_boundary=_read_json(run_root / "evidence/table_claim_safety.json")[
            "result"
        ],
        proposition_results=results,
    )


def _sf_report(sf_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_hashes = _read_json(sf_root / "phase3e2sf_artifact_hashes.json")[
        "artifacts"
    ]
    actual_hashes = {name: _sha256(sf_root / name) for name in expected_hashes}
    if actual_hashes != expected_hashes:
        raise ValueError("frozen S-F authority artifact mismatch")

    run_root = sf_root / "operational_run"
    triage = _read_json(sf_root / "phase3e2sf_system_triage_frozen.json")
    decomposition_path = run_root / "evidence/semantic_decomposition.json"
    old_semantic_path = run_root / "evidence/semantic_admission.json"
    semantic_hashes = {
        "semantic_decomposition.json": _sha256(decomposition_path),
        "semantic_admission.json": _sha256(old_semantic_path),
    }
    if semantic_hashes != triage["semantic_artifact_hashes"]:
        raise ValueError("frozen S-F semantic artifact mismatch")
    if triage["source_sha256"] != SF_SOURCE_SHA256:
        raise ValueError("frozen S-F source mismatch")

    decomposition = _read_json(decomposition_path)
    old_semantic = _read_json(old_semantic_path)
    semantic = _semantic_replay(run_root, decomposition)
    decisions = list(semantic.get("decisions") or [])
    old_decisions = list(old_semantic.get("decisions") or [])
    decision_by_id = {str(item["claim_id"]): item for item in decisions}
    old_by_id = {str(item["claim_id"]): item for item in old_decisions}
    human = _read_json(sf_root / "phase3e2sf_human_semantic_review.json")
    human_by_id = {str(item["claim_id"]): item for item in human["claims"]}
    expected_ids = [
        str(item["claim_id"])
        for item in _read_json(
            run_root / "evidence/evidence_bound_extraction_bundle.json"
        )["claims"]
    ]
    result_ids = [str(item.get("parent_claim_id") or "") for item in decomposition["results"]]
    input_ids = [str(item) for item in decomposition["input_parent_claim_ids"]]
    output_ids = [str(item) for item in decomposition["output_parent_claim_ids"]]
    identity_exact = (
        expected_ids == input_ids == output_ids == result_ids
        and set(expected_ids) == set(decision_by_id) == set(human_by_id)
    )

    repair_ids = {
        claim_id
        for claim_id, row in human_by_id.items()
        if row["human_decision"] == "HUMAN_NEEDS_REPAIR"
    }
    keep_ids = {
        claim_id
        for claim_id, row in human_by_id.items()
        if row["human_decision"] == "HUMAN_KEEP"
    }
    drop_ids = set(human_by_id) - repair_ids - keep_ids
    atomicity_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "ATOMICITY" in (row.get("repair_categories") or [])
    }
    nature_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "NATURE" in (row.get("repair_categories") or [])
    }
    evidence_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "EVIDENCE_BINDING" in (row.get("repair_categories") or [])
    }
    review_ids = {
        claim_id
        for claim_id, row in decision_by_id.items()
        if row["recommended_decision"] == "REVIEW"
    }
    keep_system_ids = {
        claim_id
        for claim_id, row in decision_by_id.items()
        if row["recommended_decision"] == "KEEP"
    }
    drop_system_ids = set(decision_by_id) - review_ids - keep_system_ids
    old_review_ids = {
        claim_id
        for claim_id, row in old_by_id.items()
        if row["recommended_decision"] == "REVIEW"
    }
    valid_ir_ids = {
        claim_id
        for claim_id, row in decision_by_id.items()
        if _validation(row).get("status") == "VALID"
    }
    atomicity_review_ids = {
        claim_id
        for claim_id, row in decision_by_id.items()
        if _guard(row, "atomicity_guard").get("status") == "REVIEW_REQUIRED"
    }
    nature_review_ids = {
        claim_id
        for claim_id, row in decision_by_id.items()
        if _guard(row, "nature_consistency_guard").get("status")
        == "REVIEW_REQUIRED"
    }
    atomicity_detected = atomicity_gold & atomicity_review_ids
    causally_correct_atomicity = {
        claim_id
        for claim_id in atomicity_detected
        if "INDEPENDENT_REVIEWABLE_PROPOSITIONS"
        in (_guard(decision_by_id[claim_id], "atomicity_guard").get("reason_codes") or [])
    }
    nature_detected = nature_gold & nature_review_ids
    nature_keep_false_positives = keep_ids & nature_review_ids
    full_nature_false_positives = (set(human_by_id) - nature_gold) & nature_review_ids
    catastrophic_false_drop = keep_ids & drop_system_ids
    unsupported_drop_ids = {
        claim_id
        for claim_id in drop_ids
        if human_by_id[claim_id].get("drop_category")
        == "UNSUPPORTED_SEMANTIC_CONTENT"
    }
    unsupported_false_keep = unsupported_drop_ids & keep_system_ids
    binding_failures = sum(
        int(_validation(row).get("evidence_binding_failures") or 0)
        for row in decisions
    )
    unsupported_content = sum(
        int(_validation(row).get("unsupported_content_failures") or 0)
        for row in decisions
    )
    residual = decision_by_id[KNOWN_NATURE_FALSE_NEGATIVE]
    known_residual_unchanged = (
        KNOWN_NATURE_FALSE_NEGATIVE in nature_gold
        and residual["recommended_decision"] == "KEEP"
        and _guard(residual, "nature_consistency_guard").get("status") == "ADMISSIBLE"
    )
    old_nature_review_ids = {
        claim_id
        for claim_id, row in old_by_id.items()
        if _guard(row, "nature_consistency_guard").get("status")
        == "REVIEW_REQUIRED"
    }
    old_nature_false_positives = old_nature_review_ids - nature_gold
    repaired_nature_false_positives = (
        old_nature_false_positives - nature_review_ids
    )

    metrics = {
        "claims": len(decisions),
        "claim_id_match": len(set(expected_ids) & set(result_ids)),
        "system_keep": len(keep_system_ids),
        "system_review": len(review_ids),
        "system_review_rate": _ratio(len(review_ids), len(decisions)),
        "system_review_human_keep": len(review_ids & keep_ids),
        "system_review_human_needs_repair": len(review_ids & repair_ids),
        "repair_detection_recall": _ratio(len(review_ids & repair_ids), len(repair_ids)),
        "atomicity_generalization_recall": _ratio(
            len(atomicity_detected), len(atomicity_gold)
        ),
        "causally_correct_atomicity_recall": _ratio(
            len(causally_correct_atomicity), len(atomicity_gold)
        ),
        "nature_generalization_recall": _ratio(
            len(nature_detected), len(nature_gold)
        ),
        "nature_human_keep_false_positives": len(nature_keep_false_positives),
        "full_nature_false_positives": len(full_nature_false_positives),
        "system_keep_precision": _ratio(
            len(keep_system_ids & keep_ids), len(keep_system_ids)
        ),
        "valid_proposition_ir_claims": len(valid_ir_ids),
        "valid_proposition_ir_rate": _ratio(len(valid_ir_ids), len(decisions)),
        "proposition_evidence_binding_failures": binding_failures,
        "unsupported_proposition_content": unsupported_content,
        "catastrophic_false_drop": len(catastrophic_false_drop),
        "unsupported_false_keep": len(unsupported_false_keep),
        "true_repair_reviews_preserved": len(old_review_ids & repair_ids & review_ids),
        "true_repair_reviews_original": len(old_review_ids & repair_ids),
        "false_positive_reviews_removed": len((old_review_ids & keep_ids) - review_ids),
        "false_positive_reviews_original": len(old_review_ids & keep_ids),
    }
    gates = {
        "S_F_CLAIMS_IS_47": metrics["claims"] == 47,
        "CLAIM_ID_MATCH_IS_47_OF_47": identity_exact,
        "SYSTEM_REVIEW_AT_MOST_14": metrics["system_review"] <= 14,
        "SYSTEM_REVIEW_RATE_AT_MOST_0_30": metrics["system_review_rate"] <= 0.30,
        "SYSTEM_REVIEW_HUMAN_NEEDS_REPAIR_AT_LEAST_12": (
            metrics["system_review_human_needs_repair"] >= 12
        ),
        "SYSTEM_REVIEW_HUMAN_KEEP_AT_MOST_2": metrics["system_review_human_keep"] <= 2,
        "REPAIR_DETECTION_RECALL_AT_LEAST_0_75": (
            metrics["repair_detection_recall"] >= 0.75
        ),
        "ATOMICITY_GENERALIZATION_RECALL_AT_LEAST_0_80": (
            metrics["atomicity_generalization_recall"] >= 0.80
        ),
        "CAUSALLY_CORRECT_ATOMICITY_RECALL_AT_LEAST_0_80": (
            metrics["causally_correct_atomicity_recall"] >= 0.80
        ),
        "NATURE_GENERALIZATION_RECALL_AT_LEAST_0_80": (
            metrics["nature_generalization_recall"] >= 0.80
        ),
        "SYSTEM_KEEP_PRECISION_AT_LEAST_0_80": (
            metrics["system_keep_precision"] >= 0.80
        ),
        "NATURE_HUMAN_KEEP_FALSE_POSITIVES_AT_MOST_3": (
            metrics["nature_human_keep_false_positives"] <= 3
        ),
        "NO_CATASTROPHIC_FALSE_DROP": not catastrophic_false_drop,
        "NO_UNSUPPORTED_FALSE_KEEP": not unsupported_false_keep,
        "VALID_PROPOSITION_IR_RATE_IS_1": metrics["valid_proposition_ir_rate"] == 1.0,
        "PROPOSITION_EVIDENCE_BINDING_FAILURES_ZERO": binding_failures == 0,
        "UNSUPPORTED_PROPOSITION_CONTENT_ZERO": unsupported_content == 0,
        "PROTECTED_ATOMICITY_TRUE_REPAIRS_REMAIN_REVIEW": (
            PROTECTED_ATOMICITY_IDS <= atomicity_review_ids
        ),
        "CLAIM_LEVEL_EVIDENCE_REPAIRS_REMAIN_REVIEW": evidence_gold <= review_ids,
        "KNOWN_RESIDUAL_NATURE_FALSE_NEGATIVE_UNCHANGED": known_residual_unchanged,
        "PRODUCT_PORTFOLIO_CASES_REMAIN_REVIEW": PORTFOLIO_IDS <= review_ids,
    }
    report = {
        "document_type": "phase3e2sh_sf_development_regression_report",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "authority": "FROZEN_S_F_DEVELOPMENT_ONLY_NOT_FRESH_GENERALIZATION",
        "source_sha256": SF_SOURCE_SHA256,
        "source_rerun": False,
        "semantic_decomposition_resampled": False,
        "human_gold_used_as_runtime_input": False,
        "replay_llm_calls": 0,
        "frozen_original_semantic_llm_calls": decomposition.get("semantic_llm_calls"),
        "frozen_input_hashes": {
            "top_level_artifacts": actual_hashes,
            "semantic_artifacts": semantic_hashes,
        },
        "metrics": metrics,
        "review_claim_ids": sorted(review_ids),
        "review_human_keep_claim_ids": sorted(review_ids & keep_ids),
        "review_human_needs_repair_claim_ids": sorted(review_ids & repair_ids),
        "atomicity_gold_claim_ids": sorted(atomicity_gold),
        "atomicity_detected_claim_ids": sorted(atomicity_detected),
        "nature_gold_claim_ids": sorted(nature_gold),
        "nature_detected_claim_ids": sorted(nature_detected),
        "nature_false_positive_signals_before": sorted(old_nature_false_positives),
        "nature_false_positive_signals_repaired": sorted(
            repaired_nature_false_positives
        ),
        "known_residual_nature_false_negative": {
            "claim_id": KNOWN_NATURE_FALSE_NEGATIVE,
            "unchanged": known_residual_unchanged,
        },
        "catastrophic_false_drop_claim_ids": sorted(catastrophic_false_drop),
        "unsupported_false_keep_claim_ids": sorted(unsupported_false_keep),
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }
    context = {
        "semantic": semantic,
        "old_semantic": old_semantic,
        "decision_by_id": decision_by_id,
        "old_by_id": old_by_id,
        "human_by_id": human_by_id,
        "repair_ids": repair_ids,
        "keep_ids": keep_ids,
        "evidence_gold": evidence_gold,
        "review_ids": review_ids,
        "atomicity_gold": atomicity_gold,
        "nature_gold": nature_gold,
        "nature_review_ids": nature_review_ids,
        "old_nature_false_positives": old_nature_false_positives,
        "repaired_nature_false_positives": repaired_nature_false_positives,
        "actual_hashes": actual_hashes,
        "semantic_hashes": semantic_hashes,
    }
    return report, context


def _coherence_report(
    sg_root: Path, sf: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, Any]:
    taxonomy_path = sg_root / "phase3e2sg_false_positive_taxonomy.json"
    taxonomy = _read_json(taxonomy_path)
    coherence_ids = {
        str(row["claim_id"])
        for row in taxonomy["records"]
        if row.get("repairability_bucket") == "EXISTING_ABSTRACTIONS"
        and row.get("exact_triggering_guard") == "CLAIM_ATOMICITY_ADMISSION_GUARD"
    }
    decisions = context["decision_by_id"]
    cases = []
    for claim_id in sorted(coherence_ids):
        atomicity = _guard(decisions[claim_id], "atomicity_guard")
        cases.append(
            {
                "claim_id": claim_id,
                "new_recommendation": decisions[claim_id]["recommended_decision"],
                "atomicity_status": atomicity.get("status"),
                "bounded_coherence_override": (atomicity.get("details") or {}).get(
                    "bounded_coherence_override"
                ),
            }
        )
    protected = {
        claim_id: _guard(decisions[claim_id], "atomicity_guard").get("status")
        for claim_id in sorted(PROTECTED_ATOMICITY_IDS)
    }
    portfolio = {
        claim_id: decisions[claim_id]["recommended_decision"]
        for claim_id in sorted(PORTFOLIO_IDS)
    }
    gates = {
        "ALL_EXISTING_ABSTRACTION_TRANSFER_CASES_RECONCILED": all(
            row["atomicity_status"] == "ADMISSIBLE" for row in cases
        ),
        "EXISTING_ABSTRACTION_TRANSFER_CASE_COUNT_IS_12": len(cases) == 12,
        "PROTECTED_ATOMICITY_CASES_REMAIN_REVIEW": all(
            status == "REVIEW_REQUIRED" for status in protected.values()
        ),
        "PRODUCT_PORTFOLIO_VECTOR_NOT_IN_SCHEMA": (
            "PRODUCT_PORTFOLIO_VECTOR" not in COHERENCE_TYPES
        ),
        "PRODUCT_PORTFOLIO_CASES_REMAIN_REVIEW": all(
            value == "REVIEW" for value in portfolio.values()
        ),
    }
    return {
        "document_type": "phase3e2sh_coherence_reconciliation_report",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "authority": sf["authority"],
        "runtime_decisions_independent_of_human_gold": True,
        "sg_taxonomy_sha256": _sha256(taxonomy_path),
        "existing_abstraction_cases": cases,
        "bounded_override_reason_counts": dict(
            Counter(
                row["bounded_coherence_override"]["reason"]
                for row in cases
                if row["bounded_coherence_override"]
            )
        ),
        "protected_atomicity_cases": protected,
        "product_portfolio_vector_implemented": False,
        "product_portfolio_cases": portfolio,
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }


def _nature_report(
    sc: Mapping[str, Any], sf: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, Any]:
    decisions = context["decision_by_id"]
    false_positive_cases = {
        claim_id: _guard(decisions[claim_id], "nature_consistency_guard").get("status")
        for claim_id in sorted(context["old_nature_false_positives"])
    }
    nature_gold = context["nature_gold"]
    detected = nature_gold & context["nature_review_ids"]
    gates = {
        "FOUR_FROZEN_FALSE_POSITIVE_SIGNALS_IDENTIFIED": len(false_positive_cases) == 4,
        "FOUR_FROZEN_FALSE_POSITIVE_SIGNALS_REPAIRED": all(
            status == "ADMISSIBLE" for status in false_positive_cases.values()
        ),
        "S_F_NATURE_RECALL_AT_LEAST_0_80": (
            sf["metrics"]["nature_generalization_recall"] >= 0.80
        ),
        "S_F_NATURE_HUMAN_KEEP_FALSE_POSITIVES_AT_MOST_3": (
            sf["metrics"]["nature_human_keep_false_positives"] <= 3
        ),
        "KNOWN_RESIDUAL_UNCHANGED": sf["known_residual_nature_false_negative"][
            "unchanged"
        ],
        "DISPOSAL_JIANG_REPAIR_REMAINS_CLOSED": (
            sc["metrics"]["original_jiang_fp_remaining"] == 0
        ),
    }
    return {
        "document_type": "phase3e2sh_nature_precision_report",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "false_positive_signals_before": false_positive_cases,
        "nature_gold_claim_ids": sorted(nature_gold),
        "nature_detected_claim_ids": sorted(detected),
        "known_residual_nature_false_negative": sf[
            "known_residual_nature_false_negative"
        ],
        "new_attribution_schema_or_taxonomy": False,
        "disposal_jiang_logic_changed": False,
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }


def _legacy_scope_report(sf: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    old = context["old_by_id"]
    new = context["decision_by_id"]
    human_keep = context["keep_ids"]
    candidates = set()
    for claim_id, decision in old.items():
        number = _guard(decision, "number_time_guard")
        subject = _guard(decision, "subject_scope_guard")
        evidence = decision.get("evidence_validation") or {}
        if (
            claim_id in human_keep
            and evidence.get("bound") is True
            and evidence.get("fidelity_status") in EXACT_FIDELITY
            and "NUMERIC_SCOPE_REVIEW_REQUIRED" in (number.get("reason_codes") or [])
            and "SUBJECT_SCOPE_REVIEW_REQUIRED" in (subject.get("reason_codes") or [])
        ):
            candidates.add(claim_id)
    cases = []
    for claim_id in sorted(candidates):
        decision = new[claim_id]
        cases.append(
            {
                "claim_id": claim_id,
                "new_recommendation": decision["recommended_decision"],
                "number_status": _guard(decision, "number_time_guard").get("status"),
                "number_reasons": _guard(decision, "number_time_guard").get(
                    "reason_codes"
                ),
                "subject_status": _guard(decision, "subject_scope_guard").get("status"),
                "subject_reasons": _guard(decision, "subject_scope_guard").get(
                    "reason_codes"
                ),
            }
        )
    unresolved = {
        claim_id: new[claim_id]["recommended_decision"]
        for claim_id in sorted(context["evidence_gold"])
    }
    gates = {
        "EXACT_BOUND_SCOPE_FALSE_POSITIVE_COUNT_IS_2": len(cases) == 2,
        "EXACT_BOUND_SCOPE_FALSE_POSITIVES_RECONCILED": all(
            row["new_recommendation"] == "KEEP"
            and row["number_reasons"] == ["AUTHORITATIVE_BOUND_SCOPE_RECONCILED"]
            and row["subject_reasons"] == ["AUTHORITATIVE_BOUND_SCOPE_RECONCILED"]
            for row in cases
        ),
        "UNRESOLVED_CLAIM_LEVEL_EVIDENCE_REPAIRS_REMAIN_REVIEW": all(
            recommendation == "REVIEW" for recommendation in unresolved.values()
        ),
    }
    return {
        "document_type": "phase3e2sh_legacy_scope_report",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "authoritative_bound_scope_cases": cases,
        "unresolved_claim_level_evidence_cases": unresolved,
        "proposition_evidence_binding_used_as_claim_binding_proof": False,
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }


def _true_positive_report(sf: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    decisions = context["decision_by_id"]
    atomicity = {
        claim_id: {
            "recommendation": decisions[claim_id]["recommended_decision"],
            "atomicity_status": _guard(decisions[claim_id], "atomicity_guard").get(
                "status"
            ),
        }
        for claim_id in sorted(PROTECTED_ATOMICITY_IDS)
    }
    evidence = {
        claim_id: decisions[claim_id]["recommended_decision"]
        for claim_id in sorted(context["evidence_gold"])
    }
    metrics = sf["metrics"]
    gates = {
        "FOUR_ATOMICITY_TRUE_REPAIRS_PROTECTED": all(
            row["recommendation"] == "REVIEW"
            and row["atomicity_status"] == "REVIEW_REQUIRED"
            for row in atomicity.values()
        ),
        "CLAIM_LEVEL_EVIDENCE_TRUE_REPAIRS_PROTECTED": all(
            recommendation == "REVIEW" for recommendation in evidence.values()
        ),
        "ALL_PREVIOUSLY_REVIEWED_TRUE_REPAIRS_PRESERVED": (
            metrics["true_repair_reviews_preserved"]
            == metrics["true_repair_reviews_original"]
            == 12
        ),
    }
    return {
        "document_type": "phase3e2sh_true_positive_protection_report",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "atomicity_protections": atomicity,
        "claim_level_evidence_protections": evidence,
        "known_residual_nature_false_negative": sf[
            "known_residual_nature_false_negative"
        ],
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--sf-root", type=Path, required=True)
    parser.add_argument("--sg-root", type=Path, required=True)
    parser.add_argument("--sc-semantic-artifact", type=Path, required=True)
    parser.add_argument("--frozen-schema-artifact", type=Path, required=True)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--focused-tests", default="NOT_RECORDED")
    parser.add_argument("--full-pytest", default="NOT_RECORDED")
    parser.add_argument("--compileall", default="NOT_RECORDED")
    parser.add_argument("--diff-check", default="NOT_RECORDED")
    parser.add_argument("--draft-pr-number", type=int)
    args = parser.parse_args()

    authority = args.authority_root.resolve()
    sf_root = args.sf_root.resolve()
    sg_root = args.sg_root.resolve()
    output = args.output_dir.resolve()
    repo = args.repo_root.resolve()
    sc_semantic_path = args.sc_semantic_artifact.resolve()
    if _sha256(sc_semantic_path) != SC_DECOMPOSITION_SHA256:
        raise ValueError("frozen S-C semantic artifact mismatch")

    production_pre = _production_state(args.production_db)
    sc_decomposition = _read_json(sc_semantic_path)
    sb = _sb_report(authority)
    sc, _, _ = _sc_report(authority, sc_decomposition)
    sb["document_type"] = "phase3e2sh_sb_regression_report"
    sb["s_h_replay_llm_calls"] = 0
    sc["document_type"] = "phase3e2sh_sc_regression_report"
    sc["s_h_replay_llm_calls"] = 0
    sc["frozen_semantic_artifact_sha256"] = SC_DECOMPOSITION_SHA256
    sf, context = _sf_report(sf_root)
    coherence = _coherence_report(sg_root, sf, context)
    nature = _nature_report(sc, sf, context)
    legacy = _legacy_scope_report(sf, context)
    protection = _true_positive_report(sf, context)

    frozen_schema = _read_json(args.frozen_schema_artifact.resolve())
    architecture = {
        "primary_prompt_sha256": _text_sha256(SOURCE_ANALYSIS_SYSTEM),
        "primary_prompt_unchanged": (
            _text_sha256(SOURCE_ANALYSIS_SYSTEM) == PRIMARY_PROMPT_SHA256
        ),
        "semantic_prompt_sha256": semantic_prompt_sha256(),
        "semantic_prompt_unchanged": semantic_prompt_sha256()
        == SEMANTIC_PROMPT_SHA256,
        "proposition_ir_schema_unchanged": proposition_ir_schema() == frozen_schema,
        "proposition_ir_inside_primary_extraction": (
            "proposition_ir" in SOURCE_ANALYSIS_SYSTEM.casefold()
        ),
        "product_portfolio_vector_implemented": (
            "PRODUCT_PORTFOLIO_VECTOR" in COHERENCE_TYPES
        ),
    }
    branch = _git(repo, "branch", "--show-current")
    head = _git(repo, "rev-parse", "HEAD")
    base_is_ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASE_IMPLEMENTATION_SHA, "HEAD"],
            cwd=repo,
            check=False,
        ).returncode
        == 0
    )
    modified_files = _git(repo, "diff", "--name-only", BASE_IMPLEMENTATION_SHA).splitlines()
    production_post = _production_state(args.production_db)
    production_unchanged = (
        production_pre["matches_frozen_baseline"]
        and production_post["matches_frozen_baseline"]
        and production_pre["sha256"] == production_post["sha256"]
    )
    implementation_gates = {
        "DEDICATED_BRANCH": branch == EXPECTED_BRANCH,
        "BASE_IMPLEMENTATION_IS_ANCESTOR": base_is_ancestor,
        "PRIMARY_EXTRACTION_PROMPT_UNCHANGED": architecture[
            "primary_prompt_unchanged"
        ],
        "SEMANTIC_DECOMPOSITION_PROMPT_UNCHANGED": architecture[
            "semantic_prompt_unchanged"
        ],
        "PROPOSITION_IR_SCHEMA_UNCHANGED": architecture[
            "proposition_ir_schema_unchanged"
        ],
        "PROPOSITION_IR_NOT_IN_PRIMARY_EXTRACTION": not architecture[
            "proposition_ir_inside_primary_extraction"
        ],
        "PRODUCT_PORTFOLIO_VECTOR_NOT_IMPLEMENTED": not architecture[
            "product_portfolio_vector_implemented"
        ],
        "S_B_REGRESSION_PASS": sb["gate"] == "PASS",
        "S_C_REGRESSION_PASS": sc["gate"] == "PASS",
        "S_F_DEVELOPMENT_REGRESSION_PASS": sf["gate"] == "PASS",
        "COHERENCE_RECONCILIATION_PASS": coherence["gate"] == "PASS",
        "NATURE_PRECISION_PASS": nature["gate"] == "PASS",
        "LEGACY_SCOPE_PASS": legacy["gate"] == "PASS",
        "TRUE_POSITIVE_PROTECTION_PASS": protection["gate"] == "PASS",
        "LLM_CALLS_DURING_INITIAL_S_H_REGRESSION_ZERO": True,
        "NEW_FRESH_SOURCE_INSPECTED_FALSE": True,
        "PRODUCTION_FROZEN": production_unchanged,
    }
    complete = all(implementation_gates.values())
    sfm = sf["metrics"]
    scm = sc["metrics"]
    final = {
        "document_type": "phase3e2sh_final_qualification_report",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "PHASE3E_STAGE3E2SH_COMPLETE": complete,
        "BRANCH": branch,
        "COMMIT_SHA": head,
        "DRAFT_PR_NUMBER": args.draft_pr_number,
        "BOUNDED_COHERENCE_RECONCILIATION_IMPLEMENTED": True,
        "LEGACY_SCOPE_PRECEDENCE_REPAIR_IMPLEMENTED": True,
        "NATURE_PRECISION_CLOSURE_IMPLEMENTED": True,
        "PRODUCT_PORTFOLIO_VECTOR_IMPLEMENTED": False,
        "S_B_ATOMICITY_RECALL": sb["atomicity"]["gold_recall"],
        "S_B_ATOMICITY_FALSE_POSITIVES": sb["atomicity"][
            "human_keep_false_positives"
        ],
        "S_B_NATURE_RECALL": sb["nature"]["gold_recall"],
        "S_B_NATURE_FALSE_POSITIVES": sb["nature"]["human_keep_false_positives"],
        "S_C_REPAIR_DETECTION_RECALL": scm["repair_detection_recall"],
        "S_C_ATOMICITY_RECALL": scm["atomicity_disposition_recall"],
        "S_C_CAUSALLY_CORRECT_ATOMICITY_RECALL": scm[
            "causally_correct_atomicity_recall"
        ],
        "S_C_NATURE_RECALL": scm["nature_recall"],
        "S_C_SYSTEM_KEEP_PRECISION": scm["system_keep_precision"],
        "S_C_REVIEW_RATE": scm["review_rate"],
        "S_F_SYSTEM_KEEP": sfm["system_keep"],
        "S_F_SYSTEM_REVIEW": sfm["system_review"],
        "S_F_SYSTEM_REVIEW_RATE": sfm["system_review_rate"],
        "S_F_SYSTEM_REVIEW_HUMAN_KEEP": sfm["system_review_human_keep"],
        "S_F_SYSTEM_REVIEW_HUMAN_NEEDS_REPAIR": sfm[
            "system_review_human_needs_repair"
        ],
        "S_F_REPAIR_DETECTION_RECALL": sfm["repair_detection_recall"],
        "S_F_ATOMICITY_RECALL": sfm["atomicity_generalization_recall"],
        "S_F_CAUSALLY_CORRECT_ATOMICITY_RECALL": sfm[
            "causally_correct_atomicity_recall"
        ],
        "S_F_NATURE_RECALL": sfm["nature_generalization_recall"],
        "S_F_NATURE_HUMAN_KEEP_FALSE_POSITIVES": sfm[
            "nature_human_keep_false_positives"
        ],
        "S_F_SYSTEM_KEEP_PRECISION": sfm["system_keep_precision"],
        "S_F_KNOWN_RESIDUAL_NATURE_FALSE_NEGATIVE": True,
        "KNOWN_RESIDUAL_NATURE_FALSE_NEGATIVE_CLAIM_ID": KNOWN_NATURE_FALSE_NEGATIVE,
        "S_F_TRUE_REPAIR_REVIEWS_PRESERVED": (
            f"{sfm['true_repair_reviews_preserved']}/{sfm['true_repair_reviews_original']}"
        ),
        "S_F_FALSE_POSITIVE_REVIEWS_REMOVED": (
            f"{sfm['false_positive_reviews_removed']}/{sfm['false_positive_reviews_original']}"
        ),
        "LLM_CALLS_DURING_INITIAL_S_H_REGRESSION": 0,
        "PRIMARY_EXTRACTION_LLM_CALLS": 0,
        "SEMANTIC_LLM_CALLS": 0,
        "NEW_FRESH_SOURCE_INSPECTED": False,
        "PRODUCTION_PRE_SHA256": production_pre["sha256"],
        "PRODUCTION_POST_SHA256": production_post["sha256"],
        "PRODUCTION_CHANGED": "NO" if production_unchanged else "YES",
        "PRODUCTION_APPLY_ATTEMPTED": False,
        "S_B_REGRESSION_GATE": sb["gate"],
        "S_C_REGRESSION_GATE": sc["gate"],
        "S_F_DEVELOPMENT_REGRESSION_GATE": sf["gate"],
        "NEXT_RECOMMENDED_STAGE": (
            "Phase 3E.2S-I — Final Independent Untouched Fresh-Source Acceptance Pilot"
        ),
        "S_F_STATUS": "FAILED_FRESH_HOLDOUT_DEVELOPMENT_ONLY",
        "PHASE3E3_STATUS": "BLOCKED_PENDING_FINAL_UNTOUCHED_HOLDOUT",
        "architecture": architecture,
        "production_pre": production_pre,
        "production_post": production_post,
        "gates": implementation_gates,
    }
    receipt = {
        "document_type": "phase3e2sh_implementation_receipt",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "base_implementation_sha": BASE_IMPLEMENTATION_SHA,
        "branch": branch,
        "head_at_qualification": head,
        "draft_pr_number": args.draft_pr_number,
        "modified_files_from_baseline": modified_files,
        "architecture": architecture,
        "implementation": {
            "bounded_coherence_reconciliation": True,
            "legacy_scope_precedence_repair": True,
            "nature_precision_closure": True,
            "product_portfolio_vector": False,
        },
        "test_evidence": {
            "focused_tests": args.focused_tests,
            "full_pytest": args.full_pytest,
            "compileall": args.compileall,
            "git_diff_check": args.diff_check,
        },
        "runtime": {
            "llm_calls_during_initial_s_h_regression": 0,
            "primary_extraction_llm_calls": 0,
            "semantic_llm_calls": 0,
            "new_fresh_source_inspected": False,
        },
        "production_pre": production_pre,
        "production_post": production_post,
        "production_apply_attempted": False,
        "qualification_complete": complete,
        "gates": implementation_gates,
    }

    artifacts = {
        "phase3e2sh_implementation_receipt.json": receipt,
        "phase3e2sh_coherence_reconciliation_report.json": coherence,
        "phase3e2sh_nature_precision_report.json": nature,
        "phase3e2sh_legacy_scope_report.json": legacy,
        "phase3e2sh_sb_regression_report.json": sb,
        "phase3e2sh_sc_regression_report.json": sc,
        "phase3e2sh_sf_development_regression_report.json": sf,
        "phase3e2sh_true_positive_protection_report.json": protection,
        "phase3e2sh_final_qualification_report.json": final,
    }
    for name, payload in artifacts.items():
        _write_json(output / name, payload)
    artifact_hashes = {name: _sha256(output / name) for name in artifacts}
    _write_json(
        output / "phase3e2sh_artifact_hashes.json",
        {
            "document_type": "phase3e2sh_artifact_hashes",
            "schema_version": "1.0",
            "generated_at_utc": _utc_now(),
            "hash_algorithm": "SHA256",
            "artifacts": artifact_hashes,
            "all_required_artifacts_hashed": len(artifact_hashes) == 9,
        },
    )
    print(
        json.dumps(
            {
                "output_dir": str(output),
                "s_b_gate": sb["gate"],
                "s_c_gate": sc["gate"],
                "s_f_gate": sf["gate"],
                "s_f_review": sfm["system_review"],
                "s_f_review_rate": sfm["system_review_rate"],
                "qualification_complete": complete,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
