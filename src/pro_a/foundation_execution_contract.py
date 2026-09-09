"""Opt-in, hash-bound foundation execution semantics. No review or DB writes.

The original v1 packet stays blocked. A newly frozen packet must explicitly bind
this contract and its changed execution projections before human completion.
"""
from __future__ import annotations

import copy
import json
from collections import Counter

from .production_promotion import PromotionError, canonical_sha256, deterministic_id


CONTRACT = {
    "contract_id": "FOUNDATION_EXECUTION_CONTRACT_V3_RELATION_NATIVE",
    "schema_version": "0.2.3",
    "temporal_rule": "VERBATIM_CATEGORY_WITH_OPTIONAL_VERBATIM_VALIDITY",
    "runtime_lifecycle_status": "categorical",
    "current_assertion_rule": "NO_CURRENT_ASSERTION_INFERRED_FROM_CATEGORY",
    "claim_admission": {"KEEP": "current", "KEEP_NEEDS_REVIEW": "needs_review", "DROP": None, "": None},
    "claim_persistence": "KEEP_ONLY_OTHERS_REMAIN_IN_REVIEW_ARTIFACT",
    "claim_missing_time_storage": "NATIVE_NULL_RETAINED_IN_PROVENANCE_SQL_EMPTY_STRING_MEANS_MISSING_NOT_A_DATE",
    "evidence_rule": "EXPLICIT_NATIVE_AUTHORITY_OR_ALL_LISTED_CLAIM_LINKS_WITH_SEPARATE_KEEP",
    "native_evidence_rule": "EXACT_SCOPED_MANIFEST_ROLE_AUTHORITY_IS_NOT_A_RELATION_DECISION",
    "evidence_rule_notice": (
        "When this row binds RELATION_NATIVE authority, only the exact manifest Evidence roles "
        "and scope are used; no Claim is required. That prior role authority never decides CREATE/REUSE. "
        "Otherwise CREATE/REUSE explicitly confirms this exact Relation and every listed exact-Evidence-ID "
        "Claim link as SUPPORTS, unless that immutable link carries an explicit source role. "
        "Every required Claim must separately be KEEP and qualified for current evidence. "
        "If you cannot confirm all listed links, choose DEFER/REJECT. These choices create no "
        "active links and never mean CONTRADICTS. Native role authority may exist while the Relation "
        "decision is blank, but no runtime Relation/evidence link is created until later executable review."
    ),
    "contradicts_rule": "EXPLICIT_FROZEN_ROLE_ANNOTATION_ONLY_NEVER_FROM_REJECT",
    "baseline_artifact_status": "handoff_baseline_not_production_current_view",
    "production_authorization": False,
}
CONTRACT_SHA256 = canonical_sha256(CONTRACT)
BOUND_CONTRACT = {**CONTRACT, "contract_sha256": CONTRACT_SHA256}
EXTRA_SNAPSHOT_TABLES = ("relation_temporal_semantics", "relation_evidence_authorizations")


def require(condition, code):
    if not condition:
        raise PromotionError(code)


def uses_contract(packet):
    value = packet.get("execution_contract")
    if value is None:
        return False
    require(value == BOUND_CONTRACT, "EXECUTION_CONTRACT_DRIFT")
    return True


def project_temporal(raw):
    """No vocabulary list, suffix interpretation, inferred dates or case folding."""
    category = raw.get("temporal_status")
    require(isinstance(category, str) and category.strip(), "TEMPORAL_CATEGORY_MISSING")
    native = {key: raw[key] for key in ("valid_from", "valid_to") if key in raw}
    require(all(value is None or isinstance(value, str) for value in native.values()), "TEMPORAL_VALIDITY_NOT_VERBATIM_TEXT")
    body = {
        "temporal_category": category,
        "native_validity": native,
        "valid_from": native.get("valid_from") or "",
        "valid_to": native.get("valid_to") or "",
        "runtime_status": "categorical",
        "contract_sha256": CONTRACT_SHA256,
    }
    return {**body, "projection_sha256": canonical_sha256(body)}


