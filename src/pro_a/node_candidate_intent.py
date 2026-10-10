"""Pure, lossless Node intent compilation; no Evidence or Canonical authority."""
import copy

from . import source_analysis_provider_record as lexical
from .source_analysis_wire import _NODE_VARIANTS, _TYPE_FIELDS, _BOOL_FIELDS

VERSION = 'node-candidate-intent-v1'
PROPERTY_FIELDS = {
    'boolean_properties': _BOOL_FIELDS,
    'text_properties': _TYPE_FIELDS - _BOOL_FIELDS - {'evidence_ref'},
    'evidence_properties': {'evidence_ref'},
}
ENCODING_GUIDANCE = """
node_candidates 使用 node-candidate-intent-v1，保持候选及引用的原始顺序。
模型判断 primary_type、公共研究属性及显式语义属性，不输出 active/preserved 物理槽位。
boolean_properties、text_properties、evidence_properties 均为 {field,value} 数组；无显式属性时为空数组。
boolean_properties 的 value 使用 TRUE/FALSE 字符串；evidence_properties 的 value 使用现有 Evidence Selection，禁止 NONE。
Event 必须明确提供 is_discrete_event、event_time、evidence_ref；Theme 必须明确提供 long_term_research_value、cross_source_or_node_value；
ResearchQuestion 必须明确提供 question、importance、what_would_change_my_mind。其他类型没有必需的类型专属属性。
已知的跨类型属性仍按其语义字段显式提供，程序根据 primary_type 无损派生 active 与 preserved_fields。
显式 FALSE 和空文本也是数据，不得因等于默认值而省略；不得重复属性、虚构属性或补猜缺失的研究判断。
每个 candidate 必须明确提供本批次 ownership_evidence_ref；程序不会推断归属或生成 Evidence。
related_candidate_names 必须精确引用本响应实际输出的 candidate。
"""


def candidate_schema():
    original = lexical.record_schema()['properties']['node_candidates']['items']['properties']
    common = {k: copy.deepcopy(v) for k, v in original.items()
              if k not in _TYPE_FIELDS | {'event_evidence', 'preserved_fields'}}
    common['ownership_evidence_ref'] = {'type': 'string'}
    for array, fields in PROPERTY_FIELDS.items():
        value = (lexical.enum(lexical.LEXICAL_BOOLEANS) if array == 'boolean_properties'
                 else lexical.selection_schema() if array == 'evidence_properties' else {'type': 'string'})
        common[array] = {'type': 'array', 'items': lexical.closed({'field': lexical.enum(fields), 'value': value})}
    return lexical.closed(common)


def compile_candidate(intent):
    """Compile only explicit semantics. Presence, false/empty values and order survive."""
    lexical.validate_shape(intent, candidate_schema())
    return compile_properties(intent)


def compile_properties(intent):
    """Compile schema-validated properties; callers own their protocol shape gate."""
    active = _NODE_VARIANTS.get(intent['primary_type'], set())
    result = {k: copy.deepcopy(v) for k, v in intent.items() if k not in PROPERTY_FIELDS}
    result['confidence'] = lexical.confidence(result['confidence'])
    result['independent_research_value'] = lexical.boolean(result['independent_research_value'])
    provided, preserved = set(), {}
    for array in PROPERTY_FIELDS:
        for entry in intent[array]:
            field = entry['field']
            if field in provided:
                raise ValueError('DUPLICATE_NODE_INTENT_PROPERTY:' + field)
            provided.add(field)
            lexical._variant_value(result if field in active else preserved, field, entry['value'])
    if active - provided:
        raise ValueError('MISSING_NODE_INTENT_PROPERTY:' + ','.join(sorted(active - provided)))
    if preserved:
        result['preserved_fields'] = preserved
    return result
