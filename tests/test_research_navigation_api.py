import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from pro_a.research_navigation import ResearchNavigation
from pro_a.workbench.api import PREFIX, create_app
from workbench_stage3_fixture import COMPANY, PRODUCT
from workbench_stage5_fixture import stage5_fixture


def test_authenticated_navigation_endpoints_are_read_only_and_safe(tmp_path, monkeypatch):
    case = stage5_fixture(tmp_path)
    specs = tmp_path / 'navigation'
    specs.mkdir()
    source = Path(__file__).resolve().parents[1] / 'research_navigation'
    for domain, root in [('ai_hardware', COMPANY), ('semiconductor', PRODUCT)]:
        value = json.loads((source / f'{domain}.json').read_text(encoding='utf-8'))
        value['root_node_ids'] = [root]
        (specs / f'{domain}.json').write_text(json.dumps(value), encoding='utf-8')
    monkeypatch.setattr('pro_a.workbench.api.ResearchNavigation',
                        lambda config: ResearchNavigation(config, spec_dir=specs))
    token = 'synthetic-stage4a-browser-token-for-tests-only'
    monkeypatch.setenv('PRO_A_WORKBENCH_TOKEN', token)
    before = hashlib.sha256(case['config'].knowledge_db.read_bytes()).hexdigest()
    with TestClient(create_app(case['config']), base_url=case['config'].origin,
                    client=('127.0.0.1', 1)) as client:
        assert client.get(PREFIX + '/research/domains').status_code == 401
        client.post(PREFIX + '/session', headers={'Origin': case['config'].origin}, json={'token': token})
        listing = client.get(PREFIX + '/research/domains')
        assert listing.status_code == 200
        assert [row['domain_id'] for row in listing.json()['domains']] == ['ai_hardware', 'semiconductor']
        tree = client.get(PREFIX + '/research/domains/ai_hardware/tree')
        assert tree.status_code == 200 and tree.json()['roots'][0]['node_id'] == COMPANY
        context = client.get(PREFIX + f'/research/nodes/{COMPANY}/domain-context')
        assert context.status_code == 200
        assert context.json()['navigation_contexts'][0]['domain_id'] == 'ai_hardware'
        assert context.json()['operational_domain_assignments'] == []
        assert client.get(PREFIX + '/research/domains/unknown/tree').status_code == 404
        assert client.get(PREFIX + '/research/domains/ai_hardware/tree?max_depth=13').status_code == 422
        for response in (listing, tree, context):
            assert str(tmp_path) not in response.text
            assert str(case['config'].artifact_root) not in response.text
    assert hashlib.sha256(case['config'].knowledge_db.read_bytes()).hexdigest() == before
