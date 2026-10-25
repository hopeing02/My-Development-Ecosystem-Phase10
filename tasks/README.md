# MDE Task Queue

- `pending`: tasks submitted from mobile/GitHub and waiting for execution
- `processing`: tasks claimed by the PC Agent
- `completed`: successfully completed task YAML and result YAML files
- `failed`: failed or recovered task YAML and result YAML files

Task files use the Phase 3 YAML schema implemented by `mde.task.loader`.

`pending/DOC-PARSER-1.json` is a DevelopmentTask request for the independent W1 runner,
not a Phase 3 YAML queue item. Run it explicitly from the repository root with
`python tools/automation/run_codex_single_task.py --request tasks/pending/DOC-PARSER-1.json --result .mde/codex-development/DOC-PARSER-1-result.json`.
The read-only specification lives in `docs/15_projects/document-parser/steps/`;
the verified human report is written to `results/` only after external validation.
Workflow/task_runner integration and automatic JSON-to-Markdown generation remain W2 work.
