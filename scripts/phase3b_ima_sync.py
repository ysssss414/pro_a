"""Preview or explicitly sync one archived Source to IMA; configured Production only."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from pro_a.ima import IMAError
from pro_a.ima_sync import preview_production_source, sync_production_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("preview-source", "sync-production-source"):
        actions.add_parser(name).add_argument("--source-id", required=True)
    args = parser.parse_args(argv)
    try:
        operation = preview_production_source if args.action == "preview-source" else sync_production_source
        result = operation(args.source_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"preview", "synced"} and not result.get("receipt_error") else 2
    except (OSError, ValueError, sqlite3.Error, IMAError):
        print(json.dumps({"status": "failed", "code": "IMA_SYNC_LOCAL_OPERATION_FAILED",
                          "error": "Local configuration, database or receipt is unavailable"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
