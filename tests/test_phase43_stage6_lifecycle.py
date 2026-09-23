from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from pro_a.company_materials import CompanyMaterials
from pro_a.production_promotion import canonical_sha256
from pro_a.stage6_lifecycle import (
    build_closure, closure_file_bytes, validate_closure,
)
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.domains import prepare_domains
from pro_a.workbench.lifecycle_closure import (
    apply_lifecycle_closure, lifecycle_status, prepare_stage6_lifecycle,
)
from pro_a.workbench.stage1_scale import (
    Stage1ReviewProjection, prepare_stage1_scale, stage1_capacity,
)
from pro_a.workbench.store import Store
from workbench_stage7_fixture import stage7_fixture
from test_phase43_stage0 import setup_source, start


ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "lifecycle_closure/phase43_stage2_foundation_v1.json"


def _schema11(tmp_path: Path):
    case = stage7_fixture(tmp_path)
    prepare_domains(case["config"])
    prepare_stage1_scale(case["config"])
    return case, prepare_stage6_lifecycle(case["config"])


def test_closure_builder_is_deterministic_and_has_exact_authority_partition(tmp_path):
    first = build_closure(ROOT)
    second = build_closure(ROOT)
    assert closure_file_bytes(first) == closure_file_bytes(second) == CLOSURE.read_bytes()
    assert validate_closure(first) == {
        "closure_id": "phase43-stage2-foundation-v1",
        "closure_sha256": first["closure_sha256"],
        "population": 274,
        "human_user_qualified": 105,
        "ai_policy_closed": 169,
    }
    human = [row for row in first["resolutions"]
             if row["resolution_source"] == "HUMAN_USER_QUALIFICATION"]
    ai = [row for row in first["resolutions"]
          if row["resolution_source"] == "AI_POLICY_QUALIFICATION"]
    assert len(human) == 105 and len(ai) == 169
    assert sum(row["mandatory_human"] for row in human) == 76
    assert sum(row["residual_sample"] for row in human) == 29
    assert all(row["human_authorization_id"] is None and
               row["human_item_attribution"] is None for row in ai)
    assert all(row["production_authorized"] is False for row in first["resolutions"])

    tampered = copy.deepcopy(first)
    tampered["resolutions"][0]["native_decision"] = "REJECT"
    resolution = tampered["resolutions"][0]
    resolution["resolution_sha256"] = canonical_sha256({
        key: value for key, value in resolution.items() if key != "resolution_sha256"
    })
    tampered["closure_sha256"] = canonical_sha256({
        key: value for key, value in tampered.items() if key != "closure_sha256"
    })
    with pytest.raises(ValueError, match="CLOSURE_AUTHORITY"):
        validate_closure(tampered)


def test_schema11_migration_is_offline_append_only_and_workbench_only(tmp_path):
    case = stage7_fixture(tmp_path)
    prepare_domains(case["config"])
    prepare_stage1_scale(case["config"])
    knowledge_before = case["config"].knowledge_db.read_bytes()
    state_before = case["config"].state_db.read_bytes()
    receipt = prepare_stage6_lifecycle(case["config"])
    assert receipt["status"] == "STAGE6_LIFECYCLE_SCHEMA_PREPARED"
    assert receipt["schema_version"] == "11"
    assert case["config"].knowledge_db.read_bytes() == knowledge_before
    backup = case["config"].state_db.with_name(
        case["config"].state_db.name + ".stage43-stage6-backup"
    )
    assert backup.read_bytes() == state_before
    with Store(case["config"]).connect() as connection:
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert prepare_stage6_lifecycle(case["config"]) == {
        "status": "ALREADY_PREPARED", "schema_version": "11"
    }

    sidecar_case = stage7_fixture(tmp_path / "sidecar")
    prepare_domains(sidecar_case["config"])
    prepare_stage1_scale(sidecar_case["config"])
    sidecar = sidecar_case["config"].state_db.with_name(
        sidecar_case["config"].state_db.name + "-wal"
    )
    sidecar.write_bytes(b"uncheckpointed")
    with pytest.raises(BoundaryError, match="STAGE6_LIFECYCLE_REQUIRES_OFFLINE"):
        prepare_stage6_lifecycle(sidecar_case["config"])


