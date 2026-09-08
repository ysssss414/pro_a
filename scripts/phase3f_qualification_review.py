from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pro_a.phase3f_qualification_review import (  # noqa: E402
    read_review_packet,
    validate_blank_qualification_packet,
    validate_completed_qualification_packet,
    write_blank_qualification_artifacts,
    write_completed_qualification_artifacts,
)


RUN_ROOT = ROOT / "workspace" / "phase3e2sl6" / "operational_run"
PRODUCTION = ROOT / "workspace" / "pro_a.db"
SOURCE_PACKET = (
    ROOT
    / "workspace"
    / "phase3f_stage1_review_completion"
    / "operational_review_packet.json"
)
OUTPUT_ROOT = ROOT / "workspace" / "phase3f_stage1_qualification_review"
PACKET = OUTPUT_ROOT / "qualification_review_packet.json"
VIEW = OUTPUT_ROOT / "qualification_review_view.md"
MANIFEST = OUTPUT_ROOT / "qualification_review_manifest.json"
AUTHORIZATION = OUTPUT_ROOT / "qualification_review_human_authorization.json"
COMPLETED_PACKET = OUTPUT_ROOT / "qualification_review_packet.completed.json"
COMPLETION_RECEIPT = OUTPUT_ROOT / "qualification_review_completion_receipt.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or validate the Phase 3F qualification-only review slice."
    )
    parser.add_argument(
        "action",
        choices=(
            "build",
            "apply-authorization",
            "validate-blank",
            "validate-completed",
        ),
    )
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    parser.add_argument("--production", type=Path, default=PRODUCTION)
    parser.add_argument("--source-packet", type=Path, default=SOURCE_PACKET)
    parser.add_argument("--packet", type=Path, default=PACKET)
    parser.add_argument("--view", type=Path, default=VIEW)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--authorization", type=Path, default=AUTHORIZATION)
    parser.add_argument("--completed-packet", type=Path, default=COMPLETED_PACKET)
    parser.add_argument("--completion-receipt", type=Path, default=COMPLETION_RECEIPT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "build":
        packet = write_blank_qualification_artifacts(
            source_packet_path=args.source_packet,
            run_root=args.run_root,
            production_path=args.production,
            packet_path=args.packet,
            view_path=args.view,
            manifest_path=args.manifest,
        )
        result = validate_blank_qualification_packet(
            packet,
            args.source_packet,
            args.run_root,
            args.production,
        )
        result["qualification_review_packet"] = str(args.packet.resolve())
        result["qualification_review_view"] = str(args.view.resolve())
        result["qualification_review_manifest"] = str(args.manifest.resolve())
    elif args.action == "apply-authorization":
        result = write_completed_qualification_artifacts(
            blank_packet_path=args.packet,
            authorization_path=args.authorization,
            completed_packet_path=args.completed_packet,
            receipt_path=args.completion_receipt,
            source_packet_path=args.source_packet,
            run_root=args.run_root,
            production_path=args.production,
        )
    else:
        packet = read_review_packet(args.packet)
        validator = (
            validate_blank_qualification_packet
            if args.action == "validate-blank"
            else validate_completed_qualification_packet
        )
        result = validator(
            packet,
            args.source_packet,
            args.run_root,
            args.production,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
