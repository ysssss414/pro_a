from __future__ import annotations

import json
from pathlib import Path

import pytest

from multiformat_helpers import write_pdf
from pro_a import pilot3_controlled_reextraction as s2
from pro_a.corpus_pilot import PilotError, production_snapshot
from pro_a.storage import sha256_file, write_json

from stability_helpers import make_config


def _prepare_frozen_fixture(tmp_path: Path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    cfg.llm.enabled = True
    monkeypatch.setenv(cfg.llm.api_key_env, "fixture-key")
    source = tmp_path / "controlled.pdf"
    write_pdf(source, ["[[PAGE:1]] Fixture source statement."])
    source_sha = sha256_file(source)
    monkeypatch.setattr(s2, "ORIGINAL_SOURCE_SHA256", source_sha)
    monkeypatch.setattr(s2, "PRODUCTION_BASELINE_SHA256", sha256_file(cfg.db_path))

    parsed = s2.parse_source_with_diagnostics(source)
    original_dir = cfg.root / "phase3c" / s2.ORIGINAL_RUN_ID
    repair_dir = cfg.root / "phase3c" / "pilot3_semantic_failure_repair"
    repair_dir.mkdir(parents=True, exist_ok=True)
    old_claim = {
        "claim_id": "CLM_OLD",
        "statement": "Fixture source statement.",
        "evidence_pointer": "[[PAGE:1]]",
        "evidence_excerpt": "Fixture source statement.",
        "attributed_to": "Fixture speaker",
    }
    old_bundle = {
        "document_type": "phase3c_extraction_bundle",
        "pilot_run_id": s2.ORIGINAL_RUN_ID,
        "source": {"sha256": source_sha},
        "claims": [old_claim],
        "model": {"usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
    }
    decisions = {
        "PILOT3_GENERALIZATION_VERDICT": "FAIL",
        "claims": [{
            "claim_id": "CLM_OLD",
            "original_claim": old_claim["statement"],
            "immutable_evidence_excerpt": old_claim["evidence_excerpt"],
            "semantic_support": "UNSUPPORTED",
            "semantic_failure_category": "TRUE_OVERREACH",
        }],
    }
    write_json(original_dir / "extraction_bundle.json", old_bundle)
    write_json(
        original_dir / "evidence_v2_repair" / "evidence_contract_v2_repaired.json",
        {"status": "fixture"},
    )
    write_json(original_dir / "pilot3_human_review_decisions.json", decisions)
    (original_dir / "pilot3_human_review_report.md").write_text("fixture", encoding="utf-8")
    (repair_dir / "pilot3_semantic_failure_repair_report.md").write_text("fixture", encoding="utf-8")
    (repair_dir / "pilot3_semantic_prompt_diff.md").write_text("fixture", encoding="utf-8")
    write_json(original_dir / "pilot3_extraction_freeze.json", {
        "source": {"sha256": source_sha, "parse_diagnostics": parsed.diagnostics},
        "freeze": {"extraction_configuration": s2._runtime_settings(cfg)},
    })
    paths = s2._original_artifact_paths(cfg.root)
    monkeypatch.setattr(
        s2, "_EXPECTED_ORIGINAL_HASHES",
        {name: sha256_file(paths[name]) for name in (
            "original_extraction_bundle",
            "original_repaired_evidence_v2",
            "original_human_review_decisions",
        )},
    )
    return cfg, source, old_bundle


def test_s2_preflight_freezes_source_prompt_runtime_and_original_verdict(tmp_path, monkeypatch):
    cfg, source, _ = _prepare_frozen_fixture(tmp_path, monkeypatch)

    result = s2.controlled_reextraction_preflight(
        source, cfg, "PILOT_20260901_A1B2C3D4",
    )

    assert result["status"] == "PASS"
    assert result["pilot_run_id"] != s2.ORIGINAL_RUN_ID
    assert result["source"]["sha256"] == sha256_file(source)
    assert result["prompt"]["prompt_sha256"] == s2.REPAIRED_PROMPT_SHA256
    assert result["prompt"]["old_prompt_sha256_not_used"] == s2.ORIGINAL_PROMPT_SHA256
    assert all(result["prompt"]["contract_checks"].values())
    assert result["runtime_semantic_settings_changed"] is False
    assert result["original_generalization_verdict"] == "FAIL"
    assert result["quality_rerun_allowed"] is False


def test_s2_preflight_rejects_original_run_id_before_extraction(tmp_path, monkeypatch):
    cfg, source, _ = _prepare_frozen_fixture(tmp_path, monkeypatch)

    with pytest.raises(PilotError, match="RUN_ID_INVALID"):
        s2.controlled_reextraction_preflight(source, cfg, s2.ORIGINAL_RUN_ID)


def test_structural_comparison_is_diagnostic_and_allows_no_new_candidate():
    old = {
        "pilot_run_id": s2.ORIGINAL_RUN_ID,
        "claims": [{
            "claim_id": "OLD",
            "statement": "Alpha is supported, beta is not.",
            "evidence_pointer": "[[PAGE:1]]",
            "evidence_excerpt": "Alpha is supported.",
            "attributed_to": "Speaker A",
        }],
        "model": {"usage": {"total_tokens": 100}},
    }
    decisions = {"claims": [{
        "claim_id": "OLD", "semantic_support": "UNSUPPORTED",
        "semantic_failure_category": "TRUE_OVERREACH",
    }]}
    new = {
        "pilot_run_id": "PILOT_20260901_A1B2C3D4",
        "claims": [],
        "model": {"usage": {"total_tokens": 20}, "llm_calls": 1},
    }
    mechanical = {
        "quote_fidelity": {"percent": 100.0},
        "quote_drift": {"percent": 0.0},
        "source_binding": {"percent": 100.0},
    }

    result = s2.build_structural_comparison(old, new, decisions, mechanical)

    mapping = result["old_failure_to_new_candidate_mapping"][0]
    assert mapping["candidate_new_claim_ids"] == []
    assert mapping["no_new_candidate"] is True
    assert mapping["semantic_verdict"] == "PENDING_HUMAN_REVIEW"
    assert result["interpretation_limits"]["missing_old_failure_is_not_automatically_fixed"] is True
    assert result["atomicity_structural_diagnostics"]["old"]["human_atomicity_metric"] is False


def test_controlled_run_calls_extraction_once_and_finalizes_without_human_review(
    tmp_path, monkeypatch,
):
    cfg, source, _ = _prepare_frozen_fixture(tmp_path, monkeypatch)
    run_id = "PILOT_20260901_DEADBEEF"
    calls = {"extraction": 0}

    def fake_extract(_source, _cfg, *, output_dir, production_db_path, required_prompt_sha256, run_id):
        calls["extraction"] += 1
        claim = {
            "claim_id": "CLM_NEW",
            "statement": "Fixture source statement.",
            "evidence_pointer": "[[PAGE:1]]",
            "evidence_excerpt": "Fixture source statement.",
            "attributed_to": "Fixture speaker",
        }
        bundle = {
            "document_type": "phase3c_extraction_bundle",
            "pilot_run_id": run_id,
            "source": {"sha256": sha256_file(source)},
            "claims": [claim],
            "model": {
                "configured_model": "deepseek-chat",
                "response_model": "deepseek-chat",
                "prompt": {"prompt_sha256": s2.REPAIRED_PROMPT_SHA256},
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                "llm_calls": 1,
            },
        }
        review = {"claims": [{"claim_id": "CLM_NEW", "decision": "PENDING"}]}
        bundle_path = Path(output_dir) / "extraction_bundle.json"
        review_path = Path(output_dir) / "extraction_review_draft.json"
        write_json(bundle_path, bundle)
        write_json(review_path, review)
        return {
            "bundle": bundle,
            "review": review,
            "extraction_bundle_path": str(bundle_path),
            "review_draft_path": str(review_path),
        }

    def fake_rebind(bundle_path, _source, *, output_dir, production_db_path):
        rebound = Path(output_dir) / "extraction_bundle_stage1_1_rebound.json"
        review = Path(output_dir) / "extraction_review_stage1_1_draft.json"
        rebound.write_bytes(Path(bundle_path).read_bytes())
        write_json(review, {"claims": [{"claim_id": "CLM_NEW", "decision": "PENDING"}]})
        return {"rebound_bundle_path": str(rebound), "review_draft_path": str(review)}

    evidence_claim = {
        "claim_id": "CLM_NEW",
        "statement": "Fixture source statement.",
        "attributed_to": "Fixture speaker",
        "original_evidence_excerpt": "Fixture source statement.",
        "bounded_context_candidates": [],
        "evidence_spans": [],
        "formal_confidence": 0.8,
        "model_confidence": 0.8,
        "human_decision": "PENDING",
    }

    def fake_evidence(_bundle, _review, _source, *, output_dir, production_db_path):
        draft = {"pilot_run_id": run_id, "source_sha256": sha256_file(source), "claims": [evidence_claim]}
        path = Path(output_dir) / "evidence_contract_v2_draft.json"
        write_json(path, draft)
        return {
            "draft": draft,
            "draft_path": str(path),
            "metrics": {
                "evidence_deterministically_bound": 1,
                "single_page_locator_bound": 1,
                "cross_page_exact_spans": 0,
                "locator_ambiguous": 0,
                "locator_unresolved": 0,
                "bounded_context_candidate_claims": 0,
            },
        }

    def fake_gate(*_args, **_kwargs):
        counts = {name: 0 for name in s2.PILOT2_GATE_A_FIDELITY_STATUSES}
        counts["EXACT_SOURCE_MATCH"] = 1
        return {
            "pilot_run_id": run_id,
            "source_sha256": sha256_file(source),
            "claims": [{
                "claim_id": "CLM_NEW",
                "fidelity_status": "EXACT_SOURCE_MATCH",
                "evidence_contract": {
                    "resolved_locator": {"locator": "PAGE:1", "authoritative": True},
                    "model_page_pointer": {"value": "[[PAGE:1]]", "status": "matched"},
                },
            }],
            "metrics": {"fidelity_counts": counts},
        }

    monkeypatch.setattr(s2, "extract_pilot_source", fake_extract)
    monkeypatch.setattr(s2, "rebind_stage1_evidence_locators", fake_rebind)
    monkeypatch.setattr(s2, "build_pilot2_evidence_support_draft", fake_evidence)
    monkeypatch.setattr(s2, "run_pilot2_gate_a_quote_fidelity", fake_gate)

    result = s2.run_controlled_reextraction(source, cfg, run_id=run_id)

    assert result["status"] == "AWAITING_REGRESSION_VALIDATION"
    assert calls["extraction"] == 1
    metrics = result["metrics"]
    assert metrics["one_logical_extraction"] is True
    assert metrics["quality_rerun"] is False
    assert metrics["human_decisions_pending"] == metrics["claims_total"] == 1
    assert metrics["human_semantic_review_executed"] is False
    assert set(metrics["semantic_metrics"].values()) == {"PENDING_HUMAN_REVIEW"}
    assert metrics["original_artifacts_unchanged"] is True
    assert metrics["production"]["unchanged"] is True
    assert metrics["PILOT3_GENERALIZATION_VERDICT"] == "FAIL"
    assert Path(metrics["artifacts"]["evidence_contract_v2"]).is_file()
    assert Path(metrics["artifacts"]["evidence_review_surface"]).read_text(
        encoding="utf-8",
    ).count("Human decision: `PENDING`") == 1

    receipt_path = cfg.root / "phase3c" / "pilot3_semantic_failure_repair" / (
        "pilot3_controlled_reextraction_regression_receipt.json"
    )
    write_json(receipt_path, {
        "document_type": s2.REGRESSION_DOCUMENT_TYPE,
        "pilot_run_id": run_id,
        "results": {name: {"status": "PASS", "detail": "fixture"} for name in s2.REQUIRED_REGRESSIONS},
    })
    finalized = s2.finalize_controlled_reextraction(
        Path(result["run_dir"]), receipt_path, cfg,
    )

    assert finalized["metrics"]["PHASE3C_PILOT3_CONTROLLED_REEXTRACTION_COMPLETE"] is True
    assert finalized["metrics"]["PHASE3C_NEXT_GATE"] == (
        "Pilot #3 Controlled Re-extraction Independent Human Review"
    )
    assert finalized["metrics"]["POST_REPAIR_INDEPENDENT_PILOT_REQUIRED"] is True
    assert production_snapshot(cfg.db_path)["sha256"] == sha256_file(cfg.db_path)
