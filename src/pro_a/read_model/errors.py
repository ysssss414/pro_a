"""Fixed public failures; exception messages and request values are never echoed."""
from __future__ import annotations

from functools import wraps
import json
import re
import sqlite3

from pro_a.company_material_intent import CompanyMaterialError
from pro_a.query import ReadOnlyDatabaseError
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.source_operations import SourceOperationError


class BridgeError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


DOMAIN_ERRORS = {
    "COMPANY_MATERIAL_TARGET_NOT_FOUND": "NODE_NOT_FOUND",
    "COMPANY_MATERIAL_TARGET_NOT_COMPANY": "NODE_NOT_COMPANY",
    "PROCESSING_RUN_NOT_FOUND": "RUN_NOT_FOUND",
    "SOURCE_NOT_FOUND": "SOURCE_NOT_FOUND",
    "ARTIFACT_NOT_REGISTERED": "REVIEW_PACKET_NOT_FOUND",
    "INVALID_CURSOR": "INVALID_ARGUMENT",
    "INVALID_FILTER": "INVALID_ARGUMENT",
}
MAX_PAYLOAD_BYTES = 131072
MAX_TEXT_CHARS = 16384
_PRIVATE_TEXT = re.compile(
    r"(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\|file://|(?:^|\s)/\S+|"
    r"\bBearer\s+\S+|\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+|"
    r"https?://[^\s/]+:[^\s/]+@)", re.I,
)
_PRIVATE_KEY = re.compile(
    r"secret|password|credential|api[_-]?key|authorization|(?:^|_)token(?:$|_)|"
    r"raw_response|raw_provider|raw_model|prompt|headers|filename|file_name|(?:^|_)path$", re.I,
)


def check_payload(value):
    """Fail closed instead of silently editing authoritative evidence."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    def visit(item, depth=0):
        if depth > 16:
            raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")
        if isinstance(item, dict):
            for key, child in item.items():
                if key != "origin_path" and _PRIVATE_KEY.search(key):
                    raise BridgeError("READ_BOUNDARY_VIOLATION")
                visit(child, depth + 1)
        elif isinstance(item, list):
            if len(item) > 100:
                raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, str):
            if len(item) > MAX_TEXT_CHARS:
                raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")
            if _PRIVATE_TEXT.search(item):
                raise BridgeError("READ_BOUNDARY_VIOLATION")

    visit(value)
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise BridgeError("PAYLOAD_LIMIT_EXCEEDED")


def read_operation(fn):
    @wraps(fn)
    def guarded(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            check_payload(result)
            return result
        except BridgeError:
            raise
        except ReadOnlyDatabaseError:
            raise BridgeError("PRODUCTION_UNAVAILABLE") from None
        except (CompanyMaterialError, SourceOperationError, BoundaryError) as error:
            raise BridgeError(DOMAIN_ERRORS.get(str(error), "READ_BOUNDARY_VIOLATION")) from None
        except (sqlite3.Error, OSError):
            raise BridgeError("READ_UNAVAILABLE") from None
        except Exception:
            raise BridgeError("READ_FAILED") from None
    return guarded
