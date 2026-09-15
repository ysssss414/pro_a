from contextlib import closing
import json
import sqlite3
import uuid

from fastapi.testclient import TestClient
import pytest

from pro_a.operational_contract import snapshot
from pro_a.production_promotion import canonical_sha256
from pro_a.research_explorer import ResearchError, ResearchExplorer
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.research_store import FollowupNotes, NoteError, prepare_research
from pro_a.workbench.review_store import prepare_reviews, schema_version
from pro_a.workbench.store import Store
from workbench_stage3_fixture import COMPANY, PRODUCT, TECH, stage3_fixture
from workbench_stage4_fixture import CONTEXT, SOURCE, SUBJECT, stage4_fixture
from workbench_stage5_fixture import DUPLICATE_NODE, GAP, NO_EVIDENCE_RELATION, RQ, stage5_fixture


@pytest.fixture
def case(tmp_path):
    value = stage5_fixture(tmp_path)
    value['service'] = ResearchExplorer(value['config'])
    return value


def test_schema6_backup_is_exact_additive_idempotent_and_backward_compatible(tmp_path):
    value = stage4_fixture(tmp_path)
    before = value['config'].state_db.read_bytes()
    result = prepare_research(value['config'])
    assert result['schema_version'] == '6'
    assert value['config'].state_db.with_name(value['config'].state_db.name + '.stage4-backup').read_bytes() == before
    assert prepare_research(value['config']) == {'status': 'ALREADY_PREPARED', 'schema_version': '6'}
    assert prepare_reviews(value['config'])['schema_version'] == '6'
    with Store(value['config']).connect() as connection:
        assert schema_version(connection) == '6'
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'followup_notes', 'followup_note_events'} <= tables


def test_global_search_is_bounded_exact_first_typed_and_private_safe(case):
    exact = case['service'].search('Synthetic Company', limit=20)
    node_ids = [row['object_id'] for row in exact['results'] if row['object_type'] == 'NODE']
    assert COMPANY in node_ids and DUPLICATE_NODE in node_ids
    alias = case['service'].search('Synthetic Photonics Alias')
    assert alias['results'][0]['object_id'] == TECH and alias['results'][0]['object_type'] == 'NODE'
    assert any(row['object_type'] == 'CLAIM' for row in case['service'].search('changed recorded')['results'])
    source = case['service'].search('Stage 4 change', object_type='SOURCE')
    assert source['results'][0]['object_id'] == SOURCE
    assert 'archived_path' not in json.dumps(source)
    assert case['service'].search('does not exist')['results'] == []
    with pytest.raises(ResearchError, match='UNSUPPORTED_RESEARCH_OBJECT'):
        case['service'].search('x', object_type='MAGIC')


def test_claim_source_filters_pages_and_stable_order(case):
    first = case['service'].claims(limit=2)
    second = case['service'].claims(cursor=first['next_cursor'], limit=2)
    reloaded = case['service'].claims(cursor=first['next_cursor'], limit=2)
    assert second == reloaded
    assert second['previous_cursor'] == '0'
    assert not ({row['claim_id'] for row in first['items']} & {row['claim_id'] for row in second['items']})
    combined = case['service'].claims(source_id=SOURCE, node_id=COMPANY, role='subject',
                                      nature='fact', status='current', linked=True, cited=True)
    assert [row['claim_id'] for row in combined['items']] == [SUBJECT]
    unlinked = case['service'].claims(source_id=SOURCE, linked=False)
    assert unlinked['items'] and all(not row['linked_nodes'] for row in unlinked['items'])
    assert case['service'].claims(q='no matching claim')['items'] == []
    sources = case['service'].sources(source_type='SYNTHETIC_TEXT', status='stored',
                                      has_claims=True, has_attribution=True, limit=2)
    assert sources['items'] and sources['total'] >= 1
    with pytest.raises(ResearchError, match='INVALID_CURSOR'):
        case['service'].claims(cursor='not-a-cursor')
    with pytest.raises(ResearchError, match='INVALID_CURSOR'):
        case['service'].sources(limit=101)


