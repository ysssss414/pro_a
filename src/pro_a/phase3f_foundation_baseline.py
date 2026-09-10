"""Hash-bound, global 1..N Source foundation review contract.

This module does not extract Sources, decide reviews, or write a database.
Native candidate content and deterministic projections are separate. Only the
shared Phase 3D engine can apply the resulting INSERT-only shadow payload.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3

from .constants import CLAIM_NATURES, NODE_TYPES, RELATION_TYPES
from .production_promotion import (
    PromotionError, canonical_sha256, deterministic_id, production_identity,
    sha256_file, build_identity_catalog, resolve_identity, nfkc_casefold,
)
from .relation_structure import directed_path_exists
from .db import ACTIVE_RELATION_SUPPORTING_CLAIM_STATUSES
from .foundation_execution_contract import (
    uses_contract, uses_identity_contract, BOUND_CONTRACT, BOUND_IDENTITY_CONTRACT, EXTRA_SNAPSHOT_TABLES, admitted_claim_row,
    authorize_links, temporal_row, authorization_row, project_temporal, evidence_link_row,
)


DOCUMENT_TYPE = "phase3f_foundation_baseline_review_packet"
PROFILE = "phase3f_complete_foundation_v1"
DECISIONS = {
    "claims": ("KEEP", "DROP", "KEEP_NEEDS_REVIEW"),
    "nodes": ("CREATE", "REUSE", "DEFER", "REJECT"),
    "aliases": ("ATTACH", "DEFER", "REJECT"),
    "relations": ("CREATE", "REUSE", "DEFER", "REJECT"),
    "baseline_views": ("ACCEPT", "DEFER", "REJECT"),
}


def require(condition, code):
    if not condition:
        raise PromotionError(code)


def seal(body, key):
    return {**copy.deepcopy(body), key: canonical_sha256(body)}


def blank_body(packet):
    body = copy.deepcopy(packet)
    body.pop("immutable_packet_sha256", None)
    body["human_completion"] = {"reviewer": "", "reason": ""}
    for records in body["objects"].values():
        for record in records:
            record["human_input"] = {"decision": "", "reason": "", "target_id": ""}
    return body


def build_review_packet(*, package, registry, production, repository_commit, objects, timestamp, execution_contract=None, evidence_governance_manifest=None, identity_evidence_index=None):
    """Build blank review from explicit lossless projections, never infer decisions."""
    require(set(objects) == set(DECISIONS), "OBJECT_UNIVERSE_INVALID")
    records = {}
    for kind, candidates in objects.items():
        records[kind] = [
            {"candidate_id": item["candidate_id"], "content": copy.deepcopy(item["content"]),
             "content_sha256": canonical_sha256(item["content"]),
             "allowed_decisions": list(DECISIONS[kind]),
             "human_input": {"decision": "", "reason": "", "target_id": ""}}
            for item in sorted(candidates, key=lambda item: item["candidate_id"])
        ]
    body = {
        "document_type": DOCUMENT_TYPE, "schema_version": 1,
        "packet_id": deterministic_id("FOUNDATION_REVIEW", package),
        "package": copy.deepcopy(package), "registry": copy.deepcopy(registry),
        "production_baseline": copy.deepcopy(production), "repository_commit": repository_commit,
        "frozen_timestamp": timestamp, "objects": records,
        "counts": {kind: len(items) for kind, items in records.items()},
        "candidate_manifest": {kind: [{"candidate_id": r["candidate_id"], "content_sha256": r["content_sha256"]}
                                      for r in items] for kind, items in records.items()},
        "human_completion": {"reviewer": "", "reason": ""},
        "decision_authority": "EXPLICIT_HUMAN_REVIEW_ONLY",
        "production_apply_authorized": False, "current_view_candidates": 0,
    }
    if execution_contract is not None:
        body["execution_contract"] = copy.deepcopy(execution_contract)
        body["packet_id"] = deterministic_id("FOUNDATION_REVIEW", {
            "package": package, "production_sha256": production["sha256"], "execution_contract": execution_contract,
        })
    if evidence_governance_manifest is not None:
        require(execution_contract in (BOUND_CONTRACT, BOUND_IDENTITY_CONTRACT), "NATIVE_EXECUTION_CONTRACT_NOT_BOUND")
        body["evidence_governance_manifest"] = copy.deepcopy(evidence_governance_manifest)
        body["packet_id"] = deterministic_id("FOUNDATION_REVIEW", {
            "prior_identity": body["packet_id"], "governance_manifest_sha256": evidence_governance_manifest["manifest_sha256"]})
    if execution_contract == BOUND_IDENTITY_CONTRACT:
        body["identity_evidence_index"] = copy.deepcopy(identity_evidence_index)
        body["identity_evidence_index_sha256"] = canonical_sha256(identity_evidence_index)
        body["packet_id"] = deterministic_id("FOUNDATION_REVIEW", {
            "prior_identity": body["packet_id"], "identity_evidence_index_sha256": body["identity_evidence_index_sha256"],
            "repository_commit": repository_commit})
    packet = seal(body, "immutable_packet_sha256")
    validate_review(packet, expected_sha256=packet["immutable_packet_sha256"], completed=False)
    return packet


def validate_review(packet, *, expected_sha256, completed):
    require(packet.get("document_type") == DOCUMENT_TYPE and packet.get("schema_version") == 1, "FOUNDATION_PACKET_TYPE_INVALID")
    require(packet.get("production_apply_authorized") is False, "PRODUCTION_AUTHORIZATION_FORBIDDEN")
    require(packet.get("decision_authority") == "EXPLICIT_HUMAN_REVIEW_ONLY", "HUMAN_AUTHORITY_INVALID")
    require(set(packet.get("objects", {})) == set(DECISIONS), "OBJECT_UNIVERSE_INVALID")
    require(canonical_sha256(blank_body(packet)) == packet.get("immutable_packet_sha256") == expected_sha256,
            "IMMUTABLE_PACKET_HASH_DRIFT")
    require(packet.get("current_view_candidates") == 0, "OFFICIAL_VIEW_CANDIDATE_FORBIDDEN")
    governed = uses_contract(packet)
    if uses_identity_contract(packet):
        from .foundation_identity_admission import validate_identity_evidence
        validate_identity_evidence(packet)
    governance_manifest = packet.get("evidence_governance_manifest")
    if governance_manifest is not None:
        from .foundation_native_evidence import validate_manifest
        require(governed, "NATIVE_EXECUTION_CONTRACT_NOT_BOUND")
        validate_manifest(governance_manifest, packet["package"]["sha256"])
    source_ids = [s["source_id"] for s in packet["registry"]["sources"]]
    require(source_ids and len(source_ids) == len(set(source_ids)), "SOURCE_REGISTRY_DUPLICATE_OR_EMPTY")
    registry = packet["registry"]
    require(registry["registry_sha256"] == canonical_sha256({k: v for k, v in registry.items() if k != "registry_sha256"}), "REGISTRY_HASH_DRIFT")
    require(registry["package_sha256"] == packet["package"]["sha256"], "PACKAGE_HASH_DRIFT")
    require(registry["package_inventory_sha256"] == packet["package"]["inventory_sha256"], "PACKAGE_INVENTORY_DRIFT")
    require(len(source_ids) == registry["expected_sources"] == registry["materialized_sources"], "SOURCE_MISSING")
    for source in registry["sources"]:
        require(source["exact_match"] is True and source["actual_sha256"] == source["expected_sha256"], "SOURCE_SHA_MISMATCH")
    seen = set()
    sources = {s["source_id"]: s for s in registry["sources"]}
    for kind, records in packet["objects"].items():
        require(len(records) == packet["counts"][kind], "CANDIDATE_COUNT_DRIFT")
        require([{k: r[k] for k in ("candidate_id", "content_sha256")} for r in records] == packet["candidate_manifest"][kind], "SILENT_CANDIDATE_OMISSION")
        for record in records:
            cid, content = record["candidate_id"], record["content"]
            require(cid not in seen, "DUPLICATE_CANDIDATE_ID")
            seen.add(cid)
            require(canonical_sha256(content) == record["content_sha256"], f"CANDIDATE_HASH_DRIFT:{cid}")
            require(record["allowed_decisions"] == list(DECISIONS[kind]), "DECISION_VOCABULARY_DRIFT")
            human = record["human_input"]
            require(set(human) == {"decision", "reason", "target_id"}, "HUMAN_FIELDS_INVALID")
            if completed:
                require(human["decision"] in DECISIONS[kind] and isinstance(human["reason"], str) and human["reason"].strip(), f"INCOMPLETE_HUMAN_REVIEW:{cid}")
            else:
                require(all(value == "" for value in human.values()), "BLANK_REVIEW_HAS_HUMAN_DECISIONS")
            if kind == "claims":
                source_id = content["source_id"]
                require(source_id in sources, f"UNREGISTERED_CLAIM_SOURCE:{cid}")
                require(content["source_sha256"] == sources[source_id]["expected_sha256"], f"CLAIM_SOURCE_SHA_MISMATCH:{cid}")
                for evidence in content["evidence"]:
                    require(evidence["source_id"] == source_id and evidence["source_sha256"] == content["source_sha256"], f"CROSS_SOURCE_PROVENANCE:{cid}")
                if "evidence_identity_adjudication" in content:
                    adjudication = content["evidence_identity_adjudication"]
                    require(governance_manifest is not None and adjudication in governance_manifest["claim_evidence_adjudications"], "UNBOUND_CLAIM_ADJUDICATION")
                    require(adjudication["claim_id"] == cid and adjudication["native_claim_sha256"] == canonical_sha256(content["raw"]), "ADJUDICATION_CLAIM_DRIFT")
                    require([e["evidence_id"] for e in content["evidence"]] == [adjudication["authoritative_evidence_id"]], "ADJUDICATION_EVIDENCE_SELECTION_DRIFT")
            if kind == "relations" and governed:
                require(content.get("decision_contract") == BOUND_CONTRACT, "RELATION_CROSS_OBJECT_RULE_NOT_BOUND")
                require(content.get("temporal_projection") == project_temporal(content["raw"]), "RELATION_TEMPORAL_PROJECTION_DRIFT")
                from .foundation_native_evidence import native_authorizations
                native = native_authorizations(record, governance_manifest, registry) if governance_manifest else []
                require(content.get("relation_native_authorizations", []) == native, "NATIVE_AUTHORIZATION_PROJECTION_DRIFT")
                require(content.get("evidence_provenance_mode") == ("RELATION_NATIVE" if native else "CLAIM_LINKED"), "RELATION_PROVENANCE_MODE_DRIFT")
    human = packet["human_completion"]
    if completed:
        require(all(isinstance(human[k], str) and human[k].strip() for k in ("reviewer", "reason")), "HUMAN_COMPLETION_MISSING")
    else:
        require(human == {"reviewer": "", "reason": ""}, "BLANK_REVIEW_HAS_HUMAN_AUTHORITY")


def validate_files(packet):
    """Hash bytes only, including on handoff reruns. No file is parsed here."""
    bindings = [("PACKAGE", packet["package"]), ("QUALIFICATION", packet["package"]["qualification_receipt"])]
    bindings.extend(("QUALIFICATION_ARTIFACT", item) for item in packet["package"].get("qualification_artifacts", []))
    for name, binding in bindings:
        path = Path(binding["path"])
        require(path.is_file(), f"{name}_FILE_MISSING")
        require(sha256_file(path) == binding["sha256"], f"{name}_HASH_DRIFT")
    for source in packet["registry"]["sources"]:
        path = Path(source["candidate_local_file"])
        require(path.is_file(), f"SOURCE_MISSING:{source['source_id']}")
        require(sha256_file(path) == source["expected_sha256"], f"SOURCE_SHA_MISMATCH:{source['source_id']}")


def claim_batches(packet):
    """Same immutable ID-list + content-binding authority as Claim batch review.

    Only clean Claims; source-local batches of at most 20. No other object class.
    """
    result = []
    for source in packet["registry"]["sources"]:
        records = [r for r in packet["objects"]["claims"] if r["content"]["source_id"] == source["source_id"]
                   and r["content"].get("qualification_status") == "DETERMINISTICALLY_MAPPABLE"]
        for start in range(0, len(records), 20):
            subset = records[start:start + 20]
            ids = [r["candidate_id"] for r in subset]
            bindings = [{"candidate_id": r["candidate_id"], "content_sha256": r["content_sha256"]} for r in subset]
            body = {"packet_id": packet["packet_id"], "immutable_packet_sha256": packet["immutable_packet_sha256"],
                    "source_id": source["source_id"], "source_sha256": source["expected_sha256"],
                    "candidate_ids": ids, "candidate_list_sha256": canonical_sha256(ids),
                    "candidate_content_bindings": bindings, "candidate_content_sha256": canonical_sha256(bindings)}
            result.append({**body, "batch_id": deterministic_id("CLAIM_BATCH", body),
                           "allowed_decisions": list(DECISIONS["claims"]),
                           "human_input": {"reviewer": "", "decision": "", "reason": ""}})
    return result


def expand_claim_batches(blank, completed, authorizations):
    expected = {b["batch_id"]: b for b in claim_batches(blank)}
    result = copy.deepcopy(completed)
    records = {r["candidate_id"]: r for r in result["objects"]["claims"]}
    used = set()
    for batch in authorizations:
        bid = batch["batch_id"]
        require(bid in expected and bid not in used, "BATCH_UNKNOWN_OR_DUPLICATE")
        used.add(bid)
        require({k: v for k, v in batch.items() if k != "human_input"} == {k: v for k, v in expected[bid].items() if k != "human_input"}, "BATCH_BINDING_DRIFT")
        human = batch["human_input"]
        require(human["reviewer"] == result["human_completion"]["reviewer"] and human["reason"].strip()
                and human["decision"] in DECISIONS["claims"], "BATCH_AUTHORITY_INVALID")
        for cid in batch["candidate_ids"]:
            require(records[cid]["human_input"] == {"decision": "", "reason": "", "target_id": ""}, "BATCH_INDIVIDUAL_CONFLICT")
            records[cid]["human_input"] = {"decision": human["decision"], "reason": human["reason"], "target_id": ""}
    validate_review(result, expected_sha256=blank["immutable_packet_sha256"], completed=True)
    return result


def _rows(connection, table):
    return [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]


def compile_mutations(packet, snapshot):
    """Deterministic projection. All explicit executable choices fail closed.

    Recompiled by Phase 3D validation; audit-only rows always retain a disposition.
    """
    timestamp = packet["frozen_timestamp"]
    governed = uses_contract(packet)
    mutations, mapping, node_ops, relation_ops, claims = [], [], [], [], []
    catalog = build_identity_catalog(snapshot["nodes"], snapshot["node_aliases"])
    identity = None
    if uses_identity_contract(packet):
        from .foundation_identity_admission import identity_plan, require_claim_subject
        identity = identity_plan(packet, snapshot, {
            r["candidate_id"]: r["human_input"] for rows in packet["objects"].values() for r in rows})
    source_rows = {r["source_id"]: r for r in snapshot["sources"]}
    claim_rows = {r["claim_id"]: r for r in snapshot["claims"]}
    nodes = dict(identity["references"]) if identity else {}  # V4 also admits exact active direct Production refs.
    executable_claims = set()
    active_evidence_claims = set()
    terms = {}
    relation_identities = {(r["from_node_id"], r["relation_type"], r["to_node_id"], r["scope"]): r for r in snapshot["node_relations"]}
    part_of = {(r["from_node_id"], r["to_node_id"]) for r in snapshot["node_relations"] if r["relation_type"] == "part_of" and r["status"] in ({"current", "categorical"} if governed else {"current"})}

    def mutate(table, key, row, authority):
        body = {"operation": "INSERT", "table": table, "key": key, "row": row, "authorized_by": authority}
        mutations.append({"mutation_id": deterministic_id("MUT", body), **body})

    def disposition(kind, record, executable):
        human = record["human_input"]
        mapping.append({"kind": kind, "candidate_id": record["candidate_id"], "content_sha256": record["content_sha256"],
                        "human_decision": human["decision"], "reason": human["reason"],
                        "disposition": "EXECUTABLE" if executable else "NON_EXECUTABLE"})

    for source in packet["registry"]["sources"]:
        sid = source["source_id"]
        if sid in source_rows:
            require(source_rows[sid]["sha256"] == source["expected_sha256"], f"SOURCE_ID_COLLISION:{sid}")
            continue
        require(not any(r["sha256"] == source["expected_sha256"] for r in source_rows.values()), f"SOURCE_SHA_ID_COLLISION:{sid}")
        row = {"source_id": sid, "title": source.get("title", sid), "original_name": Path(source["candidate_local_file"]).name,
               "archived_path": source["candidate_local_file"], "sha256": source["expected_sha256"],
               "ingestion_mode": "archive", "analysis_mode": "archive", "source_type": "unknown", "source_rank": "UNRANKED",
               "origin_type": "unknown", "author": "", "organization": "", "publication_time": "",
               "ingested_at": timestamp, "status": "stored", "ima_media_id": "", "ima_kb_id": "",
               "underlying_source_id": "", "metadata_json": json.dumps({"foundation_package": packet["package"], "source": source}, ensure_ascii=False, sort_keys=True)}
        mutate("sources", {"source_id": sid}, row, packet["packet_id"])
        source_rows[sid] = row
    for record in packet["objects"]["claims"]:
        cid, content = record["candidate_id"], record["content"]
        executable = record["human_input"]["decision"] == "KEEP"
        disposition("claims", record, executable)
        claims.append({"claim_id": cid, "source_id": content["source_id"], "executable": executable})
        if not executable:
            continue
        if identity:
            require_claim_subject(record, nodes)
        require(content.get("qualification_status") == "DETERMINISTICALLY_MAPPABLE", f"CLAIM_EXCEPTION_UNRESOLVED:{cid}")
        require(cid not in claim_rows, f"CLAIM_ID_COLLISION:{cid}")
        row = admitted_claim_row(record, packet) if governed else copy.deepcopy(content["row"])
        require(row["claim_id"] == cid and row["source_id"] == content["source_id"], f"CLAIM_PROJECTION_IDENTITY:{cid}")
        require(row["nature"] in CLAIM_NATURES, f"CLAIM_NATURE_INVALID:{cid}")
        require(row["statement"] == content["raw"]["statement"] and row["evidence_excerpt"] == content["raw"]["evidence_excerpt"], f"CLAIM_SEMANTIC_REWRITE:{cid}")
        for raw_key, row_key in (("fact_time", "fact_time"), ("publication_time", "publication_time"),
                                 ("scope", "scope"), ("attribution", "attributed_to"), ("evidence_locator", "evidence_pointer")):
            if raw_key in content["raw"]:
                native = content["raw"][raw_key]
                expected = "" if governed and raw_key in {"fact_time", "publication_time"} and native is None else native
                require(row[row_key] == expected, f"CLAIM_SEMANTIC_REWRITE:{cid}:{raw_key}")
        require(json.loads(row["structured_json"]).get("foundation_native") == content["raw"], f"CLAIM_NATIVE_METADATA_LOSS:{cid}")
        require(content["evidence"], f"CLAIM_EVIDENCE_MISSING:{cid}")
        executable_claims.add(cid)
        if row["status"] in ACTIVE_RELATION_SUPPORTING_CLAIM_STATUSES:
            active_evidence_claims.add(cid)
        mutate("claims", {"claim_id": cid}, row, cid)
    for record in packet["objects"]["nodes"]:
        cid, content, human = record["candidate_id"], record["content"], record["human_input"]
        decision = human["decision"]
        executable = decision in {"CREATE", "REUSE"}
        disposition("nodes", record, executable)
        op = {"operation_id": cid, "candidate_id": cid, "operation": decision, "executable": executable}
        node_ops.append(op)
        if not executable:
            continue
        if not identity:
            require(content["supporting_claim_ids"] and set(content["supporting_claim_ids"]) & executable_claims, f"NODE_SUPPORT_NON_EXECUTABLE:{cid}")
        else:
            op["identity_admission"] = copy.deepcopy(identity["nodes"][cid])
        require(content["primary_type"] in NODE_TYPES, f"NODE_TYPE_INVALID:{cid}")
        if decision == "REUSE":
            nid = human["target_id"]
            expected = content.get("expected_target")
            require(expected and nid == expected["node_id"] and catalog["nodes"].get(nid) == expected, f"NODE_REUSE_TARGET_DRIFT:{cid}")
            require(expected["status"] == "active" and expected["primary_type"] == content["primary_type"], f"NODE_REUSE_TYPE_MISMATCH:{cid}")
            require(resolve_identity(catalog, content["canonical_name"])["all_ids"] == [nid], f"NODE_REUSE_IDENTITY_AMBIGUOUS:{cid}")
            op.update(resolved_target_id=nid, expected_target=expected, resolution={"term": content["canonical_name"]})
        else:
            require(not human["target_id"], f"CREATE_TARGET_OVERRIDE:{cid}")
            nid = deterministic_id("NODE", {"package": packet["package"]["sha256"], "candidate_id": cid})
            require(nid not in catalog["nodes"] and not resolve_identity(catalog, content["canonical_name"])["all_ids"], f"NODE_COLLISION:{cid}")
            normalized = nfkc_casefold(content["canonical_name"])
            require(normalized not in terms, f"NODE_COLLISION:{cid}")
            terms[normalized] = nid
            row = {"node_id": nid, "canonical_name": content["canonical_name"], "primary_type": content["primary_type"],
                   "description": content.get("description", ""), "status": "active", "created_at": timestamp, "updated_at": timestamp}
            op.update(final_node=row, aliases=[])
            mutate("nodes", {"node_id": nid}, row, cid)
        nodes[cid] = nid
        if not identity:
            nodes[nid] = nid
    for record in packet["objects"]["aliases"]:
        cid, content, human = record["candidate_id"], record["content"], record["human_input"]
        executable = human["decision"] == "ATTACH"
        disposition("aliases", record, executable)
        if not executable:
            continue
        if identity:
            projection = identity["aliases"][cid]
            mapping[-1].update(copy.deepcopy(projection))
            if projection["runtime_alias_mutation_count"]:
                mutate("node_aliases", {"alias": content["alias"]},
                       {"alias": content["alias"], "node_id": projection["resolved_runtime_target_id"]}, cid)
            continue
        nid = nodes.get(content["target_ref"])
        require(nid is not None and human["target_id"] == nid, f"ALIAS_TARGET_NON_EXECUTABLE:{cid}")
        alias = content["alias"]
        require(isinstance(alias, str) and alias.strip() == alias and alias, f"ALIAS_INVALID:{cid}")
        owners = resolve_identity(catalog, alias)["all_ids"]
        require(not owners or owners == [nid], f"ALIAS_COLLISION:{cid}")
        normalized = nfkc_casefold(alias)
        require(terms.get(normalized, nid) == nid, f"ALIAS_COLLISION:{cid}")
        require(normalized not in {nfkc_casefold(n["canonical_name"]) for n in snapshot["nodes"] if n["node_id"] == nid}, f"ALIAS_EQUALS_CANONICAL:{cid}")
        require(not any(m["table"] == "nodes" and m["row"]["node_id"] == nid and nfkc_casefold(m["row"]["canonical_name"]) == normalized for m in mutations), f"ALIAS_EQUALS_CANONICAL:{cid}")
        require(not any(m["table"] == "node_aliases" and nfkc_casefold(m["row"]["alias"]) == normalized for m in mutations), f"DUPLICATE_ALIAS:{cid}")
        terms[normalized] = nid
        if not any(a["alias"] == alias and a["node_id"] == nid for a in snapshot["node_aliases"]):
            mutate("node_aliases", {"alias": alias}, {"alias": alias, "node_id": nid}, cid)
    seen_relations = set()
    for record in packet["objects"]["relations"]:
        cid, content, human = record["candidate_id"], record["content"], record["human_input"]
        decision = human["decision"]
        executable = decision in {"CREATE", "REUSE"}
        disposition("relations", record, executable)
        op = {"operation_id": cid, "candidate_id": cid, "operation": decision, "executable": executable}
        relation_ops.append(op)
        if not executable:
            continue
        require(content["relation_type"] in RELATION_TYPES, f"INVALID_RELATION_TYPE:{cid}")
        require(content.get("temporal_representation_lossless") is True, f"RELATION_TEMPORAL_MEANING_LOSS:{cid}")
        require(content["from_ref"] in nodes and content["to_ref"] in nodes, f"RELATION_ENDPOINT_NON_EXECUTABLE:{cid}")
        edge = (nodes[content["from_ref"]], content["relation_type"], nodes[content["to_ref"]], content["scope"])
        require(edge[0] != edge[2], f"PART_OF_CYCLE:{cid}" if edge[1] == "part_of" else f"RELATION_SELF_LOOP:{cid}")
        confidence = content["confidence"]
        require(confidence is None or (not isinstance(confidence, bool) and isinstance(confidence, (float, int)) and 0 <= confidence <= 1), f"RELATION_CONFIDENCE_INVALID:{cid}")
        require(edge not in seen_relations, f"DUPLICATE_RELATION_IDENTITY:{cid}")
        seen_relations.add(edge)
        row = {"relation_id": deterministic_id("REL", edge), "from_node_id": edge[0], "relation_type": edge[1],
               "to_node_id": edge[2], "scope": edge[3], "valid_from": content["valid_from"], "valid_to": content["valid_to"],
               "status": content["status"], "confidence": content["confidence"], "evidence_claim_id": content.get("evidence_claim_id"), "created_at": timestamp}
        if decision == "REUSE":
            existing = relation_identities.get(edge)
            require(existing is not None and existing["relation_id"] == human["target_id"], f"RELATION_REUSE_WRONG_TARGET:{cid}")
            require(content.get("expected_target") == existing, f"RELATION_REUSE_TARGET_DRIFT:{cid}")
            require(all(existing[k] == row[k] for k in ("valid_from", "valid_to", "status", "confidence")), f"RELATION_REUSE_SEMANTIC_DRIFT:{cid}")
            row = copy.deepcopy(existing)
        else:
            require(edge not in relation_identities, f"DUPLICATE_RELATION_IDENTITY:{cid}")
            if edge[1] == "part_of":
                require(edge[0] != edge[2] and not directed_path_exists(part_of, edge[2], edge[0]), f"PART_OF_CYCLE:{cid}")
                require(not directed_path_exists(part_of, edge[0], edge[2]), f"PART_OF_TRANSITIVE_REDUNDANCY:{cid}")
                part_of.add((edge[0], edge[2]))
            mutate("node_relations", {"relation_id": row["relation_id"]}, row, cid)
        op["final_relation"] = row
        if governed:
            temporal = temporal_row(record, row["relation_id"], packet)
            existing_temporal = next((r for r in snapshot["relation_temporal_semantics"] if r["relation_id"] == row["relation_id"]), None)
            if existing_temporal:
                require(all(existing_temporal[k] == v for k, v in temporal.items() if k != "provenance_json"), f"RELATION_TEMPORAL_REUSE_DRIFT:{cid}")
            else:
                mutate("relation_temporal_semantics", {"relation_id": row["relation_id"]}, temporal, cid)
            effective_links = authorize_links(record, packet, active_evidence_claims)
            for link in effective_links:
                auth = authorization_row(link, record, row["relation_id"], packet)
                require(not any(r["link_candidate_id"] == auth["link_candidate_id"] for r in snapshot["relation_evidence_authorizations"]), f"RELATION_AUTHORIZATION_ALREADY_BOUND:{cid}")
                mutate("relation_evidence_authorizations", {"link_candidate_id": auth["link_candidate_id"]}, auth, cid)
        else:
            effective_links = content["evidence_links"]
        if row["evidence_claim_id"]:
            require(row["evidence_claim_id"] in executable_claims, f"RELATION_EVIDENCE_CLAIM_NON_EXECUTABLE:{cid}")
        require(effective_links, f"RELATION_EVIDENCE_MISSING:{cid}")
        for evidence in effective_links:
            if evidence.get("provenance_mode") == "RELATION_NATIVE":
                native_row = evidence_link_row(evidence, row["relation_id"], timestamp)
                key = {k: native_row[k] for k in ("relation_id", "provenance_mode", "evidence_id", "evidence_role")}
                mutate("relation_evidence_links", key, native_row, cid)
                continue
            require(evidence["claim_id"] in executable_claims, f"RELATION_EVIDENCE_CLAIM_NON_EXECUTABLE:{cid}")
            require(evidence["claim_id"] in active_evidence_claims, f"RELATION_EVIDENCE_CLAIM_NOT_ACTIVE:{cid}")
            require(evidence["evidence_role"] in {"supports", "contradicts"}, f"RELATION_EVIDENCE_ROLE_INVALID:{cid}")
            key = {"relation_id": row["relation_id"], "claim_id": evidence["claim_id"], "evidence_role": evidence["evidence_role"]}
            existing = [r for r in snapshot["relation_evidence_links"] if all(r[k] == v for k, v in key.items())]
            if existing:
                require(existing[0]["status"] == "active", f"RELATION_EVIDENCE_RETIRED:{cid}")
            elif not any(m["table"] == "relation_evidence_links" and m["key"] == key for m in mutations):
                stored_link = evidence_link_row(evidence, row["relation_id"], timestamp) if governed else {**key, "status": "active", "created_at": timestamp}
                mutate("relation_evidence_links", key, stored_link, cid)
    for record in packet["objects"]["baseline_views"]:
        cid, content, human = record["candidate_id"], record["content"], record["human_input"]
        executable = human["decision"] == "ACCEPT"
        disposition("baseline_views", record, executable)
        if not executable:
            continue
        require(content["target_ref"] in nodes, f"BASELINE_NODE_NON_EXECUTABLE:{cid}")
        require(content["supporting_claim_ids"] and set(content["supporting_claim_ids"]) <= executable_claims, f"BASELINE_CLAIM_NON_EXECUTABLE:{cid}")
        support_sources = {r["content"]["source_id"] for r in packet["objects"]["claims"] if r["candidate_id"] in content["supporting_claim_ids"]}
        require(support_sources <= set(content["supporting_source_ids"]) <= set(source_rows), f"BASELINE_SOURCE_PROVENANCE_MISMATCH:{cid}")
        vid = deterministic_id("BASELINE", {"package": packet["package"]["sha256"], "candidate_id": cid})
        provenance = {"baseline_content_json": content["content_json"], "candidate_id": cid, "package": packet["package"],
                      "content_sha256": record["content_sha256"], "supporting_claim_ids": content["supporting_claim_ids"],
                      "supporting_source_ids": content["supporting_source_ids"], "as_of": content["as_of"]}
        if governed:
            provenance["artifact_status"] = BOUND_CONTRACT["baseline_artifact_status"]
        row = {"view_id": vid, "node_id": nodes[content["target_ref"]], "version": "baseline_" + vid,
               "status": "baseline", "change_level": "baseline", "previous_view_id": None,
               "content_md": content["content_md"], "content_json": json.dumps(provenance, ensure_ascii=False, sort_keys=True),
               "trigger_source_id": None, "trigger_claim_ids_json": json.dumps(content["supporting_claim_ids"]),
               "revision_date": content["as_of"], "revision_seq": 0, "accepted_proposal_id": "", "created_at": timestamp, "confirmed_at": timestamp}
        mutate("current_views", {"view_id": vid}, row, cid)
    require(len(mapping) == sum(packet["counts"].values()), "SILENT_CANDIDATE_OMISSION")
    keys = [(m["table"], canonical_sha256(m["key"])) for m in mutations]
    require(len(keys) == len(set(keys)), "DUPLICATE_MUTATION_KEY")
    return {"intended_mutations": mutations, "mapping": mapping, "node_operations": node_ops, "relation_operations": relation_ops, "claims": claims}


SNAPSHOT_TABLES = ("sources", "claims", "nodes", "node_aliases", "node_relations", "relation_evidence_links")


def _snapshot_tables(packet):
    return SNAPSHOT_TABLES + (EXTRA_SNAPSHOT_TABLES if uses_contract(packet) else ())


def build_foundation_handoff(*, packet, blank_packet, production_path, repository_commit,
                             verification_basis=None, completed_artifact=None):
    from .foundation_payload_envelope import verify_completed_artifact, BOUND_CONTRACT as ENVELOPE_CONTRACT
    actual_packet, review_basis = verify_completed_artifact(verification_basis, completed_artifact)
    require(canonical_sha256(packet) == canonical_sha256(actual_packet), "EMBEDDED_COMPLETED_ARTIFACT_MISMATCH")
    require(repository_commit == verification_basis.expected_payload_implementation_commit, "PAYLOAD_IMPLEMENTATION_BINDING_MISMATCH")
    validate_review(blank_packet, expected_sha256=blank_packet["immutable_packet_sha256"], completed=False)
    validate_review(packet, expected_sha256=blank_packet["immutable_packet_sha256"], completed=True)
    validate_files(packet)
    production = production_identity(Path(production_path))
    require(production == packet["production_baseline"], "PRODUCTION_BASELINE_DRIFT")
    with sqlite3.connect(Path(production_path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(set(_snapshot_tables(packet)) <= tables, "RELATION_EVIDENCE_SCHEMA_PRECONDITION_MISSING")
        if uses_contract(packet):
            from .foundation_schema_preparation import require_execution_schema
            require_execution_schema(connection)
        snapshot = {table: _rows(connection, table) for table in _snapshot_tables(packet)}
        if any(r["human_input"]["decision"] == "ACCEPT" for r in packet["objects"]["baseline_views"]):
            from .baseline_views import require_baseline_guards
            require_baseline_guards(connection)
    compiled = compile_mutations(packet, snapshot)
    body = {"document_type": "phase3d_promotion_payload", "payload_version": "1", "adapter_type": PROFILE,
            "production_authorization": False, "production_apply_authorized": False,
            "qualification_only": True, "qualified_execution_target": "DISPOSABLE_SHADOW_ONLY",
            "review_basis": review_basis, "payload_envelope_contract": copy.deepcopy(ENVELOPE_CONTRACT),
            "metadata": {"repository_commit": repository_commit, "production_sha256": production["sha256"],
                         "review_basis_implementation_commit": packet["repository_commit"],
                         "payload_builder_verifier_implementation_commit": repository_commit,
                         "production_schema_version": production["schema_version"], "production_schema_sha256": production["schema_sha256"],
                         "production_counts": production["counts"], "source_sha256": [r["expected_sha256"] for r in packet["registry"]["sources"]],
                         "input_artifact_roles_and_sha256": [{"role": "foundation_review", "file_sha256": review_basis["completed_packet_file_sha256"]}]},
            "foundation_review": packet, "immutable_packet_sha256": blank_packet["immutable_packet_sha256"],
            "foundation_snapshot": snapshot, **compiled}
    digest = canonical_sha256(body)
    payload = {**body, "payload_hash": digest, "payload_id": "PROMO_" + digest[:16].upper()}
    from .production_promotion import validate_payload
    validate_payload(payload, verification_basis=verification_basis, completed_artifact=completed_artifact)
    return {"payload": payload, "mapping": compiled["mapping"]}


def validate_foundation_payload(payload, connection=None, *, verification_basis=None, completed_artifact=None):
    from .foundation_payload_envelope import verify_payload_review_basis
    verify_payload_review_basis(payload, verification_basis, completed_artifact)
    require(payload.get("production_authorization") is False and payload.get("production_apply_authorized") is False
            and payload.get("qualification_only") is True, "PRODUCTION_AUTHORIZATION_FORBIDDEN")
    packet = payload["foundation_review"]
    validate_review(packet, expected_sha256=payload["immutable_packet_sha256"], completed=True)
    validate_files(packet)
    require(payload["metadata"]["review_basis_implementation_commit"] == packet["repository_commit"], "GIT_BASELINE_DRIFT")
    require(payload["metadata"]["source_sha256"] == [r["expected_sha256"] for r in packet["registry"]["sources"]], "PAYLOAD_SOURCE_BINDING_DRIFT")
    expected = compile_mutations(packet, payload["foundation_snapshot"])
    for key, value in expected.items():
        require(payload.get(key) == value, f"FOUNDATION_PAYLOAD_PROJECTION_DRIFT:{key}")
    baseline = packet["production_baseline"]
    for field in ("sha256", "schema_version", "schema_sha256", "counts"):
        require(payload["metadata"]["production_" + field] == baseline[field], "PAYLOAD_PRODUCTION_BINDING_DRIFT")
    if connection is not None:
        if uses_contract(packet):
            from .foundation_schema_preparation import require_execution_schema
            require_execution_schema(connection)
        for table in _snapshot_tables(packet):
            require(sorted(_rows(connection, table), key=canonical_sha256) == sorted(payload["foundation_snapshot"][table], key=canonical_sha256), f"FOUNDATION_SNAPSHOT_DRIFT:{table}")
        if any(m["table"] == "current_views" for m in payload["intended_mutations"]):
            from .baseline_views import require_baseline_guards
            require_baseline_guards(connection)
