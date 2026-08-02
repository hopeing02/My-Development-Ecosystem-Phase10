from pathlib import Path

from autoknowledge_lite.capture import (
    CaptureService,
    IndexFailureStore,
    safe_filename,
)
from autoknowledge_lite.mde_client import (
    CaptureSource,
    MDEClientError,
)


class FakeClient:
    def __init__(self, root: Path, *, index_error: str | None = None) -> None:
        self.root = root
        self.index_error = index_error
        self.indexed: list[tuple[str, str]] = []

    def source_path(self, source: str) -> CaptureSource:
        return CaptureSource(
            id="ks-001",
            name=source,
            category="personal",
            source_type="obsidian",
            enabled=True,
            sensitive=True,
            writable_by_capture_app=True,
            path=self.root,
        )

    def index_file(self, source: str, relative_path: str) -> dict[str, object]:
        self.indexed.append((source, relative_path))
        if self.index_error:
            raise MDEClientError(self.index_error, "index failed")
        return {"documentId": f"ks-001::{relative_path}"}


def test_capture_saves_atomically_avoids_overwrite_and_indexes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    client = FakeClient(vault)
    service = CaptureService(
        mde_client=client,
        failure_store=IndexFailureStore(tmp_path / "failures.json"),
    )

    first = service.save(
        source_name="personal",
        folder="생활/자동화",
        title="여민전 자동 충전",
        content="원본 내용",
        tags=("생활", "자동화"),
    )
    second = service.save(
        source_name="personal",
        folder="생활/자동화",
        title="여민전 자동 충전",
        content="두 번째 내용",
    )

    assert first.file_saved and first.index_succeeded
    assert first.relative_path == "생활/자동화/여민전-자동-충전.md"
    assert second.relative_path == "생활/자동화/여민전-자동-충전-2.md"
    assert first.saved_path is not None
    markdown = first.saved_path.read_text(encoding="utf-8")
    assert 'title: "여민전 자동 충전"' in markdown
    assert "원본 내용" in markdown
    assert client.indexed[0] == ("personal", first.relative_path)
    assert list(vault.rglob("*.tmp")) == []


def test_capture_keeps_saved_file_when_indexing_fails_and_retries(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    client = FakeClient(vault, index_error="DATABASE_ERROR")
    failures = IndexFailureStore(tmp_path / "failures.json")
    service = CaptureService(mde_client=client, failure_store=failures)

    result = service.save(source_name="personal", title="Saved", content="private body")

    assert result.file_saved is True
    assert result.index_succeeded is False
    assert result.saved_path is not None and result.saved_path.is_file()
    assert failures.list()[0].error_code == "DATABASE_ERROR"
    assert "private body" not in failures.path.read_text(encoding="utf-8")

    client.index_error = None
    service.retry_index("personal", result.relative_path or "")
    assert failures.list() == ()
    assert result.saved_path.read_text(encoding="utf-8").endswith("private body\n")


def test_capture_falls_back_when_mde_is_unavailable(tmp_path: Path) -> None:
    class MissingClient(FakeClient):
        def source_path(self, source: str) -> CaptureSource:
            raise MDEClientError("MDE_NOT_FOUND", "missing")

    fallback = tmp_path / "fallback"
    result = CaptureService(
        mde_client=MissingClient(tmp_path), fallback_vault=fallback
    ).save(source_name="personal", title="Offline", content="saved")

    assert result.file_saved is True
    assert result.index_attempted is False
    assert result.saved_path is not None and result.saved_path.is_relative_to(fallback)


def test_capture_rejects_path_escape_and_windows_reserved_names(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    service = CaptureService(mde_client=FakeClient(vault))

    result = service.save(
        source_name="personal", folder="../outside", title="Safe", content="body"
    )

    assert result.file_saved is False
    assert not (tmp_path / "outside").exists()
    assert safe_filename("CON") == "_CON.md"
    assert safe_filename("  invalid<> name. ") == "invalid-name.md"
