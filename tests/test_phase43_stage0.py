from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import os
import subprocess

import pytest

from pro_a.cloud_contract import DeterministicFakeProvider
from pro_a.domain_packs import canonical, compose, digest, load_pack, read_json
from pro_a.run_context import freeze_context, guard_resume, validate_context
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.domains import Domains, prepare_domains, rollback_domains
from pro_a.workbench.source_operations import SourceOperationError, SourceOperations
from pro_a.workbench.store import Store
from test_workbench_stage7 import clean_pdf, upload, start_and_finish
from workbench_stage7_fixture import stage7_fixture

ROOT = Path(__file__).resolve().parents[1]


def write_manifest(root, value):
    (root / 'pack.json').write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def pack_root(tmp_path):
    destination = tmp_path / 'pack'
    shutil.copytree(ROOT / 'domains/ai_hardware', destination)
    return destination


def test_pack_hash_and_copy_isolation(pack_root):
    first = load_pack(pack_root)
    value = first.manifest
    value['supported_node_types'].reverse()
    value = dict(reversed(list(value.items())))
    write_manifest(pack_root, value)
    assert load_pack(pack_root).sha256 == first.sha256
    value['description'] = 'Changed semantic descriptor'
    write_manifest(pack_root, value)
    assert load_pack(pack_root).sha256 != first.sha256
    assert first.manifest['description'] != value['description']


@pytest.mark.parametrize('change', [
    'unknown', 'missing', 'schema', 'version', 'node_type', 'relation', 'system_override',
    'admission', 'impact', 'view', 'pattern', 'inventory_hash', 'missing_ref', 'path', 'absolute',
    'windows_path', 'duplicate', 'nan', 'unlisted', 'missing_file', 'symlink', 'hardlink', 'oversize',
])
def test_pack_rejects_unsafe_declarations(pack_root, change):
    value = read_json(pack_root / 'pack.json')
    if change == 'unknown': value['execute'] = 'something'
    elif change == 'missing': del value['references']
    elif change == 'schema': value['compatibility']['canonical_schema'] = '0.2.4'
    elif change == 'version': value['version'] = '2.0.0'
    elif change == 'node_type': value['supported_node_types'].append('Semiconductor')
    elif change == 'relation': value['supported_relations'].append('launches')
    elif change == 'system_override': value['semantic_decomposition']['system'] = 'Override'
    elif change == 'admission': value['admission_policy']['mode'] = 'accept_all'
    elif change == 'impact': value['impact_policy']['mode'] = 'infer_beneficiaries'
    elif change == 'view': value['current_view_hints'] = {'Technology': {}}
    elif change == 'pattern': value['claim_pattern_hints'] = [{'id': 'unsupported'}]
    elif change == 'inventory_hash': value['file_inventory'][0]['sha256'] = '0' * 64
    elif change == 'missing_ref': value['references']['source_policy'] = 'missing.txt'
    elif change == 'path': value['file_inventory'][0]['path'] = '../outside.json'
    elif change == 'absolute': value['file_inventory'][0]['path'] = '/outside.json'
    elif change == 'windows_path': value['file_inventory'][0]['path'] = 'C:\\outside.json'
    elif change == 'unlisted': (pack_root / 'code.py').write_text('pass')
    elif change == 'missing_file': (pack_root / 'policy.json').unlink()
    elif change == 'symlink':
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(pack_root / 'link'), str(pack_root.parent)], capture_output=True)
            assert result.returncode == 0
        else:
            (pack_root / 'link').symlink_to(pack_root / 'policy.json')
    elif change == 'hardlink': (pack_root / 'link.json').hardlink_to(pack_root / 'policy.json')
    write_manifest(pack_root, value)
    if change == 'duplicate': (pack_root / 'pack.json').write_text('{"domain_id":"a","domain_id":"b"}')
    if change == 'nan': (pack_root / 'pack.json').write_text('{"x":NaN}')
    if change == 'oversize': (pack_root / 'pack.json').write_text(' ' * (1024 * 1024 + 1))
    with pytest.raises(BoundaryError): load_pack(pack_root)


