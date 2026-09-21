from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path
from uuid import uuid4

import pytest

from pro_a.analyzer import Analyzer
from pro_a.constants import NODE_TYPES
from pro_a.domain_packs import compose, load_pack
from pro_a.llm import LLMError
from pro_a.prompts import SOURCE_ANALYSIS_NODE_TYPES, SOURCE_ANALYSIS_SYSTEM
from pro_a.query import ReadOnlyQuery
from pro_a.semantic_decomposition import (
    SemanticDecomposer,
    SemanticDecompositionError,
    build_evidence_units,
    partition_semantic_claims,
    semantic_prompt_token_upper_bound,
)
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.domains import prepare_domains
from pro_a.workbench.stage1_scale import (
    LIMITS,
    STAGE1_POLICY_VERSION,
    Stage1ReviewProjection,
    _row_projection,
    prepare_stage1_scale,
    require_stage1_intake,
    set_stage1_intake,
    stage1_capacity,
)
from pro_a.workbench.store import Store
from stability_helpers import make_config
from test_phase43_stage0 import setup_source, start
from workbench_stage7_fixture import stage7_fixture
from pro_a.cloud_contract import DeterministicFakeProvider


ROOT = Path(__file__).resolve().parents[1]


def semantic_inputs(count: int) -> list[dict]:
    rows = []
    for index in range(count):
        claim_id = f"CLM_STAGE1_{index:03d}"
        text = f"Stage 1 parent {index} remains unchanged."
        rows.append({
            "claim_id": claim_id,
            "claim_text": text,
            "evidence_units": build_evidence_units(
                parent_claim_id=claim_id,
                bounded_evidence=text,
                source_locator=f"synthetic:paragraph:{index + 1}",
            ),
            "attribution": "Synthetic source",
            "scope": "",
            "fact_time": "",
            "assigned_nature": "fact",
        })
    return rows


class SemanticBackend:
    backend_name = "STAGE1_OFFLINE_FAKE"

    def __init__(self):
        self.calls: list[list[str]] = []
        self._metadata: dict = {}

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._metadata)

    def decompose_batch(self, claims):
        self.calls.append([claim["claim_id"] for claim in claims])
        self._metadata = {"attempts": [{
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
            "finish_reason": "stop",
        }]}
        return {"claims": [{
            "parent_claim_id": claim["claim_id"],
            "ir_status": "VALID",
            "units": [{
                "predicate_family": "status", "modality": "actual", "nature": "fact",
                "support_evidence_unit_ids": [claim["evidence_units"][0]["evidence_unit_id"]],
                "coherence_key": "stage1", "coherence_type": "INDEPENDENT",
                "time_scope": "current",
            }],
        } for claim in claims]}


@pytest.mark.parametrize("count,expected_sizes", [
    (1, [1]), (8, [8]), (9, [8, 1]), (40, [8, 8, 8, 8, 8]),
    (120, [8] * 15),
])
def test_semantic_partition_and_exact_merge(count, expected_sizes):
    inputs = semantic_inputs(count)
    before = copy.deepcopy(inputs)
    first = partition_semantic_claims(inputs)
    second = partition_semantic_claims(inputs)
    assert first == second
    assert [len(batch) for batch in first] == expected_sizes
    assert [row for batch in first for row in batch] == inputs == before

    backend = SemanticBackend()
    result = SemanticDecomposer(backend).run(inputs)
    expected_ids = [row["claim_id"] for row in inputs]
    assert backend.calls == [[row["claim_id"] for row in batch] for batch in first]
    assert result["input_parent_claim_ids"] == result["output_parent_claim_ids"] == expected_ids
    assert [row["parent_claim_id"] for row in result["results"]] == expected_ids
    assert [row["evidence_units"] for row in result["results"]] == [
        row["evidence_units"] for row in inputs
    ]


