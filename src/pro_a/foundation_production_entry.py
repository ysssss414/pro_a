"""Governed Foundation target selection around the shared mutation transaction.

External caller trust is explicit. Payloads and qualification receipts never
manufacture a Production authorization. No Foundation content is regenerated here.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re

from . import production_promotion as engine
from .foundation_payload_envelope import BOUND_CONTRACT, artifact_bytes


class ExecutionTargetMode(Enum):
    SHADOW = "SHADOW"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class QualificationReference:
    artifact: bytes | Path
    receipt_id: str
    semantic_sha256: str
    file_sha256: str


@dataclass(frozen=True)
class ProductionAuthorization:
    """Explicit external USER authorization, not a field parsed from the payload."""
    authorization_id: str
    human_authorization: str
    target_path: Path
    bindings: dict
    authority: str = "USER"
    scope: str = "EXACT_PAYLOAD_ONE_TIME"


# Exact five-table extension; existing four tables remain explicitly enumerated.
FOUNDATION_COLUMNS = {
    "sources": "source_id title original_name archived_path sha256 ingestion_mode source_type source_rank origin_type author organization publication_time ingested_at status ima_media_id ima_kb_id metadata_json underlying_source_id analysis_mode",
    "claims": "claim_id statement nature fact_time publication_time ingestion_time source_id evidence_pointer evidence_excerpt scope assumption_text status confidence novelty_level structured_json created_at attributed_to",
    "nodes": "node_id canonical_name primary_type description status created_at updated_at",
    "node_aliases": "alias node_id",
    "node_relations": "relation_id from_node_id relation_type to_node_id scope valid_from valid_to confidence status evidence_claim_id created_at",
    "relation_temporal_semantics": "relation_id temporal_category valid_from_supplied valid_to_supplied projection_sha256 contract_sha256 provenance_json",
    "relation_evidence_authorizations": "link_candidate_id relation_id claim_id relation_candidate_id provenance_mode evidence_id source_id source_sha256 evidence_sha256 evidence_role authorization_state relation_decision claim_decision contract_sha256 packet_sha256 reviewer human_authorization_manifest_id original_packet_sha256 proposition_scope authorized_proposition provenance_json created_at",
    "relation_evidence_links": "relation_id claim_id evidence_role status created_at provenance_mode evidence_id source_id source_sha256 evidence_sha256 authorization_id",
    "current_views": "view_id node_id version status change_level previous_view_id content_md content_json trigger_source_id trigger_claim_ids_json created_at confirmed_at revision_date revision_seq accepted_proposal_id",
}
FOUNDATION_KEYS = {
    "sources": ({"source_id"},), "claims": ({"claim_id"},), "nodes": ({"node_id"},), "node_aliases": ({"alias"},),
    "node_relations": ({"relation_id"},), "relation_temporal_semantics": ({"relation_id"},),
    "relation_evidence_authorizations": ({"link_candidate_id"},), "current_views": ({"view_id"},),
    "relation_evidence_links": ({"relation_id", "claim_id", "evidence_role"}, {"relation_id", "provenance_mode", "evidence_id", "evidence_role"}),
}
require = engine._require


def validate_foundation_mutations(payload):
    mutations = payload.get("intended_mutations") or []
    require(bool(mutations), "EMPTY_PRODUCTION_MUTATION_SET")
    seen = set()
    for mutation in mutations:
        table = mutation.get("table")
        require(table in FOUNDATION_COLUMNS, "UNSUPPORTED_FOUNDATION_TABLE")
        require(mutation.get("operation") == "INSERT", "FOUNDATION_INSERT_ONLY")
        row, key = mutation.get("row") or {}, mutation.get("key") or {}
        require(set(row) == set(FOUNDATION_COLUMNS[table].split()), "FOUNDATION_COLUMN_CONTRACT:" + table)
        require(set(key) in FOUNDATION_KEYS[table] and all(row[k] == v for k, v in key.items()), "FOUNDATION_KEY_CONTRACT:" + table)
        identity = (table, engine.canonical_sha256(key))
        require(identity not in seen, "DUPLICATE_MUTATION_KEY")
        seen.add(identity)
        if table == "current_views":
            require(row["status"] == row["change_level"] == "baseline" and row["view_id"].startswith("BASELINE_")
                    and row["version"].startswith("baseline_") and row["previous_view_id"] is None, "FOUNDATION_BASELINE_ISOLATION")
    return {m["table"] for m in mutations}


def validate_insert_dependencies(connection, payload):
    """Verify the frozen order against actual non-null schema FK dependencies.

    Existing rows satisfy references; otherwise exactly one earlier payload row
    must supply the key. No FK disabling, value generation or mutation reordering.
    """
    mutations = payload["intended_mutations"]
    edges = []
    for index, mutation in enumerate(mutations):
        table, row = mutation["table"], mutation["row"]
        columns = {r["name"] for r in connection.execute(f'PRAGMA table_info("{table}")')}
        require(columns == set(FOUNDATION_COLUMNS[table].split()), "FOUNDATION_SCHEMA_COLUMNS:" + table)
        groups = {}
        for fk in connection.execute(f'PRAGMA foreign_key_list("{table}")'):
            groups.setdefault(fk["id"], []).append(dict(fk))
        for group in groups.values():
            group.sort(key=lambda fk: fk["seq"])
            parent = group[0]["table"]
            values = tuple(row[fk["from"]] for fk in group)
            if any(v is None for v in values):
                continue
            columns = [fk["to"] for fk in group]
            where = " AND ".join(f'"{c}"=?' for c in columns)
            if connection.execute(f'SELECT 1 FROM "{parent}" WHERE {where}', values).fetchone():
                continue
            parents = [i for i, m in enumerate(mutations) if m["table"] == parent and tuple(m["row"][c] for c in columns) == values]
            require(len(parents) == 1 and parents[0] < index, "FOUNDATION_FK_ORDER_OR_PARENT:" + table)
            edges.append((parents[0], index))
    return {"table_order": list(dict.fromkeys(m["table"] for m in mutations)), "operation_edges": edges}


def _receipt(reference, *, entry=False):
    require(isinstance(reference, QualificationReference), "ENTRY_QUALIFICATION_REQUIRED" if entry else "PAYLOAD_QUALIFICATION_REQUIRED")
    data = artifact_bytes(reference.artifact)
    require(hashlib.sha256(data).hexdigest() == reference.file_sha256, "QUALIFICATION_FILE_SHA_MISMATCH")
    receipt = json.loads(data)
    prefix = "production_entry_qualification_receipt" if entry else "qualification_receipt"
    require(receipt.get(prefix + "_id") == reference.receipt_id, "QUALIFICATION_ID_MISMATCH")
    body = {k: v for k, v in receipt.items() if k not in {prefix + "_id", prefix + "_semantic_sha256"}}
    require(engine.canonical_sha256(body) == receipt.get(prefix + "_semantic_sha256") == reference.semantic_sha256, "QUALIFICATION_SEMANTIC_SHA_MISMATCH")
    expected_type = "phase3f_foundation_production_entry_qualification_receipt" if entry else "phase3f_foundation_payload_qualification_receipt"
    require(receipt.get("document_type") == expected_type and receipt.get("qualification_complete") is True, "QUALIFICATION_NOT_COMPLETE")
    expected_state = "QUALIFIED_FOR_EXPLICIT_ONE_TIME_PRODUCTION_APPLY_AUTHORIZATION" if entry else "QUALIFIED_FOR_EXPLICIT_PRODUCTION_APPLY_AUTHORIZATION"
    require(receipt.get("qualification_state") == expected_state, "QUALIFICATION_STATE_INVALID")
    gates = {"envelope_v2", "shadow_apply", "predicted_vs_actual", "idempotency", "rollback_recovery", "security_wrong_basis", "official_views", "accounting", "mutation_core", "applicable_full_regression"}
    if entry:
        gates |= {"exact_entry_path", "five_table_support", "authorization_gates", "applicable_full_regression"}
    require(all(receipt.get("gates", {}).get(g) == "PASS" for g in gates), "QUALIFICATION_GATES_INCOMPLETE")
    return receipt


def execution_bindings(payload, file_sha, qualification, verification_basis, execution_commit):
    """Comparison projection only; never returns or constructs an authorization."""
    basis = verification_basis
    return dict(payload_id=payload["payload_id"], payload_semantic_sha256=payload["payload_hash"], payload_file_sha256=file_sha,
        qualification_receipt_id=qualification.receipt_id, qualification_receipt_semantic_sha256=qualification.semantic_sha256,
        qualification_receipt_file_sha256=qualification.file_sha256, expected_production_sha256=basis.expected_production_sha256,
        expected_schema=basis.expected_schema_version, completed_packet_id=basis.expected_completed_packet_id,
        completed_packet_semantic_sha256=basis.expected_completed_packet_semantic_sha256,
        completed_packet_file_sha256=basis.expected_completed_packet_file_sha256,
        payload_implementation_commit=basis.expected_payload_implementation_commit, entry_implementation_commit=execution_commit,
        payload_envelope_contract_sha256=BOUND_CONTRACT["contract_sha256"])


def _check_receipt_binding(receipt, payload, file_sha, verification_basis):
    for key, expected in (("payload_id", payload["payload_id"]), ("payload_semantic_sha256", payload["payload_hash"]),
                          ("payload_file_sha256", file_sha), ("required_pre_apply_production_sha256", verification_basis.expected_production_sha256),
                          ("required_production_schema", verification_basis.expected_schema_version)):
        require(receipt.get(key) == expected, "QUALIFICATION_BINDING_MISMATCH:" + key)
    require(receipt.get("completed_review_basis") == payload["review_basis"], "QUALIFICATION_COMPLETED_BASIS_MISMATCH")
    require(receipt.get("payload_envelope_contract") == BOUND_CONTRACT, "QUALIFICATION_ENVELOPE_MISMATCH")
    core = {k: payload[k] for k in ("intended_mutations", "mapping", "node_operations", "relation_operations", "claims")}
    require(receipt.get("mutation_core_sha256") == engine.canonical_sha256(core), "QUALIFICATION_CORE_MISMATCH")
    count = len(payload["mapping"])
    require(receipt.get("insert_operations") == len(payload["intended_mutations"]) and receipt.get("accounting") == f"{count}/{count}", "QUALIFICATION_ACCOUNTING_MISMATCH")


def execute(*, payload_artifact, expected_payload_file_sha256, verification_basis, completed_artifact,
            qualification, predicted_diff_artifact, target_path, configured_production_path, execution_commit,
            mode=ExecutionTargetMode.SHADOW, authorization=None, entry_qualification=None, inject_failure_after=None):
    """Exact Foundation entry for both modes; all authority checks precede writable open."""
    from .production_execution import validate_supported_mutations, _write_json_atomic, _restore_after_failure
    require(isinstance(mode, ExecutionTargetMode), "EXECUTION_MODE_REQUIRED")
    require(isinstance(execution_commit, str) and re.fullmatch(r"[0-9a-f]{40}", execution_commit) is not None, "ENTRY_IMPLEMENTATION_REQUIRED")
    if mode is ExecutionTargetMode.PRODUCTION:
        require(isinstance(authorization, ProductionAuthorization), "PRODUCTION_AUTHORIZATION_REQUIRED")
        require(authorization.authority == "USER" and authorization.scope == "EXACT_PAYLOAD_ONE_TIME"
                and bool(authorization.human_authorization.strip()), "PRODUCTION_AUTHORIZATION_INVALID")
        require(re.fullmatch(r"[A-Za-z0-9_-]{8,128}", authorization.authorization_id) is not None, "AUTHORIZATION_ID_INVALID")
        require(inject_failure_after is None, "PRODUCTION_FAILURE_INJECTION_FORBIDDEN")
    # Freeze actual caller-supplied bytes once; do not reread a mutable path downstream.
    completed_bytes = artifact_bytes(completed_artifact)
    payload = engine.validate_payload_artifact(payload_artifact, expected_payload_file_sha256=expected_payload_file_sha256,
        verification_basis=verification_basis, completed_artifact=completed_bytes)
    require(payload.get("adapter_type") == "phase3f_complete_foundation_v1", "FOUNDATION_ADAPTER_REQUIRED")
    prior = _receipt(qualification)
    _check_receipt_binding(prior, payload, expected_payload_file_sha256, verification_basis)
    prediction_bytes = artifact_bytes(predicted_diff_artifact)
    require(hashlib.sha256(prediction_bytes).hexdigest() == prior.get("predicted_diff_file_sha256"), "PREDICTED_DIFF_FILE_MISMATCH")
    prediction = json.loads(prediction_bytes)
    require(prediction.get("payload_sha256") == payload["payload_hash"] and prediction.get("required_production_sha256") == verification_basis.expected_production_sha256, "PREDICTED_DIFF_BASIS_MISMATCH")
    target, configured = Path(target_path).resolve(), Path(configured_production_path).resolve()
    bindings = execution_bindings(payload, expected_payload_file_sha256, qualification, verification_basis, execution_commit)
    if mode is ExecutionTargetMode.SHADOW:
        engine.assert_shadow_target(target, configured)
    else:
        entry = _receipt(entry_qualification, entry=True)
        _check_receipt_binding(entry, payload, expected_payload_file_sha256, verification_basis)
        require(entry.get("entry_implementation_commit") == execution_commit, "ENTRY_IMPLEMENTATION_MISMATCH")
        require(entry.get("prior_qualification_identity") == {k: bindings[k] for k in ("qualification_receipt_id", "qualification_receipt_semantic_sha256", "qualification_receipt_file_sha256")}, "ENTRY_PRIOR_QUALIFICATION_MISMATCH")
        require(entry.get("predicted_diff_file_sha256") == prior.get("predicted_diff_file_sha256"), "ENTRY_PREDICTED_DIFF_MISMATCH")
        bindings.update(entry_qualification_receipt_id=entry_qualification.receipt_id,
            entry_qualification_receipt_semantic_sha256=entry_qualification.semantic_sha256,
            entry_qualification_receipt_file_sha256=entry_qualification.file_sha256)
        require(authorization.bindings == bindings, "PRODUCTION_AUTHORIZATION_BINDING_MISMATCH")
        require(target == configured == Path(authorization.target_path).resolve(), "PRODUCTION_TARGET_MISMATCH")
    tables = validate_supported_mutations(payload, verification_basis=verification_basis, completed_artifact=completed_bytes)
    require(verification_basis.expected_schema_version == "0.2.3", "FOUNDATION_ENTRY_SCHEMA_REQUIRED")
    before = engine.database_identity(target)
    require(before["schema_version"] == "0.2.3" and before["schema_sha256"] == payload["metadata"]["production_schema_sha256"], "ENTRY_SCHEMA_MISMATCH")
    with closing(engine.connect_read_only(target)) as connection:
        state = engine._replay_state(connection, payload)
        require(state != "CONFLICT", "PAYLOAD_REPLAY_CONFLICT")
        actual = {t: sorted(v) for t, v in engine.database_rows(connection).items()}
        expected_rows = prediction["after_rows"] if state == "ALREADY_APPLIED" else prediction["before_rows"]
        require(actual == expected_rows, "ENTRY_PREDICTED_BASELINE_MISMATCH")
        if state == "NEW":
            require(before["sha256"] == verification_basis.expected_production_sha256, "ENTRY_BASELINE_SHA_MISMATCH")
            engine.validate_executable_operations(connection, payload, verification_basis=verification_basis, completed_artifact=completed_bytes)
        dependency = validate_insert_dependencies(connection, payload)
    # One-time journal check is before any writable DB open. Shadow replay remains allowed.
    journal_path = target.parent / "foundation-executions" / authorization.authorization_id / "execution_journal.json" if mode is ExecutionTargetMode.PRODUCTION else None
    if journal_path:
        require(not journal_path.parent.exists(), "FOUNDATION_AUTHORIZATION_ALREADY_ATTEMPTED")
        require(state == "NEW", "FOUNDATION_PRODUCTION_ALREADY_APPLIED")
        journal_path.parent.mkdir(parents=True, exist_ok=False)
    backup = (journal_path.parent / "production_pre.db") if journal_path else target.with_name(target.name + ".foundation_pre.db")
    if state == "NEW":
        if backup.exists():
            require(engine.sha256_file(backup) == before["sha256"], "ENTRY_BACKUP_CONFLICT")
        else:
            engine.copy_production_to_shadow(target, backup, before["sha256"])
    journal = dict(state="PREPARED", execution_bindings=bindings, authorization_id=authorization.authorization_id if journal_path else None,
        human_authorization=authorization.human_authorization if journal_path else None, target=str(target), backup=str(backup))
    if journal_path:
        _write_json_atomic(journal_path, journal)
    result = None
    try:
        result = engine._apply_verified_payload(payload, target, verification_basis=verification_basis,
            completed_artifact=completed_bytes, inject_failure_after=inject_failure_after,
            expected_before_rows=expected_rows, expected_after_rows=prediction["after_rows"])
        with closing(engine.connect_read_only(target)) as connection:
            post_rows = {t: sorted(v) for t,v in engine.database_rows(connection).items()}
        require(post_rows == prediction["after_rows"], "ENTRY_POST_DIFF_MISMATCH")
        post = engine.database_identity(target)
        require(post["schema_sha256"] == before["schema_sha256"], "ENTRY_POST_SCHEMA_CHANGED")
        if journal_path:
            journal.update(state="COMPLETE", result=result, post_sha256=post["sha256"])
            _write_json_atomic(journal_path, journal)
        return dict(status=result["status"], database_result=result, post_identity=post, table_contracts=sorted(tables),
            dependency=dependency, execution_bindings=bindings, mode=mode.value, actual_diff_matches_prediction=True,
            backup_path=str(backup), journal_path=str(journal_path) if journal_path else None,
            shared_executor="pro_a.production_promotion._apply_verified_payload")
    except Exception:
        # Transaction errors roll back in the shared executor. Its return marks commit.
        current = engine.sha256_file(target)
        committed = result is not None and result.get("status") == "COMMITTED"
        require(backup.is_file() and engine.sha256_file(backup) == before["sha256"], "ENTRY_RECOVERY_BACKUP_MISMATCH")
        restoration = _restore_after_failure(target_path=target, backup_path=backup, expected_pre_sha256=before["sha256"],
            archive_destination=backup.parent / "source_materialization_not_used/missing", source_sha256="",
            created_directories=[], archive_root=backup.parent / "source_materialization_not_used", archive_inventory_pre=[],
            database_committed=committed, expected_database_post_sha256=result.get("shadow_post_sha256") if committed else None)
        if journal_path:
            journal.update(state=restoration["status"], restoration=restoration)
            _write_json_atomic(journal_path, journal)
        require(restoration["status"] == "FAILED_RESTORED", "ENTRY_RECOVERY_UNCERTAIN:" + current)
        raise
