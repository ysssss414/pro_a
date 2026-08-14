from __future__ import annotations

import copy
import json
from typing import Any

from .analyzer import Analyzer, attribution_subjects
from .config import AppConfig
from .constants import CHANGE_LEVELS
from .db import Database, now_iso
from .ids import make_id
from .prompts import IMPACT_SYSTEM, IMPACT_USER
from .propagation import (
    CurrentViewValidationError,
    JUDGMENT_NATURES,
    PropagationManager,
)
from .receipts import write_proposal


IMPACT_REPAIR_SYSTEM = r"""
你处于 Current View deterministic repair 模式。

程序已经对上一版候选 JSON 做了硬校验，并给出精确 validation errors。
你的任务只是在不放宽任何规则的前提下修复这些违规，输出完整的 Impact Review JSON。

硬要求：
1. 继续遵守原始 Current View Prompt 的全部规则；validator 是最终裁决，不能绕过。
2. 只修复 validation errors 指向的问题；除非修复这些问题必需，不改动其它已合规字段。
3. 不新增 Evidence 中没有的事实、应用、公司、因果或预测。
4. Claim ID、attribution、Evidence Scope、target-node-centric、Product type_specific 规则保持不变。
5. 未来语义只能由对应的 company_guidance / broker_forecast 原子 Claim 支撑；不得利用 data/fact Claim 的 evidence_excerpt 混入未来陈述。
6. Evidence-bearing 字段删除 Claim statement 未支持的数字、公司/供应商、行业趋势或因果链；major_risks 不得用“需关注”掩盖无依据因果，缺失信息只移入明确标为待验证/需跟踪的 knowledge_gaps / key_watch_items。
7. 若 validation error 指向 major_risks[n] unsupported causal inference，必须删除该 major_risks 整项；禁止同义改写、弱化措辞或改成“需关注”。如有研究价值，只能在已有 knowledge_gaps / key_watch_items 中用“缺少证据/待验证/需跟踪”表达。
8. 输出完整 JSON，不输出解释、Markdown 或补丁。
"""

IMPACT_REPAIR_USER = r"""
目标 Node：
{node_json}

当前正式 Current View（可能为空）：
---
{current_view}
---

原 Evidence：
{evidence_json}

关系/传播上下文：
{context_json}

上一版候选 JSON：
{candidate_json}

deterministic validation errors：
{validation_errors_json}

仅修复上述违规，返回完整的 Impact Review JSON。
"""


