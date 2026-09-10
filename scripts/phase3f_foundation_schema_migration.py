"""Bounded local migration/requalification runbook. Explicit phases; STOP at blank review."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pro_a.config import load_config
from pro_a.db import CURRENT_VIEW_ORDER
from pro_a.foundation_execution_contract import BOUND_CONTRACT, CONTRACT_SHA256, temporal_census
from pro_a.foundation_native_evidence import validate_manifest
from pro_a.foundation_requalification import identity_snapshot, requalify, compare_all_rows
from pro_a.foundation_schema_migration import SQL_PATH, AUTHORIZED_SQL_SHA256, execute_authorized_schema_migration
from pro_a.foundation_schema_preparation import require_execution_schema
from pro_a.phase3f_foundation_baseline import build_review_packet, blank_body, validate_review, validate_files, claim_batches, require
from pro_a.production_promotion import canonical_sha256, sha256_file, production_identity, connect_read_only

PRIOR_OUT = ROOT / "workspace/phase3f_foundation_schema_migration"
OUT = PRIOR_OUT / "resumed_connection_closure"
OLD = ROOT / "workspace/phase3f_foundation_complete_baseline"
GOV = ROOT / "workspace/phase3f_foundation_relation_native_governance"
PRODUCTION = ROOT / "workspace/pro_a.db"
ARCHIVE = ROOT / "workspace/foundation_backfill_web_sol_v1.zip"
INSTRUCTION = Path("C:/Users/cjzs0/.codex/attachments/ae761728-1215-4477-92ed-3588384b6442/pasted-text.txt")
OLD_SHA = "3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0"
ARCHIVE_SHA = "95694f1456774a195d5aed0e0c2e34c949afa1d9b803b6cc2614bd35dc90b759"
INVENTORY_SHA = "7045053967f927612af649b94628913bad2698d62e3549ae2a8eec3b9a0b4c46"
OLD_PACKET_SHA = "8f6d825add58cac586eb8eb86816565e5d327f2acc5458be0bc47e0baa98cf86"
MANIFEST_SHA = "77cbf56c1f3105b9a8719b7913ddb6405ed7e53e86f6fbc68c4463dde3e7c443"
PRE_COMMIT = "4ecc36450d1ec8551bd0a6aa65475f60a0b7c68f"
STOPPED_COMMIT = "591ed09f8e7e770601945eaeb75f060b5f3eeee3"
EXPECTED_COUNTS = {"nodes": 138, "aliases": 25, "claims": 67, "relations": 56, "baseline_views": 9}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def freeze(name, value):
    path = OUT / name
    data = (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == data, "FROZEN_RERUN_DRIFT:" + name)
    else:
        with path.open("xb") as stream:
            stream.write(data)


def binding(path):
    return {"path": str(path), "sha256": sha256_file(path)}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def official(connection):
    rows = [dict(r) for r in connection.execute("SELECT * FROM current_views WHERE status='official' ORDER BY view_id")]
    latest = {}
    for nid in sorted({r["node_id"] for r in rows}):
        row = connection.execute(f"SELECT * FROM current_views WHERE node_id=? AND status='official' ORDER BY {CURRENT_VIEW_ORDER} LIMIT 1", (nid,)).fetchone()
        latest[nid] = {"view_id": row["view_id"], "row_sha256": canonical_sha256(dict(row))}
    return {"official_views": [{"view_id": r["view_id"], "row_sha256": canonical_sha256(r)} for r in rows], "latest_official": latest}


def immutable_inputs():
    # Must precede ZIP inspection on every invocation.
    require(sha256_file(ARCHIVE) == ARCHIVE_SHA, "ARCHIVE_SHA_DRIFT")
    freeze("archive_input_freeze.json", {**binding(ARCHIVE), "size": ARCHIVE.stat().st_size, "immutable": True})
    stop = read(PRIOR_OUT / "schema_migration_stop_receipt.json")
    require(stop["receipt_sha256"] == canonical_sha256({k: v for k, v in stop.items() if k != "receipt_sha256"}) ==
            "6611e772e1d3ef77e48a3fbb8afc49221b7f58f8ff04f597efe0ef85de2fc2c1", "PRIOR_STOP_RECEIPT_DRIFT")
    freeze("resumption_authority.json", {"user_reply": "允许", "authority_kind": "EXPLICIT_CONVERSATION_FOLLOWUP",
        "approved_scope": "Fix connection closure, add integration regression, refreeze local implementation and retry the same Production/SQL two-hash authorization; STOP before Human Review.",
        "stopped_commit": STOPPED_COMMIT, "prior_stop_receipt_sha256": stop["receipt_sha256"],
        "preserved_prior_artifacts": [binding(p) for p in sorted(PRIOR_OUT.iterdir()) if p.is_file()]})
    old = read(OLD / "foundation_complete_review_packet.json")
    validate_review(old, expected_sha256=OLD_PACKET_SHA, completed=False)
    validate_files(old)
    require(old["counts"] == EXPECTED_COUNTS, "ORIGINAL_CORPUS_DRIFT")
    require(sha256_file(OLD / "foundation_complete_review_packet.json") == "497e5f9b8a13c473d54095a035fbbb62daa200ed79570c829b69006618e6f745", "OLD_PACKET_FILE_DRIFT")
    manifest = read(GOV / "human_evidence_governance_authorization_manifest.json")
    validate_manifest(manifest, ARCHIVE_SHA)
    require(manifest["manifest_id"] == "FOUNDATION_GOVERNANCE_3C35BA646C5DC664" and manifest["manifest_sha256"] == MANIFEST_SHA, "MANIFEST_DRIFT")
    require(CONTRACT_SHA256 == "9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634", "CONTRACT_DRIFT")
    require(sha256_file(SQL_PATH) == sha256_file(GOV / "qualified/proposed_schema_0_2_3_relation_native.sql") == AUTHORIZED_SQL_SHA256, "AUTHORIZED_SQL_SHA_DRIFT")
    starting = read(GOV / "starting_state_freeze.json")
    for item in starting["preserved_artifacts"]:
        require(sha256_file(Path(item["path"])) == item["sha256"], "OLD_ARTIFACT_DRIFT:" + item["path"])
    for key in ("frozen_R1F_source_inventory",):
        item = starting[key]
        require(sha256_file(Path(item["path"])) == item["sha256"], "HISTORICAL_DEFER_DRIFT")
    item = starting["frozen_R1F_0041"]["document"]
    require(sha256_file(Path(item["path"])) == item["sha256"], "HISTORICAL_DEFER_DRIFT")
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {}
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            name = entry.filename.removeprefix("foundation_backfill_web_sol_v1/")
            require(name != entry.filename and name not in members and not any(p in {"..", ""} for p in name.split("/")), "ARCHIVE_PATH_INVALID")
            members[name] = archive.read(entry)
    inventory = [{"path": n, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()} for n, data in sorted(members.items())]
    require(canonical_sha256(inventory) == old["package"]["inventory_sha256"] == INVENTORY_SHA, "INVENTORY_DRIFT")
    sibling = ARCHIVE.with_suffix("")
    inspection = sibling / "foundation_backfill_web_sol_v1"
    if sibling.exists():
        actual = [{"path": p.relative_to(inspection).as_posix(), "size": p.stat().st_size, "sha256": sha256_file(p)} for p in inspection.rglob("*") if p.is_file()]
        require(sorted(actual, key=lambda r: r["path"]) == inventory, "INSPECTION_COPY_DRIFT")
        require(not [p for p in sibling.rglob("*") if p.is_file() and not p.is_relative_to(inspection)], "INSPECTION_EXTRA_FILES")
    evidence = {e["evidence_id"]: e for e in json.loads(members["evidence_index.json"])}
    require(len(evidence) == 98 and len(old["registry"]["sources"]) == 33, "SOURCE_EVIDENCE_COUNT_DRIFT")
    accounting = {(a["kind"], a["object_id"]): a["content_sha256"] for a in old["package"]["object_accounting"]}
    for eid, e in evidence.items():
        require(canonical_sha256(e) == accounting["evidence", eid], "EVIDENCE_CONTENT_DRIFT:" + eid)
    for kind, records in old["objects"].items():
        for record in records:
            require(canonical_sha256(record["content"]["raw"]) == accounting[kind, record["candidate_id"]], "NATIVE_CANDIDATE_DRIFT")
    require(len(manifest["relation_native_authorizations"]) == 8 and all(r["role"] == "SUPPORTS" and r["relation_decision"] == "" for r in manifest["relation_native_authorizations"]), "NATIVE_ROLE_DRIFT")
    for r in manifest["relation_native_authorizations"]:
        require(canonical_sha256(evidence[r["evidence_id"]]) == r["evidence_sha256"], "NATIVE_EVIDENCE_DRIFT")
    return old, manifest, evidence


def audit_no_content_authority():
    checked = []
    for directory in sorted((ROOT / "workspace").glob("phase3f_foundation*")):
        for path in sorted(directory.rglob("*.json")):
            if any(part.startswith(("tests-", "test_", "pytest-")) for part in path.relative_to(directory).parts):
                continue
            value = read(path)
            if not isinstance(value, dict):
                continue
            if value.get("document_type") == "phase3f_foundation_baseline_review_packet":
                validate_review(value, expected_sha256=value["immutable_packet_sha256"], completed=False)
                checked.append(binding(path))
            require(not (value.get("adapter_type") == "phase3f_complete_foundation_v1" and value.get("intended_mutations")), "REAL_FOUNDATION_PAYLOAD_FOUND:" + str(path))
    return {"blank_packets_checked": checked, "scope": "All JSON artifacts in workspace/phase3f_foundation* excluding synthetic test directories", "real_foundation_payload_found": False}


def preflight(committed=False):
    old, manifest, evidence = immutable_inputs()
    require(git("branch", "--show-current") == "codex/phase3f-foundation-complete-baseline", "BRANCH_DRIFT")
    require(not git("diff", "--cached", "--name-only"), "UNEXPECTED_STAGED_FILES")
    head = git("rev-parse", "HEAD")
    if committed:
        require(git("rev-parse", "HEAD^") == PRE_COMMIT, "IMPLEMENTATION_PARENT_DRIFT")
        files = git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
        require(not git("diff", "HEAD", "--", *files), "COMMITTED_IMPLEMENTATION_WORKTREE_DRIFT")
        data = subprocess.check_output(["git", "show", "HEAD:" + SQL_PATH.relative_to(ROOT).as_posix()], cwd=ROOT)
        require(hashlib.sha256(data).hexdigest() == AUTHORIZED_SQL_SHA256, "COMMITTED_SQL_BYTES_DRIFT")
    else:
        require(head == STOPPED_COMMIT, "PRE_COMMIT_HEAD_DRIFT")
        files = []
    require(load_config(ROOT / "config.toml").db_path.resolve() == PRODUCTION.resolve(), "CONFIGURED_PRODUCTION_DRIFT")
    production = production_identity(PRODUCTION)
    require(production == old["production_baseline"] and production["sha256"] == OLD_SHA, "AUTHORIZED_PRODUCTION_IDENTITY_DRIFT")
    with closing(connect_read_only(PRODUCTION)) as con:
        views = official(con)
        require(con.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "UNVALIDATED_JOURNAL_MODE")
    prior_views = read(ROOT / "workspace/phase3f_foundation_execution_contract_preparation/qualified/starting_state_freeze.json")["official_views"]["official_views"]
    require(views["official_views"] == prior_views and len(prior_views) == 2, "OFFICIAL_CURRENT_VIEWS_DRIFT")
    authority = INSTRUCTION.read_text(encoding="utf-8")
    require("I explicitly authorize" in authority and OLD_SHA in authority and AUTHORIZED_SQL_SHA256 in authority, "HUMAN_AUTHORIZATION_BINDING_MISSING")
    return {"production": production, "views": views, "head": head, "pre_commit_head": PRE_COMMIT,
            "refrozen_from_stopped_commit": STOPPED_COMMIT, "resumption_authority": binding(OUT / "resumption_authority.json"),
            "committed_files": files, "sql": binding(SQL_PATH), "authorization": binding(INSTRUCTION),
            "archive": binding(ARCHIVE), "inventory_sha256": INVENTORY_SHA, "manifest_sha256": manifest["manifest_sha256"],
            "content_authority_audit": audit_no_content_authority(), "git_status": git("status", "--short")}


def rehearse():
    pre = preflight()
    freeze("starting_state_freeze.json", pre)
    target = OUT / "rehearsal_only.db"
    require(not target.exists(), "REHEARSAL_TARGET_ALREADY_EXISTS")
    shutil.copyfile(PRODUCTION, target)
    result = execute_authorized_schema_migration(target, configured_production_path=target, expected_old_sha256=OLD_SHA,
        expected_sql_sha256=AUTHORIZED_SQL_SHA256, backup_path=OUT / "rehearsal_recovery_only.db")
    old, manifest, evidence = immutable_inputs()
    with closing(connect_read_only(target)) as con:
        objects = requalify(old, manifest, con, evidence)
        require(official(con) == pre["views"], "REHEARSAL_OFFICIAL_DRIFT")
    require({k: len(v) for k, v in objects.items()} == EXPECTED_COUNTS, "REHEARSAL_COUNTS")
    freeze("rehearsal_result.json", {"migration": result, "qualified_counts": EXPECTED_COUNTS, "real_blank_packet_generated": False})
    print("REHEARSAL_PASS; no Production mutation; no new real packet")


def migrate():
    pre = preflight(committed=True)
    freeze("committed_preflight.json", pre)
    require_exclusive_read_handle(PRODUCTION)
    freeze("write_quiescence_preflight.json", {"exclusive_handle_probe": "PASS", "application_started": False,
        "checkpoint": "NOT_REQUIRED_DELETE_JOURNAL_NO_SIDECARS", "writer_exclusion": "BEGIN IMMEDIATE reservation rechecks old SHA before backup/DDL"})
    timestamp = datetime.now(timezone.utc).isoformat()
    result = execute_authorized_schema_migration(PRODUCTION, configured_production_path=load_config(ROOT / "config.toml").db_path,
        expected_old_sha256=OLD_SHA, expected_sql_sha256=AUTHORIZED_SQL_SHA256, backup_path=OUT / "recovery/pro_a_schema_0_2_1_authorized_original.db")
    with closing(connect_read_only(PRODUCTION)) as con:
        require_execution_schema(con)
        views = official(con)
    require(views == pre["views"], "POST_MIGRATION_OFFICIAL_DRIFT")
    freeze("migration_receipt.json", {**result, "implementation_commit": pre["head"], "migration_timestamp": timestamp,
        "official_views_before": pre["views"], "official_views_after": views, "manifest_sha256": MANIFEST_SHA,
        "contract_sha256": CONTRACT_SHA256, "authorization": pre["authorization"]})
    freeze("new_production_baseline.json", {**result["after"], "implementation_commit": pre["head"], "sql_sha256": AUTHORIZED_SQL_SHA256,
        "contract_sha256": CONTRACT_SHA256, "governance_manifest_sha256": MANIFEST_SHA,
        "governance_manifest_id": "FOUNDATION_GOVERNANCE_3C35BA646C5DC664", "migration_timestamp": timestamp,
        "backup_sha256": result["backup"]["sha256"], "official_views": views})
    print(json.dumps({"migration": result["status"], "new_production_sha256": result["after"]["sha256"], "schema": "0.2.3"}))


def require_exclusive_read_handle(path):
    """Keep the OS quiescence gate independent of SQLite transaction handling."""
    command = "$probe = [System.IO.File]::Open('" + str(path).replace("'", "''") + "',[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::None); $probe.Dispose()"
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", "$ErrorActionPreference='Stop'; " + command], check=True)


def requalification():
    migration = read(OUT / "migration_receipt.json")
    require(production_identity(PRODUCTION) == migration["after"], "NEW_PRODUCTION_BASELINE_DRIFT")
    require(git("rev-parse", "HEAD") == migration["implementation_commit"], "IMPLEMENTATION_COMMIT_DRIFT")
    old, manifest, evidence = immutable_inputs()
    with closing(connect_read_only(PRODUCTION)) as con:
        objects = requalify(old, manifest, con, evidence)
        require(official(con) == migration["official_views_before"], "OFFICIAL_DRIFT_DURING_REQUALIFICATION")
    # No packet is emitted until the full deterministic qualification above passes.
    packet = build_review_packet(package=old["package"], registry=old["registry"], production=migration["after"],
        repository_commit=migration["implementation_commit"], objects=objects, timestamp=migration["migration_timestamp"],
        execution_contract=BOUND_CONTRACT, evidence_governance_manifest=manifest)
    packet["migration_binding"] = {"sql_sha256": AUTHORIZED_SQL_SHA256, "implementation_commit": migration["implementation_commit"],
        "old_packet_sha256": OLD_PACKET_SHA, "governance_manifest_sha256": MANIFEST_SHA, "new_production_sha256": migration["after"]["sha256"],
        "schema_version": "0.2.3", "archive_sha256": ARCHIVE_SHA, "package_inventory_sha256": INVENTORY_SHA}
    packet["immutable_packet_sha256"] = canonical_sha256(blank_body(packet))
    validate_review(packet, expected_sha256=packet["immutable_packet_sha256"], completed=False)
    validate_files(packet)
    require(packet["packet_id"] != old["packet_id"] and packet["counts"] == EXPECTED_COUNTS, "NEW_PACKET_ID_OR_COUNTS_DRIFT")
    batches = claim_batches(packet)
    ids = {cid for b in batches for cid in b["candidate_ids"]}
    require(len(ids) == 66 and "FND_CLAIM_0067" in ids and "FND_CLAIM_0066" not in ids, "CLAIM_BATCH_QUALIFICATION_DRIFT")
    census = temporal_census(packet)
    require(census["lossless_count"] == 56 and len(census["category_counts"]) == 21, "TEMPORAL_CENSUS_DRIFT")
    require(census["category_counts"] == temporal_census(old)["category_counts"], "TEMPORAL_CATEGORY_DRIFT")
    with closing(connect_read_only(Path(migration["backup"]["path"]))) as con:
        comparison = compare_all_rows(old, packet, identity_snapshot(con))
    require(len(comparison) == 295 and all(r["explained"] for r in comparison), "UNEXPLAINED_REVIEW_DRIFT")
    freeze("foundation_complete_review_packet_schema_0_2_3.json", packet)
    freeze("all_295_rows_old_new_comparison.json", {"records": comparison, "classification_counts": dict(Counter(r["classification"] for r in comparison)), "unexplained_drift": 0})
    freeze("claim_batch_authorization_template.json", {"packet_id": packet["packet_id"], "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "batches": batches, "individual_exceptions": ["FND_CLAIM_0066"], "production_apply_authorized": False})
    freeze("relation_temporal_census.json", census)
    freeze("requalification_receipt.json", {"counts": packet["counts"], "sources_materialized": 33, "evidence": 98,
        "packet_id": packet["packet_id"], "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "packet_file": binding(OUT / "foundation_complete_review_packet_schema_0_2_3.json"),
        "comparison_counts": dict(Counter(r["classification"] for r in comparison)), "native_content_unchanged": 295,
        "claim_batchable": 66, "claim_individual_exceptions": ["FND_CLAIM_0066"], "native_supports": 8, "native_contradicts": 0,
        "human_decisions_present": False, "real_payload_built": False, "cloud_llm_calls": 0, "local_llm_calls": 0,
        "mechanical_requalification_pass": True, "readiness_pending_final_regression": True})
    require(production_identity(PRODUCTION) == migration["after"], "REQUALIFICATION_CHANGED_PRODUCTION")
    print(json.dumps({"packet_id": packet["packet_id"], "packet_sha256": packet["immutable_packet_sha256"], "rows_compared": 295, "human_decisions": 0}))


def finalize():
    migration = read(OUT / "migration_receipt.json")
    qualification = read(OUT / "requalification_receipt.json")
    pre = read(OUT / "committed_preflight.json")
    old, manifest, _ = immutable_inputs()
    packet = read(OUT / "foundation_complete_review_packet_schema_0_2_3.json")
    validate_review(packet, expected_sha256=qualification["immutable_packet_sha256"], completed=False)
    validate_files(packet)
    require(production_identity(PRODUCTION) == migration["after"], "FINAL_PRODUCTION_DRIFT")
    require(git("rev-parse", "HEAD") == pre["head"] and not git("diff", "HEAD", "--", *pre["committed_files"]), "FINAL_IMPLEMENTATION_DRIFT")
    require(not git("diff", "--cached", "--name-only"), "FINAL_STAGED_FILES")
    tests = {}
    for name in ("precommit_full_regression.xml", "postmigration_full_regression.xml"):
        suites = ET.parse(OUT / name).getroot().findall("testsuite")
        counts = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
        require(counts["failures"] == counts["errors"] == 0 and counts["tests"] >= 400, "REGRESSION_NOT_PASS")
        skipped = [{"name": c.get("name"), "reason": c.find("skipped").get("message")} for s in suites for c in s.findall("testcase") if c.find("skipped") is not None]
        require(skipped == [{"name": "test_symlink_equivalent_production_path_is_blocked", "reason": "Symlink creation is unavailable on this platform"}], "UNEXPECTED_TEST_SKIP")
        tests[name] = {**counts, "passed": counts["tests"] - counts["skipped"], "skipped_details": skipped, "artifact": binding(OUT / name)}
    with closing(connect_read_only(PRODUCTION)) as con:
        require_execution_schema(con)
        require(official(con) == pre["views"], "FINAL_OFFICIAL_DRIFT")
    audit = audit_no_content_authority()
    require(production_identity(Path(migration["backup"]["path"])) == migration["backup"], "RECOVERY_ARTIFACT_DRIFT")
    statuses = {"PHASE3F_SCHEMA_0_2_3_MIGRATION_COMPLETE": True, "AUTHORIZED_OLD_PRODUCTION_SHA_MATCH": True,
        "AUTHORIZED_SQL_SHA_MATCH": True, "MIGRATION_IMPLEMENTATION_COMMIT_CREATED": True,
        "MIGRATION_IMPLEMENTATION_COMMIT_PUSHED": False, "PRODUCTION_SCHEMA_VERSION": "0.2.3", "PRODUCTION_CHANGED": True,
        "NEW_PRODUCTION_SHA256": migration["after"]["sha256"], "PRODUCTION_INTEGRITY": "ok", "PRODUCTION_FK_VIOLATIONS": 0,
        "OFFLINE_BACKUP_VERIFIED": True, "OFFICIAL_CURRENT_VIEWS_UNCHANGED": True,
        "FOUNDATION_ARCHIVE_UNCHANGED": True, "FOUNDATION_PACKAGE_UNCHANGED": True,
        "RELATION_NATIVE_GOVERNANCE_REQUALIFIED": True, "CLAIM_0067_ADJUDICATION_REQUALIFIED": True,
        "CLAIM_0066_EXCEPTION_PRESERVED": True, "NEW_BLANK_REVIEW_PACKET_GENERATED": True,
        "NEW_BLANK_REVIEW_PACKET_VALID": True, "HUMAN_DECISIONS_PRESENT": False, "ALL_295_ROWS_COMPARED": True,
        "REAL_FOUNDATION_EXECUTABLE_PAYLOAD_BUILT": False, "FOUNDATION_CONTENT_APPLIED": False,
        "CLOUD_LLM_CALLS": 0, "LOCAL_LLM_CALLS": 0, "READY_FOR_FOUNDATION_COMPLETE_HUMAN_REVIEW": True,
        "PHASE3F_FOUNDATION_COMPLETE": False, "PUSH_PR_STATUS": "NOT_PERFORMED",
        "NEXT_REQUIRED_ACTION": "HUMAN_REVIEW_OF_NEW_IMMUTABLE_FOUNDATION_PACKET"}
    receipt = {"phase": "PHASE3F_FOUNDATION_SCHEMA_0_2_3_MIGRATION_AND_REQUALIFICATION", **statuses,
        "pre_commit_head": PRE_COMMIT, "implementation_commit": pre["head"], "committed_files": pre["committed_files"],
        "sql": pre["sql"], "authorization": pre["authorization"], "migration": migration, "qualification": qualification,
        "resumption_authority": pre["resumption_authority"], "refrozen_from_stopped_commit": STOPPED_COMMIT,
        "tests": tests, "postmigration_historical_tests_excluded": [
            "test_all_295_native_objects_and_original_frozen_artifacts_unchanged",
            "test_exact_frozen_production_ddl_migrates_with_synthetic_rows_only",
            "test_full_old_baseline_preflight_releases_handle_without_gc"],
        "historical_test_exclusion_reason": "These require the authorized old Production byte/schema baseline and passed before migration. New read-only migrated-schema tests cover the new baseline; the original old-baseline tests remain unmodified.",
        "archive_sha256_before_after": ARCHIVE_SHA, "package_inventory_sha256_before_after": INVENTORY_SHA,
        "manifest_id": manifest["manifest_id"], "manifest_sha256": MANIFEST_SHA, "content_authority_audit": audit,
        "remaining_git_status": git("status", "--short"), "readiness_blockers": []}
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    freeze("schema_migration_and_requalification_receipt.json", receipt)
    file_lines = "\n".join("- `" + f + "`" for f in pre["committed_files"])
    test_lines = "\n".join(f"- {name}: {value['passed']} passed / {value['failures']} failed / {value['skipped']} skipped" for name, value in tests.items())
    views = "\n".join(f"- {r['view_id']}: `{r['row_sha256']}` (before = after)" for r in pre["views"]["official_views"])
    report = f"""# Phase 3F schema 0.2.3 migration and requalification — PASS / STOP before Human Review

