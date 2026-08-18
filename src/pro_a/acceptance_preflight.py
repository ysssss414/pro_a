from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


PERMISSION_ERROR_RE = re.compile(r"PermissionError|WinError\s*5|Access is denied|拒绝访问", re.IGNORECASE)


@dataclass
class CanaryResult:
    path: str
    success: bool
    operations: list[str] = field(default_factory=list)
    error_type: str = ""
    error: str = ""
    permission_error: bool = False


@dataclass
class TempResolution:
    success: bool
    resolved_path: str = ""
    selected_root: str = ""
    selected_root_kind: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""
    canary_attempts: list[CanaryResult] = field(default_factory=list)


@dataclass
class ProbeResult:
    decision: str
    passed: bool
    started_at: str
    finished_at: str
    temp_resolution: TempResolution
    command: list[str]
    pytest_exit_code: int | None
    stdout_tail: str
    stderr_tail: str
    permission_error_detected: bool
    permission_error_diagnostic: list[str]
    cleanup_succeeded: bool | None
    cleanup_error: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def windows_user_temp_root() -> Path:
    return Path(tempfile.gettempdir()).resolve() / "pro_a_r1_acceptance_preflight"


def writable_canary(path: Path) -> CanaryResult:
    result = CanaryResult(path=str(path), success=False)
    canary = path / "writable_canary.tmp"
    renamed = path / "writable_canary.renamed"
    try:
        path.mkdir(parents=True, exist_ok=False)
        result.operations.append("create_directory")
        canary.write_bytes(b"pro_a_r1_preflight_canary\n")
        result.operations.append("create_write_file")
        canary.replace(renamed)
        result.operations.append("rename_file")
        renamed.unlink()
        result.operations.append("delete_file")
        result.success = True
    except Exception as exc:
        result.error_type = type(exc).__name__
        result.error = str(exc)
        result.permission_error = isinstance(exc, PermissionError) or bool(
            PERMISSION_ERROR_RE.search(str(exc))
        )
    return result


def resolve_fresh_pytest_basetemp(
    preferred_root: Path,
    *,
    fallback_root: Path | None = None,
    name_factory: Callable[[], str] | None = None,
    canary: Callable[[Path], CanaryResult] = writable_canary,
) -> TempResolution:
    preferred_root = Path(preferred_root).resolve()
    fallback_root = Path(fallback_root or windows_user_temp_root()).resolve()
    name_factory = name_factory or (lambda: uuid.uuid4().hex)
    attempts: list[CanaryResult] = []
    preferred_failure = ""

    roots = [("preferred", preferred_root)]
    if fallback_root != preferred_root:
        roots.append(("windows_user_temp_fallback", fallback_root))

    for root_kind, root in roots:
        candidate = root / f"pytest_{name_factory()}"
        result = canary(candidate)
        attempts.append(result)
        if result.success:
            return TempResolution(
                success=True,
                resolved_path=str(candidate),
                selected_root=str(root),
                selected_root_kind=root_kind,
                fallback_used=root_kind != "preferred",
                fallback_reason=preferred_failure if root_kind != "preferred" else "",
                canary_attempts=attempts,
            )
        if root_kind == "preferred":
            preferred_failure = f"{result.error_type}: {result.error}".strip(": ")

    return TempResolution(
        success=False,
        fallback_used=len(roots) > 1,
        fallback_reason=preferred_failure,
        canary_attempts=attempts,
    )


def permission_diagnostics(*values: str) -> list[str]:
    lines: list[str] = []
    for value in values:
        for line in value.splitlines():
            if PERMISSION_ERROR_RE.search(line) and line not in lines:
                lines.append(line[-1000:])
    return lines


def write_probe_audit(path: Path, result: ProbeResult) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_deterministic_pytest_probe(
    project_root: Path,
    test_targets: Sequence[str],
    preferred_temp_root: Path,
    *,
    fallback_temp_root: Path | None = None,
    python_executable: Path | str = sys.executable,
    audit_path: Path | None = None,
    name_factory: Callable[[], str] | None = None,
    canary: Callable[[Path], CanaryResult] = writable_canary,
    subprocess_runner: Callable[..., Any] = subprocess.run,
) -> ProbeResult:
    started_at = utc_now()
    resolution = resolve_fresh_pytest_basetemp(
        preferred_temp_root,
        fallback_root=fallback_temp_root,
        name_factory=name_factory,
        canary=canary,
    )
    command: list[str] = []
    exit_code: int | None = None
    stdout = ""
    stderr = ""
    cleanup_succeeded: bool | None = None
    cleanup_error = ""

    if resolution.success:
        command = [
            str(python_executable),
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={resolution.resolved_path}",
            *test_targets,
        ]
        try:
            completed = subprocess_runner(
                command,
                cwd=Path(project_root),
                text=True,
                capture_output=True,
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
        except Exception as exc:
            stderr = f"{type(exc).__name__}: {exc}"

        try:
            shutil.rmtree(resolution.resolved_path)
            cleanup_succeeded = True
        except FileNotFoundError:
            cleanup_succeeded = True
        except Exception as exc:
            cleanup_succeeded = False
            cleanup_error = f"{type(exc).__name__}: {exc}"

    canary_errors = "\n".join(
        f"{item.error_type}: {item.error}" for item in resolution.canary_attempts if item.error
    )
    diagnostic = permission_diagnostics(stdout, stderr, canary_errors, cleanup_error)
    passed = resolution.success and exit_code == 0
    result = ProbeResult(
        decision="PASS" if passed else "LAUNCH_GATE_BLOCKER",
        passed=passed,
        started_at=started_at,
        finished_at=utc_now(),
        temp_resolution=resolution,
        command=command,
        pytest_exit_code=exit_code,
        stdout_tail=stdout[-8000:],
        stderr_tail=stderr[-8000:],
        permission_error_detected=bool(diagnostic),
        permission_error_diagnostic=diagnostic,
        cleanup_succeeded=cleanup_succeeded,
        cleanup_error=cleanup_error,
    )
    if audit_path is not None:
        write_probe_audit(audit_path, result)
    return result
