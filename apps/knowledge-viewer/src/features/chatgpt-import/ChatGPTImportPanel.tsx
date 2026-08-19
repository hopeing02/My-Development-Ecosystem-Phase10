import { useCallback, useEffect, useState, type FormEvent } from "react";

import { CaptureGraph } from "../captures/CaptureGraph";
import type { CaptureGraphData } from "../captures/types";
import {
  ChatGPTImportApiError,
  getChatGPTGraph,
  getChatGPTMessages,
  getChatGPTSession,
  importChatGPTExport,
  importChatGPTSharedLink,
  listChatGPTSessions,
} from "./api";
import type {
  ChatGPTImportResult,
  ChatGPTMessage,
  ChatGPTSessionDetail,
  ChatGPTSessionSummary,
} from "./types";

const STATUS_LABELS = {
  imported: "가져오기 완료",
  partial: "일부 세션 가져오기 완료",
  duplicate: "이미 가져온 export",
} as const;

export function ChatGPTImportPanel() {
  const [mode, setMode] = useState<"sessions" | "import">("sessions");
  const [query, setQuery] = useState("");
  const [sessions, setSessions] = useState<ChatGPTSessionSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [detail, setDetail] = useState<ChatGPTSessionDetail | null>(null);
  const [messages, setMessages] = useState<ChatGPTMessage[]>([]);
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
      }
    } catch (caught) {
      setError(queryError(caught));
    } finally {
      setLoading(false);
    }
  }, [query]);

  const openSession = useCallback(async (sessionId: string) => {
    setSelectedId(sessionId);
    setError("");
    try {
      const [nextDetail, firstPage] = await Promise.all([
        getChatGPTSession(sessionId),
        getChatGPTMessages(sessionId),
      ]);
      let page = firstPage;
      const items = [...page.items];
      while (page.hasMore && page.nextCursor) {
        page = await getChatGPTMessages(sessionId, page.nextCursor);
        items.push(...page.items);
      }
      setDetail(nextDetail);
      setMessages(items);
    } catch (caught) {
      setError(queryError(caught));
    }
  }, []);

  useEffect(() => {
    void loadSessions("");
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  return (
    <section className="chatgpt-workspace" aria-labelledby="chatgpt-title">
      <div className="chatgpt-heading">
        <div>
          <span className="eyebrow">LOCAL · READ-ONLY PROJECTION</span>
          <h2 id="chatgpt-title">ChatGPT 세션</h2>
        </div>
        <div className="chatgpt-mode" role="tablist" aria-label="ChatGPT 화면">
          <button className={mode === "sessions" ? "active" : ""} onClick={() => setMode("sessions")}>세션 보기</button>
          <button className={mode === "import" ? "active" : ""} onClick={() => setMode("import")}>가져오기</button>
        </div>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {mode === "import" ? (
        <ImportForms onImported={() => void loadSessions("")} />
      ) : (
        <div className="chatgpt-session-layout">
          <aside className="chatgpt-session-sidebar">
            <form onSubmit={(event) => { event.preventDefault(); void loadSessions(); }}>
              <label>세션 검색<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="제목 또는 대화 내용" /></label>
              <button type="submit">검색</button>
            </form>
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
              <CaptureGraph graph={graph} onOpenCapture={() => undefined} onOpenTask={() => undefined} onOpenChatGPTSession={(sessionId) => { setGraphMode(false); void openSession(sessionId); }} />
            ) : detail ? (
              <SessionDetail detail={detail} messages={messages} />
            ) : (
              <p className="empty-state">왼쪽에서 세션을 선택하세요.</p>
            )}
          </main>
        </div>
      )}
    </section>
  );
}

function SessionDetail({ detail, messages }: { detail: ChatGPTSessionDetail; messages: ChatGPTMessage[] }) {
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
      <h4>원본 대화 순서</h4>
      <div className="chatgpt-message-list">
        {messages.map((message) => (
          <article key={message.messageId} className={`chatgpt-message role-${message.role}`}>
            <header><strong>{roleLabel(message.role)}</strong><span>#{message.sequence} · {message.timestamp ? new Date(message.timestamp).toLocaleString() : "시간 미상"}</span></header>
            <pre>{message.content}</pre>
          </article>
        ))}
      </div>
    </article>
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

function roleLabel(role: ChatGPTMessage["role"]): string {
  return ({ user: "사용자", assistant: "ChatGPT", tool: "도구", system: "시스템" })[role];
}
