# MDE Phase 7 - AI Engine

Phase 7 adds a provider-neutral AI Engine and connects it to runtime workflows.

## Runtime commands

- `ai.generate`: creates an immutable artifact bundle under `.mde/artifacts/`
- `change.review`: records an AI review and preserves the source manifest
- `ai.fix`: creates a corrected artifact bundle
- `change.apply`: validates paths, backs up existing targets, and applies generated files
- `docs.generate`: uses the same provider boundary for documentation workflows

## Providers

The built-in `mock` provider is deterministic and requires no network credentials. External providers can implement `AIProvider.execute(AIRequest) -> AIResponse` and register with `AIProviderRegistry`.

List providers:

```powershell
uv run mde ai list
```

## Mobile task example

```yaml
version: 1
task:
  id: TASK-AI-001
  type: feature
  title: Create generated file
  description: Create a text file through the AI workflow
  workflow: feature
  execution:
    auto_apply: true
    run_tests: true
    auto_save: true
    auto_push: true
  inputs:
    ai:
      provider: mock
      artifacts:
        - path: generated/example.txt
          content: generated from a mobile task
```

Generated content is staged under `.mde/artifacts` before it is applied. Existing target files are backed up under `.mde/backups`.
