import type {
  DocumentDetail,
  KnowledgeGraph,
  KnowledgeSource,
  SearchResult,
  TagCount,
  ChangePreview,
  CommandResult,
  DocumentUpdateRequest,
} from "./types";

interface Envelope<T> {
  apiVersion: string;
  success: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, string> };
}

export class KnowledgeApiError extends Error {
  constructor(public code: string, message: string, public details: Record<string, string> = {}) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers } });
  const payload = (await response.json()) as Envelope<T>;
  if (payload.apiVersion !== "1") throw new Error("지원하지 않는 Knowledge API 버전입니다.");
  if (!response.ok || !payload.success || !payload.data) {
    throw new KnowledgeApiError(payload.error?.code ?? "REQUEST_FAILED", payload.error?.message ?? "Knowledge API request failed.", payload.error?.details);
  }
  return payload.data;
}

export async function previewDocumentUpdate(sourceId: string, documentId: string, update: DocumentUpdateRequest): Promise<ChangePreview> {
  return (await request<{ preview: ChangePreview }>(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/documents/${encodeURIComponent(documentId)}/preview-update`, { method: "POST", body: JSON.stringify(update) })).preview;
}

export async function updateDocument(sourceId: string, documentId: string, update: DocumentUpdateRequest): Promise<CommandResult> {
  return request<CommandResult>(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/documents/${encodeURIComponent(documentId)}`, { method: "PATCH", body: JSON.stringify(update) });
}

export interface LinkResolutionRequest {
  expectedContentHash: string;
  linkOccurrenceId: string;
  targetDocumentId: string;
  linkStyle: "preserve" | "wiki" | "markdown";
  createBackup?: boolean;
  confirmSensitive?: boolean;
  previewOnly?: boolean;
}

export async function resolveLink(sourceId: string, documentId: string, update: LinkResolutionRequest): Promise<CommandResult | { preview: { before: string; after: string; target: { id: string; title: string; relativePath: string } } }> {
  return request(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/documents/${encodeURIComponent(documentId)}/link-resolutions`, { method: "POST", body: JSON.stringify(update) });
}

export async function reindexDocument(sourceId: string, documentId: string, confirmSensitive: boolean): Promise<CommandResult> {
  const query = confirmSensitive ? "?confirmSensitive=true" : "";
  return request<CommandResult>(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/documents/${encodeURIComponent(documentId)}/reindex${query}`, { method: "POST", body: "{}" });
}

export async function listSources(): Promise<KnowledgeSource[]> {
  return (await request<{ sources: KnowledgeSource[] }>("/api/v1/knowledge/sources")).sources;
}

export interface GraphOptions {
  tag?: string;
  includeOrphans?: boolean;
  includeBroken?: boolean;
  confirmSensitive?: boolean;
  documentId?: string;
  depth?: number;
  direction?: string;
}

export async function getGraph(sourceId: string, options: GraphOptions = {}): Promise<KnowledgeGraph> {
  const parameters = new URLSearchParams();
  Object.entries(options).forEach(([key, value]) => {
    if (value !== undefined && key !== "documentId") parameters.set(key, String(value));
  });
  const base = options.documentId
    ? `/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/documents/${encodeURIComponent(options.documentId)}/graph`
    : `/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/graph`;
  return request<KnowledgeGraph>(`${base}${parameters.size ? `?${parameters}` : ""}`);
}

export async function getDocument(sourceId: string, documentId: string, confirmSensitive: boolean): Promise<DocumentDetail> {
  const query = confirmSensitive ? "?confirmSensitive=true" : "";
  return (await request<{ document: DocumentDetail }>(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/documents/${encodeURIComponent(documentId)}${query}`)).document;
}

export async function getTags(sourceId: string, confirmSensitive: boolean): Promise<TagCount[]> {
  const query = confirmSensitive ? "?confirmSensitive=true" : "";
  return (await request<{ tags: TagCount[] }>(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/tags${query}`)).tags;
}

export async function searchDocuments(query: string, sourceId: string, tag: string, confirmSensitive: boolean): Promise<SearchResult[]> {
  const parameters = new URLSearchParams({ q: query, sourceId });
  if (tag) parameters.set("tag", tag);
  if (confirmSensitive) parameters.set("confirmSensitive", "true");
  return (await request<{ documents: SearchResult[] }>(`/api/v1/knowledge/search?${parameters}`)).documents;
}
