"""Public-safe fixtures only; no package or real Source text is required."""
import copy
from datetime import datetime
import json
from pathlib import Path
import sqlite3

import pytest

from pro_a.baseline_views import install_baseline_guards, baseline_reference
from pro_a.config import AppConfig, WorkspaceConfig, LLMConfig, IMAConfig, PipelineConfig
from pro_a.current_view import create_official_view_record
from pro_a.current_view_compare import compare_current_views, CurrentViewCompareValidationError
from pro_a.db import Database
from pro_a.phase3f_foundation_baseline import (
    build_review_packet, validate_review, blank_body, claim_batches, expand_claim_batches,
)
from pro_a.phase3f_operational_handoff import build_handoff_core
from pro_a.production_promotion import (
    PromotionError, canonical_sha256, deterministic_id, production_identity,
    sha256_file, validate_payload, apply_payload_to_shadow, copy_production_to_shadow,
)


TS = "2026-01-03T00:00:00+00:00"
COMMIT = "1" * 40


def _object(cid, **content):
    return {"candidate_id": cid, "content": content}


def _claim(cid, sid, sha):
    raw = {"statement": "Synthetic " + cid, "evidence_excerpt": "Synthetic evidence " + cid,
           "nature": "fact", "fact_time": "2026-01-01", "publication_time": "2026-01-02"}
    row = {"claim_id": cid, **raw, "ingestion_time": TS, "source_id": sid, "evidence_pointer": "synthetic:1",
           "attributed_to": "Synthetic author", "scope": "synthetic", "assumption_text": "", "status": "current",
           "confidence": None, "novelty_level": "N2", "structured_json": json.dumps({"foundation_native": raw}, sort_keys=True), "created_at": TS}
    return _object(cid, raw=raw, row=row, source_id=sid, source_sha256=sha,
                   evidence=[{"source_id": sid, "source_sha256": sha, "excerpt": raw["evidence_excerpt"]}],
                   qualification_status="DETERMINISTICALLY_MAPPABLE")


@pytest.fixture
def case(tmp_path):
    production = tmp_path / "synthetic-production.db"
    db = Database(production)
    db.init_schema()
    db.add_node("Synthetic existing", "Technology", node_id="N_EXIST")
    db.add_node("Synthetic peer", "Technology", node_id="N_PEER")
    with db.connect() as conn:
        install_baseline_guards(conn)
        conn.execute("INSERT INTO node_relations(relation_id,from_node_id,relation_type,to_node_id,scope,created_at) VALUES(?,?,?,?,?,?)",
                     ("R_EXIST", "N_EXIST", "related_to", "N_PEER", "test", TS))
    package_file, receipt_file = tmp_path / "package.bin", tmp_path / "qualification.json"
    package_file.write_bytes(b"Synthetic package identity")
    receipt_file.write_bytes(b'{"synthetic":true}')
    package = {"path": str(package_file), "sha256": sha256_file(package_file), "inventory_sha256": "2" * 64,
               "qualification_receipt": {"path": str(receipt_file), "sha256": sha256_file(receipt_file)}}
    sources = []
    for i in range(1, 4):
        path = tmp_path / f"source-{i}.bin"
        path.write_bytes(f"Synthetic Source bytes {i}".encode())
        sha = sha256_file(path)
        sources.append({"source_id": f"S{i}", "expected_sha256": sha, "actual_sha256": sha,
                        "candidate_local_file": str(path), "exact_match": True})
    registry = {"package_sha256": package["sha256"], "package_inventory_sha256": package["inventory_sha256"],
                "sources": sources, "expected_sources": 3, "materialized_sources": 3}
    registry["registry_sha256"] = canonical_sha256(registry)
    objects = {"claims": [_claim(f"C{i}", s["source_id"], s["expected_sha256"]) for i, s in enumerate(sources, 1)],
               "nodes": [_object("NC", canonical_name="Synthetic created", primary_type="Technology", supporting_claim_ids=["C1", "C2"])],
               "aliases": [_object("A1", alias="Independent synthetic alias", target_ref="NC")],
               "relations": [], "baseline_views": []}
    for cid, nid in [("NR", "N_EXIST"), ("NP", "N_PEER")]:
        target = db.one("SELECT * FROM nodes WHERE node_id=?", (nid,))
        objects["nodes"].append(_object(cid, canonical_name=target["canonical_name"], primary_type="Technology",
                                         expected_target=target, supporting_claim_ids=["C2", "C3"]))
    for i, relation_type in enumerate(["part_of", "supplies", "depends_on", "competes_with"], 1):
        objects["relations"].append(_object(f"R{i}", relation_type=relation_type, from_ref="NC", to_ref="NR",
                                            scope="test", valid_from="", valid_to="", status="current", confidence=None,
                                            temporal_representation_lossless=True,
                                            evidence_links=[{"claim_id": "C1", "evidence_role": "supports"},
                                                            {"claim_id": "C2", "evidence_role": "contradicts"}]))
    existing = db.one("SELECT * FROM node_relations WHERE relation_id='R_EXIST'")
    objects["relations"].append(_object("RR", relation_type="related_to", from_ref="NR", to_ref="NP", scope="test",
                                        valid_from="", valid_to="", status="current", confidence=None,
                                        temporal_representation_lossless=True, expected_target=existing,
                                        evidence_links=[{"claim_id": "C3", "evidence_role": "supports"}]))
    objects["baseline_views"].append(_object("B1", target_ref="NC", as_of="2026-01-03", content_md="# Synthetic frozen baseline\n",
                                             content_json={"synthetic": True}, supporting_claim_ids=["C1", "C2", "C3"],
                                             supporting_source_ids=["S1", "S2", "S3"]))
    blank = build_review_packet(package=package, registry=registry, production=production_identity(production),
                                repository_commit=COMMIT, objects=objects, timestamp=TS)
    return {"blank": blank, "production": production, "db": db, "root": tmp_path}


