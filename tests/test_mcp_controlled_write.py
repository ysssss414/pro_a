"""Disposable controlled MCP review, no external providers or production services."""
import asyncio
import copy
import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from pro_a.mcp.errors import BridgeError
from pro_a.mcp.server import create_server
from pro_a.mcp.service import ReadService, TOOLS
from pro_a.mcp.write_service import WritePolicy, WriteService, WRITE_TOOLS, EXTRA_READ_TOOLS
from pro_a.workbench.api import create_app, PREFIX
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_batch import ReviewBatch
from test_candidate_advice_submission import advice_case


@pytest.fixture(autouse=True)
def no_operator_apply(monkeypatch):
    monkeypatch.setattr('pro_a.operational_operator.Operator.execute',
                        lambda *a, **k: pytest.fail('CANONICAL_APPLY_FORBIDDEN'))


def writer(value, slot='A', **changes):
    return WriteService(value['config'], WritePolicy(**{
        'enabled': True, 'artifact_ids': (value['handle'],), 'slot': slot,
        'reviewer_id': 'synthetic-' + slot, 'execution_id': 'isolated-session-' + slot,
        'model': 'synthetic-reviewer-v1', 'isolation_attested_by_operator': True, **changes}))


def submit_pair(value):
    from mcp import Client
    async def run():
        for slot in ('A', 'B'):
            opinion = {k: v for k, v in value['opinions'][slot].items() if k != 'reviewer_type'}
            async with Client(create_server(ReadService(value['config']), writer(value, slot))) as session:
                saved = await session.call_tool('submit_reviewer_advice', {'artifact_id': value['handle'], **opinion})
                assert not saved.is_error, saved
    asyncio.run(run())


def prepare(value):
    service = writer(value)
    context = service.get_review_batch_context(value['handle'])
    items = [{'candidate_id': r['candidate_id'], 'content_sha256': r['content_sha256'],
              'decision': 'KEEP' if r['candidate_type'] == 'CLAIM' else 'CREATE',
              'reason': 'Synthetic evidence checked', 'target_node_id': ''} for r in context['candidates']]
    return mcp_call(value, 'prepare_human_review_batch', {'binding': context['binding'],
                    'expected_revision': context['revision'], 'items': items, 'reason': 'Synthetic complete batch'})


def mcp_call(value, name, arguments):
    from mcp import Client
    async def run():
        async with Client(create_server(ReadService(value['config']), writer(value))) as session:
            result = await session.call_tool(name, {'artifact_id': value['handle'], **arguments})
            assert not result.is_error, result
            return result.structured_content
    return asyncio.run(run())


def client(value, monkeypatch):
    monkeypatch.setenv(value['config'].session_token_env, 'synthetic-human-login-' + 'x' * 32)
    app = create_app(value['config'])
    http = TestClient(app, base_url=value['config'].origin, client=('127.0.0.1', 50001))
    headers = {'Origin': value['config'].origin}
    session = http.post(PREFIX + '/session', headers=headers, json={'token': 'synthetic-human-login-' + 'x' * 32})
    assert session.status_code == 200, session.text
    headers['X-CSRF-Token'] = session.json()['csrf_token']
    return http, headers


