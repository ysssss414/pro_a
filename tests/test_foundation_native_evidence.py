"""Public-safe synthetic governance probes, with no real authorization payload."""
import copy
import json
import sqlite3

import pytest

from test_phase3f_foundation_baseline import case, complete, handoff, rec, TS, COMMIT
from test_foundation_execution_preparation import governed
from pro_a.foundation_native_evidence import build_governance_manifest, native_authorizations, adjudicated_claim_content
from pro_a.foundation_execution_contract import BOUND_CONTRACT, requalified_objects, authorize_links
from pro_a.phase3f_foundation_baseline import build_review_packet, validate_review
from pro_a.production_promotion import PromotionError, canonical_sha256, sha256_file, production_identity, copy_production_to_shadow, apply_payload_to_shadow
from pro_a.db import Database
from pro_a.foundation_schema_preparation import apply_synthetic_migration, require_execution_schema


AUTHORITY = {"kind": "EXPLICIT_HUMAN_GOVERNANCE_INSTRUCTION", "instruction_sha256": "a" * 64}


@pytest.fixture
def native_case(governed):
    old = governed["blank"]
    evidence = {e["evidence_id"]: {k: v for k, v in e.items() if k != "source_sha256"}
                for c in old["objects"]["claims"] for e in c["content"]["evidence"]}
    sources = {r["source_id"]: r["expected_sha256"] for r in old["registry"]["sources"]}
    specs = [{"relation_candidate_id": "R1", "evidence_id": eid, "source_id": evidence[eid]["source_id"],
              "source_sha256": sources[evidence[eid]["source_id"]], "scope": "test", "temporal_status": "timeless_structural",
              "role": "SUPPORTS", "authorized_proposition": "Only this synthetic scoped edge", "authorization_basis": "Synthetic explicit human instruction"}
             for eid in ("E_C1", "E_C2")]
    manifest = build_governance_manifest(old, evidence, specs, [], AUTHORITY)
    objects = requalified_objects(old, manifest)
    governed["original"] = old
    governed["manifest"] = manifest
    governed["evidence_index"] = evidence
    governed["native_specs"] = specs
    governed["blank"] = build_review_packet(package=old["package"], registry=old["registry"], production=old["production_baseline"],
        repository_commit=COMMIT, objects=objects, timestamp=TS, execution_contract=BOUND_CONTRACT, evidence_governance_manifest=manifest)
    return governed


def independent_review(native_case, claim_decision="DROP"):
    p = complete(native_case["blank"])
    rec(p, "C1")["human_input"]["decision"] = claim_decision
    rec(p, "B1")["human_input"]["decision"] = "DEFER"
    for cid in ("R2", "R3", "R4"):
        rec(p, cid)["human_input"]["decision"] = "DEFER"
    return p


