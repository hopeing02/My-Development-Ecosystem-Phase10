import { useEffect, useMemo, useState } from "react";

import { searchDocuments } from "./api";
import type { ChangePreview, DocumentDetail, DocumentUpdateRequest, KnowledgeSource, SearchResult } from "./types";

interface Props {
  document: DocumentDetail;
  sourceName: string;
  sensitive: boolean;
  linkSources: KnowledgeSource[];
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onPreview: (request: DocumentUpdateRequest) => Promise<ChangePreview>;
  onSave: (request: DocumentUpdateRequest) => Promise<void>;
  onReload: () => Promise<void>;
}

export function DocumentEditor({ document, sourceName, sensitive, linkSources, onCancel, onDirtyChange, onPreview, onSave, onReload }: Props) {
  const [title, setTitle] = useState(document.title);
  const [tags, setTags] = useState(document.tags.join(", "));
  const [aliases, setAliases] = useState(document.aliases.join(", "));
  const [body, setBody] = useState(document.body);
  const [preview, setPreview] = useState<ChangePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [linkQuery, setLinkQuery] = useState("");
  const [linkSourceId, setLinkSourceId] = useState(document.sourceId);
  const [linkResults, setLinkResults] = useState<SearchResult[]>([]);
  const [conflict, setConflict] = useState(false);
  const values = useMemo(() => ({
    expectedContentHash: document.contentHash,
    title,
    tags: tags.split(",").map((item) => item.trim()).filter(Boolean),
    aliases: aliases.split(",").map((item) => item.trim()).filter(Boolean),
    body,
    createBackup: true,
    confirmSensitive: sensitive,
  }), [aliases, body, document.contentHash, sensitive, tags, title]);
  const dirty = title !== document.title || tags !== document.tags.join(", ") || aliases !== document.aliases.join(", ") || body !== document.body;
  const bodyLinks = useMemo(() => extractBodyLinks(body), [body]);
  const selectableLinkSources = useMemo(
    () => linkSources.filter((item) => item.id === document.sourceId || item.allowAsSharedLinkTarget),
    [document.sourceId, linkSources],
  );
  const linkSource = selectableLinkSources.find((item) => item.id === linkSourceId)
    ?? selectableLinkSources[0];

  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);

  useEffect(() => {
    const query = linkQuery.trim();
    if (!query) {
      setLinkResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      if (!linkSource) return;
      searchDocuments(query, linkSource.id, "", linkSource.sensitive)
        .then((items) => setLinkResults(items.filter((item) => item.id !== document.id)))
        .catch((reason: Error) => setError(reason.message));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [document.id, linkQuery, linkSource]);

  const loadPreview = async () => {
    setBusy(true);
    setError("");
    try { setPreview(await onPreview(values)); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  };
  const save = async () => {
    setBusy(true);
    setError("");
    try { await onSave(values); }
    catch (reason) {
      if ((reason as { code?: string }).code === "DOCUMENT_CONFLICT") {
        setConflict(true);
      } else {
        setError((reason as Error).message);
      }
    }
    finally { setBusy(false); }
  };

  const addLink = (target: SearchResult) => {
    const path = target.relativePath.replace(/\.md$/i, "");
    const prefix = target.sourceId === document.sourceId ? "" : `${linkSource?.name ?? target.sourceId}::`;
    const link = `[[${prefix}${path}|${target.title}]]`;
    const separator = body.length === 0 || body.endsWith("\n") ? "" : "\n";
    setBody(`${body}${separator}${link}\n`);
    setLinkQuery("");
    setLinkResults([]);
  };

  const deleteLink = (link: BodyLink) => {
    setBody(body.slice(0, link.startOffset) + body.slice(link.endOffset));
  };

  const copyDraft = async () => {
    const draft = `제목: ${title}\n태그: ${tags}\n별칭: ${aliases}\n\n${body}`;
    try {
      await navigator.clipboard.writeText(draft);
      setError("현재 변경 내용을 클립보드에 복사했습니다.");
      setConflict(false);
    } catch {
      setError("클립보드에 복사할 수 없습니다. 본문을 직접 선택해 복사해 주세요.");
    }
  };

  const reloadLatest = async () => {
    setBusy(true);
    setError("");
    try {
      await onReload();
      setConflict(false);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return <section className="document-editor">
    <div className="editor-heading"><h3>문서 편집</h3><span>Markdown</span></div>
    <label>제목<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
    <label>태그 <small>쉼표로 구분</small><input value={tags} onChange={(event) => setTags(event.target.value)} /></label>
    <label>별칭 <small>쉼표로 구분</small><input value={aliases} onChange={(event) => setAliases(event.target.value)} /></label>
    <label>본문<textarea value={body} onChange={(event) => setBody(event.target.value)} rows={18} /></label>
    <section className="editor-links">
      <h4>본문 링크 {bodyLinks.length}개</h4>
      {bodyLinks.length === 0 && <p className="muted">본문에 링크가 없습니다.</p>}
      {bodyLinks.map((link) => <div className="editor-link-item" key={`${link.startOffset}:${link.rawText}`}><span><strong>{link.label}</strong><code>{link.rawText}</code></span><button onClick={() => deleteLink(link)}>삭제</button></div>)}
      <div className="source-scope"><strong>검색 Source</strong><select aria-label="링크 검색 Source" value={linkSource?.id ?? ""} onChange={(event) => { setLinkSourceId(event.target.value); setLinkQuery(""); setLinkResults([]); }}>{selectableLinkSources.map((item) => <option key={item.id} value={item.id}>{item.name}{item.allowAsSharedLinkTarget && item.id !== document.sourceId ? " (공통)" : ""}</option>)}</select><small>현재 Source와 허용된 공통 Source만 연결할 수 있습니다.</small></div>
      <label>링크 추가 <small>{linkSource?.name ?? sourceName} 안의 기존 문서를 검색합니다.</small><input value={linkQuery} onChange={(event) => setLinkQuery(event.target.value)} placeholder={`${linkSource?.name ?? sourceName} 문서 검색`} /></label>
      {linkResults.length > 0 && <div className="editor-link-results">{linkResults.map((item) => <button key={item.id} onClick={() => addLink(item)}><strong>{item.title}</strong><small>{item.relativePath}</small><span>추가</span></button>)}</div>}
    </section>
    <h4>렌더링 미리보기</h4><pre>{body}</pre>
    {error && <p className="editor-error" role="alert">{error}</p>}
    <div className="editor-actions"><button onClick={() => void loadPreview()} disabled={!dirty || busy}>변경 미리보기</button><button onClick={onCancel} disabled={busy}>취소</button><button className="primary" onClick={() => void save()} disabled={!dirty || busy}>저장</button></div>
    {preview && <ChangePreviewDialog preview={preview} onClose={() => setPreview(null)} onSave={() => void save()} busy={busy} />}
    {conflict && <ConflictDialog busy={busy} onReload={() => void reloadLatest()} onCopy={() => void copyDraft()} onClose={() => setConflict(false)} />}
  </section>;
}

function ConflictDialog({ busy, onReload, onCopy, onClose }: { busy: boolean; onReload: () => void; onCopy: () => void; onClose: () => void }) {
  return <div className="dialog-backdrop"><section className="dialog conflict-dialog" role="dialog" aria-modal="true" aria-labelledby="conflict-title">
    <h2 id="conflict-title">다른 프로그램에서 문서가 변경되었습니다</h2>
    <p>현재 편집본은 저장되지 않았습니다. 최신 파일을 재색인해 다시 불러오거나, 내 변경 내용을 먼저 복사할 수 있습니다.</p>
    <div><button onClick={onClose}>계속 편집</button><button onClick={onCopy}>내 변경 내용 복사</button><button className="confirm" disabled={busy} onClick={onReload}>최신 내용 다시 불러오기</button></div>
  </section></div>;
}

interface BodyLink {
  rawText: string;
  label: string;
  startOffset: number;
  endOffset: number;
}

function extractBodyLinks(body: string): BodyLink[] {
  let masked = body;
  for (const pattern of [/```[\s\S]*?```|~~~[\s\S]*?~~~/g, /`(?:\\`|[^`])*?`/g]) {
    masked = masked.replace(pattern, (value) => " ".repeat(value.length));
  }
  const links: BodyLink[] = [];
  const pattern = /\[\[([^\]]+)\]\]|\[([^\]]*)\]\(([^)]+)\)/g;
  for (const match of masked.matchAll(pattern)) {
    const startOffset = match.index ?? 0;
    if (startOffset > 0 && body[startOffset - 1] === "!") continue;
    const rawText = body.slice(startOffset, startOffset + match[0].length);
    const wikiLabel = match[1]?.split("|", 2)[1] ?? match[1]?.split("#", 1)[0];
    const label = wikiLabel || match[2] || match[3] || rawText;
    links.push({ rawText, label, startOffset, endOffset: startOffset + match[0].length });
  }
  return links;
}

function ChangePreviewDialog({ preview, onClose, onSave, busy }: { preview: ChangePreview; onClose: () => void; onSave: () => void; busy: boolean }) {
  return <div className="dialog-backdrop"><section className="dialog change-preview" role="dialog" aria-modal="true" aria-labelledby="change-preview-title">
    <h2 id="change-preview-title">변경 내용</h2>
    <dl><dt>제목 이전</dt><dd>{preview.before.title}</dd><dt>제목 이후</dt><dd>{preview.after.title}</dd><dt>태그</dt><dd>{preview.after.tags.join(", ") || "없음"}</dd><dt>별칭</dt><dd>{preview.after.aliases.join(", ") || "없음"}</dd><dt>본문 변경 줄</dt><dd>{preview.bodyChangedLineCount}</dd><dt>추가 링크</dt><dd>{preview.linksAdded.join(", ") || "없음"}</dd><dt>삭제 링크</dt><dd>{preview.linksRemoved.join(", ") || "없음"}</dd></dl>
    <div><button onClick={onClose}>계속 편집</button><button className="confirm" disabled={busy} onClick={onSave}>저장</button></div>
  </section></div>;
}
