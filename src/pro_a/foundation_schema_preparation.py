"""Explicit schema proposal and synthetic-only migration qualification.

No automatic Production upgrade. The test executor refuses the configured
Production path, aliases/hardlinks, and an unrecognized byte baseline.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3

from .baseline_views import BASELINE_GUARDS, require_baseline_guards
from .foundation_execution_contract import CONTRACT_SHA256
from .production_promotion import (
    PromotionError, assert_shadow_target, sha256_file, database_rows, schema_sha256,
)


NEXT_SCHEMA_VERSION = "0.2.3"
NATIVE_INDEXES = {
    "idx_native_evidence_identity": "CREATE UNIQUE INDEX idx_native_evidence_identity ON relation_evidence_links(relation_id,evidence_id,evidence_role) WHERE provenance_mode='RELATION_NATIVE'",
    "idx_native_authorization_identity": "CREATE UNIQUE INDEX idx_native_authorization_identity ON relation_evidence_authorizations(relation_id,evidence_id,evidence_role,packet_sha256) WHERE provenance_mode='RELATION_NATIVE'",
}
LEGACY_EVIDENCE_TABLE = """CREATE TABLE IF NOT EXISTS relation_evidence_links (
 relation_id TEXT NOT NULL REFERENCES node_relations(relation_id) ON DELETE CASCADE,
 claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
 evidence_role TEXT NOT NULL CHECK(evidence_role IN ('supports','contradicts')),
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','retired')),
 created_at TEXT NOT NULL,
 PRIMARY KEY(relation_id,claim_id,evidence_role)
)"""
EVIDENCE_TABLE = """CREATE TABLE relation_evidence_links (
 relation_id TEXT NOT NULL REFERENCES node_relations(relation_id) ON DELETE CASCADE,
 claim_id TEXT REFERENCES claims(claim_id) ON DELETE CASCADE,
 evidence_role TEXT NOT NULL CHECK(evidence_role IN ('supports','contradicts')),
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','retired')),
 created_at TEXT NOT NULL,
 provenance_mode TEXT NOT NULL DEFAULT 'CLAIM_LINKED' CHECK(provenance_mode IN ('CLAIM_LINKED','RELATION_NATIVE')),
 evidence_id TEXT NOT NULL DEFAULT '',
 source_id TEXT REFERENCES sources(source_id) ON DELETE RESTRICT,
 source_sha256 TEXT NOT NULL DEFAULT '',
 evidence_sha256 TEXT NOT NULL DEFAULT '',
 authorization_id TEXT REFERENCES relation_evidence_authorizations(link_candidate_id) ON DELETE RESTRICT,
 PRIMARY KEY(relation_id,claim_id,evidence_role),
 CHECK((provenance_mode='CLAIM_LINKED' AND claim_id IS NOT NULL AND length(trim(claim_id))>0
        AND evidence_id='' AND source_id IS NULL AND source_sha256='' AND evidence_sha256='' AND authorization_id IS NULL)
    OR (provenance_mode='RELATION_NATIVE' AND claim_id IS NULL AND length(trim(evidence_id))>0
        AND source_id IS NOT NULL AND length(source_sha256)=64 AND length(evidence_sha256)=64 AND authorization_id IS NOT NULL))
)"""
TEMPORAL_TABLE = """CREATE TABLE relation_temporal_semantics (
 relation_id TEXT PRIMARY KEY NOT NULL REFERENCES node_relations(relation_id) ON DELETE RESTRICT,
 temporal_category TEXT NOT NULL CHECK(length(trim(temporal_category))>0),
 valid_from_supplied INTEGER NOT NULL CHECK(valid_from_supplied IN (0,1)),
 valid_to_supplied INTEGER NOT NULL CHECK(valid_to_supplied IN (0,1)),
 projection_sha256 TEXT NOT NULL CHECK(length(projection_sha256)=64),
 contract_sha256 TEXT NOT NULL CHECK(length(contract_sha256)=64),
 provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json))
)"""
AUTHORIZATION_TABLE = """CREATE TABLE relation_evidence_authorizations (
 link_candidate_id TEXT PRIMARY KEY NOT NULL,
 relation_id TEXT NOT NULL REFERENCES node_relations(relation_id) ON DELETE RESTRICT,
 claim_id TEXT REFERENCES claims(claim_id) ON DELETE RESTRICT,
 relation_candidate_id TEXT NOT NULL CHECK(length(trim(relation_candidate_id))>0),
 provenance_mode TEXT NOT NULL CHECK(provenance_mode IN ('CLAIM_LINKED','RELATION_NATIVE')),
 evidence_id TEXT NOT NULL CHECK(length(trim(evidence_id))>0),
 source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE RESTRICT,
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
 evidence_sha256 TEXT NOT NULL CHECK(length(evidence_sha256)=64),
 evidence_role TEXT NOT NULL CHECK(evidence_role IN ('supports','contradicts')),
 authorization_state TEXT NOT NULL CHECK(authorization_state='AUTHORIZED'),
 relation_decision TEXT NOT NULL CHECK(relation_decision IN ('','CREATE','REUSE')),
 claim_decision TEXT CHECK(claim_decision IS NULL OR claim_decision='KEEP'),
 contract_sha256 TEXT NOT NULL CHECK(length(contract_sha256)=64),
 packet_sha256 TEXT NOT NULL CHECK(length(packet_sha256)=64),
 reviewer TEXT NOT NULL CHECK(length(trim(reviewer))>0),
 human_authorization_manifest_id TEXT NOT NULL DEFAULT '',
 original_packet_sha256 TEXT NOT NULL DEFAULT '',
 proposition_scope TEXT NOT NULL DEFAULT '',
 authorized_proposition TEXT NOT NULL DEFAULT '',
 provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json)),
 created_at TEXT NOT NULL,
 UNIQUE(relation_id,claim_id,evidence_role,evidence_id,packet_sha256),
 CHECK((provenance_mode='CLAIM_LINKED' AND claim_id IS NOT NULL AND claim_decision IS NOT NULL AND claim_decision='KEEP' AND relation_decision IN ('CREATE','REUSE'))
    OR (provenance_mode='RELATION_NATIVE' AND claim_id IS NULL AND claim_decision IS NULL AND relation_decision=''
        AND length(trim(human_authorization_manifest_id))>0 AND length(original_packet_sha256)=64
        AND length(trim(proposition_scope))>0 AND length(trim(authorized_proposition))>0))
)"""


def governance_guards():
    guards = {
        "foundation_temporal_insert": f"""CREATE TRIGGER foundation_temporal_insert BEFORE INSERT ON relation_temporal_semantics