def restore_temporal(projection):
    body = {k: v for k, v in projection.items() if k != "projection_sha256"}
    require(canonical_sha256(body) == projection.get("projection_sha256"), "TEMPORAL_PROJECTION_DRIFT")
    return {"temporal_status": projection["temporal_category"], **projection["native_validity"]}


def temporal_census(packet):
    records = []
    for record in packet["objects"]["relations"]:
        raw = record["content"]["raw"]
        projected = project_temporal(raw)
        expected = {k: raw[k] for k in ("temporal_status", "valid_from", "valid_to") if k in raw}
        require(restore_temporal(projected) == expected, "TEMPORAL_LOSSLESS_ROUNDTRIP_FAILED")
        records.append({"candidate_id": record["candidate_id"], "old_content_sha256": record["content_sha256"], "projection": projected})
    return {"category_counts": dict(sorted(Counter(r["projection"]["temporal_category"] for r in records).items())),
            "relation_count": len(records), "lossless_count": len(records), "records": records}


def exact_link_candidates(relation, claim_records, package_sha256):
    """Equality join is provenance, NOT role assignment or human authorization."""
    content = relation["content"]
    refs = content.get("evidence_refs", [])
    require(len(refs) == len(set(refs)), "DUPLICATE_RELATION_EVIDENCE_REF")
    annotations = content.get("raw", {}).get("explicit_evidence_roles", [])
    result = []
    for claim in sorted(claim_records, key=lambda item: item["candidate_id"]):
        cc = claim["content"]
        for evidence in sorted(cc["evidence"], key=lambda item: item.get("evidence_id", "")):
            eid = evidence.get("evidence_id")
            if eid not in refs:
                continue
            require(evidence["source_id"] == cc["source_id"] and evidence["source_sha256"] == cc["source_sha256"], "LINK_CROSS_SOURCE_PROVENANCE")
            explicit = [a for a in annotations if a["claim_id"] == claim["candidate_id"] and a["evidence_id"] == eid]
            require(len(explicit) <= 1, "AMBIGUOUS_EXPLICIT_EVIDENCE_ROLE")
            role = explicit[0]["role"] if explicit else None
            require(role in {None, "SUPPORTS", "CONTRADICTS"}, "EXPLICIT_EVIDENCE_ROLE_INVALID")
            body = {
                "relation_candidate_id": relation["candidate_id"], "claim_id": claim["candidate_id"],
                "evidence_id": eid, "source_id": cc["source_id"], "source_sha256": cc["source_sha256"],
                "evidence_sha256": canonical_sha256(evidence), "package_sha256": package_sha256,
                "native_relation_sha256": canonical_sha256(content["raw"]),
                "native_claim_sha256": canonical_sha256(cc["raw"]),
                "derivation": "EXACT_SHARED_EVIDENCE_ID_NO_SEMANTIC_INFERENCE",
                "explicit_role": role, "explicit_role_annotation": copy.deepcopy(explicit[0]) if explicit else None,
                "authorization_state": "UNAUTHORIZED",
                "decision_rule": CONTRACT["evidence_rule"], "contract_sha256": CONTRACT_SHA256,
                "claim_qualification_status": cc["qualification_status"],
            }
            result.append({"link_candidate_id": deterministic_id("REL_EVIDENCE_CANDIDATE", body), **body})
    require(len({r["link_candidate_id"] for r in result}) == len(result), "DUPLICATE_LINK_CANDIDATE")
    require(all(any(r["claim_id"] == a["claim_id"] and r["evidence_id"] == a["evidence_id"] for r in result)
                for a in annotations), "EXPLICIT_ROLE_WITHOUT_EXACT_EVIDENCE_JOIN")
    return sorted(result, key=lambda row: row["link_candidate_id"])


def relation_review_projection(relation, claims, package_sha256, native_rows=None):
    content = copy.deepcopy(relation["content"])
    projection = project_temporal(content["raw"])
    content.update(temporal_projection=projection, temporal_representation_lossless=True,
                   valid_from=projection["valid_from"], valid_to=projection["valid_to"], status="categorical",
                   evidence_links=[], evidence_link_candidates=exact_link_candidates(relation, claims, package_sha256),
                   decision_contract=BOUND_CONTRACT,
                   evidence_provenance_mode="RELATION_NATIVE" if native_rows else "CLAIM_LINKED",
                   relation_native_authorizations=copy.deepcopy(native_rows or []))
    return content


