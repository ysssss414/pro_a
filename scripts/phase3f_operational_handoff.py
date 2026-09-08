#!/usr/bin/env python3
"""Build generic Phase 3F operational-review handoff artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pro_a.phase3f_operational_handoff import write_operational_handoff_artifacts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--completed-packet", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--completion-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--completed-artifact",
        action="append",
        default=[],
        metavar="ROLE=PATH",
        help="Additional completed artifact sealed by the completion receipt.",
    )
    return parser


def _completed_artifacts(values: list[str]) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for value in values:
        role, separator, raw_path = value.partition("=")
        if not separator or not role or not raw_path or role in artifacts:
            raise ValueError(f"invalid --completed-artifact: {value}")
        artifacts[role] = Path(raw_path)
    return artifacts


def main() -> int:
    args = _parser().parse_args()
    artifacts = write_operational_handoff_artifacts(
        args.output_dir,
        completed_packet_path=args.completed_packet,
        authorization_path=args.authorization,
        completion_receipt_path=args.completion_receipt,
        run_root=args.run_root,
        production_path=args.production,
        repository_root=args.repository_root,
        additional_completed_artifacts=_completed_artifacts(args.completed_artifact),
    )
    receipt = artifacts["operational_handoff_receipt.json"]
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt_id": receipt["receipt_id"],
                "receipt_sha256": receipt["receipt_sha256"],
                "promotion_payload_id": receipt["promotion_payload_id"],
                "promotion_payload_sha256": receipt["promotion_payload_sha256"],
                "mapping_counts": receipt["mapping_counts"],
                "operation_counts": receipt["operation_counts"],
                "production_changed": receipt["production_changed"],
                "llm_calls": receipt["llm_calls"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
