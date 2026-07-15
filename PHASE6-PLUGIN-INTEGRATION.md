# Phase 6 - Plugin and Integration Test Layer

Phase 6 introduces explicit runtime plugins for workflow command boundaries.

## Built-in plugins

- `core`: task, AI placeholder, change, documentation, refactor, and bugfix handlers
- `testing`: real subprocess-based `test.run` handler with persisted logs
- `git`: real `git.save` and `git.push` handlers

## Safety model

`mde workflow run` remains a dry run unless `--runtime` is supplied. Mobile Task execution uses the runtime registry, but Git save/push steps are deferred to Mobile Sync so completed task files and result manifests are included in the same commit.

## Commands

```powershell
uv run mde plugin list
uv run mde workflow run feature --runtime --message "runtime test"
uv run pytest
```

## Integration coverage

The test suite creates a temporary working repository and bare remote, commits through the Git plugin, pushes, and verifies the remote branch hash.