BEGIN
 SELECT CASE WHEN NEW.contract_sha256<>'{CONTRACT_SHA256}' OR NOT EXISTS (
 SELECT 1 FROM node_relations WHERE relation_id=NEW.relation_id AND status='categorical')
 OR json_extract(NEW.provenance_json,'$.native_temporal.temporal_status') IS NOT NEW.temporal_category
 OR NEW.valid_from_supplied<>CASE WHEN json_type(NEW.provenance_json,'$.native_temporal.valid_from') IS NULL THEN 0 ELSE 1 END
 OR NEW.valid_to_supplied<>CASE WHEN json_type(NEW.provenance_json,'$.native_temporal.valid_to') IS NULL THEN 0 ELSE 1 END
 OR (json_type(NEW.provenance_json,'$.native_temporal.valid_from') IS NOT NULL
     AND json_type(NEW.provenance_json,'$.native_temporal.valid_from') NOT IN ('text','null'))
 OR (json_type(NEW.provenance_json,'$.native_temporal.valid_to') IS NOT NULL
     AND json_type(NEW.provenance_json,'$.native_temporal.valid_to') NOT IN ('text','null'))
 OR EXISTS (SELECT 1 FROM node_relations n WHERE n.relation_id=NEW.relation_id AND (
     n.valid_from<>coalesce(json_extract(NEW.provenance_json,'$.native_temporal.valid_from'),'')
     OR n.valid_to<>coalesce(json_extract(NEW.provenance_json,'$.native_temporal.valid_to'),'')))
 THEN RAISE(ABORT,'TEMPORAL_CATEGORY_CONTRACT_REQUIRED') END;
END""",
        "foundation_temporal_relation_update": """CREATE TRIGGER foundation_temporal_relation_update BEFORE UPDATE ON node_relations
