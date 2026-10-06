"""Content-free failure telemetry using disposable fixtures and synthetic HTTP."""
import hashlib
import json
import logging

import pytest
import requests

from pro_a.cloud_contract import ProviderFailure
from pro_a.provider_diagnostics import build_failure_diagnostic
from test_cloud_operation_adapter_binding import setup_run, advance, jobs
from test_phase43_stage72a_provider_diagnostics import Response, adapter
from series_binding_helpers import rows


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External network forbidden")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def fail_run(tmp_path, monkeypatch, content, reason, usage, *, model="deepseek-flash"):
    value = setup_run(tmp_path, monkeypatch)
    calls = []
    def post(*args, **kwargs):
        calls.append(1)
        assert kwargs['json']['max_tokens'] == 12000
        assert kwargs['json']['tools'][0]['function']['strict'] is True
        return Response({'model': model, 'choices': [{'finish_reason': reason,
                        'message': {'role': 'assistant', 'content': None, 'tool_calls': [{'type': 'function',
                            'function': {'name': 'emit_source_analysis', 'arguments': content}}]}}], 'usage': usage},
                        headers={'content-type': 'application/json', 'x-request-id': 'req-synthetic'})
    monkeypatch.setattr('pro_a.llm.requests.post', post)
    final = advance(value)
    path=next(value['config'].artifact_root.glob('bounded-extraction/*/*.raw.json'))
    envelope=json.loads(path.read_bytes())
    import base64
    envelope['output']=base64.b64decode(envelope['raw_body_base64']).decode()
    with value['service'].store.connect() as c:
        outcome = dict(c.execute('SELECT * FROM bounded_extraction_outcomes').fetchone())
        events = [json.loads(r[0]) for r in c.execute('SELECT body_json FROM bounded_extraction_events')]
    assert final['state'] in ('BLOCKED','EXTRACTION_PROCESSING')
    assert final['provider_call_count']==1 and len(calls)==1
    assert len(jobs(value)) == 0 and not rows(value,'bounded_extraction_segment_results')
    # Legacy diagnostic semantics are tested independently through their original
    # adapter. No SourceOperations legacy Run or extraction CloudJob is created.
    legacy,request=adapter(monkeypatch,Response({'model':model,'choices':[{'finish_reason':reason,
                                      'message':{'content':content}}],'usage':usage}))
    with pytest.raises(ProviderFailure) as caught:
        legacy.invoke(request)
    job={'run':final,'raw_envelope':envelope,
         'legacy_diagnostic':diagnostic(**caught.value.diagnostic)}
    assert value['config'].knowledge_db.read_bytes() == value['production_before']
    return value, job, outcome, events


@pytest.mark.parametrize('reason,content,kind,syntax', [
    ('length', '{"value":', 'TRUNCATED', False),
    ('stop', '{"value":}', 'MALFORMED_JSON', False),
    ('stop', '[1,2]', 'NON_OBJECT_JSON', True),
    ('stop', '  ', 'EMPTY_CONTENT', False),
    ('content_filter', '{}', 'CONTENT_FILTER', True),
    ('insufficient_system_resource', '{}', 'INSUFFICIENT_SYSTEM_RESOURCE', True),
    ('tool_calls', '{}', 'TOOL_CALLS', True),
    ('PRIVATE_SOURCE_TEXT_SENTINEL', '{}', 'UNEXPECTED_FINISH_REASON', True),
])
def test_durable_output_failure_classes(tmp_path, monkeypatch, reason, content, kind, syntax):
    usage = {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150,
             'prompt_cache_hit_tokens': 20}
    value, job, outcome, events = fail_run(tmp_path, monkeypatch, content, reason, usage)
    d = job['legacy_diagnostic']
    assert d['failure_stage'] == 'MODEL_OUTPUT_PARSE'
    assert d['error_class'] == ('RESPONSE_EMPTY' if kind == 'EMPTY_CONTENT' else 'OUTPUT_PARSE_ERROR')
    assert d['output_parse_kind'] == kind
    assert d['finish_reason'] == (None if kind == 'UNEXPECTED_FINISH_REASON' else reason)
    assert d['content_length'] == len(content)
    assert d['content_sha256'] == hashlib.sha256(content.encode()).hexdigest()
    assert d['raw_response_syntactically_parseable'] is syntax
    assert 'raw_response_json_error' not in d and 'content_tail' not in d
    if not syntax:
        assert type(d['raw_response_json_error_position']) is int
        assert 0 <= d['raw_response_json_error_position'] <= len(content)
    assert (outcome['input_tokens'], outcome['output_tokens'],
            outcome['total_tokens'], outcome['cached_input_tokens']) == (100, 50, 150, 20)
    assert job['raw_envelope']['provider_reported_model'] == 'deepseek-flash'
    assert outcome['finish_reason'] in ('stop','tool_calls','length','content_filter','error')
    assert outcome['external_outcome'] in ('SUCCEEDED','TRUNCATED','FAILED')
    assert outcome['latency_ms'] >= 0
    assert list(value['config'].artifact_root.glob('bounded-extraction/*/*.raw.json'))
    assert 'PRIVATE_SOURCE_TEXT_SENTINEL' not in json.dumps([outcome, events, job])


