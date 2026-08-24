# TEST-031 ChatGPT Task Workflow Viewer

## Date

2026-08-19

## Added coverage

- ChatGPT Task list and Task detail API paths
- Task status and Activity flow rendering
- Activity-to-original-Message navigation
- Task and Activity graph-node routing
- Existing ChatGPT Session and import behavior

## Verification

### Focused Viewer tests

- Command: `npm test -- --run src/features/chatgpt-import/ChatGPTImportPanel.test.tsx src/features/chatgpt-import/api.test.ts src/features/captures/CaptureGraph.test.tsx`
- Result: 13 passed

### Viewer regression

- Command: `npm test -- --run`
- Result: 39 passed

### AutoKnowledge-Lite regression

- Command: `$env:AUTOKNOWLEDGE_CONTROL_API_KEY=''; .venv/Scripts/python.exe -m pytest -q`
- Result: 214 passed, 1 skipped
- Note: the environment key was cleared only inside the test process so mutation endpoints use the test's unauthenticated configuration.

### MDE Knowledge regression

- Command: `.venv/Scripts/python.exe -m pytest packages/mde-core/tests/knowledge -q`
- Result: 68 passed

### Production build

- Command: `npm run build`
- Result: passed; Viewer assets generated in `packages/mde-core/src/mde/knowledge/viewer`.
