"""Synthetic HTTP through the real bounded adapter; no external providers."""
from copy import deepcopy
from dataclasses import replace
import json
import re
from contextlib import contextmanager
import os
from unittest.mock import patch

import requests

from pro_a.bounded_source_analysis import BOUNDED_SOURCE_ANALYSIS_OPERATION, BoundedSourceAnalysisSegmentProvider
from pro_a.cloud_contract import DeterministicFakeProvider
from pro_a.config import LLMConfig
from pro_a.workbench.bounded_extraction_persistence import prepare_bounded_extraction_persistence
from pro_a.workbench.source_operations import SourceOperations
from pro_a.workbench.store import Store
from test_phase43_stage6_lifecycle import _schema11
from test_workbench_stage7 import clean_pdf, upload


def case(tmp_path):
    value, _ = _schema11(tmp_path)
    prepare_bounded_extraction_persistence(value['config'])
    return value


def prepare_bounded(value):
    from pro_a.workbench.domains import prepare_domains
    from pro_a.workbench.stage1_scale import prepare_stage1_scale
    from pro_a.workbench.lifecycle_closure import prepare_stage6_lifecycle
    for prepare in (prepare_domains,prepare_stage1_scale,prepare_stage6_lifecycle,prepare_bounded_extraction_persistence):
        prepare(value['config'])


class SyntheticProviders(dict):
    @property
    def call_count(self):
        return len(self[BOUNDED_SOURCE_ANALYSIS_OPERATION].transport.calls)+self['SEMANTIC_DECOMPOSITION'].call_count


@contextmanager
def synthetic_providers(value,transport=None):
    with patch.dict(os.environ,{'PROA_SYNTHETIC_BOUNDED_KEY':'synthetic-fixture'}):
        cfg=LLMConfig(enabled=True,api_key_env='PROA_SYNTHETIC_BOUNDED_KEY',model='deepseek-flash',
                      max_retries=0,max_output_tokens=12000,timeout_seconds=value['cloud_profile'].timeout_seconds)
        yield SyntheticProviders({BOUNDED_SOURCE_ANALYSIS_OPERATION:BoundedSourceAnalysisSegmentProvider(cfg,transport=transport or Transport()),
                                  'SEMANTIC_DECOMPOSITION':DeterministicFakeProvider()})


def text(count):
    return '\n'.join(f'Synthetic Company product {i:03d} has capacity {i+1} units.' for i in range(count))


class Response:
    status_code = 200
    headers = {'x-request-id': 'req-synthetic-bounded'}

    def __init__(self, content, finish='stop', output=50, reasoning=None):
        self.value = {'model':'deepseek-flash','choices':[{'finish_reason':finish,
                      'message':{'content':content,'reasoning_content':reasoning}}],
                      'usage':{'prompt_tokens':100,'completion_tokens':output,'total_tokens':100+output,
                               'prompt_cache_hit_tokens':20,'completion_tokens_details':{'reasoning_tokens':0}}}

    def json(self):
        return self.value


class Transport:
    def __init__(self, *, mode=None, callback=None):
        self.mode, self.callback, self.calls = mode, callback, []

    def __call__(self, endpoint, *, json, headers, timeout):
        self.calls.append(deepcopy(json))
        if self.callback:
            self.callback(json)
        target, source = request_parts(json)
        mode = self.mode(target, len(self.calls)) if callable(self.mode) else self.mode
        if mode == 'unknown':
            raise requests.ReadTimeout('SYNTHETIC_UNTRUSTED_EXCEPTION')
        if mode == 'truncated':
            return Response('{"wire":{"claims":[', 'length', 12000)
        if mode == 'malformed':
            return Response('SYNTHETIC_MALFORMED_PRIVATE_CONTENT')
        content=response_content(target, source, subdivision=mode=='subdivide')
        if mode=='sparse':
            value=__import__('json').loads(content)
            value['wire']['claims']=value['wire']['claims'][:1]
            for disposition in value['dispositions'][1:]:
                disposition['disposition']='NO_INDEPENDENT_CLAIM'
            content=__import__('json').dumps(value,ensure_ascii=False)
        if mode=='empty':
            value=__import__('json').loads(content)
            value['wire']['claims']=[]
            value['wire']['node_candidates']=[]
            for disposition in value['dispositions']:
                disposition['disposition']='NO_INDEPENDENT_CLAIM'
            content=__import__('json').dumps(value,ensure_ascii=False)
        return Response(content)


def request_parts(request):
    user = request['messages'][1]['content']
    target = json.loads(user.split('\nScoped existing Nodes:\n')[0].removeprefix('Frozen target:\n'))
    return target, user.split('\nComplete annotated SourcePiece:\n',1)[1]


