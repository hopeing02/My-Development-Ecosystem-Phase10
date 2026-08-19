import type { CaptureGraphData } from "../captures/types";
import type {
  ChatGPTImportResult,
  ChatGPTMessage,
  ChatGPTPage,
  ChatGPTSessionDetail,
  ChatGPTSessionSummary,
  ChatGPTTaskDetail,
  ChatGPTTaskSummary,
} from "./types";

export class ChatGPTImportApiError extends Error {
  constructor(public code: string, message: string) {
    super(message);
  }
}

export async function importChatGPTExport(
  file: File,
  controlApiKey: string,
): Promise<ChatGPTImportResult> {
  const response = await fetch("/api/v1/chatgpt/imports", {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${controlApiKey}`,
      "Content-Type": "application/zip",
      "X-File-Name": file.name,
    },
    body: file,
  });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const error = readError(payload);
    throw new ChatGPTImportApiError(error.code, error.message);
  }
  if (!isImportResult(payload)) {
    throw new ChatGPTImportApiError(
      "CHATGPT_IMPORT_RESPONSE_INVALID",
      "가져오기 응답 형식을 확인할 수 없습니다.",
    );
  }
  return payload;
}

export async function importChatGPTSharedLink(
  sharedUrl: string,
  controlApiKey: string,
): Promise<ChatGPTImportResult> {
  return requestImport({
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${controlApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url: sharedUrl }),
  });
}

export function listChatGPTSessions(
  query = "",
  cursor?: string,
): Promise<ChatGPTPage<ChatGPTSessionSummary>> {
  const parameters = new URLSearchParams({ limit: "30" });
  if (query.trim()) parameters.set("q", query.trim());
  if (cursor) parameters.set("cursor", cursor);
  return requestQuery(`/api/v1/chatgpt/sessions?${parameters}`);
}

export function getChatGPTSession(sessionId: string): Promise<ChatGPTSessionDetail> {
  return requestQuery(`/api/v1/chatgpt/sessions/${encodeURIComponent(sessionId)}`);
}

export function getChatGPTMessages(
  sessionId: string,
  cursor?: string,
): Promise<ChatGPTPage<ChatGPTMessage>> {
  const parameters = new URLSearchParams({ limit: "100" });
  if (cursor) parameters.set("cursor", cursor);
  return requestQuery(
    `/api/v1/chatgpt/sessions/${encodeURIComponent(sessionId)}/messages?${parameters}`,
  );
}

export function listChatGPTTasks(
  sessionId: string,
  cursor?: string,
): Promise<ChatGPTPage<ChatGPTTaskSummary>> {
  const parameters = new URLSearchParams({ sessionId, limit: "100" });
  if (cursor) parameters.set("cursor", cursor);
  return requestQuery(`/api/v1/chatgpt/tasks?${parameters}`);
}

export function getChatGPTTask(taskId: string): Promise<ChatGPTTaskDetail> {
  return requestQuery(`/api/v1/chatgpt/tasks/${encodeURIComponent(taskId)}`);
}

export function getChatGPTGraph(sessionId?: string): Promise<CaptureGraphData> {
  const parameters = new URLSearchParams({ limit: "300" });
  if (sessionId) parameters.set("sessionId", sessionId);
  return requestQuery(`/api/v1/chatgpt/graph?${parameters}`);
}

async function requestImport(init: RequestInit): Promise<ChatGPTImportResult> {
  const response = await fetch("/api/v1/chatgpt/shared-imports", {
    method: "POST",
    ...init,
  });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const error = readError(payload);
    throw new ChatGPTImportApiError(error.code, error.message);
  }
  if (!isImportResult(payload)) {
    throw new ChatGPTImportApiError(
      "CHATGPT_IMPORT_RESPONSE_INVALID",
      "가져오기 응답 형식을 확인할 수 없습니다.",
    );
  }
  return payload;
}

function readError(payload: unknown): { code: string; message: string } {
  const record = asRecord(payload);
  const detail = asRecord(record?.detail);
  const error = asRecord(record?.error);
  const source = detail ?? error;
  return {
    code: typeof source?.code === "string" ? source.code : "CHATGPT_IMPORT_FAILED",
    message:
      typeof source?.message === "string"
        ? source.message
        : "ChatGPT export를 가져오지 못했습니다.",
  };
}

async function requestQuery<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const error = readError(payload);
    throw new ChatGPTImportApiError(error.code, error.message);
  }
  return payload as T;
}

function isImportResult(payload: unknown): payload is ChatGPTImportResult {
  const record = asRecord(payload);
  return (
    !!record &&
    ["imported", "partial", "duplicate"].includes(String(record.status)) &&
    typeof record.importId === "string" &&
    typeof record.discoveredSessions === "number" &&
    typeof record.projectedSessions === "number" &&
    typeof record.duplicateSessions === "number" &&
    typeof record.failedSessions === "number" &&
    Array.isArray(record.warnings)
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}
