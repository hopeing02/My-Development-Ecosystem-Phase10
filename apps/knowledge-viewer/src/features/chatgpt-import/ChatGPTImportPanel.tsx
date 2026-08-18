import { useState, type FormEvent } from "react";

import {
  ChatGPTImportApiError,
  importChatGPTExport,
  importChatGPTSharedLink,
} from "./api";
import type { ChatGPTImportResult } from "./types";

const STATUS_LABELS = {
  imported: "가져오기 완료",
  partial: "일부 세션 가져오기 완료",
  duplicate: "이미 가져온 export",
} as const;

export function ChatGPTImportPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [controlApiKey, setControlApiKey] = useState("");
  const [sharedUrl, setSharedUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ChatGPTImportResult | null>(null);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !controlApiKey.trim() || busy) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await importChatGPTExport(file, controlApiKey.trim()));
    } catch (caught) {
      setError(
        caught instanceof ChatGPTImportApiError
          ? `${caught.message} (${caught.code})`
          : "ChatGPT export를 가져오지 못했습니다.",
      );
    } finally {
      setBusy(false);
    }
  };

  const submitSharedLink = async (event: FormEvent) => {
    event.preventDefault();
    if (!sharedUrl.trim() || !controlApiKey.trim() || busy) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await importChatGPTSharedLink(sharedUrl.trim(), controlApiKey.trim()));
    } catch (caught) {
      setError(
        caught instanceof ChatGPTImportApiError
          ? `${caught.message} (${caught.code})`
          : "ChatGPT 공유 링크를 가져오지 못했습니다.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="chatgpt-import-workspace" aria-labelledby="chatgpt-import-title">
      <div className="chatgpt-import-panel">
        <span className="eyebrow">LOCAL · READ-ONLY PROJECTION</span>
        <h2 id="chatgpt-import-title">ChatGPT 실제 세션 가져오기</h2>
        <p>
          ChatGPT의 Data Export ZIP을 명시적으로 선택하면 원본을 로컬에 보존하고,
          확보된 대화만 Session과 Message로 읽기 전용 투영합니다.
        </p>
        <label>
          Control API Key
          <input
            type="password"
            autoComplete="off"
            value={controlApiKey}
            onChange={(event) => setControlApiKey(event.target.value)}
          />
        </label>
        <p className="security-note">
          키는 이 화면의 메모리에서만 사용하며 브라우저 저장소에 기록하지 않습니다.
        </p>
        <form onSubmit={(event) => void submit(event)}>
          <h3>계정 Data Export</h3>
          <label>
            ChatGPT Data Export ZIP
            <input
              type="file"
              accept=".zip,application/zip"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setResult(null);
                setError("");
              }}
            />
          </label>
          <button className="chatgpt-import-submit" disabled={!file || !controlApiKey.trim() || busy}>
            {busy ? "가져오는 중…" : "로컬로 가져오기"}
          </button>
        </form>
        <form className="chatgpt-shared-form" onSubmit={(event) => void submitSharedLink(event)}>
          <h3>공개 Shared Link 1건</h3>
          <p>
            최근 세션 목록을 조회하지 않습니다. 실행할 때 공개 snapshot 1건만 로컬
            서버가 읽고 원본을 보존합니다.
          </p>
          <label>
            ChatGPT Shared Link
            <input
              type="url"
              placeholder="https://chatgpt.com/share/..."
              value={sharedUrl}
              onChange={(event) => {
                setSharedUrl(event.target.value);
                setResult(null);
                setError("");
              }}
            />
          </label>
          <button className="chatgpt-import-submit" disabled={!sharedUrl.trim() || !controlApiKey.trim() || busy}>
            {busy ? "가져오는 중…" : "공유 링크 가져오기"}
          </button>
        </form>
        {error && <div className="error" role="alert">{error}</div>}
        {result && <ImportResult result={result} />}
      </div>
    </section>
  );
}

function ImportResult({ result }: { result: ChatGPTImportResult }) {
  return (
    <section className={`chatgpt-import-result ${result.status}`} aria-live="polite">
      <h3>{STATUS_LABELS[result.status]}</h3>
      <dl>
        <dt>발견한 세션</dt><dd>{result.discoveredSessions}</dd>
        <dt>새 투영</dt><dd>{result.projectedSessions}</dd>
        <dt>중복 세션</dt><dd>{result.duplicateSessions}</dd>
        <dt>격리된 실패</dt><dd>{result.failedSessions}</dd>
      </dl>
      {result.warnings.length > 0 && (
        <div className="chatgpt-import-warnings">
          <h4>경고 {result.warnings.length}개</h4>
          <ul>
            {result.warnings.map((warning, index) => (
              <li key={`${warning.code}:${warning.sessionId ?? ""}:${index}`}>
                <code>{warning.code}</code>
                {warning.sessionId ? ` · ${warning.sessionId}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
