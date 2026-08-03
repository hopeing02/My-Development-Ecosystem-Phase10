import { useCallback, useEffect, useMemo, useState } from "react";

import { getCapture, getCaptureDiffs, getCaptureGraph, getCaptureItems, listCaptures, transitionRelation, updateCapture, type CaptureFilters } from "./api";
import { CaptureGraph } from "./CaptureGraph";
import type { CaptureDetail, CaptureGraphData, CaptureRelation, CaptureSummary, Page } from "./types";

type SessionTab = "overview" | "messages" | "commands" | "changed-files" | "diffs" | "tests" | "related" | "metadata";

const TAB_LABELS: Record<SessionTab, string> = {
  overview: "개요", messages: "대화", commands: "명령", "changed-files": "변경 파일",
  diffs: "Diff", tests: "테스트", related: "관련 단편", metadata: "메타데이터",
};

const INITIAL_FILTERS: CaptureFilters = { sort: "newest", limit: 30 };

export function CaptureWorkspace({ initialCaptureId }: { initialCaptureId?: string }) {
  const [filters, setFilters] = useState<CaptureFilters>(INITIAL_FILTERS);
  const [draftQuery, setDraftQuery] = useState("");
  const [page, setPage] = useState<Page<CaptureSummary> | null>(null);
  const [detail, setDetail] = useState<CaptureDetail | null>(null);
  const [tab, setTab] = useState<SessionTab>("overview");
  const [tabData, setTabData] = useState<Record<string, Page<Record<string, unknown>> | { items: Record<string, unknown>[]; total: number }>>({});
  const [tabErrors, setTabErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [graphMode, setGraphMode] = useState(false);
  const [graph, setGraph] = useState<CaptureGraphData | null>(null);
  const [graphDepth, setGraphDepth] = useState(2);
  const [includeCandidates, setIncludeCandidates] = useState(false);
  const [expandedGraph, setExpandedGraph] = useState(false);

  const loadList = useCallback(async (nextFilters: CaptureFilters, append = false) => {
    setLoading(true);
    try {
      setError("");
      const next = await listCaptures(nextFilters);
      setPage((current) => append && current ? { ...next, items: [...current.items, ...next.items] } : next);
    } catch (reason) { setError((reason as Error).message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void loadList(filters); }, [filters, loadList]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((current) => ({ ...current, q: draftQuery.trim() || undefined, cursor: undefined, sort: draftQuery.trim() ? "relevance" : current.sort === "relevance" ? "newest" : current.sort }));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [draftQuery]);

  const openCapture = useCallback(async (captureId: string) => {
    try {
      setError("");
      const next = await getCapture(captureId);
      setDetail(next);
      setTab("overview");
      setTabData({});
      setTabErrors({});
      setGraphMode(false);
    } catch (reason) { setError((reason as Error).message); }
  }, []);

  useEffect(() => { if (initialCaptureId) void openCapture(initialCaptureId); }, [initialCaptureId, openCapture]);

  const loadTab = useCallback(async (selected: SessionTab, force = false) => {
    if (!detail || selected === "overview" || selected === "related" || selected === "metadata" || (tabData[selected] && !force)) return;
    try {
      setTabErrors((current) => ({ ...current, [selected]: "" }));
      const data = selected === "diffs" ? await getCaptureDiffs(detail.capture.captureId) : await getCaptureItems(detail.capture.captureId, selected);
      setTabData((current) => ({ ...current, [selected]: data }));
    } catch (reason) {
      setTabErrors((current) => ({ ...current, [selected]: (reason as Error).message }));
    }
  }, [detail, tabData]);

  useEffect(() => { void loadTab(tab); }, [loadTab, tab]);

  const loadGraph = useCallback(async () => {
    try {
      setError("");
      setGraph(await getCaptureGraph({ centerId: detail?.capture.captureId, projectId: detail ? undefined : filters.projectId, depth: graphDepth, includeCandidates, expanded: expandedGraph }));
    } catch (reason) { setError((reason as Error).message); }
  }, [detail, expandedGraph, filters.projectId, graphDepth, includeCandidates]);

  useEffect(() => { if (graphMode) void loadGraph(); }, [graphMode, loadGraph]);

  const changeFilter = (key: keyof CaptureFilters, value: string) => setFilters((current) => ({ ...current, [key]: value || undefined, cursor: undefined }));
  const refreshDetail = async () => { if (detail) setDetail(await getCapture(detail.capture.captureId)); };
  const relationAction = async (relation: CaptureRelation, action: "confirm" | "reject" | "remove") => {
    try {
      await transitionRelation(relation.relationId, action);
      await refreshDetail();
      await loadList(filters);
      if (graphMode) await loadGraph();
    } catch (reason) { setError((reason as Error).message); }
  };

  return <section className="capture-workspace">
    {error && <div className="error" role="alert">{error}<button aria-label="오류 닫기" onClick={() => setError("")}>×</button></div>}
    <aside className="capture-filters" aria-label="Capture 필터">
      <div className="capture-heading"><h2>Capture</h2><button className={graphMode ? "active" : ""} onClick={() => setGraphMode((value) => !value)}>{graphMode ? "목록 보기" : "그래프 보기"}</button></div>
      <label>검색<input value={draftQuery} onChange={(event) => setDraftQuery(event.target.value)} placeholder="대화, 명령, 파일, 테스트" /></label>
      <Filter label="출처" value={filters.sourceType} onChange={(value) => changeFilter("sourceType", value)} options={[["chatgpt", "ChatGPT"], ["codex", "Codex"], ["general", "일반"]]} />
      <Filter label="수집 유형" value={filters.captureType} onChange={(value) => changeFilter("captureType", value)} options={[["clipboard_item", "클립보드 단편"], ["development_session", "개발 전체 세션"]]} />
      <Filter label="기기" value={filters.captureDevice} onChange={(value) => changeFilter("captureDevice", value)} options={[["android", "Android"], ["windows", "Windows"]]} />
      <label>프로젝트<input value={filters.projectId ?? ""} onChange={(event) => changeFilter("projectId", event.target.value)} placeholder="전체 프로젝트" /></label>
      <Filter label="상태" value={filters.status} onChange={(value) => changeFilter("status", value)} options={[["inbox", "Inbox"], ["completed", "완료"], ["in_progress", "진행 중"], ["pending", "전송 대기"], ["failed", "오류"], ["quarantined", "격리"]]} />
      <Filter label="테스트 상태" value={filters.testStatus} onChange={(value) => changeFilter("testStatus", value)} options={[["passed", "통과"], ["failed", "실패"], ["partial", "부분 통과"], ["none", "테스트 없음"], ["unknown", "알 수 없음"]]} />
      <Filter label="관계" value={filters.relationStatus} onChange={(value) => changeFilter("relationStatus", value)} options={[["linked", "전체 세션에 연결됨"], ["suggested", "연결 후보 있음"], ["unlinked", "미연결"], ["stale", "관계 재검증 필요"]]} />
      <div className="date-filters"><label>시작일<input type="date" value={filters.from ?? ""} onChange={(event) => changeFilter("from", event.target.value)} /></label><label>종료일<input type="date" value={filters.to ?? ""} onChange={(event) => changeFilter("to", event.target.value)} /></label></div>
      <Filter label="정렬" value={filters.sort} includeAll={false} onChange={(value) => changeFilter("sort", value)} options={[["newest", "최신순"], ["oldest", "오래된순"], ["title", "제목순"], ["changed_files", "변경 파일 많은 순"], ["test_failures", "테스트 실패 우선"]]} />
      <button className="filter-reset" onClick={() => { setDraftQuery(""); setFilters(INITIAL_FILTERS); }}>필터 초기화</button>
    </aside>

    <section className="capture-main">
      {graphMode ? <>
        <div className="capture-graph-controls">
          <label>연결 깊이<select value={graphDepth} onChange={(event) => setGraphDepth(Number(event.target.value))}>{[1, 2, 3, 4].map((depth) => <option key={depth}>{depth}</option>)}</select></label>
          <label className="check"><input type="checkbox" checked={includeCandidates} onChange={(event) => setIncludeCandidates(event.target.checked)} />후보 관계 보기</label>
          <label className="check"><input type="checkbox" checked={expandedGraph} onChange={(event) => setExpandedGraph(event.target.checked)} />명령·테스트 노드</label>
        </div>
        {graph?.truncated && <div className="warning">연결된 항목이 많아 일부만 표시합니다. 필터를 좁혀 주세요.</div>}
        <CaptureGraph graph={graph} onOpenCapture={(id) => void openCapture(id)} />
      </> : <>
        <div className="capture-list-heading"><h2>통합 자료</h2><span>{loading ? "불러오는 중…" : `${page?.total ?? 0}건`}</span></div>
        {!loading && page?.items.length === 0 && <div className="empty-state">조건에 맞는 Capture가 없습니다.</div>}
        <div className="capture-list">{page?.items.map((item) => <CaptureCard key={item.captureId} item={item} active={detail?.capture.captureId === item.captureId} onOpen={() => void openCapture(item.captureId)} />)}</div>
        {page?.hasMore && <button className="load-more" onClick={() => void loadList({ ...filters, cursor: page.nextCursor }, true)}>더 보기</button>}
      </>}
    </section>

    <aside className="capture-detail">
      {!detail ? <div className="empty-state">Capture를 선택하면 원문과 연결 정보를 확인할 수 있습니다.</div> : detail.capture.captureType === "clipboard_item"
        ? <ClipboardDetail detail={detail} onOpen={openCapture} onUpdate={async (value) => { setDetail(await updateCapture(detail.capture.captureId, value)); await loadList(filters); }} onRelation={relationAction} onGraph={() => setGraphMode(true)} />
        : <SessionDetail detail={detail} tab={tab} setTab={setTab} data={tabData[tab]} error={tabErrors[tab]} retry={() => void loadTab(tab, true)} onOpen={openCapture} onRelation={relationAction} onUpdate={async (value) => { setDetail(await updateCapture(detail.capture.captureId, value)); await loadList(filters); }} onGraph={() => setGraphMode(true)} />}
    </aside>
  </section>;
}

function Filter({ label, value, options, onChange, includeAll = true }: { label: string; value?: string; options: string[][]; onChange: (value: string) => void; includeAll?: boolean }) {
  return <label>{label}<select value={value ?? ""} onChange={(event) => onChange(event.target.value)}>{includeAll && <option value="">전체</option>}{options.map(([key, text]) => <option value={key} key={key}>{text}</option>)}</select></label>;
}

function CaptureCard({ item, active, onOpen }: { item: CaptureSummary; active: boolean; onOpen: () => void }) {
  return <button className={`capture-card ${active ? "active" : ""}`} onClick={onOpen} aria-label={`${badgeLabel(item)}, ${item.title}`}>
    <span className={`capture-badge source-${item.sourceType}`}>{badgeLabel(item)}</span><strong>{item.title}</strong>
    <small>{item.projectId || "프로젝트 없음"} · {deviceLabel(item.captureDevice)} · {new Date(item.capturedAt).toLocaleString()}</small>
    <span className="capture-card-stats"><Status value={item.status} kind="capture" />{item.captureType === "development_session" && <Status value={item.testStatus} kind="test" />}{item.changedFilesCount > 0 && `변경 파일 ${item.changedFilesCount}개 · `}관계 {item.relationCount}개</span>
    {item.match && <span className="capture-match">일치: {item.match.field} &gt; {item.match.snippet}</span>}
  </button>;
}

function ClipboardDetail({ detail, onOpen, onUpdate, onRelation, onGraph }: { detail: CaptureDetail; onOpen: (id: string) => Promise<void>; onUpdate: (value: Record<string, unknown>) => Promise<void>; onRelation: (relation: CaptureRelation, action: "confirm" | "reject" | "remove") => Promise<void>; onGraph: () => void }) {
  return <div className="capture-detail-body">
    <span className={`capture-badge source-${detail.capture.sourceType}`}>{badgeLabel(detail.capture)}</span><h2>{detail.capture.title}</h2>
    <CaptureFacts capture={detail.capture} metadata={detail.metadata} />
    <button className="center-action" onClick={onGraph}>그래프에서 보기</button>
    <h3>원문 <span className="derived-label">수집 원본 · 읽기 전용</span></h3>
    <button className="copy" onClick={() => void navigator.clipboard.writeText(detail.content ?? "")}>원문 복사</button>
    <pre className="capture-content">{detail.content}</pre>
    <RelationPanel relations={detail.relations} onOpen={onOpen} onAction={onRelation} />
    <MetadataEditor detail={detail} onSave={onUpdate} />
  </div>;
}

function SessionDetail({ detail, tab, setTab, data, error, retry, onOpen, onRelation, onUpdate, onGraph }: { detail: CaptureDetail; tab: SessionTab; setTab: (tab: SessionTab) => void; data?: Page<Record<string, unknown>> | { items: Record<string, unknown>[]; total: number }; error?: string; retry: () => void; onOpen: (id: string) => Promise<void>; onRelation: (relation: CaptureRelation, action: "confirm" | "reject" | "remove") => Promise<void>; onUpdate: (value: Record<string, unknown>) => Promise<void>; onGraph: () => void }) {
  return <div className="capture-detail-body session-detail"><span className="capture-badge source-codex">Codex 전체 작업</span><h2>{detail.capture.title}</h2>
    <div className="session-tabs" role="tablist" aria-label="개발 세션 상세">{(Object.keys(TAB_LABELS) as SessionTab[]).map((item) => <button role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)}>{TAB_LABELS[item]}</button>)}</div>
    {error ? <div className="tab-error" role="alert">{TAB_LABELS[tab]}을 불러오지 못했습니다.<button onClick={retry}>다시 시도</button></div> : <SessionTabContent detail={detail} tab={tab} data={data} onOpen={onOpen} onRelation={onRelation} onUpdate={onUpdate} onGraph={onGraph} />}
  </div>;
}

function SessionTabContent({ detail, tab, data, onOpen, onRelation, onUpdate, onGraph }: { detail: CaptureDetail; tab: SessionTab; data?: Page<Record<string, unknown>> | { items: Record<string, unknown>[]; total: number }; onOpen: (id: string) => Promise<void>; onRelation: (relation: CaptureRelation, action: "confirm" | "reject" | "remove") => Promise<void>; onUpdate: (value: Record<string, unknown>) => Promise<void>; onGraph: () => void }) {
  if (tab === "overview") return <><CaptureFacts capture={detail.capture} metadata={detail.metadata} /><button className="center-action" onClick={onGraph}>그래프에서 보기</button><h3>최초 요청</h3><pre>{detail.summary?.request || "기록되지 않음"}</pre><h3>작업 요약 <span className="derived-label">파생 정보</span></h3><p>{detail.summary?.summary || "기록되지 않음"}</p><dl><dt>대화</dt><dd>{detail.messagesSummary?.count ?? 0}개</dd><dt>명령</dt><dd>{detail.commandsSummary?.count ?? 0}개</dd><dt>변경 파일</dt><dd>{detail.changedFilesSummary?.count ?? 0}개</dd><dt>테스트</dt><dd><Status value={detail.testsSummary?.status ?? "unknown"} kind="test" /></dd></dl></>;
  if (tab === "related") return <RelationPanel relations={detail.relations} onOpen={onOpen} onAction={onRelation} />;
  if (tab === "metadata") return <><MetadataTable value={detail.metadata} /><MetadataEditor detail={detail} onSave={onUpdate} /></>;
  if (!data) return <p className="muted">불러오는 중…</p>;
  if (!data.items.length) return <p className="empty-state">기록된 {TAB_LABELS[tab]} 자료가 없습니다.</p>;
  if (tab === "messages") return <div className="record-list">{data.items.map((item, index) => <details key={String(item.messageId ?? index)} open={index < 8}><summary><strong>{roleLabel(item.role)}</strong> · {String(item.createdAt ?? "시간 미상")}</summary><pre>{String(item.content ?? item.normalizedContent ?? "")}</pre></details>)}</div>;
  if (tab === "commands") return <div className="record-list">{data.items.map((item, index) => <details key={String(item.commandId ?? index)}><summary><code>{String(item.command ?? "명령")}</code> · Exit {String(item.exitCode ?? "-")} · <Status value={String(item.status ?? "unknown").toLowerCase()} kind="test" /></summary><p>작업 위치: <code>{String(item.workingDirectory ?? item.cwd ?? "%REPO_ROOT%")}</code></p><h4>stdout</h4><pre>{String(item.stdout ?? "")}</pre>{Boolean(item.stderr) && <><h4>stderr</h4><pre>{String(item.stderr)}</pre></>}</details>)}</div>;
  if (tab === "changed-files") return <div className="record-list">{data.items.map((item, index) => <article key={String(item.path ?? index)}><code>{String(item.path)}</code><span>{String(item.changeType ?? "unknown")} · +{String(item.addedLines ?? 0)} / -{String(item.deletedLines ?? 0)} · {String(item.attribution ?? "귀속 미상")}</span></article>)}</div>;
  if (tab === "tests") return <div className="record-list">{data.items.map((item, index) => <article key={String(item.testId ?? index)}><strong>{String(item.framework ?? item.tool ?? "테스트")}</strong><Status value={String(item.status ?? "unknown").toLowerCase()} kind="test" /><span>{String(item.passed ?? 0)} passed · {String(item.failed ?? 0)} failed · Exit {String(item.exitCode ?? "-")}</span></article>)}</div>;
  return <div className="record-list diff-list">{data.items.map((item, index) => <details key={String(item.name ?? index)}><summary>{String(item.name ?? "patch")} · {Number(item.size ?? 0).toLocaleString()} bytes{Boolean(item.truncated) ? " · 일부 표시" : ""}</summary><pre>{String(item.content ?? "")}</pre></details>)}</div>;
}

function CaptureFacts({ capture, metadata }: { capture: CaptureSummary; metadata: Record<string, unknown> }) {
  return <dl><dt>출처</dt><dd>{sourceLabel(capture.sourceType)}</dd><dt>기기</dt><dd>{deviceLabel(capture.captureDevice)}</dd><dt>저장 시각</dt><dd>{new Date(capture.capturedAt).toLocaleString()}</dd><dt>프로젝트</dt><dd>{capture.projectId || "없음"}</dd><dt>Vault 경로</dt><dd><code>{String(metadata.documentPath ?? "-")}</code></dd><dt>상태</dt><dd><Status value={capture.status} kind="capture" /></dd><dt>관계</dt><dd>{relationStatusLabel(capture.relationStatus)}</dd></dl>;
}

function RelationPanel({ relations, onOpen, onAction }: { relations: CaptureRelation[]; onOpen: (id: string) => Promise<void>; onAction: (relation: CaptureRelation, action: "confirm" | "reject" | "remove") => Promise<void> }) {
  const visible = relations.filter((item) => item.status !== "removed");
  return <section className="relation-panel"><h3>관련 Capture {visible.length}개</h3>{visible.length === 0 && <p className="muted">연결된 Capture 또는 후보가 없습니다.</p>}{visible.map((relation) => {
    const targetId = relation.direction === "out" ? relation.toCaptureId : relation.fromCaptureId;
    return <article key={relation.relationId} className={`relation-card relation-${relation.status}`}><strong>{relation.targetTitle || targetId}</strong><span>{relationStatusLabel(relation.status)} · 신뢰도 {confidenceLabel(relation.confidence)} · {matchMethodLabel(relation.matchMethod)}</span><small>{relation.evidence.matchedMessageId ? `일치 메시지 ${relation.evidence.matchedMessageId}` : "원문을 제외한 관계 근거"}</small><div><button onClick={() => void onOpen(targetId)}>열기</button>{relation.status === "suggested" && <><button onClick={() => void onAction(relation, "confirm")}>확정</button><button onClick={() => void onAction(relation, "reject")}>거절</button></>}{["confirmed", "stale"].includes(relation.status) && <button onClick={() => void onAction(relation, "remove")}>연결 해제</button>}</div></article>;
  })}</section>;
}

function MetadataEditor({ detail, onSave }: { detail: CaptureDetail; onSave: (value: Record<string, unknown>) => Promise<void> }) {
  const [title, setTitle] = useState(detail.capture.title);
  const [tags, setTags] = useState(detail.tags.join(", "));
  const [project, setProject] = useState(detail.capture.projectId ?? "");
  const [parent, setParent] = useState(String(detail.metadata.parentDocument ?? ""));
  const [note, setNote] = useState(detail.userNote ?? "");
  const [busy, setBusy] = useState(false);
  useEffect(() => { setTitle(detail.capture.title); setTags(detail.tags.join(", ")); setProject(detail.capture.projectId ?? ""); setParent(String(detail.metadata.parentDocument ?? "")); setNote(detail.userNote ?? ""); }, [detail]);
  return <section className="capture-editor"><h3>편집 가능한 정보</h3><label>제목<input value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>태그<input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="쉼표로 구분" /></label><label>프로젝트<input value={project} onChange={(event) => setProject(event.target.value)} placeholder="프로젝트 없음" /></label><label>상위 주제 문서 ID<input value={parent} onChange={(event) => setParent(event.target.value)} placeholder="상위 주제 없음" /></label><label>내 메모<textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} /></label><button disabled={busy} onClick={() => { setBusy(true); void onSave({ title, tags: tags.split(",").map((item) => item.trim()).filter(Boolean), projectId: project || null, parentDocument: parent || null, userNote: note }).finally(() => setBusy(false)); }}>{busy ? "저장 중…" : "메타데이터 저장"}</button><p className="read-only-note">원본 대화, 명령, Diff와 테스트 결과는 읽기 전용입니다.</p></section>;
}

