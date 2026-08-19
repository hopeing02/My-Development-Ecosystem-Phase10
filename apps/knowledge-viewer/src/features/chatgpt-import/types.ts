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

export interface ChatGPTSessionSummary {
  sessionId: string;
  title: string;
  source: "chatgpt";
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  revision: number;
  projectedAt: string;
  warningCount: number;
}

export interface ChatGPTSessionDetail {
  session: ChatGPTSessionSummary & {
    sourceSessionId?: string | null;
    taskIds: string[];
    provenance: ChatGPTProvenance;
  };
  warnings: string[];
}

export interface ChatGPTMessage {
  messageId: string;
  sessionId: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  timestamp?: string | null;
  sequence: number;
  sourceMessageId?: string | null;
  provenance: ChatGPTProvenance;
}

export interface ChatGPTProvenance {
  source: "original" | "derived";
  derivedBy?: string | null;
  confidence?: number | null;
  sourceRefs: string[];
}

export interface ChatGPTPage<T> {
  items: T[];
  nextCursor?: string | null;
  hasMore: boolean;
  total: number;
}
