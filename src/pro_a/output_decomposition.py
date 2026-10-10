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
from . import output_provider_record_v4 as variant
from . import output_provider_record_v5 as intent
from . import output_provider_record_v6 as ownership
from .bounded_extraction import (OUTPUT_SERIES_VERSION, OUTPUT_BATCH_VERSION, OUTPUT_COVERAGE_VERSION,
    LEGACY_OUTPUT_SERIES_VERSION, LEGACY_OUTPUT_BATCH_VERSION, OUTPUT_SERIES_VERSIONS,
    V2_OUTPUT_SERIES_VERSION, V2_OUTPUT_BATCH_VERSION,
    INTENT_OUTPUT_SERIES_VERSION, INTENT_OUTPUT_BATCH_VERSION,
    OWNERSHIP_OUTPUT_SERIES_VERSION, OWNERSHIP_OUTPUT_BATCH_VERSION,
    OUTPUT_SUBDIVISION_VERSION, OUTPUT_POLICY_VERSION, SeriesBudget,
    create_extraction_series, _segment_contract)
from .evidence_binding import identity, validate_catalog
from .output_capacity import SEGMENT_OUTPUT_CEILING, LEGACY_SEGMENT_OUTPUT_CEILING, OPERATION_OUTPUT_BUDGET_POLICY_VERSION

LEGACY_BINDING_VERSION = 'whole-piece-output-decomposition-binding-v1'
LEGACY_PROVIDER_VERSION = 'whole-piece-output-batch-lexical-tool-provider-v3'
V3_BINDING_VERSION = 'whole-piece-output-decomposition-binding-v2'
V3_PROVIDER_VERSION = 'whole-piece-output-batch-lexical-tool-provider-v4'
V3_RECORD_VERSION = 'whole-piece-output-batch-provider-record-v3'
BINDING_VERSION = 'whole-piece-output-decomposition-binding-v3'
INTENT_BINDING_VERSION = 'whole-piece-output-decomposition-binding-v4'
OWNERSHIP_BINDING_VERSION = 'whole-piece-output-decomposition-binding-v5'
PROVIDER_VERSION = 'whole-piece-output-batch-lexical-tool-provider-v5'
PROMPT_VERSION = 'whole-piece-output-batch-lexical-tool-prompt-v4'
RESPONSE_VERSION = 'whole-piece-output-batch-response-v4'
RECORD_VERSION = variant.VERSION
SCHEMA_VERSION = variant.SCHEMA_VERSION
ENCODING_VERSION = variant.ENCODING_VERSION
CLAIM_LINKAGE_VERSION = 'whole-piece-output-claim-linkage-v2'
OPERATION = 'WHOLE_PIECE_OUTPUT_BATCH'
MODE = 'WHOLE_PIECE_OUTPUT_DECOMPOSITION'
# The existing lexical workaround is encoding, not the normalized research IR.
V3_ENCODING_SYSTEM = whole.SYSTEM[len(whole.SOURCE_ANALYSIS_SYSTEM):]
V3_SYSTEM = normalized.SEMANTIC_SYSTEM + V3_ENCODING_SYSTEM
ENCODING_SYSTEM = (V3_ENCODING_SYSTEM[:V3_ENCODING_SYSTEM.index('\ncandidate 按')]
    + variant.ENCODING_GUIDANCE + V3_ENCODING_SYSTEM[V3_ENCODING_SYSTEM.index('\nrelation supporting_claim_refs'):])
SYSTEM = normalized.SEMANTIC_SYSTEM + ENCODING_SYSTEM
INTENT_ENCODING_SYSTEM = (V3_ENCODING_SYSTEM[:V3_ENCODING_SYSTEM.index('\ncandidate 按')]
    + intent.nodes.ENCODING_GUIDANCE + V3_ENCODING_SYSTEM[V3_ENCODING_SYSTEM.index('\nrelation supporting_claim_refs'):])
INTENT_SYSTEM = normalized.SEMANTIC_SYSTEM + INTENT_ENCODING_SYSTEM
OWNERSHIP_ENCODING_SYSTEM = INTENT_ENCODING_SYSTEM.replace(intent.nodes.ENCODING_GUIDANCE, ownership.ENCODING_GUIDANCE)
OWNERSHIP_SYSTEM = (normalized.SEMANTIC_SYSTEM.replace(
    'candidate/source_reference 的 ownership_evidence_ref', 'source_reference 的 ownership_evidence_ref')
    + OWNERSHIP_ENCODING_SYSTEM)


def _system(record_version):
    return {RECORD_VERSION: SYSTEM, V3_RECORD_VERSION: V3_SYSTEM, intent.VERSION: INTENT_SYSTEM,
            ownership.VERSION: OWNERSHIP_SYSTEM}[record_version]


