"""Deterministic qualification-only review slice for Phase 3F Stage 1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .phase3f_review_completion import (
    DECISION_AUTHORITY,
    ReviewCompletionError,
    _validate_completed_human_inputs,
    read_review_packet,
    validate_blank_review_packet,
)
from .production_promotion import (
    canonical_sha256,
    connect_read_only,
    production_identity,
    sha256_file,
)


DOCUMENT_TYPE = "phase3f_stage1_qualification_review_packet"
SCHEMA_VERSION = "1"
VALIDATION_SCOPE = "STAGE1_QUALIFICATION_REVIEW_COMPLETION"
REVIEW_SCOPE = "PHASE3F_STAGE1_HANDOFF_QUALIFICATION_ONLY"
MANIFEST_DOCUMENT_TYPE = "phase3f_stage1_qualification_review_manifest"

EXPECTED_SOURCE_PACKET_ID = "REVIEW_PACKET_3B8F0B25ED21C667"
EXPECTED_SOURCE_PACKET_HASH = (
    "3b8f0b25ed21c667f47a8eac3942ba5028c22c6303ea0f484c63a5170ab0e8f0"
)
EXPECTED_RUN_ID = "INGEST_2644CBDB2693D5E0"
EXPECTED_SOURCE_ID = "SRC_1D42C19206AE3622"
EXPECTED_PRODUCTION_SHA256 = (
    "3c0007f38b136686cb1e0e73e2ad2f389983f61ae2c81679fcf5067835c4eba0"
)

SELECTED_CANDIDATES = {
    "claims": (
        "CLM_07152FCFBF4C3D1B",
        "CLM_74B65D5D09781B64",
        "CLM_229114C7C3F70FE9",
    ),
    "nodes": (
        "CAND_NODE_E8A75C771486B74E",
        "CAND_NODE_E7C5A8860931121D",
        "CAND_NODE_757A9745164C0433",
    ),
    "relations": ("PARENT_PLACEMENT_67ADDE309C1A5CAB",),
}
EXPECTED_CONTENT_HASHES = {
    "CLM_07152FCFBF4C3D1B": "f423bd311998cba2ea833983995940af544c884363985c6c955a5e72791ff888",
    "CLM_74B65D5D09781B64": "ae399072b5dfa5241d805e5cd357f9ec016a987dfb404eb5208f6a26be2c46c2",
    "CLM_229114C7C3F70FE9": "5600725f3cf6b35d6d64226bc056264c1d1b78ee7489cbb40ee2f276b24ebe90",
    "CAND_NODE_E8A75C771486B74E": "a0d5818d653ea361ca47f400ec2d5446bbd4fb274011036baeec1f94ff93ba39",
    "CAND_NODE_E7C5A8860931121D": "d546a5f136c2e984ea06639846c40401458986f24919bd724ddcb0d555287b2f",
    "CAND_NODE_757A9745164C0433": "2be61fbece0173ddf8ed4dc08d836375c62a11972f6e34d00e8bbcd4b398f8a4",
    "PARENT_PLACEMENT_67ADDE309C1A5CAB": "fc25882e82d47b69aa8f5a9c7fad05a3c84a8a2e77bd62c6335fbd04d444211c",
}
_HUMAN_FIELDS = {
    "claims": {"decision", "reason"},
    "nodes": {"decision", "reason", "target_node_id"},
    "relations": {"decision", "reason"},
}
_RECORD_FIELDS = {
    "candidate_type",
    "candidate_id",
    "provenance",
    "content",
    "content_sha256",
    "allowed_decisions",
    "decision_effects",
    "human_input",
}


class QualificationReviewError(ValueError):
    """Stable fail-closed qualification-review error."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise QualificationReviewError(code, detail)


def _repo_relative(path: Path, run_root: Path) -> str:
    root = run_root.resolve().parents[2]
    resolved = path.resolve()
    _require(root in resolved.parents, "PATH_OUTSIDE_REPOSITORY", str(path))
    return resolved.relative_to(root).as_posix()


