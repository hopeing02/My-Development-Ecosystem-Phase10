# Phase 9 - AI Automatic Fix Loop

## Flow

`generate -> review -> apply -> test`

When `test.run` fails and the task enables fix attempts:

`ai.fix -> change.apply -> test.run`

The repair cycle stops immediately when tests pass, or fails after the configured maximum.
Only failures from `test.run` enter the repair loop.

After a successful retest, MDE resumes all remaining original workflow steps instead
of returning early. Completed generation/apply steps are not repeated. Existing
enabled/condition policies still apply. A later save, push, or other step failure
propagates as a workflow failure and does not restart AI repair. The original test
step's output and checkpoint are restored from the successful retest; synthetic
repair IDs do not replace the original workflow checkpoint.

Task execution retains its existing policy: Git steps may be disabled by the Task
engine and handled by its enclosing Sync cycle. This change does not enable them.

This mechanism does not implement a deployment adapter or validate real AI review
approval. Those remain separate requirements for autonomous development-to-deployment.

## Task configuration

```yaml
version: 1
task:
  id: TASK-FIX-001
  type: bugfix
  title: Repair failing tests
  description: Fix the implementation until the test suite passes.
  workflow: bugfix
  execution:
    auto_apply: true
    run_tests: true
    auto_save: true
    auto_push: true
  inputs:
    ai:
      provider: mock
      max_fix_attempts: 2
```

`max_fix_attempts: 0` disables the automatic repair loop. The loop is bounded and never retries indefinitely.

## Failure information supplied to AI

The `ai.fix` prompt includes:

- task description
- repair attempt number
- latest test failure message

Each fix and retest is recorded in the final Workflow and Task result.
