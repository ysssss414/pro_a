"""Read-only post-schema qualification and all-row review comparison. No payload."""
from __future__ import annotations

from datetime import date
import json

from .constants import CLAIM_NATURES, NODE_TYPES, RELATION_TYPES
from .foundation_execution_contract import requalified_objects, BOUND_CONTRACT, BOUND_IDENTITY_CONTRACT, restore_temporal
from .foundation_schema_preparation import require_execution_schema
from .phase3f_foundation_baseline import require
from .production_promotion import build_identity_catalog, resolve_identity, canonical_sha256


def identity_snapshot(connection):
    return {table: [dict(r) for r in connection.execute(f'SELECT * FROM "{table}"')]
            for table in ("nodes", "node_aliases", "claims", "sources", "node_relations", "current_views")}


def target_resolution(record, kind, snapshot, candidate_nodes):
    c = record["content"]
    catalog = build_identity_catalog(snapshot["nodes"], snapshot["node_aliases"])
    def ref(value):
        if value in catalog["nodes"]:
            return {"reference": value, "existing_node": catalog["nodes"][value], "content_decision": ""}
        require(value in candidate_nodes, "UNKNOWN_NODE_REFERENCE:" + str(value))
        return {"reference": value, "candidate_pending_human_decision": True, "content_decision": ""}
    if kind == "nodes":
        return {"identity_matches": resolve_identity(catalog, c["canonical_name"]),
                "expected_target": catalog["nodes"].get(c["raw"].get("existing_node_id", ""))}
    if kind == "aliases":
        return {"target": ref(c["target_ref"]), "alias_owners": resolve_identity(catalog, c["alias"])}
    if kind == "relations":
        return {"from": ref(c["from_ref"]), "to": ref(c["to_ref"]),
                "existing_edges": [r for r in snapshot["node_relations"] if r["from_node_id"] == c["from_ref"]
                                   and r["to_node_id"] == c["to_ref"] and r["relation_type"] == c["relation_type"] and r["scope"] == c["scope"]]}
    return ref(c["target_ref"] if kind == "baseline_views" else c["raw"]["subject_ref"])


