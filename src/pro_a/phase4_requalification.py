"""Acceptance-only authorization for one failed Source's bound requalification.

This does not change the ordinary duplicate audit or the ingestion runtime.
The caller must audit the complete formal namespace and consume the grant once.
"""

import json
from pathlib import Path

from .production_promotion import sha256_file


STAGE = "GATE_B_RETRY_2"
GATE_C_STAGE = "GATE_C_RETRY_1"
GATE_C_FINAL_STAGE = "GATE_C_RETRY_2"
PURPOSE = "LIVE_PROVENANCE_REMEDIATION_REQUALIFICATION"


def assess_same_source_requalification(audit, authorization, source_sha256, namespace):
    """Fail closed unless every matching history row is the bound prior EXEC."""
    if isinstance(authorization, dict) and authorization.get("stage") == GATE_C_FINAL_STAGE:
        return _assess_final_gate_c(audit, authorization, source_sha256, namespace)
    errors = []
    authorized, unrelated = [], list(audit["historical_matches"])
    try:
        grant = authorization
        assert grant["mode"] == "SAME_SOURCE_REQUALIFICATION"
        assert grant["stage"] in {STAGE, GATE_C_STAGE} and grant["purpose"] == PURPOSE
        assert grant["authorized"] is True and grant["maximum_new_executions"] == 1
        assert grant["source_sha256"] == source_sha256
        prior = Path(namespace).resolve() / grant["prior_execution_id"]
        assert prior.parent == Path(namespace).resolve() and prior.name.startswith("EXEC_")
        identity_path = prior / "execution_identity.json"
        assert sha256_file(identity_path) == grant["prior_identity_sha256"]
        identity = json.loads(identity_path.read_bytes())
        assert identity["execution_id"] == grant["prior_execution_id"]
        assert identity["source_sha256"] == source_sha256
        assert identity["mode"] == "CONFIGURED_PROVIDER"
        evidence = []
        for key in ("prior_acceptance", "remediation_evidence", "remediation_report"):
            path = Path(grant[key]["path"])
            assert sha256_file(path) == grant[key]["sha256"]
            if key != "remediation_report":
                evidence.append(json.loads(path.read_bytes()))
        failed, remediated = evidence
        result = failed["results"]
        assert result["GATE_B_RETRY1_RESULT" if grant["stage"] == STAGE else "GATE_C_RESULT"] == "FAIL"
        assert result["PRIMARY_FAILURE_CATEGORY"] == "EVIDENCE_FAILURE"
        assert result["EXECUTION_ID"] == identity["execution_id"]
        assert result["SOURCE_SHA256"] == source_sha256
        if grant["stage"] == STAGE:
            assert remediated["results"]["REMEDIATION_RESULT"] == "PASS"
            assert remediated["original_retry1_packet"] == failed["live_result"]["packet_id"]
        else:
            assert remediated["PHASE4_STAGE41_GATE_C_EVIDENCE_REMEDIATION_COMPLETE"] is True
            assert remediated["REMEDIATION_RESULT"] == "PASS"
            assert remediated["SOURCE_SHA256"] == source_sha256
            assert remediated["BROKEN_PROVENANCE_EDGES_AFTER_REPLAY"] == 0
            assert remediated["SEMANTIC_POLICY_CHANGED"] == "NO"
            bound = {}
            for key in ("remediation_qualification", "remediation_inventory"):
                path = Path(grant[key]["path"])
                assert sha256_file(path) == grant[key]["sha256"]
                bound[key] = json.loads(path.read_bytes())
            qualification = bound["remediation_qualification"]
            assert qualification["status"] == "PASS" and qualification["broken_provenance_edges"] == 0
            assert Path(qualification["original_execution_root"]).resolve() == prior
            assert qualification["source_sha256"] == source_sha256
            assert Path(qualification["execution_root"]).name == remediated["FINAL_GATE_C_REPLAY_EXECUTION"]
            assert qualification["frozen_extraction_unchanged"] is True
            assert qualification["frozen_semantic_output_unchanged"] is True
            code = grant["remediation_code_identity"]
            assert set(code) == {"src/pro_a/corpus_pilot.py", "src/pro_a/operational_ingestion.py",
                                 "src/pro_a/table_claim_safety.py"}
            root = Path(__file__).resolve().parents[2]
            for name, digest in code.items():
                assert bound["remediation_inventory"][name] == digest == sha256_file(root / name)
        allowed = {identity_path.resolve(), (prior / "engine/run_manifest.json").resolve()}
        authorized = [r for r in unrelated if Path(r["artifact"]).resolve() in allowed]
        unrelated = [r for r in unrelated if Path(r["artifact"]).resolve() not in allowed]
        assert authorized, "NO_AUTHORIZED_PRIOR_EXECUTION_MATCH"
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"INVALID_REQUALIFICATION_BINDING:{type(exc).__name__}:{exc}")
    passed = (not errors and audit["authoritative_source_universe_complete"]
              and not audit["production_matches"] and not unrelated)
    return {"guard": "PASS" if passed else "FAIL",
            "stage": authorization.get("stage") if isinstance(authorization, dict) else None,
            "production_duplicate_count": len(audit["production_matches"]),
            "unrelated_authoritative_history_duplicate_count": len(unrelated),
            "authorized_prior_phase4_execution_match_count": len(authorized),
            "authorized_matches": authorized, "unrelated_matches": unrelated,
            "ordinary_duplicate_check": audit["duplicate_check"], "errors": errors}


