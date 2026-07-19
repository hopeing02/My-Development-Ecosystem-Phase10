from __future__ import annotations

from datetime import datetime, timezone

from autoknowledge_lite.models import ShareRecord
from autoknowledge_lite.obsidian import ObsidianNoteStore


def test_note_store_creates_safe_utf8_markdown_file(tmp_path) -> None:
    record = ShareRecord(
        job_id="12345678-0000-0000-0000-000000000000",
        received_at=datetime(2026, 7, 19, tzinfo=timezone.utc),
        content="본문",
        title="코덱스: 원격/연결? 문제",
    )
    markdown = "# 코덱스 원격 연결 문제\n\n내용"

    path = ObsidianNoteStore(tmp_path / "vault").save(record, markdown)

    assert path.name == "2026-07-19-코덱스-원격-연결-문제-12345678.md"
    assert path.read_text(encoding="utf-8") == markdown
