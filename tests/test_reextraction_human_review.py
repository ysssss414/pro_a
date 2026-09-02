from __future__ import annotations

import copy
import json

import pytest

from pro_a.corpus_pilot import PilotError
from pro_a.reextraction_human_review import (
    ANNOTATIONS_DOCUMENT_TYPE,
    HISTORICAL_RUN_ID,
    RUN_ID,
    SOURCE_SHA256,
    build_reextraction_human_review_decisions,
    close_reextraction_human_review,
)
from pro_a.storage import sha256_file, write_json

from stability_helpers import make_config


def _fixture(tmp_path):
    cfg, _ = make_config(tmp_path)
    run_dir = tmp_path / "run"
    historical_dir = tmp_path / "historical"
    output_dir = tmp_path / "output"
    ids = [f"CLM_FIXTURE_{index:02d}" for index in range(51)]
    claims = [
        {
            "claim_id": claim_id,
            "statement": f"Claim {index}",
            "evidence_excerpt": f"Evidence {index}",
        }
        for index, claim_id in enumerate(ids)
    ]
    bundle = {
        "pilot_run_id": RUN_ID,
        "source": {"sha256": SOURCE_SHA256},
        "model": {"usage": {"total_tokens": 5100}},
        "claims": claims,
    }
    evidence = {
        "pilot_run_id": RUN_ID,
        "claims": [
            {
                "claim_id": item["claim_id"],
                "original_evidence_excerpt": item["evidence_excerpt"],
            }
            for item in claims
        ],
    }
    statuses = {
        ids[1]: "QUOTE_DRIFT",
        ids[2]: "PROVENANCE_MISMATCH_RECOVERED",
        ids[4]: "EXACT_ORDERED_CROSS_PAGE_SPAN",
    }
    gate_claims = []
    for claim_id in ids:
        status = statuses.get(claim_id, "LAYOUT_NORMALIZED_EXACT_MATCH")
        gate_claims.append({
            "claim_id": claim_id,
            "fidelity_status": status,
            "primary_drift_category": "transcript_cleanup" if status == "QUOTE_DRIFT" else None,
            "nearest_deterministic_local_source_region": (
                {"locator": "PAGE:1", "text": "nearest"}
                if status == "QUOTE_DRIFT" else None
            ),
        })
    fidelity_counts = {
        "EXACT_ORDERED_CROSS_PAGE_SPAN": 1,
        "EXACT_SOURCE_MATCH": 0,
        "LAYOUT_NORMALIZED_EXACT_MATCH": 48,
        "PROVENANCE_MISMATCH_RECOVERED": 1,
        "QUOTE_DRIFT": 1,
        "UNRESOLVED_SOURCE_BINDING": 0,
    }
    quote = {
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims": gate_claims,
        "metrics": {"fidelity_counts": fidelity_counts},
    }
    reextraction_metrics = {
        "pilot_run_id": RUN_ID,
        "mechanical_diagnostics": {
            "deterministic_company_to_speaker_mutations": {"count": 0}
        },
    }
    annotations_claims = []
    for claim_id in ids:
        item = {
            "claim_id": claim_id,
            "semantic_support": "SUPPORTED",
            "evidence_admissibility": "CURRENT_CONTRACT_ADMISSIBLE",
            "semantic_failure_category": "NONE",
            "atomicity_issue": False,
            "atomicity_material_failure": False,
            "review_mode": "EXCERPT_ONLY",
            "claim_count_diagnostic": "OTHER",
            "rationale": "Fixture human review.",
        }
        annotations_claims.append(item)
    annotations_claims[1].update({
        "evidence_admissibility": "EVIDENCE_QUOTE_DRIFT_BLOCKED",
        "review_mode": "QUOTE_DRIFT_SOURCE_REGION",
        "quote_drift_semantically_material": False,
    })
    annotations_claims[2]["review_mode"] = "PROVENANCE_RECOVERY_REVIEW"
    annotations_claims[3].update({
        "semantic_support": "UNSUPPORTED",
        "semantic_failure_category": "ATTRIBUTION_ERROR",
        "attribution_failure_origin": "MODEL_OUTPUT",
        "atomicity_issue": True,
        "atomicity_material_failure": True,
    })
    annotations_claims[4].update({
        "evidence_admissibility": "V2_ORDERED_SPAN_REQUIRED",
        "review_mode": "CROSS_PAGE",
    })
    annotations_claims[5].update({
        "evidence_admissibility": "V2_CONTEXT_REQUIRED",
        "review_mode": "BOUNDED_CONTEXT",
    })
    annotations = {
        "document_type": ANNOTATIONS_DOCUMENT_TYPE,
        "schema_version": "1",
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "repair_efficacy_verdict": "PASS_WITH_REMAINING_REPAIR",
        "repair_efficacy_rationale": "Fixture has one remaining semantic defect.",
        "independent_generalization_retest": "NOT_YET_PERFORMED",
        "claim_count_diagnostic_rationale": "Fixture diagnostic.",
        "coverage_diagnostic": {
            "historical_supported_concepts_retained": 1,
            "historical_supported_concepts_lost": 0,
            "useful_new_propositions": 0,
            "precision_or_recall_claim": "NOT_MADE",
        },
        "claims": annotations_claims,
    }
    historical_metrics = {
        "true_semantic_failure_rate": {
            "numerator": 10, "denominator": 29, "fraction": "10/29", "percent": 34.48,
        },
        "atomicity": {
            "issue_rate": {
                "numerator": 13, "denominator": 29, "fraction": "13/29", "percent": 44.83,
            },
            "material_failure_rate": {
                "numerator": 7, "denominator": 29, "fraction": "7/29", "percent": 24.14,
            },
        },
        "token_economics": {
            "pilot2_extraction_total_tokens": 39782,
            "tokens_per_claim": 1371.79,
        },
        "human_review_burden": {"expanded_manual_evidence_review": 19},
    }
    paths = {
        "bundle": run_dir / "bundle.json",
        "evidence": run_dir / "evidence.json",
        "quote": run_dir / "quote.json",
        "reextraction_metrics": run_dir / "reextraction_metrics.json",
        "annotations": run_dir / "annotations.json",
        "decisions": run_dir / "decisions.json",
    }
    for key, value in (
        ("bundle", bundle),
        ("evidence", evidence),
        ("quote", quote),
        ("reextraction_metrics", reextraction_metrics),
        ("annotations", annotations),
    ):
        write_json(paths[key], value)
    write_json(historical_dir / "pilot2_human_review_metrics.json", historical_metrics)
    (historical_dir / "sentinel.txt").write_text("immutable", encoding="utf-8")
    return cfg, paths, historical_dir, output_dir


