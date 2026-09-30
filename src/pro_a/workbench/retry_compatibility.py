"""Bounded, fail-closed cross-release qualification for extraction retries."""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from pro_a.cloud_contract import canonical, digest, now, operation_contract
from pro_a.config import load_config
from pro_a.phase4_orchestration import (
    PROCESSING_MODULES,
    _compatible,
    _runtime as native_runtime,
)
from pro_a.phase4_retry import RetryPolicy
from pro_a.production_promotion import sha256_file
from .config import BoundaryError, checked_path
from .domains import Domains, config_digest, prompt_digest
from .review_store import schema_version
from .store import Store


CONTRACT_VERSION = "extraction-retry-cross-release-v1"
TABLE = "retry_compatibility_qualifications"
_CLOUD_METADATA_FIELDS = frozenset(("git_sha", "runtime_sha256"))
_NATIVE_METADATA_FIELDS = frozenset(("repository_commit",))
_CLOUD_SURFACE_FIELDS = frozenset(("domain_code_sha256", "phase4_processing_code_sha256"))
_NATIVE_SURFACE_FIELDS = frozenset(("processing_code_sha256",))
_CLOUD_EXECUTION_ROOTS = {
    "workbench/cloud_jobs.py": ("CloudJobs.run_once",),
    "workbench/source_operations.py": ("SourceOperations._advance_claimed",),
}
_CLOUD_EXECUTION_DEPENDENCIES = {
    "cloud_contract.py": None,
    "provider_diagnostics.py": None,
    "domain_packs.py": None,
    "run_context.py": None,
    "workbench/artifacts.py": None,
    "workbench/domains.py": (
        "config_digest", "prompt_digest", "Domains.assignment", "Domains.packs",
        "Domains.basis", "Domains.pending_basis", "Domains.read", "Domains.guard",
    ),
    "workbench/cloud_jobs.py": (
        "runtime_identity", "CloudProfile.validate", "CloudProfile.public_identity",
        "CloudProfile.adapter_for_operation",
        "CloudJobs.__init__", "CloudJobs.current_runtime", "CloudJobs._event",
        "CloudJobs._verify_event_chain", "CloudJobs._native_identity",
        "CloudJobs._input_payload", "CloudJobs._preflight", "CloudJobs._claim",
        "CloudJobs._owned", "CloudJobs._dispatch_intent",
        "CloudJobs._record_provider_failure", "CloudJobs._mark_call_possible",
        "CloudJobs._artifact_path", "CloudJobs._durable_result",
        "CloudJobs._write_result_artifact", "CloudJobs._register_result",
        "CloudJobs._terminal", "CloudJobs._fault", "CloudJobs._project", "CloudJobs.get",
    ),
    "workbench/source_operations.py": (
        "_canonical", "_now", "_ExtractionReplay", "SourceProfile.validate",
        "SourceOperations.__init__", "SourceOperations._event",
        "SourceOperations._transition", "SourceOperations._community_bound",
        "SourceOperations._register_input", "SourceOperations._bind_job",
        "SourceOperations._jobs_for", "SourceOperations._propagate_job_state",
        "SourceOperations._run_pending_jobs", "SourceOperations._extraction_replay",
        "SourceOperations._native_root", "SourceOperations._semantic_replay",
        "SourceOperations._copy_and_register_packet", "SourceOperations._post_processing",
        "SourceOperations._project_run", "SourceOperations.get_run",
    ),
}
_CLOUD_EXECUTION_SURFACE = {
    **_CLOUD_EXECUTION_DEPENDENCIES,
    "workbench/cloud_jobs.py": (
        *_CLOUD_EXECUTION_DEPENDENCIES["workbench/cloud_jobs.py"],
        *_CLOUD_EXECUTION_ROOTS["workbench/cloud_jobs.py"],
    ),
    "workbench/source_operations.py": (
        *_CLOUD_EXECUTION_DEPENDENCIES["workbench/source_operations.py"],
        *_CLOUD_EXECUTION_ROOTS["workbench/source_operations.py"],
    ),
}
_NATIVE_EXECUTION_ROOTS = {
    "phase4_orchestration.py": ("resume_execution",),
}
_NATIVE_EXECUTION_DEPENDENCIES = {
    **{
        f"{name}.py": None
        for name in PROCESSING_MODULES
        if name != "phase4_orchestration"
    },
    "phase4_orchestration.py": (
        "_now", "_publish", "_runtime", "_configuration", "_inventory", "_commit",
        "_result", "_compatible", "_emit", "_review", "_advance",
    ),
}
_NATIVE_EXECUTION_SURFACE = {
    **_NATIVE_EXECUTION_DEPENDENCIES,
    "phase4_orchestration.py": (
        *_NATIVE_EXECUTION_DEPENDENCIES["phase4_orchestration.py"],
        *_NATIVE_EXECUTION_ROOTS["phase4_orchestration.py"],
    ),
}
_EXECUTION_SURFACE_EXCLUSIONS = {
    "cloud": {
        "workbench/extraction_retry.py": (
            "Target-only authorization and immutable retry-copy construction; it does not "
            "exist in the historical execution and remains bound by the target contract digest."
        ),
        "workbench/retry_compatibility.py": (
            "Target-only evidence validator and authorization token; exact call-site plumbing is "
            "normalized below and the validator remains bound by the target contract digest."
        ),
    },
    "native": {},
}
_INTEGRATION_FILES = (
    "analyzer.py",
    "cloud_contract.py",
    "config.py",
    "llm.py",
    "operational_ingestion.py",
    "phase4_orchestration.py",
    "phase4_retry.py",
    "processing_context.py",
    "prompts.py",
    "provider_diagnostics.py",
    "run_context.py",
    "semantic_decomposition.py",
    "workbench/artifacts.py",
    "workbench/cloud_jobs.py",
    "workbench/domains.py",
    "workbench/source_operations.py",
    "workbench/extraction_retry.py",
    "workbench/retry_compatibility.py",
)
_CONTRACT_FILES = tuple(sorted(
    set(_INTEGRATION_FILES) | set(_CLOUD_EXECUTION_SURFACE) | set(_NATIVE_EXECUTION_SURFACE)
))


class RetryCompatibilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class _ValidatedQualification:
    """Internal evidence token; callers cannot substitute a boolean or SHA."""

    record: Mapping[str, Any]


def installed(connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,),
    ).fetchone() is not None


def prepare_retry_compatibility(config) -> dict[str, str]:
    """Operator-only additive extension; never called by startup or reads."""
    config.validate()
    if config.mode != "PRIVATE":
        raise BoundaryError("PRIVATE_SOURCE_MODE_REQUIRED")
    with Store(config).connect(operator_write=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        if schema_version(connection) not in ("9", "10", "11", "12"):
            raise BoundaryError("DOMAIN_SCHEMA_REQUIRED")
        from .extraction_retry import installed as retry_installed
        if not retry_installed(connection):
            raise BoundaryError("RETRY_SCHEMA_REQUIRED")
        if installed(connection):
            return {"status": "ALREADY_PREPARED", "extension": CONTRACT_VERSION}
        connection.execute(f'''CREATE TABLE {TABLE}(
            qualification_id TEXT PRIMARY KEY,
            processing_run_id TEXT NOT NULL REFERENCES source_processing_runs(processing_run_id),
            source_id TEXT NOT NULL REFERENCES private_sources(source_id),
            failed_attempt_id TEXT NOT NULL REFERENCES cloud_attempts(attempt_id),
            failed_job_id TEXT NOT NULL REFERENCES cloud_jobs(job_id),
            historical_runtime_sha256 TEXT NOT NULL,
            target_runtime_sha256 TEXT NOT NULL,
            historical_context_sha256 TEXT NOT NULL,
            target_contract_version TEXT NOT NULL,
            target_contract_sha256 TEXT NOT NULL,
            dimensions_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            evidence_sha256 TEXT NOT NULL,
            qualification_result TEXT NOT NULL CHECK(qualification_result='QUALIFIED'),
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            record_sha256 TEXT NOT NULL UNIQUE,
            UNIQUE(processing_run_id,failed_attempt_id,target_runtime_sha256,target_contract_sha256))''')
        for action in ("UPDATE", "DELETE"):
            connection.execute(
                f"CREATE TRIGGER {TABLE}_{action.lower()}_forbidden BEFORE {action} ON {TABLE} "
                "BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END"
            )
    return {"status": "PREPARED", "extension": CONTRACT_VERSION}


def compatibility_contract_sha256() -> str:
    package = Path(__file__).parent.parent
    return digest({
        "contract_version": CONTRACT_VERSION,
        "cloud_metadata_fields": sorted(_CLOUD_METADATA_FIELDS),
        "native_metadata_fields": sorted(_NATIVE_METADATA_FIELDS),
        "cloud_surface_fields": sorted(_CLOUD_SURFACE_FIELDS),
        "native_surface_fields": sorted(_NATIVE_SURFACE_FIELDS),
        "cloud_execution_roots": _CLOUD_EXECUTION_ROOTS,
        "cloud_execution_dependencies": _CLOUD_EXECUTION_DEPENDENCIES,
        "cloud_execution_surface": _CLOUD_EXECUTION_SURFACE,
        "native_execution_roots": _NATIVE_EXECUTION_ROOTS,
        "native_execution_dependencies": _NATIVE_EXECUTION_DEPENDENCIES,
        "native_execution_surface": _NATIVE_EXECUTION_SURFACE,
        "execution_surface_exclusions": _EXECUTION_SURFACE_EXCLUSIONS,
        "files": {name: sha256_file(package / name) for name in _CONTRACT_FILES},
    })


class _RemoveDocstrings(ast.NodeTransformer):
    def generic_visit(self, node):
        node = super().generic_visit(node)
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:]
        return node


