from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.pilot3_human_review import (
    build_pilot3_human_review_decisions,
    close_pilot3_human_review,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Close Phase 3C Pilot #3 Human Review")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("workspace/phase3c/PILOT_20260831_7AD15F72"),
    )
    parser.add_argument("--production-db", type=Path, default=Path("workspace/pro_a.db"))
    parser.add_argument("--regression-receipt", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    repair_dir = run_dir / "evidence_v2_repair"
    decisions_path = run_dir / "pilot3_human_review_decisions.json"
    build_pilot3_human_review_decisions(
        run_dir / "extraction_bundle.json",
        repair_dir / "evidence_contract_v2_repaired.json",
        repair_dir / "pilot3_quote_fidelity_repaired.json",
        run_dir / "pilot3_human_review_annotations.json",
        decisions_path,
    )
    result = close_pilot3_human_review(
        run_dir / "extraction_bundle.json",
        repair_dir / "evidence_contract_v2_repaired.json",
        repair_dir / "pilot3_quote_fidelity_repaired.json",
        run_dir / "pilot3_pre_review_metrics_repaired.json",
        run_dir / "evidence_contract_v2_draft.json",
        decisions_path,
        output_dir=run_dir,
        production_db_path=args.production_db,
        regression_receipt_path=args.regression_receipt,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
