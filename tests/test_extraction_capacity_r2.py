"""Selected 4k policy identity and frozen-input boundaries; synthetic/offline only."""
import copy
import json

import pytest

from pro_a import analyzer as module
from pro_a.analyzer import Analyzer
from pro_a.cloud_contract import operation_contract
from pro_a.workbench.cloud_jobs import CloudProfile
from stability_helpers import make_config
from test_cloud_operation_adapter_binding import setup_run, jobs, advance
from test_extraction_capacity import assert_plan


BASELINE = "761b7dab7a17d5eb02c08dfb324c532a00252039"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr("requests.sessions.Session.request", lambda *a, **k: pytest.fail("External network forbidden"))


def test_selected_policy_tuple_and_unchanged_operation_contracts(monkeypatch):
    monkeypatch.setenv("PRO_A_EXTRACTION_MAX_CHARS", "5000")
    assert (module.EXTRACTION_CAPACITY_POLICY_VERSION, module.FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS,
            module.INITIAL_EXTRACTION_PLANNER_VERSION) == (
                "source-analysis-capacity-v2", 4000, "PHASE3E2SL6_PRECALL_PARTITION_V3")
    profile = CloudProfile("deepseek", "deepseek-flash")
    assert (profile.max_output_tokens, profile.max_total_tokens) == (8192, 20000)
    identity = profile.public_identity()
    assert identity["operation_output_budget_policy_version"] == "operation-output-budget-v1"
    for operation, output, adapter in (
        ("SOURCE_ANALYSIS_PIECE", 12000, "whole-piece-lexical-tool-source-analysis-adapter-v1"),
        ("SEMANTIC_DECOMPOSITION", 8192, "semantic-backend-adapter-v2"),
    ):
        assert identity["operation_output_budgets"][operation] == {"max_output_tokens": output, "max_total_tokens": 20000}
        assert profile.adapter_for_operation(operation) == adapter
        assert operation_contract(operation)["thinking_mode"] == "disabled"
        assert operation_contract(operation)["thinking_policy_version"] == "structured-json-reasoning-v1"


def test_baseline_and_selected_policy_change_piece_and_prompt_hashes(tmp_path, monkeypatch):
    cfg, db = make_config(tmp_path)
    cfg.llm.max_chunk_chars = 22000
    analyzer = Analyzer(cfg, db)
    text = "[[PARA:1]] " + "Alpha中2026增长42%。" * 800
    selected = assert_plan(analyzer, text, 4000)
    selected_before = copy.deepcopy(selected.artifact)
    with monkeypatch.context() as old:
        old.setattr(module, "EXTRACTION_CAPACITY_POLICY_VERSION", "source-analysis-capacity-v1")
        old.setattr(module, "FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS", 5000)
        old.setattr(module, "INITIAL_EXTRACTION_PLANNER_VERSION", "PHASE3E2SL6_PRECALL_PARTITION_V2")
        baseline = assert_plan(analyzer, text, 5000)
    assert selected.artifact == selected_before
    assert selected.plan_sha256 != baseline.plan_sha256
    assert [p.source_piece.source_sha256 for p in selected.pieces] != [p.source_piece.source_sha256 for p in baseline.pieces]
    assert [p["user_prompt_sha256"] for p in selected.artifact["pieces"]] != [p["user_prompt_sha256"] for p in baseline.artifact["pieces"]]
    assert selected.artifact["planning_inputs"] == baseline.artifact["planning_inputs"]


def test_new_plan_flows_into_inputs_and_job_checkpoints_without_rewriting_old_rows(tmp_path, monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(module, "EXTRACTION_CAPACITY_POLICY_VERSION", "source-analysis-capacity-v1")
        old.setattr(module, "FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS", 5000)
        old.setattr(module, "INITIAL_EXTRACTION_PLANNER_VERSION", "PHASE3E2SL6_PRECALL_PARTITION_V2")
        value = setup_run(tmp_path, monkeypatch)
        from test_llm import FakeResponse
        from test_structured_json_reasoning_policy import completion
        old.setattr("pro_a.llm.requests.post", lambda *a, **k: FakeResponse(completion(0, content="{")))
        assert advance(value)["state"] == "BLOCKED"
    service = value["service"]
    def inputs(run_id):
        with service.store.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM source_cloud_inputs WHERE processing_run_id=? ORDER BY ordinal',(run_id,))]
    before=inputs(value['run_id'])
    def input_document(binding):
        return json.loads((value["config"].artifact_root / binding["artifact_relative"]).read_text(encoding="utf-8"))
    old_document = input_document(before[0])
    created = service.start(value["source"]["source_id"], idempotency_key="r2-new-capacity-synthetic-0001",
                            reprocess_reason="Synthetic selected capacity identity")["run"]
    service.advance_once(worker_id="capacity-r2", processing_run_id=created["processing_run_id"], provider=None)
    current = inputs(created['processing_run_id'])
    new_document = input_document(current[0])
    assert new_document["payload"]["native"]["initial_plan_sha256"] != old_document["payload"]["native"]["initial_plan_sha256"]
    for row, document in ((before[0], old_document), (current[0], new_document)):
        assert document["payload"]["native"]["initial_plan_sha256"] == document["checkpoint"]["plan_sha256"]
        assert json.loads(row["checkpoint_json"])["plan_sha256"] == document["checkpoint"]["plan_sha256"]
    assert current[0]["sha256"] != before[0]["sha256"]
    assert current[0]["artifact_id"] != before[0]["artifact_id"]
    assert inputs(value['run_id']) == before and input_document(before[0]) == old_document
    assert value["http_calls"] == []


def test_capacity_and_schema12_surfaces_fail_closed_against_capacity_baseline():
    from pro_a.workbench.retry_compatibility import _execution_surface_comparison
    _execution_surface_comparison.cache_clear()
    result = _execution_surface_comparison("native", BASELINE)
    assert result["compatible"] is False and result["reason"] == "SEMANTIC_SURFACE_CHANGED"
    # Schema12 acceptance now also changes the protected cloud surface. Neither
    # dormant persistence nor unchanged provider contracts authorize old retries.
    cloud = _execution_surface_comparison("cloud", BASELINE)
    assert cloud["compatible"] is False and cloud["reason"] == "SEMANTIC_SURFACE_CHANGED"
