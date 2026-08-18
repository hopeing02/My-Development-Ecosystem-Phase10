import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatGPTImportPanel } from "./ChatGPTImportPanel";

const api = vi.hoisted(() => ({
  importChatGPTExport: vi.fn(),
  importChatGPTSharedLink: vi.fn(),
}));

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  importChatGPTExport: api.importChatGPTExport,
  importChatGPTSharedLink: api.importChatGPTSharedLink,
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
  });

  it("uploads an explicitly selected export without persisting the key", async () => {
    render(<ChatGPTImportPanel />);
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
    expect(screen.getByRole("button", { name: "로컬로 가져오기" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "공유 링크 가져오기" })).toBeDisabled();
  });

  it("imports only the explicitly submitted public shared link", async () => {
    render(<ChatGPTImportPanel />);
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
