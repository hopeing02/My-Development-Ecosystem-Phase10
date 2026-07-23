from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# from tools import create_project
from mde.agent.runner import run_once, run_watch
from mde.ai.errors import AIConfigurationError
from mde.ai.engine import create_default_provider_registry
from mde.commands.apply import apply_patch, apply_task

# from tools.mde_doctor import print_report, run_doctor
# from tools.mde_generate import generate_command
# from tools.mde_inbox import list_patches
# from tools.mde_new import AVAILABLE_TEMPLATES, create_project
from mde.commands.new import create_project
from mde.commands.save import save
from mde.documentation import (
    TARGET_NAMES,
    apply_update as apply_documentation_update,
    check_document,
    find_documentation_root,
    preview_update,
    target_path as documentation_target_path,
)
from mde.workflow.executor import WorkflowExecutionError, execute_workflow
from mde.workflow.loader import list_workflows, load_named_workflow
from mde.workflow.models import WorkflowContext
from mde.workflow.registry import create_default_registry
from mde.plugins.runtime import create_runtime_registry, create_runtime_plugin_manager
from mde.task.executor import execute_task
from mde.task.store import TaskStore
from mde.sync import SyncPolicy, run_mobile_sync
from mde.git import repository as git_repository
from mde.knowledge.cli import register_parser as register_knowledge_parser
from mde.knowledge.cli import run as run_knowledge_command

AVAILABLE_COMMANDS = [
    "new",
    "generate",
    "apply",
    "save",
    "agent",
    "workflow",
    "task",
    "sync",
    "plugin",
    "ai",
    "inbox",
    "knowledge",
    #    "doctor",
    "docs",
    "build",
    "release",
    "obsidian",
    "deploy",
]

