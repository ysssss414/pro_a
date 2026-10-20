"""Independent A/B advice bound to the native blind review context."""
import json
import re

from pro_a.evidence_binding import identity
from .bounded_extraction_persistence import canonical, write_once
from .config import BoundaryError, checked_path
from .review import require_safe_projection
from .review_policy import ReviewPolicy, slots


def required(packet):
    return any(row['content'].get('candidate_origin') for row in packet['claims'])


def validate_opinion(packet, opinion, policy=None):
    """Validate one submitted opinion; never creates another reviewer's record."""
    fields = {'version', 'slot', 'packet_sha256', 'context_sha256', 'reviewer_type',
              'reviewer_id', 'items', 'sha256'}
    if 'reused_advice' in opinion:
        fields.add('reused_advice')
    if policy:
        fields.add('review_policy_sha256')
    body = {k: v for k, v in opinion.items() if k != 'sha256'}
    if (set(opinion) != fields or opinion['sha256'] != identity(body)
            or opinion['version'] != ('native-advice-v2' if policy else 'native-advice-v1')
            or opinion['slot'] not in slots(policy)
            or opinion['packet_sha256'] != packet['immutable_packet_sha256']
            or opinion['reviewer_type'] not in ('MODEL', 'HUMAN_REVIEWER')
            or not isinstance(opinion['reviewer_id'], str) or not opinion['reviewer_id'].strip()
            or not re.fullmatch('[0-9a-f]{64}', str(opinion['context_sha256']))):
        raise BoundaryError('ADVICE_BINDING_INVALID')
    if policy and (opinion['review_policy_sha256'] != policy['sha256']
                   or opinion['context_sha256'] != policy['binding']['context_sha256']
                   or opinion['reviewer_type'] != 'MODEL'):
        raise BoundaryError('ADVICE_POLICY_MISMATCH')
    ids = {row['candidate_id']: row['content_sha256']
           for group in ('claims', 'nodes', 'relations') for row in packet[group]}
    items = opinion['items']
    if (not isinstance(items, list) or len(items) != len(ids)
            or any(not isinstance(i, dict) for i in items)
            or {i.get('candidate_id') for i in items} != set(ids)):
        raise BoundaryError('ADVICE_UNIVERSE_INVALID')
    for item in items:
        if (set(item) != {'candidate_id', 'content_sha256', 'judgment', 'reason'}
                or item['content_sha256'] != ids[item['candidate_id']]
                or item['judgment'] not in ('SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN')
                or not isinstance(item['reason'], str) or not item['reason'].strip()):
            raise BoundaryError('ADVICE_REVISION_INVALID')
    reused = opinion.get('reused_advice', {})
    if not isinstance(reused, dict) or set(reused) - set(ids):
        raise BoundaryError('ADVICE_REUSE_INVALID')
    for proof in reused.values():
        if set(proof) != {'opinion_sha256', 'packet_sha256', 'context_sha256', 'content_sha256'} or any(
                not re.fullmatch('[0-9a-f]{64}', str(v)) for v in proof.values()):
            raise BoundaryError('ADVICE_REUSE_INVALID')
    require_safe_projection(opinion)
    return opinion


def validate(packet, opinions, policy=None):
    """Seal gate: real complete opinions required by the bound policy."""
    if set(opinions) != set(slots(policy)):
        raise BoundaryError('SINGLE_ADVICE_REQUIRED' if len(slots(policy)) == 1 else 'DUAL_ADVICE_REQUIRED')
    for slot, opinion in opinions.items():
        validate_opinion(packet, opinion, policy)
        if opinion['slot'] != slot:
            raise BoundaryError('ADVICE_SLOT_INVALID')
    if len(slots(policy)) == 2 and (opinions['A']['reviewer_id'] == opinions['B']['reviewer_id']
            or opinions['A']['context_sha256'] != opinions['B']['context_sha256']):
        raise BoundaryError('INDEPENDENT_SAME_CONTEXT_ADVICE_REQUIRED')
    return opinions


def validate_promotable(completed, opinions, policy=None):
    validate(completed, opinions, policy)
    for group in ('claims', 'nodes', 'relations'):
        for row in completed[group]:
            if row['human_input']['decision'] not in ('KEEP', 'CREATE', 'REUSE'):
                continue
            for opinion in opinions.values():
                item = next(i for i in opinion['items'] if i['candidate_id'] == row['candidate_id'])
                if item['judgment'] != 'SUPPORTED':
                    raise BoundaryError('CANDIDATE_SUPPORT_UNRESOLVED')


