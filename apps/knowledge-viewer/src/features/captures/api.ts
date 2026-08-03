import type { CaptureDetail, CaptureGraphData, CaptureSummary, Page } from "./types";

export class CaptureApiError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
  });
  const payload = await response.json() as T & { error?: { code?: string; message?: string } };
  if (!response.ok || payload.error) {
    throw new CaptureApiError(payload.error?.code ?? "CAPTURE_DETAIL_LOAD_FAILED", payload.error?.message ?? "Capture 자료를 불러오지 못했습니다.");
  }
  return payload;
}

export interface CaptureFilters {
  q?: string;
  sourceType?: string;
  captureType?: string;
  captureDevice?: string;
  projectId?: string;
  status?: string;
  testStatus?: string;
  relationStatus?: string;
  from?: string;
  to?: string;
  sort?: string;
  cursor?: string;
  limit?: number;
}

export function listCaptures(filters: CaptureFilters): Promise<Page<CaptureSummary>> {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return request(`/api/v1/captures?${query}`);
}

export function getCapture(captureId: string): Promise<CaptureDetail> {
  return request(`/api/v1/captures/${encodeURIComponent(captureId)}`);
}

export function getCaptureItems(captureId: string, collection: string, cursor?: string): Promise<Page<Record<string, unknown>>> {
  const query = new URLSearchParams({ limit: "30" });
  if (cursor) query.set("cursor", cursor);
  return request(`/api/v1/captures/${encodeURIComponent(captureId)}/${collection}?${query}`);
}

export function getCaptureDiffs(captureId: string): Promise<{ items: Record<string, unknown>[]; total: number; previewLimitBytes: number }> {
  return request(`/api/v1/captures/${encodeURIComponent(captureId)}/diffs`);
}

export function getCaptureBacklinks(documentId: string): Promise<{ items: Array<CaptureSummary & { relationType: string }>; total: number }> {
  return request(`/api/v1/documents/${encodeURIComponent(documentId)}/capture-backlinks`);
}

export function updateCapture(captureId: string, value: { title?: string; tags?: string[]; projectId?: string; parentDocument?: string; userNote?: string }): Promise<CaptureDetail> {
  return request(`/api/v1/captures/${encodeURIComponent(captureId)}`, { method: "PATCH", body: JSON.stringify(value) });
}

export function transitionRelation(relationId: string, action: "confirm" | "reject" | "remove"): Promise<Record<string, unknown>> {
  const path = action === "remove" ? `/api/v1/capture-relations/${encodeURIComponent(relationId)}` : `/api/v1/capture-relations/${encodeURIComponent(relationId)}/${action}`;
  return request(path, { method: action === "remove" ? "DELETE" : "POST", ...(action === "reject" ? { body: JSON.stringify({ rejectionReason: "viewer_rejected" }) } : {}) });
}

export function getCaptureGraph(options: { centerId?: string; projectId?: string; depth: number; includeCandidates: boolean; expanded: boolean }): Promise<CaptureGraphData> {
  const query = new URLSearchParams({ depth: String(options.depth), includeCandidates: String(options.includeCandidates) });
  if (options.projectId) query.set("projectId", options.projectId);
  if (!options.expanded) query.set("nodeTypes", "DOCUMENT,PROJECT,CLIPBOARD_CAPTURE,DEVELOPMENT_SESSION,FILE");
  const path = options.centerId ? `/api/v1/graph/neighborhood/${encodeURIComponent(options.centerId)}` : "/api/v1/graph";
  return request(`${path}?${query}`);
}