class ImpactRecoveryService:
    """Observable, retryable recovery path for persisted Impact Reviews."""

    def __init__(self, cfg: AppConfig, db: Database, analyzer: Analyzer):
        self.cfg = cfg
        self.db = db
        self.analyzer = analyzer
        self.propagation = PropagationManager(cfg, db, analyzer)

    @staticmethod
    def _json_object(value: str) -> dict[str, Any]:
        try:
            parsed = json.loads(value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}

    @staticmethod
    def _json_list(value: str) -> list[Any]:
        try:
            parsed = json.loads(value or "[]")
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return []

    def _impact(self, impact_id: str) -> dict[str, Any]:
        impact = self.db.one("SELECT * FROM impact_reviews WHERE impact_id=?", (impact_id,))
        if not impact:
            raise KeyError(impact_id)
        return impact

    def _context(self, impact: dict[str, Any]) -> dict[str, Any]:
        context = self._json_object(impact.get("payload_json") or "")
        if context:
            return context
        legacy = self._json_object(impact.get("reason") or "")
        nested = legacy.get("context")
        return nested if isinstance(nested, dict) else legacy

    def _evidence(
        self, impact: dict[str, Any], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        evidence = self.propagation._claims(context.get("claim_ids") or [])
        if context.get("propagated_change"):
            evidence.append({"propagated_change": context["propagated_change"]})
        return evidence

    def _prepared_context(
        self, context: dict[str, Any], evidence: list[dict[str, Any]]
    ) -> dict[str, Any]:
        profile = self.propagation._evidence_profile(evidence)
        required_attributions = {
            item["claim_id"]: {
                "nature": item.get("nature") or "",
                "attributed_to": item.get("attributed_to") or "",
                "required_subject": (
                    attribution_subjects(str(item.get("attributed_to") or "")) or [""]
                )[-1],
            }
            for item in evidence
            if item.get("claim_id")
            and item.get("attributed_to")
            and (
                item.get("nature") in JUDGMENT_NATURES
                or bool(self.propagation._company_subject(item))
            )
        }
        return {
            **context,
            "evidence_profile": profile,
            "required_claim_attributions": required_attributions,
        }

    def _attempt_rows(self, impact_id: str) -> list[dict[str, Any]]:
        rows = self.db.all(
            """SELECT * FROM impact_attempt_audit
               WHERE impact_id=?
               ORDER BY execution_attempt,repair_round,created_at,audit_id""",
            (impact_id,),
        )
        for row in rows:
            row["candidate"] = self._json_object(row.pop("candidate_json", "{}"))
            row["validation_errors"] = self._json_list(
                row.pop("validation_errors_json", "[]")
            )
        return rows

    def _active_proposal(self, impact_id: str) -> dict[str, Any] | None:
        return self.db.one(
            """SELECT * FROM proposals
               WHERE source_impact_id=? AND status IN ('pending','accepted')
               ORDER BY created_at DESC,proposal_id DESC LIMIT 1""",
            (impact_id,),
        )

    def _latest_proposal(self, impact_id: str) -> dict[str, Any] | None:
        return self.db.one(
            """SELECT * FROM proposals WHERE source_impact_id=?
               ORDER BY created_at DESC,proposal_id DESC LIMIT 1""",
            (impact_id,),
        )

    @staticmethod
    def _validation_errors(exc: Exception) -> list[str]:
        if isinstance(exc, CurrentViewValidationError):
            return list(exc.errors)
        return [str(exc)]

    def _proposal_candidate(
        self, impact: dict[str, Any], proposal: dict[str, Any]
    ) -> dict[str, Any]:
        stored = self._json_object(impact.get("reason") or "")
        result = stored.get("result")
        if isinstance(result, dict):
            return copy.deepcopy(result)

        payload = self._json_object(proposal.get("payload_json") or "")
        proposed = payload.get("proposed_current_view") or {}
        return {
            "requires_change": True,
            "change_level": payload.get("change_level") or "initial",
            "reason": payload.get("reason") or proposal.get("reason") or "",
            "scope_normalization_notes": payload.get("scope_normalization_notes") or [],
            "evidence_sufficiency": payload.get("evidence_sufficiency") or {},
            "proposed_current_view": proposed,
            "knowledge_gaps": (
                proposed.get("knowledge_gaps") or []
                if isinstance(proposed, dict)
                else []
            ),
            "research_question_candidates": [],
        }

    def show(self, impact_id: str) -> dict[str, Any]:
        impact = self._impact(impact_id)
        context = self._context(impact)
        evidence = self._evidence(impact, context)
        profile = self.propagation._evidence_profile(evidence)
        attempts = self._attempt_rows(impact_id)
        last_attempt = attempts[-1] if attempts else {}
        node = self.db.get_node(impact["node_id"])
        proposal = (
            self.db.one("SELECT * FROM proposals WHERE proposal_id=?", (impact["proposal_id"],))
            if impact.get("proposal_id")
            else self._latest_proposal(impact_id)
        )
        claims = [
            {
                key: item.get(key)
                for key in (
                    "claim_id",
                    "statement",
                    "nature",
                    "attributed_to",
                    "scope",
                    "confidence",
                    "source_rank",
                    "origin_type",
                    "evidence_source_id",
                    "underlying_source_id",
                    "evidence_excerpt",
                )
            }
            for item in evidence
            if item.get("claim_id")
        ]
        return {
            "impact": impact,
            "target_node": node,
            "evidence_profile": profile,
            "claims": claims,
            "last_llm_output": copy.deepcopy(last_attempt.get("candidate") or {}),
            "validation_errors": list(last_attempt.get("validation_errors") or []),
            "attempt_history": attempts,
            "proposal": proposal,
        }

    def _record_attempt(
        self,
        *,
        impact_id: str,
        execution_attempt: int,
        repair_round: int,
        phase: str,
        candidate: dict[str, Any] | None,
        validation_errors: list[str] | None = None,
        error_text: str = "",
    ) -> None:
        self.db.execute(
            """INSERT INTO impact_attempt_audit(
               audit_id,impact_id,execution_attempt,repair_round,phase,candidate_json,
               validation_errors_json,error_text,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                make_id("IATT"),
                impact_id,
                execution_attempt,
                repair_round,
                phase,
                json.dumps(candidate or {}, ensure_ascii=False),
                json.dumps(validation_errors or [], ensure_ascii=False),
                error_text,
                now_iso(),
            ),
        )

    def _generate(
        self,
        node: dict[str, Any],
        current_view_md: str,
        evidence: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        user = IMPACT_USER.format(
            node_json=json.dumps(node, ensure_ascii=False),
            current_view=current_view_md or "<NO_CURRENT_VIEW>",
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            context_json=json.dumps(context, ensure_ascii=False),
            required_attributions_json=json.dumps(
                context.get("required_claim_attributions") or {}, ensure_ascii=False
            ),
        )
        return self.analyzer.llm.json(IMPACT_SYSTEM, user)

    def _repair(
        self,
        node: dict[str, Any],
        current_view_md: str,
        evidence: list[dict[str, Any]],
        context: dict[str, Any],
        candidate: dict[str, Any],
        validation_errors: list[str],
    ) -> dict[str, Any]:
        user = IMPACT_REPAIR_USER.format(
            node_json=json.dumps(node, ensure_ascii=False),
            current_view=current_view_md or "<NO_CURRENT_VIEW>",
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            context_json=json.dumps(context, ensure_ascii=False),
            candidate_json=json.dumps(candidate, ensure_ascii=False),
            validation_errors_json=json.dumps(validation_errors, ensure_ascii=False),
        )
        return self.analyzer.llm.json(
            f"{IMPACT_SYSTEM}\n\n{IMPACT_REPAIR_SYSTEM}",
            user,
        )

    def _validate_candidate(
        self,
        node: dict[str, Any],
        candidate: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], bool]:
        result = self.analyzer._validate_impact_output(candidate, evidence)
        if not isinstance(result, dict):
            raise ValueError("Impact Review must return an object")
        level = result.get("change_level") or "none"
        if level not in {*CHANGE_LEVELS, "none"}:
            raise ValueError(f"Invalid Impact Review change_level: {level}")
        if not isinstance(result.get("requires_change"), bool):
            raise ValueError("Impact Review requires_change must be boolean")

        self.propagation._apply_initial_evidence_profile(result, evidence)
        semantic_sufficiency = result.get("evidence_sufficiency") or {}
        program_sufficient, program_reason = (
            self.propagation._programmatic_evidence_sufficiency(
                level, evidence, semantic_sufficiency
            )
        )
        result["programmatic_evidence_sufficiency"] = {
            "sufficient": program_sufficient,
            "reason": program_reason,
        }
        requires_change = (
            bool(result.get("requires_change")) and level not in (None, "", "none")
        )
        if level in {"initial", "material", "thesis"} and (
            semantic_sufficiency.get("sufficient") is False or not program_sufficient
        ):
            requires_change = False
        if requires_change:
            self.propagation._validate_current_view_quality(node, result, evidence)
        return result, requires_change

    def _finalize(
        self,
        *,
        impact: dict[str, Any],
        node: dict[str, Any],
        context: dict[str, Any],
        claim_ids: list[str],
        result: dict[str, Any],
        requires_change: bool,
    ) -> dict[str, Any]:
        gaps: list[str] = []
        if self.cfg.pipeline.create_gaps_automatically:
            for gap in result.get("knowledge_gaps") or []:
                gap_id = self.propagation._create_gap(node["node_id"], gap)
                if gap_id:
                    gaps.append(gap_id)

        rq_proposals: list[str] = []
        for candidate in result.get("research_question_candidates") or []:
            proposal_id = self.propagation._create_rq_candidate(
                candidate, node["node_id"], claim_ids, impact["batch_id"]
            )
            if proposal_id:
                rq_proposals.append(proposal_id)

        proposal_id = ""
        if requires_change:
            proposal_id = self.propagation._create_current_view_proposal(
                node["node_id"],
                result,
                claim_ids,
                context.get("trigger_source_id", ""),
                impact["batch_id"],
                context,
                impact["impact_id"],
            )
            status = "proposed"
        else:
            status = "no_change"

        self.db.execute(
            """UPDATE impact_reviews SET status=?,result_change_level=?,proposal_id=?,reason=?,
               last_error='',evaluated_at=? WHERE impact_id=?""",
            (
                status,
                result.get("change_level", "none"),
                proposal_id,
                json.dumps({"context": context, "result": result}, ensure_ascii=False),
                now_iso(),
                impact["impact_id"],
            ),
        )
        return {
            "status": status,
            "proposal_id": proposal_id,
            "gaps": gaps,
            "rq_proposals": rq_proposals,
            "result": result,
        }

    def _begin_correction(
        self,
        impact_id: str,
        proposal_id: str,
        validation_errors: list[str],
    ) -> dict[str, Any]:
        stale_reason = "Superseded by Impact correction: " + "; ".join(validation_errors)
        with self.db.transaction(immediate=True) as conn:
            proposal = conn.execute(
                "SELECT status FROM proposals WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
            if not proposal:
                raise KeyError(proposal_id)
            if proposal["status"] == "accepted":
                raise ValueError("Accepted Proposal cannot be replaced")
            if proposal["status"] in {"pending", "rejected"}:
                conn.execute(
                    """UPDATE proposals SET status='stale',reason=?,resolved_at=?
                       WHERE proposal_id=?""",
                    (stale_reason, now_iso(), proposal_id),
                )
            elif proposal["status"] != "stale":
                raise ValueError(
                    f"Proposal cannot be replaced from status: {proposal['status']}"
                )
            conn.execute(
                """UPDATE impact_reviews
                   SET status='pending',attempts=attempts+1,proposal_id='',last_error=''
                   WHERE impact_id=?""",
                (impact_id,),
            )
        write_proposal(self.cfg, self.db.proposal(proposal_id))
        return self._impact(impact_id)

    def _replace_proposal(
        self,
        impact: dict[str, Any],
        proposal: dict[str, Any],
        *,
        max_repairs: int,
    ) -> dict[str, Any]:
        context = self._context(impact)
        node = self.db.get_node(impact["node_id"])
        if not node:
            raise ValueError(f"Target Node not found: {impact['node_id']}")
        claim_ids = context.get("claim_ids") or []
        evidence = self._evidence(impact, context)
        prepared_context = self._prepared_context(context, evidence)
        current = self.db.current_view(impact["node_id"])
        current_view_md = current["content_md"] if current else ""
        candidate = self._proposal_candidate(impact, proposal)

        try:
            _, requires_change = self._validate_candidate(node, candidate, evidence)
            validation_errors = []
            if not requires_change:
                validation_errors = [
                    "Pending Current View correction must preserve requires_change=true"
                ]
        except Exception as exc:
            validation_errors = self._validation_errors(exc)

        if not validation_errors and proposal.get("status") == "pending":
            if (
                impact.get("status") != "proposed"
                or impact.get("proposal_id") != proposal["proposal_id"]
            ):
                self.db.execute(
                    """UPDATE impact_reviews
                       SET status='proposed',proposal_id=?,last_error=''
                       WHERE impact_id=?""",
                    (proposal["proposal_id"], impact["impact_id"]),
                )
            return {
                "status": "proposed",
                "proposal_id": proposal["proposal_id"],
                "proposal_status": "pending",
                "idempotent": True,
                "replacement_required": False,
            }

        impact = self._begin_correction(
            impact["impact_id"], proposal["proposal_id"], validation_errors
        )
        execution_attempt = int(impact.get("attempts") or 0)
        self._record_attempt(
            impact_id=impact["impact_id"],
            execution_attempt=execution_attempt,
            repair_round=0,
            phase="correction_original",
            candidate=candidate,
            validation_errors=validation_errors,
            error_text="",
        )

        if not self.analyzer.available:
            error = "LLM unavailable"
            self.db.execute(
                """UPDATE impact_reviews
                   SET status='needs_llm',last_error=?,evaluated_at=?
                   WHERE impact_id=?""",
                (error, now_iso(), impact["impact_id"]),
            )
            return {
                "status": "needs_llm",
                "proposal_id": "",
                "replaced_proposal_id": proposal["proposal_id"],
                "error": error,
                "validation_errors": validation_errors,
            }

        for repair_round in range(1, max_repairs + 1):
            repaired: dict[str, Any] | None = None
            try:
                repaired = self._repair(
                    node,
                    current_view_md,
                    evidence,
                    prepared_context,
                    candidate,
                    validation_errors,
                )
            except Exception as exc:
                error = str(exc)
                self._record_attempt(
                    impact_id=impact["impact_id"],
                    execution_attempt=execution_attempt,
                    repair_round=repair_round,
                    phase="correction_repair",
                    candidate=repaired,
                    validation_errors=validation_errors,
                    error_text=error,
                )
                self.db.execute(
                    """UPDATE impact_reviews
                       SET status='retry',last_error=?,evaluated_at=?
                       WHERE impact_id=?""",
                    (error, now_iso(), impact["impact_id"]),
                )
                return {
                    "status": "retry",
                    "proposal_id": "",
                    "replaced_proposal_id": proposal["proposal_id"],
                    "error": error,
                }

            try:
                result, requires_change = self._validate_candidate(
                    node, repaired, evidence
                )
                round_errors = []
                if not requires_change:
                    round_errors = [
                        "Pending Current View correction must preserve requires_change=true"
                    ]
            except Exception as exc:
                round_errors = self._validation_errors(exc)

            self._record_attempt(
                impact_id=impact["impact_id"],
                execution_attempt=execution_attempt,
                repair_round=repair_round,
                phase="correction_repair",
                candidate=repaired,
                validation_errors=round_errors,
                error_text="",
            )
            candidate = repaired
            validation_errors = round_errors
            if validation_errors:
                continue

            finalized = self._finalize(
                impact=impact,
                node=node,
                context=prepared_context,
                claim_ids=claim_ids,
                result=result,
                requires_change=True,
            )
            finalized["replaced_proposal_id"] = proposal["proposal_id"]
            return finalized

        error = validation_errors[-1]
        self.db.execute(
            """UPDATE impact_reviews
               SET status='retry',last_error=?,evaluated_at=?
               WHERE impact_id=?""",
            (error, now_iso(), impact["impact_id"]),
        )
        return {
            "status": "retry",
            "proposal_id": "",
            "replaced_proposal_id": proposal["proposal_id"],
            "error": error,
            "validation_errors": validation_errors,
        }

    def retry(
        self,
        impact_id: str,
        *,
        replace_pending: bool = False,
        max_repairs: int = 2,
    ) -> dict[str, Any]:
        if max_repairs not in {1, 2}:
            raise ValueError("max_repairs must be 1 or 2")

        impact = self._impact(impact_id)
        active = self._active_proposal(impact_id)
        if replace_pending:
            if active and active.get("status") == "accepted":
                return {
                    "status": "proposed",
                    "proposal_id": active["proposal_id"],
                    "proposal_status": "accepted",
                    "idempotent": True,
                    "error": "Accepted Proposal cannot be replaced",
                }
            replacement = active or self._latest_proposal(impact_id)
            if replacement:
                return self._replace_proposal(
                    impact, replacement, max_repairs=max_repairs
                )

        if active:
            if (
                impact.get("status") != "proposed"
                or impact.get("proposal_id") != active["proposal_id"]
            ):
                self.db.execute(
                    "UPDATE impact_reviews SET status='proposed',proposal_id=?,last_error='' WHERE impact_id=?",
                    (active["proposal_id"], impact_id),
                )
            return {
                "status": "proposed",
                "proposal_id": active["proposal_id"],
                "proposal_status": active["status"],
                "idempotent": True,
            }
        existing = self._latest_proposal(impact_id)
        if existing:
            return {
                "status": "blocked",
                "proposal_id": existing["proposal_id"],
                "proposal_status": existing["status"],
                "idempotent": True,
                "error": "Impact already owns a resolved non-active Proposal; explicit proposal correction is required",
            }
        if impact.get("status") == "no_change":
            return {"status": "no_change", "proposal_id": "", "idempotent": True}

        self.db.execute(
            """UPDATE impact_reviews
               SET status='pending',attempts=attempts+1,last_error=''
               WHERE impact_id=?""",
            (impact_id,),
        )
        impact = self._impact(impact_id)
        execution_attempt = int(impact.get("attempts") or 0)

        if not self.analyzer.available:
            error = "LLM unavailable"
            self._record_attempt(
                impact_id=impact_id,
                execution_attempt=execution_attempt,
                repair_round=0,
                phase="initial",
                candidate=None,
                validation_errors=[],
                error_text=error,
            )
            self.db.execute(
                """UPDATE impact_reviews
                   SET status='needs_llm',last_error=?,evaluated_at=?
                   WHERE impact_id=?""",
                (error, now_iso(), impact_id),
            )
            return {"status": "needs_llm", "proposal_id": "", "error": error}

        context = self._context(impact)
        node = self.db.get_node(impact["node_id"])
        if not node:
            error = f"Target Node not found: {impact['node_id']}"
            self.db.execute(
                "UPDATE impact_reviews SET status='retry',last_error=?,evaluated_at=? WHERE impact_id=?",
                (error, now_iso(), impact_id),
            )
            return {"status": "retry", "proposal_id": "", "error": error}

        claim_ids = context.get("claim_ids") or []
        evidence = self._evidence(impact, context)
        prepared_context = self._prepared_context(context, evidence)
        current = self.db.current_view(impact["node_id"])
        current_view_md = current["content_md"] if current else ""

        candidate: dict[str, Any] | None = None
        validation_errors: list[str] = []
        for repair_round in range(0, max_repairs + 1):
            phase = "initial" if repair_round == 0 else "repair"
            previous_candidate = candidate or {}
            round_candidate: dict[str, Any] | None = None
            try:
                if repair_round == 0:
                    round_candidate = self._generate(
                        node, current_view_md, evidence, prepared_context
                    )
                else:
                    round_candidate = self._repair(
                        node,
                        current_view_md,
                        evidence,
                        prepared_context,
                        previous_candidate,
                        validation_errors,
                    )
            except Exception as exc:
                error = str(exc)
                self._record_attempt(
                    impact_id=impact_id,
                    execution_attempt=execution_attempt,
                    repair_round=repair_round,
                    phase=phase,
                    candidate=round_candidate,
                    validation_errors=validation_errors,
                    error_text=error,
                )
                self.db.execute(
                    """UPDATE impact_reviews
                       SET status='retry',last_error=?,evaluated_at=?
                       WHERE impact_id=?""",
                    (error, now_iso(), impact_id),
                )
                return {"status": "retry", "proposal_id": "", "error": error}

            candidate = round_candidate
            try:
                result, requires_change = self._validate_candidate(
                    node, candidate, evidence
                )
            except Exception as exc:
                validation_errors = self._validation_errors(exc)
                self._record_attempt(
                    impact_id=impact_id,
                    execution_attempt=execution_attempt,
                    repair_round=repair_round,
                    phase=phase,
                    candidate=candidate,
                    validation_errors=validation_errors,
                    error_text="",
                )
                if repair_round < max_repairs:
                    continue
                error = validation_errors[-1]
                self.db.execute(
                    """UPDATE impact_reviews
                       SET status='retry',last_error=?,evaluated_at=?
                       WHERE impact_id=?""",
                    (error, now_iso(), impact_id),
                )
                return {
                    "status": "retry",
                    "proposal_id": "",
                    "error": error,
                    "validation_errors": validation_errors,
                }

            self._record_attempt(
                impact_id=impact_id,
                execution_attempt=execution_attempt,
                repair_round=repair_round,
                phase=phase,
                candidate=candidate,
                validation_errors=[],
                error_text="",
            )
            return self._finalize(
                impact=impact,
                node=node,
                context=prepared_context,
                claim_ids=claim_ids,
                result=result,
                requires_change=requires_change,
            )

        raise AssertionError("unreachable")
