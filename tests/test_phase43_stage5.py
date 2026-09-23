"""Stage 5 contract tests use disposable Workbench and Production fixtures only."""
from __future__ import annotations

import sqlite3
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from pro_a.company_material_intent import CompanyMaterialError, TRUST_POLICIES, validate
from pro_a.company_materials import CompanyMaterials
from pro_a.cloud_contract import DeterministicFakeProvider
from pro_a.operational_qualification import qualify
from pro_a.workbench.attribution import Attribution
from pro_a.workbench.api import PREFIX, create_app
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.source_operations import SourceOperationError
from test_workbench_stage7 import clean_pdf, upload
from workbench_stage7_fixture import stage7_fixture


COMPANY = "NODE_STAGE5_SYNTHETIC_COMPANY"
OTHER = "NODE_STAGE5_SYNTHETIC_OTHER_COMPANY"
PRODUCT = "NODE_STAGE5_SYNTHETIC_PRODUCT"


def fixture(tmp_path):
    case = stage7_fixture(tmp_path)
    with sqlite3.connect(case["config"].knowledge_db) as connection:
        connection.executemany(
            "INSERT INTO nodes(node_id,canonical_name,primary_type,description,status,created_at,updated_at) "
            "VALUES(?,?,?,'Synthetic fixture','active','2026-09-22','2026-09-22')",
            [(COMPANY, "Synthetic Stage Five Company", "Company"),
             (OTHER, "Other Synthetic Company", "Company"),
             (PRODUCT, "Synthetic Stage Five Product", "Product")],
        )
    return case


def intent(**changes):
    return {**{"target_company_node_id": COMPANY, "material_kind": "investor_qa",
               "source_channel": "knowledge_community", "material_date": "2026-09-22",
               "operator_title": "Synthetic investor Q&A"}, **changes}


def test_intent_validation_and_company_boundary(tmp_path):
    case = fixture(tmp_path)
    first = validate(case["config"], intent())
    assert first["intent_sha256"] == validate(case["config"], dict(reversed(list(intent().items()))))["intent_sha256"]
    assert first["material_trust_policy"] == "LOW_TRUST_CLUE_ONLY"
    assert TRUST_POLICIES["company_official"] == TRUST_POLICIES["exchange_official"] == "PRIMARY_OFFICIAL"
    for value, code in [(intent(target_company_node_id=PRODUCT), "COMPANY_MATERIAL_TARGET_NOT_COMPANY"),
                        (intent(target_company_node_id="NODE_MISSING"), "COMPANY_MATERIAL_TARGET_NOT_FOUND"),
                        (intent(material_kind="guessed"), "COMPANY_MATERIAL_INTENT_INVALID"),
                        (intent(source_channel="planet"), "COMPANY_MATERIAL_INTENT_INVALID"),
                        (intent(material_date="2026-02-30"), "COMPANY_MATERIAL_DATE_INVALID"),
                        (intent(operator_title="x" * 241), "COMPANY_MATERIAL_TITLE_INVALID")]:
        with pytest.raises(CompanyMaterialError, match=code):
            validate(case["config"], value)