def requalify(old, manifest, connection, evidence):
    require_execution_schema(connection)
    snapshot = identity_snapshot(connection)
    objects = requalified_objects(old, manifest)
    node_ids = {r["candidate_id"] for r in objects["nodes"]}
    claim_ids = {r["candidate_id"] for r in objects["claims"]}
    sources = {s["source_id"]: s["expected_sha256"] for s in old["registry"]["sources"]}
    existing_claims = {r["claim_id"] for r in snapshot["claims"]}
    for source in snapshot["sources"]:
        require(source["source_id"] not in sources or source["sha256"] == sources[source["source_id"]], "SOURCE_ID_COLLISION")
        require(source["sha256"] not in sources.values() or sources.get(source["source_id"]) == source["sha256"], "SOURCE_SHA_COLLISION")
    for kind, records in objects.items():
        for record in records:
            cid, c = record["candidate_id"], record["content"]
            resolution = target_resolution(record, kind, snapshot, node_ids)
            refs = c.get("evidence_refs", [e["evidence_id"] for e in c.get("evidence", [])])
            require(refs and all(e in evidence for e in refs), "EVIDENCE_ACCOUNTING_MISMATCH:" + cid)
            require(all(evidence[e]["source_id"] in sources for e in refs), "EVIDENCE_SOURCE_MISMATCH:" + cid)
            require(set(c.get("supporting_claim_ids", [])) <= claim_ids, "CLAIM_REFERENCE_MISMATCH:" + cid)
            state = "MECHANICALLY_REQUALIFIED_PENDING_HUMAN_REVIEW"
            if kind == "claims":
                raw, row = c["raw"], c["row"]
                require(cid not in existing_claims and row["claim_id"] == cid, "CLAIM_ID_COLLISION:" + cid)
                require(row["status"] == "needs_review" and row["nature"] in CLAIM_NATURES, "CLAIM_MAPPING_INVALID:" + cid)
                require(row["nature"] == c["qualification_diagnostics"]["mapped_nature"], "CLAIM_NATURE_MAPPING_DRIFT:" + cid)
                require(c["source_sha256"] == sources[c["source_id"]], "CLAIM_SOURCE_SHA_DRIFT:" + cid)
                require(json.loads(row["structured_json"])["foundation_native"] == raw, "NATIVE_CLAIM_METADATA_DRIFT:" + cid)
                for raw_key, row_key in (("statement", "statement"), ("scope", "scope"), ("evidence_excerpt", "evidence_excerpt"),
                                         ("evidence_locator", "evidence_pointer"), ("attribution", "attributed_to"),
                                         ("fact_time", "fact_time"), ("publication_time", "publication_time")):
                    require(row[row_key] == raw[raw_key], "CLAIM_FIELD_DRIFT:" + cid + ":" + raw_key)
                require(len(c["evidence"]) == 1, "UNRESOLVED_CLAIM_EVIDENCE_IDENTITY:" + cid)
                e = c["evidence"][0]
                require({k: v for k, v in e.items() if k != "source_sha256"} == evidence[e["evidence_id"]], "CLAIM_EVIDENCE_DRIFT:" + cid)
                require(e["source_id"] == c["source_id"] and e["evidence_excerpt"] == raw["evidence_excerpt"] and
                        f'{e["source_id"]} PDF p.{e["pdf_page"]}, {e["section"]}' == raw["evidence_locator"], "CLAIM_LOCATOR_EXCERPT_MISMATCH:" + cid)
                dates = [raw.get(k) for k in ("fact_time", "publication_time")]
                for value in dates:
                    if value:
                        require(date.fromisoformat(value).isoformat() == value, "INVALID_CLAIM_TIME:" + cid)
                if not any(dates):
                    require(c["qualification_status"] == "REVIEW_REQUIRED", "MISSING_TIME_NOT_BLOCKED:" + cid)
                    state = "INDIVIDUAL_TEMPORAL_EXCEPTION_KEEP_BLOCKED_NO_DATE_INVENTED"
                else:
                    require(c["qualification_status"] == "DETERMINISTICALLY_MAPPABLE", "UNRESOLVED_CLAIM_QUALIFICATION:" + cid)
            elif kind == "nodes":
                require(c["primary_type"] in NODE_TYPES, "NODE_TYPE_INVALID:" + cid)
                require(c["expected_target"] == resolution["expected_target"], "NODE_TARGET_DRIFT:" + cid)
            elif kind == "relations":
                require(c["relation_type"] in RELATION_TYPES, "RELATION_TYPE_INVALID:" + cid)
                require(restore_temporal(c["temporal_projection"]) == {k: c["raw"][k] for k in ("temporal_status", "valid_from", "valid_to") if k in c["raw"]}, "TEMPORAL_LOSS:" + cid)
                require(c["relation_native_authorizations"] or c["evidence_link_candidates"], "RELATION_EVIDENCE_PATH_MISSING:" + cid)
                require(all(link["authorization_state"] == "UNAUTHORIZED" for link in c["evidence_link_candidates"]), "CLAIM_LINK_ROLE_DECISION_APPEARED:" + cid)
            elif kind == "baseline_views":
                require(c["artifact_status"] == BOUND_CONTRACT["baseline_artifact_status"] and c["raw"]["content_md"] == c["content_md"], "HISTORICAL_BASELINE_DRIFT:" + cid)
                require(date.fromisoformat(c["as_of"]).isoformat() == c["as_of"], "BASELINE_DATE_INVALID:" + cid)
                require(set(c["supporting_source_ids"]) <= sources.keys(), "BASELINE_SOURCE_MISSING:" + cid)
            c["post_migration_qualification"] = {"state": state, "target_resolution": resolution,
                                                 "human_content_decision": "", "schema_version": "0.2.3"}
    return objects


