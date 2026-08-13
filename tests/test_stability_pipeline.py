from __future__ import annotations

from pathlib import Path

import pytest

from pro_a.cli import main
from pro_a.pipeline import IngestionPipeline

from stability_helpers import make_config


def test_archive_source_upgrades_to_standard_and_deep_without_new_source(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    pipeline = IngestionPipeline(cfg, db)
    body = "same immutable source"

    archive_request = cfg.root / "inbox" / "archive" / "source.txt"
    archive_request.write_text(body, encoding="utf-8")
    archived = pipeline.process_all()
    source_id = archived[0]["source_id"]

    standard_request = cfg.root / "inbox" / "standard" / "source.txt"
    standard_request.write_text(body, encoding="utf-8")
    standard = pipeline.process_all()

    assert standard[0]["status"] == "needs_llm"
    assert standard[0]["source_id"] == source_id
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 1
    assert db.one("SELECT ingestion_mode,analysis_mode,status FROM sources WHERE source_id=?", (source_id,)) == {
        "ingestion_mode": "standard", "analysis_mode": "archive", "status": "needs_llm"
    }

    deep_request = cfg.root / "inbox" / "deep" / "source.txt"
    deep_request.write_text(body, encoding="utf-8")
    deep = pipeline.process_all()

    assert deep[0]["status"] == "needs_llm"
    assert deep[0]["source_id"] == source_id
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 1
    assert db.one("SELECT ingestion_mode,analysis_mode,status FROM sources WHERE source_id=?", (source_id,)) == {
        "ingestion_mode": "deep", "analysis_mode": "archive", "status": "needs_llm"
    }


def test_parse_failure_keeps_request_and_does_not_create_source(tmp_path: Path):
    cfg, db = make_config(tmp_path)
    pipeline = IngestionPipeline(cfg, db)
    request = cfg.root / "inbox" / "standard" / "broken.xlsx"
    request.write_bytes(b"not an xlsx zip")

    results = pipeline.process_all()

    assert results[0]["status"] == "failed"
    assert request.exists()
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 0
    job = db.one("SELECT status,source_id,error_text FROM processing_jobs")
    assert job["status"] == "failed"
    assert not job["source_id"]
    assert job["error_text"]


def test_ingest_cli_returns_nonzero_when_any_item_fails(tmp_path: Path):
    cfg, _ = make_config(tmp_path)
    request = cfg.root / "inbox" / "standard" / "broken.xlsx"
    request.write_bytes(b"not an xlsx zip")

    with pytest.raises(SystemExit) as exc:
        main(["--config", str(cfg.config_path), "ingest", "--once"])

    assert exc.value.code == 1
    assert request.exists()