def test_bound_event_idempotency_conflicts_and_private_timeline(tmp_path):
    case = fixture(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    key = "stage5-synthetic-start-0001"
    started = case["service"].start(source["source_id"], idempotency_key=key,
                                    company_material_intent=intent())
    run = started["run"]
    assert run["company_material_intent"]["target_company_node_id"] == COMPANY
    assert run["company_material_intent_sha256"] == validate(case["config"], intent())["intent_sha256"]
    assert case["service"].start(source["source_id"], idempotency_key=key,
                                 company_material_intent=intent())["duplicate"]
    with pytest.raises(SourceOperationError, match="IDEMPOTENCY_CONFLICT"):
        case["service"].start(source["source_id"], idempotency_key=key,
                              company_material_intent=intent(operator_title="Changed"))
    with pytest.raises(SourceOperationError, match="COMPANY_MATERIAL_INTENT_CONFLICT"):
        case["service"].start(source["source_id"], idempotency_key="stage5-synthetic-start-0002",
                              company_material_intent=intent(operator_title="Changed"))
    with pytest.raises(SourceOperationError, match="COMPANY_MATERIAL_TARGET_CONFLICT"):
        case["service"].start(source["source_id"], idempotency_key="stage5-synthetic-start-0003",
                              company_material_intent=intent(target_company_node_id=OTHER))
    events = case["service"].events(run["processing_run_id"])["items"]
    assert events[0]["event_type"] == "COMPANY_MATERIAL_INTENT_BOUND"
    assert events[1]["event_type"] == "PROCESSING_QUEUED"
    timeline = CompanyMaterials(case["config"]).timeline(COMPANY)
    assert timeline["counts"] == {"total": 1, "private": 1, "canonical": 0}
    assert timeline["materials"][0]["association_basis"] == "company_material_intent"
    assert timeline["materials"][0]["claim_count"] is None
    assert timeline["snapshot_id"] == CompanyMaterials(case["config"]).timeline(COMPANY)["snapshot_id"]
    with sqlite3.connect(case["config"].knowledge_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM claim_node_links").fetchone()[0] == 0


def test_activated_canonical_material_merges_with_private_lineage(tmp_path):
    case = fixture(tmp_path)
    materials = CompanyMaterials(case["config"])
    assert materials.timeline(COMPANY)["materials"] == []
    with pytest.raises(CompanyMaterialError, match="COMPANY_MATERIAL_TARGET_NOT_COMPANY"):
        materials.timeline(PRODUCT)
    source = upload(case, clean_pdf(tmp_path))
    case["service"].start(source["source_id"], idempotency_key="stage5-synthetic-start-0004",
                          company_material_intent=intent())
    with sqlite3.connect(case["config"].knowledge_db) as connection:
        connection.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,"
                           "ingestion_mode,ingested_at) VALUES(?,?,?,? ,?,'synthetic','2026-09-23')",
                           (source["source_id"], "Canonical synthetic report", "synthetic.pdf", "synthetic",
                            source["source_sha256"]))
        connection.execute("INSERT INTO claims(claim_id,statement,nature,ingestion_time,source_id,created_at) "
                           "VALUES('CLAIM_STAGE5','Synthetic Company reports capacity growth.','fact',"
                           "'2026-09-23',?,'2026-09-23')", (source["source_id"],))
        connection.execute("INSERT INTO source_node_links(source_id,node_id,role) VALUES(?,?,'subject')",
                           (source["source_id"], COMPANY))
        connection.executemany("INSERT INTO claim_node_links(claim_id,node_id,role) VALUES('CLAIM_STAGE5',?,?)",
                               [(COMPANY, "subject"), (PRODUCT, "context")])
    timeline = materials.timeline(COMPANY)
    assert timeline["counts"] == {"total": 1, "private": 0, "canonical": 1}
    row = timeline["materials"][0]
    assert row["processing_run_id"] and row["canonical_source_id"] == source["source_id"]
    assert row["title"] == "Canonical synthetic report" and row["lifecycle"] == "activated"
    assert row["association_basis"] == "source_node_link+claim_node_link"
    assert row["claim_count"] == 1 and row["linked_node_count"] == 2
    assert {node["node_id"] for node in row["linked_nodes"]} == {COMPANY, PRODUCT}
    assert row["current_view_impact_candidate_count"] == 0


def test_canonical_source_does_not_keep_operator_company_association(tmp_path):
    case = fixture(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    case["service"].start(source["source_id"], idempotency_key="stage5-synthetic-start-0005",
                          company_material_intent=intent())
    with sqlite3.connect(case["config"].knowledge_db) as connection:
        connection.execute("INSERT INTO sources(source_id,title,original_name,archived_path,sha256,"
                           "ingestion_mode,ingested_at) VALUES(?,?,?,? ,?,'synthetic','2026-09-23')",
                           (source["source_id"], "Canonical other-company report", "synthetic.pdf",
                            "synthetic", source["source_sha256"]))
        connection.execute("INSERT INTO source_node_links(source_id,node_id,role) VALUES(?,?,'subject')",
                           (source["source_id"], OTHER))
    assert CompanyMaterials(case["config"]).timeline(COMPANY)["materials"] == []
    other = CompanyMaterials(case["config"]).timeline(OTHER)["materials"]
    assert len(other) == 1 and other[0]["association_basis"] == "source_node_link"
    assert other[0]["company_material_intent_sha256"] is None


def test_fake_provider_review_attribution_and_qualified_unapplied(tmp_path):
    case = fixture(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    run_id = case["service"].start(
        source["source_id"], idempotency_key="stage5-synthetic-vertical-0001",
        company_material_intent=intent(source_channel="company_official"),
    )["run"]["processing_run_id"]
    provider = DeterministicFakeProvider()
    for _ in range(3):
        run = case["service"].advance_once(
            worker_id="stage5-fake-worker", provider=provider, processing_run_id=run_id)
    assert provider.call_count == 2 and run["state"] == "HUMAN_REVIEW_REQUIRED"
    with sqlite3.connect(case["config"].state_db) as connection:
        checkpoints = [json.loads(row[0]) for row in connection.execute(
            "SELECT checkpoint_json FROM source_cloud_inputs WHERE processing_run_id=?", (run_id,))]
    assert len(checkpoints) == 2
    assert all(item["company_material_intent_sha256"] == run["company_material_intent_sha256"]
               and item["company_material_intent"]["target_company_node_id"] == COMPANY
               for item in checkpoints)
    # The provider receives Source-local payload; the operator's different target is checkpoint metadata only.
    with sqlite3.connect(case["config"].state_db) as connection:
        artifact = connection.execute("SELECT artifact_relative FROM source_cloud_inputs "
                                      "WHERE processing_run_id=? ORDER BY ordinal LIMIT 1", (run_id,)).fetchone()[0]
    cloud_input = json.loads((case["config"].artifact_root / artifact).read_text(encoding="utf-8"))
    assert "Synthetic Stage Five Company" not in json.dumps(cloud_input["payload"])
    assert "Stage Seven Synthetic Company" in json.dumps(cloud_input["payload"])

    artifact_id = run["packet_artifact_id"]
    reviews = ReviewWorkbench(case["config"])
    review = reviews.read(artifact_id)
    candidate_types = {item["candidate_id"]: item["candidate_type"] for item in review["items"]}
    identity = {"actor": "operator", "session_id": "stage5-fixture-session"}
    revision = 0
    for row in review["review"]["rows"]:
        response = reviews.mutate(artifact_id, "decision", {
            "basis_id": review["review"]["basis_id"], "expected_revision": revision,
            "operation_id": uuid.uuid4().hex, "candidate_id": row["candidate_id"],
            "decision": "KEEP" if candidate_types[row["candidate_id"]] == "CLAIM" else "CREATE",
            "target_node_id": "", "reviewer": "Stage Five Reviewer", "reason": "Synthetic fixture review.",
        }, identity)
        revision = response["revision"]
    reviews.mutate(artifact_id, "seal", {
        "basis_id": review["review"]["basis_id"], "expected_revision": revision,
        "operation_id": uuid.uuid4().hex, "reviewer": "Stage Five Reviewer",
        "reason": "Synthetic fixture seal.", "confirm": True,
    }, identity)
    attribution = Attribution(case["config"])
    draft = attribution.read(artifact_id)
    target = [node for node in draft["nodes"] if node["node_id"] == COMPANY]
    assert len(target) == 1 and target[0]["authority"] == "COMPANY_MATERIAL_OPERATOR_TARGET"
    assert draft["decisions"] == {}
    revision = 0
    for claim in draft["claims"]:
        response = attribution.mutate(artifact_id, "SAVE", {
            "basis_id": draft["basis_id"], "expected_revision": revision,
            "operation_id": uuid.uuid4().hex, "reviewer": "Stage Five Reviewer",
            "reason": "Human subject attribution for synthetic Company.",
            "claim_id": claim["candidate_id"], "outcome": "LINK",
            "scope": claim["scope"], "links": [{"node_id": COMPANY, "role": "subject"}],
        }, identity)
        revision = response["revision"]
    sealed = attribution.mutate(artifact_id, "SEAL", {
        "basis_id": draft["basis_id"], "expected_revision": revision,
        "operation_id": uuid.uuid4().hex, "reviewer": "Stage Five Reviewer",
        "reason": "Synthetic fixture attribution seal.", "confirm": True,
    }, identity)
    qualified = qualify(case["config"], artifact_id, sealed["sidecar_id"])
    assert qualified["status"] == "AWAITING_OPERATOR_ACTION"
    timeline = CompanyMaterials(case["config"]).timeline(COMPANY)
    assert timeline["materials"][0]["lifecycle"] == "qualified_unapplied"
    assert timeline["materials"][0]["canonical"] is False
    with sqlite3.connect(case["config"].knowledge_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0


def test_http_company_search_intent_and_timeline(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    source = upload(case, clean_pdf(tmp_path))
    monkeypatch.setenv("PRO_A_WORKBENCH_TOKEN", "s" * 40)
    app = create_app(case["config"], cloud_profile=case["cloud_profile"],
                     source_profile=case["source_profile"])
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1)) as client:
        token = client.post(PREFIX + "/session", json={"token": "s" * 40},
                            headers={"origin": case["config"].origin}).json()["csrf_token"]
        assert COMPANY in {row["node_id"] for row in
                           client.get(PREFIX + "/research/companies/search?q=Synthetic").json()["items"]}
        assert client.get(PREFIX + f"/research/companies/{COMPANY}").status_code == 200
        assert client.get(PREFIX + f"/research/companies/{PRODUCT}").json()["detail"] == "COMPANY_MATERIAL_TARGET_NOT_COMPANY"
        started = client.post(PREFIX + f"/source-operations/{source['source_id']}/process",
                              json={"idempotency_key": "stage5-synthetic-api-0001",
                                    "company_material_intent": intent()},
                              headers={"origin": case["config"].origin, "x-csrf-token": token})
        assert started.status_code == 200
        assert started.json()["run"]["company_material_intent"]["target_company_node_id"] == COMPANY
        page = client.get(PREFIX + f"/research/companies/{COMPANY}/materials").json()
        assert page["counts"]["total"] == 1 and page["materials"][0]["private"] is True
        assert client.get(PREFIX + f"/research/companies/{PRODUCT}/materials").status_code == 422