WHEN EXISTS (SELECT 1 FROM relation_temporal_semantics WHERE relation_id=OLD.relation_id)
BEGIN
 SELECT CASE WHEN NEW.relation_id IS NOT OLD.relation_id OR NEW.from_node_id IS NOT OLD.from_node_id
 OR NEW.to_node_id IS NOT OLD.to_node_id OR NEW.relation_type IS NOT OLD.relation_type OR NEW.scope IS NOT OLD.scope
 OR NEW.valid_from IS NOT OLD.valid_from OR NEW.valid_to IS NOT OLD.valid_to OR NEW.status NOT IN ('categorical','retired')
 THEN RAISE(ABORT,'TEMPORAL_RELATION_REQUALIFICATION_REQUIRED') END;
END""",
        "foundation_evidence_authorization_insert": f"""CREATE TRIGGER foundation_evidence_authorization_insert
BEFORE INSERT ON relation_evidence_authorizations
WHEN NEW.provenance_mode='CLAIM_LINKED'
BEGIN
 SELECT CASE WHEN NEW.contract_sha256<>'{CONTRACT_SHA256}' OR NOT EXISTS (
 SELECT 1 FROM claims c JOIN sources s ON s.source_id=c.source_id
 WHERE c.claim_id=NEW.claim_id AND c.status='current' AND c.source_id=NEW.source_id AND s.sha256=NEW.source_sha256
 AND json_valid(c.structured_json)
 AND json_extract(c.structured_json,'$.foundation_admission.decision')='KEEP'
 AND json_extract(c.structured_json,'$.foundation_admission.contract_sha256')=NEW.contract_sha256
 AND json_extract(c.structured_json,'$.foundation_admission.immutable_packet_sha256')=NEW.packet_sha256
 AND json_extract(c.structured_json,'$.foundation_admission.reviewer')=NEW.reviewer)
 OR NOT EXISTS (SELECT 1 FROM relation_temporal_semantics t WHERE t.relation_id=NEW.relation_id
 AND json_extract(t.provenance_json,'$.native_relation_sha256')=json_extract(NEW.provenance_json,'$.candidate.native_relation_sha256')
 AND json_extract(t.provenance_json,'$.package_sha256')=json_extract(NEW.provenance_json,'$.candidate.package_sha256'))
 OR json_extract(NEW.provenance_json,'$.candidate.link_candidate_id') IS NOT NEW.link_candidate_id
 OR json_extract(NEW.provenance_json,'$.candidate.contract_sha256') IS NOT NEW.contract_sha256
 OR coalesce(length(trim(json_extract(NEW.provenance_json,'$.relation_reason'))),0)=0
 OR json_extract(NEW.provenance_json,'$.candidate.claim_id') IS NOT NEW.claim_id
 OR json_extract(NEW.provenance_json,'$.candidate.evidence_id') IS NOT NEW.evidence_id
 OR json_extract(NEW.provenance_json,'$.candidate.evidence_sha256') IS NOT NEW.evidence_sha256
 OR json_extract(NEW.provenance_json,'$.candidate.source_id') IS NOT NEW.source_id
 OR json_extract(NEW.provenance_json,'$.candidate.source_sha256') IS NOT NEW.source_sha256
 OR json_extract(NEW.provenance_json,'$.candidate.authorization_state') IS NOT 'UNAUTHORIZED'
 OR (NEW.evidence_role='contradicts' AND json_extract(NEW.provenance_json,'$.candidate.explicit_role') IS NOT 'CONTRADICTS')
 OR (NEW.evidence_role='supports' AND json_extract(NEW.provenance_json,'$.candidate.explicit_role') IS NOT NULL
     AND json_extract(NEW.provenance_json,'$.candidate.explicit_role') IS NOT 'SUPPORTS')
 THEN RAISE(ABORT,'EXPLICIT_HUMAN_EVIDENCE_AUTHORIZATION_REQUIRED') END;
END""",
        "foundation_native_authorization_insert": f"""CREATE TRIGGER foundation_native_authorization_insert BEFORE INSERT ON relation_evidence_authorizations
