"""Preparation-only governance and migration qualification with synthetic data."""
import copy
import json
import shutil
import sqlite3

import pytest

from test_phase3f_foundation_baseline import case, complete, handoff, rec, TS, COMMIT
from pro_a.foundation_execution_contract import (
    BOUND_CONTRACT, CONTRACT_SHA256, project_temporal, restore_temporal, temporal_census,
    exact_link_candidates, authorize_links, requalified_objects, temporal_row, compare_review_objects,
    categorical_relations,
)
from pro_a.foundation_schema_preparation import (
    apply_synthetic_migration, restore_synthetic_backup, require_execution_schema, migration_sql,
)
from pro_a.phase3f_foundation_baseline import build_review_packet, validate_review, blank_body
from pro_a.production_promotion import (
    PromotionError, canonical_sha256, production_identity, sha256_file,
    copy_production_to_shadow, apply_payload_to_shadow, validate_payload,
)
from pro_a.db import Database


@pytest.fixture
def governed(case):
    old = case["blank"]
    for kind, records in old["objects"].items():
        for record in records:
            content = record["content"]
            if "raw" not in content:
                content["raw"] = copy.deepcopy(content)
            if kind == "claims":
                content["raw"]["status"] = "CANDIDATE"
                content["row"]["status"] = "needs_review"
                content["row"]["structured_json"] = json.dumps({"foundation_native": content["raw"]}, sort_keys=True)
                content["evidence"][0]["evidence_id"] = "E_" + record["candidate_id"]
            if kind == "relations":
                content["raw"]["temporal_status"] = "future_design_point" if record["candidate_id"] == "R3" else "timeless_structural"
                content["evidence_refs"] = ["E_C3"] if record["candidate_id"] == "RR" else ["E_C1", "E_C2"]
                content["raw"]["evidence_refs"] = list(content["evidence_refs"])
                if record["candidate_id"] == "R2":
                    content["raw"]["explicit_evidence_roles"] = [{"claim_id": "C2", "evidence_id": "E_C2", "role": "CONTRADICTS"}]
    apply_synthetic_migration(case["production"], configured_production_path=case["root"] / "NEVER_TOUCH.db",
                              expected_sha256=sha256_file(case["production"]))
    case["db"].execute("UPDATE node_relations SET status='categorical' WHERE relation_id='R_EXIST'")
    rec(old, "RR")["content"]["expected_target"] = case["db"].one("SELECT * FROM node_relations WHERE relation_id='R_EXIST'")
    objects = requalified_objects(old)
    seed = next(r for r in objects["relations"] if r["candidate_id"] == "RR")
    temporal = temporal_row(seed, "R_EXIST", old)
    with case["db"].connect() as con:
        con.execute(f"INSERT INTO relation_temporal_semantics({','.join(temporal)}) VALUES({','.join('?' for _ in temporal)})", tuple(temporal.values()))
    case["prior_packet"] = copy.deepcopy(old)
    case["blank"] = build_review_packet(package=old["package"], registry=old["registry"], production=production_identity(case["production"]),
        repository_commit=COMMIT, objects=objects, timestamp=TS, execution_contract=BOUND_CONTRACT)
    return case


