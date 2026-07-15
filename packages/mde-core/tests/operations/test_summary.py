from pathlib import Path
import json

from mde.task.summary import write_mobile_summary


def test_mobile_summary_is_written(tmp_path: Path) -> None:
    path = write_mobile_summary(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["counts"] == {
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
    }