def record_schema(*, record_version=RECORD_VERSION):
    if record_version == ownership.VERSION:
        return ownership.record_schema()
    if record_version == intent.VERSION:
        return intent.record_schema()
    if record_version == RECORD_VERSION:
        return variant.record_schema()
    if record_version != V3_RECORD_VERSION:
        raise ValueError('UNSUPPORTED_PROVIDER_RECORD_VERSION')
    schema = lexical.record_schema()
    for family in ('node_candidates', 'source_references'):
        item = schema['properties'][family]['items']
        item['properties']['ownership_evidence_ref'] = {'type': 'string'}
        item['required'].append('ownership_evidence_ref')
    schema['properties']['evidence_acknowledgements'] = {'type': 'array', 'items': lexical.closed({
        'evidence_ref': {'type': 'string'}})}
    schema['required'].append('evidence_acknowledgements')
    return schema


def contract(*, binding_version=BINDING_VERSION):
    if binding_version == OWNERSHIP_BINDING_VERSION:
        schema = ownership.record_schema()
        provider = 'whole-piece-output-batch-lexical-tool-provider-v7'
        return {**contract(binding_version=INTENT_BINDING_VERSION), 'binding_version': binding_version,
            'adapter_version': provider, 'provider_version': provider,
            'prompt_version': 'whole-piece-output-batch-lexical-tool-prompt-v6',
            'response_version': 'whole-piece-output-batch-response-v6', 'provider_record_version': ownership.VERSION,
            'tool_schema_version': ownership.SCHEMA_VERSION, 'tool_parameters': schema, 'tool_schema_sha256': identity(schema),
            'system_prompt_sha256': hashlib.sha256(OWNERSHIP_SYSTEM.encode()).hexdigest(),
            'provider_encoding_contract_version': ownership.ENCODING_VERSION,
            'provider_encoding_prompt_sha256': hashlib.sha256(OWNERSHIP_ENCODING_SYSTEM.encode()).hexdigest(),
            'candidate_ownership_version': ownership.OWNERSHIP_VERSION,
            'series': OWNERSHIP_OUTPUT_SERIES_VERSION, 'batch': OWNERSHIP_OUTPUT_BATCH_VERSION}
    if binding_version == INTENT_BINDING_VERSION:
        schema = intent.record_schema()
        provider = 'whole-piece-output-batch-lexical-tool-provider-v6'
        return {**contract(), 'binding_version': binding_version, 'adapter_version': provider,
            'provider_version': provider, 'prompt_version': 'whole-piece-output-batch-lexical-tool-prompt-v5',
            'response_version': 'whole-piece-output-batch-response-v5', 'provider_record_version': intent.VERSION,
            'tool_schema_version': intent.SCHEMA_VERSION, 'tool_parameters': schema, 'tool_schema_sha256': identity(schema),
            'system_prompt_sha256': hashlib.sha256(INTENT_SYSTEM.encode()).hexdigest(),
            'provider_encoding_contract_version': intent.ENCODING_VERSION,
            'provider_encoding_prompt_sha256': hashlib.sha256(INTENT_ENCODING_SYSTEM.encode()).hexdigest(),
            'node_candidate_intent_version': intent.nodes.VERSION,
            'series': INTENT_OUTPUT_SERIES_VERSION, 'batch': INTENT_OUTPUT_BATCH_VERSION}
    if binding_version not in (LEGACY_BINDING_VERSION, V3_BINDING_VERSION, BINDING_VERSION):
        raise ValueError('UNSUPPORTED_OUTPUT_CAPACITY_CONTRACT')
    historical_capacity = binding_version == LEGACY_BINDING_VERSION
    v4 = binding_version == BINDING_VERSION
    provider_version = LEGACY_PROVIDER_VERSION if historical_capacity else PROVIDER_VERSION if v4 else V3_PROVIDER_VERSION
    record_version = RECORD_VERSION if v4 else V3_RECORD_VERSION
    schema = record_schema(record_version=record_version)
    system, encoding = (SYSTEM, ENCODING_SYSTEM) if v4 else (V3_SYSTEM, V3_ENCODING_SYSTEM)
    return {**whole.contract(), 'binding_version': binding_version, 'adapter_version': provider_version,
        'provider_version': provider_version, 'prompt_version': PROMPT_VERSION if v4 else 'whole-piece-output-batch-lexical-tool-prompt-v3',
        'response_version': RESPONSE_VERSION if v4 else 'whole-piece-output-batch-response-v3',
        'provider_record_version': record_version, 'tool_schema_version': SCHEMA_VERSION if v4 else 'whole-piece-output-batch-tool-schema-v3',
        'tool_parameters': schema, 'tool_schema_sha256': identity(schema),
        'system_prompt_sha256': hashlib.sha256(system.encode()).hexdigest(),
        'series': LEGACY_OUTPUT_SERIES_VERSION if historical_capacity else OUTPUT_SERIES_VERSION if v4 else V2_OUTPUT_SERIES_VERSION,
        'batch': LEGACY_OUTPUT_BATCH_VERSION if historical_capacity else OUTPUT_BATCH_VERSION if v4 else V2_OUTPUT_BATCH_VERSION, 'coverage': OUTPUT_COVERAGE_VERSION,
        **({} if historical_capacity else {'output_budget_identity': OPERATION_OUTPUT_BUDGET_POLICY_VERSION}),
        'subdivision': OUTPUT_SUBDIVISION_VERSION, 'ownership_policy': OUTPUT_POLICY_VERSION,
        'claim_linkage_policy': CLAIM_LINKAGE_VERSION, 'research_semantic_contract': normalized.contract(),
        'normalized_analysis_record_version': normalized.VERSION,
        'provider_encoding_contract_version': ENCODING_VERSION if v4 else 'deepseek-output-batch-lexical-encoding-v3',
        'provider_encoding_prompt_sha256': hashlib.sha256(encoding.encode()).hexdigest(),
        'budget': asdict(SeriesBudget()),
        'max_output_tokens': LEGACY_SEGMENT_OUTPUT_CEILING if historical_capacity else SEGMENT_OUTPUT_CEILING,
        'semantic_context': 'COMPLETE_SOURCEPIECE',
        'evidence_segment_semantic_boundary': 'deprecated', 'output_ownership': 'EVIDENCE_BATCHED',
        'piece_hard_cap': historical.FROZEN_ACCEPTANCE_INITIAL_MAX_CHARS,
        'planner': historical.INITIAL_EXTRACTION_PLANNER_VERSION}


