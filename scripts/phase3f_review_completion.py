from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pro_a.phase3f_review_completion import (  # noqa: E402
    read_review_packet,
    validate_blank_review_packet,
    validate_completed_review_packet,
    write_blank_review_packet,
)


RUN_ROOT = ROOT / "workspace" / "phase3e2sl6" / "operational_run"
OUTPUT_ROOT = ROOT / "workspace" / "phase3f_stage1_review_completion"
PACKET_PATH = OUTPUT_ROOT / "operational_review_packet.json"
VIEW_PATH = OUTPUT_ROOT / "operational_review_view.md"
EXPECTED_RUN_ID = "INGEST_2644CBDB2693D5E0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or validate the Phase 3F blank operational review packet."
    )
    parser.add_argument("action", choices=("build", "validate-blank", "validate-completed"))
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    parser.add_argument("--packet", type=Path, default=PACKET_PATH)
    parser.add_argument("--view", type=Path, default=VIEW_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "build":
        packet = write_blank_review_packet(
            run_root=args.run_root,
            packet_path=args.packet,
            markdown_path=args.view,
        )
        result = validate_blank_review_packet(packet, args.run_root)
        result["authoritative_review_packet"] = str(args.packet.resolve())
        result["human_review_view"] = str(args.view.resolve())
    else:
        packet = read_review_packet(args.packet)
        if args.action == "validate-blank":
            result = validate_blank_review_packet(packet, args.run_root)
        else:
            result = validate_completed_review_packet(packet, args.run_root)
    if result["run_id"] != EXPECTED_RUN_ID:
        raise RuntimeError(f"UNEXPECTED_OPERATIONAL_RUN:{result['run_id']}")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
