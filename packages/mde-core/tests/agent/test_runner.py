from pathlib import Path
from types import SimpleNamespace

import pytest

from mde.agent import runner


def test_run_once_uses_mobile_sync_and_writes_heartbeat(tmp_path: Path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        runner,
        "run_mobile_sync",
        lambda root, policy: SimpleNamespace(
            remote_changed=True,
            pulled=True,
            recovered_count=1,
            completed_tasks=("TASK-1",),
            failed_tasks=(),
            commit_hash="abc123",
            pushed=True,
        ),
    )

    result = runner.run_once(repository_root=tmp_path)

    assert result.completed_tasks == ("TASK-1",)
    assert result.commit_hash == "abc123"
    assert result.pushed is True
    assert result.heartbeat_path.is_file()
    text = result.heartbeat_path.read_text(encoding="utf-8")
    assert '"status": "completed"' in text
    assert '"TASK-1"' in text
    assert not (tmp_path / ".mde" / "agent.lock").exists()


def test_run_once_writes_failed_heartbeat(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        runner,
        "run_mobile_sync",
        lambda root, policy: (_ for _ in ()).throw(RuntimeError("sync boom")),
    )

    with pytest.raises(runner.AgentError, match="sync boom"):
        runner.run_once(repository_root=tmp_path)

    heartbeat = tmp_path / "status" / "agent-heartbeat.json"
    assert heartbeat.is_file()
    text = heartbeat.read_text(encoding="utf-8")
    assert '"status": "failed"' in text
    assert "sync boom" in text
    assert not (tmp_path / ".mde" / "agent.lock").exists()


def test_watch_rejects_short_interval():
    with pytest.raises(runner.AgentError, match="at least 5"):
        runner.run_watch(interval_seconds=1, max_cycles=1)
