"""The final Gate C grant cannot become a generic same-source bypass."""
import copy
import json
from pathlib import Path

import pytest

from pro_a.phase4_orchestration import _runtime
from pro_a.phase4_requalification import GATE_C_FINAL_STAGE, PURPOSE, assess_same_source_requalification
from pro_a.production_promotion import sha256_file


@pytest.fixture
def final_case(tmp_path):
    root = Path(__file__).resolve().parents[1]
    namespace = tmp_path / "executions"
    sha = "a" * 64
    def bind(name, data):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return {"path": str(path), "sha256": sha256_file(path)}
    grant = {"mode": "SAME_SOURCE_REQUALIFICATION", "stage": GATE_C_FINAL_STAGE, "purpose": PURPOSE,
             "authorized": True, "maximum_new_executions": 1, "final_gate_c_live_retry": True,
             "source_sha256": sha, "prior_executions": {}, "remediations": {}}
    audit = {"authoritative_source_universe_complete": True, "duplicate_check": "FAIL",
             "production_matches": [], "historical_matches": []}
    for role, key in (("original", "GATE_C_RESULT"), ("retry1", "GATE_C_RETRY1_RESULT")):
        eid = "EXEC_" + role.upper()
        identity = bind(f"executions/{eid}/execution_identity.json", {"execution_id": eid,
                        "source_sha256": sha, "mode": "CONFIGURED_PROVIDER"})
        grant["prior_executions"][role] = {"execution_id": eid, "identity_sha256": identity["sha256"],
            "acceptance": bind(role + "_failure.json", {"results": {key: "FAIL",
                "PRIMARY_FAILURE_CATEGORY": "EVIDENCE_FAILURE", "EXECUTION_ID": eid, "SOURCE_SHA256": sha}})}
        audit["historical_matches"].append({"artifact": identity["path"], "source_sha256": sha})
    claim_code = {"src/pro_a/" + n + ".py": sha256_file(root / "src/pro_a" / (n + ".py"))
                  for n in ("corpus_pilot", "table_claim_safety")}
    node_code = {"src/pro_a/" + n + ".py": sha256_file(root / "src/pro_a" / (n + ".py"))
                 for n in ("production_authorization", "operational_ingestion")}
    claim = {"PHASE4_STAGE41_GATE_C_EVIDENCE_REMEDIATION_COMPLETE": True, "REMEDIATION_RESULT": "PASS",
             "SEMANTIC_POLICY_CHANGED": "NO", "BROKEN_PROVENANCE_EDGES_AFTER_REPLAY": 0,
             "SOURCE_SHA256": sha, "FINAL_GATE_C_REPLAY_EXECUTION": "EXEC_CLAIM_OFFLINE"}
    cq = {"status": "PASS", "broken_provenance_edges": 0, "source_sha256": sha,
          "original_execution_root": str(namespace / "EXEC_ORIGINAL"),
          "execution_root": str(tmp_path / "EXEC_CLAIM_OFFLINE"),
          "frozen_extraction_unchanged": True, "frozen_semantic_output_unchanged": True}
    node = {"PHASE4_STAGE41_GATE_C_NODE_PROVENANCE_BOUNDARY_REMEDIATION_COMPLETE": True,
            "REMEDIATION_RESULT": "PASS", "SEMANTIC_POLICY_CHANGED": "NO", "BROKEN_PROVENANCE_EDGES_AFTER_REPLAY": 0,
            "DIRECT_EVIDENCE_NODE_AUTHORITY": "NOT_ALLOWED", "GENERIC_NODE_PROVENANCE_GATE": "PASS",
            "DEFER_DOES_NOT_BYPASS_PROVENANCE": "PASS", "new_runtime": _runtime(), "code_file_sha256": node_code,
            "replays": {"gate_c_retry1": {"replay_root": str(tmp_path / "node_offline")}}}
    nq = {"status": "PASS", "broken_provenance_edges": 0, "donor_root": str(namespace / "EXEC_RETRY1"),
          "replay_root": str(tmp_path / "node_offline"), "retained_node_records_unchanged": True,
          "no_hidden_drops": True, "claim_proofs": [{"authoritative": True, "source_sha256": sha}]}
    for role, evidence, qualification, inventory in (("claim", claim, cq, claim_code),
                                                   ("node", node, nq, {"sha256": node_code})):
        grant["remediations"][role] = {"evidence": bind(role + ".json", evidence),
            "qualification": bind(role + "_qualification.json", qualification),
            "inventory": bind(role + "_inventory.json", inventory), "report": bind(role + ".md", "frozen report")}
    return audit, grant, sha, namespace


