"""Offline replay and gold qualification for semantic-admission decisions.

Recommendation computation is deliberately separate from gold evaluation:
human labels are accepted only by :func:`build_post_hardening_replay` after
all runtime recommendations have already been produced.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .operational_ingestion import _semantic_admission_artifact


FROZEN_ARTIFACT_SHA256 = {
    "review/phase3e2_human_semantic_review.json": (
        "2f3d317c9e6dfed3b64c2bbbb84590cc1328a680aec1b993eadb994418c639b7"
    ),
    "receipts/phase3e2_human_semantic_review_bound.json": (
        "addb5f12e782d72492a56b264ddccdb27b8e299589156fe0bf9263b6f41ed52b"
    ),
    "review/claim_repair_draft.json": (
        "013dee86810d86ebeee685dce4eb230f22e0d4b58bba40b518220d4cdc7b5cef"
    ),
    "review/semantic_admission_false_positive_census.json": (
        "696ac8ff426ff0fad08e85444d12ffc2de39dba4bd42efd85a226df0f9d20404"
    ),
}

_GUARD_KEYS = (
    "question_premise_guard",
    "precision_token_guard",
    "number_time_guard",
    "subject_scope_guard",
    "atomicity_guard",
    "nature_consistency_guard",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def recompute_semantic_recommendations(
    *,
    run_id: str,
    source_sha256: str,
    extracted_bundle: Mapping[str, Any],
    evidence_support: Mapping[str, Any],
    quote_fidelity: Mapping[str, Any],
    table_boundary: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute recommendations using Claim and permitted Source support only."""
    result = _semantic_admission_artifact(
        manifest={"run_id": run_id, "source": {"sha256": source_sha256}},
        bundle=extracted_bundle,
        evidence_draft=evidence_support,
        gate=quote_fidelity,
        table_boundary=table_boundary,
    )
    result["policy"]["human_gold_used_as_runtime_input"] = False
    return result


