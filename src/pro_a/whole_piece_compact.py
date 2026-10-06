"""Complete frozen SourcePiece, lexical tool arguments, local Wire/Evidence acceptance."""
from __future__ import annotations

import hashlib
import json
import time
from urllib.parse import urlsplit

import requests

from .analyzer import SourcePiece
from .bounded_extraction import expand_source_analysis_wire_v3
from .constants import (CLAIM_NATURES, CLAIM_STATUSES, NODE_TYPES, NOVELTY_LEVELS,
                        RELATION_TYPES, SOURCE_ORIGIN_TYPES, SOURCE_RANKS)
from .prompts import SOURCE_ANALYSIS_SYSTEM
from .evidence_binding import EVIDENCE_MODES
from .source_analysis_provider_record import (VERSION as PROVIDER_RECORD_VERSION, TOOL_SCHEMA_VERSION,
    TOOL_NAME, record_schema, tool_schema_sha256, parse_object, provider_record_to_wire_v3)
from .provider_diagnostics import safe_identifier, safe_request_id, safe_reasoning_tokens
from .source_analysis_wire import (NODE_MATCH_ROLES, SOURCE_REFERENCE_RELATION_TYPES,
                                   SourcePieceContext, build_source_evidence_catalog)

RESPONSE_VERSION = 'whole-piece-lexical-tool-source-analysis-response-v1'
PROMPT_VERSION = 'whole-piece-lexical-tool-source-analysis-prompt-v1'
ADAPTER_VERSION = 'whole-piece-lexical-tool-source-analysis-adapter-v1'
ENUM_TABLE = {
    'evidence_mode': EVIDENCE_MODES,
    'node_matches[].role': NODE_MATCH_ROLES,
    'claims[].nature': CLAIM_NATURES, 'claims[].status': CLAIM_STATUSES,
    'claims[].novelty_level': NOVELTY_LEVELS, 'node_candidates[].primary_type': NODE_TYPES,
    'source_metadata.source_rank': SOURCE_RANKS,
    'source_metadata.source_origin_type': SOURCE_ORIGIN_TYPES,
    'relation_candidates[].relation_type': sorted(set(RELATION_TYPES) - {'part_of'}),
    'source_references[].relation_type': SOURCE_REFERENCE_RELATION_TYPES,
}
BETA_ENDPOINT = 'https://api.deepseek.com/beta/chat/completions'
SYSTEM = SOURCE_ANALYSIS_SYSTEM + """
本调用仅通过 emit_source_analysis 工具提交 lexical ProviderRecord；以下表示规则替代原有 verbose JSON 格式。
语义上下文仍为完整冻结 SourcePiece；保留上文全部语义、归因与研究准入规则。不得引入外部材料、虚构 Node ID 或 Evidence。
工具对象所有字段必须出现；没有内容的数组为[]，可选文本为""。枚举必须逐字符合工具定义，不以业务角色代替 node_match role。
布尔判断仅用字符串 TRUE/FALSE。confidence 用0到1十进制字符串，不用指数、空格、NaN或Infinity；仅兼容精确负零小数，不接受负值。
每个 Evidence 固定有 evidence_ref、selection_mode、selector、occurrence 四个字符串。
完整单元用 WHOLE_UNIT、selector=""、occurrence="1"。子串总是给出模式和精确的1起始 occurrence，无论是否重复。
原文逐字存在时优先 RAW_SUBSPAN；仅现有规范化匹配需要时用 NORMALIZED_SUBSPAN，不静默改写 RAW selector。
在引用单元中按所选模式计数，给出确切次数；不能确定时，只在整段直接支持对象时选整段，否则不输出该 Evidence 绑定对象。不得猜测。
Claim 的 evidence_pointer 保留原文标记；不输出 claim_ref、evidence_excerpt 或偏移。C1、C2等由Claim数组顺序派生。
structured_json 必须是合法JSON对象的字符串，空对象为"{}"，禁止重复键与非有限数值。
candidate 按 primary_type 启用 Event、Theme、ResearchQuestion 专用槽；其他类型和未启用槽必须为 FALSE、空文本。
未启用 event_evidence 必须精确为 {"evidence_ref":"","selection_mode":"NONE","selector":"","occurrence":"1"}；NONE仅供未启用槽，不能绑定Evidence。
preserved_fields 为兼容原有canonical专用字段：每个槽均有 present 与 value。未出现用 present=FALSE及精确空默认值；
仅非当前类型的确有内容字段可用 present=TRUE。Evidence槽的空默认值为上述NONE记录，布尔槽为FALSE，文本槽为空字符串。不得静默丢弃内容。
relation supporting_claim_refs 至少一个有效本响应C引用；不输出 part_of。不得生成细分指令、dispositions或上下文依赖图。
工具schema只协助格式；所有值由本地严格验证，研究判断仍须人工审核。
"""