def test_governed_shared_phase3d_full_e2e(governed):
    before = production_identity(governed["production"])
    result = handoff(governed)
    assert result == handoff(governed)
    payload = result["payload"]
    validate_payload(payload)
    claim_rows = [m["row"] for m in payload["intended_mutations"] if m["table"] == "claims"]
    assert len(claim_rows) == 3 and all(r["status"] == "current" for r in claim_rows)
    for row in claim_rows:
        provenance = json.loads(row["structured_json"])
        assert provenance["foundation_native"]["status"] == "CANDIDATE"
        assert provenance["foundation_admission"]["pre_review_status"] == "needs_review"
        assert provenance["foundation_admission"]["decision"] == "KEEP"
    auths = [m["row"] for m in payload["intended_mutations"] if m["table"] == "relation_evidence_authorizations"]
    assert len(auths) == 9
    assert sum(a["evidence_role"] == "contradicts" for a in auths) == 1
    shadow = governed["root"] / "governed-shadow.db"
    copy_production_to_shadow(governed["production"], shadow, before["sha256"])
    applied = apply_payload_to_shadow(payload, shadow, governed["production"])
    assert applied["status"] == "COMMITTED"
    assert applied["changed_tables"]["relation_temporal_semantics"] == {"added": 4, "removed": 0}
    assert applied["changed_tables"]["relation_evidence_authorizations"] == {"added": 9, "removed": 0}
    assert apply_payload_to_shadow(payload, shadow, governed["production"])["status"] == "ALREADY_APPLIED"
    db = Database(shadow)
    with db.connect() as con:
        rows = categorical_relations(con)
        assert len(rows) == 5 and {r["temporal_category"] for r in rows} == {"future_design_point", "timeless_structural"}
        assert all(r["status"] != "current" for r in rows)
        assert not con.execute("SELECT * FROM current_views WHERE status='official'").fetchall()
        assert json.loads(con.execute("SELECT content_json FROM current_views").fetchone()[0])["artifact_status"] == BOUND_CONTRACT["baseline_artifact_status"]
    frozen = sha256_file(shadow)
    db.init_schema()
    assert sha256_file(shadow) == frozen  # No implicit downgrade/backfill.
    rollback = governed["root"] / "governed-rollback.db"
    copy_production_to_shadow(governed["production"], rollback, before["sha256"])
    with pytest.raises(PromotionError, match="INJECTED_TRANSACTION_FAILURE"):
        apply_payload_to_shadow(payload, rollback, governed["production"], inject_failure_after=len(payload["intended_mutations"]))
    assert production_identity(rollback)["semantic_snapshot"] == before["semantic_snapshot"]
    assert production_identity(governed["production"]) == before


@pytest.mark.parametrize("decision", ["KEEP_NEEDS_REVIEW", "DROP", ""])
def test_inadmissible_claim_cannot_authorize_relation(governed, decision):
    packet = complete(governed["blank"])
    rec(packet, "C1")["human_input"]["decision"] = decision
    with pytest.raises(PromotionError, match="INCOMPLETE_HUMAN_REVIEW|RELATION_CLAIM_ADMISSION_BLOCKED"):
        handoff(governed, packet)


@pytest.mark.parametrize("decision", ["DEFER", "REJECT"])
def test_relation_nonexecution_creates_no_links(governed, decision):
    packet = complete(governed["blank"])
    for record in packet["objects"]["relations"]:
        record["human_input"]["decision"] = decision
    payload = handoff(governed, packet)["payload"]
    assert not [m for m in payload["intended_mutations"] if m["table"] in {"node_relations", "relation_temporal_semantics", "relation_evidence_links", "relation_evidence_authorizations"}]


def test_join_alone_has_no_role_authority(governed):
    packet = governed["blank"]
    relation = rec(packet, "R1")
    links = exact_link_candidates(relation, packet["objects"]["claims"], packet["package"]["sha256"])
    assert links == exact_link_candidates(relation, packet["objects"]["claims"], packet["package"]["sha256"])
    assert all(l["authorization_state"] == "UNAUTHORIZED" and l["explicit_role"] is None for l in links)
    assert authorize_links(relation, packet, set()) == []
    bad = complete(packet)
    rec(bad, "R1")["content"]["evidence_link_candidates"][0]["explicit_role"] = "CONTRADICTS"
    with pytest.raises(PromotionError, match="IMMUTABLE_PACKET_HASH_DRIFT"):
        handoff(governed, bad)


