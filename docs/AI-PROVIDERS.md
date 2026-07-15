# MDE AI Providers

Phase 8 provides `mock`, `openai`, `claude`, `gemini`, and `local` providers.

## Configuration

Copy `.env.ai.example` values into your shell or secret manager. MDE does not load `.env` files automatically and never stores API keys in task YAML files.

Provider selection order:

1. Workflow step `args.provider`
2. Task `inputs.ai.provider`
3. `MDE_AI_PROVIDER`
4. `mock`

## PowerShell examples

```powershell
$env:MDE_AI_PROVIDER = "openai"
$env:OPENAI_API_KEY = "..."
$env:MDE_OPENAI_MODEL = "gpt-5-mini"
uv run mde workflow run feature --runtime --message "Create the requested feature"
```

```powershell
$env:MDE_AI_PROVIDER = "claude"
$env:ANTHROPIC_API_KEY = "..."
$env:MDE_CLAUDE_MODEL = "claude-sonnet-4-6"
```

```powershell
$env:MDE_AI_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "..."
$env:MDE_GEMINI_MODEL = "gemini-2.5-flash"
```

```powershell
$env:MDE_AI_PROVIDER = "local"
$env:MDE_LOCAL_BASE_URL = "http://127.0.0.1:11434/v1/chat/completions"
$env:MDE_LOCAL_MODEL = "your-model"
```

## Response contract

Providers must return JSON with a non-empty `summary` and an `artifacts` array. Each artifact requires a relative `path` and string `content`. Unsafe paths are rejected before files are written or applied.

## Reliability and usage

`MDE_AI_TIMEOUT` controls request timeout. `MDE_AI_MAX_RETRIES` controls exponential retries for transport failures. Manifest metadata records model, normalized token usage, attempt count, and optional estimated cost.