def contract():
    return {'response_version': RESPONSE_VERSION, 'prompt_version': PROMPT_VERSION,
            'adapter_version': ADAPTER_VERSION,
            'provider_execution_mode': 'DEEPSEEK_STRICT_TOOL_LEXICAL',
            'provider_record_version': PROVIDER_RECORD_VERSION, 'tool_schema_version': TOOL_SCHEMA_VERSION,
            'tool_schema_sha256': tool_schema_sha256(), 'tool_name': TOOL_NAME, 'tool_strict': True,
            'tool_parameters': record_schema(), 'provider_endpoint': BETA_ENDPOINT,
            'strict_tool_role': 'FORMAT_COMPLIANCE_ASSIST', 'authoritative_validator': 'LOCAL', 'wire': 'source-analysis-wire-v3',
            'evidence_binding': 'source-analysis-evidence-binding-v2',
            'expander': 'source-analysis-wire-expander-v2',
            'max_output_tokens': 12000, 'automatic_extraction_retry': False,
            'system_prompt_sha256': hashlib.sha256(SYSTEM.encode()).hexdigest()}


def piece_context(payload):
    piece = SourcePiece(**payload['source_piece'])
    if (piece.source_text != payload['source_text'] or piece.piece_id != payload['piece_id']
            or piece.source_sha256 != payload['source_piece_sha256']):
        raise ValueError('WHOLE_PIECE_INPUT_MISMATCH')
    ctx = SourcePieceContext(payload['source_sha256'], piece,
                            tuple(n['node_id'] for n in payload['scoped_node_catalog']))
    return ctx, build_source_evidence_catalog(ctx)


