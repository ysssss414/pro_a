from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
import requests

from pro_a import phase4_orchestration as orchestration
from pro_a.config import LLMConfig
from pro_a.llm import LLMError
from pro_a.operational_ingestion import run_operational_ingestion
from pro_a.phase3f_review_completion import build_blank_review_packet, validate_blank_review_packet
from pro_a.phase4_replay import FrozenSemanticReplay, frozen_replay_inputs, read_json
from pro_a.phase4_retry import ExecutionLLM, RetryPolicy
from pro_a.production_promotion import production_identity, sha256_file
from pro_a.semantic_decomposition import ChatLLMSemanticBackend, SemanticDecomposer
from stability_helpers import make_config
from test_llm import FakeResponse, completion
from test_proposition_ir import FakeBackend, _semantic_inputs


ROOT = Path(__file__).resolve().parents[1]
FROZEN_RUN = ROOT / "workspace/phase3e2sl6/operational_run"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Gate A must not make a network request")
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)


@pytest.fixture
def setup(tmp_path):
    cfg, _ = make_config(tmp_path)
    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"%PDF-1.4 synthetic source-registration fixture")
    return cfg, source


def start(setup, **kwargs):
    cfg, source = setup
    return orchestration.start_execution(source, config_path=cfg.config_path,
                                         stop_after="SOURCE_READY", **kwargs)


def resume(result, cfg, **kwargs):
    return orchestration.resume_execution(
        Path(result["execution_root"]), execution_id=result["execution_id"],
        config_path=cfg.config_path, stop_after="SOURCE_READY", **kwargs,
    )


def test_distinct_outer_ids_preserve_native_identity(setup):
    first, second = start(setup), start(setup)
    assert first["state"] == second["state"] == "SOURCE_READY"
    assert first["execution_id"] != second["execution_id"]
    identities = [read_json(Path(r["execution_root"]) / "execution_identity.json") for r in (first, second)]
    assert identities[0]["legacy_ingestion_run_id"] == identities[1]["legacy_ingestion_run_id"]
    assert identities[0]["source_id"] == identities[1]["source_id"]
    assert len({identities[0]["execution_id"], identities[0]["source_id"], identities[0]["legacy_ingestion_run_id"]}) == 3
    root = Path(first["execution_root"])
    created = read_json(root / "commits/000000.json")
    assert created["state"] == "CREATED" and not created["inventory"]
    assert resume(first, setup[0])["state"] == "SOURCE_READY"


def test_resume_after_original_removed_reuses_frozen_source(setup):
    result = start(setup)
    root = Path(result["execution_root"])
    before = (root / "execution_identity.json").read_bytes()
    setup[1].unlink()
    assert resume(result, setup[0])["state"] == "SOURCE_READY"
    assert (root / "execution_identity.json").read_bytes() == before


@pytest.mark.parametrize("content", [None, "{incomplete", "[]"])
def test_missing_or_interrupted_manifest_is_typed_block(setup, content):
    result = start(setup)
    manifest = Path(result["manifest"])
    if content is None:
        manifest.unlink()
    else:
        manifest.write_text(content)
    assert resume(result, setup[0])["state"] == "BLOCKED"
    assert (not manifest.exists()) if content is None else manifest.read_text() == content


@pytest.mark.parametrize("field", ["execution_id", "source_id", "source_sha256", "created_at"])
def test_identity_edits_never_repair_old_manifest(setup, field):
    result = start(setup)
    root = Path(result["execution_root"])
    manifest_before = (root / "execution_manifest.json").read_bytes()
    identity = read_json(root / "execution_identity.json")
    identity[field] = "CHANGED"
    (root / "execution_identity.json").write_text(json.dumps(identity), encoding="utf-8")
    blocked = resume(result, setup[0])
    assert blocked["state"] == "BLOCKED" and "IDENTITY" in blocked["code"]
    assert (root / "execution_manifest.json").read_bytes() == manifest_before


@pytest.mark.parametrize("setting", ['model = "changed"', 'max_chunk_chars = 9000',
                                    'temperature = 0.9', 'base_url = "https://invalid.example"'])
def test_material_configuration_drift_blocks(setup, setting):
    result = start(setup)
    cfg = setup[0]
    original = cfg.config_path.read_text(encoding="utf-8")
    cfg.config_path.write_text(original.replace("[llm]\n", "[llm]\n" + setting + "\n"), encoding="utf-8")
    blocked = resume(result, cfg)
    assert blocked["code"] == "PROCESSING_PROVIDER_OR_RETRY_CONFIG_DRIFT"