def test_unauthorized_runtime_link_is_rejected(governed):
    payload = handoff(governed)["payload"]
    # Apply all reviewed Source/Claim/Node/Relation mutations, but omit authorization
    # and active links using raw SQL solely to test the independent schema guard.
    con = sqlite3.connect(governed["production"])
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("BEGIN")
        for m in payload["intended_mutations"]:
            if m["table"] not in {"relation_evidence_authorizations", "relation_evidence_links"}:
                row = m["row"]
                con.execute(f"INSERT INTO {m['table']}({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
        link = next(m["row"] for m in payload["intended_mutations"] if m["table"] == "relation_evidence_links")
        with pytest.raises(sqlite3.IntegrityError, match="UNAUTHORIZED_ACTIVE_RELATION_EVIDENCE"):
            con.execute(f"INSERT INTO relation_evidence_links({','.join(link)}) VALUES({','.join('?' for _ in link)})", tuple(link.values()))
        retired = {**link, "status": "retired"}
        con.execute(f"INSERT INTO relation_evidence_links({','.join(retired)}) VALUES({','.join('?' for _ in retired)})", tuple(retired.values()))
        with pytest.raises(sqlite3.IntegrityError, match="UNAUTHORIZED_ACTIVE_RELATION_EVIDENCE"):
            con.execute("UPDATE relation_evidence_links SET status='active' WHERE relation_id=?", (link["relation_id"],))
    finally:
        con.rollback()
        con.close()


def test_admitted_provenance_and_authorizations_cannot_be_rewritten(governed):
    payload = handoff(governed)["payload"]
    shadow = governed["root"] / "immutable-provenance.db"
    copy_production_to_shadow(governed["production"], shadow, sha256_file(governed["production"]))
    apply_payload_to_shadow(payload, shadow, governed["production"])
    with Database(shadow).connect() as con:
        for statement in (
            "UPDATE claims SET structured_json='{}' WHERE claim_id='C1'",
            "UPDATE claims SET fact_time='2099-01-01' WHERE claim_id='C1'",
            "DELETE FROM claims WHERE claim_id='C1'",
            "INSERT OR REPLACE INTO claims SELECT * FROM claims WHERE claim_id='C1'",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="FROZEN_CLAIM_ADMISSION_PROVENANCE"):
                con.execute(statement)
        for table in ("relation_temporal_semantics", "relation_evidence_authorizations"):
            with pytest.raises(sqlite3.IntegrityError, match="FROZEN_GOVERNANCE"):
                con.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM {table} LIMIT 1")
        with pytest.raises(sqlite3.IntegrityError, match="RETIRE_GOVERNED_EVIDENCE"):
            con.execute("UPDATE claims SET status='needs_review' WHERE claim_id='C1'")
        con.execute("UPDATE relation_evidence_links SET status='retired' WHERE claim_id='C1'")
        con.execute("UPDATE claims SET status='needs_review' WHERE claim_id='C1'")
        with pytest.raises(sqlite3.IntegrityError, match="UNAUTHORIZED_ACTIVE_RELATION_EVIDENCE"):
            con.execute("UPDATE relation_evidence_links SET status='active' WHERE claim_id='C1'")


def test_exact_join_missing_is_not_fabricated_by_create(governed):
    packet = copy.deepcopy(governed["blank"])
    relation = rec(packet, "R1")
    relation["content"]["evidence_refs"] = ["UNJOINED_SYNTHETIC_EVIDENCE"]
    relation["content"]["raw"]["evidence_refs"] = ["UNJOINED_SYNTHETIC_EVIDENCE"]
    objects = requalified_objects(packet)
    governed["blank"] = build_review_packet(package=packet["package"], registry=packet["registry"],
        production=packet["production_baseline"], repository_commit=COMMIT, objects=objects,
        timestamp=TS, execution_contract=BOUND_CONTRACT)
    with pytest.raises(PromotionError, match="RELATION_EXPLICIT_LINK_CANDIDATES_MISSING:R1"):
        handoff(governed)


def test_keep_preserves_native_null_time_without_inventing_a_date(governed):
    packet = copy.deepcopy(governed["blank"])
    content = rec(packet, "C1")["content"]
    content["raw"]["publication_time"] = None
    content["row"]["publication_time"] = None
    content["row"]["structured_json"] = json.dumps({"foundation_native": content["raw"]}, sort_keys=True)
    objects = requalified_objects(packet)
    governed["blank"] = build_review_packet(package=packet["package"], registry=packet["registry"],
        production=packet["production_baseline"], repository_commit=COMMIT, objects=objects,
        timestamp=TS, execution_contract=BOUND_CONTRACT)
    payload = handoff(governed)["payload"]
    row = next(m["row"] for m in payload["intended_mutations"] if m["table"] == "claims" and m["key"]["claim_id"] == "C1")
    assert row["publication_time"] == ""
    assert json.loads(row["structured_json"])["foundation_native"]["publication_time"] is None
    assert json.loads(row["structured_json"])["foundation_admission"]["pre_review_time_fields"]["publication_time"] is None
    shadow = governed["root"] / "null-time-shadow.db"
    copy_production_to_shadow(governed["production"], shadow, sha256_file(governed["production"]))
    assert apply_payload_to_shadow(payload, shadow, governed["production"])["status"] == "COMMITTED"


def test_namespace_overwrite_and_predecessor_guards(governed):
    db = governed["db"]
    official = {"view_id": "VIEW_SYNTH", "node_id": "N_EXIST", "version": "v_20260103", "status": "official", "change_level": "initial", "content_md": "Synthetic official", "created_at": TS}
    with db.connect() as con:
        con.execute(f"INSERT INTO current_views({','.join(official)}) VALUES({','.join('?' for _ in official)})", tuple(official.values()))
    baseline = next(m["row"] for m in handoff_after_baseline_update(governed)["intended_mutations"] if m["table"] == "current_views")
    # Use the existing Node only in these SQL negative probes, not a real payload.
    baseline["node_id"] = "N_EXIST"
    with db.connect() as con:
        for field, value in [("view_id", "VIEW_SYNTH"), ("version", "v_20260103"), ("previous_view_id", "VIEW_SYNTH"), ("revision_seq", 1), ("version", "baselineXwrong")]:
            bad = {**baseline, field: value}
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(f"INSERT OR REPLACE INTO current_views({','.join(bad)}) VALUES({','.join('?' for _ in bad)})", tuple(bad.values()))
        con.execute(f"INSERT INTO current_views({','.join(baseline)}) VALUES({','.join('?' for _ in baseline)})", tuple(baseline.values()))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE current_views SET status='official' WHERE view_id=?", (baseline["view_id"],))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE current_views SET previous_view_id=? WHERE view_id='VIEW_SYNTH'", (baseline["view_id"],))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("DELETE FROM current_views WHERE view_id=?", (baseline["view_id"],))
        assert con.execute("SELECT content_md FROM current_views WHERE view_id='VIEW_SYNTH'").fetchone()[0] == "Synthetic official"


