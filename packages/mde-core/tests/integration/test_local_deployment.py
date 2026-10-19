import http.client
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import psutil
import pytest

from mde.git import repository as git
from mde.plugins.builtin.deployment import (
    DeploymentError,
    LocalDeploymentPlugin,
    deploy_local,
    deployment_status,
    manage_deployment,
    _snapshot,
)
from mde.task.concurrency import TaskExecutionLock, TaskLockError
from mde.workflow.models import WorkflowContext, WorkflowStep


@pytest.mark.skipif(os.name != "nt", reason="Windows MAX_PATH regression")
def test_snapshot_extracts_tracked_paths_beyond_windows_limit(tmp_path, monkeypatch):
    content = io.BytesIO()
    member = "/".join(["nested-source"] * 20) + "/file.txt"
    with zipfile.ZipFile(content, "w") as archive:
        archive.writestr(member, "tracked content")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, content.getvalue()
        ),
    )
    release = tmp_path / "release"
    _snapshot(tmp_path, release, "HEAD")
    destination = Path("\\\\?\\" + str(release / member))
    assert destination.read_text() == "tracked content"


@pytest.fixture
def repository(tmp_path: Path):
    git.run_git("init", "-b", "main", repository_root=tmp_path)
    git.run_git("config", "user.name", "MDE Test", repository_root=tmp_path)
    git.run_git("config", "user.email", "mde@example.test", repository_root=tmp_path)
    (tmp_path / ".gitignore").write_text(
        ".mde/\nlogs/\n__pycache__/\n.pytest_cache/\n", encoding="utf-8"
    )
    (tmp_path / "service.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n"
        '@app.get("/health")\ndef health():\n    return {"version": "one"}\n',
        encoding="utf-8",
    )
    git.add(repository_root=tmp_path)
    git.commit("seed service", repository_root=tmp_path)
    try:
        yield tmp_path
    finally:
        manage_deployment(tmp_path, "stop")


def request(record: dict) -> dict:
    connection = http.client.HTTPConnection("127.0.0.1", record["port"], timeout=2)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        assert response.status == 200
        return json.loads(response.read())
    finally:
        connection.close()


def test_local_lifecycle_snapshot_health_rollback_and_stop(repository: Path) -> None:
    first = deploy_local(repository, app="service:app", timeout=10)
    assert request(first) == {"version": "one"}
    assert Path(first["release"]).is_relative_to(repository / ".mde")
    source = repository / "service.py"
    source.write_text(source.read_text().replace('"one"', '"two"'), encoding="utf-8")
    git.add(repository_root=repository)
    git.commit("second version", repository_root=repository)
    second = deploy_local(repository, app="service:app", timeout=10)
    assert request(second) == {"version": "two"}
    assert request(first) == {"version": "one"}
    assert first["commit"] != second["commit"]
    rolled = manage_deployment(repository, "rollback")
    assert rolled["pid"] == first["pid"]
    assert request(rolled) == {"version": "one"}
    third = deploy_local(repository, app="service:app", timeout=10)
    assert request(third) == {"version": "two"}
    assert request(first) == {"version": "one"}
    assert not psutil.pid_exists(second["pid"])
    assert git.changed_files(repository) == ()
    assert manage_deployment(repository, "stop")["status"] == "stopped"
    assert deployment_status(repository)["status"] == "stopped"
    assert not psutil.pid_exists(first["pid"])
    assert not psutil.pid_exists(third["pid"])


@pytest.mark.parametrize("failure", ["import", "health"])
def test_failed_candidate_retains_previous_release(
    repository: Path, failure: str
) -> None:
    first = deploy_local(repository, app="service:app", timeout=10)
    state_path = repository / ".mde/deployments/local/state.json"
    before = state_path.read_bytes()
    app = "missing:app"
    if failure == "health":
        source = repository / "service.py"
        source.write_text(
            source.read_text().replace('"/health"', '"/other"'), encoding="utf-8"
        )
        git.add(repository_root=repository)
        git.commit("broken health", repository_root=repository)
        app = "service:app"
    with pytest.raises(DeploymentError, match="health check failed"):
        deploy_local(repository, app=app, timeout=1)
    assert state_path.read_bytes() == before
    assert request(first) == {"version": "one"}
    assert deployment_status(repository)["current"]["pid"] == first["pid"]


def test_promotion_write_failure_keeps_old_state(repository: Path, monkeypatch) -> None:
    first = deploy_local(repository, app="service:app", timeout=10)
    path = repository / ".mde/deployments/local/state.json"
    before = path.read_bytes()
    with monkeypatch.context() as patch:

        def fail_write(*args):
            raise OSError("disk unavailable")

        patch.setattr("mde.plugins.builtin.deployment._write_state", fail_write)
        with pytest.raises(OSError, match="disk unavailable"):
            deploy_local(repository, app="service:app", timeout=10)
    assert path.read_bytes() == before
    assert request(first) == {"version": "one"}


