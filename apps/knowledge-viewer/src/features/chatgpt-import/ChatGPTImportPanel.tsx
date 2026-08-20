import { useCallback, useEffect, useState, type FormEvent } from "react";

import { CaptureGraph } from "../captures/CaptureGraph";
import type { CaptureGraphData } from "../captures/types";
import {
  ChatGPTImportApiError,
  getChatGPTGraph,
  getChatGPTMessages,
  getChatGPTSession,
  getChatGPTTask,
  getChatGPTTimeline,
  importChatGPTExport,
  importChatGPTSharedLink,
  listChatGPTSessions,
  listChatGPTTasks,
  searchChatGPT,
} from "./api";
import type {
  ChatGPTActivity,
  ChatGPTImportResult,
  ChatGPTMessage,
  ChatGPTSearchResult,
  ChatGPTSessionDetail,
  ChatGPTSessionSummary,
  ChatGPTTaskDetail,
  ChatGPTTaskSummary,
  ChatGPTTimelineResponse,
} from "./types";

const STATUS_LABELS = {
  imported: "가져오기 완료",
  partial: "일부 세션 가져오기 완료",
  duplicate: "이미 가져온 export",
} as const;

export function ChatGPTImportPanel({ initialSessionId, initialTaskId, initialMessageId }: { initialSessionId?: string; initialTaskId?: string | null; initialMessageId?: string | null } = {}) {
  const [mode, setMode] = useState<"sessions" | "timeline" | "import">("sessions");
  const [query, setQuery] = useState("");
  const [sessions, setSessions] = useState<ChatGPTSessionSummary[]>([]);
  const [searchResults, setSearchResults] = useState<ChatGPTSearchResult[]>([]);
  const [timeline, setTimeline] = useState<ChatGPTTimelineResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string>();
  const [detail, setDetail] = useState<ChatGPTSessionDetail | null>(null);
  const [messages, setMessages] = useState<ChatGPTMessage[]>([]);
  const [tasks, setTasks] = useState<ChatGPTTaskSummary[]>([]);
  const [taskDetail, setTaskDetail] = useState<ChatGPTTaskDetail | null>(null);
  const [graph, setGraph] = useState<CaptureGraphData | null>(null);
  const [graphMode, setGraphMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadSessions = useCallback(async (search = query) => {
    setLoading(true);
    setError("");
    try {
      let page = await listChatGPTSessions(search);
      const items = [...page.items];
      while (page.hasMore && page.nextCursor) {
        page = await listChatGPTSessions(search, page.nextCursor);
        items.push(...page.items);
      }
      setSessions(items);
      if (items.length === 0) {
        setSelectedId(undefined);
        setDetail(null);
        setMessages([]);
        setTasks([]);
        setTaskDetail(null);
      }
    } catch (caught) {
      setError(queryError(caught));
    } finally {
      setLoading(false);
    }
  }, [query]);

  const openSession = useCallback(async (sessionId: string, preferredTaskId?: string) => {
    setSelectedId(sessionId);
    setError("");
    try {
      const [nextDetail, firstPage, firstTaskPage] = await Promise.all([
        getChatGPTSession(sessionId),
        getChatGPTMessages(sessionId),
        listChatGPTTasks(sessionId),
      ]);
      let page = firstPage;
      const items = [...page.items];
      while (page.hasMore && page.nextCursor) {
        page = await getChatGPTMessages(sessionId, page.nextCursor);
        items.push(...page.items);
      }
      let taskPage = firstTaskPage;
      const taskItems = [...taskPage.items];
      while (taskPage.hasMore && taskPage.nextCursor) {
        taskPage = await listChatGPTTasks(sessionId, taskPage.nextCursor);
        taskItems.push(...taskPage.items);
      }
      const nextTaskId =
        preferredTaskId &&
        taskItems.some((item) => item.taskId === preferredTaskId)
          ? preferredTaskId
          : taskItems[0]?.taskId;
      setDetail(nextDetail);
      setMessages(items);
      setTasks(taskItems);
      setTaskDetail(nextTaskId ? await getChatGPTTask(nextTaskId) : null);
    } catch (caught) {
      setError(queryError(caught));
    }
  }, []);

  const openTask = useCallback(async (taskId: string) => {
    setError("");
    try {
      setTaskDetail(await getChatGPTTask(taskId));
    } catch (caught) {
      setError(queryError(caught));
    }
  }, []);

  const openRelatedEntity = useCallback(async (
    sessionId: string,
    taskId?: string | null,
    messageId?: string | null,
  ) => {
    setMode("sessions");
    setGraphMode(false);
    await openSession(sessionId, taskId ?? undefined);
    if (messageId) {
      window.setTimeout(() => focusOriginalMessage(messageId), 0);
    }
  }, [openSession]);

  const runSearch = useCallback(async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSearchResults([]);
      await loadSessions("");
      return;
    }
    setError("");
    try {
      const result = await searchChatGPT(trimmed);
      setSearchResults(result.items);
      await loadSessions(trimmed);
    } catch (caught) {
      setError(queryError(caught));
    }
  }, [loadSessions, query]);

  useEffect(() => {
    void loadSessions("");
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!initialSessionId) return;
    void openRelatedEntity(initialSessionId, initialTaskId, initialMessageId);
  }, [initialMessageId, initialSessionId, initialTaskId, openRelatedEntity]);

  useEffect(() => {
    if (!selectedId && sessions[0]) void openSession(sessions[0].sessionId);
  }, [openSession, selectedId, sessions]);

  useEffect(() => {
    if (!graphMode) return;
    setError("");
    void getChatGPTGraph(selectedId)
      .then(setGraph)
      .catch((caught) => setError(queryError(caught)));
  }, [graphMode, selectedId]);

  useEffect(() => {
    if (mode !== "timeline") return;
    setError("");
    void getChatGPTTimeline()
      .then(setTimeline)
      .catch((caught) => setError(queryError(caught)));
  }, [mode]);

  return (
    <section className="chatgpt-workspace" aria-labelledby="chatgpt-title">
      <div className="chatgpt-heading">
        <div>
          <span className="eyebrow">LOCAL · READ-ONLY PROJECTION</span>
          <h2 id="chatgpt-title">ChatGPT 세션</h2>
        </div>
        <div className="chatgpt-mode" role="tablist" aria-label="ChatGPT 화면">
          <button className={mode === "sessions" ? "active" : ""} onClick={() => setMode("sessions")}>세션 보기</button>
          <button className={mode === "timeline" ? "active" : ""} onClick={() => setMode("timeline")}>Timeline</button>
          <button className={mode === "import" ? "active" : ""} onClick={() => setMode("import")}>가져오기</button>
        </div>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {mode === "import" ? (
        <ImportForms onImported={() => void loadSessions("")} />
      ) : mode === "timeline" ? (
        <TimelinePanel timeline={timeline} onOpen={openRelatedEntity} />
      ) : (
        <div className="chatgpt-session-layout">
          <aside className="chatgpt-session-sidebar">
            <form onSubmit={(event) => { event.preventDefault(); void runSearch(); }}>
              <label>통합 검색<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Session, Message, Task, Activity" /></label>
              <button type="submit">검색</button>
            </form>
            {searchResults.length > 0 && (
              <SearchResults items={searchResults} onOpen={openRelatedEntity} />
            )}
            <button className={graphMode ? "active" : ""} onClick={() => setGraphMode((value) => !value)}>{graphMode ? "목록 보기" : "그래프 보기"}</button>
            <h3>저장된 세션 {sessions.length}개</h3>
            {loading && <p className="muted">불러오는 중…</p>}
            {!loading && sessions.length === 0 && <p className="empty-state">가져온 ChatGPT 세션이 없습니다.</p>}
            <div className="chatgpt-session-list">
              {sessions.map((session) => (
                <button key={session.sessionId} className={selectedId === session.sessionId ? "active" : ""} onClick={() => { setGraphMode(false); void openSession(session.sessionId); }}>
                  <strong>{session.title}</strong>
                  <small>{session.messageCount}개 메시지 · {new Date(session.updatedAt).toLocaleString()}</small>
                </button>
              ))}
            </div>
          </aside>
          <main className="chatgpt-session-main">
            {graphMode ? (
              <CaptureGraph
                graph={graph}
                onOpenCapture={() => undefined}
                onOpenTask={() => undefined}
                onOpenChatGPTSession={(sessionId) => { setGraphMode(false); void openSession(sessionId); }}
                onOpenChatGPTTask={(sessionId, taskId) => { setGraphMode(false); void openSession(sessionId, taskId); }}
              />
            ) : detail ? (
              <SessionDetail detail={detail} messages={messages} tasks={tasks} taskDetail={taskDetail} onOpenTask={(taskId) => void openTask(taskId)} />
            ) : (
              <p className="empty-state">왼쪽에서 세션을 선택하세요.</p>
            )}
          </main>
        </div>
      )}
    </section>
  );
}

