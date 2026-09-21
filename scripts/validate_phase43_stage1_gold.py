"""Validate the authorized frozen 120-case binding without reading hidden truth."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_MANIFEST_SHA256 = "d833b8a6af622630c5113da3149af50fba6c4d46de59fa7ec0d178dde1a22385"
BINDING_FIELDS = (
    "case_id", "partition", "candidate_record_hash", "candidate_outcome_hash",
    "source_sha256", "evidence_hash", "snapshot_hash", "context_hash",
    "final_qualification_state", "qualification_route", "human_exception_result",
    "human_sample_result",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    body = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def validate(manifest_path: Path, binding_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    binding_path = binding_path.resolve(strict=True)
    manifest_hash = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binding_hash = sha256(binding_path)
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    cases = list(manifest.get("cases") or [])
    bound_cases = list(binding.get("cases") or [])
    by_id = {case.get("case_id"): case for case in bound_cases}
    checks = {
        "manifest_sha256": manifest_hash == EXPECTED_MANIFEST_SHA256,
        "gold_state": manifest.get("GOLD_STATE") == "HUMAN_AUTHORIZED_FROZEN_GOLD",
        "human_authority": manifest.get("FINAL_GOLD_FREEZE_AUTHORITY") == "HUMAN_USER",
        "manifest_case_count": len(cases) == manifest.get("FROZEN_GOLD_CASE_COUNT") == 120,
        "binding_case_count": len(bound_cases) == binding.get("CASE_COUNT") == 120,
        "unique_case_ids": len({case.get("case_id") for case in cases}) == 120
            and len(by_id) == 120,
        "partition_counts": (
            sum(case.get("partition") == "DEVELOPMENT" for case in cases) == 90
            and sum(case.get("partition") == "HOLDOUT" for case in cases) == 30
        ),
        "binding_manifest_sha256": (
            manifest.get("QUALIFICATION_BINDING_MANIFEST_SHA256") == binding_hash
        ),
        "qualification_pass": (
            binding.get("COMPLETE_120_CASE_QUALIFICATION") == "PASS"
            and binding.get("EXACT_CASE_BINDING_VALIDATION") == "PASS"
        ),
        "outcome_hashes": all(
            canonical_sha256(case.get("candidate_expected_outcome"))
            == case.get("candidate_expected_outcome_sha256")
            == case.get("candidate_outcome_hash")
            for case in cases
        ),
        "exact_case_bindings": all(
            case.get("case_id") in by_id
            and all(case.get(field) == by_id[case["case_id"]].get(field)
                    for field in BINDING_FIELDS)
            for case in cases
        ),
        "all_final_states_pass": all(
            case.get("final_qualification_state") == "PASS" for case in cases
        ),
    }
    passed = sum(
        all(checks.values()) and case.get("case_id") in by_id
        and all(case.get(field) == by_id[case["case_id"]].get(field)
                for field in BINDING_FIELDS)
        for case in cases
    )
    return {
        "document_type": "phase43_stage1_frozen_gold_regression",
        "status": "PASS" if all(checks.values()) and passed == 120 else "FAIL",
        "gold_state": manifest.get("GOLD_STATE"),
        "manifest_sha256": manifest_hash,
        "binding_manifest_sha256": binding_hash,
        "cases_total": len(cases), "cases_passed": passed,
        "development_cases": sum(case.get("partition") == "DEVELOPMENT" for case in cases),
        "holdout_cases": sum(case.get("partition") == "HOLDOUT" for case in cases),
        "checks": checks,
        "hidden_truth_read": False,
        "candidate_outcomes_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("binding", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.manifest, args.binding)
    body = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(body, encoding="utf-8", newline="\n")
    print(body, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
