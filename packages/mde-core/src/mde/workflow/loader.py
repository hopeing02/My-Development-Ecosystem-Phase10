from __future__ import annotations

from pathlib import Path

import yaml

from mde.exceptions import MDEError
from mde.workflow.models import WorkflowDefinition
from mde.workflow.validator import validate_workflow_document


class WorkflowNotFoundError(MDEError, FileNotFoundError):
    """Raised when a named workflow cannot be located."""


def package_workflow_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "workflows"


def workflow_search_dirs(repository_root: Path | None = None) -> tuple[Path, ...]:
    root = (repository_root or Path.cwd()).resolve()
    candidates = (root / "workflows", package_workflow_dir())
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def find_workflow_path(name: str, repository_root: Path | None = None) -> Path:
    filename = f"{name}.yaml"
    for directory in workflow_search_dirs(repository_root):
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(path) for path in workflow_search_dirs(repository_root))
    raise WorkflowNotFoundError(
        f"Workflow '{name}' was not found. Searched: {searched}"
    )


def load_workflow(path: Path) -> WorkflowDefinition:
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except yaml.YAMLError as error:
        raise MDEError(f"Invalid YAML in workflow '{path}': {error}") from error

    definition = validate_workflow_document(document)
    return WorkflowDefinition(
        version=definition.version,
        name=definition.name,
        description=definition.description,
        steps=definition.steps,
        source_path=path.resolve(),
    )


def load_named_workflow(
    name: str, repository_root: Path | None = None
) -> WorkflowDefinition:
    return load_workflow(find_workflow_path(name, repository_root))


def list_workflows(repository_root: Path | None = None) -> list[WorkflowDefinition]:
    paths: dict[str, Path] = {}
    for directory in reversed(workflow_search_dirs(repository_root)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            paths[path.stem] = path
    return [load_workflow(paths[name]) for name in sorted(paths)]
