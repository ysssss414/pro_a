from __future__ import annotations

from pathlib import Path

from multiformat_helpers import write_pdf
from stability_helpers import make_config

from pro_a.analyzer import SourceAnalysis
from pro_a.pilot3 import (
    PREFLIGHT_DOCUMENT_TYPE,
    REQUIRED_PROMPT_CATEGORIES,
    SOURCE_SELECTION_DOCUMENT_TYPE,
    _at_most_result,
    _target_result,
    pilot3_freeze,
    render_pilot3_review_surface,
    run_pilot3_independent_extraction,
    validate_preflight_receipt,
    validate_source_selection_manifest,
)
from pro_a.storage import sha256_file, write_json


class _StubLLM:
    available = True
    last_call_metadata = {}

    def json(self, system, user):  # pragma: no cover - Analyzer is fully stubbed
        raise AssertionError("stub Analyzer must not call the real LLM")


class _StubAnalyzer:
    available = True

    def __init__(self, cfg, db):
        self.llm = _StubLLM()

    def analyze_source(self, filename, text, mode):
        return SourceAnalysis(
            source_metadata={"title": "Independent fixture", "publication_time": ""},
            node_matches=[],
            node_candidates=[],
            claims=[{
                "statement": "Independent hard-tech research source.",
                "nature": "fact",
                "fact_time": "",
                "evidence_pointer": "[[PAGE:1]]",
                "evidence_excerpt": "Independent hard-tech research source.",
                "attributed_to": "Expert",
                "scope": "fixture",
                "assumption": "",
                "status": "current",
                "confidence": 0.9,
                "novelty_level": "N2",
                "structured": {},
                "related_node_ids": [],
                "related_candidate_names": [],
                "evidence_validated": True,
                "validation": {"evidence_validated": True, "model_confidence": 0.9},
            }],
            source_references=[],
            relation_candidates=[],
        )


def test_pilot3_source_selection_and_preflight_are_bound_before_extraction(tmp_path):
    cfg, _ = make_config(tmp_path)
    source = tmp_path / "independent.pdf"
    write_pdf(source, ["Independent hard-tech research source."])
    run_id = "PILOT_20260831_1234ABCD"
    manifest_path = tmp_path / "pilot3_source_selection_manifest.json"
    write_json(manifest_path, {
        "document_type": SOURCE_SELECTION_DOCUMENT_TYPE,
        "schema_version": "1",
        "pilot_run_id": run_id,
        "eligible_candidate_count": 1,
        "selection_frozen_before_semantic_extraction": True,
        "source_replacement_after_freeze_allowed": False,
        "selected_source": {"path": str(source.resolve()), "sha256": sha256_file(source)},
    })

    selection = validate_source_selection_manifest(manifest_path, source, run_id)
    freeze = pilot3_freeze(cfg)
    receipt_path = tmp_path / "preflight.json"
    write_json(receipt_path, {
        "document_type": PREFLIGHT_DOCUMENT_TYPE,
        "passed": True,
        "source_sha256": selection["source_sha256"],
        "prompt_sha256": freeze["prompt_sha256"],
        "code_file_sha256": freeze["code_file_sha256"],
        "checks": {
            "gate_b_attribution_regression": "PASS",
            "gate_c_guardrails": "PASS",
            "quote_fidelity_fail_closed": "PASS",
            "model_pointer_non_authoritative": "PASS",
            "evidence_contract_v2": "PASS",
        },
    })

    receipt = validate_preflight_receipt(
        receipt_path, selection["source_sha256"], freeze,
    )
    assert selection["parse_diagnostics"]["error_units"] == 0
    assert selection["parse_diagnostics"]["text_units"] == 1
    assert receipt["passed"] is True
    assert all(freeze["prompt_categories"][name] for name in REQUIRED_PROMPT_CATEGORIES)
    assert freeze["runtime_protections"]["company_to_speaker_mutation_removed"] is True
    assert freeze["runtime_protections"]["model_page_pointer_authoritative"] is False


