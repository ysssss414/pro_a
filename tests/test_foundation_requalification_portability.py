"""Public synthetic control-flow/handle probes; never a successful private audit."""
import copy
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import test_foundation_requalification as historical
from pro_a.foundation_execution_contract import BOUND_CONTRACT, uses_contract
from pro_a.production_promotion import PromotionError


@pytest.fixture
def runbook(tmp_path, monkeypatch):
    module = historical.load_migration_runbook()
    # Isolated locators only: no private database, archive or packet is created.
    for name in ("OLD", "GOV", "PRIOR_OUT", "OUT", "PRODUCTION", "ARCHIVE", "INSTRUCTION"):
        monkeypatch.setattr(module, name, tmp_path / name.lower())
    monkeypatch.delenv("RUN_PRIVATE_FOUNDATION_AUDIT", raising=False)
    return module


def test_public_foundation_requalification_contract():
    module = historical.load_migration_runbook()
    assert callable(module.preflight) and callable(module.requalification)
    assert callable(module.require_exclusive_read_handle)
    assert uses_contract({"execution_contract": BOUND_CONTRACT})
    changed = copy.deepcopy(BOUND_CONTRACT)
    changed["production_authorization"] = True
    with pytest.raises(PromotionError, match="EXECUTION_CONTRACT_DRIFT"):
        uses_contract({"execution_contract": changed})


@pytest.mark.parametrize("value", [None, "false"])
def test_public_absent_private_baseline_is_explicit_skip(runbook, monkeypatch, value):
    if value is not None:
        monkeypatch.setenv("RUN_PRIVATE_FOUNDATION_AUDIT", value)
    with pytest.raises(pytest.skip.Exception, match="historical private Foundation baseline is not configured in this checkout"):
        historical.require_private_foundation_baseline(runbook)


@pytest.mark.parametrize("value", ["", "yes", "1", "typo"])
def test_public_private_request_cannot_silently_downgrade(runbook, monkeypatch, value):
    monkeypatch.setenv("RUN_PRIVATE_FOUNDATION_AUDIT", value)
    with pytest.raises(pytest.fail.Exception, match="must be true or false"):
        historical.require_private_foundation_baseline(runbook)


def test_public_enabled_missing_database_fails(runbook, monkeypatch):
    monkeypatch.setenv("RUN_PRIVATE_FOUNDATION_AUDIT", "true")
    with pytest.raises(pytest.fail.Exception, match="prerequisite missing:.*production"):
        historical.require_private_foundation_baseline(runbook)


@pytest.mark.parametrize("marker", ["OLD", "GOV", "PRIOR_OUT", "ARCHIVE", "INSTRUCTION"])
def test_public_partial_authority_fails_even_without_explicit_request(runbook, marker):
    getattr(runbook, marker).mkdir()
    with pytest.raises(pytest.fail.Exception, match="prerequisite missing"):
        historical.require_private_foundation_baseline(runbook)


def virtual_prerequisites(runbook, monkeypatch, missing=None):
    """Presence-only control-flow model, not forged private artifacts or authority."""
    monkeypatch.setenv("RUN_PRIVATE_FOUNDATION_AUDIT", "true")
    required = {
        runbook.PRODUCTION, runbook.ARCHIVE, runbook.INSTRUCTION,
        runbook.OLD / "foundation_complete_review_packet.json",
        runbook.GOV / "human_evidence_governance_authorization_manifest.json",
        runbook.PRIOR_OUT / "schema_migration_stop_receipt.json",
    }
    monkeypatch.setattr(Path, "is_file", lambda path: path in required and path != missing)


@pytest.mark.parametrize("missing", ["ARCHIVE", "INSTRUCTION", "packet", "manifest", "stop"])
def test_public_enabled_incomplete_authority_fails(runbook, monkeypatch, missing):
    paths = {"packet": runbook.OLD / "foundation_complete_review_packet.json",
             "manifest": runbook.GOV / "human_evidence_governance_authorization_manifest.json",
             "stop": runbook.PRIOR_OUT / "schema_migration_stop_receipt.json"}
    path = paths[missing] if missing in paths else getattr(runbook, missing)
    virtual_prerequisites(runbook, monkeypatch, path)
    with pytest.raises(pytest.fail.Exception, match="prerequisite missing"):
        historical.require_private_foundation_baseline(runbook)