def complete(blank):
    packet = copy.deepcopy(blank)
    packet["human_completion"] = {"reviewer": "SYNTHETIC_HUMAN", "reason": "Synthetic test only"}
    for kind, records in packet["objects"].items():
        for record in records:
            cid = record["candidate_id"]
            decision = {"claims": "KEEP", "nodes": "CREATE", "aliases": "ATTACH", "relations": "CREATE", "baseline_views": "ACCEPT"}[kind]
            target = ""
            if cid in {"NR", "NP", "RR"}:
                decision = "REUSE"
                target = {"NR": "N_EXIST", "NP": "N_PEER", "RR": "R_EXIST"}[cid]
            if cid == "A1":
                target = deterministic_id("NODE", {"package": packet["package"]["sha256"], "candidate_id": "NC"})
            record["human_input"] = {"decision": decision, "reason": "Synthetic individual authorization", "target_id": target}
    return packet


def handoff(case, packet=None):
    return build_handoff_core(packet=packet or complete(case["blank"]), bundle={"blank_packet": case["blank"]},
                              production_path=case["production"], repository_commit=COMMIT,
                              completion={}, completion_receipt={}, bindings=[], authority={}, policy=None)


def reseal(case):
    packet = case["blank"]
    for kind, records in packet["objects"].items():
        for record in records:
            record["content_sha256"] = canonical_sha256(record["content"])
        packet["candidate_manifest"][kind] = [{k: r[k] for k in ("candidate_id", "content_sha256")} for r in records]
    packet["immutable_packet_sha256"] = canonical_sha256(blank_body(packet))


def rec(packet, cid):
    return next(r for rows in packet["objects"].values() for r in rows if r["candidate_id"] == cid)


def test_complete_baseline_shared_engine_e2e(case):
    before = production_identity(case["production"])
    first, second = handoff(case), handoff(case)
    assert first == second
    payload = first["payload"]
    validate_payload(payload)
    assert len(first["mapping"]) == 13
    assert sum(m["table"] == "sources" for m in payload["intended_mutations"]) == 3
    assert {r["source_id"] for r in payload["claims"]} == {"S1", "S2", "S3"}
    shadow = case["root"] / "shadow.db"
    copy_production_to_shadow(case["production"], shadow, before["sha256"])
    result = apply_payload_to_shadow(payload, shadow, case["production"])
    assert result["status"] == "COMMITTED"
    assert result["changed_tables"] == {
        "sources": {"added": 3, "removed": 0}, "claims": {"added": 3, "removed": 0},
        "nodes": {"added": 1, "removed": 0}, "node_aliases": {"added": 1, "removed": 0},
        "node_relations": {"added": 4, "removed": 0}, "relation_evidence_links": {"added": 9, "removed": 0},
        "current_views": {"added": 1, "removed": 0},
    }
    assert apply_payload_to_shadow(payload, shadow, case["production"])["status"] == "ALREADY_APPLIED"
    rollback = case["root"] / "rollback.db"
    copy_production_to_shadow(case["production"], rollback, before["sha256"])
    with pytest.raises(PromotionError, match="INJECTED_TRANSACTION_FAILURE"):
        apply_payload_to_shadow(payload, rollback, case["production"], inject_failure_after=len(payload["intended_mutations"]))
    assert production_identity(rollback)["semantic_snapshot"] == before["semantic_snapshot"]
    assert production_identity(case["production"]) == before
    with pytest.raises(PromotionError, match="CONFIGURED_PRODUCTION_WRITE_BLOCKED"):
        apply_payload_to_shadow(payload, case["production"], case["production"])


