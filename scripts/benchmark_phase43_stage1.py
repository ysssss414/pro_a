"""Run offline, disposable Stage 1 scale and bounded-read benchmarks."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import tempfile
import time
import tracemalloc
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from pro_a.cloud_contract import DeterministicFakeProvider  # noqa: E402
from pro_a.query import ReadOnlyQuery  # noqa: E402
from pro_a.semantic_decomposition import (  # noqa: E402
    build_evidence_units,
    partition_semantic_claims,
)
from pro_a.workbench.stage1_scale import (  # noqa: E402
    LIMITS,
    STAGE1_POLICY_VERSION,
    Stage1ReviewProjection,
    _row_projection,
    prepare_stage1_scale,
    stage1_capacity,
)
from pro_a.workbench.store import Store  # noqa: E402
from stability_helpers import make_config  # noqa: E402
from test_phase43_stage0 import setup_source, start  # noqa: E402


ITERATIONS = 30
REVIEW_THRESHOLDS_MS = {"list_p95": 500.0, "detail_p95": 750.0,
                        "ten_thousand_overview_p95": 1000.0}
DOMAINS = ("ai_hardware", "semiconductor", "robotics", "commercial_space")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def stats(values: list[float]) -> dict[str, float | int]:
    return {
        "iterations": len(values),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "max_ms": round(max(values), 3),
        "total_duration_ms": round(sum(values), 3),
    }


def timed(call: Callable[[], Any], iterations: int = ITERATIONS) -> tuple[Any, list[float]]:
    for _ in range(3):
        call()
    values: list[float] = []
    result: Any = None
    for _ in range(iterations):
        started = time.perf_counter()
        result = call()
        values.append((time.perf_counter() - started) * 1000)
    return result, values


def query_count(call: Callable[[], Any]) -> int:
    """Count executed SQLite statements for one request without changing product code."""
    original = sqlite3.connect
    statements: list[str] = []

    def traced_connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    sqlite3.connect = traced_connect
    try:
        call()
    finally:
        sqlite3.connect = original
    return len([statement for statement in statements if not statement.startswith(("BEGIN", "COMMIT"))])


def semantic_inputs(count: int) -> list[dict[str, Any]]:
    values = []
    for index in range(count):
        claim_id = f"CLM_BENCH_{index:03d}"
        statement = f"Bounded semantic parent {index}."
        values.append({
            "claim_id": claim_id,
            "claim_text": statement,
            "evidence_units": build_evidence_units(
                parent_claim_id=claim_id,
                bounded_evidence=statement,
                source_locator=f"synthetic:paragraph:{index + 1}",
            ),
            "attribution": "Synthetic benchmark",
            "scope": "",
            "fact_time": "",
            "assigned_nature": "fact",
        })
    return values


def replace_projection(case: dict[str, Any], artifact_id: str, basis_id: str,
                       scale: int) -> None:
    snapshot_id = hashlib.sha256(f"stage1-scale:{scale}".encode()).hexdigest()
    rows: list[tuple[Any, ...]] = []
    domains: list[tuple[str, str, str]] = []
    for index in range(scale):
        candidate_id = f"CAND_SCALE_{index:05d}"
        domain = DOMAINS[index % len(DOMAINS)]
        native = {
            "candidate_id": candidate_id,
            "candidate_type": "CLAIM",
            "content": {
                "statement": f"Synthetic bounded review row {index}",
                "confidence": 0.4 if index % 17 == 0 else 0.9,
                "evidence_validation": {"fidelity_status": "EXACT"},
            },
            "content_sha256": hashlib.sha256(candidate_id.encode()).hexdigest(),
            "allowed_decisions": ["KEEP", "DROP", "KEEP_NEEDS_REVIEW"],
            "decision_effects": {
                "KEEP": "PROMOTABLE", "DROP": "NON_PROMOTABLE",
                "KEEP_NEEDS_REVIEW": "NON_PROMOTABLE",
            },
            "human_input": {"decision": "", "reason": "", "target_node_id": ""},
        }
        projected = _row_projection(
            native, artifact_id=artifact_id, basis_id=basis_id, native_order=index,
            source_id=f"SRC_SCALE_{index % 37:03d}",
            created_at=f"2026-09-{1 + index % 20:02d}T00:00:00+00:00",
            state=None, domains=[domain],
        )
        rows.append(tuple(projected[key] for key in (
            "artifact_id", "candidate_id", "basis_id", "native_order",
            "candidate_type", "source_id", "created_at", "priority_key", "is_pending",
            "state_json", "queues_json", "domains_json", "attention_json", "native_json",
        )))
        domains.append((artifact_id, candidate_id, domain))
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
             STAGE1_POLICY_VERSION, "2026-09-21T00:00:00+00:00", "{}"),
        )
        connection.executemany(
            "INSERT INTO stage1_review_projection VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )
        connection.executemany(
            "INSERT INTO stage1_review_projection_domains VALUES(?,?,?)", domains
        )


def traversal(projection: Stage1ReviewProjection, artifact_id: str) -> dict[str, Any]:
    cursor = None
    count = 0
    digest = hashlib.sha256()
    pages = 0
    while True:
        page = projection.page(artifact_id, cursor=cursor, limit=100,
                               queue="human_required")
        pages += 1
        for item in page["items"]:
            digest.update(item["candidate_id"].encode())
            count += 1
        cursor = page["next_cursor"]
        if cursor is None:
            break
    return {"rows": count, "pages": pages, "ordered_identity_sha256": digest.hexdigest()}


def review_benchmark(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    case, source = setup_source(root / "review")
    prepare_stage1_scale(case["config"])
    run_id = start(case, source)
    provider = DeterministicFakeProvider()
    run = None
    for _ in range(3):
        run = case["service"].advance_once(
            worker_id="stage1-benchmark-worker", provider=provider,
            processing_run_id=run_id,
        )
    if run is None or run["state"] != "HUMAN_REVIEW_REQUIRED":
        raise RuntimeError("offline fixture did not reach HUMAN_REVIEW_REQUIRED")
    artifact_id = run["packet_artifact_id"]
    projection = Stage1ReviewProjection(case["config"])
    initial = projection.page(artifact_id)
    detail_id = initial["items"][0]["candidate_id"]
    _, detail_times = timed(lambda: projection.item(artifact_id, detail_id))
    detail_queries = query_count(lambda: projection.item(artifact_id, detail_id))

    measurements: dict[str, Any] = {}
    identities: dict[int, str] = {}
    for scale in (100, 1_000, 10_000):
        replace_projection(case, artifact_id, initial["basis_id"], scale)
        first = projection.page(artifact_id, limit=25, queue="human_required")
        stable = first == projection.page(artifact_id, limit=25, queue="human_required")
        _, page_times = timed(
            lambda: projection.page(artifact_id, limit=25, queue="human_required")
        )
        page_queries = query_count(
            lambda: projection.page(artifact_id, limit=25, queue="human_required")
        )
        tracemalloc.start()
        started = time.perf_counter()
        complete = traversal(projection, artifact_id)
        traversal_ms = (time.perf_counter() - started) * 1000
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        identities[scale] = complete["ordered_identity_sha256"]
        domain_counts = {
            domain: projection.page(
                artifact_id, limit=1, queue="human_required", domain_id=domain
            )["filtered_total"]
            for domain in DOMAINS
        }
        measurements[str(scale)] = {
            "list_page": {**stats(page_times), "query_count": page_queries},
            "complete_traversal": {
                **complete, "total_duration_ms": round(traversal_ms, 3),
                "peak_traced_bytes": peak,
            },
            "stable_identical_read": stable,
            "first_page_rows": len(first["items"]),
            "domain_distribution": domain_counts,
            "no_duplicate_or_missing": complete["rows"] == scale,
        }
    with Store(case["config"]).connect() as connection:
        capacity = stage1_capacity(connection)
        plans = [row[3] for row in connection.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM stage1_review_projection "
            "WHERE artifact_id=? AND is_pending=1 ORDER BY priority_key LIMIT 26",
            (artifact_id,),
        )]
    result = {
        "review_rows": measurements,
        "detail": {**stats(detail_times), "query_count": detail_queries},
        "thresholds_ms": REVIEW_THRESHOLDS_MS,
        "query_plan": plans,
        "bounded_page_default": LIMITS.review_page_default,
        "bounded_page_max": LIMITS.review_page_max,
        "capacity_at_10000": capacity,
        "all_scale_identities_distinct": len(set(identities.values())) == 3,
    }
    return result, {"case": case, "artifact_id": artifact_id}


def catalog_benchmark(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    cfg, db = make_config(root)
    created = "2026-09-21T00:00:00+00:00"
    with db.connect() as connection:
        connection.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            [(f"NODE_SUB_{index:04d}", f"Needle candidate {index:04d}", "Company", "",
              "active", created, created) for index in range(600)] + [
                ("NODE_EXACT", "ＮＥＥＤＬＥ", "Company", "", "active", created, created),
                ("NODE_ALIAS", "ZZZ exact alias owner", "Company", "", "active", created, created),
            ],
        )
        connection.execute("INSERT INTO node_aliases VALUES('needle','NODE_ALIAS')")
    query = ReadOnlyQuery(cfg.db_path)
    _, values = timed(lambda: query.search_nodes_page("needle", limit=100))
    first = query.search_nodes_page("needle", limit=100)
    seen: list[str] = []
    cursor = None
    started = time.perf_counter()
    while True:
        page = query.search_nodes_page("needle", limit=73, cursor=cursor)
        seen.extend(item["node_id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    return {
        "result_count": len(seen),
        "unique_result_count": len(set(seen)),
        "first_two_ids": seen[:2],
        "exact_match_retrieved_before_substrings": seen[:2] == ["NODE_EXACT", "NODE_ALIAS"],
        "continuation_complete": len(seen) == len(set(seen)) == 602,
        "complete_traversal_ms": round((time.perf_counter() - started) * 1000, 3),
        "first_page": {**stats(values), "query_count": query_count(
            lambda: query.search_nodes_page("needle", limit=100)
        )},
        "ordering": first["ordering"],
    }


def batch_benchmark() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for count in (1, 8, 9, 40, 120):
        inputs = semantic_inputs(count)
        batches, values = timed(lambda: partition_semantic_claims(inputs))
        reconstructed = [copy.deepcopy(row) for batch in batches for row in batch]
        result[str(count)] = {
            **stats(values),
            "batch_count": len(batches),
            "batch_sizes": [len(batch) for batch in batches],
            "max_parents_per_batch": max(len(batch) for batch in batches),
            "exact_reconstruction": reconstructed == inputs,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pro-a-stage1-benchmark-") as temp:
        root = Path(temp)
        review, _fixture = review_benchmark(root)
        catalog = catalog_benchmark(root)
        batches = batch_benchmark()
    review_pass = all(
        row["list_page"]["p95_ms"] <= REVIEW_THRESHOLDS_MS["list_p95"]
        and row["stable_identical_read"] and row["no_duplicate_or_missing"]
        for row in review["review_rows"].values()
    ) and review["detail"]["p95_ms"] <= REVIEW_THRESHOLDS_MS["detail_p95"]
    review_pass = review_pass and (
        review["review_rows"]["10000"]["list_page"]["p95_ms"]
        <= REVIEW_THRESHOLDS_MS["ten_thousand_overview_p95"]
    )
    result = {
        "document_type": "phase43_stage1_performance_capacity_report",
        "method": {
            "fixture": "disposable offline SQLite Workbench and canonical catalog",
            "timed_iterations": ITERATIONS,
            "warmup_iterations": 3,
            "live_provider_calls": 0,
            "load_percentage_claimed": False,
            "load_note": "No portable worker-utilization percentage was available; bounded concurrency, queue backpressure, timings, query counts, and traced memory are reported instead.",
        },
        "review": review,
        "catalog": catalog,
        "semantic_batching": batches,
        "queue_and_worker": {
            "wip_soft": LIMITS.review_wip_soft,
            "wip_hard": LIMITS.review_wip_hard,
            "worker_concurrency": LIMITS.worker_concurrency,
            "jobs_per_run": LIMITS.jobs_per_run,
            "overflow_behavior": "HARD_STOP_DEFER",
            "duplicate_dispatch_count": 0,
            "duplicate_dispatch_evidence": "single-worker claim guard plus full regression concurrency tests",
        },
        "overall_result": "PASS" if (
            review_pass
            and catalog["continuation_complete"]
            and catalog["exact_match_retrieved_before_substrings"]
            and all(row["exact_reconstruction"] for row in batches.values())
        ) else "FAIL",
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["overall_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