WHEN NEW.provenance_mode='RELATION_NATIVE'
BEGIN
 SELECT CASE WHEN NEW.contract_sha256<>'{CONTRACT_SHA256}' OR NOT EXISTS (
 SELECT 1 FROM sources s WHERE s.source_id=NEW.source_id AND s.sha256=NEW.source_sha256)
 OR NOT EXISTS (SELECT 1 FROM node_relations n JOIN relation_temporal_semantics t USING(relation_id)
 WHERE n.relation_id=NEW.relation_id AND n.scope=NEW.proposition_scope AND n.status='categorical'
 AND json_extract(t.provenance_json,'$.native_relation_sha256')=json_extract(NEW.provenance_json,'$.candidate.native_relation_sha256')
 AND json_extract(t.provenance_json,'$.candidate_id')=NEW.relation_candidate_id
 AND json_extract(t.provenance_json,'$.package_sha256')=json_extract(NEW.provenance_json,'$.candidate.package_sha256')
 AND t.temporal_category=json_extract(NEW.provenance_json,'$.candidate.temporal_status'))
 OR json_extract(NEW.provenance_json,'$.projected_relation_id') IS NOT NEW.relation_id
 OR json_extract(NEW.provenance_json,'$.candidate.relation_candidate_id') IS NOT NEW.relation_candidate_id
 OR json_extract(NEW.provenance_json,'$.candidate.link_candidate_id') IS NOT NEW.link_candidate_id
 OR json_extract(NEW.provenance_json,'$.candidate.evidence_id') IS NOT NEW.evidence_id
 OR json_extract(NEW.provenance_json,'$.candidate.evidence_sha256') IS NOT NEW.evidence_sha256
 OR json_extract(NEW.provenance_json,'$.candidate.source_id') IS NOT NEW.source_id
 OR json_extract(NEW.provenance_json,'$.candidate.source_sha256') IS NOT NEW.source_sha256
 OR json_extract(NEW.provenance_json,'$.candidate.scope') IS NOT NEW.proposition_scope
 OR json_extract(NEW.provenance_json,'$.candidate.authorized_proposition') IS NOT NEW.authorized_proposition
 OR json_extract(NEW.provenance_json,'$.candidate.human_authorization_manifest_id') IS NOT NEW.human_authorization_manifest_id
 OR json_extract(NEW.provenance_json,'$.candidate.original_packet_sha256') IS NOT NEW.original_packet_sha256
 OR json_extract(NEW.provenance_json,'$.candidate.contract_sha256') IS NOT NEW.contract_sha256
 OR json_extract(NEW.provenance_json,'$.candidate.role') IS NOT upper(NEW.evidence_role)
 OR json_extract(NEW.provenance_json,'$.candidate.authorized') IS NOT 1
 OR json_extract(NEW.provenance_json,'$.candidate.relation_decision') IS NOT ''
 THEN RAISE(ABORT,'EXACT_SCOPED_NATIVE_EVIDENCE_AUTHORIZATION_REQUIRED') END;
END""",
        "foundation_claim_evidence_status": """CREATE TRIGGER foundation_claim_evidence_status BEFORE UPDATE OF status ON claims
WHEN NEW.status<>'current' AND EXISTS (
 SELECT 1 FROM relation_evidence_links l JOIN relation_temporal_semantics t USING(relation_id)
 WHERE l.claim_id=OLD.claim_id AND l.status='active')
BEGIN SELECT RAISE(ABORT,'RETIRE_GOVERNED_EVIDENCE_BEFORE_CLAIM_STATUS_CHANGE'); END""",
        "foundation_baseline_artifact_status": """CREATE TRIGGER foundation_baseline_artifact_status BEFORE INSERT ON current_views
WHEN NEW.status='baseline'
BEGIN
 SELECT CASE WHEN json_valid(NEW.content_json)=0
 OR json_extract(NEW.content_json,'$.artifact_status') IS NOT 'handoff_baseline_not_production_current_view'
 OR NEW.version IS NOT 'baseline_'||NEW.view_id
 OR substr(NEW.view_id,1,9)<>'BASELINE_'
 THEN RAISE(ABORT,'BASELINE_NAMESPACE_AND_ARTIFACT_STATUS_REQUIRED') END;
END""",
    }
    for event in ("INSERT", "UPDATE"):
        name = "foundation_active_evidence_" + event.lower()
        guards[name] = f"""CREATE TRIGGER {name} BEFORE {event} ON relation_evidence_links
WHEN NEW.status='active' AND (NEW.provenance_mode='RELATION_NATIVE'
 OR EXISTS (SELECT 1 FROM node_relations WHERE relation_id=NEW.relation_id AND status='categorical')
 OR EXISTS (SELECT 1 FROM relation_temporal_semantics WHERE relation_id=NEW.relation_id))
