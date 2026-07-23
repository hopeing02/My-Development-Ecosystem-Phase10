"""Safe synchronization of managed sections in MDE documentation."""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path

START_MARKER = "<!-- MDE-DOCS:CLI-REFERENCE:START -->"
END_MARKER = "<!-- MDE-DOCS:CLI-REFERENCE:END -->"
TARGET_PATHS = {
    "mde-user-guide": Path("docs/05_commands/CMD-004-mde-user-guide.md"),
    "knowledge-guide": Path(
        "docs/05_commands/CMD-003-mde-knowledge-plugin-user-guide.md"
    ),
}
TARGET_NAMES = tuple(TARGET_PATHS)


class DocumentationError(RuntimeError):
    """Raised when managed documentation cannot be checked or updated safely."""


def find_documentation_root(start: Path | None = None) -> Path:
    """Find the MDE repository containing the official command documents."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "docs" / "05_commands").is_dir() and (
            candidate / "pyproject.toml"
        ).is_file():
            return candidate
    raise DocumentationError(
        "MDE documentation root not found. Run this command inside the MDE repository."
    )


def target_path(repository_root: Path, target: str) -> Path:
    """Resolve an allowed documentation target within the repository."""

    relative = TARGET_PATHS.get(target)
    if relative is None:
        raise DocumentationError(f"Unsupported documentation target: {target}")
    return repository_root.resolve() / relative


def render_cli_reference(
    parser: argparse.ArgumentParser,
    implemented_commands: set[str] | frozenset[str],
) -> str:
    """Render the canonical CLI reference from the live argument parser."""

    subcommands = _subparsers(parser)
    if subcommands is None:
        raise DocumentationError("MDE CLI has no registered commands.")

    help_by_name = {choice.dest: choice.help for choice in subcommands._choices_actions}
    lines = [
        "## 자동 관리 CLI 참조",
        "",
        "이 구간은 실제 MDE CLI 정의에서 생성된다. 직접 수정하지 않는다.",
        "",
        "| 명령 | 상태 | 설명 |",
        "|---|---|---|",
    ]
    for name in subcommands.choices:
        status = "implemented" if name in implemented_commands else "reserved"
        summary = str(help_by_name.get(name, "-")).replace("|", "\\|")
        lines.append(f"| `mde {name}` | {status} | {summary} |")

    for name, command_parser in subcommands.choices.items():
        if name not in implemented_commands:
            continue
        lines.extend(["", f"### `mde {name}`", ""])
        for usage in _leaf_usages(command_parser):
            lines.append(f"- `{usage}`")
    return "\n".join(lines)


def render_target_reference(
    parser: argparse.ArgumentParser,
    implemented_commands: set[str] | frozenset[str],
    target: str,
) -> str:
    """Render the managed reference for one supported document target."""

    if target == "mde-user-guide":
        return render_cli_reference(parser, implemented_commands)
    if target == "knowledge-guide":
        subcommands = _subparsers(parser)
        knowledge_parser = (
            subcommands.choices.get("knowledge") if subcommands is not None else None
        )
        if knowledge_parser is None:
            raise DocumentationError("Knowledge CLI is not registered.")
        lines = [
            "## 자동 관리 Knowledge CLI 참조",
            "",
            "이 구간은 실제 Knowledge CLI 정의에서 생성된다. 직접 수정하지 않는다.",
            "",
        ]
        lines.extend(f"- `{usage}`" for usage in _leaf_usages(knowledge_parser))
        return "\n".join(lines)
    raise DocumentationError(f"Unsupported documentation target: {target}")


def expected_document(current: str, managed_reference: str) -> str:
    """Replace exactly one managed region while preserving all other text."""

    if current.count(START_MARKER) != 1 or current.count(END_MARKER) != 1:
        raise DocumentationError(
            "Documentation target must contain exactly one managed marker pair."
        )
    if current.index(START_MARKER) >= current.index(END_MARKER):
        raise DocumentationError(
            "Documentation managed markers are in an invalid order."
        )
    prefix, _, after_start = current.partition(START_MARKER)
    _, _, suffix = after_start.partition(END_MARKER)
    managed = f"{START_MARKER}\n{managed_reference}\n{END_MARKER}"
    return f"{prefix}{managed}{suffix}"


def check_document(
    path: Path,
    parser: argparse.ArgumentParser,
    implemented_commands: set[str] | frozenset[str],
    target: str = "mde-user-guide",
) -> bool:
    """Return whether the managed section matches the live CLI."""

    current = _read_target(path)
    expected = expected_document(
        current, render_target_reference(parser, implemented_commands, target)
    )
    return current == expected


def preview_update(
    path: Path,
    parser: argparse.ArgumentParser,
    implemented_commands: set[str] | frozenset[str],
    target: str = "mde-user-guide",
) -> tuple[str, str]:
    """Return the expected document and a unified diff without writing."""

    current = _read_target(path)
    expected = expected_document(
        current, render_target_reference(parser, implemented_commands, target)
    )
    relative_label = path.as_posix()
    diff = "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=relative_label,
            tofile=relative_label,
        )
    )
    return expected, diff


def apply_update(path: Path, expected: str) -> None:
    """Write one previously rendered target without touching other files."""

    path.write_text(expected, encoding="utf-8", newline="\n")


def _read_target(path: Path) -> str:
    if not path.is_file():
        raise DocumentationError(f"Documentation target not found: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise DocumentationError(
            f"Unable to read documentation target: {path}"
        ) from error


def _subparsers(
    parser: argparse.ArgumentParser,
) -> argparse._SubParsersAction[argparse.ArgumentParser] | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _leaf_usages(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    subcommands = _subparsers(parser)
    if subcommands is None or not subcommands.choices:
        usage = " ".join(parser.format_usage().removeprefix("usage:").split())
        return (usage,)
    return tuple(
        usage for child in subcommands.choices.values() for usage in _leaf_usages(child)
    )