def test_public_enabled_archive_hash_mismatch_uses_original_rejection(runbook, monkeypatch, tmp_path):
    # Deliberately invalid public bytes, never an archive intended to pass authority.
    invalid = tmp_path / "synthetic-invalid-input.txt"
    invalid.write_text("Public negative-test bytes; not a Foundation archive.", encoding="utf-8")
    monkeypatch.setattr(runbook, "ARCHIVE", invalid)
    virtual_prerequisites(runbook, monkeypatch)
    historical.require_private_foundation_baseline(runbook)
    with pytest.raises(PromotionError, match="ARCHIVE_SHA_DRIFT"):
        runbook.immutable_inputs()
    assert not runbook.OUT.exists()  # Rejected before ZIP inspection or audit writes.


@pytest.mark.parametrize("returncode", [None, 1])
def test_public_configured_dispatches_original_strict_audit(runbook, monkeypatch, returncode):
    virtual_prerequisites(runbook, monkeypatch)
    monkeypatch.setattr(historical, "load_migration_runbook", lambda: runbook)
    calls = []

    class StrictAuditReached(Exception):
        pass

    def strict_dispatch(command, **kwargs):
        calls.append(command)
        assert command[:2] == [sys.executable, "-c"]
        assert kwargs["cwd"] == historical.ROOT
        code = command[2]
        assert "gc.disable()" in code
        assert "m['preflight'](committed=m['git']('rev-parse', 'HEAD') != m['STOPPED_COMMIT'])" in code
        assert "m['require_exclusive_read_handle'](m['PRODUCTION'])" in code
        assert "assert m['production_identity'](m['PRODUCTION']) == before" in code
        if returncode is None:
            raise StrictAuditReached("Original audit subprocess reached; no real private audit performed")
        return SimpleNamespace(returncode=returncode, stdout="", stderr="strict authority rejection")

    monkeypatch.setattr(historical.subprocess, "run", strict_dispatch)
    expected = StrictAuditReached if returncode is None else AssertionError
    with pytest.raises(expected):
        historical.test_full_old_baseline_preflight_releases_handle_without_gc()
    assert len(calls) == 1


@pytest.mark.parametrize("broken_schema", [False, True])
def test_public_identity_closes_handles_without_gc(tmp_path, broken_schema):
    # An independent minimal public SQLite contract fixture, never private authority.
    code = r"""
from contextlib import closing
import gc, os, runpy, sqlite3, sys
from pathlib import Path
from pro_a import production_promotion as pp
m = runpy.run_path('scripts/phase3f_foundation_schema_migration.py')
path = Path(sys.argv[1])
with closing(sqlite3.connect(path)) as con:
    con.execute('CREATE TABLE meta(key TEXT, value TEXT)')
    con.execute("INSERT INTO meta VALUES ('schema_version', 'synthetic-public-contract')")
    con.commit()
connections = []
original = pp.connect_read_only
def tracked(path):
    con = original(path)
    connections.append(con)
    return con
pp.connect_read_only = tracked
gc.disable()
before = path.read_bytes()
if sys.argv[2] == 'True':
    with closing(sqlite3.connect(path)) as con:
        con.execute('DROP TABLE meta')
        con.commit()
    before = path.read_bytes()
    try:
        pp.production_identity(path)
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError('missing schema must fail')
else:
    identity = pp.production_identity(path)
    with closing(pp.connect_read_only(path)) as con:
        assert con.execute('PRAGMA query_only').fetchone()[0] == 1
    assert pp.production_identity(path) == identity
for con in connections:
    try:
        con.execute('SELECT 1')
    except sqlite3.ProgrammingError:
        pass
    else:
        raise AssertionError('read handle leaked with GC disabled')
if os.name == 'nt':
    m['require_exclusive_read_handle'](path)
assert path.read_bytes() == before
assert not gc.isenabled()
"""
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path / "synthetic-read-handle.sqlite"), str(broken_schema)],
                            cwd=historical.ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