class AdvisoryReview:
    def __init__(self, reviews):
        self.reviews = reviews

    def _path(self, packet, slot):
        if slot not in ('A', 'B'):
            raise BoundaryError('ADVICE_SLOT_INVALID')
        return checked_path(self.reviews.config.artifact_root / 'review-advice' /
                            packet['immutable_packet_sha256'] / (slot + '.json'), missing=True)

    def submit(self, handle, opinion):
        from pro_a.read_model.service import ReadService
        from pro_a.read_model.review_context import basis
        packet, _, _, _ = self.reviews._context(handle)
        policy = ReviewPolicy(self.reviews).read(handle)
        if not required(packet):
            raise BoundaryError('CANDIDATE_REVIEW_REQUIRED')
        context, _, _ = basis(ReadService(self.reviews.config), handle, 'blind', opinion.get('context_sha256'))
        if opinion.get('context_sha256') != context.context_sha256:
            raise BoundaryError('ADVICE_CONTEXT_CHANGED')
        value = {**opinion, 'version': 'native-advice-v2' if policy else 'native-advice-v1',
                 'packet_sha256': packet['immutable_packet_sha256']}
        if policy:
            value['review_policy_sha256'] = policy['sha256']
        previous_handle = value.pop('reuse_from', None)
        if 'reused_advice' in value:
            raise BoundaryError('ADVICE_REUSE_PROOF_SERVER_OWNED')
        if previous_handle:
            previous, _, _, _ = self.reviews._context(previous_handle)
            if any(previous[k] != packet[k] for k in ('source', 'production_baseline')):
                raise BoundaryError('ADVICE_REUSE_CONTEXT_CHANGED')
            previous_context, _, _ = basis(ReadService(self.reviews.config), previous_handle, 'blind', None)
            from pro_a.read_model.reads import DomainReads
            domains = DomainReads(self.reviews.config)
            old_scope = domains.read(previous_context.run.processing_run_id)
            new_scope = domains.read(context.run.processing_run_id)
            if (not old_scope or not new_scope or old_scope['resume_sha256'] != new_scope['resume_sha256']
                    or previous_context.run.frozen_context.runtime_sha256 != context.run.frozen_context.runtime_sha256):
                raise BoundaryError('ADVICE_REUSE_CONTEXT_CHANGED')
            prior = json.loads(self._path(previous, value['slot']).read_text(encoding='utf-8'))
            validate_opinion(previous, prior, ReviewPolicy(self.reviews).read(previous_handle))
            self._registered(previous, prior)
            if prior['context_sha256'] != previous_context.context_sha256:
                raise BoundaryError('ADVICE_REUSE_CONTEXT_CHANGED')
            if any(prior[k] != value[k] for k in ('reviewer_id', 'reviewer_type', 'slot')):
                raise BoundaryError('ADVICE_REUSE_REVIEWER_CHANGED')
            content = {r['candidate_id']: r['content_sha256'] for group in ('claims', 'nodes', 'relations') for r in packet[group]}
            submitted = {i['candidate_id'] for i in value['items']}
            value['items'] = list(value['items'])
            value['reused_advice'] = {}
            for item in prior['items']:
                cid = item['candidate_id']
                if cid not in submitted and content.get(cid) == item['content_sha256']:
                    value['items'].append(item)
                    value['reused_advice'][cid] = {'opinion_sha256': prior['sha256'],
                        'packet_sha256': prior['packet_sha256'], 'context_sha256': prior['context_sha256'],
                        'content_sha256': item['content_sha256']}
        value.pop('sha256', None)
        value['sha256'] = identity(value)
        validate_opinion(packet, value, policy)
        with self.reviews.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            from .candidate_lifecycle import require_handle
            require_handle(self.reviews.config, handle, connection=connection)
            if ReviewPolicy(self.reviews).read(handle, connection=connection) != policy:
                raise BoundaryError('REVIEW_POLICY_BINDING_DRIFT')
            draft = connection.execute('SELECT status FROM review_drafts WHERE artifact_id=?', (handle,)).fetchone()
            if draft and draft[0] == 'SEALED':
                raise BoundaryError('ALREADY_SEALED')
            from .source_operations import SourceOperations
            run = connection.execute('SELECT processing_run_id FROM source_processing_runs WHERE packet_artifact_id=?', (handle,)).fetchone()
            if run is None:
                raise BoundaryError('CANDIDATE_NATIVE_RUN_REQUIRED')
            event = {'packet_sha256': packet['immutable_packet_sha256'], 'slot': value['slot'], 'opinion_sha256': value['sha256']}
            existing = [json.loads(r[0]) for r in connection.execute("SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type='CANDIDATE_ADVICE_SUBMITTED'", (run[0],))]
            same = [e for e in existing if e['slot'] == value['slot']]
            if same and same != [event]:
                raise BoundaryError('ADVICE_SUBMISSION_CONFLICT')
            write_once(self._path(packet, value['slot']), canonical(value).encode('utf-8'))
            if not same:
                SourceOperations._event(connection, run[0], 'CANDIDATE_ADVICE_SUBMITTED', event)
        return value

    def _registered(self, packet, opinion):
        with self.reviews.store.connect() as connection:
            rows = [json.loads(r[0]) for r in connection.execute("SELECT event_json FROM source_processing_events WHERE event_type='CANDIDATE_ADVICE_SUBMITTED'")]
        expected = {'packet_sha256': packet['immutable_packet_sha256'], 'slot': opinion['slot'], 'opinion_sha256': opinion['sha256']}
        matches = [e for e in rows if e['packet_sha256'] == expected['packet_sha256'] and e['slot'] == expected['slot']]
        if matches != [expected]:
            raise BoundaryError('ADVICE_REGISTERED_IDENTITY_MISMATCH')

    def read(self, packet, *, handle=None):
        if handle is None:
            with self.reviews.store.connect() as connection:
                row = connection.execute('SELECT artifact_id FROM registered_packets WHERE packet_id=?',
                                         (packet['packet_id'],)).fetchone()
            handle = row[0] if row else None
        policy = ReviewPolicy(self.reviews).read(handle) if handle else None
        opinions = {}
        for slot in ('A', 'B'):
            path = self._path(packet, slot)
            if path.is_file():
                opinions[slot] = json.loads(path.read_text(encoding='utf-8'))
                self._registered(packet, opinions[slot])
        validate(packet, opinions, policy)
        if handle is not None:
            from pro_a.read_model.service import ReadService
            from pro_a.read_model.review_context import basis
            basis(ReadService(self.reviews.config), handle, 'blind', opinions['A']['context_sha256'])
        return opinions
