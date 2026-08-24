import cytoscape, { type Core } from "cytoscape";
import { useEffect, useRef, useState } from "react";

import type { KnowledgeGraph } from "./types";

interface GraphViewProps {
  graph: KnowledgeGraph | null;
  centered: boolean;
  selectedId?: string;
  highlightedIds: Set<string>;
  highlightedEdge?: { source: string; target: string } | null;
  onSelectNode: (id: string, sourceId: string) => void;
}

export function GraphView({ graph, centered, selectedId, highlightedIds, highlightedEdge, onSelectNode }: GraphViewProps) {
  const container = useRef<HTMLDivElement>(null);
  const graphInstance = useRef<Core | null>(null);
  const [edgeMessage, setEdgeMessage] = useState("");

  useEffect(() => {
    if (!container.current || !graph) return;
    const titles = new Map(graph.nodes.map((node) => [node.id, node.title]));
    const brokenNodes = graph.brokenEdges.map((edge) => ({
      data: {
        id: `broken-${edge.id}`,
        label: edge.resolutionStatus === "ambiguous" ? `후보 여러 개: ${edge.target}` : `대상 없음: ${edge.target}`,
        broken: true,
        rawTarget: edge.target,
        resolutionStatus: edge.resolutionStatus,
      },
    }));
    const instance = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({
          data: {
            id: node.id,
            sourceId: node.sourceId,
            label: node.title,
            degree: node.incomingCount + node.outgoingCount,
            orphan: node.isOrphan,
            selected: node.id === selectedId,
            highlighted: highlightedIds.has(node.id),
          },
        })),
        ...brokenNodes,
        ...graph.edges.map((edge) => ({ data: { ...edge, highlighted: highlightedEdge?.source === edge.source && highlightedEdge?.target === edge.target } })),
        ...graph.brokenEdges.map((edge) => ({
          data: { id: `broken-edge-${edge.id}`, source: edge.sourceDocumentId, target: `broken-${edge.id}`, broken: true },
        })),
      ],
      style: [
        { selector: "node", style: { "background-color": "#4f7cff", width: "mapData(degree, 0, 20, 24, 54)", height: "mapData(degree, 0, 20, 24, 54)", color: "#17213d", label: "data(label)", "font-size": "11px", "text-background-color": "#ffffff", "text-background-opacity": 0.9, "text-background-padding": "3px", "text-valign": "bottom", "text-margin-y": 7 } },
        { selector: "node[?orphan]", style: { "background-color": "#97a1b7" } },
        { selector: 'node[sourceId = "ks-002"]', style: { "background-color": "#9b59b6" } },
        { selector: "node[?highlighted]", style: { "border-width": 5, "border-color": "#ffb020" } },
        { selector: "node[?selected]", style: { "border-width": 5, "border-color": "#173b8f" } },
        { selector: "node[?broken]", style: { shape: "round-rectangle", "background-color": "#fff0f0", "border-width": 2, "border-style": "dashed", "border-color": "#c14545", color: "#8d1c1c" } },
        { selector: "edge", style: { width: 1.5, "line-color": "#9aa7c7", "target-arrow-color": "#9aa7c7", "target-arrow-shape": "triangle", "curve-style": "bezier" } },
        { selector: "edge[?highlighted]", style: { width: 4, "line-color": "#ff8a00", "target-arrow-color": "#ff8a00" } },
        { selector: "edge[?broken]", style: { "line-style": "dashed", "line-color": "#c14545", "target-arrow-color": "#c14545" } },
      ],
      layout: { name: centered ? "breadthfirst" : "cose", directed: centered, animate: false, fit: true, padding: 40 },
    });
    instance.on("tap", "node", (event) => {
      if (!event.target.data("broken")) onSelectNode(event.target.id(), event.target.data("sourceId"));
      else setEdgeMessage(event.target.data("resolutionStatus") === "ambiguous" ? `후보가 여러 개인 링크: ${event.target.data("rawTarget")}` : `대상이 없는 링크: ${event.target.data("rawTarget")}`);
    });
    instance.on("tap", "edge", (event) => {
      const source = titles.get(event.target.data("source")) ?? "문서";
      const target = titles.get(event.target.data("target")) ?? event.target.data("target");
      setEdgeMessage(`${source} 문서가 ${target} 문서를 참조합니다.`);
    });
    graphInstance.current = instance;
    return () => { graphInstance.current = null; instance.destroy(); };
  }, [centered, graph, highlightedEdge, highlightedIds, onSelectNode, selectedId]);

  return (
    <div className="graph-shell">
      <div className="graph-actions">
        <button onClick={() => graphInstance.current?.layout({ name: centered ? "breadthfirst" : "cose", directed: centered, animate: false, fit: true, padding: 40 }).run()}>그래프 정리</button>
        <button onClick={() => graphInstance.current?.fit(undefined, 40)}>그래프 맞춤</button>
      </div>
      <div className="graph-canvas" ref={container} data-testid="graph-canvas" />
      {!graph && <p className="graph-empty">표시할 자료 공간을 선택하세요.</p>}
      {edgeMessage && <div className="edge-message">{edgeMessage}</div>}
    </div>
  );
}