def admitted_claim_row(record, packet):
    require(uses_contract(packet), "CLAIM_ADMISSION_CONTRACT_NOT_BOUND")
    decision, content = record["human_input"]["decision"], record["content"]
    if decision != "KEEP":
        return None  # Preserve existing audit-only KEEP_NEEDS_REVIEW/DROP policy.
    require(content["qualification_status"] == "DETERMINISTICALLY_MAPPABLE", "CLAIM_EXCEPTION_UNRESOLVED:" + record["candidate_id"])
    row = copy.deepcopy(content["row"])
    require(row["status"] in {"needs_review", "current"}, "CLAIM_STATUS_TRANSITION_NOT_AUTHORIZED")
    native_times = {key: row[key] for key in ("fact_time", "publication_time")}
    require(all(value is None or isinstance(value, str) for value in native_times.values()), "CLAIM_TIME_REPRESENTATION_INVALID")
    require(packet["human_completion"]["reviewer"].strip() and record["human_input"]["reason"].strip(), "CLAIM_ADMISSION_HUMAN_AUTHORITY_MISSING")
    structured = json.loads(row["structured_json"])
    require("foundation_admission" not in structured, "CLAIM_ADMISSION_ALREADY_PRESENT")
    structured["foundation_admission"] = {
        "contract_sha256": CONTRACT_SHA256, "decision": "KEEP", "pre_review_status": row["status"], "admitted_status": "current",
        "reviewer": packet["human_completion"]["reviewer"], "reason": record["human_input"]["reason"],
        "immutable_packet_sha256": packet["immutable_packet_sha256"], "candidate_content_sha256": record["content_sha256"],
        "pre_review_time_fields": native_times,
    }
    for key, value in native_times.items():
        row[key] = "" if value is None else value
    row["structured_json"] = json.dumps(structured, ensure_ascii=False, sort_keys=True)
    row["status"] = "current"
    return row


def authorize_links(record, packet, active_claim_ids):
    content, human = record["content"], record["human_input"]
    if human["decision"] not in {"CREATE", "REUSE"}:
        return []
    require(uses_contract(packet) and packet["human_completion"]["reviewer"].strip() and human["reason"].strip(),
            "RELATION_LINK_HUMAN_AUTHORITY_MISSING")
    require(content.get("decision_contract") == BOUND_CONTRACT, "RELATION_CROSS_OBJECT_RULE_NOT_BOUND")
    if content.get("evidence_provenance_mode") == "RELATION_NATIVE":
        from .foundation_native_evidence import native_authorizations
        manifest = packet.get("evidence_governance_manifest")
        require(manifest is not None, "NATIVE_GOVERNANCE_MANIFEST_MISSING")
        require(manifest["package_sha256"] == packet["package"]["sha256"], "GOVERNANCE_BASELINE_DRIFT")
        expected_native = native_authorizations(record, manifest, packet["registry"])
        require(content.get("relation_native_authorizations") == expected_native and expected_native, "NATIVE_AUTHORIZATION_PROJECTION_DRIFT")
        require(any(r["role"] == "SUPPORTS" for r in expected_native), "NATIVE_SUPPORTS_AUTHORIZATION_REQUIRED")
        return [{"candidate": candidate, "claim_id": None, "evidence_role": candidate["role"].lower(),
                 "provenance_mode": "RELATION_NATIVE", "authorization_state": "AUTHORIZED_BY_SEPARATE_GOVERNANCE_MANIFEST"}
                for candidate in expected_native]
    expected = exact_link_candidates(record, packet["objects"]["claims"], packet["package"]["sha256"])
    require(content.get("evidence_link_candidates") == expected, "RELATION_LINK_CANDIDATE_DRIFT")
    require(expected, "RELATION_EXPLICIT_LINK_CANDIDATES_MISSING:" + record["candidate_id"])
    claims = {r["candidate_id"]: r for r in packet["objects"]["claims"]}
    result = []
    for candidate in expected:
        cid = candidate["claim_id"]
        require(cid in active_claim_ids and claims[cid]["human_input"]["decision"] == "KEEP", "RELATION_CLAIM_ADMISSION_BLOCKED:" + cid)
        require(claims[cid]["content"]["qualification_status"] == "DETERMINISTICALLY_MAPPABLE", "RELATION_CLAIM_EXCEPTION_UNRESOLVED:" + cid)
        require(candidate["authorization_state"] == "UNAUTHORIZED", "LINK_CANDIDATE_PREAUTHORIZED")
        result.append({"candidate": candidate, "claim_id": cid,
                       "evidence_role": (candidate["explicit_role"] or "SUPPORTS").lower(),
                       "authorization_state": "AUTHORIZED_BY_HUMAN_RELATION_AND_CLAIM_DECISIONS"})
    return result


