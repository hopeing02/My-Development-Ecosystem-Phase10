from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mde.sync.engine import SyncError, run_mobile_sync
from mde.sync.models import SyncPolicy
from mde.task.store import TaskStore
from mde.task.types import TaskResult, utc_now


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _prepare_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "MDE Test")
    _git(root, "config", "user.email", "mde-test@example.invalid")
    (root / ".gitignore").write_text(".mde/\n", encoding="utf-8")


def _task_file(
    root: Path,
    order: int,
    task_id: str,
    depends_on: tuple[str, ...] = (),
    *,
    branch: str = "feature/g2-batch",
) -> None:
    destination = root / "tasks" / "pending" / f"{order:02d}-{task_id}.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    dependency_yaml = "".join(f"      - {item}\n" for item in depends_on)
    content = (
        "version: 1\n"
        "task:\n"
        f"  id: {task_id}\n"
        "  type: feature\n"
        f"  title: {task_id}\n"
        "  workflow: feature\n"
        "  repository:\n"
        f"    branch: {branch}\n"
        "    base_branch: main\n"
        "  execution:\n"
        "    auto_apply: true\n"
        "    run_tests: true\n"
        "    auto_save: true\n"
        "    auto_push: false\n"
        "  metadata:\n"
        "    batch_id: G2-BATCH\n"
        + ("    depends_on:\n" + dependency_yaml if depends_on else "")
    )
    destination.write_text(content, encoding="utf-8")


def _run_as_completed(task, root: Path, *, store: TaskStore) -> TaskResult:
    active = store.claim(task)
    file = root / "step-history.txt"
    existing = file.read_text(encoding="utf-8") if file.exists() else ""
    file.write_text(existing + task.task_id + "\n", encoding="utf-8")
    now = utc_now()
    result = TaskResult(
        task_id=active.task_id,
        status="completed",
        workflow=active.workflow,
        started_at=now,
        completed_at=now,
    )
    store.complete(active, result)
    return result


def _run_batch(root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("mde.sync.engine.git.fetch", lambda **kwargs: None)
    monkeypatch.setattr(
        "mde.sync.engine.git.has_remote_changes", lambda *args, **kwargs: False
    )
    return run_mobile_sync(
        root,
        policy=SyncPolicy(
            task_branches=True,
            auto_commit=True,
            auto_push=False,
            respect_task_policy=True,
        ),
        task_runner=_run_as_completed,
    )


def test_g2_batch_sequentially_commits_on_shared_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _task_file(tmp_path, 2, "STEP-002", ("STEP-001",))
    _task_file(tmp_path, 3, "STEP-003", ("STEP-002",))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: add pending batch")

    result = _run_batch(tmp_path, monkeypatch)
    assert result.completed_tasks == ("STEP-001", "STEP-002", "STEP-003")
    assert _git(tmp_path, "branch", "--show-current") == "main"
    assert _git(tmp_path, "status", "--porcelain") == ""
    assert _git(tmp_path, "show", "feature/g2-batch:step-history.txt") == (
        "STEP-001\nSTEP-002\nSTEP-003"
    )
    assert _git(tmp_path, "rev-list", "--count", "feature/g2-batch") == "4"
    assert (
        _git(tmp_path, "ls-tree", "-r", "--name-only", "feature/g2-batch").count(
            "tasks/completed/"
        )
        >= 3
    )

    # Repeated polling against main must not rerun completed batch tasks.
    second = _run_batch(tmp_path, monkeypatch)
    assert second.completed_tasks == ()
    assert _git(tmp_path, "show", "feature/g2-batch:step-history.txt") == (
        "STEP-001\nSTEP-002\nSTEP-003"
    )


def test_g2_rejects_out_of_order_dependency_before_branch_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001", ("STEP-002",))
    _task_file(tmp_path, 2, "STEP-002")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: invalid order")

    with pytest.raises(SyncError, match="must precede"):
        _run_batch(tmp_path, monkeypatch)
    assert _git(tmp_path, "branch", "--show-current") == "main"
    assert TaskStore(tmp_path).find("STEP-001")[0] == "pending"


def test_g2_rejects_different_batch_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _task_file(tmp_path, 2, "STEP-002", ("STEP-001",), branch="feature/other")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: inconsistent branches")

    with pytest.raises(SyncError, match="inconsistent branch"):
        _run_batch(tmp_path, monkeypatch)
    assert TaskStore(tmp_path).find("STEP-002")[0] == "pending"


def test_g2_failure_stops_next_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _task_file(tmp_path, 2, "STEP-002", ("STEP-001",))
    _task_file(tmp_path, 3, "STEP-003", ("STEP-002",))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: batch failure")
    monkeypatch.setattr("mde.sync.engine.git.fetch", lambda **kwargs: None)
    monkeypatch.setattr(
        "mde.sync.engine.git.has_remote_changes", lambda *args, **kwargs: False
    )
    visited: list[str] = []

    def runner(task, root: Path, *, store: TaskStore) -> TaskResult:
        visited.append(task.task_id)
        if task.task_id != "STEP-002":
            return _run_as_completed(task, root, store=store)
        active = store.claim(task)
        now = utc_now()
        result = TaskResult(
            task_id=active.task_id,
            status="failed",
            workflow=active.workflow,
            started_at=now,
            completed_at=now,
        )
        store.fail(active, result)
        return result

    with pytest.raises(SyncError, match="STEP-002"):
        run_mobile_sync(
            tmp_path,
            policy=SyncPolicy(
                task_branches=True,
                auto_commit=True,
                auto_push=False,
                respect_task_policy=True,
            ),
            task_runner=runner,
        )

    assert visited == ["STEP-001", "STEP-002"]
    assert TaskStore(tmp_path).find("STEP-003")[0] == "pending"
    assert "STEP-001" in _git(tmp_path, "show", "feature/g2-batch:step-history.txt")


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing", "not pending"),
        ("self", "must precede"),
        ("cycle", "must precede"),
        ("duplicate_id", "Duplicate pending"),
        ("duplicate_dependency", "invalid metadata.depends_on"),
        ("string_dependency", "invalid metadata.depends_on"),
        ("invalid_dependency", "invalid metadata.depends_on"),
        ("missing_batch", "batch_id is required"),
        ("different_batch", "different batches"),
        ("different_base", "inconsistent branch"),
        ("base_as_branch", "dedicated"),
        ("initial_as_branch", "dedicated"),
        ("no_apply", "auto_apply"),
        ("no_tests", "run_tests"),
        ("no_save", "auto_save"),
        ("mixed", "independent"),
    ],
)
def test_g2_invalid_plan_does_not_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, message: str
) -> None:
    import yaml

    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _task_file(tmp_path, 2, "STEP-002", ("STEP-001",))
    paths = sorted((tmp_path / "tasks/pending").glob("*.yaml"))
    first, second = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in paths]
    task = second["task"]
    if case == "missing":
        task["metadata"]["depends_on"] = ["ABSENT"]
    elif case == "self":
        task["metadata"]["depends_on"] = ["STEP-002"]
    elif case == "cycle":
        first["task"]["metadata"]["depends_on"] = ["STEP-002"]
    elif case == "duplicate_id":
        task["id"] = "STEP-001"
    elif case == "duplicate_dependency":
        task["metadata"]["depends_on"] = ["STEP-001", "STEP-001"]
    elif case == "string_dependency":
        task["metadata"]["depends_on"] = "STEP-001"
    elif case == "invalid_dependency":
        task["metadata"]["depends_on"] = [{}]
    elif case == "missing_batch":
        del task["metadata"]["batch_id"]
    elif case == "different_batch":
        task["metadata"]["batch_id"] = "OTHER"
    elif case == "different_base":
        task["repository"]["base_branch"] = "other-base"
    elif case == "base_as_branch":
        first["task"]["repository"]["branch"] = "main"
    elif case == "initial_as_branch":
        first["task"]["repository"] = {"branch": "main", "base_branch": "develop"}
    elif case.startswith("no_"):
        task["execution"][
            {"no_apply": "auto_apply", "no_tests": "run_tests", "no_save": "auto_save"}[
                case
            ]
        ] = False
    elif case == "mixed":
        task["metadata"] = {}
    for path, payload in zip(paths, (first, second)):
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: invalid batch")
    with pytest.raises(SyncError, match=message):
        _run_batch(tmp_path, monkeypatch)
    assert _git(tmp_path, "branch", "--show-current") == "main"
    assert _git(tmp_path, "status", "--porcelain") == ""
    assert not (tmp_path / "step-history.txt").exists()


