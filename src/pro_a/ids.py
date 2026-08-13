from __future__ import annotations

from datetime import datetime
from uuid import uuid4


def make_id(prefix: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    return f"{prefix}_{when:%Y%m%d}_{uuid4().hex[:8].upper()}"


def dated_version(existing_versions: list[str], when: datetime | None = None) -> str:
    when = when or datetime.now()
    base = f"v_{when:%Y%m%d}"
    if base not in existing_versions:
        return base
    suffixes = []
    for v in existing_versions:
        if v.startswith(base + "_"):
            try:
                suffixes.append(int(v.rsplit("_", 1)[1]))
            except ValueError:
                pass
    next_no = max(suffixes, default=0) + 1
    return f"{base}_{next_no:02d}"
