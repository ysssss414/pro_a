"""Read-only salvage of accepted output batches; never a resume qualification.

Keep failed aggregation separate from durable Provider results. Metadata votes,
exact excerpts and repeated statements cannot authorize semantic admission.
"""
import copy
import hashlib
import json
import re
from collections import defaultdict

from pro_a.evidence_binding import identity
from pro_a.output_decomposition import record_to_result
from pro_a.source_metadata_authority import FIELDS, candidate_resolution, scope
from .candidate_inputs import CandidateArchive, inspect_attempt
from .config import BoundaryError
from .domains import Domains

VERSION = 'accepted-output-forensic-projection-v1'


def require(value, code):
    if not value:
        raise BoundaryError(code)


def project_claims(documents):
    """Diagnostic grouping only. Semantic support is deliberately never inferred."""
    rows, groups, seen = [], defaultdict(list), set()
    for document in documents:
        for obj in document['objects']:
            if obj['family'] != 'claims':
                continue
            oid = obj['observation_id']
            require(oid not in seen, 'FORENSIC_DUPLICATE_OBSERVATION')
            seen.add(oid)
            require(obj['evidence'] and not obj['errors'], 'FORENSIC_INCOMPLETE_EVIDENCE')
            evidence = copy.deepcopy(obj['evidence'])
            for item in evidence:
                pointer = set(re.findall(r'PAGE:(\d+)', item['evidence_pointer']))
                locator = set(re.findall(r'PAGE:(\d+)', item['source_locator']))
                item['pointer_locator_conflict'] = bool(pointer and locator and not pointer & locator)
            statement = obj['value']['statement']
            key = identity(statement)  # no inferred subject/time/semantic equivalence
            groups[key].append(oid)
            rows.append({'observation_id': oid, 'statement': statement,
                'scope': copy.deepcopy(document['scope']), 'evidence': evidence,
                'text_group': key, 'semantic_status': 'UNCERTAIN',
                'production_admission': 'NOT_AUTHORIZED'})
    return {'claims': rows, 'text_groups': dict(groups)}


