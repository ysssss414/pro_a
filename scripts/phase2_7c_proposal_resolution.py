"""Preview or explicitly apply a human resolution artifact to configured Production."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from pro_a.human_proposal_resolution import preview_resolution, resolve_production
from pro_a.human_review_intake import HumanReviewIntakeError, read_artifact
from pro_a.query import ReadOnlyDatabaseError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("preview", "apply-production"):
        actions.add_parser(name).add_argument("--resolution", required=True)
    args = parser.parse_args(argv)
    try:
        artifact = read_artifact(args.resolution)
        result = preview_resolution(artifact) if args.action == "preview" else resolve_production(artifact)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (HumanReviewIntakeError, ReadOnlyDatabaseError, OSError, sqlite3.Error) as exc:
        code = getattr(exc, "code", "RESOLUTION_FAILED")
        committed = code == "RESOLUTION_COMMITTED_RECEIPT_FAILED"
        print(json.dumps({"status": "COMMITTED_RECEIPT_FAILED" if committed else "BLOCKED",
                          "code": code, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3 if committed else 2


if __name__ == "__main__":
    raise SystemExit(main())