IMPLEMENTED_COMMANDS = frozenset(
    {
        "new",
        "apply",
        "save",
        "agent",
        "workflow",
        "task",
        "sync",
        "plugin",
        "ai",
        "knowledge",
        "docs",
    }
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mde",
        description="My Development Ecosystem command line interface.",
    )

    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser(
        "new",
        help="Create a new MDE project.",
    )
    new_parser.add_argument(
        "project_name",
        help="Project name.",
    )
    new_parser.add_argument(
        "--template",
        default="shared",
        #        choices=sorted(AVAILABLE_TEMPLATES),
        help="Project template type.",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate MDE code artifacts.",
    )
    generate_subparsers = generate_parser.add_subparsers(dest="generate_target")

    generate_command_parser = generate_subparsers.add_parser(
        "command",
        help="Generate a command module and its test file.",
    )
    generate_command_parser.add_argument(
        "command_name",
        help="Command name.",
    )

    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply a patch file or task manifest.",
    )
    apply_parser.add_argument(
        "source",
        help="Patch file or manifest.yaml path.",
    )
    apply_parser.add_argument(
        "--target",
        help="Target file for a single patch.",
    )
    apply_parser.add_argument(
        "--no-test",
        action="store_true",
        help="Apply without running pytest.",
    )
    apply_parser.add_argument(
        "--remove-backup",
        action="store_true",
        help="Remove backup files after successful application.",
    )

    save_parser = subparsers.add_parser(
        "save",
        help="Format, test, commit, and optionally push changes.",
    )
    save_parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Git commit message.",
    )
    save_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit locally without pushing to GitHub.",
    )

    agent_parser = subparsers.add_parser(
        "agent",
        help="Run the MDE mobile automation agent.",
    )

    agent_mode_group = agent_parser.add_mutually_exclusive_group()

    agent_mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run one Agent cycle and exit.",
    )
    agent_mode_group.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor GitHub and process tasks.",
    )

    agent_parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Watch interval in seconds. Minimum: 5.",
    )
    agent_parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Compatibility flag: commit completed task results.",
    )
    agent_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit completed task results without pushing.",
    )
    agent_parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty working tree. Not recommended for automation.",
    )

    workflow_parser = subparsers.add_parser(
        "workflow",
        help="Inspect and run YAML workflows.",
    )
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_action")
    workflow_subparsers.add_parser("list", help="List available workflows.")

    workflow_show_parser = workflow_subparsers.add_parser(
        "show", help="Show a workflow definition."
    )
    workflow_show_parser.add_argument("workflow_name", help="Workflow name.")

    workflow_run_parser = workflow_subparsers.add_parser(
        "run", help="Run a workflow using the registered Python handlers."
    )
    workflow_run_parser.add_argument("workflow_name", help="Workflow name.")
    workflow_run_parser.add_argument(
        "--message", default="", help="Message made available through WorkflowContext."
    )
    workflow_run_parser.add_argument(
        "--task", dest="task_id", help="Optional task ID for the workflow context."
    )
    workflow_run_parser.add_argument(
        "--runtime",
        action="store_true",
        help="Use real test and Git plugins. Without this flag, workflow run is a safe dry run.",
    )

    task_parser = subparsers.add_parser(
        "task",
        help="Inspect and execute YAML tasks.",
    )
    task_subparsers = task_parser.add_subparsers(dest="task_action")
    task_list_parser = task_subparsers.add_parser("list", help="List tasks by status.")
    task_list_parser.add_argument(
        "--status",
        choices=("pending", "processing", "completed", "failed"),
        default="pending",
        help="Task status to list.",
    )
    task_show_parser = task_subparsers.add_parser("show", help="Show a task.")
    task_show_parser.add_argument("task_id", help="Task ID.")
    task_run_parser = task_subparsers.add_parser(
        "run", help="Claim and execute a pending task."
    )
    task_run_parser.add_argument("task_id", help="Task ID.")
    task_retry_parser = task_subparsers.add_parser(
        "retry", help="Move a failed task back to pending and resume it."
    )
    task_retry_parser.add_argument("task_id", help="Task ID.")
    task_checkpoint_parser = task_subparsers.add_parser(
        "checkpoint", help="Show a task checkpoint."
    )
    task_checkpoint_parser.add_argument("task_id", help="Task ID.")
    task_subparsers.add_parser(
        "summary", help="Write and show the mobile status summary."
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="Synchronize mobile tasks through GitHub.",
    )
    sync_subparsers = sync_parser.add_subparsers(dest="sync_action")
    sync_subparsers.add_parser("status", help="Show local and remote sync state.")
    sync_subparsers.add_parser(
        "pull", help="Fetch and fast-forward pull remote changes."
    )
    sync_run_parser = sync_subparsers.add_parser(
        "run", help="Pull, execute pending tasks, commit, and optionally push."
    )
    sync_run_parser.add_argument("--no-commit", action="store_true")
    sync_run_parser.add_argument("--no-push", action="store_true")
    sync_run_parser.add_argument("--allow-dirty", action="store_true")
    sync_run_parser.add_argument("--remote", default="origin")
    sync_run_parser.add_argument("--branch")
    sync_run_parser.add_argument(
        "--task-branches", action="store_true", help="Run each task on its own branch."
    )

    ai_parser = subparsers.add_parser(
        "ai",
        help="Inspect configured AI providers.",
    )
    ai_subparsers = ai_parser.add_subparsers(dest="ai_action")
    ai_subparsers.add_parser("list", help="List built-in AI providers.")
    ai_check_parser = ai_subparsers.add_parser(
        "check",
        help="Validate AI provider environment variables.",
    )
    ai_check_parser.add_argument(
        "--provider",
        help="Provider to validate. Defaults to MDE_AI_PROVIDER or mock.",
    )

    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Inspect installed workflow plugins.",
    )
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_action")
    plugin_subparsers.add_parser("list", help="List built-in runtime plugins.")

    inbox_parser = subparsers.add_parser(
        "inbox",
        help="Manage legacy inbox patch files.",
    )
    inbox_subparsers = inbox_parser.add_subparsers(dest="inbox_action")
    inbox_subparsers.add_parser(
        "list",
        help="List legacy inbox patches.",
    )

    register_knowledge_parser(subparsers)

    docs_parser = subparsers.add_parser(
        "docs",
        help="Check and safely update managed MDE documentation.",
    )
    docs_subparsers = docs_parser.add_subparsers(dest="docs_action")
    docs_check_parser = docs_subparsers.add_parser(
        "check", help="Check managed documentation against the live CLI."
    )
    docs_check_parser.add_argument(
        "--target", choices=TARGET_NAMES, default="mde-user-guide"
    )
    docs_update_parser = docs_subparsers.add_parser(
        "update", help="Preview or apply a managed documentation update."
    )
    docs_update_parser.add_argument(
        "--target", choices=TARGET_NAMES, default="mde-user-guide"
    )
    docs_update_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the generated change. Without this flag only a diff is shown.",
    )

    #    subparsers.add_parser(
    #        "doctor",
    #        help="Check the MDE development environment.",
    #    )

    for command in AVAILABLE_COMMANDS:
        if command in subparsers.choices:
            continue

        subparsers.add_parser(
            command,
            help=f"Reserved command: {command}",
        )

    return parser


