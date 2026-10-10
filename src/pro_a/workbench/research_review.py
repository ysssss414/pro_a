"""Internal research reader and isolated append-only annotations; no MCP writes.

Diagnostic files commit at atomic immutable publication, independently of the
bounded ledger. The existing SQLite writer lock serializes publishers, but no
ledger row/event is inserted. Replay after interruption returns the same file.
"""
import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from pro_a import output_provider_record_v7 as v7
from pro_a.evidence_binding import identity, resolve_evidence_binding_v2
from pro_a.research_quarantine import FAMILIES, VERSION, inspect_response
from .artifacts import Artifacts
from .bounded_extraction_persistence import canonical, checkpoint, write_once
from .bounded_extraction_store import BoundedExtractionStore, _verified
from .config import BoundaryError, WorkbenchConfig, checked_path

DECISIONS = ('INTERESTING', 'NEEDS_FOLLOWUP', 'NOT_USEFUL')


def _scope(run, series, segment, attempt):
    return {'source_id': run['source_id'], 'source_sha256': run['source_sha256'],
        'run_id': run['processing_run_id'], 'runtime_identity': run['runtime_identity'],
        'series_id': series.series_id, 'series_sha256': series.series_sha256,
        'source_piece_id': series.source_piece_id, 'segment_id': segment.segment_id,
        'segment_sha256': segment.segment_sha256, 'attempt_id': attempt['attempt_id'],
        'request_sha256': attempt['request_sha256'], 'configuration_sha256': attempt['configuration_sha256'],
        'provider_record_version': json.loads(attempt['request_json']).get('provider_record_version')}


def project_run(service, run_id):
    """Read existing accepted wires/attachments even when the whole run is blocked.

    Object locators are original segment/family/index, not new permanent Claim
    IDs. No observation ledger, Review Packet registration or runtime execution.
    """
    run = service.get_run(run_id)
    ledger = service.output_batches.ledger
    segments, uncalled, leaves = [], 0, 0
    for _, context, catalog, series in service.output_batches.inputs(run):
        _, plan, _, _ = ledger.read(series.series_id)
        leaves += len(plan.leaves)
        with ledger._connection() as connection:
            results = [dict(r) for r in connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id IN (SELECT segment_id FROM bounded_extraction_segments WHERE series_id=?) ORDER BY rowid', (series.series_id,))]
            attempts = [dict(r) for r in connection.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id IN (SELECT segment_id FROM bounded_extraction_segments WHERE series_id=?)', (series.series_id,))]
        uncalled += sum(not any(a['segment_id'] == s.segment_id for a in attempts) for s in plan.leaves)
        for row in results:
            result = ledger._result(series.series_id, row)
            segment = next(s for s in plan.segments if s.segment_id == row['segment_id'])
            attempt = next(a for a in attempts if a['attempt_id'] == row['attempt_id'])
            with ledger._connection() as connection:
                outcome = _verified(connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt['attempt_id'],)).fetchone())
            envelope, _ = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, attempt['attempt_id']+'.raw.json', outcome))
            document = json.loads(ledger._read_artifact(series.series_id, segment.segment_id+'.result.json', row))
            attachment = document.get('research_review_attachment')
            review = json.loads(ledger._read_artifact(series.series_id, segment.segment_id+'.review.json', attachment)) if attachment else None
            wire = json.loads(result.wire_json)
            objects = []
            for family in FAMILIES:
                for i, value in enumerate(wire.get(family, [])):
                    bindings = [b for b in (review or {}).get('bindings', []) if b['path'][:2] == [family, i]]
                    if family == 'node_candidates' and review:
                        proof = review['candidate_ownership']['candidates'][i]
                        for support in proof['supports']:
                            path = support['path']
                            bindings.extend(b for b in review['bindings'] if b['path'][:2] == path[:2] and b['role'] == 'PRIMARY')
                    if family == 'relation_candidates' and review:
                        for ref in value['supporting_claim_refs']:
                            ci = next((j for j, c in enumerate(wire['claims']) if c.get('claim_ref', 'C'+str(j+1)) == ref), None)
                            if ci is not None:
                                bindings.extend(b for b in review['bindings'] if b['path'][:2] == ['claims', ci] and b['role'] == 'PRIMARY')
                    if not review and family in ('claims', 'node_matches') and value.get('evidence_ref'):
                        bound = resolve_evidence_binding_v2(value, catalog, context)
                        bindings = [{'role': 'PRIMARY', 'binding': bound.__dict__}]
                    objects.append({'object_locator': [segment.segment_id, family, i], 'family': family, 'index': i,
                        'value': value, 'evidence': bindings, 'semantic_review_status': 'SEMANTIC_REVIEW_REQUIRED',
                        'semantic_truth': 'NOT_ESTABLISHED', 'canonical_permission': False})
            segments.append({'scope': _scope(run, series, segment, attempt), 'result_sha256': result.result_sha256,
                'provider_outcome': {**{k: outcome[k] for k in ('provider_request_id', 'input_tokens', 'output_tokens', 'latency_ms', 'artifact_relative', 'artifact_sha256')},
                                     'provider_reported_model': envelope.get('provider_reported_model')},
                'result_artifact': {'artifact_relative': row['artifact_relative'], 'artifact_sha256': row['artifact_sha256']},
                'review_attachment': attachment, 'research_review': review, 'objects': objects,
                'status': 'SEGMENT_ACCEPTED' if row['result_type'] == 'COMPLETE' else 'SUBDIVISION_REQUIRED'})
    complete = run.get('coverage_status') == 'COMPLETE'
    return {'authority': 'NON_AUTHORITATIVE_RESEARCH_VIEW', 'canonical_permission': False,
        'source_id': run['source_id'], 'run_id': run_id, 'run_state': run['state'],
        'source_status': 'SOURCE_COMPLETE' if complete else 'SOURCE_INCOMPLETE',
        'review_status': 'RESEARCH_REVIEW_PENDING', 'leaf_segment_count': leaves,
        'uncalled_segment_count': uncalled, 'accepted_segment_count': sum(s['status'] == 'SEGMENT_ACCEPTED' for s in segments),
        'segments': segments}