READY_FOR_FOUNDATION_COMPLETE_HUMAN_REVIEW = true. This authorizes no content acceptance.
PHASE3F_FOUNDATION_COMPLETE = false. All 295 content decisions remain blank.

## Exact authorization and local implementation freeze

Pre-migration/pre-commit HEAD: `{PRE_COMMIT}`

Bounded implementation commit: `{pre['head']}`; branch codex/phase3f-foundation-complete-baseline.
Exactly one local commit; no push, PR or merge. No workspace artifacts, PDFs, virtual environments,
Playwright files, historical scripts or Stage 2 untracked material were committed.
The six previously dirty integration files are scoped Foundation/Baseline isolation dependencies;
their exact changes and every new file were reviewed and tested before the commit.

The user explicitly authorized resuming after the prior connection-lifetime STOP. The original local
commit `{STOPPED_COMMIT}` was amended into this refrozen implementation; the parent remains unchanged.
Prior STOP receipt, diagnostics, tests and recovery/rehearsal artifacts are preserved byte-identically
in the parent output directory. This resumed directory is the authoritative successful run.
Read-only connections now close deterministically through contextlib.closing on normal/exception exits.
No GC workaround or quiescence-gate bypass is used. The new full preflight/OS-handle integration test
first reproduced the original failure with GC disabled, then passed with explicit closure.