def insert_row(con, table, row):
    con.execute(f"INSERT INTO {table}({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))


def test_native_and_claim_linked_coexist_with_no_native_claim_dependency(native_case):
    p = independent_review(native_case)
    result = handoff(native_case, p)
    payload = result["payload"]
    rows = [m["row"] for m in payload["intended_mutations"] if m["table"] == "relation_evidence_links"]
    assert len(rows) == 3 and sum(r["provenance_mode"] == "RELATION_NATIVE" for r in rows) == 2
    assert all(r["claim_id"] is None for r in rows if r["provenance_mode"] == "RELATION_NATIVE")
    assert not any(m["table"] == "claims" and m["key"]["claim_id"] == "C1" for m in payload["intended_mutations"])
    auths = [m["row"] for m in payload["intended_mutations"] if m["table"] == "relation_evidence_authorizations"]
    assert all(r["relation_decision"] == "" and r["claim_decision"] is None for r in auths if r["provenance_mode"] == "RELATION_NATIVE")
    assert all(r["evidence_role"] == "supports" for r in rows)
    before = production_identity(native_case["production"])
    shadow = native_case["root"] / "native-shadow.db"
    copy_production_to_shadow(native_case["production"], shadow, before["sha256"])
    assert apply_payload_to_shadow(payload, shadow, native_case["production"], **native_case["verification"])["status"] == "COMMITTED"
    assert apply_payload_to_shadow(payload, shadow, native_case["production"], **native_case["verification"])["status"] == "ALREADY_APPLIED"
    with Database(shadow).connect() as con:
        assert con.execute("SELECT count(*) FROM relation_evidence_links WHERE claim_id IS NULL AND provenance_mode='RELATION_NATIVE'").fetchone()[0] == 2
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    rid = next(r["relation_id"] for r in rows if r["provenance_mode"] == "RELATION_NATIVE")
    readback = Database(shadow).relation_evidence(rid)
    assert len(readback) == 2 and all(r["claim_id"] is None and r["statement"] is None for r in readback)
    assert all(r["authorized_proposition"] == "Only this synthetic scoped edge" for r in readback)
    rollback = native_case["root"] / "native-rollback.db"
    copy_production_to_shadow(native_case["production"], rollback, before["sha256"])
    with pytest.raises(PromotionError, match="INJECTED_TRANSACTION_FAILURE"):
        apply_payload_to_shadow(payload, rollback, native_case["production"], inject_failure_after=len(payload["intended_mutations"]), **native_case["verification"])
    assert production_identity(rollback)["semantic_snapshot"] == before["semantic_snapshot"]
    assert production_identity(native_case["production"]) == before


@pytest.mark.parametrize("decision", ["KEEP_NEEDS_REVIEW", "DROP", ""])
def test_native_evidence_admission_does_not_require_claim_keep(native_case, decision):
    p = independent_review(native_case, decision)
    links = authorize_links(rec(p, "R1"), p, {"C2", "C3"})
    assert len(links) == 2 and all(r["claim_id"] is None for r in links)
    if decision:
        assert handoff(native_case, p)["payload"]
    else:
        with pytest.raises(PromotionError, match="INCOMPLETE_HUMAN_REVIEW"):
            handoff(native_case, p)


@pytest.mark.parametrize("decision", ["", "DEFER", "REJECT"])
def test_role_authority_never_implies_relation_decision(native_case, decision):
    p = independent_review(native_case)
    rec(p, "R1")["human_input"]["decision"] = decision
    assert authorize_links(rec(p, "R1"), p, set()) == []
    assert all(r["relation_decision"] == "" for r in native_case["manifest"]["relation_native_authorizations"])
    if decision:
        payload = handoff(native_case, p)["payload"]
        assert not [m for m in payload["intended_mutations"] if m["table"] == "relation_evidence_authorizations" and m["row"]["provenance_mode"] == "RELATION_NATIVE"]


def test_native_authority_does_not_approve_endpoints_or_adjacent_claims(native_case):
    p = independent_review(native_case)
    rec(p, "NC")["human_input"]["decision"] = "DEFER"
    rec(p, "A1")["human_input"]["decision"] = "DEFER"
    with pytest.raises(PromotionError, match="RELATION_ENDPOINT_NON_EXECUTABLE"):
        handoff(native_case, p)
    p = independent_review(native_case)
    rec(p, "R2")["human_input"]["decision"] = "CREATE"
    with pytest.raises(PromotionError, match="RELATION_CLAIM_ADMISSION_BLOCKED"):
        handoff(native_case, p)


def test_native_identity_scope_and_source_are_not_interchangeable(native_case):
    p = native_case["blank"]
    bad = copy.deepcopy(rec(p, "R1"))
    bad["content"]["scope"] = "all implementations"
    with pytest.raises(PromotionError, match="NATIVE_SCOPE_MISMATCH"):
        native_authorizations(bad, native_case["manifest"], p["registry"])
    bad = copy.deepcopy(p["registry"])
    bad["sources"][0]["expected_sha256"] = "0" * 64
    with pytest.raises(PromotionError, match="NATIVE_SOURCE_SHA_MISMATCH"):
        native_authorizations(rec(p, "R1"), native_case["manifest"], bad)
    bad = independent_review(native_case)
    rec(bad, "R1")["candidate_id"] = "R2"
    with pytest.raises(PromotionError, match="NATIVE_AUTHORIZATION_PROJECTION_DRIFT"):
        authorize_links(rec(bad, "R2"), bad, set())
    bad = copy.deepcopy(p)
    bad["evidence_governance_manifest"]["relation_native_authorizations"][0]["evidence_id"] = "OTHER"
    with pytest.raises(PromotionError, match="IMMUTABLE_PACKET_HASH_DRIFT"):
        validate_review(bad, expected_sha256=p["immutable_packet_sha256"], completed=False)


@pytest.mark.parametrize("field,value", [
    ("relation_id", "R_EXIST"), ("relation_candidate_id", "R2"), ("evidence_id", "OTHER"),
    ("source_sha256", "0" * 64), ("source_id", "S3"), ("evidence_sha256", "1" * 64),
    ("proposition_scope", "all implementations"), ("authorized_proposition", "All things use all things"),
    ("evidence_role", "contradicts"), ("human_authorization_manifest_id", "OTHER_MANIFEST"),
    ("claim_decision", None),
])
def test_native_schema_independently_rejects_cross_binding(native_case, field, value):
    payload = handoff(native_case, independent_review(native_case))["payload"]
    con = sqlite3.connect(native_case["production"])
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("BEGIN")
        for m in payload["intended_mutations"]:
            if m["table"] not in {"relation_evidence_authorizations", "relation_evidence_links"}:
                insert_row(con, m["table"], m["row"])
        mode = "CLAIM_LINKED" if field == "claim_decision" else "RELATION_NATIVE"
        auth = next(m["row"] for m in payload["intended_mutations"] if m["table"] == "relation_evidence_authorizations" and m["row"]["provenance_mode"] == mode)
        error = "CHECK constraint failed" if field == "claim_decision" else "EXACT_SCOPED_NATIVE_EVIDENCE_AUTHORIZATION_REQUIRED"
        with pytest.raises(sqlite3.IntegrityError, match=error):
            insert_row(con, "relation_evidence_authorizations", {**auth, field: value})
    finally:
        con.rollback()
        con.close()


def test_native_link_and_source_provenance_are_immutable(native_case):
    payload = handoff(native_case, independent_review(native_case))["payload"]
    shadow = native_case["root"] / "native-immutable.db"
    copy_production_to_shadow(native_case["production"], shadow, sha256_file(native_case["production"]))
    apply_payload_to_shadow(payload, shadow, native_case["production"], **native_case["verification"])
    with Database(shadow).connect() as con:
        for sql in (
            "UPDATE relation_evidence_links SET evidence_id='OTHER' WHERE provenance_mode='RELATION_NATIVE'",
            "DELETE FROM relation_evidence_links WHERE provenance_mode='RELATION_NATIVE'",
            "INSERT OR REPLACE INTO relation_evidence_links SELECT * FROM relation_evidence_links WHERE provenance_mode='RELATION_NATIVE'",
            "UPDATE sources SET sha256='wrong' WHERE source_id='S1'",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="FROZEN_"):
                con.execute(sql)
        row = dict(con.execute("SELECT * FROM relation_evidence_links WHERE provenance_mode='RELATION_NATIVE' LIMIT 1").fetchone())
        row.update(relation_id="R_EXIST", evidence_id="UNAUTHORIZED")
        with pytest.raises(sqlite3.IntegrityError, match="UNAUTHORIZED_ACTIVE_RELATION_EVIDENCE"):
            insert_row(con, "relation_evidence_links", row)
        row.update(provenance_mode="CLAIM_LINKED", evidence_id="", source_id=None, source_sha256="", evidence_sha256="", authorization_id=None)
        with pytest.raises(sqlite3.IntegrityError):
            insert_row(con, "relation_evidence_links", row)  # NULL Claim cannot masquerade as Claim-linked.


def test_migration_preserves_existing_claim_link_and_checks_native_uniqueness(case):
    db = case["db"]
    with db.connect() as con:
        con.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at) VALUES('S_LEGACY','Synthetic','synthetic','synthetic',?,'archive','synthetic')", ("c" * 64,))
        con.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) VALUES('C_LEGACY','Synthetic legacy Claim','fact','synthetic','S_LEGACY','synthetic')")
    assert db.add_relation_evidence("R_EXIST", "C_LEGACY")
    before = db.all("SELECT * FROM relation_evidence_links")
    apply_synthetic_migration(case["production"], configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_sha256=sha256_file(case["production"]))
    after = db.all("SELECT * FROM relation_evidence_links")
    assert len(after) == len(before) == 1 and all(after[0][k] == v for k, v in before[0].items())
    assert after[0]["provenance_mode"] == "CLAIM_LINKED" and after[0]["evidence_id"] == ""
    assert db.relation_evidence("R_EXIST")[0]["statement"] == "Synthetic legacy Claim"
    assert db.add_relation_evidence("R_EXIST", "C_LEGACY") is False
    with db.connect() as con:
        con.execute("DROP INDEX idx_native_evidence_identity")
        con.execute("CREATE INDEX idx_native_evidence_identity ON relation_evidence_links(relation_id,evidence_id,evidence_role)")
        with pytest.raises(PromotionError, match="FOUNDATION_SCHEMA_INDEX_DRIFT"):
            require_execution_schema(con)


