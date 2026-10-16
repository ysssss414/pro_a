"""Durable candidate Origins; no Provider dispatch and no historical state edits."""
from __future__ import annotations

import hashlib
import json

from pro_a import candidate_origin
from .bounded_extraction_store import _verified
from .bounded_extraction_persistence import canonical, write_once
from .config import BoundaryError, checked_path


class CandidateArchive:
    """Read-only access to the same Source/Series validator, without worker setup."""
    def __init__(self, config):
        from .artifacts import Artifacts
        from .store import Store
        from .output_decomposition import OutputDecompositionRunner
        self.config, self.store, self.artifacts = config, Store(config), Artifacts(config)
        self.output_batches = OutputDecompositionRunner(self)

    def get_run(self, run_id):
        with self.store.connect() as connection:
            row = connection.execute('''SELECT r.processing_run_id,r.source_id,r.runtime_json,
                s.source_sha256 FROM source_processing_runs r JOIN private_sources s
                ON s.source_id=r.source_id WHERE r.processing_run_id=?''', (run_id,)).fetchone()
        if row is None:
            raise BoundaryError('CANDIDATE_RUN_UNAVAILABLE')
        return {**dict(row), 'runtime_identity': json.loads(row['runtime_json'])}


def verify_documents(config, documents, selection=None):
    archive = CandidateArchive(config)
    if not documents:
        raise BoundaryError('CANDIDATE_INPUT_REQUIRED')
    for document in documents:
        scope = document['scope']
        if document != inspect_attempt(archive, scope['run_id'], scope['attempt_id'], document.get('revisions')):
            raise BoundaryError('CANDIDATE_ORIGIN_DRIFT')
    if selection is not None:
        candidate_origin.validate_selection(documents, selection)
        from .domains import Domains
        run_id = documents[0]['scope']['run_id']
        frozen = Domains(config).read(run_id)
        if (frozen is None or frozen['context_sha256'] != selection['frozen_context_sha256']
                or any(d['scope']['runtime_identity'] != frozen['basis']['runtime'] for d in documents)):
            raise BoundaryError('SELECTION_FROZEN_CONTEXT_DRIFT')
        expected = {r['set_identity']:r['result_sha256'] for r in selection['accepted_results']}
        with archive.store.connect() as db:
            for document in documents:
                row = db.execute('SELECT * FROM bounded_extraction_segment_results WHERE attempt_id=?',
                    (document['scope']['attempt_id'],)).fetchone()
                if row is None or _verified(row)['result_sha256'] != expected[document['identity']]:
                    raise BoundaryError('SELECTION_ACCEPTED_RESULT_DRIFT')
    return documents


def inspect_attempt(service, run_id, attempt_id, revisions=None):
    """Reconstruct an input only from the verified durable attempt and Source."""
    run = service.get_run(run_id)
    with service.store.connect() as connection:
        source = connection.execute('SELECT * FROM private_sources WHERE source_id=?',
                                    (run['source_id'],)).fetchone()
    path = service.artifacts.resolve(source['storage_relative'])
    if (path.stat().st_size != source['size_bytes'] or
            hashlib.sha256(path.read_bytes()).hexdigest() != run['source_sha256']):
        raise BoundaryError('IMMUTABLE_SOURCE_CORRUPTED')
    ledger = service.output_batches.ledger
    for _, context, catalog, series in service.output_batches.inputs(run):
        _, plan, _, _ = ledger.read(series.series_id)
        with ledger._connection() as connection:
            attempt = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?',
                                         (attempt_id,)).fetchone()
            if attempt is None or not any(s.segment_id == attempt['segment_id'] for s in plan.segments):
                continue
            attempt = _verified(attempt)
            outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?',
                                         (attempt_id,)).fetchone()
            if outcome is None:
                raise BoundaryError('CANDIDATE_DURABLE_OUTCOME_REQUIRED')
            outcome = _verified(outcome)
        _, raw = ledger._decode_envelope(attempt, ledger._read_artifact(
            series.series_id, attempt_id + '.raw.json', outcome))
        segment = next(s for s in plan.segments if s.segment_id == attempt['segment_id'])
        scope = {
            'source_id': run['source_id'], 'source_sha256': run['source_sha256'],
            'source_ingestion_time': source['uploaded_at'],
            'run_id': run_id, 'runtime_identity': run['runtime_identity'],
            'series_id': series.series_id, 'series_sha256': series.series_sha256,
            'source_piece_id': series.source_piece_id, 'segment_id': segment.segment_id,
            'segment_sha256': segment.segment_sha256, 'attempt_id': attempt_id,
            'request_sha256': attempt['request_sha256'],
            'configuration_sha256': attempt['configuration_sha256'],
            'provider_record_version': json.loads(attempt['request_json']).get('provider_record_version'),
            'raw_artifact_sha256': outcome['artifact_sha256'],
            'outcome_sha256': outcome['record_sha256'],
        }
        return candidate_origin.build(raw, scope, segment, catalog, context, revisions)
    raise BoundaryError('CANDIDATE_ATTEMPT_OUTSIDE_RUN')