def response_content(target, source, *, subdivision=False):
    claims = []
    for ref in target['assigned_evidence_refs']:
        start = source.index('['+ref+']')
        unit = source[start+len(ref)+2:source.index('[/'+ref+']', start)]
        locators = re.findall(r'\[\[(PAGE:[^\]]+|PARA:[^\]]+)\]\]', source[:start])
        if not subdivision:
            claims.append({'statement':unit,'nature':'fact','evidence_ref':ref,
                           'evidence_pointer':'[['+locators[-1]+']]' if locators else 'TEXT',
                           'attributed_to':'Synthetic Company','fact_time':'','scope':'Synthetic Company',
                           'confidence':0.9,'novelty_level':'N2',
                           'related_candidate_names':['Synthetic Company']})
    value = {'wire':{'wire_version':'source-analysis-wire-v3',
             'source_metadata':{'title':'Synthetic bounded source','publication_time':'2026-09-15',
                                'source_rank':'A','source_origin_type':'primary'},'claims':claims,
             'node_candidates':[] if subdivision else [{'canonical_name':'Synthetic Company',
                 'primary_type':'Entity','confidence':0.95,'independent_research_value':True,
                 'maintenance_rationale':'Explicit synthetic company with repeated measurements.'}]},
             'dispositions':[{'evidence_ref':ref,'disposition':'SUBDIVISION_REQUIRED' if subdivision else 'CLAIMED'}
                             for ref in target['assigned_evidence_refs']]}
    return json.dumps(value, ensure_ascii=False)


def providers(value, monkeypatch, transport=None, semantic=None):
    monkeypatch.setenv('PROA_SYNTHETIC_BOUNDED_KEY', 'synthetic-fixture')
    cfg = LLMConfig(enabled=True, api_key_env='PROA_SYNTHETIC_BOUNDED_KEY', model='deepseek-flash',
                    max_retries=0, max_output_tokens=12000, timeout_seconds=value['cloud_profile'].timeout_seconds)
    transport = transport or Transport()
    bounded = BoundedSourceAnalysisSegmentProvider(cfg, transport=transport)
    return {BOUNDED_SOURCE_ANALYSIS_OPERATION:bounded, 'SEMANTIC_DECOMPOSITION':semantic or DeterministicFakeProvider()}, transport


def real_providers(value,monkeypatch,transport=None):
    from pro_a.config import load_config
    from pro_a.workbench.cloud_jobs import CloudProfile
    from pro_a.workbench.source_operations import build_source_providers
    from pro_a.semantic_decomposition import SEMANTIC_DECOMPOSITION_USER
    path=value['phase4_config']
    path.write_text(path.read_text(encoding='utf-8').replace('enabled = false\nmodel = "fake-semantic-v1"',
                    'enabled = true\nmodel = "deepseek-flash"'),encoding='utf-8')
    value['cloud_profile']=CloudProfile('deepseek','deepseek-flash')
    value['service']=SourceOperations(value['config'],value['source_profile'],value['cloud_profile'])
    monkeypatch.setenv('PROA_LLM_API_KEY','synthetic-fixture')
    result=build_source_providers(load_config(path).llm,value['cloud_profile'])
    transport=transport or Transport()
    result[BOUNDED_SOURCE_ANALYSIS_OPERATION].transport=transport
    semantic_calls=[]
    def semantic_post(endpoint,*,json,headers,timeout):
        semantic_calls.append(deepcopy(json))
        assert json['max_tokens']==8192 and json['thinking']=={'type':'disabled'}
        assert 'reasoning_effort' not in json
        prefix,suffix=SEMANTIC_DECOMPOSITION_USER.split('{claims_json}')
        user=json['messages'][1]['content']
        claims=__import__('json').loads(user[len(prefix):len(user)-len(suffix) if suffix else None])
        output={'claims':[{'parent_claim_id':c['parent_claim_id'],'ir_status':'VALID',
                  'units':[{'predicate_family':'measurement','modality':'actual','nature':c['assigned_nature'] or 'fact',
                      'support_evidence_unit_ids':[c['evidence_units'][0]['evidence_unit_id']],
                      'coherence_key':'k1','coherence_type':'INDEPENDENT','time_scope':'unspecified'}]} for c in claims]}
        return Response(__import__('json').dumps(output))
    monkeypatch.setattr('requests.post',semantic_post)
    value['semantic_http_calls']=semantic_calls
    return result,transport


def start(value, tmp_path, *, count=33):
    source = upload(value, clean_pdf(tmp_path, text=text(count)))
    run = value['service'].start(source['source_id'], idempotency_key='series-binding-synthetic-0001')['run']
    return source, run['processing_run_id']


def advance(value, run_id, provider, *, restart=False):
    if restart:
        value['service'] = SourceOperations(value['config'], value['source_profile'], value['cloud_profile'])
        if provider:
            old = provider[BOUNDED_SOURCE_ANALYSIS_OPERATION]
            provider = {**provider, BOUNDED_SOURCE_ANALYSIS_OPERATION:
                        BoundedSourceAnalysisSegmentProvider(old.cfg, transport=old.transport)}
    transport = provider[BOUNDED_SOURCE_ANALYSIS_OPERATION].transport if provider else None
    before = len(transport.calls) if isinstance(transport, Transport) else 0
    result = value['service'].advance_once(worker_id='synthetic-worker', provider=provider, processing_run_id=run_id)
    if isinstance(transport, Transport):
        assert len(transport.calls) - before <= 1
    return result


def finish(value, run_id, provider, *, restart=False, limit=100):
    for _ in range(limit):
        result = advance(value, run_id, provider, restart=restart)
        if result['state'] in ('HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED','RECOVERY_REQUIRED'):
            return result
    raise AssertionError('SYNTHETIC_WORKFLOW_DID_NOT_TERMINATE')


def rows(value, table):
    with Store(value['config']).connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM '+table)]
