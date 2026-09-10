"""Separate, immutable evidence governance; never a content-review decision."""
from __future__ import annotations

import copy
from datetime import date
import json

from .production_promotion import canonical_sha256, deterministic_id, PromotionError


def require(condition, code):
    if not condition:
        raise PromotionError(code)


def _manifest_body(manifest):
    body = copy.deepcopy(manifest)
    body.pop("manifest_sha256", None)
    body.pop("manifest_id", None)
    for row in body["relation_native_authorizations"] + body["claim_evidence_adjudications"]:
        row.pop("human_authorization_manifest_id", None)
    return body


def validate_manifest(manifest, package_sha256):
    from .foundation_execution_contract import CONTRACT_SHA256
    require(manifest["document_type"] == "foundation_evidence_governance_authorization", "GOVERNANCE_MANIFEST_TYPE")
    require(manifest["manifest_sha256"] == canonical_sha256({k: v for k, v in manifest.items() if k != "manifest_sha256"}), "GOVERNANCE_MANIFEST_HASH_DRIFT")
    require(manifest["manifest_id"] == deterministic_id("FOUNDATION_GOVERNANCE", _manifest_body(manifest)), "GOVERNANCE_MANIFEST_ID_DRIFT")
    require(manifest["package_sha256"] == package_sha256 and manifest["contract_sha256"] == CONTRACT_SHA256, "GOVERNANCE_BASELINE_DRIFT")
    require(manifest["content_review_decisions_authorized"] is False, "GOVERNANCE_IS_NOT_CONTENT_REVIEW")
    keys = []
    for row in manifest["relation_native_authorizations"]:
        require(row["human_authorization_manifest_id"] == manifest["manifest_id"] and row["relation_decision"] == "", "GOVERNANCE_IS_NOT_RELATION_DECISION")
        require(row["authorized"] is True and row["role"] in {"SUPPORTS", "CONTRADICTS"}, "NATIVE_ROLE_NOT_AUTHORIZED")
        require(row["evidence_sha256"] == canonical_sha256(row["evidence_content"]), "NATIVE_EVIDENCE_HASH_DRIFT")
        require(row["evidence_id"] == row["evidence_content"]["evidence_id"] and row["source_id"] == row["evidence_content"]["source_id"], "NATIVE_EVIDENCE_IDENTITY_DRIFT")
        require(row["original_packet_sha256"] == manifest["original_packet_sha256"] and row["package_sha256"] == package_sha256, "NATIVE_ORIGINAL_PACKET_DRIFT")
        require(row["contract_sha256"] == CONTRACT_SHA256 and row["authorized_proposition"].strip() and row["authorization_basis"].strip(), "NATIVE_PROPOSITION_AUTHORITY_MISSING")
        keys.append((row["relation_candidate_id"], row["evidence_id"], row["role"]))
    require(len(keys) == len(set(keys)), "DUPLICATE_NATIVE_AUTHORIZATION")
    ids = []
    for row in manifest["claim_evidence_adjudications"]:
        require(row["human_authorization_manifest_id"] == manifest["manifest_id"] and row["human_content_decision"] == "", "ADJUDICATION_IS_NOT_KEEP_DROP")
        require(row["reason"].strip() and row["authority_type"] == "EXPLICIT_HUMAN_SEMANTIC_ADJUDICATION", "ADJUDICATION_AUTHORITY_MISSING")
        ids.append(row["claim_id"])
    require(len(ids) == len(set(ids)), "DUPLICATE_CLAIM_ADJUDICATION")


