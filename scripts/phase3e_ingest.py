from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.operational_ingestion import (  # noqa: E402
    STOP_AFTER,
    OperationalIngestionError,
    run_operational_ingestion,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operational clean-PDF ingestion through human-review handoff"
    )
    parser.add_argument("source", nargs="?", type=Path, help="new clean PDF")
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after", choices=tuple(STOP_AFTER))
    parser.add_argument(
        "--frozen-extraction",
        type=Path,
        help="qualification-only frozen Phase 3C extraction bundle; does not call the LLM",
    )
    parser.add_argument(
        "--adaptive-retry-policy",
        choices=("allow", "forbid"),
        default="allow",
        help=(
            "forbid semantic-input-changing truncation splits for frozen acceptance; "
            "normal chunk fan-out and identical-input transport retries remain enabled"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_operational_ingestion(
            args.source,
            config_path=args.config,
            run_dir=args.run_dir,
            resume=args.resume,
            stop_after=args.stop_after,
            frozen_extraction_path=args.frozen_extraction,
            adaptive_retry_policy=args.adaptive_retry_policy,
        )
    except (OperationalIngestionError, OSError, ValueError) as exc:
        print(f"RUN_STATUS = FAILED\nERROR = {exc}", file=sys.stderr)
        return 2
    print(f"RUN_STATUS = {result['run_status']}")
    print(f"RUN_ID = {result['run_id']}")
    print(f"RUN_DIR = {result['run_dir']}")
    print(f"MANIFEST = {result['manifest']}")
    if result["run_status"] == "HUMAN_REVIEW_REQUIRED":
        print(f"CLAIM_REVIEW = {result['claim_review']}")
        print(f"NODE_REVIEW = {result['node_review']}")
        print(f"PROMOTION_PREVIEW = {result['promotion_preview']}")
    print("PRODUCTION_APPLY_ATTEMPTED = false")
    print("PRODUCTION_CHANGED = NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