Committed files:

{file_lines}

Canonical SQL path: `{SQL_PATH}`

Authorized SQL filesystem and committed blob SHA256: `{AUTHORIZED_SQL_SHA256}`

Exact bytes retained, including the historical PREPARE ONLY comment; explicit authorization is separately frozen.
No dynamic SQL regeneration or superseded SQL execution occurred.
Human authorization file/SHA: `{pre['authorization']['path']}` / `{pre['authorization']['sha256']}`.

## Production, recovery and transaction

Old Production path: `{PRODUCTION}`

Old SHA256: `{OLD_SHA}`; schema 0.2.1. Exact configured identity matched, integrity ok, FK violations 0.
New SHA256: `{migration['after']['sha256']}`; schema 0.2.3. Integrity ok, FK violations 0.
New physical schema SHA256: `{migration['after']['schema_sha256']}`.
Execution contract SHA256: `{CONTRACT_SHA256}`.
Migration timestamp (UTC): `{migration['migration_timestamp']}`.

Offline recovery artifact: `{migration['backup']['path']}`

Backup SHA256: `{migration['backup']['sha256']}`; byte-identical to authorized old Production,
independently reopened with integrity ok / FK 0 / all old semantic fingerprints equal.
The backup is retained as recovery infrastructure, not a new Production baseline.

