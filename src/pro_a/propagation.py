from __future__ import annotations

import json
import sqlite3
from typing import Any

from .analyzer import Analyzer
from .config import AppConfig
from .constants import CHANGE_LEVELS
from .db import Database, now_iso
from .ids import make_id
from .receipts import write_proposal


NO_TARGET_VIEW = "<none>"
HIGH_PRIMARY_RANKS = {"S", "A"}
MATERIAL_QUALITY_RANKS = {"S", "A", "B"}
THESIS_QUALITY_RANKS = {"S", "A"}


class PropagationManager:
    def __init__(self, cfg: AppConfig, db: Database, analyzer: Analyzer):
        self.cfg = cfg
        self.db = db
        self.analyzer = analyzer

    def _claims(self, claim_ids: list[str]) -> list[dict[str, Any]]:
        if not claim_ids:
            return []
        placeholders = ",".join("?" for _ in claim_ids)
        return self.db.all(
            f"""SELECT c.*,s.source_rank,s.origin_type,s.source_id AS evidence_source_id,
                s.underlying_source_id FROM claims c JOIN sources s ON s.source_id=c.source_id
                WHERE c.claim_id IN ({placeholders})""",
            claim_ids,
        )

    @staticmethod
    def _independence_key(claim: dict[str, Any]) -> str:
        return claim.get("underlying_source_id") or claim.get("evidence_source_id") or claim.get("source_id") or ""

    def _programmatic_evidence_sufficiency(
        self, level: str, evidence: list[dict[str, Any]], semantic: dict[str, Any]
    ) -> tuple[bool, str]:
        if level not in {"material", "thesis"}:
            return True, "No elevated evidence threshold required"

        claims = [item for item in evidence if item.get("claim_id")]
        by_id = {item["claim_id"]: item for item in claims}
        direct_ids = set(semantic.get("direct_primary_claim_ids") or [])
        decisive_ids = set(semantic.get("decisive_primary_claim_ids") or [])

        def confidence(item: dict[str, Any]) -> float:
            value = item.get("confidence")
            return float(value) if value is not None else 0.0

        direct_primary = [
            by_id[cid] for cid in direct_ids & by_id.keys()
            if by_id[cid].get("origin_type") == "primary"
            and by_id[cid].get("source_rank") in HIGH_PRIMARY_RANKS
            and confidence(by_id[cid]) >= 0.80
        ]
        decisive_primary = [
            by_id[cid] for cid in decisive_ids & by_id.keys()
            if by_id[cid].get("origin_type") == "primary"
            and by_id[cid].get("source_rank") in HIGH_PRIMARY_RANKS
            and confidence(by_id[cid]) >= 0.85
        ]

        if level == "material":
            if direct_primary:
                return True, "One high-confidence direct Primary Evidence"
            quality = [
                item for item in claims
                if item.get("source_rank") in MATERIAL_QUALITY_RANKS and confidence(item) >= 0.70
            ]
            independent = {self._independence_key(item) for item in quality if self._independence_key(item)}
            if len(independent) >= 2:
                return True, "At least two independent higher-quality Evidence sources"
            return False, "Material requires one high-confidence direct Primary Evidence or two independent higher-quality sources"

        explanation_complete = all(
            str(semantic.get(key) or "").strip()
            for key in ("invalidated_core_assumption", "logic_chain_failure", "conclusion_change")
        )
        if not explanation_complete:
            return False, "Thesis Change must identify the failed core assumption, broken logic chain, and changed conclusion"
        if decisive_primary:
            return True, "One decisive high-confidence Primary Evidence with a complete thesis-break explanation"
        quality = [
            item for item in claims
            if item.get("source_rank") in THESIS_QUALITY_RANKS and confidence(item) >= 0.80
        ]
        independent = {self._independence_key(item) for item in quality if self._independence_key(item)}
        if len(independent) >= 2:
            return True, "At least two independent high-quality Evidence sources with a complete thesis-break explanation"
        return False, "Thesis Change requires decisive Primary Evidence or two independent high-quality sources"

    def _create_gap(self, node_id: str, gap: dict[str, Any]) -> str | None:
        title = (gap.get("title") or "").strip()
        if not title:
            return None
        existing = self.db.one(
            "SELECT gap_id FROM knowledge_gaps WHERE node_id=? AND title=? AND status IN ('open','reopened','needs_refresh') LIMIT 1",
            (node_id, title),
        )
        if existing:
            return existing["gap_id"]
        gap_id = make_id("GAP")
        ts = now_iso()
        self.db.execute(
            """INSERT INTO knowledge_gaps(gap_id,node_id,title,description,status,source_claim_ids_json,freshness_due,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (gap_id, node_id, title, gap.get("description", ""), "open",
             json.dumps(gap.get("source_claim_ids") or [], ensure_ascii=False), gap.get("freshness_due", ""), ts, ts),
        )
        return gap_id

    def _pending_node_proposal_exists(self, name: str) -> bool:
        return bool(self.db.one(
            "SELECT proposal_id FROM proposals WHERE proposal_type='new_node' AND status='pending' AND payload_json LIKE ? LIMIT 1",
            (f'%"canonical_name": "{name}"%',),
        ))

    def _create_rq_candidate(self, candidate: dict[str, Any], base_node_id: str, claim_ids: list[str], batch_id: str) -> str | None:
        question = (candidate.get("question") or candidate.get("canonical_name") or "").strip()
        if not question:
            return None
        canonical_name = (candidate.get("canonical_name") or question).strip()
        if self.db.find_node_by_name_or_alias(canonical_name) or self._pending_node_proposal_exists(canonical_name):
            return None
        related = list(dict.fromkeys([base_node_id, *(candidate.get("related_node_ids") or [])]))
        payload = {
            "canonical_name": canonical_name,
            "primary_type": "ResearchQuestion",
            "aliases": [],
            "description": candidate.get("reason", ""),
            "suggested_parent_node_ids": [],
            "candidate_kind": "research_question",
            "question": question,
            "importance": candidate.get("importance", ""),
            "what_would_change_my_mind": candidate.get("what_would_change_my_mind", ""),
            "related_node_ids": related,
            "related_claim_ids": claim_ids,
        }
        pid = self.db.add_proposal(
            "new_node", payload, reason="Knowledge Gap upgraded to Research Question candidate",
            propagation_batch_id=batch_id,
        )
        write_proposal(self.cfg, self.db.proposal(pid))
        return pid

    def _create_current_view_proposal(
        self, node_id: str, result: dict[str, Any], claim_ids: list[str], trigger_source_id: str,
        batch_id: str, context: dict[str, Any], impact_id: str,
    ) -> str:
        current = self.db.current_view(node_id)
        payload = {
            "node_id": node_id,
            "change_level": result.get("change_level", "minor"),
            "reason": result.get("reason", ""),
            "scope_normalization_notes": result.get("scope_normalization_notes") or [],
            "evidence_sufficiency": result.get("evidence_sufficiency") or {},
            "programmatic_evidence_sufficiency": result.get("programmatic_evidence_sufficiency") or {},
            "proposed_current_view": result.get("proposed_current_view") or {},
            "evidence_claim_ids": claim_ids,
            "trigger_source_id": trigger_source_id,
            "previous_view_id": current["view_id"] if current else "",
            "previous_version": current["version"] if current else "",
            "context": context,
        }
        pid = self.db.add_proposal(
            "current_view_change", payload, target_node_id=node_id, reason=result.get("reason", ""),
            propagation_batch_id=batch_id, source_impact_id=impact_id,
        )
        write_proposal(self.cfg, self.db.proposal(pid))
        return pid

    @staticmethod
    def _queue_order(path_type: str) -> int:
        return 10 if path_type == "structural" else 20 if path_type == "related" else 0

    def _target_view_version(self, conn: sqlite3.Connection, node_id: str) -> str:
        row = conn.execute(
            """SELECT version FROM current_views WHERE node_id=? AND status='official'
               ORDER BY revision_date DESC,revision_seq DESC,view_id DESC LIMIT 1""",
            (node_id,),
        ).fetchone()
        return row["version"] if row else NO_TARGET_VIEW

    def _insert_impact_conn(
        self, conn: sqlite3.Connection, batch_id: str, trigger_type: str, trigger_id: str, node_id: str,
        path_type: str, status: str, context: dict[str, Any],
    ) -> str | None:
        impact_id = make_id("IMP")
        target_version = self._target_view_version(conn, node_id)
        payload = json.dumps(context, ensure_ascii=False)
        try:
            conn.execute(
                """INSERT INTO impact_reviews(
                   impact_id,batch_id,trigger_type,trigger_id,node_id,path_type,status,reason,target_view_version,
                   payload_json,queue_order,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (impact_id, batch_id, trigger_type, trigger_id, node_id, path_type, status, payload, target_version,
                 payload, self._queue_order(path_type), now_iso()),
            )
            return impact_id
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint" in str(exc):
                return None
            raise

    def _insert_impact(
        self, batch_id: str, trigger_type: str, trigger_id: str, node_id: str, path_type: str,
        status: str, context: dict[str, Any],
    ) -> str | None:
        with self.db.transaction(immediate=True) as conn:
            return self._insert_impact_conn(
                conn, batch_id, trigger_type, trigger_id, node_id, path_type, status, context,
            )

    def evaluate_node(
        self, *, batch_id: str, trigger_type: str, trigger_id: str, node_id: str, path_type: str,
        claim_ids: list[str], trigger_source_id: str = "", context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = {**(context or {}), "claim_ids": claim_ids, "trigger_source_id": trigger_source_id}
        impact_id = self._insert_impact(
            batch_id, trigger_type, trigger_id, node_id, path_type, "pending", context,
        )
        if impact_id is None:
            return {"status": "already_reviewed", "proposal_id": "", "gaps": [], "rq_proposals": []}
        try:
            return self._evaluate_impact_row(impact_id)
        except Exception as exc:
            self._mark_retry(impact_id, exc)
            return {"status": "retry", "proposal_id": "", "gaps": [], "rq_proposals": [], "error": str(exc)}

    def _mark_retry(self, impact_id: str, exc: Exception) -> None:
        self.db.execute(
            "UPDATE impact_reviews SET status='retry',last_error=?,evaluated_at=? WHERE impact_id=?",
            (str(exc), now_iso(), impact_id),
        )

    def _evaluate_impact_row(self, impact_id: str) -> dict[str, Any]:
        impact = self.db.one("SELECT * FROM impact_reviews WHERE impact_id=?", (impact_id,))
        if not impact:
            raise KeyError(impact_id)
        context = json.loads(impact.get("payload_json") or impact.get("reason") or "{}")
        node = self.db.get_node(impact["node_id"])
        current = self.db.current_view(impact["node_id"])
        claim_ids = context.get("claim_ids") or []
        evidence = self._claims(claim_ids)
        if context.get("propagated_change"):
            evidence.append({"propagated_change": context["propagated_change"]})

        self.db.execute("UPDATE impact_reviews SET attempts=attempts+1,last_error='' WHERE impact_id=?", (impact_id,))
        if not self.analyzer.available:
            self.db.execute(
                "UPDATE impact_reviews SET status='needs_llm',evaluated_at=? WHERE impact_id=?",
                (now_iso(), impact_id),
            )
            return {"status": "needs_llm", "proposal_id": "", "gaps": [], "rq_proposals": []}

        result = self.analyzer.review_impact(node, current["content_md"] if current else "", evidence, context)
        if not isinstance(result, dict):
            raise ValueError("Impact Review must return an object")
        level = result.get("change_level") or "none"
        if level not in {*CHANGE_LEVELS, "none"}:
            raise ValueError(f"Invalid Impact Review change_level: {level}")
        if not isinstance(result.get("requires_change"), bool):
            raise ValueError("Impact Review requires_change must be boolean")
        gaps = []
        if self.cfg.pipeline.create_gaps_automatically:
            for gap in result.get("knowledge_gaps") or []:
                gid = self._create_gap(node["node_id"], gap)
                if gid:
                    gaps.append(gid)

        rq_pids = []
        for candidate in result.get("research_question_candidates") or []:
            pid = self._create_rq_candidate(candidate, node["node_id"], claim_ids, impact["batch_id"])
            if pid:
                rq_pids.append(pid)

        proposal_id = ""
        level = result.get("change_level")
        requires_change = bool(result.get("requires_change")) and level not in (None, "", "none")
        semantic_sufficiency = result.get("evidence_sufficiency") or {}
        program_sufficient, program_reason = self._programmatic_evidence_sufficiency(
            level, evidence, semantic_sufficiency,
        )
        result["programmatic_evidence_sufficiency"] = {
            "sufficient": program_sufficient,
            "reason": program_reason,
        }
        if level in {"material", "thesis"} and (
            semantic_sufficiency.get("sufficient") is False or not program_sufficient
        ):
            requires_change = False
        if requires_change:
            proposal_id = self._create_current_view_proposal(
                node["node_id"], result, claim_ids, context.get("trigger_source_id", ""),
                impact["batch_id"], context, impact_id,
            )
            status = "proposed"
        else:
            status = "no_change"
        self.db.execute(
            """UPDATE impact_reviews SET status=?,result_change_level=?,proposal_id=?,reason=?,
               last_error='',evaluated_at=? WHERE impact_id=?""",
            (status, result.get("change_level", "none"), proposal_id,
             json.dumps({"context": context, "result": result}, ensure_ascii=False), now_iso(), impact_id),
        )
        return {"status": status, "proposal_id": proposal_id, "gaps": gaps, "rq_proposals": rq_pids, "result": result}

    def enqueue_from_accepted_view(
        self, conn: sqlite3.Connection, view: dict[str, Any], proposal_payload: dict[str, Any], batch_id: str,
    ) -> None:
        node_id = view["node_id"]
        claim_ids = proposal_payload.get("evidence_claim_ids") or []
        trigger_source_id = proposal_payload.get("trigger_source_id", "")
        propagated_change = {
            "node_id": node_id,
            "old_version": proposal_payload.get("previous_version", ""),
            "new_version": view["version"],
            "change_level": proposal_payload.get("change_level", ""),
            "reason": proposal_payload.get("reason", ""),
            "recent_change": (proposal_payload.get("proposed_current_view") or {}).get("recent_change", ""),
        }
        relations = conn.execute(
            "SELECT * FROM node_relations WHERE status='current' AND (from_node_id=? OR to_node_id=?)",
            (node_id, node_id),
        ).fetchall()
        for row in relations:
            relation = dict(row)
            other = relation["to_node_id"] if relation["from_node_id"] == node_id else relation["from_node_id"]
            relation["other_node_id"] = other
            relation["direction"] = "out" if relation["from_node_id"] == node_id else "in"
            path_type = "structural" if relation["relation_type"] == "part_of" else "related"
            context = {
                "trigger_node_id": node_id,
                "relation": relation,
                "propagated_change": propagated_change,
                "claim_ids": claim_ids,
                "trigger_source_id": trigger_source_id,
            }
            self._insert_impact_conn(
                conn, batch_id, "current_view", view["view_id"], other, path_type, "pending", context,
            )

    def start_from_accepted_view(
        self, view: dict[str, Any], proposal_payload: dict[str, Any], batch_id: str = "", *,
        conn: sqlite3.Connection | None = None, run: bool = True,
    ) -> str:
        batch_id = batch_id or make_id("BATCH")
        if conn is not None:
            self.enqueue_from_accepted_view(conn, view, proposal_payload, batch_id)
            return batch_id
        with self.db.transaction(immediate=True) as tx:
            self.enqueue_from_accepted_view(tx, view, proposal_payload, batch_id)
        if run:
            self.run_batch(batch_id)
        return batch_id

    def run_batch(self, batch_id: str) -> None:
        if not batch_id:
            return
        while True:
            pending_proposal = self.db.one(
                "SELECT proposal_id FROM proposals WHERE propagation_batch_id=? AND status='pending' LIMIT 1",
                (batch_id,),
            )
            if pending_proposal:
                return
            row = self.db.one(
                """SELECT impact_id FROM impact_reviews
                   WHERE batch_id=? AND status IN ('pending','deferred','retry','needs_llm')
                   ORDER BY queue_order,created_at,impact_id LIMIT 1""",
                (batch_id,),
            )
            if not row:
                return
            self.db.execute("UPDATE impact_reviews SET status='pending' WHERE impact_id=?", (row["impact_id"],))
            try:
                result = self._evaluate_impact_row(row["impact_id"])
            except Exception as exc:
                self._mark_retry(row["impact_id"], exc)
                return
            if result.get("status") in {"proposed", "needs_llm", "retry"}:
                return

    def resume_batch(self, batch_id: str) -> None:
        self.run_batch(batch_id)
