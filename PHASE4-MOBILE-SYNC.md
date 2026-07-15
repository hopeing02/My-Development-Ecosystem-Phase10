# Phase 4 - Mobile Sync Foundation

## Flow

Mobile ChatGPT -> GitHub task YAML -> PC `mde sync run`/Agent -> Workflow -> result YAML -> commit -> push -> mobile confirmation.

## Commands

```powershell
uv run mde sync status
uv run mde sync pull
uv run mde sync run
uv run mde sync run --no-push
```

## Safety rules

- Dirty worktrees are rejected by default.
- Pull uses `git pull --ff-only`.
- Detached HEAD is rejected.
- Force reset and force push are never used.
- Failed tasks stop commit and push.
- Save and push remain separate operations internally.

## Current boundary

Workflow handlers are still safe placeholder handlers. Phase 5 connects the Agent to the new Sync Engine and real test/save/push workflow policies.
