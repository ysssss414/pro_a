-- PREPARE ONLY. Future explicit Production authorization is mandatory.
PRAGMA foreign_keys=ON;
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS relation_evidence_links (
 relation_id TEXT NOT NULL REFERENCES node_relations(relation_id) ON DELETE CASCADE,
 claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
 evidence_role TEXT NOT NULL CHECK(evidence_role IN ('supports','contradicts')),
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','retired')),
 created_at TEXT NOT NULL,
 PRIMARY KEY(relation_id,claim_id,evidence_role)
);

INSERT OR IGNORE INTO relation_evidence_links
 (relation_id,claim_id,evidence_role,status,created_at)
 SELECT relation_id,evidence_claim_id,'supports','active',created_at FROM node_relations
 WHERE evidence_claim_id IS NOT NULL AND trim(evidence_claim_id)<>'';

CREATE TABLE relation_temporal_semantics (
 relation_id TEXT PRIMARY KEY NOT NULL REFERENCES node_relations(relation_id) ON DELETE RESTRICT,
 temporal_category TEXT NOT NULL CHECK(length(trim(temporal_category))>0),
 valid_from_supplied INTEGER NOT NULL CHECK(valid_from_supplied IN (0,1)),
 valid_to_supplied INTEGER NOT NULL CHECK(valid_to_supplied IN (0,1)),
 projection_sha256 TEXT NOT NULL CHECK(length(projection_sha256)=64),
 contract_sha256 TEXT NOT NULL CHECK(length(contract_sha256)=64),
 provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json))
);

CREATE TABLE relation_evidence_authorizations (
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
);

ALTER TABLE relation_evidence_links RENAME TO foundation_legacy_relation_evidence_links;

CREATE TABLE relation_evidence_links (
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
);

INSERT INTO relation_evidence_links(relation_id,claim_id,evidence_role,status,created_at) SELECT relation_id,claim_id,evidence_role,status,created_at FROM foundation_legacy_relation_evidence_links;

DROP TABLE foundation_legacy_relation_evidence_links;

CREATE UNIQUE INDEX idx_native_evidence_identity ON relation_evidence_links(relation_id,evidence_id,evidence_role) WHERE provenance_mode='RELATION_NATIVE';

CREATE UNIQUE INDEX idx_native_authorization_identity ON relation_evidence_authorizations(relation_id,evidence_id,evidence_role,packet_sha256) WHERE provenance_mode='RELATION_NATIVE';

CREATE INDEX idx_relation_temporal_category ON relation_temporal_semantics(temporal_category,relation_id);

CREATE INDEX idx_relation_evidence_authority ON relation_evidence_authorizations(relation_id,claim_id,evidence_role);

CREATE INDEX idx_relation_evidence_claim ON relation_evidence_links(claim_id,status);

DROP TRIGGER IF EXISTS foundation_baseline_replace;

CREATE TRIGGER foundation_baseline_replace
BEFORE INSERT ON current_views WHEN EXISTS (
 SELECT 1 FROM current_views WHERE status='baseline' AND (
 view_id=NEW.view_id OR (node_id=NEW.node_id AND version=NEW.version)))
BEGIN SELECT RAISE(ABORT,'FROZEN_BASELINE_REPLACE_FORBIDDEN'); END;

DROP TRIGGER IF EXISTS foundation_baseline_insert;

CREATE TRIGGER foundation_baseline_insert
BEFORE INSERT ON current_views WHEN NEW.status='baseline'
BEGIN
 SELECT CASE WHEN substr(NEW.version,1,9)<>'baseline_'
 OR EXISTS (SELECT 1 FROM current_views WHERE view_id=NEW.view_id
            OR (node_id=NEW.node_id AND version=NEW.version))
 OR COALESCE(NEW.previous_view_id,'')<>'' OR NEW.revision_seq<>0
 OR NEW.accepted_proposal_id<>'' OR NEW.change_level<>'baseline'
 THEN RAISE(ABORT,'INVALID_BASELINE_IDENTITY') END;