@pytest.fixture
def adjudication_case(governed):
    p = copy.deepcopy(governed["blank"])
    c = rec(p, "C1")["content"]
    c["raw"]["evidence_locator"] = "S1 PDF p.1, Synthetic"
    c["row"]["evidence_pointer"] = c["raw"]["evidence_locator"]
    evidence = [{"evidence_id": eid, "source_id": "S1", "pdf_page": 1, "section": "Synthetic",
        "evidence_excerpt": c["raw"]["evidence_excerpt"], "evidence_role": role, "fact_time": "2026-01-01", "publication_date": "2026-01-02"}
        for eid, role in (("E_IDENTITY", "identity"), ("E_ATTRIBUTE", "attribute"))]
    c["evidence"] = [{**e, "source_sha256": c["source_sha256"]} for e in evidence]
    c["qualification_status"] = "REVIEW_REQUIRED"
    c["qualification_diagnostics"] = {"qualification_reason": "EVIDENCE_RECORD_IDENTITY_AMBIGUOUS", "source_identity_exists": True,
        "source_reference_unique": True, "evidence_belongs_to_claimed_source": True, "evidence_locator_present": True,
        "evidence_excerpt_present": True, "mapped_nature": "fact", "mapped_status": "needs_review", "evidence_reference_unique": False}
    c["row"]["structured_json"] = json.dumps({"foundation_native": c["raw"], "qualification": c["qualification_diagnostics"]}, sort_keys=True)
    p = build_review_packet(package=p["package"], registry=p["registry"], production=p["production_baseline"],
        repository_commit=COMMIT, objects=p["objects"], timestamp=TS, execution_contract=BOUND_CONTRACT)
    spec = {"claim_id": "C1", "source_id": "S1", "source_sha256": c["source_sha256"], "authoritative_evidence_id": "E_ATTRIBUTE",
        "sibling_evidence_ids": ["E_IDENTITY"], "reason": "Explicit synthetic human semantic selection, not metadata inference"}
    m = build_governance_manifest(p, {e["evidence_id"]: e for e in evidence}, [], [spec], AUTHORITY)
    return p, m


