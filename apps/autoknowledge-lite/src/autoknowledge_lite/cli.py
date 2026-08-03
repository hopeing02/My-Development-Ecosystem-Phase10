"""AutoKnowledge Lite command line capture and MDE integration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import UTC, datetime, time
from pathlib import Path

from autoknowledge_lite.capture import CaptureService
from autoknowledge_lite.capture_relations import (
    CaptureRelationRepository,
    CaptureRelationService,
    ingest_existing_captures,
)
from autoknowledge_lite.mde_client import MDEClientError, MDEKnowledgeClient
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoknowledge-lite")
    actions = parser.add_subparsers(dest="action")
    actions.add_parser("mde-info", help="Check the MDE JSON CLI contract.")
    actions.add_parser("sources", help="List capture-writable MDE sources.")
    capture = actions.add_parser("capture", help="Save Markdown and request indexing.")
    capture.add_argument("--source")
    capture.add_argument("--folder", default="00_Inbox")
    capture.add_argument("--title", required=True)
    capture.add_argument("--tag", action="append", default=[])
    content = capture.add_mutually_exclusive_group()
    content.add_argument("--content")
    content.add_argument("--clipboard", action="store_true")
    retry = actions.add_parser("retry-index", help="Retry one saved file index.")
    retry.add_argument("--source", required=True)
    retry.add_argument("--path", required=True)
    relations = actions.add_parser(
        "capture-relations", help="Manage excerpt_of Capture relations."
    )
    relation_actions = relations.add_subparsers(dest="relation_action")
    backfill = relation_actions.add_parser(
        "backfill", help="Match existing indexed captures."
    )
    backfill.add_argument("--data-dir", type=Path)
    backfill.add_argument("--vault-dir", type=Path)
    backfill.add_argument("--mde-codex-home", type=Path)
    backfill.add_argument("--dry-run", action="store_true")
    backfill.add_argument("--limit", type=int)
    backfill.add_argument("--project")
    backfill.add_argument("--from-date")
    backfill.add_argument("--to-date")
    backfill.add_argument("--no-auto-confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = MDEKnowledgeClient()
    try:
        if args.action == "mde-info":
            info = client.integration_info()
            print(f"MDE Knowledge Plugin {info['pluginVersion']} | API v1")
            return 0
        if args.action == "sources":
            for source in client.list_sources():
                if source.enabled and source.writable_by_capture_app:
                    marker = " · 민감" if source.sensitive else ""
                    print(f"{source.name}\t{source.category}{marker}")
            return 0
        if args.action == "capture":
            content = _capture_content(args)
            result = CaptureService(mde_client=client).save(
                title=args.title,
                content=content,
                tags=tuple(args.tag),
                source_name=args.source,
                folder=args.folder,
            )
            if not result.file_saved:
                print(f"문서를 저장하지 못했습니다: {result.error_code}")
                return 1
            print(f"저장 완료: {result.relative_path}")
            if result.index_succeeded:
                print(f"색인 완료: {result.document_id}")
            elif result.index_attempted:
                print(f"색인 실패: {result.error_code} (재시도 가능)")
            else:
                print("색인 건너뜀: MDE 연동 없음")
            return 0
        if args.action == "retry-index":
            result = CaptureService(mde_client=client).retry_index(
                args.source, args.path
            )
            print(f"색인 완료: {result.get('documentId', args.path)}")
            return 0
        if args.action == "capture-relations" and args.relation_action == "backfill":
            root = args.data_dir or JsonShareStore().root
            temporary = tempfile.TemporaryDirectory() if args.dry_run else None
            working_root = Path(temporary.name) if temporary else root
            service = CaptureRelationService(CaptureRelationRepository(working_root))
            if temporary:
                existing = CaptureRelationRepository(root).captures()
                for record in existing:
                    service.repository.upsert_capture(record)
            default_codex_home = Path(
                os.environ.get(
                    "MDE_CODEX_HOME",
                    Path(
                        os.environ.get(
                            "LOCALAPPDATA", Path.home() / "AppData" / "Local"
                        )
                    )
                    / "AutoKnowledgeLite"
                    / "CodexCollector",
                )
            )
            imported = ingest_existing_captures(
                service,
                capture_index_path=root / "capture-index-v1.json",
                vault_dir=args.vault_dir or ObsidianNoteStore().vault_dir,
                codex_home=args.mde_codex_home or default_codex_home,
            )
            report = service.backfill(
                dry_run=args.dry_run,
                limit=args.limit,
                project_id=args.project,
                from_date=_date_boundary(args.from_date, end=False),
                to_date=_date_boundary(args.to_date, end=True),
                auto_confirm=not args.no_auto_confirm,
            )
            report.update(
                {
                    f"imported{key[0].upper()}{key[1:]}": value
                    for key, value in imported.items()
                }
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if temporary:
                temporary.cleanup()
            return 0
        build_parser().print_help()
        return 2
    except MDEClientError as error:
        print(f"MDE 연동 오류: {error.code}")
        return 1


def _capture_content(args: argparse.Namespace) -> str:
    if args.clipboard:
        return _clipboard_text()
    if args.content is not None:
        return args.content
    return sys.stdin.read()


def _clipboard_text() -> str:
    try:
        import tkinter
    except ImportError as error:
        raise MDEClientError(
            "CLIPBOARD_UNAVAILABLE", "Unable to read the clipboard."
        ) from error
    try:
        root = tkinter.Tk()
        root.withdraw()
        try:
            return str(root.clipboard_get())
        finally:
            root.destroy()
    except tkinter.TclError as error:
        raise MDEClientError(
            "CLIPBOARD_UNAVAILABLE", "Unable to read the clipboard."
        ) from error


def _date_boundary(value: str | None, *, end: bool) -> datetime | None:
    if not value:
        return None
    selected = datetime.fromisoformat(value).date()
    return datetime.combine(
        selected,
        time.max if end else time.min,
        tzinfo=UTC,
    )


if __name__ == "__main__":
    raise SystemExit(main())
