"""Strict type-discriminated provider encoding; unchanged normalized research IR."""
import copy

from . import source_analysis_provider_record as lexical
from .constants import NODE_TYPES
from .source_analysis_wire import _NODE_VARIANTS, _TYPE_FIELDS, _BOOL_FIELDS
from .extraction_analysis_record import VERSION as NORMALIZED_VERSION
from .analyzer import normalize_ws

VERSION = 'whole-piece-output-batch-provider-record-v4'
SCHEMA_VERSION = 'whole-piece-output-batch-tool-schema-v4'
ENCODING_VERSION = 'deepseek-output-batch-lexical-encoding-v4'
PRESERVED = {
    'preserved_boolean_fields': _BOOL_FIELDS,
    'preserved_text_fields': _TYPE_FIELDS - _BOOL_FIELDS - {'evidence_ref'},
    'preserved_evidence_fields': {'evidence_ref'},
}
ENCODING_GUIDANCE = """
candidate 保持原始顺序；按 primary_type 选择唯一类型分支，只输出公共字段和当前类型的有效字段。
Event 输出 is_discrete_event、event_time、event_evidence；Theme 输出 long_term_research_value、cross_source_or_node_value；
ResearchQuestion 输出 question、importance、what_would_change_my_mind；其他类型无类型专属字段。不得输出无关类型的占位字段。
确实存在的非当前类型字段必须显式、无损放入 preserved_boolean_fields、preserved_text_fields 或 preserved_evidence_fields；
每项含 field 与 value。没有内容时数组为空。不得重复 field，不得放入当前类型的 active field，不得推断缺失字段或自动移动非法字段。
布尔值仍为 TRUE/FALSE 字符串；Evidence value 使用原有 evidence_ref、selection_mode、selector、occurrence，不允许 NONE。
related_candidate_names 必须精确引用本响应实际输出的 candidate；不得制造候选、丢弃引用或引用其他 Segment 的候选。
"""


def record_schema():
    schema = lexical.record_schema()
    original = schema['properties']['node_candidates']['items']['properties']
    common = {k: v for k, v in original.items()
              if k not in _TYPE_FIELDS | {'event_evidence', 'preserved_fields'}}
    common['ownership_evidence_ref'] = {'type': 'string'}
    for array, fields in PRESERVED.items():
        value = (lexical.enum(lexical.LEXICAL_BOOLEANS) if array == 'preserved_boolean_fields'
                 else lexical.selection_schema() if array == 'preserved_evidence_fields' else {'type': 'string'})
        common[array] = {'type': 'array', 'items': lexical.closed({'field': lexical.enum(fields), 'value': value})}
    branches = []
    for primary in ('Event', 'Theme', 'ResearchQuestion', None):
        types = {primary} if primary else set(NODE_TYPES) - set(_NODE_VARIANTS)
        properties = copy.deepcopy(common)
        properties['primary_type'] = lexical.enum(types)
        active = _NODE_VARIANTS.get(primary, set())
        for field in sorted(active):
            name = 'event_evidence' if field == 'evidence_ref' else field
            properties[name] = lexical.selection_schema() if field == 'evidence_ref' else copy.deepcopy(original[name])
        branches.append(lexical.closed(properties))
    schema['properties']['node_candidates']['items'] = {'anyOf': branches}
    reference = schema['properties']['source_references']['items']
    reference['properties']['ownership_evidence_ref'] = {'type': 'string'}
    reference['required'].append('ownership_evidence_ref')
    schema['properties']['evidence_acknowledgements'] = {'type': 'array', 'items': lexical.closed({'evidence_ref': {'type': 'string'}})}
    schema['required'].append('evidence_acknowledgements')
    return schema


def validate_shape(value, schema):
    if 'anyOf' in schema:
        matches = 0
        for branch in schema['anyOf']:
            try:
                validate_shape(value, branch)
            except ValueError:
                continue
            matches += 1
        if matches != 1:
            raise ValueError('INVALID_PROVIDER_VARIANT_BRANCH')
    elif schema['type'] == 'object':
        if type(value) is not dict or set(value) != set(schema['properties']):
            raise ValueError('INVALID_PROVIDER_RECORD_SHAPE')
        for key, child in schema['properties'].items():
            validate_shape(value[key], child)
    elif schema['type'] == 'array':
        if type(value) is not list:
            raise ValueError('INVALID_PROVIDER_RECORD_SHAPE')
        for item in value:
            validate_shape(item, schema['items'])
    else:
        lexical.validate_shape(value, schema)


def normalize_record(content):
    record = lexical.parse_object(content)
    for family in ('claims', 'node_candidates'):
        if type(record.get(family)) is list and len(record[family]) > 100:
            raise ValueError('PROVIDER_RECORD_ARRAY_LIMIT')
    validate_shape(record, record_schema())
    stripped = copy.deepcopy(record)
    acknowledgements = stripped.pop('evidence_acknowledgements')
    candidates = stripped.pop('node_candidates')
    names = [normalize_ws(n['canonical_name']).lower() for n in candidates]
    if len(set(names)) != len(names):
        raise ValueError('DUPLICATE_PROVIDER_CANDIDATE_IDENTITY')
    stripped['node_candidates'] = []
    anchors = [r.pop('ownership_evidence_ref') for r in stripped['source_references']]
    # Unchanged non-Node lexical decoding, including all existing Claim guards.
    normalized = lexical.provider_record_to_wire_v3(stripped)
    normalized.pop('wire_version')
    for obj, anchor in zip(normalized['source_references'], anchors):
        obj['ownership_evidence_ref'] = anchor
    for candidate in candidates:
        active = _NODE_VARIANTS.get(candidate['primary_type'], set())
        obj = {k: copy.deepcopy(v) for k, v in candidate.items()
               if k not in PRESERVED and k not in _TYPE_FIELDS | {'event_evidence'}}
        obj['confidence'] = lexical.confidence(obj['confidence'])
        obj['independent_research_value'] = lexical.boolean(obj['independent_research_value'])
        for field in sorted(active):
            lexical._variant_value(obj, field, candidate['event_evidence' if field == 'evidence_ref' else field])
        preserved, seen = {}, set()
        for array in PRESERVED:
            for entry in candidate[array]:
                field = entry['field']
                if field in seen:
                    raise ValueError('DUPLICATE_PRESERVED_FIELD')
                if field in active:
                    raise ValueError('ACTIVE_FIELD_IN_PRESERVED_SLOT')
                seen.add(field)
                lexical._variant_value(preserved, field, entry['value'])
        if preserved:
            obj['preserved_fields'] = preserved
        normalized['node_candidates'].append(obj)
    return {**normalized, 'analysis_record_version': NORMALIZED_VERSION, 'evidence_acknowledgements': acknowledgements}
