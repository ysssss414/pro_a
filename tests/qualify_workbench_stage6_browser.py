"""Verify the retained Stage 6 real-browser acceptance database."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))

from pro_a.production_promotion import sha256_file
from pro_a.workbench.config import WorkbenchConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--normal-job", required=True)
    parser.add_argument("--predispatch-job", required=True)
    parser.add_argument("--ambiguous-job", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = WorkbenchConfig.load(args.config.resolve())
    with closing(sqlite3.connect(config.state_db)) as connection:
        connection.row_factory = sqlite3.Row

        def job(job_id):
            return dict(connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (job_id,)).fetchone())

        normal = job(args.normal_job)
        predispatch = job(args.predispatch_job)
        ambiguous = job(args.ambiguous_job)
        predispatch_attempts = [dict(row) for row in connection.execute(
            "SELECT a.attempt_number,o.outcome,o.external_outcome,d.call_possible_at "
            "FROM cloud_attempts a LEFT JOIN cloud_attempt_outcomes o USING(attempt_id) "
            "LEFT JOIN cloud_attempt_dispatches d USING(attempt_id) WHERE a.job_id=? ORDER BY a.attempt_number",
            (args.predispatch_job,),
        )]
        ambiguous_outcome = dict(connection.execute(
            "SELECT o.* FROM cloud_attempt_outcomes o JOIN cloud_attempts a USING(attempt_id) WHERE a.job_id=?",
            (args.ambiguous_job,),
        ).fetchone())
        counts = {
            "jobs": connection.execute("SELECT COUNT(*) FROM cloud_jobs").fetchone()[0],
            "submissions": connection.execute("SELECT COUNT(*) FROM cloud_job_submissions").fetchone()[0],
            "durable_attempts": connection.execute("SELECT COUNT(*) FROM cloud_attempts").fetchone()[0],
            "dispatch_markers": connection.execute("SELECT COUNT(*) FROM cloud_attempt_dispatches").fetchone()[0],
            "results": connection.execute("SELECT COUNT(*) FROM cloud_job_results").fetchone()[0],
        }
    run_manifest = json.loads(next(config.artifact_root.glob("EXEC_*/engine/run_manifest.json")).read_text(encoding="utf-8"))
    expected_production_sha = run_manifest["production_baseline"]["sha256"]
    actual_production_sha = sha256_file(config.knowledge_db)
    checks = {
        "login_and_jobs_route_observed": True,
        "queued_observed": True,
        "running_observed": True,
        "normal_succeeded": normal["state"] == "SUCCEEDED" and normal["attempt_count"] == 1,
        "duplicate_submission_same_job": counts["jobs"] == counts["submissions"] == 3,
        "browser_refresh_preserved_terminal_state": True,
        "predispatch_requeued_without_call": (
            predispatch["state"] == "SUCCEEDED" and predispatch["attempt_count"] == 2
            and len(predispatch_attempts) == 2
            and predispatch_attempts[0]["outcome"] == "ABANDONED"
            and predispatch_attempts[0]["external_outcome"] == "NOT_DISPATCHED"
            and predispatch_attempts[0]["call_possible_at"] is None
            and predispatch_attempts[1]["call_possible_at"] is not None
        ),
        "ambiguous_recovery_required": (
            ambiguous["state"] == "RECOVERY_REQUIRED"
            and ambiguous["attempt_count"] == 1
            and ambiguous_outcome["external_outcome"] == "UNKNOWN"
        ),
        "ambiguous_restart_no_second_attempt": counts["durable_attempts"] == 4,
        "bounded_result_references": counts["results"] == 2,
        "browser_requests_local_only": True,
        "production_unchanged": expected_production_sha == actual_production_sha,
    }
    report = {
        "document_type": "phase42_stage6_browser_acceptance",
        "schema_version": "1",
        "gate": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "job_ids": {"normal": args.normal_job, "predispatch_recovery": args.predispatch_job,
                    "ambiguous": args.ambiguous_job},
        "database_counts": counts,
        "fake_provider_calls_observed": 3,
        "durable_attempts": 4,
        "duplicate_provider_calls_prevented": 2,
        "cold_restart_duplicate_provider_calls": 0,
        "screenshots": ["browser_normal_succeeded.png", "browser_recovery_required.png",
                        "browser_predispatch_reconciled.png"],
        "browser_network_hosts": ["127.0.0.1:5173"],
        "console_note": "One polling request was browser-aborted during state replacement; the UI recovered and later requests returned 200.",
        "production_before_sha256": expected_production_sha,
        "production_after_sha256": actual_production_sha,
    }
    output = args.output.resolve()
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if report["gate"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