@pytest.mark.parametrize("field", ["repository_commit", "contract_version", "processing_code_sha256", "packages"])
def test_code_and_runtime_drift_blocks(setup, monkeypatch, field):
    result = start(setup)
    original = orchestration._runtime()
    monkeypatch.setattr(orchestration, "_runtime", lambda: {**original, field: "CHANGED"})
    assert resume(result, setup[0])["code"] == "CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE"


def test_retry_policy_serialization_and_drift(setup):
    for policy in RetryPolicy:
        result = start(setup, retry_policy=policy)
        identity = read_json(Path(result["execution_root"]) / "execution_identity.json")
        assert RetryPolicy(identity["configuration"]["retry_policy"]) is policy
        assert identity["configuration"]["semantic_max_split_depth"] == 0
        assert identity["configuration"]["adaptive_extraction_retry"] == "forbid"
        assert resume(result, setup[0], retry_policy=policy)["state"] == "SOURCE_READY"
        other = RetryPolicy.FORBID_SEMANTIC if policy is RetryPolicy.FORBID_ALL else RetryPolicy.FORBID_ALL
        assert resume(result, setup[0], retry_policy=other)["state"] == "BLOCKED"


@pytest.mark.parametrize("change", ["missing", "extra", "tamper"])
def test_artifact_inventory_blocks_before_engine_dispatch(setup, monkeypatch, change):
    result = start(setup)
    root = Path(result["execution_root"])
    frozen = next((root / "engine/source").iterdir())
    if change == "missing":
        frozen.unlink()
    elif change == "extra":
        (root / "engine/incomplete.tmp").write_text("incomplete")
    else:
        frozen.write_bytes(b"changed")
    monkeypatch.setattr(orchestration, "run_operational_ingestion", lambda **kw: pytest.fail("must block first"))
    assert resume(result, setup[0])["code"] == "ARTIFACT_INVENTORY_MISMATCH"


def test_interrupted_stage_never_appears_committed(setup, monkeypatch):
    result = start(setup)
    root = Path(result["execution_root"])
    def interrupted(**kwargs):
        (root / "engine/extraction/partial.json").write_text("{")
        raise KeyboardInterrupt()
    monkeypatch.setattr(orchestration, "run_operational_ingestion", interrupted)
    with pytest.raises(KeyboardInterrupt):
        orchestration.resume_execution(root, execution_id=result["execution_id"], config_path=setup[0].config_path)
    manifest = read_json(root / "execution_manifest.json")
    assert manifest["state"] == "PROCESSING"
    assert manifest["last_successful_state"] == "SOURCE_READY"
    assert resume(result, setup[0])["code"] == "ARTIFACT_INVENTORY_MISMATCH"


def test_commit_published_before_pointer_interruption_blocks(setup, monkeypatch):
    result = start(setup)
    root = Path(result["execution_root"])
    publish = orchestration._publish
    def interrupted(path, data):
        if path.name == "execution_manifest.json":
            raise KeyboardInterrupt()
        publish(path, data)
    monkeypatch.setattr(orchestration, "_publish", interrupted)
    with pytest.raises(KeyboardInterrupt):
        orchestration.resume_execution(root, execution_id=result["execution_id"], config_path=setup[0].config_path)
    assert resume(result, setup[0])["code"] == "UNRECONCILED_STAGE_PUBLICATION"


@pytest.mark.parametrize("claims,nodes,relations,code", [
    ([], [], [], "BLOCKED_EMPTY_CANDIDATE_SET"),
    ([{"claim_id": "CLM_X"}], [], [], "BLOCKED_EMPTY_CANDIDATE_SET"),
    ([], [{"operation_candidate_id": "CAND_X"}], [], "BLOCKED_EMPTY_CANDIDATE_SET"),
    ([], [], [{"relation_type": "supplies"}], "UNSUPPORTED_PACKET_CAPABILITY"),
])
def test_empty_or_relation_only_packet_is_explicit(tmp_path, claims, nodes, relations, code):
    native = tmp_path / "engine"
    (native / "review").mkdir(parents=True)
    (native / "promotion").mkdir()
    for name, data in {"review/claim_review.json": {"claims": claims},
                       "review/node_operation_review.json": {"records": nodes},
                       "promotion/promotion_preview.json": {"relations": {"observations": relations}}}.items():
        (native / name).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(orchestration.ExecutionBlocked, match=code):
        orchestration._review(tmp_path)
    assert not (tmp_path / "review").exists()