def handoff_after_baseline_update(governed):
    # Synthetic setup changed, so freeze a NEW blank baseline, never fake old SHA.
    p = governed["blank"]
    p["production_baseline"] = production_identity(governed["production"])
    p["immutable_packet_sha256"] = canonical_sha256(blank_body(p))
    return handoff(governed)["payload"]


def test_migration_atomic_rollback_backup_restore_and_idempotency(case):
    path = case["production"]
    backup = case["root"] / "pre-migration-backup.db"
    shutil.copyfile(path, backup)
    before = sha256_file(path)
    for fail_after in (1, 5, 15):
        with pytest.raises(PromotionError, match="INJECTED_SCHEMA_MIGRATION_FAILURE"):
            apply_synthetic_migration(path, configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_sha256=before, inject_failure_after=fail_after)
        assert sha256_file(path) == before
    result = apply_synthetic_migration(path, configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_sha256=before)
    assert result["status"] == "PREPARED_SYNTHETIC_ONLY"
    assert apply_synthetic_migration(path, configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_sha256=sha256_file(path))["status"] == "ALREADY_PREPARED"
    restore_synthetic_backup(path, backup, configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_backup_sha256=before)
    assert sha256_file(path) == before
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        apply_synthetic_migration(path, configured_production_path=path, expected_sha256=before)


