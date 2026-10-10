"""Explicit evidence intent; location proof and non-authoritative review metadata.

V1--V6 records and Evidence Binding v2 remain unchanged. This compiler does not
resolve language, rewrite facts, route claims, or grant semantic authorization.
"""
import copy
import json

from . import output_provider_record_v6 as v6
from . import source_analysis_provider_record as lexical
from .bounded_extraction import _segment_contract
from .evidence_binding import identity, resolve_evidence_binding_v2, validate_catalog

VERSION = 'whole-piece-output-batch-provider-record-v7'
SCHEMA_VERSION = 'whole-piece-output-batch-tool-schema-v7'
ENCODING_VERSION = 'deepseek-evidence-intent-encoding-v1'
INTENT_VERSION = 'evidence-intent-span-v2'
REVIEW_VERSION = 'evidence-intent-research-review-v1'
ENCODING_GUIDANCE = """
通过 emit_source_analysis 提交 v7 ProviderRecord，protocol_version 必须逐字符合工具定义。
保留原研究目标、全部研究字段、类型槽、Claim/Candidate/Relation 引用与人工审核规则。
Evidence 用 {kind,unit_anchor,selection_mode,quote,occurrence} 五个字符串，程序派生真实 Evidence ID 和跨度。
UNIT_SELECTION 必须使用输入中明确的 unit_anchor；WHOLE_UNIT 用 quote=""、occurrence="1"。
RAW_SUBSPAN 逐字引用；NORMALIZED_SUBSPAN 仅用既有 NFKC/Markdown/空白规范化，不改变选择模式。
子串 occurrence 总是显式给出从1开始的精确次数，包括同一 Unit 内重复或重叠位置；不能确定时不得猜测。
EXACT_QUOTE 仅用于完整 SourcePiece 中全局唯一且落在一个 Unit 的逐字子串；unit_anchor=""、RAW_SUBSPAN、occurrence="1"。
Claim、node_match 和 Candidate evidence_properties 的主要 Evidence 必须为 ASSIGNED；CONTEXT 不能替代主要 Evidence。
evidence_acknowledgements 对全部 ASSIGNED 单元各给一条 {anchor_id}；source_reference 给 ownership_anchor。
candidate 不输出归属字段；必须有显式 Claim.related_candidate_names 或有效 evidence_properties 支持，程序验证全部支持。
每条 Claim 的 research_review={context_dependencies:[],review_reasons:[]}，没有依赖也必须填写。
上下文依赖可引用完整 SourcePiece 内验证过的 Evidence Intent，relationship 用 ANAPHORA、TEMPORAL_INHERITANCE、ATTRIBUTION、CONDITION 或 BACKGROUND，reason 明确说明依赖。
问题前提不等于回答承认，指代、时间、数值、否定、条件和归因判断仍须忠于原文；不能确定时声明待审原因，保留限定与不确定性。
上下文仅供解释；不得借此合成跨单元实质子句、替换主要证据、转派、伪造引用或请求重试。
research_review 是非权威审核附件；原文定位成功与依赖声明均不表示事实为真，也不授权 Canonical、Semantic 或 Production 写入。
其他 lexical 值沿用既有规则：布尔 TRUE/FALSE，confidence 十进制字符串，structured_json 合法对象字符串。
"""


class IntentBindingError(ValueError):
    """Safe failure classification; no Source text or partial accepted result."""
    def __init__(self, code, **details):
        super().__init__(code)
        self.details = {'status': 'UNRESOLVED_EVIDENCE', **details}


def selection_schema():
    return lexical.closed({'kind': lexical.enum(('UNIT_SELECTION', 'EXACT_QUOTE')),
        'unit_anchor': {'type': 'string'}, 'selection_mode': lexical.enum(lexical.EVIDENCE_MODES),
        'quote': {'type': 'string'}, 'occurrence': {'type': 'string'}})


def record_schema():
    def replace(schema):
        if schema.get('type') == 'object':
            if set(schema['properties']) == set(lexical.selection_schema()['properties']):
                return selection_schema()
            return lexical.closed({k: replace(v) for k, v in schema['properties'].items()})
        if schema.get('type') == 'array':
            return {'type': 'array', 'items': replace(schema['items'])}
        return copy.deepcopy(schema)
    schema = replace(v6.record_schema())
    schema['properties']['protocol_version'] = lexical.enum((VERSION,))
    schema['required'].append('protocol_version')
    schema['properties']['evidence_acknowledgements']['items'] = lexical.closed({'anchor_id': {'type': 'string'}})
    reference = schema['properties']['source_references']['items']
    reference['properties']['ownership_anchor'] = reference['properties'].pop('ownership_evidence_ref')
    reference['required'] = list(reference['properties'])
    claim = schema['properties']['claims']['items']
    claim['properties']['research_review'] = lexical.closed({
        'context_dependencies': {'type': 'array', 'items': lexical.closed({
            'evidence': selection_schema(), 'relationship': lexical.enum((
                'ANAPHORA', 'TEMPORAL_INHERITANCE', 'ATTRIBUTION', 'CONDITION', 'BACKGROUND')),
            'reason': {'type': 'string'}})},
        'review_reasons': {'type': 'array', 'items': {'type': 'string'}}})
    claim['required'].append('research_review')
    return schema


