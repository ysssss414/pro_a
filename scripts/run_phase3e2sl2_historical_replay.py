from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pro_a.operational_ingestion import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    _semantic_admission_artifact,
)

from run_phase3e2se_qualification import _sb_report, _sc_report
from run_phase3e2sh_qualification import (
    SC_DECOMPOSITION_SHA256,
    _coherence_report,
    _legacy_scope_report,
    _nature_report,
    _sf_report,
    _true_positive_report,
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _categories(row: Mapping[str, Any]) -> set[str]:
    raw = row.get("repair_categories") or []
    if isinstance(raw, str):
        return {item.strip() for item in raw.split("+") if item.strip()}
    return {str(item) for item in raw}


def _si_replay(root: Path) -> dict[str, Any]:
    run = root / "operational_run"
    bundle = _read(run / "evidence/evidence_bound_extraction_bundle.json")
    decomposition_path = run / "evidence/semantic_decomposition.json"
    decomposition = _read(decomposition_path)
    semantic = _semantic_admission_artifact(
        manifest=_read(run / "run_manifest.json"),
        bundle=bundle,
        evidence_draft=_read(run / "evidence/evidence_binding.json"),
        gate=_read(run / "evidence/quote_fidelity.json"),
        table_boundary=_read(run / "evidence/table_claim_safety.json")["result"],
        proposition_results={
            row["parent_claim_id"]: row for row in decomposition["results"]
        },
    )
    decisions = list(semantic["decisions"])
    human = _read(root / "phase3e2si_human_semantic_review.json")
    decision_by_id = {row["claim_id"]: row for row in decisions}
    human_by_id = {row["claim_id"]: row for row in human["claims"]}
    expected_ids = [row["claim_id"] for row in bundle["claims"]]
    identity_exact = (
        expected_ids == list(decomposition["input_parent_claim_ids"])
        == list(decomposition["output_parent_claim_ids"])
        == [row["parent_claim_id"] for row in decomposition["results"]]
        and set(expected_ids) == set(decision_by_id) == set(human_by_id)
    )
    if not identity_exact:
        raise RuntimeError("S_I_REPLAY_CLAIM_UNIVERSE_MISMATCH")

    human_keep = {
        claim_id
        for claim_id, row in human_by_id.items()
        if row["human_decision"] == "HUMAN_KEEP"
    }
    repair_ids = {
        claim_id
        for claim_id, row in human_by_id.items()
        if row["human_decision"] == "HUMAN_NEEDS_REPAIR"
    }
    atomicity_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "ATOMICITY" in _categories(row)
    }
    nature_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "NATURE" in _categories(row)
    }
    duplicate_gold = {
        claim_id
        for claim_id, row in human_by_id.items()
        if "DUPLICATE" in _categories(row)
    }
    system_keep = {
        row["claim_id"] for row in decisions if row["recommended_decision"] == "KEEP"
    }
    system_review = {
        row["claim_id"]
        for row in decisions
        if row["recommended_decision"] == "REVIEW"
    }
    system_drop = {
        row["claim_id"] for row in decisions if row["recommended_decision"] == "DROP"
    }
    atomicity_detected = {
        claim_id
        for claim_id in atomicity_gold
        if decision_by_id[claim_id]["semantic_admission"]["atomicity_guard"]["status"]
        == "REVIEW_REQUIRED"
    }
    causally_correct = {
        claim_id
        for claim_id in atomicity_detected
        if "INDEPENDENT_REVIEWABLE_PROPOSITIONS"
        in decision_by_id[claim_id]["semantic_admission"]["atomicity_guard"][
            "reason_codes"
        ]
    }
    nature_detected = {
        claim_id
        for claim_id in nature_gold
        if decision_by_id[claim_id]["semantic_admission"]["nature_consistency_guard"][
            "status"
        ]
        == "REVIEW_REQUIRED"
    }
    nature_false_positives = {
        claim_id
        for claim_id in human_keep
        if decision_by_id[claim_id]["semantic_admission"]["nature_consistency_guard"][
            "status"
        ]
        == "REVIEW_REQUIRED"
    }
    validations = {
        row["claim_id"]: row["semantic_admission"]["proposition_ir_validation"]
        for row in decisions
    }
    duplicate_candidates = {
        row["claim_id"]: row["duplicate_of_claim_id"]
        for row in decisions
        if row.get("duplicate_of_claim_id")
    }
    duplicate_false_positives = set(duplicate_candidates) - duplicate_gold
    unsupported_false_keep = {
        claim_id
        for claim_id in system_keep
        if int(validations[claim_id].get("unsupported_content_failures") or 0) > 0
        or int(validations[claim_id].get("evidence_binding_failures") or 0) > 0
    }
    detected_repairs = repair_ids & (system_review | system_drop)
    repair_recall = len(detected_repairs) / len(repair_ids)
    atomicity_recall = len(atomicity_detected) / len(atomicity_gold)
    causal_recall = len(causally_correct) / len(atomicity_gold)
    nature_recall = len(nature_detected) / len(nature_gold)
    keep_precision = len(system_keep & human_keep) / len(system_keep)
    review_rate = len(system_review) / len(decisions)
    valid_ir_rate = sum(
        row["status"] == "VALID" for row in validations.values()
    ) / len(validations)
    evidence_failures = sum(
        int(row.get("evidence_binding_failures") or 0) for row in validations.values()
    )
    unsupported_content = sum(
        int(row.get("unsupported_content_failures") or 0) for row in validations.values()
    )
    catastrophic_false_drops = len(system_drop & human_keep)
    nature_fp_limit = max(3, 0.10 * len(human_keep))
    gates = {
        "CLAIM_UNIVERSE_IDENTITY_EXACT": identity_exact,
        "REPAIR_DETECTION_RECALL_AT_LEAST_0_75": repair_recall >= 0.75,
        "ATOMICITY_RECALL_AT_LEAST_0_80": atomicity_recall >= 0.80,
        "CAUSALLY_CORRECT_ATOMICITY_RECALL_AT_LEAST_0_80": causal_recall >= 0.80,
        "NATURE_RECALL_AT_LEAST_0_80": nature_recall >= 0.80,
        "SYSTEM_KEEP_PRECISION_AT_LEAST_0_80": keep_precision >= 0.80,
        "NATURE_FALSE_POSITIVE_CONTROL_PASS": len(nature_false_positives)
        <= nature_fp_limit,
        "SYSTEM_REVIEW_RATE_AT_MOST_0_30": review_rate <= 0.30,
        "VALID_PROPOSITION_IR_AT_LEAST_0_95": valid_ir_rate >= 0.95,
        "EVIDENCE_BINDING_FAILURES_ZERO": evidence_failures == 0,
        "UNSUPPORTED_PROPOSITION_CONTENT_ZERO": unsupported_content == 0,
        "CATASTROPHIC_FALSE_DROPS_ZERO": catastrophic_false_drops == 0,
        "UNSUPPORTED_FALSE_KEEP_ZERO": not unsupported_false_keep,
        "DUPLICATE_NEGATIVE_CONTROLS_PASS": not duplicate_false_positives,
        "DUPLICATE_SIMILARITY_THRESHOLD_FROZEN": DUPLICATE_SIMILARITY_THRESHOLD
        == 0.92,
    }
    return {
        "source_sha256": bundle["source"]["sha256"],
        "semantic_decomposition_sha256": _sha256(decomposition_path),
        "claim_universe": {
            "total": len(decisions),
            "human_keep": len(human_keep),
            "human_needs_repair": len(repair_ids),
            "system_keep": len(system_keep),
            "system_review": len(system_review),
            "system_drop": len(system_drop),
        },
        "metrics": {
            "repair_detection_recall": repair_recall,
            "atomicity_recall": atomicity_recall,
            "causally_correct_atomicity_recall": causal_recall,
            "nature_recall": nature_recall,
            "system_keep_precision": keep_precision,
            "system_review_rate": review_rate,
            "valid_proposition_ir_rate": valid_ir_rate,
            "evidence_binding_failures": evidence_failures,
            "unsupported_proposition_content": unsupported_content,
            "catastrophic_false_drops": catastrophic_false_drops,
            "unsupported_false_keep": len(unsupported_false_keep),
            "nature_human_keep_false_positives": len(nature_false_positives),
            "nature_false_positive_limit": nature_fp_limit,
            "duplicate_false_positives": len(duplicate_false_positives),
        },
        "duplicate": {
            "similarity_threshold": DUPLICATE_SIMILARITY_THRESHOLD,
            "gold_ids": sorted(duplicate_gold),
            "candidates": duplicate_candidates,
            "false_positive_ids": sorted(duplicate_false_positives),
        },
        "case_ids": {
            "detected_repairs": sorted(detected_repairs),
            "atomicity_detected": sorted(atomicity_detected),
            "causally_correct_atomicity": sorted(causally_correct),
            "nature_detected": sorted(nature_detected),
            "nature_false_positives": sorted(nature_false_positives),
        },
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
        "llm_calls": 0,
    }


