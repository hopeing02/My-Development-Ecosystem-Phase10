from __future__ import annotations

import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


class TestExecutionError(RuntimeError):
    """Raised when formatting, linting, or tests fail."""

    __test__ = False


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    return_code: int
    output: str


def _normalize_command(value: object) -> tuple[str, ...]:
    if value is None:
        return (sys.executable, "-m", "pytest")
    if isinstance(value, str):
        return tuple(shlex.split(value, posix=sys.platform != "win32"))
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        command = tuple(str(part) for part in value)
        if command:
            return command
    raise ValueError("testing command must be a non-empty string or sequence.")


def _count(pattern: str, output: str) -> int | None:
    match = re.search(pattern, output)
    return int(match.group(1)) if match else None


def _run(command: tuple[str, ...], root: Path, timeout: int) -> ProcessResult:
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return ProcessResult(command, completed.returncode, output)


def run_tests(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
    """Auto-fix safe Ruff issues, then lint and run the project tests.

    A remaining failure raises TestExecutionError. The existing Agent fix loop then
    invokes ai.fix, reapplies the generated patch, and executes this step again.
    """
    root = context.repository_root
    timeout = step.timeout or int(step.args.get("timeout", 900))
    configured = step.args.get("command", context.data.get("testing_command"))
    test_command = _normalize_command(configured)
    quality_enabled = bool(step.args.get("quality", configured is None))
    quality_commands = (
        ("uv", "run", "ruff", "check", ".", "--fix"),
        ("uv", "run", "ruff", "format", "."),
        ("uv", "run", "ruff", "check", "."),
    )
    commands = quality_commands + (test_command,) if quality_enabled else (test_command,)

    log_dir = root / "logs" / "tests"
    log_dir.mkdir(parents=True, exist_ok=True)
    label = context.task_id or context.workflow_name
    log_path = log_dir / f"{label}-{step.id}.log"
    sections: list[str] = []
    results: list[ProcessResult] = []

    for command in commands:
        result = _run(command, root, timeout)
        results.append(result)
        sections.append(f"$ {' '.join(command)}\n{result.output}")
        if result.return_code != 0:
            log_path.write_text("\n\n".join(sections), encoding="utf-8")
            phase = "Quality command" if command != test_command else "Tests"
            context.data["last_test_error"] = (
                f"{phase} failed with exit code {result.return_code}: "
                f"{' '.join(command)}. Log: {log_path}"
            )
            raise TestExecutionError(context.data["last_test_error"])

    log_path.write_text("\n\n".join(sections), encoding="utf-8")
    test_output = results[-1].output
    return {
        "message": "Ruff auto-fix, lint, and tests passed.",
        "commands": [list(result.command) for result in results],
        "return_code": 0,
        "passed": _count(r"(\d+) passed", test_output),
        "failed": _count(r"(\d+) failed", test_output),
        "log_path": str(log_path),
    }


class TestingWorkflowPlugin:
    name = "testing"

    def register(self, registry: CommandRegistry) -> None:
        registry.register("test.run", run_tests)
