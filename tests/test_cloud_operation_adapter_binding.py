"""Operation-specific durable identity and one-Run dual-adapter regression gate."""
from dataclasses import replace
import json
import sqlite3
from types import SimpleNamespace
from urllib.parse import unquote

import pytest

from pro_a.cloud_contract import (
    ADAPTER_VERSION, SOURCE_ANALYSIS_ADAPTER_VERSION, OPERATION_KIND,
    SOURCE_ANALYSIS_OPERATION, CloudContractError, DeterministicFakeProvider,
    adapter_version_for_operation, operation_contract, digest,
)
from pro_a.config import LLMConfig, load_config
from pro_a.semantic_decomposition import SEMANTIC_DECOMPOSITION_USER
from pro_a.workbench.cloud_jobs import CloudProfile, JobError
from pro_a.workbench.extraction_retry import frozen_cloud, prepare_extraction_retries
from pro_a.workbench.source_operations import (
    SourceOperations, SourceOperationError, build_source_providers,
)
from test_phase43_stage71_shared_core_pending import case
from test_workbench_stage7 import TEXT, clean_pdf, upload
from pro_a.output_decomposition import OPERATION as WHOLE_PIECE_OPERATION
from pro_a.output_decomposition import PROVIDER_VERSION as WHOLE_PIECE_ADAPTER_VERSION
from series_binding_helpers import prepare_bounded, request_parts, response_content, rows as ledger_rows


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External network is forbidden in qualification")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def setup_run(tmp_path, monkeypatch):
    value = case(tmp_path)
    prepare_bounded(value)
    config_path = value["phase4_config"]
    config_path.write_text(config_path.read_text(encoding="utf-8").replace(
        'enabled = false\nmodel = "fake-semantic-v1"',
        'enabled = true\nmodel = "deepseek-flash"'), encoding="utf-8")
    profile = CloudProfile("deepseek", "deepseek-flash")
    value["cloud_profile"] = profile
    service = SourceOperations(value["config"], value["source_profile"], profile)
    value["service"] = service
    value["production_before"] = value["config"].knowledge_db.read_bytes()
    value["production_writes"] = []
    value["guarded_production_connections"] = 0
    connect = sqlite3.connect
    def guarded_connect(database, *args, **kwargs):
        connection = connect(database, *args, **kwargs)
        if value["config"].knowledge_db.as_posix().casefold() in unquote(str(database)).replace("\\", "/").casefold():
            value["guarded_production_connections"] += 1
            def authorize(action, *unused):
                if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                              sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE):
                    value["production_writes"].append(action)
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            connection.set_authorizer(authorize)
        return connection
    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
    source = upload(value, clean_pdf(tmp_path))
    run = service.start(source["source_id"], idempotency_key="dual-adapter-synthetic-0001")["run"]
    value.update(source=source, run_id=run["processing_run_id"],
                 providers=build_source_providers(load_config(config_path).llm, profile))
    value["http_calls"] = []
    monkeypatch.setenv("PROA_LLM_API_KEY", "synthetic-transport-only")

    def post(_url, **kwargs):
        payload = kwargs["json"]
        value["http_calls"].append({"model": payload["model"], "system": payload["messages"][0]["content"]})
        assert payload["model"] == "deepseek-flash"
        user = payload["messages"][1]["content"]
        prefix, suffix = SEMANTIC_DECOMPOSITION_USER.split("{claims_json}")
        if user.startswith(prefix):
            claims = json.loads(user[len(prefix):len(user) - len(suffix) if suffix else None])
            output = {"claims": [{
                "parent_claim_id": claim["parent_claim_id"], "ir_status": "VALID",
                "units": [{
                    "predicate_family": "measurement", "modality": "actual",
                    "nature": claim["assigned_nature"] or "fact",
                    "support_evidence_unit_ids": [claim["evidence_units"][0]["evidence_unit_id"]],
                    "coherence_key": "k1", "coherence_type": "INDEPENDENT",
                    "time_scope": "unspecified",
                }],
            } for claim in claims]}
        else:
            target,source_text=request_parts(payload)
            import re
            target['assigned_evidence_refs'] = re.findall(r'\[(EV_[^\]]+)\]', source_text)
            output=json.loads(response_content(target,source_text))
            from lexical_record_helpers import from_wire
            from series_binding_helpers import ToolResponse
            from series_binding_helpers import batch_record
            return ToolResponse(json.dumps(batch_record(output, target)))
        return SimpleNamespace(status_code=200, text="", headers={"x-request-id": "offline-dual"},
            json=lambda: {"id": "offline-dual", "model": "deepseek-flash",
                          "choices": [{"finish_reason": "stop", "message": {
                              "content": json.dumps(output)}}],
                          "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}})
    monkeypatch.setattr("pro_a.llm.requests.post", post)
    advance(value)
    return value


def advance(value, providers=None):
    return value["service"].advance_once(
        worker_id="dual-adapter-worker", processing_run_id=value["run_id"],
        provider=value["providers"] if providers is None else providers)


def jobs(value):
    with value["service"].store.connect() as c:
        return [dict(row) for row in c.execute(
            "SELECT j.* FROM cloud_jobs j JOIN source_processing_jobs s ON s.job_id=j.job_id "
            "WHERE s.processing_run_id=? ORDER BY operation_kind", (value["run_id"],))]


def test_single_run_dual_real_adapters_to_review_packet(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    assert len(jobs(value)) == 0
    assert value['providers'][WHOLE_PIECE_OPERATION].adapter_version==WHOLE_PIECE_ADAPTER_VERSION
    assert advance(value)["state"] == "SEMANTIC_PROCESSING"
    final = advance(value)
    assert final["state"] == "HUMAN_REVIEW_REQUIRED" and final["packet_artifact_id"]
    assert final["processing_scope_mode"] == "SHARED_CORE"
    assert final["domain_assignment_status"] == "PENDING"
    rows = jobs(value)
    assert len(rows) == 1 and len(value["http_calls"]) == 2
    assert len({call["system"] for call in value["http_calls"]}) == 2
    for row in rows:
        contract = operation_contract(row["operation_kind"])
        assert row["provider_adapter_version"] == adapter_version_for_operation(row["operation_kind"])
        assert json.loads(row["prompt_json"]) == contract
        assert row["prompt_sha256"] == contract["prompt_bundle_sha256"]
        assert row["provider"] == "deepseek" and row["requested_model"] == "deepseek-flash"
        assert row["state"] == "SUCCEEDED" and row["sanitized_error"] is None
        assert row["validation_status"] == "PASS"
        assert json.loads(row["configuration_json"]) == value["cloud_profile"].public_identity()
    assert len(ledger_rows(value,'bounded_extraction_series')) == 1
    assert len(ledger_rows(value,'bounded_extraction_attempts')) == 1
    with value["service"].store.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM source_processing_runs").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM registered_packets WHERE artifact_kind='REVIEW_PACKET'").fetchone()[0] == 1
    assert value["config"].knowledge_db.read_bytes() == value["production_before"]
    assert value["production_writes"] == []
    assert value["guarded_production_connections"] > 0
    for artifact in value["config"].artifact_root.rglob("*.json"):
        assert "synthetic-transport-only" not in artifact.read_text(encoding="utf-8")


@pytest.mark.parametrize("operation", [WHOLE_PIECE_OPERATION, OPERATION_KIND])
@pytest.mark.parametrize("mismatch", ["other_adapter", "unknown_adapter", "provider"])
def test_wrong_adapter_or_provider_rejected_before_invoke(tmp_path, monkeypatch, operation, mismatch):
    value = setup_run(tmp_path, monkeypatch)
    if operation == OPERATION_KIND:
        assert advance(value)["state"] == "SEMANTIC_PROCESSING"
    selected = value["providers"][operation]
    if mismatch == "other_adapter":
        selected = value["providers"][OPERATION_KIND if operation == WHOLE_PIECE_OPERATION else WHOLE_PIECE_OPERATION]
    elif mismatch == "unknown_adapter":
        monkeypatch.setattr(selected, "adapter_version", "unknown-adapter")
    else:
        monkeypatch.setattr(selected, "provider_identity", "other-provider")
    def forbidden(_request):
        pytest.fail("Provider invoke must not occur")
    monkeypatch.setattr(selected, "invoke", forbidden)
    before = len(value["http_calls"])
    result = advance(value, {operation: selected})
    assert result["state"] == "BLOCKED"
    assert result["error"]["code"] == ("BOUNDED_EXTRACTION_FAILED" if operation == WHOLE_PIECE_OPERATION else "PROVIDER_CONTRACT_MISMATCH")
    assert len(value["http_calls"]) == before
    assert not ledger_rows(value,'bounded_extraction_attempts') if operation == WHOLE_PIECE_OPERATION else next(j for j in jobs(value) if j['operation_kind'] == operation)['attempt_count'] == 0


def test_missing_route_has_no_fallback(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    result = advance(value, {OPERATION_KIND: value["providers"][OPERATION_KIND]})
    assert result["error"]["code"] == "BOUNDED_EXTRACTION_FAILED"
    assert not value["http_calls"]


def test_environment_mapping_and_no_network_construction(monkeypatch):
    monkeypatch.setenv("PRO_A_CLOUD_PROVIDER", "deepseek")
    monkeypatch.setenv("PRO_A_CLOUD_MODEL", "deepseek-flash")
    monkeypatch.delenv("PROA_LLM_API_KEY", raising=False)
    profile = CloudProfile.from_environment()
    assert (profile.provider, profile.requested_model) == ("deepseek", "deepseek-flash")
    config = LLMConfig(enabled=True, model="deepseek-flash", max_retries=2)
    providers = build_source_providers(config, profile)
    assert profile.accepted_model_aliases == () and config.max_retries == 2
    for operation, provider in providers.items():
        assert provider.provider_identity == "deepseek"
        assert provider.adapter_version == (WHOLE_PIECE_ADAPTER_VERSION if operation==WHOLE_PIECE_OPERATION else adapter_version_for_operation(operation))
        cfg=provider.cfg if operation==WHOLE_PIECE_OPERATION else provider.backend.llm.cfg
        assert cfg.model == profile.requested_model
        assert cfg.max_retries == 0
        assert cfg.max_output_tokens == (24000 if operation == WHOLE_PIECE_OPERATION else 8192)
    assert profile.public_identity() == profile.public_identity()
    assert "api_key" not in json.dumps(profile.public_identity())
    with pytest.raises(CloudContractError, match="UNSUPPORTED_CLOUD_OPERATION"):
        adapter_version_for_operation("UNKNOWN")
    with pytest.raises(JobError, match="CLOUD_PROFILE_INVALID"):
        replace(profile, provider_adapter_version="unknown").validate()


@pytest.mark.parametrize("change", [
    {"enabled": False}, {"model": "other-model"}, {"base_url": "https://other.example"},
    {"base_url": "https://user:password@api.deepseek.com"}, {"api_key_env": "OTHER_KEY"},
])
def test_operator_constructor_rejects_incompatible_config(change):
    config = replace(LLMConfig(enabled=True, model="deepseek-flash"), **change)
    with pytest.raises(SourceOperationError, match="PROVIDER_CONFIGURATION_MISMATCH"):
        build_source_providers(config, CloudProfile("deepseek", "deepseek-flash"))


def test_unknown_operation_and_deterministic_durable_identity(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    service = value["service"]
    assert advance(value)['state']=='SEMANTIC_PROCESSING'
    row = jobs(value)[0]
    with pytest.raises(CloudContractError, match="UNSUPPORTED_CLOUD_OPERATION"):
        service.jobs.submit(idempotency_key="unknown-operation-0001", input_artifact_id=row["input_artifact_id"], operation_kind="UNKNOWN")
    duplicate = service.jobs.submit(idempotency_key="repeat-same-intent-0001", input_artifact_id=row["input_artifact_id"], operation_kind=row["operation_kind"])
    with service.store.connect() as c:
        repeated = c.execute("SELECT intent_sha256 FROM cloud_jobs WHERE job_id=?",
                             (duplicate["job"]["job_id"],)).fetchone()[0]
    assert repeated == row["intent_sha256"]
    assert duplicate["job"]["runtime_identity"] == json.loads(row["runtime_json"])
    assert service.jobs.current_runtime() == service.jobs.current_runtime()
    operation = operation_contract(SOURCE_ANALYSIS_OPERATION)
    assert digest(operation) != digest({**operation, "provider_adapter_version": "different"})


@pytest.mark.parametrize("change", ["frozen_adapter", "frozen_model", "profile_model", "runtime"])
def test_frozen_identity_drift_fails_closed(tmp_path, monkeypatch, change):
    value = setup_run(tmp_path, monkeypatch)
    service = value["service"]
    assert advance(value)['state']=='SEMANTIC_PROCESSING'
    row = jobs(value)[0]
    if change in ("frozen_adapter", "frozen_model"):
        column, changed = ("provider_adapter_version", SOURCE_ANALYSIS_ADAPTER_VERSION) if change == "frozen_adapter" else ("requested_model", "other-model")
        with service.store.connect(operator_write=True) as c:
            c.execute(f"UPDATE cloud_jobs SET {column}=? WHERE job_id=?", (changed, row["job_id"]))
    elif change == "profile_model":
        service.jobs.profile = replace(service.jobs.profile, requested_model="other-model")
    else:
        runtime = service.jobs.current_runtime()
        runtime["cloud_contract_version"] = "drift"
        runtime["runtime_sha256"] = digest({k: v for k, v in runtime.items() if k != "runtime_sha256"})
        service.jobs._runtime_override = runtime
    before = len(value["http_calls"])
    result = advance(value)
    assert result["state"] in ("BLOCKED", "FAILED")
    assert len(value["http_calls"]) == before


def test_retry_copies_operation_adapter_and_rejects_current_substitution(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    prepare_extraction_retries(value["config"])
    service = value["service"]
    provider = value["providers"][WHOLE_PIECE_OPERATION]
    from pro_a.cloud_contract import ProviderFailure
    failed_requests = []
    def fail(request):
        failed_requests.append(request)
        from pro_a.bounded_source_analysis import RawSegmentResponse
        return RawSegmentResponse(b'', 503, finish_reason='error')
    monkeypatch.setattr(provider, "invoke", fail)
    result = advance(value)
    assert result["state"] == "BLOCKED"
    original=ledger_rows(value,'bounded_extraction_attempts')
    with pytest.raises(SourceOperationError,match='RETRY_NOT_ELIGIBLE'):
        service.retry_failed_extraction(value['run_id'],original[0]['attempt_id'],
            retry_reason='Explicit synthetic retry',idempotency_key='operation-adapter-retry-0001')
    assert ledger_rows(value,'bounded_extraction_attempts') == original and len(jobs(value)) == 0
    new=service.start(value['source']['source_id'],idempotency_key='operation-adapter-reprocess-0001',reprocess_reason='Explicit synthetic reprocess')['run']
    value['run_id']=new['processing_run_id']
    advance(value)
    wrong = {WHOLE_PIECE_OPERATION: value["providers"][OPERATION_KIND]}
    result = advance(value, wrong)
    assert result["error"]["code"] == "BOUNDED_EXTRACTION_FAILED"
    assert len(failed_requests) == 1
    assert not value["http_calls"]


@pytest.mark.parametrize("operation,wrong", [
    (SOURCE_ANALYSIS_OPERATION, ADAPTER_VERSION),
    (OPERATION_KIND, SOURCE_ANALYSIS_ADAPTER_VERSION),
])
def test_historical_bad_frozen_adapter_cannot_be_reconstructed(tmp_path, monkeypatch, operation, wrong):
    if operation==SOURCE_ANALYSIS_OPERATION:
        from legacy_source_fixture import historical_case
        value=historical_case(tmp_path)
    else:
        value=setup_run(tmp_path,monkeypatch)
        advance(value)
    row = next(row for row in jobs(value) if row["operation_kind"] == operation)
    historical = {**row, "provider_adapter_version": wrong}
    with pytest.raises(SourceOperationError, match="RETRY_FROZEN_CONFIG_INCOMPLETE"):
        frozen_cloud(historical)
    assert historical["provider_adapter_version"] == wrong


def test_required_adapter_change_changes_new_identity(tmp_path, monkeypatch):
    import pro_a.cloud_contract as contract
    from pro_a.workbench.cloud_jobs import runtime_identity
    value = setup_run(tmp_path, monkeypatch)
    service = value["service"]
    old=service.get_run(value['run_id'])
    old_inputs=ledger_rows(value,'source_cloud_inputs')
    import pro_a.output_decomposition as whole
    monkeypatch.setattr(whole, "PROVIDER_VERSION", "whole-piece-provider-future")
    runtime_identity.cache_clear()
    try:
        assert advance(value)['error']['code']=='HISTORICAL_EXTRACTION_RUNTIME_INCOMPATIBLE'
        new=service.start(value['source']['source_id'],idempotency_key='changed-operation-identity-0001',reprocess_reason='Explicit changed bounded contract')['run']
        assert new['runtime_identity']['whole_piece_output_decomposition']['adapter_version']=='whole-piece-provider-future'
        assert new['runtime_identity']['runtime_sha256']!=old['runtime_identity']['runtime_sha256']
        assert ledger_rows(value,'source_cloud_inputs')==old_inputs and not value['http_calls']
        assert operation_contract(SOURCE_ANALYSIS_OPERATION)['provider_adapter_version']==SOURCE_ANALYSIS_ADAPTER_VERSION
    finally:
        runtime_identity.cache_clear()


def test_compatibility_token_does_not_bypass_adapter_check(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    service = value["service"]
    service.jobs.runtime_compatibility = object()
    monkeypatch.setattr(value['providers'][WHOLE_PIECE_OPERATION],'adapter_version',ADAPTER_VERSION)
    result=advance(value)
    assert result['error']['code']=='BOUNDED_EXTRACTION_FAILED'
    assert not ledger_rows(value,'bounded_extraction_attempts') and not value['http_calls']