END;

DROP TRIGGER IF EXISTS foundation_baseline_update;

CREATE TRIGGER foundation_baseline_update
BEFORE UPDATE ON current_views WHEN OLD.status='baseline' OR NEW.status='baseline'
BEGIN SELECT RAISE(ABORT,'FROZEN_BASELINE_UPDATE_FORBIDDEN'); END;

DROP TRIGGER IF EXISTS foundation_baseline_delete;

CREATE TRIGGER foundation_baseline_delete
BEFORE DELETE ON current_views WHEN OLD.status='baseline'
BEGIN SELECT RAISE(ABORT,'FROZEN_BASELINE_DELETE_FORBIDDEN'); END;

DROP TRIGGER IF EXISTS foundation_official_predecessor;

CREATE TRIGGER foundation_official_predecessor
BEFORE INSERT ON current_views WHEN NEW.status='official'
BEGIN
 SELECT CASE WHEN substr(NEW.version,1,9)='baseline_' OR EXISTS (
 SELECT 1 FROM current_views WHERE view_id=NEW.previous_view_id AND status='baseline')
 THEN RAISE(ABORT,'BASELINE_IS_NOT_OFFICIAL_PREDECESSOR') END;
END;

DROP TRIGGER IF EXISTS foundation_official_predecessor_update;

CREATE TRIGGER foundation_official_predecessor_update
BEFORE UPDATE ON current_views WHEN NEW.status='official'
BEGIN
 SELECT CASE WHEN substr(NEW.version,1,9)='baseline_' OR EXISTS (
 SELECT 1 FROM current_views WHERE view_id=NEW.previous_view_id AND status='baseline')
 THEN RAISE(ABORT,'BASELINE_IS_NOT_OFFICIAL_PREDECESSOR') END;
END;

