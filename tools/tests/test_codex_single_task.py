from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from tools.automation import run_codex_single_task as runner


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    for args in (
        ("init",),
        ("config", "user.name", "W1 Test"),
        ("config", "user.email", "w1@example.invalid"),
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    (root / "example.py").write_text("value = 0\n", encoding="utf-8")
    (root / ".gitignore").write_text(".mde/\n__pycache__/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True
    )
    return root


def request_file(tmp_path, project, **overrides):
    data = {
        "taskId": "TASK-001",
        "stepId": "MDE-CODEX-W1",
        "projectPath": str(project),
        "requirement": "Change value to 1",
        "allowedFiles": ["example.py"],
        "validationCommands": [[sys.executable, "-c", "assert True"]],
        "timeoutSeconds": 30,
    }
    data.update(overrides)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def fake_codex(monkeypatch, project, *, paths=None, code=0):
    def execute(task, directory):
        for path, content in (paths or {"example.py": "value = 1\n"}).items():
            (project / path).parent.mkdir(parents=True, exist_ok=True)
            (project / path).write_text(content, encoding="utf-8")
        return (
            runner.ValidationResult(("codex",), code, "", "diagnostic"),
            "implemented",
        )

    monkeypatch.setattr(runner, "_run_codex", execute)


def read_result(tmp_path, request, result=None):
    result = result or tmp_path / "result.json"
    code = runner.run_task(request, result)
    return code, json.loads(result.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "path",
    [
        "../x",
        "/x",
        "C:/x",
        "C:x",
        "//host/x",
        ".",
        "a/../../b",
        ".git/config",
        "a:stream",
        "nul",
        "a./b",
    ],
)
def test_reject_unsafe_paths(path):
    with pytest.raises(runner.CodexDevelopmentError):
        runner._normalize_repo_path(path)


def test_directory_allowlist_retains_boundary():
    allowed = (runner._normalize_repo_path("./src\\nested\\"),)
    assert allowed == ("src/nested/",)
    assert runner._is_allowed_path("src/nested/a.py", allowed)
    assert not runner._is_allowed_path("src/nested-other/a.py", allowed)


@pytest.mark.parametrize(
    "overrides",
    [
        {"taskId": "../bad"},
        {"stepId": ""},
        {"requirement": None},
        {"allowedFiles": [123]},
        {"validationCommands": [[""]]},
        {"timeoutSeconds": True},
        {"timeoutSeconds": 29},
        {"timeoutSeconds": "30"},
    ],
)
def test_invalid_request_writes_failure(tmp_path, project, overrides):
    code, result = read_result(tmp_path, request_file(tmp_path, project, **overrides))
    assert code == 1 and result["success"] is False
    assert result["error"] and result["codexExitCode"] is None


def test_invalid_json_writes_failure(tmp_path):
    request = tmp_path / "invalid.json"
    request.write_text("{", encoding="utf-8")
    code, result = read_result(tmp_path, request)
    assert code == 1 and result["error"]


def test_dirty_tree_does_not_call_codex(tmp_path, project, monkeypatch):
    (project / "example.py").write_text("preserve me", encoding="utf-8")
    monkeypatch.setattr(runner, "_run_codex", lambda *args: pytest.fail("must stop"))
    code, result = read_result(tmp_path, request_file(tmp_path, project))
    assert code == 1 and "not clean" in result["error"]
    assert (project / "example.py").read_text() == "preserve me"


def test_success_runs_real_validation(tmp_path, project, monkeypatch):
    fake_codex(monkeypatch, project)
    command = [sys.executable, "-c", "from example import value; assert value == 1"]
    code, result = read_result(
        tmp_path, request_file(tmp_path, project, validationCommands=[command])
    )
    assert code == 0 and result["success"]
    assert result["changedFiles"] == ["example.py"]
    assert result["validationResults"][0]["success"]


def test_outside_changes_fail_before_validation(tmp_path, project, monkeypatch):
    fake_codex(monkeypatch, project, paths={"outside.py": "bad"})
    code, result = read_result(tmp_path, request_file(tmp_path, project))
    assert code == 1 and result["disallowedFiles"] == ["outside.py"]
    assert result["validationResults"] == []
    assert (project / "outside.py").exists()  # Do not destroy evidence on failure.


def test_validation_changes_are_rechecked(tmp_path, project, monkeypatch):
    fake_codex(monkeypatch, project)
    command = [
        sys.executable,
        "-c",
        "from pathlib import Path; Path('outside.py').write_text('bad')",
    ]
    code, result = read_result(
        tmp_path, request_file(tmp_path, project, validationCommands=[command])
    )
    assert code == 1 and result["disallowedFiles"] == ["outside.py"]
    assert result["validationResults"][0]["success"]


def test_validation_failure_stops_next_command(tmp_path, project, monkeypatch):
    fake_codex(monkeypatch, project)
    commands = [[sys.executable, "-c", "raise SystemExit(7)"], ["never-execute"]]
    code, result = read_result(
        tmp_path, request_file(tmp_path, project, validationCommands=commands)
    )
    assert code == 1 and len(result["validationResults"]) == 1
    assert result["validationResults"][0]["exitCode"] == 7


def test_codex_failure_keeps_changes_and_diagnostics(tmp_path, project, monkeypatch):
    fake_codex(monkeypatch, project, code=124)
    code, result = read_result(tmp_path, request_file(tmp_path, project))
    assert code == 1 and result["codexExitCode"] == 124
    assert result["changedFiles"] == ["example.py"]
    assert result["codexStderr"] == "diagnostic"
    assert result["validationResults"] == []


def test_missing_codex_writes_failure(tmp_path, project, monkeypatch):
    monkeypatch.setenv("MDE_CODEX_EXECUTABLE", str(tmp_path / "missing.exe"))
    code, result = read_result(tmp_path, request_file(tmp_path, project))
    assert code == 1 and "not found" in result["error"]


def test_output_under_ignored_directory_is_supported(tmp_path, project, monkeypatch):
    fake_codex(monkeypatch, project)
    code, result = read_result(
        tmp_path, request_file(tmp_path, project), project / ".mde" / "result.json"
    )
    assert code == 0 and result["disallowedFiles"] == []


def test_output_cannot_overwrite_project_code(tmp_path, project):
    with pytest.raises(runner.CodexDevelopmentError, match="ignored"):
        runner.run_task(request_file(tmp_path, project), project / "example.py")
    assert (project / "example.py").read_text() == "value = 0\n"


def test_invalid_request_cannot_overwrite_project_code(tmp_path, project):
    request = tmp_path / "invalid.json"
    request.write_text("{", encoding="utf-8")
    with pytest.raises(runner.CodexDevelopmentError, match="ignored"):
        runner.run_task(request, project / "example.py")
    assert (project / "example.py").read_text() == "value = 0\n"


def test_null_delimited_git_paths_and_rename(tmp_path, project):
    baseline = runner.get_local_head(project)
    (project / "example.py").rename(project / "한글 file.py")
    assert runner._collect_changed_files(project, baseline) == (
        "example.py",
        "한글 file.py",
    )


def test_committed_changes_are_detected(tmp_path, project, monkeypatch):
    original = runner.get_local_head(project)

    def execute(task, directory):
        (project / "example.py").write_text("value = 1\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "."], cwd=project, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "forbidden fixture change"],
            cwd=project,
            check=True,
            capture_output=True,
        )
        return runner.ValidationResult(("codex",), 0, "", ""), "changed"

    monkeypatch.setattr(runner, "_run_codex", execute)
    code, result = read_result(tmp_path, request_file(tmp_path, project))
    assert code == 1 and "HEAD changed" in result["error"]
    assert result["changedFiles"] == ["example.py"]
    assert runner.get_local_head(project) != original


def test_cli_arguments_reuse_existing_executable(tmp_path, project, monkeypatch):
    task = runner._load_task(request_file(tmp_path, project))
    monkeypatch.setattr(
        runner, "_resolve_codex_executable", lambda: "existing-codex.exe"
    )

    def execute(command, root, timeout, prompt):
        assert command[:4] == ("existing-codex.exe", "-a", "never", "exec")
        assert command[4:6] == ("--sandbox", "workspace-write")
        assert command[-1] == "-" and root == project and timeout == 30
        assert "Do not commit" in prompt and "example.py" in prompt
        (tmp_path / "codex-last-message.txt").write_text("done", encoding="utf-8")
        return runner.ValidationResult(command, 0, "", "")

    monkeypatch.setattr(runner, "_run_process", execute)
    assert runner._run_codex(task, tmp_path)[1] == "done"


def test_missing_validation_executable(tmp_path):
    result = runner._run_process((str(tmp_path / "missing.exe"),), tmp_path, 30)
    assert result.exit_code == 127 and not result.success


def test_timeout_kills_descendant(tmp_path):
    marker = tmp_path / "child.pid"
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import subprocess, sys, time; from pathlib import Path; "
        f"p = subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        f"Path({str(marker)!r}).write_text(str(p.pid)); time.sleep(60)"
    )
    result = runner._run_process((sys.executable, "-c", parent_code), tmp_path, 2)
    assert result.exit_code == 124 and "timed out" in result.stderr
    pid = int(marker.read_text())
    try:
        process = runner.psutil.Process(pid)
    except runner.psutil.NoSuchProcess:
        return
    assert not process.is_running() or process.status() == runner.psutil.STATUS_ZOMBIE


def test_redacts_diagnostic_secrets(tmp_path):
    path = tmp_path / "result.json"
    runner._write_result(path, {"error": "password=unittest-secret"})
    assert "unittest-secret" not in path.read_text()


@pytest.mark.skipif(
    os.name == "nt", reason="Windows symlink creation requires OS privilege"
)
def test_disallow_symlink_escape(tmp_path, project):
    (project / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(runner.CodexDevelopmentError, match="link"):
        runner._load_task(request_file(tmp_path, project, allowedFiles=["link/out.py"]))
