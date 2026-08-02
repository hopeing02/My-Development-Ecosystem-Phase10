import type { KnowledgeGraph, KnowledgeSource, SearchResult, TagCount } from "./types";

export const ALL_SOURCES_ID = "__all__";

export function createCombinedSource(sources: KnowledgeSource[]): KnowledgeSource | null {
  const enabledSources = sources.filter((source) => source.enabled);
  if (enabledSources.length < 2) return null;
  return {
    id: ALL_SOURCES_ID,
    name: "전체 Source",
    category: "combined",
    sourceType: "multiple",
    sensitive: enabledSources.some((source) => source.sensitive),
    enabled: true,
    documentCount: enabledSources.reduce((total, source) => total + source.documentCount, 0),
  };
}

export function isCombinedSource(source: KnowledgeSource | null): boolean {
  return source?.id === ALL_SOURCES_ID;
}

function linkKeys(value: string): string[] {
  const cleaned = value.trim().replace(/^\[\[/, "").replace(/\]\]$/, "").split("|")[0].split("#")[0].replace(/\\/g, "/");
  const withoutExtension = cleaned.replace(/\.md$/i, "");
  const baseName = withoutExtension.split("/").at(-1) ?? withoutExtension;
  return [...new Set([cleaned, withoutExtension, baseName].map((item) => item.toLocaleLowerCase()).filter(Boolean))];
}

export function mergeGraphs(graphs: KnowledgeGraph[], source: KnowledgeSource, includeUnresolved = true): KnowledgeGraph {
  const nodes = graphs.flatMap((graph) => graph.nodes);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const candidates = new Map<string, typeof nodes>();
  nodes.forEach((node) => {
    [node.title, node.label, node.relativePath].flatMap(linkKeys).forEach((key) => {
      candidates.set(key, [...(candidates.get(key) ?? []), node]);
    });
  });
  const crossSourceEdges = [];
  const unresolved = [];
  for (const brokenEdge of graphs.flatMap((graph) => graph.brokenEdges)) {
    const sourceNode = nodeById.get(brokenEdge.sourceDocumentId);
    const matches = linkKeys(brokenEdge.target)
      .flatMap((key) => candidates.get(key) ?? [])
      .filter((node, index, items) => node.sourceId !== sourceNode?.sourceId && items.findIndex((item) => item.id === node.id) === index);
    if (sourceNode && matches.length === 1) {
      crossSourceEdges.push({
        id: `cross-source-${brokenEdge.id}`,
        source: brokenEdge.sourceDocumentId,
        target: matches[0].id,
        linkType: brokenEdge.linkType,
        displayText: brokenEdge.target,
      });
    } else if (includeUnresolved) {
      unresolved.push(brokenEdge);
    }
  }
  return {
    source,
    nodes,
    edges: [...graphs.flatMap((graph) => graph.edges), ...crossSourceEdges],
    brokenEdges: unresolved,
    totalDocumentCount: graphs.reduce((total, graph) => total + graph.totalDocumentCount, 0),
    returnedDocumentCount: graphs.reduce((total, graph) => total + graph.returnedDocumentCount, 0),
    truncated: graphs.some((graph) => graph.truncated),
  };
}

export function mergeTags(tagGroups: TagCount[][]): TagCount[] {
  const counts = new Map<string, number>();
  tagGroups.flat().forEach((tag) => counts.set(tag.name, (counts.get(tag.name) ?? 0) + tag.documentCount));
  return [...counts.entries()]
    .map(([name, documentCount]) => ({ name, documentCount }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function mergeSearchResults(resultGroups: SearchResult[][]): SearchResult[] {
  return resultGroups.flat().sort((left, right) => left.title.localeCompare(right.title));
}
