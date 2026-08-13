from pathlib import Path

from pro_a.config import load_config
from pro_a.db import Database
from pro_a.pipeline import IngestionPipeline


def test_archive_mode_without_llm_or_ima(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        f'''[workspace]\nroot = "{(tmp_path / 'workspace').as_posix()}"\nsettle_seconds = 0\n\n'''
        '''[llm]\nenabled = false\n\n[ima]\nenabled = false\n\n[pipeline]\narchive_originals = true\nwrite_receipts = true\ncreate_gaps_automatically = true\nrequire_confirmation_for_new_node = true\nrequire_confirmation_for_any_current_view_change = true\n''',
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    db = Database(cfg.db_path)
    pipeline = IngestionPipeline(cfg, db)
    pipeline.init_workspace()
    p = cfg.root / "inbox" / "archive" / "hello.txt"
    p.write_text("hello", encoding="utf-8")
    results = pipeline.process_all()
    assert results[0]["status"] == "archived"
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 1
    archived = Path(db.one("SELECT archived_path FROM sources")["archived_path"])
    assert archived.exists()
    # Exact duplicate should not create a second Source.
    p.write_text("hello", encoding="utf-8")
    results = pipeline.process_all()
    assert results[0]["status"] == "duplicate"
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 1