def build(repo: Path, sc_semantic_path: Path) -> dict[str, Any]:
    if _sha256(sc_semantic_path) != SC_DECOMPOSITION_SHA256:
        raise RuntimeError("FROZEN_S_C_SEMANTIC_ARTIFACT_MISMATCH")
    sc_decomposition = _read(sc_semantic_path)
    sb = _sb_report(repo)
    sc, _, _ = _sc_report(repo, sc_decomposition)
    sf, context = _sf_report(repo / "workspace/phase3e2sf_run")
    coherence = _coherence_report(repo / "workspace/phase3e2sg", sf, context)
    nature = _nature_report(sc, sf, context)
    legacy = _legacy_scope_report(sf, context)
    protection = _true_positive_report(sf, context)
    sh_components = {
        "coherence": coherence["gate"],
        "nature_precision": nature["gate"],
        "legacy_scope": legacy["gate"],
        "true_positive_protection": protection["gate"],
        "s_b": sb["gate"],
        "s_c": sc["gate"],
        "s_f": sf["gate"],
    }
    sh_gate = "PASS" if all(value == "PASS" for value in sh_components.values()) else "FAIL"
    si = _si_replay(repo / "workspace/phase3e2si_final_acceptance")
    stages = {
        "S_B_REPLAY": sb["gate"],
        "S_C_REPLAY": sc["gate"],
        "S_F_REPLAY": sf["gate"],
        "S_H_REPLAY": sh_gate,
        "S_I_REPLAY": si["gate"],
    }
    return {
        "document_type": "phase3e2sl2_historical_replay",
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "DEVELOPMENT_REGRESSION_REPLAY_WITH_FROZEN_EXTRACTION_AND_HUMAN_LABELS",
        "baseline": "e7878cc42447bfc06e8e23da54e2c0c720311f13",
        "llm_usage": {
            "llm_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        },
        "frozen_s_c_semantic_artifact": {
            "path": str(sc_semantic_path),
            "sha256": _sha256(sc_semantic_path),
        },
        "stages": stages,
        "all_required_historical_replays_pass": all(
            value == "PASS" for value in stages.values()
        ),
        "s_b": sb,
        "s_c": sc,
        "s_f": sf,
        "s_h": {
            "components": sh_components,
            "gate": sh_gate,
            "coherence": coherence,
            "nature_precision": nature,
            "legacy_scope": legacy,
            "true_positive_protection": protection,
        },
        "s_i": si,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--sc-semantic-artifact", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("workspace/phase3e2sl2/phase3e2sl2_historical_replay.json"),
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    sc_semantic_path = args.sc_semantic_artifact.resolve()
    output = args.output
    if not output.is_absolute():
        output = repo / output
    report = build(repo, sc_semantic_path)
    _write(output, report)
    print(
        json.dumps(
            {
                "stages": report["stages"],
                "s_i_metrics": report["s_i"]["metrics"],
                "complete": report["all_required_historical_replays_pass"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_required_historical_replays_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