def binding_for_series(series_version):
    return {LEGACY_OUTPUT_SERIES_VERSION: LEGACY_BINDING_VERSION,
            OWNERSHIP_OUTPUT_SERIES_VERSION: OWNERSHIP_BINDING_VERSION,
            INTENT_OUTPUT_SERIES_VERSION: INTENT_BINDING_VERSION,
            V2_OUTPUT_SERIES_VERSION: V3_BINDING_VERSION, OUTPUT_SERIES_VERSION: BINDING_VERSION}[series_version]


def record_version_for_series(series_version):
    if binding_for_series(series_version) == OWNERSHIP_BINDING_VERSION:
        return ownership.VERSION
    if binding_for_series(series_version) == INTENT_BINDING_VERSION:
        return intent.VERSION
    return RECORD_VERSION if binding_for_series(series_version) == BINDING_VERSION else V3_RECORD_VERSION


def piece_input(native, source_sha256, processing_run_id, ordinal, *, binding_version=BINDING_VERSION):
    # Reuse historical immutable native-input validation without reusing its identity.
    old = historical.piece_input(native, source_sha256, processing_run_id, ordinal)
    context, catalog, _ = historical.restore_input(old, source_sha256, processing_run_id, ordinal)
    series_version = contract(binding_version=binding_version)['series']
    series = create_extraction_series(context, catalog, processing_run_id, series_version=series_version)
    return {**old, 'binding_version': binding_version, 'series_id': series.series_id,
            'series_sha256': series.series_sha256}


def restore_input(value, source_sha256, processing_run_id, ordinal):
    binding_version = value['binding_version']
    expected = piece_input(value['native'], source_sha256, processing_run_id, ordinal, binding_version=binding_version)
    if identity(value) != identity(expected):
        raise ValueError('OUTPUT_INPUT_IDENTITY_MISMATCH')
    native = value['native']
    context, catalog = whole.piece_context({**native, 'source_sha256': source_sha256})
    return context, catalog, create_extraction_series(context, catalog, processing_run_id,
        series_version=contract(binding_version=binding_version)['series'])


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
    if series.series_version not in OUTPUT_SERIES_VERSIONS:
        raise ValueError('OUTPUT_SERIES_REQUIRED')
    _segment_contract(series, segment)
    selected = contract(binding_version=binding_for_series(series.series_version))
    target = {'series_id': series.series_id, 'segment_id': segment.segment_id,
        'segment_sha256': segment.segment_sha256, 'assigned_evidence_refs': list(segment.assigned_evidence_refs),
        **{k:v for k,v in selected.items() if k != 'tool_parameters'}}
    user = ('Frozen target:\n' + json.dumps(target, sort_keys=True) + '\nScoped existing Nodes:\n'
        + json.dumps(value['native']['scoped_node_catalog'], ensure_ascii=False)
        + '\nComplete annotated SourcePiece:\n' + annotated_source(context, catalog, segment.assigned_evidence_refs))
    request = {'model':'deepseek-flash', 'max_tokens':segment.max_output_tokens, 'thinking':{'type':'disabled'},
        'stream':False, 'temperature':0.1,
        'tools':[{'type':'function','function':{'name':lexical.TOOL_NAME,'strict':True,
            'description':'读取完整SourcePiece，仅提交本批次归属单元的分析记录。','parameters':selected['tool_parameters']}}],
        'tool_choice':{'type':'function','function':{'name':lexical.TOOL_NAME}},
        'messages':[{'role':'system','content':_system(selected['provider_record_version'])},{'role':'user','content':user}]}
    return {'target':target, 'request':request}