def _selected_node(tree: ast.AST, selector: str) -> ast.AST:
    node = tree
    for part in selector.split("."):
        candidates = getattr(node, "body", ())
        node = next(
            (candidate for candidate in candidates
             if isinstance(candidate, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
             and candidate.name == part),
            None,
        )
        if node is None:
            raise RetryCompatibilityError(f"EXECUTION_SURFACE_SELECTOR_MISSING:{selector}")
    return node


_COMPATIBILITY_SIGNATURES = frozenset({
    ("workbench/cloud_jobs.py", "CloudJobs.__init__"),
    ("workbench/source_operations.py", "SourceOperations.__init__"),
    ("workbench/domains.py", "Domains.guard"),
    ("phase4_orchestration.py", "_compatible"),
    ("phase4_orchestration.py", "resume_execution"),
})
_COMPATIBILITY_ASSIGNMENTS = frozenset({
    ("workbench/cloud_jobs.py", "CloudJobs.__init__"),
    ("workbench/source_operations.py", "SourceOperations.__init__"),
})
_COMPATIBILITY_CALL_KEYWORDS = {
    ("workbench/cloud_jobs.py", "CloudJobs._native_identity"): {"guard": 1},
    ("workbench/cloud_jobs.py", "CloudJobs.run_once"): {"CloudJobs": 1},
    ("workbench/source_operations.py", "SourceOperations.__init__"): {"CloudJobs": 1},
    ("workbench/source_operations.py", "SourceOperations._register_input"): {"guard": 1},
    ("workbench/source_operations.py", "SourceOperations._advance_claimed"): {
        "guard": 1, "resume_execution": 2,
    },
    ("phase4_orchestration.py", "resume_execution"): {"_compatible": 1},
}
_COMPATIBILITY_STATEMENT_REPLACEMENTS = {
    ("workbench/cloud_jobs.py", "CloudJobs._preflight"): ((
        '''
runtime_valid = (stored_runtime_hash == digest(runtime_basis)
                 and row["runtime_sha256"] == stored_runtime_hash)
if runtime_valid and canonical(stored_runtime) != canonical(current_runtime):
    try:
        from .retry_compatibility import guard_cloud_runtime
        guard_cloud_runtime(stored_runtime, current_runtime, self.runtime_compatibility)
    except Exception:
        runtime_valid = False
if not runtime_valid:
    raise JobError("RUNTIME_DRIFT")
''',
        '''
if (stored_runtime_hash != digest(runtime_basis)
        or row["runtime_sha256"] != stored_runtime_hash
        or canonical(stored_runtime) != canonical(current_runtime)):
    raise JobError("RUNTIME_DRIFT")
''',
    ),),
    ("workbench/domains.py", "Domains.guard"): (
        (
            '''
if runtime_compatibility is None:
    processing_context.guard_resume(frozen, current)
else:
    from .retry_compatibility import guard_context
    guard_context(frozen, current, runtime_compatibility)
''',
            '''processing_context.guard_resume(frozen, current)''',
        ),
        (
            '''
if runtime_compatibility is None:
    guard_resume(frozen, current)
else:
    from .retry_compatibility import guard_context
    guard_context(frozen, current, runtime_compatibility)
''',
            '''guard_resume(frozen, current)''',
        ),
    ),
    ("workbench/source_operations.py", "SourceOperations._advance_claimed"): ((
        '''
current_runtime = self.jobs.current_runtime()
if row["runtime_sha256"] != current_runtime["runtime_sha256"]:
    try:
        from .retry_compatibility import guard_cloud_runtime
        guard_cloud_runtime(
            json.loads(row["runtime_json"]), current_runtime,
            self.runtime_compatibility,
        )
    except Exception:
        self._transition(run_id, "BLOCKED", "RUNTIME_PREFLIGHT", error="RUNTIME_DRIFT")
        return self.get_run(run_id)
''',
        '''
if row["runtime_sha256"] != self.jobs.current_runtime()["runtime_sha256"]:
    self._transition(run_id, "BLOCKED", "RUNTIME_PREFLIGHT", error="RUNTIME_DRIFT")
    return self.get_run(run_id)
''',
    ),),
    ("phase4_orchestration.py", "_compatible"): ((
        '''
current_runtime = _runtime()
if identity["runtime"] != current_runtime:
    try:
        from .workbench.retry_compatibility import guard_native_runtime
        guard_native_runtime(identity["runtime"], current_runtime, runtime_compatibility)
    except Exception:
        raise ExecutionBlocked("CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE") from None
''',
        '''
if identity["runtime"] != _runtime():
    raise ExecutionBlocked("CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE")
''',
    ),),
}


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _statement_dump(statement: ast.AST) -> str:
    return ast.dump(statement, include_attributes=False)


def _replace_exact_statements(node: ast.AST, before: str, after: str) -> int:
    expected = ast.parse(before).body
    replacement = ast.parse(after).body
    expected_dump = [_statement_dump(statement) for statement in expected]
    count = 0
    for child in ast.walk(node):
        for field in ("body", "orelse", "finalbody"):
            body = getattr(child, field, None)
            if not isinstance(body, list) or len(body) < len(expected):
                continue
            index = 0
            while index <= len(body) - len(expected):
                candidate = body[index:index + len(expected)]
                if [_statement_dump(statement) for statement in candidate] == expected_dump:
                    body[index:index + len(expected)] = copy.deepcopy(replacement)
                    count += 1
                    index += len(replacement)
                else:
                    index += 1
    if count > 1:
        raise RetryCompatibilityError("EXECUTION_SURFACE_NORMALIZATION_AMBIGUOUS")
    return count


def _normalize_compatibility_plumbing(name: str, selector: str, node: ast.AST) -> ast.AST:
    key = (name, selector)
    node = copy.deepcopy(node)
    if key in _COMPATIBILITY_SIGNATURES and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        matches = [
            index for index, argument in enumerate(node.args.kwonlyargs)
            if argument.arg == "runtime_compatibility"
            and isinstance(node.args.kw_defaults[index], ast.Constant)
            and node.args.kw_defaults[index].value is None
        ]
        if len(matches) > 1:
            raise RetryCompatibilityError("EXECUTION_SURFACE_NORMALIZATION_AMBIGUOUS")
        if matches:
            index = matches[0]
            del node.args.kwonlyargs[index]
            del node.args.kw_defaults[index]
    if key in _COMPATIBILITY_ASSIGNMENTS and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        assignment = _statement_dump(ast.parse(
            "self.runtime_compatibility = runtime_compatibility"
        ).body[0])
        matches = [
            index for index, statement in enumerate(node.body)
            if _statement_dump(statement) == assignment
        ]
        if len(matches) > 1:
            raise RetryCompatibilityError("EXECUTION_SURFACE_NORMALIZATION_AMBIGUOUS")
        if matches:
            del node.body[matches[0]]
    allowed_calls = _COMPATIBILITY_CALL_KEYWORDS.get(key, {})
    call_matches = {name: [] for name in allowed_calls}
    for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
        if _call_name(call) not in allowed_calls:
            continue
        matches = [
            keyword for keyword in call.keywords
            if keyword.arg == "runtime_compatibility"
            and (
                isinstance(keyword.value, ast.Name)
                and keyword.value.id == "runtime_compatibility"
                or isinstance(keyword.value, ast.Attribute)
                and isinstance(keyword.value.value, ast.Name)
                and keyword.value.value.id == "self"
                and keyword.value.attr == "runtime_compatibility"
            )
        ]
        if len(matches) > 1:
            raise RetryCompatibilityError("EXECUTION_SURFACE_NORMALIZATION_AMBIGUOUS")
        if matches:
            call_matches[_call_name(call)].append((call, matches[0]))
    for call_name, matches in call_matches.items():
        if len(matches) not in (0, allowed_calls[call_name]):
            raise RetryCompatibilityError("EXECUTION_SURFACE_NORMALIZATION_AMBIGUOUS")
        for call, keyword in matches:
            call.keywords.remove(keyword)
    for before, after in _COMPATIBILITY_STATEMENT_REPLACEMENTS.get(key, ()):
        _replace_exact_statements(node, before, after)
    ast.fix_missing_locations(node)
    return node


def _validate_dependency_closure(tree: ast.AST, name: str,
                                 selectors: tuple[str, ...] | None) -> None:
    if selectors is None:
        return
    included = set(selectors)
    module_functions = {
        item.name for item in getattr(tree, "body", ())
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for selector in selectors:
        node = _selected_node(tree, selector)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        dependencies: set[str] = set()
        if "." in selector:
            class_name = selector.split(".", 1)[0]
            for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
                if (isinstance(call.func, ast.Attribute)
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == "self"):
                    dependencies.add(f"{class_name}.{call.func.attr}")
        else:
            dependencies.update(
                call.func.id
                for call in (item for item in ast.walk(node) if isinstance(item, ast.Call))
                if isinstance(call.func, ast.Name) and call.func.id in module_functions
            )
        missing = sorted(dependencies - included)
        if missing:
            raise RetryCompatibilityError(
                f"EXECUTION_SURFACE_DEPENDENCY_UNCLOSED:{name}:{selector}:{','.join(missing)}"
            )


def _ast_sha256(content: bytes, selectors: tuple[str, ...] | None, *, name: str = "") -> str:
    tree = _RemoveDocstrings().visit(ast.parse(content.decode("utf-8")))
    ast.fix_missing_locations(tree)
    _validate_dependency_closure(tree, name, selectors)
    selected = tree if selectors is None else {
        selector: ast.dump(
            _normalize_compatibility_plumbing(name, selector, _selected_node(tree, selector)),
            include_attributes=False,
        )
        for selector in selectors
    }
    value = ast.dump(selected, include_attributes=False) if selectors is None else canonical(selected)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _surface_manifest(sources: Mapping[str, bytes],
                      specification: Mapping[str, tuple[str, ...] | None]) -> dict[str, Any]:
    files = {
        name: {
            "source_sha256": hashlib.sha256(sources[name]).hexdigest(),
            "semantic_ast_sha256": _ast_sha256(sources[name], selectors, name=name),
        }
        for name, selectors in specification.items()
    }
    return {"files": files, "roots": {
        key: value for key, value in {
            **_CLOUD_EXECUTION_ROOTS, **_NATIVE_EXECUTION_ROOTS,
        }.items() if key in specification
    }, "semantic_surface_sha256": digest({
        name: value["semantic_ast_sha256"] for name, value in files.items()
    })}


def _execution_surface_sources(
        historical_git_sha: str,
        specification: Mapping[str, tuple[str, ...] | None],
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    package = Path(__file__).resolve().parent.parent
    root = package.parents[1]
    historical: dict[str, bytes] = {}
    target: dict[str, bytes] = {}
    for name in specification:
        repository_name = f"src/pro_a/{name}"
        historical[name] = subprocess.check_output(
            ["git", "show", f"{historical_git_sha}:{repository_name}"], cwd=root,
            stderr=subprocess.DEVNULL,
        )
        target[name] = (package / name).read_bytes()
    return historical, target


@lru_cache(maxsize=64)
def _execution_surface_comparison(kind: str, historical_git_sha: str) -> dict[str, Any]:
    specification = {
        "cloud": _CLOUD_EXECUTION_SURFACE,
        "native": _NATIVE_EXECUTION_SURFACE,
    }.get(kind)
    result: dict[str, Any] = {
        "surface_version": CONTRACT_VERSION,
        "kind": kind,
        "historical_git_sha": historical_git_sha,
        "compatible": False,
    }
    if specification is None or not re.fullmatch(r"[0-9a-f]{40,64}", historical_git_sha or ""):
        result["reason"] = "HISTORICAL_GIT_IDENTITY_INVALID"
        return result
    try:
        historical, target = _execution_surface_sources(historical_git_sha, specification)
        historical_manifest = _surface_manifest(historical, specification)
        target_manifest = _surface_manifest(target, specification)
    except (OSError, UnicodeError, subprocess.CalledProcessError, SyntaxError,
            RetryCompatibilityError) as exc:
        result["reason"] = f"EXECUTION_SURFACE_UNAVAILABLE:{type(exc).__name__}"
        return result
    result.update({
        "historical": historical_manifest,
        "target": target_manifest,
        "compatible": historical_manifest["semantic_surface_sha256"]
        == target_manifest["semantic_surface_sha256"],
        "reason": "SEMANTIC_SURFACE_EXACT" if historical_manifest["semantic_surface_sha256"]
        == target_manifest["semantic_surface_sha256"] else "SEMANTIC_SURFACE_CHANGED",
    })
    return result


def _runtime_comparison(historical: Mapping[str, Any], target: Mapping[str, Any],
                        metadata_fields: frozenset[str], *,
                        surface_fields: frozenset[str] = frozenset(),
                        surface_compatible: bool = False) -> dict[str, Any]:
    different = sorted(
        key for key in set(historical) | set(target)
        if historical.get(key) != target.get(key)
    )
    surface_differences = [
        key for key in different if key in surface_fields and surface_compatible
    ]
    semantic_differences = [
        key for key in different
        if key not in metadata_fields and key not in surface_differences
    ]
    return {
        "compatible": not semantic_differences,
        "different_fields": different,
        "semantic_differences": semantic_differences,
        "metadata_only_differences": [key for key in different if key in metadata_fields],
        "surface_equivalent_differences": surface_differences,
        "historical_sha256": digest(dict(historical)),
        "target_sha256": digest(dict(target)),
    }


def _dimension(classification: str, result: str, evidence: str) -> dict[str, str]:
    return {"classification": classification, "result": result, "evidence": evidence}


def _record_body(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in (
        "qualification_id", "processing_run_id", "source_id", "failed_attempt_id",
        "failed_job_id", "historical_runtime_sha256", "target_runtime_sha256",
        "historical_context_sha256", "target_contract_version", "target_contract_sha256",
        "dimensions_json", "evidence_json", "evidence_sha256", "qualification_result",
        "reason", "created_at",
    )}


def _validate_record(record: Mapping[str, Any]) -> _ValidatedQualification:
    value = dict(record)
    if (value.get("target_contract_version") != CONTRACT_VERSION
            or value.get("target_contract_sha256") != compatibility_contract_sha256()
            or value.get("qualification_result") != "QUALIFIED"):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_STALE")
    try:
        dimensions = json.loads(value["dimensions_json"])
        evidence = json.loads(value["evidence_json"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_EVIDENCE_INVALID") from None
    if (canonical(dimensions) != value["dimensions_json"]
            or canonical(evidence) != value["evidence_json"]
            or digest(evidence) != value["evidence_sha256"]
            or any(item.get("result") != "PASS" for item in dimensions.values())):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_EVIDENCE_MISMATCH")
    if digest(_record_body(value)) != value.get("record_sha256"):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_RECORD_MISMATCH")
    return _ValidatedQualification(value)


def _evidence(token: _ValidatedQualification) -> dict[str, Any]:
    if not isinstance(token, _ValidatedQualification):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_NOT_VALIDATED")
    validated = _validate_record(token.record)
    return json.loads(validated.record["evidence_json"])


def guard_cloud_runtime(historical: Mapping[str, Any], target: Mapping[str, Any],
                        token: _ValidatedQualification) -> None:
    evidence = _evidence(token)
    surface = evidence.get("cloud_execution_surface", {})
    comparison = _runtime_comparison(
        historical, target, _CLOUD_METADATA_FIELDS,
        surface_fields=_CLOUD_SURFACE_FIELDS,
        surface_compatible=(surface.get("compatible") is True
                            and surface.get("historical_git_sha") == historical.get("git_sha")),
    )
    if (not comparison["compatible"]
            or comparison != evidence.get("cloud_runtime")
            or historical.get("runtime_sha256") != token.record["historical_runtime_sha256"]
            or target.get("runtime_sha256") != token.record["target_runtime_sha256"]):
        raise RetryCompatibilityError("RETRY_RUNTIME_INCOMPATIBLE")


def guard_native_runtime(historical: Mapping[str, Any], target: Mapping[str, Any],
                         token: _ValidatedQualification) -> None:
    evidence = _evidence(token)
    surface = evidence.get("native_execution_surface", {})
    comparison = _runtime_comparison(
        historical, target, _NATIVE_METADATA_FIELDS,
        surface_fields=_NATIVE_SURFACE_FIELDS,
        surface_compatible=(surface.get("compatible") is True
                            and surface.get("historical_git_sha")
                            == historical.get("repository_commit")),
    )
    if not comparison["compatible"] or comparison != evidence.get("native_runtime"):
        raise RetryCompatibilityError("CODE_OR_RUNTIME_CONTRACT_INCOMPATIBLE")


def guard_context(frozen: Mapping[str, Any], current_basis: Mapping[str, Any],
                  token: _ValidatedQualification) -> None:
    evidence = _evidence(token)
    historical_basis = dict(frozen["basis"])
    historical_runtime = historical_basis.pop("runtime")
    target_basis = dict(current_basis)
    target_runtime = target_basis.pop("runtime")
    surface = evidence.get("cloud_execution_surface", {})
    comparison = _runtime_comparison(
        historical_runtime, target_runtime, _CLOUD_METADATA_FIELDS,
        surface_fields=_CLOUD_SURFACE_FIELDS,
        surface_compatible=(surface.get("compatible") is True
                            and surface.get("historical_git_sha")
                            == historical_runtime.get("git_sha")),
    )
    if (canonical(historical_basis) != canonical(target_basis)
            or not comparison["compatible"]
            or comparison != evidence.get("cloud_runtime")
            or frozen["context_sha256"] != token.record["historical_context_sha256"]):
        raise RetryCompatibilityError("PROCESSING_RUN_CONTEXT_DRIFT")


def _validate_input_artifact(config, connection, job: Mapping[str, Any]) -> dict[str, Any]:
    source_input = connection.execute(
        "SELECT * FROM source_cloud_inputs WHERE artifact_id=?", (job["input_artifact_id"],),
    ).fetchone()
    if source_input is None:
        raise RetryCompatibilityError("INPUT_ARTIFACT_UNAVAILABLE")
    from .artifacts import Artifacts
    path = Artifacts(config).resolve(source_input["artifact_relative"])
    content_sha = sha256_file(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        raise RetryCompatibilityError("INPUT_ARTIFACT_INVALID") from None
    required = {
        "document_type", "schema_version", "operation_kind", "source_id", "source_sha256",
        "processing_run_id", "native_execution_id", "payload", "payload_sha256", "checkpoint",
    }
    if (content_sha != source_input["sha256"] or content_sha != job["input_sha256"]
            or not isinstance(document, dict) or set(document) != required
            or document["document_type"] != "phase42_stage7_cloud_input"
            or document["schema_version"] != "1"
            or document["operation_kind"] != job["operation_kind"]
            or document["source_id"] != source_input["source_id"]
            or document["processing_run_id"] != source_input["processing_run_id"]
            or document["payload_sha256"] != digest(document["payload"])
            or canonical(document["checkpoint"]) != source_input["checkpoint_json"]
            or canonical(document["checkpoint"]) != job["native_checkpoint_json"]):
        raise RetryCompatibilityError("INPUT_ARTIFACT_BINDING_MISMATCH")
    return {
        "artifact_id": job["input_artifact_id"], "sha256": content_sha,
        "payload_sha256": document["payload_sha256"],
        "native_execution_id": document["native_execution_id"],
    }


def _blocked(blockers: list[str], dimensions: Mapping[str, Any],
             evidence: Mapping[str, Any]) -> dict[str, Any]:
    ordered = list(dict.fromkeys(blockers))
    return {
        "status": "BLOCKED", "qualification_result": "BLOCKED",
        "blockers": ordered, "reason": ordered[0],
        "dimensions": dict(dimensions), "evidence": dict(evidence),
        "record": None,
    }


def assess_retry_compatibility(config, run_id: str, failed_attempt_id: str,
                               *, persist: bool = False) -> dict[str, Any]:
    """Assess immutable state; persist only an exact-scope QUALIFIED record."""
    from .cloud_jobs import runtime_identity
    from .extraction_retry import frozen_cloud
    from .source_operations import SourceOperations, SourceProfile

    dimensions: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    blockers: list[str] = []
    with Store(config).connect() as connection:
        run = connection.execute(
            "SELECT * FROM source_processing_runs WHERE processing_run_id=?", (run_id,),
        ).fetchone()
        attempt = connection.execute(
            "SELECT a.*,o.outcome,o.external_outcome FROM cloud_attempts a "
            "JOIN cloud_attempt_outcomes o ON o.attempt_id=a.attempt_id WHERE a.attempt_id=?",
            (failed_attempt_id,),
        ).fetchone()
        if run is None or attempt is None:
            return _blocked(["BLOCKED_HISTORICAL_SCOPE_UNAVAILABLE"], dimensions, evidence)
        job = connection.execute("SELECT * FROM cloud_jobs WHERE job_id=?", (attempt["job_id"],)).fetchone()
        source = connection.execute("SELECT * FROM private_sources WHERE source_id=?", (run["source_id"],)).fetchone()
        binding = connection.execute(
            "SELECT * FROM domain_run_bindings WHERE processing_run_id=?", (run_id,),
        ).fetchone()
        bound = connection.execute(
            "SELECT * FROM source_processing_jobs WHERE processing_run_id=? AND job_id=? "
            "AND operation_kind='SOURCE_ANALYSIS_PIECE'", (run_id, job["job_id"]),
        ).fetchone()
        eligible = (job is not None and source is not None and binding is not None and bound is not None
                    and run["state"] == "FAILED" and run["stage"] == "EXTRACTION_JOBS"
                    and run["error_code"] == "PROVIDER_ERROR" and job["state"] == "FAILED"
                    and job["phase"] == "TERMINAL" and job["sanitized_error"] == "PROVIDER_ERROR"
                    and attempt["outcome"] == "FAILED" and attempt["external_outcome"] == "KNOWN_FAILURE")
        dimensions["historical_failed_scope"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if eligible else "FAIL",
            "Run, extraction Job and failed Attempt are relationally bound and terminal.",
        )
        if not eligible:
            return _blocked(["BLOCKED_HISTORICAL_SCOPE_INELIGIBLE"], dimensions, evidence)

        source_path = checked_path(config.artifact_root / source["storage_relative"])
        source_ok = (job["source_id"] == source["source_id"]
                     and sha256_file(source_path) == source["source_sha256"])
        dimensions["source_identity"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if source_ok else "FAIL",
            "private_sources identity and immutable Source bytes SHA-256.",
        )
        if not source_ok:
            blockers.append("BLOCKED_SOURCE_IDENTITY_CHANGED")

        try:
            frozen = Domains(config).read(run_id, connection=connection)
        except Exception:
            frozen = None
        context_ok = (frozen is not None and frozen["basis"]["source_id"] == run["source_id"]
                      and frozen["basis"]["runtime"]["runtime_sha256"] == run["runtime_sha256"])
        dimensions["frozen_context_identity"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if context_ok else "FAIL",
            "Append-only domain_run_bindings artifact and frozen context digests.",
        )
        if not context_ok:
            blockers.append("BLOCKED_CONTEXT_SEMANTIC_DRIFT")

        try:
            ref = json.loads(binding["config_path"])
            source_profile = SourceProfile(
                Path(ref["path"]), ref["max_pdf_bytes"], ref["max_extraction_pieces"],
            )
            source_profile.validate()
            cloud_profile = frozen_cloud(job)
            phase4 = load_config(source_profile.phase4_config_path)
            limits = {"max_pdf_bytes": source_profile.max_pdf_bytes,
                      "max_extraction_pieces": source_profile.max_extraction_pieces}
            config_ok = (frozen is not None
                         and config_digest(source_profile.phase4_config_path, limits)
                         == frozen["basis"]["config_sha256"]
                         and cloud_profile.public_identity() == frozen["basis"]["model_configuration"])
        except Exception:
            source_profile = cloud_profile = phase4 = None
            config_ok = False
        dimensions["frozen_effective_configuration"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if config_ok else "FAIL",
            "Persisted CloudProfile fields plus original Phase4 path and semantic config digest.",
        )
        dimensions["source_limits"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if config_ok else "FAIL",
            "max_pdf_bytes and max_extraction_pieces are taken from the frozen binding.",
        )
        if not config_ok:
            blockers.append("BLOCKED_FROZEN_CONFIG_UNRECOVERABLE")

        prompt_ok = (job["prompt_json"] == canonical(operation_contract(job["operation_kind"]))
                     and job["prompt_sha256"] == operation_contract(job["operation_kind"])["prompt_bundle_sha256"]
                     and frozen is not None and prompt_digest() == frozen["basis"]["prompt_sha256"])
        dimensions["prompt_contract"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if prompt_ok else "FAIL",
            "Persisted operation contract and combined processing prompt digest.",
        )
        if not prompt_ok:
            blockers.append("BLOCKED_EXECUTION_CONTRACT_CHANGED")

        try:
            input_evidence = _validate_input_artifact(config, connection, job)
            input_ok = True
            evidence["input_artifact"] = input_evidence
        except Exception:
            input_ok = False
        dimensions["input_artifact_identity"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if input_ok else "FAIL",
            "Registered extraction piece file, payload, checkpoint and Job hashes.",
        )
        dimensions["extraction_piece_identity"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if input_ok else "FAIL",
            "The exact SOURCE_ANALYSIS_PIECE artifact and payload remain bound.",
        )
        if not input_ok:
            blockers.append("BLOCKED_INPUT_ARTIFACT_CHANGED")

        historical_runtime = json.loads(run["runtime_json"])
        target_runtime = (runtime_identity(cloud_profile.provider_adapter_version, workbench_schema_version=schema_version(connection))
                          if cloud_profile is not None else {})
        cloud_surface = _execution_surface_comparison(
            "cloud", historical_runtime.get("git_sha", ""),
        )
        evidence["cloud_execution_surface"] = cloud_surface
        cloud_comparison = _runtime_comparison(
            historical_runtime, target_runtime, _CLOUD_METADATA_FIELDS,
            surface_fields=_CLOUD_SURFACE_FIELDS,
            surface_compatible=cloud_surface["compatible"],
        )
        evidence["cloud_runtime"] = cloud_comparison
        cloud_ok = cloud_comparison["compatible"]
        dimensions["code_runtime_identity"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if cloud_ok else "FAIL",
            "Release metadata may differ; broad code digests may differ only when the versioned "
            "historical/target execution-surface AST evidence is exact.",
        )
        dimensions["workbench_schema_semantics"] = _dimension(
            "EXACT_IDENTITY_REQUIRED",
            "PASS" if historical_runtime.get("workbench_schema_version")
            == target_runtime.get("workbench_schema_version") else "FAIL",
            "workbench_schema_version is part of the semantic runtime comparison.",
        )
        dimensions["cloud_job_schema_semantics"] = _dimension(
            "EXACT_IDENTITY_REQUIRED",
            "PASS" if all(historical_runtime.get(name) == target_runtime.get(name) for name in (
                "cloud_contract_version", "provider_adapter_version",
            )) else "FAIL",
            "cloud_contract_version and provider adapter version are exact runtime fields.",
        )
        if not cloud_ok:
            blockers.append("BLOCKED_EXECUTION_CONTRACT_CHANGED")

        context_semantic_ok = False
        current_basis = None
        if config_ok and frozen is not None:
            try:
                worker = SourceOperations(config, source_profile, cloud_profile)
                if frozen["contract_version"] == "run-processing-context-v2":
                    current_basis = Domains(config).pending_basis(source, target_runtime, source_profile, cloud_profile)
                else:
                    current_basis = Domains(config).basis(
                        connection, source, target_runtime, source_profile, cloud_profile,
                        revision=frozen["basis"]["assignment_revision"],
                    )
                historical_basis = dict(frozen["basis"]); historical_basis.pop("runtime")
                target_basis = dict(current_basis); target_basis.pop("runtime")
                context_semantic_ok = canonical(historical_basis) == canonical(target_basis)
            except Exception:
                context_semantic_ok = False
        dimensions["domain_shared_core_processing_context"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if context_semantic_ok else "FAIL",
            "Frozen non-runtime basis is exact; runtime may differ only in release metadata.",
        )
        dimensions["domain_assignment_revision"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if context_semantic_ok else "FAIL",
            "Assigned contexts use the frozen revision; later assignments are irrelevant.",
        )
        dimensions["execution_policy"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if context_semantic_ok else "FAIL",
            "Frozen execution_policy is part of the exact non-runtime context basis.",
        )
        if not context_semantic_ok:
            blockers.append("BLOCKED_CONTEXT_SEMANTIC_DRIFT")

        native_ok = False
        native_comparison: dict[str, Any] = {}
        native_root = None
        if config_ok and frozen is not None:
            try:
                native_root = checked_path(phase4.root / run["native_root_relative"])
                identity = json.loads((native_root / "execution_identity.json").read_text(encoding="utf-8"))
                target_native = native_runtime()
                native_surface = _execution_surface_comparison(
                    "native", identity["runtime"].get("repository_commit", ""),
                )
                evidence["native_execution_surface"] = native_surface
                native_comparison = _runtime_comparison(
                    identity["runtime"], target_native, _NATIVE_METADATA_FIELDS,
                    surface_fields=_NATIVE_SURFACE_FIELDS,
                    surface_compatible=native_surface["compatible"],
                )
                evidence["native_runtime"] = native_comparison
                native_ok = native_comparison["compatible"]
            except Exception:
                native_ok = False
        dimensions["native_execution_checkpoint"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if native_ok else "FAIL",
            "Existing Phase4 identity/manifest/inventory checks plus metadata-only native runtime variance.",
        )
        if not native_ok:
            blockers.append("BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE")

        provider_fields = (
            "provider", "requested_model", "accepted_model_aliases_json", "provider_adapter_version",
            "timeout_seconds", "max_output_tokens", "max_calls", "max_attempts", "max_total_tokens",
            "retry_owner", "retry_policy_id",
        )
        for name in provider_fields:
            dimensions[name] = _dimension(
                "EXACT_IDENTITY_REQUIRED", "PASS" if config_ok else "FAIL",
                "Persisted Job column equals the canonical frozen CloudProfile identity.",
            )
        dimensions["retry_orchestration_semantics"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS",
            "Target-only, versioned append-only retry orchestration; never inferred from historical state.",
        )
        dimensions["extraction_parser_output_contract"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if cloud_ok and native_ok and prompt_ok else "FAIL",
            "Prompt identity is exact and historical/target provider, parser, validation and native "
            "execution-surface AST evidence is exact.",
        )
        evidence.update({
            "processing_run_id": run_id, "source_id": run["source_id"],
            "failed_attempt_id": failed_attempt_id, "failed_job_id": job["job_id"],
            "historical_context_sha256": frozen["context_sha256"] if frozen else None,
            "target_contract_sha256": compatibility_contract_sha256(),
        })

        if blockers:
            return _blocked(blockers, dimensions, evidence)

        created = now()
        dimensions_json = canonical(dimensions)
        evidence_json = canonical(evidence)
        record: dict[str, Any] = {
            "qualification_id": "RETRY_COMPAT_" + digest({
                "run": run_id, "attempt": failed_attempt_id,
                "target": target_runtime["runtime_sha256"], "contract": compatibility_contract_sha256(),
            })[:32].upper(),
            "processing_run_id": run_id, "source_id": run["source_id"],
            "failed_attempt_id": failed_attempt_id, "failed_job_id": job["job_id"],
            "historical_runtime_sha256": historical_runtime["runtime_sha256"],
            "target_runtime_sha256": target_runtime["runtime_sha256"],
            "historical_context_sha256": frozen["context_sha256"],
            "target_contract_version": CONTRACT_VERSION,
            "target_contract_sha256": compatibility_contract_sha256(),
            "dimensions_json": dimensions_json, "evidence_json": evidence_json,
            "evidence_sha256": digest(evidence), "qualification_result": "QUALIFIED",
            "reason": "ALL_REQUIRED_DIMENSIONS_COMPATIBLE", "created_at": created,
        }
        record["record_sha256"] = digest(_record_body(record))
        token = _validate_record(record)
        try:
            _compatible(native_root, run["native_execution_id"], phase4, RetryPolicy.FORBID_ALL,
                        runtime_compatibility=token)
        except Exception:
            dimensions["native_execution_checkpoint"]["result"] = "FAIL"
            return _blocked(["BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE"], dimensions, evidence)

    if persist:
        with Store(config).connect(operator_write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not installed(connection):
                raise RetryCompatibilityError("RETRY_COMPATIBILITY_SCHEMA_REQUIRED")
            prior = connection.execute(
                f"SELECT * FROM {TABLE} WHERE processing_run_id=? AND failed_attempt_id=? "
                "AND target_runtime_sha256=? AND target_contract_sha256=?",
                (run_id, failed_attempt_id, record["target_runtime_sha256"], record["target_contract_sha256"]),
            ).fetchone()
            if prior:
                token = _validate_record(prior)
                return {"status": "QUALIFIED", "qualification_result": "QUALIFIED",
                        "blockers": [], "reason": prior["reason"], "dimensions": dimensions,
                        "evidence": evidence, "record": dict(prior), "duplicate": True}
            names = tuple(record)
            connection.execute(
                f"INSERT INTO {TABLE}({','.join(names)}) VALUES({','.join('?' for _ in names)})",
                tuple(record[name] for name in names),
            )
    return {"status": "QUALIFIED", "qualification_result": "QUALIFIED", "blockers": [],
            "reason": record["reason"], "dimensions": dimensions, "evidence": evidence,
            "record": record, "duplicate": False}


def load_qualification(connection, *, run_id: str, failed_attempt_id: str,
                       source_id: str, failed_job_id: str,
                       historical_runtime_sha256: str,
                       target_runtime: Mapping[str, Any],
                       historical_context_sha256: str) -> _ValidatedQualification | None:
    if not installed(connection):
        return None
    row = connection.execute(
        f"SELECT * FROM {TABLE} WHERE processing_run_id=? AND source_id=? AND failed_attempt_id=? "
        "AND failed_job_id=? AND historical_runtime_sha256=? AND target_runtime_sha256=? "
        "AND historical_context_sha256=? AND target_contract_version=? AND target_contract_sha256=? "
        "ORDER BY created_at DESC LIMIT 1",
        (run_id, source_id, failed_attempt_id, failed_job_id, historical_runtime_sha256,
         target_runtime.get("runtime_sha256"), historical_context_sha256, CONTRACT_VERSION,
         compatibility_contract_sha256()),
    ).fetchone()
    if row is None:
        return None
    token = _validate_record(row)
    evidence = _evidence(token)
    if (evidence.get("processing_run_id") != run_id or evidence.get("source_id") != source_id
            or evidence.get("failed_attempt_id") != failed_attempt_id
            or evidence.get("failed_job_id") != failed_job_id):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_SCOPE_MISMATCH")
    return token
