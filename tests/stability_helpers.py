from __future__ import annotations

from pathlib import Path

from pro_a.config import load_config
from pro_a.db import Database, now_iso
from pro_a.storage import ensure_workspace


def make_config(tmp_path: Path, *, ima_enabled: bool = False):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        f'''[workspace]\nroot = "{(tmp_path / 'workspace').as_posix()}"\nsettle_seconds = 0\n\n'''
        '''[llm]\nenabled = false\n\n'''
        f'''[ima]\nenabled = {str(ima_enabled).lower()}\noutput_kb_id = "output-kb"\n\n'''
        '''[pipeline]\narchive_originals = true\nwrite_receipts = true\ncreate_gaps_automatically = true\nrequire_confirmation_for_new_node = true\nrequire_confirmation_for_any_current_view_change = true\n''',
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    ensure_workspace(cfg.root)
    db = Database(cfg.db_path)
    db.init_schema()
    return cfg, db


def current_view_payload(db: Database, node_id: str, conclusion: str, *, change_level: str = "minor"):
    previous = db.current_view(node_id)
    return {
        "node_id": node_id,
        "change_level": change_level,
        "reason": conclusion,
        "proposed_current_view": {
            "one_line_conclusion": conclusion,
            "core_logic": [],
            "key_facts": [],
            "core_disagreements": [],
            "assumptions_to_verify": [],
            "investment_implication": "",
            "major_risks": [],
            "knowledge_gaps": [],
            "key_watch_items": [],
            "recent_change": conclusion,
            "evidence_claim_ids": [],
            "type_specific": {},
        },
        "evidence_claim_ids": [],
        "trigger_source_id": "",
        "previous_view_id": previous["view_id"] if previous else "",
        "previous_version": previous["version"] if previous else "",
    }


def add_source_and_claim(
    db: Database,
    *,
    source_id: str,
    claim_id: str,
    node_id: str,
    source_rank: str,
    origin_type: str,
    confidence: float,
    underlying_source_id: str = "",
):
    ts = now_iso()
    db.execute(
        """INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,source_rank,
           origin_type,ingested_at,status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (source_id, source_id, f"{source_id}.txt", f"/{source_id}.txt", source_id, "standard", source_rank,
         origin_type, ts, "analyzed", "{}"),
    )
    # v0.1.1 adds this column; keeping the helper compatible with the old schema makes the red test run meaningful.
    columns = {row["name"] for row in db.all("PRAGMA table_info(sources)")}
    if "underlying_source_id" in columns:
        db.execute("UPDATE sources SET underlying_source_id=? WHERE source_id=?", (underlying_source_id, source_id))
    db.execute(
        """INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,status,confidence,created_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (claim_id, f"claim {claim_id}", "fact", ts, source_id, "current", confidence, ts),
    )
    db.execute(
        "INSERT INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
        (claim_id, node_id, "related"),
    )
