import json
import sqlite3
from pathlib import Path

import pytest

from pro_a.phase4_source_audit import audit_source_duplicates
from pro_a.production_promotion import sha256_file


SHA = "a" * 64
OTHER = "b" * 64


@pytest.fixture
def inputs(tmp_path):
    db = tmp_path / "production.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE sources (source_id TEXT, sha256 TEXT)")
        conn.execute("INSERT INTO sources VALUES (?, ?)", ("SRC_P", OTHER))
    manifest = tmp_path / "canonical" / "run_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"source": {"source_id": "SRC_H", "sha256": OTHER}}))
    spec = {"path": str(manifest), "rows": ["source"], "sha_field": "sha256"}
    return db, manifest, spec


def test_production_match(inputs):
    db, _, spec = inputs
    result = audit_source_duplicates(OTHER, db, [spec])
    assert len(result["production_matches"]) == 1
    assert result["duplicate_check"] == "FAIL"


def test_historical_match(inputs):
    db, manifest, spec = inputs
    manifest.write_text(json.dumps({"source": {"source_id": "H", "sha256": SHA}}))
    result = audit_source_duplicates(SHA, db, [spec])
    assert not result["production_matches"]
    assert len(result["historical_matches"]) == 1
    assert result["duplicate_check"] == "FAIL"


def test_failed_preregistration_is_not_ingestion(inputs, tmp_path):
    db, _, spec = inputs
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps({"source_sha256": SHA, "preflight_result": "FAIL"}))
    result = audit_source_duplicates(SHA, db, [spec], prior_preregistrations=(prior,))
    assert result["duplicate_check"] == "PASS"
    assert len(result["prior_attempt_only_matches"]) == 1
    assert result["prior_failed_preregistration_blocks_execution"] is False


def test_inaccessible_scratch_is_never_traversed(inputs, tmp_path, monkeypatch):
    db, _, spec = inputs
    (tmp_path / "tests-unreadable").mkdir()
    def denied(*args, **kwargs):
        raise PermissionError("scratch traversal forbidden")
    monkeypatch.setattr(Path, "iterdir", denied)
    monkeypatch.setattr(Path, "glob", denied)
    monkeypatch.setattr(Path, "rglob", denied)
    assert audit_source_duplicates(SHA, db, [spec])["authoritative_source_universe_complete"]


@pytest.mark.parametrize("missing", [False, True])
def test_authoritative_unreadable_or_missing_fails(inputs, monkeypatch, missing):
    db, manifest, spec = inputs
    if missing:
        manifest.unlink()
    else:
        original = Path.read_bytes
        def denied(path):
            if path == manifest:
                raise PermissionError("authoritative root inaccessible")
            return original(path)
        monkeypatch.setattr(Path, "read_bytes", denied)
    result = audit_source_duplicates(SHA, db, [spec])
    assert not result["authoritative_source_universe_complete"]
    assert result["duplicate_check"] == "FAIL"
    assert result["errors"][0]["path"] == str(manifest)


def test_complete_no_match(inputs):
    db, _, spec = inputs
    result = audit_source_duplicates(SHA, db, [spec])
    assert result["duplicate_check"] == "PASS"
    assert result["identities_inspected"] == 2


def test_production_read_only_and_unchanged(inputs, monkeypatch):
    db, _, spec = inputs
    before = sha256_file(db)
    original = sqlite3.connect
    def readonly(path, *args, **kwargs):
        assert "mode=ro" in str(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", readonly)
    assert audit_source_duplicates(SHA, db, [spec])["duplicate_check"] == "PASS"
    assert sha256_file(db) == before


def test_inventory_deterministic(inputs):
    db, manifest, spec = inputs
    second = manifest.with_name("second.json")
    second.write_bytes(manifest.read_bytes())
    other = {**spec, "path": str(second)}
    assert audit_source_duplicates(SHA, db, [spec, other]) == audit_source_duplicates(SHA, db, [other, spec])


def test_invalid_authoritative_sha_fails(inputs):
    db, manifest, spec = inputs
    manifest.write_text('{"source": {"sha256": "invalid"}}')
    assert not audit_source_duplicates(SHA, db, [spec])["authoritative_source_universe_complete"]
