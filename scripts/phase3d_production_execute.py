from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from pro_a.config import load_config
from pro_a.production_execution import execute_authorized_production


def git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def require_clean_tracked_worktree(repo: Path) -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    if status:
        raise RuntimeError("PRODUCTION_EXECUTION_TRACKED_WORKTREE_DIRTY")


def resolve(repo: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (repo / value).resolve()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Execute one exactly authorized Phase 3D Production payload")
    result.add_argument("--repo", type=Path, default=Path.cwd())
    result.add_argument("--config", type=Path, default=Path("config.toml"))
    result.add_argument("--candidate-dir", type=Path, required=True)
    result.add_argument("--authorization", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    require_clean_tracked_worktree(repo)
    config_path = resolve(repo, args.config)
    config = load_config(config_path)
    result = execute_authorized_production(
        candidate_dir=resolve(repo, args.candidate_dir),
        authorization_path=resolve(repo, args.authorization),
        config=config,
        execution_commit=git_head(repo),
        protected_real_production_path=config.db_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
