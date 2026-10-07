"""Provider-neutral extraction acceptance over existing normalized Wire fields.

Evidence acknowledgement is execution responsibility, never a research value.
Only validated Claim Evidence determines linkage. No transport or lexical types.
"""
import copy
from collections import Counter
import hashlib

from .bounded_extraction import EvidenceDisposition, create_segment_wire_result
from .evidence_binding import EVIDENCE_SELECTION_FIELDS, resolve_evidence_binding_v2
from .prompts import SOURCE_ANALYSIS_SYSTEM

VERSION = 'normalized-extraction-analysis-record-v1'
SEMANTIC_PROMPT_VERSION = 'selective-extraction-semantic-prompt-v1'
SEMANTIC_SYSTEM = SOURCE_ANALYSIS_SYSTEM + """
研究抽取目标是 MATERIALITY_WEIGHTED_SELECTIVE_EXTRACTION，不是 exhaustive document ETL。
完整阅读完整 SourcePiece 和 assigned Evidence，只输出具有研究价值、增量价值或验证价值的 Claim。
优先定量事实、产能/出货/订单、客户/供应商、价格/ASP/成本/利润率、认证、产品规格、时间线、管理层指引、
重要战略变化、重大风险、矛盾、新颖信息、可能改变投资论点的信息和重要监测/验证点。
通用营销、模板套话、重复背景、低价值叙述、已表达的重复信息、琐碎陈述和无支持推断不要求生成 durable Claim。
执行 coverage 必须完整；每条 emitted Claim 必须有有效 Evidence，但每个 Evidence 不要求至少一个 Claim。
evidence_acknowledgements 对每个 assigned Evidence 恰好给出一条 {evidence_ref}，不重复、不遗漏、不虚构。
acknowledgement 仅声明该 Evidence 已进入本批次 processing responsibility，表示已考虑，不代表必须产生 Claim。
全部 Evidence acknowledged 且 Claims=[] 完全合法；禁止为了 coverage 制造、机械拆分或重复 Claim。
Evidence acknowledgement 不输出 Claim count、Claim refs 或 disposition；Relation 的 supporting_claim_refs 仍须按原规则输出。
本调用只承担 assigned Evidence 的输出责任，语义上下文始终为完整 SourcePiece。
无标签周围原文只供理解，不得虚构 Evidence ID 或引用其他批次 Evidence。
所有 Claim、node_match、Event 和 preserved Evidence 必须属于本批次。
candidate/source_reference 的 ownership_evidence_ref 只表达执行归属，必须属于本批次，不是永久研究语义。
Claim 引用 candidate 时须本批次同时输出；Relation 仅引用本响应 Claims，禁止跨批次合成。
source_metadata 根据完整 SourcePiece 填写，各批次逐字段一致；不得请求细分、部分完成或继续生成。
"""


def contract():
    # Model/provider/profile belong to execution identity, not this identity.
    return {'normalized_analysis_record_version': VERSION,
        'semantic_prompt_version': SEMANTIC_PROMPT_VERSION,
        'semantic_prompt_sha256': hashlib.sha256(SEMANTIC_SYSTEM.encode()).hexdigest(),
        'extraction_objective': 'MATERIALITY_WEIGHTED_SELECTIVE_EXTRACTION',
        'execution_coverage_required': True, 'claim_per_evidence_required': False,
        'every_emitted_claim_requires_valid_evidence': True, 'raw_fact_recall_100_percent_required': False,
        'claim_linkage_source': 'VALIDATED_CLAIM_EVIDENCE',
        'wire': 'source-analysis-wire-v3', 'evidence_binding': 'source-analysis-evidence-binding-v2'}


def record_to_result(record, series, segment, catalog, context):
    families = {'source_metadata', 'claims', 'node_matches', 'node_candidates', 'relation_candidates', 'source_references'}
    if (type(record) is not dict or set(record) != families | {'analysis_record_version', 'evidence_acknowledgements'}
            or record['analysis_record_version'] != VERSION):
        raise ValueError('INVALID_NORMALIZED_ANALYSIS_RECORD')
    wire = copy.deepcopy(record)
    wire.pop('analysis_record_version')
    acknowledgements = wire.pop('evidence_acknowledgements')
    if (type(acknowledgements) is not list or any(type(a) is not dict or set(a) != {'evidence_ref'}
            or type(a['evidence_ref']) is not str for a in acknowledgements)):
        raise ValueError('INVALID_EVIDENCE_ACKNOWLEDGEMENT')
    owned = set(segment.assigned_evidence_refs)
    refs = [a['evidence_ref'] for a in acknowledgements]
    if set(refs) - owned:
        raise ValueError('FOREIGN_EVIDENCE_ACKNOWLEDGEMENT')
    if any(count != 1 for count in Counter(refs).values()):
        raise ValueError('DUPLICATE_EVIDENCE_ACKNOWLEDGEMENT')
    if set(refs) != owned:
        raise ValueError('MISSING_EVIDENCE_ACKNOWLEDGEMENT')
    for family in ('node_candidates', 'source_references'):
        for obj in wire[family]:
            if obj.pop('ownership_evidence_ref') not in owned:
                raise ValueError('OUTPUT_OWNERSHIP_VIOLATION')
    expected = {ref: set() for ref in owned}
    for index, claim in enumerate(wire['claims'], 1):
        selection = {key: claim[key] for key in EVIDENCE_SELECTION_FIELDS if key in claim}
        binding = resolve_evidence_binding_v2(selection, catalog, context)
        if binding.evidence_ref not in owned:
            raise ValueError('OUTPUT_OWNERSHIP_VIOLATION')
        expected[binding.evidence_ref].add(f'C{index}')
    dispositions = tuple(EvidenceDisposition(ref, 'CLAIMED' if expected[ref] else 'NO_INDEPENDENT_CLAIM')
                         for ref in segment.assigned_evidence_refs)
    wire['wire_version'] = 'source-analysis-wire-v3'
    # Existing gates validate every other family, native types and active selector.
    return create_segment_wire_result(series, segment, wire, dispositions, catalog, context)
