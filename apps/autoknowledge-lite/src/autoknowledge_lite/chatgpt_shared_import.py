"""Archive-first import orchestration for explicit ChatGPT shared links."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from autoknowledge_lite.chatgpt_import import (
    ChatGPTImportIssue,
    ChatGPTImportResult,
    ChatGPTIssueStore,
    ChatGPTProjectionStore,
    chatgpt_source_content_hash,
)
from autoknowledge_lite.chatgpt_knowledge_adapter import (
    ChatGPTKnowledgeAdapter,
    ChatGPTKnowledgeAdapterError,
)
from autoknowledge_lite.chatgpt_shared_archive import (
    ChatGPTSharedSnapshot,
    ChatGPTSharedSnapshotFetcher,
    ChatGPTSharedSnapshotStore,
)
from autoknowledge_lite.chatgpt_shared_link_source import (
    ChatGPTSharedLinkSource,
    ChatGPTSharedLinkSourceError,
)


class SharedSnapshotFetcher(Protocol):
    def fetch(self, shared_url: str) -> ChatGPTSharedSnapshot: ...


class ChatGPTSharedImportService:
    """Fetch, archive, then project one recoverable public shared snapshot."""

    def __init__(
        self,
        data_dir: Path,
        *,
        fetcher: SharedSnapshotFetcher | None = None,
        archive_store: ChatGPTSharedSnapshotStore | None = None,
        projection_store: ChatGPTProjectionStore | None = None,
        issue_store: ChatGPTIssueStore | None = None,
        adapter: ChatGPTKnowledgeAdapter | None = None,
    ) -> None:
        self.data_dir = data_dir.resolve()
        self.fetcher = fetcher or ChatGPTSharedSnapshotFetcher()
        self.archive_store = archive_store or ChatGPTSharedSnapshotStore(self.data_dir)
        self.projection_store = projection_store or ChatGPTProjectionStore(
            self.data_dir
        )
        self.issue_store = issue_store or ChatGPTIssueStore(self.data_dir)
        self.adapter = adapter or ChatGPTKnowledgeAdapter()

    def import_shared_link(self, shared_url: str) -> ChatGPTImportResult:
        snapshot = self.fetcher.fetch(shared_url)
        archived = self.archive_store.archive(snapshot)
        source = ChatGPTSharedLinkSource(shared_url, archived.snapshot_path)
        try:
            discovery = source.discover_sessions()
        except ChatGPTSharedLinkSourceError as error:
            issue = ChatGPTImportIssue(
                code=error.code,
                source_member=f"chatgpt-share:{snapshot.share_id}",
                source_index=0,
                session_id=snapshot.share_id,
            )
            issue_path = self.issue_store.save(archived.import_id, (issue,))
            return ChatGPTImportResult(
                import_id=archived.import_id,
                raw_archive_path=archived.snapshot_path,
                raw_duplicate=archived.duplicate,
                discovered_sessions=0,
                projected_sessions=0,
                duplicate_sessions=0,
                failed_sessions=1,
                issue_report_path=issue_path,
                issues=(issue,),
            )
        if not (
            discovery.archive_sha256
            == archived.manifest.snapshot_sha256
            == snapshot.snapshot_sha256
        ):
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_ARCHIVE_HASH_MISMATCH",
                "Archived shared snapshot does not match its fetched content",
            )

        issues = [
            ChatGPTImportIssue(
                code=warning.code,
                source_member=warning.source_member,
                source_index=warning.source_index,
            )
            for warning in discovery.warnings
        ]
        reference = discovery.sessions[0]
        try:
            source_session = source.read_session(reference)
            projection = self.adapter.project(source_session)
        except (ChatGPTSharedLinkSourceError, ChatGPTKnowledgeAdapterError) as error:
            issue = ChatGPTImportIssue(
                code=error.code,
                source_member=reference.source_member,
                source_index=reference.source_index,
                session_id=reference.source_session_id,
            )
            issues.append(issue)
            issue_path = self.issue_store.save(archived.import_id, tuple(issues))
            return ChatGPTImportResult(
                import_id=archived.import_id,
                raw_archive_path=archived.snapshot_path,
                raw_duplicate=archived.duplicate,
                discovered_sessions=1,
                projected_sessions=0,
                duplicate_sessions=0,
                failed_sessions=1,
                issue_report_path=issue_path,
                issues=tuple(issues),
            )

        revision = self.projection_store.save(
            projection,
            import_id=archived.import_id,
            session_ref=reference,
            source_content_hash=chatgpt_source_content_hash(source_session),
        )
        issues.extend(
            ChatGPTImportIssue(
                code=warning,
                source_member=reference.source_member,
                source_index=reference.source_index,
                session_id=reference.source_session_id,
            )
            for warning in projection.warnings
        )
        issue_path = self.issue_store.save(archived.import_id, tuple(issues))
        return ChatGPTImportResult(
            import_id=archived.import_id,
            raw_archive_path=archived.snapshot_path,
            raw_duplicate=archived.duplicate,
            discovered_sessions=1,
            projected_sessions=0 if revision.duplicate else 1,
            duplicate_sessions=1 if revision.duplicate else 0,
            failed_sessions=0,
            issue_report_path=issue_path,
            revisions=(revision,),
            issues=tuple(issues),
        )