def run_reserved_command(command: str) -> int:
    print(f"'{command}' command is reserved but not implemented yet.")
    return 2


def run_docs_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.docs_action not in {"check", "update"}:
        print("Use docs check or docs update [--apply].")
        return 2

    root = find_documentation_root()
    path = documentation_target_path(root, args.target)
    if args.docs_action == "check":
        if check_document(path, parser, IMPLEMENTED_COMMANDS, args.target):
            print(f"MDE documentation is up to date: {path}")
            return 0
        print(f"MDE documentation is out of date: {path}")
        print("Run: uv run mde docs update --apply")
        return 1

    expected, diff = preview_update(path, parser, IMPLEMENTED_COMMANDS, args.target)
    if not diff:
        print(f"MDE documentation is already up to date: {path}")
        return 0
    if not args.apply:
        print(diff, end="")
        print("Preview only. Re-run with --apply to update the managed section.")
        return 0
    apply_documentation_update(path, expected)
    print(f"MDE documentation updated: {path}")
    print("Only the managed CLI reference section was changed.")
    return 0


def run_apply_command(args: argparse.Namespace) -> int:
    source_path = Path(args.source)
    run_tests = not args.no_test
    keep_backups = not args.remove_backup

    if source_path.name == "manifest.yaml":
        result = apply_task(
            manifest_path=source_path,
            project_root=Path.cwd(),
            run_tests=run_tests,
            keep_backups=keep_backups,
        )

        print("Task applied.")
        print(f"Files applied: {len(result.results)}")

        for item in result.results:
            print(f"{item.patch_path} -> {item.target_path}")

        return 0

    if not args.target:
        print("--target is required for a single patch.")
        return 1

    result = apply_patch(
        patch_path=source_path,
        target_path=Path(args.target),
        run_tests=run_tests,
        keep_backup=keep_backups,
    )

    print("Patch applied.")
    print(f"Patch: {result.patch_path}")
    print(f"Target: {result.target_path}")
    print(f"Backup: {result.backup_path}")

    return 0


def run_workflow_command(args: argparse.Namespace) -> int:
    if args.workflow_action == "list":
        workflows = list_workflows(Path.cwd())
        for workflow in workflows:
            print(f"{workflow.name}: {workflow.description}")
        return 0

    if args.workflow_action == "show":
        workflow = load_named_workflow(args.workflow_name, Path.cwd())
        print(f"Name: {workflow.name}")
        print(f"Version: {workflow.version}")
        print(f"Description: {workflow.description}")
        print(f"Source: {workflow.source_path}")
        print("Steps:")
        for step in workflow.steps:
            dependencies = ", ".join(step.depends_on) or "-"
            print(f"  {step.id}: {step.command} (depends_on: {dependencies})")
        return 0

    if args.workflow_action == "run":
        workflow = load_named_workflow(args.workflow_name, Path.cwd())
        context = WorkflowContext(
            workflow_name=workflow.name,
            message=args.message,
            repository_root=Path.cwd(),
            task_id=args.task_id,
        )
        registry = (
            create_runtime_registry() if args.runtime else create_default_registry()
        )
        result = execute_workflow(workflow, context, registry)
        print(f"Workflow completed: {result.workflow_name}")
        for step in result.steps:
            print(f"[{step.status}] {step.step_id}: {step.command}")
        return 0

    print("Use workflow list, workflow show NAME, or workflow run NAME.")
    return 2