@pytest.mark.parametrize("policy", list(RetryPolicy))
@pytest.mark.parametrize("failure", [429, 503, "timeout"])
def test_transport_attempt_ownership_and_forbid_all(monkeypatch, policy, failure):
    monkeypatch.setenv("PHASE4_TEST_KEY", "synthetic")
    requests_made, events = [], []
    def post(*args, **kwargs):
        requests_made.append(kwargs["json"])
        if len(requests_made) == 1:
            if failure == "timeout":
                raise requests.exceptions.Timeout("synthetic timeout")
            return FakeResponse({}, status_code=failure)
        return FakeResponse(completion('{"ok":true}'))
    monkeypatch.setattr("pro_a.llm.requests.post", post)
    client = ExecutionLLM(LLMConfig(enabled=True, api_key_env="PHASE4_TEST_KEY", max_retries=1,
                                    retry_backoff_seconds=0), policy=policy, emit=events.append)
    if policy is RetryPolicy.FORBID_ALL:
        with pytest.raises(LLMError):
            client.json("fixed system", "fixed input")
        assert len(requests_made) == 1
        assert not any(e["event"] == "RETRY_AUTHORIZED" for e in events)
    else:
        assert client.json("fixed system", "fixed input") == {"ok": True}
        assert requests_made[0] == requests_made[1]
        assert [e["policy"] for e in events if e["event"] == "RETRY_AUTHORIZED"] == [policy.value]
    assert all(e.get("result_replacement", False) is False for e in events)


def test_no_semantic_split_with_forbidden_policy_and_legacy_default_unchanged():
    backend = FakeBackend(truncate_above=1)
    with pytest.raises(Exception, match="SEMANTIC_BACKEND_FAILURE"):
        SemanticDecomposer(backend, max_split_depth=0).run(_semantic_inputs(2))
    assert len(backend.calls) == 1
    legacy = FakeBackend(truncate_above=1)
    SemanticDecomposer(legacy).run(_semantic_inputs(2))
    assert len(legacy.calls) == 3


@pytest.mark.parametrize("finish_reason", ["length", "stop"])
def test_forbidden_http_semantic_failure_has_one_attempt(monkeypatch, finish_reason):
    monkeypatch.setenv("PHASE4_TEST_KEY", "synthetic")
    calls, events = [], []
    def post(*args, **kwargs):
        calls.append(kwargs)
        return FakeResponse(completion("malformed JSON", finish_reason=finish_reason))
    monkeypatch.setattr("pro_a.llm.requests.post", post)
    client = ExecutionLLM(LLMConfig(enabled=True, api_key_env="PHASE4_TEST_KEY", max_retries=9),
                          policy=RetryPolicy.FORBID_ALL, emit=events.append)
    with pytest.raises(Exception, match="SEMANTIC_BACKEND_FAILURE"):
        SemanticDecomposer(ChatLLMSemanticBackend(client), max_split_depth=0).run(_semantic_inputs(2))
    assert len(calls) == 1
    assert not any(e["event"] == "RETRY_AUTHORIZED" for e in events)


def test_frozen_replay_requires_exact_inputs_and_single_consumption():
    inputs = _semantic_inputs(2)
    result = SemanticDecomposer(FakeBackend()).run(inputs)
    capture = {"inputs": inputs, "result": result, "origin_manifest_sha256": "a" * 64}
    replay = FrozenSemanticReplay(capture, lambda e: None)
    changed = copy.deepcopy(inputs)
    changed[0]["claim_text"] += " changed"
    with pytest.raises(ValueError, match="INPUT_MISMATCH"):
        replay(changed)
    assert replay(inputs) == result
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        replay(inputs)