def test_human_evidence_adjudication_qualifies_without_keep(adjudication_case):
    p, m = adjudication_case
    original = copy.deepcopy(rec(p, "C1"))
    c = adjudicated_claim_content(original, m)
    assert c["qualification_status"] == "DETERMINISTICALLY_MAPPABLE" and c["row"]["status"] == "needs_review"
    assert c["raw"] == original["content"]["raw"]
    assert [e["evidence_id"] for e in c["evidence"]] == ["E_ATTRIBUTE"]
    assert [e["evidence_id"] for e in c["sibling_evidence"]] == ["E_IDENTITY"]
    assert original == rec(p, "C1") and not original["human_input"]["decision"]
    assert json.loads(c["row"]["structured_json"])["qualification"]["qualification_reason"] == "EVIDENCE_RECORD_IDENTITY_AMBIGUOUS"


def test_adjudication_does_not_mask_independent_temporal_exception(adjudication_case):
    p, m = adjudication_case
    c = rec(p, "C1")
    c["content"]["raw"].update(fact_time=None, publication_time=None)
    c["content"]["row"].update(fact_time=None, publication_time=None)
    c["content"]["row"]["structured_json"] = json.dumps({"foundation_native": c["content"]["raw"], "qualification": c["content"]["qualification_diagnostics"]}, sort_keys=True)
    p = build_review_packet(package=p["package"], registry=p["registry"], production=p["production_baseline"],
        repository_commit=COMMIT, objects=p["objects"], timestamp=TS, execution_contract=BOUND_CONTRACT)
    spec = {k: m["claim_evidence_adjudications"][0][k] for k in ("claim_id", "source_id", "source_sha256", "authoritative_evidence_id", "sibling_evidence_ids", "reason")}
    evidence = {e["evidence_id"]: {k: v for k, v in e.items() if k != "source_sha256"} for e in c["content"]["evidence"]}
    m = build_governance_manifest(p, evidence, [], [spec], AUTHORITY)
    with pytest.raises(PromotionError, match="ADJUDICATION_INDEPENDENT_TEMPORAL_OR_NATURE_ISSUE"):
        adjudicated_claim_content(rec(p, "C1"), m)
