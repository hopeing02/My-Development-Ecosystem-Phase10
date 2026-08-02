import { expect, test } from "vitest";

import { createCombinedSource, mergeGraphs, mergeSearchResults, mergeTags } from "./combined";
import type { KnowledgeGraph, KnowledgeSource } from "./types";

const sources: KnowledgeSource[] = [
  { id: "ks-001", name: "docs", category: "development", sourceType: "markdown", sensitive: false, enabled: true, documentCount: 140 },
  { id: "ks-002", name: "personal", category: "personal", sourceType: "obsidian", sensitive: true, enabled: true, documentCount: 31 },
];

test("creates a sensitive combined source without changing source identities", () => {
  expect(createCombinedSource(sources)).toEqual(expect.objectContaining({
    id: "__all__",
    documentCount: 171,
    sensitive: true,
  }));
});

test("merges source graphs and preserves each node source id", () => {
  const graphFor = (source: KnowledgeSource): KnowledgeGraph => ({
    source,
    nodes: [{ id: `${source.id}::README.md`, sourceId: source.id, title: source.name, label: source.name, relativePath: "README.md", category: source.category, tags: [], incomingCount: 0, outgoingCount: 0, brokenOutgoingCount: 0, isOrphan: true, modifiedAt: "2026-07-30T00:00:00Z" }],
    edges: [], brokenEdges: [], totalDocumentCount: source.documentCount, returnedDocumentCount: 1, truncated: false,
  });
  const combined = createCombinedSource(sources)!;
  const graph = mergeGraphs(sources.map(graphFor), combined);
  expect(graph.nodes.map((node) => node.sourceId)).toEqual(["ks-001", "ks-002"]);
  expect(graph.totalDocumentCount).toBe(171);
});

test("turns a uniquely matched broken link into a cross-source edge", () => {
  const first: KnowledgeGraph = {
    source: sources[0],
    nodes: [{ id: "ks-001::Guide.md", sourceId: "ks-001", title: "Guide", label: "Guide", relativePath: "Guide.md", category: "development", tags: [], incomingCount: 0, outgoingCount: 1, brokenOutgoingCount: 1, isOrphan: false, modifiedAt: "2026-07-30T00:00:00Z" }],
    edges: [], brokenEdges: [{ id: "missing-personal", sourceDocumentId: "ks-001::Guide.md", target: "Archive Note", linkType: "wiki", resolutionStatus: "unresolved" }], totalDocumentCount: 1, returnedDocumentCount: 1, truncated: false,
  };
  const second: KnowledgeGraph = {
    source: sources[1],
    nodes: [{ id: "ks-002::90_Archive/Archive Note.md", sourceId: "ks-002", title: "Archive Note", label: "Archive Note", relativePath: "90_Archive/Archive Note.md", category: "personal", tags: [], incomingCount: 0, outgoingCount: 0, brokenOutgoingCount: 0, isOrphan: true, modifiedAt: "2026-07-30T00:00:00Z" }],
    edges: [], brokenEdges: [], totalDocumentCount: 1, returnedDocumentCount: 1, truncated: false,
  };
  const graph = mergeGraphs([first, second], createCombinedSource(sources)!);
  expect(graph.edges).toEqual([expect.objectContaining({ source: "ks-001::Guide.md", target: "ks-002::90_Archive/Archive Note.md" })]);
  expect(graph.brokenEdges).toEqual([]);
});

test("merges duplicate tags and keeps search result source ids", () => {
  expect(mergeTags([[{ name: "mde", documentCount: 2 }], [{ name: "mde", documentCount: 3 }]])).toEqual([{ name: "mde", documentCount: 5 }]);
  const results = mergeSearchResults([
    [{ id: "a", sourceId: "ks-001", title: "B", relativePath: "B.md", category: "development", tags: [], snippet: "", matchReason: "title" }],
    [{ id: "b", sourceId: "ks-002", title: "A", relativePath: "A.md", category: "personal", tags: [], snippet: "", matchReason: "title" }],
  ]);
  expect(results.map((result) => result.sourceId)).toEqual(["ks-002", "ks-001"]);
});