def _source_packet(path: Path, run_root: Path) -> dict[str, Any]:
    packet = read_review_packet(path)
    try:
        validate_blank_review_packet(packet, run_root)
    except ReviewCompletionError as exc:
        raise QualificationReviewError(
            "SOURCE_REVIEW_PACKET_INVALID", str(exc)
        ) from exc
    expected = (
        packet.get("packet_id") == EXPECTED_SOURCE_PACKET_ID
        and packet.get("immutable_packet_sha256")
        == EXPECTED_SOURCE_PACKET_HASH
        and packet["run"].get("run_id") == EXPECTED_RUN_ID
        and packet["source"].get("source_id") == EXPECTED_SOURCE_ID
        and packet["production_baseline"].get("sha256")
        == EXPECTED_PRODUCTION_SHA256
    )
    _require(expected, "SOURCE_REVIEW_PACKET_IDENTITY_MISMATCH")
    return packet


def _production(
    path: Path, source_packet: Mapping[str, Any]
) -> dict[str, Any]:
    identity = production_identity(path)
    for key, value in source_packet["production_baseline"].items():
        _require(identity.get(key) == value, "PRODUCTION_BASELINE_MISMATCH", key)
    _require(
        identity["sha256"] == EXPECTED_PRODUCTION_SHA256,
        "PRODUCTION_SHA256_MISMATCH",
    )
    return identity


def _node_context(path: Path, node_id: str) -> dict[str, str]:
    connection = connect_read_only(path)
    try:
        rows = connection.execute(
            "SELECT node_id, canonical_name, primary_type, status "
            "FROM nodes WHERE node_id = ?",
            (node_id,),
        ).fetchall()
    finally:
        connection.close()
    _require(
        len(rows) == 1,
        "PRODUCTION_NODE_NOT_UNIQUELY_RESOLVED",
        node_id,
    )
    return dict(rows[0])