def test_composition_order_conflicts_and_union(pack_root, tmp_path):
    other = tmp_path / 'other'
    shutil.copytree(pack_root, other)
    a = read_json(pack_root / 'pack.json')
    b = deepcopy(a)
    b['domain_id'] = 'semiconductor'
    for value, label in [(a, 'Alpha'), (b, 'Beta')]:
        value['normalization_candidates'] = [{'surface': 'Shared', 'preferred_label': label,
            'node_type': 'Product', 'ambiguity_group': 'test', 'source_local_equivalence_required': True}]
    write_manifest(pack_root, a)
    write_manifest(other, b)
    packs = [load_pack(pack_root), load_pack(other)]
    result = compose(packs, 'ai_hardware')
    assert result == compose(list(reversed(packs)), 'ai_hardware')
    assert result['disposition'] == 'DEFER' and result['conflicts'] == ['NORMALIZATION:Shared']
    assert result['identity_scope'] == 'GLOBAL_CANONICAL'
    with pytest.raises(BoundaryError): compose([packs[0], packs[0]], 'ai_hardware')


def setup_source(tmp_path, *, legacy=False):
    case = stage7_fixture(tmp_path)
    if not legacy:
        prepare_domains(case['config'])
    case['service'] = SourceOperations(case['config'], case['source_profile'], case['cloud_profile'])
    source = upload(case, clean_pdf(tmp_path))
    if not legacy:
        domains = Domains(case['config'])
        packs = [domains.register(ROOT / 'domains' / name) for name in ('ai_hardware', 'semiconductor')]
        domains.assign('Source', source['source_id'], primary_domain='ai_hardware', packs=packs,
                       actor='synthetic-operator', reason='Synthetic offline contract test', expected_revision=0)
    return case, source


def start(case, source, key='stage43-contract-run-0001', reason=''):
    return case['service'].start(source['source_id'], idempotency_key=key, reprocess_reason=reason)['run']['processing_run_id']


