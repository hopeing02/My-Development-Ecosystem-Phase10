"""Commit-scoped, loopback-only FastAPI deployment using the existing runtime."""

from __future__ import annotations

import http.client
import argparse
import io
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import psutil

from mde.git import repository as git
from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


class DeploymentError(RuntimeError):
    """A local release could not be started, verified, or managed."""


def _directory(root: Path, name: str) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name):
        raise DeploymentError(
            "Deployment name must use lowercase letters, digits and hyphens."
        )
    directory = (root / ".mde" / "deployments" / name).resolve()
    if not directory.is_relative_to(root.resolve()):
        raise DeploymentError("Deployment directory must remain inside the repository.")
    return directory


def _read_state(directory: Path) -> dict[str, Any]:
    path = directory / "state.json"
    if not path.exists():
        return {"version": 1, "current": None, "previous": None, "retired": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("version") != 1:
            raise ValueError("Unsupported state version.")
        if not all(
            state.get(key) is None or isinstance(state[key], dict)
            for key in ("current", "previous")
        ):
            raise ValueError("Invalid deployment record.")
        if not isinstance(state.get("retired", []), list):
            raise ValueError("Invalid retired deployment list.")
        return state
    except (OSError, ValueError) as error:
        raise DeploymentError(f"Invalid deployment state: {path}") from error


def _write_state(directory: Path, state: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f"state-{uuid4().hex}.tmp"
    try:
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, directory / "state.json")
    finally:
        temporary.unlink(missing_ok=True)


def _owned_process(record: dict[str, Any] | None) -> psutil.Process | None:
    if not record:
        return None
    try:
        process = psutil.Process(int(record["pid"]))
        if abs(process.create_time() - float(record["created"])) > 0.001:
            return None
        if process.cmdline()[1:] != record["command"][1:]:
            return None
        return process if process.is_running() else None
    except (psutil.Error, KeyError, TypeError, ValueError):
        return None


def _stop(record: dict[str, Any] | None) -> bool:
    process = _owned_process(record)
    if process is None:
        return False
    try:
        processes = list(reversed(process.children(recursive=True))) + [process]
        for child in processes:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(processes, timeout=5)
        for child in alive:
            child.kill()
        psutil.wait_procs(alive, timeout=5)
        return True
    except psutil.NoSuchProcess:
        return True


def _listener(record: dict[str, Any] | None) -> psutil.Process | None:
    process = _owned_process(record)
    if process is None or record is None:
        return None
    try:
        processes = [process, *process.children(recursive=True)]
        return next(
            (
                child
                for child in processes
                if any(
                    item.status == psutil.CONN_LISTEN
                    and item.laddr.port == record["port"]
                    for item in child.net_connections(kind="tcp")
                )
            ),
            None,
        )
    except psutil.Error:
        return None


def _healthy(record: dict[str, Any] | None) -> bool:
    if _listener(record) is None or record is None:
        return False
    connection = None
    try:
        connection = http.client.HTTPConnection(
            "127.0.0.1", record["port"], timeout=0.5
        )
        connection.request("GET", record["health_path"])
        response = connection.getresponse()
        return response.status == 200
    except (OSError, http.client.HTTPException, psutil.Error):
        return False
    finally:
        if connection is not None:
            connection.close()


def _snapshot(root: Path, release: Path, commit: str) -> None:
    result = subprocess.run(
        ["git", "archive", "--format=zip", commit],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise DeploymentError(result.stderr.decode(errors="replace"))
    release.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(result.stdout)) as archive:
        for entry in archive.infolist():
            destination = (release / entry.filename).resolve()
            if not destination.is_relative_to(release):
                raise DeploymentError("Snapshot entry escapes the release directory.")
        archive.extractall(release)


def deploy_local(
    repository_root: Path,
    *,
    app: str,
    app_dir: str = ".",
    python: str = sys.executable,
    health_path: str = "/health",
    timeout: float = 20,
    name: str = "local",
) -> dict[str, Any]:
    """Start a committed candidate; keep the previous service until health succeeds."""
    from mde.task.concurrency import TaskExecutionLock

    root = git.ensure_repository(repository_root)
    directory = _directory(root, name)
    if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", app):
        raise DeploymentError("App must be a module:attribute ASGI import string.")
    if not re.fullmatch(r"/[A-Za-z0-9_/-]*", health_path):
        raise DeploymentError(
            "Health path must be a local path without query or redirects."
        )
    if not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise DeploymentError("Health timeout must be between 0 and 120 seconds.")
    if git.changed_files(root):
        raise DeploymentError(
            "Commit and validate changes before deployment; worktree must be clean."
        )
    executable = Path(python).resolve()
    if not executable.is_file():
        raise DeploymentError(f"Python executable does not exist: {executable}")
    with TaskExecutionLock(root, f"deploy-{name}"):
        state = _read_state(directory)
        commit = git.get_local_head(root)
        release = directory / "releases" / f"{commit[:12]}-{uuid4().hex[:12]}"
        _snapshot(root, release, commit)
        source = (release / app_dir).resolve()
        if not source.is_relative_to(release) or not source.is_dir():
            raise DeploymentError(
                "App directory must exist inside the committed snapshot."
            )
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        command = [
            str(executable),
            "-m",
            "uvicorn",
            app,
            "--app-dir",
            str(source),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            (str(source), str(release / "packages/mde-core/src"), str(release))
        )
        record = None
        promoted = False
        try:
            with (release / "service.log").open("ab") as log:
                process = subprocess.Popen(
                    command,
                    cwd=release,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    start_new_session=os.name != "nt",
                )
            record = {
                "commit": commit,
                "pid": process.pid,
                "created": psutil.Process(process.pid).create_time(),
                "command": command,
                "release": str(release),
                "port": port,
                "health_path": health_path,
                "url": f"http://127.0.0.1:{port}",
            }
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                if _healthy(record):
                    break
                time.sleep(0.1)
            if not _healthy(record):
                raise DeploymentError(
                    f"Candidate health check failed. Previous deployment retained. Log: {release / 'service.log'}"
                )
            listener = _listener(record)
            if listener is None:
                raise DeploymentError("Candidate exited before promotion.")
            record.update(
                pid=listener.pid,
                created=listener.create_time(),
                command=listener.cmdline(),
            )
            retired = list(state.get("retired", []))
            if state.get("previous"):
                retired.append(state["previous"])
            pending = []
            for old in retired:
                try:
                    _stop(old)
                except psutil.Error:
                    pending.append(old)
            _write_state(
                directory,
                {
                    "version": 1,
                    "current": record,
                    "previous": state.get("current"),
                    "retired": pending,
                },
            )
            promoted = True
            return {"status": "healthy", **record}
        finally:
            if not promoted and record is not None:
                _stop(record)


def deployment_status(repository_root: Path, name: str = "local") -> dict[str, Any]:
    """Read local deployment state without creating directories or changing processes."""
    state = _read_state(_directory(repository_root.resolve(), name))
    return {
        **state,
        "status": "healthy" if _healthy(state.get("current")) else "stopped",
    }


def manage_deployment(
    repository_root: Path, action: str, name: str = "local"
) -> dict[str, Any]:
    """Roll back the active pointer or stop only processes owned by this deployment."""
    from mde.task.concurrency import TaskExecutionLock

    root = repository_root.resolve()
    directory = _directory(root, name)
    with TaskExecutionLock(root, f"deploy-{name}"):
        state = _read_state(directory)
        if action == "rollback":
            if not _healthy(state.get("previous")):
                raise DeploymentError("No healthy previous deployment is available.")
            state["current"], state["previous"] = state["previous"], state["current"]
            _write_state(directory, state)
            return {"status": "healthy", **state["current"]}
        if action != "stop":
            raise DeploymentError(f"Unsupported deployment action: {action}")
        for record in [
            state.get("current"),
            state.get("previous"),
            *state.get("retired", []),
        ]:
            _stop(record)
        _write_state(
            directory, {"version": 1, "current": None, "previous": None, "retired": []}
        )
        return {"status": "stopped"}


class LocalDeploymentPlugin:
    """Connect explicit local deployment to the existing Workflow command registry."""

    name = "deployment"

    @staticmethod
    def run(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
        tested = any(
            type(output.get("return_code")) is int and output["return_code"] == 0
            for output in context.outputs.values()
        )
        if not tested:
            raise DeploymentError(
                "Local deployment requires a successful real test result."
            )
        commit = context.data.get("commit_hash")
        if not commit or commit != git.get_local_head(context.repository_root):
            raise DeploymentError(
                "Local deployment requires the tested workflow commit."
            )
        configured = context.data.get("inputs", {}).get("deployment", {})
        if not isinstance(configured, dict):
            raise DeploymentError("Deployment inputs must be an object.")
        return deploy_local(context.repository_root, **{**configured, **step.args})

    def register(self, registry: CommandRegistry) -> None:
        registry.register("deploy.local", self.run)


def register_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "deploy", help="Deploy and manage local FastAPI releases."
    )
    actions = parser.add_subparsers(dest="deploy_action")
    local = actions.add_parser(
        "local", help="Deploy committed code to a new loopback port."
    )
    local.add_argument("--app", required=True)
    local.add_argument("--app-dir", default=".")
    local.add_argument("--python", default=sys.executable)
    local.add_argument("--health-path", default="/health")
    local.add_argument("--timeout", type=float, default=20)
    for action in (
        local,
        *(actions.add_parser(name) for name in ("status", "rollback", "stop")),
    ):
        action.add_argument("--name", default="local")


def run(args: argparse.Namespace) -> int:
    try:
        if args.deploy_action == "local":
            result = deploy_local(
                Path.cwd(),
                app=args.app,
                app_dir=args.app_dir,
                python=args.python,
                health_path=args.health_path,
                timeout=args.timeout,
                name=args.name,
            )
        elif args.deploy_action == "status":
            result = deployment_status(Path.cwd(), args.name)
        elif args.deploy_action in {"rollback", "stop"}:
            result = manage_deployment(Path.cwd(), args.deploy_action, args.name)
        else:
            print("Use deploy local, status, rollback, or stop.")
            return 2
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "healthy" or args.deploy_action == "stop" else 1
    except (RuntimeError, OSError, ValueError, psutil.Error) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
