import { expect, test } from "vitest";

import manifestText from "../public/manifest.webmanifest?raw";
import serviceWorker from "../public/sw.js?raw";

test("defines an installable standalone app manifest", () => {
  const manifest = JSON.parse(manifestText);

  expect(manifest.name).toBe("MDE Knowledge Viewer");
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons).toEqual(expect.arrayContaining([
    expect.objectContaining({ src: "/icons/knowledge-viewer.svg", purpose: "any maskable" }),
  ]));
});

test("keeps Graph API responses out of the service worker cache", () => {
  expect(serviceWorker).toContain('url.pathname.startsWith("/api/")');
  expect(serviceWorker).toContain("return;");
});
