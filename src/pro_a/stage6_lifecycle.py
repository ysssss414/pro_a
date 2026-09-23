"""Deterministic Stage 2 lifecycle closure construction and validation."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .production_promotion import canonical_sha256, sha256_file


CONTRACT_VERSION = "phase43-stage6-lifecycle-closure-v1"
CAPACITY_POLICY_VERSION = "phase43-stage6-lifecycle-capacity-v1"
CLOSURE_ID = "phase43-stage2-foundation-v1"
CLOSURE_SHA256 = "2516386da0e629102b60362553a0c63420df69f45fdd02e888757cd87ccf4feb"
POPULATION_SHA256 = "b363748e9aa05be4d66d7ff5c3d0008e9a80df29a25741f72d60c7c32c983b51"
SOURCE_PACKET_SHA256 = "06006a1c98247f1803dac9cdcd0f10ade5d84beddc56a12e3768e5a9e5bfc66c"
PRODUCTION_SHA256 = "6e5a303ccee9c192c350c2550cc232649e56ffee939b7a09cd6b170cc1c8fba1"
HUMAN_AUTHORIZATION_FILE_SHA256 = "23fa6c94d55caf7ef8cfc3291528d3d41a06948460b852d7418c68f572bf014f"
SEALED_REVIEW_A_SHA256 = "9e5735f73a039c58b598ba48d1d78d5bf434c22a8ce6c15e464f22c8aa5f9edf"
SEALED_REVIEW_B_SHA256 = "f32d03eaf14494486a7d0dc89e2f20ccbe9ad950a69b1d80d0b16fb37ebdb08f"
RECONCILIATION_SHA256 = "3631ead5334528a174a97683105fe5a1125b6e90fe9748f92c787be9c6b58b9b"
RESIDUAL_SAMPLE_SHA256 = "44051e472043f12bb416e7947d4f67a0f16d8785a4154d963e96726bbaed09a3"

SOURCE_FILES = (
    "docs/phase43_stage2_review_population_manifest.json",
    "docs/phase43_stage2_human_authorization.json",
    "docs/phase43_stage2_ai_review_reconciliation.json",
    "docs/phase43_stage2_ai_review_a.json",
    "docs/phase43_stage2_ai_review_b.json",
    "docs/phase43_stage2_final_human_qualification_receipt.json",
)


class LifecycleClosureError(ValueError):
    """The frozen Stage 2 authority cannot support a lifecycle closure."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise LifecycleClosureError(code)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def closure_file_bytes(value: Mapping[str, Any]) -> bytes:
    return canonical_bytes(value) + b"\n"


def _verify_output_hash(record: Mapping[str, Any]) -> None:
    expected = record.get("output_record_sha256")
    _require(isinstance(expected, str), "AI_OUTPUT_HASH_MISSING")
    payload = {key: value for key, value in record.items() if key != "output_record_sha256"}
    _require(canonical_sha256(payload) == expected, "AI_OUTPUT_HASH_MISMATCH")


def _source_authority() -> dict[str, Any]:
    return {
        "population_sha256": POPULATION_SHA256,
        "source_packet_immutable_sha256": SOURCE_PACKET_SHA256,
        "human_authorization_file_sha256": HUMAN_AUTHORIZATION_FILE_SHA256,
        "sealed_review_a_sha256": SEALED_REVIEW_A_SHA256,
        "sealed_review_b_sha256": SEALED_REVIEW_B_SHA256,
        "reconciliation_sha256": RECONCILIATION_SHA256,
        "residual_sample_sha256": RESIDUAL_SAMPLE_SHA256,
        "production_baseline_sha256": PRODUCTION_SHA256,
    }


