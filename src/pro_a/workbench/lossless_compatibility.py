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
    evidence = validate_token(token)
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
    evidence = validate_token(token)
    require(dict(historical) == evidence['historical_native'] and dict(target) == evidence['target_native'],
            'LOSSLESS_QUALIFICATION_NATIVE_MISMATCH')
    require({k:v for k,v in historical.items() if k != 'repository_commit'} ==
            {k:v for k,v in target.items() if k != 'repository_commit'}, 'STOP_NATIVE_SEMANTIC_CHANGE_REQUIRED')


def guard_context(frozen, current_basis, token):
    evidence = validate_token(token)
    require(frozen['context_sha256'] == evidence['scope']['frozen_context_sha256']
        and {k:v for k,v in frozen['basis'].items() if k != 'runtime'} ==
            {k:v for k,v in current_basis.items() if k != 'runtime'}, 'PROCESSING_RUN_CONTEXT_DRIFT')
    guard_cloud(frozen['basis']['runtime'], current_basis['runtime'], token)


def verify_worker(worker, run_id, token):
    from pro_a.config import load_config
    from pro_a.phase4_orchestration import _compatible
    from pro_a.phase4_retry import RetryPolicy
    from .domains import Domains
    evidence = validate_token(token, run_id=run_id)
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
    return bindings


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
