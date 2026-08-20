import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { TimelineWorkspace } from "./TimelineWorkspace";

const api = vi.hoisted(() => ({ listCaptures: vi.fn(), getChatGPTTimeline: vi.fn() }));

vi.mock("../captures/api", () => ({ listCaptures: api.listCaptures }));
vi.mock("../chatgpt-import/api", () => ({ getChatGPTTimeline: api.getChatGPTTimeline }));

beforeEach(() => {
  api.listCaptures.mockResolvedValue({
    items: [{
      captureId: "codex-1",
      title: "Implement API",
      sourceType: "codex",
      captureType: "development_session",
      captureDevice: "windows",
      projectId: "autoknowledge-lite",
      capturedAt: "2026-08-19T01:00:00Z",
      status: "completed",
      testStatus: "passed",
      relationStatus: "none",
      changedFilesCount: 2,
      commandsCount: 1,
      relationCount: 0,
    }],
    hasMore: false,
    total: 1,
  });
  api.getChatGPTTimeline.mockResolvedValue({
    items: [{
      entityType: "TASK",
      entityId: "task-1",
      title: "Design API",
      timestamp: "2026-08-19T00:00:00Z",
      sessionId: "chatgpt-1",
      sessionTitle: "Architecture",
      taskId: "task-1",
      provenance: { source: "derived", derivedBy: "rule", sourceRefs: [] },
    }],
    total: 1,
    limit: 500,
    truncated: false,
    omittedWithoutTimestamp: 0,
  });
});

afterEach(cleanup);

test("merges ChatGPT and Codex events in timestamp order and opens their sources", async () => {
  const onOpenCapture = vi.fn();
  const onOpenChatGPT = vi.fn();
  render(<TimelineWorkspace onOpenCapture={onOpenCapture} onOpenChatGPT={onOpenChatGPT} />);

  const design = await screen.findByText("Design API");
  const implementation = screen.getByText("Implement API");
  expect(design.compareDocumentPosition(implementation) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

  fireEvent.click(design.closest("button")!);
  fireEvent.click(implementation.closest("button")!);

  expect(onOpenChatGPT).toHaveBeenCalledWith("chatgpt-1", "task-1", undefined);
  expect(onOpenCapture).toHaveBeenCalledWith("codex-1");
  expect(screen.getByText("ChatGPT TASK")).toBeInTheDocument();
  expect(screen.getByText("Codex Session")).toBeInTheDocument();
});
