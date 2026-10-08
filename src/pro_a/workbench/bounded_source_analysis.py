"""SourcePiece input binding and deterministic, restartable Series execution."""
from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
import json
from collections.abc import Mapping

from pro_a.bounded_extraction import expand_source_analysis_wire_v3
from pro_a.bounded_source_analysis import (
    BOUNDED_SOURCE_ANALYSIS_BINDING_VERSION, BOUNDED_SOURCE_ANALYSIS_OPERATION,
    BOUNDED_SOURCE_ANALYSIS_PROVIDER_VERSION,
    BoundedSourceAnalysisSegmentProvider, piece_input, restore_input, segment_payload,
)
from pro_a.evidence_binding import identity
from pro_a.prompts import SOURCE_ANALYSIS_SYSTEM
from .bounded_extraction_store import BoundedExtractionStore
from .bounded_extraction_persistence import canonical
from .config import BoundaryError


def _require(value, code):
    if not value:
        raise BoundaryError(code)


class BoundedExtractionReplay:
    def __init__(self, cfg, responses, metadata):
        self.cfg, self.responses, self.metadata = cfg, responses, metadata
        self._last = {}

    @property
    def available(self):
        return True

    @property
    def last_call_metadata(self):
        return copy.deepcopy(self._last)

    def json(self, system, user):
        key = hashlib.sha256(user.encode()).hexdigest()
        _require(system == SOURCE_ANALYSIS_SYSTEM and key in self.responses, "BOUNDED_NATIVE_PROMPT_MISMATCH")
        self._last = copy.deepcopy(self.metadata[key])
        return copy.deepcopy(self.responses[key])


