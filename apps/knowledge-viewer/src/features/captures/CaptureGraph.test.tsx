import { render } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CaptureGraph } from "./CaptureGraph";

const cytoscapeState = vi.hoisted(() => ({
  selectors: [] as string[],
}));

vi.mock("cytoscape", () => ({
  default: vi.fn(({ container, style }: { container: HTMLElement; style: Array<{ selector: string }> }) => {
    cytoscapeState.selectors = style.map((item) => item.selector);
    container.append(document.createElement("canvas"));
    return {
      destroy: () => container.replaceChildren(),
      on: vi.fn(),
    };
  }),
}));

test("uses a Cytoscape truthy selector for candidate relations", () => {
  render(
    <CaptureGraph
      graph={{
        depth: 2,
        limit: 300,
        truncated: false,
        nodes: [
          { id: "clip", type: "CLIPBOARD_CAPTURE", label: "Android 단편", metadata: {} },
          { id: "session", type: "DEVELOPMENT_SESSION", label: "Windows 세션", metadata: {} },
        ],
        edges: [
          { id: "relation", from: "clip", to: "session", type: "excerpt_of", status: "suggested" },
        ],
      }}
      onOpenCapture={vi.fn()}
    />,
  );

  expect(cytoscapeState.selectors).toContain("edge[?candidate]");
  expect(cytoscapeState.selectors).not.toContain("edge[candidate = true]");
});
