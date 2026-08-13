from pathlib import Path

from pro_a.analyzer import Analyzer
from pro_a.config import load_config
from pro_a.db import Database
from pro_a.proposals import ProposalManager
from pro_a.storage import ensure_workspace


def test_accept_current_view_creates_dated_version(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        f'''[workspace]\nroot = "{(tmp_path / 'workspace').as_posix()}"\nsettle_seconds = 0\n\n'''
        '''[llm]\nenabled = false\n\n[ima]\nenabled = false\n\n[pipeline]\narchive_originals = true\nwrite_receipts = true\ncreate_gaps_automatically = true\nrequire_confirmation_for_new_node = true\nrequire_confirmation_for_any_current_view_change = true\n''',
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    ensure_workspace(cfg.root)
    db = Database(cfg.db_path)
    db.init_schema()
    node_id = db.add_node("EML", "Technology")
    payload = {
        "node_id": node_id,
        "change_level": "initial",
        "reason": "initial",
        "proposed_current_view": {
            "one_line_conclusion": "测试结论",
            "core_logic": [],
            "key_facts": [],
            "core_disagreements": [],
            "assumptions_to_verify": [],
            "investment_implication": "",
            "major_risks": [],
            "knowledge_gaps": [],
            "key_watch_items": [],
            "recent_change": "首次建立",
            "evidence_claim_ids": [],
            "type_specific": {},
        },
        "evidence_claim_ids": [],
        "trigger_source_id": "",
        "previous_version": "",
    }
    pid = db.add_proposal("current_view_change", payload, target_node_id=node_id)
    manager = ProposalManager(cfg, db, Analyzer(cfg, db))
    result = manager.accept(pid)
    assert result["version"].startswith("v_")
    assert Path(result["path"]).exists()
    assert db.current_view(node_id)["version"] == result["version"]
