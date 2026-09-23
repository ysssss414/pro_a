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
    expectBoundedVerticalScroll("jobs-workspace");
    expectBoundedVerticalScroll("jobs-workspace source-operations");
  });

  it("bounds each desktop two-column layout and contains wheel chaining in its panes", () => {
    for (const [workspaceClass, layoutClass, leftClass, rightClass] of [
      ["impact-workbench", "impact-layout", "impact-change-list", "impact-detail-column"],
      ["proposal-workspace", "proposal-workspace", "proposal-list-panel", "proposal-review-detail"],
      ["jobs-workspace durable-jobs-workspace", "jobs-layout", "jobs-list", "job-detail"],
    ]) {
      const workspace = element(workspaceClass);
      const layout = layoutClass === "proposal-workspace" ? workspace : document.createElement("div");
      if (layout !== workspace) { layout.className = layoutClass; workspace.appendChild(layout); }
      const left = document.createElement("section");
      left.className = leftClass;
      layout.appendChild(left);
      const right = document.createElement("section");
      right.className = rightClass === "proposal-review-detail" ? "detail-panel proposal-review-detail" : rightClass;
      layout.appendChild(right);
      expect(getComputedStyle(workspace).overflow).toBe("hidden");
      expect(getComputedStyle(layout).gridTemplateRows).toBe("minmax(0, 1fr)");
      for (const pane of [left, right]) {
        const style = getComputedStyle(pane);
        expect(style.minHeight).toMatch(/^0(px)?$/);
        expect(style.overflowY).toBe("auto");
        expect(style.overflowX).toBe("hidden");
        expect(style.overscrollBehavior).toBe("contain");
      }
    }
  });

  it("lets the Industry map canvas yield space while keeping its metadata intact", () => {
    const map = element("industry-map");
    for (const className of ["industry-map-header", "industry-map-modes", "industry-map-filters",
      "industry-map-canvas", "industry-map-messages", "industry-map-index", "industry-map-edge-detail", "industry-map-footer"]) {
      const block = document.createElement("div");
      block.className = className;
      map.appendChild(block);
      const style = getComputedStyle(block);
      if (className === "industry-map-canvas") expect(style.minHeight).toBe("120px");
      else expect(style.flexShrink).toBe("0");
    }
    expect(getComputedStyle(map).overflowY).toBe("auto");
    expect(getComputedStyle(map).overscrollBehavior).toBe("contain");
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
