import { useCallback, useEffect, useMemo, useState } from "react";

import { getDocument, getGraph, getTags, KnowledgeApiError, listSources, previewDocumentUpdate, reindexDocument, searchDocuments, updateDocument } from "./api";
import { createCombinedSource, isCombinedSource, mergeGraphs, mergeSearchResults, mergeTags } from "./combined";
import { GraphView } from "./GraphView";
import { DocumentEditor } from "./DocumentEditor";
import { LinkResolutionDialog } from "./LinkResolutionDialog";
import { CaptureWorkspace } from "./features/captures/CaptureWorkspace";
import { getCaptureBacklinks } from "./features/captures/api";
import type { CaptureSummary } from "./features/captures/types";
import type { CommandResult, DocumentDetail, DocumentUpdateRequest, KnowledgeGraph, KnowledgeSource, LinkOccurrence, SearchResult, TagCount } from "./types";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function App() {
  const [viewMode, setViewMode] = useState<"documents" | "captures">("documents");
  const [captureToOpen, setCaptureToOpen] = useState<string>();
  const [captureBacklinks, setCaptureBacklinks] = useState<Array<CaptureSummary & { relationType: string }>>([]);
  const [deepLink] = useState(() => {
    const parameters = new URLSearchParams(window.location.search);
    return {
      sourceId: parameters.get("sourceId") ?? "",
      documentId: parameters.get("documentId") ?? "",
    };
  });
  const [deepLinkHandled, setDeepLinkHandled] = useState(false);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [source, setSource] = useState<KnowledgeSource | null>(null);
  const [pendingSensitive, setPendingSensitive] = useState<KnowledgeSource | null>(null);
  const [confirmedSources, setConfirmedSources] = useState<Set<string>>(new Set());
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [tags, setTags] = useState<TagCount[]>([]);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [tag, setTag] = useState("");
  const [depth, setDepth] = useState(1);
  const [direction, setDirection] = useState("both");
  const [includeOrphans, setIncludeOrphans] = useState(true);
  const [includeBroken, setIncludeBroken] = useState(false);
  const [centered, setCentered] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [linkOccurrence, setLinkOccurrence] = useState<LinkOccurrence | null>(null);
  const [highlightedEdge, setHighlightedEdge] = useState<{ source: string; target: string } | null>(null);
  const [notice, setNotice] = useState("");
  const [indexRetry, setIndexRetry] = useState(false);

  const combinedSource = useMemo(() => createCombinedSource(sources), [sources]);
  const activeSources = useMemo(() => {
    if (!source) return [];
    return isCombinedSource(source) ? sources.filter((item) => item.enabled) : [source];
  }, [source, sources]);
  const confirmed = activeSources.every((item) => !item.sensitive || confirmedSources.has(item.id));
  const highlightedIds = useMemo(() => new Set(searchResults.map((item) => item.id)), [searchResults]);

  useEffect(() => {
    listSources()
      .then((items) => {
        setSources(items);
        const requested = items.find((item) => item.id === deepLink.sourceId && item.enabled);
        const fallback = items.find((item) => item.enabled && !item.sensitive) ?? null;
        if (requested?.sensitive) {
          setSource(fallback);
          setPendingSensitive(requested);
        } else {
          setSource(requested ?? fallback);
        }
      })
      .catch((reason: Error) => setError(reason.message));
  }, [deepLink.sourceId]);

  useEffect(() => {
    const protect = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", protect);
    return () => window.removeEventListener("beforeunload", protect);
  }, [dirty]);

  const mayDiscard = useCallback(() => !dirty || window.confirm("저장하지 않은 변경사항이 있습니다.\n변경을 버리시겠습니까?"), [dirty]);

  useEffect(() => {
    const captureInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    const clearInstallPrompt = () => setInstallPrompt(null);
    window.addEventListener("beforeinstallprompt", captureInstallPrompt);
    window.addEventListener("appinstalled", clearInstallPrompt);
    return () => {
      window.removeEventListener("beforeinstallprompt", captureInstallPrompt);
      window.removeEventListener("appinstalled", clearInstallPrompt);
    };
  }, []);

  const installApp = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };

  const loadGraph = useCallback(async () => {
    if (!source || !source.enabled || !confirmed) return;
    setLoading(true);
    try {
      setError("");
      const centeredSource = centered && detail
        ? sources.find((item) => item.id === detail.sourceId)
        : undefined;
      const graphSources = centeredSource ? [centeredSource] : activeSources;
      const [nextGraphs, nextTagGroups] = await Promise.all([
        Promise.all(graphSources.map((item) => getGraph(item.id, {
          tag: !centered && tag ? tag : undefined,
          includeOrphans: !centered ? includeOrphans : undefined,
          includeBroken: isCombinedSource(source) ? true : includeBroken,
          confirmSensitive: item.sensitive,
          documentId: centered ? detail?.id : undefined,
          depth,
          direction,
        }))),
        Promise.all(activeSources.map((item) => getTags(item.id, item.sensitive))),
      ]);
      setGraph(isCombinedSource(source) ? mergeGraphs(nextGraphs, source, includeBroken) : nextGraphs[0]);
      setTags(isCombinedSource(source) ? mergeTags(nextTagGroups) : nextTagGroups[0]);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, [activeSources, centered, confirmed, depth, detail, direction, includeBroken, includeOrphans, source, tag]);

  useEffect(() => { void loadGraph(); }, [loadGraph]);

  useEffect(() => {
    const trimmed = query.trim();
    if (!source || !trimmed || !confirmed) {
      setSearchResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      Promise.all(activeSources.map((item) => searchDocuments(trimmed, item.id, tag, item.sensitive)))
        .then((results) => setSearchResults(mergeSearchResults(results)))
        .catch((reason: Error) => setError(reason.message));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [activeSources, confirmed, query, source, tag]);

  const resetSourceState = (selected: KnowledgeSource) => {
    setSource(selected);
    setGraph(null);
    setDetail(null);
    setSearchResults([]);
    setQuery("");
    setTag("");
    setCentered(false);
    setEditing(false);
    setDirty(false);
    setHighlightedEdge(null);
  };

  const selectSource = (selected: KnowledgeSource) => {
    if (!mayDiscard()) return;
    if (!selected.enabled) return;
    const lockedSensitiveSource = (isCombinedSource(selected) ? sources : [selected])
      .some((item) => item.sensitive && !confirmedSources.has(item.id));
    if (lockedSensitiveSource) {
      setPendingSensitive(selected);
      return;
    }
    resetSourceState(selected);
  };

  const confirmSensitive = () => {
    if (!pendingSensitive) return;
    setConfirmedSources((current) => {
      const next = new Set(current);
      const selectedSources = isCombinedSource(pendingSensitive) ? sources : [pendingSensitive];
      selectedSources.filter((item) => item.sensitive).forEach((item) => next.add(item.id));
      return next;
    });
    resetSourceState(pendingSensitive);
    setPendingSensitive(null);
  };

  const selectNode = useCallback(async (documentId: string, center = false, documentSourceId?: string) => {
    if (!source) return;
    if (!mayDiscard()) return;
    const sourceId = documentSourceId
      ?? graph?.nodes.find((node) => node.id === documentId)?.sourceId
      ?? detail?.sourceId
      ?? source.id;
    const documentSource = sources.find((item) => item.id === sourceId);
    try {
      const nextDetail = await getDocument(sourceId, documentId, documentSource?.sensitive ?? false);
      setDetail(nextDetail);
      getCaptureBacklinks(documentId)
        .then((result) => setCaptureBacklinks(result.items))
        .catch(() => setCaptureBacklinks([]));
      setEditing(false);
      setDirty(false);
      if (center) setCentered(true);
    } catch (reason) {
      setError((reason as Error).message);
    }
  }, [detail?.sourceId, graph?.nodes, mayDiscard, source, sources]);

  useEffect(() => {
    if (
      deepLinkHandled
      || !deepLink.documentId
      || !source
      || source.id !== deepLink.sourceId
      || !confirmed
    ) return;
    setDeepLinkHandled(true);
    void selectNode(deepLink.documentId, true, deepLink.sourceId);
  }, [confirmed, deepLink, deepLinkHandled, selectNode, source]);

  const saveDocument = async (request: DocumentUpdateRequest) => {
    if (!detail) return;
    try {
      const result = await updateDocument(detail.sourceId, detail.id, request);
      if (result.indexing.status === "failed") {
        setNotice("문서는 저장되었습니다. 색인 갱신에 실패했습니다. 서버에서 다시 색인해 주세요.");
        setIndexRetry(true);
      } else {
        setNotice("문서를 저장하고 그래프를 갱신했습니다.");
        setIndexRetry(false);
      }
      setDirty(false);
      setEditing(false);
      const documentSource = sources.find((item) => item.id === detail.sourceId);
      setDetail(await getDocument(detail.sourceId, detail.id, documentSource?.sensitive ?? false));
      await loadGraph();
    } catch (reason) {
      const apiError = reason as KnowledgeApiError;
      setError(apiError.code === "DOCUMENT_CONFLICT" ? "다른 프로그램에서 문서가 변경되었습니다. 최신 내용을 다시 불러오세요." : apiError.message);
      throw apiError;
    }
  };

  const linkSaved = async (result: CommandResult) => {
    setLinkOccurrence(null);
    setNotice(result.indexing.status === "completed" ? "링크를 연결하고 그래프를 갱신했습니다." : "링크는 저장했지만 색인 갱신에 실패했습니다.");
    setIndexRetry(result.indexing.status === "failed");
    if (detail) {
      const documentSource = sources.find((item) => item.id === detail.sourceId);
      setDetail(await getDocument(detail.sourceId, detail.id, documentSource?.sensitive ?? false));
    }
    await loadGraph();
  };

  const retryIndex = async () => {
    if (!detail) return;
    try {
      const documentSource = sources.find((item) => item.id === detail.sourceId);
      await reindexDocument(detail.sourceId, detail.id, documentSource?.sensitive ?? false);
      setIndexRetry(false);
      setNotice("색인과 그래프를 다시 갱신했습니다.");
      setDetail(await getDocument(detail.sourceId, detail.id, documentSource?.sensitive ?? false));
      await loadGraph();
    } catch (reason) { setError((reason as Error).message); }
  };

  const reloadLatestDocument = async () => {
    if (!detail) return;
    const documentSource = sources.find((item) => item.id === detail.sourceId);
    await reindexDocument(detail.sourceId, detail.id, documentSource?.sensitive ?? false);
    const latest = await getDocument(detail.sourceId, detail.id, documentSource?.sensitive ?? false);
    setDetail(latest);
    setDirty(false);
    setError("");
    setNotice("최신 문서를 다시 불러왔습니다. 기존 편집 내용은 저장되지 않았습니다.");
    await loadGraph();
  };

  return (
    <main>
      <header>
        <div><span className="eyebrow">LOCAL · EXPLICIT SAVE</span><h1>MDE Knowledge Viewer</h1></div>
        <div className="header-actions">
          <nav className="primary-navigation" aria-label="통합 자료 탐색">
            <button className={viewMode === "documents" ? "active" : ""} onClick={() => setViewMode("documents")}>문서</button>
            <button className={viewMode === "captures" ? "active" : ""} onClick={() => setViewMode("captures")}>Capture</button>
          </nav>
          {installPrompt && <button className="install-app" onClick={() => void installApp()}>앱 설치</button>}
          <div className="stats">{viewMode === "captures" ? "통합 Capture Viewer" : loading ? "불러오는 중…" : graph ? `${graph.returnedDocumentCount} 문서 · ${graph.edges.length} 연결` : "대기 중"}</div>
        </div>
      </header>
      {viewMode === "captures" ? <CaptureWorkspace initialCaptureId={captureToOpen} /> : <>
      {error && <div className="error" role="alert">{error}<button aria-label="오류 닫기" onClick={() => setError("")}>×</button></div>}
      {notice && <div className="notice" role="status">{notice}{indexRetry && <button className="retry-index" onClick={() => void retryIndex()}>다시 색인</button>}<button aria-label="알림 닫기" onClick={() => setNotice("")}>×</button></div>}
      {graph?.truncated && <div className="warning">전체 {graph.totalDocumentCount.toLocaleString()}개 문서 중 연결도가 높은 {graph.returnedDocumentCount.toLocaleString()}개를 표시합니다.</div>}
      <div className="workspace">
        <aside className="sidebar">
          <h2>Source</h2>
          <div className="source-list">
            {combinedSource && (
              <button className={source?.id === combinedSource.id ? "active" : ""} onClick={() => selectSource(combinedSource)}>
                <strong>{combinedSource.name}</strong><small>통합 보기 · {combinedSource.documentCount}개 · 민감 포함</small>
              </button>
            )}
            {sources.map((item) => (
              <button disabled={!item.enabled} className={source?.id === item.id ? "active" : ""} key={item.id} onClick={() => selectSource(item)}>
                <strong>{item.name}</strong><small>{item.category} · {item.documentCount}개{item.sensitive ? " · 민감" : ""}{!item.enabled ? " · 비활성" : ""}</small>
              </button>
            ))}
          </div>
          <h2>탐색</h2>
          <label>검색<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="제목 또는 본문" /></label>
          {searchResults.length > 0 && <div className="search-results" aria-label="검색 결과">{searchResults.map((item) => <button key={item.id} onClick={() => void selectNode(item.id, true, item.sourceId)}><strong>{item.title}</strong><small>{item.relativePath}</small><span>{item.snippet}</span></button>)}</div>}
          <label>태그<select value={tag} onChange={(event) => setTag(event.target.value)}><option value="">전체</option>{tags.map((item) => <option key={item.name} value={item.name}>#{item.name} ({item.documentCount})</option>)}</select></label>
          {centered && <><label>깊이<select value={depth} onChange={(event) => setDepth(Number(event.target.value))}>{[1, 2, 3].map((item) => <option key={item} value={item}>{item}단계</option>)}</select></label><label>방향<select value={direction} onChange={(event) => setDirection(event.target.value)}><option value="both">모든 연결</option><option value="outgoing">이 문서가 참조하는 문서</option><option value="incoming">이 문서를 참조하는 문서</option></select></label></>}
          {!centered && <label className="check"><input type="checkbox" checked={includeOrphans} onChange={(event) => setIncludeOrphans(event.target.checked)} />고아 문서 표시</label>}
          <label className="check"><input type="checkbox" checked={includeBroken} onChange={(event) => setIncludeBroken(event.target.checked)} />끊어진 링크 표시</label>
        </aside>
        <section className="graph-panel">
          <div className="mode-bar"><button className={!centered ? "active" : ""} onClick={() => { if (mayDiscard()) setCentered(false); }}>전체 그래프</button><button disabled={!detail} className={centered ? "active" : ""} onClick={() => { if (mayDiscard()) setCentered(true); }}>문서 중심</button></div>
          <GraphView graph={graph} centered={centered} selectedId={detail?.id} highlightedIds={highlightedIds} highlightedEdge={highlightedEdge} onSelectNode={(id, sourceId) => void selectNode(id, false, sourceId)} />
        </section>
        <aside className="detail-panel">
          <h2>문서 상세</h2>
          {!detail ? <p className="muted">그래프의 문서를 선택하세요.</p> : editing ? <DocumentEditor
            key={`${detail.id}:${detail.contentHash}`}
            document={detail}
            sourceName={sources.find((item) => item.id === detail.sourceId)?.name ?? detail.sourceId}
            sensitive={sources.find((item) => item.id === detail.sourceId)?.sensitive ?? false}
            linkSources={sources}
            onDirtyChange={setDirty}
            onCancel={() => { if (mayDiscard()) { setEditing(false); setDirty(false); } }}
            onPreview={(request) => previewDocumentUpdate(detail.sourceId, detail.id, request)}
            onSave={saveDocument}
            onReload={reloadLatestDocument}
          /> : <>
            <div className="detail-mode"><button className="active">보기</button><button disabled={!detail.editable} onClick={() => setEditing(true)}>편집</button></div>
            <h3>{detail.title}</h3><code>{detail.relativePath}</code><button className="copy" onClick={() => void navigator.clipboard.writeText(detail.relativePath)}>경로 복사</button>
            <p className="metadata">{sources.find((item) => item.id === detail.sourceId)?.name ?? source?.name} · {detail.category}<br />수정 {new Date(detail.modifiedAt).toLocaleString()}</p>
            <div className="tag-row">{detail.tags.map((item) => <span key={item}>#{item}</span>)}</div>
            {detail.aliases.length > 0 && <p className="metadata">별칭: {detail.aliases.join(", ")}</p>}
            {!detail.editable && <p className="read-only-note">이 자료 공간은 읽기 전용입니다.<br />문서는 조회할 수 있지만 편집할 수 없습니다.</p>}
            <button className="center-action" onClick={() => { if (mayDiscard()) setCentered(true); }}>이 문서 중심으로 보기</button>
            <LinkList title="이 문서가 참조하는 문서" items={detail.outgoingLinks} onSelect={(item, center) => { setHighlightedEdge({ source: detail.id, target: item.documentId }); return selectNode(item.documentId, center, item.sourceId); }} />
            <LinkList title="이 문서를 참조하는 문서" items={detail.incomingLinks} onSelect={(item, center) => { setHighlightedEdge({ source: item.documentId, target: detail.id }); return selectNode(item.documentId, center, item.sourceId); }} />
            {captureBacklinks.length > 0 && <section className="link-list"><h4>이 문서를 참조하는 Capture {captureBacklinks.length}개</h4>{captureBacklinks.map((item) => <button key={item.captureId} onClick={() => { setCaptureToOpen(item.captureId); setViewMode("captures"); }}><strong>{item.title}</strong><small>{item.captureType === "development_session" ? "Codex 전체 작업" : item.sourceType === "chatgpt" ? "ChatGPT 답변" : item.sourceType === "codex" ? "Codex 답변 단편" : "일반 클립보드"} · {item.relationType === "parent_of" ? "상위 주제" : "Capture 문서"}</small></button>)}</section>}
            <UnresolvedLinks items={detail.unresolvedLinkOccurrences ?? []} allowRewrite={detail.editable && (sources.find((item) => item.id === detail.sourceId)?.allowLinkRewrite ?? false)} onResolve={setLinkOccurrence} />
            <TextList title="후보가 여러 개인 링크" items={detail.ambiguousLinks} />
            <h4>미리보기</h4><pre>{detail.preview}</pre>
          </>}
        </aside>
      </div>
      {pendingSensitive && <div className="dialog-backdrop"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="sensitive-title"><h2 id="sensitive-title">민감 Source 열기</h2><p><strong>{pendingSensitive.name}</strong>에 포함된 민감 자료를 화면에 표시합니다.</p><p>편집이 허용된 문서는 명시적으로 저장할 때만 원본 Markdown에 반영됩니다.</p><div><button onClick={() => setPendingSensitive(null)}>취소</button><button className="confirm" onClick={confirmSensitive}>열기</button></div></section></div>}
      {linkOccurrence && detail && <LinkResolutionDialog document={detail} occurrence={linkOccurrence} sensitive={sources.find((item) => item.id === detail.sourceId)?.sensitive ?? false} onClose={() => setLinkOccurrence(null)} onSaved={linkSaved} />}
      </>}
    </main>
  );
}

function LinkList({ title, items, onSelect }: { title: string; items: { documentId: string; sourceId: string; title: string }[]; onSelect: (item: { documentId: string; sourceId: string; title: string }, center?: boolean) => Promise<void> }) {
  return <section className="link-list"><h4>{title} {items.length}개</h4>{items.map((item) => <button key={item.documentId} onClick={() => void onSelect(item, true)}>{item.title}</button>)}</section>;
}

function TextList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return <section className="link-list"><h4>{title} {items.length}개</h4>{items.map((item) => <span key={item}>{item}</span>)}</section>;
}

function UnresolvedLinks({ items, allowRewrite, onResolve }: { items: LinkOccurrence[]; allowRewrite: boolean; onResolve: (item: LinkOccurrence) => void }) {
  if (!items.length) return null;
  return <section className="link-list"><h4>연결되지 않은 링크 {items.length}개</h4>{items.map((item) => <div className="unresolved-item" key={item.id}><span>{item.target}<small>{item.line}행 · {item.contextPreview}</small></span>{allowRewrite && <button onClick={() => onResolve(item)}>연결</button>}</div>)}</section>;
}
