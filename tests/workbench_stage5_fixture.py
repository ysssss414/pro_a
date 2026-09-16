"""Reusable synthetic Stage 5 research fixture, including the performance corpus."""
from contextlib import closing
import hashlib
import json
import sqlite3

from pro_a.workbench.research_store import prepare_research
from workbench_stage3_fixture import _view, company_content
from workbench_stage4_fixture import stage4_fixture

RQ = 'RQ_STAGE5_TECH'
GAP = 'GAP_STAGE5_TECH'
DUPLICATE_NODE = 'NODE_STAGE5_DUPLICATE_NAME'
NO_EVIDENCE_RELATION = 'REL_STAGE5_USES_OLD'


def stage5_fixture(root, *, performance=False, origin='http://127.0.0.1:8000'):
    value = stage4_fixture(root, origin=origin)
    with closing(sqlite3.connect(value['knowledge'])) as connection, connection:
        connection.execute("INSERT INTO nodes VALUES(?,?,?,'Distinct identity with duplicate label','active','2026-05-01','2026-05-01')",
                           (DUPLICATE_NODE, 'Synthetic Company', 'Industry'))
        connection.execute('INSERT INTO node_aliases VALUES(?,?)', ('Synthetic Photonics Alias', 'NODE_STAGE3_TECH'))
        connection.execute('''INSERT INTO research_questions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (RQ, 'NODE_STAGE3_TECH', 'Will synthetic photonics adoption accelerate?',
             'Material technology adoption question', 'Evidence remains mixed', .6,
             json.dumps(['CLM_STAGE4_SUBJECT']), json.dumps(['CLM_STAGE4_HISTORICAL']),
             json.dumps(['deployment timing']), 'A sustained deployment delay', 'open',
             '2026-05-01', '2026-05-02'))
        connection.execute('''INSERT INTO knowledge_gaps VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
            (GAP, 'NODE_STAGE3_TECH', 'Need newer synthetic technology evidence',
             'Confirm adoption after the next reporting period', 'open',
             json.dumps(['CLM_STAGE4_CONTEXT']), '2026-07-01', '', '', '2026-05-01', '2026-05-02'))
        connection.execute('''INSERT INTO node_relations(relation_id,from_node_id,relation_type,to_node_id,scope,
            valid_from,valid_to,confidence,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',
            (NO_EVIDENCE_RELATION, 'NODE_STAGE3_PRODUCT', 'uses', 'NODE_STAGE3_TECH',
             'older recorded state without attached evidence', '2023-01-01', '2023-12-31',
             .5, 'retired', '2026-05-02'))
        if performance:
            for index in range(20):
                node_id = f'NODE_STAGE5_PERF_{index:03d}'
                connection.execute("INSERT INTO nodes VALUES(?,?,?,'Synthetic performance Node','active','2026-05-01','2026-05-01')",
                                   (node_id, f'Synthetic Performance Company {index:03d}', 'Company'))
            for index in range(100):
                source_id = f'SRC_STAGE5_PERF_{index:03d}'
                digest = hashlib.sha256(source_id.encode()).hexdigest()
                connection.execute('''INSERT INTO sources(source_id,title,original_name,archived_path,sha256,
                    ingestion_mode,analysis_mode,source_type,source_rank,origin_type,author,organization,
                    publication_time,ingested_at,status) VALUES(?,?,?,?,?,'synthetic','synthetic',
                    'SYNTHETIC_TEXT','A','primary','','Synthetic Org',?,'2026-05-31','stored')''',
                    (source_id, f'Synthetic Performance Source {index:03d}', source_id + '.txt',
                     'synthetic/' + source_id, digest, f'2026-05-{index % 28 + 1:02d}'))
            for index in range(500):
                claim_id = f'CLM_STAGE5_PERF_{index:04d}'
                source_id = f'SRC_STAGE5_PERF_{index % 100:03d}'
                connection.execute('''INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,
                    ingestion_time,source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,status,
                    confidence,structured_json,created_at) VALUES(?,?,'fact',?,?,'2026-05-31',?,
                    'synthetic:paragraph:1',?,'','performance','current',.8,'{}','2026-05-31')''',
                    (claim_id, f'Synthetic performance evidence statement {index:04d}',
                     f'2026-05-{index % 28 + 1:02d}', f'2026-05-{index % 28 + 1:02d}', source_id,
                     f'Synthetic performance excerpt {index:04d}'))
                if index < 300:
                    connection.execute('INSERT INTO claim_node_links VALUES(?,?,?)',
                        (claim_id, f'NODE_STAGE5_PERF_{index % 20:03d}',
                         ('subject', 'context', 'related')[index % 3]))
            for index in range(20):
                node_id = f'NODE_STAGE5_PERF_{index:03d}'
                content = company_content(f'Synthetic performance conclusion {index:03d}')
                content['evidence_claim_ids'] = [f'CLM_STAGE5_PERF_{index:04d}']
                _view(connection, f'VIEW_STAGE5_PERF_{index:03d}', node_id, 'v_20260531',
                      content, '20260531', index)
    prepare_research(value['config'])
    return value
