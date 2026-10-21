"""Run one Codex development task, then check paths and validation results."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

import psutil

from mde.codex_capture.security import redact_text
from mde.git.repository import (
    GitError,
    ensure_clean_worktree,
    ensure_repository,
    get_local_head,
)


class CodexDevelopmentError(RuntimeError):
    """The task failed its execution or input contract."""


@dataclass(frozen=True)
class DevelopmentTask:
    task_id: str
    step_id: str
    project_path: Path
    requirement: str
    allowed_files: tuple[str, ...]
    validation_commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int = 1800


@dataclass(frozen=True)
class ValidationResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def _normalize_repo_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if (
        not parts
        or normalized.startswith("/")
        or PureWindowsPath(normalized).drive
        or any(part == ".." or ":" in part or "\x00" in part for part in parts)
        or any(part.endswith((" ", ".")) for part in parts)
        or any(part.casefold() == ".git" for part in parts)
        or any(PureWindowsPath(part).is_reserved() for part in parts)
    ):
        raise CodexDevelopmentError(f"Invalid repository-relative path: {value!r}")
    return "/".join(parts) + ("/" if normalized.endswith("/") else "")


def _load_task(path: Path) -> DevelopmentTask:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise CodexDevelopmentError("DevelopmentTask must be a JSON object")
    for field in ("taskId", "stepId", "projectPath", "requirement"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise CodexDevelopmentError(f"{field} must be a non-empty string")
    for field in ("taskId", "stepId"):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", data[field]):
            raise CodexDevelopmentError(f"{field} must be a safe identifier")
    project_path = Path(data["projectPath"]).expanduser()
    if not project_path.is_absolute() or not project_path.is_dir():
        raise CodexDevelopmentError(
            "projectPath must be an existing absolute directory"
        )
    project_path = project_path.resolve()
    raw_allowed = data.get("allowedFiles")
    if (
        not isinstance(raw_allowed, list)
        or not raw_allowed
        or not all(isinstance(item, str) for item in raw_allowed)
    ):
        raise CodexDevelopmentError("allowedFiles must be a non-empty string array")
    allowed_files = tuple(dict.fromkeys(map(_normalize_repo_path, raw_allowed)))
    for allowed in allowed_files:
        target = project_path / allowed
        if not target.resolve().is_relative_to(project_path):
            raise CodexDevelopmentError(
                f"allowedFiles escapes through a link: {allowed}"
            )
    commands = data.get("validationCommands")
    if not isinstance(commands, list) or not commands:
        raise CodexDevelopmentError("validationCommands must be a non-empty array")
    for command in commands:
        if (
            not isinstance(command, list)
            or not command
            or not all(
                isinstance(arg, str) and arg and "\x00" not in arg for arg in command
            )
        ):
            raise CodexDevelopmentError(
                "Each validation command must be a string array"
            )
    timeout = data.get("timeoutSeconds", 1800)
    if type(timeout) is not int or not 30 <= timeout <= 1800:
        raise CodexDevelopmentError("timeoutSeconds must be an integer in [30, 1800]")
    return DevelopmentTask(
        data["taskId"],
        data["stepId"],
        project_path,
        data["requirement"].strip(),
        allowed_files,
        tuple(tuple(command) for command in commands),
        timeout,
    )


def _git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )


def _collect_changed_files(project: Path, baseline: str) -> tuple[str, ...]:
    # NUL delimiters preserve spaces, quotes, Korean names, and rename endpoints.
    paths: set[str] = set()
    for args in (
        ("diff", "--no-renames", "--name-only", "-z", baseline, "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        result = _git(project, *args)
        if result.returncode:
            raise CodexDevelopmentError("Unable to inspect Git changes")
        paths.update(path for path in result.stdout.split("\x00") if path)
    return tuple(sorted(paths))


def _is_allowed_path(path: str, allowed_files: tuple[str, ...]) -> bool:
    return any(
        path.startswith(allowed) if allowed.endswith("/") else path == allowed
        for allowed in allowed_files
    )


def _resolve_codex_executable() -> str:
    executable = shutil.which(os.getenv("MDE_CODEX_EXECUTABLE", "codex"))
    if not executable:
        raise CodexDevelopmentError("Codex CLI not found; set MDE_CODEX_EXECUTABLE")
    return executable


def _run_process(
    command: tuple[str, ...], project: Path, timeout: int, prompt: str | None = None
) -> ValidationResult:
    try:
        process = subprocess.Popen(
            command,
            cwd=project,
            stdin=subprocess.PIPE if prompt is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            stdout, stderr = process.communicate(prompt, timeout=timeout)
            code = process.returncode
        except subprocess.TimeoutExpired:
            # Match the verified Provider's Windows descendant cleanup policy.
            try:
                children = psutil.Process(process.pid).children(recursive=True)
                for child in reversed(children):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
            except psutil.Error:
                pass
            finally:
                process.kill()
                stdout, stderr = process.communicate()
            code = 124
            stderr += f"\nExecution timed out after {timeout} seconds"
    except OSError as error:
        return ValidationResult(command, 127, "", str(error))
    return ValidationResult(command, code, stdout, stderr)


def _build_prompt(task: DevelopmentTask) -> str:
    allowed = "\n".join(f"- {path}" for path in task.allowed_files)
    commands = "\n".join("- " + " ".join(cmd) for cmd in task.validation_commands)
    return f"""Execute exactly one MDE development STEP.
