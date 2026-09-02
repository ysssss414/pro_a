from __future__ import annotations

import copy
import json

import pytest

from pro_a.corpus_pilot import PilotError
from pro_a.pilot3_human_review import (
    ANNOTATIONS_DOCUMENT_TYPE,
    RUN_ID,
    SOURCE_SHA256,
    build_pilot3_human_review_decisions,
    close_pilot3_human_review,
)
from pro_a.storage import sha256_file, write_json

from stability_helpers import make_config


def _fixture(tmp_path):
    cfg, _ = make_config(tmp_path)
    run_dir = tmp_path / "run"
    output_dir = tmp_path / "output"
    ids = [f"CLM_PILOT3_FIXTURE_{index:02d}" for index in range(70)]
    claims = [
        {
            "claim_id": claim_id,
            "statement": f"Claim {index}",
            "attributed_to": f"Speaker {index}",
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
                    {"direction": "after", "text": "context", "locators": ["PAGE:1"]}
                ],
            }
            for item in claims
        ],
    }
    gate_claims = []
    for index, claim_id in enumerate(ids):
        if index < 15:
            status = "QUOTE_DRIFT"
        elif index < 22:
            status = "EXACT_ORDERED_CROSS_PAGE_SPAN"
        else:
            status = "LAYOUT_NORMALIZED_EXACT_MATCH"
        gate_claims.append({
            "claim_id": claim_id,
            "fidelity_status": status,
            "primary_drift_category": "transcript_cleanup" if status == "QUOTE_DRIFT" else None,
            "nearest_deterministic_local_source_region": (
                {"locator": "PAGE:1", "source_text": "nearest"}
                if status == "QUOTE_DRIFT" else None
            ),
            "resolved_locator": (
                {"status": "resolved", "kind": "ordered_spans", "spans": [{"order": 1, "locator": "PAGE:1", "text": "evidence"}]}
                if status == "EXACT_ORDERED_CROSS_PAGE_SPAN" else None
            ),
        })
    fidelity_counts = {
        "EXACT_SOURCE_MATCH": 0,
        "LAYOUT_NORMALIZED_EXACT_MATCH": 48,
        "EXACT_ORDERED_CROSS_PAGE_SPAN": 7,
        "PROVENANCE_MISMATCH_RECOVERED": 0,
        "QUOTE_DRIFT": 15,
        "UNRESOLVED_SOURCE_BINDING": 0,
    }
    quote = {
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims": gate_claims,
    }
    annotations_claims = []
    for index, claim_id in enumerate(ids):
        if index < 15:
            admissibility = "EVIDENCE_QUOTE_DRIFT_BLOCKED"
            review_mode = "QUOTE_DRIFT_SOURCE_REGION"
        elif index < 22:
            admissibility = "V2_ORDERED_SPAN_REQUIRED"
            review_mode = "CROSS_PAGE"
        else:
            admissibility = "CURRENT_CONTRACT_ADMISSIBLE"
            review_mode = "EXCERPT_ONLY"
        annotations_claims.append({
            "claim_id": claim_id,
            "semantic_support": "SUPPORTED",
            "semantic_failure_category": "NONE",
            "atomicity_issue": False,
            "atomicity_material_failure": False,
            "evidence_admissibility": admissibility,
            "review_mode": review_mode,
            "quote_drift_semantically_material": False,
            "rationale": "Explicit fixture review.",
        })
    annotations_claims[22].update({
        "evidence_admissibility": "V2_CONTEXT_REQUIRED",
        "review_mode": "BOUNDED_CONTEXT",
    })
    annotations_claims[23].update({
        "semantic_support": "UNSUPPORTED",
        "semantic_failure_category": "TRUE_OVERREACH",
        "atomicity_issue": True,
        "atomicity_material_failure": True,
    })
    annotations_claims[24].update({
        "semantic_support": "AMBIGUOUS",
        "evidence_admissibility": "SOURCE_AMBIGUITY_BLOCKED",
        "review_mode": "BOUNDED_CONTEXT",
    })
    annotations = {
        "document_type": ANNOTATIONS_DOCUMENT_TYPE,
        "schema_version": "1",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "PILOT3_GENERALIZATION_VERDICT": "FAIL",
        "generalization_rationale": "Fixture semantic failure remains.",
        "PROMPT_REPAIR_NEXT": ["claim_atomicity"],
        "PHASE3C_NEXT_GATE": "Pilot #3 Semantic Failure Repair",
        "POST_REPAIR_INDEPENDENT_PILOT_REQUIRED": True,
        "claims": annotations_claims,
    }
    original_failed = {"status": "historical_failure"}
    paths = {
        "bundle": run_dir / "bundle.json",
        "evidence": run_dir / "evidence.json",
        "quote": run_dir / "quote.json",
        "pre_review": run_dir / "pre_review.json",
        "original_failed": run_dir / "original_failed.json",
        "annotations": run_dir / "annotations.json",
        "decisions": run_dir / "decisions.json",
    }
    for key, value in (
        ("bundle", bundle),
        ("evidence", evidence),
        ("quote", quote),
        ("annotations", annotations),
        ("original_failed", original_failed),
    ):
        write_json(paths[key], value)
    pre_review = {
        "pilot_run_id": RUN_ID,
        "evidence_fidelity": {"counts": fidelity_counts},
        "attribution_mechanical_qa": {"known_old_mutation_recurrence": "NO"},
        "artifacts": {
            "original_failure_artifact": {"sha256": sha256_file(paths["original_failed"])}
        },
    }
    write_json(paths["pre_review"], pre_review)
    return cfg, paths, output_dir