def test_pilot3_mechanical_targets_use_frozen_thresholds():
    assert _target_result(17, 20, at_least=85.0)["passed"] is True
    assert _target_result(16, 20, at_least=85.0)["passed"] is False
    assert _at_most_result(3, 20, at_most=15.0)["passed"] is True
    assert _at_most_result(4, 20, at_most=15.0)["passed"] is False


def test_pilot3_review_surface_keeps_semantic_decisions_pending():
    quote = {
        "pilot_run_id": "PILOT_20260831_1234ABCD",
        "source_sha256": "abc",
        "claims": [{
            "claim_id": "C1",
            "fidelity_status": "PROVENANCE_MISMATCH_RECOVERED",
            "evidence_contract": {
                "model_page_pointer": {
                    "value": "[[PAGE:2]]", "status": "mismatch", "authoritative": False,
                },
                "resolved_locator": {
                    "kind": "single_page", "locator": "PAGE:1", "authoritative": True,
                },
            },
        }],
    }
    evidence = {"claims": [{
        "claim_id": "C1",
        "statement": "The company reached qualification.",
        "attributed_to": "Expert",
        "original_evidence_excerpt": "The company reached qualification.",
        "bounded_context_candidates": [],
        "evidence_spans": [],
        "formal_confidence": 0.9,
        "model_confidence": 0.9,
    }]}

    rendered = render_pilot3_review_surface(quote, evidence)
    assert "authoritative deterministic locator" in rendered
    assert "[[PAGE:2]]` / `mismatch" in rendered
    assert "Human decision: `PENDING`" in rendered
    assert "semantic acceptance" in rendered.lower()


def test_pilot3_end_to_end_isolated_path_stops_before_human_review(
    tmp_path, monkeypatch,
):
    cfg, _ = make_config(tmp_path)
    cfg.llm.enabled = True
    monkeypatch.setenv(cfg.llm.api_key_env, "fixture-key")
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", _StubAnalyzer)
    monkeypatch.setattr(
        "pro_a.pilot3.PRODUCTION_BASELINE_SHA256", sha256_file(cfg.db_path),
    )
    source = tmp_path / "independent.pdf"
    write_pdf(source, ["Independent hard-tech research source."])
    run_id = "PILOT_20260831_1234ABCD"
    run_dir = cfg.root / "phase3c" / run_id
    run_dir.mkdir(parents=True)
    manifest_path = run_dir / "pilot3_source_selection_manifest.json"
    write_json(manifest_path, {
        "document_type": SOURCE_SELECTION_DOCUMENT_TYPE,
        "pilot_run_id": run_id,
        "eligible_candidate_count": 1,
        "selection_frozen_before_semantic_extraction": True,
        "source_replacement_after_freeze_allowed": False,
        "selected_source": {"path": str(source.resolve()), "sha256": sha256_file(source)},
    })
    freeze = pilot3_freeze(cfg)
    receipt_path = run_dir / "pilot3_preflight_receipt.json"
    write_json(receipt_path, {
        "document_type": PREFLIGHT_DOCUMENT_TYPE,
        "passed": True,
        "source_sha256": sha256_file(source),
        "prompt_sha256": freeze["prompt_sha256"],
        "code_file_sha256": freeze["code_file_sha256"],
        "checks": {"frozen_path": "PASS"},
    })

    result = run_pilot3_independent_extraction(
        source, manifest_path, receipt_path, run_id, cfg,
    )

    assert result["status"] == "PASS"
    assert result["metrics"]["PHASE3C_PILOT3_EXTRACTION_COMPLETE"] is True
    assert result["metrics"]["claims_total"] == 1
    assert result["metrics"]["human_decisions"]["PENDING"] == 1
    assert result["metrics"]["attribution_mechanical_qa"][
        "known_old_mutation_recurrence"
    ] == "NO"
    assert result["metrics"]["production"]["unchanged"] is True
    assert result["metrics"]["isolation"]["legacy_pipeline_invoked"] is False
    assert (run_dir / "evidence_review_surface.md").is_file()
