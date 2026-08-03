from __future__ import annotations

import json
import io
import subprocess
from pathlib import Path

import pytest

from mde.cli import build_parser
from mde.codex_capture.service import CodexCaptureError, CodexCaptureService
from mde.codex_capture.sessions import (
    AppServerClient,
    CodexAppSessionAdapter,
    CodexSessionAdapterError,
    SessionCheckpoint,
    normalize_thread,
)


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


def public_thread() -> dict[str, object]:
    return {
        "id": "thr_public",
        "sessionId": "thr_public",
        "name": "Public adapter test",
        "createdAt": 1785686400,
        "updatedAt": 1785686460,
        "turns": [
            {
                "id": "turn_1",
                "createdAt": 1785686401,
                "items": [
                    {
                        "type": "userMessage",
                        "id": "user_1",
                        "content": [
                            {"type": "text", "text": "Use API_KEY=secret-value safely"}
                        ],
                    },
                    {
                        "type": "reasoning",
                        "id": "private_1",
                        "summary": ["must never be collected"],
                        "content": ["hidden"],
                    },
                    {
                        "type": "agentMessage",
                        "id": "agent_1",
                        "phase": "commentary",
                        "text": "I am checking the repository.",
                    },
                    {
                        "type": "commandExecution",
                        "id": "cmd_source_1",
                        "command": "python -m pytest --version",
                        "cwd": "C:/Users/person/repo",
                        "status": "completed",
                        "aggregatedOutput": "1 passed",
                        "exitCode": 0,
                    },
                    {
                        "type": "fileChange",
                        "id": "patch_1",
                        "status": "completed",
                        "changes": [
                            {"path": "tracked.txt", "kind": "update", "diff": "+after"}
                        ],
                    },
                    {"type": "futurePublicEvent", "id": "future_1", "text": "visible"},
                ],
            }
        ],
    }


def test_normalize_thread_preserves_public_events_and_excludes_reasoning() -> None:
    result = normalize_thread(public_thread())

    assert [item["role"] for item in result["messages"]] == [
        "user",
        "assistant",
        "tool",
        "tool",
        "unknown",
    ]
    assert all(item["sourceMessageId"] != "private_1" for item in result["messages"])
    assert "secret-value" not in result["messages"][0]["content"]
    assert result["messages"][2]["messageType"] == "command"
    assert result["messages"][3]["metadata"]["appliedState"] == "unknown"
    assert result["parseStatus"] == "partial"
    assert "CODEX_MESSAGE_ROLE_UNKNOWN" in result["warnings"]
    assert all(len(item["contentHash"]) == 64 for item in result["messages"])


def test_checkpoint_detects_rewrite_and_deduplicates_messages() -> None:
    thread = public_thread()
    first = normalize_thread(thread)
    checkpoint = SessionCheckpoint(
        source_session_id="thr_public",
        source_fingerprint=first["checkpoint"]["sourceFingerprint"],
        last_message_sequence=len(first["messages"]),
    )
    turn = thread["turns"][0]  # type: ignore[index]
    turn["items"].append(turn["items"][0])  # type: ignore[index]
    turn["items"][-2] = {  # type: ignore[index]
        "type": "agentMessage",
        "id": "replacement",
        "text": "A rewritten public event",
        "phase": "final_answer",
    }

    rewritten = normalize_thread(thread, checkpoint=checkpoint)

    assert len({item["sourceMessageId"] for item in rewritten["messages"]}) == len(
        rewritten["messages"]
    )
    assert "CODEX_SESSION_CHECKPOINT_INVALID" in rewritten["warnings"]


def test_failed_turn_is_preserved_as_public_error_event() -> None:
    thread = public_thread()
    thread["turns"].append(  # type: ignore[union-attr]
        {
            "id": "turn_failed",
            "createdAt": 1785686500,
            "status": "failed",
            "items": [],
            "error": {"message": "Public retry exhausted"},
        }
    )

    result = normalize_thread(thread)

    error = result["messages"][-1]
    assert error["role"] == "tool"
    assert error["messageType"] == "error"
    assert error["content"] == "Public retry exhausted"


