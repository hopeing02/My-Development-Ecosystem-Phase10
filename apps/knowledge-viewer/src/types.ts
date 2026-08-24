export interface KnowledgeSource {
  id: string;
  name: string;
  category: string;
  sourceType: string;
  sensitive: boolean;
  enabled: boolean;
  documentCount: number;
  readOnly?: boolean;
  editableInViewer?: boolean;
  allowLinkRewrite?: boolean;
  allowDocumentCreate?: boolean;
  allowAsSharedLinkTarget?: boolean;
}

export interface GraphNode {
  id: string;
  sourceId: string;
  title: string;
  label: string;
  relativePath: string;
  category: string;
  tags: string[];
  incomingCount: number;
  outgoingCount: number;
  brokenOutgoingCount: number;
  isOrphan: boolean;
  modifiedAt: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  linkType: string;
  displayText?: string;
}

export interface BrokenEdge {
  id: string;
  sourceDocumentId: string;
  target: string;
  linkType: string;
  resolutionStatus: "unresolved" | "ambiguous";
}

export interface KnowledgeGraph {
  source: KnowledgeSource;
  nodes: GraphNode[];
  edges: GraphEdge[];
  brokenEdges: BrokenEdge[];
  totalDocumentCount: number;
  returnedDocumentCount: number;
  truncated: boolean;
}

export interface DocumentReference {
  documentId: string;
  sourceId: string;
  title: string;
}

export interface DocumentDetail {
  id: string;
  sourceId: string;
  title: string;
  relativePath: string;
  category: string;
  tags: string[];
  aliases: string[];
  modifiedAt: string;
  indexedAt: string;
  preview: string;
  body: string;
  rawContent: string;
  frontmatter: Record<string, unknown>;
  contentHash: string;
  editable: boolean;
  outgoingLinks: DocumentReference[];
  incomingLinks: DocumentReference[];
  unresolvedLinks: string[];
  ambiguousLinks: string[];
  unresolvedLinkOccurrences: LinkOccurrence[];
}

export interface LinkOccurrence {
  id: string;
  rawText: string;
  rawTarget: string;
  target: string;
  linkType: "wiki_link" | "internal_markdown";
  startOffset: number;
  endOffset: number;
  line: number;
  column: number;
  contextPreview: string;
  resolutionStatus: "unresolved" | "ambiguous";
}

export interface DocumentUpdateRequest {
  expectedContentHash: string;
  title: string;
  tags: string[];
  aliases: string[];
  body: string;
  createBackup?: boolean;
  confirmSensitive?: boolean;
}

export interface ChangePreview {
  before: { title: string; tags: string[]; aliases: string[] };
  after: { title: string; tags: string[]; aliases: string[] };
  bodyChangedLineCount: number;
  linksAdded: string[];
  linksRemoved: string[];
}

export interface CommandResult {
  fileSaved: boolean;
  graphRevision: number;
  document?: { id: string; title: string; relativePath: string; contentHash: string; modifiedAt: string };
  indexing: { status: "completed" | "failed"; documentStatus?: string; errorCode?: string; retryable?: boolean; unresolvedLinkCount?: number };
}

export interface SearchResult {
  id: string;
  sourceId: string;
  title: string;
  relativePath: string;
  category: string;
  tags: string[];
  snippet: string;
  matchReason: string;
}

export interface TagCount {
  name: string;
  documentCount: number;
}
