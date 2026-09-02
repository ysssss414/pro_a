from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from pro_a.config import load_config
from pro_a.production_promotion import (
    ArtifactPaths,
    PILOT6_EXPECTED_ARTIFACT_HASHES,
    build_promotion_payload,
    converge_phase3c_artifacts,
    production_identity,
    qualify_shadow_promotion,
)


def git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Qualify a deterministic Phase 3D payload on an exact Production shadow")
    result.add_argument("--repo", type=Path, default=Path.cwd())
    result.add_argument("--config", type=Path, default=Path("config.toml"))
    result.add_argument("--production-db", type=Path)
    result.add_argument("--run-dir", type=Path, default=Path("workspace/phase3c/PILOT_20260902_572A6DF2"))
    result.add_argument(
        "--reviewer-signoff",
        type=Path,
        default=Path("artifacts/phase3c/pilot6_delegated_reviewer_signoff.json"),
    )
    result.add_argument("--repository-commit", default="")
    result.add_argument("--output-dir", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    config_path = args.config if args.config.is_absolute() else repo / args.config
    config = load_config(config_path)
    production = (args.production_db or config.db_path).resolve()
    run_dir = args.run_dir if args.run_dir.is_absolute() else repo / args.run_dir
    signoff = args.reviewer_signoff if args.reviewer_signoff.is_absolute() else repo / args.reviewer_signoff
    output_dir = args.output_dir if args.output_dir.is_absolute() else repo / args.output_dir
    if output_dir.exists():
        raise FileExistsError(f"Qualification output already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    converged = converge_phase3c_artifacts(
        ArtifactPaths(
            rebound_bundle=run_dir / "extraction_bundle_stage1_1_rebound.json",
            table_boundary=run_dir / "pilot6_table_claim_safety_boundary.json",
            reviewer_signoff=signoff,
            review_draft=run_dir / "extraction_review_draft.json",
        ),
        expected_hashes=PILOT6_EXPECTED_ARTIFACT_HASHES,
    )
    baseline = production_identity(production)
    payload = build_promotion_payload(
        converged,
        baseline,
        repository_commit=args.repository_commit or git_head(repo),
    )
    payload_path = output_dir / "phase3d_promotion_payload.json"
    write_json(payload_path, payload)
    receipt = qualify_shadow_promotion(
        payload,
        production_path=production,
        shadow_path=output_dir / "production_shadow.db",
        receipt_path=output_dir / "phase3d_shadow_qualification_receipt.json",
    )
    print(json.dumps({
        "status": receipt["status"],
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "payload_path": str(payload_path),
        "receipt_path": str(output_dir / "phase3d_shadow_qualification_receipt.json"),
        "production_changed": False,
        "production_apply_attempted": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
