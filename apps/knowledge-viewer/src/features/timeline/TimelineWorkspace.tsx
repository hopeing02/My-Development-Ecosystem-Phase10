import { useEffect, useState } from "react";

import { listCaptures } from "../captures/api";
import type { CaptureSummary } from "../captures/types";
import { getChatGPTTimeline } from "../chatgpt-import/api";
import type { ChatGPTTimelineEntry } from "../chatgpt-import/types";

interface Props {
  onOpenCapture: (captureId: string) => void;
  onOpenChatGPT: (sessionId: string, taskId?: string | null, messageId?: string | null) => void;
}

type TimelineItem =
  | { source: "capture"; timestamp: string; capture: CaptureSummary }
  | { source: "chatgpt"; timestamp: string; entry: ChatGPTTimelineEntry };

export function TimelineWorkspace({ onOpenCapture, onOpenChatGPT }: Props) {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void Promise.allSettled([loadAllCaptures(), getChatGPTTimeline()]).then(([captures, chatgpt]) => {
      if (!active) return;
      const next: TimelineItem[] = [];
      const nextWarnings: string[] = [];
      if (captures.status === "fulfilled") {
        next.push(...captures.value.map((capture) => ({ source: "capture" as const, timestamp: capture.capturedAt, capture })));
      } else {
        nextWarnings.push("Capture Timeline을 불러오지 못했습니다.");
      }
      if (chatgpt.status === "fulfilled") {
        next.push(...chatgpt.value.items.map((entry) => ({ source: "chatgpt" as const, timestamp: entry.timestamp, entry })));
        if (chatgpt.value.omittedWithoutTimestamp > 0) {
          nextWarnings.push(`timestamp가 없어 제외한 ChatGPT 항목 ${chatgpt.value.omittedWithoutTimestamp}개`);
        }
      } else {
        nextWarnings.push("ChatGPT Timeline을 불러오지 못했습니다.");
      }
      next.sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp));
      setItems(next);
      setWarnings(nextWarnings);
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  return (
    <section className="project-timeline chatgpt-timeline" aria-labelledby="project-timeline-title">
      <div className="chatgpt-task-heading">
        <div><span className="eyebrow">LOCAL · ORIGINAL + DERIVED</span><h2 id="project-timeline-title">Project Timeline</h2></div>
        <span>{items.length}개 이벤트</span>
      </div>
      {warnings.map((warning) => <p className="warning" key={warning}>{warning}</p>)}
      {loading ? <p className="muted">Timeline을 불러오는 중…</p> : items.length === 0 ? <p className="empty-state">표시할 timestamp가 없습니다.</p> : (
        <ol>
          {items.map((item) => item.source === "capture" ? (
            <li key={`capture:${item.capture.captureId}`}>
              <time dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time>
              <button onClick={() => onOpenCapture(item.capture.captureId)}>
                <span className={`capture-badge source-${item.capture.sourceType}`}>{captureLabel(item.capture)}</span>
                <strong>{item.capture.title}</strong>
                <small>{item.capture.projectId ?? "프로젝트 미지정"} · source=original</small>
              </button>
            </li>
          ) : (
            <li key={`chatgpt:${item.entry.entityType}:${item.entry.entityId}`}>
              <time dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time>
              <button onClick={() => onOpenChatGPT(item.entry.sessionId, item.entry.taskId, item.entry.messageId)}>
                <span className={`entity-type type-${item.entry.entityType.toLowerCase()}`}>ChatGPT {item.entry.entityType}</span>
                <strong>{item.entry.title}</strong>
                <small>{item.entry.sessionTitle} · source={item.entry.provenance.source}</small>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

async function loadAllCaptures(): Promise<CaptureSummary[]> {
  let page = await listCaptures({ limit: 100, sort: "asc" });
  const items = [...page.items];
  while (page.hasMore && page.nextCursor) {
    page = await listCaptures({ limit: 100, sort: "asc", cursor: page.nextCursor });
    items.push(...page.items);
  }
  return items;
}

function captureLabel(item: CaptureSummary): string {
  if (item.captureType === "development_session") return item.sourceType === "codex" ? "Codex Session" : "Development Session";
  return item.sourceType === "chatgpt" ? "ChatGPT Clip" : item.sourceType === "codex" ? "Codex Clip" : "General Clip";
}