def _close(paths, historical_dir, output_dir, production_db):
    build_reextraction_human_review_decisions(
        paths["bundle"], paths["quote"], paths["annotations"], paths["decisions"],
    )
    return close_reextraction_human_review(
        paths["bundle"],
        paths["evidence"],
        paths["quote"],
        paths["reextraction_metrics"],
        paths["decisions"],
        historical_dir,
        output_dir=output_dir,
        production_db_path=production_db,
    )


def test_reextraction_human_review_contract_metrics_and_isolation(tmp_path, monkeypatch):
    cfg, paths, historical_dir, output_dir = _fixture(tmp_path)
    production_pre = sha256_file(cfg.db_path)
    historical_pre = {
        item.name: sha256_file(item) for item in historical_dir.iterdir() if item.is_file()
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("LLM, Production writer, IMA, propagation, or legacy pipeline invoked")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    result = _close(paths, historical_dir, output_dir, cfg.db_path)
    metrics = result["metrics"]
    ready = result["ready"]

    assert metrics["claims_reviewed"] == 51
    assert metrics["decision_counts"]["PENDING"] == 0
    assert metrics["decision_counts"] == {
        "KEEP": 47, "DROP": 1, "KEEP_NEEDS_REVIEW": 3, "PENDING": 0,
    }
    assert ready["claims"][1]["semantic_support"] == "SUPPORTED"
    assert ready["claims"][1]["evidence_admissibility"] == "EVIDENCE_QUOTE_DRIFT_BLOCKED"
    assert metrics["quote_fidelity"]["quote_drift_semantic_outcomes"]["SUPPORTED"] == 1
    assert metrics["provenance_recovery"]["semantic_outcomes"]["SUPPORTED"] == 1
    assert metrics["attribution"]["model_output"] == 1
    assert metrics["attribution"]["known_company_to_speaker_mutation_recurrence"] == "NO"
    assert metrics["atomicity"]["issues"] == 1
    assert metrics["atomicity"]["material_failures"] == 1
    assert metrics["llm_calls_added"] == 0
    assert metrics["production_write"] is False
    assert metrics["ima_invoked"] is False
    assert metrics["propagation_invoked"] is False
    assert metrics["legacy_pipeline_invoked"] is False
    assert all(value is True for value in metrics["invariants"].values())
    assert sha256_file(cfg.db_path) == production_pre
    assert historical_pre == {
        item.name: sha256_file(item) for item in historical_dir.iterdir() if item.is_file()
    }
    bundle = json.loads(paths["bundle"].read_text(encoding="utf-8"))
    assert [item["original_claim"] for item in ready["claims"]] == [
        item["statement"] for item in bundle["claims"]
    ]
    assert [item["immutable_evidence_excerpt"] for item in ready["claims"]] == [
        item["evidence_excerpt"] for item in bundle["claims"]
    ]


def test_reextraction_human_review_detects_deterministic_attribution_recurrence(tmp_path):
    cfg, paths, historical_dir, output_dir = _fixture(tmp_path)
    metrics = json.loads(paths["reextraction_metrics"].read_text(encoding="utf-8"))
    metrics["mechanical_diagnostics"]["deterministic_company_to_speaker_mutations"]["count"] = 1
    write_json(paths["reextraction_metrics"], metrics)
    with pytest.raises(PilotError, match="ATTRIBUTION_RECURRENCE_REQUIRES_FAIL"):
        _close(paths, historical_dir, output_dir, cfg.db_path)


@pytest.mark.parametrize("field", ["original_claim", "immutable_evidence_excerpt"])
def test_reextraction_human_review_rejects_claim_or_evidence_tampering(tmp_path, field):
    cfg, paths, historical_dir, output_dir = _fixture(tmp_path)
    decisions = build_reextraction_human_review_decisions(
        paths["bundle"], paths["quote"], paths["annotations"], paths["decisions"],
    )
    decisions["claims"][0][field] = "tampered"
    write_json(paths["decisions"], decisions)
    with pytest.raises(PilotError, match="_(CLAIM|EVIDENCE)_CHANGED"):
        close_reextraction_human_review(
            paths["bundle"], paths["evidence"], paths["quote"],
            paths["reextraction_metrics"], paths["decisions"], historical_dir,
            output_dir=output_dir, production_db_path=cfg.db_path,
        )
