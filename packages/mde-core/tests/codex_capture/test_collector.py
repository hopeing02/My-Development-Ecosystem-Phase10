from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from mde.cli import build_parser, main
from mde.codex_capture.git import compare_snapshots, snapshot
from mde.codex_capture.security import (
    alias_path,
    alias_text,
    is_sensitive_path,
    redact_text,
)
from mde.codex_capture.service import CodexCaptureError, CodexCaptureService


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "codex@example.invalid")
    git(repo, "config", "user.name", "Codex Test")
    (repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "initial")
    return repo


def test_snapshot_and_attribution_preserve_pre_existing_changes(
    repository: Path,
) -> None:
    (repository / "tracked.txt").write_text("dirty before\n", encoding="utf-8")
    before = snapshot(repository)
    (repository / "created.txt").write_text("new\n", encoding="utf-8")
    after = snapshot(repository)

    changes = {item["path"]: item for item in compare_snapshots(before, after)}

    assert changes["tracked.txt"]["attribution"] == "PRE_EXISTING"
    assert changes["created.txt"]["attribution"] == "SESSION_CREATED"
    assert changes["created.txt"]["attributionConfidence"] == "medium"


def test_existing_dirty_file_changed_again_is_unknown(repository: Path) -> None:
    (repository / "tracked.txt").write_text("dirty before\n", encoding="utf-8")
    before = snapshot(repository)
    (repository / "tracked.txt").write_text(
        "changed during session\n", encoding="utf-8"
    )

    change = compare_snapshots(before, snapshot(repository))[0]

    assert change["attribution"] == "UNKNOWN_ATTRIBUTION"
    assert change["attributionConfidence"] == "low"


def test_snapshot_distinguishes_staged_unstaged_rename_and_binary(
    repository: Path,
) -> None:
    (repository / "rename me.txt").write_text("rename\n", encoding="utf-8")
    git(repository, "add", "rename me.txt")
    git(repository, "commit", "-m", "rename fixture")
    (repository / "tracked.txt").write_text("staged\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    (repository / "tracked.txt").write_text("unstaged too\n", encoding="utf-8")
    git(repository, "mv", "rename me.txt", "renamed file.txt")
    (repository / "binary.bin").write_bytes(b"binary\0content")

    files = {item["path"]: item for item in snapshot(repository)["files"]}

    assert files["tracked.txt"]["staged"] is True
    assert files["tracked.txt"]["unstaged"] is True
    assert files["renamed file.txt"]["changeType"] == "renamed"
    assert files["renamed file.txt"]["oldPath"] == "rename me.txt"
    assert files["binary.bin"]["binary"] is True


def test_security_redacts_tokens_and_excludes_sensitive_paths(repository: Path) -> None:
    value, changed = redact_text("OPENAI_API_KEY=sk-abcdefghijklmnop")

    assert changed is True
    assert "abcdefghijklmnop" not in value
    assert is_sensitive_path(".env.local")
    assert is_sensitive_path("keys/server.pem")
    assert (
        alias_path(
            repository / "tracked.txt", repo_root=repository, worktree_root=repository
        )
        == "%WORKTREE_ROOT%/tracked.txt"
    )
    assert "%WORKTREE_ROOT%/tracked.txt" in alias_text(
        f"opened {repository / 'tracked.txt'}",
        repo_root=repository,
        worktree_root=repository,
    )


def test_security_redacts_quoted_secret_assignment() -> None:
    value, changed = redact_text('Example: API_KEY="secret-value"')

    assert changed is True
    assert "secret-value" not in value
    assert "[REDACTED]" in value


@pytest.mark.parametrize(
    "value",
    [
        "900101-1234567",
        "4111 1111 1111 1111",
    ],
)
def test_security_redacts_sensitive_numeric_identifiers(value: str) -> None:
    redacted, changed = redact_text(value)

    assert changed is True
    assert value not in redacted
    assert redacted == "[REDACTED]"


def test_register_start_run_finalize_creates_artifacts_and_queue(
    tmp_path: Path, repository: Path
) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "Collector test", "Capture actual Git state")
    (repository / "created.txt").write_text("created\n", encoding="utf-8")

    command = service.run_command(
        [sys.executable, "-c", "print('1 passed in 0.01s')", "pytest"],
        session_id=session["captureSessionId"],
    )
    result = service.finalize(
        session_id=session["captureSessionId"],
        summary="Implemented collector",
        transmit=False,
    )

    session_dir = service.sessions_dir / session["captureSessionId"]
    assert command["exitCode"] == 0
    assert result["state"] == "QUEUED"
    assert (session_dir / "session.json").is_file()
    assert (session_dir / "session.md").is_file()
    assert (session_dir / "session.patch").is_file()
    assert "+created" in (session_dir / "session.patch").read_text(encoding="utf-8")
    assert (service.queue_dir / f"{session['captureSessionId']}.json").is_file()
    payload = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
    assert payload["repository"]["rootAlias"] == "%REPO_ROOT%"
    assert any(item["path"] == "created.txt" for item in payload["changedFiles"])
    assert any(item["type"] == "command_output" for item in payload["attachments"])


