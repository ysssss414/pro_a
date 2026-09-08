#!/usr/bin/env python3
"""Build the Phase 3F Stage 1 qualification-only handoff artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pro_a.phase3f_handoff_requalification import (
    write_requalification_artifacts,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--source-packet", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = args.qualification_root
    artifacts = write_requalification_artifacts(
        args.output_dir,
        repository_commit=args.repository_commit,
        blank_packet_path=root / "qualification_review_packet.json",
        completed_packet_path=root / "qualification_review_packet.completed.json",
        authorization_path=root / "qualification_review_human_authorization.json",
        completion_receipt_path=root / "qualification_review_completion_receipt.json",
        qualification_manifest_path=root / "qualification_review_manifest.json",
        qualification_view_path=root / "qualification_review_view.md",
        source_packet_path=args.source_packet,
        run_root=args.run_root,
        production_path=args.production,
        repository_root=args.repository_root,
    )
    receipt = artifacts["stage1_requalification_receipt.json"]
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt_id": receipt["receipt_id"],
                "receipt_sha256": receipt["receipt_sha256"],
                "promotion_payload_id": receipt["promotion_payload_id"],
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
