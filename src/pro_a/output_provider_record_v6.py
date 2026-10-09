"""V6: explicit semantic support -> validated, set-valued Segment ownership."""
import copy

from . import output_provider_record_v5 as v5
from . import source_analysis_provider_record as lexical
from .analyzer import normalize_ws
from .bounded_extraction import EvidenceDisposition, create_segment_wire_result
from .evidence_binding import identity, resolve_evidence_binding_v2

VERSION = 'whole-piece-output-batch-provider-record-v6'
SCHEMA_VERSION = 'whole-piece-output-batch-tool-schema-v6'
ENCODING_VERSION = 'deepseek-output-batch-semantic-intent-encoding-v2'
OWNERSHIP_VERSION = 'candidate-support-set-ownership-v1'
ENCODING_GUIDANCE = v5.nodes.ENCODING_GUIDANCE.replace(
    '每个 candidate 必须明确提供本批次 ownership_evidence_ref；程序不会推断归属或生成 Evidence。',
    'candidate 不输出 ownership_evidence_ref。每个 candidate 必须有显式 Claim.related_candidate_names 引用，'
    '或在 evidence_properties 中给出有效 evidence_ref Selection。不得为归属制造 Claim。'
    '程序验证全部支持关系及 Evidence；全部支持 Evidence 必须属于当前 Segment，不能省略冲突来源。')


def record_schema():
    schema = v5.record_schema()
    node = schema['properties']['node_candidates']['items']
    del node['properties']['ownership_evidence_ref']
    node['required'].remove('ownership_evidence_ref')
    return schema


def compile_result(content, series, segment, catalog, context):
    record = lexical.parse_object(content)
    for family in ('claims', 'node_candidates'):
        if type(record.get(family)) is list and len(record[family]) > 100:
            raise ValueError('PROVIDER_RECORD_ARRAY_LIMIT')
    lexical.validate_shape(record, record_schema())
    names = [normalize_ws(n['canonical_name']).lower() for n in record['node_candidates']]
    if len(names) != len(set(names)):
        raise ValueError('DUPLICATE_PROVIDER_CANDIDATE_IDENTITY')
    owned = set(segment.assigned_evidence_refs)
    supports = [[] for _ in names]

    def bind(selection, path):
        evidence = resolve_evidence_binding_v2(lexical.selection(selection), catalog, context)
        if evidence.evidence_ref not in owned:
            raise ValueError('OUTPUT_OWNERSHIP_VIOLATION')
        return {'path': path, 'selection': copy.deepcopy(selection),
                'evidence_ref': evidence.evidence_ref, 'binding_sha256': evidence.binding_sha256}

    claimed = set()
    for ci, claim in enumerate(record['claims']):
        support = bind(claim['evidence'], ['claims', ci, 'evidence'])
        claimed.add(support['evidence_ref'])
        for ri, ref in enumerate(claim['related_candidate_names']):
            name = normalize_ws(ref).lower()
            if name not in names:
                raise ValueError('UNKNOWN_PROVIDER_CANDIDATE_REFERENCE')
            supports[names.index(name)].append({**support, 'relationship_path':
                ['claims', ci, 'related_candidate_names', ri]})
    proof = []
    for ni, candidate in enumerate(record['node_candidates']):
        for ei, entry in enumerate(candidate['evidence_properties']):
            supports[ni].append(bind(entry['value'], ['node_candidates', ni, 'evidence_properties', ei, 'value']))
        if not supports[ni]:
            raise ValueError('CANDIDATE_OWNERSHIP_SUPPORT_REQUIRED')
        # Set containment proves unique ownership in this Segment. No representative
        # Evidence is selected, even when multiple validated sources support a node.
        proof.append({'candidate_index': ni, 'evidence_refs': sorted({s['evidence_ref'] for s in supports[ni]}),
                      'supports': supports[ni]})
    wire = copy.deepcopy(record)
    acknowledgements = wire.pop('evidence_acknowledgements')
    refs = [a['evidence_ref'] for a in acknowledgements]
    if len(refs) != len(set(refs)) or set(refs) != owned:
        raise ValueError('INVALID_EVIDENCE_ACKNOWLEDGEMENT')
    candidates = [v5.nodes.compile_properties(n) for n in wire.pop('node_candidates')]
    wire['node_candidates'] = []
    for reference in wire['source_references']:
        if reference.pop('ownership_evidence_ref') not in owned:
            raise ValueError('OUTPUT_OWNERSHIP_VIOLATION')
    wire = lexical.provider_record_to_wire_v3(wire)
    wire['node_candidates'] = candidates
    dispositions = tuple(EvidenceDisposition(ref, 'CLAIMED' if ref in claimed else 'NO_INDEPENDENT_CLAIM')
                         for ref in segment.assigned_evidence_refs)
    result = create_segment_wire_result(series, segment, wire, dispositions, catalog, context)
    provenance = {'version': OWNERSHIP_VERSION, 'provider_record_sha256': identity(record),
                  'series_sha256': series.series_sha256, 'segment_sha256': segment.segment_sha256,
                  'candidates': proof, 'result_sha256': result.result_sha256}
    return result, provenance
