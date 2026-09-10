"""V4 identity planning and non-authorizing eligibility preview. No DB writes.

Identity planning is shared by the preview and the real compiler. Evidence and
Claim lifecycle authority remain governed by the unchanged V3 storage contract.
"""
from __future__ import annotations

import json

from .constants import NODE_TYPES, CLAIM_NATURES, RELATION_TYPES
from .production_promotion import (PromotionError, canonical_sha256, deterministic_id,
                                   build_identity_catalog, resolve_identity, nfkc_casefold)
from .foundation_execution_contract import uses_identity_contract, authorize_links, project_temporal
from .relation_structure import directed_path_exists


def require(condition, code):
    if not condition:
        raise PromotionError(code)


def validate_identity_evidence(packet):
    index = packet.get("identity_evidence_index", {})
    require(index and canonical_sha256(index) == packet.get("identity_evidence_index_sha256"), "IDENTITY_EVIDENCE_INDEX_DRIFT")
    sources = {s["source_id"]: s for s in packet["registry"]["sources"]}
    accounting = {(a["kind"], a["object_id"]): a["content_sha256"] for a in packet["package"].get("object_accounting", [])}
    for eid, evidence in index.items():
        require(evidence["evidence_id"] == eid and evidence["source_id"] in sources, "IDENTITY_EVIDENCE_SOURCE_INVALID:" + eid)
        source = sources[evidence["source_id"]]
        require(source["exact_match"] and source["expected_sha256"] == source["actual_sha256"], "IDENTITY_SOURCE_SHA_DRIFT:" + eid)
        if accounting:
            require(accounting.get(("evidence", eid)) == canonical_sha256(evidence), "IDENTITY_PACKAGE_EVIDENCE_DRIFT:" + eid)
    return index


def identity_plan(packet, snapshot, decisions):
    """Semantic references -> identities/effects, never insert rows or authority."""
    require(uses_identity_contract(packet), "IDENTITY_CONTRACT_REQUIRED")
    evidence = validate_identity_evidence(packet)
    catalog = build_identity_catalog(snapshot["nodes"], snapshot["node_aliases"])
    references, node_plans, alias_plans, names, terms = {}, {}, {}, {}, {}
    for nid, node in catalog["nodes"].items():
        if (node["status"] == "active" and node["primary_type"] in NODE_TYPES and node["canonical_name"].strip()
                and resolve_identity(catalog, node["canonical_name"])["all_ids"] == [nid]):
            references[nid] = nid
            names[nid] = node["canonical_name"]
    for record in packet["objects"]["nodes"]:
        cid, c = record["candidate_id"], record["content"]
        human = decisions[cid]
        if human["decision"] not in {"CREATE", "REUSE"}:
            continue
        require(c["primary_type"] in NODE_TYPES, "NODE_TYPE_INVALID:" + cid)
        require(isinstance(c["canonical_name"], str) and c["canonical_name"].strip(), "NODE_CANONICAL_MISSING:" + cid)
        matches = resolve_identity(catalog, c["canonical_name"])["all_ids"]
        if human["decision"] == "REUSE":
            nid, expected = human["target_id"], c.get("expected_target")
            require(expected and expected["node_id"] == nid and catalog["nodes"].get(nid) == expected, "NODE_REUSE_TARGET_DRIFT:" + cid)
            require(nid in references and expected["primary_type"] == c["primary_type"], "NODE_REUSE_TYPE_OR_STATUS_INVALID:" + cid)
            require(matches == [nid], "NODE_REUSE_IDENTITY_AMBIGUOUS:" + cid)
            bindings = []
            basis = "EXACT_ACTIVE_PRODUCTION_NODE_IDENTITY"
        else:
            require(not human["target_id"], "CREATE_TARGET_OVERRIDE:" + cid)
            nid = deterministic_id("NODE", {"package": packet["package"]["sha256"], "candidate_id": cid})
            normalized = nfkc_casefold(c["canonical_name"])
            require(not matches and nid not in catalog["nodes"] and normalized not in terms, "NODE_COLLISION:" + cid)
            refs = c.get("evidence_refs", [])
            require(refs and len(refs) == len(set(refs)) and all(e in evidence for e in refs), "NODE_IDENTITY_PROVENANCE_MISSING:" + cid)
            sources = {s["source_id"]: s["expected_sha256"] for s in packet["registry"]["sources"]}
            bindings = [{"evidence_id": e, "evidence_sha256": canonical_sha256(evidence[e]),
                         "source_id": evidence[e]["source_id"], "source_sha256": sources[evidence[e]["source_id"]]} for e in refs]
            basis = "EXPLICIT_CREATE_IDENTITY_AND_TYPE_WITH_IMMUTABLE_EVIDENCE_PROVENANCE"
            terms[normalized] = nid
        references[cid] = nid
        names[nid] = catalog["nodes"][nid]["canonical_name"] if human["decision"] == "REUSE" else c["canonical_name"]
        node_plans[cid] = {"resolved_runtime_target_id": nid, "decision": human["decision"], "resolution_basis": basis,
                           "identity_evidence_bindings": bindings,
                           "supporting_claim_ids_execution_role": "NON_BLOCKING_NODE_IDENTITY_PROVENANCE"}
    added_aliases = set()
    for record in packet["objects"]["aliases"]:
        cid, c = record["candidate_id"], record["content"]
        human = decisions[cid]
        if human["decision"] != "ATTACH":
            continue
        semantic = human["target_id"]
        require(semantic in references and c["target_ref"] in references, "NODE_REFERENCE_NON_EXECUTABLE:" + cid)
        nid = references[semantic]
        require(nid == references[c["target_ref"]], "ALIAS_TARGET_ID_MISMATCH:" + cid)
        alias = c["alias"]
        require(isinstance(alias, str) and alias.strip() == alias and alias, "ALIAS_INVALID:" + cid)
        normalized = nfkc_casefold(alias)
        owners = resolve_identity(catalog, alias)["all_ids"]
        require((not owners or owners == [nid]) and terms.get(normalized, nid) == nid, "ALIAS_COLLISION:" + cid)
        if normalized == nfkc_casefold(names[nid]):
            effect, count = "ATTACH_NOOP_CANONICAL_EQUIVALENT", 0
            reason = "Same target canonical under existing NFKC/casefold rule; no other owner; no redundant alias row."
        elif any(a["alias"] == alias and a["node_id"] == nid for a in snapshot["node_aliases"]):
            effect, count = "ATTACH_NOOP_ALREADY_PRESENT", 0
            reason = "Exact alias already belongs to the same existing target."
        else:
            require(normalized not in added_aliases, "DUPLICATE_ALIAS:" + cid)
            added_aliases.add(normalized)
            effect, count = "ATTACH_INSERT", 1
            reason = "Distinct unowned term resolves to the reviewed target."
        terms[normalized] = nid
        alias_plans[cid] = {"human_decision": human["decision"], "approved_semantic_target_ref": semantic,
                            "resolved_runtime_target_id": nid,
                            "resolution_basis": "APPROVED_CANDIDATE_" + node_plans[semantic]["decision"] if semantic in node_plans else "DIRECT_ACTIVE_EXISTING_NODE",
                            "compile_effect": effect, "compile_effect_reason": reason, "runtime_alias_mutation_count": count}
    return {"references": references, "nodes": node_plans, "aliases": alias_plans}


