"""Stage 1 bounded operator projection and immutable operating limits."""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from pro_a.production_promotion import canonical_sha256
from .config import BoundaryError, checked_path
from .review_store import schema_version
from .store import Store


STAGE1_POLICY_VERSION = "phase43-stage1-bounded-operator-v1"


@dataclass(frozen=True)
class Stage1Limits:
    sources_per_run: int = 1
    runs_per_24h: int = 3
    review_page_default: int = 25
    review_page_max: int = 100
    review_wip_soft: int = 100
    review_wip_hard: int = 200
    semantic_parent_cap: int = 8
    jobs_per_run: int = 31
    worker_concurrency: int = 1
    operator_nominal_cases: int = 60
    operator_nominal_minutes: int = 60
    operator_guardrail_minutes: int = 75


LIMITS = Stage1Limits()


def _canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _write_once(path: Path, content: bytes) -> None:
    path = checked_path(path, missing=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise BoundaryError("STAGE1_MIGRATION_ARTIFACT_CONFLICT")
        return
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def prepare_stage1_scale(config) -> dict[str, Any]:
    """Explicit offline Workbench v9 -> v10 migration; canonical DB is untouched."""
    config.validate()
    path = checked_path(config.state_db)
    backup = path.with_name(path.name + ".stage43-stage0-backup")
    receipt_path = path.with_name(path.name + ".stage43-stage1-migration.json")
    for suffix in ("-wal", "-shm", "-journal"):
        if path.with_name(path.name + suffix).exists():
            raise BoundaryError("STAGE1_MIGRATION_REQUIRES_OFFLINE")
    with Store(config).connect() as connection:
        version = schema_version(connection)
        if version == "10":
            return {"status": "ALREADY_PREPARED", "schema_version": "10"}
        if version != "9":
            raise BoundaryError("DOMAIN_SCHEMA_REQUIRED")
        active = connection.execute(
            "SELECT 1 FROM cloud_jobs WHERE state IN ('QUEUED','RUNNING') LIMIT 1"
        ).fetchone()
        active_run = connection.execute(
            """SELECT 1 FROM source_processing_runs
               WHERE state NOT IN ('HUMAN_REVIEW_REQUIRED','FAILED','BLOCKED','RECOVERY_REQUIRED')
               LIMIT 1"""
        ).fetchone()
        if active or active_run:
            raise BoundaryError("STAGE1_MIGRATION_REQUIRES_DRAIN")
        review_artifact_ids = [row[0] for row in connection.execute(
            """SELECT artifact_id FROM registered_packets
               WHERE COALESCE(artifact_kind,'REVIEW_PACKET')='REVIEW_PACKET'
               ORDER BY registered_at,artifact_id"""
        )]
    if review_artifact_ids:
        from .review_workbench import ReviewWorkbench
        workbench = ReviewWorkbench(config)
        for artifact_id in review_artifact_ids:
            _blank, _run, _dto, basis = workbench._context(artifact_id)
            with Store(config).connect() as connection:
                workbench._state(connection, artifact_id, basis)
    before = path.read_bytes()
    _write_once(backup, before)
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN EXCLUSIVE")
        if schema_version(connection) != "9":
            raise BoundaryError("WORKBENCH_SCHEMA_CHANGED")
        statements = (
            """CREATE TABLE stage1_review_projection_meta(
                artifact_id TEXT PRIMARY KEY REFERENCES registered_packets(artifact_id),
                basis_id TEXT NOT NULL, snapshot_id TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK(revision>=0),
                status TEXT NOT NULL CHECK(status IN ('DRAFT','SEALED')),
                total_rows INTEGER NOT NULL CHECK(total_rows>=0),
                pending_rows INTEGER NOT NULL CHECK(pending_rows>=0),
                policy_version TEXT NOT NULL, built_at TEXT NOT NULL,
                header_json TEXT NOT NULL
            )""",
            """CREATE TABLE stage1_review_projection(
                artifact_id TEXT NOT NULL REFERENCES stage1_review_projection_meta(artifact_id)
                    ON DELETE CASCADE,
                candidate_id TEXT NOT NULL, basis_id TEXT NOT NULL,
                native_order INTEGER NOT NULL CHECK(native_order>=0),
                candidate_type TEXT NOT NULL, source_id TEXT NOT NULL,
                created_at TEXT NOT NULL, priority_key TEXT NOT NULL,
                is_pending INTEGER NOT NULL CHECK(is_pending IN (0,1)),
                state_json TEXT, queues_json TEXT NOT NULL, domains_json TEXT NOT NULL,
                attention_json TEXT NOT NULL, native_json TEXT NOT NULL,
                PRIMARY KEY(artifact_id,candidate_id),
                UNIQUE(artifact_id,priority_key)
            )""",
            """CREATE TABLE stage1_review_projection_domains(
                artifact_id TEXT NOT NULL, candidate_id TEXT NOT NULL, domain_id TEXT NOT NULL,
                PRIMARY KEY(artifact_id,candidate_id,domain_id),
                FOREIGN KEY(artifact_id,candidate_id)
                    REFERENCES stage1_review_projection(artifact_id,candidate_id) ON DELETE CASCADE
            )""",
            """CREATE TABLE stage1_operator_control(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                policy_version TEXT NOT NULL, intake_paused INTEGER NOT NULL CHECK(intake_paused IN (0,1)),
                pause_reason TEXT NOT NULL, updated_at TEXT NOT NULL
            )""",
            """CREATE INDEX stage1_review_page
                ON stage1_review_projection(artifact_id,is_pending,candidate_type,priority_key)""",
            """CREATE INDEX stage1_review_pending_page
                ON stage1_review_projection(artifact_id,is_pending,priority_key)""",
            """CREATE INDEX stage1_review_global_pending
                ON stage1_review_projection(is_pending,created_at,artifact_id,candidate_id)""",
            """CREATE INDEX stage1_review_domain
                ON stage1_review_projection_domains(domain_id,artifact_id,candidate_id)""",
            "CREATE INDEX stage1_review_audit_lookup ON review_audit(artifact_id,event_id)",
            """CREATE INDEX stage1_source_run_history
                ON source_processing_runs(source_id,created_at DESC,processing_run_id)""",
        )
        for statement in statements:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO stage1_operator_control VALUES(1,?,0,'',?)",
            (STAGE1_POLICY_VERSION, datetime.now(timezone.utc).isoformat()),
        )
        connection.execute("UPDATE workbench_meta SET value='10' WHERE key='schema_version'")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise BoundaryError("STAGE1_MIGRATION_FOREIGN_KEYS")
    projection = Stage1ReviewProjection(config)
    for artifact_id in review_artifact_ids:
        projection.rebuild(artifact_id)
    receipt = {
        "document_type": "phase43_stage1_workbench_migration_receipt",
        "schema_version": "10",
        "status": "STAGE1_SCALE_SCHEMA_PREPARED",
        "policy_version": STAGE1_POLICY_VERSION,
        "limits": asdict(LIMITS),
        "backup_sha256": hashlib.sha256(before).hexdigest(),
        "migrated_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "review_projections_built": len(review_artifact_ids),
        "canonical_db_write": False,
    }
    _write_once(receipt_path, (_canonical(receipt) + "\n").encode("utf-8"))
    return receipt


