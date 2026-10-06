"""One explicit same-Batch retry for durable provider JSON syntax failures."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json as json_module

import pytest

from pro_a.cloud_contract import digest
from pro_a.workbench import bounded_extraction_persistence as persistence
from pro_a.workbench.retry_compatibility import assess_bounded_retry_compatibility
from pro_a.workbench.source_operations import SourceOperationError
from test_cloud_operation_adapter_binding import advance, setup_run
from series_binding_helpers import (
    ToolResponse, Transport, batch_record, request_parts, response_content, rows,
    synthetic_providers,
)


def _attempts(value):
    return sorted(rows(value, "bounded_extraction_attempts"), key=lambda row: row["attempt_number"])


def _malformed_failure(value, providers):
    result = advance(value, providers)
    assert result["state"] == "BLOCKED"
    assert result["error"]["code"] == "BOUNDED_EXTRACTION_FAILED"
    attempts = _attempts(value)
    assert len(attempts) == 1
    return attempts[0]


def _retry(value, attempt, *, key="malformed-json-retry-0001", reason="Explicit malformed JSON retry"):
    return value["service"].retry_failed_extraction(
        value["run_id"], attempt["attempt_id"],
        retry_reason=reason, idempotency_key=key,
    )


def test_malformed_then_valid_reuses_run_series_segment_and_request(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    transport = Transport(mode=lambda _target, call: "malformed" if call == 1 else None)
    with synthetic_providers(value, transport) as providers:
        first = _malformed_failure(value, providers)
        raw_path = next(value["config"].artifact_root.rglob(first["attempt_id"] + ".raw.json"))
        raw_before = raw_path.read_bytes()
        original = dict(first)
        original_outcome = next(row for row in rows(value, "bounded_extraction_outcomes")
                                if row["attempt_id"] == first["attempt_id"])
        original_failures = [row for row in rows(value, "bounded_extraction_events")
                             if row["event_type"] == "SEGMENT_FAILED"]

        created = _retry(value, first)
        duplicate = _retry(value, first)
        assert created["duplicate"] is False and duplicate["duplicate"] is True
        assert duplicate["attempt"]["attempt_id"] == created["attempt"]["attempt_id"]
        assert created["retry"]["retry_reason_code"] == "MALFORMED_PROVIDER_JSON"
        assert created["retry"]["retry_number"] == 1
        assert created["retry"]["retry_of_attempt_id"] == first["attempt_id"]

        second = _attempts(value)[1]
        assert second["attempt_number"] == 2
        assert second["segment_id"] == first["segment_id"]
        for field in ("request_json", "request_sha256", "configuration_sha256", "budget_identity"):
            assert second[field] == first[field]
        assert value["service"].get_run(value["run_id"])["processing_run_id"] == value["run_id"]

        assert value["service"].output_batches.advance(
            value["service"].get_run(value["run_id"]), providers, "retry-worker",
        ) is True
        assert len(transport.calls) == 2

    assert raw_path.read_bytes() == raw_before
    assert _attempts(value)[0] == original
    assert next(row for row in rows(value, "bounded_extraction_outcomes")
                if row["attempt_id"] == first["attempt_id"]) == original_outcome
    assert [row for row in rows(value, "bounded_extraction_events")
            if row["event_type"] == "SEGMENT_FAILED"] == original_failures
    accepted = rows(value, "bounded_extraction_segment_results")
    assert len(accepted) == 1 and accepted[0]["attempt_id"] == second["attempt_id"]
    binding = value["service"].output_batches.inputs(
        value["service"].get_run(value["run_id"]),
    )[0]
    _, context, catalog, series = binding
    ledger = value["service"].output_batches.ledger
    _, plan, series_row, accounting = ledger.read(series.series_id)
    segment = next(item for item in plan.segments if item.segment_id == second["segment_id"])
    outcome = next(row for row in rows(value, "bounded_extraction_outcomes")
                   if row["attempt_id"] == second["attempt_id"])
    _, body = ledger._decode_envelope(
        second, ledger._read_artifact(series.series_id, second["attempt_id"] + ".raw.json", outcome),
    )
    from pro_a.output_decomposition import record_to_result
    expected = record_to_result(body.decode("utf-8"), series, segment, catalog, context)
    actual = ledger._result(series.series_id, accepted[0])
    assert actual == expected
    assert accounting.provider_call_count == 2 and series_row["frontier_version"] == 0
    assert len(plan.segments) == 1
    assert len(rows(value, "source_processing_runs")) == 1
    assert len(rows(value, "source_processing_jobs")) == 0
    assert not [row for row in rows(value, "registered_packets")
                if row["artifact_kind"] == "REVIEW_PACKET"]
    assert value["config"].knowledge_db.read_bytes() == value["production_before"]
    with pytest.raises(SourceOperationError, match="RETRY_LIMIT_EXCEEDED"):
        _retry(value, first, key="malformed-json-retry-0002")
    assert len(_attempts(value)) == 2


def test_malformed_twice_is_terminal_without_third_call(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    transport = Transport(mode="malformed")
    with synthetic_providers(value, transport) as providers:
        first = _malformed_failure(value, providers)
        first_raw = next(value["config"].artifact_root.rglob(first["attempt_id"] + ".raw.json"))
        first_sha = hashlib.sha256(first_raw.read_bytes()).hexdigest()
        _retry(value, first)
        result = advance(value, providers)
        assert result["state"] == "BLOCKED"
        assert result["error"]["code"] == "BOUNDED_EXTRACTION_FAILED"
        assert len(transport.calls) == 2
        with pytest.raises(SourceOperationError, match="RETRY_LIMIT_EXCEEDED"):
            _retry(value, first, key="malformed-json-retry-0002")
        assert len(transport.calls) == 2
    assert len(_attempts(value)) == 2
    assert hashlib.sha256(first_raw.read_bytes()).hexdigest() == first_sha
    assert rows(value, "bounded_extraction_segment_results") == []
    assert rows(value, "bounded_extraction_series")[0]["frontier_version"] == 0


class _InvalidJsonTransport(Transport):
    def __init__(self, content, finish="tool_calls"):
        super().__init__()
        self.content = content
        self.finish = finish

    def __call__(self, endpoint, *, json, headers, timeout, allow_redirects=False):
        self.calls.append({"endpoint": endpoint, "request": json})
        return ToolResponse(self.content, finish=self.finish)


class _SemanticFailureTransport(Transport):
    def __init__(self, mutation):
        super().__init__()
        self.mutation = mutation

    def __call__(self, endpoint, *, json, headers, timeout, allow_redirects=False):
        self.calls.append({"endpoint": endpoint, "request": json})
        target, source = request_parts(json)
        import re
        target["assigned_evidence_refs"] = re.findall(r"\[(EV_[^\]]+)\]", source)
        record = batch_record(json_module.loads(response_content(target, source)), target)
        if self.mutation == "claim_linkage":
            record["dispositions"][0]["claim_refs"] = []
        elif self.mutation == "foreign_evidence":
            record["dispositions"][0]["evidence_ref"] = "EV_INVENTED"
        elif self.mutation == "invalid_selector":
            record["claims"][0]["evidence"].update(
                selection_mode="RAW_SUBSPAN", selector="absent synthetic substring",
            )
        else:
            record["node_candidates"][0]["ownership_evidence_ref"] = "EV_INVENTED"
        return ToolResponse(json_module.dumps(record, ensure_ascii=False))


def test_valid_json_contract_failure_is_not_retryable(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    transport = _InvalidJsonTransport("{}")
    with synthetic_providers(value, transport) as providers:
        first = _malformed_failure(value, providers)
        with pytest.raises(SourceOperationError, match="RETRY_NOT_ELIGIBLE"):
            _retry(value, first)
    assert len(transport.calls) == 1 and len(_attempts(value)) == 1


@pytest.mark.parametrize("mutation", [
    "claim_linkage", "foreign_evidence", "invalid_selector", "ownership",
])
def test_valid_json_semantic_and_binding_failures_are_not_retryable(
        tmp_path, monkeypatch, mutation):
    value = setup_run(tmp_path, monkeypatch)
    transport = _SemanticFailureTransport(mutation)
    with synthetic_providers(value, transport) as providers:
        first = _malformed_failure(value, providers)
        with pytest.raises(SourceOperationError, match="RETRY_NOT_ELIGIBLE"):
            _retry(value, first)
    assert len(transport.calls) == 1 and len(_attempts(value)) == 1


def test_concurrent_retry_authorization_serializes_to_one_attempt(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    with synthetic_providers(value, Transport(mode="malformed")) as providers:
        first = _malformed_failure(value, providers)

    def invoke(key):
        try:
            result = _retry(value, first, key=key)
            return result["duplicate"], result["attempt"]["attempt_id"]
        except SourceOperationError as error:
            return str(error), None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, ("concurrent-retry-key-0001", "concurrent-retry-key-0002")))
    assert sum(item[1] is not None for item in outcomes) == 1
    assert "RETRY_LIMIT_EXCEEDED" in {item[0] for item in outcomes}
    assert len(_attempts(value)) == 2


def test_concurrent_duplicate_retry_request_returns_one_attempt(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    with synthetic_providers(value, Transport(mode="malformed")) as providers:
        first = _malformed_failure(value, providers)

    def invoke(_):
        result = _retry(value, first, key="concurrent-duplicate-key-0001")
        return result["duplicate"], result["attempt"]["attempt_id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, range(2)))
    assert sorted(item[0] for item in outcomes) == [False, True]
    assert len({item[1] for item in outcomes}) == 1
    assert len(_attempts(value)) == 2


def test_attempt_authorization_crash_is_idempotently_recoverable(tmp_path, monkeypatch):
    value = setup_run(tmp_path, monkeypatch)
    with synthetic_providers(value, Transport(mode="malformed")) as providers:
        first = _malformed_failure(value, providers)
    original = persistence.checkpoint

    def crash(name):
        if name == "attempt_reserved":
            raise RuntimeError("SYNTHETIC_CRASH")

    monkeypatch.setattr(persistence, "checkpoint", crash)
    with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
        _retry(value, first)
    monkeypatch.setattr(persistence, "checkpoint", original)
    recovered = _retry(value, first)
    assert recovered["duplicate"] is True and len(_attempts(value)) == 2


@pytest.mark.parametrize("window", [
    "dispatch_durable", "raw_artifact_durable", "outcome_durable", "result_accepted",
])
def test_retry_crash_windows_never_recall_provider(tmp_path, monkeypatch, window):
    value = setup_run(tmp_path, monkeypatch)
    transport = Transport(mode=lambda _target, call: "malformed" if call == 1 else None)
    with synthetic_providers(value, transport) as providers:
        first = _malformed_failure(value, providers)
        _retry(value, first)
        triggered = False

        def crash(name):
            nonlocal triggered
            if not triggered and name == window:
                triggered = True
                raise RuntimeError("SYNTHETIC_CRASH")

        monkeypatch.setattr(persistence, "checkpoint", crash)
        with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
            value["service"].output_batches.advance(
                value["service"].get_run(value["run_id"]), providers, "crash-worker",
            )
        calls = len(transport.calls)
        monkeypatch.setattr(persistence, "checkpoint", lambda _name: None)
        completed = value["service"].output_batches.advance(
            value["service"].get_run(value["run_id"]), providers, "recovery-worker",
        )
        assert len(transport.calls) == calls
        if window == "dispatch_durable":
            assert completed is False
            assert value["service"].get_run(value["run_id"])["state"] == "RECOVERY_REQUIRED"
        else:
            assert completed is True


def test_bounded_qualification_is_event_backed_and_required_on_runtime_drift(
        tmp_path, monkeypatch):
    import pro_a.phase4_orchestration as orchestration
    from pro_a.workbench.cloud_jobs import runtime_identity

    target = runtime_identity("semantic-backend-adapter-v2", workbench_schema_version="12")
    historical = {**target, "git_sha": "35e54a7d342317487b2e99e540fb4011bdec43b1",
                  "domain_code_sha256": "0" * 64}
    historical["runtime_sha256"] = digest({
        key: item for key, item in historical.items() if key != "runtime_sha256"
    })
    target_native = orchestration._runtime()
    historical_native = {**target_native,
                         "repository_commit": "35e54a7d342317487b2e99e540fb4011bdec43b1"}
    monkeypatch.setattr(
        "pro_a.workbench.cloud_jobs.CloudJobs.current_runtime", lambda _self: historical,
    )
    monkeypatch.setattr(orchestration, "_runtime", lambda: historical_native)
    value = setup_run(tmp_path, monkeypatch)
    with synthetic_providers(value, Transport(mode="malformed")) as providers:
        first = _malformed_failure(value, providers)
    monkeypatch.setattr(
        "pro_a.workbench.cloud_jobs.CloudJobs.current_runtime", lambda _self: target,
    )
    monkeypatch.setattr(orchestration, "_runtime", lambda: target_native)
    with pytest.raises(SourceOperationError, match="RETRY_RUNTIME_INCOMPATIBLE"):
        _retry(value, first)
    qualified = assess_bounded_retry_compatibility(
        value["config"], value["run_id"], first["attempt_id"], persist=True,
    )
    assert qualified["status"] == "QUALIFIED" and qualified["duplicate"] is False
    duplicate = assess_bounded_retry_compatibility(
        value["config"], value["run_id"], first["attempt_id"], persist=True,
    )
    assert duplicate["duplicate"] is True
    created = _retry(value, first)
    assert created["retry"]["compatibility_qualification_id"] == qualified["record"]["qualification_id"]
    events = [json_module.loads(row["body_json"]) for row in rows(value, "bounded_extraction_events")
              if row["event_type"] == "BOUNDED_RETRY_COMPATIBILITY_QUALIFIED"]
    assert len(events) == 1 and events[0]["record"]["record_sha256"] == qualified["record"]["record_sha256"]


@pytest.mark.parametrize("drift", [
    "context_semantics", "frozen_config", "runtime_contract", "execution_surface",
])
def test_cross_release_qualification_rejects_semantic_and_config_drift(
        tmp_path, monkeypatch, drift):
    import pro_a.workbench.retry_compatibility as compatibility
    from pro_a.workbench.cloud_jobs import runtime_identity
    from pro_a.workbench.domains import Domains

    value = setup_run(tmp_path, monkeypatch)
    with synthetic_providers(value, Transport(mode="malformed")) as providers:
        first = _malformed_failure(value, providers)
    if drift == "frozen_config":
        path = value["phase4_config"]
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                'model = "deepseek-flash"', 'model = "different-model"',
            ), encoding="utf-8",
        )
    elif drift == "context_semantics":
        original_pending = Domains.pending_basis

        def changed(self, *args, **kwargs):
            basis = original_pending(self, *args, **kwargs)
            return {**basis, "execution_policy": "incompatible-policy"}

        monkeypatch.setattr(Domains, "pending_basis", changed)
    else:
        target = runtime_identity(
            "semantic-backend-adapter-v2", workbench_schema_version="12",
        )
        field = "cloud_contract_version" if drift == "runtime_contract" else "domain_code_sha256"
        target = {**target, field: "incompatible"}
        target["runtime_sha256"] = digest({
            key: item for key, item in target.items() if key != "runtime_sha256"
        })
        monkeypatch.setattr(
            "pro_a.workbench.cloud_jobs.runtime_identity", lambda *_args, **_kwargs: target,
        )
        if drift == "execution_surface":
            original_surface = compatibility._execution_surface_comparison

            def incompatible(kind, historical_git_sha):
                result = original_surface(kind, historical_git_sha)
                return ({**result, "compatible": False, "reason": "SEMANTIC_SURFACE_CHANGED"}
                        if kind == "cloud" else result)

            monkeypatch.setattr(compatibility, "_execution_surface_comparison", incompatible)
    result = assess_bounded_retry_compatibility(
        value["config"], value["run_id"], first["attempt_id"], persist=False,
    )
    assert result["status"] == "BLOCKED" and result["record"] is None