def test_advice_proposal_human_gate_and_seals(advice_case, monkeypatch):
    value = advice_case
    submit_pair(value)
    proposal = prepare(value)
    assert value['reviews'].read(value['handle'])['review']['revision'] == 0
    with pytest.raises(BoundaryError, match='HUMAN_USER_REQUIRED'):
        ReviewBatch(value['config']).approve(value['handle'], proposal['proposal_id'], {'principal_type': 'MODEL'}, confirm=True)
    http, headers = client(value, monkeypatch)
    endpoint = PREFIX + '/reviews/' + value['handle'] + '/batch-approval'
    body = {'proposal_id': proposal['proposal_id'], 'confirm': True}
    assert http.post(endpoint, json=body, headers={'Origin': value['config'].origin}).status_code == 403
    assert http.post(endpoint, json={**body, 'principal_type': 'HUMAN_USER'}, headers=headers).status_code == 422
    assert http.post(endpoint, json={**body, 'items': []}, headers=headers).status_code == 422
    approved = http.post(endpoint, json=body, headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()['status'] == 'SEALED'
    assert http.post(endpoint, json=body, headers=headers).json() == approved.json()
    context = writer(value).get_review_batch_context(value['handle'], 'attribution')
    items = [{'claim_id': r['candidate_id'], 'content_sha256': r['content_sha256'], 'scope': r['scope'],
              'outcome': 'NO_LINK', 'links': [], 'reason': 'No specific entity assertion'} for r in context['claims']]
    attr = mcp_call(value, 'prepare_attribution_batch', {'binding': context['binding'],
                    'expected_revision': context['revision'], 'items': items, 'reason': 'Synthetic attribution batch'})
    sealed = http.post(endpoint, json={'proposal_id': attr['proposal_id'], 'confirm': True}, headers=headers)
    assert sealed.status_code == 200, sealed.text
    from pro_a.operational_qualification import qualify
    envelope = qualify(value['config'], value['handle'], sealed.json()['result']['sidecar_id'])
    projection = writer(value).get_shadow_qualification(value['handle'])
    assert projection['object_id'] == envelope['object_id']
    assert projection['operator_status'] == 'AWAITING_OPERATOR_ACTION'
    assert value['config'].knowledge_db.read_bytes() == value['production']


def test_optional_tools_and_original_contract(advice_case):
    async def check():
        from mcp import Client
        async with Client(create_server(ReadService(advice_case['config']))) as client:
            base = (await client.list_tools()).tools
        async with Client(create_server(ReadService(advice_case['config']), writer(advice_case))) as client:
            enabled = (await client.list_tools()).tools
        assert len(base) == 14
        original = {t.name: t.model_dump() for t in base}
        assert {t.name: t.model_dump() for t in enabled if t.name in TOOLS} == original
        assert {t.name for t in enabled} == set(TOOLS + WRITE_TOOLS + EXTRA_READ_TOOLS)
        for t in enabled:
            assert t.annotations.read_only_hint == (t.name not in WRITE_TOOLS)
    asyncio.run(check())


@pytest.mark.parametrize('fault', ['context', 'universe', 'content', 'identity', 'private'])
def test_advice_rejections(advice_case, fault):
    value = advice_case
    opinion = {k: copy.deepcopy(v) for k, v in value['opinions']['A'].items() if k != 'reviewer_type'}
    if fault == 'context': opinion['context_sha256'] = '0' * 64
    if fault == 'universe': opinion['items'].pop()
    if fault == 'content': opinion['items'][0]['content_sha256'] = '0' * 64
    if fault == 'identity': opinion['reviewer_id'] = 'HUMAN_USER'
    if fault == 'private': opinion['items'][0]['reason'] = 'Bearer private-credential'
    with pytest.raises(BridgeError): writer(value).submit_reviewer_advice(value['handle'], **opinion)
    assert value['reviews'].read(value['handle'])['review']['revision'] == 0


def test_conflicts_drift_partial_restart_and_concurrent_approval(advice_case, monkeypatch):
    value = advice_case
    submit_pair(value)
    opinion = {k: copy.deepcopy(v) for k, v in value['opinions']['A'].items() if k != 'reviewer_type'}
    service = writer(value)
    before = value['config'].state_db.read_bytes()
    service.submit_reviewer_advice(value['handle'], **opinion)
    assert value['config'].state_db.read_bytes() == before
    opinion['items'][0]['reason'] = 'Conflicting third opinion'
    with pytest.raises(BridgeError, match='ADVICE_SUBMISSION_CONFLICT'):
        service.submit_reviewer_advice(value['handle'], **opinion)
    proposal = prepare(value)
    assert prepare(value) == proposal
    context = service.get_review_batch_context(value['handle'])
    for field in ('context_sha256', 'packet_sha256', 'review_basis_id'):
        binding = {**context['binding'], field: '0' * 64}
        with pytest.raises(BridgeError, match='BATCH_BINDING_DRIFT'):
            service.prepare_human_review_batch(value['handle'], binding, 0, proposal['proposal']['items'], 'Drift')
    with pytest.raises(BridgeError, match='REVISION_CONFLICT'):
        service.prepare_human_review_batch(value['handle'], context['binding'], 1, proposal['proposal']['items'], 'Drift')
    http, headers = client(value, monkeypatch)
    endpoint = PREFIX + '/reviews/' + value['handle'] + '/batch-approval'
    assert http.post(endpoint, headers=headers, json={'proposal_id': '0' * 64, 'confirm': True}).status_code == 409
    with value['reviews'].store.connect() as connection:
        relative = connection.execute('SELECT packet_relative FROM registered_packets WHERE artifact_id=?', (value['handle'],)).fetchone()[0]
    path = value['config'].artifact_root / relative
    original_packet = path.read_bytes()
    try:
        path.write_bytes(original_packet + b'\n')
        rejected = http.post(endpoint, headers=headers, json={'proposal_id': proposal['proposal_id'], 'confirm': True})
        assert rejected.status_code == 409, rejected.text
    finally:
        path.write_bytes(original_packet)
    assert value['reviews'].read(value['handle'])['review']['revision'] == 0
    original = value['reviews'].__class__.mutate
    def interrupted(self, handle, action, request, identity):
        if request['expected_revision'] == 1:
            raise RuntimeError('Synthetic process interruption')
        return original(self, handle, action, request, identity)
    body = {'proposal_id': proposal['proposal_id'], 'confirm': True}
    with monkeypatch.context() as patch:
        patch.setattr(value['reviews'].__class__, 'mutate', interrupted)
        assert http.post(endpoint, headers=headers, json=body).status_code == 503
    assert value['reviews'].read(value['handle'])['review']['revision'] == 1
    # A new application has a new signing key and requires login; durable approval survives.
    restarted, new_headers = client(value, monkeypatch)
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _: restarted.post(endpoint, headers=new_headers, json=body), range(2)))
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    assert replies[0].json() == replies[1].json()
    state = value['reviews'].read(value['handle'])['review']
    assert state['revision'] == len(proposal['proposal']['items']) + 1
    assert len(state['audit']) == state['revision']
    assert value['config'].knowledge_db.read_bytes() == value['production']


