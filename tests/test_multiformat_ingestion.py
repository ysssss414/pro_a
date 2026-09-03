import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pro_a.api import create_app
from pro_a.ima import IMAClient
from pro_a.llm import LLMError
from pro_a.pipeline import IngestionPipeline
from pro_a.query import ReadOnlyQuery
from pro_a.storage import sha256_file

from multiformat_helpers import EXCERPT, write_pdf, write_source
from stability_helpers import make_config


class FixtureLLM:
    available = True

    def __init__(self):
        self.calls = []

    def json(self, system, user):
        self.calls.append(user)
        return {
            "source_metadata": {"title": "Fixture source", "summary": "Fixture summary"},
            "node_matches": [], "node_candidates": [], "source_references": [],
            "claims": [{
                "statement": statement, "nature": "data", "attributed_to": "Fixture report",
                "evidence_excerpt": excerpt, "evidence_pointer": "model supplied pointer",
                "confidence": 0.9, "structured": {},
            } for statement, excerpt in ((EXCERPT, EXCERPT), ("Unverified metric.", "Invented evidence."))],
        }


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Live network/IMA/LLM is forbidden during format acceptance")

    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    monkeypatch.setattr("pro_a.ima.IMAClient.upload_file", forbidden)
    monkeypatch.setattr("pro_a.llm.ChatLLM.json", forbidden)


def pipeline_fixture(tmp_path):
    cfg, db = make_config(tmp_path)
    pipeline = IngestionPipeline(cfg, db)
    pipeline.analyzer.llm = FixtureLLM()
    return cfg, db, pipeline


@pytest.mark.parametrize("fmt", ["pdf", "docx", "xlsx", "pptx"])
@pytest.mark.parametrize("mode", ["standard", "deep"])
def test_isolated_multiformat_pipeline(tmp_path, fmt, mode):
    cfg, db, pipeline = pipeline_fixture(tmp_path)
    request = cfg.root / "inbox" / mode / f"fixture.{fmt}"
    locator = write_source(request)
    original_sha = sha256_file(request)
    receipt = pipeline.process_file(request, mode)
    assert receipt["status"] == "analyzed", receipt
    assert not request.exists()
    source = db.one("SELECT * FROM sources")
    assert source["source_type"] == receipt["source_type"] == fmt
    assert source["analysis_mode"] == mode and source["status"] == "analyzed"
    metadata = json.loads(source["metadata_json"])
    assert metadata["parse_diagnostics"] == receipt["parse_diagnostics"]
    assert metadata["summary"] == "Fixture summary"
    assert "analysis_quality" in metadata and "source_references_unresolved" in metadata
    claims = db.all("SELECT * FROM claims")
    assert len(claims) == 2
    valid = next(c for c in claims if c["statement"] == EXCERPT)
    invalid = next(c for c in claims if c["statement"] != EXCERPT)
    validation = json.loads(valid["structured_json"])["validation"]
    assert valid["status"] == "current" and validation["evidence_validated"] is True
    assert validation["source_locator"] == {"status": "resolved", "locator": locator}
    assert valid["evidence_pointer"] == "model supplied pointer"
    assert invalid["status"] == "needs_review"
    assert json.loads(invalid["structured_json"])["validation"]["source_locator"] == {"status": "unresolved"}
    job = db.one("SELECT * FROM processing_jobs")
    assert job["status"] == "done" and job["source_id"] == source["source_id"]
    assert job["finished_at"] and not job["error_text"]
    archived = Path(source["archived_path"])
    assert archived.suffix == f".{fmt}" and sha256_file(archived) == original_sha
    assert IMAClient(cfg.ima)._preflight(archived)[2] == archived.stat().st_size
    written = Path(receipt["receipt_path"]).read_text(encoding="utf-8")
    assert "parse_diagnostics" in written and "source_type" in written and "parse_warnings" in written
    assert "Closing note" not in written  # Full Source text must not enter the receipt.
    assert receipt["ima_status"] == "disabled" and pipeline.analyzer.llm.calls
    assert db.all("PRAGMA foreign_key_check") == []
    for table in ("proposals", "current_views", "ima_objects", "source_node_links", "claim_node_links"):
        assert db.one(f"SELECT COUNT(*) AS n FROM {table}")["n"] == 0
    detail = ReadOnlyQuery(cfg.db_path).source_detail(source["source_id"])
    assert detail["parse_diagnostics"] == receipt["parse_diagnostics"]
    assert next(c for c in detail["claims"] if c["claim_id"] == valid["claim_id"])["source_locator"] == validation["source_locator"]
    from fastapi.testclient import TestClient
    with TestClient(create_app(cfg.db_path)) as client:
        response = client.get(f"/api/sources/{source['source_id']}")
    assert response.status_code == 200
    assert response.json()["parse_diagnostics"] == receipt["parse_diagnostics"]
    assert "archived_path" not in response.text and str(cfg.root) not in response.text


