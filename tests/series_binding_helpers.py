"""Synthetic HTTP through the whole-piece compact adapter; no external providers."""
from copy import deepcopy
from dataclasses import replace
import json
import re
from contextlib import contextmanager
import os
from unittest.mock import patch

import requests

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
        return len(self['WHOLE_PIECE_OUTPUT_BATCH'].transport.calls)+self['SEMANTIC_DECOMPOSITION'].call_count


@contextmanager
def synthetic_providers(value,transport=None):
    from pro_a.output_decomposition import OutputBatchProvider
    from pro_a.output_capacity import SEGMENT_OUTPUT_CEILING
    with patch.dict(os.environ,{'PROA_SYNTHETIC_BOUNDED_KEY':'synthetic-fixture'}):
        cfg=LLMConfig(enabled=True,api_key_env='PROA_SYNTHETIC_BOUNDED_KEY',model='deepseek-flash',
                      max_retries=0,max_output_tokens=SEGMENT_OUTPUT_CEILING,timeout_seconds=value['cloud_profile'].timeout_seconds)
        yield SyntheticProviders({'WHOLE_PIECE_OUTPUT_BATCH':OutputBatchProvider(cfg,transport=transport or Transport()),
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


class ToolResponse(Response):
    def __init__(self, content, finish='tool_calls', output=50, reasoning=None):
        from pro_a.source_analysis_provider_record import TOOL_NAME
        super().__init__(None, finish, output, reasoning)
        self.value['choices'][0]['message'].update(role='assistant', tool_calls=[{
            'type': 'function', 'function': {'name': TOOL_NAME, 'arguments': content}}])


class Transport:
    def __init__(self, *, mode=None, callback=None):
        self.mode, self.callback, self.calls = mode, callback, []

    def __call__(self, endpoint, *, json, headers, timeout, allow_redirects=False):
        self.calls.append(deepcopy(json))
        if self.callback:
            self.callback(json)
        target, source = request_parts(json)
        whole = 'assigned_evidence_refs' not in target
        lexical = bool(json.get('tools'))
        response_type = ToolResponse if lexical else Response
        if whole:
            target['assigned_evidence_refs'] = re.findall(r'\[(EV_[^\]]+)\]', source)
        mode = self.mode(target, len(self.calls)) if callable(self.mode) else self.mode
        if mode == 'unknown':
            raise requests.ReadTimeout('SYNTHETIC_UNTRUSTED_EXCEPTION')
        if mode == 'truncated':
            return response_type('{"wire":{"claims":[', 'length', json['max_tokens'])
        if mode == 'malformed':
            return response_type('SYNTHETIC_MALFORMED_PRIVATE_CONTENT')
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
        if lexical:
            value = __import__('json').loads(content)
            from lexical_record_helpers import from_wire
            record = from_wire(value['wire'])
            if not whole:
                record['evidence_acknowledgements'] = [{'evidence_ref': ref} for ref in target['assigned_evidence_refs']]
                for family in ('node_candidates','source_references'):
                    for obj in record[family]:
                        obj['ownership_evidence_ref'] = target['assigned_evidence_refs'][0]
            content = __import__('json').dumps(record, ensure_ascii=False)
        return response_type(content)


def batch_record(response, target):
    from lexical_record_helpers import from_wire
    record = from_wire(response['wire'])
    record['evidence_acknowledgements'] = [{'evidence_ref': ref} for ref in target['assigned_evidence_refs']]
    for family in ('node_candidates','source_references'):
        for obj in record[family]:
            obj['ownership_evidence_ref'] = target['assigned_evidence_refs'][0]
    return record


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



def start(value, tmp_path, *, count=33):
    source = upload(value, clean_pdf(tmp_path, text=text(count)))
    run = value['service'].start(source['source_id'], idempotency_key='series-binding-synthetic-0001')['run']
    return source, run['processing_run_id']



def rows(value, table):
    with Store(value['config']).connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM '+table)]
