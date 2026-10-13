"""Synthetic cross-process approval ownership and crash recovery; no real runtime."""
import copy
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from pro_a.workbench.attribution import Attribution
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_batch import ReviewBatch
from test_candidate_advice_submission import advice_case, HUMAN
from test_mcp_controlled_write import no_operator_apply, prepare, submit_pair, writer


# A real process exit happens after approval commit, before step 0 or step 1.
WORKER = r'''
import json, os, sys, time
from pathlib import Path
from pro_a.workbench.config import WorkbenchConfig, BoundaryError
from pro_a.workbench.review_batch import ReviewBatch
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.attribution import Attribution
from pro_a.operational_operator import Operator
import requests

def forbidden(*a, **k):
    raise AssertionError('EXTERNAL_ACTION_FORBIDDEN')
Operator.execute = forbidden
requests.sessions.Session.request = forbidden
arg = json.load(sys.stdin)
raw = arg['config']
for name in ('knowledge_db', 'state_db', 'artifact_root'):
    raw[name] = Path(raw[name])
batch = ReviewBatch(WorkbenchConfig(**raw))
if arg['ready']:
    original_read = batch.read
    def ready_read(*a, **k):
        result = original_read(*a, **k)
        Path(arg['ready']).write_text('ready')
        deadline = time.monotonic() + 30
        while not Path(arg['go']).exists():
            if time.monotonic() > deadline:
                raise AssertionError('BARRIER_TIMEOUT')
            time.sleep(.02)
        return result
    batch.read = ready_read
service = ReviewWorkbench if arg['kind'] == 'native' else Attribution
original_mutate = service.mutate
def crash(self, handle, action, request, identity):
    if request['expected_revision'] == arg['stop']:
        os._exit(73)
    return original_mutate(self, handle, action, request, identity)
service.mutate = crash
try:
    print(json.dumps(batch.approve(arg['handle'], arg['pid'], arg['identity'], confirm=True)))
except BoundaryError as error:
    print(json.dumps({'error': str(error)}))
'''