@pytest.mark.parametrize("setting", ["auto_commit", "task_branches"])
def test_g2_requires_branch_commits(tmp_path: Path, setting: str) -> None:
    from mde.sync.engine import _validate_batch_plan

    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    policy = SyncPolicy(**{"auto_commit": True, "task_branches": True, setting: False})
    with pytest.raises(SyncError, match="requires task branches and commits"):
        _validate_batch_plan(TaskStore(tmp_path).list(), policy, "main")


def test_g2_commit_failure_stops_before_next_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _task_file(tmp_path, 2, "STEP-002", ("STEP-001",))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: checkpoint failure")

    def failed_commit(*args, **kwargs):
        raise RuntimeError("checkpoint unavailable")

    monkeypatch.setattr("mde.sync.engine.git.commit", failed_commit)
    with pytest.raises(RuntimeError, match="checkpoint unavailable"):
        _run_batch(tmp_path, monkeypatch)
    assert TaskStore(tmp_path).find("STEP-002")[0] == "pending"
    assert (tmp_path / "step-history.txt").read_text(encoding="utf-8") == "STEP-001\n"
    assert _git(tmp_path, "rev-list", "--count", "HEAD") == "1"


def test_g2_rejects_changed_definition_on_existing_batch_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: initial task")
    _run_batch(tmp_path, monkeypatch)
    path = next((tmp_path / "tasks/pending").glob("*.yaml"))
    path.write_text(
        path.read_text(encoding="utf-8").replace("title: STEP-001", "title: changed"),
        encoding="utf-8",
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: changed task")
    with pytest.raises(SyncError, match="definition differs"):
        _run_batch(tmp_path, monkeypatch)
    assert _git(tmp_path, "show", "feature/g2-batch:step-history.txt") == "STEP-001"


@pytest.mark.parametrize("failure", ["missing_state", "missing_commit"])
def test_g2_requires_persisted_completion_and_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    _prepare_repo(tmp_path)
    _task_file(tmp_path, 1, "STEP-001")
    _task_file(tmp_path, 2, "STEP-002", ("STEP-001",))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: completion checkpoint")
    if failure == "missing_state":
        from types import SimpleNamespace

        monkeypatch.setitem(
            _run_batch.__globals__,
            "_run_as_completed",
            lambda *args, **kwargs: SimpleNamespace(status="completed"),
        )
        message = "completed state was not persisted"
    else:
        monkeypatch.setattr("mde.sync.engine.git.changed_files", lambda root: ())
        message = "no checkpoint commit"
    with pytest.raises(SyncError, match=message):
        _run_batch(tmp_path, monkeypatch)
    assert TaskStore(tmp_path).find("STEP-002")[0] == "pending"
    assert _git(tmp_path, "rev-list", "--count", "HEAD") == "1"