@pytest.mark.parametrize("change,expected", [
    ("missing_source", "SOURCE_MISSING"), ("source_sha", "SOURCE_SHA_MISMATCH"),
    ("unregistered_source", "UNREGISTERED_CLAIM_SOURCE"), ("cross_source", "CROSS_SOURCE_PROVENANCE"),
    ("node_collision", "NODE_COLLISION"), ("alias_collision", "ALIAS_COLLISION"),
    ("alias_nonexec", "ALIAS_TARGET_NON_EXECUTABLE"), ("relation_nonexec", "RELATION_ENDPOINT_NON_EXECUTABLE"),
    ("invalid_type", "INVALID_RELATION_TYPE"), ("duplicate_edge", "DUPLICATE_RELATION_IDENTITY"),
    ("part_of_cycle", "PART_OF_CYCLE"), ("evidence_nonexec", "RELATION_EVIDENCE_CLAIM_NON_EXECUTABLE"),
    ("temporal_loss", "RELATION_TEMPORAL_MEANING_LOSS"), ("wrong_reuse", "RELATION_REUSE_WRONG_TARGET"),
    ("baseline_node", "BASELINE_NODE_NON_EXECUTABLE"), ("baseline_claim", "BASELINE_CLAIM_NON_EXECUTABLE"),
    ("incomplete_human", "INCOMPLETE_HUMAN_REVIEW"), ("candidate_drift", "IMMUTABLE_PACKET_HASH_DRIFT"),
    ("package_drift", "PACKAGE_HASH_DRIFT"), ("production_drift", "PRODUCTION_BASELINE_DRIFT"),
    ("authorization", "PRODUCTION_AUTHORIZATION_FORBIDDEN"), ("omission", "IMMUTABLE_PACKET_HASH_DRIFT"),
])
def test_fail_closed(case, change, expected):
    blank = case["blank"]
    if change == "missing_source":
        Path(blank["registry"]["sources"][0]["candidate_local_file"]).unlink()
    elif change == "source_sha":
        Path(blank["registry"]["sources"][0]["candidate_local_file"]).write_bytes(b"changed")
    elif change == "unregistered_source": rec(blank, "C1")["content"]["source_id"] = "MISSING"
    elif change == "cross_source": rec(blank, "C1")["content"]["evidence"][0]["source_id"] = "S2"
    elif change == "node_collision": rec(blank, "NC")["content"]["canonical_name"] = "Synthetic existing"
    elif change == "alias_collision": rec(blank, "A1")["content"]["alias"] = "Synthetic peer"
    elif change == "invalid_type": rec(blank, "R1")["content"]["relation_type"] = "invented"
    elif change == "duplicate_edge": rec(blank, "R2")["content"]["relation_type"] = "part_of"
    elif change == "part_of_cycle": rec(blank, "R1")["content"]["to_ref"] = "NC"
    elif change == "temporal_loss": rec(blank, "R1")["content"]["temporal_representation_lossless"] = False
    elif change == "baseline_node": rec(blank, "B1")["content"]["target_ref"] = "MISSING"
    elif change == "baseline_claim": rec(blank, "B1")["content"]["supporting_claim_ids"] = ["MISSING"]
    elif change == "package_drift": Path(blank["package"]["path"]).write_bytes(b"drift")
    elif change == "production_drift": case["db"].add_node("Drift", "Technology")
    reseal(case)
    packet = complete(blank)
    if change == "alias_nonexec": rec(packet, "NC")["human_input"]["decision"] = "DEFER"
    elif change == "relation_nonexec":
        rec(packet, "NP")["human_input"]["decision"] = "DEFER"
    elif change == "evidence_nonexec": rec(packet, "C1")["human_input"]["decision"] = "DROP"
    elif change == "wrong_reuse": rec(packet, "RR")["human_input"]["target_id"] = "WRONG"
    elif change == "incomplete_human": rec(packet, "RR")["human_input"]["decision"] = ""
    elif change == "candidate_drift": rec(packet, "C1")["content"]["raw"]["statement"] = "rewritten"
    elif change == "authorization": packet["production_apply_authorized"] = True
    elif change == "omission": packet["objects"]["relations"].pop()
    with pytest.raises((PromotionError, ValueError), match=expected):
        handoff(case, packet)


