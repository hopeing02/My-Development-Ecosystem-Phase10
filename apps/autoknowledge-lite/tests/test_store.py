from pathlib import Path

import pytest

from autoknowledge_lite import store
from autoknowledge_lite.store import JsonShareStore


def test_default_store_uses_project_data_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOKNOWLEDGE_DATA_DIR", raising=False)

    share_store = JsonShareStore()

    expected = Path(store.__file__).resolve().parents[2] / "data"
    assert share_store.root == expected.resolve()


def test_environment_store_path_overrides_project_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = tmp_path / "configured"
    monkeypatch.setenv("AUTOKNOWLEDGE_DATA_DIR", str(configured))

    share_store = JsonShareStore()

    assert share_store.root == configured.resolve()