def build_governance_manifest(packet, evidence_by_id, specs, adjudications, authority):
    """Freeze ONLY supplied human selections, never infer roles from source text."""
    from .foundation_execution_contract import CONTRACT_SHA256
    from .phase3f_foundation_baseline import validate_review
    validate_review(packet, expected_sha256=packet["immutable_packet_sha256"], completed=False)
    relations = {r["candidate_id"]: r for r in packet["objects"]["relations"]}
    claims = {r["candidate_id"]: r for r in packet["objects"]["claims"]}
    sources = {r["source_id"]: r["expected_sha256"] for r in packet["registry"]["sources"]}
    require(authority["kind"] == "EXPLICIT_HUMAN_GOVERNANCE_INSTRUCTION" and len(authority["instruction_sha256"]) == 64, "EXPLICIT_GOVERNANCE_AUTHORITY_REQUIRED")
    body = {"document_type": "foundation_evidence_governance_authorization", "schema_version": 1,
            "package_sha256": packet["package"]["sha256"], "original_packet_id": packet["packet_id"],
            "original_packet_sha256": packet["immutable_packet_sha256"], "contract_sha256": CONTRACT_SHA256,
            "authority": copy.deepcopy(authority), "content_review_decisions_authorized": False,
            "relation_native_authorizations": [], "claim_evidence_adjudications": []}
    for spec in specs:
        record = relations[spec["relation_candidate_id"]]
        content = record["content"]
        evidence = evidence_by_id[spec["evidence_id"]]
        require(spec["evidence_id"] in content["evidence_refs"], "NATIVE_EVIDENCE_NOT_IN_ORIGINAL_RELATION")
        require(spec["source_id"] == evidence["source_id"] and spec["source_sha256"] == sources[spec["source_id"]], "NATIVE_SOURCE_SHA_MISMATCH")
        require(spec["scope"] == content["scope"] and spec["temporal_status"] == content["raw"]["temporal_status"], "NATIVE_SCOPE_MISMATCH")
        row = {**copy.deepcopy(spec), "evidence_content": copy.deepcopy(evidence), "evidence_sha256": canonical_sha256(evidence),
               "native_relation_sha256": canonical_sha256(content["raw"]), "original_content_sha256": record["content_sha256"],
               "original_packet_sha256": packet["immutable_packet_sha256"], "package_sha256": packet["package"]["sha256"],
               "contract_sha256": CONTRACT_SHA256, "authorized": True, "relation_decision": "",
               "relation_type": content["relation_type"], "from_ref": content["from_ref"], "to_ref": content["to_ref"],
               "advisory_disposition": content["raw"].get("disposition"), "original_advisory_reason": content["raw"].get("reason")}
        row["link_candidate_id"] = deterministic_id("NATIVE_EVIDENCE_AUTH", row)
        body["relation_native_authorizations"].append(row)
    for spec in adjudications:
        content = claims[spec["claim_id"]]["content"]
        require(spec["source_id"] == content["source_id"] and spec["source_sha256"] == content["source_sha256"] == sources[spec["source_id"]], "ADJUDICATION_SOURCE_MISMATCH")
        selected = spec["authoritative_evidence_id"]
        require(selected in {e["evidence_id"] for e in content["evidence"]}, "ADJUDICATED_EVIDENCE_NOT_A_CANDIDATE")
        require(set(spec["sibling_evidence_ids"]) == {e["evidence_id"] for e in content["evidence"]} - {selected}, "ADJUDICATION_SIBLING_OMISSION")
        row = {**copy.deepcopy(spec), "authority_type": "EXPLICIT_HUMAN_SEMANTIC_ADJUDICATION", "human_content_decision": "",
               "native_claim_sha256": canonical_sha256(content["raw"]), "original_content_sha256": claims[spec["claim_id"]]["content_sha256"],
               "original_qualification_diagnostics": copy.deepcopy(content["qualification_diagnostics"]),
               "evidence_bindings": [{"evidence_id": eid, "evidence_sha256": canonical_sha256(evidence_by_id[eid])}
                                     for eid in sorted([selected, *spec["sibling_evidence_ids"]])]}
        body["claim_evidence_adjudications"].append(row)
    body["relation_native_authorizations"].sort(key=lambda r: (r["relation_candidate_id"], r["evidence_id"], r["role"]))
    body["claim_evidence_adjudications"].sort(key=lambda r: r["claim_id"])
    mid = deterministic_id("FOUNDATION_GOVERNANCE", body)
    for row in body["relation_native_authorizations"] + body["claim_evidence_adjudications"]:
        row["human_authorization_manifest_id"] = mid
    body["manifest_id"] = mid
    result = {**body, "manifest_sha256": canonical_sha256(body)}
    validate_manifest(result, packet["package"]["sha256"])
    return result


