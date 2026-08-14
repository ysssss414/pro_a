from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .analyzer import Analyzer, normalize_ws
from .audit import build_source_audit
from .config import AppConfig
from .db import Database, now_iso
from .ids import make_id
from .ima import IMAClient, IMAError
from .parsers import parse_source
from .propagation import PropagationManager
from .receipts import write_proposal, write_receipt
from .storage import archive_file, ensure_workspace, sha256_file


class IngestionPipeline:
    def __init__(self, cfg: AppConfig, db: Database):
        self.cfg = cfg
        self.db = db
        self.analyzer = Analyzer(cfg, db)
        self.ima = IMAClient(cfg.ima)
        self.propagation = PropagationManager(cfg, db, self.analyzer)

    def init_workspace(self) -> None:
        ensure_workspace(self.cfg.root)
        self.db.init_schema()

    def _stable(self, path: Path) -> bool:
        return (time.time() - path.stat().st_mtime) >= self.cfg.workspace.settle_seconds

    def scan(self) -> list[tuple[Path, str]]:
        out: list[tuple[Path, str]] = []
        for mode in ("archive", "standard", "deep"):
            folder = self.cfg.root / "inbox" / mode
            if not folder.exists():
                continue
            for p in sorted(folder.iterdir()):
                if p.is_file() and not p.name.startswith(("~$", ".~", ".")) and self._stable(p):
                    out.append((p, mode))
        return out

    def process_all(self) -> list[dict[str, Any]]:
        results = []
        for path, mode in self.scan():
            try:
                results.append(self.process_file(path, mode))
            except Exception as e:
                results.append({"path": str(path), "mode": mode, "status": "failed", "error": str(e)})
        return results

    @staticmethod
    def _mode_level(mode: str) -> int:
        return {"archive": 0, "standard": 1, "deep": 2}[mode]

    def _start_job(self, path: Path, mode: str) -> str:
        job_id = make_id("JOB")
        self.db.execute(
            "INSERT INTO processing_jobs(job_id,input_path,ingestion_mode,status,started_at) VALUES(?,?,?,?,?)",
            (job_id, str(path), mode, "running", now_iso()),
        )
        return job_id

    def _finish_job(self, job_id: str, status: str, source_id: str = "", error: str = "") -> None:
        self.db.execute(
            "UPDATE processing_jobs SET source_id=?,status=?,finished_at=?,error_text=? WHERE job_id=?",
            (source_id, status, now_iso(), error, job_id),
        )

    def _complete_receipt(self, job_id: str, source_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        receipt["job_id"] = job_id
        receipt["audit"] = build_source_audit(self.db, source_id)
        if self.cfg.pipeline.write_receipts:
            receipt["receipt_path"] = str(write_receipt(self.cfg, job_id, receipt))
        return receipt

    def _create_node_proposal(self, candidate: dict[str, Any], source_id: str, claim_ids: list[str], batch_id: str) -> str | None:
        name = (candidate.get("canonical_name") or "").strip()
        if not name or candidate.get("quality_eligible") is not True:
            return None
        existing = self.db.find_node_by_name_or_alias(name)
        if existing:
            for cid in claim_ids:
                self.db.execute("INSERT OR IGNORE INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
                                (cid, existing["node_id"], "related"))
            self.db.execute(
                """INSERT OR IGNORE INTO source_node_links(
                   source_id,node_id,role,confidence,link_origin) VALUES(?,?,?,?,?)""",
                (source_id, existing["node_id"], "related", candidate.get("confidence"), "candidate_resolution"),
            )
            return None
        if self.db.pending_new_node_proposal_exists(name):
            return None
        payload = {
            **candidate,
            "source_id": source_id,
            "related_claim_ids": claim_ids,
        }
        pid = self.db.add_proposal("new_node", payload, reason=candidate.get("reason", ""),
                                   propagation_batch_id=batch_id)
        write_proposal(self.cfg, self.db.proposal(pid))
        return pid

    def _insert_source(self, source_id: str, title: str, original_name: str, archived: Path, sha: str, mode: str) -> None:
        self.db.execute(
            """INSERT INTO sources(source_id,title,original_name,archived_path,sha256,ingestion_mode,ingested_at,status)
               VALUES(?,?,?,?,?,?,?,?)""",
            (source_id, title, original_name, str(archived), sha, mode, now_iso(), "stored"),
        )

    def _sync_source_to_ima(self, source_id: str, archived: Path, original_name: str) -> dict[str, Any]:
        if not (self.ima.available and self.cfg.ima.upload_originals and self.cfg.ima.source_kb_id):
            return {"status": "disabled"}
        title = f"[{source_id}] {original_name}"
        try:
            result = self.ima.upload_file(archived, self.cfg.ima.source_kb_id, self.cfg.ima.source_folder_id, title=title)
            media_id = result.get("media_id", "")
            self.db.execute("UPDATE sources SET ima_media_id=?,ima_kb_id=? WHERE source_id=?",
                            (media_id, self.cfg.ima.source_kb_id, source_id))
            self.db.execute(
                """INSERT OR REPLACE INTO ima_objects(mapping_id,local_object_type,local_object_id,ima_kb_id,ima_folder_id,
                   ima_media_id,title,synced_at,status) VALUES(?,?,?,?,?,?,?,?,?)""",
                (make_id("IMA"), "source", source_id, self.cfg.ima.source_kb_id, self.cfg.ima.source_folder_id,
                 media_id, title, now_iso(), "synced" if not result.get("skipped") else "skipped_same_name"),
            )
            return {"status": "synced", **result}
        except IMAError as e:
            return {"status": "failed", "error": str(e)}

    def _update_source_metadata(
        self, source_id: str, source_type: str, meta: dict[str, Any],
        refs: list[dict[str, Any]], analysis_quality: dict[str, Any] | None = None,
    ) -> None:
        title = (meta.get("title") or "").strip()
        metadata = {
            "summary": meta.get("summary", ""),
            "source_references_unresolved": refs,
            "analysis_quality": analysis_quality or {},
        }
        self.db.execute(
            """UPDATE sources SET title=CASE WHEN ?<>'' THEN ? ELSE title END,source_type=?,source_rank=?,origin_type=?,
               author=?,organization=?,publication_time=?,metadata_json=?,status='analyzed' WHERE source_id=?""",
            (title, title, source_type, meta.get("source_rank") or "UNRANKED", meta.get("source_origin_type") or "unknown",
             meta.get("author") or "", meta.get("organization") or "", meta.get("publication_time") or "",
             json.dumps(metadata, ensure_ascii=False), source_id),
        )
        for ref in refs:
            ref_title = (ref.get("title") or "").strip()
            if not ref_title:
                continue
            target = self.db.one("SELECT source_id FROM sources WHERE title=? AND source_id<>? ORDER BY ingested_at DESC LIMIT 1",
                                 (ref_title, source_id))
            if target:
                self.db.execute(
                    "INSERT OR IGNORE INTO source_relations(relation_id,from_source_id,relation_type,to_source_id,note,created_at) VALUES(?,?,?,?,?,?)",
                    (make_id("SREL"), source_id, ref.get("relation_type") or "references", target["source_id"],
                     ref.get("note") or "", now_iso()),
                )

    def _insert_claims(
        self, source_id: str, analysis, publication_time: str
    ) -> tuple[list[str], dict[int, str]]:
        claim_ids: list[str] = []
        claim_id_by_index: dict[int, str] = {}
        for claim_index, c in enumerate(analysis.claims):
            statement = normalize_ws(str(c.get("statement", "")))
            if not statement:
                continue
            claim_id = make_id("CLM")
            status = c.get("status") or "current"
            if not c.get("evidence_validated"):
                status = "needs_review"
            structured = dict(c.get("structured") or {})
            structured["related_candidate_names"] = c.get("related_candidate_names") or []
            if c.get("statement_normalization"):
                structured["statement_normalization"] = dict(c["statement_normalization"])
            structured["validation"] = dict(c.get("validation") or {
                "evidence_validated": bool(c.get("evidence_validated")),
                "model_confidence": c.get("confidence"),
                "errors": [] if c.get("evidence_validated") else ["evidence_excerpt_not_found"],
            })
            self.db.execute(
                """INSERT INTO claims(claim_id,statement,nature,fact_time,publication_time,ingestion_time,source_id,
                   evidence_pointer,evidence_excerpt,attributed_to,scope,assumption_text,status,confidence,novelty_level,
                   structured_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (claim_id, statement, c.get("nature") or "fact", c.get("fact_time") or "", publication_time,
                 now_iso(), source_id, c.get("evidence_pointer") or "", c.get("evidence_excerpt") or "",
                 c.get("attributed_to") or "", c.get("scope") or "", c.get("assumption") or "", status, c.get("confidence"),
                 c.get("novelty_level") or "N2", json.dumps(structured, ensure_ascii=False), now_iso()),
            )
            claim_ids.append(claim_id)
            claim_id_by_index[claim_index] = claim_id
            for node_id in c.get("related_node_ids") or []:
                if self.db.get_node(node_id):
                    self.db.execute("INSERT OR IGNORE INTO claim_node_links(claim_id,node_id,role) VALUES(?,?,?)",
                                    (claim_id, node_id, "related"))
                    self.db.execute(
                        """INSERT OR IGNORE INTO source_node_links(
                           source_id,node_id,role,confidence,link_origin,evidence_excerpt,evidence_validation_json)
                           VALUES(?,?,?,?,?,?,?)""",
                        (source_id, node_id, "related", c.get("confidence"), "claim",
                         c.get("evidence_excerpt") or "", json.dumps(structured["validation"], ensure_ascii=False)),
                    )
        return claim_ids, claim_id_by_index

    def _apply_node_matches(self, source_id: str, matches: list[dict[str, Any]]) -> list[str]:
        linked = []
        for m in matches:
            node_id = m.get("node_id")
            if not node_id or not self.db.get_node(node_id) or m.get("evidence_validated") is not True:
                continue
            role = "primary" if m.get("role") == "primary" else "related"
            self.db.execute(
                """INSERT OR REPLACE INTO source_node_links(
                   source_id,node_id,role,confidence,link_origin,derived_from_node_id,
                   evidence_excerpt,evidence_validation_json) VALUES(?,?,?,?,?,?,?,?)""",
                (source_id, node_id, role, m.get("confidence"), "direct", "",
                 m.get("evidence_excerpt") or "", json.dumps(m.get("validation") or {}, ensure_ascii=False)),
            )
            linked.append(node_id)
        return linked

    def _part_of_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        return self.db.all(
            """WITH RECURSIVE ancestors(node_id,depth,path) AS (
                 SELECT to_node_id,1,'|' || from_node_id || '|' || to_node_id || '|'
                 FROM node_relations
                 WHERE from_node_id=? AND relation_type='part_of' AND status='current'
                 UNION ALL
                 SELECT r.to_node_id,a.depth+1,a.path || r.to_node_id || '|'
                 FROM ancestors a JOIN node_relations r ON r.from_node_id=a.node_id
                 WHERE r.relation_type='part_of' AND r.status='current'
                   AND instr(a.path,'|' || r.to_node_id || '|')=0
               )
               SELECT node_id,MIN(depth) AS depth FROM ancestors GROUP BY node_id ORDER BY depth,node_id""",
            (node_id,),
        )

    def _derive_source_ancestor_links(self, source_id: str) -> None:
        origins = self.db.all(
            """SELECT node_id,role,confidence,link_origin FROM source_node_links
               WHERE source_id=? AND link_origin IN ('direct','claim')
               ORDER BY CASE role WHEN 'primary' THEN 0 ELSE 1 END,node_id""",
            (source_id,),
        )
        for origin in origins:
            for ancestor in self._part_of_ancestors(origin["node_id"]):
                existing = self.db.one(
                    "SELECT link_origin FROM source_node_links WHERE source_id=? AND node_id=?",
                    (source_id, ancestor["node_id"]),
                )
                if existing and existing["link_origin"] != "direct":
                    continue
                if existing:
                    self.db.execute(
                        """UPDATE source_node_links SET role='related',link_origin='part_of',
                           derived_from_node_id=?,evidence_excerpt='',evidence_validation_json='{}'
                           WHERE source_id=? AND node_id=?""",
                        (origin["node_id"], source_id, ancestor["node_id"]),
                    )
                else:
                    self.db.execute(
                        """INSERT INTO source_node_links(
                           source_id,node_id,role,confidence,link_origin,derived_from_node_id)
                           VALUES(?,?,?,?,?,?)""",
                        (source_id, ancestor["node_id"], "related", origin.get("confidence"),
                         "part_of", origin["node_id"]),
                    )

    @staticmethod
    def _validated_candidate_claim_indices(
        analysis, mapping: dict[str, list[int]]
    ) -> dict[str, list[int]]:
        expected = {
            normalize_ws(str(candidate.get("canonical_name") or "")).lower()
            for candidate in analysis.node_candidates
            if candidate.get("quality_eligible") is True
        }
        if set(mapping) != expected:
            raise ValueError("Candidate Claim backfill must return every eligible Candidate Node exactly once")
        validated: dict[str, list[int]] = {}
        for key, indices in mapping.items():
            if not isinstance(indices, list):
                raise ValueError(f"Candidate Claim backfill for {key!r} must be a list")
            checked: list[int] = []
            for index in indices:
                if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(analysis.claims):
                    raise ValueError(f"Candidate Claim backfill for {key!r} contains an invalid Claim index")
                claim = analysis.claims[index]
                if claim.get("evidence_validated") is not True or claim.get("status") == "needs_review":
                    raise ValueError(f"Candidate Claim backfill for {key!r} contains an unvalidated Claim")
                if index not in checked:
                    checked.append(index)
            validated[key] = checked
        return validated

    def _historical_compare(self, source_id: str, new_claim_ids: list[str]) -> None:
        if not self.analyzer.available or not new_claim_ids:
            return
        nodes = self.db.all(
            """SELECT DISTINCT l.node_id FROM claim_node_links l JOIN claims c ON c.claim_id=l.claim_id
               WHERE c.source_id=?""", (source_id,)
        )
        for nr in nodes:
            node_id = nr["node_id"]
            node = self.db.get_node(node_id)
            new_claims = self.db.all(
                """SELECT c.* FROM claims c JOIN claim_node_links l ON l.claim_id=c.claim_id
                   WHERE c.source_id=? AND l.node_id=? AND c.status<>'needs_review'""", (source_id, node_id)
            )
            history = self.db.all(
                """SELECT c.* FROM claims c JOIN claim_node_links l ON l.claim_id=c.claim_id
                   WHERE c.source_id<>? AND l.node_id=? ORDER BY c.created_at DESC LIMIT 80""", (source_id, node_id)
            )
            if not new_claims or not history:
                continue
            data = self.analyzer.compare_claims(node, new_claims, history)
            for cmp in data.get("comparisons") or []:
                new_id = cmp.get("new_claim_id")
                old_id = cmp.get("related_claim_id")
                cls = cmp.get("classification") or "new"
                if new_id not in {x["claim_id"] for x in new_claims}:
                    continue
                if cls == "new" or not old_id:
                    continue
                old = self.db.one("SELECT claim_id FROM claims WHERE claim_id=?", (old_id,))
                if not old:
                    continue
                rel_type = {"corroborates": "supports", "duplicate": "supports", "updates": "updates", "contradicts": "contradicts"}.get(cls)
                if rel_type:
                    self.db.execute(
                        "INSERT OR IGNORE INTO claim_relations(relation_id,from_claim_id,relation_type,to_claim_id,reason,created_at) VALUES(?,?,?,?,?,?)",
                        (make_id("CREL"), new_id, rel_type, old_id,
                         f"{cmp.get('reason','')} | scope: {cmp.get('scope_normalization','')}", now_iso()),
                    )
                if cls == "duplicate":
                    self.db.execute("UPDATE claims SET novelty_level='N0' WHERE claim_id=?", (new_id,))
                elif cls == "corroborates":
                    self.db.execute("UPDATE claims SET novelty_level='N1' WHERE claim_id=?", (new_id,))
                elif cls == "updates":
                    self.db.execute("UPDATE claims SET novelty_level='N2' WHERE claim_id=?", (new_id,))
                    self.db.execute("UPDATE claims SET status='updated' WHERE claim_id=?", (old_id,))
                elif cls == "contradicts":
                    self.db.execute("UPDATE claims SET status='disputed',novelty_level='N2' WHERE claim_id=?", (new_id,))
                    self.db.execute("UPDATE claims SET status='disputed' WHERE claim_id=? AND status='current'", (old_id,))

    def _direct_impacts(self, job_id: str, source_id: str) -> tuple[list[str], list[str], list[str]]:
        cv_proposals, gaps, rq_proposals = [], [], []
        rows = self.db.all(
            """SELECT l.node_id,c.claim_id,c.status,c.novelty_level FROM claim_node_links l JOIN claims c ON c.claim_id=l.claim_id
               WHERE c.source_id=?""", (source_id,)
        )
        by_node: dict[str, list[str]] = {}
        for r in rows:
            if r["status"] == "needs_review" or r["novelty_level"] == "N0":
                continue
            by_node.setdefault(r["node_id"], []).append(r["claim_id"])
        for node_id, claim_ids in by_node.items():
            result = self.propagation.evaluate_node(
                batch_id=job_id, trigger_type="source", trigger_id=source_id, node_id=node_id,
                path_type="direct", claim_ids=claim_ids, trigger_source_id=source_id,
                context={"ingestion_job_id": job_id, "direct_source": source_id},
            )
            if result.get("proposal_id"):
                cv_proposals.append(result["proposal_id"])
            gaps.extend(result.get("gaps") or [])
            rq_proposals.extend(result.get("rq_proposals") or [])
        return cv_proposals, gaps, rq_proposals

    def process_file(self, input_path: Path, mode: str) -> dict[str, Any]:
        input_path = Path(input_path)
        if mode not in {"archive", "standard", "deep"}:
            raise ValueError(mode)
        job_id = self._start_job(input_path, mode)
        source_id = ""
        warnings: list[str] = []
        try:
            sha = sha256_file(input_path)
            duplicate = self.db.one(
                """SELECT source_id,archived_path,title,ingestion_mode,analysis_mode,source_type,status,
                   publication_time FROM sources WHERE sha256=?""",
                (sha,),
            )
            if duplicate and (
                mode == "archive" or self._mode_level(duplicate["analysis_mode"]) >= self._mode_level(mode)
            ):
                input_path.unlink(missing_ok=True)
                receipt = {
                    "status": "duplicate", "mode": mode, "source_id": duplicate["source_id"],
                    "title": duplicate["title"], "archived_path": duplicate["archived_path"],
                    "ima_status": "not_reuploaded", "warnings": ["Exact SHA-256 duplicate; incoming copy removed."],
                    "node_matches": [], "node_proposals": [], "claims": [], "current_view_proposals": [], "knowledge_gaps": [],
                }
                self._finish_job(job_id, "duplicate", duplicate["source_id"])
                return self._complete_receipt(job_id, duplicate["source_id"], receipt)

            original_name = input_path.name
            source_id = duplicate["source_id"] if duplicate else make_id("SRC")
            archived = Path(duplicate["archived_path"]) if duplicate else None
            text = ""
            source_type = duplicate["source_type"] if duplicate else "unknown"

            if mode != "archive":
                # Do not consume the Inbox request until parsing succeeds.
                text, source_type = parse_source(input_path)

            if duplicate:
                requested_mode = (
                    mode if self._mode_level(mode) > self._mode_level(duplicate["ingestion_mode"])
                    else duplicate["ingestion_mode"]
                )
                self.db.execute(
                    "UPDATE sources SET ingestion_mode=?,source_type=? WHERE source_id=?",
                    (requested_mode, source_type, source_id),
                )
                self.db.execute("UPDATE processing_jobs SET source_id=? WHERE job_id=?", (source_id, job_id))
                input_path.unlink(missing_ok=True)
                ima_result = {"status": "not_reuploaded"}
            else:
                archived = archive_file(input_path, self.cfg.root, source_id)
                self._insert_source(source_id, original_name, original_name, archived, sha, mode)
                self.db.execute("UPDATE processing_jobs SET source_id=? WHERE job_id=?", (source_id, job_id))
                ima_result = self._sync_source_to_ima(source_id, archived, original_name)
                if ima_result.get("status") == "failed":
                    warnings.append("IMA source sync failed: " + ima_result.get("error", ""))

            if mode == "archive":
                self.db.execute("UPDATE sources SET status='archived' WHERE source_id=?", (source_id,))
                receipt = {
                    "status": "archived", "mode": mode, "source_id": source_id, "title": original_name,
                    "archived_path": str(archived), "ima_status": ima_result.get("status"), "warnings": warnings,
                    "node_matches": [], "node_proposals": [], "claims": [], "current_view_proposals": [], "knowledge_gaps": [],
                }
                self._finish_job(job_id, "done", source_id)
                return self._complete_receipt(job_id, source_id, receipt)

            if not self.analyzer.available:
                warnings.append("LLM disabled/missing key; Source stored but Standard/Deep analysis not run.")
                self.db.execute("UPDATE sources SET source_type=?,status='needs_llm' WHERE source_id=?", (source_type, source_id))
                receipt = {
                    "status": "needs_llm", "mode": mode, "source_id": source_id, "title": original_name,
                    "archived_path": str(archived), "ima_status": ima_result.get("status"), "warnings": warnings,
                    "node_matches": [], "node_proposals": [], "claims": [], "current_view_proposals": [], "knowledge_gaps": [],
                }
                self._finish_job(job_id, "needs_llm", source_id)
                return self._complete_receipt(job_id, source_id, receipt)

            analysis = self.analyzer.analyze_source(original_name, text, mode)
            meta = analysis.source_metadata
            candidate_claim_indices = self._validated_candidate_claim_indices(
                analysis,
                self.analyzer.backfill_candidate_claims(analysis.node_candidates, analysis.claims),
            )
            analysis_quality = {
                "rejected_node_matches": analysis.rejected_node_matches,
                "rejected_node_candidates": analysis.rejected_node_candidates,
                "rejected_claim_node_links": analysis.rejected_claim_node_links,
            }
            self._update_source_metadata(
                source_id, source_type, meta, analysis.source_references, analysis_quality,
            )
            self._apply_node_matches(source_id, analysis.node_matches)
            claim_ids, claim_id_by_index = self._insert_claims(
                source_id, analysis, meta.get("publication_time") or "",
            )
            self._derive_source_ancestor_links(source_id)
            linked_nodes = [
                row["node_id"] for row in self.db.all(
                    "SELECT node_id FROM source_node_links WHERE source_id=? ORDER BY node_id", (source_id,)
                )
            ]

            node_proposals: list[str] = []
            for candidate in analysis.node_candidates:
                key = normalize_ws(str(candidate.get("canonical_name", ""))).lower()
                related_claims = [
                    claim_id_by_index[index]
                    for index in candidate_claim_indices.get(key, [])
                    if index in claim_id_by_index
                ]
                pid = self._create_node_proposal(candidate, source_id, related_claims, job_id)
                if pid:
                    node_proposals.append(pid)

            self._historical_compare(source_id, claim_ids)
            cv_proposals, gaps, rq_proposals = self._direct_impacts(job_id, source_id)
            node_proposals.extend(rq_proposals)

            receipt = {
                "status": "analyzed", "mode": mode, "source_id": source_id,
                "title": meta.get("title") or original_name, "archived_path": str(archived),
                "ima_status": ima_result.get("status"), "warnings": warnings,
                "node_matches": linked_nodes, "node_proposals": node_proposals, "claims": claim_ids,
                "current_view_proposals": cv_proposals, "knowledge_gaps": gaps,
            }
            self.db.execute("UPDATE sources SET analysis_mode=? WHERE source_id=?", (mode, source_id))
            self._finish_job(job_id, "done", source_id)
            return self._complete_receipt(job_id, source_id, receipt)
        except Exception as e:
            source_exists = bool(
                source_id and self.db.one("SELECT source_id FROM sources WHERE source_id=?", (source_id,))
            )
            persisted_source_id = source_id if source_exists else ""
            self._finish_job(job_id, "failed", source_id=persisted_source_id, error=str(e))
            receipt = {
                "status": "failed",
                "mode": mode,
                "source_id": persisted_source_id,
                "title": input_path.name,
                "path": str(input_path),
                "error": str(e),
                "warnings": warnings,
                "node_matches": [],
                "node_proposals": [],
                "claims": [],
                "current_view_proposals": [],
                "knowledge_gaps": [],
                "job_id": job_id,
            }
            if source_exists:
                return self._complete_receipt(job_id, source_id, receipt)
            if self.cfg.pipeline.write_receipts:
                receipt["receipt_path"] = str(write_receipt(self.cfg, job_id, receipt))
            return receipt
