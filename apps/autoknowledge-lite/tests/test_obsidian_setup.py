from __future__ import annotations

import json
from pathlib import Path

from autoknowledge_lite.obsidian_setup import (
    REQUIRED_CORE_PLUGINS,
    setup_obsidian,
)


def git_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    return vault


def test_setup_creates_required_plugins_graph_template_and_bases(
    tmp_path: Path,
) -> None:
    vault = git_vault(tmp_path)

    preview = setup_obsidian(vault, apply=False)

    assert len(preview) == 10
    assert not (vault / ".obsidian").exists()

    changed = setup_obsidian(vault, apply=True)

    assert changed == preview
    plugins = json.loads(
        (vault / ".obsidian" / "core-plugins.json").read_text(encoding="utf-8")
    )
    assert "global-search" in plugins
    assert set(REQUIRED_CORE_PLUGINS).issubset(plugins)
    graph = json.loads((vault / ".obsidian" / "graph.json").read_text(encoding="utf-8"))
    assert graph["search"] == '-path:"90_Archive" -tag:#integration-test'
    assert graph["showArrow"] is True
    assert (vault / "Templates" / "Knowledge Note.md").is_file()
    assert len(list((vault / "Bases").glob("*.base"))) == 5
    assert setup_obsidian(vault, apply=False) == ()


def test_setup_merges_plugins_and_preserves_existing_graph(tmp_path: Path) -> None:
    vault = git_vault(tmp_path)
    obsidian = vault / ".obsidian"
    obsidian.mkdir()
    (obsidian / "core-plugins.json").write_text(
        '["file-explorer"]\n',
        encoding="utf-8",
    )
    existing_graph = '{"search":"custom"}\n'
    (obsidian / "graph.json").write_text(existing_graph, encoding="utf-8")

    setup_obsidian(vault, apply=True)

    plugins = json.loads((obsidian / "core-plugins.json").read_text(encoding="utf-8"))
    assert plugins[0] == "file-explorer"
    assert set(REQUIRED_CORE_PLUGINS).issubset(plugins)
    assert (obsidian / "graph.json").read_text(encoding="utf-8") == existing_graph
