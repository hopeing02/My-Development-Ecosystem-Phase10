from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from mde.codex_capture.service import CodexCaptureError, CodexCaptureService


def register_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "codex", help="Capture Windows Codex development sessions."
    )
    actions = parser.add_subparsers(dest="codex_action")

    register = actions.add_parser("register", help="Register a Git project.")
    register.add_argument("--project-id", required=True)
    register.add_argument("--path", required=True, type=Path)
    register.add_argument("--target-folder", default="40_Reference/Codex")
    register.add_argument("--display-name")

    unregister = actions.add_parser("unregister", help="Unregister a project.")
    unregister.add_argument("--project-id", required=True)
    actions.add_parser("list", help="List registered projects.")

    start = actions.add_parser("start", help="Start a capture session.")
    start.add_argument("--project", required=True)
    start.add_argument("--title", required=True)
    start.add_argument("--request")
    start.add_argument(
        "--launch",
        action="store_true",
        help="Launch the detected Codex executable and finalize when it exits.",
    )

    for name in ("stop", "finalize"):
        finalize = actions.add_parser(name, help=f"{name.title()} a capture session.")
        finalize.add_argument("--session")
        finalize.add_argument("--summary")

    status = actions.add_parser("status", help="Show active or named session status.")
    status.add_argument("--session")
    status.add_argument("--json", action="store_true")

    run = actions.add_parser("run", help="Run and capture a command.")
    run.add_argument("--session")
    run.add_argument("--cwd", type=Path)
    run.add_argument("--timeout", type=float)
    run.add_argument("command_args", nargs=argparse.REMAINDER)

    retry = actions.add_parser("retry", help="Retry queued sessions.")
    retry.add_argument("--session")

    note = actions.add_parser("add-note", help="Append a session note.")
    note.add_argument("--session")
    note.add_argument("--type", default="progress")
    note.add_argument("--message", required=True)

    actions.add_parser("doctor", help="Inspect the Windows collector environment.")


def run(args: argparse.Namespace, service: CodexCaptureService | None = None) -> int:
    service = service or CodexCaptureService()
    try:
        if args.codex_action == "register":
            item = service.register(
                args.project_id, args.path, args.target_folder, args.display_name
            )
            print(f"Registered: {item['projectId']} -> {item['repositoryPath']}")
            return 0
        if args.codex_action == "unregister":
            service.unregister(args.project_id)
            print(f"Unregistered: {args.project_id}")
            return 0
        if args.codex_action == "list":
            for item in service.list_projects():
                print(
                    f"{item['projectId']}: {item['repositoryPath']} -> {item['targetFolder']}"
                )
            return 0
        if args.codex_action == "start":
            session = service.start(args.project, args.title, args.request)
            print(f"Session started: {session['captureSessionId']}")
            if args.launch:
                executable = shutil.which("codex")
                if not executable:
                    raise CodexCaptureError(
                        "CODEX_NOT_FOUND", "Codex executable was not detected"
                    )
                completed = subprocess.run(
                    [executable], cwd=session["repositoryRoot"], check=False
                )
                result = service.finalize(
                    session_id=session["captureSessionId"],
                    closure_reason="process_exit",
                )
                print(f"Codex exited: {completed.returncode}")
                print(f"Session finalized: {result['state']}")
            return 0
        if args.codex_action in {"stop", "finalize"}:
            result = service.finalize(
                session_id=args.session,
                summary=args.summary,
                closure_reason=(
                    "manual_stop" if args.codex_action == "stop" else "manual_finalize"
                ),
            )
            print(
                f"Session finalized: {result['captureSessionId']} [{result['state']}]"
            )
            return 0
        if args.codex_action == "status":
            session = (
                service.load_session(args.session) if args.session else service.active()
            )
            if session is None:
                print("No active Codex capture session.")
                return 1
            if args.json:
                print(json.dumps(session, ensure_ascii=False, indent=2))
            else:
                print(f"Session: {session['captureSessionId']}")
                print(f"Project: {session['projectId']}")
                print(f"State: {session['state']}")
                print(f"Commands: {len(session['commands'])}")
            return 0
        if args.codex_action == "run":
            command = list(args.command_args)
            if command and command[0] == "--":
                command = command[1:]
            result = service.run_command(
                command,
                session_id=args.session,
                cwd=args.cwd,
                timeout=args.timeout,
            )
            print(f"Command: {result['commandId']} [{result['status']}]")
            return (
                0
                if result["exitCode"] == 0
                else 124 if result["timedOut"] else int(result["exitCode"] or 1)
            )
        if args.codex_action == "retry":
            results = service.retry(args.session)
            for result in results:
                print(f"{result['captureSessionId']}: {result['state']}")
            return 0 if all(item["state"] == "SAVED" for item in results) else 1
        if args.codex_action == "add-note":
            service.add_note(args.message, args.type, args.session)
            print("Note added.")
            return 0
        if args.codex_action == "doctor":
            checks = service.doctor()
            for check in checks:
                print(f"[{check['status']}] {check['name']}: {check['detail']}")
            return 1 if any(item["status"] == "ERROR" for item in checks) else 0
        print(
            "Use mde codex register|list|start|stop|status|finalize|run|retry|doctor."
        )
        return 2
    except CodexCaptureError as error:
        print(f"{error.code}: {error}")
        return 1