Preflight and final -wal/-shm/-journal: all absent. DELETE journal required; no checkpoint,
journal normalization, application start or background writer start. OS exclusive-handle probe passed.
BEGIN IMMEDIATE reserved the sole SQLite writer before backup and DDL; the exact old SHA was
rechecked under that reservation. Exact-file COMMIT executed only after schema/integrity/FK/
legacy-data checks passed. No retry, repair, restore or ad hoc Production SQL was needed.

All legacy table rows remained semantically identical except reviewed meta fields and the
legacy Claim-linked Evidence backfill ({migration['legacy_diff']['legacy_evidence_backfill_count']} rows).
Claims, Relations, Sources, Nodes, Aliases and every prior Current View/Baseline were preserved.
Full per-table counts/fingerprints are in migration_receipt.json. No Foundation candidates were promoted.
relation_temporal_semantics and relation_evidence_authorizations remain empty; active native links = 0.
Eight role authorities remain solely in the frozen manifest until later valid content review.
All exact Baseline namespace/immutability/predecessor, temporal and discriminated Evidence CHECK/FK/index/trigger guards verified.

## Official Current Views and immutable corpus

Exactly two official Current Views, full row fingerprints:

{views}

Latest-official selection uses the unchanged application ordering and yields identical rows before/after;
the complete per-node selection fingerprints are in migration_receipt.json.

