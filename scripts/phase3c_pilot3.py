from __future__ import annotations

import argparse
import json
from pathlib import Path

from pro_a.config import load_config
from pro_a.corpus_pilot import PilotError
from pro_a.pilot3 import finalize_pilot3_artifacts, run_pilot3_independent_extraction


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or finalize Phase 3C Pilot #3")
    parser.add_argument("--config", default="config.toml")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run")
    run.add_argument("--source-file", required=True, type=Path)
    run.add_argument("--manifest", required=True, type=Path)
    run.add_argument("--preflight-receipt", required=True, type=Path)
    run.add_argument("--run-id", required=True)
    run.add_argument("--production-db", type=Path)

    finalize = commands.add_parser("finalize")
    finalize.add_argument("--run-dir", required=True, type=Path)
    finalize.add_argument("--regression-receipt", required=True, type=Path)
    finalize.add_argument("--production-db", type=Path)

    args = parser.parse_args()
    cfg = load_config(args.config)
    try:
        if args.command == "run":
            result = run_pilot3_independent_extraction(
                args.source_file,
                args.manifest,
                args.preflight_receipt,
                args.run_id,
                cfg,
                production_db_path=args.production_db or cfg.db_path,
            )
        else:
            result = finalize_pilot3_artifacts(
                args.run_dir,
                args.regression_receipt,
                cfg,
                production_db_path=args.production_db or cfg.db_path,
            )
    except PilotError as exc:
        print(str(exc))
        return 1
    print(json.dumps({
        "status": result["status"],
        "pilot_run_id": result.get("pilot_run_id") or result["metrics"]["pilot_run_id"],
        "metrics_path": result["metrics_path"],
        "report_path": result["report_path"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
