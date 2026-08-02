"""AutoKnowledge Lite command line capture and MDE integration."""

from __future__ import annotations

import argparse
import sys

from autoknowledge_lite.capture import CaptureService
from autoknowledge_lite.mde_client import MDEClientError, MDEKnowledgeClient


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


if __name__ == "__main__":
    raise SystemExit(main())