Archive SHA256 before/after: `{ARCHIVE_SHA}`.
Package inventory SHA256 before/after: `{INVENTORY_SHA}`.
Archive SHA was frozen before ZIP inspection; sibling copy deterministically matched every normalized path/size/hash,
with no extra files. No archive repackaging or source PDF reparsing. Source files were only rehashed.
33/33 Sources materialized; all Source SHA identities, 98 Evidence and 295 native candidate hashes exact.
All previous packets, receipts, qualification artifacts and frozen R1F_0041 DEFER artifacts unchanged.

Governance manifest ID: `{manifest['manifest_id']}`; semantic SHA `{MANIFEST_SHA}`.
All 8 native SUPPORTS for the five named Relations requalified exactly; 0 CONTRADICTS.
No scope/proposition/source/evidence substitutions, no duplicate Claims, no Node/Relation decisions.
CPO remains external-laser implementation_variant / some implementations; R1F_0041 DEFER remains intact.
Claim-linked paths still require qualified KEEP; KEEP_NEEDS_REVIEW/DROP/blank/unresolved qualification are inadmissible.

Claim0067 authoritative Evidence is EV_F030B_P001_R5795; sibling EV_F030B_P001_MEGTRON8 retained.
Source/locator/excerpt/date/nature checks passed. 66 Claims are ordinarily batchable.
Claim0066 remains the sole missing-time individual exception, unbatched, with KEEP blocked and no invented date.
All 56 temporal projections are lossless, preserving all 21 original categories.
All 9 Baselines qualify only as historical Foundation references under immutable guards, never official Current Views.