def inspect_attempt(service, run_id, attempt_id):
    """The only quarantine producer reads hash-bound durable failed v7 attempts."""
    run = service.get_run(run_id)
    ledger = service.output_batches.ledger
    for _, context, catalog, series in service.output_batches.inputs(run):
        _, plan, _, _ = ledger.read(series.series_id)
        with ledger._connection() as connection:
            attempt = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE attempt_id=? AND segment_id IN (SELECT segment_id FROM bounded_extraction_segments WHERE series_id=?)', (attempt_id, series.series_id)).fetchone()
            if attempt is None:
                continue
            attempt = _verified(attempt)
            if connection.execute('SELECT 1 FROM bounded_extraction_segment_results WHERE attempt_id=?', (attempt_id,)).fetchone():
                raise BoundaryError('ACCEPTED_ATTEMPT_NOT_QUARANTINED')
            outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt_id,)).fetchone()
            if outcome is None:
                raise BoundaryError('DURABLE_OUTCOME_REQUIRED')
            outcome = _verified(outcome)
            failures = [json.loads(r[0]) for r in connection.execute("SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type='SEGMENT_FAILED'", (series.series_id,))]
        failure = next((f['classification'] for f in failures if f.get('attempt_id') == attempt_id), None)
        if failure is None:
            raise BoundaryError('FAILED_ATTEMPT_REQUIRED')
        raw_artifact = {'artifact_relative': outcome['artifact_relative'], 'artifact_sha256': outcome['artifact_sha256']}
        _, raw = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, attempt_id+'.raw.json', outcome))
        segment = next(s for s in plan.segments if s.segment_id == attempt['segment_id'])
        document = inspect_response(raw, _scope(run, series, segment, attempt), segment, catalog, context, failure_code=failure)
        document['raw_artifact'] = raw_artifact
        return document
    raise BoundaryError('ATTEMPT_OUTSIDE_RUN')