def test_semantic_token_boundary_forces_deterministic_split_and_rejects_oversize_parent():
    inputs = semantic_inputs(3)
    one_parent_limit = max(semantic_prompt_token_upper_bound([row]) for row in inputs)
    batches = partition_semantic_claims(inputs, max_input_tokens=one_parent_limit)
    assert [len(batch) for batch in batches] == [1, 1, 1]
    oversized = copy.deepcopy(inputs[0])
    oversized["claim_text"] += "x" * one_parent_limit
    with pytest.raises(SemanticDecompositionError, match="TOKEN_BUDGET_EXCEEDED"):
        partition_semantic_claims([oversized], max_input_tokens=one_parent_limit)


def test_zero_parent_source_skips_semantic_dispatch_and_stops_explicitly(tmp_path):
    case, source = setup_source(tmp_path)
    prepare_stage1_scale(case["config"])
    run_id = start(case, source)
    provider = DeterministicFakeProvider()
    source_output = provider._source_analysis_output

    def no_claim_output(request):
        output = copy.deepcopy(source_output(request))
        output["claims"] = []
        return output

    provider._source_analysis_output = no_claim_output
    result = None
    for _ in range(3):
        advanced = case["service"].advance_once(
            worker_id="stage1-empty-parent-worker", provider=provider,
            processing_run_id=run_id,
        )
        if advanced is not None:
            result = advanced
    assert result["state"] == "BLOCKED", json.dumps(result, sort_keys=True)
    assert result["error"]["code"] == "NATIVE_PACKET_FAILED"
    assert provider.call_count == 1
    assert [job["operation_kind"] for job in result["jobs"]] == [
        "SOURCE_ANALYSIS_PIECE"
    ]


def _node_candidate(node_type: str) -> dict:
    return {
        "canonical_name": "Stage One Company", "primary_type": node_type,
        "aliases": [], "description": "Synthetic Company candidate",
        "suggested_parent_node_ids": [], "reason": "Independent research value",
        "confidence": 0.9, "candidate_kind": "normal",
        "independent_research_value": True,
        "maintenance_rationale": "Track the company across Sources",
        "is_discrete_event": False, "event_time": "", "evidence_excerpt": "",
        "long_term_research_value": True, "cross_source_or_node_value": True,
        "question": "", "importance": "", "what_would_change_my_mind": "",
    }


class StaticAnalysisLLM:
    available = True
    last_call_metadata = {"attempts": []}

    def __init__(self, candidate):
        self.candidate = candidate

    def json(self, _system, _user):
        return {
            "source_metadata": {
                "title": "Stage 1 enum fixture", "author": "", "organization": "",
                "publication_time": "", "source_rank": "A",
                "source_origin_type": "primary", "summary": "Synthetic fixture",
            },
            "node_matches": [], "node_candidates": [copy.deepcopy(self.candidate)],
            "claims": [], "relation_candidates": [], "source_references": [],
        }


def test_company_prompt_schema_alignment_case_fail_closed_and_multi_domain(tmp_path):
    assert SOURCE_ANALYSIS_NODE_TYPES == tuple(NODE_TYPES)
    assert ", ".join(NODE_TYPES) in SOURCE_ANALYSIS_SYSTEM
    assert SOURCE_ANALYSIS_SYSTEM.count("__CANONICAL_NODE_TYPES__") == 0
    assert "Company" in SOURCE_ANALYSIS_NODE_TYPES

    cfg, db = make_config(tmp_path)
    valid = Analyzer(cfg, db)
    valid.llm = StaticAnalysisLLM(_node_candidate("Company"))
    result = valid.analyze_source("company.txt", "Stage One Company is named.", "deep")
    assert [row["primary_type"] for row in result.node_candidates] == ["Company"]

    for unsupported in ("company", "UnknownCompanyType"):
        invalid = Analyzer(cfg, db)
        invalid.llm = StaticAnalysisLLM(_node_candidate(unsupported))
        result = invalid.analyze_source("invalid.txt", "Stage One Company is named.", "deep")
        assert result.node_candidates == []
        assert result.rejected_node_candidates[0]["primary_type"] == unsupported
        assert "unsupported Node Type" in result.rejected_node_candidates[0]["rejection_reason"]

    packs = [
        load_pack(ROOT / "domains" / "ai_hardware"),
        load_pack(ROOT / "domains" / "semiconductor"),
    ]
    combined = compose(packs, "ai_hardware")
    assert combined["identity_scope"] == "GLOBAL_CANONICAL"
    assert combined["disposition"] == "READY"
    assert all("Company" in pack.manifest["supported_node_types"] for pack in packs)