@pytest.mark.parametrize('usage', [None, {}, {'prompt_tokens': 2},
    {'prompt_tokens': True, 'completion_tokens': 2, 'total_tokens': 3},
    {'prompt_tokens': 1, 'completion_tokens': -1, 'total_tokens': 3},
    {'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 10_000_001},
    {'prompt_tokens': '1', 'completion_tokens': 2, 'total_tokens': 3}])
def test_unknown_usage_does_not_invent_counts(tmp_path, monkeypatch, usage):
    _, _, outcome, _ = fail_run(tmp_path, monkeypatch, '{', 'stop', usage)
    # CloudJob's established UNKNOWN usage contract does not invent totals.
    assert [outcome[k] for k in ('input_tokens','output_tokens','total_tokens')]==[None,None,None]
    assert outcome['cached_input_tokens'] is None


def diagnostic(**details):
    return build_failure_diagnostic(provider='deepseek', model='deepseek-flash',
        operation_kind='SOURCE_ANALYSIS_PIECE', job_id='JOB_SYNTHETIC', call_id='ATT_SYNTHETIC',
        attempt_number=1, failure_code='PROVIDER_ERROR', retryable=False,
        details={'failure_stage':'MODEL_OUTPUT_PARSE','error_class':'OUTPUT_PARSE_ERROR',
                 'http_status':200, **details})


@pytest.mark.parametrize('bad', [True, -1, 1.5, '123', [], {}, 100_000_001])
def test_numeric_fields_are_strict(bad):
    fields = ('prompt_tokens','completion_tokens','total_tokens','cached_tokens',
              'content_length','raw_response_json_error_position')
    d = diagnostic(**{key:bad for key in fields})
    assert all(d[key] is None for key in fields)


def test_allowlist_and_position_validation():
    d = diagnostic(finish_reason=['stop'], output_parse_kind={'value':'TRUNCATED'},
        response_model='Bearer secret', content_sha256='A'*64,
        raw_response_syntactically_parseable=1, content_length=3,
        raw_response_json_error_position=4, raw_response_json_error='private output',
        content_tail='private output')
    assert all(d[k] is None for k in ('finish_reason','output_parse_kind','response_model',
        'content_sha256','raw_response_syntactically_parseable','raw_response_json_error_position'))
    assert 'private output' not in json.dumps(d)
    assert diagnostic(content_length=0, raw_response_json_error_position=0)['raw_response_json_error_position'] == 0


def test_fingerprint_separates_classes_without_content_identity():
    first = diagnostic(output_parse_kind='TRUNCATED', finish_reason='length',
                       content_length=10, content_sha256='a'*64)
    same = diagnostic(output_parse_kind='TRUNCATED', finish_reason='length',
                      content_length=20, content_sha256='b'*64,
                      raw_response_json_error_position=5, provider_request_id='req-other')
    other = diagnostic(output_parse_kind='MALFORMED_JSON', finish_reason='stop')
    assert first['error_fingerprint'] == same['error_fingerprint']
    assert first['error_fingerprint'] != other['error_fingerprint']


def test_private_output_never_reaches_public_surfaces(tmp_path, monkeypatch, caplog):
    markers = ['PRIVATE_SOURCE_TEXT_SENTINEL','Bearer secret','api_key=secret',
               'C:\\private\\interview.txt','cookie=private','DOCUMENT_EXCERPT_SENTINEL']
    content = '{"private":' + ' '.join(markers)
    with caplog.at_level(logging.DEBUG):
        value, job, outcome, events = fail_run(tmp_path, monkeypatch, content, 'length',
            {'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}, model='api_key=secret')
    receipt = json.dumps({'diagnostic':job['legacy_diagnostic'],'outcome':outcome})
    (tmp_path/'qualification-receipt.json').write_text(receipt, encoding='utf-8')
    with value['service'].store.connect() as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_schema WHERE type='table'")]
        database = json.dumps({t:[list(r) for r in c.execute('SELECT * FROM "'+t+'"')] for t in tables})
    disclosed = database + json.dumps([{k:v for k,v in job.items() if k != 'raw_envelope'},outcome,events]) + caplog.text + receipt
    for p in value['config'].artifact_root.rglob('*.json'):
        if not p.name.endswith('.raw.json'):
            disclosed += p.read_text(encoding='utf-8')
    assert all(marker not in disclosed for marker in markers)
    assert job['legacy_diagnostic']['content_sha256'] == hashlib.sha256(content.encode()).hexdigest()
    assert job['raw_envelope']['output'] == content


def test_standard_cached_usage_metadata(tmp_path, monkeypatch):
    _, _, outcome, _ = fail_run(tmp_path, monkeypatch, '{', 'length',
        {'prompt_tokens':3,'completion_tokens':2,'total_tokens':5,
         'prompt_tokens_details':{'cached_tokens':1}})
    assert outcome['cached_input_tokens'] == 1


@pytest.mark.parametrize('cached', [True, -1, '1', 10_000_001])
def test_invalid_cached_count_does_not_invalidate_known_usage(tmp_path, monkeypatch, cached):
    _, _, outcome, _ = fail_run(tmp_path, monkeypatch, '{', 'length',
        {'prompt_tokens':3,'completion_tokens':2,'total_tokens':5,'prompt_cache_hit_tokens':cached})
    assert outcome['input_tokens']==3 and outcome['output_tokens']==2 and outcome['total_tokens']==5
    assert outcome['cached_input_tokens'] is None


@pytest.mark.parametrize('response,stage,error,retryable', [
    (Response({}, 401), 'HTTP_RESPONSE', 'HTTP_401', False),
    (Response({}, 403), 'HTTP_RESPONSE', 'HTTP_403', False),
    (Response({}, 429), 'HTTP_RESPONSE', 'HTTP_429', True),
    (Response({}, 500), 'HTTP_RESPONSE', 'HTTP_500', True),
    (Response({}, 503), 'HTTP_RESPONSE', 'HTTP_503', True),
    (requests.exceptions.ConnectTimeout('synthetic'), 'TRANSPORT', 'TRANSPORT_TIMEOUT', False),
    (Response({}, invalid_json=True), 'PROVIDER_PARSE', 'RESPONSE_JSON_PARSE_ERROR', False),
    (Response({'choices':[]}), 'PROVIDER_PARSE', 'PROVIDER_RESPONSE_SCHEMA_ERROR', False),
])
def test_non_output_failures_keep_classification(monkeypatch, response, stage, error, retryable):
    provider, request = adapter(monkeypatch, response)
    with pytest.raises(ProviderFailure) as caught:
        provider.invoke(request)
    failure = caught.value
    d = diagnostic(**failure.diagnostic)
    assert (d['failure_stage'],d['error_class']) == (stage,error)
    assert failure.retryable is retryable
    assert d['output_parse_kind'] is None and d['finish_reason'] is None


@pytest.mark.parametrize('value', ['a'*63, 'a'*65, 'A'*64, 'a'*64+'\n', 'Bearer secret'])
def test_hash_validation_does_not_truncate(value):
    assert diagnostic(content_sha256=value)['content_sha256'] is None
