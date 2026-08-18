from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from pro_a.acceptance_preflight import (
    CanaryResult,
    resolve_fresh_pytest_basetemp,
    run_deterministic_pytest_probe,
    writable_canary,
)


def completed(returncode: int, *, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_stale_fixed_temp_path_does_not_affect_fresh_unique_preflight(tmp_path: Path):
    preferred = tmp_path / "preferred"
    stale = preferred / "preflight_pytest_tmp"
    preferred.mkdir(parents=True)
    stale.write_text("historical inaccessible path", encoding="utf-8")

    resolution = resolve_fresh_pytest_basetemp(
        preferred,
        fallback_root=tmp_path / "fallback",
        name_factory=lambda: "fresh_probe",
    )

    assert resolution.success is True
    assert resolution.resolved_path == str(preferred.resolve() / "pytest_fresh_probe")
    assert Path(resolution.resolved_path) != stale
    assert stale.read_text(encoding="utf-8") == "historical inaccessible path"


def test_writable_canary_create_write_rename_delete(tmp_path: Path):
    result = writable_canary(tmp_path / "fresh")

    assert result.success is True
    assert result.operations == [
        "create_directory",
        "create_write_file",
        "rename_file",
        "delete_file",
    ]
    assert list((tmp_path / "fresh").iterdir()) == []


def test_preferred_permission_failure_uses_explicit_audited_user_temp_fallback(
    tmp_path: Path,
):
    preferred = (tmp_path / "preferred").resolve()
    fallback = (tmp_path / "fallback").resolve()

    def canary(path: Path) -> CanaryResult:
        if path.parent == preferred:
            return CanaryResult(
                path=str(path), success=False, error_type="PermissionError",
                error="[WinError 5] Access is denied", permission_error=True,
            )
        return writable_canary(path)

    resolution = resolve_fresh_pytest_basetemp(
        preferred,
        fallback_root=fallback,
        name_factory=iter(("preferred_id", "fallback_id")).__next__,
        canary=canary,
    )

    assert resolution.success is True
    assert resolution.fallback_used is True
    assert resolution.selected_root_kind == "windows_user_temp_fallback"
    assert resolution.resolved_path == str(fallback / "pytest_fallback_id")
    assert "PermissionError" in resolution.fallback_reason
    assert [item.success for item in resolution.canary_attempts] == [False, True]


def test_unique_basetemp_is_passed_explicitly_to_each_pytest_subprocess(tmp_path: Path):
    commands: list[list[str]] = []
    names = iter(("probe_one", "probe_two"))

    def runner(command, **_kwargs):
        commands.append(command)
        return completed(0, stdout="1 passed")

    results = [
        run_deterministic_pytest_probe(
            tmp_path, ["tests/test_example.py::test_case"], tmp_path / "preferred",
            fallback_temp_root=tmp_path / "fallback", name_factory=names.__next__,
            subprocess_runner=runner,
        )
        for _ in range(2)
    ]

    basetemps = [next(arg for arg in command if arg.startswith("--basetemp=")) for command in commands]
    assert basetemps == [
        f"--basetemp={tmp_path.resolve() / 'preferred' / 'pytest_probe_one'}",
        f"--basetemp={tmp_path.resolve() / 'preferred' / 'pytest_probe_two'}",
    ]
    assert basetemps[0] != basetemps[1]
    assert all(result.passed for result in results)


@pytest.mark.parametrize(
    ("exit_code", "expected_passed", "expected_decision"),
    [(0, True, "PASS"), (1, False, "LAUNCH_GATE_BLOCKER")],
)
def test_only_zero_pytest_exit_code_passes_probe(
    tmp_path: Path, exit_code: int, expected_passed: bool, expected_decision: str,
):
    result = run_deterministic_pytest_probe(
        tmp_path, ["tests/test_example.py::test_case"], tmp_path / "preferred",
        fallback_temp_root=tmp_path / "fallback", name_factory=lambda: "exit_code_probe",
        subprocess_runner=lambda *_args, **_kwargs: completed(exit_code),
    )

    assert result.pytest_exit_code == exit_code
    assert result.passed is expected_passed
    assert result.decision == expected_decision


def test_pytest_permission_error_is_blocker_with_diagnostic_not_false_pass(tmp_path: Path):
    result = run_deterministic_pytest_probe(
        tmp_path, ["tests/test_example.py::test_case"], tmp_path / "preferred",
        fallback_temp_root=tmp_path / "fallback", name_factory=lambda: "denied_probe",
        subprocess_runner=lambda *_args, **_kwargs: completed(
            1, stderr="PermissionError: [WinError 5] Access is denied",
        ),
    )

    assert result.passed is False
    assert result.decision == "LAUNCH_GATE_BLOCKER"
    assert result.permission_error_detected is True
    assert result.permission_error_diagnostic == [
        "PermissionError: [WinError 5] Access is denied"
    ]


def test_canary_permission_failure_on_both_roots_blocks_without_running_pytest(
    tmp_path: Path,
):
    pytest_started = False

    def denied(path: Path) -> CanaryResult:
        return CanaryResult(
            path=str(path), success=False, error_type="PermissionError",
            error="[WinError 5] 拒绝访问", permission_error=True,
        )

    def runner(*_args, **_kwargs):
        nonlocal pytest_started
        pytest_started = True
        return completed(0)

    result = run_deterministic_pytest_probe(
        tmp_path, ["tests/test_example.py::test_case"], tmp_path / "preferred",
        fallback_temp_root=tmp_path / "fallback", name_factory=iter(("one", "two")).__next__,
        canary=denied, subprocess_runner=runner,
    )

    assert pytest_started is False
    assert result.pytest_exit_code is None
    assert result.passed is False
    assert result.decision == "LAUNCH_GATE_BLOCKER"
    assert result.permission_error_detected is True
    assert len(result.temp_resolution.canary_attempts) == 2
