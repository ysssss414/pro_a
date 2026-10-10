"""Exact-scope target recovery qualification, explicitly NOT semantic equivalence."""
from dataclasses import dataclass
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

from pro_a.evidence_binding import identity
from pro_a.repository_identity import repository_commit
from pro_a.source_metadata_authority import validate_resolution
from .lossless_recovery import assessment, frozen_worker, require

VERSION = 'lossless-aggregate-target-recovery-qualification-v1'
BASELINE = '56a1e26d1425e5df79585d2b80ad94bc56344af3'
_ISSUER = object()
CHANGED = frozenset(('workbench/source_operations.py', 'workbench/bounded_extraction_store.py',
    'workbench/bounded_source_analysis.py', 'workbench/bounded_resume.py', 'workbench/extraction_retry.py',
    'workbench/retry_compatibility.py', 'workbench/cloud_jobs.py'))
ADDED = frozenset(('claim_observations.py', 'source_metadata_authority.py', 'lossless_aggregate.py',
    'workbench/lossless_runtime.py', 'workbench/lossless_recovery.py', 'workbench/lossless_compatibility.py'))


def package_manifest():
    package = Path(__file__).resolve().parent.parent
    return {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(package.rglob('*')) if p.is_file() and p.suffix in ('.py', '.sql')}


def runtime_contract():
    package = Path(__file__).resolve().parent.parent
    return {'qualification_version': VERSION, 'aggregate_version': 'lossless-sourcepiece-aggregate-v2',
        'recovery_version': 'bounded-lossless-aggregate-recovery-v1',
        'target_only': True, 'semantic_equivalence_claimed': False,
        'module_sha256': {name: hashlib.sha256((package/name).read_bytes()).hexdigest() for name in sorted(CHANGED | ADDED)}}


def git_evidence(repository_root):
    """Use exact Git blobs, with no AST normalization or allow-all surface flag."""
    root = Path(repository_root)
    def git(*args, data=None):
        environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], input=data, env=environment)
    def blobs(commit):
        entries = [line.split('\t', 1) for line in git('ls-tree', '-r', commit, 'src/pro_a').decode().splitlines()
            if line.endswith(('.py', '.sql'))]
        raw = git('cat-file', '--batch', data=('\n'.join(m.split()[2] for m, _ in entries)+'\n').encode())
        offset, result = 0, {}
        for meta, path in entries:
            end = raw.index(b'\n', offset)
            oid, kind, size = raw[offset:end].decode().split()
            offset = end+1
            content = raw[offset:offset+int(size)]
            offset += int(size)+1
            require(kind == 'blob' and oid == meta.split()[2]
                and hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest() == oid,
                'HISTORICAL_EXECUTION_BLOB_INTEGRITY')
            result[path[len('src/pro_a/'):]] = hashlib.sha256(content).hexdigest()
        require(offset == len(raw), 'HISTORICAL_EXECUTION_BLOB_INTEGRITY')
        return result
    target_sha = repository_commit()
    historical, target = blobs(BASELINE), blobs(target_sha)
    require(target == package_manifest(), 'TARGET_GIT_TREE_BYTE_MISMATCH')
    require(set(target) - set(historical) == ADDED and not set(historical) - set(target),
            'STOP_RUN16_AGGREGATE_RUNTIME_INCOMPATIBLE')
    changed = {n for n in historical if historical[n] != target[n]}
    require(changed <= CHANGED and all(target[n] == historical[n] for n in historical if n not in CHANGED),
            'STOP_NATIVE_SEMANTIC_CHANGE_REQUIRED')
    # Read the historical literal hash inventory; never normalize executable ASTs.
    source = git('cat-file', 'blob', BASELINE + ':src/pro_a/workbench/cloud_jobs.py').decode('utf-8')
    function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'runtime_identity')
    names = [ast.literal_eval(n.value) for n in ast.walk(function) if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets)]
    require(len(names) == 1 and all(n in historical for n in names[0]), 'HISTORICAL_EXECUTION_BLOB_INTEGRITY')
    return {'baseline': BASELINE, 'target_commit': target_sha, 'historical_manifest': historical,
        'historical_domain_code_sha256': identity({n: historical[n] for n in names[0]}),
        'target_manifest': target, 'changed_existing_modules': sorted(changed),
        'new_target_only_modules': sorted(ADDED), 'native_and_research_bytes_unchanged': True}