def test_command_failure_timeout_and_redaction(
    tmp_path: Path, repository: Path
) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "commands")

    failed = service.run_command(
        [
            sys.executable,
            "-c",
            "import sys; print('API_KEY=secret-value'); sys.exit(3)",
        ],
        session_id=session["captureSessionId"],
    )
    timed_out = service.run_command(
        [sys.executable, "-c", "import time; time.sleep(1)"],
        session_id=session["captureSessionId"],
        timeout=0.01,
    )

    assert failed["status"] == "FAILED"
    assert failed["exitCode"] == 3
    output = (
        service.sessions_dir / session["captureSessionId"] / failed["stdoutPath"]
    ).read_text(encoding="utf-8")
    assert "secret-value" not in output
    assert timed_out["status"] == "TIMED_OUT"


def test_registration_rejects_duplicate_and_non_git(
    tmp_path: Path, repository: Path
) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    with pytest.raises(CodexCaptureError, match="demo"):
        service.register("demo", repository)
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(CodexCaptureError) as error:
        service.register("plain", plain)
    assert error.value.code == "NOT_A_GIT_REPOSITORY"


def test_cli_registers_codex_commands() -> None:
    args = build_parser().parse_args(["codex", "doctor"])
    assert args.command == "codex"
    assert args.codex_action == "doctor"


def test_save_success_is_not_reversed_by_collector_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import mde.cli
    import mde.codex_capture.service

    monkeypatch.setattr(mde.cli, "save", lambda **_: None)

    class BrokenCollector:
        def __init__(self) -> None:
            raise CodexCaptureError("QUEUE_WRITE_FAILED", "collector unavailable")

    monkeypatch.setattr(
        mde.codex_capture.service, "CodexCaptureService", BrokenCollector
    )

    assert main(["save", "-m", "successful save", "--no-push"]) == 0
    output = capsys.readouterr().out
    assert "MDE save completed" in output
    assert "Warning: Codex capture update failed" in output


def test_server_recovery_retries_queued_session(
    tmp_path: Path, repository: Path
) -> None:
    service = CodexCaptureService(
        root=tmp_path / "collector", api_url="http://127.0.0.1:9/api/v1/captures"
    )
    service.register("demo", repository)
    session = service.start("demo", "retry")
    queued = service.finalize(session_id=session["captureSessionId"])
    assert queued["state"] == "QUEUED"

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            body = json.dumps(
                {
                    "status": "saved",
                    "captureId": request["captureId"],
                    "documentId": "doc_test",
                    "documentPath": "40_Reference/Codex/test.md",
                    "captureType": "development_session",
                    "duplicate": False,
                    "revision": 1,
                    "warnings": [],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        service.api_url = f"http://127.0.0.1:{server.server_port}/api/v1/captures"
        retried = service.retry(session["captureSessionId"])
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert retried[0]["state"] == "SAVED"
    assert not (service.queue_dir / f"{session['captureSessionId']}.json").exists()


def test_server_sensitive_rejection_is_quarantined_not_queued(
    tmp_path: Path, repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "quarantine")

    def reject(_: dict[str, object]) -> dict[str, object]:
        raise CodexCaptureError("QUARANTINED", "server rejected sensitive content")

    monkeypatch.setattr(service, "_post", reject)
    result = service.finalize(session_id=session["captureSessionId"])

    assert result["state"] == "QUARANTINED"
    assert (service.quarantine_dir / f"{session['captureSessionId']}.json").is_file()
    assert not (service.queue_dir / f"{session['captureSessionId']}.json").exists()