def test_node_claim_source_and_relation_shared_semantics(case):
    node = case['service'].node(COMPANY)
    assert node['current_view']['view_id'] == 'VIEW_STAGE4_CURRENT'
    assert any(row['claim_id'] == SUBJECT and row['linked_nodes'][0]['role'] == 'subject'
               for row in node['claims']['items'])
    assert node['impact']['items'] and node['coverage']['coverage_is_attribution'] is False
    claim = case['service'].claim(SUBJECT)
    assert claim['source']['source_id'] == SOURCE
    assert any(row['node_id'] == COMPANY and row['role'] == 'subject' for row in claim['linked_nodes'])
    assert any(row['view_id'] == 'VIEW_STAGE4_CURRENT' for row in claim['official_view_citations'])
    assert any(row['relation_type'] == 'contradicts' for row in claim['claim_relations'])
    assert claim['impact']['items']
    source = case['service'].source(SOURCE, claim_limit=2, claim_status='current')
    assert source['claims']['total'] >= 1 and source['claims']['limit'] == 2
    assert any(row['node_id'] == COMPANY for row in source['explicit_nodes'])
    assert source['impact']['items']
    current = case['service'].relation('REL_STAGE4_CURRENT')
    categorical = case['service'].relation('REL_STAGE4_CATEGORY')
    historical = case['service'].relation('REL_STAGE4_HISTORY')
    no_evidence = case['service'].relation(NO_EVIDENCE_RELATION)
    assert current['status_semantics']['current'] is True and current['evidence']
    assert current['evidence'][0]['source_id'] == SOURCE
    assert {row['relation_id'] for row in current['history']} == {'REL_STAGE4_CURRENT', NO_EVIDENCE_RELATION}
    assert categorical['status_semantics'] == {'current': False, 'categorical': True, 'historical': False}
    assert historical['status_semantics']['historical'] is True
    assert no_evidence['status_semantics']['historical'] is True and no_evidence['evidence'] == []
    assert {current['relation']['from_node_id'], current['relation']['to_node_id']} == {PRODUCT, TECH}


def test_coverage_rq_gap_are_read_only_and_never_attribution(case):
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory = sqlite3.Row
        before = canonical_sha256(snapshot(connection))
    FollowupNotes(case['config']).create({
        'operation_id': uuid.uuid4().hex, 'object_type': 'GAP', 'object_id': GAP,
        'text': 'Gather missing evidence', 'status': 'OPEN',
    }, {'actor': 'operator'})
    coverage = case['service'].coverage(limit=2)
    assert coverage['coverage_is_attribution'] is False
    assert coverage['canonical_write'] is False
    assert coverage['summary']['knowledge_gaps'] == 1
    assert coverage['knowledge_gaps'][0]['notes'][0]['text'] == 'Gather missing evidence'
    home_note = case['service'].home()['open_notes'][0]
    assert (home_note['route_kind'], home_note['route_id']) == ('node', TECH)
    assert case['service'].questions()['items'][0]['rq_id'] == RQ
    assert case['service'].gaps()['items'][0]['gap_id'] == GAP
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory = sqlite3.Row
        assert canonical_sha256(snapshot(connection)) == before


