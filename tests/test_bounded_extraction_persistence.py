"""Disposable schema11 migrations and dormant ledger integration; synthetic only."""
from dataclasses import asdict
import json
import sqlite3
import socket

import pytest

from pro_a.workbench import bounded_extraction_persistence as migration
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.store import Store
from test_phase43_stage6_lifecycle import _schema11
from test_bounded_extraction import fixture, result


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original = socket.socket.connect
    def forbidden(*args, **kwargs):
        pytest.fail("NETWORK_FORBIDDEN")
    def local_only(sock, address):
        # Windows asyncio creates a loopback socket pair for its self-pipe.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original(sock, address)
        forbidden()
    monkeypatch.setattr("socket.socket.connect", local_only)
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


@pytest.fixture
def setup(tmp_path):
    case, _ = _schema11(tmp_path)
    config = case["config"]
    migration.prepare_bounded_extraction_persistence(config)
    ctx, catalog, series, plan = fixture(4)
    ledger = BoundedExtractionStore(config)
    ledger.create(series)
    return config, ledger, ctx, catalog, series, plan


def body(ctx, catalog, series, segment, subdivision=False):
    accepted = result(ctx, catalog, series, segment, claimed=not subdivision,
                      label="SUBDIVISION_REQUIRED" if subdivision else None)
    return json.dumps({"wire": json.loads(accepted.wire_json), "dispositions": [asdict(d) for d in accepted.dispositions]}).encode(), accepted


def reserve(ledger, segment, owner="worker", number=1, fence=None):
    if fence is None:
        fence = ledger.claim_segment(segment.segment_id, owner, lease_seconds=600)
    attempt = ledger.reserve_attempt(segment.segment_id, owner, fence, attempt_number=number,
        payload_sha256="a" * 64, configuration_sha256="b" * 64)
    return fence, attempt["attempt_id"]


def complete(ledger, ctx, catalog, series, segment, subdivision=False):
    fence, aid = reserve(ledger, segment)
    assert ledger.record_dispatch(aid, "worker", fence)
    raw, pure = body(ctx, catalog, series, segment, subdivision)
    ledger.record_outcome(aid, "worker", fence, raw, finish_reason="stop", provider_request_id="synthetic-request",
                          input_tokens=100, output_tokens=50, total_tokens=150, cached_input_tokens=20)
    accepted = ledger.accept_result(aid, "worker", fence, catalog, ctx)
    assert accepted["result_sha256"] == pure.result_sha256
    return fence, aid, pure


