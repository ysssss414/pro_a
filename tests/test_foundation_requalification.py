"""Read-only qualification against supplied immutable local inputs; no content decisions."""
import copy
from contextlib import closing
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from pro_a.foundation_requalification import requalify, compare_all_rows, identity_snapshot
from pro_a.foundation_execution_contract import BOUND_CONTRACT
from pro_a.phase3f_foundation_baseline import build_review_packet, validate_review, claim_batches
from pro_a.production_promotion import connect_read_only, production_identity, PromotionError

ROOT = Path(__file__).resolve().parents[1]


def test_full_old_baseline_preflight_releases_handle_without_gc():
    # Fresh process isolates the production gate from unrelated test fixture readers.
    # Automatic GC is disabled so an accidentally leaked cycle cannot hide the bug.
    code = """
import gc, runpy
m = runpy.run_path('scripts/phase3f_foundation_schema_migration.py')
gc.disable()
before = m['production_identity'](m['PRODUCTION'])
m['preflight'](committed=m['git']('rev-parse', 'HEAD') != m['STOPPED_COMMIT'])
m['require_exclusive_read_handle'](m['PRODUCTION'])
assert m['production_identity'](m['PRODUCTION']) == before
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def inputs():
    spec = importlib.util.spec_from_file_location("migration_runbook", ROOT / "scripts/phase3f_foundation_schema_migration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not (module.OLD / "foundation_complete_review_packet.json").exists():
        pytest.skip("Immutable local Foundation corpus not supplied")
    old, manifest, evidence = module.immutable_inputs()
    receipt = module.OUT / "migration_receipt.json"
    if receipt.exists():
        migration = module.read(receipt)
        target, backup = module.PRODUCTION, Path(migration["backup"]["path"])
    else:
        target, backup = module.OUT / "rehearsal_only.db", module.PRODUCTION
    if not target.exists():
        pytest.skip("Run the schema-only rehearsal before local requalification tests")
    return module, old, manifest, evidence, target, backup


def qualified(inputs):
    _, old, manifest, evidence, target, _ = inputs
    with closing(connect_read_only(target)) as con:
        return requalify(old, manifest, con, evidence)


def test_all_native_rows_requalify_without_db_writes(inputs):
    _, old, manifest, evidence, target, _ = inputs
    before = production_identity(target)
    objects = qualified(inputs)
    assert {k: len(v) for k, v in objects.items()} == old["counts"]
    for kind, records in objects.items():
        prior = {r["candidate_id"]: r for r in old["objects"][kind]}
        assert all(r["content"]["raw"] == prior[r["candidate_id"]]["content"]["raw"] for r in records)
    assert production_identity(target) == before


def test_claim_identity_and_temporal_exception_stay_separate(inputs):
    claims = {r["candidate_id"]: r["content"] for r in qualified(inputs)["claims"]}
    assert [e["evidence_id"] for e in claims["FND_CLAIM_0067"]["evidence"]] == ["EV_F030B_P001_R5795"]
    assert [e["evidence_id"] for e in claims["FND_CLAIM_0067"]["sibling_evidence"]] == ["EV_F030B_P001_MEGTRON8"]
    c66 = claims["FND_CLAIM_0066"]
    assert c66["raw"]["fact_time"] is None and c66["raw"]["publication_time"] is None
    assert c66["qualification_status"] == "REVIEW_REQUIRED"
    assert sum(c["qualification_status"] == "DETERMINISTICALLY_MAPPABLE" for c in claims.values()) == 66


def test_native_roles_and_cpo_scope_not_content_authority(inputs):
    relations = qualified(inputs)["relations"]
    auths = [a for r in relations for a in r["content"]["relation_native_authorizations"]]
    assert len(auths) == 8 and all(a["role"] == "SUPPORTS" and a["relation_decision"] == "" for a in auths)
    cpo = next(r["content"] for r in relations if r["candidate_id"] == "FND_REL_0026")
    assert cpo["raw"]["temporal_status"] == "implementation_variant"
    assert cpo["scope"] == "external-laser CPO implementations" and "R1F_0041 DEFER" in cpo["raw"]["reason"]


def test_comparison_explains_all_rows_without_accepting_content(inputs):
    _, old, manifest, _, target, backup = inputs
    # In-memory validation only; no additional real packet is persisted by tests.
    packet = build_review_packet(package=old["package"], registry=old["registry"], production=production_identity(target),
        repository_commit="a" * 40, objects=qualified(inputs), timestamp="test-only", execution_contract=BOUND_CONTRACT,
        evidence_governance_manifest=manifest)
    with closing(connect_read_only(backup)) as con:
        rows = compare_all_rows(old, packet, identity_snapshot(con))
    assert len(rows) == 295 and sum(r["human_review_semantics_changed"] for r in rows) == 123
    assert all(r["native_content_sha256_old"] == r["native_content_sha256_new"] and r["explained"] for r in rows)
    assert sum(len(b["candidate_ids"]) for b in claim_batches(packet)) == 66
    validate_review(packet, expected_sha256=packet["immutable_packet_sha256"], completed=False)


@pytest.mark.parametrize("tamper,error", [("source", "SOURCE_SHA"), ("excerpt", "CLAIM_FIELD"), ("target", "TARGET_DRIFT"), ("time", "CLAIM_FIELD")])
def test_requalification_rejects_projection_tampering(inputs, tamper, error):
    _, old, manifest, evidence, target, _ = inputs
    old = copy.deepcopy(old)
    c = old["objects"]["claims"][0]["content"]
    if tamper == "source":
        c["source_sha256"] = "0" * 64
    elif tamper == "excerpt":
        c["row"]["evidence_excerpt"] = "changed"
    elif tamper == "target":
        old["objects"]["nodes"][0]["content"]["expected_target"] = None
    else:
        c["row"]["fact_time"] = "2099-01-01"
    with closing(connect_read_only(target)) as con, pytest.raises(PromotionError, match=error):
        requalify(old, manifest, con, evidence)


def test_manifest_cannot_expand_native_authority(inputs):
    _, old, manifest, evidence, target, _ = inputs
    manifest = copy.deepcopy(manifest)
    manifest["relation_native_authorizations"][0]["role"] = "CONTRADICTS"
    with closing(connect_read_only(target)) as con, pytest.raises(PromotionError):
        requalify(old, manifest, con, evidence)
