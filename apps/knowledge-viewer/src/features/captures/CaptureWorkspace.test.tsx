import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CaptureWorkspace } from "./CaptureWorkspace";

const api = vi.hoisted(() => ({
  listCaptures: vi.fn(), getCapture: vi.fn(), getCaptureItems: vi.fn(),
  getCaptureDiffs: vi.fn(), getCaptureGraph: vi.fn(), transitionRelation: vi.fn(),
  updateCapture: vi.fn(),
}));

vi.mock("./api", () => api);
vi.mock("cytoscape", () => ({
  default: vi.fn(({ container }: { container: HTMLElement }) => {
    container.append(document.createElement("canvas"));
    return { destroy: () => container.replaceChildren(), on: vi.fn() };
  }),
}));

const summary = {
  captureId: "cap_session", documentId: "doc_session", title: "Viewer 백링크 통합",
  sourceType: "codex", captureType: "development_session", captureDevice: "windows",
  projectId: "autoknowledge-lite", capturedAt: "2026-08-03T12:10:00+09:00",
  status: "completed", testStatus: "failed", relationStatus: "suggested",
  changedFilesCount: 8, commandsCount: 4, relationCount: 1,
};

const detail = {
  capture: summary,
  metadata: { captureId: "cap_session", documentPath: "40_Reference/session.md" },
  relations: [{
    relationId: "rel_1", relationType: "excerpt_of", fromCaptureId: "cap_clip",
    toCaptureId: "cap_session", status: "suggested", confidence: "medium", score: 80,
    matchMethod: "partial_content", direction: "in", targetTitle: "Android 단편",
    evidence: { matchRatio: .9, matchedMessageId: "msg_1" },
  }],
  relationCandidates: [], tags: [], summary: { request: "Viewer를 구현해", summary: "구현 완료" },
  messagesSummary: { count: 1 }, commandsSummary: { count: 1 }, changedFilesSummary: { count: 8 },
  testsSummary: { count: 1, status: "failed" }, attachmentsSummary: { count: 1 },
  tasks: [{
    taskId: "task:cap_session:session", sessionId: "cap_session", captureId: "cap_session",
    title: "Viewer를 구현해", summary: "구현 완료", status: "completed",
    boundaryStatus: "suggested", confidence: .5,
    messageRange: { startSequence: 1, endSequence: 1 },
    counts: { messages: 1, changedFiles: 8, commands: 1, tests: 1 },
    provenance: { source: "derived", derivedBy: "rule", sourceRefs: ["capture:cap_session"] },
  }],
};

const emptyDetail = {
  ...detail,
  capture: { ...summary, captureId: "cap_empty", title: "자료 없는 세션", changedFilesCount: 0, commandsCount: 0, testStatus: "none" },
  metadata: { captureId: "cap_empty", documentPath: "40_Reference/empty.md" },
  relations: [], relationCandidates: [],
  summary: {}, messagesSummary: { count: 0 }, commandsSummary: { count: 0 },
  changedFilesSummary: { count: 0 }, testsSummary: { count: 0, status: "none" },
  attachmentsSummary: { count: 0 }, tasks: [],
};