@dataclass(frozen=True)
class LosslessQualification:
    evidence: dict
    issuer: object

    @property
    def identity(self):
        return identity(self.evidence)


def validate_token(token, *, run_id=None, resolution_identity=None):
    require(isinstance(token, LosslessQualification) and token.issuer is _ISSUER,
            'LOSSLESS_QUALIFICATION_REQUIRED')
    evidence = token.evidence
    require(evidence.get('version') == VERSION and evidence['code']['baseline'] == BASELINE,
            'LOSSLESS_QUALIFICATION_STALE')
    require(evidence['code']['target_manifest'] == package_manifest()
        and evidence['code']['target_commit'] == repository_commit()
        and evidence['target_contract'] == runtime_contract(), 'LOSSLESS_QUALIFICATION_TARGET_DRIFT')
    if run_id is not None:
        require(evidence['scope']['run_id'] == run_id, 'LOSSLESS_QUALIFICATION_SCOPE_MISMATCH')
    if resolution_identity is not None:
        require(evidence['resolution_identity'] == resolution_identity, 'LOSSLESS_QUALIFICATION_SCOPE_MISMATCH')
    return evidence


def restore_token(evidence, expected_identity):
    require(identity(evidence) == expected_identity, 'LOSSLESS_QUALIFICATION_IDENTITY_MISMATCH')
    token = LosslessQualification(evidence, _ISSUER)
    validate_token(token)
    return token


def guard_cloud(historical, target, token):
    evidence = validate_continuation(token) if isinstance(token, EvidenceQualification) else validate_token(token)
    require(dict(historical) == evidence['historical_runtime'] and dict(target) == evidence['target_runtime'],
            'LOSSLESS_QUALIFICATION_RUNTIME_MISMATCH')
    require(historical['runtime_sha256'] == identity({k: v for k, v in historical.items() if k != 'runtime_sha256'}),
            'LOSSLESS_HISTORICAL_RUNTIME_IDENTITY_MISMATCH')
    if historical['git_sha'] == BASELINE:
        require(historical['domain_code_sha256'] == evidence['code']['historical_domain_code_sha256']
            and 'lossless_aggregate_recovery' not in historical, 'LOSSLESS_HISTORICAL_RUNTIME_IDENTITY_MISMATCH')
    omitted = {'git_sha', 'runtime_sha256', 'domain_code_sha256', 'lossless_aggregate_recovery'}
    require({k:v for k,v in historical.items() if k not in omitted} == {k:v for k,v in target.items() if k not in omitted},
            'STOP_RUN16_AGGREGATE_RUNTIME_INCOMPATIBLE')


def guard_native(historical, target, token):
    evidence = validate_continuation(token) if isinstance(token, EvidenceQualification) else validate_token(token)
    require(dict(historical) == evidence['historical_native'] and dict(target) == evidence['target_native'],
            'LOSSLESS_QUALIFICATION_NATIVE_MISMATCH')
    require({k:v for k,v in historical.items() if k != 'repository_commit'} ==
            {k:v for k,v in target.items() if k != 'repository_commit'}, 'STOP_NATIVE_SEMANTIC_CHANGE_REQUIRED')


def guard_context(frozen, current_basis, token):
    evidence = validate_continuation(token) if isinstance(token, EvidenceQualification) else validate_token(token)
    require(frozen['context_sha256'] == evidence['scope']['frozen_context_sha256']
        and {k:v for k,v in frozen['basis'].items() if k != 'runtime'} ==
            {k:v for k,v in current_basis.items() if k != 'runtime'}, 'PROCESSING_RUN_CONTEXT_DRIFT')
    guard_cloud(frozen['basis']['runtime'], current_basis['runtime'], token)


