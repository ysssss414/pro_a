"""Preview or explicitly create a pending Human View Proposal in configured Production."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from pro_a.human_review_intake import HumanReviewIntakeError, read_artifact
from pro_a.production_proposal_gateway import apply_production, preview_production
from pro_a.query import ReadOnlyDatabaseError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("preview", "apply-production"):
        action = actions.add_parser(name)
        action.add_argument("--draft", required=True)
    args = parser.parse_args(argv)
    try:
        draft = read_artifact(args.draft)
        result = preview_production(draft) if args.action == "preview" else apply_production(draft)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (HumanReviewIntakeError, ReadOnlyDatabaseError, OSError, sqlite3.Error) as exc:
        code = getattr(exc, "code", "GATEWAY_FAILED")
        status = "COMMITTED_RECEIPT_FAILED" if code == "PROPOSAL_COMMITTED_RECEIPT_FAILED" else "BLOCKED"
        print(json.dumps({"status": status, "code": code, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3 if status == "COMMITTED_RECEIPT_FAILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
