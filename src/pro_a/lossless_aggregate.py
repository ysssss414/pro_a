"""Target-only bounded composite Aggregate. Historical Wire contracts stay frozen."""
import copy
from dataclasses import asdict
import json

from .analyzer import normalize_ws
from .bounded_extraction import expand_source_analysis_wire_v3, series_coverage
from .claim_observations import build_observation_ledger
from .evidence_binding import identity
from .source_analysis_wire import validate_source_analysis_wire_v2, SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION
from .source_metadata_authority import validate_resolution

VERSION = 'lossless-sourcepiece-aggregate-v2'
REPLAY_VERSION = 'lossless-sourcepiece-native-replay-v1'


class LosslessAggregateError(ValueError):
    pass


def require(value, code):
    if not value:
        raise LosslessAggregateError(code)


def seal(body):
    # JSON-native shape is stable through write-once artifact round trips.
    body = json.loads(json.dumps(body, ensure_ascii=False, allow_nan=False))
    return {**body, 'identity': identity(body)}


def build_aggregate(source_id, series, plan, results, catalog, context, resolution):
    metadata = validate_resolution(resolution)
    bound = resolution['scope']
    require(bound['processing_run_id'] == series.processing_run_id and bound['source_id'] == source_id
            and bound['source_sha256'] == context.source_sha256
            and {'source_piece_id': context.piece.piece_id, 'series_id': series.series_id,
                 'series_sha256': series.series_sha256} in bound['pieces'], 'AGGREGATE_AUTHORITY_SCOPE_MISMATCH')
    coverage = series_coverage(series, plan, results, catalog, context)
    require(coverage.complete, 'SERIES_COVERAGE_INCOMPLETE')
    validate_source_analysis_wire_v2({'wire_version': SOURCE_ANALYSIS_WIRE_SCHEMA_VERSION,
        'source_metadata': metadata, 'claims': []}, catalog, context)
    ledger = build_observation_ledger(source_id, series, plan, results, catalog, context)
    by_id = {r.segment_id: r for r in results}
    ordered = [by_id[s.segment_id] for s in plan.leaves]
    native = {'source_metadata': metadata, 'claims': [], 'node_matches': [],
        'node_candidates': [], 'relation_candidates': [], 'source_references': []}
    candidate_keys, components = {}, []
    for result in ordered:
        wire = json.loads(result.wire_json)
        part = expand_source_analysis_wire_v3(wire, catalog, context)
        offset = len(native['claims'])
        components.append({'segment_id': result.segment_id, 'result_sha256': result.result_sha256,
            'claim_offset': offset, 'claim_count': len(part['claims']),
            'metadata_variant': wire['source_metadata']})
        native['claims'].extend({**c, 'claim_ref': f'C{offset+i}'} for i, c in enumerate(part['claims'], 1))
        for family in ('node_matches', 'source_references'):
            native[family].extend(part[family])
        for candidate, expanded in zip(wire.get('node_candidates', []), part['node_candidates']):
            key = normalize_ws(candidate['canonical_name']).lower()
            require(key not in candidate_keys or candidate_keys[key] == candidate, 'NODE_CANDIDATE_CONFLICT')
            if key not in candidate_keys:
                candidate_keys[key] = copy.deepcopy(candidate)
                native['node_candidates'].append(expanded)
        for relation in part['relation_candidates']:
            native['relation_candidates'].append({**relation,
                'supporting_claim_refs': [f'C{offset+int(ref[1:])}' for ref in relation['supporting_claim_refs']]})
    require(len(components) == len(plan.leaves) <= series.budget.max_leaf_segments,
            'AGGREGATE_FROZEN_BOUND_EXCEEDED')
    bound_count = 100 * len(plan.leaves)
    require(len(native['claims']) <= bound_count and len(native['node_candidates']) <= bound_count,
            'AGGREGATE_FROZEN_BOUND_EXCEEDED')
    return seal({'version': VERSION, 'replay_version': REPLAY_VERSION, 'series_id': series.series_id,
        'series_sha256': series.series_sha256, 'source_metadata_resolution': resolution,
        'source_metadata_resolution_identity': resolution['identity'],
        'ordered_segment_result_sha256': [r.result_sha256 for r in ordered],
        'coverage': {'series_sha256': series.series_sha256,
            **{k: v for k, v in asdict(coverage).items() if k != 'coverage_sha256'}},
        'coverage_sha256': coverage.coverage_sha256, 'claim_capacity': bound_count,
        'components': components, 'observation_ledger': ledger, 'native_input': native,
        'summary_projection': 'PROVISIONAL_UNRESOLVED_ALL_ORIGINAL_VARIANTS_PRESERVED'})


def expand_aggregate(document, series, plan, results, catalog, context):
    """Rebuild from immutable results, not from a self-asserted aggregate hash."""
    expected = build_aggregate(document['observation_ledger']['source_id'], series, plan,
        results, catalog, context, document['source_metadata_resolution'])
    require(document == expected, 'AGGREGATE_IDENTITY_MISMATCH')
    return copy.deepcopy(expected['native_input'])
