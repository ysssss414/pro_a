from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = PACKAGE_ROOT / "manifest.json"
EXPECTED_SCHEMA_VERSION = "0.2.1"
EXPECTED_SCHEMA_SHA256 = "31f9b03ab06f62336104424cccb82962b8096aec66b1f23942397c6f4a637718"
FORBIDDEN_ALIAS = "可插拔光模块"


class ApplyError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", normalized)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ApplyError(f"Expected JSON object: {path.name}")
    return value


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp_path, path)


def validate_manifest() -> tuple[dict[str, Any], str]:
    if not MANIFEST_PATH.is_file():
        raise ApplyError("manifest.json is missing")
    manifest = read_json(MANIFEST_PATH)
    recorded_self_hash = (PACKAGE_ROOT / "manifest.sha256").read_text(encoding="utf-8").strip()
    expected_self_hash = f"{sha256_file(MANIFEST_PATH)}  manifest.json"
    if recorded_self_hash != expected_self_hash:
        raise ApplyError("manifest.sha256 self-hash mismatch")
    if manifest.get("package_id") != PACKAGE_ROOT.name:
        raise ApplyError("Manifest package_id does not match package directory")
    inputs = manifest.get("semantic_inputs")
    outputs = manifest.get("derived_outputs")
    if not isinstance(inputs, dict) or not inputs:
        raise ApplyError("Manifest semantic_inputs is missing or empty")
    if not isinstance(outputs, list):
        raise ApplyError("Manifest derived_outputs must be a list")

    expected_inventory = set(inputs) | set(outputs) | {"manifest.json"}
    actual_inventory = {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file()
    }
    if actual_inventory != expected_inventory:
        missing = sorted(expected_inventory - actual_inventory)
        unmanifested = sorted(actual_inventory - expected_inventory)
        raise ApplyError(
            f"Manifest inventory mismatch; missing={missing}; unmanifested={unmanifested}"
        )

    input_digest_rows: list[dict[str, Any]] = []
    for relative_path, expected in sorted(inputs.items()):
        if not isinstance(expected, dict):
            raise ApplyError(f"Invalid manifest entry: {relative_path}")
        path = PACKAGE_ROOT / relative_path
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        if actual_hash != expected.get("sha256") or actual_bytes != expected.get("bytes"):
            raise ApplyError(f"Manifest hash/size mismatch: {relative_path}")
        input_digest_rows.append(
            {"path": relative_path, "sha256": actual_hash, "bytes": actual_bytes}
        )
    actual_set_hash = hashlib.sha256(canonical_json_bytes(input_digest_rows)).hexdigest()
    if actual_set_hash != manifest.get("semantic_input_set_sha256"):
        raise ApplyError("Manifest semantic_input_set_sha256 mismatch")

    decisions = read_json(PACKAGE_ROOT / "human_decisions.json")
    payload = decisions.get("decision_payload")
    actual_decision_hash = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if actual_decision_hash != decisions.get("decision_set_sha256"):
        raise ApplyError("human_decisions.json decision_set_sha256 mismatch")
    if actual_decision_hash != manifest.get("decision_set_sha256"):
        raise ApplyError("Manifest decision_set_sha256 mismatch")
    return manifest, sha256_file(MANIFEST_PATH)


def connect_read_only(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def schema_identity(connection: sqlite3.Connection) -> tuple[str, str]:
    version_row = connection.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone()
    version = version_row[0] if version_row else ""
    rows = connection.execute(
        """SELECT name,sql FROM sqlite_master
           WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'
           ORDER BY type,name"""
    ).fetchall()
    material = "\n".join(f"{row[0]}\n{row[1] or ''}" for row in rows)
    return version, hashlib.sha256(material.encode("utf-8")).hexdigest()


def table_names(connection: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            """SELECT name FROM sqlite_master
               WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"""
        )
    ]


def json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    return value