def test_app_server_adapter_uses_official_list_and_read_methods() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
            self.calls.append((method, params))
            if method == "thread/list":
                return {"data": [public_thread()]}
            return {"thread": public_thread()}

    client = FakeClient()
    adapter = CodexAppSessionAdapter(client)  # type: ignore[arg-type]

    discovered = adapter.discover_sessions()
    read = adapter.read_session(discovered[0], None)

    assert [call[0] for call in client.calls] == ["thread/list", "thread/read"]
    assert read["sourceSessionId"] == "thr_public"


def test_app_server_client_parses_json_rpc_without_logging_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdin = io.StringIO()
            self.stdout = io.StringIO(
                '{"id":1,"result":{"userAgent":"test"}}\n'
                '{"id":2,"result":{"data":[]}}\n'
            )
            self.stderr = io.StringIO()
            self.returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            self.returncode = 0
            return 0

        def kill(self) -> None:
            self.returncode = -1

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    result = AppServerClient("codex-test").request("thread/list", {"limit": 1})

    assert result == {"data": []}


def test_manual_import_requires_consent_and_merges_final_artifacts(
    tmp_path: Path, repository: Path
) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "Conversation adapter")
    export = tmp_path / "thread-read.json"
    export.write_text(json.dumps({"thread": public_thread()}), encoding="utf-8")

    with pytest.raises(CodexCaptureError) as error:
        service.import_codex_session(session["captureSessionId"], export, consent=False)
    assert error.value.code == "CODEX_CONVERSATION_CONSENT_REQUIRED"

    imported = service.import_codex_session(
        session["captureSessionId"], export, consent=True
    )
    rewritten_thread = public_thread()
    rewritten_thread["turns"][0]["items"][2]["text"] = (  # type: ignore[index]
        "Updated public progress."
    )
    export.write_text(json.dumps({"thread": rewritten_thread}), encoding="utf-8")
    rewritten = service.import_codex_session(
        session["captureSessionId"], export, consent=True
    )
    finalized = service.finalize(session_id=session["captureSessionId"], transmit=False)
    session_dir = service.sessions_dir / session["captureSessionId"]
    payload = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
    markdown = (session_dir / "session.md").read_text(encoding="utf-8")
    reference = json.loads(
        (session_dir / "source-session-reference.json").read_text(encoding="utf-8")
    )

    assert imported["totalMessages"] == 5
    assert rewritten["newMessages"] == 1
    assert rewritten["totalMessages"] == 5
    assert finalized["state"] == "QUEUED"
    assert payload["sourceSessionId"] == "thr_public"
    assert payload["clientType"] == "manual_import"
    assert len(payload["messages"]) == 5
    assert "## Codex 대화" in markdown
    assert "must never be collected" not in markdown
    assert reference["sourcePathAlias"] == "%EXPLICIT_IMPORT%/thread-read.json"
    assert str(tmp_path) not in json.dumps(reference)
    assert (session_dir / "messages.json").is_file()
    assert (session_dir / "session-checkpoint.json").is_file()


def test_conversation_capture_can_be_disabled(
    tmp_path: Path,
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "disabled")
    monkeypatch.setenv("MDE_CODEX_CONVERSATION_CAPTURE", "false")

    with pytest.raises(CodexCaptureError) as error:
        service.attach_codex_session(
            session["captureSessionId"], "thr_public", consent=True
        )

    assert error.value.code == "CODEX_CONVERSATION_CAPTURE_DISABLED"


def test_command_event_merges_capture_sources(tmp_path: Path, repository: Path) -> None:
    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "command merge")
    command = service.run_command(
        ["python", "-m", "pytest", "--version"], session_id=session["captureSessionId"]
    )
    export = tmp_path / "thread.json"
    export.write_text(json.dumps({"thread": public_thread()}), encoding="utf-8")

    service.import_codex_session(session["captureSessionId"], export, consent=True)
    state = service.load_session(session["captureSessionId"])

    assert state["commands"][0]["commandId"] == command["commandId"]
    assert state["commands"][0]["captureSources"] == ["mde_wrapper", "codex_session"]
    command_message = next(
        item for item in state["messages"] if item["messageType"] == "command"
    )
    assert command_message["relatedCommandIds"] == [command["commandId"]]


