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
  analysisWarnings: string[];
  boundaryCandidates: ChatGPTBoundaryCandidate[];
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

export interface ChatGPTTaskSummary {
  taskId: string;
  sessionId: string;
  title: string;
  summary?: string | null;
  status: "planned" | "in_progress" | "completed" | "failed" | "cancelled";
  boundaryStatus: "suggested" | "confirmed" | "uncertain" | "manual";
  startedAt?: string | null;
  completedAt?: string | null;
  messageRange: { startSequence: number; endSequence: number };
  activityIds: string[];
  provenance: ChatGPTProvenance;
}

export interface ChatGPTActivity {
  activityId: string;
  taskId: string;
  activityType: "request" | "response" | "decision" | "command" | "file_change" | "test" | "result" | "note";
  sequence: number;
  timestamp?: string | null;
  summary?: string | null;
  entityRefs: string[];
  provenance: ChatGPTProvenance;
}

export interface ChatGPTBoundaryCandidate {
  messageSequence: number;
  confidence: number;
  reasons: string[];
  provenance: ChatGPTProvenance;
}

export interface ChatGPTTaskDetail {
  task: ChatGPTTaskSummary;
  activities: ChatGPTActivity[];
  boundaryCandidates: ChatGPTBoundaryCandidate[];
  analysisWarnings: string[];
}

export interface ChatGPTPage<T> {
  items: T[];
  nextCursor?: string | null;
  hasMore: boolean;
  total: number;
}