def snapshot_database(connection: sqlite3.Connection) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for table in table_names(connection):
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info([{table}])")]
        encoded_rows = []
        for row in connection.execute(f"SELECT * FROM [{table}]"):
            item = {column: json_safe(row[column]) for column in columns}
            encoded_rows.append(
                json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )
        snapshot[table] = sorted(encoded_rows)
    return snapshot


def table_fingerprint(rows: list[str]) -> str:
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def semantic_diff(
    before: dict[str, list[str]], after: dict[str, list[str]]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for table in sorted(set(before) | set(after)):
        before_rows = before.get(table, [])
        after_rows = after.get(table, [])
        before_counter = Counter(before_rows)
        after_counter = Counter(after_rows)
        added: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        for encoded, count in sorted((after_counter - before_counter).items()):
            added.extend(json.loads(encoded) for _ in range(count))
        for encoded, count in sorted((before_counter - after_counter).items()):
            removed.extend(json.loads(encoded) for _ in range(count))
        result[table] = {
            "before_count": len(before_rows),
            "after_count": len(after_rows),
            "delta": len(after_rows) - len(before_rows),
            "before_semantic_sha256": table_fingerprint(before_rows),
            "after_semantic_sha256": table_fingerprint(after_rows),
            "added_rows": added,
            "removed_rows": removed,
        }
    return result


def query_all_names(connection: sqlite3.Connection) -> list[dict[str, str]]:
    rows = connection.execute(
        """SELECT node_id,canonical_name,primary_type,'canonical' AS source,
                  canonical_name AS value
           FROM nodes
           UNION ALL
           SELECT n.node_id,n.canonical_name,n.primary_type,'alias',a.alias
           FROM node_aliases a JOIN nodes n ON n.node_id=a.node_id"""
    ).fetchall()
    return [dict(row) for row in rows]


def exact_object_matches(connection: sqlite3.Connection, value: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT DISTINCT n.node_id,n.canonical_name,n.primary_type
               FROM nodes n LEFT JOIN node_aliases a ON a.node_id=n.node_id
               WHERE n.canonical_name=? COLLATE NOCASE OR a.alias=? COLLATE NOCASE
               ORDER BY n.node_id""",
            (value, value),
        )
    ]


def rejected_and_deferred_values() -> list[str]:
    values: list[str] = []
    specs = [
        ("deferred_items.csv", ("endpoint", "canonical_name")),
        ("rejected_items.csv", ("endpoint", "proposed_canonical_name")),
    ]
    for filename, columns in specs:
        for row in read_csv_rows(PACKAGE_ROOT / filename):
            for column in columns:
                value = row.get(column, "").strip()
                if value and value not in values:
                    values.append(value)
    return values


def current_part_of_cycles(connection: sqlite3.Connection) -> list[list[str]]:
    graph: dict[str, list[str]] = {}
    rows = connection.execute(
        """SELECT from_node_id,to_node_id FROM node_relations
           WHERE relation_type='part_of' AND status='current'"""
    ).fetchall()
    for row in rows:
        graph.setdefault(row[0], []).append(row[1])
        graph.setdefault(row[1], [])

    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for neighbor in graph.get(node, []):
            if state.get(neighbor, 0) == 0:
                visit(neighbor)
            elif state.get(neighbor) == 1:
                index = stack.index(neighbor)
                cycle = stack[index:] + [neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def relation_id(row: dict[str, str]) -> str:
    material = "|".join(
        [
            "B2C-20260819",
            row["from_ref"],
            row["relation_type"],
            row["to_ref"],
            row["scope"],
        ]
    )
    suffix = hashlib.sha256(material.encode("utf-8")).hexdigest()[:8].upper()
    return f"REL_20260819_{suffix}"


def load_inputs() -> dict[str, Any]:
    values = {
        "decisions": read_json(PACKAGE_ROOT / "human_decisions.json"),
        "resolution": read_json(PACKAGE_ROOT / "db_resolution.json"),
        "nodes": read_csv_rows(PACKAGE_ROOT / "approved_nodes.csv"),
        "aliases": read_csv_rows(PACKAGE_ROOT / "approved_aliases.csv"),
        "reuse": read_csv_rows(PACKAGE_ROOT / "reuse_mapping.csv"),
        "structural": read_csv_rows(PACKAGE_ROOT / "structural_relations.csv"),
    }
    if len(values["nodes"]) != 24:
        raise ApplyError("approved_nodes.csv must contain exactly 24 rows")
    if len(values["aliases"]) != 2:
        raise ApplyError("approved_aliases.csv must contain exactly 2 rows")
    if len(values["reuse"]) != 11:
        raise ApplyError("reuse_mapping.csv must contain exactly 11 rows")
    if len(values["structural"]) != 24:
        raise ApplyError("structural_relations.csv must contain exactly 24 review rows")
    if any(row.get("approval_status") != "APPROVED_CREATE" for row in values["nodes"]):
        raise ApplyError("Every approved node row must be APPROVED_CREATE")
    if any(row.get("approval_status") != "APPROVED_ALIAS" for row in values["aliases"]):
        raise ApplyError("Every alias row must be APPROVED_ALIAS")
    if any(row.get("approval_status") != "APPROVED_REUSE" for row in values["reuse"]):
        raise ApplyError("Every reuse row must be APPROVED_REUSE")

    approved_structure = [
        row
        for row in values["structural"]
        if row.get("approval_status") == "APPROVED_FOR_IMPORT"
    ]
    decisions_approved = values["decisions"]["decision_payload"]["structural_relations"][
        "approved_for_import"
    ]
    if approved_structure or decisions_approved:
        csv_ids = {row["relation_decision_id"] for row in approved_structure}
        decision_ids = {row["relation_decision_id"] for row in decisions_approved}
        if csv_ids != decision_ids:
            raise ApplyError("Structural approval rows do not match human decision payload")
    values["approved_structure"] = approved_structure

    decision_creates = {
        (row["decision_id"], row["canonical_name"], row["primary_type"])
        for row in values["decisions"]["decision_payload"]["create"]
    }
    csv_creates = {
        (row["decision_id"], row["canonical_name"], row["primary_type"])
        for row in values["nodes"]
    }
    if decision_creates != csv_creates:
        raise ApplyError("approved_nodes.csv does not match human decision payload")
    return values


def validate_preconditions(
    connection: sqlite3.Connection,
    manifest: dict[str, Any],
    values: dict[str, Any],
) -> dict[str, Any]:
    version, schema_hash = schema_identity(connection)
    if version != EXPECTED_SCHEMA_VERSION or schema_hash != EXPECTED_SCHEMA_SHA256:
        raise ApplyError(
            f"Schema mismatch: version={version!r}, schema_sha256={schema_hash}"
        )

    all_names = query_all_names(connection)
    normalized_existing: dict[str, list[dict[str, str]]] = {}
    for row in all_names:
        normalized_existing.setdefault(normalize_identity(row["value"]), []).append(row)

    internal_names: dict[str, str] = {}
    for row in values["nodes"]:
        node_id = row["node_id"]
        if connection.execute("SELECT 1 FROM nodes WHERE node_id=?", (node_id,)).fetchone():
            raise ApplyError(f"CREATE Node ID already exists: {node_id}")
        name = row["canonical_name"]
        if exact_object_matches(connection, name):
            raise ApplyError(f"Canonical or alias collision: {name}")
        normalized = normalize_identity(name)
        if normalized_existing.get(normalized):
            raise ApplyError(f"Equivalent normalized existing Node/name: {name}")
        if normalized in internal_names and internal_names[normalized] != node_id:
            raise ApplyError(f"Internal CREATE identity collision: {name}")
        internal_names[normalized] = node_id

    create_ids = {row["node_id"] for row in values["nodes"]}
    for row in values["aliases"]:
        if row["node_ref"] not in create_ids:
            raise ApplyError(f"Alias target is not an approved CREATE Node: {row['alias']}")
        alias = row["alias"]
        if exact_object_matches(connection, alias):
            raise ApplyError(f"Approved alias collision: {alias}")
        normalized = normalize_identity(alias)
        if normalized_existing.get(normalized):
            raise ApplyError(f"Approved alias normalized collision: {alias}")
        owner = internal_names.get(normalized)
        if owner and owner != row["node_ref"]:
            raise ApplyError(f"Approved alias collides with another CREATE Node: {alias}")
        internal_names[normalized] = row["node_ref"]

    for row in values["reuse"]:
        match = connection.execute(
            """SELECT node_id,canonical_name,primary_type,status FROM nodes
               WHERE node_id=? AND canonical_name=? COLLATE NOCASE AND primary_type=?""",
            (row["existing_node_id"], row["canonical_name"], row["primary_type"]),
        ).fetchall()
        if len(match) != 1 or match[0]["status"] != "active":
            raise ApplyError(f"REUSE target is not uniquely active: {row['endpoint']}")

    for row in values["structural"]:
        if not row.get("to_ref"):
            continue
        parent = connection.execute(
            """SELECT node_id,canonical_name,primary_type,status FROM nodes
               WHERE node_id=? AND canonical_name=?""",
            (row["to_ref"], row["to_name"]),
        ).fetchall()
        if len(parent) != 1 or parent[0]["status"] != "active":
            raise ApplyError(f"Structural parent no longer uniquely exists: {row['to_name']}")
        if row.get("relation_type") != "part_of":
            raise ApplyError("Only part_of may appear in structural_relations.csv")

    forbidden = connection.execute(
        "SELECT node_id FROM node_aliases WHERE alias=? COLLATE NOCASE", (FORBIDDEN_ALIAS,)
    ).fetchall()
    if forbidden:
        raise ApplyError(f"Forbidden alias already exists: {FORBIDDEN_ALIAS}")

    unexpected_objects = []
    for value in rejected_and_deferred_values():
        matches = exact_object_matches(connection, value)
        if matches:
            unexpected_objects.append({"object": value, "matches": matches})
    if unexpected_objects:
        raise ApplyError(f"Deferred/rejected objects already exist: {unexpected_objects}")

    accepted_proposals = connection.execute(
        "SELECT COUNT(*) FROM proposals WHERE status='accepted'"
    ).fetchone()[0]
    if accepted_proposals != 0:
        raise ApplyError(f"Expected zero accepted Proposals, found {accepted_proposals}")
    current_views = connection.execute("SELECT COUNT(*) FROM current_views").fetchone()[0]
    if current_views != 0:
        raise ApplyError(f"Expected zero Current Views, found {current_views}")

    expected_counts = manifest["database_precondition"]["table_counts"]
    for table, expected in expected_counts.items():
        actual = connection.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        if actual != expected:
            raise ApplyError(f"Precondition count mismatch for {table}: {actual} != {expected}")

    cycles = current_part_of_cycles(connection)
    if cycles:
        raise ApplyError(f"Existing current part_of cycle detected: {cycles}")
    return {
        "schema_version": version,
        "schema_sha256": schema_hash,
        "create_collision_count": 0,
        "approved_alias_collision_count": 0,
        "reuse_targets_uniquely_active": len(values["reuse"]),
        "deferred_rejected_objects_present": 0,
        "forbidden_alias_present": False,
        "current_part_of_cycle_count": 0,
        "accepted_proposals": accepted_proposals,
        "current_views": current_views,
    }


def validate_diff(
    diff: dict[str, dict[str, Any]], values: dict[str, Any]
) -> None:
    allowed_node_ids = {row["node_id"] for row in values["nodes"]}
    allowed_aliases = {row["alias"] for row in values["aliases"]}
    allowed_relation_ids = {relation_id(row) for row in values["approved_structure"]}
    for table, table_diff in diff.items():
        if table_diff["removed_rows"]:
            raise ApplyError(f"Unexpected removed/updated rows in {table}")
        added = table_diff["added_rows"]
        if table == "nodes":
            if {row["node_id"] for row in added} != allowed_node_ids:
                raise ApplyError("Node additions differ from approved CREATE rows")
        elif table == "node_aliases":
            if {row["alias"] for row in added} != allowed_aliases:
                raise ApplyError("Alias additions differ from approved aliases")
        elif table == "node_relations":
            if {row["relation_id"] for row in added} != allowed_relation_ids:
                raise ApplyError("Relation additions differ from approved structural rows")
        elif added:
            raise ApplyError(f"Unexpected additions in forbidden table: {table}")


def execute_transaction(
    database_path: Path,
    values: dict[str, Any],
    before_snapshot: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.isolation_level = None
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("BEGIN IMMEDIATE")
        all_names = query_all_names(connection)
        normalized_existing = {normalize_identity(row["value"]) for row in all_names}
        for row in values["nodes"]:
            if exact_object_matches(connection, row["canonical_name"]):
                raise ApplyError(f"CREATE collision appeared at write gate: {row['canonical_name']}")
            if normalize_identity(row["canonical_name"]) in normalized_existing:
                raise ApplyError(
                    f"Normalized identity collision appeared at write gate: {row['canonical_name']}"
                )
        for row in values["reuse"]:
            match = connection.execute(
                """SELECT status FROM nodes WHERE node_id=? AND canonical_name=? COLLATE NOCASE
                   AND primary_type=?""",
                (row["existing_node_id"], row["canonical_name"], row["primary_type"]),
            ).fetchall()
            if len(match) != 1 or match[0]["status"] != "active":
                raise ApplyError(f"REUSE target drifted at write gate: {row['endpoint']}")

        for row in values["nodes"]:
            connection.execute(
                """INSERT INTO nodes(
                       node_id,canonical_name,primary_type,description,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                (
                    row["node_id"],
                    row["canonical_name"],
                    row["primary_type"],
                    row["description"],
                    "active",
                    row["created_at"],
                    row["created_at"],
                ),
            )

        for row in values["aliases"]:
            connection.execute(
                "INSERT INTO node_aliases(alias,node_id) VALUES(?,?)",
                (row["alias"], row["node_ref"]),
            )

        for row in values["approved_structure"]:
            connection.execute(
                """INSERT INTO node_relations(
                       relation_id,from_node_id,relation_type,to_node_id,scope,
                       valid_from,valid_to,confidence,status,evidence_claim_id,created_at
                   ) VALUES(?,?,?,?,?,'','',NULL,'current',NULL,?)""",
                (
                    relation_id(row),
                    row["from_ref"],
                    row["relation_type"],
                    row["to_ref"],
                    row["scope"],
                    "2026-08-19T00:00:00+08:00",
                ),
            )

        for row in values["nodes"]:
            count = connection.execute(
                "SELECT COUNT(*) FROM nodes WHERE canonical_name=? COLLATE NOCASE",
                (row["canonical_name"],),
            ).fetchone()[0]
            if count != 1:
                raise ApplyError(f"New canonical is not unique: {row['canonical_name']}")
        for row in values["aliases"]:
            match = connection.execute(
                "SELECT node_id FROM node_aliases WHERE alias=? COLLATE NOCASE", (row["alias"],)
            ).fetchall()
            if len(match) != 1 or match[0]["node_id"] != row["node_ref"]:
                raise ApplyError(f"New alias does not resolve uniquely: {row['alias']}")

        endpoint_errors = connection.execute(
            """SELECT relation_id FROM node_relations nr
               LEFT JOIN nodes f ON f.node_id=nr.from_node_id
               LEFT JOIN nodes t ON t.node_id=nr.to_node_id
               WHERE f.node_id IS NULL OR t.node_id IS NULL OR nr.from_node_id=nr.to_node_id"""
        ).fetchall()
        if endpoint_errors:
            raise ApplyError("Structural relation endpoint/self-relation QA failed")
        cycles = current_part_of_cycles(connection)
        if cycles:
            raise ApplyError(f"Current part_of cycle QA failed: {cycles}")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_keys:
            raise ApplyError(
                f"SQLite integrity/foreign-key QA failed: integrity={integrity}, fk={foreign_keys}"
            )

        after_snapshot = snapshot_database(connection)
        diff = semantic_diff(before_snapshot, after_snapshot)
        validate_diff(diff, values)

        if diff["nodes"]["delta"] != len(values["nodes"]):
            raise ApplyError("CREATE Node count differs from the approved rows")
        if diff["node_aliases"]["delta"] != len(values["aliases"]):
            raise ApplyError("Alias count differs from the approved rows")
        if diff["node_relations"]["delta"] != len(values["approved_structure"]):
            raise ApplyError("Structural relation count differs from approved rows")

        if connection.execute("SELECT COUNT(*) FROM current_views").fetchone()[0] != 0:
            raise ApplyError("Current Views changed unexpectedly")
        if connection.execute(
            "SELECT COUNT(*) FROM proposals WHERE status='accepted'"
        ).fetchone()[0] != 0:
            raise ApplyError("Accepted Proposals changed unexpectedly")
        if connection.execute(
            "SELECT COUNT(*) FROM node_aliases WHERE alias=? COLLATE NOCASE",
            (FORBIDDEN_ALIAS,),
        ).fetchone()[0] != 0:
            raise ApplyError("Forbidden alias was created")
        for value in rejected_and_deferred_values():
            if exact_object_matches(connection, value):
                raise ApplyError(f"Deferred/rejected object was created: {value}")

        connection.execute("COMMIT")
        qa = {
            "sqlite_integrity_check": integrity,
            "foreign_key_violations": 0,
            "new_canonical_unique": len(values["nodes"]),
            "new_alias_unique_resolution": len(values["aliases"]),
            "alias_collision_count": 0,
            "reuse_mapping_unique_resolution": len(values["reuse"]),
            "structural_endpoint_errors": 0,
            "self_part_of_count": 0,
            "current_part_of_cycle_count": 0,
            "forbidden_alias_present": False,
        }
        return after_snapshot, qa
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def count_current_formal_relations(connection: sqlite3.Connection) -> int:
    return connection.execute(
        """SELECT COUNT(*) FROM node_relations
           WHERE status='current' AND relation_type<>'part_of'"""
    ).fetchone()[0]


def count_current_part_of(connection: sqlite3.Connection) -> int:
    return connection.execute(
        """SELECT COUNT(*) FROM node_relations
           WHERE status='current' AND relation_type='part_of'"""
    ).fetchone()[0]


def apply(database_path: Path, target_identity: str, authorization_token: str) -> dict[str, Any]:
    manifest, manifest_sha = validate_manifest()
    values = load_inputs()
    database_path = database_path.resolve(strict=True)
    if not database_path.is_file():
        raise ApplyError("DatabasePath is not a file")
    if not os.access(database_path, os.W_OK):
        raise ApplyError("Target database is not writable")
    with database_path.open("r+b"):
        pass

    pre_hash = sha256_file(database_path)
    expected_hash = manifest["database_precondition"]["sha256"]
    if pre_hash != expected_hash:
        raise ApplyError(f"Target DB SHA mismatch: {pre_hash} != {expected_hash}")
    expected_token = (
        f"AUTHORIZE_{target_identity.upper()}_IMPORT:{manifest_sha}:{pre_hash}"
        if target_identity == "Production"
        else f"AUTHORIZE_ISOLATED_DRY_RUN:{manifest_sha}:{pre_hash}"
    )
    if authorization_token != expected_token:
        raise ApplyError("Authorization token does not match target identity, manifest and DB SHA")

    with connect_read_only(database_path) as read_connection:
        preflight = validate_preconditions(read_connection, manifest, values)
        before_snapshot = snapshot_database(read_connection)
        formal_relations_before = count_current_formal_relations(read_connection)
        part_of_before = count_current_part_of(read_connection)

    after_snapshot, transaction_qa = execute_transaction(
        database_path, values, before_snapshot
    )
    post_hash = sha256_file(database_path)
    with connect_read_only(database_path) as read_connection:
        committed_snapshot = snapshot_database(read_connection)
        if committed_snapshot != after_snapshot:
            raise ApplyError("Committed semantic state differs from in-transaction QA snapshot")
        formal_relations_after = count_current_formal_relations(read_connection)
        part_of_after = count_current_part_of(read_connection)
        current_views_after = read_connection.execute(
            "SELECT COUNT(*) FROM current_views"
        ).fetchone()[0]
        accepted_proposals_after = read_connection.execute(
            "SELECT COUNT(*) FROM proposals WHERE status='accepted'"
        ).fetchone()[0]
        deferred_rejected_present = [
            value
            for value in rejected_and_deferred_values()
            if exact_object_matches(read_connection, value)
        ]

    diff = semantic_diff(before_snapshot, committed_snapshot)
    counts = {
        table: {
            "before": item["before_count"],
            "after": item["after_count"],
            "delta": item["delta"],
        }
        for table, item in diff.items()
    }
    expected = {
        "new_nodes_max": 24,
        "new_nodes_exact": 24,
        "new_aliases_exact": 2,
        "forbidden_alias_delta": 0,
        "deferred_node_delta": 0,
        "rejected_node_delta": 0,
        "current_view_delta": 0,
        "formal_relation_delta": 0,
        "structural_relation_delta": len(values["approved_structure"]),
        "accepted_proposal_delta": 0,
    }
    actual = {
        "new_nodes_exact": counts["nodes"]["delta"],
        "new_aliases_exact": counts["node_aliases"]["delta"],
        "forbidden_alias_delta": 0,
        "deferred_node_delta": 0,
        "rejected_node_delta": 0,
        "current_view_delta": counts["current_views"]["delta"],
        "formal_relation_delta": formal_relations_after - formal_relations_before,
        "structural_relation_delta": part_of_after - part_of_before,
        "accepted_proposal_delta": accepted_proposals_after,
    }
    comparison = {
        key: {"expected": value, "actual": actual.get(key), "match": actual.get(key) == value}
        for key, value in expected.items()
        if key != "new_nodes_max"
    }
    comparison["new_nodes_max"] = {
        "expected": expected["new_nodes_max"],
        "actual": actual["new_nodes_exact"],
        "match": actual["new_nodes_exact"] <= expected["new_nodes_max"],
    }
    if not all(item["match"] for item in comparison.values()):
        raise ApplyError(f"Expected/actual comparison failed: {comparison}")
    if deferred_rejected_present:
        raise ApplyError(
            f"Deferred/rejected objects appeared after import: {deferred_rejected_present}"
        )

    unchanged_tables = [
        table
        for table, item in diff.items()
        if item["delta"] == 0 and not item["added_rows"] and not item["removed_rows"]
    ]
    return {
        "metadata": {
            "artifact": "B2C isolated/apply deterministic report",
            "status": "PASS",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "package_id": PACKAGE_ROOT.name,
            "manifest_sha256": manifest_sha,
            "semantic_input_set_sha256": manifest["semantic_input_set_sha256"],
            "decision_set_sha256": manifest["decision_set_sha256"],
            "target_identity": target_identity,
            "database_path_resolved_absolute": str(database_path),
        },
        "database": {
            "pre_import_sha256": pre_hash,
            "post_import_sha256": post_hash,
            "schema_version": EXPECTED_SCHEMA_VERSION,
            "schema_sha256": EXPECTED_SCHEMA_SHA256,
        },
        "pre_write_verification": {
            "manifest_complete_and_valid": True,
            "apply_script_hash_valid": True,
            "target_sha_precondition_match": True,
            "schema_compatible": True,
            "target_writable": True,
            "target_identity_recorded": target_identity,
            "create_nodes_absent": True,
            "reuse_targets_unique": True,
            "authorization_token_valid": True,
            "details": preflight,
        },
        "transaction": {
            "sequence": ["BEGIN IMMEDIATE", "nodes", "aliases", "approved structural relations", "QA", "COMMIT"],
            "committed": True,
            "rollback_on_exception": True,
            "partial_import": False,
        },
        "expected_vs_actual": comparison,
        "counts": counts,
        "semantic_diff": diff,
        "qa": {
            **transaction_qa,
            "deferred_rejected_objects_present": deferred_rejected_present,
            "existing_frozen_nodes_unmodified": not diff["nodes"]["removed_rows"],
            "existing_aliases_unmodified": not diff["node_aliases"]["removed_rows"],
            "current_views_after": current_views_after,
            "current_formal_relations_before": formal_relations_before,
            "current_formal_relations_after": formal_relations_after,
            "current_part_of_before": part_of_before,
            "current_part_of_after": part_of_after,
            "accepted_proposals_after": accepted_proposals_after,
            "source_and_claim_tables_unchanged": all(
                table in unchanged_tables
                for table in ["sources", "source_node_links", "source_relations", "claims", "claim_node_links", "claim_relations"]
            ),
            "all_non_import_tables_unchanged": all(
                table in {"nodes", "node_aliases", "node_relations"} or table in unchanged_tables
                for table in diff
            ),
        },
        "external_immutability_proofs": {
            "production_db": "TO_BE_RECORDED_BY_READ_ONLY_ORCHESTRATOR",
            "gold_v1_0_0": "TO_BE_RECORDED_BY_READ_ONLY_ORCHESTRATOR",
            "historical_quarantine_package": "TO_BE_RECORDED_BY_READ_ONLY_ORCHESTRATOR"
        },
        "stop_gate": {
            "production_write_performed": target_identity == "Production",
            "run_007_started": False,
            "gold_v1_0_0_modified": False,
            "ima_called": False,
            "real_llm_called": False,
            "b2d_started": False,
            "automatic_promotion_performed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply the frozen pro_a R1 B.2C package")
    parser.add_argument("--database-path", required=True)
    parser.add_argument("--target-identity", choices=["Isolated", "Production"], required=True)
    parser.add_argument("--authorization-token", required=True)
    parser.add_argument("--report-path", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_path).resolve()
    try:
        manifest = read_json(MANIFEST_PATH)
        protected = set(manifest.get("semantic_inputs", {})) | {"manifest.json"}
        try:
            relative_report = report_path.relative_to(PACKAGE_ROOT).as_posix()
        except ValueError:
            relative_report = ""
        if relative_report in protected:
            raise ApplyError("ReportPath may not overwrite a manifest or semantic input")
        report = apply(
            Path(args.database_path), args.target_identity, args.authorization_token
        )
        atomic_write_json(report_path, report)
        print(json.dumps({
            "status": "PASS",
            "report_path": str(report_path),
            "database_post_sha256": report["database"]["post_import_sha256"],
        }, ensure_ascii=False))
        return 0
    except Exception as exc:
        observed_database_sha = "UNAVAILABLE"
        expected_database_sha = "UNAVAILABLE"
        target_differs_from_precondition = None
        try:
            target_path = Path(args.database_path).resolve(strict=True)
            observed_database_sha = sha256_file(target_path)
            expected_database_sha = read_json(MANIFEST_PATH)["database_precondition"]["sha256"]
            target_differs_from_precondition = observed_database_sha != expected_database_sha
        except Exception:
            pass
        failure = {
            "metadata": {
                "artifact": "B2C apply failure report",
                "status": "FAIL_CLOSED",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            "error": f"{type(exc).__name__}: {exc}",
            "target_database_sha256_observed": observed_database_sha,
            "target_database_sha256_precondition": expected_database_sha,
            "target_differs_from_precondition": target_differs_from_precondition,
            "writes_committed": "UNKNOWN; inspect target_differs_from_precondition and transaction stage",
        }
        try:
            atomic_write_json(report_path, failure)
        except Exception:
            pass
        print(f"FAIL_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