def rows(config):
    with Store(config).connect() as c:
        return {r[0]: [tuple(v) for v in c.execute('SELECT * FROM "' + r[0] + '" ORDER BY rowid')]
                for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def test_migration_exact_backup_preserves_every_old_row_and_production(tmp_path):
    case, _ = _schema11(tmp_path)
    config = case["config"]
    old = rows(config)
    before, production = config.state_db.read_bytes(), config.knowledge_db.read_bytes()
    receipt = migration.prepare_bounded_extraction_persistence(config)
    assert receipt["schema_version"] == "12"
    assert config.state_db.with_name(config.state_db.name + ".stage-bounded-extraction-v12-backup").read_bytes() == before
    assert len(list(config.state_db.parent.glob("*.stage-bounded-extraction-v12-backup"))) == 1
    new = rows(config)
    old["workbench_meta"] = [(k, "12" if k == "schema_version" else v) for k, v in old["workbench_meta"]]
    assert all(new[k] == v for k, v in old.items())
    assert set(new) - set(old) == set(migration.TABLES)
    assert all(not new[t] for t in migration.TABLES)
    assert config.knowledge_db.read_bytes() == production
    after = config.state_db.read_bytes()
    assert migration.prepare_bounded_extraction_persistence(config)["status"] == "ALREADY_PREPARED"
    assert config.state_db.read_bytes() == after
    with Store(config).connect() as c:
        columns = {r[1]: r[2] for r in c.execute("PRAGMA table_info(bounded_extraction_outcomes)")}
        assert columns["latency_ms"] == "REAL"
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not c.execute("PRAGMA foreign_key_check").fetchall()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_migration_offline(tmp_path, suffix):
    case, _ = _schema11(tmp_path)
    path = case["config"].state_db
    path.with_name(path.name + suffix).write_bytes(b"synthetic-sidecar")
    with pytest.raises(BoundaryError, match="REQUIRES_OFFLINE"):
        migration.prepare_bounded_extraction_persistence(case["config"])
    assert not path.with_name(path.name + ".stage-bounded-extraction-v12-backup").exists()


def test_migration_rollback_backup_conflict_and_no_partial_schema(tmp_path, monkeypatch):
    case, _ = _schema11(tmp_path)
    config = case["config"]
    before, logical = config.state_db.read_bytes(), rows(config)
    def crash(name):
        if name == "migration_identity_tables":
            raise RuntimeError("SYNTHETIC_CRASH")
    monkeypatch.setattr(migration, "checkpoint", crash)
    with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
        migration.prepare_bounded_extraction_persistence(config)
    assert rows(config) == logical
    assert config.state_db.with_name(config.state_db.name + ".stage-bounded-extraction-v12-backup").read_bytes() == before
    monkeypatch.setattr(migration, "checkpoint", lambda name: None)
    migration.prepare_bounded_extraction_persistence(config)
    other, _ = _schema11(tmp_path / "conflict")
    path = other["config"].state_db
    path.with_name(path.name + ".stage-bounded-extraction-v12-backup").write_bytes(b"different")
    with pytest.raises(BoundaryError, match="ARTIFACT_CONFLICT"):
        migration.prepare_bounded_extraction_persistence(other["config"])


def test_active_bounded_drain_and_v11_remains_usable(setup, tmp_path):
    config, ledger, *_ = setup
    with pytest.raises(BoundaryError, match="REQUIRES_DRAIN"):
        migration.prepare_bounded_extraction_persistence(config)
    case, _ = _schema11(tmp_path / "v11")
    dormant = BoundedExtractionStore(case["config"])
    with pytest.raises(BoundaryError, match="BOUNDED_SCHEMA_REQUIRED"):
        dormant.create(fixture(1)[2])
    from pro_a.workbench.lifecycle_closure import lifecycle_status
    assert lifecycle_status(case["config"])["schema_version"] == "11"


def test_synthetic_e2e_subdivision_restart_and_foundation_equality(setup):
    from pro_a.bounded_extraction import aggregate_segment_wires
    config, ledger, ctx, catalog, series, plan = setup
    fence, _, _ = complete(ledger, ctx, catalog, series, plan.leaves[0], True)
    children = ledger.subdivide(plan.leaves[0].segment_id, "worker", fence, expected_frontier_version=0)
    ledger = BoundedExtractionStore(config)
    assert ledger.subdivide(plan.leaves[0].segment_id, "worker", fence, expected_frontier_version=0) == children
    pure = [complete(ledger, ctx, catalog, series, child)[2] for child in reversed(children)]
    series2, plan2, row, usage = ledger.read(series.series_id)
    assert row["frontier_version"] == 1 and usage.provider_call_count == 3
    assert usage.output_tokens == 150 and usage.cached_tokens == 60 and usage.total_tokens == 450
    expected = aggregate_segment_wires(series2, plan2, tuple(pure), catalog, ctx)
    sf = ledger.claim_series(series.series_id, "coordinator")
    final = ledger.finalize(series.series_id, "coordinator", sf, expected_frontier_version=1, catalog=catalog, context=ctx)
    assert final["aggregate_wire_sha256"] == expected.aggregate_wire_sha256
    assert final["coverage_sha256"] == expected.coverage.coverage_sha256
    fresh = BoundedExtractionStore(config)
    assert fresh.read(series.series_id)[2]["state"] == "SUCCEEDED_COMPLETE"
    assert fresh.finalize(series.series_id, "coordinator", sf, expected_frontier_version=1, catalog=catalog, context=ctx) == final
    private = json.loads((config.artifact_root / final["artifact_relative"]).read_bytes())
    assert private["wire"] == json.loads(expected.wire_json)
    with Store(config).connect() as c:
        for table in ("cloud_jobs", "cloud_attempts", "source_processing_jobs"):
            assert c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("truncated", [False, True])
def test_invalid_raw_durable_private_not_accepted(setup, truncated):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    raw = b'{"PRIVATE_SYNTHETIC_RAW_DO_NOT_PUBLISH":'
    outcome = ledger.record_outcome(aid, "worker", fence, raw, finish_reason="length" if truncated else "stop", output_tokens=12000 if truncated else 5)
    assert outcome["external_outcome"] == ("TRUNCATED" if truncated else "SUCCEEDED")
    with pytest.raises(BoundaryError, match="RAW_OUTCOME_NOT_ACCEPTABLE|INVALID_SEGMENT_RESPONSE"):
        ledger.accept_result(aid, "worker", fence, catalog, ctx)
    with Store(config).connect() as c:
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_segment_results").fetchone()[0] == 0
        for table in migration.TABLES:
            assert "PRIVATE_SYNTHETIC_RAW" not in str([tuple(r) for r in c.execute("SELECT * FROM " + table)])
    import base64
    artifact = json.loads((config.artifact_root / outcome["artifact_relative"]).read_bytes())
    assert base64.b64decode(artifact["raw_body_base64"]) == raw
    with pytest.raises(BoundaryError, match="VALID_SUBDIVISION_RESULT_REQUIRED"):
        ledger.subdivide(plan.leaves[0].segment_id, "worker", fence, expected_frontier_version=0)


@pytest.mark.parametrize("table", ["attempts", "dispatches", "outcomes", "segment_results", "events", "series_results"])
@pytest.mark.parametrize("action", ["UPDATE", "DELETE"])
def test_append_only_sql_guards(setup, table, action):
    config, ledger, ctx, catalog, series, plan = setup
    complete(ledger, ctx, catalog, series, plan.leaves[0])
    sf = ledger.claim_series(series.series_id, "coordinator")
    ledger.finalize(series.series_id, "coordinator", sf, expected_frontier_version=0, catalog=catalog, context=ctx)
    with Store(config).connect(operator_write=True) as c:
        sql = f"UPDATE bounded_extraction_{table} SET created_at='tampered'" if action == "UPDATE" else f"DELETE FROM bounded_extraction_{table}"
        with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_BOUNDED_AUDIT"):
            c.execute(sql)


@pytest.mark.parametrize("table,column", [("series", "series_sha256"), ("segments", "segment_sha256"), ("segments", "assigned_evidence_sha256")])
def test_semantic_sql_immutability(setup, table, column):
    config, *_ = setup
    with Store(config).connect(operator_write=True) as c:
        with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_BOUNDED_IDENTITY"):
            c.execute(f"UPDATE bounded_extraction_{table} SET {column}='tampered'")


@pytest.mark.parametrize("table,column", [("series", "series_sha256"), ("segments", "segment_sha256"),
    ("segments", "assigned_evidence_sha256"), ("attempts", "request_sha256"), ("outcomes", "artifact_sha256"),
    ("segment_results", "result_sha256"), ("series_results", "coverage_sha256")])
def test_corruption_rejected_on_fresh_read(setup, table, column):
    config, ledger, ctx, catalog, series, plan = setup
    complete(ledger, ctx, catalog, series, plan.leaves[0])
    sf = ledger.claim_series(series.series_id, "coordinator")
    ledger.finalize(series.series_id, "coordinator", sf, expected_frontier_version=0, catalog=catalog, context=ctx)
    with Store(config).connect(operator_write=True) as c:
        guard = "identity" if table in ("series", "segments") else "update"
        c.execute(f"DROP TRIGGER bounded_extraction_{table}_{guard}")
        c.execute(f"UPDATE bounded_extraction_{table} SET {column}=?", ("0" * 64,))
    before = config.state_db.read_bytes()
    with pytest.raises(ValueError, match="MISMATCH|INVALID_INITIAL_ASSIGNMENT"):
        BoundedExtractionStore(config).read(series.series_id)
    assert config.state_db.read_bytes() == before


def test_raw_immutable_and_path_guard(setup):
    config, ledger, ctx, catalog, series, plan = setup
    fence, aid = reserve(ledger, plan.leaves[0])
    ledger.record_dispatch(aid, "worker", fence)
    first = ledger.record_outcome(aid, "worker", fence, b"exact\x00\xffbytes")
    assert ledger.record_outcome(aid, "worker", fence, b"exact\x00\xffbytes") == first
    with pytest.raises(BoundaryError, match="ARTIFACT_CONFLICT"):
        ledger.record_outcome(aid, "worker", fence, b"different")
    with pytest.raises(BoundaryError, match="UNSAFE_PATH"):
        ledger._path(series.series_id, "../outside")
    path = config.artifact_root / first["artifact_relative"]
    path.write_bytes(b"tampered")
    with pytest.raises(BoundaryError, match="ARTIFACT_HASH_MISMATCH"):
        BoundedExtractionStore(config).read(series.series_id)


@pytest.mark.parametrize("cloud", [False, True])
def test_migration_rejects_active_existing_work(tmp_path, cloud):
    from legacy_source_fixture import historical_case
    case=historical_case(tmp_path)
    config = case["config"]
    with Store(config).connect(operator_write=True) as c:
        if cloud:
            # In-flight work still blocks after its owning historical Run ends.
            c.execute("UPDATE cloud_jobs SET state='RUNNING',phase='CLAIMED',fence=1,"
                      "lease_owner='synthetic-cloud',lease_expires_at='2099-01-01' WHERE job_id=?",(case['job_id'],))
        else:
            c.execute("UPDATE source_processing_runs SET state='QUEUED' WHERE processing_run_id=?",(case['run_id'],))
    before = config.state_db.read_bytes()
    with pytest.raises(BoundaryError, match="REQUIRES_DRAIN"):
        migration.prepare_bounded_extraction_persistence(config)
    assert config.state_db.read_bytes() == before


def test_migrated_v12_existing_source_cloud_review_stage1_mcp_semantics(tmp_path):
    from test_phase43_stage0 import setup_source, start
    from pro_a.cloud_contract import DeterministicFakeProvider
    from pro_a.workbench.source_operations import SourceOperations, prepare_source_operations
    from pro_a.workbench.cloud_jobs import prepare_cloud_jobs, runtime_identity
    from pro_a.workbench.stage1_scale import prepare_stage1_scale, stage1_capacity
    from pro_a.workbench.lifecycle_closure import prepare_stage6_lifecycle, lifecycle_status
    from pro_a.workbench.review_store import prepare_reviews
    from pro_a.workbench.review_workbench import ReviewWorkbench
    from pro_a.workbench.domains import prepare_domains
    from pro_a.mcp.service import ReadService
    case, source = setup_source(tmp_path, legacy=True)
    config = case["config"]
    prepare_domains(config)
    prepare_stage1_scale(config)
    prepare_stage6_lifecycle(config)
    production = config.knowledge_db.read_bytes()
    migration.prepare_bounded_extraction_persistence(config)
    for prepare in (prepare_reviews, prepare_cloud_jobs, prepare_source_operations, prepare_domains, prepare_stage1_scale, prepare_stage6_lifecycle):
        assert prepare(config) == {"status": "ALREADY_PREPARED", "schema_version": "12"}
    case["service"] = SourceOperations(config, case["source_profile"], case["cloud_profile"])
    run = start(case, source)
    from series_binding_helpers import synthetic_providers
    with synthetic_providers(case) as provider:
        for _ in range(4):
            final = case["service"].advance_once(worker_id="synthetic", provider=provider, processing_run_id=run)
            if final is None or final["state"] in ("HUMAN_REVIEW_REQUIRED", "BLOCKED", "FAILED", "RECOVERY_REQUIRED"):
                break
    assert final["state"] == "HUMAN_REVIEW_REQUIRED", final
    assert provider.call_count == 2
    handle = final["packet_artifact_id"]
    native = ReviewWorkbench(config).read(handle)
    before = config.state_db.read_bytes()
    bridge = ReadService(config)
    assert bridge.pro_a_health().workbench_schema_version == "12"
    assert bridge.get_review_context(handle).read_only
    queue = bridge.list_review_queue()
    assert queue.read_only and queue.items[0].review.status == native["review"]["status"]
    assert lifecycle_status(config)["schema_version"] == "12"
    with Store(config).connect() as c:
        assert stage1_capacity(c)["native_pending_rows"] > 0
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_series").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM bounded_extraction_series_results").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM cloud_jobs WHERE operation_kind='SOURCE_ANALYSIS_PIECE'").fetchone()[0] == 0
    assert runtime_identity("source-analysis-piece-adapter-v2", workbench_schema_version="12")["workbench_schema_version"] == "12"
    assert config.state_db.read_bytes() == before and config.knowledge_db.read_bytes() == production


def test_nonempty_v11_history_migrates_without_backfill(tmp_path):
    from legacy_source_fixture import historical_case
    case=historical_case(tmp_path,'review')
    config = case["config"]
    final=case['service'].get_run(case['run_id'])
    assert final["state"] == "HUMAN_REVIEW_REQUIRED"
    before = rows(config)
    assert len(before["source_processing_runs"]) == 1 and len(before["cloud_attempts"]) == 2
    migration.prepare_bounded_extraction_persistence(config)
    after = rows(config)
    before["workbench_meta"] = [(k, "12" if k == "schema_version" else v) for k, v in before["workbench_meta"]]
    assert all(after[k] == v for k, v in before.items())
    assert all(not after[t] for t in migration.TABLES)