def _selected_records(
    source: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    selected = {}
    for group, ids in SELECTED_CANDIDATES.items():
        records = source.get(group)
        _require(isinstance(records, list), "SOURCE_RECORD_GROUP_INVALID", group)
        by_id = {record.get("candidate_id"): record for record in records}
        _require(len(by_id) == len(records), "SOURCE_DUPLICATE_CANDIDATE_ID", group)
        _require(set(ids).issubset(by_id), "QUALIFICATION_CANDIDATE_MISSING", group)
        selected[group] = [copy.deepcopy(by_id[candidate_id]) for candidate_id in ids]
        for record in selected[group]:
            candidate_id = record["candidate_id"]
            _require(
                record.get("content_sha256") == EXPECTED_CONTENT_HASHES[candidate_id]
                == canonical_sha256(record.get("content")),
                "QUALIFICATION_CANDIDATE_CONTENT_HASH_MISMATCH",
                candidate_id,
            )
            _require(
                all(value == "" for value in record["human_input"].values()),
                "SOURCE_CANDIDATE_DECISION_NOT_BLANK",
                candidate_id,
            )
    _check_selected_semantics(selected)
    return selected


def _check_selected_semantics(
    selected: Mapping[str, list[dict[str, Any]]],
) -> None:
    records = {
        item["candidate_id"]: item["content"]
        for group in selected.values()
        for item in group
    }
    clean = records["CLM_07152FCFBF4C3D1B"]
    _require(
        clean.get("review_admitted") is True
        and (clean.get("semantic_admission") or {}).get(
            "overall_guard_disposition"
        )
        == "ADMISSIBLE",
        "CLEAN_CLAIM_PATH_MISMATCH",
    )
    drift = records["CLM_74B65D5D09781B64"].get("evidence_validation") or {}
    _require(
        drift.get("fidelity_status") == "QUOTE_DRIFT"
        and drift.get("bound") is False,
        "QUOTE_DRIFT_PATH_MISMATCH",
    )
    _require(
        records["CLM_229114C7C3F70FE9"].get("duplicate_of_claim_id")
        == "CLM_7F26222C59E13C59",
        "DUPLICATE_GOVERNANCE_PATH_MISMATCH",
    )
    create = records["CAND_NODE_E8A75C771486B74E"]
    _require(
        create.get("proposed_name") == "超节点"
        and create.get("proposed_aliases") == ["超节点架构", "超节点系统"],
        "CREATE_NODE_IDENTITY_MISMATCH",
    )
    reuse = records["CAND_NODE_E7C5A8860931121D"]
    targets = (reuse.get("exact_production_resolution") or {}).get(
        "candidate_targets"
    )
    _require(
        reuse.get("proposed_name") == "通信"
        and targets
        == [
            {
                "node_id": "NODE_20260814_1D6371B9",
                "canonical_name": "通信",
                "primary_type": "Industry",
                "status": "active",
            }
        ],
        "REUSE_NODE_TARGET_MISMATCH",
    )
    defer = records["CAND_NODE_757A9745164C0433"]
    _require(
        defer.get("proposed_name") == "PCI Express"
        and defer.get("supporting_claim_ids") == []
        and defer.get("advisory_suggestion") == "DEFER",
        "DEFER_NODE_PATH_MISMATCH",
    )
    relation = records["PARENT_PLACEMENT_67ADDE309C1A5CAB"]
    _require(
        relation.get("child_node_candidate_id")
        == "CAND_NODE_E8A75C771486B74E"
        and relation.get("relation_type") == "part_of"
        and relation.get("parent_node_id") == "NODE_20260814_164548FF",
        "PARENT_PLACEMENT_PATH_MISMATCH",
    )


def build_blank_qualification_packet(
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> dict[str, Any]:
    """Build the exact seven-item blank Stage 1 qualification slice."""
    source_path = Path(source_packet_path)
    run_root = Path(run_root)
    production_path = Path(production_path)
    source = _source_packet(source_path, run_root)
    production = _production(production_path, source)
    selected = _selected_records(source)
    parent = _node_context(production_path, "NODE_20260814_164548FF")
    reuse = _node_context(production_path, "NODE_20260814_1D6371B9")
    _require(reuse["canonical_name"] == "通信", "REUSE_DISPLAY_CONTEXT_MISMATCH")

    body = {
        "document_type": DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "packet_status": "HUMAN_COMPLETION_REQUIRED",
        "validation_scope": VALIDATION_SCOPE,
        "review_scope": REVIEW_SCOPE,
        "qualification_only": True,
        "full_operational_review_complete": False,
        "production_authorization": False,
        "unselected_candidates_reviewed": False,
        "source_review_packet": {
            "relative_path": _repo_relative(source_path, run_root),
            "file_sha256": sha256_file(source_path),
            "size_bytes": source_path.stat().st_size,
            "packet_id": source["packet_id"],
            "immutable_packet_sha256": source["immutable_packet_sha256"],
            "candidate_universe_sha256": source["summary"][
                "candidate_universe_sha256"
            ],
            "full_candidate_counts": {
                "claims": len(source["claims"]),
                "nodes": len(source["nodes"]),
                "relations": len(source["relations"]),
                "total": source["summary"]["total_operational_decisions_required"],
            },
        },
        "run": copy.deepcopy(source["run"]),
        "source": copy.deepcopy(source["source"]),
        "production_baseline": copy.deepcopy(source["production_baseline"]),
        "production_display_context": {
            "resolution_method": (
                "READ_ONLY_EXACT_NODE_ID_LOOKUP_AGAINST_FROZEN_PRODUCTION"
            ),
            "production_sha256": production["sha256"],
            "resolved_nodes": {
                "parent_placement_target": parent,
                "reuse_target": reuse,
            },
            "display_context_only": True,
        },
        "selection_contract": {
            "selection_method": (
                "EXPLICIT_STAGE1_QUALIFICATION_CANDIDATE_ID_ALLOWLIST"
            ),
            "selected_candidate_ids": {
                group: list(ids) for group, ids in SELECTED_CANDIDATES.items()
            },
            "unselected_candidate_count": 198,
        },
        "summary": {
            "claim_candidates": 3,
            "node_candidates": 3,
            "parent_placement_candidates": 1,
            "qualification_candidate_count": 7,
        },
        "human_completion": {
            "decision_authority": DECISION_AUTHORITY,
            "reviewer": "",
        },
        **selected,
        "safety": {
            "human_decisions_prefilled": False,
            "advisory_values_used_as_authorization": False,
            "evaluation_gold_used_as_authorization": False,
            "unselected_candidates_reviewed": False,
            "full_operational_review_complete": False,
            "production_apply_authorized": False,
            "production_mutation_permitted": False,
            "cloud_llm_calls": 0,
            "local_llm_calls": 0,
        },
    }
    digest = canonical_sha256(body)
    return {
        **body,
        "packet_id": f"QUALIFICATION_REVIEW_PACKET_{digest[:16].upper()}",
        "immutable_packet_sha256": digest,
    }


def _blank_editable_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(packet, dict), "PACKET_STRUCTURE_INVALID", "root")
    blank = copy.deepcopy(packet)
    completion = blank.get("human_completion")
    _require(
        isinstance(completion, dict)
        and set(completion) == {"decision_authority", "reviewer"}
        and completion.get("decision_authority") == DECISION_AUTHORITY
        and isinstance(completion.get("reviewer"), str),
        "PACKET_STRUCTURE_INVALID",
        "human_completion",
    )
    completion["reviewer"] = ""
    for group, expected_ids in SELECTED_CANDIDATES.items():
        records = blank.get(group)
        _require(isinstance(records, list), "PACKET_STRUCTURE_INVALID", group)
        _require(
            [item.get("candidate_id") for item in records] == list(expected_ids),
            "QUALIFICATION_CANDIDATE_SET_INVALID",
            group,
        )
        for record in records:
            _require(
                isinstance(record, dict) and set(record) == _RECORD_FIELDS,
                "PACKET_STRUCTURE_INVALID",
                group,
            )
            human = record.get("human_input")
            _require(
                isinstance(human, dict)
                and set(human) == _HUMAN_FIELDS[group]
                and all(isinstance(value, str) for value in human.values()),
                "PACKET_STRUCTURE_INVALID",
                record["candidate_id"],
            )
            record["human_input"] = {field: "" for field in human}
    return blank


def _validate_immutable_packet(
    packet: Mapping[str, Any],
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> None:
    for field, value in (
        ("document_type", DOCUMENT_TYPE),
        ("schema_version", SCHEMA_VERSION),
        ("validation_scope", VALIDATION_SCOPE),
        ("review_scope", REVIEW_SCOPE),
        ("qualification_only", True),
        ("full_operational_review_complete", False),
        ("production_authorization", False),
        ("unselected_candidates_reviewed", False),
    ):
        code = (
            "QUALIFICATION_SCOPE_MASQUERADE"
            if field
            in {
                "full_operational_review_complete",
                "production_authorization",
                "unselected_candidates_reviewed",
            }
            else "QUALIFICATION_PACKET_IDENTITY_INVALID"
        )
        _require(packet.get(field) == value, code, field)
    actual = _blank_editable_fields(packet)
    expected = build_blank_qualification_packet(
        source_packet_path, run_root, production_path
    )
    _require(
        packet.get("packet_id") == expected["packet_id"],
        "PACKET_ID_MISMATCH",
    )
    _require(
        packet.get("immutable_packet_sha256")
        == expected["immutable_packet_sha256"],
        "PACKET_HASH_MISMATCH",
    )
    _require(actual == expected, "IMMUTABLE_FIELDS_CHANGED")


def validate_blank_qualification_packet(
    packet: Mapping[str, Any],
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> dict[str, Any]:
    """Validate the slice identity and require all human fields blank."""
    _validate_immutable_packet(
        packet, source_packet_path, run_root, production_path
    )
    _require(
        packet["human_completion"]["reviewer"] == "",
        "BLANK_PACKET_REVIEWER_NOT_BLANK",
    )
    for group in SELECTED_CANDIDATES:
        for record in packet[group]:
            _require(
                all(value == "" for value in record["human_input"].values()),
                "BLANK_PACKET_DECISION_NOT_BLANK",
                record["candidate_id"],
            )
    return {
        "document_type": "phase3f_stage1_blank_qualification_review_validation",
        "schema_version": SCHEMA_VERSION,
        "status": "VALID_BLANK_QUALIFICATION_REVIEW_PACKET",
        "validation_scope": VALIDATION_SCOPE,
        "review_scope": REVIEW_SCOPE,
        "packet_id": packet["packet_id"],
        "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "source_review_packet_id": packet["source_review_packet"]["packet_id"],
        "run_id": packet["run"]["run_id"],
        "source_id": packet["source"]["source_id"],
        "qualification_candidate_count": 7,
        "human_decisions_present": False,
        "full_operational_review_complete": False,
        "production_authorization": False,
        "ready_for_stage1_requalification": False,
    }


def validate_completed_qualification_packet(
    packet: Mapping[str, Any],
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> dict[str, Any]:
    """Validate exactly seven decisions, never the other 198 candidates."""
    _validate_immutable_packet(
        packet, source_packet_path, run_root, production_path
    )
    try:
        reviewer, counts, total = _validate_completed_human_inputs(packet)
    except ReviewCompletionError as exc:
        raise QualificationReviewError(exc.code, str(exc)) from exc
    _require(total == 7, "QUALIFICATION_DECISION_COUNT_INVALID", str(total))
    return {
        "document_type": (
            "phase3f_stage1_qualification_review_completion_validation"
        ),
        "schema_version": SCHEMA_VERSION,
        "status": "HUMAN_QUALIFICATION_REVIEW_COMPLETE_AND_VALID",
        "validation_scope": VALIDATION_SCOPE,
        "review_scope": REVIEW_SCOPE,
        "packet_id": packet["packet_id"],
        "immutable_packet_sha256": packet["immutable_packet_sha256"],
        "completed_packet_sha256": canonical_sha256(packet),
        "source_review_packet_id": packet["source_review_packet"]["packet_id"],
        "source_review_packet_hash": packet["source_review_packet"][
            "immutable_packet_sha256"
        ],
        "run_id": packet["run"]["run_id"],
        "source_id": packet["source"]["source_id"],
        "decision_authority": DECISION_AUTHORITY,
        "reviewer": reviewer,
        "decision_counts": counts,
        "qualification_decisions_validated": total,
        "full_operational_review_complete": False,
        "production_authorization": False,
        "production_apply_authorized": False,
        "ready_for_stage1_requalification": True,
    }


def _code(value: Any) -> str:
    text = "" if value is None else str(value).lower() if isinstance(value, bool) else str(value)
    return f"{chr(96)}{text}{chr(96)}"


def _human_lines(record: Mapping[str, Any]) -> list[str]:
    lines = [
        f"- Allowed decisions: {_code(', '.join(record['allowed_decisions']))}",
        "- human_input.decision: **BLANK**",
        "- human_input.reason: **BLANK**",
    ]
    if "target_node_id" in record["human_input"]:
        lines.append(
            "- human_input.target_node_id: **BLANK** (required only for REUSE)"
        )
    return lines + [""]


def render_qualification_review_markdown(
    packet: Mapping[str, Any],
) -> str:
    """Render display context for the seven blank authoritative records."""
    source_binding = packet["source_review_packet"]
    lines = [
        "# Phase 3F Stage 1 Qualification Review Slice",
        "",
        "> **QUALIFICATION ONLY.** This is not the full operational review,",
        "> is not Production authorization, and does not review the other 198 candidates.",
        "",
        f"- Review scope: {_code(packet['review_scope'])}",
        f"- Packet ID: {_code(packet['packet_id'])}",
        f"- Immutable packet SHA256: {_code(packet['immutable_packet_sha256'])}",
        f"- Full packet: {_code(source_binding['packet_id'])}",
        (
            f"- Run / source: {_code(packet['run']['run_id'])} / "
            f"{_code(packet['source']['source_id'])}"
        ),
        f"- Frozen source SHA256: {_code(packet['source']['source_sha256'])}",
        "- All seven decisions are blank; advisory fields are non-authorizing.",
        "- Edit only human_completion.reviewer and human_input fields in the JSON packet.",
        "",
        "## Claims (3)",
        "",
    ]
    for record in packet["claims"]:
        content = record["content"]
        evidence = content.get("evidence_validation") or {}
        admission = content.get("semantic_admission") or {}
        lines += [
            f"### {_code(record['candidate_id'])}",
            "",
            f"- Content SHA256: {_code(record['content_sha256'])}",
            f"- Statement: {content.get('statement')}",
            f"- Evidence pointer: {_code(content.get('evidence_pointer'))}",
            f"- Evidence excerpt: {content.get('evidence_excerpt')}",
            (
                f"- Evidence binding: fidelity={_code(evidence.get('fidelity_status'))}, "
                f"bound={_code(evidence.get('bound'))}"
            ),
            (
                f"- Semantic guard: {_code(admission.get('overall_guard_disposition'))}; "
                f"reasons={_code(', '.join(admission.get('guard_reasons') or []))}"
            ),
            (
                f"- Duplicate reference: {_code(content.get('duplicate_of_claim_id'))}; "
                f"reconciliation={_code(content.get('duplicate_reconciliation'))}"
            ),
            (
                f"- Non-authorizing advisory: "
                f"{_code(content.get('advisory_recommendation'))} — "
                f"{content.get('advisory_recommendation_reason')}"
            ),
            *_human_lines(record),
        ]

    lines += ["## Nodes (3)", ""]
    for record in packet["nodes"]:
        content = record["content"]
        resolution = content.get("exact_production_resolution") or {}
        collisions = content.get("collision_diagnostics") or {}
        aliases = content.get("proposed_aliases") or []
        supporting = content.get("supporting_claim_ids") or []
        targets = resolution.get("candidate_targets") or []
        target_text = "; ".join(
            (
                f"{item.get('node_id')} | {item.get('canonical_name')} | "
                f"{item.get('primary_type')} | {item.get('status')}"
            )
            for item in targets
        ) or "none"
        lines += [
            f"### {_code(record['candidate_id'])} — {content.get('proposed_name')}",
            "",
            f"- Content SHA256: {_code(record['content_sha256'])}",
            f"- Proposed type: {_code(content.get('proposed_type'))}",
            (
                "- Proposed aliases (immutable node identity): "
                f"{_code(', '.join(aliases) if aliases else 'none')}"
            ),
            f"- Prospective node ID: {_code(content.get('prospective_node_id'))}",
            (
                f"- Supporting Claim IDs ({len(supporting)}): "
                f"{_code(', '.join(supporting) if supporting else 'none')}"
            ),
            f"- Exact Production resolution: {_code(target_text)}",
            (
                "- Production collision IDs: "
                f"{_code(', '.join(collisions.get('production_nocase_or_nfkc_target_ids') or []) or 'none')}"
            ),
            (
                "- Prospective ID already exists: "
                f"{_code(collisions.get('prospective_node_id_exists'))}"
            ),
            (
                f"- Non-authorizing advisory: "
                f"{_code(content.get('advisory_suggestion'))} — "
                f"{content.get('advisory_suggestion_reason')}"
            ),
            *_human_lines(record),
        ]

    relation = packet["relations"][0]
    content = relation["content"]
    context = packet["production_display_context"]
    parent = context["resolved_nodes"]["parent_placement_target"]
    lines += [
        "## Parent placement (1)",
        "",
        f"### {_code(relation['candidate_id'])}",
        "",
        f"- Content SHA256: {_code(relation['content_sha256'])}",
        (
            f"- Child candidate: {_code(content['child_node_candidate_id'])} "
            "(超节点)"
        ),
        f"- Prospective child node ID: {_code(content['prospective_child_node_id'])}",
        f"- Relation: {_code(content['relation_type'])}",
        f"- Parent node ID: {_code(parent['node_id'])}",
        f"- Canonical parent name: {_code(parent['canonical_name'])}",
        f"- Parent primary type: {_code(parent['primary_type'])}",
        f"- Parent status: {_code(parent['status'])}",
        f"- Display-context resolution: {_code(context['resolution_method'])}",
        f"- Frozen Production SHA256: {_code(context['production_sha256'])}",
        (
            "- Conditionality: relation CREATE is valid only when the child "
            "Node decision is explicitly CREATE."
        ),
        *_human_lines(relation),
        "## Completion boundary",
        "",
        (
            "A valid completion covers exactly these seven candidates. It cannot "
            "set full_operational_review_complete or production_authorization true."
        ),
        "",
    ]
    return "\n".join(lines)


def _binding(path: Path, run_root: Path) -> dict[str, Any]:
    return {
        "relative_path": _repo_relative(path, run_root),
        "file_sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def build_qualification_manifest(
    packet_path: str | Path,
    view_path: str | Path,
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> dict[str, Any]:
    """Bind the blank slice, its view, and the immutable full packet."""
    packet_path, view_path, run_root = (
        Path(packet_path),
        Path(view_path),
        Path(run_root),
    )
    packet = read_review_packet(packet_path)
    validate_blank_qualification_packet(
        packet, source_packet_path, run_root, production_path
    )
    body = {
        "document_type": MANIFEST_DOCUMENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "manifest_status": "READY_FOR_HUMAN_QUALIFICATION_INPUT",
        "review_scope": REVIEW_SCOPE,
        "source_review_packet": copy.deepcopy(packet["source_review_packet"]),
        "qualification_review_packet": {
            **_binding(packet_path, run_root),
            "packet_id": packet["packet_id"],
            "immutable_packet_sha256": packet["immutable_packet_sha256"],
        },
        "qualification_review_view": _binding(view_path, run_root),
        "selected_candidate_ids": copy.deepcopy(
            packet["selection_contract"]["selected_candidate_ids"]
        ),
        "summary": copy.deepcopy(packet["summary"]),
        "production_display_context": copy.deepcopy(
            packet["production_display_context"]
        ),
        "safety": {
            "human_decisions_present": False,
            "full_operational_review_complete": False,
            "production_authorization": False,
            "production_changed": False,
            "cloud_llm_calls": 0,
            "local_llm_calls": 0,
        },
    }
    digest = canonical_sha256(body)
    return {
        **body,
        "manifest_id": f"QUALIFICATION_REVIEW_MANIFEST_{digest[:16].upper()}",
        "manifest_sha256": digest,
    }


def validate_qualification_manifest(
    manifest: Mapping[str, Any],
    packet_path: str | Path,
    view_path: str | Path,
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> None:
    expected = build_qualification_manifest(
        packet_path,
        view_path,
        source_packet_path,
        run_root,
        production_path,
    )
    _require(dict(manifest) == expected, "QUALIFICATION_MANIFEST_INVALID")


def write_blank_qualification_artifacts(
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
    packet_path: str | Path,
    view_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Write deterministic LF-only artifacts with every decision blank."""
    packet_path, view_path, manifest_path = (
        Path(packet_path),
        Path(view_path),
        Path(manifest_path),
    )
    packet = build_blank_qualification_packet(
        source_packet_path, run_root, production_path
    )
    validate_blank_qualification_packet(
        packet, source_packet_path, run_root, production_path
    )
    for path in (packet_path, view_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    with packet_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n"
        )
    with view_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_qualification_review_markdown(packet))
    manifest = build_qualification_manifest(
        packet_path,
        view_path,
        source_packet_path,
        run_root,
        production_path,
    )
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n"
        )
    validate_qualification_manifest(
        manifest,
        packet_path,
        view_path,
        source_packet_path,
        run_root,
        production_path,
    )
    return packet


_AUTHORIZATION_FIELDS = {
    "document_type",
    "schema_version",
    "review_scope",
    "packet_id",
    "immutable_packet_sha256",
    "reviewer",
    "authority_source",
    "full_operational_review_complete",
    "production_authorization",
    "unselected_candidates_reviewed",
    "claims",
    "nodes",
    "relations",
}


def apply_qualification_authorization(
    blank_packet: Mapping[str, Any],
    authorization: Mapping[str, Any],
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply only explicitly supplied, packet-bound human-input fields."""
    validate_blank_qualification_packet(
        blank_packet, source_packet_path, run_root, production_path
    )
    _require(
        isinstance(authorization, dict)
        and set(authorization) == _AUTHORIZATION_FIELDS,
        "AUTHORIZATION_STRUCTURE_INVALID",
    )
    for field, expected in (
        ("document_type", "phase3f_stage1_qualification_human_authorization"),
        ("schema_version", SCHEMA_VERSION),
        ("review_scope", REVIEW_SCOPE),
        ("packet_id", blank_packet["packet_id"]),
        (
            "immutable_packet_sha256",
            blank_packet["immutable_packet_sha256"],
        ),
        ("full_operational_review_complete", False),
        ("production_authorization", False),
        ("unselected_candidates_reviewed", False),
    ):
        _require(
            authorization.get(field) == expected,
            "AUTHORIZATION_BINDING_INVALID",
            field,
        )
    for field in ("reviewer", "authority_source"):
        value = authorization.get(field)
        _require(
            isinstance(value, str) and value.strip() == value and value,
            "AUTHORIZATION_ATTRIBUTION_INVALID",
            field,
        )

    completed = copy.deepcopy(blank_packet)
    completed["human_completion"]["reviewer"] = authorization["reviewer"]
    for group, expected_ids in SELECTED_CANDIDATES.items():
        decisions = authorization.get(group)
        _require(
            isinstance(decisions, list)
            and [item.get("candidate_id") for item in decisions]
            == list(expected_ids),
            "AUTHORIZATION_CANDIDATE_SET_INVALID",
            group,
        )
        fields = {"candidate_id", *_HUMAN_FIELDS[group]}
        for target, supplied in zip(completed[group], decisions, strict=True):
            _require(
                isinstance(supplied, dict) and set(supplied) == fields,
                "AUTHORIZATION_DECISION_STRUCTURE_INVALID",
                target["candidate_id"],
            )
            target["human_input"].update(
                {
                    field: supplied[field]
                    for field in _HUMAN_FIELDS[group]
                }
            )
    validation = validate_completed_qualification_packet(
        completed, source_packet_path, run_root, production_path
    )
    validation["authority_source"] = authorization["authority_source"]
    return completed, validation


def write_completed_qualification_artifacts(
    blank_packet_path: str | Path,
    authorization_path: str | Path,
    completed_packet_path: str | Path,
    receipt_path: str | Path,
    source_packet_path: str | Path,
    run_root: str | Path,
    production_path: str | Path,
) -> dict[str, Any]:
    """Persist a validated completed copy while preserving the blank input."""
    blank_packet_path = Path(blank_packet_path)
    authorization_path = Path(authorization_path)
    completed_packet_path = Path(completed_packet_path)
    receipt_path = Path(receipt_path)
    run_root = Path(run_root)
    blank = read_review_packet(blank_packet_path)
    authorization = read_review_packet(authorization_path)
    completed, validation = apply_qualification_authorization(
        blank,
        authorization,
        source_packet_path,
        run_root,
        production_path,
    )
    completed_packet_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with completed_packet_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(
            json.dumps(
                completed, ensure_ascii=False, indent=2, allow_nan=False
            )
            + "\n"
        )
    body = {
        **validation,
        "authorization_artifact": _binding(authorization_path, run_root),
        "blank_qualification_packet": _binding(blank_packet_path, run_root),
        "completed_qualification_packet": {
            **_binding(completed_packet_path, run_root),
            "completed_packet_sha256": validation["completed_packet_sha256"],
        },
        "human_decisions_present": True,
        "stage1_requalification_executed": False,
        "production_changed": False,
    }
    digest = canonical_sha256(body)
    receipt = {
        **body,
        "receipt_id": f"QUALIFICATION_COMPLETION_{digest[:16].upper()}",
        "receipt_sha256": digest,
    }
    with receipt_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(
            json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n"
        )
    return receipt