def normalize_record(content, *, record_version=RECORD_VERSION):
    """DeepSeek lexical adapter -> provider-neutral native types, before binding."""
    if record_version == ownership.VERSION:
        raise ValueError('OWNERSHIP_CONTEXT_REQUIRED')
    if record_version == intent.VERSION:
        return intent.normalize_record(content)
    if record_version == RECORD_VERSION:
        return variant.normalize_record(content)
    record = lexical.parse_object(content)
    lexical.validate_shape(record, record_schema(record_version=record_version))
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


def record_to_result(content, series, segment, catalog, context, *, record_version=None):
    # Selection is frozen by Attempt identity, never inferred from response shape.
    if record_version is None:
        record_version = record_version_for_series(series.series_version)
    if series.series_version in (INTENT_OUTPUT_SERIES_VERSION, OWNERSHIP_OUTPUT_SERIES_VERSION) and record_version != record_version_for_series(series.series_version):
        raise ValueError('PROVIDER_RECORD_SERIES_VERSION_MISMATCH')
    if record_version == ownership.VERSION:
        if series.series_version != OWNERSHIP_OUTPUT_SERIES_VERSION:
            raise ValueError('PROVIDER_RECORD_SERIES_VERSION_MISMATCH')
        return ownership.compile_result(content, series, segment, catalog, context)[0]
    if record_version in (legacy.V1, legacy.RECORD_VERSION):
        return legacy.record_to_result(content, series, segment, catalog, context, record_version=record_version)
    if record_version not in (V3_RECORD_VERSION, RECORD_VERSION, intent.VERSION):
        raise ValueError('UNSUPPORTED_PROVIDER_RECORD_VERSION')
    if record_version != record_version_for_series(series.series_version):
        raise ValueError('PROVIDER_RECORD_SERIES_VERSION_MISMATCH')
    return normalized.record_to_result(normalize_record(content, record_version=record_version), series, segment, catalog, context)


class OutputBatchProvider(whole.WholePieceCompactProvider):
    adapter_version = PROVIDER_VERSION
    max_output_tokens = SEGMENT_OUTPUT_CEILING

    def __init__(self, cfg, *, transport=None, binding_version=BINDING_VERSION):
        self.binding_version = binding_version
        selected = contract(binding_version=binding_version)
        self.adapter_version = selected['provider_version']
        self.max_output_tokens = selected['max_output_tokens']
        super().__init__(cfg, transport=transport)

    @property
    def available(self):
        return bool(self.cfg.enabled and self.cfg.api_key)

    def configuration(self):
        return {'contract':contract(binding_version=self.binding_version), 'timeout_seconds':self.cfg.timeout_seconds,
                'base_url':whole.BETA_ENDPOINT, 'automatic_retry':False,
                'qualified_output_capability_tokens':self.output_capability_tokens}

    def invoke(self, payload):
        from .cloud_contract import ProviderFailure
        body, target = payload['request'], payload['target']
        selected = contract(binding_version=self.binding_version)
        if (not self.available or any(identity(target.get(k)) != identity(v) for k,v in selected.items() if k != 'tool_parameters')
                or identity(body.get('tools')) != identity([{'type':'function','function':{'name':lexical.TOOL_NAME,
                    'strict':True,'description':'读取完整SourcePiece，仅提交本批次归属单元的分析记录。','parameters':selected['tool_parameters']}}])
                or body.get('model') != 'deepseek-flash' or body.get('max_tokens') != selected['max_output_tokens']
                or body.get('thinking') != {'type':'disabled'} or body.get('stream') is not False
                or body.get('tool_choice') != {'type':'function','function':{'name':lexical.TOOL_NAME}}
                or body['messages'][0] != {'role':'system','content':_system(selected['provider_record_version'])}):
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
