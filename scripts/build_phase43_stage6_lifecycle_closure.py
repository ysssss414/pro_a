"""Build the deterministic Stage 2 lifecycle closure and its source manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pro_a.stage6_lifecycle import (
    build_closure, build_source_manifest, closure_file_bytes, immutable_write,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output", type=Path,
        default=Path("lifecycle_closure/phase43_stage2_foundation_v1.json"),
    )
    parser.add_argument(
        "--source-manifest", type=Path,
        default=Path("docs/phase43_stage6_lifecycle_source_manifest.json"),
    )
    args = parser.parse_args()
    repository = args.repository.resolve()
    closure = build_closure(repository)
    immutable_write(args.output, closure_file_bytes(closure))
    builder_paths = [repository / "src/pro_a/stage6_lifecycle.py", Path(__file__).resolve()]
    source_manifest = build_source_manifest(repository, closure, builder_paths)
    immutable_write(args.source_manifest, closure_file_bytes(source_manifest))
    print(json.dumps({
        "status": "LIFECYCLE_CLOSURE_BUILT",
        "closure_id": closure["closure_id"],
        "closure_sha256": closure["closure_sha256"],
        "rows": len(closure["resolutions"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
