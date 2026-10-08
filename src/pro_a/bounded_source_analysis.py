"""Explicit bounded Segment prompt and one-call, unparsed-content transport."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import time
from urllib.parse import urlsplit

import requests

from .analyzer import FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS, INITIAL_EXTRACTION_PLANNER_VERSION, SourcePiece
from .bounded_extraction import (
    BOUNDED_EXTRACTION_SERIES_VERSION, BOUNDED_EXTRACTION_SEGMENT_VERSION,
    BOUNDED_EXTRACTION_COVERAGE_VERSION, BOUNDED_EXTRACTION_SUBDIVISION_VERSION,
    BOUNDED_EXTRACTION_POLICY_VERSION, LEGACY_SEGMENT_OUTPUT_CEILING as SEGMENT_OUTPUT_CEILING, SeriesBudget,
    SOURCE_ANALYSIS_WIRE_V3_VERSION, SOURCE_ANALYSIS_WIRE_V3_EXPANDER_VERSION,
    create_extraction_series,
)
from .evidence_binding import SOURCE_ANALYSIS_EVIDENCE_BINDING_VERSION, validate_catalog
from .prompts import SOURCE_ANALYSIS_SYSTEM
from .provider_diagnostics import safe_identifier, safe_reasoning_tokens, safe_request_id
from .source_analysis_wire import SourcePieceContext, build_source_evidence_catalog

BOUNDED_SOURCE_ANALYSIS_BINDING_VERSION = "bounded-source-analysis-series-binding-v1"
BOUNDED_SOURCE_ANALYSIS_PROVIDER_VERSION = "bounded-source-analysis-segment-provider-v1"
BOUNDED_SOURCE_ANALYSIS_PROMPT_VERSION = "bounded-source-analysis-segment-prompt-v1"
BOUNDED_SOURCE_ANALYSIS_RESPONSE_VERSION = "bounded-source-analysis-response-v1"
BOUNDED_SOURCE_ANALYSIS_OPERATION = "BOUNDED_SOURCE_ANALYSIS_SEGMENT"

# Preserve all native semantic rules, changing only their provider representation.
BOUNDED_SOURCE_ANALYSIS_SYSTEM = SOURCE_ANALYSIS_SYSTEM + r"""
本调用采用 bounded-source-analysis-response-v1，输出恰好一个 JSON 对象，只有 wire 和 dispositions。
wire.wire_version 必须为 source-analysis-wire-v3。原有语义与准入规则全部适用。
Source 文本仅出现于带 Evidence ID 的完整材料中。标记是系统元数据，不是原文。
只允许使用 assigned_evidence_refs；不得选择范围、添加外部知识或引用未分配 Evidence。
wire.source_metadata 必须有 title、publication_time、source_rank、source_origin_type，
可选 author、organization、summary。wire.claims 是数组；每条必须有 statement、nature、
evidence_ref、evidence_pointer、attributed_to、fact_time、scope、confidence、novelty_level。
evidence_pointer 沿用原文标记。省略 evidence_selector 时选中该 Evidence 的完整精确文本。
选择局部连续原文时用 evidence_selector（逐字字符串）、evidence_occurrence（从1开始）和
evidence_mode（RAW_SUBSPAN 或 NORMALIZED_SUBSPAN），不得提供偏移；系统解析，不接受生成的 evidence_excerpt。
可选 Claim 字段为 related_node_ids、related_candidate_names、assumption、status、structured。
可选顶层数组为 node_matches、node_candidates、relation_candidates、source_references。
node_matches 使用 node_id、role、confidence、evidence_ref，可选 reason 和上述 Evidence selector。
Node candidates 保留原有类型语义与字段，必须有 canonical_name、primary_type、confidence、
independent_research_value、maintenance_rationale；涉及 Evidence 时使用同样的 Evidence 选择规则。
relations 使用 from_node_id、to_node_id、relation_type、scope、confidence、supporting_claim_refs，可选 reason；
supporting_claim_refs 为本响应中的 C1、C2 等顺序索引，至少一个，不得引用其他 Segment 的 Claim。
source_references 使用 title、relation_type（references、updates、derived_from），可选 note。
Event 必须有 is_discrete_event、event_time、evidence_ref；Theme 必须有 long_term_research_value、
cross_source_or_node_value；ResearchQuestion 必须有 question、importance、what_would_change_my_mind。
dispositions 是数组，分配的每个 Evidence ref 必须恰好出现一次，包含 evidence_ref 和 disposition。
存在引用该 ref 的 Claim 时必须为 CLAIMED；否则为 NO_INDEPENDENT_CLAIM 或 CONTEXT_ONLY。
若范围过密无法安全完整完成，wire.claims 必须为空，全部 dispositions 为 SUBDIVISION_REQUIRED；
不得提供部分结果，不得使用继续生成的自然语言或模型游标。系统负责确定性细分。
"""


def binding_contract():
    return {
        "binding_version": BOUNDED_SOURCE_ANALYSIS_BINDING_VERSION,
        "provider_version": BOUNDED_SOURCE_ANALYSIS_PROVIDER_VERSION,
        "prompt_version": BOUNDED_SOURCE_ANALYSIS_PROMPT_VERSION,
        "response_version": BOUNDED_SOURCE_ANALYSIS_RESPONSE_VERSION,
        "series": BOUNDED_EXTRACTION_SERIES_VERSION, "segment": BOUNDED_EXTRACTION_SEGMENT_VERSION,
        "coverage": BOUNDED_EXTRACTION_COVERAGE_VERSION, "subdivision": BOUNDED_EXTRACTION_SUBDIVISION_VERSION,
        "evidence_binding": SOURCE_ANALYSIS_EVIDENCE_BINDING_VERSION,
        "wire": SOURCE_ANALYSIS_WIRE_V3_VERSION, "expander": SOURCE_ANALYSIS_WIRE_V3_EXPANDER_VERSION,
        "segment_policy": BOUNDED_EXTRACTION_POLICY_VERSION, "budget": asdict(SeriesBudget()),
        "piece_hard_cap": FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS, "planner": INITIAL_EXTRACTION_PLANNER_VERSION,
        "provider": "deepseek", "model": "deepseek-flash", "max_output_tokens": SEGMENT_OUTPUT_CEILING,
        "thinking_policy": "structured-json-reasoning-v1", "thinking_mode": "disabled",
        "system_prompt_sha256": hashlib.sha256(BOUNDED_SOURCE_ANALYSIS_SYSTEM.encode()).hexdigest(),
    }


def piece_input(native, source_sha256, processing_run_id, ordinal):
    piece = SourcePiece(**native["source_piece"])
    nodes = native["scoped_node_catalog"]
    context = SourcePieceContext(source_sha256, piece, tuple(n["node_id"] for n in nodes))
    catalog = build_source_evidence_catalog(context)
    series = create_extraction_series(context, catalog, processing_run_id)
    return {"binding_version": BOUNDED_SOURCE_ANALYSIS_BINDING_VERSION,
            "ordinal": ordinal, "native": native, "context": asdict(context),
            "catalog": asdict(catalog), "series_id": series.series_id, "series_sha256": series.series_sha256}


def restore_input(value, source_sha256, processing_run_id, ordinal):
    expected = piece_input(value["native"], source_sha256, processing_run_id, ordinal)
    if json.dumps(value, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("BOUNDED_INPUT_IDENTITY_MISMATCH")
    native = value["native"]
    piece = SourcePiece(**native["source_piece"])
    if (piece.piece_id != native["piece_id"] or piece.source_text != native["source_text"]
            or piece.source_sha256 != native["source_piece_sha256"]
            or hashlib.sha256(native["user_prompt"].encode()).hexdigest() != native["user_prompt_sha256"]):
        raise ValueError("BOUNDED_NATIVE_INPUT_MISMATCH")
    context = SourcePieceContext(source_sha256, piece, tuple(n["node_id"] for n in native["scoped_node_catalog"]))
    catalog = build_source_evidence_catalog(context)
    return context, catalog, create_extraction_series(context, catalog, processing_run_id)


def annotated_source(context, catalog):
    validate_catalog(catalog, context)
    source, parts, cursor = context.piece.source_text, [], 0
    for unit in catalog.units:
        parts.extend((source[cursor:unit.source_start], f"[{unit.evidence_ref}]", unit.exact_text,
                      f"[/{unit.evidence_ref}]"))
        cursor = unit.source_end
    parts.append(source[cursor:])
    return "".join(parts)


def segment_payload(value, context, catalog, series, segment):
    target = {"series_id": series.series_id, "segment_id": segment.segment_id,
              "segment_sha256": segment.segment_sha256, "assigned_evidence_refs": list(segment.assigned_evidence_refs),
              "evidence_universe_sha256": series.evidence_universe_sha256, **binding_contract()}
    user = ("Frozen target:\n" + json.dumps(target, ensure_ascii=False, sort_keys=True) +
            "\nScoped existing Nodes:\n" + json.dumps(value["native"]["scoped_node_catalog"], ensure_ascii=False) +
            "\nComplete annotated SourcePiece:\n" + annotated_source(context, catalog))
    return {"target": target, "request": {"model": "deepseek-flash", "max_tokens": SEGMENT_OUTPUT_CEILING,
            "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"}, "temperature": 0.1,
            "messages": [{"role": "system", "content": BOUNDED_SOURCE_ANALYSIS_SYSTEM},
                         {"role": "user", "content": user}]}}


@dataclass(frozen=True)
class RawSegmentResponse:
    content: bytes
    http_status: int | None
    provider_request_id: str | None = None
    provider_reported_model: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    latency_ms: float | None = None


class BoundedSourceAnalysisSegmentProvider:
    provider_identity = "deepseek"
    adapter_version = BOUNDED_SOURCE_ANALYSIS_PROVIDER_VERSION

    def __init__(self, cfg, *, transport=None):
        self.cfg, self.transport = cfg, transport
        self._validate_configuration()

    def _validate_configuration(self):
        cfg=self.cfg
        url = urlsplit(cfg.base_url)
        if (cfg.provider != "deepseek" or cfg.model != "deepseek-flash" or cfg.max_retries != 0
                or cfg.max_output_tokens != SEGMENT_OUTPUT_CEILING or url.scheme != "https" or url.username or url.password
                or url.query or url.fragment or url.path not in ("", "/", "/v1", "/v1/")):
            raise ValueError("BOUNDED_PROVIDER_CONFIGURATION_MISMATCH")

    def configuration(self):
        self._validate_configuration()
        return {**binding_contract(), "timeout_seconds": self.cfg.timeout_seconds,
                "base_url": self.cfg.base_url, "max_retries": 0, "response_format": {"type": "json_object"},
                "accepted_model_aliases": ["deepseek-flash", "deepseek-v4-flash"]}

    @property
    def available(self):
        return bool(self.cfg.enabled and self.cfg.api_key)

    def invoke(self, payload):
        request = payload["request"]
        expected = binding_contract()
        if (any(payload["target"].get(k) != v for k, v in expected.items())
                or request["model"] != self.cfg.model or request["max_tokens"] != SEGMENT_OUTPUT_CEILING
                or request["thinking"] != {"type": "disabled"} or "reasoning_effort" in request
                or request["response_format"] != {"type": "json_object"}
                or request["messages"][0] != {"role": "system", "content": BOUNDED_SOURCE_ANALYSIS_SYSTEM}):
            raise ValueError("BOUNDED_PROVIDER_REQUEST_MISMATCH")
        if not self.cfg.enabled or not self.cfg.api_key:
            raise ValueError("BOUNDED_PROVIDER_UNAVAILABLE")
        endpoint = self.cfg.base_url.rstrip("/") + "/chat/completions"
        started = time.perf_counter()
        try:
            response = (self.transport or requests.post)(endpoint, json=request,
                headers={"Authorization": "Bearer " + self.cfg.api_key, "Content-Type": "application/json"},
                timeout=self.cfg.timeout_seconds)
        except requests.RequestException:
            return RawSegmentResponse(b"", None, latency_ms=(time.perf_counter()-started)*1000)
        latency = (time.perf_counter()-started)*1000
        status = response.status_code
        request_id = next((safe_request_id(response.headers.get(k)) for k in
                           ("x-request-id", "X-Request-ID", "x-ds-request-id") if safe_request_id(response.headers.get(k))), None)
        if status != 200:
            return RawSegmentResponse(b"", status, request_id, finish_reason="error", latency_ms=latency)
        try:
            # Parse only the HTTP wrapper. Never inspect, hash or measure reasoning_content.
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if type(content) is not str:
                raise ValueError()
            model = safe_identifier(data.get("model"))
            finish = choice.get("finish_reason")
            if finish not in ("stop", "length", "content_filter") or model not in self.configuration()["accepted_model_aliases"]:
                finish = "error"
            usage = data.get("usage") or {}
            def count(value):
                return value if type(value) is int and 0 <= value <= 10_000_000 else None
            output = count(usage.get("completion_tokens"))
            details = usage.get("completion_tokens_details") or {}
            cached = count(usage.get("prompt_cache_hit_tokens")) if "prompt_cache_hit_tokens" in usage else count(
                (usage.get("prompt_tokens_details") or {}).get("cached_tokens"))
            return RawSegmentResponse(content.encode("utf-8"), status, request_id, model, finish,
                count(usage.get("prompt_tokens")), output, count(usage.get("total_tokens")),
                cached, safe_reasoning_tokens(details.get("reasoning_tokens"), output), latency)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            return RawSegmentResponse(b"", status, request_id, finish_reason="error", latency_ms=latency)