function SearchResults({ items, onOpen }: { items: ChatGPTSearchResult[]; onOpen: (sessionId: string, taskId?: string | null, messageId?: string | null) => Promise<void> }) {
  return (
    <section className="chatgpt-related-results" aria-label="ChatGPT 관계 검색 결과">
      <h3>관계 검색 결과 {items.length}개</h3>
      {items.map((item) => (
        <button key={`${item.entityType}:${item.entityId}`} onClick={() => void onOpen(item.sessionId, item.taskId, item.messageId)}>
          <span className={`entity-type type-${item.entityType.toLowerCase()}`}>{entityTypeLabel(item.entityType)}</span>
          <strong>{item.title}</strong>
          <small>{relationPath(item)}</small>
          <span>{item.snippet}</span>
        </button>
      ))}
    </section>
  );
}

function TimelinePanel({ timeline, onOpen }: { timeline: ChatGPTTimelineResponse | null; onOpen: (sessionId: string, taskId?: string | null, messageId?: string | null) => Promise<void> }) {
  if (!timeline) return <p className="muted">Timeline을 불러오는 중…</p>;
  return (
    <section className="chatgpt-timeline" aria-labelledby="chatgpt-timeline-title">
      <div className="chatgpt-task-heading">
        <h3 id="chatgpt-timeline-title">ChatGPT Timeline {timeline.total}개</h3>
        <span>실제 timestamp만 표시</span>
      </div>
      {timeline.omittedWithoutTimestamp > 0 && <p className="warning">timestamp가 없어 제외한 항목 {timeline.omittedWithoutTimestamp}개</p>}
      {timeline.truncated && <p className="warning">최근 조회 한도를 초과하여 일부 항목만 표시합니다.</p>}
      <ol>
        {timeline.items.map((item) => (
          <li key={`${item.entityType}:${item.entityId}`}>
            <time dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time>
            <button onClick={() => void onOpen(item.sessionId, item.taskId, item.messageId)}>
              <span className={`entity-type type-${item.entityType.toLowerCase()}`}>{entityTypeLabel(item.entityType)}</span>
              <strong>{item.title}</strong>
              <small>{item.sessionTitle} · source={item.provenance.source}</small>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

function SessionDetail({ detail, messages, tasks, taskDetail, onOpenTask }: { detail: ChatGPTSessionDetail; messages: ChatGPTMessage[]; tasks: ChatGPTTaskSummary[]; taskDetail: ChatGPTTaskDetail | null; onOpenTask: (taskId: string) => void }) {
  return (
    <article className="chatgpt-session-detail">
      <span className="capture-badge source-chatgpt">ChatGPT 실제 세션</span>
      <h3>{detail.session.title}</h3>
      <dl>
        <dt>원본 구분</dt><dd>{detail.session.provenance.source === "original" ? "원본 투영" : "파생 정보"}</dd>
        <dt>메시지</dt><dd>{detail.session.messageCount}개</dd>
        <dt>생성</dt><dd>{new Date(detail.session.createdAt).toLocaleString()}</dd>
        <dt>수정</dt><dd>{new Date(detail.session.updatedAt).toLocaleString()}</dd>
        <dt>Revision</dt><dd>{detail.session.revision}</dd>
      </dl>
      {detail.warnings.length > 0 && <p className="warning">격리된 원본 항목 {detail.warnings.length}개 · Session 저장은 완료됨</p>}
      <TaskWorkflow tasks={tasks} detail={taskDetail} onOpenTask={onOpenTask} onOpenMessage={focusOriginalMessage} />
      <h4>원본 대화 순서</h4>
      <div className="chatgpt-message-list">
        {messages.map((message) => (
          <article id={messageElementId(message.messageId)} key={message.messageId} className={`chatgpt-message role-${message.role}`}>
            <header><strong>{roleLabel(message.role)}</strong><span>#{message.sequence} · {message.timestamp ? new Date(message.timestamp).toLocaleString() : "시간 미상"}</span></header>
            <pre>{message.content}</pre>
          </article>
        ))}
      </div>
    </article>
  );
}

function TaskWorkflow({ tasks, detail, onOpenTask, onOpenMessage }: { tasks: ChatGPTTaskSummary[]; detail: ChatGPTTaskDetail | null; onOpenTask: (taskId: string) => void; onOpenMessage: (messageId: string) => void }) {
  return (
    <section className="chatgpt-task-workflow" aria-labelledby="chatgpt-tasks-title">
      <div className="chatgpt-task-heading">
        <h4 id="chatgpt-tasks-title">Tasks {tasks.length}</h4>
        <span>source=derived / rule</span>
      </div>
      {tasks.length === 0 ? (
        <p className="empty-state">No Task was created without a confident user request.</p>
      ) : (
        <>
          <div className="chatgpt-task-list">
            {tasks.map((task, index) => (
              <button
                key={task.taskId}
                className={detail?.task.taskId === task.taskId ? "active" : ""}
                aria-pressed={detail?.task.taskId === task.taskId}
                onClick={() => onOpenTask(task.taskId)}
              >
                <strong>Task {index + 1} / {task.title}</strong>
                <small>{taskStatusLabel(task.status)} / confidence {confidenceLabel(task.provenance.confidence)}</small>
              </button>
            ))}
          </div>
          {detail && (
            <article className="chatgpt-task-detail">
              <header>
                <div><span className={`task-status status-${detail.task.status}`}>{taskStatusLabel(detail.task.status)}</span><span className="task-boundary">{detail.task.boundaryStatus}</span></div>
                <h5>{detail.task.title}</h5>
                <p>Messages #{detail.task.messageRange.startSequence}-#{detail.task.messageRange.endSequence} / source=derived / {detail.task.provenance.derivedBy ?? "rule"}</p>
              </header>
              <ol className="chatgpt-activity-flow">
                {detail.activities.map((activity) => {
                  const messageId = activity.entityRefs[0];
                  return (
                    <li key={activity.activityId} className={`activity-${activity.activityType}`}>
                      <button disabled={!messageId} onClick={() => messageId && onOpenMessage(messageId)}>
                        <span>{activityLabel(activity.activityType)}</span>
                        <strong>{activity.summary || "No summary"}</strong>
                        <small>#{activity.sequence} / Open original message</small>
                      </button>
                    </li>
                  );
                })}
              </ol>
              {detail.boundaryCandidates.length > 0 && <p className="warning">Unsplit Task boundary candidates: {detail.boundaryCandidates.length}</p>}
              {detail.analysisWarnings.length > 0 && <p className="warning">Task analysis warnings: {detail.analysisWarnings.length}</p>}
            </article>
          )}
        </>
      )}
    </section>
  );
}

function ImportForms({ onImported }: { onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null);

  const [controlApiKey, setControlApiKey] = useState("");
  const [sharedUrl, setSharedUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ChatGPTImportResult | null>(null);
  const [error, setError] = useState("");

  const runImport = async (request: () => Promise<ChatGPTImportResult>) => {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await request());
      onImported();
    } catch (caught) {
      setError(queryError(caught));
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !controlApiKey.trim() || busy) return;
    await runImport(() => importChatGPTExport(file, controlApiKey.trim()));
  };

  const submitSharedLink = async (event: FormEvent) => {
    event.preventDefault();
    if (!sharedUrl.trim() || !controlApiKey.trim() || busy) return;
    await runImport(() => importChatGPTSharedLink(sharedUrl.trim(), controlApiKey.trim()));
  };

  return (
    <div className="chatgpt-import-panel">
      <h2>ChatGPT 실제 세션 가져오기</h2>
      <p>Data Export ZIP 또는 공개 Shared Link를 명시적으로 선택하면 원본을 로컬에 보존하고 Session과 Message로 투영합니다.</p>
      <label>Control API Key<input type="password" autoComplete="off" value={controlApiKey} onChange={(event) => setControlApiKey(event.target.value)} /></label>
      <p className="security-note">키는 이 화면의 메모리에서만 사용하며 브라우저 저장소에 기록하지 않습니다.</p>
      <form onSubmit={(event) => void submit(event)}>
        <h3>계정 Data Export</h3>
        <label>ChatGPT Data Export ZIP<input type="file" accept=".zip,application/zip" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setResult(null); setError(""); }} /></label>
        <button className="chatgpt-import-submit" disabled={!file || !controlApiKey.trim() || busy}>{busy ? "가져오는 중…" : "로컬로 가져오기"}</button>
      </form>
      <form className="chatgpt-shared-form" onSubmit={(event) => void submitSharedLink(event)}>
        <h3>공개 Shared Link 1건</h3>
        <p>최근 계정 세션 목록에는 접근하지 않으며 사용자가 제출한 공개 snapshot 1건만 읽습니다.</p>
        <label>ChatGPT Shared Link<input type="url" placeholder="https://chatgpt.com/share/..." value={sharedUrl} onChange={(event) => { setSharedUrl(event.target.value); setResult(null); setError(""); }} /></label>
        <button className="chatgpt-import-submit" disabled={!sharedUrl.trim() || !controlApiKey.trim() || busy}>{busy ? "가져오는 중…" : "공유 링크 가져오기"}</button>
      </form>
      {error && <div className="error" role="alert">{error}</div>}
      {result && <ImportResult result={result} />}
    </div>
  );
}

function ImportResult({ result }: { result: ChatGPTImportResult }) {
  return (
    <section className={`chatgpt-import-result ${result.status}`} aria-live="polite">
      <h3>{STATUS_LABELS[result.status]}</h3>
      <dl><dt>발견한 세션</dt><dd>{result.discoveredSessions}</dd><dt>새 투영</dt><dd>{result.projectedSessions}</dd><dt>중복 세션</dt><dd>{result.duplicateSessions}</dd><dt>격리된 실패</dt><dd>{result.failedSessions}</dd></dl>
      {result.warnings.length > 0 && <div className="chatgpt-import-warnings"><h4>경고 {result.warnings.length}개</h4><ul>{result.warnings.map((warning, index) => <li key={`${warning.code}:${warning.sessionId ?? ""}:${index}`}><code>{warning.code}</code></li>)}</ul></div>}
    </section>
  );
}

function queryError(caught: unknown): string {
  return caught instanceof ChatGPTImportApiError
    ? `${caught.message} (${caught.code})`
    : "ChatGPT 자료를 불러오지 못했습니다.";
}

function entityTypeLabel(type: ChatGPTSearchResult["entityType"]): string {
  return ({
    SESSION: "Session",
    MESSAGE: "Message",
    TASK: "Task",
    ACTIVITY: "Activity",
  })[type];
}

function relationPath(item: ChatGPTSearchResult): string {
  const parts = [item.sessionTitle];
  if (item.taskId) parts.push("Task");
  if (item.messageId) parts.push("원본 Message");
  return parts.join(" → ");
}

function taskStatusLabel(status: ChatGPTTaskSummary["status"]): string {
  return ({
    planned: "\uACC4\uD68D",
    in_progress: "\uC9C4\uD589 \uC911",
    completed: "\uC644\uB8CC",
    failed: "\uC2E4\uD328",
    cancelled: "\uCDE8\uC18C",
  })[status];
}

function activityLabel(type: ChatGPTActivity["activityType"]): string {
  return ({
    request: "\uC0AC\uC6A9\uC790 \uC694\uCCAD",
    response: "AI \uC751\uB2F5",
    decision: "\uACB0\uC815",
    command: "\uBA85\uB839 \uC2E4\uD589",
    file_change: "\uD30C\uC77C \uBCC0\uACBD",
    test: "\uD14C\uC2A4\uD2B8",
    result: "\uACB0\uACFC",
    note: "\uB178\uD2B8",
  })[type];
}

function confidenceLabel(confidence?: number | null): string {
  return confidence == null ? "unknown" : Math.round(confidence * 100) + "%";
}

function messageElementId(messageId: string): string {
  return "chatgpt-message-" + encodeURIComponent(messageId);
}

function focusOriginalMessage(messageId: string): void {
  const element = document.getElementById(messageElementId(messageId));
  if (!element) return;
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  element.classList.add("source-highlight");
  window.setTimeout(() => element.classList.remove("source-highlight"), 1600);
}

function roleLabel(role: ChatGPTMessage["role"]): string {
  return ({ user: "사용자", assistant: "ChatGPT", tool: "도구", system: "시스템" })[role];
}
