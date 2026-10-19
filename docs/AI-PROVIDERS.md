# MDE AI Providers

Available providers: `mock`, `codex`, `openai`, `claude`, `gemini`, and `local`.

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

### Existing Codex CLI

Install and log in to Codex CLI beforehand (`codex login status`). Select
`inputs.ai.provider: "codex"` or `MDE_AI_PROVIDER=codex`. Existing CLI authentication
and configured default model are reused. No API key is required when using CLI ChatGPT login.
Optional environment settings:

- `MDE_CODEX_EXECUTABLE`: executable path/name (default `codex`).
- `MDE_CODEX_TIMEOUT`: per-call seconds, default 180, range (0, 1800].
- `MDE_CODEX_MODEL`: explicit CLI model override; omit to retain CLI default.

The adapter uses `codex -a never exec --sandbox read-only --ephemeral`, a stdin prompt,
`--output-schema` and `--output-last-message`. Codex proposes full artifact contents;
MDE performs review/application/testing/commit/deployment. No shell command concatenation,
automatic provider fallback, or automatic retry is used. Errors and timeout stop the step.
Timeout terminates that CLI process and its children. Raw CLI diagnostics are not echoed.
The existing CLI user configuration remains active; the adapter is not an isolated account/runtime.

Specify `inputs.ai.context_files` as repository-relative UTF-8 paths (up to 20 files,
64KiB each, 256KiB total). These current contents are supplied on each call, including
after a failed test. Only explicitly selected files are read; do not select secrets.
For fix calls, actual failed test log contents (last 64KiB) are also supplied.
Generated contents are supplied separately for review. Other providers reuse this context contract.

For a local FastAPI workflow, put the following JSON outside the target repository or
under its ignored `.mde` directory. Replace the interpreter path and test command for the project.

```json
{
  "ai": {"provider": "codex", "context_files": ["service.py", "test_service.py"]},
  "testing_command": ["C:/path/to/venv/Scripts/python.exe", "-m", "pytest", "-q"],
  "deployment": {"app": "service:app", "health_path": "/health"},
  "push": false
}
```

```powershell
uv run mde workflow run feature-local --runtime --inputs .mde/inputs.json --max-fix-attempts 1 --message "Describe the requested change"
```

Run from the target Git repository, with dependencies prepared and the initial worktree clean.
`push: true` requires a configured authenticated Git remote. The existing GitPlugin pushes
using Git credentials; a connected GitHub app does not automatically authenticate shell Git.
Default mock behavior, default feature Workflow and Task Git policy are unchanged.

Official execution contract: [OpenAI non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

### Artifact JSON

Providers must return JSON with a non-empty `summary` and an `artifacts` array. Each artifact requires a relative `path` and string `content`. Unsafe paths are rejected before files are written or applied.

For `review`, providers must also return an explicit JSON boolean `approved`. Missing,
null, string, and numeric verdicts are rejected. `approved: false` stops the workflow
before applying changes. The generated artifact contents are supplied in the review
context and included in HTTP provider prompts. Mock review explicitly approves only
for deterministic testing; it is not a real AI review.

## Reliability and usage

`MDE_AI_TIMEOUT` controls request timeout. `MDE_AI_MAX_RETRIES` controls exponential retries for transport failures. Manifest metadata records model, normalized token usage, attempt count, and optional estimated cost.
