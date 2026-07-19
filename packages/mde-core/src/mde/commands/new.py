from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")

PROJECT_ROOT = Path.cwd()

TEMPLATE_DIR = PROJECT_ROOT / "templates" / "shared"


class NewProjectError(RuntimeError):
    """Raised when a project cannot be created safely."""


@dataclass(frozen=True)
class ProjectContext:
    project_name: str
    project_title: str
    created_date: str


@dataclass(frozen=True)
class TemplateSpec:
    template_path: Path
    output_path: Path


def validate_project_name(project_name: str) -> None:
    if not PROJECT_NAME_PATTERN.match(project_name):
        raise NewProjectError(
            "Project name must use lowercase letters, numbers, and hyphens only."
        )


def to_project_title(project_name: str) -> str:
    return " ".join(word.capitalize() for word in project_name.split("-"))


def build_context(project_name: str) -> ProjectContext:
    return ProjectContext(
        project_name=project_name,
        project_title=to_project_title(project_name),
        created_date=date.today().isoformat(),
    )


def load_template(path: Path) -> str:
    print(f"Looking for template: {path}")
    print(f"Exists: {path.exists()}")
    if not path.is_file():
        raise NewProjectError(f"Template file not found: {path}")

    return path.read_text(encoding="utf-8")


def render_template(template: str, context: ProjectContext) -> str:
    return (
        template.replace("{{PROJECT_NAME}}", context.project_name)
        .replace("{{PROJECT_TITLE}}", context.project_title)
        .replace("{{CREATED_DATE}}", context.created_date)
    )


def write_text_file(path: Path, content: str) -> None:
    if path.exists():
        raise NewProjectError(f"File already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_template_specs(
    root: Path,
    project_name: str,
    template_dir: Path | None = None,
) -> list[TemplateSpec]:
    resolved_template_dir = template_dir or TEMPLATE_DIR
    app_dir = root / "apps" / project_name
    project_docs_dir = root / "docs" / "15_projects" / project_name

    return [
        TemplateSpec(
            template_path=resolved_template_dir / "README.md.tpl",
            output_path=app_dir / "README.md",
        ),
        TemplateSpec(
            template_path=resolved_template_dir / "SDS-001-overview.md.tpl",
            output_path=project_docs_dir / "SDS" / "SDS-001-overview.md",
        ),
        TemplateSpec(
            template_path=resolved_template_dir / "project.yaml.tpl",
            output_path=app_dir / ".mde" / "project.yaml",
        ),
        TemplateSpec(
            template_path=resolved_template_dir / "mde-ci.yml.tpl",
            output_path=app_dir / ".github" / "workflows" / "mde-ci.yml",
        ),
        TemplateSpec(
            template_path=resolved_template_dir / "MDE-COLLABORATION.md.tpl",
            output_path=app_dir / ".github" / "MDE-COLLABORATION.md",
        ),
    ]


def ensure_project_paths_available(root: Path, project_name: str) -> None:
    app_dir = root / "apps" / project_name
    project_docs_dir = root / "docs" / "15_projects" / project_name

    if app_dir.exists():
        raise NewProjectError(f"Path already exists: {app_dir}")

    if project_docs_dir.exists():
        raise NewProjectError(f"Path already exists: {project_docs_dir}")


def create_project(project_name: str, root_dir: Path | None = None) -> list[Path]:
    validate_project_name(project_name)

    root = root_dir or Path.cwd()
    context = build_context(project_name)

    ensure_project_paths_available(root, project_name)

    created_paths: list[Path] = []

    app_dir = root / "apps" / project_name
    docs_dir = root / "docs" / "15_projects" / project_name

    app_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    created_paths.append(app_dir)
    created_paths.append(docs_dir)

    for spec in build_template_specs(
        root, project_name, template_dir=root / "templates" / "shared"
    ):
        template = load_template(spec.template_path)
        content = render_template(template, context)
        write_text_file(spec.output_path, content)
        created_paths.append(spec.output_path)

    return created_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a new MDE project.")
    parser.add_argument("project_name", help="Project name.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        created_paths = create_project(args.project_name)
    except NewProjectError as error:
        print(error)
        return 1

    for path in created_paths:
        print(f"Created: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
