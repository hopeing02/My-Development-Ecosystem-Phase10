import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { GraphView } from "./GraphView";
import type { KnowledgeGraph } from "./types";

vi.mock("cytoscape", () => ({
  default: vi.fn(({ container }: { container: HTMLElement }) => {
    container.append(document.createElement("canvas"));
    return {
      destroy: () => container.replaceChildren(),
      fit: vi.fn(),
      layout: vi.fn(() => ({ run: vi.fn() })),
      on: vi.fn(),
    };
  }),
}));

const graph: KnowledgeGraph = {
  source: {
    id: "ks-001",
    name: "docs",
    category: "development",
    sourceType: "markdown",
    sensitive: false,
    enabled: true,
    documentCount: 0,
  },
  nodes: [],
  edges: [],
  brokenEdges: [],
  totalDocumentCount: 0,
  returnedDocumentCount: 0,
  truncated: false,
};

test("keeps React content outside the Cytoscape-owned container", () => {
  const view = render(
    <GraphView graph={graph} centered={false} highlightedIds={new Set()} onSelectNode={vi.fn()} />,
  );

  expect(view.getByTestId("graph-canvas").querySelector("canvas")).not.toBeNull();

  view.rerender(
    <GraphView graph={null} centered={false} highlightedIds={new Set()} onSelectNode={vi.fn()} />,
  );
  expect(screen.getByText("표시할 자료 공간을 선택하세요.")).toBeInTheDocument();
  expect(view.getByTestId("graph-canvas")).toBeEmptyDOMElement();

  expect(() => view.rerender(
    <GraphView graph={graph} centered={false} highlightedIds={new Set()} onSelectNode={vi.fn()} />,
  )).not.toThrow();
});
