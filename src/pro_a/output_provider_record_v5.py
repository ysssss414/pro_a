"""Explicit V5 Node intent encoding over the unchanged normalized analysis record."""
import copy

from . import source_analysis_provider_record as lexical
from . import output_provider_record_v4 as v4
from . import node_candidate_intent as nodes
from .analyzer import normalize_ws
from .extraction_analysis_record import VERSION as NORMALIZED_VERSION

VERSION = 'whole-piece-output-batch-provider-record-v5'
SCHEMA_VERSION = 'whole-piece-output-batch-tool-schema-v5'
ENCODING_VERSION = 'deepseek-output-batch-semantic-intent-encoding-v1'


def record_schema():
    schema = v4.record_schema()
    schema['properties']['node_candidates']['items'] = nodes.candidate_schema()
    return schema


def normalize_record(content):
    record = lexical.parse_object(content)
    for family in ('claims', 'node_candidates'):
        if type(record.get(family)) is list and len(record[family]) > 100:
            raise ValueError('PROVIDER_RECORD_ARRAY_LIMIT')
    lexical.validate_shape(record, record_schema())
    names = [normalize_ws(n['canonical_name']).lower() for n in record['node_candidates']]
    if len(set(names)) != len(names):
        raise ValueError('DUPLICATE_PROVIDER_CANDIDATE_IDENTITY')
    candidates = [nodes.compile_candidate(n) for n in record['node_candidates']]
    stripped = copy.deepcopy(record)
    acknowledgements = stripped.pop('evidence_acknowledgements')
    stripped['node_candidates'] = []
    anchors = [r.pop('ownership_evidence_ref') for r in stripped['source_references']]
    # Existing lexical decoders continue to own Claims, Matches and Relations.
    normalized = lexical.provider_record_to_wire_v3(stripped)
    normalized.pop('wire_version')
    for obj, anchor in zip(normalized['source_references'], anchors):
        obj['ownership_evidence_ref'] = anchor
    normalized['node_candidates'] = candidates
    return {**normalized, 'analysis_record_version': NORMALIZED_VERSION,
            'evidence_acknowledgements': acknowledgements}
