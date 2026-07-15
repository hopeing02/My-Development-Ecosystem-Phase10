# Phase 10 Operations Stability

Phase 10 adds task-specific branches, atomic task locks, persistent checkpoints,
failed-task retry, checkpoint-aware workflow resume, and a mobile-readable status summary.

## Commands

```bash
mde task retry TASK-ID
mde task checkpoint TASK-ID
mde task summary
mde sync run --task-branches
mde agent --once
```

The Agent enables task branches by default. A task may specify `repository.branch`
and `repository.base_branch`; otherwise MDE derives a safe branch such as
`feature/task-001`.

Checkpoints are stored under `.mde/checkpoints/`. Status summaries are written to
`status/mobile-summary.json`.