def run_task_command(args: argparse.Namespace) -> int:
    store = TaskStore(Path.cwd())

    if args.task_action == "list":
        tasks = store.list(args.status)
        for task in tasks:
            print(f"{task.task_id}: {task.title} [{task.workflow}]")
        return 0

    if args.task_action == "show":
        found = store.find(args.task_id)
        if found is None:
            print(f"Task not found: {args.task_id}")
            return 1
        status, path = found
        from mde.task.loader import load_task

        task = load_task(path)
        print(f"ID: {task.task_id}")
        print(f"Status: {status}")
        print(f"Type: {task.task_type}")
        print(f"Title: {task.title}")
        print(f"Workflow: {task.workflow}")
        print(f"Source: {task.source}")
        print(f"Path: {path}")
        return 0

    if args.task_action == "retry":
        destination = store.retry(args.task_id)
        print(f"Task moved to pending: {args.task_id}")
        print(f"Path: {destination}")
        return 0

    if args.task_action == "checkpoint":
        from mde.task.checkpoint import CheckpointStore

        checkpoint = CheckpointStore(Path.cwd()).load(args.task_id)
        if checkpoint is None:
            print(f"Checkpoint not found: {args.task_id}")
            return 1
        print(f"Task: {checkpoint.task_id}")
        print(f"Status: {checkpoint.status}")
        print(f"Last successful step: {checkpoint.last_successful_step or '-'}")
        print(f"Completed steps: {', '.join(checkpoint.completed_steps) or '-'}")
        if checkpoint.error:
            print(f"Error: {checkpoint.error}")
        return 0

    if args.task_action == "summary":
        from mde.task.summary import write_mobile_summary

        path = write_mobile_summary(Path.cwd())
        print(path.read_text(encoding="utf-8"), end="")
        return 0

    if args.task_action == "run":
        found = store.find(args.task_id)
        if found is None:
            print(f"Task not found: {args.task_id}")
            return 1
        status, path = found
        if status != "pending":
            print(f"Task is not pending: {args.task_id} ({status})")
            return 2
        from mde.task.loader import load_task

        result = execute_task(load_task(path), Path.cwd(), store=store)
        print(f"Task {result.status}: {result.task_id}")
        print(f"Workflow: {result.workflow}")
        print(f"Result: {result.result_path}")
        if result.error:
            print(f"Error: {result.error}")
            return 1
        return 0

    print(
        "Use task list, task show ID, task run ID, task retry ID, task checkpoint ID, or task summary."
    )
    return 2


def run_ai_command(args: argparse.Namespace) -> int:
    if args.ai_action == "list":
        for name in create_default_provider_registry().names():
            print(name)
        return 0
    if args.ai_action == "check":
        registry = create_default_provider_registry()
        provider_name = args.provider or os.environ.get("MDE_AI_PROVIDER", "mock")
        provider = registry.get(provider_name)
        name = provider.name
        if name == "mock":
            print("AI provider ready: mock")
            return 0
        if name == "local":
            base_url = os.environ.get(
                "MDE_LOCAL_BASE_URL", "http://127.0.0.1:11434/v1/chat/completions"
            )
            if not base_url.startswith(("http://", "https://")):
                raise AIConfigurationError("MDE_LOCAL_BASE_URL must be an HTTP(S) URL.")
            model = os.environ.get("MDE_LOCAL_MODEL", "local-model")
            print("AI provider ready: local")
            print(f"Model: {model}")
            print(f"Base URL: {base_url}")
            return 0
        api_key_env = getattr(provider, "api_key_env", "")
        model_env = getattr(provider, "model_env", "")
        default_model = getattr(provider, "default_model", "")
        api_key = os.environ.get(api_key_env, "").strip()
        if not api_key:
            raise AIConfigurationError(
                f"Missing API key environment variable: {api_key_env}"
            )
        model = os.environ.get(model_env, default_model)
        print(f"AI provider ready: {name}")
        print(f"Model: {model}")
        print(f"API key env: {api_key_env}")
        return 0
    print("Use ai list or ai check.")
    return 2


def run_plugin_command(args: argparse.Namespace) -> int:
    if args.plugin_action == "list":
        manager = create_runtime_plugin_manager()
        for name in manager.names():
            print(name)
        return 0
    print("Use plugin list.")
    return 2


