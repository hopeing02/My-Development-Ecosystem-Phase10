from pathlib import Path
import sqlite3

import pytest

from mde.knowledge.errors import KnowledgeContractError
from mde.knowledge.service import KnowledgeService


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_graph_resolves_direction_broken_links_orphans_and_cycles(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    root = tmp_path / "vault"
    _write(
        root / "A.md",
        "# A\n[[folder/B]]\n[[Missing]]\n[[Duplicate]]",
    )
    _write(root / "folder" / "B.md", "# B\n[[C]]")
    _write(root / "C.md", "# C\n[[A]]")
    _write(root / "Orphan.md", "# Orphan")
    _write(root / "one.md", "# Duplicate")
    _write(root / "two.md", "# Duplicate")
    source = knowledge_service.add_source(
        root, name="personal", category="personal", source_type="obsidian"
    )
    knowledge_service.scan_source(source.id)

    with pytest.raises(KnowledgeContractError) as sensitive_error:
        knowledge_service.graphs.get_source_graph(source.id)
    assert sensitive_error.value.code == "SENSITIVE_SOURCE_NOT_ALLOWED"

    graph = knowledge_service.graphs.get_source_graph(
        source.id, include_broken=True, confirm_sensitive=True
    )
    ids = {node.title: node.id for node in graph.nodes if node.title != "Duplicate"}
    assert {(edge.source, edge.target) for edge in graph.edges} == {
        (ids["A"], ids["B"]),
        (ids["B"], ids["C"]),
        (ids["C"], ids["A"]),
    }
    broken = {(link.target, link.resolution_status) for link in graph.broken_links}
    assert broken == {("Missing", "unresolved"), ("Duplicate", "ambiguous")}
    orphan = next(node for node in graph.nodes if node.title == "Orphan")
    assert orphan.is_orphan is True
    a_node = next(node for node in graph.nodes if node.title == "A")
    assert (a_node.incoming_count, a_node.outgoing_count) == (1, 1)
    assert a_node.broken_outgoing_count == 2
    assert graph.total_document_count == 6
    assert graph.returned_document_count == 6
    assert graph.truncated is False

    depth_one = knowledge_service.graphs.get_document_graph(
        source.id,
        ids["A"],
        depth=1,
        direction="outgoing",
        confirm_sensitive=True,
    )
    assert {node.title for node in depth_one.nodes} == {"A", "B"}
    depth_two = knowledge_service.graphs.get_document_graph(
        source.id,
        ids["A"],
        depth=2,
        direction="outgoing",
        confirm_sensitive=True,
    )
    assert {node.title for node in depth_two.nodes} == {"A", "B", "C"}
    incoming = knowledge_service.graphs.get_document_graph(
        source.id,
        ids["A"],
        depth=1,
        direction="incoming",
        confirm_sensitive=True,
    )
    assert {node.title for node in incoming.nodes} == {"A", "C"}


def test_graph_filters_and_validates_bounds(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    root = tmp_path / "docs"
    _write(root / "Guide.md", "---\ntags: [python]\n---\n# Guide\nsearchable")
    _write(root / "Other.md", "# Other")
    source = knowledge_service.add_source(root, name="docs", category="development")
    knowledge_service.scan_source(source.id)

    graph = knowledge_service.graphs.get_source_graph(
        source.id, tag="python", query="searchable"
    )
    assert [node.title for node in graph.nodes] == ["Guide"]

    with pytest.raises(KnowledgeContractError) as depth_error:
        knowledge_service.graphs.get_document_graph(source.id, "missing", depth=4)
    assert depth_error.value.code == "INVALID_DEPTH"
    with pytest.raises(KnowledgeContractError) as limit_error:
        knowledge_service.graphs.get_source_graph(source.id, limit=1001)
    assert limit_error.value.code == "INVALID_LIMIT"

    limited = knowledge_service.graphs.get_source_graph(source.id, limit=1)
    assert limited.total_document_count == 2
    assert limited.returned_document_count == 1
    assert limited.truncated is True


def test_wiki_display_text_is_preserved_in_graph_edge(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    root = tmp_path / "docs"
    _write(
        root / "A.md",
        "# A\n[[B#Heading|Friendly name]]\n[Site](https://example.com)\n![[file.pdf]]",
    )
    _write(root / "B.md", "# B")
    source = knowledge_service.add_source(root, name="docs", category="development")
    knowledge_service.scan_source(source.id)

    graph = knowledge_service.graphs.get_source_graph(source.id)

    assert graph.edges[0].display_text == "Friendly name"
    with sqlite3.connect(knowledge_service.repository.path) as connection:
        rows = connection.execute(
            "SELECT raw_target, normalized_target, heading, display_text, "
            "resolution_status, is_resolved FROM knowledge_links ORDER BY id"
        ).fetchall()
    assert rows == [
        ("file.pdf", "file.pdf", None, None, "attachment", 0),
        ("B#Heading|Friendly name", "B", "Heading", "Friendly name", "resolved", 1),
        ("https://example.com", "https://example.com", None, "Site", "external", 0),
    ]


def test_explicit_link_resolves_only_to_approved_shared_source(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    common_root = tmp_path / "mde-docs"
    project_root = tmp_path / "project"
    blocked_root = tmp_path / "blocked"
    _write(common_root / "04_development" / "DEV-001.md", "# 개발 표준")
    _write(blocked_root / "Secret.md", "# Secret")
    _write(
        project_root / "Work.md",
        "# Work\n[[mde-docs::04_development/DEV-001|개발 표준]]\n"
        "[[blocked::Secret|차단 대상]]",
    )
    common = knowledge_service.add_source(
        common_root, name="mde-docs", category="development"
    )
    project = knowledge_service.add_source(
        project_root, name="project", category="project"
    )
    knowledge_service.add_source(
        blocked_root, name="blocked", category="development"
    )
    knowledge_service.update_source(
        common.id, allow_as_shared_link_target=True
    )
    knowledge_service.scan_selected(all_sources=True)

    detail = knowledge_service.graphs.get_document_detail(
        project.id, f"{project.id}::Work.md"
    )
    assert [item.source_id for item in detail.outgoing_documents] == [common.id]
    assert [item.title for item in detail.outgoing_documents] == ["개발 표준"]
    assert detail.unresolved_links == ("blocked::Secret",)

    graph = knowledge_service.graphs.get_source_graph(project.id, include_broken=True)
    assert {node.source_id for node in graph.nodes} == {project.id, common.id}
    assert len(graph.edges) == 1
    assert graph.edges[0].target == f"{common.id}::04_development/DEV-001.md"

    common_detail = knowledge_service.graphs.get_document_detail(
        common.id, f"{common.id}::04_development/DEV-001.md"
    )
    assert [item.source_id for item in common_detail.incoming_documents] == [project.id]
