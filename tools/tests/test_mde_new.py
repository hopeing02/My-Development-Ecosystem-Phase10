from __future__ import annotations

from pathlib import Path

import pytest

from tools.mde_new import (
    NewProjectError,
    ProjectContext,
    build_context,
    build_template_specs,
    create_project,
    load_template,
    render_template,
    to_project_title,
    validate_project_name,
    TEMPLATE_DIR,
)


def create_test_templates(root: Path) -> None:
    template_dir = root / "templates" / "shared"
    template_dir.mkdir(parents=True)

    (template_dir / "README.md.tpl").write_text(
        "# {{PROJECT_TITLE}}\n\nProject: {{PROJECT_NAME}}\nCreated: {{CREATED_DATE}}\n",
        encoding="utf-8",
    )

    (template_dir / "SDS-001-overview.md.tpl").write_text(
        "# SDS-001 Overview\n\nProject: {{PROJECT_TITLE}}\n",
        encoding="utf-8",
    )


def test_validate_project_name_accepts_valid_name() -> None:
    validate_project_name("autoknowledge-lite")


@pytest.mark.parametrize(
    "project_name",
    [
        "AutoKnowledge",
        "auto_knowledge",
        "-autoknowledge",
        "autoknowledge-",
        "auto knowledge",
        "",
    ],
)
def test_validate_project_name_rejects_invalid_name(project_name: str) -> None:
    with pytest.raises(NewProjectError):
        validate_project_name(project_name)


def test_to_project_title() -> None:
    assert to_project_title("autoknowledge-lite") == "Autoknowledge Lite"


def test_build_context() -> None:
    context = build_context("autoknowledge-lite")

    assert context.project_name == "autoknowledge-lite"
    assert context.project_title == "Autoknowledge Lite"
    assert len(context.created_date) == 10


def test_render_template() -> None:
    context = ProjectContext(
        project_name="autoknowledge-lite",
        project_title="Autoknowledge Lite",
        created_date="2026-07-05",
    )

    result = render_template(
        "{{PROJECT_TITLE}} / {{PROJECT_NAME}} / {{CREATED_DATE}}",
        context,
    )

    assert result == "Autoknowledge Lite / autoknowledge-lite / 2026-07-05"


def test_load_template(tmp_path: Path) -> None:
    template_path = tmp_path / "README.md.tpl"
    template_path.write_text("# {{PROJECT_TITLE}}\n", encoding="utf-8")

    assert load_template(template_path) == "# {{PROJECT_TITLE}}\n"


def test_load_template_fails_when_missing(tmp_path: Path) -> None:
    with pytest.raises(NewProjectError):
        load_template(tmp_path / "missing.tpl")


def test_build_template_specs(tmp_path: Path) -> None:
    specs = build_template_specs(tmp_path, "autoknowledge-lite")

    assert specs[0].template_path == TEMPLATE_DIR / "README.md.tpl"
    assert (
        specs[0].output_path == tmp_path / "apps" / "autoknowledge-lite" / "README.md"
    )

    assert specs[1].template_path == TEMPLATE_DIR / "SDS-001-overview.md.tpl"
    assert (
        specs[1].output_path
        == tmp_path
        / "docs"
        / "15_projects"
        / "autoknowledge-lite"
        / "SDS"
        / "SDS-001-overview.md"
    )


def test_create_project_creates_directories_and_files(tmp_path: Path) -> None:
    create_test_templates(tmp_path)

    created_paths = create_project("autoknowledge-lite", root_dir=tmp_path)

    app_dir = tmp_path / "apps" / "autoknowledge-lite"
    docs_dir = tmp_path / "docs" / "15_projects" / "autoknowledge-lite"
    readme_path = app_dir / "README.md"
    sds_path = docs_dir / "SDS" / "SDS-001-overview.md"

    assert created_paths == [
        app_dir,
        docs_dir,
        readme_path,
        sds_path,
    ]

    assert readme_path.is_file()
    assert sds_path.is_file()

    assert "# Autoknowledge Lite" in readme_path.read_text(encoding="utf-8")
    assert "# SDS-001 Overview" in sds_path.read_text(encoding="utf-8")


def test_create_project_fails_if_app_path_exists(tmp_path: Path) -> None:
    create_test_templates(tmp_path)

    existing_path = tmp_path / "apps" / "autoknowledge-lite"
    existing_path.mkdir(parents=True)

    with pytest.raises(NewProjectError):
        create_project("autoknowledge-lite", root_dir=tmp_path)


def test_create_project_fails_if_docs_path_exists(tmp_path: Path) -> None:
    create_test_templates(tmp_path)

    existing_path = tmp_path / "docs" / "15_projects" / "autoknowledge-lite"
    existing_path.mkdir(parents=True)

    with pytest.raises(NewProjectError):
        create_project("autoknowledge-lite", root_dir=tmp_path)
