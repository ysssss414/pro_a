"""Synthetic contract tests only; real qualification uses the private Web-Pro package."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3

import pytest

from pro_a.phase3f_foundation_baseline import validate_files
from pro_a.production_promotion import PromotionError, sha256_file
from pro_a.structured_foundation import (
    TABLES, freeze_contract, qualify, read_package, runtime_digest,
)
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.domains import prepare_domains
from pro_a.workbench.foundation_import import import_package
from pro_a.workbench.review_workbench import ReviewWorkbench, ReviewError
from pro_a.workbench.stage1_scale import LIMITS, Stage1ReviewProjection, prepare_stage1_scale, stage1_capacity, require_stage1_intake
from pro_a.workbench.store import Store
from workbench_stage7_fixture import stage7_fixture

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'domains/semiconductor'


def package_data(name, typ):
    evidence = {'evidence_id': 'EV1', 'source_id': 'S1', 'source_sha256': 'a' * 64,
                'pdf_page': 1, 'section': 'Synthetic', 'evidence_excerpt': 'Synthetic assertion.',
                'excerpt_sha256': hashlib.sha256(b'Synthetic assertion.').hexdigest()}
    node = {'candidate_id': 'N1', 'proposed_canonical_name': name, 'proposed_primary_type': typ,
            'evidence_refs': '["EV1"]', 'disposition': 'CREATE', 'confidence': '0.9',
            'existing_node_id': '', 'possible_existing_node_id': ''}
    second = {**node, 'candidate_id': 'N2', 'proposed_canonical_name': 'New synthetic technology', 'proposed_primary_type': 'Technology'}
    relation = {'relation_candidate_id': 'R1', 'source_ref': 'N1', 'target_ref': 'N2',
        'relation_type': 'uses', 'scope': 'Synthetic', 'evidence_refs': '["EV1"]',
        'direction_check': 'PASS', 'entailment_check': 'PASS', 'disposition': 'ACCEPTABLE',
        'temporal_status': 'source_scoped'}
    data = {
        TABLES['nodes'][0]: [node, second],
        TABLES['aliases'][0]: [{'alias_candidate_id': 'A1', 'alias': 'Synthetic alias',
            'target_existing_node_id': '', 'target_candidate_id': 'N2', 'evidence_refs': '["EV1"]', 'disposition': 'REVIEW'}],
        TABLES['sources'][0]: [{'source_id': 'S1', 'physical_source_id': 'S1', 'sha256': 'a' * 64, 'logical_source_slots': 'L1'}],
        TABLES['evidence'][0]: [evidence], TABLES['relations'][0]: [relation],
        TABLES['native_evidence'][0]: [{'native_evidence_candidate_id': 'NE1', 'relation_candidate_id': 'R1',
            'source_ref': 'N1', 'target_ref': 'N2', 'relation_type': 'uses', 'scope': 'Synthetic',
            'evidence_ref': 'EV1', 'evidence_source_id': 'S1', 'source_sha256': 'a' * 64,
            'evidence_excerpt': 'Synthetic assertion.'}],
        TABLES['claims'][0]: [{'claim_candidate_id': 'C1', 'subject_ref': 'N2', 'source_id': 'S1',
            'source_sha256': 'a' * 64, 'statement': 'Synthetic assertion.', 'nature': 'fact',
            'temporal_category': 'source_scoped', 'evidence_ref': 'EV1',
            'evidence_excerpt': 'Synthetic assertion.', 'confidence': .9, 'review_ready': True}],
        'baseline_views/index.json': [], 'current_view_candidates/index.json': {'candidates': []},
        'source_scope_receipt.csv': [{'source_id': 'S1', 'scope': 'Synthetic'}],
        'provenance/source_manifest_as_uploaded.json': {'synthetic': True},
        'provenance/source_scope_receipt_as_uploaded.csv': [{'source_id': 'S1'}],
        'qa/validation_report.json': {'result': 'PASS', 'failed_checks': [], 'checks_run': 1,
            'checks_passed': 1, 'checks': [{'check': 'synthetic_fixture_only', 'result': 'PASS'}]},
    }
    return data


def write_package(root, data):
    root.mkdir(parents=True, exist_ok=True)
    encoded = {}
    for name, rows in data.items():
        if name.endswith('.csv'):
            stream = io.StringIO(newline='')
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            encoded[name] = stream.getvalue().encode()
        elif name.endswith('.jsonl'):
            encoded[name] = ('\n'.join(json.dumps(row) for row in rows) + '\n').encode()
        else:
            encoded[name] = json.dumps(rows).encode()
    manifest = {'package_name': 'synthetic_qualified_foundation', 'artifact_schema': 'WEB_CANDIDATE_HANDOFF_V1_NOT_RUNTIME_PAYLOAD',
        'generated_at': '2026-01-01T00:00:00Z', 'inputs': {},
        'metrics': {metric: len(data[name]) for name, key, metric in TABLES.values()}}
    manifest['metrics'].update(LOGICAL_SOURCE_SLOTS=1, BASELINE_VIEWS=0, CURRENT_VIEW_CANDIDATES=0)
    encoded['run_manifest.json'] = json.dumps(manifest).encode()
    encoded['PASS_A_IDENTITY_FREEZE.json'] = json.dumps({
        'candidate_identity_sha256': hashlib.sha256(encoded[TABLES['nodes'][0]]).hexdigest(),
        'alias_candidates_sha256': hashlib.sha256(encoded[TABLES['aliases'][0]]).hexdigest()}).encode()
    encoded['PACKAGE_SHA256SUMS.json'] = json.dumps({'algorithm': 'SHA-256',
        'files': {name: hashlib.sha256(value).hexdigest() for name, value in encoded.items() if name != 'qa/validation_report.json'},
        'exclusions': {'PACKAGE_SHA256SUMS.json': 'self', 'qa/validation_report.json': 'upstream receipt'}}).encode()
    for name, value in encoded.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)


@pytest.fixture
def case(tmp_path):
    fixture = stage7_fixture(tmp_path / 'workbench')
    config = fixture['config']
    prepare_domains(config)
    prepare_stage1_scale(config)
    with sqlite3.connect(config.knowledge_db) as connection:
        connection.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES('EXISTING_N1','Synthetic shared material','Product','','active','2026-01-01','2026-01-01')")
        node = connection.execute('SELECT node_id,canonical_name,primary_type FROM nodes LIMIT 1').fetchone()
        connection.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at) VALUES('EXISTING_S1','Synthetic','Synthetic','','" + 'a' * 64 + "','deep','2026-01-01')")
    root = tmp_path / 'package'
    data = package_data(node[1], node[2])
    write_package(root, data)
    return {'config': config, 'package': root, 'data': data, 'node': node[0], 'target': tmp_path}


def freeze(case):
    package = read_package(case['package'])
    contract = freeze_contract(package, pack_root=PACK, production_path=case['config'].knowledge_db,
        target_root=case['target'], repository_commit='e' * 40, runtime_sha256=runtime_digest())
    return package, contract


def run(case):
    package, contract = freeze(case)
    return qualify(package, contract, knowledge_db=case['config'].knowledge_db, pack_root=PACK)


def test_qualified_package_source_and_cross_domain_node_reuse_and_true_create(case):
    packet, report = run(case)
    assert report['sources'] == {'REUSE': 1}
    assert packet['registry']['sources'][0]['resolved_source_id'] == 'EXISTING_S1'
    assert report['classifications']['nodes'] == {'REUSE': 1, 'CREATE': 1}
    assert packet['objects']['nodes'][0]['content']['resolved_node_id'] == case['node']
    assert packet['objects']['nodes'][1]['content']['create_reason']
    assert packet['human_completion'] == {'reviewer': '', 'reason': ''}


@pytest.mark.parametrize('change', ['hash', 'missing', 'duplicate', 'receipt', 'count'])
def test_package_fail_closed(case, change):
    if change == 'duplicate':
        case['data'][TABLES['nodes'][0]].append(copy.deepcopy(case['data'][TABLES['nodes'][0]][0]))
        write_package(case['package'], case['data'])
    elif change == 'receipt':
        path = case['package'] / 'qa/validation_report.json'
        path.write_text(json.dumps({'result': 'FAIL'}))
    elif change == 'missing':
        (case['package'] / TABLES['claims'][0]).unlink()
    elif change == 'count':
        path = case['package'] / 'run_manifest.json'
        body = json.loads(path.read_text()); body['metrics']['NODE_OBSERVATIONS'] = 999
        path.write_text(json.dumps(body))
    else:
        with (case['package'] / TABLES['nodes'][0]).open('ab') as stream:
            stream.write(b'corruption')
    with pytest.raises(BoundaryError):
        read_package(case['package'])


@pytest.mark.parametrize('change,group,reason', [
    ('alias_collision', 'aliases', 'ALIAS_COLLISION'),
    ('ontology', 'nodes', 'ONTOLOGY_PRESSURE'),
    ('missing_evidence', 'claims', 'EVIDENCE_WARNING'),
    ('cross_source', 'claims', 'EVIDENCE_WARNING'),
    ('relation_direction', 'relations', 'RELATION_AMBIGUITY'),
])
def test_governed_exceptions(case, change, group, reason):
    data = case['data']
    if change == 'alias_collision':
        data[TABLES['aliases'][0]][0]['alias'] = data[TABLES['nodes'][0]][0]['proposed_canonical_name']
    elif change == 'ontology':
        data[TABLES['nodes'][0]][1]['proposed_primary_type'] = 'SemiconductorOnlyType'
    elif change == 'missing_evidence':
        data[TABLES['claims'][0]][0]['evidence_ref'] = 'ABSENT'
    elif change == 'cross_source':
        data[TABLES['evidence'][0]][0]['source_id'] = 'DIFFERENT_SOURCE'
    else:
        data[TABLES['relations'][0]][0]['direction_check'] = 'AMBIGUOUS'
    write_package(case['package'], data)
    packet, report = run(case)
    rows = [row for row in packet['objects'][group] if reason in row['content']['reasons']]
    assert rows and all(row['content']['classification'] in ('REVIEW', 'DEFER') for row in rows)


def test_evidence_source_binding_and_lossless_original_fields(case):
    packet, report = run(case)
    claim = packet['objects']['claims'][0]['content']
    assert claim['classification'] == 'ACCEPTABLE' and claim['evidence_bound']
    assert claim['evidence'][0]['source_id'] == claim['source_id']
    assert claim['raw'] == case['data'][TABLES['claims'][0]][0]
    assert set(claim['field_mapping']) == set(claim['raw'])


def test_import_replay_projection_and_ordinary_limits(case, monkeypatch):
    import requests
    monkeypatch.setattr(requests.Session, 'request', lambda *a, **k: pytest.fail('PROVIDER_CALL_FORBIDDEN'))
    package, contract = freeze(case)
    before = sha256_file(case['config'].knowledge_db)
    first = import_package(case['config'], package_root=case['package'], contract=contract, pack_root=PACK)
    second = import_package(case['config'], package_root=case['package'], contract=contract, pack_root=PACK)
    assert not first['duplicate'] and second['duplicate']
    assert first['artifact_id'] == second['artifact_id']
    assert first['report']['structural_sha256'] == second['report']['structural_sha256']
    assert first['provider_calls'] == first['raw_source_extraction_calls'] == 0
    assert sha256_file(case['config'].knowledge_db) == before
    with Store(case['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM source_processing_runs').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM cloud_jobs').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM registered_packets').fetchone()[0] == 1
        assert stage1_capacity(connection)['runs_last_24h'] == 0
    assert LIMITS.runs_per_24h == 3
    projection = Stage1ReviewProjection(case['config'])
    page = projection.page(first['artifact_id'])
    assert page['limit'] == 25 and page['total_native_rows'] == 5
    with pytest.raises(BoundaryError, match='INVALID_REVIEW_PAGE_LIMIT'):
        projection.page(first['artifact_id'], limit=101)
    detail = projection.item(first['artifact_id'], 'A1')
    assert detail['available_decisions'] == [] and detail['nonpromotable']
    with pytest.raises(ReviewError, match='FOUNDATION_NATIVE_REVIEW_REQUIRED'):
        ReviewWorkbench(case['config']).mutate(first['artifact_id'], 'SAVE', {}, {})


def test_deterministic_qualification_and_production_handoff_forbidden(case):
    first, report1 = run(case)
    second, report2 = run(case)
    assert first == second and report1 == report2
    with pytest.raises(PromotionError, match='STRUCTURED_CANDIDATE_NOT_PRODUCTION_HANDOFF'):
        validate_files(first)


@pytest.mark.parametrize('field', ['target_root', 'production_write_allowed', 'runtime_sha256'])
def test_execution_contract_cannot_be_bypassed(case, field):
    package, contract = freeze(case)
    contract[field] = True if field == 'production_write_allowed' else 'changed'
    with pytest.raises(BoundaryError):
        import_package(case['config'], package_root=case['package'], contract=contract, pack_root=PACK)


def test_package_wip_is_global_and_blocks_subsequent_intake_but_not_replay(case):
    nodes = case['data'][TABLES['nodes'][0]]
    template = nodes[1]
    nodes.extend({**template, 'candidate_id': f'EXTRA_{i:03d}',
                  'proposed_canonical_name': f'Fresh synthetic technology {i}'} for i in range(201))
    write_package(case['package'], case['data'])
    _, contract = freeze(case)
    first = import_package(case['config'], package_root=case['package'], contract=contract, pack_root=PACK)
    with Store(case['config']).connect() as connection:
        assert stage1_capacity(connection)['wip_state'] == 'HARD_STOP'
        with pytest.raises(BoundaryError, match='STAGE1_REVIEW_WIP_HARD_LIMIT'):
            require_stage1_intake(connection)
    again = import_package(case['config'], package_root=case['package'], contract=contract, pack_root=PACK)
    assert again['artifact_id'] == first['artifact_id'] and again['duplicate']
    nodes[1]['proposed_canonical_name'] = 'Another fresh technology'
    write_package(case['package'], case['data'])
    _, next_contract = freeze(case)
    with pytest.raises(BoundaryError, match='STAGE1_STRUCTURED_IMPORT_CAPACITY_BLOCKED'):
        import_package(case['config'], package_root=case['package'], contract=next_contract, pack_root=PACK)


def test_private_package_cannot_enter_demo_workbench(case):
    from dataclasses import replace
    from pro_a.workbench.foundation_import import validate_projection
    _, contract = freeze(case)
    with pytest.raises(BoundaryError, match='STRUCTURED_IMPORT_PRIVATE_ONLY'):
        import_package(replace(case['config'], mode='DEMO'), package_root=case['package'], contract=contract, pack_root=PACK)
    packet, _ = run(case)
    with pytest.raises(BoundaryError, match='STRUCTURED_IMPORT_PRIVATE_ONLY'):
        validate_projection(packet, case['package'], 'synthetic', 'synthetic', 'DEMO')
