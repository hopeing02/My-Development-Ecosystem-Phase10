from dataclasses import replace
from pathlib import Path

import pytest

from mde.knowledge.document_commands import DocumentUpdate, KnowledgeDocumentCommandService
from mde.knowledge.errors import KnowledgeContractError
from mde.knowledge.parser import parse_markdown
from mde.knowledge.service import KnowledgeService


def _indexed_service(tmp_path: Path, first_content: str) -> tuple[KnowledgeService, Path, str, str]:
    root = tmp_path / "vault"
    root.mkdir()
    first = root / "첫 문서.md"
    first.write_text(first_content, encoding="utf-8")
    (root / "대상 문서.md").write_text("---\ntitle: 대상 문서\n---\n# 대상 문서\n", encoding="utf-8")
    service = KnowledgeService(registry_path=tmp_path / "sources.json", database_path=tmp_path / "knowledge.db")
    source = service.add_source(root, name="개발", category="development")
    service.scan_source(source.id)
    first_id = f"{source.id}::첫 문서.md"
    target_id = f"{source.id}::대상 문서.md"
    return service, first, first_id, target_id


def test_update_preserves_unknown_frontmatter_bom_and_creates_backup(tmp_path: Path) -> None:
    service, path, document_id, _ = _indexed_service(
        tmp_path,
        "---\ntitle: 이전\ntags: [old]\naliases: [예전]\ncreated: 2026-07-30\ncustom_field: 유지\n---\n# 이전\n본문\n",
    )
    original = path.read_bytes()
    path.write_bytes(b"\xef\xbb\xbf" + original)
    service.index_file("ks-001", "첫 문서.md", require_capture_write=False)
    detail = service.graphs.get_document_detail("ks-001", document_id)
    commands = KnowledgeDocumentCommandService(service)

    result = commands.update_document(
        "ks-001",
        document_id,
        DocumentUpdate(detail.content_hash, "새 제목", ["#MDE", " MDE ", ""], ["새 별칭", "새 별칭"], "# 이전\n수정 본문\n"),
        confirm_sensitive=False,
    )

    assert result["indexing"]["status"] == "completed"
    assert result["graphRevision"] == 1
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    text = path.read_text(encoding="utf-8-sig")
    assert "custom_field: 유지" in text
    assert "created: 2026-07-30" in text
    assert "# 새 제목" in text
    parsed = parse_markdown(text, path)
    assert parsed.tags == ("MDE",)
    assert parsed.aliases == ("새 별칭",)
    backups = tuple((path.parent / ".mde-backups").rglob("첫 문서.*.md"))
    assert len(backups) == 1


def test_preview_does_not_write_and_conflict_keeps_external_change(tmp_path: Path) -> None:
    service, path, document_id, _ = _indexed_service(tmp_path, "# 처음\n")
    detail = service.graphs.get_document_detail("ks-001", document_id)
    commands = KnowledgeDocumentCommandService(service)
    update = DocumentUpdate(detail.content_hash, "미리보기", ["tag"], [], "본문")

    preview = commands.preview_update("ks-001", document_id, update, confirm_sensitive=False)
    assert preview["after"]["title"] == "미리보기"
    assert path.read_text(encoding="utf-8") == "# 처음\n"

    path.write_text("# 외부 변경\n", encoding="utf-8")
    with pytest.raises(KnowledgeContractError) as captured:
        commands.update_document("ks-001", document_id, update, confirm_sensitive=False)
    assert captured.value.code == "DOCUMENT_CONFLICT"
    assert path.read_text(encoding="utf-8") == "# 외부 변경\n"


def test_read_only_source_is_blocked(tmp_path: Path) -> None:
    service, _, document_id, _ = _indexed_service(tmp_path, "# 처음\n")
    current = service.registry.get("ks-001")
    service.registry._save([replace(current, read_only=True)])
    detail = service.graphs.get_document_detail("ks-001", document_id)

    with pytest.raises(KnowledgeContractError) as captured:
        KnowledgeDocumentCommandService(service).update_document(
            "ks-001",
            document_id,
            DocumentUpdate(detail.content_hash, "변경", [], [], "본문"),
            confirm_sensitive=False,
        )
    assert captured.value.code == "SOURCE_READ_ONLY"


def test_link_resolution_rewrites_only_selected_occurrence_and_reindexes(tmp_path: Path) -> None:
    service, path, document_id, target_id = _indexed_service(
        tmp_path, "# 링크\n[[없는 대상]]\n[[없는 대상]]\n"
    )
    detail = service.graphs.get_document_detail("ks-001", document_id)
    assert len(detail.unresolved_occurrences) == 2
    occurrence = detail.unresolved_occurrences[1]
    commands = KnowledgeDocumentCommandService(service)

    preview = commands.preview_link_resolution(
        "ks-001", document_id,
        expected_content_hash=detail.content_hash,
        occurrence_id=occurrence.occurrence_id,
        target_document_id=target_id,
        link_style="preserve",
        confirm_sensitive=False,
    )
    assert preview["before"] == "[[없는 대상]]"
    assert preview["after"] == "[[대상 문서|없는 대상]]"

    result = commands.resolve_link(
        "ks-001", document_id,
        expected_content_hash=detail.content_hash,
        occurrence_id=occurrence.occurrence_id,
        target_document_id=target_id,
        link_style="preserve",
        create_backup=True,
        confirm_sensitive=False,
    )
    assert path.read_text(encoding="utf-8").count("[[없는 대상]]") == 1
    assert "[[대상 문서|없는 대상]]" in path.read_text(encoding="utf-8")
    assert result["indexing"]["unresolvedLinkCount"] == 1
    target_detail = service.graphs.get_document_detail("ks-001", target_id)
    assert [item.document_id for item in target_detail.incoming_documents] == [document_id]


def test_append_child_link_updates_parent_atomically_and_is_idempotent(
    tmp_path: Path,
) -> None:
    service, path, parent_id, target_id = _indexed_service(
        tmp_path,
        "---\ntitle: 상위 주제\ntags: [parent]\ncustom: 유지\n---\n"
        "# 상위 주제\n\n본문\n",
    )
    commands = KnowledgeDocumentCommandService(service)

    result = commands.append_child_link(
        "개발", parent_id, target_id, confirm_sensitive=False
    )

    text = path.read_text(encoding="utf-8")
    assert "custom: 유지" in text
    assert "## AutoKnowledge 하위 문서" in text
    assert "- [[대상 문서|대상 문서]]" in text
    assert result["alreadyLinked"] is False
    assert isinstance(result["document"]["modifiedAt"], str)
    target_detail = service.graphs.get_document_detail("ks-001", target_id)
    assert [item.document_id for item in target_detail.incoming_documents] == [
        parent_id
    ]

    repeated = commands.append_child_link(
        "개발", parent_id, target_id, confirm_sensitive=False
    )

    assert repeated["alreadyLinked"] is True
    assert path.read_text(encoding="utf-8").count("[[대상 문서|대상 문서]]") == 1
