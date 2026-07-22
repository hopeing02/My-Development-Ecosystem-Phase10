import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mde.knowledge.audit import KnowledgeAuditLogger
from mde.knowledge.models import KnowledgeSource
from mde.knowledge.service import KnowledgeService


def _events(log_dir: Path) -> list[dict[str, object]]:
    paths = tuple(log_dir.glob("knowledge-*.log"))
    assert len(paths) == 1
    return [
        json.loads(line) for line in paths[0].read_text(encoding="utf-8").splitlines()
    ]


def test_source_lifecycle_audit_never_records_absolute_path_or_content(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    source_root = tmp_path / "민감한 개인 자료"
    source_root.mkdir()
    secret = "private-document-body"
    (source_root / "secret.md").write_text(secret, encoding="utf-8")

    knowledge_service.add_source(source_root, name="personal", category="personal")
    knowledge_service.update_source("personal", enabled=False)
    knowledge_service.remove_source("personal")

    log_dir = tmp_path / "user-data" / "logs"
    events = _events(log_dir)
    assert [event["event"] for event in events] == [
        "source.added",
        "source.updated",
        "source.removed",
    ]
    raw = next(log_dir.glob("knowledge-*.log")).read_text(encoding="utf-8")
    assert str(source_root.resolve()) not in raw
    assert secret not in raw
    assert events[1]["changes"] == {"enabled": False}


def test_scan_audit_records_counts_and_safe_relative_file_errors(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    source_root = tmp_path / "work"
    source_root.mkdir()
    (source_root / "good.md").write_text(
        "# Good\nsearch query secret", encoding="utf-8"
    )
    (source_root / "오류.md").write_bytes(b"\xff\xfeconfidential-content")
    knowledge_service.add_source(source_root, name="work", category="work")

    result = knowledge_service.scan_source("work")

    assert result.added_count == 1
    assert result.error_count == 1
    events = _events(tmp_path / "user-data" / "logs")
    assert [event["event"] for event in events] == [
        "source.added",
        "scan.started",
        "scan.completed",
    ]
    completed = events[-1]
    assert completed["counts"] == {
        "added": 1,
        "updated": 0,
        "deleted": 0,
        "unchanged": 0,
        "errors": 1,
    }
    assert completed["file_errors"] == [
        {"relative_path": "오류.md", "error": "unable to decode as UTF-8"}
    ]
    raw = next((tmp_path / "user-data" / "logs").glob("*.log")).read_text(
        encoding="utf-8"
    )
    assert str(source_root.resolve()) not in raw
    assert "confidential-content" not in raw
    assert "search query secret" not in raw


def test_search_query_and_results_are_not_audited(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    source_root = tmp_path / "docs"
    source_root.mkdir()
    (source_root / "doc.md").write_text(
        "# Visible\nunique-search-term", encoding="utf-8"
    )
    knowledge_service.add_source(source_root, name="docs", category="development")
    knowledge_service.scan_source("docs")
    log_path = next((tmp_path / "user-data" / "logs").glob("*.log"))
    before = log_path.read_text(encoding="utf-8")

    results = knowledge_service.search("unique-search-term")

    assert results[0].title == "Visible"
    assert log_path.read_text(encoding="utf-8") == before
    assert "unique-search-term" not in before


def test_audit_retention_deletes_only_logs_that_reached_thirty_days(
    tmp_path: Path,
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    expired = log_dir / "knowledge-2026-06-22.log"
    retained = log_dir / "knowledge-2026-06-23.log"
    unrelated = log_dir / "application-2026-06-01.log"
    malformed = log_dir / "knowledge-not-a-date.log"
    for path in (expired, retained, unrelated, malformed):
        path.write_text("keep-or-remove", encoding="utf-8")
    source_root = tmp_path / "source"
    source_root.mkdir()
    original = source_root / "original.md"
    original.write_text("# Original", encoding="utf-8")
    source = KnowledgeSource(
        id="ks-001",
        name="docs",
        path=source_root,
        category="development",
    )
    fixed_now = datetime(2026, 7, 22, 9, 0, tzinfo=timezone.utc)
    logger = KnowledgeAuditLogger(log_dir, clock=lambda: fixed_now)

    logger.source_added(source)

    assert not expired.exists()
    assert retained.exists()
    assert unrelated.exists()
    assert malformed.exists()
    assert original.read_text(encoding="utf-8") == "# Original"
    assert (log_dir / "knowledge-2026-07-22.log").exists()


def test_audit_retention_skips_symbolic_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    link = log_dir / "knowledge-2020-01-01.log"
    link.write_text("linked-content", encoding="utf-8")
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == link or original_is_symlink(path),
    )
    logger = KnowledgeAuditLogger(
        log_dir,
        clock=lambda: datetime(2026, 7, 22, tzinfo=timezone.utc),
    )

    assert logger.prune() == ()
    assert link.is_symlink()
    assert link.read_text(encoding="utf-8") == "linked-content"


def test_audit_retention_rejects_non_positive_days(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        KnowledgeAuditLogger(tmp_path, retention_days=0)