@pytest.mark.parametrize("mode", ["standard", "deep"])
@pytest.mark.parametrize("failure", ["empty", "unsupported", "corrupt", "exception"])
def test_parse_failures_keep_inbox_and_create_only_failed_job(tmp_path, monkeypatch, mode, failure):
    cfg, db, pipeline = pipeline_fixture(tmp_path)
    request = cfg.root / "inbox" / mode / ("fixture.zip" if failure == "unsupported" else "fixture.pdf")
    if failure == "empty":
        write_pdf(request, ["", ""])
    else:
        request.write_bytes(b"invalid format")
    if failure == "exception":
        monkeypatch.setattr("pro_a.pipeline.parse_source_with_diagnostics", Mock(side_effect=RuntimeError("parser failed")))
    original_sha = sha256_file(request)
    receipt = pipeline.process_file(request, mode)
    assert receipt["status"] == "failed"
    assert sha256_file(request) == original_sha
    assert pipeline.analyzer.llm.calls == []
    if failure == "empty":
        assert receipt["error"].startswith("PARSE_TEXT_EMPTY:")
        assert receipt["parse_diagnostics"]["image_only_or_no_extractable_text"] is True
        assert any("OCR/multimodal" in warning for warning in receipt["parse_warnings"])
    job = db.one("SELECT * FROM processing_jobs")
    assert job["status"] == "failed" and job["error_text"] and job["source_id"] == ""
    assert receipt["source_id"] == "" and Path(receipt["receipt_path"]).exists()
    tables = db.all("SELECT name FROM sqlite_master WHERE type='table'")
    for row in tables:
        if row["name"] not in {"meta", "processing_jobs"}:
            assert db.one(f'SELECT COUNT(*) AS n FROM "{row["name"]}"')["n"] == 0
    assert not list((cfg.root / "archive").rglob("*.*"))
    assert db.all("PRAGMA foreign_key_check") == []


def test_partial_pdf_succeeds_with_diagnostics_and_ambiguous_evidence(tmp_path, monkeypatch):
    cfg, db, pipeline = pipeline_fixture(tmp_path)
    request = cfg.root / "inbox" / "standard" / "partial.pdf"
    write_source(request)
    pages = [SimpleNamespace(extract_text=Mock(return_value=EXCERPT)),
             SimpleNamespace(extract_text=Mock(side_effect=RuntimeError("page failed"))),
             SimpleNamespace(extract_text=Mock(return_value=EXCERPT))]
    monkeypatch.setattr("pypdf.PdfReader", lambda _: SimpleNamespace(pages=pages))
    receipt = pipeline.process_file(request, "standard")
    assert receipt["status"] == "analyzed"
    diag = receipt["parse_diagnostics"]
    assert diag["partial_parse"] is True and diag["error_units"] == 1 and diag["text_units"] == 2
    assert any("Partial extraction" in warning for warning in receipt["parse_warnings"])
    source = db.one("SELECT * FROM sources")
    assert json.loads(source["metadata_json"])["parse_diagnostics"] == diag
    claim = db.one("SELECT * FROM claims WHERE statement=?", (EXCERPT,))
    assert json.loads(claim["structured_json"])["validation"]["source_locator"] == {
        "status": "ambiguous", "locators": ["PAGE:1", "PAGE:3"],
    }
    assert db.one("SELECT status FROM processing_jobs")["status"] == "done"
    assert not request.exists() and Path(source["archived_path"]).exists()


