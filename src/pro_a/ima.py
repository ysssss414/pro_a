from __future__ import annotations

import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import requests

from .config import IMAConfig


class IMAError(RuntimeError):
    pass


MEDIA_TYPES = {
    ".pdf": 1,
    ".doc": 3, ".docx": 3,
    ".ppt": 4, ".pptx": 4,
    ".xls": 5, ".xlsx": 5, ".xlsm": 5, ".csv": 5,
    ".md": 7, ".markdown": 7,
    ".png": 9, ".jpg": 9, ".jpeg": 9, ".webp": 9,
    ".txt": 13,
    ".xmind": 14,
    ".mp3": 15, ".m4a": 15, ".wav": 15, ".aac": 15,
}

SIZE_LIMITS = {
    5: 10 * 1024 * 1024,
    7: 10 * 1024 * 1024,
    13: 10 * 1024 * 1024,
    14: 10 * 1024 * 1024,
    9: 30 * 1024 * 1024,
}
DEFAULT_LIMIT = 200 * 1024 * 1024


class IMAClient:
    def __init__(self, cfg: IMAConfig):
        self.cfg = cfg

    @property
    def available(self) -> bool:
        return bool(self.cfg.enabled and self.cfg.client_id and self.cfg.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.available:
            raise IMAError("IMA is disabled or credentials are missing")
        return {
            "ima-openapi-clientid": self.cfg.client_id,
            "ima-openapi-apikey": self.cfg.api_key,
            "Content-Type": "application/json",
        }

    def call(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self.cfg.base_url.rstrip("/") + "/" + path.lstrip("/")
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=90)
        if resp.status_code >= 400:
            raise IMAError(f"IMA HTTP {resp.status_code}: {resp.text[:1000]}")
        data = resp.json()
        if data.get("code") != 0:
            raise IMAError(f"IMA API error {data.get('code')}: {data.get('msg')}")
        return data.get("data") or {}

    def list_addable_kbs(self, limit: int = 50) -> list[dict[str, Any]]:
        out, cursor = [], ""
        while True:
            data = self.call("openapi/wiki/v1/get_addable_knowledge_base_list", {"cursor": cursor, "limit": limit})
            out.extend(data.get("addable_knowledge_base_list") or [])
            if data.get("is_end", True):
                break
            cursor = data.get("next_cursor", "")
        return out

    def _media_type(self, path: Path) -> int:
        ext = path.suffix.lower()
        if ext not in MEDIA_TYPES:
            raise IMAError(f"IMA v0.1 upload does not map extension: {ext}")
        return MEDIA_TYPES[ext]

    def _preflight(self, path: Path) -> tuple[int, str, int]:
        media_type = self._media_type(path)
        size = path.stat().st_size
        limit = SIZE_LIMITS.get(media_type, DEFAULT_LIMIT)
        if size > limit:
            raise IMAError(f"File exceeds IMA limit for media_type={media_type}: {size} > {limit}")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix.lower() in {".md", ".markdown"}:
            content_type = "text/markdown"
        return media_type, content_type, size

    def check_same_name(self, kb_id: str, folder_id: str, name: str, media_type: int) -> bool:
        payload: dict[str, Any] = {
            "params": [{"name": name, "media_type": media_type}],
            "knowledge_base_id": kb_id,
        }
        if folder_id:
            payload["folder_id"] = folder_id
        data = self.call("openapi/wiki/v1/check_repeated_names", payload)
        results = data.get("results") or []
        return bool(results and results[0].get("is_repeated"))

    def upload_file(self, path: Path, kb_id: str, folder_id: str = "", title: str | None = None) -> dict[str, Any]:
        if not kb_id:
            raise IMAError("IMA knowledge_base_id is empty")
        path = Path(path)
        media_type, content_type, size = self._preflight(path)
        title = title or path.name

        if self.cfg.skip_same_name and self.check_same_name(kb_id, folder_id, title, media_type):
            return {"skipped": True, "reason": "same_name", "media_id": ""}

        created = self.call("openapi/wiki/v1/create_media", {
            "file_name": path.name,
            "file_size": size,
            "content_type": content_type,
            "knowledge_base_id": kb_id,
            "file_ext": path.suffix.lower().lstrip("."),
        })
        media_id = created.get("media_id")
        cred = created.get("cos_credential") or {}
        if not media_id or not cred:
            raise IMAError(f"create_media missing media_id/cos_credential: {created}")

        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as e:  # pragma: no cover
            raise IMAError("cos-python-sdk-v5 is required for IMA file upload") from e

        bucket = cred.get("bucket_name") or cred.get("bucket")
        region = cred.get("region")
        cos_key = cred.get("cos_key")
        config = CosConfig(
            Region=region,
            SecretId=cred.get("secret_id"),
            SecretKey=cred.get("secret_key"),
            Token=cred.get("token"),
            Scheme="https",
        )
        client = CosS3Client(config)
        client.upload_file(Bucket=bucket, Key=cos_key, LocalFilePath=str(path), EnableMD5=False)

        payload: dict[str, Any] = {
            "media_type": media_type,
            "media_id": media_id,
            "title": title,
            "knowledge_base_id": kb_id,
            "file_info": {
                "cos_key": cos_key,
                "file_size": size,
                "last_modify_time": int(path.stat().st_mtime or time.time()),
                "file_name": path.name,
            },
        }
        if folder_id:
            payload["folder_id"] = folder_id
        added = self.call("openapi/wiki/v1/add_knowledge", payload)
        return {"skipped": False, "media_id": added.get("media_id") or media_id, "cos_key": cos_key}
