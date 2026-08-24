# CODE-030 ChatGPT Task Workflow Viewer

## Scope

Extend the existing ChatGPT Session view without replacing the document, Capture, or graph interfaces.

## Implementation

- Read Task summaries from `GET /api/v1/chatgpt/tasks`.
- Read one Task and its Activities from `GET /api/v1/chatgpt/tasks/{taskId}`.
- Keep the original Session and Message projection as the source record.
- Render Task status, boundary status, confidence, message range, warnings, and Activity order.
- Label Task data as `source=derived`; original messages remain `source=original`.
- Open an Activity's referenced source message by scrolling to and highlighting the preserved message.
- Route ChatGPT Task and Activity graph nodes to the exact Session and Task.

## Compatibility

- Existing ChatGPT ZIP and Shared Link import controls are unchanged.
- Existing ChatGPT Session list and original message order are unchanged.
- Existing Capture graph callbacks remain available.
- Existing document navigation and generated MDE Viewer packaging remain unchanged.

## Files

- `apps/knowledge-viewer/src/features/chatgpt-import/types.ts`
- `apps/knowledge-viewer/src/features/chatgpt-import/api.ts`
- `apps/knowledge-viewer/src/features/chatgpt-import/ChatGPTImportPanel.tsx`
- `apps/knowledge-viewer/src/features/captures/CaptureGraph.tsx`
- `apps/knowledge-viewer/src/styles.css`

## Result

The Viewer now exposes Session -> Task -> Activity while retaining a direct link from every derived Activity to its original Message.
