"""Full SourcePiece semantics with bounded, locally enforced output ownership."""
import copy
from dataclasses import asdict
import hashlib
import json

from . import bounded_source_analysis as historical
from . import source_analysis_provider_record as lexical
from . import whole_piece_compact as whole
from . import extraction_analysis_record as normalized
from . import output_decomposition_legacy as legacy
from .bounded_extraction import (OUTPUT_SERIES_VERSION, OUTPUT_BATCH_VERSION, OUTPUT_COVERAGE_VERSION,
    OUTPUT_SUBDIVISION_VERSION, OUTPUT_POLICY_VERSION, SeriesBudget,
    create_extraction_series, _segment_contract)
from .evidence_binding import identity, validate_catalog

BINDING_VERSION = 'whole-piece-output-decomposition-binding-v1'
PROVIDER_VERSION = 'whole-piece-output-batch-lexical-tool-provider-v3'
PROMPT_VERSION = 'whole-piece-output-batch-lexical-tool-prompt-v3'
RESPONSE_VERSION = 'whole-piece-output-batch-response-v3'
RECORD_VERSION = 'whole-piece-output-batch-provider-record-v3'
SCHEMA_VERSION = 'whole-piece-output-batch-tool-schema-v3'
ENCODING_VERSION = 'deepseek-output-batch-lexical-encoding-v3'
CLAIM_LINKAGE_VERSION = 'whole-piece-output-claim-linkage-v2'
OPERATION = 'WHOLE_PIECE_OUTPUT_BATCH'
MODE = 'WHOLE_PIECE_OUTPUT_DECOMPOSITION'
# The existing lexical workaround is encoding, not the normalized research IR.
ENCODING_SYSTEM = whole.SYSTEM[len(whole.SOURCE_ANALYSIS_SYSTEM):]
SYSTEM = normalized.SEMANTIC_SYSTEM + ENCODING_SYSTEM


def record_schema():
    schema = lexical.record_schema()
    for family in ('node_candidates', 'source_references'):
        item = schema['properties'][family]['items']
        item['properties']['ownership_evidence_ref'] = {'type': 'string'}
        item['required'].append('ownership_evidence_ref')
    schema['properties']['evidence_acknowledgements'] = {'type': 'array', 'items': lexical.closed({
        'evidence_ref': {'type': 'string'}})}
    schema['required'].append('evidence_acknowledgements')
    return schema


def contract():
    return {**whole.contract(), 'binding_version': BINDING_VERSION, 'adapter_version': PROVIDER_VERSION,
        'provider_version': PROVIDER_VERSION, 'prompt_version': PROMPT_VERSION, 'response_version': RESPONSE_VERSION,
        'provider_record_version': RECORD_VERSION, 'tool_schema_version': SCHEMA_VERSION,
        'tool_parameters': record_schema(), 'tool_schema_sha256': identity(record_schema()),
        'system_prompt_sha256': hashlib.sha256(SYSTEM.encode()).hexdigest(),
        'series': OUTPUT_SERIES_VERSION, 'batch': OUTPUT_BATCH_VERSION, 'coverage': OUTPUT_COVERAGE_VERSION,
        'subdivision': OUTPUT_SUBDIVISION_VERSION, 'ownership_policy': OUTPUT_POLICY_VERSION,
        'claim_linkage_policy': CLAIM_LINKAGE_VERSION, 'research_semantic_contract': normalized.contract(),
        'normalized_analysis_record_version': normalized.VERSION,
        'provider_encoding_contract_version': ENCODING_VERSION,
        'provider_encoding_prompt_sha256': hashlib.sha256(ENCODING_SYSTEM.encode()).hexdigest(),
        'budget': asdict(SeriesBudget()), 'semantic_context': 'COMPLETE_SOURCEPIECE',
        'evidence_segment_semantic_boundary': 'deprecated', 'output_ownership': 'EVIDENCE_BATCHED',
        'piece_hard_cap': historical.FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS,
        'planner': historical.INITIAL_EXTRACTION_PLANNER_VERSION}


def piece_input(native, source_sha256, processing_run_id, ordinal):
    # Reuse historical immutable native-input validation without reusing its identity.
    old = historical.piece_input(native, source_sha256, processing_run_id, ordinal)
    context, catalog, _ = historical.restore_input(old, source_sha256, processing_run_id, ordinal)
    series = create_extraction_series(context, catalog, processing_run_id, series_version=OUTPUT_SERIES_VERSION)
    return {**old, 'binding_version': BINDING_VERSION, 'series_id': series.series_id,
            'series_sha256': series.series_sha256}


def restore_input(value, source_sha256, processing_run_id, ordinal):
    expected = piece_input(value['native'], source_sha256, processing_run_id, ordinal)
    if identity(value) != identity(expected):
        raise ValueError('OUTPUT_INPUT_IDENTITY_MISMATCH')
    native = value['native']
    context, catalog = whole.piece_context({**native, 'source_sha256': source_sha256})
    return context, catalog, create_extraction_series(context, catalog, processing_run_id, series_version=OUTPUT_SERIES_VERSION)


