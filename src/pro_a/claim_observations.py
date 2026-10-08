"""Offline, opt-in Observation preservation and nonauthoritative Native projection.

No Provider, Analyzer, permanent Claim ID, checkpoint or runtime is replaced.
Future runtime integration must bind these artifact identities before dispatch.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
import json

from .analyzer import normalize_ws
from .bounded_extraction import expand_source_analysis_wire_v3, series_coverage
from .evidence_binding import EVIDENCE_SELECTION_FIELDS, identity, resolve_evidence_binding_v2
from .production_promotion import deterministic_id
from .semantic_decomposition import SEMANTIC_MAX_PARENTS_PER_BATCH, partition_semantic_claims, semantic_prompt_token_upper_bound

LEDGER_VERSION = "claim-observation-ledger-v1"
PROJECTION_VERSION = "native-claim-observation-projection-v1"
ADMISSION_VERSION = "observation-semantic-admission-v1"
BLOCKED = "BLOCKED_PENDING_REVIEW"
ADMITTED = "ELIGIBLE_FOR_EXISTING_PREFLIGHT"


class ObservationError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise ObservationError(code)


def _seal(body):
    body = json.loads(json.dumps(body, ensure_ascii=False, allow_nan=False))
    return {**body, "identity": identity(body)}


def _verify(document, version):
    _require(isinstance(document, dict) and document.get("version") == version,
             "OBSERVATION_CONTRACT_MISMATCH")
    _require(document.get("identity") == identity({k: v for k, v in document.items() if k != "identity"}),
             "OBSERVATION_ARTIFACT_IDENTITY_MISMATCH")


def build_observation_ledger(source_id, series, plan, results, catalog, context):
    """Validate immutable accepted leaves and preserve each local Claim, even duplicates."""
    _require(isinstance(source_id, str) and bool(source_id.strip()), "SOURCE_ID_REQUIRED")
    coverage = series_coverage(series, plan, results, catalog, context)
    _require(coverage.complete, "SERIES_COVERAGE_INCOMPLETE")
    by_id = {r.segment_id: r for r in results}
    observations, originals = [], []
    for leaf in plan.leaves:
        result = by_id[leaf.segment_id]
        wire = json.loads(result.wire_json)
        native = expand_source_analysis_wire_v3(wire, catalog, context)
        originals.append(asdict(result))
        for local, (claim, expanded) in enumerate(zip(wire["claims"], native["claims"]), 1):
            selection = {k: claim[k] for k in EVIDENCE_SELECTION_FIELDS if k in claim}
            evidence = asdict(resolve_evidence_binding_v2(selection, catalog, context))
            binding = {"version": LEDGER_VERSION, "processing_run_id": series.processing_run_id,
                "source_id": source_id, "source_sha256": context.source_sha256,
                "source_piece_id": context.piece.piece_id, "series_id": series.series_id,
                "segment_id": leaf.segment_id, "segment_result_sha256": result.result_sha256,
                "local_claim_ordinal": local, "claim_payload_sha256": identity(claim),
                "evidence_identity": evidence["binding_sha256"]}
            observations.append({"observation_id": "OBS_" + identity(binding), "binding": binding,
                "aggregate_ordinal": len(observations) + 1, "claim": copy.deepcopy(claim),
                "expanded_claim": expanded, "evidence": evidence,
                "referenced_candidates": [copy.deepcopy(c) for c in wire.get("node_candidates", [])
                    if c["canonical_name"] in claim.get("related_candidate_names", [])]})
    return _seal({"version": LEDGER_VERSION, "processing_run_id": series.processing_run_id,
        "source_id": source_id, "source_sha256": context.source_sha256,
        "source_piece_id": context.piece.piece_id, "series_id": series.series_id,
        "coverage_sha256": coverage.coverage_sha256,
        "ordered_segment_result_shas": [r["result_sha256"] for r in originals],
        "original_segment_results": originals, "observations": observations})


def _core(observation):
    # Conservative exact comparisons: no normalization of attribution/time/scope,
    # no inferred equivalence, no deletion of confidence/assumptions/Node variants.
    return {"claim": {k: v for k, v in observation["expanded_claim"].items()
            if k not in ("claim_ref", "evidence_excerpt", "evidence_pointer")},
        "referenced_candidates": observation["referenced_candidates"]}


def _classification(members):
    if len(members) == 1:
        return "SINGLE_OBSERVATION", []
    fields = sorted({k for m in members for k in m["expanded_claim"]} - {"claim_ref"})
    differences = [k for k in fields if len({identity(m["expanded_claim"].get(k)) for m in members}) > 1]
    if len({identity(m["referenced_candidates"]) for m in members}) > 1:
        differences.append("referenced_candidates")
    if len({m["binding"]["evidence_identity"] for m in members}) > 1:
        differences.append("evidence_identity")
    if len({identity(_core(m)) for m in members}) > 1:
        return "NON_EQUIVALENT_OBSERVATIONS", differences
    if len({m["binding"]["evidence_identity"] for m in members}) > 1:
        return "SAME_ASSERTION_MULTIPLE_EVIDENCE", differences
    return "EXACT_DUPLICATE", differences


def build_native_projection(ledger, native_claims):
    """Map actual Native ordinal provenance, never fuzzy-match or infer missing refs.

    Input must be the full Analyzer result, before permanent Claim construction.
    Atomic splits or any unsupported mapping topology fail closed for review.
    """
    _verify(ledger, LEDGER_VERSION)
    observations = ledger["observations"]
    expected = {}
    for ordinal, observation in enumerate(observations, 1):
        _require(observation["aggregate_ordinal"] == ordinal, "STOP_PROJECTION_MAPPING_AMBIGUOUS")
        expected.setdefault(normalize_ws(observation["claim"]["statement"]).lower(), []).append(observation)
    _require(len(native_claims) == len(expected), "STOP_PROJECTION_MAPPING_AMBIGUOUS")
    groups, seen = [], set()
    for index, claim in enumerate(native_claims):
        key = normalize_ws(claim.get("statement", "")).lower()
        _require(key in expected and key not in seen, "STOP_PROJECTION_MAPPING_AMBIGUOUS")
        members = expected[key]
        refs = [f'C{m["aggregate_ordinal"]}' for m in members]
        _require(claim.get("_relation_claim_refs") == refs and claim.get("claim_ref") == refs[0],
                 "STOP_PROJECTION_MAPPING_AMBIGUOUS")
        seen.add(key)
        classification, differences = _classification(members)
        eligible = classification in ("SINGLE_OBSERVATION", "EXACT_DUPLICATE")
        groups.append(_seal({"native_index": index, "native_claim_sha256": identity(claim),
            "native_claim": copy.deepcopy(claim), "observation_ids": [m["observation_id"] for m in members],
            "classification": classification, "differing_fields": differences,
            "semantic_admission": ADMITTED if eligible else BLOCKED,
            "review_decision": None}))
    mapped = [o for g in groups for o in g["observation_ids"]]
    _require(len(mapped) == len(set(mapped)) == len(observations)
             and set(mapped) == {o["observation_id"] for o in observations},
             "STOP_PROJECTION_MAPPING_AMBIGUOUS")
    return _seal({"version": PROJECTION_VERSION, "ledger_identity": ledger["identity"],
        "admission_version": ADMISSION_VERSION, "native_projection_authoritative": False,
        "native_claims_sha256": identity(native_claims), "groups": groups})


def verify_projection(ledger, projection):
    _verify(ledger, LEDGER_VERSION)
    _verify(projection, PROJECTION_VERSION)
    _require(projection == build_native_projection(ledger, [g["native_claim"] for g in projection["groups"]]),
             "OBSERVATION_PROJECTION_MISMATCH")


def private_review_artifact(ledger, projection):
    """Complete private review object; persist with existing write-once artifacts.

    No Review decision is implemented. A future decision must bind group identity,
    every Observation ID, action, reason and reviewer in a new append-only contract.
    """
    verify_projection(ledger, projection)
    return _seal({"version": "claim-observation-private-review-v1", "ledger": ledger,
        "projection": projection, "allowed_future_actions": ["RETAIN", "SPLIT", "MERGE", "DEFER"],
        "decisions_applied": [], "production_admission": "NOT_AUTHORIZED"})


def bind_semantic_inputs(ledger, projection, native_records, semantic_inputs):
    """Bind existing permanent records/semantic inputs without minting new Claim IDs.

    Native record construction supplies claim_index. Missing/skipped/reordered or
    duplicate records are unsupported here and stop instead of guessing lineage.
    """
    verify_projection(ledger, projection)
    groups = projection["groups"]
    _require(len(native_records) == len(semantic_inputs) == len(groups), "STOP_PROJECTION_MAPPING_AMBIGUOUS")
    ids = [r.get("claim_id") for r in native_records]
    _require(all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids),
             "STOP_PROJECTION_MAPPING_AMBIGUOUS")
    bindings = []
    for index, (record, semantic, group) in enumerate(zip(native_records, semantic_inputs, groups)):
        claim = group["native_claim"]
        # Verify the existing operational_ingestion identity formula, including
        # pre-record Claim content. Record building may reconcile a qualifier;
        # it must not be matched back by guessing its rewritten statement.
        expected_id = deterministic_id("CLM", {"source_sha256": ledger["source_sha256"],
            "claim_index": index, "claim": {k: v for k, v in claim.items() if not k.startswith("origin_")}})
        _require(record.get("claim_index") == index and record.get("source_id") == ledger["source_id"]
                 and record.get("claim_id") == expected_id
                 and semantic.get("claim_id") == record["claim_id"]
                 and semantic.get("claim_text") == record["statement"], "STOP_PROJECTION_MAPPING_AMBIGUOUS")
        _require(all(record.get(k) == claim.get(k) for k in
            ("attributed_to", "fact_time", "scope", "nature", "evidence_excerpt", "evidence_pointer")),
            "SEMANTIC_OBSERVATION_INPUT_MISMATCH")
        _require(all(semantic.get(target) == str(record.get(source) or "") for target, source in
            (("attribution", "attributed_to"), ("scope", "scope"), ("fact_time", "fact_time"), ("assigned_nature", "nature"))),
            "SEMANTIC_OBSERVATION_INPUT_MISMATCH")
        bindings.append({"group_identity": group["identity"], "claim_id": record["claim_id"],
            "native_record_sha256": identity(record), "semantic_input": copy.deepcopy(semantic),
            "semantic_input_sha256": identity(semantic), "semantic_admission": group["semantic_admission"]})
    return _seal({"version": ADMISSION_VERSION, "projection_identity": projection["identity"],
        "ledger_identity": ledger["identity"], "bindings": bindings})


def guard_semantic_inputs(ledger, projection, admission, selected_inputs):
    """Mandatory guard for this opt-in contract, before any downstream execution.

    A caller cannot turn a BLOCKED group into an admitted one by changing a flag.
    This qualification does not activate this contract on a historical Run.
    """
    verify_projection(ledger, projection)
    _verify(admission, ADMISSION_VERSION)
    _require(admission["ledger_identity"] == ledger["identity"]
             and admission["projection_identity"] == projection["identity"], "SEMANTIC_OBSERVATION_INPUT_MISMATCH")
    bindings = admission["bindings"]
    _require(len(bindings) == len(projection["groups"]), "SEMANTIC_OBSERVATION_INPUT_MISMATCH")
    by_id = {}
    for binding, group in zip(bindings, projection["groups"]):
        _require(binding["group_identity"] == group["identity"]
                 and binding["semantic_admission"] == group["semantic_admission"]
                 and binding["semantic_input_sha256"] == identity(binding["semantic_input"])
                 and binding["claim_id"] == binding["semantic_input"].get("claim_id")
                 and binding["claim_id"] not in by_id, "SEMANTIC_OBSERVATION_INPUT_MISMATCH")
        by_id[binding["claim_id"]] = binding
    seen = set()
    for claim in selected_inputs:
        binding = by_id.get(claim.get("claim_id"))
        _require(binding is not None and claim["claim_id"] not in seen
                 and binding["semantic_input"] == claim, "SEMANTIC_OBSERVATION_INPUT_MISMATCH")
        _require(binding["semantic_admission"] == ADMITTED, BLOCKED)
        seen.add(claim["claim_id"])


def semantic_capacity_preflight(ledger, projection, admission, *, input_token_budget, extraction_jobs):
    """Predict only explicitly eligible parents; exclusions remain visible for review."""
    from .workbench.source_operations import MAX_STAGE1_JOBS_PER_RUN
    eligible = [b["semantic_input"] for b in admission["bindings"] if b["semantic_admission"] == ADMITTED]
    guard_semantic_inputs(ledger, projection, admission, eligible)
    _require(type(extraction_jobs) is int and 0 <= extraction_jobs <= MAX_STAGE1_JOBS_PER_RUN, "INVALID_EXTRACTION_JOB_COUNT")
    batches = partition_semantic_claims(eligible, max_parents=SEMANTIC_MAX_PARENTS_PER_BATCH, max_input_tokens=input_token_budget)
    total = extraction_jobs + len(batches)
    return {"version": ADMISSION_VERSION, "scope": "ELIGIBLE_PROJECTION_SUBSET_ONLY",
        "projection_identity": projection["identity"], "admission_identity": admission["identity"],
        "native_parent_claims": len(projection["groups"]), "eligible_parent_claims": len(eligible),
        "blocked_parent_claims": len(projection["groups"]) - len(eligible),
        "semantic_batch_count": len(batches), "semantic_input_token_budget": input_token_budget,
        "max_batch_token_upper_bound": max((semantic_prompt_token_upper_bound(b) for b in batches), default=0),
        "projected_total_logical_jobs": total, "job_limit": MAX_STAGE1_JOBS_PER_RUN,
        "job_budget_status": "WITHIN_BUDGET" if total <= MAX_STAGE1_JOBS_PER_RUN else "SOURCE_JOB_BUDGET_EXCEEDED",
        "all_observations_admitted": all(b["semantic_admission"] == ADMITTED for b in admission["bindings"]),
        "semantic_jobs_created": 0}