def unit_anchor(unit):
    return 'EA_' + identity({'version': INTENT_VERSION, 'source': unit.source_sha256,
        'piece': unit.piece_sha256, 'ref': unit.evidence_ref,
        'span': [unit.source_start, unit.source_end]})[:24].upper()


def unit_selection(unit, mode='WHOLE_UNIT', quote='', occurrence='1'):
    return {'kind': 'UNIT_SELECTION', 'unit_anchor': unit_anchor(unit),
            'selection_mode': mode, 'quote': quote, 'occurrence': occurrence}


def resolve_intent(intent, catalog, context, *, evidence_pointer=''):
    """One explicit unit/mode/quote/occurrence maps to the unchanged v2 resolver.

    No candidate match is chosen here. Unit selection preserves the entire legal
    explicit v2 range, including overlapping occurrences and normalized origins.
    EXACT_QUOTE has its own stricter global-uniqueness contract.
    """
    validate_catalog(catalog, context)
    lexical.validate_shape(intent, selection_schema())
    if intent['kind'] == 'UNIT_SELECTION':
        units = [u for u in catalog.units if unit_anchor(u) == intent['unit_anchor']]
        if len(units) != 1:
            raise IntentBindingError('INTENT_UNKNOWN_OR_AMBIGUOUS_ANCHOR')
        unit = units[0]
    else:
        if intent['unit_anchor'] != '' or intent['selection_mode'] != 'RAW_SUBSPAN' or intent['occurrence'] != '1':
            raise IntentBindingError('INVALID_EXACT_QUOTE_INTENT')
        quote = intent['quote']
        text = context.piece.source_text
        if not quote:
            raise IntentBindingError('INTENT_EMPTY_QUOTE')
        start = text.find(quote)
        if start < 0:
            raise IntentBindingError('INTENT_QUOTE_NOT_FOUND')
        if text.find(quote, start + 1) >= 0:
            raise IntentBindingError('INTENT_QUOTE_AMBIGUOUS')
        units = [u for u in catalog.units if u.source_start <= start and start + len(quote) <= u.source_end]
        if len(units) != 1:
            raise IntentBindingError('INTENT_QUOTE_NOT_IN_SINGLE_UNIT')
        unit = units[0]
    selection = {'evidence_ref': unit.evidence_ref, 'selection_mode': intent['selection_mode'],
                 'selector': intent['quote'], 'occurrence': intent['occurrence']}
    selected = lexical.selection(selection)  # Explicit positive occurrence; no default or mode fallback.
    binding = resolve_evidence_binding_v2({**selected, 'evidence_pointer': evidence_pointer}, catalog, context)
    return selection, binding


def source_regions(catalog, context, segment):
    validate_catalog(catalog, context)
    owned = set(segment.assigned_evidence_refs)
    if not owned <= {u.evidence_ref for u in catalog.units}:
        raise IntentBindingError('INTENT_ASSIGNED_CATALOG_MISMATCH')
    regions, cursor = [], 0
    for unit in catalog.units:
        if cursor < unit.source_start:
            regions.append({'role': 'CONTEXT', 'text': context.piece.source_text[cursor:unit.source_start]})
        regions.append({'role': 'ASSIGNED' if unit.evidence_ref in owned else 'CONTEXT',
            'anchor_id': unit_anchor(unit), 'evidence_ref': unit.evidence_ref, 'locator': unit.locator,
            'source_span': [unit.source_start, unit.source_end], 'text': unit.exact_text})
        cursor = unit.source_end
    if cursor < len(context.piece.source_text):
        regions.append({'role': 'CONTEXT', 'text': context.piece.source_text[cursor:]})
    return regions


