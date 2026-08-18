export type ChatGPTImportStatus = "imported" | "partial" | "duplicate";

export interface ChatGPTImportWarning {
  code: string;
  sessionId?: string | null;
  sourceMember?: string | null;
  sourceIndex?: number | null;
}

export interface ChatGPTImportResult {
  status: ChatGPTImportStatus;
  importId: string;
  rawDuplicate: boolean;
  discoveredSessions: number;
  projectedSessions: number;
  duplicateSessions: number;
  failedSessions: number;
  warnings: ChatGPTImportWarning[];
}
