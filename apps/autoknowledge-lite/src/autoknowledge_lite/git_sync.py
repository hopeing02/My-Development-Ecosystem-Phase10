"""Git synchronization for generated knowledge notes."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Protocol


class GitSyncError(RuntimeError):
    """Raised when a generated note cannot be synchronized."""


class NoteSync(Protocol):
    """Synchronize one generated note with remote storage."""

    def sync(self, note_path: Path) -> None:
        """Commit and push a generated note when synchronization is enabled."""


class GitNoteSync:
    """Commit and push only the generated Markdown note passed to ``sync``."""

    def __init__(
        self,
        repo_dir: Path,
        *,
        enabled: bool | None = None,
        branch: str | None = None,
    ) -> None:
        self.repo_dir = repo_dir.resolve()
        self.enabled = (
            _environment_flag("AUTOKNOWLEDGE_GIT_SYNC", default=False)
            if enabled is None
            else enabled
        )
        self.branch = branch or os.getenv("AUTOKNOWLEDGE_GIT_BRANCH", "main")
        self._lock = threading.Lock()

    def sync(self, note_path: Path) -> None:
        if not self.enabled:
            return

        resolved_note = note_path.resolve()
        try:
            relative_note = resolved_note.relative_to(self.repo_dir)
        except ValueError as error:
            raise GitSyncError("Note is outside the configured Vault.") from error
        if not resolved_note.is_file() or resolved_note.suffix.lower() != ".md":
            raise GitSyncError("Only an existing Markdown note can be synchronized.")
        if not (self.repo_dir / ".git").exists():
            raise GitSyncError("The configured Vault is not a Git repository.")

        with self._lock:
            self._run("pull", "--rebase", "--autostash", "origin", self.branch)
            self._run("add", "--", relative_note.as_posix())
            changed = self._run("diff", "--cached", "--quiet", check=False)
            if changed.returncode == 0:
                return
            if changed.returncode != 1:
                raise GitSyncError("Unable to inspect the staged knowledge note.")
            self._run("commit", "-m", f"knowledge: add {resolved_note.stem}")
            self._run("push", "origin", self.branch)

    def _run(
        self,
        *arguments: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "git",
            "-c",
            f"safe.directory={self.repo_dir.as_posix()}",
            *arguments,
        ]
        try:
            return subprocess.run(
                command,
                cwd=self.repo_dir,
                capture_output=True,
                check=check,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise GitSyncError("Unable to synchronize the knowledge note.") from error


def _environment_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}
