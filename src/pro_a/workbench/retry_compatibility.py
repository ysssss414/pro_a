"""Bounded, fail-closed cross-release qualification for extraction retries."""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
from functools import lru_cache, partial
import hashlib
import json
import os
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
_BOUNDED_QUALIFICATION_EVENT = "BOUNDED_RETRY_COMPATIBILITY_QUALIFIED"
_CLOUD_METADATA_FIELDS = frozenset(("git_sha", "runtime_sha256"))
_NATIVE_METADATA_FIELDS = frozenset(("repository_commit",))
_CLOUD_SURFACE_FIELDS = frozenset(("domain_code_sha256", "phase4_processing_code_sha256"))
_NATIVE_SURFACE_FIELDS = frozenset(("processing_code_sha256",))
_CLOUD_EXECUTION_ROOTS = {
    "workbench/cloud_jobs.py": ("CloudJobs.run_once",),
    "workbench/source_operations.py": ("SourceOperations._advance_claimed",),
}
_CLOUD_EXECUTION_DEPENDENCIES = {
    "bounded_extraction.py": None,
    "evidence_binding.py": None,
    "source_analysis_wire.py": None,
    "bounded_source_analysis.py": None,
    "whole_piece_compact.py": None,
    "output_decomposition.py": None,
    "output_decomposition_legacy.py": None,
    "extraction_analysis_record.py": None,
    "workbench/output_decomposition.py": None,
    "source_analysis_provider_record.py": None,
    "workbench/whole_piece_raw.py": None,
    "processing_context.py": None,
    "workbench/bounded_source_analysis.py": None,
    "workbench/bounded_extraction_store.py": None,
    "workbench/bounded_extraction_persistence.py": None,
    "cloud_contract.py": None,
    "provider_diagnostics.py": None,
    "domain_packs.py": None,
    "run_context.py": None,
    "workbench/artifacts.py": None,
    "workbench/stage1_scale.py": None,
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
        "SourceOperations.__init__", "SourceOperations.start", "SourceOperations._event",
        "SourceOperations._start", "SourceOperations.start_qualification_reprocess",
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
        "workbench/bounded_resume.py": (
            "Target-only explicit operator boundary. It reuses the unchanged full-run "
            "execution defaults; its complete source is bound by the target contract digest."
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
    "workbench/bounded_resume.py",
    "workbench/truncation_recovery.py",
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

_FULL_SURFACE_STATEMENT_REPLACEMENTS = {
    "bounded_extraction.py": ((
        '''
roots = tuple(s for s in plan.segments if s.parent_segment_id is None)
root_count = (len(series.eligible_evidence_refs) + series.budget.initial_evidence_refs - 1) // series.budget.initial_evidence_refs
if len(roots) != root_count or tuple(s.stable_path for s in roots) != tuple((i,) for i in range(root_count)):
    raise BoundedExtractionError("INVALID_INITIAL_ASSIGNMENT")
''',
        '''
roots = initial_extraction_plan(series).segments
if tuple(s for s in plan.segments if s.parent_segment_id is None) != roots:
    raise BoundedExtractionError("INVALID_INITIAL_ASSIGNMENT")
''',
    ),),
    "workbench/bounded_source_analysis.py": ((
        '''
from .extraction_retry import bounded_attempt_for_dispatch
attempt = bounded_attempt_for_dispatch(
    self.ledger, segment.segment_id, owner, fence,
    payload_sha256=sha,
    configuration_sha256=identity(configuration),
)
''',
        '''
attempt = self.ledger.reserve_attempt(
    segment.segment_id, owner, fence, attempt_number=1,
    payload_sha256=sha,
    configuration_sha256=identity(configuration),
)
''',
    ),),
    "workbench/bounded_extraction_store.py": ((
        '''
if existing:
    _require(existing["attempt_id"] == attempt_id, "SEGMENT_ALREADY_ACCEPTED")
    target = ("SUCCEEDED_COMPLETE" if existing["result_type"] == "COMPLETE"
              else "SUBDIVISION_REQUIRED")
    if row["state"] not in (target, "SUPERSEDED_BY_CHILDREN"):
        _require(row["state"] in ("RUNNING", "RECOVERY_REQUIRED"),
                 "INVALID_SEGMENT_TRANSITION")
        connection.execute(
            "UPDATE bounded_extraction_segments SET state=?,updated_at=? "
            "WHERE segment_id=?", (target, _now(), row["segment_id"]),
        )
        _event(
            connection, row["series_id"],
            "SEGMENT_COMPLETED" if target == "SUCCEEDED_COMPLETE"
            else "SEGMENT_SUBDIVISION_REQUIRED",
            segment_id=row["segment_id"],
        )
    return dict(existing)
''',
        '''
if existing:
    _require(existing["attempt_id"] == attempt_id, "SEGMENT_ALREADY_ACCEPTED")
    return dict(existing)
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
    if selectors is None:
        if name == 'workbench/bounded_source_analysis.py':
            # Normalize only the opt-in subdivision argument whose full-run default
            # remains True, plus its exact plumbing and narrower-mode guards.
            runner = next((node for node in tree.body if isinstance(node,ast.ClassDef)
                           and node.name == 'BoundedSourceAnalysisRunner'),None)
            functions = [node for node in getattr(runner,'body',()) if isinstance(node,ast.FunctionDef)
                         and node.name in ('advance','_observe')]
            for function in functions:
                matches = [i for i,arg in enumerate(function.args.kwonlyargs)
                           if arg.arg == 'allow_new_subdivision'
                           and isinstance(function.args.kw_defaults[i],ast.Constant)
                           and function.args.kw_defaults[i].value is True]
                for i in reversed(matches):
                    del function.args.kwonlyargs[i]; del function.args.kw_defaults[i]
                for call in (item for item in ast.walk(function) if isinstance(item,ast.Call)):
                    if _call_name(call) == '_observe':
                        call.keywords = [kw for kw in call.keywords if not (kw.arg == 'allow_new_subdivision'
                                         and isinstance(kw.value,ast.Name) and kw.value.id == 'allow_new_subdivision')]
            for observe in (function for function in functions if function.name == '_observe'):
                for code in ('BOUNDED_TRUNCATION_STOP','BOUNDED_SUBDIVISION_FORBIDDEN'):
                    _replace_exact_statements(observe,f'_require(allow_new_subdivision, "{code}")','')
        for before, after in _FULL_SURFACE_STATEMENT_REPLACEMENTS.get(name, ()):
            _replace_exact_statements(tree, before, after)
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
        *, historical_repository_root: Path | None = None,
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    package = Path(__file__).resolve().parent.parent
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", historical_git_sha or ""):
        raise RetryCompatibilityError("HISTORICAL_GIT_IDENTITY_INVALID")
    if historical_repository_root is None:
        root = package.parents[1]
        if package != root / "src/pro_a":
            raise RetryCompatibilityError("HISTORICAL_EXECUTION_REPOSITORY_REQUIRED")
    else:
        root = Path(historical_repository_root)
    try:
        root = checked_path(root)
    except BoundaryError:
        raise RetryCompatibilityError("HISTORICAL_EXECUTION_REPOSITORY_UNAVAILABLE") from None
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}

    def git(*arguments, optional=False):
        result = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *arguments],
                                env=environment, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            if optional:
                return None
            raise RetryCompatibilityError("HISTORICAL_EXECUTION_SOURCE_UNAVAILABLE")
        return result.stdout

    if Path(git("rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve() != root:
        raise RetryCompatibilityError("HISTORICAL_EXECUTION_REPOSITORY_MISMATCH")
    if git("rev-parse", "--verify", historical_git_sha + "^{commit}").decode().strip() != historical_git_sha:
        raise RetryCompatibilityError("HISTORICAL_GIT_IDENTITY_MISMATCH")
    historical: dict[str, bytes] = {}
    target: dict[str, bytes] = {}
    for name in specification:
        repository_name = f"src/pro_a/{name}"
        object_id = git("rev-parse", "--verify", f"{historical_git_sha}:{repository_name}", optional=True)
        # Absence is a different execution surface, never a compatibility waiver.
        historical[name] = b""
        if object_id is not None:
            oid = object_id.decode().strip()
            content = git("cat-file", "blob", oid)
            algorithm = hashlib.sha1 if len(oid) == 40 else hashlib.sha256
            if algorithm(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() != oid:
                raise RetryCompatibilityError("HISTORICAL_EXECUTION_BLOB_INTEGRITY")
            historical[name] = content
        target[name] = (package / name).read_bytes()
    return historical, target


def _assess_execution_surface(kind: str, historical_git_sha: str, *,
                              historical_repository_root: Path | None = None) -> dict[str, Any]:
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
        historical, target = (_execution_surface_sources(historical_git_sha, specification)
            if historical_repository_root is None else _execution_surface_sources(
                historical_git_sha, specification, historical_repository_root=historical_repository_root))
        historical_manifest = _surface_manifest(historical, specification)
        target_manifest = _surface_manifest(target, specification)
    except (OSError, UnicodeError, subprocess.CalledProcessError, SyntaxError,
            RetryCompatibilityError) as exc:
        result["reason"] = f"EXECUTION_SURFACE_UNAVAILABLE:{type(exc).__name__}"
        if isinstance(exc, RetryCompatibilityError) and re.fullmatch(r"HISTORICAL_[A-Z_]+", str(exc)):
            result["history_source_error_code"] = str(exc)
        return result
    result.update({
        "historical": historical_manifest,
        "target": target_manifest,
        "compatible": historical_manifest["semantic_surface_sha256"]
        == target_manifest["semantic_surface_sha256"],
        "reason": "SEMANTIC_SURFACE_EXACT" if historical_manifest["semantic_surface_sha256"]
        == target_manifest["semantic_surface_sha256"] else "SEMANTIC_SURFACE_CHANGED",
        "historical_source_authority": "EXACT_GIT_COMMIT_TREE",
        "explicit_history_repository": historical_repository_root is not None,
    })
    return result


@lru_cache(maxsize=64)
def _execution_surface_comparison(kind: str, historical_git_sha: str) -> dict[str, Any]:
    return _assess_execution_surface(kind, historical_git_sha)


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
                               *, persist: bool = False,
                               historical_repository_root: Path | None = None) -> dict[str, Any]:
    """Assess immutable state; persist only an exact-scope QUALIFIED record."""
    from .cloud_jobs import runtime_identity
    from .extraction_retry import frozen_cloud
    from .source_operations import SourceOperations, SourceProfile

    dimensions: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    blockers: list[str] = []
    surface_comparison = (_execution_surface_comparison if historical_repository_root is None else
        partial(_assess_execution_surface, historical_repository_root=historical_repository_root))
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
        cloud_surface = surface_comparison(
            "cloud", historical_runtime.get("git_sha", ""),
        )
        evidence["cloud_execution_surface"] = cloud_surface
        cloud_comparison = _runtime_comparison(
            historical_runtime, target_runtime, _CLOUD_METADATA_FIELDS,
            surface_fields=_CLOUD_SURFACE_FIELDS,
            surface_compatible=cloud_surface["compatible"],
        )
        evidence["cloud_runtime"] = cloud_comparison
        cloud_ok = cloud_comparison["compatible"] and (
            historical_repository_root is None or cloud_surface["compatible"])
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
                native_surface = surface_comparison(
                    "native", identity["runtime"].get("repository_commit", ""),
                )
                evidence["native_execution_surface"] = native_surface
                native_comparison = _runtime_comparison(
                    identity["runtime"], target_native, _NATIVE_METADATA_FIELDS,
                    surface_fields=_NATIVE_SURFACE_FIELDS,
                    surface_compatible=native_surface["compatible"],
                )
                evidence["native_runtime"] = native_comparison
                native_ok = native_comparison["compatible"] and (
                    historical_repository_root is None or native_surface["compatible"])
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


def assess_bounded_retry_compatibility(config, run_id: str, failed_attempt_id: str,
                                       *, persist: bool = False,
                                       bounded_only_resume: bool = False,
                                       bounded_truncation_recovery: bool = False,
                                       historical_repository_root: Path | None = None) -> dict[str, Any]:
    """Qualify an exact-scope bounded Attempt; recovery is a separate opt-in."""
    from pro_a.evidence_binding import identity
    from .bounded_extraction_store import BoundedExtractionStore, _event
    from .cloud_jobs import runtime_identity
    from .extraction_retry import (
        _json_syntax_diagnostic, bounded_frozen_components,
    )
    from .source_operations import SourceOperations, build_source_providers

    if bounded_only_resume and bounded_truncation_recovery:
        raise RetryCompatibilityError('INCOMPATIBLE_QUALIFICATION_SCOPES')

    dimensions: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    blockers: list[str] = []
    surface_comparison = (_execution_surface_comparison if historical_repository_root is None else
        partial(_assess_execution_surface, historical_repository_root=historical_repository_root))
    ledger = BoundedExtractionStore(config)
    with Store(config).connect() as connection:
        if schema_version(connection) != "12":
            return _blocked(["BLOCKED_BOUNDED_SCHEMA_REQUIRED"], dimensions, evidence)
        run = connection.execute(
            "SELECT * FROM source_processing_runs WHERE processing_run_id=?", (run_id,),
        ).fetchone()
        attempt = connection.execute(
            "SELECT a.*,g.series_id,g.state AS segment_state,s.state AS series_state,"
            "s.processing_run_id AS series_run_id FROM bounded_extraction_attempts a "
            "JOIN bounded_extraction_segments g ON g.segment_id=a.segment_id "
            "JOIN bounded_extraction_series s ON s.series_id=g.series_id "
            "WHERE a.attempt_id=?", (failed_attempt_id,),
        ).fetchone()
        if run is None or attempt is None:
            return _blocked(["BLOCKED_HISTORICAL_SCOPE_UNAVAILABLE"], dimensions, evidence)
        series_id, segment_id = attempt["series_id"], attempt["segment_id"]
        try:
            series, plan, _, _ = ledger._load(connection, series_id)
            segment = next(item for item in plan.segments if item.segment_id == segment_id)
            chain_ok = True
        except Exception:
            series = plan = segment = None
            chain_ok = False
        outcome = connection.execute(
            "SELECT * FROM bounded_extraction_outcomes WHERE attempt_id=?",
            (failed_attempt_id,),
        ).fetchone()
        latest = connection.execute(
            "SELECT attempt_id,attempt_number FROM bounded_extraction_attempts "
            "WHERE segment_id=? ORDER BY attempt_number DESC LIMIT 1", (segment_id,),
        ).fetchone()
        failed = [json.loads(row[0]) for row in connection.execute(
            "SELECT body_json FROM bounded_extraction_events WHERE series_id=? "
            "AND event_type='SEGMENT_FAILED' ORDER BY sequence", (series_id,),
        )]
        results_absent = not any((
            connection.execute(
                "SELECT 1 FROM bounded_extraction_segment_results WHERE segment_id=?",
                (segment_id,),
            ).fetchone(),
            connection.execute(
                "SELECT 1 FROM bounded_extraction_series_results WHERE series_id=?",
                (series_id,),
            ).fetchone(),
            connection.execute(
                "SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?", (run_id,),
            ).fetchone(),
        ))
        scope_ok = (
            chain_ok and run["state"] == "BLOCKED" and run["stage"] == "ORCHESTRATION"
            and run["error_code"] == "BOUNDED_EXTRACTION_FAILED"
            and run["lease_owner"] is None and attempt["series_run_id"] == run_id
            and attempt["series_state"] == "FAILED" and attempt["segment_state"] == "FAILED"
            and attempt["attempt_number"] == 1 and latest is not None
            and latest["attempt_id"] == failed_attempt_id and outcome is not None
            and outcome["external_outcome"] == "SUCCEEDED"
            and outcome["classification"] == "SUCCEEDED"
            and outcome["finish_reason"] == "tool_calls"
            and type(outcome["output_tokens"]) is int
            and segment is not None and outcome["output_tokens"] < segment.max_output_tokens
            and any(item.get("attempt_id") == failed_attempt_id
                    and item.get("classification") == "INVALID_SEGMENT_RESPONSE"
                    for item in failed)
            and results_absent
        )
        if bounded_only_resume:
            from .bounded_resume import COMPLETE, contract as boundary_contract
            from .extraction_retry import _bounded_retry_events
            retries = [r for r in _bounded_retry_events(connection,run_id=run_id)
                       if r['retry_of_attempt_id'] == failed_attempt_id]
            accepted = connection.execute('SELECT * FROM bounded_extraction_segment_results WHERE segment_id=?',(segment_id,)).fetchone()
            no_semantic = not connection.execute('SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?',(run_id,)).fetchone()
            scope_ok = (
                chain_ok and run['state']=='EXTRACTION_PROCESSING'
                and run['stage'] in ('WHOLE_PIECE_OUTPUT_DECOMPOSITION',COMPLETE)
                and run['lease_owner'] is None and attempt['series_run_id']==run_id
                and attempt['series_state'] in ('OPEN','SUCCEEDED_COMPLETE')
                and attempt['segment_state']=='SUCCEEDED_COMPLETE' and attempt['attempt_number']==1
                and latest is not None and latest['attempt_number']==2
                and len(retries)==1 and retries[0]['retry_number']==1
                and retries[0]['retry_reason_code']=='MALFORMED_PROVIDER_JSON'
                and retries[0]['new_attempt_id']==latest['attempt_id']
                and accepted is not None and accepted['result_type']=='COMPLETE'
                and accepted['attempt_id']==latest['attempt_id'] and no_semantic
                and outcome is not None and outcome['external_outcome']=='SUCCEEDED'
                and outcome['classification']=='SUCCEEDED' and outcome['finish_reason']=='tool_calls'
                and any(item.get('attempt_id')==failed_attempt_id and item.get('classification')=='INVALID_SEGMENT_RESPONSE' for item in failed)
            )
            results_absent = no_semantic
            evidence['bounded_only_resume_boundary'] = boundary_contract()
        if bounded_truncation_recovery:
            from .truncation_recovery import _assessment, contract as recovery_contract
            scope_ok = False
            try:
                profile, cloud, _, _ = bounded_frozen_components(config, connection, run)
                scope_worker = SourceOperations(config, profile, cloud)
                bindings = scope_worker.output_batches.inputs(scope_worker.get_run(run_id))
                proof = _assessment(scope_worker, connection, run_id, failed_attempt_id, bindings)
                evidence['truncation_recovery_scope'] = proof
                evidence['truncation_recovery_boundary'] = recovery_contract()
                scope_ok = chain_ok and attempt['series_run_id'] == run_id and run['lease_owner'] is None
            except (ValueError, RuntimeError, OSError):
                pass
            results_absent = not connection.execute('SELECT 1 FROM source_processing_jobs WHERE processing_run_id=?', (run_id,)).fetchone()
        dimensions["historical_failed_scope"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if scope_ok else "FAIL",
            "Run, Series, Segment, Attempt, outcome and terminal failure are exactly bound.",
        )
        dimensions["no_downstream_semantic_work"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if results_absent else "FAIL",
            ("No Semantic Job exists; the uniquely accepted retry result is preserved."
             if bounded_only_resume else "No accepted target-Batch result, Series aggregate or semantic Job exists."),
        )
        if not scope_ok:
            return _blocked(["BLOCKED_HISTORICAL_SCOPE_INELIGIBLE"], dimensions, evidence)

        try:
            source_profile, cloud_profile, frozen, source = bounded_frozen_components(
                config, connection, run,
            )
            worker = SourceOperations(config, source_profile, cloud_profile)
            source_ok = checked_path(
                config.artifact_root / source["storage_relative"]
            ).is_file()
        except Exception:
            source_profile = cloud_profile = frozen = source = worker = None
            source_ok = False
        dimensions["source_identity"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if source_ok else "FAIL",
            "Frozen Source identity, bytes, local Phase4 path and model configuration are exact.",
        )
        dimensions["frozen_effective_configuration"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if source_ok else "FAIL",
            "The original digest-guarded SourceProfile and CloudProfile remain reconstructible.",
        )
        if not source_ok:
            blockers.append("BLOCKED_FROZEN_CONFIG_UNRECOVERABLE")

        diagnostic = None
        raw_ok = False
        if outcome is not None:
            try:
                content = ledger._read_artifact(
                    series_id, failed_attempt_id + ".raw.json", outcome,
                )
                envelope, body = ledger._decode_envelope(attempt, content)
                diagnostic = None if bounded_truncation_recovery else _json_syntax_diagnostic(body)
                raw_ok = (
                    envelope["http_status"] == 200
                    and (outcome['external_outcome'] == 'TRUNCATED' and envelope['finish_reason'] == 'length'
                         if bounded_truncation_recovery else diagnostic is not None)
                    and hashlib.sha256(content).hexdigest() == outcome["artifact_sha256"]
                )
            except Exception:
                raw_ok = False
        dimensions["immutable_provider_raw"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if raw_ok else "FAIL",
            "The immutable raw envelope is hash-bound and HTTP 200.",
        )
        dimensions['durable_truncation' if bounded_truncation_recovery else "malformed_json_syntax_only"] = _dimension(
            "EXACT_IDENTITY_REQUIRED", "PASS" if (raw_ok if bounded_truncation_recovery else diagnostic is not None) else "FAIL",
            ("Durable TRUNCATED outcome and length finish; partial JSON is never parsed."
             if bounded_truncation_recovery else "Strict UTF-8 decoding succeeds and json.loads fails with JSONDecodeError."),
        )
        if not raw_ok:
            blockers.append('BLOCKED_FAILURE_NOT_TRUNCATION' if bounded_truncation_recovery else "BLOCKED_FAILURE_NOT_MALFORMED_PROVIDER_JSON")

        input_ok = prompt_ok = provider_ok = False
        if worker is not None:
            try:
                bindings = worker.output_batches.inputs(worker.get_run(run_id))
                matches = [item for item in bindings if item[3].series_id == series_id]
                if len(matches) != 1:
                    raise ValueError()
                value, context, catalog, bound_series = matches[0]
                binding = next(
                    json.loads(row[0]) for row in connection.execute(
                        "SELECT event_json FROM source_processing_events "
                        "WHERE processing_run_id=? AND event_type='BOUNDED_EXTRACTION_SERIES_BOUND'",
                        (run_id,),
                    ) if json.loads(row[0]).get("series_id") == series_id
                )
                source_input = connection.execute(
                    "SELECT * FROM source_cloud_inputs WHERE artifact_id=?",
                    (binding["cloud_input_artifact_id"],),
                ).fetchone()
                input_content = worker.artifacts.resolve(
                    source_input["artifact_relative"],
                ).read_bytes()
                input_ok = (
                    hashlib.sha256(input_content).hexdigest() == source_input["sha256"]
                    and bound_series == series and context.piece.piece_id == binding["source_piece_id"]
                    and binding["series_sha256"] == series.series_sha256
                )
                payload = worker.output_batches.segment_payload(
                    value, context, catalog, series, segment,
                )
                prompt_content = canonical(payload).encode("utf-8")
                prompt_path = ledger._path(series_id, segment_id + ".prompt.json")
                request = json.loads(attempt["request_json"])
                prompt_ok = (
                    prompt_path.read_bytes() == prompt_content
                    and hashlib.sha256(prompt_content).hexdigest() == request["payload_sha256"]
                    and identity(request) == attempt["request_sha256"]
                    and request == ledger._request(
                        series, segment, request["payload_sha256"],
                        attempt["configuration_sha256"],
                    )
                )
                providers = build_source_providers(
                    load_config(source_profile.phase4_config_path).llm, worker.jobs.profile,
                )
                provider_ok = (
                    identity(providers[worker.output_batches.operation].configuration())
                    == attempt["configuration_sha256"]
                )
                evidence["input_artifact"] = {
                    "artifact_id": source_input["artifact_id"],
                    "sha256": source_input["sha256"], "ordinal": source_input["ordinal"],
                    "series_sha256": series.series_sha256,
                }
            except Exception:
                input_ok = prompt_ok = provider_ok = False
        for name, ok, description in (
            ("input_artifact_identity", input_ok,
             "The exact bounded Batch input artifact and Series binding remain intact."),
            ("segment_prompt_identity", prompt_ok,
             "The exact Segment prompt bytes and request identity remain intact."),
            ("provider_configuration_identity", provider_ok,
             "The reconstructed provider configuration digest equals Attempt 1."),
        ):
            dimensions[name] = _dimension(
                "EXACT_IDENTITY_REQUIRED", "PASS" if ok else "FAIL", description,
            )
        if not input_ok or not prompt_ok or not provider_ok:
            blockers.append("BLOCKED_INPUT_ARTIFACT_CHANGED")

        historical_runtime = json.loads(run["runtime_json"])
        target_runtime = (
            runtime_identity(
                cloud_profile.provider_adapter_version,
                workbench_schema_version=schema_version(connection),
            ) if cloud_profile is not None else {}
        )
        cloud_surface = surface_comparison(
            "cloud", historical_runtime.get("git_sha", ""),
        )
        evidence["cloud_execution_surface"] = cloud_surface
        cloud_comparison = _runtime_comparison(
            historical_runtime, target_runtime, _CLOUD_METADATA_FIELDS,
            surface_fields=_CLOUD_SURFACE_FIELDS,
            surface_compatible=cloud_surface["compatible"],
        )
        evidence["cloud_runtime"] = cloud_comparison
        cloud_ok = cloud_comparison["compatible"] and (
            historical_repository_root is None or cloud_surface["compatible"])
        dimensions["code_runtime_identity"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if cloud_ok else "FAIL",
            "Only release metadata or AST-proven equivalent execution-surface changes may differ.",
        )
        if not cloud_ok:
            blockers.append("BLOCKED_EXECUTION_CONTRACT_CHANGED")

        context_ok = False
        if worker is not None and frozen is not None:
            try:
                if frozen["contract_version"] == "run-processing-context-v2":
                    current_basis = Domains(config).pending_basis(
                        source, target_runtime, source_profile, cloud_profile,
                    )
                else:
                    current_basis = Domains(config).basis(
                        connection, source, target_runtime, source_profile, cloud_profile,
                        revision=frozen["basis"]["assignment_revision"],
                    )
                historical_basis = dict(frozen["basis"]); historical_basis.pop("runtime")
                target_basis = dict(current_basis); target_basis.pop("runtime")
                context_ok = canonical(historical_basis) == canonical(target_basis)
            except Exception:
                context_ok = False
        dimensions["domain_shared_core_processing_context"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if context_ok else "FAIL",
            "The frozen non-runtime processing context is exact.",
        )
        if not context_ok:
            blockers.append("BLOCKED_CONTEXT_SEMANTIC_DRIFT")

        native_ok = False
        native_root = phase4 = None
        if worker is not None:
            try:
                phase4 = load_config(source_profile.phase4_config_path)
                native_root = checked_path(phase4.root / run["native_root_relative"])
                native_identity = json.loads(
                    (native_root / "execution_identity.json").read_text(encoding="utf-8")
                )
                target_native = native_runtime()
                native_surface = surface_comparison(
                    "native", native_identity["runtime"].get("repository_commit", ""),
                )
                native_comparison = _runtime_comparison(
                    native_identity["runtime"], target_native, _NATIVE_METADATA_FIELDS,
                    surface_fields=_NATIVE_SURFACE_FIELDS,
                    surface_compatible=native_surface["compatible"],
                )
                evidence["native_execution_surface"] = native_surface
                evidence["native_runtime"] = native_comparison
                native_ok = native_comparison["compatible"] and (
                    historical_repository_root is None or native_surface["compatible"])
            except Exception:
                native_ok = False
        dimensions["native_execution_checkpoint"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS" if native_ok else "FAIL",
            "The frozen Phase4 checkpoint and native execution surface remain compatible.",
        )
        if not native_ok:
            blockers.append("BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE")

        dimensions["retry_orchestration_semantics"] = _dimension(
            "SEMANTIC_COMPATIBILITY_ALLOWED", "PASS",
            ("Target-only explicit recovery reuses the same engine, performs one subdivision and zero calls."
             if bounded_truncation_recovery else "Target-only authorization reuses the append-only bounded ledger and permits one retry."),
        )
        evidence.update({
            "processing_run_id": run_id, "source_id": run["source_id"],
            "failed_attempt_id": failed_attempt_id, "failed_job_id": segment_id,
            "bounded_series_id": series_id, "bounded_segment_id": segment_id,
            "historical_context_sha256": frozen["context_sha256"] if frozen else None,
            "target_contract_sha256": compatibility_contract_sha256(),
            "malformed_json_diagnostic": diagnostic,
        })
        if blockers:
            return _blocked(blockers, dimensions, evidence)

        created = now()
        record: dict[str, Any] = {
            "qualification_id": "BOUNDED_RETRY_COMPAT_" + digest({
                "run": run_id, "attempt": failed_attempt_id,
                "target": target_runtime["runtime_sha256"],
                "contract": compatibility_contract_sha256(),
            })[:32].upper(),
            "processing_run_id": run_id, "source_id": run["source_id"],
            "failed_attempt_id": failed_attempt_id, "failed_job_id": segment_id,
            "historical_runtime_sha256": historical_runtime["runtime_sha256"],
            "target_runtime_sha256": target_runtime["runtime_sha256"],
            "historical_context_sha256": frozen["context_sha256"],
            "target_contract_version": CONTRACT_VERSION,
            "target_contract_sha256": compatibility_contract_sha256(),
            "dimensions_json": canonical(dimensions), "evidence_json": canonical(evidence),
            "evidence_sha256": digest(evidence), "qualification_result": "QUALIFIED",
            "reason": "ALL_REQUIRED_DIMENSIONS_COMPATIBLE", "created_at": created,
        }
        record["record_sha256"] = digest(_record_body(record))
        token = _validate_record(record)
        try:
            guard_cloud_runtime(historical_runtime, target_runtime, token)
            guard_context(frozen, current_basis, token)
            _compatible(
                native_root, run["native_execution_id"], phase4, RetryPolicy.FORBID_ALL,
                runtime_compatibility=token,
            )
        except Exception:
            dimensions["native_execution_checkpoint"]["result"] = "FAIL"
            return _blocked(["BLOCKED_NATIVE_CHECKPOINT_INCOMPATIBLE"], dimensions, evidence)

    if persist:
        with ledger._connection(True) as connection:
            ledger._load(connection, series_id)
            existing = []
            for row in connection.execute(
                    "SELECT body_json FROM bounded_extraction_events WHERE series_id=? "
                    "AND event_type=? ORDER BY sequence", (series_id, _BOUNDED_QUALIFICATION_EVENT)):
                value = json.loads(row[0]).get("record")
                if (value and value.get("failed_attempt_id") == failed_attempt_id
                        and value.get("target_runtime_sha256") == record["target_runtime_sha256"]
                        and value.get("target_contract_sha256") == record["target_contract_sha256"]):
                    existing.append(value)
            if len(existing) > 1:
                raise RetryCompatibilityError("RETRY_COMPATIBILITY_SCOPE_MISMATCH")
            if existing:
                prior = _validate_record(existing[0]).record
                return {
                    "status": "QUALIFIED", "qualification_result": "QUALIFIED",
                    "blockers": [], "reason": prior["reason"], "dimensions": dimensions,
                    "evidence": json.loads(prior["evidence_json"]),
                    "record": dict(prior), "duplicate": True,
                }
            _event(connection, series_id, _BOUNDED_QUALIFICATION_EVENT, record=record)
    return {
        "status": "QUALIFIED", "qualification_result": "QUALIFIED", "blockers": [],
        "reason": record["reason"], "dimensions": dimensions, "evidence": evidence,
        "record": record, "duplicate": False,
    }


def load_bounded_qualification(connection, *, run_id: str, failed_attempt_id: str,
                               segment_id: str, series_id: str, source_id: str,
                               historical_runtime_sha256: str,
                               target_runtime: Mapping[str, Any],
                               historical_context_sha256: str) -> _ValidatedQualification | None:
    """Load only an immutable, exact-scope bounded qualification event."""
    from pro_a.evidence_binding import identity

    series = connection.execute(
        "SELECT processing_run_id FROM bounded_extraction_series WHERE series_id=?",
        (series_id,),
    ).fetchone()
    attempt = connection.execute(
        "SELECT segment_id FROM bounded_extraction_attempts WHERE attempt_id=?",
        (failed_attempt_id,),
    ).fetchone()
    if (series is None or series[0] != run_id or attempt is None or attempt[0] != segment_id):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_SCOPE_MISMATCH")
    previous = "0" * 64
    records = []
    for sequence, row in enumerate(connection.execute(
            "SELECT * FROM bounded_extraction_events WHERE series_id=? ORDER BY sequence",
            (series_id,)), 1):
        value = dict(row)
        event_sha256 = value.pop("event_sha256")
        if (value["sequence"] != sequence or value["previous_sha256"] != previous
                or identity(value) != event_sha256):
            raise RetryCompatibilityError("RETRY_COMPATIBILITY_EVENT_CHAIN_MISMATCH")
        previous = event_sha256
        if value["event_type"] == _BOUNDED_QUALIFICATION_EVENT:
            record = json.loads(value["body_json"]).get("record")
            if (record and record.get("processing_run_id") == run_id
                    and record.get("source_id") == source_id
                    and record.get("failed_attempt_id") == failed_attempt_id
                    and record.get("failed_job_id") == segment_id
                    and record.get("historical_runtime_sha256") == historical_runtime_sha256
                    and record.get("target_runtime_sha256") == target_runtime.get("runtime_sha256")
                    and record.get("historical_context_sha256") == historical_context_sha256
                    and record.get("target_contract_version") == CONTRACT_VERSION
                    and record.get("target_contract_sha256") == compatibility_contract_sha256()):
                records.append(record)
    if not records:
        return None
    if len(records) != 1:
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_SCOPE_MISMATCH")
    token = _validate_record(records[0])
    bounded = _evidence(token)
    if (bounded.get("bounded_series_id") != series_id
            or bounded.get("bounded_segment_id") != segment_id):
        raise RetryCompatibilityError("RETRY_COMPATIBILITY_SCOPE_MISMATCH")
    return token
