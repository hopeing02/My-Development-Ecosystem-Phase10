"""Backward-compatible entry point for the packaged MDE CLI."""
from mde.cli import AVAILABLE_COMMANDS, build_parser, main, run_apply_command, run_reserved_command

__all__ = ["AVAILABLE_COMMANDS", "build_parser", "main", "run_apply_command", "run_reserved_command"]

if __name__ == "__main__":
    raise SystemExit(main())
