from __future__ import annotations

import json

import pytest

from pro_a.corpus_pilot import (
    PilotError,
    _claim_bundle_record,
    _controlled_reextraction_mechanical_diagnostics,
    _ordered_cross_page_spans,
    phase3c_evidence_provenance_contract,
    phase3c_gate_a_monitoring_metrics,
    phase3c_prompt_repair_status,
    resolve_pdf_evidence_locator,
)
from pro_a.gate_c_quality_hardening import (
    RESIDUAL_ROOT_CAUSES,
    RUN_ID,
    SOURCE_SHA256,
    audit_pilot2_gate_c_quality_hardening,
)
from pro_a.parsers import source_units
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from pro_a.storage import sha256_file, write_json

from stability_helpers import make_config


def test_gate_c_semantic_guardrails_are_explicit_and_attribution_is_preserved():
    status = phase3c_prompt_repair_status()

    assert status["passed"] is True
    assert all(status["categories"][name] for name in (
        "conditionality_preservation",
        "entity_inference_prevention",
        "technical_term_inference_prevention",
        "scope_invention_prevention",
        "gate_c_atomicity_clarification",
        "attribution_preservation",
    ))
    assert "删除或移动限定词" in SOURCE_ANALYSIS_SYSTEM
    assert "文件名/标题" in SOURCE_ANALYSIS_SYSTEM
    assert "不依赖该推断术语的保守 Claim" in SOURCE_ANALYSIS_SYSTEM
    assert "单一公司扩大为行业" in SOURCE_ANALYSIS_SYSTEM
    assert "不得为增加 Claim 数量" in SOURCE_ANALYSIS_SYSTEM
    assert "CLM_20260831_" not in SOURCE_ANALYSIS_SYSTEM
    assert "TGV" not in SOURCE_ANALYSIS_SYSTEM
    assert "Glass Bridge" not in SOURCE_ANALYSIS_SYSTEM


def test_gate_c_future_bundle_claim_separates_model_evidence_and_authoritative_locator():
    full_text = "[[PAGE:1]]\n可能会完成交付。"
    claim = {
        "statement": "可能会完成交付。",
        "nature": "expert_judgment",
        "evidence_pointer": "[[PAGE:1]]",
        "evidence_excerpt": "可能会完成交付。",
        "attributed_to": "研究员",
        "status": "current",
        "confidence": 0.8,
        "evidence_validated": True,
        "validation": {"evidence_validated": True, "errors": []},
        "structured": {},
    }

    record = _claim_bundle_record("CLM_FIXTURE", "SRC_FIXTURE", claim, "", full_text)
    evidence = record["phase3c_evidence"]

    assert evidence["model_evidence_excerpt"] == claim["evidence_excerpt"]
    assert evidence["model_evidence_is_proposed_quote"] is True
    assert evidence["validated_source_evidence"] == claim["evidence_excerpt"]
    assert evidence["model_page_pointer"] == {
        "value": "[[PAGE:1]]", "status": "matched", "authoritative": False,
    }
    assert evidence["resolved_locator"]["locator"] == "PAGE:1"
    assert evidence["resolved_locator"]["authoritative"] is True
    assert evidence["automatic_quote_repair_applied"] is False


def test_gate_c_evidence_provenance_is_fail_closed_and_pointer_error_is_separate():
    full_text = "[[PAGE:1]]\n其他文本。\n[[PAGE:2]]\n唯一精确引文。"
    wrong = resolve_pdf_evidence_locator(full_text, "唯一精确引文。", "[[PAGE:1]]")
    recovered = phase3c_evidence_provenance_contract(
        model_evidence_excerpt="唯一精确引文。",
        evidence_pointer="[[PAGE:1]]",
        deterministic_locator=wrong,
        fidelity_status="PROVENANCE_MISMATCH_RECOVERED",
    )
    drift_locator = resolve_pdf_evidence_locator(full_text, "唯一清理引文。", "[[PAGE:2]]")
    drift = phase3c_evidence_provenance_contract(
        model_evidence_excerpt="唯一清理引文。",
        evidence_pointer="[[PAGE:2]]",
        deterministic_locator=drift_locator,
        fidelity_status="QUOTE_DRIFT",
    )

    assert wrong["locator"] == "PAGE:2"
    assert recovered["model_page_pointer"]["status"] == "mismatch"
    assert recovered["model_page_pointer_error"] == "MODEL_PAGE_POINTER_ERROR"
    assert recovered["pointer_mismatch_is_semantic_failure"] is False
    assert recovered["resolved_locator"]["locator"] == "PAGE:2"
    assert drift["validated_source_evidence"] is None
    assert drift["canonical_ready_evidence"] is None
    assert drift["review_required"] is True
    assert drift["automatic_quote_repair_applied"] is False