class ResearchAttachments:
    def __init__(self, service):
        self.service = service
        self.config = service.config
        self.ledger = BoundedExtractionStore(self.config)
        self.artifacts = Artifacts(self.config)

    def publish(self, run_id, attempt_id):
        # These writes are internal operator actions; no public/MCP write tool.
        with self.ledger._connection(True):
            document = inspect_attempt(self.service, run_id, attempt_id)
            content = canonical(document).encode('utf-8')
            digest = hashlib.sha256(content).hexdigest()
            path = checked_path(self.config.artifact_root/'research-quarantine'/f'{digest}.json', missing=True)
            checkpoint('research_before_publish')
            write_once(path, content)
            checkpoint('research_after_publish')
        return {'artifact_relative': path.relative_to(self.config.artifact_root.resolve()).as_posix(), 'artifact_sha256': digest}

    def read(self, reference):
        content = self.artifacts.resolve(reference['artifact_relative']).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != reference['artifact_sha256'] or reference['artifact_relative'] != f'research-quarantine/{digest}.json':
            raise BoundaryError('QUARANTINE_ARTIFACT_IDENTITY_MISMATCH')
        document = json.loads(content)
        if document['version'] != VERSION or document['authority'] != 'NON_CANONICAL' or document['accepted'] is not False or document['canonical_permission'] is not False:
            raise BoundaryError('QUARANTINE_AUTHORITY_INVALID')
        scope = document['scope']
        if document != inspect_attempt(self.service, scope['run_id'], scope['attempt_id']):
            raise BoundaryError('QUARANTINE_REPLAY_MISMATCH')
        return document

    def markers(self, reference):
        document = self.read(reference)
        object_ids = {o['object_id'] for o in document['objects']}
        root = checked_path(self.config.artifact_root/'research-quarantine'/'markers'/reference['artifact_sha256'], missing=True)
        result, previous = [], '0'*64
        if not root.exists():
            return result
        for i, path in enumerate(sorted(root.glob('*.json')), 1):
            content = checked_path(path).read_bytes()
            marker = json.loads(content)
            payload = {k: v for k, v in marker.items() if k != 'marker_sha256'}
            if path.name != f'{i:08d}.json' or marker['sequence'] != i or marker['previous_sha256'] != previous or marker['quarantine_artifact'] != reference:
                raise BoundaryError('RESEARCH_MARKER_CHAIN_MISMATCH')
            if marker.get('marker_sha256') != identity(payload) or marker['version'] != 'NON_CANONICAL_RESEARCH_MARKER_V1' or marker['authority'] != 'NON_CANONICAL' or marker['canonical_permission'] is not False or marker['object_id'] not in object_ids or marker['decision'] not in DECISIONS or not marker['reviewer'].strip() or not marker['reason'].strip():
                raise BoundaryError('RESEARCH_MARKER_IDENTITY_MISMATCH')
            result.append(marker); previous = hashlib.sha256(content).hexdigest()
        return result

    def annotate(self, reference, object_id, *, reviewer, decision, reason):
        if decision not in DECISIONS or not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(reason, str) or not reason.strip():
            raise BoundaryError('INVALID_RESEARCH_MARKER')
        with self.ledger._connection(True):
            document = self.read(reference)
            if object_id not in {o['object_id'] for o in document['objects']}:
                raise BoundaryError('UNKNOWN_QUARANTINE_OBJECT')
            markers = self.markers(reference)
            root = checked_path(self.config.artifact_root/'research-quarantine'/'markers'/reference['artifact_sha256'], missing=True)
            previous = hashlib.sha256(checked_path(root/f'{len(markers):08d}.json').read_bytes()).hexdigest() if markers else '0'*64
            marker = {'version': 'NON_CANONICAL_RESEARCH_MARKER_V1', 'authority': 'NON_CANONICAL', 'canonical_permission': False,
                'quarantine_artifact': reference, 'object_id': object_id, 'reviewer': reviewer,
                'created_at': datetime.now(timezone.utc).isoformat(), 'decision': decision, 'reason': reason,
                'sequence': len(markers)+1, 'previous_sha256': previous}
            marker['marker_sha256'] = identity(marker)
            write_once(root/f'{len(markers)+1:08d}.json', canonical(marker).encode('utf-8'))
            checkpoint('research_marker_after_publish')
        return marker