class CandidateInputs:
    def __init__(self, service):
        self.service = service

    def publish(self, run_id, attempt_id, revisions=None):
        # Independent immutable input artifacts cannot alter Accepted/Coverage.
        with self.service.store.connect(operator_write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            document = inspect_attempt(self.service, run_id, attempt_id, revisions)
            content = canonical(document).encode('utf-8')
            digest = hashlib.sha256(content).hexdigest()
            relative = 'candidate-inputs/' + digest + '.json'
            path = checked_path(self.service.config.artifact_root / relative, missing=True)
            write_once(path, content)
        return {'version': candidate_origin.VERSION, 'identity': document['identity'],
                'artifact_relative': relative, 'artifact_sha256': digest}

    def read(self, reference):
        path = self.service.artifacts.resolve(reference['artifact_relative'])
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if (reference.get('version') != candidate_origin.VERSION or
                reference['artifact_sha256'] != digest or
                reference['artifact_relative'] != 'candidate-inputs/' + digest + '.json'):
            raise BoundaryError('CANDIDATE_INPUT_IDENTITY_MISMATCH')
        document = json.loads(content)
        scope = document['scope']
        if (document.get('identity') != reference['identity'] or document != inspect_attempt(
                self.service, scope['run_id'], scope['attempt_id'], document.get('revisions'))):
            raise BoundaryError('CANDIDATE_ORIGIN_DRIFT')
        return document

    def inspect(self, run_id):
        """Bounded human range editor input; never exposes paths or raw JSON."""
        from .review import require_safe_projection
        run = self.service.get_run(run_id)
        result = []
        for _, _, catalog, series in self.service.output_batches.inputs(run):
            with self.service.store.connect() as connection:
                attempts = list(connection.execute('''SELECT a.attempt_id FROM bounded_extraction_attempts a
                    JOIN bounded_extraction_segments s ON s.segment_id=a.segment_id
                    JOIN bounded_extraction_outcomes o ON o.attempt_id=a.attempt_id
                    WHERE s.series_id=? ORDER BY a.attempt_id''', (series.series_id,)))
            for attempt in attempts:
                try:
                    doc = inspect_attempt(self.service, run_id, attempt['attempt_id'])
                except ValueError as error:
                    if str(error) != 'CANDIDATE_COMPLETE_JSON_REQUIRED':
                        raise
                    continue
                _, plan, _, _ = self.service.output_batches.ledger.read(series.series_id)
                segment = next(s for s in plan.segments if s.segment_id == doc['scope']['segment_id'])
                result.append({'attempt_id': attempt['attempt_id'], 'identity': doc['identity'],
                    'claims': [{'observation_id': o['observation_id'], 'statement': (o['value'].get('statement', '') if isinstance(o['value'], dict)
                                    and isinstance(o['value'].get('statement', ''), str) else ''),
                                'status': o['status'], 'errors': o['errors']} for o in doc['objects'] if o['family'] == 'claims'],
                    'evidence': [{'evidence_ref': u.evidence_ref, 'source_start': u.source_start,
                                  'source_end': u.source_end, 'text': u.exact_text, 'locator': u.locator}
                                 for u in catalog.units if u.evidence_ref in segment.assigned_evidence_refs]})
        require_safe_projection(result)
        return {'attempts': result}