def test_catalog_exact_first_complete_continuation_and_beyond_500_prompt_lookup(tmp_path):
    cfg, db = make_config(tmp_path)
    created = "2026-09-20T00:00:00+00:00"
    with db.connect() as connection:
        nodes = [
            (f"NODE_SUB_{index:04d}", f"Needle candidate {index:04d}", "Company", "", "active", created, created)
            for index in range(600)
        ]
        nodes.extend([
            ("NODE_EXACT_CANONICAL", "ＮＥＥＤＬＥ", "Company", "", "active", created, created),
            ("NODE_EXACT_ALIAS", "ZZZ exact alias owner", "Company", "", "active", created, created),
            ("NODE_AFTER_500", "ZZZ catalog tail", "Company", "", "active", created, created),
        ])
        connection.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)", nodes,
        )
        connection.execute(
            "INSERT INTO node_aliases(alias,node_id) VALUES('needle','NODE_EXACT_ALIAS')"
        )
        connection.execute(
            "INSERT INTO node_aliases(alias,node_id) VALUES('TailMention','NODE_AFTER_500')"
        )

    query = ReadOnlyQuery(cfg.db_path)
    seen: list[str] = []
    cursor = None
    while True:
        page = query.search_nodes_page("needle", limit=73, cursor=cursor)
        seen.extend(row["node_id"] for row in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen[:2] == ["NODE_EXACT_CANONICAL", "NODE_EXACT_ALIAS"]
    assert len(seen) == len(set(seen)) == 602
    assert set(seen) == {"NODE_EXACT_CANONICAL", "NODE_EXACT_ALIAS", *(
        f"NODE_SUB_{index:04d}" for index in range(600)
    )}
    analyzer = Analyzer(cfg, db)
    scoped = analyzer._node_catalog_for_text("A local TailMention is explicit.")
    assert [row["node_id"] for row in scoped] == ["NODE_AFTER_500"]


def _stage1_finished_case(tmp_path):
    case, source = setup_source(tmp_path)
    prepare_stage1_scale(case["config"])
    run_id = start(case, source)
    provider = DeterministicFakeProvider()
    result = None
    for _ in range(3):
        result = case["service"].advance_once(
            worker_id="stage1-test-worker", provider=provider, processing_run_id=run_id
        )
    assert result["state"] == "HUMAN_REVIEW_REQUIRED"
    return case, result


def test_review_projection_snapshot_mutation_and_10000_row_bounded_traversal(tmp_path):
    case, run = _stage1_finished_case(tmp_path)
    artifact_id = run["packet_artifact_id"]
    projection = Stage1ReviewProjection(case["config"])
    first = projection.page(artifact_id, limit=1)
    assert first == projection.page(artifact_id, limit=1)
    assert first["projection_authority"] is False
    old_cursor = first["next_cursor"]

    review = case["service"].artifacts.read(artifact_id)
    workbench = __import__(
        "pro_a.workbench.review_workbench", fromlist=["ReviewWorkbench"]
    ).ReviewWorkbench(case["config"])
    full = workbench.read(artifact_id)
    row = full["review"]["rows"][0]
    native_type = next(
        item["candidate_type"] for item in review["items"]
        if item["candidate_id"] == row["candidate_id"]
    )
    workbench.mutate(artifact_id, "decision", {
        "basis_id": full["review"]["basis_id"], "expected_revision": 0,
        "operation_id": uuid4().hex, "candidate_id": row["candidate_id"],
        "decision": "KEEP" if native_type == "CLAIM" else "CREATE",
        "target_node_id": "", "reviewer": "Stage 1 reviewer",
        "reason": "Stage 1 deterministic projection update",
    }, {"actor": "stage1-operator", "session_id": "stage1-session"})
    with pytest.raises(BoundaryError, match="STALE_REVIEW_CURSOR"):
        projection.page(artifact_id, cursor=old_cursor, limit=1)
    assert projection.page(artifact_id, queue="completed")["filtered_total"] == 1

    basis_id = full["review"]["basis_id"]
    domain_ids = ("ai_hardware", "semiconductor", "robotics", "commercial_space")
    for scale in (100, 1_000, 10_000):
        snapshot_id = f"{scale:064x}"
        with Store(case["config"]).connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM stage1_review_projection_domains WHERE artifact_id=?", (artifact_id,)
            )
            connection.execute(
                "DELETE FROM stage1_review_projection WHERE artifact_id=?", (artifact_id,)
            )
            connection.execute(
                "DELETE FROM stage1_review_projection_meta WHERE artifact_id=?", (artifact_id,)
            )
            connection.execute(
                "INSERT INTO stage1_review_projection_meta VALUES(?,?,?,?,?,?,?,?,?,?)",
                (artifact_id, basis_id, snapshot_id, 0, "DRAFT", scale, scale,
                 STAGE1_POLICY_VERSION, "2026-09-20T00:00:00+00:00", '{}'),
            )
            rows = []
            domains = []
            for index in range(scale):
                candidate_id = f"CAND_SCALE_{index:05d}"
                domain_id = domain_ids[index % len(domain_ids)]
                native = {
                    "candidate_id": candidate_id, "candidate_type": "CLAIM",
                    "content": {"ordinal": index}, "allowed_decisions": ["KEEP", "DROP"],
                }
                rows.append((
                    artifact_id, candidate_id, basis_id, index, "CLAIM", "SRC_SCALE",
                    "2026-09-20T00:00:00+00:00", f"{index:012d}", 1, None,
                    '["needs_review","human_required"]', json.dumps([domain_id]), '{}',
                    json.dumps(native, sort_keys=True, separators=(",", ":")),
                ))
                domains.append((artifact_id, candidate_id, domain_id))
            connection.executemany(
                "INSERT INTO stage1_review_projection VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
            )
            connection.executemany(
                "INSERT INTO stage1_review_projection_domains VALUES(?,?,?)", domains
            )
        first_scale_page = projection.page(
            artifact_id, limit=100, queue="human_required"
        )
        assert first_scale_page == projection.page(
            artifact_id, limit=100, queue="human_required"
        )
        seen: list[str] = []
        cursor = None
        while True:
            page = projection.page(
                artifact_id, cursor=cursor, limit=100, queue="human_required"
            )
            assert len(page["items"]) <= 100
            seen.extend(item["candidate_id"] for item in page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert len(seen) == len(set(seen)) == scale
        assert seen == [f"CAND_SCALE_{index:05d}" for index in range(scale)]
        assert {
            domain_id: projection.page(
                artifact_id, limit=1, queue="human_required", domain_id=domain_id
            )["filtered_total"]
            for domain_id in domain_ids
        } == {domain_id: scale // 4 for domain_id in domain_ids}
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity["wip_state"] == "HARD_STOP"
        with pytest.raises(BoundaryError, match="WIP_HARD_LIMIT"):
            require_stage1_intake(connection)


def test_review_priority_is_deterministic_and_explainable():
    normal = _row_projection(
        {"candidate_id": "NORMAL", "candidate_type": "CLAIM", "content": {
            "confidence": 0.9, "evidence_validation": {"fidelity_status": "EXACT"},
        }}, artifact_id="ART", basis_id="BASIS", native_order=0, source_id="SRC",
        created_at="2026-09-21T00:00:00+00:00", state=None, domains=["ai_hardware"],
    )
    recovery = _row_projection(
        {"candidate_id": "RECOVERY", "candidate_type": "CLAIM", "content": {
            "recovery_required": True, "confidence": 0.9,
            "evidence_validation": {"fidelity_status": "EXACT"},
        }}, artifact_id="ART", basis_id="BASIS", native_order=99, source_id="SRC",
        created_at="2026-09-21T00:00:00+00:00", state=None, domains=["ai_hardware"],
    )
    assert recovery["attention_json"] == json.dumps({
        "domain_novelty": False, "evidence_warning": False,
        "identity_collision": False, "low_confidence_bucket": False,
        "new_node_create": False, "official_view_directly_affected": False,
        "operator_source_priority": 0, "parent_or_relation_ambiguity": False,
        "recovery_or_integrity_block": True,
    }, sort_keys=True, separators=(",", ":"))
    assert recovery["priority_key"] < normal["priority_key"]


def test_stage1_run_window_pause_and_frozen_single_worker_budget(tmp_path):
    case, run = _stage1_finished_case(tmp_path)
    assert LIMITS.sources_per_run == LIMITS.worker_concurrency == 1
    with Store(case["config"]).connect(operator_write=True) as connection:
        original = dict(connection.execute(
            "SELECT * FROM source_processing_runs WHERE processing_run_id=?",
            (run["processing_run_id"],),
        ).fetchone())
        columns = list(original)
        for index in (2, 3):
            clone = dict(original)
            clone.update({
                "processing_run_id": f"SOURCE_RUN_BUDGET_{index}",
                "idempotency_key": f"stage1-budget-window-{index:02d}",
                "state": "FAILED", "stage": "BUDGET_FIXTURE",
                "native_execution_id": None, "native_root_relative": None,
                "packet_artifact_id": None, "packet_id": None,
                "domain_context_required": 0,
            })
            connection.execute(
                f"INSERT INTO source_processing_runs({','.join(columns)}) "
                f"VALUES({','.join('?' for _ in columns)})",
                tuple(clone[column] for column in columns),
            )
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity["runs_last_24h"] == LIMITS.runs_per_24h
        assert capacity["new_intake_allowed"] is False
        with pytest.raises(BoundaryError, match="STAGE1_RUN_WINDOW_LIMIT"):
            require_stage1_intake(connection)
    assert set_stage1_intake(
        case["config"], paused=True, reason="Bounded operator pause test"
    )["status"] == "PAUSED"
    with Store(case["config"]).connect() as connection:
        with pytest.raises(BoundaryError, match="STAGE1_INTAKE_PAUSED"):
            require_stage1_intake(connection)


def test_stage1_migration_is_workbench_only_and_limits_are_frozen(tmp_path):
    case = stage7_fixture(tmp_path)
    prepare_domains(case["config"])
    knowledge_before = case["config"].knowledge_db.read_bytes()
    receipt = prepare_stage1_scale(case["config"])
    assert receipt["status"] == "STAGE1_SCALE_SCHEMA_PREPARED"
    assert receipt["canonical_db_write"] is False
    assert receipt["limits"] == asdict(LIMITS)
    assert case["config"].knowledge_db.read_bytes() == knowledge_before
    with Store(case["config"]).connect() as connection:
        assert connection.execute(
            "SELECT value FROM workbench_meta WHERE key='schema_version'"
        ).fetchone()[0] == "10"
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()


def test_stage1_migration_rebuilds_existing_native_review_packets(tmp_path):
    case, source = setup_source(tmp_path)
    run_id = start(case, source)
    provider = DeterministicFakeProvider()
    run = None
    for _ in range(3):
        run = case["service"].advance_once(
            worker_id="stage1-migration-worker", provider=provider,
            processing_run_id=run_id,
        )
    assert run["state"] == "HUMAN_REVIEW_REQUIRED"
    receipt = prepare_stage1_scale(case["config"])
    assert receipt["review_projections_built"] == 1
    page = Stage1ReviewProjection(case["config"]).page(run["packet_artifact_id"])
    assert page["total_native_rows"] == len(page["items"])
    assert page["projection_authority"] is False