## New immutable blank packet and all-row comparison

Packet ID: `{packet['packet_id']}`

Packet semantic SHA256: `{packet['immutable_packet_sha256']}`

Packet file SHA256: `{qualification['packet_file']['sha256']}`

Packet path: `{qualification['packet_file']['path']}`

Bound to the new Production SHA/schema, implementation commit, authorized SQL, manifest, original archive/inventory.
Old packet `{old['packet_id']}` / `{OLD_PACKET_SHA}` is preserved, not overwritten or reinterpreted.
Review rows: Nodes 138 / Aliases 25 / Claims 67 / Relations 56 / Baselines 9 = 295; Current View candidates 0.
Human decisions, reviewer/reason/target fields and batch authority are all blank.

All 295 rows compared in all_295_rows_old_new_comparison.json, with both native hashes, both projection hashes,
both target resolutions, both qualifications, explanations, human-review-semantic flag and explicit classification.
Native content unchanged: 295. Expected projection changes: 295 (post-migration qualification bindings).
SEMANTICALLY_UNCHANGED_REQUALIFIED: 172. REVIEW_SEMANTICS_CHANGED: 123 (67 Claim admission + 56 Relation contracts).
BLOCKED: 0 at mechanical packet readiness; INVALID: 0; unexplained drift: 0.
The known Claim0066 content-admission exception is explicitly retained, not hidden or called executable.
Human Review readiness permits governed non-executable dispositions; it is not universal promotion eligibility.