def verify_worker(worker, run_id, token):
    from pro_a.config import load_config
    from pro_a.phase4_orchestration import _compatible
    from pro_a.phase4_retry import RetryPolicy
    from .domains import Domains
    evidence = validate_continuation(token, run_id=run_id) if isinstance(token, EvidenceQualification) else validate_token(token, run_id=run_id)
    run = worker.get_run(run_id)
    bindings = worker.output_batches.inputs(run)  # Full Source/event/raw/result chains.
    with worker.store.connect() as connection:
        row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        guard_cloud(json.loads(row['runtime_json']), worker.jobs.current_runtime(), token)
        for original in evidence['scope']['accepted']:
            accepted = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?', (original['segment_id'],)).fetchone()
            outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (original['attempt_id'],)).fetchone()
            require(accepted and outcome and accepted['result_sha256'] == original['result_sha256']
                and accepted['record_sha256'] == original['record_sha256'] and outcome['artifact_sha256'] == original['raw_sha256'],
                'LOSSLESS_RECOVERY_ACCEPTED_RESULT_DRIFT')
    Domains(worker.config).guard(run_id, worker.jobs, worker.profile, runtime_compatibility=token)
    root = worker._native_root(row)
    checkpoint = root / 'commits' / evidence['native_checkpoint']['name']
    require(hashlib.sha256(checkpoint.read_bytes()).hexdigest() == evidence['native_checkpoint']['sha256'],
            'LOSSLESS_NATIVE_CHECKPOINT_DRIFT')
    _compatible(root, row['native_execution_id'], load_config(worker.profile.phase4_config_path),
        RetryPolicy.FORBID_ALL, runtime_compatibility=token)
    if isinstance(token, EvidenceQualification):
        verify_original_lossless(worker, run_id, evidence)
    return bindings


CONTINUATION_VERSION = 'lossless-evidence-regeneration-target-continuation-v1'
CONTINUATION_RELEASE = '3cb834fd98f137883f79248292eb23305cce7235'
_CONTINUATION_ISSUER = object()


@dataclass(frozen=True)
class EvidenceQualification:
    evidence: dict
    sealed_identity: str
    issuer: object

    @property
    def identity(self):
        return identity(self.evidence)


