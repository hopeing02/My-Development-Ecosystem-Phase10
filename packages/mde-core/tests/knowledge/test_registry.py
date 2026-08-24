from pathlib import Path

import pytest

from mde.knowledge.errors import SourceNotFoundError, SourceValidationError
from mde.knowledge.models import category_defaults
from mde.knowledge.registry import SourceRegistry


@pytest.mark.parametrize(
    ("category", "sensitive", "agent_access"),
    [
        ("development", False, True),
        ("project", False, True),
        ("shared", False, True),
        ("personal", True, False),
        ("work", True, False),
    ],
)
def test_category_security_defaults(
    category: str, sensitive: bool, agent_access: bool
) -> None:
    assert category_defaults(category) == (sensitive, agent_access)


def test_registry_adds_unicode_space_path_and_normalizes_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path = tmp_path / "한글 자료"
    source_path.mkdir()
    monkeypatch.chdir(tmp_path)
    registry = SourceRegistry(tmp_path / "state" / "sources.json")

    source = registry.add(
        Path("한글 자료"), name="개인 자료", category="personal", source_type="obsidian"
    )

    assert source.id == "ks-001"
    assert source.path == source_path.resolve()
    assert source.sensitive is True
    assert source.allow_agent_access is False
    assert registry.get("개인 자료") == source


def test_registry_rejects_duplicate_name_and_normalized_path(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    registry = SourceRegistry(tmp_path / "sources.json")
    registry.add(first, name="docs", category="development")

    with pytest.raises(SourceValidationError, match="name already exists"):
        registry.add(second, name="DOCS", category="project")
    with pytest.raises(SourceValidationError, match="path already exists"):
        registry.add(first / ".", name="other", category="project")


@pytest.mark.parametrize(
    ("path_kind", "message"),
    [("missing", "does not exist"), ("file", "not a directory")],
)
def test_registry_rejects_invalid_source_paths(
    tmp_path: Path, path_kind: str, message: str
) -> None:
    path = tmp_path / path_kind
    if path_kind == "file":
        path.write_text("not a directory", encoding="utf-8")
    registry = SourceRegistry(tmp_path / "sources.json")
    with pytest.raises(SourceValidationError, match=message):
        registry.add(path, name="invalid", category="development")


def test_sensitive_agent_access_requires_explicit_confirmation(tmp_path: Path) -> None:
    source_path = tmp_path / "personal"
    source_path.mkdir()
    registry = SourceRegistry(tmp_path / "sources.json")
    registry.add(source_path, name="personal", category="personal")

    with pytest.raises(SourceValidationError, match="confirm-sensitive-access"):
        registry.update("personal", allow_agent_access=True)

    updated = registry.update(
        "personal", allow_agent_access=True, confirm_sensitive_access=True
    )
    assert updated.allow_agent_access is True


def test_registry_remove_never_changes_source_files(tmp_path: Path) -> None:
    source_path = tmp_path / "vault"
    source_path.mkdir()
    original = source_path / "vault.md"
    original.write_text("# Original", encoding="utf-8")
    registry = SourceRegistry(tmp_path / "sources.json")
    registry.add(source_path, name="vault", category="personal")

    removed = registry.remove("vault")

    assert removed.name == "vault"
    assert original.read_text(encoding="utf-8") == "# Original"
    with pytest.raises(SourceNotFoundError):
        registry.get("vault")


def test_registry_persists_shared_link_target_policy(tmp_path: Path) -> None:
    source_path = tmp_path / "mde-docs"
    source_path.mkdir()
    registry = SourceRegistry(tmp_path / "sources.json")
    registry.add(source_path, name="mde-docs", category="development")

    updated = registry.update("mde-docs", allow_as_shared_link_target=True)

    assert updated.allow_as_shared_link_target is True
    assert registry.get("mde-docs").allow_as_shared_link_target is True
