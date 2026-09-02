from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pro_a.corpus_pilot import PilotError
from pro_a.gate_c_quality_hardening import audit_pilot2_gate_c_quality_hardening


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit Phase 3C Pilot #2 Gate C static quality hardening"
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--production-db", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = audit_pilot2_gate_c_quality_hardening(
            args.run_dir,
            args.production_db,
        )
    except PilotError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