def test_general_relations_do_not_inherit_part_of_cycle_rule(case):
    rec(case["blank"], "R3")["content"].update(from_ref="NR", to_ref="NC")
    reseal(case)
    handoff(case)


def test_claim_batch_exact_authority_and_exceptions(case):
    rec(case["blank"], "C3")["content"]["qualification_status"] = "REVIEW_REQUIRED"
    reseal(case)
    batches = claim_batches(case["blank"])
    assert sum(len(b["candidate_ids"]) for b in batches) == 2
    packet = complete(case["blank"])
    rec(packet, "C3")["human_input"]["decision"] = "KEEP_NEEDS_REVIEW"
    for cid in ("C1", "C2"):
        rec(packet, cid)["human_input"] = {"decision": "", "reason": "", "target_id": ""}
    for batch in batches:
        batch["human_input"] = {"reviewer": "SYNTHETIC_HUMAN", "decision": "KEEP", "reason": "Synthetic batch authorization"}
    expanded = expand_claim_batches(case["blank"], packet, batches)
    assert rec(expanded, "C1")["human_input"]["decision"] == "KEEP"
    batches[0]["candidate_ids"].append("C3")
    with pytest.raises(PromotionError, match="BATCH_BINDING_DRIFT"):
        expand_claim_batches(case["blank"], packet, batches)


def test_baseline_cannot_become_official_or_mutate_in_payload(case):
    payload = handoff(case)["payload"]
    for field, value in [("status", "official"), ("content_md", "rewritten")]:
        bad = copy.deepcopy(payload)
        next(m for m in bad["intended_mutations"] if m["table"] == "current_views")["row"][field] = value
        body = {k: v for k, v in bad.items() if k not in {"payload_id", "payload_hash"}}
        digest = canonical_sha256(body)
        bad.update(payload_hash=digest, payload_id="PROMO_" + digest[:16].upper())
        with pytest.raises(PromotionError, match="FOUNDATION_PAYLOAD_PROJECTION_DRIFT"):
            validate_payload(bad)


def test_baseline_storage_isolation_and_immutability(case):
    rec(case["blank"], "B1")["content"]["as_of"] = datetime.now().strftime("%Y%m%d")
    reseal(case)
    payload = handoff(case)["payload"]
    shadow = case["root"] / "baseline-shadow.db"
    copy_production_to_shadow(case["production"], shadow, payload["metadata"]["production_sha256"])
    apply_payload_to_shadow(payload, shadow, case["production"])
    db = Database(shadow)
    view = db.one("SELECT * FROM current_views WHERE status='baseline'")
    nid, vid = view["node_id"], view["view_id"]
    assert db.current_view(nid) is None and db.versions(nid) == []
    from pro_a.query import ReadOnlyQuery
    query = ReadOnlyQuery(shadow)
    assert query.node_current_view(nid) is None
    assert query.node_current_view_history(nid) == []
    with db.connect() as conn:
        assert baseline_reference(conn, nid) == [view]
    for sql, args in [
        ("UPDATE current_views SET content_md='changed' WHERE view_id=?", (vid,)),
        ("UPDATE current_views SET status='official' WHERE view_id=?", (vid,)),
        ("DELETE FROM current_views WHERE view_id=?", (vid,)),
        ("DELETE FROM nodes WHERE node_id=?", (nid,)),
        ("INSERT OR REPLACE INTO current_views SELECT * FROM current_views WHERE view_id=?", (vid,)),
    ]:
        with pytest.raises(sqlite3.IntegrityError, match="BASELINE"):
            db.execute(sql, args)
    db.init_schema()
    assert db.one("SELECT * FROM current_views WHERE view_id=?", (vid,)) == view
    cfg = AppConfig(WorkspaceConfig(case["root"]), LLMConfig(), IMAConfig(), PipelineConfig(), case["root"] / "unused.toml")
    from pro_a.proposals import ProposalManager
    manager = ProposalManager.__new__(ProposalManager)
    manager.cfg, manager.db = cfg, db
    with pytest.raises(KeyError):
        manager._view_for_side_effect(vid)
    with db.connect() as conn:
        from pro_a.human_proposal_resolution import resolution_write_authorizer
        conn.set_authorizer(resolution_write_authorizer(True))
        first = create_official_view_record(conn, cfg, nid, {}, "initial")
        second = create_official_view_record(conn, cfg, nid, {}, "minor")
        conn.set_authorizer(None)
    assert first["previous_view"] is None
    assert first["version"] == "v_" + datetime.now().strftime("%Y%m%d")
    assert second["previous_view"]["view_id"] == first["view_id"]
    assert set(db.versions(nid)) == {first["version"], second["version"]}
    assert {v["view_id"] for v in query.node_current_view_history(nid)} == {first["view_id"], second["view_id"]}
    assert db.one("SELECT * FROM current_views WHERE view_id=?", (vid,)) == view
    with pytest.raises(CurrentViewCompareValidationError, match="Only official"):
        compare_current_views(view, db.current_view(nid))