function MetadataTable({ value }: { value: Record<string, unknown> }) {
  return <dl className="metadata-table">{Object.entries(value).map(([key, item]) => <><dt key={`${key}-key`}>{key}</dt><dd key={`${key}-value`}>{typeof item === "object" ? JSON.stringify(item) : String(item ?? "-")}</dd></>)}</dl>;
}

function Status({ value, kind }: { value: string; kind: "capture" | "test" }) { return <span className={`status status-${value}`}>{kind === "test" ? testStatusLabel(value) : captureStatusLabel(value)}</span>; }
function badgeLabel(item: CaptureSummary) { if (item.captureType === "development_session") return "Codex 전체 작업"; if (item.sourceType === "chatgpt") return "ChatGPT 답변"; if (item.sourceType === "codex") return "Codex 답변 단편"; return "일반 클립보드"; }
function sourceLabel(value: string) { return ({ chatgpt: "ChatGPT", codex: "Codex", general: "일반" } as Record<string, string>)[value] ?? value; }
function deviceLabel(value: string) { return value === "android" ? "Android" : value === "windows" ? "Windows" : value; }
function captureStatusLabel(value: string) { return ({ inbox: "Inbox", in_progress: "진행 중", completed: "완료", pending: "전송 대기", failed: "실패", quarantined: "격리" } as Record<string, string>)[value] ?? "알 수 없음"; }
function testStatusLabel(value: string) { return ({ passed: "통과", failed: "실패", partial: "부분 통과", skipped: "건너뜀", cancelled: "취소", timed_out: "시간 초과", none: "테스트 없음", unknown: "알 수 없음" } as Record<string, string>)[value] ?? value.toUpperCase(); }
function relationStatusLabel(value: string) { return ({ linked: "연결됨", confirmed: "연결됨", suggested: "후보", rejected: "거절됨", stale: "재검증 필요", removed: "해제됨", unlinked: "미연결" } as Record<string, string>)[value] ?? value; }
function confidenceLabel(value: string) { return ({ high: "높음", medium: "중간", low: "낮음" } as Record<string, string>)[value] ?? value; }
function matchMethodLabel(value: string) { return ({ exact_message_hash: "메시지 정확 일치", partial_content: "부분 본문 일치", contiguous_message_group: "연속 메시지 일치", manual: "사용자 연결" } as Record<string, string>)[value] ?? value; }
function roleLabel(value: unknown) { return ({ user: "사용자", assistant: "Codex", tool: "도구", system_summary: "진행", error: "오류" } as Record<string, string>)[String(value)] ?? "알 수 없음"; }