def validate_continuation(token, *, run_id=None):
    from .lossless_recovery import evidence_contract
    require(isinstance(token, EvidenceQualification) and token.issuer is _CONTINUATION_ISSUER,
        'EVIDENCE_CONTINUATION_QUALIFICATION_REQUIRED')
    e = token.evidence
    require(token.identity == token.sealed_identity and e.get('version') == CONTINUATION_VERSION,
        'EVIDENCE_CONTINUATION_TOKEN_DRIFT')
    require(e['code']['target_manifest'] == package_manifest() and e['code']['target_commit'] == repository_commit()
        and e['target_contract'] == runtime_contract() and e['regeneration_contract'] == evidence_contract(),
        'EVIDENCE_CONTINUATION_TARGET_DRIFT')
    require(e['old_code']['target_commit'] == CONTINUATION_RELEASE and e['old_install']['manifest'] == e['old_code']['target_manifest']
        and e['old_install']['commit'] == CONTINUATION_RELEASE, 'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    if run_id is not None:
        require(e['scope']['run_id'] == run_id, 'EVIDENCE_CONTINUATION_SCOPE_MISMATCH')
    return e


def restore_continuation(evidence, expected_identity):
    require(identity(evidence) == expected_identity, 'EVIDENCE_CONTINUATION_TOKEN_DRIFT')
    token = EvidenceQualification(evidence, expected_identity, _CONTINUATION_ISSUER)
    validate_continuation(token)
    return token


def read_continuation_evidence(evidence, expected_identity):
    """Verify durable historical proof without issuing execution authority."""
    from .lossless_recovery import evidence_contract
    require(identity(evidence) == expected_identity and evidence.get('version') == CONTINUATION_VERSION,
        'EVIDENCE_CONTINUATION_TOKEN_DRIFT')
    require(evidence['old_code']['target_commit'] == CONTINUATION_RELEASE
        and evidence['old_install']['manifest'] == evidence['old_code']['target_manifest']
        and evidence['old_install']['commit'] == CONTINUATION_RELEASE,
        'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    require(evidence['regeneration_contract'] == evidence_contract(), 'EVIDENCE_CONTINUATION_TARGET_DRIFT')
    return evidence


def released_install_evidence(repository_root, installed_package):
    """Read the actual released Git tree and wheel RECORD, not a supplied manifest."""
    import base64
    import csv
    import io
    import zipfile
    environment = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    def git(*args):
        return subprocess.check_output(['git', '--no-replace-objects', '-C', str(repository_root), *args], env=environment)
    raw = git('archive', '--format=zip', CONTINUATION_RELEASE, 'src/pro_a')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest = {n[len('src/pro_a/'):]: hashlib.sha256(archive.read(n)).hexdigest()
            for n in archive.namelist() if n.endswith(('.py', '.sql'))}
        cloud = archive.read('src/pro_a/workbench/cloud_jobs.py').decode()
    package = Path(installed_package).resolve()
    installed = {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob('*') if p.is_file() and p.suffix in ('.py', '.sql')}
    require(installed == manifest, 'LOSSLESS_CONTINUATION_RELEASED_BYTES_MISMATCH')
    records = list(package.parent.glob('pro_a-*.dist-info/RECORD'))
    require(len(records) == 1, 'LOSSLESS_CONTINUATION_RELEASED_IDENTITY_INVALID')
    rows = list(csv.reader(io.StringIO(records[0].read_text(encoding='utf-8'))))
    for name in [*manifest, '_build_identity.json']:
        matches = [r for r in rows if r[0] == 'pro_a/' + name]
        content = (package/name).read_bytes()
        encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
        require(len(matches) == 1 and matches[0][1:] == ['sha256='+encoded, str(len(content))],
            'LOSSLESS_CONTINUATION_RELEASED_IDENTITY_INVALID')
    build = json.loads((package/'_build_identity.json').read_bytes())
    require(build == {'contract_version': 'pro-a-build-repository-identity-v1', 'repository': 'ysssss414/pro_a',
        'repository_commit': CONTINUATION_RELEASE}, 'LOSSLESS_CONTINUATION_RELEASED_IDENTITY_INVALID')
    function = next(n for n in ast.parse(cloud).body if isinstance(n, ast.FunctionDef) and n.name == 'runtime_identity')
    names = [ast.literal_eval(n.value) for n in ast.walk(function) if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets)]
    require(len(names) == 1)
    return {'commit': CONTINUATION_RELEASE, 'manifest': manifest, 'build_identity_sha256': identity(build),
        'record_sha256': hashlib.sha256(records[0].read_bytes()).hexdigest(),
        'domain_code_sha256': identity({n:manifest[n] for n in names[0]})}


def verify_original_lossless(worker, run_id, evidence):
    from .lossless_recovery import original_lossless_grant
    from .lossless_runtime import policy, resolution
    ledger = worker.output_batches.ledger
    scope = evidence['scope']
    with worker.store.connect() as connection:
        row, grant, old = original_lossless_grant(worker, connection, run_id)
        require(row == scope['original_grant'] and identity(old) == scope['original_token_identity']
            and old == evidence['original_qualification'], 'LOSSLESS_CONTINUATION_ORIGINAL_TOKEN_DRIFT')
        for series in scope['series']:
            sid = series['series_id']
            policy_grant = policy(connection, sid)
            require(policy_grant['qualification_identity'] == grant['qualification_identity']
                and policy_grant['recovery_contract'] == 'bounded-lossless-aggregate-recovery-v1')
            bound, _, _, _ = ledger._load(connection, sid)
            authority = resolution(ledger, connection, bound)
            validate_resolution(authority, bound_scope=old['scope']['authority_scope'])
            require(authority['identity'] == scope['resolution_identity'], 'LOSSLESS_CONTINUATION_RESOLUTION_DRIFT')
        first = scope['first_aggregate']
        current = connection.execute('SELECT * FROM bounded_extraction_series_results WHERE series_id=?', (first['series_id'],)).fetchone()
        require(current and dict(current) == first, 'LOSSLESS_CONTINUATION_AGGREGATE_DRIFT')
        ledger._read_artifact(first['series_id'], 'aggregate.json', first)
        failed = scope['failed']
        attempt = connection.execute('SELECT * FROM bounded_extraction_attempts WHERE attempt_id=?', (failed['attempt_id'],)).fetchone()
        outcome = connection.execute('SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?', (failed['attempt_id'],)).fetchone()
        require(attempt and attempt['record_sha256'] == failed['attempt_record_sha256']
            and outcome and outcome['artifact_sha256'] == failed['raw_sha256'], 'EVIDENCE_FAILED_ATTEMPT_DRIFT')
        ledger._read_artifact(failed['series_id'], failed['attempt_id'] + '.raw.json', outcome)


def qualify_evidence_regeneration(service, run_id, failed_attempt_id, *, historical_repository_root, released_installed_package):
    from pro_a.phase4_orchestration import _runtime
    from .lossless_recovery import evidence_assessment, original_lossless_grant, evidence_contract, evidence_request_material
    worker = frozen_worker(service, run_id, None)
    bindings = worker.output_batches.inputs(worker.get_run(run_id))
    with worker.store.connect() as connection:
        proof = evidence_assessment(worker, connection, run_id, failed_attempt_id, bindings)
        _, _, old = original_lossless_grant(worker, connection, run_id)
    code = git_evidence(historical_repository_root)
    installed = released_install_evidence(historical_repository_root, released_installed_package)
    require(old['version'] == VERSION and old['code']['baseline'] == BASELINE
        and old['code']['target_commit'] == CONTINUATION_RELEASE
        and old['code']['target_manifest'] == installed['manifest']
        and old['code']['historical_manifest'] == code['historical_manifest']
        and old['code']['historical_domain_code_sha256'] == code['historical_domain_code_sha256'],
        'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    old_contract = {**runtime_contract(), 'module_sha256': {n:installed['manifest'][n] for n in sorted(CHANGED | ADDED)}}
    require(old['target_contract'] == old_contract and old['target_runtime']['lossless_aggregate_recovery'] == old_contract
        and old['target_runtime']['git_sha'] == CONTINUATION_RELEASE
        and old['target_native']['repository_commit'] == CONTINUATION_RELEASE
        and old['historical_runtime']['git_sha'] in (BASELINE, CONTINUATION_RELEASE)
        and old['historical_native']['repository_commit'] == old['historical_runtime']['git_sha']
        and old['target_runtime']['domain_code_sha256'] == installed['domain_code_sha256']
        and old['target_runtime']['runtime_sha256'] == identity({k:v for k,v in old['target_runtime'].items() if k != 'runtime_sha256'}),
        'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    if old['historical_runtime']['git_sha'] == CONTINUATION_RELEASE:
        require(old['historical_runtime']['domain_code_sha256'] == installed['domain_code_sha256']
            and old['historical_runtime']['lossless_aggregate_recovery'] == old_contract,
            'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    # Only the operator/runtime integration may change. Research/Native/Binding
    # bytes are compared directly against both actual historical Git trees.
    allowed = {'workbench/lossless_recovery.py', 'workbench/lossless_compatibility.py'} | CHANGED
    require(set(installed['manifest']) == set(code['target_manifest'])
        and all(code['target_manifest'][n] == h for n,h in installed['manifest'].items() if n not in allowed),
        'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    for a in old['scope']['accepted']:
        require(any(all(b.get(k) == v for k,v in a.items() if k != 'configuration_sha256') for b in proof['accepted']))
    evidence = {'version': CONTINUATION_VERSION, 'scope': proof, 'original_qualification': old,
        'old_code': old['code'], 'old_install': installed, 'code': code, 'target_contract': runtime_contract(),
        'historical_runtime': old['historical_runtime'], 'target_runtime': worker.jobs.current_runtime(),
        'historical_native': old['historical_native'], 'target_native': _runtime(), 'native_checkpoint': old['native_checkpoint'],
        'regeneration_contract': evidence_contract(), 'change_classification': 'EXACT_SCOPE_TARGET_ONLY_CONTINUATION_NOT_SEMANTIC_EQUIVALENCE'}
    omitted = {'git_sha', 'runtime_sha256', 'domain_code_sha256', 'lossless_aggregate_recovery'}
    require({k:v for k,v in old['target_runtime'].items() if k not in omitted} ==
        {k:v for k,v in evidence['target_runtime'].items() if k not in omitted}, 'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    require({k:v for k,v in old['target_native'].items() if k != 'repository_commit'} ==
        {k:v for k,v in evidence['target_native'].items() if k != 'repository_commit'}, 'STOP_LOSSLESS_CONTINUATION_RUNTIME_INCOMPATIBLE')
    evidence['new_request'] = evidence_request_material(worker, proof, bindings)[0]
    token = EvidenceQualification(evidence, identity(evidence), _CONTINUATION_ISSUER)
    verify_worker(frozen_worker(service, run_id, token), run_id, token)
    return token


def qualify_recovery(service, run_id, resolution, *, historical_repository_root):
    from pro_a.phase4_orchestration import _runtime
    validate_resolution(resolution)
    worker = frozen_worker(service, run_id, None)
    run = worker.get_run(run_id)
    bindings = worker.output_batches.inputs(run)
    with worker.store.connect() as connection:
        proof = assessment(worker, connection, run_id, bindings)
        row = connection.execute('SELECT * FROM source_processing_runs WHERE processing_run_id=?', (run_id,)).fetchone()
        historical = json.loads(row['runtime_json'])
    validate_resolution(resolution, bound_scope=proof['authority_scope'])
    from pro_a.lossless_aggregate import build_aggregate
    from .lossless_runtime import accepted_results
    _, context, catalog, series = bindings[0]
    with worker.output_batches.ledger._connection() as connection:
        _, plan, _, _ = worker.output_batches.ledger._load(connection, series.series_id)
        results = accepted_results(worker.output_batches.ledger, connection, series, plan)
    aggregate = build_aggregate(proof['source_id'], series, plan, results, catalog, context, resolution)
    root = worker._native_root(row)
    native = json.loads((root / 'execution_identity.json').read_text(encoding='utf-8'))
    manifest = json.loads((root / 'execution_manifest.json').read_text(encoding='utf-8'))
    require(manifest['state'] == 'SOURCE_READY', 'LOSSLESS_NATIVE_CHECKPOINT_NOT_ELIGIBLE')
    name = f"{manifest['sequence']:06}.json"
    code = git_evidence(historical_repository_root)
    require(historical['git_sha'] in (BASELINE, code['target_commit']), 'LOSSLESS_HISTORICAL_RUNTIME_NOT_SUPPORTED')
    evidence = {'version': VERSION, 'scope': proof, 'resolution_identity': resolution['identity'],
        'accepted_aggregate_identity': aggregate['identity'],
        'accepted_observation_ledger_identity': aggregate['observation_ledger']['identity'],
        'code': code, 'target_contract': runtime_contract(), 'historical_runtime': historical,
        'target_runtime': worker.jobs.current_runtime(), 'historical_native': native['runtime'],
        'target_native': _runtime(), 'native_checkpoint': {'name': name,
            'sha256': hashlib.sha256((root/'commits'/name).read_bytes()).hexdigest()},
        'change_classification': 'EXPLICIT_VERSIONED_TARGET_RECOVERY_NOT_EXECUTION_EQUIVALENCE'}
    token = LosslessQualification(evidence, _ISSUER)
    worker = frozen_worker(service, run_id, token)
    verify_worker(worker, run_id, token)
    return token