def test_missing_or_same_execution_cannot_prepare(advice_case):
    value = advice_case
    with pytest.raises(BridgeError, match='DUAL_ADVICE_REQUIRED'):
        writer(value).get_review_batch_context(value['handle'])
    for slot in ('A', 'B'):
        value['advice'].submit(value['handle'], value['opinions'][slot])
    with pytest.raises(BridgeError, match='REVIEW_EXECUTION_UNVERIFIED'):
        writer(value).get_review_batch_context(value['handle'])
    with pytest.raises(BoundaryError, match='MCP_WRITE_DISABLED'):
        writer(value, enabled=False)
    with pytest.raises(BridgeError, match='MCP_WRITE_SCOPE_DENIED'):
        writer(value).get_review_batch_context('ART_' + '0' * 32)
    a = {k: v for k, v in value['opinions']['A'].items() if k != 'reviewer_type'}
    b = {k: v for k, v in value['opinions']['B'].items() if k != 'reviewer_type'}
    writer(value).submit_reviewer_advice(value['handle'], **a)
    with pytest.raises(BridgeError, match='INDEPENDENT_REVIEW_REQUIRED'):
        writer(value, 'B', execution_id='isolated-session-A').submit_reviewer_advice(value['handle'], **b)


def test_twelve_candidates_independent_simulators_and_exact_reuse(tmp_path_factory, monkeypatch):
    import test_candidate_replacement as fixture_module
    from series_binding_helpers import text
    old_case = fixture_module.case
    def seeded(path):
        value = old_case(path)
        with sqlite3.connect(value['config'].knowledge_db) as connection:
            connection.execute("INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                ('NODE_20261013_AAAAAAAA', 'Synthetic Company', 'Entity', 'Synthetic entity', 'active', '2026-10-13', '2026-10-13'))
        return value
    monkeypatch.setattr(fixture_module, 'case', seeded)
    monkeypatch.setattr(fixture_module, 'text', lambda _: text(12))
    value = advice_case.__wrapped__(tmp_path_factory, monkeypatch)
    packet = value['packet']
    assert len(packet['claims']) == 11 and len(packet['nodes']) == 1 and not packet['relations']
    # Each simulator receives only the frozen candidate evidence, never another opinion.
    candidates = [r for group in ('claims', 'nodes', 'relations') for r in packet[group]]
    simulation = """import json,sys,os
data=json.load(sys.stdin)
items=[{'candidate_id':r['candidate_id'],'content_sha256':r['content_sha256'],
        'judgment':'UNCERTAIN' if data['slot']=='B' and i<3 else 'SUPPORTED',
        'reason':'Synthetic isolated evidence inspection'} for i,r in enumerate(data['evidence'])]
json.dump({'pid':os.getpid(),'items':items},sys.stdout)
"""
    pids = []
    for slot in ('A', 'B'):
        response = subprocess.run([sys.executable, '-I', '-c', simulation], input=json.dumps({'slot': slot, 'evidence': candidates}),
                                  capture_output=True, text=True, check=True)
        result = json.loads(response.stdout)
        pids.append(result['pid'])
        value['opinions'][slot]['items'] = result['items']
    assert pids[0] != pids[1]
    submit_pair(value)
    service = writer(value)
    context = service.get_review_batch_context(value['handle'])
    items = [{'candidate_id': r['candidate_id'], 'content_sha256': r['content_sha256'],
              'decision': 'KEEP_NEEDS_REVIEW' if n < 3 else 'KEEP', 'target_node_id': '',
              'reason': 'Defer unresolved evidence' if n < 3 else 'Supported synthetic evidence'} for n, r in enumerate(packet['claims'])]
    node = packet['nodes'][0]
    items.append({'candidate_id': node['candidate_id'], 'content_sha256': node['content_sha256'],
                  'decision': 'REUSE', 'target_node_id': 'NODE_20261013_AAAAAAAA', 'reason': 'Exact canonical identity checked'})
    invalid = copy.deepcopy(items)
    invalid[0]['decision'] = 'KEEP'
    with pytest.raises(BridgeError, match='CANDIDATE_SUPPORT_UNRESOLVED'):
        service.prepare_human_review_batch(value['handle'], context['binding'], 0, invalid, 'Cannot override uncertain B')
    invalid = copy.deepcopy(items)
    invalid[-1]['target_node_id'] = 'NODE_20261013_BBBBBBBB'
    with pytest.raises(BridgeError):
        service.prepare_human_review_batch(value['handle'], context['binding'], 0, invalid, 'Wrong exact target')
    proposal = service.prepare_human_review_batch(value['handle'], context['binding'], 0, items, 'Twelve candidate human review')
    assert proposal['counts'] == {'KEEP': 8, 'KEEP_NEEDS_REVIEW': 3, 'REUSE': 1}
    http, headers = client(value, monkeypatch)
    endpoint = PREFIX + '/reviews/' + value['handle'] + '/batch-approval'
    saved = http.post(endpoint, headers=headers, json={'proposal_id': proposal['proposal_id'], 'confirm': True})
    assert saved.status_code == 200, saved.text
    state = value['reviews'].read(value['handle'])['review']
    assert len([a for a in state['audit'] if a['event_type'] == 'SAVE']) == 12
    context = service.get_review_batch_context(value['handle'], 'attribution')
    items = [{'claim_id': r['candidate_id'], 'content_sha256': r['content_sha256'], 'scope': r['scope'],
              'outcome': 'LINK' if n == 0 else 'NO_LINK',
              'links': [{'node_id': 'NODE_20261013_AAAAAAAA', 'role': 'context'}] if n == 0 else [],
              'reason': 'Context only, no subject inference' if n == 0 else 'No explicit entity association'} for n, r in enumerate(context['claims'])]
    for field, bad in [('node_id', 'NODE_20261013_BBBBBBBB'), ('role', 'owner')]:
        invalid = copy.deepcopy(items)
        invalid[0]['links'][0][field] = bad
        with pytest.raises(BridgeError):
            service.prepare_attribution_batch(value['handle'], context['binding'], 0, invalid, 'Invalid link')
    attr = service.prepare_attribution_batch(value['handle'], context['binding'], 0, items, 'Eight claim attribution review')
    assert attr['counts'] == {'NO_LINK': 7, 'LINK': 1}
    saved = http.post(endpoint, headers=headers, json={'proposal_id': attr['proposal_id'], 'confirm': True})
    assert saved.status_code == 200, saved.text
    # Use the existing authenticated Workbench qualification entry point.
    qualified = http.post(PREFIX + '/attribution/' + value['handle'] + '/qualify', headers=headers,
                          json={'object_id': saved.json()['result']['sidecar_id']})
    assert qualified.status_code == 200, qualified.text
    projection = service.get_shadow_qualification(value['handle'], limit=50)
    assert projection['insert_counts']['claims'] == 8 and projection['insert_counts']['claim_node_links'] == 1
    assert projection['insert_counts'].get('nodes', 0) == 0
    assert all(c['values']['current_view_use'] == 'CLUE_ONLY' for c in projection['changes'] if c['table'] == 'claims')
    assert value['config'].knowledge_db.read_bytes() == value['production']
