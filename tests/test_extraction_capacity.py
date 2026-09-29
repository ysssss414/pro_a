"""Offline capacity policy, lossless planning, and dense dual-adapter qualification."""
import collections
import copy
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from pro_a import analyzer as analyzer_module
from pro_a.analyzer import Analyzer
from pro_a.cloud_contract import (
    DeterministicFakeProvider, SOURCE_ANALYSIS_OPERATION, adapter_version_for_operation,
)
from pro_a.operational_ingestion import plan_external_source_analysis
from pro_a.semantic_decomposition import SEMANTIC_DECOMPOSITION_USER
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.source_operations import MAX_STAGE1_JOBS_PER_RUN
from stability_helpers import make_config
from test_cloud_operation_adapter_binding import advance, jobs, setup_run


BASELINE = "bc151f3131dd6e9343937f3c5db9ddb7ed8e748a"
CAP = 5_000


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("External network is forbidden in capacity qualification")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def assert_plan(analyzer, text, cap):
    first = analyzer.plan_initial_extraction(
        "capacity-fixture.txt", text, "deep", adaptive_retry_policy="forbid")
    second = analyzer.plan_initial_extraction(
        "capacity-fixture.txt", text, "deep", adaptive_retry_policy="forbid")
    assert first.artifact == second.artifact and first.plan_sha256 == second.plan_sha256
    assert first.effective_max_chars == cap
    assert "".join(p.source_piece.source_text for p in first.pieces) == text
    assert [p.source_start for p in first.pieces] == [0, *[p.source_end for p in first.pieces[:-1]]]
    assert first.pieces[-1].source_end == len(text)
    assert max(len(p.source_piece.source_text) for p in first.pieces) <= cap
    assert first.artifact["coverage"] == {
        "source_chars": len(text), "planned_chars": len(text),
        "ordered_exact_reconstruction": True, "omitted_chars": 0, "duplicated_chars": 0,
    }
    assert {loc for p in first.pieces for loc in p.locators} == set(
        Analyzer._piece_locators(text, 0, len(text)))
    assert all(p.locators == Analyzer._piece_locators(text, p.source_start, p.source_end)
               for p in first.pieces)
    assert [p.scoped_node_ids for p in first.pieces] == [p.scoped_node_ids for p in second.pieces]
    assert all(p.scoped_node_catalog == tuple(analyzer._node_catalog_for_text(p.source_piece.source_text))
               for p in first.pieces)
    assert first.artifact["planning_inputs"]["model_response_consumed"] is False
    assert first.artifact["partition_policy"]["response_time_recovery"] == "FORBIDDEN"
    return first


@pytest.mark.parametrize("cap", [4000, 5000, 6000])
def test_candidate_matrix_lossless_deterministic_catalog_and_locators(tmp_path, monkeypatch, cap):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22_000
    alpha = db.add_node("Alpha", "Product")
    beta = db.add_node("Beta", "Technology")
    text = "".join(f"[[PARA:{i}]] Alpha与Beta增长{i}%；" + "Alpha Beta 2026 产能需求。" * 14 + "\n"
                   for i in range(1, 66))
    analyzer = Analyzer(cfg, db)
    monkeypatch.setattr(analyzer.llm, "json", lambda *a: pytest.fail("Planning invoked a model"))
    # Qualification-only substitution; production has one constant and no new knob.
    monkeypatch.setattr(analyzer_module, "FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS", cap)
    plan = assert_plan(analyzer, text, cap)
    assert len(plan.pieces) > 1
    assert all(set(p.scoped_node_ids) == {alpha, beta} for p in plan.pieces)


