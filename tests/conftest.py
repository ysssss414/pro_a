from pathlib import Path

import pytest

from pro_a.db import Database


@pytest.fixture
def read_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "knowledge.db"
    db = Database(path)
    db.init_schema()
    with db.connect() as conn:
        conn.executemany(
            """INSERT INTO nodes(
               node_id,canonical_name,primary_type,description,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?)""",
            [
                (
                    "NODE_CHILD",
                    "Electro-Absorption Modulated Laser",
                    "Product",
                    "An optical transmitter component.",
                    "active",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
                (
                    "NODE_PARENT",
                    "Optical Components",
                    "Segment",
                    "Optical component universe.",
                    "active",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
                (
                    "NODE_OTHER",
                    "AI Server",
                    "Equipment",
                    "AI compute equipment.",
                    "active",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
                (
                    "NODE_RQ",
                    "Will optical interconnect adoption accelerate?",
                    "ResearchQuestion",
                    "A tracked research question.",
                    "active",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO node_aliases(alias,node_id) VALUES(?,?)",
            [("EML", "NODE_CHILD"), ("Photonics", "NODE_PARENT")],
        )
        conn.executemany(
            """INSERT INTO node_relations(
               relation_id,from_node_id,relation_type,to_node_id,scope,confidence,status,created_at
               ) VALUES(?,?,?,?,?,?,?,?)""",
            [
                (
                    "REL_PART",
                    "NODE_CHILD",
                    "part_of",
                    "NODE_PARENT",
                    "",
                    1.0,
                    "current",
                    "2026-01-01T00:00:00+00:00",
                ),
                (
                    "REL_USES",
                    "NODE_OTHER",
                    "uses",
                    "NODE_CHILD",
                    "training",
                    0.8,
                    "current",
                    "2026-01-02T00:00:00+00:00",
                ),
            ],
        )
        conn.executemany(
            """INSERT INTO sources(
               source_id,title,original_name,archived_path,sha256,ingestion_mode,
               source_type,source_rank,author,organization,publication_time,ingested_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "SRC_1",
                    "Optical Components Report",
                    "optical-report.pdf",
                    "archive/src1.pdf",
                    "a" * 64,
                    "standard",
                    "company_filing",
                    "A",
                    "Analyst One",
                    "Research Org",
                    "2026-01-15",
                    "2026-01-16T00:00:00+00:00",
                ),
                (
                    "SRC_2",
                    "AI Infrastructure Update",
                    "ai-update.md",
                    "archive/src2.md",
                    "b" * 64,
                    "deep",
                    "research_report",
                    "B",
                    "Analyst Two",
                    "Second Org",
                    "2026-02-15",
                    "2026-02-16T00:00:00+00:00",
                ),
            ],
        )
        conn.executemany(
            """INSERT INTO claims(
               claim_id,statement,nature,fact_time,publication_time,ingestion_time,
               source_id,evidence_pointer,evidence_excerpt,attributed_to,scope,
               status,confidence,novelty_level,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "CLAIM_1",
                    "EML is used in high-speed optical transmitters.",
                    "fact",
                    "2026-01-10",
                    "2026-01-15",
                    "2026-01-16T00:00:00+00:00",
                    "SRC_1",
                    "p.3",
                    "EML is used in high-speed optical transmitters.",
                    "Research Org",
                    "optical transmitters",
                    "current",
                    0.9,
                    "N1",
                    "2026-01-16T00:00:00+00:00",
                ),
                (
                    "CLAIM_2",
                    "AI infrastructure demand for optical links is growing.",
                    "broker_forecast",
                    "2026-02-10",
                    "2026-02-15",
                    "2026-02-16T00:00:00+00:00",
                    "SRC_2",
                    "section 2",
                    "Demand for optical links is growing.",
                    "Second Org",
                    "AI infrastructure",
                    "current",
                    0.7,
                    "N2",
                    "2026-02-16T00:00:00+00:00",
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
            [
                ("CLAIM_1", "NODE_CHILD", "subject"),
                ("CLAIM_2", "NODE_CHILD", "related"),
            ],
        )
        conn.execute(
            """INSERT INTO relation_evidence_links(
               relation_id,claim_id,evidence_role,status,created_at
               ) VALUES(?,?,?,?,?)""",
            (
                "REL_USES",
                "CLAIM_1",
                "supports",
                "active",
                "2026-01-16T00:00:00+00:00",
            ),
        )
        conn.execute(
            """INSERT INTO source_node_links(
               source_id,node_id,role,confidence,link_origin,derived_from_node_id,
               evidence_excerpt) VALUES(?,?,?,?,?,?,?)""",
            (
                "SRC_1",
                "NODE_CHILD",
                "primary",
                0.95,
                "existing_node_match",
                "NODE_PARENT",
                "EML",
            ),
        )
        conn.execute(
            """UPDATE sources SET analysis_mode='standard',origin_type='local_file',
                      status='analyzed',underlying_source_id='SRC_BASE'
               WHERE source_id='SRC_1'"""
        )
        conn.executemany(
            """INSERT INTO current_views(
               view_id,node_id,version,status,change_level,previous_view_id,
               content_md,content_json,trigger_source_id,trigger_claim_ids_json,
               revision_date,revision_seq,accepted_proposal_id,created_at,confirmed_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "VIEW_OLD", "NODE_CHILD", "v_20260215", "official", "minor", None,
                    "Older view", '{"thesis":"older"}', None, "[]", "20260215", 0,
                    "PROPOSAL_OLD", "2026-04-01T00:00:00+00:00", "2026-04-01T00:00:00+00:00",
                ),
                (
                    "VIEW_CURRENT", "NODE_CHILD", "v_20260301_01", "official", "material",
                    "VIEW_OLD", "# Current view\n\nOptical demand is accelerating.",
                    '{"thesis":"accelerating","risks":["pricing"]}', "SRC_1",
                    '["CLAIM_1","CLAIM_MISSING"]', "20260301", 1,
                    "PROPOSAL_CURRENT", "2026-03-01T00:00:00+00:00",
                    "2026-03-02T00:00:00+00:00",
                ),
                (
                    "VIEW_DRAFT", "NODE_CHILD", "v_20990101", "draft", "major", "VIEW_CURRENT",
                    "Draft view", "{}", None, "[]", "20990101", 0, "",
                    "2099-01-01T00:00:00+00:00", "",
                ),
            ],
        )
        conn.executemany(
            """INSERT INTO knowledge_gaps(
               gap_id,node_id,title,description,status,source_claim_ids_json,
               freshness_due,resolution_claim_id,superseded_by_gap_id,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "GAP_REFRESH", "NODE_CHILD", "Refresh pricing evidence",
                    "Validate whether pricing pressure has changed.", "needs_refresh",
                    '["CLAIM_2"]', "2026-04-01", "", "",
                    "2026-03-10T00:00:00+00:00", "2026-03-10T00:00:00+00:00",
                ),
                (
                    "GAP_OPEN", "NODE_CHILD", "Track adoption",
                    "Measure hyperscaler deployment timing.", "open",
                    '["CLAIM_1","CLAIM_MISSING"]', "2026-05-01", "", "",
                    "2026-03-11T00:00:00+00:00", "2026-03-11T00:00:00+00:00",
                ),
                (
                    "GAP_DONE", "NODE_CHILD", "Resolved gap",
                    "Historical packaging question.", "resolved", '["CLAIM_1"]',
                    "2026-01-01", "CLAIM_1", "GAP_REFRESH",
                    "2026-02-15T00:00:00+00:00", "2026-03-12T00:00:00+00:00",
                ),
            ],
        )
        conn.execute(
            """INSERT INTO research_questions(
               rq_id,node_id,question,importance,current_answer,confidence,
               supporting_claim_ids_json,opposing_claim_ids_json,key_variables_json,
               what_would_change_my_mind,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "RQ_1",
                "NODE_CHILD",
                "Will optical interconnect adoption accelerate?",
                "Material to the demand outlook.",
                "Adoption is accelerating, with timing uncertainty.",
                0.72,
                '["CLAIM_1","CLAIM_MISSING"]',
                '["CLAIM_2"]',
                '["hyperscaler capex", {"variable":"pricing","direction":"down"}]',
                "A sustained deployment delay or falling attach rate.",
                "open",
                "2026-02-15T00:00:00+00:00",
                "2026-03-15T00:00:00+00:00",
            ),
        )
    return path