def temporal_row(record, relation_id, packet):
    content = record["content"]
    expected = project_temporal(content["raw"])
    require(content.get("temporal_projection") == expected and all(content[k] == expected[k] for k in ("valid_from", "valid_to"))
            and content["status"] == expected["runtime_status"], "RELATION_TEMPORAL_PROJECTION_DRIFT")
    return {"relation_id": relation_id, "temporal_category": expected["temporal_category"],
            "valid_from_supplied": int("valid_from" in expected["native_validity"]),
            "valid_to_supplied": int("valid_to" in expected["native_validity"]),
            "projection_sha256": expected["projection_sha256"], "contract_sha256": CONTRACT_SHA256,
            "provenance_json": json.dumps({"native_temporal": restore_temporal(expected), "candidate_id": record["candidate_id"],
                "native_relation_sha256": canonical_sha256(content["raw"]), "package_sha256": packet["package"]["sha256"]}, ensure_ascii=False, sort_keys=True)}


def authorization_row(link, record, relation_id, packet):
    candidate = link["candidate"]
    native = link.get("provenance_mode") == "RELATION_NATIVE"
    if native:
        return {"link_candidate_id": candidate["link_candidate_id"], "relation_id": relation_id,
            "relation_candidate_id": record["candidate_id"], "claim_id": None, "provenance_mode": "RELATION_NATIVE",
            "evidence_id": candidate["evidence_id"], "source_id": candidate["source_id"], "source_sha256": candidate["source_sha256"],
            "evidence_sha256": candidate["evidence_sha256"], "evidence_role": link["evidence_role"], "authorization_state": "AUTHORIZED",
            "relation_decision": "", "claim_decision": None, "contract_sha256": CONTRACT_SHA256,
            "packet_sha256": packet["immutable_packet_sha256"], "reviewer": "EXPLICIT_HUMAN_GOVERNANCE_MANIFEST",
            "human_authorization_manifest_id": candidate["human_authorization_manifest_id"],
            "original_packet_sha256": candidate["original_packet_sha256"], "proposition_scope": candidate["scope"],
            "authorized_proposition": candidate["authorized_proposition"],
            "provenance_json": json.dumps({"candidate": candidate, "projected_relation_id": relation_id,
                "manifest_sha256": packet["evidence_governance_manifest"]["manifest_sha256"],
                "role_authority": "EXPLICIT_HUMAN_GOVERNANCE_NOT_CONTENT_REVIEW"}, ensure_ascii=False, sort_keys=True),
            "created_at": packet["frozen_timestamp"]}
    return {"link_candidate_id": candidate["link_candidate_id"], "relation_id": relation_id, "claim_id": candidate["claim_id"],
            "relation_candidate_id": record["candidate_id"], "provenance_mode": "CLAIM_LINKED",
            "evidence_id": candidate["evidence_id"], "source_id": candidate["source_id"], "source_sha256": candidate["source_sha256"],
            "evidence_sha256": candidate["evidence_sha256"], "evidence_role": link["evidence_role"], "authorization_state": "AUTHORIZED",
            "relation_decision": record["human_input"]["decision"], "claim_decision": "KEEP", "contract_sha256": CONTRACT_SHA256,
            "packet_sha256": packet["immutable_packet_sha256"], "reviewer": packet["human_completion"]["reviewer"],
            "human_authorization_manifest_id": "", "original_packet_sha256": "", "proposition_scope": "", "authorized_proposition": "",
            "provenance_json": json.dumps({"candidate": candidate, "relation_reason": record["human_input"]["reason"],
                "role_authority": "EXPLICIT_FROZEN_ROLE_AND_HUMAN_CONFIRMATION" if candidate["explicit_role"] else "EXPLICIT_HUMAN_CROSS_OBJECT_RULE_NOT_JOIN_ALONE"}, ensure_ascii=False, sort_keys=True),
            "created_at": packet["frozen_timestamp"]}


