from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from mde.exceptions import MDEError

PROJECT_CONFIG_PATH = Path(".mde") / "project.yaml"
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BRANCH_PLACEHOLDERS = frozenset({"{type}", "{assignee}", "{task_id}"})


class ProjectConfigError(MDEError, ValueError):
    """Raised when an MDE project configuration is missing or invalid."""


@dataclass(frozen=True)
class ProjectCommands:
    test: tuple[str, ...]
    build: tuple[str, ...]


@dataclass(frozen=True)
class RepositoryPolicy:
    default_branch: str
    branch_pattern: str
    protected_branches: tuple[str, ...]


@dataclass(frozen=True)
class PullRequestPolicy:
    required: bool
    approvals_required: int
    require_tests: bool


@dataclass(frozen=True)
class ProjectConfig:
    version: int
    project_id: str
    name: str
    repository: RepositoryPolicy
    commands: ProjectCommands
    pull_request: PullRequestPolicy
    source_path: Path | None = None


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectConfigError(f"Project field '{field}' must be a mapping.")
    return value


def _require_text(mapping: dict[str, Any], key: str, field: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectConfigError(
            f"Project field '{field}.{key}' must be a non-empty string."
        )
    return value.strip()


def _validate_identifier(value: str, field: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ProjectConfigError(
            f"Project field '{field}' must contain only letters, numbers, '.', '_', or '-'."
        )
    return value


def _text_list(mapping: dict[str, Any], key: str, field: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ProjectConfigError(f"Project field '{field}.{key}' must be a list.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ProjectConfigError(
            f"Project field '{field}.{key}' must contain only non-empty strings."
        )
    return tuple(item.strip() for item in value)


def validate_project_document(document: Any) -> ProjectConfig:
    root = _require_mapping(document, "document")
    version = root.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        raise ProjectConfigError("Project field 'version' must be integer 1.")

    project = _require_mapping(root.get("project"), "project")
    repository = _require_mapping(root.get("repository"), "repository")
    commands = _require_mapping(root.get("commands"), "commands")
    pull_request_value = root.get("pull_request", {})
    pull_request = _require_mapping(pull_request_value, "pull_request")

    project_id = _validate_identifier(
        _require_text(project, "id", "project"), "project.id"
    )
    name = _require_text(project, "name", "project")
    default_branch = _validate_identifier(
        _require_text(repository, "default_branch", "repository"),
        "repository.default_branch",
    )
    branch_pattern = _require_text(repository, "branch_pattern", "repository")
    missing_placeholders = sorted(
        placeholder
        for placeholder in _BRANCH_PLACEHOLDERS
        if placeholder not in branch_pattern
    )
    if missing_placeholders:
        missing = ", ".join(missing_placeholders)
        raise ProjectConfigError(
            f"Project field 'repository.branch_pattern' is missing: {missing}."
        )

    protected_value = repository.get("protected_branches", [default_branch])
    repository_with_default = {**repository, "protected_branches": protected_value}
    protected_branches = _text_list(
        repository_with_default, "protected_branches", "repository"
    )
    for branch in protected_branches:
        _validate_identifier(branch, "repository.protected_branches")
    if default_branch not in protected_branches:
        raise ProjectConfigError(
            "Project field 'repository.protected_branches' must include the default branch."
        )

    approvals_required = pull_request.get("approvals_required", 1)
    if (
        not isinstance(approvals_required, int)
        or isinstance(approvals_required, bool)
        or approvals_required < 0
    ):
        raise ProjectConfigError(
            "Project field 'pull_request.approvals_required' must be a non-negative integer."
        )

    return ProjectConfig(
        version=version,
        project_id=project_id,
        name=name,
        repository=RepositoryPolicy(
            default_branch=default_branch,
            branch_pattern=branch_pattern,
            protected_branches=protected_branches,
        ),
        commands=ProjectCommands(
            test=_text_list(commands, "test", "commands"),
            build=_text_list(commands, "build", "commands"),
        ),
        pull_request=PullRequestPolicy(
            required=bool(pull_request.get("required", True)),
            approvals_required=approvals_required,
            require_tests=bool(pull_request.get("require_tests", True)),
        ),
    )


def load_project_config(repository_root: Path) -> ProjectConfig:
    path = repository_root.resolve() / PROJECT_CONFIG_PATH
    if not path.is_file():
        raise ProjectConfigError(f"Project configuration not found: {path}")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ProjectConfigError(
            f"Unable to read project configuration '{path}': {error}"
        ) from error
    config = validate_project_document(document)
    return ProjectConfig(**{**config.__dict__, "source_path": path})
