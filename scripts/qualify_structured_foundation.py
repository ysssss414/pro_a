"""Freeze or execute an offline structured-package qualification in isolated Workbenches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from pro_a.production_promotion import canonical_sha256, sha256_file
from pro_a.structured_foundation import freeze_contract, read_package, require, runtime_digest
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.store import Store
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.attribution_store import prepare_attribution
from pro_a.workbench.view_store import prepare_current_views
from pro_a.workbench.impact_store import prepare_impact
from pro_a.workbench.research_store import prepare_research
from pro_a.workbench.cloud_jobs import prepare_cloud_jobs
from pro_a.workbench.source_operations import prepare_source_operations
from pro_a.workbench.domains import prepare_domains
from pro_a.workbench.stage1_scale import prepare_stage1_scale, Stage1ReviewProjection, stage1_capacity
from pro_a.workbench.foundation_import import import_package


def immutable_json(path, value):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    if path.exists():
        require(path.read_bytes() == data, 'QUALIFICATION_ARTIFACT_DRIFT')
    else:
        with path.open('xb') as stream:
            stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--expected-production-sha', required=True)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    production, output = args.production.resolve(), args.output.resolve()
    require(not production.is_relative_to(output), 'QUALIFICATION_ROOT_CONTAINS_PRODUCTION')
    before = sha256_file(production)
    require(before == args.expected_production_sha, 'PRODUCTION_SHA_MISMATCH')
    output.mkdir(parents=True, exist_ok=True)
    package = read_package(args.package)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    contract = freeze_contract(package, pack_root=args.pack, production_path=production,
        target_root=output, repository_commit=head, runtime_sha256=runtime_digest())
    contract_path = output / 'import_contract.json'
    if not args.execute:
        immutable_json(contract_path, contract)
        print(json.dumps({'status': 'IMPORT_CONTRACT_FROZEN', 'contract_sha256': contract['contract_sha256'],
                          'logical_sources': contract['logical_source_count'], 'physical_sources': contract['physical_source_count']}))
        return
    require(contract_path.is_file(), 'IMPORT_CONTRACT_MUST_BE_FROZEN_FIRST')
    require(json.loads(contract_path.read_text(encoding='utf-8')) == contract, 'FROZEN_IMPORT_CONTEXT_DRIFT')
    results = []
    for label in ('a', 'b'):
        work = output / label
        knowledge = work / 'knowledge/pro_a.db'
        if not knowledge.exists():
            knowledge.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(production, knowledge)
        require(sha256_file(knowledge) == before, 'QUALIFICATION_SNAPSHOT_DRIFT')
        config = WorkbenchConfig('PRIVATE', knowledge, work / 'state/workbench.sqlite3',
                                 work / 'artifacts', 'http://127.0.0.1:8000')
        if not config.state_db.exists():
            Store(config).initialize()
            for prepare in (prepare_reviews, prepare_attribution, prepare_current_views, prepare_impact,
                            prepare_research, prepare_cloud_jobs, prepare_source_operations,
                            prepare_domains, prepare_stage1_scale):
                prepare(config)
        first = import_package(config, package_root=args.package, contract=contract, pack_root=args.pack)
        replay = import_package(config, package_root=args.package, contract=contract, pack_root=args.pack)
        require(first['artifact_id'] == replay['artifact_id'] and replay['duplicate'], 'IMPORT_REPLAY_DUPLICATED_PACKET')
        projection = Stage1ReviewProjection(config)
        cursor, ids, detail_types = None, [], set()
        while True:
            page = projection.page(first['artifact_id'], cursor=cursor)
            require(len(page['items']) <= 25, 'REVIEW_PAGE_LIMIT_VIOLATION')
            for row in page['items']:
                ids.append(row['candidate_id'])
                if row['candidate_type'] not in detail_types:
                    detail = projection.item(first['artifact_id'], row['candidate_id'])
                    require(detail['nonpromotable'] and not detail['available_decisions'], 'UNAUTHORIZED_REVIEW_CAPABILITY')
                    detail_types.add(row['candidate_type'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        require(len(ids) == len(set(ids)) == first['report']['candidate_objects'], 'REVIEW_PROJECTION_INCOMPLETE')
        with Store(config).connect() as connection:
            counts = {name: connection.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0]
                      for name in ('registered_packets', 'source_processing_runs', 'cloud_jobs', 'stage1_review_projection')}
            capacity = stage1_capacity(connection)
        require(counts['registered_packets'] == 1 and counts['source_processing_runs'] == counts['cloud_jobs'] == 0,
                'STRUCTURED_IMPORT_CREATED_LIVE_RUN_OR_DUPLICATE')
        require(sha256_file(knowledge) == before, 'QUALIFICATION_KNOWLEDGE_CHANGED')
        results.append({'label': label, **first, 'replay_duplicate': replay['duplicate'],
                        'projection_count': len(ids), 'projection_types': sorted(detail_types),
                        'table_counts': counts, 'capacity': capacity})
        print(json.dumps({'workspace': label, 'candidates': len(ids), 'structural_sha256': first['report']['structural_sha256']}, ensure_ascii=False), flush=True)
    require(results[0]['report'] == results[1]['report'], 'DETERMINISTIC_IMPORT_DRIFT')
    after = sha256_file(production)
    require(after == before, 'PRODUCTION_CHANGED')
    final = {'status': 'AUTOMATED_IMPORT_QUALIFIED_REGRESSION_PENDING', 'contract_sha256': contract['contract_sha256'],
        'results': results, 'production_sha_before': before, 'production_sha_after': after,
        'production_write_count': 0, 'provider_calls': 0, 'raw_source_extraction_calls': 0,
        'deterministic_import': 'PASS', 'final_human_qualification': 'PENDING'}
    immutable_json(output / 'qualification_results.json', final)
    print(json.dumps({'status': final['status'], 'production_sha256': after}))


if __name__ == '__main__':
    main()
