"""Synthetic single-review policy and human approval; no Provider or Apply access."""
import asyncio
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from pro_a.mcp.errors import BridgeError
from pro_a.workbench.api import PREFIX
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_policy import ReviewPolicy
from pro_a.workbench.review_workbench import ReviewWorkbench
from test_candidate_advice_submission import advice_case, HUMAN, decisions, seal
from test_mcp_controlled_write import client, writer, no_operator_apply

SINGLE = 'SINGLE_MODEL_HUMAN'
DUAL = 'DUAL_MODEL_HUMAN'
NODES = [('CoWoS-L', 'NODE_1A7F2D5816F5B7EE'), ('CoWoS-S', 'NODE_3E0E5604C3F64891'),
         ('RDL Interposer', 'NODE_20260817_4AA22685')]


@pytest.mark.parametrize('fault', ['missing', 'content', 'context', 'reason', 'judgment', 'reviewer_type', 'policy', 'extra_slot'])
def test_single_opinion_contract_rejects_incomplete_or_forged_support(fault):
    from pro_a.evidence_binding import identity
    from pro_a.workbench.advisory_review import validate
    packet = {'immutable_packet_sha256': 'a' * 64, 'claims': [
        {'candidate_id': 'CLM_SYNTHETIC', 'content_sha256': 'b' * 64}], 'nodes': [], 'relations': []}
    policy = {'mode': SINGLE, 'sha256': 'c' * 64, 'binding': {'context_sha256': 'd' * 64}}
    opinion = {'version': 'native-advice-v2', 'slot': 'A', 'packet_sha256': 'a' * 64,
               'context_sha256': 'd' * 64, 'reviewer_type': 'MODEL', 'reviewer_id': 'synthetic-A',
               'review_policy_sha256': policy['sha256'], 'items': [
                   {'candidate_id': 'CLM_SYNTHETIC', 'content_sha256': 'b' * 64, 'judgment': 'SUPPORTED', 'reason': 'Source supports it'}]}
    opinion['sha256'] = identity(opinion)
    validate(packet, {'A': opinion}, policy)
    opinion.pop('sha256')
    if fault == 'missing': opinion['items'] = []
    if fault == 'content': opinion['items'][0]['content_sha256'] = '0' * 64
    if fault == 'context': opinion['context_sha256'] = '0' * 64
    if fault == 'reason': opinion['items'][0]['reason'] = ' '
    if fault == 'judgment': opinion['items'][0]['judgment'] = 'VERIFIED_FACT'
    if fault == 'reviewer_type': opinion['reviewer_type'] = 'HUMAN_USER'
    if fault == 'policy': opinion['review_policy_sha256'] = '0' * 64
    opinion['sha256'] = identity(opinion)
    opinions = {'A': opinion}
    if fault == 'extra_slot': opinions['B'] = copy.deepcopy(opinion)
    with pytest.raises(BoundaryError):
        validate(packet, opinions, policy)


def choose(value, mode=SINGLE):
    policies = ReviewPolicy(value['reviews'])
    return policies.select(value['handle'], mode, policies.context(value['handle']), HUMAN, confirm=True)


def single_writer(value, **changes):
    return writer(value, review_mode=SINGLE, isolation_attested_by_operator=False, **changes)


def submit(value, service=None):
    opinion = {k: v for k, v in value['opinions']['A'].items() if k != 'reviewer_type'}
    return (service or single_writer(value)).submit_reviewer_advice(value['handle'], **opinion)


def submit_mcp(value, service):
    async def run():
        from mcp import Client
        from pro_a.mcp.server import create_server
        from pro_a.mcp.service import ReadService, TOOLS
        from pro_a.mcp.write_service import WRITE_TOOLS, EXTRA_READ_TOOLS
        async with Client(create_server(ReadService(value['config']), service)) as session:
            assert {t.name for t in (await session.list_tools()).tools} == set(TOOLS + WRITE_TOOLS + EXTRA_READ_TOOLS)
            result = await session.call_tool('submit_reviewer_advice', {'artifact_id': value['handle'],
                **{k: v for k, v in value['opinions']['A'].items() if k != 'reviewer_type'}})
            assert not result.is_error, result
            return result.structured_content
    return asyncio.run(run())


