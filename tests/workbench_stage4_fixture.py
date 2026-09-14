"""Reusable synthetic Stage 4 direct-impact fixture."""
from contextlib import closing
import json
import sqlite3

from pro_a.foundation_execution_contract import CONTRACT_SHA256
from pro_a.workbench.impact_store import prepare_impact
from pro_a.workbench.store import Store
from workbench_stage3_fixture import COMPANY, PRODUCT, TECH, _view, company_content, stage3_fixture

SOURCE = 'SRC_STAGE4_CHANGE'
OLD_SOURCE = 'SRC_STAGE4_OLD'
SUBJECT = 'CLM_STAGE4_SUBJECT'
CONTEXT = 'CLM_STAGE4_CONTEXT'
UNLINKED = 'CLM_STAGE4_UNLINKED'
DEFERRED = 'CLM_STAGE4_DEFERRED'
COOCCUR = 'CLM_STAGE4_COOCCUR'
UPDATE = 'CLM_STAGE4_UPDATE'
HISTORICAL = 'CLM_STAGE4_HISTORICAL'
INACTIVE = 'NODE_STAGE4_INACTIVE'
UNATTRIBUTED = 'NODE_STAGE4_UNATTRIBUTED'
OFFICIAL = 'VIEW_STAGE4_CURRENT'
HISTORICAL_VIEW = 'VIEW_STAGE4_HISTORICAL_CITATION'
DRAFT = 'VIEWDRAFT_STAGE4_PRODUCT'


def _claim(connection, claim_id, statement, source, status='current', fact=''):
    connection.execute('''INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,ingestion_time,
        source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,status,confidence,structured_json,created_at)
        VALUES(?,?,'fact',?,'2026-04-01','2026-04-02',?,'synthetic:paragraph:1',?,'','stage4',?,0.9,'{}','2026-04-02')''',
        (claim_id, statement, fact, source, statement, status))


