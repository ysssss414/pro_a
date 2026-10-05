"""Complete frozen SourcePiece input, compact V3 output, exact Evidence binding."""
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
from .provider_diagnostics import safe_identifier, safe_request_id, safe_reasoning_tokens
from .source_analysis_wire import (NODE_MATCH_ROLES, SOURCE_REFERENCE_RELATION_TYPES,
                                   SourcePieceContext, build_source_evidence_catalog)

RESPONSE_VERSION = 'whole-piece-compact-source-analysis-response-v1'
PROMPT_VERSION = 'whole-piece-compact-source-analysis-prompt-v1'
ADAPTER_VERSION = 'whole-piece-compact-source-analysis-adapter-v1'
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
SYSTEM = SOURCE_ANALYSIS_SYSTEM + '''
本调用使用 whole-piece-compact-source-analysis-response-v1；以下输出表示规则替代原有 verbose JSON 表示。
输出恰好一个 JSON 对象，仅有 wire。wire.wire_version 为 source-analysis-wire-v3。
语义上下文是完整冻结 SourcePiece。所有标注 Evidence 都可引用，标记仅为系统元数据。
保留上文全部语义与研究准入规则。不得引入外部材料、虚构 Node ID 或 Evidence。
wire.source_metadata 必须有 title、publication_time、source_rank、source_origin_type；可选 author、organization、summary。
wire.claims 为数组，每条必须有 statement、nature、evidence_ref、evidence_pointer、attributed_to、fact_time、scope、confidence、novelty_level。
每条 Claim 只选择一个 Evidence；省略 selector 表示完整 Evidence 单元。
局部引用使用 evidence_selector 精确连续字符串、从1开始的 evidence_occurrence，以及 evidence_mode
（RAW_SUBSPAN 或 NORMALIZED_SUBSPAN）。重复文本必须给出 occurrence。不得生成偏移或 evidence_excerpt。
evidence_pointer 保留原文标记。可选 Claim 字段为 related_node_ids、related_candidate_names、assumption、status、structured。
可选顶层数组为 node_matches、node_candidates、relation_candidates、source_references。
node_matches 必须有 node_id、role、confidence、evidence_ref；可选 reason 和 Evidence selector。
node_candidates 必须有 canonical_name、primary_type、confidence、independent_research_value、maintenance_rationale；
可选 aliases、description、suggested_parent_node_ids、reason、preserved_fields。
Event 必须有 is_discrete_event、event_time、evidence_ref；Theme 必须有 long_term_research_value、cross_source_or_node_value；
ResearchQuestion 必须有 question、importance、what_would_change_my_mind。Evidence 字段同样允许 selector。
其他类型的非默认专用字段放入 preserved_fields。禁止将未出现的类型专用字段放在顶层。
relation_candidates 必须有 from_node_id、to_node_id、relation_type、scope、confidence、supporting_claim_refs，可选 reason。
supporting_claim_refs 为本响应 Claim 顺序 C1、C2 等，至少一个有效引用。
source_references 必须有 title、relation_type，可选 note。confidence 为0到1数字。
不输出 dispositions、assigned_evidence_refs、细分指令或上下文依赖图。研究判断仍需人工审核。
枚举必须与下表逐字一致，不改变大小写、不添加空格，不以实体类型或业务角色代替 role：
''' + json.dumps(ENUM_TABLE, ensure_ascii=False, sort_keys=True)


