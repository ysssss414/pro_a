"""Envelope authority is external to the payload; public synthetic fixtures."""
import copy
from dataclasses import replace
import hashlib
import json

import pytest

from test_phase3f_foundation_baseline import case, handoff
from pro_a.production_promotion import (
    PromotionError, validate_payload, validate_payload_artifact, canonical_sha256, payload_semantic_body,
    apply_payload_to_shadow, validate_executable_operations,
)
from pro_a.foundation_payload_envelope import (
    completed_semantic_sha256, verify_completed_artifact, verify_payload_review_basis, BOUND_CONTRACT,
)
from pro_a.phase3f_foundation_baseline import build_foundation_handoff, validate_foundation_payload


@pytest.fixture
def diagnostic(case):
    case['payload'] = handoff(case)['payload']
    return case


def serialize(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')


def reseal(payload):
    sha = canonical_sha256(payload_semantic_body(payload))
    payload.update(payload_hash=sha, payload_id='PROMO_' + sha[:16].upper())
    return payload


def verify_bytes(payload, verification):
    data = serialize(payload)
    return validate_payload_artifact(data, expected_payload_file_sha256=hashlib.sha256(data).hexdigest(), **verification)


def test_foundation_cannot_validate_without_external_basis(case):
    payload = handoff(case)['payload']
    with pytest.raises(PromotionError, match='TRUSTED_VERIFICATION_BASIS_REQUIRED'):
        validate_payload(payload)


def test_correct_artifact_and_three_way_identity(diagnostic):
    p, v = diagnostic['payload'], diagnostic['verification']
    actual, bound = verify_completed_artifact(v['verification_basis'], v['completed_artifact'])
    assert p['review_basis'] == bound
    assert p['foundation_review'] == actual
    assert p['payload_envelope_contract'] == BOUND_CONTRACT
    assert p['metadata']['input_artifact_roles_and_sha256'][0]['file_sha256'] == hashlib.sha256(v['completed_artifact']).hexdigest()
    assert verify_bytes(p, v) == p


@pytest.mark.parametrize('field,value,error', [
    ('completed_packet_id', 'WRONG', 'COMPLETED_PACKET_ID_BINDING_MISMATCH'),
    ('completed_packet_semantic_sha256', '0'*64, 'COMPLETED_PACKET_SEMANTIC_BINDING_MISMATCH'),
    ('completed_packet_file_sha256', '0'*64, 'COMPLETED_PACKET_FILE_BINDING_MISMATCH'),
    ('completed_packet_file_sha256', None, 'COMPLETED_PACKET_FILE_BINDING_MISMATCH'),
    ('review_execution_contract_sha256', '0'*64, 'REVIEW_EXECUTION_CONTRACT_BINDING_MISMATCH'),
    ('review_basis_implementation_commit', '0'*40, 'REVIEW_BASIS_IMPLEMENTATION_MISMATCH'),
])
def test_rehash_cannot_bless_inner_binding_tamper(diagnostic, field, value, error):
    p = copy.deepcopy(diagnostic['payload'])
    if value is None:
        del p['review_basis'][field]
    else:
        p['review_basis'][field] = value
    reseal(p)
    assert p['payload_hash'] == canonical_sha256(payload_semantic_body(p))
    # verify_bytes also recomputes the outer FILE hash of the attacker fixture.
    with pytest.raises(PromotionError, match=error):
        verify_bytes(p, diagnostic['verification'])


@pytest.mark.parametrize('field,value,error', [
    ('expected_completed_packet_id', 'WRONG', 'COMPLETED_ARTIFACT_ID_MISMATCH'),
    ('expected_completed_packet_semantic_sha256', '0'*64, 'COMPLETED_ARTIFACT_SEMANTIC_SHA_MISMATCH'),
    ('expected_completed_packet_file_sha256', '0'*64, 'COMPLETED_ARTIFACT_FILE_SHA_MISMATCH'),
    ('expected_review_execution_contract_sha256', '0'*64, 'REVIEW_EXECUTION_CONTRACT_BINDING_MISMATCH'),
    ('expected_production_sha256', '0'*64, 'PRODUCTION_TRUSTED_BINDING_MISMATCH'),
    ('expected_schema_version', 'WRONG', 'SCHEMA_TRUSTED_BINDING_MISMATCH'),
    ('expected_payload_implementation_commit', '0'*40, 'PAYLOAD_IMPLEMENTATION_BINDING_MISMATCH'),
    ('expected_review_basis_implementation_commit', '0'*40, 'REVIEW_BASIS_IMPLEMENTATION_MISMATCH'),
])
def test_external_expected_mismatch(diagnostic, field, value, error):
    v = dict(diagnostic['verification'])
    v['verification_basis'] = replace(v['verification_basis'], **{field: value})
    with pytest.raises(PromotionError, match=error):
        verify_bytes(diagnostic['payload'], v)


def test_semantically_equal_but_byte_different_artifact_rejected(diagnostic):
    v = dict(diagnostic['verification'])
    original = v['completed_artifact']
    alternate = json.dumps(json.loads(original), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    assert completed_semantic_sha256(json.loads(original)) == completed_semantic_sha256(json.loads(alternate))
    assert hashlib.sha256(original).hexdigest() != hashlib.sha256(alternate).hexdigest()
    v['completed_artifact'] = alternate
    with pytest.raises(PromotionError, match='COMPLETED_ARTIFACT_FILE_SHA_MISMATCH'):
        verify_bytes(diagnostic['payload'], v)


def test_attacker_reseals_artifact_and_payload_but_not_external_basis(diagnostic):
    p = copy.deepcopy(diagnostic['payload'])
    v = dict(diagnostic['verification'])
    actual = json.loads(v['completed_artifact'])
    actual['objects']['nodes'][0]['human_input']['reason'] = 'ATTACKER AUTHORITY'
    sha = completed_semantic_sha256(actual)
    actual['human_completion']['completed_packet_semantic_sha256'] = sha
    data = serialize(actual)
    assert completed_semantic_sha256(actual) == sha
    v['completed_artifact'] = data
    p['foundation_review'] = actual
    p['review_basis']['completed_packet_semantic_sha256'] = sha
    p['review_basis']['completed_packet_file_sha256'] = hashlib.sha256(data).hexdigest()
    p['metadata']['input_artifact_roles_and_sha256'][0]['file_sha256'] = hashlib.sha256(data).hexdigest()
    with pytest.raises(PromotionError, match='COMPLETED_ARTIFACT_FILE_SHA_MISMATCH'):
        verify_bytes(reseal(p), v)


def test_internal_declaration_is_independently_recomputed(diagnostic):
    v = dict(diagnostic['verification'])
    actual = json.loads(v['completed_artifact'])
    actual['human_completion']['completed_packet_semantic_sha256'] = '0'*64
    data = serialize(actual)
    # Even a basis that pins these fixture bytes cannot bless a false internal
    # declaration: the required independent semantic computation still fails.
    basis = replace(v['verification_basis'], expected_completed_packet_file_sha256=hashlib.sha256(data).hexdigest())
    with pytest.raises(PromotionError, match='COMPLETED_ARTIFACT_SEMANTIC_DECLARATION_MISMATCH'):
        verify_completed_artifact(basis, data)


@pytest.mark.parametrize('tamper,error', [
    ('production', 'PRODUCTION_TRUSTED_BINDING_MISMATCH'),
    ('schema', 'SCHEMA_TRUSTED_BINDING_MISMATCH'),
    ('implementation', 'PAYLOAD_IMPLEMENTATION_BINDING_MISMATCH'),
    ('envelope', 'PAYLOAD_ENVELOPE_CONTRACT_MISMATCH'),
    ('embedded_semantic', 'EMBEDDED_COMPLETED_ARTIFACT_MISMATCH'),
    ('decision', 'EMBEDDED_COMPLETED_ARTIFACT_MISMATCH'),
    ('mutation', 'FOUNDATION_PAYLOAD_PROJECTION_DRIFT'),
    ('outer', 'PAYLOAD_HASH_MISMATCH'),
])
def test_remaining_payload_tamper(diagnostic, tamper, error):
    p = copy.deepcopy(diagnostic['payload'])
    if tamper == 'production': p['metadata']['production_sha256'] = '0'*64
    if tamper == 'schema': p['metadata']['production_schema_version'] = 'WRONG'
    if tamper == 'implementation': p['metadata']['repository_commit'] = '0'*40
    if tamper == 'envelope': p['payload_envelope_contract']['contract_sha256'] = '0'*64
    if tamper == 'embedded_semantic': p['foundation_review']['human_completion']['completed_packet_semantic_sha256'] = '0'*64
    if tamper == 'decision': p['foundation_review']['objects']['nodes'][0]['human_input']['decision'] = 'DEFER'
    if tamper == 'mutation': p['intended_mutations'][0]['row']['title'] = 'TAMPER'
    if tamper == 'outer': p['payload_hash'] = '0'*64
    else: reseal(p)
    with pytest.raises(PromotionError, match=error):
        verify_bytes(p, diagnostic['verification'])


def test_outer_file_hash_is_checked(diagnostic):
    with pytest.raises(PromotionError, match='PAYLOAD_FILE_HASH_MISMATCH'):
        validate_payload_artifact(serialize(diagnostic['payload']), expected_payload_file_sha256='0'*64, **diagnostic['verification'])


def test_missing_artifact_and_direct_verifier_cannot_bypass(diagnostic):
    with pytest.raises(PromotionError, match='COMPLETED_ARTIFACT_REQUIRED'):
        validate_payload(diagnostic['payload'], verification_basis=diagnostic['verification']['verification_basis'])
    with pytest.raises(PromotionError, match='TRUSTED_VERIFICATION_BASIS_REQUIRED'):
        validate_foundation_payload(diagnostic['payload'])


@pytest.mark.parametrize('target,error', [
    ('embedded', 'EMBEDDED_COMPLETED_ARTIFACT_MISMATCH'),
    ('contract', 'PAYLOAD_ENVELOPE_CONTRACT_MISMATCH'),
])
def test_exact_json_identity_does_not_coerce_boolean_numbers(diagnostic, target, error):
    p = copy.deepcopy(diagnostic['payload'])
    if target == 'embedded':
        p['foundation_review']['production_apply_authorized'] = 0
    else:
        p['payload_envelope_contract']['three_way_binding_required'] = 1
    # Python dict equality alone conflates false/0 and true/1; the frozen JSON
    # semantic identity must not. Isolate the envelope guard itself here.
    with pytest.raises(PromotionError, match=error):
        verify_payload_review_basis(reseal(p), diagnostic['verification']['verification_basis'], diagnostic['verification']['completed_artifact'])


def test_all_entry_guards_fail_before_db_open_or_mutation(diagnostic, monkeypatch):
    p = copy.deepcopy(diagnostic['payload'])
    p['review_basis']['completed_packet_semantic_sha256'] = '0'*64
    reseal(p)
    def forbidden(*args, **kwargs):
        raise AssertionError('DATABASE_ACCESS_BEFORE_BINDING_REJECTION')
    monkeypatch.setattr('pro_a.production_promotion.sqlite3.connect', forbidden)
    class NoDatabaseAccess:
        execute = forbidden
    for action in (
        lambda: apply_payload_to_shadow(p, diagnostic['root']/'NEVER_CREATED.db', diagnostic['production'], **diagnostic['verification']),
        lambda: validate_executable_operations(NoDatabaseAccess(), p, **diagnostic['verification']),
        lambda: validate_foundation_payload(p, NoDatabaseAccess(), **diagnostic['verification']),
    ):
        with pytest.raises(PromotionError, match='COMPLETED_PACKET_SEMANTIC_BINDING_MISMATCH'):
            action()
    assert not (diagnostic['root']/'NEVER_CREATED.db').exists()


def test_builder_requires_actual_artifact_and_separates_commits(diagnostic):
    from test_phase3f_foundation_baseline import COMMIT
    p = diagnostic['payload']['foundation_review']
    v = dict(diagnostic['verification'])
    new_commit = '2'*40
    v['verification_basis'] = replace(v['verification_basis'], expected_payload_implementation_commit=new_commit)
    args = dict(packet=p, blank_packet=diagnostic['blank'], production_path=diagnostic['production'], repository_commit=new_commit)
    with pytest.raises(PromotionError, match='TRUSTED_VERIFICATION_BASIS_REQUIRED'):
        build_foundation_handoff(**args)
    first = build_foundation_handoff(**args, **v)['payload']
    second = build_foundation_handoff(**args, **v)['payload']
    assert first == second
    assert first['metadata']['repository_commit'] == new_commit
    assert first['metadata']['review_basis_implementation_commit'] == COMMIT
    assert first['foundation_review'] == p
    for key in ('intended_mutations','mapping','node_operations','relation_operations','claims'):
        assert first[key] == diagnostic['payload'][key]
