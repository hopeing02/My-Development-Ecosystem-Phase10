import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { LinkResolutionDialog } from "./LinkResolutionDialog";

const { searchDocuments, resolveLink } = vi.hoisted(() => ({ searchDocuments: vi.fn(), resolveLink: vi.fn() }));
vi.mock("./api", () => ({ searchDocuments, resolveLink }));

beforeEach(() => {
  searchDocuments.mockResolvedValue([{ id: "ks-001::target.md", sourceId: "ks-001", title: "대상", relativePath: "target.md", category: "development", tags: [], snippet: "", matchReason: "exact_title" }]);
  resolveLink
    .mockResolvedValueOnce({ preview: { before: "[[없는 링크]]", after: "[[target|없는 링크]]", target: { id: "ks-001::target.md", title: "대상", relativePath: "target.md" } } })
    .mockResolvedValueOnce({ fileSaved: true, graphRevision: 2, indexing: { status: "completed" } });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

test("searches, previews, and explicitly resolves one occurrence", async () => {
  const onSaved = vi.fn().mockResolvedValue(undefined);
  render(<LinkResolutionDialog
    document={{ id: "ks-001::doc.md", sourceId: "ks-001", title: "문서", relativePath: "doc.md", category: "development", tags: [], aliases: [], modifiedAt: "", indexedAt: "", preview: "", body: "", rawContent: "", frontmatter: {}, contentHash: "hash", editable: true, outgoingLinks: [], incomingLinks: [], unresolvedLinks: [], ambiguousLinks: [], unresolvedLinkOccurrences: [] }}
    occurrence={{ id: "occ-1", rawText: "[[없는 링크]]", rawTarget: "없는 링크", target: "없는 링크", linkType: "wiki_link", startOffset: 0, endOffset: 10, line: 1, column: 1, contextPreview: "[[없는 링크]]", resolutionStatus: "unresolved" }}
    sensitive={false} onClose={vi.fn()} onSaved={onSaved}
  />);
  fireEvent.click(
    await screen.findByRole("button", { name: /대상target.md/ }, { timeout: 5000 }),
  );
  fireEvent.click(screen.getByRole("button", { name: "변경 미리보기" }));
  expect(await screen.findByText("[[target|없는 링크]]")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "선택 문서에 연결" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ graphRevision: 2 })));
  expect(resolveLink).toHaveBeenNthCalledWith(1, "ks-001", "ks-001::doc.md", expect.objectContaining({ linkOccurrenceId: "occ-1", previewOnly: true }));
});
