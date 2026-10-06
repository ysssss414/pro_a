"""Synthetic envelope only: never contact a real provider."""
from copy import deepcopy
from dataclasses import replace

import pytest
import requests
from pro_a.config import LLMConfig
from pro_a.cloud_contract import CloudRequest, ProviderFailure, operation_contract
from pro_a.whole_piece_compact import WholePieceCompactProvider, render, contract, BETA_ENDPOINT
from pro_a.source_analysis_provider_record import TOOL_NAME, record_schema, tool_schema_sha256
from series_binding_helpers import ToolResponse
from test_source_analysis_wire import dense_fixture
from test_whole_piece_compact import payload_for


def request():
    ctx, _, _ = dense_fixture()
    return CloudRequest('JOB_SYNTHETIC', 'ATTEMPT_SYNTHETIC', 1, 'SOURCE_ANALYSIS_PIECE', 'INPUT_SYNTHETIC',
        'a'*64, 'SOURCE_SYNTHETIC', {}, '12', 'deepseek', 'deepseek-flash', operation_contract('SOURCE_ANALYSIS_PIECE'),
        {'configuration_sha256': 'b'*64}, 120, 12000, 'synthetic-one-attempt', {}, payload_for(ctx))


def provider(monkeypatch, transport):
    monkeypatch.setenv('PROA_LLM_API_KEY', 'synthetic-key')
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('NETWORK_FORBIDDEN'))
    return WholePieceCompactProvider(LLMConfig(enabled=True, model='deepseek-flash', max_retries=0,
        max_output_tokens=12000, timeout_seconds=120), transport=transport)


def test_frozen_tool_identity_and_raw_not_parsed(monkeypatch):
    calls = []
    raw = '  {"not":"valid provider record"}  '
    class ForbiddenReasoning:
        def __str__(self): raise AssertionError('REASONING_INSPECTED')
        def __bool__(self): raise AssertionError('REASONING_INSPECTED')
    def transport(endpoint, **kwargs):
        calls.append(kwargs)
        assert endpoint == BETA_ENDPOINT and kwargs['allow_redirects'] is False
        assert kwargs['timeout'] == 120
        body = kwargs['json']
        assert body == render(request().payload)
        assert body['thinking'] == {'type': 'disabled'} and body['stream'] is False
        assert body['max_tokens'] == 12000 and 'response_format' not in body
        assert body['tool_choice'] == {'type': 'function', 'function': {'name': TOOL_NAME}}
        assert len(body['tools']) == 1
        assert body['tools'][0]['function']['parameters'] == record_schema()
        assert body['tools'][0]['function']['strict'] is True
        response = ToolResponse(raw, reasoning=ForbiddenReasoning())
        response.value['choices'][0]['message']['content'] = 'MUST_NOT_JOIN_ASSISTANT_TEXT'
        return response
    result = provider(monkeypatch, transport).invoke(request())
    assert result.output == raw and result.finish_reason == 'tool_calls' and len(calls) == 1
    identity = request().prompt_identity
    assert identity['tool_schema_sha256'] == tool_schema_sha256()
    assert identity['tool_parameters'] == record_schema()
    assert contract()['provider_execution_mode'] == 'DEEPSEEK_STRICT_TOOL_LEXICAL'


@pytest.mark.parametrize('change', ['no_choice', 'two_choices', 'no_tool', 'two_tools', 'wrong_name',
    'wrong_type', 'missing_arguments', 'object_arguments', 'wrong_role', 'assistant_only'])
def test_bad_wrapper_fail_closed(monkeypatch, change):
    response = ToolResponse('{}')
    choice = response.value['choices'][0]
    message = choice['message']
    call = message['tool_calls'][0]
    if change == 'no_choice': response.value['choices'] = []
    elif change == 'two_choices': response.value['choices'] *= 2
    elif change in ('no_tool', 'assistant_only'):
        message.pop('tool_calls')
        message['content'] = '{}'
    elif change == 'two_tools': message['tool_calls'] *= 2
    elif change == 'wrong_name': call['function']['name'] = 'wrong'
    elif change == 'wrong_type': call['type'] = 'other'
    elif change == 'missing_arguments': del call['function']['arguments']
    elif change == 'object_arguments': call['function']['arguments'] = {}
    else: message['role'] = 'user'
    calls = []
    def transport(*a, **k):
        calls.append(1)
        return response
    with pytest.raises(ProviderFailure, match='INVALID_PROVIDER_TOOL_SHAPE') as error:
        provider(monkeypatch, transport).invoke(request())
    assert len(calls) == 1 and error.value.retryable is False


@pytest.mark.parametrize('field', ['tool_schema_sha256', 'tool_name', 'tool_strict', 'tool_parameters', 'bool_alias', 'schema_bool_alias'])
def test_schema_drift_before_dispatch(monkeypatch, field):
    frozen = request()
    identity = deepcopy(frozen.prompt_identity)
    if field == 'bool_alias': identity['tool_strict'] = 1
    elif field == 'schema_bool_alias': identity['tool_parameters']['additionalProperties'] = 0
    else: identity[field] = 'drift'
    def forbidden(*a, **k): pytest.fail('DISPATCH_FORBIDDEN')
    with pytest.raises(ProviderFailure, match='CONFIGURATION_MISMATCH'):
        provider(monkeypatch, forbidden).invoke(replace(frozen, prompt_identity=identity))


def test_unknown_no_retry_or_fallback(monkeypatch):
    calls = []
    def transport(*a, **k):
        calls.append(1)
        raise requests.ReadTimeout('PRIVATE_FAILURE')
    with pytest.raises(ProviderFailure, match='UNKNOWN_EXTERNAL_OUTCOME') as error:
        provider(monkeypatch, transport).invoke(request())
    assert len(calls) == 1 and error.value.external_outcome == 'UNKNOWN' and not error.value.retryable


def test_no_git_sensitive_schema_identity():
    from pro_a.workbench.retry_compatibility import _CLOUD_EXECUTION_DEPENDENCIES
    assert 'source_analysis_provider_record.py' in _CLOUD_EXECUTION_DEPENDENCIES
    assert contract()['tool_parameters'] == record_schema()
