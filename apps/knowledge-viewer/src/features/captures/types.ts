export type CaptureType = "clipboard_item" | "development_session";

export interface CaptureSummary {
  captureId: string;
  documentId?: string;
  title: string;
  sourceType: "chatgpt" | "codex" | "general";
  captureType: CaptureType;
  captureDevice: "android" | "windows";
  projectId?: string;
  capturedAt: string;
  status: string;
  testStatus: string;
  relationStatus: string;
  changedFilesCount: number;
  commandsCount: number;
  relationCount: number;
  match?: { field: string; snippet: string };
}

export interface CaptureRelation {
  relationId: string;
  relationType: string;
  fromCaptureId: string;
  toCaptureId: string;
  status: "suggested" | "confirmed" | "rejected" | "stale" | "removed";
  confidence: "high" | "medium" | "low";
  score: number;
  matchMethod: string;
  direction: "in" | "out";
  targetTitle?: string;
  evidence: { matchedMessageId?: string; matchRatio: number; timeDeltaSeconds?: number };
}

export interface CaptureDetail {
  capture: CaptureSummary;
  metadata: Record<string, unknown>;
  relations: CaptureRelation[];
  relationCandidates: CaptureRelation[];
  userNote?: string;
  tags: string[];
  content?: string;
  relatedSessions?: Array<CaptureSummary & { relation: CaptureRelation }>;
  summary?: {
    request?: string;
    summary?: string;
    repository?: Record<string, unknown>;
    startedAt?: string;
    endedAt?: string;
    closureReason?: string;
    clientType?: string;
  };
  messagesSummary?: { count: number };
  commandsSummary?: { count: number };
  changedFilesSummary?: { count: number };
  testsSummary?: { count: number; status: string };
  attachmentsSummary?: { count: number };
}

export interface Page<T> {
  items: T[];
  nextCursor?: string;
  hasMore: boolean;
  total: number;
}

export interface CaptureGraphNode {
  id: string;
  type: "DOCUMENT" | "PROJECT" | "CLIPBOARD_CAPTURE" | "DEVELOPMENT_SESSION" | "FILE" | "COMMAND" | "TEST_RESULT";
  label: string;
  metadata: Record<string, unknown>;
}

export interface CaptureGraphEdge {
  id: string;
  from: string;
  to: string;
  type: string;
  status: string;
}

export interface CaptureGraphData {
  nodes: CaptureGraphNode[];
  edges: CaptureGraphEdge[];
  truncated: boolean;
  limit: number;
  depth: number;
}