CREATE TRIGGER foundation_temporal_insert BEFORE INSERT ON relation_temporal_semantics
BEGIN
 SELECT CASE WHEN NEW.contract_sha256<>'9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634' OR NOT EXISTS (
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
END;

CREATE TRIGGER foundation_temporal_relation_update BEFORE UPDATE ON node_relations
WHEN EXISTS (SELECT 1 FROM relation_temporal_semantics WHERE relation_id=OLD.relation_id)
BEGIN
 SELECT CASE WHEN NEW.relation_id IS NOT OLD.relation_id OR NEW.from_node_id IS NOT OLD.from_node_id
 OR NEW.to_node_id IS NOT OLD.to_node_id OR NEW.relation_type IS NOT OLD.relation_type OR NEW.scope IS NOT OLD.scope
 OR NEW.valid_from IS NOT OLD.valid_from OR NEW.valid_to IS NOT OLD.valid_to OR NEW.status NOT IN ('categorical','retired')
 THEN RAISE(ABORT,'TEMPORAL_RELATION_REQUALIFICATION_REQUIRED') END;
END;

CREATE TRIGGER foundation_evidence_authorization_insert
BEFORE INSERT ON relation_evidence_authorizations
WHEN NEW.provenance_mode='CLAIM_LINKED'
BEGIN
 SELECT CASE WHEN NEW.contract_sha256<>'9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634' OR NOT EXISTS (
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
END;

CREATE TRIGGER foundation_native_authorization_insert BEFORE INSERT ON relation_evidence_authorizations
WHEN NEW.provenance_mode='RELATION_NATIVE'
BEGIN
 SELECT CASE WHEN NEW.contract_sha256<>'9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634' OR NOT EXISTS (
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
END;

CREATE TRIGGER foundation_claim_evidence_status BEFORE UPDATE OF status ON claims
WHEN NEW.status<>'current' AND EXISTS (
 SELECT 1 FROM relation_evidence_links l JOIN relation_temporal_semantics t USING(relation_id)
 WHERE l.claim_id=OLD.claim_id AND l.status='active')
BEGIN SELECT RAISE(ABORT,'RETIRE_GOVERNED_EVIDENCE_BEFORE_CLAIM_STATUS_CHANGE'); END;

CREATE TRIGGER foundation_baseline_artifact_status BEFORE INSERT ON current_views
WHEN NEW.status='baseline'
BEGIN
 SELECT CASE WHEN json_valid(NEW.content_json)=0
 OR json_extract(NEW.content_json,'$.artifact_status') IS NOT 'handoff_baseline_not_production_current_view'
 OR NEW.version IS NOT 'baseline_'||NEW.view_id
 OR substr(NEW.view_id,1,9)<>'BASELINE_'
 THEN RAISE(ABORT,'BASELINE_NAMESPACE_AND_ARTIFACT_STATUS_REQUIRED') END;
END;

CREATE TRIGGER foundation_active_evidence_insert BEFORE INSERT ON relation_evidence_links
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
END;

CREATE TRIGGER foundation_active_evidence_update BEFORE UPDATE ON relation_evidence_links
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
END;

CREATE TRIGGER foundation_native_link_update BEFORE UPDATE ON relation_evidence_links
WHEN OLD.provenance_mode='RELATION_NATIVE' OR NEW.provenance_mode='RELATION_NATIVE'
BEGIN SELECT CASE WHEN NEW.relation_id IS NOT OLD.relation_id OR NEW.claim_id IS NOT OLD.claim_id
 OR NEW.provenance_mode IS NOT OLD.provenance_mode OR NEW.evidence_id IS NOT OLD.evidence_id
 OR NEW.source_id IS NOT OLD.source_id OR NEW.source_sha256 IS NOT OLD.source_sha256
 OR NEW.evidence_sha256 IS NOT OLD.evidence_sha256 OR NEW.authorization_id IS NOT OLD.authorization_id
 OR NEW.evidence_role IS NOT OLD.evidence_role OR NEW.created_at IS NOT OLD.created_at
 THEN RAISE(ABORT,'FROZEN_NATIVE_LINK_PROVENANCE') END; END;

CREATE TRIGGER foundation_native_link_delete BEFORE DELETE ON relation_evidence_links
WHEN OLD.provenance_mode='RELATION_NATIVE'
BEGIN SELECT RAISE(ABORT,'FROZEN_NATIVE_LINK_PROVENANCE'); END;

CREATE TRIGGER foundation_native_link_replace BEFORE INSERT ON relation_evidence_links
WHEN EXISTS (SELECT 1 FROM relation_evidence_links WHERE provenance_mode='RELATION_NATIVE'
 AND relation_id=NEW.relation_id AND evidence_id=NEW.evidence_id AND evidence_role=NEW.evidence_role)
BEGIN SELECT RAISE(ABORT,'FROZEN_NATIVE_LINK_PROVENANCE'); END;

CREATE TRIGGER foundation_authorized_source_identity BEFORE UPDATE ON sources
WHEN (NEW.source_id IS NOT OLD.source_id OR NEW.sha256 IS NOT OLD.sha256)
 AND EXISTS (SELECT 1 FROM relation_evidence_authorizations WHERE source_id=OLD.source_id)
BEGIN SELECT RAISE(ABORT,'FROZEN_AUTHORIZED_SOURCE_IDENTITY'); END;

CREATE TRIGGER foundation_baseline_namespace_insert BEFORE INSERT ON current_views
WHEN NEW.status<>'baseline' AND (substr(NEW.version,1,9)='baseline_' OR substr(NEW.view_id,1,9)='BASELINE_')
BEGIN SELECT RAISE(ABORT,'BASELINE_NAMESPACE_RESERVED'); END;

CREATE TRIGGER foundation_baseline_namespace_update BEFORE UPDATE ON current_views
WHEN NEW.status<>'baseline' AND (substr(NEW.version,1,9)='baseline_' OR substr(NEW.view_id,1,9)='BASELINE_')
BEGIN SELECT RAISE(ABORT,'BASELINE_NAMESPACE_RESERVED'); END;

CREATE TRIGGER foundation_claim_admission_immutable BEFORE UPDATE ON claims
WHEN json_extract(CASE WHEN json_valid(OLD.structured_json) THEN OLD.structured_json ELSE '{}' END,'$.foundation_admission.contract_sha256')='9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634' AND (NEW.claim_id IS NOT OLD.claim_id OR NEW.statement IS NOT OLD.statement OR NEW.nature IS NOT OLD.nature OR NEW.fact_time IS NOT OLD.fact_time OR NEW.publication_time IS NOT OLD.publication_time OR NEW.ingestion_time IS NOT OLD.ingestion_time OR NEW.source_id IS NOT OLD.source_id OR NEW.evidence_pointer IS NOT OLD.evidence_pointer OR NEW.evidence_excerpt IS NOT OLD.evidence_excerpt OR NEW.attributed_to IS NOT OLD.attributed_to OR NEW.scope IS NOT OLD.scope OR NEW.assumption_text IS NOT OLD.assumption_text OR NEW.confidence IS NOT OLD.confidence OR NEW.novelty_level IS NOT OLD.novelty_level OR NEW.structured_json IS NOT OLD.structured_json OR NEW.created_at IS NOT OLD.created_at)
BEGIN SELECT RAISE(ABORT,'FROZEN_CLAIM_ADMISSION_PROVENANCE'); END;

CREATE TRIGGER foundation_claim_admission_delete BEFORE DELETE ON claims
WHEN json_extract(CASE WHEN json_valid(OLD.structured_json) THEN OLD.structured_json ELSE '{}' END,'$.foundation_admission.contract_sha256')='9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634'
BEGIN SELECT RAISE(ABORT,'FROZEN_CLAIM_ADMISSION_PROVENANCE'); END;

CREATE TRIGGER foundation_claim_admission_replace BEFORE INSERT ON claims
WHEN EXISTS (SELECT 1 FROM claims c WHERE c.claim_id=NEW.claim_id
 AND json_extract(CASE WHEN json_valid(c.structured_json) THEN c.structured_json ELSE '{}' END,'$.foundation_admission.contract_sha256')='9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634')
BEGIN SELECT RAISE(ABORT,'FROZEN_CLAIM_ADMISSION_PROVENANCE'); END;

CREATE TRIGGER foundation_immutable_relation_temporal_semantics_update BEFORE UPDATE ON relation_temporal_semantics BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_PROVENANCE'); END;

CREATE TRIGGER foundation_immutable_relation_temporal_semantics_delete BEFORE DELETE ON relation_temporal_semantics BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_PROVENANCE'); END;

CREATE TRIGGER foundation_no_replace_relation_temporal_semantics BEFORE INSERT ON relation_temporal_semantics
WHEN EXISTS (SELECT 1 FROM relation_temporal_semantics WHERE relation_id=NEW.relation_id)
BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_REPLACE'); END;

CREATE TRIGGER foundation_immutable_relation_evidence_authorizations_update BEFORE UPDATE ON relation_evidence_authorizations BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_PROVENANCE'); END;

CREATE TRIGGER foundation_immutable_relation_evidence_authorizations_delete BEFORE DELETE ON relation_evidence_authorizations BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_PROVENANCE'); END;

CREATE TRIGGER foundation_no_replace_relation_evidence_authorizations BEFORE INSERT ON relation_evidence_authorizations
WHEN EXISTS (SELECT 1 FROM relation_evidence_authorizations WHERE link_candidate_id=NEW.link_candidate_id OR (relation_id=NEW.relation_id AND claim_id IS NEW.claim_id AND evidence_role=NEW.evidence_role AND evidence_id=NEW.evidence_id AND packet_sha256=NEW.packet_sha256))
BEGIN SELECT RAISE(ABORT,'FROZEN_GOVERNANCE_REPLACE'); END;

UPDATE meta SET value='0.2.3' WHERE key='schema_version';

INSERT INTO meta(key,value) VALUES('foundation_execution_contract_sha256','9c46b3e1a211400c407fcd5c67956428a8aef7507f0a49ff47ab62e22804d634');
COMMIT;