def _close(paths, output_dir, production_db):
    build_pilot3_human_review_decisions(
        paths["bundle"], paths["evidence"], paths["quote"],
        paths["annotations"], paths["decisions"],
    )
    return close_pilot3_human_review(
        paths["bundle"], paths["evidence"], paths["quote"], paths["pre_review"],
        paths["original_failed"], paths["decisions"], output_dir=output_dir,
        production_db_path=production_db,
    )


def test_pilot3_human_review_contract_metrics_and_isolation(tmp_path, monkeypatch):
    cfg, paths, output_dir = _fixture(tmp_path)
    production_pre = sha256_file(cfg.db_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("LLM, extraction, Production writer, IMA, propagation, or legacy pipeline invoked")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    result = _close(paths, output_dir, cfg.db_path)
    metrics = result["metrics"]
    decisions = json.loads(paths["decisions"].read_text(encoding="utf-8"))

    assert metrics["claims_reviewed"] == 70
    assert metrics["pending"] == 0
    assert metrics["decision_counts"] == {
        "KEEP": 45, "DROP": 1, "KEEP_NEEDS_REVIEW": 24, "PENDING": 0,
    }
    assert metrics["semantic_counts"] == {
        "SUPPORTED": 68, "UNSUPPORTED": 1, "AMBIGUOUS": 1,
    }
    assert metrics["quote_drift"]["semantic_outcomes"]["SUPPORTED"] == 15
    assert decisions["claims"][0]["human_decision"] == "KEEP_NEEDS_REVIEW"
    assert decisions["claims"][15]["human_decision"] == "KEEP_NEEDS_REVIEW"
    assert decisions["claims"][22]["human_decision"] == "KEEP_NEEDS_REVIEW"
    assert decisions["claims"][23]["human_decision"] == "DROP"
    assert metrics["llm_calls_added"] == 0
    assert metrics["pilot3_rerun"] is False
    assert metrics["production_write"] is False
    assert metrics["ima_invoked"] is False
    assert metrics["propagation_invoked"] is False
    assert metrics["legacy_pipeline_invoked"] is False
    assert all(metrics["invariants"].values())
    assert sha256_file(cfg.db_path) == production_pre


@pytest.mark.parametrize(
    "field",
    ["original_claim", "immutable_evidence_excerpt", "attributed_to", "gate_mechanical_fidelity_status"],
)
def test_pilot3_human_review_rejects_frozen_field_tampering(tmp_path, field):
    cfg, paths, output_dir = _fixture(tmp_path)
    decisions = build_pilot3_human_review_decisions(
        paths["bundle"], paths["evidence"], paths["quote"],
        paths["annotations"], paths["decisions"],
    )
    decisions["claims"][0][field] = "tampered"
    write_json(paths["decisions"], decisions)
    with pytest.raises(PilotError, match="FROZEN_FIELD_CHANGED"):
        close_pilot3_human_review(
            paths["bundle"], paths["evidence"], paths["quote"], paths["pre_review"],
            paths["original_failed"], paths["decisions"], output_dir=output_dir,
            production_db_path=cfg.db_path,
        )


def test_pilot3_quote_drift_is_not_automatic_semantic_failure(tmp_path):
    _, paths, _ = _fixture(tmp_path)
    decisions = build_pilot3_human_review_decisions(
        paths["bundle"], paths["evidence"], paths["quote"],
        paths["annotations"], paths["decisions"],
    )
    drift = decisions["claims"][0]
    assert drift["gate_mechanical_fidelity_status"] == "QUOTE_DRIFT"
    assert drift["semantic_support"] == "SUPPORTED"
    assert drift["evidence_admissibility"] == "EVIDENCE_QUOTE_DRIFT_BLOCKED"
    assert drift["human_decision"] == "KEEP_NEEDS_REVIEW"


def test_pilot3_human_review_rejects_missing_decision(tmp_path):
    _, paths, _ = _fixture(tmp_path)
    annotations = json.loads(paths["annotations"].read_text(encoding="utf-8"))
    annotations["claims"] = copy.deepcopy(annotations["claims"][:-1])
    write_json(paths["annotations"], annotations)
    with pytest.raises(PilotError, match="ANNOTATION_COVERAGE_INVALID"):
        build_pilot3_human_review_decisions(
            paths["bundle"], paths["evidence"], paths["quote"],
            paths["annotations"], paths["decisions"],
        )