describe("CaptureWorkspace", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.clearAllMocks();
    api.listCaptures.mockResolvedValue({ items: [summary], total: 1, hasMore: false });
    api.getCapture.mockResolvedValue(detail);
    api.getCaptureItems.mockResolvedValue({ items: [], total: 0, hasMore: false });
    api.getCaptureDiffs.mockResolvedValue({ items: [], total: 0, previewLimitBytes: 500000 });
    api.getCaptureGraph.mockResolvedValue({ nodes: [], edges: [], depth: 2, limit: 300, truncated: false });
    api.transitionRelation.mockResolvedValue({ status: "confirmed" });
    api.updateCapture.mockResolvedValue(detail);
  });

  it("renders natural badges and applies source and test filters", async () => {
    render(<CaptureWorkspace />);
    expect(await screen.findByText("Codex 전체 작업")).toBeInTheDocument();
    expect(screen.getByText("Viewer 백링크 통합")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("출처"), { target: { value: "codex" } });
    fireEvent.change(screen.getByLabelText("테스트 상태"), { target: { value: "failed" } });

    await waitFor(() => expect(api.listCaptures).toHaveBeenLastCalledWith(expect.objectContaining({ sourceType: "codex", testStatus: "failed" })));
  });

  it("opens a session and lazy-loads a tab without replacing the overview", async () => {
    api.getCaptureItems.mockResolvedValueOnce({ items: [{ messageId: "msg_1", role: "assistant", content: "원본 공개 답변" }], total: 1, hasMore: false });
    render(<CaptureWorkspace />);
    fireEvent.click(await screen.findByLabelText("Codex 전체 작업, Viewer 백링크 통합"));
    expect(await screen.findByText("최초 요청")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "대화" }));
    expect(await screen.findByText("원본 공개 답변")).toBeInTheDocument();
    expect(api.getCaptureItems).toHaveBeenCalledWith("cap_session", "messages");
  });

  it("confirms a suggested relation and refreshes both list and detail", async () => {
    render(<CaptureWorkspace />);
    fireEvent.click(await screen.findByLabelText("Codex 전체 작업, Viewer 백링크 통합"));
    fireEvent.click(await screen.findByRole("tab", { name: "관련 단편" }));
    fireEvent.click(screen.getByRole("button", { name: "확정" }));

    await waitFor(() => expect(api.transitionRelation).toHaveBeenCalledWith("rel_1", "confirm"));
    expect(api.getCapture).toHaveBeenCalledTimes(2);
    expect(api.listCaptures.mock.calls.length).toBeGreaterThan(1);
  });

  it("renders populated conversation, file, command and test tabs with Task backlinks", async () => {
    api.getCaptureItems.mockImplementation((_captureId: string, collection: string) => Promise.resolve({
      items: ({
        messages: [{ messageId: "msg_1", role: "assistant", content: "실제 원본 대화", taskId: "task:cap_session:session" }],
        "changed-files": [{ path: "src/session.py", changeType: "modified", addedLines: 4, deletedLines: 1, taskId: "task:cap_session:session" }],
        commands: [{ commandId: "cmd_1", command: "uv run pytest", exitCode: 0, status: "PASSED", stdout: "125 passed", taskId: "task:cap_session:session" }],
        tests: [{ testId: "test_1", framework: "pytest", status: "PASSED", passed: 125, failed: 0, exitCode: 0, taskId: "task:cap_session:session" }],
      } as Record<string, Record<string, unknown>[]>)[collection] ?? [],
      total: 1, hasMore: false,
    }));
    render(<CaptureWorkspace />);
    fireEvent.click(await screen.findByLabelText("Codex 전체 작업, Viewer 백링크 통합"));
    expect(await screen.findByRole("tab", { name: "개요" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Viewer를 구현해/ })).toBeInTheDocument();

    for (const [tabName, evidence] of [["대화", "실제 원본 대화"], ["변경 파일", "src/session.py"], ["명령", "uv run pytest"], ["테스트", "pytest"]]) {
      fireEvent.click(screen.getByRole("tab", { name: tabName }));
      expect(await screen.findByText(evidence)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: /Viewer를 구현해/ }));
      expect(screen.getByText("Task 상세")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: `원본 ${tabName === "변경 파일" ? "파일" : tabName}` }));
      expect(await screen.findByText(evidence)).toBeInTheDocument();
    }

    fireEvent.click(screen.getByRole("button", { name: /Viewer를 구현해/ }));
    fireEvent.click(screen.getByRole("button", { name: "그래프에서 Task 보기" }));
    await waitFor(() => expect(api.getCaptureGraph).toHaveBeenLastCalledWith(expect.objectContaining({ centerId: "task:cap_session:session" })));
  });

  it("renders explicit empty states for every empty session tab and graph", async () => {
    api.listCaptures.mockResolvedValue({ items: [emptyDetail.capture], total: 1, hasMore: false });
    api.getCapture.mockResolvedValue(emptyDetail);
    api.getCaptureItems.mockResolvedValue({ items: [], total: 0, hasMore: false });
    api.getCaptureGraph.mockResolvedValue({
      nodes: [{ id: "cap_empty", type: "DEVELOPMENT_SESSION", label: "자료 없는 세션", metadata: {} }],
      edges: [], depth: 2, limit: 300, truncated: false,
    });
    render(<CaptureWorkspace />);
    fireEvent.click(await screen.findByLabelText("Codex 전체 작업, 자료 없는 세션"));
    expect(await screen.findByText("이 세션에는 연결된 Task가 없습니다.")).toBeInTheDocument();

    for (const tabName of ["대화", "변경 파일", "명령", "테스트"]) {
      fireEvent.click(screen.getByRole("tab", { name: tabName }));
      expect(await screen.findByText(`기록된 ${tabName} 자료가 없습니다.`)).toBeInTheDocument();
    }

    fireEvent.click(screen.getByRole("button", { name: "그래프 보기" }));
    expect(await screen.findByText("이 세션에 연결된 그래프 관계가 없습니다.")).toBeInTheDocument();
  });
});
