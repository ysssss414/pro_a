"""Disposable Stage 7 community ZIP and Source Operations acceptance."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import stat
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from pro_a.community_material import (CONTRACT_VERSION, SELECTION_RULE, SOURCE_PIPELINE,
                                      import_bundle, parse_bundle, preview, render_pdf)
from pro_a.company_materials import CompanyMaterials
from pro_a.cloud_contract import DeterministicFakeProvider
from pro_a.operational_qualification import qualify
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.domains import Domains
from pro_a.workbench.domains import prepare_domains
from pro_a.workbench.lifecycle_closure import prepare_stage6_lifecycle
from pro_a.workbench.source_operations import SourceOperationError
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.stage1_scale import prepare_stage1_scale
from workbench_stage7_fixture import stage7_fixture


COMPANY = "NODE_COMMUNITY_COMPANY"
OTHER = "NODE_COMMUNITY_OTHER"
PRODUCT = "NODE_COMMUNITY_PRODUCT"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def bundle(*, evidence="光模块订单增长。", extra=None, duplicate=False):
    row = {"topic_id": "topic-1", "published_at": "2026-09-20T00:00:00+00:00",
           "author": "合成作者", "keyword_sources": ["光模块"],
           "evidence_text": evidence, "evidence_text_sha256": sha(evidence.encode()),
           "routing": {"reportable": True, "relevance_level": "强相关",
                       "category": "合成分类", "credibility": "A"}}
    topics = canonical(row)
    manifest = {"contract_version": CONTRACT_VERSION,
                "bundle_id": "COMMUNITY_BUNDLE_" + sha(topics)[:24].upper(),
                "company_input": "不是目标公司的输入", "group_id": "synthetic-group",
                "group_label": "合成社群", "days": 30, "analysis_source": "detail_search",
                "generated_at": "2026-09-23T00:00:00+00:00", "input_topic_count": 1,
                "in_range_count": 1, "topic_count": 1, "reportable_topic_count": 1,
                "omitted_unrelated": 0, "omitted_missing_analysis": 0,
                "topic_ids": ["topic-1"], "topics_file_sha256": sha(topics),
                "selection_rule": SELECTION_RULE, "source_pipeline": SOURCE_PIPELINE}
    manifest["bundle_sha256"] = sha(canonical(manifest) + topics)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", canonical(manifest))
        archive.writestr("topics.jsonl", topics)
        if extra:
            archive.writestr(extra, b"unexpected")
        if duplicate:
            archive.writestr("topics.jsonl", topics)
    return output.getvalue()


def rewritten(raw, *, manifest_change=None, topic_change=None, rehash=False):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        topic = json.loads(archive.read("topics.jsonl"))
    if manifest_change:
        manifest_change(manifest)
    if topic_change:
        topic_change(topic)
    topics = canonical(topic)
    if rehash:
        manifest["topics_file_sha256"] = sha(topics)
        manifest["bundle_id"] = "COMMUNITY_BUNDLE_" + sha(topics)[:24].upper()
        manifest["bundle_sha256"] = sha(canonical({key: value for key, value in manifest.items()
                                                    if key != "bundle_sha256"}) + topics)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", canonical(manifest))
        archive.writestr("topics.jsonl", topics)
    return output.getvalue()


def symlink_member(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest = archive.read("manifest.json")
        topics = archive.read("topics.jsonl")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest)
        info = zipfile.ZipInfo("topics.jsonl")
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, topics)
    return output.getvalue()


def case(tmp_path):
    value = stage7_fixture(tmp_path)
    with sqlite3.connect(value["config"].knowledge_db) as connection:
        connection.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
            "VALUES(?,?,?,'Synthetic','active','2026-09-23','2026-09-23')",
            [(COMPANY, "Canonical Synthetic Company", "Company"),
             (OTHER, "Other Company", "Company"), (PRODUCT, "Qualified only Product", "Product")],
        )
    prepare_domains(value["config"])
    Domains(value["config"]).register(Path(__file__).resolve().parents[1] / "domains" / "ai_hardware")
    prepare_stage1_scale(value["config"])
    prepare_stage6_lifecycle(value["config"])
    return value


def test_bundle_security_hashes_and_chinese_pdf():
    raw = bundle()
    parsed = parse_bundle(raw)
    first, ranges = render_pdf(parsed)
    second, _ = render_pdf(parsed)
    assert first == second
    assert ranges == [{"topic_id": "topic-1", "start_page": 1, "end_page": 1}]
    assert "光模块订单增长" in PdfReader(io.BytesIO(first)).pages[0].extract_text()
    assert "合成分类" not in PdfReader(io.BytesIO(first)).pages[0].extract_text()
    for broken in (bundle(extra="../escape"), bundle(extra="unknown.txt"), bundle(duplicate=True),
                   symlink_member(raw)):
        with pytest.raises(SourceOperationError):
            parse_bundle(broken)
    with pytest.raises(SourceOperationError, match="COMMUNITY_BUNDLE_SHA_MISMATCH"):
        parse_bundle(rewritten(raw, manifest_change=lambda row: row.update(company_input="Changed")))
    with pytest.raises(SourceOperationError, match="COMMUNITY_TOPICS_SHA_MISMATCH"):
        parse_bundle(rewritten(raw, topic_change=lambda row: row.update(author="Changed")))
    with pytest.raises(SourceOperationError, match="COMMUNITY_EVIDENCE_SHA_MISMATCH"):
        parse_bundle(rewritten(raw, topic_change=lambda row: row.update(evidence_text_sha256="0" * 64), rehash=True))
    with pytest.raises(SourceOperationError, match="COMMUNITY_BUNDLE_NO_REPORTABLE_TOPICS"):
        parse_bundle(rewritten(raw, manifest_change=lambda row: row.update(topic_count=0), rehash=True))
    with pytest.raises(SourceOperationError, match="COMMUNITY_BUNDLE_SENSITIVE_CONTENT"):
        parse_bundle(bundle(evidence="secret=synthetic-secret"))
    with pytest.raises(SourceOperationError, match="COMMUNITY_BUNDLE_TOO_LARGE"):
        parse_bundle(b"x" * (20 * 1024 * 1024 + 1))


def test_disposable_schema11_import_dedupes_and_binds_events(tmp_path):
    value = case(tmp_path)
    raw = bundle()
    assert preview(value["config"], raw, COMPANY)["target_company"]["node_id"] == COMPANY
    with pytest.raises(SourceOperationError, match="COMPANY_MATERIAL_TARGET_NOT_COMPANY"):
        preview(value["config"], raw, PRODUCT)
    with pytest.raises(SourceOperationError, match="COMPANY_MATERIAL_TARGET_NOT_FOUND"):
        preview(value["config"], raw, "NODE_UNAPPLIED_QUALIFIED")
    first = asyncio.run(import_bundle(value["service"], raw, COMPANY, "ai_hardware", "operator"))
    second = asyncio.run(import_bundle(value["service"], raw, COMPANY, "ai_hardware", "operator"))
    assert first["source"]["source_id"] == second["source"]["source_id"]
    assert first["run"]["processing_run_id"] == second["run"]["processing_run_id"]
    assert second["duplicate"] is True
    run = first["run"]
    assert run["company_material_intent"]["source_channel"] == "knowledge_community"
    assert run["company_material_intent"]["material_kind"] == "community_material"
    assert run["company_material_intent"]["material_date"] is None
    assert run["community_provenance"]["bundle_sha256"] == parse_bundle(raw)["manifest"]["bundle_sha256"]
    assert [item["event_type"] for item in value["service"].events(run["processing_run_id"])["items"][:3]] == [
        "KNOWLEDGE_COMMUNITY_BUNDLE_BOUND", "COMPANY_MATERIAL_INTENT_BOUND", "PROCESSING_QUEUED"]
    assert CompanyMaterials(value["config"]).timeline(COMPANY)["materials"][0]["source_channel"] == "knowledge_community"
    with pytest.raises(SourceOperationError, match="COMPANY_MATERIAL_TARGET_CONFLICT"):
        asyncio.run(import_bundle(value["service"], raw, OTHER, "ai_hardware", "operator"))
    provider = DeterministicFakeProvider()
    for _ in range(3):
        result = value["service"].advance_once(
            worker_id="stage7-community-fake", provider=provider,
            processing_run_id=run["processing_run_id"])
    assert result["state"] == "HUMAN_REVIEW_REQUIRED" and provider.call_count == 2
    with sqlite3.connect(value["config"].state_db) as connection:
        checkpoints = [json.loads(row[0]) for row in connection.execute(
            "SELECT checkpoint_json FROM source_cloud_inputs WHERE processing_run_id=?",
            (run["processing_run_id"],))]
        paths = [row[0] for row in connection.execute(
            "SELECT artifact_relative FROM source_cloud_inputs WHERE processing_run_id=?",
            (run["processing_run_id"],))]
    assert checkpoints and all(item["community_bundle_sha256"] == run["community_provenance"]["bundle_sha256"]
                               for item in checkpoints)
    for path in paths:
        payload = json.loads((value["config"].artifact_root / path).read_text(encoding="utf-8"))["payload"]
        assert "合成分类" not in json.dumps(payload, ensure_ascii=False)
        assert "不是目标公司的输入" not in json.dumps(payload, ensure_ascii=False)
    artifact_id = result["packet_artifact_id"]
    reviews = ReviewWorkbench(value["config"])
    review = reviews.read(artifact_id)
    candidate_types = {item["candidate_id"]: item["candidate_type"] for item in review["items"]}
    identity = {"actor": "operator", "session_id": "community-fixture-session"}
    revision = 0
    for row in review["review"]["rows"]:
        response = reviews.mutate(artifact_id, "decision", {
            "basis_id": review["review"]["basis_id"], "expected_revision": revision,
            "operation_id": uuid.uuid4().hex, "candidate_id": row["candidate_id"],
            "decision": "KEEP" if candidate_types[row["candidate_id"]] == "CLAIM" else "CREATE",
            "target_node_id": "", "reviewer": "Community fixture reviewer", "reason": "Synthetic review",
        }, identity)
        revision = response["revision"]
    reviews.mutate(artifact_id, "seal", {
        "basis_id": review["review"]["basis_id"], "expected_revision": revision,
        "operation_id": uuid.uuid4().hex, "reviewer": "Community fixture reviewer",
        "reason": "Synthetic seal", "confirm": True,
    }, identity)
    attribution = Attribution(value["config"])
    draft = attribution.read(artifact_id)
    assert draft["decisions"] == {}
    assert any(node["node_id"] == COMPANY and node["authority"] == "COMPANY_MATERIAL_OPERATOR_TARGET"
               for node in draft["nodes"])
    revision = 0
    for claim in draft["claims"]:
        response = attribution.mutate(artifact_id, "SAVE", {
            "basis_id": draft["basis_id"], "expected_revision": revision,
            "operation_id": uuid.uuid4().hex, "reviewer": "Community fixture reviewer",
            "reason": "Human synthetic subject link", "claim_id": claim["candidate_id"],
            "outcome": "LINK", "scope": claim["scope"],
            "links": [{"node_id": COMPANY, "role": "subject"}],
        }, identity)
        revision = response["revision"]
    sealed = attribution.mutate(artifact_id, "SEAL", {
        "basis_id": draft["basis_id"], "expected_revision": revision,
        "operation_id": uuid.uuid4().hex, "reviewer": "Community fixture reviewer",
        "reason": "Human synthetic attribution seal", "confirm": True,
    }, identity)
    qualified = qualify(value["config"], artifact_id, sealed["sidecar_id"])
    assert qualified["status"] == "AWAITING_OPERATOR_ACTION"
    material = CompanyMaterials(value["config"]).timeline(COMPANY)["materials"][0]
    assert material["lifecycle"] == "qualified_unapplied" and material["canonical"] is False
    assert material["material_trust_policy"] == "LOW_TRUST_CLUE_ONLY"
    with sqlite3.connect(value["config"].knowledge_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0


def test_authenticated_preview_then_explicit_import(tmp_path, monkeypatch):
    value = case(tmp_path)
    monkeypatch.setenv("PRO_A_WORKBENCH_TOKEN", "s" * 40)
    app = create_app(value["config"], cloud_profile=value["cloud_profile"],
                     source_profile=value["source_profile"])
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1)) as client:
        token = client.post(PREFIX + "/session", json={"token": "s" * 40},
                            headers={"origin": value["config"].origin}).json()["csrf_token"]
        headers = {"origin": value["config"].origin, "x-csrf-token": token,
                   "content-type": "application/zip", "x-company-node-id": COMPANY,
                   "x-primary-domain": "ai_hardware"}
        assert client.get(PREFIX + "/source-operations/community-domains").json()["items"][0]["domain_id"] == "ai_hardware"
        response = client.post(PREFIX + "/source-operations/community-preview", content=bundle(), headers=headers)
        assert response.status_code == 200 and response.json()["topic_count"] == 1
        with sqlite3.connect(value["config"].state_db) as connection:
            assert connection.execute("SELECT COUNT(*) FROM private_sources").fetchone()[0] == 0
        response = client.post(PREFIX + "/source-operations/community-import", content=bundle(), headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["run"]["community_provenance"]["provider"] == "zsxq"
