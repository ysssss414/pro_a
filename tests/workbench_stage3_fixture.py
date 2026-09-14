"""Reusable synthetic Stage 3 canonical and Workbench fixture."""
from contextlib import closing
import json
import sqlite3

from pro_a.db import Database
from pro_a.foundation_schema_preparation import apply_synthetic_migration
from pro_a.production_promotion import sha256_file
from pro_a.workbench.attribution_store import prepare_attribution
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.store import Store
from pro_a.workbench.view_store import prepare_current_views

COMPANY = 'NODE_STAGE3_COMPANY'
PRODUCT = 'NODE_STAGE3_PRODUCT'
TECH = 'NODE_STAGE3_TECH'
COMPANY_CLAIM = 'CLM_STAGE3_COMPANY_PRIMARY'
COMPANY_CONTEXT = 'CLM_STAGE3_COMPANY_CONTEXT'
PRODUCT_CLAIM = 'CLM_STAGE3_PRODUCT_PRIMARY'
IDENTITY = {'actor': 'operator', 'session_id': 'synthetic-stage3-session'}
REVIEWER = 'Synthetic View Reviewer'


def company_content(conclusion='Synthetic Company official conclusion'):
    return {'one_line_conclusion': conclusion, 'core_logic': [f'Synthetic Company operates steadily [{COMPANY_CLAIM}]'],
            'key_facts': [f'Synthetic Company reports stable operations [{COMPANY_CLAIM}]'],
            'core_disagreements': ['Synthetic Company outlook remains uncertain'],
            'assumptions_to_verify': ['Synthetic Company assumptions need validation'],
            'investment_implication': 'Synthetic Company evidence informs company analysis',
            'major_risks': [f'Synthetic Company evidence may change [{COMPANY_CLAIM}]'],
            'knowledge_gaps': ['Synthetic Company 缺少 follow-up evidence'],
            'key_watch_items': ['需跟踪 Synthetic Company evidence'],
            'recent_change': 'Synthetic Company official revision',
            'evidence_claim_ids': [COMPANY_CLAIM], 'type_specific': {}}


def product_content(conclusion='Synthetic Product initial conclusion'):
    return {'one_line_conclusion': conclusion, 'core_logic': [f'Synthetic Product evidence is recorded [{PRODUCT_CLAIM}]'],
            'key_facts': [f'Synthetic Product is documented [{PRODUCT_CLAIM}]'],
            'core_disagreements': ['Synthetic Product outlook remains uncertain'],
            'assumptions_to_verify': ['Synthetic Product assumptions need validation'],
            'investment_implication': 'Synthetic Product evidence informs 产品 analysis',
            'major_risks': [f'Synthetic Product evidence may change [{PRODUCT_CLAIM}]'],
            'knowledge_gaps': ['Synthetic Product 缺少 follow-up evidence'],
            'key_watch_items': ['需跟踪 Synthetic Product supply and demand 供需', '需跟踪 Synthetic Product competitor 竞争', '需跟踪 Synthetic Product downstream demand 下游需求'],
            'recent_change': 'Synthetic Product initial draft', 'evidence_claim_ids': [PRODUCT_CLAIM],
            'type_specific': {key: [] for key in ('applications','demand_drivers','supply_capacity','pricing','major_suppliers','product_evolution')}}