def test_missing_schema_guards_fail_closed(case):
    case["db"].execute("DROP TRIGGER foundation_baseline_update")
    case["blank"]["production_baseline"] = production_identity(case["production"])
    reseal(case)
    with pytest.raises(ValueError, match="BASELINE_SCHEMA_PRECONDITION_MISSING"):
        handoff(case)


def test_deterministic_rerun_mismatch_rejected(case):
    from pro_a.phase3f_operational_handoff import assert_deterministic_handoff, OperationalHandoffError
    first = handoff(case)
    second = copy.deepcopy(first)
    second["mapping"].pop()
    with pytest.raises(OperationalHandoffError, match="DETERMINISTIC_RERUN_MISMATCH"):
        assert_deterministic_handoff(first, second)


@pytest.mark.parametrize("field", ["fact_time", "publication_time"])
def test_claim_time_projection_cannot_rewrite_native_values(case, field):
    rec(case["blank"], "C1")["content"]["row"][field] = "1900-01-01"
    reseal(case)
    with pytest.raises(PromotionError, match="CLAIM_SEMANTIC_REWRITE"):
        handoff(case)


def test_inactive_claim_cannot_support_active_relation(case):
    rec(case["blank"], "C1")["content"]["row"]["status"] = "needs_review"
    reseal(case)
    with pytest.raises(PromotionError, match="RELATION_EVIDENCE_CLAIM_NOT_ACTIVE"):
        handoff(case)


def test_missing_relation_evidence_schema_is_not_silently_migrated(case):
    case["db"].execute("DROP TABLE relation_evidence_links")
    case["blank"]["production_baseline"] = production_identity(case["production"])
    reseal(case)
    before = production_identity(case["production"])
    with pytest.raises(PromotionError, match="RELATION_EVIDENCE_SCHEMA_PRECONDITION_MISSING"):
        handoff(case)
    assert production_identity(case["production"]) == before


def test_package_drift_after_payload_build_is_rejected(case):
    payload = handoff(case)["payload"]
    Path(case["blank"]["package"]["path"]).write_bytes(b"Synthetic package changed after construction")
    with pytest.raises(PromotionError, match="PACKAGE_HASH_DRIFT"):
        validate_payload(payload)


def test_foundation_n1_special_case(case):
    blank = case["blank"]
    registry = blank["registry"]
    registry["sources"] = registry["sources"][:1]
    registry["expected_sources"] = registry["materialized_sources"] = 1
    registry["registry_sha256"] = canonical_sha256({k: v for k, v in registry.items() if k != "registry_sha256"})
    blank["objects"]["claims"] = blank["objects"]["claims"][:1]
    blank["counts"]["claims"] = 1
    for row in blank["objects"]["nodes"]:
        row["content"]["supporting_claim_ids"] = ["C1"]
    for row in blank["objects"]["relations"]:
        row["content"]["evidence_links"] = [{"claim_id": "C1", "evidence_role": "supports"}]
    rec(blank, "B1")["content"].update(supporting_claim_ids=["C1"], supporting_source_ids=["S1"])
    reseal(case)
    payload = handoff(case)["payload"]
    assert sum(m["table"] == "sources" for m in payload["intended_mutations"]) == 1
