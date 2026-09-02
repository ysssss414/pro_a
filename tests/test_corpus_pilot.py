from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.analyzer import SourceAnalysis
from pro_a.corpus_pilot import (
    EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE,
    STAGE1_3_CONTEXT_RADIUS,
    _bounded_context_candidates,
    _controlled_reextraction_freeze,
    _controlled_reextraction_mechanical_diagnostics,
    _ordered_cross_page_spans,
    _validate_stage1_3_context_span,
    PilotError,
    apply_production_reviewed_bundle,
    build_bounded_local_subspan,
    build_pilot2_evidence_support_draft,
    close_pilot2_human_review,
    close_stage1_2_human_review,
    extraction_bundle_sha256,
    extract_pilot_source,
    phase3c_prompt_repair_status,
    preview_reviewed_bundle,
    rebind_stage1_evidence_locators,
    resolve_pdf_evidence_locator,
    run_pilot2_gate_a_quote_fidelity,
    run_pilot2_real_extraction,
    run_stage1_3_evidence_scope_diagnostic,
    run_stage1_4_evidence_contract_v2,
    validate_review,
)
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from pro_a.storage import sha256_file, write_json

from multiformat_helpers import EXCERPT, write_pdf, write_source
from stability_helpers import make_config


class StubLLM:
    available = True
    last_call_metadata = {}

    def json(self, system, user):  # pragma: no cover - extraction is stubbed at Analyzer
        raise AssertionError("stub Analyzer should not call LLM")


class StubAnalyzer:
    available = True

    def __init__(self, cfg, db):
        self.llm = StubLLM()

    def analyze_source(self, filename, text, mode):
        assert mode == "deep"
        return SourceAnalysis(
            source_metadata={
                "title": "Fixture pilot source",
                "summary": "Deterministic fixture summary",
                "source_rank": "A",
                "source_origin_type": "secondary",
                "author": "Fixture analyst",
                "organization": "Fixture research",
                "publication_time": "2026-08-28",
            },
            node_matches=[],
            node_candidates=[{
                "canonical_name": "Glass Bridge",
                "primary_type": "Technology",
                "confidence": 0.8,
                "reason": "Fixture observation",
                "quality_eligible": True,
            }],
            claims=[
                {
                    "statement": EXCERPT,
                    "nature": "data",
                    "fact_time": "",
                    "evidence_pointer": "model pointer",
                    "evidence_excerpt": EXCERPT,
                    "attributed_to": "",
                    "scope": "fixture",
                    "assumption": "",
                    "status": "current",
                    "confidence": 0.9,
                    "novelty_level": "N2",
                    "structured": {},
                    "related_node_ids": [],
                    "related_candidate_names": ["Glass Bridge"],
                    "evidence_validated": True,
                    "validation": {"evidence_validated": True, "errors": []},
                },
                {
                    "statement": "Unvalidated fixture claim.",
                    "nature": "fact",
                    "evidence_pointer": "missing",
                    "evidence_excerpt": "not present in source",
                    "attributed_to": "",
                    "scope": "fixture",
                    "status": "current",
                    "confidence": 0.4,
                    "novelty_level": "N2",
                    "structured": {},
                    "related_node_ids": [],
                    "related_candidate_names": [],
                    "evidence_validated": False,
                },
            ],
            source_references=[],
            relation_candidates=[],
        )


def _ready_review(result, decisions=("KEEP", "DROP")):
    bundle = copy.deepcopy(result["bundle"])
    review = copy.deepcopy(result["review"])
    review["status"] = "READY"
    review["source"]["metadata_decision"] = "APPROVED"
    for claim, decision in zip(review["claims"], decisions):
        claim["decision"] = decision
    return bundle, review


def _stage1_2_decision_artifact(bundle, decisions):
    return {
        "document_type": "phase3c_human_review_decisions",
        "schema_version": "1",
        "pilot_run_id": bundle["pilot_run_id"],
        "source_metadata_accepted_as_incomplete": True,
        "decisions": [
            {
                "claim_id": claim["claim_id"],
                "decision": decision,
                "rationale": f"Fixture review decision: {decision}.",
            }
            for claim, decision in zip(bundle["claims"], decisions)
        ],
    }


