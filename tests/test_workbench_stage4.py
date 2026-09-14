from contextlib import closing
import json
import sqlite3
import uuid

from fastapi.testclient import TestClient
import pytest

from pro_a.direct_impact import DirectImpact, ImpactError
from pro_a.operational_contract import snapshot
from pro_a.production_promotion import canonical_sha256
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.impact_store import prepare_impact
from pro_a.workbench.review_store import prepare_reviews, schema_version
from pro_a.workbench.store import Store
from workbench_stage3_fixture import COMPANY, _view, company_content, stage3_fixture
from workbench_stage4_fixture import (CONTEXT, COOCCUR, DEFERRED, DRAFT, HISTORICAL, HISTORICAL_VIEW, INACTIVE,
                                      OFFICIAL, SOURCE, SUBJECT, UNATTRIBUTED, UNLINKED, UPDATE,
                                      stage4_fixture)


@pytest.fixture
def case(tmp_path):
    value = stage4_fixture(tmp_path)
    value['service'] = DirectImpact(value['config'])
    return value


def test_schema5_backup_is_exact_additive_and_idempotent(tmp_path):
    value = stage3_fixture(tmp_path)
    before = value['config'].state_db.read_bytes()
    result = prepare_impact(value['config'])
    assert result['schema_version'] == '5'
    assert value['config'].state_db.with_name(value['config'].state_db.name + '.stage3-backup').read_bytes() == before
    assert prepare_impact(value['config']) == {'status': 'ALREADY_PREPARED', 'schema_version': '5'}
    assert prepare_reviews(value['config'])['schema_version'] == '5'
    with Store(value['config']).connect() as connection:
        assert schema_version(connection) == '5'
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'impact_attention_states', 'impact_attention_events'} <= tables


def test_direct_paths_roles_views_unlinked_and_staged_split(case):
    result = case['service'].source(SOURCE)
    assert result == case['service'].source(SOURCE)
    assert result['snapshot']['query_count'] == 9
    items = result['items']
    assert any(i['reason_code'] == 'SOURCE_CONTAINS_CLAIM' and i['target_id'] == UNLINKED for i in items)
    assert any(i['reason_code'] == 'CLAIM_ATTRIBUTED_TO_NODE' and i['attribution_role'] == 'subject' for i in items)
    assert any(i['reason_code'] == 'CLAIM_ATTRIBUTED_TO_NODE' and i['attribution_role'] == 'context' for i in items)
    assert len([i for i in items if i['reason_code'] == 'CLAIM_ATTRIBUTED_TO_NODE' and
                any(step['object_id'] == SUBJECT for step in i['path_steps'])]) == 2
    assert any(i['reason_code'] == 'NODE_HAS_OFFICIAL_VIEW' and i['target_id'] == OFFICIAL for i in items)
    assert any(ref.get('status') == 'EVIDENCE_NOT_RESOLVED' for i in items
               if i['reason_code'] == 'NODE_HAS_OFFICIAL_VIEW' for ref in i['evidence_refs'])
    assert any(i['reason_code'] == 'CLAIM_CITED_BY_VIEW' and i['target_id'] == OFFICIAL for i in items)
    assert any(i['reason_code'] == 'STAGED_VIEW_DEPENDENCY' and i['target_id'] == DRAFT and i['official_or_staged'] == 'STAGED' for i in items)
    assert any(i['reason_code'] == 'CLAIM_ATTRIBUTED_TO_NODE' and i['target_id'] == 'NODE_STAGE3_TECH'
               and not any(v['reason_code'] == 'NODE_HAS_OFFICIAL_VIEW' and v['attribution_role'] == 'related'
                           for v in items) for i in items)
    assert not any(i['target_id'] in {HISTORICAL_VIEW, 'BASELINE_STAGE4'} for i in items)
    inactive = next(i for i in items if i['reason_code'] == 'CLAIM_ATTRIBUTED_TO_NODE' and i['target_id'] == INACTIVE)
    assert inactive['current_status'] == 'inactive' and inactive['is_current_impact'] is False
    assert not any(i['reason_code'] == 'NODE_HAS_OFFICIAL_VIEW' and i['attribution_role'] == 'context' for i in items)
    for claim_id in (UNLINKED, DEFERRED, COOCCUR):
        paths = [i for i in items if any(s['object_id'] == claim_id for s in i['path_steps'])]
        assert paths and {i['target_type'] for i in paths} == {'CLAIM'}


