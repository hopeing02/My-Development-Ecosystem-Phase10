import json
import subprocess
from pathlib import Path

import pytest

from mde.ai.errors import (
    AIConfigurationError,
    AIResponseValidationError,
    AITransportError,
)
from mde.ai.models import AIRequest
from mde.ai.providers.codex import CodexCLIProvider


@pytest.fixture
def cli(monkeypatch):
    state = {
        "returncode": 0,
        "document": {
            "summary": "generated",
            "approved": False,
            "artifacts": [
                {"path": "service.py", "content": "hello", "media_type": "text/plain"}
            ],
        },
    }
    monkeypatch.setattr(
        "mde.ai.providers.codex.shutil.which", lambda value: "codex.exe"
    )

    class Process:
        def __init__(self, command, **kwargs):
            state["command"] = command
            state["kwargs"] = kwargs
            self.returncode = state["returncode"]

        def communicate(self, prompt, timeout):
            state["prompt"] = prompt
            state["timeout"] = timeout
            command = state["command"]
            schema = json.loads(
                Path(command[command.index("--output-schema") + 1]).read_text()
            )
            assert schema["additionalProperties"] is False
            if state["document"] is not None:
                Path(command[command.index("--output-last-message") + 1]).write_text(
                    json.dumps(state["document"]), encoding="utf-8"
                )
            return ("ignored stdout", "PRIVATE diagnostics")

    monkeypatch.setattr(subprocess, "Popen", Process)
    return state


def request(tmp_path, action="generate"):
    return AIRequest(
        action,
        "change service",
        tmp_path,
        context={"files": [{"path": "service.py", "content": "existing"}]},
    )


def test_codex_uses_stdin_readonly_schema_and_existing_contract(
    tmp_path, cli, monkeypatch
):
    monkeypatch.setenv("MDE_CODEX_MODEL", "configured-test-model")
    response = CodexCLIProvider().execute(request(tmp_path))
    assert response.provider == "codex"
    assert response.artifacts[0].content == "hello"
    assert cli["command"][1:7] == [
        "-a",
        "never",
        "exec",
        "--sandbox",
        "read-only",
        "--ephemeral",
    ]
    assert cli["command"][-1] == "-"
    assert "--model" in cli["command"]
    assert "existing" in cli["prompt"]
    assert "shell" not in cli["kwargs"]


@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"summary": "ok", "artifacts": [], "approved": False},
        {"summary": "ok", "artifacts": [], "approved": "true"},
    ],
)
def test_codex_missing_or_invalid_response_fails(tmp_path, cli, document):
    cli["document"] = document
    with pytest.raises(AIResponseValidationError):
        CodexCLIProvider().execute(request(tmp_path))


def test_codex_nonzero_does_not_leak_diagnostics_or_fallback(tmp_path, cli):
    cli["returncode"] = 1
    with pytest.raises(AITransportError) as error:
        CodexCLIProvider().execute(request(tmp_path))
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("approved", [False, True])
def test_codex_review_preserves_boolean_verdict(tmp_path, cli, approved):
    cli["document"] = {"summary": "reviewed", "artifacts": [], "approved": approved}
    assert (
        CodexCLIProvider().execute(request(tmp_path, "review")).metadata["approved"]
        is approved
    )


def test_codex_missing_installation_and_invalid_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr("mde.ai.providers.codex.shutil.which", lambda value: None)
    with pytest.raises(AIConfigurationError, match="not found"):
        CodexCLIProvider().execute(request(tmp_path))
    monkeypatch.setattr(
        "mde.ai.providers.codex.shutil.which", lambda value: "codex.exe"
    )
    for timeout in ["invalid", "nan", "0", "1801"]:
        monkeypatch.setenv("MDE_CODEX_TIMEOUT", timeout)
        with pytest.raises(AIConfigurationError, match="TIMEOUT"):
            CodexCLIProvider().execute(request(tmp_path))


def test_codex_timeout_stops_own_process_tree(tmp_path, monkeypatch):
    stopped = []
    monkeypatch.setattr(
        "mde.ai.providers.codex.shutil.which", lambda value: "codex.exe"
    )

    class Process:
        pid = 123
        calls = 0

        def communicate(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("codex", 1)
            return ("", "")

        def kill(self):
            stopped.append("parent")

    class Owned:
        def __init__(self, pid):
            assert pid == 123

        def children(self, recursive):
            return [self]

        def kill(self):
            stopped.append("child")

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr("mde.ai.providers.codex.psutil.Process", Owned)
    with pytest.raises(AITransportError, match="timed out"):
        CodexCLIProvider().execute(request(tmp_path))
    assert stopped == ["child", "parent"]
