from pathlib import Path

from mde.knowledge.service import KnowledgeService


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_scan_search_tags_backlinks_and_source_boundaries(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    development = tmp_path / "mde-docs"
    personal = tmp_path / "personal-vault"
    work = tmp_path / "work-vault"
    project = tmp_path / "project-alpha"
    _write(
        development / "ARCH" / "ARCH-001-overview.md",
        "# MDE Workflow Engine\n#architecture\nSee [[DEV-001-standard]].",
    )
    _write(
        development / "DEV" / "DEV-001-standard.md",
        "# Development Standard\nThe workflow standard.",
    )
    _write(personal / "vault.md", "# Personal Vault\n[[가족 일정]]")
    _write(personal / "가족" / "학원일정.md", "# 가족 일정\n화요일 수학 학원 일정")
    _write(work / "업무절차" / "지출결의.md", "# 지출 결의 절차\n비밀 workflow")
    _write(project / "docs" / "README.md", "# Project Alpha\nproject workflow")

    knowledge_service.add_source(development, name="mde-docs", category="development")
    knowledge_service.add_source(
        personal, name="personal", category="personal", source_type="obsidian"
    )
    knowledge_service.add_source(work, name="work", category="work")
    knowledge_service.add_source(
        project / "docs", name="project-alpha", category="project"
    )

    general_scans = knowledge_service.scan_selected(all_sources=True)
    assert {result.source.name for result in general_scans} == {
        "mde-docs",
        "project-alpha",
    }
    knowledge_service.scan_source("personal")
    knowledge_service.scan_source("work")

    default_results = knowledge_service.search("workflow")
    assert {result.source_name for result in default_results} == {
        "mde-docs",
        "project-alpha",
    }
    assert [
        result.title for result in knowledge_service.search("학원", source="personal")
    ] == ["가족 일정"]
    assert [
        result.title for result in knowledge_service.search("지출", source="work")
    ] == ["지출 결의 절차"]
    assert [
        result.title
        for result in knowledge_service.search(tag="architecture", source="mde-docs")
    ] == ["MDE Workflow Engine"]
    backlinks = knowledge_service.backlinks("가족 일정", source="personal")
    assert [result.relative_path for result in backlinks] == ["vault.md"]

    sensitive_results = knowledge_service.search(
        "workflow", all_sources=True, include_sensitive=True
    )
    assert {result.source_name for result in sensitive_results} == {
        "mde-docs",
        "project-alpha",
        "work",
    }


def test_incremental_scan_updates_and_deletes_only_selected_source(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_file = _write(first_root / "same.md", "# First\noriginal")
    _write(second_root / "same.md", "# Second\nkeep")
    first = knowledge_service.add_source(first_root, name="first", category="project")
    second = knowledge_service.add_source(
        second_root, name="second", category="project"
    )
    assert knowledge_service.scan_source(first.id).added_count == 1
    assert knowledge_service.scan_source(second.id).added_count == 1
    assert knowledge_service.scan_source(first.id).unchanged_count == 1

    first_file.write_text("# First\nupdated", encoding="utf-8")
    assert knowledge_service.scan_source(first.id).updated_count == 1
    first_file.unlink()
    assert knowledge_service.scan_source(first.id).deleted_count == 1

    assert knowledge_service.search("keep", source=second.id)[0].source_id == second.id
    assert knowledge_service.show_source(first.id)[1] == 0
    assert knowledge_service.show_source(second.id)[1] == 1


def test_scan_continues_after_bad_file_and_does_not_log_content(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    root = tmp_path / "mixed"
    _write(root / "good.md", "# Good\nsearchable")
    bad = root / "비밀.md"
    bad.write_bytes(b"\xff\xfeprivate body")
    knowledge_service.add_source(root, name="mixed", category="development")

    result = knowledge_service.scan_source("mixed")

    assert result.added_count == 1
    assert result.error_count == 1
    assert result.errors[0].relative_path == "비밀.md"
    assert "private body" not in result.errors[0].message


def test_remove_preserves_original_and_other_source_index(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    personal_root = tmp_path / "personal"
    work_root = tmp_path / "work"
    original = _write(personal_root / "vault.md", "# Personal\nprivate")
    _write(work_root / "vault.md", "# Work\nbusiness")
    knowledge_service.add_source(personal_root, name="personal", category="personal")
    knowledge_service.add_source(work_root, name="work", category="work")
    knowledge_service.scan_source("personal")
    knowledge_service.scan_source("work")

    knowledge_service.remove_source("personal")

    assert original.read_text(encoding="utf-8") == "# Personal\nprivate"
    assert personal_root.is_dir()
    assert knowledge_service.search("business", source="work")[0].source_name == "work"


def test_agent_search_never_returns_sensitive_or_disallowed_sources(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    development = tmp_path / "development"
    personal = tmp_path / "personal"
    project = tmp_path / "project"
    _write(development / "a.md", "# Dev\nneedle")
    _write(personal / "a.md", "# Personal\nneedle")
    _write(project / "a.md", "# Project\nneedle")
    dev_source = knowledge_service.add_source(
        development, name="dev", category="development"
    )
    personal_source = knowledge_service.add_source(
        personal, name="personal", category="personal"
    )
    project_source = knowledge_service.add_source(
        project, name="project", category="project"
    )
    for source in (dev_source, personal_source, project_source):
        knowledge_service.scan_source(source.id)
    knowledge_service.update_source(project_source.id, allow_agent_access=False)

    assert [
        result.source_name for result in knowledge_service.search_for_agent("needle")
    ] == ["dev"]
    assert knowledge_service.search_for_agent("needle", [personal_source.id]) == ()


def test_like_search_fallback(tmp_path: Path) -> None:
    service = KnowledgeService(
        tmp_path / "sources.json",
        tmp_path / "knowledge.db",
        force_like_search=True,
    )
    root = tmp_path / "docs"
    _write(root / "readme.md", "# Fallback\nLIKE searchable")
    service.add_source(root, name="docs", category="development")
    service.scan_source("docs")
    assert service.repository.fts_enabled is False
    assert service.search("searchable")[0].title == "Fallback"
