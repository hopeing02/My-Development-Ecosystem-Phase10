"""Argument parser and output boundary for Knowledge Plugin commands."""

from __future__ import annotations

import argparse
from ipaddress import ip_address
import json
from pathlib import Path
import sys
import webbrowser

from mde.knowledge import __version__ as PLUGIN_VERSION
from mde.knowledge.errors import (
    KnowledgeContractError,
    KnowledgeError,
    SourceNotFoundError,
)
from mde.knowledge.models import SOURCE_CATEGORIES, SOURCE_TYPES, ScanResult
from mde.knowledge.service import KnowledgeService


def _boolean(value: str) -> bool:
    normalized = value.casefold()
    if normalized in {"true", "yes", "1", "on"}:
        return True
    if normalized in {"false", "no", "0", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _private_host(value: str) -> str:
    try:
        host = ip_address(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("host must be an IP address") from error
    if host.is_global or host.is_multicast:
        raise argparse.ArgumentTypeError(
            "host must be an all-interface bind, loopback, private LAN, or Tailscale IP address"
        )
    return str(host)


def register_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "knowledge", help="Manage local Markdown knowledge sources and indexes."
    )
    actions = parser.add_subparsers(dest="knowledge_action")

    add_parser = actions.add_parser("add", help="Register a knowledge source.")
    add_parser.add_argument("path")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--category", required=True, choices=SOURCE_CATEGORIES)
    add_parser.add_argument(
        "--type", dest="source_type", default="markdown", choices=SOURCE_TYPES
    )

    list_parser = actions.add_parser("list", help="List registered sources.")
    list_parser.add_argument("--format", dest="output_format", choices=("json",))
    info_parser = actions.add_parser(
        "integration-info", help="Show the capture integration contract."
    )
    info_parser.add_argument("--format", dest="output_format", choices=("json",))
    path_parser = actions.add_parser(
        "source-path", help="Resolve one capture-writable source path."
    )
    path_parser.add_argument("source")
    path_parser.add_argument("--format", dest="output_format", choices=("json",))
    index_parser = actions.add_parser(
        "index-file", help="Index one source-relative Markdown file."
    )
    index_parser.add_argument("--source", required=True)
    index_parser.add_argument("--path", required=True)
    index_parser.add_argument("--format", dest="output_format", choices=("json",))
    show_parser = actions.add_parser("show", help="Show one source.")
    show_parser.add_argument("source")

    update_parser = actions.add_parser("update", help="Update source settings.")
    update_parser.add_argument("source")
    update_parser.add_argument("--enabled", type=_boolean)
    update_parser.add_argument("--agent-access", type=_boolean)
    update_parser.add_argument("--capture-write", type=_boolean)
    update_parser.add_argument("--read-only", type=_boolean)
    update_parser.add_argument("--viewer-edit", type=_boolean)
    update_parser.add_argument("--link-rewrite", type=_boolean)
    update_parser.add_argument("--shared-link-target", type=_boolean)
    update_parser.add_argument("--confirm-sensitive-access", action="store_true")
    update_parser.add_argument("--confirm-sensitive-write", action="store_true")

    remove_parser = actions.add_parser(
        "remove", help="Remove index data, never source files."
    )
    remove_parser.add_argument("source")

    scan_parser = actions.add_parser("scan", help="Scan one or more sources.")
    scan_parser.add_argument("source", nargs="?")
    scan_parser.add_argument("--all", action="store_true", dest="all_sources")
    scan_parser.add_argument("--category", choices=SOURCE_CATEGORIES)
    scan_parser.add_argument("--include-sensitive", action="store_true")

    search_parser = actions.add_parser("search", help="Search indexed documents.")
    search_parser.add_argument("query", nargs="?")
    search_parser.add_argument("--source")
    search_parser.add_argument("--category", choices=SOURCE_CATEGORIES)
    search_parser.add_argument("--tag")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--all", action="store_true", dest="all_sources")
    search_parser.add_argument("--include-sensitive", action="store_true")
    search_parser.add_argument("--format", dest="output_format", choices=("json",))

    link_child_parser = actions.add_parser(
        "link-child", help="Append one child document link to a parent document."
    )
    link_child_parser.add_argument("--source", required=True)
    link_child_parser.add_argument("--parent", required=True)
    link_child_parser.add_argument("--target", required=True)
    link_child_parser.add_argument("--confirm-sensitive", action="store_true")
    link_child_parser.add_argument(
        "--format", dest="output_format", choices=("json",)
    )

    backlinks_parser = actions.add_parser(
        "backlinks", help="Show same-source backlinks."
    )
    backlinks_parser.add_argument("document")
    backlinks_parser.add_argument("--source", required=True)
    backlinks_parser.add_argument("--limit", type=int, default=100)

    serve_parser = actions.add_parser("serve", help="Run the local Graph API.")
    serve_parser.add_argument("--host", type=_private_host, default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--no-open", action="store_true")


def run(args: argparse.Namespace, service: KnowledgeService | None = None) -> int:
    _configure_console_output()
    knowledge = service or KnowledgeService()
    output_format = getattr(args, "output_format", None)
    try:
        if args.knowledge_action == "integration-info":
            payload = {
                "pluginVersion": PLUGIN_VERSION,
                "capabilities": ["list-sources", "source-path", "index-file"],
            }
            if output_format == "json":
                _print_json(_success(payload))
            else:
                print(f"Knowledge Plugin: {PLUGIN_VERSION}")
                print("Capabilities: list-sources, source-path, index-file")
            return 0
        if args.knowledge_action == "serve":
            from mde.knowledge.api import create_app

            try:
                import uvicorn
            except ImportError as error:
                raise KnowledgeContractError(
                    "MDE_NOT_READY", "Graph API dependencies are not installed."
                ) from error
            if not 1 <= args.port <= 65535:
                raise KnowledgeContractError(
                    "INVALID_PORT", "Server port must be between 1 and 65535."
                )
            url_host = f"[{args.host}]" if ":" in args.host else args.host
            url = f"http://{url_host}:{args.port}"
            print("MDE Knowledge Viewer is running.\n")
            print(f"URL: {url}")
            print("Press Ctrl+C to stop.")
            if not args.no_open:
                webbrowser.open(url)
            uvicorn.run(create_app(knowledge), host=args.host, port=args.port)
            return 0
        if args.knowledge_action == "add":
            source = knowledge.add_source(
                Path(args.path),
                name=args.name,
                category=args.category,
                source_type=args.source_type,
            )
            print(f"Knowledge source added: {source.name} ({source.id})")
            print(f"Path: {source.path}")
            return 0
        if args.knowledge_action == "list":
            if output_format == "json":
                _print_json(
                    _success(
                        {
                            "sources": [
                                _source_payload(source)
                                for source in knowledge.list_sources()
                            ]
                        }
                    )
                )
                return 0
            print("ID\tNAME\tCATEGORY\tTYPE\tSENSITIVE\tAGENT\tPATH")
            for source in knowledge.list_sources():
                print(
                    f"{source.id}\t{source.name}\t{source.category}\t{source.source_type}\t"
                    f"{'yes' if source.sensitive else 'no'}\t"
                    f"{'yes' if source.allow_agent_access else 'no'}\t{source.path}"
                )
            return 0
        if args.knowledge_action == "source-path":
            source, _ = knowledge.show_source(args.source)
            if not source.enabled:
                raise KnowledgeContractError(
                    "SOURCE_DISABLED",
                    "Knowledge source is disabled.",
                    source=args.source,
                )
            if not source.writable_by_capture_app:
                raise KnowledgeContractError(
                    "SOURCE_NOT_WRITABLE",
                    "Knowledge source does not allow capture application writes.",
                    source=args.source,
                )
            payload = _source_payload(source)
            payload["path"] = str(source.path)
            if output_format == "json":
                _print_json(_success({"source": payload}))
            else:
                print(source.path)
            return 0
        if args.knowledge_action == "index-file":
            result = knowledge.index_file(args.source, args.path)
            payload = {
                "sourceId": result.source.id,
                "sourceName": result.source.name,
                "documentId": result.document_id,
                "relativePath": result.relative_path,
                "indexed": result.indexed,
                "status": result.status,
                "title": result.title,
                "tagCount": result.tag_count,
                "linkCount": result.link_count,
                "warningCount": len(result.warnings),
                "warnings": list(result.warnings),
            }
            if output_format == "json":
                _print_json(_success({"result": payload}))
            else:
                print(
                    f"Knowledge file {result.status}: "
                    f"{result.source.name}/{result.relative_path}"
                )
            return 0
        if args.knowledge_action == "show":
            source, documents = knowledge.show_source(args.source)
            print(f"Name: {source.name}")
            print(f"Category: {source.category}")
            print(f"Type: {source.source_type}")
            print(f"Path: {source.path}")
            print(f"Enabled: {str(source.enabled).lower()}")
            print(f"Sensitive: {str(source.sensitive).lower()}")
            print(f"Agent access: {str(source.allow_agent_access).lower()}")
            print(f"Viewer editable: {str(source.editable_in_viewer).lower()}")
            print(f"Link rewrite: {str(source.allow_link_rewrite).lower()}")
            print(
                "Shared link target: "
                f"{str(source.allow_as_shared_link_target).lower()}"
            )
            print(f"Documents: {documents}")
            print(f"Last scanned: {source.last_scanned_at or '-'}")
            return 0
        if args.knowledge_action == "update":
            source = knowledge.update_source(
                args.source,
                enabled=args.enabled,
                allow_agent_access=args.agent_access,
                writable_by_capture_app=args.capture_write,
                read_only=args.read_only,
                editable_in_viewer=args.viewer_edit,
                allow_link_rewrite=args.link_rewrite,
                allow_as_shared_link_target=args.shared_link_target,
                confirm_sensitive_access=args.confirm_sensitive_access,
                confirm_sensitive_write=args.confirm_sensitive_write,
            )
            print(f"Knowledge source updated: {source.name}")
            return 0
        if args.knowledge_action == "remove":
            source = knowledge.remove_source(args.source)
            print(f"Knowledge source removed: {source.name}")
            print("Original files preserved.")
            return 0
        if args.knowledge_action == "scan":
            if args.source:
                results = (knowledge.scan_source(args.source),)
            else:
                results = knowledge.scan_selected(
                    all_sources=args.all_sources,
                    category=args.category,
                    include_sensitive=args.include_sensitive,
                )
            for result in results:
                _print_scan(result)
            return 0
        if args.knowledge_action == "search":
            results = knowledge.search(
                args.query,
                source=args.source,
                category=args.category,
                all_sources=args.all_sources,
                include_sensitive=args.include_sensitive,
                tag=args.tag,
                limit=args.limit,
            )
            if output_format == "json":
                _print_json(
                    _success(
                        {
                            "documents": [
                                {
                                    "id": item.document_id,
                                    "sourceId": item.source_id,
                                    "sourceName": item.source_name,
                                    "title": item.title,
                                    "relativePath": item.relative_path,
                                    "snippet": item.snippet,
                                }
                                for item in results
                            ]
                        }
                    )
                )
                return 0
            for result in results:
                marker = " | SENSITIVE" if result.sensitive else ""
                print(
                    f"[{result.source_name} | {result.category}{marker}] {result.title}"
                )
                print(result.relative_path)
                print(f"{result.snippet}\n")
            return 0
        if args.knowledge_action == "link-child":
            from mde.knowledge.document_commands import (
                KnowledgeDocumentCommandService,
            )

            result = KnowledgeDocumentCommandService(knowledge).append_child_link(
                args.source,
                args.parent,
                args.target,
                confirm_sensitive=args.confirm_sensitive,
            )
            if output_format == "json":
                _print_json(_success({"result": result}))
            else:
                print(f"Parent link updated: {args.parent} -> {args.target}")
            return 0
        if args.knowledge_action == "backlinks":
            results = knowledge.backlinks(
                args.document, source=args.source, limit=args.limit
            )
            print(f"Backlinks for: {args.document}")
            print(f"Source: {args.source}\n")
            for result in results:
                print(f"[{result.source_name}] {result.relative_path}")
            return 0
        print("Use a knowledge subcommand. Run 'mde knowledge -h' for details.")
        return 2
    except SourceNotFoundError:
        if output_format == "json":
            _print_json(_failure("SOURCE_NOT_FOUND", "Knowledge source was not found."))
        else:
            print("Knowledge source was not found.")
        return 1
    except KnowledgeContractError as error:
        if output_format == "json":
            _print_json(_failure(error.code, str(error), error.details))
        else:
            print(error)
        return 1
    except KnowledgeError as error:
        if output_format == "json":
            _print_json(_failure("INDEX_ERROR", "Knowledge operation failed."))
            return 1
        print(error)
        return 1


def _source_payload(source) -> dict[str, object]:
    return {
        "id": source.id,
        "name": source.name,
        "category": source.category,
        "sourceType": source.source_type,
        "enabled": source.enabled,
        "sensitive": source.sensitive,
        "writableByCaptureApp": source.writable_by_capture_app,
    }


def _success(data: dict[str, object]) -> dict[str, object]:
    return {"apiVersion": "1", "success": True, **data}


def _failure(
    code: str, message: str, details: dict[str, str] | None = None
) -> dict[str, object]:
    return {
        "apiVersion": "1",
        "success": False,
        "error": {"code": code, "message": message, "details": details or {}},
    }


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _configure_console_output() -> None:
    """Keep narrow console encodings from crashing on indexed Unicode text."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")


def _print_scan(result: ScanResult) -> None:
    print(f"Knowledge source: {result.source.name}")
    print(f"Category: {result.source.category}")
    print(f"Added: {result.added_count}")
    print(f"Updated: {result.updated_count}")
    print(f"Deleted: {result.deleted_count}")
    print(f"Unchanged: {result.unchanged_count}")
    print(f"Errors: {result.error_count}")
    if result.errors:
        print("Failed:")
        for error in result.errors:
            print(f"- {error.relative_path}: {error.message}")
