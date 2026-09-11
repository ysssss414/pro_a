"""Thin pre-Production orchestration over the existing operational/review APIs."""

from __future__ import annotations

import json
import os
import platform
import sqlite3
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import uuid4

from .config import load_config
from .operational_ingestion import run_operational_ingestion
from .phase3f_review_completion import (
    ReviewCompletionError, validate_blank_review_packet, write_blank_review_packet,
)
from .phase4_replay import FrozenSemanticReplay, frozen_replay_inputs, read_json
from .phase4_retry import ExecutionLLM, RetryPolicy
from .production_promotion import canonical_sha256, deterministic_id, production_identity, sha256_file


CONTRACT_VERSION = "phase4-execution-v1"
ROOT = Path(__file__).resolve().parents[2]
# Processing dependencies only: no environment dump or arbitrary package hashing.
PROCESSING_MODULES = (
    "phase4_orchestration", "phase4_retry", "phase4_replay", "operational_ingestion",
    "analyzer", "parsers", "pdf_layout", "pipeline", "llm", "config", "prompts",
    "constants", "proposition_ir", "semantic_decomposition", "semantic_admission",
    "table_claim_safety", "corpus_pilot", "gate_c_quality_hardening",
    "production_authorization", "production_promotion", "phase3f_review_completion",
    "db", "ids", "storage", "relation_structure",
)
CHECKPOINTS = {"SOURCE_READY", "SEMANTIC_COMPLETE", "REVIEW_READY"}


