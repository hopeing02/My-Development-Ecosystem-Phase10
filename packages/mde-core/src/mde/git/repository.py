from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class GitError(RuntimeError):
    """Raised when a git command fails or a safety rule is violated."""


@dataclass(frozen=True)
class GitState:
    local_head: str
    remote_head: str
    branch: str


@dataclass(frozen=True)
class GitCommandResult:
    args: tuple[str, ...]
    stdout: str


def run_git(*args: str, repository_root: Path | None = None) -> str:
    root = (repository_root or Path.cwd()).resolve()
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GitError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"git {' '.join(args)} failed."
        )
    return completed.stdout.strip()


def ensure_repository(repository_root: Path | None = None) -> Path:
    root = (repository_root or Path.cwd()).resolve()
    value = run_git("rev-parse", "--show-toplevel", repository_root=root)
    detected = Path(value).resolve()
    if detected != root:
        raise GitError(f"Expected repository root {root}, detected {detected}.")
    return root


def current_branch(repository_root: Path | None = None) -> str:
    branch = run_git("branch", "--show-current", repository_root=repository_root)
    if not branch:
        raise GitError("Detached HEAD is not supported by Mobile Sync.")
    return branch


def get_local_head(repository_root: Path | None = None) -> str:
    return run_git("rev-parse", "HEAD", repository_root=repository_root)


def fetch(remote: str = "origin", repository_root: Path | None = None) -> None:
    run_git("fetch", "--prune", remote, repository_root=repository_root)


def get_remote_head(
    branch: str | None = None,
    *,
    remote: str = "origin",
    repository_root: Path | None = None,
) -> str:
    active_branch = branch or current_branch(repository_root)
    return run_git(
        "rev-parse",
        f"{remote}/{active_branch}",
        repository_root=repository_root,
    )


def get_git_state(
    branch: str | None = None,
    *,
    remote: str = "origin",
    repository_root: Path | None = None,
    fetch_first: bool = False,
) -> GitState:
    if fetch_first:
        fetch(remote=remote, repository_root=repository_root)
    active_branch = branch or current_branch(repository_root)
    return GitState(
        local_head=get_local_head(repository_root),
        remote_head=get_remote_head(
            active_branch, remote=remote, repository_root=repository_root
        ),
        branch=active_branch,
    )


def has_remote_changes(
    branch: str | None = None,
    *,
    remote: str = "origin",
    repository_root: Path | None = None,
    fetch_first: bool = True,
) -> bool:
    state = get_git_state(
        branch,
        remote=remote,
        repository_root=repository_root,
        fetch_first=fetch_first,
    )
    return state.local_head != state.remote_head


def changed_files(repository_root: Path | None = None) -> tuple[str, ...]:
    output = run_git("status", "--porcelain", repository_root=repository_root)
    return tuple(line for line in output.splitlines() if line.strip())


def ensure_clean_worktree(repository_root: Path | None = None) -> None:
    changes = changed_files(repository_root)
    if changes:
        preview = ", ".join(changes[:5])
        raise GitError(f"Working tree is not clean: {preview}")


def pull_fast_forward(
    *,
    remote: str = "origin",
    branch: str | None = None,
    repository_root: Path | None = None,
) -> None:
    active_branch = branch or current_branch(repository_root)
    run_git(
        "pull",
        "--ff-only",
        remote,
        active_branch,
        repository_root=repository_root,
    )


def pull(repository_root: Path | None = None) -> None:
    """Backward-compatible safe pull."""
    pull_fast_forward(repository_root=repository_root)


def add(
    paths: Sequence[str] | None = None, repository_root: Path | None = None
) -> None:
    selected = tuple(paths or (".",))
    run_git("add", "--", *selected, repository_root=repository_root)


def commit(message: str, repository_root: Path | None = None) -> str:
    if not message.strip():
        raise GitError("Commit message must not be empty.")
    run_git("commit", "-m", message, repository_root=repository_root)
    return get_local_head(repository_root)


def push(
    *,
    remote: str = "origin",
    branch: str | None = None,
    repository_root: Path | None = None,
) -> None:
    active_branch = branch or current_branch(repository_root)
    run_git("push", remote, active_branch, repository_root=repository_root)