def evidence_link_row(link, relation_id, timestamp):
    row = {"relation_id": relation_id, "claim_id": link["claim_id"], "evidence_role": link["evidence_role"],
           "status": "active", "created_at": timestamp, "provenance_mode": "CLAIM_LINKED", "evidence_id": "",
           "source_id": None, "source_sha256": "", "evidence_sha256": "", "authorization_id": None}
    if link.get("provenance_mode") == "RELATION_NATIVE":
        c = link["candidate"]
        row.update(provenance_mode="RELATION_NATIVE", evidence_id=c["evidence_id"], source_id=c["source_id"],
                   source_sha256=c["source_sha256"], evidence_sha256=c["evidence_sha256"], authorization_id=c["link_candidate_id"])
    return row


def compare_review_objects(old, new):
    """Distinguish unchanged native meaning from changed review/authority content."""
    old_ids = {(kind, r["candidate_id"]): r for kind, rows in old["objects"].items() for r in rows}
    new_ids = {(kind, r["candidate_id"]): r for kind, rows in new["objects"].items() for r in rows}
    require(old_ids.keys() == new_ids.keys(), "REQUALIFICATION_CANDIDATE_UNIVERSE_DRIFT")
    return [{"kind": kind, "candidate_id": cid,
             "old_content_sha256": old_ids[kind, cid]["content_sha256"], "new_content_sha256": new_ids[kind, cid]["content_sha256"],
             "native_semantics_unchanged": old_ids[kind, cid]["content"]["raw"] == new_ids[kind, cid]["content"]["raw"],
             "review_content_unchanged": old_ids[kind, cid]["content"] == new_ids[kind, cid]["content"]}
            for kind, cid in sorted(old_ids)]


def requalified_objects(old_packet, governance_manifest=None):
    """Pure preparation, not a new frozen packet or authorization of real rows."""
    from .foundation_native_evidence import validate_manifest, native_authorizations, adjudicated_claim_content
    base = copy.deepcopy(old_packet)
    if governance_manifest is not None:
        validate_manifest(governance_manifest, old_packet["package"]["sha256"])
        require(governance_manifest["original_packet_sha256"] == old_packet["immutable_packet_sha256"], "GOVERNANCE_ORIGINAL_PACKET_DRIFT")
        for claim in base["objects"]["claims"]:
            claim["content"] = adjudicated_claim_content(claim, governance_manifest)
    objects = {}
    for kind, records in base["objects"].items():
        objects[kind] = []
        for record in records:
            content = copy.deepcopy(record["content"])
            if kind == "relations":
                rows = native_authorizations(record, governance_manifest, old_packet["registry"]) if governance_manifest else []
                content = relation_review_projection(record, base["objects"]["claims"], old_packet["package"]["sha256"], rows)
            elif kind == "claims":
                content["admission_contract"] = {
                    "contract_sha256": CONTRACT_SHA256,
                    "KEEP": "Explicit authorization: needs_review -> current; native/pre-review provenance retained.",
                    "KEEP_NEEDS_REVIEW": "Retained needs_review in review artifact; not persisted or active evidence in this adapter.",
                    "DROP": "No promotion or active evidence.",
                }
            elif kind == "baseline_views":
                content["artifact_status"] = CONTRACT["baseline_artifact_status"]
            objects[kind].append({"candidate_id": record["candidate_id"], "content": content})
    return objects


def categorical_relations(connection):
    """Explicit temporal-aware read; never falls back to a current-only selector."""
    return [dict(r) for r in connection.execute("""SELECT n.*,t.temporal_category,t.valid_from_supplied,t.valid_to_supplied,
        t.projection_sha256,t.provenance_json AS temporal_provenance_json
        FROM node_relations n JOIN relation_temporal_semantics t USING(relation_id) ORDER BY n.relation_id""")]