def test_policy_human_boundary_immutability_and_native_restart(advice_case, monkeypatch):
    value = advice_case
    policies = ReviewPolicy(value['reviews'])
    http, headers = client(value, monkeypatch)
    url = PREFIX + '/reviews/' + value['handle'] + '/policy'
    ctx = http.get(url).json()
    body = {'mode': SINGLE, 'binding': ctx['binding'], 'confirm': True}
    assert ctx['policy'] is None
    assert http.post(url, json=body, headers={'Origin': value['config'].origin}).status_code == 403
    assert http.post(url, json={**body, 'actor': 'HUMAN_USER'}, headers=headers).status_code == 422
    assert http.post(url, json={**body, 'confirm': False}, headers=headers).status_code == 409
    drift = {**body, 'binding': {**ctx['binding'], 'context_sha256': '0' * 64}}
    assert http.post(url, json=drift, headers=headers).status_code == 409
    response = http.post(url, json=body, headers=headers)
    assert response.status_code == 200, response.text
    policy = response.json()
    assert policy['selected_by']['principal_type'] == 'HUMAN_USER'
    assert http.post(url, json=body, headers=headers).json() == policy
    assert http.post(url, json={**body, 'mode': DUAL}, headers=headers).status_code == 409
    with pytest.raises(BoundaryError, match='HUMAN_USER_REQUIRED'):
        policies.select(value['handle'], SINGLE, ctx['binding'], {'principal_type': 'MODEL'}, confirm=True)
    service = single_writer(value)
    saved = submit_mcp(value, service)
    assert saved['opinion']['review_policy_sha256'] == policy['sha256']
    assert saved['execution']['independence_evidence'] == 'SINGLE_MODEL_OPERATOR_CONFIGURED_NOT_PLATFORM_PROVEN'
    assert submit(value, service) == saved
    assert set(value['advice'].read(value['packet'], handle=value['handle'])) == {'A'}
    with pytest.raises(BridgeError, match='ADVICE_POLICY_MISMATCH'):
        writer(value, 'B').submit_reviewer_advice(value['handle'], **{
            k: v for k, v in value['opinions']['B'].items() if k != 'reviewer_type'})
    with pytest.raises(BoundaryError):
        value['advice'].submit(value['handle'], value['opinions']['B'])
    with pytest.raises(BridgeError, match='REVIEW_EXECUTION_CONFLICT'):
        submit(value, single_writer(value, execution_id='drift'))
    with pytest.raises(BridgeError, match='REVIEW_EXECUTION_CONFLICT'):
        submit(value, single_writer(value, model='drift'))
    assert not value['advice']._path(value['packet'], 'B').exists()
    with pytest.raises(BoundaryError, match='VALIDATION_ERROR'):
        seal(value)
    decisions(value)
    state = value['reviews'].read(value['handle'])['review']
    value['reviews'].validate_completion(value['handle'], state['revision'], state['basis_id'])
    seal(value)
    restarted = ReviewWorkbench(value['config']).read(value['handle'])['review']
    assert restarted['sealed']['validation']['review_policy'] == policy
    assert set(restarted['sealed']['validation']['candidate_advisories']) == {'A'}
    assert value['config'].knowledge_db.read_bytes() == value['production']


def test_legacy_and_explicit_dual_cannot_be_reinterpreted(advice_case):
    value = advice_case
    service = single_writer(value)
    with pytest.raises(BridgeError, match='ADVICE_POLICY_MISMATCH'):
        submit(value, service)
    policy = choose(value, DUAL)
    for slot in ('A', 'B'):
        writer(value, slot).submit_reviewer_advice(value['handle'], **{
            k: v for k, v in value['opinions'][slot].items() if k != 'reviewer_type'})
        if slot == 'A':
            with pytest.raises(BridgeError, match='DUAL_ADVICE_REQUIRED'):
                writer(value).get_review_batch_context(value['handle'])
    with pytest.raises(BoundaryError, match='REVIEW_POLICY_IMMUTABLE'):
        choose(value)
    decisions(value)
    seal(value)
    assert value['reviews'].sealed_result(value['handle'])['validation']['review_policy'] == policy