def require_claim_subject(record, references):
    require(record["content"]["raw"].get("subject_ref") in references, "KEEP_CLAIM_WITH_NONEXECUTABLE_SUBJECT:" + record["candidate_id"])


def preview_eligibility(blank, snapshot, decisions):
    """Validate a separately supplied slate against a BLANK V4 review basis.

    Does not set human_completion, create a completed packet, call a mutation
    compiler, or return rows usable as a promotion payload.
    """
    from .phase3f_foundation_baseline import validate_review, DECISIONS
    validate_review(blank, expected_sha256=blank["immutable_packet_sha256"], completed=False)
    records = {r["candidate_id"]: r for rows in blank["objects"].values() for r in rows}
    require(set(decisions) == set(records), "PREVIEW_DECISION_UNIVERSE_DRIFT")
    for kind, rows in blank["objects"].items():
        for r in rows:
            human = decisions[r["candidate_id"]]
            require(human["decision"] in DECISIONS[kind] and isinstance(human["reason"], str) and human["reason"].strip()
                    and isinstance(human["target_id"], str), "PREVIEW_DECISION_INVALID:" + r["candidate_id"])
    plan = identity_plan(blank, snapshot, decisions)
    refs = plan["references"]
    sources = {r["source_id"]: r["sha256"] for r in snapshot["sources"]}
    for source in blank["registry"]["sources"]:
        sid = source["source_id"]
        require(sid not in sources or sources[sid] == source["expected_sha256"], "SOURCE_ID_COLLISION:" + sid)
        require(not any(sha == source["expected_sha256"] and other != sid for other,sha in sources.items()), "SOURCE_SHA_ID_COLLISION:" + sid)
        sources[sid] = source["expected_sha256"]
    keep = set()
    for record in blank["objects"]["claims"]:
        cid, c = record["candidate_id"], record["content"]
        if decisions[cid]["decision"] != "KEEP":
            continue
        require(c["qualification_status"] == "DETERMINISTICALLY_MAPPABLE", "CLAIM_EXCEPTION_UNRESOLVED:" + cid)
        require_claim_subject(record, refs)
        require(not any(r["claim_id"] == cid for r in snapshot["claims"]), "CLAIM_ID_COLLISION:" + cid)
        row, raw = c["row"], c["raw"]
        require(row["status"] in {"needs_review", "current"} and row["nature"] in CLAIM_NATURES, "CLAIM_ADMISSION_INPUT_INVALID:" + cid)
        require(row["claim_id"] == cid and row["source_id"] == c["source_id"], "CLAIM_PROJECTION_IDENTITY:" + cid)
        metadata = json.loads(row["structured_json"])
        require(metadata.get("foundation_native") == raw and "foundation_admission" not in metadata, "CLAIM_NATIVE_METADATA_LOSS:" + cid)
        for a, b in (("statement", "statement"), ("evidence_excerpt", "evidence_excerpt"), ("fact_time", "fact_time"),
                     ("publication_time", "publication_time"), ("scope", "scope"), ("attribution", "attributed_to"), ("evidence_locator", "evidence_pointer")):
            if a in raw:
                require(row[b] == raw[a], "CLAIM_SEMANTIC_REWRITE:" + cid + ":" + a)
        require(c["evidence"], "CLAIM_EVIDENCE_MISSING:" + cid)
        keep.add(cid)
    edges, seen, relation_checks = {}, set(), []
    for r in snapshot["node_relations"]:
        edges[r["from_node_id"], r["relation_type"], r["to_node_id"], r["scope"]] = r
    part_of = {(r["from_node_id"], r["to_node_id"]) for r in snapshot["node_relations"] if r["relation_type"] == "part_of" and r["status"] in {"current", "categorical"}}
    for record in blank["objects"]["relations"]:
        cid, c = record["candidate_id"], record["content"]
        decision = decisions[cid]["decision"]
        if decision not in {"CREATE", "REUSE"}:
            continue
        require(c["from_ref"] in refs and c["to_ref"] in refs, "CREATE_RELATION_WITH_NONEXECUTABLE_ENDPOINT:" + cid)
        require(c["relation_type"] in RELATION_TYPES, "INVALID_RELATION_TYPE:" + cid)
        projection = project_temporal(c["raw"])
        require(c["temporal_representation_lossless"] and c["temporal_projection"] == projection
                and all(c[k] == projection[k] for k in ("valid_from", "valid_to")) and c["status"] == "categorical", "RELATION_TEMPORAL_MEANING_LOSS:" + cid)
        edge = (refs[c["from_ref"]], c["relation_type"], refs[c["to_ref"]], c["scope"])
        require(edge[0] != edge[2] and edge not in seen, "RELATION_IDENTITY_INVALID:" + cid)
        confidence = c["confidence"]
        require(confidence is None or (not isinstance(confidence, bool) and isinstance(confidence, (float, int)) and 0 <= confidence <= 1), "RELATION_CONFIDENCE_INVALID:" + cid)
        seen.add(edge)
        if decision == "CREATE":
            require(edge not in edges, "DUPLICATE_RELATION_IDENTITY:" + cid)
            if edge[1] == "part_of":
                require(not directed_path_exists(part_of, edge[2], edge[0]), "PART_OF_CYCLE:" + cid)
                require(not directed_path_exists(part_of, edge[0], edge[2]), "PART_OF_TRANSITIVE_REDUNDANCY:" + cid)
                part_of.add((edge[0], edge[2]))
        else:
            existing = edges.get(edge)
            require(existing and decisions[cid]["target_id"] == existing["relation_id"] and c.get("expected_target") == existing, "RELATION_REUSE_TARGET_DRIFT:" + cid)
            require(all(existing[k] == c[k] for k in ("valid_from", "valid_to", "status", "confidence")), "RELATION_REUSE_SEMANTIC_DRIFT:" + cid)
        links = authorize_links(record, blank, keep, preview_decisions=decisions)
        require(not c.get("evidence_claim_id") or c["evidence_claim_id"] in keep, "RELATION_EVIDENCE_CLAIM_NON_EXECUTABLE:" + cid)
        require(not any(a["link_candidate_id"] == link["candidate"]["link_candidate_id"] for a in snapshot["relation_evidence_authorizations"] for link in links), "RELATION_AUTHORIZATION_ALREADY_BOUND:" + cid)
        relation_checks.append({"candidate_id": cid, "endpoint_resolution": [edge[0], edge[2]], "evidence_eligibility": links})
    for record in blank["objects"]["baseline_views"]:
        cid, c = record["candidate_id"], record["content"]
        if decisions[cid]["decision"] != "ACCEPT":
            continue
        require(c["target_ref"] in refs, "BASELINE_NODE_NON_EXECUTABLE:" + cid)
        require(c["supporting_claim_ids"] and set(c["supporting_claim_ids"]) <= keep, "BASELINE_CLAIM_NON_EXECUTABLE:" + cid)
        support_sources = {records[x]["content"]["source_id"] for x in c["supporting_claim_ids"]}
        require(support_sources <= set(c["supporting_source_ids"]) <= {s["source_id"] for s in blank["registry"]["sources"]}, "BASELINE_SOURCE_PROVENANCE_MISMATCH:" + cid)
    return {"document_type": "NON_AUTHORIZING_IDENTITY_AND_ELIGIBILITY_PREVIEW", "dependency_closure": "PASS",
            "executable_payload_built": False, "human_reauthorization_required": True,
            "identity_plan": plan, "qualified_keep_ids": sorted(keep), "relation_checks": relation_checks,
            "canonical_equivalent_noop_count": sum(a["compile_effect"] == "ATTACH_NOOP_CANONICAL_EQUIVALENT" for a in plan["aliases"].values())}
