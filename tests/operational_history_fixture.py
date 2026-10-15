"""Distinct synthetic sources, freshly sealed against each preceding real Apply."""
from contextlib import closing
import json
import shutil
import sqlite3
import uuid

from pro_a.operational_operator import Operator, OperatorConfig
from pro_a.operational_qualification import qualify
from pro_a.phase3f_review_completion import build_blank_review_packet
from pro_a.production_promotion import production_identity, sha256_file
from pro_a.workbench.artifacts import Artifacts
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.attribution_store import prepare_attribution
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.store import Store
from workbench_fixture import make_fixture, seal, write

IDENTITY = {'actor': 'operator', 'session_id': 'synthetic-history'}


def setup(root, *, schema_version='0.2.4'):
    seed = make_fixture(root, node_profile='create')
    cfg = seed['config']
    with closing(sqlite3.connect(cfg.knowledge_db)) as db, db:
        db.execute("INSERT INTO nodes VALUES('NODE_SYNTHETIC_PARENT','Synthetic Parent','Category','','active','2026-01-01','2026-01-01')")
    if schema_version == '0.2.4':
        from pro_a.admission_schema import migrate
        migrate(cfg.knowledge_db, expected_sha256=sha256_file(cfg.knowledge_db),
                backup_path=root / 'synthetic-before-b-lite.db', configured_production_path=cfg.knowledge_db)
    Store(cfg).initialize()
    prepare_reviews(cfg)
    prepare_attribution(cfg)
    operator = Operator(OperatorConfig(cfg, root / 'operator/ledger.db'))
    operator.initialize()
    return seed, operator


def request(service, handle, **extra):
    value = service.read(handle)
    state = value.get('review', value)
    return {'basis_id': state['basis_id'], 'expected_revision': state['revision'],
            'operation_id': uuid.uuid4().hex, 'reviewer': 'Synthetic History Human',
            'reason': 'Explicit isolated fixture review.', **extra}


def prepare(seed, index):
    cfg = seed['config']
    original = cfg.artifact_root / seed['run_relative']
    run = cfg.artifact_root / ('history-' + str(index)) / 'engine'
    shutil.copytree(original, run)
    # These are unregistered blank inputs. All identities are built anew below,
    # before any native review, qualification, Grant or execution.
    baseline = {k: v for k, v in production_identity(cfg.knowledge_db).items() if k != 'path'}
    source = run / 'source/synthetic.txt'
    old_sha = sha256_file(source)
    source.write_text(source.read_text().replace('Synthetic material A', 'Synthetic material ' + str(index)) + 'Independent synthetic source ' + str(index) + '.\n')
    new_sha = sha256_file(source)

    def rewrite(value):
        if isinstance(value, dict):
            return {k: (baseline if k == 'production_baseline' else rewrite(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, str):
            return value.replace(old_sha, new_sha).replace('_STAGE0', '_HISTORY_' + str(index)).replace('Synthetic material A', 'Synthetic material ' + str(index)).replace('Synthetic A', 'Synthetic alias ' + str(index))
        return value

    for path in run.rglob('*.json'):
        write(path, rewrite(json.loads(path.read_text())))
    bundle_path = run / 'evidence/evidence_bound_extraction_bundle.json'
    bundle = json.loads(bundle_path.read_text())
    bundle['source'].update(original_name='synthetic.txt', source_type='SYNTHETIC_TEXT', analysis_mode='synthetic')
    bundle['proposed_source_metadata'] = {'title': 'Synthetic History ' + str(index), 'publication_time': '2026-01-01'}
    bundle['claims'][0].update(source_id=bundle['source']['proposed_source_id'], nature='fact', scope='synthetic scope', created_at='2026-01-01T00:00:00+00:00', evidence_validated=True)
    write(bundle_path, bundle)
    for relative, prefix, id_key, sha_key in (
        ('review/claim_review.json', 'CLAIM_REVIEW', 'review_id', 'review_sha256'),
        ('review/node_operation_review.json', 'NODE_REVIEW', 'review_id', 'review_sha256'),
        ('promotion/promotion_preview.json', 'PROMOTION_PREVIEW', 'preview_id', 'preview_sha256'),
    ):
        path = run / relative
        value = json.loads(path.read_text())
        if prefix == 'NODE_REVIEW':
            value['operational_run']['claim_review_sha256'] = sha256_file(run / 'review/claim_review.json')
        write(path, seal({k: v for k, v in value.items() if k not in (id_key, sha_key)}, prefix, id_key, sha_key))
    manifest_path = run / 'run_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['source']['size_bytes'] = source.stat().st_size
    for row in manifest['artifact_inventory']:
        p = run / row['path']
        row.update(sha256=sha256_file(p), size_bytes=p.stat().st_size)
    write(manifest_path, manifest)
    packet = build_blank_review_packet(run)
    path = run.parent / 'review/packet.json'
    write(path, packet)
    handle = Artifacts(cfg).register(path.relative_to(cfg.artifact_root).as_posix(), run.relative_to(cfg.artifact_root).as_posix())['artifact_id']
    reviews = ReviewWorkbench(cfg)
    for group in ('claims', 'nodes', 'relations'):
        for row in packet[group]:
            reviews.mutate(handle, 'decision', request(reviews, handle, candidate_id=row['candidate_id'], decision='KEEP' if group == 'claims' else 'CREATE', target_node_id=''), IDENTITY)
    reviews.mutate(handle, 'seal', request(reviews, handle, confirm=True), IDENTITY)
    attr = Attribution(cfg)
    context = attr.context(handle)
    for cid, claim in context['claims'].items():
        attr.mutate(handle, 'SAVE', request(attr, handle, claim_id=cid, outcome='LINK', links=[{'node_id': next(iter(context['nodes'])), 'role': 'context'}], scope=claim['scope']), IDENTITY)
    attr.mutate(handle, 'SEAL', request(attr, handle, confirm=True), IDENTITY)
    _, sidecar = attr.sealed_context(handle)
    return handle, qualify(cfg, handle, sidecar['object_id'])


def apply(operator, envelope, *, fault=None):
    eid = envelope['object_id']
    operator.register(eid, confirm=eid)
    receipt = operator.execute(eid, confirm=eid, fault=fault)
    assert operator.reconcile(eid) == receipt
    return receipt