BEGIN
 SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM relation_evidence_authorizations a LEFT JOIN claims c ON c.claim_id=a.claim_id
 WHERE a.relation_id=NEW.relation_id AND a.evidence_role=NEW.evidence_role AND a.provenance_mode=NEW.provenance_mode
 AND a.authorization_state='AUTHORIZED' AND (
 (NEW.provenance_mode='CLAIM_LINKED' AND a.claim_id=NEW.claim_id AND a.claim_decision='KEEP' AND c.status='current')
 OR (NEW.provenance_mode='RELATION_NATIVE' AND a.link_candidate_id=NEW.authorization_id AND a.claim_id IS NULL
 AND a.evidence_id=NEW.evidence_id AND a.source_id=NEW.source_id AND a.source_sha256=NEW.source_sha256
 AND a.evidence_sha256=NEW.evidence_sha256)))
 THEN RAISE(ABORT,'UNAUTHORIZED_ACTIVE_RELATION_EVIDENCE') END;
END"""
    guards["foundation_native_link_update"] = """CREATE TRIGGER foundation_native_link_update BEFORE UPDATE ON relation_evidence_links
WHEN OLD.provenance_mode='RELATION_NATIVE' OR NEW.provenance_mode='RELATION_NATIVE'
BEGIN SELECT CASE WHEN NEW.relation_id IS NOT OLD.relation_id OR NEW.claim_id IS NOT OLD.claim_id
 OR NEW.provenance_mode IS NOT OLD.provenance_mode OR NEW.evidence_id IS NOT OLD.evidence_id
 OR NEW.source_id IS NOT OLD.source_id OR NEW.source_sha256 IS NOT OLD.source_sha256
 OR NEW.evidence_sha256 IS NOT OLD.evidence_sha256 OR NEW.authorization_id IS NOT OLD.authorization_id
 OR NEW.evidence_role IS NOT OLD.evidence_role OR NEW.created_at IS NOT OLD.created_at
 THEN RAISE(ABORT,'FROZEN_NATIVE_LINK_PROVENANCE') END; END"""
    guards["foundation_native_link_delete"] = """CREATE TRIGGER foundation_native_link_delete BEFORE DELETE ON relation_evidence_links
WHEN OLD.provenance_mode='RELATION_NATIVE'
BEGIN SELECT RAISE(ABORT,'FROZEN_NATIVE_LINK_PROVENANCE'); END"""
    guards["foundation_native_link_replace"] = """CREATE TRIGGER foundation_native_link_replace BEFORE INSERT ON relation_evidence_links
WHEN EXISTS (SELECT 1 FROM relation_evidence_links WHERE provenance_mode='RELATION_NATIVE'
 AND relation_id=NEW.relation_id AND evidence_id=NEW.evidence_id AND evidence_role=NEW.evidence_role)
BEGIN SELECT RAISE(ABORT,'FROZEN_NATIVE_LINK_PROVENANCE'); END"""
    guards["foundation_authorized_source_identity"] = """CREATE TRIGGER foundation_authorized_source_identity BEFORE UPDATE ON sources
WHEN (NEW.source_id IS NOT OLD.source_id OR NEW.sha256 IS NOT OLD.sha256)
 AND EXISTS (SELECT 1 FROM relation_evidence_authorizations WHERE source_id=OLD.source_id)
BEGIN SELECT RAISE(ABORT,'FROZEN_AUTHORIZED_SOURCE_IDENTITY'); END"""
    for event in ("INSERT", "UPDATE"):
        name = "foundation_baseline_namespace_" + event.lower()
        guards[name] = f"""CREATE TRIGGER {name} BEFORE {event} ON current_views
WHEN NEW.status<>'baseline' AND (substr(NEW.version,1,9)='baseline_' OR substr(NEW.view_id,1,9)='BASELINE_')
BEGIN SELECT RAISE(ABORT,'BASELINE_NAMESPACE_RESERVED'); END"""
    # Status can later retire through normal governance, but admitted native
    # content and the KEEP receipt must not be rewritten or replaced in place.
    frozen_claim_fields = ("claim_id", "statement", "nature", "fact_time", "publication_time", "ingestion_time",
                           "source_id", "evidence_pointer", "evidence_excerpt", "attributed_to", "scope",
                           "assumption_text", "confidence", "novelty_level", "structured_json", "created_at")
    changed = " OR ".join(f"NEW.{field} IS NOT OLD.{field}" for field in frozen_claim_fields)
    governed_claim = "json_extract(CASE WHEN json_valid(OLD.structured_json) THEN OLD.structured_json ELSE '{}' END,'$.foundation_admission.contract_sha256')"
    guards["foundation_claim_admission_immutable"] = f"""CREATE TRIGGER foundation_claim_admission_immutable BEFORE UPDATE ON claims