def render_html(view, quarantines=(), markers=()):
    """Private static view. Escape all model/source text; no promotion controls."""
    def dump(value):
        return html.escape(json.dumps(value, ensure_ascii=False, indent=2))
    def card(obj, decisions=()):
        value = obj['value']
        title = value.get('statement', value.get('canonical_name', value.get('reason', value.get('title', obj['family'])))) if isinstance(value, dict) else str(value)
        evidence = obj['evidence']
        blocks = ['<article><h3>'+html.escape(str(title))+'</h3>', '<p>'+html.escape(obj.get('location_status', 'SEGMENT_ACCEPTED'))+' · '+html.escape(obj.get('reference_status', 'RESEARCH_REVIEW_PENDING'))+' · SEMANTIC_REVIEW_REQUIRED</p>']
        for proof in evidence:
            binding = proof['binding']
            blocks.append('<blockquote>'+html.escape(binding['evidence_excerpt'])+'</blockquote><small>'+html.escape(binding['source_locator'])+' · '+str(binding['source_start'])+'–'+str(binding['source_end'])+' · '+html.escape(proof['role'])+'</small>')
        blocks.append('<details><summary>Original object, context, provenance and unresolved issues</summary><pre>'+dump(obj)+'</pre></details>')
        if decisions:
            blocks.append('<h4>Research markers</h4><pre>'+dump(decisions)+'</pre>')
        blocks.append('</article>')
        return ''.join(blocks)
    parts = ['<!doctype html><meta charset="utf-8"><title>Research review</title>',
        '<style>body{max-width:1050px;margin:2rem auto;font:16px system-ui}article{border:1px solid #aaa;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style>',
        '<h1>Research review</h1><p>Non-canonical · Human review required · No promotion authority</p>',
        '<pre>'+dump({k: v for k, v in view.items() if k != 'segments'})+'</pre>']
    for segment in view['segments']:
        parts.append('<h2>'+html.escape(segment['status'])+'</h2><details><summary>Provenance and context review</summary><pre>'+dump({k: v for k, v in segment.items() if k != 'objects'})+'</pre></details>')
        for obj in segment['objects']:
            parts.append(card(obj))
    for document in quarantines:
        parts.append('<h2>NON_CANONICAL_QUARANTINE</h2><pre>'+dump({k: v for k, v in document.items() if k != 'objects'})+'</pre>')
        for obj in document['objects']:
            decisions = [m for m in markers if m['object_id'] == obj['object_id']]
            parts.append(card(obj, decisions))
    return '\n'.join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Internal private research reader; annotations confer no canonical authority.')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--inspect-attempt', help='Read-only forensics; never publishes an attachment.')
    parser.add_argument('--publish-attempt', help='Explicit internal operator publication; isolated environments only in this stage.')
    parser.add_argument('--attachment', type=Path, help='Private JSON file containing the immutable artifact reference.')
    parser.add_argument('--object-id'); parser.add_argument('--reviewer'); parser.add_argument('--decision', choices=DECISIONS); parser.add_argument('--reason')
    args = parser.parse_args(argv)
    from .store import Store
    from .extraction_retry import bounded_frozen_components
    from .source_operations import SourceOperations
    config = WorkbenchConfig.load(args.config)
    with Store(config).connect() as connection:
        row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (args.run,)).fetchone()
        if row is None:
            raise BoundaryError('UNKNOWN_RUN')
        profile, cloud, _, _ = bounded_frozen_components(config, connection, row)
    service = SourceOperations(config, profile, cloud)
    store = ResearchAttachments(service)
    view, documents, markers = project_run(service, args.run), [], []
    if args.inspect_attempt:
        documents.append(inspect_attempt(service, args.run, args.inspect_attempt))
    if args.publish_attempt:
        print(canonical(store.publish(args.run, args.publish_attempt)))
    if args.attachment:
        reference = json.loads(args.attachment.read_text(encoding='utf-8'))
        document = store.read(reference)
        if document['scope']['run_id'] != args.run:
            raise BoundaryError('ATTACHMENT_OUTSIDE_RUN')
        if args.object_id:
            store.annotate(reference, args.object_id, reviewer=args.reviewer, decision=args.decision, reason=args.reason)
        documents.append(document); markers = store.markers(reference)
    elif args.object_id:
        parser.error('--object-id requires --attachment')
    if args.output:
        path = checked_path(args.output, missing=True)
        if path.is_relative_to(config.artifact_root.resolve()):
            raise BoundaryError('EXPORT_INSIDE_ARTIFACT_STORE_FORBIDDEN')
        with path.open('x', encoding='utf-8') as stream:
            stream.write(render_html(view, documents, markers))
    elif not args.publish_attempt:
        print(canonical({'view': view, 'quarantines': documents, 'markers': markers}))


if __name__ == '__main__':
    main()