def test_context_idempotency_restart_and_assignment(tmp_path):
    case, source = setup_source(tmp_path)
    run = start(case, source)
    domains = Domains(case['config'])
    frozen = domains.read(run)
    assert frozen['basis']['composition']['primary_domain'] == 'ai_hardware'
    assert len(frozen['basis']['composition']['packs']) == 2
    assert start(case, source, key='stage43-contract-run-0002') == run
    case['service'] = SourceOperations(case['config'], case['source_profile'], case['cloud_profile'])
    assert start(case, source) == run
    assert case['service'].get_run(run)['domain_context'] == frozen
    reordered = dict(reversed(list(frozen['basis'].items())))
    guard_resume(frozen, reordered)
    assert freeze_context(reordered, run_id=frozen['run_id'], created_at=frozen['created_at'],
                          actor=frozen['actor'], reason=frozen['reason']) == frozen
    with Store(case['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM private_sources').fetchone()[0] == 1
        assert connection.execute('SELECT COUNT(*) FROM source_processing_runs').fetchone()[0] == 1
    with pytest.raises(BoundaryError, match='STALE'):
        domains.assign('Source', source['source_id'], primary_domain='ai_hardware',
                       packs=frozen['basis']['composition']['packs'], actor='operator', reason='stale', expected_revision=0)


@pytest.mark.parametrize('field', ['pack', 'prompt', 'runtime', 'config', 'model'])
def test_resume_guard_each_axis(tmp_path, field, monkeypatch):
    case, source = setup_source(tmp_path)
    run = start(case, source)
    frozen = Domains(case['config']).read(run)
    current = deepcopy(frozen['basis'])
    if field == 'pack': current['composition']['packs'][0]['sha256'] = '1' * 64
    if field == 'prompt': current['prompt_sha256'] = '1' * 64
    if field == 'config': current['config_sha256'] = '1' * 64
    if field == 'runtime':
        current['runtime']['git_sha'] = '1' * 40
        current['runtime']['runtime_sha256'] = digest({k:v for k,v in current['runtime'].items() if k != 'runtime_sha256'})
    if field == 'model':
        current['model_configuration']['requested_model'] = 'different-model'
        current['model_configuration']['configuration_sha256'] = digest({k:v for k,v in current['model_configuration'].items() if k != 'configuration_sha256'})
    with pytest.raises(BoundaryError, match='DRIFT'): guard_resume(frozen, current)


def test_config_drift_blocks_source_and_direct_job(tmp_path):
    case, source = setup_source(tmp_path)
    run = start(case, source)
    provider = DeterministicFakeProvider()
    result = case['service'].advance_once(worker_id='domain-worker', provider=provider, processing_run_id=run)
    assert result['state'] == 'EXTRACTION_PROCESSING'
    job = result['jobs'][0]['job_id']
    path = case['phase4_config']
    path.write_text(path.read_text(encoding='utf-8').replace('max_nodes_in_prompt = 500','max_nodes_in_prompt = 499'), encoding='utf-8')
    blocked = case['service'].jobs.run_once(provider, worker_id='domain-worker', job_id=job)
    assert blocked['status'] != 'SUCCEEDED' and provider.call_count == 0
    result = case['service'].advance_once(worker_id='domain-worker', provider=provider, processing_run_id=run)
    assert result['state'] == 'BLOCKED' and provider.call_count == 0
    with pytest.raises(SourceOperationError, match='IDEMPOTENCY_CONFLICT'): start(case, source)
    with pytest.raises(SourceOperationError, match='REPROCESS_REASON'): start(case, source, key='stage43-contract-run-0002')
    assert start(case, source, key='stage43-contract-run-0003', reason='Explicit configuration change') != run


def test_schema9_full_fake_path_and_review_binding(tmp_path):
    case, source = setup_source(tmp_path)
    run = start(case, source)
    provider = DeterministicFakeProvider()
    for _ in range(3):
        result = case['service'].advance_once(worker_id='domain-worker', provider=provider, processing_run_id=run)
    assert result['state'] == 'HUMAN_REVIEW_REQUIRED', result
    assert provider.call_count == 2
    domains = Domains(case['config'])
    domains.validate_packet(result['packet_artifact_id'])
    for job in result['jobs']:
        assert job['native_checkpoint']['domain_context']['context_sha256'] == result['domain_context']['context_sha256']
    with Store(case['config']).connect() as connection:
        row = connection.execute('SELECT * FROM domain_packet_bindings').fetchone()
        companion = case['config'].artifact_root / row['companion_relative']
    companion.write_text('{}', encoding='utf-8')
    with pytest.raises(BoundaryError, match='COMPANION_CORRUPT'):
        case['service'].artifacts.native(result['packet_artifact_id'])


def test_missing_context_fails_closed(tmp_path):
    case, source = setup_source(tmp_path)
    run = start(case, source)
    with Store(case['config']).connect() as connection:
        binding = connection.execute('SELECT * FROM domain_run_bindings').fetchone()
    path = case['config'].artifact_root / binding['artifact_relative']
    before = path.read_bytes()
    path.write_text('{}')
    with pytest.raises(BoundaryError): Domains(case['config']).read(run)
    path.write_bytes(before)
    path.unlink()
    with pytest.raises(BoundaryError): Domains(case['config']).read(run)


def test_registry_immutable_and_append_only(tmp_path, pack_root):
    case = stage7_fixture(tmp_path / 'case')
    prepare_domains(case['config'])
    domains = Domains(case['config'])
    identity = domains.register(pack_root)
    assert domains.register(pack_root) == identity
    value = read_json(pack_root / 'pack.json')
    value['description'] = 'Changed same-version content'
    write_manifest(pack_root, value)
    with pytest.raises(BoundaryError, match='IMMUTABLE'): domains.register(pack_root)
    with Store(case['config']).connect(operator_write=True) as connection:
        with pytest.raises(sqlite3.IntegrityError, match='APPEND_ONLY'):
            connection.execute('DELETE FROM domain_pack_registry')


def test_migration_exact_rollback_and_legacy_bytes(tmp_path):
    case = stage7_fixture(tmp_path)
    knowledge = case['config'].knowledge_db.read_bytes()
    before = case['config'].state_db.read_bytes()
    artifacts = {p.relative_to(case['config'].artifact_root):p.read_bytes()
                 for p in case['config'].artifact_root.rglob('*') if p.is_file()}
    receipt = prepare_domains(case['config'])
    assert receipt['backup_sha256'] == hashlib.sha256(before).hexdigest()
    assert prepare_domains(case['config'])['status'] == 'ALREADY_PREPARED'
    with Store(case['config']).connect() as connection:
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
        assert connection.execute("SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == '9'
    assert rollback_domains(case['config'])['schema_version'] == '8'
    assert case['config'].state_db.read_bytes() == before
    assert case['config'].knowledge_db.read_bytes() == knowledge
    assert artifacts == {p.relative_to(case['config'].artifact_root):p.read_bytes()
                         for p in case['config'].artifact_root.rglob('*') if p.is_file()}


def test_legacy_run_is_not_backfilled_and_migration_requires_drain(tmp_path):
    case, source = setup_source(tmp_path, legacy=True)
    run = start(case, source)
    with pytest.raises(BoundaryError, match='DRAIN'): prepare_domains(case['config'])
    case['service']._transition(run, 'BLOCKED', 'SYNTHETIC_OFFLINE_STOP')
    prepare_domains(case['config'])
    assert case['service'].get_run(run)['domain_context_status'] == 'LEGACY_NO_DOMAIN_CONTEXT'
    assert Domains(case['config']).read(run) is None
    with Store(case['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM domain_run_bindings').fetchone()[0] == 0


def test_rollback_refuses_used_state(tmp_path):
    case, _ = setup_source(tmp_path)
    with pytest.raises(BoundaryError, match='STATE_CHANGED'): rollback_domains(case['config'])


SPEC_PATHS = [ROOT / 'tests/fixtures/domain_core_specs.json'] + sorted((ROOT / 'domains').glob('*/fixtures.json'))
SPECS = [case for path in SPEC_PATHS for case in read_json(path)['cases']]


@pytest.mark.parametrize('case', SPECS, ids=lambda case: case['case_id'])
def test_acceptance_spec_skeleton(case):
    assert len(SPECS) == 120 and len({item['case_id'] for item in SPECS}) == 120
    assert case['qualification_status'] == 'PENDING_HUMAN_GOLD'
    assert case['source_sha256'] is case['expected_outcome'] is case['reviewer'] is None
    assert case['material'] == 'SYNTHETIC_SPEC_ONLY'
    for domain in case['domain_ids']:
        pack = load_pack(ROOT / 'domains' / domain)
        assert pack.manifest['lifecycle']['state'] == 'PROPOSED'

def test_migration_preserves_sealed_review(tmp_path):
    from uuid import uuid4
    from pro_a.workbench.review_workbench import ReviewWorkbench
    case = stage7_fixture(tmp_path)
    _, _, result, _ = start_and_finish(case, clean_pdf(tmp_path))
    handle = result['packet_artifact_id']
    service = ReviewWorkbench(case['config'])
    view = service.read(handle)
    kinds = {item['candidate_id']:item['candidate_type'] for item in view['items']}
    revision = 0
    identity = {'actor':'synthetic-operator', 'session_id':'stage43-offline'}
    for row in view['review']['rows']:
        outcome = service.mutate(handle, 'decision', {
            'basis_id':view['review']['basis_id'], 'expected_revision':revision,
            'operation_id':uuid4().hex, 'candidate_id':row['candidate_id'],
            'decision':'KEEP' if kinds[row['candidate_id']] == 'CLAIM' else 'CREATE',
            'target_node_id':'', 'reviewer':'Synthetic reviewer', 'reason':'Synthetic explicit decision'}, identity)
        revision = outcome['revision']
    service.mutate(handle, 'seal', {'basis_id':view['review']['basis_id'], 'expected_revision':revision,
        'operation_id':uuid4().hex, 'reviewer':'Synthetic reviewer', 'reason':'Synthetic seal', 'confirm':True}, identity)
    with Store(case['config']).connect() as connection:
        sealed_before = [tuple(row) for row in connection.execute('SELECT * FROM sealed_review_artifacts')]
    assert sealed_before
    before = case['config'].state_db.read_bytes()
    prepare_domains(case['config'])
    assert service.read(handle)['review']['status'] == 'SEALED'
    with Store(case['config']).connect() as connection:
        assert sealed_before == [tuple(row) for row in connection.execute('SELECT * FROM sealed_review_artifacts')]
    # Inspecting sealed state does not modify it, so immediate exact rollback remains possible.
    rollback_domains(case['config'])
    assert case['config'].state_db.read_bytes() == before
    assert service.read(handle)['review']['status'] == 'SEALED'


@pytest.mark.parametrize('axis', ['model', 'prompt', 'runtime', 'pack'])
def test_actual_source_resume_axes(tmp_path, monkeypatch, axis):
    from pro_a.workbench import domains as domain_module
    case, source = setup_source(tmp_path)
    run = start(case, source)
    if axis == 'model':
        case['service'].jobs.profile = replace(case['cloud_profile'], requested_model='changed-model')
    elif axis == 'prompt':
        monkeypatch.setattr(domain_module, 'prompt_digest', lambda:'f' * 64)
    elif axis == 'runtime':
        runtime = deepcopy(case['service'].jobs.current_runtime())
        runtime['git_sha'] = 'a' * 40
        runtime['runtime_sha256'] = digest({k:v for k,v in runtime.items() if k != 'runtime_sha256'})
        case['service'].jobs._runtime_override = runtime
    else:
        original = domain_module.load_pack
        def changed(root):
            pack = original(root)
            return replace(pack, sha256='f' * 64)
        monkeypatch.setattr(domain_module, 'load_pack', changed)
    provider = DeterministicFakeProvider()
    blocked = case['service'].advance_once(worker_id='domain-worker', provider=provider, processing_run_id=run)
    assert blocked['state'] == 'BLOCKED' and provider.call_count == 0
    with pytest.raises((BoundaryError, SourceOperationError)):
        start(case, source)


def test_pack_revision_new_run_and_old_context(tmp_path):
    case, source = setup_source(tmp_path)
    old_run = start(case, source)
    domains = Domains(case['config'])
    frozen = domains.read(old_run)
    packs = [domains.register(ROOT / 'domains/ai_hardware')]
    domains.assign('Source', source['source_id'], primary_domain='ai_hardware', packs=packs,
                   actor='operator', reason='Explicit narrower domain scope', expected_revision=1)
    with pytest.raises(SourceOperationError, match='REPROCESS_REASON'):
        start(case, source, key='stage43-domain-revision-0002')
    new_run = start(case, source, key='stage43-domain-revision-0002', reason='Explicit narrower scope')
    assert new_run != old_run and domains.read(old_run) == frozen
    assert domains.guard(old_run, case['service'].jobs, case['source_profile'])
    with Store(case['config']).connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM private_sources').fetchone()[0] == 1


def test_nonfake_dispatch_rejected_before_call(tmp_path):
    case, source = setup_source(tmp_path)
    run = start(case, source)
    fake = DeterministicFakeProvider()
    first = case['service'].advance_once(worker_id='domain-worker', provider=fake, processing_run_id=run)
    class UnexpectedProvider:
        provider_identity = fake.provider_identity
        adapter_version = fake.adapter_version
        def invoke(self, request):
            pytest.fail('Stage 0 must never dispatch to an unqualified provider')
    blocked = case['service'].jobs.run_once(UnexpectedProvider(), worker_id='domain-worker', job_id=first['jobs'][0]['job_id'])
    assert blocked['status'] != 'SUCCEEDED'
    assert 'DOMAIN_ACTIVATION_REQUIRED' in canonical(blocked)


def test_hints_budget_and_nested_order(pack_root, tmp_path):
    value = read_json(pack_root / 'pack.json')
    value['source_analysis_hints']['max_chars'] = 2001
    write_manifest(pack_root, value)
    with pytest.raises(BoundaryError): load_pack(pack_root)
    value['source_analysis_hints']['max_chars'] = 2000
    value['relation_policies'] = [{'relation_type':'uses','from_types':['Product','Equipment'],
        'to_types':['Technology','Product'],'scope_required':True,'temporal_review_required':True,'examples_ref':'hints.txt'}]
    write_manifest(pack_root, value)
    first = load_pack(pack_root)
    value['relation_policies'][0]['from_types'].reverse()
    write_manifest(pack_root, value)
    assert load_pack(pack_root).sha256 == first.sha256
    second = tmp_path / 'second'
    third = tmp_path / 'third'
    packs = [first]
    for target, domain in [(second,'second_domain'),(third,'third_domain')]:
        shutil.copytree(pack_root,target)
        value['domain_id'] = domain
        write_manifest(target,value)
        packs.append(load_pack(target))
    with pytest.raises(BoundaryError, match='COMBINED_HINT_TOO_LONG'): compose(packs,'ai_hardware')


@pytest.mark.parametrize('change', ['unknown','missing','version','timestamp','checksum'])
def test_context_manifest_rejects_corruption(tmp_path, change):
    case, source = setup_source(tmp_path)
    frozen = Domains(case['config']).read(start(case,source))
    if change == 'unknown': frozen['extra'] = True
    elif change == 'missing': del frozen['basis']
    elif change == 'version': frozen['contract_version'] = 'unsupported'
    elif change == 'timestamp': frozen['created_at'] = 'invalid'
    else: frozen['context_sha256'] = '0' * 64
    with pytest.raises(BoundaryError): validate_context(frozen)