def _view(connection, view_id, node_id, version, content, date, seq, previous=None, status='official'):
    connection.execute('''INSERT INTO current_views(view_id,node_id,version,status,change_level,previous_view_id,
        content_md,content_json,trigger_source_id,trigger_claim_ids_json,revision_date,revision_seq,
        accepted_proposal_id,created_at,confirmed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (view_id,node_id,version,status,'baseline' if status == 'baseline' else 'initial' if previous is None else 'minor',previous,'Synthetic markdown',
         json.dumps(content), 'SRC_STAGE3_COMPANY',json.dumps(content['evidence_claim_ids']),date,seq,'',
         date+'T00:00:00+00:00',date+'T00:00:00+00:00'))


def stage3_fixture(root, *, origin='http://127.0.0.1:8000'):
    knowledge=root/'knowledge/synthetic.db'; Database(knowledge).init_schema()
    apply_synthetic_migration(knowledge, configured_production_path=root/'never-production.db', expected_sha256=sha256_file(knowledge))
    with closing(sqlite3.connect(knowledge)) as connection, connection:
        connection.execute("INSERT INTO meta VALUES('workbench_fixture_kind','SYNTHETIC_PUBLIC_SAFE')")
        for row in ((COMPANY,'Synthetic Company','Company'),(PRODUCT,'Synthetic Product','Product'),(TECH,'Synthetic Technology','Technology')):
            connection.execute("INSERT INTO nodes VALUES(?,?,?,'Synthetic Stage 3','active','2026-01-01','2026-01-01')",row)
        sources=(('SRC_STAGE3_COMPANY','Synthetic Company source','2026-02-01'),('SRC_STAGE3_CONTEXT','Synthetic context source',''),('SRC_STAGE3_PRODUCT','Synthetic Product source','2026-03-01'))
        for source_id,title,published in sources:
            connection.execute('''INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,
                analysis_mode,source_type,source_rank,origin_type,author,organization,publication_time,ingested_at,status)
                VALUES(?,?,?,?,?,'synthetic','synthetic','SYNTHETIC_TEXT','A','primary','','Synthetic Org',?,'2026-03-02','stored')''',
                (source_id,title,source_id+'.txt','synthetic/'+source_id,('a' if source_id.endswith('COMPANY') else 'b' if source_id.endswith('CONTEXT') else 'c')*64,published))
        claims=((COMPANY_CLAIM,'Synthetic Company reports stable operations','SRC_STAGE3_COMPANY','fact','2026-02-01','current'),
                (COMPANY_CONTEXT,'Synthetic context mentions the Company','SRC_STAGE3_CONTEXT','fact','','current'),
                (PRODUCT_CLAIM,'Synthetic Product is documented','SRC_STAGE3_PRODUCT','fact','2026-03-01','current'))
        for claim_id,statement,source,nature,fact,status in claims:
            connection.execute('''INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,ingestion_time,
                source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,status,confidence,structured_json,created_at)
                VALUES(?,?,?,?,?,'2026-03-02',?,'synthetic:paragraph:1',?,'','synthetic',?,0.9,?,'2026-03-02')''',
                (claim_id,statement,nature,fact,'',source,statement,status,json.dumps({'validation':{'source_locator':{'status':'resolved','locator':'TEXT'}}})))
        connection.execute('INSERT INTO claim_node_links VALUES(?,?,?)',(COMPANY_CLAIM,COMPANY,'subject'))
        connection.execute('INSERT INTO claim_node_links VALUES(?,?,?)',(COMPANY_CONTEXT,COMPANY,'context'))
        connection.execute('INSERT INTO claim_node_links VALUES(?,?,?)',(PRODUCT_CLAIM,PRODUCT,'subject'))
        old=company_content('Synthetic Company prior conclusion'); _view(connection,'VIEW_STAGE3_OLD',COMPANY,'v_20260101',old,'20260101',0)
        current=company_content(); _view(connection,'VIEW_STAGE3_CURRENT',COMPANY,'v_20260201',current,'20260201',0,'VIEW_STAGE3_OLD')
        baseline=company_content('Synthetic Company baseline projection')
        baseline['artifact_status']='handoff_baseline_not_production_current_view'
        _view(connection,'BASELINE_STAGE3',COMPANY,'baseline_BASELINE_STAGE3',baseline,'20300101',0,status='baseline')
    artifacts=root/'artifacts'; config=WorkbenchConfig('DEMO',knowledge,root/'state/workbench.sqlite3',artifacts,origin)
    Store(config).initialize(); prepare_reviews(config); prepare_attribution(config); prepare_current_views(config)
    return {'config':config,'knowledge':knowledge}
