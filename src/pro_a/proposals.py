from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .analyzer import Analyzer
from .config import AppConfig
from .constants import NODE_TYPES
from .current_view import create_official_view_record, write_official_view_file
from .db import Database, now_iso
from .ids import make_id
from .ima import IMAClient
from .propagation import PropagationManager
from .receipts import write_proposal


class ProposalManager:
    def __init__(self, cfg: AppConfig, db: Database, analyzer: Analyzer):
        self.cfg = cfg
        self.db = db
        self.analyzer = analyzer
        self.ima = IMAClient(cfg.ima)
        self.propagation = PropagationManager(cfg, db, analyzer)

    def _update_status(self, proposal_id: str, status: str, reason: str = "") -> None:
        self.db.execute(
            "UPDATE proposals SET status=?,reason=CASE WHEN ?<>'' THEN ? ELSE reason END,resolved_at=? WHERE proposal_id=?",
            (status, reason, reason, now_iso(), proposal_id),
        )
        write_proposal(self.cfg, self.db.proposal(proposal_id))

    @staticmethod
    def _result(proposal: dict[str, Any]) -> dict[str, Any]:
        raw = proposal.get("result_json") or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def accept(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.db.proposal(proposal_id)
        if not proposal:
            raise KeyError(f"Unknown proposal: {proposal_id}")
        if proposal["status"] == "accepted":
            result = self._result(proposal)
            if result.get("view_id"):
                self._run_side_effect_jobs(result["view_id"])
            if result.get("propagation_batch_id"):
                self.propagation.run_batch(result["propagation_batch_id"])
            return result
        if proposal["status"] != "pending":
            raise ValueError(f"Proposal is not pending: {proposal['status']}")

        if proposal["proposal_type"] == "new_node":
            result = self._accept_new_node(proposal)
            self.db.execute(
                "UPDATE proposals SET status='accepted',result_json=?,resolved_at=? WHERE proposal_id=?",
                (json.dumps(result, ensure_ascii=False), now_iso(), proposal_id),
            )
            write_proposal(self.cfg, self.db.proposal(proposal_id))
            batch_id = proposal.get("propagation_batch_id") or ""
            if batch_id:
                self.propagation.resume_batch(batch_id)
            return result
        if proposal["proposal_type"] != "current_view_change":
            raise ValueError(f"Unsupported proposal type: {proposal['proposal_type']}")

        result, stale_reason = self._accept_current_view_atomic(proposal_id)
        if stale_reason:
            write_proposal(self.cfg, self.db.proposal(proposal_id))
            raise ValueError(stale_reason)
        write_proposal(self.cfg, self.db.proposal(proposal_id))
        self._run_side_effect_jobs(result["view_id"])
        self.propagation.run_batch(result["propagation_batch_id"])
        return result

    def reject(self, proposal_id: str, reason: str = "") -> None:
        proposal = self.db.proposal(proposal_id)
        if not proposal:
            raise KeyError(proposal_id)
        if proposal["status"] != "pending":
            raise ValueError(f"Proposal is not pending: {proposal['status']}")
        self._update_status(proposal_id, "rejected", reason)
        batch_id = proposal.get("propagation_batch_id") or ""
        if batch_id:
            self.propagation.resume_batch(batch_id)

    def _accept_new_node(self, proposal: dict[str, Any]) -> dict[str, Any]:
        p = proposal["payload"]
        if p.get("primary_type") not in NODE_TYPES:
            raise ValueError(f"Invalid primary_type: {p.get('primary_type')}")
        node_id = self.db.add_node(
            p["canonical_name"], p["primary_type"], p.get("aliases") or [], p.get("description", "")
        )
        for parent_id in p.get("suggested_parent_node_ids") or []:
            if self.db.get_node(parent_id):
                self.db.add_relation(node_id, "part_of", parent_id)
        for related_id in p.get("related_node_ids") or []:
            if self.db.get_node(related_id) and related_id != node_id:
                self.db.add_relation(node_id, "related_to", related_id)
        source_id = p.get("source_id", "")
        if source_id:
            self.db.execute(
                """INSERT OR IGNORE INTO source_node_links(
                   source_id,node_id,role,confidence,link_origin) VALUES(?,?,?,?,?)""",
                (source_id, node_id, "related", p.get("confidence"), "candidate"),
            )
        claim_ids = p.get("related_claim_ids") or []
        for cid in claim_ids:
            self.db.execute(
                "INSERT OR IGNORE INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
                (cid, node_id, "related"),
            )
        if p.get("candidate_kind") == "research_question" or p.get("primary_type") == "ResearchQuestion":
            rq_id = make_id("RQ")
            ts = now_iso()
            self.db.execute(
                """INSERT OR IGNORE INTO research_questions(rq_id,node_id,question,importance,current_answer,confidence,
                   supporting_claim_ids_json,opposing_claim_ids_json,key_variables_json,what_would_change_my_mind,status,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rq_id, node_id, p.get("question") or p["canonical_name"], p.get("importance", ""), "", None,
                 "[]", "[]", "[]", p.get("what_would_change_my_mind", ""), "open", ts, ts),
            )
        cv_proposal = ""
        if claim_ids:
            impact = self.propagation.evaluate_node(
                batch_id=proposal.get("propagation_batch_id") or make_id("BATCH"),
                trigger_type="new_node_accept", trigger_id=proposal["proposal_id"], node_id=node_id,
                path_type="direct", claim_ids=claim_ids, trigger_source_id=source_id,
                context={"reason": "Initial Current View check after approved new Node"},
            )
            cv_proposal = impact.get("proposal_id", "")
        return {"node_id": node_id, "current_view_proposal": cv_proposal}

    @staticmethod
    def _current_view_conn(conn, node_id: str) -> dict[str, Any] | None:
        row = conn.execute(
            """SELECT * FROM current_views WHERE node_id=? AND status='official'
               ORDER BY revision_date DESC,revision_seq DESC,view_id DESC LIMIT 1""",
            (node_id,),
        ).fetchone()
        return dict(row) if row else None

    def _accept_current_view_atomic(self, proposal_id: str) -> tuple[dict[str, Any], str]:
        stale_reason = ""
        with self.db.transaction(immediate=True) as conn:
            row = conn.execute("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                raise KeyError(proposal_id)
            proposal = dict(row)
            if proposal["status"] == "accepted":
                return self._result(proposal), ""
            if proposal["status"] != "pending":
                raise ValueError(f"Proposal is not pending: {proposal['status']}")
            payload = json.loads(proposal["payload_json"])
            node_id = payload["node_id"]
            current = self._current_view_conn(conn, node_id)
            expected_id = payload.get("previous_view_id", "")
            expected_version = payload.get("previous_version", "")
            actual_id = current["view_id"] if current else ""
            actual_version = current["version"] if current else ""
            if expected_id != actual_id or expected_version != actual_version:
                stale_reason = (
                    f"stale Current View proposal: expected {expected_version or '<none>'}, "
                    f"current is {actual_version or '<none>'}"
                )
                conn.execute(
                    "UPDATE proposals SET status='stale',reason=?,resolved_at=? WHERE proposal_id=?",
                    (stale_reason, now_iso(), proposal_id),
                )
                return {}, stale_reason

            view = create_official_view_record(
                conn, self.cfg, node_id, payload.get("proposed_current_view") or {},
                payload.get("change_level", "minor"), payload.get("trigger_source_id", ""),
                payload.get("evidence_claim_ids") or [], accepted_proposal_id=proposal_id,
            )
            batch_id = proposal.get("propagation_batch_id") or make_id("BATCH")
            self.propagation.start_from_accepted_view(
                view, payload, batch_id, conn=conn, run=False,
            )
            result = {
                "view_id": view["view_id"],
                "version": view["version"],
                "path": str(view["path"]),
                "propagation_batch_id": batch_id,
            }
            conn.execute(
                """UPDATE proposals SET status='accepted',propagation_batch_id=?,result_json=?,resolved_at=?
                   WHERE proposal_id=?""",
                (batch_id, json.dumps(result, ensure_ascii=False), now_iso(), proposal_id),
            )
            self._enqueue_side_effect_job_conn(
                conn, "write_current_view_markdown", view["view_id"], {"path": str(view["path"])},
            )
            if self.cfg.ima.enabled and self.cfg.ima.upload_current_views and self.cfg.ima.output_kb_id:
                self._enqueue_side_effect_job_conn(
                    conn, "ima_sync_current_view", view["view_id"], {"path": str(view["path"])},
                )
        return result, ""

    @staticmethod
    def _enqueue_side_effect_job_conn(conn, job_type: str, object_id: str, payload: dict[str, Any]) -> None:
        ts = now_iso()
        conn.execute(
            """INSERT OR IGNORE INTO side_effect_jobs(
               job_id,job_type,object_id,payload_json,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?)""",
            (make_id("SIDE"), job_type, object_id, json.dumps(payload, ensure_ascii=False), "pending", ts, ts),
        )

    def _run_side_effect_jobs(self, view_id: str) -> None:
        jobs = self.db.all(
            """SELECT * FROM side_effect_jobs WHERE object_id=? AND status IN ('pending','retry')
               ORDER BY CASE job_type WHEN 'write_current_view_markdown' THEN 10 ELSE 20 END,created_at""",
            (view_id,),
        )
        for job in jobs:
            self.db.execute(
                "UPDATE side_effect_jobs SET attempts=attempts+1,status='running',last_error='',updated_at=? WHERE job_id=?",
                (now_iso(), job["job_id"]),
            )
            try:
                if job["job_type"] == "write_current_view_markdown":
                    self._write_view(view_id)
                elif job["job_type"] == "ima_sync_current_view":
                    self._sync_view_to_ima(view_id)
                else:
                    raise ValueError(f"Unknown side effect job type: {job['job_type']}")
            except Exception as exc:
                self.db.execute(
                    "UPDATE side_effect_jobs SET status='retry',last_error=?,updated_at=? WHERE job_id=?",
                    (str(exc), now_iso(), job["job_id"]),
                )
                if job["job_type"] == "write_current_view_markdown":
                    return
            else:
                self.db.execute(
                    "UPDATE side_effect_jobs SET status='done',updated_at=? WHERE job_id=?",
                    (now_iso(), job["job_id"]),
                )

    def _view_for_side_effect(self, view_id: str) -> dict[str, Any]:
        view = self.db.one(
            """SELECT v.*,n.node_id,n.canonical_name,n.primary_type FROM current_views v
               JOIN nodes n ON n.node_id=v.node_id WHERE v.view_id=?""",
            (view_id,),
        )
        if not view:
            raise KeyError(view_id)
        view["path"] = self.cfg.root / "generated" / "current_views" / view["node_id"] / f"Current_View_{view['version']}.md"
        return view

    def _write_view(self, view_id: str) -> None:
        view = self._view_for_side_effect(view_id)
        write_official_view_file(view)

    def _sync_view_to_ima(self, view_id: str) -> None:
        view = self._view_for_side_effect(view_id)
        path = Path(view["path"])
        if not path.exists():
            raise FileNotFoundError(path)
        uploaded = self.ima.upload_file(
            path, self.cfg.ima.output_kb_id, self.cfg.ima.output_folder_id,
            title=f"[{view['node_id']}]_{path.name}",
        )
        self.db.execute(
            """INSERT OR REPLACE INTO ima_objects(mapping_id,local_object_type,local_object_id,ima_kb_id,ima_folder_id,
               ima_media_id,title,synced_at,status) VALUES(?,?,?,?,?,?,?,?,?)""",
            (make_id("IMA"), "current_view", view_id, self.cfg.ima.output_kb_id,
             self.cfg.ima.output_folder_id, uploaded.get("media_id", ""), path.name, now_iso(),
             "skipped_same_name" if uploaded.get("skipped") else "synced"),
        )
