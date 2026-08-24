import { useEffect, useState } from "react";

import { resolveLink, searchDocuments } from "./api";
import type { CommandResult, DocumentDetail, LinkOccurrence, SearchResult } from "./types";

interface Props {
  document: DocumentDetail;
  occurrence: LinkOccurrence;
  sensitive: boolean;
  onClose: () => void;
  onSaved: (result: CommandResult) => Promise<void>;
}

export function LinkResolutionDialog({ document, occurrence, sensitive, onClose, onSaved }: Props) {
  const [query, setQuery] = useState(occurrence.target);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [preview, setPreview] = useState<{ before: string; after: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      searchDocuments(query || occurrence.target, document.sourceId, "", sensitive)
        .then((items) => setResults(items.filter((item) => item.id !== document.id)))
        .catch(() => setResults([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [document.id, document.sourceId, occurrence.target, query, sensitive]);

  const request = (previewOnly: boolean) => ({ expectedContentHash: document.contentHash, linkOccurrenceId: occurrence.id, targetDocumentId: selected!.id, linkStyle: "preserve" as const, createBackup: true, confirmSensitive: sensitive, previewOnly });
  const showPreview = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const result = await resolveLink(document.sourceId, document.id, request(true));
      if ("preview" in result) setPreview(result.preview);
    } finally { setBusy(false); }
  };
  const save = async () => {
    if (!selected) return;
    setBusy(true);
    try { await onSaved(await resolveLink(document.sourceId, document.id, request(false)) as CommandResult); } finally { setBusy(false); }
  };

  return <div className="dialog-backdrop"><section className="dialog link-resolution" role="dialog" aria-modal="true" aria-labelledby="link-title">
    <h2 id="link-title">“{occurrence.target}”을 연결할 문서 선택</h2>
    <p className="metadata">{occurrence.line}행 · {occurrence.contextPreview}</p>
    <input aria-label="연결 대상 검색" value={query} onChange={(event) => setQuery(event.target.value)} />
    <div className="target-results">{results.map((item) => <button className={selected?.id === item.id ? "selected" : ""} key={item.id} onClick={() => { setSelected(item); setPreview(null); }}><strong>{item.title}</strong><small>{item.relativePath}</small></button>)}</div>
    {preview && <div className="link-preview"><strong>변경 전</strong><code>{preview.before}</code><strong>변경 후</strong><code>{preview.after}</code></div>}
    <div><button onClick={onClose}>취소</button>{!preview ? <button className="confirm" disabled={!selected || busy} onClick={() => void showPreview()}>변경 미리보기</button> : <button className="confirm" disabled={busy} onClick={() => void save()}>선택 문서에 연결</button>}</div>
  </section></div>;
}