def test_followup_notes_persist_conflict_and_do_not_change_canonical_or_impact(case):
    service = FollowupNotes(case['config'])
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory = sqlite3.Row
        before = canonical_sha256(snapshot(connection))
    impact_before = case['service'].claim(SUBJECT)['impact']['snapshot']['snapshot_id']
    request = {'operation_id': uuid.uuid4().hex, 'object_type': 'CLAIM', 'object_id': SUBJECT,
               'text': 'Check next earnings evidence', 'status': 'OPEN'}
    created = service.create(request, {'actor': 'operator'})
    assert service.create(request, {'actor': 'operator'}) == created
    note = created['note']
    updated = service.update(note['note_id'], {'operation_id': uuid.uuid4().hex,
        'expected_revision': 1, 'text': 'Check next earnings evidence and supplier', 'status': 'DEFERRED'},
        {'actor': 'operator'})
    assert updated['note']['revision'] == 2 and updated['note']['status'] == 'DEFERRED'
    restarted = FollowupNotes(case['config']).list(object_type='CLAIM', object_id=SUBJECT)['notes'][0]
    assert restarted['revision'] == 2
    with pytest.raises(NoteError, match='NOTE_REVISION_CONFLICT') as caught:
        service.update(note['note_id'], {'operation_id': uuid.uuid4().hex,
            'expected_revision': 1, 'text': 'stale edit', 'status': 'DONE'}, {'actor': 'operator'})
    assert caught.value.current_revision == 2
    source_note = service.create({'operation_id': uuid.uuid4().hex, 'object_type': 'SOURCE',
        'object_id': SOURCE, 'text': 'Recheck source quality', 'status': 'OPEN'}, {'actor': 'operator'})['note']
    done = service.update(source_note['note_id'], {'operation_id': uuid.uuid4().hex,
        'expected_revision': 1, 'text': source_note['text'], 'status': 'DONE'}, {'actor': 'operator'})
    assert done['note']['status'] == 'DONE' and done['note']['object_id'] == SOURCE
    assert case['service'].claim(SUBJECT)['impact']['snapshot']['snapshot_id'] == impact_before
    with closing(sqlite3.connect(case['knowledge'])) as connection:
        connection.row_factory = sqlite3.Row
        assert canonical_sha256(snapshot(connection)) == before
    assert service.write_count() == 4


def test_authenticated_research_api_and_explicit_safe_errors(case, monkeypatch):
    token = 'synthetic-stage5-browser-token-for-tests-only'
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', token)
    with TestClient(create_app(case['config']), base_url=case['config'].origin,
                    client=('127.0.0.1', 1)) as client:
        assert client.get(PREFIX + '/research/home').status_code == 401
        login = client.post(PREFIX + '/session', headers={'Origin': case['config'].origin}, json={'token': token})
        csrf = login.json()['csrf_token']
        assert client.get(PREFIX + '/research/search?q=Synthetic').status_code == 200
        assert client.get(PREFIX + '/research/nodes/' + COMPANY).status_code == 200
        assert client.get(PREFIX + '/research/claims/' + SUBJECT).status_code == 200
        assert client.get(PREFIX + '/research/sources/' + SOURCE).status_code == 200
        assert client.get(PREFIX + '/research/relations/REL_STAGE4_CATEGORY').json()['status_semantics']['categorical']
        assert client.get(PREFIX + '/research/coverage').json()['coverage_is_attribution'] is False
        body = {'operation_id': uuid.uuid4().hex, 'object_type': 'NODE', 'object_id': COMPANY,
                'text': 'Verify supplier', 'status': 'OPEN'}
        saved = client.post(PREFIX + '/research/notes', headers={'Origin': case['config'].origin,
            'X-CSRF-Token': csrf}, json=body)
        assert saved.status_code == 200 and saved.json()['canonical_write'] is False
        errors = [
            client.get(PREFIX + '/research/nodes/MISSING').json(),
            client.get(PREFIX + '/research/claims/MISSING').json(),
            client.get(PREFIX + '/research/sources/MISSING').json(),
            client.get(PREFIX + '/research/relations/MISSING').json(),
        ]
        assert [row['detail'] for row in errors] == ['NODE_NOT_FOUND','CLAIM_NOT_FOUND','SOURCE_NOT_FOUND','RELATION_NOT_FOUND']
        assert str(case['knowledge']) not in json.dumps(errors)