STEP: {task.step_id}
TASK: {task.task_id}
Requirement:
{task.requirement}

Read AGENTS.md and repository governance first. Reuse verified code.
Implement only the minimum change. Modify only these repository-relative paths:
{allowed}
Do not commit, push, save through mde, release, publish, deploy, delegate,
add frameworks, or begin an automatic repair loop. Do not change ignored files,
Git metadata, or files outside the repository. Preserve unrelated behavior.
External validation will run:
{commands}
If impossible within the allowed paths, stop and report the unresolved issue.
Report changed files, summary, tests run, and unresolved issues.
Implement the requirement now.
"""


def _run_codex(task: DevelopmentTask, directory: Path) -> tuple[ValidationResult, str]:
    last_message = directory / "codex-last-message.txt"
    command = (
        _resolve_codex_executable(),
        "-a",
        "never",
        "exec",
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--color",
        "never",
        "--output-last-message",
        str(last_message),
        "-",
    )
    result = _run_process(
        command, task.project_path, task.timeout_seconds, _build_prompt(task)
    )
    summary = (
        last_message.read_text(encoding="utf-8", errors="replace")
        if last_message.exists()
        else ""
    )
    return result, summary


def _check_result_location(project: Path, result: Path) -> None:
    if not result.is_relative_to(project):
        return
    relative = result.relative_to(project).as_posix()
    if (
        ".git" in relative.casefold().split("/")
        or _git(project, "check-ignore", "-q", "--", relative).returncode != 0
        or _git(project, "ls-files", "--error-unmatch", "--", relative).returncode == 0
    ):
        raise CodexDevelopmentError(
            "Result inside the project must be an ignored, untracked path"
        )


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    # Existing capture redaction is reused for diagnostics and model output.
    def sanitized(value: Any) -> Any:
        if isinstance(value, str):
            return redact_text(value)[0]
        if isinstance(value, list):
            return [sanitized(item) for item in value]
        if isinstance(value, dict):
            return {key: sanitized(item) for key, item in value.items()}
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(sanitized(payload), stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run_task(request_path: Path, result_path: Path) -> int:
    request_path, result_path = request_path.resolve(), result_path.resolve()
    if result_path == request_path:
        raise CodexDevelopmentError("Result must not overwrite the request")
    # Protect existing repositories even when the request cannot be parsed.
    existing_parent = result_path.parent
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    detected = _git(existing_parent, "rev-parse", "--show-toplevel")
    if detected.returncode == 0:
        _check_result_location(Path(detected.stdout.strip()).resolve(), result_path)
    payload: dict[str, Any] = {
        "success": False,
        "taskId": None,
        "stepId": None,
        "codexExitCode": None,
        "changedFiles": [],
        "disallowedFiles": [],
        "validationResults": [],
        "codexSummary": "",
        "codexStderr": "",
        "error": None,
    }
    task = None
    baseline = None
    try:
        task = _load_task(request_path)
        payload.update(taskId=task.task_id, stepId=task.step_id)
        # Never overwrite a tracked file, even to report a preflight failure.
        _check_result_location(task.project_path, result_path)
    except CodexDevelopmentError as error:
        if task is not None:
            raise
        payload["error"] = str(error)
    except (OSError, ValueError) as error:
        payload["error"] = str(error)
    if task is not None and payload["error"] is None:
        try:
            ensure_repository(task.project_path)
            ensure_clean_worktree(task.project_path)
            baseline = get_local_head(task.project_path)
            result_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="mde-codex-w1-") as temporary:
                result, summary = _run_codex(task, Path(temporary))
                payload.update(
                    codexExitCode=result.exit_code,
                    codexStderr=result.stderr,
                    codexSummary=summary,
                )
            if result.exit_code:
                raise CodexDevelopmentError(
                    f"Codex exited with code {result.exit_code}"
                )

            def inspect() -> None:
                changed = _collect_changed_files(task.project_path, baseline)
                payload["changedFiles"] = list(changed)
                disallowed = [
                    path
                    for path in changed
                    if not _is_allowed_path(path, task.allowed_files)
                ]
                # Also reject links introduced under an allowed directory.
                for path in changed:
                    target = task.project_path / path
                    if target.is_symlink() or not target.resolve().is_relative_to(
                        task.project_path
                    ):
                        if path not in disallowed:
                            disallowed.append(path)
                payload["disallowedFiles"] = sorted(disallowed)
                if disallowed:
                    raise CodexDevelopmentError(
                        "Changes outside allowedFiles: " + ", ".join(disallowed)
                    )
                if get_local_head(task.project_path) != baseline:
                    raise CodexDevelopmentError(
                        "HEAD changed; commits are forbidden in W1"
                    )

            inspect()
            for command in task.validation_commands:
                validation = _run_process(
                    command, task.project_path, task.timeout_seconds
                )
                payload["validationResults"].append(
                    {
                        "command": list(command),
                        "exitCode": validation.exit_code,
                        "success": validation.success,
                        "stdout": validation.stdout,
                        "stderr": validation.stderr,
                    }
                )
                inspect()
                if not validation.success:
                    raise CodexDevelopmentError(
                        "Validation failed: " + " ".join(command)
                    )
            payload["success"] = True
        except (
            CodexDevelopmentError,
            GitError,
            OSError,
            ValueError,
            subprocess.TimeoutExpired,
        ) as error:
            payload["error"] = str(error)
        finally:
            if baseline is not None:
                try:
                    changed = _collect_changed_files(task.project_path, baseline)
                    payload["changedFiles"] = list(changed)
                    payload["disallowedFiles"] = sorted(
                        set(payload["disallowedFiles"])
                        | {
                            path
                            for path in changed
                            if not _is_allowed_path(path, task.allowed_files)
                        }
                    )
                except (
                    CodexDevelopmentError,
                    OSError,
                    subprocess.TimeoutExpired,
                ) as error:
                    payload.update(success=False, error=str(error))
    _write_result(result_path, payload)
    return 0 if payload["success"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one guarded MDE Codex development task"
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    try:
        return run_task(args.request, args.result)
    except (
        CodexDevelopmentError,
        GitError,
        OSError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
