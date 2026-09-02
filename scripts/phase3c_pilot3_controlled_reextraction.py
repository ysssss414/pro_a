from __future__ import annotations

import argparse
import json
from pathlib import Path

from pro_a.config import load_config
from pro_a.corpus_pilot import PilotError
from pro_a.pilot3_controlled_reextraction import (
    finalize_controlled_reextraction,
    run_controlled_reextraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3C Pilot #3 controlled semantic re-extraction")
    parser.add_argument("--config", default="config.toml")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run")
    run.add_argument("--source-file", required=True, type=Path)
    run.add_argument("--run-id")
    run.add_argument("--production-db", type=Path)

    finalize = commands.add_parser("finalize")
    finalize.add_argument("--run-dir", required=True, type=Path)
    finalize.add_argument("--regression-receipt", required=True, type=Path)
    finalize.add_argument("--production-db", type=Path)

    args = parser.parse_args()
    cfg = load_config(args.config)
    try:
        if args.command == "run":
            result = run_controlled_reextraction(
                args.source_file, cfg, run_id=args.run_id,
                production_db_path=args.production_db or cfg.db_path,
            )
        else:
            result = finalize_controlled_reextraction(
                args.run_dir, args.regression_receipt, cfg,
                production_db_path=args.production_db or cfg.db_path,
            )
    except PilotError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "status": result["status"],
        "pilot_run_id": result.get("pilot_run_id") or result.get("metrics", {}).get("pilot_run_id"),
        "run_dir": result.get("run_dir"),
        "metrics_path": result.get("metrics_path"),
        "report_path": result.get("report_path"),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
