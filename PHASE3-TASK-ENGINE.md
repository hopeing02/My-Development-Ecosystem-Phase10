# Phase 3 — Task Engine

Phase 3 adds a persistent YAML task queue connected to the Phase 2 Workflow Engine.

## Commands

```powershell
uv run mde task list --status pending
uv run mde task show TASK-001
uv run mde task run TASK-001
```

## State flow

`pending -> processing -> completed | failed`

Task results are written as `<TASK-ID>.result.yaml` beside the final task file.
The legacy `inbox/tasks` patch queue remains unchanged for backward compatibility.
