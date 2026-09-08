#!/usr/bin/env python3
"""Generate deterministic public-safe Phase 3F Stage 1 audit artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pro_a.phase3f_public_sanitization import write_public_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--review-packet", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--handoff-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    artifacts = write_public_audit(
        repository_root=args.repository_root,
        review_packet_path=args.review_packet,
        qualification_root=args.qualification_root,
        handoff_root=args.handoff_root,
        output_dir=args.output_dir,
    )
    manifest = artifacts["public_audit_manifest.json"]
    print(json.dumps({
        "status": "PASS",
        "artifact_count": len(artifacts),
        "manifest_id": manifest["artifact_id"],
        "manifest_sha256": manifest["artifact_sha256"],
        "source_text_included": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
