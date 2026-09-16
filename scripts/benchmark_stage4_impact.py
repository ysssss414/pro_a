"""Build the declared synthetic fixture and qualify bounded Stage 4 reads."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]

from pro_a.direct_impact import DirectImpact  # noqa: E402
from workbench_stage4_fixture import stage4_fixture  # noqa: E402


THRESHOLDS = {
    'impact_list': {'p95_ms': 250.0, 'max_query_count': 9},
    'impact_detail': {'p95_ms': 100.0, 'max_query_count': 9},
    'reverse_claim_view': {'p95_ms': 100.0, 'max_query_count': 10},
    'source_claim_node_view': {'p95_ms': 100.0, 'max_query_count': 9},
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def timed(call, iterations: int = 30) -> tuple[dict, list[float]]:
    for _ in range(3):
        call()
    timings = []
    result = {}
    for _ in range(iterations):
        started = time.perf_counter()
        result = call()
        timings.append((time.perf_counter() - started) * 1000)
    return result, timings


def expand_fixture(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        for index in range(20):
            connection.execute("INSERT INTO nodes VALUES(?,?,?,'Performance fixture','active','2026-05-01','2026-05-01')",
                               (f'NODE_PERF_{index:03d}', f'Performance Node {index:03d}', 'Company'))
        for source_index in range(100):
            source_id = f'SRC_PERF_{source_index:03d}'
            digest = hashlib.sha256(source_id.encode()).hexdigest()
            connection.execute('''INSERT INTO sources(source_id,title,original_name,archived_path,sha256,
                ingestion_mode,analysis_mode,source_type,source_rank,origin_type,organization,publication_time,
                ingested_at,status) VALUES(?,?,?,?,?,'synthetic','synthetic','SYNTHETIC_TEXT','A','primary',
                'Performance Fixture','2026-05-01','2026-05-02','stored')''',
                (source_id, f'Performance Source {source_index:03d}', source_id + '.txt',
                 'synthetic/' + source_id, digest))
            for claim_index in range(5):
                claim_id = f'CLM_PERF_{source_index:03d}_{claim_index}'
                connection.execute('''INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,
                    ingestion_time,source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,status,
                    confidence,structured_json,created_at) VALUES(?,?,'fact','2026-05-01','2026-05-01',
                    '2026-05-02',?,'TEXT',?,'','performance','current',0.9,'{}','2026-05-02')''',
                    (claim_id, f'Performance Claim {source_index:03d}/{claim_index}', source_id,
                     f'Performance Claim {source_index:03d}/{claim_index}'))
                if claim_index < 3:
                    connection.execute('INSERT INTO claim_node_links VALUES(?,?,?)',
                                       (claim_id, f'NODE_PERF_{source_index % 20:03d}',
                                        ('subject', 'context', 'related')[claim_index]))
        for index in range(20):
            claim_id = f'CLM_PERF_{index:03d}_0'
            connection.execute('''INSERT INTO current_views(view_id,node_id,version,status,change_level,
                content_md,content_json,trigger_source_id,trigger_claim_ids_json,revision_date,revision_seq,
                accepted_proposal_id,created_at,confirmed_at) VALUES(?,?,?,'official','initial','Performance',
                '{}',?,?, '20260501',0,'','2026-05-01','2026-05-01')''',
                (f'VIEW_PERF_{index:03d}', f'NODE_PERF_{index:03d}', 'v_20260501',
                 f'SRC_PERF_{index:03d}', json.dumps([claim_id])))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fixture_root = output.parent / 'performance_fixture'
    if fixture_root.exists():
        raise SystemExit('performance fixture path already exists; use a fresh evidence workspace')
    value = stage4_fixture(fixture_root)
    expand_fixture(value['knowledge'])
    service = DirectImpact(value['config'])

    list_result, list_times = timed(lambda: service.changes(limit=50, offset=0))
    change = next(row for row in list_result['changes'] if row['source']['source_id'] == 'SRC_PERF_000')
    impact_id = change['items'][0]['impact_id']
    detail_result, detail_times = timed(lambda: service.item(impact_id))
    claim_result, claim_times = timed(lambda: service.claim('CLM_PERF_000_0'))
    source_result, source_times = timed(lambda: service.source('SRC_PERF_000'))

    with closing(sqlite3.connect(value['knowledge'])) as connection:
        fixture = {
            'sources': connection.execute('SELECT count(*) FROM sources').fetchone()[0],
            'claims': connection.execute('SELECT count(*) FROM claims').fetchone()[0],
            'claim_node_links': connection.execute('SELECT count(*) FROM claim_node_links').fetchone()[0],
            'official_views': connection.execute("SELECT count(*) FROM current_views WHERE status='official'").fetchone()[0],
        }
    cases = {
        'impact_list': (list_times, list_result['snapshot']['query_count']),
        'impact_detail': (detail_times, detail_result['snapshot']['query_count']),
        'reverse_claim_view': (claim_times, claim_result['snapshot']['query_count']),
        'source_claim_node_view': (source_times, source_result['snapshot']['query_count']),
    }
    measurements = {}
    for name, (times, query_count) in cases.items():
        threshold = THRESHOLDS[name]
        p50 = round(statistics.median(times), 3)
        p95 = round(percentile(times, .95), 3)
        passed = p95 <= threshold['p95_ms'] and query_count <= threshold['max_query_count']
        measurements[name] = {'iterations': len(times), 'p50_ms': p50, 'p95_ms': p95,
                              'query_count': query_count, 'threshold': threshold,
                              'result': 'PASS' if passed else 'FAIL'}
    report = {
        'contract': 'docs/phase42_stage4_direct_impact_contract.md',
        'threshold_declared_before_measurement': True,
        'fixture': fixture,
        'measurements': measurements,
        'overall_result': 'PASS' if all(row['result'] == 'PASS' for row in measurements.values()) else 'FAIL',
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['overall_result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