def test_migration_from_0_2_1_and_sql_artifact_agree(case):
    db = case["db"]
    db.execute("DROP TABLE relation_evidence_links")
    db.execute("UPDATE meta SET value='0.2.1' WHERE key='schema_version'")
    direct = case["root"] / "direct-sql.db"
    shutil.copyfile(case["production"], direct)
    apply_synthetic_migration(case["production"], configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_sha256=sha256_file(case["production"]))
    with sqlite3.connect(direct) as con:
        con.executescript(migration_sql())
        require_execution_schema(con)
    assert production_identity(direct)["schema_sha256"] == production_identity(case["production"])["schema_sha256"]
    assert production_identity(direct)["semantic_snapshot"] == production_identity(case["production"])["semantic_snapshot"]


@pytest.mark.parametrize("raw", [
    {"temporal_status": "future_design_9999"},
    {"temporal_status": "unknown_future_category_kept_verbatim"},
    {"temporal_status": "vendor_scoped_2024_2025", "valid_from": "2024-03-02", "valid_to": None},
])
def test_temporal_roundtrip_never_parses_suffix_dates(raw):
    projection = project_temporal(raw)
    assert restore_temporal(projection) == raw
    assert projection["runtime_status"] != "current"
    if "valid_from" not in raw:
        assert projection["valid_from"] == projection["valid_to"] == ""


def test_native_optional_validity_and_schema_drift_fail_closed(case):
    path = case["production"]
    apply_synthetic_migration(path, configured_production_path=case["root"] / "NEVER_TOUCH.db", expected_sha256=sha256_file(path))
    raw = {"temporal_status": "vendor_scoped_2024_2025", "valid_from": "2024-03-02", "valid_to": None}
    projection = project_temporal(raw)
    row = temporal_row({"candidate_id": "SYNTH", "content": {
        "raw": raw, "temporal_projection": projection, "valid_from": "2024-03-02", "valid_to": "", "status": "categorical"}},
        "R_EXIST", {"package": {"sha256": "0" * 64}})
    with case["db"].connect() as con:
        con.execute("UPDATE node_relations SET status='categorical',valid_from='2024-03-02' WHERE relation_id='R_EXIST'")
        bad = {**row, "valid_to_supplied": 0}
        with pytest.raises(sqlite3.IntegrityError, match="TEMPORAL_CATEGORY_CONTRACT_REQUIRED"):
            con.execute(f"INSERT INTO relation_temporal_semantics({','.join(bad)}) VALUES({','.join('?' for _ in bad)})", tuple(bad.values()))
        con.execute(f"INSERT INTO relation_temporal_semantics({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
        result = categorical_relations(con)[0]
        assert json.loads(result["temporal_provenance_json"])["native_temporal"] == raw
        assert result["valid_from"] == "2024-03-02" and result["valid_to_supplied"] == 1
        with pytest.raises(sqlite3.IntegrityError, match="TEMPORAL_RELATION_REQUALIFICATION_REQUIRED"):
            con.execute("UPDATE node_relations SET status='current' WHERE relation_id='R_EXIST'")
        con.execute("DROP INDEX idx_relation_temporal_category")
        with pytest.raises(PromotionError, match="FOUNDATION_SCHEMA_INDEX_DRIFT"):
            require_execution_schema(con)


def test_requalification_has_new_blank_authority_and_preserves_native_content(governed):
    packet = governed["blank"]
    validate_review(packet, expected_sha256=packet["immutable_packet_sha256"], completed=False)
    assert packet["packet_id"] != governed["prior_packet"]["packet_id"]
    old = copy.deepcopy(governed["prior_packet"])
    for records in old["objects"].values():
        for r in records:
            r["content_sha256"] = canonical_sha256(r["content"])
    comparison = compare_review_objects(old, packet)
    assert len(comparison) == 13 and all(r["native_semantics_unchanged"] for r in comparison)
    assert any(not r["review_content_unchanged"] for r in comparison)
    assert all(not r["human_input"]["decision"] for records in packet["objects"].values() for r in records)
