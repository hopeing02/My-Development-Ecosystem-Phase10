from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Literal

from mde.config.project import load_project_config
from mde.exceptions import MDEError

ProjectPhase = Literal["test", "build"]
_CONTROL_TOKENS = frozenset({"|", "||", "&", "&&", ";", ">", ">>", "<"})


class ProjectCommandError(MDEError):
    """Raised when a configured project command is invalid or fails."""


@dataclass(frozen=True)
class ProjectCommandResult:
    command: tuple[str, ...]
    return_code: int
    output: str


def parse_project_command(value: str) -> tuple[str, ...]:
    if "\n" in value or "\r" in value:
        raise ProjectCommandError("Project commands must use a single line.")
    try:
        parsed = shlex.split(value, posix=sys.platform != "win32")
    except ValueError as error:
        raise ProjectCommandError(f"Invalid project command: {error}") from error
    command = tuple(
        (
            part[1:-1]
            if sys.platform == "win32"
            and len(part) >= 2
            and part[0] == part[-1]
            and part[0] in {'"', "'"}
            else part
        )
        for part in parsed
    )
    if not command:
        raise ProjectCommandError("Project command must not be empty.")
    if any(part in _CONTROL_TOKENS for part in command):
        raise ProjectCommandError(
            "Shell control operators are not allowed in project commands."
        )
    return command


def run_project_phase(
    repository_root: Path,
    phase: ProjectPhase,
    *,
    timeout_seconds: int = 900,
) -> tuple[ProjectCommandResult, ...]:
    root = repository_root.resolve()
    config = load_project_config(root)
    configured = getattr(config.commands, phase)
    results: list[ProjectCommandResult] = []

    for value in configured:
        command = parse_project_command(value)
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ProjectCommandError(
                f"Project {phase} command could not run: {' '.join(command)}: {error}"
            ) from error
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        result = ProjectCommandResult(command, completed.returncode, output)
        results.append(result)
        if completed.returncode != 0:
            detail = f"\n{output}" if output else ""
            raise ProjectCommandError(
                f"Project {phase} command failed with exit code "
                f"{completed.returncode}: {' '.join(command)}{detail}"
            )

    return tuple(results)
