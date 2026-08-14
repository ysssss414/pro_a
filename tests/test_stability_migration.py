from __future__ import annotations

import sqlite3
from pathlib import Path

from pro_a.db import Database


def test_v0_1_database_is_migrated_in_place(tmp_path: Path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT INTO meta VALUES('schema_version','0.1');
        CREATE TABLE nodes(
          node_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,primary_type TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        );
        INSERT INTO nodes VALUES('NODE_1','Legacy','Theme','','active','2026-08-13T10:00:00','2026-08-13T10:00:00');
        CREATE TABLE sources(
          source_id TEXT PRIMARY KEY,title TEXT NOT NULL,original_name TEXT NOT NULL,archived_path TEXT NOT NULL,
          sha256 TEXT NOT NULL UNIQUE,ingestion_mode TEXT NOT NULL,source_type TEXT NOT NULL DEFAULT 'unknown',
          source_rank TEXT NOT NULL DEFAULT 'UNRANKED',origin_type TEXT NOT NULL DEFAULT 'unknown',author TEXT NOT NULL DEFAULT '',
          organization TEXT NOT NULL DEFAULT '',publication_time TEXT NOT NULL DEFAULT '',ingested_at TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'stored',ima_media_id TEXT NOT NULL DEFAULT '',ima_kb_id TEXT NOT NULL DEFAULT '',
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        INSERT INTO sources VALUES(
          'SRC_1','Legacy','legacy.txt','legacy.txt','sha','standard','txt','A','primary','','','',
          '2026-08-13T10:00:00','analyzed','','','{}'
        );
        CREATE TABLE current_views(
          view_id TEXT PRIMARY KEY,node_id TEXT NOT NULL REFERENCES nodes(node_id),version TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'official',change_level TEXT NOT NULL,previous_view_id TEXT,content_md TEXT NOT NULL,
          content_json TEXT NOT NULL DEFAULT '{}',trigger_source_id TEXT,trigger_claim_ids_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL,confirmed_at TEXT NOT NULL DEFAULT '',UNIQUE(node_id,version)
        );
        INSERT INTO current_views VALUES(
          'VIEW_1','NODE_1','v_20260813_02','official','minor',NULL,'legacy','{}','SRC_1','[]',
          '2026-08-13T10:00:00','2026-08-13T10:00:00'
        );
        CREATE TABLE proposals(
          proposal_id TEXT PRIMARY KEY,proposal_type TEXT NOT NULL,target_node_id TEXT,payload_json TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',reason TEXT NOT NULL DEFAULT '',propagation_batch_id TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,resolved_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE impact_reviews(
          impact_id TEXT PRIMARY KEY,batch_id TEXT NOT NULL,trigger_type TEXT NOT NULL,trigger_id TEXT NOT NULL,
          node_id TEXT NOT NULL REFERENCES nodes(node_id),path_type TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
          result_change_level TEXT NOT NULL DEFAULT '',proposal_id TEXT NOT NULL DEFAULT '',reason TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,evaluated_at TEXT NOT NULL DEFAULT '',UNIQUE(batch_id,node_id)
        );
        INSERT INTO impact_reviews VALUES(
          'IMP_1','BATCH_1','source','SRC_1','NODE_1','direct','no_change','','','{}','2026-08-13T10:00:00',''
        );
        """
    )
    conn.commit()
    conn.close()

    db = Database(path)
    db.init_schema()

    assert db.one("SELECT value FROM meta WHERE key='schema_version'")["value"] == "0.2.1"
    source = db.one("SELECT ingestion_mode,analysis_mode,underlying_source_id FROM sources WHERE source_id='SRC_1'")
    assert source == {"ingestion_mode": "standard", "analysis_mode": "standard", "underlying_source_id": ""}
    view = db.one("SELECT revision_date,revision_seq FROM current_views WHERE view_id='VIEW_1'")
    assert view == {"revision_date": "20260813", "revision_seq": 2}
    impact = db.one("SELECT target_view_version,attempts,last_error FROM impact_reviews WHERE impact_id='IMP_1'")
    assert impact == {"target_view_version": "<none>", "attempts": 0, "last_error": ""}
    assert db.one("SELECT name FROM sqlite_master WHERE type='table' AND name='side_effect_jobs'")
    assert "attributed_to" in {row["name"] for row in db.all("PRAGMA table_info(claims)")}
    assert {
        "link_origin", "derived_from_node_id", "evidence_excerpt", "evidence_validation_json",
    } <= {row["name"] for row in db.all("PRAGMA table_info(source_node_links)")}

    db.execute("UPDATE sources SET ingestion_mode='deep',analysis_mode='standard' WHERE source_id='SRC_1'")
    db.init_schema()
    assert db.one("SELECT ingestion_mode,analysis_mode FROM sources WHERE source_id='SRC_1'") == {
        "ingestion_mode": "deep", "analysis_mode": "standard"
    }
