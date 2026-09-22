"""Frozen Stage 4D overlay boundaries; no Production or Workbench mutation."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from pro_a.qualified_overlay import QualifiedResearchOverlay
from pro_a.research_explorer import ResearchError
from pro_a.research_structure_map import ResearchStructureMap
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.store import Store
from scripts.build_phase43_stage4d_overlay import build, OUTPUT, AUTHORITY_OUTPUT, STAGE3_REVIEW

ROOT = Path(__file__).resolve().parents[1]
READY = STAGE3_REVIEW.is_file() and (ROOT / 'workspace/pro_a.db').is_file() and OUTPUT.is_file()
pytestmark = pytest.mark.skipif(not READY, reason='frozen Stage 3 private review or Production snapshot unavailable')


@pytest.fixture
def overlay():
    config = WorkbenchConfig.load(ROOT / 'workbench.toml')
    return QualifiedResearchOverlay(config)


def test_builder_binds_100_decisions_and_revised_endpoint_authority():
    value = build()
    assert value == build()
    assert value['counts'] == {
        'stage3_identity': {'REUSE_CANONICAL': 19, 'CREATE_NEW_CANONICAL': 12, 'DEFER': 14, 'REJECT': 1},
        'stage3_relation': {'CREATE_RELATION': 38, 'DEFER_RELATION': 16},
        'stage2_support': 17, 'endpoint_references': 26, 'relation_endpoint_occurrences': 76,
        'full_identity_authority_relations': 17, 'reference_backed_relations': 21,
        'unique_reuse_targets': 19,
    }
    assert len({row['visual_id'] for row in value['identities']['stage3_create']}) == 12
    assert len({row['visual_id'] for row in value['identities']['stage2_support']}) == 17
    assert len({row['reuse_target_node_id'] for row in value['identities']['reuse']}) == 19
    assert all(row['visual_id'].startswith('endpoint-ref:') and not row['identity_qualified']
               and not row['search_eligible'] and not row['hierarchy_eligible']
               for row in value['endpoint_references'])
    authorities = json.loads(AUTHORITY_OUTPUT.read_text(encoding='utf-8'))['endpoints']
    assert len(authorities) == 76
    assert all(row['target'] == row['visual_id'] for row in authorities)
    assert {row['authority'] for row in authorities} == {
        'production_canonical', 'stage3_human_identity', 'stage2_human_identity',
        'relation_scoped_reference'}
    assert len([row for row in authorities if row['authority'] == 'relation_scoped_reference']) == 29


def test_overlay_readonly_map_selection_search_and_governance(overlay):
    production = ROOT / 'workspace/pro_a.db'
    workbench = ROOT / 'workspace/workbench/state.sqlite3'
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (production, workbench)]
    summary = overlay.summary()
    assert summary['binding_status'] == 'PASS'
    assert summary['visible_qualified_nodes'] == 29
    assert summary['visible_qualified_relations'] == 38
    assert overlay.node('SC-CN-0033')['display_name'] == 'Chiplet'
    assert overlay.node('SC-CN-0033')['current_view'] is None
    assert overlay.node('SC-CN-0034')['qualification_stage'] == 'Stage 2'
    with pytest.raises(ResearchError, match='QUALIFIED_NODE_NOT_FOUND'):
        overlay.node('SC-CN-0024')
    assert 'SC-CN-0024' not in [row['candidate_id'] for row in overlay.search('SC-CN-0024')['results']]
    governance = overlay.governance()
    assert [len(governance[key]) for key in ('deferred_identities', 'deferred_relations',
                                            'rejected_identities', 'endpoint_references')] == [14, 16, 1, 26]
    hierarchy = overlay.structure_map('semiconductor', mode='hierarchy')
    assert not any(row['knowledge_state'] == 'relation_endpoint_reference' for row in hierarchy['nodes'])
    assert hierarchy['omitted_reference_hierarchy_relations'] > 0
    relationship = overlay.structure_map('semiconductor', mode='relationship', qualified_id='SC-CN-0034')
    assert {row['endpoint_reference_id'] for row in relationship['nodes']
            if row['endpoint_reference_id']} == {'SC-CN-0024'}
    assert relationship['edges'][0]['qualified_relation_id'] == 'SC-RL-0027'
    focus = overlay.structure_map('semiconductor', mode='focus', qualified_id='SC-CN-0004', depth=2)
    assert focus['contains_relation_scoped_reference']
    assert focus == overlay.structure_map('semiconductor', mode='focus', qualified_id='SC-CN-0004', depth=2)
    assert len(focus['nodes']) <= 80 and len(focus['edges']) <= 160
    with pytest.raises(ResearchError, match='QUALIFIED_SELECTION_CONFLICT'):
        overlay.structure_map('semiconductor', mode='focus', node_id='NODE_20260817_4452D283',
                              qualified_id='SC-CN-0004')
    canonical = ResearchStructureMap(overlay.config).structure_map('semiconductor', mode='hierarchy')
    assert canonical['nodes'] and all('visual_id' not in row for row in canonical['nodes'])
    after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (production, workbench)]
    assert before == after


def test_overlay_hash_or_production_drift_fails_closed(overlay, tmp_path, monkeypatch):
    tampered = tmp_path / 'overlay.json'
    tampered.write_bytes(OUTPUT.read_bytes() + b' ')
    overlay.overlay_path = tampered
    with pytest.raises(ResearchError, match='QUALIFIED_OVERLAY_BINDING_FAILED'):
        overlay.summary()
    overlay.overlay_path = OUTPUT
    monkeypatch.setattr('pro_a.qualified_overlay.sha256_file',
                        lambda path: '0' * 64 if Path(path) == overlay.config.knowledge_db
                        else hashlib.sha256(Path(path).read_bytes()).hexdigest())
    with pytest.raises(ResearchError, match='QUALIFIED_OVERLAY_BINDING_FAILED'):
        overlay.summary()


def test_authenticated_overlay_api_uses_readonly_production_copy(tmp_path, monkeypatch):
    (tmp_path / 'knowledge').mkdir()
    (tmp_path / 'state').mkdir()
    knowledge = tmp_path / 'knowledge/production-copy.db'
    shutil.copyfile(ROOT / 'workspace/pro_a.db', knowledge)
    config = WorkbenchConfig(mode='PRIVATE', knowledge_db=knowledge,
                             state_db=tmp_path / 'state/state.sqlite3', artifact_root=tmp_path / 'artifacts',
                             origin='http://127.0.0.1:8000')
    token = 'stage4d-test-token-with-at-least-32-characters'
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', token)
    Store(config).initialize()
    before = hashlib.sha256(knowledge.read_bytes()).hexdigest()
    with TestClient(create_app(config), base_url=config.origin, client=('127.0.0.1', 1)) as client:
        assert client.get(PREFIX + '/research/qualified-overlay').status_code == 401
        client.post(PREFIX + '/session', headers={'Origin': config.origin}, json={'token': token})
        summary = client.get(PREFIX + '/research/qualified-overlay')
        assert summary.status_code == 200 and summary.json()['visible_qualified_relations'] == 38
        node = client.get(PREFIX + '/research/qualified-overlay/nodes/SC-CN-0034')
        assert node.status_code == 200 and node.json()['qualification_stage'] == 'Stage 2'
        assert client.get(PREFIX + '/research/qualified-overlay/nodes/SC-CN-0024').status_code == 404
        governance = client.get(PREFIX + '/research/qualified-overlay/governance')
        assert governance.status_code == 200 and len(governance.json()['endpoint_references']) == 26
        search = client.get(PREFIX + '/research/qualified-overlay/search?q=Chiplet')
        assert search.status_code == 200 and any(row['candidate_id'] == 'SC-CN-0033'
                                                  for row in search.json()['results'])
        assert not client.get(PREFIX + '/research/qualified-overlay/search?q=SC-CN-0024').json()['results']
        direct = client.get(PREFIX + '/research/domains/semiconductor/qualified-structure-map',
                            params={'mode': 'relationship', 'qualified_id': 'SC-CN-0034'})
        assert direct.status_code == 200
        assert direct.json()['stats']['endpoint_references'] == 1
        assert client.get(PREFIX + '/research/domains/semiconductor/qualified-structure-map',
                          params={'mode': 'relationship', 'qualified_id': 'SC-CN-0034',
                                  'node_id': 'NODE_20260817_4452D283'}).status_code == 422
        canonical = client.get(PREFIX + '/research/domains/semiconductor/structure-map?mode=hierarchy')
        assert canonical.status_code == 200 and all('visual_id' not in row for row in canonical.json()['nodes'])
        for response in (summary, node, governance, direct):
            assert str(ROOT) not in response.text and str(tmp_path) not in response.text
    assert hashlib.sha256(knowledge.read_bytes()).hexdigest() == before
