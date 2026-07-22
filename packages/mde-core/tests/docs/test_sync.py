from pathlib import Path

import pytest

from mde.cli import IMPLEMENTED_COMMANDS, build_parser, main
from mde.documentation import (
    END_MARKER,
    START_MARKER,
    expected_document,
    render_cli_reference,
)


def _make_repository(root: Path, managed: str = "outdated") -> Path:
    (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    commands = root / "docs" / "05_commands"
    commands.mkdir(parents=True)
    guide = commands / "CMD-004-mde-user-guide.md"
    guide.write_text(
        f"# Before\n\n{START_MARKER}\n{managed}\n{END_MARKER}\n\n# After\n",
        encoding="utf-8",
    )
    return guide


def test_cli_reference_reports_implemented_and_reserved_commands() -> None:
    reference = render_cli_reference(build_parser(), IMPLEMENTED_COMMANDS)

    assert "| `mde docs` | implemented |" in reference
    assert "| `mde knowledge` | implemented |" in reference
    assert "| `mde generate` | reserved |" in reference
    assert "mde docs update [-h] [--target {mde-user-guide}] [--apply]" in reference


def test_expected_document_preserves_text_outside_managed_region() -> None:
    current = f"before\n{START_MARKER}\nold\n{END_MARKER}\nafter\n"

    updated = expected_document(current, "new")

    assert updated == f"before\n{START_MARKER}\nnew\n{END_MARKER}\nafter\n"


def test_expected_document_rejects_reversed_markers() -> None:
    current = f"before\n{END_MARKER}\nold\n{START_MARKER}\nafter\n"

    with pytest.raises(RuntimeError, match="invalid order"):
        expected_document(current, "new")


def test_docs_cli_previews_applies_and_checks_update(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    guide = _make_repository(tmp_path)
    original = guide.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["docs", "check"]) == 1
    assert "out of date" in capsys.readouterr().out

    assert main(["docs", "update"]) == 0
    preview = capsys.readouterr().out
    assert "Preview only" in preview
    assert guide.read_text(encoding="utf-8") == original

    assert main(["docs", "update", "--apply"]) == 0
    assert (
        "Only the managed CLI reference section was changed" in capsys.readouterr().out
    )
    updated = guide.read_text(encoding="utf-8")
    assert updated.startswith("# Before")
    assert updated.endswith("# After\n")
    assert "| `mde docs` | implemented |" in updated

    assert main(["docs", "check"]) == 0
    assert "up to date" in capsys.readouterr().out


def test_docs_cli_rejects_missing_managed_markers(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    guide = _make_repository(tmp_path)
    guide.write_text("# Unmanaged guide\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["docs", "update", "--apply"]) == 1
    assert "exactly one managed marker pair" in capsys.readouterr().out
