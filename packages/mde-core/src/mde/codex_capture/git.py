from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mde.codex_capture.security import is_sensitive_path


class GitCaptureError(RuntimeError):
    pass


def _git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as error:
        raise GitCaptureError("GIT_NOT_FOUND") from error
    if check and result.returncode != 0:
        raise GitCaptureError(f"GIT_COMMAND_FAILED: {' '.join(args)}")
    return result


def repository_root(path: Path) -> Path:
    result = _git(path, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def _hash_file(root: Path, relative: str) -> str | None:
    if is_sensitive_path(relative):
        return None
    path = root / relative
    try:
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _is_binary(root: Path, relative: str) -> bool:
    if is_sensitive_path(relative):
        return False
    try:
        with (root / relative).open("rb") as stream:
            return b"\0" in stream.read(8192)
    except OSError:
        return False


def _parse_status(root: Path, output: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    records = output.split("\0") if "\0" in output else output.splitlines()
    index = 0
    while index < len(records):
        line = records[index]
        index += 1
        if len(line) < 3:
            continue
        index_status, worktree_status, raw_path = line[0], line[1], line[3:]
        old_path = None
        path = raw_path
        if (
            index_status in {"R", "C"} or worktree_status in {"R", "C"}
        ) and "\0" in output:
            if index < len(records):
                old_path = records[index]
                index += 1
        elif " -> " in raw_path:
            old_path, path = raw_path.split(" -> ", 1)
        status_code = (
            worktree_status if worktree_status not in {" ", "?"} else index_status
        )
        change_type = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "?": "untracked",
        }.get(status_code, "unknown")
        sensitive = is_sensitive_path(path)
        files.append(
            {
                "path": path.replace("\\", "/"),
                "oldPath": old_path.replace("\\", "/") if old_path else None,
                "changeType": change_type,
                "staged": index_status not in {" ", "?"},
                "unstaged": worktree_status not in {" ", "?"},
                "untracked": index_status == "?" and worktree_status == "?",
                "binary": _is_binary(root, path),
                "sensitive": sensitive,
                "contentHash": None if sensitive else _hash_file(root, path),
            }
        )
    return files


def snapshot(root: Path) -> dict[str, Any]:
    root = repository_root(root)
    head_result = _git(root, "rev-parse", "HEAD", check=False)
    branch = _git(root, "branch", "--show-current").stdout.strip()
    status = _git(
        root, "-c", "core.quotepath=false", "status", "--porcelain=v1", "-z"
    ).stdout
    files = _parse_status(root, status)
    return {
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "head": head_result.stdout.strip() if head_result.returncode == 0 else None,
        "branch": branch or None,
        "detachedHead": not bool(branch),
        "worktreePath": str(root),
        "dirty": bool(files),
        "files": files,
    }


def compare_snapshots(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    before_by_path = {item["path"]: item for item in before.get("files", [])}
    after_by_path = {item["path"]: item for item in after.get("files", [])}
    output: list[dict[str, Any]] = []
    for path in sorted(set(before_by_path) | set(after_by_path)):
        old = before_by_path.get(path)
        new = after_by_path.get(path)
        item = dict(new or old or {"path": path})
        if old and new:
            unchanged = (
                old.get("contentHash") == new.get("contentHash")
                and old.get("staged") == new.get("staged")
                and old.get("unstaged") == new.get("unstaged")
                and old.get("changeType") == new.get("changeType")
            )
            if unchanged:
                attribution, confidence = "PRE_EXISTING", "high"
            else:
                attribution, confidence = "UNKNOWN_ATTRIBUTION", "low"
        elif new:
            attribution = (
                "SESSION_CREATED"
                if new.get("changeType") in {"added", "untracked"}
                else (
                    "SESSION_RENAMED"
                    if new.get("changeType") == "renamed"
                    else (
                        "SESSION_DELETED"
                        if new.get("changeType") == "deleted"
                        else "SESSION_MODIFIED"
                    )
                )
            )
            confidence = "medium"
        else:
            attribution, confidence = "UNKNOWN_ATTRIBUTION", "low"
        item["attribution"] = attribution
        item["attributionConfidence"] = confidence
        item.pop("contentHash", None) if item.get("sensitive") else None
        output.append(item)
    return output


def collect_patches(root: Path, files: list[dict[str, Any]]) -> dict[str, str]:
    safe_paths = [item["path"] for item in files if not item.get("sensitive")]
    if not safe_paths:
        return {"unstaged.patch": "", "staged.patch": "", "session.patch": ""}
    unstaged = _git(root, "diff", "--", *safe_paths).stdout
    for item in files:
        if (
            item.get("untracked")
            and not item.get("sensitive")
            and item.get("contentHash")
        ):
            created = _git(
                root,
                "diff",
                "--no-index",
                "--",
                "/dev/null",
                item["path"],
                check=False,
            )
            if created.returncode in {0, 1}:
                unstaged += created.stdout
    staged = _git(root, "diff", "--cached", "--", *safe_paths).stdout
    session = "# Unstaged changes\n" + unstaged + "\n# Staged changes\n" + staged
    return {
        "unstaged.patch": unstaged,
        "staged.patch": staged,
        "session.patch": session,
    }
