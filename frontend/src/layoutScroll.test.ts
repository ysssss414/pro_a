import { afterEach, describe, expect, it } from "vitest";

import "./styles.css";

afterEach(() => document.body.replaceChildren());

function element(className: string) {
  const value = document.createElement("main");
  value.className = className;
  document.body.appendChild(value);
  return value;
}

function expectBoundedVerticalScroll(className: string) {
  const value = element(className);
  const style = getComputedStyle(value);
  expect(style.flexGrow).toBe("1");
  expect(["0", "0px"]).toContain(style.minHeight);
  expect(style.overflowY).toBe("auto");
  expect(style.overflowX).toBe("hidden");
}

describe("viewport-bounded product surface scrolling", () => {
  it("makes Research Home and long Research routes vertically reachable", () => {
    const workspace = element("research-workspace");
    for (let index = 0; index < 40; index += 1) {
      const section = document.createElement("section");
      section.textContent = index === 39 ? "final Research content" : `Research section ${index}`;
      workspace.appendChild(section);
    }

    const style = getComputedStyle(workspace);
    expect(style.flexGrow).toBe("1");
    expect(["0", "0px"]).toContain(style.minHeight);
    expect(style.overflowY).toBe("auto");
    expect(style.overflowX).toBe("hidden");
    expect(workspace.lastElementChild).toHaveTextContent("final Research content");
  });

  it("bounds the other affected long-page workspaces", () => {
    expectBoundedVerticalScroll("impact-workbench");
    expectBoundedVerticalScroll("jobs-workspace");
    expectBoundedVerticalScroll("jobs-workspace source-operations");
  });

  it("preserves the classic Explorer viewport and internal panel scrolling", () => {
    const explorer = element("workspace-grid");
    const results = document.createElement("section");
    results.className = "search-results";
    explorer.appendChild(results);
    const detail = document.createElement("section");
    detail.className = "tab-panel";
    explorer.appendChild(detail);

    const explorerStyle = getComputedStyle(explorer);
    expect(explorerStyle.display).toBe("grid");
    expect(["0", "0px"]).toContain(explorerStyle.minHeight);
    expect(explorerStyle.overflow).toBe("hidden");
    expect(getComputedStyle(results).overflowY).toBe("auto");
    expect(getComputedStyle(detail).overflowY).toBe("auto");
  });
});
