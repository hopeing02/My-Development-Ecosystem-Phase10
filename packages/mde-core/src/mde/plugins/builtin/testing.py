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
    """Raised when the configured test process exits unsuccessfully."""

    __test__ = False


@dataclass(frozen=True)
class TestRunResult:
    command: tuple[str, ...]
    return_code: int
    passed: int | None
    failed: int | None
    log_path: Path


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


def run_tests(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
    configured = step.args.get("command", context.data.get("testing_command"))
    command = _normalize_command(configured)
    timeout = step.timeout or int(step.args.get("timeout", 900))
    log_dir = context.repository_root / "logs" / "tests"
    log_dir.mkdir(parents=True, exist_ok=True)
    label = context.task_id or context.workflow_name
    log_path = log_dir / f"{label}-{step.id}.log"

    completed = subprocess.run(
        command,
        cwd=context.repository_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    log_path.write_text(output, encoding="utf-8")
    passed = _count(r"(\d+) passed", output)
    failed = _count(r"(\d+) failed", output)

    result = TestRunResult(
        command=command,
        return_code=completed.returncode,
        passed=passed,
        failed=failed,
        log_path=log_path,
    )
    if completed.returncode != 0:
        raise TestExecutionError(
            f"Tests failed with exit code {completed.returncode}. Log: {log_path}"
        )
    return {
        "message": "Tests passed.",
        "command": list(result.command),
        "return_code": result.return_code,
        "passed": result.passed,
        "failed": result.failed,
        "log_path": str(result.log_path),
    }


class TestingWorkflowPlugin:
    name = "testing"

    def register(self, registry: CommandRegistry) -> None:
        registry.register("test.run", run_tests)
