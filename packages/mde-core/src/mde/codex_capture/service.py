from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import getnode, uuid4

from mde.codex_capture.git import (
    GitCaptureError,
    collect_patches,
    compare_snapshots,
    repository_root,
    snapshot,
)
from mde.codex_capture.security import alias_path, alias_text, redact_text

COLLECTOR_VERSION = "0.1.0"
OUTPUT_LIMIT = 1024 * 1024
OUTPUT_EDGE = 256 * 1024
VALID_TRANSITIONS = {
    "CREATED": {"CAPTURING"},
    "CAPTURING": {"PAUSED", "FINALIZING", "ABANDONED"},
    "PAUSED": {"CAPTURING", "FINALIZING", "ABANDONED"},
    "FINALIZING": {"SAVED", "QUEUED", "FAILED", "QUARANTINED"},
    "QUEUED": {"SAVED", "QUEUED", "QUARANTINED"},
}


class CodexCaptureError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CodexCaptureError(
            "SESSION_SERIALIZATION_FAILED", f"Cannot read {path}"
        ) from error


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise CodexCaptureError(
            "SESSION_SERIALIZATION_FAILED", f"Cannot write {path}"
        ) from error


class CodexCaptureService:
    def __init__(self, root: Path | None = None, api_url: str | None = None) -> None:
        configured = os.environ.get("MDE_CODEX_HOME")
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        selected_root = (
            root
            if root is not None
            else (
                Path(configured)
                if configured
                else Path(local) / "AutoKnowledgeLite" / "CodexCollector"
            )
        )
        self.root = selected_root.resolve()
        self.api_url = api_url or os.environ.get(
            "MDE_CAPTURE_API_URL", "http://127.0.0.1:8000/api/v1/captures"
        )
        self.config_dir = self.root / "config"
        self.sessions_dir = self.root / "sessions"
        self.queue_dir = self.root / "queue"
        self.quarantine_dir = self.root / "quarantine"
        self.logs_dir = self.root / "logs"
        for directory in (
            self.config_dir,
            self.sessions_dir,
            self.queue_dir,
            self.quarantine_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def registry_path(self) -> Path:
        return self.config_dir / "projects.json"

    @property
    def active_path(self) -> Path:
        return self.config_dir / "active-session.json"

    def register(
        self,
        project_id: str,
        path: Path,
        target_folder: str = "40_Reference/Codex",
        display_name: str | None = None,
    ) -> dict[str, Any]:
        if not project_id.strip():
            raise CodexCaptureError("INVALID_PROJECT_ID", "project ID is required")
        if not path.exists() or not path.is_dir():
            raise CodexCaptureError("PROJECT_PATH_NOT_FOUND", str(path))
        try:
            repo = repository_root(path)
        except GitCaptureError as error:
            raise CodexCaptureError("NOT_A_GIT_REPOSITORY", str(path)) from error
        projects = _read_json(self.registry_path, {})
        if project_id in projects:
            raise CodexCaptureError("PROJECT_ALREADY_REGISTERED", project_id)
        item = {
            "projectId": project_id,
            "displayName": display_name or project_id,
            "repositoryPath": str(repo),
            "targetFolder": target_folder,
            "autoFinalize": True,
            "enabled": True,
            "createdAt": _now(),
        }
        projects[project_id] = item
        _write_json(self.registry_path, projects)
        return item

    def unregister(self, project_id: str) -> None:
        projects = _read_json(self.registry_path, {})
        if project_id not in projects:
            raise CodexCaptureError("PROJECT_NOT_REGISTERED", project_id)
        del projects[project_id]
        _write_json(self.registry_path, projects)

    def list_projects(self) -> list[dict[str, Any]]:
        return list(_read_json(self.registry_path, {}).values())

    def _project(self, project_id: str) -> dict[str, Any]:
        project = _read_json(self.registry_path, {}).get(project_id)
        if not project:
            raise CodexCaptureError("PROJECT_NOT_REGISTERED", project_id)
        return project

    def start(
        self,
        project_id: str,
        title: str,
        request: str | None = None,
    ) -> dict[str, Any]:
        if self.active_path.exists():
            active = _read_json(self.active_path, {})
            raise CodexCaptureError(
                "SESSION_ALREADY_ACTIVE", str(active.get("captureSessionId", "unknown"))
            )
        project = self._project(project_id)
        repo = Path(project["repositoryPath"])
        try:
            before = snapshot(repo)
        except GitCaptureError as error:
            raise CodexCaptureError("SNAPSHOT_FAILED", str(error)) from error
        session_id = (
            f"cap_codex_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        )
        run_id = f"run_{uuid4().hex}"
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True)
        (session_dir / "command-output").mkdir()
        session = {
            "captureSessionId": session_id,
            "wrapperRunId": run_id,
            "sourceSessionId": None,
            "projectId": project_id,
            "targetFolder": project["targetFolder"],
            "title": redact_text(title)[0],
            "request": redact_text(request or "")[0] or None,
            "summary": None,
            "state": "CREATED",
            "startedAt": _now(),
            "endedAt": None,
            "closureReason": None,
            "repositoryRoot": str(repo),
            "commands": [],
            "notes": [],
            "tests": [],
        }
        self._transition(session, "CAPTURING")
        _write_json(session_dir / "before-snapshot.json", before)
        _write_json(session_dir / "session-state.json", session)
        _write_json(self.active_path, {"captureSessionId": session_id})
        return session

    def active(self) -> dict[str, Any] | None:
        if not self.active_path.exists():
            return None
        session_id = _read_json(self.active_path, {}).get("captureSessionId")
        if not session_id:
            return None
        return self.load_session(session_id)

    def load_session(self, session_id: str) -> dict[str, Any]:
        path = self.sessions_dir / session_id / "session-state.json"
        if not path.exists():
            raise CodexCaptureError("SESSION_NOT_FOUND", session_id)
        return _read_json(path, {})

    def _resolve_session(self, session_id: str | None) -> tuple[Path, dict[str, Any]]:
        if session_id is None:
            active = self.active()
            if active is None:
                raise CodexCaptureError("SESSION_NOT_FOUND", "No active session")
            session_id = active["captureSessionId"]
            session = active
        else:
            session = self.load_session(session_id)
        return self.sessions_dir / session_id, session

    def add_note(
        self, message: str, note_type: str = "progress", session_id: str | None = None
    ) -> None:
        session_dir, session = self._resolve_session(session_id)
        redacted, _ = redact_text(message)
        session["notes"].append(
            {"type": note_type, "message": redacted, "createdAt": _now()}
        )
        _write_json(session_dir / "session-state.json", session)

    def run_command(
        self,
        command: list[str],
        *,
        session_id: str | None = None,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if not command:
            raise CodexCaptureError("COMMAND_CAPTURE_FAILED", "command is required")
        session_dir, session = self._resolve_session(session_id)
        repo = Path(session["repositoryRoot"])
        working = (cwd or repo).resolve()
        try:
            working.relative_to(repo.resolve())
        except ValueError as error:
            raise CodexCaptureError(
                "COMMAND_CAPTURE_FAILED", "working directory is outside repository"
            ) from error
        command_id = f"cmd_{len(session['commands']) + 1:03d}"
        started = datetime.now(timezone.utc).astimezone()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=working,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            exit_code = completed.returncode
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as error:
            timed_out = True
            exit_code = None
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
        except OSError as error:
            raise CodexCaptureError("COMMAND_CAPTURE_FAILED", str(error)) from error
        ended = datetime.now(timezone.utc).astimezone()
        stdout = alias_text(stdout, repo_root=repo, worktree_root=repo)
        stderr = alias_text(stderr, repo_root=repo, worktree_root=repo)
        stdout_meta = self._store_output(session_dir, command_id, "stdout", stdout)
        stderr_meta = self._store_output(session_dir, command_id, "stderr", stderr)
        command_text, _ = redact_text(
            alias_text(
                subprocess.list2cmdline(command),
                repo_root=repo,
                worktree_root=repo,
            )
        )
        category, tool = classify_command(command)
        status = "TIMED_OUT" if timed_out else "PASSED" if exit_code == 0 else "FAILED"
        record = {
            "commandId": command_id,
            "command": command_text,
            "workingDirectory": alias_path(working, repo_root=repo, worktree_root=repo),
            "startedAt": started.isoformat(),
            "endedAt": ended.isoformat(),
            "durationMs": int((ended - started).total_seconds() * 1000),
            "exitCode": exit_code,
            "timedOut": timed_out,
            "stdoutPath": stdout_meta["path"],
            "stderrPath": stderr_meta["path"],
            "stdout": stdout_meta,
            "stderr": stderr_meta,
            "captureMethod": "mde_wrapper",
            "category": category,
            "tool": tool,
            "status": status,
        }
        session["commands"].append(record)
        if category != "GENERAL":
            session["tests"].append(
                parse_quality_result(record, stdout + "\n" + stderr)
            )
        _write_json(session_dir / "session-state.json", session)
        return record

    def _store_output(
        self, session_dir: Path, command_id: str, stream: str, value: str
    ) -> dict[str, Any]:
        redacted, was_redacted = redact_text(value)
        raw = redacted.encode("utf-8")
        full_hash = hashlib.sha256(raw).hexdigest()
        truncated = len(raw) > OUTPUT_LIMIT
        stored = (
            raw[:OUTPUT_EDGE] + b"\n...[TRUNCATED]...\n" + raw[-OUTPUT_EDGE:]
            if truncated
            else raw
        )
        relative = f"command-output/{command_id}.{stream}.txt"
        (session_dir / relative).write_bytes(stored)
        return {
            "path": relative,
            "truncated": truncated,
            "redacted": was_redacted,
            "originalByteLength": len(raw),
            "storedByteLength": len(stored),
            "fullOutputHash": full_hash,
        }

    def finalize(
        self,
        *,
        session_id: str | None = None,
        summary: str | None = None,
        closure_reason: str = "manual_finalize",
        transmit: bool = True,
    ) -> dict[str, Any]:
        session_dir, session = self._resolve_session(session_id)
        if session["state"] in {"SAVED", "QUEUED"}:
            return session
        self._transition(session, "FINALIZING")
        session["summary"] = redact_text(summary or "")[0] or session.get("summary")
        session["endedAt"] = _now()
        session["closureReason"] = closure_reason
        repo = Path(session["repositoryRoot"])
        try:
            before = _read_json(session_dir / "before-snapshot.json", {})
            after = snapshot(repo)
            changes = compare_snapshots(before, after)
            patches = collect_patches(repo, changes)
        except (GitCaptureError, OSError) as error:
            self._transition(session, "FAILED")
            _write_json(session_dir / "session-state.json", session)
            raise CodexCaptureError("SNAPSHOT_FAILED", str(error)) from error
        before_alias = self._alias_snapshot(before, repo)
        after_alias = self._alias_snapshot(after, repo)
        _write_json(session_dir / "before-snapshot.json", before_alias)
        _write_json(session_dir / "after-snapshot.json", after_alias)
        for filename, content in patches.items():
            redacted, _ = redact_text(content)
            (session_dir / filename).write_text(redacted, encoding="utf-8")
        payload = self._payload(session, before_alias, after_alias, changes, patches)
        for command in session["commands"]:
            for stream_name in ("stdoutPath", "stderrPath"):
                relative = command.get(stream_name)
                if not relative:
                    continue
                output_path = (session_dir / relative).resolve()
                try:
                    output_path.relative_to(session_dir.resolve())
                except ValueError:
                    continue
                payload["attachments"].append(
                    {
                        "type": "command_output",
                        "name": output_path.name,
                        "localPath": relative,
                        "content": output_path.read_text(
                            encoding="utf-8", errors="replace"
                        ),
                    }
                )
        payload = self._alias_values(payload, repo)
        content_hash = hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        envelope = {
            "schemaVersion": "1.0",
            "captureId": session["captureSessionId"],
            "sourceType": "codex",
            "captureType": "development_session",
            "captureDevice": "windows",
            "captureMethod": "windows_codex_wrapper",
            "projectId": session["projectId"],
            "targetFolder": session["targetFolder"],
            "parentDocument": None,
            "capturedAt": session["endedAt"],
            "deviceId": f"windows-{getnode():012x}",
            "contentHash": content_hash,
            "metadata": {
                "collectorVersion": COLLECTOR_VERSION,
                "wrapperRunId": session["wrapperRunId"],
            },
            "payload": payload,
        }
        _write_json(session_dir / "session.json", payload)
        _write_json(session_dir / "envelope.json", envelope)
        (session_dir / "session.md").write_text(
            render_markdown(envelope), encoding="utf-8"
        )
        _write_json(session_dir / "session-state.json", session)
        if transmit:
            try:
                response = self._post(envelope)
                session["serverResult"] = response
                self._transition(session, "SAVED")
                (self.queue_dir / f"{session['captureSessionId']}.json").unlink(
                    missing_ok=True
                )
            except CodexCaptureError as error:
                session["lastErrorCode"] = error.code
                if error.code == "QUARANTINED":
                    self._transition(session, "QUARANTINED")
                    _write_json(
                        self.quarantine_dir / f"{session['captureSessionId']}.json",
                        {
                            "captureId": session["captureSessionId"],
                            "status": "quarantined",
                            "errorCode": error.code,
                            "createdAt": _now(),
                        },
                    )
                else:
                    self._transition(session, "QUEUED")
                    self._queue(session)
        else:
            self._transition(session, "QUEUED")
            self._queue(session)
        _write_json(session_dir / "session-state.json", session)
        self.active_path.unlink(missing_ok=True)
        return session

    def retry(self, session_id: str | None = None) -> list[dict[str, Any]]:
        entries = sorted(self.queue_dir.glob("*.json"))
        if session_id:
            entries = [self.queue_dir / f"{session_id}.json"]
        results: list[dict[str, Any]] = []
        for path in entries:
            if not path.exists():
                raise CodexCaptureError("SESSION_NOT_FOUND", session_id or str(path))
            queued = _read_json(path, {})
            sid = queued["captureId"]
            session_dir = self.sessions_dir / sid
            session = self.load_session(sid)
            try:
                response = self._post(_read_json(session_dir / "envelope.json", {}))
                session["serverResult"] = response
                self._transition(session, "SAVED")
                path.unlink(missing_ok=True)
            except CodexCaptureError as error:
                queued["retryCount"] = int(queued.get("retryCount", 0)) + 1
                queued["lastErrorCode"] = error.code
                delay = min(3600, 2 ** min(queued["retryCount"], 12))
                queued["nextRetryAt"] = (
                    datetime.now(timezone.utc) + timedelta(seconds=delay)
                ).isoformat()
                _write_json(path, queued)
                session["lastErrorCode"] = error.code
            _write_json(session_dir / "session-state.json", session)
            results.append(session)
        return results

    def _queue(self, session: dict[str, Any]) -> None:
        _write_json(
            self.queue_dir / f"{session['captureSessionId']}.json",
            {
                "captureId": session["captureSessionId"],
                "status": "queued",
                "retryCount": 0,
                "lastErrorCode": session.get("lastErrorCode", "SERVER_UNREACHABLE"),
                "nextRetryAt": _now(),
            },
        )

    def _post(self, envelope: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
                server_code = detail.get("error", {}).get("code")
            except (json.JSONDecodeError, UnicodeDecodeError):
                server_code = None
            code = (
                "QUARANTINED"
                if server_code == "SENSITIVE_CONTENT_DETECTED"
                else "CAPTURE_API_REJECTED"
            )
            raise CodexCaptureError(
                code, f"Capture API returned HTTP {error.code}"
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise CodexCaptureError(
                "SERVER_UNREACHABLE", "Capture API is unavailable"
            ) from error
        return result

    def doctor(self) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        checks.append(
            {"status": "OK", "name": "Python", "detail": platform.python_version()}
        )
        git = shutil.which("git")
        checks.append(
            {
                "status": "OK" if git else "ERROR",
                "name": "Git",
                "detail": git or "not found",
            }
        )
        codex = shutil.which("codex")
        checks.append(
            {
                "status": "OK" if codex else "WARN",
                "name": "Codex",
                "detail": codex or "manual mode only",
            }
        )
        checks.append(
            {"status": "OK", "name": "Collector storage", "detail": str(self.root)}
        )
        checks.append(
            {
                "status": "OK",
                "name": "Projects",
                "detail": str(len(self.list_projects())),
            }
        )
        checks.append(
            {
                "status": "WARN" if any(self.queue_dir.glob("*.json")) else "OK",
                "name": "Queue",
                "detail": str(len(list(self.queue_dir.glob("*.json")))),
            }
        )
        checks.append({"status": "OK", "name": "Redaction", "detail": "enabled"})
        checks.append({"status": "INFO", "name": "Capture API", "detail": self.api_url})
        return checks

    @staticmethod
    def _transition(session: dict[str, Any], target: str) -> None:
        current = session.get("state")
        if current == target:
            return
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise CodexCaptureError(
                "INVALID_SESSION_TRANSITION", f"{current} -> {target}"
            )
        session["state"] = target

    @staticmethod
    def _alias_snapshot(value: dict[str, Any], repo: Path) -> dict[str, Any]:
        copied = json.loads(json.dumps(value))
        if copied.get("worktreePath"):
            copied["worktreePath"] = alias_path(
                copied["worktreePath"], repo_root=repo, worktree_root=repo
            )
        return copied

    @staticmethod
    def _alias_values(value: Any, repo: Path) -> Any:
        if isinstance(value, str):
            return alias_text(value, repo_root=repo, worktree_root=repo)
        if isinstance(value, dict):
            return {
                key: CodexCaptureService._alias_values(nested, repo)
                for key, nested in value.items()
            }
        if isinstance(value, list):
            return [CodexCaptureService._alias_values(item, repo) for item in value]
        return value

    @staticmethod
    def _payload(
        session: dict[str, Any],
        before: dict[str, Any],
        after: dict[str, Any],
        changes: list[dict[str, Any]],
        patches: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "captureSessionId": session["captureSessionId"],
            "sourceSessionId": session.get("sourceSessionId"),
            "clientType": "codex_wrapper",
            "title": session["title"],
            "request": session.get("request"),
            "summary": session.get("summary"),
            "startedAt": session["startedAt"],
            "endedAt": session["endedAt"],
            "closureReason": session["closureReason"],
            "repository": {
                "name": Path(session["repositoryRoot"]).name,
                "rootAlias": "%REPO_ROOT%",
                "branchBefore": before.get("branch"),
                "branchAfter": after.get("branch"),
                "headBefore": before.get("head"),
                "headAfter": after.get("head"),
                "worktreePathAlias": "%WORKTREE_ROOT%",
            },
            "beforeSnapshot": before,
            "afterSnapshot": after,
            "messages": [],
            "notes": session["notes"],
            "commands": session["commands"],
            "changedFiles": changes,
            "tests": session["tests"],
            "attachments": [
                {
                    "type": "patch",
                    "name": name,
                    "localPath": name,
                    "content": redact_text(patches[name])[0],
                }
                for name in ("session.patch", "staged.patch", "unstaged.patch")
            ],
        }


def classify_command(command: list[str]) -> tuple[str, str]:
    lowered = " ".join(command).lower()
    mappings = (
        ("pytest", "TEST", "pytest"),
        ("npm test", "TEST", "npm"),
        ("pnpm test", "TEST", "pnpm"),
        ("yarn test", "TEST", "yarn"),
        ("gradlew test", "TEST", "gradle"),
        ("dotnet test", "TEST", "dotnet"),
        ("cargo test", "TEST", "cargo"),
        ("go test", "TEST", "go"),
        ("ruff check", "LINT", "ruff"),
        ("eslint", "LINT", "eslint"),
        ("mypy", "TYPE_CHECK", "mypy"),
        ("black --check", "FORMAT_CHECK", "black"),
        ("npm run build", "BUILD", "npm"),
    )
    for marker, category, tool in mappings:
        if marker in lowered:
            return category, tool
    return "GENERAL", Path(command[0]).name


def parse_quality_result(command: dict[str, Any], output: str) -> dict[str, Any]:
    import re

    status = command["status"]
    result: dict[str, Any] = {
        "commandId": command["commandId"],
        "category": command["category"],
        "framework": command["tool"],
        "status": status,
        "exitCode": command["exitCode"],
    }
    if command["tool"] == "pytest":
        for name in ("passed", "failed", "skipped"):
            match = re.search(rf"(\d+)\s+{name}", output)
            if match:
                result[name] = int(match.group(1))
    return result


def render_markdown(envelope: dict[str, Any]) -> str:
    payload = envelope["payload"]
    repo = payload["repository"]
    tests = payload["tests"]
    tests_status = (
        "failed"
        if any(item["status"] == "FAILED" for item in tests)
        else "passed" if tests else "unknown"
    )
    lines = [
        "---",
        f"capture_id: {json.dumps(envelope['captureId'])}",
        'schema_version: "1.0"',
        f"title: {json.dumps('Codex 작업 — ' + payload['title'], ensure_ascii=False)}",
        'source_type: "codex"',
        'capture_type: "development_session"',
        'capture_device: "windows"',
        'capture_method: "windows_codex_wrapper"',
        f"project_id: {json.dumps(envelope['projectId'])}",
        f"repository: {json.dumps(repo['name'])}",
        f"branch_before: {json.dumps(repo.get('branchBefore'))}",
        f"branch_after: {json.dumps(repo.get('branchAfter'))}",
        f"head_before: {json.dumps(repo.get('headBefore'))}",
        f"head_after: {json.dumps(repo.get('headAfter'))}",
        f"started_at: {json.dumps(payload['startedAt'])}",
        f"ended_at: {json.dumps(payload['endedAt'])}",
        'status: "completed"',
        f"tests_status: {json.dumps(tests_status)}",
        f"changed_files_count: {len(payload['changedFiles'])}",
        "revision: 1",
        "---",
        "",
        f"# Codex 작업 — {payload['title']}",
        "",
        "## 작업 요청",
        "",
        payload.get("request") or "기록되지 않음",
        "",
        "## 작업 요약",
        "",
        payload.get("summary") or "기록되지 않음",
        "",
        "## 저장소 상태",
        "",
        f"- 저장소: `{repo['name']}`",
        f"- 브랜치: `{repo.get('branchAfter') or '-'}`",
        f"- 시작 HEAD: `{repo.get('headBefore') or '-'}`",
        f"- 종료 HEAD: `{repo.get('headAfter') or '-'}`",
        "- Worktree: `%WORKTREE_ROOT%`",
        "",
        "## 변경 파일",
        "",
    ]
    lines.extend(
        f"- `{item['path']}` — {item.get('changeType', 'unknown')} ({item['attribution']})"
        for item in payload["changedFiles"]
    )
    lines.extend(
        (
            "",
            "## 실행 명령",
            "",
            "| 명령 | 분류 | 종료 코드 | 결과 |",
            "|---|---|---:|---|",
        )
    )
    lines.extend(
        f"| `{item['command']}` | {item['category']} | {item['exitCode'] if item['exitCode'] is not None else '-'} | {item['status']} |"
        for item in payload["commands"]
    )
    lines.extend(
        (
            "",
            "## 첨부",
            "",
            "- [[session.json]]",
            "- [[session.patch]]",
            "- [[unstaged.patch]]",
            "- [[staged.patch]]",
            "",
        )
    )
    return "\n".join(lines)