def test_closure_apply_idempotence_and_operational_capacity(tmp_path, monkeypatch):
    case, _receipt = _schema11(tmp_path)
    production_sha = hashlib.sha256(case["config"].knowledge_db.read_bytes()).hexdigest()
    import pro_a.workbench.lifecycle_closure as lifecycle_module
    monkeypatch.setattr(lifecycle_module, "PRODUCTION_SHA256", production_sha)

    applied = apply_lifecycle_closure(
        case["config"], CLOSURE, expected_production_sha256=production_sha
    )
    assert applied["status"] == "LIFECYCLE_CLOSURE_APPLIED"
    assert applied["artifact_id"] is None
    assert apply_lifecycle_closure(
        case["config"], CLOSURE, expected_production_sha256=production_sha
    )["status"] == "ALREADY_APPLIED"
    status = lifecycle_status(case["config"])
    assert status["closures"][0]["historical_lifecycle_closed"] == 274
    assert status["closures"][0]["human_user_qualified"] == 105
    assert status["closures"][0]["ai_policy_closed"] == 169
    assert status["capacity"]["native_pending_rows"] == 0
    assert status["capacity"]["native_pending_review_rows"] == 0
    assert status["capacity"]["operational_pending_rows"] == 0
    assert status["capacity"]["operational_pending_review_rows"] == 0
    assert status["capacity"]["pending_review_rows"] == 0
    assert status["capacity"]["historical_lifecycle_closed"] == 274
    assert status["capacity"]["lifecycle_resolved_rows"] == 274
    assert status["capacity"]["wip_state"] == "OPEN"
    assert status["capacity"]["new_intake_allowed"] is True
    with Store(case["config"]).connect() as connection:
        meta = connection.execute("SELECT * FROM lifecycle_closure_meta").fetchone()
        assert meta["human_resolved_rows"] == 105
        assert meta["ai_policy_resolved_rows"] == 169
        assert meta["total_rows"] == 274
        assert meta["created_at"]

    with Store(case["config"]).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """INSERT INTO registered_packets(
               artifact_id,packet_id,packet_relative,run_relative,packet_sha256,file_inventory,
               artifact_kind) VALUES(?,?,?,?,?,?,?)""",
            ("ART_" + "f" * 32, "FUTURE_PACKET", "future.json", "future-run",
             "f" * 64, "{}", "REVIEW_PACKET"),
        )
        connection.execute(
            "INSERT INTO stage1_review_projection_meta VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("ART_" + "f" * 32, "basis", "snapshot", 0, "DRAFT", 1, 1,
             "phase43-stage1-bounded-operator-v1", "2026-09-23T00:00:00+00:00", "{}"),
        )
        connection.execute(
            """INSERT INTO stage1_review_projection VALUES(
               ?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("ART_" + "f" * 32, "FUTURE-1", "basis", 0, "CLAIM", "SRC", "now",
             "priority", 1, None, '["needs_review","human_required"]', "[]", "{}",
             '{"candidate_id":"FUTURE-1","candidate_type":"CLAIM","content":{}}'),
        )
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
    assert capacity["native_pending_rows"] == 1
    assert capacity["native_pending_review_rows"] == 1
    assert capacity["operational_pending_rows"] == 1
    assert capacity["operational_pending_review_rows"] == 1
    assert capacity["historical_lifecycle_closed"] == 274
    assert capacity["lifecycle_resolved_rows"] == 274

    with Store(case["config"]).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = []
        for index in range(1, 201):
            candidate_id = f"FUTURE-{index + 1}"
            rows.append((
                "ART_" + "f" * 32, candidate_id, "basis", index, "CLAIM", "SRC", "now",
                f"priority-{index:03d}", 1, None, '["needs_review","human_required"]',
                "[]", "{}", json.dumps({"candidate_id": candidate_id,
                                          "candidate_type": "CLAIM", "content": {}}),
            ))
        connection.executemany(
            "INSERT INTO stage1_review_projection VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity["native_pending_review_rows"] == 201
        assert capacity["operational_pending_review_rows"] == 201
        assert capacity["wip_state"] == "HARD_STOP"
    with Store(case["config"]).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM stage1_review_projection WHERE native_order>=101 AND artifact_id=?",
            ("ART_" + "f" * 32,),
        )
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity["native_pending_review_rows"] == 101
        assert capacity["operational_pending_review_rows"] == 101
        assert capacity["wip_state"] == "SOFT_WARNING"
        assert capacity["new_intake_allowed"] is True

    artifact_id = "ART_" + "f" * 32
    with Store(case["config"]).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """INSERT INTO lifecycle_closure_meta(
               closure_id,contract_version,capacity_policy_version,population_sha256,
               source_packet_immutable_sha256,closure_sha256,closure_file_sha256,artifact_id,
               summary_json,authority_json,human_resolved_rows,ai_policy_resolved_rows,
               total_rows,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("TEST_MIXED", "phase43-stage6-lifecycle-closure-v1",
             "phase43-stage6-lifecycle-capacity-v1", "a" * 64, "b" * 64,
             "c" * 64, "d" * 64, artifact_id, "{}", "{}", 0, 1, 1,
             "2026-09-23T00:00:00+00:00"),
        )
        connection.execute(
            """INSERT INTO lifecycle_resolutions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("TEST_MIXED", "FUTURE-1", "CLAIM", "e" * 64,
             "AI_POLICY_QUALIFICATION", "KEEP", None, None, 0, "TEST_POLICY_CLOSED",
             "f" * 64, "{}", artifact_id),
        )
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
        assert capacity["native_pending_review_rows"] == 101
        assert capacity["lifecycle_resolved_rows"] == 275
        assert capacity["operational_pending_review_rows"] == 100
        assert capacity["wip_state"] == "OPEN"
    projection = Stage1ReviewProjection(case["config"])
    assert projection.page(artifact_id, queue="needs_review")["filtered_total"] == 100
    assert projection.page(artifact_id, queue="native_pending")["filtered_total"] == 101
    lifecycle_page = projection.page(artifact_id, queue="lifecycle_closed")
    assert lifecycle_page["filtered_total"] == 1
    lifecycle_item = lifecycle_page["items"][0]
    assert lifecycle_item["native_review_pending"] is True
    assert lifecycle_item["operational_pending"] is False
    assert lifecycle_item["lifecycle_resolution_source"] == "AI_POLICY_QUALIFICATION"
    assert lifecycle_item["lifecycle_decision"] == "KEEP"
    assert lifecycle_item["followup_required"] is False
    assert lifecycle_item["closure_id"] == "TEST_MIXED"

    with Store(case["config"]).connect(operator_write=True) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_LIFECYCLE_CLOSURE"):
            connection.execute(
                "UPDATE lifecycle_closure_meta SET closure_sha256=?",
                ("0" * 64,),
            )


def test_schema11_preserves_source_start_and_company_material_timeline(tmp_path):
    case, source = setup_source(tmp_path)
    prepare_stage1_scale(case["config"])
    prepare_stage6_lifecycle(case["config"])
    run_id = start(case, source, key="stage6-schema11-company-material")
    assert run_id.startswith("SOURCE_RUN_")
    assert case["service"].list()["total"] == 1

    with sqlite3.connect(case["config"].knowledge_db) as connection, connection:
        connection.execute(
            """INSERT INTO nodes(
               node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            ("NODE_STAGE6_COMPANY", "Stage 6 Company", "Company", "Synthetic company",
             "active", "2026-09-23", "2026-09-23"),
        )
    timeline = CompanyMaterials(case["config"]).timeline("NODE_STAGE6_COMPANY")
    assert timeline["counts"] == {"total": 0, "private": 0, "canonical": 0}
    assert timeline["materials"] == []