@pytest.mark.skipif(not (FROZEN_RUN / "run_manifest.json").exists(), reason="private frozen workflow unavailable")
def test_full_frozen_engine_replay_equivalence_and_zero_production_writes(tmp_path, monkeypatch):
    cfg, _ = make_config(tmp_path)
    monkeypatch.setenv("PHASE4_TEST_KEY", "synthetic")
    cfg.config_path.write_text(cfg.config_path.read_text(encoding="utf-8").replace(
        "[llm]\nenabled = false", '[llm]\nenabled = true\napi_key_env = "PHASE4_TEST_KEY"'), encoding="utf-8")
    production = ROOT / "workspace/pro_a.db"
    before = production_identity(production)
    shutil.copyfile(production, cfg.db_path)
    isolated_before = sha256_file(cfg.db_path)
    frozen = read_json(FROZEN_RUN / "run_manifest.json")
    source = FROZEN_RUN / frozen["source"]["frozen_relative_path"]
    capture = frozen_replay_inputs(FROZEN_RUN)
    import sqlite3
    original_connect = sqlite3.connect
    connections = []
    def readonly_connect(database, *args, **kwargs):
        connections.append(str(database))
        assert "mode=ro" in str(database), "No writable DB connection allowed during replay"
        return original_connect(database, *args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", readonly_connect)
    dispatched = []
    def native_call(*args, **kwargs):
        dispatched.append(kwargs)
        return run_operational_ingestion(*args, **kwargs)
    monkeypatch.setattr(orchestration, "run_operational_ingestion", native_call)
    result = orchestration.start_execution(source, config_path=cfg.config_path, replay_run=FROZEN_RUN)
    assert result["state"] == "STOPPED", result
    assert result["code"] == "HUMAN_REVIEW_REQUIRED"
    root = Path(result["execution_root"])
    native = root / "engine"
    direct = cfg.root / "direct_replay"
    run_operational_ingestion(
        source, config_path=cfg.config_path, run_dir=direct,
        frozen_extraction_path=FROZEN_RUN / "extraction/extraction_bundle.json",
        semantic_replay=FrozenSemanticReplay(capture, lambda e: None),
        adaptive_retry_policy="forbid", semantic_max_split_depth=0,
        llm_factory=lambda c: ExecutionLLM(c, policy=RetryPolicy.FORBID_ALL, emit=lambda e: None, offline=True),
    )
    # Native semantic artifacts are compared in their entirety: no dropped
    # admission reasons, evidence, ordering or content fields.
    compared = []
    for name in ("extraction/extraction_bundle.json", "evidence/evidence_bound_extraction_bundle.json",
                 "evidence/evidence_binding.json", "evidence/quote_fidelity.json",
                 "evidence/table_claim_safety.json", "evidence/semantic_decomposition.json",
                 "evidence/semantic_admission.json"):
        assert read_json(native / name) == read_json(direct / name), name
        compared.append(name)
    assert read_json(native / "evidence/semantic_decomposition.json") == capture["result"]
    for name, field in (("review/claim_review.json", "claims"), ("review/node_operation_review.json", "records")):
        assert read_json(native / name)[field] == read_json(direct / name)[field]
        compared.append(name + ":" + field)
    packet = read_json(root / "review/packet.json")
    validate_blank_review_packet(packet, native)
    direct_packet = build_blank_review_packet(direct)
    for group in ("claims", "nodes", "aliases", "relations"):
        def content(rows):
            return [{key: value for key, value in row.items() if key != "provenance"} for row in rows]
        assert content(packet[group]) == content(direct_packet[group]), group
    assert packet["excluded_relation_inventory"] == direct_packet["excluded_relation_inventory"]
    assert packet["safety"]["production_apply_authorized"] is False
    assert result["excluded_relation_count"] > 0
    assert all(row["human_input"]["decision"] == "" for row in packet["claims"])
    before_resume = orchestration._inventory(root)
    resumed = orchestration.resume_execution(root, execution_id=result["execution_id"], config_path=cfg.config_path)
    assert resumed == result and orchestration._inventory(root) == before_resume
    events = [read_json(path) for path in (root / "attempts").glob("*.json")]
    assert [e["event"] for e in events] == ["FROZEN_SEMANTIC_RESULT_CONSUMED"]
    assert dispatched and all(call["semantic_max_split_depth"] == 0 for call in dispatched)
    assert all(call["adaptive_retry_policy"] == "forbid" for call in dispatched)
    assert connections and all("mode=ro" in path for path in connections)
    assert sha256_file(cfg.db_path) == isolated_before
    assert production_identity(production) == before
    evidence = {"status": "PASS", "execution_id": result["execution_id"],
                "comparison": "native direct replay versus outer adapter",
                "compared": compared, "parent_claims": len(capture["inputs"]),
                "review_summary": packet["summary"], "network_calls": 0,
                "production_write_count": 0, "production_sha256": before["sha256"],
                "orchestration_only_differences": ["execution_id", "timestamps", "local_paths", "receipts"],
                "frozen_result_sha256": sha256_file(FROZEN_RUN / "evidence/semantic_decomposition.json")}
    (tmp_path / "gate_a_replay_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