def compare_all_rows(old, new, old_snapshot):
    records = []
    prior = {(kind, r["candidate_id"]): r for kind, rows in old["objects"].items() for r in rows}
    require(set(prior) == {(kind, r["candidate_id"]) for kind, rows in new["objects"].items() for r in rows}, "CANDIDATE_UNIVERSE_DRIFT")
    node_ids = {r["candidate_id"] for r in old["objects"]["nodes"]}
    for kind, rows in new["objects"].items():
        for r in rows:
            cid, c = r["candidate_id"], r["content"]
            previous = prior[kind, cid]
            pc = previous["content"]
            require(pc["raw"] == c["raw"], "NATIVE_CONTENT_DRIFT:" + cid)
            old_target = target_resolution(previous, kind, old_snapshot, node_ids)
            new_target = c["post_migration_qualification"]["target_resolution"]
            require(old_target == new_target, "UNEXPLAINED_TARGET_DRIFT:" + cid)
            changed = kind in {"claims", "relations"}
            reasons = ["New Production/schema/implementation/SQL/manifest binding; deterministic target resolution rechecked; native content unchanged."]
            if kind == "claims":
                reasons.append("Explicit qualified KEEP admission and non-executable KEEP_NEEDS_REVIEW/DROP contract are now executable; this is not a decision.")
                if "evidence_identity_adjudication" in c:
                    reasons.append("Explicit human Evidence identity adjudication selects R5795 and retains MEGTRON8 sibling; original ambiguity diagnostics retained.")
                if c["qualification_status"] == "REVIEW_REQUIRED":
                    reasons.append("Existing individual missing-time exception preserved; KEEP remains blocked, no date invented.")
            elif kind == "relations":
                reasons.append("Lossless categorical temporal mapping; exact native authority or qualified-KEEP Claim-linked route; CREATE/REUSE remains blank.")
            elif kind == "baseline_views":
                reasons.append("Historical Baseline namespace and immutable storage guards now installed; not an official Current View.")
            records.append({"candidate_id": cid, "kind": kind,
                "native_content_sha256_old": canonical_sha256(pc["raw"]), "native_content_sha256_new": canonical_sha256(c["raw"]),
                "review_projection_sha256_old": previous["content_sha256"], "review_projection_sha256_new": r["content_sha256"],
                "target_resolution_old": old_target, "target_resolution_new": new_target,
                "qualification_old": {"status": pc.get("qualification_status"), "diagnostics": pc.get("qualification_diagnostics")},
                "qualification_new": {"status": c.get("qualification_status"), "diagnostics": c.get("qualification_diagnostics"), "post_migration": c["post_migration_qualification"]},
                "reason_for_change": reasons, "human_review_semantics_changed": changed,
                "classification": "REVIEW_SEMANTICS_CHANGED" if changed else "SEMANTICALLY_UNCHANGED_REQUALIFIED",
                "explained": True, "human_decision": ""})
    return sorted(records, key=lambda r: r["candidate_id"])


def requalify_identity_contract(original, prior_blank, connection, evidence):
    """New V4 projections, preserving the original package and V3 evidence layer.

    Re-run original mechanical qualification, not adjudication of new evidence.
    No decisions are accepted or copied into a review packet here.
    """
    from .phase3f_foundation_baseline import validate_review
    validate_review(prior_blank, expected_sha256=prior_blank["immutable_packet_sha256"], completed=False)
    objects = requalify(original, prior_blank["evidence_governance_manifest"], connection, evidence)
    prior = {(kind, r["candidate_id"]): r for kind, rows in prior_blank["objects"].items() for r in rows}
    require(set(prior) == {(kind, r["candidate_id"]) for kind, rows in objects.items() for r in rows}, "CANDIDATE_UNIVERSE_DRIFT")
    for kind, rows in objects.items():
        for r in rows:
            c = r["content"]
            require(c == prior[kind, r["candidate_id"]]["content"], "UNEXPLAINED_PRE_CORRECTION_PROJECTION_DRIFT:" + r["candidate_id"])
            if kind == "nodes":
                c["identity_admission_contract"] = {
                    "contract_sha256": BOUND_IDENTITY_CONTRACT["contract_sha256"],
                    "supporting_claim_ids_execution_role": "NON_BLOCKING_NODE_IDENTITY_PROVENANCE",
                    "create_identity_provenance": "EXACT_FROZEN_EVIDENCE_AND_SOURCE_BINDINGS",
                    "human_decision": "",
                }
            elif kind == "aliases":
                c["identity_admission_contract"] = {
                    "contract_sha256": BOUND_IDENTITY_CONTRACT["contract_sha256"],
                    "human_target": "SEMANTIC_CANDIDATE_OR_EXISTING_NODE_REFERENCE",
                    "runtime_target": "RESOLVED_FINAL_NODE_ID",
                    "canonical_equivalent_attach": "ATTACH_NOOP_CANONICAL_EQUIVALENT_SAME_OWNER_ONLY",
                    "human_decision": "",
                }
    return objects