def render(payload):
    ctx, catalog = piece_context(payload)
    parts, cursor = [], 0
    for unit in catalog.units:
        parts.extend((ctx.piece.source_text[cursor:unit.source_start],
                      '[' + unit.evidence_ref + ']', unit.exact_text, '[/' + unit.evidence_ref + ']'))
        cursor = unit.source_end
    parts.append(ctx.piece.source_text[cursor:])
    user = ('Frozen target:\n' + json.dumps({'source_sha256': ctx.source_sha256,
            'piece_id': ctx.piece.piece_id, 'piece_sha256': ctx.piece.source_sha256, **{k: v for k, v in contract().items() if k != 'tool_parameters'}}, sort_keys=True)
            + '\nScoped existing Nodes:\n' + json.dumps(payload['scoped_node_catalog'], ensure_ascii=False)
            + '\nComplete annotated SourcePiece:\n' + ''.join(parts))
    return {'model': 'deepseek-flash', 'max_tokens': 12000, 'thinking': {'type': 'disabled'},
            'stream': False, 'temperature': 0.1,
            'tools': [{'type': 'function', 'function': {'name': TOOL_NAME, 'strict': True,
                'description': '提交完整冻结SourcePiece的分析记录。', 'parameters': record_schema()}}],
            'tool_choice': {'type': 'function', 'function': {'name': TOOL_NAME}},
            'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}]}


def parse(content, payload):
    try:
        record = parse_object(content)
        wire = provider_record_to_wire_v3(record)
        ctx, catalog = piece_context(payload)
        return expand_source_analysis_wire_v3(wire, catalog, ctx)
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError('INVALID_WHOLE_PIECE_LEXICAL_RESPONSE') from None


class WholePieceCompactProvider:
    provider_identity = 'deepseek'
    adapter_version = ADAPTER_VERSION

    def __init__(self, cfg, *, transport=None):
        self.cfg, self.transport = cfg, transport
        url = urlsplit(cfg.base_url)
        if (cfg.provider != 'deepseek' or cfg.model != 'deepseek-flash' or cfg.max_retries != 0
                or cfg.max_output_tokens != 12000 or url.scheme != 'https' or url.username or url.password
                or url.hostname != 'api.deepseek.com' or url.port not in (None, 443)
                or url.query or url.fragment or url.path not in ('', '/', '/v1', '/v1/')):
            raise ValueError('WHOLE_PIECE_PROVIDER_CONFIGURATION_MISMATCH')

    def invoke(self, request):
        from .cloud_contract import CloudResult, ProviderFailure, now, operation_contract, digest
        cfg = self.cfg
        if (request.operation_kind != 'SOURCE_ANALYSIS_PIECE'
                or digest(request.prompt_identity) != digest(operation_contract('SOURCE_ANALYSIS_PIECE'))
                or request.requested_model != cfg.model or request.provider != self.provider_identity
                or request.timeout_seconds != cfg.timeout_seconds or request.max_output_tokens != 12000
                or cfg.max_retries != 0 or not cfg.enabled or not cfg.api_key):
            raise ProviderFailure('PROVIDER_CONFIGURATION_MISMATCH', retryable=False, external_outcome='NOT_DISPATCHED')
        body = render(request.payload)
        return self._send(body, request.operation_kind, request.attempt_number)

    def _send(self, body, operation_kind, attempt_number):
        """One lexical tool HTTP call; arguments stay unparsed for durable storage."""
        from .cloud_contract import CloudResult, ProviderFailure, now
        cfg = self.cfg
        started_at, started = now(), time.perf_counter()
        try:
            response = (self.transport or requests.post)(BETA_ENDPOINT,
                json=body, headers={'Authorization': 'Bearer ' + cfg.api_key, 'Content-Type': 'application/json'},
                timeout=cfg.timeout_seconds, allow_redirects=False)
        except requests.RequestException:
            raise ProviderFailure('UNKNOWN_EXTERNAL_OUTCOME', retryable=False, external_outcome='UNKNOWN') from None
        if response.status_code != 200:
            raise ProviderFailure('PROVIDER_ERROR', retryable=False, external_outcome='KNOWN_FAILURE',
                                  diagnostic={'http_status': response.status_code})
        try:
            data = response.json()  # HTTP wrapper only; arguments remain exact unparsed text.
        except ValueError:
            raise ProviderFailure('UNKNOWN_EXTERNAL_OUTCOME', retryable=False, external_outcome='UNKNOWN') from None
        try:
            if type(data) is not dict or type(data['choices']) is not list or len(data['choices']) != 1:
                raise ValueError()
            choice = data['choices'][0]
            message = choice['message']
            calls = message['tool_calls']
            if message['role'] != 'assistant' or type(calls) is not list or len(calls) != 1:
                raise ValueError()
            call = calls[0]
            if call['type'] != 'function' or call['function']['name'] != TOOL_NAME:
                raise ValueError()
            content = call['function']['arguments']
            if type(content) is not str:
                raise ValueError()
        except (ValueError, KeyError, TypeError, IndexError):
            raise ProviderFailure('INVALID_PROVIDER_TOOL_SHAPE', retryable=False, external_outcome='KNOWN_FAILURE') from None
        usage = data.get('usage') or {}
        if not isinstance(usage, dict):
            usage = {}
        counts = [usage.get(k) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')]
        known = all(type(v) is int and 0 <= v <= 10_000_000 for v in counts)
        cached = usage.get('prompt_cache_hit_tokens')
        if 'prompt_cache_hit_tokens' not in usage and isinstance(usage.get('prompt_tokens_details'), dict):
            cached = usage['prompt_tokens_details'].get('cached_tokens')
        if not known or type(cached) is not int or not 0 <= cached <= counts[0]:
            cached = None
        details = usage.get('completion_tokens_details')
        reasoning = safe_reasoning_tokens(details.get('reasoning_tokens'), counts[1]) if known and isinstance(details, dict) else None
        return CloudResult(provider=self.provider_identity, requested_model=cfg.model,
            provider_reported_model=safe_identifier(data.get('model')) or 'UNKNOWN',
            provider_request_id=safe_request_id(response.headers.get('x-request-id') or data.get('id')),
            operation_kind=operation_kind, attempt_number=attempt_number,
            started_at=started_at, ended_at=now(), latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=choice.get('finish_reason') if choice.get('finish_reason') in ('tool_calls', 'stop', 'length', 'content_filter') else 'UNKNOWN',
            usage_status='KNOWN' if known else 'UNKNOWN', input_tokens=counts[0] if known else None,
            output_tokens=counts[1] if known else None, total_tokens=counts[2] if known else None,
            cached_tokens=cached, reasoning_tokens=reasoning, output=content,
            transport_diagnostic={'http_status': 200})
