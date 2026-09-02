from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.corpus_pilot import PilotError
from pro_a.reextraction_human_review import (
    build_reextraction_human_review_decisions,
    close_reextraction_human_review,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Close Phase 3C Pilot #2 controlled re-extraction human review"
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--evidence-draft", required=True, type=Path)
    parser.add_argument("--quote-fidelity", required=True, type=Path)
    parser.add_argument("--reextraction-metrics", required=True, type=Path)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--historical-run-dir", required=True, type=Path)
    parser.add_argument("--production-db", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    decisions_path = args.output_dir / "reextraction_human_review_decisions.json"
    try:
        build_reextraction_human_review_decisions(
            args.bundle,
            args.quote_fidelity,
            args.annotations,
            decisions_path,
        )
        result = close_reextraction_human_review(
            args.bundle,
            args.evidence_draft,
            args.quote_fidelity,
            args.reextraction_metrics,
            decisions_path,
            args.historical_run_dir,
            output_dir=args.output_dir,
            production_db_path=args.production_db,
        )
    except PilotError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