class ExecutionBlocked(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _publish(path: Path, data: dict) -> None:
    """A temporary file is not a committed artifact; replace only after flush."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _runtime() -> dict:
    packages = {}
    for name in ("pypdf", "pymupdf", "pymupdf-layout", "requests"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "UNAVAILABLE"
    files = {name: sha256_file(Path(__file__).with_name(name + ".py"))
             for name in PROCESSING_MODULES}
    return {
        "repository_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "contract_version": CONTRACT_VERSION,
        "processing_code_sha256": canonical_sha256(files),
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
        "packages": packages,
    }


def _configuration(config, policy: RetryPolicy) -> dict:
    provider = asdict(config.llm)  # api_key_env is a variable name, never its value.
    effective = asdict(policy.transport_config(config.llm))
    return {"production_path": str(config.db_path.resolve()), "provider": provider,
            "effective_provider": effective, "retry_policy": policy.value,
            "adaptive_extraction_retry": "forbid", "semantic_max_split_depth": 0}


def _inventory(root: Path) -> dict:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] == "commits" or relative.as_posix() in {
            "execution_identity.json", "execution_manifest.json", ".lock",
        }:
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ExecutionBlocked("ARTIFACT_PATH_ESCAPE")
        if path.is_file():
            result[relative.as_posix()] = sha256_file(path)
    return result


def _commit(root: Path, identity: dict, state: str, *, code: str = "") -> dict:
    previous = read_json(root / "execution_manifest.json") if (root / "execution_manifest.json").exists() else None
    sequence = previous["sequence"] + 1 if previous else 0
    manifest = {
        "execution_id": identity["execution_id"],
        "identity_sha256": canonical_sha256(identity), "sequence": sequence,
        "state": state, "code": code, "last_transition_at": _now(),
        "last_successful_state": (
            state if state in CHECKPOINTS else (previous or {}).get("last_successful_state", "CREATED")
        ),
        "inventory": _inventory(root),
        "artifact_references": {
            "native_manifest": "engine/run_manifest.json" if (root / "engine/run_manifest.json").exists() else None,
            "review_packet": "review/packet.json" if state in {"REVIEW_READY", "STOPPED"} else None,
        },
        "production_write_count": 0,
    }
    commit = root / "commits" / f"{sequence:06}.json"
    if commit.exists():
        raise ExecutionBlocked("UNRECONCILED_STAGE_PUBLICATION")
    _publish(commit, manifest)
    _publish(root / "execution_manifest.json", manifest)
    return manifest


def _result(root: Path, state: str | None = None, code: str | None = None) -> dict:
    try:
        manifest = read_json(root / "execution_manifest.json")
    except (OSError, ValueError):
        manifest = {}
    if state == "BLOCKED":
        return {"execution_id": manifest.get("execution_id", root.name),
                "execution_root": str(root), "manifest": str(root / "execution_manifest.json"),
                "state": state, "code": code, "production_write_count": 0,
                "last_successful_state": manifest.get("last_successful_state", "UNKNOWN")}
    result = {key: manifest[key] for key in (
        "execution_id", "state", "code", "last_successful_state", "production_write_count",
    )}
    result.update(execution_root=str(root), manifest=str(root / "execution_manifest.json"))
    if state:
        result.update(state=state, code=code)
    packet_path = root / "review/packet.json"
    if result["state"] in {"REVIEW_READY", "STOPPED"}:
        packet = read_json(packet_path)
        result.update(review_packet=str(packet_path), packet_id=packet["packet_id"],
                      excluded_relation_count=packet["excluded_relation_inventory"]["count"],
                      packet_capability="OPERATIONAL_PARENT_PLACEMENT_ONLY")
    return result


def _compatible(root: Path, execution_id: str, config, policy: RetryPolicy) -> dict:
    identity = read_json(root / "execution_identity.json")
    manifest = read_json(root / "execution_manifest.json")
    if (root.name != execution_id or identity["execution_id"] != execution_id
            or manifest["execution_id"] != execution_id):
        raise ExecutionBlocked("EXECUTION_IDENTITY_MISMATCH")
    first = read_json(root / "commits/000000.json")
    if canonical_sha256(identity) != first["identity_sha256"]:
        raise ExecutionBlocked("IMMUTABLE_EXECUTION_IDENTITY_CHANGED")
    if manifest != read_json(root / "commits" / f"{manifest['sequence']:06}.json"):
        raise ExecutionBlocked("MANIFEST_COMMIT_MISMATCH")
    if len(list((root / "commits").iterdir())) != manifest["sequence"] + 1:
        raise ExecutionBlocked("UNRECONCILED_STAGE_PUBLICATION")
    if identity["runtime"] != _runtime():
        raise ExecutionBlocked("CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE")
    if identity["configuration"] != _configuration(config, policy):
        raise ExecutionBlocked("PROCESSING_PROVIDER_OR_RETRY_CONFIG_DRIFT")
    if identity["production_baseline"] != production_identity(config.db_path):
        raise ExecutionBlocked("PRODUCTION_BASELINE_CHANGED")
    if manifest["inventory"] != _inventory(root):
        raise ExecutionBlocked("ARTIFACT_INVENTORY_MISMATCH")
    native_path = root / "engine/run_manifest.json"
    if native_path.exists():
        native = read_json(native_path)
        source = native["source"]
        frozen = root / "engine" / source["frozen_relative_path"]
        if (native["run_id"] != identity["legacy_ingestion_run_id"]
                or source["source_id"] != identity["source_id"]
                or source["sha256"] != identity["source_sha256"]
                or sha256_file(frozen) != identity["source_sha256"]):
            raise ExecutionBlocked("FROZEN_SOURCE_OR_LEGACY_IDENTITY_CHANGED")
    if manifest["state"] in {"PROCESSING", "FAILED", "BLOCKED"}:
        raise ExecutionBlocked("INTERRUPTED_OR_FAILED_STAGE_REQUIRES_REVIEW")
    return identity


def _emit(root: Path, event: dict) -> None:
    path = root / "attempts" / f"{uuid4().hex}.json"
    manifest = read_json(root / "execution_manifest.json")
    _publish(path, {"created_at": _now(), "execution_id": manifest["execution_id"],
                    "stage": manifest["code"], **event})


def _review(root: Path) -> None:
    native = root / "engine"
    claims = read_json(native / "review/claim_review.json")["claims"]
    nodes = read_json(native / "review/node_operation_review.json")["records"]
    preview = read_json(native / "promotion/promotion_preview.json")
    if not claims or not nodes:
        if preview.get("relations", {}).get("observations"):
            raise ExecutionBlocked("UNSUPPORTED_PACKET_CAPABILITY")
        raise ExecutionBlocked("BLOCKED_EMPTY_CANDIDATE_SET")
    pending = root / "review.pending"
    pending.mkdir()
    packet = write_blank_review_packet(
        run_root=native, packet_path=pending / "packet.json", markdown_path=pending / "packet.md",
    )
    validate_blank_review_packet(packet, native)
    pending.rename(root / "review")


def _advance(root: Path, identity: dict, config_path: Path, stop_after: str) -> dict:
    policy = RetryPolicy(identity["configuration"]["retry_policy"])
    replay_path = root / "inputs/semantic_replay.json"
    replay = FrozenSemanticReplay(read_json(replay_path), lambda e: _emit(root, e)) if replay_path.exists() else None
    factory = lambda cfg: ExecutionLLM(cfg, policy=policy, emit=lambda e: _emit(root, e), offline=replay is not None)
    kwargs = dict(config_path=config_path, run_dir=root / "engine",
                  adaptive_retry_policy="forbid", semantic_max_split_depth=0,
                  llm_factory=factory, semantic_replay=replay)
    state = read_json(root / "execution_manifest.json")["state"]
    if state == "STOPPED":
        return _result(root)
    try:
        if state == "CREATED":
            _commit(root, identity, "PROCESSING", code="SOURCE_REGISTRATION")
            source = Path(identity["original_source_path"])
            if sha256_file(source) != identity["source_sha256"]:
                raise ExecutionBlocked("SOURCE_INPUT_CHANGED")
            run_operational_ingestion(source, stop_after="source", frozen_extraction_path=(
                root / "inputs/extraction.json" if replay is not None else None), **kwargs)
            _commit(root, identity, "SOURCE_READY")
            state = "SOURCE_READY"
        if stop_after == "SOURCE_READY":
            return _result(root)
        if state == "SOURCE_READY":
            _commit(root, identity, "PROCESSING", code="EXTRACTION_AND_EVIDENCE")
            run_operational_ingestion(resume=True, stop_after="evidence", **kwargs)
            semantic = read_json(root / "engine/evidence/semantic_decomposition.json")
            if semantic.get("status") == "SKIPPED_LLM_UNAVAILABLE":
                raise ExecutionBlocked("SEMANTIC_PROVIDER_UNAVAILABLE")
            _commit(root, identity, "SEMANTIC_COMPLETE")
            state = "SEMANTIC_COMPLETE"
        if stop_after == "SEMANTIC_COMPLETE":
            return _result(root)
        if state == "SEMANTIC_COMPLETE":
            _commit(root, identity, "PROCESSING", code="RESOLUTION_AND_REVIEW")
            run_operational_ingestion(resume=True, **kwargs)
            _review(root)
            _commit(root, identity, "REVIEW_READY")
        _commit(root, identity, "STOPPED", code="HUMAN_REVIEW_REQUIRED")
    except (ExecutionBlocked, ReviewCompletionError) as exc:
        code = getattr(exc, "code", str(exc))
        if code in {"CLAIM_REVIEW_EMPTY", "NODE_REVIEW_EMPTY"}:
            code = "BLOCKED_EMPTY_CANDIDATE_SET"
        _commit(root, identity, "BLOCKED", code=code)
    except Exception as exc:
        _commit(root, identity, "FAILED", code=f"{type(exc).__name__}:{exc}")
    return _result(root)


def start_execution(source_path: Path, *, config_path: Path = Path("config.toml"),
                    retry_policy: RetryPolicy = RetryPolicy.FORBID_ALL,
                    replay_run: Path | None = None, stop_after: str = "REVIEW_READY") -> dict:
    if stop_after not in CHECKPOINTS:
        raise ValueError("INVALID_STOP_CHECKPOINT")
    policy = RetryPolicy(retry_policy)
    config = load_config(config_path)
    source = Path(source_path).resolve()
    source_sha = sha256_file(source)
    capture = frozen_replay_inputs(Path(replay_run)) if replay_run is not None else None
    if capture is not None and capture["source_sha256"] != source_sha:
        raise ExecutionBlocked("REPLAY_SOURCE_MISMATCH")
    execution_id = f"EXEC_{uuid4().hex.upper()}"
    root = config.root / "phase4/executions" / execution_id
    if root.resolve() != root or root.exists():
        raise ExecutionBlocked("EXECUTION_PATH_UNSAFE_OR_EXISTS")
    configuration = _configuration(config, policy)
    identity = {
        "execution_id": execution_id, "source_sha256": source_sha,
        "original_source_path": str(source),
        "source_id": capture["source_id"] if capture else deterministic_id("SRC", {"source_sha256": source_sha}),
        "legacy_ingestion_run_id": f"INGEST_{source_sha[:16].upper()}",
        "created_at": _now(), "runtime": _runtime(),
        "configuration": configuration, "configuration_sha256": canonical_sha256(configuration),
        "production_baseline": production_identity(config.db_path),
        "mode": "FROZEN_RESULT_REPLAY" if capture else "CONFIGURED_PROVIDER",
        "replay_origin": capture["origin_manifest_sha256"] if capture else None,
    }
    root.mkdir(parents=True)
    for name in ("commits", "inputs", "attempts"):
        (root / name).mkdir()
    with (root / "execution_identity.json").open("x", encoding="utf-8") as handle:
        json.dump(identity, handle, ensure_ascii=False, sort_keys=True, indent=2)
    if capture is not None:
        _publish(root / "inputs/semantic_replay.json", capture)
        extraction = Path(replay_run) / "extraction/extraction_bundle.json"
        (root / "inputs/extraction.json").write_bytes(extraction.read_bytes())
        if sha256_file(root / "inputs/extraction.json") != capture["extraction_sha256"]:
            raise ExecutionBlocked("REPLAY_EXTRACTION_CHANGED_DURING_COPY")
    _commit(root, identity, "CREATED")
    return resume_execution(root, execution_id=execution_id, config_path=config_path,
                            retry_policy=policy, stop_after=stop_after)


def resume_execution(execution_root: Path, *, execution_id: str,
                     config_path: Path = Path("config.toml"),
                     retry_policy: RetryPolicy = RetryPolicy.FORBID_ALL,
                     stop_after: str = "REVIEW_READY") -> dict:
    if stop_after not in CHECKPOINTS:
        raise ValueError("INVALID_STOP_CHECKPOINT")
    root = Path(execution_root).resolve()
    config = load_config(config_path)
    if root.parent != config.root / "phase4/executions":
        return _result(root, "BLOCKED", "EXECUTION_ROOT_CONFIG_MISMATCH")
    try:
        lock = (root / ".lock").open("x")
    except FileExistsError:
        return _result(root, "BLOCKED", "EXECUTION_BUSY_OR_INTERRUPTED_LOCK")
    except OSError:
        return _result(root, "BLOCKED", "EXECUTION_MANIFEST_UNAVAILABLE")
    try:
        try:
            identity = _compatible(root, execution_id, config, RetryPolicy(retry_policy))
        except (ExecutionBlocked, ValueError, KeyError, OSError) as exc:
            return _result(root, "BLOCKED", str(exc))
        return _advance(root, identity, config_path, stop_after)
    finally:
        lock.close()
        (root / ".lock").unlink()
