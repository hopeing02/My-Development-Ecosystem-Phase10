import argparse
from io import BytesIO, TextIOWrapper
from pathlib import Path
import sys

import pytest

from mde.cli import main
from mde.knowledge.cli import run
from mde.knowledge.models import SearchResult


def test_knowledge_cli_add_scan_search_show_and_remove(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    data_home = tmp_path / "user-data"
    source = tmp_path / "개인 자료"
    source.mkdir()
    original = source / "vault.md"
    original.write_text("# 가족 일정\n#가족 화요일", encoding="utf-8")
    monkeypatch.setenv("MDE_DATA_HOME", str(data_home))

    assert (
        main(
            [
                "knowledge",
                "add",
                str(source),
                "--name",
                "personal",
                "--category",
                "personal",
                "--type",
                "obsidian",
            ]
        )
        == 0
    )
    assert main(["knowledge", "list"]) == 0
    assert "personal\tpersonal\tobsidian\tyes\tno" in capsys.readouterr().out
    assert main(["knowledge", "scan", "personal"]) == 0
    assert "Added: 1" in capsys.readouterr().out
    assert main(["knowledge", "search", "화요일", "--source", "personal"]) == 0
    assert "[personal | personal | SENSITIVE] 가족 일정" in capsys.readouterr().out
    assert main(["knowledge", "show", "personal"]) == 0
    assert "Documents: 1" in capsys.readouterr().out
    assert main(["knowledge", "remove", "personal"]) == 0
    assert "Original files preserved." in capsys.readouterr().out
    assert original.exists()


def test_knowledge_cli_requires_sensitive_agent_confirmation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source = tmp_path / "work"
    source.mkdir()
    monkeypatch.setenv("MDE_DATA_HOME", str(tmp_path / "data"))
    assert (
        main(["knowledge", "add", str(source), "--name", "work", "--category", "work"])
        == 0
    )
    capsys.readouterr()

    assert main(["knowledge", "update", "work", "--agent-access", "true"]) == 1
    assert "confirm-sensitive-access" in capsys.readouterr().out
    assert (
        main(
            [
                "knowledge",
                "update",
                "work",
                "--agent-access",
                "true",
                "--confirm-sensitive-access",
            ]
        )
        == 0
    )


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [("cp949", "업무?정리"), ("utf-8", "업무—정리")],
)
def test_knowledge_cli_handles_console_encoding(
    monkeypatch, encoding: str, expected: str
) -> None:
    class SearchService:
        def search(self, *args, **kwargs) -> tuple[SearchResult, ...]:
            return (
                SearchResult(
                    source_id="ks-001",
                    source_name="docs",
                    category="development",
                    sensitive=False,
                    document_id="ks-001::guide.md",
                    title="업무—정리",
                    relative_path="guide.md",
                    snippet="업무—정리 절차",
                ),
            )

    output = BytesIO()
    console = TextIOWrapper(output, encoding=encoding, errors="strict")
    args = argparse.Namespace(
        knowledge_action="search",
        query="업무",
        source="docs",
        category=None,
        all_sources=False,
        include_sensitive=False,
        tag=None,
        limit=20,
    )

    monkeypatch.setattr(sys, "stdout", console)
    assert run(args, service=SearchService()) == 0
    console.flush()

    rendered = output.getvalue().decode(encoding)
    assert expected in rendered
    assert console.errors == "replace"