def test_attached_session_sync_updates_same_capture_revision_and_deduplicates(
    tmp_path: Path,
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mde.codex_capture.service as service_module

    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "revision sync")
    capture_id = session["captureSessionId"]
    service.attach_codex_session(capture_id, "thr_public", consent=True)
    service.finalize(session_id=capture_id, transmit=False)

    class FakeAdapter:
        def read_session(
            self,
            reference: dict[str, object],
            checkpoint: SessionCheckpoint | None,
        ) -> dict[str, object]:
            return normalize_thread(public_thread(), checkpoint=checkpoint)

    posted: list[dict[str, object]] = []

    def post(envelope: dict[str, object]) -> dict[str, object]:
        posted.append(envelope)
        return {"status": "saved", "captureId": capture_id, "revision": 2}

    monkeypatch.setattr(service_module, "CodexAppSessionAdapter", FakeAdapter)
    monkeypatch.setattr(service, "_post", post)

    first = service.sync_codex_session(capture_id)
    second = service.sync_codex_session(capture_id)

    assert first["newMessages"] == 5
    assert first["transmitted"] is True
    assert second["newMessages"] == 0
    assert second["transmitted"] is False
    assert len(posted) == 1
    assert posted[0]["captureId"] == capture_id
    assert service.load_session(capture_id)["state"] == "SAVED"


def test_discovery_marks_active_repository_candidate_without_exposing_path(
    tmp_path: Path,
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mde.codex_capture.service as service_module

    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    active = service.start("demo", "candidate")

    class FakeAdapter:
        def discover_sessions(self) -> list[dict[str, object]]:
            return [
                {
                    "sourceSessionId": "thr_candidate",
                    "clientType": "codex_app_server",
                    "_sourceCwd": str(repository),
                    "projectPathAlias": None,
                }
            ]

    monkeypatch.setattr(service_module, "CodexAppSessionAdapter", FakeAdapter)

    candidate = service.discover_codex_sessions()[0]

    assert candidate["captureSessionCandidate"] == active["captureSessionId"]
    assert candidate["sessionLinkConfidence"] == "medium"
    assert candidate["projectPathAlias"] == "%REPO_ROOT%"
    assert "_sourceCwd" not in candidate


def test_final_sync_failure_does_not_block_existing_finalize(
    tmp_path: Path,
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mde.codex_capture.service as service_module

    service = CodexCaptureService(root=tmp_path / "collector")
    service.register("demo", repository)
    session = service.start("demo", "best effort final sync")
    capture_id = session["captureSessionId"]
    service.attach_codex_session(capture_id, "thr_unavailable", consent=True)

    class BrokenAdapter:
        def read_session(self, *args: object, **kwargs: object) -> dict[str, object]:
            raise CodexSessionAdapterError("CODEX_SESSION_ACCESS_DENIED", "unavailable")

    monkeypatch.setattr(service_module, "CodexAppSessionAdapter", BrokenAdapter)

    finalized = service.finalize(session_id=capture_id, transmit=False)

    assert finalized["state"] == "QUEUED"
    assert finalized["lastConversationErrorCode"] == "CODEX_SESSION_ACCESS_DENIED"
    assert "FINAL_SYNC_FAILED" in finalized["conversationWarnings"]


def test_cli_registers_all_session_adapter_commands() -> None:
    parser = build_parser()
    for action in (
        "discover",
        "list",
        "inspect",
        "attach",
        "detach",
        "sync",
        "import",
        "doctor",
    ):
        argv = ["codex", "sessions", action]
        if action == "inspect":
            argv += ["--source-session", "thr_1"]
        elif action in {"attach"}:
            argv += ["--capture-session", "cap_1", "--source-session", "thr_1"]
        elif action in {"detach", "sync"}:
            argv += ["--capture-session", "cap_1"]
        elif action == "import":
            argv += ["--capture-session", "cap_1", "--source-file", "export.json"]
        parsed = parser.parse_args(argv)
        assert parsed.sessions_action == action
