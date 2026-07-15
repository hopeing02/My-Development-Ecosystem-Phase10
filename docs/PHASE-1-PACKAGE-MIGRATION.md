# Phase 1 — mde-core package migration

## Result

- Runtime modules now live under `packages/mde-core/src/mde`.
- `mde` CLI entry point is `mde.cli:main`.
- Existing `tools/mde_*.py` paths remain as compatibility wrappers.
- The old `packages/mde-foundation` package remains untouched for rollback/reference.

## Module map

| Legacy | Package |
|---|---|
| `tools/mde_new.py` | `mde.commands.new` |
| `tools/mde_apply.py` | `mde.commands.apply` |
| `tools/mde_save.py` | `mde.commands.save` |
| `tools/mde_agent.py` | `mde.agent.runner` |
| `tools/mde_git.py` | `mde.git.repository` |
| `tools/mde_lock.py` | `mde.agent.lock` |
| `tools/mde_log.py` | `mde.logging.logger` |
| `tools/mde_queue.py` | `mde.task.queue` |
| `tools/mde_task.py` | `mde.task.model` |

## Verification

```powershell
uv sync
uv run pytest
uv run mde --help
uv run mde agent --once
```