def test_false_positive_controls_and_noncurrent_relations(case):
    result = case['service'].source(SOURCE)
    items = result['items']
    assert not any(any(step['object_id'] == UNATTRIBUTED for step in item['path_steps']) for item in items)
    categorical = next(i for i in items if i['target_id'] == 'REL_STAGE4_CATEGORY')
    historical = next(i for i in items if i['target_id'] == 'REL_STAGE4_HISTORY')
    assert (categorical['official_or_staged'], categorical['current_status'], categorical['is_current_impact']) == ('CATEGORICAL', 'categorical', False)
    assert categorical['temporal_status']['temporal_relation'] == 'timeless_structural'
    assert categorical['temporal_status']['effective_date'] == 'unknown'
    current = next(i for i in items if i['target_id'] == 'REL_STAGE4_CURRENT')
    assert (historical['official_or_staged'], historical['is_current_impact']) == ('HISTORICAL', False)
    assert (current['official_or_staged'], current['is_current_impact']) == ('CURRENT', True)
    assert not any(item['reason_code'] in {'CLAIM_ATTRIBUTED_TO_NODE', 'NODE_HAS_OFFICIAL_VIEW'} and
                   any(step['object_id'] in {UNLINKED, DEFERRED, COOCCUR} for step in item['path_steps']) for item in items)


def test_recorded_contradiction_and_temporal_semantics_are_literal(case):
    items = case['service'].source(SOURCE)['items']
    contradiction = [i for i in items if i['reason_code'] == 'RECORDED_CONTRADICTION']
    temporal = [i for i in items if i['reason_code'] == 'TEMPORAL_SUPERSESSION']
    assert contradiction and all('CONTRADICTS' in i['relationship_types'] or 'RELATION_EVIDENCE_CONTRADICTS' in i['relationship_types'] for i in contradiction)
    assert any(i['target_id'] == HISTORICAL for i in temporal)
    assert all(i['temporal_status']['temporal_relation'] == 'updates' for i in temporal)
    unlinked = case['service'].claim(UNLINKED)
    assert not any(i['reason_code'] == 'RECORDED_CONTRADICTION' for i in unlinked['items'])
    assert not any('confirmed' in json.dumps(i).lower() for i in unlinked['items'])


def test_reverse_reads_and_exact_item_path(case):
    source = case['service'].source(SOURCE)
    cited = next(i for i in source['items'] if i['reason_code'] == 'CLAIM_CITED_BY_VIEW')
    detail = case['service'].item(cited['impact_id'])
    assert detail['item'] == cited
    assert [s['object_type'] for s in cited['path_steps']] == ['SOURCE', 'CLAIM', 'VIEW']
    assert any(i['target_id'] == OFFICIAL for i in case['service'].claim(SUBJECT)['items'])
    assert any(i['target_id'] == OFFICIAL for i in case['service'].node(COMPANY)['items'])
    assert any(i['target_id'] == OFFICIAL for i in case['service'].view(OFFICIAL)['items'])
    with pytest.raises(ImpactError, match='NONCURRENT_RELATION'):
        case['service'].view('VIEW_STAGE3_OLD')
    with pytest.raises(ImpactError, match='IMPACT_PATH_NOT_FOUND'):
        case['service'].item(cited['impact_id'][:-1] + ('0' if cited['impact_id'][-1] != '0' else '1'))


def test_snapshot_invalidation_and_official_staged_separation(case):
    first = case['service'].source(SOURCE)
    official_ids = {i['impact_id'] for i in first['items'] if i['official_or_staged'] == 'OFFICIAL'}
    with Store(case['config']).connect(operator_write=True) as connection:
        row = connection.execute('SELECT body FROM view_drafts WHERE node_id=?', ('NODE_STAGE3_PRODUCT',)).fetchone()
        body = json.loads(row['body'])
        body['context_claim_ids'] = [SUBJECT]
        connection.execute('UPDATE view_drafts SET revision=2,body=?,updated_at=? WHERE node_id=?',
                           (json.dumps(body, sort_keys=True), '2026-04-04T00:00:00+00:00', 'NODE_STAGE3_PRODUCT'))
        event = {'revision': 2, 'action': 'SAVE', 'body': body, 'reviewer': 'Synthetic Impact Reviewer',
                 'reason': 'Synthetic staged update', 'updated_at': '2026-04-04T00:00:00+00:00'}
        connection.execute('INSERT INTO view_draft_events VALUES(?,?,?,?,?,?)',
                           ('NODE_STAGE3_PRODUCT', 2, '00000000-0000-0000-0000-000000000005',
                            'c' * 64, json.dumps(event, sort_keys=True), '{}'))
    staged_change = case['service'].source(SOURCE)
    assert staged_change['snapshot']['snapshot_id'] != first['snapshot']['snapshot_id']
    assert {i['impact_id'] for i in staged_change['items'] if i['official_or_staged'] == 'OFFICIAL'} == official_ids
    assert any(i['official_or_staged'] == 'STAGED' for i in staged_change['items'])
    with closing(sqlite3.connect(case['knowledge'])) as connection, connection:
        content = company_content('Synthetic Stage 4 newly activated official')
        content['evidence_claim_ids'] = [SUBJECT]
        _view(connection, 'VIEW_STAGE4_NEW_RECEIPT', COMPANY, 'v_20260501', content,
              '20260501', 0, OFFICIAL)
    second = case['service'].source(SOURCE)
    assert second['snapshot']['snapshot_id'] != staged_change['snapshot']['snapshot_id']
    assert {i['target_id'] for i in second['items'] if i['official_or_staged'] == 'OFFICIAL'} == {'VIEW_STAGE4_NEW_RECEIPT'}
    assert any(i['official_or_staged'] == 'STAGED' for i in second['items'])