def test_archive_and_duplicate_upgrade_contract_with_metadata_merge(tmp_path, monkeypatch):
    cfg, db, pipeline = pipeline_fixture(tmp_path)
    request = cfg.root / "inbox" / "archive" / "fixture.pdf"
    write_source(request)
    original = request.read_bytes()
    with monkeypatch.context() as guard:
        guard.setattr("pro_a.pipeline.parse_source_with_diagnostics", Mock(side_effect=AssertionError("archive must not parse")))
        archived = pipeline.process_file(request, "archive")
    assert archived["status"] == "archived" and pipeline.analyzer.llm.calls == []
    assert "parse_diagnostics" not in archived
    source_id = archived["source_id"]
    db.execute("UPDATE sources SET metadata_json=? WHERE source_id=?", (json.dumps({"retained": {"value": 7}}), source_id))
    for mode in ("standard", "deep"):
        request = cfg.root / "inbox" / mode / "fixture.pdf"
        request.write_bytes(original)
        receipt = pipeline.process_file(request, mode)
        assert receipt["status"] == "analyzed" and receipt["source_id"] == source_id
        source = db.one("SELECT * FROM sources")
        assert source["analysis_mode"] == mode and source["archived_path"] == archived["archived_path"]
        assert json.loads(source["metadata_json"])["retained"] == {"value": 7}
        for duplicate_mode in (mode, "archive", "standard"):
            request.write_bytes(original)
            calls = len(pipeline.analyzer.llm.calls)
            before = db.all("SELECT * FROM sources"), db.all("SELECT * FROM claims")
            with monkeypatch.context() as guard:
                guard.setattr("pro_a.pipeline.parse_source_with_diagnostics", Mock(side_effect=AssertionError("duplicate must not parse")))
                duplicate = pipeline.process_file(request, duplicate_mode)
            assert duplicate["status"] == "duplicate" and not request.exists()
            assert len(pipeline.analyzer.llm.calls) == calls
            assert (db.all("SELECT * FROM sources"), db.all("SELECT * FROM claims")) == before
    assert db.one("SELECT COUNT(*) AS n FROM sources")["n"] == 1
    assert db.one("SELECT COUNT(*) AS n FROM claims")["n"] == 4  # Existing upgrade semantics do not dedup Claims.


def test_failed_empty_pdf_upgrade_preserves_archived_source(tmp_path):
    cfg, db, pipeline = pipeline_fixture(tmp_path)
    request = cfg.root / "inbox" / "archive" / "empty.pdf"
    write_pdf(request, [""])
    original = request.read_bytes()
    receipt = pipeline.process_file(request, "archive")
    before = db.all("SELECT * FROM sources")
    request = cfg.root / "inbox" / "standard" / "empty.pdf"
    request.write_bytes(original)
    failed = pipeline.process_file(request, "standard")
    assert failed["status"] == "failed" and failed["source_id"] == receipt["source_id"]
    assert db.all("SELECT * FROM sources") == before and request.exists()
    assert db.one("SELECT COUNT(*) AS n FROM claims")["n"] == 0
    assert pipeline.analyzer.llm.calls == []


def test_needs_llm_keeps_parse_diagnostics(tmp_path):
    cfg, db = make_config(tmp_path)
    pipeline = IngestionPipeline(cfg, db)
    request = cfg.root / "inbox" / "standard" / "fixture.pdf"
    write_source(request)
    receipt = pipeline.process_file(request, "standard")
    assert receipt["status"] == "needs_llm"
    assert json.loads(db.one("SELECT metadata_json FROM sources")["metadata_json"])["parse_diagnostics"] == receipt["parse_diagnostics"]


def test_analyzer_source_chunking_and_truncation_recovery_remain_exact(tmp_path):
    cfg, _, pipeline = pipeline_fixture(tmp_path)
    cfg.llm.max_chunk_chars = 5000
    text = "[[PAGE:1]]\n" + "first line\n" * 480 + "[[PAGE:2]]\n" + EXCERPT
    calls = []
    original = pipeline.analyzer.llm.json

    def truncating(system, user):
        calls.append(user)
        if len(calls) == 1:
            raise LLMError("failure_category=output_truncation")
        return original(system, user)

    pipeline.analyzer.llm.json = truncating
    result = pipeline.analyzer.analyze_source("long.pdf", text, "standard")
    assert any("[[TRUNCATION_SPLIT:1]]" in call for call in calls)
    assert any("[[TRUNCATION_SPLIT:2]]" in call for call in calls)
    # The fixture response is intentionally repeated for every split; the first
    # child cannot validate Evidence that exists only in a later child.
    assert result.claims[0]["evidence_validated"] is False
    assert result.claims[0]["origin_split_path"] == "1"
    assert result.claims[1]["status"] == "needs_review"
