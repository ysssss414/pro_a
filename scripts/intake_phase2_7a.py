"""Prepare non-canonical human review drafts; submit only to an isolated SQLite DB."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from pro_a.human_review_intake import (
    HumanReviewIntakeError,
    prepare_review,
    read_artifact,
    submit_review,
)
from pro_a.query import ReadOnlyDatabaseError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare = commands.add_parser("prepare", help="read-only validation; no DB writes")
    prepare.add_argument("--db", required=True)
    prepare.add_argument("--review", required=True)
    prepare.add_argument("--output", required=True, help="new .json file; existing files are never overwritten")
    submit = commands.add_parser("submit", help="pending Proposal only; Production writes prohibited")
    submit.add_argument("--isolated-db", required=True, help="explicit isolated fixture/copy, not Production")
    submit.add_argument("--draft", required=True, help="draft with explicitly human-edited proposed_current_view")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            output = Path(args.output)
            if output.suffix.lower() != ".json":
                raise HumanReviewIntakeError("INVALID_OUTPUT", "output must be a new .json artifact")
            result = prepare_review(args.db, read_artifact(args.review))
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        else:
            result = submit_review(args.isolated_db, read_artifact(args.draft), isolated=True)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (HumanReviewIntakeError, ReadOnlyDatabaseError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"status": "BLOCKED", "code": getattr(exc, "code", "INTAKE_FAILED"),
                          "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
