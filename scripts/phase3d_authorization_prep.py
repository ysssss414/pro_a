from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pro_a.production_authorization import (  # noqa: E402
    build_authorization_manifest,
    build_node_operation_review,
    prepare_source_materialization,
    render_node_operation_review_markdown,
)
from pro_a.production_promotion import production_identity  # noqa: E402


DEFAULT_PAYLOAD = ROOT / "workspace" / "phase3d" / "STAGE3D2_QUALIFICATION_F6A9ECB_V2" / "phase3d_promotion_payload.json"
DEFAULT_PRODUCTION = ROOT / "workspace" / "pro_a.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the read-only Stage 3D.3A authorization package.")
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD)
    parser.add_argument("--production-db", type=Path, default=DEFAULT_PRODUCTION)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-candidate", type=Path, action="append", default=[])
    parser.add_argument("--searched-location", action="append", default=[])
    return parser.parse_args()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"OUTPUT_DIRECTORY_ALREADY_EXISTS:{output_dir}")
    output_dir.mkdir(parents=True)
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    production_path = args.production_db.resolve()
    production_pre = production_identity(production_path)

    source = prepare_source_materialization(
        payload,
        candidate_paths=args.source_candidate,
        production_root=production_path.parent,
        staging_root=output_dir / "source_archive_staging",
        searched_locations=args.searched_location,
    )
    review = build_node_operation_review(payload, production_path)
    source_path = output_dir / "source_materialization.json"
    review_json_path = output_dir / "node_operation_review.json"
    review_md_path = output_dir / "node_operation_review.md"
    write_json(source_path, source)
    write_json(review_json_path, review)
    review_md_path.write_text(render_node_operation_review_markdown(review), encoding="utf-8")

    production_post = production_identity(production_path)
    repository_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    manifest = build_authorization_manifest(
        repository_commit=repository_commit,
        payload=payload,
        production_pre=production_pre,
        production_post=production_post,
        source_materialization=source,
        node_review=review,
        artifact_paths=[source_path, review_json_path, review_md_path],
    )
    manifest_path = output_dir / "stage3d3a_manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({
        "artifact_dir": str(output_dir),
        "source_file_found": source["flags"]["source_file_found"],
        "source_archive_materialization_ready": source["flags"]["source_archive_materialization_ready"],
        "node_review_universe": review["review_universe"]["observed"],
        "suggestion_counts": review["suggestion_counts"],
        "production_pre_sha256": production_pre["sha256"],
        "production_post_sha256": production_post["sha256"],
        "production_changed": False,
        "production_apply_attempted": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