def compile_result(content, series, segment, catalog, context, *, plan=None):
    _segment_contract(series, segment)
    if plan is not None:
        from .bounded_extraction import series_coverage
        series_coverage(series, plan, (), catalog, context)
        if segment not in plan.leaves:
            raise IntentBindingError('INTENT_SEGMENT_NOT_ACTIVE_LEAF')
    record = lexical.parse_object(content)
    for family in ('claims', 'node_candidates'):
        if type(record.get(family)) is list and len(record[family]) > 100:
            raise ValueError('PROVIDER_RECORD_ARRAY_LIMIT')
    lexical.validate_shape(record, record_schema())
    owned = set(segment.assigned_evidence_refs)
    bindings, reviews = [], []

    def resolve(intent, path, *, primary=True, pointer=''):
        try:
            selection, bound = resolve_intent(intent, catalog, context, evidence_pointer=pointer)
        except ValueError as error:
            raise IntentBindingError(str(error), path=path) from None
        if primary and bound.evidence_ref not in owned:
            raise IntentBindingError('INTENT_SUPPORT_OUTSIDE_ASSIGNED_SEGMENT', path=path,
                evidence_ref=bound.evidence_ref, source_span=[bound.source_start, bound.source_end], scheduled=False)
        proof = {'path': path, 'intent': copy.deepcopy(intent), 'selection': selection,
                 'binding': copy.deepcopy(bound.__dict__), 'role': 'PRIMARY' if primary else 'CONTEXT'}
        bindings.append(proof)
        return selection, proof

    compiled = copy.deepcopy(record)
    del compiled['protocol_version']
    for family in ('claims', 'node_matches'):
        for index, obj in enumerate(compiled[family]):
            obj['evidence'], proof = resolve(obj['evidence'], [family, index, 'evidence'], pointer=obj.get('evidence_pointer', ''))
            if family == 'claims':
                review = obj.pop('research_review')
                contexts = []
                for ci, dependency in enumerate(review['context_dependencies']):
                    _, bound = resolve(dependency['evidence'], ['claims', index, 'research_review', 'context_dependencies', ci], primary=False)
                    contexts.append({**copy.deepcopy(dependency), 'location': bound,
                        'relationship_authorization': 'NOT_ESTABLISHED'})
                reviews.append({'claim_ref': f'C{index + 1}', 'primary_binding_sha256': proof['binding']['binding_sha256'],
                    'statuses': ['LOCATION_VERIFIED', *(['CONTEXT_DEPENDENCY_DECLARED'] if contexts else []), 'SEMANTIC_REVIEW_REQUIRED'],
                    'context_dependencies': contexts, 'review_reasons': review['review_reasons'],
                    'semantic_truth': 'NOT_ESTABLISHED'})
    for index, candidate in enumerate(compiled['node_candidates']):
        for ei, entry in enumerate(candidate['evidence_properties']):
            entry['value'], _ = resolve(entry['value'], ['node_candidates', index, 'evidence_properties', ei, 'value'])
    anchors = {unit_anchor(u): u for u in catalog.units}
    for index, ack in enumerate(compiled['evidence_acknowledgements']):
        unit = anchors.get(ack['anchor_id'])
        if unit is None:
            raise IntentBindingError('INTENT_UNKNOWN_OR_AMBIGUOUS_ANCHOR')
        selection, _ = resolve(unit_selection(unit), ['evidence_acknowledgements', index])
        compiled['evidence_acknowledgements'][index] = {'evidence_ref': selection['evidence_ref']}
    for index, reference in enumerate(compiled['source_references']):
        unit = anchors.get(reference.pop('ownership_anchor'))
        if unit is None:
            raise IntentBindingError('INTENT_UNKNOWN_OR_AMBIGUOUS_ANCHOR')
        selection, _ = resolve(unit_selection(unit), ['source_references', index])
        reference['ownership_evidence_ref'] = selection['evidence_ref']
    result, ownership = v6.compile_result(json.dumps(compiled, ensure_ascii=False), series, segment, catalog, context)
    return result, {'version': REVIEW_VERSION, 'protocol_version': VERSION,
        'schema_sha256': identity(record_schema()), 'provider_record_sha256': identity(record),
        'compiled_record_sha256': identity(compiled), 'series_sha256': series.series_sha256,
        'series_id': series.series_id,
        'segment_sha256': segment.segment_sha256, 'result_sha256': result.result_sha256,
        'authority': 'NON_AUTHORITATIVE_RESEARCH_REVIEW', 'semantic_authorization': 'NOT_ESTABLISHED',
        'canonical_permission': False, 'claims': reviews, 'bindings': bindings, 'candidate_ownership': ownership,
        'review_required_paths': [[family, i] for family in ('node_matches', 'node_candidates', 'relation_candidates')
                                  for i in range(len(record[family]))]}
