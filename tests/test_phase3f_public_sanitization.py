from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pro_a.phase3f_public_sanitization import write_public_audit
from pro_a.production_promotion import canonical_sha256, sha256_file


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "workspace" / "phase3f_stage1_public_audit"
REVIEW_PACKET = (
    ROOT
    / "workspace"
    / "phase3f_stage1_review_completion"
    / "operational_review_packet.json"
)
QUALIFICATION_ROOT = ROOT / "workspace" / "phase3f_stage1_qualification_review"
HANDOFF_ROOT = ROOT / "workspace" / "phase3f_stage1_handoff_requalification"
BANNED_KEYS = {
    "statement",
    "evidence_excerpt",
    "human_reason",
    "immutable_claim",
    "supporting_evidence",
    "original_name",
    "title",
    "summary",
    "row",
    "reason",
}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value):
    if isinstance(value, dict):
        yield from value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_persisted_public_audit_is_hash_bound_and_source_text_free() -> None:
    paths = sorted(PUBLIC_ROOT.glob("*.json"))
    assert [path.name for path in paths] == [
        "handoff_requalification_public_audit.json",
        "operational_review_public_audit.json",
        "public_audit_manifest.json",
        "qualification_review_public_audit.json",
    ]
    for path in paths:
        artifact = _read(path)
        body = {
            key: value
            for key, value in artifact.items()
            if key not in {"artifact_id", "artifact_sha256"}
        }
        digest = canonical_sha256(body)
        assert artifact["artifact_sha256"] == digest
        assert artifact["artifact_id"].endswith(digest[:16].upper())
        assert artifact["source_text_included"] is False
        assert not (set(_walk(artifact)) & BANNED_KEYS)
        assert re.search(r"[\u3400-\u9fff]", json.dumps(artifact, ensure_ascii=False)) is None

    review = _read(PUBLIC_ROOT / "operational_review_public_audit.json")
    assert review["counts"]["total_operational_decisions_required"] == 205
    qualification = _read(PUBLIC_ROOT / "qualification_review_public_audit.json")
    decisions = {
        item["candidate_id"]: item["decision"]
        for group in qualification["records"].values()
        for item in group
    }
    assert decisions == {
        "CLM_07152FCFBF4C3D1B": "KEEP",
        "CLM_74B65D5D09781B64": "KEEP_NEEDS_REVIEW",
        "CLM_229114C7C3F70FE9": "DROP",
        "CAND_NODE_E8A75C771486B74E": "CREATE",
        "CAND_NODE_E7C5A8860931121D": "REUSE",
        "CAND_NODE_757A9745164C0433": "DEFER",
        "PARENT_PLACEMENT_67ADDE309C1A5CAB": "CREATE",
    }
    handoff = _read(PUBLIC_ROOT / "handoff_requalification_public_audit.json")
    assert handoff["phase3d_validation"]["status"] == "PASS"
    assert handoff["stage1_requalification_receipt"]["production_changed"] is False
    assert handoff["phase3f_stage2_started"] is False


@pytest.mark.skipif(
    not all(
        path.is_file()
        for path in (
            REVIEW_PACKET,
            QUALIFICATION_ROOT / "qualification_review_packet.completed.json",
            HANDOFF_ROOT / "qualification_promotion_candidate.json",
        )
    ),
    reason="local evidence-bearing inputs are intentionally untracked",
)
def test_public_audit_regeneration_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    arguments = {
        "repository_root": ROOT,
        "review_packet_path": REVIEW_PACKET,
        "qualification_root": QUALIFICATION_ROOT,
        "handoff_root": HANDOFF_ROOT,
    }
    left = write_public_audit(output_dir=first, **arguments)
    right = write_public_audit(output_dir=second, **arguments)
    assert left == right
    assert {
        path.name: sha256_file(path) for path in first.glob("*.json")
    } == {
        path.name: sha256_file(path) for path in second.glob("*.json")
    }
