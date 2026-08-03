import cytoscape, { type Core } from "cytoscape";
import { useEffect, useRef, useState } from "react";

import type { CaptureGraphData } from "./types";

interface Props {
  graph: CaptureGraphData | null;
  onOpenCapture: (captureId: string) => void;
}

const COLORS: Record<string, string> = {
  DOCUMENT: "#4f7cff", PROJECT: "#9b59b6", CLIPBOARD_CAPTURE: "#2f9e72",
  DEVELOPMENT_SESSION: "#e07824", FILE: "#697386", COMMAND: "#40536d", TEST_RESULT: "#c14545",
};

export function CaptureGraph({ graph, onOpenCapture }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (!container.current || !graph) return;
    const labels = new Map(graph.nodes.map((node) => [node.id, node.label]));
    const next = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({ data: { id: node.id, label: node.label, type: node.type, color: COLORS[node.type] } })),
        ...graph.edges.map((edge) => ({ data: { id: edge.id, source: edge.from, target: edge.to, relationType: edge.type, candidate: edge.status !== "confirmed" } })),
      ],
      style: [
        { selector: "node", style: { "background-color": "data(color)", label: "data(label)", color: "#17213d", "font-size": "11px", "text-background-color": "#fff", "text-background-opacity": .9, "text-background-padding": "3px", "text-valign": "bottom", "text-margin-y": 7 } },
        { selector: "edge", style: { width: 1.5, "line-color": "#9aa7c7", "target-arrow-color": "#9aa7c7", "target-arrow-shape": "triangle", "curve-style": "bezier" } },
        { selector: "edge[?candidate]", style: { "line-style": "dashed", "line-color": "#d18a27", "target-arrow-color": "#d18a27" } },
      ],
      layout: { name: "cose", animate: false, fit: true, padding: 36 },
    });
    next.on("tap", "node", (event) => {
      const type = String(event.target.data("type"));
      if (type === "CLIPBOARD_CAPTURE" || type === "DEVELOPMENT_SESSION") onOpenCapture(event.target.id());
      else setDescription(`${typeLabel(type)} 노드, ${event.target.data("label")}`);
    });
    next.on("tap", "edge", (event) => {
      setDescription(`${labels.get(event.target.data("source")) ?? "자료"}에서 ${labels.get(event.target.data("target")) ?? "자료"}로 향하는 ${relationLabel(event.target.data("relationType"))} 관계`);
    });
    instance.current = next;
    return () => { instance.current = null; next.destroy(); };
  }, [graph, onOpenCapture]);

  return <div className="capture-graph-shell">
    <div ref={container} className="capture-graph-canvas" aria-label="Capture 지식 그래프" />
    {description && <p className="graph-description" aria-live="polite">{description}</p>}
  </div>;
}

function typeLabel(type: string) {
  return ({ DOCUMENT: "문서", PROJECT: "프로젝트", FILE: "파일", COMMAND: "명령", TEST_RESULT: "테스트" } as Record<string, string>)[type] ?? "Capture";
}

function relationLabel(type: string) {
  return ({ parent_of: "상위 주제", references: "문서 참조", belongs_to_project: "프로젝트 소속", excerpt_of: "전체 세션 포함", changed_file: "파일 변경", executed_command: "명령 실행", tested_by: "테스트" } as Record<string, string>)[type] ?? type;
}