@pytest.mark.parametrize("length", [CAP - 1, CAP, CAP + 1, 2 * CAP])
@pytest.mark.parametrize("alphabet", ["x", "中", "Alpha产能2026增长42%"])
def test_selected_cap_edges_and_unbroken_paragraph(tmp_path, length, alphabet):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22_000
    text = (alphabet * (length // len(alphabet) + 1))[:length]
    plan = assert_plan(Analyzer(cfg, db), text, CAP)
    assert len(plan.pieces) == (length + CAP - 1) // CAP


@pytest.mark.parametrize("oversized", [False, True])
def test_selected_cap_multilocators_and_oversized_unit(tmp_path, oversized):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22_000
    text = ("[[PARA:1]] " + "跨中English123" * (1000 if oversized else 100)
            + "\n[[PARA:2]] " + "第二段Beta" * 900)
    plan = assert_plan(Analyzer(cfg, db), text, CAP)
    locator_counts = collections.Counter(loc for p in plan.pieces for loc in p.locators)
    if oversized:
        assert locator_counts["PARA:1"] > 1
    assert locator_counts["PARA:2"] >= 1


def test_capacity_and_planner_versions_are_frozen_in_plan_identity(tmp_path, monkeypatch):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22_000
    analyzer = Analyzer(cfg, db)
    text = "density" * 1700
    selected = assert_plan(analyzer, text, CAP)
    assert analyzer_module.EXTRACTION_CAPACITY_POLICY_VERSION == "source-analysis-capacity-v1"
    assert selected.artifact["planner_version"] == "PHASE3E2SL6_PRECALL_PARTITION_V2"
    assert selected.artifact["partition_policy"]["capacity_policy_version"] == "source-analysis-capacity-v1"
    assert selected.artifact["partition_policy"]["frozen_acceptance_safe_max_chars"] == CAP
    monkeypatch.setattr(analyzer_module, "FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS", 10_000)
    historical_capacity = analyzer.plan_initial_extraction(
        "capacity-fixture.txt", text, "deep", adaptive_retry_policy="forbid")
    assert historical_capacity.plan_sha256 != selected.plan_sha256
    monkeypatch.setattr(analyzer_module, "FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS", CAP)
    monkeypatch.setattr(analyzer_module, "INITIAL_EXTRACTION_PLANNER_VERSION", "PHASE3E2SL6_PRECALL_PARTITION_V1")
    old_version = analyzer.plan_initial_extraction(
        "capacity-fixture.txt", text, "deep", adaptive_retry_policy="forbid")
    assert old_version.plan_sha256 != selected.plan_sha256
    monkeypatch.setattr(analyzer_module, "INITIAL_EXTRACTION_PLANNER_VERSION", "PHASE3E2SL6_PRECALL_PARTITION_V2")
    monkeypatch.setattr(analyzer_module, "EXTRACTION_CAPACITY_POLICY_VERSION", "other-policy")
    other_policy = analyzer.plan_initial_extraction(
        "capacity-fixture.txt", text, "deep", adaptive_retry_policy="forbid")
    assert other_policy.plan_sha256 != selected.plan_sha256
    profile = CloudProfile("deepseek", "deepseek-flash")
    assert (profile.max_output_tokens, profile.max_total_tokens) == (8192, 20000)


def test_baseline_native_surface_fails_closed_for_capacity_change():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    _execution_surface_comparison.cache_clear()
    result = _execution_surface_comparison("native", BASELINE)
    assert result["compatible"] is False
    assert result["reason"] == "SEMANTIC_SURFACE_CHANGED"


def test_capacity_changes_runtime_and_context_without_changing_config(tmp_path, monkeypatch):
    import hashlib
    import pro_a.phase4_orchestration as phase4
    from pro_a import processing_context
    from pro_a.workbench.cloud_jobs import runtime_identity
    from pro_a.workbench.config import BoundaryError
    from pro_a.workbench.domains import Domains
    from test_phase43_stage71_shared_core_pending import case

    value = case(tmp_path)
    service = value["service"]
    runtime_identity.cache_clear()
    current = service.jobs.current_runtime()
    baseline_analyzer = subprocess.check_output(
        ["git", "show", BASELINE + ":src/pro_a/analyzer.py"],
        cwd=Path(__file__).resolve().parents[1])
    original_hash = phase4.sha256_file
    with monkeypatch.context() as historical:
        historical.setattr(phase4, "sha256_file", lambda path:
                           hashlib.sha256(baseline_analyzer).hexdigest()
                           if path.name == "analyzer.py" else original_hash(path))
        runtime_identity.cache_clear()
        old = service.jobs.current_runtime()
    runtime_identity.cache_clear()
    assert current["phase4_processing_code_sha256"] != old["phase4_processing_code_sha256"]
    assert current["runtime_sha256"] != old["runtime_sha256"]
    source = {"source_id":"SRC_SYNTHETIC", "source_sha256":"1" * 64,
              "storage_artifact_id":"ART_SYNTHETIC", "validation_json":"{}"}
    old_basis = Domains.pending_basis(source, old, value["source_profile"], value["cloud_profile"])
    new_basis = Domains.pending_basis(source, current, value["source_profile"], value["cloud_profile"])
    assert old_basis["config_sha256"] == new_basis["config_sha256"]
    assert old_basis["model_configuration"] == new_basis["model_configuration"]
    context_args = dict(run_id="RUN_SYNTHETIC", created_at="2026-01-01T00:00:00+00:00",
                        actor="system", reason="Synthetic capacity identity qualification")
    frozen = processing_context.freeze_context(old_basis, **context_args)
    new_context = processing_context.freeze_context(new_basis, **context_args)
    assert frozen["context_sha256"] != new_context["context_sha256"]
    with pytest.raises(BoundaryError, match="PROCESSING_RUN_CONTEXT_DRIFT"):
        processing_context.guard_resume(frozen, new_basis)


def dense_pdf(path):
    from reportlab.pdfgen.canvas import Canvas
    canvas = Canvas(str(path), pagesize=(612, 792))
    for page in range(4):
        canvas.setFont("Helvetica", 8)
        for line in range(40):
            index = page * 40 + line + 1
            text = f"Stage Seven Synthetic Company reported product {index:03d} capacity of {index * 13} units in 2026."
            canvas.drawString(30, 750 - line * 17, text)
        canvas.showPage()
    canvas.save()
    return path


def test_selected_capacity_dense_single_run_dual_adapter_e2e(tmp_path, monkeypatch, record_property):
    import test_cloud_operation_adapter_binding as binding
    path = dense_pdf(tmp_path / "capacity-synthetic.pdf")
    monkeypatch.setattr(binding, "clean_pdf", lambda root: path)
    value = setup_run(tmp_path, monkeypatch)
    service = value["service"]
    run = service.get_run(value["run_id"])
    assert run["state"] == "EXTRACTION_PROCESSING"
    extraction = jobs(value)
    assert 1 < len(extraction) <= value["source_profile"].max_extraction_pieces == 16
    assert all(j["attempt_count"] == 0 for j in extraction)
    assert value["http_calls"] == []
    with service.store.connect() as c:
        row = c.execute("SELECT * FROM source_processing_runs WHERE processing_run_id=?", (value["run_id"],)).fetchone()
        native = service._native_root(row)
        inputs = [dict(r) for r in c.execute("SELECT * FROM source_cloud_inputs WHERE processing_run_id=? ORDER BY ordinal", (value["run_id"],))]
    frozen = plan_external_source_analysis(native / "engine", config_path=value["phase4_config"])
    plan = frozen["plan"]
    assert plan["partition_policy"]["effective_initial_max_chars"] == CAP
    assert plan["partition_policy"]["capacity_policy_version"] == "source-analysis-capacity-v1"
    assert plan["planner_version"] == "PHASE3E2SL6_PRECALL_PARTITION_V2"
    assert plan["coverage"]["ordered_exact_reconstruction"]
    assert plan["piece_count"] == len(extraction)
    prompts = {}
    for item in inputs:
        doc = json.loads((value["config"].artifact_root / item["artifact_relative"]).read_text(encoding="utf-8"))
        payload = doc["payload"]
        assert len(payload["source_text"]) <= CAP
        assert payload["initial_plan_sha256"] == doc["checkpoint"]["plan_sha256"] == plan["initial_extraction_plan_sha256"]
        prompts[payload["user_prompt"]] = payload["source_text"]
    assert len(prompts) == len(extraction)
    calls = []
    response_bytes = []
    response_claims = []

    def post(_url, **kwargs):
        request = kwargs["json"]
        assert request["model"] == "deepseek-flash"
        user = request["messages"][1]["content"]
        assert request["max_tokens"] == (12000 if user in prompts else 8192)
        if user in prompts:
            text = prompts[user]
            output = copy.deepcopy(DeterministicFakeProvider._source_analysis_output(
                SimpleNamespace(payload={"source_text": text})))
            statements = re.findall(r"Stage Seven Synthetic Company reported product \d+ capacity of \d+ units in 2026\.", text)
            assert len(statements) >= 30
            template = output["claims"][0]
            output["claims"] = [{**copy.deepcopy(template), "statement": line, "evidence_excerpt": line}
                                for line in statements]
            response_claims.append(len(statements))
            response_bytes.append(len(json.dumps(output).encode()))
            operation = SOURCE_ANALYSIS_OPERATION
        else:
            prefix, suffix = SEMANTIC_DECOMPOSITION_USER.split("{claims_json}")
            assert user.startswith(prefix)
            claims = json.loads(user[len(prefix):len(user) - len(suffix) if suffix else None])
            output = {"claims": [{
                "parent_claim_id": claim["parent_claim_id"], "ir_status": "VALID",
                "units": [{"predicate_family": "measurement", "modality": "actual",
                           "nature": claim["assigned_nature"] or "fact",
                           "support_evidence_unit_ids": [claim["evidence_units"][0]["evidence_unit_id"]],
                           "coherence_key": "k1", "coherence_type": "INDEPENDENT", "time_scope": "unspecified"}],
            } for claim in claims]}
            operation = "SEMANTIC_DECOMPOSITION"
        calls.append(operation)
        return SimpleNamespace(status_code=200, text="", headers={"x-request-id": "offline-capacity"},
            json=lambda: {"model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output)}}],
                          "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}})

    monkeypatch.setattr("pro_a.llm.requests.post", post)
    semantic = advance(value)
    assert semantic["state"] == "SEMANTIC_PROCESSING", semantic.get("error")
    semantic_rows = [j for j in jobs(value) if j["operation_kind"] == "SEMANTIC_DECOMPOSITION"]
    assert len(semantic_rows) > 1
    final = advance(value)
    assert final["state"] == "HUMAN_REVIEW_REQUIRED", final.get("error")
    assert final["packet_artifact_id"] and final["packet_id"]
    all_jobs = jobs(value)
    assert len(all_jobs) <= MAX_STAGE1_JOBS_PER_RUN
    assert all(j["state"] == "SUCCEEDED" and j["validation_status"] == "PASS" for j in all_jobs)
    assert all(j["provider_adapter_version"] == adapter_version_for_operation(j["operation_kind"])
               for j in all_jobs)
    assert all(j["max_output_tokens"] == (12000 if j["operation_kind"] == SOURCE_ANALYSIS_OPERATION else 8192)
               and j["max_total_tokens"] == 20000 for j in all_jobs)
    assert all(j["attempt_count"] == 1 for j in all_jobs)
    assert len(calls) == len(all_jobs) and min(response_bytes) > 20_000
    assert sum(response_claims) == 160
    persisted_plan = json.loads((native / "engine/extraction/initial_extraction_plan.json").read_text(encoding="utf-8"))
    assert persisted_plan == plan
    with service.store.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM source_processing_runs").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM registered_packets WHERE artifact_kind='REVIEW_PACKET'").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0] == 0
        assert not c.execute("SELECT 1 FROM sqlite_schema WHERE name='extraction_retries'").fetchone()
        assert c.execute("SELECT COUNT(*) FROM cloud_job_results").fetchone()[0] == len(all_jobs)
    assert value["production_writes"] == []
    assert value["config"].knowledge_db.read_bytes() == value["production_before"]
    for key, result in {"extraction_jobs":len(extraction), "semantic_jobs":len(semantic_rows),
                        "extraction_response_bytes":response_bytes, "extraction_claims":response_claims,
                        "packet_registered":True, "provider_network_calls":0}.items():
        record_property(key, result)