def _assess_final_gate_c(audit, grant, source_sha256, namespace):
    """Bind the final retry to exactly two failed EXECs and both qualified repairs."""
    from .phase4_orchestration import _runtime

    errors, authorized = [], []
    unrelated = list(audit["historical_matches"])
    namespace = Path(namespace).resolve()
    root = Path(__file__).resolve().parents[2]

    def bound(spec):
        path = Path(spec["path"])
        assert sha256_file(path) == spec["sha256"]
        return json.loads(path.read_bytes()) if path.suffix == ".json" else None

    try:
        assert grant["mode"] == "SAME_SOURCE_REQUALIFICATION" and grant["purpose"] == PURPOSE
        assert grant["authorized"] is True and grant["maximum_new_executions"] == 1
        assert grant["final_gate_c_live_retry"] is True and grant["source_sha256"] == source_sha256
        assert set(grant["prior_executions"]) == {"original", "retry1"}
        priors, allowed = {}, set()
        for role, result_key in (("original", "GATE_C_RESULT"), ("retry1", "GATE_C_RETRY1_RESULT")):
            spec = grant["prior_executions"][role]
            prior = (namespace / spec["execution_id"]).resolve()
            assert prior.parent == namespace and prior.name.startswith("EXEC_")
            identity_path = prior / "execution_identity.json"
            assert sha256_file(identity_path) == spec["identity_sha256"]
            identity = json.loads(identity_path.read_bytes())
            assert identity["execution_id"] == prior.name and identity["source_sha256"] == source_sha256
            assert identity["mode"] == "CONFIGURED_PROVIDER"
            failed = bound(spec["acceptance"])["results"]
            assert failed[result_key] == "FAIL" and failed["PRIMARY_FAILURE_CATEGORY"] == "EVIDENCE_FAILURE"
            assert failed["EXECUTION_ID"] == prior.name and failed["SOURCE_SHA256"] == source_sha256
            paths = {identity_path.resolve(), (prior / "engine/run_manifest.json").resolve()}
            assert any(Path(row["artifact"]).resolve() in paths for row in unrelated)
            allowed.update(paths)
            priors[role] = prior
        assert priors["original"] != priors["retry1"]
        repairs = {}
        for role in ("claim", "node"):
            spec = grant["remediations"][role]
            repairs[role] = {key: bound(spec[key]) for key in ("evidence", "qualification", "inventory", "report")}
            evidence, qualification = repairs[role]["evidence"], repairs[role]["qualification"]
            assert evidence["REMEDIATION_RESULT"] == "PASS" and evidence["SEMANTIC_POLICY_CHANGED"] == "NO"
            assert evidence["BROKEN_PROVENANCE_EDGES_AFTER_REPLAY"] == 0
            assert qualification["status"] == "PASS" and qualification["broken_provenance_edges"] == 0
        claim, cq = repairs["claim"]["evidence"], repairs["claim"]["qualification"]
        assert claim["PHASE4_STAGE41_GATE_C_EVIDENCE_REMEDIATION_COMPLETE"] is True
        assert claim["SOURCE_SHA256"] == cq["source_sha256"] == source_sha256
        assert Path(cq["original_execution_root"]).resolve() == priors["original"]
        assert Path(cq["execution_root"]).name == claim["FINAL_GATE_C_REPLAY_EXECUTION"]
        assert cq["frozen_extraction_unchanged"] is True and cq["frozen_semantic_output_unchanged"] is True
        node, nq = repairs["node"]["evidence"], repairs["node"]["qualification"]
        assert node["PHASE4_STAGE41_GATE_C_NODE_PROVENANCE_BOUNDARY_REMEDIATION_COMPLETE"] is True
        assert node["DIRECT_EVIDENCE_NODE_AUTHORITY"] == "NOT_ALLOWED"
        assert node["GENERIC_NODE_PROVENANCE_GATE"] == node["DEFER_DOES_NOT_BYPASS_PROVENANCE"] == "PASS"
        assert Path(nq["donor_root"]).resolve() == priors["retry1"]
        assert Path(node["replays"]["gate_c_retry1"]["replay_root"]).resolve() == Path(nq["replay_root"]).resolve()
        assert nq["retained_node_records_unchanged"] is True and nq["no_hidden_drops"] is True
        assert nq["claim_proofs"] and all(p["authoritative"] and p["source_sha256"] == source_sha256 for p in nq["claim_proofs"])
        assert node["new_runtime"] == _runtime()
        assert {"src/pro_a/production_authorization.py", "src/pro_a/operational_ingestion.py"} <= node["code_file_sha256"].keys()
        for name, digest in node["code_file_sha256"].items():
            assert repairs["node"]["inventory"]["sha256"][name] == digest == sha256_file(root / name)
        # The latest qualified Node repair supersedes the older ingestion hash;
        # unchanged Claim-evidence mechanics must still match their own seal.
        for name in ("src/pro_a/corpus_pilot.py", "src/pro_a/table_claim_safety.py"):
            assert repairs["claim"]["inventory"][name] == sha256_file(root / name)
        authorized = [r for r in unrelated if Path(r["artifact"]).resolve() in allowed]
        unrelated = [r for r in unrelated if Path(r["artifact"]).resolve() not in allowed]
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"INVALID_REQUALIFICATION_BINDING:{type(exc).__name__}:{exc}")
    passed = not errors and audit["authoritative_source_universe_complete"] and not audit["production_matches"] and not unrelated
    return {"guard": "PASS" if passed else "FAIL", "stage": grant["stage"],
            "production_duplicate_count": len(audit["production_matches"]),
            "unrelated_authoritative_history_duplicate_count": len(unrelated),
            "authorized_prior_phase4_execution_match_count": len(authorized),
            "authorized_prior_execution_count": 2 if passed else 0,
            "authorized_matches": authorized, "unrelated_matches": unrelated,
            "ordinary_duplicate_check": audit["duplicate_check"], "errors": errors}
