from __future__ import annotations

import copy
import inspect
import json

import pytest

from pro_a.corpus_pilot import PilotError
from pro_a.pilot3_controlled_reextraction_human_review import (
    ANNOTATIONS_DOCUMENT_TYPE,
    CLAIMS_TOTAL,
    EVALUATION_ANNOTATIONS_DOCUMENT_TYPE,
    RUN_ID,
    SOURCE_SHA256,
    _validate_evaluation_annotations,
    build_blind_human_decisions,
    freeze_blind_human_decisions,
)
from pro_a.storage import sha256_file, write_json


def _fixture(tmp_path):
    ids = [f"CLM_S3_FIXTURE_{index:02d}" for index in range(CLAIMS_TOTAL)]
    claims = [
        {
            "claim_id": claim_id,
            "statement": f"Statement {index}",
            "attributed_to": "Expert",
            "evidence_excerpt": f"Evidence {index}",
        }
        for index, claim_id in enumerate(ids)
    ]
    bundle = {
        "pilot_run_id": RUN_ID,
        "source": {"sha256": SOURCE_SHA256},
        "claims": claims,
    }
    evidence = {
        "pilot_run_id": RUN_ID,
        "claims": [
            {
                "claim_id": item["claim_id"],
                "original_evidence_excerpt": item["evidence_excerpt"],
                "context_locators": ["PAGE:1"],
                "bounded_context_candidates": [
                    {"direction": "before", "text": "context", "locators": ["PAGE:1"]}
                ],
            }
            for item in claims
        ],
    }
    quote_claims = []
    annotations = []
    for index, claim_id in enumerate(ids):
        if index < 9:
            status = "QUOTE_DRIFT"
            admissibility = "EVIDENCE_QUOTE_DRIFT_BLOCKED"
            review_mode = "QUOTE_DRIFT_SOURCE_REGION"
        elif index < 14:
            status = "EXACT_ORDERED_CROSS_PAGE_SPAN"
            admissibility = "V2_ORDERED_SPAN_REQUIRED"
            review_mode = "CROSS_PAGE"
        elif index == 14:
            status = "LAYOUT_NORMALIZED_EXACT_MATCH"
            admissibility = "V2_CONTEXT_REQUIRED"
            review_mode = "BOUNDED_CONTEXT"
        else:
            status = "LAYOUT_NORMALIZED_EXACT_MATCH"
            admissibility = "CURRENT_CONTRACT_ADMISSIBLE"
            review_mode = "EXCERPT_ONLY"
        quote_claims.append(
            {
                "claim_id": claim_id,
                "fidelity_status": status,
                "primary_drift_category": (
                    "transcript_cleanup" if status == "QUOTE_DRIFT" else None
                ),
                "nearest_deterministic_local_source_region": (
                    {"locator": "PAGE:1", "source_text": "source region"}
                    if status == "QUOTE_DRIFT"
                    else None
                ),
                "resolved_locator": (
                    {
                        "status": "resolved",
                        "kind": "ordered_spans",
                        "spans": [
                            {"order": 1, "locator": "PAGE:1", "text": "Evidence"}
                        ],
                    }
                    if status == "EXACT_ORDERED_CROSS_PAGE_SPAN"
                    else None
                ),
            }
        )
        annotations.append(
            {
                "claim_id": claim_id,
                "semantic_support": "SUPPORTED",
                "semantic_failure_category": "NONE",
                "atomicity_issue": False,
                "atomicity_material_failure": False,
                "evidence_admissibility": admissibility,
                "review_mode": review_mode,
                "quote_drift_semantically_material": False,
                "rationale": "Independent Source-local fixture review.",
            }
        )
    quote = {
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims": quote_claims,
    }
    annotation_document = {
        "document_type": ANNOTATIONS_DOCUMENT_TYPE,
        "schema_version": "1",
        "review_phase": "S3-A_BLIND_REVIEW",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "historical_comparison_inputs_accessed": False,
        "permitted_inputs": ["controlled run", "Source"],
        "claims": annotations,
    }
    paths = {
        "bundle": tmp_path / "bundle.json",
        "evidence": tmp_path / "evidence.json",
        "quote": tmp_path / "quote.json",
        "annotations": tmp_path / "annotations.json",
        "decisions": tmp_path / "decisions.json",
        "freeze": tmp_path / "freeze.json",
        "source": tmp_path / "source.pdf",
        "prompt": tmp_path / "prompt.py",
    }
    for name, value in (
        ("bundle", bundle),
        ("evidence", evidence),
        ("quote", quote),
        ("annotations", annotation_document),
    ):
        write_json(paths[name], value)
    paths["source"].write_bytes(b"source")
    paths["prompt"].write_text("prompt = 'frozen'\n", encoding="utf-8")
    return paths


def _build(paths):
    return build_blind_human_decisions(
        paths["bundle"],
        paths["evidence"],
        paths["quote"],
        paths["annotations"],
        paths["decisions"],
    )