## Tests and final boundary

{test_lines}

Only skip: Windows symlink creation unavailable. Pre-commit suite includes all old-Production assertions.
Post-migration suite explicitly deselects the two historical old-SHA/old-DDL assertions plus the old-baseline
preflight integration test; none can run against the newly migrated baseline without invalidating their premises.
The historical test files remain unchanged;
new read-only migrated-schema and all-row requalification checks cover the current baseline.
Tests execute writes on synthetic fixtures only. Actual Production reads are immutable/read-only.
Exact-file migration failure injection and concurrent-writer rejection passed; retained backup verified again at finalization.
The complete test XMLs, counts and exclusion names are in the final receipt.

Cloud LLM calls = 0; local LLM calls = 0; original PDF reparses = 0.
Real executable Foundation payload built = false; Foundation content applied = false.
Push/PR/merge = NOT_PERFORMED. Staged files = empty.

Remaining unrelated git status (preserved outside the bounded commit):

```text
{receipt['remaining_git_status']}
```

Next required action: HUMAN_REVIEW_OF_NEW_IMMUTABLE_FOUNDATION_PACKET.
STOP. No content decisions, executable payload, candidate application or push may follow in this run.
"""
    freeze("schema_migration_and_requalification_report.md", report)
    print(json.dumps({"ready_for_human_review": True, "foundation_complete": False, "receipt_sha256": receipt["receipt_sha256"], "new_production_sha256": migration["after"]["sha256"], "packet_id": packet["packet_id"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["preflight", "rehearse", "migrate", "requalify", "finalize"])
    args = parser.parse_args()
    if args.phase == "preflight":
        print(json.dumps(preflight(), ensure_ascii=False, indent=2))
    elif args.phase == "rehearse":
        rehearse()
    elif args.phase == "migrate":
        migrate()
    elif args.phase == "requalify":
        requalification()
    else:
        finalize()
