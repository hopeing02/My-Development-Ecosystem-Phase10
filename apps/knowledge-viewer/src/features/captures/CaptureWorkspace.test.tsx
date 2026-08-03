import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CaptureWorkspace } from "./CaptureWorkspace";

const api = vi.hoisted(() => ({
  listCaptures: vi.fn(), getCapture: vi.fn(), getCaptureItems: vi.fn(),
  getCaptureDiffs: vi.fn(), getCaptureGraph: vi.fn(), transitionRelation: vi.fn(),
  updateCapture: vi.fn(),
}));

vi.mock("./api", () => api);

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
};

describe("CaptureWorkspace", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.clearAllMocks();
    api.listCaptures.mockResolvedValue({ items: [summary], total: 1, hasMore: false });
    api.getCapture.mockResolvedValue(detail);
    api.getCaptureItems.mockResolvedValue({ items: [], total: 0, hasMore: false });
    api.getCaptureDiffs.mockResolvedValue({ items: [], total: 0, previewLimitBytes: 500000 });
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
});