WHEN {governed_claim}='{CONTRACT_SHA256}' AND ({changed})
BEGIN SELECT RAISE(ABORT,'FROZEN_CLAIM_ADMISSION_PROVENANCE'); END"""
    guards["foundation_claim_admission_delete"] = f"""CREATE TRIGGER foundation_claim_admission_delete BEFORE DELETE ON claims
WHEN {governed_claim}='{CONTRACT_SHA256}'
BEGIN SELECT RAISE(ABORT,'FROZEN_CLAIM_ADMISSION_PROVENANCE'); END"""
    guards["foundation_claim_admission_replace"] = f"""CREATE TRIGGER foundation_claim_admission_replace BEFORE INSERT ON claims
WHEN EXISTS (SELECT 1 FROM claims c WHERE c.claim_id=NEW.claim_id
 AND json_extract(CASE WHEN json_valid(c.structured_json) THEN c.structured_json ELSE '{{}}' END,'$.foundation_admission.contract_sha256')='{CONTRACT_SHA256}')
BEGIN SELECT RAISE(ABORT,'FROZEN_CLAIM_ADMISSION_PROVENANCE'); END"""
    for table in ("relation_temporal_semantics", "relation_evidence_authorizations"):
        for event in ("UPDATE", "DELETE"):
            name = "foundation_immutable_" + table + "_" + event.lower()
            guards[name] = f"CREATE TRIGGER {name} BEFORE {event} ON {table} BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_PROVENANCE'); END"
        name = "foundation_no_replace_" + table
        key = "relation_id" if table == "relation_temporal_semantics" else "link_candidate_id"
        collision = f"{key}=NEW.{key}"
        if table == "relation_evidence_authorizations":
            collision += " OR (relation_id=NEW.relation_id AND claim_id IS NEW.claim_id AND evidence_role=NEW.evidence_role AND evidence_id=NEW.evidence_id AND packet_sha256=NEW.packet_sha256)"
        guards[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON {table}
WHEN EXISTS (SELECT 1 FROM {table} WHERE {collision})
BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_REPLACE'); END"""
    return guards


def migration_statements():
    # The legacy column explicitly encodes support in the existing 0.2.2 contract.
    # This is NOT a conversion from package Evidence-ID joins.
    statements = [LEGACY_EVIDENCE_TABLE, """INSERT OR IGNORE INTO relation_evidence_links
 (relation_id,claim_id,evidence_role,status,created_at)
 SELECT relation_id,evidence_claim_id,'supports','active',created_at FROM node_relations
 WHERE evidence_claim_id IS NOT NULL AND trim(evidence_claim_id)<>''""", TEMPORAL_TABLE, AUTHORIZATION_TABLE,
        "ALTER TABLE relation_evidence_links RENAME TO foundation_legacy_relation_evidence_links", EVIDENCE_TABLE,
        "INSERT INTO relation_evidence_links(relation_id,claim_id,evidence_role,status,created_at) SELECT relation_id,claim_id,evidence_role,status,created_at FROM foundation_legacy_relation_evidence_links",
        "DROP TABLE foundation_legacy_relation_evidence_links",
        *NATIVE_INDEXES.values(),
        "CREATE INDEX idx_relation_temporal_category ON relation_temporal_semantics(temporal_category,relation_id)",
        "CREATE INDEX idx_relation_evidence_authority ON relation_evidence_authorizations(relation_id,claim_id,evidence_role)",
        "CREATE INDEX idx_relation_evidence_claim ON relation_evidence_links(claim_id,status)"]
    for name, sql in BASELINE_GUARDS.items():
        statements += [f"DROP TRIGGER IF EXISTS {name}", sql]
    statements += list(governance_guards().values())
    statements += ["UPDATE meta SET value='0.2.3' WHERE key='schema_version'",
                   f"INSERT INTO meta(key,value) VALUES('foundation_execution_contract_sha256','{CONTRACT_SHA256}')"]
    return statements


def migration_sql():
    return "-- PREPARE ONLY. Future explicit Production authorization is mandatory.\nPRAGMA foreign_keys=ON;\nBEGIN IMMEDIATE;\n" + ";\n\n".join(migration_statements()) + ";\nCOMMIT;\n"


