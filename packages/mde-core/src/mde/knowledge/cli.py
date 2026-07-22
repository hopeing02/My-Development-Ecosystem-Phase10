"""Argument parser and output boundary for Knowledge Plugin commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from mde.knowledge.errors import KnowledgeError
from mde.knowledge.models import SOURCE_CATEGORIES, SOURCE_TYPES, ScanResult
from mde.knowledge.service import KnowledgeService


def _boolean(value: str) -> bool:
    normalized = value.casefold()
    if normalized in {"true", "yes", "1", "on"}:
        return True
    if normalized in {"false", "no", "0", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


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

    actions.add_parser("list", help="List registered sources.")
    show_parser = actions.add_parser("show", help="Show one source.")
    show_parser.add_argument("source")

    update_parser = actions.add_parser("update", help="Update source settings.")
    update_parser.add_argument("source")
    update_parser.add_argument("--enabled", type=_boolean)
    update_parser.add_argument("--agent-access", type=_boolean)
    update_parser.add_argument("--confirm-sensitive-access", action="store_true")

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

    backlinks_parser = actions.add_parser(
        "backlinks", help="Show same-source backlinks."
    )
    backlinks_parser.add_argument("document")
    backlinks_parser.add_argument("--source", required=True)
    backlinks_parser.add_argument("--limit", type=int, default=100)


def run(args: argparse.Namespace, service: KnowledgeService | None = None) -> int:
    knowledge = service or KnowledgeService()
    try:
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
            print("ID\tNAME\tCATEGORY\tTYPE\tSENSITIVE\tAGENT\tPATH")
            for source in knowledge.list_sources():
                print(
                    f"{source.id}\t{source.name}\t{source.category}\t{source.source_type}\t"
                    f"{'yes' if source.sensitive else 'no'}\t"
                    f"{'yes' if source.allow_agent_access else 'no'}\t{source.path}"
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
            print(f"Documents: {documents}")
            print(f"Last scanned: {source.last_scanned_at or '-'}")
            return 0
        if args.knowledge_action == "update":
            source = knowledge.update_source(
                args.source,
                enabled=args.enabled,
                allow_agent_access=args.agent_access,
                confirm_sensitive_access=args.confirm_sensitive_access,
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
            for result in results:
                marker = " | SENSITIVE" if result.sensitive else ""
                print(
                    f"[{result.source_name} | {result.category}{marker}] {result.title}"
                )
                print(result.relative_path)
                print(f"{result.snippet}\n")
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
        print(
            "Use knowledge add, list, show, update, remove, scan, search, or backlinks."
        )
        return 2
    except KnowledgeError as error:
        print(error)
        return 1


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
