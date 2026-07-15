# Phase 9 - AI Automatic Fix Loop

## Flow

`generate -> review -> apply -> test`

When `test.run` fails and the task enables fix attempts:

`ai.fix -> change.apply -> test.run`

The repair cycle stops immediately when tests pass, or fails after the configured maximum.
Only failures from `test.run` enter the repair loop.

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
