"""Read Source identities from an operator-reviewed artifact allowlist only."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .production_promotion import connect_read_only, sha256_file


AUDIT_VERSION = "authoritative-source-allowlist-v1"


def audit_source_duplicates(source_sha256: str, production_path: Path,
                            artifacts: list[dict], *,
                            prior_preregistrations: tuple[Path, ...] = ()) -> dict:
    """Each artifact names an exact JSON row location and its Source SHA field.

    Completeness is relative to the reviewed allowlist, never a workspace scan.
    Missing/unreadable/malformed required inputs are reported, not ignored.
    A caller must enumerate any formal execution namespace before constructing
    the allowlist; test workspaces and copied databases have no implied authority.
    """
    inventory, identities, prior, errors = [], [], [], []

    def add_identity(row, path, sha_field, id_field):
        digest = row[sha_field].lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("INVALID_SOURCE_SHA256")
        identities.append({"artifact": str(path), "source_id": str(row.get(id_field, "")),
                           "source_sha256": digest})

    def failed(path, exc):
        category = "AUTHORITATIVE_PATH_UNREADABLE" if isinstance(exc, OSError) else "AUTHORITATIVE_ARTIFACT_INVALID"
        errors.append({"path": str(path), "category": category,
                       "error": f"{type(exc).__name__}:{exc}"})
        inventory.append({"path": str(path), "readable": False})

    try:
        with closing(connect_read_only(production_path)) as conn:
            rows = conn.execute("SELECT source_id, sha256 FROM sources ORDER BY source_id").fetchall()
        for row in rows:
            add_identity(dict(row), production_path, "sha256", "source_id")
        inventory.append({"path": str(production_path), "readable": True,
                          "role": "production", "identity_count": len(rows)})
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error) as exc:
        failed(production_path, exc)

    for spec in sorted(artifacts, key=lambda item: item["path"]):
        path = Path(spec["path"])
        try:
            value = json.loads(path.read_bytes())
            for key in spec["rows"]:
                value = value[key]
            rows = value if isinstance(value, list) else [value]
            if not rows:
                raise ValueError("EMPTY_AUTHORITATIVE_SOURCE_IDENTITY_SET")
            for row in rows:
                add_identity(row, path, spec["sha_field"], spec.get("id_field", "source_id"))
            inventory.append({"path": str(path), "readable": True, "role": "history",
                              "sha256": sha256_file(path), "identity_count": len(rows)})
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            failed(path, exc)

    for path in sorted(prior_preregistrations):
        try:
            value = json.loads(path.read_bytes())
            if value["preflight_result"] != "FAIL":
                raise ValueError("PRIOR_ATTEMPT_NOT_PREFLIGHT_FAILED")
            prior.append({"path": str(path), "source_sha256": value["source_sha256"],
                          "sha256": sha256_file(path), "constitutes_ingestion": False})
            inventory.append({"path": str(path), "readable": True, "role": "prior_attempt"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failed(path, exc)

    matches = [row for row in identities if row["source_sha256"] == source_sha256.lower()]
    production_matches = [row for row in matches if row["artifact"] == str(production_path)]
    historical_matches = [row for row in matches if row["artifact"] != str(production_path)]
    return {"audit_version": AUDIT_VERSION,
            "authoritative_source_universe_complete": not errors,
            "duplicate_check": "PASS" if not errors and not matches else "FAIL",
            "inventory": inventory, "identities": identities,
            "identities_inspected": len(identities),
            "unique_source_shas": len({row["source_sha256"] for row in identities}),
            "production_matches": production_matches, "historical_matches": historical_matches,
            "prior_attempt_only_matches": [row for row in prior if row["source_sha256"] == source_sha256],
            "prior_failed_preregistration_blocks_execution": False,
            "ignored_by_design": "All paths outside the reviewed allowlist; no recursive traversal",
            "errors": errors}
