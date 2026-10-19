from pathlib import Path

import pytest

from mde.ai.artifacts import ArtifactError, validate_relative_path
from mde.ai.engine import AIEngine, create_default_provider_registry


def test_default_provider_registry_contains_mock() -> None:
    assert create_default_provider_registry().names() == (
        "claude",
        "gemini",
        "local",
        "mock",
        "openai",
    )


def test_ai_engine_writes_artifact_bundle(tmp_path: Path) -> None:
    response, manifest = AIEngine().execute(
        action="generate",
        prompt="create a file",
        repository_root=tmp_path,
        run_id="TASK-1",
        step_id="generate",
        context={"artifacts": [{"path": "src/example.txt", "content": "hello"}]},
    )
    assert response.provider == "mock"
    assert manifest.is_file()
    assert (
        tmp_path / ".mde/artifacts/TASK-1/generate/files/src/example.txt"
    ).read_text() == "hello"


def test_artifact_path_rejects_parent_traversal() -> None:
    with pytest.raises(ArtifactError):
        validate_relative_path("../secret.txt")