def test_gate_c_ordered_adjacent_page_quote_is_validated_without_fake_page_locator():
    full_text = "[[PAGE:1]]\n引子。跨页前半\n[[PAGE:2]]\n跨页后半。结尾。"
    excerpt = "跨页前半跨页后半。"
    locator = resolve_pdf_evidence_locator(full_text, excerpt, "[[PAGE:1]]")
    pages = dict(source_units(full_text))
    spans = _ordered_cross_page_spans(pages, locator, excerpt)
    contract = phase3c_evidence_provenance_contract(
        model_evidence_excerpt=excerpt,
        evidence_pointer="[[PAGE:1]]",
        deterministic_locator=locator,
        fidelity_status="EXACT_ORDERED_CROSS_PAGE_SPAN",
        ordered_spans=spans,
    )

    assert locator["status"] == "unresolved"
    assert locator["reason"] == "cross_page_span"
    assert [item["locator"] for item in spans] == ["PAGE:1", "PAGE:2"]
    assert contract["validated_source_evidence"] == excerpt
    assert contract["resolved_locator"]["kind"] == "ordered_spans"
    assert "locator" not in contract["resolved_locator"]


def test_gate_c_monitoring_metrics_use_claim_grain_and_separate_semantics():
    claims = [
        {
            "fidelity_status": "EXACT_SOURCE_MATCH",
            "model_page_pointer": {"status": "matched"},
            "resolved_locator": {"status": "resolved"},
        },
        {
            "fidelity_status": "PROVENANCE_MISMATCH_RECOVERED",
            "model_page_pointer": {"status": "mismatch"},
            "resolved_locator": {"status": "resolved"},
        },
        {
            "fidelity_status": "EXACT_ORDERED_CROSS_PAGE_SPAN",
            "model_page_pointer": {"status": "unsupported"},
            "resolved_locator": {"status": "resolved", "kind": "ordered_spans"},
        },
        {
            "fidelity_status": "QUOTE_DRIFT",
            "model_page_pointer": {"status": "unsupported"},
            "resolved_locator": None,
        },
    ]

    metrics = phase3c_gate_a_monitoring_metrics(claims)

    assert metrics["grain"] == "one_phase3c_claim"
    assert metrics["evidence_quote_fidelity_rate"]["fraction"] == "3/4"
    assert metrics["evidence_quote_drift_rate"]["fraction"] == "1/4"
    assert metrics["model_page_pointer_accuracy"]["fraction"] == "1/3"
    assert metrics["deterministic_locator_recovery_rate"]["fraction"] == "1/1"
    assert metrics["semantic_support_rate_included"] is False
    assert metrics["composite_quality_score"] == "NOT_DEFINED"


def test_gate_c_conditionality_diagnostic_covers_full_guardrail_marker_set():
    bundle = {
        "claims": [{
            "claim_id": "CLM_FIXTURE",
            "statement": "若条件成立，结果 likely 改善。",
            "evidence_excerpt": "条件成立，结果改善。",
            "structured": {},
        }],
    }
    result = _controlled_reextraction_mechanical_diagnostics(
        bundle, {"claims": []}, {"claims": []},
    )

    assert result["conditionality_qa_flags"]["count"] == 1
    assert result["conditionality_qa_flags"]["claims"][0]["statement_markers"] == [
        "likely", "若",
    ]


