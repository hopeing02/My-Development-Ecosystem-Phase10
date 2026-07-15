from __future__ import annotations

import argparse
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "save.log"


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str = ""


class SaveError(RuntimeError):
    """Raised when the save workflow cannot complete safely."""


def configure_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mde.save")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def run_command(command: list[str]) -> CommandResult:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
    )


def run_required(
    command: list[str], logger: logging.Logger | None = None
) -> CommandResult:
    result = run_command(command)
    command_text = " ".join(command)

    if result.returncode != 0:
        if logger is not None:
            logger.error("FAILED: %s", command_text)
        raise SaveError(f"Command failed: {command_text}")

    if logger is not None:
        logger.info("PASSED: %s", command_text)

    return result


def get_current_branch(logger: logging.Logger | None = None) -> str:
    result = run_required(["git", "branch", "--show-current"], logger=logger)

    if not result.stdout:
        raise SaveError("Current Git branch could not be detected.")

    return result.stdout


def get_changed_files(logger: logging.Logger | None = None) -> list[str]:
    result = run_required(["git", "status", "--short"], logger=logger)

    if not result.stdout:
        return []

    return result.stdout.splitlines()


def ensure_has_changes(logger: logging.Logger | None = None) -> list[str]:
    changed_files = get_changed_files(logger=logger)

    if not changed_files:
        raise SaveError("No changes to save.")

    return changed_files


def save(commit_message: str, push: bool) -> None:
    logger = configure_logger()
    logger.info("MDE save started.")

    try:
        branch = get_current_branch(logger=logger)
        changed_files = ensure_has_changes(logger=logger)

        print(f"Current branch: {branch}")
        print(f"Changed files: {len(changed_files)}")

        logger.info("Current branch: %s", branch)
        logger.info("Changed files: %s", len(changed_files))

        run_required(["uv", "run", "black", "."], logger=logger)
        run_required(["uv", "run", "ruff", "check", "."], logger=logger)
        run_required(["uv", "run", "pytest"], logger=logger)

        run_required(["git", "add", "."], logger=logger)
        run_required(["git", "commit", "-m", commit_message], logger=logger)

        if push:
            print("Push: enabled")
            logger.info("Push: enabled")
            run_required(["git", "push"], logger=logger)
        else:
            print("Push: disabled")
            logger.info("Push: disabled")

        logger.info("MDE save completed.")

    except SaveError:
        logger.exception("MDE save failed.")
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MDE save workflow.")
    parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Git commit message.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Create commit without pushing to GitHub.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        save(commit_message=args.message, push=not args.no_push)
    except SaveError as error:
        print(error)
        return 1

    print("MDE save completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
