import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { DocumentEditor } from "./DocumentEditor";
import type { DocumentDetail } from "./types";

const { searchDocuments } = vi.hoisted(() => ({ searchDocuments: vi.fn() }));
vi.mock("./api", () => ({ searchDocuments }));

const document: DocumentDetail = {
  id: "ks-001::doc.md", sourceId: "ks-001", title: "원본", relativePath: "doc.md",
  category: "development", tags: ["old"], aliases: [], modifiedAt: "2026-07-30T00:00:00Z",
  indexedAt: "2026-07-30T00:00:00Z", preview: "본문", body: "본문", rawContent: "본문",
  frontmatter: {}, contentHash: "hash", editable: true, outgoingLinks: [], incomingLinks: [],
  unresolvedLinks: [], ambiguousLinks: [], unresolvedLinkOccurrences: [],
};
const linkSources = [
  { id: "ks-001", name: "개발", category: "development", sourceType: "markdown", sensitive: false, enabled: true, documentCount: 1 },
  { id: "ks-002", name: "mde-docs", category: "development", sourceType: "markdown", sensitive: false, enabled: true, documentCount: 1, allowAsSharedLinkTarget: true },
];

beforeEach(() => {
  searchDocuments.mockResolvedValue([{ id: "ks-001::Archive.md", sourceId: "ks-001", title: "Archive", relativePath: "90_Archive/Archive.md", category: "development", tags: [], snippet: "", matchReason: "exact_title" }]);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("previews explicit changes and saves only after user action", async () => {
  const onSave = vi.fn().mockResolvedValue(undefined);
  const onPreview = vi.fn().mockResolvedValue({
    before: { title: "원본", tags: ["old"], aliases: [] },
    after: { title: "변경", tags: ["old"], aliases: [] },
    bodyChangedLineCount: 0, linksAdded: [], linksRemoved: [],
  });
  render(<DocumentEditor document={document} sourceName="개발" sensitive={false} linkSources={linkSources} onCancel={vi.fn()} onDirtyChange={vi.fn()} onPreview={onPreview} onSave={onSave} onReload={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("제목"), { target: { value: "변경" } });
  expect(onSave).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "변경 미리보기" }));
  const dialog = await screen.findByRole("dialog", { name: "변경 내용" });
  expect(dialog).toBeInTheDocument();
  await waitFor(() => expect(onPreview).toHaveBeenCalledWith(expect.objectContaining({ expectedContentHash: "hash", title: "변경" })));
  fireEvent.click(dialog.querySelector("button.confirm")!);
  await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
});

test("adds a searched document link and deletes an exact body link", async () => {
  const linkedDocument = { ...document, body: "본문\n[[기존 링크]]\n`[[코드 링크]]`\n" };
  render(<DocumentEditor document={linkedDocument} sourceName="개발" sensitive={false} linkSources={linkSources} onCancel={vi.fn()} onDirtyChange={vi.fn()} onPreview={vi.fn()} onSave={vi.fn()} onReload={vi.fn()} />);

  expect(screen.getByText("본문 링크 1개")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "삭제" }));
  expect((screen.getByLabelText("본문") as HTMLTextAreaElement).value).not.toContain("[[기존 링크]]");
  expect((screen.getByLabelText("본문") as HTMLTextAreaElement).value).toContain("`[[코드 링크]]`");

  expect(screen.getByText("검색 Source")).toBeInTheDocument();
  expect(screen.getByText("개발")).toBeInTheDocument();
  fireEvent.change(screen.getByPlaceholderText("개발 문서 검색"), { target: { value: "Archive" } });
  fireEvent.click(await screen.findByRole("button", { name: /Archive.*90_Archive\/Archive.md.*추가/ }));
  expect((screen.getByLabelText("본문") as HTMLTextAreaElement).value).toContain("[[90_Archive/Archive|Archive]]");
});

test("adds an explicit link to an approved shared source", async () => {
  searchDocuments.mockResolvedValueOnce([{ id: "ks-002::04_development/DEV-001.md", sourceId: "ks-002", title: "개발 표준", relativePath: "04_development/DEV-001.md", category: "development", tags: [], snippet: "", matchReason: "exact_title" }]);
  render(<DocumentEditor document={document} sourceName="개발" sensitive={false} linkSources={linkSources} onCancel={vi.fn()} onDirtyChange={vi.fn()} onPreview={vi.fn()} onSave={vi.fn()} onReload={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("링크 검색 Source"), { target: { value: "ks-002" } });
  fireEvent.change(screen.getByPlaceholderText("mde-docs 문서 검색"), { target: { value: "개발 표준" } });
  fireEvent.click(await screen.findByRole("button", { name: /개발 표준.*04_development\/DEV-001.md.*추가/ }));

  expect((screen.getByLabelText("본문") as HTMLTextAreaElement).value).toContain("[[mde-docs::04_development/DEV-001|개발 표준]]");
});

test("shows save failures inside the editor", async () => {
  render(<DocumentEditor document={document} sourceName="개발" sensitive={false} linkSources={linkSources} onCancel={vi.fn()} onDirtyChange={vi.fn()} onPreview={vi.fn()} onSave={vi.fn().mockRejectedValue(new Error("저장 요청이 거부되었습니다."))} onReload={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("제목"), { target: { value: "변경" } });
  fireEvent.click(screen.getByRole("button", { name: "저장" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("저장 요청이 거부되었습니다.");
});

test("recovers from a document conflict by reindexing the latest document", async () => {
  const onReload = vi.fn().mockResolvedValue(undefined);
  const conflict = Object.assign(new Error("The document was modified after it was opened."), { code: "DOCUMENT_CONFLICT" });
  render(<DocumentEditor document={document} sourceName="개발" sensitive={false} linkSources={linkSources} onCancel={vi.fn()} onDirtyChange={vi.fn()} onPreview={vi.fn()} onSave={vi.fn().mockRejectedValue(conflict)} onReload={onReload} />);

  fireEvent.change(screen.getByLabelText("제목"), { target: { value: "충돌 편집" } });
  fireEvent.click(screen.getByRole("button", { name: "저장" }));
  expect(await screen.findByRole("dialog", { name: "다른 프로그램에서 문서가 변경되었습니다" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "최신 내용 다시 불러오기" }));
  await waitFor(() => expect(onReload).toHaveBeenCalledOnce());
});