@pytest.mark.parametrize('orphan', [False, True])
def test_policy_cannot_follow_existing_advice_or_orphan_publication(advice_case, monkeypatch, orphan):
    value = advice_case
    if orphan:
        from pro_a.workbench.source_operations import SourceOperations
        original = SourceOperations._event
        with monkeypatch.context() as patch:
            def fail(connection, run, kind, payload):
                if kind == 'CANDIDATE_ADVICE_SUBMITTED':
                    raise OSError('Synthetic registration failure')
                return original(connection, run, kind, payload)
            patch.setattr(SourceOperations, '_event', staticmethod(fail))
            with pytest.raises(OSError):
                value['advice'].submit(value['handle'], value['opinions']['A'])
    else:
        value['advice'].submit(value['handle'], value['opinions']['A'])
    with pytest.raises(BoundaryError, match='REVIEW_POLICY_TOO_LATE'):
        choose(value)


def test_fifteen_candidate_single_full_loop(tmp_path_factory, monkeypatch):
    import test_candidate_replacement as fixture
    import series_binding_helpers as helpers
    original_case, original_content = fixture.case, helpers.response_content

    def seeded(path):
        value = original_case(path)
        with sqlite3.connect(value['config'].knowledge_db) as connection:
            for name, nid in NODES:
                connection.execute('INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                    (nid, name, 'Product' if name == 'RDL Interposer' else 'Technology',
                     'Synthetic exact identity', 'active', '2026-10-14', '2026-10-14'))
        return value

    def content(*args, **kwargs):
        record = json.loads(original_content(*args, **kwargs))
        record['wire']['node_candidates'] = [{**record['wire']['node_candidates'][0], 'canonical_name': name,
            'primary_type': 'Product' if name == 'RDL Interposer' else 'Technology'} for name, _ in NODES]
        for claim in record['wire']['claims']:
            claim['related_candidate_names'] = [name for name, _ in NODES]
        return json.dumps(record)

    monkeypatch.setattr(fixture, 'case', seeded)
    monkeypatch.setattr(fixture, 'text', lambda _: '\n'.join(
        f'Synthetic Company uses CoWoS-L, CoWoS-S and RDL Interposer with measurement {i:03d} of {i+1} units.' for i in range(13)))
    monkeypatch.setattr(helpers, 'response_content', content)
    value = advice_case.__wrapped__(tmp_path_factory, monkeypatch)
    packet = value['packet']
    assert {g: len(packet[g]) for g in ('claims', 'nodes', 'relations')} == {'claims': 12, 'nodes': 3, 'relations': 0}
    for row in packet['nodes']:
        assert row['content']['proposed_type'] == row['content']['exact_production_resolution']['candidate_targets'][0]['primary_type']
    original_packet = copy.deepcopy(packet)
    policy = choose(value)
    value['opinions']['A']['items'][0]['judgment'] = 'UNCERTAIN'
    value['opinions']['A']['items'][1]['judgment'] = 'UNSUPPORTED'
    service = single_writer(value)
    saved = submit_mcp(value, service)
    assert len(saved['opinion']['items']) == 15
    context = service.get_review_batch_context(value['handle'])
    items = []
    judgments = {i['candidate_id']: i['judgment'] for i in saved['opinion']['items']}
    for row in context['candidates']:
        cid = row['candidate_id']
        decision = {'UNCERTAIN': 'KEEP_NEEDS_REVIEW', 'UNSUPPORTED': 'DROP', 'SUPPORTED': 'KEEP'}[judgments[cid]]
        target = ''
        if row['candidate_type'] == 'NODE':
            decision = 'REUSE'
            target = row['content']['exact_production_resolution']['exact_target_node_ids'][0]
        items.append({'candidate_id': cid, 'content_sha256': row['content_sha256'], 'decision': decision,
                      'target_node_id': target, 'reason': 'Synthetic source support only; reality unverified'})
    for index in (0, 1):
        invalid = copy.deepcopy(items)
        invalid[index]['decision'] = 'KEEP'
        with pytest.raises(BridgeError, match='CANDIDATE_SUPPORT_UNRESOLVED'):
            service.prepare_human_review_batch(value['handle'], context['binding'], 0, invalid, 'Invalid promotion')
    for index in range(12, 15):
        from pro_a.workbench.review_workbench import available_actions
        assert available_actions(packet, packet['nodes'][index - 12], {})['blocked_decisions']['CREATE'] == 'CREATE_COLLISION_PRESENT'
        invalid = copy.deepcopy(items)
        invalid[index].update(decision='CREATE', target_node_id='')
        with pytest.raises(BridgeError):
            service.prepare_human_review_batch(value['handle'], context['binding'], 0, invalid, 'Collision')
        invalid[index].update(decision='REUSE', target_node_id='NODE_INVALID')
        with pytest.raises(BridgeError):
            service.prepare_human_review_batch(value['handle'], context['binding'], 0, invalid, 'Wrong target')
    proposal = service.prepare_human_review_batch(value['handle'], context['binding'], 0, items, 'Synthetic fifteen')
    assert proposal['counts'] == {'KEEP': 10, 'KEEP_NEEDS_REVIEW': 1, 'DROP': 1, 'REUSE': 3}
    http, headers = client(value, monkeypatch)
    endpoint = PREFIX + '/reviews/' + value['handle'] + '/batch-approval'
    body = {'proposal_id': proposal['proposal_id'], 'confirm': True}
    mutate = ReviewWorkbench.mutate
    with monkeypatch.context() as patch:
        def interrupted(self, handle, action, request, identity):
            if request['expected_revision'] == 1:
                raise RuntimeError('Synthetic interruption')
            return mutate(self, handle, action, request, identity)
        patch.setattr(ReviewWorkbench, 'mutate', interrupted)
        assert http.post(endpoint, headers=headers, json=body).status_code == 503
    other = service.prepare_human_review_batch(value['handle'], context['binding'], 1, items, 'Explicit revised proposal')
    # Resume the original approved operation sequence after restart/concurrent replay.
    http, headers = client(value, monkeypatch)
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _: http.post(endpoint, headers=headers, json=body), range(2)))
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    assert replies[0].json() == replies[1].json()
    assert http.post(endpoint, headers=headers, json={'proposal_id': other['proposal_id'], 'confirm': True}).status_code == 409
    review = ReviewWorkbench(value['config']).read(value['handle'])['review']
    assert review['revision'] == 16 and len(review['audit']) == 16
    assert review['sealed']['validation']['review_policy'] == policy
    context = service.get_review_batch_context(value['handle'], 'attribution')
    attr_items = [{'claim_id': c['candidate_id'], 'content_sha256': c['content_sha256'], 'scope': c['scope'],
                   'outcome': 'LINK' if n == 0 else 'NO_LINK',
                   'links': [{'node_id': NODES[0][1], 'role': 'context'}] if n == 0 else [],
                   'reason': 'Explicit synthetic context; no inferred company subject'} for n, c in enumerate(context['claims'])]
    attr = service.prepare_attribution_batch(value['handle'], context['binding'], 0, attr_items, 'Separate attribution')
    result = http.post(endpoint, headers=headers, json={'proposal_id': attr['proposal_id'], 'confirm': True})
    assert result.status_code == 200, result.text
    from pro_a.workbench.attribution import Attribution
    with monkeypatch.context() as patch:
        patch.setattr('pro_a.workbench.attribution.runtime_identity', lambda: '0' * 64)
        assert Attribution(value['config']).sealed_context(value['handle'])[1]['object_id'] == result.json()['result']['sidecar_id']
    qualified = http.post(PREFIX + '/attribution/' + value['handle'] + '/qualify', headers=headers,
                          json={'object_id': result.json()['result']['sidecar_id']})
    assert qualified.status_code == 200, qualified.text
    projection = service.get_shadow_qualification(value['handle'], limit=50)
    assert projection['insert_counts']['claims'] == 10
    assert projection['insert_counts'].get('nodes', 0) == 0
    assert projection['insert_counts']['claim_node_links'] == 1
    for change in projection['changes']:
        if change['table'] == 'claims':
            assert {k: change['values'][k] for k in ('admission_semantics', 'reality_support', 'current_view_use')} == {
                'admission_semantics': 'SOURCE_ASSERTION', 'reality_support': 'UNVERIFIED', 'current_view_use': 'CLUE_ONLY'}
    assert value['reviews']._context(value['handle'])[0] == original_packet
    assert value['config'].knowledge_db.read_bytes() == value['production']
