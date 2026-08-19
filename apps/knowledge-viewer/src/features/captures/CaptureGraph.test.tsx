import { render } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CaptureGraph } from "./CaptureGraph";

const cytoscapeState = vi.hoisted(() => ({
  selectors: [] as string[],
  handlers: {} as Record<string, (event: { target: { id: () => string; data: (key: string) => unknown } }) => void>,
}));

vi.mock("cytoscape", () => ({
  default: vi.fn(({ container, style }: { container: HTMLElement; style: Array<{ selector: string }> }) => {
    cytoscapeState.selectors = style.map((item) => item.selector);
    container.append(document.createElement("canvas"));
    return {
      destroy: () => container.replaceChildren(),
      on: vi.fn((_event: string, selector: string, handler: (event: { target: { id: () => string; data: (key: string) => unknown } }) => void) => {
        cytoscapeState.handlers[selector] = handler;
      }),
    };
  }),
}));

test("uses a Cytoscape truthy selector for candidate relations", () => {
  render(
    <CaptureGraph
      graph={{
        depth: 2,
        limit: 300,
        truncated: false,
        nodes: [
          { id: "clip", type: "CLIPBOARD_CAPTURE", label: "Android 단편", metadata: {} },
          { id: "session", type: "DEVELOPMENT_SESSION", label: "Windows 세션", metadata: {} },
        ],
        edges: [
          { id: "relation", from: "clip", to: "session", type: "excerpt_of", status: "suggested" },
        ],
      }}
      onOpenCapture={vi.fn()}
      onOpenTask={vi.fn()}
    />,
  );

  expect(cytoscapeState.selectors).toContain("edge[?candidate]");
  expect(cytoscapeState.selectors).not.toContain("edge[candidate = true]");
});

test("shows an explicit state when a session has no graph relations", () => {
  const { getByText } = render(
    <CaptureGraph
      graph={{
        depth: 1,
        limit: 300,
        truncated: false,
        nodes: [
          { id: "session", type: "DEVELOPMENT_SESSION", label: "빈 세션", metadata: {} },
        ],
        edges: [],
      }}
      onOpenCapture={vi.fn()}
      onOpenTask={vi.fn()}
    />,
  );

  expect(getByText("이 세션에 연결된 그래프 관계가 없습니다.")).toBeInTheDocument();
});

test("opens a Task node without replacing existing capture node behavior", () => {
  const onOpenCapture = vi.fn();
  const onOpenTask = vi.fn();
  render(
    <CaptureGraph
      graph={{
        depth: 1,
        limit: 300,
        truncated: false,
        nodes: [
          { id: "session", type: "DEVELOPMENT_SESSION", label: "세션", metadata: {} },
          { id: "task:session:session", type: "TASK", label: "관련 Task", metadata: {} },
        ],
        edges: [
          { id: "contains", from: "session", to: "task:session:session", type: "contains_task", status: "confirmed" },
        ],
      }}
      onOpenCapture={onOpenCapture}
      onOpenTask={onOpenTask}
    />,
  );

  cytoscapeState.handlers.node({
    target: {
      id: () => "task:session:session",
      data: (key) => key === "type" ? "TASK" : "관련 Task",
    },
  });

  expect(onOpenTask).toHaveBeenCalledWith("task:session:session");
  expect(onOpenCapture).not.toHaveBeenCalled();
});

test("opens ChatGPT Task and Activity nodes through their source session", () => {
  const onOpenTask = vi.fn();
  const onOpenChatGPTSession = vi.fn();
  render(
    <CaptureGraph
      graph={{
        depth: 1,
        limit: 300,
        truncated: false,
        nodes: [
          { id: "task:chatgpt:1", type: "TASK", label: "ChatGPT Task", metadata: { sessionId: "chatgpt-1" } },
          { id: "activity:chatgpt:1", type: "ACTIVITY", label: "request #1", metadata: { sessionId: "chatgpt-1" } },
        ],
        edges: [
          { id: "contains", from: "task:chatgpt:1", to: "activity:chatgpt:1", type: "contains_activity", status: "confirmed" },
        ],
      }}
      onOpenCapture={vi.fn()}
      onOpenTask={onOpenTask}
      onOpenChatGPTSession={onOpenChatGPTSession}
    />,
  );

  for (const type of ["TASK", "ACTIVITY"]) {
    cytoscapeState.handlers.node({
      target: {
        id: () => type.toLowerCase(),
        data: (key) => ({ type, sessionId: "chatgpt-1", label: type } as Record<string, string>)[key],
      },
    });
  }

  expect(onOpenChatGPTSession).toHaveBeenCalledTimes(2);
  expect(onOpenChatGPTSession).toHaveBeenCalledWith("chatgpt-1");
  expect(onOpenTask).not.toHaveBeenCalled();
});
