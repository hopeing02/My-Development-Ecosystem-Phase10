import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";
import { getGraph, searchDocuments } from "./api";

vi.mock("./api", () => ({
  listSources: vi.fn().mockResolvedValue([
    { id: "ks-001", name: "docs", category: "development", sourceType: "markdown", sensitive: false, enabled: true, documentCount: 1 },
    { id: "ks-002", name: "personal", category: "personal", sourceType: "obsidian", sensitive: true, enabled: true, documentCount: 1 },
  ]),
  getGraph: vi.fn().mockImplementation((sourceId: string) => Promise.resolve({ source: { id: sourceId, name: sourceId }, nodes: [{ id: `${sourceId}::doc-1`, sourceId, title: "Guide" }], edges: [], brokenEdges: [], totalDocumentCount: 1, returnedDocumentCount: 1, truncated: false })),
  getTags: vi.fn().mockResolvedValue([{ name: "architecture", documentCount: 1 }]),
  getDocument: vi.fn().mockResolvedValue({ id: "ks-001::doc-1", sourceId: "ks-001", title: "Guide", relativePath: "Guide.md", category: "development", tags: ["architecture"], aliases: [], modifiedAt: "2026-07-29T00:00:00Z", indexedAt: "2026-07-29T00:00:00Z", outgoingLinks: [], incomingLinks: [], unresolvedLinks: [], ambiguousLinks: [], preview: "Preview" }),
  searchDocuments: vi.fn().mockResolvedValue([{ id: "doc-1", sourceId: "ks-001", title: "Guide", relativePath: "Guide.md", category: "development", tags: [], snippet: "Preview", matchReason: "content" }]),
}));

vi.mock("./GraphView", () => ({
  GraphView: ({ graph, onSelectNode }: { graph: { nodes: { id: string; sourceId?: string }[] } | null; onSelectNode: (id: string, sourceId: string) => void }) => <div>{graph?.nodes.map((node) => <button key={node.id} onClick={() => onSelectNode(node.id, node.sourceId ?? "ks-001")}>node</button>)}</div>,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("auto-selects a non-sensitive source and opens document detail", async () => {
  render(<App />);
  await waitFor(() => expect(getGraph).toHaveBeenCalled());
  fireEvent.click(await screen.findByRole("button", { name: "node" }));
  expect(await screen.findByText("Preview")).toBeInTheDocument();
});

test("requires confirmation before opening a sensitive source", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /personal/ }));
  expect(screen.getByRole("dialog", { name: "민감 Source 열기" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "열기" }));
  await waitFor(() => expect(getGraph).toHaveBeenCalledWith("ks-002", expect.objectContaining({ confirmSensitive: true })));
});

test("shows both repositories in one graph after confirming the sensitive source", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /전체 Source/ }));
  expect(screen.getByRole("dialog", { name: "민감 Source 열기" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "열기" }));
  await waitFor(() => {
    expect(getGraph).toHaveBeenCalledWith("ks-001", expect.objectContaining({ confirmSensitive: false }));
    expect(getGraph).toHaveBeenCalledWith("ks-002", expect.objectContaining({ confirmSensitive: true }));
  });
});

test("debounces search and opens a result in document mode", async () => {
  render(<App />);
  const input = await screen.findByPlaceholderText("제목 또는 본문");
  fireEvent.change(input, { target: { value: "Guide" } });
  await waitFor(() => expect(searchDocuments).toHaveBeenCalledWith("Guide", "ks-001", "", false), { timeout: 1000 });
  fireEvent.click((await screen.findByText("Guide")).closest("button")!);
  expect(await screen.findByText("Preview")).toBeInTheDocument();
});

test("offers installation when the browser provides an install prompt", async () => {
  const prompt = vi.fn().mockResolvedValue(undefined);
  const event = Object.assign(new Event("beforeinstallprompt"), {
    prompt,
    userChoice: Promise.resolve({ outcome: "accepted" }),
  });

  render(<App />);
  fireEvent(window, event);
  fireEvent.click(await screen.findByRole("button", { name: "앱 설치" }));

  await waitFor(() => expect(prompt).toHaveBeenCalledOnce());
  await waitFor(() => expect(screen.queryByRole("button", { name: "앱 설치" })).not.toBeInTheDocument());
});
