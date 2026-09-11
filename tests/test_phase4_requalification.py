import copy
import json

import pytest

from pro_a.phase4_requalification import assess_same_source_requalification, PURPOSE, STAGE
from pro_a.production_promotion import sha256_file


@pytest.fixture
def case(tmp_path):
    sha = "a" * 64
    namespace = tmp_path / "executions"
    prior = namespace / "EXEC_TEST"
    prior.mkdir(parents=True)
    def write(path, data):
        path.write_text(json.dumps(data), encoding="utf-8")
        return {"path": str(path), "sha256": sha256_file(path)}
    identity = write(prior / "execution_identity.json", {
        "execution_id": prior.name, "source_sha256": sha, "mode": "CONFIGURED_PROVIDER"})
    failed = write(tmp_path / "failed.json", {"results": {
        "GATE_B_RETRY1_RESULT": "FAIL", "PRIMARY_FAILURE_CATEGORY": "EVIDENCE_FAILURE",
        "EXECUTION_ID": prior.name, "SOURCE_SHA256": sha}, "live_result": {"packet_id": "PACKET_OLD"}})
    remediation = write(tmp_path / "remediation.json", {
        "results": {"REMEDIATION_RESULT": "PASS"}, "original_retry1_packet": "PACKET_OLD"})
    report = write(tmp_path / "report.md", "Independent remediation report")
    grant = {"mode": "SAME_SOURCE_REQUALIFICATION", "stage": STAGE, "purpose": PURPOSE,
             "authorized": True, "maximum_new_executions": 1, "source_sha256": sha,
             "prior_execution_id": prior.name, "prior_identity_sha256": identity["sha256"],
             "prior_acceptance": failed, "remediation_evidence": remediation,
             "remediation_report": report}
    audit = {"authoritative_source_universe_complete": True, "duplicate_check": "FAIL",
             "production_matches": [], "historical_matches": [{"artifact": identity["path"], "source_sha256": sha}]}
    return audit, grant, sha, namespace


def test_exact_failed_execution_is_allowed_without_changing_ordinary_audit(case):
    audit, grant, sha, namespace = case
    before = copy.deepcopy(audit)
    result = assess_same_source_requalification(*case)
    assert result["guard"] == "PASS"
    assert result["authorized_prior_phase4_execution_match_count"] == 1
    assert audit == before and audit["duplicate_check"] == "FAIL"


@pytest.mark.parametrize("key,value", [
    ("mode", "IGNORE_DUPLICATES"), ("stage", "GATE_C"), ("purpose", "ordinary ingestion"),
    ("authorized", False), ("maximum_new_executions", 2), ("source_sha256", "b" * 64),
    ("prior_execution_id", "EXEC_OTHER"), ("prior_execution_id", "../EXEC_TEST"),
    ("prior_identity_sha256", "0" * 64),
])
def test_mismatched_binding_is_blocked(case, key, value):
    case[1][key] = value
    assert assess_same_source_requalification(*case)["guard"] == "FAIL"


@pytest.mark.parametrize("kind", ["production", "unrelated", "incomplete", "absent_prior"])
def test_other_duplicates_and_incomplete_audits_remain_blockers(case, kind):
    audit = case[0]
    if kind == "production":
        audit["production_matches"].append({"source_sha256": case[2]})
    elif kind == "unrelated":
        audit["historical_matches"].append({"artifact": str(case[3] / "EXEC_OTHER/execution_identity.json")})
    elif kind == "incomplete":
        audit["authoritative_source_universe_complete"] = False
    else:
        audit["historical_matches"] = []
    assert assess_same_source_requalification(*case)["guard"] == "FAIL"


@pytest.mark.parametrize("key", ["prior_acceptance", "remediation_evidence", "remediation_report"])
def test_changed_evidence_is_blocked(case, key):
    case[1][key]["sha256"] = "0" * 64
    assert assess_same_source_requalification(*case)["guard"] == "FAIL"


def test_prior_success_is_not_authorized_even_with_a_fresh_hash(case):
    from pathlib import Path
    spec = case[1]["prior_acceptance"]
    path = Path(spec["path"])
    data = json.loads(path.read_bytes())
    data["results"]["GATE_B_RETRY1_RESULT"] = "PASS"
    path.write_text(json.dumps(data), encoding="utf-8")
    spec["sha256"] = sha256_file(path)
    assert assess_same_source_requalification(*case)["guard"] == "FAIL"
