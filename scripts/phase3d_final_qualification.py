from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from pro_a.config import load_config
from pro_a.production_final_qualification import (
    EXPECTED_SOURCE_ID,
    EXPECTED_SOURCE_NAME,
    EXPECTED_SOURCE_SHA256,
    build_authorization_bound_payload,
    build_manifest,
    freeze_source_package,
    qualify_final_shadow,
)
from pro_a.production_promotion import PromotionError, production_identity, sha256_file


def git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run the Stage 3D.3C final shadow qualification")
    result.add_argument("--repo", type=Path, default=Path.cwd())
    result.add_argument("--config", type=Path, default=Path("config.toml"))
    result.add_argument("--production-db", type=Path)
    result.add_argument(
        "--qualification-payload",
        type=Path,
        default=Path("workspace/phase3d/STAGE3D2_QUALIFICATION_F6A9ECB_V2/phase3d_promotion_payload.json"),
    )
    result.add_argument(
        "--draft-review",
        type=Path,
        default=Path("workspace/phase3d/STAGE3D3A_AUTHORIZATION_PREP_637D772/node_operation_review.json"),
    )
    result.add_argument(
        "--human-review",
        type=Path,
        default=Path("workspace/phase3d/STAGE3D3B_HUMAN_REVIEW_637D772/node_operation_review_human.json"),
    )
    result.add_argument(
        "--source-recovery-receipt",
        type=Path,
        default=Path("workspace/phase3d/STAGE3D_SOURCE_RECOVERY_A2AC028/source_recovery_receipt.json"),
    )
    result.add_argument("--source", type=Path)
    result.add_argument("--repository-commit", default="")
    result.add_argument("--output-dir", type=Path, required=True)
    return result


def resolve(repo: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (repo / value).resolve()


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    output_dir = resolve(repo, args.output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Qualification output already exists: {output_dir}")

    config_path = resolve(repo, args.config)
    production = (args.production_db.resolve() if args.production_db else load_config(config_path).db_path.resolve())
    production_root = production.parent
    qualification_path = resolve(repo, args.qualification_payload)
    draft_path = resolve(repo, args.draft_review)
    human_path = resolve(repo, args.human_review)
    recovery_path = resolve(repo, args.source_recovery_receipt)
    qualification_payload = load_json(qualification_path)
    draft_review = load_json(draft_path)
    human_review = load_json(human_path)
    recovery = load_json(recovery_path)
    resolved_source = recovery.get("resolved_source") or {}
    recovery_flags = recovery.get("flags") or {}
    if (
        recovery.get("document_type") != "phase3d_exact_source_recovery_receipt"
        or recovery.get("status") != "EXACT_SOURCE_RECOVERED"
        or resolved_source.get("actual_sha256") != EXPECTED_SOURCE_SHA256
        or resolved_source.get("exact_match") is not True
        or recovery_flags.get("source_archive_materialization_ready") is not True
    ):
        raise PromotionError("SOURCE_RECOVERY_RECEIPT_INVALID")
    source_path = args.source.resolve() if args.source else Path(resolved_source["path"]).resolve()
    repository_commit = args.repository_commit or git_head(repo)

    baseline = production_identity(production)
    output_dir.mkdir(parents=True)
    package_path = output_dir / "source" / f"{EXPECTED_SOURCE_ID}__{EXPECTED_SOURCE_NAME}"
    source_materialization = freeze_source_package(
        source_path,
        package_path,
        production_root=production_root,
    )
    source_materialization_path = output_dir / "source_materialization_final.json"
    write_json(source_materialization_path, source_materialization)

    payload = build_authorization_bound_payload(
        qualification_payload=qualification_payload,
        draft_review=draft_review,
        human_review=human_review,
        human_review_file_sha256=sha256_file(human_path),
        source_materialization=source_materialization,
        production=baseline,
        repository_commit=repository_commit,
        source_recovery_receipt_sha256=sha256_file(recovery_path),
    )
    payload_path = output_dir / "phase3d_authorization_bound_payload.json"
    write_json(payload_path, payload)

    receipt_path = output_dir / "phase3d_final_shadow_qualification_receipt.json"
    receipt = qualify_final_shadow(
        payload,
        production_path=production,
        production_root=production_root,
        source_package_path=package_path,
        output_dir=output_dir,
        receipt_path=receipt_path,
    )
    source_materialization["flags"]["source_archive_materialization_qualified"] = True
    source_materialization["qualification"] = {
        "status": receipt["status"],
        "shadow_archive_path": receipt["shadow"]["source_materialization"]["path"],
        "shadow_archive_sha256": receipt["shadow"]["source_materialization"]["sha256"],
        "production_archive_changed": False,
    }
    write_json(source_materialization_path, source_materialization)

    manifest = build_manifest(output_dir, repository_commit=repository_commit, payload=payload)
    manifest_path = output_dir / "stage3d3c_manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({
        "status": receipt["status"],
        "payload_id": payload["payload_id"],
        "payload_sha256": payload["payload_hash"],
        "payload_path": str(payload_path),
        "source_package_path": str(package_path),
        "source_package_sha256": source_materialization["package"]["sha256"],
        "receipt_path": str(receipt_path),
        "manifest_path": str(manifest_path),
        "production_changed": False,
        "production_apply_attempted": False,
        "production_apply_authorized": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
