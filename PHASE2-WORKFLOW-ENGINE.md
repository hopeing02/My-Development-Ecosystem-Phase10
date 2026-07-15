# MDE Phase 2 - YAML Workflow Engine

## Implemented

- Workflow models and execution context
- YAML loader with project-level override support
- Structural validator
- Command registry using Python handlers
- Sequential executor with dependencies, retry, conditions, skip, and fail-fast behavior
- Bundled `feature`, `bugfix`, `docs`, and `refactor` workflows
- CLI commands:
  - `mde workflow list`
  - `mde workflow show <name>`
  - `mde workflow run <name> --message <text> --task <id>`
- PyYAML dependency and packaged workflow resources

## Safety boundary

The default handlers record execution state only. They do not automatically edit files, run Git commits, push, or call an AI provider. Phase 3 can replace these handlers through the command registry and future plugin system.

## Verification

```powershell
uv sync
uv run pytest
uv run mde workflow list
uv run mde workflow show feature
uv run mde workflow run docs --message "README update"
```

Expected test result: `49 passed`.
