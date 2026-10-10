"""Existing v4 runner, strict acceptance and native Review; synthetic data only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from pro_a.workbench.source_operations import SourceOperations, SourceOperationError
from pro_a.workbench.config import WorkbenchConfig
from pro_a.workbench.extraction_retry import bounded_frozen_components, frozen_bounded_service
from pro_a.workbench.retry_compatibility import assess_bounded_retry_compatibility, _runtime_comparison, _CLOUD_METADATA_FIELDS, _CLOUD_SURFACE_FIELDS
from series_binding_helpers import Transport, rows, synthetic_providers
from v4_single_evidence_fixture import synthetic_case, fail_once, SingleSelectorTransport


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr('requests.sessions.Session.request',lambda *a, **k:pytest.fail('REAL_NETWORK_FORBIDDEN'))


def authorize(value, attempt_id, key='single-evidence-explicit-0001', reason='Explicit synthetic single Evidence recovery'):
    return value['service'].authorize_single_evidence_retry(value['run_id'],attempt_id,
        retry_reason=reason,idempotency_key=key)


def complete_to_packet(value, transport, *, restart=True):
    if restart:
        value['service'] = frozen_bounded_service(value['service'],value['run_id'],
            rows(value,'bounded_extraction_attempts')[0]['attempt_id'])
    with synthetic_providers(value,transport) as providers:
        completed = value['service'].resume_bounded_extraction_only(value['run_id'],worker_id='synthetic-complete',
            idempotency_key='single-evidence-finish-0001',max_new_calls=4,provider=providers)
    assert completed['bounded_complete'] and len(transport.calls) == 4
    assert len(rows(value,'bounded_extraction_segment_results')) == 4
    assert not rows(value,'source_processing_jobs')
    assert not [r for r in rows(value,'registered_packets') if r['artifact_kind']=='REVIEW_PACKET']
    assert len(rows(value,'bounded_extraction_segments')) == 4
    packet = None
    for _ in range(20):
        packet = value['service'].advance_once(worker_id='synthetic-semantic',processing_run_id=value['run_id'],provider=value['providers'])
        if packet['state'] in ('HUMAN_REVIEW_REQUIRED','BLOCKED','FAILED'):
            break
    assert packet['state'] == 'HUMAN_REVIEW_REQUIRED', packet
    assert packet['packet_artifact_id']
    assert len([r for r in rows(value,'registered_packets') if r['artifact_kind']=='REVIEW_PACKET']) == 1
    assert value['config'].knowledge_db.read_bytes() == value['production_before']
    return packet


def test_same_run_four_segments_restart_semantic_and_formal_packet(tmp_path,monkeypatch):
    value = synthetic_case(tmp_path,monkeypatch)
    first = fail_once(value)
    outcomes = rows(value,'bounded_extraction_outcomes')
    events = rows(value,'bounded_extraction_events')
    raws = {p:p.read_bytes() for p in value['config'].artifact_root.rglob('*.raw.json')}
    runtime = value['service'].get_run(value['run_id'])['runtime_identity']
    created = authorize(value,first['attempt_id'])
    assert created['retry']['retry_reason_code'] == 'EVIDENCE_SELECTOR_NOT_FOUND'
    assert created['retry']['policy_version'] == 'v4-single-evidence-same-batch-retry-v1'
    assert created['retry']['evidence_diagnostic']['violations'] == [{'path':'$.claims[7].evidence.selector','code':'EVIDENCE_SELECTOR_NOT_FOUND'}]
    assert len(rows(value,'bounded_extraction_dispatches')) == 1
    second = created['attempt']
    assert second['attempt_number'] == 2 and second['segment_id'] == first['segment_id']
    for field in ('request_json','request_sha256','configuration_sha256','budget_identity'):
        assert first[field] == second[field]
    complete_to_packet(value,Transport())
    assert value['service'].get_run(value['run_id'])['runtime_identity'] == runtime
    assert rows(value,'bounded_extraction_attempts')[0] == first
    assert rows(value,'bounded_extraction_outcomes')[0] == outcomes[0]
    assert rows(value,'bounded_extraction_events')[:len(events)] == events
    assert all(p.read_bytes() == body for p,body in raws.items())
    assert len(rows(value,'source_processing_runs')) == 1


def test_duplicate_concurrent_and_wrong_scope_authorization(tmp_path,monkeypatch):
    value = synthetic_case(tmp_path,monkeypatch); first = fail_once(value)
    with pytest.raises(SourceOperationError): authorize(value,'ATTEMPT_WRONG_ID')
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _:authorize(value,first['attempt_id']),range(2)))
    assert sorted(r['duplicate'] for r in result) == [False,True]
    assert len(rows(value,'bounded_extraction_attempts')) == 2
    assert len(rows(value,'bounded_extraction_dispatches')) == 1
    with pytest.raises(SourceOperationError,match='IDEMPOTENCY_CONFLICT'):
        authorize(value,first['attempt_id'],reason='Conflicting synthetic reason')
    with pytest.raises(SourceOperationError,match='RETRY_LIMIT_EXCEEDED'):
        authorize(value,first['attempt_id'],key='second-authorization-0002')


def test_second_failure_stops_without_third_attempt_or_semantic(tmp_path,monkeypatch):
    value = synthetic_case(tmp_path,monkeypatch); first = fail_once(value)
    authorize(value,first['attempt_id'])
    transport = SingleSelectorTransport()
    with synthetic_providers(value,transport) as providers:
        result = value['service'].resume_bounded_extraction_only(value['run_id'],worker_id='synthetic-second-fail',
            idempotency_key='second-failure-stop-0001',max_new_calls=4,provider=providers)
    assert result['run']['state'] == 'BLOCKED' and len(transport.calls) == 1
    assert len(rows(value,'bounded_extraction_attempts')) == 2
    assert rows(value,'bounded_extraction_segment_results') == [] and rows(value,'source_processing_jobs') == []
    with pytest.raises(SourceOperationError,match='RETRY_LIMIT_EXCEEDED'):
        authorize(value,first['attempt_id'],key='second-failure-retry-0002')


def test_multiple_selector_failures_not_single_failure_scope(tmp_path,monkeypatch):
    value = synthetic_case(tmp_path,monkeypatch)
    with synthetic_providers(value,SingleSelectorTransport(errors=2)) as providers:
        value['service'].resume_bounded_extraction_only(value['run_id'],worker_id='synthetic-two-errors',
            idempotency_key='multiple-failure-stop-0001',max_new_calls=4,provider=providers)
    with pytest.raises(SourceOperationError,match='RETRY_NOT_ELIGIBLE'):
        authorize(value,rows(value,'bounded_extraction_attempts')[0]['attempt_id'])
    assert len(rows(value,'bounded_extraction_attempts')) == 1


def test_runtime_surface_only_operator_hashes_can_differ():
    original = {'git_sha':'a'*40,'lossless_aggregate_recovery':{'aggregate_version':'FROZEN',
        'module_sha256':{'workbench/extraction_retry.py':'a'*64,'lossless_aggregate.py':'b'*64}}}
    target = deepcopy(original); target['lossless_aggregate_recovery']['module_sha256']['workbench/extraction_retry.py'] = 'c'*64
    def compare():
        return _runtime_comparison(original,target,_CLOUD_METADATA_FIELDS,surface_fields=_CLOUD_SURFACE_FIELDS,surface_compatible=True)
    assert compare()['compatible']
    target['lossless_aggregate_recovery']['aggregate_version'] = 'CHANGED'
    assert not compare()['compatible']
    target = deepcopy(original); target['lossless_aggregate_recovery']['module_sha256']['lossless_aggregate.py'] = 'c'*64
    assert not compare()['compatible']
    target = {}
    assert not compare()['compatible']


def test_actual_stable_frozen_run_qualifies_and_reaches_packet(tmp_path,monkeypatch):
    interpreter = os.environ.get('PRO_A_RELEASED_PYTHON')
    assert interpreter, 'Actual installed Stable interpreter is required'
    # The actual old Windows interpreter needs a short artifact root.
    root = tmp_path.parent/'synthetic-v4'
    env = {k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}
    child = subprocess.run([interpreter,'-B','-X','utf8',str(Path(__file__).with_name('v4_single_evidence_fixture.py')),
        str(root),'1c1ad9871f6f3c9a9a061afc12f9918a3f04b25b',
        str(Path(pytest.__file__).resolve().parents[1])],env=env,capture_output=True,timeout=240)
    assert child.returncode == 0, child.stderr.decode(errors='replace')
    saved = json.loads((root/'fixture.json').read_text())
    for key in ('state_db','artifact_root','knowledge_db'): saved['config'][key] = Path(saved['config'][key])
    config = WorkbenchConfig(**saved['config'])
    with sqlite3.connect(config.state_db) as c:
        c.row_factory = sqlite3.Row
        run = c.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?',(saved['run_id'],)).fetchone()
        profile, cloud, _, _ = bounded_frozen_components(config,c,run)
    service = SourceOperations(config,profile,cloud)
    value = {'service':service,'run_id':saved['run_id'],'config':config,'cloud_profile':cloud,
        'production_before':config.knowledge_db.read_bytes()}
    with pytest.raises(SourceOperationError,match='RETRY_RUNTIME_INCOMPATIBLE'):
        authorize(value,saved['failed_attempt_id'])
    qualification = assess_bounded_retry_compatibility(config,saved['run_id'],saved['failed_attempt_id'],
        bounded_single_evidence_retry=True,persist=True,historical_repository_root=Path(__file__).resolve().parents[1])
    (root/'qualification.json').write_text(json.dumps(qualification,default=str),encoding='utf-8')
    assert qualification['status'] == 'QUALIFIED', qualification
    # Real Semantic adapter shape, but strictly local deterministic transport.
    from pro_a.workbench.source_operations import build_source_providers
    from pro_a.config import load_config
    value['providers'] = build_source_providers(load_config(profile.phase4_config_path).llm,cloud)
    from test_cloud_operation_adapter_binding import SEMANTIC_DECOMPOSITION_USER
    from types import SimpleNamespace
    def semantic_post(_url, **kwargs):
        user = kwargs['json']['messages'][1]['content']
        prefix,suffix = SEMANTIC_DECOMPOSITION_USER.split('{claims_json}')
        assert user.startswith(prefix)
        claims = json.loads(user[len(prefix):len(user)-len(suffix) if suffix else None])
        response = {'claims':[{'parent_claim_id':c['parent_claim_id'],'ir_status':'VALID','units':[{
            'predicate_family':'measurement','modality':'actual','nature':c['assigned_nature'] or 'fact',
            'support_evidence_unit_ids':[c['evidence_units'][0]['evidence_unit_id']],
            'coherence_key':'k1','coherence_type':'INDEPENDENT','time_scope':'unspecified'}]} for c in claims]}
        return SimpleNamespace(status_code=200,headers={'x-request-id':'synthetic-semantic'},
            json=lambda:{'id':'synthetic-semantic','model':'deepseek-flash','choices':[{'finish_reason':'stop',
                'message':{'content':json.dumps(response)}}],'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}})
    monkeypatch.setenv('PROA_LLM_API_KEY','synthetic-transport-only')
    monkeypatch.setattr('pro_a.llm.requests.post',semantic_post)
    authorize(value,saved['failed_attempt_id'])
    complete_to_packet(value,Transport())
    assert service.get_run(saved['run_id'])['runtime_identity'] == saved['historical_runtime']