def test_two_exact_failed_execs_and_both_qualified_repairs_are_required(final_case):
    before = copy.deepcopy(final_case)
    result = assess_same_source_requalification(*final_case)
    assert result["guard"] == "PASS" and result["authorized_prior_execution_count"] == 2
    assert result["authorized_prior_phase4_execution_match_count"] == 2
    assert final_case == before and final_case[0]["duplicate_check"] == "FAIL"


@pytest.mark.parametrize("defect", ["production", "unrelated", "incomplete", "missing_original_match",
                                  "missing_retry1", "third_prior", "two_new_execs", "not_final", "wrong_source", "escape"])
def test_final_grant_remains_narrow(final_case, defect):
    audit, grant, _, _ = final_case
    if defect == "production": audit["production_matches"].append({})
    elif defect == "unrelated": audit["historical_matches"].append({"artifact": "unrelated.json"})
    elif defect == "incomplete": audit["authoritative_source_universe_complete"] = False
    elif defect == "missing_original_match": audit["historical_matches"].pop(0)
    elif defect == "missing_retry1": grant["prior_executions"].pop("retry1")
    elif defect == "third_prior": grant["prior_executions"]["third"] = {}
    elif defect == "two_new_execs": grant["maximum_new_executions"] = 2
    elif defect == "not_final": grant["final_gate_c_live_retry"] = False
    elif defect == "wrong_source": grant["source_sha256"] = "b" * 64
    else: grant["prior_executions"]["original"]["execution_id"] = "../EXEC_ORIGINAL"
    assert assess_same_source_requalification(*final_case)["guard"] == "FAIL"


@pytest.mark.parametrize("role,key", [(r, k) for r in ("claim", "node")
                                      for k in ("evidence", "qualification", "inventory", "report")])
def test_final_grant_rejects_changed_artifact_bytes(final_case, role, key):
    final_case[1]["remediations"][role][key]["sha256"] = "0" * 64
    assert assess_same_source_requalification(*final_case)["guard"] == "FAIL"


@pytest.mark.parametrize("role,key,field,value", [
    ("claim", "evidence", "REMEDIATION_RESULT", "FAIL"),
    ("claim", "qualification", "source_sha256", "b" * 64),
    ("claim", "qualification", "original_execution_root", "OTHER"),
    ("claim", "qualification", "frozen_semantic_output_unchanged", False),
    ("node", "evidence", "DIRECT_EVIDENCE_NODE_AUTHORITY", "ALLOWED"),
    ("node", "evidence", "DEFER_DOES_NOT_BYPASS_PROVENANCE", "FAIL"),
    ("node", "evidence", "new_runtime", {}),
    ("node", "qualification", "donor_root", "OTHER"),
    ("node", "qualification", "no_hidden_drops", False),
    ("node", "qualification", "claim_proofs", []),
])
def test_invalid_lineage_is_not_repaired_by_rehashing(final_case, role, key, field, value):
    spec = final_case[1]["remediations"][role][key]
    path = Path(spec["path"]); data = json.loads(path.read_bytes()); data[field] = value
    path.write_text(json.dumps(data), encoding="utf-8"); spec["sha256"] = sha256_file(path)
    assert assess_same_source_requalification(*final_case)["guard"] == "FAIL"