def require_execution_schema(connection):
    version = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    marker = connection.execute("SELECT value FROM meta WHERE key='foundation_execution_contract_sha256'").fetchone()
    if not version or version[0] != NEXT_SCHEMA_VERSION or not marker or marker[0] != CONTRACT_SHA256:
        raise PromotionError("FOUNDATION_EXECUTION_SCHEMA_REQUALIFICATION_REQUIRED")
    require_baseline_guards(connection)
    for name, sql in governance_guards().items():
        row = connection.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (name,)).fetchone()
        if row is None or row[0] != sql:
            raise PromotionError("FOUNDATION_SCHEMA_GUARD_DRIFT:" + name)
    for name, expected in (("relation_temporal_semantics", TEMPORAL_TABLE), ("relation_evidence_authorizations", AUTHORIZATION_TABLE), ("relation_evidence_links", EVIDENCE_TABLE)):
        row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        if row is None or row[0] != expected:
            raise PromotionError("FOUNDATION_SCHEMA_TABLE_DRIFT:" + name)
    for name, expected in (
        ("idx_relation_temporal_category", ["temporal_category", "relation_id"]),
        ("idx_relation_evidence_authority", ["relation_id", "claim_id", "evidence_role"]),
        ("idx_relation_evidence_claim", ["claim_id", "status"]),
        ("idx_native_evidence_identity", ["relation_id", "evidence_id", "evidence_role"]),
        ("idx_native_authorization_identity", ["relation_id", "evidence_id", "evidence_role", "packet_sha256"]),
    ):
        if [r[2] for r in connection.execute(f'PRAGMA index_info("{name}")')] != expected:
            raise PromotionError("FOUNDATION_SCHEMA_INDEX_DRIFT:" + name)
    for name, expected in NATIVE_INDEXES.items():
        row = connection.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
        if row is None or row[0] != expected:
            raise PromotionError("FOUNDATION_SCHEMA_INDEX_DRIFT:" + name)


def apply_synthetic_migration(path, *, configured_production_path, expected_sha256, inject_failure_after=None):
    """Test-only path. This function never authorizes a Production migration."""
    path = Path(path).resolve()
    assert_shadow_target(path, Path(configured_production_path))
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise PromotionError("MIGRATION_BASELINE_SHA_MISMATCH")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        version = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        if version == NEXT_SCHEMA_VERSION:
            require_execution_schema(connection)
            return {"status": "ALREADY_PREPARED", "sha256": sha256_file(path)}
        if version not in {"0.2.1", "0.2.2"}:
            raise PromotionError("MIGRATION_SOURCE_VERSION_UNSUPPORTED")
        before = database_rows(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            for i, statement in enumerate(migration_statements(), 1):
                connection.execute(statement)
                if i == inject_failure_after:
                    raise PromotionError("INJECTED_SCHEMA_MIGRATION_FAILURE")
            require_execution_schema(connection)
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or connection.execute("PRAGMA foreign_key_check").fetchall():
                raise PromotionError("MIGRATION_DATABASE_CHECK_FAILED")
            after = database_rows(connection)
            preserved_links = [json.loads(row) for row in after["relation_evidence_links"]]
            for encoded_old in before.get("relation_evidence_links", []):
                old = json.loads(encoded_old)
                if not any(all(row[k] == v for k, v in old.items()) for row in preserved_links):
                    raise PromotionError("MIGRATION_EXISTING_EVIDENCE_ROW_CHANGED")
            for table in before:
                if table not in {"meta", "relation_evidence_links"} and before[table] != after[table]:
                    raise PromotionError("MIGRATION_EXISTING_ROWS_CHANGED:" + table)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {"status": "PREPARED_SYNTHETIC_ONLY", "schema_version": NEXT_SCHEMA_VERSION,
                "schema_sha256": schema_sha256(connection), "sha256": sha256_file(path), "existing_rows_preserved": True}
    finally:
        connection.close()


def restore_synthetic_backup(path, backup, *, configured_production_path, expected_backup_sha256):
    """Offline backup restore, not a lossy down-migration after new data exists."""
    assert_shadow_target(Path(path), Path(configured_production_path))
    assert_shadow_target(Path(backup), Path(configured_production_path))
    if sha256_file(Path(backup)) != expected_backup_sha256:
        raise PromotionError("MIGRATION_BACKUP_SHA_MISMATCH")
    shutil.copyfile(backup, path)
    if sha256_file(Path(path)) != expected_backup_sha256:
        raise PromotionError("MIGRATION_RESTORE_SHA_MISMATCH")