def build_closure(repository: Path) -> dict[str, Any]:
    """Build the exact 274-row closure from tracked Stage 2 evidence."""
    root = Path(repository)
    paths = {name: root / name for name in SOURCE_FILES}
    manifest = _read(paths[SOURCE_FILES[0]])
    authorization = _read(paths[SOURCE_FILES[1]])
    reconciliation = _read(paths[SOURCE_FILES[2]])
    review_a = _read(paths[SOURCE_FILES[3]])
    review_b = _read(paths[SOURCE_FILES[4]])
    final_receipt = _read(paths[SOURCE_FILES[5]])

    _require(sha256_file(paths[SOURCE_FILES[1]]) == HUMAN_AUTHORIZATION_FILE_SHA256,
             "HUMAN_AUTHORIZATION_FILE_MISMATCH")
    _require(manifest.get("total_items") == 274, "POPULATION_COUNT")
    _require(manifest.get("ordered_population_sha256") == POPULATION_SHA256,
             "POPULATION_IDENTITY")
    _require(canonical_sha256(manifest.get("items")) == POPULATION_SHA256,
             "POPULATION_CONTENT")
    _require(manifest.get("native_immutable_packet_sha256") == SOURCE_PACKET_SHA256,
             "SOURCE_PACKET_IDENTITY")
    _require(manifest.get("production_sha_before") == PRODUCTION_SHA256,
             "PRODUCTION_BASELINE_IDENTITY")

    bindings = authorization.get("frozen_file_bindings") or {}
    expected_bindings = {
        "review_A/review.json": SEALED_REVIEW_A_SHA256,
        "review_B/review.json": SEALED_REVIEW_B_SHA256,
        "reconciliation.json": RECONCILIATION_SHA256,
        "residual_sample.json": RESIDUAL_SAMPLE_SHA256,
    }
    _require(all(bindings.get(key) == value for key, value in expected_bindings.items()),
             "SEALED_AUTHORITY_BINDING")
    _require(authorization.get("population_sha256") == POPULATION_SHA256,
             "HUMAN_POPULATION_BINDING")
    _require(authorization.get("reviewer") == "HUMAN_USER", "HUMAN_REVIEWER")
    _require(authorization.get("expanded_review_required") is False, "REVIEW_EXPANSION")
    _require(authorization.get("residual_substantive_errors") == 0,
             "RESIDUAL_ERROR_REPORT")
    _require(authorization.get("production_apply_authorized") is False,
             "PRODUCTION_APPLY_AUTHORITY")

    summary = reconciliation.get("summary") or {}
    _require(summary.get("result") == "PASS", "RECONCILIATION_RESULT")
    _require(summary.get("population_sha256") == POPULATION_SHA256,
             "RECONCILIATION_POPULATION")
    _require(summary.get("total_reviewed") == 274, "RECONCILIATION_COUNT")
    _require(summary.get("mandatory_unique") == 76, "MANDATORY_COUNT")
    _require(summary.get("sampled_items") == 29, "SAMPLE_COUNT")
    _require(summary.get("total_human_items") == 105, "HUMAN_COUNT")
    _require(summary.get("residual_eligible") == 198, "RESIDUAL_ELIGIBLE_COUNT")
    reviewer_results = summary.get("reviewer_results") or {}
    _require((reviewer_results.get("A") or {}).get("sealed_review_sha256") == SEALED_REVIEW_A_SHA256,
             "SEALED_REVIEW_A_BINDING")
    _require((reviewer_results.get("B") or {}).get("sealed_review_sha256") == SEALED_REVIEW_B_SHA256,
             "SEALED_REVIEW_B_BINDING")

    population = manifest["items"]
    population_ids = [str(row["candidate_id"]) for row in population]
    _require(len(population_ids) == len(set(population_ids)) == 274, "POPULATION_UNIQUENESS")
    population_by_id = {str(row["candidate_id"]): row for row in population}
    human_rows = authorization.get("decisions") or []
    human_by_id = {str(row["item_id"]): row for row in human_rows}
    recon_rows = reconciliation.get("items") or []
    recon_by_id = {str(row["candidate_id"]): row for row in recon_rows}
    a_by_id = {str(row["candidate_id"]): row for row in review_a.get("records") or []}
    b_by_id = {str(row["candidate_id"]): row for row in review_b.get("records") or []}
    _require(len(human_by_id) == len(human_rows) == 105, "HUMAN_SCOPE_UNIQUENESS")
    _require(set(recon_by_id) == set(a_by_id) == set(b_by_id) == set(population_ids),
             "AI_EXACT_COVERAGE")
    _require(set(human_by_id) <= set(population_ids), "HUMAN_SCOPE_OUTSIDE_POPULATION")

    mandatory_ids = {key for key, row in recon_by_id.items() if row.get("mandatory_human") is True}
    sample_ids = set((reconciliation.get("residual_sample") or {}).get("selected_ids") or [])
    _require(len(mandatory_ids) == 76 and len(sample_ids) == 29, "HUMAN_SCOPE_COUNTS")
    _require(not mandatory_ids & sample_ids, "HUMAN_SCOPE_OVERLAP")
    _require(set(human_by_id) == mandatory_ids | sample_ids, "HUMAN_SCOPE_IDENTITY")

    for record in (*a_by_id.values(), *b_by_id.values()):
        _verify_output_hash(record)
        item = population_by_id[str(record["candidate_id"])]
        _require(record.get("candidate_type") == item.get("candidate_type"), "CANDIDATE_TYPE_BINDING")
        _require(record.get("content_sha256") == item.get("content_sha256"), "CANDIDATE_CONTENT_BINDING")

    rows: list[dict[str, Any]] = []
    for candidate_id in sorted(population_ids):
        item = population_by_id[candidate_id]
        recon = recon_by_id[candidate_id]
        left, right = a_by_id[candidate_id], b_by_id[candidate_id]
        common = {
            "closure_id": CLOSURE_ID,
            "candidate_id": candidate_id,
            "candidate_type": item["candidate_type"],
            "content_sha256": item["content_sha256"],
            "source_packet_immutable_sha256": SOURCE_PACKET_SHA256,
            "population_sha256": POPULATION_SHA256,
            "mandatory_human": candidate_id in mandatory_ids,
            "residual_sample": candidate_id in sample_ids,
            "production_authorized": False,
            "artifact_id": None,
        }
        if candidate_id in human_by_id:
            decision = human_by_id[candidate_id]
            _require(decision.get("reviewer") == "HUMAN_USER", "HUMAN_ITEM_REVIEWER")
            _require(decision.get("native_content_sha256") == item["content_sha256"],
                     "HUMAN_ITEM_CONTENT_BINDING")
            native_input = decision.get("human_input") or {}
            _require(bool(native_input.get("decision")), "HUMAN_NATIVE_DECISION")
            payload = {
                **common,
                "resolution_source": "HUMAN_USER_QUALIFICATION",
                "native_decision": native_input["decision"],
                "native_target_id": native_input.get("target_id") or None,
                "authorized_decision": decision["human_user_decision"],
                "followup_required": native_input["decision"] in {"DEFER", "KEEP_NEEDS_REVIEW"},
                "closure_reason": "MANDATORY_HUMAN_QUALIFIED" if candidate_id in mandatory_ids
                                  else "RESIDUAL_SAMPLE_HUMAN_QUALIFIED",
                "human_authorization_id": canonical_sha256({
                    "authorization_file_sha256": HUMAN_AUTHORIZATION_FILE_SHA256,
                    "candidate_id": candidate_id,
                }),
                "human_item_attribution": {
                    "reviewer": "HUMAN_USER",
                    "authorization_file_sha256": HUMAN_AUTHORIZATION_FILE_SHA256,
                },
                "ai_policy_attribution": None,
            }
        else:
            _require(recon.get("mandatory_human") is False, "AI_MANDATORY_CONFLICT")
            _require(not recon.get("mandatory_triggers"), "AI_TRIGGER_CONFLICT")
            _require(recon.get("comparison") in {
                "A_B_SUBSTANTIVE_AGREEMENT", "A_B_EXACT_AGREEMENT"
            }, "AI_AGREEMENT_REQUIRED")
            _require(left.get("native_decision") == right.get("native_decision"),
                     "AI_NATIVE_DECISION_CONFLICT")
            payload = {
                **common,
                "resolution_source": "AI_POLICY_QUALIFICATION",
                "native_decision": left["native_decision"],
                "native_target_id": (left.get("proposed_operation") or {}).get("target_id") or None,
                "authorized_decision": None,
                "followup_required": left["native_decision"] in {"DEFER", "KEEP_NEEDS_REVIEW"},
                "closure_reason": "A_B_POLICY_AGREEMENT_NO_MANDATORY_TRIGGER",
                "human_authorization_id": None,
                "human_item_attribution": None,
                "ai_policy_attribution": {
                    "comparison": recon["comparison"],
                    "review_a_output_record_sha256": left["output_record_sha256"],
                    "review_b_output_record_sha256": right["output_record_sha256"],
                },
            }
        payload["resolution_sha256"] = canonical_sha256(payload)
        rows.append(payload)

    counts = Counter(row["resolution_source"] for row in rows)
    _require(counts == {"HUMAN_USER_QUALIFICATION": 105, "AI_POLICY_QUALIFICATION": 169},
             "RESOLUTION_SOURCE_COUNTS")
    _require(all(row["human_item_attribution"] is None and row["human_authorization_id"] is None
                 for row in rows if row["resolution_source"] == "AI_POLICY_QUALIFICATION"),
             "AI_HUMAN_ATTRIBUTION_FORBIDDEN")
    receipt_sha = final_receipt.get("receipt_sha256")
    _require(isinstance(receipt_sha, str) and len(receipt_sha) == 64, "FINAL_RECEIPT_BINDING")
    result: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "closure_id": CLOSURE_ID,
        "capacity_policy_version": CAPACITY_POLICY_VERSION,
        "authority": {**_source_authority(), "final_human_qualification_receipt_sha256": receipt_sha},
        "summary": {
            "population": 274,
            "historical_lifecycle_closed": 274,
            "human_user_qualified": 105,
            "ai_policy_closed": 169,
            "mandatory_human": 76,
            "residual_sample": 29,
            "production_authorized": False,
        },
        "resolutions": rows,
        "production_authorized": False,
    }
    result["closure_sha256"] = canonical_sha256(result)
    validate_closure(result)
    return result


