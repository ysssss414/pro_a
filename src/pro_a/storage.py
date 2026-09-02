from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


def ensure_workspace(root: Path) -> None:
    for rel in [
        "inbox/archive", "inbox/standard", "inbox/deep", "archive", "generated/current_views",
        "generated/receipts", "review/proposals", "logs"
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_file(input_path: Path, root: Path, source_id: str) -> Path:
    now = datetime.now()
    target_dir = root / "archive" / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = input_path.name.replace("/", "_").replace("\\", "_")
    target = target_dir / f"{source_id}__{safe_name}"
    if input_path.resolve() != target.resolve():
        shutil.move(str(input_path), str(target))
    return target


def archive_file_copy(input_path: Path, root: Path, source_id: str) -> Path:
    """Copy an input into the existing archive layout without consuming it."""
    now = datetime.now()
    target_dir = root / "archive" / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = input_path.name.replace("/", "_").replace("\\", "_")
    target = target_dir / f"{source_id}__{safe_name}"
    if target.exists():
        if sha256_file(target) == sha256_file(input_path):
            return target
        raise FileExistsError(f"Archive target already exists with different bytes: {target}")
    shutil.copy2(str(input_path), str(target))
    return target


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