def run_sync_command(args: argparse.Namespace) -> int:
    root = Path.cwd()
    if args.sync_action == "status":
        branch = git_repository.current_branch(root)
        git_repository.fetch(repository_root=root)
        state = git_repository.get_git_state(
            branch, repository_root=root, fetch_first=False
        )
        print(f"Branch: {state.branch}")
        print(f"Local: {state.local_head}")
        print(f"Remote: {state.remote_head}")
        print(f"Remote changed: {state.local_head != state.remote_head}")
        return 0

    if args.sync_action == "pull":
        git_repository.ensure_clean_worktree(root)
        branch = git_repository.current_branch(root)
        git_repository.fetch(repository_root=root)
        if git_repository.has_remote_changes(
            branch, repository_root=root, fetch_first=False
        ):
            git_repository.pull_fast_forward(branch=branch, repository_root=root)
            print("Remote changes pulled.")
        else:
            print("No remote changes.")
        return 0

    if args.sync_action == "run":
        result = run_mobile_sync(
            root,
            policy=SyncPolicy(
                remote=args.remote,
                branch=args.branch,
                auto_commit=not args.no_commit,
                auto_push=not args.no_push,
                allow_dirty_worktree=args.allow_dirty,
                task_branches=args.task_branches,
            ),
        )
        print(f"Remote changed: {result.remote_changed}")
        print(f"Pulled: {result.pulled}")
        print(f"Recovered: {result.recovered_count}")
        print(f"Completed: {len(result.completed_tasks)}")
        print(f"Failed: {len(result.failed_tasks)}")
        print(f"Commit: {result.commit_hash or '-'}")
        print(f"Pushed: {result.pushed}")
        return 0

    print("Use sync status, sync pull, or sync run.")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "new":
            if args.template != "shared":
                print("Only the shared template is available in Phase 1.")
                return 2

            created_paths = create_project(args.project_name)
            print("Project created.")
            for path in created_paths:
                print(path)
            return 0

        #        if args.command == "generate":
        #            if args.generate_target != "command":
        #                parser.print_help()
        #                return 1

        #            plan = generate_command(args.command_name)

        #            print("Command generated.")
        #            print(f"Tool path: {plan.tool_path}")
        #            print(f"Test path: {plan.test_path}")

        #            return 0

        if args.command == "apply":
            return run_apply_command(args)

        if args.command == "save":
            save(
                commit_message=args.message,
                push=not args.no_push,
            )
            print("MDE save completed.")
            return 0

        if args.command == "workflow":
            return run_workflow_command(args)

        if args.command == "task":
            return run_task_command(args)

        if args.command == "sync":
            return run_sync_command(args)
        if args.command == "plugin":
            return run_plugin_command(args)
        if args.command == "ai":
            return run_ai_command(args)
        if args.command == "knowledge":
            return run_knowledge_command(args)
        if args.command == "docs":
            return run_docs_command(args, parser)

        if args.command == "agent":
            if args.once:
                run_once(
                    auto_save=args.auto_save,
                    auto_push=not args.no_push,
                    allow_dirty_worktree=args.allow_dirty,
                )
                return 0

            if args.watch:
                run_watch(
                    interval_seconds=args.interval,
                    auto_save=args.auto_save,
                    auto_push=not args.no_push,
                )
                return 0

            print("Use --once or --watch.")
            return 2

        #        if args.command == "inbox":
        #            if args.inbox_action != "list":
        #                parser.print_help()
        #                return 1

        #            patches = list_patches()

        #            if not patches:
        #                print("No legacy inbox patches.")
        #                return 0

        #            for patch in patches:
        #                print(f"{patch.patch_path} -> {patch.target_path}")

        #            return 0

        #        if args.command == "doctor":
        #            results = run_doctor()
        #           print_report(results)

        #            if any(not result.passed for result in results):
        #                return 1

        #            return 0

        if args.command in AVAILABLE_COMMANDS:
            return run_reserved_command(args.command)

        parser.print_help()
        return 1

    except WorkflowExecutionError as error:
        print(error)
        return 1
    except RuntimeError as error:
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