def contract():
    return {'response_version': RESPONSE_VERSION, 'prompt_version': PROMPT_VERSION,
            'adapter_version': ADAPTER_VERSION, 'wire': 'source-analysis-wire-v3',
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
            'piece_id': ctx.piece.piece_id, 'piece_sha256': ctx.piece.source_sha256, **contract()}, sort_keys=True)
            + '\nScoped existing Nodes:\n' + json.dumps(payload['scoped_node_catalog'], ensure_ascii=False)
            + '\nComplete annotated SourcePiece:\n' + ''.join(parts))
    return {'model': 'deepseek-flash', 'max_tokens': 12000, 'thinking': {'type': 'disabled'},
            'response_format': {'type': 'json_object'}, 'temperature': 0.1,
            'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}]}


def parse(content, payload):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('DUPLICATE_JSON_KEY')
            obj[key] = value
        return obj
    try:
        obj = json.loads(content, object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(obj, dict) or set(obj) != {'wire'}:
            raise ValueError()
        ctx, catalog = piece_context(payload)
        return expand_source_analysis_wire_v3(obj['wire'], catalog, ctx)
    except (ValueError, TypeError, KeyError):
        raise ValueError('INVALID_WHOLE_PIECE_COMPACT_RESPONSE') from None


class WholePieceCompactProvider:
    provider_identity = 'deepseek'
    adapter_version = ADAPTER_VERSION

    def __init__(self, cfg, *, transport=None):
        self.cfg, self.transport = cfg, transport
        url = urlsplit(cfg.base_url)
        if (cfg.provider != 'deepseek' or cfg.model != 'deepseek-flash' or cfg.max_retries != 0
                or cfg.max_output_tokens != 12000 or url.scheme != 'https' or url.username or url.password
                or url.query or url.fragment or url.path not in ('', '/', '/v1', '/v1/')):
            raise ValueError('WHOLE_PIECE_PROVIDER_CONFIGURATION_MISMATCH')

    def invoke(self, request):
        from .cloud_contract import CloudResult, ProviderFailure, now, operation_contract
        cfg = self.cfg
        if (request.operation_kind != 'SOURCE_ANALYSIS_PIECE'
                or request.prompt_identity != operation_contract('SOURCE_ANALYSIS_PIECE')
                or request.requested_model != cfg.model or request.provider != self.provider_identity
                or request.timeout_seconds != cfg.timeout_seconds or request.max_output_tokens != 12000
                or cfg.max_retries != 0 or not cfg.enabled or not cfg.api_key):
            raise ProviderFailure('PROVIDER_CONFIGURATION_MISMATCH', retryable=False, external_outcome='NOT_DISPATCHED')
        body = render(request.payload)
        started_at, started = now(), time.perf_counter()
        try:
            response = (self.transport or requests.post)(cfg.base_url.rstrip('/') + '/chat/completions',
                json=body, headers={'Authorization': 'Bearer ' + cfg.api_key, 'Content-Type': 'application/json'},
                timeout=cfg.timeout_seconds)
        except requests.RequestException:
            raise ProviderFailure('UNKNOWN_EXTERNAL_OUTCOME', retryable=False, external_outcome='UNKNOWN') from None
        if response.status_code != 200:
            raise ProviderFailure('PROVIDER_ERROR', retryable=False, external_outcome='KNOWN_FAILURE',
                                  diagnostic={'http_status': response.status_code})
        try:
            data = response.json()  # HTTP envelope only; message.content remains unparsed.
            choice = data['choices'][0]
            content = choice['message']['content']
            if type(content) is not str:
                raise ValueError()
        except (ValueError, KeyError, TypeError, IndexError):
            raise ProviderFailure('UNKNOWN_EXTERNAL_OUTCOME', retryable=False, external_outcome='UNKNOWN') from None
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
            operation_kind=request.operation_kind, attempt_number=request.attempt_number,
            started_at=started_at, ended_at=now(), latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=choice.get('finish_reason') if choice.get('finish_reason') in ('stop', 'length', 'content_filter') else 'UNKNOWN',
            usage_status='KNOWN' if known else 'UNKNOWN', input_tokens=counts[0] if known else None,
            output_tokens=counts[1] if known else None, total_tokens=counts[2] if known else None,
            cached_tokens=cached, reasoning_tokens=reasoning, output=content,
            transport_diagnostic={'http_status': 200})