def test_attention_state_persists_conflicts_and_never_writes_knowledge(case):
    service = case['service']
    projected = service.source(SOURCE)
    item = next(i for i in projected['items'] if i['reason_code'] == 'CLAIM_ATTRIBUTED_TO_NODE'
                and i['target_id'] == COMPANY)
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory = sqlite3.Row
        before = canonical_sha256(snapshot(connection))
    request = {'snapshot_id': item['snapshot_id'], 'expected_revision': 0,
               'operation_id': str(uuid.uuid4()), 'reviewer': 'Stage 4 Reviewer',
               'reason': 'Recorded human attention only', 'outcome': 'NO_CHANGE'}
    response = service.set_attention(item['impact_id'], request, {'actor': 'operator'})
    assert response['canonical_write'] is False and response['attention_state']['revision'] == 1
    restarted = DirectImpact(case['config']).item(item['impact_id'])['item']['attention_state']
    assert restarted['outcome'] == 'NO_CHANGE' and restarted['status'] == 'CURRENT'
    assert service.set_attention(item['impact_id'], request, {'actor': 'operator'}) == response
    conflict = {**request, 'operation_id': str(uuid.uuid4()), 'outcome': 'MINOR'}
    with pytest.raises(ImpactError, match='REVISION_CONFLICT') as caught:
        service.set_attention(item['impact_id'], conflict, {'actor': 'operator'})
    assert caught.value.current_revision == 1
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory = sqlite3.Row
        assert canonical_sha256(snapshot(connection)) == before
    with Store(case['config']).connect() as connection:
        assert connection.execute('SELECT count(*) FROM impact_attention_states').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM impact_attention_events').fetchone()[0] == 1
    with closing(sqlite3.connect(case['knowledge'])) as connection, connection:
        content = company_content('Synthetic attention snapshot changed')
        content['evidence_claim_ids'] = [SUBJECT]
        _view(connection, 'VIEW_STAGE4_ATTENTION_NEW', COMPANY, 'v_20260601', content,
              '20260601', 0, OFFICIAL)
    assert service.item(item['impact_id'])['item']['attention_state']['status'] == 'STALE'


def test_authenticated_api_contract_and_safe_errors(case, monkeypatch):
    token = 'synthetic-stage4-browser-token-for-tests-only'
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', token)
    app = create_app(case['config'])
    with TestClient(app, base_url=case['config'].origin, client=('127.0.0.1', 1)) as client:
        assert client.get(PREFIX + '/impact/changes').status_code == 401
        login = client.post(PREFIX + '/session', headers={'Origin': case['config'].origin}, json={'token': token})
        csrf = login.json()['csrf_token']
        changes = client.get(PREFIX + '/impact/changes').json()
        change = next(row for row in changes['changes'] if row['source']['source_id'] == SOURCE)
        item = next(i for i in change['items'] if i['reason_code'] == 'CLAIM_CITED_BY_VIEW')
        assert client.get(PREFIX + '/impact/item/' + item['impact_id']).json()['item']['impact_id'] == item['impact_id']
        assert client.get(PREFIX + '/sources/' + SOURCE + '/impact').status_code == 200
        assert client.get(PREFIX + '/claims/' + SUBJECT + '/impact').status_code == 200
        assert client.get(PREFIX + '/views/' + OFFICIAL + '/evidence-impact').status_code == 200
        body = {'snapshot_id': item['snapshot_id'], 'expected_revision': 0,
                'operation_id': str(uuid.uuid4()), 'reviewer': 'API Reviewer', 'reason': 'Needs explicit review',
                'outcome': 'MATERIAL'}
        saved = client.put(PREFIX + '/impact/item/' + item['impact_id'] + '/attention',
                           headers={'Origin': case['config'].origin, 'X-CSRF-Token': csrf}, json=body)
        assert saved.status_code == 200 and saved.json()['production_authorized'] is False
        error = client.get(PREFIX + '/impact/item/unsafe').json()
        assert error == {'detail': 'IMPACT_PATH_NOT_FOUND', 'current_revision': None}
        assert str(case['knowledge']) not in json.dumps(error)
