from pathlib import Path

from mde.task.checkpoint import CheckpointStore, TaskCheckpoint


def test_checkpoint_round_trip(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path)
    store.write(
        TaskCheckpoint("TASK-1", "feature", "processing", ("prepare",), "prepare")
    )
    loaded = store.load("TASK-1")
    assert loaded is not None
    assert loaded.completed_steps == ("prepare",)
    assert loaded.last_successful_step == "prepare"


def test_checkpoint_clear(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path)
    store.write(TaskCheckpoint("TASK-1", "feature", "completed"))
    store.clear("TASK-1")
    assert store.load("TASK-1") is None
