"""P0: disposable Workbench fixtures and mock inference only."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
import requests as http_requests
import pro_a

from pro_a.config import LLMConfig
from pro_a.review_backends import CompatibleBackend, OllamaBackend
from pro_a.review_engine import ReviewEngine, ReviewerConfig
from pro_a.review_execution import Reason
from pro_a.workbench.config import BoundaryError
from test_candidate_advice_submission import advice_case, events
from test_single_model_review import choose, single_writer, submit_mcp
from test_mcp_controlled_write import writer

REAL_REQUEST = http_requests.sessions.Session.request


def engine(value, **changes):
    policy = single_writer(value).policy.model_dump()
    return ReviewEngine(value['config'], ReviewerConfig(**{**policy, **changes}))


def output(value):
    return {'context_sha256':value['opinions']['A']['context_sha256'],
            'items':[{**i,'reason':{k:'Synthetic evidence examined' for k in Reason.model_fields}}
                     for i in value['opinions']['A']['items']]}


class FakeBackend:
    model = 'synthetic-reviewer-v1'
    calls = 0
    def __init__(self, answer): self.answer = answer
    def identity(self): return {'kind':'SYNTHETIC','model':self.model}
    @property
    def metadata(self): return {'attempts':[{'attempt_number':1}] if self.calls else []}
    def infer(self, system, user):
        self.calls += 1
        assert 'untrusted data' in system
        data = json.loads(user)
        assert data['candidates'] and data['review_policy']['mode']=='SINGLE_MODEL_HUMAN'
        assert 'selected_by' not in data['review_policy'] and 'artifact_ids' not in data['reviewer']
        if isinstance(self.answer, Exception): raise self.answer
        return self.answer


def test_three_channels_same_engine_and_exact_replay(advice_case):
    v=advice_case; choose(v); e=engine(v); answer=output(v); backend=FakeBackend(answer)
    result=e.run(v['handle'],answer['context_sha256'],backend,task_id='api-first')
    assert result['status']=='SUCCEEDED' and backend.calls==1
    before=v['config'].state_db.read_bytes()
    assert e.run(v['handle'],answer['context_sha256'],backend,task_id='api-first')==result
    assert backend.calls==1 and v['config'].state_db.read_bytes()==before
    # MCP receives the same normalized advice; it must use the extracted engine.
    v['opinions']['A']['items']=result['advice']['opinion']['items']
    assert submit_mcp(v,single_writer(v))==result['advice']
    assert len(events(v))==1 and v['config'].knowledge_db.read_bytes()==v['production']
    assert v['reviews'].read(v['handle'])['review']['revision']==0


@pytest.mark.parametrize('fault',['invalid_json','missing','duplicate','id','sha','context','judgment','reason','identity','timeout'])
def test_failures_are_audited_without_advice(advice_case, fault):
    v=advice_case;choose(v);e=engine(v);answer=output(v)
    if fault=='invalid_json': answer='not JSON'
    elif fault=='missing': answer['items'].pop()
    elif fault=='duplicate': answer['items'][-1]=copy.deepcopy(answer['items'][0])
    elif fault=='id': answer['items'][0]['candidate_id']='UNKNOWN'
    elif fault=='sha': answer['items'][0]['content_sha256']='0'*64
    elif fault=='context': answer['context_sha256']='0'*64
    elif fault=='judgment': answer['items'][0]['judgment']='FACTUAL_KNOWLEDGE'
    elif fault=='reason': answer['items'][0]['reason'].pop('subject')
    elif fault=='identity': answer['reviewer_type']='HUMAN_USER'
    elif fault=='timeout': answer=TimeoutError('secret must not be in public error')
    b=FakeBackend(answer);ctx=v['opinions']['A']['context_sha256']
    result=e.run(v['handle'],ctx,b,task_id='failure')
    assert result['status']=='FAILED' and not events(v)
    expected={'missing':'ADVICE_UNIVERSE_INVALID','duplicate':'ADVICE_UNIVERSE_INVALID',
              'id':'ADVICE_UNIVERSE_INVALID','sha':'ADVICE_REVISION_INVALID',
              'context':'ADVICE_CONTEXT_CHANGED','timeout':'MODEL_REQUEST_FAILED'}
    assert result['error_code']==expected.get(fault,'MODEL_OUTPUT_INVALID')
    assert 'secret' not in json.dumps(result)
    assert e.run(v['handle'],ctx,b,task_id='failure')==result and b.calls==1
    retry=FakeBackend(output(v));assert e.run(v['handle'],ctx,retry,task_id='explicit-retry')['status']=='SUCCEEDED'
    assert len(events(v))==1 and v['config'].knowledge_db.read_bytes()==v['production']


def test_context_drift_after_inference_is_rejected(advice_case, monkeypatch):
    v=advice_case;choose(v);e=engine(v);b=FakeBackend(output(v));original=b.infer
    def infer(system,user):
        result=original(system,user)
        monkeypatch.setattr(e,'reviewer_binding',lambda *a: (_ for _ in ()).throw(BoundaryError('ADVICE_CONTEXT_CHANGED')))
        return result
    monkeypatch.setattr(b,'infer',infer)
    with pytest.raises(BoundaryError,match='ADVICE_CONTEXT_CHANGED'):
        e.run(v['handle'],v['opinions']['A']['context_sha256'],b,task_id='drift')
    assert not events(v) and list((v['config'].artifact_root/'review-executions').glob('*/failure-*.json'))


def test_provenance_and_policy_checked_before_inference(advice_case):
    v=advice_case;e=engine(v);b=FakeBackend(output(v));ctx=v['opinions']['A']['context_sha256']
    with pytest.raises(BoundaryError,match='ADVICE_POLICY_MISMATCH'):e.run(v['handle'],ctx,b,task_id='no-policy')
    assert b.calls==0;choose(v)
    assert e.run(v['handle'],ctx,b,task_id='one')['status']=='SUCCEEDED'
    other=engine(v,execution_id='different-execution')
    with pytest.raises(BoundaryError,match='REVIEW_EXECUTION_CONFLICT'):other.run(v['handle'],ctx,b,task_id='two')
    with pytest.raises(BoundaryError,match='REVIEWER_BINDING_MISMATCH'):engine(v,model='different').run(v['handle'],ctx,b,task_id='three')
    assert b.calls==1


def test_actual_compatible_http_transport(advice_case, monkeypatch):
    v=advice_case;choose(v);answer=output(v);requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(body)
            assert self.path=='/v1/chat/completions' and 'thinking' not in body
            response=json.dumps({'model':body['model'],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(answer)}}],'usage':{}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(response)));self.end_headers();self.wfile.write(response)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        endpoint=f'http://127.0.0.1:{server.server_port}/v1'
        monkeypatch.setenv('P0_SYNTHETIC_KEY','synthetic')
        def only_local(self, method, url, **kwargs):
            assert url==endpoint+'/chat/completions'
            return REAL_REQUEST(self, method, url, **kwargs)
        monkeypatch.setattr(http_requests.sessions.Session,'request',only_local)
        for backend_type in (CompatibleBackend,OllamaBackend):
            backend=(backend_type(LLMConfig(enabled=True,base_url=endpoint,model=FakeBackend.model,api_key_env='P0_SYNTHETIC_KEY')) if backend_type is CompatibleBackend else backend_type(FakeBackend.model,base_url=endpoint))
            result=engine(v).run(v['handle'],answer['context_sha256'],backend,task_id=backend_type.__name__)
            assert result['status']=='SUCCEEDED' and result['provider_attempts']==1
            assert result['advice']['execution']['model']==FakeBackend.model
        v['opinions']['A']['items']=result['advice']['opinion']['items']
        assert submit_mcp(v,single_writer(v))==result['advice']
        assert len(requests)==2 and len(events(v))==1
    finally:server.shutdown();server.server_close();thread.join()


def test_local_endpoint_and_unavailable_protection(advice_case, monkeypatch):
    import requests
    v=advice_case;choose(v)
    with pytest.raises(BoundaryError,match='LOCAL_ENDPOINT_REQUIRED'):OllamaBackend('x',base_url='https://external.invalid/v1')
    monkeypatch.setattr(requests,'post',lambda *a,**kw:(_ for _ in ()).throw(requests.ConnectionError('unavailable')))
    result=engine(v).run(v['handle'],v['opinions']['A']['context_sha256'],OllamaBackend(FakeBackend.model),task_id='offline')
    assert result['status']=='FAILED' and result['provider_attempts']==1 and not events(v)


def test_core_loads_without_mcp_packages():
    script='''import sys
class Block:
    def find_spec(self, fullname, *args):
        if fullname == 'mcp' or fullname.startswith(('mcp.','pro_a.mcp')):
            raise ImportError('MCP is unavailable')
sys.meta_path.insert(0,Block())
from pro_a.review_engine import ReviewEngine
from pro_a.review_execution import review_input
from pro_a.review_backends import CompatibleBackend, OllamaBackend
assert not any(n == 'mcp' or n.startswith(('mcp.','pro_a.mcp')) for n in sys.modules)
'''
    subprocess.run([sys.executable,'-c',script],check=True,
                   env={**os.environ,'PYTHONPATH':str(Path(pro_a.__file__).parent.parent)})


def test_adapter_parse_failure_keeps_only_content_free_diagnostics(monkeypatch):
    from pro_a.llm import LLMError
    backend=CompatibleBackend(LLMConfig())
    backend.client._attempt_events=[{'attempt_number':1,'failure_stage':'MODEL_OUTPUT_PARSE',
        'error_class':'OUTPUT_PARSE_ERROR','output_parse_kind':'MALFORMED_JSON',
        'content_tail':'private material','response_model':'Bearer PRIVATE_TOKEN',
        'provider_request_id':'secret'}]
    monkeypatch.setattr(backend.client,'json',lambda *a:(_ for _ in ()).throw(LLMError('private raw response')))
    with pytest.raises(BoundaryError,match='MODEL_OUTPUT_INVALID'):backend.infer('system','input')
    assert 'private' not in json.dumps(backend.metadata) and 'PRIVATE_TOKEN' not in json.dumps(backend.metadata)
    assert backend.metadata['attempts'][0]['output_parse_kind']=='MALFORMED_JSON'


def test_response_checkpoint_recovers_without_inference(advice_case, monkeypatch):
    v=advice_case;choose(v);e=engine(v);b=FakeBackend(output(v));ctx=v['opinions']['A']['context_sha256'];submit=e.submit
    monkeypatch.setattr(e,'submit',lambda *a:(_ for _ in ()).throw(OSError('synthetic crash')))
    with pytest.raises(OSError):e.run(v['handle'],ctx,b,task_id='recover')
    def crash_after_publication(*args):
        submit(*args)
        raise OSError('synthetic crash after durable Advice')
    monkeypatch.setattr(e,'submit',crash_after_publication)
    with pytest.raises(OSError):e.run(v['handle'],ctx,b,task_id='recover')
    assert len(events(v))==1 and b.calls==1
    monkeypatch.setattr(e,'submit',submit)
    assert e.run(v['handle'],ctx,b,task_id='recover')['status']=='SUCCEEDED' and b.calls==1
    assert len(events(v))==1


def test_unknown_outcome_and_task_conflict_do_not_retry(advice_case, monkeypatch):
    v=advice_case;choose(v);e=engine(v);b=FakeBackend(output(v));ctx=v['opinions']['A']['context_sha256']
    original=b.infer
    monkeypatch.setattr(b,'infer',lambda *a:(_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):e.run(v['handle'],ctx,b,task_id='unknown')
    monkeypatch.setattr(b,'infer',original)
    with pytest.raises(BoundaryError,match='REVIEW_EXECUTION_RECOVERY_REQUIRED'):
        e.run(v['handle'],ctx,b,task_id='unknown')
    assert b.calls==0 and not events(v)
    assert e.run(v['handle'],ctx,b,task_id='known')['status']=='SUCCEEDED'
    monkeypatch.setattr(b,'identity',lambda:{'kind':'different-backend','model':b.model})
    with pytest.raises(BoundaryError):e.run(v['handle'],ctx,b,task_id='known')
    assert b.calls==1 and len(events(v))==1


def test_dual_independence_across_mcp_and_api(advice_case):
    v=advice_case; a=writer(v); b=writer(v,'B')
    opinion=v['opinions']['A']
    a.submit_reviewer_advice(v['handle'],opinion['slot'],opinion['reviewer_id'],
                            opinion['context_sha256'],opinion['items'])
    answer=output(v); backend=FakeBackend(answer)
    # Same execution via a different entrance cannot be a second reviewer.
    policy={**b.policy.model_dump(),'execution_id':a.policy.execution_id}
    bad=ReviewEngine(v['config'],ReviewerConfig(**policy))
    with pytest.raises(BoundaryError,match='INDEPENDENT_REVIEW_REQUIRED'):
        bad.run(v['handle'],answer['context_sha256'],backend,task_id='not-independent')
    assert backend.calls==0
    # Historical dual packets have no explicit policy; native rules still apply.
    backend.infer=lambda *args:answer
    result=b.engine.run(v['handle'],answer['context_sha256'],backend,task_id='independent')
    assert result['status']=='SUCCEEDED' and len(events(v))==2
    assert v['reviews'].read(v['handle'])['review']['status']!='SEALED'
    assert v['config'].knowledge_db.read_bytes()==v['production']