def rollback_stage1_scale(config) -> dict[str, Any]:
    """Restore the exact v9 backup only while the migrated DB is still unused."""
    config.validate()
    path = checked_path(config.state_db)
    receipt_path = checked_path(path.with_name(path.name + ".stage43-stage1-migration.json"))
    backup = checked_path(path.with_name(path.name + ".stage43-stage0-backup"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for suffix in ("-wal", "-shm", "-journal"):
        if path.with_name(path.name + suffix).exists():
            raise BoundaryError("STAGE1_MIGRATION_REQUIRES_OFFLINE")
    if hashlib.sha256(backup.read_bytes()).hexdigest() != receipt["backup_sha256"]:
        raise BoundaryError("STAGE1_BACKUP_CORRUPT")
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["migrated_sha256"]:
        raise BoundaryError("STAGE1_ROLLBACK_STATE_CHANGED")
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        if schema_version(connection) != "10":
            raise BoundaryError("STAGE1_SCHEMA_REQUIRED")
    path.write_bytes(backup.read_bytes())
    return {
        "status": "ROLLED_BACK", "schema_version": "9",
        "sha256": receipt["backup_sha256"],
    }


def _snapshot(artifact_id: str, basis_id: str, revision: int, status: str,
              total_rows: int) -> str:
    return canonical_sha256({
        "artifact_id": artifact_id, "basis_id": basis_id, "revision": revision,
        "status": status, "total_rows": total_rows, "policy_version": STAGE1_POLICY_VERSION,
    })


def _bool_priority(value: bool) -> str:
    return "0" if value else "1"


def _row_projection(row: Mapping[str, Any], *, artifact_id: str, basis_id: str,
                    native_order: int, source_id: str, created_at: str,
                    state: Mapping[str, Any] | None, domains: list[str]) -> dict[str, Any]:
    content = dict(row.get("content") or {})
    guards = dict(content.get("semantic_admission") or {})
    collision = dict(content.get("collision_diagnostics") or {})
    targets = list((content.get("exact_production_resolution") or {}).get(
        "candidate_target_node_ids"
    ) or [])
    recovery = bool(content.get("recovery_required") or content.get("integrity_block"))
    identity_collision = bool(
        len(targets) > 1
        or collision.get("prospective_node_id_exists")
        or collision.get("package_internal_normalized_term_collisions")
    )
    official_view = bool(
        content.get("official_view_directly_affected")
        or content.get("current_view_id")
        or content.get("official_view_id")
    )
    evidence_warning = bool(
        guards.get("guard_reasons")
        or content.get("current_defer_reason")
        or content.get("review_admitted") is False
        or (content.get("evidence_validation") or {}).get("fidelity_status")
            not in (None, "", "EXACT")
    )
    candidate_type = str(row["candidate_type"])
    new_node = candidate_type == "NODE" and not targets
    ambiguity = bool(
        candidate_type == "PARENT_PLACEMENT"
        or content.get("parent_ambiguity")
        or content.get("relation_ambiguity")
    )
    domain_novelty = bool(content.get("domain_novelty"))
    confidence = content.get("confidence")
    low_confidence = confidence is None or (
        isinstance(confidence, (int, float)) and confidence < 0.5
    )
    attention = {
        "recovery_or_integrity_block": recovery,
        "identity_collision": identity_collision,
        "official_view_directly_affected": official_view,
        "evidence_warning": evidence_warning,
        "new_node_create": new_node,
        "parent_or_relation_ambiguity": ambiguity,
        "domain_novelty": domain_novelty,
        "low_confidence_bucket": low_confidence,
        "operator_source_priority": 0,
    }
    flags = (
        recovery, identity_collision, official_view, evidence_warning, new_node,
        ambiguity, domain_novelty, low_confidence,
    )
    priority_key = "|".join((
        *(_bool_priority(value) for value in flags),
        "999999999", created_at, source_id, artifact_id,
        f"{native_order:012d}", str(row["candidate_id"]),
    ))
    decision = str((state or {}).get("decision") or "")
    queues = ["completed", "recently_decided"] if state else ["needs_review", "human_required"]
    if candidate_type == "NODE":
        queues.append("entity_resolution")
    if candidate_type == "PARENT_PLACEMENT":
        queues.append("parent_placement")
    if decision in ("DEFER", "KEEP_NEEDS_REVIEW"):
        queues.append("deferred")
    if any(flags):
        queues.append("high_attention")
    return {
        "artifact_id": artifact_id, "candidate_id": str(row["candidate_id"]),
        "basis_id": basis_id, "native_order": native_order,
        "candidate_type": candidate_type, "source_id": source_id,
        "created_at": created_at, "priority_key": priority_key,
        "is_pending": 0 if state else 1,
        "state_json": _canonical(dict(state)) if state else None,
        "queues_json": _canonical(queues), "domains_json": _canonical(domains),
        "attention_json": _canonical(attention), "native_json": _canonical(dict(row)),
    }


class Stage1ReviewProjection:
    """Rebuildable list projection. Native packet/audit remains the authority."""

    def __init__(self, config):
        self.config = config
        self.store = Store(config)

    def rebuild(self, artifact_id: str) -> dict[str, Any]:
        from .review_workbench import GROUPS, ReviewWorkbench

        workbench = ReviewWorkbench(self.config)
        blank, _run, dto, basis = workbench._context(artifact_id)
        with self.store.connect(operator_write=True) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            if schema_version(connection) != "10":
                raise BoundaryError("STAGE1_SCHEMA_REQUIRED")
            draft, states, _audit = workbench._state(connection, artifact_id, basis)
            registered = connection.execute(
                "SELECT registered_at FROM registered_packets WHERE artifact_id=?", (artifact_id,)
            ).fetchone()
            source_id = str((dto.get("source") or {}).get("source_id") or "")
            assignment = connection.execute(
                """SELECT primary_domain,packs_json FROM domain_assignments
                   WHERE object_type='Source' AND object_id=?
                   ORDER BY revision DESC LIMIT 1""", (source_id,),
            ).fetchone()
            domains: list[str] = []
            if assignment:
                domains = [str(assignment["primary_domain"])]
                for identity in json.loads(assignment["packs_json"]):
                    domain_id = str(identity.get("domain_id") or "")
                    if domain_id and domain_id not in domains:
                        domains.append(domain_id)
            native = [row for group in GROUPS for row in blank[group]]
            status = draft["status"] if draft else "DRAFT"
            revision = int(draft["revision"]) if draft else 0
            snapshot_id = _snapshot(artifact_id, basis, revision, status, len(native))
            built_at = datetime.now(timezone.utc).isoformat()
            connection.execute("DELETE FROM stage1_review_projection_meta WHERE artifact_id=?", (artifact_id,))
            connection.execute(
                """INSERT INTO stage1_review_projection_meta
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (artifact_id, basis, snapshot_id, revision, status, len(native),
                 len(native) - len(states), STAGE1_POLICY_VERSION, built_at,
                 _canonical({key: dto[key] for key in (
                     "artifact_id", "packet_id", "packet_file_sha256",
                     "immutable_packet_sha256", "run_id", "mode", "validation_state",
                     "packet_status", "source", "summary", "excluded_relation_inventory",
                     "capabilities",
                 )})),
            )
            created_at = str(registered["registered_at"])
            for index, row in enumerate(native):
                projected = _row_projection(
                    row, artifact_id=artifact_id, basis_id=basis, native_order=index,
                    source_id=source_id, created_at=created_at,
                    state=states.get(row["candidate_id"]), domains=domains,
                )
                connection.execute(
                    """INSERT INTO stage1_review_projection VALUES(
                       :artifact_id,:candidate_id,:basis_id,:native_order,:candidate_type,
                       :source_id,:created_at,:priority_key,:is_pending,:state_json,
                       :queues_json,:domains_json,:attention_json,:native_json)""", projected,
                )
                connection.executemany(
                    "INSERT INTO stage1_review_projection_domains VALUES(?,?,?)",
                    [(artifact_id, row["candidate_id"], domain_id) for domain_id in domains],
                )
        return {
            "artifact_id": artifact_id, "basis_id": basis,
            "snapshot_id": snapshot_id, "revision": revision,
            "total_rows": len(native), "pending_rows": len(native) - len(states),
            "projection_authority": False,
        }

    @staticmethod
    def _encode_cursor(snapshot_id: str, priority_key: str) -> str:
        value = _canonical({"snapshot_id": snapshot_id, "priority_key": priority_key})
        return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> dict[str, str]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            if set(value) != {"snapshot_id", "priority_key"}:
                raise ValueError
            return {key: str(value[key]) for key in value}
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            raise BoundaryError("INVALID_REVIEW_CURSOR") from None

    def page(self, artifact_id: str, *, cursor: str | None = None,
             limit: int = LIMITS.review_page_default, queue: str = "",
             candidate_type: str = "", domain_id: str = "") -> dict[str, Any]:
        if not 1 <= limit <= LIMITS.review_page_max:
            raise BoundaryError("INVALID_REVIEW_PAGE_LIMIT")
        if queue and queue not in {
            "needs_review", "human_required", "completed", "recently_decided",
            "entity_resolution", "parent_placement", "deferred", "high_attention",
        }:
            raise BoundaryError("INVALID_REVIEW_QUEUE")
        cursor_value = self._decode_cursor(cursor) if cursor else None
        with self.store.connect() as connection:
            if schema_version(connection) != "10":
                raise BoundaryError("STAGE1_SCHEMA_REQUIRED")
            meta = connection.execute(
                "SELECT * FROM stage1_review_projection_meta WHERE artifact_id=?", (artifact_id,)
            ).fetchone()
            if meta is None:
                exists = connection.execute(
                    "SELECT 1 FROM registered_packets WHERE artifact_id=?", (artifact_id,)
                ).fetchone()
                raise BoundaryError(
                    "REVIEW_PROJECTION_REQUIRED" if exists else "ARTIFACT_NOT_REGISTERED"
                )
            if cursor_value and cursor_value["snapshot_id"] != meta["snapshot_id"]:
                raise BoundaryError("STALE_REVIEW_CURSOR")
            clauses = ["p.artifact_id=?"]
            args: list[Any] = [artifact_id]
            if cursor_value:
                clauses.append("p.priority_key>?")
                args.append(cursor_value["priority_key"])
            if queue in {"needs_review", "human_required"}:
                clauses.append("p.is_pending=1")
            elif queue in {"completed", "recently_decided"}:
                clauses.append("p.is_pending=0")
            elif queue:
                clauses.append("EXISTS(SELECT 1 FROM json_each(p.queues_json) WHERE value=?)")
                args.append(queue)
            if candidate_type:
                clauses.append("p.candidate_type=?")
                args.append(candidate_type)
            if domain_id:
                clauses.append("EXISTS(SELECT 1 FROM stage1_review_projection_domains d "
                               "WHERE d.artifact_id=p.artifact_id AND d.candidate_id=p.candidate_id "
                               "AND d.domain_id=?)")
                args.append(domain_id)
            where = " AND ".join(clauses)
            rows = connection.execute(
                f"""SELECT p.* FROM stage1_review_projection p WHERE {where}
                    ORDER BY p.priority_key LIMIT ?""", (*args, limit + 1),
            ).fetchall()
            total = int(connection.execute(
                f"SELECT COUNT(*) FROM stage1_review_projection p WHERE {where}", args
            ).fetchone()[0])
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = []
        for row in rows:
            native = json.loads(row["native_json"])
            items.append({
                "candidate_id": row["candidate_id"],
                "candidate_type": row["candidate_type"],
                "native_order": row["native_order"],
                "state": json.loads(row["state_json"]) if row["state_json"] else None,
                "queues": json.loads(row["queues_json"]),
                "domains": json.loads(row["domains_json"]),
                "attention": json.loads(row["attention_json"]),
                "content": native.get("content"),
                "allowed_decisions": native.get("allowed_decisions"),
                "projection_authority": False,
            })
        next_cursor = (
            self._encode_cursor(meta["snapshot_id"], rows[-1]["priority_key"])
            if has_more and rows else None
        )
        return {
            "artifact_id": artifact_id, "basis_id": meta["basis_id"],
            "snapshot_id": meta["snapshot_id"], "revision": meta["revision"],
            "status": meta["status"], "policy_version": meta["policy_version"],
            "packet": json.loads(meta["header_json"]),
            "total_native_rows": meta["total_rows"], "pending_rows": meta["pending_rows"],
            "filtered_total": total, "limit": limit, "items": items,
            "next_cursor": next_cursor, "projection_authority": False,
        }

    def item(self, artifact_id: str, candidate_id: str) -> dict[str, Any]:
        """Bounded on-demand detail; save/seal still revalidate native authority."""
        from .review_workbench import available_actions

        with self.store.connect() as connection:
            if schema_version(connection) != "10":
                raise BoundaryError("STAGE1_SCHEMA_REQUIRED")
            meta = connection.execute(
                "SELECT * FROM stage1_review_projection_meta WHERE artifact_id=?", (artifact_id,)
            ).fetchone()
            row = connection.execute(
                """SELECT * FROM stage1_review_projection
                   WHERE artifact_id=? AND candidate_id=?""", (artifact_id, candidate_id),
            ).fetchone()
            if meta is None or row is None:
                raise BoundaryError("NOT_REVIEWABLE")
            native = json.loads(row["native_json"])
            state = json.loads(row["state_json"]) if row["state_json"] else None
            states = {candidate_id: state} if state else {}
            blank = {
                "human_completion": {"reviewer": ""},
                "claims": [], "nodes": [], "relations": [],
            }
            group = {
                "CLAIM": "claims", "NODE": "nodes",
                "PARENT_PLACEMENT": "relations",
            }[row["candidate_type"]]
            blank[group].append(native)
            if row["candidate_type"] == "PARENT_PLACEMENT":
                child_id = native["content"]["child_node_candidate_id"]
                child = connection.execute(
                    """SELECT native_json,state_json FROM stage1_review_projection
                       WHERE artifact_id=? AND candidate_id=?""", (artifact_id, child_id),
                ).fetchone()
                if child is None:
                    raise BoundaryError("REVIEW_PROJECTION_INCOMPLETE")
                blank["nodes"].append(json.loads(child["native_json"]))
                if child["state_json"]:
                    states[child_id] = json.loads(child["state_json"])
            capability = available_actions(blank, native, states)
            event = connection.execute(
                """SELECT event_id,event_type FROM review_audit
                   WHERE artifact_id=? AND candidate_id=? ORDER BY event_id DESC LIMIT 1""",
                (artifact_id, candidate_id),
            ).fetchone()
        decision = str((state or {}).get("decision") or "")
        return {
            "artifact_id": artifact_id, "candidate_id": candidate_id,
            "basis_id": meta["basis_id"], "snapshot_id": meta["snapshot_id"],
            "revision": meta["revision"], "status": meta["status"],
            "native": native, "state": state,
            "queues": json.loads(row["queues_json"]),
            "domains": json.loads(row["domains_json"]),
            "attention": json.loads(row["attention_json"]),
            **capability,
            "decision_effect": native["decision_effects"].get(decision),
            "nonpromotable": decision in ("DEFER", "KEEP_NEEDS_REVIEW", "REJECT", "DROP"),
            "undo_event_id": (
                event["event_id"] if event and event["event_type"] == "SAVE"
                and meta["status"] != "SEALED" else None
            ),
            "projection_authority": False,
        }

    @staticmethod
    def refresh_states(connection: sqlite3.Connection, artifact_id: str,
                       candidate_ids: list[str], states: Mapping[str, Mapping[str, Any]],
                       *, revision: int, status: str) -> None:
        meta = connection.execute(
            "SELECT * FROM stage1_review_projection_meta WHERE artifact_id=?", (artifact_id,)
        ).fetchone()
        if meta is None:
            return
        for candidate_id in candidate_ids:
            row = connection.execute(
                """SELECT candidate_type,attention_json FROM stage1_review_projection
                   WHERE artifact_id=? AND candidate_id=?""", (artifact_id, candidate_id),
            ).fetchone()
            if row is None:
                raise BoundaryError("REVIEW_PROJECTION_INCOMPLETE")
            state = states.get(candidate_id)
            decision = str((state or {}).get("decision") or "")
            queues = ["completed", "recently_decided"] if state else ["needs_review", "human_required"]
            if row["candidate_type"] == "NODE":
                queues.append("entity_resolution")
            if row["candidate_type"] == "PARENT_PLACEMENT":
                queues.append("parent_placement")
            if decision in ("DEFER", "KEEP_NEEDS_REVIEW"):
                queues.append("deferred")
            if any(json.loads(row["attention_json"]).values()):
                queues.append("high_attention")
            connection.execute(
                """UPDATE stage1_review_projection
                   SET is_pending=?,state_json=?,queues_json=?
                   WHERE artifact_id=? AND candidate_id=?""",
                (0 if state else 1, _canonical(dict(state)) if state else None,
                 _canonical(queues), artifact_id, candidate_id),
            )
        pending = int(connection.execute(
            "SELECT COUNT(*) FROM stage1_review_projection WHERE artifact_id=? AND is_pending=1",
            (artifact_id,),
        ).fetchone()[0])
        snapshot_id = _snapshot(
            artifact_id, meta["basis_id"], revision, status, meta["total_rows"]
        )
        connection.execute(
            """UPDATE stage1_review_projection_meta
               SET snapshot_id=?,revision=?,status=?,pending_rows=?,built_at=?
               WHERE artifact_id=?""",
            (snapshot_id, revision, status, pending,
             datetime.now(timezone.utc).isoformat(), artifact_id),
        )


def stage1_capacity(connection: sqlite3.Connection, *, now: datetime | None = None) -> dict[str, Any]:
    if schema_version(connection) != "10":
        return {"enabled": False, "policy_version": None}
    current = now or datetime.now(timezone.utc)
    pending = int(connection.execute(
        "SELECT COUNT(*) FROM stage1_review_projection WHERE is_pending=1"
    ).fetchone()[0])
    packets = int(connection.execute(
        """SELECT COUNT(*) FROM registered_packets r
           WHERE COALESCE(r.artifact_kind,'REVIEW_PACKET')='REVIEW_PACKET'
             AND NOT EXISTS(SELECT 1 FROM stage1_review_projection_meta m
                            WHERE m.artifact_id=r.artifact_id)"""
    ).fetchone()[0])
    window_start = (current - timedelta(hours=24)).isoformat()
    runs = int(connection.execute(
        "SELECT COUNT(*) FROM source_processing_runs WHERE created_at>=?", (window_start,)
    ).fetchone()[0])
    control = connection.execute("SELECT * FROM stage1_operator_control WHERE singleton=1").fetchone()
    hard = pending > LIMITS.review_wip_hard
    soft = pending > LIMITS.review_wip_soft
    return {
        "enabled": True, "policy_version": STAGE1_POLICY_VERSION,
        "limits": asdict(LIMITS), "pending_review_rows": pending,
        "unprojected_review_packets": packets,
        "wip_state": "HARD_STOP" if hard else "SOFT_WARNING" if soft else "OPEN",
        "runs_last_24h": runs,
        "intake_paused": bool(control["intake_paused"]),
        "pause_reason": control["pause_reason"],
        "new_intake_allowed": not (hard or packets or control["intake_paused"]
                                    or runs >= LIMITS.runs_per_24h),
    }


def require_stage1_intake(connection: sqlite3.Connection) -> None:
    capacity = stage1_capacity(connection)
    if not capacity.get("enabled"):
        return
    if capacity["unprojected_review_packets"]:
        raise BoundaryError("STAGE1_REVIEW_PROJECTION_INCOMPLETE")
    if capacity["intake_paused"]:
        raise BoundaryError("STAGE1_INTAKE_PAUSED")
    if capacity["wip_state"] == "HARD_STOP":
        raise BoundaryError("STAGE1_REVIEW_WIP_HARD_LIMIT")
    if capacity["runs_last_24h"] >= LIMITS.runs_per_24h:
        raise BoundaryError("STAGE1_RUN_WINDOW_LIMIT")


def set_stage1_intake(config, *, paused: bool, reason: str) -> dict[str, Any]:
    """Explicit operator pause/resume; resume requires the frozen soft envelope."""
    if not reason or reason != reason.strip() or len(reason) > 1000:
        raise BoundaryError("STAGE1_INTAKE_REASON_REQUIRED")
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        capacity = stage1_capacity(connection)
        if not capacity.get("enabled"):
            raise BoundaryError("STAGE1_SCHEMA_REQUIRED")
        if (not paused and (
                capacity["pending_review_rows"] > LIMITS.review_wip_soft
                or capacity["unprojected_review_packets"]
        )):
            raise BoundaryError("STAGE1_INTAKE_RESUME_ENVELOPE_NOT_MET")
        updated = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """UPDATE stage1_operator_control
               SET intake_paused=?,pause_reason=?,updated_at=? WHERE singleton=1""",
            (1 if paused else 0, reason, updated),
        )
    return {
        "status": "PAUSED" if paused else "OPEN",
        "policy_version": STAGE1_POLICY_VERSION,
        "reason": reason, "updated_at": updated,
    }
