"""Versioned explicit Source authority; model agreement never grants authority."""
import copy

from .evidence_binding import identity

VERSION = 'source-metadata-authority-resolution-v1'
DECISION_VERSION = 'explicit-source-metadata-decision-v1'
FIELDS = ('title', 'publication_time', 'author', 'organization', 'source_rank', 'source_origin_type', 'summary')
KINDS = ('VERIFIED_SOURCE_PROVENANCE', 'VERIFIED_DOCUMENT_EVIDENCE',
         'EXPLICIT_HUMAN_RESOLUTION', 'MODEL_DERIVED_UNCONFIRMED', 'UNRESOLVED')


class MetadataAuthorityError(ValueError):
    pass


def require(value, code='METADATA_AUTHORITY_IDENTITY_MISMATCH'):
    if not value:
        raise MetadataAuthorityError(code)


def seal(body):
    return {**copy.deepcopy(body), 'identity': identity(body)}


def scope(run_id, source_id, source_sha256, pieces, accepted_result_shas):
    require(all(isinstance(v, str) and v for v in (run_id, source_id, source_sha256)))
    require(len(source_sha256) == 64 and pieces and accepted_result_shas)
    require(len({p['source_piece_id'] for p in pieces}) == len(pieces)
            and len({p['series_id'] for p in pieces}) == len(pieces))
    require(len(set(accepted_result_shas)) == len(accepted_result_shas))
    return {'processing_run_id': run_id, 'source_id': source_id, 'source_sha256': source_sha256,
            'pieces': copy.deepcopy(pieces), 'accepted_result_shas': list(accepted_result_shas)}


def candidate_resolution(bound_scope, evidence):
    """Evidence can propose values, never impersonate a human authorization.

    Verified provenance/document evidence must be supplied by the trusted source
    reader. Even those candidates require an explicit decision in this version;
    no document-role heuristic or PDF export metadata becomes official metadata.
    """
    for item in evidence:
        require(item.get('field') in FIELDS and item.get('kind') in KINDS)
        require(item.get('source_sha256') == bound_scope['source_sha256'])
        require(isinstance(item.get('value'), str) and isinstance(item.get('evidence'), dict))
        require(item['evidence'], 'METADATA_AUTHORITY_EVIDENCE_REQUIRED')
    fields = {}
    for field in FIELDS:
        choices = [copy.deepcopy(e) for e in evidence if e['field'] == field]
        fields[field] = {'status': 'PROVISIONAL_UNRESOLVED' if field == 'summary' else 'NEEDS_HUMAN_RESOLUTION',
            'authority_kind': 'UNRESOLVED', 'candidates': choices, 'resolved_value': None}
    return seal({'version': VERSION, 'scope': bound_scope, 'fields': fields, 'human_decision': None})


def authorize_resolution(candidate, decision):
    """Consume an explicit private operator-supplied human decision, not a vote.

    This function does not obtain user approval. The operator must supply the
    actual decision receipt with actor, reason and reference; caller authorization
    remains at the operator boundary. Synthetic receipts are only test fixtures.
    """
    require(candidate == candidate_resolution(candidate['scope'],
        [e for f in FIELDS for e in candidate['fields'][f]['candidates']]))
    require(isinstance(decision, dict) and decision.get('version') == DECISION_VERSION,
            'NEEDS_HUMAN_RESOLUTION')
    require(decision.get('candidate_identity') == candidate['identity']
            and decision.get('scope_sha256') == identity(candidate['scope']))
    require(decision.get('approved') is True and all(isinstance(decision.get(k), str)
            and decision[k].strip() for k in ('actor', 'reason', 'decision_reference')), 'NEEDS_HUMAN_RESOLUTION')
    require(set(decision.get('values', {})) == set(FIELDS) - {'summary'})
    require(all(isinstance(v, str) for v in decision['values'].values()))
    require(decision.get('summary_policy') == 'PRESERVE_ALL_VARIANTS_UNRESOLVED')
    # Conflicting independently verified witnesses require explicit disposition.
    conflicts = [field for field in FIELDS if len({e['value'] for e in candidate['fields'][field]['candidates']
        if e['kind'] in KINDS[:2]}) > 1]
    require(all(isinstance(decision.get('conflict_reasons', {}).get(f), str)
                and decision['conflict_reasons'][f].strip() for f in conflicts), 'CONFLICTING_AUTHORITY_EVIDENCE')
    fields = copy.deepcopy(candidate['fields'])
    for field, value in decision['values'].items():
        fields[field].update(status='RESOLVED', authority_kind='EXPLICIT_HUMAN_RESOLUTION',
            resolved_value=value, resolved_value_sha256=identity(value),
            authority_evidence_sha256=identity({'decision': decision,
                'candidates': fields[field]['candidates'], 'field': field}))
    return seal({'version': VERSION, 'scope': candidate['scope'], 'fields': fields,
        'human_decision': copy.deepcopy(decision)})


def validate_resolution(resolution, *, bound_scope=None):
    require(isinstance(resolution, dict) and resolution.get('version') == VERSION)
    if bound_scope is not None:
        require(resolution['scope'] == bound_scope)
    candidate = candidate_resolution(resolution['scope'],
        [e for field in FIELDS for e in resolution['fields'][field]['candidates']])
    require(resolution == authorize_resolution(candidate, resolution.get('human_decision')))
    return {**{f: resolution['fields'][f]['resolved_value'] for f in FIELDS if f != 'summary'},
        'summary': ''}  # Explicit unresolved projection; original summaries stay in each immutable result.