def _canonical_sha256(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stage1_3_decision_artifact(bundle, review, claim_id, **overrides):
    item = {
        "claim_id": claim_id,
        "primary_failure_category": "CONTEXT_INSUFFICIENT",
        "secondary_failure_categories": [],
        "atomicity_issue": False,
        "atomicity_reason": "",
        "stored_excerpt_self_sufficient": False,
        "bounded_context_supports_claim": True,
        "supporting_context_before": "Subject context.",
        "supporting_context_after": "",
        "context_locators": ["PAGE:3"],
        "diagnostic_support_span": [{"locator": "PAGE:3", "text": "Subject context."}],
        "diagnostic_disposition": "RECOVERABLE_WITH_BOUNDED_CONTEXT",
        "rationale": "The immediately preceding subject resolves the excerpt.",
    }
    item.update(overrides)
    return {
        "document_type": "phase3c_stage1_3_diagnostic_decisions",
        "schema_version": "1",
        "pilot_run_id": bundle["pilot_run_id"],
        "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
        "stage1_2_review_sha256": _canonical_sha256(review),
        "context_policy": "same_page_or_immediate_adjacent_boundary_with_500_char_radius",
        "drop_diagnostics": [item],
        "cross_page_diagnostics": [],
    }


def _stage1_3_inputs(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_pdf(source, ["Introduction", EXCERPT, "Subject context. Closing note. Object after."])
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle = copy.deepcopy(stage1["bundle"])
    claim = bundle["claims"][1]
    claim.update({
        "statement": "Subject context supports Closing note.",
        "evidence_pointer": "[[PAGE:3]]",
        "evidence_excerpt": "Closing note",
        "evidence_validated": True,
        "status": "current",
    })
    locator = {
        "status": "resolved", "locator": "PAGE:3", "match_scope": "provenance",
        "match_method": "provenance_raw_exact_substring", "canonicalization": "none",
        "comparison_start": 17, "comparison_end": 29,
        "provenance": {"pointer": "[[PAGE:3]]", "locator": "PAGE:3", "status": "matched"},
    }
    claim["validation"] = {"evidence_validated": True, "errors": [], "source_locator": locator}
    claim["structured"]["validation"] = copy.deepcopy(claim["validation"])

    review = copy.deepcopy(stage1["review"])
    review["status"] = "READY"
    review["source"]["metadata_decision"] = "APPROVED"
    review["claims"][0]["decision"] = "KEEP"
    for key in list(review["claims"][1]):
        if key not in {"decision", "human_review_rationale"} and key in claim:
            review["claims"][1][key] = copy.deepcopy(claim[key])
    review["claims"][1]["decision"] = "DROP"
    review["claims"][1]["human_review_rationale"] = "Stored excerpt omits its subject."
    review["extraction_bundle_sha256"] = extraction_bundle_sha256(bundle)
    review["stage1_2"] = {"production_apply_ready": True}

    bundle_path = cfg.root / "stage1" / "stage1_1_bundle.json"
    review_path = cfg.root / "stage1" / "stage1_2_review.json"
    decisions_path = cfg.root / "stage1" / "stage1_3_decisions.json"
    write_json(bundle_path, bundle)
    write_json(review_path, review)
    write_json(
        decisions_path,
        _stage1_3_decision_artifact(bundle, review, claim["claim_id"]),
    )
    return cfg, source, bundle, review, bundle_path, review_path, decisions_path


def _stage1_4_inputs(tmp_path, monkeypatch):
    inputs = _stage1_3_inputs(tmp_path, monkeypatch)
    cfg, source, _, _, bundle_path, review_path, decisions_path = inputs
    stage1_3 = run_stage1_3_evidence_scope_diagnostic(
        bundle_path,
        review_path,
        source,
        decisions_path,
        output_dir=cfg.root / "stage1_3",
        production_db_path=cfg.db_path,
    )
    return (*inputs, Path(stage1_3["diagnostic_path"]))


def test_stage1_extracts_to_bundle_without_canonical_mutation(tmp_path, monkeypatch):
    cfg, db = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    input_path = cfg.root / "pilot-input.pdf"
    write_source(input_path)
    before = sha256_file(cfg.db_path)
    result = extract_pilot_source(input_path, cfg)

    assert result["status"] == "PASS"
    assert input_path.exists()
    assert result["production_unchanged"] is True
    assert sha256_file(cfg.db_path) == before
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM claims")["n"] == 0
    bundle = result["bundle"]
    review = result["review"]
    assert bundle["document_type"] == "phase3c_extraction_bundle"
    assert bundle["status"] == "EXTRACTED_REVIEW_REQUIRED"
    assert review["status"] == "DRAFT"
    assert review["extraction_bundle_sha256"] == extraction_bundle_sha256(bundle)
    assert all(claim["claim_id"].startswith("CLM_") for claim in bundle["claims"])
    assert bundle["observations"]["classification"] == "OBSERVATIONAL_NON_CANONICAL"
    assert bundle["canonical_write_preview"]["all_other_tables"] == 0
    serialized = json.dumps(bundle, ensure_ascii=False)
    assert "Introduction" not in serialized
    assert Path(result["extraction_bundle_path"]).exists()
    assert Path(result["review_markdown_path"]).exists()
    assert Path(result["metrics_path"]).exists()


def test_stage1_path_never_enters_legacy_side_effects(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy side effect invoked")

    from pro_a.impact_recovery import ImpactRecoveryService
    from pro_a.ima import IMAClient
    from pro_a.pipeline import IngestionPipeline
    from pro_a.proposals import ProposalManager
    from pro_a.propagation import PropagationManager

    for cls in (IngestionPipeline, PropagationManager, ProposalManager, ImpactRecoveryService, IMAClient):
        for name in dir(cls):
            if name.startswith("_") or name in {"__init__"}:
                continue
            attribute = getattr(cls, name)
            if callable(attribute):
                monkeypatch.setattr(cls, name, forbidden)
    for name in ("process_file", "_create_node_proposal", "_create_relation_proposal", "_historical_compare", "_direct_impacts"):
        monkeypatch.setattr(IngestionPipeline, name, forbidden)

    result = extract_pilot_source(source, cfg)
    assert result["status"] == "PASS"
    assert result["metrics"]["llm_calls"] == 0


def test_review_gates_require_exact_bundle_and_safe_claim_decisions(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    result = extract_pilot_source(source, cfg)
    bundle, review = _ready_review(result, ("KEEP", "KEEP"))

    with pytest.raises(PilotError, match="unvalidated Claim"):
        validate_review(bundle, review)

    review["claims"][1]["decision"] = "KEEP_NEEDS_REVIEW"
    validated = validate_review(bundle, review)
    assert validated["claims"][0]["decision"] == "KEEP"
    assert validated["claims"][1]["status"] == "needs_review"

    stale = copy.deepcopy(bundle)
    stale["source"]["original_name"] = "changed.pdf"
    with pytest.raises(PilotError, match="hash mismatch"):
        validate_review(stale, review)

    review["claims"][0]["statement"] = "edited by reviewer"
    with pytest.raises(PilotError, match="Claim content changed"):
        validate_review(bundle, review)


def test_controlled_apply_isolated_copy_is_idempotent_and_writes_only_allowed_tables(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    result = extract_pilot_source(source, cfg)
    bundle, review = _ready_review(result, ("KEEP", "KEEP_NEEDS_REVIEW"))
    bundle_path = tmp_path / "bundle.json"
    review_path = tmp_path / "review.json"
    write_json(bundle_path, bundle)
    write_json(review_path, review)
    copy_path = Path(result["production_copy"])

    with sqlite3.connect(copy_path) as conn:
        before = {
            table: conn.execute(f"SELECT * FROM {table}").fetchall()
            for table in ("nodes", "node_aliases", "node_relations", "source_node_links", "claim_node_links", "claim_relations", "proposals", "current_views", "knowledge_gaps", "research_questions", "impact_reviews", "impact_attempt_audit", "side_effect_jobs", "ima_objects")
        }
    preview = preview_reviewed_bundle(bundle_path, review_path, copy_path)
    assert preview["status"] == "NEW"
    applied = apply_production_reviewed_bundle(
        bundle_path,
        review_path,
        source,
        db_path=copy_path,
        cfg=cfg,
        archive_root=tmp_path / "archive",
    )
    assert applied["status"] == "COMMITTED"
    assert applied["claims_created"] == 2
    assert source.exists()

    with sqlite3.connect(copy_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM processing_jobs").fetchone()[0] == 1
        for table, fingerprint in before.items():
            assert conn.execute(f"SELECT * FROM {table}").fetchall() == fingerprint
    assert sha256_file(next((tmp_path / "archive").rglob("*.pdf"))) == sha256_file(source)

    replay = apply_production_reviewed_bundle(
        bundle_path,
        review_path,
        source,
        db_path=copy_path,
        cfg=cfg,
        archive_root=tmp_path / "archive",
    )
    assert replay["status"] == "IDEMPOTENT"
    with sqlite3.connect(copy_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 2


def test_apply_blocks_configured_production_database(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    result = extract_pilot_source(source, cfg)
    bundle, review = _ready_review(result, ("DROP", "DROP"))
    bundle_path = tmp_path / "bundle.json"
    review_path = tmp_path / "review.json"
    write_json(bundle_path, bundle)
    write_json(review_path, review)
    with pytest.raises(PilotError, match="configured Production DB is blocked"):
        apply_production_reviewed_bundle(
            bundle_path, review_path, source, db_path=cfg.db_path, cfg=cfg,
        )


@pytest.mark.parametrize(
    ("body", "excerpt", "method"),
    [
        ("Exact evidence text.", "Exact evidence text.", "raw_exact_substring"),
        ("Evidence across\na line.", "Evidence across a line.", "canonical_exact_substring"),
        ("Repeated    whitespace.", "Repeated whitespace.", "canonical_exact_substring"),
        ("采用 TGV 技术。", "采用TGV技术。", "pdf_normalized_exact_substring"),
        ("Range 12-\n15 layers.", "Range 12-15 layers.", "pdf_normalized_exact_substring"),
        (
            "Micro LED（光源） ，效率高，后文继续。",
            "Micro LED(光源),效率高。",
            "pdf_normalized_exact_substring",
        ),
    ],
)
def test_pdf_locator_binding_exact_normalization_cases(body, excerpt, method):
    result = resolve_pdf_evidence_locator(f"[[PAGE:1]]\n{body}", excerpt)
    assert result["status"] == "resolved"
    assert result["locator"] == "PAGE:1"
    assert result["match_method"] == method


def test_pdf_locator_binding_ambiguity_absence_and_provenance():
    repeated = "[[PAGE:1]]\nRepeated evidence.\n[[PAGE:2]]\nRepeated evidence."
    ambiguous = resolve_pdf_evidence_locator(repeated, "Repeated evidence.")
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["locators"] == ["PAGE:1", "PAGE:2"]

    provenance = resolve_pdf_evidence_locator(
        repeated, "Repeated evidence.", "[[PAGE:2]]",
    )
    assert provenance["status"] == "resolved"
    assert provenance["locator"] == "PAGE:2"
    assert provenance["match_method"] == "provenance_raw_exact_substring"
    assert provenance["provenance"]["status"] == "matched"

    mismatch = resolve_pdf_evidence_locator(
        "[[PAGE:1]]\nOther text.\n[[PAGE:2]]\nUnique evidence.",
        "Unique evidence.",
        "[[PAGE:1]]",
    )
    assert mismatch["status"] == "resolved"
    assert mismatch["locator"] == "PAGE:2"
    assert mismatch["match_scope"] == "global"
    assert mismatch["provenance"]["status"] == "mismatch"

    absent = resolve_pdf_evidence_locator(repeated, "Absent evidence.")
    assert absent["status"] == "unresolved"
    assert absent["reason"] == "not_found"

    cross_page = resolve_pdf_evidence_locator(
        "[[PAGE:1]]\nEvidence starts here and\n[[PAGE:2]]\nends here.",
        "Evidence starts here and ends here.",
    )
    assert cross_page["status"] == "unresolved"
    assert cross_page["reason"] == "cross_page_span"
    assert cross_page["spanning_locators"] == [["PAGE:1", "PAGE:2"]]


def test_stage1_1_rebind_preserves_raw_bundle_ids_and_isolation(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")

    bundle = copy.deepcopy(stage1["bundle"])
    claim = bundle["claims"][1]
    claim["evidence_pointer"] = "[[PAGE:2]]"
    claim["evidence_excerpt"] = "Capacity   reached 42 units."
    claim["status"] = "needs_review"
    claim["evidence_validated"] = False
    claim["validation"] = {
        "evidence_validated": False,
        "errors": ["evidence_excerpt_not_found"],
        "source_locator": {"status": "unresolved"},
    }
    claim["structured"]["validation"] = copy.deepcopy(claim["validation"])
    bundle["observations"]["node_candidates"][0]["candidate_id"] = "NDC_FIXED"
    bundle["observations"]["relation_candidates"] = [{
        "candidate_id": "RLC_FIXED",
        "from": "A",
        "to": "B",
    }]
    original_path = cfg.root / "stage1" / "original_bundle.json"
    write_json(original_path, bundle)
    original_file_sha = sha256_file(original_path)
    source_sha = sha256_file(source)
    production_sha = sha256_file(cfg.db_path)
    before_claims = copy.deepcopy(bundle["claims"])
    before_observations = copy.deepcopy(bundle["observations"])

    def forbidden(*args, **kwargs):
        raise AssertionError("Stage 1.1 invoked an LLM, legacy pipeline, IMA, or governance writer")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.proposals.ProposalManager", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_proposal", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_receipt", forbidden)

    output_dir = cfg.root / "stage1_1"
    result = rebind_stage1_evidence_locators(
        original_path,
        source,
        output_dir=output_dir,
        production_db_path=cfg.db_path,
    )

    assert result["status"] == "PASS"
    assert result["production_unchanged"] is True
    assert result["original_bundle_unchanged"] is True
    assert sha256_file(original_path) == original_file_sha
    assert sha256_file(source) == source_sha
    assert sha256_file(cfg.db_path) == production_sha
    assert result["metrics"]["llm_calls"] == 0
    assert result["metrics"]["llm_calls_added"] == 0
    assert result["metrics"]["claim_ids_unchanged"] is True
    assert result["metrics"]["raw_claim_content_unchanged"] is True
    assert result["metrics"]["observations_unchanged"] is True
    assert result["bundle"]["claims"][1]["evidence_validated"] is True
    assert result["bundle"]["claims"][1]["status"] == "current"
    assert result["bundle"]["observations"] == before_observations
    assert [item["claim_id"] for item in result["bundle"]["claims"]] == [
        item["claim_id"] for item in before_claims
    ]
    for old, new in zip(before_claims, result["bundle"]["claims"]):
        for field in (
            "claim_id", "statement", "nature", "fact_time", "publication_time",
            "evidence_pointer", "evidence_excerpt", "attributed_to", "scope",
            "assumption_text", "confidence", "novelty_level", "related_node_ids",
            "related_candidate_names", "claim_index",
        ):
            assert new[field] == old[field]
    assert all(item["decision"] == "PENDING" for item in result["review"]["claims"])
    assert result["review"]["extraction_bundle_sha256"] == extraction_bundle_sha256(
        result["bundle"]
    )
    assert {path.name for path in output_dir.iterdir()} == {
        "extraction_bundle_stage1_1_rebound.json",
        "extraction_review_stage1_1_draft.json",
        "stage1_1_review.md",
        "stage1_1_metrics.json",
    }


def test_stage1_2_closure_persists_explicit_decisions_without_side_effects(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle_path = Path(stage1["extraction_bundle_path"])
    draft_path = Path(stage1["review_draft_path"])
    decisions_path = cfg.root / "stage1" / "stage1_2_decisions.json"
    write_json(
        decisions_path,
        _stage1_2_decision_artifact(stage1["bundle"], ("KEEP", "DROP")),
    )
    before_bundle = bundle_path.read_bytes()
    before_draft = draft_path.read_bytes()
    before_decisions = decisions_path.read_bytes()
    production_sha = sha256_file(cfg.db_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Stage 1.2 invoked an LLM, legacy pipeline, IMA, or governance writer")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.proposals.ProposalManager", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_proposal", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_receipt", forbidden)

    result = close_stage1_2_human_review(
        bundle_path,
        draft_path,
        decisions_path,
        output_dir=cfg.root / "stage1_2_a",
        production_db_path=cfg.db_path,
    )
    replay = close_stage1_2_human_review(
        bundle_path,
        draft_path,
        decisions_path,
        output_dir=cfg.root / "stage1_2_b",
        production_db_path=cfg.db_path,
    )

    assert result["status"] == "PASS"
    assert result["production_unchanged"] is True
    assert result["inputs_unchanged"] is True
    assert result["metrics"]["claims_human_reviewed"] == 2
    assert result["metrics"]["accept"] == 1
    assert result["metrics"]["reject"] == 1
    assert result["metrics"]["pending"] == 0
    assert result["metrics"]["production_apply_ready"] is True
    assert result["metrics"]["llm_calls_added"] == 0
    assert result["review"]["status"] == "READY"
    assert result["review"]["source"]["metadata_decision"] == "APPROVED"
    assert [claim["decision"] for claim in result["review"]["claims"]] == ["KEEP", "DROP"]
    for bundle_claim, reviewed_claim in zip(stage1["bundle"]["claims"], result["review"]["claims"]):
        assert reviewed_claim["claim_id"] == bundle_claim["claim_id"]
        assert reviewed_claim["statement"] == bundle_claim["statement"]
        assert reviewed_claim["evidence_excerpt"] == bundle_claim["evidence_excerpt"]
        assert reviewed_claim["validation"] == bundle_claim["validation"]
    assert bundle_path.read_bytes() == before_bundle
    assert draft_path.read_bytes() == before_draft
    assert decisions_path.read_bytes() == before_decisions
    assert sha256_file(cfg.db_path) == production_sha
    assert Path(result["review_path"]).read_bytes() == Path(replay["review_path"]).read_bytes()
    assert Path(result["review_markdown_path"]).read_bytes() == Path(
        replay["review_markdown_path"]
    ).read_bytes()
    assert Path(result["metrics_path"]).read_bytes() == Path(replay["metrics_path"]).read_bytes()
    validate_review(stage1["bundle"], result["review"])


def test_stage1_2_cross_page_remains_unresolved_and_blocks_apply(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle = copy.deepcopy(stage1["bundle"])
    review = copy.deepcopy(stage1["review"])
    claim = bundle["claims"][1]
    locator = {
        "status": "unresolved",
        "reason": "cross_page_span",
        "spanning_locators": [["PAGE:1", "PAGE:2"]],
    }
    claim["validation"]["source_locator"] = copy.deepcopy(locator)
    claim["structured"]["validation"] = copy.deepcopy(claim["validation"])
    review_claim = review["claims"][1]
    review_claim["validation"] = copy.deepcopy(claim["validation"])
    review_claim["structured"] = copy.deepcopy(claim["structured"])
    review["extraction_bundle_sha256"] = extraction_bundle_sha256(bundle)
    bundle_path = cfg.root / "stage1" / "cross_page_bundle.json"
    draft_path = cfg.root / "stage1" / "cross_page_review.json"
    decisions_path = cfg.root / "stage1" / "cross_page_decisions.json"
    write_json(bundle_path, bundle)
    write_json(draft_path, review)
    write_json(
        decisions_path,
        _stage1_2_decision_artifact(bundle, ("KEEP", "KEEP_NEEDS_REVIEW")),
    )

    result = close_stage1_2_human_review(
        bundle_path,
        draft_path,
        decisions_path,
        output_dir=cfg.root / "stage1_2",
        production_db_path=cfg.db_path,
    )
    closed_claim = result["review"]["claims"][1]
    assert result["metrics"]["blocked_cross_page"] == 1
    assert result["metrics"]["pending"] == 0
    assert result["metrics"]["production_apply_ready"] is False
    assert closed_claim["decision"] == "KEEP_NEEDS_REVIEW"
    assert closed_claim["validation"]["source_locator"] == locator
    with pytest.raises(PilotError, match="not Production-apply-ready"):
        validate_review(bundle, result["review"])
    validate_review(bundle, result["review"], require_production_ready=False)


def test_stage1_2_rejects_silent_corrected_claim_fields(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_source(source)
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    decisions = _stage1_2_decision_artifact(stage1["bundle"], ("KEEP", "DROP"))
    decisions["decisions"][1]["corrected_claim_text"] = "Silent rewrite"
    decisions_path = cfg.root / "stage1" / "bad_decisions.json"
    write_json(decisions_path, decisions)

    with pytest.raises(PilotError, match="fields are not exact"):
        close_stage1_2_human_review(
            Path(stage1["extraction_bundle_path"]),
            Path(stage1["review_draft_path"]),
            decisions_path,
            output_dir=cfg.root / "stage1_2",
            production_db_path=cfg.db_path,
        )


def test_stage1_3_bounded_context_is_deterministic_and_side_effect_free(tmp_path, monkeypatch):
    (
        cfg, source, bundle, review, bundle_path, review_path, decisions_path,
    ) = _stage1_3_inputs(tmp_path, monkeypatch)
    input_bytes = {
        path: path.read_bytes() for path in (source, bundle_path, review_path, decisions_path)
    }
    production_sha = sha256_file(cfg.db_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Stage 1.3 invoked an LLM, legacy pipeline, IMA, or governance writer")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.proposals.ProposalManager", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_proposal", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_receipt", forbidden)

    result = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3_a", production_db_path=cfg.db_path,
    )
    replay = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3_b", production_db_path=cfg.db_path,
    )

    assert result["status"] == "PASS"
    assert result["production_unchanged"] is True
    assert result["inputs_unchanged"] is True
    assert result["metrics"]["recoverable_context_failures"] == 1
    assert result["metrics"]["llm_calls_added"] == 0
    assert result["metrics"]["production_write"] is False
    assert result["metrics"]["ima_invoked"] is False
    item = result["diagnostic"]["drop_diagnostics"][0]
    original_claim = bundle["claims"][1]
    assert item["original_human_decision"] == "DROP"
    assert item["original_claim"] == original_claim["statement"]
    assert item["original_evidence_excerpt"] == original_claim["evidence_excerpt"]
    assert item["claim_id"] == original_claim["claim_id"]
    assert item["bounded_context_supports_claim"] is True
    assert [claim["decision"] for claim in review["claims"]] == ["KEEP", "DROP"]
    assert all(path.read_bytes() == before for path, before in input_bytes.items())
    assert sha256_file(cfg.db_path) == production_sha
    for key in ("diagnostic_path", "report_path", "metrics_path"):
        assert Path(result[key]).read_bytes() == Path(replay[key]).read_bytes()


def test_stage1_3_generator_accepts_nearest_duplicate_same_page_context():
    page = (
        "谢谢。" + "远" * (STAGE1_3_CONTEXT_RADIUS + 100) + "。"
        "谢谢。证据。后文。"
    )

    candidates = _bounded_context_candidates([("PAGE:1", page)], "PAGE:1", "证据。")

    assert candidates[0]["direction"] == "before"
    assert candidates[0]["text"] == "谢谢。"
    assert candidates[1]["direction"] == "after"
    assert candidates[1]["text"] == "后文。"


def test_stage1_3_generator_ignores_context_erased_by_binding_normalization():
    candidates = _bounded_context_candidates(
        [("PAGE:1", "前文。证据。 。后文。")], "PAGE:1", "证据。",
    )

    assert len(candidates) == 1
    assert candidates[0]["direction"] == "before"
    assert candidates[0]["text"] == "前文。"
    assert candidates[0]["locators"] == ["PAGE:1"]
    assert candidates[0]["selection_rule"]


def _raw_authoritative_locator(page: str, evidence: str) -> dict:
    start = page.find(evidence)
    assert start >= 0
    return {
        "status": "resolved",
        "locator": "PAGE:1",
        "match_method": "raw_exact_substring",
        "comparison_start": start,
        "comparison_end": start + len(evidence),
    }


def test_bounded_local_subspan_keeps_existing_valid_adjacent_candidate_unchanged():
    page = "前文。证据。后文。"

    candidates = _bounded_context_candidates(
        [("PAGE:1", page)], "PAGE:1", "证据。",
        authoritative_locator=_raw_authoritative_locator(page, "证据。"),
    )

    assert [item["text"] for item in candidates] == ["前文。", "后文。"]
    assert all(
        item["selection_rule"]
        == "same_page_or_immediate_adjacent_boundary_with_500_char_radius"
        for item in candidates
    )


def test_bounded_local_subspan_falls_back_inside_large_evidence_segment_before():
    page = "前段。" + "甲" * 601 + "证据。"

    candidates = _bounded_context_candidates(
        [("PAGE:1", page)], "PAGE:1", "证据。",
        authoritative_locator=_raw_authoritative_locator(page, "证据。"),
    )

    assert len(candidates) == 1
    assert candidates[0]["direction"] == "before"
    assert candidates[0]["text"] == "甲" * 500
    assert candidates[0]["selection_rule"] == (
        EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE
    )
    assert candidates[0]["text"] in page


def test_bounded_local_subspan_falls_back_inside_large_evidence_segment_after():
    page = "证据" + "乙" * 601 + "。后段。"

    candidates = _bounded_context_candidates(
        [("PAGE:1", page)], "PAGE:1", "证据",
        authoritative_locator=_raw_authoritative_locator(page, "证据"),
    )

    assert len(candidates) == 1
    assert candidates[0]["direction"] == "after"
    assert candidates[0]["text"] == "乙" * 500
    assert candidates[0]["selection_rule"] == (
        EVIDENCE_SEGMENT_BOUNDED_SUBSPAN_SELECTION_RULE
    )
    assert candidates[0]["text"] in page


def test_build_bounded_local_subspan_accepts_exactly_500_raw_characters():
    segment = "甲" * 500 + "证据" + "乙" * 500

    before = build_bounded_local_subspan(segment, 500, 502, "before")
    after = build_bounded_local_subspan(segment, 500, 502, "after")

    assert before == "甲" * 500
    assert after == "乙" * 500
    for candidate in (before, after):
        _validate_stage1_3_context_span(
            span={"locator": "PAGE:1", "text": candidate},
            page_by_locator={"PAGE:1": segment},
            evidence_locator="PAGE:1",
            evidence_excerpt="证据",
        )


def test_bounded_local_subspan_preserves_empty_normalization_fail_closed():
    page = "前段。" + "甲" * 600 + " " * 500 + "证据"

    with pytest.raises(PilotError, match="outside the bounded window"):
        _bounded_context_candidates(
            [("PAGE:1", page)], "PAGE:1", "证据",
            authoritative_locator=_raw_authoritative_locator(page, "证据"),
        )


@pytest.mark.parametrize("status", ["ambiguous", "unresolved"])
def test_bounded_local_subspan_does_not_guess_nonresolved_evidence(status):
    page = "前段。" + "甲" * 601 + "证据。"
    locator = {
        "status": status,
        "locator": "PAGE:1",
        "match_method": "raw_exact_substring",
        "comparison_start": page.find("证据。"),
        "comparison_end": page.find("证据。") + len("证据。"),
    }

    with pytest.raises(PilotError, match="outside the bounded window"):
        _bounded_context_candidates(
            [("PAGE:1", page)], "PAGE:1", "证据。",
            authoritative_locator=locator,
        )


def test_bounded_local_subspan_does_not_change_cross_page_omit_behavior():
    first_page = "证据" + "甲" * 601
    pages = [("PAGE:1", first_page), ("PAGE:2", "后文。")]

    candidates = _bounded_context_candidates(
        pages, "PAGE:1", "证据",
        authoritative_locator=_raw_authoritative_locator(first_page, "证据"),
    )

    assert candidates == []


def test_build_bounded_local_subspan_does_not_manufacture_unavailable_context():
    assert build_bounded_local_subspan("证据", 0, 2, "before") is None
    assert build_bounded_local_subspan("证据", 0, 2, "after") is None


def test_stage1_3_validator_rejects_context_erased_by_binding_normalization():
    with pytest.raises(PilotError, match="normalized local binding failed"):
        _validate_stage1_3_context_span(
            span={"locator": "PAGE:1", "text": "。"},
            page_by_locator={"PAGE:1": "前文。证据。 。后文。"},
            evidence_locator="PAGE:1",
            evidence_excerpt="证据。",
        )


def test_stage1_3_validator_accepts_normalized_same_page_context():
    _validate_stage1_3_context_span(
        span={"locator": "PAGE:1", "text": "上 文"},
        page_by_locator={"PAGE:1": "上 文。证 据。"},
        evidence_locator="PAGE:1",
        evidence_excerpt="证 据。",
    )


def test_stage1_3_validator_accepts_context_at_exact_same_page_boundary():
    page = "证据" + "隔" * STAGE1_3_CONTEXT_RADIUS + "上下文"

    _validate_stage1_3_context_span(
        span={"locator": "PAGE:1", "text": "上下文"},
        page_by_locator={"PAGE:1": page},
        evidence_locator="PAGE:1",
        evidence_excerpt="证据",
    )


def test_stage1_3_validator_rejects_context_outside_same_page_boundary():
    page = "证据" + "隔" * (STAGE1_3_CONTEXT_RADIUS + 1) + "上下文"

    with pytest.raises(PilotError, match="same-page context is outside the bounded window"):
        _validate_stage1_3_context_span(
            span={"locator": "PAGE:1", "text": "上下文"},
            page_by_locator={"PAGE:1": page},
            evidence_locator="PAGE:1",
            evidence_excerpt="证据",
        )


def test_stage1_3_validator_accepts_evidence_near_page_start():
    pages = {
        "PAGE:1": "旧" * 700 + "前文",
        "PAGE:2": "隔" * STAGE1_3_CONTEXT_RADIUS + "证据",
    }

    _validate_stage1_3_context_span(
        span={"locator": "PAGE:1", "text": "前文"},
        page_by_locator=pages,
        evidence_locator="PAGE:2",
        evidence_excerpt="证据",
    )


def test_stage1_3_validator_accepts_evidence_near_page_end():
    pages = {
        "PAGE:1": "证据" + "隔" * STAGE1_3_CONTEXT_RADIUS,
        "PAGE:2": "垫" * STAGE1_3_CONTEXT_RADIUS + "后文",
    }

    _validate_stage1_3_context_span(
        span={"locator": "PAGE:2", "text": "后文"},
        page_by_locator=pages,
        evidence_locator="PAGE:1",
        evidence_excerpt="证据",
    )


def test_stage1_3_validator_keeps_cross_page_isolation():
    pages = {"PAGE:1": "前文", "PAGE:2": "中间", "PAGE:3": "证据"}

    with pytest.raises(PilotError, match="distant page context is forbidden"):
        _validate_stage1_3_context_span(
            span={"locator": "PAGE:1", "text": "前文"},
            page_by_locator=pages,
            evidence_locator="PAGE:3",
            evidence_excerpt="证据",
        )


def test_stage1_3_rejects_distant_or_silent_context_changes(tmp_path, monkeypatch):
    (
        cfg, source, _, _, bundle_path, review_path, decisions_path,
    ) = _stage1_3_inputs(tmp_path, monkeypatch)
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    item = decisions["drop_diagnostics"][0]
    item["supporting_context_before"] = "Introduction"
    item["context_locators"] = ["PAGE:1"]
    item["diagnostic_support_span"] = [{"locator": "PAGE:1", "text": "Introduction"}]
    write_json(decisions_path, decisions)

    with pytest.raises(PilotError, match="distant page context is forbidden"):
        run_stage1_3_evidence_scope_diagnostic(
            bundle_path, review_path, source, decisions_path,
            output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
        )

    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    decisions["drop_diagnostics"][0]["corrected_claim_text"] = "Silent rewrite"
    write_json(decisions_path, decisions)
    with pytest.raises(PilotError, match="fields are not exact"):
        run_stage1_3_evidence_scope_diagnostic(
            bundle_path, review_path, source, decisions_path,
            output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
        )


@pytest.mark.parametrize(("primary", "disposition", "atomicity"), [
    ("TRUE_OVERREACH", "GENUINE_EXTRACTION_FAILURE", True),
    ("ATTRIBUTION_ERROR", "ATTRIBUTION_FAILURE", False),
    ("CONDITIONALITY_LOSS", "CONDITIONALITY_FAILURE", False),
])
def test_stage1_3_explicit_semantic_failures_are_not_recovered(
    tmp_path, monkeypatch, primary, disposition, atomicity,
):
    (
        cfg, source, bundle, review, bundle_path, review_path, decisions_path,
    ) = _stage1_3_inputs(tmp_path, monkeypatch)
    item_overrides = {
        "primary_failure_category": primary,
        "atomicity_issue": atomicity,
        "atomicity_reason": "Compound unsupported clauses." if atomicity else "",
        "bounded_context_supports_claim": False,
        "supporting_context_before": "",
        "context_locators": [],
        "diagnostic_support_span": [],
        "diagnostic_disposition": disposition,
        "rationale": "Bounded context does not repair this semantic failure.",
    }
    write_json(
        decisions_path,
        _stage1_3_decision_artifact(
            bundle, review, bundle["claims"][1]["claim_id"], **item_overrides,
        ),
    )
    result = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
    )
    item = result["diagnostic"]["drop_diagnostics"][0]
    assert item["primary_failure_category"] == primary
    assert item["diagnostic_disposition"] == disposition
    assert item["bounded_context_supports_claim"] is False
    assert result["metrics"]["recoverable_context_failures"] == 0


def test_stage1_3_can_record_excerpt_self_sufficient_without_rewriting_it(tmp_path, monkeypatch):
    (
        cfg, source, bundle, review, bundle_path, review_path, decisions_path,
    ) = _stage1_3_inputs(tmp_path, monkeypatch)
    write_json(
        decisions_path,
        _stage1_3_decision_artifact(
            bundle,
            review,
            bundle["claims"][1]["claim_id"],
            primary_failure_category="OTHER",
            stored_excerpt_self_sufficient=True,
            supporting_context_before="",
            context_locators=[],
            diagnostic_support_span=[],
            diagnostic_disposition="UNRESOLVED",
            rationale="The excerpt is self-sufficient; the historical DROP reason is otherwise unresolved.",
        ),
    )
    result = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
    )
    item = result["diagnostic"]["drop_diagnostics"][0]
    assert item["stored_excerpt_self_sufficient"] is True
    assert item["original_evidence_excerpt"] == bundle["claims"][1]["evidence_excerpt"]
    assert item["original_human_decision"] == "DROP"


def test_stage1_3_retains_verified_adjacent_page_evidence_spans(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_pdf(source, ["Introduction", f"{EXCERPT} First half", "second half. Tail"])
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle = copy.deepcopy(stage1["bundle"])
    claim = bundle["claims"][1]
    claim.update({
        "statement": "First half second half.",
        "evidence_pointer": "[[PAGE:2]]",
        "evidence_excerpt": "First half second half.",
        "evidence_validated": False,
        "status": "needs_review",
    })
    locator = {
        "status": "unresolved", "reason": "cross_page_span",
        "spanning_locators": [["PAGE:2", "PAGE:3"]],
        "match_scope": "none", "match_method": "none",
        "canonicalization": "unicode_nfkc+markdown_unescape+whitespace+han_spacing+hyphen_spacing+punctuation_spacing+terminal_punctuation",
        "provenance": {"pointer": "[[PAGE:2]]", "locator": "PAGE:2", "status": "mismatch"},
    }
    claim["validation"] = {
        "evidence_validated": False, "errors": ["evidence_excerpt_not_found"],
        "source_locator": locator,
    }
    claim["structured"]["validation"] = copy.deepcopy(claim["validation"])

    review = copy.deepcopy(stage1["review"])
    review["status"] = "READY"
    review["source"]["metadata_decision"] = "APPROVED"
    review["claims"][0]["decision"] = "KEEP"
    for key in list(review["claims"][1]):
        if key not in {"decision", "human_review_rationale"} and key in claim:
            review["claims"][1][key] = copy.deepcopy(claim[key])
    review["claims"][1]["decision"] = "KEEP_NEEDS_REVIEW"
    review["claims"][1]["human_review_rationale"] = "Exact Evidence spans adjacent pages."
    review["extraction_bundle_sha256"] = extraction_bundle_sha256(bundle)
    review["stage1_2"] = {"production_apply_ready": False}

    bundle_path = cfg.root / "stage1" / "bundle.json"
    review_path = cfg.root / "stage1" / "review.json"
    decisions_path = cfg.root / "stage1" / "decisions.json"
    write_json(bundle_path, bundle)
    write_json(review_path, review)
    write_json(decisions_path, {
        "document_type": "phase3c_stage1_3_diagnostic_decisions",
        "schema_version": "1",
        "pilot_run_id": bundle["pilot_run_id"],
        "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
        "stage1_2_review_sha256": _canonical_sha256(review),
        "context_policy": "same_page_or_immediate_adjacent_boundary_with_500_char_radius",
        "drop_diagnostics": [],
        "cross_page_diagnostics": [{
            "claim_id": claim["claim_id"],
            "cross_page_verified": True,
            "pages": ["PAGE:2", "PAGE:3"],
            "semantic_support": "complete",
            "evidence_spans": [
                {"locator": "PAGE:2", "text": "First half"},
                {"locator": "PAGE:3", "text": "second half."},
            ],
            "rationale": "The exact quotation continues on the immediately adjacent page.",
        }],
    })

    result = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
    )
    item = result["diagnostic"]["cross_page_diagnostics"][0]
    assert item["cross_page_verified"] is True
    assert item["pages"] == ["PAGE:2", "PAGE:3"]
    assert item["semantic_support"] == "complete"
    assert item["original_human_decision"] == "KEEP_NEEDS_REVIEW"
    assert result["metrics"]["cross_page_claims_verified"] == 1
    assert review["claims"][1]["decision"] == "KEEP_NEEDS_REVIEW"


def test_stage1_4_v2_replay_is_additive_deterministic_and_side_effect_free(tmp_path, monkeypatch):
    (
        cfg, source, bundle, review, bundle_path, review_path, decisions_path,
        diagnostic_path,
    ) = _stage1_4_inputs(tmp_path, monkeypatch)
    protected = (source, bundle_path, review_path, decisions_path, diagnostic_path)
    input_bytes = {path: path.read_bytes() for path in protected}
    production_sha = sha256_file(cfg.db_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Stage 1.4 invoked an LLM, writer, pipeline, IMA, or governance path")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.proposals.ProposalManager", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_proposal", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_receipt", forbidden)

    result = run_stage1_4_evidence_contract_v2(
        bundle_path, review_path, diagnostic_path, source,
        output_dir=cfg.root / "stage1_4_a", production_db_path=cfg.db_path,
    )
    replay = run_stage1_4_evidence_contract_v2(
        bundle_path, review_path, diagnostic_path, source,
        output_dir=cfg.root / "stage1_4_b", production_db_path=cfg.db_path,
    )

    assert result["status"] == "PASS"
    assert result["production_unchanged"] is True
    assert result["inputs_unchanged"] is True
    assert result["metrics"]["v2_support_counts"] == {
        "BLOCKED": 0, "SUPPORTED": 2, "UNSUPPORTED": 0,
    }
    assert result["metrics"]["support_mode_counts"] == {
        "BOUNDED_CONTEXT": 1, "EXCERPT_ONLY": 1, "NONE": 0, "ORDERED_SPANS": 0,
    }
    excerpt_only, context = result["contract"]["claims"]
    assert excerpt_only["support_mode"] == "EXCERPT_ONLY"
    assert context["support_mode"] == "BOUNDED_CONTEXT"
    assert context["stage1_2_decision"] == "DROP"
    assert context["stage1_3_diagnosis"] == "RECOVERABLE_WITH_BOUNDED_CONTEXT"
    assert context["supporting_context"][0]["direction"] == "before"
    assert context["supporting_context_locators"] == ["PAGE:3"]
    assert context["original_claim"] == bundle["claims"][1]["statement"]
    assert context["original_evidence_excerpt"] == bundle["claims"][1]["evidence_excerpt"]
    assert [item["claim_id"] for item in result["contract"]["claims"]] == [
        item["claim_id"] for item in bundle["claims"]
    ]
    assert [item["stage1_2_decision"] for item in result["contract"]["claims"]] == [
        item["decision"] for item in review["claims"]
    ]
    assert all(path.read_bytes() == before for path, before in input_bytes.items())
    assert sha256_file(cfg.db_path) == production_sha
    for key in ("contract_path", "report_path", "metrics_path"):
        assert Path(result[key]).read_bytes() == Path(replay[key]).read_bytes()


def test_stage1_4_accepts_exact_bounded_following_context(tmp_path, monkeypatch):
    (
        cfg, source, bundle, review, bundle_path, review_path, decisions_path,
    ) = _stage1_3_inputs(tmp_path, monkeypatch)
    decisions = _stage1_3_decision_artifact(
        bundle,
        review,
        bundle["claims"][1]["claim_id"],
        supporting_context_before="",
        supporting_context_after="Object after.",
        context_locators=["PAGE:3"],
        diagnostic_support_span=[{"locator": "PAGE:3", "text": "Object after."}],
        rationale="The immediate following object completes the local support.",
    )
    write_json(decisions_path, decisions)
    stage1_3 = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
    )
    result = run_stage1_4_evidence_contract_v2(
        bundle_path, review_path, Path(stage1_3["diagnostic_path"]), source,
        output_dir=cfg.root / "stage1_4", production_db_path=cfg.db_path,
    )
    context = result["contract"]["claims"][1]["supporting_context"]
    assert context == [{
        "direction": "after",
        "text": "Object after.",
        "locators": ["PAGE:3"],
        "selection_rule": "same_page_or_immediate_adjacent_boundary_with_500_char_radius",
    }]


def test_stage1_4_rejects_tampered_distant_context(tmp_path, monkeypatch):
    (
        cfg, source, _, _, bundle_path, review_path, _, diagnostic_path,
    ) = _stage1_4_inputs(tmp_path, monkeypatch)
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    item = diagnostic["drop_diagnostics"][0]
    item["supporting_context_before"] = "Introduction"
    item["context_locators"] = ["PAGE:1"]
    item["diagnostic_support_span"] = [{"locator": "PAGE:1", "text": "Introduction"}]
    write_json(diagnostic_path, diagnostic)

    with pytest.raises(PilotError, match="distant page context is forbidden"):
        run_stage1_4_evidence_contract_v2(
            bundle_path, review_path, diagnostic_path, source,
            output_dir=cfg.root / "stage1_4", production_db_path=cfg.db_path,
        )


@pytest.mark.parametrize(("primary", "disposition", "atomicity"), [
    ("TRUE_OVERREACH", "GENUINE_EXTRACTION_FAILURE", True),
    ("ATTRIBUTION_ERROR", "ATTRIBUTION_FAILURE", False),
    ("CONDITIONALITY_LOSS", "CONDITIONALITY_FAILURE", False),
    ("SCOPE_ERROR", "GENUINE_EXTRACTION_FAILURE", False),
])
def test_stage1_4_context_never_rescues_semantic_failures(
    tmp_path, monkeypatch, primary, disposition, atomicity,
):
    (
        cfg, source, bundle, review, bundle_path, review_path, decisions_path,
    ) = _stage1_3_inputs(tmp_path, monkeypatch)
    write_json(decisions_path, _stage1_3_decision_artifact(
        bundle,
        review,
        bundle["claims"][1]["claim_id"],
        primary_failure_category=primary,
        atomicity_issue=atomicity,
        atomicity_reason="Compound unsupported clauses." if atomicity else "",
        bounded_context_supports_claim=False,
        supporting_context_before="",
        context_locators=[],
        diagnostic_support_span=[],
        diagnostic_disposition=disposition,
        rationale="The semantic failure remains unsupported under Contract v2.",
    ))
    stage1_3 = run_stage1_3_evidence_scope_diagnostic(
        bundle_path, review_path, source, decisions_path,
        output_dir=cfg.root / "stage1_3", production_db_path=cfg.db_path,
    )
    result = run_stage1_4_evidence_contract_v2(
        bundle_path, review_path, Path(stage1_3["diagnostic_path"]), source,
        output_dir=cfg.root / "stage1_4", production_db_path=cfg.db_path,
    )
    failure = result["contract"]["claims"][1]
    assert failure["v2_support_status"] == "UNSUPPORTED"
    assert failure["support_mode"] == "NONE"
    assert failure["supporting_context"] == []
    assert failure["evidence_spans"] == []
    assert result["metrics"]["v2_support_counts"]["UNSUPPORTED"] == 1


def test_stage1_4_ordered_spans_preserve_pages_text_and_historical_decision(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot.pdf"
    write_pdf(source, ["Introduction", f"{EXCERPT} First half", "second half. Tail"])
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle = copy.deepcopy(stage1["bundle"])
    claim = bundle["claims"][1]
    claim.update({
        "statement": "First half second half.",
        "evidence_pointer": "[[PAGE:2]]",
        "evidence_excerpt": "First half second half.",
        "evidence_validated": False,
        "status": "needs_review",
    })
    locator = {
        "status": "unresolved", "reason": "cross_page_span",
        "spanning_locators": [["PAGE:2", "PAGE:3"]],
        "match_scope": "none", "match_method": "none",
        "canonicalization": "fixture",
        "provenance": {"pointer": "[[PAGE:2]]", "locator": "PAGE:2", "status": "mismatch"},
    }
    claim["validation"] = {
        "evidence_validated": False, "errors": ["evidence_excerpt_not_found"],
        "source_locator": locator,
    }
    claim["structured"]["validation"] = copy.deepcopy(claim["validation"])
    review = copy.deepcopy(stage1["review"])
    review["status"] = "READY"
    review["source"]["metadata_decision"] = "APPROVED"
    review["claims"][0]["decision"] = "KEEP"
    for key in list(review["claims"][1]):
        if key not in {"decision", "human_review_rationale"} and key in claim:
            review["claims"][1][key] = copy.deepcopy(claim[key])
    review["claims"][1]["decision"] = "KEEP_NEEDS_REVIEW"
    review["claims"][1]["human_review_rationale"] = "Exact adjacent-page Evidence."
    review["extraction_bundle_sha256"] = extraction_bundle_sha256(bundle)
    review["stage1_2"] = {"production_apply_ready": False}
    diagnostic = {
        "document_type": "phase3c_stage1_3_evidence_scope_diagnostic",
        "schema_version": "1", "status": "COMPLETED",
        "pilot_run_id": bundle["pilot_run_id"],
        "bindings": {
            "extraction_bundle_sha256": extraction_bundle_sha256(bundle),
            "stage1_2_review_sha256": _canonical_sha256(review),
            "source_sha256": bundle["source"]["sha256"],
            "decisions_sha256": "fixture",
        },
        "context_policy": "same_page_or_immediate_adjacent_boundary_with_500_char_radius",
        "drop_diagnostics": [],
        "cross_page_diagnostics": [{
            "claim_id": claim["claim_id"],
            "original_claim": claim["statement"],
            "original_evidence_excerpt": claim["evidence_excerpt"],
            "original_locator": locator,
            "original_human_decision": "KEEP_NEEDS_REVIEW",
            "cross_page_verified": True,
            "pages": ["PAGE:2", "PAGE:3"],
            "semantic_support": "complete",
            "evidence_spans": [
                {"locator": "PAGE:2", "text": "First half"},
                {"locator": "PAGE:3", "text": "second half."},
            ],
            "rationale": "Exact Evidence continues on the adjacent page.",
        }],
        "immutability": {
            "stage1_2_decisions_unchanged": True, "claim_ids_unchanged": True,
            "raw_claim_text_unchanged": True, "raw_evidence_unchanged": True,
        },
    }
    bundle_path = cfg.root / "stage1" / "bundle.json"
    review_path = cfg.root / "stage1" / "review.json"
    diagnostic_path = cfg.root / "stage1" / "diagnostic.json"
    write_json(bundle_path, bundle)
    write_json(review_path, review)
    write_json(diagnostic_path, diagnostic)

    result = run_stage1_4_evidence_contract_v2(
        bundle_path, review_path, diagnostic_path, source,
        output_dir=cfg.root / "stage1_4", production_db_path=cfg.db_path,
    )
    item = result["contract"]["claims"][1]
    assert item["v2_support_status"] == "SUPPORTED"
    assert item["support_mode"] == "ORDERED_SPANS"
    assert item["stage1_2_decision"] == "KEEP_NEEDS_REVIEW"
    assert item["original_locator"]["status"] == "unresolved"
    assert item["original_locator"].get("locator") is None
    assert item["evidence_spans"] == [
        {"order": 1, "locator": "PAGE:2", "text": "First half", "exact_source_text": True},
        {"order": 2, "locator": "PAGE:3", "text": "second half.", "exact_source_text": True},
    ]


@pytest.mark.parametrize(("category", "required_text"), [
    ("evidence_quote_verbatim_preservation", "evidence_excerpt 必须逐字复制输入原文中的一个连续片段"),
    ("claim_atomicity", "不同业务主体、时间范围、确定性级别、所需 Evidence span"),
    ("atomicity_unsupported_clause", "同一局部 Evidence scope"),
    ("attribution_preservation", "归因只写入 attributed_to"),
    ("conditionality_preservation", "修饰词必须继续附着于原本修饰的命题"),
    ("entity_inference_prevention", "实体匹配观察不等于改写 Claim 的许可"),
    ("technical_term_inference_prevention", "不得依据领域知识静默纠正为已知术语"),
    ("scope_invention_prevention", "不得扩大或替换 Claim 的对象"),
])
def test_stage1_4_prompt_minimal_repair_is_explicit(category, required_text):
    status = phase3c_prompt_repair_status()
    assert status["passed"] is True
    assert status["categories"][category] is True
    assert required_text in SOURCE_ANALYSIS_SYSTEM


@pytest.mark.parametrize(("source", "excerpt"), [
    ("他说，那个，这个方案可行。", "他说，这个方案可行。"),
    ("原文没有新增判断。", "原文新增一个判断。"),
    ("大陆公司主要做无源器件。", "大陆发言人主要做无源器件。"),
    ("清香甘的这种技术仍需验证。", "硅光技术仍需验证。"),
])
def test_gate_b_evidence_lexical_changes_are_rejected(source, excerpt):
    full_text = f"[[PAGE:1]]\n{source}"
    locator = resolve_pdf_evidence_locator(full_text, excerpt, "[[PAGE:1]]")

    assert locator["status"] == "unresolved"


def test_gate_b_speaker_boundary_deletion_is_rejected():
    full_text = (
        "[[PAGE:1]]\n价格不会大幅下降。\n\n"
        "发言人 24:53\n\n偶尔可能小幅年降。"
    )
    fabricated = "价格不会大幅下降。偶尔可能小幅年降。"

    locator = resolve_pdf_evidence_locator(full_text, fabricated, "[[PAGE:1]]")

    assert locator["status"] == "unresolved"


def test_gate_b_exact_and_layout_normalized_quotes_are_accepted():
    full_text = "[[PAGE:1]]\n逐字证\n据必须保留。"

    exact = resolve_pdf_evidence_locator(full_text, "逐字证\n据必须保留。", "[[PAGE:1]]")
    layout = resolve_pdf_evidence_locator(full_text, "逐字证据必须保留。", "[[PAGE:1]]")

    assert exact["status"] == "resolved"
    assert exact["match_method"] == "provenance_raw_exact_substring"
    assert layout["status"] == "resolved"
    assert layout["match_method"] == "provenance_pdf_normalized_exact_substring"


def test_gate_b_exact_ordered_cross_page_quote_is_accepted():
    full_text = "[[PAGE:1]]\nFirst half,\n[[PAGE:2]]\nsecond half."
    excerpt = "First half, second half."

    locator = resolve_pdf_evidence_locator(full_text, excerpt, "[[PAGE:1]]")
    spans = _ordered_cross_page_spans(
        {"PAGE:1": "First half,", "PAGE:2": "second half."}, locator, excerpt,
    )

    assert locator["status"] == "unresolved"
    assert locator["reason"] == "cross_page_span"
    assert [item["locator"] for item in spans] == ["PAGE:1", "PAGE:2"]


def test_pilot2_prompt_freeze_fails_before_extraction(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    source = cfg.root / "光互连研究方法与框架20260819.pdf"
    write_pdf(source, [EXCERPT])

    def forbidden(*args, **kwargs):
        raise AssertionError("Analyzer must not start after a prompt-freeze mismatch")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    with pytest.raises(PilotError, match="PILOT_PROMPT_FREEZE_MISMATCH"):
        extract_pilot_source(
            source, cfg, required_prompt_sha256="0" * 64,
        )


def test_pilot2_evidence_draft_is_mechanics_only_deterministic_and_exact(
    tmp_path, monkeypatch,
):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "光互连研究方法与框架20260819.pdf"
    write_pdf(source, [f"{EXCERPT} Context after.", "First half,", "second half."])
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle = copy.deepcopy(stage1["bundle"])
    claim = bundle["claims"][1]
    claim.update({
        "statement": "First half, second half.",
        "evidence_pointer": "[[PAGE:2]]",
        "evidence_excerpt": "First half, second half.",
        "evidence_validated": False,
        "status": "needs_review",
    })
    claim["validation"] = {"evidence_validated": False, "errors": ["evidence_excerpt_not_found"]}
    claim["structured"]["validation"] = copy.deepcopy(claim["validation"])
    bundle_path = cfg.root / "stage1" / "pilot2_bundle.json"
    write_json(bundle_path, bundle)
    rebound = rebind_stage1_evidence_locators(
        bundle_path, source, output_dir=cfg.root / "rebound",
        production_db_path=cfg.db_path,
    )

    first = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]), Path(rebound["review_draft_path"]), source,
        output_dir=cfg.root / "draft-a", production_db_path=cfg.db_path,
    )
    second = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]), Path(rebound["review_draft_path"]), source,
        output_dir=cfg.root / "draft-b", production_db_path=cfg.db_path,
    )

    assert first["production_unchanged"] is True
    assert first["inputs_unchanged"] is True
    assert first["metrics"]["evidence_deterministically_bound"] == 2
    assert first["metrics"]["single_page_locator_bound"] == 1
    assert first["metrics"]["cross_page_exact_spans"] == 1
    assert first["metrics"]["human_decision_counts"] == {
        "KEEP": 0, "DROP": 0, "KEEP_NEEDS_REVIEW": 0, "PENDING": 2,
    }
    excerpt, cross_page = first["draft"]["claims"]
    assert excerpt["original_evidence_excerpt"] == EXCERPT
    assert excerpt["evidence_mechanics_status"] == "CONTEXT_AVAILABLE"
    assert excerpt["bounded_context_candidates"][0]["text"] == "Context after."
    assert cross_page["evidence_mechanics_status"] == "ORDERED_SPAN_BOUND"
    assert cross_page["original_locator"]["status"] == "unresolved"
    assert cross_page["original_locator"].get("locator") is None
    assert cross_page["evidence_spans"] == [
        {"order": 1, "locator": "PAGE:2", "text": "First half,", "exact_source_text": True},
        {"order": 2, "locator": "PAGE:3", "text": "second half.", "exact_source_text": True},
    ]
    assert all(item["human_decision"] == "PENDING" for item in first["draft"]["claims"])
    assert all("v2_support_status" not in item for item in first["draft"]["claims"])
    for key in ("draft_path", "review_surface_path", "metrics_path"):
        assert Path(first[key]).read_bytes() == Path(second[key]).read_bytes()


def test_pilot2_fails_closed_on_nonidentical_exact_name_sources(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    first = cfg.root / "search" / "a" / "光互连研究方法与框架20260819.pdf"
    second = cfg.root / "search" / "b" / "光互连研究方法与框架20260819.pdf"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    write_pdf(first, ["first"])
    write_pdf(second, ["second"])

    def forbidden(*args, **kwargs):
        raise AssertionError("ambiguous Source must fail before extraction")

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", forbidden)
    with pytest.raises(PilotError, match="PILOT2_SOURCE_AMBIGUOUS"):
        run_pilot2_real_extraction(
            first, cfg.root / "search", cfg.root / "missing-bundle.json",
            cfg.root / "missing-pilot1.pdf", cfg,
        )


def test_pilot2_orchestration_runs_one_extraction_and_stops_at_pending_review(
    tmp_path, monkeypatch,
):
    cfg, _ = make_config(tmp_path)

    class CountingAnalyzer(StubAnalyzer):
        calls = 0

        def analyze_source(self, filename, text, mode):
            type(self).calls += 1
            return super().analyze_source(filename, text, mode)

    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", CountingAnalyzer)
    pilot1_source = cfg.root / "TGV玻璃专家交流.pdf"
    write_pdf(pilot1_source, [EXCERPT, "Pilot one context."])
    pilot1_stage1 = extract_pilot_source(
        pilot1_source, cfg, output_dir=cfg.root / "pilot1-stage1",
    )
    pilot1_rebound = rebind_stage1_evidence_locators(
        Path(pilot1_stage1["extraction_bundle_path"]), pilot1_source,
        output_dir=cfg.root / "pilot1-rebound", production_db_path=cfg.db_path,
    )
    CountingAnalyzer.calls = 0

    pilot2_source = cfg.root / "search" / "光互连研究方法与框架20260819.pdf"
    pilot2_source.parent.mkdir(parents=True)
    write_pdf(pilot2_source, [f"{EXCERPT} Pilot two context."])

    def forbidden(*args, **kwargs):
        raise AssertionError("Pilot #2 invoked a forbidden side-effect path")

    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.proposals.ProposalManager", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_proposal", forbidden)
    monkeypatch.setattr("pro_a.receipts.write_receipt", forbidden)

    result = run_pilot2_real_extraction(
        pilot2_source,
        cfg.root / "search",
        Path(pilot1_rebound["rebound_bundle_path"]),
        pilot1_source,
        cfg,
        production_db_path=cfg.db_path,
    )

    assert result["status"] == "PASS"
    assert CountingAnalyzer.calls == 1
    assert result["production_unchanged"] is True
    assert result["pilot1_history_unchanged"] is True
    assert result["pilot1_rerun"] is False
    assert result["prompt_status"] == phase3c_prompt_repair_status()
    assert result["extraction"]["bundle"]["model"]["prompt"]["frozen_before_extraction"] is True
    assert all(
        item["human_decision"] == "PENDING"
        for item in result["evidence"]["draft"]["claims"]
    )
    assert result["comparison"]["comparison"]["no_quality_verdict"] is True
    assert set(result["comparison"]["comparison"]["pilot2_semantic_metrics"].values()) == {
        "PENDING_HUMAN_REVIEW"
    }
    for path in (
        result["extraction"]["extraction_bundle_path"],
        result["rebound"]["review_draft_path"],
        result["evidence"]["draft_path"],
        result["evidence"]["metrics_path"],
        result["comparison"]["comparison_path"],
    ):
        assert Path(path).exists()


def test_pilot2_gate_a_classifies_exact_layout_recovery_cross_page_and_drift(
    tmp_path, monkeypatch,
):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot2-gate-a.pdf"
    write_pdf(source, [
        "Raw quote.\nLayout quote,\nwith break.\nGlobal exact.",
        "Cross first",
        "cross second.",
        "optical module by Huawei in 2024.",
    ])
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    bundle = copy.deepcopy(stage1["bundle"])
    template = copy.deepcopy(bundle["claims"][0])

    def claim(claim_id, pointer, excerpt):
        item = copy.deepcopy(template)
        item.update({
            "claim_id": claim_id,
            "statement": excerpt,
            "evidence_pointer": pointer,
            "evidence_excerpt": excerpt,
            "evidence_validated": False,
            "status": "needs_review",
            "validation": {"evidence_validated": False, "errors": []},
        })
        item["structured"] = copy.deepcopy(item.get("structured") or {})
        item["structured"]["validation"] = copy.deepcopy(item["validation"])
        return item

    bundle["claims"] = [
        claim("C_RAW", "[[PAGE:1]]", "Raw quote."),
        claim("C_LAYOUT", "[[PAGE:1]]", "Layout quote, with break."),
        claim("C_GLOBAL", "[[PAGE:2]]", "Global exact."),
        claim("C_CROSS", "[[PAGE:2]]", "Cross first cross second."),
        claim("C_DRIFT", "[[PAGE:4]]", "modulator chip by ZTE in 2025."),
        claim("C_UNKNOWN", "[[PAGE:4]]", "No deterministic anchor at all."),
    ]
    original_path = cfg.root / "stage1" / "original.json"
    write_json(original_path, bundle)
    rebound = rebind_stage1_evidence_locators(
        original_path, source, output_dir=cfg.root / "rebound", production_db_path=cfg.db_path,
    )
    evidence = build_pilot2_evidence_support_draft(
        Path(rebound["rebound_bundle_path"]), Path(rebound["review_draft_path"]), source,
        output_dir=cfg.root / "evidence", production_db_path=cfg.db_path,
    )
    input_hashes = {
        path: sha256_file(path)
        for path in (original_path, Path(rebound["rebound_bundle_path"]), Path(evidence["draft_path"]), source)
    }

    result = run_pilot2_gate_a_quote_fidelity(
        original_path,
        Path(rebound["rebound_bundle_path"]),
        Path(evidence["draft_path"]),
        source,
        output_dir=cfg.root / "gate-a",
        production_db_path=cfg.db_path,
    )

    assert result["status"] == "PASS"
    assert result["metrics"]["invariants"]["all_claims_classified"] is True
    assert result["metrics"]["invariants"]["claim_count_matches_expected"] is False
    assert result["metrics"]["fidelity_counts"]["EXACT_SOURCE_MATCH"] == 1
    assert result["metrics"]["fidelity_counts"]["LAYOUT_NORMALIZED_EXACT_MATCH"] == 1
    assert result["metrics"]["fidelity_counts"]["PROVENANCE_MISMATCH_RECOVERED"] == 1
    assert result["metrics"]["fidelity_counts"]["EXACT_ORDERED_CROSS_PAGE_SPAN"] == 1
    assert result["metrics"]["fidelity_counts"]["QUOTE_DRIFT"] == 1
    assert result["metrics"]["fidelity_counts"]["UNRESOLVED_SOURCE_BINDING"] == 1
    drift = next(item for item in result["claims"] if item["claim_id"] == "C_DRIFT")
    assert drift["fidelity_status"] == "QUOTE_DRIFT"
    assert drift["technical_term_difference"] is True
    assert drift["entity_name_difference"] is True
    assert drift["number_date_difference"] is True
    assert drift["diagnostic_diff"]
    assert all(
        sha256_file(path) == digest for path, digest in input_hashes.items()
    )
    assert result["production_unchanged"] is True
    assert all(item["human_decision"] == "PENDING" for item in result["claims"])


def test_controlled_reextraction_freezes_gate_b_path_and_uses_mechanical_flags(tmp_path):
    cfg, _ = make_config(tmp_path)
    freeze = _controlled_reextraction_freeze(cfg)

    assert freeze["gate_b_attribution_repair_active"] is True
    assert freeze["gate_b_quote_verbatim_rule_active"] is True
    assert freeze["gate_b_atomicity_rule_active"] is True
    assert freeze["extraction_configuration"]["configured_request_model"] == "deepseek-chat"
    assert set(freeze["code_file_sha256"]) == {
        "src/pro_a/analyzer.py", "src/pro_a/prompts.py", "src/pro_a/corpus_pilot.py",
    }

    diagnostics = _controlled_reextraction_mechanical_diagnostics(
        {
            "claims": [
                {
                    "claim_id": "C1",
                    "statement": "发言人产能预计提升。",
                    "evidence_excerpt": "龙头公司产能可能提升。",
                    "structured": {"statement_normalization": {
                        "method": "deterministic_attribution_prefix_or_company_replacement",
                    }},
                },
                {
                    "claim_id": "C2",
                    "statement": "袁杰（可能指新易盛）作出判断。",
                    "evidence_excerpt": "袁杰作出判断。",
                },
            ],
        },
        {
            "claims": [
                {"claim_id": "C1", "entity_name_difference": False, "technical_term_difference": True},
                {"claim_id": "C2", "entity_name_difference": True, "technical_term_difference": False},
            ],
        },
        {
            "claims": [
                {"claim_id": "C1", "evidence_spans": [{"order": 1}, {"order": 2}]},
                {"claim_id": "C2", "evidence_spans": []},
            ],
        },
    )

    assert diagnostics["deterministic_company_to_speaker_mutations"]["claim_ids"] == ["C1"]
    assert diagnostics["known_old_mutation_recurrence"] == "YES"
    assert diagnostics["speaker_business_qa_flags"]["capacity"]["claim_ids"] == ["C1"]
    assert diagnostics["entity_inference_mechanical_flags"]["claim_ids"] == ["C2"]
    assert diagnostics["technical_term_inference_mechanical_flags"]["claim_ids"] == ["C1"]
    assert diagnostics["conditionality_qa_flags"]["count"] == 2
    assert diagnostics["pre_review_atomicity_candidates"]["multi_subject_review_candidates"] == "PENDING_HUMAN_REVIEW"
    assert diagnostics["pre_review_atomicity_candidates"]["multi_evidence_span_review_candidates"]["claim_ids"] == ["C1"]


def _pilot2_human_review_inputs(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setattr("pro_a.corpus_pilot.Analyzer", StubAnalyzer)
    source = cfg.root / "pilot2-review.pdf"
    write_pdf(source, [EXCERPT])
    stage1 = extract_pilot_source(source, cfg, output_dir=cfg.root / "stage1")
    template = copy.deepcopy(stage1["bundle"]["claims"][0])

    def claim(claim_id, statement, excerpt):
        item = copy.deepcopy(template)
        item.update({
            "claim_id": claim_id,
            "statement": statement,
            "evidence_excerpt": excerpt,
        })
        return item

    bundle = copy.deepcopy(stage1["bundle"])
    bundle["claims"] = [
        claim("C_CURRENT", "Current supported.", "Current evidence."),
        claim("C_DRIFT", "Drift supported.", "Drift evidence."),
        claim("C_UNSUPPORTED", "Unsupported claim.", "Unsupported evidence."),
        claim("C_CROSS", "Cross-page supported.", "Cross evidence."),
        claim("C_CONTEXT", "Context supported.", "Context evidence."),
    ]
    bundle["model"]["usage"] = {"total_tokens": 1000}
    bundle_path = cfg.root / "original.json"
    write_json(bundle_path, bundle)
    evidence = {
        "pilot_run_id": bundle["pilot_run_id"],
        "claims": [
            {"claim_id": item["claim_id"], "original_evidence_excerpt": item["evidence_excerpt"]}
            for item in bundle["claims"]
        ],
    }
    evidence_path = cfg.root / "evidence.json"
    write_json(evidence_path, evidence)
    gate_statuses = [
        "EXACT_SOURCE_MATCH",
        "QUOTE_DRIFT",
        "LAYOUT_NORMALIZED_EXACT_MATCH",
        "EXACT_ORDERED_CROSS_PAGE_SPAN",
        "LAYOUT_NORMALIZED_EXACT_MATCH",
    ]
    gate = {
        "document_type": "phase3c_pilot2_gate_a_quote_fidelity",
        "pilot_run_id": bundle["pilot_run_id"],
        "source_sha256": bundle["source"]["sha256"],
        "claims": [
            {
                "claim_id": item["claim_id"],
                "fidelity_status": status,
                "primary_drift_category": "transcript_cleanup" if status == "QUOTE_DRIFT" else None,
            }
            for item, status in zip(bundle["claims"], gate_statuses)
        ],
    }
    gate_path = cfg.root / "gate.json"
    write_json(gate_path, gate)
    rows = [
        ("C_CURRENT", "SUPPORTED", "NONE", [], False, False,
         "CURRENT_CONTRACT_ADMISSIBLE", "KEEP", "EXCERPT_ONLY", False),
        ("C_DRIFT", "SUPPORTED", "NONE", [], False, False,
         "EVIDENCE_QUOTE_DRIFT_BLOCKED", "KEEP_NEEDS_REVIEW",
         "QUOTE_DRIFT_SOURCE_REGION", True),
        ("C_UNSUPPORTED", "UNSUPPORTED", "TRUE_OVERREACH", [], True, True,
         "CURRENT_CONTRACT_ADMISSIBLE", "DROP", "EXCERPT_ONLY", False),
        ("C_CROSS", "SUPPORTED", "NONE", [], False, False,
         "V2_ORDERED_SPAN_REQUIRED", "KEEP_NEEDS_REVIEW", "CROSS_PAGE", False),
        ("C_CONTEXT", "SUPPORTED", "NONE", [], False, False,
         "V2_CONTEXT_REQUIRED", "KEEP_NEEDS_REVIEW", "BOUNDED_CONTEXT", False),
    ]
    decisions = {
        "document_type": "phase3c_pilot2_human_review_decisions",
        "schema_version": "1",
        "pilot_run_id": bundle["pilot_run_id"],
        "source_sha256": bundle["source"]["sha256"],
        "generalization_verdict": "PASS_WITH_REPAIR",
        "generalization_rationale": "Semantic quality passes in the fixture with explicit contract repairs.",
        "claims": [],
    }
    for (
        claim_id, support, category, secondary, atomicity, material, admissibility,
        decision, review_mode, quote_drift,
    ) in rows:
        decisions["claims"].append({
            "claim_id": claim_id,
            "semantic_support": support,
            "semantic_failure_category": category,
            "secondary_failure_categories": secondary,
            "atomicity_issue": atomicity,
            "atomicity_material_failure": material,
            "evidence_admissibility": admissibility,
            "human_decision": decision,
            "review_mode": review_mode,
            "quote_drift": quote_drift,
            "quote_drift_category": "transcript_cleanup" if quote_drift else None,
            "nearest_deterministic_source_region_reference": "gate#C_DRIFT" if quote_drift else None,
            "rationale": f"Explicit fixture review for {claim_id}.",
        })
    decisions_path = cfg.root / "annotations.json"
    write_json(decisions_path, decisions)
    return cfg, bundle, gate, decisions, bundle_path, evidence_path, gate_path, decisions_path


def test_pilot2_human_review_closes_two_axes_without_side_effects(tmp_path, monkeypatch):
    (
        cfg, bundle, gate, _, bundle_path, evidence_path, gate_path, decisions_path,
    ) = _pilot2_human_review_inputs(tmp_path, monkeypatch)
    before = sha256_file(cfg.db_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Human review invoked a forbidden side-effect path")

    monkeypatch.setattr("pro_a.pipeline.IngestionPipeline", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager", forbidden)
    result = close_pilot2_human_review(
        bundle_path,
        evidence_path,
        gate_path,
        decisions_path,
        output_dir=cfg.root / "review",
        production_db_path=cfg.db_path,
    )

    assert result["status"] == "READY"
    assert result["metrics"]["claims_reviewed"] == 5
    assert result["metrics"]["decision_counts"] == {
        "KEEP": 1, "DROP": 1, "KEEP_NEEDS_REVIEW": 3, "PENDING": 0,
    }
    assert result["metrics"]["semantic_counts"] == {
        "SUPPORTED": 4, "UNSUPPORTED": 1, "AMBIGUOUS": 0,
    }
    assert result["metrics"]["quote_drift_semantic_outcomes"] == {
        "total": 1, "SUPPORTED": 1, "UNSUPPORTED": 0, "AMBIGUOUS": 0,
    }
    assert result["metrics"]["evidence_admissibility_counts"]["V2_CONTEXT_REQUIRED"] == 1
    assert result["metrics"]["evidence_admissibility_counts"]["V2_ORDERED_SPAN_REQUIRED"] == 1
    assert result["metrics"]["EVIDENCE_QUOTE_VERBATIM_PROMPT_REPAIR_CONFIRMED"] is True
    assert result["metrics"]["llm_calls_added"] == 0
    assert result["production_unchanged"] is True
    assert sha256_file(cfg.db_path) == before
    assert [item["claim_id"] for item in result["claims"]] == [
        item["claim_id"] for item in bundle["claims"]
    ]
    assert [item["gate_a_fidelity_status"] for item in result["claims"]] == [
        item["fidelity_status"] for item in gate["claims"]
    ]
    assert all(
        item["original_claim"] == original["statement"]
        and item["immutable_evidence_excerpt"] == original["evidence_excerpt"]
        for item, original in zip(result["claims"], bundle["claims"])
    )
    for key in ("decisions_artifact_path", "ready_path", "report_path", "metrics_path"):
        assert Path(result[key]).exists()


@pytest.mark.parametrize(("claim_id", "field", "value", "error"), [
    ("C_DRIFT", "human_decision", "KEEP", "DECISION_INCONSISTENT"),
    ("C_UNSUPPORTED", "human_decision", "KEEP_NEEDS_REVIEW", "DECISION_INCONSISTENT"),
    ("C_CROSS", "human_decision", "KEEP", "DECISION_INCONSISTENT"),
    ("C_CONTEXT", "human_decision", "KEEP", "DECISION_INCONSISTENT"),
    ("C_CURRENT", "original_claim", "Changed claim.", "CLAIM_MUTATED"),
    ("C_CURRENT", "immutable_evidence_excerpt", "Changed evidence.", "EVIDENCE_MUTATED"),
    ("C_CURRENT", "gate_a_fidelity_status", "QUOTE_DRIFT", "GATE_A_STATUS_CHANGED"),
])
def test_pilot2_human_review_rejects_inconsistent_or_mutated_decisions(
    tmp_path, monkeypatch, claim_id, field, value, error,
):
    (
        cfg, _, _, decisions, bundle_path, evidence_path, gate_path, _,
    ) = _pilot2_human_review_inputs(tmp_path, monkeypatch)
    selected = next(item for item in decisions["claims"] if item["claim_id"] == claim_id)
    selected[field] = value
    decisions_path = cfg.root / "mutated-annotations.json"
    write_json(decisions_path, decisions)

    with pytest.raises(PilotError, match=error):
        close_pilot2_human_review(
            bundle_path,
            evidence_path,
            gate_path,
            decisions_path,
            output_dir=cfg.root / "review",
            production_db_path=cfg.db_path,
        )
