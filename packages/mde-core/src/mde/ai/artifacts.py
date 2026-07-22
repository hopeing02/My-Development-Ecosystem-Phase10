from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from mde.ai.models import AIResponse


class ArtifactError(RuntimeError):
    """Raised when an AI artifact bundle is unsafe or malformed."""


def validate_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ArtifactError(f"Unsafe artifact path: {value}")
    if path.parts[0] in {".git", ".venv"}:
        raise ArtifactError(f"Protected artifact path: {value}")
    return path


def write_response_bundle(
    response: AIResponse,
    repository_root: Path,
    *,
    run_id: str,
    step_id: str,
) -> Path:
    bundle_dir = repository_root / ".mde" / "artifacts" / run_id / step_id
    files_dir = bundle_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    manifest_artifacts: list[dict[str, Any]] = []
    for artifact in response.artifacts:
        relative = validate_relative_path(artifact.path)
        stored_path = files_dir.joinpath(*relative.parts)
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        stored_path.write_text(artifact.content, encoding="utf-8")
        manifest_artifacts.append(
            {
                "target_path": relative.as_posix(),
                "source_path": stored_path.relative_to(repository_root).as_posix(),
                "media_type": artifact.media_type,
            }
        )

    manifest = {
        "version": 1,
        "provider": response.provider,
        "action": response.action,
        "summary": response.summary,
        "metadata": dict(response.metadata),
        "artifacts": manifest_artifacts,
    }
    manifest_path = bundle_dir / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    return manifest_path


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ArtifactError(f"AI artifact manifest not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(
        loaded.get("artifacts", []), list
    ):
        raise ArtifactError(f"Invalid AI artifact manifest: {path}")
    return loaded
