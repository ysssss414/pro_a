PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    node_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    primary_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_name_type ON nodes(canonical_name, primary_type);

CREATE TABLE IF NOT EXISTS node_aliases (
    alias TEXT PRIMARY KEY COLLATE NOCASE,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS node_relations (
    relation_id TEXT PRIMARY KEY,
    from_node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    to_node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    scope TEXT NOT NULL DEFAULT '',
    valid_from TEXT NOT NULL DEFAULT '',
    valid_to TEXT NOT NULL DEFAULT '',
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'current',
    evidence_claim_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(from_node_id, relation_type, to_node_id, scope)
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_name TEXT NOT NULL,
    archived_path TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    ingestion_mode TEXT NOT NULL,
    analysis_mode TEXT NOT NULL DEFAULT 'archive',
    source_type TEXT NOT NULL DEFAULT 'unknown',
    source_rank TEXT NOT NULL DEFAULT 'UNRANKED',
    origin_type TEXT NOT NULL DEFAULT 'unknown',
    author TEXT NOT NULL DEFAULT '',
    organization TEXT NOT NULL DEFAULT '',
    publication_time TEXT NOT NULL DEFAULT '',
    ingested_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'stored',
    ima_media_id TEXT NOT NULL DEFAULT '',
    ima_kb_id TEXT NOT NULL DEFAULT '',
    underlying_source_id TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS source_relations (
    relation_id TEXT PRIMARY KEY,
    from_source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    to_source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(from_source_id, relation_type, to_source_id)
);

CREATE TABLE IF NOT EXISTS source_node_links (
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'related',
    confidence REAL,
    link_origin TEXT NOT NULL DEFAULT 'legacy',
    derived_from_node_id TEXT NOT NULL DEFAULT '',
    evidence_excerpt TEXT NOT NULL DEFAULT '',
    evidence_validation_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY(source_id, node_id)
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    nature TEXT NOT NULL,
    fact_time TEXT NOT NULL DEFAULT '',
    publication_time TEXT NOT NULL DEFAULT '',
    ingestion_time TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    evidence_pointer TEXT NOT NULL DEFAULT '',
    evidence_excerpt TEXT NOT NULL DEFAULT '',
    attributed_to TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT '',
    assumption_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'current',
    confidence REAL,
    novelty_level TEXT NOT NULL DEFAULT 'N2',
    structured_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_id);

CREATE TABLE IF NOT EXISTS claim_node_links (
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'related',
    PRIMARY KEY(claim_id, node_id)
);

CREATE TABLE IF NOT EXISTS claim_relations (
    relation_id TEXT PRIMARY KEY,
    from_claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    to_claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(from_claim_id, relation_type, to_claim_id)
);

CREATE TABLE IF NOT EXISTS current_views (
    view_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'official',
    change_level TEXT NOT NULL,
    previous_view_id TEXT,
    content_md TEXT NOT NULL,
    content_json TEXT NOT NULL DEFAULT '{}',
    trigger_source_id TEXT,
    trigger_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    revision_date TEXT NOT NULL DEFAULT '',
    revision_seq INTEGER NOT NULL DEFAULT 0,
    accepted_proposal_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    confirmed_at TEXT NOT NULL DEFAULT '',
    UNIQUE(node_id, version)
);
CREATE INDEX IF NOT EXISTS idx_current_views_node ON current_views(node_id, created_at DESC);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    proposal_type TEXT NOT NULL,
    target_node_id TEXT,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT NOT NULL DEFAULT '',
    propagation_batch_id TEXT NOT NULL DEFAULT '',
    source_impact_id TEXT NOT NULL DEFAULT '',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    resolved_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status, created_at);

CREATE TABLE IF NOT EXISTS knowledge_gaps (
    gap_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    source_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    freshness_due TEXT NOT NULL DEFAULT '',
    resolution_claim_id TEXT NOT NULL DEFAULT '',
    superseded_by_gap_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_questions (
    rq_id TEXT PRIMARY KEY,
    node_id TEXT UNIQUE NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    importance TEXT NOT NULL DEFAULT '',
    current_answer TEXT NOT NULL DEFAULT '',
    confidence REAL,
    supporting_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    opposing_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    key_variables_json TEXT NOT NULL DEFAULT '[]',
    what_would_change_my_mind TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS impact_reviews (
    impact_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_id TEXT NOT NULL,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    path_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result_change_level TEXT NOT NULL DEFAULT '',
    proposal_id TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    target_view_version TEXT NOT NULL DEFAULT '<none>',
    payload_json TEXT NOT NULL DEFAULT '{}',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    queue_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    evaluated_at TEXT NOT NULL DEFAULT '',
    UNIQUE(batch_id, node_id, target_view_version)
);

CREATE TABLE IF NOT EXISTS side_effect_jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(job_type, object_id)
);
CREATE INDEX IF NOT EXISTS idx_side_effect_jobs_status ON side_effect_jobs(status, created_at);

CREATE TABLE IF NOT EXISTS ima_objects (
    mapping_id TEXT PRIMARY KEY,
    local_object_type TEXT NOT NULL,
    local_object_id TEXT NOT NULL,
    ima_kb_id TEXT NOT NULL DEFAULT '',
    ima_folder_id TEXT NOT NULL DEFAULT '',
    ima_media_id TEXT NOT NULL DEFAULT '',
    ima_note_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    synced_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'synced',
    UNIQUE(local_object_type, local_object_id, ima_kb_id)
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id TEXT PRIMARY KEY,
    source_id TEXT,
    input_path TEXT NOT NULL,
    ingestion_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    error_text TEXT NOT NULL DEFAULT ''
);
