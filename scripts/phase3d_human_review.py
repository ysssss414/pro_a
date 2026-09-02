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
    authoritative_human_decisions,
    bind_human_node_review,
    build_human_review_manifest,
    render_human_node_review_markdown,
)
from pro_a.production_promotion import production_identity  # noqa: E402


STAGE3D2 = ROOT / "workspace" / "phase3d" / "STAGE3D2_QUALIFICATION_F6A9ECB_V2"
STAGE3D3A = ROOT / "workspace" / "phase3d" / "STAGE3D3A_AUTHORIZATION_PREP_637D772"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bind the exact Stage 3D.3B user human Node review.")
    parser.add_argument("--payload", type=Path, default=STAGE3D2 / "phase3d_promotion_payload.json")
    parser.add_argument("--draft-review", type=Path, default=STAGE3D3A / "node_operation_review.json")
    parser.add_argument("--source-materialization", type=Path, default=STAGE3D3A / "source_materialization.json")
    parser.add_argument("--production-db", type=Path, default=ROOT / "workspace" / "pro_a.db")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"OUTPUT_DIRECTORY_ALREADY_EXISTS:{output_dir}")
    payload = read_json(args.payload)
    draft = read_json(args.draft_review)
    source = read_json(args.source_materialization)
    production_path = args.production_db.resolve()
    production_pre = production_identity(production_path)

    human_review = bind_human_node_review(
        draft_review=draft,
        payload=payload,
        source_materialization=source,
        decisions=authoritative_human_decisions(),
        production_path=production_path,
    )
    output_dir.mkdir(parents=True)
    review_json_path = output_dir / "node_operation_review_human.json"
    review_md_path = output_dir / "node_operation_review_human.md"
    write_json(review_json_path, human_review)
    review_md_path.write_text(render_human_node_review_markdown(human_review), encoding="utf-8")

    production_post = production_identity(production_path)
    repository_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    manifest = build_human_review_manifest(
        repository_commit=repository_commit,
        human_review=human_review,
        production_pre=production_pre,
        production_post=production_post,
        artifact_paths=[review_json_path, review_md_path],
    )
    manifest_path = output_dir / "stage3d3b_manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({
        "artifact_dir": str(output_dir),
        "human_review_id": human_review["human_review_id"],
        "human_review_sha256": human_review["human_review_sha256"],
        "human_review_universe": human_review["human_review_universe"]["observed"],
        "operation_counts": human_review["operation_counts"],
        "source_archive_materialization_ready": False,
        "final_production_payload_generated": False,
        "production_apply_authorized": False,
        "production_pre_sha256": production_pre["sha256"],
        "production_post_sha256": production_post["sha256"],
        "production_changed": False,
        "production_apply_attempted": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
