from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Callable

import requests

from .config import IMAConfig


class IMAError(RuntimeError):
    def __init__(self, message: str, *, code: str = "IMA_ERROR", stage: str = "preflight",
                 media_id: str = "", remote_state_uncertain: bool = False):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.media_id = media_id
        self.remote_state_uncertain = remote_state_uncertain


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

    def call(self, path: str, payload: dict[str, Any], *, stage: str = "preflight") -> dict[str, Any]:
        def error(code: str, message: str) -> IMAError:
            return IMAError(message, code=code, stage=stage,
                            remote_state_uncertain=stage in {"create_media", "add_knowledge"})

        url = self.cfg.base_url.rstrip("/") + "/" + path.lstrip("/")
        # Never include request/response bodies, headers or upstream exception text in errors.
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=90,
                                 allow_redirects=False)
        except requests.Timeout:
            raise error("IMA_TIMEOUT", "IMA request timed out") from None
        except requests.RequestException:
            raise error("IMA_CONNECTION_FAILED", "IMA request failed") from None
        if resp.status_code >= 300:
            raise error("IMA_HTTP_ERROR", f"IMA HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise error("IMA_INVALID_JSON", "IMA response is not valid JSON") from None
        if not isinstance(data, dict) or type(data.get("code")) is not int:
            raise error("IMA_INVALID_RESPONSE", "IMA response has no valid code")
        if data.get("code") != 0:
            raise error("IMA_API_ERROR", "IMA API returned a failure code")
        if not isinstance(data.get("data"), dict):
            raise error("IMA_INVALID_RESPONSE", "IMA response has no valid data object")
        return data["data"]

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
            raise IMAError("IMA does not support this file extension", code="UNSUPPORTED_MEDIA_TYPE")
        return MEDIA_TYPES[ext]

    def _preflight(self, path: Path) -> tuple[int, str, int]:
        media_type = self._media_type(path)
        try:
            size = path.stat().st_size
        except OSError:
            raise IMAError("Archived original is unavailable", code="ARCHIVE_FILE_MISSING") from None
        limit = SIZE_LIMITS.get(media_type, DEFAULT_LIMIT)
        if size > limit:
            raise IMAError(f"File exceeds IMA limit for media_type={media_type}: {size} > {limit}",
                           code="FILE_TOO_LARGE")
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
        data = self.call("openapi/wiki/v1/check_repeated_names", payload, stage="duplicate_check")
        results = data.get("results")
        if (not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict)
                or type(results[0].get("is_repeated")) is not bool):
            raise IMAError("IMA duplicate check has no valid result", code="DUPLICATE_CHECK_INVALID_RESPONSE",
                           stage="duplicate_check")
        return results[0]["is_repeated"]

    def upload_file(self, path: Path, kb_id: str, folder_id: str = "", title: str | None = None, *,
                    on_stage: Callable[[str, str], None] | None = None,
                    check_duplicate: bool | None = None) -> dict[str, Any]:
        if not kb_id:
            raise IMAError("IMA knowledge_base_id is empty", code="SOURCE_KB_NOT_CONFIGURED")
        path = Path(path)
        media_type, content_type, size = self._preflight(path)
        title = title or path.name
        media_id = ""
        stage = "preflight"

        def enter(next_stage: str) -> None:
            nonlocal stage
            stage = next_stage
            if on_stage is not None:
                on_stage(stage, media_id)

        try:
            if self.cfg.skip_same_name if check_duplicate is None else check_duplicate:
                enter("duplicate_check")
                if self.check_same_name(kb_id, folder_id, title, media_type):
                    return {"skipped": True, "reason": "same_name", "media_id": ""}

            enter("create_media")
            created = self.call("openapi/wiki/v1/create_media", {
                "file_name": path.name,
                "file_size": size,
                "content_type": content_type,
                "knowledge_base_id": kb_id,
                "file_ext": path.suffix.lower().lstrip("."),
            }, stage=stage)
            raw_id = created.get("media_id")
            media_id = raw_id if isinstance(raw_id, str) and raw_id.strip() else ""
            cred = created.get("cos_credential")
            required = ("region", "cos_key", "secret_id", "secret_key", "token")
            if (not media_id or not isinstance(cred, dict)
                    or not all(isinstance(cred.get(k), str) and cred[k].strip() for k in required)
                    or not isinstance(cred.get("bucket_name") or cred.get("bucket"), str)
                    or not (cred.get("bucket_name") or cred.get("bucket", "")).strip()):
                raise IMAError("IMA create_media response is incomplete", code="CREATE_MEDIA_INVALID_RESPONSE",
                               stage=stage, media_id=media_id, remote_state_uncertain=True)

            enter("cos_upload")
            self._upload_to_cos(path, cred)
            enter("add_knowledge")
            payload: dict[str, Any] = {
                "media_type": media_type,
                "media_id": media_id,
                "title": title,
                "knowledge_base_id": kb_id,
                "file_info": {
                    "cos_key": cred["cos_key"],
                    "file_size": size,
                    "last_modify_time": int(path.stat().st_mtime or time.time()),
                    "file_name": path.name,
                },
            }
            if folder_id:
                payload["folder_id"] = folder_id
            added = self.call("openapi/wiki/v1/add_knowledge", payload, stage=stage)
            final_id = added.get("media_id") or media_id
            if not isinstance(final_id, str) or not final_id.strip():
                raise IMAError("IMA add_knowledge has no valid media identity",
                               code="ADD_KNOWLEDGE_INVALID_RESPONSE", stage=stage)
            return {"skipped": False, "media_id": final_id}
        except IMAError as exc:
            exc.media_id = exc.media_id or media_id
            exc.remote_state_uncertain = exc.remote_state_uncertain or stage in {"create_media", "cos_upload", "add_knowledge"}
            raise
        except Exception:
            raise IMAError("IMA upload stage failed", code="IMA_UPLOAD_FAILED", stage=stage,
                           media_id=media_id, remote_state_uncertain=stage in {"create_media", "cos_upload", "add_knowledge"}) from None

    def _upload_to_cos(self, path: Path, cred: dict[str, Any]) -> None:
        try:
            from qcloud_cos import CosConfig, CosS3Client

            config = CosConfig(Region=cred["region"], SecretId=cred["secret_id"],
                               SecretKey=cred["secret_key"], Token=cred["token"], Scheme="https")
            client = CosS3Client(config)
            client.upload_file(Bucket=cred.get("bucket_name") or cred["bucket"], Key=cred["cos_key"],
                               LocalFilePath=str(path), EnableMD5=False)
        except Exception:
            raise IMAError("COS upload failed; check SDK installation and connectivity",
                           code="COS_UPLOAD_FAILED", stage="cos_upload", remote_state_uncertain=True) from None