def validate_closure(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate immutable structure and all logical hashes without source files."""
    _require(value.get("contract_version") == CONTRACT_VERSION, "CLOSURE_CONTRACT")
    _require(value.get("closure_id") == CLOSURE_ID, "CLOSURE_ID")
    _require(value.get("capacity_policy_version") == CAPACITY_POLICY_VERSION,
             "CAPACITY_POLICY")
    _require(value.get("production_authorized") is False, "PRODUCTION_AUTHORITY")
    authority = value.get("authority") or {}
    for key, expected in _source_authority().items():
        _require(authority.get(key) == expected, "AUTHORITY_" + key.upper())
    rows = value.get("resolutions") or []
    _require(len(rows) == 274, "CLOSURE_ROW_COUNT")
    _require([row.get("candidate_id") for row in rows] ==
             sorted(row.get("candidate_id") for row in rows), "CLOSURE_ORDER")
    _require(len({row.get("candidate_id") for row in rows}) == 274, "CLOSURE_UNIQUENESS")
    for row in rows:
        expected = row.get("resolution_sha256")
        payload = {key: item for key, item in row.items() if key != "resolution_sha256"}
        _require(canonical_sha256(payload) == expected, "RESOLUTION_HASH")
        _require(row.get("population_sha256") == POPULATION_SHA256, "ROW_POPULATION")
        _require(row.get("source_packet_immutable_sha256") == SOURCE_PACKET_SHA256,
                 "ROW_SOURCE_PACKET")
        _require(row.get("production_authorized") is False, "ROW_PRODUCTION_AUTHORITY")
        if row.get("resolution_source") == "AI_POLICY_QUALIFICATION":
            _require(row.get("human_authorization_id") is None and
                     row.get("human_item_attribution") is None,
                     "AI_HUMAN_ATTRIBUTION_FORBIDDEN")
    counts = Counter(row.get("resolution_source") for row in rows)
    _require(counts == {"HUMAN_USER_QUALIFICATION": 105, "AI_POLICY_QUALIFICATION": 169},
             "CLOSURE_SOURCE_COUNTS")
    expected_closure = value.get("closure_sha256")
    payload = {key: item for key, item in value.items() if key != "closure_sha256"}
    _require(canonical_sha256(payload) == expected_closure, "CLOSURE_HASH")
    _require(expected_closure == CLOSURE_SHA256, "CLOSURE_AUTHORITY")
    return {
        "closure_id": CLOSURE_ID,
        "closure_sha256": expected_closure,
        "population": 274,
        "human_user_qualified": 105,
        "ai_policy_closed": 169,
    }


def build_source_manifest(repository: Path, closure: Mapping[str, Any],
                          builder_paths: list[Path]) -> dict[str, Any]:
    root = Path(repository)
    sources = [{"path": name, "file_sha256": sha256_file(root / name)} for name in SOURCE_FILES]
    builders = [{"path": path.relative_to(root).as_posix(), "file_sha256": sha256_file(path)}
                for path in builder_paths]
    return {
        "document_type": "phase43_stage6_lifecycle_source_manifest",
        "contract_version": CONTRACT_VERSION,
        "closure_id": CLOSURE_ID,
        "closure_sha256": closure["closure_sha256"],
        "authority": {
            **_source_authority(),
            "final_human_qualification_receipt_sha256":
                closure["authority"]["final_human_qualification_receipt_sha256"],
        },
        "tracked_sources": sources,
        "builders": builders,
        "source_files_are_authority_bindings_not_rewritten_sealed_files": True,
    }


def immutable_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _require(path.read_bytes() == content, "IMMUTABLE_OUTPUT_CONFLICT")
        return
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
