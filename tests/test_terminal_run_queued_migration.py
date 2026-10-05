"""Offline eligibility only; all Sources, execution evidence and commands synthetic."""
import sqlite3

import pytest

from pro_a.workbench import bounded_extraction_persistence as migration
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.domains import prepare_domains
from pro_a.workbench.lifecycle_closure import _require_drain, prepare_stage6_lifecycle
from pro_a.workbench.stage1_scale import prepare_stage1_scale
from pro_a.workbench.store import Store
from test_bounded_extraction_persistence import no_network, rows
from test_phase43_stage6_lifecycle import _schema11
from test_phase43_stage72b_extraction_retry import failed, retry
from test_workbench_stage7 import clean_pdf, upload


def queued(tmp_path, parent="FAILED"):
    case, _ = _schema11(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    service = case["service"]
    run = service.start(source["source_id"], idempotency_key="migration-queued-fixture-0001")["run"]
    run_id = run["processing_run_id"]
    first = service.advance_once(worker_id="migration-fixture", processing_run_id=run_id)
    assert first["state"] == "EXTRACTION_PROCESSING", first
    job_id = first["jobs"][0]["job_id"]
    if parent != "EXTRACTION_PROCESSING":
        service._transition(run_id, parent, "EXTRACTION_JOBS")
    return case, run_id, job_id


def report(config):
    with Store(config).connect() as connection:
        return migration.migration_drain_report(connection)


def blocked(config):
    before = config.state_db.read_bytes()
    logical = rows(config)
    with pytest.raises(BoundaryError, match="BOUNDED_MIGRATION_REQUIRES_DRAIN"):
        migration.prepare_bounded_extraction_persistence(config)
    assert config.state_db.read_bytes() == before
    assert rows(config) == logical
    assert not config.state_db.with_name(config.state_db.name + ".stage-bounded-extraction-v12-backup").exists()


@pytest.mark.parametrize("parent", ["FAILED", "BLOCKED", "HUMAN_REVIEW_REQUIRED"])
def test_clean_terminal_history_preserved_and_normal_scheduler_cannot_select(tmp_path, monkeypatch, parent):
    case, run_id, job_id = queued(tmp_path, parent)
    config = case["config"]
    before = rows(config)
    pristine = config.state_db.read_bytes()
    production = config.knowledge_db.read_bytes()
    artifacts = {p.relative_to(config.artifact_root): p.read_bytes()
                 for p in config.artifact_root.rglob("*") if p.is_file()}
    eligibility = report(config)
    assert eligibility["terminal_unreachable_queued_job_ids"] == (job_id,)
    assert eligibility["active_job_count"] == eligibility["active_run_count"] == 0
    with Store(config).connect() as connection:
        with pytest.raises(BoundaryError, match="STAGE6_LIFECYCLE_REQUIRES_DRAIN"):
            _require_drain(connection)
    def forbidden(*args, **kwargs):
        pytest.fail("TERMINAL_RUN_DISPATCH_FORBIDDEN")
    monkeypatch.setattr(case["service"].jobs, "run_once", forbidden)
    assert case["service"].advance_once(worker_id="migration-fixture", provider=object()) is None
    assert case["service"].advance_once(worker_id="migration-fixture", provider=object(),
                                         processing_run_id=run_id) is None
    assert rows(config) == before
    assert migration.prepare_bounded_extraction_persistence(config)["schema_version"] == "12"
    assert config.state_db.with_name(config.state_db.name + ".stage-bounded-extraction-v12-backup").read_bytes() == pristine
    after = rows(config)
    before["workbench_meta"] = [(k, "12" if k == "schema_version" else v) for k, v in before["workbench_meta"]]
    assert all(after[k] == v for k, v in before.items())
    assert set(after) - set(before) == set(migration.TABLES)
    assert all(not after[t] for t in migration.TABLES)
    assert config.knowledge_db.read_bytes() == production
    assert artifacts == {p.relative_to(config.artifact_root): p.read_bytes()
                         for p in config.artifact_root.rglob("*") if p.is_file()}
    assert report(config) == eligibility
    prepared = config.state_db.read_bytes()
    assert migration.prepare_bounded_extraction_persistence(config)["status"] == "ALREADY_PREPARED"
    assert config.state_db.read_bytes() == prepared


@pytest.mark.parametrize("parent,job_state", [
    ("EXTRACTION_PROCESSING", "QUEUED"), ("EXTRACTION_PROCESSING", "RUNNING"), ("FAILED", "RUNNING"),
    ("RECOVERY_REQUIRED", "QUEUED"),
])
def test_active_running_and_recovery_always_block(tmp_path, parent, job_state):
    case, _, job_id = queued(tmp_path, parent)
    with Store(case["config"]).connect(operator_write=True) as connection:
        connection.execute("UPDATE cloud_jobs SET state=? WHERE job_id=?", (job_state, job_id))
        if parent == "RECOVERY_REQUIRED":
            connection.execute("UPDATE source_processing_runs SET manual_recovery_required=1")
    assert report(case["config"])["terminal_unreachable_queued_count"] == 0
    blocked(case["config"])


@pytest.mark.parametrize("change", [
    "attempt_count", "reserved_calls", "reserved_tokens", "fence", "lease", "started", "result",
    "request", "usage", "parent_lease", "parent_unfinished", "input_owner", "operation", "runtime",
])
def test_nonpristine_or_inconsistent_queue_blocks(tmp_path, change):
    case, _, job_id = queued(tmp_path)
    with Store(case["config"]).connect(operator_write=True) as connection:
        if change in ("attempt_count", "reserved_calls", "reserved_tokens", "fence"):
            connection.execute(f"UPDATE cloud_jobs SET {change}=1 WHERE job_id=?", (job_id,))
        elif change == "lease":
            connection.execute("UPDATE cloud_jobs SET lease_owner='worker',lease_expires_at='2099-01-01'")
        elif change == "started":
            connection.execute("UPDATE cloud_jobs SET started_at='2000-01-01'")
        elif change == "result":
            connection.execute("UPDATE cloud_jobs SET result_artifact_id='synthetic-result'")
        elif change == "request":
            connection.execute("UPDATE cloud_jobs SET provider_request_id='synthetic-request'")
        elif change == "usage":
            connection.execute("UPDATE cloud_jobs SET total_tokens=1")
        elif change == "parent_lease":
            connection.execute("UPDATE source_processing_runs SET lease_owner='worker',lease_expires_at='2099-01-01'")
        elif change == "parent_unfinished":
            connection.execute("UPDATE source_processing_runs SET ended_at=NULL")
        elif change == "input_owner":
            connection.execute("UPDATE cloud_jobs SET input_sha256=?", ("0" * 64,))
        elif change == "operation":
            connection.execute("UPDATE cloud_jobs SET operation_kind='SEMANTIC_DECOMPOSITION'")
        elif change == "runtime":
            connection.execute("UPDATE cloud_jobs SET runtime_sha256=?", ("0" * 64,))
    blocked(case["config"])


@pytest.mark.parametrize("evidence", ["attempt", "dispatch", "outcome", "result", "orphan_dispatch"])
def test_execution_evidence_blocks_even_without_counters(tmp_path, evidence):
    case, _, job_id = queued(tmp_path)
    # Deliberately inconsistent disposable evidence tests fail-closed classification.
    with sqlite3.connect(case["config"].state_db) as connection:
        if evidence != "orphan_dispatch":
            connection.execute("INSERT INTO cloud_attempts VALUES(?,?,?,?,?,?,?)",
                               ("synthetic-attempt", job_id, 1, 1, "a" * 64, "{}", "2000-01-01"))
        if evidence in ("dispatch", "outcome", "orphan_dispatch"):
            connection.execute("INSERT INTO cloud_attempt_dispatches VALUES(?,?)", ("synthetic-attempt", "2000-01-01"))
        if evidence == "outcome":
            connection.execute("INSERT INTO cloud_attempt_outcomes(attempt_id,outcome,external_outcome,usage_status,ended_at) "
                               "VALUES(?,'RECOVERY_REQUIRED','UNKNOWN','UNKNOWN','2000-01-01')", ("synthetic-attempt",))
        if evidence == "result":
            connection.execute("INSERT INTO cloud_job_results VALUES(?,?,?,?,?,?,?,?)",
                               ("synthetic-result", job_id, "synthetic-attempt", "synthetic.json", "a" * 64,
                                "PASS", "synthetic", "2000-01-01"))
    blocked(case["config"])


def test_unbound_queue_blocks(tmp_path):
    case, _, _ = queued(tmp_path)
    with sqlite3.connect(case["config"].state_db) as connection:
        connection.execute("DROP TRIGGER source_processing_jobs_delete_forbidden")
        connection.execute("DELETE FROM source_processing_jobs")
    blocked(case["config"])


def test_live_accepted_retry_blocks_even_if_parent_later_marked_failed(tmp_path):
    case = failed(tmp_path)
    retry(case)
    case["service"]._transition(case["run_id"], "FAILED", "EXTRACTION_JOBS")
    assert report(case["config"])["terminal_unreachable_queued_count"] == 0
    blocked(case["config"])


@pytest.mark.parametrize("version,prepare", [("8", prepare_domains), ("9", prepare_stage1_scale),
                                            ("10", prepare_stage6_lifecycle)])
def test_earlier_offline_guards_stay_strict(tmp_path, version, prepare):
    case, _, _ = queued(tmp_path)
    with Store(case["config"]).connect(operator_write=True) as connection:
        connection.execute("UPDATE workbench_meta SET value=? WHERE key='schema_version'", (version,))
    before = case["config"].state_db.read_bytes()
    with pytest.raises(BoundaryError, match="REQUIRES_DRAIN"):
        prepare(case["config"])
    assert case["config"].state_db.read_bytes() == before


def test_no_cloud_jobs_behavior_unchanged(tmp_path):
    case, _ = _schema11(tmp_path)
    assert report(case["config"])["active_job_count"] == 0
    assert migration.prepare_bounded_extraction_persistence(case["config"])["schema_version"] == "12"
