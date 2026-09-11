"""Consume an exact frozen semantic result, without another model generation."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from .production_promotion import sha256_file
from .semantic_decomposition import build_semantic_claim_inputs


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_ARTIFACT_NOT_OBJECT:{path.name}")
    return value


def frozen_replay_inputs(run_root: Path) -> dict:
    """Read only inventory-bound inputs; never repair or rewrite a historical run."""
    manifest = read_json(run_root / "run_manifest.json")
    if (manifest.get("document_type") != "phase3e_operational_ingestion_manifest"
            or manifest.get("schema_version") != "1"
            or manifest.get("stage_status") != "HUMAN_REVIEW_REQUIRED"):
        raise ValueError("REPLAY_RUN_NOT_COMPLETE")
    inventory = {row["path"]: row["sha256"] for row in manifest["artifact_inventory"]}
    names = ("extraction/extraction_bundle.json",
             "evidence/evidence_bound_extraction_bundle.json",
             "evidence/evidence_binding.json", "evidence/quote_fidelity.json",
             "evidence/semantic_decomposition.json")
    artifacts = {}
    for name in names:
        path = run_root / name
        if inventory.get(name) != sha256_file(path):
            raise ValueError(f"REPLAY_INPUT_INVENTORY_MISMATCH:{name}")
        artifacts[name] = read_json(path)
    source = manifest["source"]
    for name in names[:2]:
        bundle_source = artifacts[name]["source"]
        if (bundle_source["sha256"] != source["sha256"]
                or bundle_source["proposed_source_id"] != source["source_id"]):
            raise ValueError("REPLAY_SOURCE_IDENTITY_MISMATCH")
    inputs = build_semantic_claim_inputs(
        bundle=artifacts[names[1]], evidence_draft=artifacts[names[2]],
        quote_fidelity=artifacts[names[3]],
    )
    result = artifacts[names[4]]
    ids = [row["claim_id"] for row in inputs]
    if (result.get("schema_version") != "2.1"
            or result.get("input_parent_claim_ids") != ids
            or result.get("output_parent_claim_ids") != ids
            or [row["parent_claim_id"] for row in result.get("results", [])] != ids):
        raise ValueError("REPLAY_SEMANTIC_UNIVERSE_MISMATCH")
    for original, semantic in zip(inputs, result["results"]):
        if original["evidence_units"] != semantic["evidence_units"]:
            raise ValueError("REPLAY_EVIDENCE_IDENTITY_MISMATCH")
    return {
        "inputs": inputs, "result": result,
        "source_sha256": manifest["source"]["sha256"],
        "source_id": manifest["source"]["source_id"],
        "legacy_run_id": manifest["run_id"],
        "origin_manifest_sha256": sha256_file(run_root / "run_manifest.json"),
        "extraction_sha256": inventory[names[0]],
    }


class FrozenSemanticReplay:
    def __init__(self, capture: dict, emit):
        self.capture = copy.deepcopy(capture)
        self.emit = emit
        self.consumed = False

    def __call__(self, inputs: list[dict]) -> dict:
        if self.consumed:
            raise ValueError("FROZEN_SEMANTIC_RESULT_ALREADY_CONSUMED")
        if inputs != self.capture["inputs"]:
            raise ValueError("FROZEN_SEMANTIC_INPUT_MISMATCH")
        self.consumed = True
        self.emit({"event": "FROZEN_SEMANTIC_RESULT_CONSUMED",
                   "owner": "phase4.replay", "kind": "REPLAY",
                   "reason": "EXACT_FROZEN_INPUT_MATCH", "network_calls": 0,
                   "result_replacement": False,
                   "origin_manifest_sha256": self.capture["origin_manifest_sha256"]})
        return copy.deepcopy(self.capture["result"])