def _gate_c_fixture(tmp_path):
    cfg, _ = make_config(tmp_path)
    run_dir = tmp_path / "run"
    decisions = {
        "pilot_run_id": RUN_ID,
        "source_sha256": SOURCE_SHA256,
        "claims": [
            {
                "claim_id": claim_id,
                "semantic_support": "UNSUPPORTED",
                "semantic_failure_category": values["primary_failure"],
            }
            for claim_id, values in RESIDUAL_ROOT_CAUSES.items()
        ],
    }
    review_metrics = {
        "pilot_run_id": RUN_ID,
        "true_semantic_failure_rate": {"percent": 11.76},
        "atomicity": {"material_failure_rate": {"percent": 7.84}},
        "attribution": {"any_dimension": 0},
    }
    statuses = (
        ["EXACT_SOURCE_MATCH"]
        + ["LAYOUT_NORMALIZED_EXACT_MATCH"] * 34
        + ["EXACT_ORDERED_CROSS_PAGE_SPAN"] * 2
        + ["PROVENANCE_MISMATCH_RECOVERED"] * 8
        + ["QUOTE_DRIFT"] * 6
    )
    quote = {
        "pilot_run_id": RUN_ID,
        "claims": [
            {
                "claim_id": f"CLM_GATE_{index:02d}",
                "fidelity_status": status,
                "provenance_pointer": "[[PAGE:1]]",
            }
            for index, status in enumerate(statuses)
        ],
    }
    bundle = {
        "pilot_run_id": RUN_ID,
        "source": {"sha256": SOURCE_SHA256},
        "claims": [],
    }
    write_json(run_dir / "reextraction_human_review_decisions.json", decisions)
    write_json(run_dir / "reextraction_human_review_metrics.json", review_metrics)
    write_json(run_dir / "reextraction_quote_fidelity.json", quote)
    write_json(run_dir / "extraction_bundle.json", bundle)
    (run_dir / "prior_sentinel.txt").write_text("immutable", encoding="utf-8")
    return cfg, run_dir


def test_gate_c_audit_generates_only_new_artifacts_and_preserves_inputs(tmp_path, monkeypatch):
    cfg, run_dir = _gate_c_fixture(tmp_path)
    production_pre = sha256_file(cfg.db_path)
    prior_pre = {
        item.name: sha256_file(item) for item in run_dir.iterdir() if item.is_file()
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("LLM, Production writer, IMA, propagation, or legacy pipeline invoked")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    result = audit_pilot2_gate_c_quality_hardening(run_dir, cfg.db_path)
    metrics = result["metrics"]

    assert result["status"] == "PASS"
    assert metrics["PHASE3C_PILOT2_GATE_C_COMPLETE"] is True
    assert all(metrics["acceptance_checks"].values())
    assert metrics["monitoring_metrics"]["evidence_quote_fidelity_rate"]["fraction"] == "45/51"
    assert metrics["monitoring_metrics"]["model_page_pointer_accuracy"]["fraction"] == "35/45"
    assert metrics["monitoring_metrics"]["deterministic_locator_recovery_rate"]["fraction"] == "8/8"
    assert metrics["PHASE3C_NEXT_GATE"] == "Independent Generalization Pilot Authorization"
    assert metrics["llm_calls_added"] == 0
    assert metrics["production_write"] is False
    assert metrics["ima_invoked"] is False
    assert metrics["propagation_invoked"] is False
    assert metrics["legacy_pipeline_invoked"] is False
    assert sha256_file(cfg.db_path) == production_pre
    assert prior_pre == {
        name: sha256_file(run_dir / name) for name in prior_pre
    }
    assert (run_dir / "pilot2_gate_c_remaining_quality_repair_report.md").is_file()
    assert (run_dir / "pilot2_gate_c_remaining_quality_repair_metrics.json").is_file()
    assert (run_dir / "pilot2_gate_c_repair_simulation.json").is_file()


def test_gate_c_audit_rejects_changed_human_failure_category(tmp_path):
    cfg, run_dir = _gate_c_fixture(tmp_path)
    path = run_dir / "reextraction_human_review_decisions.json"
    decisions = json.loads(path.read_text(encoding="utf-8"))
    decisions["claims"][0]["semantic_failure_category"] = "OTHER"
    write_json(path, decisions)

    with pytest.raises(PilotError, match="FAILURE_CATEGORY_CHANGED"):
        audit_pilot2_gate_c_quality_hardening(run_dir, cfg.db_path)
