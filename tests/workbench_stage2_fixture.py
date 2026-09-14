"""Fresh synthetic Stage 2 evidence; all construction finishes before registration."""
from contextlib import closing
import copy
import json
import sqlite3
import uuid

from workbench_fixture import make_fixture, write, seal, CLAIM, NODE
from pro_a.phase3f_review_completion import build_blank_review_packet
from pro_a.production_promotion import production_identity, sha256_file
from pro_a.workbench.artifacts import Artifacts
from pro_a.workbench.store import Store
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.attribution_store import prepare_attribution

CLAIM_TWO = 'CLM_SYNTHETIC_STAGE2_SECOND'
CLAIM_THREE = 'CLM_SYNTHETIC_STAGE2_THIRD'
REUSE_CANDIDATE = 'CAND_NODE_SYNTHETIC_STAGE2_REUSE'
REUSE_NODE = 'NODE_SYNTHETIC_STAGE2_EXISTING'
CREATE_NODE = 'NODE_SYNTHETIC_STAGE0'
REVIEWER = 'Synthetic Human Reviewer'
IDENTITY = {'actor': 'operator', 'session_id': 'synthetic-stage2-session'}


def stage2_fixture(root, *, origin='http://127.0.0.1:8000', claim_decisions=('KEEP', 'KEEP', 'KEEP'), collision=None):
    fixture = make_fixture(root, node_profile='create', origin=origin)
    config = fixture['config']; run = config.artifact_root / fixture['run_relative']
    with closing(sqlite3.connect(config.knowledge_db)) as connection, connection:
        connection.execute("INSERT INTO nodes VALUES(?,?,'Product','','active','2026-01-01','2026-01-01')", (REUSE_NODE, 'Synthetic Existing Stage 2'))
        connection.execute("INSERT INTO nodes VALUES('NODE_SYNTHETIC_PARENT','Synthetic Parent','Category','','active','2026-01-01','2026-01-01')")
        if collision == 'node': connection.execute("UPDATE nodes SET canonical_name='Synthetic material A' WHERE node_id=?", (REUSE_NODE,))
        if collision == 'alias': connection.execute("INSERT INTO node_aliases VALUES('Synthetic A',?)", (REUSE_NODE,))
        if collision == 'reuse': connection.execute("INSERT INTO node_aliases VALUES('Synthetic Existing Stage 2','NODE_SYNTHETIC_PARENT')")
    baseline = {k:v for k,v in production_identity(config.knowledge_db).items() if k != 'path'}
    bundle_path = run/'evidence/evidence_bound_extraction_bundle.json'
    bundle = json.loads(bundle_path.read_text())
    bundle['source'].update(original_name='synthetic.txt',source_type='SYNTHETIC_TEXT',analysis_mode='synthetic')
    bundle['proposed_source_metadata']={'title':'Synthetic Stage 2 Source','publication_time':'2026-01-01'}
    bundle['claims'][0].update(source_id=bundle['source']['proposed_source_id'],nature='fact',scope='synthetic scope',
                              created_at='2026-01-01T00:00:00+00:00',evidence_validated=True)
    for claim_id in (CLAIM_TWO, CLAIM_THREE):
        claim = copy.deepcopy(bundle['claims'][0]); claim['claim_id'] = claim_id
        bundle['claims'].append(claim)
    write(bundle_path, bundle)
    claim_path = run/'review/claim_review.json'; claim_review = json.loads(claim_path.read_text())
    for claim_id in (CLAIM_TWO, CLAIM_THREE):
        claim = copy.deepcopy(claim_review['claims'][0]); claim['claim_id'] = claim_id
        claim_review['claims'].append(claim)
    claim_review = seal({k:v for k,v in claim_review.items() if k not in ('review_id','review_sha256')}, 'CLAIM_REVIEW', 'review_id', 'review_sha256')
    write(claim_path, claim_review)
    node_path = run/'review/node_operation_review.json'; node_review = json.loads(node_path.read_text())
    reused = copy.deepcopy(node_review['records'][0])
    reused.update(operation_candidate_id=REUSE_CANDIDATE, proposed_name='Synthetic Existing Stage 2', prospective_node_id='NODE_SYNTHETIC_STAGE2_PROSPECTIVE', proposed_aliases=[])
    reused['exact_production_resolution'] = {'candidate_target_node_ids':[REUSE_NODE]}
    node_review['records'].append(reused)
    node_review['operational_run']['claim_review_sha256'] = sha256_file(claim_path)
    node_review['production_baseline'] = baseline
    write(node_path, seal({k:v for k,v in node_review.items() if k not in ('review_id','review_sha256')}, 'NODE_REVIEW', 'review_id', 'review_sha256'))
    preview_path = run/'promotion/promotion_preview.json'; preview=json.loads(preview_path.read_text())
    preview['bindings']['production_baseline']=baseline
    write(preview_path, seal({k:v for k,v in preview.items() if k not in ('preview_id','preview_sha256')}, 'PROMOTION_PREVIEW', 'preview_id','preview_sha256'))
    manifest_path=run/'run_manifest.json'; manifest=json.loads(manifest_path.read_text());manifest['production_baseline']=baseline
    for row in manifest['artifact_inventory']:
        path=run/row['path'];row.update(sha256=sha256_file(path),size_bytes=path.stat().st_size)
    write(manifest_path,manifest)
    fixture['packet']=build_blank_review_packet(run)
    write(config.artifact_root/fixture['packet_relative'],fixture['packet'])
    Store(config).initialize()
    handle=Artifacts(config).register(fixture['packet_relative'],fixture['run_relative'])['artifact_id']
    prepare_reviews(config)
    review=ReviewWorkbench(config)
    for group in ('claims','nodes','relations'):
        for row in fixture['packet'][group]:
            decision=claim_decisions[[CLAIM,CLAIM_TWO,CLAIM_THREE].index(row['candidate_id'])] if group=='claims' else 'REUSE' if row['candidate_id']==REUSE_CANDIDATE else 'CREATE'
            current=review.read(handle)['review']
            review.mutate(handle,'decision',{'basis_id':current['basis_id'],'expected_revision':current['revision'],'operation_id':uuid.uuid4().hex,
                'reviewer':REVIEWER,'reason':'Explicit synthetic native human decision.','candidate_id':row['candidate_id'],'decision':decision,
                'target_node_id':REUSE_NODE if decision=='REUSE' else ''},IDENTITY)
    current=review.read(handle)['review']
    review.mutate(handle,'seal',{'basis_id':current['basis_id'],'expected_revision':current['revision'],'operation_id':uuid.uuid4().hex,
        'reviewer':REVIEWER,'reason':'Explicit native review-only seal.','confirm':True},IDENTITY)
    prepare_attribution(config)
    fixture['handle']=handle
    return fixture