def stage4_fixture(root, *, origin='http://127.0.0.1:8000'):
    value = stage3_fixture(root, origin=origin)
    with closing(sqlite3.connect(value['knowledge'])) as connection, connection:
        connection.execute("INSERT INTO nodes VALUES(?,?,?,'Synthetic Stage 4','inactive','2026-01-01','2026-01-01')",
                           (INACTIVE, 'Synthetic Inactive Company', 'Company'))
        connection.execute("INSERT INTO nodes VALUES(?,?,?,'Synthetic Stage 4','active','2026-01-01','2026-01-01')",
                           (UNATTRIBUTED, 'Synthetic Cooccurring Alias', 'Company'))
        connection.execute('INSERT INTO node_aliases VALUES(?,?)', ('Cooccurring Alias', UNATTRIBUTED))
        for source_id, title, digest in ((SOURCE, 'Synthetic Stage 4 change', 'd' * 64),
                                         (OLD_SOURCE, 'Synthetic Stage 4 old evidence', 'e' * 64)):
            connection.execute('''INSERT INTO sources(source_id,title,original_name,archived_path,sha256,
                ingestion_mode,analysis_mode,source_type,source_rank,origin_type,organization,publication_time,
                ingested_at,status) VALUES(?,?,?,?,?,'synthetic','synthetic','SYNTHETIC_TEXT','A','primary',
                'Synthetic Org','2026-04-01','2026-04-02','stored')''',
                (source_id, title, source_id + '.txt', 'synthetic/' + source_id, digest))
        _claim(connection, SUBJECT, 'Synthetic Company changed recorded operations', SOURCE, fact='2026-04-01')
        _claim(connection, CONTEXT, 'Synthetic Product is explicit context', SOURCE)
        _claim(connection, UNLINKED, 'Claim has no explicit Node attribution', SOURCE)
        _claim(connection, DEFERRED, 'Deferred attribution created no canonical link', SOURCE)
        _claim(connection, COOCCUR, 'Synthetic Cooccurring Alias appears only as text', SOURCE)
        _claim(connection, UPDATE, 'Newer explicitly recorded state', SOURCE, fact='')
        _claim(connection, HISTORICAL, 'Older explicitly recorded state', OLD_SOURCE, status='historical', fact='2025-01-01')
        connection.executemany('INSERT INTO claim_node_links VALUES(?,?,?)', [
            (SUBJECT, COMPANY, 'subject'), (SUBJECT, TECH, 'related'),
            (CONTEXT, PRODUCT, 'context'), (UPDATE, INACTIVE, 'related')])
        connection.execute("INSERT INTO claim_relations VALUES('CLREL_STAGE4_CONTRA',?,'contradicts',?,'Explicit conflict','2026-04-02')",
                           (SUBJECT, HISTORICAL))
        connection.execute("INSERT INTO claim_relations VALUES('CLREL_STAGE4_UPDATE',?,'updates',?,'Explicit later state','2026-04-02')",
                           (UPDATE, HISTORICAL))
        connection.executemany('''INSERT INTO node_relations(relation_id,from_node_id,relation_type,to_node_id,scope,
            valid_from,valid_to,confidence,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)''', [
            ('REL_STAGE4_CURRENT', PRODUCT, 'uses', TECH, 'recorded current', '2026-01-01', '', .9, 'current', '2026-04-02'),
            ('REL_STAGE4_CATEGORY', PRODUCT, 'related_to', TECH, 'general category', '', '', .8, 'categorical', '2026-04-02'),
            ('REL_STAGE4_HISTORY', COMPANY, 'supplies', TECH, 'historical', '2024-01-01', '2025-01-01', .7, 'retired', '2026-04-02')])
        connection.executemany('''INSERT INTO relation_evidence_links(relation_id,claim_id,evidence_role,status,created_at)
            VALUES(?,?,?,?,?)''', [
            ('REL_STAGE4_CURRENT', SUBJECT, 'contradicts', 'active', '2026-04-02'),
            ('REL_STAGE4_CATEGORY', CONTEXT, 'supports', 'retired', '2026-04-02'),
            ('REL_STAGE4_HISTORY', CONTEXT, 'supports', 'retired', '2026-04-02')])
        temporal = {'native_temporal': {'temporal_status': 'timeless_structural'}}
        connection.execute('''INSERT INTO relation_temporal_semantics VALUES(?,?,?,?,?,?,?)''',
            ('REL_STAGE4_CATEGORY', 'timeless_structural', 0, 0, 'f' * 64, CONTRACT_SHA256,
             json.dumps(temporal, sort_keys=True)))
        content = company_content('Synthetic Stage 4 latest official conclusion')
        content['evidence_claim_ids'] = [SUBJECT, HISTORICAL, 'CLM_STAGE4_MISSING']
        historical_view = company_content('Synthetic Stage 4 prior citation')
        historical_view['evidence_claim_ids'] = [UNLINKED]
        _view(connection, HISTORICAL_VIEW, COMPANY, 'v_20260301', historical_view,
              '20260301', 0, 'VIEW_STAGE3_CURRENT')
        _view(connection, OFFICIAL, COMPANY, 'v_20260401', content, '20260401', 0, HISTORICAL_VIEW)
        baseline = company_content('Synthetic Stage 4 nonofficial baseline')
        baseline['evidence_claim_ids'] = [UNLINKED]
        baseline['artifact_status'] = 'handoff_baseline_not_production_current_view'
        _view(connection, 'BASELINE_STAGE4', COMPANY, 'baseline_BASELINE_STAGE4', baseline,
              '20350101', 0, status='baseline')
    prepare_impact(value['config'])
    body = {'mode': 'INITIAL', 'expected_official_view_id': '', 'content': {},
            'primary_claim_ids': [CONTEXT], 'context_claim_ids': [], 'change_level': 'initial',
            'quality_validation': None}
    event = {'revision': 1, 'action': 'SAVE', 'body': body, 'reviewer': 'Synthetic Impact Reviewer',
             'reason': 'Synthetic staged dependency', 'updated_at': '2026-04-03T00:00:00+00:00'}
    response = {'draft_id': DRAFT, 'revision': 1, 'status': 'DRAFT', 'basis_sha256': 'a' * 64}
    with Store(value['config']).connect(operator_write=True) as connection:
        connection.execute('INSERT INTO view_drafts VALUES(?,?,?,?,?,?,?,?)',
                           (PRODUCT, DRAFT, 1, 'a' * 64, 'Synthetic Impact Reviewer', 'DRAFT',
                            json.dumps(body, sort_keys=True), '2026-04-03T00:00:00+00:00'))
        connection.execute('INSERT INTO view_draft_events VALUES(?,?,?,?,?,?)',
                           (PRODUCT, 1, '00000000-0000-0000-0000-000000000004', 'b' * 64,
                            json.dumps(event, sort_keys=True), json.dumps(response, sort_keys=True)))
    return value