def inspect_accepted_run(config, run_id, *, expected_runtime_sha256, expected_context_sha256):
    """Validate persisted records and reconstruct accepted results without writes.

    Expected identities pin the *recorded* runtime/context for forensics. This
    does not qualify the executing Python runtime to continue the frozen run.
    Unknown or incomplete dispatches fail closed. Callers must retain snapshots.
    """
    archive = CandidateArchive(config)
    ledger = archive.output_batches.ledger
    with archive.store.connect() as db:
        # A read transaction also prevents commit interleaving on DELETE journals.
        db.execute('BEGIN')
        version = db.execute('PRAGMA data_version').fetchone()[0]
        stored = db.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        require(stored is not None, 'FORENSIC_RUN_NOT_FOUND')
        require(stored['state'] == 'BLOCKED' and stored['error_code'] == 'SOURCE_METADATA_CONFLICT',
                'FORENSIC_RUN_NOT_METADATA_BLOCKED')
        run = archive.get_run(run_id)
        require(run['runtime_identity']['runtime_sha256'] == expected_runtime_sha256, 'FORENSIC_RUNTIME_DRIFT')
        frozen = Domains(config).read(run_id, connection=db)
        require(frozen is not None and frozen['context_sha256'] == expected_context_sha256,
                'FORENSIC_CONTEXT_DRIFT')
        require(run['runtime_identity'] == frozen['basis']['runtime'],
                'FORENSIC_RUNTIME_CONTEXT_MISMATCH')
        bindings = archive.output_batches.inputs(run)
        documents, batches, pieces, shas, evidence = [], [], [], [], []
        for value, context, catalog, series in bindings:
            _, plan, _, usage = ledger.read(series.series_id)
            require(usage.unknown_usage_calls == 0, 'FORENSIC_UNKNOWN_PROVIDER_OUTCOME')
            pieces.append({'source_piece_id': context.piece.piece_id,
                'series_id': series.series_id, 'series_sha256': series.series_sha256})
            known_raws = set()
            for segment in plan.leaves:
                attempts = db.execute('SELECT * FROM bounded_extraction_attempts WHERE segment_id=?', (segment.segment_id,)).fetchall()
                result_row = db.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (segment.segment_id,)).fetchone()
                batch = {'series_id': series.series_id, 'segment_id': segment.segment_id,
                    'assigned_evidence_refs': list(segment.assigned_evidence_refs)}
                if not attempts:
                    require(result_row is None, 'FORENSIC_RESULT_WITHOUT_ATTEMPT')
                    batch.update(status='NEVER_CALLED', provider_calls=0)
                else:
                    # This small projection supports accepted, single-attempt leaves.
                    # It does not reinterpret retry/regeneration histories.
                    require(len(attempts) == 1 and result_row is not None, 'FORENSIC_UNSUPPORTED_ATTEMPT_HISTORY')
                    attempt = attempts[0]
                    outcome = db.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (attempt['attempt_id'],)).fetchone()
                    require(outcome is not None, 'FORENSIC_UNKNOWN_PROVIDER_OUTCOME')
                    name = attempt['attempt_id'] + '.raw.json'
                    known_raws.add(name)
                    _, raw = ledger._decode_envelope(attempt, ledger._read_artifact(series.series_id, name, outcome))
                    request = json.loads(attempt['request_json'])
                    result = ledger._result(series.series_id, result_row)
                    require(result == record_to_result(raw.decode('utf-8'), series, segment, catalog, context,
                        record_version=request['provider_record_version']), 'FORENSIC_RAW_RESULT_MISMATCH')
                    payload = archive.output_batches.segment_payload(value, context, catalog, series, segment)
                    require(identity(payload) == request['payload_sha256'], 'FORENSIC_PAYLOAD_DRIFT')
                    document = inspect_attempt(archive, run_id, attempt['attempt_id'])
                    for obj in document['objects']:
                        for item in obj['evidence']:
                            excerpt = context.piece.source_text[item['source_start']:item['source_end']]
                            require(hashlib.sha256(excerpt.encode()).hexdigest() == item['raw_excerpt_sha256'],
                                    'FORENSIC_SOURCE_POSITION_MISMATCH')
                    documents.append(document)
                    shas.append(result.result_sha256)
                    metadata = json.loads(result.wire_json)['source_metadata']
                    evidence.extend({'field': field, 'kind': 'MODEL_DERIVED_UNCONFIRMED',
                        'value': metadata[field], 'source_sha256': run['source_sha256'],
                        'evidence': {'segment_id': segment.segment_id, 'result_sha256': result.result_sha256}}
                        for field in FIELDS)
                    batch.update(status='ACCEPTED_PRESERVED', provider_calls=1,
                        attempt_id=attempt['attempt_id'], result_sha256=result.result_sha256,
                        raw_sha256=outcome['artifact_sha256'], metadata=metadata)
                batches.append(batch)
            require({p.name for p in ledger._path(series.series_id, 'unused').parent.glob('*.raw.json')} == known_raws,
                    'FORENSIC_UNREGISTERED_RAW')
        require(documents, 'FORENSIC_NO_ACCEPTED_RESULTS')
        projected = project_claims(documents)
        require(db.execute('PRAGMA data_version').fetchone()[0] == version, 'FORENSIC_CONCURRENT_CHANGE')
    body = {'version': VERSION, 'run_id': run_id, 'source_id': run['source_id'],
        'source_sha256': run['source_sha256'], 'recorded_runtime_sha256': expected_runtime_sha256,
        'context_sha256': expected_context_sha256, 'batches': batches, **projected,
        'metadata_candidate': candidate_resolution(scope(run_id, run['source_id'], run['source_sha256'], pieces, shas), evidence),
        'status': 'SALVAGE_ONLY', 'resume_authorized': False, 'canonical_permission': False,
        'new_provider_calls': 0, 'writes': 0}
    return {**body, 'identity': identity(body)}
