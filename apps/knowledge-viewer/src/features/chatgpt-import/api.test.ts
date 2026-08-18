import { afterEach, describe, expect, it, vi } from "vitest";

import { importChatGPTExport } from "./api";

describe("ChatGPT import API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the selected ZIP as an authenticated binary request", async () => {
    const result = {
      status: "imported",
      importId: "chatgpt_123",
      rawDuplicate: false,
      discoveredSessions: 1,
      projectedSessions: 1,
      duplicateSessions: 0,
      failedSessions: 0,
      warnings: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["zip-data"], "export.zip", { type: "application/zip" });

    await expect(importChatGPTExport(file, "secret")).resolves.toEqual(result);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/chatgpt/imports",
      expect.objectContaining({
        method: "POST",
        body: file,
        headers: expect.objectContaining({
          Authorization: "Bearer secret",
          "Content-Type": "application/zip",
          "X-File-Name": "export.zip",
        }),
      }),
    );
  });

  it("surfaces the API error code without exposing request content", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: { code: "CHATGPT_EXPORT_INVALID", message: "Invalid ZIP." } }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const request = importChatGPTExport(new File(["bad"], "bad.zip"), "secret");
    await expect(request).rejects.toMatchObject({
      code: "CHATGPT_EXPORT_INVALID",
      message: "Invalid ZIP.",
    });
  });
});