class BoundedSourceAnalysisRunner:
    binding_version = BOUNDED_SOURCE_ANALYSIS_BINDING_VERSION
    provider_version = BOUNDED_SOURCE_ANALYSIS_PROVIDER_VERSION
    operation = BOUNDED_SOURCE_ANALYSIS_OPERATION
    provider_type = BoundedSourceAnalysisSegmentProvider
    mode = 'BOUNDED_SERIES_V1'
    piece_input = staticmethod(piece_input)
    restore_input = staticmethod(restore_input)
    segment_payload = staticmethod(segment_payload)
    def __init__(self, service):
        self.service = service
        self.ledger = BoundedExtractionStore(service.config)

    def bind(self, run, plan, checkpoint):
        from .source_operations import SourceOperationError
        run_id = run["processing_run_id"]
        _require(plan["source_sha256"] == run["source_sha256"], "BOUNDED_SOURCE_IDENTITY_MISMATCH")
        for ordinal, native in enumerate(plan["pieces"], 1):
            with self.service.store.connect() as c:
                prior=c.execute("SELECT artifact_relative,sha256 FROM source_cloud_inputs WHERE processing_run_id=? AND operation_kind='SOURCE_ANALYSIS_PIECE' AND ordinal=?",(run_id,ordinal)).fetchone()
            if prior:
                try:
                    content=self.service.artifacts.resolve(prior['artifact_relative']).read_bytes()
                except (OSError,BoundaryError):
                    raise SourceOperationError('BOUNDED_INPUT_ARTIFACT_MISMATCH') from None
                if hashlib.sha256(content).hexdigest()!=prior['sha256']:
                    raise SourceOperationError('BOUNDED_INPUT_ARTIFACT_MISMATCH')
            value = self.piece_input(native, run["source_sha256"], run_id, ordinal)
            artifact = self.service._register_input(run, "SOURCE_ANALYSIS_PIECE", ordinal, value,
                {**checkpoint, "bounded_binding_version": self.binding_version,
                 "piece_count": len(plan["pieces"]), "series_id": value["series_id"]})
            context, catalog, series = self.restore_input(value, run["source_sha256"], run_id, ordinal)
            self.ledger.create(series)
            event = {"ordinal": ordinal, "cloud_input_artifact_id": artifact,
                     "source_piece_id": context.piece.piece_id, "series_id": series.series_id,
                     "series_sha256": series.series_sha256, "initial_plan_sha256": native["initial_plan_sha256"]}
            with self.service.store.connect(operator_write=True) as c:
                c.execute("BEGIN IMMEDIATE")
                existing = [json.loads(r[0]) for r in c.execute("SELECT event_json FROM source_processing_events WHERE processing_run_id=? AND event_type='BOUNDED_EXTRACTION_SERIES_BOUND'", (run_id,))]
                same = [e for e in existing if e["ordinal"] == ordinal]
                _require(not same or same == [event], "BOUNDED_SERIES_INPUT_BINDING_CONFLICT")
                if not same:
                    self.service._event(c, run_id, "BOUNDED_EXTRACTION_SERIES_BOUND", event)

    def inputs(self, run):
        run_id, result, events = run["processing_run_id"], [], []
        with self.service.store.connect() as c:
            previous = "0" * 64
            for seq, row in enumerate(c.execute("SELECT * FROM source_processing_events WHERE processing_run_id=? ORDER BY sequence", (run_id,)), 1):
                body = json.loads(row["event_json"])
                value = {"processing_run_id": run_id, "sequence": seq, "event_type": row["event_type"],
                         "event": body, "previous_sha256": previous, "created_at": row["created_at"]}
                _require(row["sequence"] == seq and row["previous_sha256"] == previous and identity(value) == row["event_sha256"], "SOURCE_EVENT_CHAIN_MISMATCH")
                previous = row["event_sha256"]
                if row["event_type"] == "BOUNDED_EXTRACTION_SERIES_BOUND":
                    events.append(body)
            rows = list(c.execute("SELECT * FROM source_cloud_inputs WHERE processing_run_id=? AND operation_kind='SOURCE_ANALYSIS_PIECE' ORDER BY ordinal", (run_id,)))
        for ordinal, row in enumerate(rows, 1):
            content = self.service.artifacts.resolve(row["artifact_relative"]).read_bytes()
            _require(hashlib.sha256(content).hexdigest() == row["sha256"] and row["ordinal"] == ordinal, "BOUNDED_INPUT_ARTIFACT_MISMATCH")
            document = json.loads(content)
            value = document["payload"]
            _require(document["processing_run_id"] == run_id and document["source_id"] == run["source_id"]
                     and document["source_sha256"] == run["source_sha256"] and document["payload_sha256"] == identity(value)
                     and canonical(document["checkpoint"]) == row["checkpoint_json"], "BOUNDED_INPUT_ARTIFACT_MISMATCH")
            context, catalog, series = self.restore_input(value, run["source_sha256"], run_id, ordinal)
            expected = {"ordinal": ordinal, "cloud_input_artifact_id": row["artifact_id"],
                        "source_piece_id": context.piece.piece_id, "series_id": series.series_id,
                        "series_sha256": series.series_sha256, "initial_plan_sha256": value["native"]["initial_plan_sha256"]}
            _require([e for e in events if e["ordinal"] == ordinal] == [expected]
                     and document["checkpoint"]["piece_count"] == len(rows), "BOUNDED_SERIES_INPUT_BINDING_CONFLICT")
            frozen, _, _, _ = self.ledger.read(series.series_id)
            _require(frozen == series, "BOUNDED_SERIES_INPUT_BINDING_CONFLICT")
            result.append((value, context, catalog, series))
        _require(rows and len(events) == len(rows), "BOUNDED_SERIES_INPUT_BINDING_INCOMPLETE")
        return result

    def projection(self, connection, run_id):
        series = list(connection.execute("SELECT series_id,state FROM bounded_extraction_series WHERE processing_run_id=?", (run_id,)))
        leaves, attempts, complete = 0, 0, 0
        accounting=[]
        for row in series:
            _, plan, state, usage = self.ledger.read(row["series_id"])
            leaves += len(plan.leaves)
            attempts += usage.provider_call_count
            complete += int(state["state"] == "SUCCEEDED_COMPLETE")
            accounting.append(usage)
        def total(field):
            values=[getattr(usage,field) for usage in accounting]
            return sum(values) if all(value is not None for value in values) else None
        return {"extraction_execution_mode": "BOUNDED_SERIES_V1", "logical_extraction_series_count": len(series),
                "active_segment_count": leaves, "completed_series_count": complete,
                "provider_segment_attempt_count": attempts,
                "bounded_usage":{field:total(field) for field in ('input_tokens','output_tokens','total_tokens',
                    'cached_tokens','latency_ms','unknown_usage_calls','output_token_liability')},
                "coverage_status": "COMPLETE" if series and complete == len(series) else
                    "FAILED" if any(r["state"] == "FAILED" for r in series) else
                    "RECOVERY_REQUIRED" if any(r["state"] == "RECOVERY_REQUIRED" for r in series) else "PENDING"}

    def advance(self, run, provider, owner, *, allow_new_subdivision=True):
        from .source_operations import SourceOperationError
        owner = "worker_" + hashlib.sha256(owner.encode()).hexdigest()[:24]
        bindings = self.inputs(run)
        chosen = next((b for b in bindings if self.ledger.read(b[3].series_id)[2]["state"] != "SUCCEEDED_COMPLETE"), None)
        if chosen is None:
            return True
        value, context, catalog, series = chosen
        _, plan, sr, _ = self.ledger.read(series.series_id)
        if sr['state']=='RECOVERY_REQUIRED':
            self.service._transition(run['processing_run_id'],'RECOVERY_REQUIRED','BOUNDED_EXTRACTION',
                                     error='UNKNOWN_EXTERNAL_OUTCOME',manual=True)
            return False
        if sr['state']=='FAILED':
            with self.ledger._connection() as c:
                event=c.execute("SELECT body_json FROM bounded_extraction_events WHERE series_id=? AND event_type='SERIES_FAILED' ORDER BY sequence DESC LIMIT 1",(series.series_id,)).fetchone()
            code=json.loads(event[0])['code'] if event else 'BOUNDED_EXTRACTION_FAILED'
            self._terminate_pending(bindings,owner)
            raise SourceOperationError(code)
        _require(sr["state"] == "OPEN", "BOUNDED_SERIES_NOT_OPEN")
        try:
            sf = self.ledger.claim_series(series.series_id, owner, lease_seconds=self.service.jobs.profile.timeout_seconds+60)
        except BoundaryError as error:
            if str(error) == "LEASE_BUSY":
                return False
            raise
        segment, fence = None, None
        try:
            with self.ledger._connection() as c:
                states = {r["segment_id"]: r["state"] for r in c.execute("SELECT segment_id,state FROM bounded_extraction_segments WHERE series_id=?", (series.series_id,))}
            pending = sorted((s for s in plan.leaves if states[s.segment_id] != "SUCCEEDED_COMPLETE"), key=lambda s: (s.range_start, s.stable_path))
            if pending:
                segment = pending[0]
                try:
                    fence = self.ledger.claim_segment(segment.segment_id, owner, lease_seconds=self.service.jobs.profile.timeout_seconds+60)
                except BoundaryError as error:
                    if str(error) == "LEASE_BUSY":
                        return False
                    raise
                with self.ledger._connection() as c:
                    attempt = c.execute("SELECT * FROM bounded_extraction_attempts WHERE segment_id=? ORDER BY attempt_number DESC LIMIT 1", (segment.segment_id,)).fetchone()
                    dispatched = attempt and c.execute("SELECT 1 FROM bounded_extraction_dispatches WHERE attempt_id=?", (attempt["attempt_id"],)).fetchone()
                if dispatched:
                    self._observe(attempt["attempt_id"], segment, owner, fence, catalog, context,
                                  allow_new_subdivision=allow_new_subdivision)
                elif provider is not None:
                    selected = provider.get(self.operation) if isinstance(provider, Mapping) else provider
                    _require(isinstance(selected, self.provider_type) and selected.available,
                             "BOUNDED_PROVIDER_UNAVAILABLE")
                    _require(selected.provider_identity == "deepseek"
                             and selected.adapter_version == self.provider_version,
                             "BOUNDED_PROVIDER_CONTRACT_MISMATCH")
                    configuration = selected.configuration()
                    _require(configuration["timeout_seconds"] == self.service.jobs.profile.timeout_seconds, "BOUNDED_PROVIDER_CONFIGURATION_MISMATCH")
                    payload = self.segment_payload(value, context, catalog, series, segment)
                    from .strict_recovery import dispatch_payload
                    payload, prompt_name = dispatch_payload(self.ledger, segment.segment_id, payload)
                    with self.ledger._connection(True) as c:
                        segment_row, _ = self.ledger._segment_row(c, segment.segment_id)
                        self.ledger._owned(segment_row, owner, fence)
                        _, sha = self.ledger._artifact(series.series_id, prompt_name, canonical(payload).encode())
                    from .extraction_retry import bounded_attempt_for_dispatch
                    attempt = bounded_attempt_for_dispatch(
                        self.ledger, segment.segment_id, owner, fence,
                        payload_sha256=sha,
                        configuration_sha256=identity(configuration),
                    )
                    _require(self.ledger.record_dispatch(attempt["attempt_id"], owner, fence), "BOUNDED_DISPATCH_ALREADY_OBSERVED")
                    try:
                        response = selected.invoke(payload)
                    except Exception:
                        # No exception text or response excerpts cross this boundary.
                        self._observe(attempt["attempt_id"], segment, owner, fence, catalog, context,
                                      allow_new_subdivision=allow_new_subdivision)
                    else:
                        metadata = asdict(response)
                        raw = metadata.pop("content")
                        self.ledger.record_outcome(attempt["attempt_id"], owner, fence, raw, **metadata)
                        self._observe(attempt["attempt_id"], segment, owner, fence, catalog, context,
                                      allow_new_subdivision=allow_new_subdivision)
                else:
                    return False
            _, plan, sr, _ = self.ledger.read(series.series_id)
            with self.ledger._connection() as c:
                closed = all(c.execute("SELECT state FROM bounded_extraction_segments WHERE segment_id=?", (s.segment_id,)).fetchone()[0] == "SUCCEEDED_COMPLETE" for s in plan.leaves)
            if closed:
                self.ledger.finalize(series.series_id, owner, sf, expected_frontier_version=sr["frontier_version"], catalog=catalog, context=context)
            return all(self.ledger.read(b[3].series_id)[2]["state"] == "SUCCEEDED_COMPLETE" for b in bindings)
        except (ValueError, SourceOperationError) as error:
            if self.ledger.read(series.series_id)[2]["state"] == "RECOVERY_REQUIRED":
                self.service._transition(run["processing_run_id"], "RECOVERY_REQUIRED", "BOUNDED_EXTRACTION", error="UNKNOWN_EXTERNAL_OUTCOME",
                                         manual=True)
                return False
            code = "EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY" if str(error) in (
                "EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY", "SERIES_BUDGET_EXCEEDED") else "BOUNDED_EXTRACTION_FAILED"
            if self.mode == 'WHOLE_PIECE_OUTPUT_DECOMPOSITION' and str(error) in (
                    'SOURCE_METADATA_CONFLICT', 'NODE_CANDIDATE_CONFLICT', 'OUTPUT_OWNERSHIP_VIOLATION'):
                code = str(error)
            self.ledger.fail_series(series.series_id, owner, sf, code)
            self._terminate_pending(bindings,owner)
            raise SourceOperationError(code) from None
        finally:
            self.ledger.release(series.series_id, owner, series_fence=sf,
                                segment_id=segment.segment_id if segment else None, segment_fence=fence)

    def _terminate_pending(self,bindings,owner):
        # Ordered execution leaves later Series uncalled. Close them before a
        # terminal Run, including recovery from a crash after SERIES_FAILED.
        for _,_,_,series in bindings:
            if self.ledger.read(series.series_id)[2]['state']=='OPEN':
                fence=self.ledger.claim_series(series.series_id,owner,lease_seconds=self.service.jobs.profile.timeout_seconds+60)
                try:
                    self.ledger.fail_series(series.series_id,owner,fence,'UPSTREAM_SERIES_FAILED')
                finally:
                    self.ledger.release(series.series_id,owner,series_fence=fence)

    def _observe(self, attempt_id, segment, owner, fence, catalog, context, *, allow_new_subdivision=True):
        try:
            status = self.ledger.reconcile_attempt(attempt_id, owner, fence, catalog, context)
            _require(status != "UNKNOWN_EXTERNAL_OUTCOME", "UNKNOWN_EXTERNAL_OUTCOME")
        except BoundaryError:
            with self.ledger._connection() as c:
                outcome = c.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not outcome or outcome["external_outcome"] != "TRUNCATED":
                raise
        _, plan, sr, _ = self.ledger.read(segment.series_id)
        with self.ledger._connection() as c:
            outcome = c.execute("SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?", (attempt_id,)).fetchone()
            state = c.execute("SELECT state FROM bounded_extraction_segments WHERE segment_id=?", (segment.segment_id,)).fetchone()[0]
        if outcome and outcome["external_outcome"] == "TRUNCATED":
            _require(allow_new_subdivision, "BOUNDED_TRUNCATION_STOP")
            self.ledger.subdivide_after_truncation(segment.segment_id, owner, fence, expected_frontier_version=sr["frontier_version"])
        elif state == "SUBDIVISION_REQUIRED":
            _require(allow_new_subdivision, "BOUNDED_SUBDIVISION_FORBIDDEN")
            _require(sr["provider_call_reservations"] + 2 <= self.ledger.read(segment.series_id)[0].budget.max_provider_calls
                     and sr["output_liability"] + 2 * segment.max_output_tokens <= self.ledger.read(segment.series_id)[0].budget.max_cumulative_output_tokens,
                     "EXTRACTION_DENSITY_EXCEEDS_BOUNDED_POLICY")
            self.ledger.subdivide(segment.segment_id, owner, fence, expected_frontier_version=sr["frontier_version"])

    def replay(self, run, cfg):
        responses, metadata = {}, {}
        for value, context, catalog, series in self.inputs(run):
            aggregate = self.ledger.aggregate(series.series_id)
            key = value["native"]["user_prompt_sha256"]
            _require(key not in responses, "BOUNDED_NATIVE_PROMPT_MISMATCH")
            responses[key] = expand_source_analysis_wire_v3(aggregate["wire"], catalog, context)
            usage = self.ledger.read(series.series_id)[3]
            metadata[key] = {"execution_mode": self.mode, "series_id": series.series_id,
                "attempts_used": usage.provider_call_count, "max_attempts": series.budget.max_provider_calls,
                "attempts": [{"prompt_tokens": usage.input_tokens, "completion_tokens": usage.output_tokens,
                              "total_tokens": usage.total_tokens, "cached_tokens": usage.cached_tokens,
                              "latency_ms": usage.latency_ms, "finish_reason": "durable-series"}]}
        return BoundedExtractionReplay(cfg, responses, metadata)
