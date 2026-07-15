# Phase 5 - Agent Integration

`mde agent --once` now runs the Phase 4 Mobile Sync Engine under a single-agent lock.

Flow:

1. write running heartbeat
2. acquire `.mde/agent.lock`
3. fetch and fast-forward pull
4. recover interrupted processing tasks
5. execute pending YAML tasks through Workflow Engine
6. commit result files
7. push current branch
8. write completed or failed heartbeat
9. release lock

Commands:

```powershell
uv run mde agent --once
uv run mde agent --once --no-push
uv run mde agent --watch --interval 30
```

Status file: `status/agent-heartbeat.json`
Logs: `logs/agent-*.log`