def native_authorizations(record, manifest, registry):
    validate_manifest(manifest, manifest["package_sha256"])
    rows = [r for r in manifest["relation_native_authorizations"] if r["relation_candidate_id"] == record["candidate_id"]]
    sources = {r["source_id"]: r["expected_sha256"] for r in registry["sources"]}
    c = record["content"]
    for row in rows:
        require(row["native_relation_sha256"] == canonical_sha256(c["raw"]), "NATIVE_RELATION_IDENTITY_DRIFT")
        require(row["scope"] == c["scope"] and row["temporal_status"] == c["raw"]["temporal_status"], "NATIVE_SCOPE_MISMATCH")
        require(all(row[k] == c[k] for k in ("relation_type", "from_ref", "to_ref")), "NATIVE_RELATION_PROJECTION_DRIFT")
        require(row["evidence_id"] in c["evidence_refs"], "NATIVE_EVIDENCE_NOT_IN_ORIGINAL_RELATION")
        require(row["source_sha256"] == sources.get(row["source_id"]), "NATIVE_SOURCE_SHA_MISMATCH")
    return copy.deepcopy(rows)


def adjudicated_claim_content(record, manifest):
    """Resolve identity only, and independently recheck non-identity qualification."""
    validate_manifest(manifest, manifest["package_sha256"])
    content = copy.deepcopy(record["content"])
    matches = [a for a in manifest["claim_evidence_adjudications"] if a["claim_id"] == record["candidate_id"]]
    if not matches:
        return content
    adjudication = matches[0]
    require(canonical_sha256(content["raw"]) == adjudication["native_claim_sha256"], "ADJUDICATION_CLAIM_DRIFT")
    require(content["qualification_diagnostics"] == adjudication["original_qualification_diagnostics"], "ADJUDICATION_DIAGNOSTICS_DRIFT")
    require(content["qualification_diagnostics"]["qualification_reason"] == "EVIDENCE_RECORD_IDENTITY_AMBIGUOUS", "ADJUDICATION_DOES_NOT_RESOLVE_THIS_EXCEPTION")
    evidence = content["evidence"]
    for binding in adjudication["evidence_bindings"]:
        e = next(e for e in evidence if e["evidence_id"] == binding["evidence_id"])
        require(canonical_sha256({k: v for k, v in e.items() if k != "source_sha256"}) == binding["evidence_sha256"], "ADJUDICATION_EVIDENCE_DRIFT")
        require(e["source_id"] == content["source_id"] and e["source_sha256"] == content["source_sha256"], "ADJUDICATION_CROSS_SOURCE")
        require(e["evidence_excerpt"] == content["raw"]["evidence_excerpt"] and
                f'{e["source_id"]} PDF p.{e["pdf_page"]}, {e["section"]}' == content["raw"]["evidence_locator"], "ADJUDICATION_LOCATOR_OR_EXCERPT_MISMATCH")
    diag = copy.deepcopy(content["qualification_diagnostics"])
    require(all(diag[k] for k in ("source_identity_exists", "source_reference_unique", "evidence_belongs_to_claimed_source", "evidence_locator_present", "evidence_excerpt_present")), "ADJUDICATION_INDEPENDENT_QUALIFICATION_ISSUE")
    dates = [content["raw"].get(k) for k in ("fact_time", "publication_time")]
    try:
        for value in dates:
            if value:
                require(date.fromisoformat(value).isoformat() == value, "ADJUDICATION_INVALID_TIME")
    except (ValueError, TypeError):
        raise PromotionError("ADJUDICATION_INVALID_TIME") from None
    require(any(dates) and diag["mapped_nature"] == content["row"]["nature"], "ADJUDICATION_INDEPENDENT_TEMPORAL_OR_NATURE_ISSUE")
    selected = adjudication["authoritative_evidence_id"]
    content["evidence"] = [e for e in evidence if e["evidence_id"] == selected]
    content["sibling_evidence"] = [e for e in evidence if e["evidence_id"] != selected]
    diag.update(evidence_match_ids=[selected], evidence_reference_unique=True,
                qualification_reason="EXPLICIT_HUMAN_EVIDENCE_IDENTITY_ADJUDICATED",
                compatibility="CLAIM_COMPATIBLE_WITH_DETERMINISTIC_FIELD_MAPPING", temporal_classification="TEMPORAL_CLAIM_VALID")
    content.update(qualification_diagnostics=diag, qualification_status="DETERMINISTICALLY_MAPPABLE",
                   evidence_identity_adjudication=copy.deepcopy(adjudication))
    structured = json.loads(content["row"]["structured_json"])
    structured["evidence_identity_adjudication"] = copy.deepcopy(adjudication)
    structured["sibling_evidence"] = content["sibling_evidence"]
    content["row"]["structured_json"] = json.dumps(structured, ensure_ascii=False, sort_keys=True)
    return content
