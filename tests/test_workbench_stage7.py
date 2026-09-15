from __future__ import annotations

import asyncio
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from fastapi.testclient import TestClient
import pytest
from pypdf import PdfReader, PdfWriter

from multiformat_helpers import write_pdf
from pro_a.cloud_contract import CONTRACT_VERSION, DeterministicFakeProvider, RETRY_OWNER
from pro_a.operational_operator import Operator, OperatorConfig
from pro_a.operational_qualification import qualify
from pro_a.research_explorer import ResearchExplorer
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.cloud_jobs import CloudProfile
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.source_operations import (
    DEFAULT_MAX_PDF_BYTES, SourceOperationError, SourceOperations, prepare_source_operations,
)
from workbench_stage7_fixture import stage7_fixture


TEXT = "Stage Seven Synthetic Company reported 2026 capacity growth of 20 percent."


async def chunks(body: bytes, size: int = 17):
    for offset in range(0, len(body), size):
        yield body[offset:offset + size]


def clean_pdf(tmp_path: Path, name: str = "private-stage-seven.pdf", text: str = TEXT) -> Path:
    path = tmp_path / name
    write_pdf(path, [text])
    return path


def upload(case, path: Path, filename: str | None = None):
    body = path.read_bytes()
    return asyncio.run(case["service"].upload(
        chunks(body), filename=filename or path.name, mime_type="application/pdf"))


def start_and_finish(case, path: Path):
    source = upload(case, path)
    started = case["service"].start(
        source["source_id"], idempotency_key="stage7-golden-path-0001")
    provider = DeterministicFakeProvider()
    first = case["service"].advance_once(
        worker_id="stage7-worker", provider=provider,
        processing_run_id=started["run"]["processing_run_id"])
    assert first["state"] == "EXTRACTION_PROCESSING" and provider.call_count == 0
    second = case["service"].advance_once(
        worker_id="stage7-worker", provider=provider,
        processing_run_id=started["run"]["processing_run_id"])
    assert second["state"] == "SEMANTIC_PROCESSING" and provider.call_count == 1
    final = case["service"].advance_once(
        worker_id="stage7-worker", provider=provider,
        processing_run_id=started["run"]["processing_run_id"])
    return source, started, final, provider


def test_schema8_exact_backup_additive_and_stage6_jobs_survive(tmp_path):
    case = stage7_fixture(tmp_path)
    backup = case["config"].state_db.with_name("workbench.sqlite3.stage6-backup")
    assert backup.read_bytes() == case["stage6_bytes"]
    assert prepare_source_operations(case["config"])["status"] == "ALREADY_PREPARED"
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='cloud_jobs'").fetchone()[0]
        assert "SOURCE_ANALYSIS_PIECE" in schema
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        assert connection.execute(
            "SELECT value FROM workbench_meta WHERE key='schema_version'").fetchone()[0] == "8"


def test_streamed_upload_hash_immutable_duplicates_and_canonical_preflight(tmp_path):
    case = stage7_fixture(tmp_path)
    pdf = clean_pdf(tmp_path)
    first = upload(case, pdf)
    assert first["source_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert first["validation"]["gate"] == "PASS" and first["validation"]["ocr_used"] is False
    assert first["private"] is True and "storage_relative" not in first
    stored = case["config"].artifact_root / "private-sources" / first["source_sha256"][:2] / (first["source_id"] + ".pdf")
    before = stored.read_bytes()
    same_name = upload(case, pdf)
    other_name = upload(case, pdf, "renamed-private.pdf")
    assert same_name["source_id"] == other_name["source_id"] == first["source_id"]
    assert same_name["duplicate"] and other_name["duplicate"]
    assert stored.read_bytes() == before
    different = clean_pdf(tmp_path, "private-stage-seven-2.pdf", TEXT + " Updated.")
    same_filename_different_bytes = upload(case, different, pdf.name)
    assert same_filename_different_bytes["source_id"] != first["source_id"]
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM private_sources").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM source_upload_events WHERE outcome='DUPLICATE'").fetchone()[0] == 2