def annotated_source(context, catalog, assigned):
    validate_catalog(catalog, context)
    if not assigned or len(set(assigned)) != len(assigned) or not set(assigned) <= {u.evidence_ref for u in catalog.units}:
        raise ValueError('INVALID_OUTPUT_OWNERSHIP')
    source, parts, cursor = context.piece.source_text, [], 0
    for unit in catalog.units:
        if unit.evidence_ref in assigned:
            parts.extend((source[cursor:unit.source_start], '[' + unit.evidence_ref + ']',
                          unit.exact_text, '[/' + unit.evidence_ref + ']'))
            cursor = unit.source_end
    parts.append(source[cursor:])
    return ''.join(parts)


def segment_payload(value, context, catalog, series, segment):
    if series.series_version != OUTPUT_SERIES_VERSION:
        raise ValueError('OUTPUT_SERIES_REQUIRED')
    _segment_contract(series, segment)
    target = {'series_id': series.series_id, 'segment_id': segment.segment_id,
        'segment_sha256': segment.segment_sha256, 'assigned_evidence_refs': list(segment.assigned_evidence_refs),
        **{k:v for k,v in contract().items() if k != 'tool_parameters'}}
    user = ('Frozen target:\n' + json.dumps(target, sort_keys=True) + '\nScoped existing Nodes:\n'
        + json.dumps(value['native']['scoped_node_catalog'], ensure_ascii=False)
        + '\nComplete annotated SourcePiece:\n' + annotated_source(context, catalog, segment.assigned_evidence_refs))
    request = {'model':'deepseek-flash', 'max_tokens':12000, 'thinking':{'type':'disabled'},
        'stream':False, 'temperature':0.1,
        'tools':[{'type':'function','function':{'name':lexical.TOOL_NAME,'strict':True,
            'description':'读取完整SourcePiece，仅提交本批次归属单元的分析记录。','parameters':record_schema()}}],
        'tool_choice':{'type':'function','function':{'name':lexical.TOOL_NAME}},
        'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':user}]}
    return {'target':target, 'request':request}


def normalize_record(content):
    """DeepSeek lexical adapter -> provider-neutral native types, before binding."""
    record = lexical.parse_object(content)
    lexical.validate_shape(record, record_schema())
    stripped = copy.deepcopy(record)
    acknowledgements = stripped.pop('evidence_acknowledgements')
    anchors = {}
    for family in ('node_candidates','source_references'):
        anchors[family] = [obj.pop('ownership_evidence_ref') for obj in stripped[family]]
    wire = lexical.provider_record_to_wire_v3(stripped)
    wire.pop('wire_version')
    for family, refs in anchors.items():
        for obj, ref in zip(wire[family], refs):obj['ownership_evidence_ref'] = ref
    return {**wire, 'analysis_record_version': normalized.VERSION, 'evidence_acknowledgements': acknowledgements}


def record_to_result(content, series, segment, catalog, context, *, record_version=RECORD_VERSION):
    # Selection is frozen by Attempt identity, never inferred from response shape.
    if record_version in (legacy.V1, legacy.RECORD_VERSION):
        return legacy.record_to_result(content, series, segment, catalog, context, record_version=record_version)
    if record_version != RECORD_VERSION:
        raise ValueError('UNSUPPORTED_PROVIDER_RECORD_VERSION')
    return normalized.record_to_result(normalize_record(content), series, segment, catalog, context)


class OutputBatchProvider(whole.WholePieceCompactProvider):
    adapter_version = PROVIDER_VERSION

    @property
    def available(self):
        return bool(self.cfg.enabled and self.cfg.api_key)

    def configuration(self):
        return {'contract':contract(), 'timeout_seconds':self.cfg.timeout_seconds,
                'base_url':whole.BETA_ENDPOINT, 'automatic_retry':False}

    def invoke(self, payload):
        from .cloud_contract import ProviderFailure
        body, target = payload['request'], payload['target']
        if (not self.available or any(identity(target.get(k)) != identity(v) for k,v in contract().items() if k != 'tool_parameters')
                or identity(body.get('tools')) != identity([{'type':'function','function':{'name':lexical.TOOL_NAME,
                    'strict':True,'description':'读取完整SourcePiece，仅提交本批次归属单元的分析记录。','parameters':record_schema()}}])
                or body.get('model') != 'deepseek-flash' or body.get('max_tokens') != 12000
                or body.get('thinking') != {'type':'disabled'} or body.get('stream') is not False
                or body.get('tool_choice') != {'type':'function','function':{'name':lexical.TOOL_NAME}}
                or body['messages'][0] != {'role':'system','content':SYSTEM}):
            raise ValueError('OUTPUT_PROVIDER_CONFIGURATION_MISMATCH')
        try:
            result = self._send(body, OPERATION, 1)
        except ProviderFailure as error:
            unknown = error.external_outcome == 'UNKNOWN'
            status = None if unknown else error.diagnostic.get('http_status') or 200
            return historical.RawSegmentResponse(b'', status, finish_reason=None if unknown else 'error')
        return historical.RawSegmentResponse(result.output.encode('utf-8'), 200,
            provider_request_id=result.provider_request_id, provider_reported_model=result.provider_reported_model,
            finish_reason=result.finish_reason if result.finish_reason in ('tool_calls','stop','length','content_filter') else 'error',
            input_tokens=result.input_tokens, output_tokens=result.output_tokens, total_tokens=result.total_tokens,
            cached_input_tokens=result.cached_tokens, reasoning_tokens=result.reasoning_tokens, latency_ms=result.latency_ms)
