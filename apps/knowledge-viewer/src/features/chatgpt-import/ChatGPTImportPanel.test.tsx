import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatGPTImportPanel } from "./ChatGPTImportPanel";

const api = vi.hoisted(() => ({
  importChatGPTExport: vi.fn(),
  importChatGPTSharedLink: vi.fn(),
  listChatGPTSessions: vi.fn(),
  getChatGPTSession: vi.fn(),
  getChatGPTMessages: vi.fn(),
  getChatGPTGraph: vi.fn(),
}));

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  importChatGPTExport: api.importChatGPTExport,
  importChatGPTSharedLink: api.importChatGPTSharedLink,
  listChatGPTSessions: api.listChatGPTSessions,
  getChatGPTSession: api.getChatGPTSession,
  getChatGPTMessages: api.getChatGPTMessages,
  getChatGPTGraph: api.getChatGPTGraph,
}));

describe("ChatGPTImportPanel", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.clearAllMocks();
    api.importChatGPTExport.mockResolvedValue({
      status: "partial",
      importId: "chatgpt_123",
      rawDuplicate: false,
      discoveredSessions: 3,
      projectedSessions: 2,
      duplicateSessions: 0,
      failedSessions: 1,
      warnings: [{ code: "CHATGPT_SESSION_DAMAGED", sessionId: "session-3" }],
    });
    api.importChatGPTSharedLink.mockResolvedValue({
      status: "imported",
      importId: "chatgpt_shared_123",
      rawDuplicate: false,
      discoveredSessions: 1,
      projectedSessions: 1,
      duplicateSessions: 0,
      failedSessions: 0,
      warnings: [],
    });
    api.listChatGPTSessions.mockResolvedValue({
      items: [{ sessionId: "session-1", title: "Shared design", source: "chatgpt", createdAt: "2026-08-19T00:00:00Z", updatedAt: "2026-08-19T00:10:00Z", messageCount: 2, revision: 1, projectedAt: "2026-08-19T00:11:00Z", warningCount: 0 }],
      hasMore: false,
      total: 1,
    });
    api.getChatGPTSession.mockResolvedValue({
      session: { sessionId: "session-1", title: "Shared design", source: "chatgpt", createdAt: "2026-08-19T00:00:00Z", updatedAt: "2026-08-19T00:10:00Z", messageCount: 2, revision: 1, projectedAt: "2026-08-19T00:11:00Z", warningCount: 0, taskIds: [], provenance: { source: "original", sourceRefs: ["chatgpt:session-1"] } },
      warnings: [],
    });
    api.getChatGPTMessages.mockResolvedValue({
      items: [
        { messageId: "message-1", sessionId: "session-1", role: "user", content: "설계해줘", sequence: 1, provenance: { source: "original", sourceRefs: [] } },
        { messageId: "message-2", sessionId: "session-1", role: "assistant", content: "설계 결과입니다", sequence: 2, provenance: { source: "original", sourceRefs: [] } },
      ],
      hasMore: false,
      total: 2,
    });
    api.getChatGPTGraph.mockResolvedValue({ nodes: [], edges: [], truncated: false, limit: 300, depth: 1 });
  });

  it("lists stored sessions and shows original messages by default", async () => {
    render(<ChatGPTImportPanel />);

    expect(await screen.findByText("Shared design")).toBeInTheDocument();
    expect(await screen.findByText("설계해줘")).toBeInTheDocument();
    expect(screen.getByText("설계 결과입니다")).toBeInTheDocument();
    expect(screen.getByText("원본 투영")).toBeInTheDocument();
  });

  it("uploads an explicitly selected export without persisting the key", async () => {
    render(<ChatGPTImportPanel />);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    const file = new File(["zip-data"], "chatgpt-export.zip", { type: "application/zip" });

    fireEvent.change(screen.getByLabelText("ChatGPT Data Export ZIP"), {
      target: { files: [file] },
    });
    fireEvent.change(screen.getByLabelText("Control API Key"), {
      target: { value: "local-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "로컬로 가져오기" }));

    await waitFor(() => expect(api.importChatGPTExport).toHaveBeenCalledWith(file, "local-secret"));
    expect(await screen.findByText("일부 세션 가져오기 완료")).toBeInTheDocument();
    expect(screen.getByText("CHATGPT_SESSION_DAMAGED")).toBeInTheDocument();
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("keeps import disabled until both inputs are present", () => {
    render(<ChatGPTImportPanel />);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    expect(screen.getByRole("button", { name: "로컬로 가져오기" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "공유 링크 가져오기" })).toBeDisabled();
  });

  it("imports only the explicitly submitted public shared link", async () => {
    render(<ChatGPTImportPanel />);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    fireEvent.change(screen.getByLabelText("Control API Key"), {
      target: { value: "local-secret" },
    });
    fireEvent.change(screen.getByLabelText("ChatGPT Shared Link"), {
      target: { value: "https://chatgpt.com/share/conversation-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: "공유 링크 가져오기" }));

    await waitFor(() =>
      expect(api.importChatGPTSharedLink).toHaveBeenCalledWith(
        "https://chatgpt.com/share/conversation-1",
        "local-secret",
      ),
    );
    expect(await screen.findByText("가져오기 완료")).toBeInTheDocument();
  });
});