def _recommendation_matrix(
    decisions: list[Mapping[str, Any]],
    human_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    labels = ("KEEP", "NEEDS_REPAIR", "DROP")
    matrix = {
        recommendation: {label: 0 for label in labels}
        for recommendation in ("KEEP", "REVIEW", "DROP")
    }
    for decision in decisions:
        human = human_by_id[decision["claim_id"]]["human_semantic_decision"]
        matrix[decision["recommended_decision"]][human] += 1
    return matrix


def _recommendation_counts(decisions: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(item["recommended_decision"] for item in decisions)
    return {key: counts[key] for key in ("KEEP", "REVIEW", "DROP")}


def _guard_statuses(decision: Mapping[str, Any]) -> dict[str, str]:
    guards = decision.get("semantic_admission") or {}
    return {
        key: str((guards.get(key) or {}).get("status") or "NOT_PRESENT")
        for key in _GUARD_KEYS
    }


def _reason_codes(decision: Mapping[str, Any]) -> list[str]:
    guards = decision.get("semantic_admission") or {}
    return list(dict.fromkeys(
        reason
        for key in _GUARD_KEYS
        for reason in (guards.get(key) or {}).get("reason_codes") or []
        if (guards.get(key) or {}).get("status") != "ADMISSIBLE"
    ))


def _repair_categories(repair_draft: Mapping[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for entry in repair_draft.get("repair_entries") or []:
        categories = str(entry.get("repair_reason_code") or "").split("+")
        result.setdefault(entry["original_claim_id"], set()).update(categories)
    return result


def _material_diff_length(quote: Mapping[str, Any]) -> int:
    fragments = [
        str(item.get(side) or "")
        for item in quote.get("diagnostic_diff") or []
        for side in ("model", "source")
    ]
    material = re.sub(r"[\W_]+", "", "".join(fragments), flags=re.UNICODE)
    return len(material)


def _evidence_repair_category(
    entry: Mapping[str, Any],
    quote: Mapping[str, Any],
) -> str:
    note = str(entry.get("human_review_note") or "")
    lowered = note.casefold()
    if "cross-page" in lowered or "across the page" in lowered or re.search(
        r"pages?\s+\d+\s*[–-]\s*\d+", lowered
    ):
        return "CROSS_PAGE_CONTINUATION"

    pointer = str(
        ((entry.get("original_claim_snapshot") or {}).get("evidence_pointer")) or ""
    )
    expected_page = re.search(r"source page\s+(\d+)", lowered)
    pointer_page = re.search(r"PAGE:(\d+)", pointer)
    if expected_page and pointer_page and expected_page.group(1) != pointer_page.group(1):
        return "PAGE_POINTER_MISMATCH"

    if quote.get("fidelity_status") == "QUOTE_DRIFT":
        if _material_diff_length(quote) <= 4:
            return "LAYOUT_NORMALIZATION"
        return "BOUNDED_CONTEXT_INSUFFICIENT"
    if quote.get("fidelity_status") == "UNRESOLVED_SOURCE_BINDING":
        return "OTHER"
    return "OTHER"


def _evidence_binding_audit(
    repair_draft: Mapping[str, Any],
    quote_fidelity: Mapping[str, Any],
) -> dict[str, Any]:
    quote_by_id = {
        item["claim_id"]: item for item in quote_fidelity.get("claims") or []
    }
    cases = []
    for entry in repair_draft.get("repair_entries") or []:
        categories = str(entry.get("repair_reason_code") or "").split("+")
        if "EVIDENCE_BINDING" not in categories:
            continue
        claim_id = entry["original_claim_id"]
        quote = quote_by_id.get(claim_id) or {}
        cases.append({
            "claim_id": claim_id,
            "classification": _evidence_repair_category(entry, quote),
            "fidelity_status": quote.get("fidelity_status"),
            "repair_applied": False,
        })
    classifications = Counter(item["classification"] for item in cases)
    return {
        "repair_case_count": len(cases),
        "classification_counts": dict(sorted(classifications.items())),
        "cases": cases,
        "general_repair": "DEFERRED",
        "cases_fixed": 0,
        "finding": "HETEROGENEOUS_NO_SAFE_COMMON_DETERMINISTIC_REPAIR",
    }


def build_post_hardening_replay(
    *,
    old_semantic: Mapping[str, Any],
    new_semantic: Mapping[str, Any],
    human_review: Mapping[str, Any],
    repair_draft: Mapping[str, Any],
    quote_fidelity: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate frozen recommendations against human labels used only as oracle."""
    old_decisions = list(old_semantic.get("decisions") or [])
    new_decisions = list(new_semantic.get("decisions") or [])
    human_by_id = {
        item["claim_id"]: item for item in human_review.get("claim_decisions") or []
    }
    old_by_id = {item["claim_id"]: item for item in old_decisions}
    new_by_id = {item["claim_id"]: item for item in new_decisions}
    if set(old_by_id) != set(new_by_id) or set(new_by_id) != set(human_by_id):
        raise ValueError("replay Claim universes do not match")

    categories = _repair_categories(repair_draft)
    human_keep_ids = {
        claim_id for claim_id, row in human_by_id.items()
        if row["human_semantic_decision"] == "KEEP"
    }
    prior_false_drop_keep = {
        claim_id for claim_id in human_keep_ids
        if old_by_id[claim_id]["recommended_decision"] == "DROP"
    }
    atomicity_gold = {
        claim_id for claim_id, values in categories.items() if "ATOMICITY" in values
    }
    nature_gold = {
        claim_id for claim_id, values in categories.items() if "NATURE" in values
    }
    atomicity_review = {
        claim_id for claim_id in atomicity_gold
        if _guard_statuses(new_by_id[claim_id])["atomicity_guard"] == "REVIEW_REQUIRED"
    }
    nature_review = {
        claim_id for claim_id in nature_gold
        if _guard_statuses(new_by_id[claim_id])["nature_consistency_guard"] == "REVIEW_REQUIRED"
    }
    atomicity_keep_false_positives = {
        claim_id for claim_id in human_keep_ids
        if _guard_statuses(new_by_id[claim_id])["atomicity_guard"] == "REVIEW_REQUIRED"
    }
    nature_keep_false_positives = {
        claim_id for claim_id in human_keep_ids
        if _guard_statuses(new_by_id[claim_id])["nature_consistency_guard"] == "REVIEW_REQUIRED"
    }
    new_human_keep_blocked = {
        claim_id for claim_id in human_keep_ids
        if (new_by_id[claim_id].get("semantic_admission") or {}).get(
            "overall_guard_disposition"
        ) == "BLOCKED"
    }
    token_false_drop_keep_after = {
        claim_id for claim_id in prior_false_drop_keep
        if new_by_id[claim_id]["recommended_decision"] == "DROP"
    }

    atomicity_recall = len(atomicity_review) / len(atomicity_gold) if atomicity_gold else 0.0
    atomicity_keep_fp_rate = (
        len(atomicity_keep_false_positives) / len(human_keep_ids)
        if human_keep_ids else 0.0
    )
    nature_recall = len(nature_review) / len(nature_gold) if nature_gold else 0.0

    per_claim = []
    for claim_id in old_by_id:
        old = old_by_id[claim_id]
        new = new_by_id[claim_id]
        old_statuses = _guard_statuses(old)
        new_statuses = _guard_statuses(new)
        changed = [
            key for key in _GUARD_KEYS
            if old_statuses[key] != new_statuses[key]
            and not (old_statuses[key] == "NOT_PRESENT" and new_statuses[key] == "ADMISSIBLE")
        ]
        per_claim.append({
            "claim_id": claim_id,
            "old_recommendation": old["recommended_decision"],
            "new_recommendation": new["recommended_decision"],
            "human_gold_label": human_by_id[claim_id]["human_semantic_decision"],
            "changed_guards": changed,
            "old_guard_statuses": old_statuses,
            "new_guard_statuses": new_statuses,
            "reason_codes": _reason_codes(new),
        })

    human_counts = Counter(
        item["human_semantic_decision"] for item in human_by_id.values()
    )
    evidence_audit = _evidence_binding_audit(repair_draft, quote_fidelity)
    gates = {
        "human_gold_counts_match": dict(human_counts) == {
            "KEEP": 54,
            "NEEDS_REPAIR": 40,
            "DROP": 4,
        },
        "token_false_drop_keep_after_zero": not token_false_drop_keep_after,
        "atomicity_gold_recall_at_least_0_85": atomicity_recall >= 0.85,
        "atomicity_keep_false_positive_rate_at_most_0_10": atomicity_keep_fp_rate <= 0.10,
        "nature_gold_recall_complete": nature_recall == 1.0,
        "nature_keep_false_positives_at_most_3": len(nature_keep_false_positives) <= 3,
        "new_human_keep_blocked_zero": not new_human_keep_blocked,
    }
    return {
        "document_type": "phase3e2sb_semantic_admission_post_hardening_replay",
        "schema_version": "1",
        "run_id": human_review.get("run_id"),
        "source_sha256": human_review.get("source_sha256"),
        "authority": "OFFLINE_FROZEN_GOLD_DIAGNOSTIC_NO_PRODUCTION_AUTHORITY",
        "runtime_policy": {
            "real_cloud_llm_calls": 0,
            "human_gold_used_as_runtime_input": False,
            "claim_text_rewritten": False,
            "canonical_claims_changed": False,
            "repair_draft_applied": False,
        },
        "human_gold_counts": dict(sorted(human_counts.items())),
        "before_recommendation_counts": _recommendation_counts(old_decisions),
        "after_recommendation_counts": _recommendation_counts(new_decisions),
        "before_recommendation_matrix": _recommendation_matrix(old_decisions, human_by_id),
        "after_recommendation_matrix": _recommendation_matrix(new_decisions, human_by_id),
        "token_provenance_metrics": {
            "false_drop_human_keep_before": len(prior_false_drop_keep),
            "false_drop_human_keep_after": len(token_false_drop_keep_after),
            "remaining_false_drop_claim_ids": sorted(token_false_drop_keep_after),
        },
        "atomicity_metrics": {
            "gold_cases": len(atomicity_gold),
            "gold_review_count": len(atomicity_review),
            "gold_recall": atomicity_recall,
            "human_keep_false_positives": len(atomicity_keep_false_positives),
            "human_keep_false_positive_rate": atomicity_keep_fp_rate,
        },
        "nature_metrics": {
            "gold_cases": len(nature_gold),
            "gold_review_count": len(nature_review),
            "gold_recall": nature_recall,
            "human_keep_false_positives": len(nature_keep_false_positives),
        },
        "new_human_keep_blocked": len(new_human_keep_blocked),
        "new_human_keep_blocked_claim_ids": sorted(new_human_keep_blocked),
        "evidence_binding_audit": evidence_audit,
        "gates": gates,
        "frozen_gold_replay_pass": all(gates.values()),
        "per_claim": per_claim,
    }


def write_frozen_gold_replay(run_root: Path) -> tuple[Path, dict[str, Any]]:
    """Verify the S-B frozen inputs, replay them, and write the audit artifact."""
    verified_hashes = {}
    for relative, expected in FROZEN_ARTIFACT_SHA256.items():
        actual = _sha256(run_root / relative)
        if actual != expected:
            raise ValueError(f"frozen artifact hash mismatch: {relative}")
        verified_hashes[relative] = actual

    bundle = _load_json(run_root / "evidence/evidence_bound_extraction_bundle.json")
    evidence_support = _load_json(run_root / "evidence/evidence_binding.json")
    quote_fidelity = _load_json(run_root / "evidence/quote_fidelity.json")
    table_boundary = _load_json(run_root / "evidence/table_claim_safety.json")["result"]
    old_semantic = _load_json(run_root / "evidence/semantic_admission.json")
    human_review = _load_json(run_root / "review/phase3e2_human_semantic_review.json")
    repair_draft = _load_json(run_root / "review/claim_repair_draft.json")

    new_semantic = recompute_semantic_recommendations(
        run_id=str(human_review["run_id"]),
        source_sha256=str(human_review["source_sha256"]),
        extracted_bundle=bundle,
        evidence_support=evidence_support,
        quote_fidelity=quote_fidelity,
        table_boundary=table_boundary,
    )
    artifact = build_post_hardening_replay(
        old_semantic=old_semantic,
        new_semantic=new_semantic,
        human_review=human_review,
        repair_draft=repair_draft,
        quote_fidelity=quote_fidelity,
    )
    artifact["frozen_input_sha256"] = verified_hashes
    output_path = run_root / "review/semantic_admission_post_hardening_replay.json"
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path, artifact
