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
               source_id,node_id,role,confidence,link_origin,evidence_excerpt
               ) VALUES(?,?,?,?,?,?)""",
            (
                "SRC_1",
                "NODE_CHILD",
                "primary",
                0.95,
                "existing_node_match",
                "EML",
            ),
        )
        conn.execute(
            """INSERT INTO current_views(
               view_id,node_id,version,status,change_level,content_md,created_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                "VIEW_1",
                "NODE_CHILD",
                "v_20260215",
                "official",
                "minor",
                "Current view",
                "2026-02-15T00:00:00+00:00",
            ),
        )
        conn.executemany(
            """INSERT INTO knowledge_gaps(
               gap_id,node_id,title,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?)""",
            [
                (
                    "GAP_OPEN",
                    "NODE_CHILD",
                    "Open gap",
                    "open",
                    "2026-02-15T00:00:00+00:00",
                    "2026-02-15T00:00:00+00:00",
                ),
                (
                    "GAP_DONE",
                    "NODE_CHILD",
                    "Resolved gap",
                    "resolved",
                    "2026-02-15T00:00:00+00:00",
                    "2026-02-15T00:00:00+00:00",
                ),
            ],
        )
        conn.execute(
            """INSERT INTO research_questions(
               rq_id,node_id,question,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?)""",
            (
                "RQ_1",
                "NODE_RQ",
                "Will optical interconnect adoption accelerate?",
                "open",
                "2026-02-15T00:00:00+00:00",
                "2026-02-15T00:00:00+00:00",
            ),
        )
    return path
