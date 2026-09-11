import json
from pathlib import Path

import pytest

from pro_a.phase4_requalification import GATE_C_STAGE, assess_same_source_requalification
from pro_a.production_promotion import sha256_file
from test_phase4_requalification import case


@pytest.fixture
def gate_c_case(case, tmp_path):
    audit, grant, sha, namespace = case
    def write(name, data):
        path = tmp_path / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return {"path": str(path), "sha256": sha256_file(path)}
    grant["stage"] = GATE_C_STAGE
    grant["prior_acceptance"] = write("failed_c.json", {"results": {
        "GATE_C_RESULT": "FAIL", "PRIMARY_FAILURE_CATEGORY": "EVIDENCE_FAILURE",
        "EXECUTION_ID": "EXEC_TEST", "SOURCE_SHA256": sha}})
    grant["remediation_evidence"] = write("remediated_c.json", {
        "PHASE4_STAGE41_GATE_C_EVIDENCE_REMEDIATION_COMPLETE": True, "REMEDIATION_RESULT": "PASS",
        "SOURCE_SHA256": sha, "BROKEN_PROVENANCE_EDGES_AFTER_REPLAY": 0,
        "SEMANTIC_POLICY_CHANGED": "NO", "FINAL_GATE_C_REPLAY_EXECUTION": "EXEC_OFFLINE"})
    grant["remediation_qualification"] = write("qualified_c.json", {
        "status": "PASS", "broken_provenance_edges": 0, "source_sha256": sha,
        "original_execution_root": str(namespace / "EXEC_TEST"), "execution_root": str(tmp_path / "EXEC_OFFLINE"),
        "frozen_extraction_unchanged": True, "frozen_semantic_output_unchanged": True})
    root = Path(__file__).resolve().parents[1]
    code = {f"src/pro_a/{name}.py": sha256_file(root / f"src/pro_a/{name}.py")
            for name in ("corpus_pilot", "operational_ingestion", "table_claim_safety")}
    grant["remediation_code_identity"] = code
    grant["remediation_inventory"] = write("inventory_c.json", code)
    return case


def test_gate_c_exact_lineage_and_current_code_pass(gate_c_case):
    result = assess_same_source_requalification(*gate_c_case)
    assert result["guard"] == "PASS" and result["stage"] == GATE_C_STAGE
    assert gate_c_case[0]["duplicate_check"] == "FAIL"


@pytest.mark.parametrize("grant", [None, [], "invalid"])
def test_malformed_authorization_fails_closed(gate_c_case, grant):
    audit, _, sha, namespace = gate_c_case
    assert assess_same_source_requalification(audit, grant, sha, namespace)["guard"] == "FAIL"


@pytest.mark.parametrize("binding,field,value", [
    ("prior_acceptance", "GATE_C_RESULT", "PASS"),
    ("prior_acceptance", "EXECUTION_ID", "EXEC_OTHER"),
    ("remediation_evidence", "SOURCE_SHA256", "b" * 64),
    ("remediation_evidence", "REMEDIATION_RESULT", "FAIL"),
    ("remediation_evidence", "SEMANTIC_POLICY_CHANGED", "YES"),
    ("remediation_evidence", "BROKEN_PROVENANCE_EDGES_AFTER_REPLAY", 1),
    ("remediation_qualification", "original_execution_root", "EXEC_OTHER"),
    ("remediation_qualification", "frozen_semantic_output_unchanged", False),
    ("remediation_qualification", "execution_root", "EXEC_OTHER"),
])
def test_gate_c_rejects_invalid_lineage_even_with_fresh_digest(gate_c_case, binding, field, value):
    spec = gate_c_case[1][binding]
    path = Path(spec["path"])
    data = json.loads(path.read_bytes())
    (data["results"] if binding == "prior_acceptance" else data)[field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    spec["sha256"] = sha256_file(path)
    assert assess_same_source_requalification(*gate_c_case)["guard"] == "FAIL"


@pytest.mark.parametrize("kind", ["wrong_code", "missing_code", "changed_inventory", "production",
                                  "unrelated", "incomplete", "wrong_stage", "second_execution"])
def test_gate_c_cannot_bypass_duplicate_or_code_guards(gate_c_case, kind):
    audit, grant, _, namespace = gate_c_case
    if kind == "wrong_code":
        grant["remediation_code_identity"]["src/pro_a/corpus_pilot.py"] = "0" * 64
    elif kind == "missing_code":
        grant["remediation_code_identity"].pop("src/pro_a/corpus_pilot.py")
    elif kind == "changed_inventory":
        grant["remediation_inventory"]["sha256"] = "0" * 64
    elif kind == "production":
        audit["production_matches"].append({})
    elif kind == "unrelated":
        audit["historical_matches"].append({"artifact": str(namespace / "EXEC_OTHER/execution_identity.json")})
    elif kind == "incomplete":
        audit["authoritative_source_universe_complete"] = False
    elif kind == "wrong_stage":
        grant["stage"] = "GATE_C_RETRY_2"
    else:
        grant["maximum_new_executions"] = 2
    assert assess_same_source_requalification(*gate_c_case)["guard"] == "FAIL"
