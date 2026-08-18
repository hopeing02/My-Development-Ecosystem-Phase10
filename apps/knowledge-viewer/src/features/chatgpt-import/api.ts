import type { ChatGPTImportResult } from "./types";

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