def test_s3a_blind_review_covers_and_freezes_all_claims(tmp_path):
    paths = _fixture(tmp_path)
    decisions = _build(paths)
    receipt = freeze_blind_human_decisions(
        paths["decisions"],
        paths["freeze"],
        frozen_inputs={
            "source_pdf": paths["source"],
            "prompt_file": paths["prompt"],
            "extraction_bundle": paths["bundle"],
            "evidence_v2": paths["evidence"],
            "quote_fidelity": paths["quote"],
        },
    )

    assert decisions["claims_reviewed"] == 56
    assert decisions["pending"] == 0
    assert len(decisions["claims"]) == 56
    assert receipt["BLIND_REVIEW_COMPLETED_BEFORE_COMPARISON"] is True
    assert receipt["historical_comparison_inputs_accessed_before_freeze"] is False
    assert receipt["decisions"]["sha256"] == sha256_file(paths["decisions"])
    assert decisions["claims"][0]["semantic_support"] == "SUPPORTED"
    assert decisions["claims"][0]["human_decision"] == "KEEP_NEEDS_REVIEW"
    assert decisions["claims"][0]["quote_drift"] is True
    assert decisions["claims"][15]["human_decision"] == "KEEP"
    assert "old_decisions" not in inspect.signature(
        build_blind_human_decisions
    ).parameters
    assert "comparison" not in inspect.signature(
        build_blind_human_decisions
    ).parameters


def test_s3a_quote_drift_is_not_automatic_semantic_failure(tmp_path):
    paths = _fixture(tmp_path)
    annotations = json.loads(paths["annotations"].read_text(encoding="utf-8"))
    annotations["claims"][0].update(
        {
            "semantic_support": "UNSUPPORTED",
            "semantic_failure_category": "TECHNICAL_TERM_INFERENCE",
            "atomicity_issue": True,
            "atomicity_material_failure": True,
            "quote_drift_semantically_material": True,
        }
    )
    write_json(paths["annotations"], annotations)
    decisions = _build(paths)

    assert decisions["claims"][0]["human_decision"] == "DROP"
    assert decisions["claims"][1]["semantic_support"] == "SUPPORTED"
    assert decisions["claims"][1]["human_decision"] == "KEEP_NEEDS_REVIEW"


def test_s3a_rejects_incomplete_claim_coverage(tmp_path):
    paths = _fixture(tmp_path)
    annotations = json.loads(paths["annotations"].read_text(encoding="utf-8"))
    annotations["claims"] = copy.deepcopy(annotations["claims"][:-1])
    write_json(paths["annotations"], annotations)

    with pytest.raises(PilotError, match="BLIND_COVERAGE_INVALID"):
        _build(paths)


def test_s3a_rejects_historical_access_declaration(tmp_path):
    paths = _fixture(tmp_path)
    annotations = json.loads(paths["annotations"].read_text(encoding="utf-8"))
    annotations["historical_comparison_inputs_accessed"] = True
    write_json(paths["annotations"], annotations)

    with pytest.raises(PilotError, match="BLIND_BINDING_INVALID"):
        _build(paths)


def test_s3b_reconciles_old_linked_failures_new_failures_and_retention():
    old_decisions = {
        "claims": [
            {
                "claim_id": "OLD_FAIL",
                "semantic_support": "UNSUPPORTED",
                "semantic_failure_category": "TRUE_OVERREACH",
            },
            {
                "claim_id": "OLD_SUPPORTED",
                "semantic_support": "SUPPORTED",
                "semantic_failure_category": "NONE",
            },
        ]
    }
    new_decisions = {
        "claims": [
            {
                "claim_id": "NEW_LINKED_FAIL",
                "semantic_support": "UNSUPPORTED",
                "human_decision": "DROP",
                "semantic_failure_category": "TRUE_OVERREACH",
            },
            {
                "claim_id": "NEW_UNRELATED_FAIL",
                "semantic_support": "UNSUPPORTED",
                "human_decision": "DROP",
                "semantic_failure_category": "SCOPE_ERROR",
            },
            {
                "claim_id": "NEW_SUPPORTED",
                "semantic_support": "SUPPORTED",
                "human_decision": "KEEP",
                "semantic_failure_category": "NONE",
            },
        ]
    }
    comparison = {
        "old_failure_to_new_candidate_mapping": [
            {
                "old_claim_id": "OLD_FAIL",
                "candidate_new_claim_ids": ["NEW_LINKED_FAIL"],
            }
        ]
    }
    annotations = {
        "document_type": EVALUATION_ANNOTATIONS_DOCUMENT_TYPE,
        "schema_version": "1",
        "pilot_run_id": RUN_ID,
        "review_phase": "S3-B_POST_DECISION_COMPARISON",
        "old_failure_repair_outcomes": [
            {
                "old_claim_id": "OLD_FAIL",
                "related_new_claim_ids": ["NEW_LINKED_FAIL"],
                "repair_outcome": "PERSISTED_EQUIVALENT_FAILURE",
                "rationale": "Equivalent failure remains.",
            }
        ],
        "new_post_repair_failures": [
            {
                "claim_id": "NEW_UNRELATED_FAIL",
                "origin": "REPAIR_INDUCED",
                "rationale": "Separately identified new failure.",
            }
        ],
        "supported_information_retention": [
            {
                "old_claim_id": "OLD_SUPPORTED",
                "retention_category": "CLEARLY_RETAINED",
                "candidate_new_claim_ids": ["NEW_SUPPORTED"],
                "rationale": "Supported information remains.",
            }
        ],
    }

    outcomes, new_failures, retention = _validate_evaluation_annotations(
        annotations, old_decisions, new_decisions, comparison
    )
    assert len(outcomes) == 1
    assert [item["claim_id"] for item in new_failures] == ["NEW_UNRELATED_FAIL"]
    assert len(retention) == 1

    incomplete = copy.deepcopy(annotations)
    incomplete["new_post_repair_failures"] = []
    with pytest.raises(PilotError, match="NEW_FAILURE_RECONCILIATION_INVALID"):
        _validate_evaluation_annotations(
            incomplete, old_decisions, new_decisions, comparison
        )