@pytest.mark.parametrize(
    "options",
    [
        {"name": "../outside"},
        {"app": "service;exit:app"},
        {"app_dir": "../outside"},
        {"health_path": "http://example.test/health"},
        {"timeout": -1},
        {"timeout": float("nan")},
        {"python": "missing-python"},
    ],
)
def test_rejects_invalid_deployment_input(repository: Path, options: dict) -> None:
    arguments = {"app": "service:app", **options}
    with pytest.raises(DeploymentError):
        deploy_local(repository, **arguments)


def test_dirty_source_and_parallel_deploy_are_rejected(repository: Path) -> None:
    source = repository / "service.py"
    original = source.read_bytes()
    source.write_bytes(original + b"\n# dirty\n")
    with pytest.raises(DeploymentError, match="worktree must be clean"):
        deploy_local(repository, app="service:app")
    source.write_bytes(original)
    with TaskExecutionLock(repository, "deploy-local"):
        with pytest.raises(TaskLockError):
            deploy_local(repository, app="service:app")


def test_status_without_state_is_read_only(repository: Path) -> None:
    assert not (repository / ".mde").exists()
    assert deployment_status(repository)["status"] == "stopped"
    assert not (repository / ".mde").exists()
    with pytest.raises(DeploymentError, match="No healthy previous"):
        manage_deployment(repository, "rollback")


def test_cli_release_survives_launcher_and_can_be_stopped(repository: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mde.cli",
            "deploy",
            "local",
            "--app",
            "service:app",
            "--timeout",
            "10",
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )
    record = json.loads(result.stdout)
    assert request(record) == {"version": "one"}
    status = subprocess.run(
        [sys.executable, "-m", "mde.cli", "deploy", "status"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(status.stdout)["status"] == "healthy"
    subprocess.run(
        [sys.executable, "-m", "mde.cli", "deploy", "stop"],
        cwd=repository,
        capture_output=True,
        check=True,
    )
    assert not psutil.pid_exists(record["pid"])


def test_public_workflow_cli_generates_tests_commits_and_deploys(
    repository: Path, tmp_path: Path
) -> None:
    test_file = repository / "test_service.py"
    test_file.write_text(
        'import service\ndef test_service():\n    assert service.health()["version"] == "two"\n',
        encoding="utf-8",
    )
    git.add(repository_root=repository)
    git.commit("seed test", repository_root=repository)
    before = git.get_local_head(repository)
    inputs = tmp_path.parent / f"{tmp_path.name}-inputs.json"
    inputs.write_text(
        json.dumps(
            {
                "ai": {
                    "provider": "mock",
                    "artifacts": [
                        {
                            "path": "service.py",
                            "content": (repository / "service.py")
                            .read_text()
                            .replace('"one"', '"two"'),
                        }
                    ],
                },
                "testing_command": [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--noconftest",
                ],
                "deployment": {"app": "service:app", "timeout": 10},
                "push": False,
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mde.cli",
            "workflow",
            "run",
            "feature-local",
            "--runtime",
            "--inputs",
            str(inputs),
            "--max-fix-attempts",
            "1",
            "--message",
            "acceptance local deployment",
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Workflow completed: feature-local" in result.stdout
    assert "[skipped] push" in result.stdout
    assert "Deployment URL:" in result.stdout
    assert git.get_local_head(repository) != before
    state = deployment_status(repository)
    assert request(state["current"]) == {"version": "two"}
    assert state["current"]["commit"] == git.get_local_head(repository)
    assert git.changed_files(repository) == ()


def test_workflow_deployment_requires_tests_and_current_commit(
    repository: Path,
) -> None:
    context = WorkflowContext("test", repository_root=repository)
    step = WorkflowStep("deploy", "deploy.local", args={"app": "service:app"})
    with pytest.raises(DeploymentError, match="real test"):
        LocalDeploymentPlugin.run(context, step)
    context.outputs["test"] = {"return_code": 0}
    context.data["commit_hash"] = "wrong"
    with pytest.raises(DeploymentError, match="tested workflow commit"):
        LocalDeploymentPlugin.run(context, step)


def test_owned_process_check_does_not_stop_unrelated_pid(repository: Path) -> None:
    from mde.plugins.builtin.deployment import _stop

    first = deploy_local(repository, app="service:app", timeout=10)
    victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert not _stop({**first, "created": first["created"] + 1})
        forged = {
            **first,
            "pid": victim.pid,
            "created": psutil.Process(victim.pid).create_time(),
        }
        assert not _stop(forged)
        assert victim.poll() is None
        assert request(first) == {"version": "one"}
    finally:
        victim.terminate()
        victim.wait(timeout=5)


def test_corrupt_state_is_not_overwritten(repository: Path) -> None:
    path = repository / ".mde/deployments/local/state.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"invalid state")
    try:
        with pytest.raises(DeploymentError, match="Invalid deployment state"):
            deploy_local(repository, app="service:app")
        assert path.read_bytes() == b"invalid state"
    finally:
        path.unlink()
