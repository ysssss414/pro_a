"""Generate the retained Stage 5 bounded-performance qualification result."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from statistics import median
from time import perf_counter

from pro_a.current_view_workbench import CurrentViewWorkbench
from pro_a.direct_impact import DirectImpact
from pro_a.research_explorer import ResearchExplorer
from workbench_stage5_fixture import stage5_fixture

# Declared before qualification. These are interactive local SQLite p95 limits in milliseconds.
THRESHOLDS_MS = {
    'global_search': 200.0,
    'node_detail_aggregation': 750.0,
    'claim_first_page': 200.0,
    'claim_filter': 200.0,
    'source_detail': 750.0,
    'relation_detail': 200.0,
    'coverage_projection': 1500.0,
    'current_view_plus_impact': 750.0,
}


def measure(operation, *, samples=31):
    for _ in range(3):
        operation()
    values = []
    for _ in range(samples):
        started = perf_counter(); operation(); values.append((perf_counter() - started) * 1000)
    ordered = sorted(values)
    return {'samples': samples, 'p50_ms': round(median(ordered), 3),
            'p95_ms': round(ordered[int((samples - 1) * .95)], 3),
            'max_ms': round(max(ordered), 3)}


def qualify(root: Path):
    value = stage5_fixture(root, performance=True)
    service = ResearchExplorer(value['config'])
    view = CurrentViewWorkbench(value['config'])
    impact = DirectImpact(value['config'])
    with closing(sqlite3.connect(value['knowledge'])) as connection:
        counts = {
            'sources': connection.execute('SELECT COUNT(*) FROM sources').fetchone()[0],
            'claims': connection.execute('SELECT COUNT(*) FROM claims').fetchone()[0],
            'explicit_claim_node_links': connection.execute('SELECT COUNT(*) FROM claim_node_links').fetchone()[0],
            'official_views': connection.execute("SELECT COUNT(*) FROM current_views WHERE status='official'").fetchone()[0],
        }
    assert counts == {'sources': 105, 'claims': 510, 'explicit_claim_node_links': 307, 'official_views': 24}
    operations = {
        'global_search': lambda: service.search('performance evidence', limit=30),
        'node_detail_aggregation': lambda: service.node('NODE_STAGE5_PERF_000'),
        'claim_first_page': lambda: service.claims(limit=25),
        'claim_filter': lambda: service.claims(node_id='NODE_STAGE5_PERF_000', role='subject', status='current', limit=25),
        'source_detail': lambda: service.source('SRC_STAGE5_PERF_000', claim_limit=25),
        'relation_detail': lambda: service.relation('REL_STAGE4_CURRENT'),
        'coverage_projection': lambda: service.coverage(limit=25),
        'current_view_plus_impact': lambda: (view.read('NODE_STAGE5_PERF_000'), impact.node('NODE_STAGE5_PERF_000')),
    }
    measurements = {name: measure(operation) for name, operation in operations.items()}
    gates = {name: row['p95_ms'] <= THRESHOLDS_MS[name] for name, row in measurements.items()}
    result = {
        'fixture': counts, 'thresholds_declared_before_qualification_ms': THRESHOLDS_MS,
        'measurements': measurements, 'gates': gates,
        'overall_result': 'PASS' if all(gates.values()) else 'FAIL',
        'semantic_search_enabled': False, 'cloud_model_calls': 0, 'local_model_calls': 0,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['overall_result'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