@pytest.mark.parametrize("kind,code", [
    ("empty", "EMPTY_SOURCE"),
    ("signature", "INVALID_PDF_SIGNATURE"),
    ("corrupt", "CORRUPT_PDF_UNSUPPORTED"),
    ("scanned", "OCR_REQUIRED_UNSUPPORTED"),
    ("encrypted", "ENCRYPTED_PDF_UNSUPPORTED"),
])
def test_unsupported_pdfs_fail_early_without_source_or_job(tmp_path, kind, code):
    case = stage7_fixture(tmp_path)
    path = tmp_path / f"{kind}.pdf"
    if kind == "empty": path.write_bytes(b"")
    elif kind == "signature": path.write_bytes(b"not a pdf")
    elif kind == "corrupt": path.write_bytes(b"%PDF-1.7\ncorrupt")
    elif kind == "scanned": write_pdf(path, [""])
    else:
        plain = clean_pdf(tmp_path, "plain.pdf")
        reader = PdfReader(plain); writer = PdfWriter()
        for page in reader.pages: writer.add_page(page)
        writer.encrypt("secret")
        with path.open("wb") as output: writer.write(output)
    with pytest.raises(SourceOperationError, match=code):
        upload(case, path)
    with closing(sqlite3.connect(case["config"].state_db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM private_sources").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM cloud_jobs").fetchone()[0] == 0


def test_size_boundary_blocks_before_pdf_parse_and_is_configurable(tmp_path):
    case = stage7_fixture(tmp_path, max_pdf_bytes=1024 * 1024)
    valid = clean_pdf(tmp_path)
    assert upload(case, valid)["size_bytes"] < 1024 * 1024
    exact = clean_pdf(tmp_path, "exact-limit.pdf", TEXT + " Exact boundary.")
    original = exact.read_bytes()
    exact.write_bytes(original + b"\n%" + b"x" * (1024 * 1024 - len(original) - 2))
    assert exact.stat().st_size == 1024 * 1024
    assert upload(case, exact)["size_bytes"] == 1024 * 1024
    oversized = tmp_path / "oversized.pdf"
    oversized.write_bytes(b"%PDF-" + b"x" * (1024 * 1024))
    with pytest.raises(SourceOperationError, match="SOURCE_TOO_LARGE"):
        upload(case, oversized)
    assert case["source_profile"].max_pdf_bytes == 1024 * 1024
    assert DEFAULT_MAX_PDF_BYTES == 20 * 1024 * 1024


def test_http_upload_only_registers_and_start_is_durable_idempotent(tmp_path, monkeypatch):
    case = stage7_fixture(tmp_path)
    monkeypatch.setenv("PRO_A_WORKBENCH_TOKEN", "t" * 40)
    app = create_app(case["config"], cloud_profile=case["cloud_profile"],
                     source_profile=case["source_profile"])
    pdf = clean_pdf(tmp_path)
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1)) as client:
        login = client.post(PREFIX + "/session", json={"token": "t" * 40},
                            headers={"origin": case["config"].origin})
        csrf = login.json()["csrf_token"]
        response = client.post(PREFIX + "/source-operations/upload", content=pdf.read_bytes(),
                               headers={"origin": case["config"].origin,
                                        "x-csrf-token": csrf, "content-type": "application/pdf",
                                        "x-source-filename": "operator.pdf"})
        assert response.status_code == 200
        source_id = response.json()["source_id"]
        with closing(sqlite3.connect(case["config"].state_db)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM cloud_jobs").fetchone()[0] == 0
        body = {"idempotency_key": "stage7-http-process-0001", "reprocess_reason": ""}
        first = client.post(f"{PREFIX}/source-operations/{source_id}/process", json=body,
                            headers={"origin": case["config"].origin, "x-csrf-token": csrf})
        second = client.post(f"{PREFIX}/source-operations/{source_id}/process", json=body,
                             headers={"origin": case["config"].origin, "x-csrf-token": csrf})
        assert first.status_code == second.status_code == 200
        assert first.json()["run"]["processing_run_id"] == second.json()["run"]["processing_run_id"]
        assert second.json()["duplicate"] is True
        assert client.get(f"{PREFIX}/source-operations/{source_id}").status_code == 200
        capabilities = client.get(PREFIX + "/source-operations").json()["capabilities"]
        assert capabilities == {
            "source_class": "PRIVATE_CLEAN_PDF", "mime_types": ["application/pdf"],
            "max_pdf_bytes": case["source_profile"].max_pdf_bytes,
            "single_file": True, "ocr_supported": False,
        }


def test_golden_path_uses_durable_jobs_and_survives_restart(tmp_path):
    case = stage7_fixture(tmp_path)
    source, started, final, provider = start_and_finish(case, clean_pdf(tmp_path))
    assert final["state"] == "HUMAN_REVIEW_REQUIRED"
    assert final["packet_artifact_id"] and final["review"]["status"] == "DRAFT"
    assert len(final["jobs"]) == 2 and provider.call_count == 2
    assert all(job["retry_owner"] == RETRY_OWNER for job in final["jobs"])
    assert all(job["runtime_identity"]["cloud_contract_version"] == CONTRACT_VERSION for job in final["jobs"])
    assert final["usage"]["status"] == "KNOWN" and final["usage"]["total_tokens"] == 240
    restarted = SourceOperations(case["config"], case["source_profile"], case["cloud_profile"])
    persisted = restarted.source(source["source_id"])
    assert persisted["latest_run"]["processing_run_id"] == started["run"]["processing_run_id"]
    assert persisted["latest_run"]["state"] == "HUMAN_REVIEW_REQUIRED"
    assert persisted["latest_run"]["review"]["deep_link"].endswith(final["packet_artifact_id"])
    duplicate = restarted.start(source["source_id"], idempotency_key="stage7-completed-repeat-0002")
    assert duplicate["duplicate"] is True
    assert duplicate["run"]["processing_run_id"] == final["processing_run_id"]
    assert restarted.advance_once(worker_id="restart-worker", provider=provider,
                                  processing_run_id=final["processing_run_id"]) is None
    assert provider.call_count == 2


def test_budget_failure_propagates_and_explicit_failed_reprocess_keeps_source_identity(tmp_path):
    case = stage7_fixture(tmp_path)
    base = case["cloud_profile"]
    bounded = CloudProfile(
        base.provider, base.requested_model, base.accepted_model_aliases,
        base.provider_adapter_version, base.timeout_seconds, base.max_output_tokens,
        base.max_calls, base.max_attempts, 100,
    )
    service = SourceOperations(case["config"], case["source_profile"], bounded)
    source = asyncio.run(service.upload(chunks(clean_pdf(tmp_path).read_bytes()),
                                        filename="budget.pdf", mime_type="application/pdf"))
    run = service.start(source["source_id"], idempotency_key="stage7-budget-run-0001")["run"]
    service.advance_once(worker_id="budget-worker", processing_run_id=run["processing_run_id"])
    provider = DeterministicFakeProvider()
    failed = service.advance_once(worker_id="budget-worker", provider=provider,
                                  processing_run_id=run["processing_run_id"])
    assert failed["state"] == "FAILED" and failed["error"]["code"] == "BUDGET_EXCEEDED"
    assert provider.call_count == 0
    reprocessed = service.start(source["source_id"], idempotency_key="stage7-budget-run-0002",
                                reprocess_reason="Explicitly changed bounded runtime after failure.")
    assert reprocessed["duplicate"] is False
    assert reprocessed["run"]["source_id"] == source["source_id"]
    assert reprocessed["run"]["processing_run_id"] != run["processing_run_id"]


def test_runtime_and_registered_input_drift_fail_closed_without_provider_call(tmp_path):
    case = stage7_fixture(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    run = case["service"].start(source["source_id"], idempotency_key="stage7-drift-run-0001")["run"]
    case["service"].advance_once(worker_id="drift-worker", processing_run_id=run["processing_run_id"])
    with closing(sqlite3.connect(case["config"].state_db)) as connection, connection:
        relative = connection.execute(
            "SELECT artifact_relative FROM source_cloud_inputs WHERE processing_run_id=?",
            (run["processing_run_id"],)).fetchone()[0]
    (case["config"].artifact_root / relative).unlink()
    provider = DeterministicFakeProvider()
    blocked = case["service"].advance_once(worker_id="drift-worker", provider=provider,
                                           processing_run_id=run["processing_run_id"])
    assert blocked["state"] == "BLOCKED" and "ARTIFACT" in blocked["error"]["code"]
    assert provider.call_count == 0

    other = upload(case, clean_pdf(tmp_path, "runtime.pdf", TEXT + " Runtime case."))
    drift_run = case["service"].start(other["source_id"], idempotency_key="stage7-drift-run-0002")["run"]
    with closing(sqlite3.connect(case["config"].state_db)) as connection, connection:
        connection.execute("UPDATE source_processing_runs SET runtime_sha256=? WHERE processing_run_id=?",
                           ("0" * 64, drift_run["processing_run_id"]))
    runtime_blocked = case["service"].advance_once(
        worker_id="drift-worker", provider=provider,
        processing_run_id=drift_run["processing_run_id"])
    assert runtime_blocked["state"] == "BLOCKED"
    assert runtime_blocked["error"]["code"] == "RUNTIME_DRIFT"
    assert provider.call_count == 0


def test_unknown_external_outcome_projects_recovery_and_never_resubmits(tmp_path):
    case = stage7_fixture(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    run = case["service"].start(source["source_id"], idempotency_key="stage7-recovery-case-0001")["run"]
    provider = DeterministicFakeProvider("unknown_external_outcome")
    case["service"].advance_once(worker_id="worker-a", provider=provider,
                                 processing_run_id=run["processing_run_id"])
    recovered = case["service"].advance_once(worker_id="worker-a", provider=provider,
                                             processing_run_id=run["processing_run_id"])
    assert recovered["state"] == "RECOVERY_REQUIRED"
    assert recovered["error"]["manual_recovery_required"] is True
    assert provider.call_count == 1
    restarted = SourceOperations(case["config"], case["source_profile"], case["cloud_profile"])
    assert restarted.advance_once(worker_id="worker-b", provider=provider,
                                  processing_run_id=run["processing_run_id"]) is None
    assert provider.call_count == 1
    with pytest.raises(SourceOperationError, match="RECOVERY_REQUIRED_REQUIRES_RECONCILIATION"):
        restarted.start(source["source_id"], idempotency_key="stage7-recovery-case-0002",
                        reprocess_reason="runtime review")


def test_review_attribution_qualification_disposable_activation_and_research(tmp_path):
    case = stage7_fixture(tmp_path)
    source, _, run, _ = start_and_finish(case, clean_pdf(tmp_path))
    artifact_id = run["packet_artifact_id"]
    reviews = ReviewWorkbench(case["config"])
    identity = {"actor": "operator", "session_id": "stage7-session"}
    review = reviews.read(artifact_id)
    candidate_types = {item["candidate_id"]: item["candidate_type"] for item in review["items"]}
    revision = 0
    for row in review["review"]["rows"]:
        decision = "KEEP" if candidate_types[row["candidate_id"]] == "CLAIM" else "CREATE"
        response = reviews.mutate(artifact_id, "decision", {
            "basis_id": review["review"]["basis_id"], "expected_revision": revision,
            "operation_id": uuid.uuid4().hex, "candidate_id": row["candidate_id"],
            "decision": decision, "target_node_id": "", "reviewer": "Stage Seven Reviewer",
            "reason": "Explicit synthetic acceptance decision.",
        }, identity)
        revision = response["revision"]
    reviews.mutate(artifact_id, "seal", {
        "basis_id": review["review"]["basis_id"], "expected_revision": revision,
        "operation_id": uuid.uuid4().hex, "reviewer": "Stage Seven Reviewer",
        "reason": "Seal explicit synthetic decisions.", "confirm": True,
    }, identity)
    attribution = Attribution(case["config"])
    draft = attribution.read(artifact_id)
    revision = 0
    node_id = draft["nodes"][0]["node_id"]
    for claim in draft["claims"]:
        response = attribution.mutate(artifact_id, "SAVE", {
            "basis_id": draft["basis_id"], "expected_revision": revision,
            "operation_id": uuid.uuid4().hex, "reviewer": "Stage Seven Reviewer",
            "reason": "Explicit Source-to-Claim-to-Node attribution.",
            "claim_id": claim["candidate_id"], "outcome": "LINK",
            "scope": claim["scope"], "links": [{"node_id": node_id, "role": "subject"}],
        }, identity)
        revision = response["revision"]
    sealed = attribution.mutate(artifact_id, "SEAL", {
        "basis_id": draft["basis_id"], "expected_revision": revision,
        "operation_id": uuid.uuid4().hex, "reviewer": "Stage Seven Reviewer",
        "reason": "Seal explicit attribution.", "confirm": True,
    }, identity)
    envelope = qualify(case["config"], artifact_id, sealed["sidecar_id"])
    operator = Operator(OperatorConfig(case["config"], tmp_path / "operator" / "ledger.sqlite3"))
    operator.initialize()
    operator.register(envelope["object_id"], confirm=envelope["object_id"])
    receipt = operator.execute(envelope["object_id"], confirm=envelope["object_id"])
    operator.reconcile(envelope["object_id"])
    projected = case["service"].source(source["source_id"])["latest_run"]
    assert projected["state"] == "ACTIVATED"
    assert projected["qualification"]["status"] == "AWAITING_OPERATOR_ACTION"
    assert projected["activation_receipt"]["object_id"] == receipt["object_id"]
    research = ResearchExplorer(case["config"])
    discovered = research.source(source["source_id"])
    assert discovered["source"]["source_id"] == source["source_id"]
    assert discovered["claims"]["items"][0]["linked_nodes"][0]["node_id"] == node_id
    assert ResearchExplorer(case["config"]).node(node_id)["node"]["node_id"] == node_id