def launch(value, proposal, *, stop=-1, ready=None, go=None):
    raw = asdict(value['config'])
    for key, item in raw.items():
        if isinstance(item, Path):
            raw[key] = str(item)
    # Pin child imports to the same source or isolated installed package as pytest.
    import pro_a
    env = {**os.environ, 'PYTHONPATH': str(Path(pro_a.__file__).parent.parent),
           'PYTHONDONTWRITEBYTECODE': '1'}
    process = subprocess.Popen([sys.executable, '-c', WORKER], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    process.stdin.write(json.dumps({'config': raw, 'handle': value['handle'],
        'pid': proposal['proposal_id'], 'kind': proposal['proposal']['kind'], 'stop': stop,
        'identity': {**HUMAN, 'session_id': 'new-process-login'},
        'ready': str(ready) if ready else '', 'go': str(go) if go else ''}))
    process.stdin.close()
    process.stdin = None
    return process


def finish(process):
    stdout, stderr = process.communicate(timeout=90)
    assert process.returncode in (0, 73), (stdout, stderr)
    return process.returncode, json.loads(stdout) if stdout.strip() else None


def race(value, proposals, tmp_path, *, stop):
    go = tmp_path / 'go'
    ready = [tmp_path / f'ready-{n}' for n in range(len(proposals))]
    processes = [launch(value, p, stop=stop, ready=r, go=go) for p, r in zip(proposals, ready)]
    try:
        deadline = time.monotonic() + 45
        while not all(p.exists() for p in ready):
            assert all(p.poll() is None for p in processes), 'Worker exited before barrier'
            assert time.monotonic() < deadline, 'Workers did not reach barrier'
            time.sleep(.02)
        go.write_text('go')
        return [finish(p) for p in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


def proposals(value, kind):
    submit_pair(value)
    first = prepare(value)
    batch = ReviewBatch(value['config'])
    if kind == 'attribution':
        batch.approve(value['handle'], first['proposal_id'], HUMAN, confirm=True)
        context = writer(value).get_review_batch_context(value['handle'], kind)
        items = [{'claim_id': r['candidate_id'], 'content_sha256': r['content_sha256'],
                  'scope': r['scope'], 'outcome': 'NO_LINK', 'links': [],
                  'reason': 'Synthetic no entity association'} for r in context['claims']]
        first = batch.prepare(value['handle'], kind, context['binding'], context['revision'], items, 'First attribution plan')
    frozen = first['proposal']
    items = copy.deepcopy(frozen['items'])
    if kind == 'native':
        next(i for i in items if i['decision'] == 'KEEP')['decision'] = 'KEEP_NEEDS_REVIEW'
    else:
        items[0]['reason'] = 'Alternative human attribution reasoning'
    second = batch.prepare(value['handle'], kind, frozen['binding'], frozen['expected_revision'], items, 'Competing plan')
    assert first['proposal_id'] != second['proposal_id']
    return first, second


def approvals(value, kind):
    batch = ReviewBatch(value['config'])
    with batch.store.connect() as connection:
        _, prepared = batch.events(connection, value['handle'], 'MCP_BATCH_PREPARED')
        _, approved = batch.events(connection, value['handle'], 'MCP_BATCH_APPROVED')
    kinds = {p['proposal_id']: p['proposal']['kind'] for p in prepared}
    return [a for a in approved if kinds.get(a['proposal_id']) == kind]


def state(value, kind):
    if kind == 'native':
        return value['reviews'].read(value['handle'])['review']
    return Attribution(value['config']).read(value['handle'])


@pytest.mark.parametrize('kind', ['native', 'attribution'])
@pytest.mark.parametrize('stop', [0, 1])
def test_crash_competitor_and_cross_process_resume(advice_case, tmp_path, kind, stop):
    value = advice_case
    first, second = proposals(value, kind)
    assert finish(launch(value, first, stop=stop)) == (73, None)
    assert state(value, kind)['revision'] == stop
    original_approval = approvals(value, kind)
    assert len(original_approval) == 1
    # Legacy v1 approval shape remains sufficient; no new fields or migrations.
    assert set(original_approval[0]) == {'proposal_id', 'actor', 'session_id', 'reviewer'}
    rejected = finish(launch(value, second))
    assert rejected == (0, {'error': 'BATCH_APPROVAL_CONFLICT'})
    assert approvals(value, kind) == original_approval
    assert state(value, kind)['revision'] == stop
    # A competitor also cannot enter while the original is recovering.
    results = race(value, [first, second], tmp_path, stop=-1)
    assert results[0][0] == 0 and results[0][1]['status'] == 'SEALED', results
    assert results[1] == (0, {'error': 'BATCH_APPROVAL_CONFLICT'}), results
    retry = finish(launch(value, first))
    assert retry == results[0]
    sealed = state(value, kind)
    assert sealed['revision'] == len(first['proposal']['items']) + 1
    assert len(sealed['audit']) == sealed['revision']
    assert approvals(value, kind) == original_approval
    assert value['config'].knowledge_db.read_bytes() == value['production']


@pytest.mark.parametrize('kind', ['native', 'attribution'])
def test_different_proposals_simultaneously_claim_approval(advice_case, tmp_path, kind):
    value = advice_case
    first, second = proposals(value, kind)
    results = race(value, [first, second], tmp_path, stop=0)
    assert len(approvals(value, kind)) == 1, results
    assert results.count((73, None)) == 1, results
    assert results.count((0, {'error': 'BATCH_APPROVAL_CONFLICT'})) == 1, results
    assert state(value, kind)['revision'] == 0
    assert value['config'].knowledge_db.read_bytes() == value['production']


@pytest.mark.parametrize('kind', ['native', 'attribution'])
@pytest.mark.parametrize('count', [1, 2])
def test_legacy_approval_compatibility(advice_case, kind, count):
    value = advice_case
    first, second = proposals(value, kind)
    batch = ReviewBatch(value['config'])
    # Simulate the exact records left by the frozen baseline's approval window.
    with batch.store.connect(operator_write=True) as connection:
        connection.execute('BEGIN IMMEDIATE')
        for proposal in (first, second)[:count]:
            batch.record(connection, value['handle'], 'MCP_BATCH_APPROVED', {
                'proposal_id': proposal['proposal_id'], 'actor': HUMAN['actor'],
                'session_id': HUMAN['session_id'], 'reviewer': HUMAN['actor']})
    if count == 1:
        result = finish(launch(value, first))
        assert result[0] == 0 and result[1]['status'] == 'SEALED', result
        assert len(approvals(value, kind)) == 1
        assert value['config'].knowledge_db.read_bytes() == value['production']
        return
    before = value['config'].state_db.read_bytes()
    for proposal in (first, second):
        with pytest.raises(BoundaryError, match='BATCH_APPROVAL_CONFLICT'):
            batch.approve(value['handle'], proposal['proposal_id'], HUMAN, confirm=True)
    assert value['config'].state_db.read_bytes() == before
    assert state(value, kind)['revision'] == 0


@pytest.mark.parametrize('kind', ['native', 'attribution'])
def test_revision_changed_before_approval_lock_is_not_authorized(advice_case, monkeypatch, kind):
    value = advice_case
    first, _ = proposals(value, kind)
    batch = ReviewBatch(value['config'])
    connect = batch.store.connect
    service = value['reviews'] if kind == 'native' else Attribution(value['config'])
    action, request = next(batch.operations(first['proposal'], HUMAN['actor']))
    pending = True

    @contextmanager
    def intervening_write(*, operator_write=False):
        nonlocal pending
        if operator_write and pending:
            pending = False
            service.mutate(value['handle'], action, request, HUMAN)
        with connect(operator_write=operator_write) as connection:
            yield connection

    monkeypatch.setattr(batch.store, 'connect', intervening_write)
    with pytest.raises(BoundaryError, match='REVISION_CONFLICT'):
        batch.approve(value['handle'], first['proposal_id'], HUMAN, confirm=True)
    assert approvals(value, kind) == []
    assert state(value, kind)['revision'] == 1
    assert value['config'].knowledge_db.read_bytes() == value['production']


@pytest.mark.parametrize('kind', ['native', 'attribution'])
def test_same_proposal_concurrent_process_retries(advice_case, tmp_path, kind):
    value = advice_case
    first, _ = proposals(value, kind)
    results = race(value, [first, first], tmp_path, stop=-1)
    assert results[0] == results[1] and results[0][1]['status'] == 'SEALED', results
    assert len(approvals(value, kind)) == 1
    sealed = state(value, kind)
    assert sealed['revision'] == len(first['proposal']['items']) + 1
    assert len(sealed['audit']) == sealed['revision']
    assert value['config'].knowledge_db.read_bytes() == value['production']
